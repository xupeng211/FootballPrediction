<!-- markdownlint-disable MD013 MD034 -->

# FotMob Controlled Endpoint Candidate Probe No Write

- lifecycle: current-state
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-ENDPOINT-CANDIDATE-PROBE-NO-WRITE
- run_id: fotmob_controlled_endpoint_candidate_probe_no_write_v1
- mode: controlled_network_probe_no_write

## 当前阶段背景

- #1440 endpoint review 完成，推荐了 3 个候选 endpoint templates。
- 本阶段用真实 match_id 和 route_code 做 controlled live probe。
- 只保存 metadata，不保存 response body。

## #1440 Endpoint Review Inheritance

- rejected_endpoint_count: 3
- endpoint_candidate_count: 8
- next_probe_candidate_count: 3
- previous_invalid_count: 9
- previous_json_parse_ok_count: 0

## Selected Probe Samples

1. match_id=4813722, route_code=2ygkcb, pair=Liverpool vs Manchester United
2. match_id=4813492, route_code=2ynv4k, pair=Everton vs Manchester United
3. match_id=4813622, route_code=2xqo0r, pair=Tottenham Hotspur vs Manchester United

## Endpoint Templates Tested

1. `https://www.fotmob.com/api/data/matchDetails?matchId={match_id}` — Canonical /api/data/matchDetails from production FotMobApiClient.js
2. `https://www.fotmob.com/match/{match_id}` — HTML hydration route from FotMobRawDetailFetcher.js, known HTTP 200
3. `https://www.fotmob.com/matches/{route_code}/{match_id}` — SSR page route, ADG60 validated, uses route_code from user seeds

## Network Probe Summary

- allow_network_probe: True
- max_network_requests: 9
- network_requests_attempted: 1
- status_code_summary: {'403': 1}
- content_type_summary: {}
- json_parse_attempted_count: 0
- json_parse_ok_count: 0
- json_observed_count: 0
- html_detected_count: 0
- blocked_count: 1
- invalid_count: 0
- not_json_count: 0

## Probe Result Details

| Probe ID | Match ID | Team Pair | Endpoint | Status | Content-Type | JSON OK | Top-Level Keys | Validation State |
|---|---|---|---|---|---|---|---|---|
| probe-s01-t01 | 4813722 | Liverpool vs Manchester United | <https://www.fotmob.com/api/data/matchDetails?match> | 403 | None | False | - | endpoint_candidate_blocked |
| probe-s01-t02 | 4813722 | Liverpool vs Manchester United | <https://www.fotmob.com/match/{match_id}> | None | None | False | - | endpoint_candidate_planned |
| probe-s01-t03 | 4813722 | Liverpool vs Manchester United | <https://www.fotmob.com/matches/{route_code}/{match> | None | None | False | - | endpoint_candidate_planned |
| probe-s02-t01 | 4813492 | Everton vs Manchester United | <https://www.fotmob.com/api/data/matchDetails?match> | None | None | False | - | endpoint_candidate_planned |
| probe-s02-t02 | 4813492 | Everton vs Manchester United | <https://www.fotmob.com/match/{match_id}> | None | None | False | - | endpoint_candidate_planned |
| probe-s02-t03 | 4813492 | Everton vs Manchester United | <https://www.fotmob.com/matches/{route_code}/{match> | None | None | False | - | endpoint_candidate_planned |
| probe-s03-t01 | 4813622 | Tottenham Hotspur vs Manchester United | <https://www.fotmob.com/api/data/matchDetails?match> | None | None | False | - | endpoint_candidate_planned |
| probe-s03-t02 | 4813622 | Tottenham Hotspur vs Manchester United | <https://www.fotmob.com/match/{match_id}> | None | None | False | - | endpoint_candidate_planned |
| probe-s03-t03 | 4813622 | Tottenham Hotspur vs Manchester United | <https://www.fotmob.com/matches/{route_code}/{match> | None | None | False | - | endpoint_candidate_planned |

## Endpoint Decision Summary

- usable: none
- rejected: ['https://www.fotmob.com/api/data/matchDetails?matchId={match_id}']
- deferred: none
- recommended: none

## Raw Write Readiness Gate

- json_validated_count: 0
- raw_write_eligible_count: 0
- raw_write_blocked_until_json_validated: True
- raw_body_capture_planning_required: False

## No-Write Safety Review

- network_fetch_performed: True (pass)
- db_read_performed: False (pass)
- db_write_performed: False (pass)
- production_db_write_performed: False (pass)
- raw_response_body_saved: False (pass)
- raw_json_write_performed: False (pass)
- fotmob_raw_match_payloads_write_performed: False (pass)
- raw_match_data_write_performed: False (pass)
- feature_parse_performed: False (pass)
- scheduler_enabled: False (pass)
- raw_write_ready_marked: False (pass)
- browser_automation_performed: False (pass)
- captcha_bypass_performed: False (pass)
- proxy_rotation_performed: False (pass)

## Remaining Blockers

- 本阶段最多只是 endpoint_candidate_json_observed
- 本阶段不保存 raw JSON body，不写 DB，不进入 L2 raw harvesting

## Recommended Next Phase

- **FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ENDPOINT-CANDIDATE-REVIEW-FOLLOWUP-NO-WRITE**
