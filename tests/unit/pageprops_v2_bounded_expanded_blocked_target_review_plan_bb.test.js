'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PLAN_PATH = path.join(
    PROJECT_ROOT,
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.bounded_expanded_blocked_target_review_plan.phase521l2v3bb.json'
);
const PROPOSAL_PATH = path.join(
    PROJECT_ROOT,
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json'
);
const REPORT_PATH = path.join(PROJECT_ROOT, 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3BB.md');

function readJson(filePath) {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function getBlockedTargets(proposal) {
    const suspendedIds = new Set(proposal.current_effective_suspended_mapping_match_ids);
    return proposal.candidate_targets.filter(target => !suspendedIds.has(target.match_id));
}

test('L2V3BB records bounded planning only and preserves no-write safety boundaries', () => {
    const plan = readJson(PLAN_PATH);

    assert.equal(plan.proposal_phase, 'Phase 5.21L2V3BB');
    assert.equal(
        plan.bounded_expanded_blocked_target_review_planning_status,
        'completed_bounded_expanded_blocked_target_review_planning'
    );
    assert.equal(plan.pr_type, 'governance-only/planning');
    assert.equal(plan.planning_only, true);
    assert.equal(plan.runtime_code_change, false);
    assert.equal(plan.review_execution_performed, false);
    assert.equal(plan.live_fetch_performed, false);
    assert.equal(plan.detail_fetch_performed, false);
    assert.equal(plan.network_request_performed, false);
    assert.equal(plan.recapture_retry_performed, false);
    assert.equal(plan.db_write_performed, false);
    assert.equal(plan.raw_match_data_insert_performed, false);
    assert.equal(plan.matches_write_performed, false);
    assert.equal(plan.matches_external_id_modified, false);
    assert.equal(plan.raw_write_execution_performed, false);
    assert.equal(plan.raw_write_runner_write_mode_used, false);
    assert.equal(plan.re_acceptance_execution_performed, false);
    assert.equal(plan.suspension_reversal_performed, false);
    assert.equal(plan.rollback_execution_performed, false);
    assert.equal(plan.raw_write_execution_ready, false);
});

test('L2V3BB binds review scope to exactly the 42 non-suspended blocked targets', () => {
    const plan = readJson(PLAN_PATH);
    const proposal = readJson(PROPOSAL_PATH);
    const blockedTargets = getBlockedTargets(proposal);
    const externalIds = blockedTargets.map(target => target.external_id);

    assert.equal(proposal.candidate_targets.length, 50);
    assert.equal(proposal.current_effective_suspended_mapping_match_ids.length, 8);
    assert.equal(blockedTargets.length, 42);
    assert.equal(plan.bounded_review_scope.candidate_batch_size, 50);
    assert.equal(plan.bounded_review_scope.suspended_target_count, 8);
    assert.equal(plan.bounded_review_scope.blocked_pending_review_target_count, 42);
    assert.equal(plan.bounded_review_scope.max_target_count, 42);
    assert.equal(plan.bounded_review_scope.target_expansion_allowed, false);
    assert.deepEqual(plan.bounded_review_scope.blocked_target_external_ids, externalIds);
    assert.equal(new Set(plan.bounded_review_scope.blocked_target_external_ids).size, 42);
});

test('L2V3BB complies with the convergence gate target-state taxonomy', () => {
    const plan = readJson(PLAN_PATH);
    const allowedStates = new Set(plan.allowed_review_decisions);

    for (const state of [
        'clean_candidate',
        'rejected_mapping',
        'superseded_mapping',
        'eligible_for_re_acceptance_review',
        'needs_new_evidence',
        'remain_blocked',
        'abandon_current_batch_candidate',
    ]) {
        assert.equal(allowedStates.has(state), true);
    }

    assert.equal(plan.convergence_gate_applied, true);
    assert.equal(plan.target_state_delta_expected.total_targets, 42);
    assert.equal(plan.target_state_delta_expected.actual_state_changes_this_planning_pr, 0);
    assert.equal(plan.target_state_delta_expected.still_blocked_pending_review_after_planning, 42);
    assert.equal(plan.target_state_delta_expected.maximum_possible_transitions_from_blocked_pending_review, 42);
    assert.equal(plan.blocker_transition_target.raw_write_authorization_from_review_allowed, false);
});

test('L2V3BB forces architecture decision gate after bounded no-progress execution', () => {
    const plan = readJson(PLAN_PATH);

    assert.equal(plan.no_progress_stop_rule.applies_to_next_execution_phase, 'Phase 5.21L2V3BC');
    assert.equal(plan.no_progress_stop_rule.trigger_architecture_decision_gate, true);
    assert.equal(plan.no_progress_stop_rule.continue_expanded_review_planning_allowed, false);
    assert.equal(plan.no_progress_stop_rule.needs_new_evidence_alone_allows_unbounded_phase_continuation, false);
    assert.deepEqual(plan.architecture_decision_options, [
        'abandon current 50-target batch',
        'rebuild canonical identity pipeline',
        'redo source inventory strategy',
        'compare alternative source',
        'redesign FotMob identity mapping strategy',
    ]);
});

test('L2V3BB proposal delta and report stay aligned with the bounded plan', () => {
    const plan = readJson(PLAN_PATH);
    const proposal = readJson(PROPOSAL_PATH);
    const reportText = fs.readFileSync(REPORT_PATH, 'utf8');

    assert.equal(
        proposal.phase_5_21_l2v3bb_planning_status,
        plan.bounded_expanded_blocked_target_review_planning_status
    );
    assert.equal(proposal.phase_5_21_l2v3bb_artifact_path, path.relative(PROJECT_ROOT, PLAN_PATH));
    assert.equal(proposal.phase_5_21_l2v3bb_report_path, path.relative(PROJECT_ROOT, REPORT_PATH));
    assert.equal(proposal.phase_5_21_l2v3bb_bounded_review_target_count, 42);
    assert.equal(proposal.phase_5_21_l2v3bb_actual_state_changes_this_planning_pr, 0);
    assert.equal(proposal.phase_5_21_l2v3bb_architecture_decision_gate_on_no_progress, true);
    assert.equal(proposal.raw_write_execution_ready, false);
    assert.equal(
        proposal.recommended_next_step_after_l2v3bb,
        'Phase 5.21L2V3BC: bounded expanded blocked target review execution under Ingestion Convergence Gate'
    );
    assert.equal(reportText.includes('bounded_review_scope=exactly 42 blocked_pending_review targets'), true);
});

test('L2V3BB artifacts avoid full raw payload markers', () => {
    const plan = readJson(PLAN_PATH);
    const proposal = readJson(PROPOSAL_PATH);
    const reportText = fs.readFileSync(REPORT_PATH, 'utf8');
    const texts = [JSON.stringify(plan), JSON.stringify(proposal), reportText];

    for (const text of texts) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
        assert.equal(text.includes('"body":'), false);
        assert.equal(text.includes('"source_body":'), false);
    }
});
