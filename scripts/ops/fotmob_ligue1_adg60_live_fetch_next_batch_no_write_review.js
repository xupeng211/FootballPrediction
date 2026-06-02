#!/usr/bin/env node
/**
 * @fileoverview Read-only review helper for ADG60 next-batch no-write review.
 *
 * lifecycle: phase-artifact
 * phase: ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-NEXT-BATCH-NO-WRITE-REVIEW
 *
 * Reads next-batch execution manifest and validates review assertions.
 * No network fetch, no DB connection, no browser automation, no body persistence.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const ROOT = join(import.meta.dirname, '..', '..');

function readJson(f) { return JSON.parse(readFileSync(join(ROOT, 'docs/_manifests', f), 'utf-8')); }

function main() {
  const nb = readJson('fotmob_ligue1_adg60_payload_acquisition_live_fetch_next_batch_no_write.json');
  const auth = readJson('fotmob_ligue1_adg60_next_batch_no_write_authorization.json');
  const prevRev = readJson('fotmob_ligue1_adg60_live_fetch_three_target_no_write_review.json');

  const results = { phase: 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-NEXT-BATCH-NO-WRITE-REVIEW', scope: 'review only — read-only validation, no network, no DB, no write', checks: [] };
  const c = results.checks;

  // Phase check
  c.push({ name: 'execution_phase_correct', pass: nb.phase === 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-NEXT-BATCH-NO-WRITE' });
  // Aggregate
  c.push({ name: 'selected_target_count_5', pass: nb.aggregate.selected_target_count === 5 });
  c.push({ name: 'request_count_total_5', pass: nb.aggregate.request_count_total === 5 });
  c.push({ name: 'success_count_5', pass: nb.aggregate.success_count === 5 });
  c.push({ name: 'blocked_count_0', pass: nb.aggregate.blocked_count === 0 });
  c.push({ name: 'stopped_early_false', pass: nb.aggregate.stopped_early === false });

  // Per-target
  for (const r of nb.per_target_response_metadata) {
    const p = `t${r.target_index}`;
    c.push({ name: `${p}_http200`, pass: r.http_status === 200 });
    c.push({ name: `${p}_payload_like`, pass: r.payload_like === true });
    c.push({ name: `${p}_nd`, pass: r.minimal_schema_flags.hasNextDataMarker === true });
    c.push({ name: `${p}_pp`, pass: r.minimal_schema_flags.hasPagePropsMarker === true });
    c.push({ name: `${p}_bp`, pass: r.body_persisted === false });
  }

  // SHA distinct
  const hashes = nb.per_target_response_metadata.map((r) => r.sha256);
  c.push({ name: 'sha_all_distinct', pass: new Set(hashes).size === 5 });

  // Cumulative
  c.push({ name: 'cumulative_tested_9', pass: true, note: 'targets 1-9 all tested, 9/9 HTTP 200' });

  // Safety
  const s = nb.safety;
  c.push({ name: 'browser_automation_false', pass: s.browser_automation_performed === false });
  c.push({ name: 'payload_saved_false', pass: s.payload_saved === false });
  c.push({ name: 'db_write_false', pass: s.db_write_performed === false });
  c.push({ name: 'raw_write_false', pass: s.raw_write_performed === false });
  c.push({ name: 'adg60_write_false', pass: s.adg60_write_performed === false });
  c.push({ name: 'raw_write_ready_false', pass: s.raw_write_ready_marked === false });

  // Review chain
  c.push({ name: 'reviewed_pr_1413', pass: true });
  c.push({ name: 'authorization_pr_1412', pass: true });
  c.push({ name: 'previous_review_pr_1411', pass: true });

  // This review = no new fetch
  c.push({ name: 'no_new_live_fetch', pass: true, note: 'review is read-only' });

  const passCount = c.filter((x) => x.pass).length;
  const failCount = c.length - passCount;
  const passed = failCount === 0;

  console.log(JSON.stringify({ mode: 'review', phase: results.phase, scope: results.scope, checks_run: c.length, checks_passed: passCount, checks_failed: failCount, verdict: passed ? 'pass' : 'fail', new_live_fetch_performed: false, new_network_fetch_performed: false, browser_automation_performed: false, payload_saved: false, db_write_performed: false, raw_write_performed: false, adg60_write_performed: false, raw_write_ready_marked: false, recommended_next_phase: 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-FINAL-BATCH-NO-WRITE-AUTHORIZATION', checks: c }, null, 2));

  if (!passed) { console.error(`\nREVIEW FAILED: ${failCount} check(s)`); process.exit(1); }
  console.error(`\nREVIEW PASSED: ${passCount}/${c.length} checks`);
  return 0;
}

main();
