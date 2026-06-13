# FotMob L1/L2 Handoff Contract

- lifecycle: permanent
- status: current-stage design decision
- last_updated: 2026-06-13

## 1. Scope / 本文边界

本文只定义 FotMob 的 L1 -> L2 handoff contract。

本文明确不做这些事：

- 不实现 runtime 代码
- 不抓新数据
- 不访问 FotMob live detail
- 不运行 scraper
- 不写数据库
- 不做 parser / feature / model / prediction
- 不改测试
- 不改 schema / migration

本文的目的只有一个：把当前阶段谁负责发现、谁负责抓 raw、通过什么实体交接、由谁维护状态，说清楚。

## 2. Background / 背景

`docs/_reports/fotmob_l1_l2_pipeline_audit_20260613.md` 已经把当前现状说得很清楚：

- L1 存在
- L2 存在
- 但当前没有一个正式、统一、自动的 L1 -> L2 handoff / task pool / state contract

审计同时证明了两件事：

- L1 当前正式落点是 `matches`
- L2 当前真实在用的 retained raw 落点是 `raw_match_data`

真正没定死的，不是“能不能发现”或“能不能抓 raw”，而是：

- L1 发现结果到底进入哪里，才算正式交接给 L2
- L2 到底消费哪里
- 状态字段到底谁说了算

## 3. Contract Decision / 当前正式决策

当前推荐正式 handoff 承载物：`matches + pipeline_status`

当前不选另一条路线 `football_match_targets + raw_json_status / target_state` 的原因：

- 它更像长期任务池和长期 registry 设计，不是当前 retained raw 真实落地路径
- 当前 `raw_match_data` 仍然依赖 `matches(match_id)` 外键，L2 实操上离 `matches` 更近
- `#1502` 的 bounded retained raw 扩容也是围绕已有 `matches + external_id` 候选推进，不是消费 `football_match_targets`
- 如果现在硬切到 `football_match_targets`，会把“先定闭环”变成“先做迁移和接线”，实现成本和迁移成本都更高

因此，本 contract 的当前阶段正式建议是：

- L1 正式输出到 `matches`
- L2 正式从 `matches` 中挑选待抓取目标
- L1 -> L2 的 authoritative handoff state 先收敛在 `matches.pipeline_status`

这里的判断不是说 `football_match_targets` 没价值，而是说它当前还不是正式 current path。它保留为后续长期 registry / scheduler 路线候选，但不作为本阶段正式 handoff carrier。

## 4. L1 Responsibilities / L1 职责

当前阶段，FotMob L1 的正式职责只有 discovery / schedule / fixtures / match identity。

L1 应负责：

- 按 `league + season` 发现 fixtures
- 生成稳定 `match_id`
- 保留 FotMob `external_id`
- 产出基础 fixture metadata，例如联赛、赛季、主客队、比赛时间、业务状态
- 把上述结果持久化到 `matches`

L1 不负责：

- 抓 FotMob detail raw
- 写 `raw_match_data`
- 处理 parser 成功/失败
- 把 raw 转成 features

一句话讲清楚：L1 只负责“发现比赛并建立 identity”，不负责“抓比赛详情”。

## 5. L2 Responsibilities / L2 职责

当前阶段，FotMob L2 的正式职责只有消费待抓取目标、抓 detail raw、做 raw retention。

L2 应负责：

- 从正式 handoff carrier 中选择可抓取目标
- 使用 `external_id` 执行 detail fetch
- 把成功获取的 raw detail 留存在 `raw_match_data`
- 回写 handoff state，说明该目标已经 raw retained、失败、或被跳过

L2 不负责：

- 重新发现赛程
- 重建 fixture identity
- 改写 `matches` 的业务状态含义
- 在本 contract 中承担 parser / feature / training / prediction

一句话讲清楚：L2 只负责“消费已发现目标并保留 raw”，不负责“重新发现目标”。

## 6. Handoff Entity / 交接实体

当前阶段，L1 交给 L2 的最小实体就是一条可被 L2 消费的 `matches` 记录，加上 `pipeline_status` 作为 handoff state。

最小字段集合如下：

| 字段 | 必填 | 来源 | 用途 |
| --- | --- | --- | --- |
| `match_id` | yes | L1 | internal stable match key |
| `external_id` | yes | FotMob | L2 detail fetch key |
| `league` | yes | L1 | audit / filtering |
| `season` | yes | L1 | audit / filtering |
| `home_team` | yes | L1 | validation / metadata |
| `away_team` | yes | L1 | validation / metadata |
| `match_date` | yes | L1 | scheduling / audit |
| `status` | yes | L1 | decide eligible for raw retention |

