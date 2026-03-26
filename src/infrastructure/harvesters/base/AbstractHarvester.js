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
const { getErrorAuditor } = require('../../../core/harvesters/ErrorAuditor');
const { HarvesterRetryPolicy } = require('../components/HarvesterRetryPolicy');
const { HarvesterContextPool } = require('../components/HarvesterContextPool');
const { HarvesterTelemetry } = require('../components/HarvesterTelemetry');

const activeHarvesterInstances = new Set();
let globalSigintListener = null;
let globalSigtermListener = null;

class AbstractHarvester {
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
            harvestTimeoutMs: parseInt(process.env.HARVEST_TIMEOUT_MS) || config.harvestTimeoutMs || 120000,
            skipZombieCleanup: config.skipZombieCleanup || false,
            ...config,
        };

        this.pool = null;

        // V2.0: 使用 BrowserFactory 单例（确保非空）
        this.browserFactory = getBrowserFactory();

        // V2.0: 在构造函数中初始化 ErrorAuditor（测试需要）
        this.errorAuditor = getErrorAuditor();
        this.retryPolicy = new HarvesterRetryPolicy({
            errorAuditor: this.errorAuditor,
        });
        this.telemetry = new HarvesterTelemetry({
            metricsClient: getMetricsClient(),
        });

        this.networkManager = null;
        this.workerPool = null;

        this.isShuttingDown = false;
        this.shutdownPromise = null;
        this.workerLogger = logger.createWorkerLogger(0, 0);

        this.contextPool = new HarvesterContextPool({
            maxUsage: 10,
            maxSize: 20,
        });
        this._bindContextPoolCompatibility();
        this._bindTelemetryCompatibility();

        this._setupGracefulShutdown();
    }

    _bindContextPoolCompatibility() {
        const stats = () => this.contextPool.getMutableStats();
        const bind = (name, getter, setter) => ({
            configurable: true,
            enumerable: false,
            get: getter,
            set: setter
        });

        Object.defineProperties(this, {
            _contextPool: bind('_contextPool', () => this.contextPool.getPool(), value => this.contextPool.replacePool(value)),
            _contextMaxUsage: bind('_contextMaxUsage', () => this.contextPool.config.maxUsage, value => { this.contextPool.config.maxUsage = value; }),
            _contextPoolMaxSize: bind('_contextPoolMaxSize', () => this.contextPool.config.maxSize, value => { this.contextPool.config.maxSize = value; }),
            _totalContextCreations: bind('_totalContextCreations', () => stats().totalCreations, value => { stats().totalCreations = value; }),
            _totalContextReuses: bind('_totalContextReuses', () => stats().totalReuses, value => { stats().totalReuses = value; }),
            _contextEvictions: bind('_contextEvictions', () => stats().totalEvictions, value => { stats().totalEvictions = value; })
        });
    }

    _bindTelemetryCompatibility() {
        const bind = (getter, setter) => ({
            configurable: true,
            enumerable: false,
            get: getter,
            set: setter
        });

        Object.defineProperties(this, {
            stats: bind(() => this.telemetry.getStats(), value => this.telemetry.replaceStats(value)),
            startTime: bind(() => this.telemetry.startTime, value => this.telemetry.setStartTime(value)),
            metricsClient: bind(() => this.telemetry.metricsClient, value => this.telemetry.setMetricsClient(value))
        });
    }

    async extractData(page, match) {
        throw new Error('子类必须实现 extractData() 方法');
    }

    getTargetUrl(match) {
        throw new Error('子类必须实现 getTargetUrl() 方法');
    }

    async saveData(matchId, data) {
        throw new Error('子类必须实现 saveData() 方法');
    }
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
        this.retryPolicy.setErrorAuditor(this.errorAuditor);

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

    async cleanup() {
        await this._cleanupContextPool();
        this._teardownGracefulShutdown();

        if (this.browserFactory) {
            await this.browserFactory.close();
        }

        if (this.pool) {
            await this.pool.end();
            console.log('✅ 数据库连接池已关闭');
        }
        console.log('🛹 资源已清理');
    }
    _setupGracefulShutdown() {
        activeHarvesterInstances.add(this);

        if (!globalSigintListener) {
            globalSigintListener = () => {
                for (const instance of Array.from(activeHarvesterInstances)) {
                    instance._handleGracefulShutdown('SIGINT');
                }
            };
            process.on('SIGINT', globalSigintListener);
        }

        if (!globalSigtermListener) {
            globalSigtermListener = () => {
                for (const instance of Array.from(activeHarvesterInstances)) {
                    instance._handleGracefulShutdown('SIGTERM');
                }
            };
            process.on('SIGTERM', globalSigtermListener);
        }
    }

    async _handleGracefulShutdown(signal) {
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
    }

    async _waitForWorkers() {
        if (this.workerPool) {
            await this.workerPool.waitForAll(count => {
                logger.debug(`等待 ${count} 个 Worker...`);
            });
        }
    }

    async _cleanup() {
        this._teardownGracefulShutdown();

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
    _isRetryableError(error) {
        return this.retryPolicy.isRetryableError(error);
    }

    _classifyError(errorMessage) {
        return this.retryPolicy.classifyError(errorMessage);
    }

    _classifyDatabaseError(error) {
        return this.retryPolicy.classifyDatabaseError(error);
    }

    _classifyFileError(error) {
        return this.retryPolicy.classifyFileError(error);
    }

    _getRecommendedBackoff(attempt) {
        return this.retryPolicy.getRecommendedBackoff(attempt);
    }

    async harvestWithRetry(match, index, maxRetries = 3) {
        return this.retryPolicy.executeWithRetry(this, match, index, maxRetries);
    }

    async _harvestSingleMatch(match, index, attempt = 1) {
        const { match_id, home_team, away_team } = match;
        const workerId = (index % this.config.maxWorkers) + 1;
        const isRetry = attempt > 1;

        const harvestStartTime = Date.now();
        this._recordHarvestStart(match_id, workerId);

        // V4.46.3 HYPER-DRIVE: 超频延迟 (1-3s)
        const baseDelay = isRetry ? 1000 : this.config.minDelayMs;
        const maxDelay = isRetry ? 2000 : this.config.maxDelayMs;
        const delay = baseDelay + Math.random() * (maxDelay - baseDelay);
        await this._delay(delay);

        const identity = await this.networkManager.assignWorkerIdentity(workerId);

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

        console.log(`${logPrefix} Harvesting Match: ${match_id} | ${home_team} vs ${away_team}`);

        try {
            page = await context.newPage();
            await this.browserFactory.injectStealthScripts(page);

            if (isNewContext) {
                await this.browserFactory.warmupHomepage(page, { scrollMore: false, randomScrolls: false });
            }

            const targetUrl = this.getTargetUrl(match);
            await page.goto(targetUrl, {
                waitUntil: 'domcontentloaded',
                timeout: 60000,
            });

            await this.browserFactory.quickMouseMove(page, 3, 5);

            await page.waitForTimeout(isRetry ? 2000 : 3000);

            const capturedData = await this.extractData(page, match);

            if (!capturedData) {
                throw new Error('NO_DATA:无法获取数据');
            }

            const size = JSON.stringify(capturedData).length;
            if (size < 1000) {
                await this._escape403(workerId);
                throw new Error(`SIZE_TOO_SMALL:${size}`);
            }

            await this.networkManager.markProxySuccess(workerId);

            if (!this.config.dryRun) {
                await this.saveData(match_id, capturedData);
            }

            const harvestDuration = Date.now() - harvestStartTime;
            this._recordHarvestSuccess(match_id, workerId, harvestDuration, size, identity.proxy.port);

            console.log(`${logPrefix} Success: Data Saved. | ${match_id} | ${size} bytes | ${harvestDuration}ms`);
            console.log(`✅ ${logPrefix} ${home_team} vs ${away_team} | Port ${identity.proxy.port}`);

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

            const harvestDuration = Date.now() - harvestStartTime;
            const errorType = this._classifyError(error.message);
            this._recordHarvestFailure(match_id, workerId, errorType, error.message, identity?.proxy?.port);

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
            if (page) {
                try {
                    await page.close();
                } catch (e) {
                    // 忽略关闭错误
                }
            }

            const errorMessage = arguments[3]?.error || '';
            if (errorMessage && (
                errorMessage.includes('RETRYABLE_RESOURCE_ERROR') ||
                errorMessage.includes('Object collected') ||
                errorMessage.includes('target closed')
            )) {
                await this._closeWorkerContext(workerId, '资源回收错误');
            }
        }
    }

    async _triggerAutoAuth(index, errorMessage) {
        return this.retryPolicy.handleBlockedRecovery(this, index, errorMessage);
    }

    async _getOrCreateContext(workerId, identity) {
        const result = await this.contextPool.getOrCreate(workerId, identity, {
            browserFactory: this.browserFactory,
            networkManager: this.networkManager,
        });

        return {
            context: result.context,
            isNew: result.isNew,
            poolInfo: result.entry
        };
    }

    async _escape403(workerId) {
        await this.contextPool.clearCookies(workerId);
    }

    async _evictLRUContext() {
        await this.contextPool.evictLRU();
    }

    async _cleanupContextPool() {
        await this.contextPool.closeAllContexts();
    }

    _isContextValid(workerId) {
        return this.contextPool.isContextValid(workerId);
    }

    async _closeWorkerContext(workerId, reason = '') {
        return this.contextPool.closeWorkerContext(workerId, reason);
    }

    async _injectStealthScripts(page) {
        await this.browserFactory.injectStealthScripts(page);
    }

    async _simulateHumanBehavior(page) {
        await this.browserFactory.simulateHumanBehavior(page);
    }

    async _warmupHomepage(page, config = {}) {
        await this.browserFactory.warmupHomepage(page, config);
    }

    async _loadBrowserStateCookies(context) {
        return this.browserFactory.loadBrowserStateCookies(context);
    }

    _recordRetry() {
        this.telemetry.recordRetry();
    }

    _recordSuccess() {
        this.telemetry.recordSuccess();
    }

    _recordFailure() {
        this.telemetry.recordFailure();
    }

    _recordHarvestStart(matchId, workerId) {
        this.telemetry.recordHarvestStart(matchId, workerId);
    }

    _recordHarvestSuccess(matchId, workerId, durationMs, size, port) {
        this.telemetry.recordHarvestSuccess(matchId, workerId, durationMs, size, port);
    }

    _recordHarvestFailure(matchId, workerId, errorType, errorMessage, port) {
        this.telemetry.recordHarvestFailure(matchId, workerId, errorType, errorMessage, port);
    }

    _logBatchStats(payload = {}) {
        this.telemetry.logBatchStats(logger, payload);
    }

    _generateHarvestSummary() {
        return this.telemetry.generateHarvestSummary({
            harvesterName: this.constructor.name,
            maxWorkers: this.config.maxWorkers,
            contextStats: this.contextPool.getMutableStats(),
            workerIdentities: this.networkManager?.workerIdentities || null
        });
    }

    _delay(ms) {
        return new Promise(resolve => { setTimeout(resolve, ms); });
    }

    _teardownGracefulShutdown() {
        activeHarvesterInstances.delete(this);

        if (activeHarvesterInstances.size === 0 && globalSigintListener) {
            process.removeListener('SIGINT', globalSigintListener);
            globalSigintListener = null;
        }

        if (activeHarvesterInstances.size === 0 && globalSigtermListener) {
            process.removeListener('SIGTERM', globalSigtermListener);
            globalSigtermListener = null;
        }
    }

    _randomInRange(min, max) {
        return Math.floor(Math.random() * (max - min + 1)) + min;
    }

    printReport() {
        this.telemetry.printReport({
            harvesterName: this.constructor.name,
            maxWorkers: this.config.maxWorkers,
            contextStats: this.contextPool.getMutableStats(),
            workerIdentities: this.networkManager?.workerIdentities || null
        });
    }
}

module.exports = { AbstractHarvester };
