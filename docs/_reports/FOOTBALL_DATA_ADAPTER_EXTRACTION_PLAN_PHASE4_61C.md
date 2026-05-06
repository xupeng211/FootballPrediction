# Phase 4.61C Football-Data Adapter Extraction Plan

Date: 2026-05-06

## 1. Current Head / Branch

- Starting HEAD: `8b27e8520c7b5ef8496692cbbb9038eda7e1d6eb`
- Working branch: `docs/football-data-adapter-extraction-phase461c`
- Base branch: `main`

## 2. Why fetch_and_adapt_euro_leagues Was Chosen

`fetch_and_adapt_euro_leagues` is the simplest current `adapter_candidate` to split first.

It targets structured Football-Data style CSV sources. Compared with `titan_discovery`, it has less browser / discovery runtime surface. Compared with `odds_harvest_pipeline`, it has less Playwright / proxy / Redis / UPSERT / downstream L3 coupling.

The right extraction route is:

```text
source manifest
  -> local CSV staging input
  -> pure CSV parser
  -> schema mapper
  -> local staging dry-run
  -> future controlled network dry-run
  -> future small DB write
```

This phase did not implement a parser. It records the adapter plan and keeps the legacy runtime blocked.

## 3. Current Legacy Script Risk Summary

Read-only audit of `scripts/ops/fetch_and_adapt_euro_leagues.js` confirms that the legacy runtime is not a safe Codex entrypoint.

Risk summary:

- external CSV download: `downloadToTempFile()` calls `fetch(sourceMeta.url)`
- temp file write: downloaded response is streamed to an OS temp directory
- adapted CSV write: `writeAdaptedCsv()` writes an adapted output file
- DB resolver coupling: `ExistingMatchResolver` constructs a `pg` Pool and reads `matches` / `raw_match_data` for alignment
- no trusted dry-run: there is no no-network local CSV path and no source manifest input

Current responsibility split:

- downloader: `resolveCandidateList()`, `resolveDownloadSource()`, `downloadToTempFile()`
- parser: `parseAndAdaptCsv()` streams a temp CSV through `csv-parser`
- mapper: `adaptSourceRow()`, league/team/date/score/odds mapping helpers
- DB resolver: `ExistingMatchResolver`, `buildMatchId()`
- file writer: `writeAdaptedCsv()`

## 4. Current Registry State

`config/acquisition_engines.phase454.json` keeps `fetch_and_adapt_euro_leagues` as:

- `status=adapter_candidate`
- `safe_for_ai_default=false`
- `canonical_entrypoint=false`
- `allowed_next_phase=requires_future_network_dry_run_authorization`
- `test_coverage=gate_covered`
- `phase454_policy=blocked`
- `accesses_network=true`
- `writes_db=false`
- `writes_files=true`
- `dry_run_trust_level=low`

Note: the Step 6 one-off Node snippet only checked top-level arrays / values. The current registry is wrapped as `{ engines: [...] }`, so that exact snippet reports `MISSING`. A compatible read of `registry.engines` confirmed the required state.

## 5. Adapter Extraction Layer Design

Layer 1: source manifest

- `source_name`
- `source_url`
- `license_url`
- `terms_url`
- `approval_status`
- `original_filename`
- `sha256`
- `row_count`
- `field_dictionary`
- `mapping_version`
- `human_approval_note`

Layer 2: local staging input

- input is a local CSV file only
- no download
- no external network
- file hash must match the manifest

Layer 3: pure CSV parser

- input is CSV text or already parsed rows
- output is normalized row objects plus row classification
- no DB reads
- no file writes
- no external network
- no dependency on Docker, Postgres, or the legacy downloader runtime

Layer 4: schema mapper

- `Date` -> `match_date`
- `HomeTeam` -> `home_team`
- `AwayTeam` -> `away_team`
- `FTHG` -> `home_score`
- `FTAG` -> `away_score`
- `FTR` -> `actual_result`
- `Div` -> `league_name`
- odds columns -> odds candidate preview only

Layer 5: local staging dry-run

- duplicate detection
- label readiness
- invalid row detection
- `would_insert_matches=false`
- `would_insert_odds=false`
- no DB writes

Layer 6: future network dry-run

- only after explicit user authorization
- single target or very small date window
- save local staging only
- no DB writes

Layer 7: future small DB write

- separate user authorization
- `pg_dump` first
- small batch only
- before / after DB counts required

## 6. Pure Parser Design

The future parser should be a pure module with deterministic inputs and outputs.

Required behavior:

- accept CSV text or row objects from a caller
- normalize teams, dates, scores, result labels, league code / name, and optional tactical fields
- classify rows as finished / scheduled / invalid
- identify label readiness from `FTHG`, `FTAG`, and `FTR`
- identify odds fields such as `B365H`, `B365D`, `B365A`, `PSH`, `PSD`, `PSA`, and closing variants
- output odds candidate previews without writing odds
- carry provenance metadata passed in from the manifest / caller
- return validation diagnostics instead of throwing for ordinary row issues

Hard constraints:

- no `fetch`
- no `pg` / `Pool`
- no filesystem write
- no staging write
- no model artifact load
- no training or prediction execution

## 7. Source Manifest Design

The manifest is the trust boundary for any Football-Data style source.

Required manifest checks:

