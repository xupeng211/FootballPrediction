'use strict'; // lifecycle: test-fixture
const assert = require('node:assert/strict'); const fs = require('node:fs'); const path = require('node:path'); const test = require('node:test');
const RP = path.resolve(__dirname, '../../docs/_manifests/fotmob_ligue1_l2_detail_fetch_readiness.adg30.json');
function r() { return JSON.parse(fs.readFileSync(RP, 'utf8')); }
test('ADG30 32/32 L2 ready, 0 blocked', () => { const a = r(); assert.equal(a.l2_ready, 32); assert.equal(a.l2_blocked, 0); });
test('ADG30 contracts defined', () => { const a = r(); assert.ok(a.input_contract); assert.ok(a.request_contract); assert.ok(a.response_contract); assert.ok(a.output_contract); assert.ok(typeof a.request_contract.bounded === 'string'); });
test('ADG30 raw_write_ready=0', () => { const a = r(); assert.equal(a.raw_write_ready, 0); assert.equal(a.no_live_fetch, true); assert.equal(a.no_db_write, true); assert.equal(a.no_raw_write, true); });
