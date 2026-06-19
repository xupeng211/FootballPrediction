# Smoke Training Dataset Dry-Run
- lifecycle: phase-artifact
- scope: read-only smoke training dataset builder dry-run
- date: 2026-06-19
- branch: `data/smoke-training-dataset-dry-run`

## 结论

这是 **dry-run，不是真实训练**。本次新增 `scripts/ops/smoke_training_dataset_dry_run.js` 和对应单测，只读构造 Ligue 1 `is_training_eligible=true` 样本的 `X/y` 预览，不训练模型，不写 DB，不生成模型文件。

本次保持：
- no DB write / no migration / no schema change
- no live fetch / no raw payload output
- no model training / no model output / no prediction change
- no `matches` / `raw_match_data` 变更

## 数据集结果

| 指标 | 结果 |
| --- | --- |
| `sample_count` | `58` |
| `label_column` | `actual_result` |
| `x_shape` | `[58, 7]` |
| `y_shape` | `[58]` |
| `leakage_columns_detected` | `[]` |

### X 字段列表

1. `league_name`
2. `season`
3. `home_team`
4. `away_team`
5. `match_date`
6. `venue`
7. `referee`

### y 字段

`actual_result`

### 标签分布

| label | count |
| --- | ---: |
| `home_win` | 23 |
| `draw` | 17 |
| `away_win` | 18 |

### 缺失率

| feature | missing_count | total_count | missing_rate |
| --- | ---: | ---: | ---: |
| `league_name` | 0 | 58 | 0 |
| `season` | 0 | 58 | 0 |
| `home_team` | 0 | 58 | 0 |
| `away_team` | 0 | 58 | 0 |
| `match_date` | 0 | 58 | 0 |
| `venue` | 58 | 58 | 1 |
| `referee` | 58 | 58 | 1 |

## 明确排除字段

已从 `X` 明确排除：
- `actual_result`
- `home_score` / `away_score`
- `home_corners` / `away_corners`
- `home_yellow_cards` / `away_yellow_cards`
- `home_red_cards` / `away_red_cards`
- `status` / `is_finished`
- `pipeline_status` / `pipeline_status_reason`
- `source_type` / `evidence_level`
- `is_training_eligible`
- `raw_match_data`
- 其他 governance / provenance / timestamp / identity 字段

## 泄漏检查

本次 `X` 仅由 7 个批准的赛前字段组成，`y` 只来自 `actual_result`。`leakage_columns_detected=[]`，未发现赛后统计字段或 governance 字段误入 `X`。

## 风险与限制

1. `58` 条样本只适合 smoke / integration dataset，不适合正式训练。
2. `venue` 与 `referee` 当前缺失率均为 `100%`，正式训练前需要决定是否保留、填补或删除这两个字段。
3. 本次仅验证只读数据集构造路径，不代表模型质量、泛化能力或正式训练 readiness。

## 验证命令

```text
docker compose -f docker-compose.dev.yml exec -T dev bash -lc 'cd /app/.codex-tmp/smoke-training-dataset-dry-run && node scripts/ops/smoke_training_dataset_dry_run.js --json'
docker compose -f docker-compose.dev.yml exec -T dev bash -lc 'cd /app/.codex-tmp/smoke-training-dataset-dry-run && node --test tests/unit/smoke_training_dataset_dry_run.test.js'
docker compose -f docker-compose.dev.yml exec -T dev bash -lc 'cd /app/.codex-tmp/smoke-training-dataset-dry-run && node /app/node_modules/eslint/bin/eslint.js --no-ignore scripts/ops/smoke_training_dataset_dry_run.js tests/unit/smoke_training_dataset_dry_run.test.js'
git diff --check
```

下一步必须用户明确确认；本报告不构成真实训练、导出、模型产出或任何写操作授权。
