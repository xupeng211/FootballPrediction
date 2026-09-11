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
STAGE_D_ENTRYPOINT=scripts/ops/stage_d_cycle.js --dry-run (public offline); scripts/ops/stage_d_controlled_initialization.js (future separately authorized live binder)
STAGE_D_SINGLE_CYCLE_ENGINE=executeStageDOneCycle factory-bound controlled adapter
LIVE_EXECUTOR_IMPLEMENTED=YES
LIVE_EXECUTOR_DEFAULT_STATE=DISABLED
LIVE_EXECUTOR_REQUIRES_BOUNDED_AUTHORIZATION_ARTIFACT=YES
LIVE_EXECUTOR_CAN_RUN_WITH_UNKNOWN_QUOTA=NO
LIVE_BINDER_PRIVATE_CAPABILITY=MODULE_PRIVATE_SYMBOL_CREATED_ONLY_AFTER_VALIDATION
LIVE_BINDER_MAX_PROVIDER_REQUESTS=1
LIVE_BINDER_EXPECTED_REQUEST_COST_CREDITS=1
LIVE_BINDER_SCOPE=the_odds_api / h2h / uk
LIVE_BINDER_REPLAY_POLICY=IMMUTABLE_CONSUMPTION_MARKER__FAIL_CLOSED
STAGE_D_SCHEDULER_MODEL=external scheduler invokes one bounded cycle only
SCHEDULER_ENABLED=NO
CANONICAL_OUTPUT_AUTHORITY=transaction-v1 only
```

The public entrypoint is deliberately offline-only while Stage D remains
unauthorized. It cold-loads the Stage C transaction authority and plans one
cycle, but does not import a provider client, transmit, persist RAW, or publish.
The production-facing live entrypoint is exclusively
`scripts/ops/stage_d_controlled_initialization.js`; it accepts only bounded
artifact paths and never accepts a shell-supplied authorization token,
boolean, retry count, provider override or scheduler mode. It reads a
canonical, read-only authorization artifact that must be a direct child of an
explicit external runtime trust root, checks the immutable mission/provider/
market/region/max-cost/epoch/authority/quota/fixture scope, writes a durable
single-use consumption marker, and only then creates the module-private
runtime capability before calling `executeStageDOneCycle`. The capability is
not exported, logged, serialized, or returned. In production the binder fixes
the transport, evidence persistence, prospective candidate builder and
transaction-v1 publisher to reviewed factories; in `NODE_ENV=test` every
component must be supplied explicitly and the provider transport is rejected.
This implementation closes the caller-binding gap only; it does not authorize
Stage D, provider access, scheduler start, blocker #2 filesystem permission
repair, or blocker #3 independent backup/restore.

The authorization artifact schema is
`footballprediction-stage-d-controlled-initialization-authorization/v1` and
its approval status must be `OWNER_AND_CHIEF_ENGINEER_AUTHORIZED`. Its exact
scope includes `mission=CONTROLLED_STAGE_D_SINGLE_CYCLE`,
`provider=the-odds-api`, `configured_markets=[h2h]`,
`configured_regions=[uk]`, `max_provider_requests=1`,
`expected_request_cost_credits=1`, the exact `accounting_epoch_id`,
`authority_pre_head`, `authority_pre_state_hash`, pre-observation count,
pre-`STORE.json` hash, allocation-authority hash, quota-config hash,
fixture-universe RAW hash, `run_id`, `request_id`, `issued_at` and
`expires_at`. The binder rejects missing, malformed, expired, replayed,
wrong-scope, wrong-epoch, wrong-authority, untrusted, writable or
non-canonical artifacts before transport construction/use. `max_provider_requests`
greater than one is not representable in this entry path. A calendar date
never resets quota or accounting.

## Run, lock, and scheduler contract

The external scheduler supplies an opaque `run_id` for exactly one cycle. Before
any provider boundary the engine acquires `stage-d-run.lock.json` using exclusive
creation and fsync, plus a hash-bound fence in an explicitly configured,
owner-controlled runtime trust root. The operation-root parent and stable
ancestor sentinels remain defense-in-depth, but the external fence is the
non-replaceable admission/release anchor: replacing the operation root or its
parent cannot hide an active or ambiguous run. Production requires
`runLockTrustRoot`; the deterministic per-root fallback exists only for
`NODE_ENV=test`. The trust root and every parent must be real directories owned
by the runtime user and not group/world writable, and it must be a separate
path domain from the operation root. A persistent append-only ledger-generation
anchor in that trust root binds operation and ledger device/inode identities,
epoch and last-entry hash across clean releases; a valid old ledger copy is
therefore a reconciliation failure, not a new run. A second run, an old/stale
lock, a malformed lock, ownership change, or a process crash all stop the next
run with reconciliation required.
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

Provider transmission requires an exact
`footballprediction-stage-d-quota-budget/v2` configuration. The non-secret
current Owner configuration is tracked at `config/stage_d_quota_budget.json`;
any future live bootstrap must still load it through the reviewed runtime
authorization path and must not place credentials in the repository. The
configuration contains all of:

```text
provider / subscription_tier / quota_evidence_class
quota_evidence_verified=true
quota_evidence_source
billing_period_id / period_start_at / period_end_at (local governed guard period)
monthly_quota_limit
reserved_safety_buffer
automated_spend_limit
max_requests_per_stage_d_run
max_requests_per_day (or null)
stop_before_quota_exhaustion_threshold
configured_markets / configured_regions / market_count / region_count
expected_request_cost_credits / max_provider_requests_per_cycle
quota_reset_rule / automatic_zero_on_calendar_change
historical_pre_epoch_request_total / historical_pre_epoch_exact_total
post_epoch_usage_source
```

Absent, malformed, expired, or unverified configuration fails closed before an
intent can become a transmission. Credential readiness is checked locally after
intent but before the transmission boundary; invalid credentials become a
non-consumed cancellation. The gate counts terminal and ambiguous
consumed entries in the configured local guard period and rejects work that
would cross per-run, daily, automated-monthly, safety-buffer, or stop-threshold
limits. Ambiguous consumed requests and prior provider-quota divergence block
the next cycle. It does not infer a plan, quota reset rule, cost, or available
credit from historic headers.

The current Owner-declared plan and governed cost facts are:

```text
THE_ODDS_API_SUBSCRIPTION_TIER=STARTER_FREE
THE_ODDS_API_MONTHLY_QUOTA=500
RESERVED_SAFETY_CREDITS=50
AUTOMATED_MONTHLY_SPEND_LIMIT=450
STAGE_D_MARKET_COUNT=1
STAGE_D_REGION_COUNT=1
EXPECTED_REQUEST_COST_CREDITS=1
MAX_PROVIDER_REQUESTS_PER_CYCLE=1
QUOTA_EVIDENCE_CLASS=OWNER_DECLARATION_PLUS_PUBLIC_PLAN_EVIDENCE
QUOTA_RESET_RULE=PROVIDER_RECONCILED__NO_UNVERIFIED_AUTOMATIC_RESET
LOCAL_LEDGER_AUTOMATIC_ZERO_ON_CALENDAR_CHANGE=NO
QUOTA_EVIDENCE_VERIFIED=YES
QUOTA_FAIL_CLOSED=YES
```

`period_start_at` and `period_end_at` are local guard boundaries, not an
invented provider reset timestamp. A calendar change never zeros the local
ledger. A new period is admitted only after a contractually valid provider
reconciliation or explicit Owner-controlled configuration action; otherwise
the expired configuration fails closed.

The plan limit is separate from live provider state. Until a separately
authorized successful provider response supplies quota headers:

```text
PROVIDER_REPORTED_USED=UNKNOWN_UNTIL_AUTHORIZED_RESPONSE
PROVIDER_REPORTED_REMAINING=UNKNOWN_UNTIL_AUTHORIZED_RESPONSE
PROVIDER_REPORTED_LAST_COST=UNKNOWN_UNTIL_AUTHORIZED_RESPONSE
```

For every future successful HTTP response, the request ledger stores the raw
safe values and parsed values for `x-requests-used`, `x-requests-remaining`,
and `x-requests-last`. The reconciliation requires non-negative integers,
`used + remaining = 500`, `last = expected_request_cost_credits`, and a
monotonic one-credit transition from the prior reconciled response. A provider
remaining balance below the local safe budget, a missing/malformed header, or
any local/provider divergence consumes the attempt and blocks later cycles
until explicit reconciliation.

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
(the networkless fake transport accepts only serialized JSON fixtures; candidate
and publisher failures are declarative descriptors; temporary roots,
deterministic clocks and a small allow-listed declarative filesystem-fault
descriptor) are available only under
`NODE_ENV=test` and cannot arm production transport. The transaction-v1 publisher receives a pinned
authority directory descriptor for the complete read/lock/stage/rename/reopen
session; it does not re-resolve the mutable authority path during publication.
The authority reader pins the root and committed directory descriptors for each
replay and each transaction package, and the adapter revalidates the public root
identity before any duplicate no-op or publication decision. A directory
generation mismatch is an ambiguity requiring reconciliation, never a reason to
continue.
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
allocation authority, request ledger epoch/entries, required run state and the
non-secret quota configuration required to interpret exact accounting, plus a
checksummed manifest. Secrets are provisioned separately and are never part
of the snapshot. The copy contract records the source authority identity and
state hash before and after staging, includes committed packages only, writes
the manifest/checksums before a final completeness marker, and treats any
missing marker or source identity change as an invalid snapshot. It must
snapshot only a cold-load-valid transaction root, then restore to an isolated
root and prove the exact head/state/registry/provenance/ledger again before
being called a backup.

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
