/**
 * GoldenFeatureExtractor - V3.0-PRO 纯函数版
 * ==========================================
 *
 * 从 FotMob L2 原始数据中提取三大类黄金特征：
 * 1. 身价特征 (market_value_*): 球队身价统计（单位：欧元）
 * 2. 伤病特征 (injury_*): 核心球员缺失统计
 * 3. 评分特征 (rating_*): 球员评分走势
 *
 * V3.0-PRO 纯函数化:
 * - 无外部依赖，无副作用
 * - 输入 FotMob JSON，输出特征对象
 * - 所有常量从配置中心导入
 * - 完全可测试、可缓存
 *
 * @module feature_engine/extractors/GoldenFeatureExtractor
 * @version V3.0.0-PRO
 * @since 2026-03-06
 */

'use strict';

// ============================================================================
// 从配置中心导入常量
// ============================================================================

const {
    MARKET_VALUE_MULTIPLIER,
    MIN_VALID_MARKET_VALUE,
    RATING_EXCELLENT_THRESHOLD,
    RATING_GOOD_THRESHOLD,
    RATING_AVERAGE_THRESHOLD,
    MARKET_VALUE_SOURCES
} = require('../../config/constants');

// ============================================================================
// 辅助函数（纯函数）
// ============================================================================

/**
 * 安全获取对象属性
 *
 * @param {Object} obj - 源对象
 * @param {string} path - 属性路径 (如 'a.b.c')
 * @param {*} defaultValue - 默认值
 * @returns {*}
 */
function safeGet(obj, path, defaultValue = undefined) {
    if (!obj || typeof obj !== 'object') {
        return defaultValue;
    }

    const keys = path.split('.');
    let current = obj;

    for (const key of keys) {
        if (current === null || current === undefined) {
            return defaultValue;
        }
        if (typeof current !== 'object') {
            return defaultValue;
        }
        current = current[key];
    }

    return current !== undefined && current !== null ? current : defaultValue;
}

/**
 * 安全获取数组属性
 *
 * @param {Object} obj - 源对象
 * @param {string} key - 属性名
 * @param {Array} defaultValue - 默认值
 * @returns {Array}
 */
function safeGetArray(obj, key, defaultValue = []) {
    if (!obj || typeof obj !== 'object') {
        return defaultValue;
    }
    const value = obj[key];
    return Array.isArray(value) ? value : defaultValue;
}

/**
 * 检查是否为有效对象
 *
 * @param {*} value - 待检查值
 * @returns {boolean}
 */
function isValidObject(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
}

/**
 * 检查是否为有效数字
 *
 * @param {*} value - 待检查值
 * @returns {boolean}
 */
function isValidNumber(value) {
    return typeof value === 'number' && !isNaN(value) && isFinite(value);
}

// ============================================================================
// 默认配置（可被外部覆盖）
// ============================================================================

const DEFAULT_CONFIG = {
    ratingThresholds: {
        excellent: RATING_EXCELLENT_THRESHOLD || 7.0,
        good: RATING_GOOD_THRESHOLD || 6.0,
        average: RATING_AVERAGE_THRESHOLD || 5.0
    },
    defaults: {
        marketValue: 0,
        rating: 0,
        age: -1
    },
    marketValueMultiplier: MARKET_VALUE_MULTIPLIER
};

// ============================================================================
// 核心提取函数
// ============================================================================

/**
 * 从原始 JSON 数据中提取黄金特征
 *
 * @param {Object} rawData - FotMob L2 原始数据 (raw_match_data.raw_data)
 * @param {Object} config - 配置选项
 * @returns {Object} 黄金特征字典
 */
