'use strict';
/* eslint-disable max-lines -- L2V3AS planning tests keep governance assertions explicit. */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const Module = require('node:module');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_accepted_mapping_baseline_suspension_plan.js');

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();

function confirmedTarget(matchId, scheduleExternalId, observedDetailExternalId) {
    return {
        match_id: matchId,
        schedule_external_id: scheduleExternalId,
        observed_detail_external_id: observedDetailExternalId,
        source_page_url_base: `/matches/synthetic/${scheduleExternalId}`,
        contradiction_review_status: 'contradiction_confirmed',
        accepted_mapping_contradiction_confirmed: true,
        baseline_acceptance_contradiction_confirmed: true,
        mapping_suspension_required: true,
        baseline_suspension_required: true,
        re_acceptance_required: true,
        raw_write_execution_ready: false,
        payload_recapture_retry_ready: false,
    };
}

function blockedTarget(matchId, scheduleExternalId) {
    return {
        match_id: matchId,
        schedule_external_id: scheduleExternalId,
        observed_detail_external_id: null,
        source_page_url_base: `/matches/synthetic/${scheduleExternalId}`,
        contradiction_review_status: 'contradiction_blocked_pending_evidence',
        accepted_mapping_contradiction_confirmed: false,
        baseline_acceptance_contradiction_confirmed: false,
        mapping_suspension_required: false,
        baseline_suspension_required: false,
        re_acceptance_required: false,
        raw_write_execution_ready: false,
        payload_recapture_retry_ready: false,
    };
}

function syntheticArResult() {
    return {
        proposal_phase: 'Phase 5.21L2V3AR',
        execution_status: 'completed_accepted_mapping_baseline_contradiction_review_execution',
        contradiction_review_candidate_count: 5,
        contradiction_reviewed_count: 5,
        contradiction_confirmed_count: 2,
        contradiction_blocked_pending_evidence_count: 3,
        accepted_mapping_contradiction_confirmed_count: 2,
        baseline_acceptance_contradiction_confirmed_count: 2,
        mapping_suspension_required_count: 2,
        baseline_suspension_required_count: 2,
        re_acceptance_required_count: 2,
        runner_contract_fix_required: true,
        expanded_review_required: true,
        payload_recapture_retry_ready: false,
        raw_write_execution_ready: false,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        review_targets: [
            confirmedTarget('53_20252026_4830466', '4830466', '4830759'),
            confirmedTarget('53_20252026_4830461', '4830461', '4830758'),
            blockedTarget('53_20252026_4830458', '4830458'),
            blockedTarget('53_20252026_4830459', '4830459'),
            blockedTarget('53_20252026_4830460', '4830460'),
        ],
    };
}

function syntheticManifest() {
    return {
        batch_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        recommended_next_step: 'Phase 5.21L2V3AS: accepted mapping and baseline suspension planning',
        next_required_step: 'accepted_mapping_and_baseline_suspension_planning',
        raw_write_execution_ready: false,
    };
}

function syntheticOverrides() {
    return {
        arResult: syntheticArResult(),
        manifest: syntheticManifest(),
        generatedAt: '2026-05-26T00:00:00.000Z',
    };
}

test('L2V3AS is suspension planning-only and avoids fetch, retry, DB write, raw write, rollback, and suspension execution', () => {
    const result = mod.runAcceptedMappingBaselineSuspensionPlan({ writeFiles: false }, syntheticOverrides());
    const artifact = result.artifact;
    const manifest = result.updated_manifest;

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AS');
    assert.equal(artifact.phase_name, 'accepted_mapping_baseline_suspension_planning');
    assert.equal(artifact.suspension_planning_status, mod.PLANNING_STATUS);
    assert.equal(artifact.live_fetch_performed, false);
    assert.equal(artifact.detail_fetch_performed, false);
    assert.equal(artifact.network_request_performed, false);
    assert.equal(artifact.recapture_retry_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.raw_write_execution_performed, false);
    assert.equal(artifact.raw_write_runner_write_mode_used, false);
    assert.equal(artifact.mapping_suspension_execution_performed, false);
    assert.equal(artifact.baseline_suspension_execution_performed, false);
    assert.equal(artifact.rollback_execution_performed, false);
    assert.equal(artifact.re_acceptance_execution_performed, false);
    assert.equal(artifact.accepted_artifact_mutation_performed, false);
    assert.equal(artifact.baseline_artifact_mutation_performed, false);
    assert.equal(artifact.raw_write_execution_ready, false);
    assert.equal(artifact.payload_recapture_retry_ready, false);
    assert.equal(manifest.phase_5_21_l2v3as_planning_status, artifact.suspension_planning_status);
    assert.equal(manifest.raw_write_execution_ready, false);
});

