# Phase 4.78D: Single-Target Acquisition Runtime Design

**Date**: 2026-05-09
**Branch**: `docs/single-target-acquisition-runtime-design-phase478d`
**Starting HEAD**: `53f1f3e70ef7573fe6c5483e0fecc152b2f89ab2`

## 1. Executive Summary

Phase 4.78D is a design-only phase. It did not execute network access,
browser automation, scraping, acquisition, harvest, ingest, DB writes,
staging writes, training, prediction, `pg_dump`, or `pg_restore`.

The goal is to design the future first single-target acquisition runtime:

```text
source
  -> single-target acquisition adapter
  -> proxy / browser / network preflight
  -> local staging artifact
  -> source manifest / provenance
  -> local dry-run audit
  -> ordered DB writes in a later separately authorized phase
```

The recommended candidate family is `titan_discovery`, because discovery is
upstream of raw data, odds, L3 features, training features, and predictions.
This does not mean the current legacy runtime is approved. The current
`scripts/ops/titan_discovery.js` entrypoint remains blocked. Future work must
extract a new discovery-only adapter with a single-target contract, explicit
network authorization, no DB pool initialization, no `FixtureRepository.persist`
path, and staging-only output.

## 2. Titan Discovery Capability Audit

Readonly files inspected:

- `scripts/ops/titan_discovery.js`
- `src/infrastructure/services/DiscoveryService.js`
- `src/infrastructure/services/FixtureRepository.js`
- `src/infrastructure/services/BrowserProvider.js`
- `src/infrastructure/services/HttpClient.js`
- `src/infrastructure/services/FotMobExtractor.js`
- `src/infrastructure/services/NetworkInterceptor.js`
- `src/infrastructure/network/ProxyProvider.js`
- `config/acquisition_engines.phase454.json`
- `tests/unit/titan_discovery_no_network.test.js`
- `tests/unit/DiscoveryService.test.js`
- `docs/_reports/ACQUISITION_ENGINE_READINESS_PHASE4_53A.md`
- `docs/_reports/ACQUISITION_RUNTIME_INGESTION_ORDER_PHASE4_77D.md`

### 2.1 Capability Matrix

