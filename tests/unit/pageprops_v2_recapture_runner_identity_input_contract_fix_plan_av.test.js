'use strict';
/* eslint-disable max-lines -- L2V3AV planning tests keep governance assertions explicit. */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const Module = require('node:module');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(
    PROJECT_ROOT,
    'scripts/ops/pageprops_v2_recapture_runner_identity_input_contract_fix_plan.js'
);

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();

function suspendedTarget(index) {
    const scheduleExternalId = index === 0 ? '4830466' : String(4830460 + index);
    const observedDetailExternalId = index === 0 ? '4830759' : String(4830750 + index);
    return {
        match_id: `53_20252026_${scheduleExternalId}`,
        schedule_external_id: scheduleExternalId,
        source_url_fragment_external_id: scheduleExternalId,
        source_page_url_base: `/matches/synthetic/${scheduleExternalId}`,
        observed_detail_external_id: observedDetailExternalId,
        current_mapping_effective_status: 'suspended',
        current_baseline_effective_status: 'suspended',
        raw_write_execution_ready: false,
        payload_recapture_retry_ready: false,
        re_acceptance_execution_performed: false,
        suspension_reversal_performed: false,
        rollback_execution_performed: false,
    };
}

function syntheticAuPlan() {
    return {
        proposal_phase: 'Phase 5.21L2V3AU',
        re_acceptance_prerequisite_planning_status: 'completed_re_acceptance_prerequisite_planning',
        suspended_mapping_count: 8,
        suspended_baseline_count: 8,
        blocked_pending_review_target_count: 42,
        runner_contract_fix_prerequisite_required: true,
        expanded_review_prerequisite_required: true,
        fresh_final_authorization_required: true,
        payload_recapture_retry_ready: false,
        raw_write_execution_ready: false,
        re_acceptance_execution_performed: false,
        suspension_reversal_performed: false,
        rollback_execution_performed: false,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        suspended_targets_requiring_prerequisites: Array.from({ length: 8 }, (_, index) => suspendedTarget(index)),
    };
}

function syntheticAoResult() {
    return {
        per_target_results: [
            {
                match_id: '53_20252026_4830466',
                external_id: '4830466',
                schedule_external_id: '4830466',
                source_url_fragment_external_id: '4830466',
                request_url_external_id: '4830466',
                observed_detail_external_id: '4830759',
                identity_match_status: 'mismatch',
                date_compatibility_status: 'reverse_fixture_detected',
                page_url_base_match_status: 'match',
                hash_validation_status: 'hash_mismatch',
                blocker_list: ['identity_mismatch', 'reverse_fixture_detected'],
            },
        ],
    };
}

function syntheticApInvestigation() {
    return {
        accepted_source_page_url: '/matches/marseille-vs-rennes/2t9n7h#4830466',
        accepted_source_page_url_base: '/matches/marseille-vs-rennes/2t9n7h',
        source_url_fragment_external_id: '4830466',
        page_url_base_match_status: 'match',
        likely_root_cause:
            'accepted mapping and baseline accepted schedule-side slug/fragment evidence without resolved detail identity',
    };
}

function syntheticOverrides(extra = {}) {
    return {
        generatedAt: '2026-05-27T00:00:00.000Z',
        manifest: {
            batch_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
            recommended_next_step: 'Phase 5.21L2V3AV: recapture runner identity input contract fix planning',
            raw_write_execution_ready: false,
        },
        auPlan: syntheticAuPlan(),
        atResult: {},
        apInvestigation: syntheticApInvestigation(),
        aoResult: syntheticAoResult(),
        noWriteRecaptureHelperSource: `
function resolveFetchResultForTarget(target) {
    const requestUrl = buildFotMobMatchUrl(target.external_id);
    return fetchHtmlFn(requestUrl);
}
function recaptureTarget(target) {
    return reconcileRouteIdentity({ requestedScheduleExternalId: target.external_id });
}
`,
        rawDetailFetcherSource: 'function buildFotMobMatchUrl(externalId) { return externalId; }',
        routeIdentityReconcilerSource: 'function reconcileRouteIdentity() { return {}; }',
        ...extra,
    };
}

test('L2V3AV is planning-only and does not perform runner implementation or write/fetch actions', () => {
    const result = mod.runRunnerIdentityContractFixPlan({ writeFiles: false }, syntheticOverrides());
    const artifact = result.artifact;
    const manifest = result.updated_manifest;

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AV');
    assert.equal(artifact.phase_name, 'recapture_runner_identity_input_contract_fix_planning');
    assert.equal(artifact.runner_identity_contract_fix_planning_status, mod.PLANNING_STATUS);
    assert.equal(artifact.implementation_required, true);
    assert.equal(artifact.implementation_performed, false);
    assert.equal(artifact.live_fetch_performed, false);
    assert.equal(artifact.detail_fetch_performed, false);
    assert.equal(artifact.network_request_performed, false);
    assert.equal(artifact.recapture_retry_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.raw_write_execution_performed, false);
    assert.equal(artifact.re_acceptance_execution_performed, false);
    assert.equal(artifact.suspension_reversal_performed, false);
    assert.equal(artifact.rollback_execution_performed, false);
    assert.equal(manifest.phase_5_21_l2v3av_planning_status, mod.PLANNING_STATUS);
});

