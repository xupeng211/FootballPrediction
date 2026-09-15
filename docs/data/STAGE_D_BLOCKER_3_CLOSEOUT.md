# Stage D Blocker #3 — formal closure and Gate 2 acceptance

> lifecycle: current-state record
>
> 状态：`BLOCKER_3=CLOSED`、`GATE_2=ACCEPTED`、`GATE_3=NOT_AUTHORIZED`、`STAGE_D_STARTED=NO`。

This document records the formal closure of Stage D Blocker #3 and the acceptance of Gate 2,
both adjudicated by the Execution Controller and persisted here through the repository's
existing current-state mechanism. It records an already-completed and already-accepted
technical proof. It does **not** re-derive that proof, re-run it, or authorize anything new.

Nothing here authorizes Gate 3, a Stage D start, a provider request, a quota-consuming probe, a
scheduler change, a new backup generation or any production mutation.

## 1. Authorization and base revision

| Field | Value |
| --- | --- |
| Controller adjudication | `BLOCKER_3_CLOSURE_ACCEPTED=YES`, `BLOCKER_3=CLOSED`, `GATE_2_ACCEPTANCE_AUTHORIZED=YES`, `GATE_2=ACCEPTED` |
| Authorizing main | `e660e1a4152191458dc73f369c776be17ab15633` |
| Pre-merge main | `06299681e309e6b3fe2891b1a6213e78aaec6cf7` |
| Merged pull request | #1916, `SQUASH`, head `bc54a7520098257171268f3657cbe7810896cc5f` — merged at the authorized head with no drift |
| Merge tree | `3919d96a09291417cccac98f053881ba17a918a1` |
| Merged at / by | `2026-09-15T16:15:07Z` / `xupeng211` |
| Change set | 12 files, `+1705` / `−71` |
| Accepted evidence package | `/home/xupeng/FootballPrediction.artifacts/stage-d-blocker3-merge-1916-and-final-restore-closure/20260915T161642Z/` |
| Evidence manifest SHA256 | `8b2788b833b171b33e23b14a2d0d4e646c12fc750f9ac0bd49383f212fbfb973` |

The evidence package is outside the repository; the raw host evidence is not copied into Git.
This document records its conclusions and the hashes that bind them.

Re-verified independently while writing this record, rather than carried over from the closure
mission's own summary: `origin/main` is still exactly `e660e1a41…`, PR #1916 reads `MERGED` with
`mergeCommit.oid = e660e1a41…`, the package still holds 33 artifacts with 0 missing, 0 digest
mismatch, 0 mode mismatch, 0 unlisted and a matching manifest hash (`VERIFY: PASS`), and its
`18-closure-verdict.json` reports `criteria_satisfied: 12 / 12`. No target was contacted and no
remote object was read while writing this record.

## 2. What Blocker #3 was, and what closes it

Stage D's accepted authority and its evidence live in one physical failure domain. A single
disk, host or filesystem event could take the authority and every copy of it at once, so a
restore procedure existing only on that host would not be a restore procedure. Blocker #3 is the
requirement for a target in a **different physical fault domain** plus a demonstrated
isolated-restore of the real authority into it.

Blocker #3 is therefore closed by behaviour, not by tooling existing: by a physically
independent off-host target, a real canonical Stage D backup, a remote verification of that
backup, an isolated restore of it performed from authoritative merged main, and a genuinely
fresh process cold-loading the restored authority to the frozen values. Tooling alone never
closed it, and Blocker #2's closeout said so explicitly.

## 3. The accepted evidence chain

Bound verbatim to `MAIN_SHA=e660e1a4152191458dc73f369c776be17ab15633`:

```text
REMOTE_GENERATION=snap_20260915T125353656Z_d059e495e3047958

SNAPSHOT_ID=stage-d-preauth-20260909-20260909T012915Z-df5084b6d752
FINAL_MANIFEST_SHA256=4397f0a432f22154492e80abfd8f79100b20fe7ce30dff5d67487231bdd1fa74
TRANSACTION_AUTHORITY_HEAD=tx_0ba8d4ad78aef57d1bbadf6637198b08d9586c5debf3e343d07033ed98a6bb64
STATE_HASH=df5084b6d752d698bfde4646fb508f3a41396f160fbee3cca9ee1b3b412e5ddd
OBSERVATIONS=903
STORE_SHA256=ed014a6f151143aa30cefcebc47374059aa18c38a83560610571331a665199e4
ALLOCATION_AUTHORITY_SHA256=89e4276c8fe637318339821fe40d783d2f7fd8de65f6fc593b2035bd9445dad3
EPOCH=sde_b10b6bd109a6c60498fbd9e8c9ec87894e79ca1091aedbdb229083199cd00406
```

The twelve closure criteria and their evidence:

| Criterion | Value | Evidence |
| --- | --- | --- |
| `PR_1916_MERGED` | `YES` | merge receipt — squash `e660e1a41…`, merged `2026-09-15T16:15:07Z` |
| `REMOTE_GENERATION_PRE_RESTORE_VERIFY` | `PASS` | merged verifier, 14/14 objects, hashes unchanged |
| `ISOLATED_RESTORE_PASS` | `YES` | merged-main isolated restore report |
| `ZERO_ENTRY_LEDGER_RESTORE_PASS` | `YES` | zero-entry ledger section |
| `FRESH_PROCESS_CANONICAL_PROOF_PASS` | `YES` | all eight frozen values match |
| `REQUEST_ACCOUNTING_RESTORE_PROOF` | `PASS` | request-accounting and quota evidence |
| `QUOTA_STATE_RESTORE_PROOF` | `PASS` | request-accounting and quota evidence |
| `RUNTIME_SHIM_REQUIRED` | `NO` | credential-shim absence proof |
| `EXISTING_REMOTE_GENERATION_MUTATED` | `NO` | re-read after every operation, `differences: []` over 14/14 objects |
| `TARGET_HOST_IDENTITY_RECONFIRMED` | `YES` | SSH host key, machine-id, hostname, MAC, systemd unit, TLS serial, layer 2 |
| `TLS_DOWNGRADE_REGRESSION` | `NO` | HTTPS health `PASS`, plaintext HTTP `REFUSED`, certificate identity `EXPECTED` |
| `SECRET_SCAN_PASS` | `YES` | value pass 0 hits |

## 4. The target, and its identity

| Field | Value |
| --- | --- |
| Endpoint | `https://192.168.11.70:9000` (self-hosted S3-compatible store) |
| Bucket | `fp-stage-d-snapshot-archive` |
| Prefix | `stage-d-snapshots` |
| Transport contract | `create_only: true`, `delete_exposed: false` — no delete verb is expressible |
| Credential model | data-plane, minimum scope, no delete, no bucket administration |
| `NORMAL_BACKUP_RUNTIME_CAN_REMOVE_LOCK` | `NO` |

Identity was reconfirmed independently — SSH host key, `machine-id` hash, hostname, MAC address,
systemd unit and TLS certificate serial — and again at layer 2. No count of signals is asserted
here; the enumeration is the one the accepted closure report itself records. The endpoint still
identifies the same machine, so `BACKUP_TARGET_ADDRESS_IDENTITY_CHANGED` was not raised.

TLS: HTTPS health `PASS`; plaintext HTTP `REFUSED`; certificate identity `EXPECTED`;
credential-file protections `EXPECTED`. `TLS_DOWNGRADE_REGRESSION=NO`. No certificate-validation
requirement was weakened at any point; the only trust configuration in play is the ordinary CA
trust for the target's self-signed certificate.

## 5. The load-bearing proof — the existing generation restores from merged main

The generation already on the target was written by code that predates the
`required_directories` manifest field, so it is exactly the backward-compatibility case — and
exactly the case that failed before the repair.

`backup.verifySnapshot` on merged main: `PASS`, `observed_object_count: 14`,
`artifact_count: 12`, `total_bytes: 1870048`, `request_accounting_entries: 0`, `failures: []`.

`restoreExecutor.executeRestore` on merged main into a **new** isolated destination, with
`sourceRoots` empty by construction:

| Field | Value |
| --- | --- |
| `result` | `PASS` |
| `restored_object_count` | 12 |
| `restored_directory_count` | 1 — `request-accounting/entries`, mode `0o700` |
| `required_directories` | `["request-accounting/entries"]` |
| `required_directories_source` | `DERIVED_FROM_CANONICAL_LAYOUT` |
| `production_fallback_used` | `false` |
| `production_paths_read` | `[]` |
| `failures` | `[]` |
| Destination | `/home/xupeng/.stage-d-closure-e660e1a4/isolated-restore/snap_20260915T125353656Z_d059e495e3047958` |

```text
REQUIRED_DIRECTORIES_SOURCE=DERIVED_FROM_CANONICAL_LAYOUT
MANUAL_MKDIR_USED=NO          RUNTIME_SHIM_USED=NO
MONKEY_PATCH_USED=NO          NODE_OPTIONS_WORKAROUND_USED=NO
BRANCH_CODE_USED=NO           CANONICAL_SNAPSHOT_FALLBACK_USED=NO
PRODUCTION_STORE_FALLBACK_USED=NO   HIDDEN_LOCAL_CACHE_USED=NO
```

The directory that holds no files was reconstructed because the canonical layout requires it,
not because a human put it there.

## 6. Zero-entry ledger, fresh-process cold load, accounting and quota

The restored `entries/` is a plain empty `0o700` directory (`nlink 2`). A 20-path before/after
comparison across the canonical read added, removed and modified nothing
(`READER_MUTATED_RESTORED_STATE: false`), so `ZERO_ENTRY_LEDGER_RESTORE_PASS=YES`.

A scrubbed child — complete environment `PATH`, `PROBE_ROOT`, `PROBE_SNAPSHOT_ID`; `execArgv: []`;
`loaded_shim_free: true` — loaded the restored authority and returned all eight frozen values with
`ALL_VALUES_MATCH: true`. `RUNTIME_SHIM_REQUIRED=NO`, `NODE_OPTIONS_WORKAROUND_USED=NO`.

`REQUEST_ACCOUNTING_RESTORE_PROOF=PASS` and `QUOTA_STATE_RESTORE_PROOF=PASS`: the accounting
epoch is present, all counters are zero, no post-epoch request is fabricated, and the source head
transaction is the same one the manifest was written against. The historical uncertainty is
preserved and not reinterpreted — `REQUEST_ACCOUNTING_PRE_EPOCH_LOWER_BOUND=AT_LEAST_2_CONFIRMED`,
`REQUEST_ACCOUNTING_PRE_EPOCH_EXACT_TOTAL=UNKNOWN`.

`SDK_CREDENTIAL_MUTABILITY_CONFLICT=RESOLVED` by the merged change itself — the transport
deep-freezes its own record of the credential and hands the SDK a private mutable copy — with no
shim, patch or `NODE_OPTIONS` involvement.

## 7. The remote generation was read, never written

Re-read after every operation using only `listObjects` and `getObject`:
`baseline_object_count: 14` → `observed_object_count: 14`, `differences: []`, every sha256
identical to an independent pre-operation baseline taken before any operation ran.

```text
EXISTING_REMOTE_GENERATION_MUTATED=NO
writes_performed=0        deletes_performed=0
```

## 8. Cleanup safety and symlink escape

Five live scenarios drove the real executor against the real generation read-only, each failing
on purpose through a declared fault-injecting transport decorator — not a shim on the code under
test:

| Scenario | Result |
| --- | --- |
| R1 failure part-way through materialization | staging root removed, destination absent, neighbouring sentinel byte-identical, parent listing unchanged |
| R2 a symlink planted inside the staging tree | link unlinked, its target's files all present and unchanged |
| R3 the staging root's name swapped for a symlink | cleanup refused (`SNAPSHOT_INTEGRITY_VIOLATION`), recorded on the original error, foreign link not removed, its target untouched |
| R4 destination already exists | refused before any staging root was created; foreign content byte-identical |
| R5 symlink destination / symlink parent / symlinked ancestor into the source root | all three refused, including the case only the physical comparison can see |

`FAILED_RESTORE_STAGING_CLEANUP_PROOF=PASS`, `SYMLINK_ESCAPE_PROTECTION=PASS`. No path outside
the demo root was created or removed by any scenario. The same nine paths are pinned by tracked
tests in `restore_executor.test.js` (lines 186, 417, 496, 528, 563, 605, 653, 699, 738).

