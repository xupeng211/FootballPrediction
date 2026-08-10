<!-- markdownlint-disable MD013 -->

# FotMob Current State

- lifecycle: current-state
- owner: data / ingestion workflow
- update rule: update when ingestion state, blockers, active guards, or next step changes
- do not use historical ADG reports as the primary current truth
- retained raw storage state and historical audit scope are recorded below and
  in `docs/data/FOTMOB_RETAINED_RAW_STAGE_STATUS.md`

## Current authoritative status — 2026-08-11 (post-GDI1C FotMob 888 closeout)

```text
Official Architecture Decision Gate direction = redo source inventory strategy
Implementation approach = RECOVER_EXISTING_ACQUISITION_ARCHITECTURE
Evidence-backed outcome = FOTMOB_IDENTITY_BASELINE_REUSE_RECOMMENDED
PR #1819 baseline main at reconciliation =
  d3bcf3f158463b8c0c66cd03e46676b94586d4a5 (historical baseline of the #1819
  feature branch — not a claim about what main is after any merge)
Bounded transport-phase observability = implemented and tested in this
  repository revision via PR #1819 (branch fix/fotmob-detail-transport-
  observability; 30 s timeout unchanged, retry 0, redirect manual; telemetry
  persists NO payload/credentials; distinguishes waiting-headers vs
  reading-body; cannot distinguish DNS/TCP/TLS; diagnostic/audit observability
  — not a capture authorization; 4193752/4506625 NOT re-requested; five-match
  real trial stays 3/5; 16-match / DB / training remain not authorized)
V2 provenance exporter = implemented (canonical-inventory-artifact/v2, status-complete, raw retention)
  (PR #1813, merged)
FOTMOB_REAL_CAPTURE_READINESS Phase A code hardening = implemented and tested
  (malformed reason.short fail closed; started+postponed contradiction fail closed;
   core-layer 40-hex collector_code_revision enforcement in buildCaptureManifest)
Bounded auditable detail capture pipeline = implemented, tested, MERGED
  (PR #1816, squash merge b6f9f385124eab7476157777517fcd5bf01a93ab, 2026-08-04;
   PLAN / PREFLIGHT / CAPTURE / REPLAY; see "Detail capture pipeline" below)
Offline detail staging converter / validator = implemented, tested, MERGED
  (PR #1817, squash merge fd60117d283a2af9e103990f733e436fda53b100, 2026-08-06;
   post-merge main Production Gate run 31075669344 = SUCCESS;
   see "Offline detail staging converter / validator" below)
Chain available on main = PLAN → PREFLIGHT → bounded CAPTURE → REPLAY →
  verified archive/receipt → offline staging conversion → append-only retention →
  full validator
Real FotMob detail capture for the frozen 888 population = COMPLETE
  (2026-08-10/11, GDI1C: 14 formal batches, 812 unique targets, 888 raw frozen;
  ACQUISITION_NETWORK_PHASE=CLOSED; see "FotMob 888 raw acquisition closeout" below)
NEW FotMob capture is NOT the current next step
  (NEW_FOTMOB_CAPTURE_IS_NOT_CURRENT_NEXT_STEP=YES): the CAPTURE entrypoint
  remains default-off, and any capture beyond the frozen population requires
  NEW explicit user authorization; do not start automatically
Public terms / usage-boundary review = completed
FotMob written permission = absent (no written permission granted)
Bounded two-path compatibility probe = completed
  (actual probe requests = 2; match detail route = compatible at probe time;
   EPL fixtures route = compatible at probe time; no access-control signal
   observed in that bounded probe)
Batch capture executed = 14 formal batches / 812 unique targets (frozen 888
  population; no 1,140-match capture; no database write)
Not occurred since the frozen 888 acquisition: no NEW capture beyond the frozen
  population, no business database write, no migration, no canonical linkage
  write, no training, no backtest, no prediction
SC-002 = SC_002_ENFORCEMENT_INFRASTRUCTURE=COMPLETE /
  SC_002_STAGING_PRODUCTION_ROLE_DEPLOYMENT=PENDING / PR1817_CHANGES_SC002=NO
Issue #1793 (M3 historical odds staging and import foundation) = remains OPEN
This repository state executes zero real network requests
  (the probe's 2 requests were a separate authorized one-time action; no code
   path in this state performs live fetches)
Known remaining stale SC-002 wording surfaces NOT modified by PR #1818
  (NON-EXHAUSTIVE inventory — every listed entry verified; surfaces are out of
  authorized scope for PR #1818, owner-authorized follow-up required;
  dated historical reports under docs/_reports/ are excluded as time-accurate
  records, e.g. docs/_reports/db_write_guard_static_enforcement_dry_run_20260621.md:142) =
  CLAUDE.md:62, .github/pull_request_template.md:127,
  scripts/ops/helpers/agent_workflow_hardening_checks.py:175,
  scripts/ops/helpers/python_db_write_enforcement_check.py:68,178,
  scripts/ops/helpers/sql_migration_policy_enforcement_check.py:94,125,
  config/python_db_write_allowlist.json, config/sql_migration_policy_allowlist.json,
  docs/SC002_CLOSURE_PLAN.md:10,62,118,393-394,432,444,471,510,523,537,561,592,
  631,661,689,715,737,756,780,796,798,832,866,892,956,967,972
  (393-394 repeats the superseded "Python/SQL/migration enforcement not yet
  designed"; 956/967/972 Status Wording Rules still mandate "partial mitigation
  only" and forbid "complete" — conflicts with the adopted
  SC_002_ENFORCEMENT_INFRASTRUCTURE=COMPLETE layer), docs/CODEX_WORKFLOW.md:259,
  docs/SC002_BROWSER_FOTMOB_PAGEPROPS_AUDIT.md:38,324,406,
  docs/SC002_BROWSER_FOTMOB_PAGEPROPS_PLAYWRIGHT_DEEP_AUDIT.md:8,430,
  docs/SC002_SHARED_MODULE_DB_WRITE_BOUNDARY_DESIGN.md:393,410,
  docs/SC002_MANUAL_REVIEW_PHASE1.md:422,441 (422 states "Python/SQL/migration
  enforcement not yet designed" — superseded: ai_workflow_gate.py runs
  PYTHON-DB-WRITE and SQL-MIGRATION checks),
  docs/SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md:70,71,132,678,
  docs/SC002_PHASE2C_REMAINING_CONFIRMED_WRITE_PATHS_DESIGN.md:26,330,
  docs/SC002_RUNTIME_DB_ROLE_PERMISSION_REVIEW_PHASE1.md:8,
  docs/SC002_ALEMBIC_MIGRATION_GUARD_DESIGN.md:52,566,606,
  docs/SC002_INDIRECT_WRITE_PATH_DESIGN_PHASE1.md:251,258,
  docs/SC002_MANUAL_REVIEW_PHASE2D.md:119,
  docs/SC002_OVERALL_CLOSURE_ASSESSMENT.md:344,
  docs/SC002_CONSUMER_LEVEL_GUARD_AUDIT_DB_POOL_SYNC_SQL_STORE.md:177,
  docs/SC002_FINAL_CLOSURE_CHECK.md:207 (references PROJECT_STATUS wording,
  superseded by the PROJECT_STATUS correction in this PR),

  tests asserting the stale allowlist/doc wording:
  tests/unit/test_sc002_alembic_migration_runtime_guard.py:241-245,
  tests/unit/test_sc002_alembic_migration_guard_design.py:299-302,
  tests/unit/test_runtime_db_role_permission_dev_poc.py:352-355,419-424,
  tests/unit/test_manual_review_phase2d.py:263-266,
  tests/unit/test_manual_review_guard_phase2e.py:183-185,
  tests/unit/test_runtime_db_role_permission_review_phase1.py:130-133,
  tests/unit/test_changed_files_negative_case_enforcement.py:668,
  tests/unit/gatekeeper_boundary_implementation_static.test.js:349-353,391-397,
  tests/unit/manual_review_phase1_static.test.js:179-183,320-328,
  tests/unit/python_sql_migration_enforcement_design_phase1_static.test.js:185-230,
  tests/unit/shared_module_db_write_boundary_design_phase1_static.test.js:101-105,160-161,197-217,
  tests/unit/shared_module_db_write_boundary_implementation_phase1_static.test.js:153-157,186-192,
  tests/unit/test_consumer_level_guard_audit_db_pool_sync_sql_store.py:140-142,
  tests/unit/test_indirect_write_path_design_phase1.py:167-170,
  tests/unit/test_indirect_write_path_guard_phase2.py:281-284,
  tests/unit/test_python_confirmed_write_paths_design_phase2c_batch4.py:305-307,376-381,
  tests/unit/test_sc002_alembic_migration_guard_design.py:186-189,
  tests/unit/test_sc002_browser_fotmob_pageprops_playwright_deep_audit.py:105-108,407-450,
  tests/unit/test_sc002_overall_closure_assessment.py:103-110
  (several of these tests enforce stale current-state semantics on
  PROJECT_STATUS/CLOSURE_PLAN wording and would fail once the two-layer
  wording is applied to those docs — owner decision required before touching
  those docs)
```

### FotMob 888 raw acquisition closeout — 2026-08-11

