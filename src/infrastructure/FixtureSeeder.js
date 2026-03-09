/**
 * @fileoverview FixtureSeeder - L1 发现层核心模块 V4.46.6
 *
 * 工业级重构版本：
 * - 批量 UPSERT (每 50 场写入一次)
 * - 并行扫描 (可配置并发数)
 * - NetworkShield 代理池集成
 * - MetricsClient 可观测性
 * - 确定性 ID 生成
 *
 * @module infrastructure/FixtureSeeder
 * @version V4.46.6
 * @author FootballPrediction Engineering Team
 */

'use strict';

const https = require('https');
const { URL } = require('url');
const { Pool } = require('pg');
const path = require('path');
const fs = require('fs');

// ============================================================================
// V4.46.6: 核心组件集成
// ============================================================================

// 确定性 ID 生成器 (替代 Math.random)
const {
    generateRequestId,
    generateDeterministicId
} = require('../core/id_generator');

// 共享常量 (含 POSTPONED 状态)
const {
    MATCH_STATUS,
    STATUS_FINISHED,
    STATUS_LIVE,
    STATUS_SCHEDULED,
    STATUS_CANCELLED,
    STATUS_POSTPONED
} = require('../../config/shared_constants');

// V4.46.6: NetworkShield 代理池
const { getNetworkShield } = require('./network/NetworkShield');

// V4.46.6: MetricsClient 可观测性
const { getMetricsClient } = require('./monitoring/MetricsClient');

// 工厂配置
const FactoryConfig = require('../../config/factory_config');

require('dotenv').config({ path: path.resolve(__dirname, '../../.env') });

// ============================================================================
// 日志系统 (工业级分级)
// ============================================================================

const LogLevel = {
    INFO: 'INFO',
    WARN: 'WARN',
    ERROR: 'ERROR',
    SUCCESS: 'SUCCESS',
    DEBUG: 'DEBUG'
};

class Logger {
    constructor(module, requestId = null) {
        this.module = module;
        this.requestId = requestId;
    }

    setRequestId(requestId) {
        this.requestId = requestId;
    }

    _format(level, message, meta = null) {
        const timestamp = new Date().toISOString();
        const reqIdStr = this.requestId ? `[${this.requestId}] ` : '';
        const metaStr = meta ? ` | ${JSON.stringify(meta)}` : '';
        return `[${timestamp}] [${level}] [${this.module}] ${reqIdStr}${message}${metaStr}`;
    }

    info(message, meta = null) { console.log(this._format(LogLevel.INFO, message, meta)); }
    warn(message, meta = null) { console.warn(this._format(LogLevel.WARN, message, meta)); }
    error(message, error = null) {
        const meta = error ? { request_id: this.requestId || 'unknown', error: error.message, stack: error.stack } : { request_id: this.requestId || 'unknown' };
        console.error(this._format(LogLevel.ERROR, message, meta));
    }
    success(message, meta = null) { console.log(this._format(LogLevel.SUCCESS, message, meta)); }
    debug(message, meta = null) {
        if (process.env.LOG_LEVEL === 'debug') {
            console.log(this._format(LogLevel.DEBUG, message, meta));
        }
    }
}

const log = new Logger('FixtureSeeder');

// ============================================================================
// 配置加载器
// ============================================================================

function loadLeagueConfig() {
    const configPath = path.resolve(__dirname, '../../config/leagues.json');

    try {
        if (!fs.existsSync(configPath)) {
            log.warn(`配置文件不存在: ${configPath}，使用默认配置`);
            return {
                active_leagues: [{ id: 47, name: 'Premier League', country: 'England', enabled: true }],
                active_seasons: ['2023/2024', '2024/2025']
            };
        }

        const raw = fs.readFileSync(configPath, 'utf8');
        const config = JSON.parse(raw);
        const activeLeagues = config.active_leagues.filter(l => l.enabled !== false);

        log.info(`配置加载成功: ${activeLeagues.length} 个活跃联赛`, {
            leagues: activeLeagues.map(l => l.name).join(', ')
        });

        return {
            active_leagues: activeLeagues,
            active_seasons: config.active_seasons || ['2024/2025']
        };
    } catch (error) {
        log.error('配置加载失败，使用默认配置', error);
        return {
            active_leagues: [{ id: 47, name: 'Premier League', country: 'England', enabled: true }],
            active_seasons: ['2023/2024', '2024/2025']
        };
    }
}

