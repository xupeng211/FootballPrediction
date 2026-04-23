/**
 * GoldenExtractor - V5.2 黄金特征提取器
 * =======================================
 *
 * 从 FotMob L2 原始数据中提取三大类黄金特征：
 * 1. 身价特征 (market_value_*): 球队身价统计（单位：欧元）
 * 2. 伤病特征 (injury_*): 核心球员缺失统计
 * 3. 评分特征 (rating_*): 球员评分走势
 *
 * V5.2 模块化:
 * - 继承 BaseExtractor，符合行业标准
 * - 完全可测试、可监控
 * @module feature_engine/smelter/components/GoldenExtractor
 * @version V5.2.0-HOME-FORTRESS
 * @since 2026-03-14
 */

'use strict';

const { BaseExtractor } = require('./BaseExtractor');

// ============================================================================
// 配置常量
// ============================================================================

const DEFAULT_CONFIG = {
    // 身价相关
    marketValueMultiplier: 1e6,  // 百万欧元转欧元
    minValidMarketValue: 0,

    // 评分阈值
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
    },

    // 严格模式
    strictMode: false
};

// 特征字段名清单
const FEATURE_NAMES = [
    // 主队身价
    'home_market_value_total',
    'home_market_value_avg',
    'home_market_value_std',
    'home_market_value_max',
    'home_market_value_min',
    'home_market_value_source',
    'home_market_value_raw',
    'home_starters_count',

    // 客队身价
    'away_market_value_total',
    'away_market_value_avg',
    'away_market_value_std',
    'away_market_value_max',
    'away_market_value_min',
    'away_market_value_source',
    'away_market_value_raw',
    'away_starters_count',

    // 主队伤病
    'home_injury_count',
    'home_injury_doubtful_count',

    // 客队伤病
    'away_injury_count',
    'away_injury_doubtful_count',

    // 主队评分
    'home_rating_avg',
    'home_rating_std',
    'home_rating_max',
    'home_rating_min',
    'home_rating_excellent_count',
    'home_rating_good_count',
    'home_rating_average_count',
    'home_rating_poor_count',
    'home_rating_available_count',
    'home_age_avg',
    'home_u23_count',
    'home_veteran_count',

    // 客队评分
    'away_rating_avg',
    'away_rating_std',
    'away_rating_max',
    'away_rating_min',
    'away_rating_excellent_count',
    'away_rating_good_count',
    'away_rating_average_count',
    'away_rating_poor_count',
    'away_rating_available_count',
    'away_age_avg',
    'away_u23_count',
    'away_veteran_count',

    // 对比特征
    'market_value_gap',
    'market_value_ratio',
    'injury_count_gap',
    'rating_gap',
    'age_gap'
];

// ============================================================================
// GoldenExtractor 类
// ============================================================================

/**
 * 黄金特征提取器
 */
class GoldenExtractor extends BaseExtractor {
    /**
     * @param {object} config - 配置选项
     */
    constructor(config = {}) {
        super({
            name: 'GoldenExtractor',
            version: 'V5.2.0-HOME-FORTRESS',
            requiredFields: ['content.lineup'],
            config: { ...DEFAULT_CONFIG, ...config }
        });

        this.cfg = this.config; // 简写
    }

    /**
     * 获取默认配置
     * @returns {object}
     */
    getDefaultConfig() {
        return DEFAULT_CONFIG;
    }

    /**
     * 获取特征字段名清单
     * @returns {Array<string>}
     */
    getFeatureNames() {
        return FEATURE_NAMES;
    }

    /**
     * 执行特征提取
     * @param {object} rawData - FotMob L2 原始数据
     * @param {object} context - 上下文信息 { teamType?, config? }
     * @returns {object} 黄金特征字典
     */
    extract(rawData, context = {}) {
        // 参数校验
        if (!rawData || !this.isValidObject(rawData)) {
            return this.createEmptyFeatures('无效的原始数据');
        }

        const features = {};
        const teamTypes = context.teamType ? [context.teamType] : ['home', 'away'];

        // 提取各队特征
        for (const teamType of teamTypes) {
            const teamFeatures = this._extractTeamFeatures(rawData, teamType);
            Object.assign(features, teamFeatures);
        }

        // 计算对比特征（需要两队数据）
        if (teamTypes.length === 2) {
            const comparisonFeatures = this._extractComparisonFeatures(features);
            Object.assign(features, comparisonFeatures);
        }

        return features;
    }

    // ========================================================================
    // 私有提取方法
    // ========================================================================

