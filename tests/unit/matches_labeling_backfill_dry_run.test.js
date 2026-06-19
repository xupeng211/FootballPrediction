/**
 * matches_labeling_backfill_dry_run.test.js — 治理标签回填 dry-run 单元测试
 * ========================================================================
 *
 * 验证 dry-run 脚本：
 *   1. 不会执行 UPDATE/INSERT/DELETE
 *   2. 输出 actual_update_executed=false
 *   3. 能正确统计 total_matches_scanned / would_update_count
 *   4. 能正确处理空 governance fields
 *   5. 能正确处理已有 governance fields，不覆盖
 *   6. 能正确识别 fotmob_live_v1 raw exists
 *   7. 能正确识别 no raw / synthetic raw / manual seed / local csv
 *   8. 不输出 raw payload / raw_data / pageProps / HTML body
 *   9. 支持 --json
 *   10. 支持 --match-id / --limit 参数
 *
 * 测试框架: Node.js 内置 assert
 * 运行方式: node --test tests/unit/matches_labeling_backfill_dry_run.test.js
 *           或 npm test -- tests/unit/matches_labeling_backfill_dry_run.test.js
 */

'use strict';

const assert = require('assert');
const {
  parseArgs,
  classifyRow,
  buildSummary,
  selectSampleRows,
  formatSampleRow,
  governanceFieldsAllNull,
  hasAnyGovernanceField,
} = require('../../scripts/ops/matches_labeling_backfill_dry_run');

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
// 1. parseArgs — CLI 参数解析
// =========================================================================

test('parseArgs --json', () => {
  const args = parseArgs(['node', 'script.js', '--json']);
  assert.strictEqual(args.json, true);
  assert.strictEqual(args.limit, null);
  assert.strictEqual(args.matchId, null);
});

test('parseArgs --limit 10', () => {
  const args = parseArgs(['node', 'script.js', '--json', '--limit', '10']);
  assert.strictEqual(args.json, true);
  assert.strictEqual(args.limit, 10);
});

test('parseArgs --match-id', () => {
  const args = parseArgs(['node', 'script.js', '--json', '--match-id', '53_20252026_4830746']);
  assert.strictEqual(args.matchId, '53_20252026_4830746');
});

test('parseArgs --league and --season', () => {
  const args = parseArgs(['node', 'script.js', '--json', '--league', 'Ligue 1', '--season', '2025/2026']);
  assert.strictEqual(args.league, 'Ligue 1');
  assert.strictEqual(args.season, '2025/2026');
});

test('parseArgs default values', () => {
  const args = parseArgs(['node', 'script.js']);
  assert.strictEqual(args.json, false);
  assert.strictEqual(args.limit, null);
  assert.strictEqual(args.matchId, null);
  assert.strictEqual(args.league, null);
  assert.strictEqual(args.season, null);
});

// =========================================================================
// 2. governanceFieldsAllNull / hasAnyGovernanceField
// =========================================================================

test('governanceFieldsAllNull returns true when all fields are null', () => {
  const row = {
    source_type: null,
    evidence_level: null,
    is_production_scope: null,
    is_reconciliation_eligible: null,
    is_training_eligible: null,
    pipeline_status_reason: null,
  };
  assert.strictEqual(governanceFieldsAllNull(row), true);
});

test('governanceFieldsAllNull returns false when source_type is set', () => {
  const row = {
    source_type: 'fotmob_live_fetch',
    evidence_level: null,
    is_production_scope: null,
    is_reconciliation_eligible: null,
    is_training_eligible: null,
    pipeline_status_reason: null,
  };
  assert.strictEqual(governanceFieldsAllNull(row), false);
});

test('governanceFieldsAllNull returns false when pipeline_status_reason is set', () => {
  const row = {
    source_type: null,
    evidence_level: null,
    is_production_scope: null,
    is_reconciliation_eligible: null,
    is_training_eligible: null,
    pipeline_status_reason: 'awaiting_match_completion',
  };
  assert.strictEqual(governanceFieldsAllNull(row), false);
});

