# SC-002 Python / SQL / Migration Enforcement Design

- lifecycle: permanent
- owner: project governance
- created: 2026-06-23
- task: python_sql_migration_enforcement_design_phase1 (design) + python_sql_migration_enforcement_implementation_phase2A (implementation) + python_runtime_guard_implementation_phase2C_batch{1,2,3} (runtime guard) + python_confirmed_write_paths_design_phase2C_batch4 (design/classification) + consumer_level_guard_audit_db_pool_sync_sql_store (consumer audit) + python_indirect_write_path_design_phase1 (indirect design/classification)
- implementation_status: Phase2A COMPLETED, Phase2B COMPLETED, Phase2C batch1/batch2/batch3 COMPLETED (9/14 runtime guarded), Phase2C batch4 COMPLETED (5 remaining classified: 2 read_only, 3 infrastructure), consumer audit COMPLETED (3 infrastructure files: no new guards needed), indirect design COMPLETED (8 indirect paths classified: 6 needs_guard, 1 read_only, 1 false_positive)
- scanner: scripts/ops/python_db_write_static_enforcement.py
- allowlist: config/python_db_write_allowlist.json (28 entries, 9 runtime_guarded + 6 pending + 8 indirect + 5 manual review)
- guard_helper: scripts/ops/helpers/python_db_write_guard.py
- gate_integration: check_python_db_write_enforcement() in scripts/ops/ai_workflow_gate.py

## Summary

This document covers the **design and Phase2A implementation** of Python/SQL/migration
SC-002 enforcement. Phase1 designed the enforcement model and classified all Python/SQL files.
Phase2A implemented the Python static scanner, allowlist, and AI Workflow Gate changed-files
enforcement. Runtime guard implementation is reserved for Phase2C.

**This document and Phase2A implementation do NOT:**
- Implement Python runtime guard (reserved for Phase2C)
- Run any Python target script
- Execute any SQL / migration
- Connect to any database
- Perform any real DB write
- Run scraper / browser / Playwright
- Train or expand data
- Claim SC-002 is fully fixed
- Change runtime behavior of any kind

**This document DOES:**
- Statically inventory and classify all Python files with DB client or DB write keywords
- Statically inventory and classify all SQL / migration files
- Recommend an enforcement model for Python and SQL/migration layers
- Identify implementation candidates and manual review candidates
- Specify CI integration design

## Scope

### In scope

- All `*.py` files in the repository (374 total)
- All `*.sql` files in the repository (18 total)
- Alembic migration infrastructure (`src/database/migrations/`)
- Flyway-style migration files (`database/migrations/`)
- Docker initialization SQL (`deploy/docker/`)
- Python test files that connect to DB
- Static classification based on code reading, not runtime execution

### Out of scope

- JS `scripts/ops/**/*.js` files (already covered by JS-side SC-002 enforcement)
- `scripts/ops/helpers/db_write_guard.js` (the guard itself)
- Implementation of any Python guard or scanner
- Runtime behavior modification
- DB role / permission model review (separate task)
- Release gate checklist (separate task)

## Current JS-side SC-002 status

The JS side of SC-002 is now substantially addressed across multiple phases:

- **53 JS scripts guarded** (43 Phase1-7 + 6 confirmed write paths + 3 shared-module consumers + 1 odds_harvest_pipeline)
- **0 unguarded JS write paths** remain
- **0 needs_manual_review** JS scripts remain
- **All 14 manual_review candidates** reviewed and reclassified
- **Changed-files hard fail** active for `scripts/ops/**/*.js`
- **Production-like DB host hard block** enabled

However, SC-002 remains **partial mitigation only** because Python, SQL, and migration enforcement
is not yet designed or implemented. This document addresses that gap.

## Python candidate inventory

### Scan methodology

```
# Find all Python files
find . -name "*.py" -not -path "./.git/*" -not -path "./node_modules/*" \
  -not -path "./__pycache__/*" -not -path "./.claude/*" \
  -not -path "./.pytest_cache/*"

# Find Python files with DB client imports
grep -rl --include="*.py" -E "(psycopg|psycopg2|asyncpg|sqlalchemy|create_engine|sqlite3|DATABASE_URL|POSTGRES)" .

# Find Python files with DB execute/query patterns
grep -rl --include="*.py" -E "(\.execute\(|\.query\(|session\.execute|Session\(|to_sql\(|\.executemany\()" .

# Find Python files with SQL write keywords
grep -rl --include="*.py" -E "(INSERT INTO|UPDATE.*SET|DELETE FROM|UPSERT|ON CONFLICT|CREATE TABLE|ALTER TABLE|DROP TABLE|TRUNCATE)" .
```

### Counts

| Metric | Count |
|---|---|
| Total Python files in repo | **374** |
| Python files with DB client import (psycopg2/asyncpg/sqlalchemy) | **68** |
| Python files with execute/query method calls | **125** |
| Python files with SQL write keywords in code | **34** |
| Python files with confirmed DB write capability (after analysis) | **24** |
| Python files with indirect/possible DB write | **8** |
| Python files that are test fixtures only | **21** |
| Python files with no DB connection (static scan / read-only) | **37** |
| Python files in legacy archive (excluded) | **14** |

