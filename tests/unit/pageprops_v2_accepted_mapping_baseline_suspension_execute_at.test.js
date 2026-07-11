'use strict';
/* eslint-disable max-lines -- L2V3AT execution tests keep governance assertions explicit. */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const Module = require('node:module');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_accepted_mapping_baseline_suspension_execute.js');

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();

function plannedTarget(matchId, scheduleExternalId, observedDetailExternalId) {
    return {
        match_id: matchId,
        schedule_external_id: scheduleExternalId,
        observed_detail_external_id: observedDetailExternalId,
        source_page_url_base: `/matches/synthetic/${scheduleExternalId}`,
        suspension_reason: 'reverse_fixture_contradiction_confirmed',
        current_mapping_state: 'accepted_active',
        planned_mapping_state: 'suspension_planned',
        future_mapping_state_after_execution: 'suspended',
        current_baseline_state: 'accepted_active',
        planned_baseline_state: 'suspension_planned',
        future_baseline_state_after_execution: 'suspended',
        mapping_suspension_planned: true,
        baseline_suspension_planned: true,
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
        suspension_planning_status: 'blocked_pending_evidence',
        blocked_pending_review: true,
        required_future_review: 'expanded_reverse_fixture_evidence_review_required',
        raw_write_execution_ready: false,
        payload_recapture_retry_ready: false,
    };
}

function syntheticAsPlan() {
    return {
        proposal_phase: 'Phase 5.21L2V3AS',
        suspension_planning_status: 'completed_accepted_mapping_baseline_suspension_planning',
        mapping_suspension_candidate_count: 8,
        baseline_suspension_candidate_count: 8,
        blocked_pending_review_target_count: 42,
        mapping_suspension_planned_count: 8,
        baseline_suspension_planned_count: 8,
        re_acceptance_required_count: 8,
        raw_write_execution_ready: false,
        payload_recapture_retry_ready: false,
        suspension_targets: [
            plannedTarget('53_20252026_4830466', '4830466', '4830759'),
            plannedTarget('53_20252026_4830461', '4830461', '4830758'),
        ],
        blocked_pending_review_targets: [
            blockedTarget('53_20252026_4830458', '4830458'),
            blockedTarget('53_20252026_4830459', '4830459'),
            blockedTarget('53_20252026_4830460', '4830460'),
        ],
    };
}

function syntheticManifest() {
    return {
        batch_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        recommended_next_step: 'Phase 5.21L2V3AT: accepted mapping and baseline suspension execution',
        next_required_step: 'accepted_mapping_and_baseline_suspension_execution',
        raw_write_execution_ready: false,
        payload_recapture_retry_ready: false,
    };
}

function syntheticOverrides() {
    return {
        asPlan: syntheticAsPlan(),
        manifest: syntheticManifest(),
        generatedAt: '2026-05-26T00:00:00.000Z',
    };
}

test('L2V3AT is suspension execution and avoids fetch, retry, DB write, raw write, rollback, and re-acceptance', () => {
    const result = mod.runAcceptedMappingBaselineSuspensionExecute({ writeFiles: false }, syntheticOverrides());
    const artifact = result.artifact;
    const manifest = result.updated_manifest;

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AT');
    assert.equal(artifact.phase_name, 'accepted_mapping_baseline_suspension_execution');
    assert.equal(artifact.suspension_execution_performed, true);
    assert.equal(artifact.mapping_suspension_execution_performed, true);
    assert.equal(artifact.baseline_suspension_execution_performed, true);
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
    assert.equal(artifact.rollback_execution_performed, false);
    assert.equal(artifact.re_acceptance_execution_performed, false);
    assert.equal(artifact.historical_accepted_artifacts_mutated, false);
    assert.equal(artifact.raw_write_execution_ready, false);
    assert.equal(artifact.payload_recapture_retry_ready, false);
    assert.equal(manifest.phase_5_21_l2v3at_execution_status, artifact.execution_status);
    assert.equal(manifest.raw_write_execution_ready, false);
});

