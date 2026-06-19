# Training Eligibility After Score Backfill Dry-Run
- lifecycle: phase-artifact
- scope: read-only training eligibility preflight after score backfill
- date: 2026-06-19
- branch: `data/training-eligibility-after-score-dry-run`

## 结论

这是 **dry-run，不是真实写库**。本次新增 `scripts/ops/training_eligibility_after_score_dry_run.js` 和对应单测，对 score backfill 写入完成后的 `matches` 表做只读扫描，预演哪些 Ligue 1 / 2025/2026 行满足训练准入条件。

结论是：**58 条法甲目标行全部满足训练准入条件**（`would_set_true_count=58`），2 条 no-raw non-target rows 继续 keep false。无 migration、无 schema change、无 DB write、无 backfill、无 live fetch、无 raw payload 输出。

## Score Backfill 后当前状态

| 指标 | 数值 |
| --- | ---: |
| `matches` 总行数 | 60 |
| `Ligue 1 / 2025/2026` 目标行 | 58 |
| 目标行 `home_score` 非空 | 58 |
| 目标行 `away_score` 非空 | 58 |
| 目标行 `actual_result` 合法 | 58 |
| 当前 `is_training_eligible=true` | 0 |
| 当前 `is_training_eligible=false` | 60 |

## 训练准入条件

本次 dry-run 使用 11 条条件逐行评估：

| # | 条件 | 目标行通过 |
| --- | --- | ---: |
| 1 | `status=finished` | 58 |
| 2 | `pipeline_status=harvested` | 58 |
| 3 | `source_type=fotmob_live_fetch` | 58 |
| 4 | `evidence_level=strong` | 58 |
| 5 | `is_production_scope=true` | 58 |
| 6 | `is_reconciliation_eligible=true` | 58 |
| 7 | `home_score IS NOT NULL` | 58 |
| 8 | `away_score IS NOT NULL` | 58 |
| 9 | `actual_result IN (home_win, draw, away_win)` | 58 |
| 10 | `pipeline_status_reason IS NULL` | 58 |
| 11 | `is_training_eligible=false` | 58 |

**58/58 目标行全部通过。**

## Dry-Run 结果

| 指标 | 数值 |
| --- | ---: |
| `total_matches_scanned` | 60 |
| `target_ligue1_count` | 58 |
| `would_set_true_count` | **58** |
| `would_keep_false_count` | 2 |
| `current_training_eligible_true` | 0 |
| `current_training_eligible_false` | 60 |

### actual_result 分布

| 编码 | 数量 |
| --- | ---: |
| `home_win` | 23 |
| `draw` | 17 |
| `away_win` | 18 |

### 2 条 no-raw excluded keep false

| `match_id` | `league_name` | `season` | 原因摘要 |
| --- | --- | --- | --- |
| `47_20242025_900002` | Segunda | 2024/2025 | 非目标 scope, pipeline_status=pending, source_type=synthetic, evidence_level=synthetic_invalid, not production scope, not reconciliation eligible, pipeline_status_reason=no_raw |
| `140_20252026_4837496` | Segunda División | 2025/2026 | 非目标 scope, status=scheduled, pipeline_status=pending, source_type=synthetic, evidence_level=synthetic_invalid, not production scope, not reconciliation eligible, scores null, no actual_result, pipeline_status_reason=no_raw |

### by_reason 分布

| 原因 | 行数 |
| --- | ---: |
| `excluded_non_target_scope` | 2 |
| `pipeline_status_not_harvested` | 2 |
| `source_type_not_fotmob_live_fetch` | 2 |
| `evidence_level_not_strong` | 2 |
| `not_production_scope` | 2 |
| `not_reconciliation_eligible` | 2 |
| `pipeline_status_reason_not_null` | 2 |
| `status_not_finished` | 1 |
| `home_score_null` | 1 |
| `away_score_null` | 1 |
| `actual_result_invalid_or_null` | 1 |

## 风险点

1. `dry_run_only_no_db_write` — 本次不做任何写库
2. `real_training_eligibility_write_requires_explicit_user_authorization` — 真实写库需要用户再次明确授权
3. 所有 58 条 `would_set_true` 行都依赖于特征泄漏策略和预测截止时间的最终定义

## 是否可进入真实 Training Eligibility Write

从只读 preflight 结果看，**可以进入单独的真实 training eligibility write 授权阶段**。

前提仍然成立：
1. 本次只是 dry-run，不是真实写库
2. 真实 write 必须由用户再次明确授权
3. 后续 write 仍需保持 no migration / no schema change / no live fetch / no raw payload output
4. 仅修改 `matches.is_training_eligible` 列，使用与 score backfill write 同等的单事务 + 严格 WHERE 安全措施

下一步必须用户明确确认；本报告不构成真实 backfill 执行授权。
