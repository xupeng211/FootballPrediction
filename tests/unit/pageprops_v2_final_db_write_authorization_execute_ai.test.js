'use strict';
/* eslint-disable max-lines -- L2V3AI safety contract is audited together. */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const Module = require('node:module');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_final_db_write_authorization_execute.js');

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

function target(index, overrides = {}) {
    const externalId = String(9400001 + index);
    return {
        target_id: `fotmob-pageprops-v2-ligue1-2025-2026-profile-001:53_20252026_${externalId}`,
        match_id: `53_20252026_${externalId}`,
        schedule_external_id: externalId,
        source_page_url: `/matches/home-${index}-away-${index}/route-${index}#${externalId}`,
        source_page_url_base: `/matches/home-${index}-away-${index}/route-${index}`,
        source_url_fragment_external_id: externalId,
        source_inventory_record_key: `l1_api_data_leagues:overview.leagueOverviewMatches.${index}:${externalId}`,
        ...overrides,
    };
}

function finalAuthorizationPlanEntry(index, overrides = {}) {
    return {
        ...target(index),
        raw_data_version: 'fotmob_pageprops_v2',
        final_authorization_status: 'final_authorization_ready',
        final_db_write_authorization_performed: false,
        raw_write_ready_for_execution: false,
        raw_write_retry_performed: false,
        raw_write_execution_performed: false,
        final_authorization_blockers: [],
        final_authorization_evidence_summary: {
            identity_mapping_accepted: true,
            baseline_accepted: true,
            no_write_verification_passed: true,
            existing_candidate_v2_raw_rows_zero: true,
            raw_match_data_before_count_expected: true,
            unique_match_id_data_version_present: true,
            legacy_unique_match_id_absent: true,
            fk_prerequisite_satisfied: true,
            protected_tables_unchanged: true,
        },
        ...overrides,
    };
}

function manifest(overrides = {}) {
    return {
        batch_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        next_required_step: 'final_db_write_authorization_execution',
        recommended_next_step: 'Phase 5.21L2V3AI: final DB-write authorization execution',
        phase_5_21_l2v3ah_planning_status: 'completed_final_db_write_authorization_planning',
        phase_5_21_l2v3ah_final_authorization_ready_count: 50,
        baseline_acceptance_performed: true,
        baseline_accepted_count: 50,
        final_db_write_authorization_execution_performed: false,
        final_db_write_authorization_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        requires_separate_final_db_write_authorization_execution: true,
        ...overrides,
    };
}

function l2v3ahPlan(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3AH',
        phase_name: 'final_db_write_authorization_planning',
        planning_status: 'completed_final_db_write_authorization_planning',
        identity_mapping_accepted_count: 50,
        baseline_accepted_count: 50,
        no_write_verified_target_count: 50,
        final_authorization_candidate_count: 50,
        final_authorization_ready_count: 50,
        final_authorization_blocked_count: 0,
        final_db_write_reviewer_required: true,
        final_db_write_authorization_execution_performed: false,
        final_db_write_authorization_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        expected_raw_match_data_before_count: 18,
        expected_raw_match_data_after_count: 68,
        final_authorization_entries: Array.from({ length: 50 }, (_, index) => finalAuthorizationPlanEntry(index)),
        ...overrides,
    };
}

function l2v3agArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3AG',
        phase_name: 'baseline_acceptance_execution',
        baseline_acceptance_performed: true,
        baseline_accepted_count: 50,
        baseline_blocked_count: 0,
        final_db_write_authorization_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        ...overrides,
    };
}

function l2v3aeArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3AE',
        accepted_mapping_count: 50,
        blocked_mapping_count: 0,
        final_db_write_authorization_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        ...overrides,
    };
}

function l2v3acArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3AC',
        verification_status: 'passed_no_write_source_controlled',
        verified_target_count: 50,
        failed_target_count: 0,
        raw_write_runner_blocked: true,
        final_db_write_authorization_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        ...overrides,
    };
}

function l2v3aaArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3AA',
        regenerated_target_count: 50,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        ...overrides,
    };
}