test('L2V3AT records current effective suspension for mapping and baseline contradictions', () => {
    const artifact = mod.runAcceptedMappingBaselineSuspensionExecute(
        { writeFiles: false },
        syntheticOverrides()
    ).artifact;

    assert.equal(artifact.mapping_suspended_count, 2);
    assert.equal(artifact.baseline_suspended_count, 2);
    assert.equal(artifact.re_acceptance_required_count, 2);
    assert.equal(artifact.runner_contract_fix_planning_required, true);
    assert.equal(artifact.expanded_review_required, true);

    for (const target of artifact.suspended_targets) {
        assert.equal(target.previous_mapping_effective_status, 'accepted_active');
        assert.equal(target.current_mapping_effective_status, 'suspended');
        assert.equal(target.previous_baseline_effective_status, 'accepted_active');
        assert.equal(target.current_baseline_effective_status, 'suspended');
        assert.equal(target.current_effective_status, 'suspended');
        assert.equal(target.current_raw_write_status, 'raw_write_blocked');
        assert.equal(target.re_acceptance_required, true);
        assert.equal(target.raw_write_execution_ready, false);
    }
});

test('L2V3AT keeps remaining targets blocked_pending_review', () => {
    const artifact = mod.runAcceptedMappingBaselineSuspensionExecute(
        { writeFiles: false },
        syntheticOverrides()
    ).artifact;

    assert.equal(artifact.blocked_pending_review_target_count, 3);
    for (const target of artifact.blocked_pending_review_targets) {
        assert.equal(target.current_effective_status, 'blocked_pending_review');
        assert.equal(target.current_raw_write_status, 'raw_write_blocked');
        assert.equal(target.suspension_execution_performed, false);
        assert.equal(target.re_acceptance_required, false);
        assert.equal(target.raw_write_execution_ready, false);
        assert.equal(target.payload_recapture_retry_ready, false);
    }
});

test('L2V3AT blocks final DB-write authorization for current raw-write plan', () => {
    const result = mod.runAcceptedMappingBaselineSuspensionExecute({ writeFiles: false }, syntheticOverrides());
    const artifact = result.artifact;
    const manifest = result.updated_manifest;

    assert.equal(artifact.final_db_write_authorization_historical_artifact_retained, true);
    assert.equal(artifact.final_db_write_authorization_effective_status, mod.FINAL_AUTHORIZATION_EFFECTIVE_STATUS);
    assert.equal(artifact.final_db_write_authorization_usable_for_raw_write, false);
    assert.equal(artifact.raw_write_reauthorization_required_after_re_acceptance, true);
    assert.equal(manifest.final_db_write_authorization_effective_status, mod.FINAL_AUTHORIZATION_EFFECTIVE_STATUS);
    assert.equal(manifest.final_db_write_authorization_usable_for_raw_write, false);
    assert.equal(artifact.recommended_next_step, 'Phase 5.21L2V3AU: re-acceptance prerequisite planning');
    assert.equal(artifact.next_required_step, 're_acceptance_prerequisite_planning');
});

test('L2V3AT report, artifact, and manifest avoid full raw payload markers', () => {
    const result = mod.runAcceptedMappingBaselineSuspensionExecute({ writeFiles: false }, syntheticOverrides());
    const texts = [JSON.stringify(result.artifact), result.report, JSON.stringify(result.updated_manifest)];

    for (const text of texts) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
        assert.equal(text.includes('"source_body":'), false);
    }
});

