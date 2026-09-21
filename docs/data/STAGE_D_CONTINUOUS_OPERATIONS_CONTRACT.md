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
RUNTIME_FILESYSTEM_PERMISSION_CONTRACT=stage-d-runtime-filesystem-permission/v1
RUNTIME_FILESYSTEM_IDENTITY_RULE=COLD_LOAD_UID_EQUALS_AUTHORITY_OWNER_UID
RUNTIME_FILESYSTEM_APPLY_PATH=NONE__PHASE_B_IS_A_SEPARATE_OWNER_AUTHORIZED_PROCEDURE
RUNTIME_FILESYSTEM_AUDIT_ENTRYPOINT=scripts/ops/stage_d_runtime_filesystem_inspect.js (read-only; no apply mode)
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
     | POST_RESPONSE_PROCESSING_FAILURE
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

`POST_RESPONSE_PROCESSING_FAILURE` is reserved for a completed, validated HTTP
response whose later local processing failed. It is not a transport failure and
is further classified by `error_classification` as
`RAW_PERSISTENCE_FAILED`, `PROVIDER_QUOTA_RECONCILIATION_FAILED`, or
`RECEIPT_PERSISTENCE_FAILED`. The ledger keeps the exact
`response_received_at`; the immutable diagnostic is keyed by the same
`request_id` under `failure-diagnostics/`.

For a future non-2xx response, the adapter first makes the consumed
`HTTP_FAILURE_AFTER_TRANSMISSION` ledger state durable, then writes a separate,
immutable `footballprediction-stage-d-failure-diagnostic/v1` artifact under the
runtime evidence root's `failure-diagnostics/` directory. It is keyed by the
request id and contains only the HTTP status, response timestamp, strict,
individually bounded and redacted allowlisted headers, optional safe transport provenance, and a redacted UTF-8/JSON
payload capped at 4096 bytes. It is not provider market RAW, is never parsed as
market evidence, and never creates a transaction. A diagnostic persistence failure
does not roll back consumption or permit a retry; the durable terminal ledger fact
remains authoritative and the caller fails closed.

For a future exception from `transport.send()` after the durable transmission
boundary, the adapter first makes the consumed
`TRANSPORT_FAILURE_AFTER_POSSIBLE_TRANSMISSION` ledger state durable and then
writes a separate immutable
`footballprediction-stage-d-transport-failure-diagnostic/v1` artifact in the
same `failure-diagnostics/` authority. The transport artifact is strictly
allowlisted: it records the run/request binding, provider/`h2h`/`uk` envelope,
terminal state, occurrence time, a bounded allowlisted direct `Error.code` and
an `safe_error_message` derived only from that closed code allowlist (or a
fixed generic value), an allowlisted syscall, the conservative
`UNKNOWN_POST_BOUNDARY` phase, fixed proxy-contract provenance, and explicit
`transmission_boundary_crossed=true` / `http_response_received=false` flags.
It never serializes `Error`, `stack`, `cause`, arbitrary enumerable fields,
hostname/address/port values, credentials or request bodies. It is diagnostic
evidence only: it cannot become market RAW, a receipt or a transaction. A
transport-diagnostic persistence failure leaves the consumed ledger fact and
run-lock accounting authoritative and fails closed; it never permits a retry.

For a completed 2xx response, the adapter validates the status, response time
and text, then persists immutable market RAW before attempting quota
reconciliation. If reconciliation reports missing, malformed, inconsistent or
conflicting headers, the consumed ledger is terminalized as
`POST_RESPONSE_PROCESSING_FAILURE` with
`PROVIDER_QUOTA_RECONCILIATION_FAILED`, and an immutable
`footballprediction-stage-d-post-response-failure-diagnostic/v1` artifact is
written. The artifact contains the exact HTTP status and response timestamp,
the RAW SHA/reference when RAW exists, fixed failure semantics, transport
provenance only from a closed allowlist, and only bounded numeric observed
quota fields. It never stores credentials, arbitrary headers, error objects,
stack/cause data, response bodies or secret-bearing values.

Quota reconciliation remains fail-closed: no receipt, canonical transaction,
retry or follow-up quota probe is allowed after this failure, and the provider
quota actual effect remains `UNKNOWN`. A successful RAW capture therefore does
not imply quota authorization passed. A RAW persistence failure or receipt
persistence failure uses the same post-response terminal state and diagnostic;
the receipt remains unpublished, while any already-persisted RAW stays
immutable. Diagnostic persistence failure cannot undo the durable consumed
terminal state.

This ordering is also the offline-recovery contract: a later bounded local
adjudication may use the retained RAW, SHA, request identity, HTTP status and
immutable capture timestamp without re-requesting the provider. It must remain
idempotent, revalidate the evidence and quota/authority policy, and cannot
publish a transaction merely because a RAW file exists.

The consumed 2026-09-20 ECONNRESET attempt is historical evidence, not a
retroactive instance of this new schema. Its local evidence proves only the
conservative post-boundary transmission marker and the transport error; no
authoritative HTTP response, provider-quota effect, narrower failure phase or
reset origin was retained. Its provider quota effect therefore remains
`UNKNOWN`, local request budget remains consumed, no RAW/receipt/transaction
exists, and the historical attempt must not be retried or rewritten.

The subsequent owner-authorized canary is a separate immutable historical
event: retained evidence proves `HTTP_RESPONSE_RECEIVED=YES`, the 2xx branch
was reached and quota reconciliation failed after the response. The exact HTTP
status and provider quota headers were not durably retained, so both remain
`UNKNOWN` (the 2xx fact does not justify inferring status 200). The old code
persisted neither RAW nor receipt nor transaction nor a post-response
diagnostic; it remains consumed once, is not retroactively reconstructed and
must not be retried. The post-response ordering and diagnostic contract above
is prospective.

Production component construction preserves this same boundary: the resolved HMAC
preflight secret is an opaque, non-enumerable capability used only by the attestation
preflight. It is never passed to evidence persistence. Diagnostic redaction receives
only transient string values from the configured secret-bearing environment bindings;
those values are used solely for in-memory matching before persistence and are never
serialized, logged, returned, or hashed as diagnostic fields. A malformed or missing
preflight secret still fails closed before any socket, authorization consumption, request
intent, or provider transmission.

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

