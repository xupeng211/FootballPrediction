#!/usr/bin/env node
/**
 * FeatureSmelter - V5.2.0-HOME-FORTRESS 特征熔炼调度器
 * ==========================================
 *
 * 批量处理 raw_match_data，调用 4 个 Extractors 生成结构化特征
 * 将真实 Elo 从 team_elo_ratings 表注入到 l3_features.elo_features
 *
 * V5.2.0-HOME-FORTRESS 工业级重构:
 * - 引入配置中心 (config/constants.js, config/database.js)
 * - 指数退避重试逻辑
 * - 结构化 JSON 日志（ELK 友好）
 * - 纯函数化的 Extractor 调用
 * @module feature_engine/smelter/FeatureSmelter
 * @version V5.2.0-HOME-FORTRESS
 * @since 2026-03-06
 */

'use strict';

const fs = require('fs');
const path = require('path');

// 导入配置中心
const {
    DB_MAX_RETRIES,
    DB_RETRY_DELAY_MS,
    DB_RETRY_BACKOFF_MULTIPLIER,
    DEFAULT_ELO_RATING,
    LOG_LEVELS,
    MARKET_VALUE_MULTIPLIER
} = require('../../../config/constants');

const { getPool, withRetry, checkHealth, closePool, isRetryableError } = require('../../../config/database');

// V4.0: 从 utils 导入结构化日志器
const { StructuredLogger } = require('../../utils/StructuredLogger');

// 导入提取器（纯函数）
const { extractGoldenFeatures } = require('../extractors/GoldenFeatureExtractor');
const { extractTacticalFeatures } = require('../extractors/TacticalMomentumExtractor');
const { extractOddsMovementFeatures } = require('../extractors/OddsMovementExtractor');

// 2AH: in-memory prematch Elo fallback when team_elo_ratings cache is empty
const { PrematchEloComputer } = require('../elo/PrematchEloComputer');

// ============================================================================
// 配置
// ============================================================================

const DEFAULT_CONFIG = {
    batchSize: 500,
    delayMs: 5,
    rollingLookback: 5,
    debugRolling: true,
    logDir: '/app/logs/pipeline',
    enableStructuredLogging: true
};

// ============================================================================
// FeatureSmelter 类 - V5.2.0-HOME-FORTRESS 工业级实现
// ============================================================================

/**
 * 特征熔炼器
 *
 * 职责：
 * 1. 从 raw_match_data 读取原始数据
 * 2. 调用 Extractors 提取特征
 * 3. 将特征写入 l3_features 表
 */
class FeatureSmelter {
    /**
     * @param {object} config - 配置对象
     */
    constructor(config = {}) {
        this.config = { ...DEFAULT_CONFIG, ...config };
        this.pool = null;
        this.eloCache = new Map();
        this.prematchEloComputer = null;  // 2AH: in-memory Elo fallback
        this.matchEloMap = null;          // 2AH: matchId → prematch eloFeatures
        this.logger = new StructuredLogger({
            component: 'FeatureSmelter',
            logDir: this.config.logDir,
            enableStructured: this.config.enableStructuredLogging
        });
        this.isInitialized = false;

        // 统计计数器
        this.stats = {
            total: 0,
            success: 0,
            failed: 0,
            skipped: 0,
            rollingHits: 0,
            rollingMisses: 0,
            dataGaps: 0,
            marketValueHits: 0,
            marketValueMisses: 0,
            retries: 0
        };
    }

    /**
     * 初始化数据库连接和缓存
     * @returns {Promise<FeatureSmelter>}
     * @throws {Error} 初始化失败时抛出
     */
    async init() {
        try {
            // 获取数据库连接池（来自配置中心）
            this.pool = getPool();

            // 测试连接（带重试）
            const health = await checkHealth();
            if (!health.healthy) {
                throw new Error(`Database health check failed: ${health.error}`);
            }

            this.logger.info('数据库连接池已建立', { latency: health.latency });

            // 加载 Elo 缓存
            await this._loadEloCache();

            // 2AH: 当 team_elo_ratings cache 为空时，使用 in-memory prematch Elo
            if (this.eloCache.size === 0) {
                this.logger.info('team_elo_ratings 为空，启用 in-memory PrematchEloComputer');
                await this._loadPrematchEloHistory();
            }

            // 创建数据库索引
            await this._ensureIndexes();

            this.isInitialized = true;
            this.logger.info('FeatureSmelter V5.2.0-HOME-FORTRESS 初始化完成', {
                eloTeams: this.eloCache.size,
                config: {
                    batchSize: this.config.batchSize,
                    rollingLookback: this.config.rollingLookback
                }
            });

            return this;
        } catch (error) {
            this.logger.error('初始化失败', { error: error.message, stack: error.stack });
            throw error;
        }
    }

