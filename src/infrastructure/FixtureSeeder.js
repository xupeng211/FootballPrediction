/**
 * @fileoverview FixtureSeeder - L1 发现层核心模块
 *
 * 从 FotMob 联赛 API 批量获取历史赛程数据，是三层架构中 L1 层的唯一实现。
 *
 * @module infrastructure/FixtureSeeder
 * @version V178.0.0
 * @author FootballPrediction Engineering Team
 *
 * @example
 * // 基本用法
 * const { FixtureSeeder } = require('./src/infrastructure/FixtureSeeder');
 *
 * const seeder = new FixtureSeeder();
 * await seeder.init();
 * const stats = await seeder.seedAll();
 * await seeder.close();
 *
 * @example
 * // 自定义配置
 * const seeder = new FixtureSeeder({
 *   leagues: [{ id: 47, name: 'Premier League', country: 'England' }],
 *   seasons: ['2024/2025']
 * });
 */

'use strict';

const https = require('https');
const { Pool } = require('pg');
const path = require('path');
const fs = require('fs');

require('dotenv').config({ path: path.resolve(__dirname, '../../.env') });

// ============================================================================
// 日志系统 (工业级分级)
// ============================================================================

/**
 * 日志级别枚举
 * @enum {string}
 */
const LogLevel = {
    /** 常规信息 */
    INFO: 'INFO',
    /** 警告信息 */
    WARN: 'WARN',
    /** 错误信息 */
    ERROR: 'ERROR',
    /** 成功信息 */
    SUCCESS: 'SUCCESS'
};

/**
 * 生成唯一请求 ID
 * @returns {string} 格式: req_xxxxxxxxxxxxxxxx
 */
function generateRequestId() {
    const timestamp = Date.now().toString(36);
    const random = Math.random().toString(36).substring(2, 8);
    return `req_${timestamp}_${random}`;
}

/**
 * 工业级日志记录器
 *
 * @class Logger
 * @example
 * const log = new Logger('MyModule');
 * log.info('操作开始');
 * log.error('操作失败', new Error('连接超时'));
 */
class Logger {
    /**
     * 创建日志记录器实例
     * @param {string} module - 模块名称，用于标识日志来源
     * @param {string|null} [requestId=null] - 请求追踪 ID
     */
    constructor(module, requestId = null) {
        /** @type {string} */
        this.module = module;
        /** @type {string|null} */
        this.requestId = requestId;
    }

    /**
     * 设置请求 ID（用于任务级别的追踪）
     * @param {string} requestId - 请求 ID
     */
    setRequestId(requestId) {
        this.requestId = requestId;
    }

    /**
     * 格式化日志消息
     * @private
     * @param {string} level - 日志级别
     * @param {string} message - 日志消息
     * @param {Object|null} meta - 元数据
     * @returns {string} 格式化后的日志字符串
     */
    _format(level, message, meta = null) {
        const timestamp = new Date().toISOString();
        const reqIdStr = this.requestId ? `[${this.requestId}] ` : '';
        const metaStr = meta ? ` | ${JSON.stringify(meta)}` : '';
        return `[${timestamp}] [${level}] [${this.module}] ${reqIdStr}${message}${metaStr}`;
    }

    /**
     * 记录 INFO 级别日志
     * @param {string} message - 日志消息
     * @param {Object|null} [meta=null] - 附加元数据
     */
    info(message, meta = null) {
        console.log(this._format(LogLevel.INFO, message, meta));
    }

    /**
     * 记录 WARN 级别日志
     * @param {string} message - 日志消息
     * @param {Object|null} [meta=null] - 附加元数据
     */
    warn(message, meta = null) {
        console.warn(this._format(LogLevel.WARN, message, meta));
    }

    /**
     * 记录 ERROR 级别日志（包含堆栈追踪和 request_id）
     * @param {string} message - 日志消息
     * @param {Error|null} [error=null] - 错误对象，将自动提取 message 和 stack
     */
    error(message, error = null) {
        const meta = error ? {
            request_id: this.requestId || 'unknown',
            error: error.message,
            stack: error.stack
        } : { request_id: this.requestId || 'unknown' };
        console.error(this._format(LogLevel.ERROR, message, meta));
    }

