/**
 * V172-FINAL Worker 进程 (生产就绪版)
 * ====================================
 *
 * 由 Master 进程 fork 启动
 * 绑定唯一代理端口，独立浏览器实例
 *
 * V172 改进:
 * - 使用统一配置中心 (factory_config.js)
 * - 增强重试逻辑 (指数退避)
 * - 连接池管理 (100% 资源释放)
 * - 质量门禁重试 (任务回队)
 *
 * @module scripts/ops/harvest_worker
 * @version V172.100 (Production Ready)
 */

'use strict';

const path = require('path');
const fs = require('fs');

// ============================================================================
// 配置加载
// ============================================================================

const PROJECT_ROOT = process.env.PROJECT_ROOT || '/app';
const FactoryConfig = require(path.join(PROJECT_ROOT, 'config/factory_config'));
const { DatabaseConfig } = require(path.join(PROJECT_ROOT, 'src/infrastructure/database/PostgresClient'));
const { Client } = require('pg');
const { chromium } = require('playwright');

// ============================================================================
// Worker 实例配置 (从环境变量或配置中心获取)
// ============================================================================

const WORKER_ID = parseInt(process.env.WORKER_ID) || 1;
const PROXY_PORT = parseInt(process.env.PROXY_PORT) || FactoryConfig.PROXY_CONFIG.defaultPort;
const COOKIE_SAVE_INTERVAL = parseInt(process.env.COOKIE_SAVE_INTERVAL) || FactoryConfig.BROWSER.cookieSaveInterval;

// ============================================================================
// 静态指纹 (从配置中心获取)
// ============================================================================

const STATIC_FINGERPRINT = FactoryConfig.FINGERPRINT.static;

// ============================================================================
// Logger
// ============================================================================

const log = {
    info: (msg) => console.log(`[Worker ${WORKER_ID}] ${msg}`),
    success: (msg) => console.log(`[Worker ${WORKER_ID}] ✅ ${msg}`),
    warn: (msg) => console.log(`[Worker ${WORKER_ID}] ⚠️  ${msg}`),
    error: (msg) => console.log(`[Worker ${WORKER_ID}] ❌ ${msg}`),
    debug: (msg) => {
        if (FactoryConfig.LOG_CONFIG.level === 'debug') {
            console.log(`[Worker ${WORKER_ID}] 🔍 ${msg}`);
        }
    }
};

// ============================================================================
// HarvestWorker 类 (生产就绪版)
// ============================================================================

class HarvestWorker {
    constructor() {
        this.client = null;
        this.browser = null;
        this.context = null;
        this.page = null;  // V172: 跟踪当前页面，确保资源释放
        this.successCount = 0;
        this.failedCount = 0;
        this.harvestedCount = 0;
        this.running = true;
        this.currentTask = null;  // V172: 当前任务引用
        this.retryCount = new Map();  // V172: 任务重试计数器
    }

    // ========================================================================
    // 初始化
    // ========================================================================

    async init() {
        try {
            // 连接数据库 (带超时)
            this.client = new Client({
                host: DatabaseConfig.host,
                port: DatabaseConfig.port,
                database: DatabaseConfig.database,
                user: DatabaseConfig.user,
                password: DatabaseConfig.password,
                connectionTimeoutMillis: FactoryConfig.DATABASE.connectTimeout,
                query_timeout: FactoryConfig.DATABASE.queryTimeout
            });
            await this.client.connect();

            log.info(`初始化完成 (Port: ${PROXY_PORT})`);
            process.send({ type: 'READY' });

        } catch (error) {
            log.error(`初始化失败: ${error.message}`);
            await this._safeClose();
            process.exit(1);
        }
    }

    // ========================================================================
    // V172: 安全资源释放 (100% 闭环)
    // ========================================================================

    async _safeClose() {
        const errors = [];

        // 1. 关闭当前页面
        if (this.page) {
            try {
                await this.page.close();
            } catch (e) {
                errors.push(`page: ${e.message}`);
            }
            this.page = null;
        }

        // 2. 关闭浏览器上下文
        if (this.context) {
            try {
                await this.context.close();
            } catch (e) {
                errors.push(`context: ${e.message}`);
            }
            this.context = null;
        }

        // 3. 关闭浏览器
        if (this.browser) {
            try {
                await this.browser.close();
            } catch (e) {
                errors.push(`browser: ${e.message}`);
            }
            this.browser = null;
        }

        // 4. 关闭数据库连接
        if (this.client) {
            try {
                await this.client.end();
            } catch (e) {
                errors.push(`db: ${e.message}`);
            }
            this.client = null;
        }

        if (errors.length > 0) {
            log.warn(`关闭时有错误: ${errors.join(', ')}`);
        }
    }

