# SC-002 Shared Module DB Write Boundary Design

- lifecycle: permanent
- owner: project governance
- created: 2026-06-23
- task: shared_module_db_write_boundary_design_phase1

## Summary

This is a **static design document only**. It maps the DB write boundary for 3 shared modules
identified by the SC-002 static scanner and the `sc002_allowlist_cleanup_phase1`. It analyzes
whether each shared module directly writes to the DB, maps every consumer entrypoint, and
recommends where guard enforcement should live — in the shared module, at the consumer
entrypoint, or both.

**This document does NOT:**
- Modify shared module behavior
- Add any guard to shared modules
- Implement guard at any consumer entrypoint
- Run any target script
- Connect to any database
- Execute any real DB write
- Train, expand data, or run browser/scraper automation
- Claim SC-002 is fully fixed

**This document DOES:**
- Statically analyze 3 shared modules and all their consumers
- Map the full consumer entrypoint landscape
- Recommend the correct guard boundary for each module-consumer relationship
- Identify coverage gaps (unguarded consumers, missed entrypoints)
- Specify the minimal safe implementation plan for a future phase

## Scope

### In scope

- 3 shared modules from the legacy allowlist `shared_module` category:
  - `scripts/ops/helpers/dbBlueprint.js`
  - `scripts/ops/helpers/restoreMappingsWorkflow.js`
  - `scripts/ops/odds_harvest_pipeline.shared.js`
- All consumer entrypoints that import/require these shared modules
- Static analysis: imports, exports, DB client usage, write SQL, guard calls
- Guard boundary recommendation per module-consumer pair

### Out of scope

- Scripts already guarded (43 Phase1–Phase7 scripts) — re-verified for consumer status only
- `scripts/ops/helpers/db_write_guard.js` (the guard itself)
- The 4 `needs_manual_review` scripts from the audit
- The 1 `possible_indirect_write` script
- Python / SQL / migration enforcement
- Implementation of any guard
- Runtime behavior change of any kind

## Shared Modules Reviewed

| # | Module | Path | Classification |
|---|---|---|---|
| 1 | dbBlueprint.js | `scripts/ops/helpers/dbBlueprint.js` | shared_module_direct_write_boundary_needed |
| 2 | restoreMappingsWorkflow.js | `scripts/ops/helpers/restoreMappingsWorkflow.js` | shared_module_indirect_write_boundary_needed |
| 3 | odds_harvest_pipeline.shared.js | `scripts/ops/odds_harvest_pipeline.shared.js` | shared_module_indirect_write_boundary_needed |

## Per-Module Findings

### 1. dbBlueprint.js

**Path:** `scripts/ops/helpers/dbBlueprint.js`

#### Signal Analysis

| Signal | Value |
|---|---|
| DB client import | Yes — `const { Pool } = require('pg')` |
| Direct Pool/Client creation | Yes — `new Pool(...)` inside `withTemporaryDatabase` and `ensureBlueprintOnCurrentDatabase` |
| Executable query calls | Yes — `client.query(sql)` in `executeSqlFile`, `runBlueprintWriteProbe`, `inspectCoreSchema`, `assertCoreSchema`, `withTemporaryDatabase`, `ensureBlueprintOnCurrentDatabase` |
| Write SQL in code (real, not comment) | Yes — INSERT INTO matches, INSERT INTO raw_match_data, INSERT INTO matches_oddsportal_mapping (all inside `runBlueprintWriteProbe`, wrapped in BEGIN/ROLLBACK) |
| Write SQL in code (DDL) | Yes — CREATE DATABASE, DROP DATABASE inside `withTemporaryDatabase` |
| Read-only wrappers | Yes — `inspectCoreSchema`, `assertCoreSchema` are SELECT-only |
| Write helper export | Yes — `runColdStartBlueprintCheck`, `ensureBlueprintOnCurrentDatabase`, `runBlueprintWriteProbe`, `applyBlueprint`, `executeSqlFile`, `withTemporaryDatabase` |
| Read-only helper export | Yes — `buildDbConnectionConfig`, `checkDbConnection`, `inspectCoreSchema`, `assertCoreSchema`, `readExecutableSql`, `resolveBlueprintSqlFiles`, `resolveMigrationSqlFiles`, `createBlueprintCheckDatabaseName` |