- source identity and source URL are present
- license / terms URLs are present
- human approval status is explicit
- original filename is present
- local CSV `sha256` matches manifest `sha256`
- row count is declared and can be checked
- field dictionary documents CSV columns used by the mapper
- mapping version is declared
- provenance note explains who approved the file and for what use

Without license / terms review and provenance metadata, the adapter must stop before dry-run.

## 8. Local CSV Staging Dry-Run Design

The future dry-run should consume:

- `SOURCE_MANIFEST=<local json>`
- `SAMPLE_CSV=<local csv>`
- optional target scope, such as match id or small date window

It should report:

- manifest completeness
- hash match / mismatch
- row counts
- parsed rows
- invalid rows
- duplicate candidate summary
- finished label readiness
- scheduled / unlabeled row counts
- odds candidate field coverage
- `would_insert_matches=false`
- `would_insert_odds=false`
- `no_db_writes`
- `no_external_network`

Duplicate detection may use SELECT-only DB checks in a later gate, but the pure parser itself must stay DB-free.

## 9. Legacy Runtime Remains Blocked

Keep this file:

```text
scripts/ops/fetch_and_adapt_euro_leagues.js
```

It remains useful as legacy knowledge, but not as a Codex execution path.

Reasons:

- it downloads external CSV directly
- it writes temp files
- it writes adapted CSV output
- it reads DB for match alignment
- it has hidden source / network assumptions
- it has no manifest-bound local CSV mode
- it has no trusted no-network dry-run

## 10. Logic That Can Be Extracted

Only extract narrowly scoped knowledge:

- CSV column mapping knowledge
- team normalization strategy, if moved behind a pure input / output boundary
- date parsing logic, if made pure
- score / result label normalization
- match candidate construction
- odds column recognition
- row diagnostics / quality flags

These pieces must be copied or refactored into no-network, no-db, no-file-write modules with unit tests.

## 11. Logic That Must Not Be Reused Directly

Do not reuse:

- downloader runtime
- `fetch(sourceMeta.url)`
- temp file writer
- adapted CSV writer
- `ExistingMatchResolver` DB coupling
- `pg` Pool construction
- implicit football-data URL candidate iteration
- hidden network fallback behavior
- any path that writes staging, DB rows, training data, predictions, or model artifacts

## 12. Future Modules Recommended

Recommended future files:

```text
scripts/ops/football_data_source_manifest_audit.js
scripts/ops/football_data_local_csv_parser.js
scripts/ops/football_data_adapter_dry_run.js
tests/unit/football_data_local_csv_parser.test.js
tests/unit/football_data_adapter_dry_run.test.js
```

Phase 4.62C should start with `football_data_local_csv_parser.js` and local fixtures only.

## 13. Gate Verification Results

Validated:

```bash
make data-acquisition-engine-audit
```

Result:

- `registry_found=true`
- `registry_valid=true`
- `adapter_candidate_engines=titan_discovery,fetch_and_adapt_euro_leagues,odds_harvest_pipeline`
- `engines_requiring_future_network_authorization=titan_discovery,fetch_and_adapt_euro_leagues,odds_harvest_pipeline`
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
- `blocked_reason=BLOCKED: Phase 4.54 is scaffold-only...`
- `no_db_writes`
- `no_external_network`
- `no_engine_execution`

Validated:

```bash
make data-single-target-network-commit \
  ENGINE=fetch_and_adapt_euro_leagues \
  TARGET_MATCH_ID=47_20242025_900002 \
  SOURCE_MANIFEST=tests/fixtures/real_source_manifests/local_sample_history_phase452.json \
  CONFIRM_SINGLE_TARGET_NETWORK=1 || true
```

Result:

- `BLOCKED: acquisition network commit is not wired in Phase 4.54.`
- no DB writes
- no external network
- no engine execution

## 14. Unit Test Verification Results

Relevant unit tests passed:

```bash
docker compose -f docker-compose.dev.yml exec -T dev node --test tests/unit/acquisition_engine_gate.test.js
docker compose -f docker-compose.dev.yml exec -T dev node --test tests/unit/fetch_and_adapt_euro_leagues_no_network.test.js
```

Results:

- `tests/unit/acquisition_engine_gate.test.js`: 8/8 passed
- `tests/unit/fetch_and_adapt_euro_leagues_no_network.test.js`: 4/4 passed

Full default test gate also passed:

```bash
docker compose -f docker-compose.dev.yml exec -T dev npm test
```

Result:

- key smoke tests passed
- full unit suite passed
- command exited `0`

## 15. DB Before / After

Before validation:

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

`make data-dataset-status` remained `trainable=false`.

## 16. Next Step Recommendation

Preferred next step:

- Phase 4.62C: implement `football_data_local_csv_parser` pure parser plus unit tests, using local fixtures only, with no network, no DB, no file writes, no training, and no prediction.

Alternative only if the user provides all real network dry-run parameters:

- Phase 4.56A: first write a runbook for controlled network dry-run. Do not touch the network while drafting the runbook.

Without real parameters and separate authorization, no network access is allowed.

## 17. Explicit Non-Execution

Not executed in Phase 4.61C:

- DB writes
- external download
- `curl` / `wget` / `git clone`
- external football data source access
- external odds data source access
- scraping / browser automation
- harvest / ingest
- batch backfill
- real network dry-run execution
- bulk harvest
- adapted CSV write
- staging data creation
- model training
- real prediction execution
- model artifact loading
- Docker volume cleanup
- force push
- `git fetch --all`
- `git pull`
- file deletion
