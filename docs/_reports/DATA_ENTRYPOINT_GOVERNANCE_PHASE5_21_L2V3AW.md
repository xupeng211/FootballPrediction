# Data Entrypoint Governance - Phase 5.21 L2V3AW

## Scope

- phase=Phase 5.21L2V3AW
- phase_name=recapture_runner_identity_input_contract_fix_implementation
- implementation_performed=true
- runner_identity_contract_fix_implemented=true
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

## Code Behavior Changed

- src/infrastructure/services/FotMobRouteIdentityReconciler.js adds/updates the recapture identity contract resolver.
- scripts/ops/pageprops_v2_no_write_payload_recapture_execute.js now resolves request identity before route construction and blocks unsafe targets before any fetch function can run.
- The renewed raw write runner reuses this shared no-write recapture path, so schedule-side route fallback is blocked before future write eligibility.

## Implemented Contract

- schedule_external_id is retained as a correlation key, not the default detail route identity.
- accepted_detail_external_id is the request identity only after a re-accepted mapping/baseline contract is present.
- source_url_fragment_external_id, source_page_url, source_page_url_base, slug, and fragment evidence are insufficient on their own.
- recapture_request_identity and recapture_expected_identity are explicit resolver outputs.
- route_identity_strategy records accepted_detail_external_id or blocked_until_reaccepted_identity_contract.
- canonical_identity_source records reaccepted_mapping_baseline or none_until_reaccepted_mapping_baseline.

## Blocking Rules

- suspended mapping or baseline blocks recapture.
- missing re-acceptance blocks recapture.
- missing accepted detail identity blocks recapture.
- identity mismatch blocks recapture.
- reverse_fixture_detected blocks recapture.
- hash mismatch under unresolved identity mismatch is secondary_to_identity_mismatch and cannot update baseline.
- raw_write_execution_ready remains false.

## Safety Result

- schedule_side_route_default_disabled=true
- identity_contract_resolver_added_or_updated=true
- suspended_mapping_baseline_blocks_recapture=true
- missing_re_acceptance_blocks_recapture=true
- page_url_base_alone_insufficient_enforced=true
- identity_mismatch_blocks_recapture=true
- hash_mismatch_under_identity_mismatch_blocks_baseline_update=true
- raw_write_execution_ready=false
- live_fetch_performed=false
- recapture_retry_performed=false
- db_write_performed=false
- raw_match_data_insert_performed=false
- raw_write_execution_performed=false

## Next Step

- recommended_next_step=Phase 5.21L2V3AX: controlled no-write identity contract regression planning