### Exclusions

| Category | Count | Reason |
|---|---|---|
| `archive_vault_2026/legacy_v446/*.py` | 14 | Legacy archive, not active. These contain historical training/prediction scripts with psycopg2 imports but are preserved for reference only. |
| `tests/Z_LEGACY_ARCHIVE_PRE_V4.46.8/*.py` | 13 | Legacy test archive, pre-v4.46.8. Not active. |
| FotMob `*_no_write_check.py` / `*_no_write.py` / `*_no_write_report.py` | ~50 | Static analysis / planning scripts with no DB client. Many contain `_no_write_` in filename as explicit safety marker. |
| `scripts/devops/pr_body_check.py` etc. | 3 | PR validation scripts — no DB connection. |

## SQL and migration candidate inventory

### Scan methodology

```
# Find all SQL files
find . -name "*.sql" -not -path "./.git/*" -not -path "./node_modules/*"

# Find SQL files with DDL
grep -rl --include="*.sql" -E "(CREATE TABLE|ALTER TABLE|DROP TABLE|TRUNCATE|CREATE INDEX|CREATE DATABASE|DROP DATABASE|GRANT|REVOKE)" .

# Find SQL files with DML
grep -rl --include="*.sql" -E "(INSERT INTO|UPDATE.*SET|DELETE FROM|UPSERT|ON CONFLICT)" .
```

### Counts

| Metric | Count |
|---|---|
| Total SQL files in repo | **18** |
| SQL files with DDL (CREATE/ALTER/DROP/GRANT) | **17** |
| SQL files with DML (INSERT/UPDATE/DELETE) | **3** |
| SQL files with COPY operator | **0** |
| Alembic migration Python files | **3** (versions) + 1 (env.py) |
| Flyway-style migration SQL files | **13** |
| Docker init SQL files | **2** |
| Maintenance migration SQL files | **2** |
| Report/example SQL files | **1** |

## Python classification results

### Classification categories

| Category | Definition |
|---|---|
| `python_confirmed_write_path_needs_guard` | Has DB client + executable INSERT/UPDATE/DELETE/DDL in code; no Python guard equivalent |
| `python_indirect_write_path_needs_guard` | Has DB client; write may be through ORM/repository layer; needs guard |
| `python_read_only_with_wrapper` | Has DB client but only SELECT queries; has explicit read-only wrapper or safety check |
| `python_read_only_no_write_evidence` | Has DB client but only SELECT queries detected; no write SQL in executable code |
| `python_no_db_connection` | No DB client import; no DB connection creation |
| `python_static_scan_only` | Scans other files for DB write patterns; does not execute SQL itself |
| `python_test_fixture_only` | Test file that connects to test DB; not a production write path |
| `python_needs_manual_review` | Ambiguous signals; requires deeper analysis |

### Detailed Classification

#### Category 1: python_confirmed_write_path_needs_guard (14 files)

These files have confirmed DB client import + executable INSERT/UPDATE/DELETE/DDL in code
with NO Python guard equivalent (no `assertDbWriteAllowed`, no dry-run default, no env gate).

| # | Path | DB Client | Write Evidence | Dry-Run? | Guard? | Risk |
|---|---|---|---|---|---|---|
| 1 | `src/database/schema_manager.py` | psycopg2 | CREATE TABLE, ALTER TABLE, DROP TRIGGER, INSERT, UPDATE, execute_values bulk insert | No | No | **HIGH** — Schema DDL + data DML, no gate |
| 2 | `src/database/sql_store.py` | psycopg2 (via pool) | INSERT INTO matches, INSERT INTO raw_match_data, INSERT INTO matches_mapping, UPDATE matches, all with ON CONFLICT DO UPDATE | No | No | **HIGH** — Core data write store, no gate |
| 3 | `src/database/match_repository.py` | psycopg2 | INSERT INTO matches_mapping, ON CONFLICT DO UPDATE, commit, rollback | No | No | **HIGH** — Match data write repository |
| 4 | `src/database/oddsportal_db_manager.py` | psycopg2 (via pool) | INSERT/UPDATE for oddsportal mapping data | No | No | **HIGH** — Odds data write |
| 5 | `src/database/collector_repository.py` | asyncpg (via DatabasePool) | Data collection INSERT operations | No | No | **HIGH** — Data collector write path |
| 6 | `src/database/sync_db_pool.py` | psycopg2 | Connection pool with write capability (provides connections to all writers) | No | No | **MEDIUM** — Infrastructure, not direct writer |
| 7 | `src/database/db_pool.py` | asyncpg | Connection pool with write capability | No | No | **MEDIUM** — Infrastructure, not direct writer |
| 8 | `src/data/streaming/streaming_db_writer.py` | pandas + DatabasePool | DataFrame.to_sql() for streaming data writes | No | No | **HIGH** — Streaming DB writer |
| 9 | `src/core/database/odds_injector.py` | (via repository) | Odds data injection; has dry_run references but uncertain default | Has dry_run params | No | **MEDIUM** — Has dry-run but no gate |
| 10 | `scripts/maintenance/database_detox.py` | psycopg2 | Database cleanup with DELETE/UPDATE operations | No | No | **HIGH** — Destructive maintenance script |
| 11 | `scripts/maintenance/reset_l2_collection.py` | psycopg2 | L2 data reset; has dry_run refs but default uncertain | Has dry_run refs | No | **HIGH** — Destructive reset script |
| 12 | `scripts/maintenance/odds_integrity_guard.py` | (via config) | Odds integrity check with possible corrective writes | No | No | **MEDIUM** — Integrity guard may write |
| 13 | `scripts/maintenance/integrity_guard.py` | psycopg2 | General integrity guard with possible corrective writes | No | No | **MEDIUM** — Integrity guard may write |
| 14 | `scripts/ops/fotmob_registry_seed_dev_execution.py` | psycopg2 | FotMob registry seed INSERT; has --require-dev-db flag but no env gate | Has --require-dev-db | No | **HIGH** — Seed execution with DEV guard only |

