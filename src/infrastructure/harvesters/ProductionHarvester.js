/**
 * ProductionHarvester - V186 ENTERPRISE 企业级收割引擎
 * ====================================
 *
 * 从 scripts/ops/run_production_harvest.js 提取核心业务逻辑
 * 封装为可复用的收割器类
 *
 * V177 升级:
 * - Ghost Protocol 隐身衣 (30+ UA 池 + Referer 伪装)
 * - Sec-Ch-Ua 浏览器指纹完整伪装
 *
 * V178 升级:
 * - 首页预热 (建立 Session 信任)
 * - 人类行为模拟 (10-15 次鼠标位移)
 * - 完整 sec-fetch-* Headers
 * - 指数退避重试 (1s -> 2s -> 4s)
 * - 代码质量: ESLint 零缺陷标准
 *
 * V178.2 升级 (NetworkShield Bridge):
 * - 接入 22 节点代理池 (172.25.16.1:7890-7911)
 * - Session Stickiness (身份绑定)
 * - 熔断器 + 自动故障切换
 * - MAX_WORKERS 提升至 6
 *
 * V179 升级 (AUTO-PILOT):
 * - SessionManager 集成 (无人值守身份管理)
 * - 自动身份捕获 (可见浏览器过 Turnstile)
 * - 身份热加载 (Cookie 自动注入)
 * - 22 节点一对一身份绑定
 *
 * V180 升级 (DEEP-STEALTH):
 * - playwright-stealth 深度隐身插件集成
 * - 硬件信息模拟 (GPU、CPU 核心、内存)
 * - WebGL 指纹伪装 (_vendor, _renderer)
 * - 字体库模拟 (fonts-shim)
 * - 22 节点独立身份存储 (一人一车一证)
 *
 * V181 升级 (IRON-SHIELD):
 * - 弹性重试: 非致命错误自动重试 3 次
 * - 端口避障: 重试时随机更换代理端口
 * - 日志精简: 只在最终成功/失败时输出
 * - 最终扫尾: 自动多轮收割直到 100%
 *
 * V186 升级 (ENTERPRISE-HARDENING):
 * - 工业级日志系统: Winston + 日志轮转 + JSON 格式
 * - 错误分类: FATAL (程序退出) vs RETRYABLE (自动重试)
 * - 优雅停机: SIGINT/SIGTERM 信号处理 + 安全关闭
 * - 完整 JSDoc: 所有方法添加文档注释
 * - 日志元数据: WorkerID、ProxyPort、MatchID、Attempt
 *
 * @module infrastructure/harvesters/ProductionHarvester
 * @version V186.0.0
 */

'use strict';

const pLimit = require('p-limit');
const { chromium } = require('playwright');
const { Pool } = require('pg');

// 导入核心组件
const { preFlightCleanup } = require('../../core/process/ZombieKiller');
const { transformToApiFormat } = require('../../parsers/fotmob/NextDataParser');

// 导入配置
const FactoryConfig = require('../../../config/factory_config');
const { DatabaseConfig } = require('../database/PostgresClient');

// V178.2: 导入 NetworkShield
const { getNetworkShield } = require('../network/NetworkShield');

// V179: 导入 SessionManager
const { getSessionManager } = require('../network/SessionManager');

// V186: 导入企业级日志系统
const { logger } = require('../utils/Logger');

// ============================================================================
// V186: 错误类型分类系统
// ============================================================================

/**
 * 错误严重级别枚举
 * @readonly
 * @enum {string}
 */
const ErrorSeverity = {
    /** 致命错误 - 程序必须退出 */
    FATAL: 'FATAL',
    /** 可重试错误 - 自动重试 */
    RETRYABLE: 'RETRYABLE',
    /** 警告 - 可忽略 */
    WARNING: 'WARNING'
};

/**
 * V186: 错误类型分类映射
 * 根据错误消息判断错误严重级别
 * @param {Error} error - 错误对象
 * @returns {{severity: ErrorSeverity, errorType: string, reason: string}}
 */
function classifyError(error) {
    const msg = error.message.toLowerCase();
    const errorName = error.name || 'UnknownError';

    // === FATAL: 程序必须退出 ===
    const fatalPatterns = [
        { pattern: 'authentication failed', type: 'AUTH_FAILURE', reason: '身份验证失败，请检查 Cookie/Session' },
        { Pattern: 'invalid credentials', type: 'AUTH_FAILURE', reason: '凭证无效，需要重新登录' },
        { pattern: 'database connection failed', type: 'DB_FAILURE', reason: '数据库连接失败' },
        { pattern: 'econnrefused', type: 'DB_FAILURE', reason: '数据库拒绝连接' },
        { pattern: 'out of memory', type: 'OOM', reason: '内存不足' },
        { pattern: 'browser crashed', type: 'BROWSER_CRASH', reason: '浏览器崩溃' }
    ];

    for (const { pattern, type, reason } of fatalPatterns) {
        if (msg.includes(pattern)) {
            return { severity: ErrorSeverity.FATAL, errorType: type, reason };
        }
    }

    // === RETRYABLE: 可自动重试 ===
    const retryablePatterns = [
        { pattern: '403', type: 'HTTP_403', reason: '被反爬拦截，切换端口重试' },
        { Pattern: 'forbidden', type: 'HTTP_403', reason: '访问被拒绝，需要切换身份' },
        { pattern: 'turnstile', type: 'TURNSTILE', reason: 'Turnstile 验证，切换端口' },
        { pattern: 'cloudflare', type: 'CF_BLOCK', reason: 'Cloudflare 拦截' },
        { pattern: 'timeout', type: 'TIMEOUT', reason: '请求超时' },
        { pattern: 'econnreset', type: 'NETWORK', reason: '连接重置' },
        { pattern: 'enotfound', type: 'DNS', reason: 'DNS 解析失败' },
        { pattern: 'network error', type: 'NETWORK', reason: '网络错误' },
        { pattern: 'socket hang up', type: 'NETWORK', reason: 'Socket 断开' },
        { pattern: 'proxy', type: 'PROXY', reason: '代理错误' }
    ];

    for (const { pattern, type, reason } of retryablePatterns) {
        if (msg.includes(pattern)) {
            return { severity: ErrorSeverity.RETRYABLE, errorType: type, reason };
        }
    }

    // === 默认: 根据错误类型判断 ===
    if (errorName === 'TimeoutError') {
        return { severity: ErrorSeverity.RETRYABLE, errorType: 'TIMEOUT', reason: 'Playwright 超时' };
    }

    // 数据问题不重试
    if (msg.includes('no_data') || msg.includes('size_too_small')) {
        return { severity: ErrorSeverity.WARNING, errorType: 'DATA_QUALITY', reason: '数据质量问题' };
    }

    // 未知错误，保守处理为可重试
    return { severity: ErrorSeverity.RETRYABLE, errorType: 'UNKNOWN', reason: '未知错误' };
}

// V180: playwright-stealth 有兼容性问题，// 改用 Playwright 原生隐身功能 + 自定义脚本注入
// const { stealth } = require('playwright-stealth');

// ============================================================================
// V180: 深度隐身配置 - 完整硬件指纹
// ============================================================================

/**
 * V185: WebGL 渲染器池 - 用于指纹随机化
 * 避免所有 Worker 使用完全相同的硬件指纹
 */
const WEBGL_RENDERER_POOL = [
    'ANGLE (AMD, AMD Radeon(TM) Graphics (0x000013C0) Direct3D11 vs_5_0 ps_5_0, D3D11)',
    'ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 (0x00002183) Direct3D11 vs_5_0 ps_5_0, D3D11)',
    'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 (0x00002503) Direct3D11 vs_5_0 ps_5_0, D3D11)',
    'ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 (0x00002484) Direct3D11 vs_5_0 ps_5_0, D3D11)',
    'ANGLE (NVIDIA, NVIDIA GeForce GTX 1080 (0x00001B80) Direct3D11 vs_5_0 ps_5_0, D3D11)',
    'ANGLE (Intel, Intel(R) UHD Graphics 630 (0x00003E9B) Direct3D11 vs_5_0 ps_5_0, D3D11)',
    'ANGLE (Intel, Intel(R) Iris(R) Xe Graphics (0x000049A5) Direct3D11 vs_5_0 ps_5_0, D3D11)',
    'ANGLE (AMD, AMD Radeon RX 580 Series (0x000067DF) Direct3D11 vs_5_0 ps_5_0, D3D11)'
];

