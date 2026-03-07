/**
 * 共享常量加载器 - V1.0.0
 * ======================
 *
 * 从 config/shared_constants.json 加载全局共享常量，确保 Python/Node.js 一致性。
 *
 * V4.17: 建立跨语言常量统一标准
 *
 * 使用方法:
 *   const { MATCH_STATUS, MATCH_OUTCOME, HOME_WIN } = require('../config/shared_constants');
 *
 *   // 比赛状态
 *   const status = MATCH_STATUS.FINISHED;  // "finished"
 *
 *   // 比赛结果
 *   const result = MATCH_OUTCOME.HOME_WIN;  // 2
 *
 * @module config/shared_constants
 * @version V1.0.0
 * @since 2026-03-07
 */

'use strict';

const fs = require('fs');
const path = require('path');

// 加载共享常量 JSON
const CONSTANTS_PATH = path.join(__dirname, 'shared_constants.json');
let sharedConstants = null;

/**
 * 加载共享常量（带缓存）
 * @returns {Object} 共享常量对象
 */
function loadConstants() {
    if (sharedConstants) {
        return sharedConstants;
    }

    const content = fs.readFileSync(CONSTANTS_PATH, 'utf8');
    sharedConstants = JSON.parse(content);
    return sharedConstants;
}

/**
 * 重新加载常量（用于热更新）
 * @returns {Object} 共享常量对象
 */
function reloadConstants() {
    sharedConstants = null;
    return loadConstants();
}

// 加载常量
const constants = loadConstants();

// ============================================================================
// 比赛状态枚举
// ============================================================================

const MATCH_STATUS = Object.freeze({
    FINISHED: constants.match_status.FINISHED,      // "finished"
    LIVE: constants.match_status.LIVE,              // "live"
    SCHEDULED: constants.match_status.SCHEDULED,    // "scheduled"
    CANCELLED: constants.match_status.CANCELLED,    // "cancelled"
    COMPLETED: constants.match_status.COMPLETED,    // "completed"
    POSTPONED: constants.match_status.POSTPONED,    // "postponed"
    ABANDONED: constants.match_status.ABANDONED,    // "abandoned"

    /**
     * 检查状态是否为终态（不可变更）
     * @param {string} status - 状态值
     * @returns {boolean} 是否为终态
     */
    isTerminal(status) {
        const s = status?.toLowerCase();
        return s === this.FINISHED || s === this.CANCELLED || s === this.COMPLETED;
    },

    /**
     * 检查状态是否为活跃状态
     * @param {string} status - 状态值
     * @returns {boolean} 是否为活跃状态
     */
    isActive(status) {
        const s = status?.toLowerCase();
        return s === this.LIVE || s === this.SCHEDULED;
    }
});

// ============================================================================
// 比赛结果枚举
// ============================================================================

const MATCH_OUTCOME = Object.freeze({
    AWAY_WIN: constants.match_outcome.AWAY_WIN,  // 0
    DRAW: constants.match_outcome.DRAW,           // 1
    HOME_WIN: constants.match_outcome.HOME_WIN,   // 2

    /**
     * 根据比分确定结果
     * @param {number} homeScore - 主队得分
     * @param {number} awayScore - 客队得分
     * @returns {number} 结果 (0=客胜, 1=平局, 2=主胜)
     */
    fromScores(homeScore, awayScore) {
        if (homeScore > awayScore) return this.HOME_WIN;
        if (homeScore < awayScore) return this.AWAY_WIN;
        return this.DRAW;
    },

    /**
     * 获取所有标签（按顺序）
     * @returns {number[]} [0, 1, 2]
     */
    getAllLabels() {
        return [this.AWAY_WIN, this.DRAW, this.HOME_WIN];
    },

    /**
     * 获取标签名称
     * @param {number} label - 标签值
     * @returns {string} 标签名称
     */
    getLabelName(label) {
        const names = {
            [this.AWAY_WIN]: 'AWAY_WIN',
            [this.DRAW]: 'DRAW',
            [this.HOME_WIN]: 'HOME_WIN'
        };
        return names[label] || 'UNKNOWN';
    }
});

