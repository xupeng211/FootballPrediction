# L3 Legacy Label and Guard Wording Proposal

## Status

- Phase: L3C legacy label and guard wording proposal
- Lifecycle: current-state proposal document
- Runtime behavior changed: no
- Source files changed: no
- CI/workflow changed: no
- Gate enforcement changed: no
- Deletion/move/rename: no
- Enforcement added: no
- L3A basis: `docs/techdebt/L3_LEGACY_ENTRYPOINT_ISOLATION_PLAN.md`
- L3B basis: `docs/techdebt/L3_ACTIVE_ENTRYPOINT_WHITELIST.md`

## Purpose

L3A identified legacy entrypoints. L3B confirmed the active whitelist and restricted legacy boundary.

L3C now proposes **advisory label semantics** and **reusable guard wording** so that:

1. Future AI agents have clear default rules for each entrypoint class.
2. PR authors and reviewers have copyable templates for declaring entrypoint boundary impact.
3. Claude Code prompts can include concise guard wording that references these labels.
4. The L3 isolation policy is communicated without adding CI enforcement.

This proposal is **docs-only**. It does not modify any gate, workflow, source file, or runtime behavior.

## Non-enforcement statement

This document explicitly does **not**:

- Modify AI Workflow Gate (`scripts/ops/ai_workflow_gate.py`).
- Modify Gatekeeper (`scripts/devops/gatekeeper.sh`).
- Add CI enforcement checks.
- Add GitHub labels.
- Add code comments or annotations to source files.
- Modify runtime files.
- Delete, move, or rename any file.
- Implement automated policy enforcement.

It is a **human and AI agent guidance proposal only**. Enforcement requires a separate, explicitly authorized future task.

---

## Label semantics

Each entrypoint class receives a label with a **default action**, a **modification authorization** requirement, and a **runtime execution** default.

| Label | Meaning | Default action | Modification authorization needed | Runtime execution allowed by default | Notes |
|---|---|---|---|---|---|
| `active-runtime` | Current production application entrypoint | Treat as runtime source-of-truth | Task-scoped authorization that names this path | Only via documented operational path (Dockerfile CMD, `make dev-up`) | Currently: `src/main.py` only. |
| `active-api-router` | Router mounted by the active runtime entrypoint | Treat as active API surface | API-scoped task authorization | Only through the mounted app; not standalone | Currently: health, monitoring, model_management, admin (conditional). |
| `active-governance` | CI/gate/quality infrastructure | Treat as active governance surface | Explicit governance task authorization | Only via CI workflow or `make pr-gate-local` | Includes AI Workflow Gate, Gatekeeper, AST check, helpers. |
| `operational-guarded` | Makefile target or manual operational script | Read; do not run by default | Explicit operational authorization naming the target | Only with explicit user authorization | Includes `make data-l1-*`, `make pr-*`, `make dev-*`. |
| `restricted-legacy` | Historical/legacy CLI, pipeline, scraper, or router | Read-only by default | Explicit user authorization naming the exact path | **Never** without explicit user authorization | 18 entries in L3B whitelist. |
| `archive-read-only` | Historical reference material | Read-only by default | Dedicated archive authorization | **Never** | `archive_vault_2026/**`. |
| `test-only` | Test files and helpers | Read; modify only in test-scoped tasks | Test-scoped task authorization | Only via test runner (`make test`, `pytest`, `npm test`) | `tests/**`, including legacy archive tests. |
| `unknown-owner-decision` | Insufficient evidence for classification | Treat as restricted-legacy until classified | Owner decision required before any action | **Never** without owner decision | 7 categories in L3B whitelist. |

### Label usage rules

- These labels are **advisory descriptors**, not GitHub labels, not code annotations, not CI tags.
- A single file or directory may have only one label at a time.
- When an `unknown-owner-decision` entry is classified by the owner, it must be moved to the appropriate label and the whitelist document updated.
- Labels do **not** authorize action by themselves — they define the **default boundary**. Task authorization is always required.

---

## Default boundary rules

These rules apply to all AI agents and PR authors working in this repository:

### Active whitelist rules

1. Active whitelist entries may be treated as current source-of-truth for their domain.
2. Modification still requires task-specific authorization that names the affected path.
3. "Active" does not mean "free to change" — it means "this is the canonical surface."

### Restricted legacy rules

4. Restricted legacy entries are **read-only by default**.
5. Modification, execution, migration, or deletion requires a dedicated PR that:
   - Names the exact path.
   - States the reason the active guarded path is insufficient.
   - Declares the risk and validation plan.
   - Includes explicit user authorization in the PR body.
