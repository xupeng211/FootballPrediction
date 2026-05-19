# Data Entrypoint Governance - Phase 5.21 L2V3G

## A. Current Status

- phase=schedule_detail_route_normalization_fix_implementation_planning
- branch=data/pageprops-v2-route-normalization-fix-planning-phase521l2v3g
- base_main_head=e4bc97c918cf8c0dec1650f17550ca037e9606dc
- source_manifest_path=docs/\_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json
- source_normalization_proposal_path=docs/\_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.schedule_detail_identity_normalization_proposal.phase521l2v3f.json
- route_normalization_fix_proposal_path=docs/\_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.route_normalization_fix_proposal.phase521l2v3g.json

## B. PR #1280 Draft Review / Merge Result

- pr_1280_state=MERGED
- pr_1280_was_draft_reviewed=true
- pr_1280_marked_ready=true
- pr_1280_merge_commit=e4bc97c918cf8c0dec1650f17550ca037e9606dc
- merge_scope=L2V3F no-write schedule/detail identity normalization planning
- candidate_scope_explained_before_ready=true

## C. main HEAD / CI Status

- main_head=e4bc97c918cf8c0dec1650f17550ca037e9606dc
- main_ci_status=success
- main_ci_run=26077415323
- required_checks=Environment / Proxy / Static / Unit Gate success; Docker Build Validation success

## D. Authorization Scope

- planning_authorized=true
- route_normalization_fix_planning_authorized=true
- no_write=true
- no production implementation
- no DB write authorization
- no raw write authorization
- no identity mapping acceptance
- no baseline acceptance

## E. No-Write Guarantee

- db_write_performed=false
- raw_insert_performed=false
- matches_write_performed=false
- identity_mapping_acceptance_performed=false
- baseline_acceptance_performed=false
- raw_write_retry_performed=false
- schema_migration_performed=false
- parser_features_training_prediction_performed=false
- full_raw_data_pageProps_source_body_printed=false
- full_raw_data_pageProps_source_body_saved=false

## F. L2V3F Recap

- checked_target_count=8
- proposed_mapping_count=8
- high_confidence_mapping_count=0
- medium_confidence_mapping_count=8
- unresolved_mapping_count=8
- page_url_base_match_count=8
- team_pair_match_count=8
- exact_date_match_count=0
- team_date_status_mismatch_count=8
- mappings_are_proposal_only_unaccepted=true
- recommended_next_step=schedule_detail_route_normalization_fix_implementation_planning

## G. Discovery Result

- current_detail_fetch_route_uses=manifest target external_id supplied as `externalId`
- current_route_template=https://www.fotmob.com/match/{externalId}
- current_route_identity_for_l2v3f_mismatch_targets=schedule_or_listing_external_id
- current_fetcher_returns_requested_identity_as_top_level_external_id=true
- current_fetcher_observed_identity_surface=stable payload / raw_data `matchId`
- current_fetcher_contract_gap=requested schedule identity and observed canonical detail identity are not exposed as separate top-level fields.
- current_raw_write_candidate_identity_source=manifest `match_id` and manifest `external_id`
- source_inventory_adapter_preserves_source_inventory_identity=true
- route_accepts_schedule_id_but_returns_detail_id=observed for the 8 L2V3F mismatch targets through prior safe metadata
- whether_this_is_consistent_for_all_50_candidates=unknown
- next_information_needed=expanded no-write route normalization proposal or implementation planning tests before any acceptance

## H. Candidate Scope Review

- candidate_matches=58
- candidate_fotmob_pageprops_v2_raw_rows=8
- candidate_count_scope_explanation=50 manifest schedule targets plus 8 pre-existing seeded pageProps v2 match identities in current Ligue 1 2025/2026 DB safety scope.
- candidate_count_is_schedule_targets_plus_observed_detail_ids=false
- observed_detail_external_ids_in_matches_count=0
- candidate_v2_rows_are_l2v3g_writes=false
- candidate_scope_is_raw_write_success=false

## I. Route Normalization Fix Planning Conclusion

