/**
 * @file FixtureSeeder - L1 发现层核心模块 V6.4
 *
 * 工业级重构版本：
 * - 批量 UPSERT (每 50 场写入一次)
 * - 并行扫描 (可配置并发数)
 * - MetricsClient 可观测性
 * - V6.4: 集成 MatchValidator 三道铁门、熔断机制、连接池
 * @module infrastructure/FixtureSeeder
 * @version V6.4
 */

'use strict';

const https = require('https');
const { URL } = require('url');
const { Pool } = require('pg');
const path = require('path');
const fs = require('fs');

// V5.0: 核心组件集成
const { threeGatesFilter } = require('../core/validation/MatchValidator');
const { getMetricsClient } = require('./monitoring/MetricsClient');
const FactoryConfig = require('../../config/factory_config');

// V6.6: 引入共享 Normalizer 工具类
const { Normalizer } = require('../utils/Normalizer');

require('dotenv').config({ path: path.resolve(__dirname, '../../.env') });

// 生成请求ID
function generateRequestId() {
  return `req-${Date.now()}-${Math.random().toString(36).substring(2, 8)}`;
}

// ============================================================================
// 精简日志系统
// ============================================================================

class Logger {
    constructor(module, requestId = null) {
        this.module = module;
        this.requestId = requestId;
    }
    setRequestId(id) { this.requestId = id; }
    _format(level, message, meta = null) {
        const ts = new Date().toISOString();
        const req = this.requestId ? `[${this.requestId}] ` : '';
        const m = meta ? ` | ${JSON.stringify(meta)}` : '';
        return `[${ts}] [${level}] [${this.module}] ${req}${message}${m}`;
    }
    info(m, meta) { console.log(this._format('INFO', m, meta)); }
    warn(m, meta) { console.warn(this._format('WARN', m, meta)); }
    error(m, err) { console.error(this._format('ERROR', m, err ? { error: err.message } : null)); }
    success(m, meta) { console.log(this._format('SUCCESS', m, meta)); }
    debug(m, meta) { if (process.env.LOG_LEVEL === 'debug') console.log(this._format('DEBUG', m, meta)); }
}

const log = new Logger('FixtureSeeder');

// ============================================================================
// 配置加载
// ============================================================================

function loadLeagueConfig() {
    const configPath = path.resolve(__dirname, '../../config/leagues.json');
    try {
        if (!fs.existsSync(configPath)) throw new Error('Config not found');
        const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
        return {
            active_leagues: config.active_leagues.filter(l => l.enabled !== false),
            active_seasons: config.active_seasons || ['2024/2025']
        };
    } catch (e) {
        log.warn('配置加载失败，使用默认配置');
        return {
            active_leagues: [{ id: 47, name: 'Premier League', enabled: true }],
            active_seasons: ['2024/2025']
        };
    }
}

const BASE_CONFIG = {
    fotmob: { baseUrl: 'www.fotmob.com', timeout: 20000 },
    db: {
        host: process.env.DB_HOST || 'localhost',
        port: parseInt(process.env.DB_PORT || '5432'),
        database: process.env.DB_NAME || 'football_db',
        user: process.env.DB_USER || 'football_user',
        password: process.env.DB_PASSWORD || '',
        // V6.4: 连接池工业级保护参数
        max: 20,                           // 最大连接数
        idleTimeoutMillis: 30000,          // 空闲连接30秒释放
        connectionTimeoutMillis: 5000,     // 连接超时5秒
        application_name: 'fixture_seeder_v5'
    },
    delay: FactoryConfig.TIMING?.minDelayMs || 2000,
    batchSize: parseInt(process.env.L1_BATCH_SIZE) || 50,
    concurrency: parseInt(process.env.L1_CONCURRENCY) || 5,
    // V6.4: 熔断机制配置
    circuitBreaker: {
        failureThreshold: 5,               // 连续失败5次触发熔断
        resetTimeoutMs: 300000             // 5分钟后尝试恢复
    }
};

// ============================================================================
// HTTP 请求工具
// ============================================================================

async function httpsGet(url, options = {}, workerId = 0) {
    return new Promise((resolve, reject) => {
        const parsed = new URL(url);
        const opts = {
            hostname: parsed.hostname,
            port: parsed.port || 443,
            path: parsed.pathname + parsed.search,
            method: 'GET',
            timeout: options.timeout || BASE_CONFIG.fotmob.timeout,
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0.36',
                'Accept': 'application/json',
                ...options.headers
            }
        };

        const req = https.request(opts, (res) => {
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
                    resolve({ status: res.statusCode, data: null, raw: data });
                }
            });
        });

        req.on('error', reject);
        req.setTimeout(opts.timeout, () => { req.destroy(); reject(new Error('Timeout')); });
        req.end();
    });
}

