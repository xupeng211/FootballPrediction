# Phase 4.58C Titan Discovery No-Network Hardening

Date: 2026-05-05

## 1. Current Head / Branch

- Starting HEAD: `cbeb856514381e6c03dcd201827b763ea9e3e380`
- Working branch: `test/titan-discovery-no-network-phase458c`
- Base branch: `main`

## 2. Why This Engine Was Chosen

`titan_discovery` was chosen next because it is the clearest current candidate for a future Layer 2 discovery-only adapter. Discovery sits before later acquisition and staging steps, so its trust boundaries should be hardened early.

Phase 4.58C does not execute discovery. It only improves no-network / no-db governance around the legacy runtime.

## 3. Read-Only Source Audit Summary

Read-only inspection of `scripts/ops/titan_discovery.js` and `src/infrastructure/services/DiscoveryService.js` shows:

- `titan_discovery.js` exists and exposes a thin CLI around `DiscoveryService`
- it supports `--dry-run` at CLI parse level, but the flag is not clearly propagated into `DiscoveryService` construction or `service.discover(...)`
- the CLI defaults to `--all` when no scope is provided, so batch discovery is possible by default
- `DiscoveryService` builds a `pg` pool, `BrowserProvider`, `HttpClient`, `FixtureRepository`, and proxy-backed browser/network runtime
- `DiscoveryService._fetchFixtures()` performs API requests and can fall back to webpage extraction
- `DiscoveryService._scanLeague()` persists fixtures through `fixtureRepository.persist(...)`

Relevant risk points found in code:

- CLI `--dry-run` parsed but only used for console warning in `scripts/ops/titan_discovery.js`
- default batch scope when no target is provided in `parseArgs()`
- `new DiscoveryService(...)` in `titan_discovery.js`
- DB pool setup in `DiscoveryService` constructor
- browser/network runtime setup in `BrowserProvider`, `HttpClient`, and extractor wiring
- persistence through `fixtureRepository.persist(...)` in `_scanLeague()`

## 4. Current Risk Assessment

Current risks remain:

- may access external network
- may call `DiscoveryService`
- may use browser / HTTP / proxy-backed runtime
- may write DB through fixture persistence
- may scan multiple leagues by default
- current dry-run trust is insufficient
- CLI flag propagation is not clearly proven end to end
- not suitable for direct Codex execution

Because of that, this engine remains an `adapter_candidate`, not a canonical entrypoint.

## 5. Registry Update Summary

`config/acquisition_engines.phase454.json` was updated only for `titan_discovery`:

- kept `status=adapter_candidate`
- kept `safe_for_ai_default=false`
- kept `canonical_entrypoint=false`
- kept `allowed_next_phase=requires_future_network_dry_run_authorization`
- strengthened `notes` to state that the legacy runtime may touch network, call `DiscoveryService`, and batch-discover leagues
- strengthened `replacement_plan` to explicitly forbid direct reuse of the legacy runtime and require a future Layer 2 discovery-only adapter
- updated `test_coverage` from `needs_unit_tests` to `gate_covered`

## 6. No-Network / No-DB Test Coverage

Added:

- `tests/unit/titan_discovery_no_network.test.js`

Coverage added:

- registry contains `titan_discovery`
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
  ENGINE=titan_discovery \
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
  ENGINE=titan_discovery \
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

1. Phase 4.59C: continue with `odds_harvest_pipeline` and add the same no-network / dry-run trust hardening.
2. Phase 4.56A: only after the user provides the six real network dry-run parameters, prepare a runbook without actually touching the network.

## 11. Explicit Non-Execution

Not executed in Phase 4.58C:

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
