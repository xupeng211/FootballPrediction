'use strict';
/* eslint-disable max-lines -- L2V3R planning safety contract is intentionally audited together. */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_detail_url_construction_fix_plan.js');
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
            source_inventory_route: 'l1_api_data_leagues',
            home_team: `Home ${index}`,
            away_team: `Away ${index}`,
            match_date: '2025-08-15T18:45:00.000Z',
            status: 'finished',
        })),
        next_required_step: 'detail_url_construction_fix_planning',
        recommended_next_step: 'Phase 5.21L2V3R: detail URL construction fix planning',
        raw_write_ready_for_execution: false,
        accepted_mapping_count: 0,
        requires_separate_identity_mapping_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
    };
}

function syntheticL2V3QArtifact() {
    return {
        proposal_phase: 'Phase 5.21L2V3Q',
        no_write: true,
        analyzed_target_count: 42,
        unresolved_large_gap_count: 42,
        likely_reverse_fixture_or_slug_reuse_count: 42,
        detail_url_construction_suspect_count: 42,
        future_review_candidate_count: 0,
        still_blocked_count: 42,
        accepted_mapping_count: 0,
        raw_write_ready_for_execution: false,
    };
}

function sourceTextByPath() {
    return {
        'src/infrastructure/services/FotMobRawDetailFetcher.js':
            'const url = new URL(`/match/${id}`, FOTMOB_BASE_URL); const requestUrl = v.requestUrl || request.url;',
        'scripts/ops/pageprops_v2_metadata_only_detail_check.js': 'const requestUrl = buildFotMobMatchUrl(externalId);',
        'scripts/ops/single_league_small_batch_pageprops_v2_preflight.js':
            'const requestUrl = buildFotMobMatchUrl(target.external_id);',
        'scripts/ops/single_league_pageprops_v2_controlled_write_execute.js':
            'const requestUrl = buildFotMobMatchUrl(target.external_id);',
        'scripts/ops/renewed_pageprops_v2_raw_write_execute.js':
            "const base = require('./single_league_pageprops_v2_controlled_write_execute');",
    };
}

function buildSyntheticRunResult(overrides = {}) {
    return mod.runDetailUrlConstructionFixPlan({
        manifest: syntheticManifest(),
        l2v3qArtifact: syntheticL2V3QArtifact(),
        l2v3pArtifact: { attempted_unknown_target_count: 42 },
        l2v3nArtifact: { accepted_mapping_count: 0 },
        l2v3mArtifact: { accepted_mapping_count: 0 },
        l2v3eReportText:
            'source_inventory_route_used=source_inventory\nshared_page_url_base_pair_count=8\nall_pairs_share_page_url_base=true\nprimary_evidence=source inventory requested/observed pairs share the same pageUrl base and differ only by #external_id anchor\n',
        sourceTextByPath: sourceTextByPath(),
        writeFiles: false,
        ...overrides,
    });
}

test('L2V3R artifact records a no-write detail URL construction planning phase', () => {
    const result = buildSyntheticRunResult();
    assert.equal(result.ok, true);

    const artifact = result.artifact;
    const manifest = result.updated_manifest;

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3R');
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

    assert.equal(manifest.phase_5_21_l2v3r_planning_status, artifact.artifact_status);
    assert.equal(manifest.detail_url_construction_fix_planning_status, artifact.artifact_status);
    assert.equal(manifest.raw_write_ready_for_execution, false);
    assert.equal(manifest.accepted_mapping_count, 0);
});

test('current fetch path analysis identifies match external id route and no source inventory URL usage', () => {
    const result = buildSyntheticRunResult();
    const artifact = result.artifact;

    assert.equal(artifact.analyzed_fetch_paths_count, 5);
    assert.equal(artifact.current_url_strategy, 'fotmob_match_external_id_route');
    assert.equal(artifact.uses_match_external_id_route, true);
    assert.equal(artifact.uses_source_inventory_page_url, false);
    assert.equal(artifact.slug_reuse_risk, true);
    assert.equal(artifact.detail_url_construction_suspect_count, 42);
    assert.equal(artifact.precise_detail_endpoint_found, 'unknown');
    assert.equal(artifact.proposed_fix_strategy.includes('api_match_details_feasibility'), true);
    assert.equal(artifact.fix_confidence, 'medium');
});

