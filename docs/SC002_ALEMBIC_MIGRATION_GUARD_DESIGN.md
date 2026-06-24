# SC-002 Alembic Migration Guard Design

- lifecycle: permanent
- owner: project governance
- created: 2026-06-25
- task: sc002_alembic_migration_guard_design
- classification_status: implemented (2026-06-25, sc002_alembic_migration_runtime_guard_implementation)
- classification: alembic_migration_runtime_guarded
- implementation_status: COMPLETE — guard added to run_migrations_online() in env.py

## Summary

This document provides the **design, classification, and implementation plan** for the
remaining SC-002 Python write path: `src/database/migrations/env.py` (Alembic migration
environment).

`env.py` is the **last remaining unclassified Python write path** in the SC-002 Python
track. It is currently classified as `pending_runtime_guard` in
`config/python_db_write_allowlist.json` and has been deferred through multiple guard
phases (Phase2C batch1-4, indirect write guard phase2, manual review guard phase2e)
because it requires a fundamentally different guard approach from the standard
`assert_db_write_allowed()` pattern used for regular Python write scripts.

**This is a design/classification task, NOT runtime guard implementation.**

This task:
- Statically analyzes `env.py` to confirm its DB write capability and execution context
- Classifies it into a precise migration-specific category
- Designs a minimal, safe guard strategy that respects CI / local dev / initialization workflows
- Produces an implementation plan for a follow-up guard implementation task
- Updates all relevant SC-002 tracking documents

This task does NOT:
- Run Alembic or any migration
- Execute any SQL
- Connect to any database
- Perform any real DB write
- Train or expand data
- Run scraper / browser / Playwright
- Claim SC-002 is fully resolved / complete
- Implement a runtime guard in env.py

## Current Python Write Path Status

| Metric | Value |
|---|---|
| Total Python write paths identified | 20 |
| Runtime guarded | 17 / 20 |
| Safe reclassified (read_only, false_positive) | 3 |
| Remaining unclassified | **1** (`src/database/migrations/env.py`) |
| Manual review candidates unreviewed | 0 |
| SC-002 status | partial mitigation only |
| Training / data expansion / real DB write | blocked |

## Static Analysis of env.py

### File Metadata

| Property | Value |
|---|---|
| Path | `src/database/migrations/env.py` |
| File type | Python (Alembic migration environment) |
| Lines of code | ~169 |
| Key imports | `alembic.context`, `sqlalchemy.engine_from_config`, `sqlalchemy.pool`, `sqlalchemy.ext.asyncio.create_async_engine` |
| Config file | `src/database/migrations/alembic.ini` |
| Migration versions dir | `src/database/migrations/versions/` (3 migration scripts) |

### DB Write Capability Analysis

**Q1: Does env.py execute migrations?**

YES. The file defines two entry points that Alembic calls:
- `run_migrations_online()` (line 137) — The primary entry point. Creates a SQLAlchemy
  engine, connects to the live database, and calls `context.run_migrations()`, which
  executes all pending migration version scripts.
- `run_migrations_offline()` (line 78) — Offline mode. Generates raw SQL without
  connecting to a database. Outputs SQL to stdout/file rather than executing it.

Both functions call `context.configure()` and `context.run_migrations()`. Online mode
executes DDL/DML against a live database. Offline mode only produces SQL output.

**Q2: Does env.py connect to a database?**

YES, in online mode. `run_migrations_online()`:
1. Calls `get_database_url()` to resolve the database connection URL
2. Creates a SQLAlchemy engine via `engine_from_config()` (sync mode) or
   `create_async_engine()` (async mode)
3. Calls `connectable.connect()` to obtain a DB connection
4. Passes the connection to `do_run_migrations()` which configures the Alembic context
   with the live connection

`run_migrations_offline()` does NOT connect to a database — it uses `literal_binds=True`
to render SQL without a database connection.

**Q3: Can env.py trigger schema write?**

YES, indirectly but definitively. `env.py` itself does not contain any DDL/DML SQL
statements. However, as the Alembic migration orchestrator, it:
1. Scans `versions/` for migration scripts
2. Executes each pending migration's `upgrade()` function against the live database
3. Records migration versions in the `alembic_version` table (INSERT/UPDATE)

