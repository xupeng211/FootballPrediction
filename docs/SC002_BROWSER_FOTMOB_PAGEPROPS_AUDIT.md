# SC-002 Browser / FotMob / PageProps Static Audit

- lifecycle: permanent
- owner: project governance
- created: 2026-06-22
- task: specialized_browser_fotmob_pageprops_audit_phase1

## Summary

This is a **static audit** of all 43 `skipped_complex` scripts identified by the DB write guard
static enforcement scanner (`scripts/ops/db_write_guard_static_enforcement_dry_run.js`).

**This audit does NOT:**
- Run any browser, Playwright, scraper, or network fetch
- Connect to any database
- Execute any script (DRY_RUN or otherwise)
- Modify any business code
- Change scanner logic, enforcement rules, or guard behavior

**This audit DOES:**
- Statically read and analyze all 43 skipped_complex scripts
- Identify imports (DB clients, browser/Playwright, network libraries)
- Detect SQL write literals, query execution patterns, and transaction boundaries
- Classify each script's actual DB write risk based on code evidence, not filename heuristics
- Provide concrete next-action recommendations per script and per category

**Key finding:** Of the 43 skipped_complex scripts, **20 are confirmed to have real DB write
capability** (DB client import + query execution + write SQL in code). These need guard
integration or specialized pipeline guard design — they are NOT safe just because they were
categorized.

**Progress:** 6 of 6 real confirmed write paths now guarded:
- Phase 1: `odds_sniper.js`, `fixture_harvester_l1.js` (browser+DB)
- Phase 2 batch 1: `pageprops_v2_single_target_controlled_write.js`, `remaining_seeded_pageprops_v2_controlled_write.js`, `single_league_pageprops_v2_controlled_write_execute.js` (controlled-write)
- Phase 2 batch 2: `fotmob_adg60_raw_json_db_storage_no_feature_parse.js` (FotMob raw JSON DB storage)
**sc002_allowlist_cleanup_phase1** (this PR): 15 scripts reclassified as false positives.
All original 20 "confirmed_write_path" classifications are now resolved (6 guarded, 14 reclassified).
0 still_needs_guard remain. SC-002 remains partial mitigation only.

## Scope

### In scope
- All 43 scripts classified as `skipped_complex` by the static scanner
- 22 scripts listed in `scripts/ops/helpers/db_write_guard_legacy_allowlist.json` (categories: pageprops_pipeline, fotmob_pipeline, shared_module, dry_run_or_audit)
- 21 additional scripts classified by the scanner as "browser/Playwright automation — needs manual review" (category: N/A)
- Static analysis: imports, SQL patterns, query execution, transaction handling, browser/fetch usage

### Out of scope
- Scripts already guarded (43 Phase1–Phase7 scripts) — these are not re-audited
- `scripts/ops/helpers/db_write_guard.js` (the guard itself)
- `scripts/ops/ai_workflow_gate.py` (enforcement logic)
- `scripts/ops/db_write_guard_static_enforcement_dry_run.js` (scanner itself)
- Python scripts, SQL migration files, non-JS files
- Runtime behavior verification, execution testing, network validation

## Methodology

Each of the 43 scripts was statically analyzed by reading the file content and checking for:

| Signal | Detection Pattern |
|---|---|
| DB client import | `require('pg')`, `require("pg")`, `from 'pg'` |
| Pool/Client instantiation | `new Pool`, `createPool`, `new Client` |
| Query execution | `.query(`, `.execute(` |
| Transaction handling | `BEGIN`, `COMMIT`, `ROLLBACK`, `transaction` |
| Write SQL in code (not comments) | `INSERT INTO`, `UPDATE <table>`, `DELETE FROM`, `TRUNCATE`, `DROP TABLE`, `CREATE TABLE`, `ALTER TABLE`, `GRANT`, `REVOKE`, `COPY` |
| Browser/Playwright | `playwright`, `Playwright`, `puppeteer`, `chromium`, `Chromium` |
| Network/fetch | `.fetch(`, `.get(`, `.post(`, `axios`, `got(`, `request(` |
| File output | `fs.writeFile`, `fs.createWriteStream` |
| CLI entrypoint | `process.argv`, `require.main === module` |
| Dry-run naming | `dry.run`, `no.write`, `read.only`, `audit`, `preview`, `preflight`, `plan.` |
| Guard mentions | `assertDbWriteAllowed`, `db_write_guard`, `ALLOW_DB_WRITE`, `dbWriteGuard` |
| Controlled write guard | `controlled.write`, `CONTROLLED_WRITE`, `ALLOW_CONTROLLED` |

SQL literals appearing only in block comments (`/* ... */`) or line comments (`// ...`) were
excluded from the `sql_appears_in_code` signal. SQL keywords in template strings, regular
strings, or variable names within executable code were counted.

### Classification Logic

Scripts were classified using a decision tree based on the detected signals:

1. **shared_module_no_execution** — helper files consumed by entrypoints; no standalone CLI
2. **read_only** — no DB client and no query execution; planning/preview/audit context
3. **no_db_connection** — no DB client, pool, or query execution whatsoever
4. **scraper_or_browser_only** — has Playwright/Chromium but no DB client
5. **possible_indirect_write** — has DB client but write SQL execution not directly confirmed
6. **confirmed_write_path_needs_guard** — DB client + query execution + write SQL in code
7. **needs_manual_review** — ambiguous signals requiring human review

## Candidate Inventory

Total: **43 scripts** (22 allowlisted + 21 scanner-flagged browser/Playwright)

