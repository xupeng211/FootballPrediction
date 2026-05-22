'use strict';
/* eslint-disable max-lines -- L2V3AE safety contract is audited together. */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const Module = require('node:module');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_identity_mapping_acceptance_review_execute.js');

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

function enrichedTarget(index, overrides = {}) {
    const externalId = String(9100001 + index);
    return {
        target_id: `fotmob-pageprops-v2-ligue1-2025-2026-profile-001:53_20252026_${externalId}`,
        match_id: `53_20252026_${externalId}`,
        external_id: externalId,
        schedule_external_id: externalId,
        source_page_url: `/matches/home-${index}-away-${index}/route-${index}#${externalId}`,
        source_page_url_base: `/matches/home-${index}-away-${index}/route-${index}`,
        source_url_fragment_external_id: externalId,
        schedule_date: '2025-08-15T18:45:00.000Z',
        schedule_home_team: `Home ${index}`,
        schedule_away_team: `Away ${index}`,
        source_inventory_record_key: `l1_api_data_leagues:overview.leagueOverviewMatches.${index}:${externalId}`,
        regeneration_status: 'regenerated_no_write',
        regeneration_blockers: [],
        raw_write_ready_for_execution: false,
        ...overrides,
    };
}

function sourceRecord(index, overrides = {}) {
    const target = enrichedTarget(index);
    return {
        target_id: target.target_id,
        match_id: target.match_id,
        external_id: target.external_id,
        source_page_url: target.source_page_url,
        source_page_url_base: target.source_page_url_base,
        source_url_fragment_external_id: target.source_url_fragment_external_id,
        schedule_external_id: target.schedule_external_id,
        schedule_date: target.schedule_date,
        schedule_home_team: target.schedule_home_team,
        schedule_away_team: target.schedule_away_team,
        source_inventory_record_key: target.source_inventory_record_key,
        ...overrides,
    };
}

function verificationResult(index, overrides = {}) {
    const target = enrichedTarget(index);
    return {
        target_id: target.target_id,
        match_id: target.match_id,
        schedule_external_id: target.schedule_external_id,
        source_url_fragment_external_id: target.source_url_fragment_external_id,
        verification_status: 'verified',
        failure_reasons: [],
        ...overrides,
    };
}

function reviewPlanEntry(index, overrides = {}) {
    const target = enrichedTarget(index);
    return {
        target_id: target.target_id,
        match_id: target.match_id,
        schedule_external_id: target.schedule_external_id,
        source_page_url: target.source_page_url,
        source_page_url_base: target.source_page_url_base,
        source_url_fragment_external_id: target.source_url_fragment_external_id,
        schedule_date: target.schedule_date,
        schedule_home_team: target.schedule_home_team,
        schedule_away_team: target.schedule_away_team,
        source_inventory_record_key: target.source_inventory_record_key,
        verification_status: 'verified',
        review_status: 'review_ready',
        acceptance_status: 'not_accepted_planning_only',
        reviewer_required: true,
        accepted_by: null,
        accepted_at: null,
        acceptance_blockers: [],
        acceptance_evidence_summary: {
            source_url_evidence_complete: true,
            source_url_fragment_external_id_matches_schedule_external_id: true,
            source_inventory_record_present: true,
            schedule_metadata_present: true,
            verification_passed: true,
            raw_write_runner_blocked: true,
            human_review_executed: false,
        },
        raw_write_eligible_after_acceptance: false,
        ...overrides,
    };
}

function manifest(overrides = {}) {
    return {
        batch_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        next_required_step: 'identity_mapping_acceptance_review_execution',
        recommended_next_step: 'Phase 5.21L2V3AE: identity mapping acceptance review execution',
        raw_write_ready_for_execution: false,
        accepted_mapping_count: 0,
        identity_mapping_acceptance_performed: false,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        ...overrides,
    };
}

function planArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3AD',
        phase_name: 'identity_mapping_acceptance_review_planning',
        acceptance_execution_performed: false,
        accepted_mapping_count: 0,
        acceptance_review_candidate_count: 50,
        review_ready_count: 50,
        review_blocked_count: 0,
        human_review_required: true,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        review_plan_entries: Array.from({ length: 50 }, (_, index) => reviewPlanEntry(index)),
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
        db_write_performed: false,
        raw_write_ready_for_execution: false,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
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
    return mod.runIdentityMappingAcceptanceReviewExecution({
        manifest: manifest(overrides.manifest || {}),
        planArtifact: planArtifact(overrides.planArtifact || {}),
        l2v3acArtifact: l2v3acArtifact(overrides.l2v3acArtifact || {}),
        l2v3aaArtifact: l2v3aaArtifact(overrides.l2v3aaArtifact || {}),
        l2v3yArtifact: l2v3yArtifact(overrides.l2v3yArtifact || {}),
        humanReviewSatisfied: overrides.humanReviewSatisfied === true,
        acceptedBy: overrides.acceptedBy || 'codex_test_reviewer',
        acceptedAt: overrides.acceptedAt || '2026-05-22T10:30:00Z',
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

test('L2V3AE executes identity mapping acceptance review without live fetch, detail fetch, or DB write', () => {
    const result = runSynthetic({ humanReviewSatisfied: true });
    const artifact = result.artifact;
    const updatedManifest = result.updated_manifest;

    assert.equal(result.ok, true);
    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AE');
    assert.equal(artifact.phase_name, 'identity_mapping_acceptance_review_execution');
    assert.equal(artifact.acceptance_review_execution_performed, true);
    assert.equal(artifact.live_fetch_performed, false);
    assert.equal(artifact.detail_fetch_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.matches_external_id_modified, false);
    assert.equal(artifact.review_candidate_count, 50);
    assert.equal(artifact.reviewed_target_count, 50);
    assert.equal(artifact.accepted_mapping_count, 50);
    assert.equal(artifact.blocked_mapping_count, 0);
    assert.equal(artifact.human_review_required, true);
    assert.equal(artifact.human_review_satisfied, true);
    assert.equal(updatedManifest.phase_5_21_l2v3ae_accepted_mapping_count, 50);
});

test('accepted mapping does not imply baseline acceptance, raw-write readiness, or raw write authorization', () => {
    const artifact = runSynthetic({ humanReviewSatisfied: true }).artifact;

    assert.equal(artifact.identity_mapping_acceptance_performed, true);
    assert.equal(artifact.baseline_acceptance_performed, false);
    assert.equal(artifact.raw_write_retry_performed, false);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.requires_separate_baseline_acceptance, true);
    assert.equal(artifact.requires_separate_final_db_write_authorization, true);
    assert.equal(artifact.safety_contract.accepted_identity_mapping_is_not_raw_write_authorization, true);
    assert.equal(artifact.safety_contract.accepted_mapping_does_not_imply_raw_write_ready_for_execution, true);
});

test('missing human review blocks acceptance even when all targets are review-ready', () => {
    const artifact = runSynthetic({ humanReviewSatisfied: false }).artifact;

    assert.equal(artifact.acceptance_review_execution_performed, true);
    assert.equal(artifact.human_review_required, true);
    assert.equal(artifact.human_review_satisfied, false);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.blocked_mapping_count, 50);
    assert.equal(
        artifact.review_entries.every(entry => entry.acceptance_blockers.includes('human_review_missing')),
        true
    );
    assert.equal(artifact.recommended_next_step, 'Phase 5.21L2V3AF: identity mapping acceptance blocker resolution');
});

test('review-ready and verification-passed inputs do not become accepted without execution artifact', () => {
    const blocked = runSynthetic({ humanReviewSatisfied: false }).artifact;

    assert.equal(blocked.safety_contract.review_ready_is_not_accepted_without_execution_artifact, true);
    assert.equal(blocked.safety_contract.verification_passed_is_not_accepted_mapping_without_execution_artifact, true);
    for (const entry of blocked.review_entries) {
        assert.equal(entry.acceptance_status, 'not_accepted');
        assert.equal(entry.accepted_by, null);
        assert.equal(entry.accepted_at, null);
        assert.equal(entry.raw_write_eligible_after_acceptance, false);
    }
});

test('criteria blockers prevent acceptance without changing raw-write guards', () => {
    const duplicate = reviewPlanEntry(0);
    const entries = Array.from({ length: 50 }, (_, index) =>
        reviewPlanEntry(
            index,
            index === 1
                ? { source_inventory_record_key: duplicate.source_inventory_record_key }
                : index === 2
                  ? { source_url_fragment_external_id: 'mismatch' }
                  : {}
        )
    );
    const artifact = runSynthetic({
        humanReviewSatisfied: true,
        planArtifact: { review_plan_entries: entries },
    }).artifact;
    const blockers = artifact.review_entries.flatMap(entry => entry.acceptance_blockers);

    assert.equal(artifact.accepted_mapping_count < 50, true);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(blockers.includes('duplicate_source_key'), true);
    assert.equal(blockers.includes('fragment_schedule_mismatch'), true);
});

