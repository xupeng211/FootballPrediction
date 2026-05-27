'use strict';
/* eslint-disable max-lines -- L2V3AY regression execution tests keep no-write behavior explicit. */

const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const Module = require('node:module');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_identity_contract_regression_execute.js');

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();

function readJson(repoPath) {
    return JSON.parse(fs.readFileSync(path.join(PROJECT_ROOT, repoPath), 'utf8'));
}

test('L2V3AY executes 7 planned local no-write regression cases and keeps all write/fetch flags false', async () => {
    const result = await mod.runIdentityContractRegressionExecution(
        { writeFiles: false },
        { generatedAt: '2026-05-27T00:30:00.000Z' }
    );
    const artifact = result.artifact;
    const manifest = result.updated_manifest;

    assert.equal(result.ok, true);
    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AY');
    assert.equal(artifact.regression_execution_status, mod.EXECUTION_STATUS);
    assert.equal(artifact.regression_execution_performed, true);
    assert.equal(artifact.planned_regression_case_count, 7);
    assert.equal(artifact.executed_regression_case_count, 7);
    assert.equal(artifact.passed_regression_case_count, 7);
    assert.equal(artifact.failed_regression_case_count, 0);
    assert.equal(artifact.planned_blocking_rule_count, 7);
    assert.equal(artifact.blocking_rule_verified_count, 7);
    assert.equal(artifact.schedule_side_route_default_block_verified, true);
    assert.equal(artifact.suspended_mapping_baseline_block_verified, true);
    assert.equal(artifact.missing_re_acceptance_block_verified, true);
    assert.equal(artifact.page_url_base_alone_insufficient_verified, true);
    assert.equal(artifact.requested_observed_mismatch_block_verified, true);
    assert.equal(artifact.hash_mismatch_under_identity_mismatch_baseline_update_block_verified, true);
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
    assert.equal(
        artifact.recommended_next_step,
        'Phase 5.21L2V3AZ: controlled no-write suspended target review planning'
    );
    assert.equal(manifest.phase_5_21_l2v3ay_execution_status, artifact.execution_status);
    assert.equal(manifest.identity_contract_regression_execution_status, artifact.execution_status);
    assert.equal(manifest.raw_write_execution_ready, false);
});

test('L2V3AY case results match the planned identity-contract blocking semantics', async () => {
    const result = await mod.runIdentityContractRegressionExecution(
        { writeFiles: false },
        { generatedAt: '2026-05-27T00:30:00.000Z' }
    );
    const caseMap = new Map(result.artifact.regression_cases.map(item => [item.case_id, item]));
    const blockingRules = new Map(result.artifact.blocking_rules.map(item => [item.rule_id, item]));

    assert.equal(caseMap.get('schedule_external_id_is_correlation_only').result, 'pass');
    assert.equal(
        caseMap.get('schedule_external_id_is_correlation_only').observed_behavior.route_identity_strategy,
        'blocked_until_reaccepted_identity_contract'
    );
    assert.equal(
        caseMap
            .get('schedule_external_id_is_correlation_only')
            .verified_blockers.includes('missing_accepted_detail_external_id'),
        true
    );

    assert.equal(caseMap.get('suspended_mapping_baseline_blocks_before_fetch').result, 'pass');
    assert.equal(caseMap.get('suspended_mapping_baseline_blocks_before_fetch').observed_behavior.fetch_called, false);
    assert.equal(
        caseMap
            .get('suspended_mapping_baseline_blocks_before_fetch')
            .verified_blockers.includes('suspended_mapping_or_baseline'),
        true
    );

    assert.equal(caseMap.get('missing_re_acceptance_blocks_before_fetch').result, 'pass');
    assert.equal(
        caseMap.get('missing_re_acceptance_blocks_before_fetch').verified_blockers.includes('missing_re_acceptance'),
        true
    );

    assert.equal(caseMap.get('page_url_base_slug_fragment_alone_insufficient').result, 'pass');
    assert.equal(
        caseMap.get('page_url_base_slug_fragment_alone_insufficient').observed_behavior
            .page_url_base_alone_insufficient_enforced,
        true
    );

    assert.equal(caseMap.get('requested_4830466_observed_4830759_remains_blocked').result, 'pass');
    assert.equal(
        caseMap.get('requested_4830466_observed_4830759_remains_blocked').observed_behavior.observed_detail_external_id,
        '4830759'
    );
    assert.equal(
        caseMap.get('requested_4830466_observed_4830759_remains_blocked').observed_behavior.stopping_rule_triggered,
        'identity_mismatch'
    );

    assert.equal(caseMap.get('hash_mismatch_under_identity_mismatch_cannot_update_baseline').result, 'pass');
    assert.equal(
        caseMap.get('hash_mismatch_under_identity_mismatch_cannot_update_baseline').observed_behavior
            .hash_validation_status,
        'secondary_to_identity_mismatch'
    );
    assert.equal(
        caseMap.get('hash_mismatch_under_identity_mismatch_cannot_update_baseline').observed_behavior
            .baseline_update_allowed,
        false
    );

    assert.equal(caseMap.get('raw_write_execution_ready_remains_false').result, 'pass');
    assert.equal(caseMap.get('raw_write_execution_ready_remains_false').observed_behavior.all_cases_false, true);

    assert.equal(
        blockingRules.get('schedule_external_id_default_detail_route_blocked').covered_by_case_id,
        'schedule_external_id_is_correlation_only'
    );
    assert.equal(
        blockingRules.get('hash_mismatch_secondary_to_identity_mismatch_blocks_baseline_update').verified,
        true
    );
});

