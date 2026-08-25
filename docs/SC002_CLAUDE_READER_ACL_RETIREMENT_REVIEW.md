# SC-002 `claude_reader` ACL Retirement Review

- lifecycle: permanent security-audit evidence
- review date: 2026-08-25
- baseline: `main@1c8566bc51ed38c38abf39f789ef36cca596dabf`
- task: `DEVELOPMENT_POSTGRES_ROLE_RETIREMENT`
- subtask: `CLAUDE_READER_ACL_RETIREMENT_REVIEW`
- review type: **AUDIT / DECISION SUPPORT ONLY**
- artifact authority: **NONE**
- operational authority: `AGENTS.md` (this document does not replace it)

## Executive conclusion

**[CONFIRMED] `claude_reader` exists in the development PostgreSQL cluster and is
`NOLOGIN`.** The catalog audit found no membership, active session, ownership, or
grantable privilege for the role. A password verifier is still present as a
boolean catalog fact; its value was never read. It found 40 cluster dependency
rows, 54 current direct ACL privilege entries, and two default-ACL rows containing
three exploded privileges.

**[UNKNOWN / BLOCKER] A host outside the repository and development cluster could
still be a consumer.** The repository contains no current runtime consumer proof,
but repository evidence cannot prove the state of an external host. In addition,
fresh-database provisioning still creates the role and its ACLs. Therefore this
review concludes:

> `RETIREMENT_REVIEW_BLOCKED_INCOMPLETE_EVIDENCE`

This is not an authorization to drop the role or revoke any privilege. The safe
current posture is to keep the role `NOLOGIN` while an Owner decides whether to
authorize a separate retirement task after the unknown external consumer and fresh
provisioning paths are resolved.

## Scope and non-goals

In scope:

- PostgreSQL cluster metadata for every non-template database in the existing
  development cluster;
- `pg_roles`, `pg_auth_members`, `pg_shdepend`, `pg_default_acl`, `pg_database`,
  `pg_namespace`, `pg_class`, `pg_proc`, `pg_type`, `pg_stat_activity`, and ACL
  expansion metadata; `pg_authid` was used only through the boolean
  `rolpassword IS NOT NULL` check, never to read a verifier value;
- static repository provisioning and consumer references on the current main tree;
- a plan for a future, separately authorized retirement change.

Out of scope:

- role, ACL, schema, data, HBA, migration, provisioning, or default-privilege
  mutations;
- `DROP ROLE`, `DROP OWNED`, `REASSIGN OWNED`, `REVOKE`, `GRANT`, `ALTER ROLE`, and
  `ALTER DEFAULT PRIVILEGES`;
- authentication as `claude_reader`, password probes, business table contents,
  live fetches, browser runs, or secret-history inspection;
- repository cleanup, settings retirement, #1878 inventory refresh, and business
  implementation.

## Evidence and method

- **[CONFIRMED]** `origin/main` and GitHub main were both
  `1c8566bc51ed38c38abf39f789ef36cca596dabf` after `git fetch origin --prune`.
- **[CONFIRMED]** PR #1882 is merged at
  `1c8566bc51ed38c38abf39f789ef36cca596dabf`; Production Gate run `32769876965`
  succeeded for that SHA, including both required jobs.
- **[CONFIRMED]** PR #1878 remains `OPEN`, `MERGED=NO`, source HEAD
  `b3df505b9b0c4b103194d1bd9fea45c5690d7e14`, and has no tracked diff from current
  main. This review did not modify it.
- **[CONFIRMED]** Metadata was read through the existing
  `football_prediction_db_dev` PostgreSQL 15.17 container as an administrator
  metadata path. The final evidence queries used `BEGIN; SET TRANSACTION READ ONLY;`
  and `ROLLBACK`; they selected catalog/session metadata only.
- **[CONFIRMED]** No query authenticated as the target role. No password verifier
  value/hash, credential URI, or historical secret value was retrieved or printed;
  only the boolean `rolpassword IS NOT NULL` state was inspected.

## Current role state

| Catalog field | Observed value | Evidence label |
| --- | --- | --- |
| role | `claude_reader` exists (OID is intentionally not treated as an authority) | CONFIRMED |
| `rolcanlogin` | `false` | CONFIRMED |
| `rolsuper` | `false` | CONFIRMED |
| `rolinherit` | `true` | CONFIRMED |
| `rolcreaterole` | `false` | CONFIRMED |
| `rolcreatedb` | `false` | CONFIRMED |
| `rolreplication` | `false` | CONFIRMED |
| `rolbypassrls` | `false` | CONFIRMED |
| `rolconnlimit` | `-1` (unlimited, but unusable for login while `NOLOGIN`) | CONFIRMED |
| password verifier presence | `true` (`rolpassword IS NOT NULL`; value intentionally not read) | CONFIRMED |

