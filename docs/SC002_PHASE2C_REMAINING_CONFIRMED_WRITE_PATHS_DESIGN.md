# SC-002 Phase2C Remaining Confirmed Write Paths Design

- lifecycle: permanent
- owner: project governance
- created: 2026-06-24
- task: python_confirmed_write_paths_design_phase2C_batch4
- type: design / classification — NOT runtime guard implementation
- consumer_audit: consumer_level_guard_audit_db_pool_sync_sql_store completed 2026-06-24 (see docs/SC002_CONSUMER_LEVEL_GUARD_AUDIT_DB_POOL_SYNC_SQL_STORE.md)
- consumer_audit_summary: 3 infrastructure files audited. 2 write consumers already guarded (batch3). 6 read-only. 0 unguarded write consumers. 0 dynamic/unknown. No new guards needed.

## Summary

This document provides the static design analysis and classification of the 5 remaining
confirmed Python write paths that were identified as `later_needs_design` during Phase2C
batch3 analysis. Each file was statically examined (no execution, no DB connection) to
determine its actual write capability, appropriate classification, and recommended next
step.

**Key outcomes:**
- 2 files classified as `read_only_or_select_only` — no actual DB write at runtime
- 3 files classified as `infrastructure_only_needs_caller_guard` — write capability exists
  but guard belongs at caller/consumer level, not at infrastructure level
- 0 files classified as `confirmed_direct_write_needs_guard` — none of the 5 are suitable
  for direct guard implementation without further design
- **No runtime guards were added in this task.**
- **SC-002 remains partial mitigation only.**
- **training / data expansion / real DB write remain blocked.**

## Scope

| Item | Value |
|---|---|
| Task type | design phase |
| Files analyzed | 5 remaining confirmed Python write paths |
| Runtime guard added | 0 |
| Python target scripts executed | 0 |
| DB connection | No |
| SQL / migration | No |
| Real DB write | No |
| Scraper / browser / Playwright | No |
| Training / data expansion | No |

---

## Per-File Analysis

### 1. `scripts/maintenance/odds_integrity_guard.py`

**Classification:** `read_only_or_select_only`

**Analysis:**

Static code review of the entire file reveals that all `cursor.execute()` calls are
SELECT queries only:

- `check_coverage_gaps()`: SELECT with CTE (WITH finished_matches AS ...) and LEFT JOIN
  against `matches` + `match_odds`. Read-only diagnostic query.
- `check_missing_opening()`: SELECT with JOIN on `match_odds` JOIN `matches`. Filters
  for NULL odds_home_open/odds_draw_open/odds_away_open. Read-only.
- `check_anomalies()`: SELECT with CTE calculating odds_drop percentages and market_margin
  from `match_odds` JOIN `matches`. Read-only.
- `_generate_cleanup_sql()`: **Constructs a DELETE SQL string but NEVER executes it.**
  The DELETE is output to console/rich panel as a diagnostic suggestion. No
  `cursor.execute()` for the DELETE string. This is a human-readable diagnostic, not
  an automated write path.
- `main()` has `--show-sql-only` flag that skips even the DB connection.

**Observed operations:** SELECT only (SELECT COUNT, SELECT with JOINs, SELECT with CTEs)
**Observed tables:** matches, match_odds
**DB driver:** psycopg2
**Direct write boundary:** NONE — all executes are SELECT; DELETE is print-only
**Why the original classification was "confirmed write":** The `_generate_cleanup_sql()`
method generates a DELETE SQL string, which the static scanner detected as a write signal.
However, deep analysis reveals this string is only printed for human review, never executed.

**Recommended next action:** Reclassify as read-only. Move to 
`historical_python_confirmed_write_path_read_only_candidate`. No guard needed.
If a future version adds automated cleanup execution, a new design task will be needed.

---

### 2. `scripts/maintenance/integrity_guard.py`

**Classification:** `read_only_or_select_only`

**Analysis:**

This is a data integrity diagnostic tool (TITAN V4.46.5). All database operations are
SELECT only:

- `check_alignment()`: 
  - `SELECT COUNT(*) FROM matches` (reads count)
  - `SELECT COUNT(*) FROM raw_match_data` (reads count)
  - `SELECT COUNT(*) FROM l3_features` (reads count)
  - `SELECT m.match_id, ... FROM matches m LEFT JOIN raw_match_data r ... WHERE r.match_id IS NULL` (gap detection)
  - `SELECT m.match_id, ... FROM matches m LEFT JOIN l3_features l ... WHERE l.match_id IS NULL` (gap detection)
