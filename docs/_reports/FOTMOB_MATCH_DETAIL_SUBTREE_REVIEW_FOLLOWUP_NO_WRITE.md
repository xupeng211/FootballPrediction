<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 MD001 -->
# FotMob Match Detail Subtree Review Follow-Up No Write

- lifecycle: current-state
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-DETAIL-SUBTREE-REVIEW-FOLLOWUP-NO-WRITE
- run_id: fotmob_match_detail_subtree_review_followup_no_write_v1
- mode: offline_subtree_review_followup

## 当前阶段背景

- #1447 已完成 controlled subtree extraction no-write，并给出负向结果。
- 本阶段没有联网、没有读取 HTML body、没有保存 HTML body、没有保存 NEXT_DATA、没有保存 raw JSON、没有写 DB。
- 目标是复盘为什么只命中 notableMatches，并规划下一阶段 keyspace review no-write。

## #1447 Negative Finding Inheritance

- fallback_present_count: 2
- target_match_id_seen_count: 0
- strong_candidate_count: 0
- weak_candidate_count: 0
- partial_candidate_count: 0
- generic_or_irrelevant_count: 2
- best_candidate_path: props.pageProps.fallback.notableMatches:en:USA
- best_candidate_score: -5

## Why NotableMatches Is Not Match Detail

- notableMatches 是通用推荐/导航 fallback key，不含目标 match_id、球队名或 header/general/content/matchFacts/stats/lineup/events/teams。
- target_match_id_seen_count=0 是关键阻断：没有目标比赛身份，不能把任何 subtree 视为已验证详情。
- #1447 的 score=-5，state=generic_or_irrelevant_subtree，说明当前路径只应作为排除项。

## Route / Locale / Keyspace Review

- 当前结果可能来自 route/locale/header 返回的通用 fallback，也可能是只从 props.pageProps/fallback 扫描导致范围过窄。
- 仍建议下一阶段先保持 max_body_bytes=524288：#1447 两个 response 均低于 512KB，问题不是 body 截断。
- 下一阶段应扫描 bounded __NEXT_DATA__ 的 top-level keyspace metadata，而不是继续只扫 fallback.notableMatches。
- slug、route code、team names 应作为 metadata scoring signal；也要检查 SWR/Apollo/Relay/react-query/dehydratedState/fallback cache key 名称。

## Historical Code Review

- files_reviewed: 9
- relevant_paths_found: src/parsers/fotmob/NextDataParser.js, src/parsers/fotmob/MatchParser.js, src/parsers/fotmob/MatchStatsParser.js, src/infrastructure/services/FotMobRawDetailFetcher.js, scripts/ops/pageprops_v2_no_write_preview.js
- suspected parser paths: props.pageProps.content, props.pageProps.general, props.pageProps.header, content.matchFacts, content.stats, content.lineup。
- missing evidence: 没有历史 parser 证明 props.pageProps.fallback.notableMatches 是 match detail。

## Route Variant Review

| Variant | Recommendation | Reason |
|---|---|---|
| /matches/{route_code}/{match_id} | keep | current working route parses __NEXT_DATA__/pageProps/fallback but only found generic notableMatches |
| /zh-Hans/matches/{route_code}/{match_id} | review next | target user seeds were supplied with zh-Hans locale and should be compared as metadata only |
| /en/matches/{route_code}/{match_id} | review next | English locale variant may change hydration keyspace or fallback cache keys |
| original user URL path without fragment | review next | seed slug paths provide canonical slug evidence without using the fragment as a request path |
| /matches/{slug}/{route_code} | defer unless slug evidence is used | supported by seed URL shape, but should only be executed after keyspace plan selects slug routes |

## Keyspace Review Next Plan

- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-KEYSPACE-REVIEW-NO-WRITE
- max_samples: 2
- max_network_requests: <= 2
- max_body_bytes: <= 524288
- max_key_paths_recorded: <= 500
- max_scan_depth: <= 12
- value persistence: forbidden

## Raw Write Readiness Gate

- json_validated_count: 0
- raw_write_eligible_count: 0
- raw_write_blocked_until_json_validated: true
- keyspace_review_required: true
- 下一阶段只是 hydration keyspace review no-write，仍然不是 raw JSON 入库。

## No-Write Safety Review

- network_fetch_performed: false
- response_body_read: false
- html_body_saved: false
- full_next_data_saved: false
- raw_json_write_performed: false
- db_write_performed: false
- scheduler_enabled: false
- feature_parse_performed: false
- browser_automation_performed: false
- captcha_bypass_performed: false
- proxy_rotation_performed: false

## Remaining Blockers

- 尚未找到包含目标 match_id 的 match detail subtree。
- notableMatches 已排除，但完整 bounded keyspace 仍未复盘。
- route variant 只完成规划，尚未执行下一阶段受控 review。

## Recommended Next Phase

- **FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-KEYSPACE-REVIEW-NO-WRITE**
