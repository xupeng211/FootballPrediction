# Phase 4.50 - synthetic chain closure / dataset status report

## 1. 当前分支与 HEAD

- 当前分支：`work/synthetic-prediction-single-insert-phase449`
- 当前 HEAD：`9679b5f15284974f8bd95f1743a36a5e1664c85c`
- HEAD 摘要：`9679b5f feat(prediction): add synthetic prediction preflight gate`
- Phase 4.49 报告已保留：`docs/_reports/SYNTHETIC_PREDICTION_SINGLE_INSERT_PHASE4_49.md`

本阶段未执行 `git reset --hard`、`git clean`、`git pull`、`git fetch --all`，也未删除 Phase 4.49 报告或任何备份文件。

## 2. Phase 4.49 synthetic prediction 写入状态摘要

Phase 4.49 已在人工授权下完成一次单条 `predictions` 写入：

- table：`predictions`
- `match_id = 47_20242025_900002`
- `model_version = P4_SYNTH_BASELINE`
- `predicted_result = home_win`
- `prediction_date = 2026-05-04 18:47:31.694371+00`

该写入的约束与语义如下：

- synthetic baseline prediction
- not real model output
- not from `npm run predict`
- no model artifact loaded
- engineering-test-only
- not for production
- based on synthetic chain

Phase 4.50 未进行任何新的数据库写入。

## 3. 当前 DB 行数

只读核对结果：

| table                     | rows |
| ------------------------- | ---: |
| `matches`                 |    2 |
| `bookmaker_odds_history`  |    2 |
| `raw_match_data`          |    2 |
| `l3_features`             |    2 |
| `match_features_training` |    2 |
| `predictions`             |    2 |

与 Phase 4.49 写后状态一致，本阶段未发生变化。

## 4. target match 全链路状态

目标比赛：

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
| `has_predictions`       | `true`                   |

结论：

- `matches`：存在
- `raw_match_data`：存在，synthetic only
- `l3_features`：存在，synthetic only
- `match_features_training`：存在，synthetic only
- `predictions`：存在，synthetic baseline only

这说明该目标比赛的 synthetic engineering chain 已完成闭环。

## 5. raw_match_data synthetic metadata 摘要

`raw_match_data` 只读查询结果：

| field                    | value                 |
| ------------------------ | --------------------- |
| `match_id`               | `47_20242025_900002`  |
| `data_version`           | `PHASE4.43_SYNTHETIC` |
| `synthetic`              | `true`                |
| `engineering_test_only`  | `true`                |
| `not_real_external_data` | `true`                |
| `not_for_training`       | `true`                |
| `not_for_production`     | `true`                |

结论：

- synthetic provenance 保留
- 该 raw 数据不能被当作真实外部数据
- 该 raw 数据不能进入真实训练或生产预测

## 6. l3_features synthetic metadata 摘要

`l3_features` 只读查询结果：

| field                       | value                    |
| --------------------------- | ------------------------ |
| `golden_synthetic`          | `true`                   |
| `tactical_synthetic`        | `true`                   |
| `odds_synthetic`            | `true`                   |
| `elo_synthetic`             | `true`                   |
| `stitch_synthetic`          | `true`                   |
| `golden_not_for_training`   | `true`                   |
| `stitch_not_for_production` | `true`                   |
| `feature_data_version`      | `PHASE4.45_SYNTHETIC_L3` |

结论：

- L3 五个关键 JSON 组都保留 synthetic 标记
- `not_for_training` / `not_for_production` 标记仍在
- 该层只可用于工程链路验证，不可进入真实训练或 production

## 7. match_features_training synthetic metadata 摘要

`match_features_training` 只读查询结果：

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

结论：

- training feature provenance 保留完整
- 明确禁止下游真实训练
- 明确禁止下游真实预测

## 8. predictions synthetic baseline 摘要

`predictions` 只读查询结果：

| field              | value                           |
| ------------------ | ------------------------------- |
| `id`               | `2`                             |
| `match_id`         | `47_20242025_900002`            |
| `model_version`    | `P4_SYNTH_BASELINE`             |
| `predicted_result` | `home_win`                      |
| `prediction_date`  | `2026-05-04 18:47:31.694371+00` |

说明：

- 该 prediction 是 synthetic baseline
- 该 prediction 不是 real model output
- 该 prediction 不是由 `npm run predict` 产生
- 本阶段未训练模型，未执行真实预测，未加载 model artifact

当前 `predictions` 表没有单独的 JSONB / metadata / notes 字段承载 synthetic 标签，因此此条 prediction 的 synthetic 语义由以下约束共同定义：

1. `model_version = P4_SYNTH_BASELINE`
2. Phase 4.49 人工授权写入范围仅此一条
3. 上游 `raw_match_data -> l3_features -> match_features_training` 已带有完整 synthetic / engineering-test-only / not-for-production provenance
4. Phase 4.49 报告已明确其为 synthetic baseline prediction，而非真实模型输出

## 9. dataset status 摘要

执行：

```bash
make data-dataset-status
```

关键输出摘要：

- `matches = 2`
- `bookmaker_odds_history = 2`
- `raw_match_data = 2`
- `l3_features = 2`
- `match_features_training = 2`
- `predictions = 2`

标签准备度：

- `finished_matches = 1`
- `matches_with_actual_result = 1`
- `matches_with_scores = 1`
- `trainable_label_rows = 1`
- `scheduled_or_unlabeled_rows = 1`

特征准备度：

- `matches_with_raw_match_data = 2`
- `matches_with_l3_features = 2`
- `matches_with_training_features = 2`
- `matches_with_odds_history = 1`
- `full_feature_chain_rows = 1`

风险标记：

