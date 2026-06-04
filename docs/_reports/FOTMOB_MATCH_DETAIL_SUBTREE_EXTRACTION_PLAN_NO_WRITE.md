<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 MD001 -->
# FotMob Match Detail Subtree Extraction Plan No Write

- lifecycle: current-state
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-DETAIL-SUBTREE-EXTRACTION-PLAN-NO-WRITE
- run_id: fotmob_match_detail_subtree_extraction_plan_no_write_v1
- mode: offline_subtree_extraction_plan

## 当前阶段背景

- #1445 确认 /matches/{rc}/{id} 中存在 __NEXT_DATA__ + pageProps。
- match_detail_candidate_observed=2 但 target_match_id_seen=0。
- pageProps 顶层 keys 是 fallback/fetchingLeagueData/ssr/translations（Next.js 框架层）。
- 真正 match detail 数据很可能藏在 props.pageProps.fallback 或更深的 nested subtree。
- 本阶段只设计 subtree scan 方案，不执行 live extraction。

## #1445 Hydration Structure Validation Inheritance

- next_data_parse_ok_count: 2
- pageProps_present_count: 2
- match_detail_candidate_observed_count: 2
- target_match_id_seen_count: 0
- best_candidate_path: props.pageProps
- json_validated_count: 0
- raw_write_eligible_count: 0

## Why props.pageProps Is Only the Candidate Root

- target_match_id_seen_count=0 — match id 不在 pageProps 直接 key 中。
- pageProps 顶层是 Next.js 框架配置（fallback, fetchingLeagueData, ssr, translations）。
- 历史 production code (FotMobRawDetailFetcher.js) 从 __NEXT_DATA__.props.pageProps 提取数据。
- match detail 数据应在 pageProps. 的 nested subtree 中（fallback cache entry）。

## Subtree Extraction Plan

- root path: `props.pageProps`
- key search terms: matchId, id, header, general, content, matchFacts, stats, lineup
- persistence policy: metadata_only_no_body_no_json

## Priority Path Matrix

| Priority | Path | Purpose |
|---|---|---|
| 1 | `props.pageProps.fallback` | primary cache candidate from Next.js SSG |
| 2 | `props.pageProps.fallback.*.data` | potential data wrapper under fallback |
| 3 | `props.pageProps.fallback.*.matchDetails` | match details cache entry |
| 4 | `props.pageProps.fallback.*.content` | content subtree under cache |
| 5 | `props.pageProps.fallback.*.header` | header subtree under cache |
| 6 | `props.pageProps.fallback.*.general` | general subtree under cache |
| 7 | `props.pageProps.*.match` | match data at pageProps level |
| 8 | `props.pageProps.*.matchData` | explicit match data key |
| 9 | `props.pageProps.*.matchDetails` | explicit match details key |
| 10 | `props.pageProps.*.content` | content at pageProps level |

## Scoring Rules

| Signal | Score |
|---|---:|
| target match_id found in subtree | 5 |
| key path or name contains matchId/id and value matches target | 4 |
| subtree contains 'header' key | 3 |
| subtree contains 'general' key | 3 |
| subtree contains 'content' key | 3 |
| subtree contains 'matchFacts' key | 2 |
| subtree contains 'stats' key | 2 |
| subtree contains 'lineup' key | 2 |
| subtree contains 'events' key | 2 |
| subtree contains 'homeTeam' / 'awayTeam' / 'teams' key | 2 |
| subtree contains 'status' key | 1 |
| subtree contains 'fixture' key | 1 |
| subtree contains 'score' key | 1 |
| subtree contains 'tournament' / 'league' key | 1 |
| subtree only contains CountryCodes/Language/translations/static config | -3 |
| subtree lacks target match_id AND lacks team names | -5 |
| subtree is clearly translation/config dictionary | -5 |

## Candidate Classification Rules

| Min Score | State |
|---:|---|
| 10 | match_detail_subtree_strong_candidate |
| 6 | match_detail_subtree_weak_candidate |
| 3 | partial_match_detail_subtree |
| -999 | generic_or_irrelevant_subtree |

## Next Controlled Subtree Extraction Plan

- **phase**: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-MATCH-DETAIL-SUBTREE-EXTRACTION-NO-WRITE
- **route_template**: https://www.fotmob.com/matches/{route_code}/{match_id}
- **selected_match_ids**: 4813722, 4813492
- **selected_route_codes**: 2ygkcb, 2ynv4k
- **max_samples**: 2
- **max_network_requests**: 2
- **max_body_bytes**: 524288
- **max_subtree_scan_depth**: 8
- **max_key_paths_recorded**: 200
- **max_candidate_paths_recorded**: 20
- **allowed_metadata**: key path metadata, data type metadata, key presence booleans, candidate subtree path, candidate score
- **forbidden_persistence**: full HTML body, full __NEXT_DATA__ JSON, full pageProps, full match detail subtree value, raw JSON file
- **success_criteria**: find at least one subtree with score >= 6, detect target match_id in subtree, identify viable path for match detail extraction
- **failure_criteria**: max depth reached without finding any candidate with score > 0, all subtrees are generic config/translations
- **stop_conditions**: HTTP 403 on any route → stop all, HTTP 429 on any route → stop all, captcha/bot page detected → stop all, body exceeds max_body_bytes without finding NEXT_DATA → stop
- **next_phase_after_success**: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-DETAIL-SUBTREE-VALIDATION-NO-WRITE
- **notes**: Even if strong candidate found, next phase is subtree validation no-write, not raw JSON write. Full subtree extraction requires separate validation phase. L2 raw harvesting remains blocked until json_validated.

## Raw Write Readiness Gate

- json_validated_count: 0
- raw_write_eligible_count: 0
- raw_write_blocked_until_json_validated: True
- subtree_validation_required: True

## No-Write Safety Review

- network_fetch_performed: False (pass)
- response_body_read: False (pass)
- bounded_body_read_performed: False (pass)
- full_body_read_performed: False (pass)
- full_html_saved: False (pass)
- raw_response_body_saved: False (pass)
- html_body_saved: False (pass)
- full_next_data_saved: False (pass)
- raw_json_write_performed: False (pass)
- db_read_performed: False (pass)
- db_write_performed: False (pass)
- production_db_write_performed: False (pass)
- fotmob_raw_match_payloads_write_performed: False (pass)
- raw_match_data_write_performed: False (pass)
- feature_parse_performed: False (pass)
- scheduler_enabled: False (pass)
- raw_write_ready_marked: False (pass)
- browser_automation_performed: False (pass)
- captcha_bypass_performed: False (pass)
- proxy_rotation_performed: False (pass)

## Remaining Blockers

- 本阶段没有联网、没有读取 body、没有保存 HTML、没有保存 NEXT_DATA、没有保存 raw JSON、没有写 DB
- 下一阶段只是 controlled subtree extraction no-write，仍然不是 raw JSON 入库
- L2 raw harvesting 仍然 blocked

## Recommended Next Phase

- **FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-MATCH-DETAIL-SUBTREE-EXTRACTION-NO-WRITE**

