<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 MD001 -->
# FotMob Controlled Match Detail Subtree Extraction No Write

- lifecycle: current-state
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-MATCH-DETAIL-SUBTREE-EXTRACTION-NO-WRITE
- run_id: fotmob_controlled_match_detail_subtree_extraction_no_write_v1
- mode: controlled_subtree_extraction_no_write

## 当前阶段背景

- #1446 已确认 `/matches/{route_code}/{match_id}` 是当前唯一主路线。
- 本阶段只保存结构 metadata，不保存完整 HTML、完整 NEXT_DATA、candidate subtree value 或 raw JSON。
- 本阶段不写 DB，也不进入 L2 raw harvesting。

## #1446 Subtree Extraction Plan Inheritance

- root_path: props.pageProps
- priority_path_count: 10
- scoring_rule_count: 17
- max_subtree_scan_depth: 8
- json_validated_count: 0
- raw_write_eligible_count: 0

## Selected Extraction Samples

- 4813722 / 2ygkcb / Liverpool vs Manchester United
- 4813492 / 2ynv4k / Everton vs Manchester United

## Route Template

`/matches/{route_code}/{match_id}`

## Bounded Body Summary

- allow_network_probe: True
- max_network_requests: 2
- network_requests_attempted: 2
- fallback_present_count: 2
- target_match_id_seen_count: 0
- strong_candidate_count: 0
- weak_candidate_count: 0
- partial_candidate_count: 0
- generic_or_irrelevant_count: 2
- blocked_count: 0
- invalid_count: 0
- not_html_count: 0

## Subtree Scan Summary

- subtree-s01: fallback=True, target_mid=False, best=props.pageProps.fallback.notableMatches:en:USA, score=-5, state=generic_or_irrelevant_subtree
- subtree-s02: fallback=True, target_mid=False, best=props.pageProps.fallback.notableMatches:en:USA, score=-5, state=generic_or_irrelevant_subtree

## Candidate Decision

- viable_candidate_count: 0
- best_candidate_path: props.pageProps.fallback.notableMatches:en:USA
- best_candidate_score: -5
- best_candidate_state: generic_or_irrelevant_subtree
- recommended_next_action: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-DETAIL-SUBTREE-REVIEW-FOLLOWUP-NO-WRITE

## Raw Write Readiness Gate

- json_validated_count: 0
- raw_write_eligible_count: 0
- raw_write_blocked_until_json_validated: True
- subtree_validation_required: True

## No-Write Safety Review

- network_fetch_performed: True
- bounded_body_read_performed: True
- full_body_read_performed: False
- full_html_saved: False
- raw_response_body_saved: False
- html_body_saved: False
- full_next_data_saved: False
- candidate_subtree_value_saved: False
- raw_json_write_performed: False
- db_read_performed: False
- db_write_performed: False
- production_db_write_performed: False
- fotmob_raw_match_payloads_write_performed: False
- raw_match_data_write_performed: False
- feature_parse_performed: False
- scheduler_enabled: False
- raw_write_ready_marked: False
- browser_automation_performed: False
- captcha_bypass_performed: False
- proxy_rotation_performed: False

## Remaining Blockers

- candidate subtree 尚未做下一阶段 validation no-write。
- json_validated_count 仍为 0，raw_write_eligible_count 仍为 0。
- 即使发现 strong candidate，下一阶段也只是 subtree validation no-write，不是直接入库。

## Recommended Next Phase

- **FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-DETAIL-SUBTREE-REVIEW-FOLLOWUP-NO-WRITE**
