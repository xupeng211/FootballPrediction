/**
 * DataFetcher - V5.2 数据获取器
 * ==============================
 *
 * 负责所有数据库查询，支持流式读取和分批读取。
 * 从数据库获取待处理比赛、Elo 评分等数据。
 *
 * @module feature_engine/smelter/components/DataFetcher
 * @version V5.2.0-HOME-FORTRESS
 * @since 2026-03-14
 */

'use strict';

const { BaseExtractor, ExtractorError } = require('./BaseExtractor');

// ============================================================================
// 配置常量
// ============================================================================

const DEFAULT_CONFIG = {
    batchSize: 500,
    maxRetries: 3,
    retryDelayMs: 1000,
    defaultEloRating: 1500
};

// SQL 查询语句
const QUERIES = {
    // 获取待处理比赛（增量）
    getPendingMatches: `
        SELECT
            m.match_id,
            m.external_id,
            m.home_team,
            m.away_team,
            m.match_date,
            m.home_score,
            m.away_score,
            r.raw_data
        FROM matches m
        INNER JOIN raw_match_data r ON m.match_id = r.match_id
        LEFT JOIN l3_features l3 ON m.match_id = l3.match_id
        WHERE m.external_id IS NOT NULL
          AND l3.match_id IS NULL
        ORDER BY m.match_date DESC
        LIMIT $1
    `,

    // 获取所有比赛（全量）
    getAllMatches: `
        SELECT
            m.match_id,
            m.external_id,
            m.home_team,
            m.away_team,
            m.match_date,
            m.home_score,
            m.away_score,
            r.raw_data
        FROM matches m
        INNER JOIN raw_match_data r ON m.match_id = r.match_id
        WHERE m.external_id IS NOT NULL
        ORDER BY m.match_date DESC
        LIMIT $1
    `,

    // 获取 Elo 评分
    getEloRatings: `
        SELECT team_name, elo_rating
        FROM team_elo_ratings
    `,

    // 获取比赛数量统计
    getPendingCount: `
        SELECT COUNT(*) as count
        FROM matches m
        INNER JOIN raw_match_data r ON m.match_id = r.match_id
        LEFT JOIN l3_features l3 ON m.match_id = l3.match_id
        WHERE m.external_id IS NOT NULL
          AND l3.match_id IS NULL
    `,

    // 检查比赛是否存在
    checkMatchExists: `
        SELECT 1
        FROM l3_features
        WHERE match_id = $1
        LIMIT 1
    `
};

// ============================================================================
// DataFetcher 类
// ============================================================================

/**
 * 数据获取器
 */
class DataFetcher extends BaseExtractor {
    /**
     * @param {object} options - 配置选项
     * @param {object} options.pool - 数据库连接池（必填）
     */
    constructor(options = {}) {
        super({
            name: 'DataFetcher',
            version: 'V5.2.0-HOME-FORTRESS',
            requiredFields: [],
            config: { ...DEFAULT_CONFIG, ...(options.config || {}) }
        });

        if (!options.pool) {
            throw new ExtractorError(
                'DataFetcher 需要数据库连接池',
                'MISSING_POOL',
                { options }
            );
        }

        this.pool = options.pool;
        this.eloCache = new Map();
        this.isEloLoaded = false;
    }

    /**
     * 获取默认配置
     * @returns {object}
     */
    getDefaultConfig() {
        return DEFAULT_CONFIG;
    }

    /**
     * 获取特征字段名清单（DataFetcher 不产生特征）
     * @returns {Array<string>}
     */
    getFeatureNames() {
        return [];
    }

    /**
     * 执行提取（DataFetcher 不使用此方法）
     * @param {object} rawData - 原始数据
     * @param {object} context - 上下文
     */
    extract(rawData, context = {}) {
        throw new ExtractorError(
            'DataFetcher 不支持 extract 方法，请使用专用方法如 getPendingMatches()',
            'UNSUPPORTED_OPERATION',
            { extractor: this.name }
        );
    }

    // ========================================================================
    // 核心查询方法
    // ========================================================================

