/**
 * GoldenFeatureExtractor - 黄金特征提取器
 * ==========================================
 *
 * 从 FotMob L2 原始数据中提取三大类黄金特征：
 * 1. 身价特征 (market_value_*): 球队身价统计
 * 2. 伤病特征 (injury_*): 核心球员缺失统计
 * 3. 评分特征 (rating_*): 球员评分走势
 *
 * @module feature_engine/extractors/GoldenFeatureExtractor
 * @version V176.0.0
 */

'use strict';

const { safeGet, hasPath, is } = require('../../core/utils/SafeAccess');

/**
 * 安全获取数组属性（辅助函数）
 * @param {Object} obj - 源对象
 * @param {string} key - 属性名
 * @param {Array} defaultValue - 默认值
 * @returns {Array}
 */
function safeGetArray(obj, key, defaultValue = []) {
    const value = obj?.[key];
    return Array.isArray(value) ? value : defaultValue;
}

/**
 * 黄金特征提取器配置
 */
const DEFAULT_CONFIG = {
    // 评分分档阈值
    ratingThresholds: {
        excellent: 7.0,
        good: 6.0,
        average: 5.0
    },
    // 默认值
    defaults: {
        marketValue: 0,
        rating: 0,
        age: -1
    }
};

/**
 * 从原始 JSON 数据中提取黄金特征
 *
 * @param {Object} rawData - FotMob L2 原始数据 (raw_match_data.raw_data)
 * @param {Object} config - 配置选项
 * @returns {Object} 黄金特征字典
 */
