/**
 * 业务常量配置中心 - V3.0-PRO
 * ==========================================
 *
 * 集中管理所有业务常量，确保：
 * 1. 单一真实来源 (Single Source of Truth)
 * 2. 类型安全 (通过 JSDoc)
 * 3. 可审计 (所有魔术数字都有注释)
 *
 * @module config/constants
 * @version V3.0.0-PRO
 * @since 2026-03-06
 */

'use strict';

// ============================================================================
// 身价相关常量 (Market Value Constants)
// ============================================================================

/**
 * FotMob API 返回的身价单位是"百万欧元" (M_EUR)
 * 此常量用于将百万欧元转换为欧元
 *
 * @constant {number}
 * @example
 * // FotMob 返回 1.5 (百万欧元)
 * const valueInEur = 1.5 * MARKET_VALUE_MULTIPLIER; // 1,500,000 欧元
 */
const MARKET_VALUE_MULTIPLIER = 1e6;

/**
 * 身价数据的最小有效值（欧元）
 * 低于此值视为无效数据
 *
 * @constant {number}
 */
const MIN_VALID_MARKET_VALUE = 100000; // 10 万欧元

/**
 * 身价显示阈值 - 亿级（欧元）
 * 超过此值时使用"亿"作为显示单位
 *
 * @constant {number}
 */
const MARKET_VALUE_BILLION_THRESHOLD = 1e9;

/**
 * 身价显示阈值 - 千万级（欧元）
 * 超过此值时使用"千万"作为显示单位
 *
 * @constant {number}
 */
const MARKET_VALUE_TEN_MILLION_THRESHOLD = 1e7;

/**
 * 身价显示阈值 - 百万级（欧元）
 * 超过此值时使用"万"作为显示单位
 *
 * @constant {number}
 */
const MARKET_VALUE_MILLION_THRESHOLD = 1e6;

// ============================================================================
// Elo 评分常量 (Elo Rating Constants)
// ============================================================================

/**
 * 默认 Elo 评分
 * 新球队或无历史数据时的初始值
 *
 * @constant {number}
 */
const DEFAULT_ELO_RATING = 1500;

/**
 * 主场优势 Elo 加成
 * 主队在计算期望胜率时获得的额外评分
 *
 * @constant {number}
 */
const HOME_ADVANTAGE_ELO = 50;

/**
 * Elo K 因子
 * 控制每场比赛对评分的影响程度
 *
 * @constant {number}
 */
const ELO_K_FACTOR = 32;

/**
 * Elo 期望公式的分母系数
 * 标准 Elo 公式: E = 1 / (1 + 10^((Rb-Ra)/400))
 *
 * @constant {number}
 */
const ELO_SCALE_FACTOR = 400;

// ============================================================================
// EV (期望值) 常量 (Expected Value Constants)
// ============================================================================

/**
 * 高价值投注的 EV 阈值
 * EV 超过此值时推荐投注
 *
 * @constant {number}
 */
const EV_HIGH_VALUE_THRESHOLD = 0.05; // 5%

/**
 * 强烈推荐投注的 EV 阈值
 *
 * @constant {number}
 */
const EV_STRONG_RECOMMEND_THRESHOLD = 0.10; // 10%

/**
 * 边缘投注的 EV 阈值
 * EV 在此范围内时为边缘投注
 *
 * @constant {number}
 */
const EV_EDGE_THRESHOLD = 0.00; // 0%

// ============================================================================
// 身价权重常量 (Market Value Weight Constants)
// ============================================================================

/**
 * 身价差距对概率的影响权重
 * 每 1 亿欧元差距 = 此百分比的概率调整
 *
 * @constant {number}
 */
const MARKET_VALUE_WEIGHT = 0.02; // 2%

/**
 * 身价差距的基准单位（欧元）
 * 用于计算身价效应
 *
 * @constant {number}
 */
const MARKET_VALUE_SCALE = 1e8; // 1 亿欧元

