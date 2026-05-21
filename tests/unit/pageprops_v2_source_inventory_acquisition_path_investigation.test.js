'use strict';
/* eslint-disable max-lines -- L2V3W source inventory acquisition path safety contract is audited together. */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const Module = require('node:module');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(
    PROJECT_ROOT,
    'scripts/ops/pageprops_v2_source_inventory_acquisition_path_investigation.js'
);
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

function candidate(index, overrides = {}) {
    const externalId = String(9000001 + index);
    return {
        target_id: `batch:53_20252026_${externalId}`,
        batch_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        source: 'fotmob',
        route: 'html_hydration',
        source_inventory_route: 'source_inventory',
        raw_data_version: 'fotmob_pageprops_v2',
        hash_strategy: 'stable_pageprops_payload_v1',
        match_id: `53_20252026_${externalId}`,
        external_id: externalId,
        source_url: null,
        source_path: 'l1_api_data_leagues',
        source_page_url: null,
        source_page_url_base: null,
        source_url_fragment_external_id: null,
        source_slug: null,
        source_route_code: null,
        schedule_external_id: externalId,
        schedule_date: '2025-08-15T18:45:00.000Z',
        schedule_home_team: `Home ${index}`,
        schedule_away_team: `Away ${index}`,
        source_inventory_record_key: null,
        source_inventory_generated_at: 'unknown',
        identity_evidence_status: 'missing',
        league_id: 53,
        league_name: 'Ligue 1',
        season: '2025/2026',
        home_team: `Home ${index}`,
        away_team: `Away ${index}`,
        kickoff_time: '2025-08-15T18:45:00.000Z',
        match_date: '2025-08-15T18:45:00.000Z',
        status: 'finished',
        preflight_status: 'hash_baseline_ready',
        baseline_hash: 'c0365494bedfad7f49c59db649dc52d45bd364e7991f518261085349bebd530b',
        write_status: 'not_authorized',
        ...overrides,
    };
}

function syntheticManifest(overrides = {}) {
    return {
        batch_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        source: 'fotmob',
        route: 'html_hydration',
        raw_data_version: 'fotmob_pageprops_v2',
        hash_strategy: 'stable_pageprops_payload_v1',
        league: {
            league_id: 53,
            league_name: 'Ligue 1',
            season: '2025/2026',
        },
        source_inventory_result: {
            route_used: 'source_inventory',
            generated_url: 'https://www.fotmob.com/api/data/leagues?id=53&season=20252026',
            request_count: 1,
            no_full_body_printed: true,
            no_full_body_saved: true,
            no_full_json_printed: true,
            no_full_json_saved: true,
        },
        target_manifest_schema: [{ field: 'target_id', required_for_future_target: true }],
        candidate_targets: Array.from({ length: 50 }, (_, index) => candidate(index)),
        next_required_step: 'source_inventory_acquisition_path_investigation',
        recommended_next_step: 'Phase 5.21L2V3W: source inventory acquisition path investigation',
        raw_write_ready_for_execution: false,
        accepted_mapping_count: 0,
        requires_separate_identity_mapping_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        ...overrides,
    };
}

function syntheticL2V3VArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3V',
        artifact_status: 'completed_no_write_source_inventory_enrichment_implementation',
        raw_write_ready_for_execution: false,
        accepted_mapping_count: 0,
        candidate_targets_checked: 50,
        candidate_targets_with_source_page_url: 0,
        candidate_targets_with_source_page_url_base: 0,
        candidate_targets_with_source_url_fragment_external_id: 0,
        candidate_targets_with_source_inventory_record_key: 0,
        identity_evidence_missing_count: 50,
        raw_write_blocked_count: 50,
        next_required_step: 'source_inventory_acquisition_path_investigation',
        ...overrides,
    };
}

function syntheticL2V3UArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3U',
        raw_write_ready_for_execution: false,
        accepted_mapping_count: 0,
        missing_source_page_url_count: 50,
        missing_page_url_base_count: 50,
        missing_url_fragment_external_id_count: 50,
        missing_source_record_key_count: 50,
        ...overrides,
    };
}

