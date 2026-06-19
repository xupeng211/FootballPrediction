/**
 * training_eligibility_dry_run.test.js — 训练准入 dry-run 单元测试
 * ================================================================
 *
 * 验证：
 *   1. evaluateTrainingEligibility 各规则路径
 *   2. buildSummary 正确统计
 *   3. 禁止进训练的类型
 *   4. 输出不包含 raw payload
 *   5. actual_update_executed=false
 */

'use strict';

const assert = require('assert');
const {
  parseArgs,
  evaluateTrainingEligibility,
  buildSummary,
  TRAINING_VALID_SOURCE_TYPES,
  TRAINING_VALID_PIPELINE_STATUSES,
  TRAINING_FORBIDDEN_EVIDENCE,
} = require('../../scripts/ops/training_eligibility_dry_run');

let testsRun = 0;
let testsPassed = 0;

function test(name, fn) {
  testsRun++;
  try {
    fn();
    testsPassed++;
  } catch (e) {
    console.error(`\n  FAIL [${name}]: ${e.message}`);
    throw e;
  }
}

// =========================================================================
// 1. parseArgs
// =========================================================================

test('parseArgs --json', () => {
  const args = parseArgs(['node', 'script.js', '--json']);
  assert.strictEqual(args.json, true);
  assert.strictEqual(args.matchId, null);
});

test('parseArgs --match-id', () => {
  const args = parseArgs(['node', 'script.js', '--json', '--match-id', '53_20252026_4830458']);
  assert.strictEqual(args.matchId, '53_20252026_4830458');
});

test('parseArgs defaults', () => {
  const args = parseArgs(['node', 'script.js']);
  assert.strictEqual(args.json, false);
  assert.strictEqual(args.matchId, null);
});

// =========================================================================
// 2. Constants
// =========================================================================

test('TRAINING_VALID_SOURCE_TYPES includes fotmob sources', () => {
  assert.ok(TRAINING_VALID_SOURCE_TYPES.has('fotmob_live_fetch'));
  assert.ok(TRAINING_VALID_SOURCE_TYPES.has('fotmob_html_hydration'));
  assert.ok(TRAINING_VALID_SOURCE_TYPES.has('fotmob_pageprops'));
});

test('TRAINING_VALID_SOURCE_TYPES excludes synthetic', () => {
  assert.ok(!TRAINING_VALID_SOURCE_TYPES.has('synthetic'));
  assert.ok(!TRAINING_VALID_SOURCE_TYPES.has('manual_seed'));
  assert.ok(!TRAINING_VALID_SOURCE_TYPES.has('local_csv'));
  assert.ok(!TRAINING_VALID_SOURCE_TYPES.has('unknown'));
});

test('TRAINING_FORBIDDEN_EVIDENCE includes synthetic_invalid and missing', () => {
  assert.ok(TRAINING_FORBIDDEN_EVIDENCE.has('synthetic_invalid'));
  assert.ok(TRAINING_FORBIDDEN_EVIDENCE.has('missing'));
});

// =========================================================================
// 3. evaluateTrainingEligibility — PASS cases
// =========================================================================

const LIGUE1_ROW = {
  match_id: '53_20252026_4830458',
  league_name: 'Ligue 1',
  season: '2025/2026',
  status: 'finished',
  pipeline_status: 'harvested',
  home_score: 2,
  away_score: 1,
  source_type: 'fotmob_live_fetch',
  evidence_level: 'strong',
  is_production_scope: true,
  is_reconciliation_eligible: true,
  pipeline_status_reason: null,
};

test('Ligue 1 finished + fotmob_live_fetch → eligible (conditional)', () => {
  const result = evaluateTrainingEligibility(LIGUE1_ROW);
  assert.strictEqual(result.eligible, true);
  assert.ok(result.reason.includes('all_rules_passed'));
});

// =========================================================================
// 4. evaluateTrainingEligibility — FAIL cases by rule
// =========================================================================

test('Rule 1: synthetic source_type → forbidden_evidence', () => {
  const row = { ...LIGUE1_ROW, source_type: 'synthetic', evidence_level: 'synthetic_invalid' };
  const result = evaluateTrainingEligibility(row);
  assert.strictEqual(result.eligible, false);
  assert.ok(result.reason.includes('forbidden_evidence'));
});