Breakdown by scanner category:
| Category | Count | Source |
|---|---|---|
| pageprops_pipeline | 9 | allowlist |
| dry_run_or_audit | 8 | allowlist |
| shared_module | 3 | allowlist |
| fotmob_pipeline | 2 | allowlist |
| N/A (browser/Playwright) | 21 | scanner only (not allowlisted) |

Breakdown by **actual DB write capability** (this audit, updated by manual_review_phase1):
| Classification | Count |
|---|---|
| confirmed_write_path_needs_guard | 0 (all 20 resolved: 6 guarded, 14 reclassified false positive) |
| guarded (Phase1 + Phase2 batch1 + Phase2 batch2 + Phase1-7 + PRs) | 13 (6 original confirmed + 7 reclassified from needs_manual_review) |
| false_positive_select_only_with_active_wrapper | 13 (11 from allowlist_cleanup + 2 from manual_review) |
| false_positive_read_only_transaction | 3 (2 from allowlist_cleanup + 1 from manual_review) |
| false_positive_no_db_connection_static_scan | 1 |
| false_positive_policy_or_regex_keyword_only | 1 |
| false_positive_no_db_write_evidence | 3 (reclassified from needs_manual_review) |
| read_only | 12 |
| design_mapped (was shared_module_no_execution) | 3 |
| scraper_or_browser_only | 1 |
| needs_manual_review | **0** (all 4 + 1 possible_indirect_write reclassified by manual_review_phase1) |
| possible_indirect_write | **0** (reclassified to false_positive_read_only_transaction) |

## Findings by Category

### pageProps Pipeline (9 scripts)

Of 9 pageProps pipeline scripts:
- **0 are confirmed_write_path_needs_guard** after allowlist_cleanup_phase1 reclassification.
  The 3 originally classified as confirmed_write_path (`pageprops_v2_no_write_preview.js`,
  `pageprops_v2_raw_completeness_audit.js`, `single_league_small_batch_pageprops_v2_preflight.js`)
  have been reclassified as false_positive_select_only_with_active_wrapper: all use
  queryReadOnly() or safeSelect() wrappers that enforce SELECT-only at runtime.
- **4 are read_only**: `pageprops_v2_controlled_write_plan.js`,
  `pageprops_v2_recapture_runner_identity_input_contract_fix_plan.js`,
  `pageprops_v2_bounded_expanded_blocked_target_review_execute.js`,
  `single_league_small_batch_target_manifest_plan.js` — planning/manifest files with no DB
  client.
- **4 need_manual_review**: `all_seeded_pageprops_v2_canonical_read_verification.js`,
  `pageprops_v2_identity_contract_regression_execute.js`,
  `pageprops_v2_post_write_canonical_read_verification.js`,
  `pageprops_v2_suspended_target_review_execute.js` — have SQL keywords or `.query()` calls
  but no direct DB client import (may use helper modules or indirect execution).

**Key insight:** The initial audit misclassified 3 pageProps scripts as having real DB
write capability because their write SQL keywords appeared inside protection regexes and
policy description strings, not in executable SQL. Deep static analysis for
allowlist_cleanup_phase1 confirmed all 3 are SELECT-only with active wrappers.

### FotMob Pipeline (2 scripts)

- **1 is confirmed_write_path_needs_guard**: `fotmob_adg60_raw_json_db_storage_no_feature_parse.js`
  — imports `Pool` from `pg`, has write SQL (INSERT, UPDATE, UPSERT), and executes queries.
  This is a real DB write entrypoint for FotMob raw JSON storage.
- **1 is read_only**: `fotmob_ligue1_adg57_no_write_mutation_dry_run_preview.js` —
  despite the scanner detecting UPDATE keywords, our static analysis finds no DB client
  import and no query execution. The SQL keywords appear in comments/analysis context.
  The filename correctly indicates "no write mutation" and "dry run preview".

### Dry-Run / Audit (8 scripts)

Of 8 dry-run/audit scripts:
- **0 are confirmed_write_path_needs_guard** after allowlist_cleanup_phase1 reclassification.
  The 5 originally classified as confirmed_write_path have been reclassified:
  - `dataset_status_audit.js` → false_positive_select_only_with_active_wrapper (assertSafeSelect + safeSelect)
  - `formal_training_dataset_design_dry_run.js` → false_positive_read_only_transaction (BEGIN READ ONLY + assertSelectOnlySql)
  - `l3_local_dry_run.js` → false_positive_select_only_with_active_wrapper (assertSafeSelect + safeSelect)
  - `technical_debt_workflow_audit_dry_run.js` → false_positive_no_db_connection_static_scan (no pg import, fs/child_process only)
  - `training_dataset_leakage_dry_run.js` → false_positive_read_only_transaction (BEGIN READ ONLY + assertSelectOnlySql)
- **2 are read_only**: `authoritative_workflow_enforcement_dry_run.js`,
  `raw_match_data_versioned_schema_migration_preflight.js`
  — planning files with no DB client detected.
- **1 is possible_indirect_write**: `training_pipeline_smoke_dry_run.js` — has COPY
  keyword in code but execution path is unclear.

**Key insight:** The "dry_run" or "audit" label in filenames turned out to be a reliable
safety indicator for these scripts. The initial audit's classification of 5 dry-run/audit
scripts as confirmed_write_path was incorrect — the write SQL keywords were in protection
regexes (FORBIDDEN_SQL, FORBIDDEN_SQL_VERBS) and policy description strings, not in
executable SQL. The names DO match the actual capability.

### Shared Modules (3 scripts)

All 3 are now **design_mapped** by `shared_module_db_write_boundary_design_phase1` (PR pending).
Previously classified as `shared_module_no_execution`.

