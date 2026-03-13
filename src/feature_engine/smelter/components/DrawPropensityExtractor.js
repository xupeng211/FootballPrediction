/**
 * DrawPropensityExtractor - V4.0 平局倾向特征提取器
 * ===================================================
 *
 * 专门用于解决平局预测准确率低的问题
 * 提取球队"平局体质"相关特征：
 * - 历史平局率
 * - 进攻保守性 (低xG + 低失球)
 * - 比赛胶着倾向
 *
 * V4.0 模块化:
 * - 继承 BaseExtractor
 * - 专门针对平局预测的优化
 * @module feature_engine/smelter/components/DrawPropensityExtractor
 * @version V4.0.0-MODULAR
 * @since 2026-03-14
 */

'use strict';

const { BaseExtractor } = require('./BaseExtractor');

// ============================================================================
// 配置常量
// ============================================================================

const DEFAULT_CONFIG = {
    // 滚动窗口大小
    rollingWindow: 10,  // 使用更多历史数据捕捉平局倾向

    // 最小样本数
    minSamples: 5,

    // 默认值
    defaults: {
        drawRate: 0.25,              // 平均平局率
        drawTendency: 0.0,           // 平局倾向指数
        defensiveStance: 0.5,        // 防守姿态
        lowScoringRate: 0.3,         // 低进球率
        competitiveBalance: 0.5      // 竞争力平衡
    },

    // 严格模式
    strictMode: false
};

// 特征字段名清单
const FEATURE_NAMES = [
    // 主队平局体质 (5维)
    'home_draw_rate',
    'home_draw_tendency',
    'home_defensive_stance',
    'home_low_scoring_rate',
    'home_competitive_balance',

    // 客队平局体质 (5维)
    'away_draw_rate',
    'away_draw_tendency',
    'away_defensive_stance',
    'away_low_scoring_rate',
    'away_competitive_balance',

    // 对局平局预测指标 (6维)
    'combined_draw_probability',
    'match_stalemate_index',
    'defensive_showdown_score',
    'boring_match_alert',
    'tactical_stalemate_index',
    'historical_draw_pattern'
];

// ============================================================================
// DrawPropensityExtractor 类
// ============================================================================

class DrawPropensityExtractor extends BaseExtractor {
    /**
     * @param {object} options - 配置选项
     * @param {object} options.dbPool - 数据库连接池（必需）
     * @param {object} options.config - 提取器配置
     */
    constructor(options = {}) {
        super({
            name: 'DrawPropensityExtractor',
            version: 'V4.0.0-MODULAR',
            requiredFields: [],
            config: { ...DEFAULT_CONFIG, ...(options.config || {}) }
        });

        this.dbPool = options.dbPool || null;
    }

    /**
     * 获取该提取器产出的特征字段名清单
     * @returns {Array<string>}
     */
    getFeatureNames() {
        return [...FEATURE_NAMES];
    }

    /**
     * 获取默认配置
     * @returns {object}
     */
    getDefaultConfig() {
        return { ...DEFAULT_CONFIG };
    }

    /**
     * 验证数据
     * @param {object} rawData - 原始数据
     * @returns {object}
     */
    validate(rawData) {
        return { valid: true };
    }

    // ========================================================================
    // 核心提取逻辑
    // ========================================================================

    /**
     * 执行特征提取
     * @param {object} rawData - 原始数据
     * @param {object} context - 上下文
     * @returns {Promise<object>}
     */
    async extract(rawData, context = {}) {
        const startTime = Date.now();
        this.stats.totalCalls++;

        try {
            if (!this.dbPool) {
                throw new Error('DrawPropensityExtractor 需要数据库连接池');
            }

            const { home_team, away_team, match_date, match_id } = rawData;

            if (!home_team || !away_team || !match_date) {
                return this._createEmptyFeatures('Missing required fields');
            }

            // 提取主队平局体质
            const homeFeatures = await this._extractTeamDrawPropensity(
                home_team, match_date, 'home'
            );

            // 提取客队平局体质
            const awayFeatures = await this._extractTeamDrawPropensity(
                away_team, match_date, 'away'
            );

            // 计算对局平局指标
            const matchupFeatures = this._calculateMatchupDrawIndicators(
                homeFeatures, awayFeatures, home_team, away_team
            );

            const features = {
                ...homeFeatures,
                ...awayFeatures,
                ...matchupFeatures,
                _extractedAt: new Date().toISOString(),
                _version: this.version,
                _source: 'DrawPropensityAnalysis'
            };

            this.stats.successfulCalls++;
            this._updateAvgExecutionTime(Date.now() - startTime);

            return features;

        } catch (error) {
            this.stats.failedCalls++;
            this.logger.error('平局倾向特征提取失败', {
                match_id: rawData.match_id,
                error: error.message
            });
            return this._createEmptyFeatures(error.message);
        }
    }