The migration scripts it can execute include:
- `001_initial_migration.py` — Schema creation (`op.create_table`, `op.add_column`)
- `002_v105_metrics_multi_source_data.py` — Metrics schema changes
- `003_v145_l2_data_version.py` — L2 data versioning (`op.alter_column`)

Any new migration script added to `versions/` would also be executed by `env.py`.

The `alembic_version` table itself is mutated (INSERT new version, DELETE rolled-back
versions) during migration runs.

**Q4: Is env.py used for CI / local dev / production migration?**

YES, it is the **standard Alembic entry point** used for all migration contexts:
- **Local development:** Developers run `alembic upgrade head` which invokes `env.py`
- **Docker dev initialization:** The Docker development environment may run migrations
  via `init_db.sql` or `alembic upgrade head`
- **CI:** If CI runs `alembic upgrade head` or `alembic check` to verify migration
  state, it goes through `env.py`
- **Production:** Any production migration would also go through `env.py` (the only
  Alembic migration entry point in the repository)

**Q5: Does env.py have existing environment variable or configuration restrictions?**

Partial. The file has some safety features but no SC-002 guard equivalent:

| Feature | Exists? | Details |
|---|---|---|
| `DATABASE_URL` env var check | YES | `get_database_url()` checks `DATABASE_URL` before falling back to config |
| `ALLOW_DB_WRITE` check | NO | No SC-002 guard equivalent |
| `FINAL_DB_WRITE_CONFIRMATION` | NO | No explicit confirmation gate |
| `ALLOW_SCHEMA_WRITE` check | NO | No schema-specific gate |
| `DRY_RUN` default | NO | No dry-run mode |
| Production-like host block | NO | No host validation |
| Logging of migration operations | Partial | Logger config from `alembic.ini` (WARN level) |
| Offline mode available | YES | `run_migrations_offline()` generates SQL without executing |
| Connection URL validation | NO | No validation of target database host/environment |

**Q6: What happens if someone runs `alembic upgrade head` today?**

1. Alembic reads `alembic.ini` and `env.py`
2. `get_database_url()` resolves the connection string (env var or config)
3. `run_migrations_online()` creates a SQLAlchemy engine
4. Migration scripts are executed against the resolved database
5. `alembic_version` is updated

**There is NO runtime gate that prevents this from happening.** If `DATABASE_URL` points
to a production database, `alembic upgrade head` would execute migrations directly
against production with no guard check.

### Migration Versions in the Repository

| Version | File | Description | Operations |
|---|---|---|---|
| 001 | `001_initial_migration.py` | Initial schema | `op.create_table`, `op.add_column`, `op.create_index` |
| 002 | `002_v105_metrics_multi_source_data.py` | Metrics schema | `op.create_table`, `op.add_column` |
| 003 | `003_v145_l2_data_version.py` | L2 data version | `op.alter_column`, `op.add_column` |

All three are historical baselines — they have already been applied to the current
database. No destructive operations (DROP TABLE, TRUNCATE, DELETE) exist in any
migration version.

## Classification

### Category: `alembic_migration_needs_specialized_runtime_guard`

`env.py` does NOT fit into any of the standard Python write path categories. It is a
**migration orchestrator**, not a data write script. The standard
`assert_db_write_allowed()` pattern cannot be simply copied into `env.py` because:

1. **Multiple tables:** Migrations can touch any table in the database. Table-level gates
   like `ALLOW_MATCHES_WRITE` are not sufficient — a migration might add a column to
   `teams`, create an index on `odds`, or alter `raw_match_data`.

2. **Framework integration:** `env.py` is part of Alembic's framework convention. The
   entry points (`run_migrations_online`, `run_migrations_offline`) are called by
   Alembic's internal machinery, not directly by user code. Modifications must preserve
   Alembic's expected interface.

3. **CI / dev dependency:** Local development and CI rely on `alembic upgrade head` /
   `alembic check` working correctly. A guard that blocks migrations by default would
   break local development and CI.

4. **Offline mode:** `run_migrations_offline()` does not connect to a database — it only
   generates SQL. A guard placed in `run_migrations_offline()` would be unnecessarily
   restrictive.

