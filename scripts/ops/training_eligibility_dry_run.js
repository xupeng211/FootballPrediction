/**
 * training_eligibility_dry_run.js — 训练准入只读预演
 * ====================================================
 *
 * 基于 training_eligibility_policy_design_20260619.md 的 6 条准入规则，
 * 对当前 matches 表做只读扫描，预演哪些行未来可以设 is_training_eligible=true，
 * 哪些必须保持 false，以及每条 false 的原因。
 *
 * 只输出 dry-run 结果，不写库。
 *
 * 使用方式:
 *   node scripts/ops/training_eligibility_dry_run.js --json
 *   node scripts/ops/training_eligibility_dry_run.js --json --match-id "53_20252026_4830458"
 *
 * lifecycle: one-shot-helper
 *
 * @module scripts/ops/training_eligibility_dry_run
 */

'use strict';

const { getPool } = require('../../config/database');

// ---------------------------------------------------------------------------
// 常量：训练准入规则定义
// ---------------------------------------------------------------------------

/** 允许进入训练的 source_type 集合。 */
const TRAINING_VALID_SOURCE_TYPES = new Set([
  'fotmob_live_fetch',
  'fotmob_html_hydration',
  'fotmob_pageprops',
]);

/** 允许进入训练的 pipeline_status 集合。 */
const TRAINING_VALID_PIPELINE_STATUSES = new Set([
  'harvested',
  'recon_linked',
]);

/** 永远禁止进入训练的证据级别。 */
const TRAINING_FORBIDDEN_EVIDENCE = new Set([
  'synthetic_invalid',
  'missing',
]);

// ---------------------------------------------------------------------------
// CLI 参数解析
// ---------------------------------------------------------------------------

function parseArgs(argv) {
  const args = { json: false, matchId: null };
  for (let i = 2; i < argv.length; i++) {
    switch (argv[i]) {
      case '--json':
        args.json = true;
        break;
      case '--match-id':
        args.matchId = argv[++i];
        if (!args.matchId) throw new Error('--match-id requires a value');
        break;
      default:
        break;
    }
  }
  return args;
}

// ---------------------------------------------------------------------------
// 只读扫描
// ---------------------------------------------------------------------------

async function scanMatches(pool, args) {
  const conditions = [];
  const params = [];
  let i = 1;

  if (args.matchId) {
    conditions.push(`match_id = $${i++}`);
    params.push(args.matchId);
  }

  const where = conditions.length ? `WHERE ${conditions.join(' AND ')}` : '';

  const sql = `
    SELECT match_id, league_name, season, status, pipeline_status,
           home_score, away_score, data_source, external_id,
           source_type, evidence_level,
           is_production_scope, is_reconciliation_eligible,
           is_training_eligible, pipeline_status_reason
    FROM matches
    ${where}
    ORDER BY league_name, season, match_id
  `;

  const client = await pool.connect();
  try {
    return (await client.query(sql, params)).rows;
  } finally {
    client.release();
  }
}

// ---------------------------------------------------------------------------
// 规则评估
// ---------------------------------------------------------------------------

/**
 * 评估单场比赛的训练准入资格。
 *
 * 按优先级依次检查 6 条规则，返回第一个失败原因。
 * 全部通过则 eligible=true。
 *
 * @param {object} row - matches 行
 * @returns {{ eligible: boolean, reason: string|null }}
 */
function evaluateTrainingEligibility(row) {
  // Rule 1: Evidence Quality Gate
  if (!TRAINING_VALID_SOURCE_TYPES.has(row.source_type)) {
    if (TRAINING_FORBIDDEN_EVIDENCE.has(row.evidence_level)) {
      return {
        eligible: false,
        reason: `forbidden_evidence: ${row.evidence_level || 'missing'}`,
      };
    }
    return {
      eligible: false,
      reason: `invalid_source_type: ${row.source_type || 'null'}`,
    };
  }

  // Rule 2: Match Completion Gate
  if (row.status !== 'finished') {
    return {
      eligible: false,
      reason: `match_not_finished: status=${row.status}`,
    };
  }

  // Rule 2b: Valid scores required
  if (row.home_score === null || row.away_score === null) {
    return {
      eligible: false,
      reason: 'no_valid_scores: home_score or away_score is null',
    };
  }

  // Rule 3: Feature Leakage — cannot check from DB, noted in summary
  // (passed if we reach here, but noted as conditional)

  // Rule 4: Production Scope Alignment
  if (row.is_production_scope !== true) {
    return {
      eligible: false,
      reason: 'non_production_scope',
    };
  }

  // Rule 5: Pipeline Completion
  if (!TRAINING_VALID_PIPELINE_STATUSES.has(
    (row.pipeline_status || '').toLowerCase()
  )) {
    return {
      eligible: false,
      reason: `pipeline_not_complete: pipeline_status=${row.pipeline_status}`,
    };
  }

  if (row.pipeline_status_reason !== null) {
    return {
      eligible: false,
      reason: `pipeline_blocked: ${row.pipeline_status_reason}`,
    };
  }

  // Rule 6: Reconciliation Gate (should be covered by rules 1+2+4+5)
  if (row.is_reconciliation_eligible !== true) {
    return {
      eligible: false,
      reason: 'not_reconciliation_eligible',
    };
  }

  // All rules passed — conditional on leakage policy
  return {
    eligible: true,
    reason: 'all_rules_passed_conditional_on_leakage_policy',
  };
}

