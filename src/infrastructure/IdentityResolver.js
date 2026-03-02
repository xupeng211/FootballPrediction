/**
 * IdentityResolver - 比赛身份找回工具
 * ========================================
 *
 * 通过 FotMob 搜索 API 为无 external_id 的比赛找回真实 ID
 *
 * 工作流程：
 * 1. 遍历 matches 表中 external_id 为空的记录
 * 2. 使用主客队名和比赛日期调用 FotMob 搜索 API
 * 3. 模糊匹配确认比赛身份
 * 4. 更新 matches 表的 external_id
 *
 * @module infrastructure/IdentityResolver
 * @version V176.0.0
 */

'use strict';

const https = require('https');
const { Pool } = require('pg');
const path = require('path');

require('dotenv').config({ path: path.resolve(__dirname, '../../.env') });

// ============================================================================
// 配置
// ============================================================================

const CONFIG = {
    fotmob: {
        baseUrl: 'www.fotmob.com',
        searchEndpoint: '/api/search',
        matchEndpoint: '/api/matchDetails',
        timeout: 15000
    },
    matching: {
        minSimilarity: 0.65,      // 最低相似度阈值
        dateTolerance: 3          // 日期容差（天）
    },
    db: {
        host: process.env.DB_HOST || 'localhost',
        port: parseInt(process.env.DB_PORT || '5432'),
        database: process.env.DB_NAME || 'football_db',
        user: process.env.DB_USER || 'football_user',
        password: process.env.DB_PASSWORD || ''
    },
    batch: {
        size: 50,
        delay: 1000               // 请求间隔（毫秒）
    }
};

// ============================================================================
// 日志工具
// ============================================================================

const log = {
    info: (msg) => console.log(`[IdentityResolver] ${new Date().toISOString()} ${msg}`),
    warn: (msg) => console.warn(`[IdentityResolver] ⚠️ ${msg}`),
    error: (msg) => console.error(`[IdentityResolver] ❌ ${msg}`),
    success: (msg) => console.log(`[IdentityResolver] ✅ ${msg}`)
};

// ============================================================================
// 模糊匹配算法
// ============================================================================

/**
 * Levenshtein 距离计算（JS 实现）
 */
function levenshteinDistance(str1, str2) {
    const m = str1.length;
    const n = str2.length;

    const dp = Array(m + 1).fill(null).map(() => Array(n + 1).fill(0));

    for (let i = 0; i <= m; i++) dp[i][0] = i;
    for (let j = 0; j <= n; j++) dp[0][j] = j;

    for (let i = 1; i <= m; i++) {
        for (let j = 1; j <= n; j++) {
            if (str1[i - 1] === str2[j - 1]) {
                dp[i][j] = dp[i - 1][j - 1];
            } else {
                dp[i][j] = 1 + Math.min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]);
            }
        }
    }

    return dp[m][n];
}

/**
 * 计算字符串相似度（0-1）
 */
function calculateSimilarity(str1, str2) {
    if (!str1 || !str2) return 0;

    const s1 = str1.toLowerCase().trim();
    const s2 = str2.toLowerCase().trim();

    if (s1 === s2) return 1;

    const maxLen = Math.max(s1.length, s2.length);
    if (maxLen === 0) return 1;

    const distance = levenshteinDistance(s1, s2);
    return 1 - distance / maxLen;
}

/**
 * 标准化队名（去除常见后缀）
 */
function normalizeTeamName(name) {
    if (!name) return '';

    return name
        .toLowerCase()
        .replace(/\b(fc|cf|ac|as|ssc|afc|bfc|ifk|sk|fk|rb|sc|cd|ud|rc|ca|fc)\b/gi, '')
        .replace(/[^a-z0-9\s]/g, '')
        .replace(/\s+/g, ' ')
        .trim();
}

/**
 * 匹配比赛搜索结果
 */
function matchSearchResult(searchResult, homeTeam, awayTeam, matchDate) {
    const matches = searchResult?.matches || [];

    for (const match of matches) {
        const resultHome = match.home?.name || match.homeTeam?.name || '';
        const resultAway = match.away?.name || match.awayTeam?.name || '';
        const resultDate = match.date || match.matchDate || '';

        // 计算队名相似度
        const homeSim = calculateSimilarity(
            normalizeTeamName(homeTeam),
            normalizeTeamName(resultHome)
        );
        const awaySim = calculateSimilarity(
            normalizeTeamName(awayTeam),
            normalizeTeamName(resultAway)
        );

        // 检查日期匹配
        let dateMatch = true;
        if (matchDate && resultDate) {
            const expectedDate = new Date(matchDate).toDateString();
            const actualDate = new Date(resultDate).toDateString();
            const diffDays = Math.abs(
                (new Date(matchDate) - new Date(resultDate)) / (1000 * 60 * 60 * 24)
            );
            dateMatch = diffDays <= CONFIG.matching.dateTolerance;
        }

        // 综合评分
        const avgSim = (homeSim + awaySim) / 2;
        const score = dateMatch ? avgSim : avgSim * 0.7;

        if (score >= CONFIG.matching.minSimilarity) {
            return {
                matched: true,
                externalId: match.id || match.matchId,
                score,
                homeSim,
                awaySim,
                dateMatch
            };
        }
    }

    return { matched: false };
}

