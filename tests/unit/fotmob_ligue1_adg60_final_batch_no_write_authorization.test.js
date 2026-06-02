/**
 * @fileoverview Unit tests for ADG60 final-batch no-write authorization.
 *
 * lifecycle: phase-artifact
 * phase: ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-FINAL-BATCH-NO-WRITE-AUTHORIZATION
 */

import { describe, it } from 'node:test';
import assert from 'node:assert';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const ROOT = join(import.meta.dirname, '..', '..');
const m = JSON.parse(readFileSync(join(ROOT, 'docs/_manifests/fotmob_ligue1_adg60_final_batch_no_write_authorization.json'), 'utf-8'));
const helperSrc = readFileSync(join(ROOT, 'scripts/ops/fotmob_ligue1_adg60_final_batch_no_write_authorization.js'), 'utf-8');

describe('final-batch auth correct phase and review refs', () => {
  it('phase and reviewed PRs', () => {
    assert.equal(m.phase, 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-FINAL-BATCH-NO-WRITE-AUTHORIZATION');
    assert.equal(m.reviewed_next_batch_review_pr, 1414);
    assert.equal(m.reviewed_next_batch_fetch_pr, 1413);
    assert.equal(m.reviewed_next_batch_authorization_pr, 1412);
  });
});

describe('final-batch auth correct totals', () => {
  it('total=32, tested=9, remaining=23', () => {
    assert.equal(m.total_adg60_target_count, 32);
    assert.equal(m.already_tested_target_count, 9);
    assert.equal(m.remaining_target_count, 23);
    assert.deepStrictEqual(m.already_tested_target_indices, [1,2,3,4,5,6,7,8,9]);
  });
});

describe('final-batch auth candidate indices correct', () => {
  it('indices [10..32]', () => {
    const expected = Array.from({ length: 23 }, (_, i) => i + 10);
    assert.deepStrictEqual(m.candidate_target_indices, expected);
  });
});

describe('final-batch auth all 23 candidates have valid identity', () => {
  it('match_id, home, away, date, competition, hash, route all present', () => {
    assert.equal(m.candidates.length, 23);
    for (const c of m.candidates) {
      assert.ok(c.target_index >= 10 && c.target_index <= 32);
      assert.ok(typeof c.target_match_id === 'string' && c.target_match_id.length > 0);
      assert.ok(typeof c.expected_home === 'string' && c.expected_home.length > 0);
      assert.ok(typeof c.expected_away === 'string' && c.expected_away.length > 0);
      assert.ok(typeof c.expected_date === 'string');
      assert.equal(c.competition, 'Ligue 1');
      assert.ok(typeof c.corrected_hash_id === 'string');
      assert.ok(typeof c.corrected_route_hash_pair === 'string' && c.corrected_route_hash_pair.includes('#'));
    }
  });
});

describe('final-batch auth sample identities correct', () => {
  it('targets 10, 20, 32 have expected identities', () => {
    const t10 = m.candidates.find((c) => c.target_index === 10);
    assert.ok(t10);
    const t20 = m.candidates.find((c) => c.target_index === 20);
    assert.ok(t20);
    const t32 = m.candidates.find((c) => c.target_index === 32);
    assert.ok(t32);
    assert.equal(t32.expected_home, 'Strasbourg');
    assert.equal(t32.expected_away, 'Marseille');
  });
});

describe('final-batch auth all safety flags false', () => {
  it('all fetch/write/persistence flags false', () => {
    const s = m.safety;
    assert.equal(s.live_fetch_performed, false);
    assert.equal(s.network_fetch_performed, false);
    assert.equal(s.browser_automation_performed, false);
    assert.equal(s.payload_saved, false);
    assert.equal(s.response_body_saved, false);
    assert.equal(s.db_write_performed, false);
    assert.equal(s.raw_write_performed, false);
    assert.equal(s.raw_match_data_insert_performed, false);
    assert.equal(s.schema_migration_performed, false);
    assert.equal(s.adg60_write_performed, false);
    assert.equal(s.raw_write_ready_marked, false);
  });
});

describe('final-batch auth write policies blocked', () => {
  it('all write policies blocked', () => {
    const w = m.write_policy;
    assert.equal(w.db_write_prohibited, true);
    assert.equal(w.raw_write_prohibited, true);
    assert.equal(w.raw_match_data_insert_prohibited, true);
    assert.equal(w.schema_migration_prohibited, true);
    assert.equal(w.adg60_write_blocked, true);
    assert.equal(w.raw_write_ready_remains_false, true);
  });
});

describe('final-batch auth review policy correct', () => {
  it('review required, no auto raw write after final batch', () => {
    const r = m.review_policy;
    assert.equal(r.review_required_after_final_batch, true);
    assert.equal(r.no_automatic_raw_write_after_final_batch, true);
    assert.equal(r.no_automatic_db_write_after_final_batch, true);
    assert.equal(r.no_automatic_adg60_write_after_final_batch, true);
    assert.equal(r.all_32_metadata_success_does_not_by_itself_mean_raw_write_ready_true, true);
  });
});

describe('final-batch auth recommends final-batch execution', () => {
  it('recommended_next is FINAL-BATCH execution', () => {
    assert.equal(m.recommended_next_phase, 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-FINAL-BATCH-NO-WRITE');
  });
});

describe('final-batch auth helper is read-only', () => {
  it('no network/DB/browser in helper', () => {
    assert.ok(!helperSrc.match(/await\s+fetch\s*\(/), 'no live fetch');
    assert.ok(!helperSrc.match(/import\s+.*playwright/i), 'no playwright');
    assert.ok(!helperSrc.match(/import\s+.*chromium/i), 'no chromium');
    assert.ok(helperSrc.includes('read-only'), 'declared read-only');
  });
});