function extractGoldenFeatures(rawData, config = DEFAULT_CONFIG) {
    // 参数校验
    if (!rawData || !isValidObject(rawData)) {
        return createEmptyFeatures('无效的原始数据');
    }

    const features = {};

    // 提取主队特征
    const homeFeatures = extractTeamFeatures(rawData, 'home', config);
    Object.assign(features, homeFeatures);

    // 提取客队特征
    const awayFeatures = extractTeamFeatures(rawData, 'away', config);
    Object.assign(features, awayFeatures);

    // 计算对比特征
    const comparisonFeatures = extractComparisonFeatures(features);
    Object.assign(features, comparisonFeatures);

    // 元数据
    features._extractedAt = new Date().toISOString();
    features._version = 'V3.0.0-PRO';
    features._source = 'FotMob';

    return features;
}

/**
 * 提取单队特征
 * @param {Object} rawData - 原始数据
 * @param {string} teamType - 球队类型 ('home' 或 'away')
 * @param {Object} config - 配置
 * @returns {Object}
 */
function extractTeamFeatures(rawData, teamType, config) {
    const prefix = teamType;
    const features = {};

    // 获取球队数据 - 路径: content.lineup.{homeTeam|awayTeam}
    const teamKey = `${teamType}Team`;
    const teamData = safeGet(rawData, `content.lineup.${teamKey}`, null);

    // ========== 身价特征 ==========
    const marketValueFeatures = extractMarketValueFeatures(rawData, teamData, prefix, config);
    Object.assign(features, marketValueFeatures);

    // ========== 伤病特征 ==========
    const injuryFeatures = extractInjuryFeatures(teamData, prefix, config);
    Object.assign(features, injuryFeatures);

    // ========== 评分特征 ==========
    const ratingFeatures = extractRatingFeatures(teamData, prefix, config);
    Object.assign(features, ratingFeatures);

    return features;
}

/**
 * 提取身价特征 - V201.13 多路径回退策略 + 单位修正
 *
 * 策略优先级:
 * 1. totalStarterMarketValue (球队总身价，最可靠)
 * 2. starters[].marketValue 求和 (首发阵容身价)
 * 3. subs[].marketValue 求和 (替补阵容身价)
 * 4. content.table.all[].marketValue 深度搜索
 * 5. content.players[].marketValue 球员列表搜索
 * 6. 0 (数据缺失)
 *
 * ⚠️ 重要: FotMob 返回的 marketValue 单位是"百万欧元"，需要乘以 1e6 转换为欧元
 *
 * @param {Object} rawData - 原始数据（用于多路径查找）
 * @param {Object} teamData - 球队数据
 * @param {string} prefix - 特征前缀
 * @param {Object} config - 配置
 * @returns {Object}
 */
