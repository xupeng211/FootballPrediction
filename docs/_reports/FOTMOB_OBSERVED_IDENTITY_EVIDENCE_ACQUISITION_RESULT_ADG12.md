# FotMob Observed Identity Evidence Acquisition Result ADG12

- Phase: Phase 5.21-ADG12
- Status: completed_bounded_observed_identity_evidence_acquisition_execution
- Batch: ADG12_BATCH_A
- evidence_acquisition_performed=true

## Batch A Results

| external_id | status | observed_id | home vs away | guard | delta |
| --- | --- | --- | --- | --- | --- |
| 4813735 | evidence_reused_from_existing_source | 4813735 | AFC Bournemouth vs Manchester City | correct_mapping | 0 |
| 4830467 | observed_identity_acquired | 4830630 | Lens vs Le Havre | reverse_fixture_mapping_error | 159 |
| 4830468 | observed_identity_acquired | 4830751 | Monaco vs Lille | reverse_fixture_mapping_error | 259 |
| 4830469 | observed_identity_acquired | 4830628 | Rennes vs Lorient | reverse_fixture_mapping_error | 153 |
| 4830470 | observed_identity_acquired | 4830625 | Metz vs Lyon | reverse_fixture_mapping_error | 155 |
| 4830471 | observed_identity_acquired | 4830635 | Paris FC vs Marseille | reverse_fixture_mapping_error | 161 |
| 4830458 | evidence_reused_from_existing_source | 4830627 | Paris FC vs Angers | reverse_fixture_mapping_error | 161 |
| 4830464 | evidence_reused_from_existing_source | 4830689 | Paris Saint-Germain vs Nantes | reverse_fixture_mapping_error | 248 |
| 4830466 | suspended_control_not_fetched | null | ? vs ? | suspended_control_still_blocked | null |

## Counts

| Metric | Count |
| --- | --- |
| batch_sample_count | 9 |
| positive_control | 1 |
| missing_observed_targets | 5 |
| known_reverse_controls | 2 |
| suspended_control | 1 |
| request_attempts | 5 |
| evidence_reuse | 3 |
| observed_identity_acquired | 5 |
| strict_guard_passed_no_write | 1 |
| strict_guard_blocked | 8 |
| reverse_fixture_error | 7 |
| suspended_still_blocked | 1 |
| raw_write_ready | 0 |

## Safety

- no browser automation
- no direct API probing
- no proxy/captcha/access-control bypass
- no DB writes / raw writes / raw_match_data inserts
- no re-acceptance / suspension reversal
- no full HTML/pageProps/raw_data saved to disk
- no source inventory mutation / candidate mutation
- raw_write_ready_count=0

## Recommended Next Step

batch_a_successful_acquisition; plan_batch_b_or_no_write_acceptance_review; do not raw write
