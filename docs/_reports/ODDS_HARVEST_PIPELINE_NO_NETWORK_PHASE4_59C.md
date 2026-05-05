# Phase 4.59C Odds Harvest Pipeline No-Network Hardening

Date: 2026-05-05

## 1. Current Head / Branch

- Starting HEAD: `53d0d7685e71539d116762dd83398f57409f667e`
- Working branch: `test/odds-harvest-no-network-phase459c`
- Base branch: `main`

## 2. Why This Engine Was Chosen

`odds_harvest_pipeline` was chosen because odds data is important to prediction quality and this pipeline has a higher risk profile than local CSV adapters. It may touch external odds sources, launch browser automation, use network fetches, read and write Postgres, and optionally trigger downstream L3 work.

Phase 4.59C does not execute odds harvest. It only improves no-network / no-db governance around the legacy runtime.

## 3. Read-Only Source Audit Summary

Read-only inspection of `scripts/ops/odds_harvest_pipeline.js` and `scripts/ops/odds_harvest_pipeline.shared.js` shows:

- `odds_harvest_pipeline.js` exists and is wired from `npm run odds:harvest`
- the script creates a `pg` Pool at module scope
- it imports Playwright `chromium` and launches a browser in `enumerateLeagueEvents()`
- it builds OddsPortal results URLs from route config
- it uses global `fetch()` in `fetchText()` for OddsPortal pages and ajax payloads
- it uses `ReconPureDecryptor` for OddsPortal payload decoding
- it reads target matches and coverage from Postgres
- it upserts mapping and odds rows through `UPSERT_MAPPING_SQL` and `UPSERT_ODDS_SQL`
- it can spawn `scripts/ops/l3_stitch_pipeline.js` after odds processing
- `parseArgs()` recognizes `--dry-run`, but dry-run is not a safe no-network mode because enumeration, fetch/decrypt, DB reads, and optional L3 behavior remain part of the runtime path

Relevant risk points found in code:

- top-level `new Pool(...)`
- Playwright `chromium.launch(...)`
- `page.goto(...)` and pagination over OddsPortal results pages
- `fetchText()` calling external URLs through `fetch()`
- `createDecryptor()` loading a bundle URL
- `fetchAjaxEventData()` and `fetchPreMatchData()` requesting OddsPortal ajax payloads
- `upsertMappingAndOdds()` writing mapping and odds rows unless `options.dryRun`
- `runL3Stitch()` spawning L3 pipeline unless disabled or mapping-only
- default route selection covers all configured routes when no league is provided

## 4. Current Risk Assessment

Current risks remain:

- may access external network
- may access external OddsPortal odds sources
- may use browser automation
- may use proxy-adjacent recon/decryptor runtime
- may read and write Postgres
- may trigger downstream L3 work
- may batch harvest multiple leagues by default
- current dry-run trust is insufficient
- odds without clear `captured_at`, bookmaker, market, source URL, and provenance can create training leakage risk
- closing odds or post-match odds must not be treated as pre-match features
- not suitable for direct Codex execution

Because of that, this engine remains an `adapter_candidate`, not a canonical entrypoint.

## 5. Registry Update Summary

`config/acquisition_engines.phase454.json` was updated only for `odds_harvest_pipeline`:

- kept `status=adapter_candidate`
- kept `safe_for_ai_default=false`
- kept `canonical_entrypoint=false`
- kept `allowed_next_phase=requires_future_network_dry_run_authorization`
- strengthened `notes` to state that the legacy runtime may touch external odds sources, browser automation, Postgres writes, and downstream L3
- strengthened `notes` with timestamp / closing-odds leakage risk
- strengthened `replacement_plan` to explicitly forbid direct reuse of the legacy runtime
- required a future Layer 3 single-target odds acquisition adapter
- required source manifest, target scope, bookmaker / market / captured_at / source_url / sha256 / provenance capture
- kept any future network dry-run separately authorized
- required separate authorization plus `pg_dump` before any future DB write
- updated `test_coverage` from `needs_unit_tests` to `gate_covered`

## 6. No-Network / No-DB Test Coverage

Added:

- `tests/unit/odds_harvest_pipeline_no_network.test.js`

Coverage added:

- registry contains `odds_harvest_pipeline`
- governance state stays `adapter_candidate`
- `safe_for_ai_default=false`
- `canonical_entrypoint=false`
- `allowed_next_phase=requires_future_network_dry_run_authorization`
- acquisition gate engine mode stays blocked
- `would_access_network=false`
- `would_write_db=false`
- `would_execute_engine=false`
- `--commit` stays blocked
- the test does not import or execute the legacy runtime

## 7. Acquisition Gate Blocked Validation

Validated with:

```bash
make data-single-target-network-dry-run \
  ENGINE=odds_harvest_pipeline \
  TARGET_MATCH_ID=47_20242025_900002 \
  SOURCE_MANIFEST=tests/fixtures/real_source_manifests/local_sample_history_phase452.json
```

Observed blocked semantics:

- `engine_found=true`
- `would_access_network=false`
- `would_write_db=false`
- `would_execute_engine=false`

## 8. Commit Blocked Validation

Validated with:

```bash
make data-single-target-network-commit \
  ENGINE=odds_harvest_pipeline \
  TARGET_MATCH_ID=47_20242025_900002 \
  SOURCE_MANIFEST=tests/fixtures/real_source_manifests/local_sample_history_phase452.json \
  CONFIRM_SINGLE_TARGET_NETWORK=1
```

Observed result:

- blocked
- no external network
- no DB writes
- no engine execution

## 9. Preflight Scaffold

No `odds_harvest_preflight.js` scaffold was added in Phase 4.59C. The smallest safe change is to keep the legacy runtime fully blocked and covered by registry / acquisition gate tests.

## 10. DB Before / After

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

## 11. Next Step Recommendation

Two clean next steps remain:

1. Phase 4.60C: summarize adapter candidates and confirm `fetch_and_adapt_euro_leagues`, `titan_discovery`, and `odds_harvest_pipeline` are all `gate_covered`.
2. Phase 4.56A: only after the user provides the six real network dry-run parameters, prepare a runbook without actually touching the network.

## 12. Explicit Non-Execution

Not executed in Phase 4.59C:

- DB writes
- external download
- `curl` / `wget` / `git clone`
- external football data access
- external odds data access
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