test('L2V3AS plans 8-equivalent mapping and baseline suspension candidates without marking them suspended', () => {
    const artifact = mod.runAcceptedMappingBaselineSuspensionPlan({ writeFiles: false }, syntheticOverrides()).artifact;

    assert.equal(artifact.mapping_suspension_candidate_count, 2);
    assert.equal(artifact.baseline_suspension_candidate_count, 2);
    assert.equal(artifact.mapping_suspension_planned_count, 2);
    assert.equal(artifact.baseline_suspension_planned_count, 2);
    assert.equal(artifact.re_acceptance_required_count, 2);
    assert.equal(artifact.runner_contract_fix_planning_required, true);
    assert.equal(artifact.expanded_review_required, true);
    assert.equal(
        artifact.recommended_next_step,
        'Phase 5.21L2V3AT: accepted mapping and baseline suspension execution'
    );
    assert.equal(artifact.next_required_step, 'accepted_mapping_and_baseline_suspension_execution');

    for (const target of artifact.suspension_targets) {
        assert.equal(target.current_mapping_state, 'accepted_active');
        assert.equal(target.planned_mapping_state, 'suspension_planned');
        assert.equal(target.future_mapping_state_after_execution, 'suspended');
        assert.equal(target.current_baseline_state, 'accepted_active');
        assert.equal(target.planned_baseline_state, 'suspension_planned');
        assert.equal(target.future_baseline_state_after_execution, 'suspended');
        assert.equal(target.suspension_execution_performed, false);
        assert.equal(target.accepted_artifact_mutation_performed, false);
    }
});

test('L2V3AS keeps remaining targets blocked_pending_review and does not classify them safe', () => {
    const artifact = mod.runAcceptedMappingBaselineSuspensionPlan({ writeFiles: false }, syntheticOverrides()).artifact;

    assert.equal(artifact.blocked_pending_review_target_count, 3);
    for (const target of artifact.blocked_pending_review_targets) {
        assert.equal(target.suspension_planning_status, 'blocked_pending_evidence');
        assert.equal(target.blocked_pending_review, true);
        assert.equal(target.mapping_suspension_candidate, false);
        assert.equal(target.baseline_suspension_candidate, false);
        assert.equal(target.mapping_suspension_planned, false);
        assert.equal(target.baseline_suspension_planned, false);
        assert.equal(target.re_acceptance_required, false);
        assert.equal(target.raw_write_eligibility_state, 'blocked_pending_reverse_fixture_evidence');
    }
});

test('L2V3AS records suspension state model and re-acceptance prerequisites', () => {
    const artifact = mod.runAcceptedMappingBaselineSuspensionPlan({ writeFiles: false }, syntheticOverrides()).artifact;

    assert.deepEqual(artifact.suspension_state_model, [
        'accepted_active',
        'suspension_required',
        'suspension_planned',
        'suspended',
        're_acceptance_required',
        'blocked_pending_evidence',
        'superseded',
        'rejected',
    ]);
    assert.equal(artifact.what_to_suspend.includes('identity_mapping_acceptance_for_8_confirmed_contradictions'), true);
    assert.equal(artifact.what_to_suspend.includes('baseline_acceptance_for_8_confirmed_contradictions'), true);
    assert.equal(
        artifact.what_not_to_suspend_in_this_phase.includes('do_not_modify_l2v3ae_identity_mapping_acceptance_result'),
        true
    );
    assert.equal(
        artifact.what_not_to_suspend_in_this_phase.includes('do_not_modify_l2v3ag_baseline_acceptance_result'),
        true
    );
    assert.equal(artifact.re_acceptance_prerequisites.includes('runner_input_contract_fixed_or_clarified'), true);
    assert.equal(artifact.re_acceptance_prerequisites.includes('human_review_required'), true);
});

test('L2V3AS report, artifact, and manifest avoid full raw payload markers', () => {
    const result = mod.runAcceptedMappingBaselineSuspensionPlan({ writeFiles: false }, syntheticOverrides());
    const texts = [JSON.stringify(result.artifact), result.report, JSON.stringify(result.updated_manifest)];

    for (const text of texts) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
        assert.equal(text.includes('"source_body":'), false);
    }
});