test('Rule 1: unknown source_type → invalid_source_type', () => {
  const row = { ...LIGUE1_ROW, source_type: 'unknown', evidence_level: 'missing' };
  const result = evaluateTrainingEligibility(row);
  assert.strictEqual(result.eligible, false);
  assert.ok(result.reason.includes('forbidden_evidence'));
});

test('Rule 1: manual_seed source_type → invalid_source_type', () => {
  const row = { ...LIGUE1_ROW, source_type: 'manual_seed', evidence_level: 'weak' };
  const result = evaluateTrainingEligibility(row);
  assert.strictEqual(result.eligible, false);
  assert.ok(result.reason.includes('invalid_source_type'));
});

test('Rule 1: local_csv source_type → invalid_source_type', () => {
  const row = { ...LIGUE1_ROW, source_type: 'local_csv', evidence_level: 'weak' };
  const result = evaluateTrainingEligibility(row);
  assert.strictEqual(result.eligible, false);
  assert.ok(result.reason.includes('invalid_source_type'));
});

test('Rule 2: scheduled match → match_not_finished', () => {
  const row = { ...LIGUE1_ROW, status: 'scheduled' };
  const result = evaluateTrainingEligibility(row);
  assert.strictEqual(result.eligible, false);
  assert.ok(result.reason.includes('match_not_finished'));
});

test('Rule 2b: finished but no scores → no_valid_scores', () => {
  const row = { ...LIGUE1_ROW, home_score: null, away_score: null };
  const result = evaluateTrainingEligibility(row);
  assert.strictEqual(result.eligible, false);
  assert.ok(result.reason.includes('no_valid_scores'));
});

test('Rule 2b: finished but only home_score missing → no_valid_scores', () => {
  const row = { ...LIGUE1_ROW, home_score: null, away_score: 2 };
  const result = evaluateTrainingEligibility(row);
  assert.strictEqual(result.eligible, false);
  assert.ok(result.reason.includes('no_valid_scores'));
});

test('Rule 4: non-production scope → non_production_scope', () => {
  const row = { ...LIGUE1_ROW, is_production_scope: false };
  const result = evaluateTrainingEligibility(row);
  assert.strictEqual(result.eligible, false);
  assert.ok(result.reason.includes('non_production_scope'));
});

test('Rule 5: pipeline_status=failed → pipeline_not_complete', () => {
  const row = { ...LIGUE1_ROW, pipeline_status: 'failed' };
  const result = evaluateTrainingEligibility(row);
  assert.strictEqual(result.eligible, false);
  assert.ok(result.reason.includes('pipeline_not_complete'));
});

test('Rule 5: pipeline_status=pending → pipeline_not_complete', () => {
  const row = { ...LIGUE1_ROW, pipeline_status: 'pending' };
  const result = evaluateTrainingEligibility(row);
  assert.strictEqual(result.eligible, false);
  assert.ok(result.reason.includes('pipeline_not_complete'));
});

test('Rule 5: pipeline_status_reason not null → pipeline_blocked', () => {
  const row = { ...LIGUE1_ROW, pipeline_status_reason: 'synthetic_raw_not_valid' };
  const result = evaluateTrainingEligibility(row);
  assert.strictEqual(result.eligible, false);
  assert.ok(result.reason.includes('pipeline_blocked'));
});

test('Rule 6: not reconciliation_eligible → not_reconciliation_eligible', () => {
  const row = { ...LIGUE1_ROW, is_reconciliation_eligible: false };
  const result = evaluateTrainingEligibility(row);
  assert.strictEqual(result.eligible, false);
  assert.ok(result.reason.includes('not_reconciliation_eligible'));
});

// =========================================================================
// 5. evaluateTrainingEligibility — Priority order
// =========================================================================

test('Priority: evidence gate checked before match completion', () => {
  // synthetic + scheduled → should report forbidden_evidence, not match_not_finished
  const row = {
    ...LIGUE1_ROW,
    source_type: 'synthetic',
    evidence_level: 'synthetic_invalid',
    status: 'scheduled',
  };
  const result = evaluateTrainingEligibility(row);
  assert.strictEqual(result.eligible, false);
  assert.ok(result.reason.includes('forbidden_evidence'));
});

// =========================================================================
// 6. buildSummary
// =========================================================================

function makeRow(overrides = {}) {
  return {
    match_id: 'test_001',
    league_name: 'Ligue 1',
    season: '2025/2026',
    status: 'finished',
    pipeline_status: 'harvested',
    home_score: 2,
    away_score: 1,
    source_type: 'fotmob_live_fetch',
    evidence_level: 'strong',
    is_production_scope: true,
    is_reconciliation_eligible: true,
    is_training_eligible: false,
    pipeline_status_reason: null,
    ...overrides,
  };
}