```text
FOTMOB_RAW_ACQUISITION_STATUS=COMPLETE
FROZEN_TARGET_POPULATION=888
RAW_COVERAGE=888/888
MISSING=0
EXTRA=0
AUTHORITATIVE_DUPLICATES=0
XG_FAMILY_RAW_VALIDITY=888/888
FULL_RAW_RETENTION=YES
ACQUISITION_NETWORK_PHASE=CLOSED
FOTMOB_888_RAW_ASSET_FROZEN=YES（immutable；不得编辑/重写/裁剪历史 raw）
GOLDEN_DATASET_COMPLETE=NO（FotMob raw 收齐 ≠ Golden Dataset 完成）
Asset snapshot（repo-external durable location，不在 Git 内）=
  ~/.claude/audits/footballprediction-fotmob-888-asset-preservation-closeout-20260811T030000Z/
  FOTMOB_RAW_ASSET_SNAPSHOT_ID=206c1f04ecef7ad6daefe7f362180cec0240f65351155e9fbb87ad8e4221a05a
  TARGET_POPULATION_HASH=133ff028406064de60ad1d871afe6e52c1ab8b964f0e3f63f9def41ada2c1a2b
  ASSET_MANIFEST_SHA256=67bbb64fd29957a79956808b7952c6cb2fee96360129854dc269a5824f6fc4db（JSONL）
Acquisition network totals（frozen ledger accounting）=
  UNIQUE_NETWORK_TARGETS=812 · SUCCESSFUL_HTTP_200=812 · INITIAL_TIMEOUT_FAILURES=2 ·
  RETRIES=2 · TOTAL_PHYSICAL_HTTP_ATTEMPTS=814
Formal batches = 14（B01-B14）· durable bundle+checkpoint 14/14 · PENDING=0
Historical reuse = 76（GDI1B 60 + pilot/trial 13 + trial_resumed 3，REUSE_CONFIRMED）
Redundant backup = PENDING_EXTERNAL_STORAGE（本机无独立存储设备；
  backup-ready snapshot 已生成：/home/xupeng/fotmob-888-raw-snapshot/<snapshot_id>/）
Known provenance tech debt = bundle-provenance.json collector_code_revision 为
  repo-external wrapper 模板常量 bf7f4974…（权威=per-run plan.json 40b4cc4de…，
  DATA_INTEGRITY_IMPACT=NO；DOCUMENTED_NOT_WORTH_PRODUCTIZING）
This repository state executes zero live FotMob network requests（本轮纯离线；
  812 次授权捕获发生于 2026-08-10/11，网络阶段已关闭）
```

### Detail capture pipeline

The bounded, auditable detail capture pipeline (`scripts/ops/fotmob_detail_capture.js`
plus `src/infrastructure/fotmob/FotMobDetailCapture{Plan,Pipeline,Retention,Contract}.js`)
connects the validated candidate artifact to an auditable four-stage flow. The
**canonical runtime entrypoints are the `make data-fotmob-detail-capture-*`
targets** (`-help` / `-plan` / `-preflight` / `-execute` / `-replay`); the direct
Node CLI (`scripts/ops/fotmob_detail_capture.js`) is the internal engine and is
marked as such — it is a specialized implementation detail, not the documented
canonical interface.

- **PLAN** — fully offline; builds a deterministic `fotmob-detail-capture-plan/v1`
  with `plan_business_sha256`; the hash is always RECOMPUTED from the business
  fields by the shared `validateAndRecomputeCapturePlan` contract (builder and
  CAPTURE validator use the same helper); explicit selection required
  (`--season` / `--match-id` / `--limit`), never silently selects the
  1,140-candidate population. A filter that matches NOTHING fails as an
  `INPUT_ERROR` (`selection matched no candidates (season filter (...) /
  match id filter (...)) — refusing to build an empty capture plan`), and
  the contract validator independently rejects zero-candidate plans
  (`candidates must not be empty`) — an empty plan can never pass PLAN /
  PREFLIGHT / CAPTURE gates, so EXECUTE can never report a zero-request
  run as `status=complete` (round-12 P2).
- **PREFLIGHT** — fully offline; re-validates the plan schema and recomputes the
  plan hash, verifies git revision / output paths / run id / budget /
  authorization variables, and prints the candidate count and URL-path summary.
  Creates nothing, fetches nothing, writes nothing.