function extractMarketValueFeatures(rawData, teamData, prefix, config) {
    const features = {};

    // 初始化默认值
    features[`${prefix}_market_value_total`] = 0;
    features[`${prefix}_market_value_avg`] = 0;
    features[`${prefix}_market_value_std`] = 0;
    features[`${prefix}_market_value_max`] = 0;
    features[`${prefix}_market_value_min`] = 0;
    features[`${prefix}_starters_count`] = 0;
    features[`${prefix}_market_value_source`] = 'none';
    features[`${prefix}_market_value_raw`] = 0;  // 保存原始值用于调试

    // 策略 1: 使用 totalStarterMarketValue 字段（最可靠）
    const totalMarketValue = safeGet(teamData, 'totalStarterMarketValue', null);
    if (isValidNumber(totalMarketValue) && totalMarketValue > 0) {
        // ✅ V201.13 修复: 单位转换 百万欧元 -> 欧元
        const convertedValue = totalMarketValue * MARKET_VALUE_MULTIPLIER;
        features[`${prefix}_market_value_total`] = Math.round(convertedValue);
        features[`${prefix}_market_value_raw`] = totalMarketValue;  // 保存原始值
        features[`${prefix}_market_value_source`] = 'totalStarterMarketValue';

        // 尝试获取首发人数
        const starters = safeGetArray(teamData, 'starters', []);
        if (starters.length > 0) {
            features[`${prefix}_starters_count`] = starters.length;
            features[`${prefix}_market_value_avg`] = Math.round(convertedValue / starters.length);
        }

        return features;
    }

    // 策略 2: 从 starters 数组提取身价
    const starters = safeGetArray(teamData, 'starters', []);
    if (starters.length > 0) {
        // ✅ V201.13 修复: 单位转换
        const marketValues = starters
            .map(player => {
                const rawValue = safeGet(player, 'marketValue', 0);
                return isValidNumber(rawValue) && rawValue > 0 ? rawValue * MARKET_VALUE_MULTIPLIER : 0;
            })
            .filter(value => value > 0);

        if (marketValues.length > 0) {
            const sum = marketValues.reduce((acc, val) => acc + val, 0);
            const avg = sum / marketValues.length;
            const variance = marketValues.reduce((acc, val) => acc + Math.pow(val - avg, 2), 0) / marketValues.length;
            const std = Math.sqrt(variance);

            features[`${prefix}_market_value_total`] = Math.round(sum);
            features[`${prefix}_market_value_avg`] = Math.round(avg);
            features[`${prefix}_market_value_std`] = Math.round(std);
            features[`${prefix}_market_value_max`] = Math.max(...marketValues);
            features[`${prefix}_market_value_min`] = Math.min(...marketValues);
            features[`${prefix}_starters_count`] = starters.length;
            features[`${prefix}_market_value_source`] = 'starters';

            return features;
        }
    }

    // 策略 3: 从 subs 数组提取身价（替补）
    const subs = safeGetArray(teamData, 'subs', []);
    if (subs.length > 0) {
        // ✅ V201.13 修复: 单位转换
        const marketValues = subs
            .map(player => {
                const rawValue = safeGet(player, 'marketValue', 0);
                return isValidNumber(rawValue) && rawValue > 0 ? rawValue * MARKET_VALUE_MULTIPLIER : 0;
            })
            .filter(value => value > 0);

        if (marketValues.length > 0) {
            const sum = marketValues.reduce((acc, val) => acc + val, 0);
            const avg = sum / marketValues.length;
            const variance = marketValues.reduce((acc, val) => acc + Math.pow(val - avg, 2), 0) / marketValues.length;
            const std = Math.sqrt(variance);

            features[`${prefix}_market_value_total`] = Math.round(sum);
            features[`${prefix}_market_value_avg`] = Math.round(avg);
            features[`${prefix}_market_value_std`] = Math.round(std);
            features[`${prefix}_market_value_max`] = Math.max(...marketValues);
            features[`${prefix}_market_value_min`] = Math.min(...marketValues);
            features[`${prefix}_starters_count`] = subs.length;
            features[`${prefix}_market_value_source`] = 'subs';

            return features;
        }
    }

    // 策略 4: 深度搜索 - content.table.all 或 content.players
    const deepMarketValue = deepSearchMarketValue(rawData, prefix);
    if (deepMarketValue > 0) {
        features[`${prefix}_market_value_total`] = deepMarketValue;
        features[`${prefix}_market_value_source`] = 'deep_search';
        return features;
    }

    // 无数据
    features[`${prefix}_market_value_source`] = 'not_found';
    return features;
}

/**
 * 深度搜索身价数据 - V201.13 扩展搜索路径
 *
 * 搜索路径:
 * 1. content.table.all[].marketValue (球员表格)
 * 2. content.players[].marketValue (球员列表)
 * 3. content.details.stats.* (统计数据)
 * 4. header.homeMarketValue/awayMarketValue (头部信息)
 *
 * @param {Object} rawData - 原始数据
 * @param {string} prefix - 前缀
 * @returns {number} 身价（欧元）
 */
