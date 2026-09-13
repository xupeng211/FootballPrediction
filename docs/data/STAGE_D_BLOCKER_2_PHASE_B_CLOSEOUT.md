# Stage D Blocker #2 — Phase B execution closeout and deviation adjudication

Status document. This records the **closeout** of the already-executed Stage D Blocker #2
Phase B production filesystem metadata remediation, and adjudicates the one documented
execution deviation and the two executor verification-logic defects that accompanied it.

This document does **not** authorize production mutation, Stage D execution, provider
access or any future repair. It records a historical adjudication of one evidence set.

## 1. Authorization and base revision

| Field | Value |
| --- | --- |
| Authorizing main | `c86a2b567b55bcf314a136e73bd9d5e5d231ed7e` |
| Mission | `STAGE_D_BLOCKER_2_PHASE_B_PRODUCTION_REMEDIATION_CORRECTED_CONTENT_SET_RETRY` |
| Executed in dev container | `NO` — host procedure by construction (the audit requires `getfacl`) |
| Production remediation evidence root | `/home/xupeng/FootballPrediction.artifacts/stage-d-blocker2-phase-b-corrected-retry/20260913T174503Z` |
| Evidence manifest SHA256 | `87d8d4d9579936fc9d5cd8a7bbeb9f9329208c77fa59d605b27a78df54897de3` |
| Evidence shape | directory `0700`, 30 files at `0600`, 29 manifest-listed artifacts, `sha256sum -c` clean |

The evidence root is outside the repository. The raw host evidence is not copied into Git;
this document records only its conclusions and the hashes that bind them.

## 2. The original plan — 9 operations

Fresh canonical audit immediately before mutation:

```text
AUDIT_STATUS=NONCOMPLIANT_REPAIRABLE   VIOLATIONS=15   ADVISORIES=2   AMBIGUOUS=0
PLAN_STATUS=READY_WITH_ELEVATED_PRIVILEGE
PLANNED_METADATA_OPERATIONS=9          BLOCKED_OPERATIONS=0
CONTENT_BEARING_ARTIFACTS=9            PRE_MUTATION_RECHECK=9/9   DRIFT=NONE
```

The plan ranged over 15 governed objects on filesystem device `66309` and emitted 9
operations, every one carrying `elevated_privilege_required=true`:

| seq | operation | object |
| --- | --- | --- |
| 1 | `CHOWN` | `data/market_evidence/live/transactions/committed/tx_0ba8d4ad…a6bb64` (the transaction package directory) |
| 2 | `REMOVE_EXTENDED_ACL` | same directory |
| 3 | `CHMOD` | same directory |
| 4–9 | `CHOWN` | `COMMITTED`, `identity_decisions.jsonl`, `manifest.json`, `metadata.json`, `observations.jsonl`, `registry_delta.json` |

The directory's contract postcondition was `uid=1000`, `gid=1000`, `mode=0700`, and its
plan-time state was `uid=0`, `gid=0`, `mode=0750` with the extended ACL
`u::rwx,u:xupeng:r-x,g::---,m::r-x,o::---`. The six package files were `uid=0`, `gid=0`,
`mode=0400` and their postcondition preserved `0400`, changing ownership only.

## 3. What was actually executed — 8 operations

```text
ACTUAL_MUTATION_COMMANDS=8   CHOWN=7   REMOVE_EXTENDED_ACL=1   CHMOD=0
UNPLANNED_MUTATIONS=0        UNPLANNED_PATHS=0
```

Seven commands were `sudo -n /usr/bin/chown 1000:1000 -- <exact-absolute-path>` and one was
`/usr/bin/setfacl -b -- <exact-absolute-path>`. Each was a single fixed-purpose executable
against one exact absolute path: no shell, no glob, no recursion, no `find -exec`.

`sudo` was used **only** for operations the plan marked `elevated_privilege_required=true`.
The two directory operations became unprivileged once the runtime identity owned the
directory, and were run without it.

Independently recomputed from the raw pre-metadata manifest against the post-repair audit —
not from the executor's own summary — **exactly 7 governed objects changed**, and all 7 are
objects the plan targeted. The other 8 governed objects are bit-identical in ownership and
mode. Device and inode are unchanged for all 15 governed objects, so no object was replaced.

