<!-- markdownlint-disable MD013 MD012 -->
# FotMob Safe Parser Schema Reuse Plan No Write

- lifecycle: current-state
- phase: SAFE-PARSER-SCHEMA-REUSE-PLAN-NO-WRITE
- run_id: fotmob_safe_parser_schema_reuse_plan_no_write_v1
- mode: offline_safe_parser_schema_reuse_plan

## 1. 当前阶段背景

- 历史审计确认：项目过去成功采集了 2,501 条 FotMob raw detail JSON（64.58% 覆盖，平均 205KB）。
- 当前保守路线（/matches/{route_code}/{match_id} HTML hydration, direct API, endpoint candidate probe）全部失败或跳过。
- 本阶段整理历史资产中可安全复用的 parser/schema/fixture/validation 部分，不恢复任何 browser/session/cookie/anti-bot 体系。

## 2. 安全可复用资产清单

| Asset ID | Category | Path | Symbol | Recommended Use |
|---|---|---|---|---|
| parser-nextdata | parser | src/parsers/fotmob/NextDataParser.js | transformToApiFormat, extractFromHtml, validateNextDataStructure | Parse HTML/JSON responses from any FotMob data source into canonical apiFormat |
| parser-match | parser | src/parsers/fotmob/MatchParser.js | parseMatchData, firstValue, resolveMatchId | Parse match-level metadata regardless of data source format |
| parser-stats | parser | src/parsers/fotmob/MatchStatsParser.js | extractMatchStats, normalizeStat | Extract and normalize match statistics from any source |
| parser-team | parser | src/parsers/fotmob/TeamParser.js | parseTeamData | Parse team identity fields |
| parser-player | parser | src/parsers/fotmob/PlayerParser.js | parsePlayerData | Parse player identity and stats from lineup |
| parser-xg | parser | src/parsers/fotmob/XGExtractor.js | extractAllStats, extractXG | Extract expected goals data from match statistics |
| parser-league | parser | src/parsers/fotmob/LeagueParser.js | parseLeagueData | Parse league and tournament context |
| schema-raw-payloads | schema | database/migrations/V26.5__create_fotmob_raw_match_payloads.sql | CREATE TABLE fotmob_raw_match_payloads | Reuse table structure for future raw JSON storage (not for direct DB write in this phase) |
| schema-raw-match-data | schema | database/migrations/V12.6__allow_numeric_fotmob_ids_in_raw_match_data.sql | ALTER TABLE raw_match_data match_id constraint | Reuse ID format flexibility for future match_id storage |
| fixture-match-success | fixture | tests/fixtures/match_success.json | match_success.json full payload structure | Use as canonical payload shape reference; adapt new data sources to this structure |
| validation-hash | validation | src/infrastructure/services/FotMobRawDetailFetcher.js | sha256CanonicalJson, canonicalizeJson, HASH_STRATEGY_STABLE_RAW_PAYLOAD_V1 | Reuse hash strategy for payload integrity verification |
| validation-shape | validation | src/infrastructure/services/FotMobRawDetailFetcher.js | validateCanonicalRawDataShape, looksLikeValidRawDetail | Reuse shape validation to verify future payloads match canonical structure |
| validation-status | validation | src/infrastructure/services/FotMobRawDetailFetcher.js | classifyStatus, isBlockHttpStatus (403, 429) | Reuse HTTP status classification for future data source evaluation |
| report-collection | report | docs/_reports/FOTMOB_COLLECTION_REPORT.md | Collection health report with schema diff evidence | Reference for historical payload shape and collection metrics |
| report-adg60 | report | docs/_reports/FOTMOB_ADG60_RAW_JSON_DB_STORAGE_REVIEW_NO_FEATURE_PARSE.md | ADG60 storage review: 32 samples, JSONB structural integrity confirmed | Reference for JSONB storage architecture validation |
| state-current | report | docs/data/FOTMOB_CURRENT_STATE.md | Current pipeline state: raw_write_ready_count=0, ADG59B completed | Reference for current pipeline governance and authorization requirements |

Total safe reuse: 16

## 3. 只能只读参考资产清单

