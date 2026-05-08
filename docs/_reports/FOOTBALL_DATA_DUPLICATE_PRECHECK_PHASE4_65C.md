# Football-Data Duplicate Precheck Phase 4.65C

## Current State

- Branch: `feat/football-data-duplicate-precheck-phase465c`
- HEAD at report time: `16f78451ab08976e1106836f5854729c982a3b21`
- Base phase: Phase 4.64C DB write preflight merged on `main`

## PR Scope

This is a slightly larger theme PR because the changes belong to one safety
boundary: preparing Football-Data local CSV candidates for a future small DB
write without writing anything yet. The script, Makefile gate, tests,
AGENTS.md rules, and report all document the same SELECT-only duplicate /
existing match precheck behavior.

## Added Files

- `scripts/ops/football_data_duplicate_precheck.js`
- `tests/unit/football_data_duplicate_precheck.test.js`
- `docs/_reports/FOOTBALL_DATA_DUPLICATE_PRECHECK_PHASE4_65C.md`

## Design

`football_data_duplicate_precheck.js` reuses the Phase 4.63C local CSV dry-run
gate, so source manifest approval, `sha256`, `row_count`, and parser candidate
rows are validated before any DB precheck begins.

The precheck then opens a read-only DB transaction and checks each candidate
with SELECT-only queries:

- exact home / away / match date match
- reversed home / away / match date match
- same teams or reversed teams within plus/minus 2 days

Each candidate receives a preview with:

- `duplicate_risk`
- `existing_match_ids`
- `nearby_match_ids`
- `candidate_identity_key`
- `proposed_match_id_strategy=not_finalized`
- `match_id_write_allowed=false`
- `would_insert_match=false`
- `would_insert_odds=false`

## SELECT-Only DB Safety

The script uses `BEGIN READ ONLY`, SELECT statements, and `ROLLBACK`. It also
guards every SQL string and rejects write keywords including `INSERT`,
`UPDATE`, `DELETE`, `CREATE`, `ALTER`, `DROP`, `TRUNCATE`, `COPY`, `MERGE`,
`GRANT`, `REVOKE`, `COMMIT`, and `\\copy`.

The script does not execute DB writes, `pg_dump`, child processes, training, or
prediction. It does not import the legacy Football-Data downloader runtime.

## Duplicate Checks

The fixture precheck completed with:

- `candidate_rows=3`
- `trainable_label_rows=3`
- `exact_existing_matches=0`
- `reversed_team_matches=0`
- `nearby_date_matches=0`
- `invalid_candidates=0`
- all candidates had `duplicate_risk=none`

## Identity Preview

The current preview key is:

```text
league_name + season + match_date + normalized_home_team + normalized_away_team
```

This is not a final write ID. The report and gate keep
`proposed_match_id_strategy=not_finalized` and `match_id_write_allowed=false`.

## Required Before DB Write

- deterministic match_id strategy must be finalized
- duplicate policy must be approved
- exact_existing_match rows must not be inserted
- nearby_date_possible_duplicate rows require manual review
- pg_dump backup must run immediately before write
- max rows must be explicit
- target table list must be explicit
- post-write validation must compare row counts and target rows
- training/prediction must remain blocked

## Gate Results

- `make data-football-data-duplicate-precheck` without args failed as expected.
- `make data-football-data-duplicate-precheck SOURCE_MANIFEST=... LOCAL_CSV=...`
  passed with `select_only_db_reads=true`, `no_db_writes=true`, and
  `would_write_db=false`.
- `make data-football-data-duplicate-precheck-commit` remained blocked.
- `make data-football-data-duplicate-precheck-commit ... CONFIRM_FOOTBALL_DATA_DUPLICATE_PRECHECK=1`
  remained blocked.

## Existing Gate Recheck

- Football-Data CSV dry-run passed.
- Football-Data DB write preflight passed.
- Football-Data CSV commit remained blocked.
- Football-Data DB write commit remained blocked.
- Acquisition engine audit passed with `no_db_writes` and `no_external_network`.
- Single-target acquisition network scaffold remained blocked with
  `would_access_network=false`, `would_write_db=false`, and
  `would_execute_engine=false`.
- Acquisition network commit remained blocked.

## Test Results

- `node --test tests/unit/football_data_duplicate_precheck.test.js`: passed,
  20 tests.
- `node --test tests/unit/football_data_db_write_preflight.test.js`: passed,
  11 tests.
- `node --test tests/unit/football_data_adapter_dry_run.test.js`: passed,
  11 tests.
- `node --test tests/unit/football_data_local_csv_parser.test.js`: passed,
  10 tests.
- `node --test tests/unit/fetch_and_adapt_euro_leagues_no_network.test.js`:
  passed, 4 tests.
- `node --test tests/unit/acquisition_engine_gate.test.js`: passed, 8 tests.
- `npm test`: passed.
- `npm run test:coverage`: passed with `lines=87.90`, `branches=80.06`,
  `functions=80.44`.

## DB Counts

Before this phase:

- `matches=2`
- `bookmaker_odds_history=2`
- `raw_match_data=2`
- `l3_features=2`
- `match_features_training=2`
- `predictions=2`

After validation:

- `matches=2`
- `bookmaker_odds_history=2`
- `raw_match_data=2`
- `l3_features=2`
- `match_features_training=2`
- `predictions=2`

## Why No DB Write

Phase 4.65C only answers whether future candidate rows look duplicative against
existing matches. It intentionally stops before deterministic match ID policy,
insert policy, backup execution, and authorized small-batch write.

## Next Steps

- Phase 4.66C: design deterministic match_id strategy and insert candidate
  policy without writing DB.
- Or Phase 4.56A: continue the real network dry-run runbook only after the user
  provides the complete authorized parameters.

## Not Executed

- DB writes
- non-SELECT DB SQL
- `pg_dump` or `pg_restore`
- file writes from the precheck script
- external downloads
- `curl`, `wget`, or `git clone`
- external football data source access
- external odds data source access
- scraping or browser automation
- harvest, ingest, batch backfill, or bulk harvest
- real network dry-run execution
- adapted CSV or staging writes
- model training
- real prediction execution
- model artifact loading
- Docker volume cleanup
- force push
- `git fetch --all`
- `git pull`
- file deletion