// ============================================================================
// HTTP 请求工具
// ============================================================================

function httpsGet(url, options = {}) {
    return new Promise((resolve, reject) => {
        const req = https.get(url, options, (res) => {
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
        req.setTimeout(options.timeout || CONFIG.fotmob.timeout, () => {
            req.destroy();
            reject(new Error('Request timeout'));
        });
    });
}

// ============================================================================
// 核心类
// ============================================================================

class IdentityResolver {
    constructor(options = {}) {
        this.config = { ...CONFIG, ...options };
        this.pool = null;
        this.stats = {
            processed: 0,
            resolved: 0,
            failed: 0,
            skipped: 0
        };
    }

    /**
     * 初始化数据库连接
     */
    async init() {
        this.pool = new Pool(this.config.db);
        log.info('数据库连接已建立');
    }

    /**
     * 关闭数据库连接
     */
    async close() {
        if (this.pool) {
            await this.pool.end();
            this.pool = null;
        }
    }

    /**
     * 获取无 external_id 的比赛列表
     */
    async getUnresolvedMatches(limit = null) {
        const query = `
            SELECT match_id, home_team, away_team, match_date, league_name
            FROM matches
            WHERE external_id IS NULL OR external_id = ''
            ORDER BY match_date DESC
            ${limit ? `LIMIT ${limit}` : ''}
        `;

        const result = await this.pool.query(query);
        return result.rows;
    }

    /**
     * 搜索 FotMob 比赛
     */
    async searchFotMob(homeTeam, awayTeam) {
        // 构建搜索词
        const searchTerm = `${homeTeam} vs ${awayTeam}`;
        const encodedTerm = encodeURIComponent(searchTerm);
        const url = `https://${this.config.fotmob.baseUrl}${this.config.fotmob.searchEndpoint}?term=${encodedTerm}`;

        try {
            const response = await httpsGet(url, {
                timeout: this.config.fotmob.timeout,
                headers: {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/json'
                }
            });

            return response.data;
        } catch (error) {
            log.error(`搜索失败: ${searchTerm} - ${error.message}`);
            return null;
        }
    }

    /**
     * 解析单个比赛
     */
    async resolveMatch(match) {
        const { match_id, home_team, away_team, match_date } = match;

        log.info(`解析: ${home_team} vs ${away_team} (${match_date?.toDateString() || '无日期'})`);

        // 搜索比赛
        const searchResult = await this.searchFotMob(home_team, away_team);

        if (!searchResult) {
            this.stats.failed++;
            return { success: false, reason: 'search_failed' };
        }

        // 匹配结果
        const matchResult = matchSearchResult(searchResult, home_team, away_team, match_date);

        if (matchResult.matched && matchResult.externalId) {
            // 更新数据库
            await this.updateExternalId(match_id, matchResult.externalId);

            this.stats.resolved++;
            log.success(`已找回 ID: ${matchResult.externalId} (相似度: ${(matchResult.score * 100).toFixed(1)}%)`);

            return {
                success: true,
                externalId: matchResult.externalId,
                score: matchResult.score
            };
        }

        this.stats.failed++;
        return { success: false, reason: 'no_match' };
    }

    /**
     * 更新 external_id
     */
    async updateExternalId(matchId, externalId) {
        const query = `
            UPDATE matches
            SET external_id = $1, updated_at = NOW()
            WHERE match_id = $2
        `;

        await this.pool.query(query, [externalId, matchId]);
    }

    /**
     * 批量解析
     */
    async resolveBatch(limit = null) {
        log.info('========================================');
        log.info('V176 Identity Resolver 启动');
        log.info(`批次大小: ${this.config.batch.size}`);
        log.info(`相似度阈值: ${this.config.matching.minSimilarity}`);
        log.info('========================================');

        // 获取待解析列表
        const matches = await this.getUnresolvedMatches(limit);
        log.info(`发现 ${matches.length} 场待解析比赛`);

        if (matches.length === 0) {
            log.info('没有需要解析的比赛');
            return this.stats;
        }

        // 批量处理
        for (const match of matches) {
            this.stats.processed++;

            await this.resolveMatch(match);

            // 延时避免频率限制
            if (this.stats.processed < matches.length) {
                await this.sleep(this.config.batch.delay);
            }

            // 进度报告
            if (this.stats.processed % 10 === 0) {
                log.info(`进度: ${this.stats.processed}/${matches.length} (已解析: ${this.stats.resolved})`);
            }
        }

        // 汇总
        log.info('========================================');
        log.success(`解析完成!`);
        log.info(`处理: ${this.stats.processed} | 成功: ${this.stats.resolved} | 失败: ${this.stats.failed}`);
        log.info('========================================');

        return this.stats;
    }

    /**
     * 延时工具
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// ============================================================================
// 导出
// ============================================================================

module.exports = {
    IdentityResolver,
    calculateSimilarity,
    normalizeTeamName,
    matchSearchResult,
    CONFIG
};
