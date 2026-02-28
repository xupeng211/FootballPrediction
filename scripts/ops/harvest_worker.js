/**
 * V173-SENTINEL Worker 进程 (免疫系统加固版)
 * ==========================================
 *
 * 由 Master 进程 fork 启动
 * 绑定唯一代理端口，独立浏览器实例
 *
 * V173 改进:
 * - 浏览器资源"绝对释放" (Leak Proof)
 * - SIGINT/SIGTERM 信号处理
 * - 强制杀死浏览器进程 (Kill -9 级别)
 * - 动态 UA 轮换支持
 * - 深度静默模式支持
 *
 * V172 继承:
 * - 使用统一配置中心 (factory_config.js)
 * - 增强重试逻辑 (指数退避)
 * - 连接池管理 (100% 资源释放)
 * - 质量门禁重试 (任务回队)
 *
 * @module scripts/ops/harvest_worker
 * @version V173.0.0 (Sentinel Edition)
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
const PROXY_PORT = parseInt(process.env.PROXY_PORT) || FactoryConfig.PROXY_CONFIG.getPortByWorker(WORKER_ID);
const COOKIE_SAVE_INTERVAL = parseInt(process.env.COOKIE_SAVE_INTERVAL) || FactoryConfig.BROWSER.cookieSaveInterval;

// V173: 故障切换状态
let currentProxyPort = PROXY_PORT;
let turnstileFailureCount = 0;
const MAX_TURNSTILE_FAILURES = 3;

// ============================================================================
// V173: IPC 安全发送函数 (防止 process.send is not a function)
// ============================================================================

/**
 * safeSend - 安全发送消息给 Master 进程
 * 如果 process.send 不存在（非 fork 模式），则静默忽略
 */
const safeSend = (msg) => {
    try {
        if (typeof process.send === 'function') {
            process.send(msg);
        }
    } catch (e) {
        // IPC 通信失败时静默忽略
    }
};

// ============================================================================
// V173: 预清理函数 - 僵尸进程清理 (免疫系统)
// ============================================================================

/**
 * preFlightCleanup - 起飞前清理僵尸进程
 * 在 Worker 启动前执行，确保没有残留的 Chrome/Chromium 进程
 */
function preFlightCleanup() {
    const { execSync } = require('child_process');

    try {
        // 查找残留的 chromium/chrome 进程
        const zombiePids = execSync('pgrep -f "chromium|chrome" 2>/dev/null || true', {
            encoding: 'utf8',
            timeout: 5000
        }).trim();

        if (zombiePids) {
            const pids = zombiePids.split('\n').filter(p => p);
            console.log(`${log._ts()} [W${WORKER_ID}] [PRE-FLIGHT] 🧹 发现 ${pids.length} 个僵尸进程，正在清理...`);

            for (const pid of pids) {
                try {
                    execSync(`kill -9 ${pid} 2>/dev/null || true`, { timeout: 1000 });
                } catch (e) {
                    // 忽略单个进程清理失败
                }
            }
            console.log(`${log._ts()} [W${WORKER_ID}] [PRE-FLIGHT] ✅ 僵尸进程已清理`);
        } else {
            console.log(`${log._ts()} [W${WORKER_ID}] [PRE-FLIGHT] ✅ 无僵尸进程，环境干净`);
        }
    } catch (e) {
        console.log(`${log._ts()} [W${WORKER_ID}] [PRE-FLIGHT] ⚠️ 清理检查失败: ${e.message}`);
    }
}

// ============================================================================
// 静态指纹 (从配置中心获取)
// ============================================================================

const STATIC_FINGERPRINT = FactoryConfig.FINGERPRINT.static;

// ============================================================================
// Logger (V172-STRENGTHEN: 标准化日志)
// ============================================================================

const log = {
    // 时间戳生成器
    _ts: () => {
        const d = new Date();
        return `${d.toISOString().slice(0, 10)} ${d.toTimeString().slice(0, 8)}`;
    },

    info: (msg) => console.log(`${log._ts()} [W${WORKER_ID}] [INFO] ${msg}`),
    success: (msg) => console.log(`${log._ts()} [W${WORKER_ID}] [OK] ✅ ${msg}`),
    warn: (msg) => console.log(`${log._ts()} [W${WORKER_ID}] [WARN] ⚠️  ${msg}`),
    error: (msg, err = null) => {
        const stack = err?.stack ? `\n${err.stack}` : '';
        console.error(`${log._ts()} [W${WORKER_ID}] [ERR] ❌ ${msg}${stack}`);
    },
    debug: (msg) => {
        if (FactoryConfig.LOG_CONFIG.level === 'debug') {
            console.log(`${log._ts()} [W${WORKER_ID}] [DBG] 🔍 ${msg}`);
        }
    }
};