#### Exported Write-Capable Functions

| Function | What it does | Write risk |
|---|---|---|
| `runColdStartBlueprintCheck` | Creates temp DB → applies SQL blueprint → runs write probe (INSERT+ROLLBACK) → drops temp DB | HIGH — CREATE DATABASE, DROP DATABASE, INSERT via write probe |
| `ensureBlueprintOnCurrentDatabase` | Applies SQL migration files to current DB, optionally runs write probe | HIGH — SQL migration execution, optional INSERT |
| `runBlueprintWriteProbe` | INSERT into matches, raw_match_data, matches_oddsportal_mapping, all wrapped in ROLLBACK | MEDIUM — real INSERT executed but ROLLBACK prevents persistence |
| `applyBlueprint` | Iterates over SQL files and executes each via `executeSqlFile` | HIGH — executes arbitrary SQL from files |
| `executeSqlFile` | Reads SQL from file and executes via `client.query(sql)` | HIGH — executes arbitrary SQL |
| `withTemporaryDatabase` | CREATE DATABASE, DROP DATABASE on admin DB | HIGH — DDL on real DB |

#### Exported Read-Only Functions

| Function | What it does |
|---|---|
| `buildDbConnectionConfig` | Builds a connection config object (no DB connection) |
| `checkDbConnection` | Tests connectivity (SELECT 1 style) |
| `inspectCoreSchema` | SELECT from pg_tables, information_schema.columns |
| `assertCoreSchema` | Asserts schema via `inspectCoreSchema` |
| `readExecutableSql` | Reads SQL from disk (fs, no DB) |
| `resolveBlueprintSqlFiles` | Lists SQL files (fs, no DB) |
| `resolveMigrationSqlFiles` | Lists migration SQL files (fs, no DB) |
| `createBlueprintCheckDatabaseName` | Generates a database name string (no DB) |

#### Conclusion

`dbBlueprint.js` IS a direct DB write boundary. It imports `pg.Pool`, creates connections,
and has multiple functions that execute write SQL (INSERT, CREATE DATABASE, DROP DATABASE)
or execute arbitrary SQL from migration files. It exports both write-capable and read-only
functions.

**Guard boundary recommendation:** Guard at consumer entrypoint. The shared module should
NOT independently guard itself because callers use different subsets of functions:
- Most callers (18+) only use `buildDbConnectionConfig` — read-only, no guard needed at
  the module boundary
- A few callers use `runColdStartBlueprintCheck` or `ensureBlueprintOnCurrentDatabase` —
  these must be guarded at the consumer level
- Adding a blanket guard to the module's write functions would still leave the module
  importable and the guard checkable only at runtime

### 2. restoreMappingsWorkflow.js

**Path:** `scripts/ops/helpers/restoreMappingsWorkflow.js`

#### Signal Analysis

| Signal | Value |
|---|---|
| DB client import | No — does NOT import `pg`, `Pool`, or any DB client directly |
| Direct Pool/Client creation | No |
| Executable query calls | No — calls `repository.saveOddsPortalMapping(...)` which is a dependency-injected repository |
| Write SQL in code | No — write SQL is in the repository, not this module |
| Read-only wrappers | N/A — module is pure workflow orchestration |
| Write helper export | Yes — `restoreEvidenceMappings` (conditionally calls `repository.saveOddsPortalMapping`), `resyncCanonicalUrls` (conditionally calls `repository.saveOddsPortalMapping`) |
| Read-only helper export | N/A |
| Dry-run support | Yes — both exported functions accept `dryRun` parameter; when `true`, skip `repository.saveOddsPortalMapping` |

#### Consumer Analysis

`restoreMappingsWorkflow.js` has **0 active consumers** in the current codebase:
- `restoreEvidenceMappings` and `resyncCanonicalUrls` are exported but NOT imported by any
  script in `scripts/`, `tests/`, `src/`, or `.github/`
- The module is only referenced in `db_write_guard_legacy_allowlist.json`

#### Conclusion

`restoreMappingsWorkflow.js` is an INDIRECT write boundary. It does NOT import any DB
client or execute SQL directly. It receives a `repository` object via dependency injection
and calls `repository.saveOddsPortalMapping()`. The actual DB write is in the repository
implementation, not in this module.

