/**
 * MatchLabelingGovernance.test.js - 比赛治理标签计算模块 单元测试
 * =================================================================
 *
 * 覆盖 V26.7 标签推导规则的所有路径：
 *   - 7 种 source_type / evidence_level 映射
 *   - production scope 判断
 *   - reconciliation eligibility 判断
 *   - training eligibility（保守 false）
 *   - pipeline_status_reason 多个分支
 *   - computeGovernanceLabels 主入口
 *
 * 测试框架: Node.js 内置 assert
 * 运行方式: node --test tests/unit/MatchLabelingGovernance.test.js
 *           或 npm test -- tests/unit/MatchLabelingGovernance.test.js
 */

'use strict';

const assert = require('assert');
const {
  computeSourceType,
  computeEvidenceLevel,
  computeProductionScope,
  computeReconciliationEligibility,
  computeTrainingEligibility,
  computePipelineStatusReason,
  computeGovernanceLabels,
  DATA_VERSION_TO_SOURCE_TYPE,
  EVIDENCE_LEVEL_MAP,
} = require('../../src/infrastructure/services/MatchLabelingGovernance');

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
// 1. computeSourceType — data_version 直接映射
// =========================================================================

test('fotmob_live_v1 → source_type=fotmob_live_fetch', () => {
  assert.strictEqual(
    computeSourceType({ dataVersion: 'fotmob_live_v1' }),
    'fotmob_live_fetch'
  );
});

test('fotmob_html_hyd_v1 → source_type=fotmob_html_hydration', () => {
  assert.strictEqual(
    computeSourceType({ dataVersion: 'fotmob_html_hyd_v1' }),
    'fotmob_html_hydration'
  );
});

test('fotmob_pageprops_v2 → source_type=fotmob_pageprops', () => {
  assert.strictEqual(
    computeSourceType({ dataVersion: 'fotmob_pageprops_v2' }),
    'fotmob_pageprops'
  );
});

test('PHASE4.43_SYNTHETIC → source_type=synthetic', () => {
  assert.strictEqual(
    computeSourceType({ dataVersion: 'PHASE4.43_SYNTHETIC' }),
    'synthetic'
  );
});

test('PHASE4.23 → source_type=synthetic (phase pattern)', () => {
  assert.strictEqual(
    computeSourceType({ dataVersion: 'PHASE4.23' }),
    'synthetic'
  );
});

test('synthetic_v1 → source_type=synthetic (synthetic prefix)', () => {
  assert.strictEqual(
    computeSourceType({ dataVersion: 'synthetic_v1' }),
    'synthetic'
  );
});

// =========================================================================
// 2. computeSourceType — data_source 兜底映射
// =========================================================================

test('manual_html_seed → source_type=manual_seed (via dataSource)', () => {
  assert.strictEqual(
    computeSourceType({ dataSource: 'manual_html_seed' }),
    'manual_seed'
  );
});

test('local_finished_csv → source_type=local_csv (via dataSource)', () => {
  assert.strictEqual(
    computeSourceType({ dataSource: 'local_finished_csv' }),
    'local_csv'
  );
});

test('dataSource synthetic_* pattern → source_type=synthetic', () => {
  assert.strictEqual(
    computeSourceType({ dataSource: 'synthetic_local_fixture' }),
    'synthetic'
  );
});

// =========================================================================
// 3. computeSourceType — unknown 回退
// =========================================================================

test('unknown dataVersion → source_type=unknown', () => {
  assert.strictEqual(
    computeSourceType({ dataVersion: 'some_future_v9' }),
    'unknown'
  );
});

test('missing both dataVersion and dataSource → source_type=unknown', () => {
  assert.strictEqual(
    computeSourceType({}),
    'unknown'
  );
});

test('null/undefined context → source_type=unknown', () => {
  assert.strictEqual(computeSourceType(), 'unknown');
  assert.strictEqual(computeSourceType(null), 'unknown');
  assert.strictEqual(computeSourceType({ dataVersion: null, dataSource: null }), 'unknown');
});

// =========================================================================
// 4. computeEvidenceLevel
// =========================================================================

