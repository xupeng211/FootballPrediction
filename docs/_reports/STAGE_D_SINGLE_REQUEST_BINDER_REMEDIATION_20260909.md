# Stage D single-request binder remediation evidence

> lifecycle: remediation evidence
>
> scope: GATE_2 blocker #1 only
>
> this report is not GATE_2 acceptance, GATE_3 authorization, provider-request authorization, or a live execution record.

```text
MISSION=STAGE_D_PRODUCTION_SINGLE_REQUEST_BINDER_CLI_REMEDIATION
CLASSIFICATION=PASS
TARGET_BLOCKER=1
BLOCKER_2_TOUCHED=NO
BLOCKER_3_TOUCHED=NO
STAGE_D_AUTHORIZED=NO
PROVIDER_REQUEST_AUTHORIZED=NO
GATE_3_AUTHORIZED=NO
REAL_PROVIDER_REQUEST_EXECUTED=NO
PROVIDER_QUOTA_CONSUMED=NO
PRODUCTION_AUTHORITY_MUTATED=NO
```

## 1. Start state and preservation

```text
REPO=/home/xupeng/FootballPrediction.clean-dev
START_BRANCH=ops/remote-backup-host-rediscovery-strict-gate-recovery
START_HEAD=21d8f030d5877d1059d1037d128980d756c35860
ORIGIN_MAIN=21d8f030d5877d1059d1037d128980d756c35860
EXPECTED_MAIN=21d8f030d5877d1059d1037d128980d756c35860
HEAD_EQ_ORIGIN_MAIN_EQ_EXPECTED=YES
BRANCH_IS_MAIN=NO
PREEXISTING_DIRTY_FILE=docs/_reports/STAGE_D_GATE_2_CONTROLLED_INITIALIZATION_PLAN_20260909.md
PREEXISTING_DIRTY_FILE_SHA256=a482aafa029fe2dd6b5abbdc7f161842c9d25edff321859a9a7bbdaea1a49883
GATE_2_ARTIFACT_PRESERVED=YES
UNRELATED_USER_WORK_PRESERVED=YES
```

The prior Gate 2 planning artifact was read before modification and its bytes
were not edited, moved, deleted, staged, or committed by this mission. The
mission changes are limited to the private binder boundary, its CLI, tests,
and the corresponding canonical entrypoint/current-state documentation.
No change was made to `AGENTS.md`, `PROJECT_VISION.md`, quota policy,
request-accounting semantics, transaction-package ownership/mode, backup
implementation, restore implementation, provider adapter semantics, identity
policy, or scheduler behavior.

## 2. Exact implementation path

| Boundary | Confirmed implementation |
| --- | --- |
| Existing module-private capability | `src/infrastructure/market_evidence/stageDOperations.js`: private `STAGE_D_RUNTIME_AUTHORIZATION` symbol and `executeStageDOneCycle` capability check. The symbol is not exported. |
| New production binder | `src/infrastructure/market_evidence/stageDOperations.js`: exported `executeStageDControlledInitialization(options)`. This is the only code path that creates the production runtime capability. |
| Private capability creation | Private `createStageDProductionRuntimeAuthorization()` returns the non-exported symbol only after authorization read, exact-scope validation, quota validation and single-use consumption-marker creation. |
| CLI | `scripts/ops/stage_d_controlled_initialization.js`: `main()` calls only `executeStageDControlledInitialization`; its parser accepts eight bounded artifact/path flags and `--help`. |
| Existing offline CLI | `scripts/ops/stage_d_cycle.js --dry-run` remains offline-only and was not replaced or widened. |
| Authorization read/validation | `readStageDControlledAuthorization` + `validateStageDControlledAuthorization`; canonical JSON, read-only regular file, direct child of explicit external runtime trust root, owner runtime user/root, exact keys and exact hash/scope bindings are required. |
| Single-use/replay | `consumeStageDControlledAuthorization` creates `.stage-d-authorization-consumed-<authorization_id>.json` with exclusive immutable creation and fsync; `EEXIST` is `STAGE_D_AUTHORIZATION_REPLAY`. |
| Shared engine call | The binder passes the private capability, authorization-provided `run_id`/`request_id`, normalized approved quota, fixed production factories and the expected authority pre-state into `executeStageDOneCycle`. |
| Authority race fence | `expectedAuthorityPreState` is checked again after the shared run lock and fresh authority reopen, including head/state/observation count/STORE hash/allocation hash. |
| Production components | Production binder fixes `createStageDOddsApiTransport`, `createStageDEvidencePersistence`, `createStageDProspectiveCandidateBuilder`, and `createStageDTransactionPublisher`; component injection is rejected outside `NODE_ENV=test`. |

