# Phase 5.21L2T0 Single-League Target Discovery / Source Inventory Preflight

## 1. Executive Summary

Phase 5.21L2S 的 source-controlled manifest proposal 因 `candidate_targets=0` 处于 `blocked_pending_authorized_target_discovery`。本阶段在用户明确授权下新增 controlled FotMob source inventory discovery，用于发现 Ligue 1 2025/2026 的真实 FotMob match targets。

本阶段只允许 source inventory / league fixture / schedule discovery；不写 DB，不写 `raw_match_data`，不抓 match detail pageProps，不做 controlled write，不做 parser/features/training。

## 2. Current DB Baseline

Preflight 前只读 baseline：

| table                   | rows |
| ----------------------- | ---: |
| matches                 |   10 |
| raw_match_data          |   18 |
| bookmaker_odds_history  |    2 |
| l3_features             |    2 |
| match_features_training |    2 |
| predictions             |    2 |

Additional baseline:

- protected tables with existing rows: 2 (`l3_features`, `match_features_training`)
- `fotmob_pageprops_v2` rows: 8

## 3. Discovery Authorization / Guardrails

- `network_authorization=yes`
- `source_inventory_authorization=yes`
- `concurrency=1`
- `retry=0`
- no browser/proxy/captcha bypass
- no match detail fetch
- no DB write
- no full body/json print/save

## 4. Source Inventory Route

Planned route:

- route: `source_inventory`
- endpoint family: FotMob league/source inventory
- target scope: `league_id=53`, `league_name=Ligue 1`, `season=2025/2026`

Execution result:

- request count: 1
- status code: 404
- content type: `text/html; charset=utf-8`
- parse status: not attempted after non-2xx response
- blocked/captcha markers: none detected
- full body/json printed: no
- full body/json saved: no

The authorized route used by the script was:

- `https://www.fotmob.com/api/leagues?id=53&season=2025%2F2026`

The route returned 404, so the phase stopped without trying an alternate endpoint, browser/proxy, retry, or match detail request.

## 5. Known Completed Exclusions

The following seeded v2 targets remain excluded:

| external_id | fixture                      |
| ----------- | ---------------------------- |
| 4830746     | Angers vs Strasbourg         |
| 4830747     | Auxerre vs Nice              |
| 4830748     | Le Havre vs Marseille        |
| 4830750     | Metz vs Lorient              |
| 4830751     | Monaco vs Lille              |
| 4830752     | Paris Saint-Germain vs Brest |
| 4830753     | Rennes vs Paris FC           |
| 4830754     | Toulouse vs Lyon             |

## 6. Candidate Discovery Result

| metric                      | value |
| --------------------------- | ----: |
| discovered_raw_target_count |     0 |
| excluded_completed_count    |     0 |
| duplicate_removed_count     |     0 |
| invalid_identity_count      |     0 |
| candidate_targets_count     |     0 |

Result status:

- `target_population_status=source_inventory_route_unavailable`
- `required_next_step=source_inventory_route_adjustment_or_additional_authorization`
- no invented `external_id`
- no fabricated `match_id`, teams, or kickoff time
- Phase 5.21L2T must not start from this manifest state

## 7. Candidate Targets Summary

No candidate targets were discovered because the authorized source inventory route returned 404.

## 8. Manifest Update Result

Manifest path:

- `docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json`

The manifest was not updated because the source inventory request failed before candidate extraction. The existing proposal remains at:

- `known_completed_targets=8`
- `candidate_targets=0`
- no invented `external_id`
- no fabricated target data

## 9. Verification Results

Completed before the controlled network execution and refreshed during T0B:

- new source inventory tests: passed (`68/68`)
- adapter tests: passed (`5/5`)
- related unit tests: passed (`374/374`)
- `npm test`: passed
- `npm run test:coverage`: passed
- ESLint for the new script/test: passed
- Prettier for touched files: passed before source inventory execution
- `git diff --check`: passed before source inventory execution
- DB row counts unchanged after failed source inventory request
- no `tests/fixtures/l1-config-*` residue
- `docs/_staging_preview` absent

Not run because the route stopped the phase:

- PR CI
- main push CI

## L2T0B Existing L1 Schedule Discovery Audit

### Why this audit was needed

T0 was blocked because the guessed source inventory route returned HTTP 404:

- guessed route: `https://www.fotmob.com/api/leagues?id=53&season=2025%2F2026`
- no alternate endpoint, retry, browser, proxy, or match detail request was executed
- no manifest proposal update happened because no real candidates were discovered