    /**
     * 加载 Elo 缓存（带重试）
     * @private
     */
    async _loadEloCache() {
        const operation = async (pool) => {
            const result = await pool.query('SELECT team_name, elo_rating FROM team_elo_ratings');
            return result.rows;
        };

        try {
            const rows = await withRetry(operation, 'loadEloCache', {
                maxRetries: DB_MAX_RETRIES,
                initialDelayMs: DB_RETRY_DELAY_MS
            });

            this.eloCache = new Map();
            for (const row of rows) {
                if (row.team_name && row.elo_rating) {
                    this.eloCache.set(row.team_name, parseFloat(row.elo_rating));
                }
            }

            this.logger.info('Elo 缓存加载完成', { teamCount: this.eloCache.size });
        } catch (error) {
            this.logger.warn('加载 Elo 缓存失败，使用默认值', {
                error: error.message,
                defaultElo: DEFAULT_ELO_RATING
            });
        }
    }

    /**
     * 2AH: 从 match history 计算 in-memory prematch Elo（SELECT-only）。
     *
     * 当 team_elo_ratings cache 为空时，加载所有已完赛比赛，
     * 使用 PrematchEloComputer 为每场计算赛前 Elo。
     *
     * 本方法不写任何表，不修改 team_elo_ratings，不修改 l3_features。
     *
     * @returns {Promise<Map>} matchId → prematchEloFeatures
     * @private
     */
    async _loadPrematchEloHistory() {
        try {
            const operation = async (pool) => {
                const result = await pool.query(`
                    SELECT match_id, home_team, away_team,
                           home_score, away_score, match_date
                    FROM matches
                    WHERE home_score IS NOT NULL
                      AND away_score IS NOT NULL
                    ORDER BY match_date ASC, match_id ASC
                `);
                return result.rows;
            };

            const rows = await withRetry(operation, 'loadPrematchEloHistory', {
                maxRetries: DB_MAX_RETRIES,
                initialDelayMs: DB_RETRY_DELAY_MS
            });

            if (!rows || rows.length === 0) {
                this.logger.info('PrematchElo: 无历史比赛数据，跳过 in-memory Elo');
                return;
            }

            const matches = rows.map(r => ({
                matchId: r.match_id,
                homeTeam: r.home_team,
                awayTeam: r.away_team,
                homeScore: r.home_score,
                awayScore: r.away_score,
                matchDate: r.match_date,
            }));

            this.prematchEloComputer = new PrematchEloComputer();
            this.matchEloMap = this.prematchEloComputer.computeAll(matches);

            const eloHits = [...this.matchEloMap.values()]
                .filter(e => e._is_default === false).length;
            const eloDefaults = [...this.matchEloMap.values()]
                .filter(e => e._is_default === true).length;

            this.logger.info('PrematchElo 历史计算完成', {
                totalMatches: matches.length,
                computedMatches: this.matchEloMap.size,
                eloHits,
                eloDefaults,
            });
        } catch (error) {
            this.logger.warn('PrematchElo 历史计算失败，回退到默认值', {
                error: error.message,
            });
            this.matchEloMap = null;
        }
    }

    /**
     * 确保数据库索引存在
     * @private
     */
    async _ensureIndexes() {
        const indexDefinitions = [
            {
                name: 'idx_matches_home_team_date',
                query: 'CREATE INDEX IF NOT EXISTS idx_matches_home_team_date ON matches(home_team, match_date)'
            },
            {
                name: 'idx_matches_away_team_date',
                query: 'CREATE INDEX IF NOT EXISTS idx_matches_away_team_date ON matches(away_team, match_date)'
            },
            {
                name: 'idx_raw_match_data_match_id',
                query: 'CREATE INDEX IF NOT EXISTS idx_raw_match_data_match_id ON raw_match_data(match_id)'
            },
            {
                name: 'idx_l3_features_match_id',
                query: 'CREATE INDEX IF NOT EXISTS idx_l3_features_match_id ON l3_features(match_id)'
            }
        ];

        let successCount = 0;
        let failCount = 0;

        for (const indexDef of indexDefinitions) {
            try {
                await this.pool.query(indexDef.query);
                successCount++;
            } catch (error) {
                this.logger.warn(`索引创建失败: ${indexDef.name}`, { error: error.message });
                failCount++;
            }
        }

        this.logger.info('数据库索引检查完成', { success: successCount, failed: failCount });
    }

