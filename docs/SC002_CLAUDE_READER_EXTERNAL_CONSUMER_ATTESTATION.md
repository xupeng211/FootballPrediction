# SC-002 `claude_reader` External Consumer Attestation

- lifecycle: evidence
- evidence type: permanent security-audit evidence
- intended reader: Owner and independent security reviewer
- review date: 2026-08-25
- baseline: `main@d7330e5206e9eb2263dcab48a73c189ec9f82392`
- task: `DEVELOPMENT_POSTGRES_ROLE_RETIREMENT`
- subtask: `CLAUDE_READER_EXTERNAL_CONSUMER_ATTESTATION`
- review type: **AUDIT / DECISION SUPPORT ONLY**
- artifact authority: **NONE**
- operational authority: `AGENTS.md` (this document does not replace it)
- cleanup condition: retain as evidence until superseded by stronger host-topology evidence;
  archive or removal requires a separately approved documentation cleanup
- reason for a separate artifact: the Owner explicitly requested this durable, sanitized
  host-consumer evidence ledger; the unchanged `UNKNOWN` blocker does not justify copying
  the detailed host evidence into `docs/PROJECT_STATUS.md`

## Executive attestation

**[CONFIRMED] No current consumer was found on the one known development/operator
host within the explicitly audited surfaces.** The current main repository, tracked MCP
reference, repository-local permission file, current Codex and Claude configuration,
known PostgreSQL client configuration, current shell environment and startup files,
running process snapshot, running containers, user services, relevant system services,
scheduled jobs, running Compose operator configuration, and GitHub Actions workflow all
contain no evidence that a current executable consumer uses `claude_reader` as a
PostgreSQL or MCP login identity.

**[UNKNOWN / FAIL CLOSED] The complete external-host topology is not established.**
Repository/config evidence identifies and permits auditing the current host
`xupeng-MS-7D76`; it does not prove that this is the only development/operator host or
that no unenumerated external proxy, SaaS secret sink, or owner-controlled client exists.
Therefore:

```text
LOCAL_DEVELOPMENT_HOST_CONSUMER_STATE=ABSENT
EXTERNAL_HOST_CONSUMER_STATE=UNKNOWN
HOST_COVERAGE_COMPLETE=NO
NO_UNAUDITED_RELEVANT_HOSTS=NO
ACTIVE_CONSUMER_PROOF_COUNT=0
POTENTIAL_CONSUMER_UNRESOLVED_COUNT=1
```

`ABSENT` above is limited to the defined and completed local-host audit scope. It is not
the statement “no consumer exists anywhere.” The external-consumer blocker is not
cleared. The separate fresh-provisioning blocker remains unchanged, and the safe posture
continues to be `KEEP_NOLOGIN_ROLE_FOR_NOW`.

## Baseline and closure gates

| Evidence | Result | Label |
| --- | --- | --- |
| GitHub `main` | `d7330e5206e9eb2263dcab48a73c189ec9f82392` | CONFIRMED |
| `origin/main` after `git fetch origin --prune` | `d7330e5206e9eb2263dcab48a73c189ec9f82392` | CONFIRMED |
| PR #1883 | `MERGED`; merge SHA equals the baseline | CONFIRMED |
| Post-merge Production Gate | run `32811864651`; exact head equals the baseline | CONFIRMED |
| Required job 1 | `Environment / Proxy / Static / Unit Gate=SUCCESS` | CONFIRMED |
| Required job 2 | `Docker Build Validation=SUCCESS` | CONFIRMED |
| PR #1878 | `OPEN`; not merged and not modified by this task | CONFIRMED |
| Protected original worktree | `workflow/wf01-authority-convergence@6101b347d5bb853ece7bfb9effa86671c81fd85d`; `M README.md` preserved | CONFIRMED |

The task worktree was created from the exact baseline at
`/home/xupeng/FootballPrediction.claude-reader-external-consumer-attestation` on
`audit/claude-reader-external-consumer-attestation`. No work was performed in the
protected dirty worktree.

## Scope and boundaries

In scope:

- the exact current-main tracked tree, including executable/runtime paths, tracked
  configuration, current wiring documentation, tests, governance, and provisioning;
- sanitized structural inspection of current-user Codex, Claude, common MCP client,
  PostgreSQL client, shell startup, SSH topology, and repository-external operator config;
- a current process snapshot, user systemd services, relevant system systemd services,
  current-user cron, system cron files, user timers, and the available `at` surface;
- all running Docker containers, their configuration structure, and the running Compose
  working-directory/config reference;
