# Score Fields / Result Label Read-Only Audit
- lifecycle: phase-artifact
- scope: read-only audit only
- date: 2026-06-19
- branch: `docs/score-fields-result-label-audit`
## 结论
这是只读审计，不是回填。本次只做了本地只读 SQL、代码入口核对和报告整理；没有 migration、schema change、code change、DB write、backfill、live fetch、raw payload 输出，也没有触发下一阶段执行。
`matches` 表与比分/赛果直接相关的字段只有 `home_score`、`away_score`、`actual_result`。60 条 `matches` 里这 3 个字段都只有 1 条非空；58 条 `Ligue 1 / 2025/2026` 样本是 `58/58` 全空。
58 条法甲比分缺失的原因不是 raw 不存在，也不是比赛未完赛，而是当前链路已经把这 58 场保留为 `fotmob_live_v1` raw、并把 `pipeline_status` 推进到 `harvested`，但没有把 raw 里的最终比分/赛果同步回 `matches`。
## 审计边界
- 只读审计：`SELECT`、只读代码检查、文档报告。
- 未做事项：migration、schema 变更、代码修改、`UPDATE/INSERT/DELETE`、backfill、FotMob live fetch、raw payload 打印/落盘。
- 审计目标：解释 58 条法甲 `home_score / away_score` 为空的原因，并确认 raw 中是否已有可用比分证据。
## `matches` 表现状
直接相关字段：
| 字段 | 类型 |
| --- | --- |
| `home_score` | `integer` |
| `away_score` | `integer` |
| `actual_result` | `character varying` |
未发现其他直接比分字段，如 `home_goals`、`away_goals`、`score`、`result`。
全表 60 条摘要：
| 指标 | 数值 |
| --- | ---: |
| `matches` 总行数 | 60 |
| `home_score` 非空 | 1 |
| `away_score` 非空 | 1 |
| `actual_result` 非空 | 1 |
唯一已填样本：
| `match_id` | 联赛 | 赛季 | `status` | `home_score` | `away_score` | `actual_result` | raw version |
| --- | --- | --- | --- | ---: | ---: | --- | --- |
| `47_20242025_900002` | `Segunda` | `2024/2025` | `finished` | 1 | 0 | `home_win` | `PHASE4.43_SYNTHETIC` |
说明：真实 58 条法甲不是“少量缺口”，而是 `0/58` 已填；当前唯一非空 `actual_result` 来自 synthetic 行，编码为 `home_win`，不是 `H/D/A`。
## 58 条法甲缺失原因
| 指标 | 数值 |
| --- | ---: |
| `matches` 行数 | 58 |
| `status='finished'` | 58 |
| `pipeline_status='harvested'` | 58 |
| `is_training_eligible=false` | 58 |
| `home_score` 非空 | 0 |
| `away_score` 非空 | 0 |
| `actual_result` 非空 | 0 |
判断：
1. 不是比赛状态问题：`finished` 为 `58/58`。
2. 不是 raw 缺失问题：每场都有且只有 1 条 `fotmob_live_v1` retained raw。
3. 不是“少数字段漏写”问题：`harvested` 的 `58/58` 仍三字段全空。
4. 根因是当前链路只完成 raw retain / handoff state 推进，没有把最终比分/赛果投影进 `matches`。
## `raw_match_data` 比分可用性
`raw_match_data` 版本分布：
| `data_version` | 行数 |
| --- | ---: |
| `fotmob_live_v1` | 58 |
| `fotmob_html_hyd_v1` | 8 |
| `fotmob_pageprops_v2` | 8 |
| `PHASE4.23` | 1 |
| `PHASE4.43_SYNTHETIC` | 1 |
58 条法甲与 `fotmob_live_v1` 覆盖：
| 指标 | 数值 |
| --- | ---: |
| 法甲 `match_id` 数 | 58 |
| 对应 `fotmob_live_v1` distinct `match_id` | 58 |
| 缺失 `fotmob_live_v1` raw | 0 |
`fotmob_live_v1` 顶层键摘要：`_meta`、`content`、`general`、`header`、`matchId`。
比分路径摘要（58 条法甲）：
| 路径 | key 存在 | 可解析为最终比分 |
| --- | ---: | ---: |
| `raw_data.header.status.finished` | 58 | 58 为 `true` |
| `raw_data.header.status.scoreStr` | 58 | 58 |
| `raw_data.header.teams[0].score` | 58 | 58 |
| `raw_data.header.teams[1].score` | 58 | 58 |
| `raw_data.general.scoreStr` | 0 | 0 |
| `raw_data.general.homeTeam.score` | 0 | 0 |
| `raw_data.general.awayTeam.score` | 0 | 0 |
一致性：`header.status.scoreStr` 与 `header.teams[*].score` 在 `58/58` 上完全一致，`mismatch_rows = 0`。由 raw 数字比分可推导赛果分布：`H=23`、`D=17`、`A=18`。
结论：58 条法甲的 `fotmob_live_v1` raw 已有稳定、可解析的比分信息；缺的是从 raw 到 `matches` 的回填/投影，不是源数据本身。
## 比分字段候选来源
推荐优先级：
1. `raw_match_data.raw_data.header.teams[0].score` + `header.teams[1].score`
2. `raw_match_data.raw_data.header.status.scoreStr` 作为交叉校验与兜底
不建议作为当前批次主来源：`raw_data.general.scoreStr`、`raw_data.general.homeTeam.score`、`raw_data.general.awayTeam.score`，因为当前法甲样本均为 `0/58`。
## 是否可以进入 score backfill dry-run
结论：从数据前提看，可以进入 **score backfill dry-run** 的 planning / preflight；但本次没有执行 dry-run，也不能直接进入写入阶段。
原因：
- 58/58 已有 `fotmob_live_v1` raw。
- 58/58 raw 已明确 `finished=true`。
- 58/58 都能从 `header.status.scoreStr` 与 `header.teams[*].score` 解析出比分。
- 58/58 目前 `matches` 标签字段全空，具备明确 dry-run 目标集。
## 风险与下一步
风险：
1. `actual_result` 编码语义尚未统一：当前唯一非空值是 `home_win`；基于比分推导通常更适合 `H/D/A`。
2. 现有安全入口 `make data-finished-backfill-dry-run` 是单 `MATCH_ID` preflight，不是 58 场批量 score dry-run。
3. `scripts/ops/matches_labeling_backfill_dry_run.js` 是治理标签只读预演，不等同于比分字段 backfill dry-run。
4. 任何下一步仍需单独用户确认；本报告不构成 DB write、raw write 或 backfill 授权。
下一步必须由用户明确确认，且只能进入新的 **dry-run / preflight**，不能直接写库：
1. 赛果标签编码：`H/D/A` 还是 `home_win/draw/away_win`
2. dry-run 范围：单场先验还是 58 场批量预演
3. dry-run 入口：复用现有单场 preflight，还是另开一个批量只读 score backfill dry-run
