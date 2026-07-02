# L3 Active Entrypoint Whitelist

## Status

- Phase: L3B active whitelist confirmation
- Lifecycle: current-state governance document
- Runtime behavior changed: no
- Source files changed: no
- CI/workflow changed: no
- Deletion/move/rename: no
- Enforcement added: no
- L3A inventory basis: `docs/techdebt/L3_LEGACY_ENTRYPOINT_ISOLATION_PLAN.md`
- L3A report basis: `docs/_reports/L3A_LEGACY_ENTRYPOINT_INVENTORY_REPORT.md`

## Purpose

This document defines which entrypoints future AI agents may treat as **active by default**.
It is the L3B output of the TECHDEBT-L3 legacy entrypoint isolation track.

It does **not** enforce policy — it is a documentation-only reference that future phases
(L3C guard wording, eventual enforcement) may build on.

## Whitelist semantics

- **In whitelist**: may be treated as active with normal task authorization.
  Agents may read, analyze, reference, and — when the task scope explicitly permits —
  modify these paths.
- **Not in whitelist**: must **not** be modified, run, migrated, or used as a runtime
  source-of-truth without explicit user authorization.
- **Legacy/restricted** does **not** mean deleted. These files remain in the repository
  and are read-only by default for agents.
- **Unknown** means the classification needs an owner decision. Agents must treat
  unknown entries as restricted until classified.
- **Test-only** entries may be read and referenced but do not define production runtime
  behavior.
- **This is documentation-only** and does not enforce policy. It informs agent behavior
  through CLAUDE.md, AGENTS.md, and future guard wording.

---

## Active runtime entrypoints

These are the production runtime surfaces that serve the application.

| Path | Kind | Status | Evidence | Notes |
|---|---|---|---|---|
| `src/main.py` | FastAPI application | **active** | `Dockerfile` line 119: `CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]`; `docker-compose.yml` references `uvicorn src.main:app`; contains `app = FastAPI(...)` at line 109; has `if __name__ == "__main__"` at line 361 | Sole production API entrypoint. All runtime API traffic flows through this file. |

Count: **1** active runtime entrypoint.

---

## Active API router surface

These are the API routers that `src/main.py` mounts at application startup.
Only routers with confirmed `app.include_router(...)` calls are listed.

| Path | Mounted by | Status | Evidence | Notes |
|---|---|---|---|---|
| `src/api/health.py` | `src/main.py` line 136 | **active** | `app.include_router(health_router)` — unconditional mount | Health-check endpoints. |
| `src/api/monitoring.py` | `src/main.py` line 137 | **active** | `app.include_router(monitoring_router, prefix="/api/v1")` — unconditional mount | Monitoring/metrics endpoints under `/api/v1`. |
| `src/api/model_management.py` | `src/main.py` line 138 | **active** | `app.include_router(model_management_router)` — unconditional mount | Model reload/info/list endpoints. |
| `src/api/v1/endpoints/admin.py` | `src/main.py` lines 142–144 | **conditional active** | `app.include_router(admin_router, prefix="/api/v1")` inside `try/except ImportError` guard | Admin endpoints (retrain, model switch/rollback, system health). Mounted when the import succeeds; skipped silently on ImportError. |

Count: **4** API routers (3 unconditional + 1 conditional).

### Routers NOT mounted

The following files define `APIRouter` instances but are **not** included by `src/main.py`:

| Path | Reason not active | Classification |
|---|---|---|
| `src/api/predictions/predict_router.py` | Defines `router = APIRouter(...)` at line 40 with prediction endpoints, but `src/main.py` does **not** import or mount it. Current `/predict` is owned by `src/main.py` inline routes (lines 244, 304). | **Legacy candidate** — see Restricted Legacy section. |
| `src/api/rate_limiter.py` | Contains example/doc `app = FastAPI()` and `@app.get(...)` decorators at lines 20, 300, 306, 312 inside docstrings/examples — not a real router. The actual rate limiter is used via `init_rate_limiter(app)` at `src/main.py` line 119. | **Not a router** — utility module with inline examples. |

