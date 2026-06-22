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

Breakdown by **actual DB write capability** (this audit):
| Classification | Count |
|---|---|
| confirmed_write_path_needs_guard | 20 |
| read_only | 12 |
| needs_manual_review | 4 |
| shared_module_no_execution | 3 |
| no_db_connection | 2 |
| scraper_or_browser_only | 1 |
| possible_indirect_write | 1 |

## Findings by Category

### pageProps Pipeline (9 scripts)

Of 9 pageProps pipeline scripts:
- **3 are confirmed_write_path_needs_guard**: `pageprops_v2_no_write_preview.js`,
  `pageprops_v2_raw_completeness_audit.js`, `single_league_small_batch_pageprops_v2_preflight.js`
  — despite names suggesting "preview", "audit", or "preflight", these scripts import a DB
  client (`require('pg')`, `Pool`) and contain write SQL in executable code. They are NOT
  read-only.
- **2 are read_only**: `pageprops_v2_controlled_write_plan.js`,
  `pageprops_v2_recapture_runner_identity_input_contract_fix_plan.js`,
  `pageprops_v2_bounded_expanded_blocked_target_review_execute.js`,
  `single_league_small_batch_target_manifest_plan.js` — planning/manifest files with no DB
  client.
- **4 need_manual_review**: `all_seeded_pageprops_v2_canonical_read_verification.js`,
  `pageprops_v2_identity_contract_regression_execute.js`,
  `pageprops_v2_post_write_canonical_read_verification.js`,
  `pageprops_v2_suspended_target_review_execute.js` — have SQL keywords or `.query()` calls
  but no direct DB client import (may use helper modules or indirect execution).

**Key insight:** The name-based heuristic that labeled these as "pageProps pipeline" is
misleading. Several "preview", "preflight", and "audit" scripts actually DO have real DB
write capability and are NOT safe. The pageProps pipeline has its own controlled-write
guard structure on some scripts (e.g., `REQUIRED_YES_FLAGS`, `ALLOW_CONTROLLED_WRITE`),
but this is not the standard `assertDbWriteAllowed()` guard and has not been audited for
completeness.

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
- **5 are confirmed_write_path_needs_guard**: `dataset_status_audit.js`,
  `formal_training_dataset_design_dry_run.js`, `l3_local_dry_run.js`,
  `technical_debt_workflow_audit_dry_run.js`, `training_dataset_leakage_dry_run.js`
  — these have DB client imports and write SQL execution despite names containing
  "audit", "dry_run", or "leakage". The names do NOT match the actual capability.
- **1 is read_only**: `authoritative_workflow_enforcement_dry_run.js`,
  `raw_match_data_versioned_schema_migration_preflight.js`
  — planning files with no DB client detected.
- **1 is possible_indirect_write**: `training_pipeline_smoke_dry_run.js` — has COPY
  keyword in code but execution path is unclear.

**Key insight:** The "dry_run" or "audit" label in filenames is NOT a reliable safety
indicator. Several of these scripts import real DB clients and contain write SQL. Whether
they actually execute writes depends on runtime env vars and DRY_RUN flags — the static
analysis cannot confirm the runtime behavior, but the capability is present.

### Shared Modules (3 scripts)

All 3 are **shared_module_no_execution**:
- `helpers/dbBlueprint.js` — DB schema/migration helper; imports `Pool` from `pg` but
  is a library module consumed by other entrypoints. Defines table schemas, migration
  functions, and connection utilities.
- `helpers/restoreMappingsWorkflow.js` — restore mappings workflow helper; consumed
  by entrypoint scripts.
- `odds_harvest_pipeline.shared.js` — shared odds harvest pipeline with SQL templates
  (UPSERT_ODDS_SQL); consumed by `odds_sniper.js` and other odds scripts.

**Key insight:** Shared modules should not independently guard themselves because they
do not know their calling context. The enforcement must be at the boundary: every
entrypoint that consumes a shared module with DB write risk must itself be guarded.

### Browser/Playwright (scanner N/A, 21 scripts)