    /**
     * 获取球队 Elo 评分
     * @param {string} teamName - 球队名称
     * @returns {number} Elo 评分
     */
    getTeamElo(teamName) {
        if (!teamName || typeof teamName !== 'string') {
            return DEFAULT_ELO_RATING;
        }

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

        return DEFAULT_ELO_RATING;
    }

    /**
     * 获取待处理的比赛列表（带重试）
     *
     * V5.2.1: Target selection now returns distinct match_id rows with
     * data_version priority.  LIMIT applies to distinct matches, not
     * raw_match_data rows.
     *
     * Data version priority (highest first):
     *   1. fotmob_live_v1
     *   2. fotmob_pageprops_v2
     *   3. fotmob_html_hyd_v1
     *   4. other (non-legacy)
     *
     * Excluded versions: PHASE4.23, PHASE4.43_SYNTHETIC
     *
     * @param {boolean} fullRecalculate - 是否全量重算
     * @param {number} limit - 批量大小（distinct match_id 数量）
     * @returns {Promise<Array>}
     */
    async getPendingMatches(fullRecalculate = false, limit = 1000) {
        const operation = async (pool) => {
            let query;
            if (fullRecalculate) {
                query = `
                    WITH ranked AS (
                        SELECT
                            m.match_id,
                            m.external_id,
                            m.home_team,
                            m.away_team,
                            m.match_date,
                            m.home_score,
                            m.away_score,
                            r.raw_data,
                            r.data_version,
                            ROW_NUMBER() OVER (
                                PARTITION BY m.match_id
                                ORDER BY
                                    CASE r.data_version
                                        WHEN 'fotmob_live_v1' THEN 1
                                        WHEN 'fotmob_pageprops_v2' THEN 2
                                        WHEN 'fotmob_html_hyd_v1' THEN 3
                                        ELSE 99
                                    END,
                                    m.match_date DESC NULLS LAST,
                                    m.match_id,
                                    r.data_version
                            ) AS rn
                        FROM matches m
                        INNER JOIN raw_match_data r ON m.match_id = r.match_id
                        WHERE m.external_id IS NOT NULL
                          AND COALESCE(r.data_version, '') NOT IN ('PHASE4.23', 'PHASE4.43_SYNTHETIC')
                    )
                    SELECT
                        match_id,
                        external_id,
                        home_team,
                        away_team,
                        match_date,
                        home_score,
                        away_score,
                        raw_data,
                        data_version
                    FROM ranked
                    WHERE rn = 1
                    ORDER BY match_date DESC NULLS LAST, match_id
                    LIMIT $1
                `;
            } else {
                query = `
                    WITH ranked AS (
                        SELECT
                            m.match_id,
                            m.external_id,
                            m.home_team,
                            m.away_team,
                            m.match_date,
                            m.home_score,
                            m.away_score,
                            r.raw_data,
                            r.data_version,
                            ROW_NUMBER() OVER (
                                PARTITION BY m.match_id
                                ORDER BY
                                    CASE r.data_version
                                        WHEN 'fotmob_live_v1' THEN 1
                                        WHEN 'fotmob_pageprops_v2' THEN 2
                                        WHEN 'fotmob_html_hyd_v1' THEN 3
                                        ELSE 99
                                    END,
                                    m.match_date DESC NULLS LAST,
                                    m.match_id,
                                    r.data_version
                            ) AS rn
                        FROM matches m
                        INNER JOIN raw_match_data r ON m.match_id = r.match_id
                        LEFT JOIN l3_features l3 ON m.match_id = l3.match_id
                        WHERE m.external_id IS NOT NULL
                          AND l3.match_id IS NULL
                          AND COALESCE(r.data_version, '') NOT IN ('PHASE4.23', 'PHASE4.43_SYNTHETIC')
                    )
                    SELECT
                        match_id,
                        external_id,
                        home_team,
                        away_team,
                        match_date,
                        home_score,
                        away_score,
                        raw_data,
                        data_version
                    FROM ranked
                    WHERE rn = 1
                    ORDER BY match_date DESC NULLS LAST, match_id
                    LIMIT $1
                `;
            }

            const result = await pool.query(query, [limit]);
            return result.rows;
        };

        return withRetry(operation, 'getPendingMatches', {
            maxRetries: DB_MAX_RETRIES,
            initialDelayMs: DB_RETRY_DELAY_MS
        });
    }

