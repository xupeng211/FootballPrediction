# SC-002 Manual Review Phase 1

- lifecycle: permanent
- owner: project governance
- created: 2026-06-23
- task: manual_review_phase1

## Summary

This is a **static review and classification document only**. It reviews all remaining
`needs_manual_review` and `possible_indirect_write` consumers from the SC-002 audit and
shared module boundary design. It classifies each based on static code evidence.

**This document does NOT:**
- Implement any guard
- Run any target script
- Connect to any database
- Execute any real DB write
- Run scraper/browser/Playwright
- Train, expand data, or run schema migrations
- Claim SC-002 is fully fixed

**This document DOES:**
- Statically review all 14 remaining `needs_manual_review` / `possible_indirect_write` scripts
- Reclassify each based on code evidence
- Identify confirmed guard candidates (none found — all already guarded or no write)
- Update cross-document consistency counts
- Provide a complete, authoritative classification closure for the skipped_complex and
  shared-module consumer audits

## Scope

### In scope

- 9 `needs_manual_review` consumers from the `dbBlueprint.js` consumer map
  (`docs/SC002_SHARED_MODULE_DB_WRITE_BOUNDARY_DESIGN.md`)
- 4 `needs_manual_review` scripts from the broader skipped_complex audit
  (`docs/SC002_BROWSER_FOTMOB_PAGEPROPS_AUDIT.md`)
- 1 `possible_indirect_write` script from the broader audit

### Out of scope

- Scripts already confirmed as guarded (45+ Phase1–Phase7 + gatekeeper + odds_harvest_pipeline)
- Scripts already reclassified as false positives (14 by allowlist_cleanup_phase1)
- Shared modules themselves (dbBlueprint.js, restoreMappingsWorkflow.js, odds_harvest_pipeline.shared.js)
- Python/SQL/migration enforcement
- Implementation of any guard
- Runtime behavior change of any kind

## Authoritative needs_manual_review list

### Count summary

| Source | Count | Notes |
|---|---|---|
| Design doc dbBlueprint consumers | **9** | Previously listed as "8" in #1593 PR body — a typo. Actual count is 9. |
| Audit doc pageProps needs_manual_review | **4** | From the broader 43-script skipped_complex audit |
| Audit doc possible_indirect_write | **1** | training_pipeline_smoke_dry_run.js |
| **Total reviewed** | **14** | |

### Count mismatch explanation

**Previous PR #1593 reported "8 needs_manual_review consumers" — this was a typo.**
The design doc's dbBlueprint consumer table (rows 9–22) lists 9 scripts with
`recommended_task: manual_review`. The #1593 PR body listed 9 names in its Scope
section but the count claimed 8. Verified count: **9** (not 8).

Additionally, the broader audit doc separately classifies 4 pageProps scripts and
1 possible_indirect_write script as needing review. These were not counted in the
shared-module-specific PR #1593 because that PR focused only on shared module consumers.

**Corrected authoritative count: 14 scripts across both documents.**

### Authoritative paths

**Group A — dbBlueprint consumers (design doc): 9 scripts**
1. `scripts/ops/cleanup_csv_bulk_loader_import.js`
2. `scripts/ops/fetch_and_adapt_euro_leagues.js`
3. `scripts/ops/master_inventory.js`
4. `scripts/ops/purge_ghost_data.js`
5. `scripts/ops/purge_orphans.js`
6. `scripts/ops/raw_match_data_completeness_fidelity_audit.js`
7. `scripts/ops/renewed_pageprops_v2_raw_write_execute.js`
8. `scripts/ops/reset_database.js`
9. `scripts/ops/seed_fotmob_sample.js`

**Group B — pageProps needs_manual_review (audit doc): 4 scripts**
10. `scripts/ops/all_seeded_pageprops_v2_canonical_read_verification.js`
11. `scripts/ops/pageprops_v2_identity_contract_regression_execute.js`
12. `scripts/ops/pageprops_v2_post_write_canonical_read_verification.js`
13. `scripts/ops/pageprops_v2_suspended_target_review_execute.js`

**Group C — possible_indirect_write (audit doc): 1 script**
14. `scripts/ops/training_pipeline_smoke_dry_run.js`

## Per-consumer findings

### Consumer #1: cleanup_csv_bulk_loader_import.js

