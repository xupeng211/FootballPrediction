/**
 * StealthInjector - 反检测脚本注入器
 * ==============================================
 *
 * 注入 Stealth 脚本，隐藏浏览器自动化特征
 * - 禁用 navigator.webdriver
 * - 硬件并发数伪装
 * - 设备内存伪装
 * - 屏蔽自动化标志
 *
 * @module core/browser/StealthInjector
 * @version V174.0.0
 */

'use strict';

/**
 * StealthInjector - 反检测脚本注入器
 */
class StealthInjector {
    /**
     * @param {Object} options - 配置选项
     * @param {number} options.hardwareConcurrency - 伪装的 CPU 核心数
     * @param {number} options.deviceMemory - 伪装的设备内存 (GB)
     * @param {boolean} options.silent - 静默模式
     */
    constructor(options = {}) {
        this.hardwareConcurrency = options.hardwareConcurrency ?? 8;
        this.deviceMemory = options.deviceMemory ?? 8;
        this.silent = options.silent ?? false;
    }

    /**
     * 日志输出
     * @private
     */
    _log(level, msg) {
        if (this.silent) return;
        const timestamp = new Date().toISOString().slice(0, 19).replace('T', ' ');
        const prefix = '[StealthInjector]';
        console.log(`${timestamp} ${prefix} [${level.toUpperCase()}] ${msg}`);
    }

    /**
     * 生成 Stealth 脚本
     * @returns {Function} 注入脚本函数
     */
    generateScript() {
        const hardwareConcurrency = this.hardwareConcurrency;
        const deviceMemory = this.deviceMemory;

        return () => {
            // 禁用 navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

            // 硬件并发数伪装
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => hardwareConcurrency
            });

            // 设备内存伪装
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => deviceMemory
            });

            // 屏蔽自动化标志
            window.chrome = { runtime: {} };

            // 覆盖 permissions API
            const originalQuery = window.navigator.permissions?.query;
            if (originalQuery) {
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            }

            // 覆盖 plugins 长度
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // 覆盖 languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en']
            });
        };
    }

    /**
     * 向浏览器上下文注入 Stealth 脚本
     * @param {import('playwright').BrowserContext} context - Playwright 浏览器上下文
     */
    async inject(context) {
        if (!context) {
            this._log('warn', '上下文为空，跳过注入');
            return;
        }

        try {
            const script = this.generateScript();
            await context.addInitScript(script);
            this._log('debug', 'Stealth 脚本已注入');
        } catch (e) {
            this._log('error', `注入失败: ${e.message}`);
            throw e;
        }
    }

    /**
     * 静态方法：快速注入
     * @param {import('playwright').BrowserContext} context - 浏览器上下文
     * @param {Object} options - 配置选项
     */
    static async quickInject(context, options = {}) {
        const injector = new StealthInjector(options);
        return injector.inject(context);
    }
}

/**
 * 默认 Stealth 脚本（用于快速使用）
 * @returns {Function}
 */
function getDefaultStealthScript() {
    const injector = new StealthInjector();
    return injector.generateScript();
}

module.exports = {
    StealthInjector,
    getDefaultStealthScript
};