A consumed `POST_RESPONSE_PROCESSING_FAILURE` with
`PROVIDER_QUOTA_RECONCILIATION_FAILED` is also a quota-governance blocker until
the retained evidence is explicitly re-adjudicated. RAW preservation is data
protection only; it never authorizes a new provider request or treats the
provider quota actual effect as known.

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
The Stage D provider transport uses one dedicated, project-controlled, stable HTTP
CONNECT proxy endpoint rather than a proxy lease, so a Stage D request can neither
rotate across the harvesting pool nor create an unaccounted provider health request.
See [Provider transport proxy contract](#provider-transport-proxy-contract).

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

## Provider transport proxy contract

The Owner architecture decision for Stage D is a dedicated, project-controlled,
single, stable HTTP CONNECT proxy endpoint, named by `THE_ODDS_API_PROXY_URL`. The
rotating multi-node SOCKS5 pool (`config/proxy_pools.json`, `REG-TITAN-40`, ports
10001–10040) remains the bulk-harvesting pool — one worker per port for FotMob,
OddsPortal and Playwright capture — and is not reachable from the Stage D provider
path.

Recorded decision: `OWNER_PROXY_ARCHITECTURE_DECISION=DEDICATED_SINGLE_STABLE_HTTP_CONNECT_ENDPOINT`,
`ROTATING_SOCKS_POOL_FOR_STAGE_D=PROHIBITED`,
`CONCRETE_PRODUCTION_PROXY_ENDPOINT=EXTERNALLY_BOUND__REPOSITORY_UNTRACKED`,
`CONCRETE_PRODUCTION_PREFLIGHT_TARGET=EXTERNALLY_BOUND__REPOSITORY_UNTRACKED`,
`PROXY_PROTOCOL_PREFLIGHT_REQUIRED=YES`,
`PREFLIGHT_BEFORE_AUTHORIZATION_CONSUMPTION=YES`, and `STAGE_D_PROXY_FALLBACK=NONE`.

No production proxy endpoint is recorded in tracked source. A separately controlled
2026-09-20 deployment provisioned one dedicated project-controlled HTTP CONNECT listener
and a distinct TCP HMAC target, with all concrete runtime inputs held outside Git in an
owner-only binding. The Stage D transport cannot be bound to a pool name or
to a caller-supplied proxy provider, and no reachable production path falls back to
the rotating pool, to a workstation proxy, or to a direct connection. Absent
configuration fails closed as `PROXY_CONFIGURATION_MISSING` — the
repository-equivalent of `PRODUCTION_PROXY_ENDPOINT_NOT_CONFIGURED` — rather than
degrading to a fallback.

The ordering is fixed: proxy configuration validation, then proxy protocol
preflight, then — only on pass — authorization consumption, request accounting and
transmission. Before the one-shot authorization is spent, the binder resolves the
endpoint and proves it by opening a real HTTP CONNECT tunnel to a second, explicitly
configured target that must attest with a shared secret. The probe never names The Odds
API, so it cannot resolve provider DNS, contact the provider or consume provider quota.

### HTTP CONNECT preflight target

A proxy is not proven because it returned an HTTP-shaped response, and it is not
proven by anything the client can author on its own. It is proven only when it accepts
CONNECT for a project-controlled target, answers with a strict 2xx, and then carries a
fresh random challenge through the resulting tunnel that the target answers with an
HMAC-SHA-256 over that challenge under a shared secret only the target and the
verifier hold. The target is therefore a second contract, separate from the proxy
endpoint, named by `STAGE_D_PROXY_PREFLIGHT_TARGET_URL` in the canonical form
`tcp://host:port`. It is required for production Stage D: there is no implicit
default, no hardcoded workstation address, no public-Internet fallback, no provider
hostname, and no path, query, fragment or userinfo. The `tcp:` scheme is the only one
accepted, and an explicit port is mandatory because `tcp:` has no default port.
Rejecting a target that is literally the proxy's own host and port prevents an
endpoint from proving itself by talking to itself; that comparison is a literal
`host:port` match and makes no DNS-equivalence assumption.

The target's address is expressed in the proxy's coordinate system and is explicit
configuration in every environment. Nothing infers it from `socket.localAddress`,
host routes, a Docker gateway, `localhost`, `host.docker.internal` or any other
property of the current workstation. Its deployment topology — including whether the
proxy's own loopback is the right address, which depends on whether the proxy and the
target share a network namespace — is an Owner provisioning decision that this
contract deliberately does not make. An unconfigured or invalid target fails closed
before any proxy socket is opened, and in every case before authorization
consumption.

The target must not be The Odds API, FotMob, OddsPortal, a bookmaker, a public
third-party website, the proxy listener itself, or personal workstation
infrastructure. The provider hosts this repository actually talks to are enforced
as a denylist rather than left to operator discipline: naming one — or any
subdomain of one, in any letter case, with or without a trailing dot — fails
closed with `PROXY_PREFLIGHT_TARGET_EXTERNAL_HOST` at resolution time, before any
socket exists. A target that is a provider would void the proof, because a
provider is not a project-controlled attesting target, and would additionally
make the preflight an outbound contact with a third party. A denylist cannot
enumerate every public host, so this closes the concrete misconfiguration rather
than claiming completeness; the primary control remains that the target is
explicit operator configuration with no default. A pass requires all of: the endpoint's configuration resolves; the
target configuration resolves; the shared secret resolves; the TCP (or TLS) connection
to the endpoint succeeds; the endpoint receives
`CONNECT <configured-target-host>:<port> HTTP/1.1`; the response is a syntactically
valid HTTP response; the status is strictly `200`–`299`; the tunnel remains open; and
the target attestation verifies. Anything else fails closed.

### Preflight attestation: why a client-authored nonce is not enough

An earlier revision of this preflight proved the data plane by writing a fresh random
nonce through the tunnel and requiring the target to echo it back verbatim.
Independent adversarial review rejected that design, and the objection is exact: a
nonce the client invents is a value the client already knows, so a responder that
reads it — and never dials the configured target — can produce the expected reply.
Reflection is indistinguishable from forwarding when the challenge carries no secret.
A 2xx-and-reflect endpoint would therefore have passed the last gate before one-shot
authority was spent, while the configured target was never contacted.

The proof now rests on material the responder cannot compute. Each execution generates
a fresh 256-bit challenge from `crypto.randomBytes` and a fresh 128-bit run id, writes
`stage-d-proxy-preflight/v1 <run_id> <challenge>` through the tunnel, and accepts only
`stage-d-proxy-preflight/v1 <run_id> <hmac_sha256>` where the MAC is
`HMAC-SHA-256(secret, message)` over a length-prefixed, domain-separated encoding of
the version, the run id and the challenge. The received MAC is compared with
`crypto.timingSafeEqual` after an explicit length check; the secret is never compared
with string equality, and no custom cryptographic construction is used.

**What a pass proves, precisely.** It proves the CONNECT tunnel reached an entity that
holds the configured preflight shared secret — target identity and control, to the
strength of that secret. It does **not** prove The Odds API is reachable, that the
provider would accept a request, that quota exists, that general external egress works,
or that the network will hold; `provider_reachability_proven` is `false` in every
preflight result. The accepted failure domain is symmetric: a compromised shared secret
would let a hostile responder forge attestation. That is why the secret is dedicated
(never shared with the provider key, the proxy credentials, any authorization or ledger
hash, or any machine identity), required to be at least 32 bytes of key material, never
logged or persisted in any form including its length, and rotatable by replacing the
verifier and target deployments together. Asymmetric attestation would remove the
shared-secret failure domain but is out of scope for this contract.

Replay is refused by construction rather than by a nonce store: the MAC is bound to a
challenge this execution has never seen before, so a response captured from any earlier
run cannot satisfy it. A response carrying a different run id is refused on binding
before its MAC is examined.

### Preflight shared secret

The shared secret is a third contract, separate from both the proxy endpoint and the
target address, named by `STAGE_D_PROXY_PREFLIGHT_SHARED_SECRET`. Its representation is
canonical base64 of opaque bytes, which is the one encoding that survives an
environment variable, a secret store and a deploy manifest without
re-interpretation, and it lets the contract state an entropy floor in bytes rather than
in characters. The value is validated strictly — non-base64, non-canonical base64,
mis-padded base64, and anything decoding to fewer than 32 bytes are each refused —
because a lenient decode would accept a truncated secret and turn a provisioning
mistake into an intermittent attestation failure against a live target instead of a
startup refusal.

It is required for production Stage D, and its absence, blankness or invalidity fails
closed **before any proxy socket is opened** and in every case before authorization
consumption. It is never generated at runtime, never defaulted, never falls back to an
embedded test value, and never has a tracked-source default: a secret this process
invents cannot be known by the target, so a silently generated value would convert a
missing deployment input into a confusing attestation failure. It is held off every
enumerable and serialized form of the resolved object — no bytes, no hash, no length,
no prefix, no suffix — and it never appears in a log, an error message, an evidence
artifact, a JSON report, a CLI summary or a test snapshot.

`PRODUCTION_PREFLIGHT_TARGET`, `PRODUCTION_SHARED_SECRET` and the production proxy
endpoint remain absent from tracked source by design. They are externally bound only in
the dedicated deployment environment; an omitted binding still fails closed before a
socket or authorization consumption, which is the intended and correct state.

The contract in the canonical form:

```
OWNER_PROXY_ARCHITECTURE_DECISION=DEDICATED_SINGLE_STABLE_HTTP_CONNECT_ENDPOINT
PREFLIGHT_TARGET_ARCHITECTURE=HYBRID_DEPLOYMENT_ABSTRACTION
PRODUCTION_PREFLIGHT_TARGET=DEDICATED_PROJECT_CONTROLLED_STATIC_TCP_ATTESTATION_TARGET
PREFLIGHT_ATTESTATION=HMAC_SHA256_SHARED_SECRET_CHALLENGE_RESPONSE
PREFLIGHT_SHARED_SECRET=REQUIRED_AND_EXTERNALLY_PROVISIONED
PRODUCTION_TARGET_ENDPOINT=EXTERNALLY_BOUND__REPOSITORY_UNTRACKED
PRODUCTION_SHARED_SECRET=EXTERNALLY_BOUND__REPOSITORY_UNTRACKED
PREFLIGHT_BEFORE_AUTHORIZATION_CONSUMPTION=YES
PROVIDER_REACHABILITY_NOT_PROVEN=YES
PREFLIGHT_PROOF_LEVEL=AUTHENTICATED_PROJECT_CONTROLLED_TARGET_REACHABILITY
INFORMED_REFLECTOR_WITHOUT_TARGET_CONTACT=FAIL
```

**No non-2xx status is accepted as proof of anything.** `403`, `407`, `502`, `503`
and `504` get no special acceptance, and neither does any other refusal. This is
deliberate and load-bearing: a proxy that cannot open a tunnel answers `502`/`504`,
and an ordinary HTTP origin server answers `400`, `404`, `405` or `501` to a CONNECT
it does not implement — and nothing in a status line distinguishes the two. Any
non-2xx allowlist would therefore admit a non-proxy endpoint through the last gate
before the one-shot authorization is spent. That is also why the probe target must be
genuinely reachable rather than deliberately unusable: a 2xx is only attainable when
the proxy can really reach the target, so strict 2xx plus a verified target attestation
is the one rule that is both satisfiable by a working proxy and unsatisfiable by
everything else.

A `407` fails closed whether or not credentials were configured: if the endpoint will
not authenticate this probe it will not authenticate the governed request either, so
passing there would spend the authorization on a request that cannot succeed. A
synthetic `200 Connection Established` that opens no tunnel fails the attestation and
is classified `PROXY_CONNECT_ATTESTATION_TIMEOUT` — once a 2xx has been received,
failing to complete the attestation is **always** an attestation classification and
never the bare protocol timeout that precedes it, so this case has exactly one
outcome. A reflected or synthesized response, a MAC computed under the wrong key, a
response bound to another run id, a malformed or mis-sized MAC, and a tunnel that
closes before attesting are each classified separately
(`PROXY_CONNECT_ATTESTATION_MAC_INVALID`,
`PROXY_CONNECT_ATTESTATION_RUN_ID_MISMATCH`,
`PROXY_CONNECT_ATTESTATION_MALFORMED`,
`PROXY_CONNECT_TUNNEL_PROOF_FAILED`) and none of them passes. A dead endpoint, a
non-HTTP listener, a closed connection without a status line, an inactivity timeout,
an `https://` TLS failure, an invalid or non-HTTP(S) endpoint URL and a rejected
configured credential are each classified separately and none of them passes either. A dead, missing, non-CONNECT or non-tunnelling
endpoint therefore leaves `AUTHORIZATION_CONSUMED=NO`,
`PROVIDER_REQUEST_ATTEMPTED=NO` and `QUOTA_UNITS_CHARGED_OR_ASSUMED=0`, and the
unconsumed authorization remains usable until its own `expires_at` once the endpoint
and target are provisioned.

Proxy credentials, when the endpoint carries them, are held off every enumerable and
serialized form of the endpoint. They never appear in logs, errors or evidence; the
agent URL that re-attaches them is built at the point of use only, and it is never
included in a message, a durable artifact or a preflight result. The preflight
attaches them through the same canonical path the real transport uses, so the two
cannot diverge: the URL userinfo is percent-decoded before the Basic payload is
encoded, exactly as `https-proxy-agent` does it. Encoding the still-encoded userinfo
instead would authenticate with different bytes than the transport, and a secret
containing `@`, `:` or `%` would reach the proxy mangled — producing a `407` that
says nothing about the transport's real chances.

## Durability, recovery, retention and backup

The current canonical authority failure domain and every locally discovered
artifact path are `/dev/nvme0n1p5`. A same-disk directory is explicitly not a
backup target. An independent off-host target **is** configured — a self-hosted
S3-compatible endpoint with `create_only: true` and no delete verb — and it holds
a real canonical backup generation,
`snap_20260915T125353656Z_d059e495e3047958`, written to it before this closure.
From merged main the closure proved that generation's remote verification and an
isolated restore of it. That proof closed Blocker #3 and was accepted as Gate 2
(`BLOCKER_3=CLOSED`, `GATE_2=ACCEPTED`; see
[`STAGE_D_BLOCKER_3_CLOSEOUT.md`](STAGE_D_BLOCKER_3_CLOSEOUT.md)). An earlier
revision of this section stated that no independent target was configured and
that no production backup or restore proof existed; that statement is superseded
by the closure. The closure's own operations wrote no new generation and deleted
nothing: it drove the real executor against the existing generation read-only and
re-read it with `listObjects`/`getObject` only — `baseline_object_count: 14` →
`observed_object_count: 14`, `differences: []` — so `writes_performed=0`,
`deletes_performed=0` and `NEW_BACKUP_GENERATION_WRITTEN=NO` scope to those
read-only operations, not to the earlier remote write that created the
generation. `OFF_HOST=YES` with `OFF_SITE=NO`,
and `DHCP_RESERVATION_STATUS=NOT_CONFIGURED`, remain registered non-blocking
hardening items rather than Gate 2 conditions. Neither the closure nor the
approved `RPO`/`RTO` objectives authorize any further backup generation or
restore; each of those still requires its own separate Owner authorization.

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

The service policy proposed here before the Owner's decision was: irrecoverable
evidence retained indefinitely, operational logs retained 90 days,
`RPO <= 24h`, `RTO <= 4h`. That proposal carried
`OWNER_APPROVAL_REQUIRED=YES`, and **that approval has since been given** — the
token is left in this sentence as the state it held at the time of the proposal,
not as current state. The Owner has approved retention, RPO and RTO, recorded in
[`STAGE_D_OWNER_DATA_PROTECTION_AND_CREDENTIAL_POLICY.md`](STAGE_D_OWNER_DATA_PROTECTION_AND_CREDENTIAL_POLICY.md).
The approved values are `RAW_RETENTION=LONG_TERM_NO_ROUTINE_DELETION`,
`PRIMARY_DATA_RETENTION=LONG_TERM`,
`INDEPENDENT_BACKUP_RETENTION_MINIMUM=180_DAYS`,
`MINIMUM_RECENT_SUCCESSFUL_BACKUP_GENERATIONS=30`, `RPO_APPROVED=24_HOURS` and
`RTO_APPROVED=24_HOURS`.

Reconciled item by item, because the approval does not match the proposal
uniformly:

| Proposed | Outcome |
| --- | --- |
| irrecoverable evidence retained indefinitely | Approved as `RAW_RETENTION=LONG_TERM_NO_ROUTINE_DELETION` / `PRIMARY_DATA_RETENTION=LONG_TERM`. That is a long-term, no-routine-deletion policy rather than a literal indefinite-retention commitment, and the approval adds two values the proposal did not carry at all: `INDEPENDENT_BACKUP_RETENTION_MINIMUM=180_DAYS` and `MINIMUM_RECENT_SUCCESSFUL_BACKUP_GENERATIONS=30`. |
| operational logs retained 90 days | **Not addressed** by the approval. Operational log retention remains unapproved. |
| `RPO <= 24h` | Approved and in agreement: `RPO_APPROVED=24_HOURS`. |
| `RTO <= 4h` | **Superseded**: the Owner approved 24 hours where this contract proposed 4, so `RTO_APPROVED=24_HOURS` is the binding objective and the proposal is superseded rather than silently restated. |

Those six approved values are **objectives**, not measured or exercised results:
no backup, failover or recovery drill has been run against them, and the approval
authorizes no Stage D start, no provider request and no change to `GATE_3`.

## Runtime filesystem permission contract (Blocker #2)

Cold-loading the canonical authority requires more than content validity: the
process that cold-loads must be able to reach and read every governed artifact
through ordinary POSIX permission checks. The machine-readable contract is
`stage-d-runtime-filesystem-permission/v1`, implemented by
`scripts/ops/stage_d_runtime_filesystem_permission_contract.js` (inspect and
classify), `scripts/ops/stage_d_runtime_filesystem_remediation_plan.js`
(plan only) and `scripts/ops/stage_d_runtime_filesystem_audit.js` — the
read-only publication audit the binder runs before it publishes anything.
`scripts/ops/stage_d_runtime_filesystem_inspect.js` exposes exactly
two modes, `audit` and `plan`; it has no apply mode, executes no privileged
command other than a read-only `getfacl` probe, and never escalates privilege.
With `--cold-load` it delegates content authority to the existing
transaction-v1 reader rather than re-implementing it.

The governed tree is **not** one permission domain. The contract separates an
`IMMUTABLE_HISTORICAL_READ_SURFACE` (transaction authority root, `STORE.json`,
the `committed/` root, each `tx_<sha>` package directory, the immutable package
files, the allocation authority artifact, the request-accounting epoch anchor
and ledger entries) from an `ACTIVE_RUNTIME_WRITE_SURFACE` (the `.staging`
root, the request-accounting root and its `entries/` directory, the run-lock
runtime trust root). Only the write surfaces are writable by the runtime; the
immutable read surfaces are never made group- or world-writable in order to
make cold-load succeed.

Observation is fail-closed about its own completeness. A directory that cannot
be listed is recorded as an `UNOBSERVABLE_DIRECTORY_LISTING` gap — an
unrepairable finding that blocks the plan outright — rather than being read as
an empty listing: otherwise a package directory that had lost its read bit
would silently drop all six governed package artifacts from the audit while the
plan still reported the tree as repairable. A directory that is simply absent
is a different case and is reported once, as `MISSING_REQUIRED_PATH`. The plan
is generated only from objects that were actually observed, so a repair plan can
never claim coverage of a file it never saw; the directory must be made readable
and the tree re-audited before a file-level plan is produced. Extended ACLs are
parsed with the same discipline: `getfacl` annotates every entry the mask limits
with a trailing `#effective:` comment — precisely the state the publisher's own
`fchmod` produces — and the parser strips it and accepts only a strict
`[r-][w-][x-]` permission triad, so an annotated value can never be recorded as
restorable and emitted as an invalid `setfacl` argument.

A declared ACL evidence set has to cover the whole governed tree, ancestry and
governed surfaces alike. An **ancestor** is what grants traversal to everything
beneath it, and under an extended ACL the group bits in `st_mode` are the mask
rather than the group policy, so a named-user entry that denies the runtime
identity is invisible in the mode. An ancestor whose `getfacl` probe fails — or
that a declared evidence set simply omits — is therefore a blocking
`ANCESTOR_ACL_PROBE_UNAVAILABLE` finding rather than a traverse inferred from
bits. A governed **surface** that the declared set omits is the same defect one
level down and is a blocking `ACL_EVIDENCE_MISSING` finding rather than a
verdict taken from its mode bits: the surface may carry a named entry that
denies the runtime, so a mode-only reading would report a surface nobody read as
clean. The gap is reachable in production rather than theoretical, because the
audit CLI probes the evidence set and enumerates the governed surfaces in two
separate passes, and a transaction package published between them arrives with
no entry. The audit CLI builds its probe set from the ancestry and the surfaces
for exactly this reason. "Absent from the evidence set" and "probed, and carries
no named entries" are different statements, and only declaring no ACL dimension
at all leaves the dimension unrun.

The required mechanism is **identity equality**: the uid that publishes the
authority, the uid that owns the governed tree, and the uid that cold-loads it
must be the same. Group access and named POSIX ACL entries are explicitly
rejected, because the existing publisher
(`src/infrastructure/market_evidence/atomicPublisher.js`) calls `fchmod(0o400)`
on every package artifact and `transactionStore` calls `chmod(0o444)` on
`STORE.json`; on POSIX a `chmod` re-derives the ACL mask from the group bits,
so a named-entry ACL is collapsed to `---` the moment the artifact is written.
The publisher's directory modes (`0o700`) are likewise owner-only. A contract
that relied on an ACL or on group bits would therefore be silently invalidated
by the ordinary publication path.

Recurrence prevention is enforced at the Stage D binder boundary:
`scripts/ops/stage_d_controlled_initialization.js` runs
`scripts/ops/stage_d_runtime_filesystem_audit.js` before any publication work
begins. The audit resolves the runtime identity from the authority root's
owning uid and fails closed — with no override flag — when the identity about to
publish is not that identity. A privileged identity is refused on **both** sides
of that comparison, not only when a uid 0 publisher meets a non-root runtime.
Because the binder derives the runtime identity from the authority anchor's
owner, a root process facing a root-owned anchor would otherwise produce uid 0
on both sides and verify itself, which is precisely how owner-only packages kept
being published; the audit therefore rejects a uid 0 publisher and a uid 0
runtime independently, and the contract already classifies a uid 0 runtime as a
violation. This matters because a transaction package is immutable once renamed
into `committed/`, so an inaccessible package is a permanent defect at
publication time, not a repairable inconvenience.

Identity is necessary but not sufficient, because it constrains *who* publishes
and not what that publisher will create. The audit therefore also refuses two
conditions that reproduce Blocker #2 from an anchor whose owner, group and mode
are already exactly right, and that leave no trace in that mode:

- a **default ACL** on the anchor or on `.staging`, which every directory
  `atomicPublisher.mkdirSync` creates below it inherits — an inherited mask caps
  the mode the publisher's own `fchmod` can produce, so the next package is
  already damaged when it is written; and
- an effective **umask that intersects `0o700`**, which silently reduces the
  directories the publisher asks `mkdir` for. Only the owner triad is
  load-bearing here: a umask that clears group and other bits (`0o077`) cannot
  damage an owner-only postcondition and is not treated as a hazard.

Both are read-only observations, neither is repairable by the repository, and
both are refused before the execution chain is entered. The anchor's ACLs are
read with the audit CLI's own `getfacl` probe, so the binder can never be
satisfied by weaker evidence than a full audit would accept — and where that
probe is unavailable the binder refuses rather than verifying on identity alone.

Status after this contract was added (historical, superseded by the current
status below): `BLOCKER_2_PHASE_A_IMPLEMENTED=YES`,
`BLOCKER_2_PRODUCTION_REMEDIATION=NOT_EXECUTED`, `BLOCKER_2=OPEN`,
`GATE_2=NOT_ACCEPTED`, `GATE_3=NOT_AUTHORIZED`. Applying any metadata repair to
the production authority remains a separate, separately authorized Phase B host
procedure — and that continues to hold for any *future* repair.

Status after the Phase B privilege and content-proof remediation below: the first
Owner-authorized Phase B preflight ran read-only through its pre-mutation recheck
and stopped **before any mutation** at a design gate, because the Phase B
preconditions as originally written required the repair process to run as the
runtime uid/gid while every operation the planner emits against the real
production plan requires elevated privilege. Production was left untouched
(`PRODUCTION_PERMISSION_MUTATED=NO`, `PRODUCTION_CONTENT_MUTATED=NO`). That
precondition has been replaced by the explicit three-role identity model below.
`BLOCKER_2=OPEN`, `GATE_2=NOT_ACCEPTED`, `GATE_3=NOT_AUTHORIZED` were unchanged
at that point.

**Blocker #3 tooling.** The repository-side backup and isolated-restore tooling
for Blocker #3 is specified by its own contract,
[`STAGE_D_BLOCKER_3_BACKUP_TOOLING_CONTRACT.md`](STAGE_D_BLOCKER_3_BACKUP_TOOLING_CONTRACT.md).
It is explicit-invocation only: it is **not** called from `atomicPublisher`,
`stageDOperations`, the publication path, the scheduler, controlled
initialization, the request cycle or the transaction commit, so nothing in this
contract's live path can trigger a backup and nothing in the backup tooling can
trigger a cycle. Its live off-host entrypoints are separate scripts
(`stage_d_r2_backup_live.js`, `stage_d_r2_restore_live.js`) and the original
offline CLIs are byte-unchanged and remain netless; the live path takes its
target identity and its credential from explicit files, never from the
environment, a profile or a provider chain, and never from its own argv.
`LIVE_R2_CLI_WIRING=IMPLEMENTED` and
`LIVE_CONNECTIVITY_PREFLIGHT=NOT_PERFORMED`: the wiring is proven offline against
a stub SDK, and no R2 request has been made. The runtime backup credential is
required to be a data-plane credential and must not carry bucket-administration
authority, which is what makes `NORMAL_BACKUP_RUNTIME_CAN_REMOVE_LOCK=NO` true of
it; bucket lock configuration is out of scope for this work and no lock was
configured. At the time this paragraph was written Blocker #3 was still OPEN and
`GATE_2`/`GATE_3` were unchanged by it; both have since moved — `BLOCKER_3=CLOSED`
and `GATE_2=ACCEPTED`, with `GATE_3=NOT_AUTHORIZED` unchanged — on separately
authorized evidence recorded in
[`STAGE_D_BLOCKER_3_CLOSEOUT.md`](STAGE_D_BLOCKER_3_CLOSEOUT.md). Nothing in the
tooling description above changes with that closure.

**Current status.** The Owner-authorized Phase B execution governed by this
contract has since been executed and verified; the outcome is recorded in
[`STAGE_D_BLOCKER_2_PHASE_B_CLOSEOUT.md`](STAGE_D_BLOCKER_2_PHASE_B_CLOSEOUT.md).
`BLOCKER_2_PRODUCTION_REMEDIATION=EXECUTED_AND_VERIFIED`, `BLOCKER_2=CLOSED`,
`PHASE_B_COMPLETE=YES`. At that point `GATE_2=NOT_ACCEPTED` and
`GATE_3=NOT_AUTHORIZED` were deliberately retained because `BLOCKER_3` remained
open; `GATE_2` has since been accepted when `BLOCKER_3` was closed, and
`GATE_3=NOT_AUTHORIZED` still stands. See
[`STAGE_D_BLOCKER_3_CLOSEOUT.md`](STAGE_D_BLOCKER_3_CLOSEOUT.md). That execution ran under
its own separate authorization, and those authorizations are **spent**:
`PHASE_B_EXECUTION_AUTHORIZED=NO` in the block below still governs any future
repair, and the closeout is a historical adjudication of one evidence set that
does **not** authorize a future executor to skip a planner operation because it
believes that operation's postcondition already holds.

### Phase B host remediation procedure (governed here; future execution not authorized)

Phase A emits a plan and cannot apply one. Applying it is a separate
Owner-authorized host procedure, specified here so that it is bounded by the
same contract. No repository entrypoint can execute it: the audit CLI has no
apply mode and the planner is inert.

```text
PHASE_B_MUTATION_CLASS=OWNER_GROUP_MODE_METADATA_ONLY
PHASE_B_CONTENT_WRITE=FORBIDDEN
PHASE_B_RECURSIVE_CHMOD_CHOWN=FORBIDDEN
PHASE_B_EXECUTION_AUTHORIZED=NO
PHASE_B_REQUIRES=OWNER_AUTHORIZATION_AND_EXACT_PRECHECK_EVIDENCE
PHASE_B_REPAIR_EXECUTOR_POLICY=BOUNDED_PRIVILEGED_HOST_EXECUTOR
PHASE_B_RUNTIME_CAPABILITY_INJECTION=FORBIDDEN
PHASE_B_ALLOWED_OPERATION_CLASSES=CHOWN,REMOVE_EXTENDED_ACL,CHMOD
PHASE_B_EXECUTOR_IS_PROOF_IDENTITY=NO
```

#### Phase B identity model — three roles, never collapsed

An earlier revision of this section required "the repair process runs as the
runtime uid/gid that will cold-load the authority". That requirement is
unsatisfiable against the defect it exists to repair and has been removed: a
governed package published by a root-running publisher is owned by uid 0, and the
identity that cannot read it is by construction the identity that cannot
`chown`, `chmod` or `setfacl` it either. Requiring the two to be the same process
forbade every operation the planner emits. The three roles are now stated
separately, and the planner emits them as machine-readable fields
(`target_runtime_identity`, `repair_executor_policy`,
`pre_content_evidence_policy`).

**`TARGET_RUNTIME_IDENTITY`** is the ordinary identity that must own the repaired
governed surfaces and must cold-load the accepted authority afterwards. It is
freshly resolved at each Phase B execution from the authority anchor's owner —
never hard-coded — and it must not acquire a permanent elevated capability in
order to make Phase B work. It, and only it, performs the ordinary cold-load and
the fresh-process cold-load that constitute the access proof.

**`REPAIR_EXECUTOR_IDENTITY`** is a temporary, bounded, privileged host principal
whose existence is scoped to the repair window and whose authority is the
planner's exact output and nothing else. Its canonical policy is
`BOUNDED_PRIVILEGED_HOST_EXECUTOR`. It is authorized to apply only operations the
planner emitted, only when that operation carries
`elevated_privilege_required=true`, and only within the classes `CHOWN`,
`REMOVE_EXTENDED_ACL` and `CHMOD`. It may not choose arbitrary paths, add
operations, recurse, open an exploratory root shell, rewrite content, create or
delete a transaction, edit `STORE.json` or the allocation authority, or make a
provider or network request; its privilege ends when the bounded operation set
ends. **It is never the proof identity**: privileged success is not evidence that
the target runtime identity can read the authority, and a cold-load that
succeeded as the executor proves nothing about production.

A capability injected into the Stage D runtime identity (`CAP_CHOWN`,
`CAP_FOWNER`) is explicitly **not** the canonical design. It would leave every
future publication and cold-load running under a permanent capability this
contract never described, which is a worse defect than the one Phase B repairs.
`RUNTIME_CAPABILITY_INJECTION_POLICY=FORBIDDEN`.

**`PRE_REPAIR_CONTENT_EVIDENCE_READER`** is a distinct role for content evidence
collection, separate from both runtime validation and metadata mutation. It uses
an ordinary runtime read wherever that works. Only for a governed artifact that
is `EACCES` to the target runtime identity *because of the permission defect this
plan repairs* may it fall back to a privileged **read-only** open, and then only
to stream the existing inode's bytes into a SHA-256 and close. It may not write,
truncate, rename, copy over, `chmod`, `chown`, `setfacl`, repair metadata or
content, or publish; and it may not satisfy any runtime-access, transaction-head,
authority-state-hash or observation-count proof.

**Preconditions.** The accepted authority identity is unchanged and the exact
main revision equals the authorizing revision; the target runtime identity is the
ordinary uid/gid that must cold-load the authority after repair and holds no
persistent elevation; metadata mutation, where an operation requires it, is
performed by the separately bounded privileged host executor above under a
separate Owner-authorized Phase B authorization, and never becomes the proof
identity; the governed roots are on the expected filesystem device; no Stage D
run is active (the run lock is absent or already reconciled), the scheduler is
disabled and no provider request is authorized; and the pre-repair evidence below
has already been captured outside the tree that will be mutated.

**Pre-repair evidence.** A full governed-path metadata manifest (path, object
type, uid, gid, mode, device, inode, link count), a content SHA-256 manifest for
every governed artifact, the cold-load status of the authority as the runtime
identity, and the `STORE.json` and allocation-authority hashes.

*Content hashes are never optional.* Every governed artifact must carry a
`PRE_CONTENT_SHA256`, and the manifest records for each one which role produced
it — `ORDINARY_RUNTIME_READ` or `PRIVILEGED_READ_ONLY_EVIDENCE`. An artifact whose
pre-repair hash is missing is a blocking finding; the repair does not proceed and
no operation is applied against it. The digest is a precondition of both roles,
not a consequence of either: a manifest entry that names a permitted role but
carries no well-formed 64-hex digest is itself a blocking finding, because a
permitted reader that produced no hash is not content evidence and a set that
admitted one would be `READY` while proving nothing per artifact. The weaker
invariant "the post-repair content manifest matches the manifest commitment" is
**not** accepted as a substitute:
a commitment cannot prove that the bytes a privileged reader saw are the bytes
the ordinary runtime identity will later read. The proof is `PRE_SHA256 ==
POST_SHA256` per artifact, with the post-repair hash taken by the target runtime
identity through an ordinary read, so `POST == manifest commitment` is only ever
a second, independent check.

*The set is the plan's, not the manifest's.* The artifacts the proof ranges over
are enumerated by the plan — the governed surfaces that are regular files with
immutable content — and the manifest has to cover exactly that set. A manifest
that omits a governed artifact, names one twice, or carries a path the plan does
not govern is a blocking finding for that reason alone, and the verdict reports
which paths were missing, duplicated or ungoverned. Coverage is deliberately not
taken from the manifest's own length: that would make it a property of whoever
assembled the manifest, and the artifact easiest to leave out — the `EACCES` one
that the privileged reader exists for — would be exactly the one whose absence
shrank the proof instead of blocking it. A directory is governed but is not
content: it has no bytes, so no read of it, ordinary or privileged, is content
evidence.

Every artifact the target runtime identity can read is hashed by it, and that
hash's evidence source is `ORDINARY_RUNTIME_READ`. Only an artifact whose read
fails with `EACCES` *because of the permission defect this plan repairs* — the
defect being a mode/ownership/ACL finding the plan repairs for that exact path,
with the artifact bound to its observed device and inode, symlink-free, beneath
real directories — falls back to `PRIVILEGED_READ_ONLY_EVIDENCE` through the
`PRE_REPAIR_CONTENT_EVIDENCE_READER` role above. A read that failed for any other
reason (`EIO`, a missing path, a symlink, an unbound observation) has no
permitted evidence source and blocks. The fallback is read-only by construction
and is recorded per artifact, so the privileged surface of a Phase B execution is
auditable from the evidence root alone.

The authority head/state hash is recorded only if it is readable through an
already privileged evidence source; it is never obtained by escalating. A
privileged read is content evidence only: it can never satisfy the runtime-access,
transaction-head, authority-state-hash, observation-count or cold-load proofs,
which the `TARGET_RUNTIME_IDENTITY` must produce for itself.

The evidence capture must run where extended ACLs are observable. `getfacl` is
part of the `acl` package and is absent from the dev container, so a run inside
it records `ACL_PROBE_UNAVAILABLE` and the planner refuses any
`REMOVE_EXTENDED_ACL` operation (`ACL_ROLLBACK_EVIDENCE_MISSING`) rather than
deleting named entries it cannot restore. Phase B is therefore a host procedure
by construction, not a container one.

**Mutation.** Only the operations the planner emitted for the enumerated
allow-list, each applied per object after re-opening it with `O_NOFOLLOW` and
re-verifying that device/inode still match the plan's `pre` state. Path
resolution is validated above the leaf as well as at it: `O_NOFOLLOW` protects
only the last component, and a governed name whose parent directory is a symlink
resolves to an object outside the governed tree while still presenting an
ordinary regular file to every check made on the path itself — the `pre`
device/inode comparison would compare that external object against itself and
pass. The planner therefore re-walks each path's ancestry from fresh
observations and refuses every path beneath a component that is not a real
directory, so no operation is emitted for an object this contract has no
authority over. Ownership and mode changes are metadata-only; no content is
written and no artifact is
recreated, truncated or re-published. Recursive `chmod -R` and `chown -R` are
forbidden: an exact validated allow-list is enumerated first and every object is
verified individually. An operation whose `pre` observation no longer matches at
apply time aborts the procedure rather than being forced.

The mutations are applied by the `REPAIR_EXECUTOR_IDENTITY` under
`BOUNDED_PRIVILEGED_HOST_EXECUTOR`, whose authority is the planner's exact output
and nothing else. It applies an operation only when that operation carries
`elevated_privilege_required=true`, and only within `CHOWN`,
`REMOVE_EXTENDED_ACL` and `CHMOD`. It may not add, reorder or widen operations,
resolve a path other than the one recorded, follow a symlink, recurse, open an
exploratory root shell, run a package manager, touch the network, or read or
write any path outside the enumerated set. Its elevation is scoped to the bounded
operation set and ends with it: no file capability is left on any binary, no
`setuid` helper is installed, and no capability is granted to the Stage D runtime
identity. It must not become the proof identity — a cold-load that succeeded as
the executor, and in particular as root, is **not** evidence that the target
runtime identity can cold-load the authority, and no root cold-load may be
reported as the access proof.

Every privileged mutation is journalled before and after it is applied, with the
exact argv, the observed `pre` and resulting `post` metadata, and the rollback
entry that undoes it. If the executor's privilege is unavailable when an
operation needs it, the operation is not attempted with reduced semantics and the
procedure stops. If the plan, the observed metadata or the executor's own
identity drifts mid-procedure, the procedure stops rather than adapting, and a
partial application is recovered only by replaying the exact rollback entries of
the operations that were actually applied, in the planner's rollback order.

**Post-repair proof.** A metadata manifest matching the contract's
postconditions; a content SHA-256 manifest in which every artifact's
`POST_CONTENT_SHA256` equals its recorded `PRE_CONTENT_SHA256`, taken by the
target runtime identity through an ordinary read, so
`CONTENT_BYTES_BEFORE == CONTENT_BYTES_AFTER`; a successful ordinary cold-load by
the runtime identity; and exact reproduction of the accepted authority head,
state hash, `OBSERVATION_COUNT=903`, `STORE_SHA256` and
`ALLOCATION_AUTHORITY_SHA256`, repeated across a fresh process boundary.

The post-repair manifest requires no privileged read at all: if any artifact
still cannot be hashed by the target runtime identity after the repair, the
repair did not achieve its purpose regardless of what the executor observed, and
the result is `BLOCKED` rather than a passing proof.

**Rollback.** The planner pairs every operation with a metadata-only rollback
entry carrying the original uid/gid/mode/device/inode. Rollback is emitted in
the **same** order as apply rather than in reverse, because the constraints are
the same in both directions: `chown` clears the set-user/set-group bits of a
non-directory on this kernel even for a privileged caller, so ownership must be
restored before the mode is written, and `setfacl --set` rewrites the mask, so
the mode must be written after the ACL is back. Rolling back in reverse would put
the `chown` last and leave a path whose mode is not the recorded one whenever its
ownership and its special bits have both moved. Restoring
uid/gid/mode does fully undo a `CHOWN` or `CHMOD`, including the ACL mask: for a
file carrying an extended ACL the group bits *are* the mask. It does **not**
undo `REMOVE_EXTENDED_ACL`, which deletes named entries no mode change can bring
back, so that operation carries the exact observed ACL as a replayable
`setfacl --set` payload and is blocked outright when the ACL was not observed
completely. Rollback restores metadata only and is subject to the same
post-repair content-hash proof.

## Failure matrix

| Failure | Request consumed? | Retry allowed? | Canonical mutation? | Next run? | Manual review? |
| --- | --- | --- | --- | --- | --- |
| Provider timeout / no response | yes | only new request + budget | no | after terminal ledger and clean lock release | no |
| HTTP error | yes | only new request + budget | no | after terminal ledger and clean lock release | no |
| Quota exhausted / quota unknown | no | no until configuration changes | no | no | quota owner for unknown/exhausted |
| Credential invalid before transmission | no | no until credentials are corrected | no | after terminal ledger and clean lock release | credential owner |
| Stage D proxy endpoint, preflight target or preflight shared secret missing, dead, non-CONNECT, or unable to carry a verified target attestation (preflight) | no | yes, with the same unconsumed authorization, once the endpoint, target and shared secret are provisioned and the preflight passes | no | after all three are configured | proxy/network owner |
| Scheduler duplicate / stale lock / lock ambiguity | no | no | no | no | yes |
| RAW or receipt persistence failure after possible transmission | yes | only new request + budget | no | after terminal ledger | yes |
| Parser, identity, registry failure | yes | only new request + budget | no | after terminal ledger | yes |
| Transaction publication failure / authority reopen failure | yes | no while lock remains | no or unknown | no | yes |
| Governed authority unreadable by the cold-loading runtime identity (permission defect) | no | no until the authority is readable | no | no | yes — separate owner-authorized Phase B metadata repair; never a content rewrite |
| Backup failure / disk full | request state unchanged unless transmission already occurred | no automatic retry | no | no if authority state is ambiguous | yes |
| Crash before transmission | no | no until lock reconciliation | no | no | yes |
| Crash after transmission boundary | yes / ambiguous-consumed | no until lock reconciliation | no | no | yes |

The Stage C authority is not a compensation mechanism for these failures. Stage D
is still not authorized or started.