The authorization artifact schema is
`footballprediction-stage-d-controlled-initialization-authorization/v1`.
Required approval status is `OWNER_AND_CHIEF_ENGINEER_AUTHORIZED`. The exact
bounded fields include mission, provider, `configured_markets=[h2h]`,
`configured_regions=[uk]`, `max_provider_requests=1`,
`expected_request_cost_credits=1`, accounting epoch, authority pre-state,
quota configuration hash, fixture-universe RAW hash, run/request IDs and a
maximum 24-hour validity window. The artifact itself is not produced by this
mission.

The CLI command shape is:

```bash
node scripts/ops/stage_d_controlled_initialization.js \
  --authorization <direct-child-of-external-runtime-trust-root> \
  --authority-root <authorized-transaction-authority-root> \
  --allocation-authority <authorized-allocation-authority-file> \
  --ledger-root <authorized-request-accounting-root> \
  --quota-config <authorized-quota-config-file> \
  --fixture-universe-raw <authorized-fixture-universe-raw-file> \
  --evidence-root <authorized-evidence-root> \
  --run-lock-trust-root <authorized-external-runtime-trust-root>
```

This command is a future command only. It was not run with an authorization
artifact, provider credential, production authority, or live transport.

## 3. One-request proof and fail-closed boundary

The structural chain is:

```text
bounded authorization artifact
  -> exact provider/market/region/max/cost/epoch/authority/hash validation
  -> approved quota normalization
  -> exclusive single-use authorization marker
  -> private runtime Symbol created inside the module
  -> executeStageDOneCycle
  -> one REQUEST_INTENT / one transmission marker / one transport.send
  -> one terminal ledger outcome
```

The existing engine and transport provide the following independent controls:

1. `MAX_PROVIDER_REQUESTS_PER_CYCLE=1`, quota
   `max_requests_per_stage_d_run=1`, `max_provider_requests_per_cycle=1`,
   and expected request cost `1` are all validated. An authorization with
   `max_provider_requests > 1` is rejected before transport transmission.
2. `assertRequestBudget` reads the exact durable epoch/ledger, rejects
   ambiguous consumption and duplicate run IDs, and admits only one expected
   credit. Historical accounting remains
   `AT_LEAST_2_CONFIRMED` / exact `UNKNOWN`.
3. `executeStageDOneCycle` contains one provider `transport.send` call. The
   production The Odds API transport contains one `https.request` call and no
   retry loop. Provider, market, region and transaction publisher bindings are
   fixed by the reviewed factories.
4. Transmission failures, RAW/receipt failures, parser failures and HTTP
   failures are terminal consumed outcomes; they never invoke a second send.
   The run lock, generation anchor and ledger terminal state prevent an
   automatic retry or same-run replay.
5. Authorization replay is rejected by the immutable consumption marker
   before the second binder call can reach the shared engine.

The binder fails closed for missing/malformed/non-canonical/writable/untrusted
authorization, expired scope, wrong provider, wrong market, wrong region,
wrong epoch, wrong authority pre-state, wrong quota or fixture hash, unknown
quota, max greater than one, replay, caller-supplied `runtimeAuthorization`,
component override in production, missing external trust root, and any
existing engine lock/ledger/authority/quota ambiguity.

The CLI has no `--authorized`, `--runtime-authorized`, `--bypass-auth`,
`--force-live`, `--live`, retry-count, provider, market, region or raw-symbol
flag. The private capability is neither returned nor logged, and no secret or
credential is serialized into the authorization consumption marker or audit
result.

## 4. Networkless proof

Added test file:
`tests/unit/market_evidence/stage_d_controlled_initialization.test.js`.
It sets `NODE_ENV=test`, supplies every binder component explicitly, and uses
`createStageDFakeTransport` (`network_capability=none`) with temporary authority,
ledger, trust, evidence and fixture roots. The binder rejects missing component
overrides in test mode; it cannot construct the real provider transport in this
test path. The real CLI was invoked only with `--help`, which exits before
loading a provider transport.

