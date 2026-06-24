# SC-002 Overall Closure Assessment

- lifecycle: permanent
- owner: project governance
- created: 2026-06-25
- task: sc002_overall_closure_assessment
- assessment_type: static assessment / gap analysis / roadmap
- sc002_status: partial mitigation only

## Summary

This document provides an **overall closure assessment** for SC-002 (DB write safety gate).
It evaluates each of the 10 closure criteria defined in `docs/SC002_CLOSURE_PLAN.md` §6,
identifies remaining gaps, and recommends the single next task.

**This is an assessment/documentation task. It does NOT:**
- Implement any runtime guard
- Modify any business code
- Connect to any database
- Execute any SQL / migration / Alembic
- Perform any real DB write
- Run scraper / browser / Playwright
- Train or expand data
- Unlock any blocked state
- Claim SC-002 complete

## Per-Criterion Assessment

### Criterion 1: All real DB write entrypoints guarded or formally classified

**Current status:** Partially met. Substantial progress, remaining gaps exist.

**JS side — what is guarded:**
- 43 P0 `scripts/ops/**/*.js` entrypoints (Phase1–Phase7)
- 6 confirmed JS write paths (previously skipped_complex)
- 3 shared-module write-capable consumers (`odds_harvest_pipeline.js`, `gatekeeper.js`, `gatekeeper.sh`)
- **Total JS guarded: 52 entrypoints with real DB write capability**

**JS side — what is classified but NOT individually guarded:**
- 22 scripts in legacy allowlist: 9 pageprops_pipeline, 2 fotmob_pipeline, 3 shared_module, 8 dry_run_or_audit
  - These are **categorized**, not **fixed**. Each has an explicit category, reason, reviewed_at, future_action.
  - The 8 dry_run_or_audit scripts are likely read-only but haven't been verified per-script.
  - The 3 shared_module scripts are helper libraries — guard responsibility is at consumer level.
- 21 additional browser/Playwright scripts classified as `skipped_complex`:
  - After `specialized_browser_fotmob_pageprops_audit_phase1`, all 43 total skipped_complex were classified.
  - 13 guarded, 13 false_positive_select_only, 3 false_positive_read_only_transaction,
    3 false_positive_no_db_write, 1 false_positive_policy_keyword, 12 read_only,
    3 design_mapped, 1 scraper_or_browser_only, 0 needs_manual_review.
  - **Key gap:** The "design_mapped" and "false_positive" classifications are based on static
    analysis. Some scripts have not had deep per-script verification of non-write behavior
    under all runtime conditions.

**Python side — fully resolved:**
- All 20 Python write paths classified and resolved (18 guarded, 2 safe reclassified)
- 0 pending. 0 unreviewed.
- Alembic migration orchestrator (`env.py`) now guarded.

**Assessment for Criterion 1: Partially met.**
The majority of real DB write entrypoints are guarded. The remaining gap is the
22 categorized + 21 skipped_complex JS scripts that are classified but not individually
guarded. Many of these are likely read-only or non-executing, but this hasn't been
confirmed through deep per-script verification. For SC-002 closure, either each of these
must be individually verified as non-write, or the remaining ones with confirmed write
capability must be guarded.

### Criterion 2: Changed-files enforcement negative-case testing

**Current status:** Not met.

**What exists:**
- `scripts/ops/ai_workflow_gate.py` has `check_python_db_write_enforcement()` and
  `check_sql_migration_policy()` functions that hard-fail on new/modified unguarded files.
- JS changed-files enforcement is active for `scripts/ops/**/*.js`.
- SQL migration scanner (Phase2B) is active in CI.

**What is missing:**
- **Negative-case testing:** Has the enforcement been deliberately tested with a PR
  that adds an unguarded JS/Python/SQL file to confirm it correctly fails?
- **Positive-case testing:** Has it been tested that an allowlisted file passes correctly?
- **Edge-case testing:** Modified-but-not-new files, renamed files, files with false-positive
  keyword matches — are these handled correctly?

