'use strict';
/* eslint-disable max-lines -- L2V3AQ planning tests keep governance assertions explicit. */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const Module = require('node:module');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(
    PROJECT_ROOT,
    'scripts/ops/pageprops_v2_accepted_mapping_baseline_contradiction_review_plan.js'
);

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();

function syntheticManifest() {
    return {
        batch_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        candidate_targets: [
            {
                match_id: '53_20252026_4830466',
                external_id: '4830466',
                source: 'fotmob',
                route: 'html_hydration',
                raw_data_version: 'fotmob_pageprops_v2',
            },
        ],
        raw_write_execution_ready: false,
        recommended_next_step: 'Phase 5.21L2V3AQ: accepted mapping and baseline contradiction review planning',
        next_required_step: 'accepted_mapping_and_baseline_contradiction_review_planning',
    };
}

function syntheticApArtifact() {
    return {
        blocker_target_count: 1,
        blocker_target_match_id: '53_20252026_4830466',
        requested_external_id: '4830466',
        observed_detail_external_id: '4830759',
        identity_mismatch_confirmed: true,
        reverse_fixture_confirmed: true,
        date_route_mismatch_confirmed: true,
        hash_mismatch_classification: 'secondary_to_identity_mismatch_reverse_fixture',
        runner_input_contract_issue: true,
        source_url_route_issue: true,
        accepted_mapping_contradiction: true,
        baseline_acceptance_contradiction: true,
        payload_recapture_retry_ready: false,
        raw_write_execution_ready: false,
    };
}

function syntheticAeArtifact(reviewStatus = 'accepted') {
    return {
        review_entries: [
            {
                match_id: '53_20252026_4830466',
                source_page_url: '/matches/marseille-vs-rennes/2t9n7h#4830466',
                source_page_url_base: '/matches/marseille-vs-rennes/2t9n7h',
                source_url_fragment_external_id: '4830466',
                review_status: reviewStatus,
            },
        ],
    };
}

function syntheticAgArtifact(status = 'accepted_enriched_baseline_metadata') {
    return {
        baseline_entries: [
            {
                match_id: '53_20252026_4830466',
                source_page_url: '/matches/marseille-vs-rennes/2t9n7h#4830466',
                source_page_url_base: '/matches/marseille-vs-rennes/2t9n7h',
                source_url_fragment_external_id: '4830466',
                baseline_acceptance_status: status,
            },
        ],
    };
}

function syntheticMArtifact(reverse = true) {
    return {
        known_mappings: reverse
            ? [
                  {
                      schedule_external_id: '4830466',
                      detail_external_id: '4830759',
                      classification: 'reverse_fixture_detected',
                      accepted_mapping: false,
                      raw_write_blocked: true,
                  },
              ]
            : [],
    };
}

function syntheticNArtifact(status = 'reverse_fixture_detected') {
    return {
        target_summaries: [
            {
                match_id: '53_20252026_4830466',
                schedule_external_id: '4830466',
                observed_detail_external_id: status === 'reverse_fixture_detected' ? '4830759' : null,
                date_rule_status: status,
                safe_error_summary:
                    status === 'reverse_fixture_detected'
                        ? 'source-controlled reverse fixture evidence already blocks safe acceptance'
                        : 'reverse fixture evidence unavailable from source-controlled artifacts',
            },
        ],
    };
}

function syntheticOverrides() {
    return {
        manifest: syntheticManifest(),
        apArtifact: syntheticApArtifact(),
        aoArtifact: {},
        l2v3ae: syntheticAeArtifact(),
        l2v3ag: syntheticAgArtifact(),
        l2v3aa: {},
        l2v3ac: {},
        l2v3m: syntheticMArtifact(),
        l2v3n: syntheticNArtifact(),
        runnerContractSource: `
            function resolveFetchResultForTarget(target) {
                const requestUrl = buildFotMobMatchUrl(target.external_id);
                return fetchHtml(requestUrl);
            }
        `,
    };
}

test('L2V3AQ is planning-only and does not execute fetch, retry, DB write, or suspension', () => {
    const result = mod.runAcceptedMappingBaselineContradictionReviewPlan({ writeFiles: false }, syntheticOverrides());
    const artifact = result.artifact;
    const manifest = result.updated_manifest;

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AQ');
    assert.equal(artifact.planning_status, 'completed_accepted_mapping_baseline_contradiction_review_planning');
    assert.equal(artifact.live_fetch_performed, false);
    assert.equal(artifact.detail_fetch_performed, false);
    assert.equal(artifact.network_request_performed, false);
    assert.equal(artifact.recapture_retry_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.raw_write_execution_performed, false);
    assert.equal(artifact.mapping_suspension_executed, false);
    assert.equal(artifact.baseline_suspension_executed, false);
    assert.equal(artifact.mapping_rollback_executed, false);
    assert.equal(artifact.baseline_rollback_executed, false);
    assert.equal(artifact.accepted_artifact_mutation_performed, false);
    assert.equal(artifact.baseline_artifact_mutation_performed, false);
    assert.equal(artifact.raw_write_execution_ready, false);
    assert.equal(manifest.phase_5_21_l2v3aq_planning_status, artifact.planning_status);
    assert.equal(manifest.raw_write_execution_ready, false);
    assert.ok(
        [
            artifact.recommended_next_step,
            'Phase 5.21L2V3AS: accepted mapping and baseline suspension planning',
            'Phase 5.21L2V3AT: accepted mapping and baseline suspension execution',
        ].includes(manifest.recommended_next_step)
    );
    assert.ok(
        [
            artifact.next_required_step,
            'accepted_mapping_and_baseline_suspension_planning',
            'accepted_mapping_and_baseline_suspension_execution',
        ].includes(manifest.next_required_step)
    );
});

