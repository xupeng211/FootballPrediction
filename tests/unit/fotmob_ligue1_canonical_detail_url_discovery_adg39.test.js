'use strict'; // lifecycle: test-fixture
const assert = require('node:assert/strict'); const fs = require('node:fs'); const path = require('node:path'); const test = require('node:test');
const RP = path.resolve(__dirname, '../../docs/_manifests/fotmob_ligue1_canonical_detail_url_discovery.adg39.json');
function r() { return JSON.parse(fs.readFileSync(RP, 'utf8')); }

test('ADG39 L1 API already provides canonical URLs with route codes', () => { const a = r(); assert.ok(a.canonical_detail_url_found > 0); assert.ok(a.route_code_found > 0); assert.equal(a.route_code_from_l1_api, true); });
test('ADG39 L2 route code guessing blocked', () => { const a = r(); assert.equal(a.l2_route_code_guessing_blocked, true); });
test('ADG39 handoff contract defined', () => { const a = r(); assert.ok(a.handoff_contract.l1_must_deliver.includes('canonical_detail_url')); assert.ok(a.handoff_contract.l2_must_not.length >= 2); });
test('ADG39 alternate route code discovery required', () => { const a = r(); assert.equal(a.alternate_route_code_discovery_required, true); assert.equal(a.canonical_url_diagnostic_probe_required, true); });
test('ADG39 raw_write_ready=0', () => { const a = r(); assert.equal(a.raw_write_ready, 0); assert.equal(a.no_network, true); assert.equal(a.no_db_write, true); });
