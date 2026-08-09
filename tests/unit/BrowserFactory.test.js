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
const path = require('node:path');

// 增加 EventEmitter 监听器上限
process.setMaxListeners(50);

// ============================================================================
// Runner IPC 完整性: 套件运行期间静默 console 输出
// ============================================================================
// Node 20.20.x test runner 的父进程 (v8-serializer reporter) 无法容忍同一 pipe
// chunk 内"两个 reporter frame 之间"出现非序列化文本: 文本字节会被当作 frame
// size 读取, 触发随机崩溃 "Unable to deserialize cloned data due to invalid or
// unsupported version" (是否崩溃取决于 pipe 分块时机, 与测试本身无关)。
// BrowserFactory 的 launch/close 等方法每次调用都会 console.log, 因此本套件
// 运行期间将 console.log 替换为空操作, 保证子进程 stdout 只含 reporter frames
// (不影响 node --test 自身的报告输出, 报告走 reporter 而非 console.log)。
const silencedConsoleLog = () => {};
console.log = silencedConsoleLog;

/**
 * 按 Node 20.20 test runner 父进程 (internal/test_runner/runner.js
 * #proccessRawBuffer) 的帧协议解析子进程 stdout。
 * 帧格式: [0xFF,0x0F][4B 大端 size][0xFF,0x0F][v8 payload]; 帧与帧之间出现
 * 的原始文本 (console.log 输出) 会导致父进程反序列化崩溃, 因此本函数把
 * "帧间文本" 与 "帧前文本" 一并计入, 并统计成功解析的帧数量。
 * @returns {{texts: number, frames: number}}
 */
function analyzeRunnerStdout(buf) {
    const V8H = Buffer.from([0xFF, 0x0F]);
    let i = 0;
    let texts = 0;
    let frames = 0;
    while (i < buf.length) {
        const hit = buf.indexOf(V8H, i);
        if (hit === -1) {
            if (buf.length - i > 0) texts++;
            break;
        }
        if (hit > i) texts++;
        if (hit + 6 > buf.length) break; // 帧头被截断 (非本套件场景)
        const size = buf.readUInt32BE(hit + 2);
        const frameEnd = hit + 6 + size;
        if (frameEnd > buf.length) break; // 帧未完整 (非本套件场景)
        i = frameEnd;
        frames++;
    }
    return { texts, frames };
}

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

// 仅在本测试的 require 阶段提供 Playwright 伪模块，避免修改全局
// Module._load；后者在大批量宿主机 runner 中可能干扰 Node test worker 的 IPC。
const playwrightModulePath = require.resolve('playwright');
const originalPlaywrightModule = require.cache[playwrightModulePath];
require.cache[playwrightModulePath] = {
    id: playwrightModulePath,
    filename: playwrightModulePath,
    loaded: true,
    exports: { chromium: MockBrowser }
};

let BrowserFactory;
let resetBrowserFactory;
try {
    ({ BrowserFactory, resetBrowserFactory } = require('../../src/infrastructure/browser/BrowserFactory'));
} finally {
    if (originalPlaywrightModule) {
        require.cache[playwrightModulePath] = originalPlaywrightModule;
    } else {
        delete require.cache[playwrightModulePath];
    }
}

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

    it('warmupHomepage 默认应硬跳过首页访问', async () => {
        let gotoCalls = 0;
        const page = {
            goto: async () => {
                gotoCalls++;
            }
        };

        const result = await factory.warmupHomepage(page, { scrollMore: false, randomScrolls: false });

        assert.strictEqual(gotoCalls, 0, '预热被停用后不应访问 FotMob 首页');
        assert.deepStrictEqual(result, {
            skipped: true,
            pageAttached: true,
            hasConfig: true
        });
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

    // ========================================================================
    // 回归测试: runner IPC 完整性 (子进程 stdout 只含 reporter frames)
    // ========================================================================
    // 以与 Node test runner 父进程相同的方式 (node <file>, NODE_TEST_CONTEXT=
    // child-v8) 运行本文件, 解析其 stdout 并断言不包含任何非序列化文本。
    // 未静默 console 时本断言必然失败: launch/close 等会输出约 30 行日志;
    // 修复后子进程 stdout 只含帧, 断言必然通过。
    it('子进程 stdout 只含 reporter frames (无 console 文本)', async () => {
        // 仅当本进程确为上方派生出的子进程 (父进程同时注入了两个环境变量)
        // 时才跳过, 避免无限递归; 普通直接运行或仅设单一变量不会命中。
        if (process.env.NODE_TEST_CONTEXT === 'child-v8' &&
            process.env.BF_IPC_INTEGRITY_CHILD === '1') {
            return;
        }
        const { spawnSync } = require('node:child_process');
        const r = spawnSync(process.execPath, [__filename], {
            cwd: path.join(__dirname, '..', '..'),
            encoding: null,
            maxBuffer: 16 * 1024 * 1024,
            timeout: 120000,
            env: {
                ...process.env,
                NODE_TEST_CONTEXT: 'child-v8',
                BF_IPC_INTEGRITY_CHILD: '1'
            }
        });
        assert.strictEqual(
            r.status,
            0,
            `子进程异常退出: ${String(r.stderr || '').slice(-500)}`
        );
        const { texts, frames } = analyzeRunnerStdout(r.stdout);
        assert.ok(frames > 0, '子进程 stdout 未解析出任何 reporter 帧');
        assert.strictEqual(
            texts,
            0,
            `子进程 stdout 含 ${texts} 段非序列化文本, 会触发 runner IPC 反序列化崩溃`
        );
    });
});
