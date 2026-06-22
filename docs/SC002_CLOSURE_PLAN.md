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
| Changed-files enforcement | hard fail (active) |
| Production-like DB host hard block | enabled |
| Real DB write authorization | no |
| Training status | blocked |
| Data expansion status | blocked |
| Scraper / browser automation status | blocked |
| Python / SQL / migration enforcement | not yet designed |
| Runtime DB role / permission model | not fully validated |

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

4. **Python scripts are not covered.** The guard helper and static scanner only cover
   `scripts/ops/**/*.js`. Python-based DB write scripts (if any exist in the codebase)
   have no equivalent guard mechanism.

5. **SQL / migration paths are not covered.** Schema migrations and raw SQL execution
   paths do not pass through the JS guard helper. There is no equivalent enforcement
   for SQL migration files or migration runner scripts.

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
| 1 | All real DB write entrypoints are guarded or formally classified as non-write | Not met (43/66 guarded, 22+21 remaining) |
| 2 | Changed-files enforcement is active and tested with both positive and negative cases | Partial (active but needs negative-case testing) |
| 3 | Remaining browser/FotMob/pageProps paths have specialized audit results and have been either guarded or formally excluded | Not met |
| 4 | Shared modules have clear responsibility boundary: every consumer of a shared DB write-risk module is identified and verified as guarded or read-only | Not met |
| 5 | Python / SQL / migration enforcement has either a guard mechanism or a documented exclusion with rationale | Not met (not yet designed) |
| 6 | Runtime DB permissions / role restrictions are documented or tested | Not met |
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

### 1. specialized_browser_fotmob_pageprops_audit_phase1

- **Objective:** Audit all 43 skipped_complex scripts (22 allowlisted + 21 browser) to
  verify whether each script can actually execute DB writes, and produce a verified
  classification with per-script findings.
- **Allowed changes:** Read scripts, trace code paths, verify keyword context, update
  allowlist with verified classification, add audit findings to docs.
- **Forbidden actions:** Execute scripts, connect to DB, run browser automation, fetch
  network data, modify business logic, add guards to scripts (reserve for later phase).
- **Expected output:** A verified audit report (`docs/_reports/sc002_complex_candidate_audit.md`)
  with per-script findings: confirmed write-capable, confirmed read-only, or uncertain
  with specific risks. Update allowlist if findings change classification.
- **Acceptance criteria:** Every skipped_complex script has a verified classification
  based on code-path analysis. No script is classified solely by filename pattern.
  Ambiguous scripts are flagged for deeper review.

### 2. shared_module_db_write_boundary_design_phase1

- **Objective:** Design a boundary enforcement mechanism for shared modules
  (`dbBlueprint.js`, `restoreMappingsWorkflow.js`, `odds_harvest_pipeline.shared.js`)
  that ensures every consumer is guarded, without requiring each shared module to
  independently guard itself.
- **Allowed changes:** Read shared modules and their consumers, design boundary
  enforcement (caller tracing, annotation convention, or checklist approach), write
  design doc, update scanner if applicable.
- **Forbidden actions:** Modify shared module business logic, add guard calls to shared
  modules, connect to DB, execute any script.
- **Expected output:** A design document
  (`docs/SC002_SHARED_MODULE_BOUNDARY_DESIGN.md`) specifying the enforcement mechanism,
  consumer inventory, and integration plan.
- **Acceptance criteria:** Every consumer of each shared module with DB write risk is
  identified. The design explicitly states how to verify consumer guard status and how
  to enforce it for future changes. The design is reviewable and implementable in a
  follow-up phase.

### 3. python_sql_migration_enforcement_design_phase1

- **Objective:** Design enforcement mechanisms for Python-based DB write scripts, SQL
  migration files, and migration runner scripts that are outside the current JS-only
  scanner scope.
- **Allowed changes:** Inventory Python scripts and SQL migration files, analyze risks,
  design guard equivalent or documented exclusion, write design doc.
- **Forbidden actions:** Execute Python scripts, run migrations, connect to DB, modify
  migration files, modify Python business logic.
- **Expected output:** A design document
  (`docs/SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md`) with inventory, risk
  assessment, proposed enforcement, and exclusion criteria.
- **Acceptance criteria:** All Python scripts and SQL migration files with DB write risk
  are inventoried. Each has a proposed enforcement mechanism (guard equivalent) or a
  documented exclusion rationale. CI integration plan is specified.

### 4. runtime_db_role_permission_review_phase1

- **Objective:** Review and document the current runtime DB role/permission model.
  Identify whether DB-level restrictions (read-only roles, write-restricted connection
  pools, row-level security) complement or conflict with the application-layer guard.
- **Allowed changes:** Read DB connection configuration, role definitions, migration
  files; document findings; write review doc.
- **Forbidden actions:** Connect to production DB, modify roles or permissions, execute
  GRANT/REVOKE, modify connection pools.
- **Expected output:** A review document
  (`docs/SC002_DB_ROLE_PERMISSION_REVIEW.md`) documenting the current model, gaps, and
  recommendations.
- **Acceptance criteria:** Current DB roles and permissions are documented. Gaps between
  application-layer guard and DB-layer restrictions are identified. Recommendations are
  specific and actionable.

### 5. sc002_release_gate_checklist_phase1

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
