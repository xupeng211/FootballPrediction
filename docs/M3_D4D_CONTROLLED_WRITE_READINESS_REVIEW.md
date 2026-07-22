# M3-D4D Controlled Persistent Write Readiness Review

- lifecycle: current-state
- scope: documentation-only readiness review; no database connection, migration, or data write
- issue: #1793
- reviewed main baseline: `f86c8a8a067a59979fefe1de6a0db283f6a6647c` (`#1799`)

## 1. Executive Decision

**Decision: `BLOCKED`.**

M3-D4C proved the persistence contract only in a disposable PostgreSQL 15 tmpfs
environment. It did not identify a long-lived non-production target, apply either
migration through the repository's long-lived deployment surface, prove target
roles/grants, or prove target backup/restore. Therefore D4E must not be authorized
until the blocking evidence below is closed.

This is not a finding against the default-no-write contract. The contract remains
fail-closed in `src/infrastructure/odds_staging/persistenceRepository.js`; the
blockers concern the separately authorized persistent environment that does not yet
have repository evidence.

## 2. Scope and Non-Goals

This review statically inspected repository code, templates, Compose files, M3 PRs
`#1797`--`#1799`, and Issue `#1793`. It neither read `.env` nor connected to
PostgreSQL or Redis. It did not execute SQL, migrations, backup/restore commands,
or any data write.

Non-goals: selecting a real database, creating credentials or roles, granting
permissions, changing runtime code, changing migrations, importing observations,
or starting D4E/D4F.

## 3. Evidence Reviewed

- `docs/PROJECT_STATUS.md` — #1799/D4C completion boundary and no-long-lived-DB
  statement.
- PRs `#1797`, `#1798`, `#1799` — deterministic identity, default-no-write port,
  and disposable integration verification respectively.
- `database/migrations/V26.8__create_odds_historical_staging_contract.sql` and
  `V26.9__add_odds_historical_observation_fingerprint.sql` — additive staging DDL.
- `src/infrastructure/odds_staging/persistenceContracts.js` and
  `persistenceRepository.js` — plan, explicit authorization, duplicate and
  transaction contracts.
- `tests/integration/odds_staging/` and `scripts/test/odds_staging/` — D4C's
  PostgreSQL 15 tmpfs-only isolation boundary.
- `docker-compose.dev.yml`, `docker-compose.yml`, `.env.example` — static
  environment templates only; no actual values were read.
- `Makefile:3260-3310` and `docs/_reports/DB_SCHEMA_MIGRATION_RUNBOOK_PHASE4_8.md`
  — migration safety gate and migration-runbook reference.
- `deploy/docker/init_db.sql:300-414`,
  `docs/SC002_RUNTIME_DB_ROLE_PERMISSION_REVIEW_PHASE1.md`, and
  `docs/SC002_STAGING_DB_ROLE_OPERATOR_RUNBOOK.md` — dev POC and pending staging
  role model.
- `Makefile:338-340`, `docker-compose.yml`, and `docs/OPERATIONS_MANUAL.md` —
  static backup references, not completed backup/restore evidence.

## 4. Current M3 Architecture

The merged pipeline maps raw historical input to canonical accepted observations or
quarantine records, then produces a persistence plan. A plan is dry-run by default.
`HistoricalOddsStagingPersistenceRepository.execute()` requires all of:
`controlled_write` mode, `write_authorized`, an injected adapter, and an injected
authorizer. It otherwise rejects; it does not read environment variables or open a
database connection itself (`src/infrastructure/odds_staging/persistenceRepository.js`).

V26.8 defines separate import-run, source-file, accepted-observation, and quarantine
tables. V26.9 adds the accepted-observation business fingerprint. D4C verified these
only with 3 synthetic accepted records and 1 synthetic quarantine record in a
destroyed tmpfs PostgreSQL container (`docs/PROJECT_STATUS.md`).

## 5. Candidate Persistent Environments

| Environment | Configuration evidence | Long-lived | Backup evidence | Suitable for D4E | Conclusion |
| --- | --- | --- | --- | --- | --- |
| D4C local ephemeral | `tests/integration/odds_staging/docker-compose.ephemeral.yml`, `scripts/test/odds_staging/ephemeral_authorizer.js` | No; tmpfs and cleanup | Not applicable | No | Correct for D4C only, not persistent D4E |
| Development Compose | `docker-compose.dev.yml:180-220` | Yes; named `postgres_dev_data`, host port mapping | Static `make db-backup` exists; restore proof not found | No | Daily dev data and owner/backup state are not a controlled target |
| Root Compose | `docker-compose.yml:20-70` | Yes; bind-mounted `./data/postgres` | `db_backup` service is static configuration only | No | Reads `.env`; target identity, ownership and recovery are unproven |
| Dedicated test persistent DB | not found | not found | not found | No | No candidate discovered |
| Staging | `docs/SC002_STAGING_DB_ROLE_*` are plans/runbooks | unknown | checklist only | No | Role deployment and target proof are explicitly pending |
| Production / external | no verified repository deployment target | unknown | not found | Never for D4E | Out of scope and prohibited |