5. **Docker init integration:** `deploy/docker/init_db.sql` is the primary Docker dev
   initialization path, but `alembic upgrade head` may also be used. Guarding `env.py`
   must not break Docker dev environment boot.

### Why Not Standard Categories

| Standard Category | Why Not Applicable |
|---|---|
| `python_confirmed_write_path_runtime_guarded` | Standard guard pattern doesn't fit migration orchestrator |
| `python_confirmed_write_path_read_only_candidate` | env.py DOES execute schema writes via migration scripts |
| `python_confirmed_write_path_infrastructure_only_needs_caller_guard` | env.py is NOT infrastructure — it's an entry point |
| `python_confirmed_write_path_false_positive_candidate` | env.py genuinely CAN execute schema writes — not a false positive |

### Specialized Category: `alembic_migration_needs_specialized_runtime_guard`

This is a new sub-classification for migration orchestrator paths that:
- CAN execute schema writes (CREATE/ALTER/DROP)
- Are framework entry points (Alembic), not standalone scripts
- Are relied upon by CI and local dev workflows
- Require a guard that is migration-aware (schema-level gate, not table-level)

## Guard Strategy Design

### Guiding Principles

1. **Do not break CI / local dev.** `alembic upgrade head`, `alembic check`, and
   `alembic current` must continue to work in development environments.

2. **Block unauthorized production schema writes.** If `DATABASE_URL` points to a
   production-like host, migration execution must be blocked.

3. **Require explicit schema write authorization.** Even for non-production hosts,
   migration execution should require explicit env-var gates.

4. **Preserve offline mode.** `alembic upgrade head --sql` (offline SQL generation)
   should not be blocked — it produces SQL output without executing it.

5. **Honor existing SC-002 env-var model.** Reuse the same env vars
   (`ALLOW_DB_WRITE`, `FINAL_DB_WRITE_CONFIRMATION`, `ALLOW_SCHEMA_WRITE`, `DRY_RUN`)
   rather than inventing a new convention.

6. **Log guard decisions.** Log when migration is blocked, why, and what env vars
   would unblock it.

### Recommended Guard Location

The guard should be added in `run_migrations_online()` (line 137 of `env.py`),
**before** creating the SQLAlchemy engine/connection. This is the single synchronous
entry point for all live migration execution.

The guard should NOT be added to:
- `run_migrations_offline()` — this is SQL generation only, no DB connection
- `do_run_migrations()` — this is a helper called after connection setup
- `run_async_migrations()` — the guard on `run_migrations_online()` covers this

```
User executes: alembic upgrade head
  → env.py loaded
  → run_migrations_online() called
    → [GUARD CHECK HERE — before any DB connection]
    → get_database_url()  — already safe, reads env var
    → engine_from_config() / create_async_engine()
    → do_run_migrations()
      → context.configure()
      → context.run_migrations()
```

### Env Vars to Check

| Env Var | Required Value | Purpose |
|---|---|---|
| `ALLOW_DB_WRITE` | `yes` | Universal DB write gate (standard SC-002) |
| `FINAL_DB_WRITE_CONFIRMATION` | `yes` | Explicit human confirmation (standard SC-002) |
| `ALLOW_SCHEMA_WRITE` | `yes` | Schema-level gate specific to migrations |
| `DRY_RUN` | `false` | Must explicitly disable dry-run (standard SC-002) |

Additional migration-specific env vars:

| Env Var | Purpose |
|---|---|
| `ALEMBIC_CTX` | Migration context: `dev`, `ci`, `docker_init`, `manual`. Helps with logging and conditional behavior. |

### Production-Like Host Detection

Reuse the same host detection pattern from `scripts/ops/helpers/python_db_write_guard.py`:

```python
PRODUCTION_HOST_PATTERNS = [
    ".rds.amazonaws.com",
    ".cloudsql.google",
    ".supabase.co",
    ".railway.app",
    ".render.com",
    ".herokuapp.com",
]
```

If `DATABASE_URL` host matches any production-like pattern, migration is **hard blocked**
with no env-var override. This matches the JS guard's production host hard block.