    /**
     * 提取球队平局体质
     * @private
     */
    async _extractTeamDrawPropensity(teamName, matchDate, prefix) {
        const window = this.config.rollingWindow;
        const minSamples = this.config.minSamples;

        try {
            const query = `
                SELECT 
                    m.match_id,
                    m.home_team,
                    m.away_team,
                    m.home_score,
                    m.away_score,
                    m.match_date,
                    l.tactical_features->>'home_xg' as home_xg,
                    l.tactical_features->>'away_xg' as away_xg,
                    l.tactical_features->>'home_possession' as home_possession,
                    l.tactical_features->>'away_possession' as away_possession,
                    l.tactical_features->>'total_xg' as total_xg,
                    l.tactical_features->>'possession_diff' as possession_diff
                FROM matches m
                INNER JOIN l3_features l ON m.match_id = l.match_id
                WHERE m.status = 'Harvested'
                  AND m.home_score IS NOT NULL
                  AND m.match_date < $1
                  AND (m.home_team = $2 OR m.away_team = $2)
                ORDER BY m.match_date DESC
                LIMIT $3
            `;

            const result = await this.dbPool.query(query, [matchDate, teamName, window * 2]);
            const matches = result.rows;

            if (matches.length < minSamples) {
                this.logger.debug(`球队 ${teamName} 平局数据不足 (${matches.length}/${minSamples})，使用默认值`);
                return this._createDefaultTeamFeatures(prefix);
            }

            // 计算各项平局指标
            const drawRate = this._calculateDrawRate(matches, teamName);
            const drawTendency = this._calculateDrawTendency(matches, teamName);
            const defensiveStance = this._calculateDefensiveStance(matches, teamName);
            const lowScoringRate = this._calculateLowScoringRate(matches, teamName);
            const competitiveBalance = this._calculateCompetitiveBalance(matches, teamName);

            return {
                [`${prefix}_draw_rate`]: drawRate,
                [`${prefix}_draw_tendency`]: drawTendency,
                [`${prefix}_defensive_stance`]: defensiveStance,
                [`${prefix}_low_scoring_rate`]: lowScoringRate,
                [`${prefix}_competitive_balance`]: competitiveBalance
            };

        } catch (error) {
            this.logger.error(`提取 ${teamName} 平局体质失败`, { error: error.message });
            return this._createDefaultTeamFeatures(prefix);
        }
    }

    // ========================================================================
    // 平局指标计算方法
    // ========================================================================

    /**
     * 计算历史平局率
     * @private
     */
    _calculateDrawRate(matches, teamName) {
        let draws = 0;
        const window = Math.min(matches.length, this.config.rollingWindow);

        for (const match of matches.slice(0, window)) {
            const isHome = match.home_team === teamName;
            const homeScore = parseInt(match.home_score);
            const awayScore = parseInt(match.away_score);

            const teamScore = isHome ? homeScore : awayScore;
            const oppScore = isHome ? awayScore : homeScore;

            if (teamScore === oppScore) {
                draws++;
            }
        }

        return parseFloat((draws / window).toFixed(3));
    }

    /**
     * 计算平局倾向指数
     * 基于：低进球 + 低失球 + 高控球 = 平局倾向
     * @private
     */
    _calculateDrawTendency(matches, teamName) {
        let tendencySum = 0;
        let count = 0;

        for (const match of matches.slice(0, this.config.rollingWindow)) {
            const isHome = match.home_team === teamName;

            const teamScore = parseInt(isHome ? match.home_score : match.away_score) || 0;
            const oppScore = parseInt(isHome ? match.away_score : match.home_score) || 0;
            const teamXG = parseFloat(isHome ? match.home_xg : match.away_xg) || 0;
            const oppXG = parseFloat(isHome ? match.away_xg : match.home_xg) || 0;

            // 平局倾向 = 低进球数(0-2) + 低失球数(0-1) + 低xG差
            const lowScoring = teamScore <= 1 ? 0.3 : (teamScore <= 2 ? 0.15 : 0);
            const lowConceding = oppScore <= 1 ? 0.3 : (oppScore <= 2 ? 0.15 : 0);
            const xgBalance = Math.abs(teamXG - oppXG) < 0.5 ? 0.4 : 0;

            tendencySum += (lowScoring + lowConceding + xgBalance);
            count++;
        }

        if (count === 0) return this.config.defaults.drawTendency;

        const avgTendency = tendencySum / count;
        return parseFloat(avgTendency.toFixed(3));
    }

    /**
     * 计算防守姿态
     * 基于：控球率低于50% + 低失球
     * @private
     */
    _calculateDefensiveStance(matches, teamName) {
        let stanceSum = 0;
        let count = 0;

        for (const match of matches.slice(0, this.config.rollingWindow)) {
            const isHome = match.home_team === teamName;

            const possession = parseFloat(isHome ? match.home_possession : match.away_possession) || 50;
            const conceded = parseInt(isHome ? match.away_score : match.home_score) || 0;

            // 低控球 + 低失球 = 防守姿态
            const possessionScore = possession < 45 ? 0.5 : (possession < 50 ? 0.25 : 0);
            const defensiveScore = conceded === 0 ? 0.5 : (conceded <= 1 ? 0.25 : 0);

            stanceSum += (possessionScore + defensiveScore);
            count++;
        }

        if (count === 0) return this.config.defaults.defensiveStance;

        return parseFloat((stanceSum / count).toFixed(3));
    }

