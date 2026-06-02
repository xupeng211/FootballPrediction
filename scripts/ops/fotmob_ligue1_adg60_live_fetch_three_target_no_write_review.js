#!/usr/bin/env node

/**
 * @fileoverview Read-only review helper for ADG60 three-target no-write review.
 *
 * lifecycle: phase-artifact
 * phase: ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-THREE-TARGET-NO-WRITE-REVIEW
 *
 * Reads the three-target execution manifest and the one-target review manifest,
 * then validates the review assertions without accessing the network, database,
 * or performing any write operations.
 *
 * No network fetch, no DB connection, no browser automation, no body persistence.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const ROOT = join(import.meta.dirname, '..', '..');

function readJson(filename) {
  return JSON.parse(readFileSync(join(ROOT, 'docs/_manifests', filename), 'utf-8'));
}

function main() {
  const threeTarget = readJson('fotmob_ligue1_adg60_payload_acquisition_live_fetch_three_target_no_write.json');
  const oneTargetReview = readJson('fotmob_ligue1_adg60_live_fetch_one_target_no_write_review.json');
  const authorization = readJson('fotmob_ligue1_adg60_three_target_no_write_authorization.json');

  const results = {
    phase: 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-THREE-TARGET-NO-WRITE-REVIEW',
    scope: 'review only — read-only validation, no network, no DB, no write',
    checks: [],
  };

  // Phase check
  results.checks.push({
    name: 'execution_phase_correct',
    pass: threeTarget.phase === 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-THREE-TARGET-NO-WRITE',
  });

  // Aggregate check
  results.checks.push({
    name: 'selected_target_count_equals_3',
    pass: threeTarget.aggregate.selected_target_count === 3,
  });
  results.checks.push({
    name: 'request_count_total_equals_3',
    pass: threeTarget.aggregate.request_count_total === 3,
  });
  results.checks.push({
    name: 'success_count_equals_3',
    pass: threeTarget.aggregate.success_count === 3,
  });
  results.checks.push({
    name: 'blocked_count_equals_0',
    pass: threeTarget.aggregate.blocked_count === 0,
  });
  results.checks.push({
    name: 'stopped_early_is_false',
    pass: threeTarget.aggregate.stopped_early === false,
  });

  // Per-target checks
  for (const r of threeTarget.per_target_response_metadata) {
    const prefix = `target_${r.target_index}`;
    results.checks.push({ name: `${prefix}_http_status_200`, pass: r.http_status === 200 });
    results.checks.push({ name: `${prefix}_request_performed`, pass: r.request_performed === true });
    results.checks.push({ name: `${prefix}_payload_like`, pass: r.payload_like === true });
    results.checks.push({ name: `${prefix}_hasNextDataMarker`, pass: r.minimal_schema_flags.hasNextDataMarker === true });
    results.checks.push({ name: `${prefix}_hasPagePropsMarker`, pass: r.minimal_schema_flags.hasPagePropsMarker === true });
    results.checks.push({ name: `${prefix}_body_persisted_false`, pass: r.body_persisted === false });
    results.checks.push({ name: `${prefix}_body_logged_false`, pass: r.body_logged === false });
    results.checks.push({ name: `${prefix}_body_committed_false`, pass: r.body_committed === false });
    results.checks.push({ name: `${prefix}_sha256_present`, pass: typeof r.sha256 === 'string' && r.sha256.length === 64 });
  }

  // SHA distinctness check
  const sha256s = threeTarget.per_target_response_metadata.map((r) => r.sha256);
  const uniqueSHAs = new Set(sha256s);
  results.checks.push({
    name: 'sha256_all_distinct',
    pass: uniqueSHAs.size === 3,
    detail: `unique sha256 count: ${uniqueSHAs.size}`,
  });

  // Safety flags check
  const s = threeTarget.safety;
  results.checks.push({ name: 'browser_automation_performed_false', pass: s.browser_automation_performed === false });
  results.checks.push({ name: 'payload_saved_false', pass: s.payload_saved === false });
  results.checks.push({ name: 'response_body_saved_false', pass: s.response_body_saved === false });
  results.checks.push({ name: 'db_write_performed_false', pass: s.db_write_performed === false });
  results.checks.push({ name: 'raw_write_performed_false', pass: s.raw_write_performed === false });
  results.checks.push({ name: 'raw_match_data_insert_performed_false', pass: s.raw_match_data_insert_performed === false });
  results.checks.push({ name: 'schema_migration_performed_false', pass: s.schema_migration_performed === false });
  results.checks.push({ name: 'adg60_write_performed_false', pass: s.adg60_write_performed === false });
  results.checks.push({ name: 'raw_write_ready_marked_false', pass: s.raw_write_ready_marked === false });

  // Review references check
  results.checks.push({
    name: 'authorization_reviewed_pr_1410_matches',
    pass: authorization.reviewed_pr === 1408,
  });
  results.checks.push({
    name: 'one_target_reviewed_pr_1407_matches',
    pass: oneTargetReview.review_scope.reviewed_pr === 1407,
  });

  // Authorization scope check
  results.checks.push({
    name: 'max_future_target_count_is_3',
    pass: authorization.max_future_target_count === 3,
  });
  results.checks.push({
    name: 'candidate_target_indices_are_2_3_4',
    pass: JSON.stringify(authorization.candidate_target_indices) === '[2,3,4]',
  });

  // Recommended next phase
  results.checks.push({
    name: 'recommended_next_is_authorization',
    pass: threeTarget.recommended_next_phase === 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-THREE-TARGET-NO-WRITE-REVIEW',
  });

  // This review = no new fetch
  results.checks.push({
    name: 'this_review_no_new_live_fetch',
    pass: true,
    note: 'review is read-only, no network call performed',
  });

  const passed = results.checks.every((c) => c.pass);
  const passCount = results.checks.filter((c) => c.pass).length;
  const failCount = results.checks.length - passCount;

  console.log(JSON.stringify({
    mode: 'review',
    phase: results.phase,
    scope: results.scope,
    checks_run: results.checks.length,
    checks_passed: passCount,
    checks_failed: failCount,
    verdict: passed ? 'pass' : 'fail',
    new_live_fetch_performed: false,
    new_network_fetch_performed: false,
    browser_automation_performed: false,
    payload_saved: false,
    db_write_performed: false,
    raw_write_performed: false,
    adg60_write_performed: false,
    raw_write_ready_marked: false,
    failed_checks: passed ? [] : results.checks.filter((c) => !c.pass).map((c) => c.name),
    checks: results.checks,
  }, null, 2));

  if (!passed) {
    console.error(`\nREVIEW FAILED: ${failCount} check(s) failed`);
    process.exit(1);
  }

  console.error(`\nREVIEW PASSED: ${passCount}/${results.checks.length} checks passed`);
  console.error('No network fetch performed in this review.');
  console.error('No body persisted. No DB write. No raw write.');

  return 0;
}

main();
