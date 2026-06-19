/**
 * matches_labeling_backfill_dry_run.js — 治理标签回填只读预演
 * ============================================================
 *
 * 对当前 matches 表中的历史行做只读扫描，基于现有 matches 字段和
 * raw_match_data 证据，调用 MatchLabelingGovernance 计算"如果未来
 * backfill，会给每行写入什么治理标签"。
 *
 * 只输出 dry-run 结果，不写库。
 *
 * 使用方式:
 *   node scripts/ops/matches_labeling_backfill_dry_run.js --json
 *   node scripts/ops/matches_labeling_backfill_dry_run.js --json --limit 10
 *   node scripts/ops/matches_labeling_backfill_dry_run.js --json --match-id "53_20252026_4830746"
 *   node scripts/ops/matches_labeling_backfill_dry_run.js --json --league "Ligue 1" --season "2025/2026"
 *
 * lifecycle: one-shot-helper
 * cleanup: delete after real backfill is authorized and executed
 *
 * @module scripts/ops/matches_labeling_backfill_dry_run
 */

'use strict';

const { getPool } = require('../../config/database');
const {
  computeGovernanceLabels,
} = require('../../src/infrastructure/services/MatchLabelingGovernance');

// ---------------------------------------------------------------------------
// CLI 参数解析
// ---------------------------------------------------------------------------

function parseArgs(argv) {
  const args = {
    json: false,
    limit: null,
    matchId: null,
    league: null,
    season: null,
    allowWrite: false,
  };

  for (let i = 2; i < argv.length; i++) {
    const arg = argv[i];
    switch (arg) {
      case '--json':
        args.json = true;
        break;
      case '--allow-write':
        args.allowWrite = true;
        break;
      case '--limit':
        args.limit = parseInt(argv[++i], 10);
        if (Number.isNaN(args.limit) || args.limit < 1) {
          throw new Error(`Invalid --limit value: ${argv[i]}`);
        }
        break;
      case '--match-id':
        args.matchId = argv[++i];
        if (!args.matchId) throw new Error('--match-id requires a value');
        break;
      case '--league':
        args.league = argv[++i];
        if (!args.league) throw new Error('--league requires a value');
        break;
      case '--season':
        args.season = argv[++i];
        if (!args.season) throw new Error('--season requires a value');
        break;
      default:
        // 忽略未知参数
        break;
    }
  }

  return args;
}

// ---------------------------------------------------------------------------
// 只读 SELECT 扫描
// ---------------------------------------------------------------------------

/**
 * 扫描 matches 表并返回每行的上下文信息。
 *
 * SELECT-only，不写库。
 *
 * @param {import('pg').Pool} pool
 * @param {object} args - 解析后的 CLI 参数
 * @returns {Promise<Array<object>>} 每场比赛的上下文数组
 */
async function scanMatches(pool, args) {
  const conditions = [];
  const params = [];
  let paramIndex = 1;

  if (args.matchId) {
    conditions.push(`m.match_id = $${paramIndex++}`);
    params.push(args.matchId);
  }
  if (args.league) {
    conditions.push(`m.league_name = $${paramIndex++}`);
    params.push(args.league);
  }
  if (args.season) {
    conditions.push(`m.season = $${paramIndex++}`);
    params.push(args.season);
  }

  const whereClause = conditions.length > 0
    ? `WHERE ${conditions.join(' AND ')}`
    : '';

  const limitClause = args.limit ? `LIMIT ${args.limit}` : '';

  const sql = `
    SELECT
      m.match_id,
      m.league_name,
      m.season,
      m.status,
      m.pipeline_status,
      m.data_source,
      m.external_id,
      m.source_type,
      m.evidence_level,
      m.is_production_scope,
      m.is_reconciliation_eligible,
      m.is_training_eligible,
      m.pipeline_status_reason,
      r.data_version
    FROM matches m
    LEFT JOIN LATERAL (
      SELECT rd.data_version
      FROM raw_match_data rd
      WHERE rd.match_id = m.match_id
      ORDER BY
        CASE WHEN rd.data_version = 'fotmob_live_v1' THEN 1
             WHEN rd.data_version = 'fotmob_pageprops_v2' THEN 2
             WHEN rd.data_version = 'fotmob_html_hyd_v1' THEN 3
             ELSE 4
        END,
        rd.collected_at DESC NULLS LAST
      LIMIT 1
    ) r ON true
    ${whereClause}
    ORDER BY m.league_name, m.season, m.match_id
    ${limitClause}
  `;

  const client = await pool.connect();
  try {
    const result = await client.query(sql, params);
    return result.rows;
  } finally {
    client.release();
  }
}

