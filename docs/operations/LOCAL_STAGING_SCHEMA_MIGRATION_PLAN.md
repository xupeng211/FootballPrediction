# Local Staging Schema and Migration Plan

- lifecycle: current-state
- owner: project governance
- task: local_staging_phase5p_staging_schema_migration_plan_docs_only
- issue: #1636
- status: planning documentation only

## Purpose

This document defines the local staging schema and migration governance boundary.

It exists because local staging can have healthy infrastructure before schema
migration is applied. The local staging API, container, PostgreSQL service, and
Redis service can be available while DB-backed business endpoints are not ready.

This document is governance and planning documentation. It is not authorization
to execute migration.

## Current Status

Local staging PostgreSQL can be healthy while the schema is empty.

The current empty-schema state is expected during bootstrap. The Phase 5 local
staging audit recorded that the database could exist with 0 non-system tables.
That state is not a migration failure by itself.

No migration has been authorized or executed as part of bootstrap. Migration and
Alembic execution remain outside the current authorization boundary.

DB-backed business endpoints may fail until schema and migration are applied and
validated. This does not mean API or container startup failed.

## Expected Empty-Schema Behavior

An empty local staging schema is expected before an authorized migration task.

`/health` may report API or container availability separately from DB-backed
business readiness. A healthy API process does not prove tables, migrations, or
business endpoints are ready.

Business endpoints depending on tables should not be assumed ready while the
schema is empty. Prediction and data endpoints requiring tables are blocked until
an authorized migration and validation task confirms the schema state.

This plan does not call `/health/quick`, `/predict`, or any DB-backed endpoint.

## Schema and Migration Source of Truth

The repository currently contains multiple schema and migration references:

- `database/migrations/*.sql` contains SQL migration files.
- `src/database/migrations/alembic.ini` and `src/database/migrations/env.py`
  define the Alembic migration environment.
- `src/database/migrations/versions/` contains Alembic revision files.
- `Makefile` exposes `data-schema-help`, `data-schema-status`,
  `data-schema-plan`, and blocked `data-schema-migrate` safety gates.
- `docs/_reports/DB_SCHEMA_MIGRATION_RUNBOOK_PHASE4_8.md` is a historical
  migration runbook draft, not proof that local staging migration is complete.
- `MIGRATION.md` is historical schema guidance and must not be treated as a
  current execution plan by itself.
- `deploy/docker/init_db.sql` is the dev Docker bootstrap schema and SC-002
  dev-only role proof of concept. It must not be treated as a staging migration
  execution path.

Because both SQL migration files and Alembic migration files exist, the future
authorized migration task must first identify the source of truth and exact
execution path. If the source of truth is unclear at that time, the task must
stop at pending discovery and must not run migration.

This PR does not define a real migration command.

## Migration Authorization Boundary

This document is a plan, not authorization to migrate.

A future migration run requires explicit user authorization. The authorization
must name:

- target environment
- target DB
- migration command or execution path
- expected schema state before and after migration
- rollback plan
- validation plan

No production DB may be touched.

No staging DB may be touched by this PR.

No migration, Alembic command, SQL, Docker command, staging host operation, or
SC-002 role deployment is authorized by this document.

## Pre-Migration Preconditions

Before any future migration task can run, all of the following must be true:

- [ ] Target environment is explicitly authorized by the user.
- [ ] Target DB identity is confirmed without exposing secrets.
- [ ] Production DB protection is confirmed.
- [ ] SC-002 role and governance implications are reviewed.
- [ ] #1637 staging DB role deployment status is reviewed and not assumed
      complete.
- [ ] #1632 `DB_NAME` validation status is reviewed or explicitly accepted as
      pending for the migration task.
- [ ] #1633 `DB_SSL_MODE` semantics status is reviewed or explicitly accepted
      as pending for the migration task.
- [ ] Migration source of truth is identified.
- [ ] Backup and rollback approach is documented.
- [ ] Validation checklist is prepared.
- [ ] No scraper, training, data expansion, or pipeline worker is running.
- [ ] No model artifact deployment is coupled into the migration task.

## Future Migration Procedure Placeholder

The following is a placeholder only. It is not executable by this PR.

Do not run these steps without a separate authorized task.

A future authorized task should define its own concrete commands and may use
this high-level flow:

1. Confirm the target environment.
2. Confirm DB identity and safety boundary.
3. Confirm migration source of truth.
4. Prepare backup and rollback.
5. Run migration only after explicit authorization.
6. Validate schema.
7. Validate API health and DB-backed readiness only after explicit authorization.

The future task must provide the actual command, expected output, stop
conditions, and rollback decision points before any execution begins.

## Validation Checklist

Before declaring local staging schema ready, a future authorized task must
record:

- [ ] Working target environment confirmed.
- [ ] Production DB not used.
- [ ] Staging DB identity confirmed.
- [ ] Migration revision or source recorded.
- [ ] Expected schema tables documented.
- [ ] Actual schema tables documented after migration.
- [ ] Rollback readiness confirmed.
- [ ] `/health` interpretation documented.
- [ ] DB-backed endpoint validation separately authorized.
- [ ] No training, scraper, data expansion, or pipeline worker started.
- [ ] No model artifact generated or deployed as part of migration.

## Rollback Plan

Rollback must be defined before migration.

Rollback must not bypass SC-002 or DB safety controls.

The future authorized task must document the rollback target, restore method,
backup location or snapshot reference, operator confirmation, and validation
steps.

No rollback SQL is executed by this PR.

## Explicit Non-Goals

This PR does not connect to any DB.

This PR does not execute SQL.

This PR does not run Alembic.

This PR does not run migration.

This PR does not create, alter, or drop tables.

This PR does not deploy SC-002 DB roles.

This PR does not modify Docker, Compose, or env files.

This PR does not modify application code.

This PR does not operate the staging host.

This PR does not touch production DB.

This PR does not start scraper, training, or pipeline workers.

This PR does not generate or deploy model artifacts.

This PR does not call `/predict`.

This PR does not call `/health/quick`.

## Relationship to SC-002, DB Config, and Model Artifacts

#1637 SC-002 staging DB role deployment remains pending. This document does not
complete, authorize, or execute SC-002 role deployment.

#1632 `DB_NAME` validation remains pending. This document does not change DB
name validation behavior.

#1633 `DB_SSL_MODE` semantics remain pending. This document does not change DB
SSL parsing or connection behavior.

#1635 model artifact governance was documented separately in
`docs/operations/LOCAL_STAGING_MODEL_ARTIFACTS.md`. Model artifact deployment
remains separate from schema migration.

#1629 image CMD behavior remains separate. This document does not change Docker
image strategy, Dockerfile defaults, or Compose command overrides.

This document does not imply that #1637 is complete. It does not authorize
migration execution. It does not resolve #1632 or #1633.

## Related Issues

- Closes #1636.
- #1637 remains pending.
- #1632 remains pending.
- #1633 remains pending.
- #1635 was completed by PR #1643.
- #1629 remains separate.
