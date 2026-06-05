# Documentation Governance

- lifecycle: permanent
- owner: documentation governance

## Purpose

This repository needs documentation governance because documentation is now part of
the operating surface of the project. Agents and reviewers use docs to decide what
is current, what is blocked, and what may be executed safely.

Phase reports and manifests cannot grow without limit. They are useful audit
evidence during data-source exploration, but unlimited report chains make the
current source of truth hard to find. A reader should not need to inspect dozens
of phase files to understand the active state.

The project should keep a small set of main documents clear and current. Codex
must not create several new reports for every task just to prove activity. New
documents need a reader, a lifecycle, and a reason they cannot be represented by
updating an existing source-of-truth document.

## Document Classes

### 1. Source of Truth Docs

Source of truth docs are long-lived documents that users and AI agents should
read first. They summarize current state and link to supporting evidence.

| Path | Status | Notes |
|---|---|---|
| docs/PROJECT_STATUS.md | planned | Overall project status and blockers. |
| docs/DATA_SOURCE_STRATEGY.md | planned | Current data-source strategy and gates. |
| docs/FOTMOB_CURRENT_STATE.md | planned | Preferred root-level FotMob state doc. |
| docs/data/FOTMOB_CURRENT_STATE.md | exists/needs_update | Existing FotMob state doc to reconcile. |
| docs/CANONICAL_MATCH_SCHEMA.md | planned | Canonical match payload and feature schema. |
| docs/DOCUMENTATION_GOVERNANCE.md | exists | This governance policy. |
| docs/CODEX_WORKFLOW.md | exists | Codex task and PR workflow controls. |
| docs/DEVELOPMENT_WORKFLOW.md | planned | Human development workflow reference. |

If a listed document does not exist, mark it as planned. Do not create it unless
the task explicitly includes that scope.

### 2. ADR / Decision Docs

ADR docs record long-term architecture decisions. They should be stable,
searchable, and small.

Recommended naming:

- `docs/adr/ADR-0001-*.md`

This phase does not create `docs/adr/`. It only defines the rule. Decisions that
affect architecture long term should become ADRs instead of temporary phase
reports.

### 3. Phase Reports

Phase reports usually live in:

- `docs/_reports/`

Rules:

- They may be kept as audit evidence.
- They are not long-term source of truth.
- After merge they can become archive candidates.
- They must be summarized or linked from a source-of-truth doc if the conclusion
  remains active.
- They must not repeat the same conclusion across report, review, decision, and
  next-plan files.

### 4. Machine Manifests

Machine manifests usually live in:

- `docs/_manifests/`

Rules:

- Humans should not need to read them by default.
- They are not primary decision documents.
- They must have a corresponding report or source-of-truth summary.
- They must not grow as unlimited phase snapshots.
- They must not store full HTML, full pageProps, raw bodies, or sensitive source
  payloads.

### 5. Archive Docs

Archive docs will live in:

- `docs/_archive/`

Rules:

- Do not delete evidence by default.
- Move stale reports to archive only in an approved cleanup phase.
- Archive preserves history; it does not participate in current decisions.
- Archive moves must preserve information and be reviewable.

### 6. Temporary / Scratch Docs

Temporary and scratch docs should not be committed to `main`.

If a temporary document must be committed, it must declare:

- lifecycle
- intended reader
- cleanup condition
- reason it cannot remain local or become a CI artifact

## Documentation Budget

Default rules for every PR:

- Default to adding no documents.
- Update existing documents before creating new ones.
- Add at most 1 human-readable report per PR.
- Add at most 1 machine manifest per PR.
- Add at most 1 checker per PR.
- Add at most 1 test file per PR.
- Do not add report + review + decision + next-plan as a bundle.
- Do not create an endless next-plan chain.
- Do not repeat the same conclusion in multiple new files.

High-audit exceptions must be declared in the PR body. The PR must explain why
the default budget is insufficient and include Documentation Impact.

## Documentation Impact Requirement

Every PR body must include:

## Documentation Impact

| Item | Value |
|---|---|
| New docs added | `<n>` |
| Docs modified | `<n>` |
| Reports added | `<n>` |
| Manifests added | `<n>` |
| Source-of-truth docs updated | yes/no |
| Superseded docs identified | yes/no |
| Archive candidates identified | yes/no |
| Reason for new docs | `<short reason>` |

## Source of Truth Rule

Any long-term conclusion must eventually be recorded in source-of-truth docs.
Phase reports can support the conclusion, but they cannot permanently be the only
place where active truth lives.

When a phase report changes project direction, the next governance or cleanup
task should update the relevant source-of-truth document with a short summary and
links to evidence.

## Report Lifecycle

Every report must declare one lifecycle status:

- active
- evidence
- superseded
- archive_candidate
- archived

Lifecycle meaning:

- `active`: still participates in current decisions.
- `evidence`: retained as proof, but not the primary current state.
- `superseded`: replaced by a newer source-of-truth summary or decision.
- `archive_candidate`: safe candidate for a future archive move.
- `archived`: moved to archive and no longer used for current decisions.

## Codex Documentation Rules

Codex must follow these rules:

- Do not add a report only to prove work happened.
- Do not add a manifest for every task.
- Do not generate review reports by default.
- Do not create next-plan chains.
- First update main docs such as PROJECT_STATUS, DATA_SOURCE_STRATEGY, or
  FOTMOB_CURRENT_STATE when the conclusion is long-lived.
- Then consider whether a new report is still needed.
- Every new document must have a clear reader and lifecycle.
- File names must be stable, short enough to scan, and searchable.
- Machine manifests must not be treated as human-facing status docs.
- Temporary exploration should stay local unless explicitly approved.

## Phase1 Source-of-Truth Summary Status

Phase1 source-of-truth cleanup updates only active summary locations. It does
not delete, move, rename, or archive files.

Active source-of-truth status after Phase1:

| Area | Source of Truth | Status |
|---|---|---|
| Project status | docs/PROJECT_STATUS.md | planned/missing |
| Documentation governance | docs/DOCUMENTATION_GOVERNANCE.md | active |
| Codex workflow | docs/CODEX_WORKFLOW.md | active |
| Data source strategy | docs/DATA_SOURCE_STRATEGY.md | planned/missing |
| FotMob current state | docs/data/FOTMOB_CURRENT_STATE.md | active |
| Canonical match schema | docs/CANONICAL_MATCH_SCHEMA.md | planned/missing |
| Testing strategy | docs/TESTING_GUIDE.md | active |
| CI strategy | docs/GITHUB_ACTIONS_AUDIT_REPORT.md | evidence/needs_update |
| Data storage strategy | docs/DATA_MODEL_STORAGE_POLICY.md | active |

Long-lived project conclusions should be summarized in the active or planned
source-of-truth docs above. Existing reports and manifests remain evidence until
a future no-move archive-candidate phase marks lifecycle status explicitly.

## Cleanup Strategy

### Phase 0

- no deletion
- inventory only
- rules and checker

### Phase 1

- identify archive candidates
- update source-of-truth summaries
- no deletion

### Phase 2

- move superseded reports into archive
- preserve information
- avoid current-state regressions

### Phase 3

- enforce CI document budget
- require Documentation Impact
- block repeated report/review/decision/next-plan bundles
