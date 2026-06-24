# SC-002 Consumer-Level Guard Audit: db_pool / sync_db_pool / sql_store

- lifecycle: design
- owner_task: consumer_level_guard_audit_for_db_pool_sync_db_pool_sql_store
- date: 2026-06-24
- type: consumer-level audit / design (NOT runtime guard implementation)

## Task Scope

Consumer-level static audit and classification of all callers of three
infrastructure-only confirmed write paths:

1. `src/database/sql_store.py`
2. `src/database/sync_db_pool.py`
3. `src/database/db_pool.py`

This task does NOT implement runtime guards. It only discovers, classifies,
and documents which consumers may perform real DB writes, which are read-only,
and which have already been guarded.

## Search Method

Static code search with `grep -rn` across `src/` and `tests/`:

1. Direct import search:
   - `SQLStore` / `sql_store`
   - `SyncDatabasePool` / `sync_db_pool`
   - `DatabasePool` / `db_pool`
   - `get_db_pool` / `get_sync_db_pool`

2. Method-level search:
   - `execute()` / `executemany()` / `fetch()` / `fetchrow()` / `fetchval()` / `fetch_all()` / `fetch_one()`
   - `connection()` / `get_connection()`
   - `init_pool()` / `close()`

3. Convenience-function search:
   - `execute_query` / `fetch_query` / `fetchrow_query` / `fetchval_query`
   - `execute_sync_query` / `fetch_sync_all` / `fetch_sync_one`

4. Indirect-consumer search:
   - `DatabaseManager` / `get_db_manager` / `database_connection` (aliases via `src/utils/__init__.py`)

No target scripts were executed. No DB connection was made. No SQL was executed.
No live fetch / scraper / browser was used.

## Infrastructure File Summary

### 1. src/database/sql_store.py

- **Type**: SQL query string constants (V4.25 "SQL 弹药库")
- **Class**: `SQLStore` — data-only class with SQL string constants
- **Write-capable SQL strings present**: `INSERT_MATCH`, `INSERT_MATCH_MAPPING`, `UPSERT_RAW_DATA`, `UPDATE_XG`, `UPDATE_STATS`, `UPDATE_L3_ODDS_DATA`, `UPDATE_GOLDEN_FEATURES`, `MARK_HARVESTED`
- **Execution code**: NONE — no psycopg2/asyncpg/sqlalchemy imports, no connect/cursor/execute/commit/rollback
- **External consumers found**: 0

### 2. src/database/sync_db_pool.py

- **Type**: Synchronous psycopg2 connection pool (ThreadedConnectionPool)
- **Write-capable methods**: `execute()` (auto-commit), `executemany()` (auto-commit)
- **Read-only methods**: `fetch_all()`, `fetch_one()`, `get_connection()`
- **Convenience functions**: `execute_sync_query()`, `fetch_sync_all()`, `fetch_sync_one()`, `get_sync_db_pool()`, `init_global_sync_db_pool()`
- **Re-exported by**: `src/database/db_pool.py`
- **External consumers found**: 1 (`src/utils/__init__.py` — re-export only, zero downstream consumers)

### 3. src/database/db_pool.py

- **Type**: Asynchronous asyncpg connection pool
- **Write-capable methods**: `execute()` (auto-commit), `executemany()` (auto-commit)
- **Read-only methods**: `fetch()`, `fetchrow()`, `fetchval()`, `connection()`
- **Lifecycle methods**: `get_instance()`, `init_pool()`, `close()`
- **Convenience functions**: `execute_query()`, `fetch_query()`, `fetchrow_query()`, `fetchval_query()`, `get_db_pool()`, `init_global_db_pool()`
- **Re-exports**: `SyncDatabasePool`, `get_sync_db_pool`, `init_global_sync_db_pool`, `execute_sync_query`, `fetch_sync_all`, `fetch_sync_one`
- **External consumers found**: 9

## Consumer Classification

| # | Consumer | Infrastructure | Classification | Evidence |
|---|---|---|---|---|
| 1 | `src/main.py` | db_pool.py | **C (read_only)** | Only `get_instance()`, `init_pool()`, `close()` — lifecycle management, no SQL execution |
| 2 | `src/api/health.py` | db_pool.py | **C (read_only)** | Only `get_connection()` + `fetchrow("SELECT 1")` — health check SELECT only |
| 3 | `src/api/monitoring.py` | db_pool.py | **C (read_only)** | Only `get_connection()` + `fetchrow()`/`fetch()` — monitoring/metrics SELECT and EXPLAIN ANALYZE only |
| 4 | `src/ml/dataset/dataset_generator.py` | db_pool.py | **C (read_only)** | Only `db_pool.fetch(query, ...)` with SELECT — data retrieval only |
| 5 | `src/database/async_dependencies.py` | db_pool.py | **C (read_only)** | Only `get_instance()` + `get_connection()` — FastAPI dependency injection, yields connections, no SQL executed directly |
| 6 | `src/database/performance_monitor.py` | db_pool.py | **C (read_only)** | Only `get_connection()` + `fetchrow()`/`fetch()` — monitoring/metrics SELECT and pg_stat queries only |
| 7 | `src/database/collector_repository.py` | db_pool.py | **B (write_already_guarded)** | Has `connection.execute(SQL_UPSERT_MATCH, ...)` for INSERT/UPSERT on matches table. Already guarded: `assert_db_write_allowed()` called before all writes (Phase2C batch3) |
| 8 | `src/data/streaming/streaming_db_writer.py` | db_pool.py | **B (write_already_guarded)** | Has `conn.executemany(sql, values)` for INSERT/UPSERT on dynamic tables. Already guarded: `assert_db_write_allowed()` called before all writes (Phase2C batch3) |
| 9 | `tests/unit/mock_factories.py` | db_pool.py | **F (no_active_consumers)** | Test mock only — `AsyncMock` objects, no real DB usage |
| 10 | `src/utils/__init__.py` | sync_db_pool.py | **F (no_active_consumers)** | Re-exports `SyncDatabasePool as DatabaseManager`, `get_sync_db_pool as get_db_manager`, provides `database_connection()` wrapper. Zero downstream consumers of these aliases found |
| 11 | `src/database/sql_store.py` (SQLStore) | sql_store.py | **F (no_active_consumers)** | `SQLStore` class has zero external consumers. Only referenced in its own docstring example. SQL string constants exist but no code imports or executes them |

