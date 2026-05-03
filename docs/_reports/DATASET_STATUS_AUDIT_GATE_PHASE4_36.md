# Phase 4.36 - Dataset Status / Sample Audit Gate

## Current HEAD

- Base HEAD: `9ddc3ebb4babc27a21463f5ab4583537d13d3bb5`
- Working branch: `feat/dataset-status-audit-gate`

## Current Pipeline Closure

Current local dev DB remains at the minimal local closure established in Phase 4.34B:

- `matches`: 1
- `bookmaker_odds_history`: 2
- `raw_match_data`: 1
- `l3_features`: 1
- `match_features_training`: 1
- `predictions`: 1

The single `predictions` row is still the authorized local manual / baseline record:

- `match_id`: `140_20252026_4837496`
- `model_version`: `P4_LOCAL_BASELINE`
- `predicted_result`: `draw`

It is not a trained model output, did not run `npm run predict`, and did not load any model artifact.

## Dataset Status Script

Added:

- `scripts/ops/dataset_status_audit.js`

Behavior:

- SELECT-only DB audit.
- No DB writes.
- No dataset export.
- No model training.
- No prediction execution.
- No model artifact loading.
- No external network access.

Supported arguments:

- default text output
- `--json`
- `--match-id <id>`

The script reports:

1. Core table row counts.
2. `matches` status / label distribution.
3. Label readiness counts.
4. Feature readiness counts.
5. Leakage risk flags.
6. Training readiness verdict.
7. Explicit non-execution confirmations.

## Makefile Entrypoints

Added:

- `make data-dataset-status`
- `make data-training-dataset-dry-run`

Both entrypoints call:

```bash
docker compose -f docker-compose.dev.yml exec -T dev node scripts/ops/dataset_status_audit.js
```

Added blocked gate:

- `make data-training-dataset-export`

Blocked behavior:

- default: blocked
- `CONFIRM_DATASET_EXPORT=1`: still blocked / not wired in Phase 4.36

## AGENTS.md Update

Updated `AGENTS.md` to document that AI / Codex may run:

- `make data-dataset-status`
- `make data-training-dataset-dry-run`

Only under these constraints:

- SELECT-only DB access
- no training
- no prediction
- no dataset export
- no model artifact loading
- no external network

Also documented:

- real training requires a dataset readiness report first
- single local sample cannot be used as a real training set
- scheduled matches cannot be used as labels
- manual / baseline predictions are not model outputs
- `predictions` must not feed back into training

References added:

- `docs/_reports/MULTISAMPLE_TRAINING_STRATEGY_PHASE4_35.md`
- `docs/_reports/PREDICTION_SINGLE_INSERT_PHASE4_34B.md`

## Dataset Audit Result

Observed DB row counts:

| table                   | rows |
| ----------------------- | ---: |
| matches                 |    1 |
| bookmaker_odds_history  |    2 |
| raw_match_data          |    1 |
| l3_features             |    1 |
| match_features_training |    1 |
| predictions             |    1 |

Observed `matches` status distribution:

| status    | is_finished | actual_result_is_null | score_complete | rows |
| --------- | ----------: | --------------------: | -------------: | ---: |
| scheduled |       false |                  true |          false |    1 |

Label readiness:

- `finished_matches = 0`
- `matches_with_actual_result = 0`
- `matches_with_scores = 0`
- `trainable_label_rows = 0`
- `scheduled_or_unlabeled_rows = 1`

Feature readiness:

- `matches_with_raw_match_data = 1`
- `matches_with_l3_features = 1`
- `matches_with_training_features = 1`
- `matches_with_odds_history = 1`
- `full_feature_chain_rows = 1`

Leakage risk flags:

- `scheduled_matches_with_training_features = 1`
- `baseline_prediction_rows = 1`
- `prediction_rows_not_training_labels = 1`
- `raw_match_data_missing_collected_at = 0`
- `odds_history_missing_collected_at = 0`
- `l3_features_missing_computed_at = 0`
- `training_features_missing_audit_timestamps = 0`

Caveat:

- Feature timing still must be proven against kickoff cutoff before any future real training phase.

## Training Readiness Verdict

Verdict:

- `trainable = false`

Reason:

- current dev DB contains one scheduled local sample
- there is no finished labeled match set
- there are zero trainable label rows
- the current closure proves wiring only, not dataset readiness

Recommended next step:

- build a finished-match sample audit before training

## Validation

Executed:

```bash
make data-dataset-status
make data-training-dataset-dry-run
make data-training-dataset-export || true
make data-training-dataset-export CONFIRM_DATASET_EXPORT=1 || true
```

Results:

- `data-dataset-status`: success
- `data-training-dataset-dry-run`: success
- `data-training-dataset-export`: blocked
- `data-training-dataset-export CONFIRM_DATASET_EXPORT=1`: blocked

DB before and after checks remained unchanged:

| table                   | rows |
| ----------------------- | ---: |
| matches                 |    1 |
| bookmaker_odds_history  |    2 |
| raw_match_data          |    1 |
| l3_features             |    1 |
| match_features_training |    1 |
| predictions             |    1 |

## Next Step Suggestion

Recommended next phase:

```text
Phase 4.37: read-only finished-match sample source audit
```

Alternative:

```text
Phase 4.37: design a safe historical sample acquisition runbook
```

## Explicit Non-Execution

This phase did not execute:

- `INSERT / UPDATE / DELETE / CREATE / ALTER / DROP / TRUNCATE`
- `COPY / \copy`
- DB writes
- model training
- real prediction execution
- model artifact loading
- `npm run train`
- `npm run predict`
- `npm run predict:dry`
- `npm run predict:json`
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
- dataset export
- Docker volume cleanup
