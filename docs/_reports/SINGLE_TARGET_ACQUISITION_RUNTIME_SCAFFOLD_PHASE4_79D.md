# Phase 4.79D: Single-Target Acquisition Runtime Scaffold

**Date**: 2026-05-10
**Status**: Complete (scaffold-only)
**Previous phase**: Phase 4.78D — Single-Target Acquisition Runtime Design
**Next recommended phase**: Phase 4.80D or explicit user-authorized network dry-run runbook

---

## 1. Executive Summary

Phase 4.79D is a **scaffold-only** phase. It translates the Phase 4.78D design into a
concrete, validated, test-covered scaffold command that performs:

1. Parameter validation
2. Target scope validation
3. Engine family validation
4. Authorization field validation
5. Runtime plan preview (JSON output)
6. Guardrail summary

The scaffold **does not** access the network, launch a browser, use proxy, write to DB,
write to staging, execute any acquisition engine, import legacy runtime modules, or
spawn child processes.

All `would_*` fields in the output are hardcoded to `false`. The `commit_gate` is
hardcoded to `"blocked"`. Even if all authorization fields are set to `"yes"`, the
scaffold remains non-executing.

---

## 2. Implemented Command

### Script

```
scripts/ops/single_target_acquisition_runtime_scaffold.js
```

### Makefile Targets

```
make data-single-target-acquisition-runtime-scaffold    (scaffold-only, Phase 4.79D)
make data-single-target-acquisition-runtime-commit      (blocked, Phase 4.79D)
```

---

## 3. Parameter Contract

| Parameter                         | Required                             | Allowed                          | Forbidden                                                                                                                                                       | Default |
| --------------------------------- | ------------------------------------ | -------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| `--target-source`                 | yes                                  | e.g. `fotmob`                    | empty                                                                                                                                                           | none    |
| `--target-engine-family`          | yes                                  | `titan_discovery`                | `run_production`, `recon_scanner`, `odds_harvest_pipeline`, `total_war_pipeline`, `titan_marathon`, `batch_historical_backfill`, `fetch_and_adapt_euro_leagues` | none    |
| `--target-scope-type`             | yes                                  | `match_id`, `league_season_date` | `all`, `bulk`, `production`, `league`, `season`, `full_source`                                                                                                  | none    |
| `--target-match-id`               | when `scope_type=match_id`           | any non-empty string             | empty                                                                                                                                                           | none    |
| `--target-league`                 | when `scope_type=league_season_date` | e.g. `EPL`                       | empty                                                                                                                                                           | none    |
| `--target-season`                 | when `scope_type=league_season_date` | e.g. `2025-2026`                 | empty                                                                                                                                                           | none    |
| `--target-date`                   | when `scope_type=league_season_date` | ISO date `YYYY-MM-DD`            | empty                                                                                                                                                           | none    |
| `--terms-approval`                | yes                                  | `yes`, `no`                      | anything else                                                                                                                                                   | `no`    |
| `--network-dry-run-authorization` | yes                                  | `yes`, `no`                      | anything else                                                                                                                                                   | `no`    |
| `--allow-browser-runtime`         | yes                                  | `yes`, `no`                      | anything else                                                                                                                                                   | `no`    |
| `--allow-proxy-runtime`           | yes                                  | `yes`, `no`                      | anything else                                                                                                                                                   | `no`    |
| `--allow-external-network`        | yes                                  | `yes`, `no`                      | anything else                                                                                                                                                   | `no`    |
| `--allow-staging-write`           | yes                                  | `yes`, `no`                      | anything else                                                                                                                                                   | `no`    |
| `--confirm-single-target-scope`   | yes                                  | `yes` (must be `yes`)            | `no`, anything else                                                                                                                                             | `no`    |
| `--commit`                        | n/a                                  | n/a                              | always blocked                                                                                                                                                  | blocked |

---

## 4. Guardrail Output

All `would_*` fields are hardcoded to `false` in scaffold output:

```json
{
    "would_execute_legacy_titan_discovery": false,
    "would_execute_engine": false,
    "would_access_network": false,
    "would_launch_browser": false,
    "would_use_proxy": false,
    "would_write_staging": false,
    "would_create_staging_directory": false,
    "would_write_source_manifest": false,
    "would_write_db": false,
    "would_train": false,
    "would_predict": false,
    "would_bulk_harvest": false,
    "would_spawn_child_process": false,
    "commit_gate": "blocked"
}
```

