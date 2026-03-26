/**
 * AbstractHarvester - 收割器抽象基类
 * ==================================
 *
 * 封装通用收割流程调度：
 * - 收割流程编排
 * - 弹性重试机制
 * - Context 池管理
 * - 优雅停机
 * - 统计与报告
 *
 * 子类必须实现抽象方法：extractData(), getTargetUrl(), saveData()
 *
 * 组件依赖：
 * - BrowserFactory: 浏览器生命周期管理
 * - ErrorAuditor: 错误分类与重试判断
 * - NetworkManager: 代理与身份管理
 * @module infrastructure/harvesters/base/AbstractHarvester
 * @version V2.0.0 (瘦身重构版)
 */

'use strict';

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

// V2.0: 导入剥离的组件
const { getBrowserFactory } = require('../../browser/BrowserFactory');
const { getErrorAuditor, ErrorType } = require('../../../core/harvesters/ErrorAuditor');
const { getAutoAuthManager } = require('../../auth/AutoAuthManager');

// ============================================================================
// AbstractHarvester 抽象基类
// ============================================================================

/**
 *
 */
class AbstractHarvester {
    /**
     * 创建收割器实例
     * @param {object} [config] - 配置选项
     * @param {number} [config.maxWorkers] - 最大 Worker 数量
     * @param {number} [config.minDelayMs] - 最小延时（毫秒）
     * @param {number} [config.maxDelayMs] - 最大延时（毫秒）
     * @param {number} [config.batchSize] - 每批次任务数
     * @param {string} [config.leagueFilter] - 联赛过滤器
     * @param {boolean} [config.dryRun] - 试运行模式
     * @param {number} [config.maxRetries] - 最大重试次数
     * @param {number} [config.retryDelayMs] - 重试延时（毫秒）
     * @param {number} [config.maxSweepRounds] - 最大扫尾轮数
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
            ...config,
        };

        this.pool = null;

        // V2.0: 使用 BrowserFactory 单例（确保非空）
        this.browserFactory = getBrowserFactory();

        // V2.0: 在构造函数中初始化 ErrorAuditor（测试需要）
        this.errorAuditor = getErrorAuditor();

        this.stats = {
            total: 0,
            processed: 0,
            success: 0,
            failed: 0,
            retries: 0,
            sweepRounds: 0,
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
        this._contextPool = new Map(); // workerId -> { context, usageCount, lastPort, lastAccessTime }
        this._contextMaxUsage = 10; // 每个 context 最多复用 10 次
        this._contextPoolMaxSize = 20; // V4.46.5: 池子上限，防止无限增长
        this._totalContextCreations = 0;
        this._totalContextReuses = 0;
        this._contextEvictions = 0; // V4.46.5: 淘汰计数

        this._setupGracefulShutdown();
    }

    /**
     * 抽象方法：子类必须实现数据提取逻辑
     * @param {import('playwright').Page} page - Playwright Page 对象
     * @param {object} match - 比赛信息
     * @returns {Promise<object>} 提取的数据
     * @abstract
     */
    async extractData(page, match) {
        throw new Error('子类必须实现 extractData() 方法');
    }

    /**
     * 抽象方法：子类返回目标 URL
     * @param {object} match - 比赛信息
     * @returns {string} 目标 URL
     * @abstract
     */
    getTargetUrl(match) {
        throw new Error('子类必须实现 getTargetUrl() 方法');
    }

