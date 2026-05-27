'use strict';
/* eslint-disable max-lines -- L2V3BA execution tests keep no-write review assertions explicit. */

const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const Module = require('node:module');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_suspended_target_review_execute.js');

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();

function readJson(repoPath) {
    return JSON.parse(fs.readFileSync(path.join(PROJECT_ROOT, repoPath), 'utf8'));
}

test('L2V3BA executes source-controlled suspended target review without fetch, DB write, raw write, or re-acceptance', () => {
    const result = mod.runSuspendedTargetReviewExecution(
        { writeFiles: false },
        { generatedAt: '2026-05-27T05:15:04.000Z' }
    );
    const artifact = result.artifact;
    const manifest = result.updated_manifest;

    assert.equal(result.ok, true);
    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3BA');
    assert.equal(artifact.suspended_target_review_execution_status, mod.EXECUTION_STATUS);
    assert.equal(artifact.source_controlled_local_review_only, true);
    assert.equal(artifact.review_execution_performed, true);
    assert.equal(artifact.suspended_target_review_candidate_count, 8);
    assert.equal(artifact.pool_control_case_count, 1);
    assert.equal(artifact.executed_review_case_count, 9);
    assert.equal(artifact.completed_review_case_count, 9);
    assert.equal(artifact.failed_review_case_count, 0);
    assert.equal(artifact.raw_write_execution_ready, false);
    assert.equal(artifact.live_fetch_performed, false);
    assert.equal(artifact.detail_fetch_performed, false);
    assert.equal(artifact.network_request_performed, false);
    assert.equal(artifact.recapture_retry_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.matches_external_id_modified, false);
    assert.equal(artifact.raw_write_execution_performed, false);
    assert.equal(artifact.re_acceptance_execution_performed, false);
    assert.equal(artifact.suspension_reversal_performed, false);
    assert.equal(artifact.rollback_execution_performed, false);
    assert.equal(manifest.phase_5_21_l2v3ba_execution_status, mod.EXECUTION_STATUS);
    assert.equal(manifest.raw_write_execution_ready, false);
});

test('L2V3BA review cases preserve the 8 suspended mappings and keep decisions conservative', () => {
    const artifact = mod.runSuspendedTargetReviewExecution(
        { writeFiles: false },
        { generatedAt: '2026-05-27T05:15:04.000Z' }
    ).artifact;
    const caseMap = new Map(artifact.review_cases.map(item => [item.case_id, item]));
    const expectedPairs = new Map([
        ['4830461', '4830758'],
        ['4830463', '4830622'],
        ['4830465', '4830619'],
        ['4830466', '4830759'],
        ['4830481', '4830763'],
        ['4830496', '4830757'],
        ['4830508', '4830620'],
        ['4830511', '4830760'],
    ]);

    assert.equal(artifact.remain_suspended_count, 8);
    assert.equal(artifact.eligible_for_re_acceptance_review_count, 0);
    assert.equal(artifact.requires_runner_contract_followup_count, 0);
    assert.equal(artifact.requires_expanded_evidence_count, 1);
    assert.equal(artifact.reject_mapping_count, 0);
    assert.equal(artifact.supersede_mapping_count, 0);

    for (const [requestedExternalId, observedExternalId] of expectedPairs) {
        const reviewCase = caseMap.get(`suspended_target_review_${requestedExternalId}`);
        assert.equal(reviewCase.requested_external_id, requestedExternalId);
        assert.equal(reviewCase.observed_external_id, observedExternalId);
        assert.equal(reviewCase.executed, true);
        assert.equal(reviewCase.review_decision, 'remain_suspended');
        assert.equal(reviewCase.current_effective_status, 'suspended');
        assert.equal(reviewCase.contradiction_review_status, 'contradiction_confirmed');
        assert.equal(reviewCase.date_rule_status, 'reverse_fixture_detected');
        assert.equal(reviewCase.identity_contract_regression_passed, true);
        assert.equal(reviewCase.page_url_base_alone_insufficient, true);
        assert.equal(reviewCase.re_acceptance_execution_performed, false);
        assert.equal(reviewCase.suspension_reversal_performed, false);
        assert.equal(reviewCase.raw_write_execution_ready, false);
        assert.equal(reviewCase.no_live_fetch, true);
        assert.equal(reviewCase.no_db_write, true);
        assert.equal(reviewCase.no_raw_write, true);
    }
});