| component_or_file                               | role                                                 | network_behavior                                                                                       | browser_behavior                                                          | proxy_behavior                                                                            | db_pool_behavior                                            | persist_behavior                                                                                            | file_write_behavior                            | dry_run_behavior                                                                             | target_scope_behavior                                                                                                | risk        | extractable_for_single_target_adapter                                                                                        | notes                                                                   |
| ----------------------------------------------- | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- | ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | ---------------------------------------------- | -------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- | ----------- | ---------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| `scripts/ops/titan_discovery.js`                | Legacy CLI for L1 discovery                          | Calls `DiscoveryService.discover()` or `search()`, which can access FotMob                             | Indirect through `DiscoveryService`                                       | Indirect through `DiscoveryService`                                                       | Indirect through default service constructor                | Indirect through service repository                                                                         | No direct file write found from readonly audit | Parses `--dry-run` and prints warnings, but does not pass `dryRun` into `service.discover()` | Defaults to all P0 leagues when no target is provided; supports one league, all leagues, tier, all tiers, and search | high        | CLI parse rules can inform future validation; current runtime must not be reused                                             | Current CLI is not a trusted dry-run.                                   |
| `DiscoveryService`                              | Main discovery orchestrator                          | Uses `HttpClient.request()`, `SeasonDiscovery.discover()`, fallback webpage extraction, and search API | Constructs `BrowserProvider` by default and can warm up / rebuild browser | Constructs shared `ProxyProvider` by default and injects it into browser and HTTP clients | Creates `new Pool()` by default if `dbPool` is not injected | Calls `this.fixtureRepository.persist(guardedFixtures)` in `_scanLeague()`                                  | No direct file write found from readonly audit | `discover(options)` does not implement a no-persist `dryRun` branch                          | `_buildTargets()` can build one league-season but also all P0 or all leagues                                         | high        | Target building, season formatting, URL building, parsing, identity checks, and season window guard are useful design inputs | The default constructor is unsafe for a DB-free runtime.                |
| `FixtureRepository`                             | DB repository for matches and recon helpers          | none                                                                                                   | none                                                                      | none                                                                                      | `init()` creates `new Pool()` if missing                    | `persist()` calls `init()`, resolves canonical fixtures, then `_persistBatch()` inserts / updates `matches` | No direct file write found from readonly audit | No safe dry-run persist branch in the inspected path                                         | Batch persistence, not single-target staging                                                                         | high        | Do not use in future network dry-run; replace with a null/no-write sink or stdout/staging sink                               | `_persistBatch()` has `INSERT INTO matches ... ON CONFLICT DO UPDATE`.  |
| `BrowserProvider`                               | Playwright lifecycle wrapper                         | `warmup()`, `goto()`, and browser-context `fetch()` access external URLs                               | Launches Playwright Chromium and pages                                    | Can acquire `ProxyProvider` lease for browser launch and reports success/failure          | none                                                        | none                                                                                                        | No direct file write found from readonly audit | No dry-run mode; it is executable browser runtime                                            | Runtime can operate on any URL passed in                                                                             | high        | Interface concepts are useful, but launch/navigation must be behind future policy gate                                       | Browser launch is not authorization to access an external source.       |
| `HttpClient`                                    | HTTP client for discovery                            | Uses browser fetch or native `http` / `https` request                                                  | Can run via `BrowserProvider.fetch()` when stealth mode is enabled        | Uses `ProxyProvider` leases and proxy agents                                              | none                                                        | none                                                                                                        | none                                           | No global dry-run; calling `request()` performs network                                      | URL-driven, not scope-locked by itself                                                                               | high        | Request metadata and identity checks are design inputs; direct runtime must be gated                                         | Network policy must cover both stealth and raw request paths.           |
| `FotMobExtractor`                               | Fallback webpage / DOM extractor                     | Visits FotMob fixture pages and can call captured API endpoints                                        | Requires browser navigation, scrolling, selectors, and page evaluation    | Indirect through `BrowserProvider`                                                        | none                                                        | none                                                                                                        | none                                           | No dry-run mode                                                                              | League-season webpage scope, not match-id scoped                                                                     | high        | Parsing and extracted object shape are useful references only                                                                | DOM extraction is browser automation and remains blocked in this phase. |
| `NetworkInterceptor`                            | Captures target API URLs from Playwright page events | Observes Playwright requests/responses                                                                 | Requires existing page                                                    | none                                                                                      | none                                                        | none                                                                                                        | Stores captured URLs in memory only            | No dry-run mode                                                                              | Captures any matching `/api/data/` target domain URL                                                                 | medium-high | Target-domain filtering and capture metadata are useful design inputs                                                        | It should not be active unless browser/network runtime is authorized.   |
| `ProxyProvider`                                 | Proxy pool, lease, health, cooldown provider         | TCP/HTTP probes and optional radar discovery can access network endpoints                              | none                                                                      | Core proxy lease implementation                                                           | none                                                        | none                                                                                                        | none                                           | No global dry-run; health checks are real network probes                                     | Pool-level, not source-target scoped                                                                                 | high        | Config resolution and lease metadata are reusable only behind preflight gates                                                | Proxy health check is not source acquisition authorization.             |
| `config/acquisition_engines.phase454.json`      | Engine governance registry                           | Marks `titan_discovery.accesses_network=true`                                                          | Captures family-level risk                                                | Captures family-level risk                                                                | Marks `writes_db=true`                                      | Marks DB write risk                                                                                         | Marks no direct file write for titan discovery | `dry_run_trust_level=low`                                                                    | `target_scope_required=true`                                                                                         | high        | Registry fields should drive future gate validation                                                                          | `titan_discovery` is `adapter_candidate`, not canonical.                |
| `tests/unit/titan_discovery_no_network.test.js` | Governance test                                      | Verifies gate reports `would_access_network=false`                                                     | Does not launch browser                                                   | Does not lease proxy                                                                      | Does not write DB                                           | Does not execute engine                                                                                     | none                                           | Confirms scaffold-only blocked behavior                                                      | Requires target-match-id and source manifest for gate preview                                                        | low         | Test pattern is reusable for future scaffold-only runtime tests                                                              | It intentionally verifies non-execution, not network acquisition.       |
| `tests/unit/DiscoveryService.test.js`           | Unit coverage for service behavior                   | Uses injected fake HTTP in tests                                                                       | Uses fake browser providers                                               | Uses fake proxy provider in selected tests                                                | Default service has `dbPool`; tests often inject fake pool  | Tests confirm repository `persist()` is called in discovery success path                                    | none                                           | No coverage proving CLI `--dry-run` suppresses service persistence                           | Covers one league and all-league target paths                                                                        | medium      | Helps identify seams for extraction                                                                                          | Confirms current service is persistence-oriented.                       |