    /**
     * 处理单场比赛的特征提取
     * @param {object} match - 比赛数据
     * @returns {object | null} 提取的特征，失败返回 null
     */
    // eslint-disable-next-line complexity
    processMatch(match) {
        const { match_id, home_team, away_team, raw_data } = match;

        if (!raw_data) {
            this.logger.debug('跳过：无原始数据', { match_id });
            this.stats.skipped++;
            return null;
        }

        try {
            // 调用纯函数提取器
            const goldenFeatures = extractGoldenFeatures(raw_data);
            const tacticalFeatures = extractTacticalFeatures(raw_data);
            const oddsMovementFeatures = extractOddsMovementFeatures(raw_data);

            // V3.6-DATA-RESTORE: 赔率缺失警告 - 强制抛出警告而不是静默写 0
            if (!oddsMovementFeatures.has_odds_data) {
                this.logger.warn('⚠️ 赔率数据缺失 - OddsPortalProvider 未实现', {
                    match_id,
                    home_team,
                    away_team,
                    warning: 'ODDS_DATA_MISSING',
                    note: 'FotMob 不提供赔率数据，需实现 OddsPortalProvider'
                });
                this.stats.oddsMisses = (this.stats.oddsMisses || 0) + 1;
                // 标记特征为不完整
                oddsMovementFeatures._data_quality = 'INCOMPLETE_ODDS';
            } else {
                this.stats.oddsHits = (this.stats.oddsHits || 0) + 1;
            }

            // 获取 Elo 特征
            // 2AH: 优先使用 in-memory prematch Elo（按 match 粒度），否则 fallback 到 cache/默认值
            let homeElo, awayElo, isDefaultElo, prematchEloMeta;

            const cachedPrematch = this.matchEloMap
                ? this.matchEloMap.get(match_id)
                : undefined;

            if (cachedPrematch) {
                homeElo = cachedPrematch.home_elo_pre;
                awayElo = cachedPrematch.away_elo_pre;
                isDefaultElo = cachedPrematch._is_default || false;
                prematchEloMeta = {
                    _source: 'PrematchEloComputer',
                    _version: cachedPrematch._version || '2AH',
                    _home_default: cachedPrematch._home_default,
                    _away_default: cachedPrematch._away_default,
                };
            } else {
                homeElo = this.getTeamElo(home_team);
                awayElo = this.getTeamElo(away_team);
                isDefaultElo = (homeElo === DEFAULT_ELO_RATING && awayElo === DEFAULT_ELO_RATING);
            }

            const eloFeatures = {
                home_elo: homeElo,
                away_elo: awayElo,
                elo_diff: homeElo - awayElo,
                elo_expected_home: 1 / (1 + Math.pow(10, (awayElo - homeElo - 50) / 400)),
                _is_default: isDefaultElo,
                ...(prematchEloMeta || {}),
            };

            if (isDefaultElo) {
                this.stats.eloDefaults = (this.stats.eloDefaults || 0) + 1;
            } else {
                this.stats.eloHits = (this.stats.eloHits || 0) + 1;
            }

            // 统计身价数据质量
            if (goldenFeatures.home_market_value_total > 0 || goldenFeatures.away_market_value_total > 0) {
                this.stats.marketValueHits++;
            } else {
                this.stats.marketValueMisses++;
            }

            this.stats.success++;

            return {
                match_id,
                golden_features: goldenFeatures,
                tactical_features: tacticalFeatures,
                odds_movement_features: oddsMovementFeatures,
                elo_features: eloFeatures,
                computed_at: new Date().toISOString()
            };
        } catch (error) {
            this.logger.error('特征提取失败', {
                match_id,
                home_team,
                away_team,
                error: error.message
            });
            this.stats.failed++;
            return null;
        }
    }

