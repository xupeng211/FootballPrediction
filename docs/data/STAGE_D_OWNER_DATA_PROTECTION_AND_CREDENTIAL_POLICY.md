# Stage D Owner data-protection, retention/RPO/RTO and credential-rotation policy

> lifecycle: current-state record
>
> 状态：`RETENTION_POLICY_APPROVED=YES`、`CREDENTIAL_ROTATION_COMPLETED=YES`、`BLOCKER_3=CLOSED`、
> `GATE_2=ACCEPTED`、`GATE_3=NOT_AUTHORIZED`、`STAGE_D_STARTED=NO`。

This document records a project-Owner governance decision: the Stage D data-protection policy
(retention, RPO, RTO) and the rotation of the previously exposed The Odds API provider
credential. It records a decision the Owner has already taken and already declared complete.

It does **not** authorize Gate 3, and it changes no technical capability. Nothing here authorizes
a Stage D start, a provider request, a quota-consuming probe, a scheduler change, a backup
generation, a remote write or any production mutation.

## 1. Authorization and base revision

| Field | Value |
| --- | --- |
| Owner decision | `OWNER_DECISION=STAGE_D_RETENTION_RPO_RTO_APPROVAL` |
| Owner adjudication | `RETENTION_POLICY_APPROVED=YES`, `RPO_APPROVED=24_HOURS`, `RTO_APPROVED=24_HOURS`, `CREDENTIAL_ROTATION_COMPLETED=YES` |
| Canonical status | `OWNER_APPROVES_THIS_POLICY_AS_CANONICAL_STAGE_D_GOVERNANCE=YES` |
| Authorizing main | `c2abf1ce74426b476447ce461450bde0076b74c7` |
| Recorded at | `2026-09-16` |
| Decision kind | Owner policy approval — no code, schema, config or runtime change |

The Owner decision was issued directly as project governance. It is not derived from, and does
not re-derive, any technical proof in this repository. The record exists so that the canonical
current-state documents stop describing these two items as outstanding.

## 2. Approved retention policy

| Field | Approved value |
| --- | --- |
| `RAW_RETENTION` | `LONG_TERM_NO_ROUTINE_DELETION` |
| `PRIMARY_DATA_RETENTION` | `LONG_TERM` |
| `INDEPENDENT_BACKUP_RETENTION_MINIMUM` | `180_DAYS` |
| `MINIMUM_RECENT_SUCCESSFUL_BACKUP_GENERATIONS` | `30` |

Accepted Stage D RAW provider responses are durable project data assets and must not be routinely
deleted. Deletion requires a separate explicit Owner authorization or a documented legal/security
requirement.

This is a policy approval. It provisions nothing, creates no backup target, writes no backup
generation and configures no bucket lock or lifecycle rule. The backup tooling admitted by
Blocker #3 remains explicit-invocation only and is still not wired into publication, scheduler,
controlled initialization, cycle or transaction commit.

## 3. Approved recovery objectives

| Field | Approved value | Interpretation |
| --- | --- | --- |
| `RPO_APPROVED` | `24_HOURS` | A recoverable failure should not result in the loss of more than 24 hours of accepted Stage D data under normal operation. |
| `RTO_APPROVED` | `24_HOURS` | After a recoverable infrastructure or storage failure, the operational objective is to restore the Stage D data path to a verified usable state within 24 hours. |

These are operational objectives approved by the Owner. They are **not** a claim that either
objective has been demonstrated, measured or exercised. No recovery drill has been run against
these numbers at the time of writing, and none is authorized by this record.

Two boundary notes, recorded rather than left to inference:

- **`RTO` moved, and not by silent restatement.** The Stage D operations contract previously
  carried an unapproved proposal of `RPO <= 24h`, `RTO <= 4h`
  ([`STAGE_D_CONTINUOUS_OPERATIONS_CONTRACT.md`](STAGE_D_CONTINUOUS_OPERATIONS_CONTRACT.md)). The
  approved `RPO` agrees with that proposal; the approved `RTO` does not. The Owner approved
  **24 hours** where the contract proposed 4. `RTO_APPROVED=24_HOURS` is therefore the binding
  objective and the proposed `RTO <= 4h` is superseded. Operational log retention, the third item
  in that proposal, was **not** addressed by this approval and remains unapproved.