### 2.2 Current Runtime

The current runtime is:

```text
scripts/ops/titan_discovery.js
  -> parseArgs()
  -> new L1ConfigManager()
  -> new DiscoveryService()
  -> service.discover()
  -> _fetchFixtures()
  -> parser.parse()
  -> fixtureRepository.persist()
```

By default, `DiscoveryService` also constructs:

- `pg.Pool`
- `ProxyProvider`
- `BrowserProvider`
- `NetworkInterceptor`
- `SeasonDiscovery`
- `FotMobExtractor`
- `FixtureRepository`
- `HttpClient`

### 2.3 Extractable Capabilities

These parts are suitable as design references for a future adapter:

- CLI parameter parsing ideas, excluding current defaults that expand to all P0.
- `L1ConfigManager` lookup concepts for league, season, provider id, and URL building.
- `DiscoveryService._buildTargets()` logic only after removing all/bulk expansion.
- `SeasonStrategyFactory` formatting and single-year league handling.
- `SeasonDiscovery` idea only if it is separately gated as a source request.
- `DiscoveryParser` parse contract and fixture object shape.
- Provider identity checks that reject mismatched league responses.
- Season window guard concept.
- `NetworkInterceptor` target-domain filtering concept, only behind authorized browser runtime.

### 2.4 Unsafe Couplings

Unsafe couplings in the current path:

- CLI `--dry-run` is not clearly propagated into `DiscoveryService.discover()`.
- `DiscoveryService` creates a DB pool by default.
- `DiscoveryService` creates browser, proxy, HTTP, extractor, and repository runtimes by
  default.
- `_scanLeague()` always calls `fixtureRepository.persist(guardedFixtures)` when fixtures
  are found.
- `FixtureRepository.persist()` initializes DB state and writes `matches`.
- Browser warmup, browser fetch, native HTTP, webpage extraction, and proxy health checks
  are executable network paths.
- The CLI defaults to all P0 leagues if no target operation is provided.
- All-leagues, all-tiers, tier, full-sync, and search modes can expand scope beyond
  single-target acquisition.

### 2.5 Dry-Run Gaps

Readonly audit answers:

- Is the current `titan_discovery` CLI a trusted dry-run? No.
- Is `dry-run` clearly passed into the service layer? No. The CLI parses
  `options.dryRun` and prints warnings, but `service.discover()` calls do not pass
  `dryRun`.
- Is there a `FixtureRepository.persist` or similar DB write path? Yes.
- Does the current runtime build a DB pool? Yes, unless a pool is injected.
- Does it build browser / proxy runtime? Yes, by default through `DiscoveryService`.
- Can it be single-target today? Only partially. It can accept one `--league`, but it is
  league-season scoped, not `match_id` scoped, and the CLI also supports bulk expansion.
- Which code can be reused as an adapter reference? Parameter validation ideas,
  league/season/provider-id resolution, URL construction, parser output shape, identity
  checks, season window guard, and no-network tests.
- Which runtime must not be directly reused? The current CLI, default
  `DiscoveryService` constructor, default `HttpClient`, `BrowserProvider`,
  `ProxyProvider` runtime, `FotMobExtractor` browser extraction path, and
  `FixtureRepository.persist()`.
- Why not run `scripts/ops/titan_discovery.js`? It can access external FotMob, launch
  browser/proxy runtime, create a DB pool, and write `matches`; its `--dry-run` is
  low-trust and not proven end to end.

### 2.6 Required Audit Labels

