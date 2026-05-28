'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PLAN_PATH = 'docs/_manifests/fotmob_observed_identity_evidence_acquisition_plan.adg11.json';

function readJson(filePath) {
    return JSON.parse(fs.readFileSync(path.join(PROJECT_ROOT, filePath), 'utf8'));
}

test('ADG11 plan is planning-only with no execution performed', () => {
    const plan = readJson(PLAN_PATH);

    assert.equal(plan.planning_performed, true);
    assert.equal(plan.governance_type, 'planning_only_no_execution');
    assert.equal(plan.safety.live_fetch_performed, false);
    assert.equal(plan.safety.network_request_performed, false);
    assert.equal(plan.safety.db_write_performed, false);
    assert.equal(plan.safety.raw_write_execution_performed, false);
    assert.equal(plan.safety.re_acceptance_execution_performed, false);
    assert.equal(plan.safety.suspension_reversal_performed, false);
    assert.equal(plan.safety.raw_write_execution_ready, false);
});

test('ADG11 plan covers all four target groups', () => {
    const plan = readJson(PLAN_PATH);
    const groups = plan.planned_target_groups;

    assert.equal(groups.missing_observed_identity_evidence.target_count, 37);
    assert.equal(groups.missing_observed_identity_evidence.external_ids.length, 37);
    assert.equal(groups.missing_observed_identity_evidence.adg12_role, 'primary_evidence_acquisition_candidates');

    assert.equal(groups.known_reverse_fixture_controls.target_count, 5);
    assert.equal(groups.known_reverse_fixture_controls.adg12_role,
        'negative_controls_ensure_known_errors_not_re_accepted');

    assert.equal(groups.suspended_preservation_controls.target_count, 8);
    assert.equal(groups.suspended_preservation_controls.adg12_role,
        'preservation_controls_remain_blocked_no_unsuspend');

    assert.equal(groups.positive_control.target_count, 1);
    assert.deepEqual(groups.positive_control.external_ids, ['4813735']);
});

test('ADG11 Batch A policy is correctly sized and gated', () => {
    const plan = readJson(PLAN_PATH);
    const batch = plan.planned_adg12_batch_policy;

    assert.equal(batch.adg12_requires_explicit_authorization, true);
    assert.equal(batch.adg12_batch_a_planned, true);
    assert.equal(batch.adg12_batch_a_planned_sample_count, 9);
    assert.ok(batch.adg12_batch_a_external_ids.includes('4813735'),
        'Batch A must include positive control');
    assert.ok(batch.adg12_batch_a_external_ids.includes('4830458'),
        'Batch A must include reverse control');
    assert.ok(batch.adg12_batch_a_external_ids.includes('4830466'),
        'Batch A must include suspended control');
    assert.equal(batch.max_requests_per_target, 1);
    assert.equal(batch.no_retry_storm, true);
    assert.equal(batch.stop_on_403_or_block, true);
});

test('ADG11 planned evidence strategy has no prohibited operations', () => {
    const plan = readJson(PLAN_PATH);
    const strategy = plan.planned_evidence_acquisition_strategy;

    assert.equal(strategy.strategy, 'public_page_route_safe_summary_acquisition');
    const prohibited = strategy.prohibited_operations;
    assert.ok(prohibited.includes('captcha_bypass'));
    assert.ok(prohibited.includes('db_write'));
    assert.ok(prohibited.includes('raw_match_data_insert'));
    assert.ok(prohibited.includes('re_acceptance'));
    assert.ok(prohibited.includes('suspension_reversal'));
    assert.ok(prohibited.includes('saving_full_pageprops'));
    assert.ok(prohibited.includes('saving_full_raw_data'));
});

test('ADG11 planned evidence fields are safe and bounded', () => {
    const plan = readJson(PLAN_PATH);
    const fields = plan.planned_evidence_fields;

    assert.ok(fields.includes('observed_detail_id_if_safely_available'));
    assert.ok(fields.includes('observed_home_team_if_safely_available'));
    assert.ok(fields.includes('observed_away_team_if_safely_available'));
    assert.ok(fields.includes('no_full_body_saved'));
    assert.ok(fields.includes('no_db_write'));
    assert.ok(fields.includes('no_raw_write'));
    assert.ok(!fields.includes('full_html'));
    assert.ok(!fields.includes('full_raw_data'));
    assert.ok(!fields.includes('full_pageprops'));
});

test('ADG11 ADG12 prerequisites are explicit', () => {
    const plan = readJson(PLAN_PATH);

    assert.equal(plan.adg12_prerequisites.length >= 5, true);
    assert.ok(plan.adg12_prerequisites.some(p => p.includes('explicit authorization')));
    assert.ok(plan.adg12_prerequisites.some(p => p.includes('ADG11 plan merged')));
    assert.ok(plan.adg12_prerequisites.some(p => p.includes('ADG9 strict guard')));
});

test('ADG11 recommended next step is ADG12 acquisition, not raw write', () => {
    const plan = readJson(PLAN_PATH);

    assert.ok(plan.recommended_next_step.includes('ADG12'));
    assert.ok(plan.recommended_next_step.includes('bounded observed identity evidence acquisition'));
    assert.ok(!plan.recommended_next_step.toLowerCase().includes('raw write'));
});
