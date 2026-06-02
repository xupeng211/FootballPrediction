#!/usr/bin/env node
/**
 * @fileoverview Read-only review helper for ADG60 raw payload storage review.
 * No network, no DB, no write. Validates capture and extraction manifests.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const ROOT = join(import.meta.dirname, '..', '..');
function readJson(f) { return JSON.parse(readFileSync(join(ROOT, 'docs/_manifests', f), 'utf-8')); }

function main() {
  const cap = readJson('fotmob_raw_payload_capture_adg60_manifest.json');
  const ext = readJson('fotmob_raw_payload_extract_smoke_adg60_manifest.json');
  const c = [];

  c.push({ name: 'capture_phase', pass: cap.phase.includes('RAW-PAYLOAD-STORAGE') });
  c.push({ name: 'capture_success_32', pass: cap.aggregate.success_count === 32 });
  c.push({ name: 'capture_files_32', pass: cap.aggregate.file_saved_count === 32 });
  c.push({ name: 'capture_blocked_0', pass: cap.aggregate.blocked_count === 0 });
  c.push({ name: 'sha_count_32', pass: cap.per_target_results.filter((r) => r.sha256).length === 32 });
  c.push({ name: 'extract_nd_32', pass: ext.aggregate.next_data_found === 32 });
  c.push({ name: 'extract_parse_32', pass: ext.aggregate.next_data_parse_ok === 32 });
  c.push({ name: 'extract_pp_32', pass: ext.aggregate.page_props_found === 32 });
  c.push({ name: 'safety_body_false', pass: cap.safety.body_committed === false && cap.safety.db_write === false });
  c.push({ name: 'no_new_fetch', pass: true, note: 'review is read-only' });

  const passC = c.filter((x) => x.pass).length;
  const passed = c.length - passC === 0;
  console.log(JSON.stringify({ mode: 'review', verdict: passed ? 'pass' : 'fail', checks: c, new_live_fetch_performed: false, db_write_performed: false, raw_write_ready_marked: false }, null, 2));
  console.error(passed ? `\nREVIEW PASSED: ${passC}/${c.length}` : `\nREVIEW FAILED`);
  return passed ? 0 : 1;
}
main();
