/**
 * V172-FINAL MatchDetailEngine (生产就绪版)
 * ==========================================
 *
 * 核心功能:
 * - 指纹深度伪装 (navigator.webdriver, Canvas/WebGL 噪声)
 * - 行为模拟 (首页预热, 随机滚动, 鼠标微动)
 * - 网络层配合 (代理池, 随机 Header)
 * - 容错逻辑 (检测 Turnstile, 重试机制)
 *
 * V172 改进:
 * - 使用统一配置中心 (factory_config.js)
 * - 增强重试逻辑 (指数退避)
 * - 连接池 100% 释放保障
 * - 质量门禁标准化
 *
 * @module domain/services/harvesting/MatchDetailEngine
 * @version V172.100 (Production Ready)
 */

'use strict';

const path = require('path');
const fs = require('fs');
const { chromium } = require('playwright');
const { Client } = require('pg');

// ============================================================================
// 配置加载
// ============================================================================

const PROJECT_ROOT = process.env.PROJECT_ROOT || '/app';
const FactoryConfig = require(path.join(PROJECT_ROOT, 'config/factory_config'));
const { DatabaseConfig } = require(path.join(PROJECT_ROOT, 'config/database'));

// ============================================================================
// Logger
// ============================================================================

const log = {
    info: (msg, ...args) => console.log(`[${new Date().toISOString().slice(11, 19)}] ℹ️  ${msg}`, ...args),
    success: (msg, ...args) => console.log(`[${new Date().toISOString().slice(11, 19)}] ✅ ${msg}`, ...args),
    warn: (msg, ...args) => console.log(`[${new Date().toISOString().slice(11, 19)}] ⚠️  ${msg}`, ...args),
    error: (msg, ...args) => console.log(`[${new Date().toISOString().slice(11, 19)}] ❌ ${msg}`, ...args),
    stealth: (msg, ...args) => console.log(`[${new Date().toISOString().slice(11, 19)}] 🕵️ ${msg}`, ...args),
    debug: (msg, ...args) => {
        if (FactoryConfig.LOG_CONFIG.level === 'debug') {
            console.log(`[${new Date().toISOString().slice(11, 19)}] 🔍 ${msg}`, ...args);
        }
    }
};

// ============================================================================
// MatchDetailEngine (生产就绪版)
// ============================================================================

class MatchDetailEngine {
    constructor(options = {}) {
        this.options = {
            enableProxy: options.enableProxy || false,
            proxyPort: options.proxyPort || null,
            proxyServer: options.proxyServer || null,
            headless: options.headless !== false,
            timeout: options.timeout || FactoryConfig.TIMING.pageTimeout
        };

        this._browser = null;
        this._context = null;
        this._client = null;
        this._fingerprint = null;
    }

    // ========================================================================
    // 数据库连接 (带连接池管理)
    // ========================================================================

    async _getClient() {
        if (!this._client || this._client.ended) {
            this._client = new Client({
                host: DatabaseConfig.host,
                port: DatabaseConfig.port,
                database: DatabaseConfig.database,
                user: DatabaseConfig.user,
                password: DatabaseConfig.password,
                connectionTimeoutMillis: FactoryConfig.DATABASE.connectTimeout,
                query_timeout: FactoryConfig.DATABASE.queryTimeout
            });
            await this._client.connect();
        }
        return this._client;
    }

    // ========================================================================
    // V172: 安全资源释放 (100% 闭环)
    // ========================================================================

