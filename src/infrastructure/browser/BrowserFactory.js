/**
 * BrowserFactory - 浏览器工厂
 * ===========================
 *
 * 统一管理浏览器生命周期、Context 创建、隐身脚本注入和行为模拟。
 * 从 AbstractHarvester 剥离的工业级组件。
 * @module infrastructure/browser/BrowserFactory
 * @version V1.0.0
 */

'use strict';

const path = require('path');

const { chromium } = require('playwright');
const { getPathResolver } = require('../utils/PathResolver');
const { logger } = require('../utils/Logger');
const { mergeContextExtraHTTPHeaders } = require('../shared/helpers/browserHeaderUtils');

const DEFAULT_BLOCKED_RESOURCE_TYPES = ['image', 'stylesheet', 'font', 'media'];

function resolveBooleanFlag(explicitValue, envValue, defaultValue) {
    if (typeof explicitValue === 'boolean') {
        return explicitValue;
    }

    if (typeof envValue === 'string' && envValue.trim() !== '') {
        return envValue.trim().toLowerCase() !== 'false';
    }

    return defaultValue;
}

function parseBlockedResourceTypes(value) {
    if (Array.isArray(value) && value.length > 0) {
        return new Set(value.map(type => String(type).trim()).filter(Boolean));
    }

    if (typeof value === 'string' && value.trim() !== '') {
        return new Set(
            value
                .split(',')
                .map(type => type.trim())
                .filter(Boolean)
        );
    }

    return new Set(DEFAULT_BLOCKED_RESOURCE_TYPES);
}

function normalizeProxyProtocol(value) {
    const normalized = String(value || '').trim().toLowerCase();
    if (normalized === 'socks5h') {
        return 'socks5';
    }
    return normalized || 'socks5';
}

// ============================================================================
// BrowserFactory - 浏览器工厂类
// ============================================================================

/**
 *
 */
class BrowserFactory {
    /**
     * 创建 BrowserFactory 实例
     * @param {object} [config] - 配置选项
     * @param {boolean} [config.headless] - 是否无头模式
     * @param {string} [config.profilePath] - 浏览器配置文件路径
     */
    constructor(config = {}) {
        this.config = {
            headless: config.headless !== false,
            profilePath: config.profilePath || process.env.BROWSER_PROFILE_PATH || '/app/data/browser_profile',
            disableHomepageWarmup: true,
            ...config
        };
        this.config.blockResources = resolveBooleanFlag(
            this.config.blockResources,
            process.env.PLAYWRIGHT_BLOCK_RESOURCES,
            true
        );
        this.config.enableRemoteDnsHardening = resolveBooleanFlag(
            this.config.enableRemoteDnsHardening,
            process.env.PLAYWRIGHT_REMOTE_DNS_HARDENING,
            true
        );
        this.config.blockedResourceTypes = parseBlockedResourceTypes(
            this.config.blockedResourceTypes || process.env.PLAYWRIGHT_BLOCK_RESOURCE_TYPES
        );

        this.browser = null;
        this.contextSlimmingStats = new WeakMap();
    }

    // ========================================================================
    // 浏览器生命周期
    // ========================================================================

    /**
     * 启动浏览器
     * @returns {Promise<import('playwright').Browser>}
     */
    async launch() {
        if (this.browser) {
            return this.browser;
        }

        console.log('🚀 [BrowserFactory] 启动浏览器...');

        const launchArgs = [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-blink-features=AutomationControlled',
            '--disable-gpu',
            '--disable-background-networking',
            '--disable-component-update',
            '--disable-default-apps',
            '--disable-extensions',
            '--disable-sync',
            '--mute-audio',
            '--no-default-browser-check',
            '--no-first-run'
        ];
        // Chromium 对 SOCKSv5 已采用代理端解析域名；额外的 host-resolver-rules
        // 会在 Docker Desktop 网络栈中直接导致 ERR_PROXY_CONNECTION_FAILED。

        this.browser = await chromium.launch({
            headless: this.config.headless,
            args: launchArgs
        });

        console.log('✅ [BrowserFactory] 浏览器已启动');
        return this.browser;
    }

    /**
     * 关闭浏览器
     */
    async close() {
        if (this.browser) {
            try {
                await this.browser.close();
                console.log('✅ [BrowserFactory] 浏览器已关闭');
            } catch (err) {
                logger.warn('浏览器关闭失败', { error: err.message });
            }
            this.browser = null;
        }
    }