| Dimension | Evidence |
|---|---|
| File exists | Yes |
| File type | JS (CLI script) |
| Import pg/Pool | Yes — `const { Pool } = require('pg')` at line 4 |
| Import dbBlueprint | Yes — `buildDbConnectionConfig` at line 7 |
| Import db_write_guard | **Yes** — `assertDbWriteAllowed` at line 8 |
| Create pool | Yes |
| Executable query | Yes — `client.query(sql)` |
| Write SQL in code | Yes — DELETE at lines 101, 111, 116; BEGIN/COMMIT/ROLLBACK transaction at lines 100, 129, 137 |
| Write SQL real vs comment | Real — executable DELETE statements in `cleanAllImportedRows()` |
| DRY_RUN default | No explicit dry-run default |
| Guard present | **Yes** — `assertDbWriteAllowed({ script: 'cleanup_csv_bulk_loader_import.js', tables: [...], operations: ['DELETE'] })` at line 94 |
| Guard before write | **Yes** — guard at line 94, BEGIN at line 100 |
| Production host hard block | Yes — via db_write_guard.js |
| Classification | **already_guarded** |
| Evidence summary | Properly guarded with assertDbWriteAllowed BEFORE BEGIN transaction. DELETE operations correctly gated. |

### Consumer #2: fetch_and_adapt_euro_leagues.js

| Dimension | Evidence |
|---|---|
| File exists | Yes |
| File type | JS (CLI script) |
| Import pg/Pool | Yes — `const { Pool } = require('pg')` at line 11 |
| Import dbBlueprint | Yes — `REPO_ROOT`, `buildDbConnectionConfig` at line 15 |
| Import db_write_guard | No |
| Create pool | Yes |
| Executable query | Yes — `pool.query(...)` for SELECT only |
| Write SQL in code | **None** — only SELECT queries (league lookup, team queries, etc.) |
| DRY_RUN default | Not applicable (read-only) |
| Guard present | No — but not needed (SELECT-only) |
| Production host hard block | Yes — but irrelevant (SELECT-only) |
| Classification | **false_positive_no_db_write_evidence** |
| Evidence summary | Despite importing pg/Pool + buildDbConnectionConfig, this script only executes SELECT queries. No INSERT/UPDATE/DELETE/DROP/TRUNCATE/CREATE/ALTER in executable code. Read-only data fetch and transformation pipeline. |

### Consumer #3: master_inventory.js

| Dimension | Evidence |
|---|---|
| File exists | Yes |
| File type | JS (CLI script) |
| Import pg/Pool | Yes — `const { Pool } = require('pg')` at line 4 |
| Import dbBlueprint | Yes — `buildDbConnectionConfig` at line 6 |
| Import db_write_guard | No |
| Create pool | Yes |
| Executable query | Yes — `pool.query(...)` for SELECT only |
| Write SQL in code | **None** — only SELECT queries for inventory listing |
| DRY_RUN default | Not applicable (read-only) |
| Guard present | No — but not needed (SELECT-only) |
| Production host hard block | Yes — but irrelevant (SELECT-only) |
| Classification | **false_positive_no_db_write_evidence** |
| Evidence summary | Despite importing pg/Pool + buildDbConnectionConfig, this script only executes SELECT queries. Read-only inventory listing. No INSERT/UPDATE/DELETE/DROP/TRUNCATE in executable code. |

### Consumer #4: purge_ghost_data.js

| Dimension | Evidence |
|---|---|
| File exists | Yes |
| File type | JS (CLI script) |
| Import pg/Pool | Yes — `const { Pool } = require('pg')` at line 4 |
| Import dbBlueprint | Yes — `buildDbConnectionConfig` at line 7 |
| Import db_write_guard | **Yes** — `assertDbWriteAllowed` at line 8 |
| Create pool | Yes |
| Executable query | Yes — `client.query(sql)` |
| Write SQL in code | Yes — DELETE at lines 94, 136, 139; BEGIN/COMMIT/ROLLBACK at lines 133, 140, 149 |
| Write SQL real vs comment | Real — executable DELETE statements in `purgeGhostData()` |
| DRY_RUN default | No explicit dry-run default |
| Guard present | **Yes** — `assertDbWriteAllowed({ script: 'purge_ghost_data.js', tables: [...], operations: ['DELETE'] })` at line 127 |
| Guard before write | **Yes** — guard at line 127, BEGIN at line 133 |
| Production host hard block | Yes — via db_write_guard.js |
| Classification | **already_guarded** |
| Evidence summary | Properly guarded with assertDbWriteAllowed BEFORE BEGIN transaction. DELETE operations correctly gated. |

