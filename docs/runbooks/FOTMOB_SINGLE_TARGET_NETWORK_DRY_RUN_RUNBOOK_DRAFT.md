# FotMob Single-Target Network Dry-Run Runbook Draft

Phase: 4.96F
Status: draft-only, non-executing

## 1. Purpose

This runbook is a draft for a future FotMob single-target network dry-run.

It is not execution authorization. It is not a network execution plan. It is not a DB
write runbook. It is not a staging write runbook. Its only purpose is to prepare the
requirements and guardrails for one future minimal FotMob dry-run.

The future run must remain explicitly authorized, tightly scoped, and non-persistent by
default.

## 2. Current Codebase Reality

The repository already contains legacy FotMob capability:

- L1 discovery through `scripts/ops/titan_discovery.js` and `DiscoveryService`
- L2 harvest through `scripts/ops/run_production.js`, `ProductionHarvester`, and
  `FotMobStrategy`
- FotMob API client code in `src/infrastructure/network/FotMobApiClient.js`
- FotMob extractor and parser code in `FotMobExtractor` and `src/parsers/fotmob`
- Browser, proxy, cookie, and session helper paths
- DB persistence paths for `matches` and `raw_match_data`
- FotMob-related tests, fixtures, config, and historical reports

These paths cannot be used directly for a safe single-target dry-run. The legacy runtime
couples network access, browser launch, proxy runtime, DB writes, file writes, and batch
scope risk.

`titan_discovery --dry-run` is not trusted as a safe dry-run. The CLI parses the flag and
prints a warning, but the dry-run contract is not proven end to end at the service layer.

`run_production --dry-run` is not a safe no-side-effect dry-run. It can still initialize
live acquisition runtime and should be treated as a network dry-run requiring separate
authorization.

## 3. Forbidden Legacy Paths

The following paths must not be directly executed for the first FotMob safe dry-run:

- `scripts/ops/titan_discovery.js`
- `scripts/ops/run_production.js`
- `scripts/ops/batch_historical_backfill.js`
- `scripts/ops/backfill_historical_raw_match_data.js`
- `scripts/ops/titan_seeder.js`
- `ProductionHarvester`
- `FotMobStrategy` live harvest
- `FixtureRepository.persist`
- `Persistence.dualSave`
- `BrowserProvider` launch path
- `ProxyProvider` / proxy pool runtime
- any batch or bulk path

These paths may be useful for source reading, but not for execution.

## 4. Candidate Reusable Components

These components may be referenced when designing a future trusted adapter, but they must
not be executed directly from this runbook:

| Component                                               | Can reference                                                     | Cannot execute directly                                                       | Future isolation requirement                                        |
| ------------------------------------------------------- | ----------------------------------------------------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `FotMobApiClient`                                       | URL shape, headers, response handling, error semantics            | It may perform HTTP requests, proxy agent setup, and browser cookie bootstrap | Must sit behind an injected network client in a trusted adapter     |
| `FotMobExtractor`                                       | `__NEXT_DATA__`, DOM payload, and league fixture extraction ideas | It drives browser navigation and DOM evaluation                               | Must be isolated behind explicit browser authorization, default off |
| `src/parsers/fotmob/*`                                  | Pure parsing patterns and fixture shape                           | Parser use must not imply network, browser, DB, or file writes                | Must be called only on caller-provided payloads                     |
| `FotMobSchemaGuard`                                     | Raw payload schema drift inspection                               | It must not be combined with DB reads or writes by default                    | Must inspect bounded in-memory samples only                         |
| `config/registry.js` FotMob URL helpers                 | Existing FotMob URL conventions                                   | URL construction must not trigger requests                                    | Must remain pure config/reference data                              |
| FotMob tests and fixtures                               | Parser behavior and no-network test examples                      | Tests must not launch live runtime or hit external URLs                       | Must guard no-network, no-DB, no-write behavior                     |
| Single-target acquisition schemas and manifest examples | Staging and manifest field vocabulary                             | Examples are not source approval or write authorization                       | Must remain candidate-only until human approval                     |

All reusable pieces must be placed behind a future trusted adapter with dependency
injection, explicit authorization inputs, and no-side-effect defaults.

## 5. Required First Real Target Inputs

A future operator must provide all real parameters and approvals before any FotMob network
step:

- `target_source=fotmob`
- `target_scope_type=match_id` or `target_scope_type=league_season_date`
- `target_match_id`, or `target_league` plus `target_season` plus `target_date`
- target URL, if available
- source homepage URL
- terms URL
- license URL, if available
- allowed-use summary
- terms reviewed by human
- explicit network authorization
- browser allowed yes/no
- proxy allowed yes/no
- external network allowed yes/no
- staging write allowed yes/no
- no DB write confirmation
- no training confirmation
- no prediction confirmation
- final human confirmation

Missing or ambiguous inputs must stop the run.

## 6. Recommended First Dry-Run Policy

The first future FotMob dry-run should use this default policy:

- single target only
- `max_targets=1`
- stdout-only
- no DB write
- no staging write in first run
- no source manifest write in first run
- no packet write
- no browser by default
- no proxy by default
- no bulk
- no login
- no paywall bypass
- no anti-bot bypass
- no retries beyond a small bounded limit
- no model training
- no prediction
- no artifact loading

Any deviation from this policy requires a later, explicit authorization phase.

## 7. Proposed Future Adapter Shape

Future adapter should expose a narrow interface like:

- `validateInputs()`
- `preflight()`
- `dryRunFetchSingleTarget()`
- `parsePreview()`
- `summarizeToStdout()`

`dryRunFetchSingleTarget()` must only be implemented and executed in a later authorized
phase. Phase 4.96F does not implement or run it.

The adapter must follow these rules:

- inject the network client; do not directly import legacy runtime
- default to no DB access and no DB writes
- default to no staging write
- default to no browser unless explicitly authorized
- default to no proxy unless explicitly authorized
- forbid bulk expansion
- output a bounded JSON preview to stdout
- include no-network unit tests
- include no-DB unit tests
- include no-file-write unit tests before any live network step

The trusted adapter must fail closed when authorization or target scope is incomplete.

## 8. Stop Gates

Stop immediately if any of these conditions appear:

- no terms approval
- no explicit network authorization
- target scope is not single-target
- target count is greater than 1
- source requires login
- source requires paywall bypass
- source requires anti-bot bypass
- source requires proxy without authorization
- source requires browser without authorization
- any path attempts DB write
- any path attempts staging write without authorization
- any path attempts bulk expansion
- unexpected redirect or block page is encountered
- response schema is unknown or unsafe
- parser confidence is low

Stop gates must be evaluated before any external request in future phases.

## 9. Future Execution Sequence

The safe future sequence is:

1. User provides real FotMob target and terms / authorization.
2. Review the filled intake in a separate phase.
3. Record the review result in a separate phase.
4. Record the authorization decision in a separate phase.
5. Create a FotMob trusted adapter scaffold in a separate phase.
6. Add no-network and no-DB adapter tests in a separate phase.
7. Run a stdout-only network dry-run in a separate authorized phase.
8. If successful, consider staging preview in a later phase.
9. Only after staging preview passes, consider DB write preflight.
10. DB write requires separate small-write approval, backup, and rollback plan.

No step may skip the previous approval boundary.

## 10. Non-Execution Statement

Phase 4.96F did not execute:

- no FotMob access
- no network
- no browser
- no proxy
- no scrape
- no harvest
- no ingest
- no DB write
- no staging write
- no source manifest write
- no packet write
- no training
- no prediction