## 4. The omitted operation — exactly one `CHMOD`

`seq=3 CHMOD` on the transaction package directory was the only planned operation never
invoked. Its journal entry carries no `command` field and records
`result=ABORT_PRECONDITION_DRIFT`: the apply-time precondition check refused it.

**Why its postcondition was already satisfied.** While an extended ACL exists, the mode's
group bits *are* the mask. The directory's `0750` was `u::rwx` plus `mask::r-x`; the real
`group::` entry was `---`. `setfacl -b` (`seq=2`, an authorized planned operation on the
same object) removes the named entry and the mask, so the group bits fall back to the real
`group::` entry and the directory lands on exactly `0700` — the contract postcondition.
The journal records `mode 0o750 -> 0o700` with ACL
`user::rwx,user:xupeng:r-x,group::---,mask::r-x,other::--- -> user::rwx,group::---,other::---`
on the same `dev`/`ino`.

This is the mechanism the planner itself documents. Its `acl_mask_caveat` states that
"setfacl -b re-normalises `group::` from the mask it deletes; the ACL removal therefore runs
before the closing CHMOD, which is what makes `post.mode` exact", and the `REMOVE_EXTENDED_ACL`
source comment says the base `group::` entry "is re-normalised by the removal itself, which is
why the mode is set afterwards".

Canonical tooling confirms the operation became unnecessary rather than merely skipped: the
re-plan taken **after** the ACL removal dropped the directory from the plan entirely —
`VIOLATIONS` fell `15 -> 14 -> 12`, and the plan fell `9 -> 8 -> 6` operations, leaving only
the six file `CHOWN`s. The final post-repair audit reports `COMPLIANT`, `0` violations,
`PLAN_STATUS=NOT_REQUIRED`, `0` operations.

```text
OMITTED_CHMOD_POSTCONDITION_ALREADY_SATISFIED=YES
DEVIATION_CLASS=AUTHORIZED_PREDECESSOR_SIDE_EFFECT_SATISFIED_FINAL_POSTCONDITION
CONTRACT_POSTCONDITIONS_MET=9/9
```

The gratuitous ninth mutation was deliberately **not** executed. Re-running a `chmod` whose
postcondition already holds, outside a plan that no longer emits it, would be an
unaccountable production mutation performed to make a counter read 9.

## 5. The two executor verification-logic defects

Both halted forward execution; neither produced an incorrect or unexpected production state.

**Defect 1 — mode compared immediately for a `CONTRACT_POSTCONDITION` operation.** After the
first `CHOWN`, the per-operation check compared the object against the final mode expectation.
The plan marks that mode `mode_source=CONTRACT_POSTCONDITION` with `mode_applied_last=true`:
it is the postcondition of the whole directory operation group, applied by the later `CHMOD`,
not an immediate result of the `CHOWN`. The `CHOWN` itself produced exactly the expected
intermediate state — `uid/gid 0 -> 1000`, mode preserved `0750`, `dev`/`ino` unchanged.

**Defect 2 — `pre.mode` compared literally for the `CHMOD` that follows the same path's
`REMOVE_EXTENDED_ACL`.** The shared plan-time `pre` records the pre-repair snapshot; the
authorized preceding operation legitimately moves the mode, as section 4 describes. The
refusal was the safe outcome, and the canonical re-plan then showed the operation was no
longer required at all.

```text
EXECUTOR_DEFECT_1=VERIFIER_FALSE_FAILURE_NO_PRODUCTION_DEFECT
EXECUTOR_DEFECT_2=VERIFIER_FALSE_FAILURE_NO_PRODUCTION_DEFECT
```

Both are recorded in the evidence root's `mutation-journal.json` under `executor_defects`; the
misleading first entry is **annotated** (`result_original=FAIL`, `result=PASS_EXECUTED`,
`phase=initial`, `execution_succeeded=true`) rather than silently rewritten.

## 6. Rollback was not required