**Assessment for Criterion 2: Not met.**
The enforcement is active and working (multiple PRs have passed it successfully), but
deliberate negative-case testing — creating a PR with a known-unguarded file to confirm
the gate rejects it — has not been performed. This is a standard CI hardening practice.

### Criterion 3: Browser/FotMob/pageProps paths specialized audit

**Current status:** Partially met — classification exists, deep verification incomplete.

**What exists:**
- `specialized_browser_fotmob_pageprops_audit_phase1` completed. 43 skipped_complex scripts
  classified into categories with supporting evidence.
- Audit document: `docs/SC002_BROWSER_FOTMOB_PAGEPROPS_AUDIT.md`
- Key finding: 13 scripts have confirmed DB write capability (all now guarded).
  13 are false positive (SELECT-only wrappers), 12 are read-only, 3 design_mapped,
  1 scraper/browser only.

**What is missing:**
- The "false_positive_select_only_with_active_wrapper" classification (13 scripts) was
  done via static scan. A deep per-script verification — confirming that each script's
  code paths cannot reach a real DB write under any condition — has not been done.
- The "design_mapped" category (3 scripts) have identified follow-up needs but the
  follow-up tasks are not yet completed.
- Browser-layer risks (Playwright session management, cookie handling, captcha bypass)
  are documented as separate from DB write risks but have not been systematically reviewed.

**Assessment for Criterion 3: Partially met.**
The audit has classified all scripts, which is significant progress. But "classified" is
not the same as "verified non-write" or "guarded." The 13 false_positive_select_only
scripts need deeper verification to confirm they cannot write under any runtime condition.

### Criterion 4: Shared module consumer boundary

**Current status:** Substantially met — current consumers covered, proactive enforcement missing.

**What exists:**
- All 3 shared modules mapped with full consumer inventory in
  `docs/SC002_SHARED_MODULE_DB_WRITE_BOUNDARY_DESIGN.md`:
  - `dbBlueprint.js`: 24 consumers mapped, 3 write-capable (all now guarded), 18 read-only, 3 needs_manual_review (resolved)
  - `restoreMappingsWorkflow.js`: 0 active consumers
  - `odds_harvest_pipeline.shared.js`: 2 consumers (both now guarded)
- All active write-capable consumers now guarded.
- All 9 needs_manual_review consumers reviewed and reclassified.
- Guard responsibility documented at consumer entrypoint level.

**What is missing:**
- **Proactive boundary enforcement:** If a new entrypoint imports `dbBlueprint.js` and
  uses its write methods, there is no CI check that would detect this. The current
  enforcement scans for DB write keywords in the new file itself, but if the new file
  delegates write logic to the shared module, it might not trigger the keyword scanner.
- A caller-tracing mechanism or consumer checklist that triggers on shared module import
  changes has been designed but not implemented.

**Assessment for Criterion 4: Substantially met with documented gap.**
All current consumers are covered. A design for proactive enforcement exists. The
implementation of proactive enforcement is a future enhancement, not a current blocker.

### Criterion 5: Python / SQL / migration enforcement

**Current status: Met** (with deploy/docker/init_db.sql caveat tracked separately under Gate B).

**Python track:**
- ALL 20 Python write paths classified and resolved: 18 runtime guarded, 2 safe reclassified.
- Python static scanner (Phase2A): active in CI with changed-files enforcement.
- Python guard helper: `scripts/ops/helpers/python_db_write_guard.py` — enforces the same
  env-var model as the JS guard.
- Alembic migration orchestrator (`env.py`): now guarded with specialized migration guard
  (`_check_alembic_migration_guard()` in `run_migrations_online()`).
- 0 pending. 0 unreviewed.

**SQL/migration track:**
- SQL migration scanner (Phase2B): active in CI with changed-files enforcement.
- SQL migration policy allowlist: 22 entries, all historical SQL files classified.
- 0 destructive migrations found. Destructive SQL always fails gate.
- Alembic migration version scripts (3 files): classified and in allowlist.

