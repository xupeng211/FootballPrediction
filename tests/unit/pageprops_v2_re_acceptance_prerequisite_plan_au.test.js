'use strict';
/* eslint-disable max-lines -- L2V3AU planning tests keep governance assertions explicit. */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const Module = require('node:module');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_re_acceptance_prerequisite_plan.js');

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();

function suspendedTarget(index) {
    const scheduleExternalId = String(4830460 + index);
    const observedDetailExternalId = String(4830750 + index);
    return {
        match_id: `53_20252026_${scheduleExternalId}`,
        schedule_external_id: scheduleExternalId,
        observed_detail_external_id: observedDetailExternalId,
        source_page_url_base: `/matches/synthetic/${scheduleExternalId}`,
        current_mapping_effective_status: 'suspended',
        current_baseline_effective_status: 'suspended',
        current_effective_status: 'suspended',
        current_raw_write_status: 'raw_write_blocked',
        re_acceptance_required: true,
        raw_write_execution_ready: false,
        payload_recapture_retry_ready: false,
    };
}

function blockedTarget(index) {
    const scheduleExternalId = String(4830500 + index);
    return {
        match_id: `53_20252026_${scheduleExternalId}`,
        schedule_external_id: scheduleExternalId,
        observed_detail_external_id: null,
        source_page_url_base: `/matches/synthetic/${scheduleExternalId}`,
        current_effective_status: 'blocked_pending_review',
        current_raw_write_status: 'raw_write_blocked',
        blocked_pending_review: true,
        raw_write_execution_ready: false,
        payload_recapture_retry_ready: false,
    };
}

function syntheticAtResult() {
    return {
        proposal_phase: 'Phase 5.21L2V3AT',
        execution_status: 'completed_accepted_mapping_baseline_suspension_execution',
        suspension_execution_performed: true,
        mapping_suspension_execution_performed: true,
        baseline_suspension_execution_performed: true,
        mapping_suspended_count: 8,
        baseline_suspended_count: 8,
        blocked_pending_review_target_count: 42,
        re_acceptance_required_count: 8,
        runner_contract_fix_planning_required: true,
        expanded_review_required: true,
        historical_accepted_artifacts_mutated: false,
        rollback_execution_performed: false,
        re_acceptance_execution_performed: false,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        raw_write_execution_performed: false,
        raw_write_execution_ready: false,
        final_db_write_authorization_effective_status: 'blocked_or_superseded',
        payload_recapture_retry_ready: false,
        suspended_targets: Array.from({ length: 8 }, (_, index) => suspendedTarget(index)),
        blocked_pending_review_targets: Array.from({ length: 42 }, (_, index) => blockedTarget(index)),
    };
}

function syntheticManifest() {
    return {
        batch_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        recommended_next_step: 'Phase 5.21L2V3AU: re-acceptance prerequisite planning',
        next_required_step: 're_acceptance_prerequisite_planning',
        raw_write_execution_ready: false,
        payload_recapture_retry_ready: false,
    };
}

function syntheticOverrides() {
    return {
        atResult: syntheticAtResult(),
        manifest: syntheticManifest(),
        generatedAt: '2026-05-26T00:00:00.000Z',
    };
}

test('L2V3AU is re-acceptance prerequisite planning-only and avoids forbidden execution paths', () => {
    const result = mod.runReAcceptancePrerequisitePlan({ writeFiles: false }, syntheticOverrides());
    const artifact = result.artifact;
    const manifest = result.updated_manifest;

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AU');
    assert.equal(artifact.phase_name, 're_acceptance_prerequisite_planning');
    assert.equal(artifact.re_acceptance_prerequisite_planning_status, mod.PLANNING_STATUS);
    assert.equal(artifact.live_fetch_performed, false);
    assert.equal(artifact.detail_fetch_performed, false);
    assert.equal(artifact.network_request_performed, false);
    assert.equal(artifact.recapture_retry_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.matches_external_id_modified, false);
    assert.equal(artifact.raw_write_execution_performed, false);
    assert.equal(artifact.raw_write_runner_write_mode_used, false);
    assert.equal(artifact.suspension_reversal_performed, false);
    assert.equal(artifact.re_acceptance_execution_performed, false);
    assert.equal(artifact.rollback_execution_performed, false);
    assert.equal(manifest.phase_5_21_l2v3au_planning_status, mod.PLANNING_STATUS);
});

