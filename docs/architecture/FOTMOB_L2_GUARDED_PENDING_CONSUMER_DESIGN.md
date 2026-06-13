# FotMob L2 Guarded Pending Consumer Design

- lifecycle: current-stage design
- status: design-only
- last_updated: 2026-06-13
- related_contract: docs/architecture/FOTMOB_L1_L2_HANDOFF_CONTRACT.md
- related_dry_run_result: docs/_reports/fotmob_l2_pending_target_selection_dry_run_result_20260613.md

## 1. Scope / 本文边界

本文只设计 FotMob L2 guarded pending consumer / state transition workflow，不实现任何 runtime code。

本文明确不做：

- no live fetch
- no DB write
- no raw_match_data write
- no parser/model/feature/schema change
- no migration

本文目标只有一个：回答如果未来要安全消费 `matches + pipeline_status` 中的 pending targets，应该如何设计 claim、锁定、状态流转、幂等、失败重试和审计边界。

## 2. Current Facts / 当前事实

- `#1504` 已把当前阶段正式 handoff carrier 定为 `matches + pipeline_status`，并明确 `raw_match_data` 是当前 raw retained 成功落点。
- `#1505` 已提供 `scripts/ops/l2_pending_target_selection_dry_run.js`，它以 `BEGIN READ ONLY` / `SELECT` / `ROLLBACK` 方式只读筛选未来 L2 会消费的 targets。
- `#1506` 的结果报告确认当前 dev DB 中按默认规则能选出 `60` 条 pending targets。
- 当前 dry-run 规则的核心是：
  - `external_id IS NOT NULL`
  - `pipeline_status = pending`
- 当前 `matches.pipeline_status` 合法状态来自 `V12.2` / `V12.3`：
  - `pending`
  - `processing`
  - `harvested`
  - `failed`
  - `skipped`
  - `RECON_LINKED`
  - `RECON_MISMATCH`
- 当前 60 条 dry-run targets 里：
  - `selected_count = 60`
  - `failed_count = 0`
  - 主要样本为 `status=finished`、`pipeline_status=pending`
  - league naming 还存在 `Segunda` / `Segunda División` 并存现象

## 3. Consumer Goal / Consumer 目标

未来 guarded consumer 的目标应当是：

- 安全领取 pending targets
- 避免重复消费同一个 match
- 避免多个 worker 同时处理同一 target
- 支持成功、失败、重试、跳过
- 支持人工审计和事后复盘
- 支持处理中断后的恢复
- 不把 raw retention、parser、feature、training 混成一个阶段

换句话说，consumer 要解决的是 “谁被领取、何时被领取、失败后如何恢复、如何避免重复和脏状态”，而不是一次性完成全部后续数据链路。

## 4. Non-goals / 明确不做

本文明确不设计这些当前阶段之外的内容：

- 不直接实现 live FotMob fetch
- 不直接实现 raw retention
- 不改 parser
- 不改 feature/model
- 不改 odds/backtest
- 不新增 schema/migration，除非后续单独 PR 决定
- 不自动处理全部 60 条 pending targets

特别是：pending consumer design 不是授权去一次性消费当前 60 条 targets，也不是授权去立即实现批量 live fetch。

## 5. Proposed State Machine / 建议状态机

当前建议继续基于 `matches.pipeline_status` 的现有主状态设计最小状态机：

- `pending`
- `processing`
- `harvested`
- `failed`
- `skipped`

`RECON_LINKED` / `RECON_MISMATCH` 继续保留给 recon 后续流程，不应由当前 guarded pending consumer 直接写入。

### 5.1 推荐流转

```text
pending -> processing
processing -> harvested
processing -> failed
failed -> pending
failed -> skipped
pending -> skipped
processing -> pending   (仅限超时恢复或人工恢复)
```

### 5.2 Transition 说明

#### `pending -> processing`

- 触发条件：
  - target 满足当前 selection rule
  - 当前状态仍然是 `pending`
  - `external_id` 非空
  - future implementation 如要 live fetch，应先通过显式授权 gate
- 触发者：
  - future guarded consumer
- 幂等保护：
  - 必须有
  - transition 必须以 “当前状态仍是 pending” 为前置条件
- 是否允许自动重试：
  - claim 本身不需要 retry 语义
  - claim 失败应只说明“没领到”，不能强行覆盖状态
- 是否需要人工确认：
  - default no-op 模式不需要
  - 真正写状态需要显式 write authorization

