'use strict'; // lifecycle: test-fixture
const assert = require('node:assert/strict'); const fs = require('node:fs'); const path = require('node:path'); const test = require('node:test');
const RP = path.resolve(__dirname, '../../docs/_manifests/fotmob_ligue1_bounded_l2_detail_fetch_planning.adg31.json');
function r() { return JSON.parse(fs.readFileSync(RP, 'utf8')); }
test('ADG31 3 planned samples, all ready', () => { const a = r(); assert.equal(a.planned, 3); assert.equal(a.ready, 3); assert.equal(a.blocked, 0); });
test('ADG31 each sample has required fields', () => { const a = r(); for (const s of a.planned_samples) { assert.ok(s.target_id); assert.ok(s.corrected_detail); assert.ok(s.expected_home); assert.ok(s.planned_requests === 1); } });
test('ADG31 contract requires explicit authorization', () => { const a = r(); assert.ok(a.future_execution_contract.request.requires_explicit_authorization); assert.ok(a.future_execution_contract.request.stop_on_403); });
test('ADG31 raw_write_ready=0, no live fetch', () => { const a = r(); assert.equal(a.raw_write_ready, 0); assert.equal(a.no_live_fetch, true); assert.equal(a.no_network, true); assert.equal(a.no_db_write, true); });