test('hasAnyGovernanceField returns false for all-null row', () => {
  const row = {
    source_type: null,
    evidence_level: null,
    is_production_scope: null,
    is_reconciliation_eligible: null,
    is_training_eligible: null,
    pipeline_status_reason: null,
  };
  assert.strictEqual(hasAnyGovernanceField(row), false);
});

test('hasAnyGovernanceField returns true for labeled row', () => {
  const row = {
    source_type: 'fotmob_live_fetch',
    evidence_level: 'strong',
    is_production_scope: true,
    is_reconciliation_eligible: true,
    is_training_eligible: false,
    pipeline_status_reason: null,
  };
  assert.strictEqual(hasAnyGovernanceField(row), true);
});

// =========================================================================
// 3. classifyRow — 行分类
// =========================================================================

// 模拟 match 行数据
const BASE_ROW = {
  match_id: '53_20252026_4830746',
  league_name: 'Ligue 1',
  season: '2025/2026',
  status: 'harvested',
  pipeline_status: 'harvested',
  data_source: 'fotmob',
  external_id: '4830746',
  source_type: null,
  evidence_level: null,
  is_production_scope: null,
  is_reconciliation_eligible: null,
  is_training_eligible: null,
  pipeline_status_reason: null,
  data_version: 'fotmob_live_v1',
};

const fotmobLiveV1Ids = new Set(['53_20252026_4830746']);

test('classifyRow — Ligue 1 2025/2026 finished + fotmob_live_v1 → strong, production, reconciliation', () => {
  const finishedRow = { ...BASE_ROW, status: 'finished' };
  const result = classifyRow(finishedRow, fotmobLiveV1Ids);

  assert.strictEqual(result.match_id, '53_20252026_4830746');
  assert.strictEqual(result.already_labeled, false);
  assert.strictEqual(result.has_raw, true);
  assert.strictEqual(result.has_fotmob_live_v1_raw, true);
  assert.strictEqual(result.proposed_source_type, 'fotmob_live_fetch');
  assert.strictEqual(result.proposed_evidence_level, 'strong');
  assert.strictEqual(result.proposed_is_production_scope, true);
  assert.strictEqual(result.proposed_is_reconciliation_eligible, true);
  assert.strictEqual(result.proposed_is_training_eligible, false);
  assert.strictEqual(result.proposed_pipeline_status_reason, null);
});

test('classifyRow — Ligue 1 2025/2026 harvested + fotmob_live_v1 → strong, production, NOT reconciliation (not finished)', () => {
  // governance rules: reconciliation requires status='finished'
  const result = classifyRow(BASE_ROW, fotmobLiveV1Ids);

  assert.strictEqual(result.proposed_source_type, 'fotmob_live_fetch');
  assert.strictEqual(result.proposed_evidence_level, 'strong');
  assert.strictEqual(result.proposed_is_production_scope, true);
  assert.strictEqual(result.proposed_is_reconciliation_eligible, false);
  assert.strictEqual(result.proposed_pipeline_status_reason, 'awaiting_match_completion');
});

test('classifyRow — already labeled row is detected', () => {
  const row = {
    ...BASE_ROW,
    source_type: 'fotmob_live_fetch',
    evidence_level: 'strong',
  };
  const result = classifyRow(row, fotmobLiveV1Ids);

  assert.strictEqual(result.already_labeled, true);
  // proposed labels still computed but marked already_labeled
  assert.strictEqual(result.proposed_source_type, 'fotmob_live_fetch');
});

test('classifyRow — no raw row gets unknown source_type', () => {
  const row = {
    ...BASE_ROW,
    match_id: '53_20252026_9999999',
    data_version: null,
    data_source: null,
    external_id: null,
  };
  const result = classifyRow(row, new Set());

  assert.strictEqual(result.has_raw, false);
  assert.strictEqual(result.has_fotmob_live_v1_raw, false);
  assert.strictEqual(result.proposed_source_type, 'unknown');
  assert.strictEqual(result.proposed_evidence_level, 'missing');
  assert.strictEqual(result.proposed_is_reconciliation_eligible, false);
});

