# Phase 4.43 - Synthetic Raw Match Data Single Insert

## Current HEAD

- Branch: `main`
- HEAD: `80ecb30266e56644d66a4170178d4fb434cbd61f`
- HEAD summary: `80ecb30 test(data): add synthetic raw fixture for finished match`
- Git status before report generation: clean

## Backup

- backup file: `data/backups/phase443_pre_synthetic_raw_match_data_insert_20260504_025248.dump`
- backup size: `71K`

## Write Scope

Human-authorized write scope:

- table: `raw_match_data`
- operation: one explicit `INSERT`
- match_id: `47_20242025_900002`
- source fixture: `tests/fixtures/synthetic/raw_match_data_47_20242025_900002_phase442.json`
- data_version: `PHASE4.43_SYNTHETIC`

This was synthetic raw data only:

- `synthetic = true`
- `engineering_test_only = true`
- `not_real_external_data = true`
- `not_for_training = true`
- `not_for_production = true`

It is not FotMob data, not OddsPortal data, not production data, and not suitable for real model training.

## Write Before State

DB row counts before insert:

| table                   | rows |
| ----------------------- | ---: |
| matches                 |    2 |
| bookmaker_odds_history  |    2 |
| raw_match_data          |    1 |
| l3_features             |    1 |
| match_features_training |    1 |
| predictions             |    1 |

Target match before insert:

| field                 | value                    |
| --------------------- | ------------------------ |
| match_id              | `47_20242025_900002`     |
| league_name           | `Segunda`                |
| season                | `2024/2025`              |
| home_team             | `Burgos`                 |
| away_team             | `Oviedo`                 |
| home_score            | `1`                      |
| away_score            | `0`                      |
| actual_result         | `home_win`               |
| match_date            | `2024-08-17 17:30:00+00` |
| status                | `finished`               |
| is_finished           | `true`                   |
| has_raw_match_data    | `false`                  |
| has_l3_features       | `false`                  |
| has_training_features | `false`                  |
| has_predictions       | `false`                  |

Target raw row count before insert:

- `target_raw_rows = 0`

## Fixture Validation

Fixture:

```text
tests/fixtures/synthetic/raw_match_data_47_20242025_900002_phase442.json
```

Adapter dry-run without `ALLOW_SYNTHETIC=1`:

- `direct_fixture_match = true`
- `synthetic = true`
- `fixture_can_be_used_for_target = false`
- `preview_only = true`
- `would_insert_raw_match_data = false`
- warning: `synthetic_fixture_requires_explicit_ALLOW_SYNTHETIC_1`
- warning: `synthetic_fixture_not_for_training`
- no DB writes

Adapter dry-run with `ALLOW_SYNTHETIC=1`:

- `match_found = true`
- `fixture.exists = true`
- `direct_fixture_match = true`
- `synthetic = true`
- `engineering_test_only = true`
- `not_real_external_data = true`
- `not_for_training = true`
- `not_for_production = true`
- `preview_only = true`
- `synthetic_preview_allowed = true`
- `would_insert_raw_match_data = false`
- no DB writes

## raw_match_data Schema Confirmation

Confirmed before insert:

- `raw_data` is `jsonb NOT NULL`
- raw data must be non-empty
- raw data must contain `matchId`, `general`, or `header`
- `match_id` is unique in `raw_match_data`
- `match_id` references `matches(match_id)`

The synthetic fixture contains:

- `matchId`
- `general`
- `header`
- `content`
- synthetic metadata

## Insert Result

The authorized insert succeeded.

Returned row:

| field        | value                                                              |
| ------------ | ------------------------------------------------------------------ |
| id           | `2`                                                                |
| match_id     | `47_20242025_900002`                                               |
| external_id  | `900002`                                                           |
| data_version | `PHASE4.43_SYNTHETIC`                                              |
| data_hash    | `f679933712fd826e8f8785a4866e8f3d841b9a1653caea3bb733c8efbde5921e` |
| collected_at | `2026-05-03 18:53:04.863557+00`                                    |

SQL behavior:

- one explicit `BEGIN`
- one explicit `INSERT INTO raw_match_data`
- one explicit `COMMIT`
- no `ON CONFLICT DO UPDATE`
- no writes to any other table

## Write After Verification

Target raw row verification:

- `target_raw_rows = 1`
- `synthetic = true`
- `engineering_test_only = true`
- `not_real_external_data = true`
- `not_for_training = true`
- `not_for_production = true`

Raw data structure verification:

- `has_match_id = true`
- `has_general = true`
- `has_header = true`
- `has_content = true`
- `league_name = Segunda`
- `home_team = Burgos`
- `away_team = Oviedo`

DB row counts after insert:

| table                   | rows |
| ----------------------- | ---: |
| matches                 |    2 |
| bookmaker_odds_history  |    2 |
| raw_match_data          |    2 |
| l3_features             |    1 |
| match_features_training |    1 |
| predictions             |    1 |

Result:

- `raw_match_data` increased from `1 -> 2`
- all other tracked tables remained unchanged

## Backfill Preflight After Insert

`make data-finished-backfill-dry-run MATCH_ID=47_20242025_900002` reported:

- `match_found = true`
- `is_finished = true`
- `has_actual_result = true`
- `has_score = true`
- `has_raw_match_data = true`
- `has_l3_features = false`
- `has_training_features = false`
- `has_predictions = false`
- `raw_match_data.required = false`
- `l3_features.blocked_until_raw = false`
- `match_features_training.blocked_until_l3 = true`
- `predictions.blocked_until_training_features = true`

Next downstream stage remains blocked until a separate L3 dry-run / write preflight is authorized.

## Raw Fixture Dry-Run After Insert

`make data-raw-fixture-dry-run MATCH_ID=47_20242025_900002 FIXTURE=tests/fixtures/synthetic/raw_match_data_47_20242025_900002_phase442.json ALLOW_SYNTHETIC=1` remained read-only and reported:

- `direct_fixture_match = true`
- `synthetic = true`
- `preview_only = true`
- `synthetic_preview_allowed = true`
- `would_insert_raw_match_data = false`
- `no_db_writes`

## Gate Verification

Verified blocked gates:

- `make data-raw-fixture-commit`: blocked
- `make data-raw-fixture-commit ... CONFIRM_RAW_FIXTURE_COMMIT=1`: blocked
- `make data-finished-backfill-commit`: blocked
- `make data-finished-backfill-commit ... CONFIRM_FINISHED_BACKFILL=1`: blocked
- `make data-training-commit`: blocked
- `make data-training-commit CONFIRM_TRAINING=1`: blocked

No training, prediction, L3 stitch, smelt, raw ingest batch, or model artifact loading was executed.

## Risk Notes

- This row is synthetic and engineering-test-only.
- It must not be used as real external data.
- It must not be used for real model training.
- It must not be used for production outputs.
- Future L3 work must explicitly account for the synthetic provenance before any feature write.

## Recommended Next Phase

Recommended next step:

```text
Phase 4.44: synthetic raw -> L3 dry-run / l3_features write preflight
```

To reduce frequent merges, keep this Phase 4.43 report local for now and submit it together with the Phase 4.44 related gate / report in one themed PR.

## Explicit Non-Execution

This phase did not execute:

- `UPDATE`
- `DELETE`
- `CREATE`
- `ALTER`
- `DROP`
- `TRUNCATE`
- `INSERT` into any table except `raw_match_data`
- multiple `raw_match_data` inserts
- `l3_features` write
- `match_features_training` write
- `predictions` write
- raw ingest batch
- L3 stitch
- smelt
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
