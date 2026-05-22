'use strict';
/* eslint-disable max-lines -- L2V3Q safety contract stays together for auditability. */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_continued_metadata_investigation.js');
const rawWrite = require('../../scripts/ops/renewed_pageprops_v2_raw_write_execute');

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();

function readJson(repoPath) {
    return JSON.parse(fs.readFileSync(path.join(PROJECT_ROOT, repoPath), 'utf8'));
}

function readText(repoPath) {
    return fs.readFileSync(path.join(PROJECT_ROOT, repoPath), 'utf8');
}

function syntheticManifest() {
    return {
        batch_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        source: 'fotmob',
        route: 'html_hydration',
        raw_data_version: 'fotmob_pageprops_v2',
        hash_strategy: 'stable_pageprops_payload_v1',
        league: { league_id: 53, league_name: 'Ligue 1', season: '2025/2026' },
        candidate_targets: Array.from({ length: 50 }, (_, index) => ({
            match_id: `53_20252026_${9000001 + index}`,
            external_id: String(9000001 + index),
            home_team: `Home ${index}`,
            away_team: `Away ${index}`,
            match_date: '2025-08-15T18:45:00.000Z',
            kickoff_time: '2025-08-15T18:45:00.000Z',
            status: 'finished',
            season: '2025/2026',
        })),
        known_completed_targets: Array.from({ length: 8 }, (_, index) => ({
            match_id: `53_20252026_${4830746 + index}`,
            external_id: String(4830746 + index),
        })),
        matches_identity_seed_execution_status: 'completed',
        post_seed_matches_identity_verification_status: 'completed',
        raw_write_fk_prerequisite_status: 'satisfied',
        raw_write_retry_readiness_status: 'ready_for_renewed_authorization',
        eligible_raw_insert_count: 50,
        expected_raw_match_data_after_retry: 68,
        required_next_step: 'renewed_controlled_pageprops_v2_raw_write_execution',
        write_execution_status: 'blocked_missing_matches_fk_prerequisite',
        raw_match_data_write_status: 'not_executed',
        phase_5_21_l2v3p_metadata_check_status: 'completed_controlled_no_write_metadata_only_detail_check',
        raw_write_ready_for_execution: false,
        accepted_mapping_count: 0,
        requires_separate_identity_mapping_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
    };
}

function syntheticMetadataOnlyArtifact() {
    return {
        proposal_phase: 'Phase 5.21L2V3P',
        no_write: true,
        attempted_unknown_target_count: 42,
        metadata_check_success_count: 42,
        raw_write_ready_for_execution: false,
        metadata_only_target_summaries: Array.from({ length: 42 }, (_, index) => ({
            match_id: `53_20252026_${9000001 + index}`,
            schedule_external_id: String(9000001 + index),
            request_url_summary: `https://www.fotmob.com/match/${9000001 + index}`,
            http_status: 200,
            parsed: true,
            parsed_status: 'metadata_only_parsed',
            observed_detail_external_id: String(9100001 + index),
            observed_page_url_base: `/matches/detail-${index}/safe-${index}`,
            schedule_date: '2025-08-15T18:45:00.000Z',
            detail_date: 'Sat, Feb 14, 2026, 18:00 UTC',
            schedule_home_team: `Home ${index}`,
            schedule_away_team: `Away ${index}`,
            detail_home_team: `Away ${index}`,
            detail_away_team: `Home ${index}`,
            status_summary: {
                schedule_status: 'finished',
                detail_status: '[object Object]',
            },
            date_rule_status: 'unresolved_large_gap',
            canonical_identity_status: 'requested_vs_observed_external_id_mismatch',
            identity_reconciliation_status: 'unresolved_schedule_detail_mapping',
            safe_to_consider_for_future_review: false,
            controlled_metadata_check_status: 'success',
            safe_error_summary: 'metadata-only evidence collected',
            payload_size_summary: {
                body_byte_length: 1000000,
                pageprops_json_byte_length: 300000,
                suspicious_small_payload: false,
            },
            top_level_keys_summary: ['content', 'general', 'header'],
            raw_write_blocked: true,
            identity_mapping_acceptance_blocked: true,
            raw_write_blocker_status: 'blocked_pending_separate_identity_mapping_acceptance',
            identity_mapping_acceptance_blocker_status: 'blocked_pending_separate_identity_mapping_acceptance',
            accepted_mapping: false,
            raw_write_authorized: false,
        })),
    };
}

function buildSyntheticRunResult(overrides = {}) {
    return mod.runContinuedMetadataInvestigation({
        manifest: syntheticManifest(),
        metadataOnlyArtifact: syntheticMetadataOnlyArtifact(),
        writeFiles: false,
        ...overrides,
    });
}

