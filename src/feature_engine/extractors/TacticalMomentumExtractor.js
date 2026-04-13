/**
 * TacticalMomentumExtractor - 战术动量特征提取器
 * ================================================
 *
 * 从 FotMob L2 原始数据中提取战术统计和比赛动量特征：
 * 1. 战术特征 (xG, 控球率, 射门, 角球等)
 * 2. 动量特征 (momentum 时间序列分析)
 * @module feature_engine/extractors/TacticalMomentumExtractor
 * @version V176.0.0
 */

'use strict';

const { safeGet, is } = require('../../core/utils/SafeAccess');
const {
  applyMomentumFallback,
  assignMomentumSegmentFeatures,
  assignMomentumSummary,
  calculateAdvancedFeatures,
  createDefaultStatsFeatures,
  extractMomentumValues,
  extractStatsFromArray,
  resolveMomentumData
} = require('../shared/tacticalFeatureHelpers');

const DEFAULT_CONFIG = {
  momentumSegments: 6,
  momentumThreshold: 0.6,
  statsPath: 'content.stats.Periods.All.stats',
  defaults: {
    xg: 0,
    possession: 50,
    shots: 0,
    corners: 0
  }
};

function createEmptyTacticalFeatures() {
  return {
    ...createDefaultStatsFeatures(),
    has_momentum_data: false,
    momentum_samples_count: 0,
    _error: 'No valid raw data provided',
    _version: 'V176.0.0',
    _extractedAt: new Date().toISOString()
  };
}

function extractStatsFeatures(rawData, config) {
  const allStats = safeGet(rawData, config.statsPath, null);
  if (Array.isArray(allStats)) {
    return extractStatsFromArray(allStats);
  }

  const altStats = safeGet(rawData, 'content.stats', null);
  return Array.isArray(altStats) ? extractStatsFromArray(altStats) : createDefaultStatsFeatures();
}

function readMomentumValue(sample) {
  return typeof sample === 'object'
    ? safeGet(sample, 'value', 0)
    : typeof sample === 'number'
      ? sample
      : 0;
}

function createFallbackMomentumFeatures(features, config) {
  const homePossession = features.home_possession_pct || 50;
  const homeShots = features.home_shots || 0;
  const awayShots = features.away_shots || 0;
  const homeXg = features.home_xg || 0;
  const awayXg = features.away_xg || 0;
  const possessionFactor = (homePossession - 50) / 50;
  const shotsFactor = homeShots + awayShots > 0 ? (homeShots - awayShots) / (homeShots + awayShots) : 0;
  const xgFactor = homeXg + awayXg > 0 ? (homeXg - awayXg) / (homeXg + awayXg) : 0;
  const estimatedDominance = Math.round((possessionFactor * 0.3 + shotsFactor * 0.35 + xgFactor * 0.35) * 50 + 50);

  applyMomentumFallback(features, config.momentumSegments, estimatedDominance);
  features.momentum_fallback = true;
  return features;
}

function extractMomentumFeatures(rawData, config, statsFeatures = {}) {
  const features = {
    has_momentum_data: false,
    momentum_samples_count: 0
  };
  const momentum = resolveMomentumData(rawData, safeGet, is.object);

  if (!Array.isArray(momentum) || momentum.length < 3) {
    return createFallbackMomentumFeatures({ ...features, ...statsFeatures }, rawData, config);
  }

  features.has_momentum_data = true;
  features.momentum_samples_count = momentum.length;
  assignMomentumSegmentFeatures(features, momentum, config.momentumSegments, readMomentumValue);
  assignMomentumSummary(features, extractMomentumValues(momentum, readMomentumValue));
  return features;
}

function extractTacticalFeatures(rawData, config = DEFAULT_CONFIG) {
  if (!rawData || !is.object(rawData)) {
    return createEmptyTacticalFeatures();
  }

  const cfg = { ...DEFAULT_CONFIG, ...config };
  const statsFeatures = extractStatsFeatures(rawData, cfg);
  const momentumFeatures = extractMomentumFeatures(rawData, cfg, statsFeatures);
  const features = {
    ...statsFeatures,
    ...momentumFeatures,
    ...calculateAdvancedFeatures({ ...statsFeatures, ...momentumFeatures }),
    _extractedAt: new Date().toISOString(),
    _version: 'V176.0.0'
  };

  return features;
}

module.exports = {
  extractTacticalFeatures,
  extractStatsFeatures,
  extractMomentumFeatures,
  calculateAdvancedFeatures,
  createEmptyTacticalFeatures,
  DEFAULT_CONFIG
};
