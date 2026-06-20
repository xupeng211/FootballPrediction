# Training Pipeline Smoke Dry-Run
- lifecycle: phase-artifact
- scope: read-only training pipeline smoke connectivity dry-run
- date: 2026-06-19
- branch: `ml/training-pipeline-smoke-dry-run`

## 结论

这是 **smoke dry-run，不是正式训练**。本次新增 `scripts/ops/training_pipeline_smoke_dry_run.js` 和对应单测，只读读取 58 条 `is_training_eligible=true` 的 Ligue 1 2025/2026 样本，验证最小训练管道能否完成：

1. 读取 `X/y`
2. 对允许字段做最小编码
3. 固定随机种子切分 train/test
4. 跑通最小 smoke 训练流程

本次保持：
- no DB write / no migration / no schema change
- no live fetch / no raw payload output
- no model artifact commit / no prediction / no betting strategy

## 数据集范围

| 指标 | 结果 |
| --- | --- |
| `sample_count` | `58` |
| `X` 字段 | `league_name`, `season`, `home_team`, `away_team`, `match_date` |
| `y` 字段 | `actual_result` |
| `x_shape` | `[58, 5]` |
| `y_shape` | `[58]` |
| `leakage_columns_detected` | `[]` |

### 标签分布

| label | count |
| --- | ---: |
| `home_win` | 23 |
| `draw` | 17 |
| `away_win` | 18 |

## 为什么排除 `venue` / `referee`

当前 58 条样本中：

| field | missing_count | total_count | missing_rate |
| --- | ---: | ---: | ---: |
| `venue` | 58 | 58 | 1 |
| `referee` | 58 | 58 | 1 |

因此这两个字段本次不进入 `X`。本次 smoke 只验证当前可用的 5 个低风险字段。

## 训练/测试切分

使用固定随机种子 `20260619`，按标签分层切分：

| split | size | `home_win` | `draw` | `away_win` |
| --- | ---: | ---: | ---: | ---: |
| train | 43 | 17 | 13 | 13 |
| test | 15 | 6 | 4 | 5 |

## Smoke 结果

| 指标 | 结果 |
| --- | ---: |
| `class_count` | 3 |
| `baseline_accuracy` | 0.4 |
| `smoke_model_accuracy` | 0.266667 |

本次 smoke model 使用零依赖、最小可解释的类别频率 / Naive Bayes 风格管道，只用于证明训练代码路径能真实完成“读取 -> 编码 -> 切分 -> 拟合 -> 评估”。

## 为什么不评估模型好坏

1. 这不是正式训练，目标只是验证训练管道连通性。
2. 样本只有 58 条，且只来自单联赛单赛季，无法支持稳定的模型评估。
3. 当前 `smoke_model_accuracy` 低于 baseline，进一步说明这轮结果只能用于“管道能跑通”，不能用于判断模型是否可用。
4. `match_date` 只做了最小 calendar token 编码，本身也是 smoke 级实现，不代表正式特征工程方案。

## 风险与限制

1. 58 条样本只适合 smoke / integration 验证，不适合正式训练。
2. 本次没有生成或提交正式模型 artifact。
3. 本次没有做预测，也没有进入任何下注策略逻辑。
4. 任何正式训练、模型产物、导出或评估扩展都必须等待用户再次确认。

## 验证命令

```text
docker compose -f docker-compose.dev.yml exec -T dev bash -lc 'cd /app/.codex-tmp/training-pipeline-smoke-dry-run && node scripts/ops/training_pipeline_smoke_dry_run.js --json'
docker compose -f docker-compose.dev.yml exec -T dev bash -lc 'cd /app/.codex-tmp/training-pipeline-smoke-dry-run && node --test tests/unit/training_pipeline_smoke_dry_run.test.js'
docker compose -f docker-compose.dev.yml exec -T dev bash -lc 'cd /app/.codex-tmp/training-pipeline-smoke-dry-run && node /app/node_modules/eslint/bin/eslint.js --no-ignore scripts/ops/training_pipeline_smoke_dry_run.js tests/unit/training_pipeline_smoke_dry_run.test.js'
git diff --check
```

下一步必须用户确认；本报告不构成正式训练、模型落盘、预测或下注策略执行授权。