function extractGoldenFeatures(rawData, config = DEFAULT_CONFIG) {
    if (!rawData || !is.object(rawData)) {
        return createEmptyFeatures();
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
    features._version = 'V176.0.0';

    return features;
}

/**
 * 提取单队特征
 */
function extractTeamFeatures(rawData, teamType, config) {
    const prefix = teamType;
    const features = {};

    // 路径: content.lineup.{homeTeam|awayTeam}
    const teamKey = `${teamType}Team`;
    const teamData = safeGet(rawData, `content.lineup.${teamKey}`, {});

    // ========== 身价特征 ==========
    const marketValueFeatures = extractMarketValueFeatures(teamData, prefix, config);
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
 * 提取身价特征
 */
function extractMarketValueFeatures(teamData, prefix, config) {
    const features = {};
    const starters = safeGetArray(teamData, 'starters', []);

    if (starters.length === 0) {
        features[`${prefix}_market_value_total`] = 0;
        features[`${prefix}_market_value_avg`] = 0;
        features[`${prefix}_market_value_std`] = 0;
        features[`${prefix}_market_value_max`] = 0;
        features[`${prefix}_market_value_min`] = 0;
        features[`${prefix}_starters_count`] = 0;
        return features;
    }

    // 提取身价数组
    const marketValues = starters
        .map(p => safeGet(p, 'marketValue', 0))
        .filter(v => v > 0);

    if (marketValues.length > 0) {
        const sum = marketValues.reduce((a, b) => a + b, 0);
        const avg = sum / marketValues.length;
        const variance = marketValues.reduce((acc, v) => acc + Math.pow(v - avg, 2), 0) / marketValues.length;
        const std = Math.sqrt(variance);

        features[`${prefix}_market_value_total`] = Math.round(sum);
        features[`${prefix}_market_value_avg`] = Math.round(avg);
        features[`${prefix}_market_value_std`] = Math.round(std);
        features[`${prefix}_market_value_max`] = Math.max(...marketValues);
        features[`${prefix}_market_value_min`] = Math.min(...marketValues);
    } else {
        features[`${prefix}_market_value_total`] = 0;
        features[`${prefix}_market_value_avg`] = 0;
        features[`${prefix}_market_value_std`] = 0;
        features[`${prefix}_market_value_max`] = 0;
        features[`${prefix}_market_value_min`] = 0;
    }

    features[`${prefix}_starters_count`] = starters.length;

    return features;
}

/**
 * 提取伤病特征
 */
function extractInjuryFeatures(teamData, prefix, config) {
    const features = {};
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
    const doubtfulCount = unavailable.filter(p => {
        const expectedReturn = safeGet(p, 'unavailability.expectedReturn', '');
        return expectedReturn.toLowerCase().includes('doubtful');
    }).length;
    features[`${prefix}_injury_doubtful_count`] = doubtfulCount;

    return features;
}

/**
 * 提取评分特征
 */
function extractRatingFeatures(teamData, prefix, config) {
    const features = {};
    const starters = safeGetArray(teamData, 'starters', []);
    const thresholds = config.ratingThresholds;

    if (starters.length === 0) {
        features[`${prefix}_rating_avg`] = 0;
        features[`${prefix}_rating_std`] = 0;
        features[`${prefix}_rating_max`] = 0;
        features[`${prefix}_rating_min`] = 0;
        features[`${prefix}_rating_excellent_count`] = 0;
        features[`${prefix}_rating_good_count`] = 0;
        features[`${prefix}_rating_average_count`] = 0;
        features[`${prefix}_rating_poor_count`] = 0;
        features[`${prefix}_rating_available_count`] = 0;
        return features;
    }

    // 提取评分数组
    const ratings = starters
        .map(p => safeGet(p, 'performance.rating', null))
        .filter(r => r !== null && r > 0);

    if (ratings.length > 0) {
        const sum = ratings.reduce((a, b) => a + b, 0);
        const avg = sum / ratings.length;
        const variance = ratings.reduce((acc, v) => acc + Math.pow(v - avg, 2), 0) / ratings.length;
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
    } else {
        features[`${prefix}_rating_avg`] = 0;
        features[`${prefix}_rating_std`] = 0;
        features[`${prefix}_rating_max`] = 0;
        features[`${prefix}_rating_min`] = 0;
        features[`${prefix}_rating_excellent_count`] = 0;
        features[`${prefix}_rating_good_count`] = 0;
        features[`${prefix}_rating_average_count`] = 0;
        features[`${prefix}_rating_poor_count`] = 0;
    }

    features[`${prefix}_rating_available_count`] = ratings.length;

    // 年龄结构
    const ages = starters
        .map(p => safeGet(p, 'age', null))
        .filter(a => a !== null && a > 0);

    if (ages.length > 0) {
        const avgAge = ages.reduce((a, b) => a + b, 0) / ages.length;
        features[`${prefix}_age_avg`] = Math.round(avgAge * 10) / 10;
        features[`${prefix}_u23_count`] = ages.filter(a => a < 23).length;
        features[`${prefix}_veteran_count`] = ages.filter(a => a >= 30).length;
    } else {
        features[`${prefix}_age_avg`] = -1;
        features[`${prefix}_u23_count`] = 0;
        features[`${prefix}_veteran_count`] = 0;
    }

    return features;
}

/**
 * 提取对比特征
 */
function extractComparisonFeatures(features) {
    const comparison = {};

    // 身价对比
    const homeValue = features.home_market_value_total || 0;
    const awayValue = features.away_market_value_total || 0;
    comparison.market_value_gap = homeValue - awayValue;
    comparison.market_value_ratio = awayValue > 0 ? homeValue / awayValue : 1;

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
    comparison.age_gap = homeAge > 0 && awayAge > 0 ? Math.round((homeAge - awayAge) * 10) / 10 : 0;

    return comparison;
}

/**
 * 创建空特征对象
 */
function createEmptyFeatures() {
    return {
        _extractedAt: new Date().toISOString(),
        _version: 'V176.0.0',
        _error: 'No valid raw data provided'
    };
}

module.exports = {
    extractGoldenFeatures,
    extractTeamFeatures,
    extractMarketValueFeatures,
    extractInjuryFeatures,
    extractRatingFeatures,
    extractComparisonFeatures,
    DEFAULT_CONFIG
};