- static GitHub Actions workflow references and runner topology;
- narrow supplemental container-log target-string counts after PR #1882 merged.

Out of scope:

- every host not enumerated by current repository/operator topology;
- remote SSH connections, external proxy/SaaS configuration values, GitHub secret values,
  browser profiles, histories, logs other than the narrow count-only scan, transcripts,
  caches, conversation artifacts, and tool logs;
- PostgreSQL connections, catalog revalidation, authentication probes, verifier inspection,
  database/ACL/role/provisioning mutation, settings cleanup, and PR #1878 refresh;
- blocker #2 (`FRESH_PROVISIONING_RECREATES_ROLE_ACL_DEFAULT_ACL=YES`) remediation.

## Sanitized method

All target matching used exact-string comparison in memory. Repository searches emitted
filenames only. JSON/TOML/environment parsers emitted only section names, MCP server
names, configuration key paths, environment key names, booleans, and counts. Process
inspection emitted only PID, executable/`comm`, and match type; full argv and environment
values were never printed. Docker inspection emitted container names, images, executable
structure, environment key names, and match classifications; no environment value or raw
inspect JSON was printed. systemd properties and unit bodies were captured only for an
in-memory target match and emitted only unit/directive names. Cron and logs were handled
the same way. No HOME-wide scan was run.

The common Cursor/VS Code MCP settings paths were added as exact path candidates because
the task explicitly includes MCP/client configuration. This narrow expansion did not scan
the rest of HOME:

```text
WHY_SCOPE_EXPANSION_REQUIRED=EXPLICIT_MCP_CLIENT_CONFIG_COVERAGE_WITHOUT_HOME_WIDE_SCAN
```

## Known-host inventory and coverage

| Host/surface | Evidence | Audited | Consumer result |
| --- | --- | --- | --- |
| `xupeng-MS-7D76` — current development/operator host | local hostname, active worktree, host configs, process/service/container/schedule snapshots | YES | ABSENT within the defined surfaces |
| GitHub-hosted `ubuntu-latest` runner class | the only workflow declares two `ubuntu-latest` jobs; no target, DB key, secret, or variable reference | static workflow audited | no CI consumer proof |
| Other development/operator host | no authoritative inventory or exclusivity statement exists | NO — not enumerable | UNKNOWN |
| External proxy/SaaS secret sink | no authoritative inventory or value-readable evidence exists | NO — not enumerable | UNKNOWN |

```text
KNOWN_RELEVANT_HOST_COUNT=1
KNOWN_RELEVANT_HOSTS=xupeng-MS-7D76
HOSTS_AUDITED_COUNT=1
HOSTS_AUDITED=xupeng-MS-7D76
HOST_COVERAGE_COMPLETE=NO
NO_UNAUDITED_RELEVANT_HOSTS=NO
HOST_INVENTORY_EVIDENCE=LOCAL_HOSTNAME+CURRENT_CONFIG+PROCESS_SERVICE_CONTAINER_SCHEDULE_SNAPSHOTS; repository current-state docs explicitly retain external-host UNKNOWN
```

The current SSH config contains one non-wildcard host pattern, no `Include`, no project-
relevant alias, and no target-role reference. That fact does not prove the absence of an
operator host configured elsewhere, and no SSH connection was made.

## Repository current-consumer audit

The baseline main tree contains 17 tracked paths with the target literal. `src/`,
`mcp_servers/`, package scripts, `Makefile`, and GitHub workflows have zero target-literal
paths. The only `scripts/` path is a repository-governance scanner. The executable/runtime
result is therefore unchanged. This branch adds only this audit artifact as one additional
`GOVERNANCE_ONLY` reference:

```text
REPOSITORY_CURRENT_RUNTIME_CONSUMER_STATE=ABSENT
```

### Tracked MCP reference

The sanitized parser found tracked server names `docker`, `filesystem`, `playwright`, and
`pytest`. It found no PostgreSQL structural path and no target-role identity.

```text
TRACKED_POSTGRES_MCP_ENTRY=NO
TRACKED_CLAUDE_READER_MCP_IDENTITY=NO
```

### `.claude/settings.local.json`

The file has only the top-level `permissions` section. A single
`$.permissions.allow[15]` value refers to the stale PostgreSQL query permission. It has no
target-role literal and none of the structural keys for a command, args, environment,
endpoint, connection, loader, or MCP server map.