Guardrails enforced:

1. `no_external_network`
2. `no_browser_automation`
3. `no_proxy_runtime_execution`
4. `no_db_writes`
5. `no_staging_writes`
6. `no_legacy_runtime`
7. `no_training`
8. `no_prediction`

---

## 5. Blocked Commit Behavior

The `--commit` flag is unconditionally blocked. The scaffold exits non-zero with:

```
BLOCKED: single-target acquisition runtime commit/execution is not wired in Phase 4.79D.
```

The Makefile `data-single-target-acquisition-runtime-commit` target is likewise blocked
even when `CONFIRM_SINGLE_TARGET_ACQUISITION_RUNTIME=1`.

---

## 6. Why titan_discovery Legacy Runtime Remains Blocked

The legacy `scripts/ops/titan_discovery.js` entrypoint remains blocked because:

1. The current `--dry-run` flag is not propagated end-to-end to the service layer
2. It may construct a DB pool via `DiscoveryService` constructor
3. It may construct browser/proxy/network runtime via service wiring
4. `FixtureRepository.persist` can write to `matches` table
5. It defaults to all P0 leagues when no target is provided
6. CLI flag propagation is not proven with no-network/no-db tests

The `titan_discovery` engine family is registered as `adapter_candidate` in
`config/acquisition_engines.phase454.json`, not as a canonical runtime. A future
extracted discovery-only adapter must prove it does not write DB, launch browser,
or access network before it can be used.

---

## 7. Test Coverage

Tests: `tests/unit/single_target_acquisition_runtime_scaffold.test.js`

Coverage includes validation for:

- Missing `target_source` → exit non-zero
- Missing `target_engine_family` → exit non-zero
- Non-`titan_discovery` engine family → exit non-zero
- Legacy engines (`run_production`, `recon_scanner`, `odds_harvest_pipeline`) → blocked
- Forbidden scope types (`all`, `bulk`, `production`) → blocked
- Missing scope-dependent fields → exit non-zero
- `confirm_single_target_scope=no` → exit non-zero
- Invalid yes/no values → exit non-zero
- Valid `match_id` scaffold → exit 0, correct JSON output
- Valid `league_season_date` scaffold → exit 0, correct JSON output
- All `would_*` fields are `false` even when all authorization fields are `yes`
- `--commit` → exit non-zero
- Source code audit: no imports of `titan_discovery`, `DiscoveryService`, `pg`, `redis`, `playwright`, `axios`, `http`, `https`, `net`, `fs` write methods, `child_process`

The tests prove zero runtime side effects through both unit tests on exported functions
and subprocess integration tests.

---

## 8. Recommended Next Phase

**Phase 4.80D**: Single-target acquisition staging artifact schema validator.

This would define and validate:

- Staging artifact JSON schema
- Source manifest JSON schema
- Provenance field requirements
- sha256/hash verification
- Row/object count requirements
- Still no network, no DB writes, no staging writes

Alternatively:

**Phase 4.56A**: User provides explicit real source, engine, target, manifest, terms
approval, and network authorization before executing a real network dry-run runbook.

---

## 9. Explicit Non-Execution Confirmation

The following were **not** performed during Phase 4.79D:

- DB writes (INSERT/UPDATE/DELETE/CREATE/ALTER/DROP/TRUNCATE/COPY)
- Non-SELECT DB SQL
- External downloads (curl/wget/git clone)
- External football data access
- External odds data access
- Scraping
- Browser automation
- Proxy runtime execution
- Harvest / ingest
- Batch backfill
- Network dry-run execution
- Bulk harvest
- Staging artifact write
- Staging directory creation
- Source manifest write
- Packet file write
- `pg_dump` / `pg_restore`
- Model training
- Real prediction execution
- Model artifact loading
- Docker volume cleanup (`docker system prune`, `docker volume prune`)
- Force push
- `git fetch --all`
- `git pull`
- `rm -rf`
- File deletion
- Coverage threshold modification
- Test skipping
- Test deletion
- Gatekeeper bypass