Rollback is owed when a real mutation fails or production reaches an unexpected state. Neither
pause was either. Every issued command exited `0` and produced its planned state; the two
halts were verifier interpretations of correct mutations. Rollback was therefore not invoked,
and the journal's rollback manifest (9 entries, emitted in apply order rather than reversed,
with the exact restorable ACL payload travelling with the `REMOVE_EXTENDED_ACL` operation)
remains unused.

```text
ROLLBACK_REQUIRED=NO   ROLLBACK_EXECUTED=NO
```

## 7. Sequence and precondition semantics — contract coherence

The execution surfaced a real ambiguity, recorded here rather than left implicit.

The planner gives every operation on one path the **same** plan-time `pre` snapshot, while an
earlier authorized operation on that path necessarily changes metadata before a later one
runs. Read maximally — "each later operation must match the full original uid/gid/mode
snapshot" — the contract would forbid the very multi-operation plans it prescribes, since
`CHOWN`, `REMOVE_EXTENDED_ACL` and `CHMOD` are emitted together for exactly this defect shape.

The canonical machine semantics do not read it that way, and say so explicitly:

- every emitted operation carries
  `path_resolution_rule = "re-open with O_NOFOLLOW and verify dev/ino match \`pre\` before applying; abort on mismatch"` —
  the apply-time binding is **object identity**, not the full metadata snapshot;
- the contract's Mutation section restates the same binding: operations are applied "after
  re-opening it with `O_NOFOLLOW` and re-verifying that **device/inode** still match the plan's
  `pre` state";
- the group's `post` is marked `mode_applied_last=true` with `mode_source=CONTRACT_POSTCONDITION`,
  so final postconditions are sequence-aware by construction;
- `acl_mask_caveat` and the `REMOVE_EXTENDED_ACL` source comment name the expected intermediate
  metadata and its ordering consequence;
- the unit suite asserts that every emitted `CHMOD` must name the contract's own postcondition
  mode and that ranks are ordered `CHOWN(0) -> REMOVE_EXTENDED_ACL(1) -> CHMOD(2)` — i.e. the
  contract intends `CHMOD`s to be applied, not refused.

The plan in this execution was therefore executable without violating the contract's stated
preconditions, and all 9 postconditions were met. The two halts were executor verification
errors against an over-strict reading of a general anti-drift sentence, **not** contract
violations.

```text
SEQUENCE_PRECONDITION_CONTRACT_COHERENT=YES
INTERNAL_CONTRADICTION_FOUND=NO
```

**Recorded documentation finding (non-blocking).** The Mutation section's general sentence —
"An operation whose `pre` observation no longer matches at apply time aborts the procedure
rather than being forced" — is ambiguous in scope: its antecedent could be the whole `pre`
record rather than the device/inode binding named in the sentence immediately before it. That
ambiguity demonstrably cost two halts. This closeout does **not** edit that sentence: it is the
standard being adjudicated here, and tightening it is a change to the contract's normative
mutation semantics. It is recommended as a separate, narrowly scoped contract-clarification
mission if the Execution Controller wants the prose to state the binding as explicitly as the
machine-readable `path_resolution_rule` already does.

The contract's **normative** content is therefore unchanged by this PR: the mutation class,
the content-write and recursive-operation prohibitions, the allowed operation classes, the
`CHOWN` → `REMOVE_EXTENDED_ACL` → `CHMOD` ordering and its rollback ordering, the three-role
identity model, the apply-time binding and the executor policy are all byte-identical. One
thing in that file *was* corrected, and it is not normative: see section 13.

## 8. Content immutability — 9/9

```text
PRE_COUNT=9   POST_COUNT=9   PRE_SET_EQUALS_POST_SET=YES
REQUEST_ACCOUNTING_EPOCH_INCLUDED=YES
PRE_CONTENT_SET_SHA256 =78129f71e60a3a08fbd42db8cd6d3b66831d136f730f5ec56fcd15cbedf7d359
POST_CONTENT_SET_SHA256=78129f71e60a3a08fbd42db8cd6d3b66831d136f730f5ec56fcd15cbedf7d359
CONTENT_MANIFEST_DIFF_COUNT=0   CONTENT_BYTES_BEFORE_EQUALS_AFTER=YES
```

