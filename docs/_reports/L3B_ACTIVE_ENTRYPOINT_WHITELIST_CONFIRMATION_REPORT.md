# L3B Active Entrypoint Whitelist Confirmation Report

## Snapshot

- Main head: `7b4e19ce97d93c45bf76a9237bc4f0e9085a9675`
- Main CI run: `28591746865`
- Main CI conclusion: success
- Branch: `techdebt/l3b-active-entrypoint-whitelist-confirmation`
- Scan date: 2026-07-02
- Task type: docs-only

## Source documents

- `docs/techdebt/L3_LEGACY_ENTRYPOINT_ISOLATION_PLAN.md` — L3A planning document (merged in #1685)
- `docs/_reports/L3A_LEGACY_ENTRYPOINT_INVENTORY_REPORT.md` — L3A scan report (merged in #1685)
- `docs/techdebt/L3_ACTIVE_ENTRYPOINT_WHITELIST.md` — L3B whitelist document (this PR)

## Confirmation method

- L3A document review: read the full L3A plan and inventory report.
- Grep-based static recheck: re-ran the L3A scan patterns against current `main` HEAD to confirm no drift since L3A merge.
  - FastAPI/router/route-decorator scan: confirmed `src/main.py` as sole app, 5 router files, `predict_router.py` unmounted.
  - CLI/main-guard scan: confirmed `__main__` and `argparse` patterns across `src/`, `tests/`, `scripts/`.
  - Workflow/Docker/Make/package reference scan: confirmed Dockerfile `CMD`, CI workflow script invocations, `package.json` scripts, and `Makefile` targets.
- `src/main.py` router-mount verification: read lines 1–180 to confirm exact `include_router` calls.
- No runtime execution.
- No Docker run.
- No DB connection.
- No secrets read.
- No scraper, training, or pipeline execution.

## Confirmed whitelist summary

| Category | Count |
|---|---|
| Active runtime entrypoints | 1 (`src/main.py`) |
| Active API router surface | 4 (health, monitoring, model_management, admin-conditional) |
| Active governance / CI entrypoints | 11 (gatekeeper, AI workflow gate, AST check, static quality, local PR gate, PR body check, PR merge preflight, PR post-merge check, helpers/, git hooks, init dev) |
| Operational guarded targets | 11 (pr-gate-local, watch-pr, pr-body-check, pr-merge-preflight, pr-ready-check, pr-post-merge-check, data-l1-*/data-l2-*, data-help, data-check, dev-up/dev-shell, test/lint/format/etc.) |
| Restricted legacy entrypoints | 18 (run_production, titan_discovery, total_war_pipeline, batch_historical_backfill, odds_harvest_pipeline, train_model, predict_pipeline, smelt_all, l3_stitch_pipeline, maintenance/**, predict_router.py, src/ml/**, src/services/**, odds_sniper, seed_fixtures, local_dom_ingestor, csv_bulk_loader, fetch_and_adapt_euro_leagues) |
| Test-only entrypoints | 2 (tests/**, tests/Z_LEGACY_ARCHIVE_PRE_V4.46.8/**) |
| Archive (read-only) | 1 (archive_vault_2026/**) |
| Unknown / needs owner decision | 7 categories (fotmob_*.py probes, check_health.js, sentinel_watch.js, audit_dataset.js, integrity_guard.sh, run_test_suite.js, src/*/ modules with __main__) |

## Key decisions

1. **`src/main.py` confirmed as sole active API entrypoint.** Dockerfile CMD, `docker-compose.yml`, and the FastAPI app definition all converge on this single surface. No other file serves production HTTP traffic.

2. **4 routers confirmed mounted, 1 alternate router confirmed unmounted.** `src/api/health.py`, `src/api/monitoring.py`, `src/api/model_management.py` are unconditionally mounted. `src/api/v1/endpoints/admin.py` is conditionally mounted (try/except ImportError). `src/api/predictions/predict_router.py` is NOT mounted — current `/predict` routes are inline in `src/main.py`.

3. **11 governance/CI entrypoints identified as active.** These are invoked by `.github/workflows/production-gate.yml` or `Makefile` PR gates. They are governance infrastructure, not application runtime.

4. **18 legacy/restricted entrypoints classified.** Based on L3A inventory + static recheck evidence + `AGENTS.md` markings + `package.json` script references. All require explicit user authorization before modification or execution.

5. **7 unknown categories deferred to owner.** These include FotMob probe scripts, operational check/watch/audit tools, the test suite runner, and core/utility modules with `__main__` blocks. Static scan alone cannot determine whether these are active operational tools, one-shot artifacts, or safe self-test blocks.

6. **`src/api/rate_limiter.py` excluded from both active and legacy lists.** The file contains example/doc `FastAPI()` and `@app.get(...)` patterns in docstrings, not a real router. The actual rate limiter is integrated via `init_rate_limiter(app)` in `src/main.py`.

7. **Makefile `data-l1-*` / `data-l2-*` targets classified as operational guarded targets, not active runtime.** Each phase requires explicit invocation and most are gated behind phase-specific authorization. They are not automatic or daemon-driven.

8. **`package.json` scripts are NOT entrypoints themselves** — they are references to the underlying scripts. The underlying scripts (`scripts/ops/*.js`, `scripts/ops/*.py`) are the actual entrypoints and are classified individually.

9. **Archive and legacy test trees are read-only.** `archive_vault_2026/**` and `tests/Z_LEGACY_ARCHIVE_PRE_V4.46.8/**` contain runnable-looking files but are historical reference material.

10. **No enforcement is added in L3B.** This is a documentation-only whitelist. Enforcement (guard wording, CI integration, agent behavior rules) is deferred to L3C+.

## Non-decisions

- **No deletion decision.** No file is deleted, moved, or renamed in this phase.
- **No migration decision.** No legacy entrypoint is migrated to a new location or API surface.
- **No L4 API boundary reconciliation.** The relationship between `src/main.py` inline `/predict` routes and `src/api/predictions/predict_router.py` is noted but not resolved.
- **No CI enforcement decision.** No gate, workflow, or check is modified.
- **No classification of unknown entries.** Seven categories remain `needs owner decision`.
- **No decision on `src/api/v1/endpoints/admin.py` conditional status.** Whether the admin router should be unconditionally active or remain conditional is noted but not decided.

## Report Lifecycle

- **Owner**: TECHDEBT-L3 legacy entrypoint isolation track.
- **Purpose**: bounded L3B confirmation snapshot for active entrypoint whitelist.
- **Source-of-truth relationship**: supports `docs/techdebt/L3_ACTIVE_ENTRYPOINT_WHITELIST.md` (the primary L3B artifact). This report is a companion confirmation artifact, not the source-of-truth itself.
- **Supersession**: may be superseded by a future L3C guard wording or whitelist enforcement proposal. The whitelist document (`L3_ACTIVE_ENTRYPOINT_WHITELIST.md`) is the living reference; this report is a point-in-time snapshot.
- **Cleanup**: no immediate cleanup required. Future cleanup requires explicit user authorization.
- **Raw scan outputs**: temporary `/tmp` artifacts only, not committed.

## Remaining risks

- **Static classification may miss dynamic imports or undocumented runtime uses.** The whitelist is based on grep-level static analysis of the current `main` HEAD. Dynamic `importlib` usage, environment-conditional mounts, or undocumented operational procedures could surface additional entrypoints.
- **Unknown entries require owner decision.** Seven categories could not be confidently classified. Until the owner reviews them, agents must treat them as restricted.
- **This PR does not enforce whitelist policy.** Agents reading this document may still need explicit CLAUDE.md or AGENTS.md updates to change their default behavior.
- **`src/api/v1/endpoints/admin.py` conditional mount** creates ambiguity: is it intended to be always available, or is the conditional guard intentional? Owner should confirm.
- **`src/api/predictions/predict_router.py`** exists as an alternate prediction surface. If it is truly dead code, it could be a future cleanup candidate. If it is a planned migration target, its status should be documented.

## Recommended next step

Do not start automatically.

Recommended:
- Review and merge L3B if CI is green.
- Then decide separately whether to start L3C docs-only legacy label / guard wording proposal.
- Priority owner decisions needed for the 7 unknown categories before L3C can be comprehensive.