#### `processing -> harvested`

- 触发条件：
  - raw retention 已成功完成
  - `raw_match_data` 已确认存在正确 row
  - 推荐 conflict key 为 `(match_id, data_version)`
- 触发者：
  - future guarded retention flow
- 幂等保护：
  - 必须有
  - 应仅在当前仍为 `processing` 时写入 `harvested`
- 是否允许自动重试：
  - 如前一步 raw write 已完成且校验通过，可重放 `processing -> harvested`
- 是否需要人工确认：
  - 默认不需要
  - 但状态更新与 raw write 一致性必须可审计

#### `processing -> failed`

- 触发条件：
  - live fetch / transform / raw write / verification 任一步失败
- 触发者：
  - future guarded retention flow
- 幂等保护：
  - 必须有
  - 只允许从 `processing` 进入 `failed`
- 是否允许自动重试：
  - 不直接自动回 `pending`
  - 推荐先记录失败，再经显式 retry policy 处理
- 是否需要人工确认：
  - transient failure 不一定需要
  - permanent / repeated failure 需要

#### `failed -> pending`

- 触发条件：
  - 人工确认该 target 可重新尝试
  - 或 future small-batch retry flow 明确授权重试
- 触发者：
  - future retry script / 人工恢复工具
- 幂等保护：
  - 必须有
  - 只允许从 `failed` 回 `pending`
- 是否允许自动重试：
  - 可以，但必须有小批量上限、attempt cap 和明确分类
- 是否需要人工确认：
  - 推荐 yes，至少在当前阶段如此

#### `failed -> skipped`

- 触发条件：
  - target 被判断为当前阶段不值得继续重试
  - 例如稳定 404、长期结构缺失、非当前范围
- 触发者：
  - future failure triage / manual review
- 幂等保护：
  - 必须有
- 是否允许自动重试：
  - no
- 是否需要人工确认：
  - yes

#### `pending -> skipped`

- 触发条件：
  - target 明确不在当前轮范围
  - 或被识别为历史坏样本/业务上不应采集
- 触发者：
  - future curation / manual review
- 幂等保护：
  - 必须有
- 是否允许自动重试：
  - no，除非人工重新放回 `pending`
- 是否需要人工确认：
  - yes

#### `processing -> pending`

- 触发条件：
  - 仅限 claim 后 worker 崩溃、超时恢复、人工恢复
- 触发者：
  - future recovery flow
- 幂等保护：
  - 必须有
  - 必须带 timeout / stale lock 语义，不可任意回退
- 是否允许自动重试：
  - 可在严格 guard 下允许
- 是否需要人工确认：
  - 当前阶段推荐 yes

## 6. Claim / Locking Strategy / 领取与锁定策略

### 6.1 方案 A：直接用 `matches.pipeline_status` 做 claim

最小化方案是直接用条件状态更新领取目标：

```sql
UPDATE matches
SET pipeline_status = 'processing'
WHERE match_id IN (...)
  AND pipeline_status = 'pending'
RETURNING match_id, external_id, league_name, season, match_date;
```

优点：

- 直接复用当前正式 contract
- 不需要新表
- 当前阶段概念最少
- 容易和 dry-run selection 逻辑对应

缺点：

- `pipeline_status` 同时承担 handoff state 和 claim lock 语义
- 并发 worker 下只能靠条件更新保护，缺少更细粒度 lease metadata
- 无法自然记录 `locked_at`、`locked_by`、`attempt_count`、`last_error`

### 6.2 方案 B：未来引入独立 consumer job table / lease table

例如未来可以有：

```text
fotmob_l2_jobs
match_id
external_id
status
attempt_count
locked_at
locked_by
last_error
last_result
```

优点：

- claim / lease / retry metadata 更清晰
- 并发与恢复策略更容易表达
- 审计字段更容易落地

缺点：

- 当前阶段会引入额外 schema 和同步复杂度
- 会和 `matches.pipeline_status` 形成双状态源风险
- 需要新的 migration、reconciliation 和 contract 更新

### 6.3 当前阶段推荐

当前推荐先不实现 job table；先做最小 guarded transition design。

具体含义：

- 下一阶段先继续围绕 `matches + pipeline_status` 设计和验证
- 在真正出现并发 worker、长时间 lease、attempt metadata 不够用之前，不急着引入 job table
- 如果未来进入真实并发消费，再考虑 job table / lease table

## 7. Idempotency / 幂等设计

