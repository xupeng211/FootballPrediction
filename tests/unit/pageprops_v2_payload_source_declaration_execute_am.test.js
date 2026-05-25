'use strict';
/* eslint-disable max-lines -- L2V3AM declaration execution safety contract is audited together. */

const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const Module = require('node:module');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_payload_source_declaration_execute.js');

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

function candidateTarget(index = 0) {
    return {
        match_id: `53_20252026_48304${String(index).padStart(2, '0')}`,
        external_id: `48304${String(index).padStart(2, '0')}`,
        baseline_hash: 'a'.repeat(64),
    };
}

function manifest(overrides = {}) {
    return {
        batch_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        next_required_step: 'controlled_payload_source_declaration_execution',
        recommended_next_step: 'Phase 5.21L2V3AM: controlled payload source declaration execution',
        phase_5_21_l2v3al_planning_status: 'completed_controlled_payload_source_declaration_planning',
        raw_write_ready_for_execution: false,
        raw_write_execution_ready: false,
        raw_write_retry_performed: false,
        raw_write_execution_performed: false,
        raw_match_data_insert_performed: false,
        db_write_performed: false,
        requires_separate_raw_write_execution: true,
        candidate_targets: Array.from({ length: 50 }, (_value, index) => candidateTarget(index)),
        ...overrides,
    };
}

function l2v3akArtifact(overrides = {}) {
    return {
        artifact_type: 'raw_write_input_source_investigation',
        artifact_status: 'completed_controlled_raw_write_input_source_investigation',
        proposal_phase: 'Phase 5.21L2V3AK',
        safe_payload_source_path_status: 'unknown_or_missing',
        safe_payload_source_path: null,
        metadata_only_artifacts_count: 8,
        full_payload_artifact_found: false,
        live_recapture_required: true,
        raw_write_execution_ready: false,
        raw_write_execution_performed: false,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        matches_write_performed: false,
        matches_external_id_modified: false,
        network_request_performed: false,
        live_fetch_performed: false,
        detail_fetch_performed: false,
        schema_migration_performed: false,
        parser_features_training_prediction_performed: false,
        requires_separate_raw_write_execution_authorization: true,
        ...overrides,
    };
}

function l2v3alArtifact(overrides = {}) {
    return {
        artifact_type: 'payload_source_declaration_plan',
        artifact_status: 'completed_controlled_payload_source_declaration_planning',
        proposal_phase: 'Phase 5.21L2V3AL',
        selected_planned_source_type: 'controlled_live_recapture_in_memory',
        payload_source_declaration_status: 'planned_not_executed',
        source_controlled_payload_artifact_available: false,
        controlled_live_recapture_in_memory_required: true,
        payload_source_declaration_execution_required: true,
        live_recapture_authorization_required: true,
        full_payload_storage_allowed: false,
        full_payload_print_allowed: false,
        metadata_only_artifacts_accepted_as_payload: false,
        target_count: 50,
        raw_write_execution_ready: false,
        raw_write_execution_performed: false,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        matches_write_performed: false,
        matches_external_id_modified: false,
        network_request_performed: false,
        live_fetch_performed: false,
        detail_fetch_performed: false,
        live_recapture_execution_performed: false,
        schema_migration_performed: false,
        parser_features_training_prediction_performed: false,
        requires_separate_raw_write_execution_authorization: true,
        ...overrides,
    };
}

function syntheticDependencies(overrides = {}) {
    return {
        manifest: manifest(overrides.manifest || {}),
        l2v3akArtifact: l2v3akArtifact(overrides.l2v3akArtifact || {}),
        l2v3alArtifact: l2v3alArtifact(overrides.l2v3alArtifact || {}),
        writeFiles: false,
    };
}

function runSynthetic(overrides = {}) {
    return mod.runPayloadSourceDeclarationExecute(syntheticDependencies(overrides));
}

function installImportGuard(t) {
    const originalLoad = Module._load;
    Module._load = function patchedLoad(request, parent, isMain) {
        if (
            /pg|http|https|playwright|puppeteer|ProductionHarvester|odds_harvest_pipeline|child_process/i.test(request)
        ) {
            throw new Error(`blocked import: ${request}`);
        }
        return originalLoad.call(this, request, parent, isMain);
    };
    t.after(() => {
        Module._load = originalLoad;
    });
}