## 9. Secret safety of the evidence package

`SECRET_SCAN_PASS=YES`. The value pass searched every byte of the package for the values of the
credentials this workstream held and found **0 hits** across 32 files / 154,878 bytes; the shape
pass found 0 hits needing adjudication. No credential value appears in any log, report, error or
evidence file, and credentials are never passed on the command line or discovered from the
environment, a profile or a provider chain.

Directories `0700`, files `0600`; `MANIFEST.json` + `MANIFEST.sha256` verify `PASS`.

## 10. Gate 2 acceptance

```text
GATE_2_ACCEPTANCE_AUTHORIZED=YES
GATE_2=ACCEPTED
```

The accepted Gate 2 **technical** requirement is:

- physical independence — an off-host target in a different fault domain;
- a real canonical Stage D backup written to it;
- a remote verification of that backup;
- an isolated restore of it from authoritative merged main;
- a fresh-process canonical proof of the restored authority.

All five are satisfied by the evidence chain in sections 3–6, and the Controller has adjudicated
the requirement met.

**The acceptance distinguishes technical requirement from long-term operational hardening.** The
items registered in section 11 — a tracked backward-compatibility regression test, a DHCP
reservation, an off-site/cloud copy — are hardening. They do **not** invalidate Gate 2 and they
did not gate it. Recoding them as Gate 2 conditions after the fact would be a silent tightening of
an accepted requirement, which this record does not do.

## 11. Failure domain and the nonblocking follow-up register

### 11.1 Failure domain

```text
OFF_HOST=YES
OFF_SITE=NO
DHCP_RESERVATION_STATUS=NOT_CONFIGURED
OPERATIONAL_HARDENING_REQUIRED=DHCP_RESERVATION
OFFSITE_GAP_ACCEPTED_AS_NONBLOCKING=YES
LONG_TERM_OFFSITE_BACKUP_RECOMMENDED=YES
DHCP_RESERVATION_NONBLOCKING=YES
DHCP_RESERVATION_RECOMMENDED=YES
```

`OFF_HOST=YES` — the target is a different machine, reconfirmed independently by SSH host key,
machine-id hash, hostname, MAC address, systemd unit and TLS certificate serial, and again at
layer 2.

`OFF_SITE=NO` — `192.168.11.2` (this host) and `192.168.11.70` (the target) sit in one `/24` on
one layer-2 segment at one physical site. The copy is off-host but **not** off-site: a site-level
event takes both. This is stated as `NO` and is **not** upgraded to geographic disaster recovery.
The Controller has adjudicated that this gap does not block Gate 2, because the accepted
requirement is physically independent off-host recoverability, which is proven. It is registered
below as long-term disaster-recovery hardening.

`DHCP_RESERVATION_STATUS=NOT_CONFIGURED` — the target's address is DHCP-acquired
(`default via 192.168.11.1 dev enp2s0 proto dhcp src 192.168.11.70`). No reservation was found or
configured. The Controller has adjudicated that this does not block Gate 2, because target identity
was independently reconfirmed during the real closure proof using multiple host identity signals.
What a reservation buys is that an address change does not have to be *detected*; the closure
evidence records the target as already reconfirmed by independent identity signals, so an address
change would be detectable rather than silent.

### 11.2 Nonblocking follow-up register

```text
FOLLOWUP_BACKCOMPAT_TEST=OPEN_NONBLOCKING
FOLLOWUP_DHCP_RESERVATION=OPEN_NONBLOCKING
FOLLOWUP_OFFSITE_BACKUP=OPEN_NONBLOCKING
MISSING_TRACKED_BACKCOMPAT_TEST_BLOCKS_GATE_2=NO
```

**FOLLOWUP_TEST_1 / FOLLOWUP_TEST_2 — the missing zero-entry-ledger backward-compatibility test.**
Classification `TEST_HARDENING`, nonblocking.

