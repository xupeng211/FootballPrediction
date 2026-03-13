/**
 * V4.46.2 统一常量配置 (src/config)
 * ==================================
 *
 * 所有业务系统的魔术数字统一归口管理
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

const MARKET_VALUE_MULTIPLIER = 1000000; // 百万欧元

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
    POSTPONED: 'postponed'
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
// 特征工程常量
// ============================================================================

const FEATURE_CONSTANTS = {
    // Elo 差异阈值
    ELO_DIFF_THRESHOLD: 50,

    // 近期比赛场次
    RECENT_MATCHES_COUNT: 5,

    // 赔率变化阈值
    ODDS_CHANGE_THRESHOLD: 0.05,

    // 市场价值权重
    MARKET_VALUE_WEIGHT: 0.3
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
    CONFIDENCE_THRESHOLDS,

    // 特征工程
    FEATURE_CONSTANTS
};
