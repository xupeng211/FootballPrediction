# SC-002 Runtime DB Role / Permission Review — Phase 1

- lifecycle: permanent
- owner: project governance
- created: 2026-06-25
- task: runtime_db_role_permission_review_phase1
- review_type: static audit / documentation — no DB connection, no permission changes
- sc002_status: partial mitigation only

## Summary

This document provides a **static review** of the current database role, permission, and
runtime account model for the FootballPrediction system. It evaluates whether the current
model creates risks for production write safety (SC-002) and recommends a target model.

**This review does NOT:**
- Connect to any database
- Execute any SQL
- Modify any DB roles or permissions
- Run any migration or Alembic
- Perform any real DB write
- Run scraper / browser / Playwright
- Train or expand data
- Read or output real secrets or credentials

**This review DOES:**
- Statically analyze all DB user/role/connection configuration files
- Identify gaps between the current model and security best practices
- Recommend a target role model with privilege separation
- Recommend a minimal next task

**Sources analyzed:**
- `docker-compose.dev.yml` — dev DB user definitions
- `docker-compose.yml` — production service definitions
- `.env.example` — environment variable template
- `config/.env.example` — config-level env template
- `src/config/db_settings.py` — DatabaseConfig and DatabaseSettingsMixin
- `src/config/settings.py` — UnifiedSettings with get_settings()
- `src/config/common.py` — environment detection
- `deploy/docker/init_db.sql` — Docker dev schema initialization
- `deploy/docker/init_claude_reader.sql` — read-only MCP user creation
- `src/database/migrations/env.py` — Alembic migration environment
- `scripts/devops/gatekeeper.sh` — CI gatekeeper cold-start probe
- `scripts/maintenance/*.py` — maintenance scripts with DB connections
- `src/services/*.py` — service-layer DB connections
- `src/api/collectors/*.py` — data collector DB connections

## Current DB Role / Account Model

### Observed Users

| User | Source | Context | Privileges |
|---|---|---|---|
| `football_user` | `docker-compose.dev.yml`, `.env.example`, `db_settings.py` | **Universal** — app runtime, dev work, CI, migration, ingestion, training | Full DDL + DML on `football_db` (table owner) |
| `claude_reader` | `deploy/docker/init_claude_reader.sql` | MCP read-only PostgreSQL connection | SELECT only on all tables in `football_db` |
| `postgres` (admin) | `gatekeeper.sh` cold-start probe | Gatekeeper temporary DB creation | CREATEDB (via `admin_db=postgres`) |

### Connection Sources by Role

| Role | User | Key File(s) | Notes |
|---|---|---|---|
| **App runtime** (FastAPI) | `football_user` | `db_settings.py`, `docker-compose.dev.yml` | Uses `DatabaseConfig` with asyncpg/psycopg2 pool |
| **Dev / CLI work** | `football_user` | `docker-compose.dev.yml`, `env.py`, all scripts | All `make dev-*` and `docker compose exec` commands |
| **CI / Gatekeeper** | `football_user` | `gatekeeper.sh`, GitHub Actions | Cold-start blueprint replay, static enforcement scanners |
| **Alembic migrations** | `football_user` | `src/database/migrations/env.py` | Same user as app runtime — DDL mixed with DML |
| **Data ingestion** | `football_user` | `collector_repository.py`, `odds_api_client_v38.py`, `streaming_db_writer.py` | Full write access to all tables, not just ingestion targets |
| **Training** | `football_user` | `train_baseline_v1.py`, `predict_pipeline.py` | Full write access to all tables |
| **Maintenance** | `football_user` | `database_detox.py`, `reset_l2_collection.py`, `clean_corrupt_l2.py`, `fix_zombie_matches.py` | Full DDL/DML — can TRUNCATE, ALTER TABLE |
| **MCP read-only** | `claude_reader` | `init_claude_reader.sql` | SELECT only — properly restricted |
| **Gatekeeper cold-start** | `football_user` + `postgres` | `gatekeeper.sh` | Creates temporary database via `admin_db=postgres` |

### Password Management