function syntheticL2V3TArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3T',
        previous_endpoint_status: 'blocked_http_403',
        precise_detail_endpoint_found: 'unknown',
        raw_write_ready_for_execution: false,
        accepted_mapping_count: 0,
        ...overrides,
    };
}

function syntheticL2V3RArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3R',
        uses_source_inventory_page_url: false,
        raw_write_ready_for_execution: false,
        accepted_mapping_count: 0,
        ...overrides,
    };
}

function sourceTextByPath() {
    return {
        'src/infrastructure/services/FotMobSourceInventoryAdapter.js':
            'pickSourcePageUrl pageUrl matchUrl href source_page_url_base source_url_fragment_external_id source_inventory_record_key',
        'scripts/ops/single_league_target_discovery_source_inventory_preflight.js':
            'source_page_url pageUrl source_inventory_record_key identity_evidence_status',
        'scripts/ops/single_league_small_batch_target_manifest_plan.js':
            'source_page_url source_inventory_record_key identity_evidence_status',
        'scripts/ops/pageprops_v2_source_inventory_enrichment_apply.js':
            'source_page_url source_inventory_record_key identity_evidence_status',
        'scripts/ops/pageprops_v2_source_inventory_enrichment_plan.js':
            'source_page_url source_inventory_record_key identity_evidence_status',
        'scripts/ops/l1_discovery_safe_preview.js': 'safe preview source inventory no write',
        'scripts/ops/fixture_harvester_l1.js': 'fixture harvest read-only audit',
        'src/infrastructure/services/DiscoveryParser.js': 'parse fixtures',
        'src/infrastructure/services/L1ConfigManager.js': 'buildLeagueApiUrl',
        'tests/unit/single_league_target_discovery_source_inventory_preflight.test.js':
            'source_page_url source_inventory_record_key',
        'tests/unit/FotMobSourceInventoryAdapter.test.js': 'pageUrl source_inventory_record_key',
    };
}

function buildSyntheticRunResult(overrides = {}) {
    return mod.runSourceInventoryAcquisitionPathInvestigation({
        manifest: syntheticManifest(),
        l2v3vArtifact: syntheticL2V3VArtifact(),
        l2v3uArtifact: syntheticL2V3UArtifact(),
        l2v3tArtifact: syntheticL2V3TArtifact(),
        l2v3rArtifact: syntheticL2V3RArtifact(),
        sourceTextByPath: sourceTextByPath(),
        writeFiles: false,
        ...overrides,
    });
}

function installImportGuard(t) {
    const originalLoad = Module._load;
    Module._load = function patchedLoad(request, parent, isMain) {
        if (
            /pg|http|https|child_process|playwright|puppeteer|ProductionHarvester|odds_harvest_pipeline/i.test(request)
        ) {
            throw new Error(`blocked import: ${request}`);
        }
        return originalLoad.call(this, request, parent, isMain);
    };
    t.after(() => {
        Module._load = originalLoad;
    });
}

test('L2V3W artifact records no-write source inventory acquisition path investigation', () => {
    const result = buildSyntheticRunResult();
    assert.equal(result.ok, true);

    const artifact = result.artifact;
    const manifest = result.updated_manifest;

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3W');
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
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(manifest.phase_5_21_l2v3w_investigation_status, artifact.artifact_status);
    assert.equal(manifest.accepted_mapping_count, 0);
    assert.equal(manifest.raw_write_ready_for_execution, false);
});