The certified set is the plan's own — all 9 governed `content_bearing=true` artifacts,
including `REQUEST_ACCOUNTING_EPOCH.json`. Pre-repair evidence was 3 ×
`ORDINARY_RUNTIME_READ` + 6 × `PRIVILEGED_READ_ONLY_EVIDENCE` (the six package files were
`EACCES` to the runtime identity, which is the defect being repaired). Post-repair, all 9 are
`ORDINARY_RUNTIME_READ` with `privileged_post_read_used=NO`: the proof requires no privileged
read at all. Per-artifact `PRE_SHA256 == POST_SHA256` for all 9, and `dev`/`ino` are unchanged
for all 9, so the same inodes were read before and after.

## 9. Authority identity proof — ordinary runtime only

```text
PROCESS_1_COLD_LOAD=SUCCESS                     PROCESS_2_COLD_LOAD=SUCCESS
TRANSACTION_HEAD=tx_0ba8d4ad78aef57d1bbadf6637198b08d9586c5debf3e343d07033ed98a6bb64
STATE_HASH=df5084b6d752d698bfde4646fb508f3a41396f160fbee3cca9ee1b3b412e5ddd
OBSERVATION_COUNT=903
STORE_SHA256=ed014a6f151143aa30cefcebc47374059aa18c38a83560610571331a665199e4
ALLOCATION_AUTHORITY_SHA256=89e4276c8fe637318339821fe40d783d2f7fd8de65f6fc593b2035bd9445dad3
```

Both proofs come from the ordinary target runtime identity (uid/gid 1000), never from
escalation — `evidence_for_declared_runtime_identity=true`, supplementary groups included.
Process 1 is the post-repair audit; process 2 is an independent fresh-process invocation.
Before the repair this same cold-load failed `COLD_LOAD_FAILED` / `EACCES` on
`identity_decisions.jsonl`.

> The store hash literal in an earlier Controller mission prompt was malformed — 62 hex
> characters, dropping `c` at index 21. That is a prompt-transcription defect only:
> `MISSION_STORE_HASH_LITERAL_ERROR=YES`, `PRODUCTION_STORE_HASH_ERROR=NO`. The 64-character
> value above is the correct one and matches the accepted baseline.

Historical accounting is preserved verbatim and not reinterpreted:
`REQUEST_ACCOUNTING_PRE_EPOCH_LOWER_BOUND=AT_LEAST_2_CONFIRMED`,
`REQUEST_ACCOUNTING_PRE_EPOCH_EXACT_TOTAL=UNKNOWN`.

## 10. Post state

```text
POST_AUDIT_STATUS=COMPLIANT   POST_VIOLATIONS=0   POST_AMBIGUOUS=0
POST_PLAN_STATUS=NOT_REQUIRED  POST_PLANNED_OPERATIONS=0  POST_BLOCKED_OPERATIONS=0
```

A fresh read-only canonical audit taken after this closeout — ordinary runtime identity only,
no privilege — reproduced `COMPLIANT`, `PLAN_STATUS=NOT_REQUIRED`, `0` violations, `0`
operations, the cold-load head/state/903 and both artifact hashes. The zero-operation post-plan
is the controlling reason no ninth `CHMOD` may be executed now.

Safety: no provider request, no quota consumption, no Stage D start, no scheduler change, no
canonical transaction created, no content written, no Blocker #3 work, no repository change
during the remediation.

## 11. Acceptance and the no-precedent rule

```text
CLOSEOUT_VERDICT=ACCEPTED_WITH_DOCUMENTED_EXECUTION_DEVIATION
DEVIATION_REQUIRES_PRODUCTION_RETRY=NO
DEVIATION_REQUIRES_ROLLBACK=NO
DEVIATION_REQUIRES_GRATUITOUS_CHMOD=NO
BLOCKER_2_HOST_EVIDENCE=ACCEPTED_COMPLETE
BLOCKER_2=CLOSED
```