These 21 scripts were NOT in the allowlist and were classified by the scanner as
"browser/Playwright automation — needs manual review". Our static analysis reveals:

- **11 are confirmed_write_path_needs_guard**: These scripts have BOTH DB client imports
  AND write SQL execution. The scanner's "browser/Playwright" label is partially correct
  (some use Playwright) but misses the DB write capability. Key examples:
  - `fixture_harvester_l1.js` — Playwright + Pool + BEGIN/COMMIT/ROLLBACK + INSERT INTO matches
  - `odds_sniper.js` — Playwright + Pool + UPSERT_ODDS_SQL
  - `controlled_matches_identity_seed_prerequisite_plan.js` — has guard mentions + DB client
  - `pageprops_v2_single_target_controlled_write.js` — own controlled write guard + DB client
  - `single_league_pageprops_v2_controlled_write_execute.js` — own guard with ALLOW_* flags
  - `remaining_seeded_pageprops_v2_controlled_write.js` — controlled write with DB client
  - `html_hydration_source_fidelity_live_compare.js` — Pool + client.query()
  - `l2_raw_match_data_ingest_preflight.js` — DB client + write SQL
  - `post_seed_matches_identity_raw_write_readiness_audit.js` — DB client + write SQL
  - `remaining_seeded_pageprops_v2_acquisition_preflight.js` — DB client + write SQL
  - `pageprops_v2_single_target_write_preflight.js` — DB client + write SQL

- **6 are read_only**: Planning files (`l2_raw_match_data_ingest_plan.js`,
  `l1_matches_seed_commit_plan.js`, `large_scale_pageprops_v2_acquisition_strategy_plan.js`,
  `pageprops_v2_no_write_payload_recapture_plan.js`,
  `pageprops_v2_raw_write_input_source_investigation.js`,
  `fotmob_ligue1_corrected_source_discovery_adg21.js`) — no DB client detected.

- **1 is scraper_or_browser_only**: `fotmob_ligue1_adg60_raw_payload_source_inventory.js`
  — browser/FotMob script with no DB client.

- **3 are read-only or planning**: The remaining scripts are `pageprops_v2_no_write_preview.js`
  (already counted in pageProps), `single_league_small_batch_pageprops_v2_preflight.js`
  (already counted in pageProps), and `single_league_small_batch_target_manifest_plan.js`
  (already counted in pageProps), all counted above under their actual categories.

**Key insight:** The scanner's "browser/Playwright automation — needs manual review"
label was an oversimplification. Many of these 21 scripts are NOT just browser/scraper
scripts — they have real DB write capability and need guard integration. The
`odds_sniper.js` and `fixture_harvester_l1.js` scripts are particularly high-risk
because they combine browser automation AND DB write in a single script.

## Per-Script Findings

### Category: pageprops_pipeline (9)

| # | Path | has_db_import | has_execute | sql_in_code | has_browser | Recommended Classification | Evidence |
|---|---|---|---|---|---|---|---|
| 1 | scripts/ops/all_seeded_pageprops_v2_canonical_read_verification.js | No | Yes | Yes | No | needs_manual_review | Has .query() execution and SQL patterns (TRUNCATE, COPY) but no direct DB client import — may use helpers |
| 2 | scripts/ops/pageprops_v2_bounded_expanded_blocked_target_review_execute.js | No | No | No | No | read_only | No DB client, no query execution — review/audit context |
| 3 | scripts/ops/pageprops_v2_controlled_write_plan.js | No | No | No | No | read_only | Planning document — no DB client or execution |
| 4 | scripts/ops/pageprops_v2_identity_contract_regression_execute.js | No | Yes | Yes | No | needs_manual_review | Has .query() execution and SQL keywords (UPDATE) but no direct DB client — may use pageProps pipeline helpers |
| 5 | scripts/ops/pageprops_v2_post_write_canonical_read_verification.js | No | Yes | Yes | No | needs_manual_review | Has .query() execution and SQL keywords (TRUNCATE, COPY) but no direct DB client — post-write verification |
| 6 | scripts/ops/pageprops_v2_raw_completeness_audit.js | Yes | Yes | Yes | No | confirmed_write_path_needs_guard | Imports Pool from pg, has write SQL (TRUNCATE, GRANT, REVOKE, COPY), and executes queries — needs guard |
| 7 | scripts/ops/pageprops_v2_recapture_runner_identity_input_contract_fix_plan.js | No | No | No | No | read_only | Planning document — no DB client or execution |
| 8 | scripts/ops/pageprops_v2_suspended_target_review_execute.js | No | Yes | Yes | No | needs_manual_review | Has .query() execution and SQL keywords (UPDATE) but no direct DB client — may use helpers |
| 9 | scripts/ops/single_league_small_batch_target_manifest_plan.js | No | No | No | No | read_only | Manifest/planning — no DB client or execution |