- **CAPTURE** — default-off. Every authorization gate (`--execute`,
  `CONFIRM_REAL_FOTMOB_DETAIL_CAPTURE=1`, authorization id, expected-plan-sha256,
  max-requests + `CONFIRM_MAX_FOTMOB_REQUESTS`, clean git worktree, 40-hex HEAD,
  repository-external non-symlink output root, non-symlink plan, safe run id) is
  validated before any network call; the make `-execute` target fails in make
  before Node when any variable is missing. Single allowed URL
  `https://www.fotmob.com/match/<digits>` (GET, no redirect follow, no
  cookie/auth/proxy/browser, concurrency 1, retry 0, delay ≥ 60 s, 30 s timeout);
  19 content-validity gates (incl. trusted observed-match-id provenance and
  conflict detection) fail closed on empty SSR shells and untrusted identities.
  The observed match id is extracted from the RAW hydration BEFORE the
  transformer runs (allowlist: raw `pageProps.general.matchId` →
  `general.matchId`, raw `pageProps.matchId` → `matchId`); the transformer-
  injected `payload.matchId` (a copy of the request-side id) is NEVER trusted
  (R3-P1), the provenance flag `observed_match_id_is_response_derived` is
  recorded, and an input fallback always fails closed. Team markers are
  verified against the parser's EXACT ordered fallback chain
  (`general.<side>Team.name` → `header.teams[0|1].name` →
  `content.lineup.<side>Team.name` → `general.<side>Team.shortName`,
  mirroring `FotMobRawParser.extractTeams()`): the first name the
  parser will emit for each side must equal the expected team, and
  incomplete markers fail closed — a page with the right match id but
  REVERSED or misplaced home/away names can no longer pass the loose
  anywhere-in-text check and persist swapped teams (round-13 P2).
  Selection mirrors `FotMobRawParser.firstValue()` EXACTLY (round-14 P2):
  only undefined / null / the exact empty string are skipped — a
  whitespace-only `general.<side>Team.name` IS what the parser selects
  and persists, so the gate selects it too and fails the normalized
  comparison instead of silently skipping to a lower source. The collector HEAD must
  equal the plan's `generator_code_revision` (`PLAN_REVISION_HEAD_MISMATCH`
  otherwise, before any fetch or run-state write). Retention is
  a **stable allowlisted payload** (`<ordinal>-<source_match_id>.payload.json`,
  schema `fotmob-match-detail-capture-payload/v1`, business hash built by the
  shared `computeStableCapturePayloadSha256` projection) + manifest paired
  atomically with rollback/readback; the full HTML response body exists only in
  memory (hashed for audit, never persisted — no `.html` files, no
  `__NEXT_DATA__` / `pageProps` / `raw_data` in outputs). Manifest self-hash is
  required and recomputed; a run-bound immutable plan snapshot
  (`<run-dir>/plan.json`) is written before any network request; resume binds
  run id / plan SHA / source artifact SHA / authorization id / budget / delay /
  collector revision and every completed pair field-by-field (cross-run pairs
  are `RESUME_PAIR_CONTEXT_MISMATCH`, never completed); attempted / response /
  capture counters accumulate INDEPENDENTLY (a timeout or 403 is a response but
  never a completion; resume never infers responses from attempts — R3-P2-4);
  the run-state contract (`fotmob-detail-capture-run-state/v1`) records
  `network_requests_attempted`, `network_responses_received`,
  `captures_completed`, `completed_ordinals`,
  `last_network_request_attempted_at` (persisted before each native fetch —
  the inter-request delay continues across processes: remainingDelay =
  delayMs − (now − lastRequestAt); an invalid or missing timestamp with
  attempts fails closed, a backwards clock waits the full delay — R3-P2-5;
  the pacing ANCHOR is the ACTUAL fetch-start moment: the adapter re-takes
  it AFTER the pre-fetch callback (and its synchronous run-state write)
  completes, and the callback re-takes and persists a post-write
  crash-window value (one follow-up write); the ADAPTER's true fetch-start
  moment is what the manifest records, and the pipeline ACTUALIZES the
  persisted `last_network_request_attempted_at` to that same moment after
  the request settles (completion and failure paths — the failure path
  gets the moment from the thrown error) — so the anchor, the manifest and
  the cross-process resume seed all agree on the REAL request start,
  covering the last pre-fetch write's duration — a slower first write used
  to shrink the real gap between two request starts below delayMs, risking
  server rate limiting (round-16 P2, round-17 P2, round-18 P2). In addition,
  every pre-fetch run-state write refreshes a persisted
  `next_allowed_request_at` DEADLINE (= the true fetch start + delayMs — the
  callback's crash-window value uses its post-write re-taken actualAt, the
  completion/failure writes actualize the deadline from the adapter's true
  fetch-start moment), and resume seeds its gate FROM the deadline
  (initialLastRequestAt = deadline − delayMs), so the persisted gate covers
  the LAST pre-fetch write's duration even when the run-state write itself
  is what a crash loses (round-18 P2; a present-but-invalid deadline fails
  closed, a missing deadline falls back to the timestamp formula). The
  deadline's basis (the last pre-fetch moment) still precedes the write
  that carries it by one write duration — a hard crash right after the
  fetch started, before ANY actualization write, leaves exactly that gap on
  disk — so the crash window is decided by a persisted `fetch_in_flight`
  MARKER instead: the last pre-fetch write sets it true, both actualization
  writes clear it in the same write as the settlement, and a true marker on
  disk means the prior process died with a request possibly in flight —
  resume then executes the FULL delay from the recovery moment (no
  assumption that the file mtime is the write's completion moment — the
  earlier mtime anchor was removed because temp+rename keeps the TEMP
  file's mtime on real filesystems, round-20 P2, R22-P1). ONLY an explicit
  `false` takes the exact deadline path; a MISSING marker — a legacy state
  left by `0bc69dad9` or earlier, whose process may have died in the crash
  window without any marker — is treated as a possible in-flight request
  and also waits the FULL delay from the recovery moment, and an explicit
  `null` fails closed like any other non-boolean (round-21 P2, R23-P1).
  The marker decision runs BEFORE the deadline branch: a state written
  before `05cd23c55` carries neither `next_allowed_request_at` nor the
  marker, and its missing marker still forces the full recovery delay —
  absence of the deadline never re-enables the possibly-early persisted
  timestamp (round-22 P2, R24-P1). When both the deadline and
  the persisted request time are present, the read-side validator AND the
  resume seeding enforce the exact invariant
  `next_allowed_request_at === last_network_request_attempted_at + delay_ms`
  — a syntactically valid but EARLY tampered deadline fails closed like any
  other deviation (round-19 P2, R21-P2) and
  is validated on every read (non-negative, monotonic, unique ordinals, no
  auto-fixing); attempted requests are counted before the fetch, so
  failed/timeout requests are never recorded as zero. On resume, a pair left
  on disk by a prior process that crashed between the pair write and the
  run-state update is counted as a completion, so the persisted
  `captures_completed` always equals `completed_ordinals.length` (round-2 P1);
  the authorization gate validates the authorization id with the SAME contract
  as the run-state validator, so an admitted id can never produce a record its
  own consumer rejects (round-2 P2); the manifest `request_attempted_at` is
  the ACTUAL attempt instant — recorded by the adapter's pre-fetch callback
  after any inter-request delay, immediately before the native request — and
  always equals the persisted run-state timestamp; the timestamp is taken ONCE
  per attempt and used for the run-state record, `updated_at` and the manifest
  alike, so a real clock can never diverge the three (round-2/round-3 P2). The
  manifest `stable_raw_payload_sha256` is the FETCHER's hash computed with the
  trusted response-derived identity (round-3 P2); resume RECOMPUTES the
  payload business hash with the shared projection before treating a pair as
  complete (`RESUME_PAIR_BUSINESS_HASH_MISMATCH` otherwise), and a completed
  ordinal whose pair files are missing fails closed (`resume_pair_absent`) —
  never a silent re-fetch that would corrupt the counters (round-3 P2). Resume
  also binds the payload's OWN identity — `source_match_id`, `candidate_id`
  and the full `observed_identity` block (match id, source, conflict flag,
  response-derived flag) — field-by-field to the verified manifest and requires
  a response-derived identity with no conflict, exactly like replay
  (`RESUME_PAIR_PAYLOAD_IDENTITY_MISMATCH` otherwise — round-3 P2). The capture
  output root must be an ABSOLUTE path: relative forms are rejected before any
  resolution, so `OUTPUT_ROOT=../../external/captures` can never be silently
  converted into a repository-external path whose meaning depends on the
  working directory (round-3 P2). Resume binds the pair to the FULL execution
  context, not only run/plan/candidate identity: manifest `request_budget`,
  `delay_ms` and `collector_code_revision` must equal the current run-state's
  values (`RESUME_PAIR_CONTEXT_MISMATCH` otherwise) — the plan business hash
  deliberately excludes the generator revision, so a complete pair copied from
  a prior run with different budget/delay/revision is never counted complete
  (round-4 P2). The PLAN validator cross-checks every candidate against the
  declared scope: candidate `competition` must equal the plan's declared
  competition and candidate `season` must be one of the declared
  `selected_seasons` — a self-consistent but out-of-scope plan (recomputed
  hash included) fails the CAPTURE gate (round-4 P2). The delay contract is
  enforced in the authorization gate BEFORE any directory creation,
  plan-snapshot or run-state write: `--delay-ms` below 60000, non-integer or
  NaN fails closed with the run directory never created — no poisoned
  run-state.json/plan.json can ever leave a RUN_ID unrecoverable (round-5 P2).
  The response body is read under a SIZE CAP: an over-limit Content-Length is
  rejected before any byte is read, a streamed body is aborted as soon as the
  cap (8 MiB) is exceeded, and a body without a stream is checked after the
  buffer read — an oversized response stops the run with
  `SAFETY_ERROR:oversized_response_body` before any pair is retained, so a
  single oversized page can never consume unbounded memory (round-8 P2).
  EVERY early-exit path releases the body: the over-limit DECLARED
  Content-Length branch now CANCELS the response body stream before throwing
  (round-15 P2), exactly like the chunked-read over-limit path — a server
  that keeps streaming or never closes the connection can no longer leave
  the socket owned by an unread response. A
  CROSS-PROCESS EXCLUSIVE LOCK guards every run id: an atomic mkdir lock
  recording the holder's pid is acquired BEFORE the run state is read and
  held until the final state write completes (released in `finally` on every
  path). A live holder stops the competing run with `SAFETY_ERROR` before
  any fetch or state write — two processes can never interleave state
  reads/writes for the same run id; a stale lock left by a dead pid is
  broken exactly once and retried (round-8 P1). The lock uses an ATOMIC
  OWNERSHIP TOKEN: the holder writes its pid into a private temp dir and
  renames the whole dir into place (rename is atomic) — a competing process
  can never observe a "live lock without an owner" (round-9 P1). Stale
  takeover unlinks only a verified-dead pid and rmdir's the now-empty dir:
  a COMPLETE lock (with a pid) is never deleted (rmdir fails ENOTEMPTY on a
  fresh lock), and the post-acquire ownership re-verification fails closed
  if the token was lost mid-takeover; release removes only the holder's own
  token (round-9 P1). The ownership token is NON-REUSABLE (`pid:<pid>:<nonce>`
  with a monotonic nonce, so an OS-pid-recycled process can never reproduce
  a dead holder's token), and takeover/release use ATOMIC rename-based
  grab/verify/restore: the lock dir is renamed to a private trash name,
  deleted ONLY if the moved dir still carries the exact token that was
  verified stale (or both absent), otherwise renamed back — a takeover or
  release can never delete a token it did not verify, so process C can never
  delete process B's lock (round-10 P1). The holder additionally RE-VERIFIES
  ownership of the token before EVERY run-state write
  (`verifyRunLockOwnership` → `SAFETY_ERROR:run lock ownership lost`): a
  holder displaced mid-run fails closed at its next state write, BEFORE its
  next fetch can issue — two processes can never both keep fetching under
  the same run id (round-10 P1). Liveness of a holder is judged by PROCESS
  INSTANCE, not by pid liveness alone: the token records the holder's
  kernel process-start identity (`/proc/<pid>/stat` field 22, clock ticks
  since boot) as `pid:<pid>:<startTicks>:<nonce>`, and the stale judge
  re-reads `/proc/<pid>/stat` — identical start ticks → the same instance
  still runs (live); different ticks → the recorded holder instance is GONE
  (its pid was recycled by an unrelated process, `kill(pid, 0)` alone would
  keep the lock alive forever) → the lock is stale and can be taken over;
  legacy tokens without start ticks fall back to pid-liveness (round-11 P2).
  PID EQUALITY IS NEVER TREATED AS TAKEABLE: a concurrent
  `executeCaptureRun()` in the SAME process (same pid, same start ticks,
  different nonce) is judged a LIVE holder by instance identity and fails
  closed — an in-process competitor can no longer steal a live lock and burn
  two real requests for one pair (round-14 P1).
- **REPLAY** — fully offline; validates the run plan snapshot (REQUIRED — missing
  snapshot fails closed), verifies payload file hash + manifest self-hash, and
  RECOMPUTES the payload business hash with the same shared projection used at
  capture time — a tampered normalized field fails closed even when the file
  hash and manifest self-hash were refreshed (R3-P2-1). The payload's observed
  identity (match id, source, conflict flag, response-derived flag) is bound
  field-by-field to the verified manifest and must be response-derived with no
  conflict (`REPLAY_PAYLOAD_OBSERVED_IDENTITY_MISMATCH` otherwise — round-2 P2).
  Every replayed pair must be bound to the run state's run id and authorization
  id (`REPLAY_PAIR_CONTEXT_MISMATCH` otherwise — R3-P2-2); replay is TWO-PHASE:
  every pair is validated and built BEFORE any artifact is written, so a
  mismatch on any later pair leaves zero artifacts on disk (round-2 P2); the
  parser code revision comes from the bound collector revision chain. The run
  summary keeps the FULL plan scope (`plan_candidate_count` from the verified
  plan, not the completed subset — R3-P2-6) and `parsed_at` is derived from the
  capture record — repeated replays are byte-identical. Candidate identity comes
  exclusively from the verified run plan snapshot, never from file names. The
  run directory itself must satisfy the same boundary as PLAN/CAPTURE outputs —
  absolute, repository-external, no symlink ancestors — before any replay read
  or write, so replay artifacts can never be materialized inside the
  repository (round-3 P2). Replay ALSO pre-checks every output target before
  materializing: each target must be absent or byte-identical to the
  deterministic artifact this replay would produce, so a conflicting target on
  a later pair fails closed with ZERO partial output — the zero-write guarantee
  now covers output conflicts, not only input mismatches (round-3 P2). The
  pre-check additionally requires every existing target to be a REGULAR file
  (lstat): a symlink to byte-identical content passes a content comparison but
  would be rejected by the materializer AFTER earlier artifacts were written,
  so non-regular targets fail closed in the pre-check itself (round-4 P2). The
  pair's ordinal is bound to the snapshot candidate: replay requires
  `planCandidate.ordinal === ordinal` — a copied pair replayed under a wrong
  ordinal (refreshed `request_ordinal` + self-hash) fails closed before any
  artifact, so the summary can never claim an ordinal the pair does not
  actually hold (round-4 P2). Replay also binds the pair to the FULL execution
  context recorded in the run state: manifest `request_budget`, `delay_ms` and
  `collector_code_revision` must equal the run state's values
  (`REPLAY_PAIR_CONTEXT_MISMATCH` / `REPLAY_PAIR_REVISION_MISMATCH`
  otherwise) — a pair captured under a different budget, delay or collector
  revision is never replayed, so artifacts never declare parser provenance of
  the wrong revision (round-4 P2). The run-summary target is part of the
  transactional materialization: `run-summary.json` is pre-checked BEFORE any
  artifact write (absent, or a regular file with byte-identical deterministic
  content; differing content or a directory/symlink fails closed) — the
  zero-write guarantee now covers the summary too (round-4 P2). The captures
  directory itself must be a REAL directory (lstat) with no symlink anywhere
  in its ancestor chain, verified BEFORE any existsSync / readdirSync / pair
  read — a completed run whose `captures/` was replaced by a symlink to
  another directory can never replay the link target's pairs as this run's
  retained evidence (round-5 P2). Replay ALSO binds the payload's complete
  PLAN identity — `competition`, `league_id`, `season` and `expected_identity`
  (home_team, away_team, kickoff_at) — field-by-field to the verified manifest
  AND the run plan snapshot before any artifact is built: a payload whose
  plan identity was swapped (with recomputed business hash and refreshed
  file/self hashes) fails closed with `REPLAY_PAYLOAD_PLAN_IDENTITY_MISMATCH`
  and zero artifacts, so a materialized artifact can never declare a plan
  identity different from the run's real plan (round-8 P2). Resume applies
  the same plan-identity binding: `payload.competition` / `league_id` /
  `season` / `expected_identity.*` must equal the manifest's declared values
  before a pair is treated as completed (`RESUME_PAIR_PAYLOAD_IDENTITY_MISMATCH`
  otherwise — round-8 P2). Resume binds the plan identity DIRECTLY to the
  current plan candidate, not only to the manifest: a tamperer who swaps the
  SAME identity fields in BOTH files (recomputing business/file/self hashes
  and keeping the original candidate_identity_sha256, which nothing
  recomputes from manifest fields) still fails closed — manifest AND payload
  `competition` / `league_id` / `season` / home/away/kickoff are each
  compared against `expectedCandidate` (round-9 P2). Replay binds `league_id`
  to the run plan's TOP-LEVEL league id in addition to the
  payload↔manifest comparison — a synchronized league swap in both files
  fails closed with `REPLAY_PAYLOAD_PLAN_IDENTITY_MISMATCH` and zero
  artifacts, so the artifact's structured hash can never bind to the wrong
  league (round-9 P2). An oversized streamed body CANCELS the underlying
  reader before the run stops — a chunked server that keeps streaming past
  the 8 MiB cap can no longer hold the socket or block connection reuse
  (round-9 P2). Replay SHARES THE SAME cross-process run lock as capture:
  `runReplay` acquires the identical `acquireRunLock` BEFORE reading the run
  state and holds it until every replay write (detail artifacts + run
  summary) completes, releasing in `finally` — a concurrent capture or
  replay of the same run id fails closed instead of interleaving state or
  artifact writes, and replay re-verifies lock ownership before the
  artifact loop and before the summary write (round-10 P2).

No real detail-capture request has been made by the pipeline and no capture has
been executed in this repository state: every test is mocked
(`REAL_NETWORK_FORBIDDEN_IN_TEST` global fetch), the only real FotMob network
traffic is the completed two-path compatibility probe (2 requests), the run
summary records `database_writes: 0`, and real CAPTURE requires a new explicit
user authorization (`OWNER_REAL_CAPTURE_AUTHORIZATION=NO`).

### Transport-phase observability (bounded diagnostic/audit layer, PR #1819)

A bounded transport-phase observation layer is part of this repository
revision (PR #1819): the detail CAPTURE adapter
(`src/infrastructure/fotmob/FotMobTransportObservation.js` + pipeline wiring,
branch `fix/fotmob-detail-transport-observability`). When this revision is
present, every real fetch attempt persists ONE redacted observation entry in
a NEW bounded run-local file `transport-observations.json` (≤ max_requests
entries, self-hashed, crash-safe, fail-closed reads; the run-state schema is
UNCHANGED — old v1 runs resume and replay byte-identically):

- Phases are set by actual code-execution boundaries only:
  REQUEST_STARTED → AWAITING_RESPONSE_HEADERS → RESPONSE_HEADERS_RECEIVED →
  READING_RESPONSE_BODY → RESPONSE_BODY_COMPLETED (plus vocabulary terminal
  markers REQUEST_FAILED / REQUEST_ABORTED_BY_TIMEOUT). Future timeout
  evidence can therefore distinguish **waiting for response headers** from
  **reading the response body**, with real
  response-headers-received / body-reading-started / body-bytes-received /
  local-timer-fired / last-reliable-phase fields. The layer CANNOT
  distinguish DNS from TCP from TLS — those phases are never claimed.
- **The real-request safety contract is unchanged**: REQUEST_TIMEOUT_MS=30 s,
  retry 0, redirect manual, delay ≥ 60 s, concurrency 1, GET-only, budget
  unchanged. Telemetry NEVER persists cookies, authorization headers, full
  headers, tokens, sessions, proxy credentials, body fragments, HTML or URL
  query — only an allowlist (content type bounded to 200 chars, declared
  content length, location presence, redirect flag) plus non-negative
  safe-integer counters and null/enum fields. Strings are bounded, numbers
  are non-negative safe ints, unknown fields are null/enum.
- Diagnostic/audit only, bounded: an unreadable or foreign pre-existing
  observations file FAILS CLOSED at run start (before any request); once the
  primary capture outcome is finalized, failure of the FINAL telemetry
  persistence never changes that outcome, and the run summary links
  telemetry only from the verified final on-disk document (never from the
  pending in-memory state). It is NOT a new capture authorization, and the
  timeouts of runs 4193752 / 4506625 are **NOT re-requested**; the
  five-match real trial evidence stays **3/5**; 16-match capture, database
  writes and training remain **not authorized**.
- SC-002 status is unchanged by this PR
  (SC_002_ENFORCEMENT_INFRASTRUCTURE=COMPLETE /
  SC_002_STAGING_PRODUCTION_ROLE_DEPLOYMENT=PENDING).

### Current read-only retained inventory

- `matches=60`; 58 are strong/harvested FotMob matches and 60/60 have
  `external_id`.
- `raw_match_data=76`: `fotmob_live_v1=58`, hydration=8, page-props=8 and
  synthetic=2. All 76 rows are FK-linked to `matches`; there are 60 distinct
  `match_id` values and zero raw orphans.
- `fotmob_raw_match_payloads=32` are retained full raw-payload records, not
  metadata-only rows. V26.5 requires complete, unparsed `__NEXT_DATA__` JSON
  in non-null `next_data_json`, together with raw-file locators, SHA-256
  values, byte sizes, capture timestamps and ingestion metadata. Complete
  `page_props_json` can be retained when present, but the column is nullable.
  Their `match_id` values overlap retained match/raw assets at match level
  only; record-level payload-to-raw lineage, 32/32 pageProps presence and
  32/32 parser validation are not proven.
- The retained data and `matches.match_id`/`external_id` identity baseline are
  evidence assets; they do not establish a future writer entrypoint.
- The 2026-07-29 read-only schema review found no provider-scoped external-ID
  or business-identity uniqueness, no canonical import lineage and an
  update-on-conflict generic writer. These are implementation requirements,
  not permission to reuse a legacy writer.

### Current mapping-target chronology (separate from retained rows)

The retained database rows above are asset evidence, not a classification of
historical mapping targets. A static exact-ID reconciliation covers 50 concrete
Ligue 1 mapping targets:

- 32 are `clean_candidate`: L2V3BC's earlier `needs_new_evidence` targets have
  exact ADG59A promotion and ADG59B
  `accepted_source_controlled_only`/`resolved_source_controlled_only` evidence,
  with confirmed orientation/date/competition and no duplicate conflict.
- 10 remain `needs_new_evidence`: they have an exact L2V3BC identity but no
  exact ADG59A/ADG59B successor or later mapping-state mutation.
- 8 remain `remain_suspended`: L2V3AT suspended their accepted
  mapping/baseline after reverse-fixture contradictions, and no exact later
  resolution exists.

The terminal counts are `32 + 10 + 8 = 50`. No target was fuzzy-matched,
re-accepted, unsuspended, written to the database or made raw-write ready by
this reconciliation. These are not M3 Football-Data candidates and do not
define its population. The separate M3 2026-07-28 offline audit has now
compared 892 Football-Data Premier League candidates with 1,140 recovered
FotMob canonical candidates: 888 are exact unique and four are isolated
kickoff conflicts. The design selects all 1,140 for future inventory, treats
888 as linkage-only, keeps four linkage-quarantine, and treats the remaining
248 as canonical-only/unlinked. The four plus 248 are the 252 candidates
without an exact Football-Data link. That result does not reclassify any
32/10/8 Ligue 1 mapping target or validate a raw writer/import.

### Historical controlled audit milestone

Four retained rows were explicitly audited under #1487: 4/4 parseable, 4/4
SHA-valid, 4/4 inner-`matchId` valid, zero errors and zero warnings. This
historical four-row audit does not extend a full parser/audit result to all 58
current `fotmob_live_v1` retained rows. Exact named-writer/run provenance for
all 58 rows is not uniquely attributable.

### Offline detail staging converter / validator (implemented, tested, merged via PR #1817)

The offline staging layer (`scripts/ops/fotmob_detail_staging.js` plus
`src/infrastructure/fotmob/FotMobDetailStaging{Contract,Converter,Retention}.js`
and `FotMobDetailStagingSourceVerification.js`) converts archived
`fotmob-match-detail-capture-payload/v1` + `fotmob-match-detail-capture-manifest/v1`
pairs into immutable `fotmob-detail-staging-artifact/v1` snapshots. It is
**pure offline by construction**: zero network (no fetcher import), zero
database (no DB client, no migration, no canonical/staging/odds write), zero
capture, no wall-clock time in business fields (`generated_at` comes from the
manifest's `response_received_at`, recorded on the artifact as
`source_response_received_at`; `observation_id` is a deterministic
RFC 4122 UUIDv5 over the observation key). Canonical make entrypoints:
`data-fotmob-detail-staging-help` / `-receipt` / `-build` / `-validate`, all
run container-first via `$(COMPOSE_DEV) exec -T dev` (the direct Node CLI is
the internal engine). The store is append-only file snapshots plus numbered
`store-state-<seq>.json` ledger versions; outputs are repository-external
only, written with per-file atomicity (O_EXCL tmp + fsync + same-filesystem
rename) under an exclusive per-store lock, fail-closed on divergent content,
committed by the LOGICAL_COMMIT_MARKER protocol (the `commit-<seq>.json`
marker is the ONLY commit point; uncommitted residue is reported, never
treated as committed), and re-validated by `-validate`. 16 archived matches
(one/five/ten-match pilot archives, e3679262/9bc50640/02635cee) were staged,
rebuilt twice, validated twice, byte-identical across builds, with all
`canonical_match_id` null and `UNLINKED_NOT_ATTEMPTED` link status; derived
outputs were removed. The 16-match validation is an offline verification run
only — no new real capture happened and no real payload/manifest/artifact was
committed.

**PR #1817 remediation history (offline-only; PR #1817 MERGED 2026-08-06, squash
merge commit `fd60117d283a2af9e103990f733e436fda53b100`, post-merge main
Production Gate run 31075669344 = SUCCESS — the per-finding narrative below is
the pre-merge record)**:
- Blockers round (8 findings of the independent review of head c8a0489f7):
  FINDING_1 — logical commit-marker atomicity: `commit-<seq>.json` (schema
  fotmob-detail-staging-commit-marker/v1) is the single commit point, written
  last after artifacts → quarantines → summary → ledger; the marker binds the
  exact file list with per-file sha256 plus the previous marker sha256 chain;
  rollback removes only the files this attempt wrote (pre-existing identical
  files are never deleted); residue scan fails closed. FINDING_2 — on
  REPEAT_EQUIVALENT the artifact is REBUILT with recomputed business and
  integrity hashes and the FINAL classification is written back; old
  artifacts stay byte-untouched and summary / artifact / store ledger are
  three-way cross-checked by the validator. FINDING_3 — verified package
  receipts: real archive SHA-256 verification plus a safe pure-Node tar
  reader (no child_process; absolute/../symlink/hardlink/special/duplicate
  members rejected); every index entry is bound to exactly one package whose
  receipt and live archive/member hashes are re-verified per entry
  (R16-P1-1: every entry call freshly re-inspects the live archive).
  FINDING_4 — symlink-ancestor checks on every input type and an
  input/output non-overlap rule. FINDING_5 — full validator with 38 checks in
  five groups (A summary 1–10, B store ledger 11–20, C artifact 21–28,
  D quarantine 29–33, E commit 34–38), run unconditionally even when state
  errors exist. FINDING_6 — LAYER_A: observation_id recomputed as RFC 4122
  UUIDv5 over the observation key and generated_at enforced as byte-exact
  strict ISO equal to the artifact's source_response_received_at (which
  itself derives byte-exact from the manifest's `response_received_at`); LAYER_B:
  artifact_integrity_sha256 over every artifact field except itself
  (integrity hash, not a signature). FINDING_7 — SC-002 status corrected:
  SC_002_ENFORCEMENT_INFRASTRUCTURE=COMPLETE,
  SC_002_STAGING_PRODUCTION_ROLE_DEPLOYMENT=PENDING, PR1817_CHANGES_SC002=NO
  (the pre-correction wording in the original blocker record said "SC-002 is
  partial mitigation only"; the corrected two-layer state above supersedes it).
  FINDING_8 — Claude post-remediation
  self-review named CLAUDE_POST_REMEDIATION_SELF_REVIEW;
  EXTERNAL_IMPLEMENTATION_ACCEPTANCE=PENDING and READY_TO_MERGE=NO.
- Codex closed-loop round (independent review 4863122944 of head
  a3a916fdd): 13 findings remediated — P0-1 live archive re-verification
  against the receipt (SHA-256 + stable-sorted member inventory hash
  `archive_inventory_sha256`; the per-run sharing model described at review
  time is pre-R16 behavior — superseded by R16-P1-1 per-entry fresh
  re-inspection, cache never trusted across runs);
  P0-2 REPEAT_EQUIVALENT final-classification write-back + validator
  three-way summary↔artifact↔ledger cross-comparison; P1-1 two-level tar
  member-name validation (raw segments + combined normalized path, ustar
  `ustar\0`/`ustar ` magics, GNU long name, local PAX, normalized duplicates);
  P1-2 ACTUAL 16-field double-binding matrix (A/B/C/D) with per-field
  conflict tests; P1-3 receipt path through the unified input safety gate;
  P1-4 TOCTOU mitigation (O_NOFOLLOW fd reads with dev/inode checks,
  controlled private output directories, O_EXCL tmp, exclusive per-store
  lock, pre/post directory identity check — honest threat model: NOT a
  defense against a same-uid sustained-race attacker); P1-5
  MODE_1_UNANCHORED / MODE_2_EXTERNALLY_ANCHORED validation
  (`--expected-latest-marker-sha256` / repo-external `--anchor-checkpoint`);
  P2-1 strict tar parsing (octal size required, explicit content/padding
  bounds, canonical end blocks, strict PAX lengths, GLOBAL PAX rejected);
  P2-2 payload_file_sha256 / manifest_file_sha256 REQUIRED and three-source
  consistent; P2-3 RFC 4122 UUIDv5 with the official DNS-namespace test
  vector + byte-exact timestamp binding; P2-4 structured garbage
  (null/[]/string/number/boolean) → REJECTED_SCHEMA_UNKNOWN without throwing,
  convertAll never lets one bad input crash the batch; P2-5 Makefile staging
  targets container-first via `$(COMPOSE_DEV) exec -T dev`; P3-1 docs and PR
  body rewritten to match the real implementation.
Test counts: 340 staging unit tests (122 retention incl. fault-injection and
tamper [114 + 3 R18-P2-1 short-write injections (a/b/c) + 1 R19-P2-1
lockCreated regression + 2 R20-P1-1 stale-lock fail-closed regressions + 3
R20-P2-1 final-artifact gate regressions; the former P1-4 stale
auto-recovery test was reworked into the R20-P1-1 fail-closed regressions]
+ 82 source
verification [75 + 4 R17-P2-1 PAX size-override (a/b/c/d) + 3 R17-P2-1 PAX
merge-semantics (e/f/g)] + 89 contract [54 declared + 16 loop-generated
per-field conflict tests + 3 R6-P1-2 identity-semantics + 3 R7-P3-2 id-length
+ 1 R8-P2-1 strict array plainness + 3 R12-P3-1 cycle/depth guards + 3
R13-P2-3 validator depth gate + 1 R13-P3-2 proxy array refusal + 1
R14-P3-1 symbol own key refusal + 4 R15-P2-1 __proto__ own-key
regressions (a/b/c/d)] + 17 converter
+ 30 CLI (25 + 4 R20-P2-2 --limits-file regressions + 1 R21-P3-2 frozen-cap regression in the dedicated
fotmob_detail_staging_cli_limits.test.js);
runtime counts = node --test
# pass; the only gap vs static test() declarations is the loop-generated pair) green
on the remediation head; ESLint clean. Codex round-8 (head 7bbbd7658) found 2
new P2 items — R8-P2-1: isPlainJsonData now rejects non-plain arrays
(non-enumerable own toJSON / holes / symbols / extra keys / non-Array
prototypes / non-finite numbers — .every() alone skipped them, so a tampered
array could be written as bytes its artifact hash disagrees with), enforced on
both the direct accepted and the REPEAT_EQUIVALENT rebuild paths with
zero-write regressions; R8-P2-2: commitObservations refuses unretainable
LINKED_*/unknown terminal states (ok:false results pass through verbatim —
the pre-loop now whitelists accepted/rejected/quarantine only, constrains ok
vs classification, and self-validates the summary BEFORE any write). Both
remediated with production tests; 267 staging tests green under umask 022 and
0002. Codex round-9 (head 8b1fc9034) found 1 new P2 (R9-P2-1: the raw result
contract is now enforced BEFORE classification — `ok` must be a real boolean
(a truthy string 'false' no longer classifies as success), ok:true must declare
ACCEPTED_NEW (retention derives EXACT/EQUIVALENT/identity-conflict; a raw
rejected claim can no longer be discarded and committed as accepted), and
ok:false cannot claim an accepted state — 3 new zero-write regressions + legal
control; 297 staging tests green under umask 022 and 0002) and 1 non-blocking
P3 (R9-P3-1: doc field-name accuracy — generated_at derives from the manifest's
`response_received_at`, recorded on the artifact as `source_response_received_at`;
both docs corrected). Codex round-10 (head 4c1609945) found 2 new P2 + 2 new
P3, all remediated on the current head: R10-P2-1 (direct commitObservations
injection surface closed — quarantine_reason derives from the validated
error_code instead of persisting caller-supplied errors[0].message, rejected
ok:false envelopes must carry a registry E### error_code, non-ISO builtAt
refused, every write-plan document forced through isPlainJsonData, D-group
validates recorded_at strict ISO + file/ledger agreement — 5 new tests + legal
control), R10-P2-2 (validator observations shape hardening — array
observations → LEDGER_INVALID, null/non-object entries → LEDGER_INVALID
instead of a crash — 2 mutation regressions), R10-P3-1 (CAPABILITY_INDEX.md:70
and PR body field-name closure + counts synced to 279), R10-P3-2 (tar parser
rejects dangling GNU L / PAX x metadata records at end-of-archive with
SAFETY_ERROR — 2 EOF fixture tests). Codex round-11 (head d9a47e1, 18
commits) found 2 new P2 + 3 new P3, all remediated on the current head:
R11-P2-1 (result-envelope injection closure for direct commitObservations
callers — every result is descriptor-scanned and scalar-snapshotted BEFORE
any read (accessor/proxy → INPUT_ERROR), ok:true results must not carry an
error_code, runId must be a plain identifier — 4 regressions + legal
control, zero writes), R11-P2-2 (validateStagingArtifact now runs the
prohibited raw content scan (E013: HTML/credential signatures) on the whole
artifact — 1 tamper regression), R11-P3-1 (D-group quarantine_reason must
derive from the registry error_code whitelist AND agree with the ledger — 1
regression), R11-P3-2 (marker-tamper regression rehashes the marker after
tampering instead of trusting stale marker bytes — test-helper fix),
R11-P3-3 (tar PAX path records support multibyte UTF-8 names — 1
regression); counts synced to 286. Codex round-12 (head 1350ef4de) found 2
new P2 + 1 new P3, all remediated on the current head: R12-P2-1 (the
artifact is now DEEP-snapshotted, not kept as the caller's reference — a
descriptor-driven deep copy built without ever invoking JSON.stringify/
toJSON on the caller's object, plus util.types.isProxy refusal, so a
transparent Proxy artifact can no longer pass every gate on legal bytes
and inject raw content at serialization time; cycles and excessive depth
are structured INPUT_ERRORs, never RangeError — 2 regressions + legal
control), R12-P2-2 (bounded archive inspection — compressed size checked
via the PRE-READ fstat before any allocation, gunzipSync maxOutputLength,
tar member-count / single-member / total-content caps, all fail-closed
SAFETY_ERROR — 4 regressions + legal control), R12-P3-1 (isPlainJsonData
and the prohibited-content scan refuse cycles / depth overflow / proxies
as structured failures — 3 regressions); counts synced to 297. Codex
round-13 (head c00343a58) found 4 new P2 + 3 new P3, all remediated on the
current head: R13-P2-1 (verifyArchive now merges DEFAULT_ARCHIVE_LIMITS and
passes maxCompressedBytes to the pre-read fstat — the receipt CLI's first
SHA pass can no longer read a whole oversized archive into memory before
the bounded inspectArchive; 1 regression + legal control), R13-P2-2 (the
receipt↔binding SHA is enforced UNCONDITIONALLY even when a registered
live-verification capability is supplied, and the capability now carries
the canonical archive_path of the verified archive — a binding with a wrong
SHA or pointing at another archive is refused; 2 regressions), R13-P2-3
(validateStagingArtifact starts with an isPlainJsonData depth/cycle/plain
gate, so a direct-API/CLI/store-validator call agrees with the commit's
128-level gate and a cyclic or over-deep artifact is a structured
validation error instead of an unbounded hash-traversal RangeError;
2 regressions + legal control), R13-P2-4 (validateSummaryDoc validates every
observation is a non-array object before any field read — a raw/null row is
a structured SUMMARY_INVALID with short-circuit, and validateOutputRoot
skips malformed rows instead of throwing; 1 marker-consistent mutation
regression), R13-P3-1 (the result ENVELOPE itself is refused when
util.types.isProxy — before any field of the caller's object is read;
1 zero-write regression), R13-P3-2 (scanProhibitedContent refuses
proxy-wrapped values BEFORE the array/object dispatch, so a Proxy ARRAY is
a structured E013 too; 1 regression + legal control), R13-P3-3
(PROJECT_STATUS.md current-baseline contract count corrected 77→80);
counts synced to 307.
Codex round-14 (head 35a1409b2, 20 commits) found 1 new P2 + 2 new P3 —
R14-P2-1: payload/manifest reads are now capped by their LIVE ARCHIVE MEMBER
size before the read (entry selectors resolved first; missing member caps at
0 — an external file larger than the tar member is refused with SAFETY_ERROR
at the fstat size gate before its bytes are allocated; direct-API regression
R14-P2-1a + CLI/build regression G57 asserting E008 REJECTED_PROVENANCE_BROKEN
batch isolation with zero accepts + legal control), R14-P3-1: isPlainJsonData
and snapshotStrictPlainData object branches now use Reflect.ownKeys to refuse
Symbol own keys (snapshot never silently drops them; regression + legal
control), R14-P3-2: ACTIVE_MILESTONE current-overview count corrected
260→307; counts synced to 310.
Codex round-15 (head ec2f29037, 21 commits) found 1 new P2 + 1 new P3 —
R15-P2-1: a legal own "__proto__" key (JSON.parse-generated) was silently
dropped by the `{}` + `target[key] = value` write patterns — the shared
canonicalizeJson (FotMobRawDetailFetcher.js, the staging artifact hash chain's
shared base via canonicalJsonHash → sha256CanonicalJson → canonicalizeJson),
snapshotStrictPlainData and both artifact hash projections now create the
property with Object.defineProperty (enumerable data property; behavior
identical for every other key; the retention newObservations key is
internally derived as sourceMatchId:sha256 and structurally cannot be
"__proto__"). Regressions R15-P2-1a/b/c/d (contract: JSON.parse scalar +
object-value snapshot preservation with intact prototype, artifact-level
hash sensitivity + legal-control validation, nested section value exercising
only the shared canonicalizeJson) + R15-P2-1e (retention end-to-end:
convert→commit→validate preserves the field on disk and stripping it is now
a detected tamper). R15-P3-1: selector-order comment narrowed to "before the
payload/manifest input files are gated or read" (non-blocking); counts
synced to 315.
Codex round-16 (head 0cff9b262, 22 commits) found 1 new P1 + 1 new P2 + 1
new P3 — R16-P1-1: the exported verifyEntryAgainstReceipt no longer accepts
a reusable inspected capability (WeakSet identity proves only "once
produced by this module", not "reflects the CURRENT archive bytes"; an
archive replaced at the same path after a capability was issued bypassed
re-verification). Fixed: the API always freshly re-inspects the live
archive per entry and refuses ANY supplied inspected (SAFETY_ERROR); the
CLI loader's liveInspectionCache was removed (receipt document cache kept;
archive re-read per entry under the same bounded limits). Regression
R16-P1-1a (replace-archive attack: old capability refused + fresh
re-inspection catches the live SHA mismatch; V34a/b/c/d/e updated to the
new API contract). R16-P2-1: buildPackageReceipt's memberHashes lost a
legal member named "__proto__" through the legacy setter (incl. PAX
path=__proto__), so legal archives could never complete staging — fixed
with Object.defineProperty writes + hasOwnProperty existence checks in
buildPackageReceipt AND verifyPackageReceipt. Regressions R16-P2-1a (PAX
path=__proto__ member through receipt → live reverify → entry load
end-to-end), R16-P2-1b (missing "__proto__" member reference →
INPUT_ERROR), R16-P2-1c (validator member-reference fail-closed).
R16-P3-1: parsePaxRecords now fails closed on a length-valid record
without a key=value separator (SAFETY_ERROR; previously silently ignored),
and a legal "__proto__" PAX key is preserved as an own data property
(non-blocking). Counts synced to 320.
Codex round-17 (head 36202a549, 23 commits) rechecked R16 fully RESOLVED and
found 1 new blocking P2 + 2 non-blocking P3 — R17-P2-1: a legal local-PAX
`size=` override was not honored (the parser consumed only path/linkpath, so
a size-overflow archive — GNU tar leaves the header octal size 0 and carries
the real size in the extended header — failed content/padding/hash handling).
Fixed: the FULL local-PAX pending metadata is kept (consecutive x headers
merge, later record wins, defineProperty-safe spread), `size=` is strictly
parsed as an unsigned decimal safe integer at the extended header
(SAFETY_ERROR on anything else), and the effective size replaces the header
size EVERYWHERE for the member itself — resource limits, content bounds,
padding and the content hash — while metadata entries (L/x) always use their
own header size; unconsumed local-PAX metadata (path or size) at
end-of-archive is now a dangling error (R10-P3-2 rule extended from
path-only to any pending record; message now "dangling GNU/PAX metadata
override"). Regressions via production inspectArchive: R17-P2-1a size-only
override (header size 0, PAX size=3 → member size/hash correct),
R17-P2-1b size + mtime + UTF-8 path records merged, R17-P2-1c non-decimal /
unsafe sizes (abc/-3/+3/3.0/1e3/overflow) fail closed, R17-P2-1d dangling
size record fails closed. R17-P3-1 (non-blocking): the R1/R2 WeakSet
capability registry + deep-freeze were REMOVED — after R16-P1-1 no reusable
capability ever leaves the module, so the dead machinery (which could invite
a future maintainer to resurrect an unsafe cache) is gone; V34f now asserts
the plain mutable return. R17-P3-2 (non-blocking): stale "once per package
per run" comments corrected to per-entry in the source docstring, the CLI
loader block, and this document. Counts synced to 324.
Codex round-18 (head 8f1113b5a, 24 commits) rechecked R17 fully RESOLVED and
found 1 new blocking P2 — R18-P2-1: `writeJsonAtomically` ignored the return
count of `fs.writeSync(fd, bytes)`, which may legally be a SHORT write; a
truncated tmp could then be fsynced, renamed and reported written:true while
the artifact or commit marker carried partial content (validate would only
discover it later, leaving an un-committable store — violating "marker is
the only commit point, failure rolls back"). Fixed: the buffer write loops
until the whole document is persisted, and a non-integer/zero/negative
(no-progress) or overshooting return throws SAFETY_ERROR through the
existing cleanup (unlink tmp, rethrow) — the marker is never written on a
failed persistence. The store-lock PID write got the same loop (a truncated
PID could make isHolderAlive() misjudge a LIVE holder as dead and clear its
lock), and an acquire-time write failure now removes our OWN lock file
instead of leaving an unresolvable empty lock that would fail-close every
future commit. Regressions via the REAL production paths: R18-P2-1a (1-byte
short writes loop to a full artifact + marker, store validates clean),
R18-P2-1b (zero-progress fails closed on writeJsonAtomically AND an
end-to-end commit — no tmp, no file, no marker, no lock residue), R18-P2-1c
(no-progress landing exactly on the commit-marker write rolls back every
written file). Codex's non-blocking suggestion was also taken: three
production inspectArchive regressions locking the PAX merge semantics —
R17-P2-1e (consecutive x headers accumulate: path from the first, size from
the second), R17-P2-1f (a pending size override survives a GNU long-name
record, x(size) → L → member), R17-P2-1g (a PAX record before a directory
member is consumed by it — no dangling, following member intact). Counts
synced to 330.
Codex round-19 (head 5b2166c79, 25 commits) rechecked R18 fully RESOLVED and
found 1 new blocking P2 + 1 non-blocking P3 — R19-P2-1: the R18 acquire-time
lock cleanup unlinked the lock path on ANY non-EEXIST openSync failure,
even when the failure happened BEFORE the lock was created (I/O error,
permission error, fault injection) — that path could belong to ANOTHER live
holder, and unlinking it would silently break per-store exclusivity
(TOCTOU window between failed open and unlink). Fixed: a `lockCreated` flag
gates every cleanup — the lock path is only ever closed/unlinked when
openSync('wx') actually created it; EEXIST stays contention (return false,
touch nothing); any other pre-creation failure rethrows without touching
the path. Regression R19-P2-1a (a pre-created live lock owned by the
current pid + injected EIO on openSync for the lock path: the EIO
propagates, the lock file survives byte-identical, and the next normal
commit fails closed with "another process holds the store lock" — the live
holder is never cleared by a failed acquirer). R19-P3-1 (non-blocking):
docs remediation timelines are now labeled as historical cutoffs and link
the authoritative current-state document (PROJECT_STATUS.md and
ACTIVE_MILESTONE.md point to this file for rounds R16–R19; stale "Last
updated" timestamps refreshed). Counts synced to 331.
Codex round-20 (head 38dfd57ff, 26 commits) rechecked R19 fully RESOLVED
and found 1 new blocking P1 + 2 new blocking P2 + 1 non-blocking P3 —
R20-P1-1: the stale (dead-holder) lock auto-recovery was a check-then-unlink
TOCTOU — two concurrent recoverers both observe the same dead PID, one
unlinks and creates its OWN live lock, the other then unlinks that FRESH
lock (release paths even delete each other's locks) — per-store exclusivity
breaks and commits interleave. Fixed: dead locks are NEVER auto-recovered;
the acquisition fails closed with a manual-cleanup instruction and the lock
file is left byte-identical (regressions: stale lock fails closed + blocks
every retry until manual cleanup, and a failed acquirer never unlinks a
stale lock — a live lock created in the meantime survives; the former P1-4
auto-recovery test was reworked into these). R20-P2-1: the writer could
commit an artifact its own validator later rejects — validateStagingArtifact
accepts the FULL terminal-state domain (incl. downstream LINKED_CANONICAL)
and a canonical_match_id that is null OR a string, so a direct caller could
commit an ok:true/ACCEPTED_NEW artifact declaring a linked state with a
non-null canonical id: the commit succeeded while validateOutputRoot later
reported the terminal-state disagreement. Fixed: a final-artifact gate in
commitObservations enforces import_terminal_state === classification
terminal state and pins canonical_match_id null +
canonical_link_status UNLINKED_NOT_ATTEMPTED on the EXACT snapshot that is
written (ACCEPTED_NEW original AND the REPEAT_EQUIVALENT rebuild), failing
closed before any byte is written (regressions R20-P2-1a/b/c via the real
production commit path with recomputed hashes). R20-P2-2: the module
documented `options.limits` but the canonical Make/CLI had no way to raise
DEFAULT_ARCHIVE_LIMITS — a legal archive above the defaults (compressed >
256 MiB, member > 256 MiB, > 10000 members) was refused with no operator
surface. Fixed: the canonical CLI accepts --limits-file (repository-external
JSON through the same input gate, strictly validated: positive safe
integers, never above the new HARD_ARCHIVE_LIMIT_CAP), propagated to the
receipt SHA pass, the live archive inspection AND every per-entry loader;
mergeArchiveLimits centralizes the merge + validation so a direct API
caller cannot bypass the caps either (regressions: >10000-member archive
refused by default then accepted via raised cap, 1-byte compressed cap
fails the first SHA pass, tight member cap folds to E008 in build, invalid
limit values/hard-cap violations/limits-file inside the repo all fail
closed). R20-P3-1 (non-blocking, ACCEPTED): GNU global PAX (g) rejection
stays a documented fail-closed input boundary — Codex explicitly judged it
acceptable as-is and recorded it as future compatibility work; no code
change. Counts synced to 339.
Round-21 (head 4d3be869d, re-launched 2026-08-06 after a Codex quota reset):
R20-P1-1 RESOLVED / R20-P2-1 RESOLVED / R20-P2-2 PARTIALLY_RESOLVED /
R20-P3-1 ACCEPTED per round-21 re-verification. New findings: R21-P2-1
(canonical Make targets now expose LIMITS_FILE for receipt/build, appended
conditionally as --limits-file, documented in data-help + data-*-staging-help
+ README + CAPABILITY_INDEX), R21-P3-1 (stale-lock comment corrected to the
fail-closed manual-cleanup contract), R21-P3-2 (DEFAULT_ARCHIVE_LIMITS and
HARD_ARCHIVE_LIMIT_CAP are now Object.freeze'd, with a direct-API mutation
regression). Counts synced to 340.
16-match offline revalidation on the
fixed archives (e3679262/9bc50640/02635cee): RUN_1 FIRST_IMPORT → 16
ACCEPTED_NEW (validate PASS); RUN_2 EXACT_REPLAY → 16 REPEAT_EXACT with zero
new artifacts and byte-identical old artifacts; RUN_3 synthetic new
observation → 1 REPEAT_EQUIVALENT + 15 REPEAT_EXACT, marked
SYNTHETIC_DERIVED_TEST=YES / REAL_NEW_OBSERVATION_CLAIM=NO (no claim of a
real new observation). All three stores validate PASS with zero residue.
No real FotMob access, no database connection or write, no migration, no
training/backtest/prediction; no real payload/manifest/artifact committed.

### Current safety and documentation status

- This file is the active FotMob current-state source of truth; historical ADG
  reports are context, not current execution instructions.
- Legacy acquisition scripts, including the N=3 `n3_live_fotmob_raw_retain.js`
  network/UPSERT path, are historical evidence only and must not become new
  dependencies, canonical writers or recovery contracts.
- README declares FotMob production acquisition `Not yet established`. A future
  canonical writer requires a separately authorized, tested `data-*` milestone.
- Browser, session, cookie, captcha, proxy, network and database-write paths
  remain blocked unless separately authorized.

## Historical legacy ADG context (not current retained-raw status)

- ADG48 correct-orientation probe: 2 targets probed (PSG-Angers, Nice-Auxerre), both HTTP 200. Both confirmed reverse fixtures. 2o4ahb#4830473 = Angers-PSG (reverse observed again). 2sy6tc#4830472 = Auxerre-Nice (newly confirmed reverse). No correct-orientation pairs discovered. No alternate hash candidates found in pageProps. 5 known pairs: 2 confirmed reverse, 3 unverified. 27 missing canonical URLs.
- ADG46 SSR probe: FotMob match page IS accessible (HTTP 200). __NEXT_DATA__ marker FOUND. Safe summary extracted in-memory. Critical finding: route_hash_pair 2o4ahb#4830473 corresponds to REVERSE fixture (Angers home vs PSG away, Apr 2026). Expected orientation (PSG home vs Angers away, Aug 2025) needs different route_hash_pair.
- ADG44 probe result: all 5 targets attempted; FotMob API endpoints (league API id=47, id=53) return 404 via simple HTTPS GET. API architecture has changed. No canonical URLs discovered, no route_hash_pairs verified. No full payload saved. No raw write. 0/5 canonical URL found. Endpoint access requires revised strategy.
- ADG43 result: planning completed for 32 corrected candidates. 27 missing canonical_url targets require L1 discovery. 5 unverified route_hash_pair targets require detail-page verification. ADG44 bounded diagnostic probe designed but NOT executed.
- ADG42 result: total_corrected_candidates=32, canonical_url_atomic_identity_valid_count=5, canonical_url_missing_count=27, route_hash_pair_unverified_count=5, raw_write_ready_count=0.

- URL hash fragment can be detail identity evidence, but alone is insufficient for candidate acceptance.
- Ligue 1 current source inventory / candidate records show systematic home/away inversion.
- ADG12 + ADG16 combined: 17/17 Ligue 1 samples = reverse_fixture_mapping_error.
- ADG20: existing source-controlled artifacts cannot generate corrected Ligue 1 records.
- ADG20 result: proposed_corrected=0, rejected_current_reverse=10, requires_external_discovery=32, suspended_blocked=8, positive_control=1.

## Active runtime guards

- validateStrictFixtureIdentity() — strict home/away/date/competition validation
- classifyDetailCandidateIdentity() — generation-time candidate classification
- selectOrientedFixtureRecord() — oriented fixture selection from ambiguous team-pair records

## Current blockers

- A production FotMob acquisition entrypoint and current external endpoint
  availability are not proven.
- Full parser/audit coverage for all 58 retained `fotmob_live_v1` rows is not
  proven; only the historical four-row audit is complete.
- `fotmob_raw_match_payloads` stores retained offline full raw-payload assets,
  but establishes match-level overlap only, not record-level payload-to-raw
  lineage; 32/32 parser validation is not proven.
- Ten concrete historical mapping targets still need new evidence and eight
  remain suspended; retained row counts do not make the whole historical batch
  clean.
- M3 candidate-to-recovered-FotMob-candidate compatibility is proven only for
  the bounded 2022/2023–2024/2025 Premier League audit: 888 exact unique and
  four isolated kickoff conflicts out of 892 source candidates. The local
  development `matches` inventory remains zero for that scope. The recovered
  1,140-candidate `candidate-match-identity/v1` artifact has been extended with a
  `canonical-inventory-artifact/v2` schema that includes `provider_status`
  (fail-closed `fotmob-status-to-matches-status/v1`), `status_mapping_version`,
  dual hashes (identity projection + full business), and raw response provenance
  retention with SHA-256 capture manifests persisted to disk alongside raw HTML
  as a paired evidence unit, and a shared dependency-free
  `FotMobStatusContract.js` leaf module to prevent status constant drift. The v2 exporter
  (`FotMobCandidateExporter.js`) and CLI (`scripts/ops/fotmob_candidates_export.js`)
  support `--output-schema=canonical-v2` and `--retain-raw-responses` with
  git-revision binding (clean worktree required), overwrite protection, and
  formal `validateArtifactDocument()` contract enforcement before file write. This
  resolves the status-field gap. As of 2026-08-02 the FOTMOB_REAL_CAPTURE_READINESS
  Phase A pre-capture hardening (PR #1813 Debt Impact items 1–2) is implemented in
  the exporter core: malformed `reason` / `reason.short` shapes fail closed with
  deterministic `malformed_reason_object:<type>` / `non_string_reason_short:<type>`
  errors instead of being silently downgraded to scheduled; `started=true` combined
  with a `Postponed`/`Postp` reason fails closed as
  `contradictory_status_flags:started_and_postponed`; and
  `collector_code_revision` is enforced as a full 40-character lowercase hex Git SHA
  inside `buildCaptureManifest()`, so direct core calls and injected dependencies
  cannot bypass the CLI-layer `resolveGitState()` check and no raw or manifest file
  is written for an invalid revision. `ALLOWED_PROVIDER_STATUSES`,
  `STATUS_MAPPING_VERSION`, the identity-v1 output path and both hash schemes are
  unchanged. No inventory writer, link or import has been
  authorized.
- No NEW network acquisition beyond the frozen 888 population, database write,
  migration, new identity generation or legacy writer execution is authorized.

## Forbidden without explicit authorization

- live fetch, network request, browser automation, direct API probing
- DB write, raw write, raw_match_data insert
- re-acceptance, suspension reversal / unsuspend
- source inventory production mutation, candidate production mutation
- Batch C/D evidence acquisition
- full HTML / pageProps / raw_data / source body save or print

## Recommended next step

Do not start automatically. Recommended next task only after user confirmation:
the v2 exporter with status-complete hash-bound `canonical-inventory-artifact/v2`
artifact contract and raw response provenance retention is implemented
(PR #1813, merged), the FOTMOB_REAL_CAPTURE_READINESS Phase A pre-capture
code hardening is implemented and fully tested (malformed `reason.short` fail
closed, started+postponed contradiction fail closed, core-layer 40-hex
`collector_code_revision` enforcement), the bounded auditable detail capture
pipeline is merged (PR #1816, squash merge `b6f9f385…`), and the offline
detail staging converter/validator is merged (PR #1817, squash merge
`fd60117d2…`, post-merge main Production Gate 31075669344 success). The chain
available on main is PLAN → PREFLIGHT → bounded CAPTURE → REPLAY → verified
archive/receipt → offline staging conversion → append-only retention → full
validator. Real FotMob detail capture has been executed once, under explicit
Owner authorization: the GDI1C 888-population acquisition (2026-08-10/11, 14
formal batches, 812 unique targets — see the closeout block above); the
acquisition network phase is CLOSED and the frozen population is immutable.
The FotMob public terms / usage-boundary review is complete (no
written permission granted).

The former "next recommended data task" — **a controlled single-match real
FotMob detail end-to-end trial** (bounds `MATCH_COUNT=1`,
`MAX_FOTMOB_REQUESTS=1`, `MATCH_STATUS=FINISHED`, repository-external output,
zero database) — is **SUPERSEDED_BY_COMPLETED_GDI1C_FOTMOB_888_ACQUISITION**:
the trial-scale controlled prototype was superseded by the fully authorized
batch execution (2026-08-10/11, 14 formal batches, 812 unique targets, 888 raw
frozen; `OWNER_AUTHORIZES_ONE_MATCH_REAL_FOTMOB_END_TO_END_TRIAL` was never
needed because the Owner authorized the broader GDI1C acquisition directly).
The trial bounds description above is preserved as historical design record
and must NOT be offered again as a current next step.

The current next recommended phase is
**GOLDEN_DATASET_CANONICAL_MULTI_SOURCE_ASSEMBLY** (offline readiness/design of
the canonical multi-source assembly using the frozen 888 raw + retained odds
sources; GOLDEN_DATASET_COMPLETE=NO). Any NEW FotMob capture beyond the frozen
population remains a separately authorized future step (future inventory is
1,140 candidates); do not start automatically.
Linkage remains separately authorized for 888 exact identities and the four
conflicts remain quarantine. The 32/10/8 Ligue 1 states remain independent.
No network, database write, migration, canonical-linkage persistence or
legacy-writer execution is authorized here.
