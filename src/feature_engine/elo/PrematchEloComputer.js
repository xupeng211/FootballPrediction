/**
 * PrematchEloComputer — 纯内存赛前 Elo 计算器
 * ============================================
 *
 * 基于历史比赛数据，在不写 DB 的前提下计算每场比赛的赛前 Elo。
 *
 * 设计原则：
 *   1. PREMATCH-ONLY：目标比赛的 Elo 仅使用 kickoff 之前已完成的比赛。
 *   2. NO FUTURE LEAKAGE：严格按 match_date 排序，未来比赛不会影响当前 Elo。
 *   3. NO TARGET-MATCH LEAKAGE：目标比赛自身结果不参与其赛前 Elo 计算。
 *   4. SAME-TIME STABLE：同日比赛按 match_id 稳定排序，不会互相污染。
 *   5. FALLBACK METADATA：无历史球队输出 `_is_default: true`。
 *   6. NO DB WRITE：纯内存计算，不写 team_elo_ratings 或任何业务表。
 *
 * 使用方式：
 *   const computer = new PrematchEloComputer({ kFactor: 30 });
 *   const eloMap = computer.computeAll(matches);
 *   // eloMap.get("match_123") => { home_elo_pre, away_elo_pre, ... }
 *
 * lifecycle: permanent
 * scope: prematch Elo signal computation
 * owner: GOLD-AUDIT-2AH
 *
 * @module feature_engine/elo/PrematchEloComputer
 * @version V1.0.0
 */

'use strict';

const { EloRatingExtractor } = require('../extractors/EloRatingExtractor');

const DEFAULT_CONFIG = {
    initialRating: 1500.0,
    kFactor: 30,
    homeFieldAdvantage: 50,
    minRating: 800,
    maxRating: 2200,
};

/**
 * 赛前 Elo 计算器。
 *
 * 接收比赛数组（需包含 matchId, homeTeam, awayTeam, homeScore, awayScore, matchDate），
 * 按时间顺序处理，为每场比赛产出其 kickoff 时刻的赛前 Elo。
 */
class PrematchEloComputer {
    /**
     * @param {object} [config] — Elo 参数配置
     */
    constructor(config = {}) {
        this.config = { ...DEFAULT_CONFIG, ...config };
        this.extractor = new EloRatingExtractor(this.config);
    }

    /**
     * 验证比赛数据是否包含必需字段。
     * @param {object} match
     * @returns {boolean}
     */
    _isValidMatch(match) {
        return !!(
            match &&
            match.matchId &&
            match.homeTeam &&
            match.awayTeam &&
            match.matchDate
        );
    }

    /**
     * 按 match_date ASC、match_id ASC 排序，保证时序确定性。
     * @param {Array} matches
     * @returns {Array}
     */
    _sortChronologically(matches) {
        return [...matches].sort((a, b) => {
            const dateA = new Date(a.matchDate || 0);
            const dateB = new Date(b.matchDate || 0);
            if (dateA.getTime() !== dateB.getTime()) {
                return dateA - dateB;
            }
            // 同日比赛按 match_id 稳定排序
            return String(a.matchId).localeCompare(String(b.matchId));
        });
    }

    /**
     * 标记赛前 Elo 是否为默认值（无历史数据）。
     *
     * 判断标准：在目标比赛 kickoff 之前，该队是否已经参加过至少一场
     * 已处理的比赛（即有历史评分记录）。
     *
     * @param {string} teamName
     * @param {Map} ratingHistory — teamName → { firstMatchDate }
     * @param {string} targetMatchDate
     * @returns {boolean}
     */
    _isTeamDefault(teamName, ratingHistory, targetMatchDate) {
        // 检查球队当前评分是否已经偏离初始值（如通过 importRatings 导入）
        const currentRating = this.extractor.getTeamRating(teamName);
        if (currentRating !== this.config.initialRating) {
            return false;
        }
        const firstSeen = ratingHistory.get(teamName);
        if (!firstSeen) return true;
        // 如果球队历史首场比赛日期 ≥ 目标比赛日期，说明该队在
        // 本场比赛之前没有历史数据
        return new Date(firstSeen) >= new Date(targetMatchDate);
    }

