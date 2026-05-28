# FotMob Identity Mapping / Source Inventory Audit Result ADG8

- Phase: Phase 5.21-ADG8
- Status: completed_bounded_identity_mapping_source_inventory_audit_execution
- audit_execution_performed=true
- correct_mapping_count=1
- reverse_fixture_mapping_error_count=5
- home_away_inversion_count=5
- same_team_pair_wrong_leg_count=5
- date_mismatch_count=5
- source_inventory_route_error_count=5
- candidate_generation_rule_defect_count=5
- suspended_reference_still_blocked_count=2
- mapping_correction_candidate_count=5
- source_inventory_mutation_performed=false
- candidate_mutation_performed=false
- db_write_performed=false
- raw_write_execution_performed=false
- re_acceptance_execution_performed=false
- suspension_reversal_performed=false
- raw_write_execution_ready=false

## Audit Results

| sample  | expected                                   | observed                                   | orientation | date_delta | classification                    | correction |
| ------- | ------------------------------------------ | ------------------------------------------ | ----------- | ---------- | --------------------------------- | ---------- |
| 4813735 | 4813735 AFC Bournemouth vs Manchester City | 4813735 AFC Bournemouth vs Manchester City | matches     | null       | correct_mapping                   | false      |
| 4830458 | 4830458 Angers vs Paris FC                 | 4830627 Paris FC vs Angers                 | reversed    | 161        | reverse_fixture_mapping_error     | true       |
| 4830459 | 4830459 Auxerre vs Lorient                 | 4830667 Lorient vs Auxerre                 | reversed    | 196        | reverse_fixture_mapping_error     | true       |
| 4830460 | 4830460 Brest vs Lille                     | 4830648 Lille vs Brest                     | reversed    | 181        | reverse_fixture_mapping_error     | true       |
| 4830462 | 4830462 Metz vs Strasbourg                 | 4830618 Strasbourg vs Metz                 | reversed    | 154        | reverse_fixture_mapping_error     | true       |
| 4830464 | 4830464 Nantes vs Paris Saint-Germain      | 4830689 Paris Saint-Germain vs Nantes      | reversed    | 248        | reverse_fixture_mapping_error     | true       |
| 4830461 | 4830461 Lens vs Lyon                       | 4830758 Lyon vs Lens                       | reversed    | 274        | suspended_reference_still_blocked | false      |
| 4830463 | 4830463 Monaco vs Le Havre                 | 4830622 Le Havre vs Monaco                 | reversed    | 161        | suspended_reference_still_blocked | false      |

## Root Cause

- source inventory route mapping defect
- candidate generation rule defect
- same-team-pair wrong-leg / home-away guard missing

## Recommended Next Step

plan runtime correction guard for source inventory/candidate generation before any reclassification or raw write

No source inventory mutation, candidate mutation, DB write, raw write, re-acceptance, suspension reversal, live fetch, network request, browser automation, or full payload save/print was performed.