`rolinherit=true` would matter if another role became a member of
`claude_reader`; the membership audit below found no such path. The role has no
cluster-level elevated attribute identified by this review.

## Database scope

The cluster enumerated two non-template databases, both accepting connections:

| Database | `datallowconn` | Metadata audit |
| --- | --- | --- |
| `football_db` | `true` | complete |
| `postgres` | `true` | complete |

`template0` and `template1` were excluded as templates. `pg_shdepend` and
`pg_database` are shared catalogs; their rows were counted once cluster-wide, not
double-counted merely because both database connections expose them.

## Membership, sessions, ownership, and default ACL

| Check | `football_db` | `postgres` | Cluster conclusion |
| --- | ---: | ---: | --- |
| `claude_reader` is a member of another role (`member` direction) | 0 | 0 | none |
| another role is a member of `claude_reader` (`roleid` direction) | 0 | 0 | none |
| direct `LOGIN` roles inheriting `claude_reader` | 0 | 0 | none |
| active sessions with `usename=claude_reader` | 0 | 0 | none observed |
| owned database/schema/relation/function/type objects | 0 | 0 | none |

The ownership result is also confirmed by zero `pg_shdepend` rows with owner
dependency type (`deptype='o'`). No `LOGIN` role currently inherits the target's
privileges. No session was terminated.

## Dependency ledger (cluster-wide)

`pg_shdepend` rows referencing `claude_reader` were counted once by dependency
identity. The exact total is **40**, matching the prior approximate count without
requiring the old number as an assumption.

| Dependency class | Catalog evidence | Count | Classification |
| --- | --- | ---: | --- |
| database/schema/relation ACL | `pg_database` 1 + `pg_namespace` 1 + `pg_class` 36, all `deptype=a` | 38 | `SHARED_ACL` |
| default ACL | `pg_default_acl`, `deptype=a` | 2 | `DEFAULT_ACL` |
| object ownership | no `deptype=o` row | 0 | `OWNER` |
| role membership | no `pg_auth_members` row | 0 | `MEMBERSHIP` |
| other | no additional class/dependency type | 0 | `OTHER` |
| **total** |  | **40** |  |

The 36 relation dependencies are 20 relation objects carrying current SELECT
ACLs (19 ordinary tables and one view) plus 16 sequences carrying USAGE/SELECT
ACLs. A dependency row represents an ACL-bearing object, not one row per privilege
bit; therefore it is expected not to equal the exploded grant count.

## Direct privilege grant ledger

The following counts are exploded ACL privilege entries for grantee
`claude_reader`; grantable is `false` for every observed entry. Grantor metadata is
shown without any credential-bearing value.

| Scope / privilege | Count | Observed grantor / role of source | Evidence |
| --- | ---: | --- | --- |
| `football_db` `CONNECT` | 1 | `football_user` | CONFIRMED |
| `public` schema `USAGE` | 1 | `pg_database_owner` representation | CONFIRMED |
| public tables/views `SELECT` | 20 | `football_user` | CONFIRMED |
| public sequences `USAGE` | 16 | `football_user` | CONFIRMED |
| public sequences `SELECT` | 16 | `football_user` | CONFIRMED |
| functions `EXECUTE` | 0 | — | CONFIRMED |
| types `USAGE` | 0 | — | CONFIRMED |
| other direct privileges | 0 | — | CONFIRMED |
| **current direct total** | **54** |  |  |

The 20 relation objects are:

`public.bookmaker_odds_history`, `public.data_collection_log`,
`public.feature_registry`, `public.football_competition_editions`,
`public.football_competitions`, `public.football_match_target_teams`,
`public.football_match_targets`, `public.football_source_identities`,
`public.football_team_competition_participation`, `public.football_teams`,
`public.fotmob_raw_match_payloads`, `public.l3_features`, `public.league_config`,
`public.match_features_training`, `public.matches`,
`public.matches_oddsportal_mapping`, `public.odds`, `public.predictions`,
`public.raw_match_data`, and `public.v_mapping_stats` (the last is a view).

The 16 sequences are:

`public.bookmaker_odds_history_id_seq`, `public.data_collection_log_id_seq`,
`public.feature_registry_feature_id_seq`, `public.football_competition_editions_id_seq`,
`public.football_competitions_id_seq`, `public.football_match_target_teams_id_seq`,
`public.football_match_targets_id_seq`, `public.football_source_identities_id_seq`,
`public.football_team_competition_participation_id_seq`, `public.football_teams_id_seq`,
`public.fotmob_raw_match_payloads_id_seq`, `public.league_config_league_id_seq`,
`public.matches_oddsportal_mapping_id_seq`, `public.odds_id_seq`,
`public.predictions_id_seq`, and `public.raw_match_data_id_seq`.

## Default ACL ledger

