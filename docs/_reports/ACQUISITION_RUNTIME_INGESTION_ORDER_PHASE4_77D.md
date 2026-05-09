# Phase 4.77D: Acquisition Runtime And Ingestion Order Audit

**日期**: 2026-05-09
**分支**: `docs/acquisition-runtime-ingestion-order-phase477d`
**起始 HEAD**: `e00dd5587b3ebd25aa176c9d947f990857daffdd`

## 1. Executive Summary

当前项目不是没有采集引擎，而是采集引擎很多，风险等级不同，且 proxy、browser、Redis、DB write、file write 的边界还没有完全拆清。

本地 CSV dry-run、packet preview 和 packet pre-authorization closure 是 safety harness 和入库前审计工具，不应该替代真实 acquisition engine 路线。真实路线应该是：

```text
source -> engine -> network/proxy/browser runtime -> raw response -> local staging -> source manifest / provenance -> dry-run audit -> ordered DB writes
```

现阶段仍不应该直接运行 high-risk engine。正确下一步不是继续堆 packet 表单，而是做 single-target acquisition runtime design，先把 source、engine、proxy/browser/network preflight、staging artifact schema 和 manifest 生成关系设计清楚。

开始前确认：

- remote main expected HEAD: `e00dd5587b3ebd25aa176c9d947f990857daffdd`
- latest main push CI before start: `success`
- working branch: `docs/acquisition-runtime-ingestion-order-phase477d`
- L1ConfigManager l1-config residue before audit: absent
- DB row counts before audit: `2 / 2 / 2 / 2 / 2 / 2`

## 2. Engine Inventory

Registry source: `config/acquisition_engines.phase454.json`.

