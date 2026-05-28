# FotMob URL Hash Detail Identity Propagation Regression ADG4

## Scope

- phase=Phase 5.21-ADG4
- phase_name=fotmob_url_hash_detail_identity_propagation_no_write_regression_and_candidate_reclassification
- regression_execution_performed=true
- source_controlled_local_no_write_regression=true
- runtime_behavior_validated=true
- runtime_code_change=false

## Safety

- live_fetch_performed=false
- detail_fetch_performed=false
- network_request_performed=false
- db_write_performed=false
- raw_match_data_insert_performed=false
- raw_write_execution_performed=false
- re_acceptance_execution_performed=false
- suspension_reversal_performed=false
- browser_automation_performed=false
- proxy_or_captcha_bypass_performed=false
- direct_api_retry_performed=false
- full_payload_saved=false
- full_payload_printed=false

## Positive Sample

- source_page_url=https://www.fotmob.com/zh-Hans/matches/manchester-city-vs-afc-bournemouth/2feiv3#4813735
- source_url_path_slug=2feiv3
- source_url_fragment_external_id=4813735
- detail_external_id_candidate=4813735
- detail_identity_source=url_hash_fragment
- no_http_request_required=true

## Propagation Summary

- source_inventory_hash_records_count=50
- active_candidate_hash_propagation_count=50
- candidate_detail_external_id_candidate_count=50
- total_batch_target_count=50
- suspended_target_count=8
- needs_new_evidence_target_count_before=42
- detail_identity_candidate_present_count=42
- source_inventory_hash_missing_count=0
- propagation_failed_count=0
- request_contract_validation_required_count=42
- remains_needs_new_evidence_count=0
- suspended_reverse_fixture_blocked_count=8
- raw_write_ready_count=0
- re_acceptance_candidate_count=0

## Recapture Identity Contract

- recapture_expected_identity_uses_detail_candidate=true
- schedule_external_id_blind_fallback_blocked=true
- direct_api_request_contract_blocked=true
- recapture_positive_sample_expected_identity=4813735
- recapture_positive_sample_request_identity=null

## Classification Result

- 42 previously generic needs_new_evidence targets now classify as request_contract_validation_required after ADG3 propagation.
- 8 suspended targets remain blocked as suspended_reverse_fixture_blocked.
- URL hash/detail candidate presence does not authorize raw write or re-acceptance.

## Recommended Next Step

bounded request-contract/page-route validation planning under no-write constraints; do not raw write, do not re-accept, do not bypass 403
