# SC-002 Staging DB Role Deployment Plan

- lifecycle: permanent
- owner: project governance
- created: 2026-06-25
- task: sc002_staging_db_role_deployment_plan
- plan_type: deployment planning / documentation only — NO execution
- sc002_status: enforcement infrastructure complete; staging role deployment pending

## Summary

This document provides the **deployment plan** for applying the SC-002 6-role
least-privilege DB permission model to a **staging** PostgreSQL environment. It is a
**planning document only** — no deployment steps have been executed.

**This plan does NOT:**
- Connect to any database
- Execute any SQL or psql
- Modify any real DB roles or permissions
- Modify production/staging runtime configuration
- Run any migration or Alembic
- Run scraper / browser / Playwright
- Train or expand data
- Perform any real DB write
- Read or output real secrets or credentials
- Unlock training, data expansion, or real DB write

**This plan DOES:**
- Document the target 6-role model for staging
- Define pre-deployment prerequisites and checks
- Provide deployment step drafts (not executed)
- Provide a rollback plan
- Define a validation matrix
- Provide a go/no-go checklist

## Background

The SC-002 DB write safety enforcement infrastructure is complete, but the 6-role
least-privilege DB permission model has only been implemented as a **dev POC** in
`deploy/docker/init_db.sql`. The dev POC runs inside Docker containers with dev-only
placeholder passwords and is not applied to any staging or production environment.

Deploying the role model to staging is the next logical step before production
deployment. This plan covers the staging deployment only. Production deployment
requires a separate, production-specific plan.

## Target 6-Role Model

Based on the design in `docs/SC002_RUNTIME_DB_ROLE_PERMISSION_REVIEW_PHASE1.md`
and the dev POC in `deploy/docker/init_db.sql`.

| # | Role | Purpose | DDL | DML | Scope |
|---|---|---|---|---|---|
| 1 | `football_owner` | DDL / migrations / admin | Yes | Yes | ALL PRIVILEGES on `football_db` |
| 2 | `football_app` | Runtime DML (FastAPI, CLI) | No | SELECT, INSERT, UPDATE | All tables. No DDL, no DELETE/TRUNCATE |
| 3 | `football_ingestion` | Data collection / ingestion | No | SELECT all, INSERT, UPDATE limited | `matches`, `raw_match_data`, `odds` tables only |
| 4 | `football_training` | Training / prediction | No | SELECT all, INSERT, UPDATE limited | `match_features_training`, `predictions`, `training_*` tables only |
| 5 | `football_reader` | Read-only (MCP, health, dashboards) | No | SELECT only | All tables |
| 6 | `football_gatekeeper` | CI / probe / cold-start validation | CREATEDB (temp only) | SELECT only | All tables; temporary DB create via admin_db |

**Key design principle:** No single role has both DDL and runtime DML. The
`football_user` universal account is replaced by 6 role-separated accounts.

## Staging Deployment Prerequisites

Before any deployment step is executed, ALL of the following must be confirmed:

### Environment Prerequisites

- [ ] Staging PostgreSQL host identified and confirmed (NOT production)
- [ ] Staging database name confirmed (`football_db` or equivalent)
- [ ] `football_user` (universal) staging password confirmed available
- [ ] Staging DB backup completed and verified (pg_dump or snapshot)
- [ ] All active staging connections/services identified
- [ ] Service owners notified of planned maintenance window
- [ ] Monitoring/alerting dashboards confirmed operational
- [ ] Rollback account (superuser/`postgres`) access confirmed

### Safety Prerequisites

- [ ] Production DB host confirmed excluded (triple-check hostname)
- [ ] `PRODUCTION_DB_HOST_PATTERNS` in `python_db_write_guard.py` would block staging DB writes — confirm staging host is NOT in the production patterns list
- [ ] `assert_db_write_allowed` would block writes without env vars — confirm `ALLOW_DB_WRITE=yes` and `ALLOW_SCHEMA_WRITE=yes` are set only for the deployment session
- [ ] All secrets provided via secure channel (env vars, vault, or operator input) — NOT written to any repo file
- [ ] Gate B guard in `init_db.sql` (`sc002.init_sql_context`) is understood — this SQL file is for dev Docker only and MUST NOT be used for staging deployment
- [ ] Training, data expansion, and real DB write remain **blocked** — this deployment does not change their blocked status

### Access Prerequisites

- [ ] Operator has `postgres` superuser or equivalent on staging DB
- [ ] Operator can create roles, grant privileges, and alter default privileges
- [ ] Operator can connect via psql or equivalent SQL client
- [ ] Operator has confirmed the target is staging (not production)