- `helpers/dbBlueprint.js` — DB schema/migration helper; imports `Pool` from `pg`.
  Exports both write-capable functions (`runColdStartBlueprintCheck`,
  `ensureBlueprintOnCurrentDatabase`, `runBlueprintWriteProbe`, `applyBlueprint`,
  `executeSqlFile`, `withTemporaryDatabase`) and read-only functions
  (`buildDbConnectionConfig`, `checkDbConnection`, `inspectCoreSchema`, etc.).
  **24 consumers mapped:** 3 write-capable (2 unguarded gatekeeper scripts, 1 guarded
  db_vault.js), 18 read-only only (use `buildDbConnectionConfig` only), 3 needs_manual_review.
- `helpers/restoreMappingsWorkflow.js` — restore mappings workflow helper.
  **0 active consumers** in the current codebase. Uses dependency injection for DB write
  (`repository.saveOddsPortalMapping`). Built-in `dryRun` support. No direct DB client.
- `odds_harvest_pipeline.shared.js` — shared odds harvest pipeline with SQL templates
  (UPSERT_MAPPING_SQL, UPSERT_ODDS_SQL). **2 consumers mapped:** `odds_sniper.js`
  (guarded, Phase 1 ✅) and `odds_harvest_pipeline.js` (✅ **now guarded by
  `shared_module_db_write_boundary_implementation_phase1`** — `assertDbWriteAllowed()`
  in `upsertMappingAndOdds()` before BEGIN).

**Key insight updated:** Shared modules should not independently guard themselves because
most consumers only use read-only functions and a module-level guard would break them.
The enforcement must be at the consumer entrypoint. The design phase confirmed this
approach and discovered 1 high-risk unguarded consumer (`odds_harvest_pipeline.js`)
that was missed by both Phase1-7 and the skipped_complex audit.

See `docs/SC002_SHARED_MODULE_DB_WRITE_BOUNDARY_DESIGN.md` for full consumer map
and guard boundary recommendations.

### Browser/Playwright (scanner N/A, 21 scripts)

These 21 scripts were NOT in the allowlist and were classified by the scanner as
"browser/Playwright automation — needs manual review". Our static analysis reveals:

- **5 are guarded** (previously confirmed_write_path, now resolved):
  - `fixture_harvester_l1.js` — Playwright + Pool + INSERT INTO matches → guarded_in_phase1 ✅
  - `odds_sniper.js` — Playwright + Pool + UPSERT_ODDS_SQL → guarded_in_phase1 ✅
  - `pageprops_v2_single_target_controlled_write.js` → guarded_in_phase2_batch1 ✅
  - `single_league_pageprops_v2_controlled_write_execute.js` → guarded_in_phase2_batch1 ✅
  - `remaining_seeded_pageprops_v2_controlled_write.js` → guarded_in_phase2_batch1 ✅

- **6 are false_positive_select_only_with_active_wrapper** (reclassified in allowlist_cleanup_phase1):
  - `controlled_matches_identity_seed_prerequisite_plan.js` — queryReadOnly() wrapper
  - `html_hydration_source_fidelity_live_compare.js` — queryReadOnly() wrapper
  - `l2_raw_match_data_ingest_preflight.js` — assertSafeSelect() + safeSelect()
  - `pageprops_v2_no_write_preview.js` — queryReadOnly() wrapper
  - `pageprops_v2_single_target_write_preflight.js` — queryReadOnly() wrapper
  - `post_seed_matches_identity_raw_write_readiness_audit.js` — queryReadOnly() wrapper
  - `remaining_seeded_pageprops_v2_acquisition_preflight.js` — queryReadOnly() wrapper
  - `single_league_pageprops_v2_controlled_write_plan.js` — false_positive_policy_or_regex_keyword_only
  - `single_league_small_batch_pageprops_v2_preflight.js` — queryReadOnly() wrapper

- **6 are read_only**: Planning files (`l2_raw_match_data_ingest_plan.js`,
  `l1_matches_seed_commit_plan.js`, `large_scale_pageprops_v2_acquisition_strategy_plan.js`,
  `pageprops_v2_no_write_payload_recapture_plan.js`,
  `pageprops_v2_raw_write_input_source_investigation.js`,
  `fotmob_ligue1_corrected_source_discovery_adg21.js`) — no DB client detected.

- **1 is scraper_or_browser_only**: `fotmob_ligue1_adg60_raw_payload_source_inventory.js`
  — browser/FotMob script with no DB client.

**Key insight:** Of the 21 browser/Playwright scripts, only 5 had real DB write
capability — all 5 are now guarded. The remaining 9 that the initial audit classified
as confirmed_write_path have been reclassified as false positives (SELECT-only with
active wrappers, or policy/regex keyword only).

## Per-Script Findings

### Category: pageprops_pipeline (9)

