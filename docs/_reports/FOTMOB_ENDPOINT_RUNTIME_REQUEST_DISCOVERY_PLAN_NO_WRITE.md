<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 MD001 -->
# FotMob Endpoint Runtime Request Discovery Plan No Write

- lifecycle: current-state
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ENDPOINT-RUNTIME-REQUEST-DISCOVERY-PLAN-NO-WRITE
- run_id: fotmob_endpoint_runtime_request_discovery_plan_no_write_v1
- mode: offline_endpoint_runtime_discovery_plan

## 当前阶段背景

- #1451 已正式决定 FotMob HTML 页面不内嵌 match detail JSON。
- 本阶段在 offline 模式下复盘历史代码和报告，设计 endpoint/runtime request discovery 计划。
- 不联网，不保存任何响应内容，不写 DB。

## #1451 No Embedded Detail Decision Inheritance

- html_hydration_route_status: exhausted_no_embedded_match_detail
- page_level_next_data_status: no_match_detail_json_embedded
- raw_json_readiness: not_ready
- db_write_readiness: blocked
- l2_harvesting_readiness: blocked

## HTML Hydration Exhausted Summary

- /matches/{route_code}/{match_id} (default, zh-Hans, /en): NEXT_DATA ok, no match detail
- original slug path: no NEXT_DATA
- notableMatches rejected as match detail
- strong/weak candidate count = 0 across all tested routes

## Direct API Failure Summary

- /api/matchDetails: 404 or invalid
- /api/data/matchDetails: 403 or blocked
- Direct API routes blocked by FotMob access control

## Historical Code Review Summary

- files reviewed: 9
- relevant symbols found: 18
- endpoint patterns found: match_url, html_hydration

## Endpoint Candidate Inventory

- total candidates: 10
- next probe candidates: 3
- rejected/blocked: 7

### Candidate Categories

- historical known: 1
- nextjs data route: 2
- static json: 1
- runtime request: 1
- rejected 404: 1
- blocked 403: 1
- requires browser: 1
- alternative source: 2

### Top Next Probe Candidates
- ep-004 (nextjs_data_route_candidate): https://www.fotmob.com/_next/data/{buildId}/en/match/{match_id}.json (confidence=5, risk=6)
- ep-005 (nextjs_data_route_candidate): https://www.fotmob.com/_next/data/{buildId}/en/matches/{route_code}/{match_id}.json (confidence=5, risk=6)
- ep-006 (runtime_request_candidate): https://www.fotmob.com/api/matches?date={date}&status=finished (confidence=3, risk=7)

## Next Controlled Probe Plan

- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ENDPOINT-RUNTIME-CANDIDATE-PROBE-NO-WRITE
- max candidates: 3
- max samples: 2
- max network requests: 6
- max body bytes: 262144
- browser automation: forbidden
- cookies: forbidden
- captcha bypass: forbidden
- proxy rotation: forbidden
- DB write: forbidden
- raw write: forbidden

## Raw Write Readiness Gate

- json_validated_count: 0
- raw_write_eligible_count: 0
- raw_write_blocked_until_json_validated: true

## No-Write Safety Review

- 本阶段 offline，没有网络请求、没有 body 读取。
- 本阶段只做历史代码/报告静态 review。
- 当前不能入库原始 JSON，不能 raw write，不能 DB write，不能 L2 harvesting。
- 下一阶段只是 endpoint/runtime candidate probe no-write，仍不直接入库。
- 如果下一阶段仍无 json_validated，FotMob raw detail 应进入降级评估。

## Recommended Next Phase

- **FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ENDPOINT-RUNTIME-CANDIDATE-PROBE-NO-WRITE**
