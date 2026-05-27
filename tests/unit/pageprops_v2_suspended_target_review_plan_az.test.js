'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MANIFEST_PATH = path.join(
    PROJECT_ROOT,
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.suspended_target_review_plan.phase521l2v3az.json'
);
const REPORT_PATH = path.join(PROJECT_ROOT, 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AZ.md');

function readJson(filePath) {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

test('L2V3AZ records a controlled no-write suspended target review plan without execution side effects', () => {
    const artifact = readJson(MANIFEST_PATH);

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AZ');
    assert.equal(
        artifact.suspended_target_review_planning_status,
        'completed_controlled_no_write_suspended_target_review_planning'
    );
    assert.equal(artifact.planning_only, true);
    assert.equal(artifact.runtime_code_change, false);
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
    assert.equal(artifact.raw_write_execution_ready, false);
});

test('L2V3AZ plans review coverage for 8 suspended targets and keeps the 42 blocked targets blocked', () => {
    const artifact = readJson(MANIFEST_PATH);
    const suspendedIds = new Map(
        artifact.suspended_review_targets.map(item => [item.schedule_external_id, item.observed_detail_external_id])
    );
    const caseIds = artifact.planned_review_cases.map(item => item.id);

    assert.equal(artifact.reviewed_input_artifact_count, 8);
    assert.equal(artifact.suspended_target_review_candidate_count, 8);
    assert.equal(artifact.blocked_pending_review_target_count, 42);
    assert.equal(artifact.planned_review_case_count, 9);
    assert.equal(artifact.planned_review_decision_count, 6);
    assert.equal(artifact.planned_blocking_rule_count, 7);

    assert.equal(suspendedIds.get('4830461'), '4830758');
    assert.equal(suspendedIds.get('4830463'), '4830622');
    assert.equal(suspendedIds.get('4830465'), '4830619');
    assert.equal(suspendedIds.get('4830466'), '4830759');
    assert.equal(suspendedIds.get('4830481'), '4830763');
    assert.equal(suspendedIds.get('4830496'), '4830757');
    assert.equal(suspendedIds.get('4830508'), '4830620');
    assert.equal(suspendedIds.get('4830511'), '4830760');

    assert.equal(caseIds.includes('suspended_target_review_4830466'), true);
    assert.equal(caseIds.includes('blocked_pending_review_pool_control'), true);
    assert.equal(artifact.blocked_pending_review_planning.may_be_treated_as_clean, false);
    assert.equal(artifact.blocked_pending_review_planning.may_enter_raw_write_eligibility, false);
    assert.equal(artifact.blocked_pending_review_planning.raw_write_execution_ready, false);
});

test('L2V3AZ advances only to controlled no-write suspended target review execution in the current manifest', () => {
    const artifact = readJson(MANIFEST_PATH);
    const reportText = fs.readFileSync(REPORT_PATH, 'utf8');
    const texts = [JSON.stringify(artifact), reportText];

    assert.equal(
        artifact.recommended_next_step,
        'Phase 5.21L2V3BA: controlled no-write suspended target review execution'
    );
    assert.equal(
        reportText.includes('Proposal manifest update records current AZ planning status and next-step metadata only.'),
        true
    );
    assert.equal(
        reportText.includes(
            '- recommended_next_step=Phase 5.21L2V3BA: controlled no-write suspended target review execution'
        ),
        true
    );

    for (const text of texts) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
        assert.equal(text.includes('"body":'), false);
        assert.equal(text.includes('"source_body":'), false);
    }
});