| # | Path | has_db_import | has_execute | sql_in_code | has_browser | Recommended Classification | Evidence |
|---|---|---|---|---|---|---|---|
| 1 | scripts/ops/all_seeded_pageprops_v2_canonical_read_verification.js | No | Yes | Yes | No | ~~needs_manual_review~~ → **false_positive_select_only_with_active_wrapper** | Uses `config/database.js`.getPool() for DB access. Has `assertSelectOnly()` function (line 435) that blocks INSERT/UPDATE/DELETE/TRUNCATE/ALTER/DROP/CREATE/MERGE/COPY/BEGIN/COMMIT/ROLLBACK. All queries are SELECT-only through this wrapper. Reclassified in manual_review_phase1. |
| 2 | scripts/ops/pageprops_v2_bounded_expanded_blocked_target_review_execute.js | No | No | No | No | read_only | No DB client, no query execution — review/audit context |
| 3 | scripts/ops/pageprops_v2_controlled_write_plan.js | No | No | No | No | read_only | Planning document — no DB client or execution |
| 4 | scripts/ops/pageprops_v2_identity_contract_regression_execute.js | No | No | No | No | ~~needs_manual_review~~ → **false_positive_no_db_write_evidence** | Zero database code confirmed — no pg, no Pool, no dbBlueprint, no query execution. Pure file I/O (manifest JSON + markdown reports). Imports `pageprops_v2_no_write_payload_recapture_execute.js` (also no DB). Uses `FotMobRouteIdentityReconciler` for route identity only. Reclassified in manual_review_phase1. |
| 5 | scripts/ops/pageprops_v2_post_write_canonical_read_verification.js | No | Yes | Yes | No | ~~needs_manual_review~~ → **false_positive_select_only_with_active_wrapper** | Uses `config/database.js`.getPool() for DB access. Has `assertSelectOnly()` function (line 258) that blocks INSERT/UPDATE/DELETE/TRUNCATE/ALTER/DROP/CREATE/MERGE/COPY/BEGIN/COMMIT/ROLLBACK. All queries are SELECT-only through this wrapper. Reclassified in manual_review_phase1. |
| 6 | scripts/ops/pageprops_v2_raw_completeness_audit.js | Yes | Yes | Yes | No | ~~confirmed_write_path_needs_guard~~ → **false_positive_select_only_with_active_wrapper** | Imports Pool from pg but assertSelectOnly() blocks INSERT/UPDATE/DELETE/TRUNCATE/ALTER/DROP/CREATE/GRANT/REVOKE/COPY/FOR UPDATE/BEGIN/COMMIT/ROLLBACK. All queries use safeSelect(). Write keywords in audit detected from protection regex, not executable SQL. Reclassified in allowlist_cleanup_phase1 |
| 7 | scripts/ops/pageprops_v2_recapture_runner_identity_input_contract_fix_plan.js | No | No | No | No | read_only | Planning document — no DB client or execution |
| 8 | scripts/ops/pageprops_v2_suspended_target_review_execute.js | No | No | No | No | ~~needs_manual_review~~ → **false_positive_no_db_write_evidence** | Zero database code confirmed — no pg, no Pool, no dbBlueprint, no query execution. Pure file I/O (manifest + reports). Completely DB-independent. Reclassified in manual_review_phase1. |
| 9 | scripts/ops/single_league_small_batch_target_manifest_plan.js | No | No | No | No | read_only | Manifest/planning — no DB client or execution |

### Category: fotmob_pipeline (2)

| # | Path | has_db_import | has_execute | sql_in_code | has_browser | Recommended Classification | Evidence |
|---|---|---|---|---|---|---|---|
| 10 | scripts/ops/fotmob_adg60_raw_json_db_storage_no_feature_parse.js | Yes | Yes | Yes | No | ~~confirmed_write_path_needs_guard~~ → **guarded_in_phase2_batch2** ✅ | Imports Pool from pg, INSERT INTO fotmob_raw_match_payloads with ON CONFLICT DO UPDATE — GUARDED: now calls assertDbWriteAllowed() before INSERT query |
| 11 | scripts/ops/fotmob_ligue1_adg57_no_write_mutation_dry_run_preview.js | No | No | No | No | read_only | No DB client, no execution — "no write mutation" in filename is accurate per static analysis |

### Category: shared_module (3)

| # | Path | has_db_import | has_execute | sql_in_code | has_browser | Recommended Classification | Evidence |
|---|---|---|---|---|---|---|---|
| 12 | scripts/ops/helpers/dbBlueprint.js | Yes | Yes | Yes | No | ~~shared_module_no_execution~~ → **design_mapped** → **consumers_guarded** | DB schema/migration helper with write-capable functions (runColdStartBlueprintCheck, ensureBlueprintOnCurrentDatabase, runBlueprintWriteProbe). 24 consumers mapped: 2 now guarded (gatekeeper.js/sh by `gatekeeper_boundary_implementation` ✅), 1 guarded (db_vault.js ✅), 18 read-only only, 3 needs_manual_review. Design phase complete — 2 of 3 active write-capable consumers now guarded (gatekeeper.js, gatekeeper.sh). Remaining: 3 needs_manual_review consumers. |
| 13 | scripts/ops/helpers/restoreMappingsWorkflow.js | No | Yes | No | No | ~~shared_module_no_execution~~ → **design_mapped** | Restore mappings helper with dependency-injected write path. 0 active consumers. Built-in dryRun support. Design phase complete — guard at consumer entrypoint when first consumer written. |
| 14 | scripts/ops/odds_harvest_pipeline.shared.js | No | Yes | Yes | No | ~~shared_module_no_execution~~ → **design_mapped** → **consumer_guarded** | Shared odds harvest pipeline with write SQL templates. 2 consumers: odds_sniper.js (guarded ✅) and odds_harvest_pipeline.js (✅ now guarded by implementation_phase1 — `assertDbWriteAllowed()` in `upsertMappingAndOdds()`). Design + implementation complete for this module. |

### Category: dry_run_or_audit (8)