test('L2V3AT can write artifact, report, and manifest through injected writers', () => {
    const writes = [];
    const result = mod.runAcceptedMappingBaselineSuspensionExecute(
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

test('L2V3AT loadContext can read repository artifacts through default file helpers', () => {
    const context = mod.loadContext();
    const artifact = mod.buildArtifact(context);

    assert.equal(artifact.mapping_suspended_count, 8);
    assert.equal(artifact.baseline_suspended_count, 8);
    assert.equal(artifact.blocked_pending_review_target_count, 42);
    assert.equal(artifact.re_acceptance_required_count, 8);
    assert.equal(artifact.raw_write_execution_ready, false);
    assert.equal(artifact.payload_recapture_retry_ready, false);
});

test('L2V3AT internal file writers can be exercised without persisting to disk', () => {
    const writes = [];
    const originalWriteFileSync = fs.writeFileSync;

    fs.writeFileSync = function patchedWriteFileSync(filePath, value, encoding) {
        writes.push([String(filePath), String(value), encoding]);
    };

    try {
        const result = mod.runAcceptedMappingBaselineSuspensionExecute();
        assert.equal(result.ok, true);
        assert.equal(writes.length, 3);
        assert.equal(writes[0][0].endsWith(mod.ARTIFACT_OUTPUT_PATH), true);
        assert.equal(writes[1][0].endsWith(mod.REPORT_OUTPUT_PATH), true);
        assert.equal(writes[2][0].endsWith(mod.PROPOSAL_MANIFEST_PATH), true);
    } finally {
        fs.writeFileSync = originalWriteFileSync;
    }
});

test('L2V3AT runCli prints safe execution summary', async () => {
    let output = '';
    const writes = [];
    const originalWriteFileSync = fs.writeFileSync;
    const originalWrite = process.stdout.write;
    process.stdout.write = text => {
        output += text;
        return true;
    };
    fs.writeFileSync = (...args) => {
        writes.push(args);
    };

    try {
        await mod.runCli();
    } finally {
        process.stdout.write = originalWrite;
        fs.writeFileSync = originalWriteFileSync;
    }

    assert.equal(writes.length, 3);
    const parsed = JSON.parse(output);
    assert.equal(parsed.ok, true);
    assert.equal(parsed.phase, 'Phase 5.21L2V3AT');
    assert.equal(parsed.mapping_suspended_count, 8);
    assert.equal(parsed.baseline_suspended_count, 8);
    assert.equal(parsed.blocked_pending_review_target_count, 42);
    assert.equal(parsed.re_acceptance_required_count, 8);
    assert.equal(parsed.raw_write_execution_ready, false);
    assert.equal(parsed.final_db_write_authorization_effective_status, mod.FINAL_AUTHORIZATION_EFFECTIVE_STATUS);
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

test('repository L2V3AT artifacts preserve suspension execution semantics when generated', () => {
    const artifactPath = path.join(
        PROJECT_ROOT,
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.accepted_mapping_baseline_suspension_result.phase521l2v3at.json'
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
        path.join(PROJECT_ROOT, 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AT.md'),
        'utf8'
    );

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AT');
    assert.equal(artifact.execution_status, mod.EXECUTION_STATUS);
    assert.equal(artifact.suspension_execution_performed, true);
    assert.equal(artifact.mapping_suspension_execution_performed, true);
    assert.equal(artifact.baseline_suspension_execution_performed, true);
    assert.equal(artifact.mapping_suspended_count, 8);
    assert.equal(artifact.baseline_suspended_count, 8);
    assert.equal(artifact.blocked_pending_review_target_count, 42);
    assert.equal(artifact.re_acceptance_required_count, 8);
    assert.equal(artifact.historical_accepted_artifacts_mutated, false);
    assert.equal(artifact.rollback_execution_performed, false);
    assert.equal(artifact.re_acceptance_execution_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.raw_write_execution_performed, false);
    assert.equal(artifact.raw_write_execution_ready, false);
    assert.equal(artifact.final_db_write_authorization_effective_status, mod.FINAL_AUTHORIZATION_EFFECTIVE_STATUS);

    assert.equal(manifest.phase_5_21_l2v3at_execution_status, artifact.execution_status);
    assert.equal(manifest.mapping_suspended_count, 8);
    assert.equal(manifest.baseline_suspended_count, 8);
    assert.equal(manifest.raw_write_execution_ready, false);
    assert.match(report, /mapping_suspended_count=8/);
    assert.match(report, /baseline_suspended_count=8/);
    assert.match(report, /final_db_write_authorization_effective_status=blocked_or_superseded/);
});