    /**
     * 抽象方法：子类实现数据保存逻辑
     * @param {string} matchId - 比赛 ID
     * @param {object} data - 提取的数据
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
            idleTimeoutMillis: 30000,
        });

        const client = await this.pool.connect();
        await client.query('SELECT 1');
        client.release();
        console.log('✅ 数据库连接池已就绪');

        // 清理僵尸进程 (Swarm 模式下跳过，由 SwarmHarvester 统一执行)
        if (!this.config.skipZombieCleanup) {
            await preFlightCleanup();
        }

        // V2.0: 使用 BrowserFactory 启动浏览器
        await this.browserFactory.launch();

        // V2.0: 使用 ErrorAuditor 管理错误分类
        this.errorAuditor = getErrorAuditor();

        // 初始化 NetworkManager
        this.networkManager = getNetworkManager({
            maxWorkers: this.config.maxWorkers,
            stealthGenerator: generateStealthHeaders,
        });
        await this.networkManager.initialize({
            preFlightCleanup: () => this._preFlightCleanupNetworkLocks(),
        });

        // 初始化 WorkerPool
        this.workerPool = getWorkerPool({
            maxWorkers: this.config.maxWorkers,
            logger: msg => console.log(msg),
        });

        console.log(
            `📋 配置: MAX_WORKERS=${this.config.maxWorkers}, DELAY=${this.config.minDelayMs}-${this.config.maxDelayMs}ms`
        );
    }

    /**
     * 清理资源
     */
    async cleanup() {
        // V4.46.3 HYPER-DRIVE: 先清理 Context 池
        await this._cleanupContextPool();

        // V2.0: 使用 BrowserFactory 清理浏览器
        if (this.browserFactory) {
            await this.browserFactory.close();
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
        const handler = async signal => {
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
                    await Promise.race([this._waitForWorkers(), this._delay(this.config.shutdownTimeoutMs - 1000)]);
                }

                await this._cleanup();

                clearTimeout(timeoutId);
                logger.logShutdownComplete(Date.now() - (this.shutdownStartTime || Date.now()), {
                    processed: this.stats.processed,
                    success: this.stats.success,
                    failed: this.stats.failed,
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
            await this.workerPool.waitForAll(count => {
                logger.debug(`等待 ${count} 个 Worker...`);
            });
        }
    }

    /**
     * 清理资源（浏览器、数据库连接等）
     * @private
     */
    async _cleanup() {
        if (this.browserFactory) {
            try {
                await this.browserFactory.close();
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

        const lockDirs = [...pathResolver.getLockDirs(), './data/network', './data/registry', './config'];

        const specificLockFiles = [pathResolver.getRegistryLockPath(), './config/.registry.lock'];

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
     * 判断是否为可重试的错误（委托给 ErrorAuditor）
     * @param {Error} error - 错误对象
     * @returns {boolean} 是否可重试
     * @private
     */
    _isRetryableError(error) {
        return this.errorAuditor.isRetryableError(error);
    }

    /**
     * 分类错误类型（委托给 ErrorAuditor）
     * @param {string} errorMessage - 错误消息
     * @returns {string} 错误类型
     * @private
     */
    _classifyError(errorMessage) {
        return this.errorAuditor.classifyError(errorMessage);
    }

    /**
     * 带弹性重试的单场收割
     * @param {object} match - 比赛信息
     * @param {number} index - 任务索引
     * @param {number} maxRetries - 最大重试次数
     * @returns {Promise<object>} 收割结果
     */
    async harvestWithRetry(match, index, maxRetries = 3) {
        const { match_id, home_team, away_team } = match;
        const workerId = (index % this.config.maxWorkers) + 1;

        // V4.51: 调试日志 - 确认方法被调用
        console.log(`[DEBUG] harvestWithRetry called: Match ${match_id}, Worker ${workerId}`);

        let lastError = null;
        let consecutiveSizeTooSmall = 0; // V4.46.3: 连续 SIZE_TOO_SMALL 计数

        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                console.log(`[DEBUG] Attempt ${attempt} for match ${match_id}`);
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
                        console.log(
                            `⏸️  [COOLDOWN] Worker 休息 30 秒 (连续 ${consecutiveSizeTooSmall} 次 SIZE_TOO_SMALL)...`
                        );
                        await this._delay(30000);
                        consecutiveSizeTooSmall = 0; // 重置计数
                    }
                }

                if (!this._isRetryableError(new Error(result.error))) {
                    // V4.51: AutoAuth 钩子 - 检测 BLOCKED 错误并触发身份刷新
                    const errorType = this._classifyError(result.error);
                    if (errorType === ErrorType.BLOCKED) {
                        await this._triggerAutoAuth(index, result.error);
                    }
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
                        attempts: attempt,
                    };
                }
            }

            if (attempt < maxRetries) {
                const backoffMs = Math.min(1000 * Math.pow(2, attempt), 8000); // V4.46.3: 缩短退避
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

                    console.log(
                        `🔄 [RETRY-${attempt + 1}] ${home_team} vs ${away_team} 切换端口 ${currentIdentity.proxy.port} → ${newPort?.port || newPort}...`
                    );
                }

                await this._delay(backoffMs);
            }
        }