test('L2V3AQ surfaces accepted mapping and baseline contradictions from reverse fixture evidence', () => {
    const artifact = mod.runAcceptedMappingBaselineContradictionReviewPlan(
        { writeFiles: false },
        syntheticOverrides()
    ).artifact;

    assert.equal(artifact.known_reverse_fixture_target_count, 1);
    assert.equal(artifact.accepted_mapping_count, 1);
    assert.equal(artifact.baseline_accepted_count, 1);
    assert.equal(artifact.accepted_mapping_contradiction_count, 1);
    assert.equal(artifact.baseline_acceptance_contradiction_count, 1);
    assert.equal(artifact.contradiction_review_candidate_count, 1);
    assert.equal(artifact.contradiction_review_ready_count, 1);
    assert.equal(artifact.contradiction_review_blocked_count, 0);
    assert.equal(artifact.mapping_suspension_planning_required, true);
    assert.equal(artifact.baseline_suspension_planning_required, true);
    assert.equal(artifact.re_acceptance_planning_required, true);
    assert.equal(artifact.runner_contract_fix_planning_required, true);
    assert.equal(artifact.hash_mismatch_classification, 'secondary_to_identity_mismatch_reverse_fixture');
    assert.equal(artifact.hash_mismatch_baseline_update_allowed, false);
    assert.equal(artifact.reverse_fixture_evidence_blocks_raw_write_readiness, true);
    assert.equal(
        artifact.recommended_next_step,
        'Phase 5.21L2V3AR: accepted mapping and baseline contradiction review execution'
    );
    assert.deepEqual(artifact.contradiction_review_status_catalog, mod.REVIEW_STATUS_CATALOG);
    assert.equal(artifact.review_targets[0].mapping_follow_up_status, 'suspend_mapping_required');
    assert.equal(artifact.review_targets[0].baseline_follow_up_status, 'suspend_baseline_required');
});

test('L2V3AQ can fall back to runner contract fix planning when contradictions are not yet review-ready', () => {
    const overrides = syntheticOverrides();
    overrides.l2v3m = syntheticMArtifact(false);
    overrides.l2v3n = syntheticNArtifact('unknown');

    const artifact = mod.runAcceptedMappingBaselineContradictionReviewPlan({ writeFiles: false }, overrides).artifact;

    assert.equal(artifact.accepted_mapping_contradiction_count, 0);
    assert.equal(artifact.baseline_acceptance_contradiction_count, 0);
    assert.equal(artifact.contradiction_review_ready_count, 0);
    assert.equal(artifact.contradiction_review_blocked_count, 1);
    assert.equal(artifact.runner_contract_fix_planning_required, true);
    assert.equal(
        artifact.recommended_next_step,
        'Phase 5.21L2V3AR: recapture runner identity input contract fix planning'
    );
});

test('L2V3AQ can fall back to expanded contradiction review planning when no contradiction or runner fix is confirmed', () => {
    const overrides = syntheticOverrides();
    overrides.apArtifact = {
        ...syntheticApArtifact(),
        runner_input_contract_issue: false,
        accepted_mapping_contradiction: false,
        baseline_acceptance_contradiction: false,
    };
    overrides.l2v3ae = syntheticAeArtifact('blocked');
    overrides.l2v3ag = syntheticAgArtifact('blocked');
    overrides.l2v3m = syntheticMArtifact(false);
    overrides.l2v3n = syntheticNArtifact('unknown');
    overrides.runnerContractSource = 'function resolveFetchResultForTarget(target) { return target.source_page_url; }';

    const artifact = mod.runAcceptedMappingBaselineContradictionReviewPlan({ writeFiles: false }, overrides).artifact;

    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.baseline_accepted_count, 0);
    assert.equal(artifact.accepted_mapping_contradiction_count, 0);
    assert.equal(artifact.baseline_acceptance_contradiction_count, 0);
    assert.equal(artifact.runner_contract_fix_planning_required, false);
    assert.equal(
        artifact.recommended_next_step,
        'Phase 5.21L2V3AR: expanded accepted mapping/baseline contradiction review planning'
    );
});

test('L2V3AQ report, artifact, and manifest avoid full raw payload markers', () => {
    const result = mod.runAcceptedMappingBaselineContradictionReviewPlan({ writeFiles: false }, syntheticOverrides());
    const texts = [JSON.stringify(result.artifact), result.report, JSON.stringify(result.updated_manifest)];

    for (const text of texts) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
        assert.equal(text.includes('"source_body":'), false);
    }
});

