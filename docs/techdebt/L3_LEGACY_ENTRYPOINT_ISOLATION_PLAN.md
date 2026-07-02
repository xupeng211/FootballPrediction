# L3 Legacy Entrypoint Isolation Plan

## Status

- Lifecycle: current-state planning document.
- Phase: L3A inventory and planning.
- Runtime behavior changed: no.
- Source files changed: no.
- CI/workflow changed: no.
- Deletion/move/rename: no.

## Why this exists

The repository has accumulated multiple API, CLI, worker, scraper, scheduler,
training, and maintenance entrypoints. Some are active runtime surfaces, some are
legacy or admin-only, and some are test or archive artifacts.

This matters because AI agents can accidentally modify, execute, or test against
legacy entrypoints when a safer guarded path already exists. L3 should reduce
that confusion without starting with deletion or runtime migration.

## Current active entrypoint hypothesis

| Path | Kind | Confidence | Evidence | Notes |
|---|---|---:|---|---|
| `src/main.py` | FastAPI app | high | `Dockerfile` and `docker-compose.yml` run `uvicorn src.main:app`; routes are declared here | Treat as active API entrypoint. |
| `src/api/health.py` | mounted router | high | included from `src/main.py` | Active through `src.main`, not standalone. |
| `src/api/monitoring.py` | mounted router | high | included from `src/main.py` with `/api/v1` prefix | Active through `src.main`, not standalone. |
| `src/api/model_management.py` | mounted router | high | included from `src/main.py` | Active through `src.main`, not standalone. |
| `src/api/v1/endpoints/admin.py` | optional mounted router | medium | imported behind availability guard in `src/main.py` | Owner should confirm intended active status. |
| `Makefile` `data-l1-*` / `data-l2-*` targets | guarded agent command surface | high | AGENTS and Makefile route agents through these targets | Prefer over raw legacy scripts. |
| `scripts/devops/*` and `scripts/ops/ai_workflow_gate.py` | governance entrypoints | high | Production Gate and PR checks call these surfaces | Not product runtime. |

## Candidate legacy entrypoints

| Path | Kind | Reason it may be legacy | Risk | Recommended handling |
|---|---|---|---|---|
| `scripts/ops/run_production.js` | L2 production harvest CLI | AGENTS marks production harvest legacy/admin-only for agents | high | Label legacy/admin-only; require explicit authorization. |
| `scripts/ops/titan_discovery.js` | L1 discovery CLI | AGENTS says agents must not run it directly | high | Keep read-only until safe wrapper ownership is confirmed. |
| `scripts/ops/total_war_pipeline.js` | orchestration CLI | AGENTS lists it as legacy/high-risk | high | Do not modify opportunistically. |
| `scripts/ops/batch_historical_backfill.js` | backfill CLI | AGENTS lists legacy raw backfill as blocked | high | Legacy/admin-only. |
| `scripts/ops/odds_harvest_pipeline.js` | odds harvest CLI | odds ingestion requires separate authorization | high | Keep blocked for agents. |
| `scripts/ops/train_model.py` | training CLI | package script still references it; training is not current task-safe by default | medium | Mark training entrypoint; require explicit training authorization. |
| `scripts/ops/predict_pipeline.py` | prediction CLI | package script still references it; may bypass API boundary | medium | Confirm owner before modifying. |
| `scripts/ops/smelt_all.js` | feature/smelt CLI | package script references it; L3 work is not authorized by default | medium | Treat as L3 runtime, not L3A scope. |
| `scripts/ops/l3_stitch_pipeline.js` | L3 stitch CLI | package script references it | medium | Isolate from docs-only L3A tasks. |
| `scripts/maintenance/*.py` and `*.js` | maintenance CLIs | many have `__main__`, `argparse`, or DB/network naming | medium | Require task-specific approval. |
| `src/api/predictions/predict_router.py` | alternate prediction router | APIRouter exists but current `src.main` owns `/predict` | medium | Needs owner decision before use or edits. |
| `src/ml/**` executable modules | ML helper entrypoints | AST found model/inference modules with `__main__` or runner calls | medium | Treat as runtime only with explicit ML task scope. |

## Test-only / governance / archive entrypoints

| Path | Category | Reason not runtime |
|---|---|---|
| `tests/**` | test-only | may contain `__main__`, fixtures, or local helpers but should not define production runtime. |
| `tests/Z_LEGACY_ARCHIVE_PRE_V4.46.8/**` | test archive | historical test archive; not current runtime. |
| `scripts/devops/**` | governance | CI/static checks, not product runtime entrypoints. |
| `scripts/ops/local_pr_gate_preflight.py` | governance | PR/local gate helper, not business runtime. |
| `archive_vault_2026/**` | archive | historical reference only; read-only unless separately authorized. |
| `.github/**` | workflow configuration | CI orchestration, not application entrypoint. |

## Isolation policy proposal

- Maintain an active entrypoint whitelist, starting with `src/main.py` for API
  runtime and documented Makefile safe targets for agent data workflows.
- Treat legacy entrypoints as read-only unless the PR explicitly authorizes that
  exact path and runtime class.
- Treat `archive_vault_2026/**` as read-only historical material.
- Future PRs that modify legacy entrypoints must state why the active guarded
  path is insufficient.
- Agents must not fix legacy entrypoints while working on unrelated API, docs,
  CI, data, or ML tasks.
- Do not mix L3 entrypoint isolation with L4 API boundary reconciliation.
- Unknown candidates stay blocked for opportunistic edits until an owner
  decision classifies them.

## Proposed L3B tasks

1. L3B-1: confirm active entrypoint whitelist.
2. L3B-2: add docs-only legacy labeling for confirmed legacy/admin-only paths.
3. L3B-3: add optional AI gate wording for legacy entrypoints.
4. L3B-4: evaluate whether any legacy entrypoint can be archived safely.
5. L3B-5: only after evidence, consider deletion/move in a separate PR.

## Explicit non-goals

- No runtime change.
- No API boundary reconciliation.
- No deletion, move, or rename.
- No legacy migration.
- No CI gate change in L3A.
- No scraper, training, prediction, or pipeline execution.

## L3B follow-up

L3B confirms the active entrypoint whitelist in:

- `docs/techdebt/L3_ACTIVE_ENTRYPOINT_WHITELIST.md`
- `docs/_reports/L3B_ACTIVE_ENTRYPOINT_WHITELIST_CONFIRMATION_REPORT.md`

The L3B whitelist turns the L3A candidate inventory into a concrete classification:

- 1 active runtime entrypoint (`src/main.py`)
- 4 active API routers (3 unconditional + 1 conditional)
- 11 active governance/CI entrypoints
- 11 operational guarded target groups
- 18 restricted legacy entrypoints
- 2 test-only path patterns
- 1 archive path pattern
- 7 unknown categories deferred to owner decision

This update is documentation-only and does not enforce policy.

## L3C follow-up

L3C proposes label semantics and guard wording for legacy entrypoint boundaries in:

- `docs/techdebt/L3_LEGACY_LABEL_AND_GUARD_WORDING_PROPOSAL.md`
- `docs/_reports/L3C_LEGACY_LABEL_GUARD_WORDING_PROPOSAL_REPORT.md`

The L3C proposal defines 8 advisory labels (`active-runtime`, `active-api-router`, `active-governance`, `operational-guarded`, `restricted-legacy`, `archive-read-only`, `test-only`, `unknown-owner-decision`) and provides copyable PR body templates and Claude Code prompt guard wording.

This update is documentation-only and does not enforce policy.