| engine                              | status            | layer                               | source_type                                       | network              | browser                                              | proxy                                                                   | redis                       | db_read                             | db_write                                        | file_write                                  | bulk_risk | dry_run_trust                              | recommended_role                                                              |
| ----------------------------------- | ----------------- | ----------------------------------- | ------------------------------------------------- | -------------------- | ---------------------------------------------------- | ----------------------------------------------------------------------- | --------------------------- | ----------------------------------- | ----------------------------------------------- | ------------------------------------------- | --------- | ------------------------------------------ | ----------------------------------------------------------------------------- |
| `real_finished_csv_staging_dry_run` | canonical         | layer_5_local_staging_dry_run       | local manifest + local CSV                        | false                | false                                                | false                                                                   | false                       | SELECT-only duplicate/status checks | false                                           | false                                       | low       | high                                       | Keep as local staging / manifest audit harness.                               |
| `raw_match_data_local_ingest`       | canonical         | layer_5_local_staging_dry_run       | local raw fixture                                 | false                | false                                                | false                                                                   | false                       | SELECT-only preview                 | false                                           | false                                       | low       | high                                       | Keep as local raw fixture preview; commit remains blocked.                    |
| `finished_match_backfill_preflight` | canonical         | layer_7_feature_dry_run             | local DB + optional fixture                       | false                | false                                                | false                                                                   | false                       | SELECT-only chain audit             | false                                           | false                                       | low       | high                                       | Keep as downstream readiness preflight.                                       |
| `csv_bulk_loader`                   | gate_only         | layer_6_small_db_write              | local adapted CSV                                 | false                | false                                                | false                                                                   | false                       | SELECT in alignment                 | true with `--commit`                            | error log path in normal runtime            | medium    | high for parse, unsafe for commit          | Keep blocked except future explicit small-write authorization.                |
| `local_dom_ingestor`                | gate_only         | layer_4_local_staging_normalization | local HTML / clipboard                            | false                | false                                                | false                                                                   | false                       | SELECT prechecks                    | true with `--commit`                            | false from read-only scan                   | medium    | medium                                     | Keep as gated local normalization helper only.                                |
| `fetch_and_adapt_euro_leagues`      | adapter_candidate | layer_3_single_target_acquisition   | Football-Data CSV URL                             | true                 | false                                                | no explicit proxy from readonly audit                                   | false                       | SELECT existing matches             | false                                           | writes temp CSV and adapted CSV             | medium    | low / no safe no-network mode              | Extract only as future source-specific adapter design reference.              |
| `titan_discovery`                   | adapter_candidate | layer_2_discovery                   | FotMob discovery                                  | true                 | true via `DiscoveryService` fallback                 | true via `ProxyProvider` / `BrowserProvider` / `HttpClient`             | false                       | creates DB pool                     | likely writes `matches` via `FixtureRepository` | false from registry                         | high      | low                                        | Candidate family for future discovery-only adapter, not direct runtime.       |
| `odds_harvest_pipeline`             | adapter_candidate | layer_3_single_target_acquisition   | OddsPortal odds                                   | true                 | true via Playwright                                  | unknown explicit proxy in this script; recon/proxy-adjacent code exists | false from script scan      | reads target matches / coverage     | upserts mapping and odds                        | possible runtime artifacts                  | high      | low                                        | Candidate family for future odds adapter, but current runtime is too coupled. |
| `recon_scanner`                     | quarantine        | legacy_bulk_pipeline                | OddsPortal recon                                  | true                 | true via ReconNavigator / ReconBrowserContext        | true via ProxyRotator / ProxyProvider                                   | true via ioredis / Redlock  | true                                | true mapping/status updates                     | session buffer / runtime artifacts possible | high      | low                                        | Keep quarantined until browser/proxy/Redis/persistence are separated.         |
| `run_production`                    | legacy_blocked    | legacy_production_path              | FotMob pending matches                            | true                 | true via `ProductionHarvester` / `AbstractHarvester` | true via `NetworkManager` / `ProxyProvider`                             | not confirmed for runtime   | true                                | true raw data writes                            | true dual-save raw files                    | high      | medium for no-write flag, not network-safe | Keep blocked; extract narrow adapter only if needed later.                    |
| `batch_historical_backfill`         | legacy_blocked    | legacy_bulk_pipeline                | Football-Data + FotMob + DB orchestration         | true                 | indirectly through child engines                     | inherited from child engines                                            | unknown_from_readonly_audit | inherited                           | true with commit / child flows                  | true adapted CSV and logs                   | high      | low                                        | Keep blocked bulk orchestrator.                                               |
| `total_war_pipeline`                | legacy_blocked    | legacy_bulk_pipeline                | Discovery + harvest + recon + smelt orchestration | true outside dry-run | indirectly through children                          | passes `--use-proxy` to recon child                                     | unknown_from_readonly_audit | true                                | true outside dry-run                            | runtime lock/state/log writes               | high      | low                                        | Keep blocked super-orchestrator.                                              |
| `titan_marathon`                    | legacy_blocked    | legacy_bulk_pipeline                | FotMob raw data backfill                          | true outside dry-run | true via Playwright                                  | true via `NetworkShield`                                                | false from readonly scan    | true                                | inserts `raw_match_data`, updates `matches`     | possible runtime output                     | high      | medium for DB-count preview only           | Keep blocked large-scale raw harvester.                                       |

Audit gate result:

- `make data-acquisition-engines`: passed, `total_engines=13`, `safe_for_ai_default_count=3`, `blocked_count=10`, `no_db_writes`, `no_external_network`
- `make data-acquisition-engine-audit`: passed, governance fields complete, high-risk engine list identified, `no_db_writes`, `no_external_network`

## 3. Proxy / Browser / Network Runtime Audit