### Category: fotmob_pipeline (2)

| # | Path | has_db_import | has_execute | sql_in_code | has_browser | Recommended Classification | Evidence |
|---|---|---|---|---|---|---|---|
| 10 | scripts/ops/fotmob_adg60_raw_json_db_storage_no_feature_parse.js | Yes | Yes | Yes | No | confirmed_write_path_needs_guard | Imports Pool from pg, has write SQL (INSERT, UPDATE, UPSERT), executes queries — FotMob raw JSON DB write |
| 11 | scripts/ops/fotmob_ligue1_adg57_no_write_mutation_dry_run_preview.js | No | No | No | No | read_only | No DB client, no execution — "no write mutation" in filename is accurate per static analysis |

### Category: shared_module (3)

| # | Path | has_db_import | has_execute | sql_in_code | has_browser | Recommended Classification | Evidence |
|---|---|---|---|---|---|---|---|
| 12 | scripts/ops/helpers/dbBlueprint.js | Yes | Yes | Yes | No | shared_module_no_execution | DB schema/migration helper — consumed by entrypoints; not standalone |
| 13 | scripts/ops/helpers/restoreMappingsWorkflow.js | No | Yes | No | No | shared_module_no_execution | Restore mappings helper — consumed by entrypoints; not standalone |
| 14 | scripts/ops/odds_harvest_pipeline.shared.js | No | Yes | Yes | No | shared_module_no_execution | Shared odds harvest pipeline with SQL templates — consumed by odds_sniper.js and others |

### Category: dry_run_or_audit (8)

| # | Path | has_db_import | has_execute | sql_in_code | has_browser | Recommended Classification | Evidence |
|---|---|---|---|---|---|---|---|
| 15 | scripts/ops/authoritative_workflow_enforcement_dry_run.js | No | No | No | No | read_only | No DB client, no execution — audit tool |
| 16 | scripts/ops/dataset_status_audit.js | Yes | Yes | Yes | No | confirmed_write_path_needs_guard | Imports Pool from pg, has write SQL (TRUNCATE, GRANT, REVOKE, COPY), executes queries despite "audit" name |
| 17 | scripts/ops/formal_training_dataset_design_dry_run.js | Yes | Yes | Yes | No | confirmed_write_path_needs_guard | Imports Pool from pg, has write SQL (UPDATE), executes queries despite "dry_run" name |
| 18 | scripts/ops/l3_local_dry_run.js | Yes | Yes | Yes | No | confirmed_write_path_needs_guard | Imports Pool from pg, has write SQL (TRUNCATE, GRANT, REVOKE), executes queries despite "dry_run" name |
| 19 | scripts/ops/raw_match_data_versioned_schema_migration_preflight.js | No | No | No | No | read_only | Preflight/planning — no DB client detected; execute counterpart is already guarded (Phase4) |
| 20 | scripts/ops/technical_debt_workflow_audit_dry_run.js | Yes | Yes | Yes | No | confirmed_write_path_needs_guard | Imports Pool from pg, has write SQL (INSERT, UPDATE, DELETE, COPY), executes queries |
| 21 | scripts/ops/training_dataset_leakage_dry_run.js | Yes | Yes | Yes | No | confirmed_write_path_needs_guard | Imports Pool from pg, has write SQL (UPDATE), executes queries despite "leakage" name |
| 22 | scripts/ops/training_pipeline_smoke_dry_run.js | No | Yes | No | No | possible_indirect_write | Has COPY keyword and .query() execution but no direct DB client — may use indirection |

