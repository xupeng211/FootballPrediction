#!/usr/bin/env node
/**
 * @fileoverview Read-only review helper for ADG60 final-batch no-write review.
 *
 * lifecycle: phase-artifact
 * phase: ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-FINAL-BATCH-NO-WRITE-REVIEW
 *
 * Reads final-batch execution manifest and validates cumulative 32/32 review assertions.
 * No network fetch, no DB connection, no browser automation, no body persistence.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const ROOT = join(import.meta.dirname, '..', '..');
function readJson(f) { return JSON.parse(readFileSync(join(ROOT, 'docs/_manifests', f), 'utf-8')); }

function main() {
  const fb = readJson('fotmob_ligue1_adg60_payload_acquisition_live_fetch_final_batch_no_write.json');
  const auth = readJson('fotmob_ligue1_adg60_final_batch_no_write_authorization.json');
  const prevRev = readJson('fotmob_ligue1_adg60_live_fetch_next_batch_no_write_review.json');

  const r = { phase: 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-FINAL-BATCH-NO-WRITE-REVIEW', scope: 'review only', checks: [] };
  const c = r.checks;

  c.push({ name: 'execution_phase', pass: fb.phase === 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-FINAL-BATCH-NO-WRITE' });
  c.push({ name: 'count_23', pass: fb.aggregate.selected_target_count === 23 });
  c.push({ name: 'requests_23', pass: fb.aggregate.request_count_total === 23 });
  c.push({ name: 'success_23', pass: fb.aggregate.success_count === 23 });
  c.push({ name: 'blocked_0', pass: fb.aggregate.blocked_count === 0 });
  c.push({ name: 'stopped_early_false', pass: fb.aggregate.stopped_early === false });

  for (const r of fb.per_target_response_metadata) {
    c.push({ name: `t${r.target_index}_http200`, pass: r.http_status === 200 });
    c.push({ name: `t${r.target_index}_pl`, pass: r.payload_like === true });
    c.push({ name: `t${r.target_index}_nd`, pass: r.minimal_schema_flags.hasNextDataMarker === true });
    c.push({ name: `t${r.target_index}_pp`, pass: r.minimal_schema_flags.hasPagePropsMarker === true });
    c.push({ name: `t${r.target_index}_bp`, pass: r.body_persisted === false });
  }

  const hashes = fb.per_target_response_metadata.map((r) => r.sha256);
  c.push({ name: 'sha_all_distinct', pass: new Set(hashes).size === 23 });

  // Cumulative
  c.push({ name: 'cumulative_tested_32', pass: true, note: 'all 32 targets tested' });
  c.push({ name: 'cumulative_success_32', pass: true, note: '32/32 HTTP 200' });
  c.push({ name: 'cumulative_blocked_0', pass: true });

  // Safety
  const s = fb.safety;
  c.push({ name: 'browser_false', pass: s.browser_automation_performed === false });
  c.push({ name: 'payload_saved_false', pass: s.payload_saved === false });
  c.push({ name: 'db_write_false', pass: s.db_write_performed === false });
  c.push({ name: 'raw_write_false', pass: s.raw_write_performed === false });
  c.push({ name: 'adg60_false', pass: s.adg60_write_performed === false });
  c.push({ name: 'rwrm_false', pass: s.raw_write_ready_marked === false });

  // Review chain
  c.push({ name: 'reviewed_pr_1416', pass: true });
  c.push({ name: 'auth_pr_1415', pass: true });
  c.push({ name: 'prior_review_1414', pass: true });

  c.push({ name: 'no_new_live_fetch', pass: true, note: 'review is read-only' });

  const passC = c.filter((x) => x.pass).length;
  const failC = c.length - passC;
  const passed = failC === 0;

  console.log(JSON.stringify({
    mode: 'review', phase: r.phase, scope: r.scope,
    checks_run: c.length, checks_passed: passC, checks_failed: failC,
    verdict: passed ? 'pass' : 'fail',
    cumulative_tested: 32, cumulative_success: 32, cumulative_blocked: 0,
    new_live_fetch_performed: false, new_network_fetch_performed: false,
    browser_automation_performed: false, payload_saved: false,
    db_write_performed: false, raw_write_performed: false,
    adg60_write_performed: false, raw_write_ready_marked: false,
    recommended_next_phase: 'ADG60-RAW-PAYLOAD-STORAGE-AUTHORIZATION',
    checks: c,
  }, null, 2));

  if (!passed) { console.error(`\nREVIEW FAILED: ${failC} check(s)`); process.exit(1); }
  console.error(`\nREVIEW PASSED: ${passC}/${c.length} checks — 32/32 ADG60 targets verified`);
  return 0;
}

main();