#### Category 2: python_indirect_write_path_needs_guard (8 files)

These files have DB client imports and may perform writes through repository/ORM layers,
but the write path is indirect or conditional.

| # | Path | DB Client | Write Evidence | Dry-Run? | Guard? | Risk |
|---|---|---|---|---|---|---|
| 15 | `src/services/match_aligner.py` | (via repository) | May trigger match alignment writes via MatchRepository | Unknown | No | **MEDIUM** — Indirect via repository |
| 16 | `src/services/match_linker.py` | (via repository) | May trigger match linking writes via MatchRepository | Unknown | No | **MEDIUM** — Indirect via repository |
| 17 | `src/services/match_data_service.py` | (via config) | Match data service; may write via repository | Unknown | No | **MEDIUM** — Indirect via repository |
| 18 | `src/services/league_router.py` | (via config) | League routing; may write via repository | Unknown | No | **LOW** — Routing logic, unlikely direct write |
| 19 | `src/api/collectors/odds_api_client_v38.py` | (via config) | API client for odds collection; may write via collector | No | No | **LOW** — API client, write via collector |
| 20 | `scripts/maintenance/reprocess_failed_matches.py` | (via config) | Reprocess failed matches; has dry_run refs | Has dry_run refs | No | **MEDIUM** — Has dry-run refs |
| 21 | `scripts/maintenance/clean_corrupt_l2.py` | psycopg2 | Clean corrupt L2 data; has dry_run refs | Has dry_run refs | No | **MEDIUM** — Has dry-run refs |
| 22 | `scripts/maintenance/fix_zombie_matches.py` | psycopg2 | Fix zombie matches; has dry_run refs | Has dry_run refs | No | **MEDIUM** — Has dry-run refs |

#### Category 3: python_read_only_no_write_evidence (7 files)

These files import DB clients but only execute SELECT queries. No INSERT/UPDATE/DELETE/DDL
found in executable code.

| # | Path | Evidence |
|---|---|---|
| 23 | `scripts/maintenance/show_today_summary.py` | SELECT-only; read-only dashboard |
| 24 | `scripts/maintenance/monitor_war_room.py` | SELECT-only monitoring queries |
| 25 | `scripts/maintenance/check_system_health.py` | Health check queries; likely SELECT-only |
| 26 | `scripts/ops/fotmob_match_id_discovery_db_dry_run.py` | Has psycopg2 but dry_run context; SELECT for match ID discovery |
| 27 | `scripts/ops/fotmob_target_selection_db_dry_run.py` | Has psycopg2 but dry_run context; SELECT for target selection |
| 28 | `scripts/ops/fotmob_one_day_live_fetch_no_raw_write.py` | Has psycopg2 but filename says "no_raw_write"; shallow DB reads |
| 29 | `scripts/model_training/train_baseline_v1.py` | Has psycopg2 for reading training data; no write SQL detected |

#### Category 4: python_read_only_with_wrapper (2 files)

These files have explicit read-only wrappers or safety guards in Python.

| # | Path | Evidence |
|---|---|---|
| 30 | `src/database/repositories/prediction_repo.py` | Read-only prediction query repository |
| 31 | `src/api/health.py` | Health check endpoint; read-only DB ping |

#### Category 5: python_no_db_connection (10 files)

These files have NO DB client import and NO DB connection creation. SQL keywords found
are in comments, documentation strings, or policy descriptions — not executable code.

| # | Path | Evidence |
|---|---|---|
| 32 | `scripts/ops/ai_workflow_gate.py` | Static enforcement scanner; no DB client. SQL keywords are in regex patterns for scanning OTHER files. |
| 33 | `scripts/ops/_registry_seed_sql_preview.py` | Generates SQL preview text; does not execute SQL. |
| 34 | `scripts/ops/predict_pipeline.py` | Prediction pipeline orchestrator; no DB client. |
| 35 | `scripts/ops/titan_cruise_control.py` | Cruise control orchestrator; no direct DB client. |
| 36 | `scripts/ops/train_model.py` | ML training with pandas/xgboost; no direct DB client. |
| 37 | `scripts/model_training/backtest_v1.py` | Backtest with sklearn/xgboost; no direct DB client. |
| 38 | `scripts/model_artifacts/check_model_artifacts.py` | File-based model artifact checker; no DB. |
| 39 | `scripts/ops/fotmob_safe_parser_schema_reuse_plan_no_write.py` | Planning document; no DB client. |
| 40 | `scripts/ops/documentation_governance_check.py` | Doc checker; no DB. |
| 41 | `scripts/tools/diagnose_data_quality.py` | Data quality diagnosis; no direct DB client detected. |

