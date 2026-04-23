/**
 * EloAutoUpdater - 自动化 Elo 更新引擎
 * =========================================
 *
 * 监控新完赛的比赛，自动触发 Elo 评分更新
 * 支持增量更新，避免全量重算
 *
 * 集成点:
 * 1. FeatureSmelter 处理完赛后数据后调用
 * 2. 定时任务定期扫描
 * 3. 手动触发
 * @module feature_engine/elo/EloAutoUpdater
 * @version V1.0.0
 * @created 2026-03-11
 */

'use strict';

const { Pool } = require('pg');
const { EloRatingExtractor } = require('../extractors/EloRatingExtractor');

// ============================================================================
// 配置
// ============================================================================

const DEFAULT_CONFIG = {
    db: {
        host: process.env.DB_HOST || '127.0.0.1',
        port: parseInt(process.env.DB_PORT || '5432'),
        database: process.env.DB_NAME || 'football_db',
        user: process.env.DB_USER || 'football_user',
        password: process.env.DB_PASSWORD || ''
    },
    elo: {
        initialRating: 1500,
        kFactor: 20,
        homeFieldAdvantage: 50
    }
};

// ============================================================================
// EloAutoUpdater 类
// ============================================================================

/**
 *
 */
class EloAutoUpdater {
    /**
     *
     * @param config
     */
    constructor(config = {}) {
        this.config = { ...DEFAULT_CONFIG, ...config };
        this.pool = null;
        this.eloExtractor = null;
        this.stats = {
            matchesProcessed: 0,
            teamsUpdated: 0,
            lastRun: null
        };
    }

    /**
     * 初始化连接
     */
    async initialize() {
        this.pool = new Pool({ ...this.config.db, max: 5 });
        this.eloExtractor = new EloRatingExtractor(this.config.elo);

        // 加载已有 Elo 评分以保持连续性
        await this._loadExistingRatings();

        return this;
    }

    /**
     * 加载已有 Elo 评分
     * @private
     */
    async _loadExistingRatings() {
        const client = await this.pool.connect();
        try {
            const result = await client.query(`
                SELECT team_name, elo_rating, matches_played
                FROM team_elo_ratings
            `);

            for (const row of result.rows) {
                this.eloExtractor.setTeamRating(row.team_name, parseFloat(row.elo_rating));
                // 恢复历史记录
                const count = row.matches_played || 0;
                for (let i = 0; i < count; i++) {
                    if (!this.eloExtractor.ratingHistory.has(row.team_name)) {
                        this.eloExtractor.ratingHistory.set(row.team_name, []);
                    }
                    this.eloExtractor.ratingHistory.get(row.team_name).push({
                        rating: parseFloat(row.elo_rating),
                        timestamp: Date.now()
                    });
                }
            }

            console.log(`[EloAutoUpdater] 加载 ${result.rows.length} 支球队的已有评分`);
        } finally {
            client.release();
        }
    }

    /**
     * 增量更新 - 只处理缺失 Elo 的已完赛比赛
     */
    async incrementalUpdate() {
        const client = await this.pool.connect();
        try {
            // 查找缺失 Elo 的已完赛比赛
            const query = `
                SELECT
                    m.match_id,
                    m.home_team,
                    m.away_team,
                    m.home_score,
                    m.away_score,
                    m.match_date,
                    m.league_name
                FROM matches m
                LEFT JOIN l3_features l ON m.match_id = l.match_id
                WHERE m.status = 'finished'
                  AND m.home_score IS NOT NULL
                  AND m.away_score IS NOT NULL
                  AND (l.elo_features IS NULL OR l.elo_features = '{}'::jsonb)
                ORDER BY m.match_date ASC
            `;

            const result = await client.query(query);
            const matches = result.rows;

            if (matches.length === 0) {
                return { processed: 0, message: '所有比赛都已计算 Elo' };
            }

            console.log(`[EloAutoUpdater] 发现 ${matches.length} 场比赛需要更新 Elo`);

            return await this._processMatches(matches);
        } finally {
            client.release();
        }
    }

    /**
     * 处理单场比赛 - 用于实时触发
     * @param {string} matchId - 比赛 ID
     */
    async processMatch(matchId) {
        const client = await this.pool.connect();
        try {
            const query = `
                SELECT
                    m.match_id,
                    m.home_team,
                    m.away_team,
                    m.home_score,
                    m.away_score,
                    m.match_date,
                    m.league_name,
                    m.status
                FROM matches m
                WHERE m.match_id = $1
            `;

            const result = await client.query(query, [matchId]);

            if (result.rows.length === 0) {
                return { success: false, message: '比赛不存在' };
            }

            const match = result.rows[0];

            if (match.status !== 'finished') {
                return { success: false, message: '比赛尚未完赛' };
            }

            if (match.home_score === null || match.away_score === null) {
                return { success: false, message: '比分数据缺失' };
            }

            const results = await this._processMatches([match]);
            this.stats.matchesProcessed += results.processed;
            this.stats.lastRun = new Date().toISOString();

            return results;
        } finally {
            client.release();
        }
    }

    /**
     * 批量处理比赛
     * @param matches
     * @private
     */
    async _processMatches(matches) {
        const client = await this.pool.connect();
        const eloResults = new Map();

        try {
            // 计算 Elo
            for (const match of matches) {
                const matchData = {
                    matchId: match.match_id,
                    homeTeamId: match.home_team,
                    awayTeamId: match.away_team,
                    homeScore: parseInt(match.home_score, 10),
                    awayScore: parseInt(match.away_score, 10),
                    matchDate: match.match_date
                };

                const eloFeatures = this.eloExtractor.updateMatchElo(matchData);
                eloResults.set(match.match_id, {
                    ...eloFeatures,
                    league_name: match.league_name
                });
            }

            // 更新 L3 特征表
            let updated = 0;
            for (const [matchId, eloFeatures] of eloResults) {
                try {
                    await client.query(`
                        UPDATE l3_features
                        SET elo_features = $1, updated_at = NOW()
                        WHERE match_id = $2
                    `, [JSON.stringify(eloFeatures), matchId]);
                    updated++;
                } catch (err) {
                    console.error(`[EloAutoUpdater] 更新失败 [${matchId}]: ${err.message}`);
                }
            }

            // 保存球队 Elo 评分
            const allRatings = this.eloExtractor.exportAllRatings();
            let teamsSaved = 0;

            for (const [teamName, rating] of Object.entries(allRatings)) {
                const matchCount = this.eloExtractor.ratingHistory.get(teamName)?.length || 0;

                await client.query(`
                    INSERT INTO team_elo_ratings (team_name, elo_rating, matches_played, last_updated)
                    VALUES ($1, $2, $3, NOW())
                    ON CONFLICT (team_name)
                    DO UPDATE SET
                        elo_rating = EXCLUDED.elo_rating,
                        matches_played = EXCLUDED.matches_played,
                        last_updated = NOW()
                `, [teamName, rating, matchCount]);

                teamsSaved++;
            }

            return {
                success: true,
                processed: updated,
                teamsSaved,
                totalTeams: Object.keys(allRatings).length
            };
        } finally {
            client.release();
        }
    }

    /**
     * 获取统计信息
     */
    getStats() {
        return {
            ...this.stats,
            extractorStats: this.eloExtractor ? this.eloExtractor.getStats() : null
        };
    }

    /**
     * 关闭连接
     */
    async close() {
        if (this.pool) {
            await this.pool.end();
        }
    }
}

// ============================================================================
// 导出
// ============================================================================

module.exports = {
    EloAutoUpdater,
    DEFAULT_CONFIG
};
