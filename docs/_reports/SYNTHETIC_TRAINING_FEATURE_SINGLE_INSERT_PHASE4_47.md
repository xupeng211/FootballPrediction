# Phase 4.47 - Synthetic match_features_training Single Insert

## Current HEAD

- Branch: `main`
- HEAD: `20152e8e35c82ea773ed6dec5f02b59a5a80cc5b`
- HEAD summary: `20152e8 feat(training): add synthetic training feature preflight gate`
- Git status before report generation: clean

## Backup

- backup file: `data/backups/phase447_pre_synthetic_training_features_insert_20260504_114525.dump`
- backup size: `72K`

## Write Scope

Human-authorized write scope:

- table: `match_features_training`
- operation: one explicit `INSERT`
- match_id: `47_20242025_900002`
- source L3 feature data version: `PHASE4.45_SYNTHETIC_L3`
- training feature data version: `PHASE4.47_SYNTHETIC_TRAINING_FEATURE`

This was synthetic training-feature data only:

- `synthetic = true`
- `engineering_test_only = true`
- `not_real_external_data = true`
- `not_for_training = true`
- `not_for_production = true`
- `downstream_training_allowed = false`
- `downstream_prediction_allowed = false`

It is engineering-test-only, not real external data, not production data, and not suitable for real model training or production prediction.

## Write Before State

DB row counts before insert:

| table                   | rows |
| ----------------------- | ---: |
| matches                 |    2 |
| bookmaker_odds_history  |    2 |
| raw_match_data          |    2 |
| l3_features             |    2 |
| match_features_training |    1 |
| predictions             |    1 |

Target match before insert:

| field                 | value                    |
| --------------------- | ------------------------ |
| match_id              | `47_20242025_900002`     |
| season                | `2024/2025`              |
| match_date            | `2024-08-17 17:30:00+00` |
| home_team             | `Burgos`                 |
| away_team             | `Oviedo`                 |
| home_score            | `1`                      |
| away_score            | `0`                      |
| actual_result         | `home_win`               |
| status                | `finished`               |
| is_finished           | `true`                   |
| has_raw_match_data    | `true`                   |
| has_l3_features       | `true`                   |
| has_training_features | `false`                  |
| has_predictions       | `false`                  |

Synthetic L3 status before insert:

| field                     | value                    |
| ------------------------- | ------------------------ |
| match_id                  | `47_20242025_900002`     |
| external_id               | `900002`                 |
| golden_synthetic          | `true`                   |
| tactical_synthetic        | `true`                   |
| odds_synthetic            | `true`                   |
| elo_synthetic             | `true`                   |
| stitch_synthetic          | `true`                   |
| golden_not_for_training   | `true`                   |
| stitch_not_for_production | `true`                   |
| feature_data_version      | `PHASE4.45_SYNTHETIC_L3` |

Target training row count before insert:

- `target_training_rows = 0`

## match_features_training Schema Confirmation

Read-only schema inspection confirmed:

- `match_id` is the primary key
- `match_id` references `matches(match_id)` with `ON DELETE CASCADE`
- required columns without defaults:
    - `match_id`
    - `season`
    - `match_date`
    - `home_team`
    - `away_team`
- `adaptive_features` exists and is nullable `jsonb`
- `feature_version` defaults to `V25.1`
- `feature_count` defaults to `0`
- `created_at` and `updated_at` default to `CURRENT_TIMESTAMP`

No schema modification was performed.

## Synthetic Training Feature Dry-Run Before Insert

Command:

```bash
make data-synthetic-training-feature-dry-run MATCH_ID=47_20242025_900002
```

Result before insert:

- `match_found = true`
- `is_finished = true`
- `raw_match_data_found = true`
- `l3_features_found = true`
- `l3_features_synthetic = true`
- `l3_features_not_for_training = true`
- `match_features_training_exists = false`
- `predictions_exists = false`
- `would_insert_match_features_training = false`
- `would_train_model = false`
- `would_write_predictions = false`
- `preview_only = true`
- `synthetic_input = true`
- `can_write_training_features_now = false`
- `real_training_allowed = false`
- `prediction_allowed = false`
- `no_db_writes`

## Insert Result

The authorized insert succeeded.

Returned row:

| field      | value                           |
| ---------- | ------------------------------- |
| match_id   | `47_20242025_900002`            |
| season     | `2024/2025`                     |
| match_date | `2024-08-17 17:30:00+00`        |
| home_team  | `Burgos`                        |
| away_team  | `Oviedo`                        |
| created_at | `2026-05-04 03:45:42.236299+00` |
| updated_at | `2026-05-04 03:45:42.236299+00` |

SQL behavior:

