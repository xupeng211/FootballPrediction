'use strict'; // lifecycle: test-fixture
const assert = require('node:assert/strict');
const test = require('node:test');
const { build } = require('../../scripts/ops/fotmob_ligue1_adg47_ssr_probe_result_review');

test('ADG47 confirms SSR strategy viable', () => {
    const a = build();
    assert.equal(a.ssr_strategy_viable, true);
    assert.equal(a.ssr_evidence.public_match_page_http_200, true);
    assert.equal(a.ssr_evidence.next_data_marker_found, true);
    assert.equal(a.ssr_evidence.full_payload_saved, false);
});

test('ADG47 confirms reverse fixture for 2o4ahb#4830473', () => {
    const a = build();
    assert.equal(a.reverse_fixture_confirmed, true);
    const d = a.reverse_fixture_detail;
    assert.equal(d.route_hash_pair, '2o4ahb#4830473');
    assert.equal(d.expected_home, 'Paris Saint-Germain');
    assert.notEqual(d.observed_home.toLowerCase(), 'paris saint-germain');
    assert.ok(d.conclusion.includes('REVERSE'));
});

test('ADG47 records correct-orientation discovery needs', () => {
    const a = build();
    assert.equal(a.correct_orientation_route_hash_pair_missing, true);
    assert.equal(a.confirmed_reverse_fixture_count, 1);
    assert.equal(a.remaining_unverified_count, 4);
    assert.equal(a.canonical_url_missing_count, 27);
    assert.equal(a.known_route_hash_pair_count, 5);
});

test('ADG47 revised plan requires explicit authorization', () => {
    const a = build();
    assert.equal(a.revised_discovery_plan.requires_explicit_user_authorization, true);
    assert.equal(a.revised_discovery_plan.not_authorized, true);
    assert.ok(a.revised_discovery_plan.needs.length >= 3);
});

test('ADG47 performs no network request', () => {
    const a = build();
    const s = a.safety;
    assert.equal(s.live_fetch_performed, false);
    assert.equal(s.network_request_performed, false);
    assert.equal(s.db_write_performed, false);
    assert.equal(s.raw_write_execution_performed, false);
    assert.equal(s.full_payload_saved, false);
    assert.equal(s.full_html_saved, false);
    assert.equal(s.full_next_data_saved, false);
});

test('ADG47 raw_write_ready_count is 0', () => {
    const a = build();
    assert.equal(a.raw_write_ready_count, 0);
    assert.ok(a.recommended_next_step.includes('raw write'));
});
