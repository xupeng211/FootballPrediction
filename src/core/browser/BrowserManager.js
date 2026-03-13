/**
 * BrowserManager - 浏览器生命周期管理器
 * ==============================================
 *
 * 负责 Playwright 浏览器的完整生命周期管理
 * - 浏览器启动和配置
 * - 上下文创建和 Cookie 管理
 * - 资源释放和进程清理
 * - V175: ResourceShield 极致加速 (屏蔽非必要资源)
 * @module core/browser/BrowserManager
 * @version V175.0.0
 */

'use strict';

const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');
const { StealthInjector } = require('./StealthInjector');

// ============================================================================
// ResourceShield - 资源屏蔽器 (V175 极致加速)
// ============================================================================

/**
 * ResourceShield - 资源屏蔽器
 *
 * 屏蔽非必要资源，加速页面加载：
 * - image: 图片
 * - stylesheet: CSS
 * - font: 字体
 * - media: 音视频
 * - 第三方 API (非 matchDetails)
 */
class ResourceShield {
    /**
     * @param {object} options - 配置选项
     * @param {string[]} options.blockedTypes - 要屏蔽的资源类型
     * @param {string[]} options.allowedPatterns - 允许的 URL 模式
     */
    constructor(options = {}) {
        this.blockedTypes = options.blockedTypes || ['image', 'stylesheet', 'font', 'media'];
        this.allowedPatterns = options.allowedPatterns || [
            'matchDetails',
            'fotmob.com/api',
            'fotmob.com/_next/',
        ];

        this.stats = {
            totalBlocked: 0,
            byType: {}
        };

        this.silent = options.silent ?? true;
    }

    /**
     * 检查 URL 是否应该放行
     * @private
     * @param {string} url - 请求 URL
     * @returns {boolean}
     */
    _isAllowed(url) {
        return this.allowedPatterns.some(pattern => url.includes(pattern));
    }

    /**
     * 设置页面路由拦截
     * @param {import('playwright').Page} page - Playwright 页面对象
     */
    async setup(page) {
        await page.route('**/*', async (route) => {
            const request = route.request();
            const url = request.url();
            const resourceType = request.resourceType();

            // 如果是允许的 URL，直接放行
            if (this._isAllowed(url)) {
                await route.continue();
                return;
            }

            // 检查是否需要屏蔽
            if (this.blockedTypes.includes(resourceType)) {
                this.stats.totalBlocked++;
                this.stats.byType[resourceType] = (this.stats.byType[resourceType] || 0) + 1;

                if (!this.silent) {
                    console.log(`🛡️ [ResourceShield] 屏蔽: ${resourceType} - ${url.substring(0, 60)}...`);
                }

                await route.abort();
                return;
            }

            // 其他请求放行
            await route.continue();
        });

        if (!this.silent) {
            console.log(`🛡️ [ResourceShield] 已激活 - 屏蔽类型: ${this.blockedTypes.join(', ')}`);
        }
    }

    /**
     * 获取统计信息
     * @returns {object}
     */
    getStats() {
        return { ...this.stats };
    }
}

/**
 * BrowserManager - 浏览器生命周期管理器
 */
class BrowserManager {
    /**
     * @param {object} options - 配置选项
     * @param {number} options.workerId - Worker 标识符
     * @param {number} options.proxyPort - 代理端口
     * @param {boolean} options.headless - 无头模式
     * @param {object} options.config - 工厂配置 (FactoryConfig)
     * @param {boolean} options.enableResourceShield - 启用资源屏蔽 (V175)
     */
    constructor(options = {}) {
        this.workerId = options.workerId ?? 1;
        this.proxyPort = options.proxyPort ?? 7890;
        this.headless = options.headless ?? true;
        this.config = options.config ?? {};

        // 浏览器实例
        this.browser = null;
        this.context = null;
        this.page = null;

        // 状态跟踪
        this.currentProxyPort = this.proxyPort;
        this.userDataDir = `/tmp/browser_profile_worker_${this.workerId}`;

        // Stealth 注入器
        this.stealthInjector = new StealthInjector({ silent: options.silent ?? true });

        // V175: ResourceShield 资源屏蔽器
        this.enableResourceShield = options.enableResourceShield ?? true;
        this.resourceShield = null;

        // 静默模式
        this.silent = options.silent ?? false;
    }