    async close() {
        this.running = false;
        await this._safeClose();
    }

    // ========================================================================
    // 浏览器初始化 (使用配置中心)
    // ========================================================================

    async ensureBrowser() {
        if (!this.browser) {
            const proxyServer = FactoryConfig.PROXY_CONFIG.getServer(PROXY_PORT);

            this.browser = await chromium.launch({
                headless: FactoryConfig.BROWSER.headless,
                proxy: { server: proxyServer },
                args: FactoryConfig.BROWSER.launchArgs
            });

            log.debug(`浏览器已启动 (代理: ${proxyServer})`);
        }

        if (!this.context) {
            const statePath = FactoryConfig.BROWSER.getStatePath();
            const contextOptions = {
                userAgent: STATIC_FINGERPRINT.userAgent,
                viewport: STATIC_FINGERPRINT.viewport,
                locale: STATIC_FINGERPRINT.locale,
                timezoneId: STATIC_FINGERPRINT.timezoneId
            };

            // 加载持久化状态
            if (fs.existsSync(statePath)) {
                contextOptions.storageState = statePath;
                log.debug('已加载浏览器状态');
            }

            this.context = await this.browser.newContext(contextOptions);

            // V172: 注入 Stealth 脚本
            await this._injectStealthScript();
        }
    }

