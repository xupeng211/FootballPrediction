# SC-002 Indirect Write Path Design Phase1

- lifecycle: permanent
- owner: project governance
- created: 2026-06-24
- task: python_indirect_write_path_design_phase1
- source_doc: docs/SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md
- allowlist: config/python_db_write_allowlist.json

## Summary

Static design classification of all 8 `historical_python_indirect_write_path_pending_runtime_guard`
entries in `config/python_db_write_allowlist.json`. This task is **design/classification only** —
no runtime guard implementation, no DB connection, no real DB write.

**Key finding: 6 of 8 "indirect" paths are actually DIRECT write paths** that use psycopg2
directly with explicit INSERT/UPDATE and `conn.commit()`, bypassing any repository layer.
The original design document classification was imprecise — these files have their own
independent DB connections and write SQL, not mediated through MatchRepository or other
repository classes.

## Classification Summary

| # | Path | Original Classification | New Classification | Risk |
|---|---|---|---|---|
| 1 | `src/services/match_aligner.py` | indirect_write_pending | **indirect_write_needs_guard** | **HIGH** |
| 2 | `src/services/match_linker.py` | indirect_write_pending | **indirect_write_needs_guard** | **HIGH** |
| 3 | `src/services/match_data_service.py` | indirect_write_pending | **indirect_false_positive_candidate** | NONE |
| 4 | `src/services/league_router.py` | indirect_write_pending | **indirect_read_only_candidate** | NONE |
| 5 | `src/api/collectors/odds_api_client_v38.py` | indirect_write_pending | **indirect_write_needs_guard** | **HIGH** |
| 6 | `scripts/maintenance/reprocess_failed_matches.py` | indirect_write_pending | **indirect_write_needs_guard** | **MEDIUM** |
| 7 | `scripts/maintenance/clean_corrupt_l2.py` | indirect_write_pending | **indirect_write_needs_guard** | **MEDIUM** |
| 8 | `scripts/maintenance/fix_zombie_matches.py` | indirect_write_pending | **indirect_write_needs_guard** | **MEDIUM** |

**Totals:**
- `indirect_write_needs_guard`: **6** (all actually DIRECT write, need guard)
- `indirect_read_only_candidate`: **1** (league_router.py)
- `indirect_false_positive_candidate`: **1** (match_data_service.py)
- `indirect_write_already_guarded`: **0**
- `indirect_write_needs_design`: **0**
- `indirect_unknown_needs_manual_review`: **0**

## Per-File Analysis

### 1. `src/services/match_aligner.py` → indirect_write_needs_guard

- **DB driver:** psycopg2 (direct import, own `_get_connection()`)
- **Write methods:** `save_alignment()` — INSERT INTO matches_mapping with ON CONFLICT DO UPDATE
- **Write operations:** INSERT, UPSERT
- **Target tables:** `matches_mapping`
- **commit/rollback:** Explicit `conn.commit()` and `conn.rollback()` in `save_alignment()`
- **Guard:** NONE — no `assert_db_write_allowed()` or equivalent
- **dry_run flag:** No
- **Actually indirect?** NO — this file has its OWN direct DB write path via psycopg2. It does NOT import MatchRepository. It was misclassified as "indirect" in the original design doc.
- **Indirect write chain:** N/A — direct write
- **Guard recommendation:** Guard in `save_alignment()` before `cursor.execute()` with the INSERT. Guard tables: `['matches_mapping']`. Guard operations: `['INSERT', 'UPDATE']`.
- **Read methods only:** `get_missing_odds_matches()` (SELECT), `validate_alignment()` (SELECT), `_check_existing_alignment()` (SELECT), `get_alignment_stats()` (SELECT COUNT)

### 2. `src/services/match_linker.py` → indirect_write_needs_guard

- **DB driver:** psycopg2 (direct import, own `_get_connection()`)
- **Write methods:**
  - `store_odds_intelligence()` — CREATE TABLE match_odds_intelligence, INSERT INTO match_odds_intelligence ON CONFLICT DO UPDATE
  - `batch_store_odds_intelligence()` — CREATE TABLE match_odds_intelligence, execute_values() INSERT ON CONFLICT DO UPDATE
  - `sync_multi_source_to_intelligence()` — calls `store_odds_intelligence()`
- **Write operations:** CREATE TABLE, INSERT, UPSERT (ON CONFLICT DO UPDATE)
- **Target tables:** `match_odds_intelligence`
- **commit/rollback:** Explicit `conn.commit()` and `conn.rollback()` in all write methods
- **Guard:** NONE
- **dry_run flag:** No
- **Actually indirect?** NO — this file has its OWN direct DB write path. It does NOT import MatchRepository. It was misclassified as "indirect" in the original design doc.
- **Indirect write chain:** N/A — direct write
- **Guard recommendation:** Guard in `store_odds_intelligence()` and `batch_store_odds_intelligence()` before write SQL. Guard tables: `['match_odds_intelligence']`. Guard operations: `['CREATE', 'INSERT', 'UPDATE']`.
- **Read methods only:** `find_candidates()` (SELECT), `select_best_match()` (no DB, in-memory sort)

