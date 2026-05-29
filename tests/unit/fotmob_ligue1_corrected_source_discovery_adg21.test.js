'use strict';
// lifecycle: test-fixture
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const RP = path.resolve(__dirname, '../../docs/_manifests/fotmob_ligue1_corrected_source_discovery.adg21.json');
function r() { return JSON.parse(fs.readFileSync(RP, 'utf8')); }

test('ADG21 all 5 eligible targets found oriented corrected candidates', () => {
    const a = r();
    assert.equal(a.selected_target_count, 5);
    assert.equal(a.proposed_corrected_no_write, 5);
    assert.equal(a.corrected_source_not_found, 0);
    const targets = a.discovery_results.filter(t => !t.is_pc && !t.is_suspended);
    for (const t of targets) {
        assert.equal(t.selection_status, 'oriented_match_selected', `${t.external_id} must be oriented_match_selected`);
        assert.equal(t.candidate_status, 'accepted_validated');
        assert.equal(t.guard_status, 'passed');
        assert.equal(t.raw_write_ready, false);
    }
});

test('ADG21 positive control preserved', () => {
    const a = r();
    const pc = a.discovery_results.find(t => t.is_pc);
    assert.ok(pc);
    assert.equal(pc.selection_status, 'positive_control_preserved');
    assert.equal(pc.raw_write_ready, false);
});

test('ADG21 suspended control blocked', () => {
    const a = r();
    const s = a.discovery_results.find(t => t.is_suspended);
    assert.ok(s);
    assert.equal(s.selection_status, 'suspended_still_blocked');
});

test('ADG21 league API returned data (one request bounded)', () => {
    const a = r();
    assert.equal(a.request_attempt_count, 1, 'exactly one league API request');
    assert.ok(a.league_api_record_count > 500, 'league API should have many records');
});

test('ADG21 raw_write_ready=0 and safety', () => {
    const a = r();
    assert.equal(a.raw_write_ready, 0);
    assert.equal(a.re_acceptance_candidate, 0);
    assert.equal(a.no_db_write, true);
    assert.equal(a.no_raw_write, true);
    assert.equal(a.no_mutation, true);
    assert.equal(a.no_browser, true);
    assert.equal(a.no_proxy, true);
    assert.equal(a.full_payload_saved, false);
});
