'use strict';
// lifecycle: test-fixture
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const RP = path.resolve(__dirname, '../../docs/_manifests/fotmob_ligue1_corrected_generation_preview.adg25.json');
function r() { return JSON.parse(fs.readFileSync(RP, 'utf8')); }

test('ADG25 all 32 validated candidates proposed for corrected generation', () => { const a = r(); assert.equal(a.validated_count, 32); assert.equal(a.proposed_source_inventory, 32); assert.equal(a.proposed_candidate, 32); });
test('ADG25 positive control preserved, suspended blocked', () => { const a = r(); assert.equal(a.positive_preserved, 1); assert.ok(a.suspended_blocked >= 1); });
test('ADG25 raw_write_ready=0 and safety', () => { const a = r(); assert.equal(a.raw_write_ready, 0); assert.equal(a.no_network, true); assert.equal(a.no_db_write, true); assert.equal(a.no_raw_write, true); assert.equal(a.no_mutation, true); });
test('ADG25 all preview entries have raw_write_ready=false', () => { const a = r(); for (const t of a.generation_results) assert.equal(t.raw_write_ready, false); });
test('ADG25 recommends ADG26 planning, not raw write', () => { const a = r(); assert.ok(a.recommended_next_step.includes('do not raw write') || a.recommended_next_step.includes('not raw write')); });
