'use strict';
/* eslint-disable max-lines -- L2V3AG safety contract is audited together. */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const Module = require('node:module');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_baseline_acceptance_execute.js');

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

function baselinePlanEntry(index, overrides = {}) {
    const base = target(index);
    return {
        ...base,
        identity_mapping_acceptance_status: 'accepted_identity_mapping',
        baseline_review_status: 'baseline_review_ready',
        baseline_acceptance_status: 'not_accepted_planning_only',
        baseline_acceptance_execution_performed: false,
        baseline_accepted: false,
        baseline_accepted_by: null,
        baseline_accepted_at: null,
        baseline_acceptance_blockers: [],
        baseline_acceptance_evidence_summary: {
            identity_mapping_accepted: true,
            no_write_verification_passed: true,
            source_url_evidence_complete: true,
            source_url_fragment_external_id_matches_schedule_external_id: true,
            no_duplicate_identity_keys: true,
            schedule_metadata_present: true,
            regeneration_status_regenerated_no_write: true,
            regeneration_blockers_empty: true,
            source_inventory_record_present: true,
            raw_write_runner_remains_blocked: true,
            final_db_write_authorization_required_separately: true,
        },
        raw_write_eligible_after_baseline_planning: false,
        ...overrides,
    };
}

function acceptedIdentityEntry(index, overrides = {}) {
    const base = target(index);
    return {
        ...base,
        review_status: 'accepted',
        review_result: 'accepted_identity_mapping',
        acceptance_status: 'accepted_identity_mapping',
        accepted_by: 'codex_test_reviewer',
        accepted_at: '2026-05-22T10:30:00Z',
        acceptance_blockers: [],
        acceptance_evidence_summary: {
            l2v3ac_verification_passed: true,
            source_url_evidence_complete: true,
            raw_write_runner_remains_blocked: true,
            human_review_satisfied: true,
        },
        raw_write_eligible_after_acceptance: false,
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
    const base = target(index);
    return {
        ...base,
        external_id: base.schedule_external_id,
        regeneration_status: 'regenerated_no_write',
        regeneration_blockers: [],
        raw_write_ready_for_execution: false,
        ...overrides,
    };
}

function sourceRecord(index, overrides = {}) {
    const base = target(index);
    return {
        ...base,
        external_id: base.schedule_external_id,
        ...overrides,
    };
}

function manifest(overrides = {}) {
    return {
        batch_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        next_required_step: 'baseline_acceptance_execution',
        recommended_next_step: 'Phase 5.21L2V3AG: baseline acceptance execution',
        phase_5_21_l2v3af_planning_status: 'completed_baseline_acceptance_planning',
        phase_5_21_l2v3af_baseline_review_ready_count: 50,
        baseline_acceptance_execution_performed: false,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        final_db_write_authorization_performed: false,
        raw_write_ready_for_execution: false,
        requires_separate_final_db_write_authorization: true,
        ...overrides,
    };
}

function l2v3afPlan(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3AF',
        phase_name: 'baseline_acceptance_planning',
        baseline_acceptance_execution_performed: false,
        baseline_acceptance_performed: false,
        baseline_review_candidate_count: 50,
        baseline_review_ready_count: 50,
        baseline_review_blocked_count: 0,
        baseline_reviewer_required: true,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        baseline_review_entries: Array.from({ length: 50 }, (_, index) => baselinePlanEntry(index)),
        known_prior_hash_drift_context: {
            hash_drift_review_status: 'completed_no_write',
            hash_drift_classification: 'partial_systemic_stable_content_drift',
            baseline_hash_drift_must_be_reviewed_before_execution: true,
        },
        ...overrides,
    };
}

function l2v3aeArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3AE',
        phase_name: 'identity_mapping_acceptance_review_execution',
        accepted_mapping_count: 50,
        blocked_mapping_count: 0,
        human_review_satisfied: true,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        review_entries: Array.from({ length: 50 }, (_, index) => acceptedIdentityEntry(index)),
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
        raw_write_ready_for_execution: false,
        source_inventory_metadata_records: Array.from({ length: 50 }, (_, index) => sourceRecord(index)),
        ...overrides,
    };
}

