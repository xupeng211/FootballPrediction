'use strict';
/* eslint-disable max-lines -- L2V3AH safety contract is audited together. */

const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const Module = require('node:module');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_final_db_write_authorization_plan.js');

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
        schedule_date: '2025-08-15T18:45:00.000Z',
        schedule_home_team: `Home ${index}`,
        schedule_away_team: `Away ${index}`,
        source_inventory_record_key: `l1_api_data_leagues:overview.leagueOverviewMatches.${index}:${externalId}`,
        ...overrides,
    };
}

function baselineEntry(index, overrides = {}) {
    return {
        ...target(index),
        identity_mapping_acceptance_status: 'accepted_identity_mapping',
        baseline_status: 'baseline_accepted',
        baseline_acceptance_status: 'accepted_enriched_baseline_metadata',
        baseline_acceptance_execution_performed: true,
        baseline_accepted: true,
        baseline_accepted_by: 'codex_test_reviewer',
        baseline_accepted_at: '2026-05-22T16:30:00Z',
        baseline_acceptance_blockers: [],
        baseline_acceptance_evidence_summary: {
            identity_mapping_accepted: true,
            no_write_verification_passed: true,
            source_url_evidence_complete: true,
            raw_write_runner_remains_blocked: true,
            final_db_write_authorization_performed: false,
        },
        baseline_accepted_does_not_authorize_raw_write: true,
        raw_write_eligible_after_baseline_acceptance: false,
        ...overrides,
    };
}

function identityEntry(index, overrides = {}) {
    return {
        ...target(index),
        acceptance_status: 'accepted_identity_mapping',
        review_result: 'accepted_identity_mapping',
        accepted_by: 'codex_test_reviewer',
        accepted_at: '2026-05-22T10:30:00Z',
        ...overrides,
    };
}

function verificationResult(index, overrides = {}) {
    const base = target(index);
    return {
        target_id: base.target_id,
        match_id: base.match_id,
        schedule_external_id: base.schedule_external_id,
        source_url_fragment_external_id: base.source_url_fragment_external_id,
        verification_status: 'verified',
        failure_reasons: [],
        ...overrides,
    };
}

function enrichedTarget(index, overrides = {}) {
    return {
        ...target(index),
        external_id: target(index).schedule_external_id,
        regeneration_status: 'regenerated_no_write',
        regeneration_blockers: [],
        raw_write_ready_for_execution: false,
        ...overrides,
    };
}

function manifest(overrides = {}) {
    return {
        batch_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        next_required_step: 'final_db_write_authorization_planning',
        recommended_next_step: 'Phase 5.21L2V3AH: final DB-write authorization planning',
        phase_5_21_l2v3ag_execution_status: 'completed_baseline_acceptance_execution',
        phase_5_21_l2v3ag_baseline_accepted_count: 50,
        baseline_acceptance_performed: true,
        baseline_accepted_count: 50,
        final_db_write_authorization_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        requires_separate_final_db_write_authorization: true,
        ...overrides,
    };
}

function l2v3agArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3AG',
        phase_name: 'baseline_acceptance_execution',
        baseline_acceptance_execution_performed: true,
        baseline_acceptance_performed: true,
        baseline_review_candidate_count: 50,
        baseline_reviewed_target_count: 50,
        baseline_accepted_count: 50,
        baseline_rejected_count: 0,
        baseline_blocked_count: 0,
        baseline_human_review_required: true,
        baseline_human_review_satisfied: true,
        raw_write_retry_performed: false,
        final_db_write_authorization_performed: false,
        raw_write_ready_for_execution: false,
        requires_separate_final_db_write_authorization: true,
        baseline_entries: Array.from({ length: 50 }, (_, index) => baselineEntry(index)),
        ...overrides,
    };
}

function l2v3aeArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3AE',
        phase_name: 'identity_mapping_acceptance_review_execution',
        acceptance_review_execution_performed: true,
        accepted_mapping_count: 50,
        rejected_mapping_count: 0,
        blocked_mapping_count: 0,
        human_review_required: true,
        human_review_satisfied: true,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        review_entries: Array.from({ length: 50 }, (_, index) => identityEntry(index)),
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
        raw_write_ready_for_execution: false,
        verification_analysis: {
            target_results: Array.from({ length: 50 }, (_, index) => verificationResult(index)),
        },
        ...overrides,
    };
}