// ============================================================================
// 核心类: FixtureSeeder V5.0
// ============================================================================

class FixtureSeeder {
    constructor(options = {}) {
        const leagueConfig = loadLeagueConfig();
        this.config = { ...BASE_CONFIG, leagues: leagueConfig.active_leagues, seasons: leagueConfig.active_seasons, ...options };
        this.rejectionStats = { wrongLeague: 0, outsideWindow: 0, placeholder: 0, invalidData: 0 };
        this.strictMode = options.strictMode !== false;
        this.pool = null;
        this.requestId = generateRequestId();
        log.setRequestId(this.requestId);
        this.metricsClient = getMetricsClient();
        this.stats = { leagues: 0, fixtures: 0, inserted: 0, updated: 0, skipped: 0, errors: 0, batches: 0, parallelTasks: 0 };
        this._batchBuffer = [];
        this._batchSize = this.config.batchSize || 50;
        
        // V6.4: 熔断机制状态
        this._consecutiveFailures = 0;
        this._circuitBreakerOpen = false;
        this._circuitBreakerOpenedAt = null;
    }

    async init() {
        try {
            this.pool = new Pool(this.config.db);
            await this.pool.query('SELECT 1');
            log.info('数据库连接已建立');
        } catch (error) {
            log.error('数据库连接失败', error);
            throw error;
        }
    }

    async close() {
        await this._flushBatch();
        if (this.pool) {
            await this.pool.end();
            this.pool = null;
            log.info('数据库连接已关闭');
        }
    }

    async fetchLeagueFixtures(leagueId, season, workerId = 0) {
        // V6.4: 熔断机制检查
        if (this._circuitBreakerOpen) {
            const elapsed = Date.now() - this._circuitBreakerOpenedAt;
            if (elapsed < this.config.circuitBreaker.resetTimeoutMs) {
                const remaining = Math.ceil((this.config.circuitBreaker.resetTimeoutMs - elapsed) / 1000);
                log.error(`🚨 CIRCUIT BREAKER TRIGGERED - API请求被熔断，${remaining}秒后恢复`);
                throw new Error(`Circuit breaker open - retry after ${remaining}s`);
            }
            // 超过重置时间，尝试关闭熔断器
            log.warn(`🔄 熔断器超时，尝试恢复...`);
            this._circuitBreakerOpen = false;
            this._consecutiveFailures = 0;
        }

        // V6.3: FotMob API 赛季参数格式适配
        const seasonFormats = [
            season,                    // 2024/2025 (原始格式)
            season.replace('/', ''),   // 20242025 (无斜杠)
            season.replace('/', '-')   // 2024-2025 (短横线)
        ];

        let lastError = null;
        for (const seasonParam of seasonFormats) {
            const url = `https://www.fotmob.com/api/leagues?id=${leagueId}&season=${encodeURIComponent(seasonParam)}`;
            log.debug(`[Worker ${workerId}] 尝试获取联赛 ${leagueId} 赛季 ${seasonParam}...`);

            const startTime = Date.now();
            try {
                const response = await httpsGet(url, {}, workerId);
                this._recordMetrics('fetch', Date.now() - startTime, response.status === 200);

                if (response.status === 200 && response.data) {
                    // 成功，重置失败计数
                    this._consecutiveFailures = 0;
                    
                    // 验证返回的数据是否匹配请求的赛季
                    const returnedSeason = response.data.details?.season || response.data.season || seasonParam;
                    log.info(`[Worker ${workerId}] 成功获取 ${leagueId} 数据`, {
                        requestedSeason: season,
                        returnedSeason: returnedSeason,
                        matchesCount: response.data.fixtures?.allMatches?.length || 0
                    });
                    return response.data;
                }
            } catch (error) {
                lastError = error;
                log.debug(`[Worker ${workerId}] 格式 ${seasonParam} 失败: ${error.message}`);
            }
        }

        // V6.4: 所有格式失败，增加失败计数
        this._consecutiveFailures++;
        log.error(`[Worker ${workerId}] 所有赛季格式尝试失败 (连续失败 ${this._consecutiveFailures}/${this.config.circuitBreaker.failureThreshold})`, lastError);

        // 检查是否触发熔断
        if (this._consecutiveFailures >= this.config.circuitBreaker.failureThreshold) {
            this._circuitBreakerOpen = true;
            this._circuitBreakerOpenedAt = Date.now();
            log.error(`🚨 CIRCUIT BREAKER TRIGGERED - 连续 ${this._consecutiveFailures} 次API调用失败，熔断器已打开`);
            throw new Error(`Circuit breaker triggered after ${this._consecutiveFailures} consecutive failures`);
        }

        return null;
    }

