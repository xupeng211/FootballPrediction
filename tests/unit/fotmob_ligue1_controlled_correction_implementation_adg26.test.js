'use strict';
// lifecycle: test-fixture
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const RP = path.resolve(__dirname, '../../docs/_manifests/fotmob_ligue1_controlled_correction_implementation.adg26.json');
function r() { return JSON.parse(fs.readFileSync(RP, 'utf8')); }

test('ADG26 all 32 candidates pass application guard with 0 conflicts', () => { const a = r(); assert.equal(a.validated_candidate_count, 32); assert.equal(a.duplicate_conflict, 0); assert.equal(a.generation_blocked, 0); });
test('ADG26 each application has guard=passed and raw_write_ready=false', () => { const a = r(); for (const t of a.corrected_applications) { assert.equal(t.application_guard_status, 'passed'); assert.equal(t.raw_write_ready, false); } });
test('ADG26 application contract defines mutation boundary', () => { const a = r(); assert.ok(a.application_contract.mutation_boundary.includes('ADG26 does not mutate')); assert.ok(a.application_contract.rollback_audit.rollback.includes('revert')); });
test('ADG26 positive preserved, suspended excluded', () => { const a = r(); assert.equal(a.positive_preserved, 1); assert.ok(a.suspended_exclusion > 0); });
test('ADG26 raw_write_ready=0 and safety', () => { const a = r(); assert.equal(a.raw_write_ready, 0); assert.equal(a.no_network, true); assert.equal(a.no_db_write, true); assert.equal(a.no_raw_write, true); });