test('L2V3Q artifact records a no-write continued metadata investigation phase', () => {
    const result = buildSyntheticRunResult();
    assert.equal(result.ok, true);

    const artifact = result.artifact;
    const manifest = result.updated_manifest;

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3Q');
    assert.equal(artifact.no_write, true);
    assert.equal(artifact.live_source_check_performed, false);
    assert.equal(artifact.network_request_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.matches_external_id_modified, false);
    assert.equal(artifact.identity_mapping_acceptance_performed, false);
    assert.equal(artifact.baseline_acceptance_performed, false);
    assert.equal(artifact.raw_write_retry_performed, false);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.accepted_mapping_count, 0);

    assert.equal(manifest.phase_5_21_l2v3q_investigation_status, artifact.artifact_status);
    assert.equal(manifest.continued_metadata_only_investigation_status, artifact.artifact_status);
    assert.equal(manifest.raw_write_ready_for_execution, false);
    assert.equal(manifest.accepted_mapping_count, 0);
});

test('L2V3Q classifies all 42 unresolved targets as likely reverse fixture or slug reuse with missing reverse evidence', () => {
    const result = buildSyntheticRunResult();
    const artifact = result.artifact;

    assert.equal(artifact.analyzed_target_count, 42);
    assert.equal(artifact.unresolved_large_gap_count, 42);
    assert.equal(artifact.likely_reverse_fixture_or_slug_reuse_count, 42);
    assert.equal(artifact.missing_reverse_fixture_evidence_count, 42);
    assert.equal(artifact.missing_pageurl_base_count, 42);
    assert.equal(artifact.missing_team_reverse_evidence_count, 0);
    assert.equal(artifact.detail_url_construction_suspect_count, 42);
    assert.equal(artifact.route_target_regeneration_needed_count, 0);
    assert.equal(artifact.api_endpoint_preferred_count, 0);
    assert.equal(artifact.future_review_candidate_count, 0);
    assert.equal(artifact.still_blocked_count, 42);

    for (const entry of artifact.analyzed_targets) {
        assert.equal(entry.requested_vs_observed_external_id_mismatch, true);
        assert.equal(entry.team_pair_reversed, true);
        assert.equal(entry.missing_reverse_fixture_evidence, true);
        assert.equal(entry.counterfactual_reverse_fixture_detected, true);
        assert.equal(entry.likely_reverse_fixture_or_slug_reuse, true);
        assert.equal(entry.detail_url_construction_suspect, true);
        assert.equal(entry.still_blocked, true);
        assert.equal(entry.accepted_mapping, false);
        assert.equal(entry.raw_write_ready_for_execution, false);
    }
});

test('unresolved_large_gap and route-construction suspects remain blocked and unaccepted', () => {
    const result = buildSyntheticRunResult();
    const artifact = result.artifact;

    assert.equal(artifact.safety_contract.investigation_result_is_not_accepted_mapping, true);
    assert.equal(artifact.safety_contract.unresolved_large_gap_blocks_identity_mapping_acceptance, true);
    assert.equal(artifact.safety_contract.unresolved_large_gap_blocks_raw_write, true);
    assert.equal(artifact.safety_contract.likely_reverse_fixture_or_slug_reuse_is_not_accepted_mapping, true);
    assert.equal(artifact.safety_contract.detail_url_construction_suspect_is_not_accepted_mapping, true);
    assert.equal(artifact.safety_contract.future_review_candidate_is_not_accepted_mapping, true);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.raw_write_ready_for_execution, false);
});

test('L2V3Q updated manifest is still rejected by the raw write runner gate', () => {
    const result = buildSyntheticRunResult();
    const gate = rawWrite.validateManifestGate(result.updated_manifest);

    assert.equal(gate.ok, false);
    assert.match(gate.errors.join('\n'), /required_next_step|write_execution_status|raw_match_data_write_status/i);
});

test('L2V3Q artifacts avoid full raw_data pageProps and source body payloads', () => {
    const result = buildSyntheticRunResult();
    const texts = [JSON.stringify(result.artifact), result.report, JSON.stringify(result.updated_manifest)];

    for (const text of texts) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
        assert.equal(text.includes('"source_body":'), false);
    }
});

