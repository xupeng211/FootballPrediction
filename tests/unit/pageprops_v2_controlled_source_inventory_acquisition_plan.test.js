'use strict';
/* eslint-disable max-lines -- L2V3X planning safety contract is audited together. */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const Module = require('node:module');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_controlled_source_inventory_acquisition_plan.js');
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
        phase_5_21_l2v3w_investigation_status: 'completed_no_write_source_inventory_acquisition_path_investigation',
        source_inventory_acquisition_path_investigation_status:
            'completed_no_write_source_inventory_acquisition_path_investigation',
        next_required_step: 'controlled_no_write_source_inventory_acquisition_planning',
        recommended_next_step: 'Phase 5.21L2V3X: controlled no-write source inventory acquisition planning',
        raw_write_ready_for_execution: false,
        accepted_mapping_count: 0,
        requires_separate_identity_mapping_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        ...overrides,
    };
}

function syntheticL2V3WArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3W',
        artifact_status: 'completed_no_write_source_inventory_acquisition_path_investigation',
        no_write: true,
        live_source_check_performed: false,
        network_request_performed: false,
        db_write_performed: false,
        raw_insert_performed: false,
        matches_write_performed: false,
        source_inventory_contains_url_field: false,
        adapter_extracts_url_field: true,
        manifest_builder_propagates_url_field: true,
        l1_discovery_captures_url_field: true,
        current_candidates_retroactively_enrichable: false,
        requires_source_inventory_regeneration: true,
        requires_controlled_no_write_source_acquisition: true,
        accepted_mapping_count: 0,
        raw_write_ready_for_execution: false,
        recommended_strategy: 'controlled_no_write_source_inventory_acquisition_planning',
        next_required_step: 'controlled_no_write_source_inventory_acquisition_planning',
        ...overrides,
    };
}

function syntheticL2V3VArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3V',
        identity_evidence_missing_count: 50,
        accepted_mapping_count: 0,
        raw_write_ready_for_execution: false,
        ...overrides,
    };
}

function syntheticL2V3UArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3U',
        missing_source_page_url_count: 50,
        accepted_mapping_count: 0,
        raw_write_ready_for_execution: false,
        ...overrides,
    };
}

function buildSyntheticRunResult(overrides = {}) {
    return mod.runControlledSourceInventoryAcquisitionPlan({
        manifest: syntheticManifest(),
        l2v3wArtifact: syntheticL2V3WArtifact(),
        l2v3vArtifact: syntheticL2V3VArtifact(),
        l2v3uArtifact: syntheticL2V3UArtifact(),
        inputAnalysis: mod.INPUT_PATHS.map(item => ({ ...item, exists: true })),
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

test('L2V3X artifact records no-write controlled source inventory acquisition planning', () => {
    const result = buildSyntheticRunResult();
    assert.equal(result.ok, true);

    const artifact = result.artifact;
    const manifest = result.updated_manifest;

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3X');
    assert.equal(artifact.no_write, true);
    assert.equal(artifact.live_fetch_performed, false);
    assert.equal(artifact.source_acquisition_execution_performed, false);
    assert.equal(artifact.network_request_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_insert_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.matches_external_id_modified, false);
    assert.equal(artifact.identity_mapping_acceptance_performed, false);
    assert.equal(artifact.baseline_acceptance_performed, false);
    assert.equal(artifact.raw_write_retry_performed, false);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(manifest.phase_5_21_l2v3x_planning_status, artifact.artifact_status);
    assert.equal(manifest.accepted_mapping_count, 0);
    assert.equal(manifest.raw_write_ready_for_execution, false);
});

test('planned acquisition scope and endpoint remain metadata-only', () => {
    const result = buildSyntheticRunResult();
    const artifact = result.artifact;

    assert.equal(
        artifact.planned_acquisition_scope,
        'ligue1_2025_2026_profile_001_current_50_candidates_metadata_only_source_inventory'
    );
    assert.equal(artifact.planned_source_endpoint, '/api/data/leagues?id=53&season=20252026');
    assert.equal(artifact.planned_target_league_id, 53);
    assert.equal(artifact.planned_target_season, '2025/2026');
    assert.equal(artifact.planned_candidate_scope_count, 50);
    assert.equal(artifact.planned_scope_details.source_inventory_only, true);
    assert.equal(artifact.planned_scope_details.raw_match_data_generation_allowed, false);
});

test('planned metadata-only fields include required source URL identity evidence', () => {
    const result = buildSyntheticRunResult();
    const artifact = result.artifact;
    const fields = new Set(artifact.planned_metadata_fields.map(item => item.field));

    assert.equal(artifact.planned_metadata_field_count, 15);
    assert.equal(fields.has('source_page_url'), true);
    assert.equal(fields.has('source_page_url_base'), true);
    assert.equal(fields.has('source_url_fragment_external_id'), true);
    assert.equal(fields.has('source_inventory_record_key'), true);
    assert.equal(fields.has('source_endpoint_summary'), true);
    assert.equal(fields.has('acquisition_status'), true);
    assert.equal(fields.has('safe_error_summary'), true);
});

test('payload safety and stopping rules are explicit and block unsafe execution paths', () => {
    const result = buildSyntheticRunResult();
    const artifact = result.artifact;

    assert.equal(artifact.payload_safety_rules.includes('do_not_save_full_api_payload'), true);
    assert.equal(artifact.payload_safety_rules.includes('do_not_save_full_pageProps'), true);
    assert.equal(artifact.payload_safety_rules.includes('do_not_save_full_raw_data'), true);
    assert.equal(artifact.payload_safety_rules.includes('do_not_save_full_html_or_source_body'), true);
    assert.equal(artifact.payload_safety_rules.includes('do_not_record_cookies_tokens_headers'), true);
    assert.equal(artifact.stopping_rules.includes('http_block_or_captcha_signal'), true);
    assert.equal(artifact.stopping_rules.includes('rate_limit_signal'), true);
    assert.equal(artifact.stopping_rules.includes('unexpected_schema_drift'), true);
    assert.equal(artifact.stopping_rules.includes('any_attempted_write_path'), true);
});

test('acquisition plan is not accepted mapping or raw write authorization', () => {
    const result = buildSyntheticRunResult();
    const artifact = result.artifact;

    assert.equal(artifact.acquisition_execution_authorization_required, true);
    assert.equal(artifact.baseline_acceptance_required, true);
    assert.equal(artifact.final_db_write_authorization_required, true);
    assert.equal(artifact.safety_contract.controlled_acquisition_plan_is_not_accepted_mapping, true);
    assert.equal(artifact.safety_contract.controlled_acquisition_plan_is_not_raw_write_authorization, true);
    assert.equal(artifact.safety_contract.source_inventory_acquisition_execution_requires_separate_authorization, true);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.raw_write_ready_for_execution, false);
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
    assert.equal(typeof loaded.runControlledSourceInventoryAcquisitionPlan, 'function');
});

test('runControlledSourceInventoryAcquisitionPlan can write outputs to explicit temp paths', () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'l2v3x-acquisition-plan-'));
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
        assert.equal(JSON.parse(fs.readFileSync(artifactPath, 'utf8')).proposal_phase, 'Phase 5.21L2V3X');
        assert.match(fs.readFileSync(reportPath, 'utf8'), /controlled acquisition plan is not accepted mapping/i);
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
    assert.match(successOutput, /Phase 5.21L2V3X/);
    assert.match(successOutput, /raw_write_ready_for_execution/);
});