test('L2V3AQ can write artifact, report, and manifest through injected writers', () => {
    const writes = [];
    const result = mod.runAcceptedMappingBaselineContradictionReviewPlan(
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

test('L2V3AQ loadContext can read repository artifacts through default file helpers', () => {
    const context = mod.loadContext();

    assert.equal(context.acceptedMappingCount, 50);
    assert.equal(context.baselineAcceptedCount, 50);
    assert.equal(context.knownReverseFixtureTargetCount, 8);
    assert.equal(context.acceptedMappingContradictionCount, 8);
    assert.equal(context.baselineAcceptanceContradictionCount, 8);
    assert.equal(context.reviewCandidateCount, 50);
    assert.equal(context.reviewReadyCount, 8);
    assert.equal(context.reviewBlockedCount, 42);
});

test('L2V3AQ internal file writers can be exercised without persisting to disk', () => {
    const writes = [];
    const originalWriteFileSync = fs.writeFileSync;

    fs.writeFileSync = function patchedWriteFileSync(filePath, value, encoding) {
        writes.push([String(filePath), String(value), encoding]);
    };

    try {
        const result = mod.runAcceptedMappingBaselineContradictionReviewPlan();
        assert.equal(result.ok, true);
        assert.equal(writes.length, 3);
        assert.equal(writes[0][0].endsWith(mod.ARTIFACT_OUTPUT_PATH), true);
        assert.equal(writes[1][0].endsWith(mod.REPORT_OUTPUT_PATH), true);
        assert.equal(writes[2][0].endsWith(mod.PROPOSAL_MANIFEST_PATH), true);
    } finally {
        fs.writeFileSync = originalWriteFileSync;
    }
});

test('L2V3AQ runCli prints safe planning summary', async () => {
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
    assert.equal(parsed.phase, 'Phase 5.21L2V3AQ');
    assert.equal(parsed.accepted_mapping_contradiction_count, 8);
    assert.equal(parsed.baseline_acceptance_contradiction_count, 8);
    assert.equal(parsed.contradiction_review_candidate_count, 50);
    assert.equal(parsed.contradiction_review_ready_count, 8);
    assert.equal(parsed.contradiction_review_blocked_count, 42);
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

test('repository L2V3AQ artifacts preserve planning-only contradiction review semantics', () => {
    const artifact = JSON.parse(
        fs.readFileSync(
            path.join(
                PROJECT_ROOT,
                'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.accepted_mapping_baseline_contradiction_review_plan.phase521l2v3aq.json'
            ),
            'utf8'
        )
    );
    const manifest = JSON.parse(
        fs.readFileSync(
            path.join(PROJECT_ROOT, 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json'),
            'utf8'
        )
    );
    const report = fs.readFileSync(
        path.join(PROJECT_ROOT, 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AQ.md'),
        'utf8'
    );

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AQ');
    assert.equal(artifact.live_fetch_performed, false);
    assert.equal(artifact.detail_fetch_performed, false);
    assert.equal(artifact.network_request_performed, false);
    assert.equal(artifact.recapture_retry_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.mapping_suspension_executed, false);
    assert.equal(artifact.baseline_suspension_executed, false);
    assert.equal(artifact.accepted_mapping_contradiction_count, 8);
    assert.equal(artifact.baseline_acceptance_contradiction_count, 8);
    assert.equal(artifact.contradiction_review_candidate_count, 50);
    assert.equal(artifact.contradiction_review_ready_count, 8);
    assert.equal(artifact.contradiction_review_blocked_count, 42);
    assert.equal(artifact.raw_write_execution_ready, false);
    assert.equal(
        artifact.recommended_next_step,
        'Phase 5.21L2V3AR: accepted mapping and baseline contradiction review execution'
    );

    assert.equal(
        manifest.phase_5_21_l2v3aq_planning_status,
        'completed_accepted_mapping_baseline_contradiction_review_planning'
    );
    assert.equal(manifest.raw_write_execution_ready, false);
    assert.equal(manifest.accepted_mapping_contradiction_count, 8);
    assert.equal(manifest.baseline_acceptance_contradiction_count, 8);
    assert.equal(manifest.contradiction_review_candidate_count, 50);
    assert.equal(manifest.contradiction_review_ready_count, 8);
    assert.equal(manifest.contradiction_review_blocked_count, 42);
    assert.ok(
        [
            artifact.recommended_next_step,
            'Phase 5.21L2V3AS: accepted mapping and baseline suspension planning',
            'Phase 5.21L2V3AT: accepted mapping and baseline suspension execution',
        ].includes(manifest.recommended_next_step)
    );
    assert.ok(
        [
            artifact.next_required_step,
            'accepted_mapping_and_baseline_suspension_planning',
            'accepted_mapping_and_baseline_suspension_execution',
        ].includes(manifest.next_required_step)
    );
    assert.match(report, /accepted_mapping_contradiction_count=8/);
    assert.match(report, /baseline_acceptance_contradiction_count=8/);
    assert.match(
        report,
        /recommended_next_step=Phase 5.21L2V3AR: accepted mapping and baseline contradiction review execution/
    );
});