6. Agents must not fix, refactor, or "improve" legacy entrypoints while working on unrelated tasks.

### Unknown entry rules

7. Unknown entries are **no-touch** until the owner classifies them.
8. No default modification, execution, migration, or deletion.
9. An agent encountering an unknown entry must flag it and request owner decision.

### Archive rules

10. Archive paths (`archive_vault_2026/**`, `tests/Z_LEGACY_ARCHIVE_PRE_V4.46.8/**`) are **read-only**.
11. Any modification requires a dedicated archive-maintenance PR with explicit authorization.

### Operational guarded rules

12. Operational guarded targets are **not run by default**.
13. Each invocation requires explicit user authorization.
14. Read-only targets (`make pr-body-check`, `make watch-pr`, `make data-help`) are safe to run.

### Cross-cutting rules

15. L3 tasks must not mix with L4 API boundary reconciliation.
16. Deletion, move, or rename of any entrypoint requires a dedicated PR with explicit user authorization.
17. Enforcement of these rules requires a separate, explicitly authorized future task.

---

## Entrypoint Boundary Impact — PR body template

Copy this section into any PR body to declare entrypoint boundary impact:

```markdown
## Entrypoint Boundary Impact

| Item | Value |
|---|---|
| Active runtime entrypoint modified | no |
| Active API router modified | no |
| Active governance entrypoint modified | no |
| Operational guarded target modified | no |
| Restricted legacy entrypoint touched | no |
| Archive path touched | no |
| Unknown entrypoint touched | no |
| Test-only path modified | no (or yes, with test scope declared) |
| L4 API boundary reconciliation included | no |
| Deletion / move / rename included | no |

### Active entrypoint modification detail

If any active entrypoint is modified, list each path and the task authorization that covers it:

| Path | Label | Task scope | Authorization |
|---|---|---|---|
| (none, or path) | (label) | (scope) | (how authorized) |

### Operational target execution

If any operational guarded target was executed during this task, list each:

| Target | Reason | Authorization |
|---|---|---|
| (none, or target) | (why) | (how authorized) |
```

---

## Legacy Entrypoint Authorization — PR body template

Copy this section when a PR needs to touch a restricted legacy entrypoint:

```markdown
## Legacy Entrypoint Authorization

### Authorization request

| Path | Label | Action | Reason active path insufficient | Risk | Validation plan | Rollback plan |
|---|---|---|---|---|---|---|
| (path) | restricted-legacy | (modify/run/migrate/delete) | (why) | (risk) | (how validated) | (how rolled back) |

### Explicit user authorization

- [ ] I confirm that the above legacy entrypoint action is authorized for this PR.
- [ ] I understand that legacy entrypoint modifications carry elevated risk.
- [ ] I have verified that no active guarded path can serve the same purpose.

### Post-action verification

- [ ] The legacy entrypoint change has been tested.
- [ ] The active whitelist has been updated if the legacy status changed.
- [ ] No other legacy entrypoints were modified opportunistically.
```

---

## Unknown Entrypoint Owner Decision — template

Copy this section when requesting owner classification of an unknown entry:

```markdown
## Unknown Entrypoint Owner Decision Request

| Path or pattern | Current label | Proposed label | Evidence for proposal | Impact if classified as proposed |
|---|---|---|---|---|
| (path) | unknown-owner-decision | (proposed label) | (evidence) | (impact) |

### Decision needed

Please classify the above entry as one of:
- `active-runtime` / `active-api-router` / `active-governance` / `operational-guarded`
- `restricted-legacy`
- `archive-read-only`
- `test-only`

Once classified, the L3 active entrypoint whitelist (`docs/techdebt/L3_ACTIVE_ENTRYPOINT_WHITELIST.md`) will be updated.

### Owner decision

- [ ] Classified as: _______
- [ ] Whitelist update PR authorized: yes / no
- [ ] Additional notes: _______
```

---

## Archive Exception Authorization — template

Copy this section when a PR needs to touch an archive path:

```markdown
## Archive Exception Authorization

| Path | Reason access needed | Read or write | Risk | Authorization |
|---|---|---|---|---|
| (path) | (why) | (read / write) | (risk) | (how authorized) |

### Confirmation

- [ ] This archive access is scoped to the exact paths listed above.
- [ ] No other archive files are modified opportunistically.
- [ ] The archive is not being used as a runtime source-of-truth.
- [ ] After this PR, the archive returns to read-only status.
```

---

## No L4 mixing — wording