    /**
     * 批量计算所有比赛的赛前 Elo。
     *
     * 算法：
     *   1. 按 match_date ASC, match_id ASC 排序
     *   2. 遍历排序后的比赛
     *   3. 对每场比赛，读取**当前** Elo 状态作为赛前 Elo 并记录
     *   4. 用该场比赛结果更新 Elo 状态（供后续比赛使用）
     *
     * 这样保证第 N 场的赛前 Elo 只使用了第 1..N-1 场的结果。
     *
     * @param {Array} matches — 比赛数组
     * @returns {Map<string, object>} matchId → prematchEloFeatures
     */
    computeAll(matches) {
        if (!Array.isArray(matches) || matches.length === 0) {
            return new Map();
        }

        const results = new Map();
        const ratingHistory = new Map(); // teamName → firstMatchDate
        const sorted = this._sortChronologically(matches);
        const eligible = sorted.filter(m => this._isValidMatch(m));

        for (const match of eligible) {
            const matchDate = match.matchDate;

            // 记录目标比赛的赛前 Elo
            const homeRatingPre = this.extractor.getTeamRating(match.homeTeam);
            const awayRatingPre = this.extractor.getTeamRating(match.awayTeam);
            const homeRatingAdjusted = homeRatingPre + this.config.homeFieldAdvantage;

            const homeExpected = this.extractor.calculateExpectedScore(
                homeRatingAdjusted, awayRatingPre
            );
            const awayExpected = 1 - homeExpected;

            const isHomeDefault = this._isTeamDefault(
                match.homeTeam, ratingHistory, matchDate
            );
            const isAwayDefault = this._isTeamDefault(
                match.awayTeam, ratingHistory, matchDate
            );

            results.set(match.matchId, {
                home_elo_pre: Math.round(homeRatingPre * 100) / 100,
                away_elo_pre: Math.round(awayRatingPre * 100) / 100,
                elo_diff: Math.round((homeRatingPre - awayRatingPre) * 100) / 100,
                elo_diff_adjusted: Math.round(
                    (homeRatingAdjusted - awayRatingPre) * 100
                ) / 100,
                expected_home_win: Math.round(homeExpected * 1000) / 1000,
                expected_away_win: Math.round(awayExpected * 1000) / 1000,
                home_field_advantage_applied: this.config.homeFieldAdvantage,
                _is_default: isHomeDefault && isAwayDefault,
                _home_default: isHomeDefault,
                _away_default: isAwayDefault,
                _version: 'PrematchEloComputer-V1.0.0',
                _computed_at: new Date().toISOString(),
            });

            // 记录每支球队首次出现日期
            if (!ratingHistory.has(match.homeTeam)) {
                ratingHistory.set(match.homeTeam, matchDate);
            }
            if (!ratingHistory.has(match.awayTeam)) {
                ratingHistory.set(match.awayTeam, matchDate);
            }

            // 用本场比赛结果更新 Elo 状态，供后续比赛使用
            this.extractor.updateMatchElo({
                homeTeamId: match.homeTeam,
                awayTeamId: match.awayTeam,
                homeScore: match.homeScore ?? null,
                awayScore: match.awayScore ?? null,
                matchDate,
            });
        }

        return results;
    }

    /**
     * 计算单场比赛的赛前 Elo。
     *
     * 从历史比赛数据中筛选 kickoff 之前的比赛，
     * 按时间顺序计算 Elo，然后返回目标比赛的赛前 Elo。
     *
     * @param {Array} historicalMatches — 所有历史比赛
     * @param {object} targetMatch — 目标比赛
     * @returns {object} prematchEloFeatures
     */
    computeOne(historicalMatches, targetMatch) {
        if (!this._isValidMatch(targetMatch)) {
            return {
                home_elo_pre: this.config.initialRating,
                away_elo_pre: this.config.initialRating,
                elo_diff: 0,
                expected_home_win: 0.5,
                expected_away_win: 0.5,
                _is_default: true,
                _error: 'Invalid target match',
                _version: 'PrematchEloComputer-V1.0.0',
            };
        }

        const targetDate = new Date(targetMatch.matchDate);
        const priorMatches = (historicalMatches || [])
            .filter(m => this._isValidMatch(m))
            .filter(m => new Date(m.matchDate) < targetDate);

        // 计算历史 Elo
        const tempExtractor = new EloRatingExtractor(this.config);
        const sorted = this._sortChronologically(priorMatches);
        for (const match of sorted) {
            tempExtractor.updateMatchElo({
                homeTeamId: match.homeTeam,
                awayTeamId: match.awayTeam,
                homeScore: match.homeScore ?? null,
                awayScore: match.awayScore ?? null,
                matchDate: match.matchDate,
            });
        }

        // 目标比赛赛前评分
        const homeRatingPre = tempExtractor.getTeamRating(targetMatch.homeTeam);
        const awayRatingPre = tempExtractor.getTeamRating(targetMatch.awayTeam);
        const homeRatingAdjusted = homeRatingPre + this.config.homeFieldAdvantage;
        const homeExpected = tempExtractor.calculateExpectedScore(
            homeRatingAdjusted, awayRatingPre
        );

        const isHomeDefault = homeRatingPre === this.config.initialRating;
        const isAwayDefault = awayRatingPre === this.config.initialRating;

        return {
            home_elo_pre: Math.round(homeRatingPre * 100) / 100,
            away_elo_pre: Math.round(awayRatingPre * 100) / 100,
            elo_diff: Math.round((homeRatingPre - awayRatingPre) * 100) / 100,
            elo_diff_adjusted: Math.round(
                (homeRatingAdjusted - awayRatingPre) * 100
            ) / 100,
            expected_home_win: Math.round(homeExpected * 1000) / 1000,
            expected_away_win: Math.round((1 - homeExpected) * 1000) / 1000,
            home_field_advantage_applied: this.config.homeFieldAdvantage,
            _is_default: isHomeDefault && isAwayDefault,
            _home_default: isHomeDefault,
            _away_default: isAwayDefault,
            _version: 'PrematchEloComputer-V1.0.0',
            _computed_at: new Date().toISOString(),
        };
    }

    /**
     * 导出当前 Elo 状态（用于增量处理）。
     * @returns {object} teamName → rating
     */
    exportRatings() {
        return this.extractor.exportAllRatings();
    }

    /**
     * 导入已有评分（用于增量处理）。
     * @param {object} ratings — teamName → rating
     */
    importRatings(ratings) {
        this.extractor.importRatings(ratings);
    }

    /**
     * 重置内部状态。
     */
    reset() {
        this.extractor.reset();
    }
}

module.exports = { PrematchEloComputer, DEFAULT_CONFIG };
