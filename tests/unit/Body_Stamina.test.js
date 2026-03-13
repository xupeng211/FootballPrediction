/**
 * Body_Stamina.test.js - TITAN 体魄与续航测试
 * =============================================
 *
 * 12-14 项原子级测试，验证浏览器隐身能力和 Context 池资源回收。
 *
 * @module tests/unit/Body_Stamina
 * @version V1.0.0
 */

'use strict';

const { describe, it, beforeEach } = require('node:test');
const assert = require('node:assert');
const { BrowserFactory, resetBrowserFactory } = require('../../src/infrastructure/browser/BrowserFactory');
const { ContextPoolManager, resetContextPoolManager } = require('../../src/infrastructure/browser/ContextPoolManager');

describe('TITAN 体魄与续航测试 - 钢铁怪兽的 72 小时', () => {

    beforeEach(() => {
        resetBrowserFactory();
        resetContextPoolManager();
    });

    // ============================================================================
    // A. 隐身衣与手脚 (Browser & Stealth - 5项)
    // ============================================================================

    describe('A. 隐身衣与手脚 (Browser & Stealth)', () => {
        it('A1: BrowserFactory 必须包含完整的 Stealth 注入脚本能力', async () => {
            const factory = new BrowserFactory();

            // 验证 injectStealthScripts 方法存在
            assert.strictEqual(typeof factory.injectStealthScripts, 'function',
                '必须存在 injectStealthScripts 方法');

            // Mock page 对象验证脚本注入
            let scriptInjected = false;
            const mockPage = {
                addInitScript: async (fn) => {
                    if (typeof fn === 'function') {
                        scriptInjected = true;
                        // 验证脚本内容包含关键指纹覆盖
                        const scriptStr = fn.toString();
                        assert.ok(scriptStr.includes('webdriver'),
                            '脚本必须覆盖 webdriver');
                        assert.ok(scriptStr.includes('platform'),
                            '脚本必须覆盖 platform');
                        assert.ok(scriptStr.includes('plugins'),
                            '脚本必须覆盖 plugins');
                        assert.ok(scriptStr.includes('WebGL'),
                            '脚本必须覆盖 WebGL');
                    }
                }
            };

            await factory.injectStealthScripts(mockPage);
            assert.strictEqual(scriptInjected, true,
                'Stealth 脚本必须被注入');
        });

        it('A2: quickMouseMove 生成的坐标必须在 Viewport 合法范围内', async () => {
            const factory = new BrowserFactory();
            const moves = [];

            // Mock page 对象捕获坐标
            const mockPage = {
                mouse: {
                    move: async (x, y, options) => {
                        moves.push({ x, y, steps: options?.steps });
                    }
                }
            };

            await factory.quickMouseMove(mockPage, 3, 5);

            // 验证移动次数在范围内
            assert.ok(moves.length >= 3 && moves.length <= 5,
                `移动次数 ${moves.length} 应在 3-5 之间`);

            // 验证所有坐标在合法 Viewport 内
            for (const move of moves) {
                assert.ok(move.x >= 100 && move.x <= 1800,
                    `X 坐标 ${move.x} 应在 100-1800 之间`);
                assert.ok(move.y >= 100 && move.y <= 900,
                    `Y 坐标 ${move.y} 应在 100-900 之间`);
                assert.strictEqual(move.steps, 5,
                    'steps 应等于 5');
            }
        });

        it('A3: createContext 必须正确传递 Identity 属性到 Context', async () => {
            const factory = new BrowserFactory();

            // Mock browser 和 context
            let capturedConfig = null;
            factory.browser = {
                newContext: async (config) => {
                    capturedConfig = config;
                    return {
                        close: async () => {},
                        clearCookies: async () => {}
                    };
                }
            };

            const identity = {
                proxy: { url: 'http://proxy:8080' },
                stealth: {
                    viewport: { width: 1920, height: 1080 },
                    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
                    extraHTTPHeaders: { 'Accept-Language': 'en-US,en;q=0.9' },
                    deviceScaleFactor: 1,
                    locale: 'en-US',
                    timezoneId: 'America/New_York'
                }
            };

            await factory.createContext(identity);

            // 验证所有 Identity 属性被正确传递
            assert.deepStrictEqual(capturedConfig.viewport, identity.stealth.viewport,
                'viewport 必须匹配');
            assert.strictEqual(capturedConfig.userAgent, identity.stealth.userAgent,
                'userAgent 必须匹配');
            assert.deepStrictEqual(capturedConfig.extraHTTPHeaders, identity.stealth.extraHTTPHeaders,
                'extraHTTPHeaders 必须匹配');
            assert.strictEqual(capturedConfig.deviceScaleFactor, identity.stealth.deviceScaleFactor,
                'deviceScaleFactor 必须匹配');
            assert.strictEqual(capturedConfig.locale, identity.stealth.locale,
                'locale 必须匹配');
            assert.strictEqual(capturedConfig.timezoneId, identity.stealth.timezoneId,
                'timezoneId 必须匹配');
            assert.deepStrictEqual(capturedConfig.proxy, { server: identity.proxy.url },
                'proxy 必须匹配');
        });

        it('A4: warmupHomepage 必须执行 3-5 次随机滚动', async () => {
            const factory = new BrowserFactory();
            const wheels = [];
            let gotoCalled = false;

            // Mock page 对象
            const mockPage = {
                goto: async (url, options) => {
                    gotoCalled = true;
                    assert.strictEqual(url, 'https://www.fotmob.com/',
                        '必须访问 FotMob 首页');
                },
                mouse: {
                    wheel: async (x, y) => {
                        wheels.push({ x, y });
                    }
                }
            };

            // Mock _delay 避免实际等待
            factory._delay = async () => {};

            await factory.warmupHomepage(mockPage);

            assert.strictEqual(gotoCalled, true, 'goto 必须被调用');
            assert.ok(wheels.length >= 3 && wheels.length <= 5,
                `滚动次数 ${wheels.length} 应在 3-5 之间`);

            // 验证滚动方向正确
            for (const wheel of wheels) {
                assert.strictEqual(wheel.x, 0, '水平滚动应为 0');
                assert.ok(wheel.y >= 100 && wheel.y <= 300,
                    `垂直滚动 ${wheel.y} 应在 100-300 之间`);
            }
        });

        it('A5: simulateHumanBehavior 必须执行随机鼠标移动', async () => {
            const factory = new BrowserFactory();
            const moves = [];

            const mockPage = {
                mouse: {
                    move: async (x, y, options) => {
                        moves.push({ x, y, steps: options?.steps });
                    }
                }
            };

            // Mock _delay
            factory._delay = async () => {};

            await factory.simulateHumanBehavior(mockPage);

            // 验证移动次数在 10-15 之间
            assert.ok(moves.length >= 10 && moves.length <= 15,
                `移动次数 ${moves.length} 应在 10-15 之间`);

            // 验证坐标范围和 steps
            for (const move of moves) {
                assert.ok(move.x >= 100 && move.x <= 1800,
                    'X 坐标应在合法范围内');
                assert.ok(move.y >= 100 && move.y <= 900,
                    'Y 坐标应在合法范围内');
                assert.ok(move.steps >= 5 && move.steps <= 15,
                    'steps 应在 5-15 之间');
            }
        });
    });

    // ============================================================================
    // B. 新陈代谢与续航 (Context Pool & LRU - 7项)
    // ============================================================================

    describe('B. 新陈代谢与续航 (Context Pool & LRU)', () => {
        it('B5: 达到 maxSize 时必须触发淘汰逻辑', async () => {
            const pool = new ContextPoolManager({ maxSize: 3, maxUsage: 10 });

            // Mock 依赖
            let evictCalled = false;
            const originalEvict = pool._evictLRU.bind(pool);
            pool._evictLRU = async () => {
                evictCalled = true;
                return originalEvict();
            };

            const mockFactory = {
                createContext: async () => ({
                    close: async () => {},
                    clearCookies: async () => {}
                }),
                loadBrowserStateCookies: async () => false
            };

            const mockNetworkManager = null;
            const identity = { proxy: { port: 8001 } };

            // 创建 3 个 context（达到 maxSize）
            await pool.getOrCreate(1, identity, { browserFactory: mockFactory, networkManager: mockNetworkManager });
            await pool.getOrCreate(2, identity, { browserFactory: mockFactory, networkManager: mockNetworkManager });
            await pool.getOrCreate(3, identity, { browserFactory: mockFactory, networkManager: mockNetworkManager });

            // 第 4 个应该触发淘汰
            evictCalled = false;
            await pool.getOrCreate(4, identity, { browserFactory: mockFactory, networkManager: mockNetworkManager });

            assert.strictEqual(evictCalled, true,
                '超过 maxSize 时必须触发 _evictLRU');
        });

        it('B6: LRU 必须物理关闭最久未使用的 Context', async () => {
            const pool = new ContextPoolManager({ maxSize: 2, maxUsage: 10 });
            const closedContexts = [];
            let contextId = 0;

            const mockFactory = {
                createContext: async () => {
                    const id = ++contextId;
                    return {
                        id,
                        close: async () => {
                            closedContexts.push(id);
                        },
                        clearCookies: async () => {}
                    };
                },
                loadBrowserStateCookies: async () => false
            };

            const identity = { proxy: { port: 8001 } };

            // 创建 2 个 context (达到 maxSize)
            await pool.getOrCreate(1, identity, { browserFactory: mockFactory, networkManager: null });
            await new Promise(r => { setTimeout(r, 50); });
            await pool.getOrCreate(2, identity, { browserFactory: mockFactory, networkManager: null });

            // 立即访问 worker 1，让 worker 2 成为最久未使用
            await new Promise(r => { setTimeout(r, 50); });
            await pool.getOrCreate(1, identity, { browserFactory: mockFactory, networkManager: null });

            // 获取 worker 2 的 context ID（应该是最久未使用的）
            const entry2 = pool.getEntry(2);
            const context2Id = entry2.context.id;

            // 创建第 3 个，应该淘汰 worker 2 (最久未使用)
            await new Promise(r => { setTimeout(r, 50); });
            await pool.getOrCreate(3, identity, { browserFactory: mockFactory, networkManager: null });

            // 验证最久未使用的 context 被关闭
            assert.ok(closedContexts.includes(context2Id),
                `最久未使用的 Context (ID: ${context2Id}) 应被物理关闭`);
            assert.strictEqual(pool.getEntry(2), undefined,
                'Worker 2 的条目应从池中移除');
            assert.ok(pool.getEntry(1) !== undefined, 'Worker 1 应仍在池中');
            assert.ok(pool.getEntry(3) !== undefined, 'Worker 3 应在新池中');
        });

        it('B7: usageCount 达到阈值后必须强制注销并重建', async () => {
            const pool = new ContextPoolManager({ maxSize: 5, maxUsage: 3 });
            let createCount = 0;
            let closeCount = 0;

            const mockFactory = {
                createContext: async () => {
                    createCount++;
                    return {
                        close: async () => { closeCount++; },
                        clearCookies: async () => {}
                    };
                },
                loadBrowserStateCookies: async () => false
            };

            const identity = { proxy: { port: 8001 } };

            // 第 1 次创建 (usageCount = 0)
            await pool.getOrCreate(1, identity, { browserFactory: mockFactory, networkManager: null });
            assert.strictEqual(createCount, 1, '第 1 次应创建');

            // 复用 3 次（usageCount 从 0 -> 1 -> 2 -> 3，达到 maxUsage）
            await pool.getOrCreate(1, identity, { browserFactory: mockFactory, networkManager: null });
            await pool.getOrCreate(1, identity, { browserFactory: mockFactory, networkManager: null });
            await pool.getOrCreate(1, identity, { browserFactory: mockFactory, networkManager: null });

            // 第 5 次应该触发重建 (usageCount >= maxUsage)
            await pool.getOrCreate(1, identity, { browserFactory: mockFactory, networkManager: null });
            assert.strictEqual(createCount, 2, '达到 maxUsage 后应重建');
            assert.strictEqual(closeCount, 1, '旧 context 应被关闭');
        });

        it('B8: cleanup 方法必须关闭所有池内 Context', async () => {
            const pool = new ContextPoolManager({ maxSize: 5, maxUsage: 10 });
            const closedContexts = [];

            const mockFactory = {
                createContext: async (id) => ({
                    close: async () => { closedContexts.push(id); },
                    clearCookies: async () => {}
                }),
                loadBrowserStateCookies: async () => false
            };

            const identity = { proxy: { port: 8001 } };

            // 创建 3 个 context
            await pool.getOrCreate(1, identity, { browserFactory: mockFactory, networkManager: null });
            await pool.getOrCreate(2, identity, { browserFactory: mockFactory, networkManager: null });
            await pool.getOrCreate(3, identity, { browserFactory: mockFactory, networkManager: null });

            assert.strictEqual(pool.getSize(), 3, '池中应有 3 个 context');

            // 执行 cleanup
            await pool.cleanup();

            assert.strictEqual(pool.getSize(), 0, 'cleanup 后池应为空');
            assert.strictEqual(closedContexts.length, 3,
                '所有 3 个 context 应被关闭');
        });

        it('B9: port 变更时必须重建 Context', async () => {
            const pool = new ContextPoolManager({ maxSize: 5, maxUsage: 10 });
            let createCount = 0;

            const mockFactory = {
                createContext: async () => {
                    createCount++;
                    return {
                        close: async () => {},
                        clearCookies: async () => {}
                    };
                },
                loadBrowserStateCookies: async () => false
            };

            // 第 1 次，port 8001
            await pool.getOrCreate(1, { proxy: { port: 8001 } },
                { browserFactory: mockFactory, networkManager: null });
            assert.strictEqual(createCount, 1);

            // 复用，相同 port
            await pool.getOrCreate(1, { proxy: { port: 8001 } },
                { browserFactory: mockFactory, networkManager: null });
            assert.strictEqual(createCount, 1, '相同 port 应复用');

            // port 变更，应该重建
            await pool.getOrCreate(1, { proxy: { port: 8002 } },
                { browserFactory: mockFactory, networkManager: null });
            assert.strictEqual(createCount, 2, 'port 变更应重建');
        });

        it('B10: clearCookies 必须成功清理指定 Worker 的 Cookies', async () => {
            const pool = new ContextPoolManager({ maxSize: 5, maxUsage: 10 });
            let clearCalled = false;

            const mockFactory = {
                createContext: async () => ({
                    close: async () => {},
                    clearCookies: async () => { clearCalled = true; }
                }),
                loadBrowserStateCookies: async () => false
            };

            const identity = { proxy: { port: 8001 } };
            await pool.getOrCreate(1, identity, { browserFactory: mockFactory, networkManager: null });

            // 先增加 usageCount
            await pool.getOrCreate(1, identity, { browserFactory: mockFactory, networkManager: null });
            const entryBefore = pool.getEntry(1);
            assert.strictEqual(entryBefore.usageCount, 1);

            // 清理 cookies
            const result = await pool.clearCookies(1);

            assert.strictEqual(result, true, 'clearCookies 应返回 true');
            assert.strictEqual(clearCalled, true, 'clearCookies 应被调用');

            // usageCount 应被重置
            const entryAfter = pool.getEntry(1);
            assert.strictEqual(entryAfter.usageCount, 0, 'usageCount 应被重置为 0');
        });

        it('B11: 统计功能必须准确记录创建、复用和淘汰', async () => {
            const pool = new ContextPoolManager({ maxSize: 2, maxUsage: 10 });

            const mockFactory = {
                createContext: async () => ({
                    close: async () => {},
                    clearCookies: async () => {}
                }),
                loadBrowserStateCookies: async () => false
            };

            const identity = { proxy: { port: 8001 } };

            // 初始统计
            let stats = pool.getStats();
            assert.strictEqual(stats.totalCreations, 0, '初始创建数应为 0');
            assert.strictEqual(stats.totalReuses, 0, '初始复用数应为 0');
            assert.strictEqual(stats.totalEvictions, 0, '初始淘汰数应为 0');

            // 创建 2 个 (达到 maxSize)
            await pool.getOrCreate(1, identity, { browserFactory: mockFactory, networkManager: null });
            await pool.getOrCreate(2, identity, { browserFactory: mockFactory, networkManager: null });
            stats = pool.getStats();
            assert.strictEqual(stats.totalCreations, 2, '创建数应为 2');

            // 复用 2 次
            await pool.getOrCreate(1, identity, { browserFactory: mockFactory, networkManager: null });
            await pool.getOrCreate(2, identity, { browserFactory: mockFactory, networkManager: null });
            stats = pool.getStats();
            assert.strictEqual(stats.totalReuses, 2, '复用数应为 2');
            assert.ok(stats.reuseRate.includes('50'), '复用率应约为 50%');

            // 第 3 个创建，触发 LRU 淘汰
            await new Promise(r => { setTimeout(r, 50); });
            await pool.getOrCreate(3, identity, { browserFactory: mockFactory, networkManager: null });
            stats = pool.getStats();
            assert.strictEqual(stats.totalEvictions, 1, '淘汰数应为 1');
        });
    });
});