---

## Active governance / CI entrypoints

These are scripts that the CI/CD pipeline (Production Gate) or local PR gates invoke.
They are not application runtime entrypoints but are active in the governance layer.

| Path | Used by | Status | Evidence | Notes |
|---|---|---|---|---|
| `scripts/devops/gatekeeper.sh` | `.github/workflows/production-gate.yml` line 138 | **active** | `bash scripts/devops/gatekeeper.sh --mode="${GATEKEEPER_CI_MODE}"` | Primary CI gate entrypoint. |
| `scripts/ops/ai_workflow_gate.py` | `.github/workflows/production-gate.yml` lines 150, 153, 159 | **active** | `python3 scripts/ops/ai_workflow_gate.py --pr-body-file ...` | AI Workflow Gate (P0 risk checks). Has `argparse` CLI and `if __name__ == "__main__"`. |
| `scripts/devops/check_python_ast_utf8.py` | `.github/workflows/production-gate.yml` line 166 | **active** | `python3 scripts/devops/check_python_ast_utf8.py` | Validates Python files are valid UTF-8 and parseable AST. |
| `scripts/devops/static_quality_changed_lines.py` | `Makefile` line 201 (`pr-gate-local`) → `scripts/ops/local_pr_gate_preflight.py` | **active** | Referenced by local PR gate preflight for mypy changed-line diagnostics | Mypy changed-line false-positive filter. |
| `scripts/ops/local_pr_gate_preflight.py` | `Makefile` line 201 (`pr-gate-local`) | **active** | `make pr-gate-local` → `python3 scripts/ops/local_pr_gate_preflight.py` | Local PR Gate preflight runner. Has `argparse` CLI. |
| `scripts/devops/pr_body_check.py` | `Makefile` line 248 (`pr-body-check`) | **active** | Referenced by `make pr-body-check` | PR body validation. |
| `scripts/devops/pr_merge_preflight.py` | `Makefile` line 214 (`pr-merge-preflight`) | **active** | Referenced by `make pr-merge-preflight` | Merge preflight evidence check. |
| `scripts/devops/pr_post_merge_check.py` | `Makefile` line 278 (`pr-post-merge-check`) | **active** | Referenced by `make pr-post-merge-check` | Post-merge cleanup gate. |
| `scripts/ops/helpers/` directory | CI + local gates (various) | **active** | `scripts/ops/helpers/` contains `ai_workflow_gate.py` dependencies: `pr_authorization_matrix.py`, `pr_authorization_rules.py`, `dangerous_file_change_check.py`, `db_write_guard*.js`, `db_write_guard_advisory_check.py`, `python_db_write_guard.py`, `python_db_write_enforcement_check.py`, `sql_migration_policy_enforcement_check.py`, `governance_p1_checks.py`, `agent_workflow_hardening_checks.py`, `garbage_prevention_checks.py`, `section_content_quality.py`, `git_change_helpers.py`, `repoHygiene.js`, and others | Gate helper library. All files are governance infrastructure, not application runtime. |
| `scripts/devops/install_git_hooks.sh` | Developer setup | **active** | Referenced by `package.json` `init:hooks` script | Git hooks installation. |
| `scripts/devops/init_dev.sh` | Developer setup | **active** | Referenced by `package.json` `init:dev` script | Development environment initialization. |

Count: **11** active governance/CI entrypoints (including the `scripts/ops/helpers/` directory as one logical unit).

---

## Operational guarded targets

These are `Makefile` targets that agents may invoke under specific guard conditions.
They are not automatic runtime entrypoints — each requires explicit invocation and
most are gated behind phase-specific authorization.

