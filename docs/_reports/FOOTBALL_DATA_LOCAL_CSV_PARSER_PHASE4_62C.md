# Phase 4.62C Football-Data Local CSV Parser

Date: 2026-05-06

## 1. Current Head / Branch

- Starting HEAD: `7640fc16bec86a8f7999179828de50fd723b3af7`
- Working branch: `feat/football-data-local-csv-parser-phase462c`
- Report timestamp (UTC): `2026-05-06T07:37:16Z`

## 2. Why This Phase Implements a Pure Parser

Phase 4.61C defined the extraction route for `fetch_and_adapt_euro_leagues`:

```text
source manifest
  -> local CSV staging input
  -> pure CSV parser
  -> schema mapper
  -> local staging dry-run
  -> future controlled network dry-run
  -> future small DB write
```

Phase 4.62C implements only the pure parser layer.

This keeps the current phase inside the approved boundary:

- local synthetic CSV fixture only
- no external football-data access
- no external odds source access
- no downloader reuse
- no DB reads from parser
- no DB writes
- no adapted CSV writes
- no training
- no prediction execution

## 3. Added / Updated Files

- `scripts/lib/football_data_local_csv_parser.js`
- `tests/fixtures/football_data/football_data_sample_phase462c.csv`
- `tests/unit/football_data_local_csv_parser.test.js`
- `AGENTS.md`
- `docs/_reports/FOOTBALL_DATA_LOCAL_CSV_PARSER_PHASE4_62C.md`

## 4. Parser Design

`scripts/lib/football_data_local_csv_parser.js` is a pure parser module.

It accepts CSV text or already parsed rows and returns structured parser output.

It does not:

- access the network
- read DB
- write DB
- write files
- spawn child processes
- import `scripts/ops/fetch_and_adapt_euro_leagues.js`
- import `pg`

Parser output includes:

- `parser_version`
- `source_name`
- `total_rows`
- `parsed_rows`
- `candidate_rows`
- `row_classification`
- `warnings`
- `errors`
- `non_execution_confirmations`

Safety confirmations returned by the parser:

- `no_external_network`
- `no_db_reads`
- `no_db_writes`
- `no_file_writes`
- `no_legacy_runtime`
- `no_training`
- `no_prediction_execution`

## 5. Supported Fields

The parser recognizes these Football-Data style columns in Phase 4.62C:

- `Div`
- `Date`
- `Time`
- `HomeTeam`
- `AwayTeam`
- `FTHG`
- `FTAG`
- `FTR`
- `B365H`
- `B365D`
- `B365A`
- `PSH`
- `PSD`
- `PSA`

The parser maps:

- `Div` -> `league_name`
- `Date` + `Time` -> `match_date`
- `HomeTeam` -> `home_team`
- `AwayTeam` -> `away_team`
- `FTHG` -> `home_score`
- `FTAG` -> `away_score`
- `FTR` -> `actual_result`

## 6. Label Mapping

Supported label mapping:

- `H` -> `home_win`
- `D` -> `draw`
- `A` -> `away_win`

Fallback when `FTR` is missing but the final score is complete:

- `home_score > away_score` -> `home_win`
- `home_score = away_score` -> `draw`
- `home_score < away_score` -> `away_win`

`FTHG`, `FTAG`, and `FTR` are treated as label-only fields in this phase. They are not treated as features.

## 7. Fixture Test Summary

Local synthetic parser fixture:

`tests/fixtures/football_data/football_data_sample_phase462c.csv`

Fixture coverage:

- 1 valid `home_win`
- 1 valid `draw`
- 1 valid `away_win`
- 1 invalid date row
- 1 missing score row
- Bet365 odds columns present
- Pinnacle odds columns present

Fixture results:

- `total_rows=5`
- `candidate_rows=3`
- `finished_rows=3`
- `trainable_label_rows=3`
- `skipped_rows=2`
- `invalid_date_rows=1`
- `missing_score_rows=1`
- `odds_preview_rows=3`

## 8. Unit Test Results

Validated commands:

```bash
docker compose -f docker-compose.dev.yml exec -T dev node --test tests/unit/football_data_local_csv_parser.test.js
docker compose -f docker-compose.dev.yml exec -T dev node --test tests/unit/fetch_and_adapt_euro_leagues_no_network.test.js
docker compose -f docker-compose.dev.yml exec -T dev node --test tests/unit/acquisition_engine_gate.test.js
docker compose -f docker-compose.dev.yml exec -T dev npm test
```

Observed results:

- `tests/unit/football_data_local_csv_parser.test.js`: 5/5 passed
- `tests/unit/fetch_and_adapt_euro_leagues_no_network.test.js`: 4/4 passed
- `tests/unit/acquisition_engine_gate.test.js`: 8/8 passed
- `npm test`: exited `0`; default gate passed

The new parser unit test explicitly monkey patches and blocks:

- `http.request`
- `https.request`
- `global.fetch`
- `child_process.spawn`
- `child_process.exec`
- `child_process.execFile`

It also blocks parser-time imports of:

- `pg`
- `fs`
- `http`
- `https`
- `child_process`
- `fetch_and_adapt_euro_leagues`

## 9. Gate Blocked Verification

Validated commands:

```bash
make data-acquisition-engine-audit

make data-single-target-network-dry-run \
  ENGINE=fetch_and_adapt_euro_leagues \
  TARGET_MATCH_ID=47_20242025_900002 \
  SOURCE_MANIFEST=tests/fixtures/real_source_manifests/local_sample_history_phase452.json || true

make data-single-target-network-commit \
  ENGINE=fetch_and_adapt_euro_leagues \
  TARGET_MATCH_ID=47_20242025_900002 \
  SOURCE_MANIFEST=tests/fixtures/real_source_manifests/local_sample_history_phase452.json \
  CONFIRM_SINGLE_TARGET_NETWORK=1 || true
```

Expected safety properties that remain required:

- `engine_found=true`
- `would_access_network=false`
- `would_write_db=false`
- `would_execute_engine=false`
- dry-run gate blocked
- commit gate blocked

Observed Phase 4.62C result:

- `make data-acquisition-engine-audit`: passed, `fetch_and_adapt_euro_leagues` remained an `adapter_candidate`
- scaffold gate: `engine_found=true`
- scaffold gate: `would_access_network=false`
- scaffold gate: `would_write_db=false`
- scaffold gate: `would_execute_engine=false`
- scaffold gate: blocked with `Phase 4.54 is scaffold-only`
- commit gate: blocked with `acquisition network commit is not wired in Phase 4.54`

## 10. DB Before / After

Before implementation:

- `matches=2`
- `bookmaker_odds_history=2`
- `raw_match_data=2`
- `l3_features=2`
- `match_features_training=2`
- `predictions=2`

After validation the counts must remain unchanged:

- `matches=2`
- `bookmaker_odds_history=2`
- `raw_match_data=2`
- `l3_features=2`
- `match_features_training=2`
- `predictions=2`

Observed after validation:

- `matches=2`
- `bookmaker_odds_history=2`
- `raw_match_data=2`
- `l3_features=2`
- `match_features_training=2`
- `predictions=2`

## 11. Next Step Recommendation

Preferred next step:

- Phase 4.63C: implement `football_data_adapter_dry_run`, connect the parser to local `source manifest` + local CSV dry-run, and keep `would_insert_matches=false` / `would_insert_odds=false`

Alternative only if the user later provides the six required real network dry-run parameters:

- Phase 4.56A: write a controlled football-data network dry-run runbook first, without touching the network

Without real parameters and separate authorization, no network access is allowed.

## 12. Explicit Non-Execution

Not executed in Phase 4.62C:

- DB writes
- DB reads from the parser
- parser file writes
- adapted CSV writes
- external download
- `curl` / `wget` / `git clone`
- external football data source access
- external odds data source access
- scraping / browser automation
- harvest / ingest
- batch backfill
- real network dry-run execution
- bulk harvest
- model training
- real prediction execution
- model artifact loading
- Docker volume cleanup
- force push
- `git fetch --all`
- `git pull`
- file deletion