function l2v3yArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3Y',
        candidate_scope_count: 50,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
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
    return mod.runFinalDbWriteAuthorizationExecution({
        manifest: manifest(overrides.manifest || {}),
        l2v3ahPlan: l2v3ahPlan(overrides.l2v3ahPlan || {}),
        l2v3agArtifact: l2v3agArtifact(overrides.l2v3agArtifact || {}),
        l2v3aeArtifact: l2v3aeArtifact(overrides.l2v3aeArtifact || {}),
        l2v3acArtifact: l2v3acArtifact(overrides.l2v3acArtifact || {}),
        l2v3aaArtifact: l2v3aaArtifact(overrides.l2v3aaArtifact || {}),
        l2v3yArtifact: l2v3yArtifact(overrides.l2v3yArtifact || {}),
        dbSafetyStatus: goodDbSafetyStatus(overrides.dbSafetyStatus || {}),
        finalDbWriteHumanReviewSatisfied: overrides.finalDbWriteHumanReviewSatisfied === true,
        authorizedBy: overrides.authorizedBy || 'codex_test_authorizer',
        authorizedAt: overrides.authorizedAt || '2026-05-25T00:00:00Z',
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

test('L2V3AI is final DB-write authorization execution and does not perform DB or raw writes', () => {
    const result = runSynthetic({ finalDbWriteHumanReviewSatisfied: true });
    const artifact = result.artifact;
    const updatedManifest = result.updated_manifest;

    assert.equal(result.ok, true);
    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AI');
    assert.equal(artifact.phase_name, 'final_db_write_authorization_execution');
    assert.equal(artifact.final_db_write_authorization_execution_performed, true);
    assert.equal(artifact.final_db_write_authorization_performed, true);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.raw_write_retry_performed, false);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(updatedManifest.final_db_write_authorization_performed, true);
    assert.equal(updatedManifest.raw_write_ready_for_execution, false);
});

test('user final authorization execution does not authorize raw write execution', () => {
    const artifact = runSynthetic({ finalDbWriteHumanReviewSatisfied: true }).artifact;

    assert.equal(artifact.final_db_write_human_review_satisfied, true);
    assert.equal(artifact.authorization_evidence_summary.user_authorized_final_db_write_authorization_execution, true);
    assert.equal(
        artifact.authorization_evidence_summary.user_did_not_authorize_raw_write_execution_in_this_phase,
        true
    );
    assert.equal(artifact.safety_contract.final_authorization_is_not_raw_write_execution, true);
    assert.equal(artifact.safety_contract.requires_separate_raw_write_execution, true);
    assert.equal(artifact.requires_separate_raw_write_execution, true);
    assert.match(artifact.recommended_next_step, /Phase 5.21L2V3AJ/);
});

test('missing human final authorization blocks performed authorization', () => {
    const artifact = runSynthetic().artifact;

    assert.equal(artifact.final_db_write_authorization_performed, false);
    assert.equal(artifact.final_db_write_human_review_satisfied, false);
    assert.equal(artifact.final_authorization_accepted_count, 0);
    assert.equal(artifact.final_authorization_blocked_count, 50);
    assert.equal(
        artifact.final_authorization_entries.every(entry =>
            entry.final_authorization_blockers.includes('human_final_authorization_missing')
        ),
        true
    );
    assert.equal(artifact.raw_write_ready_for_execution, false);
});

test('missing upstream identity mapping, baseline acceptance, and no-write verification fail closed', () => {
    const validation = mod.validateInputs(
        manifest(),
        l2v3ahPlan({
            identity_mapping_accepted_count: 49,
            baseline_accepted_count: 49,
            no_write_verified_target_count: 49,
        }),
        l2v3agArtifact({ baseline_acceptance_performed: false, baseline_accepted_count: 49 }),
        l2v3aeArtifact({ accepted_mapping_count: 49 }),
        l2v3acArtifact({ verification_status: 'failed', verified_target_count: 49, raw_write_runner_blocked: false }),
        l2v3aaArtifact({ regenerated_target_count: 49 }),
        l2v3yArtifact({ candidate_scope_count: 49 })
    );
    const errors = validation.errors.join('\n');

    assert.equal(validation.ok, false);
    assert.match(errors, /identity_mapping_accepted_count must be 50/);
    assert.match(errors, /baseline_accepted_count must be 50/);
    assert.match(errors, /no_write_verified_target_count must be 50/);
    assert.match(errors, /L2V3AG baseline_acceptance_performed must be true/);
    assert.match(errors, /L2V3AE accepted_mapping_count must be 50/);
    assert.match(errors, /L2V3AC verification_status/);
    assert.match(errors, /L2V3AA regenerated_target_count must be 50/);
    assert.match(errors, /L2V3Y candidate_scope_count must be 50/);
});

test('DB safety blockers prevent final authorization without writes', () => {
    const artifact = runSynthetic({
        finalDbWriteHumanReviewSatisfied: true,
        dbSafetyStatus: {
            matches_count: 59,
            raw_match_data_count: 19,
            fotmob_pageprops_v2_count: 9,
            candidate_v2_existing_rows: 1,
            bookmaker_odds_history_count: 3,
            unique_match_id_data_version_present: false,
            fk_prerequisite_satisfied: false,
            protected_tables_unchanged: false,
        },
    }).artifact;
    const blockers = artifact.final_authorization_entries.flatMap(entry => entry.final_authorization_blockers);

    assert.equal(artifact.final_db_write_authorization_performed, false);
    assert.equal(artifact.final_authorization_blocked_count, 50);
    assert.equal(blockers.includes('matches_count_mismatch'), true);
    assert.equal(blockers.includes('raw_match_data_before_count_mismatch'), true);
    assert.equal(blockers.includes('fotmob_pageprops_v2_count_mismatch'), true);
    assert.equal(blockers.includes('candidate_v2_raw_rows_already_exist'), true);
    assert.equal(blockers.includes('protected_table_drift'), true);
    assert.equal(blockers.includes('unique_constraint_missing_or_wrong'), true);
    assert.equal(blockers.includes('fk_prerequisite_not_satisfied'), true);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
});

test('missing explicit DB safety evidence fails closed', () => {
    const artifact = mod.runFinalDbWriteAuthorizationExecution({
        manifest: manifest(),
        l2v3ahPlan: l2v3ahPlan(),
        l2v3agArtifact: l2v3agArtifact(),
        l2v3aeArtifact: l2v3aeArtifact(),
        l2v3acArtifact: l2v3acArtifact(),
        l2v3aaArtifact: l2v3aaArtifact(),
        l2v3yArtifact: l2v3yArtifact(),
        finalDbWriteHumanReviewSatisfied: true,
        authorizedBy: 'codex_test_authorizer',
        authorizedAt: '2026-05-25T00:00:00Z',
        writeFiles: false,
    }).artifact;

    const blockers = artifact.final_authorization_entries.flatMap(entry => entry.final_authorization_blockers);
    assert.equal(artifact.final_db_write_authorization_performed, false);
    assert.equal(blockers.includes('db_unavailable'), true);
    assert.equal(blockers.includes('matches_count_mismatch'), true);
    assert.equal(blockers.includes('raw_match_data_before_count_mismatch'), true);
    assert.equal(blockers.includes('hidden_bidi_unresolved'), true);
    assert.equal(blockers.includes('ci_not_green'), true);
});

test('helper refuses DB write, raw write retry, raw write ready, network, and payload flags', () => {
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
        '--mark-raw-write-ready=yes',
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
    assert.match(errors, /mark-raw-write-ready=yes is blocked/);
    assert.match(errors, /print-full-pageprops=yes is blocked/);
});

test('helper does not import network, DB, browser, proxy, harvest, odds, or child process modules on load', t => {
    installImportGuard(t);
    const loaded = loadFreshModule();
    assert.equal(typeof loaded.runFinalDbWriteAuthorizationExecution, 'function');
});

test('outputs avoid full raw data, pageProps, source body, and HTML payloads', () => {
    const result = runSynthetic({ finalDbWriteHumanReviewSatisfied: true });
    for (const text of [JSON.stringify(result.artifact), result.report, JSON.stringify(result.updated_manifest)]) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
        assert.equal(text.includes('"source_body":'), false);
        assert.equal(text.includes('"full_json":'), false);
    }
});