为了避免歧义，这里补两条约束：

- 表里的逻辑字段 `league`，在当前 `matches` 实现里对应 `league_name`
- 业务状态字段指的是 `matches.status`，它表达比赛本身是 `scheduled/live/finished/...`
- handoff 状态字段指的是 `matches.pipeline_status`，它表达 L1 -> L2 流水线推进到哪一步

换句话说：

- `status` 说的是“这场球是什么状态”
- `pipeline_status` 说的是“这条 L1 产物有没有被 L2 处理”

## 7. State Machine / 状态机

当前阶段推荐的最小正式状态机，直接复用 `matches.pipeline_status` 已有命名：

| 状态名 | 含义 | 谁写入 | 什么时候变更 | 失败如何处理 | 是否允许 retry |
| --- | --- | --- | --- | --- | --- |
| `pending` | L1 已发现并写入 `matches`，L2 尚未处理 | L1 | fixture 成功落到 `matches` 后 | 不适用 | yes |
| `processing` | L2 已领取目标，正在执行 raw fetch / retain | L2 | L2 consumer 开始处理该目标时 | 若 fetch 或 retain 失败，转 `failed` | yes |
| `harvested` | raw retain 已成功完成 | L2 | `raw_match_data` 成功写入并通过最小校验后 | 不适用 | 通常不需要 |
| `failed` | L2 处理失败，但目标仍可后续重试 | L2 | fetch 失败、transform 失败、raw write 失败、guard 失败后 | 保留失败信息在日志/报告，后续可人工或程序重试 | yes |
| `skipped` | 当前轮次明确不处理该目标 | L1 或 L2 | 明确不在本轮范围、业务状态不合适、人工排除时 | 如后续条件变化，可人工回到 `pending` | yes |

当前 contract 的流转建议如下：

```text
L1 discover success
-> matches row inserted/updated
-> pipeline_status = pending
-> L2 selects pending rows
-> pipeline_status = processing
-> raw retain success -> pipeline_status = harvested
-> raw retain failure -> pipeline_status = failed
```

关于 `matches.status` 与 eligible 规则，当前阶段建议只定原则，不把策略做得过细：

- `external_id` 为空的目标，不应进入 L2
- 明显不在当前 raw retention 范围内的业务状态，可以标记 `skipped`
- 其余可消费目标进入 `pending`

关于 retry，当前阶段也只定最小原则：

- `failed` 可以重试
- 重试前应先回到 `pending`，再由 L2 重新领取
- 当前 schema 没有完备 failure metadata，本 contract 不强行扩展字段，只先把主状态定死

## 8. Raw Retention Contract / raw 留存契约

本 contract 只定义到 raw retained 为止。

L2 成功后，当前正式写入边界是：

- 写入表：`raw_match_data`
- 推荐 `data_version`：`fotmob_live_v1`
- conflict key：`(match_id, data_version)`

成功条件的最小定义：

1. L2 通过 `external_id` 成功拿到 detail raw
2. `raw_match_data` 成功完成 INSERT/UPSERT
3. 写入对象仍然绑定同一个 `match_id`
4. 最小结构校验通过
5. 之后才允许把 `pipeline_status` 改成 `harvested`

这里要特别说明：

- `fotmob_raw_match_payloads` 是另一条长期 raw JSON 设计路线
- 当前 contract 不把它定义成 FotMob L1 -> L2 正式 handoff 的成功落点
- 如果未来切换到那条路线，需要新的 contract 或本 contract 的下一版更新

## 9. Parser Boundary / parser 边界

本 contract 只到 raw retained。

明确边界如下：

- parser 不属于本 PR 实现范围
- parser 成功/失败不纳入当前这版 L1 -> L2 handoff state machine
- parser contract 留给下一阶段单独定义

原因很简单：

- 当前最急的是先定 L1 和 L2 之间怎么交接
- parser 属于 raw retained 之后的下一层责任边界
- 现在把 parser 硬塞回同一个 contract，只会把当前决策重新搞复杂

所以本阶段的正式口径是：

```text
本 contract 只到 raw retained。
parser success / failure 留到下一阶段 parser contract。
```

## 10. #1502 Classification / #1502 在新 contract 中的位置

`#1502` 的正式归类应当是：

```text
#1502 是 bounded candidate-driven L2 retained raw validation。
它不是正式 L1 -> L2 自动闭环。
在新 contract 下，它应被视为 L2 consumer 的手工验证样本，而不是正式任务池。
```

原因：