| component_or_file                                                                       | proxy_related_behavior                                              | browser_related_behavior                                          | network_related_behavior                                             | redis_or_queue_behavior                                  | db_coupling                                            | file_write_behavior                           | risk_level | notes                                                                                       |
| --------------------------------------------------------------------------------------- | ------------------------------------------------------------------- | ----------------------------------------------------------------- | -------------------------------------------------------------------- | -------------------------------------------------------- | ------------------------------------------------------ | --------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------- |
| `config/proxy_pool.js`, `config/proxy_pool.json`, `config/proxy_pools.json`             | Central proxy pool config reader/builder for host, ports, protocol. | none                                                              | Enables proxy server construction.                                   | none                                                     | none                                                   | reads config files                            | medium     | Proxy config is partly centralized.                                                         |
| `src/infrastructure/network/ProxyProvider.js`                                           | Main proxy lease, health, cooldown, assignment provider.            | none                                                              | Can run TCP / HTTP / radar health probes against external endpoints. | none                                                     | none                                                   | none from scan                                | high       | It is a component, but network policy is not globally gated for all engines.                |
| `src/infrastructure/harvesters/ProxyRotator.js`                                         | Legacy compatibility wrapper over `ProxyProvider`.                  | Provides Playwright proxy data to legacy recon/backfill code.     | Delegates health/assignment to provider.                             | none                                                     | none                                                   | structured logs possible through logger       | high       | Used by Recon; legacy interface remains.                                                    |
| `src/infrastructure/services/BrowserProvider.js`                                        | Uses fixed proxy or `ProxyProvider` lease.                          | Launches Playwright Chromium and browser fetch.                   | Warmup/goto/fetch external URLs.                                     | none                                                     | none                                                   | none from scan                                | high       | Discovery browser runtime is separated from DiscoveryService, but still executable runtime. |
| `src/infrastructure/services/HttpClient.js`                                             | Supports proxy agents and proxy rotation metadata.                  | Can use shadow browser fetch through BrowserProvider.             | Native http/https plus stealth/browser modes, retry/backoff.         | none                                                     | none                                                   | none from scan                                | high       | HTTP behavior is componentized but not a single repo-wide network policy gate.              |
| `src/infrastructure/network/NetworkManager.js`                                          | Assigns worker identities with proxy leases.                        | Indirect through harvest context/browser factory.                 | Initializes proxy provider and session manager.                      | no Redis from scan                                       | none                                                   | session/cache behavior through dependencies   | high       | Tied to L2 harvest path.                                                                    |
| `src/infrastructure/network/NetworkShield.js`                                           | 22-node proxy pool, circuit breaker, worker port binding.           | none                                                              | Proxy assignment and failure handling.                               | none                                                     | none                                                   | none                                          | high       | Separate from ProxyProvider, so proxy management is not fully unified.                      |
| `src/core/browser/BrowserManager.js` and `src/infrastructure/browser/BrowserFactory.js` | Build Playwright proxy config from env / identity.                  | Launch Chromium and contexts, writes browser state in some paths. | Browser navigation/fetch through pages.                              | none                                                     | none                                                   | browser profile / state files possible        | high       | Browser runtime exists in multiple modules.                                                 |
| `src/infrastructure/recon/ReconNavigator.js` and `ReconBrowserContext`                  | Accept proxy / lease / rotator and rotate on retry.                 | Own Recon Playwright runtime.                                     | Navigates OddsPortal and protocol fetch paths.                       | through scanner/stitcher lock setup                      | via repository/stitcher dependencies                   | session/buffer artifacts possible             | high       | Recon has its own runtime stack.                                                            |
| `scripts/ops/recon_scanner_impl.js`                                                     | Instantiates `ProxyRotator` and `ProxyProvider`.                    | Creates navigator handles.                                        | Recon acquisition runtime.                                           | Creates ioredis client and registers Redis health check. | Creates pg pool and DB-backed stores.                  | reads config and can use session buffer paths | high       | Most coupled runtime found.                                                                 |
| `scripts/ops/odds_harvest_pipeline.js`                                                  | unknown explicit proxy from readonly audit                          | Launches Playwright directly.                                     | Uses `fetch` and OddsPortal pages.                                   | none from scan                                           | reads matches, upserts mapping / odds, may spawn L3    | possible runtime artifacts                    | high       | Not suitable as first direct dry-run.                                                       |
| `src/infrastructure/harvesters/ProductionHarvester.js` / `AbstractHarvester`            | Uses `NetworkManager` / `ProxyProvider`.                            | Uses BrowserFactory / context pool.                               | Harvests FotMob pending matches.                                     | no direct Redis                                          | reads pending matches, writes raw data via Persistence | writes raw JSON files in dual-save            | high       | L2 production path is not staging-first.                                                    |
| `scripts/ops/fetch_and_adapt_euro_leagues.js`                                           | no explicit proxy from readonly audit                               | false                                                             | Native `fetch` to football-data CSV URL.                             | false                                                    | reads existing matches/raw referee for alignment       | writes temp file and adapted CSV              | high       | Has no safe no-network mode.                                                                |