    /**
     * 获取待处理的比赛列表
     * @param {boolean} fullRecalculate - 是否全量重算
     * @param {number} limit - 批量大小
     * @returns {Promise<Array>} 比赛数组
     */
    async getPendingMatches(fullRecalculate = false, limit = 1000) {
        const startTime = Date.now();
        this.stats.totalCalls++;

        try {
            const query = fullRecalculate ? QUERIES.getAllMatches : QUERIES.getPendingMatches;
            const result = await this._queryWithRetry(query, [limit]);

            this.stats.successfulCalls++;
            this._updateExecutionTime(Date.now() - startTime);

            this.logger.debug('获取待处理比赛', {
                count: result.rows.length,
                fullRecalculate,
                limit
            });

            return result.rows;
        } catch (error) {
            this.stats.failedCalls++;
            this.logger.error('获取待处理比赛失败', {
                error: error.message,
                fullRecalculate,
                limit
            });
            throw error;
        }
    }

    /**
     * 流式获取待处理比赛（生成器）
     * @param {boolean} fullRecalculate - 是否全量重算
     * @param {number} batchSize - 每批大小
     * @yields {object} 单场比赛数据
     */
    async *streamPendingMatches(fullRecalculate = false, batchSize = null) {
        const size = batchSize || this.config.batchSize;
        let offset = 0;
        let hasMore = true;

        while (hasMore) {
            const matches = await this.getPendingMatches(fullRecalculate, size);

            if (matches.length === 0) {
                hasMore = false;
                break;
            }

            for (const match of matches) {
                yield match;
            }

            offset += matches.length;
            hasMore = matches.length === size;
        }
    }

    /**
     * 批量获取待处理比赛
     * @param {boolean} fullRecalculate - 是否全量重算
     * @param {number} batchSize - 每批大小
     * @yields {Array} 比赛批次数组
     */
    async *batchPendingMatches(fullRecalculate = false, batchSize = null) {
        const size = batchSize || this.config.batchSize;
        const matches = await this.getPendingMatches(fullRecalculate, size);

        if (matches.length > 0) {
            yield matches;
        }
    }

    /**
     * 获取待处理比赛数量
     * @returns {Promise<number>}
     */
    async getPendingCount() {
        this.stats.totalCalls++;

        try {
            const result = await this._queryWithRetry(QUERIES.getPendingCount, []);
            this.stats.successfulCalls++;
            return parseInt(result.rows[0].count, 10);
        } catch (error) {
            this.stats.failedCalls++;
            this.logger.error('获取待处理数量失败', { error: error.message });
            return 0;
        }
    }

    // ========================================================================
    // Elo 评分相关
    // ========================================================================

    /**
     * 加载 Elo 评分到缓存
     * @returns {Promise<number>} 加载的球队数量
     */
    async loadEloCache() {
        this.stats.totalCalls++;

        try {
            const result = await this._queryWithRetry(QUERIES.getEloRatings, []);

            this.eloCache.clear();
            for (const row of result.rows) {
                if (row.team_name && row.elo_rating !== null) {
                    this.eloCache.set(row.team_name, parseFloat(row.elo_rating));
                }
            }

            this.isEloLoaded = true;
            this.stats.successfulCalls++;

            this.logger.info('Elo 缓存加载完成', { teamCount: this.eloCache.size });
            return this.eloCache.size;

        } catch (error) {
            this.stats.failedCalls++;
            this.logger.warn('加载 Elo 缓存失败', { error: error.message });
            return 0;
        }
    }

    /**
     * 获取球队 Elo 评分
     * @param {string} teamName - 球队名称
     * @returns {number} Elo 评分
     */
    getTeamElo(teamName) {
        if (!teamName || typeof teamName !== 'string') {
            return this.config.defaultEloRating;
        }

        // 精确匹配
        const elo = this.eloCache.get(teamName);
        if (elo !== undefined) {
            return elo;
        }

        // 模糊匹配
        const normalizedTeamName = teamName.toLowerCase().replace(/[^a-z0-9]/g, '');
        for (const [cachedName, cachedElo] of this.eloCache) {
            const normalizedCachedName = cachedName.toLowerCase().replace(/[^a-z0-9]/g, '');
            if (normalizedCachedName === normalizedTeamName) {
                return cachedElo;
            }
        }

        return this.config.defaultEloRating;
    }