- `#1502` 证明了 `raw_match_data` retained raw 扩容可以做，而且 parser dry-run `58/58` 通过
- 但它没有把 L1 discover 后的新 fixtures 自动推进到 L2
- 它消费的是 bounded candidate scope，不是正式 scheduler / task pool

所以 `#1502` 的意义是“验证了 L2 retained raw 这条路是真的能跑”，不是“已经拥有正式 handoff contract”。

## 11. Risks / 风险

如果不先把 contract 定死，风险会继续累积：

- `matches + pipeline_status` 与 `football_match_targets` 双轨继续分叉
- retained raw 与长期 registry 设计长期脱节
- 后续 parser / feature 很难追踪 raw 来源到底来自哪条正式路径
- 自动调度很容易误消费错误目标或重复消费
- 团队会继续把“bounded sample 扩容”误判成“正式流水线已经打通”
- 状态字段没有 authoritative source，后续任何报表和调度都会越来越不可信

## 12. Minimal Implementation Plan / 后续最小实现计划

本 contract 之后，建议只做一个后续最小实现 PR：

```text
下一 PR 只实现基于 matches + pipeline_status 的 L2 pending target selection dry-run。
```

这个最小 PR 应只做这些事：

- 从 `matches` 中选择 `external_id` 非空、`pipeline_status='pending'` 的候选
- 输出 dry-run summary，明确哪些目标会被 L2 消费
- 不抓新数据
- 不做 live fetch
- 不写 `raw_match_data`
- 不改 parser

这样做的好处是：

- 先把“L2 到底消费谁”落成最小、可验证的 current path
- 不会把下一步升级成 live fetch 或 schema 迁移
- 可以直接验证本 contract 的可执行性

## 13. Non-goals / 明确不做

本 contract 明确不做这些事：

- 不抓新数据
- 不写 DB
- 不改 parser
- 不做 feature / model / training / prediction
- 不做 odds
- 不做 backtest
- 不新增 migration
- 不新增 schema
- 不把 `football_match_targets` 立刻接成正式生产任务池
- 不解决所有历史 legacy 路线

## 14. Evidence / 证据索引

- `docs/_reports/fotmob_l1_l2_pipeline_audit_20260613.md`
  - 证明 L1 存在、L2 存在，但当前没有正式统一 handoff contract。
- `src/infrastructure/services/DiscoveryService.js`
  - 证明 L1 有正式 discover 写库路径，也有 candidates preview 只读路径。
- `src/infrastructure/services/DiscoveryAttributeMapper.js`
  - 证明 L1 已能稳定产出 `match_id / external_id / season / home_team / away_team / match_date / status`。
- `src/infrastructure/services/FixtureRepository.js`
  - 证明 L1 当前正式落点是 `matches`。
- `database/migrations/V12.2__add_matches_pipeline_status.sql`
  - 证明 `matches.pipeline_status` 已被明确设计为 L1/L2 pipeline state。
- `database/migrations/V12.3__expand_matches_pipeline_status_for_recon.sql`
  - 证明 `pipeline_status` 后续被扩展过，说明这条路线是历史真实存在的工业化思路。
- `src/infrastructure/services/FotMobRawDetailFetcher.js`
  - 证明 L2 detail fetch 当前按 `external_id` 工作，而且自己不是任务池。
- `scripts/ops/single_live_fotmob_raw_ingest_smoke.js`
  - 证明当前单目标 retained raw 路线依赖显式 `match_id + external_id` 输入，并写 `raw_match_data`。
- `scripts/ops/n3_live_fotmob_raw_retain.js`
  - 证明当前小批量 retained raw 路线写 `raw_match_data`，并使用 `(match_id, data_version)` 冲突键。
- `scripts/ops/l2_raw_match_data_write.js`
  - 证明另一条 L2 controlled write 路线仍是 exact-scope 工具，不是通用 handoff consumer。
- `database/migrations/V26.5__create_fotmob_raw_match_payloads.sql`
  - 证明仓库里存在长期 raw JSON 存储路线，但它不是当前 retained raw 事实落点。
- `database/migrations/V26.6__create_football_calendar_target_registry.sql`
  - 证明仓库里存在长期 target registry / state machine 设计，但它当前不是正式 current path。
- `docs/_reports/fotmob_retain_more_raw_sample_20260612.md`
  - 证明 `24` 条 retained raw 扩容依赖已有 `matches` 候选，不是自动 L1 -> L2 闭环。
- `docs/_reports/fotmob_retain_50_raw_parser_validation_20260613.md`
  - 证明 `#1502` 的本质是 bounded retained raw 扩容加 parser dry-run，不是正式自动 handoff。