```yaml
current_runtime:
    entrypoint: scripts/ops/titan_discovery.js
    status: blocked_adapter_candidate
    dry_run_trust: low
extractable_capabilities:
    - parameter_validation_reference
    - league_season_provider_resolution_reference
    - season_strategy_reference
    - discovery_parser_output_shape
    - provider_identity_check
    - season_window_guard
unsafe_couplings:
    - cli_dry_run_not_proven_to_service_layer
    - default_db_pool_constructor
    - default_browser_proxy_http_runtime_constructor
    - fixture_repository_persist_in_scan_path
dry_run_gaps:
    - cli_prints_dry_run_warning_only
    - service_discover_has_no_no_persist_branch
    - no_test_proves_cli_dry_run_blocks_persist
db_write_risks:
    - FixtureRepository.persist
    - FixtureRepository._persistBatch
    - matches_insert_update_path
proxy_browser_network_needs:
    - proxy_config_preflight_before_lease
    - browser_launch_preflight_before_navigation
    - network_policy_gate_before_fetch_or_navigation
why_not_run_current_script:
    - accesses_external_fotmob
    - may_launch_browser_runtime
    - may_lease_proxy_runtime
    - creates_db_pool_by_default
    - can_write_matches
    - can_expand_to_bulk_scope
```

## 3. Single-Target Contract

This phase does not implement a command. Future names under consideration:

- `make data-single-target-acquisition-runtime-design`
- `make data-single-target-acquisition-network-dry-run`

The future runtime must reject missing or bulk scope before any network, browser, proxy,
staging, DB, training, or prediction action.

| parameter                       | meaning                                                               | default                             | allowed values                                                              | forbidden values                                                                                                          | safety constraints                                                                                  |
| ------------------------------- | --------------------------------------------------------------------- | ----------------------------------- | --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| `TARGET_SOURCE`                 | Human-readable source name and source family.                         | required for future network dry-run | `fotmob`, or a specific approved source id such as `fotmob_league_fixtures` | empty, `all`, `bulk`, `production`, unknown source                                                                        | Must match source manifest and terms approval.                                                      |
| `TARGET_ENGINE_FAMILY`          | Candidate engine family, not legacy command.                          | required                            | `titan_discovery` for first candidate                                       | `run_production`, `recon_scanner`, `batch_historical_backfill`, `total_war_pipeline`, `titan_marathon`, arbitrary scripts | Does not authorize legacy runtime execution.                                                        |
| `TARGET_SCOPE_TYPE`             | Type of single-target lock.                                           | required                            | `match_id`, `league_season_date`                                            | `all`, `bulk`, `production`, `league`, `all_leagues`, `all_tiers`, `tier`, `full_sync`                                    | Must be one target match or one tiny explicit date window.                                          |
| `TARGET_MATCH_ID`               | Existing or expected deterministic match id for `match_id` scope.     | empty                               | One explicit id such as `47_20252026_900001`                                | wildcard, comma list, range, empty when `TARGET_SCOPE_TYPE=match_id`                                                      | Must not imply DB write; used only to lock target identity.                                         |
| `TARGET_LEAGUE`                 | League id or canonical league code for date-window scope.             | empty                               | One approved league id/code                                                 | all leagues, tier, country, wildcard                                                                                      | Required for `league_season_date`; must not expand to all active leagues.                           |
| `TARGET_SEASON`                 | Season for date-window scope.                                         | empty                               | One explicit season such as `2025/2026` or source-native season id          | all seasons, latest, current without concrete value                                                                       | Must be concrete and recorded in artifact.                                                          |
| `TARGET_DATE`                   | One date for date-window scope.                                       | empty                               | ISO date `YYYY-MM-DD`                                                       | ranges, month, season, relative dates                                                                                     | Date window must be bounded to the single date unless a later phase approves a tiny explicit range. |
| `SOURCE_MANIFEST`               | Local manifest draft or candidate path.                               | required for future network dry-run | Local repo-relative or absolute path provided by user                       | remote URL, missing path                                                                                                  | Manifest can be draft but must include source, terms, and approval status fields.                   |
| `TERMS_APPROVAL`                | Human confirmation that terms/license were reviewed for this dry-run. | `false`                             | `true` only with human note                                                 | implicit true, empty                                                                                                      | Required before any real external request.                                                          |
| `NETWORK_DRY_RUN_AUTHORIZATION` | User authorization for one network dry-run.                           | `false`                             | `true` only for the named target/source/scope                               | generic blanket approval                                                                                                  | Required before network access; not reusable for DB write.                                          |
| `ALLOW_BROWSER_RUNTIME`         | Permission to launch and use browser runtime.                         | `false`                             | `false`, `true`                                                             | implicit true                                                                                                             | Browser launch still requires network authorization before navigation.                              |
| `ALLOW_PROXY_RUNTIME`           | Permission to resolve and lease proxy runtime.                        | `false`                             | `false`, `true`                                                             | implicit true                                                                                                             | Proxy preflight is separate from source acquisition.                                                |
| `ALLOW_EXTERNAL_NETWORK`        | Permission to access external source.                                 | `false`                             | `false`, `true`                                                             | implicit true                                                                                                             | Must be `true` only with terms and network dry-run authorization.                                   |
| `ALLOW_STAGING_WRITE`           | Permission to write local staging artifact.                           | `false`                             | `false`, `true`                                                             | implicit true                                                                                                             | Future first run may be stdout-only; staging write needs separate authorization.                    |
| `CONFIRM_SINGLE_TARGET_SCOPE`   | Human confirmation that scope is not bulk.                            | `false`                             | `true`                                                                      | implicit true                                                                                                             | Must be true for future network dry-run.                                                            |

