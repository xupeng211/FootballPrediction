# Project Status

- lifecycle: current-state
- owner: project governance

Last updated: 2026-06-24

## ci_local_parity_preflight_phase1 completed

- **ci_local_parity_preflight_phase1** — local PR Gate preflight added.
  - New script: `scripts/ops/local_pr_gate_preflight.py`
  - New tests: `tests/unit/test_local_pr_gate_preflight.py` (23 tests)
  - New Makefile target: `make pr-gate-local PR_BODY=<file>`
  - New npm script: `npm run pr-gate-local`
  - Goal: improve remote CI first-pass rate by catching failures locally.
  - This is workflow / CI parity hardening, NOT SC-002 closure.
  - Does NOT change 6/14 runtime guarded state.
  - Does NOT change remaining 8 confirmed write paths.
  - Does NOT change 8 indirect write paths.
  - Does NOT change 5 manual review candidates.
  - Does NOT unlock training / data expansion / real DB write.
  - SC-002 remains partial mitigation only.
  - Training / data expansion / real DB write remain blocked.

## Current baseline

- `main` includes PR #1463 (P0 AI Workflow Gate CI enforcement).
- `main` includes PR #16XX (`agent_workflow_rules_hardening_phase1`) — three-layer agent
  workflow discipline codified into the repo:
  1. **Resident rules**: `CLAUDE.md` now contains comprehensive non-negotiable agent
     workflow hardening rules (branch, scope, safety, SC-002, PR, task-type, post-merge
     discipline). Agents no longer need repeated long-form prompts for basic discipline.
  2. **PR template**: `.github/pull_request_template.md` now includes `## SC-002 status`,
     `## Remaining risks`, and a 16-item Agent Workflow Hardening Checklist.
  3. **CI / AI Workflow Gate**: `scripts/ops/ai_workflow_gate.py` enforces:
     - New required sections: `## SC-002 status`, `## Remaining risks`
     - Forbidden rewrite file patterns (`*_v2.py`, `*_final.js`, etc.) for new files
     - Forbidden safety claims (prematurely declaring SC-002 resolved or training/DB write unblocked)
     - Large risky change detection (deletion/rename/scanner-count thresholds)
     - Existing gates preserved (Phase2A Python, Phase2B SQL, Phase2 JS DB write)
  - SC-002 remains partial mitigation only.
  - training / data expansion / real DB write remain blocked.
- `main` includes PR #1464 (local CI gatekeeper entrypoint).
- `main` includes PR #1567 (authoritative workflow enforcement dry-run).
- `main` includes PR #1569 (p0_db_write_safety_gate_fix_phase1 — unified guard + 8 scripts).
- `p0_db_write_guard_hardening_production_host_block` hardens the guard: production-like
  DB hosts are now blocked by default (previously warning-only). No production override exists.
- `p0_db_write_safety_gate_fix_phase2` adds guard to 8 more P0 scripts/ops entrypoints.
  Phase1 + Phase2 + Phase3 + Phase4 + Phase5 + Phase7 = 43 scripts now protected. SC-002 remains partial mitigation only.
- Remote GitHub Actions `production-gate.yml` is the final CI authority.
- Local `make ci-local-pr` is a pre-push helper, not a full replacement for remote CI.
- AI workflow governance rules are enforced by:
  - `scripts/ops/ai_workflow_gate.py` (CI-enforced workflow and documentation checks)
  - `scripts/devops/gatekeeper.sh` (CI-enforced, multi-phase)
  - `scripts/ops/documentation_governance_check.py` (standalone checker)
  - `.github/pull_request_template.md` (mandatory PR structure)
  - `docs/CODEX_WORKFLOW.md` (Codex task rules)
  - `docs/DOCUMENTATION_GOVERNANCE.md` (doc lifecycle rules)

## Current SC-002 status (DB write safety gate)

- SC-002 is **not fully fixed**. This remains partial mitigation only.
- A unified guard helper (`scripts/ops/helpers/db_write_guard.js`) has been added.
- Production-like DB host (RDS, Cloud SQL, Supabase, etc.) is hard blocked by default.
  No production override exists. No `ALLOW_PRODUCTION_DB_WRITE` bypass variable exists.