// ============================================================================
// V4.46.6 配置
// ============================================================================

const BASE_CONFIG = {
    fotmob: {
        baseUrl: 'www.fotmob.com',
        leagueEndpoint: '/api/leagues',
        timeout: 20000
    },
    db: {
        host: process.env.DB_HOST || 'localhost',
        port: parseInt(process.env.DB_PORT || '5432'),
        database: process.env.DB_NAME || 'football_db',
        user: process.env.DB_USER || 'football_user',
        password: process.env.DB_PASSWORD || ''
    },
    // V4.46.6: 从工厂配置读取延时
    delay: FactoryConfig.TIMING?.minDelayMs || 2000,

    // V4.46.6: 批量写入配置
    batchSize: parseInt(process.env.L1_BATCH_SIZE) || 50,

    // V4.46.6: 并行扫描配置
    concurrency: parseInt(process.env.L1_CONCURRENCY) || 5,

    // V4.46.6: L1 专用代理端口段 (与 L2/L3 隔离)
    proxyPortRange: { start: 7890, end: 7894 }
};

// ============================================================================
// V4.46.6: 代理感知 HTTP 工具
// ============================================================================

/**
 * V4.46.6: 代理感知 HTTP GET 请求
 * @param {string} url - 请求 URL
 * @param {Object} options - 请求选项
 * @param {number} [workerId=0] - Worker ID (用于代理分配)
 * @returns {Promise<{status: number, data: Object|null, raw: string}>}
 */
async function httpsGetWithProxy(url, options = {}, workerId = 0) {
    return new Promise(async (resolve, reject) => {
        const shield = getNetworkShield();
        const parsedUrl = new URL(url);

        // V4.46.6: 尝试获取代理配置 (L1 使用专用端口段)
        let proxyConfig = null;
        try {
            // 计算专用代理端口 (7890-7894 范围)
            const l1Port = BASE_CONFIG.proxyPortRange.start + (workerId % 5);
            proxyConfig = {
                host: process.env.PROXY_HOST || '172.25.16.1',
                port: l1Port
            };
            log.debug(`[Worker ${workerId}] 使用代理: ${proxyConfig.host}:${proxyConfig.port}`);
        } catch (e) {
            log.debug(`代理不可用，直连模式: ${e.message}`);
        }

        const requestOptions = {
            hostname: parsedUrl.hostname,
            port: parsedUrl.port || 443,
            path: parsedUrl.pathname + parsedUrl.search,
            method: 'GET',
            timeout: options.timeout || BASE_CONFIG.fotmob.timeout,
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                ...options.headers
            }
        };

        // V4.46.6: 如果有代理，添加代理配置
        if (proxyConfig) {
            requestOptions.agent = new (require('http').Agent)({
                host: proxyConfig.host,
                port: proxyConfig.port
            });
        }

        const req = https.request(requestOptions, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                try {
                    resolve({
                        status: res.statusCode,
                        data: res.statusCode === 200 ? JSON.parse(data) : null,
                        raw: data
                    });
                } catch (e) {
                    resolve({ status: res.statusCode, data: null, raw: data, error: e.message });
                }
            });
        });

        req.on('error', (e) => {
            log.debug(`HTTP 请求失败 (Worker ${workerId}): ${e.message}`);
            reject(e);
        });

        req.setTimeout(options.timeout || BASE_CONFIG.fotmob.timeout, () => {
            req.destroy();
            reject(new Error('Request timeout'));
        });

        req.end();
    });
}

// 向后兼容: 保留原有函数名
const httpsGet = httpsGetWithProxy;

// ============================================================================
// 核心类: FixtureSeeder V4.46.6
// ============================================================================