// ============================================================================
// 默认概率配置
// ============================================================================

const DEFAULT_PROBABILITIES = Object.freeze({
    HOME_WIN: constants.default_probabilities.HOME_WIN,  // 0.46
    DRAW: constants.default_probabilities.DRAW,           // 0.26
    AWAY_WIN: constants.default_probabilities.AWAY_WIN,   // 0.28

    /**
     * 转换为数组（按 AWAY_WIN, DRAW, HOME_WIN 顺序）
     * @returns {number[]} [0.28, 0.26, 0.46]
     */
    toArray() {
        return [this.AWAY_WIN, this.DRAW, this.HOME_WIN];
    },

    /**
     * 转换为对象
     * @returns {Object} 概率对象
     */
    toObject() {
        return {
            HOME_WIN: this.HOME_WIN,
            DRAW: this.DRAW,
            AWAY_WIN: this.AWAY_WIN
        };
    }
});

// ============================================================================
// 赔率限制配置
// ============================================================================

const ODDS_LIMITS = Object.freeze({
    MIN_ODDS: constants.odds_limits.min_odds,       // 1.01
    MAX_ODDS: constants.odds_limits.max_odds,       // 1000.0
    MIN_PAYOUT: constants.odds_limits.min_payout,   // 1.02
    MAX_PAYOUT: constants.odds_limits.max_payout,   // 1.08

    /**
     * 检查赔率是否在有效范围内
     * @param {number} odds - 赔率值
     * @returns {boolean} 是否有效
     */
    isValidOdds(odds) {
        return odds >= this.MIN_ODDS && odds <= this.MAX_ODDS;
    },

    /**
     * 检查返还率是否在有效范围内
     * @param {number} payout - 返还率
     * @returns {boolean} 是否有效
     */
    isValidPayout(payout) {
        return payout >= this.MIN_PAYOUT && payout <= this.MAX_PAYOUT;
    }
});

// ============================================================================
// 置信度阈值配置
// ============================================================================

const CONFIDENCE_THRESHOLDS = Object.freeze({
    HIGH: constants.confidence_thresholds.high,       // 0.70
    MEDIUM: constants.confidence_thresholds.medium,   // 0.55
    LOW: constants.confidence_thresholds.low,         // 0.40

    /**
     * 根据置信度获取等级
     * @param {number} confidence - 置信度
     * @returns {string} 等级名称
     */
    getLevel(confidence) {
        if (confidence >= this.HIGH) return 'HIGH';
        if (confidence >= this.MEDIUM) return 'MEDIUM';
        if (confidence >= this.LOW) return 'LOW';
        return 'VERY_LOW';
    }
});

// ============================================================================
// 向后兼容常量（直接导出数值）
// ============================================================================

// 比赛结果（整数）
const HOME_WIN = MATCH_OUTCOME.HOME_WIN;  // 2
const DRAW = MATCH_OUTCOME.DRAW;           // 1
const AWAY_WIN = MATCH_OUTCOME.AWAY_WIN;   // 0

// 比赛状态（字符串）
const STATUS_FINISHED = MATCH_STATUS.FINISHED;      // "finished"
const STATUS_LIVE = MATCH_STATUS.LIVE;              // "live"
const STATUS_SCHEDULED = MATCH_STATUS.SCHEDULED;    // "scheduled"
const STATUS_CANCELLED = MATCH_STATUS.CANCELLED;    // "cancelled"

// ============================================================================
// 导出
// ============================================================================

module.exports = {
    // 枚举对象
    MATCH_STATUS,
    MATCH_OUTCOME,

    // 配置对象
    DEFAULT_PROBABILITIES,
    ODDS_LIMITS,
    CONFIDENCE_THRESHOLDS,

    // 向后兼容常量（比赛结果）
    HOME_WIN,
    DRAW,
    AWAY_WIN,

    // 向后兼容常量（比赛状态）
    STATUS_FINISHED,
    STATUS_LIVE,
    STATUS_SCHEDULED,
    STATUS_CANCELLED,

    // 工具函数
    loadConstants,
    reloadConstants
};
