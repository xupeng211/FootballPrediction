# Score Backfill Dry-Run
- lifecycle: phase-artifact
- scope: read-only score/result backfill preflight only
- date: 2026-06-19
- branch: `data/score-backfill-dry-run`

## 结论
这是 dry-run，不是真实写库。本次新增 `scripts/ops/score_backfill_dry_run.js` 和对应单测，只做只读 SQL 扫描、比分/赛果投影预演和报告整理；没有 migration、schema change、DB write、backfill、live fetch、raw payload 输出，也没有修改 `matches` 或 `raw_match_data`。

结论是：`Ligue 1 / 2025/2026` 的 58 条目标行都满足 score backfill write 前置条件。dry-run 结果为 `would_update_count=58`、`would_skip_count=2`，2 条 no-raw 非目标行继续跳过。

## 当前 `matches` 缺失情况
`matches` 中与本次范围直接相关的字段只有 `home_score`、`away_score`、`actual_result`。

| 指标 | 数值 |
| --- | ---: |
| `matches` 总行数 | 60 |
| `Ligue 1 / 2025/2026` 目标行 | 58 |
| 目标行 `home_score` 非空 | 0 |
| 目标行 `away_score` 非空 | 0 |
| 目标行 `actual_result` 非空 | 0 |
| dry-run `would_update_count` | 58 |
| dry-run `would_skip_count` | 2 |

## Dry-Run 规则
来源路径只使用：
1. `raw_data.header.teams[0].score` -> `proposed_home_score`
2. `raw_data.header.teams[1].score` -> `proposed_away_score`
3. `raw_data.header.status.scoreStr` -> 一致性交叉校验

目标 58 条必须同时满足：
- `league_name='Ligue 1'`，`season='2025/2026'`
- `status='finished'`
- `pipeline_status='harvested'`
- `source_type='fotmob_live_fetch'`
- `evidence_level='strong'`
- `raw_match_data.data_version='fotmob_live_v1'`
- 每场恰好 1 条 `fotmob_live_v1`
- `scoreStr` 可用
- `teams[0].score / teams[1].score` 可用
- `scoreStr` 与 `teams score` 一致
- 当前 `home_score / away_score / actual_result` 全空

## `actual_result` 编码选择
本次 dry-run 的写入建议编码固定为 `home_win / draw / away_win`，不使用 `H/D/A` 作为 proposed write value。

理由：
1. 当前库中唯一非空 `matches.actual_result` 样本就是 `home_win`
2. 现有仓库测试与特征代码已经使用 `home_win / draw / away_win`
3. dry-run 目标是预演未来写入值，应优先对齐仓库现有枚举格式

`H/D/A` 只保留为辅助统计，不作为写入建议。

## 预演结果
58 条目标行验证摘要：

| 校验项 | 通过数 |
| --- | ---: |
| `status='finished'` | 58 |
| `pipeline_status='harvested'` | 58 |
| `source_type='fotmob_live_fetch'` | 58 |
| `evidence_level='strong'` | 58 |
| 当前 score/result 三字段全空 | 58 |
| `fotmob_live_v1` 单条 raw | 58 |
| `raw_data_version='fotmob_live_v1'` | 58 |
| `scoreStr` 可用 | 58 |
| `teams score` 可用 | 58 |
| `scoreStr` 与 `teams score` 一致 | 58 |
| proposed score 非空 | 58 |
| proposed `actual_result` 合法 | 58 |

赛果分布：
| 编码 | 数量 |
| --- | ---: |
| `home_win` | 23 |
| `draw` | 17 |
| `away_win` | 18 |

辅助统计：`H=23`、`D=17`、`A=18`。

一致性结论：`scoreStr` 与 `teams[0/1].score` 在 `58/58` 上一致，`mismatch_count=0`。

## 异常 / 跳过
继续跳过的 2 条 no-raw excluded：

| `match_id` | 原因摘要 |
| --- | --- |
| `47_20242025_900002` | 非目标联赛/赛季，`pipeline_status` 非 `harvested`，无 `fotmob_live_v1` raw，且当前已有 synthetic score/result |
| `140_20252026_4837496` | 非目标状态（`scheduled`），非目标联赛，`pipeline_status` 非 `harvested`，无 `fotmob_live_v1` raw |

本次 dry-run 未发现目标 58 条中的 raw 缺失、重复 raw、比分不一致或 proposed result 非法值。

## 是否可进入真实 Score Backfill Write
从只读 preflight 结果看，可以进入单独的真实 score backfill write 授权阶段。

前提仍然成立：
1. 本次只是 dry-run，不是真实写库
2. 真实 write 必须由用户再次明确授权
3. 后续 write 仍需保持 no migration / no schema change / no live fetch / no raw payload output

下一步必须用户明确确认；本报告不构成真实 backfill 执行授权。
