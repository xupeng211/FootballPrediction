<!-- markdownlint-disable MD013 MD034 -->

# FotMob Controlled JSON Probe No Write

- lifecycle: current-state
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-JSON-PROBE-NO-WRITE
- run_id: fotmob_controlled_json_probe_no_write_v1
- mode: controlled_network_probe_no_write

## 当前阶段背景

- 从 #1438 known match page seed parse 进入。
- 使用 #1438 解析出的真实 FotMob match_id 进行 JSON endpoint 探测。
- 最多 3 个样本，最多 3 个 endpoint / 样本，最多 9 个 HTTP request。
- 只保存 metadata，不保存 response body。

## #1438 Seed Inheritance

- user_seed_count: 12
- parsed_count: 12
- route_candidate_count: 12
- current_target_match_true_count: 7
- exact_or_reversed_pair_count: 7
- route_validated_count: 0
- json_validated_count: 0
- raw_write_eligible_count: 0

## Selected Probe Samples

1. Manchester United vs Liverpool (route_code=2ygkcb, match_id=4813722)
2. Manchester United vs Everton (route_code=2ynv4k, match_id=4813492)
3. Manchester United vs Tottenham Hotspur (route_code=2xqo0r, match_id=4813622)

## Endpoint Candidate Plan

| # | Endpoint Template | Reason |
|---|---|
| 1 | `https://www.fotmob.com/api/matchDetails?matchId={match_id}` | Standard FotMob matchDetails API without geo/locale params |
| 2 | `https://www.fotmob.com/api/matchDetails?matchId={match_id}&ccode3=USA` | FotMob matchDetails API with USA country code for content negotiation |
| 3 | `https://www.fotmob.com/api/matchDetails?matchId={match_id}&timezone=UTC` | FotMob matchDetails API with UTC timezone override |

## Network Probe Summary

- allow_network_probe: True
- max_network_requests: 9
- network_requests_attempted: 9
- status_code_summary: {'404': 9}
- content_type_summary: {}
- json_parse_attempted_count: 0
- json_parse_ok_count: 0
- html_detected_count: 0
- blocked_count: 0
- invalid_count: 9
- not_json_count: 0

## Probe Result Details

| Probe ID | Match ID | Endpoint | Status | Content-Type | JSON OK | Top-Level Keys | Validation State | Stop Reason |
|---|---|---|---|---|---|---|---|---|
| probe-user-seed-04-ep01 | 4813722 | <https://www.fotmob.com/api/matchDetails?matchId={match_id}> | 404 | None | False | - | json_probe_invalid | invalid_404 |
| probe-user-seed-04-ep02 | 4813722 | <https://www.fotmob.com/api/matchDetails?matchId={match_id}&ccode3=USA> | 404 | None | False | - | json_probe_invalid | invalid_404 |
| probe-user-seed-04-ep03 | 4813722 | <https://www.fotmob.com/api/matchDetails?matchId={match_id}&timezone=UTC> | 404 | None | False | - | json_probe_invalid | invalid_404 |
| probe-user-seed-05-ep01 | 4813492 | <https://www.fotmob.com/api/matchDetails?matchId={match_id}> | 404 | None | False | - | json_probe_invalid | invalid_404 |
| probe-user-seed-05-ep02 | 4813492 | <https://www.fotmob.com/api/matchDetails?matchId={match_id}&ccode3=USA> | 404 | None | False | - | json_probe_invalid | invalid_404 |
| probe-user-seed-05-ep03 | 4813492 | <https://www.fotmob.com/api/matchDetails?matchId={match_id}&timezone=UTC> | 404 | None | False | - | json_probe_invalid | invalid_404 |
| probe-user-seed-06-ep01 | 4813622 | <https://www.fotmob.com/api/matchDetails?matchId={match_id}> | 404 | None | False | - | json_probe_invalid | invalid_404 |
| probe-user-seed-06-ep02 | 4813622 | <https://www.fotmob.com/api/matchDetails?matchId={match_id}&ccode3=USA> | 404 | None | False | - | json_probe_invalid | invalid_404 |
| probe-user-seed-06-ep03 | 4813622 | <https://www.fotmob.com/api/matchDetails?matchId={match_id}&timezone=UTC> | 404 | None | False | - | json_probe_invalid | invalid_404 |

## Raw Write Readiness Gate

- json_probe_observed_count: 0
- json_probe_blocked_count: 0
- json_probe_invalid_count: 9
- json_probe_not_json_count: 0
- json_validated_count: 0
- raw_write_eligible_count: 0
- raw_write_blocked_until_json_validated: True

## No-Write Safety Review

- network_fetch_performed: True ✅
- db_read_performed: False ✅
- db_write_performed: False ✅
- production_db_write_performed: False ✅
- raw_response_body_saved: False ✅
- raw_json_write_performed: False ✅
- fotmob_raw_match_payloads_write_performed: False ✅
- raw_match_data_write_performed: False ✅
- feature_parse_performed: False ✅
- scheduler_enabled: False ✅
- raw_write_ready_marked: False ✅
- browser_automation_performed: False ✅
- captcha_bypass_performed: False ✅
- proxy_rotation_performed: False ✅

## Remaining Blockers

- 本阶段最多只是 json_probe_observed
- 本阶段不保存 raw JSON body
- 本阶段不写 DB
- 本阶段不进入 L2 raw harvesting

## Recommended Next Phase

- **FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-JSON-PROBE-ENDPOINT-REVIEW-NO-WRITE**
