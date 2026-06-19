/**
 * MatchLabelingGovernance - 比赛治理标签计算模块
 * ===============================================
 *
 * 纯函数模块，集中推导 matches 表 6 个治理字段：
 *   source_type, evidence_level, is_production_scope,
 *   is_reconciliation_eligible, is_training_eligible,
 *   pipeline_status_reason
 *
 * 规则版本: V26.7-writer-support-v1（保守版）
 * 生命周期: permanent
 *
 * @module infrastructure/services/MatchLabelingGovernance
 */

'use strict';

// ---------------------------------------------------------------------------
// 常量映射表
// ---------------------------------------------------------------------------

/**
 * raw_match_data.data_version → source_type 直接映射。
 * 仅收录已知稳定版本标识符，未知版本不匹配。
 */
const DATA_VERSION_TO_SOURCE_TYPE = Object.freeze({
  fotmob_live_v1: 'fotmob_live_fetch',
  fotmob_html_hyd_v1: 'fotmob_html_hydration',
  fotmob_pageprops_v2: 'fotmob_pageprops',
});

/**
 * data_source 模式 → source_type 兜底映射。
 * 仅当无法从 data_version 确定时使用。
 * 按顺序匹配，命中第一个即停止。
 */
const DATA_SOURCE_PATTERNS = Object.freeze([
  { pattern: /manual.*seed/i, sourceType: 'manual_seed' },
  { pattern: /local.*csv/i, sourceType: 'local_csv' },
  { pattern: /csv/i, sourceType: 'local_csv' },
  { pattern: /synthetic/i, sourceType: 'synthetic' },
]);

/**
 * 以 phase 或 synthetic 开头的 data_version 视为合成数据。
 */
const SYNTHETIC_VERSION_PATTERN = /^(phase|synthetic)/i;

/**
 * source_type → evidence_level 映射。
 */
const EVIDENCE_LEVEL_MAP = Object.freeze({
  fotmob_live_fetch: 'strong',
  fotmob_html_hydration: 'medium',
  fotmob_pageprops: 'medium',
  manual_seed: 'weak',
  local_csv: 'weak',
  synthetic: 'synthetic_invalid',
  unknown: 'missing',
});

/** 当前生产范围：仅 Ligue 1 / 2025/2026 主线。 */
const PRODUCTION_LEAGUES = Object.freeze(['Ligue 1']);
const PRODUCTION_SEASON = '2025/2026';

// ---------------------------------------------------------------------------
// 辅助函数
// ---------------------------------------------------------------------------

/**
 * @param {*} value
 * @returns {string|null}
 */
function normalizeText(value) {
  if (value === null || value === undefined) return null;
  return String(value).trim();
}

/**
 * @param {*} value
 * @returns {string|null}
 */
function normalizeLower(value) {
  const text = normalizeText(value);
  return text ? text.toLowerCase() : null;
}

// ---------------------------------------------------------------------------
// 公开 API
// ---------------------------------------------------------------------------

/**
 * 从可用证据推导 source_type。
 *
 * 优先级：
 *   1. raw_match_data.data_version 已知稳定标识符
 *   2. data_version 匹配合成数据模式（phase* / synthetic*）
 *   3. matches.data_source 模式匹配（兜底）
 *   4. 'unknown'
 *
 * @param {Object} context
 * @param {string} [context.dataVersion] - raw_match_data.data_version
 * @param {string} [context.dataSource] - matches.data_source
 * @returns {string} source_type 值
 */