        return {
            success: false,
            match_id,
            error: `重试 ${maxRetries} 次后仍失败: ${lastError}`,
            attempts: maxRetries,
        };
    }

    /**
     * 单次收割尝试
     * @param {object} match - 比赛信息
     * @param {number} index - 任务索引
     * @param {number} attempt - 当前尝试次数
     * @returns {Promise<object>} 收割结果
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

        // V4.51: 关键业务日志 - 开始收割
        console.log(`${logPrefix} Harvesting Match: ${match_id} | ${home_team} vs ${away_team}`);

        try {
            // 创建新页面（而非新 context）
            page = await context.newPage();
            // V2.0: 使用 BrowserFactory 注入隐身脚本
            await this.browserFactory.injectStealthScripts(page);

            // 首页预热 - 仅在新 context 时执行完整预热
            if (isNewContext) {
                await this.browserFactory.warmupHomepage(page, { scrollMore: false, randomScrolls: false });
            }

            // 导航到目标页面
            const targetUrl = this.getTargetUrl(match);
            await page.goto(targetUrl, {
                waitUntil: 'domcontentloaded',
                timeout: 60000,
            });

            // V2.0: 使用 BrowserFactory 的简化版鼠标移动
            await this.browserFactory.quickMouseMove(page, 3, 5);

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
            this.metricsClient.recordHarvestSuccess(match_id, workerId, harvestDuration, size, identity.proxy.port);

            // V4.51: 关键业务日志 - 收割成功
            console.log(`${logPrefix} Success: Data Saved. | ${match_id} | ${size} bytes | ${harvestDuration}ms`);
            console.log(
                `✅ ${logPrefix} ${home_team} vs ${away_team} | Port ${identity.proxy.port}`
            );

            return {
                success: true,
                match_id,
                size,
                workerId,
                port: identity.proxy.port,
                attempt,
                duration: harvestDuration,
            };
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

            return {
                success: false,
                match_id,
                error: error.message,
                workerId,
                attempt,
                errorType,
                duration: harvestDuration,
            };
        } finally {
            // V4.46.3 HYPER-DRIVE: 仅关闭 page，保留 context 供复用
            if (page) {
                try {
                    await page.close();
                } catch (e) {
                    // 忽略关闭错误
                }
            }

            // V4.51: 物理资源强制释放 - 如果发生对象回收错误，清理该 worker 的 context
            const errorMessage = arguments[3]?.error || '';
            if (errorMessage && (
                errorMessage.includes('RETRYABLE_RESOURCE_ERROR') ||
                errorMessage.includes('Object collected') ||
                errorMessage.includes('target closed')
            )) {
                const poolEntry = this._contextPool.get(workerId);
                if (poolEntry?.context) {
                    try {
                        await poolEntry.context.close();
                        this._contextPool.delete(workerId);
                        console.log(`  🧹 [W${workerId}] 强制清理 Context (资源回收错误)`);
                    } catch (e) {
                        // 忽略关闭错误
                    }
                }
            }
        }
    }

    /**
     * V4.51: AutoAuth 自动鉴权触发钩子
     * 当检测到 BLOCKED 错误（Turnstile/Captcha）时自动触发身份刷新
     * @param {number} index - 任务索引
     * @param {string} errorMessage - 错误消息
     * @returns {Promise<void>}
     * @private
     */
    async _triggerAutoAuth(index, errorMessage) {
        const workerId = (index % this.config.maxWorkers) + 1;

        console.log('\n');
        console.log('═══════════════════════════════════════════════════════════════');
        console.log(`  \x1b[33m[AUTO-AUTH]\x1b[0m 检测到 BLOCKED 错误，触发自动身份刷新...`);
        console.log(`  错误详情: ${errorMessage}`);
        console.log('═══════════════════════════════════════════════════════════════');

        try {
            // 1. 清理当前 Worker 的 Session
            let currentPort = null;
            let newPort = null;

            if (this.networkManager?.sessionManager) {
                const identity = this.networkManager.getWorkerIdentity(workerId);
                if (identity?.proxy?.port) {
                    currentPort = identity.proxy.port;
                    await this.networkManager.sessionManager.clearSession(currentPort);
                    console.log(`  🧹 [AUTO-AUTH] 已清理 Worker ${workerId} 的旧 Session (Port ${currentPort})`);
                }
            }

            // 2. 强制切换端口
            if (this.networkManager) {
                const currentIdentity = this.networkManager.getWorkerIdentity(workerId);
                if (currentIdentity?.proxy?.port) {
                    newPort = await this.networkManager.forceReassignPort(workerId, currentIdentity.proxy.port);
                    const newPortValue = newPort?.port || newPort;
                    console.log(
                        `  🔄 [AUTO-AUTH] 端口切换: ${currentIdentity.proxy.port} → ${newPortValue}`
                    );
                    newPort = newPortValue;
                }
            }

            // 3. V4.51.1: 调用 AutoAuthManager 刷新 Session
            if (newPort) {
                const autoAuthManager = this.autoAuthManager || getAutoAuthManager();
                const refreshResult = await autoAuthManager.refreshSession(workerId, newPort);

                if (refreshResult.success) {
                    console.log(`  🔑 [AUTO-AUTH] Session 热刷新成功 (${refreshResult.cookieCount} cookies)`);
                } else {
                    console.log(`  ⚠️ [AUTO-AUTH] Session 刷新失败: ${refreshResult.error}`);
                    console.log(`  💡 提示: 请在宿主机运行 'node scripts/capture_auth.js --port ${newPort}' 手动捕获身份`);
                }
            }

            // 4. 清理 Context 池中的相关 Context
            const poolEntry = this._contextPool.get(workerId);
            if (poolEntry?.context) {
                try {
                    await poolEntry.context.close();
                    this._contextPool.delete(workerId);
                    console.log(`  🧹 [AUTO-AUTH] 已清理 Worker ${workerId} 的旧 Context`);
                } catch (e) {
                    // 忽略关闭错误
                }
            }

            console.log('  ✅ [AUTO-AUTH] 身份刷新完成，下次请求将使用新身份\n');
        } catch (error) {
            console.error(`  ❌ [AUTO-AUTH] 身份刷新失败: ${error.message}`);
            console.log('  ⚠️  将在下次收割时重试...\n');
        }
    }

    // ========================================================================
    // V4.46.3 HYPER-DRIVE: Browser Context Pooling
    // ========================================================================

    /**
     * 获取或创建 BrowserContext（带复用池）
     * V4.46.5 HARDENING: 增加 LRU 淘汰机制
     * @param {number} workerId - Worker ID
     * @param {object} identity - Worker 身份信息
     * @returns {Promise<{context: BrowserContext, isNew: boolean, poolInfo: object}>}
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

            // V2.0: 使用 BrowserFactory 创建 Context
            const context = await this.browserFactory.createContext(identity);

            // Cookie 热加载
            let cookieLoaded = false;
            if (this.networkManager) {
                cookieLoaded = await this.networkManager.loadSessionToContext(context, currentPort);
            }
            if (!cookieLoaded) {
                cookieLoaded = await this.browserFactory.loadBrowserStateCookies(context);
            }

            const now = Date.now();
            const newEntry = {
                context,
                usageCount: 0,
                lastPort: currentPort,
                cookieLoaded,
                createdAt: now,
                lastAccessTime: now, // V4.46.5: LRU 时间戳
            };

            this._contextPool.set(workerId, newEntry);
            this._totalContextCreations++;

            console.log(
                `🔄 [W${workerId}] Context 创建: ${reason} | Port ${currentPort} | Cookie=${cookieLoaded} | Pool=${this._contextPool.size}/${this._contextPoolMaxSize}`
            );

            return { context, isNew: true, poolInfo: newEntry };
        }

        // 复用现有 context
        poolEntry.usageCount++;
        poolEntry.lastAccessTime = Date.now(); // V4.46.5: 更新访问时间
        this._totalContextReuses++;

        console.log(
            `♻️  [W${workerId}] Context 复用: ${poolEntry.usageCount}/${this._contextMaxUsage} | Port ${currentPort}`
        );

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
                poolEntry.usageCount = 0; // 重置计数
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
                    console.log(
                        `🗑️ [LRU] 淘汰 W${oldestWorkerId} Context (空闲 ${((Date.now() - oldestTime) / 1000).toFixed(0)}s)`
                    );
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
            const evictionRate =
                this._totalContextCreations > 0
                    ? ((this._contextEvictions / this._totalContextCreations) * 100).toFixed(0)
                    : '0';
            console.log(
                `🧹 Context 池清理: ${cleaned} 个 | 创建=${this._totalContextCreations} | 复用=${this._totalContextReuses} | 淘汰=${this._contextEvictions} (${evictionRate}%)`
            );
        }
    }

    /**
     * 兼容旧测试：委托 BrowserFactory 注入隐身脚本
     * @param {import('playwright').Page} page
     * @returns {Promise<void>}
     * @private
     */
    async _injectStealthScripts(page) {
        await this.browserFactory.injectStealthScripts(page);
    }

    /**
     * 兼容旧测试：委托 BrowserFactory 模拟人类行为
     * @param {import('playwright').Page} page
     * @returns {Promise<void>}
     * @private
     */
    async _simulateHumanBehavior(page) {
        await this.browserFactory.simulateHumanBehavior(page);
    }

    /**
     * 兼容旧测试：委托 BrowserFactory 首页预热
     * @param {import('playwright').Page} page
     * @param {object} config
     * @returns {Promise<void>}
     * @private
     */
    async _warmupHomepage(page, config = {}) {
        await this.browserFactory.warmupHomepage(page, config);
    }

    /**
     * 兼容旧测试：委托 BrowserFactory 加载 Cookie
     * @param {import('playwright').BrowserContext} context
     * @returns {Promise<boolean>}
     * @private
     */
    async _loadBrowserStateCookies(context) {
        return this.browserFactory.loadBrowserStateCookies(context);
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
        const rate = this.stats.total > 0 ? ((this.stats.success / this.stats.total) * 100).toFixed(1) : '0.0';

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
            const reuseRate = (
                (this._totalContextReuses / (this._totalContextCreations + this._totalContextReuses)) *
                100
            ).toFixed(0);
            const evictionRate = ((this._contextEvictions / this._totalContextCreations) * 100).toFixed(0);
            console.log(
                `  Context 池: 创建=${this._totalContextCreations} 复用=${this._totalContextReuses} (${reuseRate}% 复用率) 淘汰=${this._contextEvictions} (${evictionRate}%)`
            );
        }

        if (this.networkManager && this.networkManager.workerIdentities) {
            for (const [workerId, identity] of this.networkManager.workerIdentities) {
                if (identity && identity.proxy) {
                    const successRate = (identity.getSuccessRate() * 100).toFixed(0);
                    console.log(
                        `    W${workerId}: Port ${identity.proxy.port} | ${identity.requestCount} 请求 | ${successRate}% 成功率`
                    );
                }
            }
        }
        console.log('═══════════════════════════════════════════════════════════════');
    }
}

module.exports = { AbstractHarvester };