    /**
     * 记录 SUCCESS 级别日志
     * @param {string} message - 日志消息
     * @param {Object|null} [meta=null] - 附加元数据
     */
    success(message, meta = null) {
        console.log(this._format(LogLevel.SUCCESS, message, meta));
    }
}

const log = new Logger('FixtureSeeder');

// ============================================================================
// 配置加载器
// ============================================================================

/**
 * @typedef {Object} LeagueConfig
 * @property {number} id - 联赛 ID（FotMob 格式）
 * @property {string} name - 联赛名称
 * @property {string} country - 所属国家
 * @property {boolean} [enabled=true] - 是否启用
 */

/**
 * @typedef {Object} LeagueConfigFile
 * @property {string} version - 配置版本
 * @property {LeagueConfig[]} active_leagues - 活跃联赛列表
 * @property {LeagueConfig[]} inactive_leagues - 非活跃联赛列表
 * @property {string[]} active_seasons - 活跃赛季列表
 */

/**
 * 从配置文件加载联赛配置
 *
 * @function loadLeagueConfig
 * @returns {Object} 包含 active_leagues 和 active_seasons 的配置对象
 * @example
 * const config = loadLeagueConfig();
 * console.log(config.active_leagues); // [{ id: 47, name: 'Premier League', ... }]
 */
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

        // 只加载 enabled=true 的联赛
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
// 基础配置
// ============================================================================

/**
 * 基础配置对象
 * @constant {Object}
 */
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
    delay: 2000
};

// ============================================================================
// HTTP 工具
// ============================================================================

/**
 * HTTP GET 请求封装
 *
 * @async
 * @function httpsGet
 * @param {string} url - 请求 URL
 * @param {Object} [options={}] - 请求选项
 * @param {number} [options.timeout] - 超时时间（毫秒）
 * @returns {Promise<{status: number, data: Object|null, raw: string}>} 响应对象
 */