test('L2V3BA pool control keeps all 42 blocked_pending_review targets blocked', () => {
    const artifact = mod.runSuspendedTargetReviewExecution(
        { writeFiles: false },
        { generatedAt: '2026-05-27T05:15:04.000Z' }
    ).artifact;
    const poolControl = artifact.review_cases.find(item => item.case_id === 'blocked_pending_review_pool_control');

    assert.equal(poolControl.executed, true);
    assert.equal(poolControl.review_decision, 'requires_expanded_evidence');
    assert.equal(poolControl.blocked_pending_review_target_count, 42);
    assert.equal(poolControl.may_be_treated_as_clean, false);
    assert.equal(poolControl.may_enter_raw_write_eligibility, false);
    assert.equal(poolControl.re_acceptance_execution_performed, false);
    assert.equal(poolControl.suspension_reversal_performed, false);
    assert.equal(poolControl.raw_write_execution_ready, false);
    assert.equal(artifact.blocked_pending_review_target_count, 42);
    assert.equal(
        artifact.blocked_pending_review_target_status,
        'blocked_pending_review_not_clean_not_raw_write_eligible'
    );
    assert.equal(artifact.recommended_next_step, 'Phase 5.21L2V3BB: expanded blocked target review planning');
});

test('L2V3BA allows only AZ-planned decisions and never emits prohibited execution decisions', () => {
    const artifact = mod.runSuspendedTargetReviewExecution(
        { writeFiles: false },
        { generatedAt: '2026-05-27T05:15:04.000Z' }
    ).artifact;
    const decisions = new Set(artifact.review_cases.map(item => item.review_decision));

    for (const decision of decisions) {
        assert.equal(mod.ALLOWED_DECISIONS.includes(decision), true);
        assert.equal(mod.PROHIBITED_DECISIONS.includes(decision), false);
    }
    assert.equal(decisions.has('accepted'), false);
    assert.equal(decisions.has('reaccepted'), false);
    assert.equal(decisions.has('baseline_accepted'), false);
    assert.equal(decisions.has('raw_write_ready'), false);
    assert.equal(decisions.has('suspension_reversed'), false);
    assert.equal(decisions.has('rollback_performed'), false);
    assert.equal(artifact.prohibited_review_decisions_absent, true);
});

test('L2V3BA checked-in artifact and proposal delta stay aligned with execution output', () => {
    mod.runSuspendedTargetReviewExecution({}, { generatedAt: '2026-05-27T05:15:04.000Z' });

    const artifact = readJson(mod.ARTIFACT_OUTPUT_PATH);
    const proposal = readJson(mod.PROPOSAL_MANIFEST_PATH);

    assert.equal(artifact.suspended_target_review_execution_status, mod.EXECUTION_STATUS);
    assert.equal(artifact.executed_review_case_count, 9);
    assert.equal(artifact.completed_review_case_count, 9);
    assert.equal(artifact.failed_review_case_count, 0);
    assert.equal(artifact.remain_suspended_count, 8);
    assert.equal(artifact.requires_expanded_evidence_count, 1);
    assert.equal(artifact.raw_write_execution_ready, false);
    assert.equal(proposal.phase_5_21_l2v3ba_execution_status, mod.EXECUTION_STATUS);
    assert.equal(proposal.suspended_target_review_execution_status, mod.EXECUTION_STATUS);
    assert.equal(proposal.executed_review_case_count, 9);
    assert.equal(proposal.completed_review_case_count, 9);
    assert.equal(proposal.failed_review_case_count, 0);
    assert.equal(proposal.remain_suspended_count, 8);
    assert.equal(proposal.requires_expanded_evidence_count, 1);
    assert.equal(
        proposal.recommended_next_step_after_l2v3ba,
        'Phase 5.21L2V3BB: expanded blocked target review planning'
    );
});

test('L2V3BA report, artifact, and manifest avoid full raw payload markers', () => {
    const result = mod.runSuspendedTargetReviewExecution(
        { writeFiles: false },
        { generatedAt: '2026-05-27T05:15:04.000Z' }
    );
    const texts = [JSON.stringify(result.artifact), result.report, JSON.stringify(result.updated_manifest)];

    for (const text of texts) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
        assert.equal(text.includes('"body":'), false);
        assert.equal(text.includes('"source_body":'), false);
    }
});