`tests/unit/market_evidence/backup/restore_required_directories.test.js` (34,622 bytes, 17 tests,
sha256 `c893e0c33ea9040406b4f9cc11ebbcde77cc879efad1095286cd3024c6b3f76e`) was exercised during
PR #1916 but was **never committed**: `.gitignore` line 285 is `backup/`, which matches the whole
`tests/unit/market_evidence/backup/` directory, so `git status` hides the file, `git add -u`
cannot add a new untracked file, and `git add <pathspec>` refuses it — while the shell glob still
picks it up and runs it. That is why the merged backup suite is 251 tracked tests and not the 268
the PR body reports; 268 − 251 = 17.

This is an **evidence-accuracy** defect in the merged record, and it does not reopen Blocker #3 or
Gate 2: the exact backward-compatibility case was exercised end-to-end against the real pre-field
remote generation from authoritative merged main and passed isolated restore plus fresh-process
cold-load. It is **not** claimed here that the file was tracked during PR #1916; it was not.

Measured while writing this record, in a clean worktree at `e660e1a41…` with the file added:

```text
the 17 tests alone                      17 pass / 0 fail
the whole backup directory, tracked only 251 pass / 0 fail
the whole backup directory, with the file 268 pass / 0 fail
eslint on the file                      clean, exit 0
network access                          none — the file installs a network tripwire and asserts zero attempts
```

The file already contains both objectives the follow-up names: CASE F (`a generation written
before the field existed is admitted, verified, and restored`) asserts
`required_directories_source === 'DERIVED_FROM_CANONICAL_LAYOUT'` for the legacy path, and CASE A
plus CASE E cover the zero-entry ledger derivation, isolated restore and fresh-process load. The
assertion is version-bound and layout-shaped, not generation-shaped.

It is preserved byte-for-byte in the accepted evidence package as
`probe/13a-UNTRACKED-restore_required_directories.test.js`; the original file was left untouched.

**Why it is deferred rather than added here.** Adding it requires a `.gitignore` exception, which
is a repository-wide hygiene change rather than a documentation one, and `FOLLOWUP_BACKCOMPAT_TEST`
is required to read `OPEN_NONBLOCKING`. This record is a pure closure recording, so the repair is
left as a separate, narrowly scoped change: re-include the directory with the narrowest possible
exception (`!tests/unit/market_evidence/backup/` — a literal path, so no broad backup artifact can
be admitted), add the file, and correct the test figures in the merged PR's record. Nothing about
Gate 2 depends on it.

**FOLLOWUP_NETWORK_1 — DHCP reservation.** Classification `OPERATIONAL_HARDENING`,
`NONBLOCKING_FOR_GATE_2`.

| Field | Value |
| --- | --- |
| Address | `192.168.11.70` |
| Interface | `enp2s0` |
| MAC | `34:97:f6:e3:b0:32` |
| DHCP server | `192.168.11.1` |

No router or DHCP server configuration was inspected or changed by this mission, and none should
be changed unless it is already safely automated and separately authorized.

**FOLLOWUP_DR_1 — off-site disaster-recovery copy.** Classification
`DISASTER_RECOVERY_HARDENING`, `NONBLOCKING_FOR_GATE_2`. The long-term objective is an independent
off-site or cloud copy, since the current target is off-host but not off-site.

## 12. PR #1914 status

Read-only. No action was taken on it: it was not merged, closed, edited, rebased, commented on or
pushed to, and no AWS API was called.

```text
PR_1914_ACTION=NONE
AWS_PR_1914_CURRENT_STATE=OPEN_HEAD_4b1ff1240_MERGEABLE_CONFLICTING_DIRTY
AWS_FALLBACK=HISTORICAL_CANDIDATE_REQUIRING_REBASE_OR_REIMPLEMENTATION
AWS_FALLBACK_STATUS=NOT_CURRENTLY_ACTIVE
```

| Field | Value |
| --- | --- |
| State | `OPEN`, not draft, `mergedAt: null`, `closedAt: null` |
| Head | `4b1ff1240655c196570d53f4f57d3ff408922be3` (2 commits: `120f002af`, `4b1ff1240`) |
| Base | `main` |
| Merge base | `c946b51c06fb1945f1b8c3b320e9007ac189523e` — main has moved on by 2 commits |
| `mergeable` / `mergeStateStatus` | `CONFLICTING` / `DIRTY` |
| Conflicting path | `src/infrastructure/market_evidence/backup/liveTargetIdentity.js` — the only one; its other two paths merge cleanly |