    /**
     * 提取单队特征
     * @private
     * @param {object} rawData - 原始数据
     * @param {string} teamType - 球队类型 ('home' 或 'away')
     * @returns {object}
     */
    _extractTeamFeatures(rawData, teamType) {
        const prefix = teamType;
        const features = {};

        // 获取球队数据
        const teamKey = `${teamType}Team`;
        const teamData = this.safeGet(rawData, `content.lineup.${teamKey}`, null);

        // ========== 身价特征 ==========
        const marketValueFeatures = this._extractMarketValueFeatures(rawData, teamData, prefix);
        Object.assign(features, marketValueFeatures);

        // ========== 伤病特征 ==========
        const injuryFeatures = this._extractInjuryFeatures(teamData, prefix);
        Object.assign(features, injuryFeatures);

        // ========== 评分特征 ==========
        const ratingFeatures = this._extractRatingFeatures(teamData, prefix);
        Object.assign(features, ratingFeatures);

        return features;
    }

    _extractStarterCount(teamData) {
        return this._safeGetArray(teamData, 'starters').length;
    }

    /**
     * 提取身价特征
     * @private
     * @param {object} rawData - 原始数据
     * @param {object} teamData - 球队数据
     * @param {string} prefix - 特征前缀
     * @returns {object}
     */
    _extractMarketValueFeatures(rawData, teamData, prefix) {
        const features = {};
        const starters = this._safeGetArray(teamData, 'starters');
        const startersCount = this._extractStarterCount(teamData);

        // 初始化默认值
        features[`${prefix}_market_value_total`] = 0;
        features[`${prefix}_market_value_avg`] = 0;
        features[`${prefix}_market_value_std`] = 0;
        features[`${prefix}_market_value_max`] = 0;
        features[`${prefix}_market_value_min`] = 0;
        features[`${prefix}_starters_count`] = startersCount;
        features[`${prefix}_market_value_source`] = 'none';
        features[`${prefix}_market_value_raw`] = 0;

        // 策略 1: 使用 totalStarterMarketValue 字段
        const totalMarketValue = this.safeGet(teamData, 'totalStarterMarketValue', null);
        if (this.isValidNumber(totalMarketValue) && totalMarketValue > 0) {
            const convertedValue = totalMarketValue * this.cfg.marketValueMultiplier;
            features[`${prefix}_market_value_total`] = Math.round(convertedValue);
            features[`${prefix}_market_value_raw`] = totalMarketValue;
            features[`${prefix}_market_value_source`] = 'totalStarterMarketValue';

            if (startersCount > 0) {
                features[`${prefix}_market_value_avg`] = Math.round(convertedValue / starters.length);
            }

            return features;
        }

        // 策略 2: 从 starters 数组提取
        if (starters.length > 0) {
            const marketValues = starters
                .map(player => {
                    const rawValue = this.safeGet(player, 'marketValue', 0);
                    return this.isValidNumber(rawValue) && rawValue > 0
                        ? rawValue * this.cfg.marketValueMultiplier
                        : 0;
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
                features[`${prefix}_market_value_source`] = 'starters';

                return features;
            }
        }

        // 策略 3: 深度搜索
        const deepValue = this._deepSearchMarketValue(rawData, prefix);
        if (deepValue > 0) {
            features[`${prefix}_market_value_total`] = deepValue;
            features[`${prefix}_market_value_source`] = 'deep_search';
        }

        return features;
    }

    /**
     * 提取伤病特征
     * @private
     * @param {object} teamData - 球队数据
     * @param {string} prefix - 特征前缀
     * @returns {object}
     */
    _extractInjuryFeatures(teamData, prefix) {
        const features = {};

        if (!teamData || !this.isValidObject(teamData)) {
            features[`${prefix}_injury_count`] = 0;
            features[`${prefix}_injury_doubtful_count`] = 0;
            return features;
        }

        const unavailable = this._safeGetArray(teamData, 'unavailable');

        features[`${prefix}_injury_count`] = unavailable.length;

        // 预计回归统计
        const doubtfulCount = unavailable.filter(player => {
            const expectedReturn = this.safeGet(player, 'unavailability.expectedReturn', '');
            return typeof expectedReturn === 'string' &&
                expectedReturn.toLowerCase().includes('doubtful');
        }).length;
        features[`${prefix}_injury_doubtful_count`] = doubtfulCount;

        return features;
    }

    /**
     * 提取评分特征
     * @private
     * @param {object} teamData - 球队数据
     * @param {string} prefix - 特征前缀
     * @returns {object}
     */
    _extractRatingFeatures(teamData, prefix) {
        const features = {};
        const thresholds = this.cfg.ratingThresholds;

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

        if (!teamData || !this.isValidObject(teamData)) {
            return features;
        }

        const starters = this._safeGetArray(teamData, 'starters');
        if (starters.length === 0) {
            return features;
        }

        // 提取评分数组
        const ratings = starters
            .map(player => this.safeGet(player, 'performance.rating', null))
            .filter(rating => this.isValidNumber(rating) && rating > 0);

        if (ratings.length > 0) {
            const sum = ratings.reduce((acc, val) => acc + val, 0);
            const avg = sum / ratings.length;
            const variance = ratings.reduce((acc, val) => acc + Math.pow(val - avg, 2), 0) / ratings.length;
            const std = Math.sqrt(variance);

            features[`${prefix}_rating_avg`] = Math.round(avg * 100) / 100;
            features[`${prefix}_rating_std`] = Math.round(std * 100) / 100;
            features[`${prefix}_rating_max`] = Math.max(...ratings);
            features[`${prefix}_rating_min`] = Math.min(...ratings);

            features[`${prefix}_rating_excellent_count`] = ratings.filter(r => r >= thresholds.excellent).length;
            features[`${prefix}_rating_good_count`] = ratings.filter(r => r >= thresholds.good && r < thresholds.excellent).length;
            features[`${prefix}_rating_average_count`] = ratings.filter(r => r >= thresholds.average && r < thresholds.good).length;
            features[`${prefix}_rating_poor_count`] = ratings.filter(r => r < thresholds.average).length;
        }

        features[`${prefix}_rating_available_count`] = ratings.length;

        // 年龄结构
        const ages = starters
            .map(player => this.safeGet(player, 'age', null))
            .filter(age => this.isValidNumber(age) && age > 0);

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
     * @private
     * @param {object} features - 已提取的特征
     * @returns {object}
     */
    _extractComparisonFeatures(features) {
        const comparison = {};

        // 身价对比
        const homeValue = features.home_market_value_total || 0;
        const awayValue = features.away_market_value_total || 0;
        comparison.market_value_gap = homeValue - awayValue;
        comparison.market_value_ratio = awayValue > 0
            ? Math.round((homeValue / awayValue) * 1000) / 1000
            : (homeValue > 0 ? 999 : 1);

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
        comparison.age_gap = (homeAge > 0 && awayAge > 0)
            ? Math.round((homeAge - awayAge) * 10) / 10
            : 0;

        return comparison;
    }

    // ========================================================================
    // 工具方法
    // ========================================================================

    /**
     * 深度搜索身价数据
     * @private
     * @param {object} rawData - 原始数据
     * @param {string} prefix - 前缀
     * @returns {number}
     */
    _deepSearchMarketValue(rawData, prefix) {
        if (!rawData || !this.isValidObject(rawData)) {
            return 0;
        }

        // 路径 1: content.table.all
        const tableAll = this.safeGet(rawData, 'content.table.all', null);
        if (Array.isArray(tableAll) && tableAll.length > 0) {
            const marketValues = tableAll
                .map(player => {
                    const rawValue = this.safeGet(player, 'marketValue', 0);
                    return this.isValidNumber(rawValue) && rawValue > 0
                        ? rawValue * this.cfg.marketValueMultiplier
                        : 0;
                })
                .filter(value => value > 0);

            if (marketValues.length > 0) {
                const sum = marketValues.reduce((acc, val) => acc + val, 0);
                return Math.round(sum);
            }
        }

        // 路径 2: header 信息
        const header = this.safeGet(rawData, 'header', null);
        if (header && this.isValidObject(header)) {
            const homeValue = this.safeGet(header, 'homeMarketValue', 0);
            const awayValue = this.safeGet(header, 'awayMarketValue', 0);
            if (prefix === 'home' && this.isValidNumber(homeValue) && homeValue > 0) {
                return Math.round(homeValue * this.cfg.marketValueMultiplier);
            }
            if (prefix === 'away' && this.isValidNumber(awayValue) && awayValue > 0) {
                return Math.round(awayValue * this.cfg.marketValueMultiplier);
            }
        }

        return 0;
    }

    /**
     * 安全获取数组
     * @private
     * @param {object} obj - 源对象
     * @param {string} key - 属性名
     * @returns {Array}
     */
    _safeGetArray(obj, key) {
        if (!obj || typeof obj !== 'object') {
            return [];
        }
        const value = obj[key];
        return Array.isArray(value) ? value : [];
    }
}

// ============================================================================
// 导出
// ============================================================================
module.exports = {
    GoldenExtractor,
    DEFAULT_CONFIG,
    FEATURE_NAMES
};