class FixtureSeeder {
    constructor(options = {}) {
        const leagueConfig = loadLeagueConfig();

        this.config = {
            ...BASE_CONFIG,
            leagues: leagueConfig.active_leagues,
            seasons: leagueConfig.active_seasons,
            ...options
        };

        this.pool = null;

        // V4.46.6: 确定性请求 ID
        this.requestId = generateRequestId();
        log.setRequestId(this.requestId);

        // V4.46.6: MetricsClient
        this.metricsClient = getMetricsClient();

        // V4.46.6: NetworkShield
        this.networkShield = getNetworkShield();

        // 统计信息
        this.stats = {
            leagues: 0,
            fixtures: 0,
            inserted: 0,
            updated: 0,
            skipped: 0,
            errors: 0,
            batches: 0,
            parallelTasks: 0
        };

        // V4.46.6: 批量写入缓冲区
        this._batchBuffer = [];
        this._batchSize = this.config.batchSize || 50;
    }

    async init() {
        try {
            this.pool = new Pool(this.config.db);
            await this.pool.query('SELECT 1');
            log.info('V4.46.6 数据库连接已建立');
        } catch (error) {
            log.error('数据库连接失败', error);
            throw error;
        }
    }

    async close() {
        // 刷新剩余缓冲区
        await this._flushBatch();

        if (this.pool) {
            await this.pool.end();
            this.pool = null;
            log.info('数据库连接已关闭');
        }
    }

    /**
     * V4.46.6: 从 FotMob API 获取联赛赛程 (带代理支持)
     */
    async fetchLeagueFixtures(leagueId, season, workerId = 0) {
        const seasonParam = season.replace('/', '');
        const url = `https://www.fotmob.com/api/leagues?id=${leagueId}&season=${seasonParam}`;

        log.debug(`[Worker ${workerId}] 获取联赛 ${leagueId} 赛季 ${season}...`, { url });

        const startTime = Date.now();

        try {
            const response = await httpsGetWithProxy(url, {}, workerId);

            const duration = Date.now() - startTime;
            this._recordMetrics('fetch', duration, response.status === 200);

            if (response.status !== 200 || !response.data) {
                log.warn(`[Worker ${workerId}] 获取失败: HTTP ${response.status}`, { leagueId, season });
                return null;
            }

            return response.data;
        } catch (error) {
            const duration = Date.now() - startTime;
            this._recordMetrics('fetch', duration, false);
            log.error(`[Worker ${workerId}] 请求失败`, error);
            return null;
        }
    }

    parseFixtures(leagueData, leagueInfo, season) {
        const fixtures = [];

        const allMatches = leagueData?.fixtures?.allMatches ||
            leagueData?.overview?.matches?.allMatches ||
            [];

        if (!Array.isArray(allMatches) || allMatches.length === 0) {
            log.warn(`未找到 allMatches 数据`, { league: leagueInfo.name, season });
            return [];
        }

        log.info(`发现 ${allMatches.length} 场比赛`, { league: leagueInfo.name });

        let parseErrors = 0;
        for (const match of allMatches) {
            try {
                const fixture = this.parseMatch(match, leagueInfo, season);
                if (fixture) {
                    fixtures.push(fixture);
                }
            } catch (e) {
                parseErrors++;
                if (parseErrors <= 3) {
                    log.warn(`解析错误: ${e.message}`, { matchId: match?.id });
                }
            }
        }

        if (parseErrors > 0) {
            log.warn(`解析错误总数: ${parseErrors}`);
        }

        log.info(`成功解析: ${fixtures.length} 场`);

        return fixtures.filter(f => f && f.external_id);
    }

