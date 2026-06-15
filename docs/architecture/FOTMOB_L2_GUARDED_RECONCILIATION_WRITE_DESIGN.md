# FotMob L2 Guarded Reconciliation Write Design

- lifecycle: current-stage design decision
- scope: guarded reconciliation write design only
- status: design-only / no runtime implementation
- related contract: `docs/architecture/FOTMOB_L1_L2_HANDOFF_CONTRACT.md`
- related guarded consumer design: `docs/architecture/FOTMOB_L2_GUARDED_PENDING_CONSUMER_DESIGN.md`
- related reconciliation preview: `docs/_reports/fotmob_l2_reconciliation_preview_20260615.md`

## 1. Purpose / 目的

本文只定义未来如何安全地把已确认的 reconciliation candidates 从 `pending` 标记为 `harvested`。

当前明确不做：

- 当前不写 DB
- 当前不实现脚本
- 当前不修改 `pipeline_status`
- 当前只是 design gate

本文目标不是授权立刻修状态，而是把未来如果真的写库，必须满足的 guard、事务边界、授权方式和失败处理讲清楚。

## 2. Current Evidence / 当前证据

- `#1508` 证明当前 `60` 条 pending targets 中，有 `58` 条属于 `raw_exists_but_pending`。
- `#1509` 证明这 `58` 条 anomaly 全部集中在 `Ligue 1 / 2025/2026 / finished`，且：
  - `raw_row_count = 58`
  - `duplicate_raw_count = 0`
- `#1510` 证明这 `58` 条在当前 dev DB 中全部满足 reconciliation preview 的建议条件，结果为：
  - `candidate_total = 58`
  - `suggest_harvested_count = 58`
  - `hold_duplicate_raw_count = 0`
  - `hold_non_finished_count = 0`
  - `hold_missing_hash_or_payload_count = 0`
  - `hold_external_id_mismatch_count = 0`

结论是：当前 read-only 证据支持“这 58 条看起来像可被建议修正的 `pending -> harvested` 候选”，但这仍然不是写库授权。

## 3. Write Scope / 允许未来写入的最小范围

未来 guarded write 只允许做一件事：

- `matches.pipeline_status: pending -> harvested`

未来 guarded write 不能做：

- 不抓 FotMob
- 不写 `raw_match_data`
- 不改 raw payload
- 不改 `matches` 里的比赛元数据
- 不改 parser output
- 不改 feature/model
- 不新增 schema
- 不处理不满足 reconciliation candidate 条件的记录

也就是说，未来 write 如果存在，必须是 narrow reconciliation write，而不是新一轮 L2 ingest。

## 4. Required Hard Guards / 必须硬性保护

未来写库脚本必须满足以下硬保护：

- 默认 no-op
- 必须显式 `--allow-write`
- batch size 默认 `<= 3`
- 最大 batch size `<= 3`，不能通过参数突破
- 必须先执行 read-only preview
- 必须输出 before/after preview
- 必须在单事务中执行
- 必须逐行校验
- 必须只允许 `pending -> harvested`
- 必须禁止 live fetch
- 必须禁止 raw payload output

这里的关键不是“能不能写”，而是“默认绝不写，只有显式授权且 guard 全通过才允许尝试一小批”。

## 5. Candidate Eligibility / 候选资格

未来一条 row 只有同时满足以下条件，才允许进入 guarded write candidate：

- `matches.pipeline_status = 'pending'`
- `matches.external_id` 非空
- `matches.status = 'finished'`
- `raw_match_data` 存在同 `match_id + data_version = 'fotmob_live_v1'`
- 同 `match_id + data_version = 'fotmob_live_v1'` 的 raw row count = 1
- raw row `raw_data` 非空
- raw row `data_hash` 非空
- 如果 `raw_match_data.external_id` 存在，必须等于 `matches.external_id`
- 当前 row 不能已是 `harvested`
- 当前 row 不能是 `processing`
- 当前 row 不能是 `failed`
- 当前 row 不能是 `skipped`

当前 read-only 证据表明 58 条 Ligue 1 样本满足这些条件，但 future write 仍必须在真正执行前重新做一次实时校验，不允许直接复用旧报告当执行凭证。

## 6. Hold / Exclusion Reasons / 暂缓原因

未来脚本必须把以下情况排除或 hold，不允许写入：

- no raw
- duplicate raw
- non-finished match
- missing external_id
- raw_data missing
- data_hash missing
- external_id mismatch
- status already harvested
- status processing
- status failed/skipped
- unknown pipeline_status

设计原则是：任何不确定性都优先变成 hold，而不是“先写了再说”。

## 7. Proposed SQL Guard / SQL 防护草案

未来 preview candidate select 可参考以下伪 SQL：

```sql
WITH candidate AS (
  SELECT
    m.match_id,
    m.external_id,
    m.pipeline_status,
    m.status,
    COUNT(r.id) AS raw_row_count
  FROM matches m
  JOIN raw_match_data r
    ON r.match_id = m.match_id
   AND r.data_version = 'fotmob_live_v1'
  WHERE m.pipeline_status = 'pending'
    AND NULLIF(BTRIM(m.external_id), '') IS NOT NULL
    AND LOWER(COALESCE(m.status, '')) = 'finished'
  GROUP BY m.match_id, m.external_id, m.pipeline_status, m.status
  HAVING COUNT(r.id) = 1
)
SELECT *
FROM candidate
ORDER BY match_id
LIMIT 3;
```

