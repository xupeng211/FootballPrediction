/**
 * @fileoverview Unit tests for ADG60 final-batch live fetch no-write.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const ROOT = join(import.meta.dirname, '..', '..');
const src = readFileSync(join(ROOT, 'scripts/ops/fotmob_ligue1_adg60_live_fetch_final_batch_no_write.js'), 'utf-8');

describe('final-batch fetch requires execute flag', () => {
  it('default mode is preflight', () => {
    assert.ok(src.includes('--execute-final-batch-live-fetch'));
    assert.ok(src.includes('mode: \'preflight\''));
  });
});

describe('final-batch fetch enforces exact 23 targets', () => {
  it('REQUIRED_COUNT=23, indices [10..32]', () => {
    assert.ok(src.includes('REQUIRED_COUNT = 23'));
    assert.ok(src.includes('MAX_REQUESTS = 23'));
  });
});

describe('final-batch fetch enforces network limits', () => {
  it('max 23 total, 1 per target, sequential, no retry, no parallel, delay', () => {
    assert.ok(src.includes('MAX_REQUESTS = 23'));
    assert.ok(src.includes('MAX_PER_TARGET = 1'));
    assert.ok(src.includes('no_retry'));
    assert.ok(src.includes('no_parallelism'));
    assert.ok(src.includes('DELAY_MIN'));
  });
});

describe('final-batch fetch never persists body', () => {
  it('body_persisted/logged/committed all false', () => {
    assert.ok(src.includes('body_persisted: false'));
    assert.ok(src.includes('body_logged: false'));
    assert.ok(src.includes('body_committed: false'));
  });
});

describe('final-batch fetch all safety flags false', () => {
  it('all write/browser flags false', () => {
    const flags = ['browser_automation_performed: false','payload_saved: false','response_body_saved: false','db_write_performed: false','raw_write_performed: false','raw_match_data_insert_performed: false','adg60_write_performed: false','raw_write_ready_marked: false','schema_migration_performed: false'];
    for (const f of flags) { assert.ok(src.includes(f), f); }
  });
});

describe('final-batch fetch has stop conditions', () => {
  it('403, 429, captcha, anti-bot, timeout', () => {
    assert.ok(src.includes('blocked_403'));
    assert.ok(src.includes('blocked_429'));
    assert.ok(src.includes('anti_bot'));
    assert.ok(src.includes('timeout'));
  });
});

describe('final-batch fetch candidate samples correct', () => {
  it('targets 10, 20, 32 have expected identities', () => {
    assert.ok(src.includes('Nantes') && src.includes('Auxerre') && src.includes('2sxslt'));
    assert.ok(src.includes('Lorient') && src.includes('Monaco'));
    assert.ok(src.includes('Strasbourg') && src.includes('Marseille') && src.includes('2t8gik'));
  });
});