| Path or target | Category | Status | Evidence | Notes |
|---|---|---|---|---|
| `make pr-gate-local` | local PR validation | **active guarded** | `Makefile` lines 201–211 | Primary local pre-push validation. Safe: static analysis only in default mode. |
| `make watch-pr` | CI monitoring | **active guarded** | `Makefile` lines 234–245 | Unified CI watch command. Safe: read-only `gh` queries. |
| `make pr-body-check` | PR validation | **active guarded** | `Makefile` lines 248–252 | PR body + Gate evidence check. Safe: read-only. |
| `make pr-merge-preflight` | merge safety | **active guarded** | `Makefile` lines 214–219 | Pre-merge evidence check. Safe: read-only. |
| `make pr-ready-check` | merge readiness | **active guarded** | `Makefile` lines 221–231 | Combined body + merge preflight. Safe: read-only. |
| `make pr-post-merge-check` | post-merge cleanup | **active guarded** | `Makefile` lines 278–297 | Post-merge verification. Safe: read-only until CONFIRM_CLEANUP set. |
| `make data-l1-*` / `make data-l2-*` | data harvesting | **guarded** | `Makefile` lines 408–1030 | Multi-phase guarded data pipeline. Each phase requires explicit authorization. Most phases are read-only/preview; write phases are explicitly gated. |
| `make data-help` | data policy | **active guarded** | `Makefile` lines 408–420 | Safe data harvesting entrypoint policy display. Safe: read-only. |
| `make data-check` | data environment | **active guarded** | `Makefile` lines 620–628 | Read-only data environment check. Safe: no network, no DB, no write. |
| `make dev-up` / `make dev-shell` | dev environment | **active** | `Makefile` lines 384–396 | Containerized dev environment lifecycle. |
| `make test` / `make test-unit` / `make lint` / `make format` / `make security` / `make verify` | quality | **active** | `Makefile` lines 161–185 | Standard quality checks. Safe: local static/runtime checks in container. |

Count: **11** operational guarded target groups.

---

## Restricted legacy entrypoints

These entrypoints exist in the repository but must **not** be modified, run, or
treated as active runtime surfaces without explicit user authorization.

| Path | Category | Restriction | Reason | Required authorization before change |
|---|---|---|---|---|
| `scripts/ops/run_production.js` | L2 production harvest CLI | **do not run, do not modify** | `AGENTS.md` marks it deprecated/admin-only for agents; `package.json` `start` and `harvest:production` scripts reference it | Explicit production harvest authorization |
| `scripts/ops/titan_discovery.js` | L1 discovery CLI | **do not run, do not modify** | `AGENTS.md` says agents must not run it directly; triggers network discovery | Explicit discovery authorization + safe wrapper |
| `scripts/ops/total_war_pipeline.js` | orchestration CLI | **do not run, do not modify** | `AGENTS.md` lists it as legacy/high-risk; `package.json` `titan:total-war` references it | Explicit orchestration authorization |
| `scripts/ops/batch_historical_backfill.js` | backfill CLI | **do not run, do not modify** | `AGENTS.md` lists legacy raw backfill as blocked | Explicit backfill authorization |
| `scripts/ops/odds_harvest_pipeline.js` | odds harvest CLI | **do not run, do not modify** | Odds ingestion requires separate authorization; `package.json` `odds:harvest` references it | Explicit odds harvesting authorization |
| `scripts/ops/train_model.py` | training CLI | **do not run without training authorization** | `package.json` `train`, `train:fast`, `train:deep` scripts reference it; has `argparse` CLI; training is blocked by default | Explicit training authorization |
| `scripts/ops/predict_pipeline.py` | prediction CLI | **do not run without prediction authorization** | `package.json` `predict`, `predict:dry`, `predict:json` scripts reference it; has `argparse` CLI; may bypass API boundary | Explicit prediction authorization |
| `scripts/ops/smelt_all.js` | feature/smelt CLI | **do not run, do not modify** | `package.json` `smelt` script references it; L3 work not authorized by default | Explicit L3/smelt authorization |
| `scripts/ops/l3_stitch_pipeline.js` | L3 stitch CLI | **do not run, do not modify** | `package.json` `l3:stitch` script references it | Explicit L3 stitch authorization |
| `scripts/maintenance/**` | maintenance CLIs | **do not run without maintenance authorization** | Multiple scripts with `__main__`, `argparse`, or DB/network naming; task-scoped approval required | Task-specific maintenance approval |
| `src/api/predictions/predict_router.py` | alternate prediction router | **do not modify, do not mount** | Defines `APIRouter` with prediction endpoints but is NOT mounted by `src/main.py`; current `/predict` is owned by `src/main.py` inline routes | Owner decision on whether to deprecate, merge, or activate |
| `src/ml/**` executable modules | ML helper entrypoints | **do not run without ML task scope** | Multiple modules (`dataset_generator.py`, `engine.py`, `xgboost_classifier.py`, etc.) have `if __name__ == "__main__"` blocks for standalone execution | Explicit ML task authorization |
| `src/services/**` modules with `__main__` | service self-tests | **do not run without service task scope** | `event_bus.py`, `league_router.py`, `service_container.py`, `match_aligner.py`, `odds_filter.py` have `__main__` or `argparse` for local testing | Task-specific service authorization |
| `scripts/ops/odds_sniper.js` | odds sniper CLI | **do not run, do not modify** | `package.json` `odds:sniper` references it; odds tools are blocked | Explicit odds authorization |
| `scripts/ops/seed_fixtures.js` | seed fixtures CLI | **do not run without data authorization** | `package.json` `seed`, `seed:all` scripts reference it | Explicit data seeding authorization |
| `scripts/ops/local_dom_ingestor.js` | local DOM ingestor | **do not run, do not modify** | `package.json` `etl:local-dom` references it | Explicit ETL authorization |
| `scripts/ops/csv_bulk_loader.js` | CSV bulk loader | **do not run, do not modify** | `package.json` `etl:csv-bulk` references it | Explicit ETL authorization |
| `scripts/ops/fetch_and_adapt_euro_leagues.js` | Euro leagues fetch | **do not run, do not modify** | `package.json` `etl:fetch-epl`, `etl:fetch-euro` reference it; triggers network fetch | Explicit fetch authorization |

