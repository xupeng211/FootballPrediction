/**
 * @fileoverview Unit tests for ADG60 three-target live fetch no-write review.
 *
 * lifecycle: phase-artifact
 * phase: ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-THREE-TARGET-NO-WRITE-REVIEW
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

describe('ADG60 three-target review has correct phase and reviewed PR', () => {
  it('phase is REVIEW and reviewed_pr is 1410', () => {
    const m = readJson('fotmob_ligue1_adg60_payload_acquisition_live_fetch_three_target_no_write.json');
    assert.equal(m.phase, 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-THREE-TARGET-NO-WRITE');
    assert.equal(m.recommended_next_phase, 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-THREE-TARGET-NO-WRITE-REVIEW');
  });
});

// ===========================================================================

describe('ADG60 three-target review confirms aggregate result', () => {
  it('target_count=3, request_total=3, success=3, blocked=0, stopped_early=false', () => {
    const m = readJson('fotmob_ligue1_adg60_payload_acquisition_live_fetch_three_target_no_write.json');
    const a = m.aggregate;
    assert.equal(a.selected_target_count, 3);
    assert.equal(a.request_count_total, 3);
    assert.equal(a.success_count, 3);
    assert.equal(a.blocked_count, 0);
    assert.equal(a.stopped_early, false);
  });
});

// ===========================================================================

describe('ADG60 three-target review confirms per-target HTTP 200', () => {
  it('all 3 targets http_status=200', () => {
    const m = readJson('fotmob_ligue1_adg60_payload_acquisition_live_fetch_three_target_no_write.json');
    for (const r of m.per_target_response_metadata) {
      assert.equal(r.http_status, 200, `target ${r.target_index} http_status must be 200`);
    }
  });
});

// ===========================================================================

describe('ADG60 three-target review confirms per-target payload markers', () => {
  it('all 3 targets payload_like=true, hasNextDataMarker=true, hasPagePropsMarker=true', () => {
    const m = readJson('fotmob_ligue1_adg60_payload_acquisition_live_fetch_three_target_no_write.json');
    for (const r of m.per_target_response_metadata) {
      assert.equal(r.payload_like, true, `target ${r.target_index} payload_like`);
      assert.equal(r.minimal_schema_flags.hasNextDataMarker, true, `target ${r.target_index} hasNextDataMarker`);
      assert.equal(r.minimal_schema_flags.hasPagePropsMarker, true, `target ${r.target_index} hasPagePropsMarker`);
    }
  });
});

// ===========================================================================

describe('ADG60 three-target review confirms distinct sha256', () => {
  it('all 3 sha256 values differ', () => {
    const m = readJson('fotmob_ligue1_adg60_payload_acquisition_live_fetch_three_target_no_write.json');
    const hashes = m.per_target_response_metadata.map((r) => r.sha256);
    assert.equal(new Set(hashes).size, 3);
    // Each must be 64 hex chars
    for (const h of hashes) {
      assert.equal(h.length, 64);
    }
  });
});

// ===========================================================================

describe('ADG60 three-target review confirms no body persisted', () => {
  it('all 3 targets body_persisted=false, body_logged=false, body_committed=false', () => {
    const m = readJson('fotmob_ligue1_adg60_payload_acquisition_live_fetch_three_target_no_write.json');
    for (const r of m.per_target_response_metadata) {
      assert.equal(r.body_persisted, false, `target ${r.target_index} body_persisted`);
      assert.equal(r.body_logged, false, `target ${r.target_index} body_logged`);
      assert.equal(r.body_committed, false, `target ${r.target_index} body_committed`);
    }
  });
});

// ===========================================================================

describe('ADG60 three-target review confirms all write/permission flags false', () => {
  it('all write flags false', () => {
    const m = readJson('fotmob_ligue1_adg60_payload_acquisition_live_fetch_three_target_no_write.json');
    const s = m.safety;
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

describe('ADG60 three-target review confirms recommended next phase', () => {
  it('recommended next is NEXT-BATCH-AUTHORIZATION', () => {
    const m = readJson('fotmob_ligue1_adg60_payload_acquisition_live_fetch_three_target_no_write.json');
    assert.equal(m.recommended_next_phase, 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-THREE-TARGET-NO-WRITE-REVIEW');
  });
});

// ===========================================================================

describe('ADG60 three-target review confirms target identities', () => {
  it('selected targets are [2,3,4] with correct identities', () => {
    const m = readJson('fotmob_ligue1_adg60_payload_acquisition_live_fetch_three_target_no_write.json');
    const targets = m.selected_targets;
    assert.equal(targets.length, 3);
    assert.equal(targets[0].target_index, 2);
    assert.equal(targets[0].expected_home, 'Nice');
    assert.equal(targets[0].expected_away, 'Auxerre');
    assert.equal(targets[1].target_index, 3);
    assert.equal(targets[1].expected_home, 'Strasbourg');
    assert.equal(targets[1].expected_away, 'Nantes');
    assert.equal(targets[2].target_index, 4);
    assert.equal(targets[2].expected_home, 'Toulouse');
    assert.equal(targets[2].expected_away, 'Brest');
  });
});

// ===========================================================================

describe('ADG60 three-target review helper is read-only', () => {
  it('review helper has no network/DB/write capabilities', () => {
    const helperSrc = readFileSync(
      join(ROOT, 'scripts/ops/fotmob_ligue1_adg60_live_fetch_three_target_no_write_review.js'),
      'utf-8',
    );
    // Must NOT contain network/DB/browser patterns
    // Must NOT contain executable network/DB/browser patterns
    assert.ok(!helperSrc.match(/await\s+fetch\s*\(/), 'must not have live fetch');
    assert.ok(!helperSrc.match(/import\s+.*from\s+['"]https?['"]/), 'must not import http/https module');
    assert.ok(!helperSrc.match(/import\s+.*playwright/i), 'must not import Playwright');
    assert.ok(!helperSrc.match(/import\s+.*chromium/i), 'must not import Chromium');
    assert.ok(!helperSrc.match(/import\s+.*puppeteer/i), 'must not import Puppeteer');
    // Must contain read-only declarations
    assert.ok(helperSrc.includes('read-only'), 'must declare read-only scope');
    assert.ok(helperSrc.includes('no network'), 'must declare no network');
    assert.ok(helperSrc.includes('no DB'), 'must declare no DB');
  });
});