    /**
     * V4.46.6: 解析单场比赛 (使用 match_date 替代 match_time)
     */
    parseMatch(match, leagueInfo, season) {
        const externalId = match.id?.toString() || null;
        if (!externalId) {
            return null;
        }

        const homeTeam = match.home?.name || match.home?.shortName || null;
        const awayTeam = match.away?.name || match.away?.shortName || null;

        if (!homeTeam || !awayTeam) {
            return null;
        }

        const utcTime = match.status?.utcTime || match.time || null;
        const matchDate = utcTime ? new Date(utcTime) : null;

        // 提取比分
        let homeScore = null;
        let awayScore = null;

        if (match.status?.scoreStr) {
            const parts = match.status.scoreStr.split(/ - /);
            if (parts.length === 2) {
                const h = parseInt(parts[0].trim());
                const a = parseInt(parts[1].trim());
                if (!isNaN(h) && !isNaN(a)) {
                    homeScore = h;
                    awayScore = a;
                }
            }
        }

        if (homeScore === null && match.home?.score !== undefined) {
            homeScore = match.home.score;
            awayScore = match.away?.score ?? null;
        }

        const status = this.determineStatus(match, homeScore, awayScore);

        // V4.46.6: 确定性 match_id 格式
        const seasonTag = season.replace('/', '');
        const matchId = `${leagueInfo.id}_${seasonTag}_${externalId}`;

        return {
            match_id: matchId,
            external_id: externalId,
            league_name: leagueInfo.name,
            season: season,
            home_team: homeTeam,
            away_team: awayTeam,
            match_date: matchDate,  // V4.46.6: 使用 match_date
            home_score: homeScore,
            away_score: awayScore,
            status: status,
            data_source: 'FotMob'
        };
    }

    /**
     * V4.46.6: 增强状态判断 (含 POSTPONED 支持)
     */
    determineStatus(match, homeScore, awayScore) {
        const status = match.status;

        if (typeof status === 'object' && status !== null) {
            // V4.46.6: 优先检查 POSTPONED
            if (status.postponed) return STATUS_POSTPONED || 'postponed';
            if (status.cancelled) return STATUS_CANCELLED;
            if (status.awarded) return 'awarded';
            if (status.finished) return STATUS_FINISHED;
            if (status.started) return STATUS_LIVE;
        }

        if (homeScore !== null && awayScore !== null) {
            return STATUS_FINISHED;
        }

        return STATUS_SCHEDULED;
    }

    // ========================================================================
    // V4.46.6: 批量 UPSERT 优化
    // ========================================================================

    /**
     * V4.46.6: 添加到批量缓冲区
     */
    async addToBatch(fixture) {
        this._batchBuffer.push(fixture);

        if (this._batchBuffer.length >= this._batchSize) {
            await this._flushBatch();
        }
    }

    /**
     * V4.46.6: 批量刷新写入
     */
    async _flushBatch() {
        if (this._batchBuffer.length === 0) return;

        const batch = [...this._batchBuffer];
        this._batchBuffer = [];

        const startTime = Date.now();

        try {
            // 构建批量 VALUES 子句
            const valueGroups = [];
            const flatValues = [];
            let paramIndex = 1;

            for (const fixture of batch) {
                const placeholders = [];
                const values = [
                    fixture.match_id,
                    fixture.external_id,
                    fixture.league_name,
                    fixture.season,
                    fixture.home_team,
                    fixture.away_team,
                    fixture.match_date,
                    fixture.home_score,
                    fixture.away_score,
                    fixture.status,
                    fixture.data_source
                ];

                for (const val of values) {
                    flatValues.push(val);
                    placeholders.push(`$${paramIndex}`);
                    paramIndex++;
                }

                valueGroups.push(`(${placeholders.join(', ')})`);
            }

            const query = `
                INSERT INTO matches (
                    match_id, external_id, league_name, season,
                    home_team, away_team, match_date,
                    home_score, away_score, status, data_source,
                    created_at, updated_at
                ) VALUES ${valueGroups.join(', ')}
                ON CONFLICT (match_id)
                DO UPDATE SET
                    external_id = EXCLUDED.external_id,
                    home_score = COALESCE(EXCLUDED.home_score, matches.home_score),
                    away_score = COALESCE(EXCLUDED.away_score, matches.away_score),
                    status = EXCLUDED.status,
                    updated_at = NOW()
            `;

            await this.pool.query(query, flatValues);

            this.stats.inserted += batch.length;
            this.stats.batches++;

            const duration = Date.now() - startTime;
            this._recordMetrics('batch_write', duration, true);

            log.debug(`批量写入成功: ${batch.length} 条记录 (${duration}ms)`);

        } catch (error) {
            log.error(`批量写入失败，回退逐条写入`, error);
            this.stats.errors++;

            // 回退: 逐条写入
            for (const fixture of batch) {
                await this.upsertFixture(fixture);
            }
        }
    }