function l2v3aaArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3AA',
        regenerated_target_count: 50,
        raw_write_ready_for_execution: false,
        enriched_targets: Array.from({ length: 50 }, (_, index) => enrichedTarget(index)),
        ...overrides,
    };
}

function l2v3yArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3Y',
        candidate_scope_count: 50,
        db_write_performed: false,
        raw_write_ready_for_execution: false,
        ...overrides,
    };
}

function runSynthetic(overrides = {}) {
    return mod.runFinalDbWriteAuthorizationPlanning({
        manifest: manifest(overrides.manifest || {}),
        l2v3agArtifact: l2v3agArtifact(overrides.l2v3agArtifact || {}),
        l2v3aeArtifact: l2v3aeArtifact(overrides.l2v3aeArtifact || {}),
        l2v3acArtifact: l2v3acArtifact(overrides.l2v3acArtifact || {}),
        l2v3aaArtifact: l2v3aaArtifact(overrides.l2v3aaArtifact || {}),
        l2v3yArtifact: l2v3yArtifact(overrides.l2v3yArtifact || {}),
        dbSafetyStatus: overrides.dbSafetyStatus || {},
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

test('L2V3AH is final DB-write authorization planning-only and does not perform authorization', () => {
    const result = runSynthetic();
    const artifact = result.artifact;
    const updatedManifest = result.updated_manifest;

    assert.equal(result.ok, true);
    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AH');
    assert.equal(artifact.phase_name, 'final_db_write_authorization_planning');
    assert.equal(artifact.planning_only, true);
    assert.equal(artifact.final_db_write_authorization_execution_performed, false);
    assert.equal(artifact.final_db_write_authorization_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.matches_external_id_modified, false);
    assert.equal(artifact.raw_write_retry_performed, false);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(updatedManifest.final_db_write_authorization_performed, false);
    assert.equal(updatedManifest.raw_write_ready_for_execution, false);
});

test('baseline accepted and final authorization ready do not imply performed authorization or raw write', () => {
    const artifact = runSynthetic().artifact;
    const firstEntry = artifact.final_authorization_entries[0];

    assert.equal(artifact.baseline_accepted_count, 50);
    assert.equal(artifact.final_authorization_ready_count, 50);
    assert.equal(artifact.final_authorization_blocked_count, 0);
    assert.equal(artifact.final_db_write_authorization_performed, false);
    assert.equal(artifact.raw_write_authorization_performed, false);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(firstEntry.final_authorization_status, 'final_authorization_ready');
    assert.equal(firstEntry.final_db_write_authorization_performed, false);
    assert.equal(firstEntry.raw_write_ready_for_execution, false);
    assert.equal(artifact.safety_contract.baseline_accepted_does_not_imply_final_db_write_authorization, true);
    assert.equal(artifact.safety_contract.final_authorization_ready_does_not_imply_final_authorization_performed, true);
});

test('write scope is restricted to future raw_match_data pageProps v2 inserts and protected tables stay out of scope', () => {
    const artifact = runSynthetic().artifact;

    assert.equal(artifact.write_scope.planning_only_current_phase, true);
    assert.equal(artifact.write_scope.future_execution_scope_table, 'raw_match_data');
    assert.equal(artifact.write_scope.future_execution_data_version, 'fotmob_pageprops_v2');
    assert.equal(artifact.write_scope.future_execution_target_count, 50);
    assert.equal(artifact.non_write_scope.no_matches_write, true);
    assert.equal(artifact.non_write_scope.no_matches_external_id_change, true);
    assert.equal(artifact.non_write_scope.no_schema_migration, true);
    assert.equal(artifact.non_write_scope.no_parser_features_training_prediction, true);
});

test('expected before and after row counts and runner guard stay documented without marking raw-write ready', () => {
    const artifact = runSynthetic().artifact;

    assert.equal(artifact.expected_raw_match_data_before_count, 18);
    assert.equal(artifact.expected_raw_match_data_after_count, 68);
    assert.equal(artifact.expected_raw_match_data_delta_count, 50);
    assert.equal(artifact.expected_fotmob_pageprops_v2_before_count, 8);
    assert.equal(artifact.expected_fotmob_pageprops_v2_after_count, 58);
    assert.equal(artifact.raw_write_runner_guard_status.ok, false);
    assert.equal(artifact.raw_write_runner_guard_status.error_count, 52);
    assert.equal(artifact.raw_write_runner_guard_status.blocked_until_final_authorization_execution, true);
    assert.equal(artifact.raw_write_ready_for_execution, false);
});

test('blocking criteria prevent final authorization readiness without performing writes', () => {
    const duplicate = baselineEntry(0);
    const blockedArtifact = runSynthetic({
        l2v3agArtifact: {
            baseline_entries: Array.from({ length: 50 }, (_, index) =>
                baselineEntry(
                    index,
                    index === 1
                        ? { source_inventory_record_key: duplicate.source_inventory_record_key }
                        : index === 2
                          ? { baseline_accepted: false }
                          : {}
                )
            ),
        },
        l2v3acArtifact: {
            verification_analysis: {
                target_results: Array.from({ length: 50 }, (_, index) =>
                    verificationResult(index, index === 3 ? { verification_status: 'failed' } : {})
                ),
            },
        },
        dbSafetyStatus: {
            raw_match_data_count: 19,
            candidate_v2_raw_rows_existing_count: 1,
            unique_match_id_data_version_present: false,
        },
    }).artifact;
    const blockers = blockedArtifact.final_authorization_entries.flatMap(entry => entry.final_authorization_blockers);

    assert.equal(blockedArtifact.final_authorization_ready_count < 50, true);
    assert.equal(blockedArtifact.final_db_write_authorization_performed, false);
    assert.equal(blockedArtifact.raw_write_ready_for_execution, false);
    assert.equal(blockers.includes('baseline_not_accepted'), true);
    assert.equal(blockers.includes('duplicate_or_conflicting_identity_key'), true);
    assert.equal(blockers.includes('no_write_verification_not_passed'), true);
    assert.equal(blockers.includes('raw_match_data_before_count_mismatch'), true);
    assert.equal(blockers.includes('candidate_v2_raw_rows_already_exist'), true);
    assert.equal(blockers.includes('unique_constraint_missing_or_wrong'), true);
});

test('identity review rejection blocks final authorization planning entries explicitly', () => {
    const blockedArtifact = runSynthetic({
        l2v3aeArtifact: {
            review_entries: Array.from({ length: 50 }, (_, index) =>
                identityEntry(index, {
                    acceptance_status: 'blocked_identity_mapping',
                    review_result: 'blocked_identity_mapping',
                })
            ),
        },
    }).artifact;
    const blockers = blockedArtifact.final_authorization_entries.flatMap(entry => entry.final_authorization_blockers);

    assert.equal(blockers.includes('identity_mapping_not_accepted'), true);
    assert.equal(blockedArtifact.final_authorization_ready_count < 50, true);
});

test('artifact stays in continued planning when readiness count is inconsistent without blockers', () => {
    const artifact = mod.buildArtifact({
        loaded: {
            manifest: manifest(),
            l2v3agArtifact: l2v3agArtifact(),
            l2v3aeArtifact: l2v3aeArtifact(),
            l2v3acArtifact: l2v3acArtifact(),
            l2v3aaArtifact: l2v3aaArtifact(),
            l2v3yArtifact: l2v3yArtifact(),
        },
        plan: {
            baseline_accepted_count: 50,
            identity_mapping_accepted_count: 50,
            no_write_verified_target_count: 50,
            enriched_target_count: 50,
            final_authorization_candidate_count: 50,
            final_authorization_ready_count: 49,
            final_authorization_blocked_count: 0,
            final_authorization_blocker_count: 0,
            final_authorization_entries: [],
            db_safety_status: {
                raw_match_data_count: 18,
                candidate_v2_raw_rows_existing_count: 0,
                unique_match_id_data_version_present: true,
                legacy_unique_match_id_absent: true,
                fk_prerequisite_satisfied: true,
                protected_tables_unchanged: true,
                raw_write_runner_guard_ok: false,
                raw_write_runner_guard_error_count: 52,
            },
        },
    });

    assert.equal(artifact.planning_status, mod.ARTIFACT_STATUS);
    assert.equal(artifact.next_required_step, 'continued_final_db_write_authorization_planning');
});

test('input validation fails closed on missing upstream acceptance and unsafe write state', () => {
    const alreadyPlanned = mod.validateInputs(
        manifest({
            phase_5_21_l2v3ah_planning_status: 'completed_final_db_write_authorization_planning',
            next_required_step: 'final_db_write_authorization_execution',
        }),
        l2v3agArtifact(),
        l2v3aeArtifact(),
        l2v3acArtifact(),
        l2v3aaArtifact(),
        l2v3yArtifact()
    );
    assert.equal(alreadyPlanned.ok, true);

    const validation = mod.validateInputs(
        manifest({
            next_required_step: 'raw_write_retry',
            phase_5_21_l2v3ag_execution_status: 'missing',
            phase_5_21_l2v3ag_baseline_accepted_count: 49,
            final_db_write_authorization_performed: true,
            raw_write_ready_for_execution: true,
        }),
        l2v3agArtifact({
            proposal_phase: 'Phase 5.21L2V3AF',
            baseline_acceptance_performed: false,
            baseline_accepted_count: 49,
            baseline_blocked_count: 1,
            baseline_human_review_satisfied: false,
            final_db_write_authorization_performed: true,
        }),
        l2v3aeArtifact({
            accepted_mapping_count: 49,
            blocked_mapping_count: 1,
            human_review_satisfied: false,
            db_write_performed: true,
        }),
        l2v3acArtifact({
            verification_status: 'failed',
            verified_target_count: 49,
            failed_target_count: 1,
            raw_write_runner_blocked: false,
        }),
        l2v3aaArtifact({
            regenerated_target_count: 49,
            raw_write_retry_performed: true,
        }),
        l2v3yArtifact({
            candidate_scope_count: 49,
            raw_match_data_insert_performed: true,
        })
    );
    const errors = validation.errors.join('\n');

    assert.equal(validation.ok, false);
    assert.match(errors, /manifest next_required_step/);
    assert.match(errors, /phase_5_21_l2v3ag_execution_status/);
    assert.match(errors, /L2V3AG artifact is required/);
    assert.match(errors, /L2V3AE accepted_mapping_count must be 50/);
    assert.match(errors, /L2V3AC verification_status/);
    assert.match(errors, /L2V3AA regenerated_target_count must be 50/);
    assert.match(errors, /L2V3Y candidate_scope_count must be 50/);
    assert.match(errors, /raw-write, final authorization, or raw-ready state/);
});

test('helper refuses final authorization execution, DB write, raw write retry, network, and payload flags', () => {
    const parsed = mod.parseArgs([
        '--allow-db-write=yes',
        '--allow-network=yes',
        '--allow-live-fetch=yes',
        '--allow-detail-fetch=yes',
        '--allow-raw-match-data-write=yes',
        '--allow-matches-write=yes',
        '--execute-final-db-write-authorization=yes',
        '--authorize-final-db-write=yes',
        '--perform-final-authorization=yes',
        '--allow-raw-write-retry=yes',
        '--execute-raw-write=yes',
        '--mark-raw-write-ready=yes',
        '--print-full-pageprops=yes',
    ]);
    const validation = mod.validateCliOptions(parsed);
    const errors = validation.errors.join('\n');

    assert.equal(validation.ok, false);
    assert.match(errors, /allow-db-write=yes is blocked/);
    assert.match(errors, /allow-live-fetch=yes is blocked/);
    assert.match(errors, /allow-detail-fetch=yes is blocked/);
    assert.match(errors, /execute-final-db-write-authorization=yes is blocked/);
    assert.match(errors, /authorize-final-db-write=yes is blocked/);
    assert.match(errors, /allow-raw-write-retry=yes is blocked/);
    assert.match(errors, /execute-raw-write=yes is blocked/);
    assert.match(errors, /mark-raw-write-ready=yes is blocked/);
    assert.match(errors, /print-full-pageprops=yes is blocked/);
});

test('helper does not import network, DB, browser, proxy, harvest, odds, or child process modules on load', t => {
    installImportGuard(t);
    const loaded = loadFreshModule();
    assert.equal(typeof loaded.runFinalDbWriteAuthorizationPlanning, 'function');
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

test('runFinalDbWriteAuthorizationPlanning can write outputs to explicit temp paths', () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'l2v3ah-final-db-write-auth-plan-'));
    const artifactPath = path.join(tmpDir, 'artifact.json');
    const reportPath = path.join(tmpDir, 'report.md');
    const manifestPath = path.join(tmpDir, 'manifest.json');

    try {
        const result = mod.runFinalDbWriteAuthorizationPlanning({
            manifest: manifest(),
            l2v3agArtifact: l2v3agArtifact(),
            l2v3aeArtifact: l2v3aeArtifact(),
            l2v3acArtifact: l2v3acArtifact(),
            l2v3aaArtifact: l2v3aaArtifact(),
            l2v3yArtifact: l2v3yArtifact(),
            writeFiles: true,
            artifactOutputPath: artifactPath,
            reportOutputPath: reportPath,
            manifestOutputPath: manifestPath,
        });

        assert.equal(result.ok, true);
        assert.equal(JSON.parse(fs.readFileSync(artifactPath, 'utf8')).proposal_phase, 'Phase 5.21L2V3AH');
        assert.match(
            fs.readFileSync(reportPath, 'utf8'),
            /final_authorization_ready is not final authorization performed/i
        );
        assert.equal(JSON.parse(fs.readFileSync(manifestPath, 'utf8')).raw_write_ready_for_execution, false);
    } finally {
        fs.rmSync(tmpDir, { recursive: true, force: true });
    }
});

test('CLI covers help, invalid options, and planning output without writes', () => {
    let helpOutput = '';
    let invalidOutput = '';
    let successOutput = '';

    const helpStatus = mod.runCli(['--help'], { stdout: text => (helpOutput += text) });
    const invalidStatus = mod.runCli(['--unknown'], { stdout: text => (invalidOutput += text) });
    const successStatus = mod.runCli(['--write-files=false'], { stdout: text => (successOutput += text) });

    assert.equal(helpStatus, 0);
    assert.match(helpOutput, /final DB-write authorization planning only/);
    assert.equal(invalidStatus, 2);
    assert.match(invalidOutput, /unknown arguments/);
    assert.equal(successStatus, 0);
    assert.match(successOutput, /"final_authorization_ready_count": 50/);
    assert.match(successOutput, /"final_db_write_authorization_performed": false/);
    assert.match(successOutput, /"raw_write_ready_for_execution": false/);
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
        assert.match(output, /manifest next_required_step must be final_db_write_authorization_planning/);
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
    assert.match(result.stdout, /final DB-write authorization planning only/i);
    assert.equal(result.stderr, '');
});

test('repository L2V3AH artifacts preserve final authorization planning-only safety when generated', () => {
    const artifactPath =
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.final_db_write_authorization_plan.phase521l2v3ah.json';
    if (!fs.existsSync(path.join(PROJECT_ROOT, artifactPath))) return;

    const manifestJson = readJson('docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json');
    const artifact = readJson(artifactPath);
    const report = readText('docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AH.md');

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AH');
    assert.equal(artifact.final_db_write_authorization_planning_only, true);
    assert.equal(artifact.identity_mapping_accepted_count, 50);
    assert.equal(artifact.baseline_accepted_count, 50);
    assert.equal(artifact.no_write_verified_target_count, 50);
    assert.equal(artifact.final_authorization_candidate_count, 50);
    assert.equal(artifact.final_authorization_ready_count, 50);
    assert.equal(artifact.final_authorization_blocked_count, 0);
    assert.equal(artifact.final_db_write_authorization_execution_performed, false);
    assert.equal(artifact.final_db_write_authorization_performed, false);
    assert.equal(artifact.raw_write_retry_performed, false);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.expected_raw_match_data_before_count, 18);
    assert.equal(artifact.expected_raw_match_data_after_count, 68);
    assert.equal(manifestJson.phase_5_21_l2v3ah_final_authorization_ready_count, 50);
    assert.equal([false, true].includes(manifestJson.final_db_write_authorization_performed), true);
    if (manifestJson.final_db_write_authorization_performed === true) {
        assert.equal(
            manifestJson.phase_5_21_l2v3ai_execution_status,
            'completed_final_db_write_authorization_execution'
        );
    }
    assert.equal(manifestJson.raw_write_ready_for_execution, false);
    assert.equal(manifestJson.requires_separate_final_db_write_authorization_execution, true);
    assert.match(report, /current user instruction authorizes planning only, not DB write/i);
});
