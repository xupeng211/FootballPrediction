/**
 * SessionManager - V179 无人值守身份获取系统
 * ==============================================
 *
 * 为 ProductionHarvester 提供全自动的身份支持，实现：
 * - 自动身份捕获（打开可见浏览器过 Turnstile 验证）
 * - 身份热加载（收割时自动注入 Cookie）
 * - 22 节点一对一绑定 (7890-7911)
 * - 异常自愈（指数退避重试）
 *
 * @module infrastructure/network/SessionManager
 * @version V179.0.0
 */

'use strict';

const { chromium } = require('playwright');
const fs = require('fs').promises;
const path = require('path');
const FactoryConfig = require('../../../config/factory_config');

// V4.46.5 HARDENING: 使用确定性 ID 生成器（零模拟铁律）
const { generateLockId } = require('../../core/id_generator');

// ============================================================================
// 默认配置
// ============================================================================

const DEFAULT_CONFIG = {
    /** 会话存储路径 */
    profilePath: '/app/data/sessions',

    /** 会话 TTL (小时) */
    sessionTtlHours: 24,

    /** 最大刷新尝试次数 */
    maxRefreshAttempts: 3,

    /** 刷新时是否使用无头模式（必须 false 才能过 Turnstile） */
    headlessRefresh: false,

    /** 目标站点 */
    targetUrl: 'https://www.fotmob.com/',

    /** 测试比赛 URL */
    testUrl: 'https://www.fotmob.com/matches/-/4813729',

    /** Turnstile 等待超时 (ms) */
    turnstileTimeout: 60000,

    /** 刷新锁超时 (ms) */
    lockTimeout: 120000,

    /** V179.1: 在无 X Server 环境下是否跳过可见浏览器刷新 */
    skipHeadlessRefreshInContainer: true
};

// ============================================================================
// Logger
// ============================================================================

/**
 * 简单日志器
 */
class Logger {
    constructor(prefix = '[SessionManager]') {
        this.prefix = prefix;
    }

    _timestamp() {
        return new Date().toISOString().slice(11, 19);
    }

    info(msg) {
        console.log(`[${this._timestamp()}] ${this.prefix} ℹ️  ${msg}`);
    }

    success(msg) {
        console.log(`[${this._timestamp()}] ${this.prefix} ✅ ${msg}`);
    }

    warn(msg) {
        console.log(`[${this._timestamp()}] ${this.prefix} ⚠️  ${msg}`);
    }

    error(msg) {
        console.log(`[${this._timestamp()}] ${this.prefix} ❌ ${msg}`);
    }

    debug(msg) {
        if (process.env.LOG_LEVEL === 'debug') {
            console.log(`[${this._timestamp()}] ${this.prefix} 🔍 ${msg}`);
        }
    }
}

// ============================================================================
// SessionManager 类
// ============================================================================

/**
 * SessionManager - 无人值守身份管理器
 *
 * @class
 * @example
 * const sessionManager = new SessionManager();
 * await sessionManager.initialize();
 *
 * // 刷新指定端口的会话
 * await sessionManager.refreshSession(7890, 'http://172.25.16.1:7890');
 *
 * // 获取或刷新会话
 * const session = await sessionManager.getOrRefreshSession(7890);
 *
 * // 加载会话到浏览器上下文
 * await sessionManager.loadSessionToContext(context, 7890);
 */
class SessionManager {
    /**
     * 创建 SessionManager 实例
     *
     * @param {Object} [options={}] - 配置选项
     */
    constructor(options = {}) {
        /** @type {Object} */
        this.config = { ...DEFAULT_CONFIG, ...options };

        /** @type {Logger} */
        this.logger = new Logger('[SessionManager]');

        /** @type {Map<number, Object>} 端口 -> 刷新锁 */
        this._refreshLocks = new Map();

        /** @type {Map<number, Object>} 端口 -> 会话缓存 */
        this._sessionCache = new Map();

        /** @type {Object} 统计信息 */
        this._stats = {
            totalRefreshes: 0,
            successfulRefreshes: 0,
            failedRefreshes: 0,
            cacheHits: 0,
            cacheMisses: 0
        };

        /** @type {boolean} 是否已初始化 */
        this._initialized = false;
    }

