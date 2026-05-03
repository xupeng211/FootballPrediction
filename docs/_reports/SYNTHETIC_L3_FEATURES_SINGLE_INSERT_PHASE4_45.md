# Phase 4.45 - Synthetic l3_features Single Insert

## Current HEAD

- Branch: `main`
- HEAD: `643e3fa34a7e4c8df81a200136b3dc2e5b950c49`
- HEAD summary: `643e3fa feat(l3): add synthetic L3 preflight gate`
- Git status before report generation: clean

## Backup

- backup file: `data/backups/phase445_pre_synthetic_l3_features_insert_20260504_040526.dump`
- backup size: `71K`

## Write Scope

Human-authorized write scope:

- table: `l3_features`
- operation: one explicit `INSERT`
- match_id: `47_20242025_900002`
- source raw data version: `PHASE4.43_SYNTHETIC`
- feature data version: `PHASE4.45_SYNTHETIC_L3`

This was synthetic L3 data only:

- `synthetic = true`
- `engineering_test_only = true`
- `not_real_external_data = true`
- `not_for_training = true`
- `not_for_production = true`

It is engineering-test-only, not real external data, not production data, and not suitable for real model training.

## Write Before State

DB row counts before insert:

| table                   | rows |
| ----------------------- | ---: |
| matches                 |    2 |
| bookmaker_odds_history  |    2 |
| raw_match_data          |    2 |
| l3_features             |    1 |
| match_features_training |    1 |
| predictions             |    1 |

Target match before insert:

| field                 | value                |
| --------------------- | -------------------- |
| match_id              | `47_20242025_900002` |
| home_team             | `Burgos`             |
| away_team             | `Oviedo`             |
| home_score            | `1`                  |
| away_score            | `0`                  |
| actual_result         | `home_win`           |
| status                | `finished`           |
| is_finished           | `true`               |
| has_raw_match_data    | `true`               |
| has_l3_features       | `false`              |
| has_training_features | `false`              |
| has_predictions       | `false`              |

Synthetic raw status before insert:

| field                  | value                 |
| ---------------------- | --------------------- |
| match_id               | `47_20242025_900002`  |
| data_version           | `PHASE4.43_SYNTHETIC` |
| synthetic              | `true`                |
| engineering_test_only  | `true`                |
| not_real_external_data | `true`                |
| not_for_training       | `true`                |
| not_for_production     | `true`                |

Target L3 row count before insert:

- `target_l3_rows = 0`

## l3_features Schema Confirmation

Read-only schema inspection confirmed:

- `match_id` is the primary key
- `match_id` references `matches(match_id)` with `ON DELETE CASCADE`
- `external_id` exists and is nullable
- JSONB feature columns exist and default to `{}`:
    - `golden_features`
    - `tactical_features`
    - `odds_movement_features`
    - `odds_features`
    - `elo_features`
    - `rolling_features`
    - `efficiency_features`
    - `draw_features`
    - `market_sentiment`
    - `stitch_summary`
- `computed_at`, `created_at`, and `updated_at` are `NOT NULL` and default to `now()`

No schema modification was performed.

## Synthetic L3 Dry-Run Before Insert

Command:

```bash
make data-synthetic-l3-dry-run MATCH_ID=47_20242025_900002
```

Result before insert:

- `match_found = true`
- `is_finished = true`
- `raw_match_data_found = true`
- `synthetic = true`
- `engineering_test_only = true`
- `not_real_external_data = true`
- `not_for_training = true`
- `not_for_production = true`
- `l3_features_exists = false`
- `match_features_training_exists = false`
- `predictions_exists = false`
- `would_insert_l3_features = false`
- `would_update_matches = false`
- `would_trigger_elo = false`
- `can_write_l3_now = false`
- `preview_only = true`
- `no_db_writes`

The dry-run preview included:

- `golden_features`
- `tactical_features`
- `odds_features`
- `elo_features`
- `stitch_summary`

## Insert Result

The authorized insert succeeded.

Returned row:

| field       | value                           |
| ----------- | ------------------------------- |
| match_id    | `47_20242025_900002`            |
| external_id | `900002`                        |
| computed_at | `2026-05-03 20:05:54.909887+00` |
| created_at  | `2026-05-03 20:05:54.909887+00` |
| updated_at  | `2026-05-03 20:05:54.909887+00` |

SQL behavior:

- one explicit `BEGIN`
- one explicit `INSERT INTO l3_features`
- one explicit `COMMIT`
- no `ON CONFLICT DO UPDATE`
- no writes to any other table
- no `smelt`
- no `l3:stitch`
- no ELO recalculation