/**
 * 查询每场比赛是否有 fotmob_live_v1 raw。
 *
 * @param {import('pg').Pool} pool
 * @param {string[]} matchIds - 要查询的 match_id 列表
 * @returns {Promise<Set<string>>} 拥有 fotmob_live_v1 raw 的 match_id 集合
 */
async function getFotmobLiveV1MatchIds(pool, matchIds) {
  if (matchIds.length === 0) return new Set();

  const client = await pool.connect();
  try {
    const result = await client.query(
      `SELECT DISTINCT match_id
       FROM raw_match_data
       WHERE match_id = ANY($1::text[])
         AND data_version = 'fotmob_live_v1'`,
      [matchIds]
    );
    return new Set(result.rows.map((r) => r.match_id));
  } finally {
    client.release();
  }
}

// ---------------------------------------------------------------------------
// 字段空值判断
// ---------------------------------------------------------------------------

/**
 * 检查某行的治理字段是否全部为空（即从未被 backfill）。
 */
function governanceFieldsAllNull(row) {
  return (
    row.source_type === null &&
    row.evidence_level === null &&
    row.is_production_scope === null &&
    row.is_reconciliation_eligible === null &&
    row.is_training_eligible === null &&
    row.pipeline_status_reason === null
  );
}

/**
 * 检查某行的治理字段是否有任意一个非空。
 */
function hasAnyGovernanceField(row) {
  return !governanceFieldsAllNull(row);
}

// ---------------------------------------------------------------------------
// 行分类
// ---------------------------------------------------------------------------

/**
 * 对单行 match 进行分类并生成 proposed labels。
 *
 * @param {object} row - matches 行（含 data_version）
 * @param {Set<string>} fotmobLiveV1Ids - 有 fotmob_live_v1 raw 的 match_id 集合
 * @returns {object} 分类结果和 proposed labels
 */
function classifyRow(row, fotmobLiveV1Ids) {
  const hasFotmobLiveV1Raw = fotmobLiveV1Ids.has(row.match_id);
  // 合成数据版本（PHASE* / synthetic*）不视为有效证据
  const isSyntheticVersion = row.data_version && /^(phase|synthetic)/i.test(String(row.data_version));
  const hasRaw = row.data_version !== null && row.data_version !== undefined && !isSyntheticVersion;
  const alreadyLabeled = hasAnyGovernanceField(row);

  const context = {
    dataVersion: row.data_version,
    dataSource: row.data_source,
    leagueName: row.league_name,
    season: row.season,
    status: row.status,
    pipelineStatus: row.pipeline_status,
    hasFotmobLiveV1Raw,
    externalId: row.external_id,
  };

  const proposed = computeGovernanceLabels(context);

  return {
    match_id: row.match_id,
    league_name: row.league_name,
    season: row.season,
    status: row.status,
    pipeline_status: row.pipeline_status,
    already_labeled: alreadyLabeled,
    has_raw: hasRaw,
    data_version: row.data_version || null,
    has_fotmob_live_v1_raw: hasFotmobLiveV1Raw,
    current_source_type: row.source_type,
    current_evidence_level: row.evidence_level,
    current_is_production_scope: row.is_production_scope,
    current_is_reconciliation_eligible: row.is_reconciliation_eligible,
    current_is_training_eligible: row.is_training_eligible,
    current_pipeline_status_reason: row.pipeline_status_reason,
    proposed_source_type: proposed.source_type,
    proposed_evidence_level: proposed.evidence_level,
    proposed_is_production_scope: proposed.is_production_scope,
    proposed_is_reconciliation_eligible: proposed.is_reconciliation_eligible,
    proposed_is_training_eligible: proposed.is_training_eligible,
    proposed_pipeline_status_reason: proposed.pipeline_status_reason,
  };
}

// ---------------------------------------------------------------------------
// 聚合统计辅助函数
// ---------------------------------------------------------------------------

/**
 * 统计字符串字段的分布。
 */
function countDistribution(rows, keyFn) {
  const dist = {};
  for (const r of rows) {
    const val = keyFn(r);
    dist[val] = (dist[val] || 0) + 1;
  }
  return dist;
}

/**
 * 统计布尔字段的分布。
 */
function countBooleanDistribution(rows, keyFn) {
  const dist = { true: 0, false: 0 };
  for (const r of rows) {
    dist[keyFn(r) ? 'true' : 'false']++;
  }
  return dist;
}

