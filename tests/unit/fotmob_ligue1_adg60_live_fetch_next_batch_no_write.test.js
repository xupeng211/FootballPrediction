/**
 * @fileoverview Unit tests for ADG60 next-batch live fetch no-write.
 *
 * lifecycle: phase-artifact
 * phase: ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-NEXT-BATCH-NO-WRITE
 */

import { describe, it } from 'node:test';
import assert from 'node:assert';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const ROOT = join(import.meta.dirname, '..', '..');
const src = readFileSync(join(ROOT, 'scripts/ops/fotmob_ligue1_adg60_live_fetch_next_batch_no_write.js'), 'utf-8');

describe('next-batch fetch default mode does not fetch', () => {
  it('requires execute flag', () => {
    assert.ok(src.includes('--execute-next-batch-live-fetch'), 'must require execute flag');
    assert.ok(src.includes('mode: \'preflight\''), 'default must be preflight');
  });
});

describe('next-batch fetch refuses wrong count', () => {
  it('requires exactly 5', () => {
    assert.ok(src.includes('REQUIRED_COUNT = 5'), 'must require 5 targets');
  });
});

describe('next-batch fetch refuses wrong indices', () => {
  it('requires [5,6,7,8,9]', () => {
    assert.ok(src.includes('REQUIRED_INDICES = [5, 6, 7, 8, 9]'), 'must require exact indices');
  });
});

describe('next-batch fetch enforces identity checks', () => {
  it('validates home, away, date, competition, hash, route', () => {
    const fields = ['expected_home', 'expected_away', 'expected_date', 'competition', 'corrected_hash_id', 'corrected_route_hash_pair'];
    for (const f of fields) assert.ok(new RegExp(f).test(src), `must check ${f}`);
  });
});

describe('next-batch fetch enforces network limits', () => {
  it('max 5 total, 1 per target', () => {
    assert.ok(src.includes('MAX_REQUESTS = 5'), 'max 5 requests');
    assert.ok(src.includes('MAX_PER_TARGET = 1'), '1 per target');
    assert.ok(src.includes('no_retry'), 'no retry');
    assert.ok(src.includes('no_parallelism'), 'no parallelism');
    assert.ok(src.includes('DELAY_MIN'), 'delay policy');
  });
});

describe('next-batch fetch never persists body', () => {
  it('body_persisted, body_logged, body_committed all false', () => {
    assert.ok(src.includes('body_persisted: false'), 'body_persisted false');
    assert.ok(src.includes('body_logged: false'), 'body_logged false');
    assert.ok(src.includes('body_committed: false'), 'body_committed false');
  });
});

describe('next-batch fetch all safety flags false', () => {
  it('all write/permission flags false', () => {
    const flags = ['browser_automation_performed: false', 'payload_saved: false', 'response_body_saved: false', 'db_write_performed: false', 'raw_write_performed: false', 'raw_match_data_insert_performed: false', 'adg60_write_performed: false', 'raw_write_ready_marked: false', 'schema_migration_performed: false'];
    for (const f of flags) assert.ok(src.includes(f), `must have ${f}`);
  });
});

describe('next-batch fetch stop conditions', () => {
  it('has stop conditions for 403, 429, captcha, anti-bot', () => {
    assert.ok(src.includes('blocked_403'), '403 stop');
    assert.ok(src.includes('blocked_429'), '429 stop');
    assert.ok(src.includes('anti_bot'), 'anti-bot stop');
    assert.ok(src.includes('timeout'), 'timeout stop');
  });
});

describe('next-batch fetch candidate identities', () => {
  it('targets [5,6,7,8,9] match authorization', () => {
    assert.ok(src.includes('53_20252026_4830478') && src.includes('Lens') && src.includes('2f5cib'), 'target 5');
    assert.ok(src.includes('53_20252026_4830479') && src.includes('Lorient') && src.includes('2he6a1'), 'target 6');
    assert.ok(src.includes('53_20252026_4830476') && src.includes('Angers') && src.includes('2o5ty5'), 'target 7');
    assert.ok(src.includes('53_20252026_4830477') && src.includes('Le Havre') && src.includes('363pdo'), 'target 8');
    assert.ok(src.includes('53_20252026_4830480') && src.includes('Lyon') && src.includes('2s51f2'), 'target 9');
  });
});

describe('next-batch fetch recommends review next', () => {
  it('phase is next-batch no-write', () => {
    assert.ok(src.includes('ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-NEXT-BATCH-NO-WRITE'), 'correct phase');
  });
});