    async close() {
        const errors = [];

        // 1. 保存浏览器状态
        if (this._context) {
            try {
                const profilePath = FactoryConfig.BROWSER.profilePath;
                const statePath = FactoryConfig.BROWSER.getStatePath();

                if (!fs.existsSync(profilePath)) {
                    fs.mkdirSync(profilePath, { recursive: true });
                }

                const state = await this._context.storageState();
                fs.writeFileSync(statePath, JSON.stringify(state, null, 2));
                log.stealth('浏览器状态已保存');
            } catch (e) {
                errors.push(`state_save: ${e.message}`);
            }

            try {
                await this._context.close();
            } catch (e) {
                errors.push(`context: ${e.message}`);
            }
            this._context = null;
        }

        // 2. 关闭浏览器
        if (this._browser) {
            try {
                await this._browser.close();
            } catch (e) {
                errors.push(`browser: ${e.message}`);
            }
            this._browser = null;
        }

        // 3. 关闭数据库连接
        if (this._client && !this._client.ended) {
            try {
                await this._client.end();
            } catch (e) {
                errors.push(`db: ${e.message}`);
            }
            this._client = null;
        }

        if (errors.length > 0) {
            log.warn(`关闭时有警告: ${errors.join(', ')}`);
        }
    }

    // ========================================================================
    // 指纹生成 (会话镜像优先)
    // ========================================================================

    _generateFingerprint(hasPersistedState = false) {
        let fp;

        if (hasPersistedState && FactoryConfig.FINGERPRINT.static) {
            // 检测到持久化状态，激活静态指纹同步模式
            fp = {
                ...FactoryConfig.FINGERPRINT.static,
                generatedAt: new Date().toISOString(),
                mode: 'STATIC_MIRROR'
            };
            log.stealth('🪞 [L2-Mirror] 检测到持久化状态，已激活静态指纹同步模式');
        } else {
            // 无持久化状态，使用随机指纹
            fp = {
                ...FactoryConfig.randomChoice(FactoryConfig.FINGERPRINT.pool),
                locale: FactoryConfig.randomChoice(FactoryConfig.FINGERPRINT.languages),
                timezoneId: FactoryConfig.randomChoice(FactoryConfig.FINGERPRINT.timezones),
                generatedAt: new Date().toISOString(),
                mode: 'RANDOM'
            };
            log.stealth('🎲 [L2-Random] 无持久化状态，使用随机指纹');
        }

        this._fingerprint = fp;
        return fp;
    }

    // ========================================================================
    // 浏览器初始化 (使用配置中心)
    // ========================================================================

    async _initBrowser() {
        if (this._browser && this._context) {
            return { browser: this._browser, context: this._context };
        }

        // 检查是否有持久化状态
        const statePath = FactoryConfig.BROWSER.getStatePath();
        const hasPersistedState = fs.existsSync(statePath);

        // 生成指纹
        const fp = this._generateFingerprint(hasPersistedState);

        // 代理配置 - 优先级: options > 环境变量
        const proxyServer = this.options.proxyServer
            || process.env.CONTAINER_PROXY
            || process.env.HTTPS_PROXY
            || process.env.HTTP_PROXY;

        // 启动参数 (从配置中心获取)
        const launchOptions = {
            headless: this.options.headless,
            args: FactoryConfig.BROWSER.launchArgs
        };

        // 上下文选项
        const contextOptions = {
            userAgent: fp.userAgent,
            viewport: fp.viewport,
            deviceScaleFactor: fp.deviceScaleFactor,
            locale: fp.locale,
            timezoneId: fp.timezoneId,
            javaScriptEnabled: true,
            ignoreHTTPSErrors: true,
            storageState: undefined
        };

        // 代理配置
        if (proxyServer) {
            contextOptions.proxy = { server: proxyServer };
            log.stealth(`代理: ${proxyServer}`);
        } else if (this.options.enableProxy && this.options.proxyPort) {
            const proxy = FactoryConfig.PROXY_CONFIG.getServer(this.options.proxyPort);
            contextOptions.proxy = { server: proxy };
            log.stealth(`代理: ${proxy}`);
        }

        // 加载持久化状态
        try {
            if (fs.existsSync(statePath)) {
                const stateData = JSON.parse(fs.readFileSync(statePath, 'utf8'));
                contextOptions.storageState = statePath;

                const cookieCount = stateData.cookies ? stateData.cookies.length : 0;
                log.stealth(`✅ 认证状态加载成功 (Cookies: ${cookieCount})`);
            } else {
                log.warn('⚠️  未找到已保存的认证状态');
                log.warn('   请先运行: node scripts/capture_auth.js');
            }
        } catch (e) {
            log.warn(`无法加载浏览器状态: ${e.message}`);
        }

        log.stealth(`User-Agent: ${fp.userAgent}`);

        // 启动浏览器
        this._browser = await chromium.launch(launchOptions);
        this._context = await this._browser.newContext(contextOptions);

        // 注入 Stealth 脚本
        await this._injectStealthScript(fp);

        log.stealth('Stealth 脚本已注入');

        return { browser: this._browser, context: this._context };
    }