**No precedent.** Accepting 8 executed operations plus 1 planned `CHMOD` already satisfied by
the authorized preceding ACL removal is a historical adjudication of **this exact evidence
set**. It does **not** modify the canonical future execution policy, and it does **not**
authorize a future executor to skip a planner operation because it believes that operation's
postcondition is already satisfied. Any future equivalent case must follow the then-current
canonical contract or obtain separate authorization. The planner's ordering invariant
(`CHOWN` → `REMOVE_EXTENDED_ACL` → `CHMOD`, rollback in the same order) is unchanged.

## 12. State after closeout

```text
BLOCKER_2_PRODUCTION_REMEDIATION=EXECUTED_AND_VERIFIED
BLOCKER_2_RUNTIME_PERMISSION_CONTRACT=COMPLIANT
BLOCKER_2_CONTENT_IMMUTABILITY=PASS
BLOCKER_2_AUTHORITY_IDENTITY_PRESERVED=PASS
BLOCKER_2_ORDINARY_RUNTIME_COLD_LOAD=PASS
BLOCKER_2_FRESH_PROCESS_PROOF=PASS
BLOCKER_2_POST_REPAIR_PLAN=NOT_REQUIRED
PHASE_B_CLOSEOUT=ACCEPTED_WITH_DOCUMENTED_EXECUTION_DEVIATION
BLOCKER_2=CLOSED      PHASE_B_COMPLETE=YES
BLOCKER_3=OPEN        GATE_2=NOT_ACCEPTED      GATE_3=NOT_AUTHORIZED
```

Gate 2 remains `NOT_ACCEPTED` and Gate 3 remains `NOT_AUTHORIZED` because **Blocker #3 is
still open**: the existing authority and evidence paths sit on the same physical failure
domain. This closeout does not select a backup target, copy data, perform a restore, or change
retention/RPO/RTO. Stage D has not started: no provider request, no quota consumption, no
scheduler enablement, no canonical transaction.

## 13. Independent review finding — stale contract status corrected

The independent Codex review of this closeout returned one blocking `P1` with `P0=0`, `P2=0`,
`P3=0`: the canonical
[`STAGE_D_CONTINUOUS_OPERATIONS_CONTRACT.md`](STAGE_D_CONTINUOUS_OPERATIONS_CONTRACT.md) — the
normative source for any future controlled host procedure — still declared
`BLOCKER_2_PRODUCTION_REMEDIATION=NOT_EXECUTED` / `BLOCKER_2=OPEN`, and still carried a heading
stating Phase B was "not executed, not authorized". The reviewer's hazard is concrete: a
future executor reading that contract would see the completed metadata repair as pending work
and could re-run privileged mutation against the production authority.

The finding is correct, and it is a **stale current-state claim**, not a defect in normative
logic. The contract itself declares `lifecycle: current-state contract`, and no source file,
test, schema or gate asserts on those literals — the only other occurrence in the repository is
inside a superseded mission-scope record. Correcting it therefore required no machine-logic
change.

What changed in that file: the two stale state paragraphs are marked historical/superseded and
a current-status block replaces the stale claim; the section heading no longer says the
procedure was never executed; and the statement that the historical execution's authorizations
are **spent** was added explicitly alongside the unchanged
`PHASE_B_EXECUTION_AUTHORIZED=NO`. What did **not** change: the mutation class, the
content-write and recursive-operation prohibitions, the allowed operation classes, the
`CHOWN` → `REMOVE_EXTENDED_ACL` → `CHMOD` ordering and its rollback ordering, the three-role
identity model, the executor policy, the apply-time binding, and the no-precedent rule. The
status block was corrected to match the closeout, exactly as the other three current-state
documents were.

```text
REVIEW_P1_HAZARD=STALE_CONTRACT_STATUS_CLAIM
REVIEW_P1_REQUIRED_MACHINE_LOGIC_CHANGE=NO
REVIEW_P1_RESOLUTION=CURRENT_STATE_CORRECTED_NORMATIVE_SEMANTICS_UNCHANGED
PHASE_B_EXECUTION_AUTHORIZED=NO
```

Because the audited text is the contract that governs privileged production mutation, this
correction is confined to state claims; the normative prose ambiguity recorded in section 7
remains open and is still recommended for its own narrowly scoped mission.