    /**
     * 批量保存特征到数据库（带重试）
     * @param {Array} features - 特征数组
     * @returns {Promise<number>} 成功保存的数量
     */
    async saveFeatures(features) {
        if (!features || features.length === 0) {
            return 0;
        }

        const operation = async (pool) => {
            const client = await pool.connect();
            let savedCount = 0;

            try {
                await client.query('BEGIN');

                for (const feature of features) {
                    // V3.1-FINAL-POLISH: 修复审计建议，补全 external_id 字段
                    const query = `
                        INSERT INTO l3_features (
                            match_id,
                            external_id,
                            golden_features,
                            tactical_features,
                            odds_movement_features,
                            elo_features,
                            computed_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                        ON CONFLICT (match_id) DO UPDATE SET
                            external_id = EXCLUDED.external_id,
                            golden_features = EXCLUDED.golden_features,
                            tactical_features = EXCLUDED.tactical_features,
                            odds_movement_features = EXCLUDED.odds_movement_features,
                            elo_features = EXCLUDED.elo_features,
                            computed_at = EXCLUDED.computed_at
                    `;

                    await client.query(query, [
                        feature.match_id,
                        feature.external_id || feature.match_id,  // 默认使用 match_id
                        JSON.stringify(feature.golden_features),
                        JSON.stringify(feature.tactical_features),
                        JSON.stringify(feature.odds_movement_features),
                        JSON.stringify(feature.elo_features),
                        feature.computed_at
                    ]);
                    savedCount++;
                }

                await client.query('COMMIT');
                return savedCount;
            } catch (error) {
                await client.query('ROLLBACK');
                throw error;
            } finally {
                client.release();
            }
        };

        return withRetry(operation, 'saveFeatures', {
            maxRetries: DB_MAX_RETRIES,
            initialDelayMs: DB_RETRY_DELAY_MS
        });
    }

    /**
     * 执行特征熔炼
     * @param {object} options - 执行选项
     * @param {boolean} [options.fullRecalculate] - 是否全量重算
     * @param {number} [options.limit] - 批量大小
     * @returns {Promise<object>} 执行统计
     */
    /**
     * Process a batch of matches — either collect preview entries (noWrite) or
     * accumulate features for saving (write mode).
     * @private
     */
    async _processBatch(matches, { isNoWrite, batchSize, allFeatures, previewEntries }) {
        for (let i = 0; i < matches.length; i += batchSize) {
            const batch = matches.slice(i, i + batchSize);
            for (const match of batch) {
                const features = this.processMatch(match);
                if (isNoWrite) {
                    previewEntries.push(this._buildPreviewEntry(match, features));
                } else if (features) {
                    allFeatures.push(features);
                }
            }
            if (!isNoWrite && allFeatures.length >= batchSize) {
                const saved = await this.saveFeatures(allFeatures.splice(0, batchSize));
                this.logger.debug('批量保存完成', { saved });
            }
            if (!isNoWrite && this.config.delayMs > 0) {
                await new Promise(resolve => { setTimeout(resolve, this.config.delayMs); });
            }
        }
    }

    async run(options = {}) {
        const {
            fullRecalculate = false,
            limit = this.config.batchSize,
            dryRun = false,
            noWrite = false,
            preview = false,
        } = options;

        const isNoWrite = dryRun || noWrite || preview;

        this.logger.info('开始特征熔炼', {
            fullRecalculate, limit, isNoWrite,
            mode: isNoWrite ? 'NO-WRITE PREVIEW' : 'WRITE ENABLED',
            config: this.config
        });

        if (isNoWrite) {
            this.logger.info('NO-WRITE PREVIEW MODE — DB writes disabled, INSERT/UPDATE suppressed');
        }

        // 重置统计
        this.stats = {
            total: 0,
            success: 0,
            failed: 0,
            skipped: 0,
            rollingHits: 0,
            rollingMisses: 0,
            dataGaps: 0,
            marketValueHits: 0,
            marketValueMisses: 0,
            oddsMisses: 0,
            oddsHits: 0,
            eloDefaults: 0,
            eloHits: 0,
            retries: 0
        };

        const startTime = Date.now();

        try {
            // 获取待处理比赛
            const matches = await this.getPendingMatches(fullRecalculate, limit);
            this.stats.total = matches.length;

            this.logger.info('待处理比赛数量', { count: matches.length });

            if (matches.length === 0) {
                this.logger.info('无待处理比赛，任务完成');
                return this.stats;
            }

            // 批量处理
            const batchSize = isNoWrite ? limit : 50;
            const allFeatures = [];
            const previewEntries = [];

            await this._processBatch(matches, { isNoWrite, batchSize, allFeatures, previewEntries });

            // 保存剩余特征 — only in write mode
            if (!isNoWrite && allFeatures.length > 0) {
                await this.saveFeatures(allFeatures);
            }

            const duration = Date.now() - startTime;

            if (isNoWrite) {
                this.logger.info('NO-WRITE PREVIEW 完成', {
                    ...this.stats,
                    duration_ms: duration,
                    preview_count: previewEntries.length,
                    note: 'No INSERT/UPDATE was executed. l3_features unchanged.'
                });
                return {
                    ...this.stats,
                    duration_ms: duration,
                    isNoWrite: true,
                    isDryRun: true,
                    preview: previewEntries.length,
                    previewEntries,
                    _note: 'NO-WRITE PREVIEW — l3_features NOT modified'
                };
            }

            this.logger.info('特征熔炼完成', {
                ...this.stats,
                duration_ms: duration,
                success_rate: this.stats.total > 0 ? (this.stats.success / this.stats.total * 100).toFixed(2) + '%' : 'N/A',
                market_value_coverage: this.stats.success > 0 ? (this.stats.marketValueHits / this.stats.success * 100).toFixed(2) + '%' : 'N/A'
            });

            return this.stats;
        } catch (error) {
            this.logger.error('特征熔炼失败', {
                error: error.message,
                stack: error.stack,
                stats: this.stats
            });
            throw error;
        }
    }

