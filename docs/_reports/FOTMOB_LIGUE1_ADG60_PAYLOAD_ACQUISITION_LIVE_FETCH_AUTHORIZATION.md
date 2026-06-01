<!-- markdownlint-disable MD013 -->

# FotMob Ligue 1 ADG60 Payload Acquisition Live Fetch Authorization

- lifecycle: phase-artifact
- phase: ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-AUTHORIZATION
- scope: live-fetch authorization boundary only
- based_on: ADG60 preflight no-write; ADG60 raw payload source inventory; ADG60 payload acquisition plan; ADG60 authorization gate; ADG60 dry-run no-write
- target_count: 32
- current blockers: blocked_missing_payload=32; blocked_requires_explicit_write_authorization=32
- raw_write_ready_count: 0
- dry-run matrix count: 32
- command_preview_only: true
- command_executed: false
- no live fetch in this PR
- no network fetch in this PR
- no browser automation in this PR
- no payload save in this PR
- no acquisition execution in this PR
- no DB write
- no raw write
- no raw_match_data insert
- no schema migration
- no ADG60 write

This PR defines a live/network fetch authorization boundary for ADG60 payload acquisition. It does not execute any fetch, save any payload, or write any data.

## Authorization Contract

### 1. Target Scope

- exactly 32 ADG59B accepted Ligue 1 targets
- no scope expansion
- no target discovery
- no extra leagues
- no extra seasons
- no extra matches
- no opportunistic collection

### 2. Live/Network Fetch Authorization Boundary

This PR defines the authorization boundary only. Execution is deferred to future phases.

| Authorization Flag | Value |
| --- | --- |
| authorization_stage_requested | true |
| live_fetch_may_be_requested_in_next_phase | true |
| network_fetch_may_be_requested_in_next_phase | true |
| browser_automation_may_be_requested_in_next_phase | false |
| current_pr_live_fetch_performed | false |
| current_pr_network_fetch_performed | false |
| current_pr_browser_automation_performed | false |

- Browser automation is not recommended for the initial execution phase. Minimal direct detail endpoint access is preferred.
- Any future live/network fetch execution must re-check this authorization gate before proceeding.

### 3. Fetch Method Policy

Recommended priority for future execution phases:

- **Preferred**: minimal direct detail endpoint / pageProps route if already source-controlled and stable. Use corrected_route_hash_pair from ADG59B source-controlled artifacts.
- **Acceptable only if explicitly authorized**: browser-backed capture (Playwright/Puppeteer/Chromium). Requires separate authorization because of higher anti-bot risk and higher payload fingerprint variability.
- **Not preferred**: legacy API route guessing (FotMob legacy API endpoints returned 404; not reliable).
- **Forbidden without separate approval**: uncontrolled crawler, broad discovery, recursive fetch, full-site crawl.

### 4. Batch Policy

Future live fetch execution must follow this policy:

- initial batch size: 1 target only
- max batch size before manual review: 3 targets
- require manual review after first successful target
- require manual review after any mismatch
- no automatic 32-target full run in first execution PR
- batch size increase requires separate authorization PR

### 5. Rate-Limit / Delay Policy

Future execution must apply:

- minimum delay between requests: 20-60 seconds
- randomized human-like delay allowed only if explicitly authorized
- stop on 429 / 403 / captcha / anti-bot / redirect anomaly
- no retry storm
- no parallel fetch in first execution PR
- max requests per run must be explicitly declared before execution

### 6. Payload Persistence Policy

This PR does not save any payload.

Future payload persistence, if separately authorized, must satisfy:

- payload persistence must be separately authorized
- full raw payload must not be committed to git
- HTML / `__NEXT_DATA__` / pageProps / source body must not be committed to git
- source-controlled manifests may store only: metadata, hash, size, timestamp, target identity, status
- raw payload storage path must be gitignored (`data/raw_external/`)
- verify `.gitignore` coverage before any payload persistence
- cleanup policy required before any local file output
- payload minimization policy required before any acquisition
- stable hash policy required before any acquisition

### 7. DB / Raw Write Policy

DB and raw write operations remain strictly prohibited:

- DB write remains prohibited
- raw write remains prohibited
- raw_match_data insert remains prohibited
- schema migration remains prohibited
- ADG60 write remains blocked
- raw_write_ready_count remains 0
- future payload capture success does not imply raw_write_ready=true
- raw_write_ready can only be reconsidered after source-controlled metadata/hash validation AND separate write authorization

### 8. Stop Conditions

Future live fetch execution must immediately stop on:

- target identity mismatch
- home/away orientation mismatch
- expected date mismatch
- competition mismatch
- missing corrected_hash_id
- missing route hash
- duplicate raw_match_data row already exists
- output directory not clean
- payload would be saved to git-tracked path
- full HTML would be saved
- full pageProps would be saved
- DB write attempted
- raw_match_data insert attempted
- unexpected network route
- unexpected redirect
- 403 / 429 / captcha / anti-bot / blocked response
- unexpected schema / payload structure
- payload too large (> 5 MB per target)
- more targets than authorized batch
- any automatic retry loop

## Future Execution Prerequisites

Before any future live fetch execution PR, these must be confirmed:

1. This authorization gate is merged and unmodified.
2. Authorization contract flags are re-checked.
3. Target scope is still exactly 32 ADG59B accepted Ligue 1 targets.
4. Batch size and rate-limit are explicitly declared in the execution PR.
5. Output directory is clean and gitignored.
6. Stop conditions are wired into the execution script.
7. No DB write, raw write, or raw_match_data insert code paths are reachable.
8. Execution PR explicitly references this authorization gate.

## Safety

- live_fetch_performed: false
- network_fetch_performed: false
- browser_automation_performed: false
- payload_saved: false
- acquisition_execution_performed: false
- db_write_performed: false
- raw_write_performed: false
- raw_match_data_insert_performed: false
- schema_migration_performed: false
- adg60_write_performed: false

## Recommended Next Phase

- recommended next phase: ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-ONE-TARGET-NO-WRITE
- next phase must execute live fetch for at most 1 target
- next phase must still not DB write / raw_match_data insert
- if payload persistence is separately authorized, store only to gitignored external raw storage and commit only metadata/hash/status manifest
- if payload persistence is NOT authorized, perform request/response metadata dry-run only (no body save)
