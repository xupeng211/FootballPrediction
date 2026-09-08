# Stage D continuous operations contract

> lifecycle: current-state contract
>
> 状态：`CONTROLLED_ADAPTER_IMPLEMENTED__OPERATIONALLY_DISABLED`。本合同定义 Stage D 的受控运行边界，
> 不授权网络、scheduler、provider request、canonical transaction 或 Stage D 启动。

## Scope and authority

```text
STAGE_D_NAME=EPL 1X2 CONTINUOUS MARKET EVIDENCE OPERATIONS
TARGET_COMPETITION=EPL
MARKET_SCOPE=1X2 / The Odds API h2h decimal response
PROVIDER_SCOPE=The Odds API only
STAGE_D_ENTRYPOINT=scripts/ops/stage_d_cycle.js --dry-run (public offline); executeStageDOneCycle (internal live adapter)
STAGE_D_SINGLE_CYCLE_ENGINE=executeStageDOneCycle factory-bound controlled adapter
LIVE_EXECUTOR_IMPLEMENTED=YES
LIVE_EXECUTOR_DEFAULT_STATE=DISABLED
LIVE_EXECUTOR_REQUIRES_EXPLICIT_RUNTIME_AUTHORIZATION=YES
LIVE_EXECUTOR_CAN_RUN_WITH_UNKNOWN_QUOTA=NO
STAGE_D_SCHEDULER_MODEL=external scheduler invokes one bounded cycle only
SCHEDULER_ENABLED=NO
CANONICAL_OUTPUT_AUTHORITY=transaction-v1 only
```

The public entrypoint is deliberately offline-only while Stage D remains
unauthorized. It cold-loads the Stage C transaction authority and plans one
cycle, but does not import a provider client, transmit, persist RAW, or publish.
The module-level `executeStageDOneCycle` adapter is production-capable only
when all reviewed factories, the exact runtime authorization token, and a
verified quota configuration are supplied. Its default call path is a hard
authorization failure; tests bind only the local fake transport. The adapter
must not revive the retired Stage C live route or introduce another writer.

## Run, lock, and scheduler contract

The external scheduler supplies an opaque `run_id` for exactly one cycle. Before
any provider boundary the engine acquires `stage-d-run.lock.json` using exclusive
creation and fsync, plus a hash-bound parent-directory reconciliation sentinel.
The parent sentinel is outside the operation root, so replacing the root inode
cannot hide an active or ambiguous run. A second run, an old/stale lock, a
malformed lock, ownership change, or a process crash all stop the next run with
reconciliation required.
There is deliberately no TTL takeover or automatic stale-lock deletion.

The scheduler itself owns cadence. Until the owner supplies verified quota and a
configured billing boundary, `CADENCE=UNSET` and the scheduler must remain
disabled. Once separately authorized, its maximum work unit is one EPL `h2h`
request per cycle; it must not embed retry loops or call a fallback provider.
The production transport is explicitly bound to The Odds API and is never
selected by the public dry-run CLI.

## Durable request-accounting epoch

The sealed epoch is repository-runtime sidecar data, not a canonical transaction:

```text
LEDGER_ROOT=data/market_evidence/live/request-accounting
HISTORICAL_PRE_EPOCH_REQUEST_TOTAL=AT_LEAST_2_CONFIRMED
HISTORICAL_PRE_EPOCH_EXACT_TOTAL=UNKNOWN
```

`REQUEST_ACCOUNTING_EPOCH.json` binds the epoch identifier, UTC start time and
the exact Stage C authority head/state hash. Each immutable numbered ledger entry
is canonical JSON, read-only, fsynced, hash-chained to the epoch genesis hash and
cold-load validated. The ledger does not rewrite the historical lower bound into
an invented exact total.

For each provider attempt the only valid lifecycle is:

```text
REQUEST_INTENT / TRANSMISSION_NOT_STARTED
  -> (local credential preflight)
  -> TRANSMISSION_STARTED_OR_MAY_HAVE_STARTED / consumed
  -> RESPONSE_RECEIVED
     | HTTP_FAILURE_AFTER_TRANSMISSION
     | TRANSPORT_FAILURE_AFTER_POSSIBLE_TRANSMISSION
     | (remain ambiguous-consumed after crash)

REQUEST_INTENT / TRANSMISSION_NOT_STARTED
  -> (credential preflight failure)
  -> CANCELLED_BEFORE_TRANSMISSION / not consumed
```

Every ledger record binds `request_id`, `run_id`, provider, market scope,
creation/transmission/response times, terminal state, quota units, receipt
reference and error class. A retry is not automatic: it needs a new `request_id`,
a new budget decision and a new run admission. Duplicate request IDs and any
terminal-state rewrite are rejected. Usage is never decremented; network
ambiguity after the durable transmission boundary remains consumed.

## Quota and request-budget contract

Provider transmission requires a repository-external, exact
`footballprediction-stage-d-quota-budget/v1` configuration containing all of:

```text
quota_evidence_verified=true
quota_evidence_source
billing_period_id / period_start_at / period_end_at
monthly_quota_limit
reserved_safety_buffer
max_requests_per_stage_d_run
max_requests_per_day (or null)
stop_before_quota_exhaustion_threshold
```

