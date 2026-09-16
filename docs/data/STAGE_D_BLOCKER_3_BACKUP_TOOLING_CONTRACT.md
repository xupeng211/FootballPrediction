# Stage D Blocker #3 — independent backup and isolated-restore tooling contract

> lifecycle: current-state contract
>
> 状态：`TOOLING_IMPLEMENTED__OFFLINE_ONLY__NOT_WIRED_TO_A_TARGET`。本合同定义 Stage D
> Blocker #3 的 repository-side backup / restore tooling 边界：它可以被构建、被离线证明，但
> **没有** target、**没有** credential、**没有** CLI wiring。它不授权 R2 provisioning、
> 不授权真实 backup、不授权 production restore，也不关闭 Blocker #3。

## Why Blocker #3 exists

Stage D's accepted authority and its evidence currently live in one physical
failure domain. A single disk, a single host or a single filesystem event can
take the authority and every copy of it at once, so no restore procedure
existing only on that host is a restore procedure at all. Blocker #3 is closed
by a target in a *different* physical fault domain, plus an isolated-restore
proof run against it — not by a script that copies files next to the originals.

This document specifies the repository-side half of that work. Provisioning the
off-host target is an Owner action under a separate authorization. The read-only
preflight that established the target class and the Owner handoff was delivered
as external evidence rather than as a repository document, so it is not linked
from here. What it establishes, and all this contract relies on, is that the
target must be a **dedicated bucket in a different physical fault domain** (not a
second partition, a second internal SSD, or a same-host USB device).

This contract makes no claim about R2 credential scoping that has not been
freshly checked against current provider documentation, and no part of the design
depends on such a claim. In particular it does **not** claim that "R2 cannot
prefix-scope credentials" — that statement is false of temporary credentials, and
a design that rested on it would be resting on a falsehood. What current official
Cloudflare documentation supports, as of 2026-09-14, is the three-layer model
below. It is recorded as the provider's current documented capability, not as a
property this repository proves: the repository cannot verify any of it offline,
and none of it is asserted by a test here.

```text
CREDENTIAL_SCOPE_LAYER_1=LONG_LIVED_API_TOKEN
  BUCKET_LEVEL_SCOPING=DOCUMENTED      ("you can scope your token to a set of buckets")
  OBJECT_OR_PREFIX_SCOPING=NOT_DOCUMENTED_FOR_THIS_LAYER
  PERMISSIONS=Admin Read & Write | Admin Read only | Object Read & Write | Object Read only
  WRITE_ONLY_PERMISSION_DOCUMENTED=NO
  DELETE_LACKING_PERMISSION_DOCUMENTED=NO

CREDENTIAL_SCOPE_LAYER_2=TEMPORARY_CREDENTIAL
  BUCKET_BINDING=EXACTLY_ONE
  PREFIX_SCOPING=DOCUMENTED            ("restrict the credential further to specific paths within the bucket")
  OBJECT_KEY_SCOPING=DOCUMENTED        (exact object keys, alongside prefixes)
  EXCEEDS_PARENT_TOKEN=NO

CREDENTIAL_SCOPE_LAYER_3=ACTION_LEVEL_SCOPE
  EXPLICIT_ACTION_LIST=DOCUMENTED
  ACTIONS_AVAILABLE=PutObject, GetObject, HeadObject, ListObjectsV2, (also) DeleteObject, DeleteObjects
  DELETE_EXCLUDABLE_BY_CHOICE=YES      (exclusion is an issuance choice, not a provider inability)
  ISSUANCE_MECHANISM=LOCAL_SIGNING_ONLY ("`actions` is currently supported via local signing only")
```

Two consequences are load-bearing. The first is that the **shape** of a
credential does not determine its **authority**: a long-lived API token and a
temporary credential both arrive as an access key id, a secret access key and an
optional session token, and nothing in those bytes says which bucket permissions
the credential carries. The transport therefore reports the credential's class
(`session_token_present`) and never its authority, because authority is an
issuance-time property it cannot observe. The second is that
`DELETE_EXCLUDABLE_BY_CHOICE=YES` describes what is *expressible*, not what has
been *expressed*: whether a given target's credential excludes
`DeleteObject`/`DeleteObjects` is a provisioning fact this repository cannot
check, and layer 3 depends on **local, client-side signing** with the parent
token's secret access key in a trusted environment — an issuance decision that
belongs to provisioning and is outside this repository.

The tooling instead relies on properties it states and tests for itself, all of
which hold for every target regardless of how that target's credentials happen to
be scoped: the transport contract below admits no delete verb, so the writer
needs no delete permission anywhere; the live credential is loaded from an
explicit file and never discovered, so the authority in use is the authority the
operator named; and `BUCKET_LOCK_CONFIGURATION` is out of scope for this mission
outright, so no Cloudflare REST API is called to configure a lock.

### Data-plane and bucket-administration credentials are different classes

```text
DATA_PLANE_CREDENTIAL=object operations only (put, get, head, list)
BUCKET_ADMINISTRATION_CREDENTIAL=create/list/delete buckets, edit bucket configuration, configure locks
RUNTIME_BACKUP_CREDENTIAL_CLASS=DATA_PLANE_REQUIRED
RUNTIME_BACKUP_CREDENTIAL_MUST_NOT_ADMINISTER=YES
CREDENTIAL_CLASS_VERIFIABLE_FROM_BYTES=NO
```

The runtime backup credential **must not** possess bucket-administration
authority. That is a requirement on issuance rather than a property this
repository enforces, and the distinction is exactly why it is written down: the
class is invisible at runtime. `Object Read & Write` is a data-plane permission;
`Admin Read & Write` — which current documentation describes as "create, list,
and delete buckets, edit bucket configuration" — is a bucket-administration
credential, and issuing one for a backup run would hand the backup path the
ability to change the bucket and its lock configuration. The transport refuses
every administration verb unconditionally, so an over-scoped credential grants
nothing *through this tooling*; what it grants *through any other holder of the
same file* is the reason the class is constrained at issuance. Provisioning a
credential of the correct class, and keeping a bucket-administration credential
out of the backup runtime, are operator obligations recorded here, not controls
this repository implements.

### Bucket Lock: a separate defensive layer, and what it can and cannot do

```text
BUCKET_LOCK_CONFIGURATION=OUT_OF_SCOPE_FOR_THIS_MISSION
LOCK_CONFIGURED_BY_THIS_MISSION=NO
INDEFINITE_RETENTION=YES
ADMINISTRATIVELY_REMOVABLE=YES
NORMAL_BACKUP_RUNTIME_CAN_REMOVE_LOCK=NO
BUCKET_LOCK_IS_A_SEPARATE_LAYER=YES
```

Bucket Lock is a **separate defensive layer** from this tooling, and an
Indefinite Bucket Lock is **not** described here as irreversible, because it is
not: current documentation describes removing a rule as a supported operation
(dashboard *Delete*, `wrangler r2 bucket lock remove`, or the put-bucket-lock-
configuration API) and states that changing lock configuration requires an API
token with permission to edit R2 bucket configuration. `INDEFINITE_RETENTION=YES`
means the rule's condition never expires on its own;
`ADMINISTRATIVELY_REMOVABLE=YES` means an administrator can still change it. The
two are not in tension, and conflating them is how a lock gets described as
stronger than it is.

`NORMAL_BACKUP_RUNTIME_CAN_REMOVE_LOCK=NO` is precisely the
`DATA_PLANE_CREDENTIAL` / `BUCKET_ADMINISTRATION_CREDENTIAL` distinction above:
lock configuration is bucket administration, so a data-plane runtime credential
cannot reach it. That is the property the lock layer is worth having — it means a
backup process that is compromised *through this tooling* cannot strip the
retention protecting the generations it writes. It is worth being equally clear
about what the layer is not: this tooling neither configures a lock nor depends
on one, no lock is configured by this mission, and a bucket without a lock is
still a valid target for everything specified here. Configuring a lock is an
Owner provisioning action under a separate authorization, and whether the target
has one is not observable from this repository.

