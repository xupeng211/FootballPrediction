/**
 * V4.46.2 统一常量配置
 * ====================
 *
 * 所有业务系统的魔术数字统一归口管理
 * 严禁在业务代码中硬编码参数
 *
 * @module config/constants
 * @version V4.46.2
 */

'use strict';

// ============================================================================
// 数据库配置
// ============================================================================

const DB_MAX_RETRIES = parseInt(process.env.DB_MAX_RETRIES) || 3;
const DB_RETRY_DELAY_MS = parseInt(process.env.DB_RETRY_DELAY_MS) || 1000;
const DB_RETRY_BACKOFF_MULTIPLIER = parseFloat(process.env.DB_RETRY_BACKOFF_MULTIPLIER) || 2;

// ============================================================================
// Elo 配置
// ============================================================================

const DEFAULT_ELO_RATING = 1500;
const ELO_K_FACTOR = 32;

// ============================================================================
// 市场价值配置
// ============================================================================

const MARKET_VALUE_MULTIPLIER = 10000; // 万欧元 (FotMob API 返回的单位是万欧元)

// ============================================================================
// 日志级别
// ============================================================================

const LOG_LEVELS = {
    DEBUG: 'debug',
    INFO: 'info',
    WARN: 'warn',
    ERROR: 'error'
};

// ============================================================================
// 比赛状态
// ============================================================================

const MATCH_STATUS = {
    FINISHED: 'finished',
    LIVE: 'live',
    SCHEDULED: 'scheduled',
    CANCELLED: 'cancelled',
    COMPLETED: 'completed',
    POSTPONED: 'postponed',

    /**
     * 从FotMob状态转换为内部状态
     * @param {object} status - FotMob状态对象
     * @param {boolean} status.finished - 是否完场
     * @param {boolean} status.started - 是否开始
     * @param {boolean} status.cancelled - 是否取消
     * @param {boolean} status.awarded - 是否判给
     * @param {number|null} homeScore - 主队比分
     * @param {number|null} awayScore - 客队比分
     * @returns {string} 内部状态字符串
     */
    fromFotMob(status, homeScore, awayScore) {
        if (!status) return 'scheduled';

        if (status.awarded) return 'awarded';
        if (status.cancelled) return 'cancelled';
        if (status.finished) return 'finished';
        if (status.started) return 'live';

        return 'scheduled';
    }
};

// ============================================================================
// 比赛结果
// ============================================================================

const MATCH_OUTCOME = {
    AWAY_WIN: 0,
    DRAW: 1,
    HOME_WIN: 2
};

// ============================================================================
// 置信度阈值
// ============================================================================

const CONFIDENCE_THRESHOLDS = {
    HIGH: 0.70,
    MEDIUM: 0.55,
    LOW: 0.40
};

// ============================================================================
// 导出
// ============================================================================

module.exports = {
    // 数据库
    DB_MAX_RETRIES,
    DB_RETRY_DELAY_MS,
    DB_RETRY_BACKOFF_MULTIPLIER,

    // Elo
    DEFAULT_ELO_RATING,
    ELO_K_FACTOR,

    // 市场价值
    MARKET_VALUE_MULTIPLIER,

    // 日志
    LOG_LEVELS,

    // 比赛状态
    MATCH_STATUS,
    MATCH_OUTCOME,

    // 置信度
    CONFIDENCE_THRESHOLDS
};