- one explicit `BEGIN`
- one explicit `INSERT INTO match_features_training`
- one explicit `COMMIT`
- no `ON CONFLICT DO UPDATE`
- no writes to any other table
- no model training
- no prediction execution
- no model artifact loading

## adaptive_features Summary

Inserted `adaptive_features` contains:

- `synthetic = true`
- `engineering_test_only = true`
- `not_real_external_data = true`
- `not_for_training = true`
- `not_for_production = true`
- `target_match_id = 47_20242025_900002`
- `source_l3_feature_data_version = PHASE4.45_SYNTHETIC_L3`
- `feature_data_version = PHASE4.47_SYNTHETIC_TRAINING_FEATURE`
- `downstream_training_allowed = false`
- `downstream_prediction_allowed = false`
- `source = synthetic_l3_features`

Included synthetic feature groups:

- `golden_features`
- `tactical_features`
- `odds_features`
- `elo_features`
- `stitch_summary`

## Write After Verification

Target `match_features_training` row:

- `match_id = 47_20242025_900002`
- `season = 2024/2025`
- `match_date = 2024-08-17 17:30:00+00`
- `home_team = Burgos`
- `away_team = Oviedo`
- `adaptive_features_type = object`
- `synthetic = true`
- `engineering_test_only = true`
- `not_real_external_data = true`
- `not_for_training = true`
- `not_for_production = true`
- `feature_data_version = PHASE4.47_SYNTHETIC_TRAINING_FEATURE`
- `downstream_training_allowed = false`
- `downstream_prediction_allowed = false`

Target training row count after insert:

- `target_training_rows = 1`

DB row counts after insert:

| table                   | rows |
| ----------------------- | ---: |
| matches                 |    2 |
| bookmaker_odds_history  |    2 |
| raw_match_data          |    2 |
| l3_features             |    2 |
| match_features_training |    2 |
| predictions             |    1 |

Result:

- `match_features_training` increased from `1 -> 2`
- all other tracked tables remained unchanged

## Gate Verification After Insert

`make data-synthetic-training-feature-dry-run MATCH_ID=47_20242025_900002` reported:

- `match_found = true`
- `raw_match_data_found = true`
- `l3_features_found = true`
- `l3_features_synthetic = true`
- `match_features_training_exists = true`
- `predictions_exists = false`
- `would_insert_match_features_training = false`
- `would_train_model = false`
- `would_write_predictions = false`
- `no_db_writes`

`make data-finished-backfill-dry-run MATCH_ID=47_20242025_900002` reported:

- `has_raw_match_data = true`
- `has_l3_features = true`
- `has_training_features = true`
- `has_predictions = false`
- `predictions.blocked_until_training_features = false`
- `predictions.must_not_predict_without_approved_artifact = true`
- `no_db_writes`

Verified blocked gates:

- `make data-synthetic-training-feature-commit`: blocked
- `make data-synthetic-training-feature-commit ... CONFIRM_SYNTHETIC_TRAINING_FEATURE=1`: blocked
- `make data-training-feature-commit`: blocked
- `make data-training-feature-commit MATCH_ID=47_20242025_900002 CONFIRM_TRAINING_FEATURE=1`: blocked
- `make data-prediction-commit`: blocked
- `make data-prediction-commit CONFIRM_PREDICTION=1`: blocked

No training, prediction, model artifact loading, `smelt`, `l3:stitch`, ELO recalculation, raw ingest, or external network access was executed.

## Risk Notes

- This row is synthetic and engineering-test-only.
- It must not be used as real external data.
- It must not be used for real model training.
- It must not be used for production outputs.
- `downstream_training_allowed=false` is explicit.
- `downstream_prediction_allowed=false` is explicit.
- Future prediction work must account for synthetic provenance before any preview or write.

## Recommended Next Phase

Recommended next step:

```text
Phase 4.48: synthetic match_features_training -> prediction preflight gate
```

To reduce frequent merges, keep this Phase 4.47 report local for now and submit it together with the Phase 4.48 related gate / report in one themed PR.

## Explicit Non-Execution

This phase did not execute:

- `UPDATE`
- `DELETE`
- `CREATE`
- `ALTER`
- `DROP`
- `TRUNCATE`
- `INSERT` into any table except `match_features_training`
- multiple `match_features_training` inserts
- `raw_match_data` write
- `l3_features` write
- `predictions` write
- `smelt`
- `l3:stitch`
- ELO recalculation
- model training
- real prediction execution
- model artifact loading
- `local_dom_ingestor --commit`
- `csv_bulk_loader --commit`
- `raw_match_data_local_ingest --commit`
- external download
- `curl`
- `wget`
- `git clone`
- external network access
- real harvest / scrape / ingest
- batch backfill
- network dry-run
- bulk harvest
- Docker volume cleanup
- `git push`
- `git pull`
- `git fetch --all`
- commit
