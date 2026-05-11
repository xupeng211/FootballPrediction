# FotMob Single-Target Dry-Run Readiness Gap Report

Phase: 4.96F
Status: docs-only readiness gap report
Starting HEAD: `eaa8e9f3f5d6121c9f5b5a60f724c0bb8d139a92`

## 1. Executive Summary

FotMob legacy capability exists in this repository. The project has discovery, harvest,
API client, extractor, parser, browser/proxy/session, DB persistence, tests, config, and
historical documentation around FotMob.

Safe single-target dry-run capability does not yet exist.

Direct execution of legacy FotMob runtime is not recommended. The next engineering work
should be a trusted FotMob single-target adapter scaffold, not direct harvest.

## 2. Current FotMob Inventory Summary

Discovery:

- `scripts/ops/titan_discovery.js` is the legacy L1 CLI.
- `src/infrastructure/services/DiscoveryService.js` wires FotMob HTTP, browser,
  proxy, parser, and persistence.
- `titan_discovery --dry-run` is not trusted because dry-run behavior is not proven
  through the service and repository layers.

Harvest:

- `scripts/ops/run_production.js`, `ProductionHarvester`, `AbstractHarvester`, and
  `FotMobStrategy` form the legacy L2 raw harvest path.
- `run_production --dry-run` is still a live acquisition path and is not a safe
  no-side-effect dry-run.

Parser:

- `src/parsers/fotmob/*` contains FotMob parser utilities including `NextDataParser`,
  match / league / team / player parsers, and `XGExtractor`.
- These can inform future pure parsing, but must only parse caller-provided payloads.

API client:

- `src/infrastructure/network/FotMobApiClient.js` builds FotMob match details requests.
- It can use proxy agents and browser bootstrap behavior, so it is not safe as a direct
  first dry-run entrypoint.

Extractor:

- `src/infrastructure/services/FotMobExtractor.js` can inspect FotMob page data and
  fallback DOM payloads.
- It depends on browser navigation and must remain blocked unless browser runtime is
  explicitly authorized in a later phase.

Browser / proxy / session:

- `src/infrastructure/services/BrowserProvider.js` launches Playwright Chromium.
- `config/proxy_pools.json` defines `fotmob_pool`.
- Session and cookie helpers exist in `scripts/capture_auth*.js`,
  `scripts/import_manual_cookies.js`, `scripts/inject_cookie.js`, and
  `scripts/inject_total_war_cookies.js`.
- The requested path `src/infrastructure/network/BrowserProvider.js` was not present;
  the active browser provider path is `src/infrastructure/services/BrowserProvider.js`.

DB persistence:

- `FixtureRepository.persist` writes `matches`.
- `Persistence.dualSave` writes `raw_match_data` and local raw JSON files.
- These paths must remain blocked unless a separate DB write phase is authorized.

Tests:

- FotMob tests cover parser helpers, compliance mode, schema guard, API client,
  discovery behavior, and no-network governance.
- Future adapter tests still need explicit no-network, no-DB, and no-file-write guards.

Config:

- `config/acquisition_engines.phase454.json` marks `titan_discovery` as
  `adapter_candidate`, with network and DB write risk and low dry-run trust.
- `config/registry.js` contains FotMob URL helper conventions.
- `config/proxy_pools.json` contains `fotmob_pool`.

Docs:

- Existing reports document that `run_production`, `titan_discovery`, and other
  acquisition engines remain blocked legacy paths.
- Single-target acquisition schemas and templates exist, but they are generic and do not
  create a trusted FotMob adapter.

## 3. Main Risks

- network access risk: legacy FotMob paths can call external FotMob endpoints.
- browser runtime risk: discovery and extraction can launch Playwright / Chromium.
- proxy runtime risk: `fotmob_pool`, `ProxyProvider`, and `NetworkManager` can be used.
- DB write risk: `FixtureRepository.persist` and `Persistence.dualSave` write DB tables.
- bulk / batch risk: default discovery can scan P0 leagues, and harvest / backfill paths
  can operate in batches.
- dry-run trust risk: `titan_discovery --dry-run` and `run_production --dry-run` are not
  trusted safe dry-runs.
- terms / allowed-use gap: there is no approved FotMob terms or allowed-use evidence for a
  future network dry-run.
- staging / manifest gap: there is no approved FotMob source manifest or staging writer.
- source schema drift risk: FotMob payload fields can change and break parser assumptions.
- anti-bot / login / paywall boundary risk: browser, cookie, and session helpers exist and
  must not be used to bypass source controls.

## 4. Adapter Readiness Gaps

The following gaps must be closed before a real FotMob single-target network dry-run:

- trusted single-target adapter entrypoint
- strict input contract
- no-network preflight
- no-DB guarantee
- no-staging default
- no-browser/proxy default
- bounded stdout preview
- source manifest candidate design
- schema validation
- parser confidence and error reporting
- rate limit / retry policy
- terms / allowed-use evidence
- tests guarding no network, no DB, and no file writes

## 5. Recommended Next Phase

Recommended next phase: Phase 4.97F, FotMob trusted single-target adapter scaffold.

Phase 4.97F should:

- not access the network
- not write DB
- not write staging
- only implement parameter validation, dependency injection, and no-side-effect scaffold
- not call legacy runtime
- not call browser or proxy runtime
- not call DB
- add no-network, no-DB, and no-write tests

The scaffold should prove safety before any future external request is considered.

## 6. Why Not Collect Data Now

Do not collect data now because there is no real target, no terms / allowed-use evidence,
and no explicit network authorization.

The existing FotMob runtime is not safe for first use. Its dry-run behavior is not trusted,
and legacy paths may touch the network, write DB rows, write local files, or expand into
batch scope.

The correct order is to build a trusted adapter first, prove that it has no side effects,
and only then run one minimal stdout-only dry-run after explicit authorization.

## 7. Explicit Non-Execution

Phase 4.96F did not execute:

- external FotMob access
- external football data access
- external odds data access
- curl / wget
- browser automation
- proxy runtime
- scraping
- harvest
- ingest
- batch backfill
- network dry-run
- staging write
- source manifest write
- packet write
- DB writes
- pg_dump / pg_restore
- training
- prediction
- file deletion