Lock documentation also records that rules are prefix-scoped and that a rule
without a prefix applies to every object in the bucket. That is relevant to
provisioning and to nothing in this tooling's own contract.

## Scope and authority

The four adjudication lines below read `OPEN` / `NOT_ACCEPTED` while this tooling
was being built. Blocker #3 has since been closed and Gate 2 accepted by the
Controller, on evidence bound to main
`e660e1a4152191458dc73f369c776be17ab15633` — recorded in
[`STAGE_D_BLOCKER_3_CLOSEOUT.md`](STAGE_D_BLOCKER_3_CLOSEOUT.md). They are
corrected here because this is a current-state contract; nothing else in this
document changes, and in particular the tooling was not what closed the blocker.

```text
BLOCKER_3_STATUS=CLOSED                       (was OPEN when this contract was written)
GATE_2=ACCEPTED                               (was NOT_ACCEPTED)
GATE_3=NOT_AUTHORIZED
STAGE_D_STARTED=NO

BACKUP_TOOLING_CLASS=OFFLINE_IMPLEMENTATION_ONLY
BACKUP_TOOLING_ENTRYPOINT=scripts/ops/stage_d_backup_snapshot.js (offline, filesystem transport)
RESTORE_TOOLING_ENTRYPOINT=scripts/ops/stage_d_restore_verify.js (offline, filesystem transport)
LIVE_BACKUP_TOOLING_ENTRYPOINT=scripts/ops/stage_d_r2_backup_live.js (live-R2 wiring)
LIVE_RESTORE_TOOLING_ENTRYPOINT=scripts/ops/stage_d_r2_restore_live.js (live-R2 wiring)
LIVE_R2_CLI_WIRING=IMPLEMENTED
LIVE_CLI_PROVEN_MODE=OFFLINE_PREFLIGHT_ONLY
LIVE_CONNECTIVITY_PREFLIGHT=NOT_PERFORMED
LIVE_TARGET_IDENTITY_SOURCE=EXPLICIT_FILE (no default location, no discovery)
LIVE_CREDENTIAL_SOURCE=EXPLICIT_FILE (no default, no profile, no environment, no provider chain)
LIVE_TARGET_CONTACTED=NO
OFFLINE_CLIS_UNCHANGED_NETLESS=YES
BACKUP_INVOCATION_INTEGRATED_INTO_PUBLICATION_PATH=NO
BUCKET_LOCK_CONFIGURATION=OUT_OF_SCOPE_FOR_THIS_MISSION
POLICY_B_STATUS=PROPOSED_NOT_APPROVED
RPO_ZERO_COMMITTED_TRANSACTIONS=NOT_YET_ENFORCED
```

The tooling is **explicit-invocation only**. It is not called from
`atomicPublisher`, `stageDOperations`, the publication path, the scheduler,
controlled initialization, the request cycle or the transaction commit. Nothing
in a live cycle can trigger a backup, and nothing in this tooling can trigger a
cycle.

### Controller scope reconciliation for PR #1911

PR #1911 was built against a Controller authorization enumerating 27 exact
paths. Five further paths were created without prior authority, and three
authorized paths were never created. A read-only reconciliation adjudicated all
five, and the Execution Controller has since supplementally authorized them.

```text
PR1911_SCOPE_RECONCILIATION=CONTROLLER_APPROVED
ORIGINAL_CONTROLLER_AUTHORIZED_PATHS=27
SUPPLEMENTALLY_AUTHORIZED_PATH_COUNT=5
UNUSED_ORIGINAL_AUTHORIZED_PATH_COUNT=3
FINAL_AUTHORIZED_PATH_COUNT=29
UNAUTHORIZED_CHANGED_PATHS=0
BUILDER_ORIGINAL_SCOPE_EXPANSION=UNAUTHORIZED_AT_TIME_OF_CREATION
CONTROLLER_LATER_ADJUDICATION=APPROVED
OTHER_UNDISCLOSED_SCOPE_EXPANSION=NO
MANDATORY_TEST_MATRIX=40_COVERED_0_PARTIAL_0_NOT_FOUND
```

The five supplementally authorized paths are
`tests/helpers/backup_authority_fixture.js`, `tests/helpers/network_tripwire.js`,
`tests/unit/market_evidence/backup/backup_cli.test.js`,
`tests/unit/market_evidence/backup/no_production_defaults.test.js` and
`tests/unit/market_evidence/backup/transport_contract.test.js`. All five are
test-support or test-only and none is reachable from shipped code. The tripwire
is required by this contract's own offline proof; the CLI and absence-sweep
suites cover the operator surface and the whole-tree properties that a
per-module test layout has no home for; the fixture builds synthetic authorities
through the real pipeline, because production must not be copied.

This authorization is effective for the PR #1911 workstream only and is **not**
precedent. It corrects an original authorization that under-specified this
contract's own test plan; it does not license a future Builder to add paths
without prior Controller authorization, and it changes no exclusion.

The three unused authorized paths are
`tests/unit/market_evidence/backup/local_transport.test.js`,
`tests/unit/market_evidence/backup/r2_transport.test.js` and
`tests/unit/market_evidence/backup/end_to_end_offline_restore.test.js`, recorded
as `UNUSED_AUTHORIZED` with `UNUSED_ORIGINAL_PATHS_ARE_COVERAGE_GAPS=NO`. Their
responsibilities were reorganized into the final layout — the two transport
suites into `transport_contract.test.js`, and the end-to-end restore obligation
into `backup_cli.test.js`, where it is exercised through the real operator
surface as child processes rather than through library calls. They are not
required to be created for filename compliance, and no duplicate test file
exists to satisfy a name.

The historical deviation is recorded rather than rewritten: the five paths were
unauthorized when they were created, and the Controller's approval is a later
adjudication. Nothing in this section accepts or merges PR #1911, and nothing in
it closes Blocker #3.

## RPO/RTO policy — historical proposal state and current approved state

Two distinct things are recorded below, and reading either as the other is the
error this section exists to prevent: the proposal state this contract was
written under (`HISTORICAL_PROPOSAL_STATE`), and the objectives the Owner has
since approved (`CURRENT_OWNER_APPROVED_STATE`).

### HISTORICAL_PROPOSAL_STATE

Two candidate policies were put to the Controller. **Proposal B** — a snapshot
on every canonical commit, giving `RPO=0` for committed transactions — was the
recommended one and was recorded as `PROPOSED`, never as the governing policy.
Proposal A (`RPO <= 24h`) was the fallback.

`POLICY_B_STATUS=PROPOSED_NOT_APPROVED` still means exactly what it says, and
the approval recorded below does not change it: the tooling does not assume
per-commit invocation, no caller is wired to invoke it per commit, and
`RPO_ZERO_COMMITTED_TRANSACTIONS=NOT_YET_ENFORCED`. Adoption of Proposal B would
still require the invocation point *and* the availability argument that `RPO=0`
requires; neither exists.

### CURRENT_OWNER_APPROVED_STATE

The Owner has since approved the recovery objectives. They are recorded
canonically in
[`STAGE_D_OWNER_DATA_PROTECTION_AND_CREDENTIAL_POLICY.md`](STAGE_D_OWNER_DATA_PROTECTION_AND_CREDENTIAL_POLICY.md)
and are restated here only so that this current-state contract stops describing
them otherwise:

```text
RPO_APPROVED=24_HOURS
RTO_APPROVED=24_HOURS
POLICY_B_STATUS=PROPOSED_NOT_APPROVED
RPO_ZERO_COMMITTED_TRANSACTIONS=NOT_YET_ENFORCED
```

`RPO=24_HOURS` is therefore the approved recovery-point objective, not a
fallback awaiting adoption, and `RTO=24_HOURS` is the approved recovery-time
objective. Both are objectives and not measurements: no recovery drill has been
run against either, and this contract claims neither has been demonstrated.

The approval is bounded to those objectives. It adopts no proposed policy, and
it imposes no per-commit invocation, no continuous replication, no stronger
durability guarantee and no additional backup obligation — Proposal B is
exactly as unapproved after the approval as it was before it.

