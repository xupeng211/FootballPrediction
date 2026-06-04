<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 MD001 -->
# FotMob Hydration Route Variant Decision

- lifecycle: current-state
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-ROUTE-VARIANT-FOLLOWUP-NO-WRITE decision
- run_id: fotmob_hydration_route_variant_followup_no_write_v1
- mode: controlled

## Route Variants Tested

- en variant attempted: 2
- slug variant attempted: 2

## Inherited Baseline (from #1449)

- default/zh-Hans route: fetchingLeagueData + translations + notableMatches
- strong candidate: 0, weak candidate: 0
- notableMatches rejected as match detail

## LIVE PROBE RESULTS

### rtv-s01 — 4813722 (variant=en)

- status: route_variant_keyspace_review_completed
- redirect_observed: False
- next_data_parse_ok: True
- pageProps_present: True
- strong_candidate_count: 0
- weak_candidate_count: 0
- top_candidate_path: props.pageProps.fetchingLeagueData
- top_candidate_score: 1
- top_candidate_state: partial_or_ambiguous_path
- differs_from_baseline: False
- variant_decision: route_variant_same_generic_keyspace

### rtv-s01 — 4813722 (variant=slug)

- status: route_variant_next_data_parse_failed
- redirect_observed: False
- next_data_parse_ok: False
- pageProps_present: False
- strong_candidate_count: 0
- weak_candidate_count: 0
- top_candidate_path: None
- top_candidate_score: 0
- top_candidate_state: None
- differs_from_baseline: False
- variant_decision: None

### rtv-s02 — 4813492 (variant=en)

- status: route_variant_keyspace_review_completed
- redirect_observed: False
- next_data_parse_ok: True
- pageProps_present: True
- strong_candidate_count: 0
- weak_candidate_count: 0
- top_candidate_path: props.pageProps.fetchingLeagueData
- top_candidate_score: 1
- top_candidate_state: partial_or_ambiguous_path
- differs_from_baseline: False
- variant_decision: route_variant_same_generic_keyspace

### rtv-s02 — 4813492 (variant=slug)

- status: route_variant_next_data_parse_failed
- redirect_observed: False
- next_data_parse_ok: False
- pageProps_present: False
- strong_candidate_count: 0
- weak_candidate_count: 0
- top_candidate_path: None
- top_candidate_score: 0
- top_candidate_state: None
- differs_from_baseline: False
- variant_decision: None

## Key Findings

- unlock_detail: 0
- differs_no_detail: 0
- same_generic: 2
- blocked: 0
- invalid: 2

- best route variant: en
- best candidate path: props.pageProps.fetchingLeagueData
- best candidate score: 1

## Why Raw Write Is Still Blocked

- 本阶段只比较 route variant keyspace metadata，未验证任何 JSON value。
- json_validated_count=0。
- raw_write_eligible_count=0。
- 即使某个 variant 解锁 candidate path，也需要先做 path validation no-write。

## Recommended Next Phase

- **FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-FOTMOB-PAGE-NO-EMBEDDED-DETAIL-DECISION-NO-WRITE**