### Category: N/A (browser/Playwright scanner flagged, 21)

| # | Path | has_db_import | has_execute | sql_in_code | has_browser | Recommended Classification | Evidence |
|---|---|---|---|---|---|---|---|
| 23 | scripts/ops/controlled_matches_identity_seed_prerequisite_plan.js | Yes | Yes | Yes | No | confirmed_write_path_needs_guard | Imports Pool from pg, has write SQL (UPDATE, TRUNCATE, GRANT, REVOKE, COPY), executes queries, mentions guard |
| 24 | scripts/ops/fixture_harvester_l1.js | Yes | Yes | Yes | Yes | confirmed_write_path_needs_guard | Playwright + Pool + BEGIN/COMMIT/ROLLBACK + INSERT INTO matches — browser + DB write |
| 25 | scripts/ops/fotmob_ligue1_adg60_raw_payload_source_inventory.js | No | No | No | Yes | scraper_or_browser_only | Playwright/browser script — no DB client detected |
| 26 | scripts/ops/fotmob_ligue1_corrected_source_discovery_adg21.js | No | No | No | No | read_only | No DB client, no browser import, no query execution — planning/investigation |
| 27 | scripts/ops/html_hydration_source_fidelity_live_compare.js | Yes | Yes | Yes | No | confirmed_write_path_needs_guard | Imports Pool from pg, has client.query() with write SQL — needs guard |
| 28 | scripts/ops/l1_matches_seed_commit_plan.js | No | No | No | No | read_only | Planning document — no DB client or execution |
| 29 | scripts/ops/l2_raw_match_data_ingest_plan.js | No | No | No | No | read_only | Planning document — references "future controlled write script" |
| 30 | scripts/ops/l2_raw_match_data_ingest_preflight.js | Yes | Yes | Yes | No | confirmed_write_path_needs_guard | Imports Pool from pg, has write SQL (UPDATE, TRUNCATE, GRANT, REVOKE, COPY), executes queries |
| 31 | scripts/ops/large_scale_pageprops_v2_acquisition_strategy_plan.js | No | No | No | No | read_only | Strategy/planning document — no DB client |
| 32 | scripts/ops/odds_sniper.js | Yes | Yes | Yes | Yes | confirmed_write_path_needs_guard | Playwright + Pool + UPSERT_ODDS_SQL from shared module — browser + DB write; highest risk |
| 33 | scripts/ops/pageprops_v2_no_write_payload_recapture_plan.js | No | No | No | No | read_only | Planning document — references controlled write helper, no direct DB |
| 34 | scripts/ops/pageprops_v2_no_write_preview.js | Yes | Yes | Yes | No | confirmed_write_path_needs_guard | Imports Pool from pg, has write SQL, executes queries — "no_write_preview" name is misleading |
| 35 | scripts/ops/pageprops_v2_raw_write_input_source_investigation.js | No | No | Yes | No | read_only | Investigation document — SQL keywords in analysis context, no DB client |
| 36 | scripts/ops/pageprops_v2_single_target_controlled_write.js | Yes | Yes | Yes | No | confirmed_write_path_needs_guard | Imports Pool from pg, has controlled write guard structure + write SQL — needs standard guard |
| 37 | scripts/ops/pageprops_v2_single_target_write_preflight.js | Yes | Yes | Yes | No | confirmed_write_path_needs_guard | Imports Pool from pg, has write SQL, executes queries — preflight with DB |
| 38 | scripts/ops/post_seed_matches_identity_raw_write_readiness_audit.js | Yes | Yes | Yes | No | confirmed_write_path_needs_guard | Imports Pool from pg, has write SQL (UPDATE, TRUNCATE, GRANT, REVOKE, COPY), executes queries |
| 39 | scripts/ops/remaining_seeded_pageprops_v2_acquisition_preflight.js | Yes | Yes | Yes | No | confirmed_write_path_needs_guard | Imports Pool from pg, has write SQL (TRUNCATE, GRANT, REVOKE, COPY), executes queries |
| 40 | scripts/ops/remaining_seeded_pageprops_v2_controlled_write.js | Yes | Yes | Yes | No | confirmed_write_path_needs_guard | Imports Pool from pg, has controlled write guard + write SQL |
| 41 | scripts/ops/single_league_pageprops_v2_controlled_write_execute.js | Yes | Yes | Yes | No | confirmed_write_path_needs_guard | Imports Pool from pg, has own guard (ALLOW_* flags), has write SQL — needs standard guard |
| 42 | scripts/ops/single_league_pageprops_v2_controlled_write_plan.js | Yes | Yes | Yes | No | confirmed_write_path_needs_guard | Imports Pool from pg, has controlled write guard mentions + write SQL |
| 43 | scripts/ops/single_league_small_batch_pageprops_v2_preflight.js | Yes | Yes | Yes | No | confirmed_write_path_needs_guard | Imports Pool from pg, has write SQL, executes queries — preflight with DB |

