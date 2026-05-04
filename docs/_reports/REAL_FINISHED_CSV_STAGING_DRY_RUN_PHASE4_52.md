# Phase 4.52 - source manifest + real finished CSV staging dry-run gate

## 1. 当前 HEAD

- 当前分支：`feat/real-source-staging-dry-run-gate`
- 起始 HEAD：`4893452985f8b6f28e9aeefdcb88a91d10391421`
- HEAD 摘要：`4893452 docs(data): add real data source strategy`

本阶段目标是实现本地 source manifest + 本地 finished CSV 的 staging dry-run gate，不涉及任何数据库写入、外部下载、训练或预测。

## 2. 当前 DB / dataset status

只读确认结果：

| table                     | rows |
| ------------------------- | ---: |
| `matches`                 |    2 |
| `bookmaker_odds_history`  |    2 |
| `raw_match_data`          |    2 |
| `l3_features`             |    2 |
| `match_features_training` |    2 |
| `predictions`             |    2 |

`make data-dataset-status` 关键结果：

- `trainable = false`
- `finished_matches = 1`
- `trainable_label_rows = 1`
- `full_feature_chain_rows = 1`
- `baseline_prediction_rows = 1`
- `prediction_rows_not_training_labels = 2`

结论：

- 当前只有 1 条真实 finished label
- 当前完整工程闭环仍是 synthetic-derived
- 当前 dev DB 仍不能用于真实训练

## 3. Phase 4.51 strategy 摘要

Phase 4.51 已明确：

- 停止继续堆 synthetic 数据
- 真实数据必须经过 source / license / provenance / schema mapping / leakage 防护
- 下一阶段需要一个只读的 real source staging dry-run gate

Phase 4.52 实现了这一 gate，但仍保持：

- local files only
- SELECT-only DB duplicate check
- no DB writes
- no external downloads
- no training
- no prediction execution

## 4. source manifest path / summary

新增本地 sample manifest：

`tests/fixtures/real_source_manifests/local_sample_history_phase452.json`

对应本地 CSV：

`data/mock/sample_history.csv`

manifest 摘要：

| field             | value                                |
| ----------------- | ------------------------------------ |
| `source_name`     | `local_sample_history`               |
| `source_type`     | `local_staging_csv`                  |
| `source_url`      | `local:data/mock/sample_history.csv` |
| `license_type`    | `local_fixture_for_dry_run_only`     |
| `allowed_use`     | `dry_run_gate_validation_only`       |
| `approval_status` | `dry_run_only`                       |
| `mapping_version` | `PHASE4.52_REAL_CSV_DRY_RUN`         |

说明：

- 这是本地 staging / gate 测试 manifest
- 不是外部真实数据下载
- 不代表真实外部数据 license 已完成

## 5. manifest required fields audit

执行：

```bash
make data-real-source-audit \
  SOURCE_MANIFEST=tests/fixtures/real_source_manifests/local_sample_history_phase452.json
```

关键结果：

- `manifest_found = true`
- `required_fields_complete = true`
- `field_dictionary_present = true`
- `human_approval_note_present = true`
- `approval_status = dry_run_only`
- `dry_run_only = true`
- `can_use_for_db_write = false`
- `no_db_writes`

manifest 必填字段审计通过。

## 6. CSV file integrity audit

执行：

```bash
make data-real-finished-csv-dry-run \
  SOURCE_MANIFEST=tests/fixtures/real_source_manifests/local_sample_history_phase452.json \
  SAMPLE_CSV=data/mock/sample_history.csv
```

关键结果：

- `sample_csv_found = true`
- `sha256_matches_manifest = true`
- `row_count_matches_manifest = true`

CSV 完整性摘要：

| field                | value                                                              |
| -------------------- | ------------------------------------------------------------------ |
| `sample_csv`         | `data/mock/sample_history.csv`                                     |
| `sha256`             | `6cdb9e6a2df94c2c6bd8dc718f26e95fbb431526a54e659ee6fb24b2ae98d5ea` |
| `manifest_row_count` | `4`                                                                |
| `actual_row_count`   | `4`                                                                |

## 7. schema detection / mapping summary

检测到的列：

- `match_id`
- `external_id`
- `league_name`
- `season`
- `home_team`
- `away_team`
- `match_date`
- `status`
- `bookmaker_name`
- `market_type`
- `open_home`
- `open_draw`
- `open_away`
- `close_home`
- `close_draw`
- `close_away`
- `home_score`
- `away_score`

映射检测命中：

- `match_date -> match_date`
- `home_team -> home_team`
- `away_team -> away_team`
- `home_score -> home_score`
- `away_score -> away_score`
- `league -> league_name`
- `season -> season`
- `bookmaker -> bookmaker_name`
- `market_type -> market_type`
- `home_odds -> open_home`
- `draw_odds -> open_draw`
- `away_odds -> open_away`

结果：

