'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const RP = path.resolve(__dirname, '../../docs/_manifests/fotmob_ligue1_corrected_source_inventory_generation.adg20.json');
function r() { return JSON.parse(fs.readFileSync(RP, 'utf8')); }

test('ADG20 proposed_corrected=0 — source-controlled data insufficient', () => { const a = r(); assert.equal(a.proposed_corrected, 0, 'cannot fabricate corrected records from current source inventory'); });
test('ADG20 rejected_current_reverse=10 from observed evidence', () => { const a = r(); assert.equal(a.rejected_current_reverse, 10); });
test('ADG20 requires_external_discovery=32', () => { const a = r(); assert.equal(a.requires_external_discovery, 32); });
test('ADG20 suspended=8, positive_control=1 preserved', () => { const a = r(); assert.equal(a.suspended_blocked, 8); assert.equal(a.positive_control, 1); });
test('ADG20 raw_write_ready=0 and safety', () => { const a = r(); assert.equal(a.raw_write_ready, 0); assert.equal(a.no_db_write, true); assert.equal(a.no_raw_write, true); assert.equal(a.source_inventory_mutation_performed, false); assert.equal(a.candidate_mutation_performed, false); });
test('ADG20 recommends external discovery, not raw write', () => { const a = r(); const s = a.recommended_next_step.toLowerCase(); assert.ok(s.includes('external') || s.includes('discovery')); assert.ok(s.includes('do not raw write') || s.includes('not raw write')); });
