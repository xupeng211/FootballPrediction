# Phase 4.46 - Synthetic Training Feature Preflight Gate

## Current HEAD

- Base HEAD: `643e3fa34a7e4c8df81a200136b3dc2e5b950c49`
- Working branch: `feat/synthetic-training-feature-preflight-gate`
- Phase 4.45 report preserved: `docs/_reports/SYNTHETIC_L3_FEATURES_SINGLE_INSERT_PHASE4_45.md`

## Phase 4.45 Synthetic l3_features Status

Phase 4.45 had already inserted one human-authorized synthetic `l3_features` row for:

- `match_id = 47_20242025_900002`
- `external_id = 900002`
- `feature_data_version = PHASE4.45_SYNTHETIC_L3`

The stored JSONB payloads remain:

- `synthetic = true`
- `engineering_test_only = true`
- `not_real_external_data = true`
- `not_for_training = true`
- `not_for_production = true`

This row is engineering-test-only synthetic L3 data, not real production feature data, and not suitable for real model training.

## Current DB Row Counts

Row counts before and after Phase 4.46 validation remained unchanged:

| table                   | rows |
| ----------------------- | ---: |
| matches                 |    2 |
| bookmaker_odds_history  |    2 |
| raw_match_data          |    2 |
| l3_features             |    2 |
| match_features_training |    1 |
| predictions             |    1 |

## Target Match Status

Target:

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
| has_l3_features       | `true`               |
| has_training_features | `false`              |
| has_predictions       | `false`              |

Conclusion:

- the target finished match exists
- it has synthetic raw and synthetic L3 rows
- it still has no downstream `match_features_training`
- predictions remain absent

## l3_features Synthetic Metadata Summary

Read-only verification of the target L3 row confirmed:

- `match_id = 47_20242025_900002`
- `external_id = 900002`
- `golden_synthetic = true`
- `tactical_synthetic = true`
- `odds_synthetic = true`
- `elo_synthetic = true`
- `stitch_synthetic = true`
- `golden_engineering_test_only = true`
- `golden_not_real_external_data = true`
- `golden_not_for_training = true`
- `stitch_not_for_production = true`
- `feature_data_version = PHASE4.45_SYNTHETIC_L3`

## match_features_training Schema Summary

Read-only schema inspection confirmed:

- primary key: `PRIMARY KEY (match_id)`
- foreign key: `FOREIGN KEY (match_id) REFERENCES matches(match_id) ON DELETE CASCADE`
- required columns without defaults:
    - `match_id`
    - `season`
    - `match_date`
    - `home_team`
    - `away_team`
- `feature_version` defaults to `V25.1`
- `adaptive_features` is nullable `jsonb`
- `feature_count` defaults to `0`
- `created_at` and `updated_at` default to `CURRENT_TIMESTAMP`

Implication:

- the target match currently has no `match_features_training`
- a future write would still require explicit authorization and a backup phase
- Phase 4.46 intentionally does not perform that write

## Existing Training Feature / Model Entrypoint Risk Audit

Relevant existing entrypoints were audited read-only:

| entrypoint                                                         | current behavior               | write / train risk         |
| ------------------------------------------------------------------ | ------------------------------ | -------------------------- |
| `make data-training-feature-dry-run MATCH_ID=<id>`                 | local training-feature preview | dry-run only               |
| `make data-training-feature-commit ... CONFIRM_TRAINING_FEATURE=1` | blocked                        | not wired                  |
| `make data-training-commit`                                        | blocked placeholder            | no real training allowed   |
| `make data-prediction-commit`                                      | blocked placeholder            | no real prediction allowed |
| `npm run train`                                                    | real model training path       | prohibited                 |
| `npm run predict`                                                  | real model inference path      | prohibited                 |

Decision:

- the new synthetic gate must not call `match_features_training_local_write_gate.js --commit`
- the new synthetic gate must not call `npm run train`
- the new synthetic gate must not call `npm run predict`
- the new synthetic gate must stay SELECT-only and preview-only

## New Script Behavior

Added:

```text
scripts/ops/synthetic_training_feature_preflight.js
```

Supported commands:

```bash
node scripts/ops/synthetic_training_feature_preflight.js --match-id 47_20242025_900002
node scripts/ops/synthetic_training_feature_preflight.js --match-id 47_20242025_900002 --json
node scripts/ops/synthetic_training_feature_preflight.js --match-id 47_20242025_900002 --commit
```

Behavior:

- performs SELECT-only DB checks
- reads the target `matches`, `raw_match_data`, and `l3_features` rows
- checks synthetic L3 provenance flags
- checks existing downstream presence for `match_features_training` and `predictions`
- emits a preview-only `match_features_training` shape
- emits an `adaptive_features` preview derived from synthetic L3 payload groups
- emits `would_insert_match_features_training=false`
- emits `would_train_model=false`
- emits `would_write_predictions=false`
- emits `preview_only=true`
- emits `synthetic_input=true`
- emits `can_write_training_features_now=false`
- emits `real_training_allowed=false`
- emits `prediction_allowed=false`
- does not write `match_features_training`
- does not write `predictions`
- does not train a model
- does not load model artifacts
- does not access external network

`--commit` behavior:

```text
BLOCKED: synthetic training feature commit is not wired in Phase 4.46.
```