Count: **18** restricted legacy entrypoints.

---

## Test-only entrypoints

These paths contain test code only. They do not define production runtime behavior.

| Path pattern | Reason |
|---|---|
| `tests/**` | All test files — unit, integration, smoke, load, and legacy archive tests. May contain `__main__`, fixtures, or API test clients but are not production runtime. |
| `tests/Z_LEGACY_ARCHIVE_PRE_V4.46.8/**` | Historical test archive. Contains runnable-looking test files (`run_benchmarks.py`, `load_test_pipeline.py`, `coverage_analyzer.py`, etc.) but is pre-V4.46.8 legacy. Read-only. |

Count: **2** test-only path patterns.

---

## Archive (read-only historical)

| Path pattern | Reason |
|---|---|
| `archive_vault_2026/**` | Historical reference material. Read-only unless separately authorized for archive maintenance. |

Count: **1** archive path pattern.

---

## Unknown / needs owner decision

These entries could not be confidently classified from static evidence alone.

| Path or pattern | Why unknown | Proposed decision owner | Recommended next step |
|---|---|---|---|
| `scripts/ops/fotmob_*.py` (multiple files) | ~12 FotMob investigation/probe scripts with `argparse` CLIs and `__main__` guards. Some are `_no_write` variants, others are `_dry_run` or `_check` variants. Their operational status (active investigation tool vs. one-shot artifact) is unclear without owner input. | @xupeng211 | Owner review: classify each as active investigation tool, one-shot report artifact, or legacy. |
| `scripts/ops/check_health.js` | `package.json` `titan:check` references it. Not listed in AGENTS.md as blocked, but unclear if it is an active operational check or legacy. | @xupeng211 | Owner decision: active monitoring or legacy. |
| `scripts/ops/sentinel_watch.js` | `package.json` `titan:watch` references it. Watch/monitor semantics unclear from static scan. | @xupeng211 | Owner decision: active monitoring or legacy. |
| `scripts/ops/audit_dataset.js` | `package.json` `titan:audit` references it. Audit semantics unclear — could be read-only analysis or could touch data. | @xupeng211 | Owner decision: read-only audit or data-mutating. |
| `scripts/maintenance/integrity_guard.sh` | `package.json` `status` script references it. Name suggests integrity checking, but implementation is unverified. | @xupeng211 | Owner decision: active integrity guard or legacy. |
| `scripts/test/run_test_suite.js` | `package.json` `test`, `test:unit`, `test:affected`, `test:integration`, `test:coverage` reference it. Test runner — likely active, but verify it is the canonical test entrypoint. | @xupeng211 | Confirm as active test infrastructure or legacy. |
| `src/core/**`, `src/utils/**`, `src/schemas/**` modules with `__main__` | Several core/utility modules have `if __name__ == "__main__"` blocks (`environment_detector.py`, `environment_validator.py`, `path_manager.py`, `types.py`, `safe_eval.py`, `typed_matcher.py`, `notifier.py`, `team_alias.py`, `match_features.py`). These appear to be self-test/demo blocks, not runtime entrypoints, but static scan alone cannot confirm. | @xupeng211 | Owner review: confirm as self-test-only, no runtime dependency. |

