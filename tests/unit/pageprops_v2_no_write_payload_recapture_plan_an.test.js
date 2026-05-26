'use strict';
/* eslint-disable max-lines -- L2V3AN no-write recapture planning contract is audited together. */

const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const Module = require('node:module');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_no_write_payload_recapture_plan.js');

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
        next_required_step: 'controlled_no_write_payload_recapture_planning',
        recommended_next_step: 'Phase 5.21L2V3AN: controlled no-write payload recapture planning',
        phase_5_21_l2v3am_execution_status: 'completed_controlled_payload_source_declaration_execution',
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
        full_payload_artifact_found: false,
        live_recapture_required: true,
        raw_write_execution_ready: false,
        raw_write_execution_performed: false,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        network_request_performed: false,
        live_fetch_performed: false,
        detail_fetch_performed: false,
        ...overrides,
    };
}

function l2v3alArtifact(overrides = {}) {
    return {
        artifact_type: 'payload_source_declaration_plan',
        artifact_status: 'completed_controlled_payload_source_declaration_planning',
        proposal_phase: 'Phase 5.21L2V3AL',
        selected_planned_source_type: 'controlled_live_recapture_in_memory',
        target_count: 50,
        raw_write_execution_ready: false,
        raw_write_execution_performed: false,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        network_request_performed: false,
        live_fetch_performed: false,
        detail_fetch_performed: false,
        ...overrides,
    };
}

function l2v3amArtifact(overrides = {}) {
    return {
        artifact_type: 'payload_source_declaration_result',
        artifact_status: 'completed_controlled_payload_source_declaration_execution',
        proposal_phase: 'Phase 5.21L2V3AM',
        payload_source_declaration_performed: true,
        selected_source_type: 'controlled_live_recapture_in_memory',
        payload_source_status: 'declared',
        live_recapture_required: true,
        live_recapture_authorization_required: true,
        full_payload_storage_allowed: false,
        full_payload_print_allowed: false,
        in_memory_only: true,
        target_count: 50,
        raw_write_execution_ready: false,
        raw_write_execution_performed: false,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        network_request_performed: false,
        live_fetch_performed: false,
        detail_fetch_performed: false,
        live_recapture_execution_performed: false,
        ...overrides,
    };
}

function syntheticDependencies(overrides = {}) {
    return {
        manifest: manifest(overrides.manifest || {}),
        l2v3akArtifact: l2v3akArtifact(overrides.l2v3akArtifact || {}),
        l2v3alArtifact: l2v3alArtifact(overrides.l2v3alArtifact || {}),
        l2v3amArtifact: l2v3amArtifact(overrides.l2v3amArtifact || {}),
        writeFiles: false,
    };
}