| Context | Default Password | Storage | Risk |
|---|---|---|---|
| Docker dev | `football_pass` | `docker-compose.dev.yml` (inline) | Hardcoded — acceptable for local dev only |
| Docker production | `change-me-in-production` | `db_settings.py` (fallback) | Placeholder — must be overridden via env var |
| WSL2 development | `change-me-in-production` | `db_settings.py` (fallback) | Placeholder — low risk for local dev |
| Claude reader (MCP) | `claude_readonly_2026` | `init_claude_reader.sql` (inline) | Hardcoded — must be overridden in production |
| `.env.example` | `your_secure_password_here` | template file | Placeholder — must be filled by operator |

## Risk Analysis

### Risk 1: Single Super-User (HIGH)

`football_user` owns all tables and has full DDL + DML privileges. Every component —
app runtime, migrations, ingestion, training, maintenance, CI — connects as this
same user.

**Impact:** If any single component is compromised (e.g., a data collector with
network access), the attacker gains full read/write/drop access to the entire
database.

**Current mitigation:** Application-layer guard (`assert_db_write_allowed`) blocks
writes unless explicit env vars are set. This is effective but is a single layer —
a bypass at the application layer leaves the database fully exposed.

### Risk 2: Migration and Runtime Privileges Mixed (HIGH)

Alembic migrations (`env.py`) connect as `football_user` — the same user as app
runtime. A migration has DDL privileges (CREATE/ALTER/DROP TABLE), and the app
runtime also has these privileges.

**Impact:** A bug in app runtime code could accidentally execute DDL. Conversely,
a migration script could execute DML that should be reserved for app runtime.

**Current mitigation:** `env.py` now has a migration guard (`_check_alembic_migration_guard()`)
that requires `ALLOW_SCHEMA_WRITE=yes`. The app-level guard also blocks DDL without
`ALLOW_SCHEMA_WRITE=yes`. Both operate at the application layer, not the DB layer.

### Risk 3: No Read-Only App Runtime User (MEDIUM)

All read-only operations (health checks, SELECT queries, dashboard, MCP) use
`football_user` with full write privileges, except for MCP which has `claude_reader`.

**Impact:** A read-only query path that is compromised could be used to write data.
Connection strings for read-only use cases have full write credentials.

**Current mitigation:** The application-layer guard blocks writes by default
(`DRY_RUN=true`). MCP has a dedicated read-only user (`claude_reader`) — good
practice, but only used for MCP.

### Risk 4: Ingestion User Has Overly Broad Write Access (MEDIUM)

Data collection scripts connect as `football_user` and can write to ALL tables,
not just the specific tables they need (e.g., `matches`, `raw_match_data`, `odds`).

**Impact:** A misconfigured ingestion script could accidentally write to training
tables, predictions, or registry tables.

**Current mitigation:** Table-level gates (`ALLOW_RAW_MATCH_DATA_WRITE`,
`ALLOW_MATCHES_WRITE`, `ALLOW_ODDS_WRITE`) in the application-layer guard limit
which tables can be written to.

### Risk 5: Training User Has Full Write Access (MEDIUM)

Training scripts connect as `football_user` with full write access.

**Impact:** Training could accidentally write to production data tables instead of
training-specific tables.

**Current mitigation:** `ALLOW_TRAINING_WRITE` gate in the application-layer guard.

### Risk 6: Hardcoded Credentials in Source Control (MEDIUM)

- `football_pass` in `docker-compose.dev.yml` — acceptable for local dev
- `claude_readonly_2026` in `init_claude_reader.sql` — should be env var
- `change-me-in-production` placeholder in `db_settings.py` — should fail loudly if not overridden

### Risk 7: Application-Layer Only Protection (MEDIUM)

