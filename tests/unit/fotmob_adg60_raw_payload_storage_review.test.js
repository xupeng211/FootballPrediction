/**
 * @fileoverview Unit tests for ADG60 raw payload storage review.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const ROOT = join(import.meta.dirname, '..', '..');
const rev = JSON.parse(readFileSync(join(ROOT, 'docs/_manifests/fotmob_adg60_raw_payload_storage_review_manifest.json'), 'utf-8'));
const helperSrc = readFileSync(join(ROOT, 'scripts/ops/fotmob_adg60_raw_payload_storage_review.js'), 'utf-8');

describe('storage review phase and refs', () => {
  it('phase and reviewed PR', () => {
    assert.equal(rev.phase, 'ADG60-RAW-PAYLOAD-STORAGE-REVIEW-NO-DB');
    assert.equal(rev.reviewed_pr, 1418);
  });
});

describe('storage review safety', () => {
  it('all flags false', () => {
    const s = rev.safety;
    assert.equal(s.new_live_fetch_performed, false);
    assert.equal(s.db_write_performed, false);
    assert.equal(s.raw_write_performed, false);
    assert.equal(s.adg60_write_performed, false);
    assert.equal(s.raw_write_ready_marked, false);
  });
});

describe('storage review readiness', () => {
  it('foundation ready, raw_write_ready false, db prohibited', () => {
    assert.equal(rev.readiness_decision.storage_foundation_ready, true);
    assert.equal(rev.readiness_decision.raw_write_ready_remains_false, true);
    assert.equal(rev.readiness_decision.db_write_remains_prohibited, true);
  });
});

describe('storage review recommends parser development', () => {
  it('next phase is PARSER-DEVELOPMENT-NO-DB', () => {
    assert.equal(rev.recommended_next_phase, 'ADG60-RAW-PAYLOAD-PARSER-DEVELOPMENT-NO-DB');
  });
});

describe('storage review helper read-only', () => {
  it('no network/DB', () => {
    assert.ok(!helperSrc.match(/await\s+fetch\s*\(/));
    assert.ok(helperSrc.includes('read-only'));
  });
});