test('input validation rejects prerequisite drift and unsafe write state branches', () => {
    const alreadyExecutedGate = mod.validateInputs(
        manifest({
            phase_5_21_l2v3ae_execution_status: 'completed_identity_mapping_acceptance_review_execution',
            next_required_step: 'baseline_acceptance_planning',
        }),
        planArtifact(),
        l2v3acArtifact(),
        l2v3aaArtifact(),
        l2v3yArtifact()
    );
    assert.equal(alreadyExecutedGate.ok, true);

    const validation = mod.validateInputs(
        manifest({
            next_required_step: 'raw_write_retry',
            accepted_mapping_count: 1,
            identity_mapping_acceptance_performed: true,
            raw_write_ready_for_execution: true,
        }),
        planArtifact({
            proposal_phase: 'Phase 5.21L2V3AE',
            phase_name: 'identity_mapping_acceptance_review_execution',
            acceptance_execution_performed: true,
            accepted_mapping_count: 1,
            acceptance_review_candidate_count: 49,
            review_ready_count: 49,
            review_blocked_count: 1,
            human_review_required: false,
            db_write_performed: true,
        }),
        l2v3acArtifact({
            proposal_phase: 'Phase 5.21L2V3AB',
            verification_status: 'failed',
            verified_target_count: 49,
            failed_target_count: 1,
            raw_write_runner_blocked: false,
            matches_write_performed: true,
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
    assert.match(errors, /manifest accepted_mapping_count must be 0/);
    assert.match(errors, /L2V3AD review plan artifact is required/);
    assert.match(errors, /L2V3AC verification_status/);
    assert.match(errors, /L2V3AA regenerated_target_count must be 50/);
    assert.match(errors, /L2V3Y candidate_scope_count must be 50/);
    assert.match(errors, /write-ready, DB-write, baseline, or raw retry state/);
});

test('execution blockers cover source, duplication, regeneration, audit, and upstream guard branches', () => {
    const entries = Array.from({ length: 50 }, (_, index) => reviewPlanEntry(index));
    entries[0] = reviewPlanEntry(0, {
        review_status: 'review_blocked',
        acceptance_status: 'accepted_identity_mapping',
        source_page_url: '',
        source_page_url_base: '',
        source_url_fragment_external_id: '',
        source_inventory_record_key: '',
        schedule_date: '',
        schedule_home_team: '',
        schedule_away_team: '',
        acceptance_evidence_summary: null,
    });
    entries[1] = reviewPlanEntry(1, { match_id: entries[0].match_id });
    entries[2] = reviewPlanEntry(2, { source_url_fragment_external_id: entries[1].source_url_fragment_external_id });

    const enrichedTargets = Array.from({ length: 50 }, (_, index) => enrichedTarget(index));
    enrichedTargets[0] = enrichedTarget(0, {
        regeneration_status: 'blocked',
        regeneration_blockers: ['manual_review_required'],
    });
    const sourceRecords = Array.from({ length: 50 }, (_, index) => sourceRecord(index)).filter(
        record => record.target_id !== entries[0].target_id
    );

    const execution = mod.executeAcceptanceReview(
        manifest(),
        planArtifact({ review_plan_entries: entries }),
        l2v3acArtifact({ raw_write_runner_blocked: false }),
        l2v3aaArtifact({ enriched_targets: enrichedTargets }),
        l2v3yArtifact({ source_inventory_metadata_records: sourceRecords }),
        { humanReviewSatisfied: true }
    );
    const blockers = execution.review_entries.flatMap(entry => entry.acceptance_blockers);

    assert.equal(execution.accepted_mapping_count < 50, true);
    assert.equal(blockers.includes('plan_entry_not_review_ready'), true);
    assert.equal(blockers.includes('plan_entry_not_planning_only'), true);
    assert.equal(blockers.includes('missing_source_url_evidence'), true);
    assert.equal(blockers.includes('fragment_schedule_mismatch'), true);
    assert.equal(blockers.includes('duplicate_target_or_match_id'), true);
    assert.equal(blockers.includes('duplicate_fragment_external_id'), true);
    assert.equal(blockers.includes('schedule_team_date_mismatch'), true);
    assert.equal(blockers.includes('regeneration_status_not_clean'), true);
    assert.equal(blockers.includes('regeneration_blockers_present'), true);
    assert.equal(blockers.includes('source_inventory_record_missing'), true);
    assert.equal(blockers.includes('raw_write_runner_unexpectedly_ready'), true);
    assert.equal(blockers.includes('incomplete_audit_trail'), true);

    const unsafeExecution = mod.executeAcceptanceReview(
        manifest({ baseline_acceptance_performed: true, raw_write_retry_performed: true }),
        planArtifact(),
        l2v3acArtifact(),
        l2v3aaArtifact(),
        l2v3yArtifact(),
        { humanReviewSatisfied: true }
    );
    const unsafeBlockers = unsafeExecution.review_entries[0].acceptance_blockers;
    assert.equal(unsafeBlockers.includes('baseline_acceptance_already_performed'), true);
    assert.equal(unsafeBlockers.includes('raw_write_retry_already_performed'), true);
});

test('argument parser covers split values, aliases, false tokens, invalid reviewer fields, and continuation outcome', () => {
    const parsed = mod.parseArgs([
        '--human-review-satisfied',
        'on',
        '--write_files',
        'off',
        '--accepted-by',
        'codex_split_reviewer',
        '--accepted_at',
        '2026-05-22T10:45:00Z',
        '--allow-network',
        '0',
        'positional-drift',
    ]);

    assert.equal(parsed.humanReviewSatisfied, true);
    assert.equal(parsed.writeFiles, false);
    assert.equal(parsed.acceptedBy, 'codex_split_reviewer');
    assert.equal(parsed.acceptedAt, '2026-05-22T10:45:00Z');
    assert.equal(parsed.allowNetwork, false);
    assert.deepEqual(parsed.unknown, ['positional-drift']);
    assert.match(mod.validateCliOptions(parsed).errors.join('\n'), /unknown arguments: positional-drift/);

    const invalidReviewer = mod.validateCliOptions(
        mod.parseArgs(['--human-review-satisfied=yes', '--accepted-by=', '--accepted-at='])
    );
    assert.equal(invalidReviewer.ok, false);
    assert.match(invalidReviewer.errors.join('\n'), /accepted-by is required/);
    assert.match(invalidReviewer.errors.join('\n'), /accepted-at is required/);

    const artifact = mod.buildArtifact({
        execution: {
            review_candidate_count: 49,
            reviewed_target_count: 49,
            accepted_mapping_count: 0,
            rejected_mapping_count: 0,
            blocked_mapping_count: 0,
            review_blocker_count: 0,
            acceptance_evidence_summary_present_count: 49,
            review_entries: [],
        },
        humanReviewSatisfied: true,
    });
    assert.equal(
        artifact.recommended_next_step,
        'Phase 5.21L2V3AF: continued identity mapping acceptance review planning'
    );
});

test('helper refuses DB write, live/detail fetch, baseline, raw write, parser, browser, proxy, and payload flags', () => {
    const parsed = mod.parseArgs([
        '--allow-db-write=yes',
        '--allow-network=yes',
        '--allow-live-fetch=yes',
        '--allow-detail-fetch=yes',
        '--allow-raw-match-data-write=yes',
        '--allow-matches-write=yes',
        '--allow-matches-external-id-write=yes',
        '--accept-baseline=yes',
        '--allow-raw-write-retry=yes',
        '--execute-raw-write=yes',
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
    assert.match(validation.errors.join('\n'), /accept-baseline=yes is blocked/);
    assert.match(validation.errors.join('\n'), /allow-raw-write-retry=yes is blocked/);
    assert.match(validation.errors.join('\n'), /execute-raw-write=yes is blocked/);
    assert.match(validation.errors.join('\n'), /print-full-pageprops=yes is blocked/);
});

test('helper does not import network, DB, browser, proxy, harvest, odds, or child process modules on load', t => {
    installImportGuard(t);
    const loaded = loadFreshModule();
    assert.equal(typeof loaded.runIdentityMappingAcceptanceReviewExecution, 'function');
});

test('outputs avoid full raw data, pageProps, source body, and HTML payloads', () => {
    const result = runSynthetic({ humanReviewSatisfied: true });
    for (const text of [JSON.stringify(result.artifact), result.report, JSON.stringify(result.updated_manifest)]) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
        assert.equal(text.includes('"source_body":'), false);
        assert.equal(text.includes('"full_json":'), false);
    }
});

test('runIdentityMappingAcceptanceReviewExecution can write execution outputs to explicit temp paths', () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'l2v3ae-acceptance-review-exec-'));
    const artifactPath = path.join(tmpDir, 'artifact.json');
    const reportPath = path.join(tmpDir, 'report.md');
    const manifestPath = path.join(tmpDir, 'manifest.json');

    try {
        const result = mod.runIdentityMappingAcceptanceReviewExecution({
            manifest: manifest(),
            planArtifact: planArtifact(),
            l2v3acArtifact: l2v3acArtifact(),
            l2v3aaArtifact: l2v3aaArtifact(),
            l2v3yArtifact: l2v3yArtifact(),
            humanReviewSatisfied: true,
            acceptedBy: 'codex_test_reviewer',
            acceptedAt: '2026-05-22T10:30:00Z',
            writeFiles: true,
            artifactOutputPath: artifactPath,
            reportOutputPath: reportPath,
            manifestOutputPath: manifestPath,
        });

        assert.equal(result.ok, true);
        assert.equal(JSON.parse(fs.readFileSync(artifactPath, 'utf8')).proposal_phase, 'Phase 5.21L2V3AE');
        assert.match(fs.readFileSync(reportPath, 'utf8'), /accepted mapping does not imply raw_write_ready/i);
        assert.equal(JSON.parse(fs.readFileSync(manifestPath, 'utf8')).raw_write_ready_for_execution, false);
    } finally {
        fs.rmSync(tmpDir, { recursive: true, force: true });
    }
});

test('CLI covers help, invalid options, accepted execution, and blocked human review execution', () => {
    let helpOutput = '';
    let invalidOutput = '';
    let acceptedOutput = '';
    let blockedOutput = '';

    const helpStatus = mod.runCli(['--help'], { stdout: text => (helpOutput += text) });
    const invalidStatus = mod.runCli(['--unknown'], { stdout: text => (invalidOutput += text) });
    const acceptedStatus = mod.runCli(['--write-files=false', '--human-review-satisfied=yes'], {
        stdout: text => (acceptedOutput += text),
    });
    const blockedStatus = mod.runCli(['--write-files=false', '--human-review-satisfied=no'], {
        stdout: text => (blockedOutput += text),
    });

    assert.equal(helpStatus, 0);
    assert.match(helpOutput, /identity mapping acceptance review execution/);
    assert.equal(invalidStatus, 2);
    assert.match(invalidOutput, /unknown arguments/);
    if (acceptedStatus === 0) {
        assert.match(acceptedOutput, /"accepted_mapping_count": 50/);
        assert.equal(blockedStatus, 0);
        assert.match(blockedOutput, /"accepted_mapping_count": 0/);
    } else {
        assert.equal(acceptedStatus, 3);
        assert.match(acceptedOutput, /manifest next_required_step/);
        assert.equal(blockedStatus, 3);
        assert.match(blockedOutput, /manifest next_required_step/);
    }
});

test('repository L2V3AE artifacts preserve acceptance execution safety when generated', () => {
    const artifactPath =
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.identity_mapping_acceptance_result.phase521l2v3ae.json';
    if (!fs.existsSync(path.join(PROJECT_ROOT, artifactPath))) return;

    const manifestJson = readJson('docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json');
    const artifact = readJson(artifactPath);
    const report = readText('docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AE.md');

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AE');
    assert.equal(artifact.acceptance_review_execution_performed, true);
    assert.equal(artifact.accepted_mapping_count, 50);
    assert.equal(artifact.blocked_mapping_count, 0);
    assert.equal(artifact.human_review_satisfied, true);
    assert.equal(artifact.baseline_acceptance_performed, false);
    assert.equal(artifact.raw_write_retry_performed, false);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(manifestJson.phase_5_21_l2v3ae_accepted_mapping_count, 50);
    assert.equal(manifestJson.raw_write_ready_for_execution, false);
    assert.equal(manifestJson.requires_separate_baseline_acceptance, true);
    assert.equal(manifestJson.requires_separate_final_db_write_authorization, true);
    assert.match(report, /accepted identity mapping is not raw write authorization/i);
});