**Candidate persistent target: `TARGET_ENVIRONMENT_NOT_PROVEN`.** Existence of a
Compose `db` service is not evidence that it is isolated, backed up, owned, or
authorized for D4E.

## 6. Migration Ordering and Deployment

V26.8 precedes V26.9 lexically and V26.9 depends on V26.8's observations table.
That ordering is **partially verified** as SQL dependency evidence only. The
repository safety surface is `make data-schema-*`; `make data-schema-plan` lists
only older migrations, while `make data-schema-migrate` explicitly stops with
"Migration execution is not wired" (`Makefile:3284-3310`).

No static evidence was found that a canonical long-lived runner discovers V26.8/V26.9,
records applied versions/checksums, serializes concurrent deploys, supports a plan,
or defines failure recovery. D4C direct SQL success is not evidence for such a
runner. Therefore:

```text
MIGRATION_ORDERING: not_verified
```

Before D4E, an authorized operator must identify the runner, demonstrate its ordered
V26.8 -> V26.9 plan against the named non-production target, define lock/version
ledger/checksum behavior, and record its forward-fix policy. This review does not
authorize executing that work.

## 7. Schema and Fingerprint Policy

`V26.9__add_odds_historical_observation_fingerprint.sql` adds nullable
`CHAR(64) business_fingerprint` and permits NULL specifically for legacy state.
The D4C adapter requires a SHA-256 fingerprint for each new accepted observation;
the repository uses it for identical-versus-divergent duplicate comparison
(`persistenceContracts.js`, `persistenceRepository.js`).

The current persistent-row inventory is **not found** because this review did not
connect to a database. Old V26.8 rows and NULL fingerprints therefore cannot be
assumed absent. Recommended strategy is **C — block D4E until existing-row inventory
is completed**. After an authorized inventory proves the selected target is empty,
or proves all relevant rows have compatible fingerprints, strategy A (nullable
schema, application-enforced non-NULL for every new write) can be re-evaluated.
No backfill or `NOT NULL` migration is authorized here.

## 8. Role and Grant Matrix

The repository contains a dev-only POC: `deploy/docker/init_db.sql:300-414` and
`.env.example` describe owner/app/ingestion/training/reader/gatekeeper roles.
`docs/SC002_RUNTIME_DB_ROLE_PERMISSION_REVIEW_PHASE1.md` and
`docs/SC002_STAGING_DB_ROLE_OPERATOR_RUNBOOK.md` state that staging role deployment
remains pending. This is a design, not verified persistent grants.

| Object | Staging writer SELECT | INSERT | UPDATE | DELETE | USAGE | Rationale |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `odds_historical_import_runs` | yes | yes | yes, terminal status only | no | n/a | create and complete one run |
| `odds_historical_source_files` | yes | yes | no | no | n/a | lineage is immutable |
| `odds_historical_staging_observations` | yes | yes | no | no | identity/fingerprint immutable |
| `odds_historical_quarantine` | yes | yes | no | no | quarantine is immutable audit evidence |
| identity sequences | n/a | n/a | n/a | no | yes | generated identifiers only |
| target schema | n/a | n/a | n/a | no | yes | no CREATE/ALTER/DROP |

The migration role must be separate from this writer and hold DDL only for the
approved migration window. A reader may SELECT accepted staging rows only; it must
not receive quarantine access by default. No runtime role should receive
TRUNCATE/CREATE/ALTER/DROP/GRANT/REVOKE or broad `public` privileges.

```text
ROLE_GRANT_READINESS: design_only
```

## 9. Backup, Rollback and Resume

`make db-backup` and root Compose backup configuration are evidence of an intended
backup mechanism, while `docs/OPERATIONS_MANUAL.md` contains operational guidance.
No target-specific completed backup, restore drill, recovery owner, retention, or
RPO/RTO evidence was found.

```text
BACKUP_READINESS: missing
ROLLBACK_READINESS: partial
```

Schema rollback must default to a documented forward fix: V26.8/V26.9 have no down
migration. Data rollback cannot be assumed to be a broad DELETE; a future runbook
must identify the single `run_key`, source hash, affected rows, and an auditable
rolled-back state or explicitly authorized scoped recovery procedure. D4C proves
transaction rollback for a disposable database only. It does not prove persistent
operator abort, recovery, or resume behavior.

## 10. Candidate Match Identity Boundary

`mapAcceptedObservation()` writes `canonical_match_id: null`, retains #1797's local
candidate ID in `candidate_match_id`, and marks
`canonical_match_fk_status: unverified_database_fk`
(`src/infrastructure/odds_staging/persistenceContracts.js`). V26.8 deliberately
creates no `matches` foreign key (`V26.8` column comment).

```text
STAGING_WRITE_IMPACT: non_blocking_with_quarantine_and_unverified_status
CANONICAL_INTEGRATION_IMPACT: blocking
```