## The snapshot contract

A **snapshot generation** is one immutable set of objects that captures the
governed authority at one identity. Its shape is fixed:

```text
<snapshot_id>/payload/<logical_path>   one object per governed input, byte-identical
<snapshot_id>/MANIFEST.json            the authoritative description, canonical JSON
<snapshot_id>/COMPLETE                 the completeness marker, written LAST
```

`snapshot_id` matches `^snap_\d{8}T\d{9}Z_[a-f0-9]{16}$`: millisecond wall
clock plus 64 bits of entropy. Two attempts in the same millisecond stay
distinguishable, and the generation id is never the transaction head — the head
is an attribute of the snapshot, recorded inside the manifest, not its name.

### Governed input set

Exactly these categories, and no others:

| Category | Source | Required |
| --- | --- | --- |
| `transaction_package` | `<authority_root>/committed/tx_*/**` | yes |
| `store` | `<authority_root>/STORE.json` | yes |
| `allocation_authority` | the explicit allocation artifact path | yes |
| `request_accounting_epoch` | `<ledger_root>/REQUEST_ACCOUNTING_EPOCH.json` | yes |
| `request_accounting_entry` | `<ledger_root>/entries/\d{12}\.json` | when present |
| `run_state` | each explicitly named run-state input | only when named |
| `quota_config` | the explicit non-secret quota configuration path | yes |

There is **no directory walk** that collects "whatever is there". Every category
is named, and a missing required category fails the snapshot. Two exclusions are
absolute:

- **`.staging` is never snapshotted.** Staging is mutable by construction; its
  presence under the authority root is tolerated but it is never enumerated,
  never copied and never named in a manifest. Staging is excluded from the
  *snapshot*, and — separately — the live staging directory remains the
  publisher's; this tooling neither reads it nor cleans it.
- **Secrets are never snapshotted.** A configured path whose basename looks like
  a credential (`.env`, `*credential*`, `*secret*`, `*token*`, `*.pem`,
  `*.key`, `id_*`, `.npmrc`, `.netrc`, `*password*`) is refused rather than
  silently skipped, because silently skipping a misconfiguration hides it. The
  manifest carries `secrets_included: false` as a positive assertion, and
  `validateSnapshotManifest` refuses a manifest that claims otherwise.

### Required directories

A category list describes files. A directory that holds no files therefore
leaves no trace in it, and the governed layout has exactly one such directory
that is required rather than incidental: `<ledger_root>/entries`, which the
canonical ledger layout requires to exist and the canonical reader refuses a
ledger root without — **whether or not the ledger has recorded anything**.

The enumerated input set therefore carries `required_directories` alongside
`entries`: the directories the restored tree must contain even though no
artifact occupies them. It is enumerated from the same walk that produces the
files, not inferred from them, and it is sorted so the manifest's canonical bytes
do not depend on the order the enumeration happened to produce.

| Required when | Directory |
| --- | --- |
| always | `<authority_root>/committed` |
| per committed package | `<authority_root>/committed/tx_*` |
| the request ledger is present | `<ledger_root>/entries` — recorded even when empty |
| run-state inputs are named | `run-state` |

A required directory may **contain** artifacts, and may not **be** one. Every
ancestor of a required directory is checked against the artifact list, not just
the whole path, because the conflict is the same one at every level: an artifact
occupying `run-state` makes `run-state/<name>` just as uncreatable as an artifact
occupying `run-state/<name>` itself. Paths are otherwise held to the same rule as
artifact logical paths — no absolute path, no empty/`.`/`..` segment, no
`.staging` — and the restore refuses at creation time as well, so a directory that
escapes the destination root is refused by the writer, by validation and by the
restore. A required directory that merely shares a name prefix with an artifact
(`transactions/committed` beside `transactions/committed.json`) is not a conflict.

### Manifest

Canonical JSON (`canonicalJson`), so the manifest hash is a function of content
alone and not of key order or whitespace. It binds:

- the schema version `stage-d-independent-backup-snapshot/v1` and the exact
  `snapshot_id`;
- `source_before` and `source_after` — the full identity tuple captured before
  and after the byte copy, with `source_identity_equal: true` required and
  `source_before == source_after` enforced by validation;
- a `source` summary (head transaction id and content hash, head sequence, head
  knowledge time, state hash, decision/observation/registry/capture counts, the
  allocation authority content hash, the store hash, and the governed input-set
  digest);
- the request-accounting epoch identity and its terminal hash, carrying
  `historical_pre_epoch_request_total` and `historical_pre_epoch_exact_total`
  verbatim from the epoch — including `AT_LEAST_2_CONFIRMED` and `UNKNOWN`,
  which are **not reinterpreted** here;
- every artifact: logical path, category, object key, size, SHA-256;
- `required_directories` — the directories no artifact occupies, sorted, and
  bound by the manifest hash like every other field. The field is **optional and
  its absence carries meaning**: `Object.hasOwn` separates "absent" from
  "present and empty", and only the absent case may have its requirement
  re-derived (see *Old-generation compatibility*);
- `artifact_count` and `total_bytes`, both re-derived from the artifact list at
  validation time.

### Completeness marker

`COMPLETE` is a separate object, written **last**, binding the manifest's object
key, the manifest's SHA-256, the artifact count, the total bytes, the source
head, the source state hash and the completion time.

Splitting the marker from the manifest is what makes a partial generation
detectable. A crash between the payload and the marker leaves objects that no
verifier will accept, and because nothing in this system can delete, the partial
generation stays as visible evidence rather than being quietly cleaned up.
"Accepted" is defined by the marker, never by the presence of a manifest.

### Write sequence

```text
1. assert the transport contract
2. choose a generation id and prove the generation is absent
3. capture the source identity BEFORE
4. copy every governed input with a create-only write
5. read every written object back, re-hash it and re-head it
6. capture the source identity AFTER and require BEFORE == AFTER
7. re-enumerate the governed input set, re-read every input and require the
   content digest to be unchanged
8. write the manifest, binding both identities
9. write the completeness marker LAST, binding the manifest hash
```

Step 7 re-enumerates the governed input set, re-reads every input and requires
the content digest to be unchanged. There is deliberately **no second comparison
of the `required_directories` set**, and the reason is worth stating because the
comparison is the obvious thing to write: no reachable tree can fail it.

- A `committed/tx_*` package directory that *appears* empty is refused by the
  identity capture at step 6, because a package's file set is part of the
  authority contract and the canonical reader rejects a package that holds none.
- The same directory *disappearing* takes its files with it, so the digest at
  step 7 reports it first.
- The two directories every generation requires — `transactions/committed` and
  `request-accounting/entries` — are required *because the walk found them*, so
  their absence surfaces as an `ENOENT` from the re-enumeration rather than as a
  difference between two sets.
- A run-state input that changes kind changes the file set with it.

A check that no reachable tree can fail reads like a safety property without
being one, and shipping it invites the reader to trust a line that never runs.
The writer states the guarantee in a comment at that point in the sequence
instead, where it can be argued about, and the property that does hold is tested
where it is observable: a tree whose layout moves during the copy is never
sealed, with a positive control proving the same tree seals when the layout is
left alone.

**Documented deviation.** The mission's written sequence places the manifest (8)
before the AFTER identity capture (6). Those two requirements cannot both hold:
the manifest schema must bind the source-after identity, so the manifest cannot
be sealed before that identity exists. This implementation resolves the conflict
in favour of the schema and of the last-written completeness marker, which both
readings agree on. The deviation is reported to the Controller rather than
papered over, and it is stated in the writer's own header comment.

If the source moves during the copy — either the identity tuple changes or the
governed input set changes — the generation is abandoned **before** the manifest
and marker, `SourceChangedDuringSnapshotError` is raised, and the partial
payload is left in place rather than deleted. An accepted generation is a
permanent claim about one authority identity; a claim that became false while it
was being written must never be sealed.

## The transport contract

Five capabilities, no more:

```text
REQUIRED = putObjectCreateOnly | getObject | headObject | listObjects | describe
FORBIDDEN = deleteObject, deleteObjects, deletePrefix, deleteGeneration,
            emptyBucket, removeObject, overwriteAcceptedSnapshot,
            putObjectOverwrite, createBucket, deleteBucket, configureBucket,
            putBucketLock, putBucketLifecycle, putBucketPolicy
```

Presence of any forbidden verb is a contract violation rather than a warning: a
transport that can delete cannot carry an immutable backup generation, because a
bug in the writer would then be able to destroy the evidence the writer exists to
protect. `describe()` must declare `create_only: true` and
`delete_exposed: false`, and the writer and verifier both assert the whole
contract before touching a byte.

**A transport speaks logical keys on both sides of its boundary.** A configured
prefix is an addressing detail of the off-host target, not part of a generation:
the manifest records logical keys, the verifier compares the listed set against
them for exact equality, and `putObjectCreateOnly`, `getObject` and `headObject`
all map between the two. `listObjects` is the one method where the provider
hands back a physical key, so it is the one place the prefix could leak — and a
leak is not cosmetic: the exact set comparison would report every object as
unexpected *and* every expected object as missing, leaving a prefixed transport
unable to verify a generation it had just written. The prefix is stripped on the
way out, the provider is addressed in physical keys on the way in, and a test
pins both halves.

**Create-only is atomic, and it is never emulated.** The filesystem transport
uses `open(..., O_CREAT|O_EXCL)`, where the create and the existence check are
one syscall. The S3-compatible transport uses `If-None-Match: *`, which
Cloudflare R2 documents as implemented for `PutObject`, so the condition and the
write are one server-side operation. A `HEAD`-then-`PUT` emulation is **never**
used: that pattern is race-prone and would let two writers both believe they
created the same generation.

## The R2 transport — signing is the provider's job

`createR2Transport` delegates signing entirely to `@aws-sdk/client-s3`. No
Signature V4 logic is written in this repository: canonical-request
construction, signing-key derivation and credential signing are all
provider-supplied. That is an architecture decision, not an omission, and a
test asserts that no `AWS4-HMAC-SHA256`, `StringToSign`, `X-Amz-`,
`credentialScope` or HMAC primitive appears anywhere under the backup sources.

`@aws-sdk/client-s3` is the only new runtime dependency this work adds. It is an
approved exception to the zero-new-dependency rule for exactly one reason: an
otherwise correct hand-written signer is a far larger and less reviewable
surface than a mature SDK. It is linked on demand at both levels — the barrel
does **not** re-export it eagerly, and the transport module links it when a
transport is constructed rather than when the module is required. `require` is
what links a dependency, so a barrel that deferred while the module it defers to
linked eagerly would have moved the boundary without holding it: requiring
either one must leave the network client unlinked, and only constructing a
transport may link it.

That is what the offline CLIs rely on — they reach the backup tooling through
the barrel and never construct an R2 transport, so they never link the client.
The one test that links it is the one that constructs an R2 transport. Both
halves are asserted by test in fresh child processes, and the second half is
asserted because a probe that observed nothing would make the first half pass
for the wrong reason.

**A note on the name.** The module, `createR2Transport` and the reported
`kind: 'r2-s3'` / `version: 'stage-d-r2-s3-transport/v1'` still name R2, while the
transport also serves the self-hosted S3 target. The name is a label, not a
claim: what the transport speaks is the S3 API, and `describe()` already reports
the `endpoint`, `bucket` and `region` that identify which provider actually
served the run, so the evidence names the target twice over. Renaming would touch
the module path, the lazy-surface contract in the barrel, the identity assertions
six test files make against it and the version string already recorded in
existing evidence — for a change no consumer would observe. It is therefore
recorded as `FU-4 NONBLOCKING_COSMETIC_FOLLOWUP` and deliberately left open
rather than turned into a broad rename.

### Credential model

```text
CREDENTIAL_SOURCE=INJECTED_EXPLICIT
ENVIRONMENT_FALLBACK=NO
PROFILE_FALLBACK=NO
INSTANCE_METADATA_FALLBACK=NO
DEFAULT_PROVIDER_CHAIN=NO
```

Credentials are injected by the caller or the transport refuses to construct.
There is no environment fallback, no `~/.aws` fallback, no instance-metadata
fallback and no default provider chain: the SDK ships a provider chain and this
transport never lets it run, because an executor that silently picks up ambient
credentials cannot be reasoned about. A test asserts that the transport
still refuses when `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` and
`AWS_PROFILE` are all set in the environment.

That refusal is unconditional, and it holds on **every** construction path. The
transport builds its own client, always, from the credentials it has just
validated, and passes them explicitly, so there is nothing left for the SDK's
provider chain to discover. The seam a test uses is the SDK *surface* — the
five classes, supplied as `sdk` — never a client instance: a caller-supplied
client could be backed by the default provider chain, and validating the
`credentials` argument would prove nothing about it, leaving the transport
sending through a credential source it cannot name while reporting
`credential_source: INJECTED_EXPLICIT`. A refusal that only applies on one
branch is a conditional guarantee, which is not a guarantee.

A client *instance* is therefore refused outright rather than ignored, because a
caller whose client was silently dropped would believe it was in use. Because
the transport now constructs the client itself, the invariant is something a
test can check rather than something the document asserts: one test reads the
configuration the transport handed its client and requires it to be exactly
`endpoint`, `region`, `forcePathStyle` and the validated `credentials` — nothing
that could resolve a credential from anywhere else. Another asserts that
constructing the transport without credentials is refused even when
`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` and `AWS_PROFILE` are all set in
the environment, and that an SDK surface missing any of the five verbs is
refused at construction rather than at first use.

Errors are rebuilt from provider-supplied identifiers only (error name and HTTP
status). Nothing from the client configuration is interpolated, so a secret
cannot reach a message, a stack trace assembled here, or a report — asserted by
a test that fails a call with a secret embedded in the provider's message.
`describe()` excludes credentials entirely and is safe to serialize.

The credential carries three fields, not two. `accessKeyId` and
`secretAccessKey` are required and `sessionToken` is optional, because a
temporary credential is exactly that shape; the transport passes a session token
through to the client when one is present. `describe()` reports
`session_token_present` — the credential's **class**, never its value — so a run
can record that it used a temporary credential without recording anything that
could be used. That field is the only thing about a credential that reaches a
report, and it is a boolean.

### The credential object the SDK is handed

The transport freezes its own record of the credential, and hands the SDK a
**mutable copy** of it. The pinned SDK requires that copy.

`@aws-sdk/core`'s `resolveAwsSdkSigV4Config` wraps the caller's credentials in an
async provider and, on first resolution, annotates *that same object* in place
with `$source` and a `CREDENTIALS_CODE` feature flag. There is no copy on that
path and `const attributedCreds = creds` is literally the caller's object, so a
frozen credential fails at the first signed request with

```text
TypeError: Cannot set properties of undefined (setting 'CREDENTIALS_CODE')
```

— and it fails *late*. The mutation is deferred to provider resolution, which
happens while signing rather than at construction, so code that constructs an
`S3Client` and stops there reports success for both shapes. That is how an
incompatible freeze reached `main` and required a disclosed runtime shim for the
only live backup run so far.

The repair keeps the freeze where it belongs and removes it where it does not:
the transport's own `resolvedCredentials` record stays frozen — it is the
transport's state and nothing should be able to mutate it — and the object
passed to `S3Client` is a fresh, mutable copy built field by field from it. The
caller's object is never passed through, so a mutation performed by the SDK
cannot reach the caller's credential either; the SDK annotates its own copy and
the caller's input is untouched.

Nothing else about credential handling changes. The copy is still built from the
validated credential and nothing else, no provider chain becomes reachable, the
session token still reaches the client and still does not reach `describe()`, and
nothing is written back to disk.

A test drives the **real pinned SDK** rather than a stub — a stub the transport
itself supplies cannot exhibit a behaviour of the library it stands in for — and
resolves the provider the transport built, because resolving it is the step that
failed. Its positive control is the same call on a mutable credential, which
still fails on the pinned version: if a future SDK stops mutating, the control
breaks loudly instead of the test quietly passing for the wrong reason. A second
arm proves the caller's frozen input is still frozen and unannotated afterwards,
and a third proves two transports never share the object the SDK sees.

