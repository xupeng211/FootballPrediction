'use strict';
/* eslint-disable max-lines -- L2V3AK input source safety contract is audited together. */

const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const Module = require('node:module');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_raw_write_input_source_investigation.js');

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

function candidateTarget(index = 0, overrides = {}) {
    return {
        match_id: `53_20252026_48304${String(index).padStart(2, '0')}`,
        external_id: `48304${String(index).padStart(2, '0')}`,
        source_path: 'l1_api_data_leagues',
        source_page_url: `https://www.fotmob.com/matches/example/${index}#48304${String(index).padStart(2, '0')}`,
        source_url_fragment_external_id: `48304${String(index).padStart(2, '0')}`,
        baseline_hash: 'a'.repeat(64),
        pageprops_summary: {
            parse_status: 'pageprops_v2_parsed',
            raw_data_shape_valid: true,
            has_pageProps: true,
            pageProps_path_count: 123,
        },
        ...overrides,
    };
}

function manifest(overrides = {}) {
    return {
        batch_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        next_required_step: 'continued_controlled_raw_write_planning',
        recommended_next_step: 'Phase 5.21L2V3AK: continued controlled raw write planning',
        phase_5_21_l2v3aj_planning_status: 'completed_controlled_raw_match_data_write_execution_planning',
        raw_write_ready_for_execution: false,
        raw_write_retry_performed: false,
        raw_write_execution_performed: false,
        raw_match_data_insert_performed: false,
        db_write_performed: false,
        requires_separate_raw_write_execution: true,
        candidate_targets: Array.from({ length: 3 }, (_value, index) => candidateTarget(index)),
        baseline_accepted_count: 50,
        ...overrides,
    };
}

function metadataArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3Y',
        candidate_scope_count: 50,
        raw_write_ready_for_execution: false,
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
        raw_write_execution_performed: false,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        matches_write_performed: false,
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
        rawWriteRunnerSource:
            overrides.rawWriteRunnerSource ||
            'const MANIFEST_PATH = base.MANIFEST_PATH; function readManifestFile(){} async function recaptureTargetsSequential(){ await base.recaptureTarget(); } const insertSql = base.buildInsertRawMatchDataSql(recaptureGate.targets, collectedAt);',
        rawWriteBaseHelperSource:
            overrides.rawWriteBaseHelperSource ||
            'const { fetchHtml } = require("./pageprops_v2_no_write_preview"); function buildRawDataForTarget(){ return { pageProps: safePageProps }; } const sql = "INSERT INTO raw_match_data";',
        writeFiles: false,
    };
}

