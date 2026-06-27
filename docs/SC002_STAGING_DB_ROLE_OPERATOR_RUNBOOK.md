# SC-002 Staging DB Role Operator Runbook

- lifecycle: permanent
- owner: project governance
- issue: #1637
- task: sc002_staging_db_role_operator_runbook
- scope: staging DB role deployment operator checklist
- status: documentation only — no execution performed

## 1. Purpose

This runbook turns the existing SC-002 staging DB role deployment design into an operator checklist.

It is intended for a future, explicitly authorized staging DB role deployment window.

**This document does not authorize execution by itself.**

## 2. Current Status

SC-002 enforcement infrastructure is complete, but staging DB role deployment remains pending.

The staging database has not yet been updated with the SC-002 6-role least-privilege model.

Until the staging role deployment is executed and validated:

- real DB writes remain blocked
- training remains blocked
- data expansion remains blocked
- `pipeline_worker` remains fail-fast
- #1637 remains open
- #1656 remains blocked by #1637

## 3. Non-Goals

This runbook does not:

- connect to any database
- execute SQL
- run psql
- create, alter, drop, grant, or revoke DB roles
- run Alembic or migrations
- modify production or staging runtime configuration
- start scraper, training, prediction, or pipeline jobs
- start Docker containers
- read or print secrets
- authorize production deployment

Production deployment requires a separate production-specific plan.

## 4. Source Documents

This runbook is derived from:

- `docs/SC002_STAGING_DB_ROLE_DEPLOYMENT_PLAN.md`
- `docs/SC002_FINAL_CLOSURE_CHECK.md`
- `docs/SC002_RUNTIME_DB_ROLE_PERMISSION_REVIEW_PHASE1.md`
- `deploy/docker/init_db.sql` dev POC
- `.env.example` role-specific credential templates
- JS and Python DB write guards

## 5. Hard Authorization Gate

Do not execute any staging DB operation unless **all** of the following are true:

- project owner explicitly authorizes this exact execution window
- operator identity is known and recorded
- target DB host is confirmed as staging
- target DB name is confirmed
- production DB host is explicitly excluded
- current staging backup or snapshot exists
- rollback account access is confirmed
- all secrets are provided through a secure non-repo channel
- validation checklist is printed or otherwise ready for manual check-off
- rollback plan is reviewed and accepted

If any item is missing, **stop**.

## 6. Production Hard Stop

The operator must stop immediately if:

- the DB host resembles production
- the environment is production-like
- `ALLOW_PRODUCTION_DB_WRITE` exists anywhere in the execution environment
- any command points to a production DB hostname
- any command points to a production DB credential
- any production secret appears in a local file
- the operator cannot prove the target is staging

Production DB must **never** be targeted by this runbook.

Production host patterns that SHALL NOT match the staging target:

```
rds.amazonaws.com, .rds.amazonaws, cloudsql.google, .supabase., .supabase.co,
.vercel, .fly.dev, .railway.app, .render.com, .heroku,
prod-db, db.prod, db.production, production-db
```

## 7. Target Identity Check

Before any write-capable step, perform a **read-only identity check**.

Example inspection query draft:

```sql
SELECT current_database(), inet_server_addr(), inet_server_port(), version();
```

The operator must record:

- timestamp
- hostname
- database name
- server address
- operator identity
- confirmation that the target is staging
- confirmation that the target is **not** production

Do not proceed if identity is unclear.

## 8. Target 6-Role Model

The target staging role model is:

| Role | Purpose | DDL | DML | Scope |
|------|---------|:---:|:---:|-------|
| `football_owner` | DDL / migration / admin | yes | yes | all privileges on target DB |
| `football_app` | normal runtime DML | no | yes | SELECT / INSERT / UPDATE on all tables; no DDL |
| `football_ingestion` | collection / ingestion | no | limited | SELECT all; INSERT / UPDATE on ingestion tables |
| `football_training` | training / prediction | no | limited | SELECT all; INSERT / UPDATE on training / prediction tables |
| `football_reader` | read-only access | no | no | SELECT only |
| `football_gatekeeper` | CI / probes / cold-start validation | temp CREATEDB only | no | SELECT only plus temporary DB create for probes |

The old universal `football_user` account must remain available during transition and rollback.

Do **not** drop `football_user` during the staging deployment window.

## 9. Secret Handling

Passwords must be generated and distributed **outside the repository**.

Never write real passwords into:

- repo files
- issue comments
- PR descriptions
- logs
- screenshots
- copied terminal output

Use placeholders in documentation:

```text
<OWNER_PASSWORD>
<APP_PASSWORD>
<INGESTION_PASSWORD>
<TRAINING_PASSWORD>
<READER_PASSWORD>
<GATEKEEPER_PASSWORD>
```

## 10. Pre-Flight Checklist

All items must be checked before execution:

- [ ] project owner authorization recorded
- [ ] operator identity recorded
- [ ] staging DB host confirmed
- [ ] staging DB name confirmed
- [ ] production DB excluded
- [ ] staging backup / snapshot completed within 24 hours
- [ ] rollback account / superuser access confirmed
- [ ] `football_user` credentials available for rollback
- [ ] all 6 role passwords generated via secure channel
- [ ] maintenance window approved if needed
- [ ] monitoring / logs available
- [ ] validation matrix ready
- [ ] rollback plan reviewed
- [ ] no scraper / training / pipeline job running
- [ ] no secrets written into repo files

If any item is unchecked, **stop**.

## 11. Deployment Step Drafts

The following steps are draft operator guidance.

They are **not executed** by this document.

### Step A — Read-only inspection

Inspect DB identity, existing roles, and current grants.

Expected evidence:

- target DB identity recorded
- existing `football_%` roles listed
- current `football_user` grants listed

### Step B — Create or update roles

