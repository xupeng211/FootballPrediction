/**
 * OddsFluxDetector - 赔率背离监测器
 * ===================================
 *
 * TITAN V5.0 首个预测算法模块
 * 监测赔率异常波动，识别潜在价值投注机会
 *
 * @module analysis/OddsFluxDetector
 * @version V5.0.0
 */

'use strict';

/**
 * 赔率背离检测结果
 * @typedef {Object} DeviationResult
 * @property {boolean} hasDeviation - 是否存在背离
 * @property {number} deviationRate - 背离率 (0-1)
 * @property {string} direction - 背离方向 ('up' | 'down' | 'none')
 * @property {number} signalStrength - 信号强度 (0-1)
 */

/**
 * 赔率背离监测器类
 */
class OddsFluxDetector {
    /**
     * 创建 OddsFluxDetector 实例
     * @param {object} config - 配置选项
     * @param {number} config.deviationThreshold - 背离阈值 (默认 0.15 = 15%)
     * @param {number} config.minOdds - 最小赔率 (默认 1.01)
     * @param {number} config.maxOdds - 最大赔率 (默认 1000)
     */
    constructor(config = {}) {
        this.config = {
            deviationThreshold: config.deviationThreshold || 0.15,
            minOdds: config.minOdds || 1.01,
            maxOdds: config.maxOdds || 1000
        };
    }

    /**
     * 检测赔率背离
     * @param {number} openingOdds - 初始赔率 (开盘赔率)
     * @param {number} currentOdds - 当前赔率 (收盘/实时赔率)
     * @returns {DeviationResult} 背离检测结果
     */
    detectDeviation(openingOdds, currentOdds) {
        // 验证输入
        if (!this._isValidOdds(openingOdds) || !this._isValidOdds(currentOdds)) {
            return {
                hasDeviation: false,
                deviationRate: 0,
                direction: 'none',
                signalStrength: 0,
                error: 'INVALID_ODDS'
            };
        }

        // 计算赔率变化率
        // 公式: (当前 - 初始) / 初始
        const changeRate = (currentOdds - openingOdds) / openingOdds;

        // 计算背离率 (绝对值)
        const deviationRate = Math.abs(changeRate);

        // 判断背离方向
        let direction = 'none';
        if (changeRate > 0) {
            direction = 'up'; // 赔率上升 = 胜率预期下降
        } else if (changeRate < 0) {
            direction = 'down'; // 赔率下降 = 胜率预期上升
        }

        // 判断是否触发背离阈值
        const hasDeviation = deviationRate > this.config.deviationThreshold;

        // 计算信号强度 (0-1)
        // 当背离率 = 阈值时，强度 = 0.5
        // 当背离率 >= 2倍阈值时，强度 = 1.0
        let signalStrength = 0;
        if (hasDeviation) {
            signalStrength = Math.min(1.0, 0.5 + (deviationRate - this.config.deviationThreshold) / this.config.deviationThreshold * 0.5);
        }

        return {
            hasDeviation,
            deviationRate: Math.round(deviationRate * 10000) / 10000, // 保留4位小数
            direction,
            signalStrength: Math.round(signalStrength * 100) / 100, // 保留2位小数
            openingOdds,
            currentOdds
        };
    }

    /**
     * 批量检测多组赔率背离
     * @param {Array<{openingOdds: number, currentOdds: number, matchId: string}>} oddsList - 赔率列表
     * @returns {Array<DeviationResult & {matchId: string}>} 批量检测结果
     */
    detectBatch(oddsList) {
        if (!Array.isArray(oddsList)) {
            return [];
        }

        return oddsList.map(item => {
            const result = this.detectDeviation(item.openingOdds, item.currentOdds);
            return {
                ...result,
                matchId: item.matchId || null
            };
        });
    }

    /**
     * 获取背离统计摘要
     * @param {Array<DeviationResult>} results - 检测结果列表
     * @returns {object} 统计摘要
     */
    getSummary(results) {
        if (!Array.isArray(results) || results.length === 0) {
            return {
                total: 0,
                deviationCount: 0,
                upCount: 0,
                downCount: 0,
                avgDeviationRate: 0,
                maxDeviationRate: 0
            };
        }

        const total = results.length;
        const deviationCount = results.filter(r => r.hasDeviation).length;
        const upCount = results.filter(r => r.direction === 'up').length;
        const downCount = results.filter(r => r.direction === 'down').length;

        const deviationRates = results.map(r => r.deviationRate);
        const avgDeviationRate = deviationRates.reduce((a, b) => a + b, 0) / total;
        const maxDeviationRate = Math.max(...deviationRates);

        return {
            total,
            deviationCount,
            upCount,
            downCount,
            avgDeviationRate: Math.round(avgDeviationRate * 10000) / 10000,
            maxDeviationRate: Math.round(maxDeviationRate * 10000) / 10000,
            deviationRate: Math.round((deviationCount / total) * 100) / 100
        };
    }

    /**
     * 验证赔率有效性
     * @private
     * @param {number} odds - 赔率值
     * @returns {boolean}
     */
    _isValidOdds(odds) {
        return typeof odds === 'number' &&
               !isNaN(odds) &&
               isFinite(odds) &&
               odds >= this.config.minOdds &&
               odds <= this.config.maxOdds;
    }

    /**
     * 更新配置
     * @param {object} newConfig - 新配置
     */
    updateConfig(newConfig) {
        this.config = {
            ...this.config,
            ...newConfig
        };
    }

    /**
     * 获取当前配置
     * @returns {object}
     */
    getConfig() {
        return { ...this.config };
    }
}

/**
 * 便捷函数：单例检测
 * @param {number} openingOdds - 初始赔率
 * @param {number} currentOdds - 当前赔率
 * @param {number} threshold - 背离阈值 (默认 0.15)
 * @returns {DeviationResult}
 */
function detectOddsFlux(openingOdds, currentOdds, threshold = 0.15) {
    const detector = new OddsFluxDetector({ deviationThreshold: threshold });
    return detector.detectDeviation(openingOdds, currentOdds);
}

module.exports = {
    OddsFluxDetector,
    detectOddsFlux
};