function computeSourceType(context = {}) {
  const safeContext = context || {};
  const { dataVersion, dataSource } = safeContext;
  const normalizedVersion = normalizeLower(dataVersion);

  // 1. 直接映射已知 data_version
  if (normalizedVersion && DATA_VERSION_TO_SOURCE_TYPE[normalizedVersion]) {
    return DATA_VERSION_TO_SOURCE_TYPE[normalizedVersion];
  }

  // 2. 合成数据模式
  if (normalizedVersion && SYNTHETIC_VERSION_PATTERN.test(normalizedVersion)) {
    return 'synthetic';
  }

  // 3. data_source 模式兜底
  const normalizedSource = normalizeLower(dataSource);
  if (normalizedSource) {
    for (const { pattern, sourceType } of DATA_SOURCE_PATTERNS) {
      if (pattern.test(normalizedSource)) {
        return sourceType;
      }
    }
  }

  // 4. 无法判断
  return 'unknown';
}

/**
 * 从 source_type 推导 evidence_level。
 *
 * @param {string} sourceType
 * @returns {string} evidence_level 值
 */
function computeEvidenceLevel(sourceType) {
  return EVIDENCE_LEVEL_MAP[sourceType] || 'missing';
}

/**
 * 判断是否在生产范围内。
 * 当前仅 Ligue 1 / 2025/2026 为 true。
 *
 * @param {Object} context
 * @param {string} [context.leagueName]
 * @param {string} [context.season]
 * @returns {boolean}
 */
function computeProductionScope(context = {}) {
  const safeContext = context || {};
  const { leagueName, season } = safeContext;
  const normalizedLeague = normalizeText(leagueName);
  const normalizedSeason = normalizeText(season);
  if (!normalizedLeague || !normalizedSeason) return false;
  return (
    PRODUCTION_LEAGUES.includes(normalizedLeague) &&
    normalizedSeason === PRODUCTION_SEASON
  );
}

/**
 * 判断是否可以进入 reconciliation。
 *
 * 条件（全部满足）：
 *   - status = finished
 *   - 有 fotmob_live_v1 raw
 *   - evidence_level = strong
 *   - is_production_scope = true
 *
 * @param {Object} context
 * @param {string} [context.status]
 * @param {boolean} [context.hasFotmobLiveV1Raw]
 * @param {string} [context.evidenceLevel]
 * @param {boolean} [context.isProductionScope]
 * @returns {boolean}
 */
function computeReconciliationEligibility(context = {}) {
  const safeContext = context || {};
  const {
    status,
    hasFotmobLiveV1Raw,
    evidenceLevel,
    isProductionScope,
  } = safeContext;
  if (normalizeLower(status) !== 'finished') return false;
  if (!hasFotmobLiveV1Raw) return false;
  if (evidenceLevel !== 'strong') return false;
  if (!isProductionScope) return false;
  return true;
}

/**
 * 判断是否可以用于训练。
 * 当前保守策略：一律 false，等训练准入规则明确后再调整。
 *
 * @returns {boolean}
 */
function computeTrainingEligibility(/* _context */) {
  return false;
}

/**
 * 计算 pipeline_status_reason。
 *
 * 按优先级依次检查，返回第一个匹配的原因：
 *   1. 未完赛 → awaiting_match_completion
 *   2. 合成数据 → synthetic_raw_not_valid
 *   3. 非生产联赛 → non_production_league
 *   4. pending 且无 fotmob_live_v1 raw → pending_without_fotmob_live_v1_raw
 *   5. external_id 缺失或不可信 → external_id_unverified
 *   6. 无 fotmob 证据 → no_fotmob_evidence
 *   7. 无明确原因 → NULL
 *
 * @param {Object} context
 * @param {string} [context.status]
 * @param {string} [context.pipelineStatus]
 * @param {boolean} [context.hasFotmobLiveV1Raw]
 * @param {string} [context.sourceType]
 * @param {boolean} [context.isProductionScope]
 * @param {string} [context.externalId]
 * @returns {string|null}
 */