### 7.1 同一个 match 被重复处理怎么办

必须假设重复领取、重复执行、进程重启都会发生。

因此 future implementation 至少要满足：

- claim 必须依赖 `WHERE pipeline_status = 'pending'`
- 任何后续状态写入必须依赖当前状态条件
- raw write 必须依赖 `raw_match_data` 的唯一性/冲突保护

### 7.2 raw 写入如何避免重复

当前 contract 已推荐：

- 写入表：`raw_match_data`
- 推荐 `data_version`：`fotmob_live_v1`
- conflict key：`(match_id, data_version)`

当前参考实现也说明两种现实：

- `l2_raw_match_data_write.js` 使用 `ON CONFLICT (match_id, data_version) DO NOTHING`
- `n3_live_fotmob_raw_retain.js` 使用 `ON CONFLICT (match_id, data_version) DO UPDATE`

对 guarded consumer 来说，当前推荐是：

- 继续以 `(match_id, data_version)` 作为幂等主键
- 状态机设计不依赖 “再次插入成功” 才算成功
- 只要目标 row 已存在且与本轮目标一致，future implementation 可将其视作 idempotent success 候选

### 7.3 如果 raw 已存在但 `pipeline_status` 仍是 `pending`

这是异常状态，不应直接按普通 pending 处理。

当前推荐：

- read-only preview 应把这类 target 标为 anomaly
- 不直接 live fetch
- 不直接自动写 `harvested`
- 后续单独做 guarded reconciliation preview / fix design

### 7.4 如果 `pipeline_status = harvested` 但 raw 缺失

这也是异常状态。

当前推荐：

- 先只读审计
- 不自动回退到 `pending`
- 不自动重抓
- 后续单独做 harvested/raw consistency audit

## 8. Failure / Retry Policy / 失败与重试

### 8.1 失败分类

future implementation 至少要区分：

- 网络失败：timeout / connection reset / temporary 5xx
- rate limit / anti-bot：403 / throttle / blocked
- not found / invalid route：404
- transform failure：例如 `TRANSFORM_FAILED: no structured match data`
- raw write failure：DB transaction / conflict / verification mismatch
- post-write status update failure

### 8.2 关于 `external_id=900002` 的历史 blocker

当前 dry-run 的样本里包含：

- `match_id = 47_20242025_900002`
- `external_id = 900002`

同时现有 `FotMobRawDetailFetcher` 已明确存在失败形态：

- `TRANSFORM_FAILED: no structured match data`

因此未来 retry policy 必须把这类 target 当作历史风险样本看待：

- `pending` 不代表一定可 fetch
- `external_id` 非空也不代表一定能得到结构化 detail payload
- 对类似 `900002` 的历史坏样本，应优先以小批量、单目标、显式授权方式验证，不要自动批量并发推进

### 8.3 retry 建议

当前阶段推荐的保守策略：

- transient error：
  - 可重试
  - max attempts 很小，建议 `<= 2`
  - retry interval 应显式，不隐式循环
- rate limit / anti-bot：
  - 不立刻自动重试
  - 应结束本轮并上报
- 404 / no structured match data：
  - 先进入 `failed`
  - 不自动无限重试
  - 经人工确认后才决定回 `pending` 还是 `skipped`
- repeated failure：
  - 超过小上限后进入人工审查

### 8.4 parser 不参与本阶段，但未来要留好边界

当前阶段应把：

- fetch 失败
- hydration / transform 失败
- raw write 失败

都视为 L2 retained raw 阶段的失败。

未来 parser 失败应单独建 parser contract，不应复用同一个 `pipeline_status` 直接混写。

## 9. Batch Size / Rate Limit / Safety Gate / 批量与安全闸

当前推荐：

- 初始 batch size 极小，建议 `1-3`
- 明确分阶段：
  - dry-run
  - preview
  - guarded write
  - live fetch
- 每阶段必须单独 PR
- 不允许一次性消费 60 条
- 必须有 max limit hard cap
- 必须有显式 `--allow-write` flag
- 必须有显式 `--allow-live-fetch` flag
- 默认全是 no-op / dry-run

推荐的安全闸顺序：

1. read-only selection dry-run
2. read-only transition preview
3. guarded pending -> processing write
4. single-target or tiny-batch live fetch for already-processing targets
5. guarded `processing -> harvested/failed` completion transition

## 10. Audit Trail / 审计信息

未来至少需要能重建以下审计字段：

