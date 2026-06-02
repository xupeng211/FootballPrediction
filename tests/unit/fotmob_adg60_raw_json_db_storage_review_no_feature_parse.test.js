/**
 * @fileoverview Unit tests for ADG60 raw JSON DB storage review.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const ROOT = join(import.meta.dirname, '..', '..');
const mf = JSON.parse(readFileSync(join(ROOT, 'docs/_manifests/fotmob_raw_json_db_storage_adg60_manifest.json'), 'utf-8'));
const rev = JSON.parse(readFileSync(join(ROOT, 'docs/_manifests/fotmob_raw_json_db_storage_review_adg60_manifest.json'), 'utf-8'));
const helperSrc = readFileSync(join(ROOT, 'scripts/ops/fotmob_adg60_raw_json_db_storage_review_no_feature_parse.js'), 'utf-8');

describe('review phase and refs', () => {
  it('phase and reviewed PR', () => {
    assert.equal(rev.phase, 'ADG60-RAW-JSON-DB-STORAGE-REVIEW-NO-FEATURE-PARSE');
    assert.equal(rev.reviewed_pr, 1420);
  });
});

describe('review DB facts', () => {
  it('32 rows, 32 distinct, 32 json present', () => {
    assert.equal(rev.db_row_count, 32);
    assert.equal(rev.distinct_match_id_count, 32);
    assert.equal(rev.json_present_count, 32);
  });
});

describe('review idempotency', () => {
  it('inserted=32 first, existing=32 rerun', () => {
    assert.equal(rev.inserted_count, 32);
    assert.equal(rev.existing_count, 32);
    assert.equal(rev.idempotency_result, 'pass');
  });
});

describe('review migration safety', () => {
  it('no DROP/TRUNCATE/DELETE, has JSONB and GIN', () => {
    assert.equal(rev.migration_review.verdict, 'pass');
  });
});

describe('review storage safety', () => {
  it('all safe: raw Layer only, no feature parse', () => {
    assert.equal(rev.raw_json_storage_review.verdict, 'pass');
    assert.equal(rev.safety_review.verdict, 'pass');
    const s = rev.safety;
    assert.equal(s.feature_parse_performed, false);
    assert.equal(s.raw_match_data_insert_performed, false);
    assert.equal(s.l3_features_write_performed, false);
    assert.equal(s.predictions_write_performed, false);
    assert.equal(s.raw_write_ready_marked, false);
    assert.equal(s.new_db_write_performed, false);
  });
});

describe('review recommends collection design', () => {
  it('next phase is LONG-RUN-COLLECTION-DESIGN', () => {
    assert.equal(rev.recommended_next_phase, 'FOTMOB-RAW-JSON-LONG-RUN-COLLECTION-DESIGN');
  });
});

describe('review helper read-only', () => {
  it('no network/DB write', () => {
    assert.ok(!helperSrc.match(/await\s+fetch\s*\(/));
    assert.ok(helperSrc.includes('read-only'));
  });
});