test('L2V3BA can write artifact, report, and proposal through injected writers', () => {
    const writes = [];
    const result = mod.runSuspendedTargetReviewExecution(
        {},
        {
            generatedAt: '2026-05-27T05:15:04.000Z',
            writeJsonFile: (targetPath, value) => writes.push(['json', targetPath, value]),
            writeTextFile: (targetPath, value) => writes.push(['text', targetPath, value]),
            writeProposalManifestFile: (targetPath, value) => writes.push(['manifest', targetPath, value]),
        }
    );

    assert.equal(result.ok, true);
    assert.deepEqual(
        writes.map(([kind, targetPath]) => [kind, targetPath]),
        [
            ['json', mod.ARTIFACT_OUTPUT_PATH],
            ['text', mod.REPORT_OUTPUT_PATH],
            ['manifest', mod.PROPOSAL_MANIFEST_PATH],
        ]
    );
});

test('L2V3BA proposal writer can insert a minimal delta and fails closed without the AZ anchor', () => {
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'l2v3ba-proposal-'));
    const tempProposalPath = path.join(tempDir, 'proposal.json');
    const result = mod.runSuspendedTargetReviewExecution(
        { writeFiles: false },
        { generatedAt: '2026-05-27T05:15:04.000Z' }
    );

    fs.writeFileSync(tempProposalPath, `{\n${mod.PROPOSAL_INSERTION_ANCHOR}\n}\n`, 'utf8');
    mod.writeProposalManifestFile(tempProposalPath, result.artifact);

    const written = fs.readFileSync(tempProposalPath, 'utf8');
    assert.match(
        written,
        /"phase_5_21_l2v3ba_execution_status": "completed_controlled_no_write_suspended_target_review_execution"/
    );
    assert.match(
        written,
        /"recommended_next_step_after_l2v3ba": "Phase 5.21L2V3BB: expanded blocked target review planning"/
    );

    fs.writeFileSync(tempProposalPath, '{\n  "no_anchor": true\n}\n', 'utf8');
    assert.throws(
        () => mod.writeProposalManifestFile(tempProposalPath, result.artifact),
        /Failed to apply minimal L2V3BA proposal manifest delta/
    );
});

test('L2V3BA buildArtifact rejects invalid prerequisite context', () => {
    assert.throws(
        () =>
            mod.buildArtifact({
                manifest: {},
                azPlan: {},
                atSuspensionResult: {},
                arContradictionResult: {},
                ayRegressionResult: {},
                generatedAt: '2026-05-27T05:15:04.000Z',
            }),
        /L2V3AZ suspended target review plan is required/
    );
});

test('L2V3BA runCli prints a safe no-write summary', () => {
    let output = '';
    const originalWrite = process.stdout.write;
    process.stdout.write = text => {
        output += text;
        return true;
    };

    try {
        mod.runCli();
    } finally {
        process.stdout.write = originalWrite;
    }

    const parsed = JSON.parse(output);
    assert.equal(parsed.ok, true);
    assert.equal(parsed.phase, 'Phase 5.21L2V3BA');
    assert.equal(parsed.executed_review_case_count, 9);
    assert.equal(parsed.completed_review_case_count, 9);
    assert.equal(parsed.failed_review_case_count, 0);
    assert.equal(parsed.raw_write_execution_ready, false);
    assert.equal(parsed.live_fetch_performed, false);
    assert.equal(parsed.network_request_performed, false);
    assert.equal(parsed.db_write_performed, false);
});

test('L2V3BA main-module execution prints the same safe summary when spawned directly', () => {
    const result = spawnSync('node', [MODULE_PATH], {
        cwd: PROJECT_ROOT,
        encoding: 'utf8',
    });

    assert.equal(result.status, 0);
    const parsed = JSON.parse(result.stdout);
    assert.equal(parsed.ok, true);
    assert.equal(parsed.phase, 'Phase 5.21L2V3BA');
    assert.equal(parsed.failed_review_case_count, 0);
});

test('L2V3BA script keeps imports local and does not add network or DB modules', t => {
    const originalLoad = Module._load;
    Module._load = function patchedLoad(request, parent, isMain) {
        if (/^pg$|axios|playwright|puppeteer|mysql|sequelize/i.test(request)) {
            throw new Error(`blocked import: ${request}`);
        }
        return originalLoad.call(this, request, parent, isMain);
    };

    t.after(() => {
        Module._load = originalLoad;
    });

    const fresh = loadFreshModule();
    const source = fs.readFileSync(MODULE_PATH, 'utf8');

    assert.equal(typeof fresh.runSuspendedTargetReviewExecution, 'function');
    assert.doesNotMatch(source, /ProductionHarvester|raw_match_data_local_ingest|backfill_historical_raw_match_data/);
    for (const forbidden of ['fetch(', 'axios', 'puppeteer', 'playwright', 'new Client(']) {
        assert.equal(source.includes(forbidden), false);
    }
});
