/**
 * EloRatingExtractor - Elo 动态评分提取器
 * ==========================================
 *
 * 实现标准 Elo 算法，动态计算球队实力指纹。
 *
 * 核心公式：
 *   R_new = R_old + K × (Actual - Expected)
 *   Expected = 1 / (1 + 10^((R_opponent - R_self) / 400))
 * @module feature_engine/extractors/EloRatingExtractor
 * @version V176.0.0
 */

'use strict';

// SafeAccess 模块已移除（未使用的死代码）

/**
 * Elo 系统配置
 */
const DEFAULT_CONFIG = {
    // 基础参数
    initialRating: 1500.0,      // 初始评分
    kFactor: 30,                 // K 因子（评分变化权重）
    homeFieldAdvantage: 50,      // 主场优势（加分）

    // 评分范围
    minRating: 800,
    maxRating: 2200,

    // 动态 K 因子（可选）
    enableDynamicK: false,
    dynamicKConfig: {
        newPlayerThreshold: 10,  // 新球队场次阈值
        highRatingThreshold: 1800,
        lowRatingThreshold: 1400
    }
};

/**
 * EloRatingExtractor 类
 */
class EloRatingExtractor {
    /**
     *
     * @param config
     */
    constructor(config = {}) {
        this.config = { ...DEFAULT_CONFIG, ...config };

        // 球队评分存储
        this.teamRatings = new Map();

        // 评分历史（用于追溯）
        this.ratingHistory = new Map();

        // 统计信息
        this.stats = {
            totalUpdates: 0,
            teamsProcessed: 0,
            lastUpdated: null
        };
    }

    /**
     * 获取球队当前 Elo 评分
     * @param teamId
     */
    getTeamRating(teamId) {
        if (!teamId) return this.config.initialRating;
        return this.teamRatings.get(String(teamId)) ?? this.config.initialRating;
    }

    /**
     * 设置球队 Elo 评分
     * @param teamId
     * @param rating
     */
    setTeamRating(teamId, rating) {
        const clampedRating = Math.max(
            this.config.minRating,
            Math.min(this.config.maxRating, rating)
        );
        this.teamRatings.set(String(teamId), clampedRating);

        // 记录历史
        if (!this.ratingHistory.has(String(teamId))) {
            this.ratingHistory.set(String(teamId), []);
        }
        this.ratingHistory.get(String(teamId)).push({
            rating: clampedRating,
            timestamp: Date.now()
        });
    }

    /**
     * 计算预期得分
     * E = 1 / (1 + 10^((R_opp - R_self) / 400))
     * @param ratingSelf
     * @param ratingOpponent
     */
    calculateExpectedScore(ratingSelf, ratingOpponent) {
        const diff = ratingOpponent - ratingSelf;
        return 1 / (1 + Math.pow(10, diff / 400));
    }

    /**
     * 计算动态 K 因子
     * @param teamId
     * @param matchCount
     */
    calculateKFactor(teamId, matchCount) {
        if (!this.config.enableDynamicK) {
            return this.config.kFactor;
        }

        const rating = this.getTeamRating(teamId);
        const { newPlayerThreshold, highRatingThreshold, lowRatingThreshold } = this.config.dynamicKConfig;

        let k = this.config.kFactor;

        // 新球队使用更高 K 因子（更快收敛）
        if (matchCount < newPlayerThreshold) {
            k *= 1.5;
        }

        // 高评分球队更稳定
        if (rating > highRatingThreshold) {
            k *= 0.8;
        }

        // 低评分球队学习更快
        if (rating < lowRatingThreshold) {
            k *= 1.3;
        }

        return k;
    }

    /**
     * 更新单场比赛的 Elo 评分
     * @param {object} match - 比赛数据 { homeTeamId, awayTeamId, homeScore, awayScore, matchDate }
     * @returns {object} Elo 特征
     */
    updateMatchElo(match) {
        const {
            homeTeamId,
            awayTeamId,
            homeScore,
            awayScore,
            matchDate
        } = match;

        // 获取当前评分
        const homeRatingPre = this.getTeamRating(homeTeamId);
        const awayRatingPre = this.getTeamRating(awayTeamId);

        // 应用主场优势
        const homeRatingAdjusted = homeRatingPre + this.config.homeFieldAdvantage;

        // 计算预期得分
        const homeExpected = this.calculateExpectedScore(homeRatingAdjusted, awayRatingPre);
        const awayExpected = 1 - homeExpected;

        // 确定实际得分
        let homeActual, awayActual;
        if (homeScore > awayScore) {
            homeActual = 1;
            awayActual = 0;
        } else if (homeScore < awayScore) {
            homeActual = 0;
            awayActual = 1;
        } else {
            homeActual = 0.5;
            awayActual = 0.5;
        }

        // 计算评分变化
        const homeMatches = this.ratingHistory.get(String(homeTeamId))?.length ?? 0;
        const awayMatches = this.ratingHistory.get(String(awayTeamId))?.length ?? 0;

        const homeK = this.calculateKFactor(homeTeamId, homeMatches);
        const awayK = this.calculateKFactor(awayTeamId, awayMatches);

        const homeChange = homeK * (homeActual - homeExpected);
        const awayChange = awayK * (awayActual - awayExpected);

        // 更新评分
        const homeRatingPost = homeRatingPre + homeChange;
        const awayRatingPost = awayRatingPre + awayChange;

        this.setTeamRating(homeTeamId, homeRatingPost);
        this.setTeamRating(awayTeamId, awayRatingPost);

        // 更新统计
        this.stats.totalUpdates++;
        this.stats.lastUpdated = matchDate || new Date().toISOString();

        // 返回特征
        return {
            home_elo_pre: Math.round(homeRatingPre * 100) / 100,
            away_elo_pre: Math.round(awayRatingPre * 100) / 100,
            home_elo_post: Math.round(homeRatingPost * 100) / 100,
            away_elo_post: Math.round(awayRatingPost * 100) / 100,
            elo_diff: Math.round((homeRatingPre - awayRatingPre) * 100) / 100,
            elo_diff_adjusted: Math.round((homeRatingAdjusted - awayRatingPre) * 100) / 100,
            expected_home_win: Math.round(homeExpected * 1000) / 1000,
            expected_away_win: Math.round(awayExpected * 1000) / 1000,
            home_elo_change: Math.round(homeChange * 100) / 100,
            away_elo_change: Math.round(awayChange * 100) / 100,
            k_factor_home: homeK,
            k_factor_away: awayK,
            _version: 'V176.0.0',
            _extractedAt: new Date().toISOString()
        };
    }

