# Ligue 1 Corrected Generation Regression ADG15

- Phase: Phase 5.21-ADG15
- Status: completed_corrected_generation_regression

## Counts
| Metric | Count |
| --- | --- |
| total_batch | 51 |
| request_contract | 42 |
| suspended | 8 |
| positive_control | 1 |
| accepted_validated_no_write | 1 |
| rejected_reverse_fixture_mapping | 7 |
| unknown_insufficient_evidence | 35 |
| suspended_still_blocked | 8 |
| correction_candidate_required | 7 |
| raw_write_ready | 0 |

## Results
| ext_id | expected | classification | status | correction | delta |
| --- | --- | --- | --- | --- | --- |
| 4830466 | Rennes vs Marseille | suspended_still_blocked | blocked | false | null |
| 4830461 | Lens vs Lyon | suspended_still_blocked | blocked | false | null |
| 4830463 | Monaco vs Le Havre | suspended_still_blocked | blocked | false | null |
| 4830465 | Nice vs Toulouse | suspended_still_blocked | blocked | false | null |
| 4830460 | Brest vs Lille | unknown_insufficient_evidence | blocked | false | null |
| 4830458 | Angers vs Paris FC | rejected_reverse_fixture_mapping | blocked | true | 161 |
| 4830459 | Auxerre vs Lorient | unknown_insufficient_evidence | blocked | false | null |
| 4830462 | Metz vs Strasbourg | unknown_insufficient_evidence | blocked | false | null |
| 4830464 | Nantes vs Paris Saint-Germain | rejected_reverse_fixture_mapping | blocked | true | 248 |
| 4830473 | Paris Saint-Germain vs Angers | unknown_insufficient_evidence | blocked | false | null |
| 4830471 | Marseille vs Paris FC | rejected_reverse_fixture_mapping | blocked | true | 161 |
| 4830472 | Nice vs Auxerre | unknown_insufficient_evidence | blocked | false | null |
| 4830470 | Lyon vs Metz | rejected_reverse_fixture_mapping | blocked | true | 155 |
| 4830469 | Lorient vs Rennes | rejected_reverse_fixture_mapping | blocked | true | 153 |
| 4830467 | Le Havre vs Lens | rejected_reverse_fixture_mapping | blocked | true | 159 |
| 4830474 | Strasbourg vs Nantes | unknown_insufficient_evidence | blocked | false | null |
| 4830475 | Toulouse vs Brest | unknown_insufficient_evidence | blocked | false | null |
| 4830468 | Lille vs Monaco | rejected_reverse_fixture_mapping | blocked | true | 259 |
| 4830478 | Lens vs Brest | unknown_insufficient_evidence | blocked | false | null |
| 4830479 | Lorient vs Lille | unknown_insufficient_evidence | blocked | false | null |
| 4830482 | Nantes vs Auxerre | unknown_insufficient_evidence | blocked | false | null |
| 4830484 | Toulouse vs Paris Saint-Germain | unknown_insufficient_evidence | blocked | false | null |
| 4830476 | Angers vs Rennes | unknown_insufficient_evidence | blocked | false | null |
| 4830477 | Le Havre vs Nice | unknown_insufficient_evidence | blocked | false | null |
| 4830481 | Monaco vs Strasbourg | suspended_still_blocked | blocked | false | null |
| 4830483 | Paris FC vs Metz | unknown_insufficient_evidence | blocked | false | null |
| 4830480 | Lyon vs Marseille | unknown_insufficient_evidence | blocked | false | null |
| 4830488 | Marseille vs Lorient | unknown_insufficient_evidence | blocked | false | null |
| 4830490 | Nice vs Nantes | unknown_insufficient_evidence | blocked | false | null |
| 4830485 | Auxerre vs Monaco | unknown_insufficient_evidence | blocked | false | null |
| 4830487 | Lille vs Toulouse | unknown_insufficient_evidence | blocked | false | null |
| 4830486 | Brest vs Paris FC | unknown_insufficient_evidence | blocked | false | null |
| 4830489 | Metz vs Angers | unknown_insufficient_evidence | blocked | false | null |
| 4830491 | Paris Saint-Germain vs Lens | unknown_insufficient_evidence | blocked | false | null |
| 4830493 | Strasbourg vs Le Havre | unknown_insufficient_evidence | blocked | false | null |
| 4830492 | Rennes vs Lyon | unknown_insufficient_evidence | blocked | false | null |
| 4830498 | Lyon vs Angers | unknown_insufficient_evidence | blocked | false | null |
| 4830501 | Nantes vs Rennes | unknown_insufficient_evidence | blocked | false | null |
| 4830495 | Brest vs Nice | unknown_insufficient_evidence | blocked | false | null |
| 4830497 | Lens vs Lille | unknown_insufficient_evidence | blocked | false | null |
| 4830502 | Paris FC vs Strasbourg | unknown_insufficient_evidence | blocked | false | null |
| 4830494 | Auxerre vs Toulouse | unknown_insufficient_evidence | blocked | false | null |
| 4830496 | Le Havre vs Lorient | suspended_still_blocked | blocked | false | null |
| 4830500 | Monaco vs Metz | unknown_insufficient_evidence | blocked | false | null |
| 4830499 | Marseille vs Paris Saint-Germain | unknown_insufficient_evidence | blocked | false | null |
| 4830510 | Strasbourg vs Marseille | unknown_insufficient_evidence | blocked | false | null |
| 4830505 | Lorient vs Monaco | unknown_insufficient_evidence | blocked | false | null |
| 4830511 | Toulouse vs Nantes | suspended_still_blocked | blocked | false | null |
| 4830508 | Paris Saint-Germain vs Auxerre | suspended_still_blocked | blocked | false | null |
| 4830507 | Nice vs Paris FC | unknown_insufficient_evidence | blocked | false | null |
| 4813735 | AFC Bournemouth vs Manchester City | accepted_validated | passed | false | 0 |

## Safety

- no live fetch / network / DB write / raw write
- no re-acceptance / suspension reversal
- no source inventory / candidate production mutation
- raw_write_ready_count=0

## Recommended Next Step

many targets lack observed identity; recommend evidence acquisition planning; do not raw write
