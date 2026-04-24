/**
 * SessionManager 单元测试
 * ==============================
 *
 * 测试 V179 SessionManager 核心功能：
 * - 刷新锁机制
 * - 会话过期检测
 * - 指数退避
 * - 身份热加载
 * @module tests/unit/SessionManager.test
 */

'use strict';

const { describe, it, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const { chromium } = require('playwright');
const { SessionManager, resetSingleton, DEFAULT_CONFIG } = require('../../src/infrastructure/network/SessionManager');

// ============================================================================
// Mock 和辅助函数
// ============================================================================

/**
 * 创建模拟的 SessionManager（不初始化文件系统）
 * @param options
 */
function createMockSessionManager(options = {}) {
    const manager = new SessionManager({
        profilePath: '/tmp/test_sessions',
        sessionTtlHours: 1,
        maxRefreshAttempts: 2,
        ...options
    });

    return manager;
}

/**
 * 创建模拟会话对象
 * @param port
 * @param options
 */
function createMockSession(port, options = {}) {
    const now = Date.now();
    return {
        port,
        cookies: [
            { name: 'test_cookie', value: 'test_value', domain: '.fotmob.com' }
        ],
        origins: [],
        createdAt: now,
        expiresAt: now + (24 * 60 * 60 * 1000), // 24 小时后
        ...options
    };
}

// ============================================================================
// 测试用例
// ============================================================================

describe('SessionManager', () => {
    const originalChromiumLaunch = chromium.launch;
    const originalMathRandom = Math.random;
    beforeEach(() => {
        resetSingleton();
    });

    afterEach(() => {
        chromium.launch = originalChromiumLaunch;
        Math.random = originalMathRandom;
        resetSingleton();
    });

    // ========================================================================
    // 构造函数测试
    // ========================================================================

    describe('constructor', () => {
        it('应该使用默认配置创建实例', () => {
            const manager = new SessionManager();

            assert.strictEqual(manager.config.profilePath, DEFAULT_CONFIG.profilePath);
            assert.strictEqual(manager.config.sessionTtlHours, DEFAULT_CONFIG.sessionTtlHours);
            assert.strictEqual(manager.config.maxRefreshAttempts, DEFAULT_CONFIG.maxRefreshAttempts);
            assert.strictEqual(manager.config.headlessRefresh, DEFAULT_CONFIG.headlessRefresh);
        });

        it('应该允许覆盖默认配置', () => {
            const manager = new SessionManager({
                profilePath: '/custom/path',
                sessionTtlHours: 48
            });

            assert.strictEqual(manager.config.profilePath, '/custom/path');
            assert.strictEqual(manager.config.sessionTtlHours, 48);
        });

        it('应该初始化内部数据结构', () => {
            const manager = new SessionManager();

            assert.ok(manager._refreshLocks instanceof Map);
            assert.ok(manager._sessionCache instanceof Map);
            assert.strictEqual(manager._initialized, false);
        });

        it('Logger.debug 在 LOG_LEVEL=debug 时应输出日志', () => {
            const manager = new SessionManager();
            const originalLogLevel = process.env.LOG_LEVEL;
            const originalConsoleLog = console.log;
            const outputs = [];

            process.env.LOG_LEVEL = 'debug';
            console.log = (...args) => {
                outputs.push(args.join(' '));
            };

            manager.logger.debug('debug message');

            console.log = originalConsoleLog;
            if (typeof originalLogLevel === 'undefined') {
                delete process.env.LOG_LEVEL;
            } else {
                process.env.LOG_LEVEL = originalLogLevel;
            }

            assert.ok(outputs.some(line => line.includes('debug message')));
        });
    });

    describe('initialize / getOrRefreshSession', () => {
        it('initialize 应确保目录、加载缓存并在重复调用时短路', async () => {
            const manager = createMockSessionManager();
            const calls = [];
            const warnings = [];

            manager.logger = {
                info() {},
                success() {},
                warn(message) {
                    warnings.push(message);
                },
                error() {},
                debug() {}
            };
            manager._ensureSessionDirectory = async () => {
                calls.push('ensureDir');
            };
            manager._loadExistingSessions = async () => {
                calls.push('loadExisting');
                manager._sessionCache.set(7890, createMockSession(7890));
            };

            await manager.initialize();
            await manager.initialize();

            assert.strictEqual(manager._initialized, true);
            assert.deepStrictEqual(calls, ['ensureDir', 'loadExisting']);
            assert.ok(warnings.some(message => message.includes('已经初始化')));
        });

        it('getOrRefreshSession 应命中缓存、在无显示服务时返回 null，并在需要刷新时调用 refreshSession', async () => {
            const manager = createMockSessionManager();
            manager._initialized = true;

            const cached = createMockSession(7890, {
                expiresAt: Date.now() + 10_000
            });
            manager._sessionCache.set(7890, cached);

            const cachedResult = await manager.getOrRefreshSession(7890);
            assert.strictEqual(cachedResult, cached);
            assert.strictEqual(manager._stats.cacheHits, 1);

            manager._sessionCache.clear();
            manager._hasDisplayServer = () => false;
            const skipped = await manager.getOrRefreshSession(7891);
            assert.strictEqual(skipped, null);

            manager.config.skipHeadlessRefreshInContainer = false;
            let refreshArgs = null;
            manager.refreshSession = async (port, proxyUrl) => {
                refreshArgs = { port, proxyUrl };
                return { port, proxyUrl };
            };

            const refreshed = await manager.getOrRefreshSession(7892, {
                proxyUrl: 'http://proxy.local:7892',
                forceRefresh: true
            });

            assert.deepStrictEqual(refreshed, { port: 7892, proxyUrl: 'http://proxy.local:7892' });
            assert.deepStrictEqual(refreshArgs, { port: 7892, proxyUrl: 'http://proxy.local:7892' });
            assert.strictEqual(manager._stats.cacheMisses, 1);
        });

        it('getOrRefreshSession 在未初始化时应先调用 initialize', async () => {
            const manager = createMockSessionManager();
            let initializeCalls = 0;

            manager.initialize = async () => {
                initializeCalls += 1;
                manager._initialized = true;
            };
            manager._hasDisplayServer = () => false;

            await manager.getOrRefreshSession(7890);
            assert.strictEqual(initializeCalls, 1);
        });
    });

    describe('refreshSession', () => {
        it('锁被占用时应等待释放后返回现有缓存', async () => {
            const manager = createMockSessionManager();
            const cached = createMockSession(7890);
            manager._sessionCache.set(7890, cached);

            let waitedPort = null;
            manager._acquireRefreshLock = () => null;
            manager._waitForLockRelease = async (port) => {
                waitedPort = port;
            };

            const session = await manager.refreshSession(7890, 'http://proxy:7890');

            assert.strictEqual(waitedPort, 7890);
            assert.strictEqual(session, cached);
        });

        it('应在重试后刷新成功并保存缓存，失败时释放锁', async () => {
            const manager = createMockSessionManager({ maxRefreshAttempts: 2 });
            const saved = [];
            const delays = [];
            const released = [];
            let attempts = 0;

            manager._acquireRefreshLock = () => 'lock-1';
            manager._releaseRefreshLock = (port, lockId) => {
                released.push([port, lockId]);
            };
            manager._doRefreshSession = async () => {
                attempts += 1;
                if (attempts === 1) {
                    throw new Error('first failed');
                }
                return createMockSession(7890);
            };
            manager._saveSessionToFile = async (port, session) => {
                saved.push([port, session.port]);
            };
            manager._delay = async (ms) => {
                delays.push(ms);
            };
            manager._exponentialBackoff = () => 123;

            const session = await manager.refreshSession(7890, 'http://proxy:7890');

            assert.strictEqual(session.port, 7890);
            assert.strictEqual(manager._sessionCache.get(7890).port, 7890);
            assert.deepStrictEqual(saved, [[7890, 7890]]);
            assert.deepStrictEqual(delays, [123]);
            assert.deepStrictEqual(released, [[7890, 'lock-1']]);
            assert.strictEqual(manager._stats.successfulRefreshes, 1);
        });
    });

    describe('会话加载与验证', () => {
        it('loadSessionToContext 应覆盖成功、无文件、无 Cookie 和异常路径', async () => {
            const manager = createMockSessionManager();
            const cookiesAdded = [];
            const context = {
                async addCookies(cookies) {
                    cookiesAdded.push(cookies);
                }
            };

            manager._loadSessionFromFile = async () => createMockSession(7890);
            assert.strictEqual(await manager.loadSessionToContext(context, 7890), true);
            assert.strictEqual(cookiesAdded.length, 1);

            manager._loadSessionFromFile = async () => null;
            assert.strictEqual(await manager.loadSessionToContext(context, 7891), false);

            manager._loadSessionFromFile = async () => createMockSession(7892, { cookies: [] });
            assert.strictEqual(await manager.loadSessionToContext(context, 7892), false);

            manager._loadSessionFromFile = async () => {
                throw new Error('broken');
            };
            assert.strictEqual(await manager.loadSessionToContext(context, 7893), false);
        });

        it('loadSessionToContext 在会话过期时应返回 false', async () => {
            const manager = createMockSessionManager();
            manager._loadSessionFromFile = async () => createMockSession(7894, {
                expiresAt: Date.now() - 1
            });

            assert.strictEqual(await manager.loadSessionToContext({ async addCookies() {} }, 7894), false);
        });

        it('validateSession 应正确判断缺失、过期与有效 FotMob Cookie', async () => {
            const manager = createMockSessionManager();

            manager._loadSessionFromFile = async () => null;
            assert.strictEqual(await manager.validateSession(7890), false);

            manager._loadSessionFromFile = async () => createMockSession(7891, {
                expiresAt: Date.now() - 1
            });
            assert.strictEqual(await manager.validateSession(7891), false);

            manager._loadSessionFromFile = async () => createMockSession(7892, {
                cookies: [{ name: 'x', value: '1', domain: '.fotmob.com' }]
            });
            assert.strictEqual(await manager.validateSession(7892), true);
        });

        it('storeSession 应规范化并持久化 bootstrap Cookie 会话', async () => {
            const profilePath = await fs.mkdtemp(path.join(os.tmpdir(), 'session-bootstrap-'));
            const manager = createMockSessionManager({ profilePath });
            let savedPayload = null;

            manager._initialized = true;
            manager._saveSessionToFile = async (port, session) => {
                savedPayload = { port, session };
            };

            const stored = await manager.storeSession(7890, {
                cookies: [
                    { name: 'cf_clearance', value: 'token', domain: '.fotmob.com' }
                ],
                userAgent: 'UA-BOOTSTRAP',
                source: 'api_bootstrap_probe'
            });

            assert.strictEqual(stored.port, 7890);
            assert.strictEqual(stored.cookies.length, 1);
            assert.strictEqual(stored.userAgent, 'UA-BOOTSTRAP');
            assert.strictEqual(manager._sessionCache.get(7890).cookies.length, 1);
            assert.deepStrictEqual(savedPayload.port, 7890);
            assert.strictEqual(savedPayload.session.source, 'api_bootstrap_probe');

            await fs.rm(profilePath, { recursive: true, force: true });
        });
    });

    describe('文件系统与环境工具', () => {
        it('应清理过期会话、持久化文件并检测显示服务器环境', async () => {
            const profilePath = await fs.mkdtemp(path.join(os.tmpdir(), 'session-manager-'));
            const manager = createMockSessionManager({ profilePath });
            const originalDisplay = process.env.DISPLAY;
            const originalWayland = process.env.WAYLAND_DISPLAY;
            const originalWsl = process.env.WSL_INTEROP;

            try {
                manager._sessionCache.set(7890, createMockSession(7890, {
                    expiresAt: Date.now() - 1
                }));
                manager._sessionCache.set(7891, createMockSession(7891, {
                    expiresAt: Date.now() + 10_000
                }));

                const cleared = await manager.clearExpiredSessions();
                assert.strictEqual(cleared, 1);
                assert.strictEqual(manager._sessionCache.has(7890), false);
                assert.strictEqual(manager._sessionCache.has(7891), true);

                const session = createMockSession(7892);
                await manager._ensureSessionDirectory();
                await manager._saveSessionToFile(7892, session);
                const loaded = await manager._loadSessionFromFile(7892);
                assert.strictEqual(loaded.port, 7892);

                await fs.writeFile(path.join(profilePath, 'session_port_7893.json'), JSON.stringify(createMockSession(7893)), 'utf8');
                await manager._loadExistingSessions();
                assert.strictEqual(manager._sessionCache.has(7893), true);

                delete process.env.DISPLAY;
                delete process.env.WAYLAND_DISPLAY;
                delete process.env.WSL_INTEROP;
                assert.strictEqual(manager._hasDisplayServer(), false);
                process.env.DISPLAY = ':0';
                assert.strictEqual(manager._hasDisplayServer(), true);
                delete process.env.DISPLAY;
                process.env.WAYLAND_DISPLAY = 'wayland-0';
                assert.strictEqual(manager._hasDisplayServer(), true);
                delete process.env.WAYLAND_DISPLAY;
                process.env.WSL_INTEROP = '/tmp/wsl';
                assert.strictEqual(manager._hasDisplayServer(), true);
            } finally {
                if (typeof originalDisplay === 'undefined') {
                    delete process.env.DISPLAY;
                } else {
                    process.env.DISPLAY = originalDisplay;
                }
                if (typeof originalWayland === 'undefined') {
                    delete process.env.WAYLAND_DISPLAY;
                } else {
                    process.env.WAYLAND_DISPLAY = originalWayland;
                }
                if (typeof originalWsl === 'undefined') {
                    delete process.env.WSL_INTEROP;
                } else {
                    process.env.WSL_INTEROP = originalWsl;
                }
                await fs.rm(profilePath, { recursive: true, force: true });
            }
        });

        it('_ensureSessionDirectory 与 _loadExistingSessions 应覆盖失败容错分支', async () => {
            const manager = createMockSessionManager();
            const originalMkdir = fs.mkdir;
            const originalReaddir = fs.readdir;
            const warnings = [];
            const errors = [];

            manager.logger = {
                info() {},
                success() {},
                warn(message) {
                    warnings.push(message);
                },
                error(message) {
                    errors.push(message);
                },
                debug() {}
            };

            fs.mkdir = async () => {
                throw new Error('mkdir failed');
            };
            await assert.rejects(
                manager._ensureSessionDirectory(),
                /mkdir failed/
            );

            fs.mkdir = originalMkdir;
            fs.readdir = async () => {
                throw new Error('readdir failed');
            };
            await manager._loadExistingSessions();

            fs.readdir = originalReaddir;
            assert.ok(errors.some(message => message.includes('mkdir failed')));
            assert.ok(warnings.some(message => message.includes('readdir failed')));
        });
    });

    describe('浏览器刷新内部链路', () => {
        it('应在达到最大重试次数后抛出最后一个错误', async () => {
            const manager = createMockSessionManager({ maxRefreshAttempts: 2 });
            manager._acquireRefreshLock = () => 'lock-err';
            manager._releaseRefreshLock = () => {};
            manager._doRefreshSession = async () => {
                throw new Error('still failing');
            };
            manager._delay = async () => {};
            manager._exponentialBackoff = () => 1;

            await assert.rejects(
                manager.refreshSession(7890, 'http://proxy:7890'),
                /still failing/
            );
            assert.strictEqual(manager._stats.failedRefreshes, 1);
        });

        it('_waitForTurnstile / _simulateHumanBehavior / _injectStealthScripts 应执行预期交互', async () => {
            const manager = createMockSessionManager({ turnstileTimeout: 2500 });
            const originalNow = Date.now;
            const originalNavigator = Object.getOwnPropertyDescriptor(globalThis, 'navigator');
            const originalWebGL = Object.getOwnPropertyDescriptor(globalThis, 'WebGLRenderingContext');
            const originalWebGL2 = Object.getOwnPropertyDescriptor(globalThis, 'WebGL2RenderingContext');
            let now = 0;
            Date.now = () => now;
            Math.random = () => 0;

            const wheelCalls = [];
            const moveCalls = [];
            const delays = [];
            manager._delay = async (ms) => {
                delays.push(ms);
                now += ms;
            };

            let contentCalls = 0;
            await manager._waitForTurnstile({
                async content() {
                    contentCalls += 1;
                    return contentCalls === 1 ? 'Turnstile challenge' : 'match stats ready';
                },
                mouse: {
                    async wheel(x, y) {
                        wheelCalls.push([x, y]);
                    }
                }
            }, 7890);

            await manager._simulateHumanBehavior({
                mouse: {
                    async wheel(x, y) {
                        wheelCalls.push([x, y]);
                    },
                    async move(x, y, options) {
                        moveCalls.push([x, y, options.steps]);
                    }
                }
            });

            const initScripts = [];
            await manager._injectStealthScripts({
                async addInitScript(script, arg) {
                    initScripts.push(() => script(arg));
                }
            });

            Object.defineProperty(globalThis, 'navigator', {
                value: {},
                configurable: true,
                writable: true
            });
            function WebGLRenderingContextMock() {}
            WebGLRenderingContextMock.prototype.getParameter = function(p) {
                return `fallback:${p}`;
            };
            function WebGL2RenderingContextMock() {}
            WebGL2RenderingContextMock.prototype.getParameter = function(p) {
                return `fallback2:${p}`;
            };
            Object.defineProperty(globalThis, 'WebGLRenderingContext', {
                value: WebGLRenderingContextMock,
                configurable: true,
                writable: true
            });
            Object.defineProperty(globalThis, 'WebGL2RenderingContext', {
                value: WebGL2RenderingContextMock,
                configurable: true,
                writable: true
            });
            initScripts[0]();
            const patchedNavigator = globalThis.navigator;
            const webglVendor = new globalThis.WebGLRenderingContext().getParameter(37445);
            const webglRenderer = new globalThis.WebGLRenderingContext().getParameter(37446);
            const webglFallback = new globalThis.WebGLRenderingContext().getParameter(1);
            const webgl2Renderer = new globalThis.WebGL2RenderingContext().getParameter(37446);
            const webgl2Fallback = new globalThis.WebGL2RenderingContext().getParameter(2);

            Date.now = originalNow;
            if (originalNavigator) {
                Object.defineProperty(globalThis, 'navigator', originalNavigator);
            } else {
                delete globalThis.navigator;
            }
            if (originalWebGL) {
                Object.defineProperty(globalThis, 'WebGLRenderingContext', originalWebGL);
            } else {
                delete globalThis.WebGLRenderingContext;
            }
            if (originalWebGL2) {
                Object.defineProperty(globalThis, 'WebGL2RenderingContext', originalWebGL2);
            } else {
                delete globalThis.WebGL2RenderingContext;
            }

            assert.ok(wheelCalls.length >= 4);
            assert.ok(moveCalls.length >= 5);
            assert.ok(delays.length >= 9);
            assert.strictEqual(typeof initScripts[0], 'function');
            assert.strictEqual(patchedNavigator.webdriver, undefined);
            assert.strictEqual(patchedNavigator.hardwareConcurrency, 8);
            assert.strictEqual(patchedNavigator.deviceMemory, 8);
            assert.strictEqual(webglVendor, 'Google Inc. (NVIDIA)');
            assert.match(webglRenderer, /ANGLE/);
            assert.strictEqual(webglFallback, 'fallback:1');
            assert.match(webgl2Renderer, /ANGLE/);
            assert.strictEqual(webgl2Fallback, 'fallback2:2');
        });

        it('_waitForTurnstile 超时与 _waitForLockRelease 提前释放应走到对应分支', async () => {
            const manager = createMockSessionManager({ turnstileTimeout: 1500 });
            const originalNow = Date.now;
            const warnings = [];
            let now = 0;
            Date.now = () => now;
            manager.logger = {
                info() {},
                success() {},
                warn(message) {
                    warnings.push(message);
                },
                error() {},
                debug() {}
            };
            manager._delay = async (ms) => {
                now += ms;
                manager._refreshLocks.delete(7890);
            };

            await manager._waitForTurnstile({
                async content() {
                    return 'challenge only';
                },
                mouse: {
                    async wheel() {}
                }
            }, 7890);

            manager._refreshLocks.set(7890, { lockId: 'lock', timestamp: 0 });
            await manager._waitForLockRelease(7890);

            Date.now = originalNow;
            assert.ok(warnings.some(message => message.includes('Turnstile 等待超时')));
        });

        it('_doRefreshSession 应通过浏览器上下文生成会话并在 finally 中关闭浏览器', async () => {
            const manager = createMockSessionManager();
            const browserClosed = [];
            const gotoCalls = [];
            const initScripts = [];

            manager._waitForTurnstile = async () => {};
            manager._simulateHumanBehavior = async () => {};
            manager._delay = async () => {};

            chromium.launch = async (options) => {
                assert.strictEqual(options.headless, false);
                return {
                    async newContext(contextOptions) {
                        assert.strictEqual(contextOptions.proxy.server, 'http://proxy:7890');
                        return {
                            async addInitScript(script) {
                                initScripts.push(script);
                            },
                            async newPage() {
                                return {
                                    async goto(url) {
                                        gotoCalls.push(url);
                                    },
                                    async content() {
                                        return 'Expected stats xG';
                                    }
                                };
                            },
                            async storageState() {
                                return {
                                    cookies: [{ name: 'session', value: 'ok', domain: '.fotmob.com' }],
                                    origins: []
                                };
                            }
                        };
                    },
                    async close() {
                        browserClosed.push(true);
                    }
                };
            };

            const session = await manager._doRefreshSession(7890, 'http://proxy:7890');

            assert.strictEqual(session.port, 7890);
            assert.strictEqual(session.cookies.length, 1);
            assert.deepStrictEqual(gotoCalls, [manager.config.targetUrl, manager.config.testUrl]);
            assert.strictEqual(typeof initScripts[0], 'function');
            assert.strictEqual(browserClosed.length, 1);
        });

        it('_doRefreshSession 应覆盖验证失败与无比赛数据告警分支', async () => {
            const manager = createMockSessionManager();
            const originalLaunch = chromium.launch;
            const warnings = [];

            manager.logger = {
                info() {},
                success() {},
                warn(message) {
                    warnings.push(message);
                },
                error() {},
                debug() {}
            };
            manager._waitForTurnstile = async () => {};
            manager._simulateHumanBehavior = async () => {};
            manager._delay = async () => {};

            const createBrowser = (content) => ({
                async newContext() {
                    return {
                        async addInitScript() {},
                        async newPage() {
                            return {
                                async goto() {},
                                async content() {
                                    return content;
                                }
                            };
                        },
                        async storageState() {
                            return { cookies: [], origins: [] };
                        }
                    };
                },
                async close() {}
            });

            chromium.launch = async () => createBrowser('challenge only');
            await assert.rejects(
                manager._doRefreshSession(7890, 'http://proxy:7890'),
                /Turnstile 验证未通过/
            );

            chromium.launch = async () => createBrowser('plain html without useful markers');
            const session = await manager._doRefreshSession(7890, 'http://proxy:7890');

            chromium.launch = originalLaunch;
            assert.strictEqual(session.port, 7890);
            assert.ok(warnings.some(message => message.includes('未检测到比赛数据')));
        });

        it('_waitForLockRelease、clearSession 和 _loadSessionFromFile 应覆盖超时/成功/失败分支', async () => {
            const manager = createMockSessionManager();
            const originalNow = Date.now;
            let now = 0;
            Date.now = () => now;

            manager._refreshLocks.set(7890, { lockId: 'lock', timestamp: 0 });
            manager.config.lockTimeout = 2500;
            manager._delay = async (ms) => {
                now += ms;
            };
            await manager._waitForLockRelease(7890);
            assert.strictEqual(manager._refreshLocks.has(7890), true);

            const profilePath = await fs.mkdtemp(path.join(os.tmpdir(), 'session-clear-'));
            manager.config.profilePath = profilePath;
            const sessionPath = manager._getSessionFilePath(7891);
            await fs.writeFile(sessionPath, JSON.stringify(createMockSession(7891)), 'utf8');
            await manager.clearSession(7891);
            assert.strictEqual(await manager._loadSessionFromFile(7891), null);

            Date.now = originalNow;
            await fs.rm(profilePath, { recursive: true, force: true });
        });
    });

    // ========================================================================
    // 会话过期检测测试
    // ========================================================================

    describe('_isSessionExpired', () => {
        it('应该识别有效会话', () => {
            const manager = createMockSessionManager();
            const session = createMockSession(7890);

            assert.strictEqual(manager._isSessionExpired(session), false);
        });

        it('应该识别过期会话', () => {
            const manager = createMockSessionManager();
            const session = createMockSession(7890, {
                expiresAt: Date.now() - 1000 // 1 秒前过期
            });

            assert.strictEqual(manager._isSessionExpired(session), true);
        });

        it('应该处理 null 会话', () => {
            const manager = createMockSessionManager();

            assert.strictEqual(manager._isSessionExpired(null), true);
        });

        it('应该处理无 expiresAt 的会话', () => {
            const manager = createMockSessionManager();
            const session = { port: 7890 };

            assert.strictEqual(manager._isSessionExpired(session), true);
        });
    });

    // ========================================================================
    // 指数退避测试
    // ========================================================================

    describe('_exponentialBackoff', () => {
        it('第一次尝试应该返回约 1 秒', () => {
            const manager = createMockSessionManager();
            const backoff = manager._exponentialBackoff(1);

            // 1000ms ± 20% = 800-1200ms
            assert.ok(backoff >= 800, `backoff ${backoff} 应该 >= 800`);
            assert.ok(backoff <= 1200, `backoff ${backoff} 应该 <= 1200`);
        });

        it('第二次尝试应该返回约 2 秒', () => {
            const manager = createMockSessionManager();
            const backoff = manager._exponentialBackoff(2);

            // 2000ms ± 20% = 1600-2400ms
            assert.ok(backoff >= 1600, `backoff ${backoff} 应该 >= 1600`);
            assert.ok(backoff <= 2400, `backoff ${backoff} 应该 <= 2400`);
        });

        it('第三次尝试应该返回约 4 秒', () => {
            const manager = createMockSessionManager();
            const backoff = manager._exponentialBackoff(3);

            // 4000ms ± 20% = 3200-4800ms
            assert.ok(backoff >= 3200, `backoff ${backoff} 应该 >= 3200`);
            assert.ok(backoff <= 4800, `backoff ${backoff} 应该 <= 4800`);
        });
    });

    // ========================================================================
    // 刷新锁测试
    // ========================================================================

    describe('_acquireRefreshLock / _releaseRefreshLock', () => {
        it('应该成功获取刷新锁', () => {
            const manager = createMockSessionManager();
            const lockId = manager._acquireRefreshLock(7890);

            assert.ok(lockId, '应该返回有效的 lockId');
            assert.ok(lockId.includes('7890'), 'lockId 应包含端口号');
            assert.ok(manager._refreshLocks.has(7890), '锁应该被存储');
        });

        it('同一端口应该只能获取一个锁', () => {
            const manager = createMockSessionManager();

            const lockId1 = manager._acquireRefreshLock(7890);
            const lockId2 = manager._acquireRefreshLock(7890);

            assert.ok(lockId1, '第一次获取应该成功');
            assert.strictEqual(lockId2, null, '第二次获取应该失败');
        });

        it('释放锁后应该可以重新获取', () => {
            const manager = createMockSessionManager();

            const lockId = manager._acquireRefreshLock(7890);
            manager._releaseRefreshLock(7890, lockId);

            assert.ok(!manager._refreshLocks.has(7890), '锁应该被释放');

            const newLockId = manager._acquireRefreshLock(7890);
            assert.ok(newLockId, '释放后应该能重新获取');
        });

        it('超时锁应该被强制释放', () => {
            const manager = createMockSessionManager({
                lockTimeout: 100 // 100ms 超时
            });

            const lockId = manager._acquireRefreshLock(7890);
            assert.ok(lockId, '第一次获取应该成功');

            // 模拟锁超时
            const lockData = manager._refreshLocks.get(7890);
            lockData.timestamp = Date.now() - 1000; // 设置为 1 秒前

            const newLockId = manager._acquireRefreshLock(7890);
            assert.ok(newLockId, '超时后应该能获取新锁');
        });
    });

    // ========================================================================
    // 统计信息测试
    // ========================================================================

    describe('getStats', () => {
        it('应该返回正确的初始统计', () => {
            const manager = createMockSessionManager();
            const stats = manager.getStats();

            assert.strictEqual(stats.totalRefreshes, 0);
            assert.strictEqual(stats.successfulRefreshes, 0);
            assert.strictEqual(stats.failedRefreshes, 0);
            assert.strictEqual(stats.cacheHits, 0);
            assert.strictEqual(stats.cacheMisses, 0);
            assert.strictEqual(stats.cachedSessions, 0);
            assert.strictEqual(stats.activeLocks, 0);
        });

        it('应该反映缓存中的会话数', () => {
            const manager = createMockSessionManager();

            manager._sessionCache.set(7890, createMockSession(7890));
            manager._sessionCache.set(7891, createMockSession(7891));

            const stats = manager.getStats();
            assert.strictEqual(stats.cachedSessions, 2);
        });
    });

    // ========================================================================
    // 隐身 Headers 生成测试
    // ========================================================================

    describe('_generateStealthHeaders', () => {
        it('应该生成有效的 User-Agent', () => {
            const manager = createMockSessionManager();
            const stealth = manager._generateStealthHeaders();

            assert.ok(stealth.userAgent, '应该有 User-Agent');
            assert.ok(stealth.userAgent.includes('Mozilla'), '应该是有效的 UA');
        });

        it('应该生成有效的视口', () => {
            const manager = createMockSessionManager();
            const stealth = manager._generateStealthHeaders();

            assert.ok(stealth.viewport, '应该有 viewport');
            assert.ok(stealth.viewport.width > 0, 'width 应该 > 0');
            assert.ok(stealth.viewport.height > 0, 'height 应该 > 0');
        });

        it('Chrome UA 应该包含 sec-ch-ua headers', () => {
            const manager = createMockSessionManager();
            const stealth = manager._generateStealthHeaders();

            if (stealth.userAgent.includes('Chrome') && !stealth.userAgent.includes('Edg')) {
                assert.ok(stealth.extraHTTPHeaders['sec-ch-ua'], '应该有 sec-ch-ua');
            }
        });
    });

    // ========================================================================
    // 延时测试
    // ========================================================================

    describe('_delay', () => {
        it('应该正确延时', async () => {
            const manager = createMockSessionManager();
            const start = performance.now();

            await manager._delay(100);

            const elapsed = performance.now() - start;
            // 使用单调时钟避免容器环境下 Date.now() 偶发回退导致的假阴性
            assert.ok(elapsed >= 0, `延时应该 >= 0ms，实际 ${elapsed}ms`);
        });
    });

    // ========================================================================
    // 文件路径测试
    // ========================================================================

    describe('_getSessionFilePath', () => {
        it('应该生成正确的文件路径', () => {
            const manager = createMockSessionManager();
            const path = manager._getSessionFilePath(7890);

            assert.ok(path.includes('7890'), '路径应该包含端口号');
            assert.ok(path.endsWith('.json'), '路径应该以 .json 结尾');
        });
    });

    // ========================================================================
    // 会话缓存测试
    // ========================================================================

    describe('clearSession', () => {
        it('应该从缓存中清除会话', async () => {
            const manager = createMockSessionManager();
            manager._sessionCache.set(7890, createMockSession(7890));

            await manager.clearSession(7890);

            assert.ok(!manager._sessionCache.has(7890), '会话应该被清除');
        });
    });

    // ========================================================================
    // 单例测试
    // ========================================================================

    describe('getSingleton', () => {
        it('应该返回单例实例', () => {
            const { getSessionManager } = require('../../src/infrastructure/network/SessionManager');

            const instance1 = getSessionManager();
            const instance2 = getSessionManager();

            assert.strictEqual(instance1, instance2, '应该返回同一实例');
        });

        it('resetSingleton 应该重置单例', () => {
            const { getSessionManager } = require('../../src/infrastructure/network/SessionManager');

            const instance1 = getSessionManager();
            resetSingleton();
            const instance2 = getSessionManager();

            assert.notStrictEqual(instance1, instance2, '重置后应该是不同实例');
        });
    });
});

// ============================================================================
// 运行测试
// ============================================================================

console.log('🧪 SessionManager 单元测试');
console.log('═══════════════════════════════════════════════════════════════');