### Consumer #5: purge_orphans.js

| Dimension | Evidence |
|---|---|
| File exists | Yes |
| File type | JS (CLI script) |
| Import pg/Pool | Yes — `const { Pool } = require('pg')` at line 4 |
| Import dbBlueprint | Yes — `buildDbConnectionConfig` at line 7 |
| Import db_write_guard | **Yes** — `assertDbWriteAllowed` at line 8 |
| Create pool | Yes |
| Executable query | Yes — `client.query(sql)` |
| Write SQL in code | Yes — DELETE at lines 132, 145; BEGIN/COMMIT/ROLLBACK at lines 131, 151, 159 |
| Write SQL real vs comment | Real — executable DELETE statements |
| DRY_RUN default | No explicit dry-run default |
| Guard present | **Yes** — `assertDbWriteAllowed({ script: 'purge_orphans.js', tables: [...], operations: ['DELETE'] })` at line 125 |
| Guard before write | **Yes** — guard at line 125, BEGIN at line 131 |
| Production host hard block | Yes — via db_write_guard.js |
| Classification | **already_guarded** |
| Evidence summary | Properly guarded with assertDbWriteAllowed BEFORE BEGIN transaction. DELETE operations correctly gated. |

### Consumer #6: raw_match_data_completeness_fidelity_audit.js

| Dimension | Evidence |
|---|---|
| File exists | Yes |
| File type | JS (CLI script) |
| Import pg/Pool | Yes (lazy) — `const { Pool } = require('pg')` inside `createDefaultPool()` at line 760 |
| Import dbBlueprint | Yes (lazy) — `buildDbConnectionConfig` at line 761 |
| Import db_write_guard | **Yes** — `assertDbWriteAllowed` at line 4 |
| Create pool | Yes (lazy) |
| Executable query | Yes |
| Write SQL in code | Guarded — SQL mutation guard at line 718 blocks INSERT/UPDATE/DELETE/TRUNCATE/ALTER/DROP/CREATE |
| DRY_RUN default | Not applicable (audit context) |
| Guard present | **Yes** — `assertDbWriteAllowed` at line 783 + SQL mutation guard |
| Guard before write | Yes |
| Production host hard block | Yes — via db_write_guard.js |
| Classification | **already_guarded** |
| Evidence summary | Imports assertDbWriteAllowed at line 4. Has guarded write paths with both SQL-level and entrypoint-level protection. |

### Consumer #7: renewed_pageprops_v2_raw_write_execute.js

| Dimension | Evidence |
|---|---|
| File exists | Yes |
| File type | JS (CLI script) |
| Import pg/Pool | Yes (lazy) — via base module `single_league_pageprops_v2_controlled_write_execute.js` |
| Import dbBlueprint | Yes (lazy) — via base module |
| Import db_write_guard | **Transitive** — base module imports `assertDbWriteAllowed` at line 8, calls at line 1518 |
| Create pool | Yes (via base) |
| Executable query | Yes — INSERT at lines 784, 802; BEGIN/COMMIT/ROLLBACK |
| Write SQL real vs comment | Real — executable INSERT statements routed through base's `queryControlledWrite` |
| DRY_RUN default | Via base module |
| Guard present | **Yes (transitive)** — base.assertDbWriteAllowed at line 1518 of base, invoked before BEGIN transactions in base's `queryControlledWrite` |
| Guard before write | Yes — base module guard is before all write operations |
| Production host hard block | Yes — via base module's db_write_guard |
| Classification | **already_guarded** (transitive via base module) |
| Evidence summary | Inherits full guard coverage from `single_league_pageprops_v2_controlled_write_execute.js` (Phase 2 batch 1 guarded). All write operations go through base's `queryControlledWrite` which calls assertDbWriteAllowed before BEGIN. |

### Consumer #8: reset_database.js

