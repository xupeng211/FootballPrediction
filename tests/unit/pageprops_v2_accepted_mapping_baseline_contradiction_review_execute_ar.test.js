'use strict';
/* eslint-disable max-lines -- L2V3AR execution tests keep governance assertions explicit. */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const Module = require('node:module');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(
    PROJECT_ROOT,
    'scripts/ops/pageprops_v2_accepted_mapping_baseline_contradiction_review_execute.js'
);

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();

function readyTarget(matchId, scheduleExternalId, observedDetailExternalId) {
    return {
        match_id: matchId,
        schedule_external_id: scheduleExternalId,
        observed_detail_external_id: observedDetailExternalId,
        ae_review_status: 'accepted',
        ag_baseline_acceptance_status: 'accepted_enriched_baseline_metadata',
        source_page_url_base: `/matches/synthetic/${scheduleExternalId}`,
        reverse_fixture_detected: true,
        reverse_fixture_evidence_status: 'reverse_fixture_detected',
        contradiction_review_planned_status: 'contradiction_review_ready',
        accepted_mapping_contradiction: true,
        baseline_acceptance_contradiction: true,
        mapping_follow_up_status: 'suspend_mapping_required',
        baseline_follow_up_status: 'suspend_baseline_required',
        re_acceptance_follow_up_status: 're_acceptance_required',
        contradiction_safe_error_summary:
            'source-controlled review metadata indicates same pageUrl base, reversed teams, and large date gap',
    };
}

function blockedTarget(matchId, scheduleExternalId) {
    return {
        match_id: matchId,
        schedule_external_id: scheduleExternalId,
        observed_detail_external_id: null,
        ae_review_status: 'accepted',
        ag_baseline_acceptance_status: 'accepted_enriched_baseline_metadata',
        source_page_url_base: `/matches/synthetic/${scheduleExternalId}`,
        reverse_fixture_detected: false,
        reverse_fixture_evidence_status: 'unknown',
        contradiction_review_planned_status: 'blocker_investigation_required',
        accepted_mapping_contradiction: false,
        baseline_acceptance_contradiction: false,
        mapping_follow_up_status: 'contradiction_not_reviewed',
        baseline_follow_up_status: 'contradiction_not_reviewed',
        re_acceptance_follow_up_status: 'blocker_investigation_required',
        contradiction_safe_error_summary:
            'observed detail metadata is unavailable in source-controlled artifacts; date rule status remains unknown and blocked',
    };
}

function syntheticAqPlan() {
    return {
        proposal_phase: 'Phase 5.21L2V3AQ',
        planning_status: 'completed_accepted_mapping_baseline_contradiction_review_planning',
        accepted_mapping_count: 5,
        baseline_accepted_count: 5,
        accepted_mapping_contradiction_count: 2,
        baseline_acceptance_contradiction_count: 2,
        contradiction_review_candidate_count: 5,
        contradiction_review_ready_count: 2,
        contradiction_review_blocked_count: 3,
        runner_contract_fix_planning_required: true,
        raw_write_execution_ready: false,
        payload_recapture_retry_ready: false,
        review_targets: [
            readyTarget('53_20252026_4830466', '4830466', '4830759'),
            readyTarget('53_20252026_4830461', '4830461', '4830758'),
            blockedTarget('53_20252026_4830458', '4830458'),
            blockedTarget('53_20252026_4830459', '4830459'),
            blockedTarget('53_20252026_4830460', '4830460'),
        ],
    };
}

function syntheticManifest() {
    return {
        batch_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        recommended_next_step: 'Phase 5.21L2V3AR: accepted mapping and baseline contradiction review execution',
        next_required_step: 'accepted_mapping_and_baseline_contradiction_review_execution',
        raw_write_execution_ready: false,
    };
}

function syntheticOverrides() {
    return {
        aqPlan: syntheticAqPlan(),
        manifest: syntheticManifest(),
        generatedAt: '2026-05-26T00:00:00.000Z',
    };
}

test('L2V3AR is contradiction review execution and still avoids fetch, retry, DB write, raw write, and suspension execution', () => {
    const result = mod.runAcceptedMappingBaselineContradictionReviewExecute(
        { writeFiles: false },
        syntheticOverrides()
    );
    const artifact = result.artifact;
    const manifest = result.updated_manifest;

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AR');
    assert.equal(artifact.phase_name, 'accepted_mapping_baseline_contradiction_review_execution');
    assert.equal(artifact.contradiction_review_execution_performed, true);
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
    assert.equal(artifact.re_acceptance_execution_performed, false);
    assert.equal(artifact.mapping_rollback_execution_performed, false);
    assert.equal(artifact.baseline_rollback_execution_performed, false);
    assert.equal(artifact.accepted_artifact_mutation_performed, false);
    assert.equal(artifact.baseline_artifact_mutation_performed, false);
    assert.equal(artifact.raw_write_execution_ready, false);
    assert.equal(artifact.payload_recapture_retry_ready, false);
    assert.equal(manifest.phase_5_21_l2v3ar_execution_status, artifact.execution_status);
    assert.equal(manifest.raw_write_execution_ready, false);
});

