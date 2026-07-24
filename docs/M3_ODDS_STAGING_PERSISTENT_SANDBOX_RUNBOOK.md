# M3 Odds Staging Persistent Sandbox Runbook

- lifecycle: permanent
- scope: M3-D4D-B1 local persistent sandbox only

## Boundary

The only permitted target is Compose project `fp_m3_persistent_sandbox`, service
`m3-persistent-postgres`, database `fp_m3_persistent_sandbox`, PostgreSQL 15. It has no
host port, uses its dedicated named volume, and is not development, staging, or production.
Project `.env` is never read; the operator uses only an external sandbox env file.

Secrets live outside the repository in `/home/xupeng/.config/footballprediction/m3-persistent-sandbox`
(0700 directory, 0600 files). Custom-format backups live outside the repository in
`/home/xupeng/.local/share/footballprediction/backups/m3-persistent-sandbox` (0700/0600).

## Operator surface

`make m3-odds-sandbox-bootstrap` creates only the sandbox, sandbox roles, and migration
ledger. `make m3-odds-sandbox-plan` lists exactly V26.8 and V26.9 with SHA-256 values.
Apply requires `ALLOW_M3_PERSISTENT_SANDBOX_MIGRATION=1` and the exact confirmation
`I_AUTHORIZE_M3_D4D_B1_SANDBOX_MIGRATION`; it uses a fixed advisory lock, a transaction per
migration/ledger row, and rejects checksum drift. No automatic down migration exists.

`make m3-odds-sandbox-status`, `make m3-odds-sandbox-verify`, and
`make m3-odds-sandbox-backup` provide inventory, grant verification, and backup. Stop removes
only this project containers/network and intentionally retains its named volume.

## Roles and D4E boundary

`fp_m3_sandbox_owner` is bootstrap/backup-only; `fp_m3_sandbox_migrator` owns migration DDL
and ledger; writer is least-privilege insert/select with controlled terminal-run updates;
reader cannot read quarantine or mutate. No business row is authorized in D4D-B1.
`canonical_match_id` remains NULL, candidate identity remains unverified, and no `matches` FK
is created. D4E requires separate explicit authorization and restore-verification evidence.

## REV2B restore permission evidence

`make m3-odds-sandbox-restore-verify` creates a fresh nonce-qualified PostgreSQL 15 tmpfs
clone with no host port, restores the verified custom backup using `pg_restore --exit-on-error`,
and always removes its container, network, temporary secret directory, and SQL copies.

The verified writer transaction inserts one synthetic import run, source file, accepted
observation, and quarantine record; it proves `canonical_match_id IS NULL`, an unverified
candidate ID, and a 64-character synthetic business fingerprint, then rolls the whole
transaction back. It also proves writer `CREATE ROLE`, `CREATE DATABASE`, `GRANT`, destructive
DML/DDL, and privileged `SET ROLE` fail with SQLSTATE `42501`; reader regressions are checked
the same way. No probe uses a real match, source file, or historical odds payload.

The helper machine-audits `pg_roles`, `pg_auth_members`, database/schema/table/sequence ACLs,
and `pg_default_acl`. Writer/reader have no dangerous membership or role attributes; PUBLIC has
no database CREATE, schema CREATE, staging-table privileges, quarantine SELECT, or staging
sequence privileges. Explicit default-function revocations account for PostgreSQL's otherwise
default PUBLIC EXECUTE behavior; default table/sequence behavior grants no PUBLIC access. Writer
has sequence USAGE only, while reader has no sequence write privilege. The final clone inventory
requires two ledger rows and zero business/probe objects.

This is restore and role/grant evidence only. The completed D4D decision is
**READY_FOR_D4E_AUTHORIZATION**; D4E still requires a separate explicit authorization.

## REV3 migration-runner evidence

`make m3-odds-sandbox-runner-probes` is a separate disposable-only harness. The production
wrapper still has a fixed V26.8/V26.9 allowlist and fixed repository source; it accepts neither a
custom migration directory nor a pause flag. The harness creates nonce-qualified PostgreSQL 15
tmpfs projects only, copies base migrations into a 0700 temporary directory, and invokes the same
internal runner core for its runtime-only V99 fixtures.

The completed REV3 run proved: a V99.1 migration created DDL then failed with SQLSTATE `22012`,
leaving no object or ledger row; its repaired identical version resumed, and a further rerun was a
no-op. V99.2 checksum drift produced `RUNNER_CHECKSUM_CONFLICT` before its sentinel SQL ran; the
original checksum and `applied_at` remained immutable. Two concurrent V99.3 runners used
PostgreSQL advisory lock key `731642941`; runner A recorded the same backend PID at acquisition,
critical section, and release, while runner B returned lock-busy without migration SQL. All three
probes ended with empty business tables, no matches FK, one-or-zero expected probe objects, and
fully removed containers, networks, volumes, and temporary directories.

Technical runner probes are closed. D4D is merged; D4E/D4F remain separately authorized work.

## D4E controlled-write implementation (pending implementation PR Gate)

`make m3-odds-sandbox-d4e-preflight`, `make m3-odds-sandbox-d4e-write`, and
`make m3-odds-sandbox-d4e-conflict-probe` are fixed-target operator surfaces. They require both
`ALLOW_M3_D4E_PERSISTENT_SANDBOX_WRITE=1` and the exact D4E authorization phrase. The code accepts
only the deterministic nine-row `m3_d4e_synthetic_v1.jsonl` fixture, the exact sandbox project,
database, service, writer role and internal Docker network; it rejects localhost, production,
staging, arbitrary tables, arbitrary SQL and non-synthetic samples before a transaction begins.

The adapter uses `pg_try_advisory_xact_lock(731642942)`, five-second lock timeout and a
30-second statement timeout. It uses the existing persistence plan/repository contract and writer
permissions only; it never writes `matches` or canonical odds. The disposable probe proves 6/3
first write, 0/0/9 identical replay and divergent accepted rollback. Persistent use remains
forbidden until this implementation's Draft PR has passed its complete Production Gate.