| Dimension | Evidence |
|---|---|
| File exists | Yes |
| File type | JS (CLI script) |
| Import pg/Pool | Yes — `const { Pool } = require('pg')` at line 4 |
| Import dbBlueprint | Yes — `buildDbConnectionConfig` at line 6 |
| Import db_write_guard | **Yes** — `assertDbWriteAllowed` at line 7 |
| Create pool | Yes |
| Executable query | Yes — `client.query(sql)` |
| Write SQL in code | Yes — TRUNCATE at lines 91, 95; BEGIN/COMMIT/ROLLBACK at lines 94, 96, 107 |
| Write SQL real vs comment | Real — executable TRUNCATE statements |
| DRY_RUN default | No explicit dry-run default |
| Guard present | **Yes** — `assertDbWriteAllowed({ script: 'reset_database.js', tables: [...], operations: ['TRUNCATE'] })` at line 88 |
| Guard before write | **Yes** — guard at line 88, BEGIN at line 94 |
| Production host hard block | Yes — via db_write_guard.js |
| Classification | **already_guarded** |
| Evidence summary | Properly guarded with assertDbWriteAllowed BEFORE BEGIN transaction. TRUNCATE operations correctly gated. |

### Consumer #9: seed_fotmob_sample.js

| Dimension | Evidence |
|---|---|
| File exists | Yes |
| File type | JS (CLI script) |
| Import pg/Pool | Yes — `const { Pool } = require('pg')` at line 6 |
| Import dbBlueprint | Yes — `buildDbConnectionConfig`, `REPO_ROOT` at line 8 |
| Import db_write_guard | **Yes** — `assertDbWriteAllowed` at line 10 |
| Create pool | Yes |
| Executable query | Yes — `client.query(sql)` |
| Write SQL in code | Yes — INSERT at lines 537, 586; UPDATE/ON CONFLICT DO UPDATE at lines 553, 565, 595; BEGIN/COMMIT/ROLLBACK at lines 647, 650, 663 |
| Write SQL real vs comment | Real — executable INSERT/UPDATE with ON CONFLICT |
| DRY_RUN default | No explicit dry-run default |
| Guard present | **Yes** — `assertDbWriteAllowed({ script: 'seed_fotmob_sample.js', tables: [...], operations: ['INSERT', 'UPDATE'] })` at line 635 |
| Guard before write | **Yes** — guard at line 635, BEGIN at line 647 |
| Production host hard block | Yes — via db_write_guard.js |
| Classification | **already_guarded** |
| Evidence summary | Properly guarded with assertDbWriteAllowed BEFORE BEGIN transaction. INSERT/UPDATE with ON CONFLICT DO UPDATE correctly gated. |

### Consumer #10: all_seeded_pageprops_v2_canonical_read_verification.js

| Dimension | Evidence |
|---|---|
| File exists | Yes |
| File type | JS (CLI script) |
| Import pg/Pool | Indirect — via `require('../../config/database').getPool()` at line 867 |
| Import dbBlueprint | No |
| Import db_write_guard | No |
| Create pool | Indirect |
| Executable query | Yes — SELECT only |
| Write SQL in code | **None** — has `assertSelectOnly()` function at line 430 blocking INSERT/UPDATE/DELETE/TRUNCATE/ALTER/DROP/CREATE/MERGE/COPY/BEGIN/COMMIT/ROLLBACK |
| DRY_RUN default | Not applicable (read-only verification) |
| Guard present | Self-protected — `assertSelectOnly()` wrapper enforces SELECT-only at query level |
| Production host hard block | Not applicable (SELECT-only) |
| Classification | **false_positive_select_only_with_active_wrapper** |
| Evidence summary | All DB queries pass through `assertSelectOnly()` wrapper which actively blocks any non-SELECT SQL. No write path exists. SQL mutation guard at line 435 covers all write verbs. Read-only canonical verification. |

### Consumer #11: pageprops_v2_identity_contract_regression_execute.js