function runSynthetic(overrides = {}) {
    return mod.runNoWritePayloadRecapturePlan(syntheticDependencies(overrides));
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

test('L2V3AN is a planning-only no-write payload recapture phase', () => {
    const artifact = runSynthetic().artifact;

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AN');
    assert.equal(artifact.phase_name, 'controlled_no_write_payload_recapture_planning');
    assert.equal(artifact.planning_status, mod.ARTIFACT_STATUS);
    assert.equal(artifact.recapture_planning_status, 'planned_not_executed');
    assert.equal(artifact.no_write_payload_recapture_execution_performed, false);
    assert.equal(artifact.live_recapture_execution_performed, false);
    assert.equal(artifact.network_request_performed, false);
    assert.equal(artifact.live_fetch_performed, false);
    assert.equal(artifact.detail_fetch_performed, false);
});

test('planned scope uses controlled live recapture in memory for 50 targets', () => {
    const artifact = runSynthetic().artifact;

    assert.equal(artifact.planned_source_type, 'controlled_live_recapture_in_memory');
    assert.equal(artifact.planned_target_count, 50);
    assert.equal(artifact.recapture_scope.target_count, 50);
    assert.equal(artifact.recapture_scope.no_browser_proxy_captcha_bypass, true);
    assert.equal(artifact.recapture_scope.no_raw_write, true);
    assert.equal(artifact.recapture_scope.no_db_write, true);
});

test('planning requires separate no-write live recapture authorization', () => {
    const artifact = runSynthetic().artifact;

    assert.equal(artifact.current_user_instruction_authorizes_planning_only, true);
    assert.equal(artifact.live_recapture_authorization_required, true);
    assert.equal(artifact.no_write_recapture_authorization_required, true);
    assert.equal(artifact.recapture_execution_ready, false);
    assert.equal(artifact.raw_write_execution_ready, false);
    assert.match(artifact.recommended_next_step, /Phase 5.21L2V3AO/);
});

test('payload handling remains in-memory only and metadata-safe', () => {
    const artifact = runSynthetic().artifact;

    assert.equal(artifact.in_memory_only, true);
    assert.equal(artifact.full_payload_storage_allowed, false);
    assert.equal(artifact.full_payload_print_allowed, false);
    assert.equal(artifact.cookies_tokens_headers_persisted, false);
    assert.equal(artifact.metadata_only_artifacts_accepted_as_payload, false);
    assert.equal(artifact.source_url_evidence_accepted_as_payload, false);
    assert.equal(artifact.baseline_hashes_accepted_as_payload, false);
});

test('planned output fields are safe metadata only', () => {
    const artifact = runSynthetic().artifact;

    assert.ok(artifact.planned_safe_output_fields.includes('stable_pageprops_payload_v1_hash'));
    assert.ok(artifact.planned_safe_output_fields.includes('structural_summary'));
    assert.ok(!artifact.planned_safe_output_fields.includes('raw_data'));
    assert.ok(!artifact.planned_safe_output_fields.includes('pageProps'));
    assert.ok(!artifact.planned_safe_output_fields.includes('source_body'));
});

test('identity and hash validation rules are planned explicitly', () => {
    const artifact = runSynthetic().artifact;

    assert.equal(artifact.planned_identity_validation_rule_count, 5);
    assert.ok(
        artifact.planned_identity_validation_rules.includes(
            'requested_schedule_external_id_must_match_accepted_mapping_baseline_and_enriched_targets'
        )
    );
    assert.ok(
        artifact.planned_identity_validation_rules.includes(
            'source_url_fragment_external_id_must_match_schedule_external_id'
        )
    );
    assert.match(artifact.planned_hash_validation_policy, /stable_pageprops_payload_v1/);
    assert.match(artifact.planned_hash_validation_policy, /must not print or save full payloads/);
    assert.match(artifact.planned_hash_validation_policy, /must not auto-update baseline/);
});

test('stopping rules include block, mismatch, DB write attempt, and full payload leak', () => {
    const artifact = runSynthetic().artifact;

    assert.equal(artifact.planned_stopping_rule_count, mod.PLANNED_STOPPING_RULES.length);
    for (const rule of [
        'http_403',
        'captcha_or_block_marker',
        'parse_failure',
        'identity_mismatch',
        'hash_mismatch_unexplained',
        'db_write_path_attempt',
        'full_payload_leak_attempt',
    ]) {
        assert.ok(artifact.planned_stopping_rules.includes(rule));
    }
});

test('recapture planning does not imply raw write readiness or raw write execution', () => {
    const artifact = runSynthetic().artifact;

    assert.equal(artifact.recapture_plan_is_not_recapture_execution, true);
    assert.equal(artifact.recapture_plan_is_not_raw_write_readiness, true);
    assert.equal(artifact.future_recapture_success_does_not_authorize_raw_write_by_itself, true);
    assert.equal(artifact.raw_write_execution_ready, false);
    assert.equal(artifact.raw_write_execution_performed, false);
    assert.equal(artifact.requires_separate_raw_write_execution_authorization, true);
});

test('helper refuses live fetch, detail fetch, DB write, recapture execution, raw write, and payload flags', () => {
    const parsed = mod.parseArgs([
        '--allow-db-write=yes',
        '--allow-network=yes',
        '--allow-live-fetch=yes',
        '--allow-detail-fetch=yes',
        '--allow-raw-match-data-write=yes',
        '--allow-matches-external-id-write=yes',
        '--allow-no-write-recapture-execution=yes',
        '--execute-no-write-recapture=yes',
        '--execute-live-fetch=yes',
        '--execute-detail-fetch=yes',
        '--execute-raw-write=yes',
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
    assert.match(errors, /allow-no-write-recapture-execution=yes is blocked/);
    assert.match(errors, /execute-no-write-recapture=yes is blocked/);
    assert.match(errors, /execute-live-fetch=yes is blocked/);
    assert.match(errors, /execute-detail-fetch=yes is blocked/);
    assert.match(errors, /execute-raw-write=yes is blocked/);
    assert.match(errors, /write-mode=yes is blocked/);
    assert.match(errors, /print-full-pageprops=yes is blocked/);
});

test('input validation fails if AM declaration is missing or unsafe', () => {
    assert.equal(
        runSynthetic({
            l2v3amArtifact: {
                payload_source_status: 'blocked',
            },
        }).ok,
        false
    );
    assert.equal(
        runSynthetic({
            l2v3amArtifact: {
                selected_source_type: 'source_controlled_payload_artifact',
            },
        }).ok,
        false
    );
    assert.equal(
        runSynthetic({
            l2v3amArtifact: {
                live_fetch_performed: true,
            },
        }).ok,
        false
    );
});

test('outputs avoid full raw data, pageProps, source body, and HTML payloads', () => {
    const { artifact, report } = runSynthetic();
    const combined = `${JSON.stringify(artifact)}\n${report}`;

    for (const text of [combined]) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
        assert.equal(text.includes('"source_body":'), false);
        assert.equal(text.includes('"full_json":'), false);
    }
});

test('runNoWritePayloadRecapturePlan can write outputs to explicit temp paths', () => {
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'l2v3an-'));
    const artifactPath = path.join(tempDir, 'artifact.json');
    const reportPath = path.join(tempDir, 'report.md');
    const manifestPath = path.join(tempDir, 'manifest.json');

    const result = mod.runNoWritePayloadRecapturePlan({
        ...syntheticDependencies(),
        writeFiles: true,
        artifactOutputPath: artifactPath,
        reportOutputPath: reportPath,
        manifestOutputPath: manifestPath,
    });

    assert.equal(result.ok, true);
    assert.equal(JSON.parse(fs.readFileSync(artifactPath, 'utf8')).proposal_phase, 'Phase 5.21L2V3AN');
    assert.match(fs.readFileSync(reportPath, 'utf8'), /phase_name=controlled_no_write_payload_recapture_planning/i);
    assert.equal(JSON.parse(fs.readFileSync(manifestPath, 'utf8')).next_required_step, mod.NEXT_REQUIRED_STEP);
});