test('runFinalDbWriteAuthorizationExecution can write outputs to explicit temp paths', () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'l2v3ai-final-db-write-auth-exec-'));
    const artifactPath = path.join(tmpDir, 'artifact.json');
    const reportPath = path.join(tmpDir, 'report.md');
    const manifestPath = path.join(tmpDir, 'manifest.json');

    try {
        const result = mod.runFinalDbWriteAuthorizationExecution({
            manifest: manifest(),
            l2v3ahPlan: l2v3ahPlan(),
            l2v3agArtifact: l2v3agArtifact(),
            l2v3aeArtifact: l2v3aeArtifact(),
            l2v3acArtifact: l2v3acArtifact(),
            l2v3aaArtifact: l2v3aaArtifact(),
            l2v3yArtifact: l2v3yArtifact(),
            dbSafetyStatus: goodDbSafetyStatus(),
            finalDbWriteHumanReviewSatisfied: true,
            authorizedBy: 'codex_test_authorizer',
            authorizedAt: '2026-05-25T00:00:00Z',
            writeFiles: true,
            artifactOutputPath: artifactPath,
            reportOutputPath: reportPath,
            manifestOutputPath: manifestPath,
        });

        assert.equal(result.ok, true);
        assert.equal(JSON.parse(fs.readFileSync(artifactPath, 'utf8')).proposal_phase, 'Phase 5.21L2V3AI');
        assert.match(fs.readFileSync(reportPath, 'utf8'), /final authorization is not raw write execution/i);
        assert.equal(JSON.parse(fs.readFileSync(manifestPath, 'utf8')).raw_write_ready_for_execution, false);
    } finally {
        fs.rmSync(tmpDir, { recursive: true, force: true });
    }
});