```text
SETTINGS_LOCAL_STALE_POSTGRES_PERMISSION_REFERENCE=YES
SETTINGS_LOCAL_REFERENCE_CLASSIFICATION=STALE_PERMISSION_REFERENCE_NOT_CONSUMER_PROOF
SETTINGS_LOCAL_ACTIVE_CONSUMER_PROOF=NO
SETTINGS_LOCAL_MODIFIED=NO
```

Permission to call a tool is not evidence that a loader, endpoint, credential, login
identity, or current MCP server exists.

## Reference classification ledger

| Classification | Current-tree or host reference |
| --- | --- |
| `PROVISIONING_ONLY` | `deploy/docker/init_claude_reader.sql`; `docker-compose.yml`; `docker-compose.dev.yml`; the running database container's matching initdb mount path |
| `TEST_ONLY` | `tests/unit/test_claude_reader_provisioning.py`; `tests/unit/test_runtime_db_role_permission_review_phase1.py` |
| `GOVERNANCE_ONLY` | `config/sql_migration_policy_allowlist.json`; `scripts/ops/helpers/repoHygiene.js`; `docs/MCP_ARCHITECTURE.md`; `docs/PROJECT_STATUS.md`; `docs/SC002_CLAUDE_READER_ACL_RETIREMENT_REVIEW.md`; `docs/SC002_CLOSURE_PLAN.md`; `docs/SC002_FINAL_CLOSURE_CHECK.md`; `docs/SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md`; `docs/SC002_STAGING_DB_ROLE_DEPLOYMENT_PLAN.md` |
| `HISTORICAL_DOC_ONLY` | `docs/M3_D4F_READINESS_REVIEW.md`; `docs/SC002_OVERALL_CLOSURE_ASSESSMENT.md`; `docs/SC002_RUNTIME_DB_ROLE_PERMISSION_REVIEW_PHASE1.md` |
| `STALE_PERMISSION_ONLY` | `.claude/settings.local.json` stale `mcp__postgres__query` allow-entry |
| `ACTIVE_CONSUMER_PROOF` | none |
| `POTENTIAL_CONSUMER_REQUIRES_REVIEW` | none among observed literal references |
| `UNKNOWN` | unenumerated external operator host/proxy/SaaS identity boundary; this is a coverage gap, not an observed target-role reference |

The new `docs/SC002_CLAUDE_READER_EXTERNAL_CONSUMER_ATTESTATION.md` file is itself
`GOVERNANCE_ONLY` audit evidence with `ARTIFACT_AUTHORITY=NONE`; it is not a runtime
consumer or a parallel current-state authority.

The provisioning SQL contains seven active target-role statements and both Compose files
mount it into the initdb path. Those facts reproduce blocker #2; they do not establish a
runtime consumer. This task did not modify or execute provisioning.

## Host-local configuration results

### Codex

`~/.codex/config.toml` parsed successfully. Its sections were enumerated without values;
the only MCP server name is `openaiDeveloperDocs`. No parsed key or value contains a
PostgreSQL reference or the target role.

```text
CODEX_CONFIG_POSTGRES_ENTRY=NO
CODEX_CONFIG_TARGET_ROLE_REFERENCE=NO
CODEX_CURRENT_CONSUMER_PROVEN=NO
```

### Claude

The exact current config candidates `~/.claude/settings.json`,
`~/.claude/settings.local.json`, and `~/.claude.json` parsed successfully. The auxiliary
plugin registry config and the exact supported config candidates under `~/.claude/` were
also audited while history/log/transcript/cache/conversation/tool-log paths were excluded.
No MCP server, PostgreSQL structural path, or target-role reference was found.

```text
CLAUDE_HOST_CONFIG_POSTGRES_REFERENCE=NO
CLAUDE_HOST_CONFIG_TARGET_ROLE_REFERENCE=NO
CLAUDE_HOST_ACTIVE_CONSUMER_PROVEN=NO
```

### Other exact operator/client config

- the exact Cursor and VS Code settings files that exist contain no MCP server,
  PostgreSQL structural path, or target-role reference;
- `~/.pgpass` is absent; neither supported `pg_service.conf` path contains a target-role
  reference;
- two existing shell startup files and `~/.psqlrc` candidate handling yielded zero
  target-role matches;
- the current process environment has zero key/value target-role matches;
- `clean-dev/.env` was parsed structurally: 129 key names, one DB identity key selected
  (`DB_USER`), and zero target-role values; no value was printed;
- the running Compose config declares seven DB identity-key occurrences, none referencing
  the target role.

```text
KNOWN_OPERATOR_CONFIG_CONSUMER_STATE=ABSENT
CURRENT_PROCESS_ENV_TARGET_ROLE_KEY_COUNT=0
SHELL_PROFILE_TARGET_ROLE_MATCH_COUNT=0
```

