<!-- markdownlint-disable MD013 MD034 -->

# FotMob JSON Endpoint Review No Write

- lifecycle: current-state
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-JSON-PROBE-ENDPOINT-REVIEW-NO-WRITE
- run_id: fotmob_json_endpoint_review_no_write_v1
- mode: offline_endpoint_review

## 当前阶段背景

- #1439 用 3 个真实 match_id 测试了 3 个 endpoint templates，9 个请求全部 404。
- 当前使用的 `/api/matchDetails?matchId={id}` 模式无效或已过时。
- 本阶段离线复盘仓库历史 FotMob endpoint/route 审计材料，找出更靠谱的 endpoint 候选。
- 已经有真实 match_id 和 route_code。当前任务不是继续抓数据，而是找正确的 endpoint pattern。

## #1439 失败结果继承

- user_seed_count: 12
- parsed_seed_count: 12
- route_candidate_count: 12
- selected_sample_count: 3
- network_requests_attempted: 9
- json_parse_ok_count: 0
- invalid_count: 9
- json_validated_count: 0
- raw_write_eligible_count: 0

## 404 Endpoint Rejection Summary

| # | Endpoint Template | Prior Attempts | Result | Decision |
|---|---:|---|---|
| 1 | `https://www.fotmob.com/api/matchDetails?matchId={match_id}` | 3 | 404 | reject |
| 2 | `https://www.fotmob.com/api/matchDetails?matchId={match_id}&ccode3=USA` | 3 | 404 | reject |
| 3 | `https://www.fotmob.com/api/matchDetails?matchId={match_id}&timezone=UTC` | 3 | 404 | reject |

## Historical File Review Summary

| File | Exists | Endpoint Patterns Found | Notes |
|---|---:|---|
| docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.detail_api_endpoint_feasibility.phase521l2v3s.json | yes | 3 | matchDetails_refs=5, /api/data/ refs=2, pageProps_refs=0, NEXT_DATA_refs=0 |
| docs/_reports/FOTMOB_DETAIL_ROUTE_SELECTOR_PHASE5_12L2B.md | yes | 4 | matchDetails_refs=4, /api/data/ refs=2, pageProps_refs=0, NEXT_DATA_refs=3 |
| docs/_reports/FOTMOB_RAW_DETAIL_ACCESS_ROUTE_AUDIT_PHASE5_12L2A.md | yes | 2 | matchDetails_refs=3, /api/data/ refs=3, pageProps_refs=0, NEXT_DATA_refs=0 |
| docs/_reports/FOTMOB_IDENTITY_ANTI_BOT_DIFFERENTIAL_DIAGNOSIS_RESULT_ADG2.md | yes | 3 | matchDetails_refs=1, /api/data/ refs=1, pageProps_refs=1, NEXT_DATA_refs=0 |
| scripts/ops/fotmob_live_fetch_route_review_no_write.py | yes | 0 | matchDetails_refs=0, /api/data/ refs=0, pageProps_refs=0, NEXT_DATA_refs=0 |

## Endpoint Candidate Matrix

| ID | Category | Endpoint Template | Source | Confidence | Risk | Priority | Next Probe |
|---|---|---|---:|---:|---:|---|
| ep-cand-001 | rejected | `https://www.fotmob.com/api/matchDetails?matchId={match_id}` | pr1439_failed_probe | 0 | 10 | 0 | no |
| ep-cand-002 | api_json_direct | `https://www.fotmob.com/api/data/matchDetails?matchId={match_` | code_search | 7 | 6 | 1 | yes |
| ep-cand-003 | api_json_direct | `https://www.fotmob.com/api/data/matchDetails?matchId={match_` | code_search | 4 | 5 | 2 | yes |
| ep-cand-004 | html_hydration | `https://www.fotmob.com/match/{match_id}` | code_search | 9 | 3 | 1 | yes |
| ep-cand-005 | html_hydration | `https://www.fotmob.com/matches/{route_code}/{match_id}` | historical_report | 8 | 2 | 2 | yes |
| ep-cand-006 | page_derived | `https://www.fotmob.com/zh-Hans/matches/{match_slug}/{route_c` | page_derived | 9 | 1 | 3 | yes |
| ep-cand-007 | deferred | `https://www.fotmob.com/api/data/matchDetails?matchId={match_` | historical_report | 9 | 9 | 0 | no |
| ep-cand-008 | deferred | `http://data.fotmob.com/webcl/ltc/gsm/{match_id}_en_gen.json.` | historical_report | 2 | 8 | 0 | no |

## Next Probe Plan Summary

- **selected_candidate_count**: 3
- **max_samples**: 3
- **max_endpoint_templates**: 3
- **max_network_requests**: 9
- **selected_match_ids**:
  - 4813722
  - 4813492
  - 4813622
- **selected_route_codes**:
  - 2ygkcb
  - 2ynv4k
  - 2xqo0r
- **selected_endpoint_templates**:
  - https://www.fotmob.com/api/data/matchDetails?matchId={match_id}
  - https://www.fotmob.com/match/{match_id}
  - https://www.fotmob.com/api/data/matchDetails?matchId={match_id}&ccode3=USA
- **allow_network_required**: True
- **raw_response_body_saved**: False
- **raw_json_write**: False
- **db_write**: False
- **stop_conditions**:
  - 403 on any endpoint → stop that endpoint immediately
  - 429 on any endpoint → stop all probes immediately
  - captcha/cloudflare detected → stop all probes
  - content_type=text/html → record as html_hydration, do NOT parse body
  - content_type=application/json → record top-level keys only, do NOT save body
- **safety_boundaries**:
  - No response body saved
  - No raw JSON write
  - No DB write
  - No browser automation
  - No proxy rotation
  - No session cookies
  - Metadata only: status_code, content_type, top_level_keys
- **next_phase_notes**: Next phase should probe /api/data/matchDetails (the canonical endpoint from production code), /match/{match_id} (HTML hydration route, known 200), and /matches/{route_code}/{match_id} (SSR page, known 200). All three use the /data/ prefix or page routes that differ from the #1439 404 endpoints. If /api/data/matchDetails returns 403, that confirms anti-bot blocking; the HTML hydration routes should return 200 but with text/html content_type.

## Raw Write Readiness Gate

- json_validated_count: 0
- raw_write_eligible_count: 0
- raw_write_blocked_until_json_validated: True
- controlled_endpoint_probe_required: True

## No-Write Safety Review

- network_fetch_performed: False (pass)
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

- 已经有真实 match_id
- 但旧 endpoint /api/matchDetails (without /data/) 全部 404
- 本阶段没有联网、没有 raw body、没有 raw JSON、没有 DB write
- 下一阶段仍然是 controlled endpoint candidate probe no-write，不是 raw write

## Recommended Next Phase

- **FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-ENDPOINT-CANDIDATE-PROBE-NO-WRITE**