/**
 * 生成风险标记列表。
 */
function buildRiskFlags(unlabeled, candidateTotal, bySourceType) {
  const riskFlags = [];
  if (unlabeled.length === 0) {
    riskFlags.push('no_unlabeled_rows: all matches already have governance labels');
  }
  if (candidateTotal === 0 && unlabeled.length > 0) {
    riskFlags.push('zero_candidates_excluded_no_raw: all unlabeled matches have no raw evidence');
  }
  const syntheticCount = bySourceType['synthetic'] || 0;
  if (syntheticCount > 0) {
    riskFlags.push(`synthetic_source_detected: ${syntheticCount} unlabeled rows have source_type=synthetic`);
  }
  const unknownCount = bySourceType['unknown'] || 0;
  if (unknownCount > 0) {
    riskFlags.push(`unknown_source_detected: ${unknownCount} unlabeled rows have source_type=unknown`);
  }
  return riskFlags;
}

/**
 * 提取 class A / B / C 关键行的 proposed labels。
 */
function extractKeyRows(classified) {
  const classARows = classified.filter(
    (r) =>
      r.league_name === 'Ligue 1' &&
      r.season === '2025/2026' &&
      r.pipeline_status === 'harvested' &&
      r.has_fotmob_live_v1_raw
  );
  const classBRow = classified.find((r) => r.match_id === '140_20252026_4837496');
  const classCRow = classified.find((r) => r.match_id === '47_20242025_900002');

  return { classARows, classBRow, classCRow };
}

/**
 * 格式化 class summary。
 */
function formatClassSummary(classARows) {
  if (classARows.length === 0) return null;
  return {
    count: classARows.length,
    expected_source_type: 'fotmob_live_fetch',
    expected_evidence_level: 'strong',
    expected_is_production_scope: true,
    expected_is_reconciliation_eligible: true,
    expected_is_training_eligible: false,
    expected_pipeline_status_reason: null,
  };
}

/**
 * 格式化单个 class row 的 proposed labels。
 */
function formatClassRowProposed(row) {
  if (!row) return null;
  return {
    match_id: row.match_id,
    proposed_source_type: row.proposed_source_type,
    proposed_evidence_level: row.proposed_evidence_level,
    proposed_is_production_scope: row.proposed_is_production_scope,
    proposed_is_reconciliation_eligible: row.proposed_is_reconciliation_eligible,
    proposed_is_training_eligible: row.proposed_is_training_eligible,
    proposed_pipeline_status_reason: row.proposed_pipeline_status_reason,
    already_labeled: row.already_labeled,
  };
}

/**
 * 格式化 no-raw excluded 行的 proposed labels（最多 10 条）。
 */
function formatNoRawExcluded(excludedNoRaw) {
  return excludedNoRaw.slice(0, 10).map((r) => ({
    match_id: r.match_id,
    league_name: r.league_name,
    season: r.season,
    status: r.status,
    proposed_source_type: r.proposed_source_type,
    proposed_evidence_level: r.proposed_evidence_level,
    proposed_is_production_scope: r.proposed_is_production_scope,
    proposed_is_reconciliation_eligible: r.proposed_is_reconciliation_eligible,
    proposed_is_training_eligible: r.proposed_is_training_eligible,
    proposed_pipeline_status_reason: r.proposed_pipeline_status_reason,
  }));
}

// ---------------------------------------------------------------------------
// 聚合统计主函数
// ---------------------------------------------------------------------------

/**
 * 基于分类结果生成聚合统计。
 *
 * @param {Array<object>} classified - classifyRow 的输出数组
 * @returns {object} 聚合统计数据
 */