It is **not** merge-ready and is **not** claimed to be. It was retained as the cloud fallback for
the off-site half of the failure domain because it is the adjudicated provider path — the survivor
of ten evaluated providers after the R2 route was payment-blocked — and nothing supersedes it. Its
`DOCUMENTED_SUPPORTED` atomic create-only claim remains **not live-proven**; establishing it needs
AWS provisioning, which has not happened.

## 13. What this mission did and did not change

This is a documentation-only change set:

| Path | Change |
| --- | --- |
| `docs/data/STAGE_D_BLOCKER_3_CLOSEOUT.md` | new — this record |
| `docs/agentic/missions/STAGE_D_BLOCKER_3_FORMAL_CLOSURE_AND_GATE_2_ACCEPTANCE.json` | new — the mission scope contract |
| `docs/PROJECT_STATUS.md` | current-state status |
| `docs/ACTIVE_MILESTONE.md` | current-state status |
| `docs/CAPABILITY_INDEX.md` | current-state status |
| `docs/data/STAGE_D_BLOCKER_3_BACKUP_TOOLING_CONTRACT.md` | stale current-state claims corrected; lifecycle unchanged |
| `docs/data/STAGE_D_CONTINUOUS_OPERATIONS_CONTRACT.md` | stale current-state claims corrected; lifecycle unchanged |

No production runtime behavior changes. The mutation class, the transport contract, the restore
executor, the required-directory semantics, the credential model, both CLIs, every schema, every
test and the `.gitignore` file are byte-identical after this change set.

**Historical evidence is not rewritten.** Dated evidence documents and superseded mission-scope
records that still read `BLOCKER_3=OPEN` or `GATE_2=NOT_ACCEPTED` are left exactly as they were —
they were true when written. Only the documents that declare themselves current-state are brought
to the accepted state. In particular the two state blocks in the Blocker #3 tooling contract and
in the continuous-operations contract are marked superseded with the current status added, rather
than deleted, so the record of what changed is itself preserved.

## 14. What remains unproven, stated as such

- **PR #1914's atomic create-only claim is `DOCUMENTED_SUPPORTED`, not live-proven.** It needs AWS
  provisioning, which this mission did not do.
- **`O_NOFOLLOW` refusal during the walk's `lstat`→`open` window** has no deterministic in-process
  seam and is covered by tracked tests and by mutation, not by a live race.
- **The DHCP reservation question** is observable only from the DHCP server; the target cannot
  answer it and no privileged escalation was taken to look.
- **Whether the off-site gap is acceptable** is a governance decision, adjudicated here as
  nonblocking for Gate 2 and recorded as long-term hardening rather than resolved.

## 15. State after closeout

```text
BLOCKER_3=CLOSED
GATE_2=ACCEPTED
GATE_3=NOT_AUTHORIZED
STAGE_D_STARTED=NO
THE_ODDS_API_CONTACTED=NO
NEW_BACKUP_GENERATION_WRITTEN=NO
REMOTE_BACKUP_OBJECTS_DELETED=NO
PR_1914_MERGED=NO
AWS_PROVISIONING_STARTED=NO
```

No provider request, no quota consumption, no Stage D start, no scheduler change, no canonical
transaction, no new backup generation, no remote write or delete, no production mutation and no
Gate 3 authorization. Gate 3 stays `NOT_AUTHORIZED`; the next Controller mission decides whether
prerequisites justify authorizing exactly one real The Odds API request, and this record neither
pre-empts nor predicts that decision.

Related: [`STAGE_D_BLOCKER_3_BACKUP_TOOLING_CONTRACT.md`](STAGE_D_BLOCKER_3_BACKUP_TOOLING_CONTRACT.md),
[`STAGE_D_CONTINUOUS_OPERATIONS_CONTRACT.md`](STAGE_D_CONTINUOUS_OPERATIONS_CONTRACT.md),
[`STAGE_D_BLOCKER_2_PHASE_B_CLOSEOUT.md`](STAGE_D_BLOCKER_2_PHASE_B_CLOSEOUT.md).
