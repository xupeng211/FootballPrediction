<!-- markdownlint-disable MD013 -->

# FotMob Ligue 1 ADG60 Raw Payload Source Inventory

- lifecycle: phase-artifact
- phase: ADG60-RAW-PAYLOAD-SOURCE-INVENTORY
- scope: inventory only
- no live fetch
- no network fetch
- no browser automation
- no DB write
- no raw write
- no raw_match_data insert
- no payload save
- no schema migration
- no ADG60 write
- current blocker: blocked_missing_payload=32

This PR does not acquire raw payload. It only inventories existing code paths.

## Candidate Files Reviewed

- candidate_files_reviewed: 133
- reusable_candidates: 21
- dangerous_candidates: 49
- deprecated_candidates: 0

## Classification Table

| path | type | safety | reuse |
| --- | --- | --- | --- |
| docs/_manifests/fotmob_ligue1_adg59b_source_controlled_acceptance_suspension_state.json | manifest | safe_to_read_only | reference_only |
| docs/_manifests/fotmob_ligue1_adg60_preflight_no_write.json | manifest | safe_to_read_only | reference_only |
| docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.controlled_raw_match_data_write_execution_plan.phase521l2v3aj.json | manifest | safe_to_read_only | reference_only |
| docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.no_write_payload_recapture_plan.phase521l2v3an.json | manifest | safe_to_read_only | reference_only |
| docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.no_write_payload_recapture_result.phase521l2v3ao.json | manifest | safe_to_read_only | reference_only |
| docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.raw_write_input_source_investigation.phase521l2v3ak.json | manifest | safe_to_read_only | reference_only |
| docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AK.md | report | safe_to_read_only | reference_only |
| docs/_reports/FOTMOB_RAW_DETAIL_ACCESS_ROUTE_AUDIT_PHASE5_12L2A.md | report | safe_to_read_only | reference_only |
| docs/_reports/RAW_MATCH_DATA_COMPLETENESS_SOURCE_FIDELITY_AUDIT_PHASE5_21L2A.md | report | safe_to_read_only | reference_only |
| docs/_reports/RAW_MATCH_DATA_INGEST_PLANNING_PHASE5_13L2.md | report | safe_to_read_only | reference_only |
| docs/_reports/RAW_STORAGE_STRATEGY_REVISION_PLANNING_PHASE5_21L2C.md | report | safe_to_read_only | reference_only |
| docs/_reports/SINGLE_LEAGUE_PAGEPROPS_V2_CONTROLLED_WRITE_EXECUTION_PHASE5_21L2V.md | report | safe_to_read_only | reference_only |
| docs/_reports/SINGLE_LEAGUE_PAGEPROPS_V2_CONTROLLED_WRITE_PLANNING_PHASE5_21L2U.md | report | safe_to_read_only | reference_only |
| scripts/ops/fotmob_ligue1_ssr_pageprops_discovery_gate_adg46.js | raw-write script | dangerous_write_capable | do_not_use |
| scripts/ops/pageprops_v2_no_write_payload_recapture_execute.js | no-write execute | dangerous_live_fetch_capable | reference_only |
| scripts/ops/pageprops_v2_no_write_payload_recapture_plan.js | no-write plan | safe_as_reference_only | reusable_with_guardrails |
| scripts/ops/pageprops_v2_no_write_preview.js | no-write execute | dangerous_live_fetch_capable | reference_only |
| scripts/ops/pageprops_v2_raw_write_input_source_investigation.js | no-write execute | safe_as_reference_only | reference_only |
| scripts/ops/pageprops_v2_target_identity_reconciliation_plan.js | no-write plan | safe_as_reference_only | reference_only |
| scripts/ops/raw_match_data_completeness_fidelity_audit.js | audit script | safe_as_reference_only | reusable_with_guardrails |
| scripts/ops/renewed_pageprops_v2_raw_write_execute.js | raw-write script | dangerous_write_capable | do_not_use |
| scripts/ops/single_league_pageprops_v2_controlled_write_execute.js | controlled-write script | dangerous_write_capable | do_not_use |
| scripts/ops/single_league_pageprops_v2_controlled_write_plan.js | no-write plan | safe_as_reference_only | reference_only |
| scripts/ops/single_league_small_batch_pageprops_v2_preflight.js | no-write execute | dangerous_live_fetch_capable | reference_only |

## Reusable Candidates

- scripts/ops/fotmob_ligue1_canonical_detail_url_discovery_adg39.js
- scripts/ops/l2_raw_match_data_ingest_authorization.js
- scripts/ops/l2_raw_match_data_ingest_plan.js
- scripts/ops/l2_remaining_raw_match_data_acquisition_authorization.js
- scripts/ops/l2_remaining_raw_match_data_acquisition_preflight.js
- scripts/ops/large_scale_pageprops_v2_acquisition_strategy_plan.js
- scripts/ops/pageprops_v2_continued_date_rule_investigation.js
- scripts/ops/pageprops_v2_continued_detail_endpoint_investigation.js
- scripts/ops/pageprops_v2_continued_metadata_investigation.js
- scripts/ops/pageprops_v2_detail_api_endpoint_feasibility.js

## Dangerous Candidates

- scripts/ops/all_seeded_pageprops_v2_canonical_read_verification.js
- scripts/ops/backfill_historical_raw_match_data.js
- scripts/ops/fotmob_ligue1_correct_orientation_route_hash_gate_adg48.js
- scripts/ops/fotmob_ligue1_ssr_pageprops_bounded_probe_adg46.js
- scripts/ops/fotmob_ligue1_ssr_pageprops_discovery_gate_adg46.js
- scripts/ops/html_hydration_source_fidelity_live_compare.js
- scripts/ops/l2_raw_match_data_ingest_preflight.js
- scripts/ops/l2_raw_match_data_write.js
- scripts/ops/l2_remaining_raw_match_data_write.js
- scripts/ops/pageprops_v2_accepted_mapping_baseline_contradiction_review_execute.js
- scripts/ops/pageprops_v2_accepted_mapping_baseline_contradiction_review_plan.js
- scripts/ops/pageprops_v2_accepted_mapping_baseline_suspension_execute.js
- scripts/ops/pageprops_v2_accepted_mapping_baseline_suspension_plan.js
- scripts/ops/pageprops_v2_baseline_acceptance_execute.js

## Deprecated Candidates

- none classified

## Target Adaptability

- target_match_id / corrected_hash_id / corrected_route_hash_pair are available for all 32 targets.
- Existing pageProps v2 planning paths can guide an authorization-gated acquisition plan.
- Live recapture and controlled write scripts are reference-only or do-not-use in this phase.
- Legacy API routes are not preferred for ADG60 payload acquisition.

## Recommended Next Step

Prepare an authorization-gated ADG60 payload acquisition plan that reuses pageProps v2 planning/preflight references only; do not execute recapture or raw write in this inventory PR.