- `scheduled_matches_with_training_features = 1`
- `baseline_prediction_rows = 1`
- `prediction_rows_not_training_labels = 2`

训练准备度：

- `trainable = false`
- 原因：当前 DB 只有 `1` 条可训练 label，只有 `1` 条 full feature-chain row，低于真实训练讨论门槛 `200`
- 推荐下一步：`Build a finished-match sample audit before training.`

结论：

- 当前 dev DB 仍不具备真实模型训练条件
- synthetic 链路闭环不等于真实训练 readiness
- 下一步不应继续堆 synthetic 数据，而应转向真实 finished match 数据策略

## 10. dry-run gates 复验结果

### 10.1 finished backfill dry-run

执行：

```bash
make data-finished-backfill-dry-run MATCH_ID=47_20242025_900002
```

确认：

- `has_raw_match_data = true`
- `has_l3_features = true`
- `has_training_features = true`
- `has_predictions = true`
- `no_db_writes`

### 10.2 synthetic L3 dry-run

执行：

```bash
make data-synthetic-l3-dry-run MATCH_ID=47_20242025_900002
```

确认：

- `raw_match_data_found = true`
- `synthetic = true`
- `l3_features_exists = true`
- `match_features_training_exists = true`
- `predictions_exists = true`
- `would_insert_l3_features = false`
- `would_trigger_elo = false`
- `no_db_writes`

### 10.3 synthetic training feature dry-run

执行：

```bash
make data-synthetic-training-feature-dry-run MATCH_ID=47_20242025_900002
```

确认：

- `raw_match_data_found = true`
- `l3_features_found = true`
- `l3_features_synthetic = true`
- `match_features_training_exists = true`
- `predictions_exists = true`
- `would_insert_match_features_training = false`
- `would_train_model = false`
- `would_write_predictions = false`
- `no_db_writes`

### 10.4 synthetic prediction dry-run

执行：

```bash
make data-synthetic-prediction-dry-run MATCH_ID=47_20242025_900002
```

确认：

- `raw_match_data_found = true`
- `l3_features_found = true`
- `match_features_training_found = true`
- `training_features_synthetic = true`
- `predictions_exists = true`
- `target_model_version_exists = true`
- `recommended_model_version = P4_SYNTH_BASELINE`
- `would_write_predictions = false`
- `would_train_model = false`
- `would_load_model_artifact = false`
- `would_execute_real_prediction = false`
- `no_db_writes`

## 11. commit gates blocked 复验结果

已复验以下 commit gates：

- `make data-synthetic-l3-commit`
- `make data-synthetic-l3-commit MATCH_ID=47_20242025_900002 CONFIRM_SYNTHETIC_L3=1`
- `make data-synthetic-training-feature-commit`
- `make data-synthetic-training-feature-commit MATCH_ID=47_20242025_900002 CONFIRM_SYNTHETIC_TRAINING_FEATURE=1`
- `make data-synthetic-prediction-commit`
- `make data-synthetic-prediction-commit MATCH_ID=47_20242025_900002 CONFIRM_SYNTHETIC_PREDICTION=1`
- `make data-training-commit`
- `make data-training-commit CONFIRM_TRAINING=1`
- `make data-prediction-commit`
- `make data-prediction-commit CONFIRM_PREDICTION=1`

结果：

- synthetic L3 commit gate：blocked，Phase 4.44 not wired
- synthetic training feature commit gate：blocked，Phase 4.46 not wired
- synthetic prediction commit gate：blocked，Phase 4.48 not wired
- training commit gate：blocked，Phase 4.29 not wired
- prediction commit gate：blocked，Phase 4.29 not wired

附加确认：

- 不写 DB
- 不训练
- 不执行真实预测
- 不加载 model artifact

## 12. DB 前后统计

Phase 4.50 前后行数一致：

| table                     | rows_before_phase450 | rows_after_phase450 |
| ------------------------- | -------------------: | ------------------: |
| `matches`                 |                    2 |                   2 |
| `bookmaker_odds_history`  |                    2 |                   2 |
| `raw_match_data`          |                    2 |                   2 |
| `l3_features`             |                    2 |                   2 |
| `match_features_training` |                    2 |                   2 |
| `predictions`             |                    2 |                   2 |

结论：本阶段为纯只读审计，没有任何 DB side effect。

## 13. 关键结论

1. `47_20242025_900002` 的 synthetic engineering chain 已闭环：
   `matches -> synthetic raw_match_data -> synthetic l3_features -> synthetic match_features_training -> synthetic baseline prediction`
2. 该链路只用于工程验证。
3. raw / L3 / training / prediction 都是 synthetic 或 synthetic-derived。
4. 该链路不能用于真实训练。
5. 该链路不能用于生产预测。
6. 当前 dev DB 仍不具备真实模型训练条件。
7. synthetic chain closure 不是训练 readiness，也不是 production readiness。

## 14. 下一步建议

- 停止继续堆 synthetic 数据
- 转向真实 finished match 数据源策略
- 设计真实数据 source / license / provenance / schema mapping
- 设计多样本真实 dataset import dry-run
- 在真实训练前先完成 finished-match sample audit 和 kickoff cutoff / leakage 审计

## 15. 明确未执行事项

本阶段明确未执行：

- `INSERT`
- `UPDATE`
- `DELETE`
- `CREATE`
- `ALTER`
- `DROP`
- `TRUNCATE`
- `COPY`
- `\copy`
- `pg_dump`
- DB writes
- `predictions` write
- `match_features_training` write
- `l3_features` write
- `raw_match_data` write
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
- 外网数据源访问
- 真实 harvest / scrape / ingest
- batch backfill
- network dry-run
- bulk harvest
- Docker volume 清理
- `git push --force`
- `git push --mirror`
- `git fetch --all`
- `git pull`
- 删除文件
