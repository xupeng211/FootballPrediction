/**
 * TacticalExtractor - V5.2 战术动量特征提取器
 * =============================================
 *
 * 从 FotMob L2 原始数据中提取战术统计和比赛动量特征：
 * 1. 战术特征 (xG, 控球率, 射门, 角球等)
 * 2. 动量特征 (momentum 时间序列分析)
 *
 * V5.2 模块化:
 * - 继承 BaseExtractor，符合行业标准
 * @module feature_engine/smelter/components/TacticalExtractor
 * @version V5.2.0-HOME-FORTRESS
 * @since 2026-03-14
 */

'use strict';

const { BaseExtractor } = require('./BaseExtractor');

// ============================================================================
// 配置常量
// ============================================================================

const DEFAULT_CONFIG = {
    // 动量分析参数
    momentumSegments: 6,           // 将比赛分为 6 个时段
    momentumThreshold: 0.6,        // 支配度阈值

    // 统计映射路径
    statsPath: 'content.stats.Periods.All.stats',

    // 默认值
    defaults: {
        xg: 0,
        possession: 50,
        shots: 0,
        corners: 0
    },

    // 严格模式
    strictMode: false
};

// 特征字段名清单
const FEATURE_NAMES = [
    // xG
    'home_xg', 'away_xg', 'total_xg', 'xg_diff', 'xg_ratio',
    'home_xg_per_shot', 'away_xg_per_shot',

    // 控球率
    'home_possession', 'away_possession',
    'home_possession_pct', 'away_possession_pct',
    'possession_diff', 'possession_ratio',

    // 射门
    'home_shots', 'away_shots',
    'home_shots_on_target', 'away_shots_on_target',
    'home_shots_off_target', 'away_shots_off_target',
    'home_shot_accuracy', 'away_shot_accuracy',
    'shots_on_target_diff',

    // 角球
    'home_corners', 'away_corners',
    'corners_diff', 'total_corners',

    // 犯规和牌
    'home_fouls', 'away_fouls',
    'home_yellow_cards', 'away_yellow_cards',
    'home_red_cards', 'away_red_cards',
    'fouls_diff', 'total_fouls',
    'home_discipline_score', 'away_discipline_score',
    'discipline_diff',

    // 机会创造
    'home_big_chances', 'away_big_chances',
    'big_chances_diff',

    // 综合实力
    'home_strength_index', 'away_strength_index',
    'strength_diff',

    // 动量
    'has_momentum_data',
    'momentum_samples_count',
    'momentum_overall_mean',
    'momentum_direction',
    'momentum_trend',
    'momentum_seg1_mean', 'momentum_seg1_std', 'momentum_seg1_dominance',
    'momentum_seg2_mean', 'momentum_seg2_std', 'momentum_seg2_dominance',
    'momentum_seg3_mean', 'momentum_seg3_std', 'momentum_seg3_dominance',
    'momentum_seg4_mean', 'momentum_seg4_std', 'momentum_seg4_dominance',
    'momentum_seg5_mean', 'momentum_seg5_std', 'momentum_seg5_dominance',
    'momentum_seg6_mean', 'momentum_seg6_std', 'momentum_seg6_dominance'
];

// 统计类型映射
const STATS_MAPPING = {
    'Expected goals (xG)': { home: 'home_xg', away: 'away_xg' },
    'Expected goals': { home: 'home_xg', away: 'away_xg' },
    'xG': { home: 'home_xg', away: 'away_xg' },
    'Ball possession': { home: 'home_possession', away: 'away_possession' },
    'Possession': { home: 'home_possession', away: 'away_possession' },
    'Total shots': { home: 'home_shots', away: 'away_shots' },
    'Shots': { home: 'home_shots', away: 'away_shots' },
    'Shots on target': { home: 'home_shots_on_target', away: 'away_shots_on_target' },
    'Shots off target': { home: 'home_shots_off_target', away: 'away_shots_off_target' },
    'Corners': { home: 'home_corners', away: 'away_corners' },
    'Corner kicks': { home: 'home_corners', away: 'away_corners' },
    'Fouls': { home: 'home_fouls', away: 'away_fouls' },
    'Yellow cards': { home: 'home_yellow_cards', away: 'away_yellow_cards' },
    'Red cards': { home: 'home_red_cards', away: 'away_red_cards' },
    'Big chances': { home: 'home_big_chances', away: 'away_big_chances' }
};

// ============================================================================
// TacticalExtractor 类
// ============================================================================