Count: **7** unknown categories.

---

## Future change rules

- Future PRs **may** modify active whitelist paths only if the task explicitly authorizes them.
- Future PRs **may not** modify restricted legacy entrypoints without explicit user authorization.
- Future PRs **may not** mix L3 entrypoint isolation with L4 API boundary reconciliation.
- Future PRs **may not** delete, move, or rename entrypoints without a dedicated deletion/migration PR.
- Future PRs **may not** mount `src/api/predictions/predict_router.py` without an owner decision and explicit task authorization.
- Archive paths (`archive_vault_2026/**`, `tests/Z_LEGACY_ARCHIVE_PRE_V4.46.8/**`) remain read-only by default.
- Unknown entries remain restricted until an owner decision classifies them.
- These rules are **documentation-only** in L3B. Enforcement may be added in a future phase (L3C+).

## Relationship to L3A

- `docs/techdebt/L3_LEGACY_ENTRYPOINT_ISOLATION_PLAN.md` — L3A planning document that established the inventory and classification framework.
- `docs/_reports/L3A_LEGACY_ENTRYPOINT_INVENTORY_REPORT.md` — L3A scan report with raw grep/AST evidence.
- This document (L3B) turns the L3A candidate inventory into a concrete whitelist.

## References

- `AGENTS.md` — agent workflow hardening rules and legacy entrypoint markings.
- `CLAUDE.md` — project instructions and safety discipline.
- `.github/workflows/production-gate.yml` — CI pipeline definition.
- `Dockerfile` — production image entrypoint definition.
- `Makefile` — operational targets and guard definitions.
- `package.json` — Node.js script references.

## Next recommended task

Do not start automatically.

Recommended next task only after user confirmation:

- **L3C**: docs-only legacy label / guard wording proposal, building on this whitelist.
- Do not implement enforcement until separately authorized.
- Do not start L4 API boundary reconciliation.

## L3C follow-up

L3C proposes label semantics and guard wording for legacy entrypoint boundaries in:

- `docs/techdebt/L3_LEGACY_LABEL_AND_GUARD_WORDING_PROPOSAL.md`
- `docs/_reports/L3C_LEGACY_LABEL_GUARD_WORDING_PROPOSAL_REPORT.md`

The L3C proposal builds on this whitelist by defining 8 advisory labels and providing copyable PR body templates and Claude Code prompt guard wording. It does not add CI enforcement.

## L3D follow-up

L3D proposes review ownership and future CODEOWNERS wording in:

- `docs/techdebt/L3_REVIEW_OWNERSHIP_AND_CODEOWNERS_WORDING_PROPOSAL.md`
- `docs/_reports/L3D_REVIEW_OWNERSHIP_CODEOWNERS_WORDING_PROPOSAL_REPORT.md`

The L3D proposal maps each L3 label to a review ownership area, provides a reviewer checklist, and drafts future CODEOWNERS placeholder structure. It does not implement CODEOWNERS or enforcement.
