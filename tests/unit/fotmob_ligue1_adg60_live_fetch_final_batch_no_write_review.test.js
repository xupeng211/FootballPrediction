/**
 * @fileoverview Unit tests for ADG60 final-batch no-write review.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const ROOT = join(import.meta.dirname, '..', '..');
const fb = JSON.parse(readFileSync(join(ROOT, 'docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_live_fetch_final_batch_no_write.json'), 'utf-8'));
const rev = JSON.parse(readFileSync(join(ROOT, 'docs/_manifests/fotmob_ligue1_adg60_live_fetch_final_batch_no_write_review.json'), 'utf-8'));
const helperSrc = readFileSync(join(ROOT, 'scripts/ops/fotmob_ligue1_adg60_live_fetch_final_batch_no_write_review.js'), 'utf-8');

describe('final-batch review phase and refs', () => {
  it('phase and reviewed PRs', () => {
    assert.equal(rev.phase, 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-FINAL-BATCH-NO-WRITE-REVIEW');
    assert.equal(rev.reviewed_pr, 1416);
    assert.equal(rev.reviewed_authorization_pr, 1415);
    assert.equal(rev.reviewed_prior_review_pr, 1414);
  });
});

describe('final-batch review aggregate', () => {
  it('count=23, success=23, blocked=0', () => {
    assert.equal(rev.aggregate_result.success_count, 23);
    assert.equal(rev.aggregate_result.blocked_count, 0);
    assert.equal(rev.aggregate_result.stopped_early, false);
  });
});

describe('final-batch review cumulative', () => {
  it('tested 32/32, success 32, blocked 0', () => {
    assert.equal(rev.cumulative_result.total_adg60_target_count, 32);
    assert.equal(rev.cumulative_result.tested_target_count, 32);
    assert.equal(rev.cumulative_result.successful_target_count, 32);
    assert.equal(rev.cumulative_result.blocked_target_count, 0);
  });
});

describe('final-batch review per-target checks', () => {
  it('all final batch targets http=200, payload_like=true', () => {
    for (const r of fb.per_target_response_metadata) {
      assert.ok(r.target_index >= 10 && r.target_index <= 32);
      assert.equal(r.http_status, 200);
      assert.equal(r.payload_like, true);
      assert.equal(r.minimal_schema_flags.hasNextDataMarker, true);
      assert.equal(r.minimal_schema_flags.hasPagePropsMarker, true);
      assert.equal(r.body_persisted, false);
    }
  });
});

describe('final-batch review safety', () => {
  it('all safety flags false', () => {
    const s = rev.safety;
    assert.equal(s.new_live_fetch_performed, false);
    assert.equal(s.new_network_fetch_performed, false);
    assert.equal(s.new_browser_automation_performed, false);
    assert.equal(s.payload_saved, false);
    assert.equal(s.db_write_performed, false);
    assert.equal(s.raw_write_performed, false);
    assert.equal(s.raw_match_data_insert_performed, false);
    assert.equal(s.adg60_write_performed, false);
    assert.equal(s.raw_write_ready_marked, false);
  });
});

describe('final-batch review reads raw_write_ready false', () => {
  it('raw_write_ready remains false', () => {
    assert.equal(rev.readiness_decision.raw_write_ready_remains_false, true);
    assert.equal(rev.readiness_decision.db_write_remains_prohibited, true);
  });
});

describe('final-batch review recommends raw payload storage auth', () => {
  it('next phase is RAW-PAYLOAD-STORAGE-AUTHORIZATION', () => {
    assert.equal(rev.recommended_next_phase, 'ADG60-RAW-PAYLOAD-STORAGE-AUTHORIZATION');
  });
});

describe('final-batch review helper read-only', () => {
  it('no network/DB/browser', () => {
    assert.ok(!helperSrc.match(/await\s+fetch\s*\(/), 'no fetch');
    assert.ok(!helperSrc.match(/import\s+.*playwright/i), 'no playwright');
    assert.ok(helperSrc.includes('read-only'), 'read-only');
  });
});
