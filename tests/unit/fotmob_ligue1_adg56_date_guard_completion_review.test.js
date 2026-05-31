'use strict'; const assert = require('node:assert/strict'); const test = require('node:test'); const { build } = require('../../scripts/ops/fotmob_ligue1_adg56_date_guard_completion_review');
test('ADG56 all 32 dates completed, 0 remaining unknown', () => { const a = build(); assert.equal(a.total_targets, 32); assert.equal(a.date_pass_after_adg56, 32); assert.equal(a.remaining_date_unknown, 0); });
test('ADG56 all 32 eligible, 0 blocked', () => { const a = build(); assert.equal(a.eligibility_ready_no_write, 32); assert.equal(a.eligibility_date_unknown, 0); assert.equal(a.eligibility_blocked, 0); });
test('ADG56 all 32 require re-acceptance, none executed', () => { const a = build(); assert.equal(a.suspended_requires_authorization, 32); assert.equal(a.re_acceptance_performed, false); assert.equal(a.suspension_reversal_performed, false); });
test('ADG56 no network, no DB/raw write', () => { const a = build(); const s = a.safety; assert.equal(s.live_fetch_performed, false); assert.equal(s.db_write_performed, false); assert.equal(s.raw_write_execution_performed, false); });
test('ADG56 raw_write_ready_count=0', () => { const a = build(); assert.equal(a.raw_write_ready_count, 0); });