`football_db.pg_default_acl` contains **2 catalog rows** for this grantee and **3
exploded privilege entries**:

| Owner/grantor | Schema | Object type | Privileges | Count |
| --- | --- | --- | --- | ---: |
| `football_user` | `public` | tables (`r`) | `SELECT` | 1 |
| `football_user` | `public` | sequences (`S`) | `USAGE`, `SELECT` | 2 |

`postgres` has no local default-ACL row for this grantee. These defaults are a
future-permission dependency: revoking current table/sequence ACLs alone would not
prevent a future object from receiving them again.

## Repository provisioning and consumer map

### Provisioning source

**[CONFIRMED]** `deploy/docker/init_claude_reader.sql` currently contains seven
active statements (the commented revoke/drop examples are not executed):

1. create `claude_reader` as `NOLOGIN`;
2. grant `CONNECT` on `football_db`;
3. grant `USAGE` on `public`;
4. grant `SELECT` on all current public tables;
5. grant `USAGE, SELECT` on all current public sequences;
6. default `SELECT` on future public tables;
7. default `USAGE, SELECT` on future public sequences.

It contains no password-provisioning statement. The script is mounted into the
official PostgreSQL initdb directory by both `docker-compose.yml` and
`docker-compose.dev.yml`; on a fresh volume whose `POSTGRES_DB` is `football_db`,
the script recreates the role and these ACL/default-ACL relations. It is not a
runtime application consumer.

### Static current consumer evidence

**[CONFIRMED]** The tracked `.claude/mcp-config.json` server names are
`docker`, `filesystem`, `playwright`, and `pytest`; no PostgreSQL-named entry is
present. Tracked `.claude/settings.json` reports skills disabled. No current
`src/` runtime caller or tracked inline credential for `claude_reader` was proven.
The remaining repository references are provisioning, governance, tests, or
historical documentation. `.claude/settings.local.json` is a tracked host-local
configuration blob (its host-local semantics do not make it untracked); it was not
modified or retired, and no raw configuration value was printed. A sanitized
structural scan finds one stale `mcp__postgres__query` permission reference in that
file. This is not proof of a loader, endpoint, identity, or active consumer, but it
must be included in the external-consumer UNKNOWN rather than omitted.

**[UNKNOWN]** Repository evidence cannot establish whether an external host, proxy,
or operator tool still holds a connection configuration. `EXTERNAL_HOST_CONSUMER_STATE`
therefore remains `UNKNOWN`, not `NONE`.

### Repository ↔ current DB reconciliation

| Provisioning contract | Current DB observation | Result |
| --- | --- | --- |
| create `claude_reader NOLOGIN` | role exists, `rolcanlogin=false` | MATCH |
| `football_db CONNECT` | one direct CONNECT ACL | MATCH |
| public schema `USAGE` | one direct USAGE ACL | MATCH (grantor is the database-owner representation) |
| all public tables `SELECT` | 19 tables + 1 view, 20 SELECT entries | MATCH |
| all public sequences `USAGE, SELECT` | 16 sequences × 2 privileges | MATCH |
| default table `SELECT` | one default-ACL row / one exploded privilege | MATCH |
| default sequence `USAGE, SELECT` | one default-ACL row / two exploded privileges | MATCH |
| repository password provisioning | absent | current DB retains a verifier (`rolpassword IS NOT NULL=true`) — `CONTRACT_ONLY`, not a state match |

The ACL/category rows reconcile to the repository contract. The password row is
intentionally **not** a state match: the repository no longer provisions a
password on a fresh database, while this existing database still retains a
verifier. The schema ACL's
`pg_database_owner` grantor display is a PostgreSQL catalog representation, not an
unexplained extra privilege.

If only current database ACLs were revoked while these repository mounts and the
init script remained, a fresh database would recreate the role and grants. A real
retirement task must therefore address the script and both compose mounts before
or together with any database mutation. The future task would also need to review
the unit tests, SQL-migration allowlist, repository-hygiene reference, and
historical/current documentation that intentionally describe the retained role.

## Security interpretation and blockers

### Authentication risk

**[CONFIRMED] Current direct-login risk is closed while the role remains
`NOLOGIN`** by the completed #1882 state: the current tracked PostgreSQL MCP entry
is absent and current repository provisioning does not create a password. The
catalog still reports a password verifier present (`rolpassword IS NOT NULL=true`),
but its value was not read. That verifier would become relevant again if an
unauthorized change restored `LOGIN`; this review neither restores login nor
performs password rotation. This does not claim that a historical credential has
been erased from Git history; historical secret history remediation is out of
scope.

### Privilege and maintenance debt

**[CONFIRMED]** The retained ACL is still a maintenance dependency: 40 dependency
rows, 54 direct privilege entries, and 3 default-ACL privilege entries remain.
Those ACLs are not an active direct-login vulnerability while the role is
`NOLOGIN`, but they continue to grant read capability to any future authorized
role membership and cause fresh provisioning to recreate the state.