Create the six target roles only after authorization and backup.

Use secure password input. Do **not** hardcode passwords.

If roles already exist from a previous partial run, verify their state before recreating.

### Step C — Apply grants

Apply least-privilege grants according to the target model (§8).

Do not grant DELETE, TRUNCATE, CREATE, ALTER, DROP, GRANT, or REVOKE to runtime roles (`app`, `ingestion`, `training`, `reader`, `gatekeeper`).

### Step D — Apply default privileges

Configure default privileges so future tables and sequences inherit the intended permissions.

### Step E — Update staging service credentials

Switch staging services from `football_user` to role-specific credentials only after role creation and grants are validated.

| Component | Target Role | Env Vars |
|-----------|------------|----------|
| Alembic / migrations | `football_owner` | `DB_OWNER_USER`, `DB_OWNER_PASSWORD` |
| FastAPI app runtime | `football_app` | `DB_APP_USER`, `DB_APP_PASSWORD` |
| Data collectors / ingestion | `football_ingestion` | `DB_INGESTION_USER`, `DB_INGESTION_PASSWORD` |
| Training pipeline | `football_training` | `DB_TRAINING_USER`, `DB_TRAINING_PASSWORD` |
| Health checks / MCP / dashboards | `football_reader` | `DB_READER_USER`, `DB_READER_PASSWORD` |
| CI gatekeeper probes | `football_gatekeeper` | `DB_GATEKEEPER_USER`, `DB_GATEKEEPER_PASSWORD` |

### Step F — Validate

Run the validation matrix (§12) and record actual results.

### Step G — Observe

Observe staging for permission errors before unblocking downstream tasks.

Recommended observation period: 1-2 weeks with monitoring before claiming success.

## 12. Validation Matrix

Expected behavior:

| Operation | `owner` | `app` | `ingestion` | `training` | `reader` | `gatekeeper` |
|-----------|:---:|:---:|:---:|:---:|:---:|:---:|
| SELECT matches | allow | allow | allow | allow | allow | allow |
| SELECT raw_match_data | allow | allow | allow | allow | allow | allow |
| INSERT matches | allow | allow | allow | deny | deny | deny |
| UPDATE matches | allow | allow | allow | deny | deny | deny |
| DELETE matches | allow | deny | deny | deny | deny | deny |
| INSERT raw_match_data | allow | allow | allow | deny | deny | deny |
| INSERT match_features_training | allow | allow | deny | allow | deny | deny |
| CREATE TABLE | allow | deny | deny | deny | deny | deny |
| ALTER TABLE | allow | deny | deny | deny | deny | deny |
| DROP TABLE | allow | deny | deny | deny | deny | deny |
| TRUNCATE | allow | deny | deny | deny | deny | deny |
| GRANT / REVOKE | allow | deny | deny | deny | deny | deny |
| CREATE DATABASE temporary probe | allow | deny | deny | deny | deny | allow |
| Production host | **blocked** | **blocked** | **blocked** | **blocked** | **blocked** | **blocked** |

Any unexpected **allow** is a stop condition.

Any unexpected **deny** for required runtime behavior must be investigated before proceeding.

## 13. Rollback Plan

### Immediate rollback (during deployment window)

1. Revert staging services to `football_user` credentials.
2. Verify service connectivity.
3. Stop any failing staging process.
4. Record error evidence.

### Optional role cleanup

Only if roles should not persist:

```sql
REVOKE ALL PRIVILEGES ON DATABASE football_db FROM
    football_owner, football_app, football_ingestion,
    football_training, football_reader, football_gatekeeper;
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM
    football_owner, football_app, football_ingestion,
    football_training, football_reader, football_gatekeeper;
DROP ROLE IF EXISTS football_owner, football_app, football_ingestion,
    football_training, football_reader, football_gatekeeper;
```

Do **not** execute the SQL above without explicit operator review and staging-host confirmation.

### Rollback safety

- Rollback must never target production.
- `football_user` must remain available throughout.
- Record the rollback with timestamp, reason, and operator identity.

## 14. Evidence Capture

The operator should record:

- issue number (#1637)
- execution date / time
- operator identity
- authorization source
- staging host confirmation
- backup confirmation
- role creation result
- grant result
- default privilege result
- validation matrix result (per-cell pass/fail)
- rollback readiness confirmation
- post-deployment observation notes

Do **not** include secrets in evidence.

## 15. Go / No-Go Criteria

### Go (all must be true)

- staging target confirmed
- production excluded
- backup verified
- secrets handled outside repo
- rollback ready
- operator authorized
- validation matrix ready
- monitoring available

### No-Go (any true = STOP)

- target identity unclear
- production-like host detected
- backup missing
- secrets found in repo files
- rollback account unavailable
- validation cannot be performed
- training / scraper / pipeline would start during deployment
- operator is unsure

## 16. Relationship to #1656

#1656 remains blocked until #1637 is executed and validated.

Do **not** replace `pipeline_worker` fail-fast with a real runtime command until:

- staging roles are deployed
- role-specific service credentials are validated
- DB write permissions are verified
- pipeline ownership / command authority is decided
- the project owner authorizes the next implementation step

## 17. Exit Criteria for #1637

#1637 should remain open until:

- staging role deployment is actually executed
- validation matrix passes
- rollback plan is verified as available
- service credential transition is documented
- no training / data expansion is started prematurely
- evidence is posted back to #1637

Design alone is not enough to close #1637.

## 18. Recommended Next Step

After this runbook PR is merged, the next phase should be a manual authorization gate.

Recommended sequence:

1. merge this docs-only runbook PR
2. decide whether to authorize staging DB execution
3. confirm staging access and backup
4. run a controlled manual deployment phase
5. post evidence to #1637
6. only then revisit #1656

Do not start automatically.