test('L2V3AU keeps 8 suspended mappings and baselines blocked behind prerequisites', () => {
    const artifact = mod.runReAcceptancePrerequisitePlan({ writeFiles: false }, syntheticOverrides()).artifact;

    assert.equal(artifact.suspended_mapping_count, 8);
    assert.equal(artifact.suspended_baseline_count, 8);
    assert.equal(artifact.re_acceptance_required_count, 8);
    assert.equal(artifact.raw_write_execution_ready, false);
    assert.equal(artifact.payload_recapture_retry_ready, false);

    for (const target of artifact.suspended_targets_requiring_prerequisites) {
        assert.equal(target.current_mapping_effective_status, 'suspended');
        assert.equal(target.current_baseline_effective_status, 'suspended');
        assert.equal(target.current_raw_write_status, 'raw_write_blocked');
        assert.equal(target.identity_mismatch_resolution_required, true);
        assert.equal(target.reverse_fixture_resolution_required, true);
        assert.equal(target.human_review_required, true);
        assert.equal(target.baseline_hash_update_allowed_before_identity_resolution, false);
        assert.equal(target.re_acceptance_execution_performed, false);
        assert.equal(target.suspension_reversal_performed, false);
    }
});

test('L2V3AU mapping prerequisites require identity, reverse-fixture, source consistency, and human review', () => {
    const artifact = mod.runReAcceptancePrerequisitePlan({ writeFiles: false }, syntheticOverrides()).artifact;
    const prerequisiteIds = artifact.mapping_re_acceptance_prerequisites.map(item => item.id);

    assert.equal(artifact.mapping_re_acceptance_prerequisite_count, 8);
    assert.equal(prerequisiteIds.includes('reverse_fixture_evidence_resolved'), true);
    assert.equal(prerequisiteIds.includes('schedule_detail_identity_contract_clarified'), true);
    assert.equal(prerequisiteIds.includes('accepted_detail_identity_supported_by_sufficient_evidence'), true);
    assert.equal(prerequisiteIds.includes('page_url_base_slug_fragment_insufficient'), true);
    assert.equal(prerequisiteIds.includes('source_url_detail_identity_date_team_status_consistency_required'), true);
    assert.equal(prerequisiteIds.includes('no_unresolved_identity_mismatch'), true);
    assert.equal(prerequisiteIds.includes('no_unresolved_reverse_fixture_detected'), true);
    assert.equal(prerequisiteIds.includes('human_review_required'), true);
});

test('L2V3AU baseline prerequisites block hash re-acceptance while identity mismatch is unresolved', () => {
    const artifact = mod.runReAcceptancePrerequisitePlan({ writeFiles: false }, syntheticOverrides()).artifact;
    const prerequisiteIds = artifact.baseline_re_acceptance_prerequisites.map(item => item.id);

    assert.equal(artifact.baseline_re_acceptance_prerequisite_count, 5);
    assert.equal(prerequisiteIds.includes('identity_mismatch_resolved_first'), true);
    assert.equal(prerequisiteIds.includes('hash_mismatch_secondary_until_identity_corrected'), true);
    assert.equal(prerequisiteIds.includes('baseline_hash_update_cannot_bypass_identity_mismatch'), true);
    assert.equal(prerequisiteIds.includes('baseline_evidence_binds_to_correct_accepted_identity'), true);
    assert.equal(prerequisiteIds.includes('baseline_re_acceptance_requires_separate_review'), true);
});

test('L2V3AU keeps 42 remaining targets blocked_pending_review', () => {
    const artifact = mod.runReAcceptancePrerequisitePlan({ writeFiles: false }, syntheticOverrides()).artifact;

    assert.equal(artifact.blocked_pending_review_target_count, 42);
    assert.equal(artifact.expanded_review_prerequisite_required, true);
    assert.equal(artifact.blocked_targets_clean_acceptance_inferred, false);
    for (const target of artifact.blocked_pending_review_targets) {
        assert.equal(target.current_effective_status, 'blocked_pending_review');
        assert.equal(target.current_raw_write_status, 'raw_write_blocked');
        assert.equal(target.expanded_review_required, true);
        assert.equal(target.clean_acceptance_inferred, false);
        assert.equal(target.raw_write_execution_ready, false);
    }
});

test('L2V3AU requires runner contract planning and a fresh authorization chain', () => {
    const result = mod.runReAcceptancePrerequisitePlan({ writeFiles: false }, syntheticOverrides());
    const artifact = result.artifact;
    const manifest = result.updated_manifest;

    assert.equal(artifact.runner_contract_fix_prerequisite_required, true);
    assert.equal(artifact.runner_contract_prerequisite_status, 'fix_planning_required_before_recapture_retry');
    assert.equal(artifact.recapture_runner_must_use_accepted_mapping_source_url_detail_identity, true);
    assert.equal(artifact.schedule_side_route_alone_allowed_for_recapture_retry, false);
    assert.equal(artifact.runner_contract_fix_implementation_performed, false);
    assert.equal(artifact.fresh_final_authorization_required, true);
    assert.equal(artifact.prior_final_db_write_authorization_effective_status, 'blocked_or_superseded');
    assert.equal(artifact.direct_path_from_suspended_state_to_raw_write_allowed, false);
    assert.equal(manifest.fresh_final_authorization_required, true);
    assert.equal(manifest.re_acceptance_execution_performed, false);
    assert.equal(artifact.recommended_next_step, mod.NEXT_STEP_RUNNER_CONTRACT_FIX);
});