function runSynthetic(overrides = {}) {
    return mod.runRawWriteInputSourceInvestigation(syntheticDependencies(overrides));
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

test('L2V3AK is planning and investigation only', () => {
    const artifact = runSynthetic().artifact;

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AK');
    assert.equal(artifact.phase_name, 'continued_controlled_raw_write_planning');
    assert.equal(artifact.planning_only, true);
    assert.equal(artifact.raw_write_execution_ready, false);
    assert.equal(artifact.raw_write_execution_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.matches_external_id_modified, false);
});

test('raw write runner input contract requires live recapture and does not accept payload file path', () => {
    const artifact = runSynthetic().artifact;

    assert.equal(artifact.raw_write_runner_input_contract_status, mod.INPUT_CONTRACT_STATUS);
    assert.equal(artifact.raw_write_runner_input_contract.requires_manifest_metadata, true);
    assert.equal(artifact.raw_write_runner_input_contract.requires_live_recapture, true);
    assert.equal(artifact.raw_write_runner_input_contract.requires_full_pageprops_payload, true);
    assert.equal(artifact.raw_write_runner_input_contract.constructs_raw_data_in_memory_from_pageprops, true);
    assert.equal(artifact.raw_write_runner_input_contract.accepts_payload_file_path, false);
    assert.equal(artifact.raw_write_runner_write_mode_invoked, false);
});

test('missing safe payload source path blocks raw write execution readiness', () => {
    const artifact = runSynthetic().artifact;

    assert.equal(artifact.safe_payload_source_path_status, 'unknown_or_missing');
    assert.equal(artifact.safe_payload_source_path, null);
    assert.equal(artifact.payload_source_accepted_count, 0);
    assert.equal(artifact.full_payload_artifact_found, false);
    assert.equal(artifact.raw_write_execution_ready, false);
    assert.equal(artifact.controlled_payload_source_planning_required, true);
});

test('metadata-only artifacts cannot be used as raw payload', () => {
    const artifact = runSynthetic().artifact;

    assert.equal(artifact.metadata_only_artifacts_cannot_be_used_as_raw_payload, true);
    assert.equal(artifact.metadata_only_artifacts_count, 8);
    assert.equal(
        artifact.reviewed_artifact_summaries.every(summary => summary.metadata_only),
        true
    );
});

test('nonexistent payload path cannot be accepted', () => {
    const artifact = runSynthetic({
        manifest: {
            safe_payload_source_path:
                'docs/_controlled_payloads/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.missing.json',
        },
    }).artifact;
    const declared = artifact.payload_source_candidates.find(
        candidate => candidate.candidate_type === 'declared_payload_source_path'
    );

    assert.equal(artifact.nonexistent_payload_path_cannot_be_accepted, true);
    assert.equal(declared.accepted, false);
    assert.equal(declared.status, 'rejected');
    assert.equal(declared.evidence[0].source_controlled_path_exists, false);
    assert.equal(artifact.raw_write_execution_ready, false);
});

test('source URL evidence cannot be treated as raw payload', () => {
    const artifact = runSynthetic().artifact;
    const sourceEvidence = artifact.payload_source_candidates.find(
        candidate => candidate.candidate_type === 'source_url_identity_evidence'
    );

    assert.equal(artifact.source_url_evidence_cannot_be_treated_as_raw_payload, true);
    assert.equal(sourceEvidence.accepted, false);
    assert.equal(sourceEvidence.status, 'rejected');
    assert.match(sourceEvidence.reason, /identity only/);
});

test('baseline acceptance and hashes cannot be treated as raw payload', () => {
    const artifact = runSynthetic().artifact;
    const baseline = artifact.payload_source_candidates.find(
        candidate => candidate.candidate_type === 'accepted_baseline_hash_metadata'
    );

    assert.equal(artifact.baseline_accepted_cannot_be_treated_as_raw_payload, true);
    assert.equal(baseline.accepted, false);
    assert.equal(baseline.status, 'rejected');
    assert.match(baseline.reason, /hash gates/);
});

test('separate raw write execution authorization remains required', () => {
    const artifact = runSynthetic().artifact;

    assert.equal(artifact.requires_separate_raw_write_execution_authorization, true);
    assert.equal(artifact.raw_write_execution_ready, false);
    assert.match(artifact.recommended_next_step, /Phase 5.21L2V3AL/);
    assert.notEqual(artifact.next_required_step, 'controlled_raw_match_data_write_execution');
});

test('helper refuses DB write, raw write, network, detail fetch, and write mode flags', () => {
    const parsed = mod.parseArgs([
        '--allow-db-write=yes',
        '--allow-network=yes',
        '--allow-live-fetch=yes',
        '--allow-detail-fetch=yes',
        '--allow-raw-match-data-write=yes',
        '--allow-matches-external-id-write=yes',
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
    assert.match(errors, /execute-raw-write=yes is blocked/);
    assert.match(errors, /commit-raw-write=yes is blocked/);
    assert.match(errors, /write-mode=yes is blocked/);
    assert.match(errors, /print-full-pageprops=yes is blocked/);
});

test('input validation fails if AJ source status is no longer unknown', () => {
    const result = runSynthetic({
        l2v3ajArtifact: {
            write_input_source_status: 'ready',
        },
    });

    assert.equal(result.ok, false);
    assert.equal(result.status, 3);
    assert.match(result.errors.join('\n'), /write_input_source_status must remain unknown/);
});

test('input validation blocks prohibited write state in reviewed artifacts', () => {
    const result = runSynthetic({
        l2v3aiArtifact: {
            db_write_performed: true,
        },
    });

    assert.equal(result.ok, false);
    assert.match(result.errors.join('\n'), /final_db_write_authorization_result contains prohibited/);
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

test('runRawWriteInputSourceInvestigation can write outputs to explicit temp paths', () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'l2v3ak-plan-'));
    const artifactPath = path.join(tmpDir, 'artifact.json');
    const reportPath = path.join(tmpDir, 'report.md');
    const manifestPath = path.join(tmpDir, 'manifest.json');

    try {
        const result = mod.runRawWriteInputSourceInvestigation({
            ...syntheticDependencies(),
            writeFiles: true,
            artifactOutputPath: artifactPath,
            reportOutputPath: reportPath,
            manifestOutputPath: manifestPath,
        });

        assert.equal(result.ok, true);
        assert.equal(JSON.parse(fs.readFileSync(artifactPath, 'utf8')).proposal_phase, 'Phase 5.21L2V3AK');
        assert.match(fs.readFileSync(reportPath, 'utf8'), /safe_payload_source_path_status=unknown_or_missing/i);
        assert.equal(JSON.parse(fs.readFileSync(manifestPath, 'utf8')).raw_write_execution_ready, false);
    } finally {
        fs.rmSync(tmpDir, { recursive: true, force: true });
    }
});

test('CLI covers help, invalid options, planning output, and no write markers', () => {
    let helpOutput = '';
    let invalidOutput = '';
    let successOutput = '';
    const originalReadFileSync = fs.readFileSync;

    fs.readFileSync = function patchedReadFileSync(filePath, ...rest) {
        const textPath = String(filePath);
        if (textPath.endsWith(mod.MANIFEST_PATH)) {
            return JSON.stringify(manifest(), null, 2);
        }
        if (textPath.endsWith(mod.L2V3Y_ARTIFACT_PATH)) {
            return JSON.stringify(metadataArtifact({ proposal_phase: 'Phase 5.21L2V3Y' }), null, 2);
        }
        if (textPath.endsWith(mod.L2V3AA_ARTIFACT_PATH)) {
            return JSON.stringify(metadataArtifact({ proposal_phase: 'Phase 5.21L2V3AA' }), null, 2);
        }
        if (textPath.endsWith(mod.L2V3AC_ARTIFACT_PATH)) {
            return JSON.stringify(metadataArtifact({ proposal_phase: 'Phase 5.21L2V3AC' }), null, 2);
        }
        if (textPath.endsWith(mod.L2V3AE_ARTIFACT_PATH)) {
            return JSON.stringify(metadataArtifact({ proposal_phase: 'Phase 5.21L2V3AE' }), null, 2);
        }
        if (textPath.endsWith(mod.L2V3AG_ARTIFACT_PATH)) {
            return JSON.stringify(
                metadataArtifact({ proposal_phase: 'Phase 5.21L2V3AG', baseline_accepted_count: 50 }),
                null,
                2
            );
        }
        if (textPath.endsWith(mod.L2V3AJ_ARTIFACT_PATH)) {
            return JSON.stringify(l2v3ajArtifact(), null, 2);
        }
        return originalReadFileSync.call(this, filePath, ...rest);
    };

    try {
        const helpStatus = mod.runCli(['--help'], { stdout: text => (helpOutput += text) });
        const invalidStatus = mod.runCli(['--unknown'], { stdout: text => (invalidOutput += text) });
        const successStatus = mod.runCli(['--write-files=false'], { stdout: text => (successOutput += text) });

        assert.equal(helpStatus, 0);
        assert.match(helpOutput, /input source investigation only/);
        assert.equal(invalidStatus, 2);
        assert.match(invalidOutput, /unknown arguments/);
        assert.equal(successStatus, 0);
        assert.match(successOutput, /"safe_payload_source_path_status": "unknown_or_missing"/);
        assert.match(successOutput, /"raw_write_execution_ready": false/);
        assert.match(successOutput, /"db_write_performed": false/);
        assert.match(successOutput, /"raw_match_data_insert_performed": false/);
    } finally {
        fs.readFileSync = originalReadFileSync;
    }
});

test('helper does not import network, DB, browser, proxy, harvest, odds, or child process modules on load', t => {
    installImportGuard(t);
    const loaded = loadFreshModule();
    assert.equal(typeof loaded.runRawWriteInputSourceInvestigation, 'function');
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
    assert.match(result.stdout, /input source investigation only/i);
    assert.equal(result.stderr, '');
});

test('repository L2V3AK artifacts preserve planning-only semantics when generated', () => {
    const artifactPath =
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.raw_write_input_source_investigation.phase521l2v3ak.json';
    if (!fs.existsSync(path.join(PROJECT_ROOT, artifactPath))) return;

    const manifestJson = readJson('docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json');
    const artifact = readJson(artifactPath);
    const report = readText('docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AK.md');

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AK');
    assert.equal(artifact.planning_only, true);
    assert.equal(artifact.safe_payload_source_path_status, 'unknown_or_missing');
    assert.equal(artifact.raw_write_execution_ready, false);
    assert.equal(artifact.raw_write_execution_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.requires_separate_raw_write_execution_authorization, true);
    assert.equal(manifestJson.phase_5_21_l2v3ak_planning_status, mod.ARTIFACT_STATUS);
    assert.equal(manifestJson.raw_write_execution_ready, false);
    assert.match(report, /metadata_only_artifacts_cannot_be_used_as_raw_payload=true/i);
});
