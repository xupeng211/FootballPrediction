'use strict';
// lifecycle: test-fixture
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const RP = path.resolve(__dirname, '../../docs/_manifests/fotmob_ligue1_corrected_source_validation.adg22.json');
function r() { return JSON.parse(fs.readFileSync(RP, 'utf8')); }

test('ADG22 all 5 corrected candidates validated', () => { const a = r(); assert.equal(a.corrected_validated, 5); assert.equal(a.corrected_failed, 0); });
test('ADG22 each corrected candidate passes guard and candidate classification', () => {
    const a = r(); const v = a.validation_results.filter(t => !t.is_pc && !t.is_suspended);
    assert.equal(v.length, 5);
    for (const t of v) { assert.equal(t.validation_status, 'corrected_candidate_validated_no_write'); assert.equal(t.validated, true); assert.equal(t.rw, false); }
});
test('ADG22 positive control preserved, suspended blocked', () => { const a = r(); assert.equal(a.positive_preserved, 1); assert.equal(a.suspended_blocked, 1); });
test('ADG22 raw_write_ready=0 and safety', () => { const a = r(); assert.equal(a.raw_write_ready, 0); assert.equal(a.no_network, true); assert.equal(a.no_db_write, true); assert.equal(a.no_raw_write, true); assert.equal(a.no_mutation, true); });