    /**
     * 单条 UPSERT (回退方案)
     */
    async upsertFixture(fixture) {
        const query = `
            INSERT INTO matches (
                match_id, external_id, league_name, season,
                home_team, away_team, match_date,
                home_score, away_score, status, data_source,
                created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, NOW(), NOW())
            ON CONFLICT (match_id)
            DO UPDATE SET
                external_id = EXCLUDED.external_id,
                home_score = COALESCE(EXCLUDED.home_score, matches.home_score),
                away_score = COALESCE(EXCLUDED.away_score, matches.away_score),
                status = EXCLUDED.status,
                updated_at = NOW()
            RETURNING (xmax = 0) AS inserted
        `;

        const values = [
            fixture.match_id,
            fixture.external_id,
            fixture.league_name,
            fixture.season,
            fixture.home_team,
            fixture.away_team,
            fixture.match_date,
            fixture.home_score,
            fixture.away_score,
            fixture.status,
            fixture.data_source
        ];

        try {
            const result = await this.pool.query(query, values);
            if (result.rows[0]?.inserted) {
                this.stats.inserted++;
            } else {
                this.stats.updated++;
            }
            return true;
        } catch (error) {
            log.error(`UPSERT 失败: ${fixture.match_id}`, error);
            this.stats.errors++;
            return false;
        }
    }

    /**
     * V4.46.6: 并行处理单个联赛-赛季
     */
    async processLeagueSeason(league, season, workerId = 0) {
        log.info(`[Worker ${workerId}] 处理: ${league.name} (ID: ${league.id}) - ${season}`);

        const leagueData = await this.fetchLeagueFixtures(league.id, season, workerId);

        if (!leagueData) {
            log.warn(`[Worker ${workerId}] 跳过 ${league.name} - ${season}: 无数据`);
            return { fixtures: 0, success: false };
        }

        const fixtures = this.parseFixtures(leagueData, league, season);
        log.info(`[Worker ${workerId}] 发现 ${fixtures.length} 场比赛`);

        // V4.46.6: 批量写入
        for (const fixture of fixtures) {
            await this.addToBatch(fixture);
            this.stats.fixtures++;
        }

        // 记录 L1 发现指标
        this._recordMetrics('discovery', 0, true);

        log.success(`[Worker ${workerId}] ${league.name} - ${season}: ${fixtures.length} 场已处理`);

        return { fixtures: fixtures.length, success: true };
    }