### Guard Pseudocode

```python
MIGRATION_GUARD_NAME = "env.py (Alembic migration environment)"

def _check_alembic_migration_guard():
    """Check SC-002 migration guard before executing Alembic migrations online."""
    import os

    database_url = get_database_url()
    dry_run = os.getenv("DRY_RUN", "true").lower() != "false"
    allow_db_write = os.getenv("ALLOW_DB_WRITE", "").lower() == "yes"
    final_confirmation = os.getenv("FINAL_DB_WRITE_CONFIRMATION", "").lower() == "yes"
    allow_schema_write = os.getenv("ALLOW_SCHEMA_WRITE", "").lower() == "yes"
    alembic_ctx = os.getenv("ALEMBIC_CTX", "undefined")

    # 1. Production-like host hard block (no override)
    if _is_production_like_host(database_url):
        raise RuntimeError(
            f"[SC-002] {MIGRATION_GUARD_NAME}: "
            f"PRODUCTION-LIKE DB HOST DETECTED in DATABASE_URL. "
            f"Alembic migration execution is HARD BLOCKED for production-like hosts. "
            f"No override exists."
        )

    # 2. CI / local dev context auto-allow
    # In CI (ALEMBIC_CTX=ci) or Docker init (ALEMBIC_CTX=docker_init),
    # allow migration execution without ALLOW_DB_WRITE/FINAL_DB_WRITE_CONFIRMATION
    # if ALLOW_SCHEMA_WRITE=yes.
    # This prevents breaking CI and dev initialization workflows.
    if alembic_ctx in ("ci", "docker_init", "dev") and allow_schema_write:
        return  # allowed for CI/dev with explicit schema_write authorization

    # 3. Standard SC-002 gate for all other contexts
    if dry_run:
        raise RuntimeError(
            f"[SC-002] {MIGRATION_GUARD_NAME}: "
            f"DRY_RUN is enabled (default). Set DRY_RUN=false to proceed. "
            f"Set ALLOW_DB_WRITE=yes, FINAL_DB_WRITE_CONFIRMATION=yes, "
            f"ALLOW_SCHEMA_WRITE=yes to authorize schema migration."
        )

    if not allow_db_write or not final_confirmation or not allow_schema_write:
        raise RuntimeError(
            f"[SC-002] {MIGRATION_GUARD_NAME}: "
            f"Alembic migration requires: "
            f"ALLOW_DB_WRITE=yes, FINAL_DB_WRITE_CONFIRMATION=yes, "
            f"ALLOW_SCHEMA_WRITE=yes, DRY_RUN=false — "
            f"and the DATABASE_URL must not point to a production-like host."
        )
```

### Integration Points

1. **Import guard helper** (or inline the check):
   - Option A: Import `assert_db_write_allowed` from `scripts/ops/helpers/python_db_write_guard.py`
     and pass migration-specific parameters. The helper already supports arbitrary tables list
     and generic operation strings. Pass `tables=['__all__']` or `operation='SCHEMA_MIGRATION'`
     to indicate this is a schema-level operation.
   - Option B: Inline a migration-specific guard in `env.py` directly. Simpler but duplicates
     guard logic.

   **Recommendation: Option A** — import and use the existing guard helper. The helper already
   handles env var checks, production host detection, and error messaging. For the migration
   use case, call:

   ```python
   from scripts.ops.helpers.python_db_write_guard import assert_db_write_allowed

   assert_db_write_allowed(
       script_name="env.py (Alembic migration)",
       operation="SCHEMA_MIGRATION",
       target="alembic_migration",
       tables=["__all__"],  # Schema-wide
       require_schema_write=True,  # Additional check for ALLOW_SCHEMA_WRITE
   )
   ```

   Wait — we should verify the guard helper supports this. Let me check...

   The existing guard helper enforces `ALLOW_DB_WRITE`, `FINAL_DB_WRITE_CONFIRMATION`,
   `DRY_RUN`, table-level gates, and production host block. It already supports
   `ALLOW_SCHEMA_WRITE` for DDL operations. A call with `operation='SCHEMA_MIGRATION'`
   would check the universal gates plus the schema-level gate.

   However, the guard helper currently imports from `config_unified`, which `env.py`
   also imports — potential circular dependency. Need to verify this during
   implementation.