#### Category 6: python_static_scan_only (2 files)

These files scan OTHER files for DB write patterns but do not execute SQL themselves.

| # | Path | Evidence |
|---|---|---|
| 42 | `scripts/ops/helpers/db_write_guard_advisory_check.py` | Calls JS scanner via subprocess; no direct DB. |
| 43 | `scripts/maintenance/archives/check_data_status.py` | Archive check script; static data analysis. |

#### Category 7: python_test_fixture_only (21 files)

These are test files that may connect to a test database. They are not production write paths.

| # | Path |
|---|---|
| 44 | `tests/conftest.py` |
| 45 | `tests/integration/docker_connectivity_check.py` |
| 46 | `tests/integration/docker_smoke_test.py` |
| 47 | `tests/integration/docker_integration_report.py` |
| 48 | `tests/unit/BridgeRadar_V55.test.py` |
| 49 | `tests/unit/config_package_test.py` |
| 50 | `tests/unit/fotmob_raw_json_long_run_collector_dry_run.test.py` |
| 51 | `tests/unit/fotmob_raw_json_long_run_collector_dry_run_review_check.test.py` |
| 52 | `tests/unit/fotmob_registry_seed_dry_run.test.py` |
| 53 | `tests/unit/fotmob_registry_seed_dry_run_review_check.test.py` |
| 54 | `tests/unit/test_ai_workflow_gate.py` |
| 55 | `tests/unit/test_ai_workflow_gate_enforcement.py` |
| 56 | `tests/unit/test_audit_fotmob_retained_quality_guards.py` |
| 57 | `tests/unit/test_documentation_governance_check.py` |
| 58 | `tests/unit/test_fotmob_raw_parser_contract.py` |
| 59 | `tests/unit/test_n3_live_fotmob_retain_guards.py` |
| 60 | `tests/unit/test_pr_body_check.py` |
| 61 | `tests/unit/test_pr_merge_preflight.py` |
| 62 | `tests/unit/test_pr_post_merge_check.py` |
| 63 | `tests/unit/test_pr_post_merge_check_protected.py` |
| 64 | `tests/unit/test_single_live_fotmob_retain_guards.py` |

#### Category 8: python_needs_manual_review (5 files)

These files have ambiguous signals that require deeper human analysis.

| # | Path | Reason |
|---|---|---|
| 65 | `scripts/maintenance/reprocess_from_local.py` | Has DB config import; write path unclear from static scan |
| 66 | `scripts/maintenance/fotmob_historical_backfill.py` | Historical backfill; may have write capability |
| 67 | `src/api/monitoring/prometheus_metrics.py` | Monitoring with DB queries; may have write for metrics storage |
| 68 | `src/api/monitoring.py` | API monitoring; DB access pattern unclear |
| 69 | `scripts/tools/diagnose_diagnostic.py` | Diagnostic tool; may have DB write for fix operations |

### Python classification summary

| Category | Count |
|---|---|
| python_confirmed_write_path_needs_guard | **14** |
| python_indirect_write_path_needs_guard | **8** |
| python_read_only_no_write_evidence | **7** |
| python_read_only_with_wrapper | **2** |
| python_no_db_connection | **10** |
| python_static_scan_only | **2** |
| python_test_fixture_only | **21** |
| python_needs_manual_review | **5** |
| **Total classified** | **69** |

## SQL and migration classification results

### Classification categories

| Category | Definition |
|---|---|
| `sql_schema_definition` | DDL-only migration; defines schema structure |
| `sql_allowed_migration_candidate` | Contains DML that is legitimate for a migration (e.g., data backfill as part of schema change) |
| `sql_destructive_migration_needs_policy` | Contains DROP, TRUNCATE, or DELETE that could destroy data |
| `sql_seed_or_data_write_needs_gate` | Contains seed data or data write that needs runtime gate |
| `sql_test_fixture_only` | Used only by test infrastructure |
| `sql_docs_or_example_only` | Documentation or generated preview; not executed |
| `sql_needs_manual_review` | Ambiguous purpose; requires deeper analysis |

### Detailed Classification

#### Flyway-style Migrations (database/migrations/)