test('L2V3AY checked-in artifact and proposal delta stay aligned with execution output', () => {
    const artifact = readJson(mod.ARTIFACT_OUTPUT_PATH);
    const proposal = readJson(mod.PROPOSAL_MANIFEST_PATH);

    assert.equal(artifact.regression_execution_status, mod.EXECUTION_STATUS);
    assert.equal(artifact.executed_regression_case_count, 7);
    assert.equal(artifact.passed_regression_case_count, 7);
    assert.equal(artifact.failed_regression_case_count, 0);
    assert.equal(artifact.blocking_rule_verified_count, 7);
    assert.equal(artifact.raw_write_execution_ready, false);
    assert.equal(
        artifact.recommended_next_step,
        'Phase 5.21L2V3AZ: controlled no-write suspended target review planning'
    );

    assert.equal(proposal.phase_5_21_l2v3ay_execution_status, mod.EXECUTION_STATUS);
    assert.equal(proposal.identity_contract_regression_execution_status, mod.EXECUTION_STATUS);
    assert.equal(proposal.executed_regression_case_count, 7);
    assert.equal(proposal.passed_regression_case_count, 7);
    assert.equal(proposal.failed_regression_case_count, 0);
    assert.equal(proposal.blocking_rule_verified_count, 7);
    assert.equal(proposal.raw_write_execution_ready, false);
    assert.equal(
        proposal.recommended_next_step_after_l2v3ay,
        'Phase 5.21L2V3AZ: controlled no-write suspended target review planning'
    );
});