test('URL fragment id alone cannot be assumed to reach the server', () => {
    const url = 'https://www.fotmob.com/matches/home-vs-away/abc123#9000001';

    assert.equal(mod.stripHash(url), 'https://www.fotmob.com/matches/home-vs-away/abc123');
    assert.equal(mod.extractFragment(url), '9000001');
    assert.equal(mod.fragmentReachesServer(url), false);

    const result = buildSyntheticRunResult();
    const fragmentRoute = result.artifact.route_candidate_analysis.find(
        item => item.route_candidate === '/matches/{slug}#{externalId}'
    );
    assert.equal(fragmentRoute.fragment_preserved_in_request, true);
    assert.equal(fragmentRoute.fragment_reaches_server, false);
    assert.match(fragmentRoute.risk, /cannot_be_assumed_to_select_server_payload/);
});

test('slug route reuse risk and URL construction suspect remain blocked from acceptance and raw write', () => {
    const result = buildSyntheticRunResult();
    const artifact = result.artifact;

    assert.equal(artifact.safety_contract.detail_url_construction_plan_is_not_accepted_mapping, true);
    assert.equal(artifact.safety_contract.proposed_url_fix_is_not_raw_write_authorization, true);
    assert.equal(artifact.safety_contract.unresolved_url_construction_suspect_blocks_identity_mapping_acceptance, true);
    assert.equal(artifact.safety_contract.unresolved_url_construction_suspect_blocks_raw_write, true);
    assert.equal(artifact.safety_contract.slug_route_reuse_risk_blocks_raw_write, true);
    assert.equal(artifact.safety_contract.fragment_id_alone_is_not_identity_evidence, true);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.raw_write_ready_for_execution, false);
});

test('L2V3R updated manifest is still rejected by the raw write runner gate', () => {
    const result = buildSyntheticRunResult();
    const gate = rawWrite.validateManifestGate(result.updated_manifest);

    assert.equal(gate.ok, false);
    assert.match(gate.errors.join('\n'), /required_next_step|write_execution_status|raw_match_data_write_status/i);
});

