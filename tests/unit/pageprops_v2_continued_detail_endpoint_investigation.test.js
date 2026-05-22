'use strict';
/* eslint-disable max-lines -- L2V3T safety contract is intentionally audited together. */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_continued_detail_endpoint_investigation.js');
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
        next_required_step: 'continued_detail_endpoint_investigation',
        raw_write_ready_for_execution: false,
        accepted_mapping_count: 0,
        requires_separate_identity_mapping_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        phase_5_21_l2v3s_feasibility_status: 'completed_no_write_detail_api_endpoint_feasibility_verification',
    };
}

function syntheticL2V3QArtifact() {
    return {
        proposal_phase: 'Phase 5.21L2V3Q',
        missing_pageurl_base_count: 42,
        detail_url_construction_suspect_count: 42,
        route_target_regeneration_needed_count: 0,
    };
}

function syntheticL2V3RArtifact() {
    return {
        proposal_phase: 'Phase 5.21L2V3R',
        current_url_strategy: 'fotmob_match_external_id_route',
        uses_match_external_id_route: true,
        uses_source_inventory_page_url: false,
        slug_reuse_risk: true,
        source_inventory_evidence: {
            source_inventory_route_used: 'source_inventory',
            shared_page_url_base_pair_count: 8,
            all_pairs_share_page_url_base: true,
        },
    };
}

function syntheticL2V3SArtifact() {
    return {
        proposal_phase: 'Phase 5.21L2V3S',
        controlled_live_check_performed: true,
        block_or_captcha_count: 1,
        precise_detail_endpoint_found: 'unknown',
        endpoint_avoids_slug_reuse: 'unknown',
        raw_write_ready_for_execution: false,
        accepted_mapping_count: 0,
        controlled_endpoint_check: {
            stop_reason: 'CONTROLLED_BLOCK_SIGNAL:HTTP_403',
            checked_targets: [
                {
                    target_category: 'known_reverse_fixture_or_slug_reuse',
                    requested_schedule_external_id: '4830460',
                    match_id: '53_20252026_4830460',
                    team_safe_summary: {
                        requested: 'Brest-Lille',
                    },
                    schedule_detail_date_safe_summary: {
                        requested_date: '2025-08-17',
                    },
                    status_safe_summary: {
                        requested_status: 'finished',
                    },
                },
            ],
        },
    };
}

function sourceTextByPath() {
    return {
        'scripts/ops/single_league_target_discovery_source_inventory_preflight.js':
            'match?.pageUrl match?.matchUrl match?.url match?.href',
        'scripts/ops/pageprops_v2_target_source_inventory_reconciliation_plan.js':
            'page_url_base page_url_anchor source_inventory_page_url_base',
        'src/infrastructure/services/FotMobRawDetailFetcher.js': 'buildFotMobMatchUrl pageUrlBase',
        'src/infrastructure/network/FotMobApiClient.js': '/api/data/matchDetails fetchMatchDetails',
        'scripts/ops/l2_raw_detail_preview.js': 'api/data/matchDetails api_match_details alternate_route',
        'src/infrastructure/services/FotMobDetailRouteSelector.js': 'html_hydration api_match_details alternate_route',
        'src/infrastructure/services/MarathonService.js': 'api/data/matchDetails api/matchDetails',
        'src/parsers/fotmob/NextDataParser.js': '__NEXT_DATA__ props.pageProps',
        'docs/_reports/RAW_STORAGE_STRATEGY_REVISION_PLANNING_PHASE5_21L2C.md': 'buildId',
        'tests/unit/pageprops_v2_no_write_preview.test.js': 'buildId',
        'tests/unit/html_hydration_source_fidelity_live_compare.test.js': 'buildId',
    };
}

function response(body, status = 200, contentType = 'application/json') {
    return {
        status,
        url: 'https://www.fotmob.com/api/data/matchDetails?matchId=4830460',
        headers: {
            get(name) {
                return String(name).toLowerCase() === 'content-type' ? contentType : '';
            },
        },
        async text() {
            return body;
        },
    };
}

function fakeJsonBody({ id = '4830460', home = 'Brest', away = 'Lille', date = '2025-08-17T00:00:00.000Z' } = {}) {
    return JSON.stringify({
        general: {
            matchId: id,
            homeTeam: { name: home },
            awayTeam: { name: away },
            matchTimeUTC: date,
            status: { type: 'finished' },
        },
        header: {
            teams: [{ name: home }, { name: away }],
        },
        content: {
            matchFacts: {
                matchId: id,
            },
        },
    });
}