/**
 * 战术动量特征提取器
 */
class TacticalExtractor extends BaseExtractor {
    /**
     * @param {object} config - 配置选项
     */
    constructor(config = {}) {
        super({
            name: 'TacticalExtractor',
            version: 'V5.2.0-HOME-FORTRESS',
            requiredFields: ['content.stats'],
            config: { ...DEFAULT_CONFIG, ...config }
        });

        this.cfg = this.config;
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
     * @param {object} context - 上下文信息
     * @returns {object} 战术动量特征字典
     */
    extract(rawData, context = {}) {
        if (!rawData || !this.isValidObject(rawData)) {
            return this.createEmptyFeatures('无效的原始数据');
        }

        const features = {};

        // ========== 1. 提取战术统计特征 ==========
        const statsFeatures = this._extractStatsFeatures(rawData);
        Object.assign(features, statsFeatures);

        // ========== 2. 提取动量特征 ==========
        const momentumFeatures = this._extractMomentumFeatures(rawData);
        Object.assign(features, momentumFeatures);

        // ========== 3. 计算高级特征 ==========
        const advancedFeatures = this._calculateAdvancedFeatures(features);
        Object.assign(features, advancedFeatures);

        return features;
    }

    // ========================================================================
    // 私有提取方法
    // ========================================================================

    /**
     * 提取统计特征
     * @private
     * @param {object} rawData - 原始数据
     * @returns {object}
     */
    _extractStatsFeatures(rawData) {
        const features = {};

        // 路径: content.stats.Periods.All.stats
        const allStats = this.safeGet(rawData, this.cfg.statsPath, null);

        if (!allStats || !Array.isArray(allStats)) {
            // 尝试备用路径
            const altStats = this.safeGet(rawData, 'content.stats', null);
            if (altStats && Array.isArray(altStats)) {
                return this._extractStatsFromArray(altStats);
            }
            return this._createDefaultStatsFeatures();
        }

        return this._extractStatsFromArray(allStats);
    }

    /**
     * 从统计数组中提取特征
     * @private
     * @param {Array} statsArray - 统计数组
     * @returns {object}
     */
    _extractStatsFromArray(statsArray) {
        const features = {};

        for (const statItem of statsArray) {
            const statName = statItem.title || '';

            if (statItem.stats && Array.isArray(statItem.stats)) {
                // 检查是否是嵌套结构
                if (statItem.stats.length > 0 && typeof statItem.stats[0] === 'object') {
                    for (const subStat of statItem.stats) {
                        if (subStat.title && subStat.stats) {
                            const mapping = STATS_MAPPING[subStat.title];
                            if (mapping && Array.isArray(subStat.stats)) {
                                features[mapping.home] = this._parseStatValue(subStat.stats[0]);
                                features[mapping.away] = this._parseStatValue(subStat.stats[1]);
                            }
                        }
                    }
                } else {
                    // 直接值格式
                    const mapping = STATS_MAPPING[statName];
                    if (mapping) {
                        features[mapping.home] = this._parseStatValue(statItem.stats[0]);
                        features[mapping.away] = this._parseStatValue(statItem.stats[1]);
                    }
                }
            }

            // 兼容旧格式
            if (statItem.home !== undefined && statItem.away !== undefined) {
                const mapping = STATS_MAPPING[statName];
                if (mapping) {
                    features[mapping.home] = this._parseStatValue(statItem.home);
                    features[mapping.away] = this._parseStatValue(statItem.away);
                }
            }
        }

        // 处理百分比值
        if (features.home_possession !== undefined) {
            features.home_possession_pct = this._parsePercentage(features.home_possession);
        }
        if (features.away_possession !== undefined) {
            features.away_possession_pct = this._parsePercentage(features.away_possession);
        }

        return features;
    }

    /**
     * 解析统计值
     * @private
     * @param {*} value - 原始值
     * @returns {number}
     */
    _parseStatValue(value) {
        if (value === null || value === undefined) {
            return 0;
        }

        if (typeof value === 'number') {
            return value;
        }

        if (typeof value === 'string') {
            if (value.includes('%')) {
                return parseFloat(value.replace('%', ''));
            }
            const parsed = parseFloat(value);
            return isNaN(parsed) ? 0 : parsed;
        }

        return 0;
    }

    /**
     * 解析百分比值
     * @private
     * @param {*} value - 原始值
     * @returns {number}
     */
    _parsePercentage(value) {
        if (typeof value === 'number') {
            return value > 1 ? value : value * 100;
        }
        return 50;
    }

    /**
     * 创建默认统计特征
     * @private
     * @returns {object}
     */
    _createDefaultStatsFeatures() {
        return {
            home_xg: 0, away_xg: 0,
            home_possession: 50, away_possession: 50,
            home_possession_pct: 50, away_possession_pct: 50,
            home_shots: 0, away_shots: 0,
            home_shots_on_target: 0, away_shots_on_target: 0,
            home_corners: 0, away_corners: 0,
            home_fouls: 0, away_fouls: 0,
            home_yellow_cards: 0, away_yellow_cards: 0,
            home_red_cards: 0, away_red_cards: 0,
            home_big_chances: 0, away_big_chances: 0
        };
    }

    /**
     * 提取动量特征
     * @private
     * @param {object} rawData - 原始数据
     * @returns {object}
     */
    _extractMomentumFeatures(rawData) {
        const features = {
            has_momentum_data: false,
            momentum_samples_count: 0
        };

        // 尝试多种路径提取 momentum 数据
        let momentum = this.safeGet(rawData, 'content.momentum.main.data', null);

        if (!momentum || !Array.isArray(momentum)) {
            momentum = this.safeGet(rawData, 'content.momentum.data', null);
        }

        if (!momentum || !Array.isArray(momentum)) {
            const momentumObj = this.safeGet(rawData, 'content.momentum', null);
            if (momentumObj && this.isValidObject(momentumObj)) {
                momentum = this.safeGet(momentumObj, 'data', null) ||
                    this.safeGet(momentumObj, 'main.data', null);
            }
        }

        // 检查是否有有效的 momentum 数据
        if (!momentum || !Array.isArray(momentum) || momentum.length < 3) {
            return this._createFallbackMomentumFeatures(features);
        }

        features.has_momentum_data = true;
        features.momentum_samples_count = momentum.length;

        // 分析 momentum 时间序列
        const segmentSize = Math.ceil(momentum.length / this.cfg.momentumSegments);
        const segments = [];

        for (let i = 0; i < this.cfg.momentumSegments; i++) {
            const start = i * segmentSize;
            const end = Math.min(start + segmentSize, momentum.length);
            segments.push(momentum.slice(start, end));
        }

        // 计算每个时段的动量统计
        for (let i = 0; i < segments.length; i++) {
            const segment = segments[i];
            if (segment.length === 0) continue;

            const values = segment
                .map(s => typeof s === 'object' ? this.safeGet(s, 'value', 0) : (typeof s === 'number' ? s : 0))
                .filter(v => !isNaN(v));

            if (values.length === 0) continue;

            const mean = values.reduce((a, b) => a + b, 0) / values.length;
            const variance = values.reduce((acc, v) => acc + Math.pow(v - mean, 2), 0) / values.length;
            const std = Math.sqrt(variance);
            const dominance = Math.round((mean + 100) / 2);

            features[`momentum_seg${i + 1}_mean`] = Math.round(mean * 100) / 100;
            features[`momentum_seg${i + 1}_std`] = Math.round(std * 100) / 100;
            features[`momentum_seg${i + 1}_dominance`] = Math.max(0, Math.min(100, dominance));
            features[`momentum_seg${i + 1}_samples`] = values.length;
        }

        // 计算整体动量趋势
        const allValues = momentum
            .map(s => typeof s === 'object' ? this.safeGet(s, 'value', 0) : (typeof s === 'number' ? s : 0))
            .filter(v => !isNaN(v));

        if (allValues.length > 0) {
            const overallMean = allValues.reduce((a, b) => a + b, 0) / allValues.length;
            features.momentum_overall_mean = Math.round(overallMean * 100) / 100;

            // 判断动量方向
            if (overallMean > 10) {
                features.momentum_direction = 'home_dominant';
            } else if (overallMean < -10) {
                features.momentum_direction = 'away_dominant';
            } else {
                features.momentum_direction = 'balanced';
            }

            // 计算动量变化趋势
            const halfPoint = Math.floor(allValues.length / 2);
            const firstHalf = allValues.slice(0, halfPoint);
            const secondHalf = allValues.slice(halfPoint);

            if (firstHalf.length > 0 && secondHalf.length > 0) {
                const firstMean = firstHalf.reduce((a, b) => a + b, 0) / firstHalf.length;
                const secondMean = secondHalf.reduce((a, b) => a + b, 0) / secondHalf.length;
                features.momentum_trend = Math.round((secondMean - firstMean) * 100) / 100;
            }
        }

        return features;
    }

    /**
     * 创建降级动量特征
     * @private
     * @param {object} features - 现有特征
     * @returns {object}
     */
    _createFallbackMomentumFeatures(features) {
        features.has_momentum_data = false;
        features.momentum_samples_count = 0;
        features.momentum_direction = 'unknown';
        features.momentum_trend = 0;

        // 为每个时段分配默认值
        for (let i = 1; i <= this.cfg.momentumSegments; i++) {
            features[`momentum_seg${i}_mean`] = 0;
            features[`momentum_seg${i}_std`] = 0;
            features[`momentum_seg${i}_dominance`] = 50;
            features[`momentum_seg${i}_samples`] = 0;
        }

        features.momentum_overall_mean = 0;
        features.momentum_fallback = true;

        return features;
    }

    /**
     * 计算高级特征
     * @private
     * @param {object} features - 基础特征
     * @returns {object}
     */
    _calculateAdvancedFeatures(features) {
        const advanced = {};

        // xG 相关
        const homeXg = features.home_xg || 0;
        const awayXg = features.away_xg || 0;

        advanced.total_xg = homeXg + awayXg;
        advanced.xg_diff = homeXg - awayXg;
        advanced.xg_ratio = awayXg > 0 ? homeXg / awayXg : (homeXg > 0 ? 99 : 1);

        const homeShots = features.home_shots || 0;
        const awayShots = features.away_shots || 0;
        advanced.home_xg_per_shot = homeShots > 0 ? homeXg / homeShots : 0;
        advanced.away_xg_per_shot = awayShots > 0 ? awayXg / awayShots : 0;

        // 控球率相关
        const homePossession = features.home_possession_pct || 50;
        const awayPossession = features.away_possession_pct || 50;

        advanced.possession_diff = homePossession - awayPossession;
        advanced.possession_ratio = awayPossession > 0 ? homePossession / awayPossession : 1;

        // 射门效率
        const homeShotsOnTarget = features.home_shots_on_target || 0;
        const awayShotsOnTarget = features.away_shots_on_target || 0;

        advanced.home_shot_accuracy = homeShots > 0 ? homeShotsOnTarget / homeShots : 0;
        advanced.away_shot_accuracy = awayShots > 0 ? awayShotsOnTarget / awayShots : 0;
        advanced.shots_on_target_diff = homeShotsOnTarget - awayShotsOnTarget;

        // 角球和犯规
        const homeCorners = features.home_corners || 0;
        const awayCorners = features.away_corners || 0;
        advanced.corners_diff = homeCorners - awayCorners;
        advanced.total_corners = homeCorners + awayCorners;

        const homeFouls = features.home_fouls || 0;
        const awayFouls = features.away_fouls || 0;
        advanced.fouls_diff = homeFouls - awayFouls;
        advanced.total_fouls = homeFouls + awayFouls;

        // 纪律性
        const homeYellows = features.home_yellow_cards || 0;
        const awayYellows = features.away_yellow_cards || 0;
        const homeReds = features.home_red_cards || 0;
        const awayReds = features.away_red_cards || 0;

        advanced.home_discipline_score = 10 - (homeYellows * 0.5 + homeReds * 2);
        advanced.away_discipline_score = 10 - (awayYellows * 0.5 + awayReds * 2);
        advanced.discipline_diff = advanced.home_discipline_score - advanced.away_discipline_score;

        // 机会创造
        const homeBigChances = features.home_big_chances || 0;
        const awayBigChances = features.away_big_chances || 0;
        advanced.big_chances_diff = homeBigChances - awayBigChances;

        // 综合实力指数
        advanced.home_strength_index = Math.round(
            (homeXg * 30) +
            (homeShotsOnTarget * 5) +
            (homePossession * 0.2) +
            (homeBigChances * 10)
        );
        advanced.away_strength_index = Math.round(
            (awayXg * 30) +
            (awayShotsOnTarget * 5) +
            (awayPossession * 0.2) +
            (awayBigChances * 10)
        );
        advanced.strength_diff = advanced.home_strength_index - advanced.away_strength_index;

        return advanced;
    }
}

// ============================================================================
// 导出
// ============================================================================
module.exports = {
    TacticalExtractor,
    DEFAULT_CONFIG,
    FEATURE_NAMES,
    STATS_MAPPING
};
