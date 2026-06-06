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

## Phase3B Review

Phase3B reviews the Phase3A mapping only. It does not delete, move, rename, or
archive files. Filename pattern alone is not enough to approve a future move.

| Candidate | Current proposed action | Phase3B classification | Reason | Evidence replacement | Risk | Future action |
|---|---|---|---|---|---|---|
| `docs/_reports/FOTMOB_*` old probe chains | Move to `docs/_archive/_reports/FOTMOB_*` | evidence_keep_in_place_for_now | FotMob reports may contain historical success, endpoint failure, raw payload, or anti-bot boundary evidence. | `docs/data/FOTMOB_CURRENT_STATE.md` only partially preserves this history. | high | Keep in place until owner confirms specific files are summarized. |
| `docs/_reports/*_REVIEW*.md` | Move to `docs/_archive/_reports/*_REVIEW*.md` | needs_owner_review | Some review reports may contain unique validation or safety notes. | Active docs and PR bodies may not preserve all detail. | medium | Review specific files before any move. |
| `docs/_reports/*_NEXT_PLAN*.md` | Move to `docs/_archive/_reports/*_NEXT_PLAN*.md` | needs_owner_review | Next-plan files may include unresolved blockers. | `docs/CODEX_WORKFLOW.md` preserves workflow rules, not every blocker. | medium | Move only after blocker content is copied or closed. |
| `docs/_reports/*_DECISION*.md` | Move to `docs/_archive/_reports/*_DECISION*.md` | evidence_keep_in_place_for_now | Decisions may be current architecture evidence until ADR/source summary exists. | `docs/DOCUMENTATION_GOVERNANCE.md` defines policy but not every decision. | high | Keep in place until replacement summary or ADR is reviewed. |
| `docs/_manifests/*.json` | Move to `docs/_archive/_manifests/*.json` | blocked_do_not_move | Manifest references and automation consumers are not audited. | Matching report/source summary is not verified per file. | high | Do not move until dependency scan and owner review complete. |
| `docs/_reports/FOTMOB_CONTROLLED_JSON_PROBE_NO_WRITE_REVIEW.md` | Move to `docs/_archive/_reports/FOTMOB_CONTROLLED_JSON_PROBE_NO_WRITE_REVIEW.md` | evidence_keep_in_place_for_now | Specific FotMob endpoint review may preserve no-write and failure-boundary evidence. | `docs/data/FOTMOB_CURRENT_STATE.md` summarizes but may not include probe detail. | medium | Keep in place until endpoint findings are summarized. |
| `docs/_reports/FOTMOB_ENDPOINT_RUNTIME_CANDIDATE_PROBE_NEXT_PLAN.md` | Move to `docs/_archive/_reports/FOTMOB_ENDPOINT_RUNTIME_CANDIDATE_PROBE_NEXT_PLAN.md` | needs_owner_review | Could contain unresolved endpoint discovery blocker details. | `docs/CODEX_WORKFLOW.md` preserves workflow order only. | medium | Owner must confirm blockers are obsolete or summarized. |
| `docs/_reports/FOTMOB_CONTROLLED_JSON_PROBE_NO_WRITE_ENDPOINT_DECISION.md` | Move to `docs/_archive/_reports/FOTMOB_CONTROLLED_JSON_PROBE_NO_WRITE_ENDPOINT_DECISION.md` | evidence_keep_in_place_for_now | Endpoint decision may preserve historical route and no-write rationale. | `docs/data/FOTMOB_CURRENT_STATE.md` only summarizes current boundary. | high | Keep until decision content is summarized or owner approves. |

Phase3B result: no candidate is safe for automatic future move. A future move
task must use a smaller, owner-approved candidate list.

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
