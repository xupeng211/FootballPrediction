'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const RP = path.resolve(__dirname, '../../docs/_manifests/fotmob_ligue1_oriented_fixture_selection_regression.adg18.json');
function r() { return JSON.parse(fs.readFileSync(RP, 'utf8')); }

test('ADG18 positive control oriented_match_selected', () => { const a = r(); const pc = a.results.find(t => t.external_id === '4813735'); assert.ok(pc); assert.equal(pc.classification, 'oriented_match_selected'); assert.equal(pc.status, 'passed'); assert.equal(pc.rw_ready, false); });
test('ADG18 known reverse samples rejected', () => { const a = r(); const ids = ['4830458','4830459','4830460','4830462','4830464','4830467','4830468','4830469','4830470','4830471'];
    for (const id of ids) { const t = a.results.find(r => r.external_id === id); if (t && t.classification !== 'unknown_insufficient_evidence') assert.ok(t.classification.includes('rejected'), `${id} must be rejected, got ${t.classification}`); } });
test('ADG18 suspended targets blocked', () => { const a = r(); const s = a.results.filter(t => t.is_suspended); assert.equal(s.length, 8); for (const t of s) assert.equal(t.classification, 'suspended_still_blocked'); });
test('ADG18 raw_write_ready=0', () => { const a = r(); assert.equal(a.raw_write_ready, 0); assert.equal(a.re_acceptance, 0); for (const t of a.results) assert.equal(t.rw_ready, false); });
test('ADG18 safety flags', () => { const a = r(); assert.equal(a.no_db_write, true); assert.equal(a.no_raw_write, true); assert.equal(a.no_mutation, true); assert.equal(a.full_payload_saved, false); });
