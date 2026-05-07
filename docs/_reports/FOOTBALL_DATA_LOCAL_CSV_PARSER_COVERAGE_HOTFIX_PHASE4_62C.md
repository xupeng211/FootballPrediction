# Phase 4.62C Hotfix Football-Data Parser Coverage Gate

Date: 2026-05-07

## 1. Current Head / Branch

- Starting main HEAD: `747c3bb6ad0f6b288b830d1157cfb18f15d64461`
- Working branch: `test/football-data-parser-coverage-hotfix-phase462c`
- Base branch: `main`

## 2. Main Red Gate Reason

The merge commit from PR #1170 reached `main`, then the `Production Gate` push workflow failed.

Failure context:

- run id: `25424427867`
- event: `push`
- branch: `main`
- headSha: `747c3bb6ad0f6b288b830d1157cfb18f15d64461`
- failed step: `Run Gatekeeper`
- failed command: `npm run test:coverage`

Key failure:

```text
[TEST-GATE] 覆盖率门禁已启用: lines>=80, functions>=80, branches>=80
[TEST-GATE] 覆盖率未达标: branches=79.96 < 80
[TEST-GATE] 覆盖率测试已完成，但覆盖率门禁失败。
[Gatekeeper] GATEKEEPER_FAILURE_REASON=npm run test:coverage failed
```

Local reproduction before the hotfix also failed with:

```text
branches=79.98 < 80
```

## 3. Fix Strategy

This hotfix does not change the coverage threshold.

This hotfix does not bypass Gatekeeper.

The fix is intentionally narrow:

- add parser branch coverage tests
- keep the parser pure
- keep legacy runtime blocked
- keep external network / DB / file-write boundaries unchanged

One parser behavior bug was corrected:

- before: invalid non-empty `FTR` could fall back to score-derived result when the score was complete
- after: non-empty unsupported `FTR` is `invalid_result`

This matches the Phase 4.62C rule that score-derived fallback is only allowed when `FTR` is missing.

## 4. Test Changes Summary

Updated:

- `tests/unit/football_data_local_csv_parser.test.js`
- `scripts/lib/football_data_local_csv_parser.js`

Added parser branch coverage for:

- `FTR` missing with score-derived fallback
- invalid non-empty `FTR`
- `FTR` / score mismatch
- missing `HomeTeam`
- no odds columns
- partial odds columns
- rows input instead of CSV text
- default parser options
- `dd/mm/yy` date parsing
- missing `Time`
- empty CSV text

## 5. Coverage Gate Result

After the hotfix:

```text
lines=87.69
statements=87.69
functions=80.28
branches=80.02
```

`npm run test:coverage` exited `0`.

## 6. Parser Safety Constraints

The parser safety constraints remain in place:

- no network
- no DB read
- no DB write
- no file write from parser
- no legacy runtime import
- no training
- no prediction execution

The unit test still monkey-patches / blocks:

- `http.request`
- `https.request`
- `global.fetch`
- `child_process.spawn`
- `child_process.exec`
- `child_process.execFile`
- parser-time imports of `pg`, `fs`, `http`, `https`, `child_process`, and `fetch_and_adapt_euro_leagues`

## 7. Gate Blocked Verification

Validated:

```bash
make data-acquisition-engine-audit
```

Result:

- `registry_found=true`
- `registry_valid=true`
- `fetch_and_adapt_euro_leagues` remains an `adapter_candidate`
- `no_db_writes`
- `no_external_network`

Validated:

```bash
make data-single-target-network-dry-run \
  ENGINE=fetch_and_adapt_euro_leagues \
  TARGET_MATCH_ID=47_20242025_900002 \
  SOURCE_MANIFEST=tests/fixtures/real_source_manifests/local_sample_history_phase452.json || true
```

Result:

- `engine_found=true`
- `would_access_network=false`
- `would_write_db=false`
- `would_execute_engine=false`
- blocked with `Phase 4.54 is scaffold-only`

Validated:

```bash
make data-single-target-network-commit \
  ENGINE=fetch_and_adapt_euro_leagues \
  TARGET_MATCH_ID=47_20242025_900002 \
  SOURCE_MANIFEST=tests/fixtures/real_source_manifests/local_sample_history_phase452.json \
  CONFIRM_SINGLE_TARGET_NETWORK=1 || true
```

Result:

- blocked with `acquisition network commit is not wired in Phase 4.54`

## 8. DB Before / After

Before hotfix validation:

- `matches=2`
- `bookmaker_odds_history=2`
- `raw_match_data=2`
- `l3_features=2`
- `match_features_training=2`
- `predictions=2`

After hotfix validation:

- `matches=2`
- `bookmaker_odds_history=2`
- `raw_match_data=2`
- `l3_features=2`
- `match_features_training=2`
- `predictions=2`

## 9. Validation Summary

Validated commands:

```bash
docker compose -f docker-compose.dev.yml exec -T dev node --test tests/unit/football_data_local_csv_parser.test.js
docker compose -f docker-compose.dev.yml exec -T dev node --test tests/unit/fetch_and_adapt_euro_leagues_no_network.test.js
docker compose -f docker-compose.dev.yml exec -T dev node --test tests/unit/acquisition_engine_gate.test.js
docker compose -f docker-compose.dev.yml exec -T dev npm run test:coverage
docker compose -f docker-compose.dev.yml exec -T dev npm test
docker compose -f docker-compose.dev.yml exec -T dev npx eslint scripts/lib/football_data_local_csv_parser.js tests/unit/football_data_local_csv_parser.test.js --no-cache
docker compose -f docker-compose.dev.yml exec -T dev npx prettier --check AGENTS.md scripts/lib/football_data_local_csv_parser.js tests/unit/football_data_local_csv_parser.test.js docs/_reports/FOOTBALL_DATA_LOCAL_CSV_PARSER_PHASE4_62C.md
```

Results:

- parser unit tests: 10/10 passed
- football-data legacy no-network tests: 4/4 passed
- acquisition gate tests: 8/8 passed
- `npm run test:coverage`: passed
- `npm test`: passed
- eslint: passed
- prettier: passed

## 10. Next Step

Recommended next step:

- Phase 4.63C: implement `football_data_adapter_dry_run`, connect the parser to local source manifest + local CSV dry-run, and still avoid DB writes.

## 11. Explicit Non-Execution

Not executed in this hotfix:

- coverage threshold changes
- Gatekeeper bypass
- DB writes
- parser DB reads
- parser file writes
- external download
- `curl` / `wget` / `git clone`
- external football data source access
- external odds data source access
- scraping / browser automation
- harvest / ingest
- batch backfill
- network dry-run execution
- bulk harvest
- model training
- real prediction execution
- model artifact loading
- Docker volume cleanup
- force push
- `git fetch --all`
- `git pull`
- file deletion