// ============================================================================
// 伤病权重常量 (Injury Weight Constants)
// ============================================================================

/**
 * 伤病差距对概率的影响权重
 * 每 1 人伤病差距 = 此百分比的概率调整
 *
 * @constant {number}
 */
const INJURY_WEIGHT = 0.005; // 0.5%

// ============================================================================
// 评分阈值常量 (Rating Threshold Constants)
// ============================================================================

/**
 * 优秀评分阈值
 * 球员评分 >= 此值视为优秀
 *
 * @constant {number}
 */
const RATING_EXCELLENT_THRESHOLD = 7.0;

/**
 * 良好评分阈值
 * 球员评分 >= 此值且 < 优秀阈值视为良好
 *
 * @constant {number}
 */
const RATING_GOOD_THRESHOLD = 6.0;

/**
 * 平均评分阈值
 * 球员评分 >= 此值且 < 良好阈值视为平均
 *
 * @constant {number}
 */
const RATING_AVERAGE_THRESHOLD = 5.0;

// ============================================================================
// 重试与超时常量 (Retry & Timeout Constants)
// ============================================================================

/**
 * 数据库操作最大重试次数
 *
 * @constant {number}
 */
const DB_MAX_RETRIES = 3;

/**
 * 数据库操作初始重试延迟（毫秒）
 *
 * @constant {number}
 */
const DB_RETRY_DELAY_MS = 1000;

/**
 * 数据库操作重试延迟乘数（指数退避）
 *
 * @constant {number}
 */
const DB_RETRY_BACKOFF_MULTIPLIER = 2;

/**
 * 数据库连接超时（毫秒）
 *
 * @constant {number}
 */
const DB_CONNECTION_TIMEOUT_MS = 30000;

// ============================================================================
// 日志级别常量 (Log Level Constants)
// ============================================================================

/**
 * 日志级别枚举
 *
 * @readonly
 * @enum {string}
 */
const LOG_LEVELS = Object.freeze({
    ERROR: 'error',
    WARN: 'warn',
    INFO: 'info',
    DEBUG: 'debug',
    TRACE: 'trace'
});

// ============================================================================
// 数据源常量 (Data Source Constants)
// ============================================================================

/**
 * 身价数据来源类型
 *
 * @readonly
 * @enum {string}
 */
const MARKET_VALUE_SOURCES = Object.freeze({
    TOTAL_STARTER: 'totalStarterMarketValue',
    STARTERS: 'starters',
    SUBS: 'subs',
    DEEP_SEARCH: 'deep_search',
    NOT_FOUND: 'not_found'
});

// ============================================================================
// 导出
// ============================================================================

module.exports = {
    // 身价常量
    MARKET_VALUE_MULTIPLIER,
    MIN_VALID_MARKET_VALUE,
    MARKET_VALUE_BILLION_THRESHOLD,
    MARKET_VALUE_TEN_MILLION_THRESHOLD,
    MARKET_VALUE_MILLION_THRESHOLD,

    // Elo 常量
    DEFAULT_ELO_RATING,
    HOME_ADVANTAGE_ELO,
    ELO_K_FACTOR,
    ELO_SCALE_FACTOR,

    // EV 常量
    EV_HIGH_VALUE_THRESHOLD,
    EV_STRONG_RECOMMEND_THRESHOLD,
    EV_EDGE_THRESHOLD,

    // 权重常量
    MARKET_VALUE_WEIGHT,
    MARKET_VALUE_SCALE,
    INJURY_WEIGHT,

    // 评分阈值
    RATING_EXCELLENT_THRESHOLD,
    RATING_GOOD_THRESHOLD,
    RATING_AVERAGE_THRESHOLD,

    // 重试与超时
    DB_MAX_RETRIES,
    DB_RETRY_DELAY_MS,
    DB_RETRY_BACKOFF_MULTIPLIER,
    DB_CONNECTION_TIMEOUT_MS,

    // 枚举
    LOG_LEVELS,
    MARKET_VALUE_SOURCES
};
