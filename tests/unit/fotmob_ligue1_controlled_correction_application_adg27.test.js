'use strict';
// lifecycle: test-fixture
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
function r(p) { return JSON.parse(fs.readFileSync(path.resolve(__dirname, '../../docs/_manifests/', p), 'utf8')); }

test('ADG27 corrected source inventory has 32 records, all guard=passed', () => { const a = r('fotmob_ligue1_corrected_source_inventory.adg27.json'); assert.equal(a.corrected_source_inventory_records.length, 32); for (const t of a.corrected_source_inventory_records) { assert.equal(t.guard_status, 'passed'); assert.equal(t.raw_write_ready, false); assert.equal(t.source_inventory_write_ready, false); } });
test('ADG27 corrected candidates has 32 records', () => { const a = r('fotmob_ligue1_corrected_candidates.adg27.json'); assert.equal(a.corrected_candidate_records.length, 32); for (const t of a.corrected_candidate_records) { assert.equal(t.raw_write_ready, false); assert.equal(t.candidate_write_ready, false); } });
test('ADG27 audit has 0 failures, superseded tracked', () => { const a = r('fotmob_ligue1_controlled_correction_audit.adg27.json'); assert.equal(a.failures, 0); assert.equal(a.positive_preserved, true); assert.ok(a.suspended_excluded > 0); assert.ok(a.rollback_plan.includes('revert')); });
test('ADG27 all artifacts have db_write_performed=false', () => { for (const fp of ['fotmob_ligue1_corrected_source_inventory.adg27.json', 'fotmob_ligue1_corrected_candidates.adg27.json', 'fotmob_ligue1_controlled_correction_audit.adg27.json']) { assert.equal(r(fp).db_write_performed, false); } });