    // ========================================================================
    // 公共 API
    // ========================================================================

    /**
     * 初始化 SessionManager
     *
     * @returns {Promise<void>}
     */
    async initialize() {
        if (this._initialized) {
            this.logger.warn('已经初始化，跳过');
            return;
        }

        this.logger.info('🚀 初始化 SessionManager V179...');

        // 确保会话目录存在
        await this._ensureSessionDirectory();

        // 加载现有会话到缓存
        await this._loadExistingSessions();

        this._initialized = true;
        this.logger.success(`SessionManager 就绪，已加载 ${this._sessionCache.size} 个会话`);
    }

    /**
     * 获取或刷新会话（主入口）
     *
     * @param {number} port - 代理端口
     * @param {Object} [options={}] - 选项
     * @param {string} [options.proxyUrl] - 代理 URL
     * @param {boolean} [options.forceRefresh] - 强制刷新
     * @returns {Promise<Object|null>} 会话对象
     */
    async getOrRefreshSession(port, options = {}) {
        if (!this._initialized) {
            await this.initialize();
        }

        const { proxyUrl, forceRefresh = false } = options;

        // 检查缓存
        if (!forceRefresh) {
            const cachedSession = this._sessionCache.get(port);
            if (cachedSession && !this._isSessionExpired(cachedSession)) {
                this._stats.cacheHits++;
                this.logger.debug(`端口 ${port} 会话缓存命中`);
                return cachedSession;
            }
        }

        // V179.1: 检测容器环境（无 X Server）
        if (this.config.skipHeadlessRefreshInContainer && !this._hasDisplayServer()) {
            this.logger.warn(`端口 ${port} 无 X Server，跳过可见浏览器刷新（容器环境）`);
            this.logger.info(`提示: 请在宿主机运行 'node scripts/capture_auth.js' 手动捕获身份`);
            return null;
        }

        this._stats.cacheMisses++;

        // 需要刷新
        this.logger.info(`端口 ${port} 需要刷新会话...`);

        const finalProxyUrl = proxyUrl || `http://172.25.16.1:${port}`;
        return this.refreshSession(port, finalProxyUrl);
    }

    /**
     * 刷新指定端口的会话（自动身份捕获）
     *
     * @param {number} port - 代理端口
     * @param {string} proxyUrl - 代理 URL
     * @returns {Promise<Object|null>} 刷新后的会话
     */
    async refreshSession(port, proxyUrl) {
        this._stats.totalRefreshes++;

        // 获取刷新锁
        const lockId = this._acquireRefreshLock(port);
        if (!lockId) {
            this.logger.warn(`端口 ${port} 刷新锁获取失败，可能有其他进程正在刷新`);
            // 等待锁释放后返回现有会话
            await this._waitForLockRelease(port);
            return this._sessionCache.get(port) || null;
        }

        try {
            // 指数退避重试
            let lastError = null;
            for (let attempt = 1; attempt <= this.config.maxRefreshAttempts; attempt++) {
                try {
                    this.logger.info(`端口 ${port} 第 ${attempt}/${this.config.maxRefreshAttempts} 次刷新尝试...`);

                    const session = await this._doRefreshSession(port, proxyUrl);

                    // 保存会话
                    await this._saveSessionToFile(port, session);

                    // 更新缓存
                    this._sessionCache.set(port, session);

                    this._stats.successfulRefreshes++;
                    this.logger.success(`端口 ${port} 会话刷新成功！`);

                    return session;
                } catch (error) {
                    lastError = error;
                    this.logger.warn(`端口 ${port} 第 ${attempt} 次刷新失败: ${error.message}`);

                    if (attempt < this.config.maxRefreshAttempts) {
                        const backoff = this._exponentialBackoff(attempt);
                        this.logger.info(`等待 ${backoff}ms 后重试...`);
                        await this._delay(backoff);
                    }
                }
            }

            this._stats.failedRefreshes++;
            this.logger.error(`端口 ${port} 刷新失败，已达到最大重试次数`);
            throw lastError || new Error('刷新失败');

        } finally {
            // 释放刷新锁
            this._releaseRefreshLock(port, lockId);
        }
    }