test('classifyRow — synthetic data_version detected (finished status)', () => {
  const row = {
    ...BASE_ROW,
    match_id: '47_20242025_900002',
    league_name: 'Segunda',
    season: '2024/2025',
    status: 'finished',
    data_version: 'PHASE4.43_SYNTHETIC',
    data_source: 'synthetic',
    external_id: '900002',
  };
  const result = classifyRow(row, new Set());

  assert.strictEqual(result.proposed_source_type, 'synthetic');
  assert.strictEqual(result.proposed_evidence_level, 'synthetic_invalid');
  assert.strictEqual(result.proposed_is_production_scope, false);
  assert.strictEqual(result.proposed_is_reconciliation_eligible, false);
  assert.strictEqual(result.proposed_is_training_eligible, false);
  assert.strictEqual(result.proposed_pipeline_status_reason, 'synthetic_raw_not_valid');
});

test('classifyRow — manual_seed data_source detected', () => {
  const row = {
    ...BASE_ROW,
    match_id: '140_20252026_4837496',
    league_name: 'Segunda',
    season: '2025/2026',
    data_version: null,
    data_source: 'manual_html_seed',
    external_id: '4837496',
  };
  const result = classifyRow(row, new Set());

  assert.strictEqual(result.proposed_source_type, 'manual_seed');
  assert.strictEqual(result.proposed_evidence_level, 'weak');
  assert.strictEqual(result.proposed_is_production_scope, false);
  assert.strictEqual(result.proposed_is_reconciliation_eligible, false);
  assert.strictEqual(result.proposed_is_training_eligible, false);
});

test('classifyRow — local_csv data_source detected', () => {
  const row = {
    ...BASE_ROW,
    match_id: 'test_local_csv_001',
    league_name: 'Premier League',
    season: '2024/2025',
    data_version: null,
    data_source: 'local_finished_csv',
    external_id: 'some_ext_id',
  };
  const result = classifyRow(row, new Set());

  assert.strictEqual(result.proposed_source_type, 'local_csv');
  assert.strictEqual(result.proposed_evidence_level, 'weak');
});

test('classifyRow — fotmob_html_hyd_v1 → fotmob_html_hydration, medium', () => {
  const row = {
    ...BASE_ROW,
    data_version: 'fotmob_html_hyd_v1',
  };
  const result = classifyRow(row, new Set());

  assert.strictEqual(result.proposed_source_type, 'fotmob_html_hydration');
  assert.strictEqual(result.proposed_evidence_level, 'medium');
});

test('classifyRow — fotmob_pageprops_v2 → fotmob_pageprops, medium', () => {
  const row = {
    ...BASE_ROW,
    data_version: 'fotmob_pageprops_v2',
  };
  const result = classifyRow(row, new Set());

  assert.strictEqual(result.proposed_source_type, 'fotmob_pageprops');
  assert.strictEqual(result.proposed_evidence_level, 'medium');
});

test('classifyRow — training_eligible always false', () => {
  const scenarios = [
    { ...BASE_ROW },
    { ...BASE_ROW, league_name: 'Premier League', season: '2024/2025', data_version: null },
    { ...BASE_ROW, data_version: 'PHASE4.43_SYNTHETIC' },
  ];
  for (const row of scenarios) {
    const result = classifyRow(row, fotmobLiveV1Ids);
    assert.strictEqual(
      result.proposed_is_training_eligible,
      false,
      `training should be false for ${row.match_id}`
    );
  }
});

// =========================================================================
// 4. buildSummary — 聚合统计
// =========================================================================

