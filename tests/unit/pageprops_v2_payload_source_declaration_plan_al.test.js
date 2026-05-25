'use strict';
/* eslint-disable max-lines -- L2V3AL declaration planning safety contract is audited together. */

const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const Module = require('node:module');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_payload_source_declaration_plan.js');

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
        source_path: 'l1_api_data_leagues',
        source_page_url: `https://www.fotmob.com/matches/example/${index}#48304${String(index).padStart(2, '0')}`,
        source_url_fragment_external_id: `48304${String(index).padStart(2, '0')}`,
        baseline_hash: 'a'.repeat(64),
    };
}

function manifest(overrides = {}) {
    return {
        batch_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        next_required_step: 'controlled_payload_source_declaration_planning',
        recommended_next_step: 'Phase 5.21L2V3AL: controlled payload source declaration planning',
        phase_5_21_l2v3ak_planning_status: 'completed_controlled_raw_write_input_source_investigation',
        raw_write_ready_for_execution: false,
        raw_write_execution_ready: false,
        raw_write_retry_performed: false,
        raw_write_execution_performed: false,
        raw_match_data_insert_performed: false,
        db_write_performed: false,
        requires_separate_raw_write_execution: true,
        candidate_targets: Array.from({ length: 50 }, (_value, index) => candidateTarget(index)),
        baseline_accepted_count: 50,
        ...overrides,
    };
}

function metadataArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3Y',
        candidate_scope_count: 50,
        raw_write_ready_for_execution: false,
        raw_write_execution_ready: false,
        raw_write_retry_performed: false,
        raw_write_execution_performed: false,
        raw_match_data_insert_performed: false,
        db_write_performed: false,
        network_request_performed: false,
        live_fetch_performed: false,
        detail_fetch_performed: false,
        schema_migration_performed: false,
        parser_features_training_prediction_performed: false,
        ...overrides,
    };
}

function l2v3ajArtifact(overrides = {}) {
    return {
        artifact_type: 'controlled_raw_match_data_write_execution_plan',
        proposal_phase: 'Phase 5.21L2V3AJ',
        phase_name: 'controlled_raw_match_data_write_execution_planning',
        write_input_source_status: 'unknown_no_safe_payload_source_path_declared',
        write_input_source_paths_found: [],
        raw_write_execution_ready: false,
        raw_write_execution_performed: false,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        matches_write_performed: false,
        requires_separate_raw_write_execution_authorization: true,
        ...overrides,
    };
}

function l2v3akArtifact(overrides = {}) {
    return {
        artifact_type: 'raw_write_input_source_investigation',
        artifact_status: 'completed_controlled_raw_write_input_source_investigation',
        proposal_phase: 'Phase 5.21L2V3AK',
        planning_only: true,
        raw_write_runner_input_contract_status: 'requires_manifest_metadata_plus_live_recapture_to_construct_raw_data',
        raw_write_runner_input_contract: {
            requires_manifest_metadata: true,
            requires_live_recapture: true,
            requires_full_pageprops_payload: true,
            constructs_raw_data_in_memory_from_pageprops: true,
            accepts_payload_file_path: false,
            write_mode_invoked: false,
        },
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
        metadata_only_artifacts_cannot_be_used_as_raw_payload: true,
        nonexistent_payload_path_cannot_be_accepted: true,
        source_url_evidence_cannot_be_treated_as_raw_payload: true,
        baseline_accepted_cannot_be_treated_as_raw_payload: true,
        full_payload_printed_or_saved: false,
        requires_separate_raw_write_execution_authorization: true,
        ...overrides,
    };
}