    /**
     * 加载会话到浏览器上下文（身份热加载）
     *
     * @param {import('playwright').BrowserContext} context - Playwright 上下文
     * @param {number} port - 代理端口
     * @returns {Promise<boolean>} 是否成功加载
     */
    async loadSessionToContext(context, port) {
        try {
            const session = await this._loadSessionFromFile(port);

            if (!session) {
                this.logger.debug(`端口 ${port} 无会话文件，跳过加载`);
                return false;
            }

            if (this._isSessionExpired(session)) {
                this.logger.warn(`端口 ${port} 会话已过期，跳过加载`);
                return false;
            }

            // 注入 Cookie
            if (session.cookies && session.cookies.length > 0) {
                await context.addCookies(session.cookies);
                this.logger.success(`端口 ${port} 已加载 ${session.cookies.length} 个 Cookie`);
                return true;
            }

            this.logger.warn(`端口 ${port} 会话无 Cookie`);
            return false;

        } catch (error) {
            this.logger.error(`端口 ${port} 加载会话失败: ${error.message}`);
            return false;
        }
    }

    /**
     * 验证会话有效性
     *
     * @param {number} port - 代理端口
     * @returns {Promise<boolean>} 是否有效
     */
    async validateSession(port) {
        const session = await this._loadSessionFromFile(port);

        if (!session) {
            return false;
        }

        if (this._isSessionExpired(session)) {
            return false;
        }

        // 检查是否有有效的 FotMob Cookie
        const fotmobCookies = (session.cookies || []).filter(c =>
            c.domain && c.domain.includes('fotmob')
        );

        return fotmobCookies.length > 0;
    }

    /**
     * 获取统计信息
     *
     * @returns {Object} 统计信息
     */
    getStats() {
        return {
            ...this._stats,
            cachedSessions: this._sessionCache.size,
            activeLocks: this._refreshLocks.size
        };
    }

    /**
     * 清除指定端口的会话缓存
     *
     * @param {number} port - 代理端口
     * @returns {Promise<void>}
     */
    async clearSession(port) {
        this._sessionCache.delete(port);

        const sessionPath = this._getSessionFilePath(port);
        try {
            await fs.unlink(sessionPath);
            this.logger.info(`端口 ${port} 会话已清除`);
        } catch (error) {
            // 文件不存在，忽略
        }
    }

    /**
     * 清除所有过期会话
     *
     * @returns {Promise<number>} 清除的会话数量
     */
    async clearExpiredSessions() {
        let cleared = 0;

        for (const [port, session] of this._sessionCache) {
            if (this._isSessionExpired(session)) {
                await this.clearSession(port);
                cleared++;
            }
        }

        if (cleared > 0) {
            this.logger.info(`已清除 ${cleared} 个过期会话`);
        }

        return cleared;
    }

    // ========================================================================
    // 私有方法
    // ========================================================================

    /**
     * 确保会话目录存在
     * @private
     */
    async _ensureSessionDirectory() {
        try {
            await fs.mkdir(this.config.profilePath, { recursive: true });
            this.logger.debug(`会话目录已确保: ${this.config.profilePath}`);
        } catch (error) {
            this.logger.error(`创建会话目录失败: ${error.message}`);
            throw error;
        }
    }