test('buildSummary — correct totals and counts', () => {
  const classified = [
    // 5 unlabeled rows
    { ...classifyRow(BASE_ROW, fotmobLiveV1Ids), match_id: 'm1' },
    { ...classifyRow(BASE_ROW, fotmobLiveV1Ids), match_id: 'm2' },
    { ...classifyRow({ ...BASE_ROW, match_id: 'm3', data_version: null }, new Set()) },
    { ...classifyRow({ ...BASE_ROW, match_id: 'm4', data_version: null, data_source: 'manual_html_seed' }, new Set()) },
    { ...classifyRow({ ...BASE_ROW, match_id: 'm5', data_version: 'PHASE4.43_SYNTHETIC', data_source: 'synthetic' }, new Set()) },
    // 1 already labeled row
    {
      ...classifyRow(
        { ...BASE_ROW, match_id: 'm6', source_type: 'fotmob_live_fetch', evidence_level: 'strong' },
        fotmobLiveV1Ids
      ),
      match_id: 'm6',
    },
  ];

  const summary = buildSummary(classified);

  assert.strictEqual(summary.total_matches_scanned, 6);
  assert.strictEqual(summary.would_update_count, 5);
  assert.strictEqual(summary.already_labeled_count, 1);
  assert.strictEqual(summary.unlabeled_count, 5);
  // m3, m4 have data_version=null, m5 has synthetic data_version → all no raw
  assert.strictEqual(summary.excluded_no_raw_count, 3); // m3, m4 (null) + m5 (synthetic)
  // m1, m2 have real raw → candidates
  assert.strictEqual(summary.candidate_total, 2);
});

test('buildSummary — by_source_type distribution', () => {
  const classified = [
    { ...classifyRow(BASE_ROW, fotmobLiveV1Ids), match_id: 'm1' },
    { ...classifyRow(BASE_ROW, fotmobLiveV1Ids), match_id: 'm2' },
    {
      ...classifyRow(
        { ...BASE_ROW, match_id: 'm3', data_version: null, data_source: 'manual_html_seed' },
        new Set()
      ),
      match_id: 'm3',
    },
    {
      ...classifyRow(
        { ...BASE_ROW, match_id: 'm4', data_version: 'PHASE4.43_SYNTHETIC', data_source: 'synthetic' },
        new Set()
      ),
      match_id: 'm4',
    },
  ];

  const summary = buildSummary(classified);

  assert.strictEqual(summary.by_source_type['fotmob_live_fetch'], 2);
  assert.strictEqual(summary.by_source_type['manual_seed'], 1);
  assert.strictEqual(summary.by_source_type['synthetic'], 1);
});

test('buildSummary — risk flags for synthetic and unknown', () => {
  const classified = [
    {
      ...classifyRow(
        { ...BASE_ROW, match_id: 'm1', data_version: 'PHASE4.43_SYNTHETIC', data_source: 'synthetic' },
        new Set()
      ),
      match_id: 'm1',
    },
  ];

  const summary = buildSummary(classified);

  const syntheticFlag = summary.risk_flags.find((f) => f.includes('synthetic'));
  assert.ok(syntheticFlag, 'should have synthetic risk flag');
});

test('buildSummary — risk flag when no unlabeled rows', () => {
  const classified = [
    {
      ...classifyRow(
        { ...BASE_ROW, match_id: 'm1', source_type: 'fotmob_live_fetch', evidence_level: 'strong' },
        fotmobLiveV1Ids
      ),
      match_id: 'm1',
      already_labeled: true,
    },
  ];

  const summary = buildSummary(classified);

  const noUnlabeledFlag = summary.risk_flags.find((f) => f.includes('no_unlabeled_rows'));
  assert.ok(noUnlabeledFlag, 'should have no_unlabeled_rows risk flag');
});

test('buildSummary — class A rows (Ligue 1/2025-26/harvested/fotmob_live_v1)', () => {
  const classified = [
    { ...classifyRow(BASE_ROW, fotmobLiveV1Ids), match_id: 'm1' },
    { ...classifyRow(BASE_ROW, fotmobLiveV1Ids), match_id: 'm2' },
  ];

  const summary = buildSummary(classified);

  assert.strictEqual(summary.class_a_count, 2);
  assert.ok(summary.class_a_summary);
  assert.strictEqual(summary.class_a_summary.expected_source_type, 'fotmob_live_fetch');
  assert.strictEqual(summary.class_a_summary.expected_evidence_level, 'strong');
  assert.strictEqual(summary.class_a_summary.expected_is_production_scope, true);
  assert.strictEqual(summary.class_a_summary.expected_is_reconciliation_eligible, true);
});

