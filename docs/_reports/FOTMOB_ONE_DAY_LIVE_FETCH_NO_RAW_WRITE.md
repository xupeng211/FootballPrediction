<!-- markdownlint-disable MD013 -->

# FotMob One-day Live Fetch No Raw Write

- lifecycle: current-state
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ONE-DAY-LIVE-FETCH-NO-RAW-WRITE
- run_id: fotmob_one_day_live_fetch_no_raw_write_v1
- purpose: 极小规模真实 FotMob live fetch availability probe
- explicit_allow_flag_present: true
- DB target source: db_backed_selection
- 本阶段真实访问 FotMob（若有 attempted_target_count > 0）
- 本阶段没有保存 raw response body
- 本阶段没有写 raw JSON
- 本阶段没有写 DB
- 本阶段没有 parser
- 本阶段没有 scheduler
- 本阶段不是大规模采集

## Probe Result

- attempted_target_count: 1
- completed_target_count: 1
- skipped_target_count: 2
- stopped_early: true
- stop_reason: unexpected_html
- status_code_summary: {'404': 1}
- content_type_summary: {'text/html; charset=utf-8': 1}
- json_parse_ok_count: 0
- error_categories: {'unexpected_html': 1}

## Request Budget And Rate Limit

- global_request_budget: 3
- used: 1
- remaining: 2
- concurrency: 1
- sleep_seconds: 5
- max_attempts_per_target: 1

## Per-target Result

| source_match_id | status_code | content_type | response_size_bytes | json_parse_ok | error_category | stop_policy_triggered |
|-----------------|-------------|--------------|---------------------|---------------|----------------|-----------------------|
| fixture-eng-friend-001 | 404 | text/html; charset=utf-8 | 195491 | false | unexpected_html | true |

## Safety Review

- network_fetch_performed: true
- raw_response_body_saved: false
- db_write_performed: false
- raw_json_write_performed: false
- fotmob_raw_match_payloads_write_performed: false
- raw_match_data_write_performed: false
- feature_parse_performed: false
- scheduler_enabled: false
- raw_write_ready_marked: false
- browser_automation_performed: false
- captcha_bypass_performed: false
- proxy_rotation_performed: false
- retry_storm_performed: false

## Remaining Gaps

- 尚未授权 raw JSON dev write
- 尚未验证长期稳定 route
- 尚未启用 scheduler
- 尚未实现 parser/features/training/prediction

## Recommended Next Phase

- FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-LIVE-FETCH-ROUTE-REVIEW-NO-WRITE
- 若本阶段触发 stop policy，应先做 no-write route review，不得直接 raw write
- 若后续进入 raw write，仍只允许 dev/local、极少量、review 后再扩大