| # | Path | DDL | DML | Destructive? | Classification | Notes |
|---|---|---|---|---|---|---|
| 1 | `database/migrations/V6.5__hardened_matches_schema.sql` | ALTER TABLE, CREATE INDEX, CREATE TRIGGER | UPDATE (data migration) | No | `sql_allowed_migration_candidate` | Schema hardening with data migration |
| 2 | `database/migrations/V6.6__hardened_l2_raw_storage.sql` | ALTER TABLE | None | No | `sql_schema_definition` | L2 storage hardening |
| 3 | `database/migrations/V12.2__add_matches_pipeline_status.sql` | ALTER TABLE | UPDATE (backfill) | No | `sql_allowed_migration_candidate` | Pipeline status field with data backfill |
| 4 | `database/migrations/V12.3__expand_matches_pipeline_status_for_recon.sql` | ALTER TABLE | UPDATE (backfill) | No | `sql_allowed_migration_candidate` | Pipeline status expansion |
| 5 | `database/migrations/V12.4__create_matches_oddsportal_mapping.sql` | CREATE TABLE, CREATE INDEX | None | No | `sql_schema_definition` | New mapping table |
| 6 | `database/migrations/V12.5__create_bookmaker_odds_history.sql` | CREATE TABLE, CREATE INDEX | None | No | `sql_schema_definition` | New odds history table |
| 7 | `database/migrations/V12.6__allow_numeric_fotmob_ids_in_raw_match_data.sql` | ALTER TABLE | None | No | `sql_schema_definition` | Type change |
| 8 | `database/migrations/V12.7__add_tactical_stats_to_matches.sql` | ALTER TABLE | None | No | `sql_schema_definition` | New columns |
| 9 | `database/migrations/V12.8__add_alignment_meta_to_bookmaker_odds_history.sql` | ALTER TABLE | None | No | `sql_schema_definition` | New columns |
| 10 | `database/migrations/V26.4__create_l3_features_table.sql` | CREATE TABLE | None | No | `sql_schema_definition` | New features table |
| 11 | `database/migrations/V26.5__create_fotmob_raw_match_payloads.sql` | CREATE TABLE | None | No | `sql_schema_definition` | New raw payloads table |
| 12 | `database/migrations/V26.6__create_football_calendar_target_registry.sql` | CREATE TABLE | None | No | `sql_schema_definition` | New registry table |
| 13 | `database/migrations/V26.7__add_matches_labeling_governance_columns.sql` | ALTER TABLE | None | No | `sql_schema_definition` | New governance columns |

#### Docker Init SQL

| # | Path | DDL | DML | Destructive? | Classification | Notes |
|---|---|---|---|---|---|---|
| 14 | `deploy/docker/init_db.sql` | CREATE TABLE, CREATE EXTENSION, CREATE INDEX | INSERT (seed data) | No (IF NOT EXISTS) | `sql_seed_or_data_write_needs_gate` | Docker dev environment init. Contains full schema + seed data. Should only run in dev Docker context. |
| 15 | `deploy/docker/init_claude_reader.sql` | CREATE USER, GRANT, ALTER DEFAULT PRIVILEGES | None | No | `sql_schema_definition` | Creates read-only DB user for MCP. Legitimate infrastructure SQL. |

#### Maintenance Migrations

| # | Path | DDL | DML | Destructive? | Classification | Notes |
|---|---|---|---|---|---|---|
| 16 | `scripts/maintenance/migrations/V6_0_add_backfill_progress.sql` | ALTER TABLE | None | No | `sql_allowed_migration_candidate` | Maintenance migration for backfill tracking |
| 17 | `scripts/maintenance/migrations/V6_0_add_market_sentiment.sql` | ALTER TABLE | None | No | `sql_allowed_migration_candidate` | Maintenance migration for market sentiment |

#### Report / Example SQL

| # | Path | DDL | DML | Destructive? | Classification | Notes |
|---|---|---|---|---|---|---|
| 18 | `docs/_reports/FOTMOB_REGISTRY_SEED_DRY_RUN_SQL_PREVIEW.sql` | CREATE TABLE IF NOT EXISTS | INSERT with ON CONFLICT | No | `sql_docs_or_example_only` | Generated SQL preview from dry-run. Not a migration. Not executed automatically. |

### SQL and migration classification summary

| Category | Count |
|---|---|
| sql_schema_definition | **10** |
| sql_allowed_migration_candidate | **5** |
| sql_seed_or_data_write_needs_gate | **1** |
| sql_destructive_migration_needs_policy | **0** |
| sql_test_fixture_only | **0** |
| sql_docs_or_example_only | **1** |
| sql_needs_manual_review | **1** (V6.5 has UPDATE DML in migration — needs policy review) |

### Alembic Migration Python Files

| # | Path | Classification | Notes |
|---|---|---|---|
| A1 | `src/database/migrations/env.py` | `python_confirmed_write_path_needs_guard` | Alembic environment; orchestrates migrations at runtime. Can execute arbitrary DDL/DML. |
| A2 | `src/database/migrations/versions/001_initial_migration.py` | `sql_schema_definition` | Initial schema creation via Alembic |
| A3 | `src/database/migrations/versions/002_v105_metrics_multi_source_data.py` | `sql_allowed_migration_candidate` | Metrics schema migration |
| A4 | `src/database/migrations/versions/003_v145_l2_data_version.py` | `sql_allowed_migration_candidate` | L2 data version migration (contains ALTER TABLE) |

