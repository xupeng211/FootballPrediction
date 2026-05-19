# Data Entrypoint Governance - Phase 5.21 L2V3L

## A. Current Status

- phase=Phase 5.21L2V3L
- phase_name=date_mismatch_resolution_planning
- branch=data/pageprops-v2-date-mismatch-resolution-planning-phase521l2v3l
- started_after_pr_1285_merge=true
- planning_status=completed_root_cause_identified
- identity_mapping_acceptance_performed=false
- accepted_mapping_count=0
- raw_write_ready_for_execution=false

## B. PR #1285 Merge Result

- pr=1285
- title=docs(data): execute pageProps v2 identity mapping review
- merge_method=squash
- merge_commit=9500041a278be7bd7d85ba7aa36921b4bcbd3552
- merged_at=2026-05-19T11:42:57Z
- scope=L2V3K no-write review execution
- no_db_write=true
- no_raw_match_data_insert=true
- no_identity_mapping_acceptance=true
- no_baseline_acceptance=true
- no_raw_write_retry=true

## C. Hidden / Bidi Unicode Check

- pr_diff_scan=clean
- changed_files_scanned=4
- character_types_found_in_diff=[]
- safe_to_mark_ready=true
- safe_to_merge=true

## D. DB Row Count Safety Result (Pre-Merge)

- matches=60
- raw_match_data=18
- fotmob_pageprops_v2_rows=8
- bookmaker_odds_history=2
- l3_features=2
- match_features_training=2
- predictions=2
- check_method=SELECT-only via docker exec psql
- db_write_performed=false
- no_new_rows_since_l2v3j=true

## E. L2V3L Authorization Scope

- date_mismatch_resolution_planning_authorized=true
- no_write_readonly_analysis_authorized=true
- provenance_tracing_authorized=true
- planning_artifact_authorized=true
- manifest_update_authorized=true
- report_generation_authorized=true
- tests_and_docs_authorized=true
- db_write_authorized=false
- raw_match_data_insert_authorized=false
- matches_write_authorized=false
- matches_external_id_update_authorized=false
- identity_mapping_acceptance_authorized=false
- baseline_acceptance_authorized=false
- raw_write_retry_authorized=false

## F. No-Write Guarantee

- db_write_performed=false
- raw_insert_performed=false
- matches_write_performed=false
- matches_external_id_modified=false
- schema_migration_performed=false
- feature_extraction_training_prediction_performed=false
- browser_proxy_captcha_bypass_performed=false
- full_body_or_full_source_payload_saved=false
- full_body_or_full_source_payload_printed=false

## G. Date Provenance Analysis

### G.1 Schedule Date Source

- source=FotMob API leagues?id=53&season=20252026 source inventory
- field_path=overview.matches.allMatches[].matchTimeUTC or equivalent
- authority=league schedule listing via FotMob public API
- represents=scheduled match date as listed in the league season overview

### G.2 Detail Date Source

- source=pageProps.general.matchTimeUTC from detail page
- field_path=pageProps.general.matchTimeUTC
- authority=detail page canonical match
- represents=actual match date of the fixture served by FotMob for that pageUrl

### G.3 Date Divergence

- schedule date comes from league overview listing
- detail date comes from pageProps of the detail page
- pageUrl slug is shared between first-leg and second-leg fixtures
- detail page resolves to the most recent/canonical fixture for that slug

## H. Root Cause

- primary=fotmob_pageurl_slug_cross_fixture_reuse
- confidence=high

FotMob uses the same pageUrl base slug for both home and away fixtures between the same two teams within a season. The slug /matches/{home}-vs-{away}/{slug} is shared. When the fetcher navigates to the schedule target's pageUrl, FotMob serves the most recent/canonical fixture for that slug, which is the reverse/second-leg fixture.

Supporting evidence:

- All 8 pairs share the same pageUrl base
- All 8 pairs have team names in reversed home/away order
- Schedule dates are all Aug-Sep 2025 (early season, Matchdays 1-7)
- Detail dates are all Jan-May 2026 (mid-to-late season)
- Detail dates cluster in two groups: 5 on May 17 2026 (Matchday 38), 3 on Jan 17-24 2026 (mid-season)
- Schedule external_ids and detail external_ids are distinct and non-overlapping
- No multiple detail IDs per schedule ID or vice versa
- All 8 share match status 'finished'
- Source inventory confirms schedule IDs are from league overview allMatches

### H.1 Sub-Classifications

- reverse_fixture_second_leg: 8 (schedule=first meeting, detail=return fixture)
- cross_season_slug_reuse: 0 (all within 2025/2026 season)
- timezone_only_mismatch: 0 (gaps of 118-275d cannot be timezone)

## I. Date Gap Pattern Analysis

### I.1 Cluster 1: Matchday 38 (Final Day)

| Schedule ID | Schedule Date | Detail ID | Detail Date | Gap   |
| ----------- | ------------- | --------- | ----------- | ----- |
| 4830466     | 2025-08-15    | 4830759   | 2026-05-17  | ~275d |
| 4830461     | 2025-08-16    | 4830758   | 2026-05-17  | ~274d |
| 4830481     | 2025-08-31    | 4830763   | 2026-05-17  | ~259d |
| 4830496     | 2025-09-21    | 4830757   | 2026-05-17  | ~238d |
| 4830511     | 2025-09-27    | 4830760   | 2026-05-17  | ~232d |