## Classification Summary

| Category | Count | Consumers |
|---|---|---|
| **A** consumer_write_needs_guard | **0** | — |
| **B** consumer_write_already_guarded | **2** | `collector_repository.py`, `streaming_db_writer.py` |
| **C** consumer_read_only | **6** | `main.py`, `health.py`, `monitoring.py`, `dataset_generator.py`, `async_dependencies.py`, `performance_monitor.py` |
| **D** consumer_dynamic_sql_needs_design | **0** | — |
| **E** consumer_unknown_needs_manual_review | **0** | — |
| **F** no_active_consumers | **3** | `SQLStore` (sql_store.py), `src/utils/__init__.py`, `mock_factories.py` |
| **Total** | **11** | |

## Key Findings

### 1. All write-capable consumers already guarded

The two consumers that execute write SQL through `db_pool.py` infrastructure are
`collector_repository.py` and `streaming_db_writer.py`. Both were already guarded
in Phase2C batch3 with `assert_db_write_allowed()` before all INSERT/UPSERT operations.

### 2. No category A (write_needs_guard) consumers

Zero consumers fall into the "write but unguarded" category. All remaining
consumers only perform SELECT queries or connection lifecycle management.

### 3. SQLStore has zero active consumers

The `SQLStore` class in `sql_store.py` defines SQL string constants for
INSERT/UPDATE/UPSERT operations, but no code in the entire codebase imports or
uses it. It is effectively dead code. The SQL strings defined there
(INSERT_MATCH, UPSERT_RAW_DATA, etc.) are not the same SQL executed by the
guarded consumers — those use their own inline SQL (e.g., `SQL_UPSERT_MATCH` in
`collector_repository.py` is defined locally, not from SQLStore).

### 4. SyncDatabasePool has zero active direct consumers

`SyncDatabasePool` is only re-exported through `db_pool.py` and `src/utils/__init__.py`.
The `src/utils/__init__.py` alias (`DatabaseManager`, `get_db_manager`, `database_connection()`)
has zero downstream consumers. All async consumers use `DatabasePool` (asyncpg) instead.

### 5. Convenience functions have zero active consumers

`execute_query`, `fetch_query`, `execute_sync_query`, `fetch_sync_all`, etc.
have no active consumers outside of test mocks.

## Next Implementation Candidates

Since all write consumers of these three infrastructure files are already
guarded (collector_repository.py and streaming_db_writer.py in batch3), there
are **no new guard implementation candidates** from this audit.

### Recommended follow-up actions (separate tasks):

1. **SQLStore deprecation/cleanup** — `sql_store.py` has zero consumers and
   contains write-capable SQL strings. Consider deprecation notice and eventual
   removal in a cleanup PR.
2. **SyncDatabasePool utils alias cleanup** — `src/utils/__init__.py` re-exports
   `SyncDatabasePool as DatabaseManager` and `get_sync_db_pool as get_db_manager`
   with zero downstream consumers. Consider removal.
3. **Continue Phase2C batch4 guard implementation** — The 5 remaining confirmed
   write paths classified in `docs/SC002_PHASE2C_REMAINING_CONFIRMED_WRITE_PATHS_DESIGN.md`
   still need guard implementation for their direct write entries.

## Remaining Risks

- **SQLStore write strings exist but unused** — If SQLStore is later adopted by
  a consumer without a guard, new unguarded write paths could appear. Mitigation:
  the static enforcement scanner and ai_workflow_gate.py would flag new
  consumers that write without guard.
- **SyncDatabasePool aliases unused but available** — If a future module imports
  `DatabaseManager` or `database_connection` from `src.utils` and uses them for
  writes without guard, the static scanner should catch it.
- **Dynamic SQL in streaming_db_writer.py** — While already guarded, the
  streaming_db_writer constructs SQL dynamically (`INSERT INTO {table_name}`).
  The guard covers the entry point; table-level granularity is limited to the
  table name passed at runtime.

## Explicit Confirmations

- [x] No target scripts were executed
- [x] No DB connection was made
- [x] No SQL / migration was executed
- [x] No real DB write was performed
- [x] No runtime guards were added
- [x] No files were marked `runtime_guarded`
- [x] No files were marked `safe`
- [x] SC-002 remains partial mitigation only
- [x] Training / data expansion / real DB write remain blocked
- [x] Indirect write paths were NOT processed
- [x] Manual review candidates were NOT processed

## Next Recommended Task

Do not start automatically.

Recommended next task only after user confirmation:

- Continue Phase2C batch4 guard implementation for the 5 remaining confirmed
  write paths (those classified as `needs_guard` in the batch4 design doc).
- OR: SQLStore deprecation cleanup (remove dead code with zero consumers).
- OR: SyncDatabasePool utils alias cleanup.