| # | Path | has_db_import | has_execute | sql_in_code | has_browser | Recommended Classification | Evidence |
|---|---|---|---|---|---|---|---|
| 15 | scripts/ops/authoritative_workflow_enforcement_dry_run.js | No | No | No | No | read_only | No DB client, no execution — audit tool |
| 16 | scripts/ops/dataset_status_audit.js | Yes | Yes | Yes | No | ~~confirmed_write_path_needs_guard~~ → **false_positive_select_only_with_active_wrapper** | Imports Pool from pg but assertSafeSelect() + FORBIDDEN_SQL regex blocks all write verbs. All 5 query functions use safeSelect(). Write keywords in audit from FORBIDDEN_SQL protection regex, not executable SQL. Reclassified in allowlist_cleanup_phase1 |
| 17 | scripts/ops/formal_training_dataset_design_dry_run.js | Yes | Yes | Yes | No | ~~confirmed_write_path_needs_guard~~ → **false_positive_read_only_transaction** | Imports Pool from pg but uses BEGIN READ ONLY + ROLLBACK + assertSelectOnlySql() allowing only SELECT/WITH. All queries go through querySelectOnly(). Reclassified in allowlist_cleanup_phase1 |
| 18 | scripts/ops/l3_local_dry_run.js | Yes | Yes | Yes | No | ~~confirmed_write_path_needs_guard~~ → **false_positive_select_only_with_active_wrapper** | Imports Pool from pg but assertSafeSelect() + FORBIDDEN_SQL regex blocks all write verbs. Both queries use safeSelect(). Reclassified in allowlist_cleanup_phase1 |
| 19 | scripts/ops/raw_match_data_versioned_schema_migration_preflight.js | No | No | No | No | read_only | Preflight/planning — no DB client detected; execute counterpart is already guarded (Phase4) |
| 20 | scripts/ops/technical_debt_workflow_audit_dry_run.js | No | No | No | No | ~~confirmed_write_path_needs_guard~~ → **false_positive_no_db_connection_static_scan** | No pg import, no Pool, no DB connection. Uses fs.readFileSync/readdirSync + child_process.execSync for static file scanning. The INSERT/UPDATE/DELETE keywords detected by the audit are from scanDbWriteScripts() regex PATTERNS used to scan OTHER files — these are not executable SQL. Reclassified in allowlist_cleanup_phase1 |
| 21 | scripts/ops/training_dataset_leakage_dry_run.js | Yes | Yes | Yes | No | ~~confirmed_write_path_needs_guard~~ → **false_positive_read_only_transaction** | Imports Pool from pg but uses BEGIN READ ONLY + ROLLBACK + assertSelectOnlySql() allowing only SELECT/WITH/BEGIN READ ONLY/ROLLBACK. All queries go through querySelectOnly(). Reclassified in allowlist_cleanup_phase1 |
| 22 | scripts/ops/training_pipeline_smoke_dry_run.js | No | Yes | No | No | ~~possible_indirect_write~~ → **false_positive_read_only_transaction** | Uses BEGIN READ ONLY + ROLLBACK + assertSelectOnlySql() (allowing only SELECT/WITH/BEGIN READ ONLY/ROLLBACK). Explicit `actual_update_executed: false` markers at lines 465, 583. Local `buildDbConfig()` instead of dbBlueprint. No actual DB writes. Reclassified in manual_review_phase1. |

### Category: N/A (browser/Playwright scanner flagged, 21)