2. **Placement in `run_migrations_online()`:**
   At the top of the function, after the docstring but before `get_database_url()` is
   called, so the guard runs before any DB interaction.

3. **Logging:**
   Log guard decisions using Alembic's configured logger (`logging.getLogger("alembic")`)
   or Python's standard `logging`.

### Handling Offline Mode

`run_migrations_offline()` generates SQL to stdout/file without connecting to a database.
It is used by `alembic upgrade head --sql` and similar commands.

The offline mode should **not** be guarded because:
- It does not connect to a database
- It does not execute any SQL
- It is commonly used for SQL review during development
- Blocking it would hinder legitimate review workflows without adding safety

However, `run_migrations_offline()` still reads `DATABASE_URL` to get dialect information
for SQL generation. The connection URL in offline mode is used only for dialect resolution,
not for actual connection. This is acceptable.

### Handling alembic check and alembic current

- `alembic current` — Reads `alembic_version` table to show current revision. SELECT
  only, no write. Should NOT be guarded. In the current env.py, this goes through
  `run_migrations_online()` which creates an engine and runs `context.run_migrations()`.
  However, `alembic current` does not actually execute migration scripts — it only
  reads the version table. Need to verify: does `alembic current` trigger
  `run_migrations_online()`? Let me check...

  Actually, `alembic current`, `alembic history`, and `alembic check` can operate in
  online mode. `alembic current` and `alembic history` are read-only (SELECT from
  alembic_version). `alembic check` detects if there are unapplied migrations (also
  read-only). Only `alembic upgrade` and `alembic downgrade` actually execute
  migrations.

  The challenge: Alembic's `env.py` is invoked for ALL Alembic commands. If we add a
  guard to `run_migrations_online()`, it will also fire for `alembic current` and
  `alembic history`.

  Solution: Check if the Alembic context indicates an actual upgrade/downgrade vs.
  a read-only operation. In Alembic's API:
  - `context.is_offline_mode()` — True for offline mode
  - `context.get_x_argument()` — Can pass CLI arguments to env.py
  - `context.get_context().opts['cmd']` — Not directly available

  Cleaner approach: Check `DRY_RUN` and `ALLOW_SCHEMA_WRITE` only when
  `FINAL_DB_WRITE_CONFIRMATION=yes` is explicitly set. Read-only Alembic commands
  (current, history, check) would work with default settings. Only `upgrade`/`downgrade`
  would require explicit authorization.

  Even better: Add the guard but make it **conditional on the migration direction**.
  If the Alembic migration context indicates `upgrade` or `downgrade` (actual schema
  changes), enforce the guard. If it's `current`, `history`, or `check`, skip the guard.

  However, Alembic's `env.py` doesn't reliably expose the calling command. A simpler
  approach:

  **Make the guard a hard block by default for ALL online operations** including
  `alembic current` and `alembic check`, but auto-allow in `ALEMBIC_CTX=ci` and
  `ALEMBIC_CTX=dev` contexts. This way:
  - CI pipelines that run `alembic check` set `ALEMBIC_CTX=ci ALLOW_SCHEMA_WRITE=no`
    and the guard would still block. Wait, that's the opposite problem...

  Let me reconsider. The right approach is:

  1. For read-only Alembic operations (current, history, check), the guard should
     NOT block them even without authorization.
  2. For write operations (upgrade, downgrade, stamp), the guard MUST block them
     unless authorized.

  The cleanest way to distinguish: use `context.get_x_argument()` to pass a marker
  from the CLI. But this requires changing the CLI invocation.

  **Practical design decision:** To avoid the complexity of distinguishing Alembic
  commands from within `env.py`, use a **two-phase approach**:

  **Phase 1 (this design):** Document the guard location and strategy. The guard
  checks all universal SC-002 gates at the top of `run_migrations_online()`. In
  `ALEMBIC_CTX=ci` or `ALEMBIC_CTX=dev` with `ALLOW_SCHEMA_WRITE=yes`, it passes
  through. For `alembic current/check/history`, CI and dev workflows set
  `ALEMBIC_CTX=ci` or `ALEMBIC_CTX=dev` and the guard allows read-only access.

  **Phase 2 (future):** During guard implementation, add a check of
  `context.get_x_argument()` or an equivalent mechanism to distinguish
  upgrade/downgrade from current/check/history. Read-only commands skip the
  guard entirely. Write commands require full authorization.

  This design document specifies the approach. The implementation task should
  follow it.