test('CLI covers help, invalid options, planning output, and no-write markers', () => {
    let helpOutput = '';
    let invalidOutput = '';
    let successOutput = '';
    const originalReadFileSync = fs.readFileSync;

    fs.readFileSync = function patchedReadFileSync(filePath, ...rest) {
        const textPath = String(filePath);
        if (textPath.endsWith(mod.MANIFEST_PATH)) {
            return JSON.stringify(manifest(), null, 2);
        }
        if (textPath.endsWith(mod.L2V3AK_ARTIFACT_PATH)) {
            return JSON.stringify(l2v3akArtifact(), null, 2);
        }
        if (textPath.endsWith(mod.L2V3AL_ARTIFACT_PATH)) {
            return JSON.stringify(l2v3alArtifact(), null, 2);
        }
        if (textPath.endsWith(mod.L2V3AM_ARTIFACT_PATH)) {
            return JSON.stringify(l2v3amArtifact(), null, 2);
        }
        return originalReadFileSync.call(this, filePath, ...rest);
    };

    try {
        const helpStatus = mod.runCli(['--help'], { stdout: text => (helpOutput += text) });
        const invalidStatus = mod.runCli(['--unknown'], { stdout: text => (invalidOutput += text) });
        const successStatus = mod.runCli(['--write-files=false'], { stdout: text => (successOutput += text) });

        assert.equal(helpStatus, 0);
        assert.match(helpOutput, /plans controlled no-write payload recapture only/i);
        assert.equal(invalidStatus, 2);
        assert.match(invalidOutput, /unknown arguments/);
        assert.equal(successStatus, 0);
        assert.match(successOutput, /"planned_source_type": "controlled_live_recapture_in_memory"/);
        assert.match(successOutput, /"live_recapture_execution_performed": false/);
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
    assert.equal(typeof loaded.runNoWritePayloadRecapturePlan, 'function');
});

test('script entrypoint prints help without writes when executed as main module', () => {
    const result = spawnSync(process.execPath, [MODULE_PATH, '--help'], {
        cwd: PROJECT_ROOT,
        encoding: 'utf8',
    });

    assert.equal(result.status, 0);
    assert.match(result.stdout, /controlled no-write payload recapture only/i);
    assert.equal(result.stderr, '');
});

test('repository L2V3AN artifacts preserve planning-only semantics when generated', () => {
    const artifactPath =
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.no_write_payload_recapture_plan.phase521l2v3an.json';
    if (!fs.existsSync(path.join(PROJECT_ROOT, artifactPath))) return;

    const manifestJson = readJson('docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json');
    const artifact = readJson(artifactPath);
    const report = readText('docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AN.md');

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AN');
    assert.equal(artifact.planned_source_type, mod.PLANNED_SOURCE_TYPE);
    assert.equal(artifact.no_write_payload_recapture_execution_performed, false);
    assert.equal(artifact.live_fetch_performed, false);
    assert.equal(artifact.detail_fetch_performed, false);
    assert.equal(artifact.network_request_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.raw_write_execution_ready, false);
    assert.equal(artifact.full_payload_storage_allowed, false);
    assert.equal(artifact.full_payload_print_allowed, false);
    assert.equal(manifestJson.phase_5_21_l2v3an_planning_status, mod.ARTIFACT_STATUS);
    assert.ok(
        [
            mod.NEXT_REQUIRED_STEP,
            'no_write_payload_recapture_blocker_investigation',
            'partial_recapture_review_planning',
            'controlled_recapture_result_verification_planning',
            'accepted_mapping_and_baseline_contradiction_review_planning',
            'accepted_mapping_and_baseline_contradiction_review_execution',
            'accepted_mapping_and_baseline_suspension_planning',
            'expanded_accepted_mapping_baseline_contradiction_review_planning',
            'recapture_runner_identity_input_contract_fix_planning',
            'continued_no_write_recapture_blocker_investigation',
        ].includes(manifestJson.next_required_step)
    );
    assert.match(report, /current_user_instruction_authorizes_planning_only=true/i);
    assert.match(report, /This next step requires a new, separate, explicit no-write live recapture authorization/i);
});