test('fotmob_live_fetch → evidence_level=strong', () => {
  assert.strictEqual(computeEvidenceLevel('fotmob_live_fetch'), 'strong');
});

test('fotmob_html_hydration → evidence_level=medium', () => {
  assert.strictEqual(computeEvidenceLevel('fotmob_html_hydration'), 'medium');
});

test('fotmob_pageprops → evidence_level=medium', () => {
  assert.strictEqual(computeEvidenceLevel('fotmob_pageprops'), 'medium');
});

test('manual_seed → evidence_level=weak', () => {
  assert.strictEqual(computeEvidenceLevel('manual_seed'), 'weak');
});

test('local_csv → evidence_level=weak', () => {
  assert.strictEqual(computeEvidenceLevel('local_csv'), 'weak');
});

test('synthetic → evidence_level=synthetic_invalid', () => {
  assert.strictEqual(computeEvidenceLevel('synthetic'), 'synthetic_invalid');
});

test('unknown → evidence_level=missing', () => {
  assert.strictEqual(computeEvidenceLevel('unknown'), 'missing');
});

test('garbage input → evidence_level=missing', () => {
  assert.strictEqual(computeEvidenceLevel('not_a_real_type'), 'missing');
  assert.strictEqual(computeEvidenceLevel(''), 'missing');
});

// =========================================================================
// 5. computeProductionScope
// =========================================================================

test('Ligue 1 / 2025/2026 → production_scope=true', () => {
  assert.strictEqual(
    computeProductionScope({ leagueName: 'Ligue 1', season: '2025/2026' }),
    true
  );
});

test('Segunda / 2024/2025 → production_scope=false (non-production league)', () => {
  assert.strictEqual(
    computeProductionScope({ leagueName: 'Segunda', season: '2024/2025' }),
    false
  );
});

test('Ligue 1 / 2024/2025 → production_scope=false (wrong season)', () => {
  assert.strictEqual(
    computeProductionScope({ leagueName: 'Ligue 1', season: '2024/2025' }),
    false
  );
});

test('Premier League / 2025/2026 → production_scope=false (non-production league)', () => {
  assert.strictEqual(
    computeProductionScope({ leagueName: 'Premier League', season: '2025/2026' }),
    false
  );
});

test('missing league/season → production_scope=false', () => {
  assert.strictEqual(computeProductionScope({}), false);
  assert.strictEqual(computeProductionScope({ leagueName: 'Ligue 1' }), false);
  assert.strictEqual(computeProductionScope({ season: '2025/2026' }), false);
});

// =========================================================================
// 6. computeReconciliationEligibility
// =========================================================================

test('finished + fotmob_live_v1 + strong + production → reconciliation=true', () => {
  assert.strictEqual(
    computeReconciliationEligibility({
      status: 'finished',
      hasFotmobLiveV1Raw: true,
      evidenceLevel: 'strong',
      isProductionScope: true,
    }),
    true
  );
});

test('scheduled (not finished) → reconciliation=false', () => {
  assert.strictEqual(
    computeReconciliationEligibility({
      status: 'scheduled',
      hasFotmobLiveV1Raw: true,
      evidenceLevel: 'strong',
      isProductionScope: true,
    }),
    false
  );
});

test('finished + no fotmob_live_v1 raw → reconciliation=false', () => {
  assert.strictEqual(
    computeReconciliationEligibility({
      status: 'finished',
      hasFotmobLiveV1Raw: false,
      evidenceLevel: 'strong',
      isProductionScope: true,
    }),
    false
  );
});

test('finished + fotmob_live_v1 + medium evidence → reconciliation=false', () => {
  assert.strictEqual(
    computeReconciliationEligibility({
      status: 'finished',
      hasFotmobLiveV1Raw: true,
      evidenceLevel: 'medium',
      isProductionScope: true,
    }),
    false
  );
});

test('finished + fotmob_live_v1 + strong + non-production → reconciliation=false', () => {
  assert.strictEqual(
    computeReconciliationEligibility({
      status: 'finished',
      hasFotmobLiveV1Raw: true,
      evidenceLevel: 'strong',
      isProductionScope: false,
    }),
    false
  );
});