/**
 * V185: 生成随机化的深度隐身配置
 * 每次调用生成略微不同的硬件指纹，避免特征过于单一
 * @param {number} workerId - Worker ID，用于确定性随机
 * @returns {Object} 随机化的隐身配置
 */
function generateStealthConfig(workerId = 1) {
    // 基于 workerId 的确定性随机种子（同一 worker 每次生成相同配置）
    const seed = workerId * 17 + 42;

    // CPU 核心数: 8-24 之间（主流配置）
    const hardwareConcurrency = 8 + (seed % 17); // 8-24

    // 内存: 4, 8, 16, 32 GB（主流配置）
    const memoryOptions = [4, 8, 8, 16, 16, 16, 32];
    const deviceMemory = memoryOptions[seed % memoryOptions.length];

    // WebGL 渲染器
    const renderer = WEBGL_RENDERER_POOL[seed % WEBGL_RENDERER_POOL.length];
    const vendor = renderer.includes('NVIDIA') ? 'Google Inc. (NVIDIA)' :
                   renderer.includes('Intel') ? 'Google Inc. (Intel)' :
                   'Google Inc. (AMD)';

    // 视口尺寸微调 (±50px)
    const viewportWidth = 1920 + ((seed % 5) - 2) * 20; // 1880-1960
    const viewportHeight = 1080 + ((seed % 5) - 2) * 15; // 1050-1110

    return {
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        viewport: { width: viewportWidth, height: viewportHeight },
        deviceScaleFactor: 1,
        locale: 'en-US',
        timezoneId: 'Europe/London',
        platform: 'Win32',
        hardwareConcurrency,
        deviceMemory,
        webgl: { vendor, renderer },
        fonts: [
            'Arial', 'Arial Unicode MS', 'Calibri', 'Cambria', 'Georgia', 'Times New Roman',
            'Segoe UI', 'Tahoma', 'Verdana', 'Helvetica Neue', 'Helvetica', 'Helvetica Neue Cyr'
        ]
    };
}

/**
 * V180: 深度隐身配置 (默认值，用于向后兼容)
 * @deprecated 使用 generateStealthConfig(workerId) 替代
 */
const DEEP_STEALTH_CONFIG = generateStealthConfig(1);

// ============================================================================
// V179.2: 固定指纹配置 - 与 capture_auth.js 完全一致
// ============================================================================

/**
 * V179.2: 固定指纹 - 必须与 capture_auth.js 中使用的指纹完全一致
 * 这是从宿主机浏览器捕获 Cookie 时使用的指纹
 */
const FIXED_FINGERPRINT = {
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
    locale: 'en-US',
    timezoneId: 'Europe/London',
    platform: 'Win32'
};

// V177: Ghost Protocol - 30+ 浏览器指纹池 (保留备用)
const GHOST_UA_POOL = [
    // Chrome 桌面端 (Windows)
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
    // Chrome 桌面端 (macOS)
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    // Edge 桌面端
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0',
    // Firefox 桌面端
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:135.0) Gecko/20100101 Firefox/135.0',
    // Safari 桌面端 (macOS)
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15'
];

const GHOST_VIEWPORTS = [
    { width: 1920, height: 1080 },
    { width: 1366, height: 768 },
    { width: 1440, height: 900 },
    { width: 1536, height: 864 },
    { width: 1280, height: 720 },
    { width: 1600, height: 900 },
    { width: 2560, height: 1440 },
    { width: 1287, height: 1271 }
];

/**
 * 获取随机 UA (备用)
 * @returns {string} 随机 User-Agent
 */
function getRandomUA() {
    return GHOST_UA_POOL[Math.floor(Math.random() * GHOST_UA_POOL.length)];
}

/**
 * 获取随机视口 (备用)
 * @returns {Object} 视口配置
 */
function getRandomViewport() {
    return GHOST_VIEWPORTS[Math.floor(Math.random() * GHOST_VIEWPORTS.length)];
}

/**
 * V179.2: 生成固定指纹 Headers - 与 capture_auth.js 一致
 * @param {boolean} useFixed - 是否使用固定指纹 (默认 true)
 * @returns {Object} 包含 userAgent, viewport, extraHTTPHeaders 的对象
 */
