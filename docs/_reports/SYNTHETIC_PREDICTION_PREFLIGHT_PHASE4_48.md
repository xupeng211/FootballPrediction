# Phase 4.48 - Synthetic match_features_training to Prediction Preflight Gate

## Current HEAD

- start branch: `main`
- start HEAD: `20152e8e35c82ea773ed6dec5f02b59a5a80cc5b`
- work branch: `feat/synthetic-prediction-preflight-gate`
- base summary: `20152e8 feat(training): add synthetic training feature preflight gate`

Phase 4.47 local report was preserved:

- `docs/_reports/SYNTHETIC_TRAINING_FEATURE_SINGLE_INSERT_PHASE4_47.md`

No `git reset --hard`, `git clean`, or file deletion was performed.

## Phase 4.47 Synthetic Training Feature Status Summary

The target finished match already has one synthetic `match_features_training` row written under the prior human-authorized Phase 4.47 step:

- `match_id = 47_20242025_900002`
- `feature_data_version = PHASE4.47_SYNTHETIC_TRAINING_FEATURE`
- `synthetic = true`
- `engineering_test_only = true`
- `not_real_external_data = true`
- `not_for_training = true`
- `not_for_production = true`
- `downstream_training_allowed = false`
- `downstream_prediction_allowed = false`

That row remains engineering-only and must not be treated as a real training input or real model-output source.

## Current DB Row Counts

Read-only checks during Phase 4.48 confirmed:

| table                   | rows |
| ----------------------- | ---: |
| matches                 |    2 |
| bookmaker_odds_history  |    2 |
| raw_match_data          |    2 |
| l3_features             |    2 |
| match_features_training |    2 |
| predictions             |    1 |

Phase 4.48 performed no DB writes and the counts remained unchanged before and after validation.

## Target Match Status

Target match:

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
| has_training_features | `true`                   |
| has_predictions       | `false`                  |

## match_features_training Synthetic Metadata Summary

Read-only inspection of `match_features_training` for the target match confirmed:

| field                         | value                                  |
| ----------------------------- | -------------------------------------- |
| match_id                      | `47_20242025_900002`                   |
| synthetic                     | `true`                                 |
| engineering_test_only         | `true`                                 |
| not_real_external_data        | `true`                                 |
| not_for_training              | `true`                                 |
| not_for_production            | `true`                                 |
| feature_data_version          | `PHASE4.47_SYNTHETIC_TRAINING_FEATURE` |
| downstream_training_allowed   | `false`                                |
| downstream_prediction_allowed | `false`                                |

This synthetic provenance is explicit and remains intact.

## predictions Schema Summary

Read-only schema inspection confirmed:

- `match_id` is `NOT NULL` and references `matches(match_id)`
- `model_version` is `character varying(20)` in practice through the unique index and existing application expectations
- `predicted_result` is `NOT NULL`
- unique constraint exists on `(match_id, model_version)`
- current target match has no prediction rows

This is why the synthetic preview recommends `model_version = P4_SYNTH_BASELINE`, which fits within the 20-character limit.

## Existing Prediction / Model Entrypoint Risk Audit

Read-only audit confirmed these remain dangerous or prohibited for this phase:

- `npm run predict`
- `npm run predict:dry`
- `npm run predict:json`
- `npm run train`
- `scripts/ops/predict_pipeline.py`
- `node scripts/ops/prediction_local_write_gate.js --commit`
- `make data-prediction-commit`
- `make data-prediction-write-commit`

Phase 4.48 therefore adds a separate SELECT-only synthetic preview gate instead of calling any real prediction, model artifact, training, or write path.

## New synthetic_prediction_preflight.js Behavior

Added:

```text
scripts/ops/synthetic_prediction_preflight.js
```

Supported usage:

```bash
node scripts/ops/synthetic_prediction_preflight.js --match-id 47_20242025_900002
node scripts/ops/synthetic_prediction_preflight.js --match-id 47_20242025_900002 --json
node scripts/ops/synthetic_prediction_preflight.js --match-id 47_20242025_900002 --commit
```

Behavior:

- only executes guarded `SELECT` queries
- blocks any non-`SELECT` SQL through a forbidden verb check
- uses container DB defaults (`db`, `POSTGRES_*`, `DB_*`)
- emits match status, upstream synthetic-chain status, prediction status, preview payload, gating decision, and non-execution confirmations
- never writes `predictions`
- never trains a model
- never loads a model artifact
- never executes real prediction logic
- never accesses external network

If `--commit` is passed, it immediately fails with:

```text
BLOCKED: synthetic prediction commit is not wired in Phase 4.48.
```

## Makefile Entrypoints

Added safe entrypoints:

```text
make data-synthetic-prediction-dry-run MATCH_ID=<id>
make data-synthetic-prediction-commit MATCH_ID=<id> CONFIRM_SYNTHETIC_PREDICTION=1
```

Behavior:

- dry-run requires `MATCH_ID`
- commit target is blocked without `CONFIRM_SYNTHETIC_PREDICTION=1`
- commit target remains blocked even with `CONFIRM_SYNTHETIC_PREDICTION=1`
- no DB writes are wired behind the commit target in Phase 4.48

## AGENTS.md Update

Added Phase 4.48 synthetic prediction rules:

- AI / Codex may run `make data-synthetic-prediction-dry-run MATCH_ID=<id>` only with explicit user authorization
- input `match_features_training` must already be marked synthetic / engineering-test-only / not-for-training
- no DB writes, no prediction writes, no model training, no prediction execution, no model artifact loading, no external network access
- `make data-synthetic-prediction-commit` and `node scripts/ops/synthetic_prediction_preflight.js --commit` remain prohibited until a future separately authorized phase

Referenced reports:

- `docs/_reports/SYNTHETIC_TRAINING_FEATURE_SINGLE_INSERT_PHASE4_47.md`
- `docs/_reports/SYNTHETIC_TRAINING_FEATURE_PREFLIGHT_PHASE4_46.md`
- `docs/_reports/MULTISAMPLE_TRAINING_STRATEGY_PHASE4_35.md`

## Dry-Run Validation Results

Missing-argument validation:

```bash
make data-synthetic-prediction-dry-run
```

Result:

- failed as expected
- error text: `ERROR: provide MATCH_ID=<id>`

Target dry-run:

```bash
make data-synthetic-prediction-dry-run MATCH_ID=47_20242025_900002
```

Confirmed output semantics:

- `mode = dry-run / preflight`
- `match_found = true`
- `is_finished = true`
- `raw_match_data_found = true`
- `l3_features_found = true`
- `match_features_training_found = true`
- `training_features_synthetic = true`
- `training_features_not_for_training = true`
- `training_features_not_for_production = true`
- `downstream_prediction_allowed = false`
- `predictions_exists = false`
- `target_model_version_exists = false`
- `recommended_model_version = P4_SYNTH_BASELINE`
- `model_version_length<=20 = true`
- `would_write_predictions = false`
- `would_train_model = false`
- `would_load_model_artifact = false`
- `would_execute_real_prediction = false`
- `preview_only = true`
- `synthetic_input = true`
- `not_real_model_output = true`
- `prediction_allowed = false`
- `can_write_prediction_now = false`
- `real_prediction_allowed = false`
- `model_training_allowed = false`
- `no_db_writes`
- `no_prediction_write`
- `no_model_training`
- `no_prediction_execution`
- `no_model_artifact_load`
- `no_external_network`

## Synthetic Prediction Preview Summary

The dry-run emits an engineering-only baseline preview with:

- `target_table = predictions`
- `model_version = P4_SYNTH_BASELINE`
- `predicted_result = home_win`
- `preview_only = true`
- `not_real_model_output = true`
- `based_on_synthetic_chain = true`
- `not_for_production = true`
- note explaining this is not a real model prediction

The preview uses the known `actual_result = home_win` only for engineering visibility and explicitly states that it must not be treated as real model output.

## Commit Gate Blocked Results

Verified blocked behavior:

```bash
make data-synthetic-prediction-commit
make data-synthetic-prediction-commit MATCH_ID=47_20242025_900002 CONFIRM_SYNTHETIC_PREDICTION=1
```

Both commands were blocked:

- first command requires `CONFIRM_SYNTHETIC_PREDICTION=1`
- second command still reports `synthetic prediction commit is not wired in Phase 4.48`

No prediction write, model training, prediction execution, model artifact loading, or DB write occurred.

## Old Gate Rechecks

Rechecked:

```bash
make data-finished-backfill-dry-run MATCH_ID=47_20242025_900002
make data-synthetic-training-feature-dry-run MATCH_ID=47_20242025_900002
```

Confirmed:

- `has_training_features = true`
- `has_predictions = false`
- `match_features_training_exists = true`
- `predictions_exists = false`
- `no_db_writes`

This confirms the upstream synthetic chain remains intact and Phase 4.48 introduced no writes.

## DB Before / After Statistics

Before validation:

| table                   | rows |
| ----------------------- | ---: |
| matches                 |    2 |
| bookmaker_odds_history  |    2 |
| raw_match_data          |    2 |
| l3_features             |    2 |
| match_features_training |    2 |
| predictions             |    1 |

After validation:

| table                   | rows |
| ----------------------- | ---: |
| matches                 |    2 |
| bookmaker_odds_history  |    2 |
| raw_match_data          |    2 |
| l3_features             |    2 |
| match_features_training |    2 |
| predictions             |    1 |

Result:

- DB row counts were unchanged
- no business table write occurred

## Recommended Next Phase

Recommended next step:

```text
Phase 4.49: artificial authorization for one synthetic baseline prediction insert
```

Alternative:

```text
Stop the synthetic chain and move back to a real data-source strategy.
```

## Explicit Non-Execution

Phase 4.48 did not execute:

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
- `predictions` write
- `match_features_training` write
- `l3_features` write
- `raw_match_data` write
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