## Inserted JSONB Feature Summary

Inserted JSONB columns:

- `golden_features`
- `tactical_features`
- `odds_movement_features`
- `odds_features`
- `elo_features`
- `rolling_features`
- `efficiency_features`
- `draw_features`
- `market_sentiment`
- `stitch_summary`

Each inserted JSONB payload contains:

- `synthetic = true`
- `engineering_test_only = true`
- `not_real_external_data = true`
- `not_for_training = true`
- `not_for_production = true`
- `target_match_id = 47_20242025_900002`
- `source_raw_data_version = PHASE4.43_SYNTHETIC`
- `feature_data_version = PHASE4.45_SYNTHETIC_L3`

Feature notes:

- `golden_features` includes the known finished label and score for engineering-chain validation.
- `tactical_features` includes synthetic shape-only stat previews from the synthetic raw fixture.
- `odds_features` and `odds_movement_features` explicitly state no target odds history is linked.
- `elo_features` explicitly states ELO was not computed and must not be fabricated.
- `stitch_summary` marks the write as single-row synthetic L3 only and blocks downstream training/prediction use.

## Write After Verification

Target L3 row:

- `match_id = 47_20242025_900002`
- `external_id = 900002`
- `golden_features` type: `object`
- `tactical_features` type: `object`
- `odds_features` type: `object`
- `elo_features` type: `object`
- `stitch_summary` type: `object`

Metadata verification:

- `golden_synthetic = true`
- `tactical_synthetic = true`
- `odds_synthetic = true`
- `elo_synthetic = true`
- `stitch_synthetic = true`
- `golden_not_for_training = true`
- `stitch_not_for_production = true`
- `golden_engineering_test_only = true`
- `golden_not_real_external_data = true`
- `feature_data_version = PHASE4.45_SYNTHETIC_L3`

Target L3 row count after insert:

- `target_l3_rows = 1`

DB row counts after insert:

| table                   | rows |
| ----------------------- | ---: |
| matches                 |    2 |
| bookmaker_odds_history  |    2 |
| raw_match_data          |    2 |
| l3_features             |    2 |
| match_features_training |    1 |
| predictions             |    1 |

Result:

- `l3_features` increased from `1 -> 2`
- all other tracked tables remained unchanged

## Gate Verification After Insert

`make data-synthetic-l3-dry-run MATCH_ID=47_20242025_900002` reported:

- `match_found = true`
- `raw_match_data_found = true`
- `synthetic = true`
- `l3_features_exists = true`
- `match_features_training_exists = false`
- `predictions_exists = false`
- `would_insert_l3_features = false`
- `would_update_matches = false`
- `would_trigger_elo = false`
- `no_db_writes`

`make data-finished-backfill-dry-run MATCH_ID=47_20242025_900002` reported:

- `has_raw_match_data = true`
- `has_l3_features = true`
- `has_training_features = false`
- `has_predictions = false`
- `match_features_training.blocked_until_l3 = false`
- `predictions.blocked_until_training_features = true`
- `no_db_writes`

Verified blocked gates:

- `make data-synthetic-l3-commit`: blocked
- `make data-synthetic-l3-commit ... CONFIRM_SYNTHETIC_L3=1`: blocked
- `make data-l3-write-commit`: blocked
- `make data-l3-write-commit MATCH_ID=47_20242025_900002 CONFIRM_L3_WRITE=1`: blocked
- `make data-training-commit`: blocked
- `make data-training-commit CONFIRM_TRAINING=1`: blocked

No training, prediction, `smelt`, `l3:stitch`, ELO recalculation, raw ingest, or model artifact loading was executed.

## Risk Notes

- This row is synthetic and engineering-test-only.
- It must not be used as real external data.
- It must not be used for real model training.
- It must not be used for production outputs.
- Future training-feature work must explicitly account for the synthetic provenance before any write.

## Recommended Next Phase

Recommended next step:

```text
Phase 4.46: synthetic l3_features -> match_features_training preflight gate
```

To reduce frequent merges, keep this Phase 4.45 report local for now and submit it together with the Phase 4.46 related gate / report in one themed PR.

## Explicit Non-Execution

This phase did not execute:

- `UPDATE`
- `DELETE`
- `CREATE`
- `ALTER`
- `DROP`
- `TRUNCATE`
- `INSERT` into any table except `l3_features`
- multiple `l3_features` inserts
- `raw_match_data` write
- `match_features_training` write
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