## Enforcement design options

### Option 1: Python assert_db_write_allowed() equivalent

**Description:** Create a Python equivalent of `assertDbWriteAllowed()` that checks the same
environment variables (ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, DRY_RUN, table-level gates)
and blocks production-like DB hosts.

**Pros:**
- Direct equivalent to proven JS pattern
- Same env var gating model
- Easy to understand and audit
- Can be added incrementally to each Python write path

**Cons:**
- Requires modifying each Python write entrypoint
- Python scripts use different DB connection patterns (psycopg2 direct, asyncpg pool,
  SQLAlchemy ORM, pandas to_sql) — a single helper may need variants
- Need to maintain both JS and Python versions of the same logic

### Option 2: Static scanner only (Python keyword scanner)

**Description:** Add Python file scanning to the JS static enforcement scanner (or create a
Python equivalent) that detects DB write keywords in Python files and flags unguarded files.

**Pros:**
- No runtime behavior change
- Can be added to CI as changed-files enforcement
- Catches new/modified unguarded Python files

**Cons:**
- Static scan has higher false positive rate for Python (many patterns like `.execute()` in
  non-DB contexts)
- Does not protect existing files — only new/modified
- No runtime protection

### Option 3: DB role / permission model

**Description:** Enforce write restrictions at the database level using PostgreSQL roles.
Application services get read-only roles by default; write-capable roles require explicit
authorization.

**Pros:**
- Database-level enforcement — cannot be bypassed in application code
- Works for all languages (JS, Python, SQL)
- Industry-standard approach

**Cons:**
- Requires DBA-level changes
- May break existing functionality during rollout
- Needs careful service-by-service migration
- Separate task (runtime_db_role_permission_review_phase1)

### Option 4: CI policy gate for changed files

**Description:** Extend the existing `ai_workflow_gate.py` changed-files enforcement to cover
Python files and SQL migration files, similar to what currently exists for JS files.

**Pros:**
- Leverages existing CI infrastructure
- Can have Python-specific keyword detection
- Can have migration-specific allowlist

**Cons:**
- Static only — no runtime protection
- Only catches new/modified files
- Python keyword detection is harder (more false positives)

## Recommended enforcement model

**Recommended: Hybrid approach combining Options 1 + 2 + 4, phased over multiple implementation phases.**

### Phase 2A: Python static scanner (Option 2 + 4) ✅ COMPLETED