The user flagged that the project already had L1 schedule discovery / fixture discovery capability. Continuing to write a new source inventory fetcher from scratch would duplicate existing L1 work and risk diverging from the route/parser already used by the project.

### Searched files / modules

T0B searched and read the relevant L1/data files only:

- `src/infrastructure/services/DiscoveryService.js`
- `src/infrastructure/services/DiscoveryParser.js`
- `src/infrastructure/services/DiscoveryAttributeMapper.js`
- `src/infrastructure/services/DiscoveryDataValidator.js`
- `src/infrastructure/shared/helpers/discoveryParserShared.js`
- `src/infrastructure/services/L1ConfigManager.js`
- `src/infrastructure/services/SeasonStrategy.js`
- `src/infrastructure/services/FixtureRepository.js`
- `scripts/ops/l1_discovery_safe_preview.js`
- `scripts/ops/titan_discovery.js`
- `scripts/ops/seed_fixtures.js`
- `scripts/ops/fixture_harvester_l1.js`
- `tests/unit/DiscoveryService.discoverCandidates.test.js`
- `tests/unit/l1_discovery_safe_preview.test.js`
- `docs/_reports/L1_DISCOVERY_SAFE_PREVIEW_WRAPPER_PHASE5_03L1.md`
- `docs/_reports/L1_DISCOVERY_CANDIDATES_EXTRACTION_PHASE5_04L1.md`
- `docs/_reports/L1_CONTROLLED_NETWORK_CANDIDATES_PREVIEW_PHASE5_05L1.md`
- `docs/_reports/TITAN_DISCOVERY_NO_NETWORK_PHASE4_58C.md`
- `Makefile`
- `AGENTS.md`

### Candidate capabilities found

| Capability                        | Path                                                                                             | Input                                                                                    | Output                                                                                    | Network                                                   | DB write                                  | Dry/no-write                                       | Browser/proxy                          | Useful fields              | Tests/docs                                                             | Safety classification    | Reuse decision                                                                                 |
| --------------------------------- | ------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- | --------------------------------------------------------- | ----------------------------------------- | -------------------------------------------------- | -------------------------------------- | -------------------------- | ---------------------------------------------------------------------- | ------------------------ | ---------------------------------------------------------------------------------------------- |
| L1 candidates-only discovery      | `src/infrastructure/services/DiscoveryService.js` / `discoverCandidates()`                       | `source=fotmob`, `scope`, `leagueId`, `season`, `date`, `maxTargets<=10`, injected fetch | normalized candidates with `match_id`, `external_id`, teams, `match_date`, `status`       | only with injected safe client and explicit authorization | no, `writeDb=false`, disabled repository  | yes                                                | blocked by options                     | yes                        | `DiscoveryService.discoverCandidates.test.js`, Phase 5.04/5.05 reports | safe candidates preview  | `reusable_with_adapter` because date/maxTargets constraints do not cover 20-50 season manifest |
| L1 safe wrapper                   | `scripts/ops/l1_discovery_safe_preview.js`                                                       | make/CLI preview args                                                                    | stdout JSON preview/candidates                                                            | default no; controlled preview only                       | no                                        | yes                                                | blocked                                | yes                        | `l1_discovery_safe_preview.test.js`, Make targets                      | safe wrapper             | `route_hint_only` and reusable orchestration pattern                                           |
| L1 parser stack                   | `DiscoveryParser`, `DiscoveryDataValidator`, `DiscoveryAttributeMapper`, `discoveryParserShared` | FotMob league/source JSON                                                                | fixtures with `match_id`, `external_id`, `home_team`, `away_team`, `match_date`, `status` | no                                                        | no                                        | pure parser                                        | no                                     | yes                        | unit tests through `DiscoveryService.discoverCandidates.test.js`       | parser-only safe         | `parser_only_reusable`                                                                         |
| L1 route/config/season formatting | `L1ConfigManager.buildLeagueApiUrl()`, `SeasonStrategyFactory`                                   | league id and season                                                                     | `https://www.fotmob.com/api/data/leagues?id=53&season=20252026`                           | no                                                        | no                                        | yes                                                | no                                     | route/season identity      | `L1ConfigManager.test.js`, `SeasonStrategy.test.js`                    | safe route/config helper | `reuse_ready` for route construction                                                           |
| Legacy L1 discovery CLI           | `scripts/ops/titan_discovery.js`                                                                 | broad CLI options                                                                        | scan report after `DiscoveryService.discover()`                                           | yes                                                       | yes through `FixtureRepository.persist()` | dry-run flag exists but not trusted by prior audit | may use browser/proxy/runtime fallback | yes after persist path     | docs mark blocked/deprecated for agents                                | unsafe legacy/admin      | `unsafe_or_deprecated`                                                                         |
| Seed entrypoint                   | `scripts/ops/seed_fixtures.js`                                                                   | league/season/all                                                                        | writes fixtures through `DiscoveryService.discover()`                                     | yes                                                       | yes                                       | no safe T0B path                                   | may use L1 runtime                     | yes after write path       | L1 docs                                                                | unsafe for T0B           | `unsafe_or_deprecated`                                                                         |
| OddsPortal recovery harvester     | `scripts/ops/fixture_harvester_l1.js`                                                            | hardcoded Bundesliga/OddsPortal browser flow                                             | generated/persisted fixtures                                                              | yes                                                       | yes                                       | no                                                 | Playwright/browser                     | no FotMob source inventory | none for this scope                                                    | unsafe and wrong source  | `not_reusable`                                                                                 |
| Fixture repository                | `src/infrastructure/services/FixtureRepository.js`                                               | normalized fixtures                                                                      | `matches` writes / recon mapping side effects                                             | no by itself                                              | yes                                       | no for T0B                                         | no                                     | write path only            | unit tests                                                             | write component          | `not_reusable`                                                                                 |