function syntheticDependencies(overrides = {}) {
    return {
        manifest: manifest(overrides.manifest || {}),
        l2v3yArtifact: metadataArtifact({ proposal_phase: 'Phase 5.21L2V3Y', ...(overrides.l2v3yArtifact || {}) }),
        l2v3aaArtifact: metadataArtifact({ proposal_phase: 'Phase 5.21L2V3AA', ...(overrides.l2v3aaArtifact || {}) }),
        l2v3acArtifact: metadataArtifact({ proposal_phase: 'Phase 5.21L2V3AC', ...(overrides.l2v3acArtifact || {}) }),
        l2v3aeArtifact: metadataArtifact({ proposal_phase: 'Phase 5.21L2V3AE', ...(overrides.l2v3aeArtifact || {}) }),
        l2v3agArtifact: metadataArtifact({
            proposal_phase: 'Phase 5.21L2V3AG',
            baseline_accepted_count: 50,
            ...(overrides.l2v3agArtifact || {}),
        }),
        l2v3aiArtifact: metadataArtifact({ proposal_phase: 'Phase 5.21L2V3AI', ...(overrides.l2v3aiArtifact || {}) }),
        l2v3ajArtifact: l2v3ajArtifact(overrides.l2v3ajArtifact || {}),
        l2v3akArtifact: l2v3akArtifact(overrides.l2v3akArtifact || {}),
        rawWriteRunnerSource:
            overrides.rawWriteRunnerSource ||
            'const MANIFEST_PATH = base.MANIFEST_PATH; function readManifestFile(){} async function recaptureTargetsSequential(){ await base.recaptureTarget(); }',
        rawWriteBaseHelperSource:
            overrides.rawWriteBaseHelperSource ||
            'const { fetchHtml } = require("./pageprops_v2_no_write_preview"); function buildRawDataForTarget(){ return { pageProps: safePageProps }; }',
        writeFiles: false,
    };
}

