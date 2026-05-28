'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const RP = path.resolve(__dirname, '../../docs/_manifests/fotmob_observed_identity_evidence_acquisition_batch_b.adg16.json');
function r() { return JSON.parse(fs.readFileSync(RP, 'utf8')); }

test('ADG16 Batch B has 10 targets', () => { const a = r(); assert.equal(a.batch_results.length, 10); assert.equal(a.batch_id, 'ADG16_BATCH_B'); });
test('ADG16 all 10 are reverse_fixture_mapping_error', () => {
    const a = r();
    for (const t of a.batch_results) { assert.equal(t.guard_classification, 'rejected_reverse_fixture_mapping', `${t.external_id} must be reverse`); }
    assert.equal(a.reverse_fixture_mapping_error_count, 10);
});
test('ADG16 3 reused, 7 acquired', () => { const a = r(); assert.equal(a.evidence_reuse_count, 3); assert.equal(a.observed_identity_acquired_count, 7); });
test('ADG16 raw_write_ready=0', () => { const a = r(); assert.equal(a.raw_write_ready_count, 0); for (const t of a.batch_results) assert.equal(t.raw_write_ready, false); });
test('ADG16 safety flags', () => { const a = r(); assert.equal(a.no_db_write, true); assert.equal(a.no_raw_write, true); assert.equal(a.no_re_acceptance, true); assert.equal(a.full_body_saved, false); });
