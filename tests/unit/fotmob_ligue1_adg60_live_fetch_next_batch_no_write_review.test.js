/**
 * @fileoverview Unit tests for ADG60 next-batch live fetch no-write review.
 *
 * lifecycle: phase-artifact
 * phase: ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-NEXT-BATCH-NO-WRITE-REVIEW
 */

import { describe, it } from 'node:test';
import assert from 'node:assert';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const ROOT = join(import.meta.dirname, '..', '..');
const m = JSON.parse(readFileSync(join(ROOT, 'docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_live_fetch_next_batch_no_write.json'), 'utf-8'));
const rev = JSON.parse(readFileSync(join(ROOT, 'docs/_manifests/fotmob_ligue1_adg60_live_fetch_next_batch_no_write_review.json'), 'utf-8'));
const helperSrc = readFileSync(join(ROOT, 'scripts/ops/fotmob_ligue1_adg60_live_fetch_next_batch_no_write_review.js'), 'utf-8');

describe('next-batch review correct phase and refs', () => {
  it('phase and reviewed PRs', () => {
    assert.equal(rev.phase, 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-NEXT-BATCH-NO-WRITE-REVIEW');
    assert.equal(rev.reviewed_pr, 1413);
    assert.equal(rev.reviewed_authorization_pr, 1412);
    assert.equal(rev.reviewed_previous_review_pr, 1411);
  });
});

describe('next-batch review aggregate result', () => {
  it('count=5, success=5, blocked=0, stopped=false', () => {
    const a = rev.aggregate_result;
    assert.equal(a.selected_target_count, 5);
    assert.equal(a.request_count_total, 5);
    assert.equal(a.success_count, 5);
    assert.equal(a.blocked_count, 0);
    assert.equal(a.stopped_early, false);
  });
});

describe('next-batch review per-target all 200', () => {
  it('all http_status=200, payload_like=true, nd=true, pp=true', () => {
    for (const r of rev.reviewed_fetch_results) {
      assert.equal(r.http_status, 200, `t${r.target_index} status`);
      assert.equal(r.payload_like, true, `t${r.target_index} pl`);
      assert.equal(r.hasNextDataMarker, true, `t${r.target_index} nd`);
      assert.equal(r.hasPagePropsMarker, true, `t${r.target_index} pp`);
    }
  });
});

describe('next-batch review no body persisted', () => {
  it('all body_persisted=false', () => {
    for (const r of rev.reviewed_fetch_results) {
      assert.equal(r.body_persisted, false);
      assert.equal(r.body_logged, false);
      assert.equal(r.body_committed, false);
    }
  });
});

describe('next-batch review cumulative evidence', () => {
  it('tested 9/32, successful 9', () => {
    assert.equal(rev.cumulative_result.tested_target_count, 9);
    assert.equal(rev.cumulative_result.total_adg60_target_count, 32);
    assert.equal(rev.cumulative_result.successful_target_count, 9);
    assert.equal(rev.cumulative_result.blocked_target_count, 0);
  });
});

describe('next-batch review safety flags', () => {
  it('all false', () => {
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

describe('next-batch review ready decision', () => {
  it('raw_write_ready=false, recommended final-batch auth', () => {
    assert.equal(rev.readiness_decision.raw_write_ready_remains_false, true);
    assert.equal(rev.readiness_decision.db_write_remains_prohibited, true);
    assert.equal(rev.recommended_next_phase, 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-FINAL-BATCH-NO-WRITE-AUTHORIZATION');
  });
});

describe('next-batch review helper is read-only', () => {
  it('no network/DB/browser', () => {
    assert.ok(!helperSrc.match(/await\s+fetch\s*\(/), 'no live fetch');
    assert.ok(!helperSrc.match(/import\s+.*playwright/i), 'no playwright');
    assert.ok(!helperSrc.match(/import\s+.*chromium/i), 'no chromium');
    assert.ok(helperSrc.includes('read-only'), 'declared read-only');
  });
});