test('repository L2V3Q artifacts preserve no-write and blocking semantics', () => {
    const manifest = readJson('docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json');
    const artifact = readJson(
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.continued_metadata_investigation.phase521l2v3q.json'
    );
    const report = readText('docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3Q.md');

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3Q');
    assert.equal(artifact.no_write, true);
    assert.equal(artifact.network_request_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.likely_reverse_fixture_or_slug_reuse_count, 42);
    assert.equal(artifact.detail_url_construction_suspect_count, 42);
    assert.equal(artifact.route_target_regeneration_needed_count, 0);
    assert.equal(artifact.future_review_candidate_count, 0);

    assert.equal(manifest.phase_5_21_l2v3q_investigation_status, 'completed_no_write_metadata_pattern_investigation');
    assert.equal(manifest.raw_write_ready_for_execution, false);
    assert.equal(manifest.accepted_mapping_count, 0);
    if (manifest.phase_5_21_l2v3u_planning_status) {
        assert.equal(
            manifest.phase_5_21_l2v3u_planning_status,
            'completed_no_write_source_inventory_enrichment_planning'
        );
        if (manifest.phase_5_21_l2v3v_implementation_status) {
            assert.equal(
                manifest.phase_5_21_l2v3v_implementation_status,
                'completed_no_write_source_inventory_enrichment_implementation'
            );
            if (manifest.phase_5_21_l2v3w_investigation_status) {
                assert.equal(
                    manifest.phase_5_21_l2v3w_investigation_status,
                    'completed_no_write_source_inventory_acquisition_path_investigation'
                );
                if (manifest.phase_5_21_l2v3x_planning_status) {
                    assert.equal(
                        manifest.phase_5_21_l2v3x_planning_status,
                        'completed_no_write_controlled_source_inventory_acquisition_planning'
                    );
                    if (manifest.phase_5_21_l2v3y_execution_status) {
                        assert.equal(
                            manifest.phase_5_21_l2v3y_execution_status,
                            'completed_metadata_only_source_inventory_acquisition_execution'
                        );
                        if (manifest.phase_5_21_l2v3aa_execution_status) {
                            assert.equal(
                                manifest.phase_5_21_l2v3aa_execution_status,
                                'completed_controlled_no_write_enriched_target_regeneration_execution'
                            );
                            if (manifest.phase_5_21_l2v3ab_planning_status) {
                                assert.equal(
                                    manifest.phase_5_21_l2v3ab_planning_status,
                                    'completed_no_write_enriched_no_write_verification_planning'
                                );
                                assert.equal(
                                    manifest.recommended_next_step,
                                    'Phase 5.21L2V3AC: controlled enriched no-write verification execution'
                                );
                                assert.equal(
                                    manifest.next_required_step,
                                    'controlled_enriched_no_write_verification_execution'
                                );
                            } else {
                                assert.equal(
                                    manifest.recommended_next_step,
                                    'Phase 5.21L2V3AB: enriched no-write verification planning'
                                );
                                assert.equal(manifest.next_required_step, 'enriched_no_write_verification_planning');
                            }
                        } else if (manifest.phase_5_21_l2v3z_planning_status) {
                            assert.equal(
                                manifest.phase_5_21_l2v3z_planning_status,
                                'completed_no_write_enriched_target_regeneration_planning'
                            );
                            assert.equal(
                                manifest.recommended_next_step,
                                'Phase 5.21L2V3AA: controlled enriched target regeneration execution'
                            );
                            assert.equal(
                                manifest.next_required_step,
                                'controlled_enriched_target_regeneration_execution'
                            );
                        } else {
                            assert.equal(
                                manifest.recommended_next_step,
                                'Phase 5.21L2V3Z: enriched target regeneration planning'
                            );
                            assert.equal(manifest.next_required_step, 'enriched_target_regeneration_planning');
                        }
                    } else {
                        assert.equal(
                            manifest.recommended_next_step,
                            'Phase 5.21L2V3Y: controlled no-write source inventory acquisition execution'
                        );
                        assert.equal(
                            manifest.next_required_step,
                            'controlled_no_write_source_inventory_acquisition_execution'
                        );
                    }
                } else {
                    assert.equal(
                        manifest.recommended_next_step,
                        'Phase 5.21L2V3X: controlled no-write source inventory acquisition planning'
                    );
                    assert.equal(
                        manifest.next_required_step,
                        'controlled_no_write_source_inventory_acquisition_planning'
                    );
                }
            } else {
                assert.equal(
                    manifest.recommended_next_step,
                    'Phase 5.21L2V3W: source inventory acquisition path investigation'
                );
                assert.equal(manifest.next_required_step, 'source_inventory_acquisition_path_investigation');
            }
        } else {
            assert.equal(manifest.recommended_next_step, 'Phase 5.21L2V3V: source inventory enrichment implementation');
            assert.equal(manifest.next_required_step, 'source_inventory_enrichment_implementation');
        }
    } else if (manifest.phase_5_21_l2v3t_investigation_status) {
        assert.equal(
            manifest.phase_5_21_l2v3t_investigation_status,
            'completed_no_write_continued_detail_endpoint_investigation'
        );
        assert.equal(manifest.recommended_next_step, 'Phase 5.21L2V3U: source inventory enrichment planning');
        assert.equal(manifest.next_required_step, 'source_inventory_enrichment_planning');
    } else if (manifest.phase_5_21_l2v3s_feasibility_status) {
        assert.equal(
            manifest.phase_5_21_l2v3s_feasibility_status,
            'completed_no_write_detail_api_endpoint_feasibility_verification'
        );
        assert.equal(manifest.recommended_next_step, 'Phase 5.21L2V3T: continued detail endpoint investigation');
        assert.equal(manifest.next_required_step, 'continued_detail_endpoint_investigation');
    } else if (manifest.phase_5_21_l2v3r_planning_status) {
        assert.equal(manifest.recommended_next_step, 'Phase 5.21L2V3S: detail API endpoint feasibility verification');
        assert.equal(manifest.next_required_step, 'detail_api_endpoint_feasibility_verification');
    } else {
        assert.equal(manifest.recommended_next_step, 'Phase 5.21L2V3R: detail URL construction fix planning');
        assert.equal(manifest.next_required_step, 'detail_url_construction_fix_planning');
    }
    assert.match(report, /\|\s*detail_url_construction_suspect_count\s*\|\s*42\s*\|/);
});

