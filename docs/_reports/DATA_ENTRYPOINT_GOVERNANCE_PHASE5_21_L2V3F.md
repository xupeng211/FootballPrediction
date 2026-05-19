# Data Entrypoint Governance - Phase 5.21 L2V3F

## A. Current Status

- phase=schedule detail identity normalization fix planning
- branch=data/pageprops-v2-schedule-detail-normalization-phase521l2v3f
- base_head=3a769e5892b7e983d8e7a765b5f8c7b09fd79704
- main_head=3a769e5892b7e983d8e7a765b5f8c7b09fd79704
- main_ci_status=success
- source_manifest_path=docs/\_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json
- renewed_baseline_proposal_path=docs/\_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.renewed_baseline_proposal.phase521l2v3c.json
- source_inventory_reconciliation_report=docs/\_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3E.md
- normalization_proposal_path=docs/\_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.schedule_detail_identity_normalization_proposal.phase521l2v3f.json
- report_path=docs/\_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3F.md

## B. PR #1279 Merge Result

- pr_1279_state=MERGED
- pr_1279_merge_commit=3a769e5892b7e983d8e7a765b5f8c7b09fd79704
- merge_scope=L2V3E no-write source inventory reconciliation planning

## C. main HEAD / CI Status

- main_head=3a769e5892b7e983d8e7a765b5f8c7b09fd79704
- main_ci_status=success

## D. Authorization Scope

- planning_authorized=true
- schedule_detail_normalization_authorized=true
- network_authorized_for_source_inventory_only=true
- no match detail live check executed in L2V3F
- no accepted identity mapping
- no accepted baseline replacement
- no raw write authorization

## E. No-Write Guarantee

- db_write_performed=false
- raw_insert_performed=false
- identity_mapping_acceptance_performed=false
- baseline_acceptance_performed=false
- raw_write_retry_performed=false
- full raw_data/pageProps/source body printed=false
- full raw_data/pageProps/source body saved=false

## F. L2V3E Root Cause Recap

- l2v3e_suspected_root_cause=schedule_vs_detail_external_id_mismatch
- l2v3e_root_cause_confidence=high
- checked_target_count=8
- proposed_mapping_count=8
- high_confidence_mapping_count=0
- unresolved_mapping_count=8

## G. Schedule / Listing Vs Detail Identity Evidence

- requested_vs_observed_external_id_behavior=distinct_identity_surfaces_observed
- page_url_base_match_count=8
- team_pair_match_count=8
- exact_date_match_count=0
- team_date_status_compatible_count=0
- team_date_status_mismatch_count=8
- multiple_detail_ids_for_same_schedule_id_count=0
- multiple_schedule_ids_for_same_detail_id_count=0

## H. PageUrl Base Normalization Analysis

- primary_anchor=page_url_base
- page_url_base_match_status_counts={"match":8}
- team_date_status_match_status_counts={"date_mismatch":8}
- page_url_base_is_candidate_anchor_only=true
- high_confidence_requires_page_url_base_plus_team_date_status_compatibility=true

## I. 8 Mismatch Target Safe Mapping Summary