- **`POLICY_B` is a different and stricter claim, and it is not approved by this record.**
  `POLICY_B_STATUS=PROPOSED_NOT_APPROVED` / `RPO_ZERO_COMMITTED_TRANSACTIONS=NOT_YET_ENFORCED`
  appears in the current-state documents and stays exactly as it is. Policy B commits to an `RPO`
  of **zero** for committed transactions; the Owner approved an `RPO` of 24 hours. A 24-hour
  objective does not satisfy, approve or enforce a zero-loss objective, and this record must never
  be read as doing so.

## 4. Credential rotation policy

| Field | Value |
| --- | --- |
| `CREDENTIAL_ROTATION_COMPLETED` | `YES` |
| `THE_ODDS_API_REPLACEMENT_CREDENTIAL_PRESENT_LOCALLY` | `YES` |
| `OLD_CREDENTIAL_USABLE_FOR_FUTURE_LIVE_REQUEST` | `NO` |

The previously exposed The Odds API credential has been rotated by the Owner. The old credential
must not be used for any future live request. The replacement credential is held in the approved
local secret environment and must never be printed, committed, logged, copied into evidence
artifacts, PR bodies, chat messages or repository files.

That the replacement credential exists **only** there is the Owner's declaration, restated here
rather than independently established. §5 corroborates the narrower facts — the credential is
declared, it is not exported into this session's shell environment, and its secret file is
owner-only, gitignored and was never added to the repository — and nothing in this record could
exclude a copy held outside this host, for example in a provider dashboard or a password manager.
No such exclusivity is claimed on this record's own evidence.

This record intentionally contains **no credential value, no prefix, no length and no hash** of
either the old or the replacement credential. Rotation is asserted by the Owner and corroborated
by the metadata evidence in §5; it is not asserted here on the basis of having read any secret.

## 5. Read-only verification performed while writing this record

The checks below were performed without reading, comparing, hashing, measuring or otherwise
processing the value of either credential. Every method below matches a variable **name** or a
line of a file; no method ever places a credential value in a pipeline, a comparison, a command
argument or an output. Every result is a boolean, a filesystem timestamp or a filesystem mode.

The filesystem observations were taken on the Owner's workstation, outside the repository tree
that carries this record. They are properties of that host's local secret file and are **not**
re-derivable from this repository; only the two `git` checks are.

| Check | Method | Result |
| --- | --- | --- |
| Replacement credential is declared | match the variable **name** in that host's approved local `.env`, counting matching lines only | `API_KEY_DECLARED=YES` |
| Credential not exported into the shell environment | match the variable **name** across this session's environment, counting matching names only | `API_KEY_IN_SHELL_ENV=NO` |
| Secret-file protections as observed | `stat` on that host's local secret file, plus `git check-ignore -v .env` in this repository | mode `0600`, owner-only; `.env` matched by `.gitignore:33` |
| That secret file's mtime advanced after the Owner declared rotation complete | `stat` mtime, observed twice in the same session on that host | `2026-09-06 01:06` → `2026-09-16 08:25:38 +0800` |
| No commit on any ref ever added the approved secret file path | `git log --all --diff-filter=A -- .env` | no such commit |

Stated as limits rather than left to inference, because the boundary is exactly what makes this
record honest:

- **Presence of the declaration is established; the value's shape is not.** Whether the value is
  non-empty, and whether it has any particular length, prefix or hash, is **not** established by
  this record and is not claimed anywhere in it. Establishing any of those would require reading
  the value, which this mission's scope forbids.
- **No value-based leak scan was performed and none is claimed.** Establishing that the credential
  value appears in no tracked file requires the value itself in the search pipeline, which is the
  prohibited operation. What is established instead is narrower and stated as such: the approved
  secret file is gitignored, and no commit on any ref ever added that path. It does not establish
  that the value appears nowhere else in history, which is exactly what a value-based scan would
  be needed to show. A value-based leak scan remains a reasonable
  separate task under its own authorization, and its absence is a gap in this record, not a
  passed check.