Answers:

- proxy manager 是否是独立组件？Partly. `ProxyProvider` is a component, but `NetworkShield`, `ProxyRotator`, browser managers, Recon, and harvest code still maintain overlapping proxy behavior.
- proxy 配置是否集中？Partly. `config/proxy_pool*` centralizes pool values, while older paths still use `active_registry`, env, or legacy wrappers.
- browser runtime 是否集中？No. Browser runtime exists in `BrowserProvider`, `BrowserFactory`, `BrowserManager`, Recon `ReconBrowserContext`, odds harvest direct `chromium.launch`, and Marathon direct `chromium.launch`.
- network policy 是否集中？not_clearly_separated_yet. No single gate currently mediates all `fetch`, Playwright navigation, proxy probes, and child runtime execution.
- rate limit / retry 是否集中？not_clearly_separated_yet. Retry/backoff appears in `HttpClient`, Recon retry coordinator/protocol fetch, odds harvest, NetworkShield, and harvester retry policy.
- Redis / queue 是否和采集逻辑耦合？Yes for Recon: `recon_scanner_impl.js` initializes ioredis and Redlock-backed distributed locking.
- DB write 是否和采集逻辑耦合？Yes for `DiscoveryService`, `ProductionHarvester`, `MarathonService`, `ReconMappingPersistence`, `odds_harvest_pipeline`, `csv_bulk_loader --commit`, and `local_dom_ingestor --commit`.

## 4. Acquisition Order

Correct real acquisition order:

```text
target source selection
  -> legal / terms approval
  -> target scope selection
  -> engine selection
  -> proxy / browser / network preflight
  -> single-target network dry-run
  -> local staging artifact
  -> source manifest / provenance
  -> local dry-run audit
```

Required design constraints:

- target scope must be a single match or very small explicit window
- engine must be registered and classified before runtime use
- proxy / browser / network preflight must be separate from harvest execution
- first network dry-run must write only staging, not DB
- staging artifact must include source URL, capture timestamp, engine version, target scope, sha256, row/object count, and raw response metadata
- manifest must be generated or reviewed before any DB write preflight trusts the artifact
- no training or prediction may run from acquisition output without later gates

## 5. DB Ingestion Order

Schema inspection showed all downstream tables reference `matches(match_id)`:

- `bookmaker_odds_history.match_id -> matches.match_id`
- `raw_match_data.match_id -> matches.match_id`
- `l3_features.match_id -> matches.match_id`
- `match_features_training.match_id -> matches.match_id`
- `predictions.match_id -> matches.match_id`
- related runtime tables such as `odds` and `matches_oddsportal_mapping` also reference `matches`

