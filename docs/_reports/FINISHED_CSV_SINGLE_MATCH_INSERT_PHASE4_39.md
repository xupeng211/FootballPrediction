# Phase 4.39 - Single Finished CSV Match Insert

## Current HEAD

- Base HEAD: `c15038e0bc850efaedfc7e5619873c3da5a63a30`
- Working branch: `main`

## Backup

- backup file: `data/backups/phase439_pre_finished_csv_match_insert_20260504_013331.dump`
- backup size: `71K`

## Write Before State

Write target:

- `SAMPLE_CSV = data/mock/sample_history.csv`
- source row: `4`
- target `match_id = 47_20242025_900002`

Dry-run candidate summary before insert:

- `total_rows = 4`
- `finished_rows = 1`
- `trainable_label_rows = 1`
- unique trainable finished candidate:
    - `match_id_preview = 47_20242025_900002`
    - `home_score = 1`
    - `away_score = 0`
    - `actual_result = home_win`
    - `label_source = score`

DB row counts before insert:

| table                   | rows |
| ----------------------- | ---: |
| matches                 |    1 |
| bookmaker_odds_history  |    2 |
| raw_match_data          |    1 |
| l3_features             |    1 |
| match_features_training |    1 |
| predictions             |    1 |

Target existence before insert:

- `target_match_rows = 0`

Dataset baseline before insert:

- `finished_matches = 0`
- `matches_with_actual_result = 0`
- `matches_with_scores = 0`

## Insert Result

Inserted one row into `matches` only.

Inserted values:

- `match_id = 47_20242025_900002`
- `external_id = 900002`
- `league_name = Segunda`
- `season = 2024/2025`
- `home_team = Burgos`
- `away_team = Oviedo`
- `home_score = 1`
- `away_score = 0`
- `actual_result = home_win`
- `match_date = 2024-08-17 17:30:00+00`
- `status = finished`
- `is_finished = true`
- `data_source = local_finished_csv`
- `data_version = PHASE4.39`
- `pipeline_status = pending`

SQL behavior:

- one explicit `INSERT INTO matches`
- one explicit transaction
- no `ON CONFLICT DO UPDATE`
- no insert to any other table

## Write After Verification

Target row after insert:

- exists: yes
- `target_match_rows = 1`

Target row content:

| field           | value                    |
| --------------- | ------------------------ |
| match_id        | `47_20242025_900002`     |
| external_id     | `900002`                 |
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

DB row counts after insert:

| table                   | rows |
| ----------------------- | ---: |
| matches                 |    2 |
| bookmaker_odds_history  |    2 |
| raw_match_data          |    1 |
| l3_features             |    1 |
| match_features_training |    1 |
| predictions             |    1 |

Result:

- `matches` increased from `1 -> 2`
- all other tracked tables remained unchanged

## Dataset Status Improvement

`make data-dataset-status` after insert reported:

- `matches = 2`
- `finished_matches = 1`
- `matches_with_actual_result = 1`
- `matches_with_scores = 1`
- `trainable_label_rows = 1`
- `scheduled_or_unlabeled_rows = 1`

Training readiness remained:

- `trainable = false`

Reason:

- there is now one finished trainable row
- but the sample count is still far below the minimum threshold for real training

## Finished CSV Dry-Run After Insert

`make data-finished-csv-dry-run SAMPLE_CSV=data/mock/sample_history.csv` remained read-only and reported:

- `finished_rows = 1`
- `trainable_label_rows = 1`
- `db_existing_rows = 1`
- target row `47_20242025_900002` now shows `db_match_exists = true`

Warnings remained unchanged:

- duplicate `47_20242025_900001`
- scheduled unlabeled rows
- invalid date on row 5

## Gate Verification

Verified blocked / safe gates:

- `make data-finished-csv-commit`: blocked
- `make data-finished-csv-commit ... CONFIRM_FINISHED_CSV_COMMIT=1`: blocked
- `make data-training-dataset-export`: blocked
- `make data-training-dataset-export CONFIRM_DATASET_EXPORT=1`: blocked
- `make data-training-dry-run`: safe preview only
- `make data-training-commit`: blocked
- `make data-training-commit CONFIRM_TRAINING=1`: blocked

## Risk Notes

- The inserted finished match does not yet have matching local `raw_match_data`, `l3_features`, or `match_features_training` rows.
- The row is intentionally marked `pipeline_status = pending` to avoid implying that downstream feature stages already ran.
- Future phases should keep write scope narrow and avoid bulk import before a dedicated runbook exists.

## Recommended Next Phase

Recommended next phase:

```text
Phase 4.40: submit Phase 4.39 report, or design raw/l3/training feature backfill dry-run for the new finished match
```

## Explicit Non-Execution

This phase did not execute:

- `UPDATE`
- `DELETE`
- `CREATE`
- `ALTER`
- `DROP`
- `TRUNCATE`
- `INSERT` into any table except `matches`
- multiple `matches` inserts
- `csv_bulk_loader --commit`
- `local_dom_ingestor --commit`
- `COPY / \copy`
- external download
- `curl`
- `wget`
- `git clone`
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