All SC-002 write protection is at the application layer (env var gates +
`assert_db_write_allowed`). If the application-layer guard is bypassed
(e.g., direct psql connection, script that doesn't import the guard),
the database offers no additional protection.

**Impact:** A single unguarded script or direct DB connection can bypass all
SC-002 protections.

### Risk 8: No Environment-Specific DB Users (LOW-MEDIUM)

Dev, staging, and production all use the same user naming convention
(`football_user`). There is no mechanism to prevent a dev-configured script
from accidentally connecting to a production database (beyond the
production-host hard block in the guard helper).

**Current mitigation:** Production-like host detection in the guard helper
blocks writes to RDS, Cloud SQL, Supabase, etc.

## Recommended Target Model

### Proposed PostgreSQL Roles

| Role | Privileges | Used By | Current State |
|---|---|---|---|
| `football_owner` | Full DDL + DML (table owner) | Schema migrations, admin maintenance | No — currently `football_user` |
| `football_app` | SELECT, INSERT, UPDATE on all tables; no DDL | FastAPI app runtime | No — currently `football_user` |
| `football_ingestion` | INSERT, UPDATE on matches, raw_match_data, odds tables only | Data collectors, streaming writers | No — currently `football_user` |
| `football_training` | SELECT on all tables; INSERT, UPDATE on training/predictions tables only | Training pipelines | No — currently `football_user` |
| `football_reader` | SELECT on all tables | MCP, health checks, dashboards, read-only audits | Partially — `claude_reader` exists for MCP only |
| `football_gatekeeper` | CREATEDB (temporary), SELECT on all tables | CI cold-start blueprint check | Partially — uses `postgres` admin + `football_user` |

### Transition Principles

1. **Least privilege:** Each role gets only the minimum privileges needed.
2. **Defense in depth:** DB-layer roles complement (not replace) application-layer guards.
3. **No production defaults:** All production passwords come from environment variables
   or a secrets manager.
4. **Backward compatibility:** Existing scripts continue to work during transition
   (e.g., `football_user` is renamed to `football_owner` with a compatibility alias).
5. **Dev environment unchanged:** `docker-compose.dev.yml` continues to use a single
   user for development simplicity. Role separation applies to staging/production.

### Implementation Phases

**Phase 1 (this task — COMPLETED):** Static audit and target model design.
**Phase 2 (future):** Implement role separation in Docker dev environment as proof-of-concept.
**Phase 3 (future):** Deploy to staging. Update connection configs per component.
**Phase 4 (future):** Deploy to production. Validate with read-only health checks first.

## Minimal Next Task

**Apply the proposed role model in `deploy/docker/init_db.sql` and `docker-compose.dev.yml`
as a dev-only proof-of-concept.**

This is a safe first step because:
- It only affects the Docker dev environment.
- It validates the role model works before touching staging/production.
- It can be tested with `make dev-up` and existing test suites.
- Rollback is simple: revert the SQL and compose changes.

**Scope:** Only `deploy/docker/init_db.sql` and `docker-compose.dev.yml`. No runtime
code changes. No production changes.

**Forbidden:** Connect to production DB, modify live permissions, execute GRANT/REVOKE
against any non-dev database. Training, data expansion, and real DB write remain blocked.

**Do not start automatically.** Recommended next task only after user confirmation.

## Uncertainties

1. **Production environment:** The current codebase has no production deployment
   configuration beyond `docker-compose.yml`. The exact production DB host, user,
   and permission model are unknown from static analysis alone. This review is
   based on dev/Docker configurations.

2. **Existing production DB state:** If a production database exists, its current
   role configuration is unknown. Any role changes must be tested in staging first.

3. **Connection pool impact:** Changing the DB user per component requires updating
   connection pool configurations. The impact on connection count and pool sizing
   is not assessed here.

4. **Flyway vs. Alembic:** The repository has both Flyway-style SQL migrations
   (`database/migrations/*.sql`) and Alembic migrations (`src/database/migrations/`).
   Which is authoritative for production schema management is unclear.

5. **Gateway/proxy DB access:** The `host.docker.internal` pattern in dev compose
   suggests the dev container accesses the host's DB. The production network topology
   for DB access is unknown.

## Explicit Non-Goals

This review does NOT:
- Connect to any database
- Execute any SQL
- Modify any DB roles or permissions
- Run any migration or Alembic
- Perform any real DB write
- Run scraper / browser / Playwright
- Train or expand data
- Read or output real secrets or credentials
- Claim SC-002 is complete
- Claim "safe to train," "safe to write," or "production ready"

## References

| Document | Relevance |
|---|---|
| `docs/SC002_CLOSURE_PLAN.md` §6 Criterion #6 | This review addresses criterion #6 |
| `docs/SC002_OVERALL_CLOSURE_ASSESSMENT.md` | Overall SC-002 gap analysis |
| `src/config/db_settings.py` | DatabaseConfig + environment detection |
| `deploy/docker/init_db.sql` | Schema DDL — no role creation beyond tables |
| `deploy/docker/init_claude_reader.sql` | Only existing role separation (read-only MCP) |
| `scripts/ops/helpers/python_db_write_guard.py` | Application-layer guard — current primary protection |
| `src/database/migrations/env.py` | Alembic migration environment — now guarded |