test('CLI covers help, invalid options, authorized execution output, and no write markers', () => {
    let helpOutput = '';
    let invalidOutput = '';
    let successOutput = '';

    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'l2v3ai-final-db-write-auth-cli-'));
    const dbSafetyPath = path.join(tmpDir, 'db-safety.json');
    fs.writeFileSync(dbSafetyPath, JSON.stringify(goodDbSafetyStatus(), null, 2));

    try {
        const helpStatus = mod.runCli(['--help'], { stdout: text => (helpOutput += text) });
        const invalidStatus = mod.runCli(['--unknown'], { stdout: text => (invalidOutput += text) });
        const successStatus = mod.runCli(
            [
                '--write-files=false',
                '--final-db-write-human-review-satisfied=yes',
                '--authorized-by=codex_test_authorizer',
                `--db-safety-status-file=${dbSafetyPath}`,
            ],
            { stdout: text => (successOutput += text) }
        );

        assert.equal(helpStatus, 0);
        assert.match(helpOutput, /final DB-write authorization execution only/);
        assert.match(helpOutput, /db-safety-status-file/);
        assert.equal(invalidStatus, 2);
        assert.match(invalidOutput, /unknown arguments/);
        assert.equal(successStatus, 0);
        assert.match(successOutput, /"final_db_write_authorization_performed": true/);
        assert.match(successOutput, /"raw_match_data_insert_performed": false/);
        assert.match(successOutput, /"raw_write_retry_performed": false/);
        assert.match(successOutput, /"raw_write_ready_for_execution": false/);
        assert.match(successOutput, /"requires_separate_raw_write_execution": true/);
    } finally {
        fs.rmSync(tmpDir, { recursive: true, force: true });
    }
});

test('repository L2V3AI artifacts preserve final authorization without raw write when generated', () => {
    const artifactPath =
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.final_db_write_authorization_result.phase521l2v3ai.json';
    if (!fs.existsSync(path.join(PROJECT_ROOT, artifactPath))) return;

    const manifestJson = readJson('docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json');
    const artifact = readJson(artifactPath);
    const report = readText('docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AI.md');

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AI');
    assert.equal(artifact.final_db_write_authorization_execution_performed, true);
    assert.equal(artifact.final_db_write_authorization_performed, true);
    assert.equal(artifact.final_authorization_accepted_count, 50);
    assert.equal(artifact.final_authorization_blocked_count, 0);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.raw_write_retry_performed, false);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.requires_separate_raw_write_execution, true);
    assert.equal(manifestJson.final_db_write_authorization_performed, true);
    assert.equal(manifestJson.raw_write_ready_for_execution, false);
    assert.equal(manifestJson.requires_separate_raw_write_execution, true);
    assert.match(report, /user did not authorize raw write retry/i);
});
