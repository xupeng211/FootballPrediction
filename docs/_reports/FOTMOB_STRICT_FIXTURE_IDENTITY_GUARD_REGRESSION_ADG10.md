# FotMob Strict Fixture Identity Guard Regression ADG10

- Phase: Phase 5.21-ADG10
- Status: completed_strict_fixture_identity_guard_regression
- regression_execution_performed=true

## Counts

| Metric | Count |
| --- | --- |
| positive_control | 1 |
| request_contract_targets | 42 |
| suspended_targets | 8 |
| guard_passed | 0 |
| guard_blocked | 50 |
| reverse_fixture_mapping_error | 5 |
| home_away_inversion | 0 |
| same_team_pair_wrong_leg | 0 |
| date_mismatch | 5 |
| missing_observed_identity_evidence | 37 |
| correction_candidate_required | 5 |
| suspended_still_blocked | 8 |
| raw_write_ready | 0 |
| re_acceptance_candidate | 0 |

## Request Contract Target Regression

| external_id | expected_teams | classification | status | correction | date_delta |
| --- | --- | --- | --- | --- | --- |
| 4830460 | Brest vs Lille | reverse_fixture_mapping_error | blocked | true | 181 |
| 4830458 | Angers vs Paris FC | reverse_fixture_mapping_error | blocked | true | 161 |
| 4830459 | Auxerre vs Lorient | reverse_fixture_mapping_error | blocked | true | 196 |
| 4830462 | Metz vs Strasbourg | reverse_fixture_mapping_error | blocked | true | 154 |
| 4830464 | Nantes vs Paris Saint-Germain | reverse_fixture_mapping_error | blocked | true | 248 |
| 4830473 | Paris Saint-Germain vs Angers | missing_observed_identity_evidence | blocked | false | null |
| 4830471 | Marseille vs Paris FC | missing_observed_identity_evidence | blocked | false | null |
| 4830472 | Nice vs Auxerre | missing_observed_identity_evidence | blocked | false | null |
| 4830470 | Lyon vs Metz | missing_observed_identity_evidence | blocked | false | null |
| 4830469 | Lorient vs Rennes | missing_observed_identity_evidence | blocked | false | null |
| 4830467 | Le Havre vs Lens | missing_observed_identity_evidence | blocked | false | null |
| 4830474 | Strasbourg vs Nantes | missing_observed_identity_evidence | blocked | false | null |
| 4830475 | Toulouse vs Brest | missing_observed_identity_evidence | blocked | false | null |
| 4830468 | Lille vs Monaco | missing_observed_identity_evidence | blocked | false | null |
| 4830478 | Lens vs Brest | missing_observed_identity_evidence | blocked | false | null |
| 4830479 | Lorient vs Lille | missing_observed_identity_evidence | blocked | false | null |
| 4830482 | Nantes vs Auxerre | missing_observed_identity_evidence | blocked | false | null |
| 4830484 | Toulouse vs Paris Saint-Germain | missing_observed_identity_evidence | blocked | false | null |
| 4830476 | Angers vs Rennes | missing_observed_identity_evidence | blocked | false | null |
| 4830477 | Le Havre vs Nice | missing_observed_identity_evidence | blocked | false | null |
| 4830483 | Paris FC vs Metz | missing_observed_identity_evidence | blocked | false | null |
| 4830480 | Lyon vs Marseille | missing_observed_identity_evidence | blocked | false | null |
| 4830488 | Marseille vs Lorient | missing_observed_identity_evidence | blocked | false | null |
| 4830490 | Nice vs Nantes | missing_observed_identity_evidence | blocked | false | null |
| 4830485 | Auxerre vs Monaco | missing_observed_identity_evidence | blocked | false | null |
| 4830487 | Lille vs Toulouse | missing_observed_identity_evidence | blocked | false | null |
| 4830486 | Brest vs Paris FC | missing_observed_identity_evidence | blocked | false | null |
| 4830489 | Metz vs Angers | missing_observed_identity_evidence | blocked | false | null |
| 4830491 | Paris Saint-Germain vs Lens | missing_observed_identity_evidence | blocked | false | null |
| 4830493 | Strasbourg vs Le Havre | missing_observed_identity_evidence | blocked | false | null |
| 4830492 | Rennes vs Lyon | missing_observed_identity_evidence | blocked | false | null |
| 4830498 | Lyon vs Angers | missing_observed_identity_evidence | blocked | false | null |
| 4830501 | Nantes vs Rennes | missing_observed_identity_evidence | blocked | false | null |
| 4830495 | Brest vs Nice | missing_observed_identity_evidence | blocked | false | null |
| 4830497 | Lens vs Lille | missing_observed_identity_evidence | blocked | false | null |
| 4830502 | Paris FC vs Strasbourg | missing_observed_identity_evidence | blocked | false | null |
| 4830494 | Auxerre vs Toulouse | missing_observed_identity_evidence | blocked | false | null |
| 4830500 | Monaco vs Metz | missing_observed_identity_evidence | blocked | false | null |
| 4830499 | Marseille vs Paris Saint-Germain | missing_observed_identity_evidence | blocked | false | null |
| 4830510 | Strasbourg vs Marseille | missing_observed_identity_evidence | blocked | false | null |
| 4830505 | Lorient vs Monaco | missing_observed_identity_evidence | blocked | false | null |
| 4830507 | Nice vs Paris FC | missing_observed_identity_evidence | blocked | false | null |

## Suspended Preservation Regression

| external_id | classification | status |
| --- | --- | --- |
| 4830466 | suspended_reference_still_blocked | blocked |
| 4830461 | suspended_reference_still_blocked | blocked |
| 4830463 | suspended_reference_still_blocked | blocked |
| 4830465 | suspended_reference_still_blocked | blocked |
| 4830481 | suspended_reference_still_blocked | blocked |
| 4830496 | suspended_reference_still_blocked | blocked |
| 4830511 | suspended_reference_still_blocked | blocked |
| 4830508 | suspended_reference_still_blocked | blocked |

## Positive Control

| external_id | classification | status |
| --- | --- | --- |
| 4813735 | correct_mapping | passed |

## Safety

- no live fetch / network request / browser automation / direct API probing
- no DB writes / raw writes / raw_match_data inserts
- no re-acceptance / suspension reversal
- no source inventory mutation / candidate mutation execution
- no full payload saved
- raw_write_ready_count=0

## Recommended Next Step

evidence_acquisition_planning_for_targets_without_observed_identity; do not raw write