    /**
     * Build a no-write preview entry for a single match.
     *
     * Summarises each extractor output without touching the database.
     * Called only in dryRun / noWrite / preview mode.
     *
     * @param {object} match — raw match row from DB
     * @param {object|null} features — output of processMatch(), or null on failure
     * @returns {object} preview entry with extractor summaries
     * @private
     */
    // eslint-disable-next-line complexity
    _buildPreviewEntry(match, features) {
        const base = {
            match_id: match.match_id,
            external_id: match.external_id || null,
            home_team: match.home_team || null,
            away_team: match.away_team || null,
            data_version: match.data_version || null,
            has_raw_data: Boolean(match.raw_data),
            extractors: {},
            error: null,
            would_write_l3_features: false,
            actual_db_write: false,
        };

        if (!features) {
            base.error = 'processMatch returned null (raw_data missing or extractor threw)';
            return base;
        }

        base.would_write_l3_features = true;

        const extractorFields = [
            { key: 'golden_features', label: 'golden_features' },
            { key: 'tactical_features', label: 'tactical_features' },
            { key: 'odds_movement_features', label: 'odds_movement_features' },
            { key: 'elo_features', label: 'elo_features' },
        ];

        for (const { key, label } of extractorFields) {
            const val = features[key];
            if (val === undefined || val === null) {
                base.extractors[label] = {
                    present: false,
                    keys: 0,
                    empty: true,
                    reason: 'extractor output missing',
                };
            } else if (typeof val === 'object' && !Array.isArray(val)) {
                const keys = Object.keys(val).filter(k => !k.startsWith('_'));
                const dataKeys = Object.keys(val).filter(k => !k.startsWith('_') && val[k] !== null && val[k] !== undefined && val[k] !== '' && !(typeof val[k] === 'object' && Object.keys(val[k]).length === 0));
                const summary = {
                    present: true,
                    keys: keys.length,
                    data_keys: dataKeys.length,
                    empty: dataKeys.length === 0,
                    reason: dataKeys.length === 0 ? 'all values null/empty' : null,
                };
                // 2AH: 为 elo_features 展示实际 Elo 值
                if (label === 'elo_features') {
                    summary.home_elo = val.home_elo;
                    summary.away_elo = val.away_elo;
                    summary.elo_diff = val.elo_diff;
                    summary.elo_expected_home = val.elo_expected_home;
                    summary._is_default = val._is_default;
                    if (val._source) summary._source = val._source;
                    if (val._version) summary._version = val._version;
                }
                base.extractors[label] = summary;
            } else {
                base.extractors[label] = {
                    present: true,
                    keys: Array.isArray(val) ? val.length : 1,
                    empty: Array.isArray(val) ? val.length === 0 : (val === null || val === undefined),
                };
            }
        }

        return base;
    }

    /**
     * 关闭资源
     */
    async close() {
        this.logger.info('正在关闭 FeatureSmelter...');

        // 关闭日志器
        this.logger.close();

        this.isInitialized = false;
        this.logger.info('FeatureSmelter 已完全关闭');
    }
}

// ============================================================================
// 导出
// ============================================================================

module.exports = {
    FeatureSmelter,
    StructuredLogger,
    DEFAULT_CONFIG
};
