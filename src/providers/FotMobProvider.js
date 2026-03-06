/**
 * FotMobProvider - FotMob 数据源提供者
 * ==============================================
 *
 * 实现 DataSourceProvider 接口，封装所有 FotMob 相关的数据获取逻辑。
 *
 * 特性:
 * - 支持联赛赛程获取
 * - 支持比赛详情获取
 * - 统一的错误处理
 * - 使用 Registry 配置
 *
 * @module providers/FotMobProvider
 * @version V197.0.0
 * @since V196-TECH-DEBT-002
 */

'use strict';

const https = require('https');
const Registry = require('../../config/registry');
const { DataSourceProvider, DataSourceType } = require('../interfaces/DataSourceProvider');

/**
 * FotMob 数据源提供者
 * @extends DataSourceProvider
 */
class FotMobProvider extends DataSourceProvider {
    /**
     * 创建 FotMobProvider 实例
     * @param {Object} [config={}] - 配置选项
     * @param {number} [config.timeout=20000] - 请求超时 (ms)
     * @param {number} [config.delay=2000] - 请求间隔 (ms)
     */
    constructor(config = {}) {
        super();

        this.config = {
            timeout: config.timeout || Registry.APIS.FOTMOB.TIMEOUT,
            delay: config.delay || 2000,
            baseUrl: config.baseUrl || Registry.APIS.FOTMOB.BASE_URL,
            apiBase: config.apiBase || Registry.APIS.FOTMOB.API_BASE,
            ...config
        };

        /** @type {Map<string, any>} */
        this._cache = new Map();

        /** @type {boolean} */
        this._initialized = false;
    }

    /**
     * 数据源类型
     * @type {string}
     */
    get sourceType() {
        return DataSourceType.FOTMOB;
    }

    /**
     * 数据源显示名称
     * @type {string}
     */
    get displayName() {
        return 'FotMob';
    }

    /**
     * 初始化提供者
     * @async
     * @returns {Promise<void>}
     */
    async initialize() {
        if (this._initialized) {
            return;
        }

        // 验证配置
        if (!this.config.apiBase) {
            throw new Error('FotMob API base URL is required');
        }

        this._initialized = true;
        console.log(`✅ FotMobProvider 初始化完成 (API: ${this.config.apiBase})`);
    }

    /**
     * HTTP GET 请求封装
     * @private
     * @async
     * @param {string} url - 请求 URL
     * @param {Object} [options={}] - 请求选项
     * @returns {Promise<{status: number, data: Object|null, raw: string, error?: string}>}
     */
    async _httpsGet(url, options = {}) {
        return new Promise((resolve, reject) => {
            const req = https.get(url, {
                timeout: options.timeout || this.config.timeout,
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
            req.setTimeout(options.timeout || this.config.timeout, () => {
                req.destroy();
                reject(new Error('Request timeout'));
            });
        });
    }

    /**
     * 获取联赛赛程数据
     * @async
     * @param {number} leagueId - 联赛 ID (FotMob 格式)
     * @param {string} season - 赛季 (格式: 2024/2025)
     * @returns {Promise<Object|null>} 联赛数据对象
     *
     * @example
     * const data = await provider.fetchLeagueFixtures(47, '2024/2025');
     * console.log(data.fixtures.allMatches.length);
     */
    async fetchLeagueFixtures(leagueId, season) {
        if (!this._initialized) {
            await this.initialize();
        }

        // 使用 Registry 构建 URL
        const seasonParam = season.replace('/', '');
        const url = Registry.APIS.FOTMOB.leagues(leagueId, seasonParam);

        console.log(`📡 FotMob: 获取联赛 ${leagueId} 赛季 ${season}...`);

        try {
            const response = await this._httpsGet(url);

            if (response.status !== 200 || !response.data) {
                console.warn(`⚠️ FotMob: 获取失败 - HTTP ${response.status}`);
                return null;
            }

            return response.data;
        } catch (error) {
            console.error(`❌ FotMob: 请求失败 - ${error.message}`);
            return null;
        }
    }

    /**
     * 获取比赛详情数据
     * @async
     * @param {string} externalId - 外部比赛 ID
     * @returns {Promise<Object|null>} 比赛详情数据
     */
    async fetchMatchDetails(externalId) {
        if (!this._initialized) {
            await this.initialize();
        }

        const url = Registry.APIS.FOTMOB.matchDetails(externalId);

        try {
            const response = await this._httpsGet(url);

            if (response.status !== 200 || !response.data) {
                return null;
            }

            return response.data;
        } catch (error) {
            console.error(`❌ FotMob: 获取比赛详情失败 - ${error.message}`);
            return null;
        }
    }

    /**
     * 解析联赛数据为比赛列表
     * @param {Object} leagueData - FotMob API 返回的联赛数据
     * @param {Object} leagueInfo - 联赛配置信息 {id, name, country}
     * @param {string} season - 赛季
     * @returns {Object[]} 比赛数据数组
     */
    parseFixtures(leagueData, leagueInfo, season) {
        const fixtures = [];

        // 兼容多种数据结构
        const allMatches = leagueData?.fixtures?.allMatches ||
                          leagueData?.overview?.matches?.allMatches ||
                          [];

        if (!Array.isArray(allMatches) || allMatches.length === 0) {
            console.warn(`⚠️ FotMob: 未找到 allMatches 数据 (${leagueInfo.name})`);
            return [];
        }

        console.log(`📊 FotMob: 发现 ${allMatches.length} 场比赛 (${leagueInfo.name})`);

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
                    console.warn(`⚠️ FotMob: 解析错误 - ${e.message}`);
                }
            }
        }

