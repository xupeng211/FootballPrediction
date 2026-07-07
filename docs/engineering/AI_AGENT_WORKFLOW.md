# AI Agent Workflow Governance

lifecycle: permanent
scope: AI agent collaboration rules for this repository

## Purpose

AI agents (Claude Code, Codex, etc.) working in this repository are not
outsourced code writers. They are engineering collaborators responsible for
maintaining code, tests, documentation, project state, and safety boundaries.

## Core Rules

### 1. Canonical Documentation

Do not create scattered temporary reports. Prefer updating existing canonical
documents. If a task creates durable project knowledge (milestones, status
changes, safety boundary shifts, architecture decisions), update the relevant
canonical document. If no documentation update is needed, explicitly state why
in the final report.

### 2. Documentation Impact Check

Every task must include a documentation impact assessment:

- Did this task change project behavior?
- Did this task change data semantics?
- Did this task change safety boundaries?
- Did this task change run commands or CLI interfaces?
- Did this task change current project status (readiness, signal availability)?
- Did this task create durable knowledge?
- Did this task deprecate or invalidate an old assumption?
- Which canonical document was updated? If none, why?

### 3. No Temporary Document Spam

Temporary reports, audit dumps, local run logs, and one-off summaries should
not be committed to the repository. Milestones should be summarized into
canonical docs. The final report of a task is ephemeral — the canonical doc
update is durable.

### 4. Branch and PR Discipline

- Work on a task branch; never commit directly to main.
- Open a PR for every change (including docs-only).
- Wait for CI; do not bypass gates or merge with failing checks.
- Squash-merge with a descriptive subject line.
- Delete the remote branch after merge.
- Do not force-push or rebase shared branches without explicit authorization.

### 5. Safety Boundary Discipline

The following actions require explicit, scoped authorization:

- DB writes (INSERT, UPDATE, DELETE, DDL, migration)
- Smelt execution (real smelt, not no-write preview)
- Model training (dry-run or real)
- Prediction and backtest execution
- External data collection (scrapers, browser automation, FotMob/OddsPortal access)

The following do NOT imply authorization:

- No-write preview success does not imply DB write authorization.
- Dry-run success does not imply training readiness.
- CI green does not imply training authorization.
- Allowlist presence does not authorize runtime DB writes.

### 6. Final Report Quality

Final reports must be concise and must not substitute for documentation
updates. If durable knowledge was produced, the final report must reference
the canonical document that was updated.

### 7. Stale Documentation

If an agent discovers stale, conflicting, or misleading documentation, it must
either fix it within the current task scope, or explicitly report it as a
follow-up task. Silent acceptance of incorrect docs is not acceptable.

### 8. Scope Discipline

- Do not expand task scope beyond what was authorized.
- If scope expansion is needed, stop and ask for confirmation.
- Do not chain unrelated tasks together in a single PR.

### 9. Audit Trail

Each task's final report must record:

- PR number and URL
- Head SHA and merge commit SHA
- CI run ID and result
- Remote branch deleted (yes/no)
- Main green status (yes/no/not verified)
- Next recommended task
- "Do not start automatically"

## Documentation Index

| Document | Purpose |
|---|---|
| `AGENTS.md` | Agent entry point |
| `CLAUDE.md` | Claude Code project instructions |
| `docs/engineering/AI_AGENT_WORKFLOW.md` | This document |
| `docs/data/elo_prematch_signal.md` | Elo signal integration status |
| `docs/data/FOTMOB_CURRENT_STATE.md` | FotMob ingestion state |
| `docs/ml/training_no_write_report_only_guard.md` | Training guard docs |