| # | Path | has_db_import | has_execute | sql_in_code | has_browser | Recommended Classification | Evidence |
|---|---|---|---|---|---|---|---|
| 23 | scripts/ops/controlled_matches_identity_seed_prerequisite_plan.js | Yes | Yes | Yes | No | ~~confirmed_write_path_needs_guard~~ → **false_positive_select_only_with_active_wrapper** | Imports Pool from pg but queryReadOnly() blocks INSERT/UPDATE/DELETE/TRUNCATE/ALTER/DROP/CREATE/LOCK/COPY/GRANT/REVOKE/MERGE + FOR UPDATE/SHARE/NO KEY UPDATE/KEY SHARE. All 5 DB-accessing functions use queryReadOnly(). The INSERT/UPDATE keywords appear only in planning metadata (FUTURE_INSERT_COLUMNS, insert_missing_matches_identity_row_in_l2v1) describing what a future phase would do — not executable SQL. Reclassified in allowlist_cleanup_phase1 |
| 24 | scripts/ops/fixture_harvester_l1.js | Yes | Yes | Yes | Yes | ~~confirmed_write_path_needs_guard~~ → **guarded_in_phase1** ✅ | Playwright + Pool + BEGIN/COMMIT/ROLLBACK + INSERT INTO matches — GUARDED: now calls assertDbWriteAllowed() in persistFixtures() before DB write |
| 25 | scripts/ops/fotmob_ligue1_adg60_raw_payload_source_inventory.js | No | No | No | Yes | scraper_or_browser_only | Playwright/browser script — no DB client detected |
| 26 | scripts/ops/fotmob_ligue1_corrected_source_discovery_adg21.js | No | No | No | No | read_only | No DB client, no browser import, no query execution — planning/investigation |
| 27 | scripts/ops/html_hydration_source_fidelity_live_compare.js | Yes | Yes | Yes | No | ~~confirmed_write_path_needs_guard~~ → **false_positive_select_only_with_active_wrapper** | Imports Pool from pg but queryReadOnly() enforces SELECT-only: blocks non-SELECT SQL + INSERT/UPDATE/DELETE/TRUNCATE/ALTER/DROP/CREATE/GRANT/REVOKE/COPY/FOR UPDATE. Only query is a SELECT from raw_match_data. Also makes live HTTP fetch to FotMob for comparison (read-only). Reclassified in allowlist_cleanup_phase1 |
| 28 | scripts/ops/l1_matches_seed_commit_plan.js | No | No | No | No | read_only | Planning document — no DB client or execution |
| 29 | scripts/ops/l2_raw_match_data_ingest_plan.js | No | No | No | No | read_only | Planning document — references "future controlled write script" |
| 30 | scripts/ops/l2_raw_match_data_ingest_preflight.js | Yes | Yes | Yes | No | ~~confirmed_write_path_needs_guard~~ → **false_positive_select_only_with_active_wrapper** | Imports Pool from pg but assertSafeSelect() + FORBIDDEN_SQL_VERBS (18 verbs: INSERT/UPDATE/DELETE/CREATE/ALTER/DROP/TRUNCATE/UPSERT/MERGE/GRANT/REVOKE/BEGIN/COMMIT/ROLLBACK/LOCK/COPY). All 3 DB queries use safeSelect(). Also makes live HTTP fetch to FotMob. Reclassified in allowlist_cleanup_phase1 |
| 31 | scripts/ops/large_scale_pageprops_v2_acquisition_strategy_plan.js | No | No | No | No | read_only | Strategy/planning document — no DB client |
| 32 | scripts/ops/odds_sniper.js | Yes | Yes | Yes | Yes | ~~confirmed_write_path_needs_guard~~ → **guarded_in_phase1** ✅ | Playwright + Pool + UPSERT_ODDS_SQL from shared module — GUARDED: now calls assertDbWriteAllowed() in upsertMappingAndOdds() and runTargetedStitch() before DB write |
| 33 | scripts/ops/pageprops_v2_no_write_payload_recapture_plan.js | No | No | No | No | read_only | Planning document — references controlled write helper, no direct DB |
| 34 | scripts/ops/pageprops_v2_no_write_preview.js | Yes | Yes | Yes | No | ~~confirmed_write_path_needs_guard~~ → **false_positive_select_only_with_active_wrapper** | Imports Pool from pg but queryReadOnly() enforces SELECT-only with write/lock keyword blocking. Only query is a SELECT from raw_match_data for comparison against live fetch. "no_write_preview" in filename is accurate — preview only, db_write_executed: false. Reclassified in allowlist_cleanup_phase1 |
| 35 | scripts/ops/pageprops_v2_raw_write_input_source_investigation.js | No | No | Yes | No | read_only | Investigation document — SQL keywords in analysis context, no DB client |
| 36 | scripts/ops/pageprops_v2_single_target_controlled_write.js | Yes | Yes | Yes | No | ~~confirmed_write_path_needs_guard~~ → **guarded_in_phase2_batch1** ✅ | Imports Pool from pg, INSERT INTO raw_match_data — GUARDED: guard added before BEGIN transaction |
| 37 | scripts/ops/pageprops_v2_single_target_write_preflight.js | Yes | Yes | Yes | No | ~~confirmed_write_path_needs_guard~~ → **false_positive_select_only_with_active_wrapper** | Imports from pageprops_v2_no_write_preview, defines own queryReadOnly() wrapper. All 3 DB queries (loadTargetMatchMetadata, loadExistingRawVersions, loadProtectedTableBaseline) are SELECT-only through queryReadOnly(). Preflight only, db_write_executed: false. Reclassified in allowlist_cleanup_phase1 |
| 38 | scripts/ops/post_seed_matches_identity_raw_write_readiness_audit.js | Yes | Yes | Yes | No | ~~confirmed_write_path_needs_guard~~ → **false_positive_select_only_with_active_wrapper** | Imports Pool from pg but queryReadOnly() blocks INSERT/UPDATE/DELETE/TRUNCATE/ALTER/DROP/CREATE/LOCK/COPY/GRANT/REVOKE/MERGE + FOR UPDATE/SHARE locks. All 4 DB queries are SELECT-only through queryReadOnly(). Embedded report explicitly states "It does not write DB." Reclassified in allowlist_cleanup_phase1 |
| 39 | scripts/ops/remaining_seeded_pageprops_v2_acquisition_preflight.js | Yes | Yes | Yes | No | ~~confirmed_write_path_needs_guard~~ → **false_positive_select_only_with_active_wrapper** | Imports from pageprops_v2_no_write_preview, defines own queryReadOnly() wrapper. All 4 DB queries (loadTargetMatchMetadata, loadExistingRawVersions, loadProtectedTableBaselineRows, loadSchemaConstraints) are SELECT-only. Preflight only, db_write_executed: false. Reclassified in allowlist_cleanup_phase1 |
| 40 | scripts/ops/remaining_seeded_pageprops_v2_controlled_write.js | Yes | Yes | Yes | No | ~~confirmed_write_path_needs_guard~~ → **guarded_in_phase2_batch1** ✅ | Imports Pool from pg, INSERT INTO raw_match_data — GUARDED: guard added before BEGIN transaction |
| 41 | scripts/ops/single_league_pageprops_v2_controlled_write_execute.js | Yes | Yes | Yes | No | ~~confirmed_write_path_needs_guard~~ → **guarded_in_phase2_batch1** ✅ | Imports Pool from pg, INSERT INTO raw_match_data — GUARDED: guard added before BEGIN transaction |
| 42 | scripts/ops/single_league_pageprops_v2_controlled_write_plan.js | Yes | Yes | Yes | No | ~~confirmed_write_path_needs_guard~~ → **false_positive_policy_or_regex_keyword_only** | Imports Pool from pg but queryReadOnly() blocks write SQL. The only INSERT mention is in a conflict_policy description string ("INSERT ... ON CONFLICT (match_id, data_version) DO NOTHING with post-write verification") — not executable SQL. Planning only, db_write_executed: false. Reclassified in allowlist_cleanup_phase1 |
| 43 | scripts/ops/single_league_small_batch_pageprops_v2_preflight.js | Yes | Yes | Yes | No | ~~confirmed_write_path_needs_guard~~ → **false_positive_select_only_with_active_wrapper** | Imports Pool from pg but queryReadOnly() enforces SELECT-only. All DB queries (loadProtectedTableBaselineRows, loadExistingRawVersions) are SELECT-only through queryReadOnly(). Preflight only, db_write_executed: false. Reclassified in allowlist_cleanup_phase1 |

