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

const { chromium } = require('playwright');
const { Pool } = require('pg');

// 导入核心组件
const { preFlightCleanup } = require('../../core/process/ZombieKiller');
const { transformToApiFormat } = require('../../parsers/fotmob/NextDataParser');

// 导入配置
const { DatabaseConfig } = require('../database/PostgresClient');

// V186: 导入企业级日志系统
const { logger } = require('../utils/Logger');

// V4.46: 导入 PathResolver - 统一路径管理
const { getPathResolver } = require('../utils/PathResolver');

// V4.46: 导入 NetworkManager - 网络与会话管理
const { getNetworkManager, WorkerIdentity } = require('../network/NetworkManager');

// V4.46: 导入 StealthFingerprint - 隐身指纹生成
const { generateStealthHeaders } = require('../network/StealthFingerprint');

// V4.46: 导入 WorkerPool - Worker 调度中心
const { getWorkerPool } = require('./workers/WorkerPool');

// V4.46: 隐身指纹相关常量和函数已迁移到 StealthFingerprint.js
// 通过 require('../network/StealthFingerprint') 导入

// V4.46: WorkerIdentity 类已迁移到 NetworkManager.js
// 通过 require('../network/NetworkManager') 导入

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

        // V4.46: 使用 NetworkManager 统一管理网络和会话
        this.networkManager = null;

        // V4.46: 使用 WorkerPool 统一管理 Worker 调度
        this.workerPool = null;

        // V186: 优雅停机状态
        this.isShuttingDown = false;
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
            const activeCount = this.workerPool ? this.workerPool.getActiveCount() : 0;
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
     * V4.46: 委托给 WorkerPool
     * @private
     * @returns {Promise<void>}
     */
    async _waitForWorkers() {
        if (this.workerPool) {
            await this.workerPool.waitForAll((count) => {
                logger.debug(`等待 ${count} 个 Worker...`);
            });
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
     * V4.46: 委托给 WorkerPool
     * @param {number} workerId - Worker ID
     */
    _registerWorker(workerId) {
        if (this.workerPool) {
            this.workerPool.register(workerId);
        }
    }

    /**
     * V186: 注销 Worker 活跃状态
     * V4.46: 委托给 WorkerPool
     * @param {number} workerId - Worker ID
     */
    _unregisterWorker(workerId) {
        if (this.workerPool) {
            this.workerPool.unregister(workerId);
        }
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
        // V4.46: 使用 PathResolver 统一路径管理
        const pathResolver = getPathResolver();
        const statePath = pathResolver.getBrowserStatePath();

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

        // V4.46: 使用 PathResolver 统一路径管理
        const pathResolver = getPathResolver();

        const lockDirs = [
            ...pathResolver.getLockDirs(),
            './data/network',
            './data/registry',
            './config'
        ];

        // V179.1: 额外检查特定的锁文件路径
        const specificLockFiles = [
            pathResolver.getRegistryLockPath(),
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

                // V4.46: 使用 NetworkManager 进行端口避障
                const currentIdentity = this.networkManager?.getWorkerIdentity(workerId);

                if (currentIdentity) {
                    await this.networkManager.forceReassignPort(workerId, currentIdentity.proxy.port);
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

        // V4.46: 使用 NetworkManager 获取/刷新 Worker 身份
        const identity = await this.networkManager.assignWorkerIdentity(workerId);

        // 代理配置
        const disableProxy = process.env.DISABLE_PROXY === 'true';
        const proxyConfig = disableProxy ? undefined : { server: identity.proxy.url };

        // 创建浏览器上下文
        const context = await this.browser.newContext({
            viewport: identity.stealth.viewport,
            userAgent: identity.stealth.userAgent,
            extraHTTPHeaders: identity.stealth.extraHTTPHeaders,
            proxy: proxyConfig,
            deviceScaleFactor: identity.stealth.deviceScaleFactor || 1,
            locale: identity.stealth.locale || 'en-US',
            timezoneId: identity.stealth.timezoneId || 'Europe/London'
        });

        // V4.46: 使用 NetworkManager 身份热加载
        let cookieLoaded = false;
        if (this.networkManager) {
            cookieLoaded = await this.networkManager.loadSessionToContext(context, identity.proxy.port);
        }
        if (!cookieLoaded) {
            cookieLoaded = await this._loadBrowserStateCookies(context);
        }

        const page = await context.newPage();
        await this._injectStealthScripts(page);

        // V181: 精简日志 - 只在首次或重试成功时输出
        const logPrefix = isRetry ? `[W${workerId}-R${attempt}]` : `[W${workerId}]`;

        try {
            // 首页预热（始终执行）
            // V193: 重试时也需要执行预热
            const warmupConfig = isRetry ? { scrollMore: true, randomScrolls: true } : { scrollMore: false, randomScrolls: false };
            await this._warmupHomepage(page, warmupConfig);

            // 请求拦截
            let capturedData = null;
            let capturedUrl = null;
            await page.route('**/*', async (route) => {
                const url = route.request().url();
                const type = route.request().resourceType();

                if (['image', 'media', 'font'].includes(type)) {
                    await route.abort();
                    return;
                }

                if (url.includes('matchfacts') || url.includes('matchDetails')) {
                    console.log(`[DEBUG] 捕获 API 请求: ${url.slice(0, 100)}...`);
                    try {
                        const response = await route.fetch();
                        const body = await response.text();
                        console.log(`[DEBUG] 响应状态: ${response.status()}`);
                        console.log(`[DEBUG] 响应体大小: ${body.length} 字节`);
                        console.log(`[DEBUG] 响应体内容: ${body}`);
                        try {
                            capturedData = JSON.parse(body);
                            capturedUrl = url;
                            console.log(`[DEBUG] JSON 解析成功`);
                        } catch (parseError) {
                            console.log(`[DEBUG] JSON 解析失败: ${parseError.message}`);
                        }
                        await route.fulfill({ response });
                    } catch (routeError) {
                        console.log(`[DEBUG] 请求失败: ${routeError.message}`);
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

            // V4.46: 使用 MatchDetailEngine 进行数据解析
            if (!capturedData) {
                console.log(`[DEBUG] 尝试从 __NEXT_DATA__ 提取数据...`);
                const nextData = await page.evaluate(() => {
                    const script = document.getElementById('__NEXT_DATA__');
                    return script ? JSON.parse(script.textContent) : null;
                });

                console.log(`[DEBUG] nextData 存在: ${!!nextData}`);
                console.log(`[DEBUG] nextData.props 存在: ${!!nextData?.props}`);
                console.log(`[DEBUG] nextData.props.pageProps 存在: ${!!nextData?.props?.pageProps}`);

                capturedData = transformToApiFormat(nextData);

                console.log(`[DEBUG] capturedData 存在: ${!!capturedData}`);
                console.log(`[DEBUG] capturedData keys: ${capturedData ? Object.keys(capturedData).join(', ') : 'N/A'}`);
            }
            // 验证数据
            if (!capturedData) {
                throw new Error('NO_DATA:无法获取数据');
            }

            const size = JSON.stringify(capturedData).length;
            if (size < 1000) {
                throw new Error(`SIZE_TOO_SMALL:${size}`);
            }

            // V4.46: 使用 NetworkManager 标记代理成功
            await this.networkManager.markProxySuccess(workerId);

            if (this.config.dryRun) {
                console.log(`✅ ${logPrefix} ${home_team} vs ${away_team} | ${size} bytes`);
                return { success: true, match_id, size, workerId, port: identity.proxy.port, attempt };
            }

            await this.saveRawData(match_id, capturedData);
            console.log(`✅ ${logPrefix} ${home_team} vs ${away_team} | ${size} bytes | Port ${identity.proxy.port}`);

            return { success: true, match_id, size, workerId, port: identity.proxy.port, attempt };

        } catch (error) {
            // V4.46: 使用 NetworkManager 标记代理失败
            await this.networkManager.markProxyFailed(workerId, error.message);

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

        // V4.46: 使用 NetworkManager 统一管理网络和会话
        this.networkManager = getNetworkManager({
            maxWorkers: this.config.maxWorkers,
            stealthGenerator: generateStealthHeaders
        });
        await this.networkManager.initialize({
            preFlightCleanup: () => this._preFlightCleanupNetworkLocks()
        });

        // V4.46: 使用 WorkerPool 统一管理 Worker 调度
        this.workerPool = getWorkerPool({
            maxWorkers: this.config.maxWorkers,
            logger: (msg) => console.log(msg)
        });

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
        // V4.9: 支持 SERIE_A_PILOT 模式 - 只收割意甲最近 10 场已结束比赛
        const serieAPilot = process.env.SERIE_A_PILOT === 'true';

        let query, params;
        if (serieAPilot) {
            query = `
                SELECT
                    m.match_id,
                    m.external_id,
                    m.home_team,
                    m.away_team,
                    m.match_date
                FROM matches m
                LEFT JOIN raw_match_data r ON m.match_id = r.match_id
                WHERE r.match_id IS NULL
                    AND m.league_name = 'Serie A'
                    AND m.status = $MATCH_STATUS.FINISHED
                    ORDER BY m.match_date DESC
                    LIMIT 10
                ORDER BY m.match_date DESC
                LIMIT 10
            `;
            params = [];
            console.log('🇮🇹 SERIE-A-PILOT 模式: 只收割意甲最近 10 场已结束比赛');
        } else {
            query = `
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
            params = [this.config.batchSize || 500];
        }

        const result = await this.pool.query(query, params);
        return result.rows;
    }

    /**
     * V181: 执行多轮收割直到 100% 成功率或达到或所有比赛完成
     * V4.46-TITAN: 支持单场比赛收割模式
     * @param {Object} [options={}] - 收割选项
     * @param {string} [options.matchId] - 单场比赛 ID (可选)
     * @param {boolean} [options.force=false] - 强制收割已收割的比赛
     * @returns {Promise<Object>} 收割结果
     */
    async run(options = {}) {
        const { matchId, force = false } = options;

        // V4.46-TITAN: 单场比赛收割模式
        if (matchId) {
            return this._runSingleMatch(matchId, force);
        }

        // 批量收割模式
        this.startTime = Date.now();
        this.stats.sweepRounds++;

        console.log('═══════════════════════════════════════════════════════════════');
        console.log(`  V181 IRON-SHIELD 无人值守收割引擎 - 第 ${this.stats.sweepRounds} 轮`);
        console.log('  22 节点代理池 | 6 Worker 集群 | 弹性重试 | 発能避障');
        console.log('═══════════════════════════════════════════════════════════════');

        const allMatches = [];
        const remainingMatches = [];

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

            // V4.46: 使用 WorkerPool 进行并发收割
            const results = await this.workerPool.executeAll(
                matches,
                (match, index) => this._harvestWithRetry(match, index)
            );

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
     * V4.46-TITAN: 单场比赛收割模式
     * 支持两种模式：
     * 1. 数据库模式：match_id 存在于 matches 表
     * 2. 直接收割模式：使用 external_id 直接收割（当 match_id 不在数据库时）
     * @param {string} matchId - 比赛 ID 或 external_id
     * @param {boolean} [force=false] - 强制收割已收割的比赛
     * @returns {Promise<Object>} 收割结果
     */
    async _runSingleMatch(matchId, force = false) {
        this.startTime = Date.now();
        this.stats.sweepRounds = 1;

        console.log('═══════════════════════════════════════════════════════════════');
        console.log(`  V4.46-TITAN 单场比赛收割模式`);
        console.log(`  MatchID: ${matchId} | Force: ${force}`);
        console.log('═══════════════════════════════════════════════════════════════');

        // 尝试从数据库查询比赛信息
        let query = `
            SELECT
                m.match_id,
                m.external_id,
                m.home_team,
                m.away_team,
                m.match_date
            FROM matches m
            WHERE m.match_id = $1 OR m.external_id = $1
        `;

        // 如果不强制收割，检查是否已收割
        if (!force) {
            query = `
                SELECT
                    m.match_id,
                    m.external_id,
                    m.home_team,
                    m.away_team,
                    m.match_date
                FROM matches m
                LEFT JOIN raw_match_data r ON m.match_id = r.match_id
                WHERE (m.match_id = $1 OR m.external_id = $1)
                    AND r.match_id IS NULL
            `;
        }

        const result = await this.pool.query(query, [matchId]);

        let match;
        if (result.rows.length === 0) {
            // V4.46-TITAN: 直接收割模式 - 比赛不在数据库中
            // 使用 external_id 作为 match_id 进行收割
            console.log(`📡 比赛不在数据库中，启用直接收割模式...`);

            // 判断 matchId 格式并提取 external_id
            // 格式1: 纯数字 (4803306) -> 直接使用
            // 格式2: 复合ID (55_20242025_4803306) -> 提取最后一部分
            let externalId;
            if (/^\d+$/.test(matchId)) {
                externalId = matchId;
            } else if (matchId.includes('_')) {
                const parts = matchId.split('_');
                externalId = parts[parts.length - 1];
            } else {
                externalId = matchId;
            }

            match = {
                match_id: matchId,
                external_id: externalId,
                home_team: 'Unknown',
                away_team: 'Unknown',
                match_date: new Date()
            };

            console.log(`📋 比赛: External ID ${match.external_id}`);
        } else {
            match = result.rows[0];
            console.log(`📋 比赛: ${match.home_team} vs ${match.away_team}`);
        }

        this.stats.total = 1;

        // 执行收割
        const harvestResult = await this._harvestWithRetry(match, 0, this.config.maxRetries);

        if (harvestResult.success) {
            this.stats.success = 1;
            this.stats.processed = 1;
            console.log(`✅ 收割成功: ${match.home_team} vs ${match.away_team}`);
        } else {
            this.stats.failed = 1;
            this.stats.processed = 1;
            console.error(`❌ 收割失败: ${harvestResult.error}`);
        }

        // 打印报告
        this.printReport();

        return {
            total: 1,
            success: this.stats.success,
            failed: this.stats.failed,
            matchId,
            error: harvestResult.success ? null : harvestResult.error
        };
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
        // V4.46: 打印 NetworkManager 身份统计 (防御性检查)
        if (this.networkManager && this.networkManager.workerIdentities) {
            for (const [workerId, identity] of this.networkManager.workerIdentities) {
                if (identity && identity.proxy) {
                    const successRate = (identity.getSuccessRate() * 100).toFixed(0);
                    console.log(`    W${workerId}: Port ${identity.proxy.port} | ${identity.requestCount} 请求 | ${successRate}% 成功率`);
                }
            }
        }
        console.log('═══════════════════════════════════════════════════════════════');
    }

    /**
     * 清理资源
     */
    async cleanup() {
        if (this.browser) {
            await this.browser.close();
        }
        if (this.pool) {
            await this.pool.end();
        }
        console.log('🛹 资源已清理');
    }
}

// ============================================================================
// CLI 启动逻辑 (V4.46-ignition)
// ============================================================================

if (require.main === module) {
    // 使用原生 process.argv 解析参数 (不依赖 commander)
    const args = process.argv.slice(2);
    const options = {
        matchId: null,
        force: false,
        verbose: false
    };

    for (const arg of args) {
        if (arg.startsWith('--matchId=')) {
            options.matchId = arg.split('=')[1];
        } else if (arg === '--force' || arg === '-f') {
            options.force = true;
        } else if (arg === '--verbose' || arg === '-v') {
            options.verbose = true;
        }
    }

    console.log('🚀 [IGNITION] Starting ProductionHarvester in CLI mode...');
    console.log('📊 Options:', JSON.stringify(options, null, 2));

    // V4.46-TITAN: 修复入口逻辑 - 必须先 init() 再 run()
    (async () => {
        const harvester = new ProductionHarvester({
            verboseLogging: options.verbose
        });

        try {
            // 第一步：初始化 (数据库、浏览器、NetworkManager、WorkerPool)
            console.log('🔧 [IGNITION] 初始化收割器...');
            await harvester.init();

            // 第二步：执行收割
            console.log('🔥 [IGNITION] 开始收割...');
            const result = await harvester.run({
                matchId: options.matchId,
                force: options.force
            });

            console.log('✅ [IGNITION] Harvest completed!');
            console.log('📊 Result:', JSON.stringify(result, null, 2));

            // 第三步：清理资源
            await harvester.cleanup();

            process.exit(0);
        } catch (err) {
            console.error('💥 [IGNITION] Fatal error:', err);
            console.error('📊 Stack:', err.stack);
            process.exit(1);
        }
    })();
}

module.exports = { ProductionHarvester };