- `match_id`
- `external_id`
- `old_status`
- `new_status`
- `worker/run_id`
- `attempted_at`
- `result`
- `error_code`
- `error_message`
- `raw_match_data id`
- `data_version`
- `source script`
- `commit sha`

当前 PR 只设计，不新增表。

因此当前推荐是：

- 先通过结构化日志、stdout JSON、报告 artifact 保留这些字段
- 等真正进入并发/恢复复杂度上升时，再决定是否需要单独审计表

## 11. Minimal Implementation Roadmap / 最小实施路线

推荐后续拆成多个小 PR：

- PR A：read-only transition preview，模拟 `pending -> processing`，不写库
- PR B：guarded state transition script，只允许 `pending -> processing`，必须 `--allow-write`，batch size `<= 3`
- PR C：processing timeout / recovery preview，专门只读检查哪些 `processing` targets 可能是 stale claims
- PR D：guarded raw retention for processing targets，batch size `<= 1`，必须 `--allow-live-fetch` + `--allow-write`
- PR E：基于 raw retention 结果执行 `processing -> harvested` 或 `processing -> failed` 的 guarded completion transition

这条路线的核心不是快，而是：

- 每一步都可观察
- 每一步都能回滚思路
- 每一步都能隔离失败面

## 12. Acceptance Criteria / 验收标准

未来实现 PR 至少应满足：

- default mode never writes
- write mode requires explicit flag
- live fetch requires explicit separate flag
- batch size hard cap
- all transitions are conditional on current status
- every write is idempotent or guarded
- raw write and status update failure must not leave ambiguous state
- logs can reconstruct what happened

补充建议：

- claim 结果必须返回实际成功领取的 rows，而不是假设全部成功
- stale `processing` recovery 必须有单独 preview
- `failed -> pending` 不应默认自动化批量执行

## 13. Risks / 风险

当前至少有这些风险：

- 60 条 pending 里可能存在历史坏样本
- league naming 不收敛，例如 `Segunda` / `Segunda División`
- pending 不代表一定可 fetch
- live fetch 可能触发 rate limit / anti-bot
- status transition 与 raw write 可能不一致
- 并发 worker 可能重复领取
- `pipeline_status` 语义可能被其他旧脚本污染
- legacy 路径里存在 `ON CONFLICT (match_id)` 风格，和当前推荐的 `(match_id, data_version)` 不完全一致
- old consumer / harvester 代码已经存在从 `matches LEFT JOIN raw_match_data` 扫 pending 的思路，但 guard 粒度不足，不能直接当成当前正式实现

## 14. Recommendation / 当前推荐结论

当前明确建议：

下一 PR 不做 live fetch。
下一 PR 推荐只做 read-only transition preview。
目标是模拟哪些 records 会从 pending 被 claim 为 processing，但不写 DB。

换句话说，下一步只回答：

- 哪些 pending rows 会被 future consumer 领取
- 如果应用 `pending -> processing` guard，会成功领取多少
- 哪些 rows 会因为异常条件被排除或标记为 anomaly

但下一步仍然：

- 不做 live fetch
- 不写 DB
- 不更新 `pipeline_status`

## 15. Evidence / 证据索引

- `docs/architecture/FOTMOB_L1_L2_HANDOFF_CONTRACT.md`
- `docs/_reports/fotmob_l2_pending_target_selection_dry_run_20260613.md`
- `docs/_reports/fotmob_l2_pending_target_selection_dry_run_result_20260613.md`
- `scripts/ops/l2_pending_target_selection_dry_run.js`
- `scripts/ops/l2_raw_match_data_write.js`
- `scripts/ops/n3_live_fotmob_raw_retain.js`
- `src/infrastructure/services/FotMobRawDetailFetcher.js`
- `database/migrations/V12.2__add_matches_pipeline_status.sql`
- `database/migrations/V12.3__expand_matches_pipeline_status_for_recon.sql`
- `database/migrations/V26.5__create_fotmob_raw_match_payloads.sql`
- `database/migrations/V26.6__create_football_calendar_target_registry.sql`
- `src/infrastructure/services/MarathonService.js`
- `src/infrastructure/harvesters/ProductionHarvester.js`
- `scripts/ops/backfill_historical_raw_match_data.js`

### Evidence / Gaps

- 本次指定文件均存在，未发现缺失项
- 当前没有看到专门的 claim lease schema；如果未来需要并发 worker 级别锁定，需另开 schema design / migration PR
