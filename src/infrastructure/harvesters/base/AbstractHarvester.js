/**
 * AbstractHarvester - 收割器抽象基类
 * ==================================
 *
 * 封装所有通用收割逻辑：
 * - 浏览器初始化与管理
 * - 代理设置与轮换
 * - 页面预热与行为模拟
 * - 弹性重试机制
 * - 异常处理与资源清理
 *
 * 子类必须实现抽象方法：extractData()
 *
 * @module infrastructure/harvesters/base/AbstractHarvester
 * @version V1.0.0
 */

'use strict';

const { chromium } = require('playwright');
const { Pool } = require('pg');

// 导入核心组件
const { preFlightCleanup } = require('../../../core/process/ZombieKiller');
const { DatabaseConfig } = require('../../database/PostgresClient');
const { logger } = require('../../utils/Logger');
const { getPathResolver } = require('../../utils/PathResolver');
const { getNetworkManager } = require('../../network/NetworkManager');
const { generateStealthHeaders } = require('../../network/StealthFingerprint');
const { getWorkerPool } = require('../workers/WorkerPool');

// V4.46: 导入指标客户端
const { getMetricsClient } = require('../../monitoring/MetricsClient');

// ============================================================================
// AbstractHarvester 抽象基类
// ============================================================================

class AbstractHarvester {
    /**
     * 创建收割器实例
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
     * @param {boolean} [config.skipZombieCleanup=false] - 跳过僵尸进程清理（Swarm 模式）
     */
    constructor(config = {}) {
        this.config = {
            maxWorkers: parseInt(process.env.MAX_WORKERS) || config.maxWorkers || 6,
            minDelayMs: parseInt(process.env.MIN_DELAY_MS) || config.minDelayMs || 10000,
            maxDelayMs: parseInt(process.env.MAX_DELAY_MS) || config.maxDelayMs || 20000,
            batchSize: parseInt(process.env.BATCH_SIZE) || config.batchSize || 500,
            leagueFilter: config.leagueFilter || process.env.LEAGUE_FILTER || null,
            dryRun: config.dryRun || false,
            useFixedFingerprint: config.useFixedFingerprint !== false,
            maxRetries: parseInt(process.env.MAX_RETRIES) || config.maxRetries || 3,
            retryDelayMs: parseInt(process.env.RETRY_DELAY_MS) || config.retryDelayMs || 5000,
            maxSweepRounds: parseInt(process.env.MAX_SWEEP_ROUNDS) || config.maxSweepRounds || 3,
            targetSuccessRate: parseFloat(process.env.TARGET_SUCCESS_RATE) || config.targetSuccessRate || 1.0,
            verboseLogging: process.env.VERBOSE_LOGGING === 'true' || config.verboseLogging || false,
            shutdownTimeoutMs: parseInt(process.env.SHUTDOWN_TIMEOUT_MS) || config.shutdownTimeoutMs || 30000,
            skipZombieCleanup: config.skipZombieCleanup || false,
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

        this.networkManager = null;
        this.workerPool = null;

        this.isShuttingDown = false;
        this.shutdownPromise = null;
        this.workerLogger = logger.createWorkerLogger(0, 0);

        // V4.46: 初始化指标客户端
        this.metricsClient = getMetricsClient();

        // V4.46.3 HYPER-DRIVE: Browser Context Pooling
        // V4.46.5 HARDENING: LRU 淘汰机制防止内存泄漏
        this._contextPool = new Map();  // workerId -> { context, usageCount, lastPort, lastAccessTime }
        this._contextMaxUsage = 10;     // 每个 context 最多复用 10 次
        this._contextPoolMaxSize = 20;  // V4.46.5: 池子上限，防止无限增长
        this._totalContextCreations = 0;
        this._totalContextReuses = 0;
        this._contextEvictions = 0;     // V4.46.5: 淘汰计数

        this._setupGracefulShutdown();
    }

    /**
     * 抽象方法：子类必须实现数据提取逻辑
     * @param {import('playwright').Page} page - Playwright Page 对象
     * @param {Object} match - 比赛信息
     * @returns {Promise<Object>} 提取的数据
     * @abstract
     */
    async extractData(page, match) {
        throw new Error('子类必须实现 extractData() 方法');
    }

    /**
     * 抽象方法：子类返回目标 URL
     * @param {Object} match - 比赛信息
     * @returns {string} 目标 URL
     * @abstract
     */
    getTargetUrl(match) {
        throw new Error('子类必须实现 getTargetUrl() 方法');
    }

    /**
     * 抽象方法：子类实现数据保存逻辑
     * @param {string} matchId - 比赛 ID
     * @param {Object} data - 提取的数据
     * @returns {Promise<void>}
     * @abstract
     */
    async saveData(matchId, data) {
        throw new Error('子类必须实现 saveData() 方法');
    }

    // ========================================================================
    // 初始化与生命周期
    // ========================================================================

    /**
     * 初始化收割器
     * 建立数据库连接、启动浏览器、初始化 NetworkManager 和 WorkerPool
     */
    async init() {
        console.log(`🚀 初始化 ${this.constructor.name}...`);

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

        const client = await this.pool.connect();
        await client.query('SELECT 1');
        client.release();
        console.log('✅ 数据库连接池已就绪');

        // 清理僵尸进程 (Swarm 模式下跳过，由 SwarmHarvester 统一执行)
        if (!this.config.skipZombieCleanup) {
            await preFlightCleanup();
        }

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

        // 初始化 NetworkManager
        this.networkManager = getNetworkManager({
            maxWorkers: this.config.maxWorkers,
            stealthGenerator: generateStealthHeaders
        });
        await this.networkManager.initialize({
            preFlightCleanup: () => this._preFlightCleanupNetworkLocks()
        });

        // 初始化 WorkerPool
        this.workerPool = getWorkerPool({
            maxWorkers: this.config.maxWorkers,
            logger: (msg) => console.log(msg)
        });

        console.log(`📋 配置: MAX_WORKERS=${this.config.maxWorkers}, DELAY=${this.config.minDelayMs}-${this.config.maxDelayMs}ms`);
    }

    /**
     * 清理资源
     */
    async cleanup() {
        // V4.46.3 HYPER-DRIVE: 先清理 Context 池
        await this._cleanupContextPool();

        if (this.browser) {
            await this.browser.close();
            console.log('✅ 浏览器已关闭');
        }
        if (this.pool) {
            await this.pool.end();
            console.log('✅ 数据库连接池已关闭');
        }
        console.log('🛹 资源已清理');
    }

    // ========================================================================
    // 优雅停机机制
    // ========================================================================

    /**
     * 设置优雅停机信号处理器
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

            const timeoutId = setTimeout(() => {
                logger.warn(`⏰ 停机超时 (${this.config.shutdownTimeoutMs}ms)，强制退出`);
                process.exit(1);
            }, this.config.shutdownTimeoutMs);

            try {
                if (activeCount > 0) {
                    logger.info(`⏳ 等待 ${activeCount} 个活跃 Worker 完成...`);
                    await Promise.race([
                        this._waitForWorkers(),
                        this._delay(this.config.shutdownTimeoutMs - 1000)
                    ]);
                }

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
     * 等待所有活跃 Worker 完成
     * @private
     */
    async _waitForWorkers() {
        if (this.workerPool) {
            await this.workerPool.waitForAll((count) => {
                logger.debug(`等待 ${count} 个 Worker...`);
            });
        }
    }

    /**
     * 清理资源（浏览器、数据库连接等）
     * @private
     */
    async _cleanup() {
        if (this.browser) {
            try {
                await this.browser.close();
            } catch (err) {
                logger.warn('浏览器关闭失败', { error: err.message });
            }
        }

        if (this.pool) {
            try {
                await this.pool.end();
            } catch (err) {
                logger.warn('数据库连接池关闭失败', { error: err.message });
            }
        }
    }

    // ========================================================================
    // 网络与代理管理
    // ========================================================================

    /**
     * 预清理 NetworkShield 锁文件
     * @returns {Promise<number>} 清理的锁文件数量
     * @private
     */
    async _preFlightCleanupNetworkLocks() {
        const fs = require('fs').promises;
        const path = require('path');
        const pathResolver = getPathResolver();

        const lockDirs = [
            ...pathResolver.getLockDirs(),
            './data/network',
            './data/registry',
            './config'
        ];

        const specificLockFiles = [
            pathResolver.getRegistryLockPath(),
            './config/.registry.lock'
        ];

        let cleanedCount = 0;

        for (const dir of lockDirs) {
            try {
                const files = await fs.readdir(dir);
                const lockFiles = files.filter(f => f.endsWith('.lock'));

                for (const lockFile of lockFiles) {
                    const lockPath = path.join(dir, lockFile);
                    try {
                        await fs.unlink(lockPath);
                        cleanedCount++;
                    } catch (unlinkError) {
                        // 忽略删除失败
                    }
                }
            } catch (dirError) {
                // 目录不存在，忽略
            }
        }

        for (const lockPath of specificLockFiles) {
            try {
                await fs.unlink(lockPath);
                cleanedCount++;
            } catch (unlinkError) {
                // 忽略
            }
        }

        if (cleanedCount > 0) {
            console.log(`✅ 预清理完成: 已移除 ${cleanedCount} 个残留锁文件`);
        }

        return cleanedCount;
    }

    // ========================================================================
    // 弹性重试机制
    // ========================================================================

    /**
     * 判断是否为可重试的错误
     * @param {Error} error - 错误对象
     * @returns {boolean} 是否可重试
     * @private
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

        const nonRetryablePatterns = [
            '403',
            'ERR_BLOCKED',
            'Access denied',
            'Forbidden',
            'Turnstile'
        ];

        for (const pattern of nonRetryablePatterns) {
            if (msg.includes(pattern)) {
                return false;
            }
        }

        for (const pattern of retryablePatterns) {
            if (msg.includes(pattern)) {
                return true;
            }
        }

        // V4.46.3: NO_DATA 不可重试
        if (msg.includes('NO_DATA')) {
            return false;
        }

        // V4.46.3: SIZE_TOO_SMALL 可重试（可能是 403 逃逸）
        if (msg.includes('SIZE_TOO_SMALL')) {
            return true;
        }

        return false;
    }

    /**
     * 带弹性重试的单场收割
     * @param {Object} match - 比赛信息
     * @param {number} index - 任务索引
     * @param {number} maxRetries - 最大重试次数
     * @returns {Promise<Object>} 收割结果
     */
    async harvestWithRetry(match, index, maxRetries = 3) {
        const { match_id, home_team, away_team } = match;
        let lastError = null;
        let consecutiveSizeTooSmall = 0;  // V4.46.3: 连续 SIZE_TOO_SMALL 计数

        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                const result = await this._harvestSingleMatch(match, index, attempt);

                if (result.success) {
                    if (attempt > 1) {
                        console.log(`✅ [RETRY-${attempt}] ${home_team} vs ${away_team} 重试成功`);
                        this.stats.retries++;
                    }
                    return result;
                }

                // V4.46.3: 连续 SIZE_TOO_SMALL 检测
                if (result.error && result.error.includes('SIZE_TOO_SMALL')) {
                    consecutiveSizeTooSmall++;
                    if (consecutiveSizeTooSmall >= 3) {
                        console.log(`⏸️  [COOLDOWN] Worker 休息 30 秒 (连续 ${consecutiveSizeTooSmall} 次 SIZE_TOO_SMALL)...`);
                        await this._delay(30000);
                        consecutiveSizeTooSmall = 0;  // 重置计数
                    }
                }

                if (!this._isRetryableError(new Error(result.error))) {
                    return result;
                }

                lastError = result.error;
            } catch (error) {
                lastError = error.message;

                if (!this._isRetryableError(error)) {
                    return {
                        success: false,
                        match_id,
                        error: error.message,
                        attempts: attempt
                    };
                }
            }

            if (attempt < maxRetries) {
                const backoffMs = Math.min(1000 * Math.pow(2, attempt), 8000);  // V4.46.3: 缩短退避
                const workerId = (index % this.config.maxWorkers) + 1;

                // V4.46.3: 403 逃逸策略 - 强制切换到不同端口
                const currentIdentity = this.networkManager?.getWorkerIdentity(workerId);

                if (currentIdentity) {
                    // 强制切换到随机新端口（避障）
                    const newPort = await this.networkManager.forceReassignPort(workerId, currentIdentity.proxy.port);

                    // 清理 Cookie（403 逃逸）
                    if (this.networkManager.sessionManager) {
                        await this.networkManager.sessionManager.clearSession(currentIdentity.proxy.port);
                        console.log(`🧹 [RETRY-${attempt + 1}] 清理旧 Cookie...`);
                    }

                    console.log(`🔄 [RETRY-${attempt + 1}] ${home_team} vs ${away_team} 切换端口 ${currentIdentity.proxy.port} → ${newPort?.port || newPort}...`);
                }

                await this._delay(backoffMs);
            }
        }