test('buildSummary — correct totals for all-eligible set', () => {
  const rows = [
    makeRow({ match_id: 'm1' }),
    makeRow({ match_id: 'm2' }),
    makeRow({ match_id: 'm3' }),
  ];
  const summary = buildSummary(rows);
  assert.strictEqual(summary.total_matches_scanned, 3);
  assert.strictEqual(summary.would_set_true_count, 3);
  assert.strictEqual(summary.would_keep_false_count, 0);
  assert.strictEqual(summary.current_training_eligible_true, 0);
  assert.strictEqual(summary.current_training_eligible_false, 3);
});

test('buildSummary — mixed eligible and ineligible', () => {
  const rows = [
    makeRow({ match_id: 'm1' }),
    makeRow({ match_id: 'm2', source_type: 'synthetic', evidence_level: 'synthetic_invalid' }),
    makeRow({ match_id: 'm3', status: 'scheduled' }),
  ];
  const summary = buildSummary(rows);
  assert.strictEqual(summary.would_set_true_count, 1);
  assert.strictEqual(summary.would_keep_false_count, 2);
  assert.ok(summary.by_reason['forbidden_evidence: synthetic_invalid']);
  assert.ok(summary.by_reason['match_not_finished: status=scheduled']);
});

test('buildSummary — by_reason aggregation', () => {
  const rows = [
    makeRow({ match_id: 'm1' }),
    makeRow({ match_id: 'm2', source_type: 'synthetic', evidence_level: 'synthetic_invalid' }),
    makeRow({ match_id: 'm3', source_type: 'synthetic', evidence_level: 'synthetic_invalid' }),
    makeRow({ match_id: 'm4', status: 'scheduled' }),
  ];
  const summary = buildSummary(rows);
  assert.strictEqual(summary.by_reason['forbidden_evidence: synthetic_invalid'], 2);
  assert.strictEqual(summary.by_reason['match_not_finished: status=scheduled'], 1);
});

test('buildSummary — mode and actual_update_executed', () => {
  const summary = buildSummary([makeRow()]);
  assert.strictEqual(summary.mode, 'dry_run');
  assert.strictEqual(summary.actual_update_executed, false);
});

test('buildSummary — risk flags include leakage policy note', () => {
  const summary = buildSummary([makeRow()]);
  const leakageNote = summary.risk_flags.find((f) => f.includes('leakage policy'));
  assert.ok(leakageNote, 'should note leakage policy is conditional');
});

test('buildSummary — no_raw_excluded_false captures synthetic rows', () => {
  const rows = [
    makeRow({ match_id: '53_xxx' }),
    makeRow({
      match_id: '140_20252026_4837496',
      league_name: 'Segunda División',
      season: '2025/2026',
      status: 'scheduled',
      source_type: 'synthetic',
      evidence_level: 'synthetic_invalid',
      is_production_scope: false,
      is_reconciliation_eligible: false,
      home_score: null,
      away_score: null,
    }),
    makeRow({
      match_id: '47_20242025_900002',
      league_name: 'Segunda',
      season: '2024/2025',
      status: 'finished',
      source_type: 'synthetic',
      evidence_level: 'synthetic_invalid',
      is_production_scope: false,
      is_reconciliation_eligible: false,
      pipeline_status_reason: 'synthetic_raw_not_valid',
    }),
  ];
  const summary = buildSummary(rows);
  assert.strictEqual(summary.no_raw_excluded_false.length, 2);
  assert.strictEqual(summary.would_keep_false_count, 2);
});

// =========================================================================
// 7. Output safety
// =========================================================================

test('buildSummary output contains no raw_data or raw payload', () => {
  const summary = buildSummary([makeRow()]);
  const str = JSON.stringify(summary);
  assert.ok(!str.includes('raw_data'));
  assert.ok(!str.includes('raw_payload'));
  assert.ok(!str.includes('pageProps'));
  assert.ok(!str.includes('__NEXT_DATA__'));
});

// =========================================================================
// 报告
// =========================================================================

console.log(`\n=== Training Eligibility Dry-Run Unit Tests: ${testsPassed}/${testsRun} passed ===`);
if (testsPassed < testsRun) {
  console.error(`FAILED: ${testsRun - testsPassed} test(s) failed`);
  process.exitCode = 1;
}
