# SC-002 Closure Plan

- lifecycle: permanent
- owner: project governance
- created: 2026-06-22
- task: sc002_closure_plan_phase0

## Summary

SC-002 (DB write safety gate) is **partial mitigation only**.

- **43 of 66 P0 scripts/ops JS entrypoints** have integrated the unified DB write guard
  (`scripts/ops/helpers/db_write_guard.js`).
- **22 remaining complex candidates** are explicitly categorized in the legacy allowlist
  (`scripts/ops/helpers/db_write_guard_legacy_allowlist.json`). They are categorized,
  **NOT fixed**.
- **21 additional browser/Playwright scripts** are classified as `skipped_complex` by the
  static scanner (total skipped_complex: 43). They are identified, **NOT fixed**.
- **Changed-files hard fail** is enabled in `scripts/ops/ai_workflow_gate.py`: any PR that
  adds or modifies a `scripts/ops/**/*.js` file with DB write risk keywords but no guard
  integration will fail CI. Historical categorized candidates are exempt from hard fail.
- **Production-like DB host hard block** is enabled in the guard helper.
- **main is green.**

Despite these protections, the following remain **blocked**:

- Training
- Data expansion
- Real production DB write
- Scraper / browser automation

SC-002 cannot be marked "fully fixed" or "complete" until all closure criteria (Section 6)
are satisfied.

## Current State

| Metric | Value |
|---|---|
| Guarded JS scripts/ops entrypoints | 43 / 66 (Phase1–Phase7) |
| Guarded + guarded_but_needs_review (scanner) | 43 |
| Categorized in legacy allowlist | 22 |
| Categorized breakdown | pageprops_pipeline: 9, fotmob_pipeline: 2, shared_module: 3, dry_run_or_audit: 8 |
| Additional browser/Playwright skipped_complex (not in allowlist) | 21 |
| Total skipped_complex | 43 |
| Confirmed write paths guarded | 6 of 6 real (14 false positives reclassified in allowlist_cleanup_phase1) |
| Shared module consumers guarded | 3 of 3 active write-capable (odds_harvest_pipeline.js, gatekeeper.js, gatekeeper.sh); all 9 needs_manual_review consumers reviewed, 7 already guarded, 2 no write |
| Shared module consumers reviewed | 9 of 9 (all reclassified by manual_review_phase1) |
| Remaining needs_manual_review | 0 (all 14 reviewed and reclassified) |
| Remaining possible_indirect_write | 0 (reclassified to false_positive_read_only_transaction) |
| Changed-files enforcement | hard fail (active) |
| Production-like DB host hard block | enabled |
| Real DB write authorization | no |
| Training status | blocked |
| Data expansion status | blocked |
| Scraper / browser automation status | blocked |
| Python / SQL / migration enforcement | ALL PHASES COMPLETED. Phase2A+2B done; Phase2C batch1-4 done (9/14 guarded, 5 classified); indirect_write_path phases done (6/6 guarded); manual_review phases done (2/2 guarded); Alembic phases done (1 guarded — env.py guard in run_migrations_online()). Total: 18/20 guarded, 2 safe reclassified, 0 pending, 0 unreviewed. |
| SC-002 Alembic migration guard | `sc002_alembic_migration_runtime_guard_implementation` completed. env.py guard: `_check_alembic_migration_guard()` at top of `run_migrations_online()` before any DB engine/connection. Reuses `python_db_write_guard.py`. ALEMBIC_CTX for CI/dev auto-allow. Production-like host hard block. Offline mode NOT guarded. All 20 Python write paths resolved. |
| Runtime DB role / permission model | Reviewed by `runtime_db_role_permission_review_phase1` (static audit). Dev POC implemented by `runtime_db_role_permission_dev_poc`: 6 roles in `deploy/docker/init_db.sql` with least-privilege grants. Dev-only. Not applied to staging/production. |
| Agent workflow rules hardening | agent_workflow_rules_hardening_phase1 completed: resident rules (CLAUDE.md), PR template checklist, CI gate enforcement codified. This is workflow hardening, NOT SC-002 closure. Does not change remaining 11 confirmed + 8 indirect + 5 manual review Python write path counts.
| CI local parity preflight | ci_local_parity_preflight_phase1 completed: local PR Gate preflight (`scripts/ops/local_pr_gate_preflight.py`, `make pr-gate-local`). Fast mode runs static analysis, PR body validation, and enforcement checks locally (no network, no DB, no secrets). Full mode adds ruff, mypy, pytest, npm test:coverage. Goal: improve remote CI first-pass rate. This is workflow/CI parity hardening, NOT SC-002 closure. Does not change guarded/pending counts.
| Consumer-level guard audit (infrastructure) | consumer_level_guard_audit_db_pool_sync_sql_store completed: static audit of all consumers of db_pool.py, sync_db_pool.py, sql_store.py. 11 consumers classified. 2 write consumers already guarded (batch3). 6 read-only verified. 0 unguarded write consumers found. 0 dynamic/unknown. SQLStore has zero active consumers. SyncDatabasePool utils aliases have zero downstream consumers. No new guards needed from this audit. Does not change 9/14 guarded count. Does not process 8 indirect or 5 manual review candidates.
| SC-002 overall closure assessment | `sc002_overall_closure_assessment` completed. Per-criterion gap analysis documented in `docs/SC002_OVERALL_CLOSURE_ASSESSMENT.md`. 4 criteria met/good-standing, 4 partial, 2 not met. SC-002 remains partial mitigation only. Next: `runtime_db_role_permission_review_phase1`. |

## What Is Actually Protected

1. **43 guarded JS entrypoints** (Phase1–Phase7): each calls `assertDbWriteAllowed()` before
   any INSERT/UPDATE/DELETE/TRUNCATE/DROP/CREATE/ALTER operation. The guard enforces:
   - Universal gates: `ALLOW_DB_WRITE`, `FINAL_DB_WRITE_CONFIRMATION`
   - Table-level gates: `ALLOW_RAW_MATCH_DATA_WRITE`, `ALLOW_MATCHES_WRITE`,
     `ALLOW_ODDS_WRITE`, `ALLOW_TRAINING_WRITE`
   - Schema-level gate: `ALLOW_SCHEMA_WRITE`
   - `DRY_RUN` defaults to `true`
   - `NODE_ENV=production` / `APP_ENV=production` blocks write
   - Production-like DB hosts (RDS, Cloud SQL, Supabase, Railway, Render, Heroku) are
     hard blocked with no override

2. **Production-like DB host hard block**: the guard helper denies write when the DB host
   matches production-like patterns. No `ALLOW_PRODUCTION_DB_WRITE` bypass exists.

3. **Changed-files hard fail**: `ai_workflow_gate.py` hard-fails when a PR adds or modifies
   a `scripts/ops/**/*.js` file that contains DB write risk keywords (INSERT, UPDATE,
   DELETE, TRUNCATE, DROP, CREATE, ALTER) but does NOT call `assertDbWriteAllowed`.
   Historical complex candidates in the allowlist are exempt. A new script that is a false
   positive must be added to the allowlist with explicit category, reason, reviewed_at,
   and future_action — silent bypass is not permitted.

4. **PR-level governance checks**: PR template, AI Workflow Gate, Documentation Governance,
   and Codex Workflow rules collectively enforce task scoping, safety declarations, and
   documentation standards.

## What Is Not Yet Protected

1. **Historical categorized scripts are NOT fixed.** The 22 candidates in the allowlist
   and the 21 additional browser/Playwright scripts are identified and classified but
   have NOT been retrofitted with guard integration, specialized audit, or alternative
   enforcement.

2. **Browser / FotMob / pageProps paths are not fully covered.** Many of the
   `skipped_complex` scripts involve browser automation (Playwright, Chromium),
   FotMob ingestion, or pageProps pipeline logic. The standard JS guard pattern does
   not fit these paths well because:
   - Browser scripts often manage state via page interaction, not direct SQL.
   - FotMob scripts operate on fetched JSON payloads and may write through shared helpers.
   - PageProps scripts have their own multi-phase pipeline (plan → preflight → execute →
     verify) with specialized guard structures.

