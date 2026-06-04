<!-- markdownlint-disable MD013 MD034 -->

# FotMob JSON Endpoint — Next Probe Plan

## Overview

- 本计划基于 #1439 失败结果和仓库历史 endpoint 审计材料生成。
- #1439 的 /api/matchDetails (without /data/) 全部 404，已 reject。
- 本计划推荐新的 endpoint candidates 供下一阶段 controlled probe。
- 下一阶段仍然是 no-write：只保存 metadata，不保存 body。

## Recommended Endpoint Templates for Next Probe

| # | Endpoint Template | Source | Why Better Than #1439 |
|---|---|---|
| 1 | `https://www.fotmob.com/api/data/matchDetails?matchId={match_id}` | code_search | Has /data/ prefix — canonical path from production code |
| 2 | `https://www.fotmob.com/match/{match_id}` | code_search | HTML hydration route — known HTTP 200 from ADG60 |
| 3 | `https://www.fotmob.com/api/data/matchDetails?matchId={match_id}&ccode3` | code_search | Has /data/ prefix — canonical path from production code |

## Probe Parameters

- **selected_candidate_count**: 3
- **max_samples**: 3
- **max_endpoint_templates**: 3
- **max_network_requests**: 9
- **selected_match_ids**: ['4813722', '4813492', '4813622']
- **selected_route_codes**: ['2ygkcb', '2ynv4k', '2xqo0r']
- **allow_network_required**: True
- **raw_response_body_saved**: False
- **raw_json_write**: False
- **db_write**: False

## Selected Match IDs

- match_id=4813722, route_code=2ygkcb
- match_id=4813492, route_code=2ynv4k
- match_id=4813622, route_code=2xqo0r

## Stop Conditions

- 403 on any endpoint → stop that endpoint immediately
- 429 on any endpoint → stop all probes immediately
- captcha/cloudflare detected → stop all probes
- content_type=text/html → record as html_hydration, do NOT parse body
- content_type=application/json → record top-level keys only, do NOT save body

## Safety Boundaries

- No response body saved
- No raw JSON write
- No DB write
- No browser automation
- No proxy rotation
- No session cookies
- Metadata only: status_code, content_type, top_level_keys

## Why Next Phase Is Still No-Write

- 这仍然是 endpoint discovery，不是 data harvesting。
- 即使 endpoint 返回 200 + JSON，也只能记录 metadata。
- 不允许 raw JSON body 保存、raw JSON write、DB write。
- L2 raw harvesting 仍然 blocked。

## Next Phase Recommendation

- **FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-ENDPOINT-CANDIDATE-PROBE-NO-WRITE**
