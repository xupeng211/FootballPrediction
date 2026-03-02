/**
 * OddsMovementExtractor - 赔率变动/Steam 信号提取器
 * ================================================
 *
 * 从赔率时间序列中提取市场情绪信号：
 * 1. Steam Strength - 临场剧烈跳水检测
 * 2. Market Consensus - 隐含概率分布
 * 3. 异常检测 - 赔率与实力模型背离
 *
 * @module feature_engine/extractors/OddsMovementExtractor
 * @version V176.0.0
 */

'use strict';

const { safeGet, is } = require('../../core/utils/SafeAccess');

/**
 * 默认配置
 */
const DEFAULT_CONFIG = {
    // Steam 检测参数
    steamThreshold: 0.10,           // 10% 变化触发 Steam
    steamTimeWindowMinutes: 30,     // 临场 30 分钟窗口

    // 异常检测参数
    anomalyThreshold: 0.15,         // 15% 背离触发异常

    // 默认赔率（数据缺失时）
    defaultOdds: { home: 2.5, draw: 3.3, away: 2.8 }
};

/**
 * 安全获取数组属性
 */
function safeGetArray(obj, key, defaultValue = []) {
    const value = obj?.[key];
    return Array.isArray(value) ? value : defaultValue;
}

/**
 * 从原始数据中提取赔率变动特征
 *
 * @param {Object} rawData - FotMob L2 原始数据
 * @param {Object} tacticalFeatures - 战术特征（用于异常检测）
 * @param {Object} config - 配置选项
 * @returns {Object} 赔率特征字典
 */
function extractOddsMovementFeatures(rawData, tacticalFeatures = {}, config = DEFAULT_CONFIG) {
    if (!rawData || !is.object(rawData)) {
        return createEmptyOddsFeatures();
    }

    const features = {};

    // 提取赔率数据
    const oddsData = extractOddsData(rawData);

    // 1. 基础赔率特征
    const basicFeatures = extractBasicOddsFeatures(oddsData);
    Object.assign(features, basicFeatures);

    // 2. 隐含概率（Market Consensus）
    const consensusFeatures = calculateMarketConsensus(oddsData);
    Object.assign(features, consensusFeatures);

    // 3. Steam 信号检测
    const steamFeatures = detectSteamSignals(oddsData, config);
    Object.assign(features, steamFeatures);

    // 4. 异常检测（与 xG 模型对比）
    const anomalyFeatures = detectOddsAnomaly(features, tacticalFeatures, config);
    Object.assign(features, anomalyFeatures);

    // 元数据
    features._version = 'V176.0.0';
    features._extractedAt = new Date().toISOString();

    return features;
}

/**
 * 从原始数据中提取赔率数据
 */
function extractOddsData(rawData) {
    const oddsData = {
        initial: { home: null, draw: null, away: null },
        current: { home: null, draw: null, away: null },
        history: [],
        hasData: false
    };

    // 尝试多种路径提取赔率
    // 路径 1: content.odds
    const odds = safeGet(rawData, 'content.odds', {});

    // 路径 2: general.betting
    const betting = safeGet(rawData, 'general.betting', {});

    // 提取初盘赔率
    if (odds.initial) {
        oddsData.initial.home = safeGet(odds.initial, 'home');
        oddsData.initial.draw = safeGet(odds.initial, 'draw');
        oddsData.initial.away = safeGet(odds.initial, 'away');
    }

    // 提取当前赔率
    if (odds.current) {
        oddsData.current.home = safeGet(odds.current, 'home');
        oddsData.current.draw = safeGet(odds.current, 'draw');
        oddsData.current.away = safeGet(odds.current, 'away');
    }

    // 提取历史赔率
    if (odds.history && Array.isArray(odds.history)) {
        oddsData.history = odds.history;
    }

    // 从 betting 提取
    if (betting.odds1X2) {
        const odds1X2 = betting.odds1X2;
        if (!oddsData.initial.home && odds1X2.initial) {
            oddsData.initial.home = odds1X2.initial.home;
            oddsData.initial.draw = odds1X2.initial.draw;
            oddsData.initial.away = odds1X2.initial.away;
        }
        if (!oddsData.current.home && odds1X22.current) {
            oddsData.current.home = odds1X2.current.home;
            oddsData.current.draw = odds1X2.current.draw;
            oddsData.current.away = odds1X2.current.away;
        }
    }

    // 判断是否有有效数据
    oddsData.hasData = !!(oddsData.initial.home || oddsData.current.home);

    return oddsData;
}