    /**
     * 获取浏览器实例
     * @returns {import('playwright').Browser|null}
     */
    getBrowser() {
        return this.browser;
    }

    // ========================================================================
    // Context 创建
    // ========================================================================

    /**
     * 创建浏览器上下文
     * @param {object} identity - Worker 身份信息
     * @param {object} identity.proxy - 代理配置
     * @param {object} identity.stealth - 隐身配置
     * @param {boolean} [disableProxy] - 是否禁用代理
     * @returns {Promise<import('playwright').BrowserContext>}
     */
    async createContext(identity, disableProxy = false) {
        if (!this.browser) {
            throw new Error('浏览器未启动，请先调用 launch()');
        }

        const proxyConfig = this._buildContextProxyConfig(identity, disableProxy);
        const contextOptions = this._buildContextOptions(identity, proxyConfig);
        const context = await this.browser.newContext(contextOptions);

        await this._enableResourceSlimming(context);

        return context;
    }

    _buildContextProxyConfig(identity, disableProxy) {
        if (disableProxy || process.env.DISABLE_PROXY === 'true') {
            return undefined;
        }

        const proxyProtocol = normalizeProxyProtocol(process.env.PROXY_PROTOCOL || 'socks5');
        const proxyUrl = identity.proxy.url.startsWith('socks5') || identity.proxy.url.startsWith('http')
            ? identity.proxy.url.replace(/^socks5h:\/\//i, 'socks5://')
            : `${proxyProtocol}://${identity.proxy.host}:${identity.proxy.port}`;

        return { server: proxyUrl };
    }

    _buildContextOptions(identity, proxyConfig) {
        const extraHTTPHeaders = mergeContextExtraHTTPHeaders({
            extraHeaders: identity.stealth.extraHTTPHeaders || {},
            userAgent: identity.stealth.userAgent,
            acceptLanguage: this._resolveAcceptLanguage(identity.stealth),
            platform: identity.stealth.platform || 'Win32'
        });

        return {
            viewport: identity.stealth.viewport,
            userAgent: identity.stealth.userAgent,
            extraHTTPHeaders,
            proxy: proxyConfig,
            deviceScaleFactor: identity.stealth.deviceScaleFactor || 1,
            locale: identity.stealth.locale || 'en-US',
            timezoneId: identity.stealth.timezoneId || 'Europe/London',
            serviceWorkers: this.config.blockResources ? 'block' : 'allow'
        };
    }

    _resolveAcceptLanguage(stealthConfig = {}) {
        if (stealthConfig.locale === 'en-US') {
            return 'en-US,en;q=0.9';
        }

        return stealthConfig.extraHTTPHeaders?.['accept-language']
            || stealthConfig.extraHTTPHeaders?.['Accept-Language']
            || 'en-US,en;q=0.9';
    }

    _buildStableStealthProfile(stealthConfig = {}) {
        const locale = typeof stealthConfig.locale === 'string' && stealthConfig.locale.trim()
            ? stealthConfig.locale.trim()
            : 'en-US';
        const platform = typeof stealthConfig.platform === 'string' && stealthConfig.platform.trim()
            ? stealthConfig.platform.trim()
            : 'Win32';
        const normalizedLanguages = Array.isArray(stealthConfig.languages) && stealthConfig.languages.length > 0
            ? stealthConfig.languages.map(value => String(value).trim()).filter(Boolean)
            : [locale, 'en'].filter((value, index, source) => source.indexOf(value) === index);
        const hardwareConcurrency = Number.isFinite(Number(stealthConfig.hardwareConcurrency))
            ? Math.max(1, Math.round(Number(stealthConfig.hardwareConcurrency)))
            : 8;
        const deviceMemory = Number.isFinite(Number(stealthConfig.deviceMemory))
            ? Math.max(1, Math.round(Number(stealthConfig.deviceMemory)))
            : 8;
        const webgl = {
            vendor: stealthConfig.webgl?.vendor || 'Google Inc. (NVIDIA)',
            renderer: stealthConfig.webgl?.renderer || 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)'
        };

        return {
            platform,
            languages: normalizedLanguages.length > 0 ? normalizedLanguages : ['en-US', 'en'],
            hardwareConcurrency,
            deviceMemory,
            webgl
        };
    }

    // ========================================================================
    // 隐身脚本注入
    // ========================================================================