// ---------------------------------------------------------------------------
// 汇总构建
// ---------------------------------------------------------------------------

function countDistribution(rows, keyFn) {
  const dist = {};
  for (const r of rows) {
    const k = keyFn(r);
    dist[k] = (dist[k] || 0) + 1;
  }
  return dist;
}

function buildSummary(rows) {
  const evaluated = rows.map((row) => ({
    match_id: row.match_id,
    league_name: row.league_name,
    season: row.season,
    status: row.status,
    pipeline_status: row.pipeline_status,
    source_type: row.source_type,
    evidence_level: row.evidence_level,
    is_production_scope: row.is_production_scope,
    is_reconciliation_eligible: row.is_reconciliation_eligible,
    current_training_eligible: row.is_training_eligible,
    ...evaluateTrainingEligibility(row),
  }));

  const wouldSetTrue = evaluated.filter((r) => r.eligible);
  const wouldKeepFalse = evaluated.filter((r) => !r.eligible);
  const byReason = countDistribution(wouldKeepFalse, (r) => r.reason);

  // Sample rows
  const sampleTrue = wouldSetTrue.slice(0, 5).map(formatSampleRow);
  const sampleFalse = wouldKeepFalse.map(formatSampleRow);

  // Risk flags
  const riskFlags = [];
  const syntheticInTraining = wouldSetTrue.filter(
    (r) => r.source_type === 'synthetic'
  );
  if (syntheticInTraining.length > 0) {
    riskFlags.push(
      `CRITICAL: ${syntheticInTraining.length} synthetic rows would be training-eligible`
    );
  }
  const notFinishedInTraining = wouldSetTrue.filter(
    (r) => r.status !== 'finished'
  );
  if (notFinishedInTraining.length > 0) {
    riskFlags.push(
      `WARNING: ${notFinishedInTraining.length} non-finished rows would be training-eligible`
    );
  }
  riskFlags.push(
    'NOTE: all would_set_true rows are conditional on feature leakage policy and cutoff time definition'
  );
  if (rowHasAnyMissingLeakageSignal(evaluated)) {
    riskFlags.push(
      'WARNING: feature leakage policy and prediction cutoff time are NOT yet defined — training eligibility remains conditional'
    );
  }

  return {
    mode: 'dry_run',
    actual_update_executed: false,
    script: 'scripts/ops/training_eligibility_dry_run.js',
    policy_ref: 'docs/_reports/training_eligibility_policy_design_20260619.md',
    generated_at: new Date().toISOString(),
    total_matches_scanned: rows.length,
    current_training_eligible_true: rows.filter((r) => r.is_training_eligible === true).length,
    current_training_eligible_false: rows.filter((r) => r.is_training_eligible === false).length,
    would_set_true_count: wouldSetTrue.length,
    would_keep_false_count: wouldKeepFalse.length,
    by_reason: byReason,
    sample_true: sampleTrue,
    sample_false: sampleFalse,
    risk_flags: riskFlags,
    ligue1_candidates: wouldSetTrue.filter(
      (r) => r.league_name === 'Ligue 1' && r.season === '2025/2026'
    ).length,
    no_raw_excluded_false: wouldKeepFalse
      .filter((r) => r.source_type === 'synthetic')
      .map((r) => ({
        match_id: r.match_id,
        league_name: r.league_name,
        season: r.season,
        reason: r.reason,
      })),
  };
}

function rowHasAnyMissingLeakageSignal(evaluated) {
  // If any row would be set true, leakage policy is needed
  return evaluated.some((r) => r.eligible);
}

function formatSampleRow(r) {
  return {
    match_id: r.match_id,
    league_name: r.league_name,
    season: r.season,
    status: r.status,
    source_type: r.source_type,
    evidence_level: r.evidence_level,
    is_production_scope: r.is_production_scope,
    is_reconciliation_eligible: r.is_reconciliation_eligible,
    current_training_eligible: r.current_training_eligible,
    would_set_true: r.eligible,
    reason: r.reason,
  };
}

// ---------------------------------------------------------------------------
// 主流程
// ---------------------------------------------------------------------------

async function main() {
  const args = parseArgs(process.argv);
  const pool = getPool();

  const rows = await scanMatches(pool, args);
  const summary = buildSummary(rows);

  console.log(JSON.stringify(summary, null, 2));
  await pool.end();
}

if (require.main === module) {
  main().catch((err) => {
    console.error('Training eligibility dry-run failed:', err.message);
    process.exitCode = 1;
  });
}

module.exports = {
  parseArgs,
  scanMatches,
  evaluateTrainingEligibility,
  buildSummary,
  TRAINING_VALID_SOURCE_TYPES,
  TRAINING_VALID_PIPELINE_STATUSES,
  TRAINING_FORBIDDEN_EVIDENCE,
};