    /**
     * 获取两队 Elo 特征
     * @param {string} homeTeam - 主队名称
     * @param {string} awayTeam - 客队名称
     * @returns {object} Elo 特征对象
     */
    getEloFeatures(homeTeam, awayTeam) {
        const homeElo = this.getTeamElo(homeTeam);
        const awayElo = this.getTeamElo(awayTeam);
        const isDefaultElo = (homeElo === this.config.defaultEloRating &&
                              awayElo === this.config.defaultEloRating);

        return {
            home_elo: homeElo,
            away_elo: awayElo,
            elo_diff: homeElo - awayElo,
            elo_expected_home: 1 / (1 + Math.pow(10, (awayElo - homeElo - 50) / 400)),
            _is_default: isDefaultElo
        };
    }

    /**
     * 检查 Elo 缓存是否已加载
     * @returns {boolean}
     */
    isEloCacheLoaded() {
        return this.isEloLoaded;
    }

    /**
     * 清除 Elo 缓存
     */
    clearEloCache() {
        this.eloCache.clear();
        this.isEloLoaded = false;
        this.logger.debug('Elo 缓存已清除');
    }

    // ========================================================================
    // 辅助方法
    // ========================================================================

    /**
     * 检查比赛是否已处理
     * @param {string} matchId - 比赛 ID
     * @returns {Promise<boolean>}
     */
    async isMatchProcessed(matchId) {
        try {
            const result = await this._queryWithRetry(QUERIES.checkMatchExists, [matchId]);
            return result.rows.length > 0;
        } catch (error) {
            this.logger.error('检查比赛状态失败', { matchId, error: error.message });
            return false;
        }
    }

    // ========================================================================
    // 私有方法
    // ========================================================================

    /**
     * 带重试的查询
     * @private
     * @param {string} query - SQL 查询
     * @param {Array} params - 查询参数
     * @returns {Promise<object>}
     */
    async _queryWithRetry(query, params) {
        let lastError;
        let delay = this.config.retryDelayMs;

        for (let attempt = 0; attempt < this.config.maxRetries; attempt++) {
            try {
                return await this.pool.query(query, params);
            } catch (error) {
                lastError = error;

                // 检查是否可重试
                if (!this._isRetryableError(error)) {
                    throw error;
                }

                this.logger.warn(`查询失败，${this.config.maxRetries - attempt - 1} 次重试剩余`, {
                    attempt: attempt + 1,
                    error: error.message
                });

                // 指数退避
                await this._sleep(delay);
                delay *= 2;
            }
        }

        throw lastError;
    }

    /**
     * 检查错误是否可重试
     * @private
     * @param {Error} error - 错误对象
     * @returns {boolean}
     */
    _isRetryableError(error) {
        if (!error) return false;

        const retryableCodes = [
            'ECONNRESET',
            'ETIMEDOUT',
            'ECONNREFUSED',
            '08000',  // connection_exception
            '08003',  // connection_does_not_exist
            '08006',  // connection_failure
            '40001'   // serialization_failure
        ];

        return retryableCodes.some(code =>
            error.code === code ||
            (error.message && error.message.includes(code))
        );
    }

    /**
     * 睡眠
     * @private
     * @param {number} ms - 毫秒
     * @returns {Promise<void>}
     */
    _sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * 更新执行时间
     * @private
     * @param {number} executionTime - 执行时间
     */
    _updateExecutionTime(executionTime) {
        const { successfulCalls } = this.stats;
        if (successfulCalls === 1) {
            this.stats.avgExecutionTimeMs = executionTime;
        } else {
            this.stats.avgExecutionTimeMs =
                (this.stats.avgExecutionTimeMs * (successfulCalls - 1) + executionTime) / successfulCalls;
        }
    }
}

// ============================================================================
// 导出
// ============================================================================
module.exports = {
    DataFetcher,
    QUERIES,
    DEFAULT_CONFIG
};
