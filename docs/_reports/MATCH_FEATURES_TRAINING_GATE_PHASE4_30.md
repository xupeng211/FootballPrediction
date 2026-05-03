# Phase 4.30 - match_features_training Local Write Gate

## Current HEAD

- Base HEAD: `82f2d4da7a5eb4998c904c5f1068922143cc08b5`
- Working branch: `feat/training-feature-local-write-gate`
- Target match: `140_20252026_4837496`
- Fixture context: `tests/fixtures/l3/raw_match_data_phase419_sample.json`

## Current DB State

| table                   | rows before gate | rows after gate |
| ----------------------- | ---------------: | --------------: |
| matches                 |                1 |               1 |
| bookmaker_odds_history  |                2 |               2 |
| raw_match_data          |                1 |               1 |
| l3_features             |                1 |               1 |
| match_features_training |                0 |               0 |
| predictions             |                0 |               0 |

Target chain state:

- Target match exists: yes
- Target `l3_features` exists: yes
- Target `match_features_training` rows: 0
- Target `predictions` rows: 0
- Target `l3_features` JSONB types: `golden_features`, `tactical_features`, `odds_features`, `elo_features`, and `stitch_summary` are all objects

## Phase 4.29 Gate Verification

Existing mainline training / prediction gates were revalidated before adding the Phase 4.30 gate:

- `make data-training-dry-run`: safe preview only; no training and no DB writes
- `make data-training-commit`: blocked
- `make data-training-commit CONFIRM_TRAINING=1`: still blocked
- `make data-prediction-dry-run`: safe preview only; no prediction and no DB writes
- `make data-prediction-commit`: blocked
- `make data-prediction-commit CONFIRM_PREDICTION=1`: still blocked

No `npm run train`, `npm run predict`, model artifact generation, prediction write, or DB write was executed.

## match_features_training Structure Summary

Required fields:

- `match_id`
- `season`
- `match_date`
- `home_team`
- `away_team`

Defaults:

- `feature_version`: `'V25.1'`
- `feature_count`: `0`
- `created_at`: `CURRENT_TIMESTAMP`
- `updated_at`: `CURRENT_TIMESTAMP`

Feature fields:

- Nullable numeric fields cover rolling xG, shots on target, possession, team rating, table position, points, Elo gap, fatigue, rest days, incentives, low scoring tendency, and Elo cluster features.
- `adaptive_features` is nullable JSONB and is the natural future target for a compact preview derived from `l3_features`.

Constraints:

- Primary key: `match_id`
- Foreign key: `match_id` references `matches(match_id)` with `ON DELETE CASCADE`

Minimum future insert fields:

- `match_id`
- `season`
- `match_date`
- `home_team`
- `away_team`
- Optional derived values from `l3_features`, most likely stored under `adaptive_features`

## Training / Prediction Risk Audit

Observed high-risk entries remain blocked:

- `npm run train`, `npm run train:fast`, and `npm run train:deep` invoke `scripts/ops/train_model.py`.
- `npm run predict`, `npm run predict:dry`, and `npm run predict:json` invoke `scripts/ops/predict_pipeline.py`.
- Existing `predict:dry` is not treated as a Phase 4.30-safe no-op because it still enters model loading / inference flow.
- `npm run l3:stitch`, `npm run smelt`, and ELO recalculation entries remain outside this phase.

Current data is sufficient to generate a training feature preview: yes.

Current data is sufficient for real model training: no. There is only one scheduled local sample, no finished historical outcome set, and no model artifact policy.

Current data is sufficient for prediction execution: no. Prediction requires an authorized model artifact policy, target window, inference runbook, and explicit write policy.

## Added Gate Behavior

Added script:

```bash
node scripts/ops/match_features_training_local_write_gate.js --match-id <id>
```

Default behavior:

- Runs dry-run mode.
- Performs SELECT-only checks against `matches`, `l3_features`, `match_features_training`, and `predictions`.
- Builds a `match_features_training` preview from the existing `l3_features` row.
- Marks the record as not trainable because a single scheduled match is insufficient for training.
- Confirms no DB writes, training, prediction, model artifact writes, or external network access.

Commit behavior:

- `--commit` exits non-zero immediately.
- Error: `BLOCKED: match_features_training commit is not wired in Phase 4.30.`
- No DB writes are wired behind commit mode.

## Makefile Entrypoints

Added safe dry-run:

```bash
make data-training-feature-dry-run MATCH_ID=<id>
```

Added blocked commit gate:

```bash
make data-training-feature-commit MATCH_ID=<id> CONFIRM_TRAINING_FEATURE=1
```

The commit gate remains blocked / not wired in Phase 4.30, even with `CONFIRM_TRAINING_FEATURE=1`.

## AGENTS.md Update

`AGENTS.md` now permits only the dry-run gate when explicitly authorized:

- `make data-training-feature-dry-run MATCH_ID=<id>`

It explicitly forbids:

- `make data-training-feature-commit`
- `make data-training-feature-commit CONFIRM_TRAINING_FEATURE=1`
- `node scripts/ops/match_features_training_local_write_gate.js --commit`
- `npm run train`
- `npm run predict`
- `npm run model:train`
- `npm run model:predict`
- Any write to `match_features_training` or `predictions`

Related reports:

- `docs/_reports/TRAINING_PREDICTION_PREFLIGHT_PHASE4_29.md`
- `docs/_reports/L3_FEATURES_SINGLE_INSERT_PHASE4_28.md`

## Dry-run Output Summary

Validation command:

```bash
make data-training-feature-dry-run MATCH_ID=140_20252026_4837496
```

Observed semantics:

- `mode`: `dry-run`
- `match_found`: true
- `l3_features_found`: true
- `match_features_training_exists`: false
- `predictions_exists`: false
- `would_insert_match_features_training`: false
- `would_train_model`: false
- `would_write_predictions`: false
- `feature_source`: `l3_features`
- `trainable`: false
- `reason`: `Single scheduled match is insufficient for real model training.`

Non-execution confirmations:

- `no_db_writes`
- `no_insert`
- `no_update`
- `no_delete`
- `no_training`
- `no_prediction`
- `no_model_artifact_write`
- `no_external_network`

## Commit Gate Verification

Validation commands:

```bash
make data-training-feature-commit
make data-training-feature-commit MATCH_ID=140_20252026_4837496 CONFIRM_TRAINING_FEATURE=1
```

Observed results:

- Default commit gate: blocked
- Commit gate with `CONFIRM_TRAINING_FEATURE=1`: still blocked
- No DB writes, training, prediction, or model artifact writes were executed.

## Next Steps

- Future `match_features_training` writes require a separate user authorization phase.
- A backup must be taken before any authorized write.
- Writes should remain restricted to one explicitly scoped `match_id` until a broader runbook exists.
- Real training remains blocked until there is a multi-match finished historical dataset, outcome strategy, feature schema mapping, artifact policy, and validation plan.
- Prediction remains blocked until there is a trusted model artifact manifest, target window policy, no-write preview semantics, and explicit output/write authorization.

## Explicit Non-Execution

This phase did not execute:

- `INSERT / UPDATE / DELETE / CREATE / ALTER / DROP / TRUNCATE`
- `match_features_training` write
- `predictions` write
- model training
- prediction execution
- `npm run train`
- `npm run predict`
- `npm run smelt`
- `npm run l3:stitch`
- ELO recalculation
- `local_dom_ingestor --commit`
- `csv_bulk_loader --commit`
- external network access
- real harvest / scrape / ingest
- batch backfill
- network dry-run
- bulk harvest
- Docker volume cleanup
