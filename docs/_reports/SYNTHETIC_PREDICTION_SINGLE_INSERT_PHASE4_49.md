# Phase 4.49 - synthetic baseline prediction 单条写入（本地草案）

## 1. 当前分支与 HEAD

- 当前分支：`work/synthetic-prediction-single-insert-phase449`
- 当前 HEAD：`9679b5f15284974f8bd95f1743a36a5e1664c85c`
- HEAD 摘要：`9679b5f feat(prediction): add synthetic prediction preflight gate`
- 本阶段未执行 `git pull`、`git fetch --all`、`git push`、`commit`

## 2. 备份

- 备份文件：`data/backups/phase449_pre_synthetic_prediction_insert_20260505_024716.dump`
- 备份大小：`72K`
- 备份方式：`pg_dump --format=custom`
- 结果：备份成功，文件非空

## 3. 写入前 DB 行数

| table                     | rows_before |
| ------------------------- | ----------: |
| `matches`                 |           2 |
| `bookmaker_odds_history`  |           2 |
| `raw_match_data`          |           2 |
| `l3_features`             |           2 |
| `match_features_training` |           2 |
| `predictions`             |           1 |

## 4. target match 状态

| field                   | value                    |
| ----------------------- | ------------------------ |
| `match_id`              | `47_20242025_900002`     |
| `season`                | `2024/2025`              |
| `match_date`            | `2024-08-17 17:30:00+00` |
| `home_team`             | `Burgos`                 |
| `away_team`             | `Oviedo`                 |
| `home_score`            | `1`                      |
| `away_score`            | `0`                      |
| `actual_result`         | `home_win`               |
| `status`                | `finished`               |
| `is_finished`           | `true`                   |
| `has_raw_match_data`    | `true`                   |
| `has_l3_features`       | `true`                   |
| `has_training_features` | `true`                   |
| `has_predictions`       | `false`                  |

## 5. synthetic raw / L3 / training feature 状态

写入前确认：

- `raw_match_data_found = true`
- `l3_features_found = true`
- `match_features_training_found = true`
- `training_features_synthetic = true`
- `training_features_engineering_test_only = true`
- `training_features_not_real_external_data = true`
- `training_features_not_for_training = true`
- `training_features_not_for_production = true`
- `downstream_training_allowed = false`
- `downstream_prediction_allowed = false`
- `target_prediction_rows = 0`
- `target_model_rows = 0`

`match_features_training.adaptive_features` 关键元数据：

| field                           | value                                  |
| ------------------------------- | -------------------------------------- |
| `synthetic`                     | `true`                                 |
| `engineering_test_only`         | `true`                                 |
| `not_real_external_data`        | `true`                                 |
| `not_for_training`              | `true`                                 |
| `not_for_production`            | `true`                                 |
| `feature_data_version`          | `PHASE4.47_SYNTHETIC_TRAINING_FEATURE` |
| `downstream_training_allowed`   | `false`                                |
| `downstream_prediction_allowed` | `false`                                |

## 6. synthetic prediction dry-run 写入前摘要

执行：

```bash
make data-synthetic-prediction-dry-run MATCH_ID=47_20242025_900002
```

关键结果：

- `match_found = true`
- `raw_match_data_found = true`
- `l3_features_found = true`
- `match_features_training_found = true`
- `training_features_synthetic = true`
- `training_features_not_for_training = true`
- `training_features_not_for_production = true`
- `predictions_exists = false`
- `target_model_version_exists = false`
- `recommended_model_version = P4_SYNTH_BASELINE`
- `recommended_model_version_length = 17`
- `model_version_length<=20 = true`
- `would_write_predictions = false`
- `would_train_model = false`
- `would_load_model_artifact = false`
- `would_execute_real_prediction = false`
- `prediction_allowed = false`
- `real_prediction_allowed = false`
- `model_training_allowed = false`
- `preview_only = true`
- `not_real_model_output = true`
- `no_db_writes`

这一步仅为 SELECT-only preflight，没有任何写库动作。

## 7. predictions 表结构与约束摘要

只读检查确认：

- `match_id`：`varchar(50)`，`NOT NULL`
- `model_version`：`varchar(20)`，`NOT NULL`
- `predicted_result`：`varchar(10)`，`NOT NULL`
- `prediction_date`：默认 `CURRENT_TIMESTAMP`
- `id`：`bigint`，默认序列
- 外键：`predictions_match_id_fkey` -> `matches(match_id)`
- 唯一约束：`predictions_match_id_model_version_key (match_id, model_version)`

本次插入可安全使用的最小字段：

- `match_id`
- `model_version`
- `predicted_result`

同时确认：

- 没有额外 `NOT NULL` 且无默认值的列阻塞本次最小插入
- `model_version = P4_SYNTH_BASELINE` 长度为 `17`，符合 `varchar(20)` 约束

## 8. INSERT 结果

执行方式：

- 显式 `BEGIN`
- 单条 `INSERT INTO predictions`
- `RETURNING id, match_id, model_version, predicted_result, prediction_date`
- 显式 `COMMIT`