## Deployment Step Drafts

**IMPORTANT: These are DRAFT steps. Do NOT execute without explicit authorization
and staging access confirmation. All SQL shown is illustrative — real passwords
must come from a secrets source, not from this document.**

### Step 0: Preflight Read-Only Inspection

```sql
-- Verify staging DB identity (NOT production)
SELECT current_database(), inet_server_addr(), version();

-- List existing roles
SELECT rolname, rolsuper, rolcreaterole, rolcreatedb, rolcanlogin
FROM pg_catalog.pg_roles
WHERE rolname LIKE 'football_%' OR rolname = 'claude_reader'
ORDER BY rolname;

-- List existing table grants for football_user
SELECT grantee, table_schema, table_name, privilege_type
FROM information_schema.table_privileges
WHERE grantee = 'football_user'
ORDER BY table_name, privilege_type;
```

### Step 1: Create Roles

Create all 6 roles. Passwords must be provided via secure channel — use
`\prompt` in psql or set PGPassword env var. Do NOT hardcode passwords.

```sql
-- football_owner: DDL + migration owner
CREATE ROLE football_owner WITH LOGIN PASSWORD :'owner_password';
GRANT ALL PRIVILEGES ON DATABASE football_db TO football_owner;

-- football_app: runtime DML, no DDL
CREATE ROLE football_app WITH LOGIN PASSWORD :'app_password';
GRANT CONNECT ON DATABASE football_db TO football_app;
GRANT USAGE ON SCHEMA public TO football_app;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO football_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO football_app;

-- football_ingestion: write-limited to ingestion tables
CREATE ROLE football_ingestion WITH LOGIN PASSWORD :'ingestion_password';
GRANT CONNECT ON DATABASE football_db TO football_ingestion;
GRANT USAGE ON SCHEMA public TO football_ingestion;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO football_ingestion;
GRANT INSERT, UPDATE ON matches, raw_match_data, odds TO football_ingestion;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO football_ingestion;

-- football_training: training/prediction limited write
CREATE ROLE football_training WITH LOGIN PASSWORD :'training_password';
GRANT CONNECT ON DATABASE football_db TO football_training;
GRANT USAGE ON SCHEMA public TO football_training;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO football_training;
GRANT INSERT, UPDATE ON match_features_training, predictions TO football_training;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO football_training;

-- football_reader: SELECT only
CREATE ROLE football_reader WITH LOGIN PASSWORD :'reader_password';
GRANT CONNECT ON DATABASE football_db TO football_reader;
GRANT USAGE ON SCHEMA public TO football_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO football_reader;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO football_reader;

-- football_gatekeeper: CI/probe, SELECT only, temp CREATEDB
CREATE ROLE football_gatekeeper WITH LOGIN PASSWORD :'gatekeeper_password';
ALTER ROLE football_gatekeeper CREATEDB;
GRANT CONNECT ON DATABASE football_db TO football_gatekeeper;
GRANT USAGE ON SCHEMA public TO football_gatekeeper;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO football_gatekeeper;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO football_gatekeeper;
```

### Step 2: Set Default Privileges

Ensure future tables/sequences inherit correct privileges:

```sql
-- Owner default privileges (inherits ALL by default)
ALTER DEFAULT PRIVILEGES FOR ROLE football_owner IN SCHEMA public
    GRANT ALL PRIVILEGES ON TABLES TO football_owner;
ALTER DEFAULT PRIVILEGES FOR ROLE football_owner IN SCHEMA public
    GRANT ALL PRIVILEGES ON SEQUENCES TO football_owner;

-- App default privileges
ALTER DEFAULT PRIVILEGES FOR ROLE football_owner IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE ON TABLES TO football_app;
ALTER DEFAULT PRIVILEGES FOR ROLE football_owner IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO football_app;

-- Ingestion default privileges
ALTER DEFAULT PRIVILEGES FOR ROLE football_owner IN SCHEMA public
    GRANT SELECT ON TABLES TO football_ingestion;
ALTER DEFAULT PRIVILEGES FOR ROLE football_owner IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO football_ingestion;

-- Training default privileges
ALTER DEFAULT PRIVILEGES FOR ROLE football_owner IN SCHEMA public
    GRANT SELECT ON TABLES TO football_training;
ALTER DEFAULT PRIVILEGES FOR ROLE football_owner IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO football_training;

-- Reader default privileges
ALTER DEFAULT PRIVILEGES FOR ROLE football_owner IN SCHEMA public
    GRANT SELECT ON TABLES TO football_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE football_owner IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO football_reader;

-- Gatekeeper default privileges
ALTER DEFAULT PRIVILEGES FOR ROLE football_owner IN SCHEMA public
    GRANT SELECT ON TABLES TO football_gatekeeper;
ALTER DEFAULT PRIVILEGES FOR ROLE football_owner IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO football_gatekeeper;
```