function deepSearchMarketValue(rawData, prefix) {
    if (!rawData || !isValidObject(rawData)) {
        return 0;
    }

    // 路径 1: content.table.all (球员表格数据)
    const tableAll = safeGet(rawData, 'content.table.all', null);
    if (Array.isArray(tableAll) && tableAll.length > 0) {
        const teamKey = prefix === 'home' ? 'homeTeam' : 'awayTeam';

        // 过滤出该球队的球员
        const teamPlayers = tableAll.filter(player => {
            const teamName = safeGet(player, 'team', '');
            const isHome = safeGet(player, 'isHome', null);
            // 通过 isHome 标志或 team 名称匹配
            if (isHome !== null) {
                return (prefix === 'home' && isHome === true) || (prefix === 'away' && isHome === false);
            }
            return true;  // 无法区分时，使用全部
        });

        if (teamPlayers.length > 0) {
            const marketValues = teamPlayers
                .map(player => {
                    const rawValue = safeGet(player, 'marketValue', 0);
                    // ✅ V201.13 修复: 单位转换
                    return isValidNumber(rawValue) && rawValue > 0 ? rawValue * MARKET_VALUE_MULTIPLIER : 0;
                })
                .filter(value => value > 0);

            if (marketValues.length > 0) {
                const sum = marketValues.reduce((acc, val) => acc + val, 0);
                return Math.round(sum);
            }
        }
    }

    // 路径 2: content.players (球员列表)
    const playersList = safeGet(rawData, 'content.players', null);
    if (Array.isArray(playersList) && playersList.length > 0) {
        // 尝试按球队过滤
        const teamPlayers = playersList.filter(player => {
            const teamRole = safeGet(player, 'teamRole', '');
            return teamRole.toLowerCase().includes(prefix);
        });

        const targetPlayers = teamPlayers.length > 0 ? teamPlayers : playersList;

        const marketValues = targetPlayers
            .map(player => {
                const rawValue = safeGet(player, 'marketValue', 0);
                // ✅ V201.13 修复: 单位转换
                return isValidNumber(rawValue) && rawValue > 0 ? rawValue * MARKET_VALUE_MULTIPLIER : 0;
            })
            .filter(value => value > 0);

        if (marketValues.length > 0) {
            const sum = marketValues.reduce((acc, val) => acc + val, 0);
            return Math.round(sum);
        }
    }

    // 路径 3: content.details.stats
    const details = safeGet(rawData, 'content.details', null);
    if (details && isValidObject(details)) {
        const stats = safeGet(details, 'stats', null);
        if (stats && isValidObject(stats)) {
            for (const key of Object.keys(stats)) {
                const lowerKey = key.toLowerCase();
                if (lowerKey.includes('market') || lowerKey.includes('value')) {
                    const value = stats[key];
                    if (isValidNumber(value) && value > 0) {
                        // ✅ V201.13 修复: 假设也是百万欧元
                        return Math.round(value * MARKET_VALUE_MULTIPLIER);
                    }
                }
            }
        }
    }

    // 路径 4: header 信息
    const header = safeGet(rawData, 'header', null);
    if (header && isValidObject(header)) {
        const homeValue = safeGet(header, 'homeMarketValue', 0);
        const awayValue = safeGet(header, 'awayMarketValue', 0);
        if (prefix === 'home' && isValidNumber(homeValue) && homeValue > 0) {
            return Math.round(homeValue * MARKET_VALUE_MULTIPLIER);
        }
        if (prefix === 'away' && isValidNumber(awayValue) && awayValue > 0) {
            return Math.round(awayValue * MARKET_VALUE_MULTIPLIER);
        }
    }

    // 路径 5: 直接在顶层搜索 marketValue 相关字段
    const rawContent = safeGet(rawData, 'content', null);
    if (rawContent && isValidObject(rawContent)) {
        // 递归搜索所有包含 marketValue 的字段
        const foundValues = [];
        const searchObject = (obj, depth = 0) => {
            if (depth > 5 || !obj || typeof obj !== 'object') return;
            for (const key of Object.keys(obj)) {
                const lowerKey = key.toLowerCase();
                if (lowerKey === 'marketvalue' || lowerKey === 'market_value') {
                    const value = obj[key];
                    if (isValidNumber(value) && value > 0) {
                        foundValues.push(value * MARKET_VALUE_MULTIPLIER);
                    }
                } else if (typeof obj[key] === 'object') {
                    searchObject(obj[key], depth + 1);
                }
            }
        };
        searchObject(rawContent);

        if (foundValues.length > 0) {
            // 取中位数，避免异常值
            foundValues.sort((a, b) => a - b);
            const midIndex = Math.floor(foundValues.length / 2);
            return Math.round(foundValues[midIndex]);
        }
    }

    return 0;
}