function buildSyntheticRunResult(overrides = {}) {
    return mod.runContinuedDetailEndpointInvestigation({
        manifest: syntheticManifest(),
        l2v3qArtifact: syntheticL2V3QArtifact(),
        l2v3rArtifact: syntheticL2V3RArtifact(),
        l2v3sArtifact: syntheticL2V3SArtifact(),
        sourceTextByPath: sourceTextByPath(),
        writeFiles: false,
        controlledLiveCheck: false,
        networkAuthorization: false,
        ...overrides,
    });
}

test('L2V3T artifact records a no-write continued endpoint investigation phase', async () => {
    const result = await buildSyntheticRunResult();
    assert.equal(result.ok, true);

    const artifact = result.artifact;
    const manifest = result.updated_manifest;

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3T');
    assert.equal(artifact.no_write, true);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.matches_external_id_modified, false);
    assert.equal(artifact.identity_mapping_acceptance_performed, false);
    assert.equal(artifact.baseline_acceptance_performed, false);
    assert.equal(artifact.raw_write_retry_performed, false);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.controlled_live_check_performed, false);
    assert.equal(artifact.previous_endpoint_status, 'blocked_http_403');

    assert.equal(manifest.phase_5_21_l2v3t_investigation_status, artifact.artifact_status);
    assert.equal(manifest.continued_detail_endpoint_investigation_status, artifact.artifact_status);
    assert.equal(manifest.raw_write_ready_for_execution, false);
    assert.equal(manifest.accepted_mapping_count, 0);
});

test('source-controlled endpoint hints recommend source inventory enrichment planning', async () => {
    const result = await buildSyntheticRunResult();
    const artifact = result.artifact;
    const publicApi = artifact.endpoint_hints.find(item => item.endpoint_hint_key === 'api_data_match_details');
    const sourceInventory = artifact.endpoint_hints.find(
        item => item.endpoint_hint_key === 'source_inventory_page_url_slug_route'
    );
    const buildData = artifact.endpoint_hints.find(item => item.endpoint_hint_key === 'nextjs_build_data_route');

    assert.equal(artifact.analyzed_endpoint_hint_count, 6);
    assert.equal(artifact.new_endpoint_candidate_count, 0);
    assert.equal(artifact.precise_detail_endpoint_found, 'unknown');
    assert.equal(artifact.endpoint_avoids_slug_reuse, 'unknown');
    assert.equal(publicApi.safe_conclusion, 'public_no_write_access_still_blocked_by_http_403');
    assert.match(sourceInventory.safe_conclusion, /current_manifest_does_not_store_them/);
    assert.equal(buildData.code_evidence_found, false);
    assert.equal(buildData.docs_or_tests_only, true);
    assert.equal(artifact.evidence_summary.source_inventory_enrichment_required, true);
    assert.equal(artifact.evidence_summary.build_data_route_executable_builder_found, false);
    assert.equal(artifact.recommended_strategy, 'Phase 5.21L2V3U: source inventory enrichment planning');
    assert.equal(artifact.strategy_confidence, 'medium');
    assert.equal(artifact.requires_followup_implementation, false);
    assert.equal(artifact.recommended_next_step, 'Phase 5.21L2V3U: source inventory enrichment planning');
    assert.equal(artifact.next_required_step, 'source_inventory_enrichment_planning');
});

test('controlled 403 recheck remains blocked and does not save payload or write DB', async () => {
    const result = await buildSyntheticRunResult({
        controlledLiveCheck: true,
        networkAuthorization: true,
        maxTargets: 1,
        fetchFn: async () => response('{"code":403,"error":"Forbidden"}', 403),
    });
    const artifact = result.artifact;
    const target = artifact.controlled_endpoint_check.checked_targets[0];

    assert.equal(artifact.controlled_live_check_performed, true);
    assert.equal(artifact.checked_target_count, 1);
    assert.equal(artifact.block_or_captcha_count, 1);
    assert.equal(artifact.precise_detail_endpoint_found, 'unknown');
    assert.equal(target.full_payload_saved, false);
    assert.equal(target.full_payload_printed, false);
    assert.equal(target.db_write_performed, false);
    assert.equal(target.raw_insert_performed, false);
    assert.match(target.safe_error_summary, /CONTROLLED_BLOCK_SIGNAL/);
    assert.equal(artifact.recommended_next_step, 'Phase 5.21L2V3U: source inventory enrichment planning');
});

test('optional safe success still cannot authorize raw write or accepted mapping', async () => {
    const result = await buildSyntheticRunResult({
        controlledLiveCheck: true,
        networkAuthorization: true,
        maxTargets: 1,
        fetchFn: async () => response(fakeJsonBody()),
    });
    const artifact = result.artifact;

    assert.equal(artifact.controlled_live_check_performed, true);
    assert.equal(artifact.checked_target_count, 1);
    assert.equal(artifact.precise_detail_endpoint_found, true);
    assert.equal(artifact.endpoint_avoids_slug_reuse, true);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.recommended_next_step, 'Phase 5.21L2V3U: precise detail endpoint strategy implementation');
    assert.equal(artifact.next_required_step, 'precise_detail_endpoint_strategy_implementation');
    assert.equal(artifact.safety_contract.endpoint_investigation_result_is_not_raw_write_authorization, true);
});