### 3. `src/services/match_data_service.py` → indirect_false_positive_candidate

- **DB driver:** psycopg2 (imported but only for `_get_connection()` and `close()`)
- **Write methods:** NONE
- **Write operations:** NONE
- **Target tables:** NONE
- **commit/rollback:** No commit/rollback anywhere in the file
- **Guard:** N/A (no write path)
- **dry_run flag:** N/A
- **Actually indirect?** N/A — NO write capability whatsoever
- **Evidence:** The file is a skeleton class with only `__init__`, `_get_connection()`, and `close()`. It defines `MatchAligner = MatchDataService` and `MatchLinker = MatchDataService` as type aliases, but the MatchDataService class itself has zero write methods. The aliases suggest it was intended as a base class or facade, but the current implementation is a bare connection manager without any data operations.
- **Indirect write chain:** NONE — no write methods exist
- **Guard recommendation:** No guard needed. Reclassify to false_positive. If the class is later extended with actual write methods from match_aligner.py or match_linker.py, re-evaluate.
- **Recommendation:** Consider removing the MatchAligner/MatchLinker aliases — they are misleading (suggesting this is equivalent to the full implementations in separate files).

### 4. `src/services/league_router.py` → indirect_read_only_candidate

- **DB driver:** psycopg2 (imported only in `discover_all_leagues()` method)
- **Write methods:** NONE
- **Write operations:** NONE
- **Target tables:** NONE (SELECT DISTINCT on matches only)
- **commit/rollback:** No commit — `conn.close()` after SELECT, no write
- **Guard:** N/A (read-only)
- **dry_run flag:** N/A
- **Actually indirect?** N/A — NO write capability
- **Evidence:** The `discover_all_leagues()` method executes only `SELECT DISTINCT league_name FROM matches ORDER BY league_name`. All other methods (`resolve_url()`, `resolve_with_fallback()`) are pure URL string manipulation — no DB access at all. No INSERT/UPDATE/DELETE/CREATE/ALTER/TRUNCATE anywhere.
- **Indirect write chain:** NONE — SELECT-only
- **Guard recommendation:** No guard needed. Reclassify to read_only. File is a URL routing utility with one optional SELECT query for league discovery.
- **Note:** `discover_all_leagues()` creates a NEW psycopg2 connection (not using the class connection) and properly closes it. This is read-only and self-contained.

### 5. `src/api/collectors/odds_api_client_v38.py` → indirect_write_needs_guard

- **DB driver:** psycopg2 (direct import in `save_odds_to_db()`)
- **Write methods:** `save_odds_to_db()` — INSERT INTO match_odds ON CONFLICT DO UPDATE
- **Write operations:** INSERT, UPSERT (ON CONFLICT (match_id, provider) DO UPDATE)
- **Target tables:** `match_odds`
- **commit/rollback:** Explicit `conn.commit()` in try block; no explicit rollback (connection closes in finally)
- **Guard:** NONE
- **dry_run flag:** No
- **Actually indirect?** NO — this file has its OWN direct DB write path. It was misclassified as "indirect" (assumed write via collector layer) but actually imports psycopg2 directly and executes INSERT with commit.
- **Indirect write chain:** N/A — direct write
- **Guard recommendation:** Guard in `save_odds_to_db()` before `cursor.execute(sql, ...)`. Guard tables: `['match_odds']`. Guard operations: `['INSERT', 'UPDATE']`.
- **Other methods:** All other methods (`fetch_odds()`, `fetch_match_list()`, `validate_tls_fingerprint()`, `stealth_health_check()`) are network-only (HTTP fetch via StealthClient), no DB access.

### 6. `scripts/maintenance/reprocess_failed_matches.py` → indirect_write_needs_guard

- **DB driver:** psycopg2 (imported, `get_db_connection()` helper)
- **Write methods:** `reprocess_match()` — UPDATE matches SET l2_extracted_features, l2_data_version, extracted_at, collection_status, last_error
- **Write operations:** UPDATE
- **Target tables:** `matches`
- **commit/rollback:** `conn.commit()` after UPDATE in non-dry-run path
- **Guard:** NONE
- **dry_run flag:** YES — `--dry-run` flag exists (`action="store_true"`). **But default is FALSE** — when `--dry-run` is NOT passed, `args.dry_run` is `False` and real UPDATE+commit executes. This is the INVERSE of the safe default (DRY_RUN=true).
- **Actually indirect?** NO — this script has its OWN direct DB write path. It does NOT go through any repository layer. It was misclassified as "indirect" in the original design doc.
- **Indirect write chain:** N/A — direct write
- **Guard recommendation:**
  1. Guard in `reprocess_match()` before `cursor.execute(update_query, params)` and `conn.commit()` when `not dry_run`.
  2. Consider inverting the dry_run default: `--no-dry-run` with `action="store_true"` would make dry_run=True the default (safer). Or add guard that blocks when `DRY_RUN` env var is not explicitly set.
  3. Guard tables: `['matches']`. Guard operations: `['UPDATE']`.