- **Status:** Implemented by `python_sql_migration_enforcement_implementation_phase2A` (PR #1597).
- Scanner: `scripts/ops/python_db_write_static_enforcement.py` — scans `.py` files for DB write risk keywords, supports JSON output, allowlist, changed-files mode, full-scan mode, comment/docstring awareness
- Allowlist: `config/python_db_write_allowlist.json` — 27 historical baseline entries (14 confirmed + 8 indirect + 5 manual review) with complete metadata
- Gate integration: `check_python_db_write_enforcement()` in `scripts/ops/ai_workflow_gate.py` — new/modified Python files with DB write signals fail CI unless in allowlist
- Historical Python files in allowlist pass with baseline status; new/modified files not in allowlist get hard fail

### Phase 2B: SQL migration policy scanner (Option 4) ✅ COMPLETED

- **Status:** Implemented by `sql_migration_policy_implementation_phase2B` (PR #1599).
- Scanner: `scripts/ops/sql_migration_policy_static_enforcement.py` — detects DDL, DML, destructive, privilege, and Alembic API signals in SQL/migration files
- Allowlist: `config/sql_migration_policy_allowlist.json` — 22 historical baseline entries with allowed/disallowed operations
- Gate helper: `scripts/ops/helpers/sql_migration_policy_enforcement_check.py`
- Gate integration: check #10 in `scripts/ops/ai_workflow_gate.py` main()
- Destructive SQL policy: any new file with DROP DATABASE, DROP TABLE, TRUNCATE, etc. always fails gate (even if allowlisted)
- Changed-files enforcement: new/modified SQL/migration files with DML/destructive/privilege signals fail CI unless in allowlist with complete metadata

### Phase 2C: Python guard helper (Option 1) — BATCH1+BATCH2+BATCH3 COMPLETED

- Create `scripts/ops/helpers/python_db_write_guard.py` — Python equivalent of the JS guard ✅ COMPLETED
- Support env-var gate model matching JS guard (ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, DRY_RUN, table-level gates, production host hard block) ✅ COMPLETED
- Batch1 guarded 3 of 14 highest-risk Python confirmed write paths:
  1. `src/database/match_repository.py` — INSERT/UPDATE on matches_mapping
  2. `scripts/maintenance/database_detox.py` — ALTER/UPDATE on prematch_features
  3. `scripts/maintenance/reset_l2_collection.py` — TRUNCATE on raw_match_data, collection_audit_logs
- Batch2 guarded 3 more confirmed write paths (6 of 14 total):
  4. `src/database/schema_manager.py` — CREATE/ALTER on match_features_training, matches, raw_match_data
  5. `src/database/oddsportal_db_manager.py` — UPSERT on matches_mapping
  6. `scripts/ops/fotmob_registry_seed_dev_execution.py` — INSERT on 7 football_* registry tables
- Batch3 guarded 3 more confirmed write paths (9 of 14 total):
  7. `src/core/database/odds_injector.py` — UPDATE on matches (l3_odds_data quality-based UPSERT)
  8. `src/database/collector_repository.py` — UPSERT on matches
  9. `src/data/streaming/streaming_db_writer.py` — INSERT/UPSERT on dynamic tables (matches, odds, etc.)
- **5 remaining confirmed write paths still pending (Phase2C batch4) — all later_needs_design**
- **8 indirect write paths NOT yet processed**
- **5 manual review candidates NOT yet processed**
- **5 later_needs_design identified:** odds_integrity_guard.py (reads-only), integrity_guard.py (SELECT-only), sql_store.py (SQL string constants only), sync_db_pool.py (infrastructure), db_pool.py (infrastructure)
- Lower-risk and indirect paths to follow incrementally in batch4+

### Phase 2D: Manual review of needs_manual_review files (5 files)

- Review the 5 `python_needs_manual_review` files
- Reclassify based on deeper analysis

### Phase 2E: DB role / permission model (Option 3 — separate task)

- Already planned as `runtime_db_role_permission_review_phase1`
- Should follow after Python/SQL enforcement is designed and initial guards are in place

## CI integration design

### Changed-files enforcement for Python

```
ai_workflow_gate.py detects changed Python files → 
  python_db_write_scanner.py scans for DB write keywords →
    if confirmed write path and no guard:
      if new/modified file: HARD FAIL
      if historical file: ADVISORY WARNING
```

### Changed-files enforcement for SQL/migration

```
ai_workflow_gate.py detects changed SQL/migration files →
  sql_migration_policy_scanner.py checks for:
    - Destructive operations (HARD FAIL without policy gate)
    - DDL without migration metadata (WARNING)
    - DML in non-migration SQL files (HARD FAIL without allowlist)
```

### Allowlist structure

A `python_db_write_allowlist.json` and `sql_migration_allowlist.json` should be created,
analogous to the existing `db_write_guard_legacy_allowlist.json` for JS files.

Each entry must include:
- `path`: file path
- `category`: classification category
- `reason`: why it is exempt or classified as-is
- `reviewed_at`: review date
- `future_action`: what follow-up is needed

## Implementation candidates

In priority order for follow-up implementation phases:

### Priority 1 (HIGH): Core DB write paths

| # | Path | Category | Target Phase |
|---|---|---|---|
| 1 | `src/database/schema_manager.py` | python_confirmed_write_path_needs_guard | Phase 2C |
| 2 | `src/database/sql_store.py` | python_confirmed_write_path_needs_guard | Phase 2C |
| 3 | `src/database/match_repository.py` | python_confirmed_write_path_needs_guard | Phase 2C |
| 4 | `src/database/oddsportal_db_manager.py` | python_confirmed_write_path_needs_guard | Phase 2C |
| 5 | `src/database/collector_repository.py` | python_confirmed_write_path_needs_guard | Phase 2C |
| 6 | `src/data/streaming/streaming_db_writer.py` | python_confirmed_write_path_needs_guard | Phase 2C |
| 7 | `scripts/ops/fotmob_registry_seed_dev_execution.py` | python_confirmed_write_path_needs_guard | Phase 2C |
| 8 | `src/database/migrations/env.py` | python_confirmed_write_path_needs_guard | Phase 2B |

### Priority 2 (MEDIUM): Maintenance scripts

| # | Path | Category | Target Phase |
|---|---|---|---|
| 9 | `scripts/maintenance/database_detox.py` | python_confirmed_write_path_needs_guard | Phase 2C |
| 10 | `scripts/maintenance/reset_l2_collection.py` | python_confirmed_write_path_needs_guard | Phase 2C |
| 11 | `scripts/maintenance/odds_integrity_guard.py` | python_confirmed_write_path_needs_guard | Phase 2C |
| 12 | `scripts/maintenance/integrity_guard.py` | python_confirmed_write_path_needs_guard | Phase 2C |
| 13 | `scripts/maintenance/reprocess_failed_matches.py` | python_indirect_write_path_needs_guard | Phase 2C |
| 14 | `scripts/maintenance/clean_corrupt_l2.py` | python_indirect_write_path_needs_guard | Phase 2C |
| 15 | `scripts/maintenance/fix_zombie_matches.py` | python_indirect_write_path_needs_guard | Phase 2C |

### Priority 3 (LOW): Infrastructure and indirect paths

| # | Path | Category | Target Phase |
|---|---|---|---|
| 16 | `src/database/sync_db_pool.py` | python_confirmed_write_path_needs_guard | Phase 2C |
| 17 | `src/database/db_pool.py` | python_confirmed_write_path_needs_guard | Phase 2C |
| 18 | `src/core/database/odds_injector.py` | python_confirmed_write_path_needs_guard | Phase 2C |
| 19-24 | 6 indirect service paths | python_indirect_write_path_needs_guard | Phase 2D |

### Migration/SQL candidates

| # | Item | Category | Target Phase |
|---|---|---|---|
| M1 | `deploy/docker/init_db.sql` | sql_seed_or_data_write_needs_gate | Phase 2B |
| M2 | SQL migration policy scanner | New CI infrastructure | Phase 2B |
| M3 | Migration allowlist | New configuration | Phase 2B |

## Manual review candidates

The following 5 Python files need deeper manual review to determine their exact DB write
status. Evidence is insufficient from static scan alone.

| # | Path | Reason for manual review |
|---|---|---|
| MR1 | `scripts/maintenance/reprocess_from_local.py` | Has DB config import; actual write path unclear without tracing |
| MR2 | `scripts/maintenance/fotmob_historical_backfill.py` | Historical backfill; may INSERT historical data |
| MR3 | `src/api/monitoring/prometheus_metrics.py` | May write metrics to DB or only expose Prometheus endpoint |
| MR4 | `src/api/monitoring.py` | DB access pattern unclear; may be read-only health checks |
| MR5 | `scripts/tools/diagnose_diagnostic.py` | Diagnostic tool; may have write operations for auto-fix |

## Risks and unknowns

### Known risks

1. **No Python guard equivalent exists today.** Any Python script with psycopg2 can write to
   the database without passing through any gate. The production-like DB host hard block is
   only enforced in the JS guard helper.

2. **SQL migration execution is unguarded.** Alembic migrations (`src/database/migrations/env.py`)
   and Flyway migrations (`database/migrations/*.sql`) can execute arbitrary DDL/DML with no
   runtime gate. Migration execution is not covered by the JS guard.

3. **Docker init SQL runs with full privileges.** `deploy/docker/init_db.sql` creates the
   full schema and seed data. If accidentally run against a non-dev database, it would
   create tables and insert data.

4. **Python maintenance scripts have destructive capability.** `database_detox.py`,
   `reset_l2_collection.py`, and similar scripts have DELETE/TRUNCATE capability with no
   runtime guard.

5. **14 confirmed Python write paths have no guard.** These are production-capable DB write
   entrypoints that bypass the entire SC-002 JS enforcement framework.

6. **Static analysis may miss dynamic imports.** Python's dynamic import mechanisms
   (`importlib`, `__import__`, dynamic `getattr`) could hide DB client usage from static
   scans.

### Static analysis limitations

- This analysis reads source code but does not trace runtime execution paths
- Dynamic imports, eval(), exec(), and runtime code generation could bypass detection
- SQL keywords in f-strings or dynamically constructed queries may be missed
- Files that import DB connection from wrapper modules may appear safe but have write
  capability through the wrapper
- The `ddtrace` / Datadog tracing may intercept DB calls in ways not visible in static code

## Explicit non-goals

This design phase explicitly does NOT:

- Implement any Python guard, scanner, or enforcement
- Run any Python target script
- Execute any SQL or migration
- Connect to any database
- Perform any real DB write
- Run scraper / browser / Playwright
- Train or expand data
- Change runtime behavior of any kind
- Create a Python equivalent of `assertDbWriteAllowed()`
- Add migration policy enforcement to CI
- Review the DB role / permission model
- Close SC-002
- Unlock training, data expansion, or real DB write
- Classify files without evidence (all uncertain files are marked `needs_manual_review`)

## SC-002 status impact

- **SC-002 remains partial mitigation only.**
- **Python and SQL/migration enforcement design is complete.**
- **Python Phase2A static scanner completed. Phase2B SQL/migration scanner completed.**
- **Python Phase2C batch1 runtime guard completed: 3 of 14 confirmed write paths guarded.**
- **Python Phase2C batch2 runtime guard completed: 3 more confirmed write paths guarded (6 of 14 total).**
- **Python Phase2C batch3 runtime guard completed: 3 more confirmed write paths guarded (9 of 14 total).**
- **24 Python files identified as confirmed or indirect write paths needing guard.**
- **5 confirmed Python write paths still pending runtime guard (all later_needs_design).**
- **8 indirect write paths still pending design + guard.**
- **5 Python files need manual review.**
- **14 SQL migration files classified; 1 seed SQL needs gate; 0 destructive migrations found.**
- **1 Alembic env.py confirmed write path needing guard.**
- **No runtime behavior changed. No target script executed. No DB connection. No real DB write.**
- **No scraper/browser/Playwright. No training/data expansion/schema migration.**
- Training, data expansion, real DB write remain BLOCKED.

## Next recommended task

Based on the current implementation status, the recommended next task is:

**`python_runtime_guard_implementation_phase2C_batch4`** — Continue Python runtime guard
for the remaining 5 confirmed write paths (all later_needs_design). This should:

1. Design guard approaches for the 5 later_needs_design files before implementation
2. Consider indirect write paths or manual review candidates as alternatives
3. Update allowlist classifications as each path is guarded
4. NOT process indirect write paths or manual review candidates unless explicitly scoped
5. NOT execute any Python target script
6. NOT connect to DB

Do not start automatically. Recommended next task only after user confirmation.
