'use strict';
// lifecycle: test-fixture
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const RP = path.resolve(__dirname, '../../docs/_manifests/fotmob_ligue1_remaining_corrected_source_discovery.adg23.json');
function r() { return JSON.parse(fs.readFileSync(RP, 'utf8')); }

test('ADG23 all 27 remaining targets found oriented corrected candidates', () => {
    const a = r();
    const remaining = a.discovery_results.filter(t => !t.is_pc && !t.is_suspended && !t.is_adg22_control);
    assert.equal(remaining.length, 27);
    assert.equal(a.proposed_corrected, 27);
    assert.equal(a.corrected_not_found, 0);
    for (const t of remaining) {
        assert.equal(t.selection_status, 'oriented_match_selected', `${t.external_id} must be oriented`);
        assert.equal(t.candidate_status, 'accepted_validated');
        assert.equal(t.guard_status, 'passed');
        assert.equal(t.raw_write_ready, false);
    }
});
test('ADG23 combined with ADG21: 32/32 pending targets found', () => {
    const a = r();
    assert.equal(a.adg22_validated_controls, 5, '5 from ADG21 validated');
    assert.equal(a.proposed_corrected, 27, '27 newly discovered');
    // 5 + 27 = 32 total (all non-suspended non-rejected Ligue 1 targets)
});
test('ADG23 positive control preserved, suspended blocked', () => { const a = r(); assert.equal(a.positive_preserved, 1); assert.equal(a.suspended_blocked, 1); });
test('ADG23 raw_write_ready=0 and safety', () => { const a = r(); assert.equal(a.raw_write_ready, 0); assert.equal(a.no_db_write, true); assert.equal(a.no_raw_write, true); assert.equal(a.no_mutation, true); });
