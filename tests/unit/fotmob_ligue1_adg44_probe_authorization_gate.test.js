'use strict'; // lifecycle: test-fixture
const assert = require('node:assert/strict');
const test = require('node:test');
const { build } = require('../../scripts/ops/fotmob_ligue1_adg44_probe_authorization_gate');

test('ADG44 auth gate selects exactly 5 future probe targets', () => {
    const a = build();
    assert.equal(a.future_probe_target_count, 5);
    assert.equal(a.future_probe_targets.length, 5);
    assert.equal(a.max_targets, 5);
    assert.equal(a.max_requests_per_target, 1);
});

test('ADG44 auth gate includes both missing and unverified target types', () => {
    const a = build();
    const statuses = a.future_probe_targets.map(t => t.current_status);
    assert.ok(statuses.some(s => s === 'canonical_url_missing_needs_l1_discovery'));
    assert.ok(statuses.some(s => s === 'route_hash_pair_unverified_needs_detail_verification'));
});

test('ADG44 auth gate requires explicit user authorization', () => {
    const a = build();
    assert.equal(a.requires_explicit_user_authorization, true);
    assert.equal(a.authorization_gate_prepared, true);
    assert.equal(a.probe_not_executed, true);
    assert.ok(a.authorization_scope.includes('ADG44'));
    assert.ok(a.authorization_scope.includes('does NOT authorize'));
});

test('ADG44 probe boundary enforces all stop rules', () => {
    const a = build();
    const b = a.probe_boundary;
    assert.equal(b.stop_on_403_or_block, true);
    assert.equal(b.stop_on_captcha, true);
    assert.equal(b.stop_on_first_identity_mismatch, true);
    assert.equal(b.stop_on_first_access_blocker, true);
    assert.equal(b.no_retry_on_block, true);
    assert.equal(b.no_browser, true);
    assert.equal(b.no_proxy, true);
    assert.equal(b.no_bypass, true);
    assert.equal(b.no_full_payload, true);
    assert.equal(b.safe_summary_only, true);
});

test('ADG44 auth gate blocks all write operations', () => {
    const a = build();
    const b = a.probe_boundary;
    assert.equal(b.no_db_write, true);
    assert.equal(b.no_raw_write, true);
    assert.equal(b.no_raw_match_data_insert, true);
    assert.equal(b.no_re_acceptance, true);
    assert.equal(b.no_suspension_reversal, true);
    assert.equal(b.raw_write_ready_count, 0);
});

test('ADG44 safety flags are all false', () => {
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

test('ADG44 all probe targets have required metadata', () => {
    const a = build();
    for (const t of a.future_probe_targets) {
        assert.ok(t.target_match_id);
        assert.ok(t.expected_home);
        assert.ok(t.expected_away);
        assert.ok(t.current_status);
        assert.ok(t.why_selected);
        assert.ok(t.expected_probe_source);
        assert.equal(t.max_request_count, 1);
        assert.equal(t.safe_summary_only, true);
        assert.equal(t.raw_write_ready, false);
    }
});