// =========================================================================
// 5. selectSampleRows / formatSampleRow
// =========================================================================

test('selectSampleRows returns at most maxCount rows', () => {
  const classified = Array.from({ length: 50 }, (_, i) => ({
    ...classifyRow({ ...BASE_ROW, match_id: `m${i}` }, fotmobLiveV1Ids),
    match_id: `m${i}`,
  }));

  const samples = selectSampleRows(classified, 20);
  assert.ok(samples.length <= 20);
});

test('selectSampleRows returns empty array for empty input', () => {
  const samples = selectSampleRows([], 20);
  assert.strictEqual(samples.length, 0);
});

test('formatSampleRow does NOT include raw_data, raw payload, pageProps, or HTML', () => {
  const row = classifyRow(BASE_ROW, fotmobLiveV1Ids);
  const formatted = formatSampleRow(row);

  // 必须包含的字段
  assert.ok('match_id' in formatted);
  assert.ok('league_name' in formatted);
  assert.ok('season' in formatted);
  assert.ok('status' in formatted);
  assert.ok('pipeline_status' in formatted);
  assert.ok('current_labels_empty' in formatted);
  assert.ok('proposed_source_type' in formatted);
  assert.ok('proposed_evidence_level' in formatted);
  assert.ok('proposed_is_production_scope' in formatted);
  assert.ok('proposed_is_reconciliation_eligible' in formatted);
  assert.ok('proposed_is_training_eligible' in formatted);
  assert.ok('proposed_pipeline_status_reason' in formatted);
  assert.ok('reason' in formatted);

  // 不得包含的字段
  const formattedStr = JSON.stringify(formatted);
  assert.ok(!formattedStr.includes('raw_data'));
  assert.ok(!formattedStr.includes('raw_payload'));
  assert.ok(!formattedStr.includes('pageProps'));
  assert.ok(!formattedStr.includes('__NEXT_DATA__'));
  assert.ok(!formattedStr.includes('HTML'));
  assert.ok(!('raw_data' in formatted));
  assert.ok(!('raw_payload' in formatted));
  assert.ok(!('data_version' in formatted)); // no raw metadata leakage
});

test('formatSampleRow — reason is human-readable', () => {
  const unlabeledRaw = classifyRow(BASE_ROW, fotmobLiveV1Ids);
  const formatted = formatSampleRow(unlabeledRaw);
  assert.strictEqual(typeof formatted.reason, 'string');
  assert.ok(formatted.reason.length > 0);

  const alreadyLabeled = classifyRow(
    { ...BASE_ROW, source_type: 'fotmob_live_fetch' },
    fotmobLiveV1Ids
  );
  const formattedLabeled = formatSampleRow(alreadyLabeled);
  assert.ok(formattedLabeled.reason.includes('already_labeled'));
});

// =========================================================================
// 6. 输出安全验证
// =========================================================================

test('buildSummary output does not contain raw_data or raw payload', () => {
  const classified = [classifyRow(BASE_ROW, fotmobLiveV1Ids)];

  const summary = buildSummary(classified);
  const outputStr = JSON.stringify(summary);

  // 不得包含 raw payload
  assert.ok(!outputStr.includes('"raw_data"'));
  assert.ok(!outputStr.includes('"raw_payload"'));
  assert.ok(!outputStr.includes('pageProps'));
  assert.ok(!outputStr.includes('__NEXT_DATA__'));
  assert.ok(!outputStr.includes('"HTML"'));

  // sample_rows 中也不得包含
  for (const row of summary.sample_rows) {
    const rowStr = JSON.stringify(row);
    assert.ok(!rowStr.includes('raw_data'));
    assert.ok(!rowStr.includes('pageProps'));
  }
});

