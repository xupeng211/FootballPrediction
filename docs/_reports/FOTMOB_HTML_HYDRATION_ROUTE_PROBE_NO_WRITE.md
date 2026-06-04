<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 -->
# FotMob HTML Hydration Route Probe No Write
- lifecycle: current-state
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HTML-HYDRATION-ROUTE-PROBE-NO-WRITE
- run_id: fotmob_html_hydration_route_probe_no_write_v1
- mode: controlled_network_probe_no_write
## 当前阶段背景
- #1441 验证 /api/data/matchDetails 返回 HTTP 403，API 路线被反爬阻断。
- 本阶段只测试 HTML hydration 页面路线：/match/{id} 和 /matches/{rc}/{id}。
- 只读取 status + headers metadata，不读取完整 body。
## #1441 Endpoint Probe Inheritance
- api_data_matchDetails_status: blocked_403
- api_data_matchDetails_attempted: 1
- json_parse_ok_count: 0
- json_validated_count: 0
- raw_write_eligible_count: 0

## Selected Route Samples
1. match_id=4813722, route_code=2ygkcb, pair=Liverpool vs Manchester United
2. match_id=4813492, route_code=2ynv4k, pair=Everton vs Manchester United
3. match_id=4813622, route_code=2xqo0r, pair=Tottenham Hotspur vs Manchester United

## Route Templates Tested
1. `https://www.fotmob.com/match/{match_id}` — html_hydration_match_page
2. `https://www.fotmob.com/matches/{route_code}/{match_id}` — html_hydration_matches_page

## Network Probe Summary
- allow_network_probe: True
- max_network_requests: 6
- network_requests_attempted: 6
- status_code_summary: {'200': 6}
- content_type_summary: {'text/html; charset=utf-8': 6}
- html_route_observed_count: 6
- html_route_redirect_observed_count: 0
- html_route_blocked_count: 0
- html_route_invalid_count: 0
- html_route_not_html_count: 0

## Probe Result Details

| Probe ID | Match ID | Team Pair | Route | Status | Content-Type | Redirect | Validation State |
|---|---|---|---|---|---|---|---|
| html-probe-s01-t01 | 4813722 | Liverpool vs Manchester United | <https://www.fotmob.com/match/{match_id}> | 200 | text/html; charset=utf-8 | - | html_route_observed |
| html-probe-s01-t02 | 4813722 | Liverpool vs Manchester United | <https://www.fotmob.com/matches/{route_code}/{match> | 200 | text/html; charset=utf-8 | - | html_route_observed |
| html-probe-s02-t01 | 4813492 | Everton vs Manchester United | <https://www.fotmob.com/match/{match_id}> | 200 | text/html; charset=utf-8 | - | html_route_observed |
| html-probe-s02-t02 | 4813492 | Everton vs Manchester United | <https://www.fotmob.com/matches/{route_code}/{match> | 200 | text/html; charset=utf-8 | - | html_route_observed |
| html-probe-s03-t01 | 4813622 | Tottenham Hotspur vs Manchester United | <https://www.fotmob.com/match/{match_id}> | 200 | text/html; charset=utf-8 | - | html_route_observed |
| html-probe-s03-t02 | 4813622 | Tottenham Hotspur vs Manchester United | <https://www.fotmob.com/matches/{route_code}/{match> | 200 | text/html; charset=utf-8 | - | html_route_observed |

## Route Decision Summary
- usable: ['https://www.fotmob.com/match/{match_id}', 'https://www.fotmob.com/matches/{route_code}/{match_id}']
- rejected: none
- deferred: none
- recommended: https://www.fotmob.com/match/{match_id}

## Raw Write Readiness Gate
- json_validated_count: 0
- raw_write_eligible_count: 0
- raw_write_blocked_until_json_validated: True
- html_hydration_extraction_planning_required: True

## No-Write Safety Review
- network_fetch_performed: True (pass)
- db_read_performed: False (pass)
- db_write_performed: False (pass)
- production_db_write_performed: False (pass)
- response_body_read: False (pass)
- raw_response_body_saved: False (pass)
- html_body_saved: False (pass)
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
- 本阶段最多只是 html_route_observed
- 本阶段不读取完整 HTML body
- 本阶段不保存 HTML body
- 本阶段不保存 raw JSON，不写 DB，不进入 L2 raw harvesting
- 即使 html_route_observed，下一阶段也只是 hydration extraction plan no-write，不是直接抓 raw body

## Recommended Next Phase

- **FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HTML-HYDRATION-EXTRACTION-PLAN-NO-WRITE**
