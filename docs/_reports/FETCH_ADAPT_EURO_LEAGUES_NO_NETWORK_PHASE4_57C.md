# Phase 4.57C Fetch And Adapt Euro Leagues No-Network Hardening

Date: 2026-05-05

## 1. Current Head / Branch

- Starting HEAD: `f181a5301aadb2236ac831846a10dc71fafa76aa`
- Working branch: `test/football-data-adapter-no-network-phase457c`
- Base branch: `main`

## 2. Why This Engine Was Chosen

`fetch_and_adapt_euro_leagues` was chosen first among the current `adapter_candidate` engines because it is source-specific, its source family is relatively clear, and its runtime is easier to classify than `titan_discovery` or `odds_harvest_pipeline`.

The goal in Phase 4.57C is not to download anything. The goal is to improve dry-run trust governance around this legacy downloader and make its blocked state explicit and test-protected.

## 3. Read-Only Source Audit Summary

Read-only inspection of `scripts/ops/fetch_and_adapt_euro_leagues.js` shows:

- it builds football-data URLs under `https://www.football-data.co.uk/mmz4281/...`
- it uses `fetch(...)` to download CSV content
- it writes a temporary CSV file under a temp directory
- it reads the local DB through `pg` to align matches
- it writes an adapted CSV to `data/mock/real_euro_league_adapted.csv` by default
- it has no safe no-network dry-run mode
- it has no source manifest input
- it does not emit the provenance / hash / manifest discipline required by the current canonical route

Relevant risk points found in code:

- network fetch: `downloadToTempFile()` around lines 540-553
- football-data URL construction: `resolveCandidateList()` around lines 562-583
- DB read alignment: `ExistingMatchResolver.load()` around lines 311-340
- adapted CSV write: `writeAdaptedCsv()` around lines 714-722

## 4. Current Risk Assessment

Current risks remain:

- may access external network
- may download external CSV
- may write adapted CSV
- may read DB for alignment
- has no trusted dry-run
- is not suitable for direct Codex execution

Because of that, this engine remains an `adapter_candidate`, not a canonical entrypoint.

## 5. Registry Update Summary

`config/acquisition_engines.phase454.json` was updated only for `fetch_and_adapt_euro_leagues`:

- kept `status=adapter_candidate`
- kept `safe_for_ai_default=false`
- kept `canonical_entrypoint=false`
- kept `allowed_next_phase=requires_future_network_dry_run_authorization`
- strengthened `notes` to state that the legacy runtime fetches external CSV, reads DB, and writes adapted output
- strengthened `replacement_plan` to explicitly forbid direct reuse of the legacy downloader runtime
- updated `test_coverage` from `needs_unit_tests` to `gate_covered`

## 6. No-Network / No-DB Test Coverage

Added:

- `tests/unit/fetch_and_adapt_euro_leagues_no_network.test.js`

Coverage added:

- registry contains `fetch_and_adapt_euro_leagues`
- governance state stays `adapter_candidate`
- `safe_for_ai_default=false`
- `canonical_entrypoint=false`
- `allowed_next_phase=requires_future_network_dry_run_authorization`
- acquisition gate engine mode stays blocked
- `would_access_network=false`
- `would_write_db=false`
- `would_execute_engine=false`
- `--commit` stays blocked
- the test does not import or execute the legacy downloader runtime

## 7. Acquisition Gate Blocked Validation

Validated with:

```bash
make data-single-target-network-dry-run \
  ENGINE=fetch_and_adapt_euro_leagues \
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
  ENGINE=fetch_and_adapt_euro_leagues \
  TARGET_MATCH_ID=47_20242025_900002 \
  SOURCE_MANIFEST=tests/fixtures/real_source_manifests/local_sample_history_phase452.json \
  CONFIRM_SINGLE_TARGET_NETWORK=1
```

Result:

- blocked
- no external network
- no DB writes
- no engine execution

## 9. DB Before / After

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

## 10. Next Step Recommendation

Two clean next steps remain:

1. Phase 4.58C: continue with `titan_discovery` or `odds_harvest_pipeline` and add the same no-network / dry-run trust hardening.
2. Phase 4.56A: only after the user provides the six real network dry-run parameters, prepare a runbook without actually touching the network.

## 11. Explicit Non-Execution

Not executed in Phase 4.57C:

- DB writes
- external download
- `curl` / `wget` / `git clone`
- external football data access
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