/**
 * 提取伤病特征
 * @param {Object} teamData - 球队数据
 * @param {string} prefix - 特征前缀
 * @param {Object} config - 配置
 * @returns {Object}
 */
function extractInjuryFeatures(teamData, prefix, config) {
    const features = {};

    if (!teamData || !isValidObject(teamData)) {
        features[`${prefix}_injury_count`] = 0;
        return features;
    }

    const unavailable = safeGetArray(teamData, 'unavailable', []);

    // 基础伤病统计
    features[`${prefix}_injury_count`] = unavailable.length;

    // 伤病类型细分
    const injuryTypes = {};
    for (const player of unavailable) {
        const unavailability = safeGet(player, 'unavailability', {});
        const type = safeGet(unavailability, 'type', 'unknown');
        injuryTypes[type] = (injuryTypes[type] || 0) + 1;
    }

    // 将类型统计平铺为特征
    for (const [type, count] of Object.entries(injuryTypes)) {
        const safeKey = type.replace(/[^a-zA-Z0-9]/g, '_').toLowerCase();
        features[`${prefix}_injury_${safeKey}_count`] = count;
    }

    // 预计回归统计
    const doubtfulCount = unavailable.filter(player => {
        const expectedReturn = safeGet(player, 'unavailability.expectedReturn', '');
        return typeof expectedReturn === 'string' && expectedReturn.toLowerCase().includes('doubtful');
    }).length;
    features[`${prefix}_injury_doubtful_count`] = doubtfulCount;

    return features;
}

/**
 * 提取评分特征
 * @param {Object} teamData - 球队数据
 * @param {string} prefix - 特征前缀
 * @param {Object} config - 配置
 * @returns {Object}
 */
function extractRatingFeatures(teamData, prefix, config) {
    const features = {};
    const thresholds = config.ratingThresholds || DEFAULT_CONFIG.ratingThresholds;

    // 初始化默认值
    features[`${prefix}_rating_avg`] = 0;
    features[`${prefix}_rating_std`] = 0;
    features[`${prefix}_rating_max`] = 0;
    features[`${prefix}_rating_min`] = 0;
    features[`${prefix}_rating_excellent_count`] = 0;
    features[`${prefix}_rating_good_count`] = 0;
    features[`${prefix}_rating_average_count`] = 0;
    features[`${prefix}_rating_poor_count`] = 0;
    features[`${prefix}_rating_available_count`] = 0;
    features[`${prefix}_age_avg`] = -1;
    features[`${prefix}_u23_count`] = 0;
    features[`${prefix}_veteran_count`] = 0;

    if (!teamData || !isValidObject(teamData)) {
        return features;
    }

    const starters = safeGetArray(teamData, 'starters', []);

    if (starters.length === 0) {
        return features;
    }

    // 提取评分数组
    const ratings = starters
        .map(player => safeGet(player, 'performance.rating', null))
        .filter(rating => isValidNumber(rating) && rating > 0);

    if (ratings.length > 0) {
        const sum = ratings.reduce((acc, val) => acc + val, 0);
        const avg = sum / ratings.length;
        const variance = ratings.reduce((acc, val) => acc + Math.pow(val - avg, 2), 0) / ratings.length;
        const std = Math.sqrt(variance);

        features[`${prefix}_rating_avg`] = Math.round(avg * 100) / 100;
        features[`${prefix}_rating_std`] = Math.round(std * 100) / 100;
        features[`${prefix}_rating_max`] = Math.max(...ratings);
        features[`${prefix}_rating_min`] = Math.min(...ratings);

        // 评分分档统计
        features[`${prefix}_rating_excellent_count`] = ratings.filter(r => r >= thresholds.excellent).length;
        features[`${prefix}_rating_good_count`] = ratings.filter(r => r >= thresholds.good && r < thresholds.excellent).length;
        features[`${prefix}_rating_average_count`] = ratings.filter(r => r >= thresholds.average && r < thresholds.good).length;
        features[`${prefix}_rating_poor_count`] = ratings.filter(r => r < thresholds.average).length;
    }

    features[`${prefix}_rating_available_count`] = ratings.length;

    // 年龄结构
    const ages = starters
        .map(player => safeGet(player, 'age', null))
        .filter(age => isValidNumber(age) && age > 0);

    if (ages.length > 0) {
        const avgAge = ages.reduce((acc, val) => acc + val, 0) / ages.length;
        features[`${prefix}_age_avg`] = Math.round(avgAge * 10) / 10;
        features[`${prefix}_u23_count`] = ages.filter(age => age < 23).length;
        features[`${prefix}_veteran_count`] = ages.filter(age => age >= 30).length;
    }

    return features;
}