test('L2V3AM executes payload source declaration only', () => {
    const artifact = runSynthetic().artifact;

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AM');
    assert.equal(artifact.phase_name, 'controlled_payload_source_declaration_execution');
    assert.equal(artifact.payload_source_declaration_execution_performed, true);
    assert.equal(artifact.payload_source_declaration_performed, true);
    assert.equal(artifact.live_recapture_execution_performed, false);
    assert.equal(artifact.raw_write_execution_ready, false);
    assert.equal(artifact.raw_write_execution_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.matches_external_id_modified, false);
});

test('selected source type is declared as controlled live recapture in memory', () => {
    const artifact = runSynthetic().artifact;

    assert.equal(artifact.selected_source_type, 'controlled_live_recapture_in_memory');
    assert.equal(artifact.payload_source_status, 'declared');
    assert.equal(artifact.source_controlled_payload_artifact_available, false);
    assert.equal(artifact.full_payload_artifact_found, false);
    assert.equal(artifact.source_path, null);
    assert.equal(artifact.current_raw_write_runner_constructs_raw_data_in_memory, true);
    assert.equal(artifact.current_runner_accepts_source_controlled_payload_file_path, false);
});

test('future live recapture requirements are recorded but not executed', () => {
    const artifact = runSynthetic().artifact;

    assert.equal(artifact.controlled_live_recapture_in_memory_required, true);
    assert.equal(artifact.live_recapture_required, true);
    assert.equal(artifact.live_recapture_authorization_required, true);
    assert.equal(artifact.no_browser_proxy_captcha_bypass, true);
    assert.equal(artifact.no_uncontrolled_retry, true);
    assert.ok(artifact.stop_conditions.includes('http_403'));
    assert.ok(artifact.stop_conditions.includes('identity_mismatch'));
    assert.equal(artifact.network_request_performed, false);
    assert.equal(artifact.live_fetch_performed, false);
    assert.equal(artifact.detail_fetch_performed, false);
});

test('payload safety disallows full payload storage and print', () => {
    const artifact = runSynthetic().artifact;

    assert.equal(artifact.full_payload_storage_allowed, false);
    assert.equal(artifact.full_payload_print_allowed, false);
    assert.equal(artifact.in_memory_only, true);
    assert.equal(artifact.full_raw_data_printed_or_saved, false);
    assert.equal(artifact.full_pageprops_printed_or_saved, false);
    assert.equal(artifact.full_source_body_printed_or_saved, false);
    assert.equal(artifact.cookies_tokens_headers_saved, false);
});

test('metadata-only, source URL evidence, and baseline hashes remain rejected as payload', () => {
    const artifact = runSynthetic().artifact;

    assert.equal(artifact.metadata_only_artifacts_accepted_as_payload, false);
    assert.equal(artifact.source_url_evidence_accepted_as_payload, false);
    assert.equal(artifact.baseline_hashes_accepted_as_payload, false);
});

test('payload source declaration does not imply raw write readiness or raw write execution', () => {
    const artifact = runSynthetic().artifact;

    assert.equal(artifact.payload_source_declaration_is_not_raw_write_execution, true);
    assert.equal(artifact.payload_source_declaration_does_not_make_raw_write_execution_ready, true);
    assert.equal(artifact.future_live_recapture_success_does_not_authorize_raw_write_by_itself, true);
    assert.equal(artifact.raw_write_execution_ready, false);
    assert.equal(artifact.raw_write_execution_performed, false);
    assert.equal(artifact.requires_separate_raw_write_execution_authorization, true);
    assert.match(artifact.recommended_next_step, /Phase 5.21L2V3AN/);
});