/**
 * 提取基础赔率特征
 */
function extractBasicOddsFeatures(oddsData) {
    const features = {};

    // 初盘赔率
    features.initial_home_odds = oddsData.initial.home || 0;
    features.initial_draw_odds = oddsData.initial.draw || 0;
    features.initial_away_odds = oddsData.initial.away || 0;

    // 当前赔率
    features.current_home_odds = oddsData.current.home || 0;
    features.current_draw_odds = oddsData.current.draw || 0;
    features.current_away_odds = oddsData.current.away || 0;

    // 赔率变化（绝对值和百分比）
    if (features.initial_home_odds > 0 && features.current_home_odds > 0) {
        features.home_odds_change = features.current_home_odds - features.initial_home_odds;
        features.home_odds_change_pct = (features.home_odds_change / features.initial_home_odds) * 100;

        features.draw_odds_change = features.current_draw_odds - features.initial_draw_odds;
        features.draw_odds_change_pct = (features.draw_odds_change / features.initial_draw_odds) * 100;

        features.away_odds_change = features.current_away_odds - features.initial_away_odds;
        features.away_odds_change_pct = (features.away_odds_change / features.initial_away_odds) * 100;

        // 总变化幅度
        features.total_movement = Math.abs(features.home_odds_change_pct) +
                                   Math.abs(features.draw_odds_change_pct) +
                                   Math.abs(features.away_odds_change_pct);
    } else {
        features.home_odds_change = 0;
        features.home_odds_change_pct = 0;
        features.draw_odds_change = 0;
        features.draw_odds_change_pct = 0;
        features.away_odds_change = 0;
        features.away_odds_change_pct = 0;
        features.total_movement = 0;
    }

    features.has_odds_data = oddsData.hasData;
    features.odds_history_count = oddsData.history.length;

    return features;
}

/**
 * 计算市场共识（隐含概率）
 */
function calculateMarketConsensus(oddsData) {
    const features = {};

    // 使用当前赔率计算隐含概率
    const home = oddsData.current.home || oddsData.initial.home || 0;
    const draw = oddsData.current.draw || oddsData.initial.draw || 0;
    const away = oddsData.current.away || oddsData.initial.away || 0;

    if (home > 0 && draw > 0 && away > 0) {
        // 原始隐含概率
        const rawHome = 1 / home;
        const rawDraw = 1 / draw;
        const rawAway = 1 / away;

        // 总边际（用于归一化）
        const margin = rawHome + rawDraw + rawAway;

        // 归一化后的隐含概率
        features.implied_prob_home = Math.round((rawHome / margin) * 1000) / 1000;
        features.implied_prob_draw = Math.round((rawDraw / margin) * 1000) / 1000;
        features.implied_prob_away = Math.round((rawAway / margin) * 1000) / 1000;

        // 博彩公司边际（水钱）
        features.bookmaker_margin = Math.round((margin - 1) * 1000) / 1000;

        // 最可能结果
        const probs = [
            { outcome: 'home', prob: features.implied_prob_home },
            { outcome: 'draw', prob: features.implied_prob_draw },
            { outcome: 'away', prob: features.implied_prob_away }
        ];
        probs.sort((a, b) => b.prob - a.prob);
        features.favorite = probs[0].outcome;
        features.favorite_prob = probs[0].prob;

        // 概率分布熵（衡量不确定性）
        const entropy = -(
            features.implied_prob_home * Math.log2(features.implied_prob_home) +
            features.implied_prob_draw * Math.log2(features.implied_prob_draw) +
            features.implied_prob_away * Math.log2(features.implied_prob_away)
        );
        features.prob_entropy = Math.round(entropy * 100) / 100;

    } else {
        features.implied_prob_home = 0.333;
        features.implied_prob_draw = 0.333;
        features.implied_prob_away = 0.333;
        features.bookmaker_margin = 0;
        features.favorite = 'unknown';
        features.favorite_prob = 0;
        features.prob_entropy = 1.585; // 最大熵
    }

    return features;
}

