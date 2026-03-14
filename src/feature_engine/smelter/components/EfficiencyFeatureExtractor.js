/**
 * EfficiencyFeatureExtractor - V5.2 效率特征提取器
 * =================================================
 *
 * 计算进攻/防守效率指标，识别：
 * - "高效杀手": 高转化率，低射门数
 * - "浪射王": 低转化率，高射门数
 *
 * 效率指标 = shots_on_target / shots_total
 * 终极效率 = goals / xG
 *
 * V5.2 模块化:
 * - 继承 BaseExtractor
 * - 完全赛前数据，无泄露风险
 * @module feature_engine/smelter/components/EfficiencyExtractor
 * @version V5.2.0-HOME-FORTRESS
 * @since 2026-03-14
 */

'use strict';

const { BaseExtractor } = require('./BaseExtractor');

// ============================================================================
// 配置常量
// ============================================================================

const DEFAULT_CONFIG = {
    // 滚动窗口大小
    rollingWindow: 5,

    // 最小样本数
    minSamples: 3,

    // 默认值
    defaults: {
        shotConversion: 0.33,      // 射门转化率 33%
        bigChanceConversion: 0.25, // 绝佳机会转化率 25%
        finishingEfficiency: 1.0,  // 终结效率 (goals/xG)
        defensiveSolidity: 1.0,    // 防守稳固性
        pressEfficiency: 0.5       // 压迫效率
    },

    // 严格模式
    strictMode: false
};

// 特征字段名清单
const FEATURE_NAMES = [
    // 主队效率特征 (5维)
    'home_shot_conversion',
    'home_big_chance_conversion',
    'home_finishing_efficiency',
    'home_defensive_solidity',
    'home_press_efficiency',

    // 客队效率特征 (5维)
    'away_shot_conversion',
    'away_big_chance_conversion',
    'away_finishing_efficiency',
    'away_defensive_solidity',
    'away_press_efficiency',

    // 对比效率特征 (4维)
    'shot_conversion_diff',
    'finishing_efficiency_diff',
    'offensive_quality_index',
    'defensive_quality_index'
];

// ============================================================================
// EfficiencyFeatureExtractor 类
// ============================================================================

class EfficiencyFeatureExtractor extends BaseExtractor {
    /**
     * @param {object} options - 配置选项
     * @param {object} options.dbPool - 数据库连接池（必需）
     * @param {object} options.config - 提取器配置
     */
    constructor(options = {}) {
        super({
            name: 'EfficiencyFeatureExtractor',
            version: 'V5.2.0-HOME-FORTRESS',
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
                throw new Error('EfficiencyFeatureExtractor 需要数据库连接池');
            }

            const { home_team, away_team, match_date, match_id } = rawData;

            if (!home_team || !away_team || !match_date) {
                return this._createEmptyFeatures('Missing required fields');
            }

            // 提取主队效率特征
            const homeFeatures = await this._extractTeamEfficiencyFeatures(
                home_team, match_date, 'home'
            );

            // 提取客队效率特征
            const awayFeatures = await this._extractTeamEfficiencyFeatures(
                away_team, match_date, 'away'
            );

            // 计算对比特征
            const comparisonFeatures = this._calculateComparisonFeatures(
                homeFeatures, awayFeatures
            );

            const features = {
                ...homeFeatures,
                ...awayFeatures,
                ...comparisonFeatures,
                _extractedAt: new Date().toISOString(),
                _version: this.version,
                _source: 'EfficiencyMetrics'
            };

            this.stats.successfulCalls++;
            this._updateAvgExecutionTime(Date.now() - startTime);

            return features;

        } catch (error) {
            this.stats.failedCalls++;
            this.logger.error('效率特征提取失败', {
                match_id: rawData.match_id,
                error: error.message
            });
            return this._createEmptyFeatures(error.message);
        }
    }