## Risk Summary

### Confirmed DB Write Paths (0 remaining unguarded)

All 20 originally identified confirmed write paths are now resolved:
- **6 guarded** (Phase1, Phase2 batch1, Phase2 batch2)
- **14 reclassified as false positives** (allowlist_cleanup_phase1)

This means there are **0 remaining confirmed_write_path_needs_guard** scripts.
SC-002 remains partial mitigation only (4 needs_manual_review, 3 shared_module,
1 possible_indirect_write, and Python/SQL/migration enforcement still not designed).

### Read-Only / No DB (14 scripts)

These 14 scripts have **no detected DB client** and are likely safe from DB write risk:
- 12 read_only: planning, manifest, investigation, preview files
- 2 no_db_connection: no DB-related signals at all

**However**, "no DB client detected" is a static signal, not a runtime guarantee. Some of
these scripts import helper modules (`pageprops_v2_no_write_preview.js` is imported by
controlled write scripts) that may provide DB access indirectly.

### Shared Modules (3 scripts — 3 consumers guarded across 2 implementation phases)

Boundary design complete. All 3 active write-capable consumers of shared modules now guarded:
- `odds_harvest_pipeline.js` (HIGH priority) guarded by `shared_module_db_write_boundary_implementation_phase1`
  — `assertDbWriteAllowed()` in `upsertMappingAndOdds()` before BEGIN transaction.
- `gatekeeper.js` and `gatekeeper.sh` (MEDIUM priority) guarded by `gatekeeper_boundary_implementation`
  — `assertDbWriteAllowed()` before `runColdStartBlueprintCheck` (CREATE DATABASE, DROP DATABASE, INSERT write probe).
- **0 needs_manual_review consumers remain.** All 9 dbBlueprint consumers reviewed and reclassified by `manual_review_phase1` (7 already_guarded + 2 no_write_evidence).
- `db_vault.js` was already guarded in Phase1.
See `docs/SC002_SHARED_MODULE_DB_WRITE_BOUNDARY_DESIGN.md` and `docs/SC002_MANUAL_REVIEW_PHASE1.md` for full consumer map and per-script evidence.

### Needs Manual Review (0 scripts — RESOLVED)

All 4 `needs_manual_review` scripts and 1 `possible_indirect_write` script have been
reviewed and reclassified by `manual_review_phase1`:
- 2 reclassified to **false_positive_select_only_with_active_wrapper**: `all_seeded_pageprops_v2_canonical_read_verification.js`, `pageprops_v2_post_write_canonical_read_verification.js` — SELECT-only with `assertSelectOnly()` wrapper
- 2 reclassified to **false_positive_no_db_write_evidence**: `pageprops_v2_identity_contract_regression_execute.js`, `pageprops_v2_suspended_target_review_execute.js` — zero DB connection code, pure file I/O
- 1 reclassified to **false_positive_read_only_transaction**: `training_pipeline_smoke_dry_run.js` — BEGIN READ ONLY + ROLLBACK + assertSelectOnlySql()

All 9 needs_manual_review shared-module consumers also reviewed and reclassified (7 already_guarded + 2 no_write_evidence). See `docs/SC002_MANUAL_REVIEW_PHASE1.md` for full evidence.

### Guarded in Phase 1 (2 scripts — was confirmed_write_path)

- `odds_sniper.js` ✅ — guarded in `upsertMappingAndOdds()` and `runTargetedStitch()`
- `fixture_harvester_l1.js` ✅ — guarded in `persistFixtures()`

### Scraper/Browser Only (1 script)

- `fotmob_ligue1_adg60_raw_payload_source_inventory.js` — browser script with no DB client.

### Possible Indirect Write (1 script)

- `training_pipeline_smoke_dry_run.js` — has COPY keyword and `.query()` execution but
  no direct DB client import.

## Recommended Next Actions

### Immediate (can proceed with authorization)

1. **confirmed_write_path_guard_phase** — Integrate `assertDbWriteAllowed()` into the
   20 confirmed-write-path scripts. Priority order:
   - High-risk browser+DB scripts first: `odds_sniper.js`, `fixture_harvester_l1.js`
   - Controlled-write scripts: standardize to use `assertDbWriteAllowed()` alongside
     their existing controlled-write guards
   - Misleading-name scripts: add guard and update documentation to reflect actual capability

2. **shared_module_boundary_design_phase1** — Design boundary enforcement for the 3 shared
   modules. Map every consumer entrypoint and verify each is guarded.

3. **sc002_allowlist_cleanup_phase1** — Update the legacy allowlist to reflect the findings
   of this audit. Move 14 read_only/no_db_connection scripts to a verified-read-only list.
   Keep the 20 confirmed_write_path scripts categorized as needing guard.

### Follow-up (after guard integration)

4. **scraper_browser_execution_policy_phase1** — Define a policy for when and how browser
   automation scripts (`fixture_harvester_l1.js`, `odds_sniper.js`,
   `fotmob_ligue1_adg60_raw_payload_source_inventory.js`) may execute. These scripts
   have risks beyond DB write (network access, session management, captcha, proxy rotation).

5. **manual_review_phase1** — Manually review the 4 `needs_manual_review` scripts by
   tracing their full execution path through helper modules. Determine whether they
   actually execute DB writes or are truly read-only.