test('L2V3AR confirms reverse-fixture accepted mapping and baseline contradictions', () => {
    const artifact = mod.runAcceptedMappingBaselineContradictionReviewExecute(
        { writeFiles: false },
        syntheticOverrides()
    ).artifact;

    assert.equal(artifact.contradiction_review_candidate_count, 5);
    assert.equal(artifact.contradiction_reviewed_count, 5);
    assert.equal(artifact.contradiction_confirmed_count, 2);
    assert.equal(artifact.contradiction_not_confirmed_count, 0);
    assert.equal(artifact.contradiction_blocked_pending_evidence_count, 3);
    assert.equal(artifact.accepted_mapping_contradiction_confirmed_count, 2);
    assert.equal(artifact.baseline_acceptance_contradiction_confirmed_count, 2);
    assert.equal(artifact.mapping_suspension_required_count, 2);
    assert.equal(artifact.baseline_suspension_required_count, 2);
    assert.equal(artifact.re_acceptance_required_count, 2);
    assert.equal(artifact.runner_contract_fix_required, true);
    assert.equal(artifact.expanded_review_required, true);
    assert.equal(artifact.recommended_next_step, 'Phase 5.21L2V3AS: accepted mapping and baseline suspension planning');
    assert.equal(artifact.next_required_step, 'accepted_mapping_and_baseline_suspension_planning');
});

test('L2V3AR keeps blocked targets blocked_pending_review instead of treating them as clean', () => {
    const artifact = mod.runAcceptedMappingBaselineContradictionReviewExecute(
        { writeFiles: false },
        syntheticOverrides()
    ).artifact;
    const blockedTargets = artifact.review_targets.filter(
        target => target.contradiction_review_status === 'contradiction_blocked_pending_evidence'
    );

    assert.equal(blockedTargets.length, 3);
    for (const target of blockedTargets) {
        assert.equal(target.accepted_mapping_contradiction_confirmed, false);
        assert.equal(target.baseline_acceptance_contradiction_confirmed, false);
        assert.equal(target.mapping_suspension_required, false);
        assert.equal(target.baseline_suspension_required, false);
        assert.equal(target.re_acceptance_required, false);
        assert.equal(target.raw_write_execution_ready, false);
        assert.equal(target.payload_recapture_retry_ready, false);
        assert.equal(target.review_blocker_status, 'insufficient_reverse_fixture_evidence_blocked_pending_review');
    }
});

test('L2V3AR treats hash mismatch as secondary and page URL evidence alone as insufficient', () => {
    const artifact = mod.runAcceptedMappingBaselineContradictionReviewExecute(
        { writeFiles: false },
        syntheticOverrides()
    ).artifact;
    const confirmedTarget = artifact.review_targets.find(
        target => target.contradiction_review_status === 'contradiction_confirmed'
    );

    assert.equal(artifact.hash_mismatch_baseline_update_allowed, false);
    assert.equal(artifact.page_url_base_slug_fragment_evidence_alone_sufficient, false);
    assert.equal(confirmedTarget.hash_mismatch_classification, 'secondary_to_identity_mismatch_reverse_fixture');
    assert.equal(confirmedTarget.hash_mismatch_baseline_update_allowed, false);
    assert.equal(confirmedTarget.page_url_base_slug_fragment_evidence_sufficient_for_acceptance, false);
    assert.equal(
        confirmedTarget.page_url_base_slug_fragment_evidence_review_result,
        'insufficient_against_reverse_fixture_evidence'
    );
});

test('L2V3AR report, artifact, and manifest avoid full raw payload markers', () => {
    const result = mod.runAcceptedMappingBaselineContradictionReviewExecute(
        { writeFiles: false },
        syntheticOverrides()
    );
    const texts = [JSON.stringify(result.artifact), result.report, JSON.stringify(result.updated_manifest)];

    for (const text of texts) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
        assert.equal(text.includes('"source_body":'), false);
    }
});

