/**
 * HarvestWorkerEntry - V175 拦截模式收割 Worker 入口
 * ==============================================
 *
 * V175 新特性:
 * - 优先使用拦截模式 (DOM 提取，提速 55%)
 * - 降级到原有的 HTML 解析模式
 * - ResourceShield 屏蔽非必要资源
 *
 * @module scripts/harvest_worker_entry
 * @version V175.0.0
 */

'use strict';

const path = require('path');
const { Client } = require('pg');

// 模块导入
const { WorkerMessenger } = require('../core/ipc');
const { ZombieKiller, preFlightCleanup } = require('../core/process');
const { BrowserManager } = require('../core/browser');
const { detectFromPage, extractAndTransform, interceptMatchDetails } = require('../parsers/fotmob');
const { extractAllStats } = require('../parsers/fotmob/XGExtractor');
const { MatchQueries, RawDataQueries } = require('../models');

// 配置导入
const PROJECT_ROOT = process.env.PROJECT_ROOT || '/app';
const FactoryConfig = require(path.join(PROJECT_ROOT, 'config/factory_config'));
const { DatabaseConfig } = require(path.join(PROJECT_ROOT, 'src/infrastructure/database/PostgresClient'));

// ============================================================================
// Worker 实例配置
// ============================================================================

const WORKER_ID = parseInt(process.env.WORKER_ID) || 1;
const PROXY_PORT = parseInt(process.env.PROXY_PORT) || FactoryConfig.PROXY_CONFIG.getPortByWorker(WORKER_ID);

// ============================================================================
// 日志工具
// ============================================================================

const log = {
    _ts: () => new Date().toISOString().slice(0, 19).replace('T', ' '),
    info: (msg) => console.log(`${log._ts()} [W${WORKER_ID}] [INFO] ${msg}`),
    success: (msg) => console.log(`${log._ts()} [W${WORKER_ID}] [OK] ✅ ${msg}`),
    warn: (msg) => console.log(`${log._ts()} [W${WORKER_ID}] [WARN] ⚠️  ${msg}`),
    error: (msg, err = null) => {
        const stack = err?.stack ? `\n${err.stack}` : '';
        console.error(`${log._ts()} [W${WORKER_ID}] [ERR] ❌ ${msg}${stack}`);
    }
};

// ============================================================================
// HarvestWorkerEntry 类
// ============================================================================

class HarvestWorkerEntry {
    constructor() {
        // 核心组件
        this.messenger = new WorkerMessenger(WORKER_ID, { silent: true });
        this.browserManager = new BrowserManager({
            workerId: WORKER_ID,
            proxyPort: PROXY_PORT,
            headless: FactoryConfig.BROWSER.headless,
            config: FactoryConfig
        });

        // 数据库
        this.dbClient = null;
        this.matchQueries = null;
        this.rawDataQueries = null;

        // 状态
        this.running = true;
        this.successCount = 0;
        this.failedCount = 0;
        this.harvestedCount = 0;
        this.retryCount = new Map();
        this.turnstileFailureCount = 0;
    }

    async init() {
        // 等待 IPC 就绪
        await this.messenger.waitForReady(5000);

        // 连接数据库
        this.dbClient = new Client({
            host: DatabaseConfig.host,
            port: DatabaseConfig.port,
            database: DatabaseConfig.database,
            user: DatabaseConfig.user,
            password: DatabaseConfig.password,
            connectionTimeoutMillis: FactoryConfig.DATABASE.connectTimeout,
            query_timeout: FactoryConfig.DATABASE.queryTimeout
        });
        await this.dbClient.connect();

        // 初始化查询类
        this.matchQueries = new MatchQueries(this.dbClient);
        this.rawDataQueries = new RawDataQueries(this.dbClient);

        log.info(`初始化完成 (Port: ${PROXY_PORT})`);

        // 发送 READY 信号
        await new Promise(r => setTimeout(r, 2000));
        this.messenger.notifyReady();
    }