    /**
     * 注入原生隐身脚本
     * V4.46.1: 修复 platform 与 UA 不一致导致的指纹泄露
     * @param {import('playwright').Page} page - Playwright 页面对象
     */
    async injectStealthScripts(page, identity = null) {
        const stableFingerprint = this._buildStableStealthProfile(identity?.stealth || {});

        await page.addInitScript((fingerprint) => {
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
                get: () => fingerprint.platform,
                configurable: true
            });

            // 【关键修复】模拟语言 - 包含 q 值权重
            Object.defineProperty(navigator, 'languages', {
                get: () => fingerprint.languages,
                configurable: true
            });

            // 绑定稳定硬件并发，避免同一身份在每次页面加载时漂移
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => fingerprint.hardwareConcurrency,
                configurable: true
            });

            // 绑定稳定设备内存
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => fingerprint.deviceMemory,
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
            // WebGL 指纹伪装 - 复用稳定渲染器，避免每次页面初始化漂移
            // ═══════════════════════════════════════════════════════════════
            const selectedRenderer = fingerprint.webgl;

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

        }, stableFingerprint);
    }

    // ========================================================================
    // 行为模拟
    // ========================================================================

    /**
     * 首页预热 - 建立 Session 信任
     * @param {import('playwright').Page} page - Playwright Page 对象
     * @param {object} [config] - 预热配置
     * @param {boolean} [config.scrollMore] - 是否滚动更多
     * @param {boolean} [config.randomScrolls] - 是否随机滚动
     */
    async warmupHomepage(page, config = {}) {
        const warmupDisabled = this.config.disableHomepageWarmup !== false;

        if (warmupDisabled) {
            console.log('⏭️  [BrowserFactory] 首页预热已停用，直接进入目标详情页');
            return {
                skipped: true,
                pageAttached: Boolean(page),
                hasConfig: Boolean(config && Object.keys(config).length > 0)
            };
        }

        console.log('🏠 [BrowserFactory] 首页预热: 访问 FotMob 首页...');

        await page.goto('https://www.fotmob.com/', { waitUntil: 'domcontentloaded' });

        // 随机停留 3-6 秒
        await this._delay(this._randomInRange(3000, 6000));

        // 3-5 次随机滚动
        const scrollCount = this._randomInRange(3, 5);
        for (let i = 0; i < scrollCount; i++) {
            await page.mouse.wheel(0, this._randomInRange(100, 300));
            await this._delay(this._randomInRange(500, 1500));
        }

        console.log(`✅ [BrowserFactory] 首页预热完成 (${scrollCount} 次滚动)`);
        return {
            skipped: false,
            scrollCount
        };
    }

    /**
     * 人类行为模拟
     * @param {import('playwright').Page} page - Playwright Page 对象
     */
    async simulateHumanBehavior(page) {
        const moves = this._randomInRange(10, 15);

        for (let i = 0; i < moves; i++) {
            await page.mouse.move(
                this._randomInRange(100, 1800),
                this._randomInRange(100, 900),
                { steps: this._randomInRange(5, 15) }
            );
            await this._delay(this._randomInRange(200, 800));
        }

        console.log(`🎭 [BrowserFactory] 行为模拟完成 (${moves} 次鼠标移动)`);
    }

    /**
     * 简化版鼠标移动（收割时使用）
     * @param {import('playwright').Page} page - Playwright Page 对象
     * @param {number} [minMoves] - 最小移动次数
     * @param {number} [maxMoves] - 最大移动次数
     */
    async quickMouseMove(page, minMoves = 3, maxMoves = 5) {
        const moves = this._randomInRange(minMoves, maxMoves);
        for (let i = 0; i < moves; i++) {
            await page.mouse.move(
                this._randomInRange(100, 1800),
                this._randomInRange(100, 900),
                { steps: 5 }
            );
            await this._delay(100);
        }
    }

    // ========================================================================
    // Cookie 管理
    // ========================================================================

    /**
     * 从 browser_state.json 加载 Cookie
     * @param {import('playwright').BrowserContext} context - Playwright 上下文
     * @returns {Promise<boolean>} 是否成功加载
     */
    async loadBrowserStateCookies(context) {
        const fs = require('fs').promises;
        const pathResolver = getPathResolver();
        const statePath = pathResolver.getBrowserStatePath();
        const sessionPath = path.join(process.cwd(), 'data', 'sessions', 'fotmob_session.json');
        const candidatePaths = [statePath, sessionPath];

        for (const candidatePath of candidatePaths) {
            try {
                const content = await fs.readFile(candidatePath, 'utf8');
                const state = JSON.parse(content);
                const rawCookies = Array.isArray(state)
                    ? state
                    : Array.isArray(state?.cookies)
                        ? state.cookies
                        : [];
                const validCookies = rawCookies
                    .map((cookie) => this._normalizeContextCookie(cookie))
                    .filter(Boolean);

                if (validCookies.length > 0) {
                    await context.addCookies(validCookies);
                    console.log(`🔑 [BrowserFactory] 浏览器身份加载成功: ${validCookies.length} 个 Cookie | source=${candidatePath}`);
                    return true;
                }
            } catch (error) {
                // 继续检查下一个候选路径
            }
        }

        return false;
    }

    getResourceSlimmingStats(context) {
        const stats = this.contextSlimmingStats.get(context);
        if (!stats) {
            return {
                enabled: false,
                blockedTotal: 0,
                continuedTotal: 0,
                blockedByType: {}
            };
        }

        return {
            enabled: stats.enabled,
            blockedTotal: stats.blockedTotal,
            continuedTotal: stats.continuedTotal,
            blockedByType: { ...stats.blockedByType }
        };
    }

    async _enableResourceSlimming(context) {
        const blockedByType = {};
        for (const resourceType of this.config.blockedResourceTypes) {
            blockedByType[resourceType] = 0;
        }

        const stats = {
            enabled: this.config.blockResources,
            blockedTotal: 0,
            continuedTotal: 0,
            blockedByType
        };
        this.contextSlimmingStats.set(context, stats);

        if (!this.config.blockResources) {
            return;
        }

        if (!context || typeof context.route !== 'function') {
            return;
        }

        await context.route('**/*', async (route) => {
            const resourceType = route.request().resourceType();

            try {
                if (this.config.blockedResourceTypes.has(resourceType)) {
                    stats.blockedTotal++;
                    stats.blockedByType[resourceType] = (stats.blockedByType[resourceType] || 0) + 1;
                    await route.abort('blockedbyclient');
                    return;
                }

                stats.continuedTotal++;
                await route.continue();
            } catch (error) {
                if (!this._isIgnorableRouteError(error)) {
                    throw error;
                }
            }
        });
    }

    _isIgnorableRouteError(error) {
        const message = String(error?.message || '').toLowerCase();
        return message.includes('target closed')
            || message.includes('page closed')
            || message.includes('context closed')
            || message.includes('route is already handled');
    }

    _normalizeContextCookie(cookie = {}) {
        const expires = Number(cookie?.expires ?? cookie?.expirationDate);
        const normalized = {
            name: String(cookie?.name || '').trim(),
            value: String(cookie?.value || '').trim(),
            domain: String(cookie?.domain || '').trim(),
            path: String(cookie?.path || '/'),
            httpOnly: Boolean(cookie?.httpOnly),
            secure: Boolean(cookie?.secure)
        };

        if (!normalized.name || !normalized.value || !normalized.domain) {
            return null;
        }

        if (Number.isFinite(expires) && expires > 0) {
            if (expires < Date.now() / 1000) {
                return null;
            }
            normalized.expires = expires;
        }

        const sameSite = this._normalizeCookieSameSite(cookie?.sameSite);
        if (sameSite) {
            normalized.sameSite = sameSite;
        }

        return normalized;
    }

    _normalizeCookieSameSite(rawValue) {
        const sameSite = String(rawValue || '').trim().toLowerCase();
        if (sameSite === 'no_restriction' || sameSite === 'none') {
            return 'None';
        }
        if (sameSite === 'lax') {
            return 'Lax';
        }
        if (sameSite === 'strict') {
            return 'Strict';
        }
        return undefined;
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
}

// ============================================================================
// 单例模式
// ============================================================================

let _instance = null;

/**
 * 获取 BrowserFactory 单例
 * @param {object} [config] - 配置选项
 * @returns {BrowserFactory}
 */
function getBrowserFactory(config = {}) {
    if (!_instance) {
        _instance = new BrowserFactory(config);
    }
    return _instance;
}

/**
 * 重置单例（用于测试）
 */
function resetBrowserFactory() {
    _instance = null;
}

module.exports = {
    BrowserFactory,
    getBrowserFactory,
    resetBrowserFactory
};