    /**
     * 加载现有会话到缓存
     * @private
     */
    async _loadExistingSessions() {
        try {
            const files = await fs.readdir(this.config.profilePath);
            const sessionFiles = files.filter(f => f.startsWith('session_port_') && f.endsWith('.json'));

            for (const file of sessionFiles) {
                const match = file.match(/session_port_(\d+)\.json/);
                if (match) {
                    const port = parseInt(match[1]);
                    const session = await this._loadSessionFromFile(port);
                    if (session && !this._isSessionExpired(session)) {
                        this._sessionCache.set(port, session);
                        this.logger.debug(`加载端口 ${port} 会话到缓存`);
                    }
                }
            }
        } catch (error) {
            this.logger.warn(`加载现有会话失败: ${error.message}`);
        }
    }

    /**
     * 执行会话刷新（打开可见浏览器过验证）
     * @private
     * @param {number} port - 代理端口
     * @param {string} proxyUrl - 代理 URL
     * @returns {Promise<Object>} 会话对象
     */
    async _doRefreshSession(port, proxyUrl) {
        this.logger.info(`端口 ${port} 启动可见浏览器...`);

        // 获取隐身指纹
        const stealth = this._generateStealthHeaders();

        // 启动可见浏览器
        const browser = await chromium.launch({
            headless: this.config.headlessRefresh,
            slowMo: 50,
            args: [
                '--disable-blink-features=AutomationControlled',
                '--start-maximized',
                '--no-sandbox',
                '--disable-setuid-sandbox'
            ]
        });

        const context = await browser.newContext({
            viewport: stealth.viewport,
            userAgent: stealth.userAgent,
            extraHTTPHeaders: stealth.extraHTTPHeaders,
            proxy: {
                server: proxyUrl
            },
            ignoreHTTPSErrors: true
        });

        // 注入隐身脚本
        await this._injectStealthScripts(context);

        const page = await context.newPage();

        try {
            // 步骤 1: 访问 FotMob 首页
            this.logger.info(`端口 ${port} 访问 FotMob 首页...`);
            await page.goto(this.config.targetUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });

            // 步骤 2: 等待 Turnstile 验证
            this.logger.info(`端口 ${port} 等待 Turnstile 验证 (${this.config.turnstileTimeout}ms 超时)...`);
            await this._waitForTurnstile(page, port);

            // 步骤 3: 模拟人类行为
            await this._simulateHumanBehavior(page);

            // 步骤 4: 访问测试比赛页验证身份
            this.logger.info(`端口 ${port} 访问测试比赛页验证身份...`);
            await page.goto(this.config.testUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
            await this._delay(3000);

            // 步骤 5: 验证页面内容
            const content = await page.content();
            const hasTurnstile = content.includes('Turnstile') || content.includes('challenge');
            const hasMatchData = content.includes('xG') || content.includes('Expected') || content.includes('stats');

            if (hasTurnstile && !hasMatchData) {
                throw new Error('Turnstile 验证未通过');
            }

            if (!hasMatchData) {
                this.logger.warn(`端口 ${port} 未检测到比赛数据，但继续保存会话`);
            }

            // 步骤 6: 保存会话状态
            const state = await context.storageState();

            const session = {
                port,
                cookies: state.cookies || [],
                origins: state.origins || [],
                createdAt: Date.now(),
                expiresAt: Date.now() + (this.config.sessionTtlHours * 60 * 60 * 1000),
                userAgent: stealth.userAgent,
                viewport: stealth.viewport,
                proxyUrl
            };

            this.logger.success(`端口 ${port} 身份捕获成功！Cookie 数量: ${session.cookies.length}`);

            return session;

        } finally {
            await browser.close();
        }
    }

