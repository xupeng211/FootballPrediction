# FotMob URL Hash Detail Identity Propagation Implementation ADG3

> Date: 2026-05-27
> Phase: Phase 5.21-ADG3
> Scope: runtime implementation, no fetch, no DB write

## 1. Context

ADG2 found that FotMob source inventory already extracts and persists URL hash evidence, but active candidate and recapture identity paths did not carry it as formal detail identity evidence.

Positive sample retained as the control:

`https://www.fotmob.com/zh-Hans/matches/manchester-city-vs-afc-bournemouth/2feiv3#4813735`

- source_url_path_slug=`2feiv3`
- source_url_fragment_external_id=`4813735`
- detail_external_id_candidate=`4813735`
- detail_identity_source=`url_hash_fragment`

## 2. Runtime Changes

ADG3 adds runtime propagation of URL-hash detail identity evidence:

- `FotMobSourceInventoryAdapter` now exposes `source_url_path_slug`, `detail_external_id_candidate`, and `detail_identity_source` from parsed URL fragments.
- `single_league_target_discovery_source_inventory_preflight` carries those fields into generated candidate targets.
- `pageprops_v2_source_inventory_enrichment_apply` preserves the same fields when enriching source-controlled candidate targets.
- `pageprops_v2_enriched_target_regeneration_execute` regenerates enriched targets with URL-hash detail identity candidate fields.
- `FotMobRouteIdentityReconciler` reads `detail_external_id_candidate` and uses it as `recapture_expected_identity` when no accepted detail id exists, while keeping `recapture_request_identity=null` until accepted/reaccepted identity contract requirements are satisfied.
- `pageprops_v2_no_write_payload_recapture_execute` carries detail identity candidate/source through normalized candidates and target result summaries.

## 3. Safety Contract

- live_fetch_performed=false
- network_request_performed=false
- db_write_performed=false
- raw_match_data_insert_performed=false
- raw_write_execution_performed=false
- matches_write_performed=false
- matches_external_id_modified=false
- re_acceptance_execution_performed=false
- suspension_reversal_performed=false
- parser_features_training_prediction_performed=false
- full_payload_saved=false
- full_payload_printed=false
- raw_write_execution_ready=false

URL hash evidence improves identity propagation only. It does not accept a mapping, does not unsuspend a target, does not make a target clean, and does not authorize raw write.

## 4. Blocker Preservation

The recapture contract still blocks:

- missing accepted detail identity
- missing re-acceptance
- suspended mapping or baseline
- reverse fixture / home-away inversion
- page URL or slug alone
- identity mismatch
- hash mismatch secondary to identity mismatch

Blind `schedule_external_id` fallback remains blocked.

## 5. Request Contract

ADG3 does not address the direct API 403 found by ADG2. The direct `matchDetails?matchId=4813735` route remains request-contract/access blocked and requires separate review. No bypass, proxy, captcha handling, or retry behavior was added.

## 6. Recommended Next Step

Run review/verification for the runtime propagation path and then plan the next bounded identity verification step. Do not raw write, do not re-accept, and do not execute bulk recapture from this implementation alone.