## Runtime snapshot results

### Processes

The scanner excluded itself and its ancestor chain. It inspected 689 other PIDs. All 689
argv files were readable and none contained the target. Environment files were readable
for 217 PIDs; 472 were permission-inaccessible. All 49 inaccessible environments whose
process names matched the task's relevant classes (`node`, `python`, `npx`, `codex`,
`claude`, PostgreSQL, MCP, proxy, or Docker) mapped to one of the inspected Docker
containers or `docker.service`; uncovered relevant processes were zero.

```text
PROCESS_MATCH_COUNT=0
PROCESS_CURRENT_CONSUMER_PROVEN=NO
KNOWN_PROCESS_CONSUMER_STATE=ABSENT
FULL_PROCESS_ARGV_PRINTED=NO
```

This is a current snapshot, not a historical or future process guarantee.

### Containers and running Compose

All nine running containers were inspected structurally. One target-literal match exists:
the `football_prediction_db_dev` initdb mount path. No environment identity key or command
uses the target role, so the match is `PROVISIONING_ONLY`, not a current consumer. The
running Compose working directory and config file were resolved from Compose labels and
audited by exact path; none of its seven DB identity-key occurrences references the target.

```text
RUNNING_CONTAINERS_AUDITED=9
CONTAINER_TARGET_ROLE_MATCH_COUNT=1
CONTAINER_TARGET_ROLE_MATCH_CLASS=PROVISIONING_ONLY_INITDB_MOUNT
CONTAINER_CURRENT_CONSUMER_PROVEN=NO
KNOWN_CONTAINER_CONSUMER_STATE=ABSENT
FULL_CONTAINER_ENV_PRINTED=NO
```

### systemd and scheduled jobs

The user systemd audit discovered 117 unit files and 80 loaded services; their 120-unit
union was inspected. The relevant system audit inspected `containerd.service`,
`docker.service`, `iio-sensor-proxy.service`, and `kmod-static-nodes.service`. There were no
target-role property or unit-directive matches. No service was changed.

The current-user crontab is absent. Four system cron files and four user timers were
audited, with zero matches. No relevant system timer exists. The host has no `atq`
executable, so no `at` entries were enumerated; no observed configuration points to `at`
as a project scheduling surface.

```text
USER_SYSTEMD_UNITS_AUDITED=120
USER_SYSTEMD_TARGET_ROLE_MATCH_COUNT=0
USER_SYSTEMD_CURRENT_CONSUMER_PROVEN=NO
SYSTEM_SYSTEMD_RELEVANT_UNITS_AUDITED=4
SYSTEM_SYSTEMD_TARGET_ROLE_MATCH_COUNT=0
SYSTEM_SYSTEMD_MUTATIONS=0
SCHEDULED_JOBS_AUDITED=current-user crontab + 4 system cron files + 4 user timers; atq unavailable
SCHEDULED_JOB_TARGET_ROLE_MATCH_COUNT=0
SCHEDULED_JOB_CURRENT_CONSUMER_PROVEN=NO
KNOWN_SERVICE_CONSUMER_STATE=ABSENT
KNOWN_SCHEDULED_JOB_CONSUMER_STATE=ABSENT
```

## CI and external-service boundary

The single tracked workflow has two `ubuntu-latest` runner declarations. Static parsing
found no target-role literal, PostgreSQL-related environment key, `secrets.*` reference,
or `vars.*` reference. No GitHub secret value was requested or read.

```text
CI_TARGET_ROLE_REFERENCE=NO
CI_CURRENT_CONSUMER_PROVEN=NO
```

This proves only current tracked workflow wiring. It does not enumerate every external
operator/SaaS secret sink and is therefore not evidence for complete host topology.

## Supplemental post-NOLOGIN log evidence

PR #1882 merged at `2026-08-24T19:44:16Z`. Seven relevant running-container log sources
were scanned from that time using count-only target matching. Six target-string matches
occurred in `football_prediction_db_dev`, from
`2026-08-24T23:40:34.035094608Z` through
`2026-08-24T23:41:41.687000823Z`. A predefined event classifier categorized all six as
`SQL_STATEMENT_REFERENCE`; explicit authentication events, NOLOGIN rejections, password
failures, and successful target connections were all zero. No raw line was printed.

