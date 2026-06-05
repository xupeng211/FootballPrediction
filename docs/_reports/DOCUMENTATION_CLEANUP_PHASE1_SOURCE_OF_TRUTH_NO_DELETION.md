# Documentation Cleanup Phase1 Source of Truth No Deletion

- lifecycle: evidence
- phase: DOCUMENTATION-CLEANUP-PHASE1-SOURCE-OF-TRUTH-SUMMARY-NO-DELETION

## Summary

This phase only updates source-of-truth summaries and marks which document
classes should be treated as current truth. No files were deleted, moved,
renamed, or archived. No manifest, next-plan, review report, or decision report
was added. FotMob payload reconstruction remains deferred.

## Source of Truth Inventory

| Area | Preferred Source of Truth | Exists | Updated This PR | Notes |
|---|---|---|---|---|
| Project status | docs/PROJECT_STATUS.md | no | no | planned; do not auto-create |
| Documentation governance | docs/DOCUMENTATION_GOVERNANCE.md | yes | yes | active governance policy |
| Codex workflow | docs/CODEX_WORKFLOW.md | yes | yes | active Codex workflow policy |
| Data source strategy | docs/DATA_SOURCE_STRATEGY.md | no | no | planned; summarize later |
| FotMob current state | docs/data/FOTMOB_CURRENT_STATE.md | yes | yes | active FotMob state |
| Canonical match schema | docs/CANONICAL_MATCH_SCHEMA.md | no | no | planned; create after schema decision |
| Development workflow | docs/DEVELOPMENT_WORKFLOW.md | no | no | planned; do not auto-create |
| Testing strategy | docs/TESTING_GUIDE.md | yes | no | existing test guidance |
| CI strategy | docs/GITHUB_ACTIONS_AUDIT_REPORT.md | yes | no | evidence; needs current summary later |
| Data storage strategy | docs/DATA_MODEL_STORAGE_POLICY.md | yes | no | active storage policy |

## Current Project State Summary

- #1454 merged: FotMob safe parser/schema reuse plan is in `main`.
- #1455 merged: documentation governance and Codex workflow controls are in `main`.
- Documentation governance is active.
- Codex workflow controls are active.
- Phase0 counted 609 docs files, 358 reports, 172 manifests, 6 next-plan files,
  62 review reports, and 13 decision reports.
- No deletion has occurred.
- No archive operation has occurred.
- The current task is documentation governance, not FotMob feature development.

## FotMob / Data Source Summary

- FotMob historical raw detail success is acknowledged as evidence.
- The current endpoint route is still not restored as an active acquisition path.
- FotMob should be treated as an optional adapter, not the system root.
- The canonical match schema should be the stable internal root.
- High-risk browser/session/cookie/anti-bot assets remain not reactivated.
- The next FotMob technical task remains deferred until documentation governance
  cleanup confirms current source-of-truth and archive-candidate status.

## Reports That Should Not Be Treated As Source of Truth

The following document classes are historical evidence or machine support, not
current truth:

- old FotMob probe reports
- repeated review reports
- next-plan reports
- decision reports that were superseded by later current-state summaries
- machine manifests

## Archive Candidates For Phase2

These are candidates only. No files are moved in this phase.

| Candidate Pattern | Reason | Phase2 Action | Risk |
|---|---|---|---|
| docs/_reports/FOTMOB_* old probe/report chains | long exploration history | mark lifecycle status first | medium |
| docs/_manifests/* old machine manifests | machine snapshots are not source truth | map active vs evidence manifests | high |
| `*_REVIEW*.md` | repeated companion reviews | mark evidence or archive_candidate | medium |
| `*_NEXT_PLAN*.md` | next-plan chain creates stale direction | replace with source summary | low |
| superseded decision reports | decision state moved forward | promote active decision to source docs | medium |

## Phase2 Proposal

Recommended next task:

DOCUMENTATION-CLEANUP-PHASE2-ARCHIVE-CANDIDATE-MARKING-NO-MOVE

Phase2 should still avoid moving files. It should mark lifecycle status or
prepare an archive mapping table before any archive operation is authorized.

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
| Phase2 archive candidates identified | 5 |