6. **sc002_release_gate_checklist_phase1** — Create detailed per-gate verification
   checklists incorporating this audit's findings.

## SC-002 Impact

- **SC-002 remains partial mitigation only.** This audit is evidence input, not a fix.
- **This audit does NOT close SC-002.**
- **This audit does NOT unlock training.**
- **This audit does NOT unlock data expansion.**
- **This audit does NOT unlock real DB write.**
- **43/66 scripts are guarded. All 20 originally identified confirmed write paths are now resolved:**
  - **6 guarded** (Phase1: 2, Phase2 batch1: 3, Phase2 batch2: 1)
  - **14 reclassified as false positives** (allowlist_cleanup_phase1)
  - **0 still_needs_guard remain**
- **The gap is now more precisely characterized: 4 needs_manual_review + 1 possible_indirect_write + 3 shared_module = 8 scripts needing further action.**
- **Reclassification categories:**
  - **false_positive_select_only_with_active_wrapper: 11 scripts** — SELECT-only queries through active SQL enforcement wrappers (queryReadOnly, safeSelect, assertSafeSelect, assertSelectOnly)
  - **false_positive_read_only_transaction: 2 scripts** — BEGIN READ ONLY + ROLLBACK + assertSelectOnlySql
  - **false_positive_no_db_connection_static_scan: 1 script** — no pg import, no DB connection
  - **false_positive_policy_or_regex_keyword_only: 1 script** — write keywords only in policy description strings

## Non-Goals

This task (`specialized_browser_fotmob_pageprops_audit_phase1`) is a **static audit and
documentation governance task only**. It explicitly is NOT:

- Running any browser, Playwright, scraper, or network fetch
- Connecting to any database
- Executing any script (DRY_RUN or otherwise)
- Modifying any business code, scripts/ops entrypoints, or shared modules
- Changing scanner logic, enforcement rules, or the guard helper
- Enabling new hard fails or continuing Phase8
- Training, data expansion, or real DB write
- Fixing or guarding any of the audited scripts (reserved for follow-up phases)
- Claiming SC-002 is fully fixed or any blocked activity is now safe

## Allowlist Cleanup Phase 1 (sc002_allowlist_cleanup_phase1)

Completed 2026-06-23. This section documents the formal reclassification of 15 scripts
from `confirmed_write_path_needs_guard` to verified false positive categories.

### Reclassification Summary

| Category | Count | Scripts |
|---|---|---|
| false_positive_select_only_with_active_wrapper | 11 | dataset_status_audit.js, l3_local_dry_run.js, controlled_matches_identity_seed_prerequisite_plan.js, html_hydration_source_fidelity_live_compare.js, l2_raw_match_data_ingest_preflight.js, pageprops_v2_no_write_preview.js, pageprops_v2_raw_completeness_audit.js, pageprops_v2_single_target_write_preflight.js, post_seed_matches_identity_raw_write_readiness_audit.js, remaining_seeded_pageprops_v2_acquisition_preflight.js, single_league_small_batch_pageprops_v2_preflight.js |
| false_positive_read_only_transaction | 2 | training_dataset_leakage_dry_run.js, formal_training_dataset_design_dry_run.js |
| false_positive_no_db_connection_static_scan | 1 | technical_debt_workflow_audit_dry_run.js |
| false_positive_policy_or_regex_keyword_only | 1 | single_league_pageprops_v2_controlled_write_plan.js |

### Evidence per Script

All 15 reclassifications are based on deep static analysis with evidence:

1. **SELECT-only with active wrapper (11 scripts):** Each imports `pg.Pool` but every DB
   query passes through an active wrapper function (`queryReadOnly`, `safeSelect`,
   `assertSafeSelect`, `assertSelectOnly`) that throws on any non-SELECT SQL, write
   keywords, or lock clauses. Write SQL keywords (INSERT, UPDATE, DELETE, TRUNCATE, etc.)
   appear only in the protection regexes — never in executable SQL strings.

2. **READ ONLY transaction (2 scripts):** Use `BEGIN READ ONLY` + `ROLLBACK` +
   `assertSelectOnlySql()` guard that explicitly permits only SELECT, WITH, BEGIN READ
   ONLY, and ROLLBACK statements.

3. **No DB connection static scan (1 script):** No `require('pg')`, no `Pool`, no DB
   connection. Uses `fs` and `child_process.execSync` for git/file-system operations.
   Write keywords detected by the audit are from `scanDbWriteScripts()` regex PATTERNS
   used to scan OTHER files.

4. **Policy/regex keyword only (1 script):** Has `queryReadOnly()` wrapper. INSERT
   keyword appears only in a `conflict_policy` description string ("INSERT ... ON
   CONFLICT (match_id, data_version) DO NOTHING with post-write verification") — not
   in executable SQL.

### Still Needs Guard

**0 scripts** remain as confirmed_write_path_needs_guard after this cleanup.

### Still Needs Manual Review

**4 scripts** remain needs_manual_review (unchanged by this cleanup):
- `all_seeded_pageprops_v2_canonical_read_verification.js`
- `pageprops_v2_identity_contract_regression_execute.js`
- `pageprops_v2_post_write_canonical_read_verification.js`
- `pageprops_v2_suspended_target_review_execute.js`

### Non-Goals of This Cleanup

- This cleanup does NOT guard any scripts (that was Phase1/Phase2).
- This cleanup does NOT close SC-002.
- This cleanup does NOT unlock training, data expansion, or real DB write.
- This cleanup does NOT review the 4 needs_manual_review scripts.
- This cleanup does NOT address shared_module boundary enforcement.
- This cleanup does NOT address Python/SQL/migration enforcement.