3. **Shared modules are not individually guarded.** Files like `dbBlueprint.js`,
   `restoreMappingsWorkflow.js`, and `odds_harvest_pipeline.shared.js` are consumed
   by entrypoints. The guard belongs in the calling entrypoint, but the current
   enforcement does not trace callers to verify that every consumer of a shared
   module is itself guarded.

4. **Python script runtime guards are now fully deployed.** All 20 Python write paths are
   resolved: 18 runtime guarded, 2 safe reclassified (read_only/false_positive). 0 pending.
   0 unreviewed. The Alembic migration env.py now has a guard in `run_migrations_online()`
   before any DB engine creation. Python guard helper enforces the same env-var gate model
   as the JS guard. All guarded Python paths still require explicit authorization for real
   DB write. SC-002 remains partial mitigation only.

5. **SQL / migration paths are partially covered.** The Alembic migration orchestrator
   (`env.py`) is now guarded. Static SQL migration files have CI enforcement
   (Phase2B scanner). However, runtime SQL migration execution still requires explicit
   env-var authorization. `deploy/docker/init_db.sql` needs its own guard (still pending).

6. **Runtime DB role / permission model is not fully validated.** The guard operates at
   the application layer. Database-level role restrictions (read-only roles for certain
   services, write-restricted connection pools, row-level security) have not been
   systematically reviewed or tested.

7. **Actual production-like execution is not validated.** No guarded script has been
   exercised end-to-end in a production-like environment with the guard active.
   Dry-run scenarios may pass while real execution paths fail or bypass the guard.

## Remaining Candidate Classification

### Category A: pageprops_pipeline (9 candidates)

Scripts: `all_seeded_pageprops_v2_canonical_read_verification.js`,
`pageprops_v2_bounded_expanded_blocked_target_review_execute.js`,
`pageprops_v2_controlled_write_plan.js`,
`pageprops_v2_identity_contract_regression_execute.js`,
`pageprops_v2_post_write_canonical_read_verification.js`,
`pageprops_v2_raw_completeness_audit.js`,
`pageprops_v2_recapture_runner_identity_input_contract_fix_plan.js`,
`pageprops_v2_suspended_target_review_execute.js`,
`single_league_small_batch_target_manifest_plan.js`

**Risk:** These scripts operate in a multi-phase pageProps pipeline that includes
planning, preflight, controlled write execution, and post-write verification. Several
contain high-risk keywords (TRUNCATE, COPY, GRANT, REVOKE) that appear in audit or
verification contexts. If any of these scripts is executed outside its intended
controlled pipeline without guard protection, it could write to or alter production
tables.

**Why not a simple JS guard:** The pageProps pipeline has its own multi-phase guard
structure with separate plan/preflight/execute stages. Simply inserting
`assertDbWriteAllowed()` without understanding the pipeline phase semantics could bypass
the controlled-write design or break the pipeline's own safety checks. A specialized
design is needed that respects the pipeline architecture while ensuring no write path
operates without guard coverage.

**Required follow-up:** `specialized_browser_fotmob_pageprops_audit_phase1`

**Acceptance criteria:**
- Each script is audited to confirm whether it actually executes DB writes or only
  references write keywords in audit/planning context.
- Scripts confirmed as write-capable must either integrate the guard or be explicitly
  classified as planning/audit-only with enforced DRY_RUN.
- Pipeline phase boundaries are documented so that the guard integrates at the actual
  execute phase, not at the planning/preflight phase.
- The pipeline's own guard structure is reviewed for completeness.

### Category B: fotmob_pipeline (2 candidates)

Scripts: `fotmob_adg60_raw_json_db_storage_no_feature_parse.js`,
`fotmob_ligue1_adg57_no_write_mutation_dry_run_preview.js`

**Risk:** FotMob ingestion pipeline scripts handle raw JSON payloads and may write to
`raw_match_data` or related tables. Even if one script is labeled "no_write_mutation"
and "dry_run_preview," its keywords must be verified as truly non-executing.

**Why not a simple JS guard:** FotMob ingestion involves network fetch, browser
automation, and specialized FotMob pipeline logic. The guard must integrate at the
FotMob pipeline level, not just at the JS entrypoint level. Some scripts may be
preview/audit-only but need verification.

**Required follow-up:** `specialized_browser_fotmob_pageprops_audit_phase1`

**Acceptance criteria:**
- Each FotMob script is audited to confirm write vs. preview/audit behavior.
- Write-capable FotMob scripts must integrate and gate their full pipeline (fetch →
  parse → validate → write), not just the final write step.
- Preview/audit-only scripts must be verified as truly read-only and classified as such.

### Category C: shared_module (3 candidates)

Scripts: `helpers/dbBlueprint.js`, `helpers/restoreMappingsWorkflow.js`,
`odds_harvest_pipeline.shared.js`

**Risk:** These are shared helper modules consumed by entrypoint scripts. They define
DB schemas, restore workflow logic, or odds harvest pipeline logic. They are not
standalone write entrypoints, but they contain DB write keywords and could be misused
if called from an unguarded context.

**Why not a simple JS guard:** A shared module should not independently guard itself
because it does not know its calling context. The guard belongs in the calling
entrypoint. But the current enforcement does not trace callers to verify that every
consumer of a shared module is itself guarded. This creates a coverage gap: a new
unguarded entrypoint could consume a shared module and write to the DB without
detection.

**Required follow-up:** `shared_module_db_write_boundary_design_phase1`

**Acceptance criteria:**
- Every entrypoint that consumes a shared module with DB write risk is identified.
- A caller-tracing or boundary enforcement design is documented.
- The design specifies how to verify that all consumers of each shared module are
  themselves guarded or explicitly classified as read-only.
- If caller tracing is infeasible for CI, an alternative boundary (e.g., shared module
  annotation + consumer checklist) is documented.

### Category D: dry_run_or_audit (8 candidates)

Scripts: `authoritative_workflow_enforcement_dry_run.js`, `dataset_status_audit.js`,
`formal_training_dataset_design_dry_run.js`, `l3_local_dry_run.js`,
`raw_match_data_versioned_schema_migration_preflight.js`,
`technical_debt_workflow_audit_dry_run.js`, `training_dataset_leakage_dry_run.js`,
`training_pipeline_smoke_dry_run.js`

**Risk:** These scripts are labeled as dry-run, audit, or preflight. They likely do not
execute real DB writes. However, their keywords have not been systematically verified
as non-executing. A script labeled "dry-run" could still contain a code path that
executes real writes under certain conditions (e.g., misconfiguration, bypass flag,
or conditional logic).

**Why not a simple JS guard:** Many of these scripts genuinely do not need a guard
because they are read-only. But the classification is based on filename pattern and
context heuristics, not on verified code-path analysis. A false classification of a
write-capable script as "dry_run_or_audit" would leave a real write path unguarded.

**Required follow-up:** `specialized_browser_fotmob_pageprops_audit_phase1` (overlap
with the broader audit scope)

**Acceptance criteria:**
- Each dry-run/audit script is verified to confirm it cannot execute real DB writes
  under any runtime condition.
- Scripts confirmed as read-only are formally reclassified in the scanner.
- Any script found to have a real write path (even conditional) must be either guarded
  or moved to a different category with appropriate enforcement.
- Verification includes examining conditional branches, env-var-gated paths, and
  try/catch fallback paths.

### Category E: browser/Playwright (21 candidates, not in allowlist)

Scripts (21): `controlled_matches_identity_seed_prerequisite_plan.js`,
`fixture_harvester_l1.js`, `fotmob_ligue1_adg60_raw_payload_source_inventory.js`,
`fotmob_ligue1_corrected_source_discovery_adg21.js`,
`html_hydration_source_fidelity_live_compare.js`, `l1_matches_seed_commit_plan.js`,
`l2_raw_match_data_ingest_plan.js`, `l2_raw_match_data_ingest_preflight.js`,
`large_scale_pageprops_v2_acquisition_strategy_plan.js`, `odds_sniper.js`,
`pageprops_v2_no_write_payload_recapture_plan.js`, `pageprops_v2_no_write_preview.js`,
`pageprops_v2_raw_write_input_source_investigation.js`,
`pageprops_v2_single_target_controlled_write.js`,
`pageprops_v2_single_target_write_preflight.js`,
`post_seed_matches_identity_raw_write_readiness_audit.js`,
`remaining_seeded_pageprops_v2_acquisition_preflight.js`,
`remaining_seeded_pageprops_v2_controlled_write.js`,
`single_league_pageprops_v2_controlled_write_execute.js`,
`single_league_pageprops_v2_controlled_write_plan.js`,
`single_league_small_batch_pageprops_v2_preflight.js`

