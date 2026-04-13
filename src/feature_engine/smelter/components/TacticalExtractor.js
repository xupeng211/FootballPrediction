/**
 * TacticalExtractor - V5.2 战术动量特征提取器
 * =============================================
 *
 * 从 FotMob L2 原始数据中提取战术统计和比赛动量特征：
 * 1. 战术特征 (xG, 控球率, 射门, 角球等)
 * 2. 动量特征 (momentum 时间序列分析)
 *
 * V5.2 模块化:
 * - 继承 BaseExtractor，符合行业标准
 * @module feature_engine/smelter/components/TacticalExtractor
 * @version V5.2.0-HOME-FORTRESS
 * @since 2026-03-14
 */

'use strict';

const { BaseExtractor } = require('./BaseExtractor');
const {
  STATS_MAPPING,
  applyMomentumFallback,
  assignMomentumSegmentFeatures,
  assignMomentumSummary,
  calculateAdvancedFeatures,
  createDefaultStatsFeatures,
  extractMomentumValues,
  extractStatsFromArray,
  resolveMomentumData
} = require('../../../feature_engine/shared/tacticalFeatureHelpers');

const DEFAULT_CONFIG = {
  momentumSegments: 6,
  momentumThreshold: 0.6,
  statsPath: 'content.stats.Periods.All.stats',
  defaults: {
    xg: 0,
    possession: 50,
    shots: 0,
    corners: 0
  },
  strictMode: false
};

const FEATURE_NAMES = [
  'home_xg', 'away_xg', 'total_xg', 'xg_diff', 'xg_ratio',
  'home_xg_per_shot', 'away_xg_per_shot',
  'home_possession', 'away_possession',
  'home_possession_pct', 'away_possession_pct',
  'possession_diff', 'possession_ratio',
  'home_shots', 'away_shots',
  'home_shots_on_target', 'away_shots_on_target',
  'home_shots_off_target', 'away_shots_off_target',
  'home_shot_accuracy', 'away_shot_accuracy',
  'shots_on_target_diff',
  'home_corners', 'away_corners',
  'corners_diff', 'total_corners',
  'home_fouls', 'away_fouls',
  'home_yellow_cards', 'away_yellow_cards',
  'home_red_cards', 'away_red_cards',
  'fouls_diff', 'total_fouls',
  'home_discipline_score', 'away_discipline_score',
  'discipline_diff',
  'home_big_chances', 'away_big_chances',
  'big_chances_diff',
  'home_strength_index', 'away_strength_index',
  'strength_diff',
  'has_momentum_data',
  'momentum_samples_count',
  'momentum_overall_mean',
  'momentum_direction',
  'momentum_trend',
  'momentum_seg1_mean', 'momentum_seg1_std', 'momentum_seg1_dominance',
  'momentum_seg2_mean', 'momentum_seg2_std', 'momentum_seg2_dominance',
  'momentum_seg3_mean', 'momentum_seg3_std', 'momentum_seg3_dominance',
  'momentum_seg4_mean', 'momentum_seg4_std', 'momentum_seg4_dominance',
  'momentum_seg5_mean', 'momentum_seg5_std', 'momentum_seg5_dominance',
  'momentum_seg6_mean', 'momentum_seg6_std', 'momentum_seg6_dominance'
];

class TacticalExtractor extends BaseExtractor {
  constructor(config = {}) {
    super({
      name: 'TacticalExtractor',
      version: 'V5.2.0-HOME-FORTRESS',
      requiredFields: ['content.stats'],
      config: { ...DEFAULT_CONFIG, ...config }
    });

    this.cfg = this.config;
  }

  getDefaultConfig() {
    return DEFAULT_CONFIG;
  }

  getFeatureNames() {
    return FEATURE_NAMES;
  }

  extract(rawData) {
    if (!rawData || !this.isValidObject(rawData)) {
      return this.createEmptyFeatures('无效的原始数据');
    }

    const statsFeatures = this._extractStatsFeatures(rawData);
    const momentumFeatures = this._extractMomentumFeatures(rawData);
    return {
      ...statsFeatures,
      ...momentumFeatures,
      ...calculateAdvancedFeatures({ ...statsFeatures, ...momentumFeatures })
    };
  }

  _extractStatsFeatures(rawData) {
    const allStats = this.safeGet(rawData, this.cfg.statsPath, null);
    if (Array.isArray(allStats)) {
      return extractStatsFromArray(allStats, STATS_MAPPING);
    }

    const altStats = this.safeGet(rawData, 'content.stats', null);
    return Array.isArray(altStats)
      ? extractStatsFromArray(altStats, STATS_MAPPING)
      : createDefaultStatsFeatures();
  }

  _extractMomentumFeatures(rawData) {
    const features = {
      has_momentum_data: false,
      momentum_samples_count: 0
    };
    const momentum = resolveMomentumData(rawData, this.safeGet.bind(this), this.isValidObject.bind(this));
    if (!Array.isArray(momentum) || momentum.length < 3) {
      applyMomentumFallback(features, this.cfg.momentumSegments, 50);
      features.momentum_fallback = true;
      return features;
    }

    const readValue = (sample) => (
      typeof sample === 'object'
        ? this.safeGet(sample, 'value', 0)
        : typeof sample === 'number'
          ? sample
          : 0
    );

    features.has_momentum_data = true;
    features.momentum_samples_count = momentum.length;
    assignMomentumSegmentFeatures(features, momentum, this.cfg.momentumSegments, readValue);
    assignMomentumSummary(features, extractMomentumValues(momentum, readValue));
    return features;
  }
}

module.exports = {
  TacticalExtractor,
  DEFAULT_CONFIG,
  FEATURE_NAMES,
  STATS_MAPPING
};