- `generate_fix_commands()`: Prints shell commands (`npm start -- --match-ids ...`),
  NOT SQL commands. No DB interaction at all.
- `run()`: orchestrates connect → check_alignment → generate_fix_commands → close

**Observed operations:** SELECT only (SELECT COUNT, SELECT with LEFT JOIN)
**Observed tables:** matches, raw_match_data, l3_features
**DB driver:** psycopg2
**Direct write boundary:** NONE — every cursor.execute() is SELECT
**Why the original classification was "confirmed write":** The file imports psycopg2 and
has execute patterns, which the static scanner flagged. It also has a `DB_CONFIG` with
password embedded in the source (hardcoded defaults — but password defaults to '' via
env var). The "possible corrective writes" claim in the original evidence was not validated
against the actual code at classification time.

**Recommended next action:** Reclassify as read-only. Move to
`historical_python_confirmed_write_path_read_only_candidate`. No guard needed.
Consider removing hardcoded DB_CONFIG defaults in a separate cleanup PR.

---

### 3. `src/database/sql_store.py`

**Classification:** `infrastructure_only_needs_caller_guard`

**Analysis:**

This file is a SQL query string store (V4.25 "SQL 弹药库"). It defines SQL string constants
in a `SQLStore` class but contains no execution code:

- No `import psycopg2`, no `import asyncpg`, no `import sqlalchemy`
- No `connect()`, no `cursor()`, no `execute()`, no `commit()`, no `rollback()`
- No database driver of any kind

SQL strings defined (write-capable):
- `INSERT_MATCH`: INSERT INTO matches ... ON CONFLICT DO UPDATE
- `INSERT_MATCH_MAPPING`: INSERT INTO matches_mapping ... ON CONFLICT DO UPDATE
- `UPSERT_RAW_DATA`: INSERT INTO raw_match_data ... ON CONFLICT DO UPDATE
- `UPDATE_XG`: UPDATE matches SET xg_home/xg_away
- `UPDATE_STATS`: UPDATE matches SET xg/possession
- `UPDATE_L3_ODDS_DATA`: UPDATE matches SET l3_odds_data
- `UPDATE_GOLDEN_FEATURES`: UPDATE matches SET golden_features
- `MARK_HARVESTED`: UPDATE matches SET l2_harvested

SQL strings defined (read-only):
- `GET_MATCH_BY_ID`, `GET_MATCH_BY_EXTERNAL_ID`, `GET_MATCH_SEASON`, `CHECK_MATCH_EXISTS`
- `GET_ALL_MATCHES`, `GET_MATCHES_BY_SEASON`, `GET_MATCH_IDS_BY_LEAGUE`
- `COUNT_MATCHES`, `COUNT_MATCHES_BY_LEAGUE`
- `GET_UNHARVESTED_MATCHES`, `GET_UNHARVESTED_COUNT`
- `GET_FOTMOB_ID`, `CHECK_MAPPING_EXISTS`, `GET_RAW_DATA_BY_MATCH`
- `HEALTH_CHECK`, `GET_DB_STATS`, `COUNT_NULL_FIELD`, `GET_DUPLICATE_EXTERNAL_IDS`

**Consumers:** Grep across the codebase shows no active imports consuming `SQLStore` or
`from src.database.sql_store`. The convenience instance `SQL = SQLStore()` at the bottom
of the file may be used via `from src.database.sql_store import SQL`, but no active
consumers were found in the current `src/` or `scripts/` directories. This may be dead
code or consumed from outside the scanned paths.

**Observed operations:** NONE — no execution code
**Observed tables:** matches, matches_mapping, raw_match_data (via SQL strings only)
**DB driver:** None imported
**Direct write boundary:** NONE — file only defines strings; execution is elsewhere
**Why the original classification was "confirmed write":** The file contains INSERT,
UPDATE, and UPSERT SQL strings which the static scanner detected as write signals.
However, string constants do not constitute a write path — execution code is required.

**Recommended next action:** Reclassify as infrastructure. Guard at consumers that execute
these SQL strings, not here. If `SQLStore` has no active consumers, consider
deprecation/removal in a cleanup PR. Move to
`historical_python_confirmed_write_path_infrastructure_only_needs_caller_guard`.

