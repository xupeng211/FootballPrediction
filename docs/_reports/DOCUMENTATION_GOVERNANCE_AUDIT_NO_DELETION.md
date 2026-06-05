# Documentation Governance Audit No Deletion

- lifecycle: evidence
- phase: DOCUMENTATION-GOVERNANCE-AND-CODEX-WORKFLOW-CONTROL-PHASE0-NO-DELETION

## Summary

This phase is inventory and governance only. It deletes no files, moves no files,
renames no files, and archives no files. The goal is to establish document
classes, PR documentation budgets, Codex workflow controls, and a checker before
any cleanup phase starts.

## Inventory

Baseline counts were taken before this Phase 0 PR added governance files.

| Item | Count |
|---|---:|
| total docs files | 609 |
| total markdown files | 428 |
| total json manifest files | 175 |
| docs/_reports count | 358 |
| docs/_manifests count | 172 |
| docs/_fixtures count | 2 |
| docs/_archive count | 0 |
| root docs count | 33 |
| FotMob-related report count | 166 |
| duplicate-looking report count | 79 |
| next-plan count | 6 |
| review-report count | 62 |
| decision-report count | 13 |

## Top Problem Areas

- FotMob report chain too long: 166 report files include FotMob in the name.
- Manifest proliferation: 172 files live under `docs/_manifests`.
- Review/decision/next-plan repetition: 79 report files match those patterns.
- Source-of-truth unclear: most proposed root-level current-state docs are absent.
- Stale docs risk: phase reports can outlive the conclusion they supported.
- Codex task report pattern: small tasks have created report/review/plan bundles.

## Proposed Source of Truth Docs

| Path | Status | Action |
|---|---|---|
| docs/PROJECT_STATUS.md | missing/planned | Create in Phase 1 or later. |
| docs/DATA_SOURCE_STRATEGY.md | missing/planned | Create in Phase 1 or later. |
| docs/FOTMOB_CURRENT_STATE.md | missing/planned | Reconcile with existing subpath doc. |
| docs/data/FOTMOB_CURRENT_STATE.md | exists/needs_update | Summarize active FotMob state. |
| docs/CANONICAL_MATCH_SCHEMA.md | missing/planned | Create only after schema direction. |
| docs/DOCUMENTATION_GOVERNANCE.md | added by this PR | Governance source of truth. |
| docs/CODEX_WORKFLOW.md | added by this PR | Codex workflow source of truth. |
| docs/DEVELOPMENT_WORKFLOW.md | missing/planned | Create only when scoped. |

## Archive Candidates

These are candidates only. No files are moved in this phase.

| Path | Reason | Suggested Action | Risk |
|---|---|---|---|
| docs/_reports/FOTMOB_PAYLOAD_SHAPE_RECONSTRUCTION_NEXT_PLAN.md | next-plan artifact | Summarize then archive candidate | low |
| docs/_reports/FOTMOB_SAFE_PARSER_SCHEMA_REUSE_PLAN_NO_WRITE_REVIEW.md | companion review | Keep evidence, mark superseded | low |
| docs/_reports/FOTMOB_ENDPOINT_RUNTIME_CANDIDATE_PROBE_NEXT_PLAN.md | next-plan chain | Summarize active result first | medium |
| docs/_reports/FOTMOB_HYDRATION_KEYSPACE_REVIEW_NEXT_PLAN.md | next-plan chain | Summarize active result first | medium |
| docs/_reports/FOTMOB_CONTROLLED_ENDPOINT_CANDIDATE_PROBE_NO_WRITE_REVIEW.md | duplicate review | Archive after source summary | medium |
| docs/_reports/FOTMOB_LIGUE1_ADG60_LIVE_FETCH_*_REVIEW.md | repeated batch reviews | Collapse into one summary | medium |
| docs/_manifests/fotmob_safe_parser_schema_reuse_plan_no_write_manifest.json | machine artifact | Link from source summary only | low |
| docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.*.json | phase snapshots | Preserve, then archive candidates | high |

## Duplicate / Superseded Candidates

| Candidate | Reason | Phase 1 handling |
|---|---|---|
| FOTMOB_*_REVIEW.md companion files | Repeat report checks | Mark evidence or archive_candidate. |
| FOTMOB_*_DECISION*.md files | Decision docs not in ADR form | Promote active decisions to source docs. |
| FOTMOB_*_NEXT_PLAN.md files | Next-plan chain | Replace with one next task in source docs. |
| FotMob ADG numbered reports | Long phase sequence | Identify latest active summary. |
| fotmob_pageprops_v2 phase manifests | Machine snapshot chain | Keep only current state references active. |
| PR body reports | Not durable source of truth | Mirror lasting conclusions into docs. |

## Phase 1 Cleanup Proposal

- no deletion
- update source-of-truth summaries
- mark superseded reports
- prepare archive move candidates
- add Documentation Impact template to PR guidance
- optionally add CI doc guard later

## Safety

| Item | Value |
|---|---|
| files_deleted | 0 |
| files_moved | 0 |
| files_renamed | 0 |
| branch_cleanup | false |
| destructive_action | false |