Hard defaults for all design/scaffold modes:

- `ALLOW_EXTERNAL_NETWORK=false`
- `ALLOW_STAGING_WRITE=false`
- `would_write_db=false`
- `would_train=false`
- `would_predict=false`
- `would_execute_engine=false`
- `would_spawn_legacy_runtime=false`
- `bulk_scope=false`

Bulk scope is always forbidden:

- all leagues
- all P0
- all tiers
- all seasons
- full sync
- production harvest
- implicit current/latest source crawl
- any expansion not listed in the user authorization

## 4. Proxy / Browser / Network Preflight Design

Preflight is not execution. Preflight must validate configuration and policy before any
network dry-run, and it must remain separated from harvest/acquisition execution.

### 4.1 Proxy Preflight

Required fields:

```yaml
proxy_preflight:
    proxy_config_resolved: false
    proxy_pool_available: false
    proxy_health_check_required: false
    proxy_lease_required: false
    proxy_usage_logged: false
    proxy_optional_or_required: optional
```

Rules:

- Proxy config resolution may inspect local config only.
- Proxy health checks are network actions and need explicit permission.
- Proxy lease allocation is not permission to access the target source.
- Proxy usage must be logged with `source`, `engine_family`, `target_scope`, and
  `lease_id`.
- If `ALLOW_PROXY_RUNTIME=false`, the future adapter must not call `ProxyProvider`.
- If proxy is required by the selected source, the run must fail closed unless the user
  explicitly authorizes proxy runtime.

### 4.2 Browser Preflight

Required fields:

```yaml
browser_preflight:
    browser_required: false
    browser_provider_selected: null
    browser_launch_allowed: false
    headless_mode: true
    playwright_chromium_dependency: unchecked
    no_browser_http_only_path_possible: unknown_from_readonly_audit
```

Rules:

- Browser launch and browser navigation are separate decisions.
- `ALLOW_BROWSER_RUNTIME=true` allows launch preflight only when network authorization is
  also checked for navigation.
- Browser preflight must identify whether HTTP-only acquisition can satisfy the target.
- Browser runtime must not use search, scroll, DOM extraction, or captured API fallback
  unless those actions are explicitly in scope.
- Browser launch does not imply external source access.

### 4.3 Network Preflight

Required fields:

```yaml
network_preflight:
    source_url_known: false
    terms_approval_confirmed: false
    target_scope_locked: false
    rate_limit_defined: false
    retry_policy_defined: false
    user_agent_policy_defined: false
    no_login_paywall_bypass: true
    no_anti_bot_bypass: true
    no_bulk_expansion: true
```

Rules:

- Preflight is not network dry-run authorization.
- Network dry-run authorization must name the exact source, engine family, and target.
- Source terms/license review must be human-confirmed before external access.
- No login, paywall, anti-bot, or technical access-control bypass is allowed.
- Request cap, retry cap, user agent policy, timeout, and rate limit must be explicit.
- The network policy gate must cover:
    - global `fetch`
    - `http.request`
    - `https.request`
    - Playwright `page.goto`
    - Playwright page-context `fetch`
    - proxy radar / health probes
    - `child_process` launch of legacy runtimes

### 4.4 Separation Rules

- Proxy/browser/network preflight and acquisition execution must be separate code paths.
- Proxy health check is not permission to collect source data.
- Browser launch is not permission to navigate to the source.
- Network authorization is not staging write authorization.
- Staging artifact approval is not DB write approval.
- Any attempt to expand from single target to bulk must fail closed.