function runSynthetic(overrides = {}) {
    return mod.runPayloadSourceDeclarationPlan(syntheticDependencies(overrides));
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

test('L2V3AL is payload source declaration planning only', () => {
    const artifact = runSynthetic().artifact;

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AL');
    assert.equal(artifact.phase_name, 'controlled_payload_source_declaration_planning');
    assert.equal(artifact.planning_only, true);
    assert.equal(artifact.payload_source_declaration_execution_performed, false);
    assert.equal(artifact.live_recapture_execution_performed, false);
    assert.equal(artifact.raw_write_execution_ready, false);
    assert.equal(artifact.raw_write_execution_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.matches_external_id_modified, false);
});

test('controlled live recapture in memory can be planned but not executed', () => {
    const artifact = runSynthetic().artifact;
    const selected = artifact.source_type_candidates.find(candidate => candidate.selected_for_planning);

    assert.equal(artifact.source_type_candidate_count, 4);
    assert.equal(artifact.selected_planned_source_type, 'controlled_live_recapture_in_memory');
    assert.equal(artifact.payload_source_declaration_status, 'planned_not_executed');
    assert.equal(selected.source_type, 'controlled_live_recapture_in_memory');
    assert.equal(selected.payload_source_accepted, false);
    assert.equal(selected.in_memory_only, true);
    assert.equal(artifact.live_recapture_authorization_required, true);
    assert.equal(artifact.live_recapture_required_does_not_authorize_live_fetch, true);
});

test('source-controlled payload artifact direction remains unavailable and cannot be invented', () => {
    const artifact = runSynthetic().artifact;
    const candidate = artifact.source_type_candidates.find(
        entry => entry.source_type === 'source_controlled_payload_artifact'
    );

    assert.equal(artifact.source_controlled_payload_artifact_available, false);
    assert.equal(candidate.source_status, 'unavailable_missing');
    assert.equal(candidate.payload_source_accepted, false);
    assert.equal(candidate.source_path, null);
    assert.equal(candidate.raw_write_runner_contract_change_required_if_selected, true);
});

test('metadata-only, source URL evidence, and baseline hashes are not accepted as payload', () => {
    const artifact = runSynthetic().artifact;
    const unsupported = artifact.source_type_candidates.find(
        candidate => candidate.source_type === 'unsupported_metadata_only_artifact'
    );

    assert.equal(artifact.metadata_only_artifacts_accepted_as_payload, false);
    assert.equal(unsupported.payload_source_accepted, false);
    assert.match(unsupported.reason, /metadata-only artifacts/);
});

test('planned source type does not imply accepted payload source or raw write readiness', () => {
    const artifact = runSynthetic().artifact;

    assert.equal(artifact.payload_source_accepted, false);
    assert.equal(artifact.planned_source_type_is_not_payload_source_accepted, true);
    assert.equal(artifact.planned_source_type_is_not_raw_write_execution_ready, true);
    assert.equal(artifact.raw_write_execution_ready, false);
    assert.equal(artifact.requires_separate_raw_write_execution_authorization, true);
    assert.equal(artifact.payload_source_declaration_execution_required, true);
    assert.match(artifact.recommended_next_step, /Phase 5.21L2V3AM/);
});

test('payload declaration schema records in-memory policy and no full payload persistence', () => {
    const artifact = runSynthetic().artifact;
    const planned = artifact.declaration_schema.planned_values;

    assert.equal(planned.source_type, 'controlled_live_recapture_in_memory');
    assert.equal(planned.source_status, 'planned_not_executed');
    assert.equal(planned.source_path, null);
    assert.equal(planned.live_recapture_required, true);
    assert.equal(planned.live_recapture_authorization_required, true);
    assert.equal(planned.full_payload_storage_allowed, false);
    assert.equal(planned.full_payload_print_allowed, false);
    assert.equal(planned.in_memory_only, true);
    assert.equal(planned.raw_write_execution_ready, false);
});

test('current runner contract supports planned live recapture direction without accepting payload file path', () => {
    const artifact = runSynthetic().artifact;

    assert.equal(artifact.raw_write_runner_contract_change_required, false);
    assert.equal(artifact.raw_write_runner_input_contract.requires_manifest_metadata, true);
    assert.equal(artifact.raw_write_runner_input_contract.requires_live_recapture, true);
    assert.equal(artifact.raw_write_runner_input_contract.requires_full_pageprops_payload, true);
    assert.equal(artifact.raw_write_runner_input_contract.constructs_raw_data_in_memory_from_pageprops, true);
    assert.equal(artifact.raw_write_runner_input_contract.accepts_payload_file_path, false);
    assert.equal(artifact.raw_write_runner_write_mode_invoked, false);
});

test('helper refuses declaration execution, live recapture, DB write, raw write, network, and write mode flags', () => {
    const parsed = mod.parseArgs([
        '--allow-db-write=yes',
        '--allow-network=yes',
        '--allow-live-fetch=yes',
        '--allow-detail-fetch=yes',
        '--allow-raw-match-data-write=yes',
        '--allow-matches-external-id-write=yes',
        '--allow-payload-source-declaration-execution=yes',
        '--allow-live-recapture-execution=yes',
        '--execute-payload-source-declaration=yes',
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
    assert.match(errors, /allow-payload-source-declaration-execution=yes is blocked/);
    assert.match(errors, /allow-live-recapture-execution=yes is blocked/);
    assert.match(errors, /execute-payload-source-declaration=yes is blocked/);
    assert.match(errors, /execute-live-recapture=yes is blocked/);
    assert.match(errors, /execute-raw-write=yes is blocked/);
    assert.match(errors, /commit-raw-write=yes is blocked/);
    assert.match(errors, /write-mode=yes is blocked/);
    assert.match(errors, /print-full-pageprops=yes is blocked/);
});

test('input validation fails if AK no longer reports missing safe payload source path', () => {
    const result = runSynthetic({
        l2v3akArtifact: {
            safe_payload_source_path_status: 'ready',
        },
    });

    assert.equal(result.ok, false);
    assert.equal(result.status, 3);
    assert.match(result.errors.join('\n'), /safe_payload_source_path_status must remain unknown_or_missing/);
});

test('input validation fails if AK claims a full payload artifact exists', () => {
    const result = runSynthetic({
        l2v3akArtifact: {
            full_payload_artifact_found: true,
        },
    });

    assert.equal(result.ok, false);
    assert.match(result.errors.join('\n'), /full_payload_artifact_found must be false/);
});

test('input validation blocks prohibited write state in reviewed artifacts', () => {
    const result = runSynthetic({
        l2v3agArtifact: {
            db_write_performed: true,
        },
    });

    assert.equal(result.ok, false);
    assert.match(result.errors.join('\n'), /baseline_acceptance_result contains prohibited/);
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

test('runPayloadSourceDeclarationPlan can write outputs to explicit temp paths', () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'l2v3al-plan-'));
    const artifactPath = path.join(tmpDir, 'artifact.json');
    const reportPath = path.join(tmpDir, 'report.md');
    const manifestPath = path.join(tmpDir, 'manifest.json');

    try {
        const result = mod.runPayloadSourceDeclarationPlan({
            ...syntheticDependencies(),
            writeFiles: true,
            artifactOutputPath: artifactPath,
            reportOutputPath: reportPath,
            manifestOutputPath: manifestPath,
        });

        assert.equal(result.ok, true);
        assert.equal(JSON.parse(fs.readFileSync(artifactPath, 'utf8')).proposal_phase, 'Phase 5.21L2V3AL');
        assert.match(
            fs.readFileSync(reportPath, 'utf8'),
            /selected_planned_source_type=controlled_live_recapture_in_memory/i
        );
        assert.equal(JSON.parse(fs.readFileSync(manifestPath, 'utf8')).raw_write_execution_ready, false);
    } finally {
        fs.rmSync(tmpDir, { recursive: true, force: true });
    }
});

test('CLI covers help, invalid options, planning output, and no write markers', () => {
    let helpOutput = '';
    let invalidOutput = '';
    let successOutput = '';

    const helpStatus = mod.runCli(['--help'], { stdout: text => (helpOutput += text) });
    const invalidStatus = mod.runCli(['--unknown'], { stdout: text => (invalidOutput += text) });
    const successStatus = mod.runCli(['--write-files=false'], { stdout: text => (successOutput += text) });

    assert.equal(helpStatus, 0);
    assert.match(helpOutput, /declaration planning only/);
    assert.equal(invalidStatus, 2);
    assert.match(invalidOutput, /unknown arguments/);
    assert.equal(successStatus, 0);
    assert.match(successOutput, /"selected_planned_source_type": "controlled_live_recapture_in_memory"/);
    assert.match(successOutput, /"raw_write_execution_ready": false/);
    assert.match(successOutput, /"db_write_performed": false/);
    assert.match(successOutput, /"raw_match_data_insert_performed": false/);
});

test('helper does not import network, DB, browser, proxy, harvest, odds, or child process modules on load', t => {
    installImportGuard(t);
    const loaded = loadFreshModule();
    assert.equal(typeof loaded.runPayloadSourceDeclarationPlan, 'function');
});

test('import guard blocks forbidden modules when exercised', t => {
    installImportGuard(t);
    assert.throws(() => Module._load('pg', module, false), /blocked import: pg/);
});

test('script entrypoint prints help without writes when executed as main module', () => {
    const result = spawnSync(process.execPath, [MODULE_PATH, '--help'], {
        cwd: PROJECT_ROOT,
        encoding: 'utf8',
    });

    assert.equal(result.status, 0);
    assert.match(result.stdout, /declaration planning only/i);
    assert.equal(result.stderr, '');
});

test('repository L2V3AL artifacts preserve planning-only semantics when generated', () => {
    const artifactPath =
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.payload_source_declaration_plan.phase521l2v3al.json';
    if (!fs.existsSync(path.join(PROJECT_ROOT, artifactPath))) return;

    const manifestJson = readJson('docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json');
    const artifact = readJson(artifactPath);
    const report = readText('docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AL.md');

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AL');
    assert.equal(artifact.planning_only, true);
    assert.equal(artifact.selected_planned_source_type, mod.SELECTED_PLANNED_SOURCE_TYPE);
    assert.equal(artifact.payload_source_declaration_status, mod.PAYLOAD_SOURCE_DECLARATION_STATUS);
    assert.equal(artifact.raw_write_execution_ready, false);
    assert.equal(artifact.raw_write_execution_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.full_payload_storage_allowed, false);
    assert.equal(artifact.full_payload_print_allowed, false);
    assert.equal(artifact.requires_separate_raw_write_execution_authorization, true);
    assert.equal(manifestJson.phase_5_21_l2v3al_planning_status, mod.ARTIFACT_STATUS);
    assert.equal(manifestJson.raw_write_execution_ready, false);
    assert.match(report, /metadata_only_artifacts_accepted_as_payload=false/i);
});
