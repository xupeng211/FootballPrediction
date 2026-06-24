# SC-002 Manual Review Phase2D

- lifecycle: permanent
- owner: project governance
- created: 2026-06-25
- task: python_manual_review_phase2d
- source_doc: docs/SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md
- allowlist: config/python_db_write_allowlist.json

## Summary

Static manual review of all 5 remaining `historical_python_needs_manual_review` entries
in `config/python_db_write_allowlist.json`. This task is **static classification only** —
no runtime guard implementation, no DB connection, no real DB write.

**Key finding: 2 of 5 "manual review" paths are confirmed DIRECT write paths** that
have executable INSERT/UPDATE with `conn.commit()`. Both need runtime guard in a future
implementation task. The remaining 3 are safe to reclassify (2 false positives, 1 read-only).

## Classification Summary

| # | Path | Current Classification | New Classification | Write? | Risk |
|---|---|---|---|---|---|
| 1 | `scripts/maintenance/reprocess_from_local.py` | needs_manual_review | **manual_confirmed_write_needs_guard** | UPDATE + commit | HIGH |
| 2 | `scripts/maintenance/fotmob_historical_backfill.py` | needs_manual_review | **manual_false_positive_candidate** | None (deprecated) | NONE |
| 3 | `src/api/monitoring/prometheus_metrics.py` | needs_manual_review | **manual_confirmed_write_needs_guard** | INSERT + commit | MEDIUM |
| 4 | `src/api/monitoring.py` | needs_manual_review | **manual_read_only_candidate** | None (SELECT only) | NONE |
| 5 | `scripts/tools/diagnose_diagnostic.py` | needs_manual_review | **manual_false_positive_candidate** | None (broken file) | NONE |

**Totals:**
- `manual_confirmed_write_needs_guard`: **2** (reprocess_from_local.py, prometheus_metrics.py)
- `manual_read_only_candidate`: **1** (monitoring.py)
- `manual_false_positive_candidate`: **2** (fotmob_historical_backfill.py, diagnose_diagnostic.py)
- `manual_confirmed_write_already_guarded`: **0**
- `manual_needs_design`: **0**
- `manual_unknown_needs_followup`: **0**

## Per-File Analysis

### 1. `scripts/maintenance/reprocess_from_local.py` → manual_confirmed_write_needs_guard

- **DB driver:** psycopg2 (direct import, own `get_db_connection()`)
- **Write methods:** `backfill_features()` — UPDATE matches SET l2_extracted_features with explicit `conn.commit()`
- **Write operations:** UPDATE
- **Target tables:** `matches`
- **Read methods:** `fetch_matches_with_raw_json()` (SELECT), `extract_features_from_json()` (no DB)
- **Guard:** NONE — no `assert_db_write_allowed()` or equivalent
- **dry_run flag:** No
- **Guard recommendation:** In `backfill_features()` before `cur.execute(UPDATE...)` and `conn.commit()`. Guard tables: `['matches']`. Guard operations: `['UPDATE']`.
- **Note:** Similar to `reprocess_failed_matches.py` (which was guarded in indirect_write_path_guard_phase2). This script also does offline feature backfill from local raw JSON.

### 2. `scripts/maintenance/fotmob_historical_backfill.py` → manual_false_positive_candidate

- **DB driver:** NONE — `FotMobCoreCollector = None` (placeholder), `CollectionSentry = None`
- **DB driver import:** No psycopg2/asyncpg/sqlalchemy import anywhere in file
- **Write operations:** NONE — no INSERT/UPDATE/DELETE/CREATE/ALTER/TRUNCATE in this file
- **Commit:** NONE — no commit/execute
- **DEPRECATED status:** Explicitly marked DEPRECATED (V4.13). Core dependencies (`FotMobCoreCollector`, `CollectionSentry`) are set to `None`. `get_config_manager()` raises `NotImplementedError`. Script cannot execute.
- **dry_run flag:** Has `--dry-run` parameter but script cannot actually perform writes since collector is None.
- **Target tables:** N/A — write would happen in now-deleted `FotMobCoreCollector` class
- **Guard recommendation:** No guard needed. Reclassify as false positive. Consider removing file in a cleanup PR.

### 3. `src/api/monitoring/prometheus_metrics.py` → manual_confirmed_write_needs_guard