| table                     | depends_on                                                    | why_order_matters                                                                                                   | allowed_source                                       | allowed_write_gate                  | current_write_status                                                                         | preconditions                                                                    | post_write_validation                                            |
| ------------------------- | ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------- | ----------------------------------- | -------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| `matches`                 | none for identity root                                        | Establishes `match_id`, teams, season, date, status, label fields. All downstream tables depend on it.              | reviewed source manifest / staged acquisition result | future explicit small DB write gate | blocked except existing historical paths, not AI-default                                     | source terms, provenance, duplicate precheck, deterministic match identity       | row count, duplicate check, status/date/team validation          |
| `bookmaker_odds_history`  | `matches.match_id`                                            | Odds need an existing match identity and must preserve bookmaker/market/captured timing/source digest.              | local odds staging / reviewed CSV odds fields        | future odds small-write gate        | blocked for AI; `csv_bulk_loader --commit` and `local_dom_ingestor --commit` are not allowed | existing match, source digest, bookmaker, market, open/close timestamp semantics | unique market check, source_digest, collected_at, leakage review |
| `raw_match_data`          | `matches.match_id`                                            | Raw provider payload must attach to a known match and preserve provider metadata / source hash.                     | single-target raw staging artifact                   | future raw small-write gate         | blocked for AI; local preview only                                                           | existing match, target match identity, raw payload hash, provider metadata       | unique match row, `raw_data` non-empty, data_hash, collected_at  |
| `l3_features`             | `matches.match_id`, usually `raw_match_data` and odds context | Feature computation must avoid post-match leakage and cannot precede raw / odds availability when those are inputs. | approved feature dry-run output                      | future L3 write gate                | blocked                                                                                      | valid raw/odds inputs, leakage audit, feature version                            | feature completeness, no synthetic contamination, computed_at    |
| `match_features_training` | `matches.match_id`, finished label, valid features            | Training rows require finished labels and valid pre-match features; scheduled rows are not trainable labels.        | reviewed feature chain                               | future training feature gate        | blocked                                                                                      | finished match, `actual_result`, L3 readiness, no leakage                        | label count, feature_count, no prediction feedback               |
| `predictions`             | `matches.match_id`, model artifact, feature readiness         | Predictions are outputs, not labels, and must not feed back into training.                                          | approved model inference output                      | future prediction write gate        | blocked                                                                                      | model artifact authorization, feature row readiness, prediction run approval     | prediction count, model_version uniqueness, no training feedback |

Important constraints:

- match identity must be resolved first.
- odds must carry bookmaker, market, captured/open/close timing, source URL/digest, and provenance.
- raw match data must retain provider metadata and source hash.
- `l3_features` must not include post-match leakage features when used for pre-match prediction.
- `match_features_training` requires finished labels and valid features.
- `predictions` cannot be used as training labels.
- synthetic rows and baseline predictions cannot contaminate real training data.

DB row counts before and after this audit remained:

| table                     | rows |
| ------------------------- | ---: |
| `matches`                 |    2 |
| `bookmaker_odds_history`  |    2 |
| `raw_match_data`          |    2 |
| `l3_features`             |    2 |
| `match_features_training` |    2 |
| `predictions`             |    2 |

## 6. First Real Network Dry-Run Candidate

Recommended candidate for Phase 4.78D design: `titan_discovery` capability, but not the current `scripts/ops/titan_discovery.js` runtime.

| field                            | assessment                                                                                                                                                                                                |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| candidate_engine                 | future extracted `titan_discovery` discovery-only adapter                                                                                                                                                 |
| why_candidate                    | Discovery comes before raw / odds / feature writes, and a single-target discovery or tiny date-window dry-run can validate source -> engine -> staging -> manifest without touching DB.                   |
| required_refactor_before_run     | Extract CLI-independent adapter, prove `--dry-run` propagation, disable `FixtureRepository.persist`, require target scope, require no DB pool write path, and emit staging artifact instead of DB writes. |
| proxy/browser needs              | Must use a preflighted `ProxyProvider` / `BrowserProvider` path or a no-browser HTTP-only mode, with explicit network policy gate.                                                                        |
| source terms needs               | FotMob / chosen source terms and allowed-use review must be explicit before any real network request.                                                                                                     |
| target scope                     | One league-season-day window or one explicitly identified target, not all P0 / all leagues.                                                                                                               |
| would_write_db=false requirement | Mandatory. The future dry-run must not instantiate writable persistence or must inject a no-write repository.                                                                                             |
| would_write_staging              | Future design should write a single local staging artifact only after explicit authorization for staging writes. Phase 4.77D did not write staging.                                                       |
| risk                             | Medium-high until runtime is extracted; lower than odds/recon/bulk because it can be made identity-first and DB-free.                                                                                     |

