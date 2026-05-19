'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const {
    assertRawWriteIdentityGate,
    reconcileRouteIdentity,
} = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MANIFEST_PATH = path.join(
    PROJECT_ROOT,
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json'
);
const REVIEW_PLAN_PATH = path.join(
    PROJECT_ROOT,
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.identity_mapping_acceptance_review_plan.phase521l2v3j.json'
);
const REPORT_PATH = path.join(PROJECT_ROOT, 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3J.md');

function readJson(filePath) {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function readText(filePath) {
    return fs.readFileSync(filePath, 'utf8');
}

test('L2V3J review plan is planning-only and not accepted mapping', () => {
    const plan = readJson(REVIEW_PLAN_PATH);
    const manifest = readJson(MANIFEST_PATH);

    assert.equal(plan.proposal_phase, 'Phase 5.21L2V3J');
    assert.equal(plan.planning_only, true);
    assert.equal(plan.identity_mapping_acceptance_performed, false);
    assert.equal(plan.baseline_acceptance_performed, false);
    assert.equal(plan.raw_write_retry_performed, false);
    assert.equal(plan.raw_write_ready_for_execution, false);
    assert.equal(plan.accepted_mapping_count, 0);
    assert.equal(plan.raw_write_guard_compatibility.review_plan_usable_by_raw_write, false);
    assert.equal(manifest.phase_5_21_l2v3j_planning_status, 'completed_planning_only');
    assert.equal(manifest.phase_5_21_l2v3j_review_plan_is_accepted_mapping, false);
    assert.equal(manifest.phase_5_21_l2v3j_review_plan_usable_by_raw_write, false);
});

test('review statuses distinguish review readiness from acceptance', () => {
    const plan = readJson(REVIEW_PLAN_PATH);
    const statuses = plan.review_status_model;

    assert.ok(statuses.review_not_started);
    assert.ok(statuses.review_ready);
    assert.ok(statuses.review_blocked);
    assert.ok(statuses.accepted);
    assert.equal(plan.raw_write_guard_compatibility.review_ready_is_accepted_mapping, false);
    assert.equal(plan.raw_write_guard_compatibility.review_blocked_is_accepted_mapping, false);
    assert.equal(plan.review_ready_count, 0);
    assert.equal(plan.review_blocked_count, 8);
});

test('L2V3J entries remain blocked when date mismatch is unresolved', () => {
    const plan = readJson(REVIEW_PLAN_PATH);

    assert.equal(plan.review_plan_entries.length, 8);
    for (const entry of plan.review_plan_entries) {
        assert.equal(entry.review_status, 'review_blocked');
        assert.equal(entry.acceptance_status, 'not_accepted_planning_only');
        assert.equal(entry.date_match_status, 'mismatch_unresolved');
        assert.equal(entry.mapping_confidence, 'medium');
        assert.equal(entry.raw_write_eligible_after_acceptance, false);
        assert.equal(entry.safety_blockers.includes('date_mismatch_unresolved'), true);
        assert.equal(entry.reviewer_required, true);
        assert.equal(entry.accepted_by, null);
        assert.equal(entry.accepted_at, null);
    }
});

test('review plan blocking rules cover mismatch and conflict failure modes', () => {
    const plan = readJson(REVIEW_PLAN_PATH);
    const blockers = plan.blocking_rules;

    assert.equal(blockers.includes('date_mismatch_unresolved'), true);
    assert.equal(blockers.includes('team_mismatch'), true);
    assert.equal(blockers.includes('page_url_base_mismatch'), true);
    assert.equal(blockers.includes('multiple_detail_ids_for_same_schedule_id'), true);
    assert.equal(blockers.includes('multiple_schedule_ids_for_same_detail_id'), true);
    assert.equal(blockers.includes('unstable_detail_identity'), true);
    assert.equal(blockers.includes('missing_observed_detail_id'), true);
    assert.equal(blockers.includes('fetch_or_parse_failure'), true);
    assert.equal(blockers.includes('block_or_captcha'), true);
    assert.equal(blockers.includes('proposal_only_mapping_available'), true);
    assert.equal(blockers.includes('human_review_missing'), true);
});

test('review plan does not clear raw write guard without accepted mapping', () => {
    const result = reconcileRouteIdentity({
        target: {
            external_id: '4830466',
            home_team: 'Rennes',
            away_team: 'Marseille',
            match_date: '2025-08-15T18:45:00.000Z',
            page_url_base: '/matches/marseille-vs-rennes/2t9n7h',
        },
        pageProps: {
            general: {
                matchId: '4830759',
                homeTeam: { name: 'Marseille' },
                awayTeam: { name: 'Rennes' },
                matchTimeUTC: '2026-05-17T19:00:00.000Z',
                pageUrl: '/matches/marseille-vs-rennes/2t9n7h#4830759',
            },
        },
        proposalOnlyMapping: true,
        acceptedIdentityMappingPresent: false,
    });
    const gate = assertRawWriteIdentityGate(result);

    assert.equal(result.identity_reconciliation_status, 'unresolved_schedule_detail_mapping');
    assert.equal(result.proposal_mapping_used_for_raw_write, false);
    assert.equal(result.safety_blockers.includes('accepted_identity_mapping_missing'), true);
    assert.equal(gate.ok, false);
    assert.equal(gate.transaction_began, false);
    assert.equal(gate.inserted_raw_match_data_count, 0);
});

test('identity mapping review planning remains separate from baseline and DB authorization', () => {
    const plan = readJson(REVIEW_PLAN_PATH);
    const manifest = readJson(MANIFEST_PATH);

    assert.equal(plan.raw_write_guard_compatibility.identity_mapping_acceptance_does_not_accept_baseline, true);
    assert.equal(plan.raw_write_guard_compatibility.identity_mapping_acceptance_does_not_authorize_db_write, true);
    assert.equal(plan.raw_write_guard_compatibility.raw_write_still_requires_separate_baseline_acceptance, true);
    assert.equal(
        plan.raw_write_guard_compatibility.raw_write_still_requires_separate_final_db_write_authorization,
        true
    );
    assert.equal(manifest.requires_separate_identity_mapping_acceptance, true);
    assert.equal(manifest.requires_separate_baseline_acceptance, true);
    assert.equal(manifest.requires_separate_final_db_write_authorization, true);
    assert.equal(manifest.raw_write_ready_for_execution, false);
});

test('L2V3J review plan and report avoid full payload markers', () => {
    const planText = readText(REVIEW_PLAN_PATH);
    const reportText = readText(REPORT_PATH);
    const manifestText = readText(MANIFEST_PATH);

    for (const text of [planText, reportText, manifestText]) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
    }
});