function runSynthetic(overrides = {}) {
    return mod.runBaselineAcceptanceExecution({
        manifest: manifest(overrides.manifest || {}),
        l2v3afPlan: l2v3afPlan(overrides.l2v3afPlan || {}),
        l2v3aeArtifact: l2v3aeArtifact(overrides.l2v3aeArtifact || {}),
        l2v3acArtifact: l2v3acArtifact(overrides.l2v3acArtifact || {}),
        l2v3aaArtifact: l2v3aaArtifact(overrides.l2v3aaArtifact || {}),
        l2v3yArtifact: l2v3yArtifact(overrides.l2v3yArtifact || {}),
        baselineHumanReviewSatisfied: overrides.baselineHumanReviewSatisfied === true,
        acceptedBy: overrides.acceptedBy || 'codex_test_baseline_reviewer',
        acceptedAt: overrides.acceptedAt || '2026-05-22T16:30:00Z',
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

test('L2V3AG executes baseline acceptance without live fetch, detail fetch, or DB write', () => {
    const result = runSynthetic({ baselineHumanReviewSatisfied: true });
    const artifact = result.artifact;
    const updatedManifest = result.updated_manifest;

    assert.equal(result.ok, true);
    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AG');
    assert.equal(artifact.phase_name, 'baseline_acceptance_execution');
    assert.equal(artifact.baseline_acceptance_execution_performed, true);
    assert.equal(artifact.live_fetch_performed, false);
    assert.equal(artifact.detail_fetch_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.matches_external_id_modified, false);
    assert.equal(artifact.baseline_review_candidate_count, 50);
    assert.equal(artifact.baseline_reviewed_target_count, 50);
    assert.equal(artifact.baseline_accepted_count, 50);
    assert.equal(artifact.baseline_blocked_count, 0);
    assert.equal(artifact.baseline_human_review_required, true);
    assert.equal(artifact.baseline_human_review_satisfied, true);
    assert.equal(updatedManifest.phase_5_21_l2v3ag_baseline_accepted_count, 50);
    assert.equal(updatedManifest.baseline_reviewed_target_count, 50);
    assert.equal(updatedManifest.baseline_human_review_required, true);
    assert.equal(updatedManifest.baseline_human_review_satisfied, true);
    assert.equal(updatedManifest.accepted_identity_mapping_count, 50);
    assert.equal(updatedManifest.baseline_acceptance_evidence_summary_present_count, 50);
});

test('baseline accepted does not imply raw-write readiness, raw write authorization, or final authorization', () => {
    const artifact = runSynthetic({ baselineHumanReviewSatisfied: true }).artifact;

    assert.equal(artifact.baseline_acceptance_performed, true);
    assert.equal(artifact.raw_write_authorization_performed, false);
    assert.equal(artifact.raw_write_retry_performed, false);
    assert.equal(artifact.final_db_write_authorization_performed, false);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.requires_separate_final_db_write_authorization, true);
    assert.equal(artifact.safety_contract.baseline_accepted_does_not_imply_raw_write_authorization, true);
    assert.equal(artifact.safety_contract.baseline_accepted_does_not_imply_raw_write_ready_for_execution, true);
});

test('missing baseline human review blocks baseline acceptance', () => {
    const artifact = runSynthetic({ baselineHumanReviewSatisfied: false }).artifact;

    assert.equal(artifact.baseline_acceptance_execution_performed, true);
    assert.equal(artifact.baseline_human_review_required, true);
    assert.equal(artifact.baseline_human_review_satisfied, false);
    assert.equal(artifact.baseline_accepted_count, 0);
    assert.equal(artifact.baseline_blocked_count, 50);
    assert.equal(
        artifact.baseline_entries.every(entry =>
            entry.baseline_acceptance_blockers.includes('baseline_human_review_missing')
        ),
        true
    );
    assert.equal(artifact.recommended_next_step, 'Phase 5.21L2V3AH: baseline acceptance blocker resolution');
});

test('missing accepted mapping, failed verification, and source evidence gaps block acceptance', () => {
    const entries = Array.from({ length: 50 }, (_, index) =>
        baselinePlanEntry(
            index,
            index === 1
                ? { source_page_url: '', source_page_url_base: '' }
                : index === 2
                  ? { source_url_fragment_external_id: 'mismatch' }
                  : {}
        )
    );
    const identities = Array.from({ length: 50 }, (_, index) =>
        acceptedIdentityEntry(index, index === 3 ? { acceptance_status: 'not_accepted' } : {})
    );
    const verifications = Array.from({ length: 50 }, (_, index) =>
        verificationResult(index, index === 4 ? { verification_status: 'failed' } : {})
    );
    const artifact = runSynthetic({
        baselineHumanReviewSatisfied: true,
        l2v3afPlan: { baseline_review_entries: entries },
        l2v3aeArtifact: { review_entries: identities },
        l2v3acArtifact: { verification_analysis: { target_results: verifications } },
    }).artifact;
    const blockers = artifact.baseline_entries.flatMap(entry => entry.baseline_acceptance_blockers);

    assert.equal(artifact.baseline_accepted_count < 50, true);
    assert.equal(blockers.includes('missing_source_url_evidence'), true);
    assert.equal(blockers.includes('fragment_schedule_mismatch'), true);
    assert.equal(blockers.includes('identity_mapping_not_accepted'), true);
    assert.equal(blockers.includes('verification_not_passed'), true);
    assert.equal(artifact.raw_write_ready_for_execution, false);
});

test('unresolved blockers, duplicates, regeneration drift, and raw-write readiness block acceptance', () => {
    const duplicate = baselinePlanEntry(0);
    const entries = Array.from({ length: 50 }, (_, index) =>
        baselinePlanEntry(
            index,
            index === 1
                ? { source_inventory_record_key: duplicate.source_inventory_record_key }
                : index === 2
                  ? { baseline_review_status: 'baseline_review_blocked', baseline_acceptance_blockers: ['manual'] }
                  : {}
        )
    );
    const enrichedTargets = Array.from({ length: 50 }, (_, index) =>
        enrichedTarget(
            index,
            index === 3 ? { regeneration_status: 'blocked', regeneration_blockers: ['date_rule'] } : {}
        )
    );
    const artifact = runSynthetic({
        baselineHumanReviewSatisfied: true,
        manifest: { raw_write_ready_for_execution: true },
        l2v3afPlan: { baseline_review_entries: entries },
        l2v3aaArtifact: { enriched_targets: enrichedTargets },
    });

    assert.equal(artifact.ok, false);
    assert.match(artifact.errors.join('\n'), /raw-ready state/);

    const cleanManifestArtifact = runSynthetic({
        baselineHumanReviewSatisfied: true,
        l2v3afPlan: { baseline_review_entries: entries },
        l2v3aaArtifact: { enriched_targets: enrichedTargets },
    }).artifact;
    const blockers = cleanManifestArtifact.baseline_entries.flatMap(entry => entry.baseline_acceptance_blockers);

    assert.equal(blockers.includes('duplicate_or_conflicting_identity_key'), true);
    assert.equal(blockers.includes('plan_entry_not_baseline_ready'), true);
    assert.equal(blockers.includes('unresolved_planning_blocker'), true);
    assert.equal(blockers.includes('regeneration_not_clean'), true);
});

test('input validation rejects invalid upstream state and permits idempotent completed manifest metadata', () => {
    const alreadyExecutedGate = mod.validateInputs(
        manifest({
            phase_5_21_l2v3ag_execution_status: 'completed_baseline_acceptance_execution',
            next_required_step: 'final_db_write_authorization_planning',
            baseline_acceptance_performed: true,
        }),
        l2v3afPlan(),
        l2v3aeArtifact(),
        l2v3acArtifact(),
        l2v3aaArtifact(),
        l2v3yArtifact()
    );
    assert.equal(alreadyExecutedGate.ok, true);

    const validation = mod.validateInputs(
        manifest({
            next_required_step: 'raw_write_retry',
            phase_5_21_l2v3af_planning_status: 'blocked',
            phase_5_21_l2v3af_baseline_review_ready_count: 49,
            raw_write_retry_performed: true,
        }),
        l2v3afPlan({
            proposal_phase: 'Phase 5.21L2V3AG',
            phase_name: 'baseline_acceptance_execution',
            baseline_acceptance_execution_performed: true,
            baseline_acceptance_performed: true,
            baseline_review_candidate_count: 49,
            baseline_review_ready_count: 49,
            baseline_review_blocked_count: 1,
            baseline_reviewer_required: false,
        }),
        l2v3aeArtifact({
            proposal_phase: 'Phase 5.21L2V3AF',
            phase_name: 'baseline_acceptance_planning',
            accepted_mapping_count: 49,
            blocked_mapping_count: 1,
            human_review_satisfied: false,
        }),
        l2v3acArtifact({
            proposal_phase: 'Phase 5.21L2V3AB',
            verification_status: 'failed',
            verified_target_count: 49,
            failed_target_count: 1,
            raw_write_runner_blocked: false,
        }),
        l2v3aaArtifact({
            regenerated_target_count: 49,
            raw_write_ready_for_execution: true,
        }),
        l2v3yArtifact({
            candidate_scope_count: 49,
            raw_match_data_insert_performed: true,
        })
    );
    const errors = validation.errors.join('\n');

    assert.equal(validation.ok, false);
    assert.match(errors, /manifest next_required_step/);
    assert.match(errors, /phase_5_21_l2v3af_planning_status/);
    assert.match(errors, /baseline_review_ready_count must be 50/);
    assert.match(errors, /L2V3AF plan artifact is required/);
    assert.match(errors, /L2V3AE accepted_mapping_count must be 50/);
    assert.match(errors, /L2V3AC verification_status/);
    assert.match(errors, /L2V3AA regenerated_target_count must be 50/);
    assert.match(errors, /L2V3Y candidate_scope_count must be 50/);
    assert.match(errors, /raw-ready state/);
});

test('helper refuses DB write, live/detail fetch, raw write retry, final authorization, and payload flags', () => {
    const parsed = mod.parseArgs([
        '--allow-db-write=yes',
        '--allow-network=yes',
        '--allow-live-fetch=yes',
        '--allow-detail-fetch=yes',
        '--allow-raw-match-data-write=yes',
        '--allow-matches-write=yes',
        '--allow-matches-external-id-write=yes',
        '--allow-raw-write-retry=yes',
        '--execute-raw-write=yes',
        '--authorize-final-db-write=yes',
        '--allow-training=yes',
        '--allow-prediction=yes',
        '--print-full-pageprops=yes',
    ]);
    const validation = mod.validateCliOptions(parsed);

    assert.equal(validation.ok, false);
    assert.match(validation.errors.join('\n'), /allow-db-write=yes is blocked/);
    assert.match(validation.errors.join('\n'), /allow-live-fetch=yes is blocked/);
    assert.match(validation.errors.join('\n'), /allow-detail-fetch=yes is blocked/);
    assert.match(validation.errors.join('\n'), /allow-raw-match-data-write=yes is blocked/);
    assert.match(validation.errors.join('\n'), /allow-matches-external-id-write=yes is blocked/);
    assert.match(validation.errors.join('\n'), /allow-raw-write-retry=yes is blocked/);
    assert.match(validation.errors.join('\n'), /authorize-final-db-write=yes is blocked/);
    assert.match(validation.errors.join('\n'), /print-full-pageprops=yes is blocked/);
});

test('argument parser covers aliases, invalid reviewer fields, help, and continuation outcome', () => {
    const parsed = mod.parseArgs([
        '--baseline-human-review-satisfied',
        'on',
        '--write_files',
        'off',
        '--accepted-by',
        'codex_split_reviewer',
        '--accepted_at',
        '2026-05-22T16:45:00Z',
        '--allow-network',
        '0',
        'positional-drift',
    ]);

    assert.equal(parsed.baselineHumanReviewSatisfied, true);
    assert.equal(parsed.writeFiles, false);
    assert.equal(parsed.acceptedBy, 'codex_split_reviewer');
    assert.equal(parsed.acceptedAt, '2026-05-22T16:45:00Z');
    assert.equal(parsed.allowNetwork, false);
    assert.deepEqual(parsed.unknown, ['positional-drift']);
    assert.match(mod.validateCliOptions(parsed).errors.join('\n'), /unknown arguments: positional-drift/);

    const invalidReviewer = mod.validateCliOptions(
        mod.parseArgs(['--baseline-human-review-satisfied=yes', '--accepted-by=', '--accepted-at='])
    );
    assert.equal(invalidReviewer.ok, false);
    assert.match(invalidReviewer.errors.join('\n'), /accepted-by is required/);
    assert.match(invalidReviewer.errors.join('\n'), /accepted-at is required/);

    const artifact = mod.buildArtifact({
        execution: {
            baseline_review_candidate_count: 49,
            baseline_reviewed_target_count: 49,
            baseline_accepted_count: 0,
            baseline_rejected_count: 0,
            baseline_blocked_count: 0,
            baseline_review_blocker_count: 0,
            baseline_acceptance_evidence_summary_present_count: 49,
            baseline_entries: [],
        },
        baselineHumanReviewSatisfied: true,
    });
    assert.equal(artifact.recommended_next_step, 'Phase 5.21L2V3AH: continued baseline acceptance planning');
});

test('helper does not import network, DB, browser, proxy, harvest, odds, or child process modules on load', t => {
    installImportGuard(t);
    const loaded = loadFreshModule();
    assert.equal(typeof loaded.runBaselineAcceptanceExecution, 'function');
});

test('outputs avoid full raw data, pageProps, source body, and HTML payloads', () => {
    const result = runSynthetic({ baselineHumanReviewSatisfied: true });
    for (const text of [JSON.stringify(result.artifact), result.report, JSON.stringify(result.updated_manifest)]) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
        assert.equal(text.includes('"source_body":'), false);
        assert.equal(text.includes('"full_json":'), false);
    }
});

test('runBaselineAcceptanceExecution can write outputs to explicit temp paths', () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'l2v3ag-baseline-acceptance-execute-'));
    const artifactPath = path.join(tmpDir, 'artifact.json');
    const reportPath = path.join(tmpDir, 'report.md');
    const manifestPath = path.join(tmpDir, 'manifest.json');

    try {
        const result = mod.runBaselineAcceptanceExecution({
            manifest: manifest(),
            l2v3afPlan: l2v3afPlan(),
            l2v3aeArtifact: l2v3aeArtifact(),
            l2v3acArtifact: l2v3acArtifact(),
            l2v3aaArtifact: l2v3aaArtifact(),
            l2v3yArtifact: l2v3yArtifact(),
            baselineHumanReviewSatisfied: true,
            acceptedBy: 'codex_temp_reviewer',
            acceptedAt: '2026-05-22T16:30:00Z',
            writeFiles: true,
            artifactOutputPath: artifactPath,
            reportOutputPath: reportPath,
            manifestOutputPath: manifestPath,
        });

        assert.equal(result.ok, true);
        assert.equal(JSON.parse(fs.readFileSync(artifactPath, 'utf8')).proposal_phase, 'Phase 5.21L2V3AG');
        assert.match(fs.readFileSync(reportPath, 'utf8'), /baseline accepted is not raw write authorization/i);
        assert.equal(JSON.parse(fs.readFileSync(manifestPath, 'utf8')).raw_write_ready_for_execution, false);
    } finally {
        fs.rmSync(tmpDir, { recursive: true, force: true });
    }
});