| requested_match_id  | requested_schedule_external_id | requested_teams             | requested_match_date     | requested_status | source_inventory_page_url_base                                       | manifest_page_url_base | live_observed_page_url_base                                          | observed_detail_external_id | observed_teams              | observed_match_date      | observed_status | page_url_base_match_status | team_date_status_match_status | schedule_external_id_vs_detail_external_id_status | proposed_normalization_key | mapping_confidence | safety_blockers           |
| ------------------- | ------------------------------ | --------------------------- | ------------------------ | ---------------- | -------------------------------------------------------------------- | ---------------------- | -------------------------------------------------------------------- | --------------------------- | --------------------------- | ------------------------ | --------------- | -------------------------- | ----------------------------- | ------------------------------------------------- | -------------------------- | ------------------ | ------------------------- |
| 53_20252026_4830466 | 4830466                        | Rennes-Marseille            | 2025-08-15T18:45:00.000Z | finished         | https://www.fotmob.com/matches/marseille-vs-rennes/2t9n7h            |                        | https://www.fotmob.com/matches/marseille-vs-rennes/2t9n7h            | 4830759                     | Marseille-Rennes            | 2026-05-17T19:00:00.000Z | finished        | match                      | date_mismatch                 | different                                         | page_url_base              | medium             | team_date_status_mismatch |
| 53_20252026_4830461 | 4830461                        | Lens-Lyon                   | 2025-08-16T15:00:00.000Z | finished         | https://www.fotmob.com/matches/lens-vs-lyon/2s3gtg                   |                        | https://www.fotmob.com/matches/lens-vs-lyon/2s3gtg                   | 4830758                     | Lyon-Lens                   | 2026-05-17T19:00:00.000Z | finished        | match                      | date_mismatch                 | different                                         | page_url_base              | medium             | team_date_status_mismatch |
| 53_20252026_4830481 | 4830481                        | Monaco-Strasbourg           | 2025-08-31T15:15:00.000Z | finished         | https://www.fotmob.com/matches/monaco-vs-strasbourg/379ruz           |                        | https://www.fotmob.com/matches/monaco-vs-strasbourg/379ruz           | 4830763                     | Strasbourg-Monaco           | 2026-05-17T19:00:00.000Z | finished        | match                      | date_mismatch                 | different                                         | page_url_base              | medium             | team_date_status_mismatch |
| 53_20252026_4830496 | 4830496                        | Le Havre-Lorient            | 2025-09-21T15:15:00.000Z | finished         | https://www.fotmob.com/matches/lorient-vs-le-havre/2t6haw            |                        | https://www.fotmob.com/matches/lorient-vs-le-havre/2t6haw            | 4830757                     | Lorient-Le Havre            | 2026-05-17T19:00:00.000Z | finished        | match                      | date_mismatch                 | different                                         | page_url_base              | medium             | team_date_status_mismatch |
| 53_20252026_4830511 | 4830511                        | Toulouse-Nantes             | 2025-09-27T17:00:00.000Z | finished         | https://www.fotmob.com/matches/nantes-vs-toulouse/38dikf             |                        | https://www.fotmob.com/matches/nantes-vs-toulouse/38dikf             | 4830760                     | Nantes-Toulouse             | 2026-05-17T19:00:00.000Z | finished        | match                      | date_mismatch                 | different                                         | page_url_base              | medium             | team_date_status_mismatch |
| 53_20252026_4830463 | 4830463                        | Monaco-Le Havre             | 2025-08-16T17:00:00.000Z | finished         | https://www.fotmob.com/matches/le-havre-vs-monaco/362v61             |                        | https://www.fotmob.com/matches/le-havre-vs-monaco/362v61             | 4830622                     | Le Havre-Monaco             | 2026-01-24T18:00:00.000Z | finished        | match                      | date_mismatch                 | different                                         | page_url_base              | medium             | team_date_status_mismatch |
| 53_20252026_4830465 | 4830465                        | Nice-Toulouse               | 2025-08-16T19:05:00.000Z | finished         | https://www.fotmob.com/matches/nice-vs-toulouse/38dxtn               |                        | https://www.fotmob.com/matches/nice-vs-toulouse/38dxtn               | 4830619                     | Toulouse-Nice               | 2026-01-17T18:00:00.000Z | finished        | match                      | date_mismatch                 | different                                         | page_url_base              | medium             | team_date_status_mismatch |
| 53_20252026_4830508 | 4830508                        | Paris Saint-Germain-Auxerre | 2025-09-27T19:05:00.000Z | finished         | https://www.fotmob.com/matches/auxerre-vs-paris-saint-germain/2t4i9k |                        | https://www.fotmob.com/matches/auxerre-vs-paris-saint-germain/2t4i9k | 4830620                     | Auxerre-Paris Saint-Germain | 2026-01-23T19:00:00.000Z | finished        | match                      | date_mismatch                 | different                                         | page_url_base              | medium             | team_date_status_mismatch |

## J. Proposed Normalization Model

- normalized_identity_model={
  "schedule_external_id": "separate",
  "detail_external_id": "separate",
  "page_url_base": "proposal_only_anchor",
  "league_id": 53,
  "season": "2025/2026",
  "home_team": "proposal_only",
  "away_team": "proposal_only",
  "match_date": "proposal_only",
  "status": "proposal_only",
  "mapping_confidence": "proposal_only",
  "mapping_source": "source_inventory_page_url_base_plus_prior_safe_live_metadata",
  "mapping_verified_at": "2026-05-19T01:13:49.568Z"
  }

## K. Proposed Gating Rules

- raw_write_ready_for_execution=false unless separate identity mapping acceptance completes
- proposal_only_mapping_never_usable_by_raw_write_runner=true
- unresolved_or_unaccepted_normalization_blocks_baseline_acceptance=true
- unresolved_or_unaccepted_normalization_blocks_raw_write_retry=true
- requires_separate_identity_mapping_acceptance=true
- requires_separate_baseline_acceptance=true
- requires_separate_final_db_write_authorization=true

## L. Required Fix / Continue Investigation Decision

- code_fix_required=true
- manifest_regeneration_required=false
- identity_mapping_acceptance_required=true
- continue_investigation_required=false
- recommended_next_step=schedule_detail_route_normalization_fix_implementation_planning

## M. Normalization Proposal File Path

- normalization_proposal_path=docs/\_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.schedule_detail_identity_normalization_proposal.phase521l2v3f.json

## N. DB Row Count Safety Result

- matches=60
- raw_match_data=18
- bookmaker_odds_history=2
- l3_features=2
- match_features_training=2
- predictions=2
- candidate_matches=58
- candidate_fotmob_pageprops_v2_raw_rows=8
- expected_matches=60
- expected_raw_match_data=18
- db_check_mode=SELECT-only via db container psql
- db_write_performed=false

### N.1 Candidate Scope Clarification For Draft Review