### How the live path obtains a target and a credential

```text
TARGET_IDENTITY_SOURCE=EXPLICIT_FILE
TARGET_IDENTITY_DEFAULT_LOCATION=NONE
TARGET_IDENTITY_DISCOVERY=NO
CREDENTIAL_SOURCE=EXPLICIT_FILE
CREDENTIAL_DEFAULT_LOCATION=NONE
CREDENTIAL_FILE_MODE=0600_OR_STRICTER
CREDENTIAL_FILE_OWNER_MUST_BE_ONLY_READER=YES
IMPLICIT_CREDENTIAL_DISCOVERY=NO
SECRET_VALUE_IN_ARGV=NO
SECRET_VALUE_IN_LOGS=NO
SECRET_VALUE_IN_EVIDENCE=NO
```

Two loaders, two files, two jobs. `liveTargetIdentity.js` reads the **non-secret**
addressing half — provider, endpoint, bucket, region, prefix and three bounded
labels — from a closed nine-field schema, so a credential pasted into it is
refused as an undefined field rather than accepted and ignored.
`liveCredentialLoader.js` reads the secret half. Neither has a default location,
and neither reads the environment at all: not `AWS_ACCESS_KEY_ID`, not
`AWS_PROFILE`, not `AWS_SHARED_CREDENTIALS_FILE`, not `~/.aws`, not instance
metadata, and not the SDK's provider chain. Both properties are asserted
structurally — the module sources are checked for `process.env`, `homedir` and an
SDK require — because "this loader ignores the environment" is a claim about the
code rather than about a list of variables someone thought of.

### Two provider classes, and the endpoint is bound to the one that names it

The identity's `provider` field is a closed enum with two members, each an
adjudicated target class rather than a configuration value: `cloudflare-r2` and
`self-hosted-s3`. Adding a third is a design decision that requires a mission,
not an operator who needs one more endpoint.

Region is validated **per provider**, not against a flat union. R2's S3 API takes
`auto`; the self-hosted class takes `us-east-1`. The distinction is load-bearing
because the region reaches the signature while the endpoint decides where the
request goes, so a union would admit the two cross pairs — `cloudflare-r2` with
`us-east-1`, and `self-hosted-s3` with `auto` — that name no real target. With one
provider a flat list could not express that mistake; with two it can, so the
check reads the pair.

The endpoint is bound to the provider that names it. For `cloudflare-r2` the host
must be an account subdomain **under** `r2.cloudflarestorage.com`: a suffix test
rather than a substring test, so a host that merely contains that domain and ends
somewhere else is refused, and the bare registrable domain is refused because it
names no account. For `self-hosted-s3` the endpoint must be a **literal IPv4
address in a range that is not globally routable** (`10/8`, `100.64/10`,
`169.254/16`, `172.16/12`, `192.168/16`), written as the canonical dotted quad.

Both self-hosted rules exist to keep this class from becoming a way around the
constraints the other class is subject to:

- **Loopback is refused**, with its own message, because a loopback endpoint is
  the current machine: a "backup" written to one shares the exact failure domain
  it exists to survive.
- **A publicly routable address is refused**, so adding this class cannot turn
  the live backup path into a way to ship production bytes to an arbitrary public
  destination.
- **A DNS name is refused** even when it looks private, because resolving one is
  a network call this loader does not make, and a name it does not resolve is a
  destination it has not checked.
- **A non-canonical spelling is refused.** This is not pedantry. The URL parser
  applies the WHATWG legacy IPv4 rules to the host, so `192.168.011.070` is read
  with **octal** octets and becomes `192.168.9.56`, and the short form
  `192.168.11` is read as a 24-bit tail and becomes `192.168.0.11`. Both land
  inside `192.168.0.0/16`, so a range test alone admits them while the transport
  dials a host the identity file does not name. The field must read as the
  address it dials, so the raw spelling is compared against the parsed address
  and a mismatch is refused. The refusal names the rule and states neither the
  spelling nor the address that spelling resolves to, because the no-echo rule
  below holds here too: what names a target in evidence is the
  `target_fingerprint`, and a refusal is a message that reaches a log.

The rule is narrower than "an operator may only use their own host", which is not
something a loader can establish. What it establishes is the network the address
sits in, and that is all it claims.

**Create-only for the self-hosted class rests on the endpoint, not on this
repository's reading of a vendor's documentation.** The `If-None-Match: *`
requirement above is unchanged, and R2's support for it is recorded from
Cloudflare's documentation. For a self-hosted endpoint no vendor statement covers
the operator's own server, so the atomicity of `PutObject` carrying
`If-None-Match: *` must be established for that endpoint by live evidence before a
generation is relied upon: a server that accepted the header and wrote anyway
would let two writers both believe they created the same generation. Neither
class's `PutObject` behaviour is proven by this repository offline.

Fail-closed means every one of these is a refusal rather than a degradation: a
missing or non-string path, a path that is not a regular file, a symbolic link, a
file readable or writable by group or other (0600 or stricter), an empty file, a
file over 64 KiB, a file that changes between being measured and being read,
malformed JSON, a document that is not an object, an undefined field, a missing
required field, and an empty or padded value. There is no partial load and no
fallback to an ambient credential.

**No field value is ever echoed in an error**, in either loader. A field is named,
and only when that name is itself safe to print: `endpont` is a typo worth
reporting, and an access key id used as a JSON object key is not. The parsers'
own messages are replaced rather than forwarded, because `JSON.parse` quotes the
input it choked on and that input is the file. The credential file's **path** is
never reported either — a pointer to secret material is itself worth not
publishing — while the identity file's `target_fingerprint` (16 hex characters
over provider, endpoint, bucket, region and prefix) **is** reported, so evidence
can name which target a run addressed without restating the account-bearing
endpoint. Credential errors are additionally routed through a scrubber that
replaces every credential value with `[REDACTED]` before anything is printed, so
even an un-authored error text cannot carry a secret to a terminal.

A credential file must not live inside the repository or inside a directory whose
name ends in `.artifacts`, and both are refused before the file is opened. The
evidence-directory rule is a **named convention, not a proof**: it recognises the
shape it was written against, and keeping the file outside the repository and
outside any evidence root remains an operator obligation. Parent-directory
symlinks and file ownership are deliberately not checked, for the reasons
recorded in the loaders' own headers.

A precondition failure (`412`, or `409` where a proxy reports it that way) is
classified as `ObjectAlreadyExistsError`. Anything else is a real failure and is
**not** reinterpreted as a benign collision, because swallowing a genuine write
error as "already exists" would lose a generation.

### What this transport refuses to be

- it cannot delete — no delete verb is implemented, and none may be added;
- it cannot administer — bucket creation, bucket locks, lifecycle rules and the
  Cloudflare REST API are all out of scope, and `BUCKET_LOCK_CONFIGURATION` is
  **out of scope for this work**; the tooling never calls a Cloudflare REST API
  to configure a lock;
- it cannot run at import time — constructing the module performs no I/O and no
  network access, and a client is built only when the caller asks for one.

## Verification

`verifySnapshot` is read-only: it never writes, never repairs and never deletes.
A generation that fails verification stays exactly as it is, because a failed
verification is evidence *about* a generation and repairing it in place would
destroy that evidence. Re-running the writer produces a new generation instead.

Verification is anchored on the completeness marker. Failures are collected
rather than thrown, so one report describes everything wrong with a generation
instead of only the first thing:

```text
MISSING_COMPLETENESS_MARKER   the generation was never sealed
INVALID_COMPLETENESS_MARKER   the marker is absent, non-canonical or malformed
IDENTITY_MISMATCH             the marker contradicts the manifest it binds
MISSING_MANIFEST              the marker binds a manifest that does not exist
MANIFEST_HASH_MISMATCH        the manifest is not the bytes the marker sealed
INVALID_MANIFEST              the manifest is absent, non-canonical or malformed
ARTIFACT_KEY_MISMATCH         an artifact is not stored where its logical path implies
ARTIFACT_MISSING              an object the manifest accounts for is absent
ARTIFACT_SIZE_MISMATCH        an artifact's length drifted
ARTIFACT_HASH_MISMATCH        an artifact's content drifted
MISSING_REQUIRED_CATEGORY     the generation does not carry a required category
UNEXPECTED_OBJECT             the generation carries an object no entry accounts for
SOURCE_SUMMARY_MISMATCH       the summary contradicts the identity the manifest captured
```

Because nothing in this system can delete, an extra object under a generation is
either a foreign write or a bug, and either way the generation is not the
generation the manifest claims — so the observed key set must be exactly what
the manifest and marker describe.

## Isolated restore and its proof

A restore is only evidence if it happens somewhere the source cannot reach.
Restoring beside the source would prove nothing, and restoring onto the source
would be a catastrophe. The destination must therefore be:

- supplied explicitly — there is no default restore location;
- **non-existent** — a restore never overwrites, and the command refuses rather
  than merging into an existing tree;
- outside the governed production area, by the same whole-segment match the
  local transport uses;
- outside every source root the caller names, and not containing one — compared
  **physically as well as lexically**, because `path.resolve` never asks the
  filesystem: a destination reached through a symlinked ancestor names none of
  the source roots while every write through it lands inside one, and the
  immediate parent's own `lstat` cannot see it either when the link sits higher
  up. Both views of both sides are compared, so a destination that is disjoint
  from the source in name only is refused;
- free of symbolic-link ancestors, and created with `0700`.

A failed restore leaves the destination **exactly as it was found** — that is,
still non-existent. It is built at a staging path beside the destination and
committed only after every artifact has been written and the proof has come back
`PASS`, so the destination cannot be observed holding unproven content. Building
it at its final path instead would have made every later failure — a missing
object, a hash the manifest does not bind, or a proof that returns `FAIL` —
leave behind a partial tree at a path that had not existed before, and because a
restore refuses a destination that already exists, that tree could never have
been restored into again.

The staging root is therefore removed when the restore fails, and it is the
**only** thing a failed restore removes:

- its name is minted by the invocation that creates it — `.<destination
  basename>.restore-staging-<random>`, the suffix drawn locally and never derived
  from anything the caller supplied — which is what makes "the staging root this
  invocation created" a decidable question rather than a pattern match;
- the cleanup removes the *contents* of that one directory and then the
  directory, naming nothing that is not that path joined with a name
  `readdirSync` returned. There is no traversal to refuse and no denylist to keep
  current, because `readdirSync` cannot return `..`;
- a symbolic link inside the staging tree is **unlinked, never entered**.
  Descending through one would make the cleanup's reach a property of whatever
  the link points at, and the restored tree refuses symbolic-link parents when it
  is written, so a link in there is foreign content — exactly what must not be
  walked into;
- a staging root that is not a plain directory is refused rather than followed,
  and `rmdir` refuses a directory that is not empty, so something arriving
  between the walk and the removal stops the cleanup instead of being deleted;
- the destination is not a special case here, it is simply a different path, and
  nothing outside the staging root is ever named. A preexisting destination is
  never deleted, and neither is anything else already in the parent;
- a cleanup that fails is **recorded on the failure that caused it**, never
  thrown in its place. The restore already failed for a reason the operator
  needs, and replacing that reason with "the tidy-up failed as well" would hide
  the one that matters. The note is appended best-effort; an error that cannot
  carry one is still the error that gets reported.

The **commit itself is create-only**, because that is the point at which "a
restore never overwrites" has to be decided, and a check made earlier cannot
decide it: another process can create the destination in between. The commit
therefore creates the destination with `mkdir`, which creates or fails with
`EEXIST` and can never replace. A plain `rename` is atomic but is not usable
here — POSIX rename onto an existing **empty** directory succeeds, so a
destination that appeared after the freshness check would be silently adopted
and overwritten, which is the one outcome a restore must never produce. The
staged entries are moved in one by one, and any failure moves every one of them
back and removes the directory again: the destination is either absent, or the
complete proven tree. Entries are only ever moved, never deleted, and a
directory that is no longer empty refuses to be removed, so the rollback stops
rather than deletes anything it did not put there.

The report names the destination, not the staging path: the layout fields are
recomputed from the final destination — they are a pure function of the
destination and the manifest — while the bytes, hashes, modes and identity in
the report are the proof's own, carried through unaltered.

The executor then restores every artifact from the generation, byte for byte,
at the production permission contract's modes:

```text
DIRECTORY_MODE=0700
transaction_package=0400   store=0444   allocation_authority=0444
request_accounting_epoch=0400   request_accounting_entry=0400
run_state=0444   quota_config=0444
```

`umask` does not apply to an explicit `chmod`, so the restored mode is exactly
the mode the contract names rather than the process default.

**Required directories are materialized in their own right**, before the content
is written, from the manifest's `required_directories`. A directory that no
artifact occupies is thus produced by the restore rather than as a by-product of
one that does — which is the whole point: `entries/` exists after a restore of a
zero-entry ledger because the manifest said it must, not because something
happened to be written into it. Each path is refused at creation time if it
escapes the destination root, and the proof compares the created set against the
manifest before it asks the canonical readers anything.

### Old-generation compatibility

A generation written before `required_directories` existed is still **admitted,
verified and restored**. The restore re-derives the requirement from the
canonical layout instead: a manifest that carries any `request-accounting`
artifact is a generation whose ledger root must contain `entries`, because that
is what the ledger contract says a ledger root is. The derivation reads no
snapshot id, no timestamp and no machine path, and it is applied **only** when
the field is absent — `Object.hasOwn`, not a truthiness test, so a generation
that genuinely requires no directory stays distinguishable from one that
predates the field.

`required_directories_source` records which of the two the restore used,
`MANIFEST_REQUIRED_DIRECTORIES` or `DERIVED_FROM_CANONICAL_LAYOUT`, so an
operator can see that a restored old generation was reconstructed from the
contract rather than read from the artifact. The report carries
`required_directories` and `restored_directory_count` alongside it. A generation
is never rewritten to add the field: the old generation on the backup target is
read-only for this tooling, which has no delete verb and no update verb at all.

**The proof is performed by the canonical readers.** `proveRestoredRoot` points
`openMarketEvidenceAuthoritySnapshot` and `readRequestLedger` at the restored
root with no other input and compares the result against what the manifest
bound — the head transaction id and content hash, head sequence, state hash, the
four counts, the request-accounting epoch id, entry count and terminal hash, and
the store, allocation and quota hashes. A bespoke checker would prove only that
the checker and the writer agree; the canonical readers prove the restored bytes
are an authority the runtime would accept.

The directory comparison runs **before** either reader is called, and the
canonical readers are not called at all when it fails. This ordering is the
repair, not a detail: a reader pointed at a root missing `entries/` fails with
`ENOENT ... lstat '<fd>/entries'` — or `UNSAFE_PATH` when the path is a file —
naming a descriptor-scoped path the operator never wrote, which is how a missing
directory was reported as a transport-shaped mystery. With the directories
checked first, an incomplete layout is named as an incomplete layout, and the
report's `proof` is `null` while `failures` describes what was actually found.

When `--fresh-process` is requested the same proof is repeated across a process
boundary: a child process imports the canonical readers, is given the restored
paths and nothing else, and inherits **no environment at all** beyond `PATH`, so
a result cannot come from an ambient credential, an ambient configuration or a
production path the parent happened to have in scope. A child that cannot load
the restored root fails the whole proof even though the in-process half
succeeded.

The report carries `production_fallback_used: false` and
`production_paths_read: []` as positive assertions. If a required governed
artifact cannot be restored from the generation, the restore fails; it never
substitutes a file from somewhere else.

## No production defaults, anywhere

Every root is explicit. There is no default authority root, no default ledger
root, no default transport root and no default restore location. An operator who
forgets an argument gets an error, never a backup of whatever happened to be in
the default location.