test('L2V3AV represents requested 4830466 observed 4830759 as a blocking contract issue', () => {
    const artifact = mod.runRunnerIdentityContractFixPlan({ writeFiles: false }, syntheticOverrides()).artifact;

    assert.equal(artifact.current_runner_schedule_side_route_issue_confirmed, true);
    assert.equal(artifact.schedule_side_route_detected_in_current_runner, true);
    assert.equal(artifact.runner_uses_accepted_source_page_url_as_request_contract, false);
    assert.equal(artifact.requested_observed_mismatch_example, mod.REQUESTED_OBSERVED_MISMATCH_EXAMPLE);
    assert.equal(artifact.requested_external_id, '4830466');
    assert.equal(artifact.observed_detail_external_id, '4830759');
    assert.equal(artifact.identity_match_status, 'mismatch');
    assert.equal(artifact.date_compatibility_status, 'reverse_fixture_detected');
    assert.equal(artifact.page_url_base_slug_fragment_alone_insufficient, true);
});

test('L2V3AV plans the required contract fields and input priority order', () => {
    const artifact = mod.runRunnerIdentityContractFixPlan({ writeFiles: false }, syntheticOverrides()).artifact;
    const fieldIds = artifact.planned_contract_fields.map(field => field.id);
    const priorityIds = artifact.planned_input_priority_order.map(item => item.id);

    assert.equal(artifact.planned_contract_field_count, 10);
    assert.deepEqual(fieldIds, [
        'schedule_external_id',
        'source_url_fragment_external_id',
        'source_page_url',
        'source_page_url_base',
        'accepted_detail_external_id',
        'observed_detail_external_id',
        'recapture_request_identity',
        'recapture_expected_identity',
        'route_identity_strategy',
        'canonical_identity_source',
    ]);
    assert.equal(priorityIds.includes('use_schedule_external_id_only_as_correlation_key'), true);
    assert.equal(priorityIds.includes('use_reaccepted_accepted_detail_external_id_as_expected_identity'), true);
    assert.equal(priorityIds[0], 'block_if_current_effective_mapping_or_baseline_suspended');
});

test('L2V3AV plans blocking rules for mismatch, suspension, missing re-acceptance, and baseline hash safety', () => {
    const artifact = mod.runRunnerIdentityContractFixPlan({ writeFiles: false }, syntheticOverrides()).artifact;
    const ruleIds = artifact.planned_blocking_rules.map(rule => rule.id);

    assert.equal(artifact.planned_blocking_rule_count, 7);
    assert.equal(ruleIds.includes('identity_mismatch_blocks_recapture_retry'), true);
    assert.equal(ruleIds.includes('reverse_fixture_detected_blocks_recapture_retry'), true);
    assert.equal(ruleIds.includes('page_url_base_match_alone_insufficient'), true);
    assert.equal(ruleIds.includes('suspended_mapping_or_baseline_blocks_retry'), true);
    assert.equal(ruleIds.includes('missing_accepted_mapping_blocks_retry'), true);
    assert.equal(ruleIds.includes('missing_re_acceptance_blocks_retry'), true);
    assert.equal(ruleIds.includes('hash_mismatch_under_identity_mismatch_cannot_update_baseline'), true);
    assert.equal(artifact.hash_mismatch_under_identity_mismatch_secondary, true);
});

test('L2V3AV keeps suspended mappings and baselines blocked from retry', () => {
    const artifact = mod.runRunnerIdentityContractFixPlan({ writeFiles: false }, syntheticOverrides()).artifact;

    assert.equal(artifact.suspended_mapping_count, 8);
    assert.equal(artifact.suspended_baseline_count, 8);
    assert.equal(artifact.blocked_pending_review_target_count, 42);
    assert.equal(artifact.suspended_mapping_baseline_blocks_retry, true);
    for (const target of artifact.suspended_targets_contract_plan) {
        assert.equal(target.current_mapping_effective_status, 'suspended');
        assert.equal(target.current_baseline_effective_status, 'suspended');
        assert.equal(target.retry_blocked, true);
        assert.equal(target.recapture_request_identity, 'blocked_until_reaccepted_contract');
        assert.equal(target.recapture_expected_identity, 'blocked_until_reaccepted_contract');
        assert.equal(target.canonical_identity_source, 'none_until_mapping_baseline_reaccepted');
    }
});

test('L2V3AV rejects invalid AU prerequisite inputs before planning', () => {
    const invalidAuPlan = {
        ...syntheticAuPlan(),
        proposal_phase: 'Phase 5.21L2V3AT',
        suspended_mapping_count: 7,
        suspended_baseline_count: 7,
        blocked_pending_review_target_count: 41,
        runner_contract_fix_prerequisite_required: false,
        raw_write_execution_ready: true,
        re_acceptance_execution_performed: true,
    };

    const errors = mod.validateAuPrerequisitePlan(invalidAuPlan);
    assert.equal(errors.length >= 5, true);
    assert.throws(
        () =>
            mod.runRunnerIdentityContractFixPlan(
                { writeFiles: false },
                {
                    ...syntheticOverrides(),
                    auPlan: invalidAuPlan,
                }
            ),
        /Cannot plan L2V3AV runner contract fix/
    );
});