test('validateInputs fails closed on unsafe manifest and L2V3W states', () => {
    const invalidManifest = mod.validateInputs(
        syntheticManifest({
            next_required_step: 'raw_write_retry',
            raw_write_ready_for_execution: true,
            accepted_mapping_count: 1,
        }),
        syntheticL2V3WArtifact()
    );
    const invalidW = mod.validateInputs(
        syntheticManifest(),
        syntheticL2V3WArtifact({
            proposal_phase: 'Phase 5.21L2V3V',
            live_source_check_performed: true,
            network_request_performed: true,
            source_inventory_contains_url_field: true,
            current_candidates_retroactively_enrichable: true,
            requires_controlled_no_write_source_acquisition: false,
            raw_write_ready_for_execution: true,
            accepted_mapping_count: 1,
        })
    );

    assert.equal(invalidManifest.ok, false);
    assert.match(invalidManifest.errors.join('\n'), /next_required_step/);
    assert.match(invalidManifest.errors.join('\n'), /raw_write_ready_for_execution/);
    assert.match(invalidManifest.errors.join('\n'), /accepted_mapping_count/);
    assert.equal(invalidW.ok, false);
    assert.match(invalidW.errors.join('\n'), /L2V3W artifact/);
    assert.match(invalidW.errors.join('\n'), /live_source_check_performed/);
    assert.match(invalidW.errors.join('\n'), /network_request_performed/);
    assert.match(invalidW.errors.join('\n'), /source_inventory_contains_url_field/);
    assert.match(invalidW.errors.join('\n'), /current_candidates_retroactively_enrichable/);
    assert.match(invalidW.errors.join('\n'), /requires_controlled_no_write_source_acquisition/);
    assert.match(invalidW.errors.join('\n'), /raw_write_ready_for_execution/);
    assert.match(invalidW.errors.join('\n'), /accepted_mapping_count/);
});

test('repository L2V3X artifacts preserve planning-only safety when generated', () => {
    const artifactPath =
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.controlled_source_inventory_acquisition_plan.phase521l2v3x.json';
    if (!fs.existsSync(path.join(PROJECT_ROOT, artifactPath))) {
        return;
    }

    const manifest = readJson('docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json');
    const artifact = readJson(artifactPath);
    const report = readText('docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3X.md');

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3X');
    assert.equal(artifact.no_write, true);
    assert.equal(artifact.live_fetch_performed, false);
    assert.equal(artifact.source_acquisition_execution_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_insert_performed, false);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.acquisition_execution_authorization_required, true);
    assert.equal(manifest.phase_5_21_l2v3x_planning_status, artifact.artifact_status);
    assert.equal(manifest.raw_write_ready_for_execution, false);
    assert.equal(manifest.accepted_mapping_count, 0);
    assert.match(report, /controlled acquisition plan is not raw write authorization/i);
});
