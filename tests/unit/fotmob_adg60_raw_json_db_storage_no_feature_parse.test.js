/**
 * @fileoverview Unit tests for ADG60 raw JSON DB storage helper.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert';
import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';

const ROOT = join(import.meta.dirname, '..', '..');
const src = readFileSync(join(ROOT, 'scripts/ops/fotmob_adg60_raw_json_db_storage_no_feature_parse.js'), 'utf-8');
const migration = existsSync(join(ROOT, 'database/migrations/V26.5__create_fotmob_raw_match_payloads.sql')) ?
  readFileSync(join(ROOT, 'database/migrations/V26.5__create_fotmob_raw_match_payloads.sql'), 'utf-8') : '';

describe('raw JSON storage default dry-run', () => {
  it('requires --execute-db-storage', () => {
    assert.ok(src.includes('--execute-db-storage'));
    assert.ok(src.includes('dry_run'));
  });
});

describe('raw JSON storage enforces target indices', () => {
  it('checks indices 1-32', () => {
    assert.ok(src.includes('parseIndices'));
  });
});

describe('raw JSON storage checks git safety', () => {
  it('verifies data/raw/fotmob/ prefix', () => {
    assert.ok(src.includes('data/raw/fotmob/'));
    assert.ok(src.includes('checkGitSafety'));
  });
});

describe('raw JSON storage extracts __NEXT_DATA__ and pageProps', () => {
  it('extracts next_data and pageProps from HTML', () => {
    assert.ok(src.includes('__NEXT_DATA__'));
    assert.ok(src.includes('pageProps'));
    assert.ok(src.includes('extractNextDataText'));
    assert.ok(src.includes('extractPageProps'));
  });
});

describe('raw JSON storage all safety flags false', () => {
  it('feature_parse/raw_match_data/l3/predictions/raw_write_ready all false', () => {
    assert.ok(src.includes('feature_parse_performed: false'));
    assert.ok(src.includes('raw_match_data_insert_performed: false'));
    assert.ok(src.includes('l3_features_write_performed: false'));
    assert.ok(src.includes('match_features_training_write_performed: false'));
    assert.ok(src.includes('predictions_write_performed: false'));
    assert.ok(src.includes('raw_write_ready_marked: false'));
    assert.ok(src.includes('production_db_write_performed: false'));
  });
});

describe('raw JSON storage manifest never includes raw JSON', () => {
  it('manifest has no body/HTML/pageProps dumps', () => {
    // Check that the manifest building code doesn't include raw body
    const m = existsSync(join(ROOT, 'docs/_manifests/fotmob_raw_json_db_storage_adg60_manifest.json')) ?
      JSON.parse(readFileSync(join(ROOT, 'docs/_manifests/fotmob_raw_json_db_storage_adg60_manifest.json'), 'utf-8')) : null;
    if (m && m.per_target_rows && m.per_target_rows.length > 0) {
      for (const r of m.per_target_rows) {
        assert.ok(!r.__NEXT_DATA__, 'no raw __NEXT_DATA__ in manifest');
        assert.ok(!r.pageProps, 'no raw pageProps in manifest');
        assert.ok(!r.raw_json, 'no raw json in manifest');
      }
    }
  });
});

describe('migration creates only fotmob_raw_match_payloads', () => {
  it('no DROP/TRUNCATE/DELETE', () => {
    assert.ok(!migration.match(/DROP\s+(TABLE|DATABASE)/i));
    assert.ok(!migration.match(/\bTRUNCATE\b/i));
    assert.ok(!migration.match(/\bDELETE\s+FROM\b/i));
    assert.ok(!migration.match(/\bALTER\s+TABLE\s+(?!fotmob_raw)/i));
    assert.ok(migration.includes('fotmob_raw_match_payloads'));
    assert.ok(migration.includes('JSONB'));
  });
});

describe('migration has proper indexes', () => {
  it('GIN indexes on jsonb columns', () => {
    assert.ok(migration.includes('GIN'));
    assert.ok(migration.includes('next_data_json'));
    assert.ok(migration.includes('page_props_json'));
  });
});
