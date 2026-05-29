'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const RP = path.resolve(__dirname, '../../docs/_manifests/fotmob_ligue1_corrected_source_inventory_preview.adg19.json');
function r() { return JSON.parse(fs.readFileSync(RP, 'utf8')); }

test('ADG19 positive control accepted_validated_no_write', () => { const a = r(); const pc = a.preview_results.find(t => t.external_id === '4813735'); assert.ok(pc); assert.equal(pc.classification, 'accepted_validated_no_write'); assert.equal(pc.raw_write_ready, false); });
test('ADG19 rejected_reverse_fixture_mapping=10', () => { const a = r(); assert.equal(a.rejected_reverse_fixture_mapping, 10); for (const t of a.preview_results.filter(t => t.classification === 'rejected_reverse_fixture_mapping')) { assert.equal(t.correction_needed, true); assert.equal(t.raw_write_ready, false); } });
test('ADG19 requires_new_record for majority', () => { const a = r(); assert.ok(a.requires_new_record > 30, 'majority should need new records'); });
test('ADG19 suspended still blocked', () => { const a = r(); assert.equal(a.suspended_still_blocked, 8); });
test('ADG19 raw_write_ready=0 and safety flags', () => { const a = r(); assert.equal(a.raw_write_ready, 0); assert.equal(a.re_acceptance_candidate, 0); assert.equal(a.no_db_write, true); assert.equal(a.no_raw_write, true); assert.equal(a.source_inventory_mutation_performed, false); assert.equal(a.candidate_mutation_performed, false); });