- **DB driver:** psycopg2 (conditional import in try/except, `DB_AVAILABLE` flag)
- **Write methods:** `DeadLetterQueue._persist_to_database()` — INSERT INTO failed_market_data with explicit `conn.commit()`
- **Write operations:** INSERT
- **Target tables:** `failed_market_data`
- **Write gating:** `self._persist_to_db = persist_to_db and DB_AVAILABLE`. Default `persist_to_db=True` — write is enabled by default. Failures silently caught (`except Exception: pass`).
- **Read-only portion:** `HarvestMetrics` class, Prometheus Counter/Gauge/Histogram — all metrics only, no DB
- **Guard:** NONE — no `assert_db_write_allowed()` or equivalent
- **dry_run flag:** No
- **Guard recommendation:** In `_persist_to_database()` before `cursor.execute(INSERT...)` and `conn.commit()`. Guard tables: `['failed_market_data']`. Guard operations: `['INSERT']`. Consider adding a parameter to disable DB persistence for dry-run scenarios.

### 4. `src/api/monitoring.py` → manual_read_only_candidate

- **DB driver:** asyncpg via `DatabasePool` (infrastructure, already classified as `infrastructure_only_needs_caller_guard`)
- **DB operations:** ALL SELECT/fetchrow/fetchval — `SELECT 1`, `SELECT COUNT(*) FROM teams/matches/predictions/pg_stat_activity`
- **Write operations:** NONE — no INSERT/UPDATE/DELETE/CREATE/ALTER/TRUNCATE
- **Commit:** NONE — no commit, no execute with DML/DDL
- **Target tables:** N/A — read-only health checks and monitoring queries
- **Guard:** N/A — no write path to guard
- **Guard recommendation:** No guard needed. Reclassify as read-only. The `DatabasePool` infrastructure is already classified appropriately, and this consumer is read-only.

### 5. `scripts/tools/diagnose_diagnostic.py` → manual_false_positive_candidate

- **DB driver:** psycopg2 appears in import but file is syntactically broken
- **Syntax state:** The file is corrupted — contains invalid Python syntax (colons instead of equals in dict, missing parens, mixed JavaScript/Node.js syntax, `const`, `=>` arrow functions, template literals, `module.exports`)
- **Executable:** No — file would fail immediately with SyntaxError
- **Write operations:** NONE executable — has `SELECT` (broken) and `INSERT`/`UPDATE`/`DELETE` are not present in any coherent form
- **Commit:** NONE — no commit anywhere
- **Guard recommendation:** No guard needed. Reclassify as false positive (broken/unparseable file). Consider removing or rewriting in a cleanup PR.

## Phase2E Implementation (python_manual_review_guard_phase2e)

- **Completed:** 2026-06-25
- **Task:** python_manual_review_guard_phase2e
- **Status:** COMPLETE — both manual review write paths now have runtime guard

| # | File | Guard Location | Operation | Table |
|---|---|---|---|---|
| 1 | `scripts/maintenance/reprocess_from_local.py` | `backfill_features()` before UPDATE | UPDATE | `matches` |
| 2 | `src/api/monitoring/prometheus_metrics.py` | `_persist_to_database()` before INSERT | INSERT | `failed_market_data` |

Guard details:
- Uses existing `helpers/python_db_write_guard.py` pattern
- All guards placed before real DB write operations
- Real DB write remains blocked unless ALLOW_DB_WRITE=yes, FINAL_DB_WRITE_CONFIRMATION=yes, table-specific gates, DRY_RUN=false

## Next Guard Candidates (Phase2D original — ALL COMPLETED in Phase2E)

| # | File | Operation | Table | Guard Location |
|---|---|---|---|---|
| 1 | `scripts/maintenance/reprocess_from_local.py` | UPDATE | matches | `backfill_features()` before `cur.execute(UPDATE...)` |
| 2 | `src/api/monitoring/prometheus_metrics.py` | INSERT | failed_market_data | `_persist_to_database()` before `cursor.execute(INSERT...)` |

## SC-002 Status After Phase2E

- SC-002 remains **partial mitigation only**.
- **17/20** Python write paths runtime guarded.
- **3 of 5** manual review candidates reclassified as safe (no guard needed).
- **2 of 5** manual review candidates now guarded in Phase2E.
- **0** manual review candidates remain — all 5 classified, 2 guarded.
- Training / data expansion / real DB write remain **blocked**.

## Non-Goals

This task is a **static review/classification** task only. It is explicitly NOT:

- Runtime guard implementation
- Execution of any Python target script
- DB connection
- Real DB write
- SQL / migration execution
- Scraper / browser / Playwright execution
- Training or data expansion
- Marking any path as `runtime_guarded` (that is for the guard implementation task)
- Claiming SC-002 is resolved or complete

## Next Recommended Task

`sc002_alembic_migration_guard` — design and implement guard for the remaining Alembic migration entry (`src/database/migrations/env.py`), the last ungarded Python write path.

Do not start automatically. Recommended next task only after user confirmation.