---

### 4. `src/database/sync_db_pool.py`

**Classification:** `infrastructure_only_needs_caller_guard`

**Analysis:**

This is a synchronous PostgreSQL connection pool manager using
`psycopg2.pool.ThreadedConnectionPool`. It provides a generic SQL execution interface:

Write-capable methods:
- `execute(query, params, conn)`: Executes arbitrary SQL + `active_conn.commit()`. 
  Auto-commits after every execution — no distinction between read and write SQL.
- `executemany(query, params_list, conn)`: Batch executes arbitrary SQL + `active_conn.commit()`.
  Same auto-commit behavior.

Read-only methods:
- `fetch_all(query, params, conn)`: SELECT with RealDictCursor
- `fetch_one(query, params, conn)`: SELECT with RealDictCursor
- `get_connection()`: Context manager providing a connection with session settings

Convenience exports:
- `execute_sync_query()`: wraps `pool.execute(query, params)`
- `fetch_sync_all()`: wraps `pool.fetch_all(query, params)`
- `fetch_sync_one()`: wraps `pool.fetch_one(query, params)`

**Problem with guarding at this level:** The `execute()` method is generic — it accepts
any SQL and cannot distinguish INSERT/UPDATE/DELETE from benign operations.
Adding `assert_db_write_allowed()` here would:
1. Block all `execute()` calls including those that happen to be read-only but use execute
   (e.g., `SET timezone TO 'UTC'` on connection setup)
2. Potentially break health checks that use execute for probe queries
3. Create a blanket block that's overly broad

**Callers:** `src/utils/__init__.py` imports `get_sync_db_pool`. The convenience functions
are re-exported through `db_pool.py`. Callers go through `get_sync_db_pool()` or the
convenience functions.

**Observed operations:** Generic execute/executemany with auto-commit (both read and write)
**Observed tables:** N/A — infrastructure, tables depend on caller's SQL
**DB driver:** psycopg2
**Direct write boundary:** Yes — `execute()` and `executemany()` have commit. But guard at
infrastructure level is inappropriate because the method cannot distinguish reads from writes.

**Recommended next action:** Reclassify as infrastructure. Guard policy: all callers
that pass DML/DDL SQL through `execute()` or `executemany()` must have their own guard.
A separate design task should inventory all sync_db_pool consumers and determine
guard placement. Move to
`historical_python_confirmed_write_path_infrastructure_only_needs_caller_guard`.

---

### 5. `src/database/db_pool.py`

**Classification:** `infrastructure_only_needs_caller_guard`

**Analysis:**

This is an asynchronous PostgreSQL connection pool manager using `asyncpg`. It provides
a generic async SQL execution interface (V30.0 dual-mode with sync_db_pool re-export).

Write-capable methods:
- `execute(query, *args, timeout)`: Executes arbitrary SQL via asyncpg.
  asyncpg auto-commits by default unless inside a transaction.
- `executemany(query, args_list, timeout)`: Batch executes arbitrary SQL.

Read-only methods:
- `fetch(query, *args, timeout)`: SELECT returning list of Records
- `fetchrow(query, *args, timeout)`: SELECT returning single Record or None
- `fetchval(query, *args, column, timeout)`: SELECT returning single value

Convenience exports:
- `execute_query(query, *args)`: wraps `pool.execute(query, *args)`
- `fetch_query(query, *args)`: wraps `pool.fetch(query, *args)`
- `fetchrow_query(query, *args)`: wraps `pool.fetchrow(query, *args)`
- `fetchval_query(query, *args)`: wraps `pool.fetchval(query, *args)`

Also re-exports from `sync_db_pool`: `SyncDatabasePool`, `execute_sync_query`,
`fetch_sync_all`, `fetch_sync_one`, `get_sync_db_pool`, `init_global_sync_db_pool`

**Known callers:**
- `src/main.py`: `DatabasePool.get_instance()` + `init_pool()` (app bootstrap)
- `src/api/health.py`: `DatabasePool.get_instance()` for health checks (read-only SELECT 1)
- `src/api/monitoring.py`: `DatabasePool.get_instance()` (monitoring queries)
- `src/database/collector_repository.py`: `DatabasePool` + `connection()` (write —
  already guarded by batch3)