test('L2V3AV can represent an unconfirmed runner route issue without advancing readiness', () => {
    const auPlan = {
        ...syntheticAuPlan(),
        suspended_targets_requiring_prerequisites: Array.from({ length: 8 }, (_, index) => ({
            ...suspendedTarget(index),
            schedule_external_id: String(4830600 + index),
            observed_detail_external_id: String(4830600 + index),
        })),
    };
    const result = mod.runRunnerIdentityContractFixPlan(
        { writeFiles: false },
        {
            ...syntheticOverrides(),
            auPlan,
            aoResult: {
                per_target_results: [
                    {
                        external_id: '4830466',
                        schedule_external_id: '4830466',
                        observed_detail_external_id: '4830466',
                        identity_match_status: 'identity_match',
                    },
                ],
            },
            noWriteRecaptureHelperSource: 'function recaptureTarget(target) { return target.source_page_url; }',
        }
    );
    const artifact = result.artifact;

    assert.equal(artifact.current_runner_schedule_side_route_issue_confirmed, false);
    assert.equal(artifact.schedule_side_route_detected_in_current_runner, false);
    assert.equal(artifact.requested_observed_mismatch_example, '4830466->4830466');
    assert.equal(artifact.raw_write_execution_ready, false);
    assert.equal(artifact.payload_recapture_retry_ready, false);
    assert.equal(artifact.implementation_performed, false);
});

test('L2V3AV suspended target contract builder preserves explicit source fields and default blockers', () => {
    const target = mod.buildSuspendedContractTarget({
        match_id: '53_20252026_4830999',
        schedule_external_id: '4830999',
        source_url_fragment_external_id: '4831888',
        source_page_url: '/matches/a-vs-b/abc#4831888',
        source_page_url_base: '/matches/a-vs-b/abc',
        observed_detail_external_id: '4831888',
    });

    assert.equal(target.source_url_fragment_external_id, '4831888');
    assert.equal(target.source_page_url, '/matches/a-vs-b/abc#4831888');
    assert.equal(target.source_page_url_base, '/matches/a-vs-b/abc');
    assert.equal(target.observed_detail_external_id, '4831888');
    assert.equal(target.accepted_detail_external_id, null);
    assert.equal(target.retry_blocked, true);
    assert.deepEqual(target.retry_blockers, [
        'suspended_mapping_or_baseline',
        'missing_re_acceptance',
        'fresh_final_authorization_required',
    ]);
});

test('L2V3AV report, artifact, and manifest avoid full payload markers', () => {
    const result = mod.runRunnerIdentityContractFixPlan({ writeFiles: false }, syntheticOverrides());
    const texts = [JSON.stringify(result.artifact), result.report, JSON.stringify(result.updated_manifest)];

    for (const text of texts) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
        assert.equal(text.includes('"source_body":'), false);
    }
});

test('L2V3AV can write artifact, report, and manifest through injected writers', () => {
    const writes = [];
    const result = mod.runRunnerIdentityContractFixPlan(
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

test('L2V3AV runCli prints a safe planning summary', async () => {
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
    assert.equal(parsed.phase, 'Phase 5.21L2V3AV');
    assert.equal(typeof parsed.current_runner_schedule_side_route_issue_confirmed, 'boolean');
    assert.equal(parsed.requested_observed_mismatch_example, mod.REQUESTED_OBSERVED_MISMATCH_EXAMPLE);
    assert.equal(parsed.implementation_required, true);
    assert.equal(parsed.implementation_performed, false);
    assert.equal(parsed.raw_write_execution_ready, false);
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

test('repository L2V3AV artifacts preserve planning-only semantics when generated', () => {
    const artifactPath = path.join(
        PROJECT_ROOT,
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.recapture_runner_identity_input_contract_fix_plan.phase521l2v3av.json'
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
        path.join(PROJECT_ROOT, 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AV.md'),
        'utf8'
    );

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AV');
    assert.equal(artifact.runner_identity_contract_fix_planning_status, mod.PLANNING_STATUS);
    assert.equal(artifact.current_runner_schedule_side_route_issue_confirmed, true);
    assert.equal(artifact.requested_observed_mismatch_example, mod.REQUESTED_OBSERVED_MISMATCH_EXAMPLE);
    assert.equal(artifact.planned_contract_field_count, 10);
    assert.equal(artifact.planned_blocking_rule_count, 7);
    assert.equal(artifact.implementation_required, true);
    assert.equal(artifact.implementation_performed, false);
    assert.equal(artifact.live_fetch_performed, false);
    assert.equal(artifact.recapture_retry_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.raw_write_execution_performed, false);
    assert.equal(artifact.raw_write_execution_ready, false);
    assert.equal(manifest.phase_5_21_l2v3av_planning_status, mod.PLANNING_STATUS);
    assert.match(report, /requested_observed_mismatch_example=4830466->4830759/);
    assert.match(report, /no runner implementation/);
});
