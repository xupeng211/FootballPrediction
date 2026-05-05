# Phase 4.60C Adapter Candidate Readiness Closure

Date: 2026-05-05

## 1. Current Head / Branch

- Starting HEAD: `a730e04e241ae5c1a5f41c2e61e74518b1cdb177`
- Working branch: `docs/adapter-candidate-readiness-closure-phase460c`
- Base branch: `main`

## 2. Why This Closure Was Done

Phase 4.60C closes the current adapter candidate hardening cycle. The goal is to confirm that the three main acquisition adapter candidates are all covered by no-network / no-db gate tests, remain blocked for direct Codex execution, and require future explicit network dry-run authorization before any real acquisition work.

This phase does not modify business logic. It only records readiness, gate behavior, tests, and the future adapter extraction route.

## 3. Adapter Candidate Overview

The three adapter candidates covered by this closure are:

- `fetch_and_adapt_euro_leagues`
- `titan_discovery`
- `odds_harvest_pipeline`

All three remain legacy runtime sources for future adapter extraction. None of them is a canonical entrypoint.

## 4. Current Candidate State

| Candidate                      | status              | safe_for_ai_default | canonical_entrypoint | allowed_next_phase                              | test_coverage  |
| ------------------------------ | ------------------- | ------------------- | -------------------- | ----------------------------------------------- | -------------- |
| `fetch_and_adapt_euro_leagues` | `adapter_candidate` | `false`             | `false`              | `requires_future_network_dry_run_authorization` | `gate_covered` |
| `titan_discovery`              | `adapter_candidate` | `false`             | `false`              | `requires_future_network_dry_run_authorization` | `gate_covered` |
| `odds_harvest_pipeline`        | `adapter_candidate` | `false`             | `false`              | `requires_future_network_dry_run_authorization` | `gate_covered` |

Additional registry observations:

- all three have `phase454_policy=blocked`
- all three have `accesses_network=true`
- `fetch_and_adapt_euro_leagues` has `writes_db=false` but writes adapted output files in legacy runtime
- `titan_discovery` has `writes_db=true`
- `odds_harvest_pipeline` has `writes_db=true`
- all three have `dry_run_trust_level=low`

## 5. Main Risks By Candidate

### fetch_and_adapt_euro_leagues

Current risks:

- external CSV download
- adapted CSV output write
- DB read for alignment
- no safe no-network runtime mode
- source license / provenance must be handled before any real use

Future route:

- extract a source-specific adapter only after source manifest, license review, local staging, and no-network tests are in place

### titan_discovery

Current risks:

- calls `DiscoveryService`
- may use browser or HTTP runtime
- may construct DB-backed discovery services
- may batch-discover leagues
- CLI dry-run trust is not proven end to end

Future route:

- extract a Layer 2 discovery-only adapter with source manifest support, strict target scope, no-db tests, and explicit future network dry-run authorization

### odds_harvest_pipeline

Current risks:

- uses Playwright runtime
- targets OddsPortal odds sources
- creates a `pg` Pool
- performs mapping / odds UPSERT in legacy runtime
- can spawn downstream L3 work
- odds timestamp, closing odds, bookmaker, market, and provenance mistakes can create training leakage

Future route:

- extract a Layer 3 single-target odds acquisition adapter with source manifest support, strict target scope, bookmaker / market / captured_at / source_url / sha256 / provenance capture, and no-db tests

## 6. Gate Verification Results

Validated scaffold-only gates for all three candidates with:

```bash
make data-single-target-network-dry-run \
  ENGINE=<candidate> \
  TARGET_MATCH_ID=47_20242025_900002 \
  SOURCE_MANIFEST=tests/fixtures/real_source_manifests/local_sample_history_phase452.json
```

Observed for each candidate:

- `engine_found=true`
- `would_access_network=false`
- `would_write_db=false`
- `would_execute_engine=false`
- blocked by Phase 4.54 scaffold-only policy
- `no_db_writes`
- `no_external_network`
- `no_engine_execution`

The scaffold gate did not execute any legacy runtime.

## 7. Commit Gate Verification Results

Validated commit gates for all three candidates with:

```bash
make data-single-target-network-commit \
  ENGINE=<candidate> \
  TARGET_MATCH_ID=47_20242025_900002 \
  SOURCE_MANIFEST=tests/fixtures/real_source_manifests/local_sample_history_phase452.json \
  CONFIRM_SINGLE_TARGET_NETWORK=1
```

Observed for each candidate:

- `BLOCKED: acquisition network commit is not wired in Phase 4.54.`
- no DB writes
- no external network
- no engine execution

## 8. Unit Test Verification

Relevant unit tests passed:

- `tests/unit/acquisition_engine_gate.test.js`: 8/8 passed
- `tests/unit/fetch_and_adapt_euro_leagues_no_network.test.js`: 4/4 passed
- `tests/unit/titan_discovery_no_network.test.js`: 4/4 passed
- `tests/unit/odds_harvest_pipeline_no_network.test.js`: 4/4 passed

Full default test gate also passed:

```bash
docker compose -f docker-compose.dev.yml exec -T dev npm test
```

Result:

- key smoke tests passed
- full unit suite passed
- command exited `0`

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

## 10. Conclusion

Phase 4.60C closes the current adapter candidate readiness cycle:

- all three adapter candidates are `gate_covered`
- all three remain `adapter_candidate`
- all three remain unsafe for direct Codex execution
- all three legacy runtimes remain blocked
- acquisition gates report no network, no DB write, and no engine execution
- commit gates remain blocked

Future work must extract adapters from legacy scripts. It must not directly run the old pipelines.

## 11. Next Step Recommendation

Two clean next steps remain:

1. Phase 4.61C: design an adapter extraction plan and choose one candidate to split into pure parser, source manifest handling, and a no-network adapter scaffold.
2. Phase 4.56A: only after the user provides the six real network dry-run parameters, write a runbook first without touching the network.

Without the six real network dry-run parameters, no real network access is allowed.

## 12. Explicit Non-Execution

Not executed in Phase 4.60C:

- DB writes
- external download
- `curl` / `wget` / `git clone`
- external football data access
- external odds data access
- scraping / browser automation for acquisition
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