function buildSummary(classified) {
  const total = classified.length;
  const unlabeled = classified.filter((r) => !r.already_labeled);
  const alreadyLabeled = classified.filter((r) => r.already_labeled);
  const excludedNoRaw = classified.filter((r) => !r.has_raw);

  const bySourceType = countDistribution(unlabeled, (r) => r.proposed_source_type);
  const byEvidenceLevel = countDistribution(unlabeled, (r) => r.proposed_evidence_level);
  const byProductionScope = countBooleanDistribution(unlabeled, (r) => r.proposed_is_production_scope);
  const byReconciliationEligible = countBooleanDistribution(unlabeled, (r) => r.proposed_is_reconciliation_eligible);
  const byTrainingEligible = countBooleanDistribution(unlabeled, (r) => r.proposed_is_training_eligible);
  const byPipelineStatusReason = countDistribution(unlabeled, (r) => r.proposed_pipeline_status_reason || 'NULL');

  const candidateTotal = unlabeled.filter((r) => r.has_raw).length;
  const riskFlags = buildRiskFlags(unlabeled, candidateTotal, bySourceType);

  const { classARows, classBRow, classCRow } = extractKeyRows(classified);

  return {
    total_matches_scanned: total,
    would_update_count: unlabeled.length,
    already_labeled_count: alreadyLabeled.length,
    unlabeled_count: unlabeled.length,
    by_source_type: bySourceType,
    by_evidence_level: byEvidenceLevel,
    by_production_scope: byProductionScope,
    by_reconciliation_eligible: byReconciliationEligible,
    by_training_eligible: byTrainingEligible,
    by_pipeline_status_reason: byPipelineStatusReason,
    excluded_no_raw_count: excludedNoRaw.length,
    candidate_total: candidateTotal,
    sample_rows: selectSampleRows(classified, 20),
    risk_flags: riskFlags,
    class_a_count: classARows.length,
    class_a_summary: formatClassSummary(classARows),
    class_b_proposed: formatClassRowProposed(classBRow),
    class_c_proposed: formatClassRowProposed(classCRow),
    no_raw_excluded_proposed: formatNoRawExcluded(excludedNoRaw),
  };
}

/**
 * 选取代表性样本行。
 * 优先：Ligue 1 2025/2026、有 raw 的行、不同 source_type 各取几条。
 */
function selectSampleRows(classified, maxCount) {
  const samples = [];
  const seen = new Set();

  // 优先：Ligue 1 2025/2026 + 有 raw + unlabeled
  const ligue1Rows = classified.filter(
    (r) =>
      r.league_name === 'Ligue 1' &&
      r.season === '2025/2026' &&
      r.has_raw &&
      !r.already_labeled
  );
  for (const r of ligue1Rows) {
    if (samples.length >= maxCount) break;
    if (seen.has(r.match_id)) continue;
    seen.add(r.match_id);
    samples.push(formatSampleRow(r));
  }

  // 第二优先：no-raw excluded
  const noRawRows = classified.filter((r) => !r.has_raw && !r.already_labeled);
  for (const r of noRawRows) {
    if (samples.length >= maxCount) break;
    if (seen.has(r.match_id)) continue;
    seen.add(r.match_id);
    samples.push(formatSampleRow(r));
  }

  // 第三优先：already labeled
  const alreadyLabeledRows = classified.filter((r) => r.already_labeled);
  for (const r of alreadyLabeledRows) {
    if (samples.length >= maxCount) break;
    if (seen.has(r.match_id)) continue;
    seen.add(r.match_id);
    samples.push(formatSampleRow(r));
  }

  // 剩余补齐
  for (const r of classified) {
    if (samples.length >= maxCount) break;
    if (seen.has(r.match_id)) continue;
    seen.add(r.match_id);
    samples.push(formatSampleRow(r));
  }

  return samples;
}

/**
 * 格式化单行样本输出——只包含允许的字段，禁止 raw payload。
 */
function formatSampleRow(r) {
  return {
    match_id: r.match_id,
    league_name: r.league_name,
    season: r.season,
    status: r.status,
    pipeline_status: r.pipeline_status,
    current_labels_empty: !r.already_labeled,
    proposed_source_type: r.proposed_source_type,
    proposed_evidence_level: r.proposed_evidence_level,
    proposed_is_production_scope: r.proposed_is_production_scope,
    proposed_is_reconciliation_eligible: r.proposed_is_reconciliation_eligible,
    proposed_is_training_eligible: r.proposed_is_training_eligible,
    proposed_pipeline_status_reason: r.proposed_pipeline_status_reason,
    reason: buildReason(r),
  };
}

/**
 * 为样本行构建简短原因说明。
 */
function buildReason(r) {
  if (r.already_labeled) {
    return 'already_labeled: governance fields populated, skipping';
  }
  if (!r.has_raw) {
    return 'no_raw: excluded from backfill candidates';
  }
  if (r.proposed_is_reconciliation_eligible) {
    return 'production candidate: ready for reconciliation';
  }
  if (r.proposed_is_production_scope && r.has_fotmob_live_v1_raw) {
    return 'production scope with fotmob_live_v1 raw';
  }
  if (r.proposed_pipeline_status_reason === 'non_production_league') {
    return 'non-production league or season';
  }
  return `pipeline_status_reason=${r.proposed_pipeline_status_reason || 'NULL'}`;
}

