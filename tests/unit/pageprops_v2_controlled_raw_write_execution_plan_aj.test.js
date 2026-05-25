'use strict';
/* eslint-disable max-lines -- L2V3AJ planning contract is audited together. */

const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const Module = require('node:module');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_controlled_raw_write_execution_plan.js');

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

function manifest(overrides = {}) {
    return {
        batch_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        next_required_step: 'controlled_raw_match_data_write_execution_planning',
        recommended_next_step: 'Phase 5.21L2V3AJ: controlled raw_match_data write execution planning',
        final_db_write_authorization_performed: true,
        final_db_write_authorization_execution_performed: true,
        raw_write_ready_for_execution: false,
        raw_write_retry_performed: false,
        raw_write_execution_performed: false,
        raw_match_data_insert_performed: false,
        db_write_performed: false,
        requires_separate_raw_write_execution: true,
        ...overrides,
    };
}

function finalAuthArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3AI',
        phase_name: 'final_db_write_authorization_execution',
        final_db_write_authorization_execution_performed: true,
        final_db_write_authorization_performed: true,
        final_db_write_human_review_required: true,
        final_db_write_human_review_satisfied: true,
        identity_mapping_accepted_count: 50,
        baseline_accepted_count: 50,
        no_write_verified_target_count: 50,
        final_authorization_candidate_count: 50,
        final_authorization_reviewed_count: 50,
        final_authorization_accepted_count: 50,
        final_authorization_blocked_count: 0,
        candidate_v2_existing_rows: 0,
        expected_raw_match_data_after_future_write: 68,
        requires_separate_raw_write_execution: true,
        raw_write_ready_for_execution: false,
        raw_write_retry_performed: false,
        raw_write_execution_performed: false,
        raw_match_data_insert_performed: false,
        matches_write_performed: false,
        db_write_performed: false,
        network_request_performed: false,
        live_fetch_performed: false,
        detail_fetch_performed: false,
        schema_migration_performed: false,
        parser_features_training_prediction_performed: false,
        ...overrides,
    };
}

function l2v3agArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3AG',
        baseline_acceptance_performed: true,
        baseline_accepted_count: 50,
        raw_write_ready_for_execution: false,
        raw_write_retry_performed: false,
        raw_match_data_insert_performed: false,
        db_write_performed: false,
        ...overrides,
    };
}

function l2v3aeArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3AE',
        accepted_mapping_count: 50,
        raw_write_ready_for_execution: false,
        raw_write_retry_performed: false,
        raw_match_data_insert_performed: false,
        db_write_performed: false,
        ...overrides,
    };
}

function l2v3acArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3AC',
        verification_status: 'passed_no_write_source_controlled',
        verified_target_count: 50,
        raw_write_runner_blocked: true,
        raw_write_ready_for_execution: false,
        raw_write_retry_performed: false,
        raw_match_data_insert_performed: false,
        db_write_performed: false,
        ...overrides,
    };
}

function l2v3aaArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3AA',
        regenerated_target_count: 50,
        raw_write_ready_for_execution: false,
        raw_write_retry_performed: false,
        raw_match_data_insert_performed: false,
        db_write_performed: false,
        ...overrides,
    };
}

function l2v3yArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3Y',
        candidate_scope_count: 50,
        raw_write_ready_for_execution: false,
        raw_write_retry_performed: false,
        raw_match_data_insert_performed: false,
        db_write_performed: false,
        ...overrides,
    };
}

function goodDbSafetyStatus(overrides = {}) {
    return {
        source: 'test_select_only_db_safety_snapshot',
        checked_at: '2026-05-25T00:00:00Z',
        db_available: true,
        matches_count: 60,
        raw_match_data_count: 18,
        fotmob_pageprops_v2_count: 8,
        candidate_v2_existing_rows: 0,
        candidate_matches_missing_fk_count: 0,
        bookmaker_odds_history_count: 2,
        l3_features_count: 2,
        match_features_training_count: 2,
        predictions_count: 2,
        protected_tables_unchanged: true,
        unique_match_id_data_version_present: true,
        legacy_unique_match_id_absent: true,
        fk_prerequisite_satisfied: true,
        hidden_bidi_resolved: true,
        full_payload_scan_clean: true,
        ci_green: true,
        raw_write_runner_guard_ok: false,
        raw_write_runner_guard_error_count: 52,
        ...overrides,
    };
}

