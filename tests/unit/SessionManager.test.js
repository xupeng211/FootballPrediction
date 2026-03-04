/**
 * SessionManager 单元测试
 * ==============================
 *
 * 测试 V179 SessionManager 核心功能：
 * - 刷新锁机制
 * - 会话过期检测
 * - 指数退避
 * - 身份热加载
 *
 * @module tests/unit/SessionManager.test
 */

'use strict';

const { describe, it, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert');
const { SessionManager, resetSingleton, DEFAULT_CONFIG } = require('../../src/infrastructure/network/SessionManager');

// ============================================================================
// Mock 和辅助函数
// ============================================================================

/**
 * 创建模拟的 SessionManager（不初始化文件系统）
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
    beforeEach(() => {
        resetSingleton();
    });

    afterEach(() => {
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
            const start = Date.now();

            await manager._delay(100);

            const elapsed = Date.now() - start;
            assert.ok(elapsed >= 90, `延时应该 >= 100ms，实际 ${elapsed}ms`);
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
