<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 MD001 -->
# FotMob Hydration Structure Validation No Write

- lifecycle: current-state
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-STRUCTURE-VALIDATION-NO-WRITE
- run_id: fotmob_hydration_structure_validation_no_write_v1
- mode: controlled_hydration_structure_validation_no_write

## 当前阶段背景

- #1444 确认 /matches/{rc}/{id} 中存在 __NEXT_DATA__ + pageProps。
- 本阶段在内存中解析 __NEXT_DATA__ JSON 结构寻找 match detail subtree。
- 只保存结构 metadata（key paths, key presence, score），不保存完整 JSON。

## #1444 Inspection Inheritance

- hydration_structure_observed_count: 2
- route_template: https://www.fotmob.com/matches/{route_code}/{match_id}
- selected_match_ids: ['4813722', '4813492']
- selected_route_codes: ['2ygkcb', '2ynv4k']
- full_html_saved: False
- raw_json_write_performed: False
- json_validated_count: 0
- raw_write_eligible_count: 0

## Selected Validation Samples

- match_id=4813722, route_code=2ygkcb, pair=Liverpool vs Manchester United
- match_id=4813492, route_code=2ynv4k, pair=Everton vs Manchester United

## Route Template

`https://www.fotmob.com/matches/{route_code}/{match_id}`

## Bounded Body Validation Summary

- allow_network_probe: True
- max_network_requests: 2
- network_requests_attempted: 2
- next_data_parse_ok_count: 2
- pageProps_present_count: 2
- target_match_id_seen_count: 0
- match_detail_candidate_observed_count: 2
- partial_match_detail_candidate_count: 0
- generic_structure_only_count: 0
- structure_not_match_detail_count: 0
- blocked_count: 0
- invalid_count: 0
- not_html_count: 0

## Match Detail Candidate Decision

- viable candidates: 2
- best score: 6
- next action: subtree extraction plan

| Validation ID | Match ID | ND Parse | pageProps | mid Seen | Candidate Score | Top pageProps Keys | State |
|---|---|---|---:|---:|---|---|
| val-s01 | 4813722 | True | True | False | 6 | fallback, fetchingLeagueData, ssr, translations | hydration_match_detail_candidate_observed |
| val-s02 | 4813492 | True | True | False | 6 | fallback, fetchingLeagueData, ssr, translations | hydration_match_detail_candidate_observed |

## Raw Write Readiness Gate

- json_validated_count: 0
- raw_write_eligible_count: 0
- raw_write_blocked_until_json_validated: True
- controlled_extraction_validation_required: True

## Recommended Next Phase

- **FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-DETAIL-SUBTREE-EXTRACTION-PLAN-NO-WRITE**

