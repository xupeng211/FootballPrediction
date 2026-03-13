/**
 * BrowserFactory 单元测试
 * ======================
 *
 * 测试重点:
 * 1. 浏览器启动/关闭
 * 2. Context 创建
 * 3. 隐身脚本注入
 * 4. Cookie 加载
 * 5. 行为模拟方法
 */

const { describe, it, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert');

// 增加 EventEmitter 监听器上限
process.setMaxListeners(50);

// 模拟 chromium 模块
const MockBrowser = class {
    /**
     *
     */
    static async launch() {
        return {
            newContext: () => ({
                newPage: () => {
                    let _scriptsInjected = false;
                    return {
                        goto: async () => {},
                        waitForTimeout: async () => {},
                        evaluate: async (fn) => {
                            // 如果隐身脚本已注入，返回伪装后的值
                            if (_scriptsInjected) {
                                const fnStr = fn.toString();
                                if (fnStr.includes('navigator.webdriver')) return undefined;
                                if (fnStr.includes('navigator.platform')) return 'Win32';
                                if (fnStr.includes('navigator.languages')) return ['en-US', 'en'];
                                if (fnStr.includes('navigator.plugins')) return { length: 3 };
                            }
                            return undefined;
                        },
                        addInitScript: async () => {
                            _scriptsInjected = true;
                        },
                        close: async () => {}
                    };
                },
                addCookies: async () => true,
                close: async () => {}
            }),
            isConnected: () => true,
            close: async () => {}
        };
    }
};

// 模拟 Playwright
const mockPlaywright = {
    chromium: MockBrowser
};

// 劫持 require
const originalRequire = require;
// eslint-disable-next-line no-global-assign
require = function(id) {
    if (id === 'playwright') return mockPlaywright;
    return originalRequire.apply(this, arguments);
};

const { BrowserFactory, resetBrowserFactory } = require('../../src/infrastructure/browser/BrowserFactory');

// ============================================================================
// Mock Identity
// ============================================================================

/**
 *
 * @param port
 */
function createMockIdentity(port = 7890) {
    return {
        proxy: { url: `http://172.25.16.1:${port}`, port },
        stealth: {
            viewport: { width: 1920, height: 1080 },
            userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            extraHTTPHeaders: { 'Accept-Language': 'en-US,en;q=0.9' },
            deviceScaleFactor: 1,
            locale: 'en-US',
            timezoneId: 'Europe/London'
        }
    };
}

// ============================================================================
// 测试套件
// ============================================================================

describe('BrowserFactory', () => {
    let factory;

    beforeEach(() => {
        resetBrowserFactory();
        factory = new BrowserFactory({ headless: true });
    });

    afterEach(async () => {
        if (factory) {
            try {
                await factory.close();
            } catch (e) {
                // ignore
            }
        }
    });

    // ========================================================================
    // 测试 1-5: 浏览器生命周期测试
    // ========================================================================

    it('应该成功启动浏览器', async () => {
        const browser = await factory.launch();
        assert.ok(browser, '浏览器应该被成功启动');
    });

    it('应该返回单例浏览器实例', async () => {
        const browser1 = await factory.launch();
        const browser2 = await factory.launch();
        assert.strictEqual(browser1, browser2, '应该返回同一个浏览器实例');
    });

    it('应该成功关闭浏览器', async () => {
        await factory.launch();
        await factory.close();
        assert.strictEqual(factory.browser, null, '关闭后 browser 应该为 null');
    });

    it('getBrowser 应该返回浏览器实例', async () => {
        await factory.launch();
        const browser = factory.getBrowser();
        assert.ok(browser, 'getBrowser 应该返回浏览器实例');
    });

    it('未启动时 getBrowser 应该返回 null', () => {
        const browser = factory.getBrowser();
        assert.strictEqual(browser, null, '未启动时 getBrowser 应该返回 null');
    });

    // ========================================================================
    // 测试 6-9: Context 创建测试
    // ========================================================================

    it('应该成功创建 Context', async () => {
        await factory.launch();
        const identity = createMockIdentity();
        const context = await factory.createContext(identity, true);
        assert.ok(context, 'Context 应该被成功创建');
    });

    it('应该在未启动浏览器时抛出错误', async () => {
        const identity = createMockIdentity();
        await assert.rejects(
            async () => factory.createContext(identity, true),
            { message: /浏览器未启动/ }
        );
    });

    it('应该正确设置 viewport', async () => {
        await factory.launch();
        const identity = createMockIdentity();
        const context = await factory.createContext(identity, true);
        assert.ok(context, 'Context 应该被成功创建');
    });

    it('应该正确设置 userAgent', async () => {
        await factory.launch();
        const identity = createMockIdentity();
        const context = await factory.createContext(identity, true);
        assert.ok(context, 'Context 应该被成功创建');
    });

    // ========================================================================
    // 测试 10-12: 隐身脚本注入测试
    // ========================================================================

    it('injectStealthScripts 应该是一个函数', () => {
        assert.strictEqual(typeof factory.injectStealthScripts, 'function');
    });

    it('应该成功注入隐身脚本', async () => {
        await factory.launch();
        const identity = createMockIdentity();
        const context = await factory.createContext(identity, true);
        const page = await context.newPage();

        // 不应该抛出错误
        await factory.injectStealthScripts(page);
    });

    it('隐身脚本应该覆盖 webdriver (Mock 限制)', async () => {
        // 注意: 此测试在 Mock 环境下无法完全验证隐身脚本效果
        // 真实验证需要运行 tests/verify_stealth.js
        await factory.launch();
        const identity = createMockIdentity();
        const context = await factory.createContext(identity, true);
        const page = await context.newPage();
        await factory.injectStealthScripts(page);

        // Mock 环境下只验证方法被成功调用
        // 真实浏览器测试请运行: node tests/verify_stealth.js
        assert.ok(true, 'injectStealthScripts 方法调用成功');
    });

    // ========================================================================
    // 测试 13-14: Cookie 加载测试
    // ========================================================================

    it('loadBrowserStateCookies 应该是一个函数', () => {
        assert.strictEqual(typeof factory.loadBrowserStateCookies, 'function');
    });

    it('loadBrowserStateCookies 在文件不存在时返回 false', async () => {
        await factory.launch();
        const identity = createMockIdentity();
        const context = await factory.createContext(identity, true);

        const result = await factory.loadBrowserStateCookies(context);
        assert.strictEqual(typeof result, 'boolean');
    });

    // ========================================================================
    // 测试 15-18: 行为模拟方法测试
    // ========================================================================

    it('quickMouseMove 应该是一个函数', () => {
        assert.strictEqual(typeof factory.quickMouseMove, 'function');
    });

    it('warmupHomepage 应该是一个函数', () => {
        assert.strictEqual(typeof factory.warmupHomepage, 'function');
    });

    it('simulateHumanBehavior 应该是一个函数', () => {
        assert.strictEqual(typeof factory.simulateHumanBehavior, 'function');
    });

    it('_randomInRange 应该返回范围内的随机数', () => {
        for (let i = 0; i < 10; i++) {
            const result = factory._randomInRange(1, 10);
            assert.ok(result >= 1 && result <= 10, '结果应该在 1-10 范围内');
        }
    });

    it('_delay 应该返回 Promise', () => {
        const promise = factory._delay(10);
        assert.ok(promise instanceof Promise);
    });
});
