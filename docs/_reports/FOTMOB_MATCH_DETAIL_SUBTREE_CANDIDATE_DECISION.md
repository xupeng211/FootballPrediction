<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 MD001 -->
# FotMob Match Detail Subtree Candidate Decision

- lifecycle: current-state
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-MATCH-DETAIL-SUBTREE-EXTRACTION-NO-WRITE decision
- run_id: fotmob_controlled_match_detail_subtree_extraction_no_write_v1

## subtree-s01 — 4813722

- props.pageProps found: True
- fallback found: True
- target match_id seen: False
- team names seen: False
- best_candidate_path: props.pageProps.fallback.notableMatches:en:USA
- best_candidate_score: -5
- best_candidate_state: generic_or_irrelevant_subtree
- key presence: none

## subtree-s02 — 4813492

- props.pageProps found: True
- fallback found: True
- target match_id seen: False
- team names seen: False
- best_candidate_path: props.pageProps.fallback.notableMatches:en:USA
- best_candidate_score: -5
- best_candidate_state: generic_or_irrelevant_subtree
- key presence: none

## Why Raw Write Is Still Blocked

- 本阶段只识别 subtree path/score metadata，没有验证 JSON schema。
- 未保存 candidate subtree value，也未保存 raw JSON。
- json_validated_count=0 且 raw_write_eligible_count=0。

## Recommended Next Phase

- **FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-DETAIL-SUBTREE-REVIEW-FOLLOWUP-NO-WRITE**