| Dimension | Evidence |
|---|---|
| File exists | Yes |
| File type | JS (CLI script) |
| Import pg/Pool | **No** |
| Import dbBlueprint | **No** |
| Import db_write_guard | **No** |
| Create pool | No |
| Executable query | No |
| Write SQL in code | **None** |
| DRY_RUN default | Not applicable (no DB) |
| Guard present | Not applicable (no DB connection) |
| Production host hard block | Not applicable |
| Classification | **false_positive_no_db_write_evidence** |
| Evidence summary | Zero database connection code. Pure file I/O on manifest JSON files and markdown reports. Imports `pageprops_v2_no_write_payload_recapture_execute.js` (also no DB). Uses `FotMobRouteIdentityReconciler` for route identity operations only. No SQL, no Pool, no pg, no dbBlueprint. |

### Consumer #12: pageprops_v2_post_write_canonical_read_verification.js

| Dimension | Evidence |
|---|---|
| File exists | Yes |
| File type | JS (CLI script) |
| Import pg/Pool | Indirect — via `require('../../config/database').getPool()` at line 686 |
| Import dbBlueprint | No |
| Import db_write_guard | No |
| Create pool | Indirect |
| Executable query | Yes — SELECT only |
| Write SQL in code | **None** — has `assertSelectOnly()` function at line 253 blocking INSERT/UPDATE/DELETE/TRUNCATE/ALTER/DROP/CREATE/MERGE/COPY/BEGIN/COMMIT/ROLLBACK |
| DRY_RUN default | Not applicable (read-only verification) |
| Guard present | Self-protected — `assertSelectOnly()` wrapper enforces SELECT-only at query level |
| Production host hard block | Not applicable (SELECT-only) |
| Classification | **false_positive_select_only_with_active_wrapper** |
| Evidence summary | All DB queries pass through `assertSelectOnly()` wrapper which actively blocks any non-SELECT SQL. No write path exists. SQL mutation guard at line 258 covers all write verbs. Read-only post-write verification. |

### Consumer #13: pageprops_v2_suspended_target_review_execute.js

| Dimension | Evidence |
|---|---|
| File exists | Yes |
| File type | JS (CLI script) |
| Import pg/Pool | **No** |
| Import dbBlueprint | **No** |
| Import db_write_guard | **No** |
| Create pool | No |
| Executable query | No |
| Write SQL in code | **None** |
| DRY_RUN default | Not applicable (no DB) |
| Guard present | Not applicable (no DB connection) |
| Production host hard block | Not applicable |
| Classification | **false_positive_no_db_write_evidence** |
| Evidence summary | Zero database connection code. Pure file I/O on manifest/report files. No SQL, no Pool, no pg, no dbBlueprint. Completely DB-independent. |

### Consumer #14: training_pipeline_smoke_dry_run.js

| Dimension | Evidence |
|---|---|
| File exists | Yes |
| File type | JS (CLI script) |
| Import pg/Pool | Yes (lazy) — `const { Pool } = require('pg')` inside `openReadOnlyClient()` at line 125 |
| Import dbBlueprint | No — uses local `buildDbConfig()` function (lines 107-118) |
| Import db_write_guard | No |
| Create pool | Yes (lazy) |
| Executable query | Yes — `pool.query(sql)` |
| Write SQL in code | **None** — uses `BEGIN READ ONLY` (line 10), `ROLLBACK` (line 11), `assertSelectOnlySql()` (line 140) |
| Write SQL real vs comment | Not applicable — all queries are wrapped in READ ONLY transaction |
| DRY_RUN default | Implicit — `actual_update_executed: false` markers at lines 465, 583 |
| Guard present | Self-protected — `assertSelectOnlySql()` allows only SELECT, WITH, BEGIN READ ONLY, ROLLBACK |
| Production host hard block | Not applicable (read-only transaction) |
| Classification | **false_positive_read_only_transaction** |
| Evidence summary | Uses BEGIN READ ONLY + ROLLBACK pattern. assertSelectOnlySql() explicitly restricts to SELECT-only SQL. Explicit actual_update_executed: false markers document that no actual writes occur. |

## Reclassification decisions

### Summary table