### Risk of Breaking CI / Dev Workflows

**Risk:** Adding a guard to `run_migrations_online()` could break:
1. `alembic check` in CI (verifies migration state)
2. `alembic current` in local dev (shows current revision)
3. `alembic upgrade head` in Docker init

**Mitigation:**
1. **`ALEMBIC_CTX` env var:** Allow auto-pass in CI and dev contexts when
   `ALLOW_SCHEMA_WRITE=yes`. CI and dev should set `ALEMBIC_CTX=ci` or
   `ALEMBIC_CTX=dev` and `ALLOW_SCHEMA_WRITE=yes` in their environment.
2. **Grace period:** Document that CI will need to set these env vars. If CI
   doesn't currently run Alembic, no action is needed.
3. **Docker init compatibility:** `deploy/docker/init_db.sql` is the primary
   Docker dev initialization path, NOT Alembic. Alembic migrations in the
   Docker dev context are supplementary. The guard won't break Docker dev boot
   because `init_db.sql` doesn't go through Alembic.

**Verification needed during implementation:**
- Check if CI runs `alembic` commands (check, current, upgrade, etc.)
- Check if Docker dev initialization runs `alembic`
- Check if any Makefile target invokes `alembic`

### Non-Goals of This Guard

The guard will NOT:
- Prevent `run_migrations_offline()` from generating SQL (offline mode is read-only)
- Validate the content of migration scripts (that's a review task)
- Prevent adding new migration scripts to `versions/` (that's a CI policy task)
- Replace the role of `deploy/docker/init_db.sql` guard (separate concern)
- Validate migration rollback paths or downgrade safety
- Enforce migration naming conventions
- Prevent `alembic stamp` operations (these can be needed for migration state repair)

## Implementation Plan

### Phase 1: Guard Implementation (future task)

**Task name:** `sc002_alembic_migration_runtime_guard_implementation`

**Steps:**
1. **Audit CI and dev workflows** for Alembic usage:
   - Check CI configs for `alembic` commands
   - Check Makefile targets for `alembic` invocations
   - Check Docker init flow for `alembic` usage
   - Check any shell scripts or README instructions
2. **Implement the guard** in `run_migrations_online()`:
   - Option A (preferred): Import `assert_db_write_allowed` from the existing guard
     helper. Handle import path setup (sys.path must include project root).
   - Option B (fallback): Inline a migration-specific guard using the same env-var
     and host detection logic as the existing helper.
3. **Add `ALEMBIC_CTX` support:** The guard reads `ALEMBIC_CTX` env var for context
   identification.
4. **Update `alembic.ini`:** Document the new env var requirements in comments.
5. **Update CI / dev configs:** Add `ALEMBIC_CTX=ci`, `ALEMBIC_CTX=dev`, or
   `ALEMBIC_CTX=docker_init` with `ALLOW_SCHEMA_WRITE=yes` where Alembic is legitimately
   used.
6. **Test the guard:** Verify that:
   - `alembic upgrade head` with no guard env vars is **blocked**
   - `alembic upgrade head` with `ALEMBIC_CTX=dev ALLOW_SCHEMA_WRITE=yes` is **allowed**
   - `alembic upgrade head` with production-like host in DATABASE_URL is **hard blocked**
   - `alembic upgrade head --sql` (offline mode) is **not blocked**
   - `alembic current` and `alembic check` behavior is correct for intended contexts
7. **Update allowlist:** Change `env.py` classification from `pending_runtime_guard`
   to `alembic_migration_runtime_guarded`.
8. **Update docs:** Update this design doc, `SC002_CLOSURE_PLAN.md`, and
   `PROJECT_STATUS.md`.

### Phase 2: CI Integration (after guard implementation)

1. Add `ALEMBIC_CTX=ci ALLOW_SCHEMA_WRITE=yes` to CI environment if CI runs Alembic
2. Ensure CI-only env vars are NOT set in development or production environments
3. Add a CI step that verifies the guard is active (negative test: blocked without vars)

### Phase 3: Production Migration Runbook (future)

When production schema migrations are needed in the future:
1. Operator sets `ALEMBIC_CTX=manual ALLOW_DB_WRITE=yes FINAL_DB_WRITE_CONFIRMATION=yes ALLOW_SCHEMA_WRITE=yes DRY_RUN=false`
2. Operator runs `alembic upgrade head` only against a verified non-production-like host
3. Audit logs record the migration run

## Impact Analysis

### What This Design Changes

| Item | Before | After |
|---|---|---|
| env.py classification | `pending_runtime_guard` (vague) | `alembic_migration_needs_specialized_runtime_guard` (precise) |
| Guard strategy | None | Documented, ready for implementation |
| Implementation readiness | Deferred, unclear approach | Clear plan with pseudocode and guard location |
| Tracking | Listed as "remaining" | Now has explicit category, design doc, and next task |

### What This Design Does NOT Change

- env.py runtime behavior — NO GUARD ADDED (this is design only)
- SC-002 status — remains partial mitigation only
- Python write paths guarded count — still 17 / 20
- Training / data expansion / real DB write — remain blocked
- Any database — no connection, no SQL, no migration execution
- Any existing CI or dev workflow

### Safety Boundary

This design task is a **documentation and planning task**. It:
- Reads and analyzes source code (env.py, alembic.ini, migration versions)
- Writes design documentation and plan
- Updates tracking configuration files
- Creates static tests that verify classification state
- Does NOT modify env.py runtime behavior
- Does NOT connect to any database
- Does NOT run any migration, SQL, scraper, browser, or training

## Related Documents

| Document | Relationship |
|---|---|
| `docs/SC002_CLOSURE_PLAN.md` | Parent document — tracks all SC-002 closure criteria |
| `docs/SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md` | Predecessor — original Python/SQL/migration inventory and design |
| `config/python_db_write_allowlist.json` | Configuration — env.py classification lives here |
| `config/sql_migration_policy_allowlist.json` | Configuration — cross-reference entry for env.py |
| `docs/PROJECT_STATUS.md` | Status dashboard — reflects current SC-002 state |
| `src/database/migrations/env.py` | Target file — the Alembic environment being analyzed |
| `src/database/migrations/alembic.ini` | Config — Alembic configuration referenced by env.py |
| `scripts/ops/helpers/python_db_write_guard.py` | Reference — existing guard helper pattern |

## Validation

### Static Tests Added

The implementation will add `tests/unit/test_sc002_alembic_migration_guard_design.py` with
tests that verify:

1. `env.py` is classified as `alembic_migration_needs_specialized_runtime_guard` in the allowlist
2. Python write paths guarded count is 17 out of 20
3. `env.py` is the only remaining unclassified Python write path
4. SC-002 remains partial mitigation only
5. Training / data expansion / real DB write remain blocked
6. The design document exists and has required sections

### Pre-Deploy Validation

- `py_compile` on the design doc? No — it's markdown
- `py_compile` on the test file? Yes
- `make pr-gate-local PR_BODY=/tmp/pr_body_alembic_migration_guard_design.md` — fast mode
- Existing tests must still pass (Phase2A scanner, Phase2B scanner, AI Workflow Gate)

## Next Recommended Task

**`sc002_alembic_migration_runtime_guard_implementation`** — Implement the runtime guard
in `env.py` following the design specified in this document.

Prerequisites:
- This design doc is merged to `main`
- CI and dev workflow audit completed (check if Alembic is used)
- User explicitly authorizes the guard implementation

The implementation task must:
1. Follow the guard strategy in this document
2. NOT execute any migration
3. NOT connect to any database
4. NOT perform any real DB write
5. NOT train or expand data
6. Verify guard behavior with dry-run tests
7. Update allowlist to `alembic_migration_runtime_guarded`

Do not start automatically. Recommended next task only after user confirmation.
