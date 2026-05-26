'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MANIFEST_PATH = path.join(
    PROJECT_ROOT,
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.identity_contract_regression_plan.phase521l2v3ax.json'
);
const PROPOSAL_PATH = path.join(
    PROJECT_ROOT,
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json'
);

function readJson(filePath) {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

test('L2V3AX records a controlled no-write regression plan without execution side effects', () => {
    const artifact = readJson(MANIFEST_PATH);

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AX');
    assert.equal(
        artifact.regression_planning_status,
        'completed_controlled_no_write_identity_contract_regression_planning'
    );
    assert.equal(artifact.planning_only, true);
    assert.equal(artifact.runtime_code_change, false);
    assert.equal(artifact.live_fetch_performed, false);
    assert.equal(artifact.network_request_performed, false);
    assert.equal(artifact.recapture_retry_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.raw_write_execution_performed, false);
    assert.equal(artifact.raw_write_execution_ready, false);
});

test('L2V3AX plans regression coverage for the L2V3AW identity contract behavior', () => {
    const artifact = readJson(MANIFEST_PATH);
    const caseIds = artifact.planned_regression_cases.map(item => item.id);

    assert.equal(artifact.reviewed_input_artifact_count, 7);
    assert.equal(artifact.target_behavior_under_test_count, 7);
    assert.equal(artifact.planned_regression_case_count, 7);
    assert.equal(artifact.planned_blocking_rule_count, 7);
    assert.equal(caseIds.includes('schedule_external_id_is_correlation_only'), true);
    assert.equal(caseIds.includes('requested_4830466_observed_4830759_remains_blocked'), true);
    assert.equal(caseIds.includes('hash_mismatch_under_identity_mismatch_cannot_update_baseline'), true);
    assert.equal(caseIds.includes('raw_write_execution_ready_remains_false'), true);
});

test('L2V3AX advances only to no-write regression execution in the current manifest', () => {
    const artifact = readJson(MANIFEST_PATH);
    const proposal = readJson(PROPOSAL_PATH);

    assert.equal(
        artifact.recommended_next_step,
        'Phase 5.21L2V3AY: controlled no-write identity contract regression execution'
    );
    assert.equal(
        proposal.phase_5_21_l2v3ax_planning_status,
        'completed_controlled_no_write_identity_contract_regression_planning'
    );
    assert.equal(proposal.planned_regression_case_count, 7);
    assert.equal(proposal.raw_write_execution_ready, false);
    assert.equal(
        proposal.recommended_next_step_after_l2v3ax,
        'Phase 5.21L2V3AY: controlled no-write identity contract regression execution'
    );
});