## 5. Staging Artifact Schema

Phase 4.78D only designs the schema. It does not write an artifact or create a staging
directory. A future first dry-run may start as stdout-only preview before staging writes
are authorized.

Draft schema:

```yaml
artifact_version: '1'
phase: '4.79D-or-later'
source:
    name: 'fotmob'
    source_url: null
    terms_url: null
    license_url: null
target_scope:
    type: 'match_id'
    match_id: null
    league: null
    season: null
    date: null
engine_family: 'titan_discovery'
engine_version:
    adapter_name: 'single_target_discovery_adapter'
    adapter_version: null
    legacy_reference: 'scripts/ops/titan_discovery.js'
runtime:
    browser:
        enabled: false
        provider: null
        headless: true
    proxy:
        enabled: false
        provider: null
        lease_id: null
    network:
        requested_at: null
        completed_at: null
        duration_ms: null
        rate_limit_policy: null
        retry_policy: null
capture:
    raw_payload_sha256: null
    raw_payload_bytes: 0
    content_type: null
    status_code: null
    row_count: null
    object_count: null
provenance:
    captured_by: null
    captured_at: null
    command: null
    git_commit: null
    container_image: null
safety:
    would_write_db: false
    would_train: false
    would_predict: false
    bulk_scope: false
    post_match_leakage_checked: false
outputs:
    raw_payload_path: null
    normalized_preview_path: null
    manifest_candidate_path: null
```

Schema constraints:

- `would_write_db` must be `false`.
- `would_train` must be `false`.
- `would_predict` must be `false`.
- `bulk_scope` must be `false`.
- `source_url`, `terms_url`, target scope, engine family, git commit, capture time, and
  payload hash are mandatory before any future manifest audit treats the artifact as real.
- Staging artifact write needs a separate user authorization.
- Staging artifact does not imply DB write approval.

## 6. Source Manifest Generation Design

Design flow:

```text
staging artifact
  -> manifest candidate
  -> manifest audit
  -> local dry-run audit
  -> duplicate precheck
  -> insert policy
  -> small write auth
```

Manifest candidate fields:

| field                     | required       | description                                                                                |
| ------------------------- | -------------- | ------------------------------------------------------------------------------------------ |
| `source_name`             | yes            | Human-readable source name.                                                                |
| `source_url`              | yes            | Exact source URL used for the capture.                                                     |
| `license_url`             | yes            | License page or `unknown_pending_human_review`.                                            |
| `terms_url`               | yes            | Terms page or `unknown_pending_human_review`.                                              |
| `allowed_use`             | yes            | Human-reviewed intended use.                                                               |
| `downloaded_by`           | yes            | User or automation identity that performed the capture.                                    |
| `downloaded_at`           | yes            | Capture timestamp.                                                                         |
| `engine_family`           | yes            | `titan_discovery` for this candidate family.                                               |
| `engine_version`          | yes            | Adapter version and git commit.                                                            |
| `target_scope`            | yes            | Exact `match_id` or `league_season_date` target.                                           |
| `original_payload_sha256` | yes            | SHA-256 of the raw payload.                                                                |
| `row_count`               | conditional    | Required for tabular payload.                                                              |
| `object_count`            | conditional    | Required for JSON/object payload.                                                          |
| `staging_artifact_path`   | yes if written | Local artifact path, if staging write was authorized.                                      |
| `approval_status`         | yes            | `draft_for_network_dry_run`, `dry_run_only`, or `approved_for_dry_run`; never DB approval. |
| `human_approval_note`     | yes            | Human note for source terms and target scope.                                              |

Rules:

- Acquisition output cannot go directly into DB.
- Manifest must pass audit before local dry-run gates trust the data.
- Source terms/license must be human-confirmed.
- Source manifest is not DB write approval.
- DB writes require a later authorization, backup, small-batch policy, and post-write
  validation.

## 7. Guardrails

Future adapter hard boundaries:

```yaml
would_write_db: false
would_execute_engine: false # in design and scaffold phases
would_train: false
would_predict: false
would_spawn_legacy_runtime: false
would_execute_pg_dump: false
would_execute_pg_restore: false
would_bulk_harvest: false
```

Implementation guardrails for the future scaffold/runtime:

- Do not instantiate `pg.Pool` in design or scaffold modes.
- Do not instantiate `FixtureRepository` in network dry-run mode.
- Do not call `FixtureRepository.persist()`.
- Do not call `csv_bulk_loader` or any `--commit` path.
- Do not call `raw_match_data_local_ingest` commit.
- Do not call L3 stitch, smelt, training, prediction, ELO recalculation, or model artifact
  loading.
- Do not call bulk backfill, total-war, production harvest, recon scanner, odds harvest,
  or titan marathon.
- Do not spawn `scripts/ops/titan_discovery.js` as a child process.
- Do not import legacy runtime modules when import side effects could initialize browser,
  proxy, DB, Redis, file, or network behavior.
- Use dependency injection for any future adapter dependencies:
    - no-write result sink
    - no-network policy guard in design/scaffold
    - explicit network client only after authorization
    - explicit staging writer only after staging authorization

Blocking details:

- DB pool initialization: fail if the adapter receives or attempts to construct a DB pool.
- `FixtureRepository.persist`: fail if the adapter imports or calls this path.
- `csv_bulk_loader commit`: fail on any `--commit` flag.
- `raw_match_data_local_ingest commit`: fail on any `--commit` flag.
- L3 stitch / smelt / train / predict: fail on command names, npm scripts, or child process
  execution.
- Bulk backfill and legacy pipeline spawn: fail on child process attempts or engine ids not
  approved for the exact single-target scope.

## 8. First Dry-Run Readiness

Before any future real network dry-run, all conditions must be true:

- explicit `TARGET_SOURCE`
- explicit `TARGET_ENGINE_FAMILY`
- explicit `TARGET_SCOPE_TYPE`
- explicit target id or one-date window
- terms/license approval from a human
- network dry-run authorization from the user for that exact target
- proxy preflight design accepted
- browser preflight design accepted
- network preflight design accepted
- staging artifact schema accepted
- source manifest candidate schema accepted
- `would_write_db=false` confirmed
- `would_train=false` confirmed
- `would_predict=false` confirmed
- `bulk_scope=false` confirmed
- no legacy runtime spawn confirmed

Readiness is not DB approval. A future dry-run output must still pass manifest audit,
local dry-run audit, duplicate precheck, insert policy, and small write authorization
before any DB write phase.

## 9. Recommended Next Phase

Recommended:

```text
Phase 4.79D: single-target acquisition runtime scaffold
```

Goals:

- implement scaffold-only command
- validate the parameter contract
- output `would_access_network=false`
- output `would_write_db=false`
- output `would_write_staging=false`
- output `would_train=false`
- output `would_predict=false`
- do not touch network
- do not write DB
- do not write staging
- do not spawn legacy runtime

Possible future command:

```text
make data-single-target-acquisition-runtime-design
```

Alternative:

```text
Phase 4.56A: real network dry-run runbook
```

Only choose the alternative after the user provides a real source, engine family, target
match/window, source manifest, terms approval, proxy/browser policy, staging authorization,
and network dry-run authorization.

## 10. Explicit Non-Execution

Not executed in Phase 4.78D:

- DB writes
- non-SELECT DB SQL
- external download
- `curl`
- `wget`
- `git clone`
- external football data access
- external odds data access
- scraping
- browser automation
- harvest
- ingest
- batch backfill
- network dry-run
- bulk harvest
- staging artifact write
- source manifest write
- packet file write
- `pg_dump`
- `pg_restore`
- model training
- real prediction
- model artifact loading
- Docker volume cleanup
- force push
- `git pull`
- `git fetch --all`
- file deletion

## 11. Validation Snapshot

Readonly validation before writing this report:

- Starting main HEAD: `53f1f3e70ef7573fe6c5483e0fecc152b2f89ab2`
- Latest main push CI before start: `success`
- Working branch: `docs/single-target-acquisition-runtime-design-phase478d`
- `make dev-ps`: services healthy
- `make data-check`: passed
- `make data-schema-status`: passed
- `make data-dataset-status`: passed
- direct SELECT-only DB row counts: `2 / 2 / 2 / 2 / 2 / 2`
- `make data-acquisition-engines`: passed, `no_db_writes`, `no_external_network`
- `make data-acquisition-engine-audit`: passed, `no_db_writes`, `no_external_network`
- `l1-config` residue before report: absent

Final formatting, test, DB row-count, and PR CI results are tracked in the PR and final
turn report.