    /**
     * 提取球队效率特征（核心逻辑）
     * @private
     * @param {string} teamName - 球队名
     * @param {string} matchDate - 比赛日期
     * @param {string} prefix - 特征前缀 (home/away)
     * @returns {Promise<object>}
     */
    async _extractTeamEfficiencyFeatures(teamName, matchDate, prefix) {
        const window = this.config.rollingWindow;
        const minSamples = this.config.minSamples;

        try {
            // 查询球队历史比赛效率数据
            const query = `
                SELECT 
                    m.match_id,
                    m.home_team,
                    m.away_team,
                    m.home_score,
                    m.away_score,
                    m.match_date,
                    l.tactical_features->>'home_shots' as home_shots,
                    l.tactical_features->>'away_shots' as away_shots,
                    l.tactical_features->>'home_shots_on_target' as home_shots_on_target,
                    l.tactical_features->>'away_shots_on_target' as away_shots_on_target,
                    l.tactical_features->>'home_xg' as home_xg,
                    l.tactical_features->>'away_xg' as away_xg,
                    l.tactical_features->>'home_big_chances' as home_big_chances,
                    l.tactical_features->>'away_big_chances' as away_big_chances,
                    l.tactical_features->>'home_possession' as home_possession,
                    l.tactical_features->>'away_possession' as away_possession,
                    l.tactical_features->>'home_ppda' as home_ppda,
                    l.tactical_features->>'away_ppda' as away_ppda
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
                this.logger.debug(`球队 ${teamName} 效率数据不足 (${matches.length}/${minSamples})，使用默认值`);
                return this._createDefaultTeamFeatures(prefix);
            }

            // 计算各项效率指标
            const shotConversion = this._calculateShotConversion(matches, teamName);
            const bigChanceConversion = this._calculateBigChanceConversion(matches, teamName);
            const finishingEfficiency = this._calculateFinishingEfficiency(matches, teamName);
            const defensiveSolidity = this._calculateDefensiveSolidity(matches, teamName);
            const pressEfficiency = this._calculatePressEfficiency(matches, teamName);

            return {
                [`${prefix}_shot_conversion`]: shotConversion,
                [`${prefix}_big_chance_conversion`]: bigChanceConversion,
                [`${prefix}_finishing_efficiency`]: finishingEfficiency,
                [`${prefix}_defensive_solidity`]: defensiveSolidity,
                [`${prefix}_press_efficiency`]: pressEfficiency
            };

        } catch (error) {
            this.logger.error(`提取 ${teamName} 效率特征失败`, { error: error.message });
            return this._createDefaultTeamFeatures(prefix);
        }
    }

    // ========================================================================
    // 效率指标计算方法
    // ========================================================================

    /**
     * 计算射门转化率
     * shot_conversion = shots_on_target / shots_total
     * @private
     */
    _calculateShotConversion(matches, teamName) {
        let shotsOnTargetSum = 0;
        let shotsTotalSum = 0;
        let count = 0;

        for (const match of matches.slice(0, this.config.rollingWindow)) {
            const isHome = match.home_team === teamName;

            const shots = parseInt(isHome ? match.home_shots : match.away_shots) || 0;
            const shotsOnTarget = parseInt(isHome ? match.home_shots_on_target : match.away_shots_on_target) || 0;

            if (shots > 0) {
                shotsOnTargetSum += shotsOnTarget;
                shotsTotalSum += shots;
                count++;
            }
        }

        if (count === 0 || shotsTotalSum === 0) {
            return this.config.defaults.shotConversion;
        }

        return parseFloat((shotsOnTargetSum / shotsTotalSum).toFixed(3));
    }

    /**
     * 计算绝佳机会转化率
     * big_chance_conversion = goals_from_big_chances / big_chances
     * @private
     */
    _calculateBigChanceConversion(matches, teamName) {
        let bigChancesSum = 0;
        let goalsSum = 0;
        let count = 0;

        for (const match of matches.slice(0, this.config.rollingWindow)) {
            const isHome = match.home_team === teamName;

            const bigChances = parseInt(isHome ? match.home_big_chances : match.away_big_chances) || 0;
            const goals = parseInt(isHome ? match.home_score : match.away_score) || 0;

            bigChancesSum += bigChances;
            goalsSum += goals;
            count++;
        }

        // 简化：使用进球数 / (big_chances + 2) 作为近似
        if (count === 0 || bigChancesSum === 0) {
            return this.config.defaults.bigChanceConversion;
        }

        // 估算：大约50%进球来自绝佳机会
        const estimatedGoalsFromBigChances = goalsSum * 0.5;
        const conversion = Math.min(estimatedGoalsFromBigChances / bigChancesSum, 1.0);

        return parseFloat(conversion.toFixed(3));
    }

    /**
     * 计算终结效率 (Finishing Efficiency)
     * finishing_efficiency = actual_goals / expected_goals
     * > 1.0: 超常发挥，把握机会能力强
     * < 1.0: 浪费机会，临门一脚欠佳
     * @private
     */
    _calculateFinishingEfficiency(matches, teamName) {
        let goalsSum = 0;
        let xgSum = 0;
        let count = 0;

        for (const match of matches.slice(0, this.config.rollingWindow)) {
            const isHome = match.home_team === teamName;

            const goals = parseInt(isHome ? match.home_score : match.away_score) || 0;
            const xg = parseFloat(isHome ? match.home_xg : match.away_xg) || 0;

            if (xg > 0) {
                goalsSum += goals;
                xgSum += xg;
                count++;
            }
        }

        if (count === 0 || xgSum === 0) {
            return this.config.defaults.finishingEfficiency;
        }

        const efficiency = goalsSum / xgSum;
        // 限制在合理范围 0.3 - 2.0
        const clamped = Math.max(0.3, Math.min(2.0, efficiency));

        return parseFloat(clamped.toFixed(3));
    }

    /**
     * 计算防守稳固性
     * defensive_solidity = expected_conceded / actual_conceded
     * > 1.0: 防守优于预期
     * < 1.0: 防守差于预期
     * @private
     */
    _calculateDefensiveSolidity(matches, teamName) {
        let concededSum = 0;
        let xgAgainstSum = 0;
        let count = 0;

        for (const match of matches.slice(0, this.config.rollingWindow)) {
            const isHome = match.home_team === teamName;

            // 丢球数 = 对方进球数
            const conceded = parseInt(isHome ? match.away_score : match.home_score) || 0;
            // 预期丢球 = 对方xG
            const xgAgainst = parseFloat(isHome ? match.away_xg : match.home_xg) || 0;

            concededSum += conceded;
            xgAgainstSum += xgAgainst;
            count++;
        }

        if (count === 0 || concededSum === 0) {
            return this.config.defaults.defensiveSolidity;
        }

        // solidity = xG_against / actual_conceded (越高越好)
        const solidity = xgAgainstSum / concededSum;
        // 限制在合理范围 0.5 - 2.0
        const clamped = Math.max(0.5, Math.min(2.0, solidity));

        return parseFloat(clamped.toFixed(3));
    }

    /**
     * 计算压迫效率 (Pressing Efficiency)
     * 基于 PPDA (Passes Per Defensive Action) 计算
     * PPDA越低 = 压迫越积极
     * @private
     */
    _calculatePressEfficiency(matches, teamName) {
        let ppdaSum = 0;
        let count = 0;

        for (const match of matches.slice(0, this.config.rollingWindow)) {
            const isHome = match.home_team === teamName;

            const ppda = parseFloat(isHome ? match.home_ppda : match.away_ppda) || 0;

            if (ppda > 0) {
                ppdaSum += ppda;
                count++;
            }
        }

        if (count === 0) {
            return this.config.defaults.pressEfficiency;
        }

        const avgPPDA = ppdaSum / count;
        // 将PPDA转换为效率指数 (0-1)
        // PPDA=5 (高压) -> 1.0, PPDA=20 (低压) -> 0.0
        const efficiency = Math.max(0, Math.min(1, (25 - avgPPDA) / 20));

        return parseFloat(efficiency.toFixed(3));
    }

    /**
     * 计算对比特征
     * @private
     */
    _calculateComparisonFeatures(home, away) {
        // 射门转化率差
        const homeConversion = home.home_shot_conversion || 0.33;
        const awayConversion = away.away_shot_conversion || 0.33;
        const conversionDiff = homeConversion - awayConversion;

        // 终结效率差
        const homeFinishing = home.home_finishing_efficiency || 1.0;
        const awayFinishing = away.away_finishing_efficiency || 1.0;
        const finishingDiff = homeFinishing - awayFinishing;

        // 进攻质量指数 (射门转化 + 终结效率)
        const offensiveQuality = homeConversion * 0.5 + homeFinishing * 0.5;

        // 防守质量指数 (防守稳固性)
        const defensiveQuality = home.home_defensive_solidity || 1.0;

        return {
            shot_conversion_diff: parseFloat(conversionDiff.toFixed(3)),
            finishing_efficiency_diff: parseFloat(finishingDiff.toFixed(3)),
            offensive_quality_index: parseFloat(offensiveQuality.toFixed(3)),
            defensive_quality_index: parseFloat(defensiveQuality.toFixed(3))
        };
    }

    // ========================================================================
    // 辅助方法
    // ========================================================================

    _createDefaultTeamFeatures(prefix) {
        const d = this.config.defaults;
        return {
            [`${prefix}_shot_conversion`]: d.shotConversion,
            [`${prefix}_big_chance_conversion`]: d.bigChanceConversion,
            [`${prefix}_finishing_efficiency`]: d.finishingEfficiency,
            [`${prefix}_defensive_solidity`]: d.defensiveSolidity,
            [`${prefix}_press_efficiency`]: d.pressEfficiency
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
    EfficiencyFeatureExtractor,
    FEATURE_NAMES,
    DEFAULT_CONFIG
};