test('L2V3R artifacts avoid full raw_data pageProps and source body payloads', () => {
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

test('runDetailUrlConstructionFixPlan fails closed when L2V3Q gate is not satisfied', () => {
    const invalidArtifact = {
        ...syntheticL2V3QArtifact(),
        detail_url_construction_suspect_count: 41,
    };
    const result = buildSyntheticRunResult({ l2v3qArtifact: invalidArtifact });

    assert.equal(result.ok, false);
    assert.equal(result.status, 2);
    assert.match(result.errors.join('\n'), /detail_url_construction_suspect_count must be 42/i);
});

test('validation covers manifest safety failures and idempotent completed L2V3R input', () => {
    const invalidNext = mod.validateInputs(
        { ...syntheticManifest(), next_required_step: 'raw_write_retry' },
        syntheticL2V3QArtifact()
    );
    assert.equal(invalidNext.ok, false);
    assert.match(invalidNext.errors.join('\n'), /next_required_step/);

    const invalidReady = mod.validateInputs(
        { ...syntheticManifest(), raw_write_ready_for_execution: true },
        syntheticL2V3QArtifact()
    );
    assert.equal(invalidReady.ok, false);
    assert.match(invalidReady.errors.join('\n'), /raw_write_ready_for_execution/);

    const invalidQReady = mod.validateInputs(syntheticManifest(), {
        ...syntheticL2V3QArtifact(),
        raw_write_ready_for_execution: true,
    });
    assert.equal(invalidQReady.ok, false);
    assert.match(invalidQReady.errors.join('\n'), /L2V3Q raw_write_ready_for_execution/);

    const invalidAccepted = mod.validateInputs(syntheticManifest(), {
        ...syntheticL2V3QArtifact(),
        accepted_mapping_count: 1,
    });
    assert.equal(invalidAccepted.ok, false);
    assert.match(invalidAccepted.errors.join('\n'), /accepted_mapping_count/);

    const completedManifest = {
        ...syntheticManifest(),
        next_required_step: 'detail_api_endpoint_feasibility_verification',
        phase_5_21_l2v3r_planning_status: 'completed_no_write_detail_url_construction_fix_planning',
    };
    const completedGate = mod.validateInputs(completedManifest, syntheticL2V3QArtifact());
    assert.equal(completedGate.ok, true);
});

test('source file analysis and URL helpers cover fallback branches', () => {
    const analysis = mod.analyzeSourceFiles(
        [
            {
                key: 'custom',
                path: 'custom.js',
                routePattern: 'buildFotMobMatchUrl(externalId)',
                sourceInventoryPattern: 'buildDetailRequestFromSourceInventoryPageUrl(',
            },
        ],
        {
            sourceTextByPath: {
                'custom.js':
                    'const requestUrl = buildFotMobMatchUrl(externalId); buildDetailRequestFromSourceInventoryPageUrl(target);',
            },
        }
    );
    const summary = mod.buildFetchPathSummary(analysis);

    assert.equal(analysis[0].uses_match_external_id_route, true);
    assert.equal(analysis[0].uses_source_inventory_page_url, true);
    assert.equal(summary.uses_source_inventory_page_url, true);
    assert.equal(summary.fetch_paths_using_source_inventory_page_url_count, 1);
    assert.equal(mod.stripHash(''), null);
    assert.equal(mod.extractFragment('https://www.fotmob.com/matches/foo'), null);
    assert.equal(mod.fragmentReachesServer('https://www.fotmob.com/matches/foo'), false);
    assert.equal(mod.extractL2V3ESourceInventoryEvidence('').all_pairs_share_page_url_base, false);
});

test('manifest URL summary and fetch path summary cover empty and populated branches', () => {
    const emptyManifestUrlSummary = mod.summarizeManifestUrlFields({});
    const manifestUrlSummary = mod.summarizeManifestUrlFields({
        candidate_targets: [
            {
                external_id: '1',
                page_url: '/matches/a#1',
                pageUrl: '/matches/a#1',
                page_url_base: '/matches/a',
                source_inventory_page_url_base: '/matches/a',
                manifest_page_url_base: '/matches/a',
                source_inventory_record_key: 'fixtures#1',
                source_inventory_route: 'l1_api_data_leagues',
                source_url: 'https://www.fotmob.com/api/data/leagues?id=53',
            },
            {},
        ],
    });
    const emptyFetchSummary = mod.buildFetchPathSummary([]);
    const fullEvidence = mod.extractL2V3ESourceInventoryEvidence(
        [
            'source_inventory_route_used=source_inventory',
            'source_inventory_request_url=https://www.fotmob.com/api/data/leagues?id=53&season=20252026',
            'shared_page_url_base_pair_count=8',
            'all_pairs_share_page_url_base=true',
            'primary_evidence=source inventory requested/observed pairs share the same pageUrl base',
        ].join('\n')
    );
    const realSourceAnalysis = mod.analyzeSourceFiles([
        {
            key: 'fotmob_raw_detail_fetcher',
            path: 'src/infrastructure/services/FotMobRawDetailFetcher.js',
            routePattern: 'new URL(`/match/${id}`, FOTMOB_BASE_URL)',
            sourceInventoryPattern: 'buildDetailRequestFromSourceInventoryPageUrl(',
        },
    ]);

    assert.equal(emptyManifestUrlSummary.candidate_targets_count, 0);
    assert.equal(manifestUrlSummary.candidate_targets_count, 2);
    assert.equal(manifestUrlSummary.page_url_count, 1);
    assert.equal(manifestUrlSummary.source_inventory_record_key_count, 1);
    assert.equal(emptyFetchSummary.analyzed_fetch_paths_count, 0);
    assert.equal(emptyFetchSummary.uses_match_external_id_route, false);
    assert.equal(emptyFetchSummary.uses_source_inventory_page_url, false);
    assert.equal(realSourceAnalysis[0].uses_match_external_id_route, true);
    assert.equal(realSourceAnalysis[0].supports_request_url_override, true);
    assert.equal(fullEvidence.source_inventory_route_used, 'source_inventory');
    assert.equal(fullEvidence.shared_page_url_base_pair_count, 8);
    assert.equal(fullEvidence.all_pairs_share_page_url_base, true);
    assert.match(fullEvidence.primary_evidence, /source inventory/);
});

test('buildArtifact marks slug reuse risk false when no detail URL suspects exist', () => {
    const artifact = mod.buildArtifact({
        manifest: syntheticManifest(),
        l2v3qArtifact: {
            ...syntheticL2V3QArtifact(),
            detail_url_construction_suspect_count: 0,
        },
        l2v3pArtifact: { attempted_unknown_target_count: 42 },
        l2v3nArtifact: { accepted_mapping_count: 0 },
        l2v3mArtifact: { accepted_mapping_count: 0 },
        l2v3eReportText: '',
        sourceFileAnalysis: [],
    });

    assert.equal(artifact.detail_url_construction_suspect_count, 0);
    assert.equal(artifact.slug_reuse_risk, false);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.accepted_mapping_count, 0);
});

test('runDetailUrlConstructionFixPlan can write planning outputs to explicit temp paths', () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'l2v3r-plan-'));
    const artifactPath = path.join(tmpDir, 'artifact.json');
    const reportPath = path.join(tmpDir, 'report.md');
    const manifestPath = path.join(tmpDir, 'manifest.json');

    try {
        const result = buildSyntheticRunResult({
            writeFiles: true,
            artifactOutputPath: artifactPath,
            reportOutputPath: reportPath,
            manifestOutputPath: manifestPath,
        });

        assert.equal(result.ok, true);
        assert.equal(JSON.parse(fs.readFileSync(artifactPath, 'utf8')).proposal_phase, 'Phase 5.21L2V3R');
        assert.match(fs.readFileSync(reportPath, 'utf8'), /detail URL construction plan is not an accepted mapping/);
        assert.equal(JSON.parse(fs.readFileSync(manifestPath, 'utf8')).raw_write_ready_for_execution, false);
    } finally {
        fs.rmSync(tmpDir, { recursive: true, force: true });
    }
});

