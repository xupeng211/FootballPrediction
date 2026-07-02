# L3 Review Ownership and CODEOWNERS Wording Proposal

## Status

- Phase: L3D review ownership and CODEOWNERS wording proposal
- Lifecycle: current-state proposal document
- Runtime behavior changed: no
- Source files changed: no
- CI/workflow changed: no
- Gate enforcement changed: no
- CODEOWNERS changed: no
- GitHub labels created: no
- Deletion/move/rename: no
- Enforcement added: no
- L3A basis: `docs/techdebt/L3_LEGACY_ENTRYPOINT_ISOLATION_PLAN.md`
- L3B basis: `docs/techdebt/L3_ACTIVE_ENTRYPOINT_WHITELIST.md`
- L3C basis: `docs/techdebt/L3_LEGACY_LABEL_AND_GUARD_WORDING_PROPOSAL.md`

## Purpose

L3A identified legacy entrypoints. L3B confirmed the active whitelist. L3C proposed advisory labels and guard wording.

L3D now proposes **review ownership semantics** and **future CODEOWNERS wording** so that:

1. Each entrypoint label has a clear default reviewer role.
2. Future agents and PR authors know who should review changes to each ownership area.
3. A future CODEOWNERS file can be structured around these ownership areas when the repo owner is ready.
4. Reviewer checklists make boundary-crossing explicit before merge.
5. Unknown entries have a defined owner-decision workflow.

This proposal is **docs-only**. It does not create, modify, or implement CODEOWNERS.

## Non-enforcement statement

This document explicitly does **not**:

- Modify `.github/CODEOWNERS` or create a new CODEOWNERS file.
- Modify `.github/**` (workflows, templates, branch protection).
- Modify AI Workflow Gate (`scripts/ops/ai_workflow_gate.py`).
- Modify Gatekeeper (`scripts/devops/gatekeeper.sh`).
- Add CI enforcement checks.
- Add GitHub labels.
- Add code annotations to source files.
- Implement reviewer automation or required-review rules.
- Delete, move, or rename any file.

It is a **human and AI agent guidance proposal only**. CODEOWNERS implementation and enforcement require separate, explicitly authorized future tasks.

---

## Review ownership semantics

Each L3 entrypoint label maps to a review ownership area. The owner is the default reviewer for changes touching that area.

| Ownership area | Applies to L3 label | Default reviewer role | Required authorization before modification | Runtime execution allowed by default | Notes |
|---|---|---|---|---|---|
| Runtime owner | `active-runtime` | Repo owner / runtime maintainer | Task-scoped authorization naming the path | Only via Dockerfile CMD or `make dev-up` | Currently: `src/main.py`. |
| API surface owner | `active-api-router` | Repo owner / API maintainer | API-scoped task authorization | Only through mounted app, not standalone | health, monitoring, model_management, admin (conditional). |
| Governance owner | `active-governance` | Repo owner / CI maintainer | Explicit governance task authorization | Only via CI workflow or `make pr-gate-local` | AI Workflow Gate, Gatekeeper, AST check, helpers. Must not be modified in non-governance PRs. |
| Operational owner | `operational-guarded` | Repo owner / ops maintainer | Explicit operational authorization naming the target | Only with explicit user authorization | `make data-l1-*`, `make pr-*`, `make dev-*`. |
| Legacy owner decision | `restricted-legacy` | Repo owner | Explicit user authorization naming exact path | **Never** without explicit user authorization | 18 entries in L3B whitelist. Read-only by default. |
| Archive owner decision | `archive-read-only` | Repo owner | Dedicated archive authorization | **Never** | `archive_vault_2026/**`. |
| Test owner | `test-only` | Repo owner / test maintainer | Test-scoped task authorization | Only via test runner (`make test`, `pytest`, `npm test`) | `tests/**`. |
| Unknown owner decision | `unknown-owner-decision` | Repo owner (decision required) | Owner decision required before any action | **Never** without owner decision | 7 categories in L3B whitelist. Blocked until classified. |