    parseFixtures(leagueData, leagueInfo, season) {
        let allMatches = leagueData?.fixtures?.allMatches || leagueData?.overview?.matches?.allMatches || [];
        if (!Array.isArray(allMatches) || allMatches.length === 0) {
            log.warn(`未找到 allMatches 数据`, { league: leagueInfo.name });
            return [];
        }

        log.info(`API 返回 ${allMatches.length} 场比赛`, { league: leagueInfo.name });

        // V5.0: 三道铁门数据过滤
        if (this.strictMode) {
            log.info('🛡️ 启动三道铁门数据过滤...');
            const beforeCount = allMatches.length;
            allMatches = threeGatesFilter(allMatches, leagueInfo, season, this.rejectionStats, log);
            const afterCount = allMatches.length;
            log.info(`🛡️ 铁门过滤完成: ${beforeCount} → ${afterCount} 场 (${((afterCount/beforeCount)*100).toFixed(1)}% 通过率)`);
            if (leagueInfo.id === 47 && Math.abs(afterCount - 380) > 20) {
                log.warn(`⚠️ 过滤后比赛数量(${afterCount})与英超应有场数(380)偏差超过20场`);
            }
        }

        const fixtures = [];
        let parseErrors = 0;
        for (const match of allMatches) {
            try {
                const fixture = this.parseMatch(match, leagueInfo, season);
                if (fixture) fixtures.push(fixture);
            } catch (e) {
                parseErrors++;
                if (parseErrors <= 3) log.warn(`解析错误: ${e.message}`);
            }
        }
        if (parseErrors > 0) log.warn(`解析错误总数: ${parseErrors}`);
        log.info(`成功解析: ${fixtures.length} 场`);
        return fixtures.filter(f => f && f.external_id);
    }

    // V6.6: normalizeSeason 方法已迁移至共享 Normalizer 工具类
    // 使用: Normalizer.normalizeSeason(season)

    parseMatch(match, leagueInfo, season) {
        const externalId = match.id?.toString();
        if (!externalId) return null;

        const homeTeam = match.home?.name || match.home?.shortName;
        const awayTeam = match.away?.name || match.away?.shortName;
        if (!homeTeam || !awayTeam) return null;

        // V6.0: 智能时间戳解析
        let matchDate = null;
        const rawTime = match.status?.utcTime || match.time || match.timestamp || match.status?.startTime;
        if (rawTime) {
            try {
                if (typeof rawTime === 'number' || /^\d+$/.test(String(rawTime))) {
                    const num = parseInt(rawTime, 10);
                    matchDate = new Date(num > 1000000000000 ? num : num * 1000);
                } else {
                    matchDate = new Date(rawTime);
                }
                if (isNaN(matchDate.getTime())) matchDate = null;
            } catch (e) {
                matchDate = null;
            }
        }

        let homeScore = null, awayScore = null;
        if (match.status?.scoreStr) {
            const parts = match.status.scoreStr.split(/ - /);
            if (parts.length === 2) {
                const h = parseInt(parts[0].trim());
                const a = parseInt(parts[1].trim());
                if (!isNaN(h) && !isNaN(a)) { homeScore = h; awayScore = a; }
            }
        }
        if (homeScore === null && match.home?.score !== undefined) {
            homeScore = match.home.score;
            awayScore = match.away?.score ?? null;
        }

        const status = this.determineStatus(match, homeScore, awayScore);

        // V6.5: 强制转换赛季格式为标准格式
        const normalizedSeason = Normalizer.normalizeSeason(season);
        const seasonTag = normalizedSeason.replace('/', '');
        const matchId = `${leagueInfo.id}_${seasonTag}_${externalId}`;

        // V6.5: 同步计算 is_finished 字段
        const isFinished = status === 'finished';

        return {
            match_id: matchId,
            external_id: externalId,
            league_name: leagueInfo.name,
            season: normalizedSeason,        // ✅ 使用规范化赛季
            home_team: homeTeam,
            away_team: awayTeam,
            match_date: matchDate,
            home_score: homeScore,
            away_score: awayScore,
            status: status,                  // ✅ 已小写归一化
            is_finished: isFinished,         // ✅ V6.5 新增：与 status 同步
            data_source: 'FotMob'
        };
    }

