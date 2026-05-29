'use strict';
// lifecycle: test-fixture
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const RP = path.resolve(__dirname, '../../docs/_manifests/fotmob_ligue1_corrected_artifacts_regression.adg28.json');
function r() { return JSON.parse(fs.readFileSync(RP, 'utf8')); }

test('ADG28 32/32 source records validated, 0 missing, 0 guard failed', () => { const a = r(); assert.equal(a.source_count, 32); assert.equal(a.validated, 32); assert.equal(a.missing, 0); assert.equal(a.guard_failed, 0); });
test('ADG28 audit consistent', () => { const a = r(); assert.equal(a.audit_consistent, true); });
test('ADG28 raw_write_ready=0 and safety', () => { const a = r(); assert.equal(a.raw_write_ready, 0); assert.equal(a.no_db_write, true); assert.equal(a.no_raw_write, true); assert.equal(a.no_network, true); });