    /**
     * V172: 注入 Stealth 脚本
     */
    async _injectStealthScript() {
        await this.context.addInitScript(() => {
            // 禁用 navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

            // 硬件并发数伪装
            Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });

            // 设备内存伪装
            Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });

            // 屏蔽自动化标志
            window.chrome = { runtime: {} };
        });

        log.debug('Stealth 脚本已注入');
    }

    // ========================================================================
    // Cookie 状态保存
    // ========================================================================

    async saveCookieState() {
        if (this.context) {
            try {
                const profilePath = FactoryConfig.BROWSER.profilePath;
                const statePath = FactoryConfig.BROWSER.getStatePath();

                if (!fs.existsSync(profilePath)) {
                    fs.mkdirSync(profilePath, { recursive: true });
                }

                const state = await this.context.storageState();
                fs.writeFileSync(statePath, JSON.stringify(state, null, 2));
                log.debug('Cookie 状态已保存');

            } catch (e) {
                log.warn(`Cookie 保存失败: ${e.message}`);
            }
        }
    }

    // ========================================================================
    // V172: 单场收割 (带重试逻辑)
    // ========================================================================

    async harvest(task) {
        const { match_id, external_id, home_team, away_team } = task;
        const startTime = Date.now();

        this.currentTask = task;
        process.send({ type: 'TASK_START', matchId: match_id });

        try {
            await this.ensureBrowser();
            this.page = await this.context.newPage();

            // V172: 访问首页预热
            await this.page.goto('https://www.fotmob.com/', {
                timeout: FactoryConfig.TIMING.apiTimeout
            });
            await this.page.waitForTimeout(2000);

            // V172: 请求 API
            const apiData = await this.page.evaluate(async (matchId) => {
                try {
                    const res = await fetch(`https://www.fotmob.com/api/matchDetails?matchId=${matchId}`, {
                        credentials: 'include'
                    });
                    return await res.json();
                } catch (e) {
                    return { error: e.message };
                }
            }, external_id);

            // ====================================================================
            // V172: 质量门禁检查
            // ====================================================================

            const validation = FactoryConfig.QUALITY_GATE.isValid(apiData);

            if (!validation.valid) {
                throw new Error(`${validation.reason}:${validation.size || 0}`);
            }

            // ====================================================================
            // 解析和存储
            // ====================================================================

            const parsedData = this.parseMatchData(apiData);

            await this.storeRawJson(match_id, apiData);
            await this.updateMatch(match_id, parsedData);

            this.successCount++;
            this.harvestedCount++;

            // 清除重试计数
            this.retryCount.delete(match_id);

            const responseTime = Date.now() - startTime;
            const rawSize = JSON.stringify(apiData).length;
            log.success(`${home_team} vs ${away_team} | xG: ${parsedData.xg_home} - ${parsedData.xg_away} | ${rawSize} bytes`);

            // 定期保存 Cookie
            if (this.harvestedCount % COOKIE_SAVE_INTERVAL === 0) {
                await this.saveCookieState();
            }

            process.send({
                type: 'TASK_SUCCESS',
                matchId: match_id,
                responseTime,
                rawSize
            });

            return true;

        } catch (error) {
            this.failedCount++;

            // V172: 判断是否可重试
            const errorType = error.message.split(':')[0];
            const retryKey = match_id;
            const currentRetries = this.retryCount.get(retryKey) || 0;

            if (FactoryConfig.RETRY.isRetryable(errorType) && currentRetries < FactoryConfig.RETRY.maxAttempts) {
                // 可重试：增加计数并通知 Master
                this.retryCount.set(retryKey, currentRetries + 1);

                const backoffDelay = FactoryConfig.getExponentialBackoff(currentRetries + 1);
                log.warn(`${home_team} vs ${away_team}: ${error.message} (重试 ${currentRetries + 1}/${FactoryConfig.RETRY.maxAttempts}, 等待 ${backoffDelay}ms)`);

                process.send({
                    type: 'TASK_RETRY',
                    matchId: match_id,
                    error: error.message,
                    retryCount: currentRetries + 1,
                    backoffDelay
                });

            } else {
                // 不可重试：标记为失败
                log.error(`${home_team} vs ${away_team}: ${error.message} (最终失败)`);

                process.send({
                    type: 'TASK_FAILED',
                    matchId: match_id,
                    error: error.message
                });
            }

            return false;

        } finally {
            // V172: 确保 page 被关闭 (防泄漏)
            if (this.page) {
                try {
                    await this.page.close();
                } catch (e) {
                    log.debug(`关闭 page 失败: ${e.message}`);
                }
                this.page = null;
            }
            this.currentTask = null;
        }
    }

    // ========================================================================
    // 数据解析
    // ========================================================================

    parseMatchData(apiData) {
        const result = {
            xg_home: null,
            xg_away: null,
            possession_home: null,
            possession_away: null
        };

        try {
            const periods = apiData?.content?.stats?.Periods;
            const allStats = periods?.All?.stats || [];

            // 查找 xG
            const xgGroup = allStats.find(g => {
                const title = (g.title || '').toLowerCase();
                return title.includes('expected goals');
            });

            if (xgGroup?.stats) {
                const xgRow = xgGroup.stats.find(s =>
                    (s.key || '').toLowerCase() === 'expected_goals'
                );

                if (xgRow?.stats?.length >= 2) {
                    result.xg_home = parseFloat(xgRow.stats[0]);
                    result.xg_away = parseFloat(xgRow.stats[1]);
                }
            }

        } catch (e) {
            log.warn(`解析失败: ${e.message}`);
        }

        // NaN 容错
        if (isNaN(result.xg_home)) result.xg_home = null;
        if (isNaN(result.xg_away)) result.xg_away = null;

        return result;
    }

    // ========================================================================
    // 数据存储
    // ========================================================================

    async storeRawJson(matchId, rawData) {
        const query = `
            INSERT INTO raw_match_data (match_id, l2_raw_json, collected_at)
            VALUES ($1, $2::jsonb, NOW())
            ON CONFLICT (match_id) DO UPDATE SET
                l2_raw_json = EXCLUDED.l2_raw_json,
                collected_at = NOW()
        `;
        await this.client.query(query, [matchId, JSON.stringify(rawData)]);
    }

    async updateMatch(matchId, parsedData) {
        const query = `
            UPDATE matches SET
                xg_home = $2,
                xg_away = $3,
                updated_at = NOW()
            WHERE match_id = $1
        `;
        await this.client.query(query, [matchId, parsedData.xg_home, parsedData.xg_away]);
    }

    // ========================================================================
    // 随机延时 (使用配置中心)
    // ========================================================================

    async randomDelay() {
        const ms = FactoryConfig.getRandomDelay();
        const seconds = (ms / 1000).toFixed(1);
        log.debug(`休眠 ${seconds}s...`);
        await new Promise(r => setTimeout(r, ms));
    }

    // ========================================================================
    // 主循环
    // ========================================================================

    async run() {
        await this.init();

        // 监听 Master 消息
        process.on('message', async (msg) => {
            switch (msg.type) {
                case 'TASK':
                    await this.harvest(msg.task);
                    await this.randomDelay();
                    break;

                case 'TASK_RETRY_FROM_MASTER':
                    // V172: Master 重新分配的重试任务
                    await this.harvest(msg.task);
                    await this.randomDelay();
                    break;

                case 'SHUTDOWN':
                    log.info('收到关闭信号');
                    this.running = false;
                    await this.close();
                    process.exit(0);
                    break;
            }
        });

        // V172: 捕获未处理异常
        process.on('uncaughtException', async (error) => {
            log.error(`未捕获异常: ${error.message}`);
            await this.close();
            process.exit(1);
        });

        process.on('unhandledRejection', async (reason) => {
            log.error(`未处理的 Promise 拒绝: ${reason}`);
            await this.close();
            process.exit(1);
        });
    }
}

// ============================================================================
// 启动
// ============================================================================

const worker = new HarvestWorker();
worker.run().catch(error => {
    console.error(`[Worker ${WORKER_ID}] 启动失败:`, error);
    process.exit(1);
});