    /**
     * 确定比赛状态 - V6.5 修复版
     * 返回标准化的全小写状态
     * @param {Object} match - FotMob 原始比赛对象
     * @param {number|null} homeScore - 主队比分
     * @param {number|null} awayScore - 客队比分
     * @returns {string} 标准化状态 (全小写)
     */
    determineStatus(match, homeScore, awayScore) {
        const status = match.status;
        let result = 'scheduled';

        if (typeof status === 'object' && status !== null) {
            if (status.postponed) result = 'postponed';
            else if (status.cancelled) result = 'cancelled';
            else if (status.awarded) result = 'awarded';
            else if (status.finished) result = 'finished';
            else if (status.started) result = 'live';
        } else if (homeScore !== null && awayScore !== null) {
            result = 'finished';
        }

        // V6.5: 强制小写归一化
        return result.toLowerCase();
    }

    async addToBatch(fixture) {
        this._batchBuffer.push(fixture);
        if (this._batchBuffer.length >= this._batchSize) await this._flushBatch();
    }

    async _flushBatch() {
        if (this._batchBuffer.length === 0) return;
        const batch = [...this._batchBuffer];
        this._batchBuffer = [];
        const startTime = Date.now();

        try {
            const valueGroups = [];
            const flatValues = [];
            let paramIndex = 1;

            for (const fixture of batch) {
                const placeholders = [];
                const values = [
                    fixture.match_id, fixture.external_id, fixture.league_name, fixture.season,
                    fixture.home_team, fixture.away_team, fixture.match_date,
                    fixture.home_score, fixture.away_score, fixture.status, fixture.is_finished, fixture.data_source
                ];
                for (const val of values) {
                    flatValues.push(val);
                    placeholders.push(`$${paramIndex++}`);
                }
                valueGroups.push(`(${placeholders.join(', ')})`);
            }

            const query = `
                INSERT INTO matches (match_id, external_id, league_name, season, home_team, away_team,
                    match_date, home_score, away_score, status, is_finished, data_source)
                VALUES ${valueGroups.join(', ')}
                ON CONFLICT (match_id) DO UPDATE SET
                    external_id = EXCLUDED.external_id,
                    home_score = COALESCE(EXCLUDED.home_score, matches.home_score),
                    away_score = COALESCE(EXCLUDED.away_score, matches.away_score),
                    status = EXCLUDED.status,
                    is_finished = EXCLUDED.is_finished,
                    updated_at = NOW()
            `;

            await this.pool.query(query, flatValues);
            this.stats.inserted += batch.length;
            this.stats.batches++;
            this._recordMetrics('batch_write', Date.now() - startTime, true);
            log.debug(`批量写入成功: ${batch.length} 条记录`);
        } catch (error) {
            log.error(`批量写入失败，回退逐条写入`, error);
            this.stats.errors++;
            for (const fixture of batch) await this.upsertFixture(fixture);
        }
    }

    async upsertFixture(fixture) {
        const query = `
            INSERT INTO matches (match_id, external_id, league_name, season, home_team, away_team,
                match_date, home_score, away_score, status, is_finished, data_source, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW(), NOW())
            ON CONFLICT (match_id) DO UPDATE SET
                external_id = EXCLUDED.external_id,
                home_score = COALESCE(EXCLUDED.home_score, matches.home_score),
                away_score = COALESCE(EXCLUDED.away_score, matches.away_score),
                status = EXCLUDED.status,
                is_finished = EXCLUDED.is_finished,
                updated_at = NOW()
            RETURNING (xmax = 0) AS inserted
        `;
        const values = [fixture.match_id, fixture.external_id, fixture.league_name, fixture.season,
            fixture.home_team, fixture.away_team, fixture.match_date, fixture.home_score,
            fixture.away_score, fixture.status, fixture.is_finished, fixture.data_source];
        try {
            const result = await this.pool.query(query, values);
            if (result.rows[0]?.inserted) this.stats.inserted++;
            else this.stats.updated++;
            return true;
        } catch (error) {
            log.error(`UPSERT 失败: ${fixture.match_id}`, error);
            this.stats.errors++;
            return false;
        }
    }