function computePipelineStatusReason(context = {}) {
  const safeContext = context || {};
  const {
    status,
    pipelineStatus,
    hasFotmobLiveV1Raw,
    sourceType,
    isProductionScope,
    externalId,
  } = safeContext;
  const normalizedStatus = normalizeLower(status);
  const normalizedPipelineStatus = normalizeLower(pipelineStatus);

  // 1. 未完赛
  if (
    normalizedStatus !== 'finished' &&
    normalizedPipelineStatus !== 'failed' &&
    normalizedPipelineStatus !== 'skipped'
  ) {
    return 'awaiting_match_completion';
  }

  // 2. 合成数据
  if (sourceType === 'synthetic') {
    return 'synthetic_raw_not_valid';
  }

  // 3. 非生产联赛
  if (isProductionScope === false) {
    return 'non_production_league';
  }

  // 4. 无 fotmob_live_v1 raw
  if (!hasFotmobLiveV1Raw) {
    return 'pending_without_fotmob_live_v1_raw';
  }

  // 5. external_id 缺失
  const normalizedExternalId = normalizeText(externalId);
  if (!normalizedExternalId) {
    return 'external_id_unverified';
  }

  // 6. 无明确原因
  return null;
}

// ---------------------------------------------------------------------------
// 主入口：一次性计算全部 6 个治理字段
// ---------------------------------------------------------------------------

/**
 * 计算全部 6 个治理标签字段。
 *
 * @param {Object} context
 * @param {string} [context.dataVersion]     - raw_match_data.data_version（如果存在）
 * @param {string} [context.dataSource]      - matches.data_source
 * @param {string} [context.leagueName]      - matches.league_name
 * @param {string} [context.season]          - matches.season
 * @param {string} [context.status]          - matches.status
 * @param {string} [context.pipelineStatus]  - matches.pipeline_status
 * @param {boolean} [context.hasFotmobLiveV1Raw] - raw_match_data 中是否有 fotmob_live_v1
 * @param {string} [context.externalId]      - matches.external_id
 * @returns {{
 *   source_type: string,
 *   evidence_level: string,
 *   is_production_scope: boolean,
 *   is_reconciliation_eligible: boolean,
 *   is_training_eligible: boolean,
 *   pipeline_status_reason: string|null
 * }}
 */
function computeGovernanceLabels(context = {}) {
  const safeContext = context || {};
  const sourceType = computeSourceType(safeContext);
  const evidenceLevel = computeEvidenceLevel(sourceType);
  const isProductionScope = computeProductionScope(safeContext);
  const isReconciliationEligible = computeReconciliationEligibility({
    status: safeContext.status,
    hasFotmobLiveV1Raw: safeContext.hasFotmobLiveV1Raw,
    evidenceLevel,
    isProductionScope,
  });
  const isTrainingEligible = computeTrainingEligibility(safeContext);
  const pipelineStatusReason = computePipelineStatusReason({
    status: safeContext.status,
    pipelineStatus: safeContext.pipelineStatus,
    hasFotmobLiveV1Raw: safeContext.hasFotmobLiveV1Raw,
    sourceType,
    isProductionScope,
    externalId: safeContext.externalId,
  });

  return {
    source_type: sourceType,
    evidence_level: evidenceLevel,
    is_production_scope: isProductionScope,
    is_reconciliation_eligible: isReconciliationEligible,
    is_training_eligible: isTrainingEligible,
    pipeline_status_reason: pipelineStatusReason,
  };
}

// ---------------------------------------------------------------------------
// 导出
// ---------------------------------------------------------------------------

module.exports = {
  // 常量
  DATA_VERSION_TO_SOURCE_TYPE,
  DATA_SOURCE_PATTERNS,
  SYNTHETIC_VERSION_PATTERN,
  EVIDENCE_LEVEL_MAP,
  PRODUCTION_LEAGUES,
  PRODUCTION_SEASON,

  // 子函数（便于单元测试）
  computeSourceType,
  computeEvidenceLevel,
  computeProductionScope,
  computeReconciliationEligibility,
  computeTrainingEligibility,
  computePipelineStatusReason,

  // 主入口
  computeGovernanceLabels,
};