// ---------------------------------------------------------------------------
// 真实写库
// ---------------------------------------------------------------------------

/**
 * 单事务执行治理字段回填 UPDATE。
 *
 * 安全约束：
 *   - 只更新 source_type / evidence_level / is_production_scope /
 *     is_reconciliation_eligible / is_training_eligible / pipeline_status_reason
 *   - 只更新当前治理字段全部为空的行
 *   - values 来自 MatchLabelingGovernance.computeGovernanceLabels
 *   - 单事务，任何失败触发 ROLLBACK
 *
 * @param {import('pg').Pool} pool
 * @param {Array<object>} classified - classifyRow 的输出数组
 * @returns {Promise<number>} 实际更新的行数
 */
async function executeWrite(pool, classified) {
  const toUpdate = classified.filter((r) => !r.already_labeled);

  if (toUpdate.length === 0) {
    return 0;
  }

  const client = await pool.connect();
  try {
    await client.query('BEGIN');

    let updatedCount = 0;
    for (const row of toUpdate) {
      const result = await client.query(
        `UPDATE matches
         SET source_type = $1,
             evidence_level = $2,
             is_production_scope = $3,
             is_reconciliation_eligible = $4,
             is_training_eligible = $5,
             pipeline_status_reason = $6,
             updated_at = NOW()
         WHERE match_id = $7
           AND source_type IS NULL
           AND evidence_level IS NULL
           AND is_production_scope IS NULL
           AND is_reconciliation_eligible IS NULL
           AND is_training_eligible IS NULL
           AND pipeline_status_reason IS NULL`,
        [
          row.proposed_source_type,
          row.proposed_evidence_level,
          row.proposed_is_production_scope,
          row.proposed_is_reconciliation_eligible,
          row.proposed_is_training_eligible,
          row.proposed_pipeline_status_reason,
          row.match_id,
        ]
      );
      updatedCount += result.rowCount;
    }

    await client.query('COMMIT');
    return updatedCount;
  } catch (err) {
    await client.query('ROLLBACK');
    throw err;
  } finally {
    client.release();
  }
}

/**
 * 写入后验证：检查 matches / raw_match_data 行数、pipeline_status 分布是否不变。
 *
 * @param {import('pg').Pool} pool
 * @returns {Promise<object>} 验证结果
 */
async function verifyPostWrite(pool) {
  const client = await pool.connect();
  try {
    const matchCount = await client.query('SELECT COUNT(*) AS cnt FROM matches');
    const rawCount = await client.query('SELECT COUNT(*) AS cnt FROM raw_match_data');

    const pipelineDist = await client.query(
      `SELECT pipeline_status, COUNT(*) AS cnt
       FROM matches
       GROUP BY pipeline_status
       ORDER BY pipeline_status`
    );

    const governancePopulated = await client.query(
      `SELECT COUNT(*) AS cnt FROM matches
       WHERE source_type IS NOT NULL
          OR evidence_level IS NOT NULL
          OR is_production_scope IS NOT NULL
          OR is_reconciliation_eligible IS NOT NULL
          OR is_training_eligible IS NOT NULL
          OR pipeline_status_reason IS NOT NULL`
    );

    const ligue1Labels = await client.query(
      `SELECT source_type, evidence_level, is_production_scope,
              is_reconciliation_eligible, is_training_eligible,
              pipeline_status_reason, COUNT(*) AS cnt
       FROM matches
       WHERE league_name = 'Ligue 1' AND season = '2025/2026'
       GROUP BY source_type, evidence_level, is_production_scope,
                is_reconciliation_eligible, is_training_eligible,
                pipeline_status_reason`
    );

    const noRawLabels = await client.query(
      `SELECT match_id, source_type, evidence_level, is_production_scope,
              is_reconciliation_eligible, is_training_eligible,
              pipeline_status_reason
       FROM matches
       WHERE source_type = 'synthetic'
       ORDER BY match_id`
    );

    return {
      matches_row_count: parseInt(matchCount.rows[0].cnt, 10),
      raw_match_data_row_count: parseInt(rawCount.rows[0].cnt, 10),
      pipeline_status_distribution: pipelineDist.rows,
      governance_populated_count: parseInt(governancePopulated.rows[0].cnt, 10),
      ligue1_label_summary: ligue1Labels.rows,
      no_raw_excluded_labels: noRawLabels.rows,
    };
  } finally {
    client.release();
  }
}

// ---------------------------------------------------------------------------
// 预检门禁
// ---------------------------------------------------------------------------

