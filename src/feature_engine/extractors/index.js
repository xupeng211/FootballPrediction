/**
 * V177 特征引擎 - 提取器模块
 * =============================
 *
 * 导出所有特征提取器
 *
 * @module feature_engine/extractors
 */

'use strict';

const GoldenFeatureExtractor = require('./GoldenFeatureExtractor');
const TacticalMomentumExtractor = require('./TacticalMomentumExtractor');
const EloRatingExtractor = require('./EloRatingExtractor');
const OddsMovementExtractor = require('./OddsMovementExtractor');
const { AnomalyDetector, ANOMALY_CONFIG } = require('./AnomalyDetector');

module.exports = {
    // 黄金特征提取器
    extractGoldenFeatures: GoldenFeatureExtractor.extractGoldenFeatures,
    GoldenFeatureExtractor,

    // 战术动量提取器
    extractTacticalFeatures: TacticalMomentumExtractor.extractTacticalFeatures,
    TacticalMomentumExtractor,

    // Elo 动态评分提取器
    EloRatingExtractor: EloRatingExtractor.EloRatingExtractor,
    calculateEloFeatures: EloRatingExtractor.calculateEloFeatures,

    // 赔率变动/Steam 信号提取器
    extractOddsMovementFeatures: OddsMovementExtractor.extractOddsMovementFeatures,
    OddsMovementExtractor,

    // V177: 异常检测器
    AnomalyDetector,
    ANOMALY_CONFIG,

    // 版本
    VERSION: 'V177.0.0'
};