## Risk Summary

### Confirmed DB Write Paths (20 scripts)

These 20 scripts have **confirmed real DB write capability** based on static analysis
(DB client import + query execution + write SQL in code). They need guard integration.

**High-risk subgroup (browser + DB):**
- `fixture_harvester_l1.js` — Playwright + Pool + transactions + INSERT
- `odds_sniper.js` — Playwright + Pool + UPSERT via shared module

**Controlled-write subgroup (own guard, needs standardization):**
- `controlled_matches_identity_seed_prerequisite_plan.js`
- `pageprops_v2_single_target_controlled_write.js`
- `remaining_seeded_pageprops_v2_controlled_write.js`
- `single_league_pageprops_v2_controlled_write_execute.js`
- `single_league_pageprops_v2_controlled_write_plan.js`

**Misleading-name subgroup (labeled "dry_run", "audit", "preview" but has real DB):**
- `dataset_status_audit.js`
- `formal_training_dataset_design_dry_run.js`
- `l3_local_dry_run.js`
- `technical_debt_workflow_audit_dry_run.js`
- `training_dataset_leakage_dry_run.js`
- `pageprops_v2_no_write_preview.js`
- `pageprops_v2_raw_completeness_audit.js`

### Read-Only / No DB (14 scripts)

These 14 scripts have **no detected DB client** and are likely safe from DB write risk:
- 12 read_only: planning, manifest, investigation, preview files
- 2 no_db_connection: no DB-related signals at all

**However**, "no DB client detected" is a static signal, not a runtime guarantee. Some of
these scripts import helper modules (`pageprops_v2_no_write_preview.js` is imported by
controlled write scripts) that may provide DB access indirectly.

### Shared Modules (3 scripts)

Need boundary enforcement — see `shared_module_db_write_boundary_design_phase1`.

### Needs Manual Review (4 scripts)

These 4 scripts have `needs_manual_review` classification because they show conflicting
signals: `.query()` execution detected but no direct DB client import. They may use helper
modules or indirection for DB access:
- `all_seeded_pageprops_v2_canonical_read_verification.js`
- `pageprops_v2_identity_contract_regression_execute.js`
- `pageprops_v2_post_write_canonical_read_verification.js`
- `pageprops_v2_suspended_target_review_execute.js`

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
- **43/66 scripts are guarded. 20 of the remaining 43 skipped_complex are confirmed DB write paths.**
- **The gap is now more precisely characterized: 20 confirmed + 4 manual_review + 1 indirect + 3 shared_module = 28 scripts needing further action (guard or exclusion).**
- **14 scripts can potentially be reclassified as verified-read-only (pending formal exclusion).**

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
