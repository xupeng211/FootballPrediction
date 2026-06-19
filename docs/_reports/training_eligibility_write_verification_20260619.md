# Training Eligibility Write Verification
- lifecycle: phase-artifact
- scope: authorized real training eligibility write for Ligue 1 2025/2026
- date: 2026-06-19
- branch: `data/training-eligibility-write`
- parent: `data/training-eligibility-after-score-dry-run`

## Authorization

用户已明确授权执行真实 `is_training_eligible=true` write。This report documents the execution, verification, and outcomes.

## Preflight 结果

| 指标 | 预期 | 实际 | 匹配 |
| --- | ---: | ---: | --- |
| `total_matches_scanned` | 60 | 60 | ✓ |
| `target_ligue1_count` | 58 | 58 | ✓ |
| `would_set_true_count` | 58 | 58 | ✓ |
| `would_keep_false_count` | 2 | 2 | ✓ |
| `current_training_eligible_true` | 0 | 0 | ✓ |
| `current_training_eligible_false` | 60 | 60 | ✓ |
| `actual_result` 分布 | H=23/D=17/A=18 | H=23/D=17/A=18 | ✓ |

2 条 no-raw excluded 已确认 keep false：
- `47_20242025_900002` — Segunda 2024/2025, synthetic
- `140_20252026_4837496` — Segunda División 2025/2026, scheduled

Preflight 全部通过，进入真实写入。

## 写入范围

仅写入 `matches` 表的一个字段：
- `matches.is_training_eligible`

目标范围：
- 58 条 Ligue 1 / 2025/2026
- 满足 11 条训练准入条件（详见 dry-run report）
- 写入前 `is_training_eligible=false`

## 写入 SQL 安全边界

使用单条参数化 VALUES-based UPDATE，单事务执行：

```sql
UPDATE matches SET is_training_eligible = true
FROM (VALUES
  ($1::text),
  ...
  ($58::text)
) AS v(match_id)
WHERE matches.match_id = v.match_id
  AND matches.is_training_eligible = false
  AND matches.status = 'finished'
  AND matches.pipeline_status = 'harvested'
  AND matches.source_type = 'fotmob_live_fetch'
  AND matches.evidence_level = 'strong'
  AND matches.is_production_scope = true
  AND matches.is_reconciliation_eligible = true
  AND matches.home_score IS NOT NULL
  AND matches.away_score IS NOT NULL
  AND matches.actual_result IN ('home_win', 'draw', 'away_win')
  AND matches.pipeline_status_reason IS NULL
RETURNING matches.match_id
```

防误写措施：12 条 WHERE 条件逐列验证，确保只更新完全合格的 match。

## 写入结果

- `updated_count`: **58** (与 expected_count=58 完全一致)
- `write_result.success`: **true**

## Post-Write Verification

| 校验项 | 预期 | 实际 | 状态 |
| --- | ---: | ---: | --- |
| `updated_count` | 58 | 58 | ✓ |
| `matches` 总行数 | 60 | 60 | ✓ |
| `raw_match_data` 总行数 | 76 | 76 | ✓ |
| `pipeline_status=harvested` | 58 | 58 | ✓ |
| `pipeline_status=pending` | 2 | 2 | ✓ |
| `is_training_eligible=true` | 58 | 58 | ✓ |
| `is_training_eligible=false` | 2 | 2 | ✓ |
| `actual_result` 分布 | H=23/D=17/A=18 | H=23/D=17/A=18 | ✓ |

## 2 条 no-raw excluded 未写入

| `match_id` | `is_training_eligible` | 被本次写入修改 |
| --- | --- | --- |
| `47_20242025_900002` | false | 否 |
| `140_20252026_4837496` | false | 否 |

## 安全确认

| 项目 | 状态 |
| --- | --- |
| 无 migration | ✓ |
| 无 schema change | ✓ |
| 无 raw_match_data 写入 | ✓ |
| 无 score/result 变更 | ✓ |
| 无 live fetch | ✓ |
| 无 raw payload 输出 | ✓ |
| 无 parser change | ✓ |
| 无 features change | ✓ |
| 无 training change | ✓ |
| 无 prediction change | ✓ |
| 无 pipeline_status 变更 | ✓ |
| 无 governance 其他字段变更 | ✓ |
| 单事务 | ✓ |
| 12 条严格 WHERE 条件 | ✓ |

## 下一步

真实 `is_training_eligible=true` write 已完成。58 条 Ligue 1 法甲现在可用于训练。下一步必须用户确认：
1. 训练数据集构建是否需要额外验证
2. 特征泄漏策略和预测截止时间定义
3. 是否需要启动训练 pipeline
