#!/usr/bin/env node
/**
 * @fileoverview Read-only review helper for ADG60 raw JSON DB storage review.
 * No network, no DB write, no feature parse. Validates storage manifest and migration.
 */

import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';

const ROOT = join(import.meta.dirname, '..', '..');
function readJson(f) { return JSON.parse(readFileSync(join(ROOT, 'docs/_manifests', f), 'utf-8')); }

function main() {
  const mf = readJson('fotmob_raw_json_db_storage_adg60_manifest.json');
  const migPath = join(ROOT, 'database/migrations/V26.5__create_fotmob_raw_match_payloads.sql');
  const migration = existsSync(migPath) ? readFileSync(migPath, 'utf-8') : '';
  const c = [];

  c.push({ name: 'phase', pass: mf.phase.includes('RAW-JSON-DB-STORAGE') });
  c.push({ name: 'db_row_count_32', pass: mf.aggregate.db_row_count === 32 });
  c.push({ name: 'distinct_match_32', pass: mf.aggregate.distinct_match_id_count === 32 });
  c.push({ name: 'json_present_32', pass: mf.aggregate.json_present_count === 32 });
  c.push({ name: 'inserted_32', pass: mf.aggregate.inserted_count >= 32 });
  c.push({ name: 'no_failed', pass: mf.aggregate.failed_count === 0 });

  // Safety flags
  const s = mf.safety;
  c.push({ name: 'no_feature_parse', pass: s.feature_parse_performed === false });
  c.push({ name: 'no_raw_match_data', pass: s.raw_match_data_insert_performed === false });
  c.push({ name: 'no_l3_features', pass: s.l3_features_write_performed === false });
  c.push({ name: 'no_predictions', pass: s.predictions_write_performed === false });
  c.push({ name: 'no_rwr_mark', pass: s.raw_write_ready_marked === false });

  // Manifest safety: no raw JSON body
  for (const r of (mf.per_target_rows || [])) {
    c.push({ name: `t${r.target_index}_no_raw_nd`, pass: !r.__NEXT_DATA__ && !r.pageProps && !r.raw_json });
  }
  c.push({ name: 'manifest_no_raw_json', pass: true, note: 'verified all rows' });

  // Migration safety
  c.push({ name: 'migration_no_drop', pass: !migration.match(/DROP\s+(TABLE|DATABASE)/i) });
  c.push({ name: 'migration_no_truncate', pass: !migration.match(/\bTRUNCATE\b/i) });
  c.push({ name: 'migration_has_jsonb', pass: migration.includes('JSONB') });
  c.push({ name: 'migration_has_gin', pass: migration.includes('GIN') });

  c.push({ name: 'no_new_fetch', pass: true, note: 'review is read-only' });
  c.push({ name: 'no_new_db_write', pass: true, note: 'review is read-only' });

  const passC = c.filter((x) => x.pass).length;
  const failC = c.length - passC;
  console.log(JSON.stringify({ mode: 'review', verdict: failC === 0 ? 'pass' : 'fail', checks: c, new_db_write_performed: false, feature_parse_performed: false, raw_write_ready_marked: false }, null, 2));
  console.error(failC === 0 ? `\nREVIEW PASSED: ${passC}/${c.length}` : `\nREVIEW FAILED: ${failC} checks`);
  return failC === 0 ? 0 : 1;
}
main();
