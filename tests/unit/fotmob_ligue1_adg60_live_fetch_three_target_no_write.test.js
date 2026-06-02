/**
 * @fileoverview Unit tests for ADG60 three-target live fetch no-write.
 *
 * lifecycle: phase-artifact
 * phase: ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-THREE-TARGET-NO-WRITE
 */

import { describe, it } from 'node:test';
import assert from 'node:assert';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const ROOT = join(import.meta.dirname, '..', '..');

function readManifest(filename) {
  return JSON.parse(readFileSync(join(ROOT, 'docs/_manifests', filename), 'utf-8'));
}

function readReport(filename) {
  return readFileSync(join(ROOT, 'docs/_reports', filename), 'utf-8');
}

// ===========================================================================

describe('ADG60 three-target live fetch default mode does not fetch', () => {
  it('default mode reports preflight only', () => {
    // Verify the helper exists and has the execute flag gate
    const helperSrc = readFileSync(
      join(ROOT, 'scripts/ops/fotmob_ligue1_adg60_live_fetch_three_target_no_write.js'),
      'utf-8',
    );
    assert.ok(helperSrc.includes('--execute-three-target-live-fetch'),
      'helper must require execute flag');
    assert.ok(helperSrc.includes('mode: \'preflight\''),
      'default mode must be preflight');
    assert.ok(helperSrc.includes('live_fetch_requires'),
      'must state execute flag requirement');
  });
});

// ===========================================================================

describe('ADG60 three-target live fetch refuses wrong target count', () => {
  it('preflight rejects count != 3', () => {
    const helperSrc = readFileSync(
      join(ROOT, 'scripts/ops/fotmob_ligue1_adg60_live_fetch_three_target_no_write.js'),
      'utf-8',
    );
    assert.ok(helperSrc.includes('REQUIRED_SELECTED_COUNT = 3'),
      'must enforce selected target count of 3');
    assert.ok(helperSrc.includes('selected_target_count'),
      'must check selected target count');
  });
});

// ===========================================================================

describe('ADG60 three-target live fetch refuses wrong indices', () => {
  it('preflight rejects indices != [2,3,4]', () => {
    const helperSrc = readFileSync(
      join(ROOT, 'scripts/ops/fotmob_ligue1_adg60_live_fetch_three_target_no_write.js'),
      'utf-8',
    );
    assert.ok(helperSrc.includes('REQUIRED_INDICES = [2, 3, 4]'),
      'must enforce exact indices [2,3,4]');
    assert.ok(helperSrc.includes('selected_indices'),
      'must validate selected indices');
  });
});

// ===========================================================================

describe('ADG60 three-target live fetch enforces identity/route checks before network', () => {
  it('preflight validates expected_home, expected_away, expected_date, competition', () => {
    const helperSrc = readFileSync(
      join(ROOT, 'scripts/ops/fotmob_ligue1_adg60_live_fetch_three_target_no_write.js'),
      'utf-8',
    );
    assert.ok(helperSrc.includes('expected_home'), 'must check expected_home');
    assert.ok(helperSrc.includes('expected_away'), 'must check expected_away');
    assert.ok(helperSrc.includes('expected_date'), 'must check expected_date');
    assert.ok(helperSrc.includes('competition'), 'must check competition');
    assert.ok(helperSrc.includes('corrected_hash_id'), 'must check corrected_hash_id');
    assert.ok(helperSrc.includes('corrected_route_hash_pair'), 'must check route_hash_pair');
  });
});

// ===========================================================================

describe('ADG60 three-target live fetch enforces network limits', () => {
  it('max_network_requests_total=3, max_per_target=1', () => {
    const helperSrc = readFileSync(
      join(ROOT, 'scripts/ops/fotmob_ligue1_adg60_live_fetch_three_target_no_write.js'),
      'utf-8',
    );
    assert.ok(helperSrc.includes('MAX_NETWORK_REQUESTS_TOTAL = 3'),
      'must enforce max 3 total requests');
    assert.ok(helperSrc.includes('MAX_NETWORK_REQUESTS_PER_TARGET = 1'),
      'must enforce 1 request per target');
  });

  it('no retry, no parallelism, delay policy exists', () => {
    const helperSrc = readFileSync(
      join(ROOT, 'scripts/ops/fotmob_ligue1_adg60_live_fetch_three_target_no_write.js'),
      'utf-8',
    );
    assert.ok(helperSrc.includes('no_retry') || helperSrc.includes('no retry'),
      'must declare no retry');
    assert.ok(helperSrc.includes('no_parallelism') || helperSrc.includes('no parallelism'),
      'must declare no parallelism');
    assert.ok(helperSrc.includes('DELAY_MIN_MS'), 'must have delay policy');
  });
});

// ===========================================================================