- **Read methods:** `get_matches_needing_deep_features()` (SELECT), `get_failed_matches()` (SELECT), stats query at end (SELECT COUNT)

### 7. `scripts/maintenance/clean_corrupt_l2.py` → indirect_write_needs_guard

- **DB driver:** psycopg2 (imported, `L2DataCleaner.connect()`)
- **Write methods:** `clean_corrupt_records()` — UPDATE matches SET l2_raw_json = NULL, l2_data_version = NULL, l2_collected_at = NULL
- **Write operations:** UPDATE (sets fields to NULL — data deletion)
- **Target tables:** `matches`
- **commit/rollback:** `self.conn.commit()` after UPDATEs in non-dry-run path
- **Guard:** NONE
- **dry_run flag:** YES — `--dry-run` flag exists (`action="store_true"`). **But default is FALSE** — when `--dry-run` is NOT passed, `args.dry_run` is `False`. Additionally, there's no env-var guard; the only protection is the interactive `confirm = input("确认删除? (yes/no): ")` prompt, which can be bypassed.
- **Actually indirect?** NO — this script has its OWN direct DB write path. It was correctly identified as having psycopg2 access but misclassified as "indirect" (the write is direct).
- **Indirect write chain:** N/A — direct write
- **Guard recommendation:**
  1. Guard in `clean_corrupt_records()` before UPDATE loop and `self.conn.commit()` when `not dry_run`.
  2. Same dry_run default concern as reprocess_failed_matches.py — default is write-enabled.
  3. Guard tables: `['matches']`. Guard operations: `['UPDATE']` (data nullification).
- **Read methods:** `detect_corrupt_records()` (SELECT), `preview_cleanup()` (no DB — just prints), `get_statistics()` (SELECT COUNT)

### 8. `scripts/maintenance/fix_zombie_matches.py` → indirect_write_needs_guard

- **DB driver:** psycopg2 (imported in `ZombieMatchFixer.get_connection()`)
- **Write methods:**
  - `fix_zombie_matches()` — orchestrates; calls `_batch_update_matches()` + `conn.commit()` when not dry_run
  - `_batch_update_matches()` — UPDATE matches SET status, home_score, away_score, is_finished
  - `clean_predictions()` — deletes CSV prediction files (filesystem write, not DB write)
- **Write operations:** UPDATE
- **Target tables:** `matches`
- **commit/rollback:** `conn.commit()` in `fix_zombie_matches()` after batch update
- **Guard:** NONE
- **dry_run flag:** YES — `--dry-run` flag exists (`action="store_true"`). **But default is FALSE** — when `--dry-run` is NOT passed, `args.dry_run` is `False` and real UPDATE+commit executes.
- **Actually indirect?** NO — this script has its OWN direct DB write path. It was misclassified as "indirect" in the original design doc.
- **Indirect write chain:** N/A — direct write
- **Guard recommendation:**
  1. Guard in `fix_zombie_matches()` before `_batch_update_matches()` and `conn.commit()` when `not self.dry_run`.
  2. Same dry_run default concern — default is write-enabled.
  3. Guard tables: `['matches']`. Guard operations: `['UPDATE']`.
- **Read methods:** `analyze_before_state()` (SELECT COUNT/CASE), `fetch_zombie_matches()` (SELECT with LEFT JOIN), `analyze_after_state()` (SELECT COUNT), `extract_score_from_raw()` (no DB), `extract_odds_from_raw()` (no DB)

## Guard Placement Recommendations

| # | Path | Guard Location | Tables | Operations |
|---|---|---|---|---|
| 1 | match_aligner.py | `save_alignment()` before cursor.execute() | `matches_mapping` | INSERT, UPDATE |
| 2 | match_linker.py | `store_odds_intelligence()` and `batch_store_odds_intelligence()` before write SQL | `match_odds_intelligence` | CREATE, INSERT, UPDATE |
| 5 | odds_api_client_v38.py | `save_odds_to_db()` before cursor.execute() | `match_odds` | INSERT, UPDATE |
| 6 | reprocess_failed_matches.py | `reprocess_match()` before cursor.execute() when not dry_run | `matches` | UPDATE |
| 7 | clean_corrupt_l2.py | `clean_corrupt_records()` before UPDATE loop when not dry_run | `matches` | UPDATE |
| 8 | fix_zombie_matches.py | `fix_zombie_matches()` before `_batch_update_matches()` when not dry_run | `matches` | UPDATE |