    async harvest(task) {
        const { match_id, external_id, home_team, away_team, fotmob_id } = task;
        const startTime = Date.now();

        this.messenger.notifyTaskStart(match_id);

        try {
            // 1. 启动浏览器
            await this.browserManager.ensureBrowser();
            const page = await this.browserManager.newPage();

            // 2. 构建目标 URL
            const matchUrl = `https://www.fotmob.com/match/${fotmob_id}`;
            log.info(`🌐 渗透目标: ${matchUrl}`);

            // 3. V175: 尝试拦截模式 (优先)
            let apiData = null;
            let usedMode = 'intercept';

            try {
                const interceptResult = await interceptMatchDetails(page, matchUrl, {
                    timeout: 15000  // 15 秒超时
                });

                if (interceptResult.success && interceptResult.data) {
                    apiData = interceptResult.data;
                    usedMode = interceptResult.mode || 'intercept';
                    log.info(`✅ V175 拦截模式成功 (${usedMode}): ${interceptResult.responseTime}ms`);
                }
            } catch (interceptError) {
                log.warn(`拦截模式失败: ${interceptError.message}，降级到解析模式`);
            }

            // 4. 如果拦截失败，降级到原有的 HTML 解析模式
            if (!apiData) {
                usedMode = 'fallback';

                // 配置请求过滤
                await this.setupPageRoutes(page);

                // 页面加载
                await page.goto(matchUrl, {
                    timeout: 90000,
                    waitUntil: 'domcontentloaded'
                });
                await page.waitForLoadState('networkidle', { timeout: 20000 }).catch(() => {});

                // 检测 Cloudflare
                const cfResult = await detectFromPage(page);
                if (cfResult.blocked) {
                    throw new Error('CF_BLOCK:Cloudflare 拦截');
                }

                // 模拟人类行为
                await this.simulateHumanBehavior(page);

                // 提取和转换数据
                const extractResult = await extractAndTransform(page, external_id);
                if (!extractResult.success) {
                    throw new Error(extractResult.error);
                }

                apiData = extractResult.data;
                log.info(`📦 降级模式成功`);
            }

            // 5. 质量门禁
            const validation = FactoryConfig.QUALITY_GATE.isValid(apiData);
            if (!validation.valid) {
                throw new Error(`${validation.reason}:${validation.size || 0}`);
            }

            // 6. 解析和存储
            const stats = extractAllStats(apiData);
            await this.rawDataQueries.storeRawJson(match_id, apiData);
            await this.matchQueries.updateStats(match_id, stats);

            this.successCount++;
            this.harvestedCount++;
            this.retryCount.delete(match_id);
            this.turnstileFailureCount = 0;

            const responseTime = Date.now() - startTime;
            const rawSize = JSON.stringify(apiData).length;
            log.success(`${home_team} vs ${away_team} | xG: ${stats.xg_home} - ${stats.xg_away} | ${rawSize} bytes | ${usedMode}`);

            this.messenger.notifyTaskSuccess(match_id, { responseTime, rawSize, mode: usedMode });

            return true;

        } catch (error) {
            return this.handleHarvestError(task, error, startTime);
        } finally {
            await this.browserManager.closePage();
            await this.browserManager.cleanupPages();
        }
    }

    async setupPageRoutes(page) {
        await page.route('**/*', (route) => {
            const allowedTypes = ['document', 'xhr', 'fetch', 'script', 'stylesheet'];
            if (allowedTypes.includes(route.request().resourceType())) {
                route.continue();
            } else {
                route.abort();
            }
        });
    }

    async simulateHumanBehavior(page) {
        const readDelay = 3000 + Math.random() * 3000;
        await page.waitForTimeout(readDelay);

        const scrollAmount = 100 + Math.floor(Math.random() * 300);
        await page.evaluate((scroll) => window.scrollBy(0, scroll), scrollAmount);
        await page.waitForTimeout(500 + Math.random() * 500);
    }

    handleHarvestError(task, error, startTime) {
        const { match_id, home_team, away_team } = task;
        const errorType = error.message.split(':')[0];

        this.failedCount++;

        // 检测连续失败
        if (errorType.includes('SIZE_TOO_SMALL') || errorType.includes('TURNSTILE') || errorType.includes('NO_NEXT_DATA')) {
            this.turnstileFailureCount++;
            if (this.turnstileFailureCount >= 3) {
                this.messenger.notifyCoolDown({
                    error: error.message,
                    failureCount: this.turnstileFailureCount
                });
                this.switchProxy();
            }
        } else {
            this.turnstileFailureCount = 0;
        }

        // 重试逻辑
        const currentRetries = this.retryCount.get(match_id) || 0;
        if (FactoryConfig.RETRY.isRetryable(errorType) && currentRetries < FactoryConfig.RETRY.maxAttempts) {
            this.retryCount.set(match_id, currentRetries + 1);
            const backoffDelay = FactoryConfig.getExponentialBackoff(currentRetries + 1);
            log.warn(`${home_team} vs ${away_team}: ${error.message} (重试 ${currentRetries + 1})`);
            this.messenger.notifyTaskRetry(match_id, error.message, currentRetries + 1, backoffDelay);
        } else {
            log.error(`${home_team} vs ${away_team}: ${error.message}`);
            this.messenger.notifyTaskFailed(match_id, error.message);
        }

        return false;
    }

    switchProxy() {
        const newPort = this.browserManager.getNextProxyPort();
        this.browserManager.switchProxyPort(newPort);
    }

    async close() {
        this.running = false;
        await this.browserManager.safeClose();
        await this.browserManager.forceKill();
        if (this.dbClient) {
            await this.dbClient.end();
        }
    }

    async randomDelay() {
        const ms = FactoryConfig.getRandomDelay();
        await new Promise(r => setTimeout(r, ms));
    }
}

module.exports = {
    HarvestWorkerEntry,
    WORKER_ID,
    PROXY_PORT,
    log
};