    /**
     * 批量计算历史比赛的 Elo（时序处理）
     * @param {Array} matches - 比赛数组（需按 matchDate 升序排列）
     * @returns {Map} matchId -> eloFeatures
     */
    calculateSequentialElo(matches) {
        const results = new Map();

        // 按日期排序
        const sortedMatches = [...matches].sort((a, b) => {
            const dateA = new Date(a.matchDate || 0);
            const dateB = new Date(b.matchDate || 0);
            return dateA - dateB;
        });

        for (const match of sortedMatches) {
            const eloFeatures = this.updateMatchElo(match);
            results.set(match.matchId, eloFeatures);
        }

        this.stats.teamsProcessed = this.teamRatings.size;

        return results;
    }

    /**
     * 获取所有球队当前评分（导出）
     */
    exportAllRatings() {
        const ratings = {};
        for (const [teamId, rating] of this.teamRatings) {
            ratings[teamId] = rating;
        }
        return ratings;
    }

    /**
     * 导入已有评分（用于增量处理）
     * @param ratings
     */
    importRatings(ratings) {
        if (!ratings || typeof ratings !== 'object') return;

        for (const [teamId, rating] of Object.entries(ratings)) {
            this.teamRatings.set(teamId, rating);
        }
    }

    /**
     * 获取系统统计信息
     */
    getStats() {
        const ratings = Array.from(this.teamRatings.values());
        return {
            ...this.stats,
            teamCount: this.teamRatings.size,
            avgRating: ratings.length > 0 ? ratings.reduce((a, b) => a + b, 0) / ratings.length : this.config.initialRating,
            maxRating: ratings.length > 0 ? Math.max(...ratings) : this.config.initialRating,
            minRating: ratings.length > 0 ? Math.min(...ratings) : this.config.initialRating
        };
    }

    /**
     * 重置系统
     */
    reset() {
        this.teamRatings.clear();
        this.ratingHistory.clear();
        this.stats = {
            totalUpdates: 0,
            teamsProcessed: 0,
            lastUpdated: null
        };
    }
}

/**
 * 从历史比赛数据计算单场比赛的 Elo 特征（无状态版本）
 * @param {Array} historicalMatches - 历史比赛数组
 * @param {object} targetMatch - 目标比赛
 * @param config
 * @returns {object} Elo 特征
 */
function calculateEloFeatures(historicalMatches, targetMatch, config = {}) {
    const extractor = new EloRatingExtractor(config);

    // 过滤目标比赛之前的比赛
    const targetDate = new Date(targetMatch.matchDate);
    const priorMatches = historicalMatches.filter(m => {
        const matchDate = new Date(m.matchDate);
        return matchDate < targetDate;
    });

    // 按时间顺序计算 Elo
    extractor.calculateSequentialElo(priorMatches);

    // 计算目标比赛的 Elo 特征（不更新）
    const homeRatingPre = extractor.getTeamRating(targetMatch.homeTeamId);
    const awayRatingPre = extractor.getTeamRating(targetMatch.awayTeamId);
    const homeRatingAdjusted = homeRatingPre + extractor.config.homeFieldAdvantage;

    const homeExpected = extractor.calculateExpectedScore(homeRatingAdjusted, awayRatingPre);
    const eloDiff = homeRatingPre - awayRatingPre;

    return {
        home_elo_pre: Math.round(homeRatingPre * 100) / 100,
        away_elo_pre: Math.round(awayRatingPre * 100) / 100,
        elo_diff: Math.round(eloDiff * 100) / 100,
        elo_diff_adjusted: Math.round((homeRatingAdjusted - awayRatingPre) * 100) / 100,
        expected_home_win: Math.round(homeExpected * 1000) / 1000,
        expected_away_win: Math.round((1 - homeExpected) * 1000) / 1000,
        home_field_advantage_applied: extractor.config.homeFieldAdvantage,
        _version: 'V176.0.0',
        _extractedAt: new Date().toISOString()
    };
}

/**
 * 创建空 Elo 特征
 */
function createEmptyEloFeatures() {
    return {
        home_elo_pre: 1500,
        away_elo_pre: 1500,
        elo_diff: 0,
        expected_home_win: 0.5,
        expected_away_win: 0.5,
        _error: 'Insufficient historical data',
        _version: 'V176.0.0',
        _extractedAt: new Date().toISOString()
    };
}

module.exports = {
    EloRatingExtractor,
    calculateEloFeatures,
    createEmptyEloFeatures,
    DEFAULT_CONFIG
};