- `mapping_columns_missing = []`
- 该本地 sample CSV 能完成 `matches` / labels / odds preview 的基本 schema 检测
- 当前 sample 没有独立 `actual_result` / `FTR` 列，因此 finished label 由比分在 finished 条件下推导

## 8. row classification summary

row classification 结果：

| field                         | value |
| ----------------------------- | ----: |
| `total_rows`                  |     4 |
| `finished_rows`               |     1 |
| `trainable_label_rows`        |     1 |
| `skipped_rows`                |     3 |
| `duplicate_source_rows`       |     1 |
| `invalid_date_rows`           |     1 |
| `missing_team_rows`           |     0 |
| `missing_score_rows`          |     3 |
| `scheduled_or_unlabeled_rows` |     3 |

解释：

- 2 条 `Man Utd vs Liverpool` scheduled rows 共享同一 `match_id`
- 1 条 `Burgos vs Oviedo` finished row 可形成 trainable label preview
- 1 条 `Spurs vs Arsenal` 行带有 `not-a-date`

## 9. candidate preview summary

dry-run 预览中的关键候选：

### Row 2 / Row 3

- `generated_match_id_preview = 47_20242025_900001`
- `status = scheduled`
- `trainable = false`
- `skip_reason = not_finished`
- warnings:
    - `not_finished`
    - `missing_label`
    - `missing_complete_score`

### Row 4

- `generated_match_id_preview = 47_20242025_900002`
- `match_date = 2024-08-17T17:30:00.000Z`
- `league_name = Segunda`
- `season = 2024_2025`
- `home_team = Burgos`
- `away_team = Oviedo`
- `home_score = 1`
- `away_score = 0`
- `actual_result = home_win`
- `label_source = score`
- `data_source = local_sample_history`
- `data_version = PHASE4.52_REAL_CSV_DRY_RUN`
- `would_insert_matches = false`
- `would_insert_odds = false`
- `trainable = true`

### Row 5

- `generated_match_id_preview = 47_20242025_900003`
- `match_date = not-a-date`
- `status = scheduled`
- `trainable = false`
- warnings:
    - `invalid_match_date`
    - `not_finished`
    - `missing_label`
    - `missing_complete_score`

## 10. duplicate / existing match check

SELECT-only duplicate / existing match 结果：

- `existing_matches_count = 1`
- `db_match_exists = true` 的候选为：
    - `47_20242025_900002`

结果说明：

- 本地 dry-run 只做 DB existence preview
- 没有任何 DB write
- 没有自动 dedupe / upsert

## 11. leakage guard result

脚本明确输出：

- `final_score_used_only_as_label = true`
- `no_post_match_features_inserted = true`
- `no_predictions_used = true`
- `no_synthetic_rows_used_for_real_training = true`
- `training_features_require_kickoff_cutoff_before_future_use = true`

结论：

- finished score / `actual_result` 只用于 label preview
- 本阶段没有构造任何赛前 feature 写入
- 没有把 `predictions` 表数据反哺训练
- 没有把 synthetic rows 混入真实训练

## 12. commit gate blocked result

缺确认变量时：

```bash
make data-real-finished-csv-commit
```

结果：

- `BLOCKED: real finished CSV commit requires CONFIRM_REAL_CSV_COMMIT=1 and is not wired in Phase 4.52.`

带确认变量时：

```bash
make data-real-finished-csv-commit \
  SOURCE_MANIFEST=tests/fixtures/real_source_manifests/local_sample_history_phase452.json \
  SAMPLE_CSV=data/mock/sample_history.csv \
  CONFIRM_REAL_CSV_COMMIT=1
```

结果：

- `BLOCKED: real finished CSV commit is not wired in Phase 4.52.`

结论：

- commit gate 在有无确认变量两种路径下都仍然 blocked
- 没有写 DB

## 13. DB 前后统计

Phase 4.52 前后 DB 行数一致：

| table                     | rows_before | rows_after |
| ------------------------- | ----------: | ---------: |
| `matches`                 |           2 |          2 |
| `bookmaker_odds_history`  |           2 |          2 |
| `raw_match_data`          |           2 |          2 |
| `l3_features`             |           2 |          2 |
| `match_features_training` |           2 |          2 |
| `predictions`             |           2 |          2 |

结论：本阶段为纯 dry-run / audit，没有任何 DB side effect。

## 14. 下一步建议

- Phase 4.53：用户提供真实 staging CSV + source manifest 后，运行同一套 dry-run gate
- 或 Phase 4.53：人工授权某个来源下载前的 license / terms 审计
- 仍不建议直接写库
- 仍不训练
- 仍不预测

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
- DB writes
- external download
- `curl`
- `wget`
- `git clone`
- 外部足球数据源访问
- scraping / browser automation
- harvest / ingest
- `local_dom_ingestor --commit`
- `csv_bulk_loader --commit`
- `raw_match_data_local_ingest --commit`
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
- batch backfill
- network dry-run
- bulk harvest
- Docker volume 清理
- `git push --force`
- `git push --mirror`
- `git fetch --all`
- `git pull`
- 删除文件