    /**
     * 等待 Turnstile 验证完成
     * @private
     * @param {import('playwright').Page} page - Playwright 页面对象
     * @param {number} port - 代理端口
     */
    async _waitForTurnstile(page, port) {
        const startTime = Date.now();

        while (Date.now() - startTime < this.config.turnstileTimeout) {
            const content = await page.content();
            const hasChallenge = content.includes('Turnstile') ||
                                 content.includes('challenge') ||
                                 content.includes('cf-browser-verification');

            if (!hasChallenge) {
                this.logger.success(`端口 ${port} Turnstile 验证通过！`);
                return;
            }

            // 随机滚动模拟人类行为
            await page.mouse.wheel(0, Math.floor(Math.random() * 200) + 50);
            await this._delay(1000);
        }

        // 超时但不一定失败，继续尝试
        this.logger.warn(`端口 ${port} Turnstile 等待超时，继续尝试...`);
    }

    /**
     * 模拟人类行为
     * @private
     * @param {import('playwright').Page} page - Playwright 页面对象
     */
    async _simulateHumanBehavior(page) {
        // 随机滚动 3-5 次
        const scrollCount = Math.floor(Math.random() * 3) + 3;
        for (let i = 0; i < scrollCount; i++) {
            await page.mouse.wheel(0, Math.floor(Math.random() * 300) + 100);
            await this._delay(Math.floor(Math.random() * 1000) + 500);
        }

        // 随机鼠标移动 5-10 次
        const moveCount = Math.floor(Math.random() * 6) + 5;
        for (let i = 0; i < moveCount; i++) {
            await page.mouse.move(
                Math.floor(Math.random() * 1800) + 100,
                Math.floor(Math.random() * 900) + 100,
                { steps: Math.floor(Math.random() * 10) + 5 }
            );
            await this._delay(Math.floor(Math.random() * 500) + 200);
        }
    }

