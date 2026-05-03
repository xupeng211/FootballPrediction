# Phase 4.34B - Prediction Single Insert Retry

## Current HEAD

- Branch: `main`
- HEAD: `c80c24d4cebc766f93c5983e92d4d28afd444ba9`
- Target match: `140_20252026_4837496`

## Phase 4.34 Failure Summary

The first Phase 4.34 insert attempt failed before commit because `predictions.model_version` is `character varying(20)`, while the requested value `PHASE4_LOCAL_BASELINE` has length 21.

PostgreSQL rejected the value with:

```text
ERROR: value too long for type character varying(20)
```

No partial write was found after the failure.

## Phase 4.34A Read-only Verification Summary

Phase 4.34A confirmed:

- `predictions_total_rows`: 0
- `target_prediction_rows`: 0
- `failed_model_version_rows`: 0
- `model_version` maximum length: 20
- `P4_LOCAL_BASELINE` length: 17

## Backup

- Backup file: `data/backups/phase434b_pre_prediction_insert_20260503_202001.dump`
- Backup size: `71K`
- Backup command: `pg_dump --format=custom` against the local Docker dev PostgreSQL database

## Pre-insert Row Counts

| table                   | rows |
| ----------------------- | ---: |
| matches                 |    1 |
| bookmaker_odds_history  |    2 |
| raw_match_data          |    1 |
| l3_features             |    1 |
| match_features_training |    1 |
| predictions             |    0 |

## Preconditions

- Target match exists: yes
- Target `match_features_training` exists: yes
- Target `adaptive_features` type: object
- Target `predictions` rows before insert: 0
- Target `P4_LOCAL_BASELINE` rows before insert: 0
- Old failed `PHASE4_LOCAL_BASELINE` rows before insert: 0
- `predictions.model_version` maximum length: 20
- `P4_LOCAL_BASELINE` length: 17

Target match:

- `match_id`: `140_20252026_4837496`
- `season`: `2025/2026`
- `match_date`: `2026-05-24 17:00:00+00`
- `home_team`: `Cultural Leonesa`
- `away_team`: `Burgos CF`
- `status`: `scheduled`
- `pipeline_status`: `pending`

## Insert Result

A single authorized local insert was executed into `predictions` only.

Returned row:

- `id`: 1
- `match_id`: `140_20252026_4837496`
- `model_version`: `P4_LOCAL_BASELINE`
- `predicted_result`: `draw`
- `prediction_date`: `2026-05-03 12:20:18.526835+00`

This is a manual / baseline prediction for local pipeline closure verification only. It is not a trained model output, not produced by `npm run predict`, and no model artifact was loaded.

## Post-insert Verification

Target prediction verification:

- `target_prediction_rows`: 1
- `target_prediction_model_rows` for `P4_LOCAL_BASELINE`: 1
- `failed_model_version_rows` for `PHASE4_LOCAL_BASELINE`: 0

## Post-insert Row Counts

| table                   | rows |
| ----------------------- | ---: |
| matches                 |    1 |
| bookmaker_odds_history  |    2 |
| raw_match_data          |    1 |
| l3_features             |    1 |
| match_features_training |    1 |
| predictions             |    1 |

Only `predictions` changed, from 0 to 1. The other tracked tables remained unchanged.

## Gate Verification

After the insert, `make data-prediction-write-dry-run MATCH_ID=140_20252026_4837496` reported:

- `mode`: `dry-run`
- `match_found`: true
- `match_features_training_found`: true
- `predictions_exists`: true
- `prediction_rows`: 1
- `would_write_predictions`: false
- `would_train_model`: false
- `would_load_model_artifact`: false
- `no_db_writes`: present

Training / prediction safety gates were revalidated:

- `make data-training-dry-run`: safe preview only
- `make data-training-commit`: blocked
- `make data-training-commit CONFIRM_TRAINING=1`: blocked
- `make data-prediction-dry-run`: safe preview only
- `make data-prediction-commit`: blocked
- `make data-prediction-commit CONFIRM_PREDICTION=1`: blocked
- `make data-prediction-write-commit`: blocked
- `make data-prediction-write-commit MATCH_ID=140_20252026_4837496 CONFIRM_PREDICTION_WRITE=1`: blocked

## Risks and Next Steps

- This row is a local manually authorized baseline prediction seed, not a model prediction.
- The target match is scheduled and should not be used as evidence of model quality.
- Real prediction remains blocked until an approved model artifact, inference policy, output policy, and verification runbook exist.
- Real training remains blocked until a multi-match finished historical dataset and artifact policy exist.

Recommended next phase:

- `Phase 4.35`: submit this Phase 4.34B report, or design a multi-sample data strategy / real model training preflight runbook.

## Explicit Non-Execution

This phase did not execute:

- `UPDATE`
- `DELETE`
- `CREATE`
- `ALTER`
- `DROP`
- `TRUNCATE`
- `INSERT` into any table other than `predictions`
- duplicate `predictions` write
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
- Docker volume cleanup
- `git push`
- `git pull`
- `git fetch --all`
- commit
