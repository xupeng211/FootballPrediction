# Phase 4.28 - L3 Features Single Insert

## Current HEAD

- Branch: `main`
- HEAD: `2f179fd4c9a7733342756d7d540cf4d7ba83b380`
- Target match: `140_20252026_4837496`
- Fixture: `tests/fixtures/l3/raw_match_data_phase419_sample.json`

## Backup

- Backup file: `data/backups/phase428_pre_l3_features_insert_20260503_171518.dump`
- Backup size: `69K`
- Backup command: `pg_dump --format=custom`

## Pre-Insert State

| table                   | rows before |
| ----------------------- | ----------: |
| matches                 |           1 |
| bookmaker_odds_history  |           2 |
| raw_match_data          |           1 |
| l3_features             |           0 |
| match_features_training |           0 |
| predictions             |           0 |

Target preconditions:

- Target match exists: yes
- Odds history rows: 2
- `raw_match_data` exists: yes
- Target `l3_features` rows: 0

## Insert Result

A single authorized `INSERT INTO l3_features` was executed for:

- `match_id`: `140_20252026_4837496`
- Source fixture: `tests/fixtures/l3/raw_match_data_phase419_sample.json`
- Source DB reads: `matches`, `bookmaker_odds_history`, `raw_match_data`

Returned values:

- `match_id`: `140_20252026_4837496`
- `computed_at`: `2026-05-03 09:15:52.069702+00`
- `created_at`: `2026-05-03 09:15:52.069702+00`
- `updated_at`: `2026-05-03 09:15:52.069702+00`

Inserted JSONB groups:

- `golden_features`
- `tactical_features`
- `odds_features`
- `elo_features`
- `stitch_summary`

Defaulted JSONB groups remain available through table defaults:

- `odds_movement_features`
- `rolling_features`
- `efficiency_features`
- `draw_features`
- `market_sentiment`

## Post-Insert l3_features Verification

- Target `l3_features` rows: 1
- `golden_features`: object
- `tactical_features`: object
- `odds_features`: object
- `elo_features`: object
- `stitch_summary`: object

## Post-Insert Row Counts

| table                   | rows after |
| ----------------------- | ---------: |
| matches                 |          1 |
| bookmaker_odds_history  |          2 |
| raw_match_data          |          1 |
| l3_features             |          1 |
| match_features_training |          0 |
| predictions             |          0 |

Only `l3_features` changed from 0 to 1.

## Gate Verification

Post-insert `make data-l3-write-dry-run` result:

- `mode`: `dry-run`
- `match_found`: `true`
- `raw_match_data_found`: `true`
- `odds_history_rows`: `2`
- `l3_features_exists`: `true`
- `l3_features_rows`: `1`
- `would_insert_l3_features`: `false`
- `would_update_matches`: `false`
- `would_trigger_elo`: `false`
- Non-execution confirmations include `no_db_writes`, `no_insert`, `no_update`, `no_delete`, `no_smelt`, `no_l3_stitch`, `no_l3_write`, `no_elo`, and `no_external_network`

Post-insert `make data-l3-dry-run` result:

- Read-only dry-run still succeeds
- `would_write_l3_features`: `false`
- `would_update_matches`: `false`
- `would_trigger_elo`: `false`

## Risks And Notes

- This was a manual single-row local dev DB insert, not a production L3 pipeline run.
- The inserted feature payload is intentionally conservative and traceable to local fixture plus read-only DB preflight data.
- ELO remains unavailable by design.
- No `matches` update was performed.
- No training or prediction table was populated.

## Explicit Non-Execution

The phase did not execute:

- `UPDATE`
- `DELETE`
- `CREATE`
- `ALTER`
- `DROP`
- `TRUNCATE`
- `INSERT` into any table except `l3_features`
- duplicate `l3_features` insert
- `raw_match_data` commit
- `npm run smelt`
- `npm run l3:stitch`
- ELO recalculation
- model training
- prediction write
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

## Next Steps

- Phase 4.29 can submit this report, or design the next `match_features_training` / prediction preflight runbook.
- Any next write should remain single-match, explicitly authorized, backed up, and isolated from smelt / stitch / ELO unless separately authorized.
