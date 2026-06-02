/**
 * @fileoverview Unit tests for ADG60 next-batch no-write authorization.
 *
 * lifecycle: phase-artifact
 * phase: ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-NEXT-BATCH-NO-WRITE-AUTHORIZATION
 */

import { describe, it } from 'node:test';
import assert from 'node:assert';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const ROOT = join(import.meta.dirname, '..', '..');

function readJson(filename) {
  return JSON.parse(readFileSync(join(ROOT, 'docs/_manifests', filename), 'utf-8'));
}

// ===========================================================================

describe('ADG60 next-batch authorization has correct phase and review refs', () => {
  it('phase is AUTHORIZATION, reviewed refs correct', () => {
    const m = readJson('fotmob_ligue1_adg60_next_batch_no_write_authorization.json');
    assert.equal(m.phase, 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-NEXT-BATCH-NO-WRITE-AUTHORIZATION');
    assert.equal(m.reviewed_three_target_review_pr, 1411);
    assert.equal(m.reviewed_three_target_fetch_pr, 1410);
    assert.equal(m.reviewed_three_target_authorization_pr, 1409);
  });
});

// ===========================================================================

describe('ADG60 next-batch authorization has max 5 targets', () => {
  it('max_future_target_count=5, candidate_indices=[5,6,7,8,9]', () => {
    const m = readJson('fotmob_ligue1_adg60_next_batch_no_write_authorization.json');
    assert.equal(m.max_future_target_count, 5);
    assert.deepStrictEqual(m.candidate_target_indices, [5, 6, 7, 8, 9]);
  });
});

// ===========================================================================

describe('ADG60 next-batch authorization candidates have valid identities', () => {
  it('all 5 candidates have match_id, home, away, date, route', () => {
    const m = readJson('fotmob_ligue1_adg60_next_batch_no_write_authorization.json');
    assert.equal(m.candidates.length, 5);
    const expected = [
      { idx: 5, home: 'Lens', away: 'Brest', matchId: '53_20252026_4830478', route: '2f5cib#4830478' },
      { idx: 6, home: 'Lorient', away: 'Lille', matchId: '53_20252026_4830479', route: '2he6a1#4830479' },
      { idx: 7, home: 'Angers', away: 'Rennes', matchId: '53_20252026_4830476', route: '2o5ty5#4830476' },
      { idx: 8, home: 'Le Havre', away: 'Nice', matchId: '53_20252026_4830477', route: '363pdo#4830477' },
      { idx: 9, home: 'Lyon', away: 'Marseille', matchId: '53_20252026_4830480', route: '2s51f2#4830480' },
    ];
    for (let i = 0; i < 5; i++) {
      const c = m.candidates[i];
      const e = expected[i];
      assert.equal(c.target_index, e.idx);
      assert.equal(c.expected_home, e.home);
      assert.equal(c.expected_away, e.away);
      assert.equal(c.target_match_id, e.matchId);
      assert.equal(c.corrected_route_hash_pair, e.route);
      assert.equal(c.corrected_hash_id, c.corrected_route_hash_pair.split('#')[1]);
    }
  });
});

// ===========================================================================

describe('ADG60 next-batch authorization all safety flags false', () => {
  it('all fetch/write/persistence flags false', () => {
    const m = readJson('fotmob_ligue1_adg60_next_batch_no_write_authorization.json');
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

// ===========================================================================

describe('ADG60 next-batch authorization all write policies blocked', () => {
  it('all write policies blocked', () => {
    const m = readJson('fotmob_ligue1_adg60_next_batch_no_write_authorization.json');
    const w = m.write_policy;
    assert.equal(w.db_write_prohibited, true);
    assert.equal(w.raw_write_prohibited, true);
    assert.equal(w.raw_match_data_insert_prohibited, true);
    assert.equal(w.schema_migration_prohibited, true);
    assert.equal(w.adg60_write_blocked, true);
    assert.equal(w.raw_write_ready_remains_false, true);
  });
});

// ===========================================================================

describe('ADG60 next-batch authorization browser policy prohibited', () => {
  it('all browser policies prohibited', () => {
    const m = readJson('fotmob_ligue1_adg60_next_batch_no_write_authorization.json');
    const b = m.browser_policy;
    assert.equal(b.browser_automation_prohibited, true);
    assert.equal(b.playwright_prohibited, true);
    assert.equal(b.chromium_prohibited, true);
  });
});

// ===========================================================================

describe('ADG60 next-batch authorization execution policy sequential only', () => {
  it('sequential, no retry, no parallelism, 20-60s delay', () => {
    const m = readJson('fotmob_ligue1_adg60_next_batch_no_write_authorization.json');
    const e = m.future_execution_policy;
    assert.equal(e.max_network_requests, 5);
    assert.equal(e.exactly_one_request_per_target, true);
    assert.equal(e.sequential_only, true);
    assert.equal(e.no_retry, true);
    assert.equal(e.no_parallel_fetch, true);
    assert.equal(e.delay_between_requests_seconds.min, 20);
    assert.equal(e.delay_between_requests_seconds.max, 60);
    assert.equal(e.timeout_seconds_per_request, 20);
  });
});

// ===========================================================================

describe('ADG60 next-batch authorization review policy blocks auto-expansion', () => {
  it('review required, no auto 32-target', () => {
    const m = readJson('fotmob_ligue1_adg60_next_batch_no_write_authorization.json');
    const r = m.review_policy;
    assert.equal(r.review_required_after_next_batch, true);
    assert.equal(r.no_automatic_next_batch, true);
    assert.equal(r.no_automatic_32_target_run, true);
    assert.equal(r.any_failure_blocks_expansion, true);
  });
});

// ===========================================================================

describe('ADG60 next-batch authorization recommends next-batch execution next', () => {
  it('recommended_next is NEXT-BATCH execution', () => {
    const m = readJson('fotmob_ligue1_adg60_next_batch_no_write_authorization.json');
    assert.equal(m.recommended_next_phase, 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-NEXT-BATCH-NO-WRITE');
  });
});

// ===========================================================================

describe('ADG60 next-batch authorization stop conditions cover required guards', () => {
  it('stop conditions include 403, 429, captcha, anti-bot, redirect, DB write', () => {
    const m = readJson('fotmob_ligue1_adg60_next_batch_no_write_authorization.json');
    const sc = m.stop_conditions;
    assert.ok(sc.some((c) => c.includes('403')));
    assert.ok(sc.some((c) => c.includes('429')));
    assert.ok(sc.some((c) => c.includes('captcha')));
    assert.ok(sc.some((c) => c.includes('anti-bot')));
    assert.ok(sc.some((c) => c.includes('redirect')));
    assert.ok(sc.some((c) => c.includes('DB write attempted')));
    assert.ok(sc.some((c) => c.includes('raw_match_data insert attempted')));
    assert.ok(sc.some((c) => c.includes('browser automation attempted')));
  });
});