function generateStealthHeaders(useFixed = true) {
    // V179.2: 强制使用固定指纹，与 capture_auth.js 一致
    if (useFixed) {
        const ua = FIXED_FINGERPRINT.userAgent;
        const viewport = FIXED_FINGERPRINT.viewport;

        return {
            userAgent: ua,
            viewport,
            locale: FIXED_FINGERPRINT.locale,
            timezoneId: FIXED_FINGERPRINT.timezoneId,
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

    // 备用：随机指纹
    const ua = getRandomUA();
    const viewport = getRandomViewport();
    const isChrome = ua.includes('Chrome') && !ua.includes('Edg');
    const isEdge = ua.includes('Edg');

    let secChUa = '';
    if (isChrome) {
        secChUa = '"Chromium";v="133", "Google Chrome";v="133", "Not-A.Brand";v="99"';
    } else if (isEdge) {
        secChUa = '"Chromium";v="133", "Microsoft Edge";v="133", "Not-A.Brand";v="99"';
    }

    return {
        userAgent: ua,
        viewport,
        extraHTTPHeaders: isChrome || isEdge ? {
            'sec-ch-ua': secChUa,
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': ua.includes('Windows') ? '"Windows"' : '"macOS"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'accept-language': 'en-US,en;q=0.9',
            'accept-encoding': 'gzip, deflate, br'
        } : {}
    };
}

// ============================================================================
// V178.2: Worker 身份绑定 (Session Stickiness)
// ============================================================================

/**
 * WorkerIdentity - 每个 Worker 的身份绑定
 * 确保【代理 IP + User-Agent + 视口尺寸】在一次 Session 中保持一致
 */
class WorkerIdentity {
    constructor(workerId, proxy, stealth) {
        this.workerId = workerId;
        this.proxy = proxy;
        this.stealth = stealth;
        this.sessionId = `WORKER-${workerId}-${Date.now()}`;
        this.createdAt = Date.now();
        this.requestCount = 0;
        this.successCount = 0;
        this.failureCount = 0;
    }

    /**
     * 记录请求
     */
    recordRequest(success) {
        this.requestCount++;
        if (success) {
            this.successCount++;
        } else {
            this.failureCount++;
        }
    }

    /**
     * 获取成功率
     * @returns {number} 成功率 (0-1)
     */
    getSuccessRate() {
        if (this.requestCount === 0) return 1;
        return this.successCount / this.requestCount;
    }

    /**
     * 是否需要更换身份（连续失败 3 次）
     * @returns {boolean}
     */
    needsReidentity() {
        return this.failureCount >= 3 && this.getSuccessRate() < 0.5;
    }
}

// ============================================================================
// ProductionHarvester 类
// ============================================================================

class ProductionHarvester {
    /**
     * V186: 创建 ProductionHarvester 实例
     * @param {Object} [config={}] - 配置选项
     * @param {number} [config.maxWorkers=6] - 最大 Worker 数量
     * @param {number} [config.minDelayMs=10000] - 最小延时（毫秒）
     * @param {number} [config.maxDelayMs=20000] - 最大延时（毫秒）
     * @param {number} [config.batchSize=500] - 每批次任务数
     * @param {string} [config.leagueFilter] - 联赛过滤器
     * @param {boolean} [config.dryRun=false] - 试运行模式
     * @param {number} [config.maxRetries=3] - 最大重试次数
     * @param {number} [config.retryDelayMs=5000] - 重试延时（毫秒）
     * @param {number} [config.maxSweepRounds=3] - 最大扫尾轮数
     * @param {number} [config.targetSuccessRate=1.0] - 目标成功率
     * @param {boolean} [config.verboseLogging=false] - 详细日志模式
     */
    constructor(config = {}) {
        // V186: ENTERPRISE 配置 - 工业级日志 + 优雅停机
        this.config = {
            maxWorkers: parseInt(process.env.MAX_WORKERS) || config.maxWorkers || 6,
            minDelayMs: parseInt(process.env.MIN_DELAY_MS) || config.minDelayMs || 10000,
            maxDelayMs: parseInt(process.env.MAX_DELAY_MS) || config.maxDelayMs || 20000,
            batchSize: parseInt(process.env.BATCH_SIZE) || config.batchSize || 500,
            leagueFilter: config.leagueFilter || process.env.LEAGUE_FILTER || null,
            dryRun: config.dryRun || false,
            useFixedFingerprint: config.useFixedFingerprint !== false,
            // V181: 弹性重试配置
            maxRetries: parseInt(process.env.MAX_RETRIES) || config.maxRetries || 3,
            retryDelayMs: parseInt(process.env.RETRY_DELAY_MS) || config.retryDelayMs || 5000,
            // V181: 最终扫尾配置
            maxSweepRounds: parseInt(process.env.MAX_SWEEP_ROUNDS) || config.maxSweepRounds || 3,
            targetSuccessRate: parseFloat(process.env.TARGET_SUCCESS_RATE) || config.targetSuccessRate || 1.0,
            // V186: 日志精简模式
            verboseLogging: process.env.VERBOSE_LOGGING === 'true' || config.verboseLogging || false,
            // V186: 优雅停机配置
            shutdownTimeoutMs: parseInt(process.env.SHUTDOWN_TIMEOUT_MS) || config.shutdownTimeoutMs || 30000,
            ...config
        };

        this.pool = null;
        this.browser = null;
        this.stats = {
            total: 0,
            processed: 0,
            success: 0,
            failed: 0,
            retries: 0,
            sweepRounds: 0
        };
        this.startTime = null;

        // V178.2: NetworkShield 代理管理器
        this.networkShield = null;

        // V179: SessionManager 身份管理器
        this.sessionManager = null;

        // V178.2: Worker 身份池 (Session Stickiness)
        this.workerIdentities = new Map();

        // V181: 端口避障 - 记录失败端口
        this.failedPorts = new Set();

        // V181: 可用端口池 (7890-7911)
        this.availablePorts = Array.from({ length: 22 }, (_, i) => 7890 + i);

        // V186: 优雅停机状态
        this.isShuttingDown = false;
        this.activeWorkers = new Set();
        this.shutdownPromise = null;
        this.workerLogger = logger.createWorkerLogger(0, 0); // 默认日志器

        // V186: 注册信号处理器
        this._setupGracefulShutdown();
    }

    // ========================================================================
    // V186: 优雅停机机制
    // ========================================================================

    /**
     * V186: 设置优雅停机信号处理器
     * 监听 SIGINT (Ctrl+C) 和 SIGTERM 信号
     * @private
     */
    _setupGracefulShutdown() {
        const handler = async (signal) => {
            if (this.isShuttingDown) {
                logger.warn('🔄 已在停机中，请稍候...');
                return;
            }

            this.isShuttingDown = true;
            const activeCount = this.activeWorkers.size;
            logger.logGracefulShutdown(signal, activeCount);

            // 设置停机超时
            const timeoutId = setTimeout(() => {
                logger.warn(`⏰ 停机超时 (${this.config.shutdownTimeoutMs}ms)，强制退出`);
                process.exit(1);
            }, this.config.shutdownTimeoutMs);

            try {
                // 等待所有活跃 Worker 完成
                if (activeCount > 0) {
                    logger.info(`⏳ 等待 ${activeCount} 个活跃 Worker 完成...`);
                    await Promise.race([
                        this._waitForWorkers(),
                        this._delay(this.config.shutdownTimeoutMs - 1000)
                    ]);
                }

                // 清理资源
                await this._cleanup();

                clearTimeout(timeoutId);
                logger.logShutdownComplete(Date.now() - (this.shutdownStartTime || Date.now()), {
                    processed: this.stats.processed,
                    success: this.stats.success,
                    failed: this.stats.failed
                });

                process.exit(0);
            } catch (err) {
                logger.error('停机过程中发生错误', err);
                process.exit(1);
            }
        };

        process.on('SIGINT', () => handler('SIGINT'));
        process.on('SIGTERM', () => handler('SIGTERM'));
    }

    /**
     * V186: 等待所有活跃 Worker 完成
     * @private
     * @returns {Promise<void>}
     */
    async _waitForWorkers() {
        while (this.activeWorkers.size > 0) {
            logger.debug(`等待 ${this.activeWorkers.size} 个 Worker...`);
            await this._delay(500);
        }
    }

    /**
     * V186: 清理资源（浏览器、数据库连接等）
     * @private
     * @returns {Promise<void>}
     */
    async _cleanup() {
        // 关闭浏览器
        if (this.browser) {
            try {
                await this.browser.close();
                logger.info('✅ 浏览器已关闭');
            } catch (err) {
                logger.warn('浏览器关闭失败', { error: err.message });
            }
        }

        // 关闭数据库连接池
        if (this.pool) {
            try {
                await this.pool.end();
                logger.info('✅ 数据库连接池已关闭');
            } catch (err) {
                logger.warn('数据库连接池关闭失败', { error: err.message });
            }
        }
    }

    /**
     * V186: 注册 Worker 为活跃状态
     * @param {number} workerId - Worker ID
     */
    _registerWorker(workerId) {
        this.activeWorkers.add(workerId);
    }

    /**
     * V186: 注销 Worker 活跃状态
     * @param {number} workerId - Worker ID
     */
    _unregisterWorker(workerId) {
        this.activeWorkers.delete(workerId);
    }

    // ========================================================================
    // V178: 核心辅助方法
    // ========================================================================

    /**
     * V178: 延时辅助方法 - 解决 Promise executor return 问题
     * @param {number} ms - 延时毫秒数
     * @returns {Promise<void>}
     */
    _delay(ms) {
        return new Promise(resolve => {
            setTimeout(resolve, ms);
        });
    }

    /**
     * V178: 生成指定范围内的随机整数
     * @param {number} min - 最小值
     * @param {number} max - 最大值
     * @returns {number} 随机整数
     */
    _randomInRange(min, max) {
        return Math.floor(Math.random() * (max - min + 1)) + min;
    }

    /**
     * V179.1: 直接从 browser_state.json 加载 Cookie
     * 兼容 Windows 助手的同步文件
     * @param {import('playwright').BrowserContext} context - Playwright 上下文
     * @returns {Promise<boolean>} 是否成功加载
     */
    async _loadBrowserStateCookies(context) {
        const fs = require('fs').promises;
        const statePath = '/app/data/browser_profile/browser_state.json';

        try {
            const content = await fs.readFile(statePath, 'utf8');
            const state = JSON.parse(content);

            if (state.cookies && state.cookies.length > 0) {
                // 过滤出有效的 Cookie
                const validCookies = state.cookies.filter(c => {
                    // 排除过期 Cookie
                    if (c.expires && c.expires < Date.now() / 1000) {
                        return false;
                    }
                    return true;
                });

                if (validCookies.length > 0) {
                    await context.addCookies(validCookies);
                    console.log(`🔑 浏览器身份加载成功: ${validCookies.length} 个 Cookie`);
                    return true;
                }
            }
            return false;
        } catch (error) {
            // 文件不存在或解析失败
            return false;
        }
    }

    // ========================================================================
    // V178.2: NetworkShield 桥接方法
    // ========================================================================

    /**
     * V179.1: 预清理 NetworkShield 锁文件（自愈机制）
     * 在异常退出后，锁文件可能残留，导致后续启动失败
     * @returns {Promise<number>} 清理的锁文件数量
     */
    async _preFlightCleanupNetworkLocks() {
        const fs = require('fs').promises;
        const path = require('path');

        const lockDirs = [
            '/app/data/network',
            '/app/data/registry',
            '/app/config',           // V179.1: Registry 锁文件位置
            './data/network',
            './data/registry',
            './config'
        ];

        // V179.1: 额外检查特定的锁文件路径
        const specificLockFiles = [
            '/app/config/.registry.lock',
            './config/.registry.lock'
        ];

        let cleanedCount = 0;

        // 清理目录中的锁文件
        for (const dir of lockDirs) {
            try {
                const files = await fs.readdir(dir);
                const lockFiles = files.filter(f => f.endsWith('.lock'));

                for (const lockFile of lockFiles) {
                    const lockPath = path.join(dir, lockFile);
                    try {
                        await fs.unlink(lockPath);
                        console.log(`🔧 已清理残留锁文件: ${lockPath}`);
                        cleanedCount++;
                    } catch (unlinkError) {
                        // 忽略删除失败
                    }
                }
            } catch (dirError) {
                // 目录不存在，忽略
            }
        }

        // 清理特定路径的锁文件
        for (const lockPath of specificLockFiles) {
            try {
                await fs.unlink(lockPath);
                console.log(`🔧 已清理残留锁文件: ${lockPath}`);
                cleanedCount++;
            } catch (unlinkError) {
                // 文件不存在或删除失败，忽略
            }
        }

        if (cleanedCount > 0) {
            console.log(`✅ 预清理完成: 已移除 ${cleanedCount} 个残留锁文件`);
        }

        return cleanedCount;
    }

    /**
     * V178.2: 初始化 NetworkShield 代理池
     * V179.1: 增加锁文件自愈 + 宽容启动
     * @returns {Promise<void>}
     */
    async _initNetworkShield() {
        // V179.1: 预清理残留锁文件
        await this._preFlightCleanupNetworkLocks();

        this.networkShield = getNetworkShield({
            proxyHost: FactoryConfig.PROXY_CONFIG.serverTemplate.match(/[\d.]+/)[0] || '172.25.16.1',
            portRange: { start: 7890, end: 7911 },
            logLevel: 'info',
            maxConsecutiveFailures: 3,
            cooldownMinutes: 5
        });

        // V179.1: 宽容启动 - 捕获初始化错误
        try {
            await this.networkShield.initialize();

            const status = this.networkShield.getStatus();
            console.log(`📡 NetworkShield 已就绪: ${status.nodes.active}/${status.nodes.total} 节点可用`);
        } catch (initError) {
            console.error(`⚠️ NetworkShield 初始化失败: ${initError.message}`);
            console.log(`📡 NetworkShield 将在降级模式下运行（使用 FactoryConfig 代理池）`);

            // 不抛出错误，允许系统继续运行
            // NetworkShield 的其他方法会处理 null 情况
        }
    }

    /**
     * V179: 初始化 SessionManager 身份管理器
     * @returns {Promise<void>}
     */
    async _initSessionManager() {
        this.sessionManager = getSessionManager({
            profilePath: '/app/data/sessions',
            sessionTtlHours: 24,
            maxRefreshAttempts: 3,
            headlessRefresh: false
        });

        await this.sessionManager.initialize();

        const stats = this.sessionManager.getStats();
        console.log(`🔑 SessionManager 已就绪: ${stats.cachedSessions} 个会话缓存`);
    }

    /**
     * V178.2: 为 Worker 分配身份（代理 IP + User-Agent + 视口）
     * 实现 Session Stickiness
     * V179: 集成 SessionManager 自动身份管理
     * V179.1: 增加 NetworkShield 降级模式兼容
     * @param {number} workerId - Worker 编号
     * @returns {Promise<WorkerIdentity>} Worker 身份
     */
    async _assignWorkerIdentity(workerId) {
        // 检查是否已有身份且不需要更换
        const existing = this.workerIdentities.get(workerId);
        if (existing && !existing.needsReidentity()) {
            console.log(`🔄 Worker ${workerId} 复用身份: Port ${existing.proxy.port}`);
            return existing;
        }

        // 从 NetworkShield 获取健康代理（如果可用）
        const sessionId = `WORKER-${workerId}`;
        let proxyAssignment;

        // V179.1: 检查 NetworkShield 是否可用
        if (this.networkShield && typeof this.networkShield.getNextHealthyProxy === 'function') {
            try {
                proxyAssignment = await this.networkShield.getNextHealthyProxy(sessionId);
            } catch (error) {
                console.warn(`⚠️ Worker ${workerId} NetworkShield 获取代理失败: ${error.message}`);
                // 降级：使用 FactoryConfig 的代理池
                const port = FactoryConfig.PROXY_CONFIG.getPortByWorker(workerId);
                proxyAssignment = {
                    sessionId,
                    port,
                    url: FactoryConfig.PROXY_CONFIG.getServer(port)
                };
            }
        } else {
            // NetworkShield 不可用，直接使用 FactoryConfig
            console.log(`📡 Worker ${workerId} 使用 FactoryConfig 代理池（NetworkShield 降级模式）`);
            const port = FactoryConfig.PROXY_CONFIG.getPortByWorker(workerId);
            proxyAssignment = {
                sessionId,
                port,
                url: FactoryConfig.PROXY_CONFIG.getServer(port)
            };
        }

        // V179: 尝试获取或刷新会话（自动身份管理）
        if (this.sessionManager) {
            try {
                const session = await this.sessionManager.getOrRefreshSession(proxyAssignment.port, {
                    proxyUrl: proxyAssignment.url
                });
                if (session) {
                    console.log(`🔑 Worker ${workerId} 会话状态: ${session.cookies?.length || 0} Cookie, 过期于 ${new Date(session.expiresAt).toLocaleString()}`);
                }
            } catch (error) {
                console.warn(`⚠️ Worker ${workerId} 会话刷新失败: ${error.message}`);
                // 继续使用无会话模式
            }
        }

        // 生成隐身指纹
        const stealth = generateStealthHeaders();

        // 创建 Worker 身份
        const identity = new WorkerIdentity(workerId, proxyAssignment, stealth);
        this.workerIdentities.set(workerId, identity);

        console.log(`🆔 Worker ${workerId} 新身份绑定:`);
        console.log(`   Proxy: ${proxyAssignment.url}`);
        console.log(`   UA: ${stealth.userAgent.substring(0, 50)}...`);
        console.log(`   Viewport: ${stealth.viewport.width}x${stealth.viewport.height}`);

        return identity;
    }

    /**
     * V178.2: 标记代理成功
     * @param {number} workerId - Worker 编号
     * @param {number} latency - 延迟（毫秒）
     */
    async _markProxySuccess(workerId, latency = 0) {
        const identity = this.workerIdentities.get(workerId);
        if (identity && identity.proxy && this.networkShield) {
            identity.recordRequest(true);
            await this.networkShield.markProxySuccess(identity.proxy.port, latency);
        }
    }

    /**
     * V178.2: 标记代理失败 + 熔断切换
     * @param {number} workerId - Worker 编号
     * @param {string} reason - 失败原因
     */
    async _markProxyFailed(workerId, reason) {
        const identity = this.workerIdentities.get(workerId);
        if (identity && identity.proxy && this.networkShield) {
            identity.recordRequest(false);
            await this.networkShield.markProxyFailed(identity.proxy.port, reason);

            // V181: 记录失败端口用于避障
            this.failedPorts.add(identity.proxy.port);

            // 检查是否需要熔断切换
            if (identity.needsReidentity()) {
                console.log(`⚡ Worker ${workerId} 触发熔断，准备切换身份...`);
                this.workerIdentities.delete(workerId);
            }
        }
    }

    // ========================================================================
    // V181: IRON-SHIELD 弹性重试机制
    // ========================================================================

    /**
     * V181: 判断是否为可重试的错误（非 403 的网络错误）
     * @param {Error} error - 错误对象
     * @returns {boolean} 是否可重试
     */
    _isRetryableError(error) {
        const msg = error.message || '';
        const retryablePatterns = [
            'ERR_CONNECTION_CLOSED',
            'ERR_CONNECTION_RESET',
            'ERR_CONNECTION_TIMED_OUT',
            'ERR_TIMED_OUT',
            'ETIMEDOUT',
            'ECONNRESET',
            'ECONNREFUSED',
            'ENOTFOUND',
            'net::ERR_',
            'TIMEOUT',
            'Navigation timeout'
        ];

        // 403 错误不可重试（反爬机制，重试无意义）
        const nonRetryablePatterns = [
            '403',
            'ERR_BLOCKED',
            'Access denied',
            'Forbidden',
            'Turnstile'
        ];

        // 检查是否为不可重试错误
        for (const pattern of nonRetryablePatterns) {
            if (msg.includes(pattern)) {
                return false;
            }
        }

        // 检查是否为可重试错误
        for (const pattern of retryablePatterns) {
            if (msg.includes(pattern)) {
                return true;
            }
        }

        // 默认：数据问题不重试
        if (msg.includes('NO_DATA') || msg.includes('SIZE_TOO_SMALL')) {
            return false;
        }

        return false;
    }

    /**
     * V181: 获取避障端口（随机选择非失败端口）
     * @param {number} excludePort - 需要排除的端口
     * @returns {number} 新端口号
     */
    _getAlternativePort(excludePort) {
        // 过滤掉失败的端口
        const healthyPorts = this.availablePorts.filter(p =>
            p !== excludePort && !this.failedPorts.has(p)
        );

        if (healthyPorts.length === 0) {
            // 所有端口都失败，清空失败记录重新开始
            console.log('⚠️ 所有端口都失败，重置避障记录...');
            this.failedPorts.clear();
            return this.availablePorts[Math.floor(Math.random() * this.availablePorts.length)];
        }

        return healthyPorts[Math.floor(Math.random() * healthyPorts.length)];
    }

    /**
     * V181: 强制更换 Worker 端口（端口避障）
     * @param {number} workerId - Worker 编号
     * @param {number} failedPort - 失败的端口
     * @returns {Promise<WorkerIdentity>} 新身份
     */
    async _forceReassignPort(workerId, failedPort) {
        const newPort = this._getAlternativePort(failedPort);

        // 清除旧身份
        this.workerIdentities.delete(workerId);

        // 创建新身份
        const sessionId = `WORKER-${workerId}-RETRY-${Date.now()}`;
        const proxyAssignment = {
            sessionId,
            port: newPort,
            url: `http://172.25.16.1:${newPort}`
        };

        const stealth = generateStealthHeaders();
        const identity = new WorkerIdentity(workerId, proxyAssignment, stealth);
        this.workerIdentities.set(workerId, identity);

        return identity;
    }

    /**
     * V181: 带弹性重试的单场收割
     * @param {Object} match - 比赛信息
     * @param {number} index - 任务索引
     * @param {number} maxRetries - 最大重试次数 (默认 3)
     * @returns {Promise<Object>} 收割结果
     */
    async _harvestWithRetry(match, index, maxRetries = 3) {
        const { match_id, home_team, away_team } = match;
        let lastError = null;

        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                const result = await this._harvestSingleMatch(match, index, attempt);

                // 成功
                if (result.success) {
                    if (attempt > 1) {
                        console.log(`✅ [RETRY-${attempt}] ${home_team} vs ${away_team} 重试成功`);
                        this.stats.retries++;
                    }
                    return result;
                }

                // 失败但不可重试
                if (!this._isRetryableError(new Error(result.error))) {
                    return result;
                }

                lastError = result.error;

            } catch (error) {
                lastError = error.message;

                // 不可重试的错误直接返回
                if (!this._isRetryableError(error)) {
                    return {
                        success: false,
                        match_id,
                        error: error.message,
                        attempts: attempt
                    };
                }
            }

            // 准备重试：指数退避 + 端口避障
            if (attempt < maxRetries) {
                const backoffMs = Math.min(1000 * Math.pow(2, attempt), 10000);
                const workerId = (index % this.config.maxWorkers) + 1;
                const currentIdentity = this.workerIdentities.get(workerId);

                if (currentIdentity) {
                    // 端口避障：切换到新端口
                    await this._forceReassignPort(workerId, currentIdentity.proxy.port);
                    console.log(`🔄 [RETRY-${attempt + 1}] ${home_team} vs ${away_team} 切换端口避障...`);
                }

                await this._delay(backoffMs);
            }
        }

        // 所有重试失败
        return {
            success: false,
            match_id,
            error: `重试 ${maxRetries} 次后仍失败: ${lastError}`,
            attempts: maxRetries
        };
    }

    /**
     * V181: 单次收割尝试（内部方法）
     * @param {Object} match - 比赛信息
     * @param {number} index - 任务索引
     * @param {number} attempt - 当前尝试次数
     * @returns {Promise<Object>} 收割结果
     */
    async _harvestSingleMatch(match, index, attempt = 1) {
        const { match_id, external_id, home_team, away_team } = match;
        const workerId = (index % this.config.maxWorkers) + 1;
        const isRetry = attempt > 1;

        // 随机延迟（重试时缩短延迟）
        const baseDelay = isRetry ? 3000 : this.config.minDelayMs;
        const maxDelay = isRetry ? 6000 : this.config.maxDelayMs;
        const delay = baseDelay + Math.random() * (maxDelay - baseDelay);
        await this._delay(delay);

        // 获取/刷新 Worker 身份
        const identity = await this._assignWorkerIdentity(workerId);

        // 代理配置
        const disableProxy = process.env.DISABLE_PROXY === 'true';
        const proxyConfig = disableProxy ? undefined : { server: identity.proxy.url };

        // 创建浏览器上下文
        const context = await this.browser.newContext({
            viewport: identity.stealth.viewport,
            userAgent: identity.stealth.userAgent,
            extraHTTPHeaders: identity.stealth.extraHTTPHeaders,
            proxy: proxyConfig,
            deviceScaleFactor: DEEP_STEALTH_CONFIG.deviceScaleFactor,
            locale: DEEP_STEALTH_CONFIG.locale,
            timezoneId: DEEP_STEALTH_CONFIG.timezoneId
        });

        // 身份热加载
        let cookieLoaded = false;
        if (this.sessionManager) {
            cookieLoaded = await this.sessionManager.loadSessionToContext(context, identity.proxy.port);
        }
        if (!cookieLoaded) {
            cookieLoaded = await this._loadBrowserStateCookies(context);
        }

        const page = await context.newPage();
        await this._injectStealthScripts(page);

        // V181: 精简日志 - 只在首次或重试成功时输出
        const logPrefix = isRetry ? `[W${workerId}-R${attempt}]` : `[W${workerId}]`;

        try {
            // 首页预热（始终执行，            // V193: 重试时也需要执行预热，            const warmupConfig = isRetry ? { scrollMore: true, randomScrolls: true } : { scrollMore: false, randomScrolls: false };
            await this._warmupHomepage(page, warmupConfig);

            // 请求拦截
            let capturedData = null;
            await page.route('**/*', async (route) => {
                const url = route.request().url();
                const type = route.request().resourceType();

                if (['image', 'media', 'font'].includes(type)) {
                    await route.abort();
                    return;
                }

                if (url.includes('matchfacts') || url.includes('matchDetails')) {
                    try {
                        const response = await route.fetch();
                        const body = await response.text();
                        try {
                            capturedData = JSON.parse(body);
                        } catch (parseError) {
                            // JSON 解析失败
                        }
                        await route.fulfill({ response });
                    } catch (routeError) {
                        await route.continue();
                    }
                } else {
                    await route.continue();
                }
            });

            // 导航
            const matchUrl = `https://www.fotmob.com/match/${external_id}`;
            await page.goto(matchUrl, {
                waitUntil: 'domcontentloaded',
                timeout: 60000
            });

            // 行为模拟（重试时简化）
            if (!isRetry) {
                await this._simulateHumanBehavior(page);
            } else {
                const moves = this._randomInRange(3, 5);
                for (let i = 0; i < moves; i++) {
                    await page.mouse.move(
                        this._randomInRange(100, 1800),
                        this._randomInRange(100, 900),
                        { steps: 5 }
                    );
                    await this._delay(200);
                }
            }

            await page.waitForTimeout(isRetry ? 3000 : 5000);

            // 数据解析
            if (!capturedData) {
                const nextData = await page.evaluate(() => {
                    const script = document.getElementById('__NEXT_DATA__');
                    return script ? JSON.parse(script.textContent) : null;
                });
                capturedData = transformToApiFormat(nextData);
            }

            // 验证数据
            if (!capturedData) {
                throw new Error('NO_DATA:无法获取数据');
            }

            const size = JSON.stringify(capturedData).length;
            if (size < 1000) {
                throw new Error(`SIZE_TOO_SMALL:${size}`);
            }

            await this._markProxySuccess(workerId);

            if (this.config.dryRun) {
                console.log(`✅ ${logPrefix} ${home_team} vs ${away_team} | ${size} bytes`);
                return { success: true, match_id, size, workerId, port: identity.proxy.port, attempt };
            }

            await this.saveRawData(match_id, capturedData);
            console.log(`✅ ${logPrefix} ${home_team} vs ${away_team} | ${size} bytes | Port ${identity.proxy.port}`);

            return { success: true, match_id, size, workerId, port: identity.proxy.port, attempt };

        } catch (error) {
            await this._markProxyFailed(workerId, error.message);

            // V181: 精简日志 - 只在最终失败时输出
            if (attempt >= 3 || !this._isRetryableError(error)) {
                console.error(`❌ ${logPrefix} ${home_team} vs ${away_team}: ${error.message}`);
            }

            return { success: false, match_id, error: error.message, workerId, attempt };
        } finally {
            await page.close();
            await context.close();
        }
    }

    // ========================================================================
    // 生命周期方法
    // ========================================================================

    async init() {
        console.log('🚀 初始化 ProductionHarvester V179.1 (AUTO-PILOT + Self-Healing)...');

        // 数据库连接池
        this.pool = new Pool({
            host: DatabaseConfig.host,
            port: DatabaseConfig.port,
            database: DatabaseConfig.database,
            user: DatabaseConfig.user,
            password: DatabaseConfig.password,
            max: 20,
            idleTimeoutMillis: 30000
        });

        // 测试连接
        const client = await this.pool.connect();
        await client.query('SELECT 1');
        client.release();
        console.log('✅ 数据库连接池已就绪');

        // 清理僵尸进程
        await preFlightCleanup();

        // 启动浏览器
        this.browser = await chromium.launch({
            headless: true,
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-gpu'
            ]
        });
        console.log('✅ 浏览器已启动');

        // V178.2: 初始化 NetworkShield 代理池
        await this._initNetworkShield();

        // V179: 初始化 SessionManager
        await this._initSessionManager();

        console.log(`📋 配置: MAX_WORKERS=${this.config.maxWorkers}, DELAY=${this.config.minDelayMs}-${this.config.maxDelayMs}ms`);
    }

    // ========================================================================
    // V178: 行为模拟方法
    // ========================================================================

    /**
     * V178: 首页预热 - 建立 Session 信任
     * @param {import('playwright').Page} page - Playwright Page 对象
     */
    async _warmupHomepage(page) {
        console.log('🏠 首页预热: 访问 FotMob 首页...');

        await page.goto('https://www.fotmob.com/', { waitUntil: 'domcontentloaded' });

        // 随机停留 3-6 秒
        await this._delay(this._randomInRange(3000, 6000));

        // 3-5 次随机滚动
        const scrollCount = this._randomInRange(3, 5);
        for (let i = 0; i < scrollCount; i++) {
            await page.mouse.wheel(0, this._randomInRange(100, 300));
            await this._delay(this._randomInRange(500, 1500));
        }

        console.log(`✅ 首页预热完成 (${scrollCount} 次滚动)`);
    }

    /**
     * V178: 人类行为模拟 - 10-15 次鼠标位移
     * @param {import('playwright').Page} page - Playwright Page 对象
     */
    async _simulateHumanBehavior(page) {
        const moves = this._randomInRange(10, 15);

        for (let i = 0; i < moves; i++) {
            await page.mouse.move(
                this._randomInRange(100, 1800),
                this._randomInRange(100, 900),
                { steps: this._randomInRange(5, 15) }
            );
            await this._delay(this._randomInRange(200, 800));
        }

        console.log(`🎭 行为模拟完成 (${moves} 次鼠标移动)`);
    }

    /**
     * V180: 注入原生隐身脚本
     * 包含完整的硬件信息、WebGL 指纹伪装
     * @param {import('playwright').Page} page - Playwright 页面对象
     */
    async _injectStealthScripts(page) {
        await page.addInitScript(() => {
            /* eslint-disable no-undef */
            // 1. 覆盖 webdriver 标志
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
                configurable: true
            });

            // 2. 模拟 Chrome 插件数组
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {
                        0: 'Chrome PDF Plugin',
                        description: 'Portable Document Format',
                        filename: 'internal-pdf-viewer',
                        length: 1,
                        MimeTypes: ['application/pdf']
                    },
                    {
                        0: 'Chrome PDF Viewer',
                        description: '',
                        filename: 'mhjfbmdg-nopdfs',
                        length: 1,
                        MimeTypes: ['application/pdf']
                    },
                    {
                        0: 'Native Client',
                        description: '',
                        filename: 'internal-nacl',
                        length: 1,
                        MimeTypes: ['application/x-nacl', 'application/x-pnacl', 'application/x-google-chrome-tab']
                    }
                ],
                configurable: true
            });

            // 3. 模拟语言
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
                configurable: true
            });

            // 4. 模拟硬件并发 (V180: 24 核)
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 24,
                configurable: true
            });

            // 5. 模拟设备内存 (V180: 8GB)
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8,
                configurable: true
            });

            // 6. V180: WebGL 指纹伪装 - 关键！
            const getParameterProxyHandler = {
                apply: function(target, thisArg, args) {
                    const param = args[0];
                    // UNMASKED_VENDOR_WEBGL
                    if (param === 37445) {
                        return 'Google Inc. (AMD)';
                    }
                    // UNMASKED_RENDERER_WEBGL
                    if (param === 37446) {
                        return 'ANGLE (AMD, AMD Radeon(TM) Graphics (0x000013C0) Direct3D11 vs_5_0 ps_5_0, D3D11)';
                    }
                    return target.apply(thisArg, args);
                }
            };

            // 伪装 WebGL
            if (typeof WebGLRenderingContext !== 'undefined') {
                const originalGetParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = new Proxy(originalGetParameter, getParameterProxyHandler);
            }

            // 伪装 WebGL2
            if (typeof WebGL2RenderingContext !== 'undefined') {
                const originalGetParameter2 = WebGL2RenderingContext.prototype.getParameter;
                WebGL2RenderingContext.prototype.getParameter = new Proxy(originalGetParameter2, getParameterProxyHandler);
            }

            // 7. 覆盖 permissions 查询
            const originalQueryInterface = window.navigator.permissions?.query;
            if (originalQueryInterface) {
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQueryInterface(parameters)
                );
            }

            // 8. 隐藏自动化标志
            delete window.__webdriver_evaluate;
            delete window.__webdriver_script_function;
            delete window.__webdriver_script_fn;
            delete window.__webdriver_unwrapped;

            // 9. 覆盖 toString
            const oldToString = Function.prototype.toString;
            Function.prototype.toString = function() {
                if (this === navigator.permissions?.query) {
                    return 'function permissions() { [native code] }';
                }
                return oldToString.call(this);
            };

            console.log('[V180] 深度隐身脚本已注入 (WebGL + Hardware)');
        });
    }

    /**
     * 获取待收割的比赛列表
     * @returns {Promise<Array>} 比赛列表
     */
    async getPendingMatches() {
        const query = `
            SELECT
                m.match_id,
                m.external_id,
                m.home_team,
                m.away_team,
                m.match_date
            FROM matches m
            LEFT JOIN raw_match_data r ON m.match_id = r.match_id
            WHERE r.match_id IS NULL
            ORDER BY m.match_date DESC
            LIMIT $1
        `;

        const result = await this.pool.query(query, [this.config.batchSize || 500]);
        return result.rows;
    }

    /**
     * V181: 判断是否为可重试的错误（非 403 的网络错误)
     * @param {Error} error - 错误对象
     * @returns {boolean} 是否可重试
     */
    _isRetryableError(error) {
        const msg = error.message || '';
        const retryablePatterns = [
            'ERR_CONNECTION_CLOSED',
            'ERR_CONNECTION_RESET',
            'ERR_CONNECTION_TIMED_OUT',
            'ERR_TIMED_OUT',
            'ETIMEDOUT',
            'ECONNRESET',
            'ECONNREFUSED',
            'ENOTFOUND',
            'net::ERR_',
            'TIMEout',
            'Navigation timeout'
        ];

        // 403 错误不可重试（反爬机制)
        const nonRetryablePatterns = [
            '403',
            'ERR_BLOCKED',
            'Access denied',
            'Forbidden',
            'Turnstile'
        ];

        // 检查是否为不可重试错误
        for (const pattern of nonRetryablePatterns) {
            if (msg.includes(pattern)) {
                return false;
            }
        }

        // 检查是否为可重试错误
        for (const pattern of retryablePatterns) {
            if (msg.includes(pattern)) {
                return true;
            }
        }

        return false;
    }

    /**
     * V181: 获取避障端口（随机选择一个未失败的端口)
     * @param {number} excludePort - 要排除的端口
     * @returns {number} 新端口
     */
    _getAlternativePort(excludePort) {
        const healthyPorts = this.availablePorts.filter(p =>
            p !== excludePort && !this.failedPorts.has(p)
        );

        if (healthyPorts.length === 0) {
            // 所有端口都失败了，重置并返回随机端口
            this.failedPorts.clear();
            return this.availablePorts[Math.floor(Math.random() * this.availablePorts.length)];
        }

        return healthyPorts[Math.floor(Math.random() * healthyPorts.length)];
    }

    /**
     * V181: 执行多轮收割直到 100% 成功率或达到或所有比赛完成
     * @returns {Promise<Object>} 收割结果
     */
    async run() {
        this.startTime = Date.now();
        this.stats.sweepRounds++;

        console.log('═══════════════════════════════════════════════════════════════');
        console.log(`  V181 IRON-SHIELD 无人值守收割引擎 - 第 ${this.stats.sweepRounds} 轮`);
        console.log('  22 节点代理池 | 6 Worker 集群 | 弹性重试 | 発能避障');
        console.log('═══════════════════════════════════════════════════════════════');

        let allMatches = [];
        let remainingMatches = [];

        while (true) {
            const matches = await this.getPendingMatches();
            this.stats.total = matches.length;

            if (matches.length === 0) {
                console.log('🎉 所有比赛收割完成！');
                break;
            }

            console.log(`📋 第 ${this.stats.sweepRounds} 轮: 待收割 ${matches.length} 场`);

            if (this.config.dryRun) {
                console.log('⚠️ DRY RUN 模式 - 不会写入数据库');
            }

            // 并发收割
            const limit = pLimit(this.config.maxWorkers);

            const results = await Promise.all(matches.map((match, index) =>
                limit(() => this._harvestWithRetry(match, index))
            ));

            // 统计本轮结果
            let roundSuccess = 0;
            let roundFailed = 0;
            for (const result of results) {
                this.stats.processed++;
                if (result.success) {
                this.stats.success++;
                roundSuccess++;
            } else {
                this.stats.failed++;
                roundFailed++;
            }
        }

            const roundRate = matches.length > 0
                ? ((roundSuccess / matches.length) * 100).toFixed(1)
                : '0.0';

            console.log(`📊 第 ${this.stats.sweepRounds} 轮: 成功 ${roundSuccess}/${matches.length} (${roundRate}%)`);

            // 检查是否需要继续
            if (roundFailed === 0) {
                console.log('✅ 本轮 100% 成功，收割完成');
                break;
            }

            console.log(`🔄 检测到 ${roundFailed} 场失败， 准备下一轮扫尾...`);

            // 等待一段时间再开始下一轮
            await this._delay(5000);
        }

        // 最终报告
        this.printReport();
        return {
            total: this.stats.total,
            success: this.stats.success,
            failed: this.stats.failed,
        };
    }

    /**
     * 单场比赛收割 - V178.2: 接入 NetworkShield
     * @param {Object} match - 比赛信息对象
     * @param {number} index - 任务索引
     * @returns {Promise<Object>} 收割结果
     */
    async harvestMatch(match, index = 0) {
        const { match_id, external_id, home_team, away_team } = match;

        // V178.2: 计算 Worker ID (Round-Robin)
        const workerId = (index % this.config.maxWorkers) + 1;

        // 随机延迟
        const delay = this.config.minDelayMs +
            Math.random() * (this.config.maxDelayMs - this.config.minDelayMs);
        await this._delay(delay);

        // V178.2: 获取 Worker 身份（代理 IP + UA + 视口）
        const identity = await this._assignWorkerIdentity(workerId);

        // V179.5: 实验模式 - 支持禁用代理 (直接使用本地 IP)
        const disableProxy = process.env.DISABLE_PROXY === 'true';
        const proxyConfig = disableProxy ? undefined : { server: identity.proxy.url };

        // V180: 创建浏览器上下文（使用绑定身份 + 深度隐身配置）
        // 注意: hardwareConcurrency, deviceMemory, webgl 必须通过 addInitScript 注入
        // Playwright newContext 不支持这些参数
        const context = await this.browser.newContext({
            viewport: identity.stealth.viewport,
            userAgent: identity.stealth.userAgent,
            extraHTTPHeaders: identity.stealth.extraHTTPHeaders,
            proxy: proxyConfig,
            // V180: 深度隐身配置 - Playwright 支持的参数
            deviceScaleFactor: DEEP_STEALTH_CONFIG.deviceScaleFactor,
            locale: DEEP_STEALTH_CONFIG.locale,
            timezoneId: DEEP_STEALTH_CONFIG.timezoneId
            // hardwareConcurrency, deviceMemory, webgl 通过 _injectStealthScripts 注入
        });

        if (disableProxy) {
            console.log(`🔬 [W${workerId}] 实验模式: 已禁用代理，使用本地 IP`);
        } else {
            console.log(`📡 [W${workerId}] 代理模式: ${identity.proxy.url}`);
        }

        // V179: 身份热加载 - 注入会话 Cookie
        let cookieLoaded = false;
        if (this.sessionManager) {
            cookieLoaded = await this.sessionManager.loadSessionToContext(context, identity.proxy.port);
            if (cookieLoaded) {
                console.log(`🔑 [W${workerId}] 身份热加载成功 (SessionManager)`);
            }
        }

        // V179.1: 回退 - 直接从 browser_state.json 加载 Cookie
        if (!cookieLoaded) {
            cookieLoaded = await this._loadBrowserStateCookies(context);
            if (cookieLoaded) {
                console.log(`🔑 [W${workerId}] 身份热加载成功 (browser_state.json)`);
            }
        }

        const page = await context.newPage();

        // V180: 注入原生隐身脚本
        await this._injectStealthScripts(page);
        console.log(`🥷 [W${workerId}] 深度隐身装甲已激活`);

        try {
            console.log(`🌐 [W${workerId}] 渗透: ${home_team} vs ${away_team} | Port ${identity.proxy.port}`);

            // V178: 首页预热 - 建立 Session 信任
            await this._warmupHomepage(page);

            // 设置请求拦截
            let capturedData = null;

            // eslint-disable-next-line no-loop-func
            await page.route('**/*', async (route) => {
                const url = route.request().url();
                const type = route.request().resourceType();

                // 屏蔽非必要资源
                if (['image', 'media', 'font'].includes(type)) {
                    await route.abort();
                    return;
                }

                // 捕获目标 API
                if (url.includes('matchfacts') || url.includes('matchDetails')) {
                    try {
                        const response = await route.fetch();
                        const body = await response.text();
                        try {
                            capturedData = JSON.parse(body);
                            console.log(`📡 [W${workerId}] 拦截 API: ${url.slice(0, 50)}...`);
                        } catch (parseError) {
                            // JSON 解析失败 - 非 JSON 响应，静默忽略
                        }
                        await route.fulfill({ response });
                    } catch (routeError) {
                        // 路由请求失败 - 网络问题，继续请求
                        await route.continue();
                    }
                } else {
                    await route.continue();
                }
            });

            // 构建目标 URL
            const matchUrl = `https://www.fotmob.com/match/${external_id}`;

            // 导航到比赛页面
            await page.goto(matchUrl, {
                waitUntil: 'domcontentloaded',
                timeout: 60000
            });

            // V178: 行为模拟 - 10-15 次鼠标位移
            await this._simulateHumanBehavior(page);

            // 等待数据
            await page.waitForTimeout(5000);

            // 如果拦截失败，使用 NextDataParser
            if (!capturedData) {
                // 使用 NextDataParser (document 是浏览器环境全局变量)
                /* eslint-disable no-undef */
                const nextData = await page.evaluate(() => {
                    const script = document.getElementById('__NEXT_DATA__');
                    return script ? JSON.parse(script.textContent) : null;
                });
                /* eslint-enable no-undef */
                capturedData = transformToApiFormat(nextData);
                console.log(`📄 [W${workerId}] 使用 __NEXT_DATA__ 解析`);
            }

            // 验证数据
            if (!capturedData) {
                throw new Error('NO_DATA:无法获取数据');
            }

            const size = JSON.stringify(capturedData).length;
            if (size < 1000) {
                throw new Error(`SIZE_TOO_SMALL:${size}`);
            }

            // V178.2: 标记代理成功
            await this._markProxySuccess(workerId);

            // DRY RUN 模式
            if (this.config.dryRun) {
                console.log(`✅ [W${workerId}] ${home_team} vs ${away_team} | ${size} bytes | DRY RUN`);
                return { success: true, match_id, size, workerId, port: identity.proxy.port };
            }

            // 写入数据库
            // V179.5: 检查 JSON 序列化是否有效
            try {
                const jsonString = JSON.stringify(capturedData);
                console.log(`📝 [W${workerId}] JSON 序列化成功: ${jsonString.length} 字节`);
            } catch (jsonError) {
                throw new Error(`JSON_SERIALIZE_ERROR: ${jsonError.message}`);
            }
            await this.saveRawData(match_id, capturedData);
            console.log(`✅ [W${workerId}] ${home_team} vs ${away_team} | ${size} bytes | Port ${identity.proxy.port}`);

            return { success: true, match_id, size, workerId, port: identity.proxy.port };

        } catch (error) {
            // V180: 捕获 403 错误并详细记录
            if (error.message && (
                error.message.includes('403') ||
                error.message.includes('net::ERR_BLOCKED') ||
                error.message.includes('Access denied')
            )) {
                console.log(`🚨 [W${workerId}] 403/BLOCKED 错误! 检测到反爬虫机制`);
                console.log(`   📊 错误详情: ${error.message}`);
                // 尝试获取页面 HTML 进行分析
                try {
                    const html = await page.content();
                    const title = await page.title();
                    console.log(`   📄 页面标题: ${title}`);
                    console.log(`   📏 HTML 长度: ${html.length} 字符`);
                    // 检查是否有 Turnstile/验证相关内容
                    if (html.includes('turnstile') || html.includes('challenge') || html.includes('cf-')) {
                        console.log(`   🔍 检测到 Turnstile/Challenge 内容!`);
                    }
                    // V180: 打印响应 Headers 用于分析
                    const headers = await page.evaluate(() => {
                        return Object.fromEntries(
                            ...performance.getEntriesByType('navigation').map(e => [e.name, e.value])
                        );
                    });
                    console.log(`   📋 响应 Headers: ${JSON.stringify(headers, null, 2).slice(0, 500)}`);
                } catch (htmlError) {
                    console.log(`   ⚠ 无法获取页面信息: ${htmlError.message}`);
                }
            }

            // V178.2: 标记代理失败 + 熔断
            await this._markProxyFailed(workerId, error.message);

            console.error(`❌ [W${workerId}] ${home_team} vs ${away_team}: ${error.message}`);
            return { success: false, match_id, error: error.message, workerId };
        } finally {
            await page.close();
            await context.close();
        }
    }

    /**
     * 保存原始数据
     * @param {string} matchId - 比赛 ID
     * @param {Object} rawData - 原始数据对象
     */
    async saveRawData(matchId, rawData) {
        const client = await this.pool.connect();
        try {
            const query = `
                INSERT INTO raw_match_data (match_id, raw_data, collected_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (match_id)
                DO UPDATE SET raw_data = EXCLUDED.raw_data, collected_at = NOW()
            `;
            // V179.2: 修复参数顺序 - $1=match_id, $2=raw_data
            await client.query(query, [matchId, JSON.stringify(rawData)]);
        } finally {
            client.release();
        }
    }

    /**
     * V181: 打印报告 (包含重试和扫尾统计)
     */
    printReport() {
        const elapsed = ((Date.now() - this.startTime) / 1000).toFixed(1);
        const rate = this.stats.total > 0
            ? ((this.stats.success / this.stats.total) * 100).toFixed(1)
            : '0.0';

        console.log('═══════════════════════════════════════════════════════════════');
        console.log('  📊 V181 IRON-SHIELD 收割完成报告');
        console.log('═══════════════════════════════════════════════════════════════');
        console.log(`  总计: ${this.stats.total} 场`);
        console.log(`  成功: ${this.stats.success} 场`);
        console.log(`  失败: ${this.stats.failed} 场`);
        console.log(`  成功率: ${rate}%`);
        console.log(`  重试次数: ${this.stats.retries}`);
        console.log(`  扫尾轮数: ${this.stats.sweepRounds}`);
        console.log(`  耗时: ${elapsed} 秒`);
        console.log(`  Worker 数: ${this.config.maxWorkers}`);

        // V178.2: 打印 Worker 身份统计
        console.log('───────────────────────────────────────────────────────────────');
        console.log('  Worker 身份统计:');
        for (const [workerId, identity] of this.workerIdentities) {
            const successRate = (identity.getSuccessRate() * 100).toFixed(0);
            console.log(`    W${workerId}: Port ${identity.proxy.port} | ` +
                `${identity.requestCount} 请求 | ${successRate}% 成功率`);
        }
        console.log('═══════════════════════════════════════════════════════════════');
    }

    /**
     * 清理资源
     */
    async cleanup() {
        // V178.2: 关闭 NetworkShield
        if (this.networkShield) {
            this.networkShield.shutdown();
        }

        // V179: 打印 SessionManager 统计
        if (this.sessionManager) {
            const stats = this.sessionManager.getStats();
            console.log('📊 SessionManager 统计:');
            console.log(`   总刷新: ${stats.totalRefreshes}`);
            console.log(`   成功刷新: ${stats.successfulRefreshes}`);
            console.log(`   失败刷新: ${stats.failedRefreshes}`);
            console.log(`   缓存命中: ${stats.cacheHits}`);
            console.log(`   缓存未命中: ${stats.cacheMisses}`);
        }

        if (this.browser) {
            await this.browser.close();
        }
        if (this.pool) {
            await this.pool.end();
        }
        console.log('🛹 资源已清理');
    }
}

module.exports = { ProductionHarvester };