test('runContinuedMetadataInvestigation fails closed when manifest gate is not satisfied', () => {
    const invalidManifest = {
        ...syntheticManifest(),
        candidate_targets: syntheticManifest().candidate_targets.slice(0, 49),
    };

    const result = mod.runContinuedMetadataInvestigation({
        manifest: invalidManifest,
        metadataOnlyArtifact: syntheticMetadataOnlyArtifact(),
        writeFiles: false,
    });

    assert.equal(result.ok, false);
    assert.equal(result.status, 2);
    assert.match(result.errors.join('\n'), /candidate_targets must contain 50 entries/i);
});

test('runContinuedMetadataInvestigation fails closed when metadata-only artifact gate is not satisfied', () => {
    const invalidArtifact = {
        ...syntheticMetadataOnlyArtifact(),
        metadata_check_success_count: 41,
    };

    const result = mod.runContinuedMetadataInvestigation({
        manifest: syntheticManifest(),
        metadataOnlyArtifact: invalidArtifact,
        writeFiles: false,
    });

    assert.equal(result.ok, false);
    assert.equal(result.status, 3);
    assert.match(result.errors.join('\n'), /metadata_check_success_count must be 42/i);
});

test('classification counts missing team reverse evidence when team pair is not reversed', () => {
    const metadataOnlyArtifact = syntheticMetadataOnlyArtifact();
    metadataOnlyArtifact.metadata_only_target_summaries = [
        {
            ...metadataOnlyArtifact.metadata_only_target_summaries[0],
            detail_home_team: metadataOnlyArtifact.metadata_only_target_summaries[0].schedule_home_team,
            detail_away_team: metadataOnlyArtifact.metadata_only_target_summaries[0].schedule_away_team,
            observed_page_url_base: '',
        },
    ];

    const result = mod.runContinuedMetadataInvestigation({
        manifest: {
            ...syntheticManifest(),
            candidate_targets: [syntheticManifest().candidate_targets[0]],
        },
        metadataOnlyArtifact: {
            ...metadataOnlyArtifact,
            attempted_unknown_target_count: 42,
            metadata_check_success_count: 42,
        },
        writeFiles: false,
    });

    assert.equal(result.ok, false);
    assert.equal(result.status, 2);
    assert.match(result.errors.join('\n'), /candidate_targets must contain 50 entries/i);

    const entry = mod.buildClassificationEntry({
        target: syntheticManifest().candidate_targets[0],
        metadataEntry: metadataOnlyArtifact.metadata_only_target_summaries[0],
    });
    const counts = mod.buildCounts([entry]);

    assert.equal(entry.team_pair_reversed, false);
    assert.equal(entry.missing_reverse_fixture_evidence, false);
    assert.equal(entry.likely_reverse_fixture_or_slug_reuse, false);
    assert.equal(entry.detail_url_construction_suspect, false);
    assert.equal(counts.missing_team_reverse_evidence_count, 1);
    assert.equal(counts.likely_reverse_fixture_or_slug_reuse_count, 0);
    assert.equal(counts.detail_url_construction_suspect_count, 0);
});