Copy this statement into any L3-scope PR body:

```markdown
## L4 API Boundary Reconciliation Exclusion

This PR does **not** include L4 API boundary reconciliation.

Specifically, this PR does not:
- Migrate API endpoints between routers.
- Change which router owns a given route.
- Reinterpret active API router ownership.
- Merge, split, or rename API routers.
- Mount or unmount routers from `src/main.py`.
- Change the relationship between `src/main.py` inline routes and `src/api/predictions/predict_router.py`.

L4 API boundary reconciliation requires a separate, explicitly authorized task.
```

---

## Prompt guard wording for future Claude Code tasks

Copy this block into Claude Code task prompts to activate L3 boundary awareness:

```text
## L3 Entrypoint Boundary Rules (active for this task)

Before working on this task, read the L3 active entrypoint whitelist:
- `docs/techdebt/L3_ACTIVE_ENTRYPOINT_WHITELIST.md`

During this task, follow these default rules:

1. **Active whitelist**: you may read and reference active entrypoints. Modification still requires task-scoped authorization.
2. **Restricted legacy**: do NOT modify, run, migrate, delete, move, or rename any restricted legacy entrypoint unless this task explicitly authorizes the exact path. See the whitelist document for the full restricted legacy list (18 entries).
3. **Unknown**: do NOT touch any unknown entrypoint. If your work requires it, stop and request an owner decision using the template in `docs/techdebt/L3_LEGACY_LABEL_AND_GUARD_WORDING_PROPOSAL.md`.
4. **Archive**: `archive_vault_2026/**` is read-only. Do not modify.
5. **Operational guarded**: do not run `make data-l1-*`, `make data-l2-*`, or other operational targets unless this task explicitly authorizes them.
6. **No L4 mixing**: do not combine L3 entrypoint isolation work with L4 API boundary reconciliation.
7. **No deletion without a dedicated PR**: do not delete, move, or rename any entrypoint file unless this task is a dedicated deletion/migration PR.
8. **Enforcement is not active**: these rules are advisory (docs-only in L3C). You are expected to follow them voluntarily. Do not modify CI gates to add enforcement.

If you are unsure about an entrypoint's status, consult the whitelist document first. If still unsure, stop and ask.
```

### Short prompt variant

For brief task prompts where the full block is too long:

```text
L3 boundary rules active. Read `docs/techdebt/L3_ACTIVE_ENTRYPOINT_WHITELIST.md`.
Do not touch restricted-legacy, unknown, or archive paths without explicit authorization.
Do not mix L3 with L4.
```

---

## Relationship to L3A and L3B

| Document | Phase | Role |
|---|---|---|
| `docs/techdebt/L3_LEGACY_ENTRYPOINT_ISOLATION_PLAN.md` | L3A | Original inventory and classification framework |
| `docs/_reports/L3A_LEGACY_ENTRYPOINT_INVENTORY_REPORT.md` | L3A | Scan evidence and risk map |
| `docs/techdebt/L3_ACTIVE_ENTRYPOINT_WHITELIST.md` | L3B | Concrete whitelist (1 active runtime, 4 API routers, 11 governance, 11 guarded, 18 restricted legacy, 2 test-only, 1 archive, 7 unknown) |
| `docs/_reports/L3B_ACTIVE_ENTRYPOINT_WHITELIST_CONFIRMATION_REPORT.md` | L3B | Confirmation snapshot and key decisions |
| `docs/techdebt/L3_LEGACY_LABEL_AND_GUARD_WORDING_PROPOSAL.md` | L3C | **This document** — label semantics and guard wording proposal |
| `docs/_reports/L3C_LEGACY_LABEL_GUARD_WORDING_PROPOSAL_REPORT.md` | L3C | Bounded proposal report |

## References

- `AGENTS.md` — agent workflow hardening rules
- `CLAUDE.md` — project instructions and safety discipline
- `.github/workflows/production-gate.yml` — CI pipeline definition
- `scripts/ops/ai_workflow_gate.py` — existing AI Workflow Gate implementation (not modified by L3C)
- `scripts/devops/gatekeeper.sh` — existing Gatekeeper (not modified by L3C)

## Next recommended task

Do not start automatically.

Recommended next task only after user confirmation:

- Review and merge L3C if CI is green.
- Future **L3D** may propose docs-only CODEOWNERS / review ownership wording that maps labels to reviewer responsibility.
- Future **L3E** (or separate authorization) may propose CI enforcement of selected label boundaries.
- Do not implement gate enforcement until separately authorized.
- Do not start L4 API boundary reconciliation.
