/**
 * TacticalMomentumExtractor - 战术动量特征提取器
 * ================================================
 *
 * 从 FotMob L2 原始数据中提取战术统计和比赛动量特征：
 * 1. 战术特征 (xG, 控球率, 射门, 角球等)
 * 2. 动量特征 (momentum 时间序列分析)
 *
 * @module feature_engine/extractors/TacticalMomentumExtractor
 * @version V176.0.0
 */

'use strict';

const { safeGet, hasPath, is } = require('../../core/utils/SafeAccess');

/**
 * 默认配置
 */
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
    }
};

/**
 * 安全获取数组属性
 */
function safeGetArray(obj, key, defaultValue = []) {
    const value = obj?.[key];
    return Array.isArray(value) ? value : defaultValue;
}

/**
 * 从原始数据中提取战术动量特征
 *
 * @param {Object} rawData - FotMob L2 原始数据 (raw_match_data.raw_data)
 * @param {Object} config - 配置选项
 * @returns {Object} 战术动量特征字典
 */
function extractTacticalFeatures(rawData, config = DEFAULT_CONFIG) {
    if (!rawData || !is.object(rawData)) {
        return createEmptyTacticalFeatures();
    }

    const features = {};
    const cfg = { ...DEFAULT_CONFIG, ...config };

    // ========== 1. 提取战术统计特征 ==========
    const statsFeatures = extractStatsFeatures(rawData, cfg);
    Object.assign(features, statsFeatures);

    // ========== 2. 提取动量特征 ==========
    const momentumFeatures = extractMomentumFeatures(rawData, cfg);
    Object.assign(features, momentumFeatures);

    // ========== 3. 计算高级特征 ==========
    const advancedFeatures = calculateAdvancedFeatures(features, cfg);
    Object.assign(features, advancedFeatures);

    // 元数据
    features._extractedAt = new Date().toISOString();
    features._version = 'V176.0.0';

    return features;
}

/**
 * 提取统计特征 (xG, 控球率, 射门等)
 */
function extractStatsFeatures(rawData, config) {
    const features = {};

    // 路径: content.stats.Periods.All.stats
    const allStats = safeGet(rawData, config.statsPath, null);

    if (!allStats || !Array.isArray(allStats)) {
        // 尝试备用路径
        const altStats = safeGet(rawData, 'content.stats', null);
        if (altStats && Array.isArray(altStats)) {
            return extractStatsFromArray(altStats, features);
        }

        // 无统计数据，返回默认值
        return createDefaultStatsFeatures(features);
    }

    return extractStatsFromArray(allStats, features);
}

/**
 * 从统计数组中提取特征
 * V176: 适配 FotMob 数据格式 { title, stats: [home, away] }
 */
