/**
 * ApiSniffer - FotMob API 流量嗅探器
 * ==============================================
 *
 * 负责:
 * - 拦截浏览器中的 API 请求
 * - 提取关键 Headers (x-* 自定义头, Cookie)
 * - 缓存通行证供轻量级请求复用
 *
 * V175 Ghost Protocol 核心组件
 *
 * @module parsers/fotmob/ApiSniffer
 * @version V175.0.0
 */

'use strict';

// ============================================================================
// V175 考古发现 - FotMob API 保护机制分析
// ============================================================================
//
// 📋 重要发现 (2026-03-01):
//
// FotMob API 使用双重验证机制:
// 1. 动态签名令牌 (x-mas): JWT 式令牌，每个请求动态生成
// 2. TLS 指纹检测: 只接受真实浏览器的 TLS 指纹
//
// x-mas 令牌结构 (Base64 编码的 JSON):
// {
//     "body": {
//         "url": "/api/data/matchDetails?matchId=xxx",
//         "code": 1772310404745,  // 时间戳
//         "foo": "production:0ea04a6760ecc7df4e8371971c11a8cdd5910ec4"  // 会话哈希
//     },
//     "signature": "BA536874453C2B3419BDD04D5B1B4EB6"  // 请求签名
// }
//
// 旧版静态 x-mas/x-foo (Python master_collector.py) 已过时:
// - x-mas: "Content-Type: application/json; charset=utf-8" (Base64)
// - x-foo: "https://www.fotmob.com/" (Base64)
//
// 结论: 无法脱离浏览器进行 API 请求，必须使用 Playwright 或 TLS 指纹模拟库
// ============================================================================

/**
 * 考古版 Headers - Python 成功经验 (已过时，仅供参考)
 *
 * ⚠️ 警告: 这些静态 Headers 已不再有效！
 * FotMob 现在使用动态签名 + TLS 指纹双重验证
 *
 * 来源: _deprecated/legacy_scripts_v1_v170/collectors/master_collector.py
 *
 * 历史解码说明:
 * - x-mas: "Content-Type: application/json; charset=utf-8" (Base64)
 * - x-foo: "https://www.fotmob.com/" (Base64)
 */
const ARCHAEOLOGY_HEADERS = {
    // 🎯 旧版静态 Headers (已过时)
    'x-mas': 'Q29udGVudC1UeXBlOiBhcHBsaWNhdGlvbi9qc29uOyBjaGFyc2V0PXV0Zi04',
    'x-foo': 'aHR0cHM6Ly93d3cuZm90bW9iLmNvbS8=',

    // 完整的配套 Headers
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'no-cache',
    'pragma': 'no-cache',
    'priority': 'u=1, i',
    'referer': 'https://www.fotmob.com/',
    'sec-ch-ua': '"Chromium";v="131", "Not_A Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Linux"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
};

/**
 * API 端点配置 - 考古版 URL 格式
 *
 * 关键发现: Python 版本使用 /api/matchDetails (不带 /data/ 前缀)
 */
const API_ENDPOINTS = {
    // 🎯 考古发现的正确端点 (Query 参数格式)
    matchDetails: 'https://www.fotmob.com/api/matchDetails',

    // 旧版端点 (可能已失效)
    legacyMatchDetails: 'https://www.fotmob.com/api/data/matchDetails',

    // 其他端点
    matchesByDate: 'https://www.fotmob.com/api/matchesByDate',
    leagues: 'https://www.fotmob.com/api/leagues'
};

/**
 * 获取考古版 Headers
 * @param {Object} [overrides] - 可选的覆盖字段
 * @returns {Object}
 */
function getArchaeologyHeaders(overrides = {}) {
    return {
        ...ARCHAEOLOGY_HEADERS,
        ...overrides
    };
}

/**
 * 构建考古版 API URL
 * @param {string} matchId - 比赛 ID
 * @returns {string}
 */
function buildMatchDetailsUrl(matchId) {
    return `${API_ENDPOINTS.matchDetails}?matchId=${matchId}`;
}

/**
 * API 请求通行证
 * @typedef {Object} ApiPassport
 * @property {string} url - 请求 URL
 * @property {Object} headers - 请求头
 * @property {string} cookie - Cookie 字符串
 * @property {number} capturedAt - 捕获时间戳
 * @property {string} matchId - 比赛 ID (如果可提取)
 */

/**
 * ApiSniffer - API 流量嗅探器
 */