**Remaining caveat:**
`deploy/docker/init_db.sql`:
- Contains full DDL (CREATE TABLE, CREATE EXTENSION) and seed INSERT.
- Designed for Docker dev environment initialization only.
- No runtime guard prevents execution against a non-dev database.
- Classified as `sql_seed_or_data_write_needs_gate` in the SQL allowlist.
- This is a Gate B concern (controlled staging DB write), not a Python/SQL enforcement gap.

**Assessment for Criterion 5: Met.**
The Python track is fully complete. The SQL/migration track has CI enforcement and
classification. `deploy/docker/init_db.sql` is tracked separately under Gate B and
does not block this criterion.

### Criterion 6: Runtime DB role / permission model

**Current status: Not met.**

**What exists:**
- Application-layer guard (`assertDbWriteAllowed` / `assert_db_write_allowed`) enforces
  write authorization through environment variables.
- Production-like DB host hard block at the application layer.
- `deploy/docker/init_claude_reader.sql` creates a read-only PostgreSQL user for MCP.

**What is missing:**
- No systematic review of current DB roles, permissions, and connection pool configurations.
- No verification that application-layer guard and DB-layer permissions are aligned.
- No review of whether PostgreSQL row-level security or role-based access could complement
  the application-layer guard.
- The task `runtime_db_role_permission_review_phase1` is defined in the closure plan
  but has not been executed.

**Assessment for Criterion 6: Reviewed, not yet met for implementation.**
`runtime_db_role_permission_review_phase1` has been completed. The static audit
documented 8 specific risks and designed a target 6-role model. See
`docs/SC002_RUNTIME_DB_ROLE_PERMISSION_REVIEW_PHASE1.md` for full analysis.
Implementation (role creation, privilege grants) has not been started.
Criterion #6 remains unmet for implementation.

### Criterion 7: No production override exists

**Current status: Met.**

- No `ALLOW_PRODUCTION_DB_WRITE` bypass variable exists.
- Production-like DB hosts (RDS, Cloud SQL, Supabase, Railway, Render, Heroku) are
  hard-blocked by the guard helper with no override.
- Production environment detection (`ENV=production`, `NODE_ENV=production`, etc.)
  triggers hard block.
- `DRY_RUN=true` is the default — explicit `DRY_RUN=false` is required for any write.

**Assessment for Criterion 7: Met.** No gaps identified.

### Criterion 8: Training and data expansion remain blocked

**Current status: Met.**

- Training is blocked by explicit env-var gates (`ALLOW_TRAINING_WRITE=yes` required).
- Data expansion is blocked by explicit env-var gates.
- No training or data expansion has been executed.
- PR-body template, CI gate, and agent workflow rules all explicitly enforce this block.
- All SC-002 documentation consistently states training/data expansion are blocked.

**Assessment for Criterion 8: Met.** Blocks are in place and enforced.

### Criterion 9: PROJECT_STATUS.md matches closure state

**Current status: Will be verified at closure.**

- `docs/PROJECT_STATUS.md` is actively maintained and reflects current SC-002 state.
- Each phase completion updates PROJECT_STATUS.md.
- A final verification at closure time will confirm full alignment.

**Assessment for Criterion 9: In good standing.** The doc is being maintained throughout.

### Criterion 10: CI green after closure PR merge

**Current status: Will be verified at closure.**

- Main branch Production Gate is currently green.
- This is a per-PR check that must pass at closure time.

**Assessment for Criterion 10: In good standing.** Standard CI discipline applies.

## deploy/docker/init_db.sql: Additional Risk

Although not part of the 10 formal closure criteria, `deploy/docker/init_db.sql` is
tracked in the closure plan (Current State table row 14, Category D) and the SQL
migration policy allowlist. It contains:

- Full DDL: CREATE TABLE, CREATE EXTENSION, CREATE INDEX
- Seed data: INSERT statements for development initialization

**Risk:** If accidentally executed against a non-dev database (e.g., production), it
would create tables and insert seed data. There is no runtime guard on this file —
it depends entirely on the operator knowing it is Docker-only.

**Status:** Classified as `sql_seed_or_data_write_needs_gate`. Needs a guard that:
- Validates the execution context (must be Docker dev environment)
- Blocks execution against production-like hosts
- Requires explicit authorization for any non-Docker execution

This is assigned to Gate B (controlled staging DB write), not the Python/SQL track.

## Summary Table

| # | Criterion | Status | Key Gap |
|---|---|---|---|
| 1 | All real DB write entrypoints guarded | **Partial** | 43 skipped_complex JS scripts classified but not individually verified non-write |
| 2 | Changed-files enforcement negative-case testing | **Not met** | No deliberate negative-case CI test with known-unguarded file |
| 3 | Browser/FotMob/pageProps specialized audit | **Partial** | 13 false_positive scripts need deep verification; 3 design_mapped need follow-up |
| 4 | Shared module consumer boundary | **Substantially met** | Proactive enforcement (caller tracing) designed but not implemented |
| 5 | Python/SQL/migration enforcement | **Met** | `init_db.sql` caveat tracked under Gate B |
| 6 | Runtime DB role/permission model | **Reviewed** | Static audit done (8 risks, target model). Implementation not started. |
| 7 | No production override exists | **Met** | No gaps |
| 8 | Training/data expansion blocked | **Met** | No gaps |
| 9 | PROJECT_STATUS.md matches closure state | **Good standing** | Will verify at closure |
| 10 | CI green after closure PR merge | **Good standing** | Per-PR check |

**SC-002 overall verdict: partial mitigation only. Cannot be closed.**
4 criteria met (5, 7, 8) or in good standing (9, 10).
4 criteria partially met or not met (1, 2, 3, 4).
2 criteria not met (6, plus init_db.sql caveat).

## Gap Priority and Effort

| Priority | Criterion | Effort | Rationale |
|---|---|---|---|
| 1 | #6 — DB role/permission review | Low | Documentation/review task. Clear scope in CLOSURE_PLAN. No code changes. |
| 2 | #2 — Negative-case testing | Low-Medium | CI test task. Create test PR with unguarded file, verify gate rejects it. |
| 3 | #3 — Deep verification of false_positive scripts | Medium | 13 scripts need per-script path verification. Static analysis already done. |
| 4 | #1 — Complete classification closure | Medium | Convert "categorized" to "verified non-write" or "guarded" for remaining scripts. |
| 5 | #4 — Proactive boundary enforcement | Medium-High | Design implementation. Could be deferred to post-closure enhancement. |

## Next Recommended Task

**`runtime_db_role_permission_review_phase1`**

This is the highest-priority, lowest-effort remaining task:
- **Objective:** Review and document the current runtime DB role/permission model.
- **Scope:** Read-only audit of DB connection configuration, role definitions, migration
  files. Document findings, gaps, and recommendations.
- **Why this task:** It unblocks criterion #6, has the lowest implementation risk
  (documentation only, no code changes), and is a prerequisite for Gate B readiness.
- **Forbidden:** Connect to production DB, modify roles or permissions, execute
  GRANT/REVOKE, modify connection pools.

**Do not start automatically.** Recommended next task only after user confirmation.

## Non-Goals of This Assessment

This assessment does NOT:
- Authorize any DB write, migration, training, or data expansion
- Change the blocked status of any Gate (A, B, or C)
- Implement any runtime guard or CI enforcement change
- Modify business code, configuration, or test fixtures beyond documentation
- Claim SC-002 is complete, resolved, or fully fixed
- Claim "safe to train," "safe to write," or "production ready"

SC-002 remains **partial mitigation only**. Training, data expansion, and real DB write
remain **blocked**.