function extractStatsFromArray(statsArray, features) {
    // FotMob 统计类型映射
    const statsMapping = {
        // xG 相关
        'Expected goals (xG)': { home: 'home_xg', away: 'away_xg' },
        'Expected goals': { home: 'home_xg', away: 'away_xg' },
        'xG': { home: 'home_xg', away: 'away_xg' },
        'xGOT': { home: 'home_xgot', away: 'away_xgot' },

        // 控球率
        'Ball possession': { home: 'home_possession', away: 'away_possession' },
        'Possession': { home: 'home_possession', away: 'away_possession' },

        // 射门
        'Total shots': { home: 'home_shots', away: 'away_shots' },
        'Shots': { home: 'home_shots', away: 'away_shots' },
        'Shots on target': { home: 'home_shots_on_target', away: 'away_shots_on_target' },
        'Shots off target': { home: 'home_shots_off_target', away: 'away_shots_off_target' },
        'Shots inside box': { home: 'home_shots_inside_box', away: 'away_shots_inside_box' },
        'Shots outside box': { home: 'home_shots_outside_box', away: 'away_shots_outside_box' },
        'Blocked shots': { home: 'home_blocked_shots', away: 'away_blocked_shots' },
        'Hit woodwork': { home: 'home_hit_woodwork', away: 'away_hit_woodwork' },

        // 角球和任意球
        'Corners': { home: 'home_corners', away: 'away_corners' },
        'Corner kicks': { home: 'home_corners', away: 'away_corners' },
        'Free kicks': { home: 'home_free_kicks', away: 'away_free_kicks' },

        // 犯规和牌
        'Fouls': { home: 'home_fouls', away: 'away_fouls' },
        'Yellow cards': { home: 'home_yellow_cards', away: 'away_yellow_cards' },
        'Red cards': { home: 'home_red_cards', away: 'away_red_cards' },

        // 越位
        'Offsides': { home: 'home_offsides', away: 'away_offsides' },

        // 传球
        'Passes': { home: 'home_passes', away: 'away_passes' },
        'Accurate passes': { home: 'home_accurate_passes', away: 'away_accurate_passes' },
        'Pass accuracy': { home: 'home_pass_accuracy', away: 'away_pass_accuracy' },

        // 其他
        'Big chances': { home: 'home_big_chances', away: 'away_big_chances' },
        'Counter attacks': { home: 'home_counter_attacks', away: 'away_counter_attacks' }
    };

    // 遍历统计数组
    for (const statItem of statsArray) {
        const statName = statItem.title || '';

        // V176: 处理嵌套统计 (如 Shots 包含子项)
        if (statItem.stats && Array.isArray(statItem.stats)) {
            // 检查是否是嵌套结构 (stats 包含对象数组)
            if (statItem.stats.length > 0 && typeof statItem.stats[0] === 'object') {
                // 递归处理嵌套统计
                for (const subStat of statItem.stats) {
                    if (subStat.title && subStat.stats) {
                        const mapping = statsMapping[subStat.title];
                        if (mapping && Array.isArray(subStat.stats)) {
                            features[mapping.home] = parseStatValue(subStat.stats[0]);
                            features[mapping.away] = parseStatValue(subStat.stats[1]);
                        }
                    }
                }
            } else {
                // 直接值格式: stats: [homeValue, awayValue]
                const mapping = statsMapping[statName];
                if (mapping) {
                    features[mapping.home] = parseStatValue(statItem.stats[0]);
                    features[mapping.away] = parseStatValue(statItem.stats[1]);
                }
            }
        }

        // 兼容旧格式: { title, home, away }
        if (statItem.home !== undefined && statItem.away !== undefined) {
            const mapping = statsMapping[statName];
            if (mapping) {
                features[mapping.home] = parseStatValue(statItem.home);
                features[mapping.away] = parseStatValue(statItem.away);
            }
        }
    }

    // 处理百分比值 (如控球率)
    if (features.home_possession !== undefined) {
        features.home_possession_pct = parsePercentage(features.home_possession);
    }
    if (features.away_possession !== undefined) {
        features.away_possession_pct = parsePercentage(features.away_possession);
    }

    return features;
}

/**
 * 解析统计值
 */
function parseStatValue(value) {
    if (value === null || value === undefined) {
        return 0;
    }

    // 如果是数字，直接返回
    if (typeof value === 'number') {
        return value;
    }

    // 如果是字符串，尝试解析
    if (typeof value === 'string') {
        // 处理百分比 (如 "55%")
        if (value.includes('%')) {
            return parseFloat(value.replace('%', ''));
        }
        // 处理普通数字
        const parsed = parseFloat(value);
        return isNaN(parsed) ? 0 : parsed;
    }

    return 0;
}

/**
 * 解析百分比值
 */
function parsePercentage(value) {
    if (typeof value === 'number') {
        // 如果值大于 1，假设已经是百分比形式
        return value > 1 ? value : value * 100;
    }
    return 50; // 默认 50%
}

/**
 * 创建默认统计特征
 */
