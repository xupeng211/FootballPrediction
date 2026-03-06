#!/usr/bin/env node
/**
 * FeatureSmelter - V3.0-PRO 特征熔炼调度器
 * ==========================================
 *
 * 批量处理 raw_match_data，调用 4 个 Extractors 生成结构化特征
 * 将真实 Elo 从 team_elo_ratings 表注入到 l3_features.elo_features
 *
 * V3.0-PRO 工业级重构:
 * - 引入配置中心 (config/constants.js, config/database.js)
 * - 指数退避重试逻辑
 * - 结构化 JSON 日志（ELK 友好）
 * - 纯函数化的 Extractor 调用
 *
 * @module feature_engine/smelter/FeatureSmelter
 * @version V3.0.0-PRO
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
} = require('../../config/constants');

const { getPool, withRetry, checkHealth, closePool, isRetryableError } = require('../../config/database');

// 导入提取器（纯函数）
const { extractGoldenFeatures } = require('../extractors/GoldenFeatureExtractor');
const { extractTacticalFeatures } = require('../extractors/TacticalMomentumExtractor');
const { extractOddsMovementFeatures } = require('../extractors/OddsMovementExtractor');

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
// 结构化日志器
// ============================================================================

/**
 * 结构化日志器 - 输出 JSON 格式，便于 ELK 采集
 */
class StructuredLogger {
    /**
     * @param {Object} options - 日志选项
     * @param {string} options.component - 组件名称
     * @param {string} options.logDir - 日志目录
     * @param {boolean} options.enableStructured - 是否启用结构化输出
     */
    constructor(options = {}) {
        this.component = options.component || 'FeatureSmelter';
        this.logDir = options.logDir || '/app/logs/pipeline';
        this.enableStructured = options.enableStructured !== false;
        this.logStream = null;

        this._ensureLogDirectory();
        this._initLogStream();
    }

    /**
     * 确保日志目录存在
     * @private
     */
    _ensureLogDirectory() {
        if (!fs.existsSync(this.logDir)) {
            try {
                fs.mkdirSync(this.logDir, { recursive: true });
            } catch (error) {
                console.warn(`[WARN] 无法创建日志目录: ${error.message}`);
            }
        }
    }

    /**
     * 初始化日志文件流
     * @private
     */
    _initLogStream() {
        const logFileName = `smelter_${new Date().toISOString().slice(0, 10)}.jsonl`;
        const logFilePath = path.join(this.logDir, logFileName);

        try {
            this.logStream = fs.createWriteStream(logFilePath, { flags: 'a' });
        } catch (error) {
            console.warn(`[WARN] 无法创建日志文件: ${error.message}`);
        }
    }

    /**
     * 输出结构化日志
     *
     * @param {string} level - 日志级别 (error, warn, info, debug)
     * @param {string} message - 日志消息
     * @param {Object} [context] - 附加上下文
     */
    log(level, message, context = {}) {
        const logEntry = {
            timestamp: new Date().toISOString(),
            level,
            component: this.component,
            message,
            ...context
        };

        // 控制台输出
        const consoleMethod = level === 'error' ? 'error' : level === 'warn' ? 'warn' : 'log';
        if (this.enableStructured) {
            console[consoleMethod](JSON.stringify(logEntry));
        } else {
            const prefix = `[${logEntry.timestamp}] [${level.toUpperCase()}]`;
            console[consoleMethod](`${prefix} ${message}`, Object.keys(context).length > 0 ? context : '');
        }

        // 文件输出（JSONL 格式）
        if (this.logStream && this.logStream.writable) {
            try {
                this.logStream.write(JSON.stringify(logEntry) + '\n');
            } catch (writeError) {
                // 忽略写入错误
            }
        }
    }

    info(message, context = {}) {
        this.log(LOG_LEVELS.INFO, message, context);
    }

    warn(message, context = {}) {
        this.log(LOG_LEVELS.WARN, message, context);
    }

    error(message, context = {}) {
        this.log(LOG_LEVELS.ERROR, message, context);
    }

    debug(message, context = {}) {
        if (process.env.LOG_LEVEL === 'debug') {
            this.log(LOG_LEVELS.DEBUG, message, context);
        }
    }

    close() {
        if (this.logStream) {
            try {
                this.logStream.end();
            } catch (error) {
                // 忽略关闭错误
            }
            this.logStream = null;
        }
    }
}

// ============================================================================
// FeatureSmelter 类 - V3.0-PRO 工业级实现
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
     * @param {Object} config - 配置对象
     */
    constructor(config = {}) {
        this.config = { ...DEFAULT_CONFIG, ...config };
        this.pool = null;
        this.eloCache = new Map();
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
     *
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

            // 创建数据库索引
            await this._ensureIndexes();

            this.isInitialized = true;
            this.logger.info('FeatureSmelter V3.0-PRO 初始化完成', {
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
     *
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
     * @param {boolean} fullRecalculate - 是否全量重算
     * @param {number} limit - 批量大小
     * @returns {Promise<Array>}
     */
    async getPendingMatches(fullRecalculate = false, limit = 1000) {
        const operation = async (pool) => {
            let query;
            if (fullRecalculate) {
                query = `
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
                `;
            } else {
                query = `
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
     *
     * @param {Object} match - 比赛数据
     * @returns {Object|null} 提取的特征，失败返回 null
     */
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
            const homeElo = this.getTeamElo(home_team);
            const awayElo = this.getTeamElo(away_team);

            // V3.6-DATA-RESTORE: Elo 默认值检测
            const isDefaultElo = (homeElo === DEFAULT_ELO_RATING && awayElo === DEFAULT_ELO_RATING);

            const eloFeatures = {
                home_elo: homeElo,
                away_elo: awayElo,
                elo_diff: homeElo - awayElo,
                elo_expected_home: 1 / (1 + Math.pow(10, (awayElo - homeElo - 50) / 400)),
                _is_default: isDefaultElo
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
     *
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
     *
     * @param {Object} options - 执行选项
     * @param {boolean} [options.fullRecalculate] - 是否全量重算
     * @param {number} [options.limit] - 批量大小
     * @returns {Promise<Object>} 执行统计
     */
    async run(options = {}) {
        const { fullRecalculate = false, limit = this.config.batchSize } = options;

        this.logger.info('开始特征熔炼', { fullRecalculate, limit, config: this.config });

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
            const batchSize = 50;
            const allFeatures = [];

            for (let i = 0; i < matches.length; i += batchSize) {
                const batch = matches.slice(i, i + batchSize);

                for (const match of batch) {
                    const features = this.processMatch(match);
                    if (features) {
                        allFeatures.push(features);
                    }
                }

                // 批量保存
                if (allFeatures.length >= batchSize) {
                    const saved = await this.saveFeatures(allFeatures.splice(0, batchSize));
                    this.logger.debug('批量保存完成', { saved, progress: `${Math.min(i + batchSize, matches.length)}/${matches.length}` });
                }

                // 延时控制
                if (this.config.delayMs > 0) {
                    await new Promise(resolve => setTimeout(resolve, this.config.delayMs));
                }
            }

            // 保存剩余特征
            if (allFeatures.length > 0) {
                await this.saveFeatures(allFeatures);
            }

            const duration = Date.now() - startTime;

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