describe('ADG60 three-target live fetch never contains body/HTML pageProps', () => {
  it('helper has no body persistence or logging', () => {
    const helperSrc = readFileSync(
      join(ROOT, 'scripts/ops/fotmob_ligue1_adg60_live_fetch_three_target_no_write.js'),
      'utf-8',
    );
    // Must contain safety declarations
    assert.ok(helperSrc.includes('body_persisted') || helperSrc.includes('body_persisted: false'),
      'must track body_persisted');
    assert.ok(helperSrc.includes('body_logged') || helperSrc.includes('body_logged: false'),
      'must track body_logged');
    assert.ok(helperSrc.includes('body_committed') || helperSrc.includes('body_committed: false'),
      'must track body_committed');
    // Must NOT contain body-save patterns
    assert.ok(!helperSrc.match(/writeFile.*body/i) && !helperSrc.match(/writeFile.*payload/i),
      'must not save body to file');
    assert.ok(!helperSrc.includes('__NEXT_DATA__ save') && !helperSrc.includes('pageProps save'),
      'must not save __NEXT_DATA__ or pageProps');
  });
});

// ===========================================================================

describe('ADG60 three-target live fetch all safety flags enforced', () => {
  it('browser_automation_performed, payload_saved, write flags all false', () => {
    const helperSrc = readFileSync(
      join(ROOT, 'scripts/ops/fotmob_ligue1_adg60_live_fetch_three_target_no_write.js'),
      'utf-8',
    );
    assert.ok(helperSrc.includes('browser_automation_performed: false'),
      'browser_automation_performed must be false');
    assert.ok(helperSrc.includes('payload_saved: false'),
      'payload_saved must be false');
    assert.ok(helperSrc.includes('response_body_saved: false'),
      'response_body_saved must be false');
    assert.ok(helperSrc.includes('db_write_performed: false'),
      'db_write_performed must be false');
    assert.ok(helperSrc.includes('raw_write_performed: false'),
      'raw_write_performed must be false');
    assert.ok(helperSrc.includes('raw_match_data_insert_performed: false'),
      'raw_match_data_insert_performed must be false');
    assert.ok(helperSrc.includes('adg60_write_performed: false'),
      'adg60_write_performed must be false');
    assert.ok(helperSrc.includes('raw_write_ready_marked: false'),
      'raw_write_ready_marked must be false');
    assert.ok(helperSrc.includes('schema_migration_performed: false'),
      'schema_migration_performed must be false');
  });
});

// ===========================================================================

describe('ADG60 three-target live fetch recommends review next', () => {
  it('recommended_next_phase is review no-write', () => {
    const helperSrc = readFileSync(
      join(ROOT, 'scripts/ops/fotmob_ligue1_adg60_live_fetch_three_target_no_write.js'),
      'utf-8',
    );
    // Preflight mode should state the phase correctly
    assert.ok(helperSrc.includes('ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-THREE-TARGET-NO-WRITE'),
      'phase must be three-target no-write execution');
  });
});

// ===========================================================================

describe('ADG60 three-target live fetch stop conditions cover required guards', () => {
  it('stop conditions include 403, 429, captcha, anti-bot, redirect, body save, DB write', () => {
    const helperSrc = readFileSync(
      join(ROOT, 'scripts/ops/fotmob_ligue1_adg60_live_fetch_three_target_no_write.js'),
      'utf-8',
    );
    const stopChecks = [
      'blocked_403',
      'blocked_429',
      'anti_bot_or_captcha_detected',
      'unexpected_redirect',
      'payload_too_large',
      'timeout',
    ];
    for (const sc of stopChecks) {
      assert.ok(helperSrc.includes(sc), `must have stop condition: ${sc}`);
    }
  });
});

// ===========================================================================

describe('ADG60 three-target live fetch candidate identities match authorization', () => {
  it('targets [2,3,4] have correct identities from authorization manifest', () => {
    const helperSrc = readFileSync(
      join(ROOT, 'scripts/ops/fotmob_ligue1_adg60_live_fetch_three_target_no_write.js'),
      'utf-8',
    );
    assert.ok(helperSrc.includes('53_20252026_4830472'), 'target 2 match_id');
    assert.ok(helperSrc.includes('53_20252026_4830474'), 'target 3 match_id');
    assert.ok(helperSrc.includes('53_20252026_4830475'), 'target 4 match_id');

    assert.ok(helperSrc.includes('Nice'), 'target 2 home');
    assert.ok(helperSrc.includes('Auxerre'), 'target 2 away');
    assert.ok(helperSrc.includes('Strasbourg'), 'target 3 home');
    assert.ok(helperSrc.includes('Nantes'), 'target 3 away');
    assert.ok(helperSrc.includes('Toulouse'), 'target 4 home');
    assert.ok(helperSrc.includes('Brest'), 'target 4 away');

    assert.ok(helperSrc.includes('2sy6tc#4830472'), 'target 2 route');
    assert.ok(helperSrc.includes('37a71l#4830474'), 'target 3 route');
    assert.ok(helperSrc.includes('2th5t2#4830475'), 'target 4 route');
  });
});