| # | Script | Old Classification | New Classification |
|---|---|---|---|
| 1 | cleanup_csv_bulk_loader_import.js | needs_manual_review | **already_guarded** |
| 2 | fetch_and_adapt_euro_leagues.js | needs_manual_review | **false_positive_no_db_write_evidence** |
| 3 | master_inventory.js | needs_manual_review | **false_positive_no_db_write_evidence** |
| 4 | purge_ghost_data.js | needs_manual_review | **already_guarded** |
| 5 | purge_orphans.js | needs_manual_review | **already_guarded** |
| 6 | raw_match_data_completeness_fidelity_audit.js | needs_manual_review | **already_guarded** |
| 7 | renewed_pageprops_v2_raw_write_execute.js | needs_manual_review | **already_guarded** (transitive) |
| 8 | reset_database.js | needs_manual_review | **already_guarded** |
| 9 | seed_fotmob_sample.js | needs_manual_review | **already_guarded** |
| 10 | all_seeded_pageprops_v2_canonical_read_verification.js | needs_manual_review | **false_positive_select_only_with_active_wrapper** |
| 11 | pageprops_v2_identity_contract_regression_execute.js | needs_manual_review | **false_positive_no_db_write_evidence** |
| 12 | pageprops_v2_post_write_canonical_read_verification.js | needs_manual_review | **false_positive_select_only_with_active_wrapper** |
| 13 | pageprops_v2_suspended_target_review_execute.js | needs_manual_review | **false_positive_no_db_write_evidence** |
| 14 | training_pipeline_smoke_dry_run.js | possible_indirect_write | **false_positive_read_only_transaction** |

### Reclassification counts

| Category | Count |
|---|---|
| already_guarded | **7** (6 direct + 1 transitive) |
| false_positive_no_db_write_evidence | **3** |
| false_positive_select_only_with_active_wrapper | **2** |
| false_positive_read_only_transaction | **1** |
| confirmed_write_path_needs_guard | **0** |
| remaining needs_manual_review | **0** |

## Confirmed guard candidates

**None.** All 14 reviewed scripts are either:
- Already guarded (7 — guard integrated in earlier Phase1–Phase7 guard phases)
- No write evidence (3 — SELECT-only or no DB connection)
- Self-protected with active SELECT-only wrappers (2)
- Self-protected with READ ONLY transaction (1)

## Remaining manual review

**None.** All 14 needs_manual_review / possible_indirect_write scripts have been reviewed
and reclassified with evidence. Zero scripts remain in `needs_manual_review` or
`possible_indirect_write` status.

The consolidated classification now aligns with reality: all write-capable scripts are
guarded, and all remaining classified-as-review scripts are verified non-write.

## Risks and unknowns

- **Reclassification is static-only.** Classifications are based on code reading, not
  runtime execution. Dynamic code paths (eval, dynamic require, runtime code generation)
  could theoretically bypass static detection.
- **Guard integrity not tested.** This review confirms guard presence in code, but does
  not verify that guards cannot be bypassed at runtime, or that env var checks are
  sufficient in all execution contexts.
- **Production-like host block still not tested.** The guard helper's production host
  detection has not been tested against actual production hostnames.
- **Python/SQL/migration enforcement not yet designed.** This review only covers
  `scripts/ops/**/*.js` files. Python scripts, SQL migration files, and migration
  runner scripts remain outside the current guard scope.

## Next recommended task

`python_sql_migration_enforcement_design_phase1` ✅ **COMPLETED.** Design document:
`docs/SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md`. Python and SQL/migration
files are now inventoried and classified. 14 confirmed Python write paths, 8 indirect,
5 manual review. 18 SQL files classified. Recommended enforcement: Hybrid model.
Next step: `python_sql_migration_enforcement_implementation_phase2A`.

**Note:** This manual_review_phase1 covers JS scripts only (`scripts/ops/**/*.js`).
Python / SQL / migration review remains a separate concern. See
`docs/SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md` for the Python/SQL layer.
Do not start automatically. Recommended next task only after user confirmation.

## SC-002 status impact

- **SC-002 remains partial mitigation only.**
- **0 needs_manual_review scripts remain** after this review.
- **0 possible_indirect_write scripts remain** after this review.
- **All 7 write-capable reviewed consumers are already guarded.**
- **All 3 read-only reviewed consumers verified no-write.**
- **All 2 SELECT-only verified via active wrappers.**
- **All 1 read-only transaction verified.**
- **No guard implemented in this phase** (all guards were already in place).
- **No target script executed.**
- **No DB connection.**
- **No real DB write.**
- **No scraper/browser/Playwright.**
- **No training/data expansion/schema migration.**
- Training, data expansion, real DB write remain BLOCKED.