/**
 * 检测 Steam 信号（临场剧烈变动）
 */
function detectSteamSignals(oddsData, config) {
    const features = {
        steam_detected: false,
        steam_strength: 0,
        steam_direction: 'none',
        steam_outcome: 'none'
    };

    if (!oddsData.hasData || oddsData.history.length < 2) {
        return features;
    }

    const history = oddsData.history;

    // 找到临场 30 分钟内的赔率变化
    const recentHistory = history.filter(h => {
        const minutesToKickoff = safeGet(h, 'minutesToKickoff', 999);
        return minutesToKickoff <= config.steamTimeWindowMinutes;
    });

    if (recentHistory.length < 2) {
        return features;
    }

    // 计算各结果的变动
    const outcomes = ['home', 'draw', 'away'];
    let maxSteam = 0;
    let steamOutcome = 'none';
    let steamDirection = 'none';

    for (const outcome of outcomes) {
        const values = recentHistory
            .map(h => safeGet(h, outcome))
            .filter(v => v > 0);

        if (values.length < 2) continue;

        const first = values[0];
        const last = values[values.length - 1];
        const change = Math.abs((last - first) / first);

        if (change > maxSteam) {
            maxSteam = change;
            steamOutcome = outcome;
            steamDirection = last < first ? 'drop' : 'rise';
        }
    }

    // 判断是否触发 Steam
    if (maxSteam >= config.steamThreshold) {
        features.steam_detected = true;
        features.steam_strength = Math.round(maxSteam * 1000) / 1000;
        features.steam_direction = steamDirection;
        features.steam_outcome = steamOutcome;
    }

    return features;
}

/**
 * 检测赔率异常（与 xG 模型对比）
 */
function detectOddsAnomaly(oddsFeatures, tacticalFeatures, config) {
    const features = {
        odds_anomaly_flag: false,
        odds_vs_xg_divergence: 0
    };

    // 需要 xG 数据
    const homeXg = tacticalFeatures.home_expected_goals || 0;
    const awayXg = tacticalFeatures.away_expected_goals || 0;

    if (!oddsFeatures.has_odds_data || (homeXg === 0 && awayXg === 0)) {
        return features;
    }

    // 基于 xG 计算预期胜率（简化模型）
    const totalXg = homeXg + awayXg;
    const xgBasedHomeWin = totalXg > 0 ? homeXg / totalXg : 0.5;

    // 与隐含概率对比
    const impliedHomeWin = oddsFeatures.implied_prob_home || 0.5;
    const divergence = Math.abs(xgBasedHomeWin - impliedHomeWin);

    features.odds_vs_xg_divergence = Math.round(divergence * 1000) / 1000;

    // 判断是否异常
    if (divergence >= config.anomalyThreshold) {
        features.odds_anomaly_flag = true;

        // 记录背离方向
        features.anomaly_direction = xgBasedHomeWin > impliedHomeWin ? 'xg_higher' : 'odds_higher';
    }

    return features;
}

/**
 * 创建空赔率特征
 */
function createEmptyOddsFeatures() {
    return {
        has_odds_data: false,
        initial_home_odds: 0,
        initial_draw_odds: 0,
        initial_away_odds: 0,
        current_home_odds: 0,
        current_draw_odds: 0,
        current_away_odds: 0,
        implied_prob_home: 0.333,
        implied_prob_draw: 0.333,
        implied_prob_away: 0.333,
        steam_detected: false,
        steam_strength: 0,
        odds_anomaly_flag: false,
        _error: 'No odds data available',
        _version: 'V176.0.0',
        _extractedAt: new Date().toISOString()
    };
}

module.exports = {
    extractOddsMovementFeatures,
    extractOddsData,
    calculateMarketConsensus,
    detectSteamSignals,
    detectOddsAnomaly,
    createEmptyOddsFeatures,
    DEFAULT_CONFIG
};
