'use strict';
// lifecycle: test-fixture
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const RP = path.resolve(__dirname, '../../docs/_manifests/fotmob_ligue1_remaining_corrected_source_validation.adg24.json');
function r() { return JSON.parse(fs.readFileSync(RP, 'utf8')); }

test('ADG24 all 27 corrected candidates validated', () => { const a = r(); assert.equal(a.validated, 27); assert.equal(a.failed, 0); });
test('ADG24 each validated candidate passes guard', () => {
    const a = r(); const v = a.validation_results.filter(t => !t.is_pc && !t.is_suspended && !t.is_adg22_control);
    assert.equal(v.length, 27);
    for (const t of v) { assert.equal(t.validated, true); assert.equal(t.rw, false); assert.equal(t.guard_status, 'passed'); }
});
test('ADG24 ADG22 5 controls preserved', () => { const a = r(); assert.equal(a.adg22_controls, 5); });
test('ADG24 raw_write_ready=0 and safety', () => { const a = r(); assert.equal(a.raw_write_ready, 0); assert.equal(a.no_network, true); assert.equal(a.no_db_write, true); assert.equal(a.no_raw_write, true); });
test('ADG24 32/32 combined milestone (ADG22 5 + ADG24 27)', () => {
    const a = r(); assert.equal(a.validated + a.adg22_controls, 32,
        '32/32 pending Ligue 1 targets now have validated corrected candidates'); });
