# FotMob Identity Mapping / Source Inventory Audit Plan ADG7

> Date: 2026-05-28
> Phase: Phase 5.21-ADG7
> Scope: planning only

## 1. Planning Goal

ADG7 plans a bounded identity mapping correction and source inventory audit after ADG6 proved that the positive control `#4813735` validates through the public page-route while 5 request-contract samples resolve to reversed or home/away inverted fixtures.

ADG7 does not execute live fetch, network request, browser automation, direct API probing, DB write, raw write, re-acceptance, suspension reversal, source inventory mutation, candidate mutation execution, or full payload save/print.

## 2. ADG6 Input Summary

- `positive_sample_result=page_route_identity_validated`
- `observed_detail_id=4813735`
- `reverse_fixture_or_home_away_inversion_count=5`
- `suspended_reference_blocked_count=2`
- `anti_bot_or_access_block_count=0`
- `insufficient_safe_evidence_count=0`
- `identity_mismatch_count=0`
- `raw_write_ready_count=0`
- `direct_api_request_contract_blocked=true`

## 3. Planned Audit Samples

Positive control:

- `positive_bournemouth_mancity_4813735`: expected and observed detail id `4813735`; observed teams `AFC Bournemouth` / `Manchester City`; classification `page_route_identity_validated`

Reverse fixture samples:

- `4830458 -> observed_detail_id=4830627`
- `4830459 -> observed_detail_id=4830667`
- `4830460 -> observed_detail_id=4830648`
- `4830462 -> observed_detail_id=4830618`
- `4830464 -> observed_detail_id=4830689`

Suspended reference samples:

- `4830461 -> observed_detail_id=4830758`
- `4830463 -> observed_detail_id=4830622`

The future 42-target request-contract population remains in ADG8 planning scope. ADG7 does not execute the full audit.

## 4. Planned Audit Fields

- `target_match_id`
- `schedule_external_id`
- `expected_detail_external_id_candidate`
- `observed_detail_id`
- `source_page_url`
- `source_url_path_slug`
- `source_url_fragment_external_id`
- `expected_home_team`
- `expected_away_team`
- `observed_home_team`
- `observed_away_team`
- `expected_match_date`
- `observed_match_date`
- `expected_competition`
- `observed_competition`
- `source_inventory_record_key`
- `candidate_generation_rule`
- `route_matching_rule`
- `team_pair_key`
- `home_away_orientation_status`
- `date_delta`
- `competition_match_status`
- `reverse_fixture_detected`
- `mapping_correction_candidate`
- `audit_classification`

## 5. Planned Classifications

- `correct_mapping`
- `reverse_fixture_mapping_error`
- `home_away_inversion`
- `same_team_pair_wrong_leg`
- `date_mismatch`
- `competition_mismatch`
- `source_inventory_route_error`
- `candidate_generation_rule_defect`
- `slug_collision_or_ambiguous_route`
- `detail_hash_candidate_wrong_for_target`
- `suspended_reference_still_blocked`
- `insufficient_source_inventory_evidence`

## 6. Planned Correction Strategy

- require strict home/away/date/competition validation before accepting any detail hash candidate
- do not accept `detail_external_id_candidate` based only on URL hash
- add candidate generation guard for reversed home/away, wrong same-team-pair leg, date mismatch, and competition/season mismatch
- output `mapping_correction_candidate`, `superseded_detail_external_id_candidate`, and `rejected_detail_external_id_candidate`
- preserve suspended blockers
- keep `raw_write_execution_ready=false` until correction is implemented and no-write validated

## 7. ADG8 Safety Boundaries

- no raw write
- no `raw_match_data` insert
- no matches write
- no re-acceptance
- no suspension reversal
- no source inventory mutation
- no candidate mutation execution
- no full payload save/print
- no bulk harvesting
- no 403/proxy/captcha/access-control bypass

Recommended next step: ADG8 bounded identity mapping/source inventory audit execution with explicit authorization.