async function httpsGet(url, options = {}) {
    return new Promise((resolve, reject) => {
        const req = https.get(url, {
            timeout: options.timeout || BASE_CONFIG.fotmob.timeout,
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                ...options.headers
            }
        }, (res) => {
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

        req.on('error', (e) => reject(e));
        req.setTimeout(options.timeout || BASE_CONFIG.fotmob.timeout, () => {
            req.destroy();
            reject(new Error('Request timeout'));
        });
    });
}

// ============================================================================
// 核心类
// ============================================================================

/**
 * @typedef {Object} FixtureData
 * @property {string} match_id - 比赛唯一标识符，格式: ${league_id}_${season}_${externalId}
 * @property {string} external_id - FotMob 比赛ID
 * @property {string} league_name - 联赛名称
 * @property {string} season - 赛季，格式: 2024/2025
 * @property {string} home_team - 主队名称
 * @property {string} away_team - 客队名称
 * @property {Date|null} match_date - 比赛时间
 * @property {number|null} home_score - 主队得分
 * @property {number|null} away_score - 客队得分
 * @property {string} status - 比赛状态: scheduled/live/finished/cancelled/awarded
 * @property {string} data_source - 数据来源，固定为 'FotMob'
 */

/**
 * @typedef {Object} SeederStats
 * @property {number} leagues - 处理的联赛数量
 * @property {number} fixtures - 处理的比赛总数
 * @property {number} inserted - 新增记录数
 * @property {number} updated - 更新记录数
 * @property {number} skipped - 跳过记录数
 * @property {number} errors - 错误数量
 */

/**
 * @typedef {Object} SeederOptions
 * @property {LeagueConfig[]} [leagues] - 自定义联赛列表
 * @property {string[]} [seasons] - 自定义赛季列表
 * @property {Object} [db] - 自定义数据库配置
 * @property {number} [delay] - 请求间隔（毫秒）
 */

/**
 * FixtureSeeder - L1 发现层核心类
 *
 * 负责从 FotMob API 批量获取赛程数据并写入 PostgreSQL 数据库。
 *
 * @class FixtureSeeder
 * @example
 * const seeder = new FixtureSeeder();
 * await seeder.init();
 * const stats = await seeder.seedAll();
 * console.log(`处理完成: ${stats.inserted} 新增, ${stats.updated} 更新`);
 * await seeder.close();
 */
class FixtureSeeder {
    /**
     * 创建 FixtureSeeder 实例
     *
     * @constructor
     * @param {SeederOptions} [options={}] - 配置选项
     */
    constructor(options = {}) {
        // 从配置文件加载联赛列表
        const leagueConfig = loadLeagueConfig();

        /** @type {Object} */
        this.config = {
            ...BASE_CONFIG,
            leagues: leagueConfig.active_leagues,
            seasons: leagueConfig.active_seasons,
            ...options
        };

        /** @type {import('pg').Pool|null} */
        this.pool = null;

        /** @type {SeederStats} */
        this.stats = {
            leagues: 0,
            fixtures: 0,
            inserted: 0,
            updated: 0,
            skipped: 0,
            errors: 0
        };
    }

    /**
     * 初始化数据库连接
     *
     * @async
     * @method init
     * @throws {Error} 数据库连接失败时抛出错误
     * @returns {Promise<void>}
     */
    async init() {
        try {
            this.pool = new Pool(this.config.db);
            // 测试连接
            await this.pool.query('SELECT 1');
            log.info('数据库连接已建立');
        } catch (error) {
            log.error('数据库连接失败', error);
            throw error;
        }
    }

    /**
     * 关闭数据库连接
     *
     * @async
     * @method close
     * @returns {Promise<void>}
     */
    async close() {
        if (this.pool) {
            await this.pool.end();
            this.pool = null;
            log.info('数据库连接已关闭');
        }
    }

    /**
     * 从 FotMob API 获取联赛赛程数据
     *
     * @async
     * @method fetchLeagueFixtures
     * @param {number} leagueId - 联赛 ID（FotMob 格式，如 47 代表英超）
     * @param {string} season - 赛季，格式: 2024/2025
     * @returns {Promise<Object|null>} 联赛数据对象，失败时返回 null
     *
     * @example
     * const data = await seeder.fetchLeagueFixtures(47, '2024/2025');
     * console.log(data.fixtures.allMatches.length); // 380
     */
    async fetchLeagueFixtures(leagueId, season) {
        const seasonParam = season.replace('/', '');
        const url = `https://www.fotmob.com/api/leagues?id=${leagueId}&season=${seasonParam}`;

        log.info(`获取联赛 ${leagueId} 赛季 ${season}...`, { url });

        try {
            const response = await httpsGet(url);

            if (response.status !== 200 || !response.data) {
                log.warn(`获取失败: HTTP ${response.status}`, { leagueId, season });
                return null;
            }

            return response.data;
        } catch (error) {
            log.error(`请求失败`, error);
            return null;
        }
    }

    /**
     * 解析联赛数据为比赛列表
     *
     * @method parseFixtures
     * @param {Object} leagueData - FotMob API 返回的联赛数据
     * @param {LeagueConfig} leagueInfo - 联赛配置信息
     * @param {string} season - 赛季
     * @returns {FixtureData[]} 比赛数据数组
     */
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
     * 解析单场比赛数据
     *
     * V178: match_id 格式 = `${league_id}_${season}_${externalId}`
     * 例如: 47_20242025_123456789
     *
     * @method parseMatch
     * @param {Object} match - FotMob API 返回的比赛对象
     * @param {LeagueConfig} leagueInfo - 联赛配置信息
     * @param {string} season - 赛季
     * @returns {FixtureData|null} 比赛数据对象，无效数据返回 null
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

        // V178: match_id = league_id + season + fotmob_id (严格格式)
        const seasonTag = season.replace('/', '');  // 2023/2024 -> 20232024
        const matchId = `${leagueInfo.id}_${seasonTag}_${externalId}`;

        return {
            match_id: matchId,
            external_id: externalId,
            league_name: leagueInfo.name,
            season: season,
            home_team: homeTeam,
            away_team: awayTeam,
            match_date: matchDate,
            home_score: homeScore,
            away_score: awayScore,
            status: status,
            data_source: 'FotMob'
        };
    }

    /**
     * 确定比赛状态
     *
     * @method determineStatus
     * @param {Object} match - 比赛对象
     * @param {number|null} homeScore - 主队得分
     * @param {number|null} awayScore - 客队得分
     * @returns {string} 状态: scheduled/live/finished/cancelled/awarded
     */
    determineStatus(match, homeScore, awayScore) {
        const status = match.status;

        if (typeof status === 'object' && status !== null) {
            if (status.cancelled) return 'cancelled';
            if (status.awarded) return 'awarded';
            if (status.finished) return 'finished';
            if (status.started) return 'live';
        }

        if (homeScore !== null && awayScore !== null) {
            return 'finished';
        }

        return 'scheduled';
    }

    /**
     * UPSERT 比赛数据到数据库
     *
     * 使用 PostgreSQL ON CONFLICT 语法实现幂等写入：
     * - 新记录：INSERT
     * - 已存在：UPDATE 比分和状态
     *
     * @async
     * @method upsertFixture
     * @param {FixtureData} fixture - 比赛数据
     * @returns {Promise<boolean>} 成功返回 true，失败返回 false
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
     * 执行全量收割
     *
     * 遍历所有配置的联赛和赛季，从 FotMob API 获取数据并写入数据库。
     *
     * @async
     * @method seedAll
     * @returns {Promise<SeederStats>} 收割统计信息
     *
     * @example
     * const stats = await seeder.seedAll();
     * console.log(`处理 ${stats.fixtures} 场比赛`);
     * console.log(`新增 ${stats.inserted}，更新 ${stats.updated}`);
     */
    async seedAll() {
        log.info('═══════════════════════════════════════════════════════════════');
        log.info('V178 Fixture Seeder 启动');
        log.info(`目标联赛: ${this.config.leagues.length} 个`);
        log.info(`目标赛季: ${this.config.seasons.join(', ')}`);
        log.info('═══════════════════════════════════════════════════════════════');

        // 验证联赛配置
        if (this.config.leagues.length === 0) {
            log.warn('没有配置活跃联赛，任务终止');
            return this.stats;
        }

        for (const league of this.config.leagues) {
            for (const season of this.config.seasons) {
                this.stats.leagues++;

                log.info(`处理: ${league.name} (ID: ${league.id}) - ${season}`);

                const leagueData = await this.fetchLeagueFixtures(league.id, season);

                if (!leagueData) {
                    log.warn(`跳过 ${league.name} - ${season}: 无数据`);
                    continue;
                }

                const fixtures = this.parseFixtures(leagueData, league, season);
                log.info(`发现 ${fixtures.length} 场比赛`);

                for (const fixture of fixtures) {
                    await this.upsertFixture(fixture);
                    this.stats.fixtures++;
                }

                log.success(`${league.name} - ${season}: ${fixtures.length} 场已处理`);

                await this.sleep(this.config.delay);
            }
        }

        log.info('═══════════════════════════════════════════════════════════════');
        log.success('赛程收割完成!');
        log.info('统计', {
            leagues: this.stats.leagues,
            fixtures: this.stats.fixtures,
            inserted: this.stats.inserted,
            updated: this.stats.updated,
            errors: this.stats.errors
        });
        log.info('═══════════════════════════════════════════════════════════════');

        return this.stats;
    }

    /**
     * 异步延时
     * @private
     * @param {number} ms - 延时毫秒数
     * @returns {Promise<void>}
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * 获取任务执行摘要（含成功率指标）
     *
     * @method getSummary
     * @returns {Object} 任务摘要对象
     * @returns {number} return.total - 处理的比赛总数
     * @returns {number} return.inserted - 新增记录数
     * @returns {number} return.updated - 更新记录数
     * @returns {number} return.errors - 错误数量
     * @returns {number} return.success_rate - 成功率百分比 (0-100)
     * @returns {string} return.status - 任务状态: success/warning/failed
     *
     * @example
     * const summary = seeder.getSummary();
     * console.log(`成功率: ${summary.success_rate}%`);
     * console.log(`状态: ${summary.status}`);
     */
    getSummary() {
        const total = this.stats.fixtures;
        const success = this.stats.inserted + this.stats.updated;
        const errors = this.stats.errors;

        // 计算成功率
        const successRate = total > 0 ? ((success / total) * 100).toFixed(2) : '0.00';

        // 判断任务状态
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
            timestamp: new Date().toISOString()
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
    generateRequestId,
    CONFIG: BASE_CONFIG
};