test('current source-controlled candidates are not retroactively enrichable', () => {
    const result = buildSyntheticRunResult();
    const artifact = result.artifact;

    assert.equal(artifact.current_candidate_url_evidence_counts.target_count, 50);
    assert.equal(artifact.current_candidate_url_evidence_counts.source_page_url_count, 0);
    assert.equal(artifact.current_candidate_url_evidence_counts.source_page_url_base_count, 0);
    assert.equal(artifact.current_candidate_url_evidence_counts.source_url_fragment_external_id_count, 0);
    assert.equal(artifact.current_candidate_url_evidence_counts.source_inventory_record_key_count, 0);
    assert.equal(artifact.current_candidate_url_evidence_counts.identity_evidence_missing_count, 50);
    assert.equal(artifact.source_inventory_contains_url_field, false);
    assert.equal(artifact.current_candidates_retroactively_enrichable, false);
    assert.equal(artifact.requires_source_inventory_regeneration, true);
    assert.equal(artifact.requires_controlled_no_write_source_acquisition, true);
});

test('code paths can capture and propagate source URL evidence when source inventory provides it', () => {
    const result = buildSyntheticRunResult();
    const artifact = result.artifact;

    assert.equal(artifact.analyzed_acquisition_path_count, mod.ACQUISITION_PATHS.length);
    assert.equal(artifact.source_inventory_input_file_count, mod.SOURCE_INVENTORY_INPUT_PATHS.length);
    assert.equal(artifact.adapter_extracts_url_field, true);
    assert.equal(artifact.manifest_builder_propagates_url_field, true);
    assert.equal(artifact.l1_discovery_captures_url_field, true);
    assert.equal(artifact.requires_l1_discovery_rerun, 'unknown');
    assert.equal(artifact.recommended_strategy, 'controlled_no_write_source_inventory_acquisition_planning');
    assert.equal(artifact.strategy_confidence, 'medium');
});

test('source URL evidence presence still does not imply accepted mapping or raw write readiness', () => {
    const manifest = syntheticManifest({
        candidate_targets: [
            candidate(0, {
                source_page_url: '/matches/home-vs-away/abcd12#9000001',
                source_page_url_base: '/matches/home-vs-away/abcd12',
                source_url_fragment_external_id: '9000001',
                source_inventory_record_key: 'l1_api_data_leagues:matches.allMatches.0:9000001',
                identity_evidence_status: 'complete',
            }),
            ...Array.from({ length: 49 }, (_, index) => candidate(index + 1)),
        ],
    });
    const result = buildSyntheticRunResult({ manifest });

    assert.equal(result.artifact.source_inventory_contains_url_field, true);
    assert.equal(result.artifact.current_candidates_retroactively_enrichable, true);
    assert.equal(result.artifact.accepted_mapping_count, 0);
    assert.equal(result.artifact.raw_write_ready_for_execution, false);
    assert.equal(result.artifact.safety_contract.acquisition_investigation_result_is_not_accepted_mapping, true);
    assert.equal(result.artifact.safety_contract.acquisition_investigation_result_is_not_raw_write_authorization, true);
});

test('updated manifest is still rejected by the raw write runner gate', () => {
    const result = buildSyntheticRunResult();
    const gate = rawWrite.validateManifestGate(result.updated_manifest);

    assert.equal(gate.ok, false);
    assert.match(gate.errors.join('\n'), /required_next_step|write_execution_status|raw_match_data_write_status/i);
});

test('outputs avoid full raw data pageProps and source body payloads', () => {
    const result = buildSyntheticRunResult();
    const texts = [JSON.stringify(result.artifact), result.report, JSON.stringify(result.updated_manifest)];

    for (const text of texts) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
        assert.equal(text.includes('"source_body":'), false);
        assert.equal(text.includes('"full_json":'), false);
    }
});

test('helper does not import network, DB, browser, proxy, odds, or harvest modules', t => {
    installImportGuard(t);
    const loaded = loadFreshModule();
    assert.equal(typeof loaded.runSourceInventoryAcquisitionPathInvestigation, 'function');
});

test('runSourceInventoryAcquisitionPathInvestigation can write outputs to explicit temp paths', () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'l2v3w-acquisition-path-'));
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
        assert.equal(JSON.parse(fs.readFileSync(artifactPath, 'utf8')).proposal_phase, 'Phase 5.21L2V3W');
        assert.match(fs.readFileSync(reportPath, 'utf8'), /acquisition investigation result is not accepted mapping/i);
        assert.equal(JSON.parse(fs.readFileSync(manifestPath, 'utf8')).raw_write_ready_for_execution, false);
    } finally {
        fs.rmSync(tmpDir, { recursive: true, force: true });
    }
});