test('all false defaults → reconciliation=false', () => {
  assert.strictEqual(computeReconciliationEligibility({}), false);
});

// =========================================================================
// 7. computeTrainingEligibility — 保守 false
// =========================================================================

test('training_eligible always false (conservative default)', () => {
  assert.strictEqual(computeTrainingEligibility(), false);
  assert.strictEqual(computeTrainingEligibility({ anything: 'yes' }), false);
  assert.strictEqual(
    computeTrainingEligibility({ status: 'finished', isProductionScope: true }),
    false
  );
});

// =========================================================================
// 8. computePipelineStatusReason
// =========================================================================

test('scheduled → pipeline_status_reason=awaiting_match_completion', () => {
  assert.strictEqual(
    computePipelineStatusReason({
      status: 'scheduled',
      pipelineStatus: 'pending',
      sourceType: 'fotmob_live_fetch',
      isProductionScope: true,
    }),
    'awaiting_match_completion'
  );
});

test('in_progress → pipeline_status_reason=awaiting_match_completion', () => {
  assert.strictEqual(
    computePipelineStatusReason({
      status: 'in_progress',
      pipelineStatus: 'pending',
      sourceType: 'fotmob_live_fetch',
      isProductionScope: true,
    }),
    'awaiting_match_completion'
  );
});

test('synthetic → pipeline_status_reason=synthetic_raw_not_valid', () => {
  assert.strictEqual(
    computePipelineStatusReason({
      status: 'finished',
      pipelineStatus: 'pending',
      sourceType: 'synthetic',
      isProductionScope: true,
    }),
    'synthetic_raw_not_valid'
  );
});

test('non-production league → pipeline_status_reason=non_production_league', () => {
  assert.strictEqual(
    computePipelineStatusReason({
      status: 'finished',
      pipelineStatus: 'pending',
      sourceType: 'fotmob_live_fetch',
      isProductionScope: false,
    }),
    'non_production_league'
  );
});

test('pending + no fotmob_live_v1 raw → pending_without_fotmob_live_v1_raw', () => {
  assert.strictEqual(
    computePipelineStatusReason({
      status: 'finished',
      pipelineStatus: 'pending',
      hasFotmobLiveV1Raw: false,
      sourceType: 'unknown',
      isProductionScope: true,
    }),
    'pending_without_fotmob_live_v1_raw'
  );
});

test('missing external_id → external_id_unverified', () => {
  assert.strictEqual(
    computePipelineStatusReason({
      status: 'finished',
      pipelineStatus: 'pending',
      hasFotmobLiveV1Raw: true,
      sourceType: 'fotmob_live_fetch',
      isProductionScope: true,
      externalId: '',
    }),
    'external_id_unverified'
  );
});

test('null external_id → external_id_unverified', () => {
  assert.strictEqual(
    computePipelineStatusReason({
      status: 'finished',
      pipelineStatus: 'pending',
      hasFotmobLiveV1Raw: true,
      sourceType: 'fotmob_live_fetch',
      isProductionScope: true,
      externalId: null,
    }),
    'external_id_unverified'
  );
});

test('all conditions met → pipeline_status_reason=null', () => {
  assert.strictEqual(
    computePipelineStatusReason({
      status: 'finished',
      pipelineStatus: 'harvested',
      hasFotmobLiveV1Raw: true,
      sourceType: 'fotmob_live_fetch',
      isProductionScope: true,
      externalId: 'valid_ext_123',
    }),
    null
  );
});

test('failed pipeline_status with unfinished status → skips awaiting_match_completion', () => {
  // failed/skipped should NOT be classified as awaiting_match_completion
  // With hasFotmobLiveV1Raw unset, it lands on pending_without_fotmob_live_v1_raw
  assert.strictEqual(
    computePipelineStatusReason({
      status: 'scheduled',
      pipelineStatus: 'failed',
      sourceType: 'fotmob_live_fetch',
      isProductionScope: true,
    }),
    'pending_without_fotmob_live_v1_raw'
  );
});

// =========================================================================
// 9. computeGovernanceLabels — 主入口集成测试
// =========================================================================