1. Current detail fetch route uses schedule/listing external_id for L2V3F mismatch targets.
2. If FotMob accepts a schedule/listing ID but returns a canonical detail identity, the system must model both identities separately.
3. Fetcher output should expose `requested_schedule_external_id`, `observed_detail_external_id`, `page_url_base`, `canonical_page_url`, and `identity_reconciliation_status`.
4. Route normalization fix should start at `FotMobRawDetailFetcher` contract and be consumed by source inventory, manifest/preflight proposal, and raw write precondition gates.
5. Raw write should continue to use manifest schedule `match_id` only after a separate accepted identity mapping artifact exists; otherwise raw write must be blocked.
6. `matches.external_id` must not be overwritten with detail external_id.
7. PageUrl base match plus date mismatch remains medium confidence and cannot become high confidence.
8. Candidate matches=58 / candidate v2 rows=8 must remain a DB safety scope explanation, not a write-success signal.
9. A dedicated accepted identity mapping artifact is required before baseline acceptance or raw write retry.
10. Full 50-candidate route normalization evidence remains unknown and can be handled by a later no-write expansion if required.

## J. Proposed Fetcher / Raw-Write Gating Contract

- fetcher_must_not_silently_treat_requested_external_id_as_canonical_detail_identity=true
- fetcher_should_expose_requested_schedule_external_id=true
- fetcher_should_expose_observed_detail_external_id=true
- fetcher_should_expose_page_url_base=true
- fetcher_should_expose_identity_mismatch_status=true
- fetcher_must_not_mutate_db=true
- fetcher_must_not_rewrite_matches_external_id=true
- raw_write_blocked_when_requested_schedule_id_differs_from_observed_detail_id_without_accepted_mapping=true
- proposal_only_mapping_is_insufficient=true
- date_mismatch_blocks_high_confidence_acceptance=true
- raw_write_ready_for_execution=false
- requires_separate_identity_mapping_acceptance=true
- requires_separate_baseline_acceptance=true
- requires_separate_final_db_write_authorization=true

## K. Manifest / Proposal / Report Updates

- report_added=docs/\_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3G.md
- proposal_added=docs/\_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.route_normalization_fix_proposal.phase521l2v3g.json
- manifest_updated=true
- route_normalization_fix_required=true
- accepted_identity_mapping_created=false
- accepted_baseline_created=false
- raw_write_ready_for_execution=false

## L. DB Row Count Safety Result

- db_check_mode=SELECT-only via db container psql
- matches=60
- raw_match_data=18
- bookmaker_odds_history=2
- l3_features=2
- match_features_training=2
- predictions=2
- ligue1_2025_2026_matches=58
- fotmob_pageprops_v2_rows=8
- db_write_performed=false

## M. Tests / Validation

- `jq empty` on changed JSON: passed
- L2V3G unit tests: passed, 6 tests
- targeted L2V3 / L2V3B / L2V3C / L2V3D / L2V3E / L2V3F / L2V3G / L2V / L2U / L2T / fetcher / source inventory / selector / stable hash safety suite: passed, 833 tests
- `npm test`: passed
- `npm run test:coverage`: passed
- `npm run lint`: passed
- prettier check on changed docs/json/test files: passed
- `git diff --check`: passed
- DB row count safety check: passed, SELECT-only
- l1-config residue check: passed, no `tests/fixtures/l1-config-*` filesystem or tracked residue
- docs/\_staging_preview absence check: passed, directory absent

## N. PR Status

- branch_ready_for_pr=true
- pr_created=true
- pr_number=1281
- pr_url=https://github.com/xupeng211/FootballPrediction/pull/1281
- pr_status=open_pending_ci

## O. Next Step Recommendation

- recommended_next_step=Phase 5.21L2V3H: schedule_detail_route_normalization_fix_implementation
- note=this still does not authorize DB write, raw_match_data insert, identity mapping acceptance, baseline acceptance, or raw write retry

## P. Explicit Non-Execution

- no DB writes
- no raw_match_data inserts
- no matches writes
- no bookmaker_odds_history writes
- no l3_features writes
- no match_features_training writes
- no predictions writes
- no schema migration
- no production parser implementation
- no feature extraction
- no training/prediction
- no browser/proxy/captcha bypass
- no identity mapping acceptance
- no accepted baseline replacement
- no raw write retry
- no proposal mapping marked as accepted
- no proposal hash marked as accepted baseline
- no raw_write_ready_for_execution=true
- no full raw_data/pageProps/source body print/save
- no invented external_id, target, payload, or hash
- no matches.external_id modification
