'use strict'; // lifecycle: test-fixture
const assert = require('node:assert/strict'); const fs = require('node:fs'); const path = require('node:path'); const test = require('node:test');
const RP = path.resolve(__dirname, '../../docs/_manifests/fotmob_ligue1_bounded_l2_detail_fetch_execution.adg32.json');
function r() { return JSON.parse(fs.readFileSync(RP, 'utf8')); }
test('ADG32 3 planned, at least 1 attempted', () => { const a = r(); assert.equal(a.planned, 3); assert.ok(a.attempted >= 1); });
test('ADG32 first sample shows home/away inversion at detail page level', () => {
    const a = r(); const s0 = a.fetch_results[0];
    assert.equal(s0.status, 'validation_failed');
    assert.equal(s0.orientation, 'reversed', 'home/away reversed indicates L1 league API orientation data differs from detail page content');
    assert.ok(s0.observed_home && s0.observed_away);
});
test('ADG32 subsequent samples not attempted due to prior blocker', () => { const a = r(); assert.ok(a.not_attempted >= 1); });
test('ADG32 raw_write_ready=0, no full payload', () => { const a = r(); assert.equal(a.raw_write_ready, 0); assert.equal(a.full_payload_saved, false); assert.equal(a.no_db_write, true); assert.equal(a.no_raw_write, true); assert.equal(a.no_browser, true); assert.equal(a.no_proxy, true); });