test('L2V3AY artifact, report, and proposal avoid full payload markers', async () => {
    const result = await mod.runIdentityContractRegressionExecution(
        { writeFiles: false },
        { generatedAt: '2026-05-27T00:30:00.000Z' }
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

test('L2V3AY can write artifact, report, and proposal through injected writers', async () => {
    const writes = [];
    const result = await mod.runIdentityContractRegressionExecution(
        {},
        {
            generatedAt: '2026-05-27T00:30:00.000Z',
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

test('L2V3AY proposal writer can insert a minimal delta and fails closed without the AX anchor', async () => {
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'l2v3ay-proposal-'));
    const tempProposalPath = path.join(tempDir, 'proposal.json');
    const result = await mod.runIdentityContractRegressionExecution(
        { writeFiles: false },
        { generatedAt: '2026-05-27T00:30:00.000Z' }
    );

    fs.writeFileSync(tempProposalPath, `{\n${mod.PROPOSAL_INSERTION_ANCHOR}\n}\n`, 'utf8');
    mod.writeProposalManifestFile(tempProposalPath, result.artifact);

    const written = fs.readFileSync(tempProposalPath, 'utf8');
    assert.match(
        written,
        /"phase_5_21_l2v3ay_execution_status": "completed_controlled_no_write_identity_contract_regression_execution"/
    );
    assert.match(
        written,
        /"recommended_next_step_after_l2v3ay": "Phase 5.21L2V3AZ: controlled no-write suspended target review planning"/
    );

    fs.writeFileSync(tempProposalPath, '{\n  "no_anchor": true\n}\n', 'utf8');
    assert.throws(
        () => mod.writeProposalManifestFile(tempProposalPath, result.artifact),
        /Failed to apply minimal L2V3AY proposal manifest delta/
    );

    fs.writeFileSync(
        tempProposalPath,
        '{\n' +
            '    "recommended_next_step_after_l2v3ax": "BROKEN_ANCHOR",\n' +
            '    "phase_5_21_l2v3ay_execution_status": "stale"\n' +
            '}\n',
        'utf8'
    );
    mod.writeProposalManifestFile(tempProposalPath, result.artifact);
    assert.equal(
        fs.readFileSync(tempProposalPath, 'utf8'),
        '{\n' +
            '    "recommended_next_step_after_l2v3ax": "BROKEN_ANCHOR",\n' +
            '    "phase_5_21_l2v3ay_execution_status": "stale"\n' +
            '}\n'
    );
});

test('L2V3AY buildArtifact rejects invalid prerequisite context', async () => {
    await assert.rejects(
        () =>
            mod.buildArtifact({
                manifest: {},
                axPlan: {},
                awImplementation: {},
                aoResult: {},
                baseTarget: null,
                generatedAt: '2026-05-27T00:30:00.000Z',
            }),
        /L2V3AX plan artifact is required/
    );
});

test('L2V3AY helper builders cover nested overrides, null fallbacks, and match_id-based target lookup', () => {
    const pageProps = mod.buildFixturePageProps('9999999', {
        general: { status: 'live' },
        header: null,
    });
    const caseTarget = mod.buildCaseTarget({});
    const context = mod.loadContext({
        manifest: {
            candidate_targets: [{ match_id: '53_20252026_4830466', baseline_hash: '0'.repeat(64) }],
        },
        axPlan: readJson(mod.AX_PLAN_PATH),
        awImplementation: readJson(mod.AW_IMPLEMENTATION_PATH),
        aoResult: readJson(mod.AO_RECAPTURE_RESULT_PATH),
        generatedAt: '2026-05-27T00:30:00.000Z',
    });

    assert.equal(pageProps.general.matchId, '9999999');
    assert.equal(pageProps.general.status, 'live');
    assert.equal(pageProps.header, null);
    assert.equal(caseTarget.schedule_external_id, null);
    assert.equal(caseTarget.home_team, null);
    assert.equal(context.baseTarget.match_id, '53_20252026_4830466');
});

test('L2V3AY runCli prints a safe no-write summary', async () => {
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
    assert.equal(parsed.phase, 'Phase 5.21L2V3AY');
    assert.equal(parsed.executed_regression_case_count, 7);
    assert.equal(parsed.passed_regression_case_count, 7);
    assert.equal(parsed.failed_regression_case_count, 0);
    assert.equal(parsed.raw_write_execution_ready, false);
    assert.equal(parsed.live_fetch_performed, false);
    assert.equal(parsed.network_request_performed, false);
    assert.equal(parsed.db_write_performed, false);
});

test('L2V3AY main-module execution prints the same safe summary when spawned directly', () => {
    const result = spawnSync('node', [MODULE_PATH], {
        cwd: PROJECT_ROOT,
        encoding: 'utf8',
    });

    assert.equal(result.status, 0);
    const parsed = JSON.parse(result.stdout);
    assert.equal(parsed.ok, true);
    assert.equal(parsed.phase, 'Phase 5.21L2V3AY');
    assert.equal(parsed.failed_regression_case_count, 0);
});

test('L2V3AY script keeps imports local and does not add network or DB modules', t => {
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

    assert.equal(typeof fresh.runIdentityContractRegressionExecution, 'function');
    assert.doesNotMatch(source, /ProductionHarvester|raw_match_data_local_ingest|backfill_historical_raw_match_data/);
});