    // ========================================================================
    // Stealth 脚本注入
    // ========================================================================

    async _injectStealthScript(fp) {
        const webglConfig = fp.webgl || FactoryConfig.FINGERPRINT.static.webgl;
        const webglVendor = webglConfig?.vendor || 'Google Inc. (NVIDIA)';
        const webglRenderer = webglConfig?.renderer || 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060)';

        await this._context.addInitScript(`
            // 1. 禁用 navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

            // 2. 修改 plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                    { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                    { name: 'Native Client', filename: 'internal-nacl-plugin' }
                ]
            });

            // 3. 修改 languages
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });

            // 4. 硬件并发数伪装
            Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => ${fp.hardwareConcurrency || 8} });

            // 5. 设备内存伪装
            Object.defineProperty(navigator, 'deviceMemory', { get: () => ${fp.deviceMemory || 8} });

            // 6. Canvas 噪声注入
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function(type) {
                if (type === 'image/png' || !type) {
                    const context = this.getContext('2d');
                    if (context) {
                        const imageData = context.getImageData(0, 0, this.width, this.height);
                        for (let i = 0; i < imageData.data.length; i += 4) {
                            imageData.data[i] = Math.max(0, Math.min(255, imageData.data[i] + (Math.random() > 0.5 ? 1 : -1)));
                        }
                        context.putImageData(imageData, 0, 0);
                    }
                }
                return originalToDataURL.apply(this, arguments);
            };

            // 7. WebGL 硬件伪装
            const webglVendor = "${webglVendor}";
            const webglRenderer = "${webglRenderer}";

            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return webglVendor;  // UNMASKED_VENDOR_WEBGL
                if (parameter === 37446) return webglRenderer; // UNMASKED_RENDERER_WEBGL
                return getParameter.apply(this, arguments);
            };

            // 8. WebGL2 伪装
            if (typeof WebGL2RenderingContext !== 'undefined') {
                const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
                WebGL2RenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) return webglVendor;
                    if (parameter === 37446) return webglRenderer;
                    return getParameter2.apply(this, arguments);
                };
            }

            // 9. 屏蔽自动化标志
            window.chrome = { runtime: {} };

            // 10. 权限 API
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        `);
    }

    // ========================================================================
    // 行为模拟 (使用配置中心)
    // ========================================================================

    async _warmupHomepage(page) {
        log.stealth('首页预热: 访问 FotMob 首页...');

        await page.goto('https://www.fotmob.com/', {
            waitUntil: 'domcontentloaded',
            timeout: FactoryConfig.TIMING.apiTimeout
        });

        // 随机停留
        await this._randomDelay(FactoryConfig.TIMING.preVisitDelay);

        // 模拟滚动
        const scrollSteps = FactoryConfig.randomInRange(...FactoryConfig.BEHAVIOR.scrollSteps);
        for (let i = 0; i < scrollSteps; i++) {
            await page.mouse.wheel(0, FactoryConfig.randomInRange(...FactoryConfig.BEHAVIOR.scrollDistance));
            await new Promise(r => setTimeout(r, FactoryConfig.randomInRange(...FactoryConfig.BEHAVIOR.scrollInterval)));
        }

        log.stealth(`首页预热完成 (${scrollSteps} 次滚动)`);
    }

    async _simulateHumanBehavior(page) {
        const moves = FactoryConfig.randomInRange(...FactoryConfig.BEHAVIOR.mouseMoves);

        for (let i = 0; i < moves; i++) {
            const x = FactoryConfig.randomInRange(100, 1800);
            const y = FactoryConfig.randomInRange(100, 900);

            await page.mouse.move(x, y, {
                steps: FactoryConfig.randomInRange(...FactoryConfig.BEHAVIOR.mouseSteps)
            });

            await new Promise(r => setTimeout(r, FactoryConfig.randomInRange(...FactoryConfig.BEHAVIOR.mouseInterval)));
        }

        log.stealth(`模拟 ${moves} 次鼠标移动`);
    }

    async _randomDelay(range) {
        const ms = FactoryConfig.getRandomDelay(range);
        log.stealth(`等待 ${(ms / 1000).toFixed(1)} 秒...`);
        await new Promise(r => setTimeout(r, ms));
    }

    // ========================================================================
    // 错误检测
    // ========================================================================

    _isTurnstileError(data) {
        if (!data) return false;

        const errorIndicators = FactoryConfig.QUALITY_GATE.errorKeywords;
        const str = JSON.stringify(data).toLowerCase();
        return errorIndicators.some(ind => str.includes(ind.toLowerCase()));
    }

    // ========================================================================
    // V172: 获取比赛详情 (增强重试逻辑)
    // ========================================================================

    async fetchMatchDetails(externalId, options = {}) {
        const maxAttempts = options.maxAttempts || FactoryConfig.RETRY.maxAttempts;
        let lastError = null;

        for (let attempt = 1; attempt <= maxAttempts; attempt++) {
            log.info(`\n🕵️ 尝试 ${attempt}/${maxAttempts}: ID=${externalId}`);

            try {
                const result = await this._attemptFetch(externalId, attempt);

                // 检测 Turnstile 错误
                if (this._isTurnstileError(result.data)) {
                    log.warn(`检测到 Turnstile 拦截 (尝试 ${attempt})`);
                    lastError = new Error('TURNSTILE_REQUIRED');

                    if (attempt < maxAttempts) {
                        // V172: 使用指数退避
                        const backoff = FactoryConfig.getExponentialBackoff(attempt);
                        log.stealth(`指数退避: ${backoff}ms`);
                        await new Promise(r => setTimeout(r, backoff));
                        continue;
                    }
                }

                // 成功获取数据
                if (result.data && !this._isTurnstileError(result.data)) {
                    return {
                        success: true,
                        data: result.data,
                        fingerprint: this._fingerprint,
                        attempts: attempt
                    };
                }

            } catch (error) {
                lastError = error;
                log.error(`尝试 ${attempt} 失败: ${error.message}`);

                if (attempt < maxAttempts) {
                    const backoff = FactoryConfig.getExponentialBackoff(attempt);
                    await new Promise(r => setTimeout(r, backoff));
                }
            }
        }

        return {
            success: false,
            error: lastError?.message || 'All attempts failed',
            fingerprint: this._fingerprint
        };
    }

    /**
     * 单次尝试获取
     */
    async _attemptFetch(externalId, attempt) {
        // 每次尝试使用新指纹
        if (attempt > 1) {
            this._fingerprint = null;
            if (this._context) {
                try {
                    await this._context.close();
                } catch (e) {
                    log.debug(`关闭 context 失败: ${e.message}`);
                }
                this._context = null;
            }
        }

        const { context } = await this._initBrowser();
        const page = await context.newPage();

        let capturedData = null;
        const consoleLogs = [];

        // 收集控制台日志
        page.on('console', msg => {
            consoleLogs.push(`[${msg.type()}] ${msg.text()}`);
        });

        // API 拦截
        page.on('response', async (response) => {
            const url = response.url();

            if (url.includes('/api/matchDetails')) {
                try {
                    const data = await response.json();
                    capturedData = data;
                    log.stealth(`🎯 API 拦截成功: ${url.substring(0, 60)}...`);
                } catch (e) {
                    log.warn(`API 解析失败: ${e.message}`);
                }
            }
        });

        try {
            // Step 1: 首页预热 (仅首次尝试)
            if (attempt === 1) {
                await this._warmupHomepage(page);
            }

            // Step 2: 访问比赛详情页
            const matchUrl = `https://www.fotmob.com/matches/-/${externalId}`;
            log.stealth(`访问: ${matchUrl}`);

            // 设置随机 Header
            await page.setExtraHTTPHeaders({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': this._fingerprint.locale,
                'Referer': 'https://www.fotmob.com/',
                'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"'
            });

            await page.goto(matchUrl, {
                waitUntil: 'domcontentloaded',
                timeout: this.options.timeout
            });

            // Step 3: 行为模拟
            await this._simulateHumanBehavior(page);

            // V172: 阅读延时
            const readDelayMs = FactoryConfig.randomInRange(...FactoryConfig.TIMING.readDelay);
            log.stealth(`📖 模拟阅读延时: ${(readDelayMs / 1000).toFixed(1)} 秒`);
            await new Promise(r => setTimeout(r, readDelayMs));

            // Step 4: 等待 API 响应
            await this._randomDelay(FactoryConfig.TIMING.pageDelay);

            // Step 5: 备用方案 - 直接 API 请求
            if (!capturedData || this._isTurnstileError(capturedData)) {
                log.stealth('尝试直接 API 请求...');

                try {
                    const apiResponse = await page.evaluate(async (matchId) => {
                        const res = await fetch(`https://www.fotmob.com/api/matchDetails?matchId=${matchId}`, {
                            headers: {
                                'Accept': 'application/json',
                                'Origin': 'https://www.fotmob.com',
                                'Referer': 'https://www.fotmob.com/'
                            }
                        });
                        return await res.json();
                    }, externalId);

                    if (!this._isTurnstileError(apiResponse)) {
                        capturedData = apiResponse;
                    }
                } catch (e) {
                    log.warn(`直接请求失败: ${e.message}`);
                }
            }

        } finally {
            try {
                await page.close();
            } catch (e) {
                log.debug(`关闭 page 失败: ${e.message}`);
            }
        }

        return { data: capturedData, consoleLogs };
    }

    // ========================================================================
    // 数据解析
    // ========================================================================

    parseMatchData(rawData, homeTeam, awayTeam) {
        const result = {
            xg_home: null,
            xg_away: null,
            possession_home: null,
            possession_away: null,
            shots_home: null,
            shots_away: null,
            shots_on_target_home: null,
            shots_on_target_away: null
        };

        if (!rawData || this._isTurnstileError(rawData)) {
            log.warn('parseMatchData: 数据无效或包含 Turnstile 错误');
            return result;
        }

        try {
            const content = rawData?.content || {};
            const periods = content?.stats?.Periods;
            const allStats = periods?.All?.stats || [];

            log.debug(`统计分组数: ${allStats.length}`);

            // 提取 xG
            const xgGroup = allStats.find(g => {
                const title = (g.title || g.key || '').toLowerCase();
                return title.includes('expected goals') || title.includes('xg');
            });

            if (xgGroup && xgGroup.stats && Array.isArray(xgGroup.stats)) {
                const xgRow = xgGroup.stats.find(s => {
                    const key = (s.key || '').toLowerCase();
                    return key === 'expected_goals' || key.includes('expected_goals');
                });

                if (xgRow && Array.isArray(xgRow.stats) && xgRow.stats.length >= 2) {
                    const homeXg = parseFloat(xgRow.stats[0]);
                    const awayXg = parseFloat(xgRow.stats[1]);

                    if (!isNaN(homeXg) && !isNaN(awayXg)) {
                        result.xg_home = homeXg;
                        result.xg_away = awayXg;
                        log.debug(`xG 提取成功: 主=${homeXg}, 客=${awayXg}`);
                    }
                }
            }

            // 提取控球率
            const topStats = allStats.find(g => {
                const title = (g.title || '').toLowerCase();
                return title.includes('top stats');
            });

            if (topStats && topStats.stats) {
                const possessionRow = topStats.stats.find(s => {
                    const title = (s.title || s.key || '').toLowerCase();
                    return title.includes('ball possession') || title.includes('possession');
                });

                if (possessionRow && Array.isArray(possessionRow.stats) && possessionRow.stats.length >= 2) {
                    result.possession_home = parseInt(possessionRow.stats[0]);
                    result.possession_away = parseInt(possessionRow.stats[1]);
                }
            }

            // 提取射门
            const shotsGroup = allStats.find(g => {
                const title = (g.title || '').toLowerCase();
                return title.includes('shots');
            });

            if (shotsGroup && shotsGroup.stats) {
                const totalShots = shotsGroup.stats.find(s => {
                    const title = (s.title || s.key || '').toLowerCase();
                    return title.includes('total shots') || title === 'shots';
                });

                if (totalShots && Array.isArray(totalShots.stats) && totalShots.stats.length >= 2) {
                    result.shots_home = parseInt(totalShots.stats[0]);
                    result.shots_away = parseInt(totalShots.stats[1]);
                }

                const onTarget = shotsGroup.stats.find(s => {
                    const title = (s.title || s.key || '').toLowerCase();
                    return title.includes('on target');
                });

                if (onTarget && Array.isArray(onTarget.stats) && onTarget.stats.length >= 2) {
                    result.shots_on_target_home = parseInt(onTarget.stats[0]);
                    result.shots_on_target_away = parseInt(onTarget.stats[1]);
                }
            }

        } catch (error) {
            log.warn(`解析失败: ${error.message}`);
        }

        // NaN 容错
        const validateNumber = (value) => {
            if (value === null || value === undefined) return null;
            if (typeof value === 'string') {
                const parsed = parseFloat(value);
                return isNaN(parsed) ? null : parsed;
            }
            if (typeof value === 'number') {
                return isNaN(value) ? null : value;
            }
            return null;
        };

        result.xg_home = validateNumber(result.xg_home);
        result.xg_away = validateNumber(result.xg_away);
        result.possession_home = validateNumber(result.possession_home);
        result.possession_away = validateNumber(result.possession_away);
        result.shots_home = validateNumber(result.shots_home);
        result.shots_away = validateNumber(result.shots_away);

        return result;
    }

    // ========================================================================
    // V172: 数据存储 (使用配置中心质量门禁)
    // ========================================================================

    async storeMatchDetails(matchId, rawData, parsedData) {
        const client = await this._getClient();

        // V172: 使用配置中心的质量门禁
        const validation = FactoryConfig.QUALITY_GATE.isValid(rawData);

        if (!validation.valid) {
            log.error(`🚫 质量门禁拦截: ${validation.reason} (size: ${validation.size || 'N/A'})`);
            return {
                stored: false,
                reason: validation.reason,
                rawSize: validation.size
            };
        }

        log.stealth(`✅ 质量门禁通过: ${validation.size} bytes`);

        // 存储原始 JSON
        const rawQuery = `
            INSERT INTO raw_match_data (match_id, raw_data, collected_at)
            VALUES ($1, $2::jsonb, NOW())
            ON CONFLICT (match_id) DO UPDATE SET
                raw_data = EXCLUDED.raw_data,
                collected_at = NOW()
        `;

        await client.query(rawQuery, [matchId, JSON.stringify(rawData)]);

        // 更新解析字段
        const updateQuery = `
            UPDATE matches SET
                xg_home = $2,
                xg_away = $3,
                updated_at = NOW()
            WHERE match_id = $1
        `;

        await client.query(updateQuery, [matchId, parsedData.xg_home, parsedData.xg_away]);

        // 存储到 metrics 表
        try {
            const metricsQuery = `
                INSERT INTO metrics_multi_source_data (match_id, source, metric_type, metric_value, collected_at)
                VALUES ($1, 'FotMob', 'l2_stats', $2::jsonb, NOW())
                ON CONFLICT (match_id, source, metric_type) DO UPDATE SET
                    metric_value = EXCLUDED.metric_value,
                    collected_at = NOW()
            `;

            const metricsValue = {
                xg_home: parsedData.xg_home,
                xg_away: parsedData.xg_away,
                possession_home: parsedData.possession_home,
                possession_away: parsedData.possession_away,
                shots_home: parsedData.shots_home,
                shots_away: parsedData.shots_away,
                shots_on_target_home: parsedData.shots_on_target_home,
                shots_on_target_away: parsedData.shots_on_target_away
            };

            await client.query(metricsQuery, [matchId, JSON.stringify(metricsValue)]);
        } catch (e) {
            log.warn(`存储 metrics 失败: ${e.message}`);
        }

        log.success(`数据已存储: xG=${parsedData.xg_home}/${parsedData.xg_away}`);

        return { stored: true, rawSize: validation.size };
    }

    // ========================================================================
    // 完整采集流程
    // ========================================================================

    async harvestMatch(matchInfo) {
        const { match_id, external_id, home_team, away_team } = matchInfo;

        log.info(`\n${'═'.repeat(60)}`);
        log.info(`开始采集: ${home_team} vs ${away_team}`);
        log.info(`ID: ${external_id}`);
        log.info('═'.repeat(60));

        try {
            // Step 1: 获取原始数据 (带重试)
            const fetchResult = await this.fetchMatchDetails(external_id);

            if (!fetchResult.success) {
                return {
                    success: false,
                    match_id,
                    error: fetchResult.error,
                    fingerprint: fetchResult.fingerprint
                };
            }

            const rawData = fetchResult.data;

            // Step 2: 解析数据
            const parsedData = this.parseMatchData(rawData, home_team, away_team);

            log.info(`解析结果:`);
            log.info(`  xG: ${parsedData.xg_home} - ${parsedData.xg_away}`);
            log.info(`  控球: ${parsedData.possession_home}% - ${parsedData.possession_away}%`);
            log.info(`  射门: ${parsedData.shots_home} - ${parsedData.shots_away}`);

            // Step 3: 存储数据
            const storeResult = await this.storeMatchDetails(match_id, rawData, parsedData);

            // Cookie 续期
            if (storeResult.stored && this._context) {
                try {
                    const profilePath = FactoryConfig.BROWSER.profilePath;
                    const statePath = FactoryConfig.BROWSER.getStatePath();

                    if (!fs.existsSync(profilePath)) {
                        fs.mkdirSync(profilePath, { recursive: true });
                    }

                    const state = await this._context.storageState();
                    fs.writeFileSync(statePath, JSON.stringify(state, null, 2));
                    log.stealth('🔄 Cookie 已续期');
                } catch (e) {
                    log.warn(`Cookie 续期失败: ${e.message}`);
                }
            }

            return {
                success: storeResult.stored,
                match_id,
                data: parsedData,
                fingerprint: fetchResult.fingerprint,
                attempts: fetchResult.attempts,
                rawSize: storeResult.rawSize
            };

        } catch (error) {
            log.error(`采集失败: ${error.message}`);
            return {
                success: false,
                match_id,
                error: error.message
            };
        }
    }

    // ========================================================================
    // 指纹摘要
    // ========================================================================

    getFingerprintSummary() {
        if (!this._fingerprint) return null;

        return {
            userAgent: this._fingerprint.userAgent.substring(0, 50) + '...',
            viewport: `${this._fingerprint.viewport.width}x${this._fingerprint.viewport.height}`,
            locale: this._fingerprint.locale,
            timezone: this._fingerprint.timezoneId,
            platform: this._fingerprint.platform
        };
    }
}

// ============================================================================
// 导出
// ============================================================================

module.exports = {
    MatchDetailEngine,
    FactoryConfig
};
