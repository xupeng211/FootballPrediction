'use strict'; // lifecycle: test-fixture
const assert = require('node:assert/strict');
const test = require('node:test');
const { build } = require('../../scripts/ops/fotmob_ligue1_correct_orientation_route_hash_gate_adg48');

test('ADG48 selects exactly 3 future targets', () => { const a = build(); assert.equal(a.future_probe_target_count, 3); assert.equal(a.future_ssr_probe_targets.length, 3); assert.equal(a.max_targets, 3); });
test('ADG48 includes all 3 target types', () => { const a = build(); const s = a.future_ssr_probe_targets.map(t => t.current_status); assert.ok(s.includes('known_route_hash_pair_confirmed_reverse')); assert.ok(s.includes('route_hash_pair_unverified_needs_detail_verification')); assert.ok(s.includes('canonical_url_missing_needs_l1_discovery')); });
test('ADG48 requires explicit user authorization', () => { const a = build(); assert.equal(a.requires_explicit_user_authorization, true); assert.equal(a.authorization_gate_prepared, true); assert.equal(a.probe_not_executed, true); });
test('ADG48 boundary enforces all stop rules', () => { const a = build(); const b = a.probe_boundary; assert.equal(b.stop_on_403_or_block, true); assert.equal(b.stop_on_captcha, true); assert.equal(b.no_full_html_saved, true); assert.equal(b.no_full_next_data_saved, true); assert.equal(b.no_db_write, true); assert.equal(b.no_raw_write, true); assert.equal(b.raw_write_ready_count, 0); });
test('ADG48 confirms known counts', () => { const a = build(); assert.equal(a.confirmed_reverse_count, 1); assert.equal(a.remaining_unverified_count, 4); assert.equal(a.canonical_url_missing_count, 27); });
test('ADG48 safety all false', () => { const a = build(); const s = a.safety; assert.equal(s.live_fetch_performed, false); assert.equal(s.network_request_performed, false); assert.equal(s.db_write_performed, false); assert.equal(s.raw_write_execution_performed, false); assert.equal(s.full_payload_saved, false); });
test('ADG48 raw_write_ready_count=0', () => { const a = build(); assert.equal(a.raw_write_ready_count, 0); assert.ok(a.recommended_next_step.includes('raw write')); });