## Non-Guard Candidates

### Read-only (no guard needed)

- **`league_router.py`** — SELECT DISTINCT only. URL routing logic. No write capability.

### False positive (no guard needed, no write path)

- **`match_data_service.py`** — Skeleton class with only connection management. No write methods. The MatchAligner/MatchLinker aliases are misleading; they point to MatchDataService which has zero data operations.

## Original Design Doc Discrepancies

The original design doc (`docs/SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md`) classified
these 8 paths as "indirect" with assumptions about repository-layer mediation. This detailed
static analysis reveals:

| Original Assumption | Actual Finding |
|---|---|
| match_aligner.py writes "via MatchRepository" | Uses OWN psycopg2 connection, INSERT directly |
| match_linker.py writes "via MatchRepository" | Uses OWN psycopg2 connection, INSERT+CREATE TABLE directly |
| match_data_service.py "may write via repository" | Has ZERO write methods — bare connection manager |
| league_router.py "may write via repository" | SELECT DISTINCT only — URL routing utility |
| odds_api_client_v38.py "may write via collector" | Uses OWN psycopg2 connection, INSERT directly |
| reprocess_failed_matches.py "has dry_run refs but uncertain default" | Default is write-enabled (dry_run=False), has direct UPDATE |
| clean_corrupt_l2.py "has dry_run refs but uncertain default" | Default is write-enabled (dry_run=False), has direct UPDATE |
| fix_zombie_matches.py "has dry_run refs but uncertain default" | Default is write-enabled (dry_run=False), has direct UPDATE |

## Phase2 Implementation (python_indirect_write_path_guard_phase2)

- **Completed:** 2026-06-25
- **Task:** python_indirect_write_path_guard_phase2
- **Status:** COMPLETE — all 6 indirect_write_needs_guard paths now have runtime guard

All 6 target files now have `assert_db_write_allowed()` calls before real DB write operations:

| # | Path | Guard Location | Operation | Table |
|---|---|---|---|---|
| 1 | `src/services/match_aligner.py` | `save_alignment()` before INSERT | INSERT | `matches_mapping` |
| 2 | `src/services/match_linker.py` | `store_odds_intelligence()` before CREATE TABLE + INSERT; `batch_store_odds_intelligence()` before CREATE TABLE + INSERT | CREATE, INSERT | `match_odds_intelligence` |
| 3 | `src/api/collectors/odds_api_client_v38.py` | `save_odds_to_db()` before INSERT | INSERT | `match_odds` |
| 4 | `scripts/maintenance/reprocess_failed_matches.py` | `reprocess_match()` before UPDATE | UPDATE | `matches` |
| 5 | `scripts/maintenance/clean_corrupt_l2.py` | `clean_corrupt_records()` before UPDATE | UPDATE | `matches` |
| 6 | `scripts/maintenance/fix_zombie_matches.py` | `fix_zombie_matches()` before UPDATE | UPDATE | `matches` |

Guard details:
- Uses existing `helpers/python_db_write_guard.py` `assert_db_write_allowed()` pattern
- All guards placed before real DB write operations (not after)
- For scripts with existing `--dry-run` flags: `dry_run` parameter integrated into guard call
- Real DB write remains blocked unless ALLOW_DB_WRITE=yes, FINAL_DB_WRITE_CONFIRMATION=yes, table-specific gates, DRY_RUN=false

## Non-Goals

This task is a **design/classification** task only. It is explicitly NOT:

- Runtime guard implementation
- Execution of any Python target script
- DB connection
- Real DB write
- SQL / migration execution
- Scraper / browser / Playwright execution
- Training or data expansion
- Marking any path as `runtime_guarded` or `safe`
- Claiming SC-002 is resolved or complete

## SC-002 Status

- SC-002 remains **partial mitigation only**.
- training / data expansion / real DB write remain **blocked**.
- **15/20** Python write paths now have runtime guard (9 confirmed + 6 indirect).
- 5 remaining confirmed paths classified (2 read_only, 3 infrastructure).
- 2 of 8 indirect paths reclassified as safe (1 read_only, 1 false_positive).
- 6 of 8 indirect paths now runtime guarded (completed via `python_indirect_write_path_guard_phase2`).
- 5 manual review candidates NOT processed.
- SC-002 is NOT complete. Production DB write still requires explicit authorization.

## Next Recommended Task

`python_manual_review_phase2D` — review the 5 manual review candidates.

Do not start automatically. Recommended next task only after user confirmation.