        return {
            success: false,
            match_id,
            error: `重试 ${maxRetries} 次后仍失败: ${lastError}`,
            attempts: maxRetries
        };
    }

    /**
     * 单次收割尝试
     * @param {Object} match - 比赛信息
     * @param {number} index - 任务索引
     * @param {number} attempt - 当前尝试次数
     * @returns {Promise<Object>} 收割结果
     * @private
     */
    async _harvestSingleMatch(match, index, attempt = 1) {
        const { match_id, home_team, away_team } = match;
        const workerId = (index % this.config.maxWorkers) + 1;
        const isRetry = attempt > 1;

        // V4.46: 记录收割开始时间
        const harvestStartTime = Date.now();
        this.metricsClient.recordHarvestStart(match_id, workerId);

        // V4.46.3 HYPER-DRIVE: 超频延迟 (1-3s)
        const baseDelay = isRetry ? 1000 : this.config.minDelayMs;
        const maxDelay = isRetry ? 2000 : this.config.maxDelayMs;
        const delay = baseDelay + Math.random() * (maxDelay - baseDelay);
        await this._delay(delay);

        // 获取 Worker 身份
        const identity = await this.networkManager.assignWorkerIdentity(workerId);

        // V4.46.3 HYPER-DRIVE: 使用 Context 池复用
        let contextResult;
        try {
            contextResult = await this._getOrCreateContext(workerId, identity);
        } catch (contextError) {
            console.error(`❌ [W${workerId}] Context 创建失败: ${contextError.message}`);
            return { success: false, match_id, error: contextError.message, workerId, attempt };
        }

        const { context, isNew: isNewContext } = contextResult;
        let page = null;

        const logPrefix = isRetry ? `[W${workerId}-R${attempt}]` : `[W${workerId}]`;

        try {
            // 创建新页面（而非新 context）
            page = await context.newPage();
            await this._injectStealthScripts(page);

            // 首页预热 - 仅在新 context 时执行完整预热
            if (isNewContext) {
                await this._warmupHomepage(page, { scrollMore: false, randomScrolls: false });
            }

            // 导航到目标页面
            const targetUrl = this.getTargetUrl(match);
            await page.goto(targetUrl, {
                waitUntil: 'domcontentloaded',
                timeout: 60000
            });

            // 行为模拟 - 简化版
            const moves = this._randomInRange(3, 5);
            for (let i = 0; i < moves; i++) {
                await page.mouse.move(
                    this._randomInRange(100, 1800),
                    this._randomInRange(100, 900),
                    { steps: 5 }
                );
                await this._delay(100);
            }

            await page.waitForTimeout(isRetry ? 2000 : 3000);

            // 调用子类实现的数据提取逻辑
            const capturedData = await this.extractData(page, match);

            // 验证数据
            if (!capturedData) {
                throw new Error('NO_DATA:无法获取数据');
            }

            const size = JSON.stringify(capturedData).length;
            if (size < 1000) {
                // V4.46.3 HYPER-DRIVE: 403 逃逸 - 仅清理 cookies
                await this._escape403(workerId);
                throw new Error(`SIZE_TOO_SMALL:${size}`);
            }

            // 标记代理成功
            await this.networkManager.markProxySuccess(workerId);

            // 保存数据（由子类实现）
            if (!this.config.dryRun) {
                await this.saveData(match_id, capturedData);
            }

            // V4.46: 记录收割成功指标
            const harvestDuration = Date.now() - harvestStartTime;
            this.metricsClient.recordHarvestSuccess(
                match_id,
                workerId,
                harvestDuration,
                size,
                identity.proxy.port
            );

            console.log(`✅ ${logPrefix} ${home_team} vs ${away_team} | ${size} bytes | Port ${identity.proxy.port} | ${harvestDuration}ms`);

            return { success: true, match_id, size, workerId, port: identity.proxy.port, attempt, duration: harvestDuration };

        } catch (error) {
            await this.networkManager.markProxyFailed(workerId, error.message);

            // V4.46: 记录收割失败指标
            const harvestDuration = Date.now() - harvestStartTime;
            const errorType = this._classifyError(error.message);
            this.metricsClient.recordHarvestFailure(
                match_id,
                workerId,
                errorType,
                error.message,
                identity?.proxy?.port
            );

            if (attempt >= 3 || !this._isRetryableError(error)) {
                console.error(`❌ ${logPrefix} ${home_team} vs ${away_team}: ${error.message}`);
            }

            return { success: false, match_id, error: error.message, workerId, attempt, errorType, duration: harvestDuration };
        } finally {
            // V4.46.3 HYPER-DRIVE: 仅关闭 page，保留 context 供复用
            if (page) {
                try {
                    await page.close();
                } catch (e) {
                    // 忽略关闭错误
                }
            }
        }
    }

    /**
     * V4.46: 分类错误类型
     * @param {string} errorMessage - 错误消息
     * @returns {string} 错误类型
     * @private
     */
    _classifyError(errorMessage) {
        const msg = (errorMessage || '').toLowerCase();
        // V4.46.1: 全局熔断错误识别
        if (msg.includes('circuit_breaker_open') || msg.includes('全局熔断') || msg.includes('所有代理节点不可用')) return 'BLOCKED';
        if (msg.includes('403') || msg.includes('forbidden')) return 'RATE_LIMITED';
        if (msg.includes('timeout') || msg.includes('timed out')) return 'TIMEOUT';
        if (msg.includes('no_data') || msg.includes('size_too_small')) return 'NO_DATA';
        if (msg.includes('connection') || msg.includes('network')) return 'NETWORK_ERROR';
        if (msg.includes('turnstile') || msg.includes('captcha')) return 'BLOCKED';
        return 'UNKNOWN';
    }

    // ========================================================================
    // V4.46.3 HYPER-DRIVE: Browser Context Pooling
    // ========================================================================

    /**
     * 获取或创建 BrowserContext（带复用池）
     * V4.46.5 HARDENING: 增加 LRU 淘汰机制
     * @param {number} workerId - Worker ID
     * @param {Object} identity - Worker 身份信息
     * @returns {Promise<{context: BrowserContext, isNew: boolean, poolInfo: Object}>}
     * @private
     */
    async _getOrCreateContext(workerId, identity) {
        const poolEntry = this._contextPool.get(workerId);
        const currentPort = identity.proxy.port;

        // 检查是否需要重建 context
        let needsRebuild = false;
        let reason = '';

        if (!poolEntry) {
            needsRebuild = true;
            reason = 'NEW_WORKER';
        } else if (poolEntry.usageCount >= this._contextMaxUsage) {
            needsRebuild = true;
            reason = `MAX_USAGE(${poolEntry.usageCount}/${this._contextMaxUsage})`;
        } else if (poolEntry.lastPort !== currentPort) {
            needsRebuild = true;
            reason = `PORT_CHANGE(${poolEntry.lastPort}→${currentPort})`;
        }

        if (needsRebuild) {
            // V4.46.5 HARDENING: 在创建新 Context 前检查池子大小
            await this._evictLRUContext();

            // 关闭旧 context
            if (poolEntry?.context) {
                try {
                    await poolEntry.context.close();
                } catch (e) {
                    // 忽略关闭错误
                }
            }

            // 创建新 context
            const proxyConfig = process.env.DISABLE_PROXY === 'true' ? undefined : { server: identity.proxy.url };

            const context = await this.browser.newContext({
                viewport: identity.stealth.viewport,
                userAgent: identity.stealth.userAgent,
                extraHTTPHeaders: identity.stealth.extraHTTPHeaders,
                proxy: proxyConfig,
                deviceScaleFactor: identity.stealth.deviceScaleFactor || 1,
                locale: identity.stealth.locale || 'en-US',
                timezoneId: identity.stealth.timezoneId || 'Europe/London'
            });

            // Cookie 热加载
            let cookieLoaded = false;
            if (this.networkManager) {
                cookieLoaded = await this.networkManager.loadSessionToContext(context, currentPort);
            }
            if (!cookieLoaded) {
                cookieLoaded = await this._loadBrowserStateCookies(context);
            }

            const now = Date.now();
            const newEntry = {
                context,
                usageCount: 0,
                lastPort: currentPort,
                cookieLoaded,
                createdAt: now,
                lastAccessTime: now  // V4.46.5: LRU 时间戳
            };

            this._contextPool.set(workerId, newEntry);
            this._totalContextCreations++;

            console.log(`🔄 [W${workerId}] Context 创建: ${reason} | Port ${currentPort} | Cookie=${cookieLoaded} | Pool=${this._contextPool.size}/${this._contextPoolMaxSize}`);

            return { context, isNew: true, poolInfo: newEntry };
        }

        // 复用现有 context
        poolEntry.usageCount++;
        poolEntry.lastAccessTime = Date.now();  // V4.46.5: 更新访问时间
        this._totalContextReuses++;

        console.log(`♻️  [W${workerId}] Context 复用: ${poolEntry.usageCount}/${this._contextMaxUsage} | Port ${currentPort}`);

        return { context: poolEntry.context, isNew: false, poolInfo: poolEntry };
    }

    /**
     * 403 逃逸：仅清理 Cookies 而非重启浏览器
     * @param {number} workerId - Worker ID
     * @returns {Promise<void>}
     * @private
     */
    async _escape403(workerId) {
        const poolEntry = this._contextPool.get(workerId);
        if (poolEntry?.context) {
            try {
                // 仅清理 cookies，保留 context
                await poolEntry.context.clearCookies();
                poolEntry.usageCount = 0;  // 重置计数
                console.log(`🧹 [W${workerId}] 403 逃逸: Cookies 已清理`);
            } catch (e) {
                console.log(`⚠️  [W${workerId}] 403 逃逸失败: ${e.message}`);
            }
        }
    }

    /**
     * V4.46.5 HARDENING: LRU 淘汰 - 清理最久未使用的 Context
     * 当池子大小超过上限时自动触发
     * @private
     */
    async _evictLRUContext() {
        if (this._contextPool.size <= this._contextPoolMaxSize) {
            return;
        }

        // 按 lastAccessTime 排序，找到最久未使用的条目
        let oldestEntry = null;
        let oldestWorkerId = null;
        let oldestTime = Infinity;

        for (const [workerId, entry] of this._contextPool) {
            if (entry.lastAccessTime < oldestTime) {
                oldestTime = entry.lastAccessTime;
                oldestEntry = entry;
                oldestWorkerId = workerId;
            }
        }

        if (oldestEntry && oldestWorkerId !== null) {
            try {
                if (oldestEntry.context) {
                    await oldestEntry.context.close();
                    this._contextEvictions++;
                    console.log(`🗑️ [LRU] 淘汰 W${oldestWorkerId} Context (空闲 ${((Date.now() - oldestTime) / 1000).toFixed(0)}s)`);
                }
            } catch (e) {
                // 忽略关闭错误
            }
            this._contextPool.delete(oldestWorkerId);
        }
    }

    /**
     * 清理所有 Context 池
     * @private
     */
    async _cleanupContextPool() {
        let cleaned = 0;
        for (const [workerId, entry] of this._contextPool) {
            try {
                if (entry.context) {
                    await entry.context.close();
                    cleaned++;
                }
            } catch (e) {
                // 忽略
            }
        }
        this._contextPool.clear();

        if (cleaned > 0 || this._totalContextCreations > 0) {
            const evictionRate = this._totalContextCreations > 0
                ? ((this._contextEvictions / this._totalContextCreations) * 100).toFixed(0)
                : '0';
            console.log(`🧹 Context 池清理: ${cleaned} 个 | 创建=${this._totalContextCreations} | 复用=${this._totalContextReuses} | 淘汰=${this._contextEvictions} (${evictionRate}%)`);
        }
    }

    // ========================================================================
    // 浏览器行为模拟
    // ========================================================================

    /**
     * 首页预热 - 建立 Session 信任
     * @param {import('playwright').Page} page - Playwright Page 对象
     * @param {Object} [config={}] - 预热配置
     */
    async _warmupHomepage(page, config = {}) {
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
     * 人类行为模拟
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
     * 注入原生隐身脚本
     * V4.46.1: 修复 platform 与 UA 不一致导致的指纹泄露
     * @param {import('playwright').Page} page - Playwright 页面对象
     */
    async _injectStealthScripts(page) {
        await page.addInitScript(() => {
            // ═══════════════════════════════════════════════════════════════
            // 核心指纹覆盖 - 必须与 UA 完全一致
            // ═══════════════════════════════════════════════════════════════

            // 覆盖 webdriver 标志
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
                configurable: true
            });

            // 【关键修复】覆盖 platform - 必须与 UA 中的 Windows 匹配
            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32',
                configurable: true
            });

            // 【关键修复】模拟语言 - 包含 q 值权重
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
                configurable: true
            });

            // 模拟硬件并发 (随机化)
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8 + (Math.floor(Math.random() * 17)),
                configurable: true
            });

            // 模拟设备内存
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => [4, 8, 8, 16, 16, 32][Math.floor(Math.random() * 6)],
                configurable: true
            });

            // 模拟 Chrome 插件数组
            Object.defineProperty(navigator, 'plugins', {
                get: () => {
                    const plugins = [
                        Object.create(Plugin.prototype, {
                            name: { value: 'Chrome PDF Plugin' },
                            description: { value: 'Portable Document Format' },
                            filename: { value: 'internal-pdf-viewer' },
                            length: { value: 1 }
                        }),
                        Object.create(Plugin.prototype, {
                            name: { value: 'Chrome PDF Viewer' },
                            description: { value: '' },
                            filename: { value: 'mhjfbmdg-nopdfs' },
                            length: { value: 1 }
                        }),
                        Object.create(Plugin.prototype, {
                            name: { value: 'Native Client' },
                            description: { value: '' },
                            filename: { value: 'internal-nacl' },
                            length: { value: 1 }
                        })
                    ];
                    plugins.item = (i) => plugins[i] || null;
                    plugins.namedItem = (name) => plugins.find(p => p.name === name) || null;
                    plugins.refresh = () => {};
                    return plugins;
                },
                configurable: true
            });

            // ═══════════════════════════════════════════════════════════════
            // WebGL 指纹伪装 - 随机化
            // ═══════════════════════════════════════════════════════════════
            const WEBGL_RENDERERS = [
                { vendor: 'Google Inc. (NVIDIA)', renderer: 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)' },
                { vendor: 'Google Inc. (NVIDIA)', renderer: 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 Direct3D11 vs_5_0 ps_5_0, D3D11)' },
                { vendor: 'Google Inc. (AMD)', renderer: 'ANGLE (AMD, AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0, D3D11)' },
                { vendor: 'Google Inc. (Intel)', renderer: 'ANGLE (Intel, Intel UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)' }
            ];
            const selectedRenderer = WEBGL_RENDERERS[Math.floor(Math.random() * WEBGL_RENDERERS.length)];

            const getParameterProxyHandler = {
                apply: function(target, thisArg, args) {
                    const param = args[0];
                    // UNMASKED_VENDOR_WEBGL
                    if (param === 37445) return selectedRenderer.vendor;
                    // UNMASKED_RENDERER_WEBGL
                    if (param === 37446) return selectedRenderer.renderer;
                    return target.apply(thisArg, args);
                }
            };

            if (typeof WebGLRenderingContext !== 'undefined') {
                const originalGetParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = new Proxy(originalGetParameter, getParameterProxyHandler);
            }

            if (typeof WebGL2RenderingContext !== 'undefined') {
                const originalGetParameter2 = WebGL2RenderingContext.prototype.getParameter;
                WebGL2RenderingContext.prototype.getParameter = new Proxy(originalGetParameter2, getParameterProxyHandler);
            }

            // ═══════════════════════════════════════════════════════════════
            // Canvas 指纹噪音
            // ═══════════════════════════════════════════════════════════════
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function(type) {
                if (this.width > 0 && this.height > 0) {
                    const ctx = this.getContext('2d');
                    if (ctx) {
                        // 添加微弱噪音
                        const imageData = ctx.getImageData(0, 0, this.width, this.height);
                        for (let i = 0; i < imageData.data.length; i += 4) {
                            imageData.data[i] ^= (Math.random() * 2) | 0;
                        }
                        ctx.putImageData(imageData, 0, 0);
                    }
                }
                return originalToDataURL.apply(this, arguments);
            };

            // ═══════════════════════════════════════════════════════════════
            // 隐藏自动化标志
            // ═══════════════════════════════════════════════════════════════
            delete window.__webdriver_evaluate;
            delete window.__webdriver_script_function;
            delete window.__webdriver_script_fn;
            delete window.__webdriver_unwrapped;
            delete window.__selenium_evaluate;
            delete window.__selenium_script_function;
            delete window.__selenium_script_fn;
            delete window.__fxdriver_evaluate;
            delete window.__driver_evaluate;
            delete window.__webdriver_script_fn;
            delete window.__lastWatirAlert;
            delete window.__lastWatirConfirm;
            delete window.__lastWatirPrompt;
            delete window._Selenium_IDE_Recorder;
            delete window._selenium;
            delete window.calledSelenium;

            // 删除 window.chrome.csi 和 window.chrome.loadTimes 的自动化特征
            if (window.chrome) {
                window.chrome.runtime = window.chrome.runtime || {};
            }

            // ═══════════════════════════════════════════════════════════════
            // 覆盖 permissions 查询
            // ═══════════════════════════════════════════════════════════════
            const originalQueryInterface = window.navigator.permissions?.query;
            if (originalQueryInterface) {
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQueryInterface(parameters)
                );
            }

            // ═══════════════════════════════════════════════════════════════
            // 覆盖 toString 保持原生外观
            // ═══════════════════════════════════════════════════════════════
            const oldToString = Function.prototype.toString;
            Function.prototype.toString = function() {
                if (this === navigator.permissions?.query) {
                    return 'function query() { [native code] }';
                }
                if (this === HTMLCanvasElement.prototype.toDataURL) {
                    return 'function toDataURL() { [native code] }';
                }
                return oldToString.call(this);
            };

            // ═══════════════════════════════════════════════════════════════
            // iframe contentWindow 检测绕过
            // ═══════════════════════════════════════════════════════════════
            const originalContentWindow = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'contentWindow');
            Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
                get: function() {
                    const window = originalContentWindow.get.call(this);
                    if (window) {
                        Object.defineProperty(window.navigator, 'webdriver', { get: () => undefined });
                    }
                    return window;
                }
            });

            console.log('[Stealth] V4.46.1 深度隐身脚本已注入');
        });
    }

    /**
     * 从 browser_state.json 加载 Cookie
     * @param {import('playwright').BrowserContext} context - Playwright 上下文
     * @returns {Promise<boolean>} 是否成功加载
     * @private
     */
    async _loadBrowserStateCookies(context) {
        const fs = require('fs').promises;
        const pathResolver = getPathResolver();
        const statePath = pathResolver.getBrowserStatePath();

        try {
            const content = await fs.readFile(statePath, 'utf8');
            const state = JSON.parse(content);

            if (state.cookies && state.cookies.length > 0) {
                const validCookies = state.cookies.filter(c => {
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
            return false;
        }
    }

    // ========================================================================
    // 工具方法
    // ========================================================================

    /**
     * 延时辅助方法
     * @param {number} ms - 延时毫秒数
     * @returns {Promise<void>}
     */
    _delay(ms) {
        return new Promise(resolve => {
            setTimeout(resolve, ms);
        });
    }

    /**
     * 生成指定范围内的随机整数
     * @param {number} min - 最小值
     * @param {number} max - 最大值
     * @returns {number} 随机整数
     */
    _randomInRange(min, max) {
        return Math.floor(Math.random() * (max - min + 1)) + min;
    }

    /**
     * 打印收割报告
     */
    printReport() {
        const elapsed = ((Date.now() - this.startTime) / 1000).toFixed(1);
        const rate = this.stats.total > 0
            ? ((this.stats.success / this.stats.total) * 100).toFixed(1)
            : '0.0';

        console.log('═══════════════════════════════════════════════════════════════');
        console.log(`  📊 ${this.constructor.name} 收割完成报告`);
        console.log('═══════════════════════════════════════════════════════════════');
        console.log(`  总计: ${this.stats.total} 场`);
        console.log(`  成功: ${this.stats.success} 场`);
        console.log(`  失败: ${this.stats.failed} 场`);
        console.log(`  成功率: ${rate}%`);
        console.log(`  重试次数: ${this.stats.retries}`);
        console.log(`  扫尾轮数: ${this.stats.sweepRounds}`);
        console.log(`  耗时: ${elapsed} 秒`);
        console.log(`  Worker 数: ${this.config.maxWorkers}`);

        // V4.46.3 HYPER-DRIVE: Context 池统计
        if (this._totalContextCreations > 0) {
            const reuseRate = ((this._totalContextReuses / (this._totalContextCreations + this._totalContextReuses)) * 100).toFixed(0);
            const evictionRate = ((this._contextEvictions / this._totalContextCreations) * 100).toFixed(0);
            console.log(`  Context 池: 创建=${this._totalContextCreations} 复用=${this._totalContextReuses} (${reuseRate}% 复用率) 淘汰=${this._contextEvictions} (${evictionRate}%)`);
        }

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
}

module.exports = { AbstractHarvester };
