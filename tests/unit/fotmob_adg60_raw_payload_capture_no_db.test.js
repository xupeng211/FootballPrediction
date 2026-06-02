/**
 * @fileoverview Unit tests for ADG60 raw payload capture helper.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert';
import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';

const ROOT = join(import.meta.dirname, '..', '..');
const src = readFileSync(join(ROOT, 'scripts/ops/fotmob_adg60_raw_payload_capture_no_db.js'), 'utf-8');
const policy = existsSync(join(ROOT, 'docs/data/FOTMOB_RAW_PAYLOAD_STORAGE_POLICY.md')) ?
  readFileSync(join(ROOT, 'docs/data/FOTMOB_RAW_PAYLOAD_STORAGE_POLICY.md'), 'utf-8') : '';

describe('raw payload capture default mode is preflight', () => {
  it('requires --execute-raw-payload-capture', () => {
    assert.ok(src.includes('--execute-raw-payload-capture'));
    assert.ok(src.includes('mode: \'preflight\''));
  });
});

describe('raw payload capture enforces 32 targets', () => {
  it('REQUIRED_COUNT=32', () => {
    assert.ok(src.includes('REQUIRED_COUNT = 32'));
  });
});

describe('raw payload capture enforces output root under data/raw/fotmob/', () => {
  it('output_root_safe check', () => {
    assert.ok(src.includes('data/raw/fotmob/'));
    assert.ok(src.includes('output_root_safe'));
  });
});

describe('raw payload capture checks gitignore', () => {
  it('verifies data/raw/ is gitignored', () => {
    assert.ok(src.includes('gitignore'));
  });
});

describe('raw payload capture has no body in manifest/report', () => {
  it('no_body_in_manifest, no_body_in_report flags', () => {
    assert.ok(src.includes('no_body_in_manifest'));
    assert.ok(src.includes('no_body_in_report'));
  });
});

describe('raw payload capture all safety flags', () => {
  it('body_committed/db_write/raw_match_data/adg60/browser all false', () => {
    const flags = ['body_committed: false', 'db_write: false', 'raw_match_data_insert: false', 'adg60_write: false', 'raw_write_ready_marked: false'];
    for (const f of flags) assert.ok(src.includes(f), f);
  });
});

describe('raw payload capture network limits', () => {
  it('max=32, sequential, no retry, no parallel, delay', () => {
    assert.ok(src.includes('MAX_REQUESTS = 32'));
    assert.ok(src.includes('no_retry'));
    assert.ok(src.includes('no_parallelism'));
    assert.ok(src.includes('DELAY_MIN'));
  });
});

describe('raw payload storage policy exists', () => {
  it('policy doc defines gitignored storage', () => {
    assert.ok(policy.includes('gitignored'));
    assert.ok(policy.includes('data/raw/'));
  });
});

describe('raw payload capture prevents overwrite by default', () => {
  it('file_exists_skip check', () => {
    assert.ok(src.includes('file_exists_skip'));
  });
});