    /**
     * 计算低进球率
     * 总进球 <= 2 的比赛占比
     * @private
     */
    _calculateLowScoringRate(matches, teamName) {
        let lowScoringCount = 0;
        const window = Math.min(matches.length, this.config.rollingWindow);

        for (const match of matches.slice(0, window)) {
            const isHome = match.home_team === teamName;

            const teamScore = parseInt(isHome ? match.home_score : match.away_score) || 0;
            const oppScore = parseInt(isHome ? match.away_score : match.home_score) || 0;
            const totalGoals = teamScore + oppScore;

            if (totalGoals <= 2) {
                lowScoringCount++;
            }
        }

        return parseFloat((lowScoringCount / window).toFixed(3));
    }

    /**
     * 计算竞争力平衡
     * 基于 xG 和比分的接近程度
     * @private
     */
    _calculateCompetitiveBalance(matches, teamName) {
        let balanceSum = 0;
        let count = 0;

        for (const match of matches.slice(0, this.config.rollingWindow)) {
            const isHome = match.home_team === teamName;

            const homeScore = parseInt(match.home_score) || 0;
            const awayScore = parseInt(match.away_score) || 0;
            const homeXG = parseFloat(match.home_xg) || 0;
            const awayXG = parseFloat(match.away_xg) || 0;

            // 比分差距
            const scoreDiff = Math.abs(homeScore - awayScore);
            const scoreBalance = scoreDiff <= 1 ? 0.5 : 0;

            // xG差距
            const xgDiff = Math.abs(homeXG - awayXG);
            const xgBalance = xgDiff <= 0.5 ? 0.5 : (xgDiff <= 1.0 ? 0.25 : 0);

            balanceSum += (scoreBalance + xgBalance);
            count++;
        }

        if (count === 0) return this.config.defaults.competitiveBalance;

        return parseFloat((balanceSum / count).toFixed(3));
    }

    /**
     * 计算对局平局指标
     * @private
     */
    _calculateMatchupDrawIndicators(home, away, homeTeam, awayTeam) {
        // 综合平局概率
        const homeDrawRate = home.home_draw_rate || 0.25;
        const awayDrawRate = away.away_draw_rate || 0.25;
        const combinedDrawProb = (homeDrawRate + awayDrawRate) / 2;

        // 胶着指数 (双方都有平局体质)
        const homeTendency = home.home_draw_tendency || 0;
        const awayTendency = away.away_draw_tendency || 0;
        const stalemateIndex = (homeTendency + awayTendency) / 2;

        // 防守对决分数
        const homeDefense = home.home_defensive_stance || 0.5;
        const awayDefense = away.away_defensive_stance || 0.5;
        const defensiveShowdown = (homeDefense + awayDefense) / 2;

        // 无聊比赛警报 (双方都是低进球)
        const homeLowScoring = home.home_low_scoring_rate || 0;
        const awayLowScoring = away.away_low_scoring_rate || 0;
        const boringAlert = (homeLowScoring + awayLowScoring) / 2;

        // 战术僵局指数
        const tacticalStalemate = (home.home_competitive_balance || 0.5) +
                                   (away.away_competitive_balance || 0.5);

        // 历史平局模式 (简化计算)
        const drawPattern = (homeDrawRate > 0.3 && awayDrawRate > 0.3) ? 0.8 :
                           (homeDrawRate > 0.25 || awayDrawRate > 0.25) ? 0.5 : 0.2;

        return {
            combined_draw_probability: parseFloat(combinedDrawProb.toFixed(3)),
            match_stalemate_index: parseFloat(stalemateIndex.toFixed(3)),
            defensive_showdown_score: parseFloat(defensiveShowdown.toFixed(3)),
            boring_match_alert: parseFloat(boringAlert.toFixed(3)),
            tactical_stalemate_index: parseFloat(tacticalStalemate.toFixed(3)),
            historical_draw_pattern: parseFloat(drawPattern.toFixed(3))
        };
    }

    // ========================================================================
    // 辅助方法
    // ========================================================================

    _createDefaultTeamFeatures(prefix) {
        const d = this.config.defaults;
        return {
            [`${prefix}_draw_rate`]: d.drawRate,
            [`${prefix}_draw_tendency`]: d.drawTendency,
            [`${prefix}_defensive_stance`]: d.defensiveStance,
            [`${prefix}_low_scoring_rate`]: d.lowScoringRate,
            [`${prefix}_competitive_balance`]: d.competitiveBalance
        };
    }

    _createEmptyFeatures(reason = 'No valid data') {
        const features = {};
        FEATURE_NAMES.forEach(name => {
            features[name] = 0;
        });
        features._error = reason;
        features._extractedAt = new Date().toISOString();
        features._version = this.version;
        return features;
    }
}

// ============================================================================
// 导出
// ============================================================================

module.exports = {
    DrawPropensityExtractor,
    FEATURE_NAMES,
    DEFAULT_CONFIG
};