```text
LOG_EVIDENCE_AVAILABLE=YES
POST_NOLOGIN_TARGET_ROLE_LOG_MATCH_COUNT=6
POST_NOLOGIN_TARGET_ROLE_SQL_REFERENCE_COUNT=6
POST_NOLOGIN_TARGET_ROLE_AUTH_EVENT_COUNT=0
POST_NOLOGIN_SUCCESSFUL_TARGET_CONNECTION_COUNT=0
```

The six statement references are consistent with metadata/audit SQL and are governance
evidence, not consumer proof. Logs are supplemental only and cannot establish global
absence.

## Unknowns and final decision

The single unresolved set is:

```text
POTENTIAL_CONSUMER_UNRESOLVED_SET=UNENUMERATED_EXTERNAL_OPERATOR_HOST_OR_EXTERNAL_PROXY_SAAS_IDENTITY_BOUNDARY
```

No repository document, local client configuration, SSH structure, workflow, or machine
fact proves that every development/operator host is in the inventory. Because
`HOST_COVERAGE_COMPLETE=NO`, the `ABSENT` gate is not satisfied even though every known
and authorized local surface returned no consumer proof.

```text
EXTERNAL_HOST_CONSUMER_STATE=UNKNOWN
EXTERNAL_CONSUMER_BLOCKER_CLEARED=NO
FRESH_PROVISIONING_RECREATES_ROLE_ACL_DEFAULT_ACL=YES
PROVISIONING_BLOCKER_REMAINS=YES
RETIREMENT_REVIEW_DECISION_AFTER_ATTESTATION=RETIREMENT_REVIEW_BLOCKED_INCOMPLETE_EVIDENCE
RECOMMENDED_NEXT_OWNER_DECISION=KEEP_NOLOGIN_ROLE_FOR_NOW_OR_AUTHORIZE_NARROW_EVIDENCE_GAP_FOLLOWUP
```

This is a successful fail-closed evidence audit, not retirement approval. No provisioning
design or remediation is started.

## Documentation governance decision

The external-consumer result remains `UNKNOWN`, exactly matching the existing
project-wide blocker. The artifact adds scoped supporting evidence without changing the
authoritative current-state conclusion, business milestone, capability, entrypoint,
repository navigation, or target architecture. Therefore no source-of-truth backflow is
appropriate in this PR.

```text
CAPABILITY_INDEX_UPDATE_REQUIRED=NO
ACTIVE_MILESTONE_UPDATE_REQUIRED=NO
PROJECT_STATUS_UPDATE_REQUIRED=NO
README_ENTRYPOINT_UPDATE_REQUIRED=NO
PROJECT_MAP_UPDATE_REQUIRED=NO
PROJECT_VISION_UPDATE_REQUIRED=NO
CURRENT_STATE_BACKFLOW_PATHS=NONE
PARALLEL_AUTHORITY_CREATED=NO
```

## No-side-effect ledger

```text
READ_ONLY_ATTESTATION=YES
DB_CONNECTION_ATTEMPTS=0
TARGET_ROLE_AUTH_PROBES=0

HOST_CONFIG_MODIFICATIONS=0
SETTINGS_LOCAL_MODIFIED=NO
SETTINGS_LOCAL_RETIREMENT_STARTED=NO

HISTORICAL_SECRET_VALUE_RETRIEVED=NO
CURRENT_PASSWORD_VERIFIER_VALUE_RETRIEVED=NO
SECRET_OUTPUT_REDACTED=YES
TOOL_OUTPUT_REPEATS_SECRET=NO
RAW_CONFIG_VALUES_PRINTED=NO
FULL_PROCESS_ARGV_PRINTED=NO
FULL_CONTAINER_ENV_PRINTED=NO
SHELL_HISTORY_READ=NO
REMOTE_SSH_CONNECTIONS=0
SHELL_XTRACE_ENABLED=NO

DROP_ROLE_EXECUTED=NO
DROP_OWNED_EXECUTED=NO
REVOKE_EXECUTED=NO
GRANT_EXECUTED=NO
ALTER_ROLE_EXECUTED=NO
ALTER_DEFAULT_PRIVILEGES_EXECUTED=NO
ACL_MUTATIONS=0
ROLE_MUTATIONS=0

PROVISIONING_MODIFIED=NO
PROVISIONING_RETIREMENT_STARTED=NO
REPOSITORY_CLEANUP_EXECUTED=NO
INVENTORY_REFRESH_EXECUTED=NO
PR_1878_MODIFIED=NO
PR_1878_MERGED=NO
SYSTEM_SYSTEMD_MUTATIONS=0
USER_README_MODIFICATION_PRESERVED=YES
```
