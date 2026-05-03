# Phase 4.40 - Finished Match Backfill Preflight Gate

## Current HEAD

- Base HEAD: `c15038e0bc850efaedfc7e5619873c3da5a63a30`
- Working branch: `feat/finished-match-backfill-preflight-gate`
- Phase 4.39 report preserved: `docs/_reports/FINISHED_CSV_SINGLE_MATCH_INSERT_PHASE4_39.md`

## Phase 4.39 Finished Match State

Target finished match inserted in Phase 4.39:

| field           | value                    |
| --------------- | ------------------------ |
| match_id        | `47_20242025_900002`     |
| league_name     | `Segunda`                |
| season          | `2024/2025`              |
| home_team       | `Burgos`                 |
| away_team       | `Oviedo`                 |
| home_score      | `1`                      |
| away_score      | `0`                      |
| actual_result   | `home_win`               |
| match_date      | `2024-08-17 17:30:00+00` |
| status          | `finished`               |
| is_finished     | `true`                   |
| data_source     | `local_finished_csv`     |
| data_version    | `PHASE4.39`              |
| pipeline_status | `pending`                |

## DB Row Counts

Row counts before and after this Phase 4.40 preflight work remained unchanged:

| table                   | rows |
| ----------------------- | ---: |
| matches                 |    2 |
| bookmaker_odds_history  |    2 |
| raw_match_data          |    1 |
| l3_features             |    1 |
| match_features_training |    1 |
| predictions             |    1 |

`make data-dataset-status` remains SELECT-only and reports:

- `finished_matches = 1`
- `matches_with_actual_result = 1`
- `matches_with_scores = 1`
- `trainable_label_rows = 1`
- `scheduled_or_unlabeled_rows = 1`
- `full_feature_chain_rows = 1`
- `trainable = false`
- reason: current DB has only `1` trainable labeled row and `1` full feature-chain row; minimum pre-training discussion threshold is `200`

## Target Chain Status

SELECT-only chain check for `47_20242025_900002`:

| field                 | value   |
| --------------------- | ------- |
| match_found           | `true`  |
| is_finished           | `true`  |
| has_actual_result     | `true`  |
| has_score             | `true`  |
| has_raw_match_data    | `false` |
| has_l3_features       | `false` |
| has_training_features | `false` |
| has_predictions       | `false` |

Conclusion:

- the target finished match exists and has a valid label
- the target has no raw/L3/training/prediction downstream records yet
- the next safe step must start with an exact raw fixture strategy

## Local JSON Fixture Audit

Read-only scan covered `15` JSON files under `tests` and `data`, excluding `data/postgres` and `data/backups`.

Candidate-like files were identified only by schema terms such as `score` or `finished`, not by direct target identity:

| file                                                                             | observed identity                                     | assessment                                  |
| -------------------------------------------------------------------------------- | ----------------------------------------------------- | ------------------------------------------- |
| `tests/fixtures/l3/raw_match_data_phase419_sample.json`                          | `140_20252026_4837496`, Cultural Leonesa vs Burgos CF | schema reference only, not Burgos vs Oviedo |
| `tests/fixtures/match_success.json`                                              | `55_20242025_4803413`, Chelsea vs Arsenal             | schema reference only, not target match     |
| `tests/Z_LEGACY_ARCHIVE_PRE_V4.46.8/fixtures/premium_match_sample.json`          | `4813415`, AFC Bournemouth vs Newcastle United        | schema reference only, not target match     |
| `tests/Z_LEGACY_ARCHIVE_PRE_V4.46.8/fixtures/mock_responses/fotmob_success.json` | `4147463`, Manchester City vs Liverpool               | schema reference only, not target match     |

No direct local raw fixture was found for:

- `match_id = 47_20242025_900002`
- `home_team = Burgos`
- `away_team = Oviedo`

Additional observations:

- `tests/Z_LEGACY_ARCHIVE_PRE_V4.46.8/test_data/quality_test_sample_20251130.json` was skipped as large during the shallow audit.
- `tests/fixtures/l1-config-5XOks7/broken.json` is intentionally malformed and produced a JSON parse error.
- No fixture was imported or written to DB.

## Backfill Entrypoint Risk Audit

Existing relevant entrypoints:

| entrypoint                                                         | current behavior                                                                      | write risk                       |
| ------------------------------------------------------------------ | ------------------------------------------------------------------------------------- | -------------------------------- |
| `make data-raw-dry-run SAMPLE_RAW=<path> MATCH_ID=<id>`            | local fixture dry-run via `scripts/ops/raw_match_data_local_ingest.js`                | dry-run only; `--commit` blocked |
| `make data-raw-commit ... CONFIRM_RAW_COMMIT=1`                    | blocked in Makefile                                                                   | not wired                        |
| `make data-l3-write-dry-run SAMPLE_RAW=<path> MATCH_ID=<id>`       | local L3 write preview via `scripts/ops/l3_features_local_write_gate.js`              | dry-run only; `--commit` blocked |
| `make data-l3-write-commit ... CONFIRM_L3_WRITE=1`                 | blocked in Makefile                                                                   | not wired                        |
| `make data-training-feature-dry-run MATCH_ID=<id>`                 | SELECT-only preview via `scripts/ops/match_features_training_local_write_gate.js`     | dry-run only; `--commit` blocked |
| `make data-training-feature-commit ... CONFIRM_TRAINING_FEATURE=1` | blocked in Makefile                                                                   | not wired                        |
| `make data-prediction-write-dry-run MATCH_ID=<id>`                 | SELECT-only prediction write preview via `scripts/ops/prediction_local_write_gate.js` | dry-run only; no model load      |
| `make data-prediction-write-commit ... CONFIRM_PREDICTION_WRITE=1` | blocked in Makefile                                                                   | not wired                        |
| `npm run smelt` / `npm run l3:stitch`                              | real L3 pipeline entrypoints                                                          | prohibited for this phase        |
| `node scripts/ops/batch_historical_backfill.js`                    | batch backfill entrypoint                                                             | prohibited for this phase        |

