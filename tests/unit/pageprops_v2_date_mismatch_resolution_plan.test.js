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
const DATE_PLAN_PATH = path.join(
    PROJECT_ROOT,
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.date_mismatch_resolution_plan.phase521l2v3l.json'
);
const REVIEW_RESULT_PATH = path.join(
    PROJECT_ROOT,
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.identity_mapping_acceptance_review_result.phase521l2v3k.json'
);
const REPORT_PATH = path.join(PROJECT_ROOT, 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3L.md');

function readJson(filePath) {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function readText(filePath) {
    return fs.readFileSync(filePath, 'utf8');
}

test('L2V3L is no-write planning phase', () => {
    const plan = readJson(DATE_PLAN_PATH);
    const manifest = readJson(MANIFEST_PATH);

    assert.equal(plan.planning_only, true);
    assert.equal(plan.no_write, true);
    assert.equal(plan.no_acceptance, true);
    assert.equal(plan.identity_mapping_acceptance_performed, false);
    assert.equal(plan.baseline_acceptance_performed, false);
    assert.equal(plan.raw_write_retry_performed, false);
    assert.equal(plan.raw_write_ready_for_execution, false);
    assert.equal(plan.db_write_performed, false);
    assert.equal(plan.raw_insert_performed, false);
    assert.equal(plan.matches_write_performed, false);

    assert.equal(manifest.phase_5_21_l2v3l_planning_status, 'completed_root_cause_identified');
    assert.equal(manifest.phase_5_21_l2v3l_identity_mapping_acceptance_performed, false);
    assert.equal(manifest.phase_5_21_l2v3l_db_write_performed, false);
    assert.equal(manifest.raw_write_ready_for_execution, false);
});

test('root cause identified as fotmob pageurl slug cross-fixture reuse', () => {
    const plan = readJson(DATE_PLAN_PATH);
    const manifest = readJson(MANIFEST_PATH);

    assert.equal(plan.root_cause.primary, 'fotmob_pageurl_slug_cross_fixture_reuse');
    assert.equal(plan.root_cause.confidence, 'high');
    assert.equal(manifest.phase_5_21_l2v3l_date_mismatch_root_cause, 'fotmob_pageurl_slug_cross_fixture_reuse');
    assert.equal(manifest.phase_5_21_l2v3l_date_mismatch_root_cause_confidence, 'high');
});

test('all 8 candidates classified as reverse_fixture_detected', () => {
    const plan = readJson(DATE_PLAN_PATH);
    const manifest = readJson(MANIFEST_PATH);

    assert.equal(plan.application_to_8_candidates.all_8_classification, 'reverse_fixture_detected');
    assert.equal(plan.application_to_8_candidates.all_8_acceptance_eligible, false);
    assert.equal(plan.root_cause.sub_classifications.reverse_fixture_second_leg.count, 8);
    assert.equal(plan.root_cause.sub_classifications.cross_season_slug_reuse.count, 0);
    assert.equal(plan.root_cause.sub_classifications.timezone_only_mismatch.count, 0);

    assert.equal(manifest.phase_5_21_l2v3l_reverse_fixture_detected_count, 8);
    assert.equal(manifest.phase_5_21_l2v3l_cross_season_slug_reuse_count, 0);
    assert.equal(manifest.phase_5_21_l2v3l_timezone_only_mismatch_count, 0);
});

test('pageUrl base match alone cannot override date mismatch', () => {
    const plan = readJson(DATE_PLAN_PATH);

    assert.equal(plan.pageurl_base_as_mapping_anchor_assessment.pageurl_base_sufficient_for_acceptance, false);
    assert.equal(plan.pageurl_base_as_mapping_anchor_assessment.pageurl_base_confidence, 'weak_to_medium');

    const anchorAssessment = plan.pageurl_base_as_mapping_anchor_assessment;
    assert.equal(
        anchorAssessment.requires_additional_evidence.includes(
            'exact date match or explicit date compatibility explanation'
        ),
        true
    );
});

test('reverse_fixture_detected blocks identity mapping acceptance', () => {
    const plan = readJson(DATE_PLAN_PATH);

    const rules = plan.proposed_date_compatibility_rules;
    assert.equal(rules.reverse_fixture_detected.mapping_confidence, 'confirmed_mismatch_not_acceptance');
    assert.equal(rules.reverse_fixture_detected.acceptance_eligible, 'no');

    assert.equal(plan.raw_write_guard_compatibility.reverse_fixture_detected_blocks_acceptance, true);
    assert.equal(plan.raw_write_guard_compatibility.reverse_fixture_detected_blocks_raw_write, true);
    assert.equal(plan.raw_write_guard_compatibility.pageurl_base_alone_insufficient_for_acceptance, true);
});

test('cross_season_slug_reuse blocks acceptance', () => {
    const plan = readJson(DATE_PLAN_PATH);

    const rules = plan.proposed_date_compatibility_rules;
    assert.equal(rules.cross_season_slug_reuse.mapping_confidence, 'confirmed_mismatch_not_acceptance');
    assert.equal(rules.cross_season_slug_reuse.acceptance_eligible, 'no');
});

test('unresolved large date gap blocks acceptance', () => {
    const plan = readJson(DATE_PLAN_PATH);

    const rules = plan.proposed_date_compatibility_rules;
    assert.equal(rules.unresolved_large_gap.mapping_confidence, 'invalid_mapping');
    assert.equal(rules.unresolved_large_gap.acceptance_eligible, 'no');
    assert.equal(rules.unresolved_large_gap.condition, 'date gap > 30d without explanation');
});

test('date mismatch resolution plan is not accepted mapping', () => {
    const plan = readJson(DATE_PLAN_PATH);
    const manifest = readJson(MANIFEST_PATH);

    assert.equal(plan.raw_write_guard_compatibility.date_mismatch_plan_is_accepted_mapping, false);
    assert.equal(plan.raw_write_guard_compatibility.date_mismatch_plan_usable_by_raw_write, false);
    assert.equal(manifest.phase_5_21_l2v3l_date_mismatch_plan_is_accepted_mapping, false);
    assert.equal(manifest.phase_5_21_l2v3l_date_mismatch_plan_usable_by_raw_write, false);
});

test('identity mapping acceptance still does not equal baseline acceptance', () => {
    const plan = readJson(DATE_PLAN_PATH);

    assert.equal(plan.raw_write_guard_compatibility.identity_mapping_acceptance_does_not_accept_baseline, true);
    assert.equal(plan.raw_write_guard_compatibility.identity_mapping_acceptance_does_not_authorize_db_write, true);
    assert.equal(plan.raw_write_guard_compatibility.raw_write_still_requires_separate_baseline_acceptance, true);
});

test('identity mapping acceptance still does not equal final DB-write authorization', () => {
    const plan = readJson(DATE_PLAN_PATH);

    assert.equal(
        plan.raw_write_guard_compatibility.raw_write_still_requires_separate_final_db_write_authorization,
        true
    );
    assert.equal(
        plan.raw_write_guard_compatibility.raw_write_still_requires_separate_identity_mapping_acceptance,
        true
    );
});

test('raw_write_ready_for_execution remains false', () => {
    const plan = readJson(DATE_PLAN_PATH);
    const manifest = readJson(MANIFEST_PATH);

    assert.equal(plan.raw_write_ready_for_execution, false);
    assert.equal(manifest.raw_write_ready_for_execution, false);
});

test('date provenance correctly identifies schedule vs detail sources', () => {
    const plan = readJson(DATE_PLAN_PATH);

    const prov = plan.date_provenance_analysis;
    assert.equal(prov.schedule_date_source.includes('leagues?id=53'), true);
    assert.equal(prov.detail_date_source.includes('pageProps'), true);
    assert.equal(prov.detail_date_field_path, 'pageProps.general.matchTimeUTC');
    assert.equal(prov.date_source_divergence.includes('schedule date comes from overview listing'), true);
});

test('date gap pattern analysis identifies two clusters', () => {
    const plan = readJson(DATE_PLAN_PATH);

    const patterns = plan.date_gap_pattern_analysis;
    assert.equal(patterns.cluster_1_matchday_38_likely.detail_date, '2026-05-17T19:00:00.000Z');
    assert.equal(patterns.cluster_1_matchday_38_likely.detail_ids.length, 5);
    assert.equal(patterns.cluster_2_mid_season_likely.detail_ids.length, 3);
    assert.equal(patterns.cluster_1_matchday_38_likely.schedule_ids.length, 5);
    assert.equal(patterns.cluster_2_mid_season_likely.schedule_ids.length, 3);
});

test('proposed date resolution statuses cover all mismatch scenarios', () => {
    const plan = readJson(DATE_PLAN_PATH);

    const statuses = plan.proposed_date_resolution_statuses;
    assert.equal('date_match' in statuses, true);
    assert.equal('same_utc_day' in statuses, true);
    assert.equal('timezone_only_mismatch' in statuses, true);
    assert.equal('reverse_fixture_detected' in statuses, true);
    assert.equal('cross_season_slug_reuse' in statuses, true);
    assert.equal('unresolved_large_gap' in statuses, true);
    assert.equal('unknown' in statuses, true);
});

test('reverse fixture is identity mismatch not mapping', () => {
    const plan = readJson(DATE_PLAN_PATH);

    const app = plan.application_to_8_candidates;
    assert.equal(app.all_8_recommended_action.includes('should NOT be accepted as a mapping'), true);
    assert.equal(app.all_8_recommended_action.includes('identity mismatches'), true);
    assert.equal(
        app.mapping_acceptance_not_applicable.includes('correct remediation is not identity mapping acceptance'),
        true
    );
});

test('no full raw_data/pageProps/source body in L2V3L artifacts', () => {
    const planText = readText(DATE_PLAN_PATH);
    const reportText = readText(REPORT_PATH);
    const manifestText = readText(MANIFEST_PATH);

    for (const text of [planText, reportText, manifestText]) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
    }
});

test('L2V3L plan does not clear raw write guard', () => {
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
        reverseFixtureDetected: true,
    });
    const gate = assertRawWriteIdentityGate(result);

    assert.equal(result.identity_reconciliation_status, 'unresolved_schedule_detail_mapping');
    assert.equal(gate.ok, false);
    assert.equal(gate.transaction_began, false);
    assert.equal(gate.inserted_raw_match_data_count, 0);
});

test('manifest metadata consistent across L2V3J, L2V3K, and L2V3L', () => {
    const manifest = readJson(MANIFEST_PATH);

    assert.equal(manifest.phase_5_21_l2v3j_review_blocked_count, 8);
    assert.equal(manifest.phase_5_21_l2v3k_review_blocked_count, 8);
    assert.equal(manifest.phase_5_21_l2v3l_reverse_fixture_detected_count, 8);

    assert.equal(manifest.phase_5_21_l2v3j_accepted_mapping_count, 0);
    assert.equal(manifest.phase_5_21_l2v3k_accepted_mapping_count, 0);
    assert.equal(manifest.phase_5_21_l2v3l_accepted_mapping_count, 0);

    assert.equal(manifest.requires_separate_identity_mapping_acceptance, true);
    assert.equal(manifest.requires_separate_baseline_acceptance, true);
    assert.equal(manifest.requires_separate_final_db_write_authorization, true);
    assert.equal(manifest.raw_write_ready_for_execution, false);
});