class ApiSniffer {
    /**
     * @param {Object} options - 配置选项
     * @param {string[]} options.targetPatterns - 目标 URL 模式
     * @param {number} options.maxCacheSize - 最大缓存数量
     * @param {number} options.passportTTL - 通行证有效期 (ms)
     */
    constructor(options = {}) {
        this.targetPatterns = options.targetPatterns || [
            'api.fotmob.com/teams?id=',
            'api.fotmob.com/matchDetails',
            'api.fotmob.com/match',
            'www.fotmob.com/api/'
        ];

        this.maxCacheSize = options.maxCacheSize || 100;
        this.passportTTL = options.passportTTL || 5 * 60 * 1000; // 5 分钟

        // 通行证缓存
        this.passports = new Map();

        // 原始请求记录
        this.capturedRequests = [];

        // 统计
        this.stats = {
            totalIntercepted: 0,
            matchedIntercepted: 0,
            cacheHits: 0,
            cacheMisses: 0
        };
    }

    /**
     * 设置页面请求拦截
     * @param {import('playwright').Page} page - Playwright 页面对象
     */
    async setupInterception(page) {
        await page.route('**/*', async (route) => {
            const request = route.request();
            const url = request.url();
            const method = request.method();

            // 记录所有请求
            this.stats.totalIntercepted++;

            // 检查是否匹配目标模式
            if (this._isTargetUrl(url)) {
                this.stats.matchedIntercepted++;

                // 提取通行证
                const passport = this._extractPassport(request);

                // 缓存通行证
                this._cachePassport(url, passport);

                // 记录请求
                this.capturedRequests.push({
                    url,
                    method,
                    passport,
                    timestamp: Date.now()
                });

                // 打印捕获日志
                this._logCapture(url, passport);
            }

            // 继续请求
            await route.continue();
        });
    }

    /**
     * 检查 URL 是否匹配目标模式
     * @private
     * @param {string} url - 请求 URL
     * @returns {boolean}
     */
    _isTargetUrl(url) {
        return this.targetPatterns.some(pattern => url.includes(pattern));
    }

    /**
     * 从请求中提取通行证
     * @private
     * @param {import('playwright').Request} request - Playwright 请求对象
     * @returns {ApiPassport}
     */
    _extractPassport(request) {
        const headers = request.headers();
        const url = request.url();

        // 提取关键 Headers
        const keyHeaders = {};

        // 提取所有 x- 开头的自定义头
        for (const [key, value] of Object.entries(headers)) {
            if (key.toLowerCase().startsWith('x-')) {
                keyHeaders[key] = value;
            }
        }

        // 提取常用关键头
        const importantHeaders = [
            'user-agent',
            'accept',
            'accept-language',
            'accept-encoding',
            'referer',
            'origin',
            'sec-ch-ua',
            'sec-ch-ua-mobile',
            'sec-ch-ua-platform',
            'sec-fetch-dest',
            'sec-fetch-mode',
            'sec-fetch-site'
        ];

        for (const header of importantHeaders) {
            if (headers[header]) {
                keyHeaders[header] = headers[header];
            }
        }

        // 提取 Cookie
        const cookie = headers['cookie'] || '';

        // 提取 matchId
        const matchId = this._extractMatchId(url);

        return {
            url,
            headers: keyHeaders,
            cookie,
            capturedAt: Date.now(),
            matchId,
            // 完整 Headers (用于调试)
            _rawHeaders: headers
        };
    }

    /**
     * 从 URL 中提取 matchId
     * @private
     * @param {string} url - 请求 URL
     * @returns {string|null}
     */
    _extractMatchId(url) {
        // 尝试从 URL 参数提取
        const matchIdMatch = url.match(/[?&]matchId=(\d+)/);
        if (matchIdMatch) return matchIdMatch[1];

        // 尝试从路径提取
        const pathMatch = url.match(/match\/?(\d+)/);
        if (pathMatch) return pathMatch[1];

        // 尝试从 id 参数提取
        const idMatch = url.match(/[?&]id=(\d+)/);
        if (idMatch) return idMatch[1];

        return null;
    }

    /**
     * 缓存通行证
     * @private
     * @param {string} url - 请求 URL
     * @param {ApiPassport} passport - 通行证
     */
    _cachePassport(url, passport) {
        // 生成缓存键
        const cacheKey = this._generateCacheKey(url);

        // 检查缓存大小
        if (this.passports.size >= this.maxCacheSize) {
            // 删除最旧的条目
            const oldestKey = this.passports.keys().next().value;
            this.passports.delete(oldestKey);
        }

        this.passports.set(cacheKey, {
            ...passport,
            cachedAt: Date.now()
        });
    }