```text
AUTHORITY_ROOT_DEFAULT=NONE
LEDGER_ROOT_DEFAULT=NONE
TRANSPORT_ROOT_DEFAULT=NONE
RESTORE_DESTINATION_DEFAULT=NONE
PRODUCTION_PATH_FALLBACK=NONE
```

The production area is named in exactly one place in the whole implementation —
the `PRODUCTION_MARKERS` denylist in the local transport — and it is named there
so it can be **refused**. The match is on whole path segments, not on a
substring, so `.../live-2` is not condemned by a proximity to `.../live`. A test
asserts that the production area is named exactly once in executable code, that
the single mention is inside that denylist, and that no ops CLI names it at all.

The refusal is decided by **where a path lands**, not only by what it spells. The
lexical match is necessary but not sufficient, because `path.resolve` never asks
the filesystem: a path reached through a symlinked ancestor spells the governed
area nowhere, and its final component is an ordinary directory, while every read
and write through it lands inside. A guard built on the lexical match alone would
accept such a root and then write a snapshot into the authority it exists to
protect — which is precisely the accident, not an exotic attack, the guard is
there to prevent. Every accepted root, input and destination is therefore also
resolved through its longest existing prefix and the whole-segment match is run
against that real location; the not-yet-existing tail is appended unchanged, so a
destination that is safe to create is still accepted, and one that would land in
the governed area is refused before anything is created. Both arms are asserted,
and each site that accepts a path has a test that fails if the second arm is
removed.

This is a check on **acceptance**, and it is honest about that. A root is
resolved when it is accepted; the transport refuses symbolic links anywhere
inside its root on every access, but the ancestor chain above the root is not
re-resolved per operation. Moving a symlink into that chain *after* a transport
has been constructed is outside what this guard covers — the tooling is
explicit-invocation, single-process and names its roots once, so the window this
leaves is one an operator would have to open deliberately against themselves,
and closing it would mean re-resolving the caller's own parent directories on
every write, which no check of this kind can do meaningfully while the same
actor can also write the files directly.

**Explicit is not the same as safe**, so the refusal is applied on the read side
as well as the write side:

```text
SNAPSHOT_AUTHORITY_ROOT_GOVERNED_PRODUCTION=REFUSED
SNAPSHOT_LEDGER_ROOT_GOVERNED_PRODUCTION=REFUSED
SNAPSHOT_ALLOCATION_ARTIFACT_GOVERNED_PRODUCTION=REFUSED
SNAPSHOT_QUOTA_CONFIG_GOVERNED_PRODUCTION=REFUSED
SNAPSHOT_RUN_STATE_INPUT_GOVERNED_PRODUCTION=REFUSED
TRANSPORT_ROOT_GOVERNED_PRODUCTION=REFUSED
RESTORE_DESTINATION_GOVERNED_PRODUCTION=REFUSED
```

Every input root is checked, not only the authority root, because a guard on one
argument would leave the same hole reachable through the ledger, the allocation
artifact, the quota configuration or run state. This is deliberately fail-closed:
reading the governed authority in order to snapshot it is a decision a future,
explicitly authorized mission makes by changing this refusal, not something a
command-line argument can turn on. Until then a snapshot cannot be pointed at
production even by an operator who means to.

Neither offline CLI accepts an endpoint, bucket, region, credential or profile
flag. Those flags are **rejected rather than ignored**, in both spellings:
`--endpoint https://…` and `--endpoint=…` mean the same thing to whoever types
them, so a check that matched only the first would silently ignore the second and
let an operator believe the command was aimed at R2 when it was not. The rejected
value is never echoed back — a value passed to one of these flags may be a
credential, so echoing it would turn a refusal into a leak. A test drives every
flag in both spellings at both offline CLIs and asserts each is refused by name,
with the value appearing in neither stdout nor stderr.

### The live entrypoints are separate files

```text
LIVE_BACKUP_ENTRYPOINT=scripts/ops/stage_d_r2_backup_live.js
LIVE_RESTORE_ENTRYPOINT=scripts/ops/stage_d_r2_restore_live.js
OFFLINE_CLIS_MODIFIED=NO
LIVE_WIRING_ADDED_AS_A_FLAG_ON_THE_OFFLINE_CLIS=NO
OFFLINE_CLIS_REFUSE_LIVE_FLAGS=YES
```

The live path is two new entrypoints, not two new flags. "The offline CLI cannot
address a remote target" is a property that was proven, reviewed and merged in
PR #1911; teaching that CLI an endpoint flag would destroy the property while
leaving the file looking unchanged. The offline CLIs are therefore **byte-
unchanged** by the live wiring, and the live flag names
(`--target-identity-file`, `--credential-file`, `--preflight-only`) are refused
by them for the same reason any other unimplemented flag is: their allowlist
admits only what they implement, so a new flag is refused without anyone having
to remember to add it to a denylist. A test asserts both halves — that each
offline CLI still refuses the live flags, and that neither CLI's source contains
a reference to the live loaders, the R2 transport or the SDK.

The live CLIs carry the same refusal architecture and additionally reject
**inline secrets**: `--access-key-id`, `--secret-access-key`, `--session-token`,
`--access-key`, `--secret-key`, `--token`, `--api-token`, `--credentials`,
`--credential`, `--profile`, `--aws-access-key-id`, `--aws-secret-access-key`,
`--aws-session-token`, `--aws-profile`, `--endpoint`, `--endpoint-url`,
`--bucket`, `--region`, `--prefix`, `--r2` and `--s3` are all refused by name in
both spellings, with the value never echoed. A credential reaches the live path
through a file and nothing else, so `SECRET_VALUE_IN_ARGV=NO` is a property of
the accepted surface rather than a convention about how the command is typed.

### The live CLIs have an offline preflight, and it is not a connectivity probe

```text
PREFLIGHT_CLASS=OFFLINE_PREFLIGHT
LIVE_CONNECTIVITY_PREFLIGHT=LIVE_CONNECTIVITY_PREFLIGHT (a different class, not implemented)
OFFLINE_PREFLIGHT_NETWORK_CALLS=0
OFFLINE_PREFLIGHT_PROVES=the wiring loads, validates and constructs
OFFLINE_PREFLIGHT_DOES_NOT_PROVE=reachability, credentials, permissions or the target's existence
```

`--preflight-only` loads the identity, loads the credential, constructs the real
R2 transport and asserts the transport contract, then reports and stops. It makes
**zero** network calls, and it says so in its own output rather than leaving the
operator to infer it: the report carries `preflight_class: 'OFFLINE_PREFLIGHT'`,
`live_connectivity_preflight: 'NOT_PERFORMED'` and `network_calls_made: 0`. The
two classes are named separately because they answer different questions — an
offline preflight proves that the wiring, the files and the validation are
correct and proves nothing about whether the target exists, whether the
credential is accepted or whether the permissions are sufficient. A probe that
wrote a conditional-create object and read it back would be the connectivity
class, is the thing
`preflight-probe/conditional-write/v1/PROBE.json` names, and is **not** part of
this work: no such object was written, and the key is recorded here only so that
the probe this repository does not perform has a defined namespace.

The offline preflight is exercised under the network tripwire in a child
process, so "zero network calls" is asserted by a seal rather than by reading the
code. Constructing the transport is what links `@aws-sdk/client-s3`; the client
constructor performs no I/O, so this is the one place where a real SDK object
exists without a request being possible — and the tripwire is what makes that
statement checkable.

That named list is a denylist, and a denylist can only refuse the names someone
thought to write down. The names that matter most here are exactly the ones that
keep being invented, and the near-misses slip past it: `--r2-access-key-id=…`
contains no `--r2=` (the character after `--r2` is `-`, not `=`), and
`--storage-endpoint=…` contains no `--endpoint`. Both were parsed by nothing,
ignored, and the command ran to completion and exited `0` while carrying an
access key or an API token in its own argv. Each CLI therefore **accepts only
the flags it implements** — the live CLIs by the same rule, which is why the
offline CLIs refuse the live flags without a second denylist to maintain: every
argument must be one of that CLI's own flags
(beyond the named refusals above), a flag it does not implement is refused by
name, a value never begins with `--` so a flag in a value position is reported
as the missing value it is rather than consumed, and a bare positional argument
is refused without being echoed — a stray token is as likely to be a pasted
secret as a mistyped path. The `--flag=value` form is refused explicitly for
implemented flags rather than silently failing as a missing value, since these
CLIs read values from the following argument.