    /**
     * 日志输出
     * @param level
     * @param msg
     * @private
     */
    _log(level, msg) {
        if (this.silent) return;
        const timestamp = new Date().toISOString().slice(0, 19).replace('T', ' ');
        const prefix = `[W${this.workerId}] [Browser]`;
        console.log(`${timestamp} ${prefix} [${level.toUpperCase()}] ${msg}`);
    }

    /**
     * 获取代理服务器地址
     * @returns {string}
     */
    getProxyServer() {
        if (this.config?.PROXY_CONFIG?.getServer) {
            return this.config.PROXY_CONFIG.getServer(this.currentProxyPort);
        }
        return `http://172.25.16.1:${this.currentProxyPort}`;
    }

    /**
     * 获取随机 User-Agent
     * @returns {string}
     */
    getRandomUA() {
        if (this.config?.FINGERPRINT?.getRandomUA) {
            return this.config.FINGERPRINT.getRandomUA();
        }
        return 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36';
    }

    /**
     * 获取随机视口
     * @returns {object}
     */
    getRandomViewport() {
        if (this.config?.FINGERPRINT?.getRandomViewport) {
            return this.config.FINGERPRINT.getRandomViewport();
        }
        return { width: 1920, height: 1080 };
    }

    /**
     * 获取静态指纹配置
     * @returns {object}
     */
    getStaticFingerprint() {
        return this.config?.FINGERPRINT?.static ?? {
            locale: 'zh-CN',
            timezoneId: 'Asia/Shanghai'
        };
    }

    /**
     * 获取启动参数
     * @returns {string[]}
     */
    getLaunchArgs() {
        const baseArgs = this.config?.BROWSER?.launchArgs ?? [];

        // 资源压制参数
        const resourceCappingArgs = [
            '--js-flags=--max-old-space-size=256',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-software-rasterizer',
            '--disable-background-networking',
            '--disable-extensions',
            '--disable-plugins'
        ];

        return [...baseArgs, ...resourceCappingArgs];
    }

    /**
     * 确保用户数据目录存在
     * @private
     */
    _ensureUserDataDir() {
        if (!fs.existsSync(this.userDataDir)) {
            fs.mkdirSync(this.userDataDir, { recursive: true });
        }
    }

    /**
     * 检查 Cookie 是否过期
     * @param {string} statePath - 状态文件路径
     * @returns {{ valid: boolean, reason?: string }}
     */
    checkCookieExpiry(statePath) {
        if (!fs.existsSync(statePath)) {
            return { valid: false, reason: 'NOT_FOUND' };
        }

        try {
            const stateContent = fs.readFileSync(statePath, 'utf8');
            const state = JSON.parse(stateContent);
            const cookieMaxAge = this.config?.SENTINEL_CONFIG?.cookieMaxAgeMs ?? (24 * 60 * 60 * 1000);
            const stateStat = fs.statSync(statePath);
            const fileAge = Date.now() - stateStat.mtimeMs;

            if (fileAge > cookieMaxAge) {
                return {
                    valid: false,
                    reason: 'EXPIRED',
                    age: Math.round(fileAge / 3600000)
                };
            }

            return { valid: true, age: Math.round(fileAge / 60000) };

        } catch (e) {
            return { valid: false, reason: 'PARSE_ERROR', error: e.message };
        }
    }