function runSynthetic(overrides = {}) {
    return mod.runControlledRawWriteExecutionPlanning({
        manifest: manifest(overrides.manifest || {}),
        l2v3aiArtifact: finalAuthArtifact(overrides.l2v3aiArtifact || {}),
        l2v3agArtifact: l2v3agArtifact(overrides.l2v3agArtifact || {}),
        l2v3aeArtifact: l2v3aeArtifact(overrides.l2v3aeArtifact || {}),
        l2v3acArtifact: l2v3acArtifact(overrides.l2v3acArtifact || {}),
        l2v3aaArtifact: l2v3aaArtifact(overrides.l2v3aaArtifact || {}),
        l2v3yArtifact: l2v3yArtifact(overrides.l2v3yArtifact || {}),
        dbSafetyStatus: goodDbSafetyStatus(overrides.dbSafetyStatus || {}),
        writeFiles: false,
    });
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

test('L2V3AJ is planning-only and does not perform DB or raw writes', () => {
    const result = runSynthetic();
    const artifact = result.artifact;
    const updatedManifest = result.updated_manifest;

    assert.equal(result.ok, true);
    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AJ');
    assert.equal(artifact.phase_name, 'controlled_raw_match_data_write_execution_planning');
    assert.equal(artifact.raw_write_execution_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.final_db_write_authorization_performed, true);
    assert.equal(updatedManifest.final_db_write_authorization_performed, true);
});

test('final authorization performed does not imply raw write execution and separate explicit authorization remains required', () => {
    const artifact = runSynthetic().artifact;

    assert.equal(artifact.requires_separate_raw_write_execution_authorization, true);
    assert.equal(artifact.raw_write_execution_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.match(artifact.recommended_next_step, /Phase 5.21L2V3AK/);
});

test('planned write scope is restricted to raw_match_data and protected tables remain out of scope', () => {
    const artifact = runSynthetic().artifact;

    assert.equal(artifact.planned_write_table, 'raw_match_data');
    assert.equal(artifact.planned_data_version, 'fotmob_pageprops_v2');
    assert.equal(artifact.planned_target_count, 50);
    assert.equal(artifact.planned_insert_mode, 'insert_only');
    assert.equal(artifact.protected_table_write_scope, false);
    assert.equal(artifact.transaction_plan.non_raw_table_writes_allowed, false);
});

test('expected count 18 -> 68 and transaction rollback rules are documented', () => {
    const artifact = runSynthetic().artifact;

    assert.equal(artifact.expected_raw_match_data_before_count, 18);
    assert.equal(artifact.expected_insert_count, 50);
    assert.equal(artifact.expected_raw_match_data_after_count, 68);
    assert.equal(artifact.transaction_plan.rollback_on_any_mismatch, true);
    assert.equal(artifact.transaction_plan.no_partial_commit, true);
    assert.equal(artifact.transaction_plan.commit_only_if_all_checks_pass, true);
});

test('payload source unknown keeps next step in continued planning instead of execution', () => {
    const artifact = runSynthetic().artifact;

    assert.equal(artifact.write_input_source_status, 'unknown_no_safe_payload_source_path_declared');
    assert.equal(artifact.write_input_source_unknown, true);
    assert.equal(artifact.write_input_source_paths_found.length, 0);
    assert.equal(artifact.controlled_raw_write_execution_planning_status, mod.CONTINUED_STATUS);
    assert.equal(artifact.next_required_step, 'continued_controlled_raw_write_planning');
});

test('safe payload source declaration allows planning output to point at execution phase', () => {
    const artifact = runSynthetic({
        manifest: {
            safe_payload_source_path:
                'docs/_controlled_payloads/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.safe_payloads.json',
        },
    }).artifact;

    assert.equal(artifact.write_input_source_unknown, false);
    assert.equal(artifact.write_input_source_paths_found.length, 1);
    assert.equal(artifact.controlled_raw_write_execution_planning_status, mod.READY_STATUS);
    assert.equal(artifact.next_required_step, 'controlled_raw_match_data_write_execution');
});

test('validateInputs accepts already-planned manifest when next step advanced to later AJ phases', () => {
    const validation = mod.validateInputs(
        manifest({
            phase_5_21_l2v3aj_planning_status: mod.ARTIFACT_STATUS,
            next_required_step: 'continued_controlled_raw_write_planning',
        }),
        finalAuthArtifact(),
        l2v3agArtifact(),
        l2v3aeArtifact(),
        l2v3acArtifact(),
        l2v3aaArtifact(),
        l2v3yArtifact()
    );

    assert.equal(validation.ok, true);
    assert.deepEqual(validation.errors, []);
});

test('candidate existing v2 rows, FK failures, and UNIQUE mismatch block execution planning', () => {
    const artifact = runSynthetic({
        dbSafetyStatus: {
            candidate_v2_existing_rows: 1,
            fk_prerequisite_satisfied: false,
            unique_match_id_data_version_present: false,
            legacy_unique_match_id_absent: false,
        },
    }).artifact;

    assert.equal(artifact.controlled_raw_write_execution_planning_status, mod.BLOCKED_STATUS);
    assert.equal(artifact.blocking_reasons_detected.includes('candidate_v2_raw_rows_already_exist'), true);
    assert.equal(artifact.blocking_reasons_detected.includes('fk_prerequisite_not_satisfied'), true);
    assert.equal(artifact.blocking_reasons_detected.includes('unique_constraint_missing_or_wrong'), true);
    assert.equal(artifact.next_required_step, 'controlled_raw_write_execution_blocker_resolution');
});

test('pageProps v2 count drift and protected table drift are blocked explicitly', () => {
    const artifact = runSynthetic({
        dbSafetyStatus: {
            fotmob_pageprops_v2_count: 9,
            bookmaker_odds_history_count: 3,
        },
    }).artifact;

    assert.equal(artifact.blocking_reasons_detected.includes('fotmob_pageprops_v2_count_mismatch'), true);
    assert.equal(artifact.blocking_reasons_detected.includes('protected_table_drift'), true);
    assert.equal(artifact.next_required_step, 'controlled_raw_write_execution_blocker_resolution');
});

test('missing final authorization evidence fails input validation', () => {
    const validation = mod.validateInputs(
        manifest({ final_db_write_authorization_performed: false }),
        finalAuthArtifact({ final_db_write_authorization_performed: false }),
        l2v3agArtifact(),
        l2v3aeArtifact(),
        l2v3acArtifact(),
        l2v3aaArtifact(),
        l2v3yArtifact()
    );
    const errors = validation.errors.join('\n');

    assert.equal(validation.ok, false);
    assert.match(errors, /manifest final_db_write_authorization_performed must be true/);
    assert.match(errors, /L2V3AI final_db_write_authorization_performed must be true/);
});

test('helper refuses raw write, DB write, network, write mode, and payload flags', () => {
    const parsed = mod.parseArgs([
        '--allow-db-write=yes',
        '--allow-network=yes',
        '--allow-live-fetch=yes',
        '--allow-detail-fetch=yes',
        '--allow-raw-match-data-write=yes',
        '--allow-matches-write=yes',
        '--allow-raw-write-retry=yes',
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
    assert.match(errors, /allow-raw-write-retry=yes is blocked/);
    assert.match(errors, /execute-raw-write=yes is blocked/);
    assert.match(errors, /commit-raw-write=yes is blocked/);
    assert.match(errors, /write-mode=yes is blocked/);
    assert.match(errors, /print-full-pageprops=yes is blocked/);
});

test('helper does not import network, DB, browser, proxy, harvest, odds, or child process modules on load', t => {
    installImportGuard(t);
    const loaded = loadFreshModule();
    assert.equal(typeof loaded.runControlledRawWriteExecutionPlanning, 'function');
});

test('import guard blocks forbidden modules when exercised', t => {
    installImportGuard(t);
    assert.throws(() => Module._load('pg', module, false), /blocked import: pg/);
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

test('runControlledRawWriteExecutionPlanning can write outputs to explicit temp paths', () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'l2v3aj-plan-'));
    const artifactPath = path.join(tmpDir, 'artifact.json');
    const reportPath = path.join(tmpDir, 'report.md');
    const manifestPath = path.join(tmpDir, 'manifest.json');

    try {
        const result = mod.runControlledRawWriteExecutionPlanning({
            manifest: manifest(),
            l2v3aiArtifact: finalAuthArtifact(),
            l2v3agArtifact: l2v3agArtifact(),
            l2v3aeArtifact: l2v3aeArtifact(),
            l2v3acArtifact: l2v3acArtifact(),
            l2v3aaArtifact: l2v3aaArtifact(),
            l2v3yArtifact: l2v3yArtifact(),
            dbSafetyStatus: goodDbSafetyStatus(),
            writeFiles: true,
            artifactOutputPath: artifactPath,
            reportOutputPath: reportPath,
            manifestOutputPath: manifestPath,
        });

        assert.equal(result.ok, true);
        assert.equal(JSON.parse(fs.readFileSync(artifactPath, 'utf8')).proposal_phase, 'Phase 5.21L2V3AJ');
        assert.match(fs.readFileSync(reportPath, 'utf8'), /rollback_on_any_mismatch=true/i);
        assert.equal(
            JSON.parse(fs.readFileSync(manifestPath, 'utf8')).requires_separate_raw_write_execution_authorization,
            true
        );
    } finally {
        fs.rmSync(tmpDir, { recursive: true, force: true });
    }
});

test('CLI covers help, invalid options, planning output, and no write markers', () => {
    let helpOutput = '';
    let invalidOutput = '';
    let successOutput = '';

    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'l2v3aj-cli-'));
    const dbSafetyPath = path.join(tmpDir, 'db-safety.json');
    fs.writeFileSync(dbSafetyPath, JSON.stringify(goodDbSafetyStatus(), null, 2));

    try {
        const helpStatus = mod.runCli(['--help'], { stdout: text => (helpOutput += text) });
        const invalidStatus = mod.runCli(['--unknown'], { stdout: text => (invalidOutput += text) });
        const successStatus = mod.runCli([`--db-safety-status-file=${dbSafetyPath}`, '--write-files=false'], {
            stdout: text => (successOutput += text),
        });

        assert.equal(helpStatus, 0);
        assert.match(helpOutput, /planning only/);
        assert.match(helpOutput, /db-safety-status-file/);
        assert.equal(invalidStatus, 2);
        assert.match(invalidOutput, /unknown arguments/);
        assert.equal(successStatus, 0);
        assert.match(successOutput, /"planned_write_table": "raw_match_data"/);
        assert.match(successOutput, /"raw_write_execution_performed": false/);
        assert.match(successOutput, /"db_write_performed": false/);
        assert.match(successOutput, /"raw_match_data_insert_performed": false/);
        assert.match(successOutput, /"requires_separate_raw_write_execution_authorization": true/);
    } finally {
        fs.rmSync(tmpDir, { recursive: true, force: true });
    }
});

test('CLI returns status 3 when source-controlled manifest state is invalid', () => {
    const originalReadFileSync = fs.readFileSync;
    let output = '';

    fs.readFileSync = function patchedReadFileSync(filePath, ...rest) {
        if (String(filePath).endsWith(mod.MANIFEST_PATH)) {
            return JSON.stringify(manifest({ next_required_step: 'wrong-step' }), null, 2);
        }
        return originalReadFileSync.call(this, filePath, ...rest);
    };

    try {
        const status = mod.runCli(['--write-files=false'], { stdout: text => (output += text) });
        assert.equal(status, 3);
        assert.match(output, /manifest next_required_step must be controlled_raw_match_data_write_execution_planning/);
    } finally {
        fs.readFileSync = originalReadFileSync;
    }
});

test('script entrypoint prints help without writes when executed as main module', () => {
    const result = spawnSync(process.execPath, [MODULE_PATH, '--help'], {
        cwd: PROJECT_ROOT,
        encoding: 'utf8',
    });

    assert.equal(result.status, 0);
    assert.match(result.stdout, /planning only/i);
    assert.equal(result.stderr, '');
});

test('repository L2V3AJ artifacts preserve planning-only semantics when generated', () => {
    const artifactPath =
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.controlled_raw_match_data_write_execution_plan.phase521l2v3aj.json';
    if (!fs.existsSync(path.join(PROJECT_ROOT, artifactPath))) return;

    const manifestJson = readJson('docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json');
    const artifact = readJson(artifactPath);
    const report = readText('docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AJ.md');

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AJ');
    assert.equal(artifact.planning_only, true);
    assert.equal(artifact.raw_write_execution_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.final_db_write_authorization_performed, true);
    assert.equal(artifact.planned_write_table, 'raw_match_data');
    assert.equal(artifact.planned_target_count, 50);
    assert.equal(artifact.expected_raw_match_data_after_count, 68);
    assert.equal(manifestJson.final_db_write_authorization_performed, true);
    assert.equal(manifestJson.requires_separate_raw_write_execution_authorization, true);
    assert.equal(
        [
            'continued_controlled_raw_write_planning',
            'controlled_raw_match_data_write_execution',
            'controlled_raw_write_execution_blocker_resolution',
            'controlled_payload_source_declaration_planning',
            'controlled_payload_source_declaration_execution',
            'controlled_no_write_payload_recapture_planning',
            'controlled_no_write_payload_recapture_execution',
        ].includes(manifestJson.next_required_step),
        true
    );
    assert.match(report, /safe_metadata_and_counts_only=true/i);
});