### Step 3: Update Staging Service Environment Variables

Update the staging environment (docker-compose, .env, or secrets manager) to use
role-specific credentials instead of the universal `football_user`:

| Component | Current User | Target User | Env Var(s) |
|---|---|---|---|
| Alembic / migrations | `football_user` | `football_owner` | `DB_OWNER_USER`, `DB_OWNER_PASSWORD` |
| FastAPI app runtime | `football_user` | `football_app` | `DB_APP_USER`, `DB_APP_PASSWORD` |
| Data collectors / ingestion | `football_user` | `football_ingestion` | `DB_INGESTION_USER`, `DB_INGESTION_PASSWORD` |
| Training pipeline | `football_user` | `football_training` | `DB_TRAINING_USER`, `DB_TRAINING_PASSWORD` |
| Health checks / MCP / dashboards | `football_user` | `football_reader` | `DB_READER_USER`, `DB_READER_PASSWORD` |
| CI gatekeeper probes | `football_user` | `football_gatekeeper` | `DB_GATEKEEPER_USER`, `DB_GATEKEEPER_PASSWORD` |

**Important:** The `football_user` universal account should remain in place during
the transition. Decommission `football_user` only after all services are verified
on their new role-specific accounts.

### Step 4: Non-Destructive Permission Probes

After role creation and service env var updates, run permission probes to validate
each role's access. These are non-destructive SELECT/function checks.

```sql
-- Probe: football_reader can SELECT (expected: SUCCESS)
SET ROLE football_reader;
SELECT count(*) FROM matches LIMIT 1;

-- Probe: football_reader cannot INSERT (expected: ERROR - permission denied)
SET ROLE football_reader;
INSERT INTO matches (match_id, home_team, away_team) VALUES ('_probe_', 'X', 'Y');

-- Probe: football_app can INSERT (expected: SUCCESS)
SET ROLE football_app;
-- (use a dry-run or rollback-only probe)

-- Probe: football_app cannot CREATE TABLE (expected: ERROR - permission denied)
SET ROLE football_app;
CREATE TABLE _probe_table_ (id int);

-- Probe: football_ingestion on non-ingestion table (expected: ERROR)
SET ROLE football_ingestion;
UPDATE match_features_training SET _probe_ = 1 WHERE false;

-- Probe: football_owner can run migration (expected: SUCCESS)
SET ROLE football_owner;
CREATE TABLE IF NOT EXISTS _probe_migration_test_ (id int);
DROP TABLE IF EXISTS _probe_migration_test_;
```

### Step 5: Validate Each Role

Run the validation matrix (see §Validation Matrix below). Each role's expected
behavior must match actual behavior. Any deviation must be resolved before
proceeding.

## Validation Matrix

| Operation | `owner` | `app` | `ingestion` | `training` | `reader` | `gatekeeper` |
|---|---|---|---|---|---|---|
| SELECT matches | Allow | Allow | Allow | Allow | Allow | Allow |
| SELECT raw_match_data | Allow | Allow | Allow | Allow | Allow | Allow |
| INSERT matches | Allow | Allow | Allow | Deny | Deny | Deny |
| UPDATE matches | Allow | Allow | Allow | Deny | Deny | Deny |
| DELETE matches | Allow | Deny | Deny | Deny | Deny | Deny |
| INSERT raw_match_data | Allow | Allow | Allow | Deny | Deny | Deny |
| INSERT match_features_training | Allow | Allow | Deny | Allow | Deny | Deny |
| CREATE TABLE | Allow | Deny | Deny | Deny | Deny | Deny |
| ALTER TABLE | Allow | Deny | Deny | Deny | Deny | Deny |
| DROP TABLE | Allow | Deny | Deny | Deny | Deny | Deny |
| TRUNCATE | Allow | Deny | Deny | Deny | Deny | Deny |
| GRANT / REVOKE | Allow | Deny | Deny | Deny | Deny | Deny |
| CREATE DATABASE (temp) | Allow | Deny | Deny | Deny | Deny | Allow |
| Production host | **Blocked** | **Blocked** | **Blocked** | **Blocked** | **Blocked** | **Blocked** |

Legend: Allow = operation should succeed. Deny = operation should fail with permission error.
Blocked = application-layer guard rejects regardless of DB permissions.