    async processLeagueSeason(league, season, workerId = 0) {
        log.info(`[Worker ${workerId}] 处理: ${league.name} - ${season}`);
        const leagueData = await this.fetchLeagueFixtures(league.id, season, workerId);
        if (!leagueData) {
            log.warn(`[Worker ${workerId}] 跳过 ${league.name}: 无数据`);
            return { fixtures: 0, success: false };
        }

        const fixtures = this.parseFixtures(leagueData, league, season);
        log.info(`[Worker ${workerId}] 发现 ${fixtures.length} 场比赛`);

        for (const fixture of fixtures) {
            await this.addToBatch(fixture);
            this.stats.fixtures++;
        }
        this._recordMetrics('discovery', 0, true);
        log.success(`[Worker ${workerId}] ${league.name}: ${fixtures.length} 场已处理`);
        return { fixtures: fixtures.length, success: true };
    }

    async seedAll() {
        log.info('═══════════════════════════════════════════════════════════════');
        log.info('V5.0 Fixture Seeder 启动');
        log.info(`请求 ID: ${this.requestId}`);
        log.info(`目标联赛: ${this.config.leagues.length} 个`);
        log.info(`目标赛季: ${this.config.seasons.join(', ')}`);
        log.info(`并发数: ${this.config.concurrency}`);
        log.info('═══════════════════════════════════════════════════════════════');

        if (this.config.leagues.length === 0) {
            log.warn('没有配置活跃联赛，任务终止');
            return this.stats;
        }

        const startTime = Date.now();
        const tasks = [];
        for (const league of this.config.leagues) {
            for (const season of this.config.seasons) tasks.push({ league, season });
        }
        this.stats.leagues = tasks.length;
        log.info(`总任务数: ${tasks.length} 个联赛-赛季组合`);

        const concurrency = this.config.concurrency;
        for (let i = 0; i < tasks.length; i += concurrency) {
            const batch = tasks.slice(i, i + concurrency);
            this.stats.parallelTasks++;
            log.info(`并行批次 #${this.stats.parallelTasks}: 处理 ${batch.length} 个任务`);

            const batchPromises = batch.map((task, idx) =>
                this.processLeagueSeason(task.league, task.season, idx)
            );
            const results = await Promise.allSettled(batchPromises);
            results.forEach((result) => {
                if (result.status === 'rejected') {
                    log.error(`任务失败`, result.reason);
                    this.stats.errors++;
                }
            });

            if (i + concurrency < tasks.length) await this.sleep(this.config.delay);
        }

        await this._flushBatch();
        const duration = Date.now() - startTime;

        log.info('═══════════════════════════════════════════════════════════════');
        log.success('V5.0 赛程收割完成!');
        log.info('统计', {
            leagues: this.stats.leagues,
            fixtures: this.stats.fixtures,
            inserted: this.stats.inserted,
            updated: this.stats.updated,
            errors: this.stats.errors,
            batches: this.stats.batches,
            durationMs: duration,
            throughput: `${(this.stats.fixtures / (duration / 1000)).toFixed(2)} 场/秒`
        });
        log.info('🛡️ 三道铁门拦截统计:', this.rejectionStats);
        log.info('═══════════════════════════════════════════════════════════════');

        this._recordMetrics('complete', duration, true);
        return this.stats;
    }

    _recordMetrics(operation, durationMs, success) {
        try {
            if (operation === 'discovery' && this.metricsClient?.recordL1Discovery) {
                this.metricsClient.recordL1Discovery(1);
            } else if (operation === 'fetch' && this.metricsClient?.recordL1FetchDuration) {
                this.metricsClient.recordL1FetchDuration(durationMs);
            } else if (operation === 'batch_write' && this.metricsClient?.recordL1BatchWrite) {
                this.metricsClient.recordL1BatchWrite(durationMs, this._batchSize);
            } else if (operation === 'complete' && this.metricsClient?.recordL1Complete) {
                this.metricsClient.recordL1Complete(this.stats);
            }
        } catch (e) {
            // 静默失败
        }
    }

    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    getSummary() {
        const total = this.stats.fixtures;
        const success = this.stats.inserted + this.stats.updated;
        const successRate = total > 0 ? ((success / total) * 100).toFixed(2) : '0.00';
        return {
            total,
            inserted: this.stats.inserted,
            updated: this.stats.updated,
            errors: this.stats.errors,
            success_rate: parseFloat(successRate),
            status: parseFloat(successRate) >= 99 ? 'success' : parseFloat(successRate) >= 95 ? 'warning' : 'failed',
            timestamp: new Date().toISOString(),
            requestId: this.requestId,
            version: 'V5.0'
        };
    }
}

module.exports = { FixtureSeeder, Logger, loadLeagueConfig, CONFIG: BASE_CONFIG };