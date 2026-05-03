# Phase 4.31 - match_features_training Single Insert

## Current HEAD

- Branch: `main`
- HEAD: `20758c85c4d1ecb09401b348e49cd31e16a8c165`
- Target match: `140_20252026_4837496`

## Backup

- Backup file: `data/backups/phase431_pre_match_features_training_insert_20260503_192543.dump`
- Backup size: `70K`
- Backup command: `pg_dump --format=custom` against the local Docker dev PostgreSQL database

## Pre-insert Row Counts

| table                   | rows |
| ----------------------- | ---: |
| matches                 |    1 |
| bookmaker_odds_history  |    2 |
| raw_match_data          |    1 |
| l3_features             |    1 |
| match_features_training |    0 |
| predictions             |    0 |

## Preconditions

- Target match exists: yes
- Target `l3_features` exists: yes
- Target `match_features_training` rows before insert: 0
- Target `predictions` rows before insert: 0
- `l3_features` JSONB fields were present as objects: `golden_features`, `tactical_features`, `odds_features`, `elo_features`, and `stitch_summary`

Target match:

- `match_id`: `140_20252026_4837496`
- `season`: `2025/2026`
- `match_date`: `2026-05-24 17:00:00+00`
- `home_team`: `Cultural Leonesa`
- `away_team`: `Burgos CF`
- `status`: `scheduled`
- `pipeline_status`: `pending`

## Insert Result

A single authorized local insert was executed into `match_features_training` only.

Returned row:

- `match_id`: `140_20252026_4837496`
- `season`: `2025/2026`
- `match_date`: `2026-05-24 17:00:00+00`
- `home_team`: `Cultural Leonesa`
- `away_team`: `Burgos CF`
- `created_at`: `2026-05-03 11:25:58.079951+00`
- `updated_at`: `2026-05-03 11:25:58.079951+00`

Inserted fields:

- Required fields were sourced from `matches`.
- `adaptive_features` was sourced from the existing `l3_features` JSONB fields.
- Numeric feature columns were left as NULL because they are nullable and were not computed in this phase.
- `feature_version`, `feature_count`, `created_at`, and `updated_at` used database defaults.

## Post-insert Verification

Target row verification:

- `target_training_rows`: 1
- `adaptive_features` type: `object`
- `adaptive_features` contains `source`: yes
- `adaptive_features` contains `trainable`: yes
- `adaptive_features` contains `golden_features`: yes
- `adaptive_features` contains `tactical_features`: yes
- `adaptive_features` contains `odds_features`: yes
- `adaptive_features` contains `elo_features`: yes

## Post-insert Row Counts

| table                   | rows |
| ----------------------- | ---: |
| matches                 |    1 |
| bookmaker_odds_history  |    2 |
| raw_match_data          |    1 |
| l3_features             |    1 |
| match_features_training |    1 |
| predictions             |    0 |

Only `match_features_training` changed, from 0 to 1. `predictions` remained 0.

## Gate Verification

After the insert, `make data-training-feature-dry-run MATCH_ID=140_20252026_4837496` reported:

- `mode`: `dry-run`
- `match_found`: true
- `l3_features_found`: true
- `match_features_training_exists`: true
- `match_features_training_rows`: 1
- `predictions_exists`: false
- `prediction_rows`: 0
- `would_insert_match_features_training`: false
- `would_train_model`: false
- `would_write_predictions`: false
- `no_db_writes`: present

Training / prediction safety gates were revalidated:

- `make data-training-dry-run`: safe preview only
- `make data-training-commit`: blocked
- `make data-training-commit CONFIRM_TRAINING=1`: blocked
- `make data-prediction-dry-run`: safe preview only
- `make data-prediction-commit`: blocked
- `make data-prediction-commit CONFIRM_PREDICTION=1`: blocked

## Risks and Next Steps

- This row is a local manually authorized training feature seed, not a trained model dataset.
- The target match is scheduled and the sample is not trainable by itself.
- Real training still requires a multi-match finished historical dataset, outcome strategy, feature schema policy, model artifact policy, and validation runbook.
- Prediction remains blocked until there is an explicit prediction runbook and authorization.

Recommended next phase:

- `Phase 4.32`: submit this Phase 4.31 report, or design a `predictions` single-write preflight runbook.

## Explicit Non-Execution

This phase did not execute:

- `UPDATE`
- `DELETE`
- `CREATE`
- `ALTER`
- `DROP`
- `TRUNCATE`
- `INSERT` into any table other than `match_features_training`
- duplicate `match_features_training` insert
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
- `git push`
- `git pull`
- `git fetch --all`
- commit
