# Project Status

- lifecycle: current-state
- owner: project governance

Last updated: 2026-06-21

## Current baseline

- `main` includes PR #1463 (P0 AI Workflow Gate CI enforcement).
- `main` includes PR #1464 (local CI gatekeeper entrypoint).
- `main` includes PR #1567 (authoritative workflow enforcement dry-run).
- Remote GitHub Actions `production-gate.yml` is the final CI authority.
- Local `make ci-local-pr` is a pre-push helper, not a full replacement for remote CI.
- AI workflow governance rules are enforced by:
  - `scripts/ops/ai_workflow_gate.py` (CI-enforced workflow and documentation checks)
  - `scripts/devops/gatekeeper.sh` (CI-enforced, multi-phase)
  - `scripts/ops/documentation_governance_check.py` (standalone checker)
  - `.github/pull_request_template.md` (mandatory PR structure)
  - `docs/CODEX_WORKFLOW.md` (Codex task rules)
  - `docs/DOCUMENTATION_GOVERNANCE.md` (doc lifecycle rules)

## Current operating rules

- One task / one branch / one PR.
- Do not work directly on `main`.
- Do not mix governance changes with runtime business code (CI-enforced).
- Do not start automatically. Recommended next task only after user confirmation (CI-enforced).
- PR body must include all mandatory sections: Scope, Documentation Impact, Safety Impact,
  Validation, CI Gate Scope, No-deletion/move/rename confirmation, Rollback Plan,
  Next Recommended Task.
- CI Gate Scope must state what validation proves and does not prove.
- If a PR adds or modifies `docs/_reports/*.md`, it must update an
  authoritative doc or give a concrete source-of-truth no-update reason in the
  PR body.

## Current allowed work

- Small docs-only source-of-truth updates (like this file).
- Read-only audits.
- Small, scoped CI/governance fixes that do not touch runtime code.
- Future FotMob/data work only after explicit user confirmation and under
  read-only/no-write constraints.

## Current blocked work

- DB write and schema migration.
- Raw data write (`raw_match_data`).
- Real scraper and browser automation.
- Large archive moves (delete/move/rename of historical files).
- Automatic next-task execution.
- Mixed governance + business-code PRs.
- Implementation PRs that substitute reports/manifests/tests for runtime behavior change.
- Consecutive governance-only PRs without explicit human confirmation.
- Formal model training.
- Data expansion / large-scale raw acquisition.

## Current source-of-truth docs

| Doc | Status |
|---|---|
| `docs/PROJECT_STATUS.md` | active (this file) |
| `docs/DATA_SOURCE_STRATEGY.md` | active (created alongside this file) |
| `docs/CODEX_WORKFLOW.md` | active |
| `docs/DOCUMENTATION_GOVERNANCE.md` | active |
| `docs/data/FOTMOB_CURRENT_STATE.md` | active — read for FotMob state |
| `docs/AGENT_WORKFLOW.md` | active |
| `docs/TESTING_GUIDE.md` | active — needs provenance review |
| `docs/GITHUB_ACTIONS_AUDIT_REPORT.md` | evidence/needs_update — stale CI references |

## Current technical debt posture

- `docs/_reports/` contains 434 historical report files as of the
  authoritative workflow enforcement dry-run.
- `docs/_manifests/` contains 171 historical manifest files.
- These are archived evidence; they should not be read as current truth.
- Bulk archive moves are planned but not yet executed.
- Stale docs (`GITHUB_ACTIONS_AUDIT_REPORT.md`, `TESTING_GUIDE.md`) should be
  reviewed and marked or superseded in small scoped PRs.
- Technical debt remains high enough to block data expansion and formal
  training. Current P0 debt includes DB write safety, cutoff strategy, training
  eligibility, and schema/init alignment.

## Current training and expansion posture

- Minimal training loop: connected for smoke-level validation only.
- Formal training: blocked.
- Formal cohort candidates / smoke-level candidates: 58.
- Formal candidates with odds: 0.
- Formal training must not start until eligibility, odds, cutoff-time policy,
  and DB write safety blockers are resolved.
- Data expansion: blocked by P0 technical debt and raw/write governance.
- DB write safety: blocked / fix pending. The P0 DB write safety dry-run found
  122 production DB-write risk files, including 66 P0 files and 110 files with
  no safety gate. SC-002 is still unresolved.
- Authoritative document backflow: fix phase1 starts enforcement through the PR
  template, AI Workflow Gate, Documentation Governance, Codex Workflow, and this
  current-state update.

## Recent dry-run conclusions now reflected here

| Dry-run | Current conclusion |
|---|---|
| `formal_training_cohort_inventory_dry_run` | Formal training remains blocked; only 58 smoke-level candidates were found and formal candidates with odds = 0. |
| `technical_debt_workflow_audit_dry_run` | P0 technical debt blocks data expansion and formal training; priority debt is DB write safety, cutoff strategy, training eligibility, and schema/init alignment. |
| `p0_db_write_safety_gate_dry_run` | DB write safety remains blocked; 122 production DB-write risk files were found, P0 = 66, 110 lack gates, SC-002 remains unfixed. |
| `authoritative_workflow_enforcement_dry_run` | The project already has authoritative docs, but `_reports` has overgrown and AI agents were not forced to maintain current-state docs. |

## Current FotMob status

- FotMob data ingestion is blocked. See `docs/data/FOTMOB_CURRENT_STATE.md` for details.
- `raw_write_ready_count` is 0.
  **(Superseded 2026-06-11: retained raw storage has moved forward. 4 real FotMob raw
  payloads exist in `raw_match_data` with `data_version=fotmob_live_v1`, audited
  4/4 parseable, sha valid, inner matchId ok, 0 errors, 0 warnings. See
  `docs/data/FOTMOB_RETAINED_RAW_STAGE_STATUS.md`.)**
- No DB write, raw write, browser automation, or network data collection is authorized.
  **(Partial exception: the 4 retained raw rows above were written under explicit
  authorization in #1485 and #1486.)**
- Parser, schema, fixture, and validation assets from #1454 are safe to reuse as
  offline references only.

## Next recommended sequence

1. Complete `p0_db_write_safety_gate_fix_phase1`.
2. Keep formal training and data expansion blocked until DB write safety,
   cutoff strategy, training eligibility, and schema/init alignment are handled.
3. Do not start model training, data expansion, or raw-write work automatically.
4. Do not start automatically. Recommended next task only after user confirmation.
