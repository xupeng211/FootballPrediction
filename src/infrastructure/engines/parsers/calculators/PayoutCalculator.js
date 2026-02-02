/**
 * PayoutCalculator - V167.000 Consolidated Edition
 * ===================================================
 *
 * [Genesis.Reconstruction] Payout 计算引擎 - 独立模块
 *
 * 所有 Payout 计算逻辑集中管理，遵循单一职责原则。
 *
 * 统一公式: Payout% = 1 / (1/H + 1/D + 1/A) * 100
 *
 * @module parsers/calculators/PayoutCalculator
 * @version V167.000
 * @since 2026-02-02
 * @author [Genesis.Reconstruction]
 */

'use strict';

const { PAYOUT_CONFIG } = require('../../config/EngineConfig');

/**
 * V167.000: PayoutCalculator - 统一返还率计算引擎
 *
 * 所有 Payout 计算逻辑集中管理，遵循单一职责原则
 */
class PayoutCalculator {
    /**
     * V167.000: 计算市场返还率
     *
     * 统一公式: Payout% = 1 / (1/H + 1/D + 1/A) * 100
     *
     * @param {number} h - Home odds (主胜赔率)
     * @param {number} d - Draw odds (平局赔率)
     * @param {number} a - Away odds (客胜赔率)
     * @param {Object} options - 可选配置
     * @returns {number|null} 返还率百分比，无效输入返回 null
     *
     * @example
     * // 标准计算
     * PayoutCalculator.calculate(2.0, 3.5, 4.0);  // => 91.53
     *
     * // 边界情况
     * PayoutCalculator.calculate(0, 3.5, 4.0);     // => null (无效赔率)
     * PayoutCalculator.calculate(2.0, 3.5, null);   // => null (缺失赔率)
     */
    static calculate(h, d, a, options = {}) {
        const config = { ...PAYOUT_CONFIG, ...options };

        // 输入验证
        if (!PayoutCalculator._isValidOdds(h, d, a, config)) {
            return null;
        }

        // 统一公式计算
        const margin = (1 / h) + (1 / d) + (1 / a);
        const payout = margin > 0 ? (1 / margin) * 100 : null;

        // 范围验证
        if (payout === null) {
            return null;
        }

        if (payout < config.MIN_VALID_PAYOUT || payout > config.MAX_VALID_PAYOUT) {
            console.warn(`[PayoutCalculator] ⚠️ Payout out of range: ${payout.toFixed(2)}% (${config.MIN_VALID_PAYOUT}-${config.MAX_VALID_PAYOUT})`);
        }

        // 精度处理
        return parseFloat(payout.toFixed(config.PAYOUT_DECIMAL_PLACES));
    }

    /**
     * V167.000: 批量计算返还率
     * @param {Array} oddsArray - 赔率数组 [[h, d, a], ...]
     * @returns {Array} 返还率数组
     */
    static calculateBatch(oddsArray) {
        return oddsArray.map(([h, d, a]) => PayoutCalculator.calculate(h, d, a));
    }

    /**
     * V167.000: 验证赔率有效性
     * @private
     */
    static _isValidOdds(h, d, a, config) {
        // 检查是否存在 null/undefined
        if (h === null || h === undefined ||
            d === null || d === undefined ||
            a === null || a === undefined) {
            return false;
        }

        // 检查是否为有效数字
        if (isNaN(h) || isNaN(d) || isNaN(a)) {
            return false;
        }

        // 检查范围
        if (h < config.MIN_VALID_ODDS || h > config.MAX_VALID_ODDS ||
            d < config.MIN_VALID_ODDS || d > config.MAX_VALID_ODDS ||
            a < config.MIN_VALID_ODDS || a > config.MAX_VALID_ODDS) {
            return false;
        }

        // 检查是否为正数
        if (h <= 0 || d <= 0 || a <= 0) {
            return false;
        }

        return true;
    }

    /**
     * V167.000: 从赔率对象计算返还率
     * @param {Object} odds - 赔率对象 {home, draw, away}
     * @returns {number|null} 返还率百分比
     */
    static fromOddsObject(odds) {
        if (!odds || typeof odds !== 'object') {
            return null;
        }

        const h = parseFloat(odds.home || odds.h || odds.H);
        const d = parseFloat(odds.draw || odds.d || odds.D);
        const a = parseFloat(odds.away || odds.a || odds.A);

        return PayoutCalculator.calculate(h, d, a);
    }

    /**
     * V167.000: 判断返还率是否健康
     * @param {number} payout - 返还率
     * @returns {boolean} 是否健康
     */
    static isHealthy(payout) {
        return payout !== null &&
               payout >= PAYOUT_CONFIG.MIN_VALID_PAYOUT &&
               payout <= PAYOUT_CONFIG.MAX_VALID_PAYOUT;
    }
}

module.exports = { PayoutCalculator };
