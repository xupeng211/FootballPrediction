# Documentation Cleanup Phase3A Archive Move Plan No Deletion No Move

- lifecycle: phase-artifact

## Summary

Phase3A creates a proposed archive move mapping only. It does not delete, move,
rename, archive, create manifests, create next-plans, or continue FotMob work.
All destinations below are proposed paths for future review, not executed moves.

## Archive Move Mapping

| Candidate file or pattern | Current lifecycle status | Proposed archive destination | Reason for archive candidacy | Evidence/source-of-truth replacement | Risk level | Do-not-move-yet reason if uncertain | Rollback plan | Owner review requirement |
|---|---|---|---|---|---|---|---|---|
| `docs/_reports/FOTMOB_*` old probe chains | archive_candidate | `docs/_archive/_reports/FOTMOB_*` | Current FotMob state is summarized elsewhere. | `docs/data/FOTMOB_CURRENT_STATE.md` | high | Some reports may validate #1454 history. | Move back to original path. | Required before any move. |
| `docs/_reports/*_REVIEW*.md` | archive_candidate | `docs/_archive/_reports/*_REVIEW*.md` | Repeated review reports should become evidence. | Active source-of-truth docs and PR bodies. | medium | Keep if it contains unique validation. | Move back to original path. | Required before any move. |
| `docs/_reports/*_NEXT_PLAN*.md` | archive_candidate | `docs/_archive/_reports/*_NEXT_PLAN*.md` | Next-plan chains should not drive current state. | `docs/CODEX_WORKFLOW.md` | medium | Keep if it has unresolved blocker detail. | Move back to original path. | Required before any move. |
| `docs/_reports/*_DECISION*.md` | archive_candidate | `docs/_archive/_reports/*_DECISION*.md` | Decisions need durable summaries or ADRs. | `docs/DOCUMENTATION_GOVERNANCE.md` or future ADR. | high | Confirm no current architecture decision is lost. | Move back to original path. | Required before any move. |
| `docs/_manifests/*.json` | evidence | `docs/_archive/_manifests/*.json` | Machine artifacts are not current human docs. | Matching report or source-of-truth summary. | high | Automation references must be checked first. | Move back to original path. | Required before any move. |
| `docs/_reports/FOTMOB_CONTROLLED_JSON_PROBE_NO_WRITE_REVIEW.md` | archive_candidate | `docs/_archive/_reports/FOTMOB_CONTROLLED_JSON_PROBE_NO_WRITE_REVIEW.md` | Covered by current FotMob safety state. | `docs/data/FOTMOB_CURRENT_STATE.md` | medium | Verify no unique endpoint guard remains. | Move back to original path. | Required before any move. |
| `docs/_reports/FOTMOB_ENDPOINT_RUNTIME_CANDIDATE_PROBE_NEXT_PLAN.md` | archive_candidate | `docs/_archive/_reports/FOTMOB_ENDPOINT_RUNTIME_CANDIDATE_PROBE_NEXT_PLAN.md` | Superseded by active workflow ordering. | `docs/CODEX_WORKFLOW.md` | medium | Verify no blocker is missing from active docs. | Move back to original path. | Required before any move. |
| `docs/_reports/FOTMOB_CONTROLLED_JSON_PROBE_NO_WRITE_ENDPOINT_DECISION.md` | archive_candidate | `docs/_archive/_reports/FOTMOB_CONTROLLED_JSON_PROBE_NO_WRITE_ENDPOINT_DECISION.md` | Historical decision should be evidence only. | `docs/data/FOTMOB_CURRENT_STATE.md` | high | Confirm decision is summarized before move. | Move back to original path. | Required before any move. |

## Do Not Move Yet

| Candidate | Reason |
|---|---|
| `docs/DOCUMENTATION_GOVERNANCE.md` | Active governance source of truth. |
| `docs/CODEX_WORKFLOW.md` | Active Codex workflow source of truth. |
| `docs/data/FOTMOB_CURRENT_STATE.md` | Active FotMob current-state source of truth. |
| `docs/_reports/DOCUMENTATION_GOVERNANCE_AUDIT_NO_DELETION.md` | Phase0 evidence for cleanup history. |
| `docs/_reports/DOCUMENTATION_CLEANUP_PHASE1_SOURCE_OF_TRUTH_NO_DELETION.md` | Phase1 evidence and source-of-truth handoff. |
| `docs/_reports/DOCUMENTATION_CLEANUP_PHASE2_ARCHIVE_CANDIDATE_MARKING_NO_MOVE.md` | Phase2 lifecycle map. |
| `docs/_reports/DOCUMENTATION_CLEANUP_PHASE3A_ARCHIVE_MOVE_PLAN_NO_DELETION_NO_MOVE.md` | Current proposed plan. |

## Owner Review Requirement

No future move may happen until an owner reviews the mapping, confirms every
source path and destination, and verifies the source-of-truth replacement. A
future move PR must list every moved file and keep a rollback plan.

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
| Source-of-truth docs updated | 2 |
| Phase reports updated | 1 |
| New reports added | 1 |
| New manifests added | 0 |
| Existing docs deleted | 0 |
| Existing docs moved | 0 |
| Existing docs renamed | 0 |
| Candidate patterns reviewed | 5 |
| Specific files mapped | 3 |
| Do-not-move-yet items | 7 |
| High-risk items excluded | 4 |

## Next Recommended Task

DOCUMENTATION-CLEANUP-PHASE3B-REVIEW-ARCHIVE-MOVE-PLAN