## Makefile Entrypoints

Added:

```text
make data-synthetic-training-feature-dry-run MATCH_ID=<id>
make data-synthetic-training-feature-commit MATCH_ID=<id> CONFIRM_SYNTHETIC_TRAINING_FEATURE=1  # blocked in Phase 4.46
```

Behavior:

- `data-synthetic-training-feature-dry-run` requires `MATCH_ID`
- `data-synthetic-training-feature-dry-run` runs `scripts/ops/synthetic_training_feature_preflight.js`
- `data-synthetic-training-feature-commit` is blocked by default
- `data-synthetic-training-feature-commit` remains blocked even with `CONFIRM_SYNTHETIC_TRAINING_FEATURE=1`

`data-help` was updated to list both entries.

## AGENTS.md Update

Added synthetic training feature safety rules:

- `make data-synthetic-training-feature-dry-run MATCH_ID=<id>` is only allowed with explicit user authorization
- input `l3_features` must already be marked synthetic and engineering-test-only
- input `l3_features` must already be marked not-for-training
- the gate must remain SELECT-only
- no DB writes
- no model training
- no prediction execution
- no model artifact loading
- no external network

Added explicit prohibitions for:

- `make data-synthetic-training-feature-commit`
- `make data-synthetic-training-feature-commit CONFIRM_SYNTHETIC_TRAINING_FEATURE=1`
- `node scripts/ops/synthetic_training_feature_preflight.js --commit`
- `node scripts/ops/match_features_training_local_write_gate.js --commit`
- `npm run train`
- `npm run predict`

Added policy statement:

- synthetic training feature preview is engineering-only
- synthetic training feature preview is not for real training
- synthetic training feature preview must not enter production
- real `match_features_training` write still requires separate authorization and `pg_dump`

## Dry-Run Validation

Missing argument gate:

```bash
make data-synthetic-training-feature-dry-run || true
```

Result:

- failed as expected
- message: `ERROR: provide MATCH_ID=<id>`

Target synthetic training feature dry-run:

```bash
make data-synthetic-training-feature-dry-run MATCH_ID=47_20242025_900002
```

Result:

- `mode = dry-run`
- `phase = 4.46`
- `match_found = true`
- `is_finished = true`
- `has_actual_result = true`
- `has_score = true`
- `raw_match_data_found = true`
- `l3_features_found = true`
- `l3_features_synthetic = true`
- `l3_features_not_for_training = true`
- `l3_features_not_for_production = true`
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
- `no_training_feature_write`
- `no_prediction_write`
- `no_model_training`
- `no_prediction_execution`
- `no_external_network`

## adaptive_features Preview Summary

The new preview emits a conservative future-shape payload for `adaptive_features` with:

- `source = PHASE4.45_SYNTHETIC_L3`
- `feature_data_version = PHASE4.46_SYNTHETIC_TRAINING_PREFLIGHT`
- `synthetic = true`
- `engineering_test_only = true`
- `not_real_external_data = true`
- `not_for_training = true`
- `not_for_production = true`
- `target_match_id = 47_20242025_900002`

The preview includes summarized groups for:

- `golden_features`
- `tactical_features`
- `odds_features`
- `elo_features`
- `stitch_summary`

This keeps the preview useful for engineering-shape validation without pretending real training data is available.

## Commit Gate Validation

Validated:

```bash
make data-synthetic-training-feature-commit || true
make data-synthetic-training-feature-commit MATCH_ID=47_20242025_900002 CONFIRM_SYNTHETIC_TRAINING_FEATURE=1 || true
```

Result:

- both commands were blocked
- no DB writes occurred
- no training or prediction path was invoked

## Existing Gate Recheck

`make data-finished-backfill-dry-run MATCH_ID=47_20242025_900002` remained read-only and reported:

- `has_raw_match_data = true`
- `has_l3_features = true`
- `has_training_features = false`
- `has_predictions = false`
- `no_db_writes`

`make data-synthetic-l3-dry-run MATCH_ID=47_20242025_900002` remained read-only and reported:

- `l3_features_exists = true`
- `match_features_training_exists = false`
- `predictions_exists = false`
- `no_db_writes`

## DB Before/After Summary

DB row counts were unchanged across all Phase 4.46 validations:

| table                   | rows before | rows after |
| ----------------------- | ----------: | ---------: |
| matches                 |           2 |          2 |
| bookmaker_odds_history  |           2 |          2 |
| raw_match_data          |           2 |          2 |
| l3_features             |           2 |          2 |
| match_features_training |           1 |          1 |
| predictions             |           1 |          1 |

## Recommended Next Phase

Recommended next step:

```text
Phase 4.47: artificial authorization for one synthetic match_features_training write
```

Alternative:

```text
continue searching for a legal real raw / L3 source before any downstream training-feature write
```

## Explicit Non-Execution

This phase did not execute:

- `INSERT`
- `UPDATE`
- `DELETE`
- `CREATE`
- `ALTER`
- `DROP`
- `TRUNCATE`
- `COPY`
- export
- DB writes
- `match_features_training` write
- `l3_features` write
- `raw_match_data` write
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
- `git push --force`
- `git push --mirror`
- `git fetch --all`
- `git pull`
- file deletion
