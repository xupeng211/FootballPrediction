# Phase 4.29 - Training / Prediction Preflight Gates

## Current HEAD

- Base HEAD: `2f179fd4c9a7733342756d7d540cf4d7ba83b380`
- Working branch: `feat/training-prediction-preflight-gates`
- Target match: `140_20252026_4837496`

## Phase 4.28 Status

Phase 4.28 completed a single authorized local `l3_features` insert:

- `matches`: 1
- `bookmaker_odds_history`: 2
- `raw_match_data`: 1
- `l3_features`: 1
- `match_features_training`: 0
- `predictions`: 0

The Phase 4.28 report is included in this change:

- `docs/_reports/L3_FEATURES_SINGLE_INSERT_PHASE4_28.md`

## Current DB Row Counts

| table                   | rows before gates | rows after gates |
| ----------------------- | ----------------: | ---------------: |
| matches                 |                 1 |                1 |
| bookmaker_odds_history  |                 2 |                2 |
| raw_match_data          |                 1 |                1 |
| l3_features             |                 1 |                1 |
| match_features_training |                 0 |                0 |
| predictions             |                 0 |                0 |

## Target Chain State

- Target match exists: yes
- Target `l3_features` exists: yes
- `golden_features`: object
- `tactical_features`: object
- `odds_features`: object
- `elo_features`: object
- `stitch_summary`: object
- Target `match_features_training` rows: 0
- Target `predictions` rows: 0

## match_features_training Structure Summary

Required fields:

- `match_id`
- `season`
- `match_date`
- `home_team`
- `away_team`

Defaults:

- `feature_version`: `V25.1`
- `feature_count`: `0`
- `created_at`: `CURRENT_TIMESTAMP`
- `updated_at`: `CURRENT_TIMESTAMP`

Feature fields:

- Numeric rolling / table / points / Elo / fatigue / incentive fields are nullable.
- `adaptive_features` is nullable JSONB.

Constraints:

- Primary key: `match_id`
- Foreign key: `match_id` references `matches(match_id)` with `ON DELETE CASCADE`

Training suitability:

- Current local data is not sufficient for training.
- There is only one scheduled target match and zero `match_features_training` rows.
- The inspected training script requires finished matches with scores and enough historical examples. Its default minimum sample count is 100.

## predictions Structure Summary

Required fields:

- `id`
- `match_id`
- `model_version`
- `predicted_result`

Defaults:

- `id`: sequence-backed
- `prediction_date`: `CURRENT_TIMESTAMP`

Prediction fields:

- `confidence_home`, `confidence_draw`, `confidence_away`, `final_confidence`, and `edge` are nullable numeric fields.
- `recommended_bet` and `is_correct` are nullable.

Constraints:

- Primary key: `id`
- Unique key: `(match_id, model_version)`
- Foreign key: `match_id` references `matches(match_id)` with `ON DELETE CASCADE`

Prediction suitability:

- Current data is not sufficient for a trusted prediction execution.
- The target match is scheduled and has `l3_features`, but `elo_features` is intentionally unavailable.
- A trusted model artifact policy, prediction target window, and explicit write policy are still missing.

## Training / Prediction Entry Risk Audit

Observed package scripts:

- `npm run train` runs `scripts/ops/train_model.py`
- `npm run train:fast` runs the same training pipeline with smaller hyperparameters
- `npm run train:deep` runs the same training pipeline with larger hyperparameters
- `npm run predict` runs `scripts/ops/predict_pipeline.py`
- `npm run predict:dry` runs `scripts/ops/predict_pipeline.py --dry-run`
- `npm run predict:json` runs `scripts/ops/predict_pipeline.py --format json`

Training risk:

- `scripts/ops/train_model.py` reads finished historical matches joined to `l3_features`.
- It trains an XGBoost model.
- It saves model and scaler artifacts through `joblib.dump`.
- It is not a safe dry-run gate.
- It depends on a sufficiently large finished historical dataset and model artifact policy.

Prediction risk:

- `scripts/ops/predict_pipeline.py` loads the TITAN model through `get_titan_model`.
- It reads pending matches joined to `l3_features`.
- Its `--dry-run` flag still enters the model loading and inference path.
- It is not a Phase 4.29-safe no-op preview.
- Additional inference modules include code paths capable of inserting into `predictions`; those paths must remain blocked unless separately authorized.

## Added Makefile Gates

Added safe preview placeholders:

```bash
make data-training-dry-run
make data-prediction-dry-run
```

These do not call training or prediction scripts and do not write DB state.

Added blocked commit gates:

```bash
make data-training-commit CONFIRM_TRAINING=1
make data-prediction-commit CONFIRM_PREDICTION=1
```

These remain blocked / not wired in Phase 4.29, even with confirmation variables.

## AGENTS.md Update Summary

The AI / Codex safety rules now explicitly forbid:

- `npm run train`
- `npm run predict`
- `npm run predict:dry`
- `npm run model:train`
- `npm run model:predict`
- Any command that writes `match_features_training`
- Any command that writes `predictions`
- Any training command that loads or generates model artifacts
- `make data-training-commit`
- `make data-training-commit CONFIRM_TRAINING=1`
- `make data-prediction-commit`
- `make data-prediction-commit CONFIRM_PREDICTION=1`

Allowed by default only when they remain no-op safety previews:

- `make data-training-dry-run`
- `make data-prediction-dry-run`

## Gate Verification

Executed safe gate verification:

- `make data-training-dry-run`: safe preview only, no training
- `make data-training-commit`: blocked
- `make data-training-commit CONFIRM_TRAINING=1`: still blocked
- `make data-prediction-dry-run`: safe preview only, no prediction
- `make data-prediction-commit`: blocked
- `make data-prediction-commit CONFIRM_PREDICTION=1`: still blocked

No training, prediction, model artifact generation, or DB writes were executed.

## Next Steps

- A future training phase should define a runbook with dataset scope, minimum sample criteria, feature schema, model artifact paths, validation metrics, and rollback / cleanup policy.
- A future prediction phase should define a runbook with match scope, model artifact manifest, target window, output policy, no-write dry-run semantics, and explicit DB write authorization if needed.
- Keep `npm run train`, `npm run predict`, smelt, stitch, and ELO blocked until a future phase explicitly authorizes them.

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
- `git fetch --all`
- `git pull`
- file deletion