The module has built-in `dryRun` support — when `dryRun: true`, no `saveOddsPortalMapping`
call is made. This is a good pattern.

**Guard boundary recommendation:** Guard at consumer entrypoint. Since:
- The module has no DB client of its own
- The module already supports `dryRun`
- The module has 0 active consumers today
- Any future consumer would need to inject a repository that may or may not write to DB

The guard belongs in the repository implementation that is injected. When a consumer is
written, it should pass `dryRun: true` by default and require explicit authorization.

### 3. odds_harvest_pipeline.shared.js

**Path:** `scripts/ops/odds_harvest_pipeline.shared.js`

#### Signal Analysis

| Signal | Value |
|---|---|
| DB client import | No — does NOT import `pg`, `Pool`, or any DB client |
| Direct Pool/Client creation | No |
| Executable query calls | No — only exports SQL string constants |
| Write SQL in code | Yes — `UPSERT_MAPPING_SQL` (INSERT INTO matches_oddsportal_mapping ... ON CONFLICT DO UPDATE) and `UPSERT_ODDS_SQL` (INSERT INTO odds ... ON CONFLICT DO UPDATE) |
| Read-only SQL in code | Yes — `COVERAGE_SQL` (SELECT/COUNT), `TARGETS_SQL` (SELECT) |
| Write helper export | SQL string constants only — no query execution function |
| Read-only helper export | Yes — utility functions: `parseArgs`, `sleep`, `extractMedianOddsSnapshots`, `normalizeTitleKey` |

#### Consumer Analysis

| # | Consumer | Imports | Guard Status |
|---|---|---|---|
| 1 | `scripts/ops/odds_sniper.js` | `UPSERT_ODDS_SQL`, `CURRENT_BOOKMAKER`, `OPENING_BOOKMAKER`, `DEFAULT_USER_AGENT`, `DEFAULT_RETRIES`, `DEFAULT_RETRY_DELAY_MS`, `extractMedianOddsSnapshots` | ✅ Guarded (Phase 1) — calls `assertDbWriteAllowed()` in `upsertMappingAndOdds()` and `runTargetedStitch()` |
| 2 | `scripts/ops/odds_harvest_pipeline.js` | `UPSERT_MAPPING_SQL`, `UPSERT_ODDS_SQL`, `COVERAGE_SQL`, `TARGETS_SQL`, `CURRENT_BOOKMAKER`, `OPENING_BOOKMAKER`, `RESULTS_BASE_URL`, `TARGET_SEASON`, `extractMedianOddsSnapshots`, `normalizeTitleKey`, `parseArgs`, `sleep`, `DEFAULT_CONCURRENCY`, `DEFAULT_L3_BATCH_SIZE`, `DEFAULT_PROGRESS_EVERY`, `DEFAULT_RETRIES`, `DEFAULT_RETRY_DELAY_MS`, `DEFAULT_USER_AGENT`, `LEAGUE_ROUTE_CATALOG`, `MATCH_DELTA_MS`, `MONTHS`, `ODDSPORTAL_TEAM_ALIASES`, `TARGET_SEASON_TAG` | ⚠️ UNGUARDED — has `#!/usr/bin/env node`, imports `Pool` from `pg`, executes `UPSERT_MAPPING_SQL` and `UPSERT_ODDS_SQL` write SQL, but has NO `assertDbWriteAllowed()` call |

#### Critical Finding

**`odds_harvest_pipeline.js` is an UNGUARDED consumer** of `odds_harvest_pipeline.shared.js`.
It:
- Is a CLI entrypoint (`#!/usr/bin/env node`)
- Imports `Pool` from `pg` directly
- Imports `UPSERT_MAPPING_SQL` and `UPSERT_ODDS_SQL` (write SQL) from the shared module
- Uses Playwright/Chromium for browser automation
- Has NO `assertDbWriteAllowed()` call
- Is NOT in the SC-002 allowlist
- Was NOT covered by Phase1–Phase7 guard integration
- Was NOT in the 43 skipped_complex audit scope

This represents a **real unguarded DB write path** that consumes a shared module.

#### Conclusion

`odds_harvest_pipeline.shared.js` is an INDIRECT write boundary. It does NOT import any DB
client or execute SQL — it only exports SQL string constants (some read-only, some write).
The actual DB write happens in the consumer entrypoints that import `UPSERT_MAPPING_SQL`
and `UPSERT_ODDS_SQL` and execute them against their own `Pool`.