### Reuse / consolidation decision

Chosen path: **B - reusable_with_adapter**.

`discoverCandidates()` already proves the safe split between L1 fetch/parse candidates and DB persistence, but it is scoped to `date` and `MAX_TARGETS<=10`. The single-league manifest needs a 20-50 target season inventory. T0B therefore did not call legacy runners and did not build a new independent parser. Instead it added a thin adapter:

- `src/infrastructure/services/FotMobSourceInventoryAdapter.js`
- reuses `L1ConfigManager` and `SeasonStrategyFactory` for the known L1 route and season format
- reuses `DiscoveryParser` for source JSON extraction and field normalization
- does not import `DiscoveryService`, `FixtureRepository`, `titan_discovery`, `ProductionHarvester`, odds pipeline, browser, proxy, or `pg`
- performs no network by itself; tests use fake payloads only

Current T0 script changed as follows:

- before: hand-built source inventory URL used `/api/leagues` and failed with HTTP 404
- after: source inventory URL is built through the adapter using existing L1 route knowledge: `/api/data/leagues?id=53&season=20252026`
- before: T0 carried a local source inventory matcher as the primary parse path
- after: T0 uses the adapter/`DiscoveryParser` for parse/normalize and keeps the manifest policy, exclusions, caps, and guardrails locally
- no live retry was executed in T0B

### Duplication risk assessment

The duplicate-development risk was real. The repo already had a safe L1 candidates path and a documented route family. Rebuilding a separate source inventory fetcher would have duplicated route selection, season formatting, match-id normalization, team extraction, status mapping, and dedupe behavior.

The adapter keeps the remaining L2T0-specific logic only where it belongs:

- manifest target shape
- exclusion of existing `fotmob_pageprops_v2` completed targets
- 20-50 candidate cap and readiness status
- raw/pageProps/parser/training guardrails

One behavior changed intentionally: duplicate external IDs are now deduped inside the reused L1 parser before the manifest policy layer, so `duplicate_removed_count` only reports duplicates that survive adapter normalization.

### T0B non-execution

T0B executed no external FotMob/network request. It did not retry the 404, did not switch live endpoint, did not launch browser/proxy, did not fetch match detail/pageProps, did not write DB, did not write `raw_match_data`, did not update `matches`, did not implement parser/features/training, and did not invent targets.

## 10. Recommended Next Phase

Not ready. Recommended next phase:

- Phase 5.21L2T0C: authorized source inventory retry using reused L1 discovery path
- requires explicit network authorization
- no DB write
- no `raw_match_data` write
- no `matches` write
- no match detail pageProps acquisition unless a later phase explicitly authorizes Phase 5.21L2T
- use `FotMobSourceInventoryAdapter` / existing L1 `/api/data/leagues` route
- update manifest only with real candidates discovered from source inventory
- no parser/features/training

## 11. Explicit Non-Execution

Confirmed by design before execution:

- no DB writes
- no `raw_match_data` writes
- no `bookmaker_odds_history` writes
- no match detail pageProps fetch
- no controlled write
- no schema migration
- no `matches` writes
- no parser implementation
- no feature extraction
- no `l3_features` write
- no `match_features_training` write
- no training/prediction
- no browser/proxy/captcha bypass
- no full raw_data/pageProps/source body print/save
- no file deletion
- no invented `external_id` / fake target data