test('L2V3AS can write artifact, report, and manifest through injected writers', () => {
    const writes = [];
    const result = mod.runAcceptedMappingBaselineSuspensionPlan(
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

test('L2V3AS loadContext can read repository artifacts through default file helpers', () => {
    const context = mod.loadContext();
    const artifact = mod.buildArtifact(context);

    assert.equal(artifact.mapping_suspension_candidate_count, 8);
    assert.equal(artifact.baseline_suspension_candidate_count, 8);
    assert.equal(artifact.blocked_pending_review_target_count, 42);
    assert.equal(artifact.mapping_suspension_planned_count, 8);
    assert.equal(artifact.baseline_suspension_planned_count, 8);
    assert.equal(artifact.re_acceptance_required_count, 8);
    assert.equal(artifact.raw_write_execution_ready, false);
    assert.equal(artifact.payload_recapture_retry_ready, false);
});

test('L2V3AS internal file writers can be exercised without persisting to disk', () => {
    const writes = [];
    const originalWriteFileSync = fs.writeFileSync;

    fs.writeFileSync = function patchedWriteFileSync(filePath, value, encoding) {
        writes.push([String(filePath), String(value), encoding]);
    };

    try {
        const result = mod.runAcceptedMappingBaselineSuspensionPlan();
        assert.equal(result.ok, true);
        assert.equal(writes.length, 3);
        assert.equal(writes[0][0].endsWith(mod.ARTIFACT_OUTPUT_PATH), true);
        assert.equal(writes[1][0].endsWith(mod.REPORT_OUTPUT_PATH), true);
        assert.equal(writes[2][0].endsWith(mod.PROPOSAL_MANIFEST_PATH), true);
    } finally {
        fs.writeFileSync = originalWriteFileSync;
    }
});

test('L2V3AS runCli prints safe planning summary', async () => {
    let output = '';
    const originalWrite = process.stdout.write;
    process.stdout.write = text => {
        output += text;
        return true;
    };

    try {
        await mod.runCli();
    } finally {
        process.stdout.write = originalWrite;
    }

    const parsed = JSON.parse(output);
    assert.equal(parsed.ok, true);
    assert.equal(parsed.phase, 'Phase 5.21L2V3AS');
    assert.equal(parsed.mapping_suspension_candidate_count, 8);
    assert.equal(parsed.baseline_suspension_candidate_count, 8);
    assert.equal(parsed.blocked_pending_review_target_count, 42);
    assert.equal(parsed.mapping_suspension_planned_count, 8);
    assert.equal(parsed.baseline_suspension_planned_count, 8);
    assert.equal(parsed.re_acceptance_required_count, 8);
    assert.equal(parsed.raw_write_execution_ready, false);
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

test('repository L2V3AS artifacts preserve planning-only suspension semantics', () => {
    const artifactPath = path.join(
        PROJECT_ROOT,
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.accepted_mapping_baseline_suspension_plan.phase521l2v3as.json'
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
        path.join(PROJECT_ROOT, 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AS.md'),
        'utf8'
    );

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AS');
    assert.equal(artifact.suspension_planning_status, mod.PLANNING_STATUS);
    assert.equal(artifact.live_fetch_performed, false);
    assert.equal(artifact.detail_fetch_performed, false);
    assert.equal(artifact.network_request_performed, false);
    assert.equal(artifact.recapture_retry_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.mapping_suspension_execution_performed, false);
    assert.equal(artifact.baseline_suspension_execution_performed, false);
    assert.equal(artifact.rollback_execution_performed, false);
    assert.equal(artifact.re_acceptance_execution_performed, false);
    assert.equal(artifact.accepted_artifact_mutation_performed, false);
    assert.equal(artifact.mapping_suspension_candidate_count, 8);
    assert.equal(artifact.baseline_suspension_candidate_count, 8);
    assert.equal(artifact.blocked_pending_review_target_count, 42);
    assert.equal(artifact.mapping_suspension_planned_count, 8);
    assert.equal(artifact.baseline_suspension_planned_count, 8);
    assert.equal(artifact.re_acceptance_required_count, 8);
    assert.equal(artifact.raw_write_execution_ready, false);
    assert.equal(
        artifact.recommended_next_step,
        'Phase 5.21L2V3AT: accepted mapping and baseline suspension execution'
    );

    assert.equal(manifest.phase_5_21_l2v3as_planning_status, artifact.suspension_planning_status);
    assert.equal(manifest.mapping_suspension_planned_count, 8);
    assert.equal(manifest.baseline_suspension_planned_count, 8);
    assert.equal(manifest.raw_write_execution_ready, false);
    assert.match(report, /mapping_suspension_planned_count=8/);
    assert.match(report, /baseline_suspension_planned_count=8/);
    assert.match(report, /raw_write_execution_ready=false/);
});
