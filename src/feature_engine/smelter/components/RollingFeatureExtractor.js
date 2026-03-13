/**
 * RollingFeatureExtractor - V4.0 滚动统计特征提取器
 * ==================================================
 *
 * 从数据库历史数据中提取【赛前可用】的滚动统计特征：
 * 1. 近N场进攻效率 (xG, shots, shots_on_target)
 * 2. 近N场控球率均值
 * 3. 近N场胜率/平局率/输球率
 * 4. 休息天数差异
 *
 * V4.0 模块化:
 * - 继承 BaseExtractor
 * - 完全赛前数据，无泄露风险
 * @module feature_engine/smelter/components/RollingExtractor
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
    rollingWindow: 5,

    // 最小样本数（少于此数返回默认值）
    minSamples: 3,

    // 默认值
    defaults: {
        xgAvg: 1.2,
        possessionAvg: 50,
        shotsAvg: 12,
        shotsOnTargetAvg: 4,
        winRate: 0.33,
        drawRate: 0.25,
        lossRate: 0.42,
        restDays: 7
    },

    // 严格模式
    strictMode: false
};

// 特征字段名清单
const FEATURE_NAMES = [
    // 主队滚动进攻特征 (6维)
    'home_last5_xg_avg',
    'home_last5_possession_avg',
    'home_last5_shots_avg',
    'home_last5_shots_on_target_avg',
    'home_last5_shot_conversion',
    'home_last5_strength_index',

    // 客队滚动进攻特征 (6维)
    'away_last5_xg_avg',
    'away_last5_possession_avg',
    'away_last5_shots_avg',
    'away_last5_shots_on_target_avg',
    'away_last5_shot_conversion',
    'away_last5_strength_index',

    // 主队战绩特征 (3维)
    'home_last5_win_rate',
    'home_last5_draw_rate',
    'home_last5_loss_rate',

    // 客队战绩特征 (3维)
    'away_last5_win_rate',
    'away_last5_draw_rate',
    'away_last5_loss_rate',

    // 对比特征 (3维)
    'rest_days_diff',
    'form_momentum_diff',
    'xg_diff_rolling'
];

// ============================================================================
// RollingFeatureExtractor 类
// ============================================================================

class RollingFeatureExtractor extends BaseExtractor {
    /**
     * @param {object} options - 配置选项
     * @param {object} options.dbPool - 数据库连接池（必需）
     * @param {object} options.config - 提取器配置
     */
    constructor(options = {}) {
        super({
            name: 'RollingFeatureExtractor',
            version: 'V4.0.0-MODULAR',
            requiredFields: [],
            config: { ...DEFAULT_CONFIG, ...(options.config || {}) }
        });

        this.dbPool = options.dbPool || null;
        this.cache = new Map(); // 球队历史数据缓存
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
                throw new Error('RollingFeatureExtractor 需要数据库连接池');
            }

            const { home_team, away_team, match_date, match_id } = rawData;

            if (!home_team || !away_team || !match_date) {
                return this._createEmptyFeatures('Missing required fields');
            }

            // 提取主队滚动特征
            const homeFeatures = await this._extractTeamRollingFeatures(
                home_team, match_date, 'home'
            );

            // 提取客队滚动特征
            const awayFeatures = await this._extractTeamRollingFeatures(
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
                _source: 'RollingStatistics'
            };

            this.stats.successfulCalls++;
            this._updateAvgExecutionTime(Date.now() - startTime);

            return features;

        } catch (error) {
            this.stats.failedCalls++;
            this.logger.error('滚动特征提取失败', {
                match_id: rawData.match_id,
                error: error.message
            });
            return this._createEmptyFeatures(error.message);
        }
    }

    /**
     * 提取球队滚动特征（核心逻辑）
     * @private
     * @param {string} teamName - 球队名
     * @param {string} matchDate - 比赛日期
     * @param {string} prefix - 特征前缀 (home/away)
     * @returns {Promise<object>}
     */
    async _extractTeamRollingFeatures(teamName, matchDate, prefix) {
        const window = this.config.rollingWindow;
        const minSamples = this.config.minSamples;

        try {
            // 查询球队历史比赛（该场比赛之前）
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
                    l.tactical_features->>'home_shots' as home_shots,
                    l.tactical_features->>'away_shots' as away_shots,
                    l.tactical_features->>'home_shots_on_target' as home_shots_on_target,
                    l.tactical_features->>'away_shots_on_target' as away_shots_on_target
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
                this.logger.debug(`球队 ${teamName} 历史数据不足 (${matches.length}/${minSamples})，使用默认值`);
                return this._createDefaultTeamFeatures(prefix);
            }

            // 计算滚动统计
            const stats = this._calculateRollingStats(matches, teamName);

            // 计算战绩
            const record = this._calculateWinDrawLoss(matches, teamName);

            // 计算休息天数
            const restDays = this._calculateRestDays(matches, matchDate);

            return {
                [`${prefix}_last5_xg_avg`]: stats.xgAvg,
                [`${prefix}_last5_possession_avg`]: stats.possessionAvg,
                [`${prefix}_last5_shots_avg`]: stats.shotsAvg,
                [`${prefix}_last5_shots_on_target_avg`]: stats.shotsOnTargetAvg,
                [`${prefix}_last5_shot_conversion`]: stats.shotConversion,
                [`${prefix}_last5_strength_index`]: stats.strengthIndex,
                [`${prefix}_last5_win_rate`]: record.winRate,
                [`${prefix}_last5_draw_rate`]: record.drawRate,
                [`${prefix}_last5_loss_rate`]: record.lossRate,
                [`${prefix}_rest_days`]: restDays
            };

        } catch (error) {
            this.logger.error(`提取 ${teamName} 滚动特征失败`, { error: error.message });
            return this._createDefaultTeamFeatures(prefix);
        }
    }

    /**
     * 计算滚动统计数据
     * @private
     */
    _calculateRollingStats(matches, teamName) {
        let xgSum = 0, possessionSum = 0, shotsSum = 0, shotsOnTargetSum = 0;
        let count = 0;

        for (const match of matches.slice(0, this.config.rollingWindow)) {
            const isHome = match.home_team === teamName;

            // 使用安全的数值解析
            const xg = parseFloat(isHome ? match.home_xg : match.away_xg) || 0;
            const possession = parseFloat(isHome ? match.home_possession : match.away_possession) || 50;
            const shots = parseInt(isHome ? match.home_shots : match.away_shots) || 0;
            const shotsOnTarget = parseInt(isHome ? match.home_shots_on_target : match.away_shots_on_target) || 0;

            xgSum += xg;
            possessionSum += possession;
            shotsSum += shots;
            shotsOnTargetSum += shotsOnTarget;
            count++;
        }

        if (count === 0) {
            return {
                xgAvg: this.config.defaults.xgAvg,
                possessionAvg: this.config.defaults.possessionAvg,
                shotsAvg: this.config.defaults.shotsAvg,
                shotsOnTargetAvg: this.config.defaults.shotsOnTargetAvg,
                shotConversion: 0.33,
                strengthIndex: 50
            };
        }

        const xgAvg = xgSum / count;
        const possessionAvg = possessionSum / count;
        const shotsAvg = shotsSum / count;
        const shotsOnTargetAvg = shotsOnTargetSum / count;
        const shotConversion = shotsAvg > 0 ? shotsOnTargetAvg / shotsAvg : 0.33;
        const strengthIndex = (xgAvg * 20) + (possessionAvg * 0.5) + (shotConversion * 30);

        return {
            xgAvg: parseFloat(xgAvg.toFixed(2)),
            possessionAvg: parseFloat(possessionAvg.toFixed(1)),
            shotsAvg: parseFloat(shotsAvg.toFixed(1)),
            shotsOnTargetAvg: parseFloat(shotsOnTargetAvg.toFixed(1)),
            shotConversion: parseFloat(shotConversion.toFixed(3)),
            strengthIndex: parseFloat(strengthIndex.toFixed(1))
        };
    }

    /**
     * 计算胜平负战绩
     * @private
     */
    _calculateWinDrawLoss(matches, teamName) {
        let wins = 0, draws = 0, losses = 0;
        const window = Math.min(matches.length, this.config.rollingWindow);

        for (const match of matches.slice(0, window)) {
            const isHome = match.home_team === teamName;
            const homeScore = parseInt(match.home_score);
            const awayScore = parseInt(match.away_score);

            if (isHome) {
                if (homeScore > awayScore) wins++;
                else if (homeScore === awayScore) draws++;
                else losses++;
            } else {
                if (awayScore > homeScore) wins++;
                else if (awayScore === homeScore) draws++;
                else losses++;
            }
        }

        const total = wins + draws + losses;
        if (total === 0) {
            return {
                winRate: this.config.defaults.winRate,
                drawRate: this.config.defaults.drawRate,
                lossRate: this.config.defaults.lossRate
            };
        }

        return {
            winRate: parseFloat((wins / total).toFixed(3)),
            drawRate: parseFloat((draws / total).toFixed(3)),
            lossRate: parseFloat((losses / total).toFixed(3))
        };
    }

    /**
     * 计算休息天数
     * @private
     */
    _calculateRestDays(matches, currentDate) {
        if (matches.length === 0) {
            return this.config.defaults.restDays;
        }

        const lastMatch = matches[0];
        const lastDate = new Date(lastMatch.match_date);
        const current = new Date(currentDate);
        const diffTime = Math.abs(current - lastDate);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

        return Math.min(diffDays, 14); // 最多14天
    }

    /**
     * 计算对比特征
     * @private
     */
    _calculateComparisonFeatures(home, away) {
        const homeRest = home.home_rest_days || 7;
        const awayRest = away.away_rest_days || 7;

        // 休息天数差（主队 - 客队，正值表示主队休息更多）
        const restDaysDiff = homeRest - awayRest;

        // 势头差（主队胜率 - 客队胜率）
        const formMomentumDiff = (home.home_last5_win_rate || 0.33) - (away.away_last5_win_rate || 0.33);

        // 滚动xG差
        const xgDiffRolling = (home.home_last5_xg_avg || 1.2) - (away.away_last5_xg_avg || 1.2);

        return {
            rest_days_diff: restDaysDiff,
            form_momentum_diff: parseFloat(formMomentumDiff.toFixed(3)),
            xg_diff_rolling: parseFloat(xgDiffRolling.toFixed(2))
        };
    }

    // ========================================================================
    // 辅助方法
    // ========================================================================

    _createDefaultTeamFeatures(prefix) {
        const d = this.config.defaults;
        return {
            [`${prefix}_last5_xg_avg`]: d.xgAvg,
            [`${prefix}_last5_possession_avg`]: d.possessionAvg,
            [`${prefix}_last5_shots_avg`]: d.shotsAvg,
            [`${prefix}_last5_shots_on_target_avg`]: d.shotsOnTargetAvg,
            [`${prefix}_last5_shot_conversion`]: 0.33,
            [`${prefix}_last5_strength_index`]: 50,
            [`${prefix}_last5_win_rate`]: d.winRate,
            [`${prefix}_last5_draw_rate`]: d.drawRate,
            [`${prefix}_last5_loss_rate`]: d.lossRate,
            [`${prefix}_rest_days`]: d.restDays
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
    RollingFeatureExtractor,
    FEATURE_NAMES,
    DEFAULT_CONFIG
};
