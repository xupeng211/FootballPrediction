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
const REVIEW_RESULT_PATH = path.join(
    PROJECT_ROOT,
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.identity_mapping_acceptance_review_result.phase521l2v3k.json'
);
const REVIEW_PLAN_PATH = path.join(
    PROJECT_ROOT,
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.identity_mapping_acceptance_review_plan.phase521l2v3j.json'
);
const REPORT_PATH = path.join(PROJECT_ROOT, 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3K.md');

function readJson(filePath) {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function readText(filePath) {
    return fs.readFileSync(filePath, 'utf8');
}

test('L2V3K is no-write review execution phase', () => {
    const result = readJson(REVIEW_RESULT_PATH);
    const manifest = readJson(MANIFEST_PATH);

    assert.equal(result.review_execution_only, true);
    assert.equal(result.no_write, true);
    assert.equal(result.no_acceptance, true);
    assert.equal(result.identity_mapping_acceptance_performed, false);
    assert.equal(result.baseline_acceptance_performed, false);
    assert.equal(result.raw_write_retry_performed, false);
    assert.equal(result.raw_write_ready_for_execution, false);
    assert.equal(result.db_write_performed, false);
    assert.equal(result.raw_insert_performed, false);
    assert.equal(result.matches_write_performed, false);
    assert.equal(result.matches_external_id_modified, false);

    assert.equal(manifest.phase_5_21_l2v3k_execution_status, 'completed_no_accepted_mapping');
    assert.equal(manifest.phase_5_21_l2v3k_identity_mapping_acceptance_performed, false);
    assert.equal(manifest.phase_5_21_l2v3k_db_write_performed, false);
    assert.equal(manifest.raw_write_ready_for_execution, false);
});

test('review result artifact cannot be used by raw write runner as accepted mapping', () => {
    const result = readJson(REVIEW_RESULT_PATH);
    const manifest = readJson(MANIFEST_PATH);

    assert.equal(result.raw_write_guard_compatibility.review_result_usable_by_raw_write, false);
    assert.equal(result.raw_write_guard_compatibility.review_result_artifact_is_not_accepted_mapping, true);
    assert.equal(result.raw_write_guard_compatibility.accepted_identity_mapping_artifact_present, false);
    assert.equal(manifest.phase_5_21_l2v3k_review_result_is_accepted_mapping, false);
    assert.equal(manifest.phase_5_21_l2v3k_review_result_usable_by_raw_write, false);
});

test('review_ready is not accepted mapping', () => {
    const result = readJson(REVIEW_RESULT_PATH);
    const manifest = readJson(MANIFEST_PATH);

    assert.equal(result.raw_write_guard_compatibility.review_ready_is_accepted_mapping, false);
    assert.equal(result.review_execution_rules_applied.review_ready_is_not_accepted, true);
    assert.equal(manifest.phase_5_21_l2v3k_review_ready_is_accepted, false);
    assert.equal(manifest.phase_5_21_l2v3k_review_ready_count, 0);
});

test('review_blocked is not accepted mapping', () => {
    const result = readJson(REVIEW_RESULT_PATH);
    const manifest = readJson(MANIFEST_PATH);

    assert.equal(result.raw_write_guard_compatibility.review_blocked_is_accepted_mapping, false);
    assert.equal(result.review_execution_rules_applied.review_blocked_is_not_accepted, true);
    assert.equal(manifest.phase_5_21_l2v3k_review_blocked_is_accepted, false);
    assert.equal(manifest.phase_5_21_l2v3k_review_blocked_count, 8);
});

test('ready_for_human_acceptance_authorization is not accepted mapping', () => {
    const result = readJson(REVIEW_RESULT_PATH);
    const manifest = readJson(MANIFEST_PATH);

    assert.equal(
        result.raw_write_guard_compatibility.ready_for_human_acceptance_authorization_is_accepted_mapping,
        false
    );
    assert.equal(result.review_execution_rules_applied.ready_for_human_acceptance_authorization_is_not_accepted, true);
    assert.equal(manifest.phase_5_21_l2v3k_ready_for_human_acceptance_authorization_is_accepted, false);
    assert.equal(manifest.phase_5_21_l2v3k_ready_for_human_acceptance_authorization_count, 0);
});

test('accepted_mapping_count remains 0', () => {
    const result = readJson(REVIEW_RESULT_PATH);
    const manifest = readJson(MANIFEST_PATH);

    assert.equal(result.accepted_mapping_count, 0);
    assert.equal(result.review_summary.accepted_mapping_count, 0);
    assert.equal(manifest.phase_5_21_l2v3k_accepted_mapping_count, 0);

    for (const entry of result.review_entries) {
        assert.equal(entry.acceptance_status, 'not_accepted');
        assert.equal(entry.accepted_by, null);
        assert.equal(entry.accepted_at, null);
        assert.equal(entry.raw_write_eligible, false);
    }
});

test('unresolved date mismatch keeps all 8 mappings review_blocked', () => {
    const result = readJson(REVIEW_RESULT_PATH);

    assert.equal(result.review_entries.length, 8);
    for (const entry of result.review_entries) {
        assert.equal(entry.review_result, 'review_blocked');
        assert.equal(entry.date_match_status, 'mismatch_unresolved');
        assert.equal(entry.acceptance_status, 'not_accepted');
        assert.equal(entry.safety_blockers.includes('date_mismatch_unresolved'), true);
        assert.equal(entry.safety_blockers.includes('human_review_required'), true);
        assert.equal(entry.reviewer_required, true);
        assert.equal(entry.ready_for_human_acceptance_authorization, false);
        assert.equal(entry.raw_write_eligible, false);
    }
});

test('medium-confidence mapping remains blocked without separate human acceptance', () => {
    const result = readJson(REVIEW_RESULT_PATH);

    for (const entry of result.review_entries) {
        assert.equal(entry.mapping_confidence, 'medium');
        assert.equal(entry.review_result, 'review_blocked');
        assert.equal(entry.acceptance_status, 'not_accepted');
    }

    assert.equal(
        result.review_execution_rules_applied
            .medium_confidence_mapping_cannot_become_accepted_without_separate_authorization,
        true
    );
});

test('no human review evidence blocks acceptance', () => {
    const result = readJson(REVIEW_RESULT_PATH);

    for (const entry of result.review_entries) {
        assert.equal(entry.reviewer_required, true);
        assert.equal(entry.accepted_by, null);
    }

    assert.equal(
        result.review_execution_rules_applied.no_human_review_evidence_forces_review_blocked_or_ready_for_human,
        true
    );
});

test('identity mapping acceptance still does not equal baseline acceptance', () => {
    const result = readJson(REVIEW_RESULT_PATH);

    assert.equal(result.raw_write_guard_compatibility.identity_mapping_acceptance_does_not_accept_baseline, true);
    assert.equal(result.raw_write_guard_compatibility.identity_mapping_acceptance_does_not_authorize_db_write, true);
    assert.equal(result.raw_write_guard_compatibility.raw_write_still_requires_separate_baseline_acceptance, true);
});

test('identity mapping acceptance still does not equal final DB-write authorization', () => {
    const result = readJson(REVIEW_RESULT_PATH);

    assert.equal(
        result.raw_write_guard_compatibility.raw_write_still_requires_separate_final_db_write_authorization,
        true
    );
    assert.equal(
        result.raw_write_guard_compatibility.raw_write_still_requires_separate_identity_mapping_acceptance,
        true
    );
});

test('raw_write_ready_for_execution remains false', () => {
    const result = readJson(REVIEW_RESULT_PATH);
    const manifest = readJson(MANIFEST_PATH);

    assert.equal(result.raw_write_ready_for_execution, false);
    assert.equal(manifest.raw_write_ready_for_execution, false);
});

test('no full raw_data/pageProps/source body in L2V3K artifacts', () => {
    const resultText = readText(REVIEW_RESULT_PATH);
    const reportText = readText(REPORT_PATH);
    const manifestText = readText(MANIFEST_PATH);

    for (const text of [resultText, reportText, manifestText]) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
    }
});

test('L2V3K review result does not clear raw write guard without accepted mapping', () => {
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
        reviewResultPresent: true,
        reviewResultAccepted: false,
    });
    const gate = assertRawWriteIdentityGate(result);

    assert.equal(result.identity_reconciliation_status, 'unresolved_schedule_detail_mapping');
    assert.equal(result.proposal_mapping_used_for_raw_write, false);
    assert.equal(result.safety_blockers.includes('accepted_identity_mapping_missing'), true);
    assert.equal(gate.ok, false);
    assert.equal(gate.transaction_began, false);
    assert.equal(gate.inserted_raw_match_data_count, 0);
});

