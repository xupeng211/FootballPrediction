'use strict'; // lifecycle: test-fixture
const assert = require('node:assert/strict');
const test = require('node:test');
const { build } = require('../../scripts/ops/fotmob_ligue1_ssr_pageprops_discovery_gate_adg46');

test('ADG46 gate selects exactly 2 future SSR probe targets', () => {
    const a = build();
    assert.equal(a.future_probe_target_count, 2);
    assert.equal(a.future_ssr_probe_targets.length, 2);
    assert.equal(a.max_targets, 2);
    assert.equal(a.max_requests_per_target, 1);
});

test('ADG46 gate chooses fotmob_ssr_pageprops as strategy', () => {
    const a = build();
    assert.equal(a.chosen_strategy, 'fotmob_ssr_pageprops');
    assert.ok(Array.isArray(a.chosen_reason));
    assert.ok(a.chosen_reason.length >= 4);
});

test('ADG46 gate requires explicit user authorization', () => {
    const a = build();
    assert.equal(a.requires_explicit_user_authorization, true);
    assert.equal(a.authorization_gate_prepared, true);
    assert.equal(a.ssr_probe_not_executed, true);
    assert.ok(a.authorization_scope.includes('ADG46'));
    assert.ok(a.authorization_scope.includes('does NOT authorize'));
});

test('ADG46 probe boundary enforces all SSR safety rules', () => {
    const a = build();
    const b = a.probe_boundary;
    assert.equal(b.public_match_page_only, true);
    assert.equal(b.no_browser_automation, true);
    assert.equal(b.no_proxy, true);
    assert.equal(b.no_bypass, true);
    assert.equal(b.stop_on_403_or_block, true);
    assert.equal(b.stop_on_captcha, true);
    assert.equal(b.in_memory_parse_only, true);
    assert.equal(b.no_full_html_saved, true);
    assert.equal(b.no_full_pageprops_saved, true);
    assert.equal(b.no_full_next_data_saved, true);
    assert.equal(b.no_db_write, true);
    assert.equal(b.no_raw_write, true);
    assert.equal(b.raw_write_ready_count, 0);
});

test('ADG46 gate defines allowed and forbidden fields', () => {
    const a = build();
    assert.ok(Array.isArray(a.allowed_safe_summary_fields));
    assert.ok(a.allowed_safe_summary_fields.length >= 15);
    assert.ok(Array.isArray(a.forbidden_fields_in_save));
    const forbidden = a.forbidden_fields_in_save;
    assert.ok(forbidden.includes('full_html'));
    assert.ok(forbidden.includes('full_pageprops'));
    assert.ok(forbidden.includes('full_next_data'));
    assert.ok(forbidden.includes('full_raw_data'));
});

test('ADG46 safety flags are all false', () => {
    const a = build();
    const s = a.safety;
    assert.equal(s.live_fetch_performed, false);
    assert.equal(s.network_request_performed, false);
    assert.equal(s.db_write_performed, false);
    assert.equal(s.raw_write_execution_performed, false);
    assert.equal(s.full_payload_saved, false);
    assert.equal(s.full_html_saved, false);
    assert.equal(s.full_pageprops_saved, false);
    assert.equal(s.browser_bypass_performed, false);
});

test('ADG46 both targets have complete metadata', () => {
    const a = build();
    for (const t of a.future_ssr_probe_targets) {
        assert.ok(t.target_match_id);
        assert.ok(t.expected_home);
        assert.ok(t.expected_away);
        assert.ok(t.current_status);
        assert.ok(t.why_selected);
        assert.equal(t.max_request_count, 1);
        assert.equal(t.safe_summary_only, true);
        assert.equal(t.full_payload_saved, false);
        assert.equal(t.raw_write_ready, false);
    }
});
