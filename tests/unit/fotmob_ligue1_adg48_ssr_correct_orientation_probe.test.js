'use strict'; // lifecycle: test-fixture
const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const MANIFEST = path.resolve(__dirname, '../../docs/_manifests/fotmob_ligue1_adg48_ssr_correct_orientation_probe.json');

test('ADG48 probe targets 3 targets, 2 attempted, 1 not attempted', () => {
    const a = JSON.parse(fs.readFileSync(MANIFEST, 'utf8'));
    assert.equal(a.planned_probe_target_count, 3);
    assert.equal(a.attempted_request_count, 2);
    assert.equal(a.successful_http_200_count, 2);
    assert.equal(a.probe_not_attempted_missing_request_url_count + a.not_attempted_due_to_prior_stop_count, 1);
});

test('ADG48 both attempted pages have __NEXT_DATA__ markers', () => {
    const a = JSON.parse(fs.readFileSync(MANIFEST, 'utf8'));
    assert.equal(a.next_data_marker_found_count, 2);
    assert.ok(a.results.filter(r => r.request_attempted).every(r => r.next_data_marker_present));
});

test('ADG48 target 1 confirms reverse pair observed again', () => {
    const a = JSON.parse(fs.readFileSync(MANIFEST, 'utf8'));
    const t1 = a.results[0];
    assert.equal(t1.classification, 'reverse_pair_observed_again');
    assert.equal(t1.observed_home, 'Angers');
    assert.equal(a.reverse_pair_observed_again_count, 1);
});

test('ADG48 target 2 confirms second reverse fixture', () => {
    const a = JSON.parse(fs.readFileSync(MANIFEST, 'utf8'));
    const t2 = a.results[1];
    assert.equal(t2.classification, 'route_hash_pair_reverse_fixture_rejected');
    assert.equal(t2.observed_home, 'Auxerre');
    assert.equal(a.reverse_fixture_rejected_count, 1);
});

test('ADG48 no full payload saved', () => {
    const a = JSON.parse(fs.readFileSync(MANIFEST, 'utf8'));
    assert.equal(a.full_html_saved, false);
    assert.equal(a.full_next_data_saved, false);
    assert.equal(a.full_pageprops_saved, false);
    assert.equal(a.full_payload_saved, false);
});

test('ADG48 safety and write boundaries preserved', () => {
    const a = JSON.parse(fs.readFileSync(MANIFEST, 'utf8'));
    const s = a.safety;
    assert.equal(s.db_write_performed, false);
    assert.equal(s.raw_write_execution_performed, false);
    assert.equal(s.full_payload_saved, false);
    assert.equal(s.browser_bypass_performed, false);
    assert.equal(a.raw_write_ready_count, 0);
});
