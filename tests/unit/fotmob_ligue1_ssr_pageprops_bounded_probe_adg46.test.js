'use strict'; // lifecycle: test-fixture
const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const MANIFEST = path.resolve(__dirname, '../../docs/_manifests/fotmob_ligue1_ssr_pageprops_bounded_probe.adg46.json');

test('ADG46 SSR probe manifest exists with valid structure', () => {
    const a = JSON.parse(fs.readFileSync(MANIFEST, 'utf8'));
    assert.equal(a.chosen_strategy, 'fotmob_ssr_pageprops');
    assert.equal(a.user_authorization_confirmed, true);
    assert.equal(a.ssr_gate_merged, true);
    assert.equal(a.planned_probe_target_count, 2);
    assert.ok(Array.isArray(a.results));
    assert.equal(a.results.length, 2);
});

test('ADG46 SSR probe found __NEXT_DATA__ marker on target 1', () => {
    const a = JSON.parse(fs.readFileSync(MANIFEST, 'utf8'));
    assert.equal(a.next_data_marker_found_count, 1);
    assert.equal(a.pageprops_marker_found_count, 1);
    assert.equal(a.hydration_marker_found_count, 1);
    assert.equal(a.successful_http_200_count, 1);
});

test('ADG46 SSR probe correctly identified reverse fixture on target 1', () => {
    const a = JSON.parse(fs.readFileSync(MANIFEST, 'utf8'));
    const r1 = a.results[0];
    assert.equal(r1.classification, 'route_hash_pair_reverse_fixture_rejected');
    assert.equal(r1.observed_home, 'Angers');
    assert.equal(r1.observed_away, 'Paris Saint-Germain');
    // Expected is PSG home vs Angers away — observed is reversed
    assert.notEqual(r1.observed_home.toLowerCase(), 'paris saint-germain');
});

test('ADG46 SSR probe target 2 correctly not attempted', () => {
    const a = JSON.parse(fs.readFileSync(MANIFEST, 'utf8'));
    const r2 = a.results[1];
    assert.equal(r2.request_attempted, false);
    assert.ok(r2.classification === 'not_attempted_due_to_prior_stop' || r2.classification === 'probe_not_attempted_missing_request_url');
});

test('ADG46 no full payload saved', () => {
    const a = JSON.parse(fs.readFileSync(MANIFEST, 'utf8'));
    assert.equal(a.full_html_saved, false);
    assert.equal(a.full_next_data_saved, false);
    assert.equal(a.full_pageprops_saved, false);
    assert.equal(a.full_payload_saved, false);
    assert.ok(a.results.every(r => r.full_html_saved !== true));
    assert.ok(a.results.every(r => r.raw_write_ready === false));
});

test('ADG46 safety and write boundaries preserved', () => {
    const a = JSON.parse(fs.readFileSync(MANIFEST, 'utf8'));
    const s = a.safety;
    assert.equal(s.db_write_performed, false);
    assert.equal(s.raw_write_execution_performed, false);
    assert.equal(s.raw_match_data_insert_performed, false);
    assert.equal(s.full_payload_saved, false);
    assert.equal(s.full_html_saved, false);
    assert.equal(s.full_next_data_saved, false);
    assert.equal(s.browser_bypass_performed, false);
    assert.equal(s.proxy_used, false);
    assert.equal(s.captcha_bypass, false);
    assert.equal(a.raw_write_ready_count, 0);
});