/**
 * 写入前 dry-run 预检。如果关键指标与预期不符，立即停止。
 *
 * @param {object} summary - buildSummary 的输出
 */
function preflightGate(summary) {
  const checks = [
    { field: 'total_matches_scanned', expected: 60, actual: summary.total_matches_scanned },
    { field: 'would_update_count', expected: 60, actual: summary.would_update_count },
    { field: 'already_labeled_count', expected: 0, actual: summary.already_labeled_count },
    { field: 'candidate_total', expected: 58, actual: summary.candidate_total },
    { field: 'excluded_no_raw_count', expected: 2, actual: summary.excluded_no_raw_count },
  ];

  const failures = [];
  for (const { field, expected, actual } of checks) {
    if (actual !== expected) {
      failures.push(`${field}: expected=${expected}, actual=${actual}`);
    }
  }

  if (failures.length > 0) {
    throw new Error(
      `Preflight gate FAILED. Count mismatch:\n${failures.join('\n')}\n` +
      'Write aborted. Verify database state before retrying.'
    );
  }

  return true;
}

// ---------------------------------------------------------------------------
// 主流程
// ---------------------------------------------------------------------------

async function main() {
  const args = parseArgs(process.argv);

  if (args.allowWrite && !args.json) {
    console.error('Error: --allow-write requires --json');
    process.exitCode = 1;
    return;
  }

  const pool = getPool();

  // 1. 扫描 matches（dry-run 和 write 模式共享）
  const rows = await scanMatches(pool, args);

  // 2. 批量查询 fotmob_live_v1 raw 存在性
  const allMatchIds = rows.map((r) => r.match_id);
  const fotmobLiveV1Ids = await getFotmobLiveV1MatchIds(pool, allMatchIds);

  // 3. 逐行分类
  const classified = rows.map((row) => classifyRow(row, fotmobLiveV1Ids));

  // 4. 构建摘要
  const summary = buildSummary(classified);

  if (args.allowWrite) {
    // ===================================================================
    // 写模式
    // ===================================================================

    // 预检门禁
    preflightGate(summary);

    // 执行写入
    const updatedCount = await executeWrite(pool, classified);

    // 写入后验证
    const verification = await verifyPostWrite(pool);

    // 构建输出
    const output = {
      mode: 'write',
      actual_update_executed: true,
      script: 'scripts/ops/matches_labeling_backfill_dry_run.js',
      governance_module: 'src/infrastructure/services/MatchLabelingGovernance.js',
      rule_version: 'V26.7-writer-support-v1',
      generated_at: new Date().toISOString(),
      preflight: {
        passed: true,
        total_matches_scanned: summary.total_matches_scanned,
        would_update_count: summary.would_update_count,
        already_labeled_count: summary.already_labeled_count,
        candidate_total: summary.candidate_total,
        excluded_no_raw_count: summary.excluded_no_raw_count,
      },
      write_result: {
        updated_count: updatedCount,
        transaction: 'single_transaction_committed',
      },
      post_write_verification: verification,
    };

    console.log(JSON.stringify(output, null, 2));
  } else {
    // ===================================================================
    // Dry-run 模式（默认）
    // ===================================================================
    const output = {
      mode: 'dry_run',
      actual_update_executed: false,
      script: 'scripts/ops/matches_labeling_backfill_dry_run.js',
      governance_module: 'src/infrastructure/services/MatchLabelingGovernance.js',
      rule_version: 'V26.7-writer-support-v1',
      generated_at: new Date().toISOString(),
      filters_applied: {
        limit: args.limit,
        match_id: args.matchId,
        league: args.league,
        season: args.season,
      },
      ...summary,
    };

    console.log(JSON.stringify(output, null, 2));
  }

  // 退出
  await pool.end();
}

// ---------------------------------------------------------------------------
// 入口
// ---------------------------------------------------------------------------

if (require.main === module) {
  main().catch((err) => {
    console.error('Dry-run failed:', err.message);
    process.exitCode = 1;
  });
}

module.exports = {
  parseArgs,
  scanMatches,
  getFotmobLiveV1MatchIds,
  classifyRow,
  buildSummary,
  countDistribution,
  countBooleanDistribution,
  buildRiskFlags,
  extractKeyRows,
  formatClassSummary,
  formatClassRowProposed,
  formatNoRawExcluded,
  selectSampleRows,
  formatSampleRow,
  governanceFieldsAllNull,
  hasAnyGovernanceField,
  executeWrite,
  verifyPostWrite,
  preflightGate,
};