test('updated manifest is still rejected by the raw write runner gate', async () => {
    const result = await buildSyntheticRunResult();
    const gate = rawWrite.validateManifestGate(result.updated_manifest);

    assert.equal(gate.ok, false);
    assert.match(gate.errors.join('\n'), /required_next_step|write_execution_status|raw_match_data_write_status/i);
});

test('CLI parsing covers unknowns, help, and max-target validation', () => {
    const parsed = mod.parseArgs([
        '--controlled-live-check',
        'yes',
        '--network_authorization=no',
        '--max-targets',
        '1',
        '--write-files=false',
        '--mystery',
        '--h',
    ]);
    const invalid = mod.validateCliOptions({
        controlledLiveCheck: true,
        networkAuthorization: false,
        maxTargets: 2,
        unknown: ['mystery'],
    });

    assert.equal(parsed.controlledLiveCheck, true);
    assert.equal(parsed.networkAuthorization, false);
    assert.equal(parsed.maxTargets, 1);
    assert.equal(parsed.writeFiles, false);
    assert.equal(parsed.help, true);
    assert.deepEqual(parsed.unknown, ['mystery']);
    assert.equal(invalid.ok, false);
    assert.match(invalid.errors.join('\n'), /network-authorization/);
    assert.match(invalid.errors.join('\n'), /max-targets/);
});

test('L2V3T outputs avoid full raw data pageProps and source body payloads', async () => {
    const result = await buildSyntheticRunResult({
        controlledLiveCheck: true,
        networkAuthorization: true,
        maxTargets: 1,
        fetchFn: async () => response(fakeJsonBody()),
    });
    const texts = [JSON.stringify(result.artifact), result.report, JSON.stringify(result.updated_manifest)];

    for (const text of texts) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
        assert.equal(text.includes('"source_body":'), false);
    }
});

test('runContinuedDetailEndpointInvestigation can write outputs to explicit temp paths', async () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'l2v3t-investigation-'));
    const artifactPath = path.join(tmpDir, 'artifact.json');
    const reportPath = path.join(tmpDir, 'report.md');
    const manifestPath = path.join(tmpDir, 'manifest.json');

    try {
        const result = await buildSyntheticRunResult({
            writeFiles: true,
            artifactOutputPath: artifactPath,
            reportOutputPath: reportPath,
            manifestOutputPath: manifestPath,
        });

        assert.equal(result.ok, true);
        assert.equal(JSON.parse(fs.readFileSync(artifactPath, 'utf8')).proposal_phase, 'Phase 5.21L2V3T');
        assert.match(fs.readFileSync(reportPath, 'utf8'), /endpoint investigation result is not an accepted mapping/i);
        assert.equal(JSON.parse(fs.readFileSync(manifestPath, 'utf8')).raw_write_ready_for_execution, false);
    } finally {
        fs.rmSync(tmpDir, { recursive: true, force: true });
    }
});

test('repository L2V3T artifacts preserve no-write investigation semantics when generated', () => {
    const artifactPath =
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.continued_detail_endpoint_investigation.phase521l2v3t.json';
    if (!fs.existsSync(path.join(PROJECT_ROOT, artifactPath))) {
        return;
    }

    const manifest = readJson('docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json');
    const artifact = readJson(artifactPath);
    const report = readText('docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3T.md');

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3T');
    assert.equal(artifact.no_write, true);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.previous_endpoint_status, 'blocked_http_403');
    assert.equal(artifact.recommended_next_step, 'Phase 5.21L2V3U: source inventory enrichment planning');
    assert.equal(manifest.phase_5_21_l2v3t_investigation_status, artifact.artifact_status);
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
                                assert.ok(
                                    [
                                        'Phase 5.21L2V3AC: controlled enriched no-write verification execution',
                                        'Phase 5.21L2V3AD: identity mapping acceptance review planning',
                                        'Phase 5.21L2V3AE: identity mapping acceptance review execution',
                                    ].includes(manifest.recommended_next_step)
                                );
                                assert.ok(
                                    [
                                        'controlled_enriched_no_write_verification_execution',
                                        'identity_mapping_acceptance_review_planning',
                                        'identity_mapping_acceptance_review_execution',
                                    ].includes(manifest.next_required_step)
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
    } else {
        assert.equal(manifest.recommended_next_step, 'Phase 5.21L2V3U: source inventory enrichment planning');
        assert.equal(manifest.next_required_step, 'source_inventory_enrichment_planning');
    }
    assert.match(report, /public_api_match_details_status=public_no_write_access_still_blocked_by_http_403/);
});