- candidate_count_scope_explanation=the 58-row DB safety scope is the current Ligue 1 2025/2026 `matches` population, composed of 50 source-controlled manifest schedule targets plus 8 pre-existing seeded pageProps v2 match identities.
- candidate_count_is_schedule_targets_plus_observed_detail_ids=false
- observed_detail_external_ids_in_matches_count=0
- observed_detail_external_ids_in_candidate_v2_rows_count=0
- candidate_matches_58_breakdown=50 manifest schedule targets + 8 pre-existing known completed pageProps v2 seeded targets
- candidate_v2_rows_explanation=the 8 `fotmob_pageprops_v2` rows are pre-existing raw rows for seeded match_ids `53_20252026_4830746`, `53_20252026_4830747`, `53_20252026_4830748`, `53_20252026_4830750`, `53_20252026_4830751`, `53_20252026_4830752`, `53_20252026_4830753`, `53_20252026_4830754`.
- candidate_v2_rows_are_l2v3f_writes=false
- candidate_v2_rows_are_raw_write_success_for_l2v3f=false
- rows_are_preexisting=true
- raw_match_data_created_at_updated_at_source_columns=not present in current schema; safe summary used `match_id`, `external_id`, `data_version`, and `collected_at`
- l2v3f_db_write_performed=false
- l2v3f_raw_write_succeeded=false
- whether_this_blocks_ready_for_review=false

| match_id            | external_id | data_version        | collected_at               | safe match identity                                       |
| ------------------- | ----------- | ------------------- | -------------------------- | --------------------------------------------------------- |
| 53_20252026_4830746 | 4830746     | fotmob_pageprops_v2 | 2026-05-16 13:37:39.108+00 | Angers-Strasbourg, 2026-05-10T19:00:00Z, finished         |
| 53_20252026_4830747 | 4830747     | fotmob_pageprops_v2 | 2026-05-16 09:57:56.892+00 | Auxerre-Nice, 2026-05-10T19:00:00Z, finished              |
| 53_20252026_4830748 | 4830748     | fotmob_pageprops_v2 | 2026-05-16 13:37:39.108+00 | Le Havre-Marseille, 2026-05-10T19:00:00Z, finished        |
| 53_20252026_4830750 | 4830750     | fotmob_pageprops_v2 | 2026-05-16 13:37:39.108+00 | Metz-Lorient, 2026-05-10T19:00:00Z, finished              |
| 53_20252026_4830751 | 4830751     | fotmob_pageprops_v2 | 2026-05-16 13:37:39.108+00 | Monaco-Lille, 2026-05-10T19:00:00Z, finished              |
| 53_20252026_4830752 | 4830752     | fotmob_pageprops_v2 | 2026-05-16 13:37:39.108+00 | Paris Saint-Germain-Brest, 2026-05-10T19:00:00Z, finished |
| 53_20252026_4830753 | 4830753     | fotmob_pageprops_v2 | 2026-05-16 13:37:39.108+00 | Rennes-Paris FC, 2026-05-10T19:00:00Z, finished           |
| 53_20252026_4830754 | 4830754     | fotmob_pageprops_v2 | 2026-05-16 13:37:39.108+00 | Toulouse-Lyon, 2026-05-10T19:00:00Z, finished             |

## O. Test Results

- targeted L2V3F/L2V3E/L2 ingest/source inventory/shared helper tests: passed (133 tests)
- npm test: passed (5447 tests, 435 suites)
- npm run test:coverage: passed (lines=90.09, branches=80.03, functions=85.34)
- npm run lint: passed
- prettier check for changed files: passed
- npm run format:check: not used as final gate because repository-wide existing formatting warnings include unrelated files; changed-file prettier check passed
- git diff --check: passed
- DB row count safety check: passed, SELECT-only
- l1-config residue check: passed, no matching residue found under tests/fixtures/docs
- docs/\_staging_preview absence check: passed
- dev-container psql direct check: not available (`psql` not installed in dev container); db container psql used for SELECT-only check

## P. PR Status

- pr_created=true
- pr_number=1280
- pr_url=https://github.com/xupeng211/FootballPrediction/pull/1280
- pr_base=main
- pr_head=data/pageprops-v2-schedule-detail-normalization-phase521l2v3f
- pr_draft=true
- pr_ci_status=pending at report update time

## Q. Next Step Recommendation

- recommended_next_step=schedule_detail_route_normalization_fix_implementation_planning
- unresolved or unaccepted normalization blocks baseline acceptance.
- unresolved or unaccepted normalization blocks raw write retry.

## R. Explicit Non-Execution

- no DB writes
- no raw_match_data inserts
- no matches writes
- no bookmaker_odds_history writes
- no l3_features writes
- no match_features_training writes
- no predictions writes
- no schema migration
- no parser implementation for production execution
- no feature extraction
- no training/prediction
- no browser/proxy/captcha bypass
- no accepted identity mapping
- no accepted baseline replacement
- no raw write retry
- no proposal hash marked as accepted baseline
- no full raw_data/pageProps/source body print/save
- no invented external_id, target, payload, or hash
- no matches.external_id modification