实际写入结果：

| field              | value                           |
| ------------------ | ------------------------------- |
| `id`               | `2`                             |
| `match_id`         | `47_20242025_900002`            |
| `model_version`    | `P4_SYNTH_BASELINE`             |
| `predicted_result` | `home_win`                      |
| `prediction_date`  | `2026-05-04 18:47:31.694371+00` |

本次只写入 `predictions` 一条记录，没有使用 `ON CONFLICT DO UPDATE`，没有 `UPDATE`，没有 `DELETE`。

说明：

- 这是一条 **synthetic baseline prediction**
- **not real model output**
- **not from `npm run predict`**
- **no model artifact loaded**
- **engineering-test-only**
- **not for production**
- **based on synthetic chain**

由于 `predictions` 表当前没有单独的 JSONB / metadata / notes 字段可承载这些标签，本次 synthetic 语义由以下三部分共同界定：

1. 人工授权范围仅允许写入该单条 baseline prediction
2. `model_version = P4_SYNTH_BASELINE`
3. 上游 `raw_match_data -> l3_features -> match_features_training` 已明确带有 synthetic / engineering-test-only / not-for-production 标记

## 9. prediction row 验证结果

写入后确认：

- 目标 row 查询返回 1 行
- `target_prediction_rows = 1`
- `target_model_rows = 1`
- `model_version = P4_SYNTH_BASELINE`
- `predicted_result = home_win`

## 10. 写入后 DB 行数

| table                     | rows_after |
| ------------------------- | ---------: |
| `matches`                 |          2 |
| `bookmaker_odds_history`  |          2 |
| `raw_match_data`          |          2 |
| `l3_features`             |          2 |
| `match_features_training` |          2 |
| `predictions`             |          2 |

结果：

- `predictions`：`1 -> 2`
- 除 `predictions` 外，其他目标业务表行数均未变化

## 11. gates 验证结果

### 11.1 synthetic prediction dry-run（写后）

执行：

```bash
make data-synthetic-prediction-dry-run MATCH_ID=47_20242025_900002
```

关键结果：

- `match_found = true`
- `raw_match_data_found = true`
- `l3_features_found = true`
- `match_features_training_found = true`
- `predictions_exists = true`
- `target_model_version_exists = true`
- `would_write_predictions = false`
- `would_train_model = false`
- `would_load_model_artifact = false`
- `would_execute_real_prediction = false`
- `no_db_writes`

### 11.2 finished backfill dry-run（写后）

执行：

```bash
make data-finished-backfill-dry-run MATCH_ID=47_20242025_900002
```

关键结果：

- `has_raw_match_data = true`
- `has_l3_features = true`
- `has_training_features = true`
- `has_predictions = true`
- `no_db_writes`

### 11.3 commit gates 仍 blocked

验证命令：

- `make data-synthetic-prediction-commit`
- `make data-synthetic-prediction-commit MATCH_ID=47_20242025_900002 CONFIRM_SYNTHETIC_PREDICTION=1`
- `make data-prediction-write-commit`
- `make data-prediction-write-commit MATCH_ID=47_20242025_900002 CONFIRM_PREDICTION_WRITE=1`
- `make data-prediction-commit`
- `make data-prediction-commit CONFIRM_PREDICTION=1`
- `make data-training-commit`
- `make data-training-commit CONFIRM_TRAINING=1`

结果摘要：

- synthetic prediction commit gate：blocked，Phase 4.48 not wired
- prediction write commit gate：blocked，Phase 4.32 not wired
- prediction commit gate：blocked，Phase 4.29 not wired
- training commit gate：blocked，Phase 4.29 not wired

附加确认：

- 不写 DB
- 不训练
- 不执行真实预测
- 不加载 model artifact

## 12. 明确未执行事项

本阶段明确未执行：

- `UPDATE`
- `DELETE`
- `CREATE`
- `ALTER`
- `DROP`
- `TRUNCATE`
- `INSERT` 到 `predictions` 之外任何表
- 多条 `predictions INSERT`
- `raw_match_data` write
- `l3_features` write
- `match_features_training` write
- `npm run smelt`
- `npm run l3:stitch`
- `npm run elo:recalc`
- model training
- real prediction execution
- model artifact loading
- `npm run train`
- `npm run predict`
- `npm run predict:dry`
- `npm run predict:json`
- `local_dom_ingestor --commit`
- `csv_bulk_loader --commit`
- `raw_match_data_local_ingest --commit`
- external download
- `curl`
- `wget`
- `git clone`
- 外网访问
- 真实 harvest / scrape / ingest
- batch backfill
- network dry-run
- bulk harvest
- Docker volume 清理
- `git pull`
- `git fetch --all`
- `commit`
- `push`
- `PR`
- `merge`

## 13. 下一步建议

建议下一阶段进入：

```text
Phase 4.50：synthetic chain closure / dataset status report
```

为了减少频繁合并，建议 Phase 4.49 报告先不提交，后续与 Phase 4.50 report / gate 一起组成一个主题 PR。
