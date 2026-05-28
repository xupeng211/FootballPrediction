# FotMob Request-Contract / Page-Route Validation Plan ADG5

> Date: 2026-05-28
> Phase: Phase 5.21-ADG5
> Scope: planning only

## 1. Planning Goal

ADG5 uses the ADG4 no-write regression result to plan a bounded ADG6 validation run for targets that now carry `detail_external_id_candidate` but still classify as `request_contract_validation_required`.

ADG5 does not execute page-route validation, direct API probing, browser automation, live fetch, DB write, raw write, re-acceptance, or suspension reversal.

## 2. ADG4 Input Summary

- `detail_identity_candidate_present_count=42`
- `request_contract_validation_required_count=42`
- `remains_needs_new_evidence_count=0`
- `source_inventory_hash_missing_count=0`
- `propagation_failed_count=0`
- `suspended_reverse_fixture_blocked_count=8`
- `raw_write_ready_count=0`
- `direct_api_request_contract_blocked=true`
- `schedule_external_id_blind_fallback_blocked=true`

## 3. Planned Samples

ADG6 must stay bounded to the current 50-target batch:

- positive sample: `#4813735`
- request-contract sample count: 5
- suspended reference sample count: 2

Planned request-contract sample external ids:

- `4830458`
- `4830459`
- `4830460`
- `4830462`
- `4830464`

Planned suspended reference sample external ids:

- `4830461`
- `4830463`

These reference samples remain blocked as `suspended_reverse_fixture_blocked` and are not validation-eligible for clean/re-acceptance.

## 4. Planned Validation Fields

- `sample_id`
- `source_page_url`
- `source_url_path_slug`
- `source_url_fragment_external_id`
- `detail_external_id_candidate`
- `detail_identity_source`
- `expected_home_team`
- `expected_away_team`
- `expected_match_date`
- `expected_competition`
- `page_route_url_without_fragment`
- `page_http_status`
- `page_content_type`
- `redirect_summary`
- `hydration_marker_present`
- `safe_identity_marker_present`
- `observed_detail_id_if_safely_available`
- `observed_home_team_if_safely_available`
- `observed_away_team_if_safely_available`
- `observed_date_if_safely_available`
- `anti_bot_signs`
- `request_contract_status`
- `validation_classification`
- `no_full_body_saved`
- `no_db_write`
- `no_raw_write`

## 5. Planned Classifications

- `page_route_identity_validated`
- `page_route_available_but_identity_not_observed`
- `direct_api_request_contract_blocked`
- `request_contract_headers_session_locale_required`
- `anti_bot_or_access_block`
- `redirect_or_locale_mismatch`
- `hydration_marker_missing`
- `identity_mismatch`
- `reverse_fixture_or_home_away_inversion`
- `suspended_reference_blocked`
- `insufficient_safe_evidence`

## 6. ADG6 Safety Boundaries

- bounded sample count only
- no bulk fetch
- no DB write
- no raw write
- no `raw_match_data` insert
- no re-acceptance
- no suspension reversal
- no captcha bypass
- no proxy bypass
- no login
- no access-control bypass
- no uncontrolled retry
- no full HTML save
- no full payload save
- stop sample on `401` / `403` / captcha / block / rate-limit
- treat direct API `403` as request-contract blocker, not bypass target
- page-route validation may record safe summaries only

## 7. Safety Status

- `planning_performed=true`
- `live_fetch_performed=false`
- `network_request_performed=false`
- `direct_api_probing_performed=false`
- `browser_automation_performed=false`
- `db_write_performed=false`
- `raw_write_execution_performed=false`
- `re_acceptance_execution_performed=false`
- `suspension_reversal_performed=false`
- `full_payload_saved=false`
- `full_payload_printed=false`

## 8. Recommended Next Step

ADG6 bounded request-contract / page-route validation execution requires explicit authorization. ADG5 does not authorize raw write, re-acceptance, or 403 bypass.