test('L2V3AU report, artifact, and manifest avoid full payload markers', () => {
    const result = mod.runReAcceptancePrerequisitePlan({ writeFiles: false }, syntheticOverrides());
    const texts = [JSON.stringify(result.artifact), result.report, JSON.stringify(result.updated_manifest)];

    for (const text of texts) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
        assert.equal(text.includes('"source_body":'), false);
    }
});

test('L2V3AU can write artifact, report, and manifest through injected writers', () => {
    const writes = [];
    const result = mod.runReAcceptancePrerequisitePlan(
        {},
        {
            ...syntheticOverrides(),
            writeJsonFile: (targetPath, value) => writes.push(['json', targetPath, value]),
            writeTextFile: (targetPath, value) => writes.push(['text', targetPath, value]),
        }
    );

    assert.equal(result.ok, true);
    assert.deepEqual(
        writes.map(([kind, targetPath]) => [kind, targetPath]),
        [
            ['json', mod.ARTIFACT_OUTPUT_PATH],
            ['text', mod.REPORT_OUTPUT_PATH],
            ['json', mod.PROPOSAL_MANIFEST_PATH],
        ]
    );
});

test('L2V3AU runCli prints a safe planning summary without writing during the test', async () => {
    let output = '';
    const writes = [];
    const originalWrite = process.stdout.write;
    const originalWriteFileSync = fs.writeFileSync;
    process.stdout.write = text => {
        output += text;
        return true;
    };
    fs.writeFileSync = function patchedWriteFileSync(filePath, value, encoding) {
        writes.push([String(filePath), String(value), encoding]);
    };

    try {
        await mod.runCli();
    } finally {
        process.stdout.write = originalWrite;
        fs.writeFileSync = originalWriteFileSync;
    }

    const parsed = JSON.parse(output);
    assert.equal(parsed.ok, true);
    assert.equal(parsed.phase, 'Phase 5.21L2V3AU');
    assert.equal(parsed.suspended_mapping_count, 8);
    assert.equal(parsed.suspended_baseline_count, 8);
    assert.equal(parsed.blocked_pending_review_target_count, 42);
    assert.equal(parsed.raw_write_execution_ready, false);
    assert.equal(parsed.payload_recapture_retry_ready, false);
    assert.equal(writes.length, 3);
});

test('module load avoids DB, network, browser, proxy, and child process imports', () => {
    const seen = [];
    const originalLoad = Module._load;
    Module._load = function wrapped(request, parent, isMain) {
        seen.push(request);
        return originalLoad.call(this, request, parent, isMain);
    };
    try {
        delete require.cache[require.resolve(MODULE_PATH)];
        require(MODULE_PATH);
    } finally {
        Module._load = originalLoad;
        delete require.cache[require.resolve(MODULE_PATH)];
    }

    const joined = seen.join('\n');
    assert.doesNotMatch(joined, /\bpg\b|psql|postgres|child_process|playwright|puppeteer|axios|undici/i);
    assert.doesNotMatch(joined, /BrowserProvider|proxy/i);
});

test('repository L2V3AU artifacts preserve planning-only semantics when generated', () => {
    const artifactPath = path.join(
        PROJECT_ROOT,
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.re_acceptance_prerequisite_plan.phase521l2v3au.json'
    );
    if (!fs.existsSync(artifactPath)) return;

    const artifact = JSON.parse(fs.readFileSync(artifactPath, 'utf8'));
    const manifest = JSON.parse(
        fs.readFileSync(
            path.join(PROJECT_ROOT, 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json'),
            'utf8'
        )
    );
    const report = fs.readFileSync(
        path.join(PROJECT_ROOT, 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AU.md'),
        'utf8'
    );

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AU');
    assert.equal(artifact.re_acceptance_prerequisite_planning_status, mod.PLANNING_STATUS);
    assert.equal(artifact.suspended_mapping_count, 8);
    assert.equal(artifact.suspended_baseline_count, 8);
    assert.equal(artifact.blocked_pending_review_target_count, 42);
    assert.equal(artifact.runner_contract_fix_prerequisite_required, true);
    assert.equal(artifact.expanded_review_prerequisite_required, true);
    assert.equal(artifact.fresh_final_authorization_required, true);
    assert.equal(artifact.re_acceptance_execution_performed, false);
    assert.equal(artifact.suspension_reversal_performed, false);
    assert.equal(artifact.rollback_execution_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.raw_write_execution_performed, false);
    assert.equal(artifact.raw_write_execution_ready, false);
    assert.equal(artifact.payload_recapture_retry_ready, false);

    assert.equal(manifest.phase_5_21_l2v3au_planning_status, mod.PLANNING_STATUS);
    assert.equal(manifest.runner_contract_fix_prerequisite_required, true);
    assert.match(report, /mapping_re_acceptance_prerequisite_count=8/);
    assert.match(report, /baseline_re_acceptance_prerequisite_count=5/);
    assert.match(report, /fresh_final_authorization_required=true/);
});