test('fotmob_live_v1 Ligue 1 2025/2026 finished → 完整标签', () => {
  const labels = computeGovernanceLabels({
    dataVersion: 'fotmob_live_v1',
    dataSource: 'fotmob',
    leagueName: 'Ligue 1',
    season: '2025/2026',
    status: 'finished',
    pipelineStatus: 'harvested',
    hasFotmobLiveV1Raw: true,
    externalId: '4451815',
  });

  assert.strictEqual(labels.source_type, 'fotmob_live_fetch');
  assert.strictEqual(labels.evidence_level, 'strong');
  assert.strictEqual(labels.is_production_scope, true);
  assert.strictEqual(labels.is_reconciliation_eligible, true);
  assert.strictEqual(labels.is_training_eligible, false);
  assert.strictEqual(labels.pipeline_status_reason, null);
});

test('fotmob_html_hyd_v1 Ligue 1 2025/2026 finished → medium, no reconciliation', () => {
  const labels = computeGovernanceLabels({
    dataVersion: 'fotmob_html_hyd_v1',
    leagueName: 'Ligue 1',
    season: '2025/2026',
    status: 'finished',
    pipelineStatus: 'pending',
    hasFotmobLiveV1Raw: false,
    externalId: '4451815',
  });

  assert.strictEqual(labels.source_type, 'fotmob_html_hydration');
  assert.strictEqual(labels.evidence_level, 'medium');
  assert.strictEqual(labels.is_production_scope, true);
  assert.strictEqual(labels.is_reconciliation_eligible, false); // medium evidence
  assert.strictEqual(labels.is_training_eligible, false);
  assert.strictEqual(labels.pipeline_status_reason, 'pending_without_fotmob_live_v1_raw');
});

test('fotmob_pageprops_v2 → medium evidence', () => {
  const labels = computeGovernanceLabels({
    dataVersion: 'fotmob_pageprops_v2',
    leagueName: 'Ligue 1',
    season: '2025/2026',
    status: 'finished',
    pipelineStatus: 'pending',
    hasFotmobLiveV1Raw: false,
    externalId: '4451815',
  });

  assert.strictEqual(labels.source_type, 'fotmob_pageprops');
  assert.strictEqual(labels.evidence_level, 'medium');
  assert.strictEqual(labels.is_reconciliation_eligible, false);
});

test('manual_html_seed → weak evidence', () => {
  const labels = computeGovernanceLabels({
    dataSource: 'manual_html_seed',
    leagueName: 'Ligue 1',
    season: '2025/2026',
    status: 'finished',
    pipelineStatus: 'pending',
    hasFotmobLiveV1Raw: false,
    externalId: '4451815',
  });

  assert.strictEqual(labels.source_type, 'manual_seed');
  assert.strictEqual(labels.evidence_level, 'weak');
  assert.strictEqual(labels.is_reconciliation_eligible, false);
});

test('local_finished_csv → weak evidence', () => {
  const labels = computeGovernanceLabels({
    dataSource: 'local_finished_csv',
    leagueName: 'Segunda',
    season: '2024/2025',
    status: 'finished',
    pipelineStatus: 'pending',
    hasFotmobLiveV1Raw: false,
    externalId: 'some_ext',
  });

  assert.strictEqual(labels.source_type, 'local_csv');
  assert.strictEqual(labels.evidence_level, 'weak');
  assert.strictEqual(labels.is_production_scope, false);
  assert.strictEqual(labels.is_reconciliation_eligible, false);
  assert.strictEqual(labels.pipeline_status_reason, 'non_production_league');
});

test('PHASE4.43_SYNTHETIC → synthetic_invalid', () => {
  const labels = computeGovernanceLabels({
    dataVersion: 'PHASE4.43_SYNTHETIC',
    leagueName: 'Ligue 1',
    season: '2025/2026',
    status: 'finished',
    pipelineStatus: 'pending',
    hasFotmobLiveV1Raw: false,
    externalId: 'synth_001',
  });

  assert.strictEqual(labels.source_type, 'synthetic');
  assert.strictEqual(labels.evidence_level, 'synthetic_invalid');
  assert.strictEqual(labels.is_reconciliation_eligible, false);
  assert.strictEqual(labels.pipeline_status_reason, 'synthetic_raw_not_valid');
});