### Prior-count reconciliation

| Prior evidence | Current strict measurement | Interpretation |
| ---: | ---: | --- |
| dependencies ≈ 40 | 40 `pg_shdepend` rows | no dependency-count drift |
| direct grants ≈ 57 | 54 direct ACL entries + 3 default-ACL entries | the old combined figure is reconciled by separating default ACL privileges; no current extra/missing grant was found |

The explanation for the 57-to-54 direct split is **[INFERRED]** from the exact
current ledger: three exploded default-ACL privileges were previously included in
the combined grant number. The current audit keeps object ACL and future default
ACL counts separate as required.

### Retirement blockers

1. **BLOCKER — unknown external consumer:** no external-host evidence proves that
   no operator, proxy, or out-of-repository client can still use the retained role.
2. **BLOCKER — future provisioning dependency:** both compose paths still mount an
   init script that recreates the role, current ACLs, and default ACLs on a fresh
   database.

Non-blocking findings are the current `NOLOGIN` ACL residue itself, zero active
sessions, zero membership, zero ownership, and non-grantable direct privileges.

## Retirement decision

`RETIREMENT_REVIEW_DECISION=RETIREMENT_REVIEW_BLOCKED_INCOMPLETE_EVIDENCE`

This is the required conservative conclusion, not a drop recommendation. The
review is complete for the auditable development cluster, but it cannot prove the
external-consumer boundary and cannot authorize a retirement while fresh
provisioning still recreates the role.

## Future execution plan (design only; not authorized here)

Only after an Owner authorizes a separate execution task:

1. Keep the role `NOLOGIN`; do not restore login or create a password. Treat the
   existing verifier as a conditional residual risk and never print or copy its
   value.
2. Reconfirm all non-template cluster databases, active sessions, both membership
   directions, ownership, default ACLs, and external consumer attestations.
3. Remove/retire the future provisioning role/ACL statements and both compose initdb
   mounts, then update their tests/allowlists/documentation and review the tracked
   `.claude/settings.local.json` `mcp__postgres__query` permission reference in the
   same reviewed change.
4. Remove the two default-ACL rows/privileges with precise, owner-aware
   `ALTER DEFAULT PRIVILEGES` operations.
5. Revoke the 54 current direct ACL entries only after consumer approval and a
   captured rollback grant map; do not use a broad `DROP OWNED` shortcut.
6. Resolve any membership or ownership discovered by the recheck. `DROP OWNED`
   and `REASSIGN OWNED` are **NOT_AUTHORIZED / HIGH_RISK** defaults, not shortcuts.
7. Re-measure dependencies until zero or an Owner-approved retained state, then
   consider `DROP ROLE` as the final operation only if explicitly authorized.
8. Run fresh-volume provisioning regression, exact-head CI, and post-change
   metadata verification across every development database.

### Recovery design

If a future precise revoke exposes a previously hidden consumer, restore only the
smallest required `GRANT` set from the captured ledger, preserving `NOLOGIN`; do
not restore `LOGIN` as a rollback default. Any ownership or membership recovery
requires a new Owner-approved plan. No rollback mutation was executed in this
review.

## Safety and side-effect ledger

```text
AUDIT_ONLY=YES
DB_METADATA_READS=YES
DB_SECURITY_WRITES=0
DB_SCHEMA_WRITES=0
DB_BUSINESS_DATA_WRITES=0
ROLE_MUTATIONS=0
ACL_MUTATIONS=0
DROP_ROLE=0
DROP_OWNED=0
REASSIGN_OWNED=0
REVOKE=0
GRANT=0
ALTER_ROLE=0
ALTER_DEFAULT_PRIVILEGES=0
PROVISIONING_EXECUTIONS=0
TARGET_ROLE_AUTH_PROBES=0
AUTH_SCRIPT_EXECUTIONS=0
BROWSER_RUNS=0
LIVE_FETCH=0
RAW_WRITES=0
MIGRATION_APPLY=0
HISTORICAL_SECRET_VALUE_RETRIEVED=NO
SECRET_OUTPUT_REDACTED=YES
TOOL_OUTPUT_REPEATS_SECRET=NO
HISTORY_REWRITE_EXECUTED=NO
REPOSITORY_CLEANUP_EXECUTED=NO
PR_1878_MODIFIED=NO
USER_README_MODIFIED=NO
```

## Owner decision gate

Recommended next owner decision: authorize **one** follow-up evidence task to
obtain an external-consumer attestation and prepare a provisioning-retirement
change plan, or explicitly keep `claude_reader` as a `NOLOGIN` retained ACL role.
Do not merge this review automatically, do not revoke/drop anything from this
artifact, and do not start cleanup or business work.