- **The mtime advance is the strongest corroboration available, and it is still only about a
  file.** It was observed on that host, moving from a timestamp before the Owner declared rotation
  complete to one after. An mtime records that a file was written; it does not record what was
  written, so it corroborates the Owner's declaration without proving it. Neither timestamp is
  re-derivable from this repository.

Rotation is therefore recorded as **Owner-attested and metadata-corroborated**. This record does
not claim an independent value-level proof, and §4 makes no claim about provider-side revocation
beyond the Owner's statement that the old credential must not be used.

No provider endpoint was contacted for any of these checks, and no quota was consumed.

## 6. What this changes, and what it does not

Preserved exactly, unchanged by this record:

```text
BLOCKER_3=CLOSED
GATE_2=ACCEPTED
GATE_3=NOT_AUTHORIZED
STAGE_D_STARTED=NO
```

Also unchanged: `CONTINUOUS_CAPTURE_READY=NO`, `STAGE_D_BINDER_AUTHORIZATION=NO`,
`STAGE_D_PROVIDER_QUOTA_EVIDENCE=CLOSED_CONFIGURATION_ONLY`, `THE_ODDS_API_CONTACTED=NO`, and the
live executor's disabled-by-default state.

This record consumes no quota and certainly reaches no provider: nothing in §5 touched a network
endpoint, and the request-accounting epoch is unchanged by it. The epoch's own consumed-request
count is production ledger state living at an operator-supplied root with no canonical default
path, so it is **not** re-measured here and this record makes no claim about its current value;
the last recorded value is inherited from the accepted closure, not re-derived.

Resolved by this record — the Owner-governance prerequisites that the canonical documents still
listed as outstanding: credential rotation, and the approval of retention / RPO / RTO. Together
with `BLOCKER_3=CLOSED` and `GATE_2=ACCEPTED`, this completes the Owner-confirmation set that the
Stage C pilot record enumerates as preceding any separate authorization of a bounded live
preflight.

## 7. What this record does not establish

- It does not authorize Gate 3. `GATE_3` stays `NOT_AUTHORIZED`; whether the prerequisites justify
  authorizing exactly one real The Odds API request remains a separate Controller decision that
  this record neither pre-empts nor predicts.
- It does not demonstrate that the approved RPO or RTO are achievable. They are objectives, not
  measured results.
- It does not provision, configure or verify any backup target, retention rule, lifecycle policy
  or bucket lock. The off-host target the accepted Blocker #3 closure already established is
  unaffected by this record, which neither configures it further nor claims to have verified it.
- It does not assert that a historical credential has been erased from any system outside the
  approved local secret environment, and it makes no claim about provider-side revocation beyond
  the Owner's statement that the old credential must not be used.
- **It does not by itself make every current-state document coherent.** One further current-state
  contract, [`STAGE_D_BLOCKER_3_BACKUP_TOOLING_CONTRACT.md`](STAGE_D_BLOCKER_3_BACKUP_TOOLING_CONTRACT.md),
  still carries a `## RPO/RTO policy — one proposal, deliberately unapproved` section whose
  "Proposal A (uniform `RPO <= 24h`) remains the fallback" line, and a header status stating that
  no target exists, are both superseded by this approval and by the accepted Blocker #3 closure.
  That file is outside this mission's authorized paths, so it is reported here rather than edited.
  It is a documentation-coherence residual: it changes no state token, `GATE_3` included.

Related: [`STAGE_D_BLOCKER_3_CLOSEOUT.md`](STAGE_D_BLOCKER_3_CLOSEOUT.md),
[`STAGE_C_CANONICAL_MARKET_EVIDENCE_PILOT.md`](STAGE_C_CANONICAL_MARKET_EVIDENCE_PILOT.md),
[`../PROJECT_STATUS.md`](../PROJECT_STATUS.md), [`../ACTIVE_MILESTONE.md`](../ACTIVE_MILESTONE.md).
