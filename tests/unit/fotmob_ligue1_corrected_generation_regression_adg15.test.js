'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const RESULT_PATH = 'docs/_manifests/fotmob_ligue1_corrected_generation_regression.adg15.json';

function readResult() { return JSON.parse(fs.readFileSync(path.join(PROJECT_ROOT, RESULT_PATH), 'utf8')); }

test('ADG15 positive control #4813735 accepted_validated', () => {
    const a = readResult();
    const pc = a.regression_results.find(r => r.external_id === '4813735');
    assert.ok(pc);
    assert.equal(pc.classification, 'accepted_validated');
    assert.equal(pc.correction, false);
    assert.equal(pc.raw_write_ready, false);
});

test('ADG15 seven reverse samples all rejected_reverse_fixture_mapping', () => {
    const a = readResult();
    const ids = ['4830458','4830464','4830467','4830468','4830469','4830470','4830471'];
    for (const id of ids) {
        const r = a.regression_results.find(t => t.external_id === id);
        assert.ok(r, `${id} must exist`);
        assert.equal(r.classification, 'rejected_reverse_fixture_mapping', `${id} must be rejected`);
        assert.equal(r.correction, true, `${id} must need correction`);
        assert.equal(r.raw_write_ready, false);
    }
});

test('ADG15 suspended targets remain blocked', () => {
    const a = readResult();
    const suspended = a.regression_results.filter(r => r.is_suspended);
    assert.equal(suspended.length, 8);
    for (const s of suspended) {
        assert.equal(s.classification, 'suspended_still_blocked');
        assert.equal(s.correction, false);
    }
});

test('ADG15 counts are consistent', () => {
    const a = readResult();
    assert.equal(a.total_batch_target_count, 51, '50 candidates + 1 positive control');
    assert.equal(a.accepted_validated_no_write_count, 1);
    assert.equal(a.rejected_reverse_fixture_mapping_count, 7);
    assert.equal(a.suspended_still_blocked_count, 8);
    assert.equal(a.unknown_insufficient_evidence_count, 35);
    assert.equal(a.correction_candidate_required_count, 7);
    assert.equal(a.raw_write_ready_count, 0);
    assert.equal(a.re_acceptance_candidate_count, 0);
});

test('ADG15 safety: no-write, no-mutation', () => {
    const a = readResult();
    assert.equal(a.no_db_write, true);
    assert.equal(a.no_raw_write, true);
    assert.equal(a.no_re_acceptance, true);
    assert.equal(a.source_inventory_mutation_performed, false);
    assert.equal(a.candidate_mutation_performed, false);
    assert.equal(a.raw_write_execution_performed, false);
    assert.equal(a.full_payload_saved, false);
});

test('ADG15 next step recommends evidence planning, not raw write', () => {
    const a = readResult();
    const step = a.recommended_next_step.toLowerCase();
    assert.ok(step.includes('do not raw write'), 'must explicitly say do not raw write');
    assert.ok(step.includes('evidence') || step.includes('correction') || step.includes('planning'),
        'must recommend planning/evidence/correction');
});
