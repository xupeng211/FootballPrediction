'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const RESULT_PATH = 'docs/_manifests/fotmob_observed_identity_evidence_acquisition_result.adg12.json';
const { BATCH_A_IDS } = require('../../scripts/ops/fotmob_observed_identity_evidence_acquisition_execute_adg12');
const {
    validateStrictFixtureIdentity,
    FIXTURE_IDENTITY_GUARD_PASSED,
    FIXTURE_IDENTITY_GUARD_BLOCKED,
} = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

function readResult() {
    return JSON.parse(fs.readFileSync(path.join(PROJECT_ROOT, RESULT_PATH), 'utf8'));
}

test('ADG12 Batch A has exactly 9 samples', () => {
    const artifact = readResult();
    assert.equal(artifact.batch_sample_count, 9);
    assert.equal(artifact.batch_id, 'ADG12_BATCH_A');
    assert.equal(artifact.evidence_acquisition_performed, true);
});

test('ADG12 positive control #4813735 passes strict guard', () => {
    const artifact = readResult();
    const pc = artifact.batch_results.find(r => r.schedule_external_id === '4813735');
    assert.ok(pc);
    assert.equal(pc.strict_guard_classification, 'correct_mapping');
    assert.equal(pc.strict_guard_status, FIXTURE_IDENTITY_GUARD_PASSED);
    assert.equal(pc.raw_write_execution_ready, false);
});

test('ADG12 suspended control #4830466 remains blocked', () => {
    const artifact = readResult();
    const s = artifact.batch_results.find(r => r.schedule_external_id === '4830466');
    assert.ok(s);
    assert.equal(s.strict_guard_classification, 'suspended_control_still_blocked');
    assert.equal(s.is_suspended_reference, true);
    assert.equal(s.raw_write_execution_ready, false);
});

test('ADG12 reverse controls 4830458 and 4830464 remain blocked', () => {
    const artifact = readResult();
    for (const id of ['4830458', '4830464']) {
        const r = artifact.batch_results.find(t => t.schedule_external_id === id);
        assert.ok(r, `${id} must exist`);
        assert.equal(r.strict_guard_classification, 'reverse_fixture_mapping_error');
        assert.equal(r.strict_guard_status, FIXTURE_IDENTITY_GUARD_BLOCKED);
    }
});

test('ADG12 newly acquired targets should have observed identity', () => {
    const artifact = readResult();
    const acquired = artifact.batch_results.filter(r =>
        r.evidence_acquisition_status === 'observed_identity_acquired');
    // All 5 missing-observed targets were acquired
    assert.equal(acquired.length, 5);
    for (const r of acquired) {
        assert.ok(r.observed_detail_id);
        assert.ok(r.observed_home_team);
        assert.ok(r.observed_away_team);
        assert.ok(r.fetched === true);
    }
});

test('ADG12 raw_write_ready_count always zero', () => {
    const artifact = readResult();
    assert.equal(artifact.raw_write_ready_count, 0);
    assert.equal(artifact.re_acceptance_candidate_count, 0);
    for (const r of artifact.batch_results) {
        assert.equal(r.raw_write_execution_ready, false);
    }
});

test('ADG12 safety: no full body saved, no DB write, no mutations', () => {
    const artifact = readResult();

    assert.equal(artifact.no_db_write, true);
    assert.equal(artifact.no_raw_write, true);
    assert.equal(artifact.no_re_acceptance, true);
    assert.equal(artifact.no_suspension_reversal, true);
    assert.equal(artifact.source_inventory_mutation_performed, false);
    assert.equal(artifact.candidate_mutation_performed, false);
    assert.equal(artifact.full_body_saved, false);
    assert.equal(artifact.full_payload_saved, false);
    assert.equal(artifact.full_response_saved, false);
    assert.equal(artifact.no_browser_automation, true);
    assert.equal(artifact.no_direct_api_probing, true);
    assert.equal(artifact.no_proxy_bypass, true);
    assert.equal(artifact.no_captcha_bypass, true);
});

test('ADG12 Batch A IDs match ADG11 plan', () => {
    assert.deepEqual(BATCH_A_IDS, [
        '4813735', '4830467', '4830468', '4830469', '4830470', '4830471',
        '4830458', '4830464', '4830466',
    ]);
});

test('ADG12 guard integration still works for correct mapping', () => {
    const result = validateStrictFixtureIdentity({
        schedule_external_id: '4813735',
        detail_external_id_candidate: '4813735',
        expected_home_team: 'AFC Bournemouth',
        expected_away_team: 'Manchester City',
        observed_detail_id: '4813735',
        observed_home_team: 'AFC Bournemouth',
        observed_away_team: 'Manchester City',
        expected_match_date: '2026-05-19T18:30:00.000Z',
        observed_match_date: 'Tue, May 19, 2026, 18:30 UTC',
    });

    assert.equal(result.fixture_identity_guard_status, FIXTURE_IDENTITY_GUARD_PASSED);
    assert.equal(result.audit_classification, 'correct_mapping');
});