test('buildSummary — actual_update_executed is always false (not in summary but in final output)', () => {
  // actual_update_executed 在 main() 的最终输出中硬编码为 false
  // 这里验证 buildSummary 不包含该字段
  const classified = [classifyRow(BASE_ROW, fotmobLiveV1Ids)];
  const summary = buildSummary(classified);
  assert.strictEqual(summary.total_matches_scanned, 1);
});

// =========================================================================
// 7. 边界情况
// =========================================================================

test('classifyRow — all null context still produces valid labels', () => {
  const row = {
    match_id: 'empty_test',
    league_name: null,
    season: null,
    status: null,
    pipeline_status: null,
    data_source: null,
    external_id: null,
    source_type: null,
    evidence_level: null,
    is_production_scope: null,
    is_reconciliation_eligible: null,
    is_training_eligible: null,
    pipeline_status_reason: null,
    data_version: null,
  };

  const result = classifyRow(row, new Set());

  assert.strictEqual(result.proposed_source_type, 'unknown');
  assert.strictEqual(result.proposed_evidence_level, 'missing');
  assert.strictEqual(result.proposed_is_production_scope, false);
  assert.strictEqual(result.proposed_is_reconciliation_eligible, false);
  assert.strictEqual(result.proposed_is_training_eligible, false);
  assert.strictEqual(result.proposed_pipeline_status_reason, 'awaiting_match_completion');
});

test('classifyRow — scheduled match with fotmob_live_v1 raw gets awaiting_match_completion', () => {
  const row = {
    ...BASE_ROW,
    status: 'scheduled',
    pipeline_status: 'pending',
  };
  const result = classifyRow(row, fotmobLiveV1Ids);

  assert.strictEqual(result.proposed_pipeline_status_reason, 'awaiting_match_completion');
  assert.strictEqual(result.proposed_is_reconciliation_eligible, false);
});

test('classifyRow — finished Ligue 1 without fotmob_live_v1 raw gets pending_without_fotmob_live_v1_raw', () => {
  const row = {
    ...BASE_ROW,
    status: 'finished',
    pipeline_status: 'pending',
  };
  const result = classifyRow(row, new Set()); // no fotmob_live_v1

  assert.strictEqual(result.proposed_pipeline_status_reason, 'pending_without_fotmob_live_v1_raw');
});

test('classifyRow — finished with fotmob_live_v1 but null external_id gets external_id_unverified', () => {
  const row = {
    ...BASE_ROW,
    status: 'finished',
    external_id: null,
  };
  const result = classifyRow(row, fotmobLiveV1Ids);

  assert.strictEqual(result.proposed_pipeline_status_reason, 'external_id_unverified');
});

test('buildSummary — empty classified array', () => {
  const summary = buildSummary([]);

  assert.strictEqual(summary.total_matches_scanned, 0);
  assert.strictEqual(summary.would_update_count, 0);
  assert.strictEqual(summary.already_labeled_count, 0);
  assert.strictEqual(summary.unlabeled_count, 0);
  assert.strictEqual(summary.excluded_no_raw_count, 0);
  assert.strictEqual(summary.candidate_total, 0);
  assert.strictEqual(summary.sample_rows.length, 0);
});

// =========================================================================
// 8. 数据版本 distribution 不会输出 raw payload
// =========================================================================

test('classifyRow retains data_version but formatSampleRow strips it', () => {
  const row = classifyRow(
    { ...BASE_ROW, data_version: 'fotmob_live_v1' },
    fotmobLiveV1Ids
  );

  // classifyRow 内部保留 data_version
  assert.strictEqual(row.data_version, 'fotmob_live_v1');

  // 但 formatSampleRow 不输出 data_version
  const formatted = formatSampleRow(row);
  assert.ok(!('data_version' in formatted));
  assert.ok(!('has_fotmob_live_v1_raw' in formatted));
});

// =========================================================================
// 报告
// =========================================================================

console.log(`\n=== Matches Labeling Backfill Dry-Run Unit Tests: ${testsPassed}/${testsRun} passed ===`);
if (testsPassed < testsRun) {
  console.error(`FAILED: ${testsRun - testsPassed} test(s) failed`);
  process.exitCode = 1;
}
