'use strict'; // lifecycle: test-fixture
const assert = require('node:assert/strict');
const test = require('node:test');
const { build } = require('../../scripts/ops/fotmob_ligue1_canonical_url_pair_discovery_planning_adg43');

test('ADG43 identifies 27 missing canonical URL targets and 5 unverified targets', () => {
    const a = build();
    assert.equal(a.total_corrected_candidates, 32);
    assert.equal(a.missing_canonical_url_targets, 27);
    assert.equal(a.unverified_route_hash_pair_targets, 5);
    assert.equal(a.missing_canonical_url_targets + a.unverified_route_hash_pair_targets, 32);
});

test('ADG43 all 27 missing targets are classified correctly', () => {
    const a = build();
    const missing = a.target_groups.missing_canonical_url_targets;
    assert.equal(missing.length, 27);
    assert.ok(missing.every(t => t.classification === 'canonical_url_missing_needs_l1_discovery'));
    assert.ok(missing.every(t => t.l2_guessing_blocked === true));
    assert.ok(missing.every(t => t.raw_write_blocked === true));
    assert.ok(missing.every(t => t.canonical_pair_probe_required === true));
    assert.ok(missing.every(t => t.expected_home && t.expected_away));
});

test('ADG43 all 5 unverified targets have route_hash_pair and need verification', () => {
    const a = build();
    const unverified = a.target_groups.unverified_route_hash_pair_targets;
    assert.equal(unverified.length, 5);
    assert.ok(unverified.every(t => t.route_code && t.hash_id));
    assert.ok(unverified.every(t => t.route_hash_pair));
    assert.ok(unverified.every(t => t.canonical_detail_url));
    assert.ok(unverified.every(t => t.classification === 'route_hash_pair_unverified_needs_detail_verification'));
    assert.ok(unverified.every(t => t.detail_page_verification_required === true));
    assert.ok(unverified.every(t => t.raw_write_blocked === true));
    assert.ok(unverified.every(t => t.slug_orientation_reversed === true));
    assert.ok(unverified.every(t => t.reverse_fixture_risk === true));
});

test('ADG43 blocks all L2 guessing, detail ID as route code, and raw write', () => {
    const a = build();
    assert.equal(a.l2_guessing_blocked_count, 32);
    assert.equal(a.raw_write_ready_count, 0);
    assert.equal(a.canonical_pair_probe_required_count, 27);
    assert.equal(a.alternate_hash_id_discovery_required_count, 5);
    assert.equal(a.reverse_fixture_risk_count, 5);
});

test('ADG43 safety flags are all false', () => {
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
    assert.equal(s.browser_bypass_performed, false);
});

test('ADG43 ADG44 probe design is correct and not executed', () => {
    const a = build();
    const p = a.adg44_probe_design;
    assert.equal(p.not_executed_in_adg43, true);
    assert.equal(p.explicit_user_authorization_required, true);
    assert.equal(p.no_full_payload, true);
    assert.equal(p.no_browser, true);
    assert.equal(p.no_proxy, true);
    assert.equal(p.no_bypass, true);
    assert.ok(p.max_target_count <= 5);
    assert.ok(p.max_request_count <= 5);
    assert.ok(p.stop_on_403_or_block);
    assert.ok(p.stop_on_captcha);
    assert.ok(p.stop_on_first_identity_mismatch);
    assert.ok(Array.isArray(p.safe_summary_fields));
    assert.ok(p.safe_summary_fields.every(f => typeof f === 'string'));
});