test('local broad node --test DB insert attempt is documented as blocked and non-persistent', () => {
    const artifact = runSynthetic().artifact;
    const incident = artifact.local_validation_incident_review;

    assert.equal(incident.broad_node_test_accidental_e2e_db_insert_attempt_observed, true);
    assert.equal(incident.insert_attempt_succeeded, false);
    assert.equal(incident.insert_attempt_blocked_by_db_constraint, true);
    assert.equal(incident.cleanup_ran, true);
    assert.equal(incident.followup_select_only_row_count_unchanged, true);
    assert.equal(incident.protected_tables_unchanged, true);
    assert.equal(incident.raw_match_data_rows_added, 0);
    assert.equal(incident.matches_rows_added_or_modified, 0);
    assert.equal(incident.matches_external_id_modified, false);
    assert.equal(incident.later_explicit_file_list_validation_passed, true);
    assert.equal(incident.not_successful_db_write, true);
    assert.equal(incident.not_raw_write_execution, true);
    assert.equal(incident.not_regular_safety_validation_entrypoint, true);
    assert.equal(incident.l2v3am_db_write_performed, false);
});

test('helper refuses live recapture, DB write, raw write, network, and write mode flags', () => {
    const parsed = mod.parseArgs([
        '--allow-db-write=yes',
        '--allow-network=yes',
        '--allow-live-fetch=yes',
        '--allow-detail-fetch=yes',
        '--allow-raw-match-data-write=yes',
        '--allow-matches-external-id-write=yes',
        '--allow-live-recapture-execution=yes',
        '--execute-live-recapture=yes',
        '--execute-raw-write=yes',
        '--commit-raw-write=yes',
        '--write-mode=yes',
        '--print-full-pageprops=yes',
    ]);
    const validation = mod.validateCliOptions(parsed);
    const errors = validation.errors.join('\n');

    assert.equal(validation.ok, false);
    assert.match(errors, /allow-db-write=yes is blocked/);
    assert.match(errors, /allow-network=yes is blocked/);
    assert.match(errors, /allow-live-fetch=yes is blocked/);
    assert.match(errors, /allow-detail-fetch=yes is blocked/);
    assert.match(errors, /allow-raw-match-data-write=yes is blocked/);
    assert.match(errors, /allow-matches-external-id-write=yes is blocked/);
    assert.match(errors, /allow-live-recapture-execution=yes is blocked/);
    assert.match(errors, /execute-live-recapture=yes is blocked/);
    assert.match(errors, /execute-raw-write=yes is blocked/);
    assert.match(errors, /commit-raw-write=yes is blocked/);
    assert.match(errors, /write-mode=yes is blocked/);
    assert.match(errors, /print-full-pageprops=yes is blocked/);
});

test('input validation fails if AL did not plan the selected source type', () => {
    const result = runSynthetic({
        l2v3alArtifact: {
            selected_planned_source_type: 'unknown',
        },
    });

    assert.equal(result.ok, false);
    assert.equal(result.status, 3);
    assert.match(result.errors.join('\n'), /selected planned source type/);
});

test('input validation fails if a full payload artifact is claimed available', () => {
    const result = runSynthetic({
        l2v3akArtifact: {
            full_payload_artifact_found: true,
        },
    });

    assert.equal(result.ok, false);
    assert.match(result.errors.join('\n'), /full payload artifact/);
});

test('input validation blocks prohibited write or fetch state in reviewed artifacts', () => {
    const result = runSynthetic({
        l2v3alArtifact: {
            live_fetch_performed: true,
        },
    });

    assert.equal(result.ok, false);
    assert.match(result.errors.join('\n'), /payload_source_declaration_plan contains prohibited/);
});

test('outputs avoid full raw data, pageProps, source body, and HTML payloads', () => {
    const result = runSynthetic();
    for (const text of [JSON.stringify(result.artifact), result.report, JSON.stringify(result.updated_manifest)]) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
        assert.equal(text.includes('"source_body":'), false);
        assert.equal(text.includes('"full_json":'), false);
    }
});

