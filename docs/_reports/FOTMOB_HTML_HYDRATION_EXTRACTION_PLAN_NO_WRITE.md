<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 -->
# FotMob HTML Hydration Extraction Plan No Write

- lifecycle: current-state
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HTML-HYDRATION-EXTRACTION-PLAN-NO-WRITE
- run_id: fotmob_html_hydration_extraction_plan_no_write_v1
- mode: offline_extraction_plan

## 当前阶段背景

- #1442 验证 6/6 HTML routes 返回 200 text/html。
- API 路线 (/api/data/matchDetails) 被 403 阻断。
- HTML hydration route 现在是主要数据入口路径。
- 本阶段只离线设计下一阶段安全提取方案，不读取 body。

## #1442 Route Probe Inheritance

- html_route_observed_count: 6
- html_route_blocked_count: 0
- html_route_invalid_count: 0
- response_body_read: False
- html_body_saved: False
- json_validated_count: 0
- raw_write_eligible_count: 0

## Why HTML Route Is Now Primary Path

- /api/data/matchDetails → HTTP 403 (anti-bot blocked)
- /api/matchDetails → HTTP 404 (no /data/ prefix)
- /match/{id} → HTTP 200 text/html ✅
- /matches/{rc}/{id} → HTTP 200 text/html ✅
- HTML hydration (__NEXT_DATA__ + pageProps) is the viable data extraction route.

## Extraction Plan Candidate Matrix

| Candidate | Route | Match ID | RC | Body Limit | Markers | Priority |
|---|---|---|---:|---:|---|
| extract-cand-s01-r01 | https://www.fotmob.com/match/{match_id} | 4813722 | 2ygkcb | 262144 | __NEXT_DATA__, pageProps, matchId | 1 |
| extract-cand-s01-r02 | https://www.fotmob.com/matches/{route_code}/{match | 4813722 | 2ygkcb | 262144 | __NEXT_DATA__, pageProps, matchId | 2 |
| extract-cand-s02-r01 | https://www.fotmob.com/match/{match_id} | 4813492 | 2ynv4k | 262144 | __NEXT_DATA__, pageProps, matchId | 1 |
| extract-cand-s02-r02 | https://www.fotmob.com/matches/{route_code}/{match | 4813492 | 2ynv4k | 262144 | __NEXT_DATA__, pageProps, matchId | 2 |
| extract-cand-s03-r01 | https://www.fotmob.com/match/{match_id} | 4813622 | 2xqo0r | 262144 | __NEXT_DATA__, pageProps, matchId | 1 |
| extract-cand-s03-r02 | https://www.fotmob.com/matches/{route_code}/{match | 4813622 | 2xqo0r | 262144 | __NEXT_DATA__, pageProps, matchId | 2 |

## Allowed Markers

- `__NEXT_DATA__`
- `pageProps`
- `matchId`
- `header`
- `general`
- `content`
- `script`

## Forbidden Persistence

- full HTML body save
- raw JSON file write
- DB write (any table)
- raw response body persistence
- pageProps full extraction save
- __NEXT_DATA__ full dump save

## Limited Inspection Next Plan

- **phase**: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-LIMITED-HTML-HYDRATION-INSPECTION-NO-WRITE
- **max_samples**: 2
- **max_route_templates**: 2
- **max_network_requests**: 4
- **max_body_bytes**: 524288
- **allowed_markers**: __NEXT_DATA__, pageProps, matchId, header, general
- **forbidden_persistence**: full HTML body save, raw JSON file write, DB write (any table), raw response body persistence, pageProps full extraction save
- **success_criteria**: __NEXT_DATA__ script tag found in first 256KB, pageProps marker found, match_id confirmed in hydrated data
- **stop_conditions**: 403 on any route → stop all, 429 on any route → stop all, captcha/bot page detected → stop all, body exceeds 512KB without marker → stop that route
- **next_phase_after_success**: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-EXTRACTION-VALIDATION-NO-WRITE
- **next_phase_after_failure**: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HTML-HYDRATION-ROUTE-REVIEW-FOLLOWUP-NO-WRITE
- **notes**: Even if markers are found, next phase is extraction validation no-write, not raw JSON write. Full body extraction requires separate planning. L2 raw harvesting remains blocked until json_validated.

## Raw Write Readiness Gate

- json_validated_count: 0
- raw_write_eligible_count: 0
- raw_write_blocked_until_json_validated: True
- limited_body_inspection_required: True

## No-Write Safety Review

- network_fetch_performed: False (pass)
- response_body_read: False (pass)
- raw_response_body_saved: False (pass)
- html_body_saved: False (pass)
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

- 本阶段没有联网、没有读取 HTML body、没有保存 HTML body、没有保存 raw JSON、没有写 DB
- 下一阶段只是 limited inspection no-write，仍然不是 raw JSON 入库
- L2 raw harvesting 仍然 blocked

## Recommended Next Phase

- **FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-LIMITED-HTML-HYDRATION-INSPECTION-NO-WRITE**