### Ownership escalation rules

- If a PR touches an ownership area without the corresponding reviewer's awareness, the reviewer should flag it.
- Restricted legacy, archive, and unknown entries always escalate to repo owner decision.
- Governance entries should not be modified in PRs whose primary scope is runtime, API, data, or docs.
- Test-only entries should not be treated as runtime source-of-truth by any reviewer.

---

## Future CODEOWNERS wording proposal

**This section is a proposal only. It does not implement CODEOWNERS.**

The existing `.github/CODEOWNERS` assigns all entries to `@xupeng211`. The L3 entrypoint taxonomy suggests a future structure where different ownership areas could map to different reviewer groups, if and when the repo owner decides to delegate review responsibility.

### Proposed future CODEOWNERS structure (example only — not implemented)

```text
# === Example only — not implemented in this PR ===
# Actual team/user handles must be decided by repo owner.
# Future implementation requires separate PR and explicit authorization.

# Active runtime / API surface
/src/main.py                         @REPO_OWNER_RUNTIME
/src/api/health.py                   @REPO_OWNER_API
/src/api/monitoring.py               @REPO_OWNER_API
/src/api/model_management.py         @REPO_OWNER_API
/src/api/v1/endpoints/admin.py       @REPO_OWNER_API

# Governance / CI entrypoints
/scripts/ops/ai_workflow_gate.py     @REPO_OWNER_GOVERNANCE
/scripts/ops/helpers/                @REPO_OWNER_GOVERNANCE
/scripts/devops/                     @REPO_OWNER_GOVERNANCE
/.github/workflows/                  @REPO_OWNER_GOVERNANCE
/.github/pull_request_template.md    @REPO_OWNER_GOVERNANCE

# Tech debt docs (L3 track)
/docs/techdebt/                      @REPO_OWNER_TECHDEBT
/docs/_reports/                      @REPO_OWNER_TECHDEBT

# AI agent governance
/AGENTS.md                           @REPO_OWNER_GOVERNANCE
/CLAUDE.md                           @REPO_OWNER_GOVERNANCE
/docs/AGENT_WORKFLOW.md              @REPO_OWNER_GOVERNANCE
/docs/AI_AGENT_WORKFLOW_HARDENING.md @REPO_OWNER_GOVERNANCE

# Restricted legacy (read-only by default — CODEOWNERS review required for any touch)
/scripts/ops/run_production.js       @REPO_OWNER_LEGACY
/scripts/ops/titan_discovery.js       @REPO_OWNER_LEGACY
/scripts/ops/total_war_pipeline.js    @REPO_OWNER_LEGACY
/scripts/ops/batch_historical_backfill.js @REPO_OWNER_LEGACY
/scripts/ops/odds_harvest_pipeline.js @REPO_OWNER_LEGACY
/scripts/ops/train_model.py          @REPO_OWNER_LEGACY
/scripts/ops/predict_pipeline.py     @REPO_OWNER_LEGACY
/scripts/ops/smelt_all.js            @REPO_OWNER_LEGACY
/scripts/ops/l3_stitch_pipeline.js   @REPO_OWNER_LEGACY
/scripts/ops/odds_sniper.js          @REPO_OWNER_LEGACY
/scripts/ops/seed_fixtures.js        @REPO_OWNER_LEGACY
/scripts/ops/local_dom_ingestor.js    @REPO_OWNER_LEGACY
/scripts/ops/csv_bulk_loader.js      @REPO_OWNER_LEGACY
/scripts/ops/fetch_and_adapt_euro_leagues.js @REPO_OWNER_LEGACY
/scripts/maintenance/                @REPO_OWNER_LEGACY
/src/api/predictions/predict_router.py @REPO_OWNER_LEGACY

# Archive (read-only)
/archive_vault_2026/                 @REPO_OWNER_ARCHIVE

# Docker / Compose / Deploy
/Dockerfile                          @REPO_OWNER_INFRA
/**/Dockerfile                       @REPO_OWNER_INFRA
/docker-compose*.yml                 @REPO_OWNER_INFRA
/docker-compose*.yaml                @REPO_OWNER_INFRA
/.devcontainer/                      @REPO_OWNER_INFRA

# DB / Migrations / SC-002
/database/migrations/                @REPO_OWNER_DB
/src/database/migrations/            @REPO_OWNER_DB
/alembic/                            @REPO_OWNER_DB
*.sql                                @REPO_OWNER_DB
```

