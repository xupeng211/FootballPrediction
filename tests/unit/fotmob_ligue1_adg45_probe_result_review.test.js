'use strict'; // lifecycle: test-fixture
const assert = require('node:assert/strict');
const test = require('node:test');
const { build } = require('../../scripts/ops/fotmob_ligue1_adg45_probe_result_review');

test('ADG45 review records ADG44 endpoint 404 counts correctly', () => {
    const a = build();
    const s = a.adg44_result_summary;
    assert.equal(s.endpoint_http_request_count, 2);
    assert.equal(s.endpoint_404_count, 2);
    assert.equal(s.successful_http_200_count, 0);
    assert.equal(s.target_classified_count, 5);
    assert.equal(s.canonical_url_pair_discovered_count, 0);
    assert.equal(s.route_hash_pair_verified_count, 0);
    assert.equal(s.all_targets_blocked, true);
    assert.ok(s.stop_reason.includes('fotmob_api_endpoints_not_accessible'));
});

test('ADG45 root cause correctly identifies simple HTTPS strategy failure', () => {
    const a = build();
    assert.equal(a.root_cause.simple_https_get_endpoint_strategy_failed, true);
    assert.ok(a.root_cause.evidence.includes('404'));
    assert.ok(a.root_cause.implication.includes('cannot proceed'));
});

test('ADG45 L1 discovery strategy requires revision', () => {
    const a = build();
    assert.equal(a.l1_discovery_strategy_requires_revision, true);
    assert.ok(Array.isArray(a.revised_strategy_options));
    assert.ok(a.revised_strategy_options.length >= 3);
    for (const s of a.revised_strategy_options) {
        assert.ok(s.name);
        assert.ok(s.description);
        assert.equal(s.requires_authorization, true);
        assert.equal(s.not_executed_in_adg45, true);
    }
});

test('ADG45 does not execute any network request', () => {
    const a = build();
    const s = a.safety;
    assert.equal(s.live_fetch_performed, false);
    assert.equal(s.network_request_performed, false);
    assert.equal(s.db_write_performed, false);
    assert.equal(s.raw_write_execution_performed, false);
    assert.equal(s.raw_match_data_insert_performed, false);
    assert.equal(s.full_payload_saved, false);
    assert.equal(s.re_acceptance_performed, false);
    assert.equal(s.suspension_reversal_performed, false);
});

test('ADG45 raw_write_ready_count is 0', () => {
    const a = build();
    assert.equal(a.raw_write_ready_count, 0);
    assert.ok(a.recommended_next_step.includes('raw write'));
});

test('ADG45 recommends user authorization for next step', () => {
    const a = build();
    assert.ok(a.recommended_next_step.includes('authorization'));
    assert.ok(a.recommended_next_step.includes('raw write'));
    assert.ok(a.recommended_approach.length > 0);
});