test('unknown data source → source_type=unknown, evidence=missing', () => {
  const labels = computeGovernanceLabels({
    leagueName: 'Unknown League',
    season: '2025/2026',
    status: 'finished',
    pipelineStatus: 'pending',
    hasFotmobLiveV1Raw: false,
    externalId: '',
  });

  assert.strictEqual(labels.source_type, 'unknown');
  assert.strictEqual(labels.evidence_level, 'missing');
  assert.strictEqual(labels.pipeline_status_reason, 'non_production_league');
});

test('scheduled match → awaiting_match_completion', () => {
  const labels = computeGovernanceLabels({
    dataVersion: 'fotmob_live_v1',
    leagueName: 'Ligue 1',
    season: '2025/2026',
    status: 'scheduled',
    pipelineStatus: 'pending',
    hasFotmobLiveV1Raw: true,
    externalId: '4451815',
  });

  assert.strictEqual(labels.source_type, 'fotmob_live_fetch');
  assert.strictEqual(labels.evidence_level, 'strong');
  assert.strictEqual(labels.is_production_scope, true);
  assert.strictEqual(labels.is_reconciliation_eligible, false); // not finished
  assert.strictEqual(labels.is_training_eligible, false);
  assert.strictEqual(labels.pipeline_status_reason, 'awaiting_match_completion');
});

test('pending without fotmob_live_v1 raw → correct reason', () => {
  const labels = computeGovernanceLabels({
    dataSource: 'fotmob',
    leagueName: 'Ligue 1',
    season: '2025/2026',
    status: 'finished',
    pipelineStatus: 'pending',
    hasFotmobLiveV1Raw: false,
    externalId: '4451815',
  });

  assert.strictEqual(labels.is_production_scope, true);
  assert.strictEqual(labels.is_reconciliation_eligible, false);
  assert.strictEqual(labels.pipeline_status_reason, 'pending_without_fotmob_live_v1_raw');
});

test('training_eligible always false across all scenarios', () => {
  const scenarios = [
    { dataVersion: 'fotmob_live_v1', leagueName: 'Ligue 1', season: '2025/2026', status: 'finished', hasFotmobLiveV1Raw: true, externalId: '123' },
    { dataSource: 'manual_html_seed', leagueName: 'Ligue 1', season: '2025/2026', status: 'finished', hasFotmobLiveV1Raw: false },
    {},
  ];
  for (const ctx of scenarios) {
    assert.strictEqual(
      computeGovernanceLabels(ctx).is_training_eligible,
      false,
      `training should be false for ${JSON.stringify(ctx)}`
    );
  }
});

// =========================================================================
// 10. 常量完整性检查
// =========================================================================

test('DATA_VERSION_TO_SOURCE_TYPE covers all known versions', () => {
  assert.strictEqual(DATA_VERSION_TO_SOURCE_TYPE['fotmob_live_v1'], 'fotmob_live_fetch');
  assert.strictEqual(DATA_VERSION_TO_SOURCE_TYPE['fotmob_html_hyd_v1'], 'fotmob_html_hydration');
  assert.strictEqual(DATA_VERSION_TO_SOURCE_TYPE['fotmob_pageprops_v2'], 'fotmob_pageprops');
  assert.strictEqual(Object.keys(DATA_VERSION_TO_SOURCE_TYPE).length, 3);
});

test('EVIDENCE_LEVEL_MAP covers all source types', () => {
  const sourceTypes = Object.values(DATA_VERSION_TO_SOURCE_TYPE);
  sourceTypes.push('manual_seed', 'local_csv', 'synthetic', 'unknown');
  for (const st of sourceTypes) {
    assert.ok(EVIDENCE_LEVEL_MAP[st], `EVIDENCE_LEVEL_MAP missing entry for ${st}`);
  }
});

// =========================================================================
// 报告
// =========================================================================

console.log(`\n=== MatchLabelingGovernance Unit Tests: ${testsPassed}/${testsRun} passed ===`);
if (testsPassed < testsRun) {
  console.error(`FAILED: ${testsRun - testsPassed} test(s) failed`);
  process.exitCode = 1;
}