function createDefaultStatsFeatures(features) {
    const defaults = {
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

    Object.assign(features, defaults);
    return features;
}

/**
 * 提取动量特征
 * 支持多种数据路径:
 * - content.momentum.main.data
 * - content.momentum.data
 * - content.momentum
 */
function extractMomentumFeatures(rawData, config) {
    const features = {
        has_momentum_data: false,
        momentum_samples_count: 0
    };

    // 尝试多种路径提取 momentum 数据
    let momentum = safeGet(rawData, 'content.momentum.main.data', null);

    if (!momentum || !Array.isArray(momentum)) {
        momentum = safeGet(rawData, 'content.momentum.data', null);
    }

    if (!momentum || !Array.isArray(momentum)) {
        const momentumObj = safeGet(rawData, 'content.momentum', null);
        if (momentumObj && is.object(momentumObj)) {
            momentum = safeGet(momentumObj, 'data', null) || safeGet(momentumObj, 'main.data', null);
        }
    }

    // 检查是否有有效的 momentum 数据
    if (!momentum || !Array.isArray(momentum) || momentum.length < 3) {
        // 无 momentum 数据，使用统计拟合降级方案
        return createFallbackMomentumFeatures(features, rawData, config);
    }

    features.has_momentum_data = true;
    features.momentum_samples_count = momentum.length;

    // 分析 momentum 时间序列
    const segmentSize = Math.ceil(momentum.length / config.momentumSegments);
    const segments = [];

    for (let i = 0; i < config.momentumSegments; i++) {
        const start = i * segmentSize;
        const end = Math.min(start + segmentSize, momentum.length);
        const segment = momentum.slice(start, end);
        segments.push(segment);
    }

    // 计算每个时段的动量统计
    for (let i = 0; i < segments.length; i++) {
        const segment = segments[i];
        if (segment.length === 0) continue;

        // 提取动量值 (通常是 -100 到 100 之间的值)
        const values = segment
            .map(s => typeof s === 'object' ? safeGet(s, 'value', 0) : (typeof s === 'number' ? s : 0))
            .filter(v => !isNaN(v));

        if (values.length === 0) continue;

        // 计算均值和标准差
        const mean = values.reduce((a, b) => a + b, 0) / values.length;
        const variance = values.reduce((acc, v) => acc + Math.pow(v - mean, 2), 0) / values.length;
        const std = Math.sqrt(variance);

        // 动量支配度 (-100 到 100 映射到 0 到 100)
        const dominance = Math.round((mean + 100) / 2);

        features[`momentum_seg${i + 1}_mean`] = Math.round(mean * 100) / 100;
        features[`momentum_seg${i + 1}_std`] = Math.round(std * 100) / 100;
        features[`momentum_seg${i + 1}_dominance`] = Math.max(0, Math.min(100, dominance));
        features[`momentum_seg${i + 1}_samples`] = values.length;
    }

    // 计算整体动量趋势
    const allValues = momentum
        .map(s => typeof s === 'object' ? safeGet(s, 'value', 0) : (typeof s === 'number' ? s : 0))
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

        // 计算动量变化趋势 (后半段 vs 前半段)
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
 * 创建降级动量特征 (基于统计数据拟合)
 */
function createFallbackMomentumFeatures(features, rawData, config) {
    features.has_momentum_data = false;
    features.momentum_samples_count = 0;
    features.momentum_direction = 'unknown';
    features.momentum_trend = 0;

    // 基于统计数据估算动量
    const homePossession = features.home_possession_pct || 50;
    const homeShots = features.home_shots || 0;
    const awayShots = features.away_shots || 0;
    const homeXg = features.home_xg || 0;
    const awayXg = features.away_xg || 0;

    // 简单估算：基于控球率和射门
    const possessionFactor = (homePossession - 50) / 50; // -1 到 1
    const shotsFactor = homeShots + awayShots > 0
        ? (homeShots - awayShots) / (homeShots + awayShots)
        : 0;
    const xgFactor = homeXg + awayXg > 0
        ? (homeXg - awayXg) / (homeXg + awayXg)
        : 0;

    // 综合估算支配度
    const estimatedDominance = Math.round(
        (possessionFactor * 0.3 + shotsFactor * 0.35 + xgFactor * 0.35) * 50 + 50
    );

    // 为每个时段分配估算值
    for (let i = 1; i <= config.momentumSegments; i++) {
        features[`momentum_seg${i}_mean`] = 0;
        features[`momentum_seg${i}_std`] = 0;
        features[`momentum_seg${i}_dominance`] = estimatedDominance;
        features[`momentum_seg${i}_samples`] = 0;
    }

    features.momentum_overall_mean = 0;
    features.momentum_fallback = true;

    return features;
}

/**
 * 计算高级特征 (派生特征)
 */
function calculateAdvancedFeatures(features, config) {
    const advanced = {};

    // ========== xG 相关 ==========
    const homeXg = features.home_xg || 0;
    const awayXg = features.away_xg || 0;

    advanced.total_xg = homeXg + awayXg;
    advanced.xg_diff = homeXg - awayXg;
    advanced.xg_ratio = awayXg > 0 ? homeXg / awayXg : (homeXg > 0 ? 99 : 1);

    // xG 效率 (每射门的 xG)
    const homeShots = features.home_shots || 0;
    const awayShots = features.away_shots || 0;
    advanced.home_xg_per_shot = homeShots > 0 ? homeXg / homeShots : 0;
    advanced.away_xg_per_shot = awayShots > 0 ? awayXg / awayShots : 0;

    // ========== 控球率相关 ==========
    const homePossession = features.home_possession_pct || 50;
    const awayPossession = features.away_possession_pct || 50;

    advanced.possession_diff = homePossession - awayPossession;
    advanced.possession_ratio = awayPossession > 0 ? homePossession / awayPossession : 1;

    // ========== 射门效率 ==========
    const homeShotsOnTarget = features.home_shots_on_target || 0;
    const awayShotsOnTarget = features.away_shots_on_target || 0;

    advanced.home_shot_accuracy = homeShots > 0 ? homeShotsOnTarget / homeShots : 0;
    advanced.away_shot_accuracy = awayShots > 0 ? awayShotsOnTarget / awayShots : 0;
    advanced.shots_on_target_diff = homeShotsOnTarget - awayShotsOnTarget;

    // ========== 角球和犯规 ==========
    const homeCorners = features.home_corners || 0;
    const awayCorners = features.away_corners || 0;
    advanced.corners_diff = homeCorners - awayCorners;
    advanced.total_corners = homeCorners + awayCorners;

    const homeFouls = features.home_fouls || 0;
    const awayFouls = features.away_fouls || 0;
    advanced.fouls_diff = homeFouls - awayFouls;
    advanced.total_fouls = homeFouls + awayFouls;

    // ========== 纪律性 ==========
    const homeYellows = features.home_yellow_cards || 0;
    const awayYellows = features.away_yellow_cards || 0;
    const homeReds = features.home_red_cards || 0;
    const awayReds = features.away_red_cards || 0;

    advanced.home_discipline_score = 10 - (homeYellows * 0.5 + homeReds * 2);
    advanced.away_discipline_score = 10 - (awayYellows * 0.5 + awayReds * 2);
    advanced.discipline_diff = advanced.home_discipline_score - advanced.away_discipline_score;

    // ========== 机会创造 ==========
    const homeBigChances = features.home_big_chances || 0;
    const awayBigChances = features.away_big_chances || 0;
    advanced.big_chances_diff = homeBigChances - awayBigChances;

    // ========== 综合实力指数 ==========
    // 基于 xG、射门、控球率的综合评分
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

/**
 * 创建空战术特征
 */
function createEmptyTacticalFeatures() {
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
        has_momentum_data: false,
        momentum_samples_count: 0,
        _error: 'No valid raw data provided',
        _version: 'V176.0.0',
        _extractedAt: new Date().toISOString()
    };
}

module.exports = {
    extractTacticalFeatures,
    extractStatsFeatures,
    extractMomentumFeatures,
    calculateAdvancedFeatures,
    createEmptyTacticalFeatures,
    DEFAULT_CONFIG
};