## Rollback Plan

If any validation step fails or unexpected issues arise, roll back as follows:

### Immediate Rollback (during deployment window)

1. **Revert env vars:** Switch all staging services back to `football_user` credentials.
   This is the fastest rollback — env var changes take effect on service restart.
2. **Verify connectivity:** Confirm all services are operational with `football_user`.
3. **Revoke new roles (optional):** If roles should not persist:
   ```sql
   REVOKE ALL PRIVILEGES ON DATABASE football_db FROM football_owner, football_app, football_ingestion, football_training, football_reader, football_gatekeeper;
   REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM football_owner, football_app, football_ingestion, football_training, football_reader, football_gatekeeper;
   DROP ROLE IF EXISTS football_owner, football_app, football_ingestion, football_training, football_reader, football_gatekeeper;
   ```
4. **Audit trail:** Record the rollback in the deployment log with timestamp, reason,
   and operator identity.

### Delayed Rollback (post-deployment window)

1. Same steps as immediate rollback, but also verify no data was written with new roles
   that would be orphaned by role deletion.
2. Check application logs for any permission errors during the new-role window.

### Rollback Safety Rules

- Production DB must NEVER be targeted during rollback (same host-check rules as deployment).
- Rollback must be tested conceptually before deployment begins.
- The `postgres` superuser account must remain available throughout for emergency access.
- `football_user` must NOT be dropped until all services are verified on new roles.

## Go / No-Go Checklist

Before executing any deployment step, ALL items must be checked:

### Go Criteria (all must be YES)

- [ ] Staging DB backup completed and verified within last 24 hours
- [ ] Staging DB host confirmed (NOT production — triple-checked)
- [ ] Production DB host explicitly excluded from all deployment commands
- [ ] All 6 role passwords generated and provided via secure channel
- [ ] No passwords, secrets, or credentials written to any repo file
- [ ] Service owners notified of planned maintenance window
- [ ] Rollback plan reviewed and accepted
- [ ] Validation matrix printed and ready for manual check-off
- [ ] Monitoring dashboards confirmed operational (before/after comparison)
- [ ] `football_user` credentials confirmed available for emergency rollback
- [ ] Superuser (`postgres`) access confirmed for emergency operations

### No-Go Criteria (any YES = STOP)

- [ ] Production DB host is in any deployment command, script, or env var
- [ ] Any real secret or password exists in a repo file
- [ ] Training, data expansion, or real DB write is attempted during deployment
- [ ] `deploy/docker/init_db.sql` is used for staging deployment (it is dev-only)
- [ ] The `ALLOW_PRODUCTION_DB_WRITE` variable is set (must never exist)
- [ ] The `sc002.init_sql_context` guard is bypassed or modified
- [ ] Any unguarded DB write script is executed without explicit authorization

### Post-Deployment Verification (before closing window)

- [ ] All 6 roles created and visible in `pg_roles`
- [ ] Validation matrix completed with expected results (no surprises)
- [ ] Application-layer guard (`assert_db_write_allowed`) tested with each role
- [ ] Staging services operational with new role-specific credentials
- [ ] Monitoring shows no anomalous errors or permission failures
- [ ] Rollback window documented (how long until rollback becomes more complex)

## What This Plan Does NOT Do

This plan explicitly does NOT:

- Execute any SQL against any database
- Modify any real DB roles, permissions, or configuration
- Deploy to production
- Unlock training, data expansion, or real DB write
- Modify staging/production runtime configuration
- Create or distribute real secrets or credentials
- Change the SC-002 enforcement infrastructure
- Replace the dev-only `deploy/docker/init_db.sql` guard
- Claim staging deployment is complete
- Claim any blocked action is now safe or authorized

## What Happens After Staging Deployment

After successful staging deployment and validation:

1. The role model runs in staging for an observation period (recommended: 1-2 weeks).
2. Any permission issues or missing grants are identified and resolved.
3. A production deployment plan is created, adapted from this staging plan with
   production-specific hostnames, secrets management, and rollback procedures.
4. SC-002 criterion #6 is updated from "substantially met" to "fully met" when both
   staging and production have the role model deployed.

## Next Steps

1. Obtain explicit staging access authorization from the project owner.
2. Generate role-specific passwords via a secure secrets manager.
3. Confirm staging backup is current.
4. Schedule a maintenance window with service owners.
5. Execute deployment steps per this plan.
6. Run validation matrix.
7. Observe staging for 1-2 weeks.
8. Create production deployment plan.

Do not start automatically. Each step requires explicit authorization.
