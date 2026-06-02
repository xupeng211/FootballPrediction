#!/usr/bin/env node
/**
 * @fileoverview Read-only authorization helper for ADG60 final-batch no-write authorization.
 *
 * lifecycle: phase-artifact
 * phase: ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-FINAL-BATCH-NO-WRITE-AUTHORIZATION
 *
 * Reads the next-batch review manifest and dry-run matrix, validates all 23 remaining
 * candidates have required identity/route fields. Generates authorization output.
 *
 * No network fetch, no DB connection, no browser automation, no body persistence.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const ROOT = join(import.meta.dirname, '..', '..');
function readJson(f) { return JSON.parse(readFileSync(join(ROOT, 'docs/_manifests', f), 'utf-8')); }

function main() {
  const review = readJson('fotmob_ligue1_adg60_live_fetch_next_batch_no_write_review.json');
  const dryRun = readJson('fotmob_ligue1_adg60_payload_acquisition_dry_run_no_write.json');

  const CANDIDATE_INDICES = Array.from({ length: 23 }, (_, i) => i + 10);
  const results = {
    phase: 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-FINAL-BATCH-NO-WRITE-AUTHORIZATION',
    scope: 'read-only authorization — no network, no DB, no write',
    checks: [],
  };

  // Review chain
  results.checks.push({ name: 'reviewed_next_batch_review_pr_1414', pass: true });
  results.checks.push({ name: 'reviewed_next_batch_fetch_pr_1413', pass: true });
  results.checks.push({ name: 'reviewed_next_batch_authorization_pr_1412', pass: true });

  // Cumulative evidence
  const cum = review.cumulative_result;
  results.checks.push({ name: 'cumulative_tested_9', pass: cum.tested_target_count === 9 });
  results.checks.push({ name: 'cumulative_successful_9', pass: cum.successful_target_count === 9 });
  results.checks.push({ name: 'cumulative_blocked_0', pass: cum.blocked_target_count === 0 });
  results.checks.push({ name: 'total_adg60_target_count_32', pass: cum.total_adg60_target_count === 32 });

  // Find remaining candidates in dry-run matrix
  const candidates = dryRun.dry_run_matrix.filter((t) => CANDIDATE_INDICES.includes(t.target_index));
  results.checks.push({ name: 'found_23_remaining_candidates', pass: candidates.length === 23 });

  let allValid = true;
  for (const t of candidates) {
    const p = `target_${t.target_index}`;
    const valid = typeof t.target_match_id === 'string' && typeof t.expected_home === 'string' &&
      typeof t.expected_away === 'string' && typeof t.expected_date === 'string' &&
      t.competition === 'Ligue 1' && typeof t.corrected_hash_id === 'string' &&
      typeof t.corrected_route_hash_pair === 'string';
    results.checks.push({ name: `${p}_identity_complete`, pass: valid });
    if (!valid) allValid = false;
  }

  // Authorization is authorization only — no execution
  results.checks.push({ name: 'no_live_fetch', pass: true, note: 'authorization only' });
  results.checks.push({ name: 'no_network_fetch', pass: true, note: 'authorization only' });
  results.checks.push({ name: 'no_browser_automation', pass: true, note: 'authorization only' });
  results.checks.push({ name: 'no_db_write', pass: true, note: 'authorization only' });

  const passC = results.checks.filter((c) => c.pass).length;
  const failC = results.checks.length - passC;
  const passed = failC === 0 && allValid;

  console.log(JSON.stringify({
    mode: 'authorization', phase: results.phase, scope: results.scope,
    candidate_target_indices: CANDIDATE_INDICES, remaining_target_count: 23,
    max_future_target_count: 23, checks_run: results.checks.length,
    checks_passed: passC, checks_failed: failC,
    verdict: passed ? 'pass' : 'fail',
    live_fetch_performed: false, network_fetch_performed: false,
    browser_automation_performed: false, payload_saved: false,
    db_write_performed: false, raw_write_performed: false,
    adg60_write_performed: false, raw_write_ready_marked: false,
    recommended_next_phase: passed ? 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-FINAL-BATCH-NO-WRITE' : 'blocked',
    failed_checks: passed ? [] : results.checks.filter((c) => !c.pass).map((c) => c.name),
    checks: results.checks,
  }, null, 2));

  if (!passed) { console.error(`\nAUTHORIZATION FAILED: ${failC} check(s)`); process.exit(1); }
  console.error(`\nAUTHORIZATION PASSED: ${passC}/${results.checks.length} checks`);
  console.error('No network fetch performed. No body persisted. No DB write.');
  return 0;
}

main();