**Guard boundary recommendation:** Guard at consumer entrypoint. The shared module cannot
guard itself because it has no DB connection. The enforcement must be:
- Verify that every consumer that imports `UPSERT_MAPPING_SQL` or `UPSERT_ODDS_SQL` calls
  `assertDbWriteAllowed()` before executing those SQL strings

## Consumer Entrypoint Map

### dbBlueprint.js Consumers

| # | Consumer Path | Type | Imports | DB Write Possible? | Has Guard? | Recommended Guard Location | Recommended Task |
|---|---|---|---|---|---|---|---|
| 1 | `scripts/ops/gatekeeper.js` | CLI script | `runColdStartBlueprintCheck` | Yes — creates/drops temp DB, runs write probe | No | consumer_entrypoint | implement_consumer_guard |
| 2 | `scripts/devops/gatekeeper.sh` | Shell/CI script | `runColdStartBlueprintCheck` (via inline node) | Yes — creates/drops temp DB, runs write probe | No | consumer_entrypoint | implement_consumer_guard |
| 3 | `scripts/ops/db_vault.js` | CLI script | `ensureBlueprintOnCurrentDatabase`, `buildDbConnectionConfig`, `REPO_ROOT` | Yes — applies migrations, optional write probe | Yes (`assertDbWriteAllowed` at line 271) ✅ | already_guarded_consumer | no_action |
| 4 | `scripts/ops/csv_bulk_loader.js` | CLI script | `REPO_ROOT`, `MIGRATIONS_DIR`, `buildDbConnectionConfig`, `readExecutableSql` (read-only helpers) | Yes — but via its own Pool + INSERT, not via dbBlueprint write functions | Yes (`assertDbWriteAllowed` at line 608) ✅ | already_guarded_consumer | no_action |
| 5 | `scripts/ops/local_dom_ingestor.js` | CLI script | `REPO_ROOT`, `MIGRATIONS_DIR`, `buildDbConnectionConfig`, `readExecutableSql` (read-only helpers) | Yes — but via its own Pool + INSERT, not via dbBlueprint write functions | Yes (`assertDbWriteAllowed` at line 496) ✅ | already_guarded_consumer | no_action |
| 6 | `scripts/ops/pageprops_v2_single_target_controlled_write.js` | CLI script | `buildDbConnectionConfig` (read-only only) | Yes — via own Pool + INSERT | Yes (Phase 2 batch 1) ✅ | already_guarded_consumer | no_action |
| 7 | `scripts/ops/remaining_seeded_pageprops_v2_controlled_write.js` | CLI script | `buildDbConnectionConfig` (read-only only) | Yes — via own Pool + INSERT | Yes (Phase 2 batch 1) ✅ | already_guarded_consumer | no_action |
| 8 | `scripts/ops/single_league_pageprops_v2_controlled_write_execute.js` | CLI script | `buildDbConnectionConfig` (read-only only) | Yes — via own Pool + INSERT | Yes (Phase 2 batch 1) ✅ | already_guarded_consumer | no_action |
| 9 | `scripts/ops/cleanup_csv_bulk_loader_import.js` | CLI script | `buildDbConnectionConfig` (read-only only) | Unknown — needs review | Unknown | needs_manual_review | manual_review |
| 10 | `scripts/ops/fetch_and_adapt_euro_leagues.js` | CLI script | `REPO_ROOT`, `buildDbConnectionConfig` (read-only only) | Unknown — needs review | Unknown | needs_manual_review | manual_review |
| 11 | `scripts/ops/html_hydration_source_fidelity_live_compare.js` | CLI script | `buildDbConnectionConfig` (read-only only) | No — SELECT-only via queryReadOnly() | No (false_positive, reclassified) ✅ | no_guard_needed | no_action |
| 12 | `scripts/ops/master_inventory.js` | CLI script | `buildDbConnectionConfig` (read-only only) | Unknown — needs review | Unknown | needs_manual_review | manual_review |
| 13 | `scripts/ops/pageprops_v2_no_write_preview.js` | CLI script | `buildDbConnectionConfig` (read-only only) | No — SELECT-only via queryReadOnly() | No (false_positive, reclassified) ✅ | no_guard_needed | no_action |
| 14 | `scripts/ops/pageprops_v2_raw_completeness_audit.js` | CLI script | `buildDbConnectionConfig` (read-only only) | No — SELECT-only via assertSelectOnly() | No (false_positive, reclassified) ✅ | no_guard_needed | no_action |
| 15 | `scripts/ops/pageprops_v2_single_target_write_preflight.js` | CLI script | `buildDbConnectionConfig` (read-only only) | No — SELECT-only via queryReadOnly() | No (false_positive, reclassified) ✅ | no_guard_needed | no_action |
| 16 | `scripts/ops/purge_ghost_data.js` | CLI script | `buildDbConnectionConfig` (read-only only) | Yes — has own Pool + DELETE | Unknown — needs verification | needs_manual_review | manual_review |
| 17 | `scripts/ops/purge_orphans.js` | CLI script | `buildDbConnectionConfig` (read-only only) | Yes — has own Pool + DELETE | Unknown — needs verification | needs_manual_review | manual_review |
| 18 | `scripts/ops/raw_match_data_completeness_fidelity_audit.js` | CLI script | `buildDbConnectionConfig` (read-only only) | Unknown — needs review | Unknown | needs_manual_review | manual_review |
| 19 | `scripts/ops/remaining_seeded_pageprops_v2_acquisition_preflight.js` | CLI script | `buildDbConnectionConfig` (read-only only) | No — SELECT-only via queryReadOnly() | No (false_positive, reclassified) ✅ | no_guard_needed | no_action |
| 20 | `scripts/ops/renewed_pageprops_v2_raw_write_execute.js` | CLI script | `buildDbConnectionConfig` (read-only only) | Yes — has own Pool + INSERT | Unknown — needs verification | needs_manual_review | manual_review |
| 21 | `scripts/ops/reset_database.js` | CLI script | `buildDbConnectionConfig` (read-only only) | Yes — has own Pool + DELETE/TRUNCATE | Unknown — needs verification | needs_manual_review | manual_review |
| 22 | `scripts/ops/seed_fotmob_sample.js` | CLI script | `buildDbConnectionConfig`, `REPO_ROOT` (read-only only) | Unknown — needs review | Unknown | needs_manual_review | manual_review |
| 23 | `scripts/ops/single_league_pageprops_v2_controlled_write_plan.js` | CLI script | `buildDbConnectionConfig` (read-only only) | No — SELECT-only via queryReadOnly() | No (false_positive, reclassified) ✅ | no_guard_needed | no_action |
| 24 | `scripts/ops/single_league_small_batch_pageprops_v2_preflight.js` | CLI script | `buildDbConnectionConfig` (read-only only) | No — SELECT-only via queryReadOnly() | No (false_positive, reclassified) ✅ | no_guard_needed | no_action |

