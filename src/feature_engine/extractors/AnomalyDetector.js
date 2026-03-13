/**
 * AnomalyDetector - V177 三维异常检测引擎
 * ========================================
 *
 * 从 GoldenDataMerger.py 迁移的核心业务逻辑
 * 检测：核心球员缺阵、身价断层、赔率背离
 * @module feature_engine/extractors/AnomalyDetector
 * @version V177.0.0
 */

'use strict';

// ============================================================================
// 常量配置
// ============================================================================

const ANOMALY_CONFIG = {
    // 置信度惩罚权重
    severityWeights: {
        HIGH: 0.15,
        MEDIUM: 0.08,
        LOW: 0.03
    },

    // 核心球员位置
    keyPositions: ['GK', 'CB', 'CM', 'ST', 'CF', 'CAM', 'CDM', 'LW', 'RW', 'LB', 'RB'],

    // 核心球员评分阈值
    keyPlayerRatingThreshold: 7.0,

    // 身价断层阈值 (欧元)
    hugeMarketValueGapThreshold: 100_000_000,  // 1亿欧元

    // 模型与市场背离阈值
    modelMarketDivergenceThreshold: 0.15  // 15%
};

// ============================================================================
// AnomalyDetector 类
// ============================================================================

/**
 *
 */
class AnomalyDetector {
    /**
     *
     * @param config
     */
    constructor(config = {}) {
        this.config = { ...ANOMALY_CONFIG, ...config };
    }

    /**
     * 执行三维异常检测
     * @param {object} params - 检测参数
     * @param {object} params.fundamentals - 基本面数据 (阵容、伤病)
     * @param {object} params.oddsData - 赔率数据
     * @param {object} params.prediction - 模型预测结果
     * @returns {object} 异常分析结果
     */
    analyze({ fundamentals, oddsData, prediction }) {
        const anomalies = [];
        const result = {
            detected: false,
            anomalies: [],
            confidence_adjustment: 1.0,
            summary: ''
        };

        // 1. 核心球员缺阵检测
        const playerAnomaly = this._checkKeyPlayerMissing(fundamentals);
        if (playerAnomaly) {
            anomalies.push(playerAnomaly);
        }

        // 2. 身价断层检测
        const mvAnomaly = this._checkMarketValueGap(fundamentals);
        if (mvAnomaly) {
            anomalies.push(mvAnomaly);
        }

        // 3. 模型与市场背离检测
        const divergenceAnomaly = this._checkModelMarketDivergence(oddsData, prediction);
        if (divergenceAnomaly) {
            anomalies.push(divergenceAnomaly);
        }

        // 汇总结果
        if (anomalies.length > 0) {
            result.detected = true;
            result.anomalies = anomalies;

            // 计算置信度惩罚
            const totalPenalty = anomalies.reduce((sum, a) => {
                return sum + (this.config.severityWeights[a.severity] || 0);
            }, 0);

            result.confidence_adjustment = Math.max(0.5, 1.0 - totalPenalty);
            result.summary = this._generateSummary(anomalies);
        }

        return result;
    }

    /**
     * 检测核心球员缺阵
     * @param fundamentals
     */
    _checkKeyPlayerMissing(fundamentals) {
        if (!fundamentals) return null;

        const homeMissing = fundamentals.home_missing || [];
        const awayMissing = fundamentals.away_missing || [];

        const keyPlayersHome = homeMissing.filter(p => this._isKeyPlayer(p)).length;
        const keyPlayersAway = awayMissing.filter(p => this._isKeyPlayer(p)).length;

        if (keyPlayersHome === 0 && keyPlayersAway === 0) {
            return null;
        }

        const totalKeyMissing = keyPlayersHome + keyPlayersAway;

        return {
            type: 'KEY_PLAYER_MISSING',
            severity: totalKeyMissing >= 2 ? 'HIGH' : 'MEDIUM',
            details: {
                home_key_missing: keyPlayersHome,
                away_key_missing: keyPlayersAway,
                total_key_missing: totalKeyMissing,
                home_missing_list: homeMissing.slice(0, 3).map(p => p.name || 'Unknown'),
                away_missing_list: awayMissing.slice(0, 3).map(p => p.name || 'Unknown')
            }
        };
    }