        if (parseErrors > 0) {
            console.warn(`⚠️ FotMob: 解析错误总数: ${parseErrors}`);
        }

        return fixtures.filter(f => f && f.external_id);
    }

    /**
     * 解析单场比赛数据
     * @param {Object} match - FotMob API 返回的比赛对象
     * @param {Object} leagueInfo - 联赛配置信息
     * @param {string} season - 赛季
     * @returns {Object|null} 比赛数据对象
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

        // 使用 Registry 的状态映射
        const status = Registry.MATCH_STATUS.fromFotMob(match.status, homeScore, awayScore);

        // 构建 match_id (格式: leagueId_season_externalId)
        const seasonTag = season.replace('/', '');  // 2023/2024 -> 20232024
        const matchId = `${leagueInfo.id}_${seasonTag}_${externalId}`;

        return {
            match_id: matchId,
            external_id: externalId,
            league_name: leagueInfo.name,
            league_id: leagueInfo.id,
            season: season,
            home_team: homeTeam,
            away_team: awayTeam,
            match_date: matchDate,
            home_score: homeScore,
            away_score: awayScore,
            status: status,
            data_source: DataSourceType.FOTMOB
        };
    }

    /**
     * 健康检查
     * @async
     * @returns {Promise<{healthy: boolean, latency?: number, error?: string}>}
     */
    async healthCheck() {
        const startTime = Date.now();

        try {
            // 使用英超 ID 47 进行简单测试
            const url = `${this.config.apiBase}/leagues?id=47`;
            const response = await this._httpsGet(url, { timeout: 10000 });

            const latency = Date.now() - startTime;

            if (response.status === 200) {
                return { healthy: true, latency };
            } else {
                return { healthy: false, latency, error: `HTTP ${response.status}` };
            }
        } catch (error) {
            const latency = Date.now() - startTime;
            return { healthy: false, latency, error: error.message };
        }
    }

    /**
     * 关闭提供者
     * @async
     * @returns {Promise<void>}
     */
    async close() {
        this._cache.clear();
        this._initialized = false;
        console.log('🔒 FotMobProvider 已关闭');
    }
}

// ============================================================================
// 注册到全局工厂
// ============================================================================

const { factory } = require('../interfaces/DataSourceProvider');
factory.register(DataSourceType.FOTMOB, FotMobProvider);

// ============================================================================
// 导出
// ============================================================================

module.exports = {
    FotMobProvider,
    DataSourceType
};
