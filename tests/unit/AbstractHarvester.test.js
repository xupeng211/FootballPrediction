/**
 * AbstractHarvester 完整测试套件
 * =====================================
 *
 * 测试覆盖：
 * - 构造函数与配置
 * - 抽象方法
 * - 错误分类逻辑
 * - AutoAuth 触发机制
 * - 弹性重试机制
 * - Context 池管理
 * - 403 逃逸机制
 * - 工具方法
 * - 报告打印
 * - 浏览器行为模拟
 * - Cookie 加载
 */

const { describe, it, beforeEach, afterEach, mock } = require('node:test');
const assert = require('node:assert');

// 增加 EventEmitter 监听器上限，避免测试警告
process.setMaxListeners(50);

// 模拟 chromium 模块，避免加载 Playwright
const MockBrowser = class {
    /**
     *
     */
    static async launch() {
        return {
            newContext: () => ({
                newPage: () => ({}),
                cookies: async () => [],
                addCookies: async () => {},
                clearCookies: async () => {},
                close: async () => {}
            }),
            close: async () => {}
        };
    }
};

// 使用 mock 替换 chromium
const originalRequire = require;
const Module = require('module');

// 劫持 require 来模拟 playwright
const originalLoad = Module._load;
Module._load = function(request, parent, isMain) {
    if (request === 'playwright') {
        return { chromium: MockBrowser };
    }
    return originalLoad.apply(this, arguments);
};

const { AbstractHarvester } = require('../../src/infrastructure/harvesters/base/AbstractHarvester');
const { ProductionHarvester } = require('../../src/infrastructure/harvesters/ProductionHarvester');
const { AutoAuthManager } = require('../../src/infrastructure/auth/AutoAuthManager');

// 恢复原始的 Module._load
Module._load = originalLoad;