test('CLI covers help, invalid options, missing review block, and execution output without writes', () => {
    let helpOutput = '';
    let invalidOutput = '';
    let blockedOutput = '';
    let successOutput = '';

    const helpStatus = mod.runCli(['--help'], { stdout: text => (helpOutput += text) });
    const invalidStatus = mod.runCli(['--unknown'], { stdout: text => (invalidOutput += text) });
    const blockedStatus = mod.runCli(['--write-files=false'], { stdout: text => (blockedOutput += text) });
    const successStatus = mod.runCli(['--write-files=false', '--baseline-human-review-satisfied=yes'], {
        stdout: text => (successOutput += text),
    });

    assert.equal(helpStatus, 0);
    assert.match(helpOutput, /baseline acceptance execution/i);
    assert.equal(invalidStatus, 2);
    assert.match(invalidOutput, /unknown arguments/);
    assert.equal(blockedStatus, 0);
    assert.match(blockedOutput, /"baseline_accepted_count": 0/);
    assert.equal(successStatus, 0);
    assert.match(successOutput, /"baseline_accepted_count": 50/);
    assert.match(successOutput, /"raw_write_ready_for_execution": false/);
});

test('repository L2V3AG artifacts preserve baseline execution safety when generated', () => {
    const artifactPath =
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.baseline_acceptance_result.phase521l2v3ag.json';
    if (!fs.existsSync(path.join(PROJECT_ROOT, artifactPath))) return;

    const manifestJson = readJson('docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json');
    const artifact = readJson(artifactPath);
    const report = readText('docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AG.md');

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AG');
    assert.equal(artifact.phase_name, 'baseline_acceptance_execution');
    assert.equal(artifact.baseline_acceptance_execution_performed, true);
    assert.equal(artifact.baseline_acceptance_performed, true);
    assert.equal(artifact.baseline_review_candidate_count, 50);
    assert.equal(artifact.baseline_reviewed_target_count, 50);
    assert.equal(artifact.baseline_accepted_count, 50);
    assert.equal(artifact.baseline_blocked_count, 0);
    assert.equal(artifact.raw_write_retry_performed, false);
    assert.equal(artifact.final_db_write_authorization_performed, false);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(manifestJson.phase_5_21_l2v3ag_baseline_accepted_count, 50);
    assert.equal(manifestJson.baseline_reviewed_target_count, 50);
    assert.equal(manifestJson.baseline_human_review_required, true);
    assert.equal(manifestJson.baseline_human_review_satisfied, true);
    assert.equal(manifestJson.baseline_acceptance_performed, true);
    assert.equal(manifestJson.raw_write_ready_for_execution, false);
    assert.equal(manifestJson.requires_separate_final_db_write_authorization, true);
    assert.match(report, /baseline accepted is not raw write authorization/i);
});