Absent, malformed, expired, or unverified configuration fails closed before an
intent can become a transmission. Credential readiness is checked locally after
intent but before the transmission boundary; invalid credentials become a
non-consumed cancellation. The gate counts terminal and ambiguous
consumed entries in the configured billing period and rejects work that would
cross per-run, daily, monthly, safety-buffer, or stop-threshold limits. It does
not infer a plan, quota reset rule, cost, or available credit from historic
headers.

Current quota facts remain:

```text
THE_ODDS_API_SUBSCRIPTION_TIER=UNKNOWN
THE_ODDS_API_MONTHLY_QUOTA=UNKNOWN
THE_ODDS_API_QUOTA_RESET_RULE=UNKNOWN
THE_ODDS_API_REQUEST_COST_MODEL=UNKNOWN
QUOTA_EVIDENCE_VERIFIED=NO
QUOTA_FAIL_CLOSED=YES
```

Thus `REQUESTS_PER_CYCLE_MAX=1` is a code-bound upper limit, while daily and
monthly estimates are non-authoritative and must not authorize a cycle.

## Capture, publication, duplicate and temporal policy

The controlled adapter is ordered as follows:

```text
lock -> authority reopen -> quota gate -> request intent -> consumed boundary
-> acquire and durably persist content-addressed RAW + receipt
-> request terminal record -> duplicate check -> transaction-v1 publisher -> fresh authority reopen
```

It must use the configured operator-approved ledger root, a fresh verified
authority reader, the production system clock and the existing Stage C
`offlinePipeline -> prospectiveBatch -> atomicPublisher -> authorityReader`
chain; no direct observation, registry, allocation or transaction file write is
allowed. Production transport, persistence, candidate-builder, publisher and
runtime-authorization capabilities are factory-bound. The test-only seams
(networkless fake transport, temporary roots, deterministic clock and local
filesystem fault hooks) are available only under `NODE_ENV=test` and cannot
arm production transport. The transaction-v1 publisher receives a pinned
authority directory descriptor for the complete read/lock/stage/rename/reopen
session; it does not re-resolve the mutable authority path during publication.
The default proxy lease adapter disables background health probes, so a Stage D
request cannot create an unaccounted provider health request.

An already canonical The Odds API RAW SHA-256 is a successful
`NO_OP_DUPLICATE_RAW_HASH`: the request remains accounted, the scheduler records
the no-op result, and no second canonical transaction is published. The existing
transaction authority also rejects duplicate observation IDs and reuses the same
logical capture/receipt transaction rather than publishing it twice.

Each publication must preserve `capture_started_at`, `response_received_at`,
`ingested_at`, provider update time, `knowledge_time`, `projection_available_at`
and transaction publication time. Publisher-owned knowledge time remains bound
into transaction identity and must not precede its input evidence. No later cycle
may make future provider information visible to an earlier as-of query.

## Durability, recovery, retention and backup

The current canonical authority failure domain and every locally discovered
artifact path are `/dev/nvme0n1p5`. A same-disk directory is explicitly not a
backup target. No independent target is configured, so no production backup or
restore proof exists.

When an owner designates a physically/administratively independent target, a
backup snapshot must include immutable transaction packages, `STORE.json`,
allocation authority, request ledger epoch/entries, required run state and a
checksummed manifest. It must snapshot only a cold-load-valid transaction root,
then restore to an isolated root and prove the exact head/state/registry/
provenance/ledger again before being called a backup.

Proposed but unapproved service policy is: irrecoverable evidence retained
indefinitely, operational logs retained 90 days, `RPO <= 24h`, `RTO <= 4h`.
`OWNER_APPROVAL_REQUIRED=YES`.

## Failure matrix

| Failure | Request consumed? | Retry allowed? | Canonical mutation? | Next run? | Manual review? |
| --- | --- | --- | --- | --- | --- |
| Provider timeout / no response | yes | only new request + budget | no | after terminal ledger and clean lock release | no |
| HTTP error | yes | only new request + budget | no | after terminal ledger and clean lock release | no |
| Quota exhausted / quota unknown | no | no until configuration changes | no | no | quota owner for unknown/exhausted |
| Credential invalid before transmission | no | no until credentials are corrected | no | after terminal ledger and clean lock release | credential owner |
| Scheduler duplicate / stale lock / lock ambiguity | no | no | no | no | yes |
| RAW or receipt persistence failure after possible transmission | yes | only new request + budget | no | after terminal ledger | yes |
| Parser, identity, registry failure | yes | only new request + budget | no | after terminal ledger | yes |
| Transaction publication failure / authority reopen failure | yes | no while lock remains | no or unknown | no | yes |
| Backup failure / disk full | request state unchanged unless transmission already occurred | no automatic retry | no | no if authority state is ambiguous | yes |
| Crash before transmission | no | no until lock reconciliation | no | no | yes |
| Crash after transmission boundary | yes / ambiguous-consumed | no until lock reconciliation | no | no | yes |

The Stage C authority is not a compensation mechanism for these failures. Stage D
is still not authorized or started.