    /**
     * 确保浏览器已启动
     * @returns {Promise<{ browser, context, page }>}
     */
    async ensureBrowser() {
        this._ensureUserDataDir();

        // 1. 启动浏览器
        if (!this.browser) {
            const proxyServer = this.getProxyServer();

            this.browser = await chromium.launch({
                headless: this.headless,
                proxy: { server: proxyServer },
                args: this.getLaunchArgs()
            });

            this._log('info', `浏览器已启动 (Port: ${proxyServer})`);
        }

        // 2. 创建上下文
        if (!this.context) {
            const randomViewport = this.getRandomViewport();
            const dynamicUA = this.getRandomUA();
            const staticFingerprint = this.getStaticFingerprint();

            const contextOptions = {
                userAgent: dynamicUA,
                viewport: randomViewport,
                locale: staticFingerprint.locale,
                timezoneId: staticFingerprint.timezoneId,
                ignoreHTTPSErrors: true
            };

            // 检查 Cookie 状态
            const statePath = `${this.userDataDir}/browser_state.json`;
            const cookieCheck = this.checkCookieExpiry(statePath);

            if (cookieCheck.valid) {
                contextOptions.storageState = statePath;
                this._log('debug', `已加载浏览器状态 (${cookieCheck.age} 分钟前)`);
            } else if (cookieCheck.reason === 'EXPIRED') {
                this._log('warn', `Cookie 已过期 (${cookieCheck.age} 小时)，将使用全新身份`);
                // 备份旧 Cookie
                const backupPath = `${statePath}.expired.${Date.now()}`;
                fs.renameSync(statePath, backupPath);
            } else if (cookieCheck.reason === 'PARSE_ERROR') {
                this._log('warn', `Cookie 解析失败: ${cookieCheck.error}，将使用全新身份`);
                fs.unlinkSync(statePath);
            }

            this.context = await this.browser.newContext(contextOptions);

            // 注入 Stealth 脚本
            await this.stealthInjector.inject(this.context);

            this._log('info', `Context 已创建 (Viewport: ${randomViewport.width}x${randomViewport.height})`);
        }

        return {
            browser: this.browser,
            context: this.context
        };
    }

    /**
     * 创建新页面
     * @param {object} options - 页面选项
     * @param {boolean} options.enableResourceShield - 是否启用资源屏蔽 (默认使用实例设置)
     * @returns {Promise<import('playwright').Page>}
     */
    async newPage(options = {}) {
        await this.ensureBrowser();
        this.page = await this.context.newPage();

        // V175: 设置资源屏蔽
        const shouldEnableShield = options.enableResourceShield ?? this.enableResourceShield;
        if (shouldEnableShield) {
            this.resourceShield = new ResourceShield({ silent: this.silent });
            await this.resourceShield.setup(this.page);
            this._log('debug', 'ResourceShield 已激活');
        }

        return this.page;
    }

    /**
     * 关闭当前页面 (V175: 轻量级，保留 Browser)
     * 只关闭 page，不关闭 browser 和 context
     */
    async closePage() {
        if (this.page) {
            try {
                await this.page.close();
            } catch (e) {
                this._log('debug', `关闭 page 失败: ${e.message}`);
            }
            this.page = null;
        }
    }

    /**
     * V175: 重置 Context (中等重量级)
     * 关闭 page 和 context，但保留 browser
     * 用于切换代理或遇到严重错误时
     */
    async resetContext() {
        // 1. 关闭页面
        await this.closePage();

        // 2. 关闭上下文
        if (this.context) {
            try {
                await this.context.close();
            } catch (e) {
                this._log('debug', `关闭 context 失败: ${e.message}`);
            }
            this.context = null;
        }

        this._log('info', 'Context 已重置 (Browser 保留)');
    }

    /**
     * V175: 检查 Browser 是否健康
     * @returns {boolean}
     */
    isBrowserHealthy() {
        if (!this.browser) return false;

        try {
            // 尝试获取浏览器版本，检查是否存活
            return this.browser.isConnected();
        } catch (e) {
            return false;
        }
    }

    /**
     * V175: 确保 Browser 可用
     * 如果 browser 不健康，重新启动
     * @returns {Promise<boolean>}
     */
    async ensureBrowserHealthy() {
        if (this.isBrowserHealthy()) {
            return true;
        }

        this._log('warn', 'Browser 不健康，正在重启...');

        // 清理旧实例
        await this.safeClose();

        // 重新启动
        await this.ensureBrowser();
        return this.isBrowserHealthy();
    }