// ============================================================================
// V172-STRENGTHEN: 安全 JSON 解析器
// ============================================================================

function safeJsonParse(str, fallback = null) {
    if (!str || typeof str !== 'string') {
        return fallback;
    }
    try {
        return JSON.parse(str);
    } catch (e) {
        log.warn(`JSON 解析失败: ${e.message}, 输入前 100 字符: ${str.slice(0, 100)}`);
        return fallback;
    }
}

function safeJsonStringify(obj, fallback = '{}') {
    try {
        return JSON.stringify(obj);
    } catch (e) {
        log.warn(`JSON 序列化失败: ${e.message}`);
        return fallback;
    }
}

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
            safeSend({ type: 'READY' });

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
            const proxyServer = FactoryConfig.PROXY_CONFIG.getServer(currentProxyPort);

            // V173: 动态 UA 轮换 - 每次启动浏览器时获取随机 UA
            const dynamicUA = FactoryConfig.FINGERPRINT.getRandomUA();

            this.browser = await chromium.launch({
                headless: FactoryConfig.BROWSER.headless,
                proxy: { server: proxyServer },
                args: FactoryConfig.BROWSER.launchArgs
            });

            log.info(`浏览器已启动 (代理: ${proxyServer}, UA: ${dynamicUA.substring(0, 50)}...)`);
        }

        if (!this.context) {
            const statePath = FactoryConfig.BROWSER.getStatePath();

            // V173: 随机视口尺寸 - 每次创建 context 时随机
            const randomViewport = FactoryConfig.FINGERPRINT.getRandomViewport();

            // V173: 动态 UA - 确保每次都是新的
            const dynamicUA = FactoryConfig.FINGERPRINT.getRandomUA();

            const contextOptions = {
                userAgent: dynamicUA,
                viewport: randomViewport,
                locale: STATIC_FINGERPRINT.locale,
                timezoneId: STATIC_FINGERPRINT.timezoneId
            };

            // V173: 检查 Cookie 是否被"投毒"（过期或损坏）
            if (fs.existsSync(statePath)) {
                try {
                    const stateContent = fs.readFileSync(statePath, 'utf8');
                    const state = JSON.parse(stateContent);

                    // 检查 Cookie 是否过期（默认 24 小时）
                    const cookieMaxAge = FactoryConfig.SENTINEL_CONFIG.cookieMaxAgeMs;
                    const stateStat = fs.statSync(statePath);
                    const fileAge = Date.now() - stateStat.mtimeMs;

                    if (fileAge > cookieMaxAge) {
                        log.warn(`Cookie 已过期 (${Math.round(fileAge / 3600000)} 小时)，将使用全新身份`);
                        // 备份旧 Cookie
                        const backupPath = `${statePath}.expired.${Date.now()}`;
                        fs.renameSync(statePath, backupPath);
                        log.info(`旧 Cookie 已备份到: ${backupPath}`);
                    } else {
                        contextOptions.storageState = statePath;
                        log.debug(`已加载浏览器状态 (${Math.round(fileAge / 60000)} 分钟前)`);
                    }
                } catch (e) {
                    log.warn(`Cookie 解析失败: ${e.message}，将使用全新身份`);
                    // 删除损坏的 Cookie 文件
                    fs.unlinkSync(statePath);
                }
            }

            this.context = await this.browser.newContext(contextOptions);

            // V173: 注入 Stealth 脚本
            await this._injectStealthScript();

            log.info(`Context 已创建 (Viewport: ${randomViewport.width}x${randomViewport.height})`);
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
    // V173: 网页渗透模式 - 狸猫换太子战术
    // ========================================================================

    /**
     * V173: 模拟真人行为
     */
    async _simulateHumanBehavior() {
        // 1. 随机等待 3-6 秒 (模拟阅读时间)
        const readDelay = 3000 + Math.random() * 3000;
        await this.page.waitForTimeout(readDelay);
        log.debug(`模拟阅读 ${Math.round(readDelay / 1000)}s`);

        // 2. 随机滚动
        const scrollAmount = 100 + Math.floor(Math.random() * 300);
        await this.page.evaluate((scroll) => {
            window.scrollBy(0, scroll);
        }, scrollAmount);
        log.debug(`模拟滚动 ${scrollAmount}px`);

        // 3. 等待滚动完成
        await this.page.waitForTimeout(500 + Math.random() * 500);
    }

    /**
     * V173: 检测 Cloudflare 拦截页面
     * @returns {boolean} true 表示被拦截
     */
    async _checkCloudflareBlock() {
        const content = await this.page.content();
        const title = await this.page.title();

        // 检测 Cloudflare 挑战页面
        const cfIndicators = [
            'Just a moment...',
            'Checking your browser',
            'Please Wait...',
            'Cloudflare',
            'cf-browser-verification',
            'challenge-platform'
        ];

        const isBlocked = cfIndicators.some(indicator =>
            content.includes(indicator) || title.includes(indicator)
        );

        if (isBlocked) {
            log.warn('检测到 Cloudflare 拦截页面');
            return true;
        }

        return false;
    }

    /**
     * V173: 从 __NEXT_DATA__ 提取 JSON 数据
     */
    async _extractNextData() {
        const rawData = await this.page.evaluate(() => {
            const el = document.getElementById('__NEXT_DATA__');
            if (!el) return null;

            try {
                return JSON.parse(el.innerHTML);
            } catch (e) {
                return { error: `JSON 解析失败: ${e.message}` };
            }
        });

        return rawData;
    }

    /**
     * V173: 转换 __NEXT_DATA__ 格式为 API 兼容格式
     * FotMob 网页版数据结构:
     *   pageProps.content - 核心数据 (stats, lineup, shotmap 等)
     *   pageProps.general - 比赛基本信息
     *   pageProps.header - 头部信息
     */
    _transformNextDataToApiFormat(nextData, matchId) {
        if (!nextData || !nextData.props || !nextData.props.pageProps) {
            log.warn('__NEXT_DATA__ 结构不完整');
            return null;
        }

        const pageProps = nextData.props.pageProps;

        // V173: 网页版数据结构
        // content 包含: matchFacts, stats, playerStats, shotmap, lineup, table 等
        // 这与 API 的 content 结构兼容

        const apiFormat = {
            matchId: matchId,
            content: pageProps.content || {},
            general: pageProps.general || {},
            header: pageProps.header || {},
            // 保留元数据
            _meta: {
                source: 'web_infiltration',
                extractedAt: new Date().toISOString(),
                hasStats: !!(pageProps.content?.stats),
                hasLineup: !!(pageProps.content?.lineup),
                hasShotmap: !!(pageProps.content?.shotmap)
            }
        };

        // 验证核心数据是否存在
        if (!pageProps.content) {
            log.warn('pageProps.content 不存在');
            return null;
        }

        log.debug(`数据转换完成: stats=${apiFormat._meta.hasStats}, lineup=${apiFormat._meta.hasLineup}`);

        return apiFormat;
    }

    // ========================================================================
    // V173: 单场收割 - 网页渗透模式
    // ========================================================================

    async harvest(task) {
        const { match_id, external_id, home_team, away_team } = task;
        const startTime = Date.now();

        this.currentTask = task;
        safeSend({ type: 'TASK_START', matchId: match_id });

        try {
            await this.ensureBrowser();
            this.page = await this.context.newPage();

            // ====================================================================
            // V173: 网页渗透模式 - 访问比赛详情页
            // ====================================================================

            // V173: 构建比赛详情页 URL
            // 使用 fotmob_id（从 external_id 传递过来，纯数字格式）
            const fotmobId = task.fotmob_id;

            // 检查 ID 是否有效（必须是纯数字）
            if (!fotmobId || !/^\d+$/.test(fotmobId)) {
                log.error(`无效的 FotMob ID: ${fotmobId}`);
                throw new Error(`INVALID_FOTMOB_ID:ID 不是纯数字`);
            }

            const matchUrl = `https://www.fotmob.com/match/${fotmobId}`;
            log.info(`🌐 渗透目标: ${matchUrl}`);

            // 访问比赛页面
            await this.page.goto(matchUrl, {
                timeout: FactoryConfig.TIMING.pageTimeout,
                waitUntil: 'domcontentloaded'
            });

            // 等待网络空闲
            await this.page.waitForLoadState('networkidle', {
                timeout: 30000
            }).catch(() => {
                log.debug('网络空闲等待超时，继续处理');
            });

            // ====================================================================
            // V173: 检测 Cloudflare 拦截
            // ====================================================================

            const isBlocked = await this._checkCloudflareBlock();

            if (isBlocked) {
                // 等待 10 秒看是否自动通过
                log.info('等待 Cloudflare 验证...');
                await this.page.waitForTimeout(10000);

                const stillBlocked = await this._checkCloudflareBlock();
                if (stillBlocked) {
                    throw new Error('CF_BLOCK:Cloudflare 持续拦截');
                }
            }

            // ====================================================================
            // V173: 模拟真人行为
            // ====================================================================

            await this._simulateHumanBehavior();

            // ====================================================================
            // V173: 从 __NEXT_DATA__ 提取数据
            // ====================================================================

            const nextData = await this._extractNextData();

            if (!nextData) {
                throw new Error('NO_NEXT_DATA:无法找到 __NEXT_DATA__ 标签');
            }

            // 转换为 API 兼容格式
            const apiData = this._transformNextDataToApiFormat(nextData, external_id);

            if (!apiData) {
                throw new Error('DATA_TRANSFORM_FAILED:数据格式转换失败');
            }

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

            safeSend({
                type: 'TASK_SUCCESS',
                matchId: match_id,
                responseTime,
                rawSize
            });

            return true;

        } catch (error) {
            this.failedCount++;

            // V173: 检测错误类型
            const errorType = error.message.split(':')[0];

            // V173: CF_BLOCK 检测 - 触发 Worker 熔断
            if (errorType === 'CF_BLOCK') {
                log.error(`🚨 Cloudflare 拦截！触发 Worker 熔断`);

                // 通知 Master 该 Worker 被熔断
                safeSend({
                    type: 'WORKER_CIRCUIT_BREAK',
                    workerId: WORKER_ID,
                    error: error.message,
                    proxyPort: currentProxyPort
                });

                // 自动切换到下一个端口
                const oldPort = currentProxyPort;
                currentProxyPort = FactoryConfig.PROXY_CONFIG.getNextPort(currentProxyPort);
                log.info(`端口切换: ${oldPort} -> ${currentProxyPort}`);

                // 清理 Cookie
                const cookiePath = FactoryConfig.BROWSER.getStatePath();
                if (fs.existsSync(cookiePath)) {
                    const backupPath = `${cookiePath}.cf_blocked.${Date.now()}`;
                    fs.renameSync(cookiePath, backupPath);
                    log.warn(`Cookie 已被 Cloudflare 标记，备份到: ${backupPath}`);
                }
            }

            // V173: 检测 Turnstile/数据错误并自动切换端口
            if (errorType.includes('SIZE_TOO_SMALL') || errorType.includes('TURNSTILE') || errorType.includes('NO_NEXT_DATA')) {
                turnstileFailureCount++;

                // V173: 检查是否需要进入冷却模式
                if (FactoryConfig.FOTMOB_COOL_DOWN?.shouldTrigger(errorType, turnstileFailureCount)) {
                    log.warn(`检测到连续 ${turnstileFailureCount} 次 Turnstile 错误，触发深度静默`);

                    // 通知 Master 该 Worker 需要冷却
                    safeSend({
                        type: 'WORKER_COOL_DOWN',
                        workerId: WORKER_ID,
                        error: error.message,
                        failureCount: turnstileFailureCount
                    });

                    // V173: 自动切换到下一个端口
                    const oldPort = currentProxyPort;
                    currentProxyPort = FactoryConfig.PROXY_CONFIG.getNextPort(currentProxyPort);
                    log.info(`端口切换: ${oldPort} -> ${currentProxyPort}`);

                    // V173: 如果 Cookie 被标记，自动清理
                    if (turnstileFailureCount >= FactoryConfig.FOTMOB_COOL_DOWN.triggerThreshold) {
                        const cookiePath = FactoryConfig.BROWSER.getStatePath();
                        if (fs.existsSync(cookiePath)) {
                            const backupPath = cookiePath + '.old';
                            fs.renameSync(cookiePath, backupPath);
                            log.warn(`Cookie 已被标记，已备份到: ${backupPath}`);
                        }
                    }
                }
            } else {
                // 非 Turnstile 错误，重置计数
                turnstileFailureCount = 0;
            }

            // V172: 判断是否可重试
            const retryKey = match_id;
            const currentRetries = this.retryCount.get(retryKey) || 0;

            if (FactoryConfig.RETRY.isRetryable(errorType) && currentRetries < FactoryConfig.RETRY.maxAttempts) {
                // 可重试：增加计数并通知 Master
                this.retryCount.set(retryKey, currentRetries + 1);

                const backoffDelay = FactoryConfig.getExponentialBackoff(currentRetries + 1);
                log.warn(`${home_team} vs ${away_team}: ${error.message} (重试 ${currentRetries + 1}/${FactoryConfig.RETRY.maxAttempts}, 等待 ${backoffDelay}ms)`);

                safeSend({
                    type: 'TASK_RETRY',
                    matchId: match_id,
                    error: error.message,
                    retryCount: currentRetries + 1,
                    backoffDelay
                });

            } else {
                // 不可重试：标记为失败
                log.error(`${home_team} vs ${away_team}: ${error.message} (最终失败)`);

                safeSend({
                    type: 'TASK_FAILED',
                    matchId: match_id,
                    error: error.message
                });
            }

            return false;

        } finally {
            // V173: 浏览器资源"绝对释放" (Leak Proof)
            // 1. 关闭当前页面
            if (this.page) {
                try {
                    await this.page.close();
                } catch (e) {
                    log.debug(`关闭 page 失败: ${e.message}`);
                }
                this.page = null;
            }

            // 2. V173: 每次任务后重置 context (防止内存泄漏)
            // 注意：不关闭 browser，保持长连接效率
            if (this.context) {
                try {
                    // 清理所有页面
                    const pages = this.context.pages();
                    for (const p of pages) {
                        try { await p.close(); } catch (e) { /* 忽略 */ }
                    }
                } catch (e) {
                    log.debug(`清理 context 页面失败: ${e.message}`);
                }
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
        // V173: 预清理 - 杀死僵尸进程
        preFlightCleanup();

        await this.init();

        // V173: 信号处理 - 确保手动停止时也能清理浏览器进程
        const gracefulShutdown = async (signal) => {
            log.info(`收到 ${signal} 信号，正在清理资源...`);
            this.running = false;
            await this._forceKillBrowser();
            await this._safeClose();
            process.exit(0);
        };

        process.on('SIGINT', () => gracefulShutdown('SIGINT'));
        process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));

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
                    await this._forceKillBrowser();
                    await this._safeClose();
                    process.exit(0);
                    break;
            }
        });

        // V172: 捕获未处理异常
        process.on('uncaughtException', async (error) => {
            log.error(`未捕获异常: ${error.message}`);
            await this._forceKillBrowser();
            await this._safeClose();
            process.exit(1);
        });

        process.on('unhandledRejection', async (reason) => {
            log.error(`未处理的 Promise 拒绝: ${reason}`);
            await this._forceKillBrowser();
            await this._safeClose();
            process.exit(1);
        });
    }

    /**
     * V173: 强制杀死浏览器进程 (Kill -9 级别)
     * 确保即使手动停止脚本，所有浏览器进程也必须被物理强制杀死
     */
    async _forceKillBrowser() {
        const { execSync } = require('child_process');

        try {
            // 查找当前进程相关的 chrome 进程
            const chromePids = execSync('pgrep -P $$ 2>/dev/null || true', {
                encoding: 'utf8',
                timeout: 2000
            }).trim();

            if (chromePids) {
                const pids = chromePids.split('\n').filter(p => p);
                for (const pid of pids) {
                    try {
                        execSync(`kill -9 ${pid} 2>/dev/null || true`, { timeout: 1000 });
                    } catch (e) {
                        // 忽略
                    }
                }
                log.debug(`已强制清理 ${pids.length} 个子进程`);
            }
        } catch (e) {
            // 忽略清理错误
        }
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