Assessment:

- raw/L3/training/prediction each already has a narrow dry-run or blocked commit gate.
- none should be used as an implicit orchestration path for this finished match.
- Phase 4.40 adds a preflight gate that only reports the dependency chain and prevents out-of-order writes.

## New Script Behavior

Added:

```text
scripts/ops/finished_match_backfill_preflight.js
```

Supported commands:

```bash
node scripts/ops/finished_match_backfill_preflight.js --match-id 47_20242025_900002
node scripts/ops/finished_match_backfill_preflight.js --match-id 47_20242025_900002 --fixture tests/fixtures/match_success.json
node scripts/ops/finished_match_backfill_preflight.js --match-id 47_20242025_900002 --json
```

Behavior:

- default mode is `preflight`
- performs SELECT-only DB checks
- optionally reads one local JSON fixture
- reports target chain status
- reports fixture direct-match status
- reports ordered backfill plan: `raw_match_data -> l3_features -> match_features_training -> predictions`
- does not call raw ingest, L3 write, training feature write, prediction write, training, prediction, model artifact loading, harvest, scrape, or external network

`--commit` behavior:

```text
BLOCKED: finished match backfill commit is not wired in Phase 4.40.
```

## Makefile Entrypoints

Added:

```text
make data-finished-backfill-dry-run MATCH_ID=<id>
make data-finished-backfill-dry-run MATCH_ID=<id> FIXTURE=<path>
make data-finished-backfill-commit MATCH_ID=<id> CONFIRM_FINISHED_BACKFILL=1  # blocked in Phase 4.40
```

`data-finished-backfill-dry-run` requires `MATCH_ID` and remains read-only.

`data-finished-backfill-commit` is intentionally blocked even when `CONFIRM_FINISHED_BACKFILL=1` is provided.

## AGENTS.md Update

Updated safety rules to allow only:

```text
make data-finished-backfill-dry-run MATCH_ID=<id>
```

Only under these conditions:

- explicit user authorization
- SELECT-only DB checks
- local fixture read-only checks
- no DB writes
- no training
- no prediction
- no external network
- no large export

Added explicit prohibitions for:

- `make data-finished-backfill-commit`
- `make data-finished-backfill-commit CONFIRM_FINISHED_BACKFILL=1`
- `node scripts/ops/finished_match_backfill_preflight.js --commit`
- raw/L3/training/prediction local write commit commands

Added sequencing rule:

```text
raw_match_data -> l3_features -> match_features_training -> predictions
```

and clarified that similar fixtures must not be used as target raw data.

## Dry-Run Validation

Missing argument gate:

```bash
make data-finished-backfill-dry-run || true
```

Result:

- failed as expected
- message: `ERROR: provide MATCH_ID=<id>`

Target preflight:

```bash
make data-finished-backfill-dry-run MATCH_ID=47_20242025_900002
```

Result:

- `mode = preflight`
- `match_found = true`
- `is_finished = true`
- `has_actual_result = true`
- `has_score = true`
- `has_raw_match_data = false`
- `has_l3_features = false`
- `has_training_features = false`
- `has_predictions = false`
- `raw_match_data.required = true`
- `raw_match_data.available_direct_fixture = false`
- `l3_features.blocked_until_raw = true`
- `match_features_training.blocked_until_l3 = true`
- `predictions.blocked_until_training_features = true`
- `predictions.must_not_predict_without_approved_artifact = true`

Non-execution confirmations included:

- `no_db_writes`
- `no_insert`
- `no_update`
- `no_delete`
- `no_raw_ingest`
- `no_l3_write`
- `no_training_feature_write`
- `no_prediction_write`
- `no_training`
- `no_prediction_execution`
- `no_model_artifact_load`
- `no_external_network`

## Optional Fixture Mismatch Validation

Command:

```bash
make data-finished-backfill-dry-run \
  MATCH_ID=47_20242025_900002 \
  FIXTURE=tests/fixtures/match_success.json || true
```

Result:

- fixture was read locally only
- fixture parsed successfully
- fixture identity: `55_20242025_4803413`, Chelsea vs Arsenal
- target identity: `47_20242025_900002`, Burgos vs Oviedo
- `available_direct_fixture = false`
- warning: `fixture_mismatch_target_match`
- no DB writes

## Commit Gate Validation

Commands:

```bash
make data-finished-backfill-commit || true
make data-finished-backfill-commit MATCH_ID=47_20242025_900002 CONFIRM_FINISHED_BACKFILL=1 || true
```

Results:

- both commands were blocked
- commit remains not wired in Phase 4.40
- no DB writes occurred

## Next Step

Recommended Phase 4.41 options:

- prepare a legal local raw fixture runbook for `47_20242025_900002`
- implement raw fixture matching / adapter dry-run before any raw write

Any real write must be separately authorized, preceded by pg_dump, and scoped to one table/stage at a time.

## Explicit Non-Execution

This phase did not execute:

- `INSERT`
- `UPDATE`
- `DELETE`
- `CREATE`
- `ALTER`
- `DROP`
- `TRUNCATE`
- `COPY / \copy`
- DB writes
- raw_match_data write
- l3_features write
- match_features_training write
- predictions write
- raw ingest
- L3 stitch
- smelt
- model training
- real prediction execution
- model artifact loading
- `local_dom_ingestor --commit`
- `csv_bulk_loader --commit`
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
- `git push --force`
- `git push --mirror`
- `git fetch --all`
- `git pull`
- file deletion
