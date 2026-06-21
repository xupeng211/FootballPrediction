# Authoritative Workflow Enforcement Dry Run

- lifecycle: phase-artifact
- date: 2026-06-21
- branch: `chore/authoritative-workflow-enforcement-dry-run`
- script: `scripts/ops/authoritative_workflow_enforcement_dry_run.js`
- test: `tests/unit/authoritative_workflow_enforcement_dry_run.test.js`
- authoritative backlinks: `docs/PROJECT_STATUS.md`, `docs/DOCUMENTATION_GOVERNANCE.md`, `docs/CODEX_WORKFLOW.md`

## Safety

- Static scan only.
- No network, no database connection, no database write, no raw write.
- No data acquisition, no model training, no model artifact generation.
- No business logic, data collection logic, or training logic changed.
- No file deletion, move, rename, or new authoritative document entrypoint.

## Summary Answers

| Question | Answer |
| --- | --- |
| Project already has authoritative docs? | Yes. |
| Current authoritative entrypoints? | `PROJECT_STATUS`, `DOCUMENTATION_GOVERNANCE`, `CODEX_WORKFLOW`, `AGENT_WORKFLOW`, PR template, `AGENTS.md`, `CLAUDE.md`, `DATA_SOURCE_STRATEGY`, `docs/data/FOTMOB_CURRENT_STATE.md`. |
| Which docs are stale? | `PROJECT_STATUS`, `DOCUMENTATION_GOVERNANCE`, `CODEX_WORKFLOW`, `CHANGELOG`, `README.md`. |
| Is `docs/_reports` overgrown? | Yes: 434 report files after this report, about 57k lines; manifests remain 171. |
| Recent 3 dry-run conclusions reflected? | No. All 3 are missing from `PROJECT_STATUS.md`. |
| Are agents clearly forced to maintain authoritative docs? | Partially. Rules prefer source-of-truth updates, but completion is not hard-gated. |
| PR template forces authoritative-doc update status? | No. It has documentation/debt fields but no explicit authoritative-doc status. |
| Gatekeeper/CI blocks report-only PR without source-of-truth update? | No. Current gate counts doc sprawl but does not enforce backflow. |
| Add CI check? | Yes. |
| Modify PR template? | Yes. |
| Modify `CODEX_WORKFLOW.md`? | Yes. |
| Modify `DOCUMENTATION_GOVERNANCE.md`? | Yes. |
| Enter `authoritative_workflow_enforcement_fix_phase1`? | Yes, after user confirmation. |

## Current Authoritative Docs

Recommended as current entrypoints:

- `docs/PROJECT_STATUS.md`
- `docs/DOCUMENTATION_GOVERNANCE.md`
- `docs/CODEX_WORKFLOW.md`
- `docs/AGENT_WORKFLOW.md`
- `.github/pull_request_template.md`
- `AGENTS.md`
- `CLAUDE.md`
- `docs/DATA_SOURCE_STRATEGY.md`
- `docs/data/FOTMOB_CURRENT_STATE.md`

Do not create replacements such as `PROJECT_STATUS_V2.md`, `NEW_WORKFLOW.md`, `NEW_RULES.md`, or a new workflow authority document.

## Stale / Drift Findings

- `docs/PROJECT_STATUS.md` last updated `2026-06-07`; the audited dry-runs are dated `2026-06-20`.
- `docs/PROJECT_STATUS.md` reports `docs/_reports` count as 363, but this branch has 434 after this report.
- `docs/DOCUMENTATION_GOVERNANCE.md` and `docs/CODEX_WORKFLOW.md` still list existing docs such as `PROJECT_STATUS` and `DATA_SOURCE_STRATEGY` as planned.
- `docs/CHANGELOG.md` is historical and does not reflect June 2026 governance/data safety conclusions.
- `README.md` still presents production-ready posture without pointing readers to current blockers in `PROJECT_STATUS`.

## Recent Dry-Run Backflow

| Report | Reflected in `PROJECT_STATUS.md`? | Required status delta |
| --- | --- | --- |
| `formal_training_cohort_inventory_dry_run_20260620.md` | No | Formal training remains blocked: 58 smoke/integration candidates, 0 formal candidates with odds, no model training authorization. |
| `technical_debt_workflow_audit_dry_run_20260620.md` | No | Technical debt audit blocks data expansion and formal training until P0 debt is handled. |
| `p0_db_write_safety_gate_dry_run_20260620.md` | No | DB write gate is audit-only: 122 production DB-write scripts detected, 66 P0, 110 with no gate. |

## Enforcement Gaps

P0:

- PRs can add `docs/_reports/*.md` without updating `PROJECT_STATUS` or another authoritative doc.
- AI Workflow Gate does not block report-only PRs that skip authoritative-doc backflow.
- Recent key dry-run conclusions have not been reflected in `PROJECT_STATUS.md`.
- PR template lacks an explicit authoritative/source-of-truth doc update status.

P1:

- `CODEX_WORKFLOW.md` lacks a hard completion standard for source-of-truth update or explicit no-update justification.
- `DOCUMENTATION_GOVERNANCE.md` describes backflow as eventual/next-task behavior, not an enforced PR gate.
- `documentation_governance_check.py` exists but is not wired as a general Production Gate source-of-truth backflow check.
- Current doc-sprawl gate allows up to 5 new reports/manifests without backlink enforcement.

P2:

- 425 existing reports lack an obvious backlink to current authoritative docs.
- Legacy `.github/PULL_REQUEST_TEMPLATE.md` exists alongside active lowercase template.
- `README.md` and `CHANGELOG.md` are not aligned with current governance/blocker state.
- Planned docs listed in governance remain missing or unresolved.

## Recommended Fix Phase1

Minimum files to modify after user confirmation:

- `.github/pull_request_template.md`
- `scripts/ops/ai_workflow_gate.py`
- `tests/unit/test_ai_workflow_gate.py`
- `docs/DOCUMENTATION_GOVERNANCE.md`
- `docs/CODEX_WORKFLOW.md`
- `docs/PROJECT_STATUS.md`

Minimum checks:

- If a PR adds `docs/_reports/*.md`, require either an authoritative doc update or an explicit PR-body no-update justification.
- Require PR template row: authoritative/source-of-truth docs updated `yes/no` plus reason.
- Fail hollow Documentation Impact answers.
- Keep `_reports` as evidence only; active conclusions must flow to current-state docs.

Recommendation: enter `authoritative_workflow_enforcement_fix_phase1` only after explicit user approval. Do not start automatically.