test('repository L2V3R artifacts preserve planning-only and blocking semantics', () => {
    const manifest = readJson('docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json');
    const artifact = readJson(
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.detail_url_construction_fix_plan.phase521l2v3r.json'
    );
    const report = readText('docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3R.md');

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3R');
    assert.equal(artifact.no_write, true);
    assert.equal(artifact.network_request_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.current_url_strategy, 'fotmob_match_external_id_route');
    assert.equal(artifact.slug_reuse_risk, true);
    assert.equal(artifact.fragment_reaches_server, false);
    assert.equal(artifact.detail_url_construction_suspect_count, 42);

    assert.equal(manifest.phase_5_21_l2v3r_planning_status, 'completed_no_write_detail_url_construction_fix_planning');
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
                                        'Phase 5.21L2V3AF: baseline acceptance planning',
                                        'Phase 5.21L2V3AG: baseline acceptance execution',
                                        'Phase 5.21L2V3AH: final DB-write authorization planning',
                                        'Phase 5.21L2V3AI: final DB-write authorization execution',
                                        'Phase 5.21L2V3AJ: controlled raw_match_data write execution planning',
                                        'Phase 5.21L2V3AK: controlled raw_match_data write execution',
                                        'Phase 5.21L2V3AK: controlled raw write execution blocker resolution',
                                        'Phase 5.21L2V3AK: continued controlled raw write planning',
                                        'Phase 5.21L2V3AL: controlled payload source declaration planning',
                                        'Phase 5.21L2V3AM: controlled payload source declaration execution',
                                        'Phase 5.21L2V3AN: controlled no-write payload recapture planning',
                                        'Phase 5.21L2V3AO: controlled no-write payload recapture execution',
                                        'Phase 5.21L2V3AP: no-write payload recapture blocker investigation',
                                        'Phase 5.21L2V3AP: partial recapture review planning',
                                        'Phase 5.21L2V3AP: controlled recapture result verification planning',
                                        'Phase 5.21L2V3AQ: accepted mapping and baseline contradiction review planning',
                                        'Phase 5.21L2V3AQ: recapture runner identity input contract fix planning',
                                        'Phase 5.21L2V3AQ: continued no-write recapture blocker investigation',
                                    ].includes(manifest.recommended_next_step)
                                );
                                assert.ok(
                                    [
                                        'controlled_enriched_no_write_verification_execution',
                                        'identity_mapping_acceptance_review_planning',
                                        'identity_mapping_acceptance_review_execution',
                                        'baseline_acceptance_planning',
                                        'baseline_acceptance_execution',
                                        'final_db_write_authorization_planning',
                                        'final_db_write_authorization_execution',
                                        'controlled_raw_match_data_write_execution_planning',
                                        'controlled_raw_match_data_write_execution',
                                        'controlled_raw_write_execution_blocker_resolution',
                                        'continued_controlled_raw_write_planning',
                                        'controlled_payload_source_declaration_planning',
                                        'controlled_payload_source_declaration_execution',
                                        'controlled_no_write_payload_recapture_planning',
                                        'controlled_no_write_payload_recapture_execution',
                                        'no_write_payload_recapture_blocker_investigation',
                                        'partial_recapture_review_planning',
                                        'controlled_recapture_result_verification_planning',
                                        'accepted_mapping_and_baseline_contradiction_review_planning',
                                        'recapture_runner_identity_input_contract_fix_planning',
                                        'continued_no_write_recapture_blocker_investigation',
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
    } else {
        assert.equal(manifest.recommended_next_step, 'Phase 5.21L2V3S: detail API endpoint feasibility verification');
        assert.equal(manifest.next_required_step, 'detail_api_endpoint_feasibility_verification');
    }
    assert.match(report, /detail_url_construction_suspect_count=42/);
});