All 5 detail IDs (4830757-4830763) share the same date (May 17, 2026), consistent with the final Ligue 1 matchday.

### I.2 Cluster 2: Mid-Season Matchdays

| Schedule ID | Schedule Date | Detail ID | Detail Date | Gap   |
| ----------- | ------------- | --------- | ----------- | ----- |
| 4830463     | 2025-08-16    | 4830622   | 2026-01-24  | ~161d |
| 4830465     | 2025-08-16    | 4830619   | 2026-01-17  | ~154d |
| 4830508     | 2025-09-27    | 4830620   | 2026-01-23  | ~118d |

All 3 detail IDs (4830619-4830622) cluster in late January 2026, consistent with mid-season reverse fixtures.

## J. PageUrl Base as Mapping Anchor

- sufficient_for_acceptance=false
- confidence=weak_to_medium

A shared pageUrl base confirms the same team pair but does not distinguish between first-leg and second-leg fixtures. Date mismatch of 118-275 days indicates different matches. pageUrl base alone is insufficient for identity mapping acceptance.

## K. Proposed Date Compatibility Rules

| Rule                     | Condition                                | Confidence         | Acceptance                            |
| ------------------------ | ---------------------------------------- | ------------------ | ------------------------------------- |
| date_match               | schedule_date == detail_date             | high               | eligible with human review            |
| same_utc_day             | abs(schedule_date - detail_date) < 24h   | high               | eligible with human review            |
| reverse_fixture_detected | same pageUrl, reversed teams, gap > 30d  | confirmed_mismatch | NOT eligible                          |
| postponed_or_rescheduled | same teams, gap < 30d, explicit evidence | medium             | eligible with human review + evidence |
| cross_season_slug_reuse  | same pageUrl, different season           | confirmed_mismatch | NOT eligible                          |
| unresolved_large_gap     | gap > 30d, no explanation                | invalid_mapping    | NOT eligible                          |

## L. Proposed Date Resolution Statuses

- date_match
- same_utc_day
- timezone_only_mismatch
- within_tolerance
- postponed_or_rescheduled_explained
- reverse_fixture_detected
- cross_season_slug_reuse
- unresolved_large_gap
- unknown

## M. Application to 8 Candidates

- all_8_classification=reverse_fixture_detected
- all_8_acceptance_eligible=false

These are identity mismatches, not identity mappings. The schedule external_id and detail external_id should NOT be accepted as a mapping because they represent different fixtures.

The correct remediation is NOT identity mapping acceptance, but fetcher route correction: the schedule ID should either fetch its own detail page (not the reverse fixture) or the pageUrl should include the specific fixture identifier (fragment anchor).

## N. Recommended Remediation

- short_term: Classify all 8 as reverse_fixture_detected. Block all from acceptance.
- medium_term: Implement date compatibility rule engine in fetcher/route normalizer.
- long_term: Fix fetcher route to use schedule external_id as fragment anchor when navigating to detail page.

None of these involve DB writes, identity mapping acceptance, baseline acceptance, or raw write retry.

## O. Raw Write Guard Compatibility

- date_mismatch_plan_usable_by_raw_write=false
- date_mismatch_plan_is_accepted_mapping=false
- reverse_fixture_detected_blocks_acceptance=true
- reverse_fixture_detected_blocks_raw_write=true
- pageurl_base_alone_insufficient_for_acceptance=true
- raw_write_still_requires_separate_identity_mapping_acceptance=true
- raw_write_still_requires_separate_baseline_acceptance=true
- raw_write_still_requires_separate_final_db_write_authorization=true
- raw_write_ready_for_execution=false

## P. Manifest Metadata Updates

- phase_5_21_l2v3l_planning_status added
- date_mismatch_resolution_planning_status updated
- date_mismatch_root_cause recorded
- reverse_fixture_detected_count=8
- accepted_mapping_count=0 unchanged
- raw_write_ready_for_execution=false unchanged

## Q. Test Results

- L2V3L targeted tests: pending
- L2V3K tests: pending
- L2V3J tests: pending
- prettier: pending
- git diff --check: pending
- hidden/bidi scan: pending
- JSON validation: pending

## R. Next Recommendation

Phase 5.21L2V3M: date_mismatch_resolution_rule_implementation

Implement the proposed date compatibility rules as a no-write rule engine:

- date_match, same_utc_day, reverse_fixture_detected, etc.
- Integrate with FotMobRouteIdentityReconciler
- Block all identity mapping acceptance when reverse_fixture_detected
- No DB writes, no raw writes, no baseline acceptance

## S. Explicit Non-Execution

- no DB writes
- no raw_match_data inserts
- no matches writes
- no matches.external_id modification
- no schema migration
- no feature extraction / training / prediction
- no browser/proxy/captcha bypass
- no identity mapping acceptance
- no baseline acceptance
- no raw write retry
- no accepted mapping emitted
- no reverse_fixture_detected treated as accepted mapping
- no pageUrl base alone accepted as mapping anchor
- no full raw_data/pageProps/source body saved or printed
- no existing evidence files deleted