    /**
     * 注入隐身脚本
     * @private
     * @param {import('playwright').BrowserContext} context - Playwright 上下文
     */
    async _injectStealthScripts(context) {
        await context.addInitScript(() => {
            /* eslint-disable no-undef */
            // 禁用 webdriver 标志
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

            // WebGL 伪装
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(p) {
                if (p === 37445) return 'Google Inc. (NVIDIA)';
                if (p === 37446) return 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)';
                return getParameter.apply(this, arguments);
            };

            // WebGL2 伪装
            if (typeof WebGL2RenderingContext !== 'undefined') {
                const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
                WebGL2RenderingContext.prototype.getParameter = function(p) {
                    if (p === 37445) return 'Google Inc. (NVIDIA)';
                    if (p === 37446) return 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)';
                    return getParameter2.apply(this, arguments);
                };
            }

            // 硬件伪装
            Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
            Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
            /* eslint-enable no-undef */
        });
    }

    /**
     * 生成隐身 Headers - V180: 使用深度隐身配置
     * @private
     * @returns {Object} 隐身配置
     */
    _generateStealthHeaders() {
        // V180: 使用与 ProductionHarvester 完全一致的深度隐身配置
        const userAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0 Safari/537.36';
        const viewport = { width: 1920, height: 1080 };

        return {
            userAgent,
            viewport,
            extraHTTPHeaders: {
                'sec-ch-ua': '"Chromium";v="131", "Google Chrome";v="131", "Not-A.Brand";v="99"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'none',
                'sec-fetch-user': '?1',
                'accept-language': 'en-US,en;q=0.9',
                'accept-encoding': 'gzip, deflate, br'
            }
        };
    }

    /**
     * 获取刷新锁
     * @private
     * @param {number} port - 代理端口
     * @returns {string|null} 锁 ID
     */
    _acquireRefreshLock(port) {
        const existing = this._refreshLocks.get(port);
        if (existing) {
            // 检查是否超时
            if (Date.now() - existing.timestamp < this.config.lockTimeout) {
                return null;
            }
            // 超时，强制释放
            this.logger.warn(`端口 ${port} 刷新锁超时，强制释放`);
            this._refreshLocks.delete(port);
        }

        // V4.46.5 HARDENING: 使用确定性 ID 生成器
        const lockId = generateLockId(port);
        this._refreshLocks.set(port, {
            lockId,
            timestamp: Date.now()
        });

        return lockId;
    }

    /**
     * 释放刷新锁
     * @private
     * @param {number} port - 代理端口
     * @param {string} lockId - 锁 ID
     */
    _releaseRefreshLock(port, lockId) {
        const existing = this._refreshLocks.get(port);
        if (existing && existing.lockId === lockId) {
            this._refreshLocks.delete(port);
        }
    }

    /**
     * 等待锁释放
     * @private
     * @param {number} port - 代理端口
     */
    async _waitForLockRelease(port) {
        const maxWait = this.config.lockTimeout;
        const startTime = Date.now();

        while (Date.now() - startTime < maxWait) {
            if (!this._refreshLocks.has(port)) {
                return;
            }
            await this._delay(1000);
        }
    }

    /**
     * 检查会话是否过期
     * @private
     * @param {Object} session - 会话对象
     * @returns {boolean} 是否过期
     */
    _isSessionExpired(session) {
        if (!session || !session.expiresAt) {
            return true;
        }
        return Date.now() > session.expiresAt;
    }

    /**
     * V179.1: 检测是否有 X Server（显示服务器）
     * @private
     * @returns {boolean} 是否有可用的显示服务器
     */
    _hasDisplayServer() {
        // 检查 DISPLAY 环境变量
        if (process.env.DISPLAY) {
            return true;
        }

        // 检查 WAYLAND_DISPLAY 环境变量
        if (process.env.WAYLAND_DISPLAY) {
            return true;
        }

        // 检查是否在 WSLg 环境中
        if (process.env.WSL_INTEROP) {
            return true;
        }

        return false;
    }

    /**
     * 指数退避
     * @private
     * @param {number} attempt - 尝试次数 (1-based)
     * @returns {number} 退避时间 (ms)
     */
    _exponentialBackoff(attempt) {
        // 1s -> 2s -> 4s
        const baseDelay = 1000 * Math.pow(2, attempt - 1);
        const delay = Math.min(baseDelay, 4000);

        // ±20% 抖动
        const jitter = delay * 0.2 * (Math.random() * 2 - 1);
        return Math.floor(delay + jitter);
    }

    /**
     * 延时辅助方法
     * @private
     * @param {number} ms - 延时毫秒数
     * @returns {Promise<void>}
     */
    _delay(ms) {
        return new Promise(resolve => {
            setTimeout(() => resolve(), ms);
        });
    }

    /**
     * 获取会话文件路径
     * @private
     * @param {number} port - 代理端口
     * @returns {string} 文件路径
     */
    _getSessionFilePath(port) {
        return path.join(this.config.profilePath, `session_port_${port}.json`);
    }

    /**
     * 保存会话到文件
     * @private
     * @param {number} port - 代理端口
     * @param {Object} session - 会话对象
     */
    async _saveSessionToFile(port, session) {
        const filePath = this._getSessionFilePath(port);
        await fs.writeFile(filePath, JSON.stringify(session, null, 2), 'utf8');
        this.logger.debug(`会话已保存: ${filePath}`);
    }

    /**
     * 从文件加载会话
     * @private
     * @param {number} port - 代理端口
     * @returns {Promise<Object|null>} 会话对象
     */
    async _loadSessionFromFile(port) {
        try {
            const filePath = this._getSessionFilePath(port);
            const content = await fs.readFile(filePath, 'utf8');
            return JSON.parse(content);
        } catch (error) {
            return null;
        }
    }
}

// ============================================================================
// 单例模式
// ============================================================================

let _instance = null;

/**
 * 获取 SessionManager 单例
 *
 * @param {Object} [options] - 配置选项
 * @returns {SessionManager} SessionManager 实例
 */
function getSessionManager(options) {
    if (!_instance) {
        _instance = new SessionManager(options);
    }
    return _instance;
}

/**
 * 重置单例（用于测试）
 */
function resetSingleton() {
    _instance = null;
}

// ============================================================================
// 导出
// ============================================================================

module.exports = {
    SessionManager,
    getSessionManager,
    resetSingleton,
    DEFAULT_CONFIG
};