test('runPayloadSourceDeclarationExecute can write outputs to explicit temp paths', () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'l2v3am-execute-'));
    const artifactPath = path.join(tmpDir, 'artifact.json');
    const reportPath = path.join(tmpDir, 'report.md');
    const manifestPath = path.join(tmpDir, 'manifest.json');

    try {
        const result = mod.runPayloadSourceDeclarationExecute({
            ...syntheticDependencies(),
            writeFiles: true,
            artifactOutputPath: artifactPath,
            reportOutputPath: reportPath,
            manifestOutputPath: manifestPath,
        });

        assert.equal(result.ok, true);
        assert.equal(JSON.parse(fs.readFileSync(artifactPath, 'utf8')).proposal_phase, 'Phase 5.21L2V3AM');
        assert.match(fs.readFileSync(reportPath, 'utf8'), /selected_source_type=controlled_live_recapture_in_memory/i);
        assert.equal(JSON.parse(fs.readFileSync(manifestPath, 'utf8')).raw_write_execution_ready, false);
    } finally {
        fs.rmSync(tmpDir, { recursive: true, force: true });
    }
});

test('CLI covers help, invalid options, execution output, and no write markers', () => {
    let helpOutput = '';
    let invalidOutput = '';
    let successOutput = '';

    const helpStatus = mod.runCli(['--help'], { stdout: text => (helpOutput += text) });
    const invalidStatus = mod.runCli(['--unknown'], { stdout: text => (invalidOutput += text) });
    const successStatus = mod.runCli(['--write-files=false'], { stdout: text => (successOutput += text) });

    assert.equal(helpStatus, 0);
    assert.match(helpOutput, /declaration only/);
    assert.equal(invalidStatus, 2);
    assert.match(invalidOutput, /unknown arguments/);
    assert.equal(successStatus, 0);
    assert.match(successOutput, /"selected_source_type": "controlled_live_recapture_in_memory"/);
    assert.match(successOutput, /"payload_source_status": "declared"/);
    assert.match(successOutput, /"raw_write_execution_ready": false/);
    assert.match(successOutput, /"db_write_performed": false/);
    assert.match(successOutput, /"raw_match_data_insert_performed": false/);
});

test('helper does not import network, DB, browser, proxy, harvest, odds, or child process modules on load', t => {
    installImportGuard(t);
    const loaded = loadFreshModule();
    assert.equal(typeof loaded.runPayloadSourceDeclarationExecute, 'function');
});

test('script entrypoint prints help without writes when executed as main module', () => {
    const result = spawnSync(process.execPath, [MODULE_PATH, '--help'], {
        cwd: PROJECT_ROOT,
        encoding: 'utf8',
    });

    assert.equal(result.status, 0);
    assert.match(result.stdout, /controlled payload source declaration only/i);
    assert.equal(result.stderr, '');
});

test('repository L2V3AM artifacts preserve declaration-only semantics when generated', () => {
    const artifactPath =
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.payload_source_declaration_result.phase521l2v3am.json';
    if (!fs.existsSync(path.join(PROJECT_ROOT, artifactPath))) return;

    const manifestJson = readJson('docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json');
    const artifact = readJson(artifactPath);
    const report = readText('docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AM.md');

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AM');
    assert.equal(artifact.payload_source_declaration_performed, true);
    assert.equal(artifact.selected_source_type, mod.SELECTED_SOURCE_TYPE);
    assert.equal(artifact.payload_source_status, mod.PAYLOAD_SOURCE_STATUS);
    assert.equal(artifact.raw_write_execution_ready, false);
    assert.equal(artifact.raw_write_execution_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.full_payload_storage_allowed, false);
    assert.equal(artifact.full_payload_print_allowed, false);
    assert.equal(artifact.requires_separate_raw_write_execution_authorization, true);
    assert.equal(manifestJson.phase_5_21_l2v3am_execution_status, mod.ARTIFACT_STATUS);
    assert.equal(manifestJson.raw_write_execution_ready, false);
    assert.match(report, /payload_source_declaration_is_not_raw_write_execution=true/i);
    assert.match(report, /broad_node_test_accidental_e2e_db_insert_attempt_observed=true/i);
    assert.match(report, /insert_attempt_succeeded=false/i);
    assert.match(report, /followup_select_only_row_count_unchanged=true/i);
    assert.match(report, /not_successful_db_write=true/i);
});