/**
 * 提取对比特征
 * @param {Object} features - 已提取的特征
 * @returns {Object}
 */
function extractComparisonFeatures(features) {
    const comparison = {};

    // 身价对比
    const homeValue = features.home_market_value_total || 0;
    const awayValue = features.away_market_value_total || 0;
    comparison.market_value_gap = homeValue - awayValue;
    comparison.market_value_ratio = awayValue > 0 ? Math.round((homeValue / awayValue) * 1000) / 1000 : (homeValue > 0 ? 999 : 1);

    // 伤病对比
    const homeInjury = features.home_injury_count || 0;
    const awayInjury = features.away_injury_count || 0;
    comparison.injury_count_gap = homeInjury - awayInjury;

    // 评分对比
    const homeRating = features.home_rating_avg || 0;
    const awayRating = features.away_rating_avg || 0;
    comparison.rating_gap = Math.round((homeRating - awayRating) * 100) / 100;

    // 年龄对比
    const homeAge = features.home_age_avg || 0;
    const awayAge = features.away_age_avg || 0;
    comparison.age_gap = (homeAge > 0 && awayAge > 0) ? Math.round((homeAge - awayAge) * 10) / 10 : 0;

    // 数据来源标记
    comparison.home_value_source = features.home_market_value_source || 'none';
    comparison.away_value_source = features.away_market_value_source || 'none';

    return comparison;
}

/**
 * 创建空特征对象
 * @param {string} reason - 原因说明
 * @returns {Object}
 */
function createEmptyFeatures(reason = 'No valid raw data provided') {
    return {
        home_market_value_total: 0,
        home_market_value_avg: 0,
        home_market_value_std: 0,
        home_market_value_max: 0,
        home_market_value_min: 0,
        home_starters_count: 0,
        home_injury_count: 0,
        home_rating_avg: 0,
        home_rating_std: 0,
        home_age_avg: -1,
        home_market_value_source: 'none',
        home_market_value_raw: 0,
        away_market_value_total: 0,
        away_market_value_avg: 0,
        away_market_value_std: 0,
        away_market_value_max: 0,
        away_market_value_min: 0,
        away_starters_count: 0,
        away_injury_count: 0,
        away_rating_avg: 0,
        away_rating_std: 0,
        away_age_avg: -1,
        away_market_value_source: 'none',
        away_market_value_raw: 0,
        market_value_gap: 0,
        market_value_ratio: 1,
        injury_count_gap: 0,
        rating_gap: 0,
        age_gap: 0,
        _extractedAt: new Date().toISOString(),
        _version: 'V3.0.0-PRO',
        _source: 'FotMob',
        _error: reason
    };
}

// ============================================================================
// 导出
// ============================================================================
module.exports = {
    extractGoldenFeatures,
    extractTeamFeatures,
    extractMarketValueFeatures,
    extractInjuryFeatures,
    extractRatingFeatures,
    extractComparisonFeatures,
    createEmptyFeatures,
    DEFAULT_CONFIG
};