Why not choose others now:

- `fetch_and_adapt_euro_leagues` always downloads external CSV and writes adapted output; no safe no-network mode exists.
- `odds_harvest_pipeline` mixes Playwright, fetch, DB upsert, and optional L3 trigger.
- `recon_scanner` mixes browser, proxy, Redis, DB-backed mapping/status writes, and runtime session artifacts.
- `run_production`, `batch_historical_backfill`, `total_war_pipeline`, and `titan_marathon` are bulk or production paths.

## 7. Gaps / Next Steps

Current gaps:

- proxy manager needs a runtime registry that distinguishes config resolution, health probe, lease allocation, and actual external request permission
- network policy needs a single gate covering native `fetch`, `http(s).request`, Playwright navigation, proxy radar, and child process launch
- browser runtime needs an adapter boundary; current browser launch exists in several modules
- staging artifact schema is not yet defined for first real acquisition output
- manifest generation from acquisition output is not yet formalized
- `titan_discovery` dry-run propagation and persistence suppression need tests before any future use
- `recon_scanner` remains quarantined until proxy/browser/Redis/persistence are separated
- `odds_harvest_pipeline` remains blocked until it is extracted into a no-DB, single-target odds adapter
- legacy bulk orchestrators remain blocked

## 8. Recommended Next Phase

Recommended:

```text
Phase 4.78D: single-target acquisition runtime design
```

Goal:

- choose one candidate engine family
- design a single-target network dry-run runbook
- design proxy / browser / network preflight
- design staging artifact schema
- define source manifest generation from staging output
- still no network, no DB writes, no real staging writes

Alternative:

```text
Phase 4.56A: real network dry-run runbook only after user provides source / engine / match / manifest / terms approval / network authorization
```

## 9. Validation Performed

Read-only validation completed:

- `git status --short`: clean before changes
- `git branch --show-current`: `docs/acquisition-runtime-ingestion-order-phase477d`
- `git rev-parse HEAD`: `e00dd5587b3ebd25aa176c9d947f990857daffdd`
- latest main push CI before start: `success`
- `make dev-ps`: services healthy
- `make data-check`: passed
- `make data-schema-status`: passed
- `make data-dataset-status`: passed
- direct SELECT-only DB row counts: unchanged at `2 / 2 / 2 / 2 / 2 / 2`
- schema inspection via `\d` for `matches`, `bookmaker_odds_history`, `raw_match_data`, `l3_features`, `match_features_training`, `predictions`
- `make data-acquisition-engines`: passed, no DB writes / no external network
- `make data-acquisition-engine-audit`: passed, no DB writes / no external network
- l1-config residue before audit: absent
- `git diff --check`: passed
- `npx prettier --check AGENTS.md docs/_reports/ACQUISITION_RUNTIME_INGESTION_ORDER_PHASE4_77D.md`: passed
- `npm test`: passed
- `npm run test:coverage`: passed; existing thresholds remained `lines>=80`, `functions>=80`, `branches>=80`
- direct SELECT-only DB row counts after validation: unchanged at `2 / 2 / 2 / 2 / 2 / 2`
- l1-config residue after validation: absent

## 10. Explicit Non-Execution

Not executed:

- DB writes
- non-SELECT DB SQL
- external download
- `curl` / `wget` / `git clone`
- external football data access
- external odds data access
- scraping
- browser automation
- harvest
- ingest
- batch backfill
- network dry-run
- bulk harvest
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