    /**
     * 生成缓存键
     * @private
     * @param {string} url - 请求 URL
     * @returns {string}
     */
    _generateCacheKey(url) {
        // 提取 API 端点作为键
        try {
            const urlObj = new URL(url);
            return `${urlObj.hostname}${urlObj.pathname}`;
        } catch {
            return url;
        }
    }

    /**
     * 打印捕获日志
     * @private
     * @param {string} url - 请求 URL
     * @param {ApiPassport} passport - 通行证
     */
    _logCapture(url, passport) {
        const xHeaders = Object.keys(passport.headers).filter(k => k.toLowerCase().startsWith('x-'));
        const cookieLen = passport.cookie ? passport.cookie.length : 0;

        console.log(`🎯 [ApiSniffer] 捕获 API 请求:`);
        console.log(`   URL: ${url.substring(0, 80)}...`);
        console.log(`   X-Headers: ${xHeaders.length} 个`);
        console.log(`   Cookie: ${cookieLen} 字符`);
        console.log(`   User-Agent: ${(passport.headers['user-agent'] || '').substring(0, 50)}...`);
    }

    // ============================================================================
    // 公共 API
    // ============================================================================

    /**
     * 获取最新的通行证
     * @param {string} [pattern] - 可选的 URL 模式匹配
     * @returns {ApiPassport|null}
     */
    getLatestPassport(pattern = null) {
        // 查找匹配的最新通行证
        for (let i = this.capturedRequests.length - 1; i >= 0; i--) {
            const req = this.capturedRequests[i];

            // 检查 TTL
            if (Date.now() - req.timestamp > this.passportTTL) {
                continue;
            }

            // 检查模式匹配
            if (pattern && !req.url.includes(pattern)) {
                continue;
            }

            this.stats.cacheHits++;
            return req.passport;
        }

        this.stats.cacheMisses++;
        return null;
    }

    /**
     * 获取用于 HTTP 客户端的 Headers
     * @param {string} [customCookie] - 可选的自定义 Cookie
     * @returns {Object}
     */
    getHeadersForHttpClient(customCookie = null) {
        const passport = this.getLatestPassport();
        if (!passport) {
            throw new Error('没有可用的通行证，请先启动浏览器捕获');
        }

        const headers = { ...passport.headers };

        // 使用自定义 Cookie 或捕获的 Cookie
        if (customCookie) {
            headers['cookie'] = customCookie;
        } else if (passport.cookie) {
            headers['cookie'] = passport.cookie;
        }

        return headers;
    }

    /**
     * 获取所有捕获的请求
     * @returns {Array}
     */
    getCapturedRequests() {
        return [...this.capturedRequests];
    }

    /**
     * 获取统计信息
     * @returns {Object}
     */
    getStats() {
        return {
            ...this.stats,
            cachedPassports: this.passports.size,
            capturedRequests: this.capturedRequests.length
        };
    }

    /**
     * 清理过期缓存
     */
    cleanupExpired() {
        const now = Date.now();
        let cleaned = 0;

        // 清理通行证缓存
        for (const [key, passport] of this.passports) {
            if (now - passport.capturedAt > this.passportTTL) {
                this.passports.delete(key);
                cleaned++;
            }
        }

        // 清理请求记录
        this.capturedRequests = this.capturedRequests.filter(
            req => now - req.timestamp <= this.passportTTL
        );

        if (cleaned > 0) {
            console.log(`🧹 [ApiSniffer] 清理了 ${cleaned} 个过期通行证`);
        }
    }

    /**
     * 重置所有缓存
     */
    reset() {
        this.passports.clear();
        this.capturedRequests = [];
        this.stats = {
            totalIntercepted: 0,
            matchedIntercepted: 0,
            cacheHits: 0,
            cacheMisses: 0
        };
        console.log('🔄 [ApiSniffer] 缓存已重置');
    }

    /**
     * 导出通行证 (用于调试或持久化)
     * @returns {Object}
     */
    exportPassports() {
        return {
            passports: Object.fromEntries(this.passports),
            requests: this.capturedRequests,
            stats: this.stats,
            exportedAt: new Date().toISOString()
        };
    }
}

module.exports = {
    ApiSniffer,
    // V175 考古发现导出
    ARCHAEOLOGY_HEADERS,
    API_ENDPOINTS,
    getArchaeologyHeaders,
    buildMatchDetailsUrl
};