- `p0_db_write_safety_gate_fix_phase1` (#1569): 8 scripts integrated.
- `p0_db_write_guard_hardening_production_host_block` (#1570): production host hard block.
- `p0_db_write_safety_gate_fix_phase2` (#1571): 8 more scripts integrated.
- `db_write_guard_static_enforcement_dry_run` (#1572): static scanner deployed.
- `p0_db_write_safety_gate_fix_phase3` (#1573): 8 more scripts integrated.
- `db_write_guard_static_enforcement_fix_phase1` (#1575): advisory warning in
  ai_workflow_gate.py for new/modified unguarded scripts/ops JS files.
- `p0_db_write_safety_gate_fix_phase4` (#1576): 6 more scripts integrated.
- `p0_db_write_safety_gate_fix_phase5` (#1579): 7 more scripts integrated.
- `p0_db_write_safety_gate_fix_phase6` (#1580): 5 more scripts integrated.
- `p0_db_write_safety_gate_fix_phase7` (#1582): 1 script integrated.
- **Phase1 + Phase2 + Phase3 + Phase4 + Phase5 + Phase6 + Phase7 = 43 of 66 P0 scripts now guarded.**
- **db_write_guard_static_enforcement_fix_phase2** (#1583): changed-files enforcement
  upgraded from advisory to hard fail in ai_workflow_gate.py. New/modified unguarded
  scripts/ops JS files now cause CI failure. Historical full-scan candidates are
  explicitly categorized (NOT fixed) and exempt from hard fail.
- **sc002_closure_plan_phase0** (#1584): SC-002 closure plan documented in
  `docs/SC002_CLOSURE_PLAN.md`. This is the authoritative SC-002 status reference.
  SC-002 remains partial mitigation only. 43/66 guarded. 22 categorized, not fixed.
  21 additional browser/Playwright scripts identified as skipped_complex (total 43).
  Training, data expansion, and real DB write remain blocked.
- **specialized_browser_fotmob_pageprops_audit_phase1** (#1585): Static audit of all
  43 skipped_complex scripts completed. See `docs/SC002_BROWSER_FOTMOB_PAGEPROPS_AUDIT.md`.
  Key findings: 20 confirmed DB write paths, 14 read-only/no-DB, 4 need manual review,
  3 shared modules, 1 scraper/browser only, 1 possible indirect write.
  The gap is now precisely characterized: 28 scripts need guard/exclusion action.
  SC-002 remains partial mitigation only.
- **confirmed_write_path_guard_phase1_high_risk_browser_db** (#1586): Guard integration
  complete for the 2 highest-risk browser+DB skipped_complex scripts:
  `odds_sniper.js` and `fixture_harvester_l1.js`. Both now call `assertDbWriteAllowed()`
  before DB write operations. These are NOT part of the original 66 P0 — they are
  skipped_complex write paths now guarded.
- **confirmed_write_path_guard_phase2_batch1** (this PR): Guard integration for 3
  controlled-write scripts with INSERT INTO raw_match_data:
  `pageprops_v2_single_target_controlled_write.js`,
  `remaining_seeded_pageprops_v2_controlled_write.js`,
  `single_league_pageprops_v2_controlled_write_execute.js`.
  Remaining confirmed_write_path_needs_guard: 15 of 20.
  SC-002 remains partial mitigation only.
- **confirmed_write_path_guard_phase2_batch2** (this PR): Guard integration for 1
  FotMob raw JSON DB storage script with INSERT INTO fotmob_raw_match_payloads:
  `fotmob_adg60_raw_json_db_storage_no_feature_parse.js`.
  Now calls `assertDbWriteAllowed()` before INSERT query.
  6 confirmed write paths guarded. Remaining: 14 of 20.
  Deep static analysis revealed that 10+ of the remaining
  "confirmed_write_path_needs_guard" scripts are false positives (SELECT-only with
  active SQL enforcement wrappers, or no DB connection at all).
  SC-002 remains partial mitigation only.
- **sc002_allowlist_cleanup_phase1** (this PR): Formal reclassification of 15 scripts
  from `confirmed_write_path_needs_guard` to verified false positive categories:
  - 11 false_positive_select_only_with_active_wrapper (SELECT-only + queryReadOnly/safeSelect)
  - 2 false_positive_read_only_transaction (BEGIN READ ONLY + ROLLBACK + assertSelectOnlySql)
  - 1 false_positive_no_db_connection_static_scan (no pg import, fs/child_process only)
  - 1 false_positive_policy_or_regex_keyword_only (INSERT only in conflict_policy string)
  All 20 original confirmed_write_path classifications are now resolved (6 guarded, 14
  reclassified). **0 still_needs_guard remain.**
  4 needs_manual_review remain unchanged. 3 shared_module unchanged. 1
  possible_indirect_write unchanged. SC-002 remains partial mitigation only.
  Training, data expansion, and real DB write remain blocked.
- **shared_module_db_write_boundary_implementation_phase1** (#1592): HIGH priority
  guard implemented for `odds_harvest_pipeline.js` — the unguarded consumer discovered
  by the design phase. `assertDbWriteAllowed()` added in `upsertMappingAndOdds()` before
  BEGIN transaction, guarding INSERT/UPSERT on `matches_oddsportal_mapping` and `odds`
  tables. Same pattern as `odds_sniper.js` (Phase 1). Gatekeeper.js / gatekeeper.sh
  still pending. 8 needs_manual_review consumers still pending. No target script
  executed. No DB connection. No Playwright/browser run. SC-002 remains partial
  mitigation only. Training, data expansion, real DB write remain blocked.
- **gatekeeper_boundary_implementation** (this PR): MEDIUM priority guard implemented
  for `gatekeeper.js` and `gatekeeper.sh` — the CI infrastructure consumers of
  `dbBlueprint.js`. Both entrypoints now call `assertDbWriteAllowed()` before
  `runColdStartBlueprintCheck` (which triggers CREATE DATABASE, DROP DATABASE, and
  INSERT write probe on `matches`, `raw_match_data`, `matches_oddsportal_mapping`).
  Guard at consumer entrypoint, not module level. Guard pattern: `assertDbWriteAllowed({
  script: 'gatekeeper.js', tables: ['matches', 'raw_match_data',
  'matches_oddsportal_mapping'], operations: ['CREATE', 'DROP', 'INSERT'] })` (same
  pattern for gatekeeper.sh with script 'gatekeeper.sh'). dbBlueprint.js unchanged.
  No target script executed. No DB connection. No real DB write. No scraper/browser run.
  No training. No data expansion. No schema migration. 9 needs_manual_review consumers
  still pending (corrected count — PR body typo said 8). SC-002 remains partial mitigation
  only. Training, data expansion,
  real DB write remain blocked.
- **manual_review_phase1** (this PR): Static review and reclassification of all 14
  remaining `needs_manual_review` / `possible_indirect_write` scripts from both the
  shared-module design doc (9 dbBlueprint consumers) and the broader skipped_complex
  audit (4 pageProps + 1 possible_indirect_write). Full per-script evidence in
  `docs/SC002_MANUAL_REVIEW_PHASE1.md`. Results:
  - **7 already_guarded** (had guard from Phase1-7; design doc classification was stale):
    cleanup_csv_bulk_loader_import.js, purge_ghost_data.js, purge_orphans.js,
    raw_match_data_completeness_fidelity_audit.js, renewed_pageprops_v2_raw_write_execute.js
    (transitive via base), reset_database.js, seed_fotmob_sample.js
  - **3 false_positive_no_db_write_evidence** (SELECT-only or zero DB connection):
    fetch_and_adapt_euro_leagues.js, master_inventory.js, pageprops_v2_identity_contract_
    regression_execute.js, pageprops_v2_suspended_target_review_execute.js
  - **2 false_positive_select_only_with_active_wrapper**: all_seeded_pageprops_v2_
    canonical_read_verification.js, pageprops_v2_post_write_canonical_read_verification.js
  - **1 false_positive_read_only_transaction**: training_pipeline_smoke_dry_run.js
  - **0 confirmed_write_path_needs_guard**, **0 remaining needs_manual_review**
  - Count mismatch resolved: previous PR said "8" (typo), actual design-doc count is 9;
    combined with audit-doc 5 = 14 total reviewed
  - No guard implemented (all already guarded). No target script executed. No DB
    connection. No real DB write. No scraper/browser. SC-002 remains partial mitigation
    only. Training, data expansion, real DB write remain blocked.
- **shared_module_db_write_boundary_design_phase1** (#1591): Static design of shared
  module DB write boundary completed. 3 shared modules mapped with full consumer
  entrypoint inventory:
  - `dbBlueprint.js` (24 consumers, 3 write-capable, 18 read-only, 3 needs_manual_review)
  - `restoreMappingsWorkflow.js` (0 active consumers, dependency-injected write path)
  - `odds_harvest_pipeline.shared.js` (2 consumers: 1 guarded, 1 UNGUARDED gap found —
    `odds_harvest_pipeline.js`)
  Key findings: `odds_harvest_pipeline.js` is an unguarded CLI entrypoint consuming
  write SQL from the shared module (not in any prior audit or guard phase).
  `gatekeeper.js`/`gatekeeper.sh` use `runColdStartBlueprintCheck` (DB write path) with
  no guard. Consumer entrypoint map recommends guard at consumer level, not module level.
  No runtime behavior changed. SC-002 remains partial mitigation only.
  Training, data expansion, and real DB write remain blocked.
- Remaining 22 complex candidates categorized into:
  - `pageprops_pipeline` (9): pageProps/FotMob pipeline scripts
  - `fotmob_pipeline` (2): FotMob ingestion scripts
  - `shared_module` (3): shared helper modules consumed by entrypoints
  - `dry_run_or_audit` (8): dry-run, audit, preflight scripts
  - Plus 21 browser/Playwright scripts previously classified as `skipped_complex`
- Each remaining candidate has: explicit category, reason, reviewed_at, future_action.
  These are NOT counted as "guarded" and SC-002 is NOT "fully fixed".
- DB write safety status: **blocked / partial phase1-7 guards added**.
- Guard remains opt-in per script for historical files. New scripts touching
  `scripts/ops/` with DB write risk MUST integrate the guard or be explicitly
  allowlisted — enforced via CI hard fail on changed-files.
- Training and data expansion remain blocked.
- No real DB write is authorized.
- Changed-files hard fail scope: **scripts/ops/\*\*/\*.js only**. Python, SQL, and
  migration enforcement is not yet designed.

## Current operating rules

- One task / one branch / one PR.
- Do not work directly on `main`.
- Do not mix governance changes with runtime business code (CI-enforced).
- Do not start automatically. Recommended next task only after user confirmation (CI-enforced).
- PR body must include all mandatory sections: Scope, Documentation Impact, Safety Impact,
  Validation, CI Gate Scope, No-deletion/move/rename confirmation, Rollback Plan,
  Next Recommended Task.
- CI Gate Scope must state what validation proves and does not prove.
- If a PR adds or modifies `docs/_reports/*.md`, it must update an
  authoritative doc or give a concrete source-of-truth no-update reason in the
  PR body.

## Current allowed work

- Small docs-only source-of-truth updates (like this file).
- Read-only audits.
- Small, scoped CI/governance fixes that do not touch runtime code.
- SC-002 closure planning, governance, and documentation tasks.
- Future FotMob/data work only after explicit user confirmation and under
  read-only/no-write constraints.

## Current blocked work

- DB write and schema migration.
- Raw data write (`raw_match_data`).
- Real scraper and browser automation.
- Large archive moves (delete/move/rename of historical files).
- Automatic next-task execution.
- Mixed governance + business-code PRs.
- Implementation PRs that substitute reports/manifests/tests for runtime behavior change.
- Consecutive governance-only PRs without explicit human confirmation.
- Formal model training.
- Data expansion / large-scale raw acquisition.

## Current source-of-truth docs

| Doc | Status |
|---|---|
| `docs/PROJECT_STATUS.md` | active (this file) |
| `docs/DATA_SOURCE_STRATEGY.md` | active (created alongside this file) |
| `docs/CODEX_WORKFLOW.md` | active |
| `docs/DOCUMENTATION_GOVERNANCE.md` | active |
| `docs/data/FOTMOB_CURRENT_STATE.md` | active — read for FotMob state |
| `docs/AGENT_WORKFLOW.md` | active |
| `docs/SC002_CLOSURE_PLAN.md` | active — authoritative SC-002 status reference |
| `docs/SC002_BROWSER_FOTMOB_PAGEPROPS_AUDIT.md` | active — static audit of all 43 skipped_complex scripts |
| `docs/SC002_SHARED_MODULE_DB_WRITE_BOUNDARY_DESIGN.md` | active — shared module DB write boundary design |
| `docs/SC002_MANUAL_REVIEW_PHASE1.md` | active — manual review and reclassification of all needs_manual_review scripts |
| `docs/SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md` | active — Python/SQL/migration enforcement design |
| `docs/TESTING_GUIDE.md` | active — needs provenance review |
| `docs/GITHUB_ACTIONS_AUDIT_REPORT.md` | evidence/needs_update — stale CI references |

## Current technical debt posture

- `docs/_reports/` contains 434 historical report files as of the
  authoritative workflow enforcement dry-run.
- `docs/_manifests/` contains 171 historical manifest files.
- These are archived evidence; they should not be read as current truth.
- Bulk archive moves are planned but not yet executed.
- Stale docs (`GITHUB_ACTIONS_AUDIT_REPORT.md`, `TESTING_GUIDE.md`) should be
  reviewed and marked or superseded in small scoped PRs.
- Technical debt remains high enough to block data expansion and formal
  training. Current P0 debt includes DB write safety, cutoff strategy, training
  eligibility, and schema/init alignment.

## Current training and expansion posture

- Minimal training loop: connected for smoke-level validation only.
- Formal training: blocked.
- Formal cohort candidates / smoke-level candidates: 58.
- Formal candidates with odds: 0.
- Formal training must not start until eligibility, odds, cutoff-time policy,
  and DB write safety blockers are resolved.
- Data expansion: blocked by P0 technical debt and raw/write governance.
- DB write safety: blocked / partial phase1+phase2+phase3+phase4+phase5+phase6 guards added. The P0 DB
  write safety dry-run found 122 production DB-write risk files, including 66 P0
  files and 110 files with no safety gate. Phase1+Phase2+Phase3+Phase4+Phase5+Phase7 = 43 scripts/ops
  now guarded (Phase1+Phase2+Phase3+Phase4+Phase5+Phase7 = 43/66). A static enforcement dry-run scanner
  has been added to audit remaining coverage. SC-002 is partially mitigated, NOT
  fully fixed. Remaining scripts need Phase8+ or static enforcement.
- Authoritative document backflow: fix phase1 starts enforcement through the PR
  template, AI Workflow Gate, Documentation Governance, Codex Workflow, and this
  current-state update.

## Recent dry-run conclusions now reflected here

| Dry-run | Current conclusion |
|---|---|
| `formal_training_cohort_inventory_dry_run` | Formal training remains blocked; only 58 smoke-level candidates were found and formal candidates with odds = 0. |
| `technical_debt_workflow_audit_dry_run` | P0 technical debt blocks data expansion and formal training; priority debt is DB write safety, cutoff strategy, training eligibility, and schema/init alignment. |
| `p0_db_write_safety_gate_dry_run` | DB write safety remains blocked; 122 production DB-write risk files were found, P0 = 66, 110 lack gates, SC-002 remains unfixed. |
| `authoritative_workflow_enforcement_dry_run` | The project already has authoritative docs, but `_reports` has overgrown and AI agents were not forced to maintain current-state docs. |

## Current FotMob status

- FotMob data ingestion is blocked. See `docs/data/FOTMOB_CURRENT_STATE.md` for details.
- `raw_write_ready_count` is 0.
  **(Superseded 2026-06-11: retained raw storage has moved forward. 4 real FotMob raw
  payloads exist in `raw_match_data` with `data_version=fotmob_live_v1`, audited
  4/4 parseable, sha valid, inner matchId ok, 0 errors, 0 warnings. See
  `docs/data/FOTMOB_RETAINED_RAW_STAGE_STATUS.md`.)**
- No DB write, raw write, browser automation, or network data collection is authorized.
  **(Partial exception: the 4 retained raw rows above were written under explicit
  authorization in #1485 and #1486.)**
- Parser, schema, fixture, and validation assets from #1454 are safe to reuse as
  offline references only.

## Next recommended sequence

1. SC-002 closure plan phase0 completed. See `docs/SC002_CLOSURE_PLAN.md` for the
   authoritative SC-002 status, closure criteria, release gates, and recommended
   next tasks.
2. Phase1-7 = 43 scripts/ops entrypoints now guarded (~65% of P0).
3. Static enforcement dry-run scanner deployed for coverage auditing.
4. Changed-files hard fail enabled for new/modified unguarded scripts/ops JS files.
5. **All JS-level guard work is now complete.**
6. **python_sql_migration_enforcement_design_phase1** — Python/SQL/migration enforcement
   design completed. See `docs/SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md`.
7. **Python Phase2A static scanner + Phase2B SQL scanner completed.**
8. **Python Phase2C batch1 runtime guard completed (3 of 14 confirmed Python write paths).**
9. **Python Phase2C batch2 runtime guard completed (3 more of 14 confirmed Python write paths; 6 total guarded).**
10. **agent_workflow_rules_hardening_phase1 completed** — three-layer agent workflow
   discipline codified: resident rules (CLAUDE.md), PR template checklist, CI gate
   enforcement. Future tasks can reference these standing rules instead of long prompts.
10. SC-002 remains partial mitigation only.
11. Next recommended tasks (in priority order):
    - `python_runtime_guard_implementation_phase2C_batch3` — guard remaining 8
      confirmed Python write paths (8 of 14 remaining after batch1+batch2)
    - `python_indirect_write_path_design_phase1` — design approach for 8 indirect
      write paths
    - `python_manual_review_phase2D` — review 5 manual review candidates
    - `runtime_db_role_permission_review_phase1` — review DB-level role/permission model
    - `sc002_release_gate_checklist_phase1` — create detailed per-gate verification
      checklists
11. Keep formal training and data expansion blocked until DB write safety resolved
    and release gate criteria met.
12. Do not start model training, data expansion, raw-write work, scraper/browser
    automation automatically.
13. Do not start automatically. Recommended next task only after user confirmation.