test('L2V3K manifest metadata is consistent with L2V3J review plan', () => {
    const manifest = readJson(MANIFEST_PATH);
    const plan = readJson(REVIEW_PLAN_PATH);
    const result = readJson(REVIEW_RESULT_PATH);

    assert.equal(manifest.phase_5_21_l2v3j_review_blocked_count, 8);
    assert.equal(manifest.phase_5_21_l2v3k_review_blocked_count, 8);
    assert.equal(plan.review_blocked_count, 8);
    assert.equal(result.review_blocked_count, 8);

    assert.equal(manifest.phase_5_21_l2v3j_accepted_mapping_count, 0);
    assert.equal(manifest.phase_5_21_l2v3k_accepted_mapping_count, 0);
    assert.equal(plan.accepted_mapping_count, 0);
    assert.equal(result.accepted_mapping_count, 0);

    assert.equal(manifest.requires_separate_identity_mapping_acceptance, true);
    assert.equal(manifest.requires_separate_baseline_acceptance, true);
    assert.equal(manifest.requires_separate_final_db_write_authorization, true);
});

test('all 8 review entries preserve both external IDs', () => {
    const result = readJson(REVIEW_RESULT_PATH);
    const plan = readJson(REVIEW_PLAN_PATH);

    const planIds = new Set(plan.review_plan_entries.map(e => `${e.schedule_external_id}:${e.detail_external_id}`));
    const resultIds = new Set(result.review_entries.map(e => `${e.schedule_external_id}:${e.detail_external_id}`));

    assert.equal(planIds.size, 8);
    assert.equal(resultIds.size, 8);
    for (const id of planIds) {
        assert.equal(resultIds.has(id), true);
    }
});