### Important caveats

- `@REPO_OWNER_RUNTIME`, `@REPO_OWNER_API`, `@REPO_OWNER_GOVERNANCE`, `@REPO_OWNER_LEGACY`, `@REPO_OWNER_ARCHIVE`, `@REPO_OWNER_INFRA`, `@REPO_OWNER_DB`, `@REPO_OWNER_TECHDEBT` are **placeholder handles only**. They do not correspond to actual GitHub teams or users.
- The repo owner (`@xupeng211`) must decide actual handles before any CODEOWNERS implementation.
- This PR does **not** create or modify `.github/CODEOWNERS`.
- Future CODEOWNERS implementation requires:
  - A separate, explicitly authorized PR.
  - Confirmation that all placeholder handles are replaced with real GitHub users/teams.
  - A separate CI validation pass.
  - Explicit owner sign-off.

---

## Reviewer checklist template

Copy this checklist into any PR that touches entrypoint paths:

```markdown
## L3 Entrypoint Reviewer Checklist

### Entrypoint labels identified

- [ ] All changed files have been classified against the L3 active entrypoint whitelist (`docs/techdebt/L3_ACTIVE_ENTRYPOINT_WHITELIST.md`).
- [ ] Each changed file's L3 label is listed in the Entrypoint Boundary Impact table.

### Active whitelist check

- [ ] No active runtime entrypoint (`src/main.py`) is modified without runtime-scope authorization.
- [ ] No active API router is modified without API-scope authorization.
- [ ] No active governance entrypoint is modified without governance authorization.

### Restricted legacy check

- [ ] No restricted legacy entrypoint is touched. If touched, the Legacy Entrypoint Authorization table is completed and explicit user authorization is confirmed.

### Unknown entry check

- [ ] No unknown entrypoint is touched. If an unknown entry needs to be touched, an Owner Decision Request has been filed and resolved before merge.

### Archive check

- [ ] No archive path (`archive_vault_2026/**`) is touched. If touched, the Archive Exception Authorization table is completed.

### L4 boundary check

- [ ] This PR does not include L4 API boundary reconciliation.
- [ ] No router ownership change, router mount/unmount, or route migration is included.

### Deletion / move / rename check

- [ ] No file is deleted, moved, or renamed. If deletion/move/rename is required, it is in a dedicated PR with explicit authorization.

### Runtime execution check

- [ ] No restricted legacy, archive, or unknown entrypoint was executed during this task.
- [ ] If an operational guarded target was executed, it is listed in the Operational Target Execution table.

### Governance / CI file check

- [ ] No governance or CI file (`.github/**`, `scripts/devops/**`, `scripts/ops/ai_workflow_gate.py`, `scripts/ops/helpers/**`) is modified without governance authorization.

### Source-of-truth docs check

- [ ] If this PR changes entrypoint status, the L3 active entrypoint whitelist has been updated.
- [ ] If this PR adds a new entrypoint, it has been classified and added to the whitelist.

### Report lifecycle check

- [ ] Any new `docs/_reports/**` artifact has a Report Lifecycle section.
- [ ] The report declares its owner, purpose, source-of-truth relationship, supersession, and cleanup policy.

### Rollback plan check

- [ ] A rollback plan is present in the PR body.
```

---

## PR body review ownership template

Copy this section into any PR body to declare review ownership impact:

```markdown
## Review Ownership Impact

| Ownership area | Label | File count changed | Reviewer required | Authorization present |
|---|---|---|---|---|
| Runtime owner | active-runtime | (count) | (who) | yes / no / n/a |
| API surface owner | active-api-router | (count) | (who) | yes / no / n/a |
| Governance owner | active-governance | (count) | (who) | yes / no / n/a |
| Operational owner | operational-guarded | (count) | (who) | yes / no / n/a |
| Legacy owner decision | restricted-legacy | (count) | repo owner | yes / no / n/a |
| Archive owner decision | archive-read-only | (count) | repo owner | yes / no / n/a |
| Test owner | test-only | (count) | (who) | yes / no / n/a |
| Unknown owner decision | unknown-owner-decision | (count) | repo owner (decision needed) | yes / no / n/a |

### Owner decision required

- [ ] No owner decision is required for this PR.
- [ ] Owner decision required for: (list paths and reason)

### CODEOWNERS impact

- [ ] This PR does not create or modify `.github/CODEOWNERS`.
- [ ] This PR does not change branch protection or required-review rules.

### Enforcement impact

- [ ] This PR does not add or modify CI enforcement of review ownership.
```

---

## Future Claude Code prompt guard wording

Copy this block into Claude Code task prompts for L3D-aware review ownership:

```text
## L3D Review Ownership Rules (active for this task)

Before working on this task, read:
- `docs/techdebt/L3_ACTIVE_ENTRYPOINT_WHITELIST.md` — active entrypoint whitelist
- `docs/techdebt/L3_LEGACY_LABEL_AND_GUARD_WORDING_PROPOSAL.md` — label semantics
- `docs/techdebt/L3_REVIEW_OWNERSHIP_AND_CODEOWNERS_WORDING_PROPOSAL.md` — review ownership (this document)

During this task, follow these rules:

1. **Identify affected ownership area**: for each file you change, determine which L3 label and ownership area it belongs to.
2. **Active whitelist**: modification requires task-scoped authorization. Name the affected path in the PR body.
3. **Restricted legacy**: do NOT modify, run, migrate, delete, move, or rename. Read-only by default.
4. **Unknown entries**: do NOT touch. If your work requires it, stop and request an owner decision.
5. **Archive**: `archive_vault_2026/**` is read-only. Do not modify.
6. **Governance files**: do NOT modify `.github/**`, `scripts/devops/**`, `scripts/ops/ai_workflow_gate.py`, or `scripts/ops/helpers/**` unless this task is explicitly a governance-authorized task.
7. **No CODEOWNERS change**: do NOT create or modify `.github/CODEOWNERS` unless this task explicitly authorizes CODEOWNERS implementation.
8. **No L4 mixing**: do not combine L3 entrypoint isolation with L4 API boundary reconciliation.
9. **Reviewer checklist**: include the L3 Entrypoint Reviewer Checklist in the PR body if any entrypoint path is touched.
10. **No enforcement**: these rules are advisory. Do not add CI enforcement or required-review rules.

If you are unsure about an ownership area, consult the whitelist and label documents first. If still unsure, stop and ask.
```

### Short prompt variant

```text
L3D review ownership rules active. Read `docs/techdebt/L3_ACTIVE_ENTRYPOINT_WHITELIST.md`.
Identify ownership area for each changed file. Do not touch restricted-legacy, unknown, archive, or governance files without explicit authorization. Do not modify CODEOWNERS. Do not mix L3 with L4.
```

---

## Owner decision workflow for unknown entries

When an AI agent or PR author encounters an `unknown-owner-decision` entry that their work requires touching, follow this workflow:

1. **Collect evidence**: what is the path, what does static scan show, why does the task need to touch it?
2. **Identify current classification**: confirm the entry is listed as `unknown-owner-decision` in the L3B whitelist.
3. **File an Owner Decision Request**: use the Unknown Entrypoint Owner Decision template from `docs/techdebt/L3_LEGACY_LABEL_AND_GUARD_WORDING_PROPOSAL.md`.
4. **Do not proceed without a decision**: the entry remains restricted (read-only, no-touch) until the repo owner classifies it.
5. **Wait for owner response**: the owner may classify it as `active-runtime`, `active-api-router`, `active-governance`, `operational-guarded`, `restricted-legacy`, `archive-read-only`, or `test-only`.
6. **Record the decision**: once classified, update `docs/techdebt/L3_ACTIVE_ENTRYPOINT_WHITELIST.md` to move the entry from the Unknown section to its new category.
7. **Proceed with task**: after classification and whitelist update, the task may proceed with the authorization appropriate to the new label.

### Unknown entry decision record template

```markdown
## Unknown Entrypoint Owner Decision Record

| Path | Previous label | New label | Decision date | Decided by | Evidence | Whitelist updated |
|---|---|---|---|---|---|---|
| (path) | unknown-owner-decision | (new label) | (date) | @owner | (summary) | yes / no |
```

---

## Relationship to L3A / L3B / L3C

| Document | Phase | Role |
|---|---|---|
| `docs/techdebt/L3_LEGACY_ENTRYPOINT_ISOLATION_PLAN.md` | L3A | Original inventory and classification framework |
| `docs/_reports/L3A_LEGACY_ENTRYPOINT_INVENTORY_REPORT.md` | L3A | Scan evidence and risk map |
| `docs/techdebt/L3_ACTIVE_ENTRYPOINT_WHITELIST.md` | L3B | Concrete whitelist (1+4+11+11+18+2+1+7 entries) |
| `docs/_reports/L3B_ACTIVE_ENTRYPOINT_WHITELIST_CONFIRMATION_REPORT.md` | L3B | Confirmation snapshot |
| `docs/techdebt/L3_LEGACY_LABEL_AND_GUARD_WORDING_PROPOSAL.md` | L3C | Label semantics and guard wording |
| `docs/_reports/L3C_LEGACY_LABEL_GUARD_WORDING_PROPOSAL_REPORT.md` | L3C | Label proposal report |
| `docs/techdebt/L3_REVIEW_OWNERSHIP_AND_CODEOWNERS_WORDING_PROPOSAL.md` | L3D | **This document** — review ownership and CODEOWNERS wording proposal |
| `docs/_reports/L3D_REVIEW_OWNERSHIP_CODEOWNERS_WORDING_PROPOSAL_REPORT.md` | L3D | Bounded proposal report |

## References

- `.github/CODEOWNERS` — existing CODEOWNERS file (not modified by L3D)
- `AGENTS.md` — agent workflow hardening rules
- `CLAUDE.md` — project instructions and safety discipline
- `docs/AGENT_WORKFLOW.md` — detailed agent workflow documentation

## Next recommended task

Do not start automatically.

Recommended next task only after user confirmation:

- Review and merge L3D if CI is green.
- Future **L3E** may classify the 7 unknown categories as docs-only owner decisions, resolving the last open taxonomy gap in the L3 track.
- Do not implement CODEOWNERS or enforcement until separately authorized.
- Do not start L4 API boundary reconciliation.

## L3E follow-up

L3E records docs-only owner decisions for the 7 previously unknown categories in:

- `docs/techdebt/L3_UNKNOWN_ENTRYPOINT_OWNER_DECISIONS.md`
- `docs/_reports/L3E_UNKNOWN_ENTRYPOINT_OWNER_DECISIONS_REPORT.md`

The L3E decisions complete the L3 taxonomy. The 7 unknown categories are classified: 6 as restricted-legacy, 1 as test-only. The `src/**` `__main__` blocks are resolved as active-runtime modules with test-only self-test blocks. The `unknown-owner-decision` label is now empty but retained for future discoveries.