The 12 new tests cover:

```text
NO_AUTHORIZATION_REJECTED_WITH_ZERO_TRANSMISSIONS=PASS
MALFORMED_AUTHORIZATION_REJECTED_WITH_ZERO_TRANSMISSIONS=PASS
WRONG_PROVIDER_REJECTED_WITH_ZERO_TRANSMISSIONS=PASS
WRONG_MARKET_REJECTED_WITH_ZERO_TRANSMISSIONS=PASS
WRONG_REGION_REJECTED_WITH_ZERO_TRANSMISSIONS=PASS
MAX_REQUESTS_2_REJECTED_WITH_ZERO_TRANSMISSIONS=PASS
WRONG_ACCOUNTING_EPOCH_REJECTED_WITH_ZERO_TRANSMISSIONS=PASS
UNKNOWN_QUOTA_REJECTED_WITH_ZERO_TRANSMISSIONS=PASS
VALID_OFFLINE_SINGLE_CYCLE_FAKE_TRANSMISSIONS_MAX_1=PASS
REPLAY_OR_SECOND_USE_DOES_NOT_CAUSE_SECOND_TRANSMISSION=PASS
ERROR_AFTER_TRANSMISSION_DOES_NOT_TRIGGER_SECOND_PROVIDER_TRANSMISSION=PASS
CLI_CANNOT_ACCEPT_RAW_PRIVATE_RUNTIME_AUTHORIZATION_FROM_OPERATOR=PASS
CALLER_SUPPLIED_PRIVATE_CAPABILITY_REJECTED=PASS
```

The test runner reports 12/12 test cases passing (13 named negative/positive
assertion categories above because the first test case covers both missing and
malformed artifacts). The valid path recorded exactly one
fake transport call; the replay path recorded one first call and zero second
calls; the post-transmission error path recorded one call and a durable
`TRANSPORT_FAILURE_AFTER_POSSIBLE_TRANSMISSION` terminal state. All rejected
paths recorded zero fake transport calls and zero temporary ledger requests.

## 5. Existing Stage D regression and validation evidence

Commands actually run and results:

```text
node --check src/infrastructure/market_evidence/stageDOperations.js                         PASS
node --check scripts/ops/stage_d_controlled_initialization.js                                PASS
node --check tests/unit/market_evidence/stage_d_controlled_initialization.test.js             PASS
npx eslint <three changed JavaScript files>                                                    PASS
git diff --check                                                                               PASS
node --test tests/unit/market_evidence/stage_d_controlled_initialization.test.js               12/12 PASS
TMPDIR=<nested temporary directory> node --test stage_d_operations + stage_d_boundary_security 39/39 PASS
node scripts/ops/stage_d_controlled_initialization.js --help                                  PASS; no provider path
make verify-targeted                                                                           PASS
make verify-strict                                                                             PASS; gatekeeper mode=push
```

The direct Stage D regression command without a nested `TMPDIR` exposed an
existing test-only fallback assumption: four old run-lock tests attempted to
create `/.stage-d-runtime-trust` when executed as non-root. No source or
filesystem workaround was made. The same existing regression suite passed
39/39 with a nested temporary directory, and both canonical validation
profiles passed. No live provider path was executed by either profile.

## 6. Production state and no-side-effect evidence

The accepted authority pre-state remains:

```text
AUTHORITY_HEAD=tx_0ba8d4ad78aef57d1bbadf6637198b08d9586c5debf3e343d07033ed98a6bb64
STATE_HASH=df5084b6d752d698bfde4646fb508f3a41396f160fbee3cca9ee1b3b412e5ddd
OBSERVATIONS=903
STORE_SHA256=ed014a6f151143aa30cefcebc47374059aa18c38a83560610571331a665199e4
ALLOCATION_AUTHORITY_SHA256=89e4276c8fe637318339821fe40d783d2f7fd8de65f6fc593b2035bd9445dad3
```

Read-only checks during this mission also reported:

```text
PRIMARY_STORE_SHA256=ed014a6f151143aa30cefcebc47374059aa18c38a83560610571331a665199e4
PRIMARY_ALLOCATION_SHA256=89e4276c8fe637318339821fe40d783d2f7fd8de65f6fc593b2035bd9445dad3
ACCOUNTING_EPOCH_ID=sde_b10b6bd109a6c60498fbd9e8c9ec87894e79ca1091aedbdb229083199cd00406
POST_EPOCH_ENTRY_COUNT_BEFORE=0
POST_EPOCH_REQUEST_COUNT_BEFORE=0
POST_EPOCH_LAST_ENTRY_HASH_BEFORE=e0cc9d8b901e9acb2126eacbb37fa8b0a1dc5241362c19726ed2e9de25cfad9e
POST_EPOCH_ENTRY_COUNT_AFTER=0
POST_EPOCH_REQUEST_COUNT_AFTER=0
POST_EPOCH_LAST_ENTRY_HASH_AFTER=e0cc9d8b901e9acb2126eacbb37fa8b0a1dc5241362c19726ed2e9de25cfad9e
PRE_EPOCH_REQUEST_TOTAL_LOWER_BOUND=AT_LEAST_2_CONFIRMED
PRE_EPOCH_REQUEST_EXACT_TOTAL=UNKNOWN
```

The primary committed transaction package remains `root:root`/`0400` for
the ordinary `xupeng` runtime user. A primary authority cold-load under that
identity still fails with the existing permission blocker; this mission did
not use sudo, chmod, chown, a root workaround, or a production write. The
accepted snapshot remained unchanged. Its manifest SHA is
`4397f0a432f22154492e80abfd8f79100b20fe7ce30dff5d67487231bdd1fa74`; its
`sha256sum -c SHA256SUMS` completed with every listed file `OK`. This verifies
planning integrity, not independent physical fault-domain readiness.

```text
REAL_PROVIDER_REQUEST_EXECUTED=NO
PROVIDER_QUOTA_CONSUMED=NO
PRODUCTION_AUTHORITY_MUTATED=NO
PRODUCTION_LEDGER_MUTATED=NO
STAGE_D_STARTED=NO
SCHEDULER_STARTED=NO
BLOCKER_2_REMEDIATION_ATTEMPTED=NO
BLOCKER_3_REMEDIATION_ATTEMPTED=NO
```

## 7. Documentation impact and handoff

Because the production-facing canonical entrypoint and authorization contract
changed, the following authoritative current-state documents were updated:

```text
README.md
docs/CAPABILITY_INDEX.md
docs/ACTIVE_MILESTONE.md
docs/PROJECT_STATUS.md
docs/data/STAGE_D_CONTINUOUS_OPERATIONS_CONTRACT.md
```

`PROJECT_VISION.md` was reviewed and did not require an update: the change
implements the already-described controlled market-evidence boundary and does
not add a new North Star capability. The prior Gate 2 artifact was preserved,
not rewritten to claim acceptance.

The only future live command proposed by this remediation is the exact CLI
command in section 2, preceded by the existing offline preflight command:

```bash
node scripts/ops/stage_d_cycle.js --dry-run \
  --authority-root <authority-root> \
  --ledger-root <ledger-root> \
  --quota-config <quota-config> \
  --operation-root <operation-root> \
  --run-lock-trust-root <runtime-trust-root> \
  --run-id <single-use-run-id> \
  --now <utc-now>

node scripts/ops/stage_d_controlled_initialization.js \
  --authorization <authorization-artifact> \
  --authority-root <authority-root> \
  --allocation-authority <allocation-authority> \
  --ledger-root <ledger-root> \
  --quota-config <quota-config> \
  --fixture-universe-raw <fixture-universe-raw> \
  --evidence-root <evidence-root> \
  --run-lock-trust-root <runtime-trust-root>
```

Neither future command was run as a live initialization. The second command
still requires separate Owner and Chief Engineer authorization, and the
ordinary runtime permission and independent backup blockers remain unresolved.
After one separately authorized invocation and its evidence capture, the
future executor must stop; it must not start a second request, another cycle,
or scheduler.

```text
CAPABILITY_INDEX_UPDATE_REQUIRED=YES
ACTIVE_MILESTONE_UPDATE_REQUIRED=YES
PROJECT_STATUS_UPDATE_REQUIRED=YES
README_ENTRYPOINT_UPDATE_REQUIRED=YES
PROJECT_MAP_UPDATE_REQUIRED=NO
PROJECT_VISION_UPDATE_REQUIRED=NO
```