### restoreMappingsWorkflow.js Consumers

| # | Consumer Path | Type | Imports | DB Write Possible? | Has Guard? | Recommended Guard Location | Recommended Task |
|---|---|---|---|---|---|---|---|
| — | **No active consumers** | — | — | N/A | N/A | consumer_entrypoint (when first consumer is written) | no_action (module unused) |

### odds_harvest_pipeline.shared.js Consumers

| # | Consumer Path | Type | Imports | DB Write Possible? | Has Guard? | Recommended Guard Location | Recommended Task |
|---|---|---|---|---|---|---|---|
| 1 | `scripts/ops/odds_sniper.js` | CLI script (browser+DB) | `UPSERT_ODDS_SQL`, `CURRENT_BOOKMAKER`, `OPENING_BOOKMAKER`, `extractMedianOddsSnapshots`, `DEFAULT_USER_AGENT`, `DEFAULT_RETRIES`, `DEFAULT_RETRY_DELAY_MS` | Yes — INSERT INTO odds via UPSERT_ODDS_SQL | Yes (Phase 1) ✅ | already_guarded_consumer | no_action |
| 2 | `scripts/ops/odds_harvest_pipeline.js` | CLI script (browser+DB) | `UPSERT_MAPPING_SQL`, `UPSERT_ODDS_SQL`, `COVERAGE_SQL`, `TARGETS_SQL`, plus 18+ utility/config exports | Yes — INSERT/UPSERT via both write SQL templates | ✅ **Guarded (implementation phase1)** — `assertDbWriteAllowed()` in `upsertMappingAndOdds()` before BEGIN transaction | already_guarded_consumer | no_action |