For a D4E staging-only write, candidate identity is acceptable only with
`canonical_match_id = NULL`, no new FK, no canonical odds-table write, and no
training read. It remains a hard blocker for canonical integration or training.

## 11. Proposed D4E Sample Envelope

This is a recommendation, not authorization.

| Item | D4E limit |
| --- | --- |
| Target environment | Named, non-production persistent sandbox; currently not selected |
| Database/schema | Explicit allowlisted database and isolated schema or empty dedicated database |
| Import runs / source files | 1 / 1 |
| Accepted / quarantine | <= 9 / <= 3 |
| Total business records | <= 12 |
| Coverage | home, draw, away, unknown timestamp, unverified candidate identity, quarantine |
| Duplicate coverage | identical replay must produce net zero; divergent case is preflight/rollback-only, never committed |
| `canonical_match_id` | must remain NULL |
| Transaction | one authorized transaction; timeout selected before execution |
| Backup prerequisite | target-specific backup and independently verified restore path |
| Rollback prerequisite | run-key scoped, operator-approved procedure and owner |
| Operator confirmation | proposed `I_AUTHORIZE_M3_D4E_PERSISTENT_SANDBOX_WRITE` |
| Post-write verification | identity print, exact row deltas, quarantine exclusion, replay net zero |
| Retention | retain run/source/audit evidence; no broad cleanup command |

The user must separately choose whether the sample is synthetic or a verified real
historical subset. This review makes neither choice and authorizes neither.

## 12. Required Authorization Gates

D4E may begin only when all of the following are explicitly satisfied:

1. User names the exact non-production target and confirms production/staging hosts are excluded.
2. User authorizes V26.8 and V26.9 for that target after a runner plan is reviewed.
3. User authorizes the maximum write counts and synthetic versus real-sample source.
4. Migration role and least-privilege writer role are identified and validated.
5. Target-specific backup and restore are verified; rollback owner/window are named.
6. Existing target schema/row inventory resolves V26.9 NULL-fingerprint risk.
7. Candidate IDs remain non-canonical; no `matches` FK or canonical-table write is allowed.
8. Preflight prints and independently confirms DB identity, database-name allowlist, schema, and role without exposing secrets.
9. The write authorizer requires an execution-specific confirmation, including the proposed phrase above.
10. One transaction, statement timeout, concurrency exclusion, and stop-on-error rules are approved.
11. Post-write reconciliation checks exact row deltas, audit counts, quarantine exclusion, and identical replay net zero.
12. Any conflict, identity mismatch, absent backup, or unexpected row delta aborts without expanding the batch.

## 13. Readiness Decision Matrix

| Domain | Status | Evidence | Blocks D4E |
| --- | --- | --- | --- |
| Target environment | not proven | Compose files only; no named sandbox/owner proof | yes |
| Migration ordering | not verified | `Makefile:3284-3310` blocks execution; V26.8/V26.9 absent from static plan | yes |
| Role/grant | design only | dev POC and pending staging documentation | yes |
| Backup | missing | static backup references, no target restore evidence | yes |
| Rollback | partial | D4C transaction rollback only; no persistent operator runbook | yes |
| Fingerprint policy | unresolved | V26.9 nullable; target row inventory not found | yes |
| Candidate identity | bounded | NULL canonical ID/no FK in D4B contract | no for staging-only, yes for canonical integration |
| Audit/observability | partial | immutable run contract exists; target monitoring/owner not proven | yes |
| Sample cap | designed | Section 11 | no, once target gates pass |
| Explicit authorization | absent | this review is not D4E authorization | yes |

## 14. Blocking Conditions

1. **Persistent sandbox evidence closure (P0):** identify a named non-production,
   non-staging target, its owner, isolation boundary, database/schema allowlist, and
   backup/restore owner. Acceptance: an independently reviewed target record and
   backup/restore proof under new authorization.
2. **Migration deployment evidence closure (P0):** identify the canonical runner and
   prove V26.8 -> V26.9 ordering, version ledger/checksum/lock behavior, and
   forward-fix policy for that target. Acceptance: an authorized preflight plan;
   no migration execution is authorized by this document.
3. **Least-privilege grant closure (P0):** define and validate a migration role and
   table-scoped writer/reader grants matching Section 8. Acceptance: authorized
   role/grant inventory with no broad runtime privileges.
4. **Fingerprint inventory closure (P1):** determine whether the named target has
   V26.8 tables or legacy NULL fingerprints. Acceptance: authorized read-only
   inventory and an approved strategy before a D4E write.
5. **Run-key recovery drill design (P1):** approve scoped abort, rollback, resume,
   and post-write reconciliation for the one-run envelope. Acceptance: operator
   checklist with a named recovery owner.

## 15. Exact Next Action

**M3-D4D-B1 — Persistent Sandbox Environment, Migration-Runner, and Recovery Evidence Closure.**

This is the smallest blocker-closure task: it must remain planning/preflight until a
new user authorization names the target and permits only the necessary read-only
inventory and recovery evidence collection. It must not perform a migration or write
data automatically.

Do not start automatically.
Recommended next task only after user confirmation.