test('L2V3AR can write artifact, report, and manifest through injected writers', () => {
    const writes = [];
    const result = mod.runAcceptedMappingBaselineContradictionReviewExecute(
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

test('L2V3AR loadContext can read repository artifacts through default file helpers', () => {
    const context = mod.loadContext();
    const artifact = mod.buildArtifact(context);

    assert.equal(artifact.contradiction_review_candidate_count, 50);
    assert.equal(artifact.contradiction_reviewed_count, 50);
    assert.equal(artifact.contradiction_confirmed_count, 8);
    assert.equal(artifact.contradiction_blocked_pending_evidence_count, 42);
    assert.equal(artifact.accepted_mapping_contradiction_confirmed_count, 8);
    assert.equal(artifact.baseline_acceptance_contradiction_confirmed_count, 8);
    assert.equal(artifact.mapping_suspension_required_count, 8);
    assert.equal(artifact.baseline_suspension_required_count, 8);
    assert.equal(artifact.raw_write_execution_ready, false);
});

test('L2V3AR internal file writers can be exercised without persisting to disk', () => {
    const writes = [];
    const originalWriteFileSync = fs.writeFileSync;

    fs.writeFileSync = function patchedWriteFileSync(filePath, value, encoding) {
        writes.push([String(filePath), String(value), encoding]);
    };

    try {
        const result = mod.runAcceptedMappingBaselineContradictionReviewExecute();
        assert.equal(result.ok, true);
        assert.equal(writes.length, 3);
        assert.equal(writes[0][0].endsWith(mod.ARTIFACT_OUTPUT_PATH), true);
        assert.equal(writes[1][0].endsWith(mod.REPORT_OUTPUT_PATH), true);
        assert.equal(writes[2][0].endsWith(mod.PROPOSAL_MANIFEST_PATH), true);
    } finally {
        fs.writeFileSync = originalWriteFileSync;
    }
});

test('L2V3AR runCli prints safe execution summary', async () => {
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
    assert.equal(parsed.phase, 'Phase 5.21L2V3AR');
    assert.equal(parsed.contradiction_review_candidate_count, 50);
    assert.equal(parsed.contradiction_reviewed_count, 50);
    assert.equal(parsed.contradiction_confirmed_count, 8);
    assert.equal(parsed.contradiction_blocked_pending_evidence_count, 42);
    assert.equal(parsed.accepted_mapping_contradiction_confirmed_count, 8);
    assert.equal(parsed.baseline_acceptance_contradiction_confirmed_count, 8);
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

test('repository L2V3AR artifacts preserve contradiction review execution semantics', () => {
    const artifactPath = path.join(
        PROJECT_ROOT,
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.accepted_mapping_baseline_contradiction_review_result.phase521l2v3ar.json'
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
        path.join(PROJECT_ROOT, 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AR.md'),
        'utf8'
    );

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AR');
    assert.equal(artifact.contradiction_review_execution_performed, true);
    assert.equal(artifact.live_fetch_performed, false);
    assert.equal(artifact.detail_fetch_performed, false);
    assert.equal(artifact.network_request_performed, false);
    assert.equal(artifact.recapture_retry_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.mapping_suspension_execution_performed, false);
    assert.equal(artifact.baseline_suspension_execution_performed, false);
    assert.equal(artifact.re_acceptance_execution_performed, false);
    assert.equal(artifact.contradiction_review_candidate_count, 50);
    assert.equal(artifact.contradiction_reviewed_count, 50);
    assert.equal(artifact.contradiction_confirmed_count, 8);
    assert.equal(artifact.contradiction_blocked_pending_evidence_count, 42);
    assert.equal(artifact.accepted_mapping_contradiction_confirmed_count, 8);
    assert.equal(artifact.baseline_acceptance_contradiction_confirmed_count, 8);
    assert.equal(artifact.mapping_suspension_required_count, 8);
    assert.equal(artifact.baseline_suspension_required_count, 8);
    assert.equal(artifact.raw_write_execution_ready, false);
    assert.equal(artifact.recommended_next_step, 'Phase 5.21L2V3AS: accepted mapping and baseline suspension planning');

    assert.equal(manifest.phase_5_21_l2v3ar_execution_status, artifact.execution_status);
    assert.equal(manifest.contradiction_review_execution_performed, true);
    assert.equal(manifest.contradiction_confirmed_count, 8);
    assert.equal(manifest.contradiction_blocked_pending_evidence_count, 42);
    assert.equal(manifest.raw_write_execution_ready, false);
    assert.match(report, /accepted_mapping_contradiction_confirmed_count=8/);
    assert.match(report, /baseline_acceptance_contradiction_confirmed_count=8/);
    assert.match(report, /raw_write_execution_ready=false/);
});
