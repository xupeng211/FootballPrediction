# Phase 4.38 - Local Finished CSV Sample Import Dry-Run Gate

## Current HEAD

- Base HEAD: `d3f1f89f68907bfc2fd63ef3fda8a411d2c21e56`
- Working branch: `feat/finished-csv-dry-run-gate`

## Current DB / Dataset Status

Current dev DB remained unchanged before and after Phase 4.38 validation:

| table                   | rows |
| ----------------------- | ---: |
| matches                 |    1 |
| bookmaker_odds_history  |    2 |
| raw_match_data          |    1 |
| l3_features             |    1 |
| match_features_training |    1 |
| predictions             |    1 |

`make data-dataset-status` still reports:

- `trainable = false`
- `finished_matches = 0`
- `matches_with_actual_result = 0`
- `matches_with_scores = 0`
- `trainable_label_rows = 0`

This phase does not change DB state. It only adds a local finished CSV preview gate.

## `data/mock/sample_history.csv` Structure

Observed sample:

- path: `data/mock/sample_history.csv`
- rows: `4`
- columns:
    - `match_id`
    - `external_id`
    - `league_name`
    - `season`
    - `home_team`
    - `away_team`
    - `match_date`
    - `status`
    - `bookmaker_name`
    - `market_type`
    - `open_home`
    - `open_draw`
    - `open_away`
    - `close_home`
    - `close_draw`
    - `close_away`
    - `home_score`
    - `away_score`

Important sample properties:

- rows 1-2 are duplicate scheduled rows for the same `match_id`
- row 3 is a finished row with full score
- row 4 contains `match_date=not-a-date`

## Dry-Run Summary

`make data-finished-csv-dry-run SAMPLE_CSV=data/mock/sample_history.csv` produced:

- `mode = dry-run`
- `csv_path = data/mock/sample_history.csv`
- `total_rows = 4`
- `finished_rows = 1`
- `trainable_label_rows = 1`
- `skipped_rows = 3`
- `would_insert_matches = false`
- `would_update_matches = false`
- `would_write_db = false`
- `db_existing_rows = 0`

## Label Mapping Rules

Implemented mapping order:

1. direct result fields:
    - `actual_result`
    - `FTR`
    - `result`
2. score-derived result:
    - `home_score` / `away_score`
    - `FTHG` / `FTAG`
    - `home_goals` / `away_goals`

Normalization:

- `H` / `home` / `home_win` / `1` => `home_win`
- `D` / `draw` / `x` => `draw`
- `A` / `away` / `away_win` / `2` => `away_win`

Score-derived rules:

- `home_score > away_score` => `home_win`
- `home_score = away_score` => `draw`
- `home_score < away_score` => `away_win`

Finished detection:

- `status in finished|completed|full_time|ft`
- or `is_finished=true`
- or complete score plus label

Non-trainable rows:

- scheduled rows
- rows without label
- rows without complete score
- rows with invalid dates

## Candidate Preview Summary

### Row 2

- `match_id_preview = 47_20242025_900001`
- `status = scheduled`
- `trainable = false`
- `skip_reason = not_finished`

Warnings:

- `not_finished`
- `missing_label`
- `missing_complete_score`

### Row 3

- `match_id_preview = 47_20242025_900001`
- `status = scheduled`
- `trainable = false`
- `skip_reason = not_finished`

Warnings:

- `not_finished`
- `missing_label`
- `missing_complete_score`

### Row 4

- `match_id_preview = 47_20242025_900002`
- `league_name = Segunda`
- `season = 2024_2025`
- `home_team = Burgos`
- `away_team = Oviedo`
- `home_score = 1`
- `away_score = 0`
- `actual_result = home_win`
- `label_source = score`
- `status = finished`
- `trainable = true`

This is the single trainable finished preview row in the sample.

### Row 5

- `match_id_preview = 47_20242025_900003`
- `status = scheduled`
- `match_date = not-a-date`
- `trainable = false`
- `skip_reason = not_finished`

Warnings:

- `invalid_match_date`
- `not_finished`
- `missing_label`
- `missing_complete_score`

## Mapping Warnings

Observed warnings:

- duplicate preview match id:
    - `47_20242025_900001`
- scheduled rows without labels:
    - rows 2 and 3
- invalid date:
    - row 5

These warnings confirm that future write phases must isolate malformed or non-trainable rows instead of assuming the whole CSV is safe.

## New Script

Added:

- `scripts/ops/finished_csv_local_dry_run.js`

Behavior:

- reads only a local CSV
- identifies compatible columns
- derives finished / trainable label status
- builds candidate preview rows
- optionally performs SELECT-only DB duplicate check for `match_id`
- blocks `--commit`

The script does not:

- write DB
- call `csv_bulk_loader --commit`
- train
- predict
- load model artifacts
- export files
- access external network

## Makefile Entrypoints

Added:

- `make data-finished-csv-dry-run SAMPLE_CSV=<path>`
- `make data-finished-csv-commit SAMPLE_CSV=<path> CONFIRM_FINISHED_CSV_COMMIT=1`

Behavior:

- dry-run requires `SAMPLE_CSV`
- commit gate is blocked both:
    - without `CONFIRM_FINISHED_CSV_COMMIT=1`
    - with `CONFIRM_FINISHED_CSV_COMMIT=1`

Phase 4.38 still does not wire any real finished CSV DB write path.

## AGENTS.md Update

Updated `AGENTS.md` to document:

- `make data-finished-csv-dry-run SAMPLE_CSV=<local csv>` is allowed only with explicit user authorization
- CSV must be local
- dry-run only
- no DB writes
- no training
- no prediction
- no external network
- no large export

Also documented:

- `make data-finished-csv-commit` is blocked
- `node scripts/ops/finished_csv_local_dry_run.js --commit` is blocked
- `csv_bulk_loader --commit` remains prohibited
- finished CSV import must confirm label mapping in reports first
- scheduled / unlabeled rows are not training samples
- external CSV download remains prohibited without separate authorization

## Validation

Executed:

```bash
make data-finished-csv-dry-run || true
make data-finished-csv-dry-run SAMPLE_CSV=data/mock/sample_history.csv
make data-finished-csv-commit || true
make data-finished-csv-commit \
  SAMPLE_CSV=data/mock/sample_history.csv \
  CONFIRM_FINISHED_CSV_COMMIT=1 || true
```

Results:

- missing `SAMPLE_CSV`: fails as expected
- dry-run: succeeds
- commit without confirm: blocked
- commit with confirm: still blocked

## DB Before / After

DB row counts were unchanged:

| table                   | rows |
| ----------------------- | ---: |
| matches                 |    1 |
| bookmaker_odds_history  |    2 |
| raw_match_data          |    1 |
| l3_features             |    1 |
| match_features_training |    1 |
| predictions             |    1 |

## Recommended Next Phase

Recommended next steps:

```text
Phase 4.39: human-authorized single-row or small-batch finished CSV matches write runbook
```

Alternative:

```text
Phase 4.39: extend CSV mapping to support more result/date/status field variants
```

## Explicit Non-Execution

This phase did not execute:

- `INSERT / UPDATE / DELETE / CREATE / ALTER / DROP / TRUNCATE`
- `COPY / \copy`
- DB writes
- `csv_bulk_loader --commit`
- `local_dom_ingestor --commit`
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