未来写入 SQL 草案必须至少包含如下 guard：

```sql
UPDATE matches
SET pipeline_status = 'harvested',
    updated_at = NOW()
WHERE match_id = $1
  AND pipeline_status = 'pending'
  AND EXISTS (
    SELECT 1
    FROM raw_match_data r
    WHERE r.match_id = matches.match_id
      AND r.data_version = 'fotmob_live_v1'
  )
RETURNING match_id, pipeline_status;
```

补充说明：

- `V12.2` migration 中已经使用了 `updated_at = NOW()`，说明仓库当前设计默认期待该列存在。
- 如果 future execution 环境里 `matches` 实际没有 `updated_at`，未来脚本必须按真实 schema 调整，不允许借机新增 migration。
- 仅有 `EXISTS raw_match_data` 还不够；future script 还必须在 preview 阶段把 duplicate raw、缺失 `raw_data/data_hash`、external_id mismatch 排除掉。

## 8. Transaction / Rollback Design / 事务与回滚设计

未来事务设计必须遵守：

- 一批最多 `3` 条
- 每批一个 transaction
- 任意 row 不满足 guard，整批 rollback
- 执行前输出 before rows
- 执行 guarded update
- 执行后输出 after rows
- 对比数量必须一致
- 不一致则 rollback
- 成功才 commit
- dry-run 默认 rollback，或者根本不进入 write transaction

推荐顺序：

1. 先做 read-only candidate preview
2. 固定本批 candidate list，最多 3 条
3. 开启 write transaction
4. 再次逐行验证当前状态仍满足 guard
5. 执行 `pending -> harvested`
6. 读取 after rows，对比 before/after 数量与状态变化
7. 任何异常立即 rollback
8. 只有全部一致才 commit

## 9. CLI Contract / 命令行契约

未来脚本建议名字：

```text
scripts/ops/l2_guarded_reconciliation_write.js
```

建议 CLI：

```text
--limit <n>              默认 3，最大 3
--json
--league <name>
--season <season>
--status <status>
--allow-write            没有这个参数绝不写库
--expected-count <n>     可选，防止写入数量漂移
```

必须明确：

- 不带 `--allow-write`：只 preview，不写
- 带 `--allow-write`：也必须先 preview，再写
- 写入前必须打印 candidate list
- 写入后必须打印 before/after
- 不允许 quiet mode
- 不允许一次把 `58` 条全部写完

## 10. Audit Output / 审计输出要求

未来脚本必须输出：

- phase
- safety flags
- selected candidates
- before `pipeline_status`
- after `pipeline_status`
- per-row decision
- commit/rollback result
- skipped/held reasons
- no raw payload

每条 row 只允许输出：

- `match_id`
- `external_id`
- `league_name`
- `season`
- `home_team`
- `away_team`
- `match_date`
- `old_pipeline_status`
- `new_pipeline_status`
- `raw_data_version`
- `raw_row_count`
- `decision`
- `reason`

## 11. Failure Modes / 失败模式

未来至少要显式处理这些失败模式：

- row drift：preview 后状态被别人改了
  - 处理：停止、rollback、报告
- raw disappeared
  - 处理：停止、rollback、报告
- duplicate raw 出现
  - 处理：停止、rollback、报告
- external_id mismatch
  - 处理：停止、rollback、报告
- DB transaction error
  - 处理：停止、rollback、报告
- partial update attempt
  - 处理：停止、rollback、报告
- updated count mismatch
  - 处理：停止、rollback、报告
- CI / local env mismatch
  - 处理：停止、报告，不自动修复
- stale branch / stale main
  - 处理：停止、重新同步后再 review，不自动继续旧 baseline

原则非常简单：future write 失败后只允许 rollback 和报告，不允许“顺手自动修复”。

## 12. Rollout Plan / 推进计划

建议按以下阶段推进：

1. design PR：当前 PR，只写本文档
2. no-op-by-default write script draft：默认不写，只 preview + tests
3. guarded write script with `--allow-write`，但不执行真实写库
4. user 手动确认后，最多 batch size `3`，小批量执行
5. 执行后再做 read-only verification report

这个 rollout 的目的，是把“设计、脚本、授权、执行、验证”拆开，而不是让单个 PR 同时承担全部风险。

## 13. Explicit Non-Goals / 明确非目标

本设计明确不做：

- 不抓数据
- 不修 raw
- 不改 parser
- 不做 feature/model
- 不改 schema
- 不创建 migration
- 不执行真实 write
- 不处理 `900002` no raw 的那 `1` 条
- 不处理 scheduled pending 的那 `1` 条
- 不处理后续 L2 live consumer

## 14. Next Recommended Task / 下一步建议

- 下一 PR 可以做 no-op-by-default guarded reconciliation write script draft。
- 默认仍不写 DB。
- 只实现 preview + SQL guard + tests。
- 即使带上 `--allow-write` 设计，本阶段也不要实际执行写库。
- Do not start automatically
- Recommended next task only after user confirmation

## 15. Gaps / 缺口

- 本次只读检查中，用户要求的证据文件都存在，当前没有额外缺失项。
- future write 真正落地前，仍需再次核对执行环境里的 `matches.updated_at`、`raw_match_data.external_id`、`raw_match_data.raw_data`、`raw_match_data.data_hash` 是否与当前 dev DB 观察一致。