| Asset ID | Category | Path | Risk Reason | Safety Status |
|---|---|---|---|---|
| risk-fotmob-api-client | browser_session | src/infrastructure/network/FotMobApiClient.js | Requires Playwright browser bootstrap for cf_clearance cookie capture; targets /api/data/matchDetails which returns 403 without session. Browser/session/cookie/anti-bot stack. | read_only_reference_only |
| risk-session-manager | browser_session | src/infrastructure/network/SessionManager.js | Automates Turnstile bypass; manages 22-node port map for FotMob sessions; opens visible browsers; captures and persists Cloudflare cookies. | do_not_reactivate |
| risk-auto-auth | browser_session | src/infrastructure/auth/AutoAuthManager.js | Opens visible browser for FotMob login/cookie capture; saves authenticated session state. | do_not_reactivate |
| risk-session-warmer | browser_session | src/infrastructure/harvesters/SessionWarmer.js | Progressive navigation + proxy rotation + Cloudflare cookie establishment methodology (though targets OddsPortal, technique is site-agnostic). | read_only_reference_only |
| risk-stealth-navigator | anti_bot | src/infrastructure/harvesters/StealthNavigator.js | Bezier mouse movement, scroll simulation, vision healing, CAPTCHA bypass primitives. | do_not_reactivate |
| risk-stealth-fingerprint | anti_bot | src/infrastructure/network/StealthFingerprint.js | 30+ spoofed browser fingerprint pool; WebGL renderer pool; matches capture_auth.js fingerprint for FotMob. | do_not_reactivate |
| risk-stealth-config | anti_bot | src/infrastructure/network/enhanced_stealth_config.js | Enhanced stealth configuration for anti-detection. | do_not_reactivate |
| risk-browser-factory | browser_core | src/infrastructure/browser/BrowserFactory.js | Generic Playwright browser lifecycle; not FotMob-specific but enables anti-bot bypass via stealth scripts. | read_only_reference_only |
| risk-context-pool | browser_core | src/infrastructure/browser/ContextPoolManager.js | Playwright context pool management for multi-session harvesting. | read_only_reference_only |
| risk-fotmob-extractor | browser_core | src/infrastructure/services/FotMobExtractor.js | Uses Playwright browser; league-level scraping with NetworkInterceptor; browser-based DOM scanning. | do_not_reactivate |
| risk-network-interceptor | browser_core | src/infrastructure/services/NetworkInterceptor.js | Passive API endpoint discovery via Playwright page request/response events; requires browser runtime. | read_only_reference_only |
| risk-archive-v6 | archive | archive_vault_2026/archive_v6/* | Full harvesting pipeline: capture_auth.js, inject_golden_cookies.js, auto_harvest_v6.js, sniffer_harvest_v6.js. Contains cookie injection, auth capture, automated harvesting with anti-bot bypass. | do_not_reactivate |
| risk-archive-legacy | archive | archive_vault_2026/legacy_v446/* | Legacy hyper_swarm_stealth.js and related scripts; massive-scale anti-bot harvesting infrastructure. | do_not_reactivate |

Total read-only reference: 13

## 4. Canonical Payload Shape 草案

| Section | Required | Evidence | Purpose |
|---|---|---|---|
| general | True | match_success.json, NextDataParser.transformToApiFormat, collection report schema diff | Match identity and status |
| header | True | match_success.json, NextDataParser.transformToApiFormat | Tournament and venue context |
| content.stats | True | match_success.json (Possession, Shots, ShotsOnTarget, xG), NextDataParser._meta.hasStats | Match statistics |
| content.lineup | True | match_success.json (homeTeam/awayTeam with starters + subs), NextDataParser._meta.hasLineup | Team lineups with player details |
| content.shotmap | False | match_success.json (array of shot objects), NextDataParser._meta.hasShotmap | Shot map with xG coordinates |
| content.events | True | match_success.json (Goal, YellowCard events with minute/score/player) | Match incidents/timeline |
| xG/expectedGoals | False | match_success.json content.stats.xG, content.shotmap[].xG | Expected goals for advanced analysis |
| tournament/venue | False | match_success.json header.tournament, header.venue, _extra fields | Match context metadata |

## 5. Source Adapter 设计原则

- future FotMob source → map to canonical general/header/content
- alternative source → adapter layer normalizes equivalent fields
- paid source → same canonical mapping, different auth layer
- historical fixture → validate against canonical shape

## 6. Raw Write Gate

- json_validated_count: 0
- raw_write_eligible_count: 0
- raw_write_allowed: false
- db_write_allowed: false
- raw_write_blocked_until_validated_payload: true
- 需要 validated raw detail payload + schema mapping review + parser test coverage + explicit authorization

## 7. 推荐下一步

- **HISTORICAL-FOTMOB-PAYLOAD-SHAPE-RECONSTRUCTION-READONLY**

本阶段明确：不恢复旧浏览器/cookie/anti-bot体系，不使用 Playwright，不抓 cookie，不绕反爬，不写 DB，不 raw write。只复用安全 parser/schema/fixture/validation 资产。
