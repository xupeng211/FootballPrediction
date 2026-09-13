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

This contract makes **no claim about how far an R2 credential can be scoped**,
and no part of the design depends on such a claim. R2's credential-scoping and
lock behaviour is a provider capability that cannot be established offline, so it
is not asserted here. The tooling instead relies on two properties it states and
tests for itself, both of which hold for every target regardless of how that
target's credentials happen to be scoped: the transport contract below admits no
delete verb, so the writer needs no delete permission anywhere; and
`BUCKET_LOCK_CONFIGURATION` is out of scope for this mission outright, so no
Cloudflare REST API is called to configure a lock.

## Scope and authority

```text
BLOCKER_3_STATUS=OPEN
GATE_2=NOT_ACCEPTED
GATE_3=NOT_AUTHORIZED
STAGE_D_STARTED=NO

BACKUP_TOOLING_CLASS=OFFLINE_IMPLEMENTATION_ONLY
BACKUP_TOOLING_ENTRYPOINT=scripts/ops/stage_d_backup_snapshot.js (offline, filesystem transport)
RESTORE_TOOLING_ENTRYPOINT=scripts/ops/stage_d_restore_verify.js (offline, filesystem transport)
LIVE_R2_CLI_WIRING=NOT_IMPLEMENTED
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

## RPO/RTO policy — one proposal, deliberately unapproved

Two candidate policies were put to the Controller. **Proposal B** — a snapshot
on every canonical commit, giving `RPO=0` for committed transactions — is the
recommended one and is recorded here as `PROPOSED`, not as the governing policy.
Proposal A (uniform `RPO <= 24h`) remains the fallback.

`POLICY_B_STATUS=PROPOSED_NOT_APPROVED` means exactly what it says: the tooling
does not assume per-commit invocation, no caller is wired to invoke it per
commit, and `RPO_ZERO_COMMITTED_TRANSACTIONS=NOT_YET_ENFORCED`. A future
authorization that adopts Proposal B must add the invocation point *and* the
availability argument that `RPO=0` requires; neither exists yet.

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
7. re-enumerate the governed input set and require it to be unchanged
8. write the manifest, binding both identities
9. write the completeness marker LAST, binding the manifest hash
```

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
transport accepts an injected client as a seam for the command mechanics (the
tests drive the S3 verbs through one, with no network), and an injected client
is not a way to bring a different credential source: credentials are validated
before the client is chosen, so a caller cannot hand in a client backed by the
SDK's default provider chain and leave the transport with no explicit-credential
claim to make. A refusal that only applies on one branch is a conditional
guarantee, which is not a guarantee. A test constructs the transport with a
stub client and no credentials and asserts it is refused.

Errors are rebuilt from provider-supplied identifiers only (error name and HTTP
status). Nothing from the client configuration is interpolated, so a secret
cannot reach a message, a stack trace assembled here, or a report — asserted by
a test that fails a call with a secret embedded in the provider's message.
`describe()` excludes credentials entirely and is safe to serialize.

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
- outside every source root the caller names, and not containing one;
- free of symbolic-link ancestors, and created with `0700`.

A failed restore leaves the destination **exactly as it was found** — that is,
still non-existent. It is built at a staging path beside the destination and
moved into place with a single `rename` only after every artifact has been
written and the proof has come back `PASS`, so the destination cannot be
observed in a partial state: it either does not exist, or it exists complete
and proven. Building it at its final path instead would have made every later
failure — a missing object, a hash the manifest does not bind, or a proof that
returns `FAIL` — leave behind a partial tree at a path that had not existed
before, and because a restore refuses a destination that already exists, that
tree could never have been restored into again.

Nothing is ever removed, so a failure leaves the staging directory in place as
visible evidence of the attempt while the destination stays untouched. The
report names the destination, not the staging path: the layout fields are
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

**The proof is performed by the canonical readers.** `proveRestoredRoot` points
`openMarketEvidenceAuthoritySnapshot` and `readRequestLedger` at the restored
root with no other input and compares the result against what the manifest
bound — the head transaction id and content hash, head sequence, state hash, the
four counts, the request-accounting epoch id, entry count and terminal hash, and
the store, allocation and quota hashes. A bespoke checker would prove only that
the checker and the writer agree; the canonical readers prove the restored bytes
are an authority the runtime would accept.

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

Neither CLI accepts an endpoint, bucket, region, credential or profile flag.
Those flags are **rejected rather than ignored**, in both spellings: `--endpoint
https://…` and `--endpoint=…` mean the same thing to whoever types them, so a
check that matched only the first would silently ignore the second and let an
operator believe the command was aimed at R2 when it was not. The rejected value
is never echoed back — a value passed to one of these flags may be a credential,
so echoing it would turn a refusal into a leak. A test drives every flag in both
spellings at both CLIs and asserts each is refused by name, with the value
appearing in neither stdout nor stderr. Live R2 wiring is a separate, explicitly
authorized change.

That named list is a denylist, and a denylist can only refuse the names someone
thought to write down. The names that matter most here are exactly the ones that
keep being invented, and the near-misses slip past it: `--r2-access-key-id=…`
contains no `--r2=` (the character after `--r2` is `-`, not `=`), and
`--storage-endpoint=…` contains no `--endpoint`. Both were parsed by nothing,
ignored, and the command ran to completion and exited `0` while carrying an
access key or an API token in its own argv. Each CLI therefore **accepts only
the flags it implements**: every argument must be one of that CLI's own flags
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
`dns.lookup` and `globalThis.fetch` with throwers, and asserts zero attempts
across a full write, verify and restore. A test that silently reached a provider
endpoint would pass for the wrong reason and would consume someone's quota while
doing it.

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
| A create-only write loses to an existing key | no | no | no | the generation id is already taken; choose another |
| A read-back after write disagrees | no | no | no | the transport is not trustworthy; stop |
| Completeness marker missing | n/a | yes, into a new generation | no | the generation is incomplete; it is never repaired in place |
| Artifact hash or size drift | n/a | yes, into a new generation | no | the generation is corrupt; re-snapshot from a healthy authority |
| Restore destination already exists | n/a | no | no | a restore never overwrites; choose a fresh destination |
| Restored root fails the canonical-reader proof | n/a | no | no | the restore is not evidence; treat the generation as suspect |
| Fresh process cannot load the restored root | n/a | no | no | the restored root is not self-sufficient; the proof fails |

## What this work does not do

```text
R2_BUCKET_CREATED=NO              R2_BUCKET_MODIFIED=NO
R2_OBJECT_WRITTEN=NO              LIVE_S3_REQUEST_EXECUTED=NO
CLOUDFLARE_AUTH_USED=NO           API_TOKEN_CREATED=NO
BACKUP_CREATED=NO                 PRODUCTION_BACKUP_CREATED=NO
PRODUCTION_RESTORE_EXECUTED=NO    PRODUCTION_CONTENT_MUTATED=NO
PRODUCTION_METADATA_MUTATED=NO    PROVIDER_REQUEST_EXECUTED=NO
THE_ODDS_API_QUOTA_CONSUMED=NO    STAGE_D_STARTED=NO
SCHEDULER_CHANGED=NO              POLICY_B_ACTIVATED=NO
BLOCKER_3_CLOSED=NO               GATE_2_ACCEPTED=NO
GATE_3_AUTHORIZED=NO
```

Blocker #3 is closed by an off-host target and an isolated-restore proof run
against it. Neither exists yet. This contract describes the tooling that will
perform that proof; it is not the proof, and it does not close the blocker.
