'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PLAN_PATH = 'docs/_manifests/fotmob_ligue1_source_inventory_inversion_correction_plan.adg13.json';

function readPlan() {
    return JSON.parse(fs.readFileSync(path.join(PROJECT_ROOT, PLAN_PATH), 'utf8'));
}

test('ADG13 plan confirms systematic home/away inversion', () => {
    const p = readPlan();
    assert.equal(p.systematic_home_away_inversion_confirmed, true);
    assert.equal(p.newly_acquired_reverse_fixture_count, 5);
    assert.equal(p.known_reverse_control_count, 2);
    assert.equal(p.total_reverse_evidence_count, 7);
    assert.equal(p.planning_performed, true);
});

test('ADG13 plan identifies 4 runtime paths to correct', () => {
    const p = readPlan();
    assert.equal(p.runtime_paths_to_correct.length, 4);
    const paths = p.runtime_paths_to_correct.map(r => r.path);
    assert.ok(paths.some(p => p.includes('FotMobSourceInventoryAdapter')));
    assert.ok(paths.some(p => p.includes('source_inventory_enrichment_apply')));
    assert.ok(paths.some(p => p.includes('enriched_target_regeneration_execute')));
    assert.ok(paths.some(p => p.includes('FotMobRouteIdentityReconciler')));
});

test('ADG13 plan has 8 correction rules', () => {
    const p = readPlan();
    assert.equal(p.correction_strategy.rules.length, 8);
    const ruleNames = p.correction_strategy.rules.map(r => r.rule);
    assert.ok(ruleNames.includes('team_pair_orientation_binding'));
    assert.ok(ruleNames.includes('positive_control_preservation'));
    assert.ok(ruleNames.includes('suspended_preservation'));
    assert.ok(ruleNames.includes('url_hash_as_evidence_not_acceptance'));
    assert.ok(ruleNames.includes('raw_write_boundary'));
});

test('ADG13 plans to stop Batch B/C/D expansion', () => {
    const p = readPlan();
    assert.equal(p.recommendation_on_remaining_37_targets.stop_batch_expansion, true);
});

test('ADG13 ADG14 validation targets defined', () => {
    const p = readPlan();
    const v = p.adg14_validation_targets;
    assert.deepEqual(v.must_pass, ['4813735']);
    assert.equal(v.must_block.length, 7);
    assert.equal(v.must_remain_suspended.length, 8);
});

test('ADG13 plan is planning-only, no execution', () => {
    const p = readPlan();
    assert.equal(p.safety.live_fetch_performed, false);
    assert.equal(p.safety.db_write_performed, false);
    assert.equal(p.safety.raw_write_execution_performed, false);
    assert.equal(p.safety.re_acceptance_execution_performed, false);
    assert.equal(p.safety.suspension_reversal_performed, false);
    assert.equal(p.safety.source_inventory_mutation_performed, false);
    assert.equal(p.safety.raw_write_execution_ready, false);
    assert.equal(p.safety.batch_b_c_d_expansion_performed, false);
});

test('ADG13 recommends ADG14 implementation, not raw write', () => {
    const p = readPlan();
    const step = p.recommended_next_step.toLowerCase();
    assert.ok(step.includes('adg14'), 'must recommend ADG14');
    assert.ok(step.includes('do not raw write') || step.includes('not raw write'),
        'must say do not raw write');
});