test('CLI parsing covers help, unknowns, and write-files option', () => {
    const parsed = mod.parseArgs(['--write-files=false', '--mystery', 'positional', '--h']);
    const splitParsed = mod.parseArgs(['--write-files', 'maybe']);
    const invalid = mod.validateCliOptions({ unknown: ['mystery'] });

    assert.equal(parsed.writeFiles, false);
    assert.equal(parsed.help, true);
    assert.deepEqual(parsed.unknown, ['mystery', 'positional']);
    assert.equal(splitParsed.writeFiles, true);
    assert.equal(invalid.ok, false);
    assert.match(invalid.errors.join('\n'), /unknown arguments/);
});

test('runCli covers help, invalid options, and repository no-write success', () => {
    let helpOutput = '';
    let invalidOutput = '';
    let successOutput = '';

    const helpStatus = mod.runCli(['--help'], { stdout: text => (helpOutput += text) });
    const invalidStatus = mod.runCli(['--unknown'], { stdout: text => (invalidOutput += text) });
    const successStatus = mod.runCli(['--write-files=false'], { stdout: text => (successOutput += text) });

    assert.equal(helpStatus, 0);
    assert.match(helpOutput, /Usage:/);
    assert.equal(invalidStatus, 2);
    assert.match(invalidOutput, /unknown arguments/);
    assert.equal(successStatus, 0);
    assert.match(successOutput, /Phase 5.21L2V3W/);
    assert.match(successOutput, /raw_write_ready_for_execution/);
});

test('validateInputs fails closed on unsafe manifest and L2V3V states', () => {
    const invalidManifest = mod.validateInputs(
        syntheticManifest({
            next_required_step: 'raw_write_retry',
            raw_write_ready_for_execution: true,
            accepted_mapping_count: 1,
        }),
        syntheticL2V3VArtifact()
    );
    const invalidV = mod.validateInputs(
        syntheticManifest(),
        syntheticL2V3VArtifact({
            proposal_phase: 'Phase 5.21L2V3U',
            raw_write_ready_for_execution: true,
            accepted_mapping_count: 1,
            identity_evidence_missing_count: 49,
        })
    );

    assert.equal(invalidManifest.ok, false);
    assert.match(invalidManifest.errors.join('\n'), /next_required_step/);
    assert.match(invalidManifest.errors.join('\n'), /raw_write_ready_for_execution/);
    assert.match(invalidManifest.errors.join('\n'), /accepted_mapping_count/);
    assert.equal(invalidV.ok, false);
    assert.match(invalidV.errors.join('\n'), /L2V3V artifact/);
    assert.match(invalidV.errors.join('\n'), /raw_write_ready_for_execution/);
    assert.match(invalidV.errors.join('\n'), /accepted_mapping_count/);
    assert.match(invalidV.errors.join('\n'), /identity_evidence_missing_count/);
});

test('repository L2V3W artifacts preserve investigation-only safety when generated', () => {
    const artifactPath =
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.source_inventory_acquisition_path_investigation.phase521l2v3w.json';
    if (!fs.existsSync(path.join(PROJECT_ROOT, artifactPath))) {
        return;
    }

    const manifest = readJson('docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json');
    const artifact = readJson(artifactPath);
    const report = readText('docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3W.md');

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3W');
    assert.equal(artifact.no_write, true);
    assert.equal(artifact.live_source_check_performed, false);
    assert.equal(artifact.network_request_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.current_candidates_retroactively_enrichable, false);
    assert.equal(artifact.requires_controlled_no_write_source_acquisition, true);
    assert.equal(manifest.phase_5_21_l2v3w_investigation_status, artifact.artifact_status);
    assert.equal(manifest.raw_write_ready_for_execution, false);
    assert.equal(manifest.accepted_mapping_count, 0);
    assert.match(report, /acquisition investigation result is not raw write authorization/i);
});
