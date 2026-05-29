'use strict'; // lifecycle: test-fixture
const assert = require('node:assert/strict'); const fs = require('node:fs'); const path = require('node:path'); const test = require('node:test');
const RP = path.resolve(__dirname, '../../docs/_manifests/fotmob_ligue1_l1_l2_orientation_reconciliation.adg33.json');
function r() { return JSON.parse(fs.readFileSync(RP, 'utf8')); }
test('ADG33 root cause identified: enriched URL contains wrong-leg slug', () => { const a = r(); assert.equal(a.confirmed_root_cause, 'enriched_source_page_url_contains_wrong_leg_slug'); assert.equal(a.l1_orientation_correct, true); assert.equal(a.l2_url_construction_wrong, true); });
test('ADG33 32 targets checked, slug mismatch found', () => { const a = r(); assert.equal(a.total, 32); assert.ok(a.affected_slug_mismatch > 0); });
test('ADG33 ADG21-ADG27 conclusion remains valid', () => { const a = r(); assert.equal(a.l1_orientation_correct, true); });
test('ADG33 raw_write_ready=0', () => { const a = r(); assert.equal(a.raw_write_ready, 0); assert.equal(a.no_live_fetch, true); assert.equal(a.no_db_write, true); });