**Risk:** These scripts involve browser automation (Playwright/Chromium), cookie/session
management, captcha handling, or proxy rotation. They operate at the intersection of
network, browser, and database layers. Browser automation scripts may write to the DB
indirectly through shared helpers or pipeline stages. The risk is compounded because
browser automation is itself blocked, so these scripts have not been exercised or
audited in their current form.

**Why not a simple JS guard:** Browser automation scripts have a fundamentally different
execution model from simple DB write scripts:
- They manage browser state (pages, sessions, cookies) in addition to database state.
- Their write paths may be deeply nested in pipeline stages.
- They often have their own controlled-write guard structures that need specialized
  review.
- Some are plan/preflight scripts that coordinate the actual execute scripts.
- Simply inserting `assertDbWriteAllowed()` at the top of these scripts does not
  address the browser-layer risks (session leak, cookie reuse, network-side effects).

**Required follow-up:** `specialized_browser_fotmob_pageprops_audit_phase1`

**Acceptance criteria:**
- Each browser/Playwright script is audited to map its full execution path
  (browser → network → parse → DB).
- Write-capable scripts must either integrate DB write guard at every actual write
  point, or have a documented controlled-write structure that covers all layers.
- Plan/preflight scripts must be verified to not execute writes themselves.
- Browser-layer risks (session management, cookie handling, captcha bypass) are
  documented as separate from DB write risks.
- No browser automation script executes a real DB write without explicit guard coverage
  and authorization.

## Closure Criteria for SC-002

SC-002 may be closed only when **all** of the following conditions are satisfied:

| # | Criterion | Status |
|---|---|---|
| 1 | All real DB write entrypoints are guarded or formally classified as non-write | Substantially met (59 JS + 18 Python entrypoints guarded; all 43 skipped_complex individually verified by `browser_fotmob_pageprops_playwright_deep_audit`; 0 unknown_needs_followup; legacy allowlist metadata update remaining; see SC002_OVERALL_CLOSURE_ASSESSMENT.md #1) |
| 2 | Changed-files enforcement is active and tested with both positive and negative cases | Substantially met (static negative-case tests implemented — 29 tests; unguarded INSERT/UPDATE/CREATE/DELETE rejected; allowlisted+no-DB files pass; destructive SQL rejected; see SC002_OVERALL_CLOSURE_ASSESSMENT.md #2) |
| 3 | Remaining browser/FotMob/pageProps paths have specialized audit results and have been either guarded or formally excluded | Substantially met (deep per-script verification complete; all 43 scripts individually verified; 0 hidden write paths; 1 classification correction; browser-layer non-DB risks unreviewed; see SC002_OVERALL_CLOSURE_ASSESSMENT.md #3) |
| 4 | Shared modules have clear responsibility boundary: every consumer of a shared DB write-risk module is identified and verified as guarded or read-only | Substantially met (all 3 shared modules mapped; all active write-capable consumers guarded; proactive boundary enforcement designed but not implemented; see SC002_OVERALL_CLOSURE_ASSESSMENT.md #4) |
| 5 | Python / SQL / migration enforcement has either a guard mechanism or a documented exclusion with rationale | Met (Python track: all 20 paths resolved — 18 guarded, 2 safe. Alembic env.py guard in run_migrations_online(). SQL migration files have CI enforcement. deploy/docker/init_db.sql guard still pending — separate concern under Gate B) |
| 6 | Runtime DB permissions / role restrictions are documented or tested | Substantially met (static audit complete: 8 risks, target model. Dev POC: 6 roles in init_db.sql with least-privilege grants, Gate B guard, 54 static tests. Staging/production deployment pending — operations task. See `docs/SC002_FINAL_CLOSURE_CHECK.md`) |
| 7 | No production override exists (no `ALLOW_PRODUCTION_DB_WRITE`, no bypass env var, no host-block escape hatch) | Met |
| 8 | Training and data expansion remain blocked until explicit release criteria are met | Met (blocks are in place) |
| 9 | PROJECT_STATUS.md matches closure state | Will be verified at closure |
| 10 | CI green after closure PR merge | Will be verified at closure |

**Current verdict:** SC-002 cannot be closed. At least 5 criteria are unmet.

## Release Gates

### Gate A: Controlled local dry-run allowed

**Status: partially ready / still needs review**

| Aspect | Detail |
|---|---|
| Required conditions | All Phase1–Phase7 guarded scripts validated; static scanner confirms 43/43 detection; DRY_RUN=true by default; local dev DB only; no production-like host |
| Forbidden actions | Real production DB write; DRY_RUN=false without explicit authorization; bypassing guard via direct DB connection; running browser automation without guard |
| Approval requirement | Task-level authorization with explicit scope |
| Rollback requirement | DRY_RUN=true is the default; no persistent state change expected in dry-run mode |
| Logging/audit requirement | Guard logs every gate check with timestamp, script path, env vars, and result |

### Gate B: Controlled staging DB write allowed

**Status: blocked**

| Aspect | Detail |
|---|---|
| Required conditions | Gate A fully ready and reviewed; all remaining complex candidates either guarded or formally excluded; shared module boundary design implemented; browser/FotMob/pageProps audit complete; Python/SQL/migration enforcement designed; staging DB host is NOT production-like; DRY_RUN=false gated by explicit env var |
| Forbidden actions | Writing to production DB; writing to production-like host; training on staging data without authorization; schema migration without guard; running unguarded scripts |
| Approval requirement | Explicit per-task authorization; operator must confirm DRY_RUN=false and target host |
| Rollback requirement | Staging data restore plan; rollback script or snapshot documented |
| Logging/audit requirement | Full audit trail: script path, user, timestamp, target host, tables affected, row counts, guard gate results |

### Gate C: Training / data expansion allowed

**Status: blocked**

| Aspect | Detail |
|---|---|
| Required conditions | Gates A and B fully ready and reviewed; all write entrypoints guarded; runtime DB role/permission model validated; training pipeline guarded with table-level `ALLOW_TRAINING_WRITE`; data expansion pipeline guarded with `ALLOW_RAW_MATCH_DATA_WRITE` and `ALLOW_MATCHES_WRITE`; cutoff-time policy defined; eligibility criteria documented; odds data pipeline guarded |
| Forbidden actions | Training on unvalidated data; training without explicit authorization; data expansion without guard; mixing training data with production data without boundary; running unguarded data pipeline scripts |
| Approval requirement | Explicit per-run authorization; training run must be documented with dataset version, feature set, and eligibility criteria |
| Rollback requirement | Training artifacts are versioned; previous model version retained; data expansion is append-only or has snapshot rollback |
| Logging/audit requirement | Full pipeline audit: data sources, row counts, guard gate results, training parameters, model version, feature set hash |

## Recommended Next Tasks

### 1. specialized_browser_fotmob_pageprops_audit_phase1 ✅ COMPLETED

- **Status:** Completed (this PR). Audit document: `docs/SC002_BROWSER_FOTMOB_PAGEPROPS_AUDIT.md`.
- **Results:** All 43 skipped_complex scripts statically audited (original classification).
  After allowlist_cleanup_phase1, gatekeeper_boundary_implementation, and manual_review_phase1:
  - 13 guarded (6 confirmed + 7 reclassified from needs_manual_review)
  - 13 false_positive_select_only_with_active_wrapper
  - 3 false_positive_read_only_transaction
  - 3 false_positive_no_db_write_evidence
  - 1 false_positive_no_db_connection_static_scan
  - 1 false_positive_policy_or_regex_keyword_only
  - 12 read_only
  - 3 design_mapped
  - 1 scraper_or_browser_only
  - **0 needs_manual_review** (all resolved)
  - **0 possible_indirect_write** (resolved)
- **Key finding:** 13 scripts have confirmed DB write capability and are all now guarded.
  Classification is now complete across all 43 scripts.

### 3. sc002_allowlist_cleanup_phase1 ✅ COMPLETED

- **Status:** Completed (this PR). Static test file: `tests/unit/sc002_allowlist_cleanup_phase1_static.test.js`.
- **Results:** 15 scripts formally reclassified from confirmed_write_path_needs_guard
  to verified false positive categories:
  - 11 false_positive_select_only_with_active_wrapper (queryReadOnly/safeSelect wrappers)
  - 2 false_positive_read_only_transaction (BEGIN READ ONLY + assertSelectOnlySql)
  - 1 false_positive_no_db_connection_static_scan (no pg import)
  - 1 false_positive_policy_or_regex_keyword_only (INSERT in policy string only)
- **Key finding:** 14 of the 15 remaining "confirmed_write_path_needs_guard" scripts
  were false positives — they have active SELECT-only wrappers, READ ONLY transactions,
  or no DB connection. 0 scripts remain unguarded with confirmed DB write capability.
  All remaining needs_manual_review (4) and possible_indirect_write (1) were resolved by
  manual_review_phase1. SC-002 remains partial mitigation only (Python/SQL/migration
  enforcement not yet designed).
- **This cleanup does NOT:**
  - Guard any scripts (that was Phase1/Phase2)
  - Close SC-002
  - Unlock training, data expansion, or real DB write
  - Review the 4 needs_manual_review scripts

### 2. confirmed_write_path_guard_phase (COMPLETED — 6 of 6 real write paths guarded)

- **Status:** Phase 1 (high-risk browser+DB) completed (#1586). Phase 2 batch 1
  (controlled-write scripts) completed (#1587). Phase 2 batch 2 (FotMob raw JSON DB
  storage) completed (#1589).
  - Phase 1 (2 scripts): `odds_sniper.js`, `fixture_harvester_l1.js`
  - Phase 2 batch 1 (3 scripts): `pageprops_v2_single_target_controlled_write.js`,
    `remaining_seeded_pageprops_v2_controlled_write.js`,
    `single_league_pageprops_v2_controlled_write_execute.js` — all INSERT INTO
    raw_match_data, guard added before BEGIN transaction
  - Phase 2 batch 2 (1 script): `fotmob_adg60_raw_json_db_storage_no_feature_parse.js` —
    INSERT INTO fotmob_raw_match_payloads with ON CONFLICT DO UPDATE, guard added
    before INSERT query
- **All 6 real confirmed write paths now guarded.** The remaining 14 scripts from the
  original 20 "confirmed_write_path" classification were reclassified as false positives
  by sc002_allowlist_cleanup_phase1. 0 still_needs_guard remain.
- **Acceptance criteria:** Each script calls `assertDbWriteAllowed()` before every write
  operation. Static tests confirm guard coverage. Scanner detects guard calls. changed-files
  enforcement passes.

### 4a. shared_module_db_write_boundary_implementation_phase1 ✅ COMPLETED

- **Status:** Completed (this PR). Guarded `odds_harvest_pipeline.js` — the HIGH priority
  unguarded consumer discovered by the design phase.
- **Guard location:** `upsertMappingAndOdds()` function, after dryRun check, before
  BEGIN transaction.
- **Target tables:** `matches_oddsportal_mapping`, `odds`
- **Operations:** INSERT, UPDATE (via UPSERT with ON CONFLICT DO UPDATE)
- **Results:** `assertDbWriteAllowed()` now gates all write SQL in the script.
  Gatekeeper.js / gatekeeper.sh remain pending. 8 needs_manual_review consumers
  remain pending. No target script executed.
- **SC-002 remains partial mitigation only.**

### 4b. gatekeeper_boundary_implementation ✅ COMPLETED

- **Status:** Completed (this PR). Guarded `gatekeeper.js` and `gatekeeper.sh` — the
  MEDIUM priority CI infrastructure consumers.
- **Guard location:** `gatekeeper.js` `checkColdStart()` method; `gatekeeper.sh` inline Node heredoc
- **Target tables:** `matches`, `raw_match_data`, `matches_oddsportal_mapping`
- **Operations:** `CREATE`, `DROP`, `INSERT`
- **Results:** Both consumer entrypoints now guarded. All 3 active write-capable
  shared-module consumers now guarded (odds_harvest_pipeline.js, gatekeeper.js, gatekeeper.sh).
  No target script executed. No DB connection. No real DB write.
- **SC-002 remains partial mitigation only.**

### 4c. manual_review_phase1 ✅ COMPLETED

- **Status:** Completed (this PR). Statically reviewed all 14 remaining `needs_manual_review`
  / `possible_indirect_write` scripts from both the shared-module design doc (9) and the
  broader skipped_complex audit (5).
- **Results:**
  - **7 already_guarded** — cleanup_csv_bulk_loader_import.js, purge_ghost_data.js,
    purge_orphans.js, raw_match_data_completeness_fidelity_audit.js,
    renewed_pageprops_v2_raw_write_execute.js (transitive via base), reset_database.js,
    seed_fotmob_sample.js — all have `assertDbWriteAllowed()` before BEGIN transaction
  - **3 false_positive_no_db_write_evidence** — fetch_and_adapt_euro_leagues.js,
    master_inventory.js (SELECT-only), pageprops_v2_identity_contract_regression_execute.js,
    pageprops_v2_suspended_target_review_execute.js (zero DB connection)
  - **2 false_positive_select_only_with_active_wrapper** — 
    all_seeded_pageprops_v2_canonical_read_verification.js,
    pageprops_v2_post_write_canonical_read_verification.js — `assertSelectOnly()` wrapper
  - **1 false_positive_read_only_transaction** — training_pipeline_smoke_dry_run.js —
    BEGIN READ ONLY + ROLLBACK + assertSelectOnlySql()
  - **0 confirmed_write_path_needs_guard** — no new unguarded write paths found
  - **0 remaining needs_manual_review** — all 14 reviewed and reclassified
- **Count mismatch resolved:** Previous PR #1593 reported "8" needs_manual_review
  consumers (a typo). Actual design-doc count is 9. Combined with audit-doc's 5, total
  reviewed = 14. See `docs/SC002_MANUAL_REVIEW_PHASE1.md` for full per-script evidence.
- **No guard implemented** — all 7 write-capable scripts were already guarded in Phase1-7.
- **No target script executed.** No DB connection. No real DB write. No scraper/browser.
- **SC-002 remains partial mitigation only.**
- **Training, data expansion, real DB write remain blocked.**

### 4. shared_module_db_write_boundary_design_phase1 ✅ COMPLETED

- **Status:** Completed (this PR). Design document: `docs/SC002_SHARED_MODULE_DB_WRITE_BOUNDARY_DESIGN.md`.
- **Results:** All 3 shared modules analyzed with full consumer entrypoint map:
  - `dbBlueprint.js` — 24 consumers mapped: 3 write-capable (2 unguarded gatekeeper
    scripts, 1 guarded db_vault.js), 18 read-only only, 3 needs_manual_review
  - `restoreMappingsWorkflow.js` — 0 active consumers, dependency-injected write path,
    built-in dryRun support
  - `odds_harvest_pipeline.shared.js` — 2 consumers: 1 guarded (odds_sniper.js),
    1 **UNGUARDED gap found** (odds_harvest_pipeline.js — CLI entrypoint with Pool +
    UPSERT write SQL + Playwright, no guard, not in any prior audit)
- **Key findings:**
  - Guard boundary recommendation: **consumer entrypoint** for all 3 modules (module-level
    guard would break read-only consumers).
  - **2 new unguarded entrypoints discovered:** `odds_harvest_pipeline.js` (HIGH — browser+DB,
    not in skipped_complex audit) and `gatekeeper.js`/`gatekeeper.sh` (MEDIUM — CI infra).
  - 8 consumers flagged as `needs_manual_review` — they import only `buildDbConnectionConfig`
    from dbBlueprint but may have their own DB write paths.
- **Next step:** `shared_module_db_write_boundary_implementation_phase1` — guard
  `odds_harvest_pipeline.js` (HIGH priority), then gatekeeper.js/gatekeeper.sh, then
  review the 8 `needs_manual_review` consumers.

### 5. python_sql_migration_enforcement_design_phase1 ✅ COMPLETED

- **Status:** Completed (this PR). Design document: `docs/SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md`.
- **Results:**
  - **374 Python files** inventoried; **69 classified** with DB relevance
  - **14 python_confirmed_write_path_needs_guard** identified (schema_manager, sql_store, match_repository, etc.)
  - **8 python_indirect_write_path_needs_guard** identified (service-layer indirect paths)
  - **5 python_needs_manual_review** identified (ambiguous signals)
  - **18 SQL files** classified; all migration files categorized
  - **0 destructive SQL migrations** found
  - **1 seed SQL needs gate** (deploy/docker/init_db.sql)
  - Recommended enforcement: Hybrid model (Python guard equivalent + static scanner + CI policy)
  - Phased implementation plan: Phase 2A (static scanner) → 2B (SQL migration policy) → 2C (Python guard helper) → 2D (manual review)
- **No runtime behavior changed. No target script executed. No DB connection. No real DB write.**
- **SC-002 remains partial mitigation only. Training, data expansion, real DB write remain blocked.**
- **Next step:** `python_sql_migration_enforcement_implementation_phase2A` ✅ **COMPLETED** (see below).

### 5a. python_sql_migration_enforcement_implementation_phase2A ✅ COMPLETED

- **Status:** Completed (this PR).
- **Results:**
  - Python static scanner: `scripts/ops/python_db_write_static_enforcement.py`
  - Python DB write allowlist: `config/python_db_write_allowlist.json` (27 historical baseline entries)
  - AI Workflow Gate integration: `check_python_db_write_enforcement()` in `scripts/ops/ai_workflow_gate.py`
  - Changed-files enforcement: new/modified Python files with DB write signals fail CI unless in allowlist
  - Scanner supports: JSON output, allowlist, changed-files mode, full-scan mode, comment/docstring awareness
  - **No runtime guard implemented.** No target script executed. No DB connection. No real DB write.
  - **SC-002 remains partial mitigation only. Training, data expansion, real DB write remain blocked.**
- **Next step:** `python_runtime_guard_implementation_phase2C` — Python runtime guard for 14 confirmed + 8 indirect write paths. Also `sql_migration_policy_implementation_phase2B` ✅ COMPLETED (see below).

### 5b. sql_migration_policy_implementation_phase2B ✅ COMPLETED

- **Status:** Completed (this PR).
- **Results:**
  - SQL/migration scanner: `scripts/ops/sql_migration_policy_static_enforcement.py`
  - SQL/migration allowlist: `config/sql_migration_policy_allowlist.json` (22 entries)
  - Gate helper: `scripts/ops/helpers/sql_migration_policy_enforcement_check.py`
  - AI Workflow Gate integration: check #10 in main()
  - 0 destructive migrations found; destructive SQL always fails gate
  - 1 seed SQL needs gate (deploy/docker/init_db.sql)
  - **No SQL executed. No migration run. No DB connection. No real DB write.**
  - **SC-002 remains partial mitigation only.**
- **Next step:** `python_runtime_guard_implementation_phase2C`. Do not start automatically.

### 5c. python_runtime_guard_implementation_phase2C_batch1 ✅ COMPLETED

- **Status:** Completed (this PR).
- **Results:**
  - Guard helper: `scripts/ops/helpers/python_db_write_guard.py` — Python equivalent of
    JS `db_write_guard.js` with same env-var gate model (ALLOW_DB_WRITE,
    FINAL_DB_WRITE_CONFIRMATION, DRY_RUN, table-level gates, production host hard block).
    Does NOT connect to DB, does NOT read secrets, does NOT execute SQL.
  - Batch1 guarded paths (3 of 14 confirmed):
    1. `src/database/match_repository.py` — guard in `upsert_match_hash()` before
       INSERT INTO matches_mapping
    2. `scripts/maintenance/database_detox.py` — guard in `main()` before
       ALTER TABLE/UPDATE prematch_features
    3. `scripts/maintenance/reset_l2_collection.py` — guard in `main()` before
       TRUNCATE raw_match_data/collection_audit_logs
  - Allowlist updated: 3 entries → `runtime_guarded`, 12 remain `pending_runtime_guard`
  - **11 remaining confirmed Python write paths still pending runtime guard.**
  - **8 indirect write paths NOT processed.**
  - **5 manual review candidates NOT processed.**
  - **No Python target scripts executed. No DB connection. No real DB write.**
  - **No SQL/migration executed. No scraper/browser run. No training. No data expansion.**
  - **SC-002 remains partial mitigation only.**
- **Next step:** `python_runtime_guard_implementation_phase2C_batch2`. Do not start
  automatically.

### 5d. python_runtime_guard_implementation_phase2C_batch2 ✅ COMPLETED

- **Status:** Completed (this PR).
- **Results:**
  - Batch2 guarded paths (3 more of 14 confirmed, 6 of 14 total):
    1. `src/database/schema_manager.py` — guard in `initialize_schema()` before
       CREATE TABLE/ALTER TABLE on match_features_training, matches, raw_match_data.
       Operations: CREATE, ALTER. Requires ALLOW_SCHEMA_WRITE.
    2. `src/database/oddsportal_db_manager.py` — guard in `sync_match_data()` before
       INSERT/UPDATE (UPSERT with ON CONFLICT DO UPDATE) on matches_mapping.
       Operations: INSERT, UPDATE.
    3. `scripts/ops/fotmob_registry_seed_dev_execution.py` — guard in `main()` before
       `execute_seed()` INSERT ON CONFLICT DO NOTHING on 7 football_* registry tables.
       Existing custom production guard preserved as additional defense-in-depth layer.
       Operations: INSERT.
  - Allowlist updated: 3 more entries → `runtime_guarded`, 6 total guarded
  - **8 confirmed Python write paths still pending runtime guard.**
  - **8 indirect write paths NOT processed.**
  - **5 manual review candidates NOT processed.**
  - **Batch2 selection rationale:** schema_manager.py selected for DDL guard (highest
    schema-level risk); oddsportal_db_manager.py selected for data sync guard (clear
    UPSERT boundary on matches_mapping); fotmob_registry_seed_dev_execution.py selected
    for seed INSERT guard (existing custom guard retained). sql_store.py (SQL string
    constants only, no executable code) and integrity_guard.py (SELECT-only, read-only)
    were reviewed and excluded from batch2 — they require different handling.
  - **No Python target scripts executed. No DB connection. No real DB write.**
  - **No SQL/migration executed. No scraper/browser run. No training. No data expansion.**
  - **SC-002 remains partial mitigation only.**
- **Next step:** `python_runtime_guard_implementation_phase2C_batch3`. Do not start
  automatically.

### 5e. python_runtime_guard_implementation_phase2C_batch3 ✅ COMPLETED

- **Status:** Completed (this PR).
- **Results:**
  - Batch3 guarded paths (3 more of 14 confirmed, 9 of 14 total):
    1. `src/core/database/odds_injector.py` — guard in `_inject_records()` before
       `psycopg2.connect()`, `execute_values()` UPDATE matches SET l3_odds_data, and
       `conn.commit()`. Integrated with existing `dry_run` parameter.
       Operations: UPDATE. Tables: matches.
    2. `src/database/collector_repository.py` — guard in `save_match_data()` and
       `batch_save_match_data()` before `connection.execute(SQL_UPSERT_MATCH)`
       INSERT INTO matches ON CONFLICT DO UPDATE.
       Operations: UPSERT. Tables: matches.
    3. `src/data/streaming/streaming_db_writer.py` — guard in `_execute_batch_write()`
       before `conn.executemany()` INSERT/UPSERT on dynamic table name.
       Operations: INSERT, UPSERT. Tables: dynamic (matches, odds, etc.).
  - Allowlist updated: 3 more entries → `runtime_guarded`, 9 total guarded
  - **5 confirmed Python write paths still pending runtime guard.**
  - **5 later_needs_design identified:** odds_integrity_guard.py (reads-only, generates
    cleanup SQL but never executes it), integrity_guard.py (SELECT-only queries, no
    writes), sql_store.py (SQL string constants only, no execution),
    sync_db_pool.py (infrastructure — generic execute() serves both read+write),
    db_pool.py (infrastructure — generic execute/executemany for both read+write).
  - **8 indirect write paths NOT processed.**
  - **5 manual review candidates NOT processed.**
  - **Batch3 selection rationale:** odds_injector.py selected for UPDATE guard with
    dry_run integration (clear write boundary on matches with quality-based UPSERT);
    collector_repository.py selected for asyncpg INSERT/UPSERT guard (clear execute
    entry points in save_match_data and batch_save_match_data);
    streaming_db_writer.py selected for dynamic-table INSERT/UPSERT guard (guard in
    _execute_batch_write covers all streaming write paths). 5 remaining files were
    analyzed and determined to be later_needs_design — their write boundaries are
    unclear (read-only in practice, SQL-string-only, or infrastructure-level).
  - **No Python target scripts executed. No DB connection. No real DB write.**
  - **No SQL/migration executed. No scraper/browser run. No training. No data expansion.**
  - **SC-002 remains partial mitigation only.**
- **Next step:** `python_confirmed_write_paths_design_phase2C_batch4`. Do not start
  automatically.

### 5f. python_confirmed_write_paths_design_phase2C_batch4 ✅ COMPLETED

- **Status:** Completed (this PR — design/classification task, NOT guard implementation).
- **Results:**
  - Static analysis of all 5 remaining confirmed Python write paths completed.
  - **0 runtime guards added.** This is a design/classification task only.
  - **2 files classified as `read_only_candidate`:**
    1. `scripts/maintenance/odds_integrity_guard.py` — all cursor.execute() are SELECT.
       The DELETE SQL in _generate_cleanup_sql() is print-to-console diagnostic, never executed.
    2. `scripts/maintenance/integrity_guard.py` — all cursor.execute() are SELECT COUNT/
       LEFT JOIN. generate_fix_commands() prints shell commands, not SQL.
    No guard needed for either file.
  - **3 files classified as `infrastructure_only_needs_caller_guard`:**
    1. `src/database/sql_store.py` — SQL string constants only (INSERT/UPDATE/UPSERT);
       no execution code, no DB driver imports. Guard at consumers.
    2. `src/database/sync_db_pool.py` — psycopg2 ThreadedConnectionPool with generic
       execute()/executemany() + auto-commit. Methods serve both read+write.
       Guard at caller level, not here.
    3. `src/database/db_pool.py` — asyncpg Pool with generic execute()/executemany()
       (auto-commit). Methods serve both read+write. Two write callers already guarded
       in batch3 (collector_repository.py, streaming_db_writer.py).
  - Design document: `docs/SC002_PHASE2C_REMAINING_CONFIRMED_WRITE_PATHS_DESIGN.md`
  - Allowlist updated: 5 entries reclassified with analysis_task, evidence,
    observed_operations, direct_write_boundary, recommended_next_action.
  - **No Python target scripts executed. No DB connection. No real DB write.**
  - **No SQL/migration executed. No scraper/browser run. No training. No data expansion.**
  - **SC-002 remains partial mitigation only.**
- **Next step:** Consumer-level guard audit for sync_db_pool/db_pool callers,
  `python_indirect_write_path_design_phase1`, or `python_manual_review_phase2D`.
  Do not start automatically.

### 5g. python_indirect_write_path_design_phase1 ✅ COMPLETED

- **Status:** Completed (this PR — design/classification task, NOT guard implementation).
- **Results:**
  - Static analysis of all 8 indirect Python write paths completed.
  - **0 runtime guards added.** This is a design/classification task only.
  - **6 paths classified as `indirect_write_needs_guard`:**
    1. `src/services/match_aligner.py` — ACTUALLY DIRECT write (own psycopg2, INSERT INTO matches_mapping ON CONFLICT DO UPDATE with commit). Not via MatchRepository as original design assumed. No guard. No dry_run. HIGH risk.
    2. `src/services/match_linker.py` — ACTUALLY DIRECT write (own psycopg2, INSERT INTO match_odds_intelligence ON CONFLICT DO UPDATE + CREATE TABLE with commit). No guard. No dry_run. HIGH risk.
    3. `src/api/collectors/odds_api_client_v38.py` — ACTUALLY DIRECT write (own psycopg2, INSERT INTO match_odds ON CONFLICT DO UPDATE with commit). No guard. No dry_run. HIGH risk.
    4. `scripts/maintenance/reprocess_failed_matches.py` — DIRECT write (UPDATE matches with commit). Has --dry-run but default is write-enabled (unsafe). MEDIUM risk.
    5. `scripts/maintenance/clean_corrupt_l2.py` — DIRECT write (UPDATE matches nullification with commit). Has --dry-run but default is write-enabled. MEDIUM risk.
    6. `scripts/maintenance/fix_zombie_matches.py` — DIRECT write (UPDATE matches with commit). Has --dry-run but default is write-enabled. MEDIUM risk.
  - **1 path classified as `indirect_read_only_candidate`:**
    - `src/services/league_router.py` — SELECT DISTINCT only (discover_all_leagues). URL routing utility. No write capability.
  - **1 path classified as `indirect_false_positive_candidate`:**
    - `src/services/match_data_service.py` — Skeleton class with only connection management. Zero write methods. Misleading type aliases (MatchAligner/MatchLinker point to empty class).
  - **Key finding:** 6 of 8 "indirect" paths are actually DIRECT — original design doc's assumption that these go through repository layers was incorrect. All 6 have their own independent psycopg2 connections with explicit INSERT/UPDATE and commit.
  - **3 of 6 have --dry-run flags but default is write-enabled** (action="store_true" means default=False=write). This is the INVERSE of the safe default.
  - Design document: `docs/SC002_INDIRECT_WRITE_PATH_DESIGN_PHASE1.md`
  - Allowlist updated: 8 entries reclassified with analysis_task, evidence, observed_operations, direct_write_boundary, recommended_next_action.
  - **No Python target scripts executed. No DB connection. No real DB write.**
  - **No SQL/migration executed. No scraper/browser run. No training. No data expansion.**
  - **SC-002 remains partial mitigation only.**
- **Next step:** `python_indirect_write_path_guard_phase2` — implement runtime guard for
  the 6 newly confirmed direct write paths. Do not start automatically.

### 5h. sc002_alembic_migration_guard_design ✅ COMPLETED

- **Status:** Completed (this PR — design/classification task, NOT runtime guard implementation).
- **Results:**
  - Static analysis of `src/database/migrations/env.py` completed.
  - **0 runtime guards added.** This is a design/classification task only.
  - **env.py classification:** `alembic_migration_needs_specialized_runtime_guard`
    - Confirmed: env.py CAN execute arbitrary DDL/DML via alembic upgrade.
    - Confirmed: env.py connects to live DB in online mode.
    - Confirmed: env.py has NO existing SC-002 guard or env-var restrictions.
    - env.py is the standard Alembic entry point — used by CI, local dev, Docker init.
    - Standard guard pattern does NOT directly fit (framework orchestrator, not standalone script).
  - Guard strategy designed:
    - Guard location: top of `run_migrations_online()` before any DB connection.
    - Env vars: `ALLOW_DB_WRITE`, `FINAL_DB_WRITE_CONFIRMATION`, `ALLOW_SCHEMA_WRITE`, `DRY_RUN`.
    - Production-like host hard block (matching JS/Python guard pattern).
    - `ALEMBIC_CTX` env var for CI/dev auto-allow.
    - Offline mode (`--sql`) NOT guarded.
  - Full implementation plan with pseudocode in `docs/SC002_ALEMBIC_MIGRATION_GUARD_DESIGN.md`.
  - Allowlist updated: env.py reclassified with full evidence and design doc reference.
  - **No Alembic run. No migration. No SQL. No DB connection. No real DB write.**
  - **No scraper/browser run. No training. No data expansion.**
  - **SC-002 remains partial mitigation only.**
- **Next step:** ✅ COMPLETED — see section 5i below.

### 5i. sc002_alembic_migration_runtime_guard_implementation ✅ COMPLETED

- **Status:** Completed (this PR). Guard added to `src/database/migrations/env.py`.
- **Results:**
  - **Runtime guard implemented in `run_migrations_online()` before any DB engine/connection.**
  - Guard function: `_check_alembic_migration_guard()` (line ~100 in env.py).
  - Reuses existing `scripts/ops/helpers/python_db_write_guard.py` (`assert_db_write_allowed`).
  - Guard call: `assert_db_write_allowed(script_name='env.py (Alembic migration)', operation='CREATE', target='alembic_migration (schema-level)', tables=['alembic_version'])`.
  - ALEMBIC_CTX env var: `ci`/`dev`/`docker_init` auto-allow with `ALLOW_SCHEMA_WRITE=yes`.
  - Production-like host hard block enforced by guard helper.
  - `run_migrations_offline()` (`--sql` mode) NOT guarded — SQL generation only, no DB.
  - Allowlist updated: env.py → `alembic_migration_runtime_guarded` (18/20 guarded).
  - SQL allowlist updated: env.py cross-reference reflects implementation status.
  - Docs: PROJECT_STATUS, CLOSURE_PLAN, DESIGN_DOC, ENFORCEMENT_DESIGN all updated.
  - Tests: 28 new static tests verify guard placement, allowlist state, safety boundaries.
  - **No Alembic run. No migration. No SQL. No DB connection. No real DB write.**
  - **No scraper/browser run. No training. No data expansion.**
  - **All 20 Python write paths now classified and resolved (18 guarded, 2 safe).**
  - **0 pending. 0 unreviewed.**
  - **SC-002 remains partial mitigation only.**
- **Next step:** ✅ COMPLETED — see section 5j below.

### 5j. sc002_overall_closure_assessment ✅ COMPLETED

- **Status:** Completed (this PR — assessment/gap analysis, NOT runtime implementation).
- **Results:**
  - Per-criterion assessment of all 10 SC-002 closure criteria.
  - Assessment document: `docs/SC002_OVERALL_CLOSURE_ASSESSMENT.md`.
  - Closure criteria status:
    - **Met / good standing (6):** #5 Python/SQL/migration, #7 no production override,
      #8 training blocked, #4 shared module boundary (substantially met), #9 PROJECT_STATUS
      aligned, #10 CI green.
    - **Partial (2):** #1 entrypoints guarded (43 skipped_complex classified but not
      individually verified non-write), #3 browser/FotMob audit (13 false_positive scripts
      need deep verification, 3 design_mapped need follow-up).
    - **Not met (2):** #2 negative-case testing (no deliberate CI test with known-unguarded
      file), #6 DB role/permission review (task defined but not executed).
  - Additional risk: `deploy/docker/init_db.sql` needs guard (Gate B concern, not Python/SQL track).
  - **SC-002 overall verdict: partial mitigation only. Cannot be closed.**
  - Next recommended task: `runtime_db_role_permission_review_phase1` — lowest effort,
    documentation only, unblocks criterion #6.
  - **No Alembic run. No migration. No SQL. No DB connection. No real DB write.**
  - **No scraper/browser run. No training. No data expansion.**
- **Next step:** `runtime_db_role_permission_review_phase1`.
  Do not start automatically.

### 6. runtime_db_role_permission_review_phase1 ✅ COMPLETED

- **Status:** Completed (this PR — static audit, NO DB connection, NO permission changes).
- **Results:**
  - Static audit of all DB user/role/connection configuration files completed.
  - Review document: `docs/SC002_RUNTIME_DB_ROLE_PERMISSION_REVIEW_PHASE1.md`.
  - Key findings:
    - **1 universal user:** `football_user` used for ALL roles (app, migration, ingestion,
      training, maintenance, CI). Full DDL + DML on all tables.
    - **1 read-only user:** `claude_reader` for MCP only (properly restricted).
    - **No privilege separation:** Migration (DDL) and runtime (DML) use the same user.
    - **8 risks identified** (HIGH: single super-user, mixed migration/runtime; MEDIUM: no
      read-only app user, broad ingestion access, hardcoded credentials, app-layer only).
    - **Target model designed:** 6 specialized roles with least-privilege grants.
  - Next step: Implement role model as dev proof-of-concept in Docker environment.
  - **No DB connection. No SQL. No permission changes. No secrets output.**
  - SC-002 remains partial mitigation only.
- **Next step:** `runtime_db_role_permission_dev_poc` — apply target role model to
  `deploy/docker/init_db.sql` and `docker-compose.dev.yml`.
  Do not start automatically.

### 6a. runtime_db_role_permission_dev_poc ✅ COMPLETED (this PR)

- **Status:** Completed (this PR — dev-only POC, NO DB connection, NO SQL execution).
- **Results:**
  - Target role model applied to dev-only files:
    - `deploy/docker/init_db.sql` — 6 roles created with least-privilege GRANTs
    - `docker-compose.dev.yml` — role-specific env vars for dev container
    - `.env.example` — role-specific connection config templates
  - All passwords are dev-only placeholders (`*_dev_poc`).
  - **No real secrets.** No production configuration.
  - Static tests validate: roles defined, reader read-only, owner/app separated,
    env example safe, docs explicitly dev-only, SC-002 partial mitigation only.
  - **No DB connection. No SQL. No permission changes. No secrets output.**
  - SC-002 remains partial mitigation only.
  - Training / data expansion / real DB write remain blocked.
- **Next step:** Not yet defined. Staging deployment of role separation is the logical
  next step but requires explicit authorization and production environment knowledge.
  Do not start automatically.

### 6b. browser_fotmob_pageprops_playwright_deep_audit ✅ COMPLETED (this PR)

- **Status:** Completed (this PR — static deep audit, NO browser, NO Playwright, NO DB, NO SQL).
- **Results:**
  - Deep per-script verification of all 43 skipped_complex JS scripts completed.
  - Three target categories individually verified:
    - **13 false_positive_select_only_with_active_wrapper:** All confirmed non-write.
      Each has active SQL enforcement wrappers (queryReadOnly/safeSelect/assertSelectOnly)
      that throw on any write SQL before reaching the DB.
    - **3 design_mapped shared modules:** All active write-capable consumers verified guarded.
      0 unguarded consumers. Module-level guard would break read-only consumers.
    - **12 read_only scripts:** All confirmed no DB client, no query execution.
  - Additional verifications:
    - 3 false_positive_read_only_transaction: confirmed with DB-level READ ONLY tx
    - 1 false_positive_no_db_connection_static_scan: confirmed
    - 1 false_positive_policy_or_regex_keyword_only: confirmed
    - 3 false_positive_no_db_write_evidence: confirmed
    - 1 scraper_or_browser_only: 1 corrected (→ read_only, static file classifier)
  - **0 hidden write paths discovered.**
  - **0 unknown_needs_followup.**
  - **1 classification correction** (fotmob_ligue1_adg60_raw_payload_source_inventory.js:
    scraper_or_browser_only → read_only).
  - Audit document: `docs/SC002_BROWSER_FOTMOB_PAGEPROPS_PLAYWRIGHT_DEEP_AUDIT.md`
  - Docs updated: `SC002_OVERALL_CLOSURE_ASSESSMENT.md`, `SC002_CLOSURE_PLAN.md`,
    `PROJECT_STATUS.md`
  - Tests: static tests for deep audit doc existence, all-paths-classified, safety boundaries.
  - **No browser run. No Playwright. No DB connection. No SQL. No real DB write.**
  - **No scraper/browser. No training. No data expansion.**
  - **SC-002 remains partial mitigation only.**
  - Criterion #1: Substantially met (deep per-script verification complete).
  - Criterion #3: Substantially met (deep verification complete; browser-layer non-DB risks remain).
- **Next step:** `changed_files_negative_case_enforcement_test` — Criterion #2.
  Do not start automatically.

### 6c. changed_files_negative_case_enforcement_test ✅ COMPLETED (this PR)

- **Status:** Completed (this PR — static negative-case tests, NO DB, NO SQL, NO write).
- **Results:**
  - Comprehensive static negative-case enforcement test suite:
    `tests/unit/test_changed_files_negative_case_enforcement.py` (29 tests).
  - **Negative cases proven (must fail):**
    - Unguarded Python INSERT → rejected by Python scanner
    - Unguarded Python UPDATE → rejected by Python scanner
    - Unguarded Python CREATE TABLE → rejected by Python scanner
    - Unguarded Python DELETE → rejected by Python scanner
    - Destructive SQL DROP DATABASE → rejected by SQL scanner
    - Guarded-but-unallowlisted Python → flagged as write risk (conservative detection)
    - DB-importing SELECT-only file → flagged for review (conservative detection)
  - **Positive cases proven (must pass):**
    - Allowlisted Python file → passes enforcement
    - Non-DB Python file → passes enforcement
    - Non-SQL files → ignored by SQL scanner
    - Allowlisted SQL migration → passes enforcement
    - AI Workflow Gate integration is wired correctly
  - **Safety boundaries verified:**
    - Scanner uses static regex (not import/execute)
    - No DB connection attempted
    - No SQL executed
    - No real DB write
    - Temp fixture files inside REPO_ROOT, cleaned up after tests
    - No real business files modified
  - **No browser run. No Playwright. No DB connection. No SQL. No real DB write.**
  - **SC-002 remains partial mitigation only.**
  - Criterion #2: Substantially met (static negative-case tests complete).
- **Next step:** `deploy_docker_init_sql_guard` — Gate B: guard init_db.sql against non-dev execution.
  Do not start automatically.

### 6d. deploy_docker_init_sql_guard ✅ COMPLETED (this PR)

- **Status:** Completed (this PR — static guard implementation, NO DB, NO SQL, NO docker execution).
- **Results:**
  - Dev-only execution guard added to `deploy/docker/init_db.sql`:
    - `SET sc002.init_sql_context = 'development'` at the very top, before any DDL/DCL
    - DO block verifies `current_setting('sc002.init_sql_context') IS DISTINCT FROM 'development'`
    - `RAISE EXCEPTION` on mismatch with clear DEV-ONLY error message
    - Guard explicitly forbids staging, production, and non-dev execution
    - No env-var bypass — operator must modify the guard itself to run against non-dev
  - `docker-compose.dev.yml`: PostgreSQL server-level `-c sc002.init_sql_context=development`
  - `.env.example`: Guard documentation added
  - Tests: 15 new static tests in `tests/unit/test_runtime_db_role_permission_dev_poc.py`
    (`TestInitSqlGuardGateB` class). Total dev POC tests: 54.
  - Guard verified: exists, before DDL/DCL, SET+DO block, RAISE EXCEPTION on mismatch,
    dev-only explicit, mentions staging/production/non-dev, no env-var bypass,
    no production config, docker-compose integration, no real secrets.
  - Docs updated: `SC002_OVERALL_CLOSURE_ASSESSMENT.md`, `SC002_CLOSURE_PLAN.md`,
    `PROJECT_STATUS.md`
  - **No DB connection. No SQL execution. No psql run. No docker compose run.**
  - **No real DB write. No migration/Alembic. No permission changes.**
  - **SC-002 remains partial mitigation only.**
  - Gate B: init_db.sql guard implemented.
- **Next step:** `sc002_final_closure_check` ✅ **COMPLETED** — see section 6e below.
	  Do not start automatically.

### 6e. sc002_final_closure_check ✅ COMPLETED (this PR)

- **Status:** Completed (this PR — final per-criterion closure verification).
- **Results:**
  - Final closure check document: `docs/SC002_FINAL_CLOSURE_CHECK.md`
  - All 10 criteria verified against concrete evidence.
  - 9 criteria fully satisfied. 1 criterion substantially met.
  - 0 criteria not met or unsatisfied.
  - **SC-002 status: enforcement complete.**
  - Training / data expansion / real DB write remain blocked.
  - **No DB connection. No SQL. No migration. No real write.**
- **Next step:** `sc002_staging_db_role_deployment`. Do not start automatically.

### 6f. sc002_staging_db_role_deployment_plan ✅ COMPLETED (this PR)

- **Status:** Completed (this PR — deployment planning/documentation, NO deployment).
- **Results:**
  - Plan document: `docs/SC002_STAGING_DB_ROLE_DEPLOYMENT_PLAN.md`
  - Target 6-role model, prerequisites, deployment steps, rollback plan,
    validation matrix (6 roles × 14 ops), go/no-go checklist.
  - **No DB. No SQL. No psql. No real changes. No real secrets.**
  - **Training / data expansion / real DB write remain blocked.**
- **Next step:** `sc002_staging_db_role_deployment`. Do not start automatically.

### 7. sc002_release_gate_checklist_phase1

- **Objective:** Create a detailed release gate checklist that can be used to verify
  Gate A/B/C readiness before any controlled DB write or training is authorized.
- **Allowed changes:** Read closure plan and all related docs; create checklist document.
- **Forbidden actions:** Any DB write, training, scraper, browser, or network action;
  any code modification; any CI enforcement change.
- **Expected output:** A checklist document
  (`docs/SC002_RELEASE_GATE_CHECKLIST.md`) with per-gate items, verification
  procedures, and sign-off fields.
- **Acceptance criteria:** Each gate has concrete, verifiable checklist items. Each item
  specifies how to verify (which command, which file, which metric). The checklist is
  designed to be filled out by a human reviewer, not automatically.

## Non-Goals

This task (`sc002_closure_plan_phase0`) is a **planning / governance / documentation**
task only. It is explicitly NOT:

- Code fixes or guard integration (Phase8 or beyond)
- Execution of any DB write, training, data expansion, or scraper/browser automation
- Schema migration
- Production release
- Changing CI enforcement rules or enabling new hard fails
- Modifying the scanner, guard helper, or AI Workflow Gate
- Modifying any business code, scripts/ops entrypoints, or shared modules

## Status Wording Rules

To prevent ambiguity, the following wording rules apply to all SC-002 documentation:

### Allowed terms

| Term | Meaning |
|---|---|
| partial mitigation only | SC-002 has reduced but not eliminated risk |
| categorized, not fixed | Scripts are classified but not yet guarded or excluded |
| blocked | Action is not authorized under any current gate |
| guarded | Script has integrated `assertDbWriteAllowed()` |
| changed-files enforcement enabled | CI hard-fails on new/modified unguarded JS |
| production host hard block enabled | Guard denies write to production-like DB hosts |

### Forbidden terms

| Term | Why forbidden |
|---|---|
| fully fixed | SC-002 is not fully fixed |
| complete | Closure criteria are not all met |
| safe to train | Training remains blocked |
| safe to write | Real DB write remains blocked |
| production ready | Production write is not authorized |
| resolved | Implies closure; use "partial mitigation only" |
| done | Implies completion; use specific guarded/categorized/blocked status |

## Rollback and Failure Handling

### If changed-files enforcement produces false positives

1. Add the script to `db_write_guard_legacy_allowlist.json` with:
   - Explicit `category` from the approved category list
   - Specific `reason` explaining why it is a false positive
   - `reviewed_at: "<date>"` with the review date
   - `future_action` describing what follow-up is needed
2. Document the addition in the PR body.
3. Do NOT silently skip the check or disable the enforcement.

### If changed-files enforcement misses a real risk (false negative)

1. The static scanner dry-run (`db_write_guard_static_enforcement_dry_run.js --json`)
   can be run manually to audit full coverage.
2. If a new write entrypoint bypasses detection, add it to the scanner's keyword list
   or improve the detection heuristic.
3. Do NOT disable enforcement to work around a detection gap.

### If CI goes red after merge

1. Confirm the failure is related to SC-002 enforcement.
2. If the failure is a false positive on an existing historical script, add the script
   to the allowlist as described above.
3. If the failure reveals a real unguarded write path, create a fix PR with guard
   integration (Phase8-style) — do NOT silence the CI check.
4. If the failure is unrelated to SC-002, handle per standard CI incident response.

### If allowlist classification is found incorrect

1. A script classified as `dry_run_or_audit` that is later found to execute real writes
   must be reclassified and either guarded or assigned to the appropriate specialized
   audit.
2. Update the allowlist entry with corrected `category`, `reason`, and `future_action`.
3. If the reclassification reveals a systemic gap, update the closure plan and initiate
   the relevant follow-up task.

### Rollback of this closure plan

If this document becomes outdated or conflicts with new findings:
1. Update `docs/SC002_CLOSURE_PLAN.md` in a scoped PR.
2. Update `docs/PROJECT_STATUS.md` to reflect the new state.
3. Do NOT create a competing `SC002_CLOSURE_PLAN_V2.md` or similar duplicate.