    /**
     * 检测身价断层
     * @param fundamentals
     */
    _checkMarketValueGap(fundamentals) {
        if (!fundamentals || fundamentals.market_value_gap === undefined) {
            return null;
        }

        const mvGap = Math.abs(fundamentals.market_value_gap);

        if (mvGap <= this.config.hugeMarketValueGapThreshold) {
            return null;
        }

        return {
            type: 'HUGE_MARKET_VALUE_GAP',
            severity: 'MEDIUM',
            details: {
                gap_eur: fundamentals.market_value_gap,
                gap_million_eur: Math.round(mvGap / 1_000_000),
                direction: fundamentals.market_value_gap > 0 ? 'home_stronger' : 'away_stronger'
            }
        };
    }

    /**
     * 检测模型与市场背离
     * @param oddsData
     * @param prediction
     */
    _checkModelMarketDivergence(oddsData, prediction) {
        if (!prediction || !oddsData) return null;

        const avgOdds = oddsData.avg_odds || oddsData;
        const finalH = parseFloat(avgOdds.final_h) || 2.0;
        const finalD = parseFloat(avgOdds.final_d) || 3.3;
        const finalA = parseFloat(avgOdds.final_a) || 3.5;

        // 计算市场隐含概率
        const total = (1 / finalH) + (1 / finalD) + (1 / finalA);
        const marketProbs = {
            'Home': (1 / finalH) / total,
            'Draw': (1 / finalD) / total,
            'Away': (1 / finalA) / total
        };

        const modelPred = prediction.final_prediction || prediction.prediction || '';
        const modelConf = parseFloat(prediction.final_confidence || prediction.confidence) || 0.5;
        const marketProb = marketProbs[modelPred] || 0.33;

        const gap = Math.abs(modelConf - marketProb);

        if (gap <= this.config.modelMarketDivergenceThreshold) {
            return null;
        }

        return {
            type: 'MODEL_MARKET_DIVERGENCE',
            severity: 'MEDIUM',
            details: {
                model_prediction: modelPred,
                model_confidence: Math.round(modelConf * 100) / 100,
                market_probability: Math.round(marketProb * 100) / 100,
                gap: Math.round(gap * 100) / 100,
                interpretation: modelConf > marketProb ? '模型更看好' : '市场更看好'
            }
        };
    }

    /**
     * 判断是否为核心球员
     * @param player
     */
    _isKeyPlayer(player) {
        if (!player) return false;

        // 基于位置判断
        const position = (player.position || '').toUpperCase();
        if (this.config.keyPositions.includes(position)) {
            return true;
        }

        // 基于评分判断
        const rating = parseFloat(player.rating);
        if (!isNaN(rating) && rating >= this.config.keyPlayerRatingThreshold) {
            return true;
        }

        // 基于原因判断 (关键伤病)
        const reason = (player.reason || '').toLowerCase();
        const keyReasons = ['injury', 'suspension', 'red card', 'muscular', 'knee', 'ankle'];
        if (keyReasons.some(r => reason.includes(r))) {
            return true;
        }

        return false;
    }

    /**
     * 生成异常摘要
     * @param anomalies
     */
    _generateSummary(anomalies) {
        const parts = [];

        for (const anomaly of anomalies) {
            switch (anomaly.type) {
                case 'KEY_PLAYER_MISSING':
                    parts.push(`核心缺阵:${anomaly.details.total_key_missing}人`);
                    break;
                case 'HUGE_MARKET_VALUE_GAP':
                    parts.push(`身价差:€${anomaly.details.gap_million_eur}M`);
                    break;
                case 'MODEL_MARKET_DIVERGENCE':
                    parts.push(`模型背离:${Math.round(anomaly.details.gap * 100)}%`);
                    break;
            }
        }

        return parts.join(' | ');
    }

    /**
     * 应用置信度调整到预测结果
     * @param {object} prediction - 原始预测结果
     * @param {object} anomalyResult - 异常检测结果
     * @returns {object} 调整后的预测结果
     */
    applyAdjustment(prediction, anomalyResult) {
        if (!anomalyResult.detected) {
            return prediction;
        }

        const adjusted = { ...prediction };
        const originalConf = parseFloat(prediction.final_confidence || prediction.confidence) || 0.5;
        adjusted.original_confidence = originalConf;
        adjusted.final_confidence = Math.max(0.1, originalConf * anomalyResult.confidence_adjustment);
        adjusted.anomaly_detected = true;
        adjusted.anomaly_summary = anomalyResult.summary;
        adjusted.anomalies = anomalyResult.anomalies;

        return adjusted;
    }
}

// ============================================================================
// 导出
// ============================================================================

module.exports = {
    AnomalyDetector,
    ANOMALY_CONFIG
};
