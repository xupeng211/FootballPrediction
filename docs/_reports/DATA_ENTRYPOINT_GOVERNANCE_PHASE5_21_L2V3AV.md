# Data Entrypoint Governance - Phase 5.21 L2V3AV

## Scope

- phase=Phase 5.21L2V3AV
- phase_name=recapture_runner_identity_input_contract_fix_planning
- runner_identity_contract_fix_planning_status=completed_recapture_runner_identity_input_contract_fix_planning
- implementation_required=true
- implementation_performed=false
- live_fetch_performed=false
- detail_fetch_performed=false
- network_request_performed=false
- recapture_retry_performed=false
- re_acceptance_execution_performed=false
- suspension_reversal_performed=false
- rollback_execution_performed=false
- db_write_performed=false
- raw_match_data_insert_performed=false
- matches_write_performed=false
- matches_external_id_modified=false
- raw_write_execution_performed=false
- raw_write_runner_write_mode_used=false
- full_payload_saved=false
- full_payload_printed=false

## Current Runner Schedule-Side Route Issue

- current_runner_schedule_side_route_issue_confirmed=true
- schedule_side_route_detected_in_current_runner=true
- runner_uses_accepted_source_page_url_as_request_contract=false
- requested_observed_mismatch_example=4830466->4830759
- requested_external_id=4830466
- observed_detail_external_id=4830759
- page_url_base_match_status=match
- page_url_base_slug_fragment_alone_insufficient=true
- identity_match_status=mismatch
- date_compatibility_status=reverse_fixture_detected
- hash_validation_status=hash_mismatch
- hash_mismatch_under_identity_mismatch_secondary=true
- likely_root_cause=accepted mapping and baseline accepted schedule-side slug/fragment evidence without resolved detail identity, while L2V3M/L2V3N already recorded the same schedule id as a reverse fixture

## Planned Contract Fields

- schedule_external_id: correlation_key_only_not_default_detail_route
- source_url_fragment_external_id: evidence_component_not_sufficient_alone
- source_page_url: candidate_request_evidence_requires_reaccepted_binding
- source_page_url_base: insufficient_without_detail_identity_team_date_status
- accepted_detail_external_id: future_reaccepted_expected_identity
- observed_detail_external_id: runtime_observation_to_reconcile_not_accept
- recapture_request_identity: must_be_explicit_and_auditable
- recapture_expected_identity: must_match_reaccepted_detail_identity
- route_identity_strategy: block_on_unresolved_or_suspended_identity
- canonical_identity_source: future_reaccepted_mapping_and_evidence_chain

## Planned Input Priority Order

1. block_if_current_effective_mapping_or_baseline_suspended: current_effective_governance_status
2. require_future_reaccepted_mapping_before_retry: mapping_baseline_re_acceptance_chain
3. use_reaccepted_accepted_detail_external_id_as_expected_identity: accepted_detail_external_id
4. bind_source_page_url_and_fragment_to_expected_identity: source_page_url plus source_url_fragment_external_id
5. use_schedule_external_id_only_as_correlation_key: schedule_external_id
6. reconcile_observed_detail_external_id_after_authorized_no_write_retry: observed_detail_external_id
7. require_fresh_final_authorization_before_any_raw_write: fresh_final_authorization

## Planned Blocking Rules

- identity_mismatch -> block: identity_mismatch_blocks_recapture_retry
- reverse_fixture_detected -> block: reverse_fixture_detected_blocks_recapture_retry
- page_url_base_match_only -> block: page_url_base_match_alone_insufficient
- suspended_mapping_or_baseline -> block: suspended_mapping_or_baseline_blocks_retry
- missing_accepted_mapping -> block: missing_accepted_mapping_blocks_retry
- missing_re_acceptance -> block: missing_re_acceptance_blocks_retry
- hash_mismatch_with_identity_mismatch -> block_baseline_update: hash_mismatch_under_identity_mismatch_cannot_update_baseline

## Future Implementation Test Cases

- schedule_external_id_cannot_be_default_detail_route_identity
- accepted_detail_external_id_required_for_retry_after_reacceptance
- source_page_url_fragment_alone_does_not_authorize_retry
- requested_4830466_observed_4830759_blocks_retry
- suspended_mapping_baseline_blocks_retry
- hash_mismatch_secondary_under_identity_mismatch
- implementation_has_no_db_write_or_raw_write_mode

## Readiness

- suspended_mapping_count=8
- suspended_baseline_count=8
- blocked_pending_review_target_count=42
- suspended_mapping_baseline_blocks_retry=true
- payload_recapture_retry_ready=false
- raw_write_execution_ready=false
- recommended_next_step=Phase 5.21L2V3AW: recapture runner identity input contract fix implementation
- next_required_step=recapture_runner_identity_input_contract_fix_implementation

## Explicit Non-Execution

- no runner implementation
- no live fetch
- no detail fetch
- no network request
- no recapture retry
- no DB writes
- no raw_match_data inserts
- no matches writes
- no matches.external_id changes
- no raw write execution
- no re-acceptance execution
- no suspension reversal
- no rollback
- no parser/features/training/prediction
- no full payload printed or saved