The distinction the contract draws is between **refusing** an argument and
**ignoring** it. Ignoring is the dangerous outcome: the operator believes the
command went somewhere it did not, and a credential that was silently swallowed
is one nobody knows is compromised. Refusing is always safe, so where the two
are in tension the tooling refuses.

## Offline proof

Every test in this work runs with no network. A tripwire helper replaces
`http.request`, `http.get`, `https.request`, `https.get`, `net.connect`,
`net.createConnection`, `net.Socket.prototype.connect`, `tls.connect`,
`dns.lookup`, `dns.resolve`, `dns.promises.lookup`, `dns.promises.resolve`,
`http2.connect`, `globalThis.fetch` and `globalThis.WebSocket` with throwers,
and asserts zero attempts across a full write, verify and restore. A test that
silently reached a provider endpoint would pass for the wrong reason and would
consume someone's quota while doing it.

The seal is enumerated rather than sampled, and it was extended when the live
path was wired: `http2.connect` because an SDK transport may negotiate HTTP/2
instead of the `https.request` the earlier seal covered,
`dns.promises.lookup` and `dns.promises.resolve` because the promise API is a
separate function object from the callback one, and `globalThis.WebSocket`
because it is a network client that reaches no `http`/`net` function at all. The
newly sealed entry points are exercised by the existing driver that walks the
seal list generically, so a seal that was added without being installed fails a
test rather than sitting in a list.

The seal covers every backup test file, not only the test in each that was
written with the tripwire in mind — an outbound attempt is the same breach
wherever in the file it comes from, and a file that sealed one test would leave
the rest unproven. It also covers the **child processes**: the ops CLIs are
exercised as real child processes, so a seal that lived only in the test's own
process would leave the code under test free to reach the network. Each file
installs the tripwire for its whole duration and asserts zero attempts at the
end, and the CLI harness loads the tripwire into the child through
`NODE_OPTIONS=--require`, where an attempt sets a non-zero exit and reports
itself on stderr rather than passing unnoticed. The preload is armed by an
environment variable the harness sets, so importing the helper ordinarily never
changes a process's behaviour. A test asserts the child seal itself, because a
seal nobody can show working is not evidence.

**Fixtures are synthetic.** The accepted authority baseline — head
`tx_0ba8d4ad…`, state hash `df5084b6…`, `OBSERVATION_COUNT=903` — is *not*
copied into a fixture. Production must not be copied or mutated by this work, so
the fixtures build an authority from scratch through the real pipeline
(`seedFotMobFixtureUniverse`, `persistVerifiedAllocationAuthority`,
`bootstrapMarketEvidenceTransactionStore`, the canonical prospective
transaction builder and publisher, `initializeRequestAccountingEpoch`). The
synthetic authority exercises the same canonical readers and the same
permission contract the production authority does, without touching it.

## Failure matrix

| Failure | Snapshot sealed? | Retry? | Objects deleted? | Next action |
| --- | --- | --- | --- | --- |
| Source identity moves during the copy | no | no | no — the partial payload stays as evidence | investigate the mover before re-running |
| Governed input set changes during the copy | no | no | no | investigate the writer before re-running |
| The governed directory layout changes during the copy | no | no | no | investigate the writer before re-running; a required directory that appeared or went is reported by the identity capture or the content digest, never by a comparison of the two directory sets — the writer carries none |
| A create-only write loses to an existing key | no | no | no | the generation id is already taken; choose another |
| A read-back after write disagrees | no | no | no | the transport is not trustworthy; stop |
| Completeness marker missing | n/a | yes, into a new generation | no | the generation is incomplete; it is never repaired in place |
| Artifact hash or size drift | n/a | yes, into a new generation | no | the generation is corrupt; re-snapshot from a healthy authority |
| Restore destination already exists | n/a | no | no | a restore never overwrites; choose a fresh destination |
| Restored layout is missing a required directory | n/a | no | **yes** — the staging root of that restore only | the generation does not describe the tree; treat it as suspect. Named as a missing directory, never as an `ENOENT` about a descriptor path |
| Restored root fails the canonical-reader proof | n/a | no | **yes** — the staging root of that restore only | the restore is not evidence; treat the generation as suspect |
| The staging root cannot be removed after a failure | n/a | no | no | the original failure is the reported one; the note appended to it names the path left behind |
| Fresh process cannot load the restored root | n/a | no | no | the restored root is not self-sufficient; the proof fails |
| Identity or credential file missing, loose or invalid | n/a | no | no | the live CLI fails closed before a transport exists |
| Identity file carries a secret-shaped value | n/a | no | no | refused as a schema violation; a target identity is non-secret by construction |
| Credential file inside the repository or an evidence directory | n/a | no | no | refused before the file is opened; keep the file elsewhere |
| Delete operation requested of the transport | n/a | no | no | there is no delete verb; the request cannot be expressed |

## What this work does not do

```text
R2_BUCKET_CREATED=NO              R2_BUCKET_MODIFIED=NO
R2_OBJECT_WRITTEN=NO              LIVE_S3_REQUEST_EXECUTED=NO
CLOUDFLARE_AUTH_USED=NO           API_TOKEN_CREATED=NO
CREDENTIAL_CREATED=NO             CREDENTIAL_VALUE_INSPECTED=NO
BUCKET_LOCK_CONFIGURED=NO         R2_BUCKET_LOCK_MODIFIED=NO
BACKUP_CREATED=NO                 PRODUCTION_BACKUP_CREATED=NO
PRODUCTION_RESTORE_EXECUTED=NO    PRODUCTION_CONTENT_MUTATED=NO
PRODUCTION_METADATA_MUTATED=NO    PROVIDER_REQUEST_EXECUTED=NO
THE_ODDS_API_QUOTA_CONSUMED=NO    STAGE_D_STARTED=NO
SCHEDULER_CHANGED=NO              POLICY_B_ACTIVATED=NO
BLOCKER_3_CLOSED_BY_THIS_WORK=NO  GATE_2_ACCEPTED_BY_THIS_WORK=NO
GATE_3_AUTHORIZED_BY_THIS_WORK=NO
```

Each `..._BY_THIS_WORK` line is a statement about this workstream, not about the
repository's current state: the live wiring neither closed Blocker #3 nor
accepted Gate 2. Both have since happened, on separately authorized evidence —
`BLOCKER_3=CLOSED`, `GATE_2=ACCEPTED`, `GATE_3=NOT_AUTHORIZED`,
`STAGE_D_STARTED=NO`. See
[`STAGE_D_BLOCKER_3_CLOSEOUT.md`](STAGE_D_BLOCKER_3_CLOSEOUT.md).

The live wiring is repository-side and offline. It makes the R2 target
*addressable* and *provable*; it does not make it *reached*. Every live-mode
statement in this contract is a statement about what the code would do with a
target, established against a stub SDK in an in-memory bucket, and the words
"the target" throughout mean the address the tooling was given rather than a
bucket anyone contacted. No credential was created, no credential value was
inspected, no lock was configured and no request was made.

Blocker #3 is closed by an off-host target and an isolated-restore proof run
against it. Both now exist: the target was provisioned separately by the Owner,
and the isolated restore of the real pre-repair generation — the one written
before the `required_directories` field existed — was performed from merged main
and cold-loaded by a fresh process to the frozen authority values. `BLOCKER_3`
is therefore `CLOSED` and `GATE_2` is `ACCEPTED`. This contract is unchanged by
that: it still describes only the tooling, it is still not the proof, and it
authorizes nothing further. The proof itself is recorded in
[`STAGE_D_BLOCKER_3_CLOSEOUT.md`](STAGE_D_BLOCKER_3_CLOSEOUT.md).