    /**
     * V175: 获取任务级页面 (复用模式)
     * Worker 进程持有长连接 Browser，每次任务只创建新 page
     * @param {object} options - 页面选项
     * @returns {Promise<import('playwright').Page>}
     */
    async getTaskPage(options = {}) {
        // 确保 browser 健康
        await this.ensureBrowserHealthy();

        // 如果没有 context，创建一个
        if (!this.context) {
            const randomViewport = this.getRandomViewport();
            const dynamicUA = this.getRandomUA();
            const staticFingerprint = this.getStaticFingerprint();

            this.context = await this.browser.newContext({
                userAgent: dynamicUA,
                viewport: randomViewport,
                locale: staticFingerprint.locale,
                timezoneId: staticFingerprint.timezoneId,
                ignoreHTTPSErrors: true
            });

            await this.stealthInjector.inject(this.context);
            this._log('debug', `新 Context 已创建`);
        }

        // 关闭旧页面（如果有）
        await this.closePage();

        // 创建新页面
        this.page = await this.context.newPage();

        // 设置资源屏蔽
        const shouldEnableShield = options.enableResourceShield ?? this.enableResourceShield;
        if (shouldEnableShield) {
            this.resourceShield = new ResourceShield({ silent: this.silent });
            await this.resourceShield.setup(this.page);
        }

        return this.page;
    }

    /**
     * 保存 Cookie 状态
     */
    async saveCookieState() {
        if (this.context) {
            try {
                const statePath = `${this.userDataDir}/browser_state.json`;
                const state = await this.context.storageState();
                fs.writeFileSync(statePath, JSON.stringify(state, null, 2));
                this._log('debug', 'Cookie 状态已保存');
            } catch (e) {
                this._log('warn', `Cookie 保存失败: ${e.message}`);
            }
        }
    }

    /**
     * 切换代理端口
     * @param {number} newPort - 新代理端口
     */
    switchProxyPort(newPort) {
        const oldPort = this.currentProxyPort;
        this.currentProxyPort = newPort;
        this._log('info', `端口切换: ${oldPort} -> ${newPort}`);
    }

    /**
     * 获取下一个代理端口
     * @returns {number}
     */
    getNextProxyPort() {
        if (this.config?.PROXY_CONFIG?.getNextPort) {
            return this.config.PROXY_CONFIG.getNextPort(this.currentProxyPort);
        }
        // 默认轮换 22 个端口
        const ports = Array.from({ length: 22 }, (_, i) => 7890 + i);
        const currentIndex = ports.indexOf(this.currentProxyPort);
        return ports[(currentIndex + 1) % ports.length];
    }

    /**
     * 安全关闭所有资源
     */
    async safeClose() {
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

        if (errors.length > 0) {
            this._log('warn', `关闭时有错误: ${errors.join(', ')}`);
        }
    }

    /**
     * 强制杀死浏览器进程
     */
    async forceKill() {
        const { execSync } = require('child_process');

        try {
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
                this._log('debug', `已强制清理 ${pids.length} 个子进程`);
            }
        } catch (e) {
            // 忽略清理错误
        }

        // 重置实例引用
        this.browser = null;
        this.context = null;
        this.page = null;
    }

    /**
     * 清理上下文中的所有页面
     */
    async cleanupPages() {
        if (this.context) {
            try {
                const pages = this.context.pages();
                for (const p of pages) {
                    try {
                        await p.close();
                    } catch (e) {
                        // 忽略
                    }
                }
            } catch (e) {
                this._log('debug', `清理 context 页面失败: ${e.message}`);
            }
        }
    }

    /**
     * 获取当前状态
     * @returns {object}
     */
    getStatus() {
        return {
            workerId: this.workerId,
            currentProxyPort: this.currentProxyPort,
            hasBrowser: !!this.browser,
            hasContext: !!this.context,
            hasPage: !!this.page,
            userDataDir: this.userDataDir
        };
    }
}

module.exports = {
    BrowserManager,
    ResourceShield
};