describe('AbstractHarvester 完整测试套件', () => {
    let originalEnv;
    let harvesterInstances = [];

    beforeEach(() => {
        // 保存原始环境变量
        originalEnv = { ...process.env };

        // 设置测试环境变量
        process.env.MAX_WORKERS = '1';
        process.env.MIN_DELAY_MS = '10';
        process.env.MAX_DELAY_MS = '20';
        process.env.MAX_RETRIES = '3';
        process.env.DISABLE_PROXY = 'true';

        // 重置实例列表
        harvesterInstances = [];
    });

    afterEach(() => {
        // 恢复环境变量
        process.env = originalEnv;

        // 清理所有 harvester 实例的信号监听器
        for (const harvester of harvesterInstances) {
            if (harvester.isShuttingDown === false) {
                harvester.isShuttingDown = true; // 防止停机逻辑执行
            }
        }
        harvesterInstances = [];

        // 移除所有 SIGINT/SIGTERM 监听器（防止测试框架检测到未清理的资源）
        process.removeAllListeners('SIGINT');
        process.removeAllListeners('SIGTERM');
    });

    // 辅助函数：创建 harvester 并跟踪实例
    /**
     *
     * @param HarvesterClass
     * @param config
     */
    function createHarvester(HarvesterClass, config = {}) {
        const harvester = new HarvesterClass(config);
        harvesterInstances.push(harvester);
        return harvester;
    }

    // ========================================================================
    // 测试 1: 构造函数与配置
    // ========================================================================

    describe('构造函数与配置', () => {
        it('应该使用默认配置创建实例', () => {
            // 清除环境变量以测试默认值
            delete process.env.MAX_WORKERS;
            delete process.env.MIN_DELAY_MS;
            delete process.env.MAX_DELAY_MS;

            const harvester = createHarvester(AbstractHarvester);
            assert.strictEqual(harvester.config.maxWorkers, 6);
            assert.strictEqual(harvester.config.minDelayMs, 10000);
            assert.strictEqual(harvester.config.maxDelayMs, 20000);
        });

        it('应该覆盖默认配置', () => {
            const harvester = createHarvester(AbstractHarvester, {
                maxWorkers: 10,
                minDelayMs: 5000,
                maxDelayMs: 10000
            });
            assert.strictEqual(harvester.config.maxWorkers, 10);
            assert.strictEqual(harvester.config.minDelayMs, 5000);
            assert.strictEqual(harvester.config.maxDelayMs, 10000);
        });

        it('应该从环境变量读取配置', () => {
            process.env.MAX_WORKERS = '8';
            process.env.MIN_DELAY_MS = '2000';
            process.env.MAX_DELAY_MS = '4000';

            const harvester = createHarvester(AbstractHarvester);
            assert.strictEqual(harvester.config.maxWorkers, 8);
            assert.strictEqual(harvester.config.minDelayMs, 2000);
            assert.strictEqual(harvester.config.maxDelayMs, 4000);
        });

        it('应该初始化统计对象', () => {
            const harvester = createHarvester(AbstractHarvester);
            assert.strictEqual(harvester.stats.total, 0);
            assert.strictEqual(harvester.stats.processed, 0);
            assert.strictEqual(harvester.stats.success, 0);
            assert.strictEqual(harvester.stats.failed, 0);
        });
    });

    // ========================================================================
    // 测试 2: 抽象方法
    // ========================================================================

    describe('抽象方法', () => {
        it('extractData 应该抛出错误', async () => {
            const harvester = createHarvester(AbstractHarvester);

            try {
                await harvester.extractData({}, {});
                assert.fail('应该抛出错误');
            } catch (error) {
                assert.ok(error.message.includes('子类必须实现'));
            }
        });

        it('getTargetUrl 应该抛出错误', () => {
            const harvester = createHarvester(AbstractHarvester);

            try {
                harvester.getTargetUrl({});
                assert.fail('应该抛出错误');
            } catch (error) {
                assert.ok(error.message.includes('子类必须实现'));
            }
        });

        it('saveData 应该抛出错误', async () => {
            const harvester = createHarvester(AbstractHarvester);

            try {
                await harvester.saveData('test', {});
                assert.fail('应该抛出错误');
            } catch (error) {
                assert.ok(error.message.includes('子类必须实现'));
            }
        });
    });

    // ========================================================================
    // 测试 3: 错误分类逻辑
    // ========================================================================

    describe('错误分类测试', () => {
        it('应该正确识别 BLOCKED 错误 (Turnstile)', () => {
            const harvester = createHarvester(AbstractHarvester);
            const errorType = harvester._classifyError('Turnstile challenge required');
            assert.strictEqual(errorType, 'BLOCKED');
        });

        it('应该正确识别 BLOCKED 错误 (Captcha)', () => {
            const harvester = createHarvester(AbstractHarvester);
            const errorType = harvester._classifyError('Captcha verification failed');
            assert.strictEqual(errorType, 'BLOCKED');
        });

        it('应该正确识别 BLOCKED 错误 (Circuit Breaker)', () => {
            const harvester = createHarvester(AbstractHarvester);
            const errorType = harvester._classifyError('circuit_breaker_open');
            assert.strictEqual(errorType, 'BLOCKED');
        });

        it('应该正确识别 RATE_LIMITED 错误', () => {
            const harvester = createHarvester(AbstractHarvester);
            const errorType = harvester._classifyError('403 Forbidden');
            assert.strictEqual(errorType, 'RATE_LIMITED');
        });

        it('应该正确识别 NETWORK_ERROR 错误', () => {
            const harvester = createHarvester(AbstractHarvester);
            const errorType = harvester._classifyError('Connection refused');
            assert.strictEqual(errorType, 'NETWORK_ERROR');
        });

        it('应该正确识别 TIMEOUT 错误', () => {
            const harvester = createHarvester(AbstractHarvester);
            const errorType = harvester._classifyError('Request timeout');
            assert.strictEqual(errorType, 'TIMEOUT');
        });

        it('应该正确识别 NO_DATA 错误', () => {
            const harvester = createHarvester(AbstractHarvester);
            const errorType = harvester._classifyError('no_data');
            assert.strictEqual(errorType, 'NO_DATA');
        });

        it('应该对未知错误返回 UNKNOWN', () => {
            const harvester = createHarvester(AbstractHarvester);
            const errorType = harvester._classifyError('Some random error');
            assert.strictEqual(errorType, 'UNKNOWN');
        });
    });

    // ========================================================================
    // 测试 4: AutoAuth 触发机制
    // ========================================================================

    describe('AutoAuth 触发测试', () => {
        it('应该在 NetworkManager 不存在时优雅处理', async () => {
            const harvester = createHarvester(AbstractHarvester);

            // Mock NetworkManager 为 null
            harvester.networkManager = null;

            // 执行 AutoAuth - 不应该抛出异常
            try {
                await harvester._triggerAutoAuth(1, 'Turnstile required');
                // 成功完成，没有异常
                assert.ok(true);
            } catch (error) {
                // 如果抛出异常，测试失败
                assert.fail(`不应该抛出异常: ${error.message}`);
            }
        });

        it('应该在 BLOCKED 错误时触发 AutoAuth', async () => {
            const harvester = createHarvester(ProductionHarvester, { maxRetries: 1 });

            // Mock _harvestSingleMatch 返回 BLOCKED 错误
            harvester._harvestSingleMatch = async () => {
                return {
                    success: false,
                    match_id: 'test',
                    error: 'Turnstile challenge required',
                    workerId: 1
                };
            };

            // Mock _triggerAutoAuth
            let autoAuthTriggered = false;
            harvester._triggerAutoAuth = async (workerId, error) => {
                autoAuthTriggered = true;
            };

            // Mock _isRetryableError - Turnstile 不可重试
            harvester._isRetryableError = (error) => false;

            // 执行收割
            const result = await harvester.harvestWithRetry(
                { match_id: 'test', home_team: 'A', away_team: 'B' },
                0,
                1
            );

            // 验证 AutoAuth 被触发
            assert.strictEqual(autoAuthTriggered, true, 'AutoAuth 应该在 BLOCKED 错误时被触发');
            assert.strictEqual(result.success, false, '收割应该失败');
        });

        it('应该正确清理 Session 和切换端口', async () => {
            const harvester = createHarvester(AbstractHarvester);

            // Mock NetworkManager
            const sessionCleared = { called: false, port: null };
            const portSwitched = { called: false, oldPort: null, newPort: null };

            harvester.networkManager = {
                getWorkerIdentity: (workerId) => ({
                    proxy: { port: 7890, url: 'http://172.25.16.1:7890' }
                }),
                sessionManager: {
                    clearSession: async (port) => {
                        sessionCleared.called = true;
                        sessionCleared.port = port;
                    }
                },
                forceReassignPort: async (workerId, oldPort) => {
                    portSwitched.called = true;
                    portSwitched.oldPort = oldPort;
                    portSwitched.newPort = 7891;
                    return { port: 7891 };
                }
            };

            // Mock Context Pool
            const contextClosed = { called: false };
            harvester._contextPool = new Map();
            harvester._contextPool.set(1, {
                context: {
                    close: async () => {
                        contextClosed.called = true;
                    }
                }
            });

            // 执行 AutoAuth
            await harvester._triggerAutoAuth(1, 'Turnstile required');

            // 验证清理操作
            assert.strictEqual(sessionCleared.called, true, 'Session 应该被清理');
            assert.strictEqual(sessionCleared.port, 7890, '应该清理正确的端口 Session');
            assert.strictEqual(portSwitched.called, true, '端口应该被切换');
            assert.strictEqual(portSwitched.oldPort, 7890, '应该从旧端口切换');
            assert.strictEqual(contextClosed.called, true, 'Context 应该被关闭');
        });
    });

    // ========================================================================
    // 测试 5: 可重试错误判断
    // ========================================================================

    describe('可重试错误判断', () => {
        it('应该将网络错误标记为可重试', () => {
            const harvester = createHarvester(AbstractHarvester);

            const retryableErrors = [
                'ERR_CONNECTION_CLOSED',
                'ERR_CONNECTION_RESET',
                'ERR_TIMED_OUT',
                'ETIMEDOUT',
                'ECONNRESET',
                'ECONNREFUSED',
                'ENOTFOUND',
                'net::ERR_CONNECTION_FAILED',
                'Navigation timeout',
                'CF_BLOCK'
            ];

            for (const errorMsg of retryableErrors) {
                const isRetryable = harvester._isRetryableError(new Error(errorMsg));
                assert.strictEqual(isRetryable, true, `${errorMsg} 应该是可重试的`);
            }
        });

        it('应该将 BLOCKED 错误标记为不可重试', () => {
            const harvester = createHarvester(AbstractHarvester);

            const nonRetryableErrors = [
                '403 Forbidden',
                'ERR_BLOCKED_BY_CLIENT',
                'Access denied',
                'Turnstile challenge required'
            ];

            for (const errorMsg of nonRetryableErrors) {
                const isRetryable = harvester._isRetryableError(new Error(errorMsg));
                assert.strictEqual(isRetryable, false, `${errorMsg} 应该是不可重试的`);
            }
        });

        it('应该将 SIZE_TOO_SMALL 标记为可重试', () => {
            const harvester = createHarvester(AbstractHarvester);
            const isRetryable = harvester._isRetryableError(new Error('SIZE_TOO_SMALL:500'));
            assert.strictEqual(isRetryable, true, 'SIZE_TOO_SMALL 应该是可重试的');
        });

        it('应该将 NO_DATA 标记为不可重试', () => {
            const harvester = createHarvester(AbstractHarvester);
            const isRetryable = harvester._isRetryableError(new Error('NO_DATA:无法获取数据'));
            assert.strictEqual(isRetryable, false, 'NO_DATA 应该是不可重试的');
        });
    });

    // ========================================================================
    // 测试 6: 弹性重试机制
    // ========================================================================

    describe('弹性重试机制', () => {
        it('应该在成功时立即返回', async () => {
            const harvester = createHarvester(AbstractHarvester);

            // Mock _harvestSingleMatch 返回成功
            harvester._harvestSingleMatch = async () => {
                return { success: true, match_id: 'test', size: 5000 };
            };

            const result = await harvester.harvestWithRetry({ match_id: 'test' }, 0, 3);

            assert.strictEqual(result.success, true);
            assert.strictEqual(result.attempts, undefined);  // 第一次就成功，不会有 attempts 字段
        });

        it('应该在不可重试错误时立即失败', async () => {
            const harvester = createHarvester(AbstractHarvester);

            // Mock _harvestSingleMatch 返回 BLOCKED 错误
            harvester._harvestSingleMatch = async () => {
                return { success: false, match_id: 'test', error: 'Turnstile challenge required', attempt: 1 };
            };

            // Mock _isRetryableError
            harvester._isRetryableError = () => false;

            // Mock _triggerAutoAuth
            harvester._triggerAutoAuth = async () => {};

            const result = await harvester.harvestWithRetry({ match_id: 'test' }, 0, 3);

            assert.strictEqual(result.success, false);
            // 不可重试错误应该立即失败，不会重试
            assert.ok(result.attempts === undefined || result.attempts === 1, '应该只尝试一次');
        });

        it('应该在达到最大重试次数后失败', async () => {
            const harvester = createHarvester(AbstractHarvester);

            let attempts = 0;

            // Mock _harvestSingleMatch 返回可重试错误
            harvester._harvestSingleMatch = async () => {
                attempts++;
                return { success: false, match_id: 'test', error: 'ERR_CONNECTION_RESET' };
            };

            // Mock NetworkManager
            harvester.networkManager = {
                getWorkerIdentity: () => ({ proxy: { port: 7890 } }),
                forceReassignPort: async () => ({ port: 7891 }),
                sessionManager: { clearSession: async () => {} }
            };

            const result = await harvester.harvestWithRetry({ match_id: 'test' }, 0, 3);

            assert.strictEqual(result.success, false);
            assert.strictEqual(attempts, 3);  // 尝试了 3 次
        });

        it('应该在重试成功后返回', async () => {
            const harvester = createHarvester(AbstractHarvester);

            let attempts = 0;

            // Mock _harvestSingleMatch - 第 2 次成功
            harvester._harvestSingleMatch = async () => {
                attempts++;
                if (attempts === 1) {
                    return { success: false, match_id: 'test', error: 'ERR_CONNECTION_RESET' };
                }
                return { success: true, match_id: 'test', size: 5000 };
            };

            // Mock NetworkManager
            harvester.networkManager = {
                getWorkerIdentity: () => ({ proxy: { port: 7890 } }),
                forceReassignPort: async () => ({ port: 7891 }),
                sessionManager: { clearSession: async () => {} }
            };

            const result = await harvester.harvestWithRetry({ match_id: 'test' }, 0, 3);

            assert.strictEqual(result.success, true);
            assert.strictEqual(attempts, 2);  // 尝试了 2 次
            assert.strictEqual(harvester.stats.retries, 1);  // 重试计数增加
        });

        it('应该在连续 SIZE_TOO_SMALL 时触发冷却', async () => {
            const harvester = createHarvester(AbstractHarvester);

            let attempts = 0;
            let cooldownTriggered = false;

            // Mock _harvestSingleMatch - 连续返回 SIZE_TOO_SMALL
            harvester._harvestSingleMatch = async () => {
                attempts++;
                return { success: false, match_id: 'test', error: 'SIZE_TOO_SMALL:500' };
            };

            // Mock _delay 来检测冷却
            const originalDelay = harvester._delay.bind(harvester);
            harvester._delay = async (ms) => {
                if (ms === 30000) {
                    cooldownTriggered = true;
                } else {
                    await originalDelay(ms);
                }
            };

            // Mock NetworkManager
            harvester.networkManager = {
                getWorkerIdentity: () => ({ proxy: { port: 7890 } }),
                forceReassignPort: async () => ({ port: 7891 }),
                sessionManager: { clearSession: async () => {} }
            };

            const result = await harvester.harvestWithRetry({ match_id: 'test' }, 0, 4);

            assert.strictEqual(cooldownTriggered, true, '应该触发 30 秒冷却');
        });
    });

    // ========================================================================
    // 测试 7: Context 池管理
    // ========================================================================

    describe('Context 池管理', () => {
        it('_cleanupContextPool 应该清理所有 Context', async () => {
            const harvester = createHarvester(AbstractHarvester);

            // Mock Context 池
            const contexts = [];
            for (let i = 1; i <= 3; i++) {
                contexts.push({
                    context: {
                        close: async () => {}
                    }
                });
                harvester._contextPool.set(i, contexts[i - 1]);
            }

            // 执行清理
            await harvester._cleanupContextPool();

            // 验证池已清空
            assert.strictEqual(harvester._contextPool.size, 0, 'Context 池应该被清空');
        });

        it('_evictLRUContext 应该在池子超过上限时淘汰最久未使用的 Context', async () => {
            const harvester = createHarvester(AbstractHarvester);
            harvester._contextPoolMaxSize = 2;

            // 添加 3 个 Context，模拟不同访问时间
            const contexts = [];
            for (let i = 1; i <= 3; i++) {
                const context = {
                    context: {
                        close: async () => {}
                    },
                    lastAccessTime: Date.now() - (i * 1000)
                };
                contexts.push(context);
                harvester._contextPool.set(i, context);
            }

            // 执行 LRU 淘汰
            await harvester._evictLRUContext();

            // 验证最旧的 Context 被淘汰
            assert.strictEqual(harvester._contextPool.size, 2, '应该淘汰 1 个 Context');
            assert.strictEqual(harvester._contextPool.has(3), false, '最久未使用的 Context 应该被淘汰');
            assert.strictEqual(harvester._contextEvictions, 1, '淘汰计数应该增加');
        });

        it('_escape403 应该清理 Cookies', async () => {
            const harvester = createHarvester(AbstractHarvester);

            // Mock Context 池
            const clearCookiesCalled = { called: false };
            harvester._contextPool.set(1, {
                context: {
                    clearCookies: async () => {
                        clearCookiesCalled.called = true;
                    }
                },
                usageCount: 5
            });

            // 执行 403 逃逸
            await harvester._escape403(1);

            // 验证 Cookies 被清理
            assert.strictEqual(clearCookiesCalled.called, true, 'Cookies 应该被清理');

            // 验证 usageCount 被重置
            const entry = harvester._contextPool.get(1);
            assert.strictEqual(entry.usageCount, 0, 'usageCount 应该被重置');
        });

        it('_evictLRUContext 应该在池子未满时不淘汰', async () => {
            const harvester = createHarvester(AbstractHarvester);
            harvester._contextPoolMaxSize = 10;

            // 添加 3 个 Context
            for (let i = 1; i <= 3; i++) {
                harvester._contextPool.set(i, {
                    context: { close: async () => {} },
                    lastAccessTime: Date.now()
                });
            }

            // 执行 LRU 淘汰
            await harvester._evictLRUContext();

            // 验证没有淘汰
            assert.strictEqual(harvester._contextPool.size, 3, '池子未满，不应该淘汰');
        });
    });

    // ========================================================================
    // 测试 8: 工具方法
    // ========================================================================

    describe('工具方法测试', () => {
        it('_delay 应该正确延时', async () => {
            const harvester = createHarvester(AbstractHarvester);
            const start = Date.now();
            await harvester._delay(100);
            const elapsed = Date.now() - start;
            assert.ok(elapsed >= 90, '延时应该接近 100ms'); // 允许 10ms 误差
        });

        it('_randomInRange 应该生成范围内的随机数', () => {
            const harvester = createHarvester(AbstractHarvester);

            for (let i = 0; i < 100; i++) {
                const value = harvester._randomInRange(1, 10);
                assert.ok(value >= 1 && value <= 10, `值 ${value} 应该在 [1, 10] 范围内`);
            }
        });
    });

    // ========================================================================
    // 测试 9: 报告打印
    // ========================================================================

    describe('报告打印', () => {
        it('printReport 应该正确打印统计信息', () => {
            const harvester = createHarvester(AbstractHarvester);

            // 设置统计数据
            harvester.stats = {
                total: 100,
                processed: 95,
                success: 90,
                failed: 5,
                retries: 10,
                sweepRounds: 2
            };

            harvester.startTime = Date.now() - 60000;  // 1 分钟前

            // 执行打印（不应该抛出异常）
            harvester.printReport();

            assert.ok(true);  // 如果没有异常，测试通过
        });

        it('printReport 应该正确处理零数据', () => {
            const harvester = createHarvester(AbstractHarvester);

            // 保持默认统计数据（全为 0）
            harvester.startTime = Date.now();

            // 执行打印（不应该抛出异常）
            harvester.printReport();

            assert.ok(true);
        });
    });

    // ========================================================================
    // 测试 10: 浏览器行为模拟
    // ========================================================================

    describe('浏览器行为模拟', () => {
        it('_injectStealthScripts 应该注入隐身脚本', async () => {
            const harvester = createHarvester(AbstractHarvester);

            // Mock Page
            const addInitScriptCalled = { called: false };
            const mockPage = {
                addInitScript: async (script) => {
                    addInitScriptCalled.called = true;
                    // 验证脚本内容
                    assert.ok(typeof script === 'function', '应该传入函数');
                }
            };

            // 执行注入
            await harvester._injectStealthScripts(mockPage);

            assert.strictEqual(addInitScriptCalled.called, true, 'addInitScript 应该被调用');
        });

        it('_simulateHumanBehavior 应该模拟鼠标移动', async () => {
            const harvester = createHarvester(AbstractHarvester);

            // Mock Page
            const moveCount = { count: 0 };
            const mockPage = {
                mouse: {
                    move: async (x, y, options) => {
                        moveCount.count++;
                    }
                }
            };

            // 执行行为模拟
            await harvester._simulateHumanBehavior(mockPage);

            // 验证鼠标移动次数（应该在 10-15 之间）
            assert.ok(moveCount.count >= 10 && moveCount.count <= 15, '应该有 10-15 次鼠标移动');
        });

        it('_warmupHomepage 应该访问首页', async () => {
            const harvester = createHarvester(AbstractHarvester);

            // Mock Page
            const gotoCalled = { called: false, url: null };
            const mockPage = {
                goto: async (url, options) => {
                    gotoCalled.called = true;
                    gotoCalled.url = url;
                },
                mouse: {
                    wheel: async (x, y) => {}
                },
                waitForTimeout: async (ms) => {}
            };

            // 执行首页预热
            await harvester._warmupHomepage(mockPage, { scrollMore: false, randomScrolls: false });

            // 验证访问了 FotMob 首页
            assert.strictEqual(gotoCalled.called, true, '应该调用 goto');
            assert.ok(gotoCalled.url.includes('fotmob.com'), '应该访问 FotMob 首页');
        });
    });

    // ========================================================================
    // 测试 11: Cookie 加载
    // ========================================================================

    describe('Cookie 加载', () => {
        it('_loadBrowserStateCookies 应该加载有效的 Cookie', async () => {
            const harvester = createHarvester(AbstractHarvester);

            // Mock context
            const cookiesAdded = { cookies: [] };
            const mockContext = {
                addCookies: async (cookies) => {
                    cookiesAdded.cookies = cookies;
                }
            };

            // Mock fs 模块
            const fs = require('fs').promises;
            const originalReadFile = fs.readFile;
            fs.readFile = async (path, encoding) => {
                if (path.includes('browser_state.json')) {
                    return JSON.stringify({
                        cookies: [
                            { name: 'test1', value: 'value1', expires: Date.now() / 1000 + 3600 },
                            { name: 'test2', value: 'value2', expires: Date.now() / 1000 + 3600 }
                        ]
                    });
                }
                return originalReadFile(path, encoding);
            };

            // 执行加载
            const result = await harvester._loadBrowserStateCookies(mockContext);

            // 恢复原始函数
            fs.readFile = originalReadFile;

            // 验证加载成功
            assert.strictEqual(result, true, '应该成功加载 Cookie');
            assert.strictEqual(cookiesAdded.cookies.length, 2, '应该加载 2 个 Cookie');
        });

        it('_loadBrowserStateCookies 应该过滤过期的 Cookie', async () => {
            const harvester = createHarvester(AbstractHarvester);

            // Mock context
            const cookiesAdded = { cookies: [] };
            const mockContext = {
                addCookies: async (cookies) => {
                    cookiesAdded.cookies = cookies;
                }
            };

            // Mock fs 模块
            const fs = require('fs').promises;
            const originalReadFile = fs.readFile;
            fs.readFile = async (path, encoding) => {
                if (path.includes('browser_state.json')) {
                    return JSON.stringify({
                        cookies: [
                            { name: 'expired', value: 'value', expires: Date.now() / 1000 - 3600 },  // 已过期
                            { name: 'valid', value: 'value', expires: Date.now() / 1000 + 3600 }   // 有效
                        ]
                    });
                }
                return originalReadFile(path, encoding);
            };

            // 执行加载
            const result = await harvester._loadBrowserStateCookies(mockContext);

            // 恢复原始函数
            fs.readFile = originalReadFile;

            // 验证只加载了有效的 Cookie
            assert.strictEqual(result, true, '应该成功加载 Cookie');
            assert.strictEqual(cookiesAdded.cookies.length, 1, '应该只加载 1 个有效 Cookie');
            assert.strictEqual(cookiesAdded.cookies[0].name, 'valid', '应该是有效的 Cookie');
        });

        it('_loadBrowserStateCookies 应该在文件不存在时返回 false', async () => {
            const harvester = createHarvester(AbstractHarvester);

            // Mock context
            const mockContext = {
                addCookies: async (cookies) => {}
            };

            // Mock fs 模块
            const fs = require('fs').promises;
            const originalReadFile = fs.readFile;
            fs.readFile = async (path, encoding) => {
                throw new Error('文件不存在');
            };

            // 执行加载
            const result = await harvester._loadBrowserStateCookies(mockContext);

            // 恢复原始函数
            fs.readFile = originalReadFile;

            // 验证返回 false
            assert.strictEqual(result, false, '文件不存在时应该返回 false');
        });
    });

    // ========================================================================
    // 测试 12: AutoAuthManager 测试
    // ========================================================================

    describe('AutoAuthManager 测试', () => {
        it('应该使用默认配置创建实例', () => {
            const manager = new AutoAuthManager();
            assert.strictEqual(manager.config.headless, false);  // 默认可见
            assert.strictEqual(manager.config.timeout, 60000);
            assert.ok(manager.config.targetUrl.includes('fotmob.com'));
        });

        it('应该覆盖默认配置', () => {
            const manager = new AutoAuthManager({
                headless: true,
                timeout: 30000,
                targetUrl: 'https://example.com'
            });
            assert.strictEqual(manager.config.headless, true);
            assert.strictEqual(manager.config.timeout, 30000);
            assert.strictEqual(manager.config.targetUrl, 'https://example.com');
        });

        it('launchBrowser 应该成功启动', async () => {
            const manager = new AutoAuthManager({ headless: true });

            // 执行启动
            await manager.launchBrowser();

            // 验证浏览器已启动
            assert.ok(manager.browser !== null, '浏览器应该已启动');

            // 清理
            await manager.cleanup();
        });

        it('createContext 应该在浏览器未启动时抛出错误', async () => {
            const manager = new AutoAuthManager();

            try {
                await manager.createContext();
                assert.fail('应该抛出错误');
            } catch (error) {
                assert.ok(error.message.includes('浏览器未启动'));
            }
        });

        it('createPage 应该在上下文未创建时抛出错误', async () => {
            const manager = new AutoAuthManager();

            try {
                await manager.createPage();
                assert.fail('应该抛出错误');
            } catch (error) {
                assert.ok(error.message.includes('上下文未创建'));
            }
        });
    });
});