- `src/data/streaming/streaming_db_writer.py`: `DatabasePool.get_instance()` + 
  `get_connection()` (write — already guarded by batch3)

**Problem with guarding at this level:** Same as sync_db_pool — the `execute()` and
`executemany()` methods are generic. Adding guard here would block health checks and
read-only consumers that legitimately use these methods (e.g., `SET timezone`, 
`SET statement_timeout` during connection setup).

**Observed operations:** Generic execute/executemany (asyncpg, auto-commit)
**Observed tables:** N/A — infrastructure, tables depend on caller's SQL
**DB driver:** asyncpg
**Direct write boundary:** Yes — but guard at infrastructure level is inappropriate.

**Recommended next action:** Reclassify as infrastructure. Guard policy: all callers
that pass DML/DDL SQL through `execute()` or `executemany()` must have their own guard.
Two of the known write callers (collector_repository.py, streaming_db_writer.py) are
already guarded in batch3. A separate design task should complete the consumer inventory
and ensure all write-callers are guarded. Move to
`historical_python_confirmed_write_path_infrastructure_only_needs_caller_guard`.

---

## Classification Summary

| # | File | Classification | Write Capability | Guard Needed? |
|---|---|---|---|---|
| 1 | `odds_integrity_guard.py` | read_only_or_select_only | None (SELECT only; DELETE is print-only) | No |
| 2 | `integrity_guard.py` | read_only_or_select_only | None (SELECT only) | No |
| 3 | `sql_store.py` | infrastructure_only_needs_caller_guard | Via consumers (SQL strings only, no execution) | At consumers |
| 4 | `sync_db_pool.py` | infrastructure_only_needs_caller_guard | Via callers (generic execute+commit) | At callers |
| 5 | `db_pool.py` | infrastructure_only_needs_caller_guard | Via callers (generic execute, auto-commit) | At callers |

## Remaining Risks

1. **Read-only candidates (2 files):** The read-only classification was determined by
   static analysis only. If these files are later modified to add write capability,
   they will need re-classification.
2. **SQL store (1 file):** No active consumers found in codebase scan. If consumers
   exist outside scanned paths or are added later, they need guard.
3. **Infrastructure (2 files):** `sync_db_pool.execute()` and `db_pool.execute()` remain
   unguarded — any new code calling these methods with write SQL is not blocked.
   Consumer-level guard inventory and enforcement is needed.
4. **Known write callers of db_pool:** Two callers (collector_repository.py,
   streaming_db_writer.py) are already guarded in batch3. Other write callers may exist
   and need audit.
5. **Hardcoded DB credentials in integrity_guard.py:** The file has hardcoded defaults
   (`'host': 'localhost'`, `'password': 'football_pass'`). This is a pre-existing
   security concern separate from write guard.

## Next Recommended Tasks

Do not start automatically. Recommended next tasks only after user confirmation:

1. **Consumer-level guard for sync_db_pool callers** — inventory all code paths that
   call `sync_db_pool.execute()` or `sync_db_pool.executemany()` with DML/DDL, and add
   `assert_db_write_allowed()` at each write call site. See 
   `docs/SC002_PHASE2C_REMAINING_CONFIRMED_WRITE_PATHS_DESIGN.md` for analysis.

2. **Consumer-level guard for db_pool callers** — complete the inventory of all code that
   calls `db_pool.execute()` or `db_pool.executemany()` with DML/DDL. Two known write
   callers are already guarded (batch3). Audit remaining callers.

3. **SQL store deprecation or consumer guard** — determine if `sql_store.py` has active
   consumers. If yes, guard at each consumer. If no, consider deprecation/removal.

4. **python_indirect_write_path_design_phase1** — design approach for 8 indirect write
   paths.

5. **python_manual_review_phase2D** — review 5 manual review candidates.

## Verification Statements

- No Python target scripts were executed during this analysis.
- No database connection was established during this analysis.
- No SQL/migration was executed during this analysis.
- No real DB write was performed.
- SC-002 remains partial mitigation only.
- training / data expansion / real DB write remain blocked.
- 9 of 14 confirmed Python write paths are runtime_guarded (batch1+batch2+batch3).
- 5 remaining confirmed Python write paths have been classified in this design task.
- 0 new runtime guards were added in this design task.
- 0 files were marked as safe.
