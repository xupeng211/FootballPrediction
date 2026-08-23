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

The project should keep a small set of main documents clear and current. AI
agents must not create several new reports for every task just to prove activity. New
documents need a reader, a lifecycle, and a reason they cannot be represented by
updating an existing source-of-truth document.

## Document Classes

### 1. Source of Truth Docs

Source of truth docs are long-lived documents that users and AI agents should
read first. They summarize current state and link to supporting evidence.

| Path | Status | Notes |
|---|---|---|
| README.md | active | `Canonical Business Entrypoints` is the formal business-entrypoint authority. |
| docs/PROJECT_MAP.md | active | Repository structure and Agent navigation map; not a progress ledger. |
| docs/PROJECT_VISION.md | active | Permanent North Star and target-system blueprint; not workflow, current-state, or execution authority. |
| docs/CAPABILITY_INDEX.md | active | Long-lived capability, asset, status, entrypoint, and authorization index. |
| docs/ACTIVE_MILESTONE.md | active | Current battle line, completed node, blockers, and next Owner decision. |
| docs/PROJECT_STATUS.md | active | Overall current state, blockers, and supporting completed history. |
| docs/DATA_SOURCE_STRATEGY.md | active | Current data-source strategy and gates. |
| docs/FOTMOB_CURRENT_STATE.md | not used | Do not create a parallel root-level FotMob authority. |
| docs/data/FOTMOB_CURRENT_STATE.md | active | FotMob acquisition, retention, and domain blocker current state. |
| docs/CANONICAL_MATCH_SCHEMA.md | planned | Canonical match payload and feature schema. |
| docs/MODEL_ARTIFACTS.md | active | Manifest, artifact-readiness, and activation boundary; candidate evidence remains external research state. |
| docs/DOCUMENTATION_GOVERNANCE.md | exists | This governance policy. |
| AGENTS.md | active |唯一 operational workflow authority for AI development. |
| docs/AGENT_WORKFLOW.md | active |唯一 detailed workflow explanation. |
| docs/DEVELOPMENT_WORKFLOW.md | planned | Human development workflow reference. |

If a listed document does not exist, mark it as planned. Do not create it unless
the task explicitly includes that scope.

`COMMAND_CENTER.md` is a historical snapshot and remains non-authoritative. It
must not be restored as the current project map or used to override the current
state documents above.

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
- They are an evidence library, not the current-state entrypoint.
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
- If a task allows a new report, the exact path must be listed. Broad patterns
  such as `docs/_reports/*.md`, `docs/_reports/*AUDIT*.md`,
  `docs/_reports/*NEXT_PLAN*.md`, `docs/_reports/*REVIEW*.md`, and
  `docs/_reports/*DECISION*.md` are prohibited.
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
| Adds docs/_reports artifact | yes/no |
| Manifests added | `<n>` |
| Source-of-truth docs updated | yes/no |
| Updated authoritative docs | `<paths>` |
| If not updated, explicit reason | `<required when no>` |
| Active conclusions reflected in PROJECT_STATUS.md | yes/no/n/a |
| Superseded docs identified | yes/no |
| Archive candidates identified | yes/no |
| Reason for new docs | `<short reason>` |
| Capability changed? | `yes` / `no` |
| Milestone changed? | `yes` / `no` |
| Canonical entrypoint changed? | `yes` / `no` |
| Current blocker changed? | `yes` / `no` |
| Data/model/authorization contract changed? | `yes` / `no` |
| Repository structure/authority navigation changed? | `yes` / `no` |
| Project vision / target-state changed? | `yes` / `no` |

## Source of Truth Rule

Any long-term conclusion must be recorded in source-of-truth docs. Phase reports
can support the conclusion, but they cannot permanently be the only place where
active truth lives.

`AGENTS.md`, `docs/AGENT_WORKFLOW.md`, `docs/PROJECT_VISION.md`, `docs/PROJECT_MAP.md`,
`docs/CAPABILITY_INDEX.md`, `docs/ACTIVE_MILESTONE.md`,
`docs/PROJECT_STATUS.md`, `docs/DOCUMENTATION_GOVERNANCE.md`,
`docs/DATA_SOURCE_STRATEGY.md`, `docs/data/FOTMOB_CURRENT_STATE.md`,
`docs/MODEL_ARTIFACTS.md`, and `README.md` are the existing authoritative
update targets for workflow, navigation, capability, milestone, model, and
current-state backflow. Their roles are distinct; none is a replacement for
another.

Any PR that adds or modifies `docs/_reports/*.md` must either:

- update at least one relevant authoritative doc in the same PR, or
- state a concrete source-of-truth no-update reason in the PR body.

The no-update reason must not be a hollow placeholder such as `n/a`, `none`,
`not needed`, `no`, `无`, or `无需`. "Update later" must not become the
default reason for repeated report-only work. Key dry-run conclusions that
change active project status must be reflected in `docs/PROJECT_STATUS.md`.

When a phase report changes project direction, the next governance or cleanup
task should update the relevant source-of-truth document with a short summary and
links to evidence.

## Documentation Backflow Contract

This is a lightweight contract over the existing documents, not a second project
map or workflow authority. A PR that changes a long-lived business capability,
canonical entrypoint, capability status, training/evaluation behavior,
data/model/authorization contract, major blocker, milestone completion, North Star,
target architecture, or vision maturity state must
either update the relevant current-state source of truth or provide a concrete
no-update reason in its `Documentation Impact` table.

The stable mapping is intentionally small:

| Declared impact | Required current-state backflow |
|---|---|
| Capability or asset status | `docs/CAPABILITY_INDEX.md` |
| Active milestone, major DONE, or next Owner decision | `docs/ACTIVE_MILESTONE.md` |
| Canonical business entrypoint | `README.md` + `docs/CAPABILITY_INDEX.md` |
| Project-wide current blocker or stage | `docs/PROJECT_STATUS.md` |
| FotMob acquisition/retention/domain blocker | `docs/data/FOTMOB_CURRENT_STATE.md` |
| Workflow or authorization semantics | `AGENTS.md` + `docs/AGENT_WORKFLOW.md` |
| Repository structure or authority navigation | `docs/PROJECT_MAP.md` |
| North Star, target architecture, or vision maturity state | `docs/PROJECT_VISION.md` |

The PR body uses machine-readable `yes` / `no` declarations for capability,
milestone, canonical entrypoint, current blocker, data/model/authorization
contract, repository-navigation, and project-vision impact. A positive capability/status/entrypoint/milestone/blocker/contract/vision
declaration cannot be bypassed by a generic no-update sentence. A bugfix that
does not change the declared long-lived semantics may use a specific reason that
states what changed and why lifecycle, status, entrypoint, contract, blocker, or
navigation truth did not change. `n/a`, `none`, `not needed`, `no update needed`,
`无`, and `无需` are invalid reasons, including when a classified category is
explicitly declared unchanged.

When `Project vision / target-state changed?` is `yes`, the PR must update and
declare `docs/PROJECT_VISION.md`; a no-update reason is never an acceptable
substitute. A routine implementation bugfix may set it to `no` when its target
state is unchanged and explain that boundary concretely.

The existing `scripts/ops/ai_workflow_gate.py` required CI step calls its small
`scripts/ops/helpers/documentation_backflow.py` path classifier. It checks only
the changed paths plus the PR declaration; it does not infer business meaning,
rewrite Markdown, create manifests, or add a new required GitHub check. The
existing cleanup checker remains focused on its allowlist/destructive-operation
scope and is reused for governance-file safety.

Do not create replacement authority files such as `PROJECT_STATUS_V2.md`,
`NEW_RULES.md`, `NEW_WORKFLOW.md`, or similar parallel entrypoints to bypass the
existing authoritative docs.

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
- Do not add reports, manifests, review reports, decision reports, or next-plan
  files unless the task explicitly allows the exact path.
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
| Project status | docs/PROJECT_STATUS.md | active |
| Documentation governance | docs/DOCUMENTATION_GOVERNANCE.md | active |
| Agent workflow authority | AGENTS.md + docs/AGENT_WORKFLOW.md | active |
| Data source strategy | docs/DATA_SOURCE_STRATEGY.md | active |
| FotMob current state | docs/data/FOTMOB_CURRENT_STATE.md | active |
| Canonical match schema | docs/CANONICAL_MATCH_SCHEMA.md | planned/missing |
| Testing strategy | docs/TESTING_GUIDE.md | active |
| CI strategy | `.github/workflows/production-gate.yml` + GitHub ruleset/API | active/current |
| Data storage strategy | docs/DATA_MODEL_STORAGE_POLICY.md | active |

Long-lived project conclusions should be summarized in the active or planned
source-of-truth docs above. Existing reports and manifests remain evidence until
a future no-move archive-candidate phase marks lifecycle status explicitly.

## Phase2 Archive Candidate Marking Status

Phase2 only marks archive candidates and lifecycle states. It does not delete,
move, rename, or archive files.

Lifecycle states now used for documentation cleanup are:

- `active`
- `evidence`
- `superseded`
- `archive_candidate`
- `archived`

Phase3 may execute an archive move only after a reviewed mapping table exists.
Deletion remains forbidden by default. A stale setup/instruction file may be
removed in a separately scoped cleanup change only after a caller inventory
proves that it has no supported entry, automation caller, or configuration
dependency, and the exact path is recorded in the governance checker. Active
docs take priority over phase reports, and Codex must not treat `superseded` or
`archive_candidate` files as current conclusions.

## Phase3A Archive Move Plan Status

Phase3A creates a proposed archive move mapping only. It does not delete, move,
rename, archive, or create `docs/_archive/` content.

Proposed archive destinations are not authorization to move files. Owner review
is required before any later task can move archive candidates. Active docs still
take priority over reports. Deletion remains forbidden unless the narrowly
scoped, evidence-backed exception above is satisfied.

## AI Guardrail Hardening Status

AI workflow guardrails now require one task, one branch, and one PR. Tasks must
not combine feature work with cleanup, audit with repair, merge with new work,
or documentation governance with business code.

Merge-only tasks are zero-change tasks. They may verify state, merge the
approved PR, sync local `main`, delete the task branch, and report final state,
but they must not edit files or start follow-up work.

Destructive operations require an exact owner-approved file list, explicit
destructive flag, rollback plan, and no broad patterns. Archive moves require an
owner-approved candidate list; filename patterns such as `FOTMOB_*`,
`*_REVIEW*`, `*_DECISION*`, and `*_NEXT_PLAN*` are not move authorization.

Every PR must state CI Gate Scope. Production Gate success does not prove
full-system coverage, model/data quality, or authorization for unscoped runtime,
DB, browser, scraper, network, or raw-write work. Host validation unavailable
results must be separated from container validation.

High-risk FotMob, scraper, browser, Playwright, Chromium, cookie/session,
captcha, proxy rotation, DB write, raw write, and network data collection work
remains blocked unless a future task explicitly authorizes the exact scope.

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

- mark active, evidence, superseded, and archive_candidate docs
- no move
- no deletion

### Phase 3

- create and review archive move mapping before moving anything
- move confirmed archive_candidate files only after owner review
- preserve information
- avoid current-state regressions
