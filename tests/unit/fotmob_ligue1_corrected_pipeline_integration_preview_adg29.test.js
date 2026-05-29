'use strict'; // lifecycle: test-fixture
const assert = require('node:assert/strict'); const fs = require('node:fs'); const path = require('node:path'); const test = require('node:test');
const RP = path.resolve(__dirname, '../../docs/_manifests/fotmob_ligue1_corrected_pipeline_integration_preview.adg29.json');
function r() { return JSON.parse(fs.readFileSync(RP, 'utf8')); }
test('ADG29 32/32 source inventory ready, 32/32 candidates ready', () => { const a = r(); assert.equal(a.si_ready, 32); assert.equal(a.cand_ready, 32); });
test('ADG29 32/32 L2 identity ready, 0 missing', () => { const a = r(); assert.equal(a.l2_ready, 32); assert.equal(a.l2_missing, 0); });
test('ADG29 raw_write_ready=0', () => { const a = r(); assert.equal(a.raw_write_ready, 0); assert.equal(a.no_db_write, true); assert.equal(a.no_raw_write, true); });