## Recommended Guard Boundary

### Module-Level Guard: NOT RECOMMENDED

Adding `assertDbWriteAllowed()` inside the shared modules is NOT the right approach because:

1. **dbBlueprint.js** exports both write-capable and read-only functions. Most consumers
   (18+ of 24) only use `buildDbConnectionConfig` — a read-only config builder. A module-level
   guard would break these read-only consumers or require them to set env vars unnecessarily.

2. **restoreMappingsWorkflow.js** has no DB client of its own and uses dependency injection.
   A guard here would need to know about the repository implementation, which violates the
   module's design.

3. **odds_harvest_pipeline.shared.js** has no DB client of its own — it only exports SQL
   strings. Adding a guard to a string-exporting module would be misplaced.

### Consumer-Level Guard: RECOMMENDED

The guard belongs at the **consumer entrypoint** — the script that imports the shared module,
creates a Pool, and executes the SQL. This is the established SC-002 pattern (used by all
43 Phase1–Phase7 scripts) and works correctly for shared module consumers:

- `odds_sniper.js` (Phase 1) demonstrates the correct pattern: imports `UPSERT_ODDS_SQL`
  from the shared module, creates its own `Pool`, and calls `assertDbWriteAllowed()` before
  executing the SQL.

- `db_vault.js`, `csv_bulk_loader.js`, `local_dom_ingestor.js` all follow the pattern of
  importing read-only helpers from `dbBlueprint.js` and calling `assertDbWriteAllowed()`
  before their own write operations.

### Boundary Summary

| Shared Module | Recommended Guard Boundary | Rationale |
|---|---|---|
| dbBlueprint.js | consumer_entrypoint | Module exports both read-only and write functions; most consumers use only read-only; forcing guard at module level would break read-only consumers |
| restoreMappingsWorkflow.js | consumer_entrypoint (when first consumer written) | Module uses dependency injection; no DB client of its own; 0 active consumers today |
| odds_harvest_pipeline.shared.js | consumer_entrypoint | Module exports SQL strings only; no DB client of its own; guard must be in the script that executes the SQL |

## Do Not Implement Yet

The following actions are explicitly reserved for a follow-up implementation phase:

1. **Do NOT add `assertDbWriteAllowed()` to `dbBlueprint.js`.** This would break 18+
   read-only consumers that use `buildDbConnectionConfig`. The write-capable functions
   (`runColdStartBlueprintCheck`, `ensureBlueprintOnCurrentDatabase`) are used by CI
   infrastructure (gatekeeper) and the guard integration needs careful design.

2. **Do NOT guard `odds_harvest_pipeline.js` in this phase.** It is a high-risk unguarded
   consumer, but it involves browser automation (Playwright) and has complex pipeline logic
   that needs its own dedicated task. Adding a simple `assertDbWriteAllowed()` without
   understanding its full execution model could create a false sense of security.

3. **Do NOT guard `restoreMappingsWorkflow.js` at the module level.** It has 0 active
   consumers and uses dependency injection. Guarding it now would be premature.

4. **Do NOT change the classification of the 8 `needs_manual_review` consumers** in the
   consumer map above. They import only `buildDbConnectionConfig` from dbBlueprint but may
   have their own DB write paths via separate Pool imports. They need individual review.

## Risks and Unknowns

### Known Gaps

| Gap | Severity | Detail |
|---|---|---|
| `odds_harvest_pipeline.js` — ~~UNGUARDED~~ **NOW GUARDED** | ~~HIGH~~ **RESOLVED** | CLI entrypoint with Pool + write SQL from shared module + Playwright. Guard added in `upsertMappingAndOdds()` by `shared_module_db_write_boundary_implementation_phase1`. ✅ |
| `gatekeeper.js` — UNGUARDED | MEDIUM | Uses `runColdStartBlueprintCheck` which creates/drops temp DBs. CI infrastructure, not user-facing, but still a DB write path. |
| `gatekeeper.sh` — UNGUARDED | MEDIUM | Shell script that runs `runColdStartBlueprintCheck` via inline node. Same risk as gatekeeper.js. |
| 8 consumers with `needs_manual_review` | LOW–MEDIUM | These use only `buildDbConnectionConfig` from dbBlueprint but may have their own DB write paths. Need individual review. |
| `restoreMappingsWorkflow.js` future risk | LOW | 0 active consumers today, but if a consumer is written without guard, it would be an unguarded write path. |