    /**
     * V4.46.6: 并行执行全量收割
     */
    async seedAll() {
        log.info('═══════════════════════════════════════════════════════════════');
        log.info('V4.46.6 Fixture Seeder 启动 (工业级并行模式)');
        log.info(`请求 ID: ${this.requestId}`);
        log.info(`目标联赛: ${this.config.leagues.length} 个`);
        log.info(`目标赛季: ${this.config.seasons.join(', ')}`);
        log.info(`并发数: ${this.config.concurrency}`);
        log.info(`批量大小: ${this._batchSize}`);
        log.info('═══════════════════════════════════════════════════════════════');

        if (this.config.leagues.length === 0) {
            log.warn('没有配置活跃联赛，任务终止');
            return this.stats;
        }

        const startTime = Date.now();

        // 构建任务列表
        const tasks = [];
        for (const league of this.config.leagues) {
            for (const season of this.config.seasons) {
                tasks.push({ league, season });
            }
        }

        this.stats.leagues = tasks.length;
        log.info(`总任务数: ${tasks.length} 个联赛-赛季组合`);

        // V4.46.6: 并行执行
        const concurrency = this.config.concurrency;
        const results = [];

        for (let i = 0; i < tasks.length; i += concurrency) {
            const batch = tasks.slice(i, i + concurrency);
            this.stats.parallelTasks++;

            log.info(`并行批次 #${this.stats.parallelTasks}: 处理 ${batch.length} 个任务`);

            const batchPromises = batch.map((task, idx) =>
                this.processLeagueSeason(task.league, task.season, idx)
            );

            const batchResults = await Promise.allSettled(batchPromises);

            batchResults.forEach((result, idx) => {
                if (result.status === 'fulfilled') {
                    results.push(result.value);
                } else {
                    log.error(`任务失败`, result.reason);
                    this.stats.errors++;
                }
            });

            // 批次间延时 (避免 API 限流)
            if (i + concurrency < tasks.length) {
                await this.sleep(this.config.delay);
            }
        }

        // 刷新剩余缓冲区
        await this._flushBatch();

        const duration = Date.now() - startTime;

        log.info('═══════════════════════════════════════════════════════════════');
        log.success('V4.46.6 赛程收割完成!');
        log.info('统计', {
            leagues: this.stats.leagues,
            fixtures: this.stats.fixtures,
            inserted: this.stats.inserted,
            updated: this.stats.updated,
            errors: this.stats.errors,
            batches: this.stats.batches,
            parallelBatches: this.stats.parallelTasks,
            durationMs: duration,
            throughput: `${(this.stats.fixtures / (duration / 1000)).toFixed(2)} 场/秒`
        });
        log.info('═══════════════════════════════════════════════════════════════');

        // V4.46.6: 最终指标上报
        this._recordMetrics('complete', duration, true);

        return this.stats;
    }

    /**
     * V4.46.6: 记录指标到 MetricsClient
     */
    _recordMetrics(operation, durationMs, success) {
        try {
            if (operation === 'discovery') {
                // L1 发现计数
                if (this.metricsClient?.recordL1Discovery) {
                    this.metricsClient.recordL1Discovery(1);
                }
            } else if (operation === 'fetch') {
                // HTTP 请求耗时
                if (this.metricsClient?.recordL1FetchDuration) {
                    this.metricsClient.recordL1FetchDuration(durationMs);
                }
            } else if (operation === 'batch_write') {
                // 批量写入耗时
                if (this.metricsClient?.recordL1BatchWrite) {
                    this.metricsClient.recordL1BatchWrite(durationMs, this._batchSize);
                }
            } else if (operation === 'complete') {
                // 完成统计
                if (this.metricsClient?.recordL1Complete) {
                    this.metricsClient.recordL1Complete(this.stats);
                }
            }
        } catch (e) {
            log.debug(`指标记录失败: ${e.message}`);
        }
    }

    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    getSummary() {
        const total = this.stats.fixtures;
        const success = this.stats.inserted + this.stats.updated;
        const errors = this.stats.errors;

        const successRate = total > 0 ? ((success / total) * 100).toFixed(2) : '0.00';

        let status;
        if (total === 0) {
            status = 'empty';
        } else if (parseFloat(successRate) >= 99) {
            status = 'success';
        } else if (parseFloat(successRate) >= 95) {
            status = 'warning';
        } else {
            status = 'failed';
        }

        return {
            total,
            inserted: this.stats.inserted,
            updated: this.stats.updated,
            errors,
            success_rate: parseFloat(successRate),
            status,
            leagues: this.stats.leagues,
            batches: this.stats.batches,
            parallelBatches: this.stats.parallelTasks,
            timestamp: new Date().toISOString(),
            requestId: this.requestId,
            version: 'V4.46.6'
        };
    }
}

// ============================================================================
// 导出
// ============================================================================

module.exports = {
    FixtureSeeder,
    Logger,
    LogLevel,
    loadLeagueConfig,
    // V4.46.6: 删除原有的 generateRequestId (使用 id_generator)
    CONFIG: BASE_CONFIG,
    // V4.46.6: 导出代理感知 HTTP 工具
    httpsGet: httpsGetWithProxy
};
