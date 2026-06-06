# Documentation Cleanup Phase2 Archive Candidate Marking No Move

- lifecycle: phase-artifact

## Summary

This phase only marks archive candidates and lifecycle status patterns. It did
not delete, move, rename, archive, add manifests, add next-plans, or continue
FotMob development. It prepares Phase3 moves without changing evidence files.

## Lifecycle Definitions

| Lifecycle | Meaning | Can Codex Use As Current Truth |
|---|---|---|
| active | Current source-of-truth doc or current valid conclusion. | yes |
| evidence | Historical proof that can support current docs. | limited |
| superseded | Replaced by a newer source-of-truth summary. | no |
| archive_candidate | Candidate for future archive move, not moved yet. | no |
| archived | Already moved to archive and not used for current decisions. | no |

## Active Source of Truth Docs

| Area | Active Document | Status | Notes |
|---|---|---|---|
| Documentation governance | docs/DOCUMENTATION_GOVERNANCE.md | active | Defines budgets and lifecycle rules. |
| Codex workflow | docs/CODEX_WORKFLOW.md | active | Defines task and PR behavior. |
| Documentation cleanup phase1 status | docs/_reports/DOCUMENTATION_CLEANUP_PHASE1_SOURCE_OF_TRUTH_NO_DELETION.md | evidence | Phase1 summary and handoff. |
| FotMob current state | docs/data/FOTMOB_CURRENT_STATE.md | active | Current FotMob safety boundary. |
| Data source strategy | docs/DATA_SOURCE_STRATEGY.md | planned/missing | Create only when scoped. |
| Project status | docs/PROJECT_STATUS.md | planned/missing | Create only when scoped. |
| Canonical match schema | docs/CANONICAL_MATCH_SCHEMA.md | planned/missing | Create after schema direction review. |

## Archive Candidate Patterns

| Pattern | Lifecycle | Reason | Phase3 Candidate Action | Risk |
|---|---|---|---|---|
| `docs/_reports/FOTMOB_*` old probe chains | archive_candidate | Current FotMob state now lives in source-of-truth docs. | Map before moving. | May contain needed evidence. |
| `docs/_reports/*_REVIEW*.md` | archive_candidate | Review conclusions are often repeated later. | Keep only linked evidence. | Could hide audit trail. |
| `docs/_reports/*_NEXT_PLAN*.md` | archive_candidate | Next-plan chains are not current truth. | Replace with active workflow summary. | Some blockers may be unique. |
| `docs/_reports/*_DECISION*.md` | archive_candidate | Decisions need source-of-truth summaries. | Confirm supersession first. | Could remove context from current docs. |
| `docs/_manifests/*.json` | evidence | Machine files are not human current-state docs. | Archive stale manifests after mapping. | Automation may still reference some. |
| old endpoint probe reports after #1453/#1454 | archive_candidate | #1454 established safe reuse and blocked risky paths. | Link as evidence, then move. | Endpoint history may matter. |
| old documentation audit reports after Phase1/Phase2 | evidence | Audits prove process but should not drive current state alone. | Keep until Phase3 map review. | Needed for governance history. |
| redundant Codex final report style docs if any | archive_candidate | PR bodies and active docs should carry current status. | Move only after owner review. | May contain missing validation details. |

## Explicit Do-Not-Archive-Yet List

| Path or Pattern | Reason |
|---|---|
| docs/DOCUMENTATION_GOVERNANCE.md | Active governance source of truth. |
| docs/CODEX_WORKFLOW.md | Active Codex workflow source of truth. |
| docs/_reports/DOCUMENTATION_GOVERNANCE_AUDIT_NO_DELETION.md | Phase0 evidence for current cleanup. |
| docs/_reports/DOCUMENTATION_CLEANUP_PHASE1_SOURCE_OF_TRUTH_NO_DELETION.md | Phase1 evidence and handoff. |
| docs/_reports/DOCUMENTATION_CLEANUP_PHASE2_ARCHIVE_CANDIDATE_MARKING_NO_MOVE.md | Current Phase2 lifecycle map. |
| docs/data/FOTMOB_CURRENT_STATE.md | Active FotMob current-state doc. |
| any report still needed to validate #1454/#1455/#1456 history | Keep until merge history is fully mapped. |

## Superseded Candidate Examples

| Path or Pattern | Superseded By | Reason |
|---|---|---|
| old FotMob endpoint failure probe reports | docs/data/FOTMOB_CURRENT_STATE.md | Current state summarizes allowed and blocked paths. |
| repeated FotMob review reports | docs/data/FOTMOB_CURRENT_STATE.md | Reviews should become evidence, not current truth. |
| old next-plan reports | docs/CODEX_WORKFLOW.md | Active workflow order belongs in workflow docs. |
| superseded decision reports | future source-of-truth summary | Candidate only until summary confirms replacement. |

If filenames are not enough to prove supersession, mark only as candidate. A
source-of-truth summary must confirm replacement before archive move.

## Phase3 Safety Preconditions

Phase3 requires clean `main`, updated source-of-truth docs, reviewed archive
map, PR body entries for every moved file, and rollback plan. It must touch no
business, data pipeline, raw artifact, model artifact, or CI workflow files. It
must delete no docs, move only confirmed candidates into `docs/_archive/`, and
preserve original relative paths or record a mapping table.

## Codex Usage Rules After Phase2

Codex must read active docs first. Evidence can support historical claims but
cannot override active docs. Superseded and archive_candidate docs cannot be
used as current truth. If active docs conflict with a report, active docs win.
If active docs are missing, update source-of-truth docs instead of extending a
report chain.

## Phase3 Proposal

DOCUMENTATION-CLEANUP-PHASE3-ARCHIVE-MOVE-PLAN-NO-DELETION

Phase3 should still delete nothing. It may only move confirmed candidates into
`docs/_archive/` after a reviewed mapping table is available.

## Safety

| Item | Value |
|---|---|
| Files deleted | 0 |
| Files moved | 0 |
| Files renamed | 0 |
| Archive operation performed | no |
| New manifests added | 0 |
| New next-plans added | 0 |
| Business code changed | no |
| FotMob code changed | no |
| DB used | no |
| Browser automation used | no |
| Scraper run | no |

## Documentation Impact

| Item | Value |
|---|---|
| Source-of-truth docs updated | 3 |
| New reports added | 1 |
| New manifests added | 0 |
| Existing docs deleted | 0 |
| Existing docs moved | 0 |
| Existing docs renamed | 0 |
| Archive candidate patterns identified | 8 |
| Do-not-archive-yet patterns identified | 7 |