### Static Analysis Limitations

- This analysis is purely static — it reads source code but does not trace runtime execution.
- Dynamic `require()` calls or indirect imports may be missed.
- Consumers that import `buildDbConnectionConfig` but use their own Pool for writes are
  flagged as `needs_manual_review` — they may or may not be safe.
- The `odds_harvest_pipeline.js` gap was found because this design traced shared module
  consumers. It was NOT in the original 43 skipped_complex audit.

## Next Implementation Candidates

In priority order for a follow-up `shared_module_db_write_boundary_implementation_phase1`:

### Priority 1: Guard `odds_harvest_pipeline.js` ✅ COMPLETED

- **Status:** Completed by `shared_module_db_write_boundary_implementation_phase1`.
- **Guard location:** `upsertMappingAndOdds()` function, after `if (options.dryRun) return` check, before `client.query('BEGIN')` transaction.
- **Target tables:** `matches_oddsportal_mapping`, `odds`
- **Operations:** INSERT, UPDATE (via UPSERT with ON CONFLICT DO UPDATE)
- **Guard pattern:** `assertDbWriteAllowed({ script: 'odds_harvest_pipeline.js', tables: ['matches_oddsportal_mapping', 'odds'], operations: ['INSERT', 'UPDATE'] })`
- **Verification:** Static test confirms guard import, call position (before BEGIN), table names, and operation names. Changed-files enforcement passes.
- **Existing safety mechanisms preserved:** dryRun check remains before guard; production-like DB host hard block enforced by guard helper; Playwright/browser logic unchanged; scraper logic unchanged.

### Priority 2: Guard `gatekeeper.js` and `gatekeeper.sh` — PENDING

- **Risk:** MEDIUM — CI infrastructure, temp DB operations
- **Action:** Add `assertDbWriteAllowed()` or equivalent guard before
  `runColdStartBlueprintCheck`. Consider whether the write probe (INSERT + ROLLBACK)
  itself needs guarding or whether the temp DB lifecycle is sufficient isolation.
- **Verification:** Gatekeeper CI still passes after guard integration
- **Blocked by:** Needs dedicated implementation task.

### Priority 3: Review 8 `needs_manual_review` consumers — PENDING

- **Risk:** LOW–MEDIUM — uncertain write capability
- **Action:** Individually review each of the 8 consumers flagged as `needs_manual_review`
  in the consumer map. For each, determine: does it have its own Pool? Does it execute
  its own write SQL? Is it already guarded? Should it be guarded?
- **Verification:** Updated consumer map with resolved classifications
- **Blocked by:** Needs dedicated manual review task.

### Priority 4: Future consumer checklist for `restoreMappingsWorkflow.js` — PENDING

- **Risk:** LOW — 0 active consumers today
- **Action:** When a consumer of `restoreMappingsWorkflow.js` is first written, ensure it
  either passes `dryRun: true` by default or calls `assertDbWriteAllowed()` before setting
  `dryRun: false`
- **Verification:** PR review checklist item; changed-files enforcement
- **Blocked by:** First consumer being written

## SC-002 Status Impact

- **SC-002 remains partial mitigation only.**
- **1 HIGH priority guard implemented:** `odds_harvest_pipeline.js` now calls
  `assertDbWriteAllowed()` before INSERT/UPSERT write SQL on `matches_oddsportal_mapping`
  and `odds` tables. Guard follows the same pattern as `odds_sniper.js` (Phase 1).
- **1 HIGH priority gap resolved:** `odds_harvest_pipeline.js` was NOT in the original
  43 skipped_complex audit. It was discovered by the design phase and is now guarded.
- **2 remaining gaps (MEDIUM):** `gatekeeper.js` / `gatekeeper.sh` still pending.
- **8 needs_manual_review consumers** still pending.
- **3 shared modules** remain `design_mapped` (no module-level guard change).
- Training, data expansion, real DB write, scraper/browser remain BLOCKED.
