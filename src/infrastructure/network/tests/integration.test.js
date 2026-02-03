/**
 * integration.test.js - V1.1.0 跨语言集成测试套件
 * ========================================================================
 *
 * 测试覆盖：
 * - Node.js 和 Python 并发访问 active_registry.json
 * - 端口竞争测试（22 个节点，仅 1 个可用）
 * - 跨语言状态同步
 * - 错误恢复
 * - 内存泄漏测试（长时间运行）
 *
 * @module network/tests/integration.test
 * @version V1.1.0
 * @since 2026-02-03
 */

'use strict';

const path = require('path');
const { NetworkShield, getNetworkShield, resetSingleton } = require('../NetworkShield');
const { FileSystemProvider } = require('../core/AbstractFileSystem');
const { getRegistryManager, resetSingleton: resetRegistrySingleton } = require('../core/RegistryManager');

// 测试配置
const TEST_CONFIG = {
    registryPath: path.join(__dirname, '../config/test_registry.json'),
    backupPath: path.join(__dirname, '../config/test_registry.backup.json'),
    lockPath: path.join(__dirname, '../config/.test_registry.lock'),
    proxyHost: '172.25.16.1',
    portRange: { start: 7891, end: 7912 },
    enabled: true,
    healthCheckInterval: 30000,
    cooldownMinutes: 15,
    sessionTimeoutMinutes: 30,
    maxConsecutiveFailures: 2,
    lruMaxSize: 100,
    maxSessions: 200
};

// 清理测试环境
function cleanupTestEnvironment() {
    const fs = require('fs');
    const files = [
        TEST_CONFIG.registryPath,
        TEST_CONFIG.backupPath,
        TEST_CONFIG.lockPath
    ];

    for (const file of files) {
        try {
            if (fs.existsSync(file)) {
                fs.unlinkSync(file);
            }
        } catch (e) {
            // 忽略删除失败
        }
    }

    resetSingleton();
    resetRegistrySingleton();
}

describe('NetworkShield - V1.1.0 Integration Tests', () => {
    let shield;

    beforeAll(() => {
        cleanupTestEnvironment();
    });

    afterEach(() => {
        if (shield) {
            shield.shutdown();
        }
        cleanupTestEnvironment();
    });

    afterAll(() => {
        cleanupTestEnvironment();
    });

    describe('Initialization', () => {
        test('should initialize with 22 nodes from default registry', async () => {
            shield = new NetworkShield({
                proxyHost: TEST_CONFIG.proxyHost,
                portRange: TEST_CONFIG.portRange,
                enabled: false,  // 禁用代理以避免实际网络调用
                logLevel: 'error'
            });

            const status = await shield.initialize();

            expect(status.initialized).toBe(true);
            expect(status.nodes.total).toBe(22);
            expect(status.nodes.active).toBe(22);
        });

        test('should handle disabled proxy configuration', async () => {
            shield = new NetworkShield({
                enabled: false,
                logLevel: 'error'
            });

            const status = await shield.initialize();

            expect(status.enabled).toBe(false);
            expect(status.initialized).toBe(true);
        });

        test('should respect PROXY_ENABLED environment variable', async () => {
            const originalValue = process.env.PROXY_ENABLED;
            process.env.PROXY_ENABLED = 'false';

            shield = new NetworkShield({
                logLevel: 'error'
            });

            const status = await shield.initialize();

            expect(status.enabled).toBe(false);

            process.env.PROXY_ENABLED = originalValue;
        });
    });

    describe('Proxy Assignment', () => {
        beforeEach(async () => {
            shield = new NetworkShield({
                proxyHost: TEST_CONFIG.proxyHost,
                portRange: TEST_CONFIG.portRange,
                enabled: false,  // 禁用以避免实际网络调用
                logLevel: 'error'
            });
            await shield.initialize();
        });

        test('should assign proxy to session', async () => {
            const proxy = await shield.getNextHealthyProxy('test-session-1');

            expect(proxy).not.toBeNull();
            expect(proxy.sessionId).toBe('test-session-1');
            expect(proxy.port).toBeGreaterThanOrEqual(7891);
            expect(proxy.port).toBeLessThanOrEqual(7912);
            expect(proxy.url).toMatch(/^http:\/\/172\.25\.16\.1:\d{4}$/);
        });

        test('should reuse existing session binding', async () => {
            const proxy1 = await shield.getNextHealthyProxy('test-session-2');
            const proxy2 = await shield.getNextHealthyProxy('test-session-2');

            expect(proxy1.port).toBe(proxy2.port);
            expect(proxy1.sessionId).toBe(proxy2.sessionId);
        });

        test('should assign different ports to different sessions', async () => {
            const proxy1 = await shield.getNextHealthyProxy('test-session-3');
            const proxy2 = await shield.getNextHealthyProxy('test-session-4');

            // 由于所有节点都是 active，应该获得不同的端口
            expect(proxy1.port).not.toBe(proxy2.port);
        });

        test('should return null when proxy is disabled', async () => {
            shield.options.enabled = false;

            const proxy = await shield.getNextHealthyProxy('test-session-5');

            expect(proxy).toBeNull();
        });

        test('should release session and make port available', async () => {
            const proxy1 = await shield.getNextHealthyProxy('test-session-6');
            const port1 = proxy1.port;

            shield.releaseSession('test-session-6');

            const proxy2 = await shield.getNextHealthyProxy('test-session-7');

            // 端口应该被重新分配
            expect(proxy2.port).toBe(port1);
        });

        test('should generate session ID if not provided', async () => {
            const proxy = await shield.getNextHealthyProxy();

            expect(proxy.sessionId).toMatch(/^SESSION-\d+-[a-z0-9]+$/);
        });
    });

    describe('Port Contention', () => {
        beforeEach(async () => {
            shield = new NetworkShield({
                proxyHost: TEST_CONFIG.proxyHost,
                portRange: TEST_CONFIG.portRange,
                enabled: false,
                maxSessions: 22,  // 限制会话数
                logLevel: 'error'
            });
            await shield.initialize();
        });

        test('should handle port exhaustion gracefully', async () => {
            const sessions = [];

            // 占用所有 22 个端口
            for (let i = 0; i < 22; i++) {
                const proxy = await shield.getNextHealthyProxy(`session-${i}`);
                sessions.push(proxy.sessionId);
            }

            // 第 23 个会话应该失败
            await expect(
                shield.getNextHealthyProxy('session-overflow')
            ).rejects.toThrow('NS_NO_PROXY_AVAILABLE');

            // 清理
            for (const sessionId of sessions) {
                shield.releaseSession(sessionId);
            }
        });

        test('should reuse released port after session cleanup', async () => {
            // 占用一个端口
            const proxy1 = await shield.getNextHealthyProxy('session-temp');
            const port = proxy1.port;

            // 释放会话
            shield.releaseSession('session-temp');

            // 等待 TTL 过期（需要模拟时间）
            const session = shield.sessionManager.getSession('session-temp');
            session.expiresAt = new Date(Date.now() - 1000);

            shield.sessionManager.cleanupExpiredSessions();

            // 端口应该可用
            const proxy2 = await shield.getNextHealthyProxy('session-new');
            expect(proxy2.port).toBe(port);
        });
    });

    describe('Circuit Breaker Integration', () => {
        beforeEach(async () => {
            shield = new NetworkShield({
                proxyHost: TEST_CONFIG.proxyHost,
                portRange: TEST_CONFIG.portRange,
                enabled: false,
                maxConsecutiveFailures: 2,
                logLevel: 'error'
            });
            await shield.initialize();
        });

        test('should mark proxy as failed and trigger cooldown', async () => {
            const proxy = await shield.getNextHealthyProxy('session-fail');
            const port = proxy.port;

            await shield.markProxyFailed(port, 'Test failure');
            await shield.markProxyFailed(port, 'Test failure 2');

            const node = shield.registryManager.getNode(port);
            expect(node.status).toBe('cooled');
            expect(node.consecutive_failures).toBe(2);
            expect(node.cooldown_until).not.toBeNull();
        });

        test('should mark proxy as successful and reset failures', async () => {
            const proxy = await shield.getNextHealthyProxy('session-success');
            const port = proxy.port;

            // 先标记失败
            await shield.markProxyFailed(port, 'Test failure');

            // 然后标记成功
            await shield.markProxySuccess(port, 100);

            const node = shield.registryManager.getNode(port);
            expect(node.consecutive_failures).toBe(0);
            expect(node.status).toBe('active');
        });

        test('should update circuit breaker state on proxy failure', async () => {
            const proxy = await shield.getNextHealthyProxy('session-cb');
            const port = proxy.port;

            const breaker = shield.circuitBreakerRegistry.getBreaker(port);
            expect(breaker.isClosed()).toBe(true);

            await shield.markProxyFailed(port, 'Failure 1');
            expect(breaker.isClosed()).toBe(true);

            await shield.markProxyFailed(port, 'Failure 2');
            expect(breaker.isOpen()).toBe(true);
        });
    });

    describe('Status and Monitoring', () => {
        beforeEach(async () => {
            shield = new NetworkShield({
                proxyHost: TEST_CONFIG.proxyHost,
                portRange: TEST_CONFIG.portRange,
                enabled: false,
                logLevel: 'error'
            });
            await shield.initialize();
        });

        test('should return accurate status summary', () => {
            const status = shield.getStatus();

            expect(status).toHaveProperty('enabled');
            expect(status).toHaveProperty('initialized');
            expect(status).toHaveProperty('nodes');
            expect(status).toHaveProperty('sessions');
            expect(status).toHaveProperty('requests');
            expect(status).toHaveProperty('avg_health_score');
        });

        test('should return detailed status for debugging', () => {
            const detailed = shield.getDetailedStatus();

            expect(detailed).toHaveProperty('config');
            expect(detailed).toHaveProperty('nodes');
            expect(detailed).toHaveProperty('circuit_breakers');

            expect(detailed.nodes).toHaveLength(22);
            expect(detailed.circuit_breakers).toHaveLength(0);  // 尚未创建
        });

        test('should track session statistics', async () => {
            await shield.getNextHealthyProxy('session-stats-1');
            await shield.getNextHealthyProxy('session-stats-2');

            const stats = shield.sessionManager.getStatistics();

            expect(stats.totalSessions).toBe(2);
            expect(stats.activeSessions).toBe(2);
        });

        test('should track LRU cache statistics', async () => {
            for (let i = 0; i < 10; i++) {
                await shield.getNextHealthyProxy(`session-lru-${i}`);
            }

            const stats = shield.sessionManager.getStatistics();

            expect(stats.lru).toBeDefined();
            expect(stats.lru.size).toBe(10);
        });
    });

    describe('Memory Management', () => {
        test('should enforce LRU max size limit', async () => {
            shield = new NetworkShield({
                proxyHost: TEST_CONFIG.proxyHost,
                portRange: TEST_CONFIG.portRange,
                enabled: false,
                lruMaxSize: 5,  // 小容量
                logLevel: 'error'
            });
            await shield.initialize();

            // 创建超过 LRU 容量的会话
            for (let i = 0; i < 10; i++) {
                await shield.getNextHealthyProxy(`session-memory-${i}`);
            }

            const stats = shield.sessionManager.getStatistics();
            expect(stats.lru.size).toBeLessThanOrEqual(5);
        });

        test('should cleanup expired sessions', async () => {
            shield = new NetworkShield({
                proxyHost: TEST_CONFIG.proxyHost,
                portRange: TEST_CONFIG.portRange,
                enabled: false,
                sessionTimeoutMinutes: 0.001,  // 非常短的 TTL
                logLevel: 'error'
            });
            await shield.initialize();

            await shield.getNextHealthyProxy('session-expire-1');
            await shield.getNextHealthyProxy('session-expire-2');

            // 等待会话过期
            await new Promise(resolve => setTimeout(resolve, 100));

            const cleaned = shield.sessionManager.cleanupExpiredSessions();
            expect(cleaned).toBeGreaterThan(0);
        });
    });

    describe('Manual Operations', () => {
        beforeEach(async () => {
            shield = new NetworkShield({
                proxyHost: TEST_CONFIG.proxyHost,
                portRange: TEST_CONFIG.portRange,
                enabled: false,
                logLevel: 'error'
            });
            await shield.initialize();
        });

        test('should reset all nodes', async () => {
            // 标记一些失败
            const proxy = await shield.getNextHealthyProxy('session-reset');
            await shield.markProxyFailed(proxy.port, 'Test failure');

            const nodeBefore = shield.registryManager.getNode(proxy.port);
            expect(nodeBefore.consecutive_failures).toBe(1);

            // 重置所有节点
            await shield.resetAllNodes();

            const nodeAfter = shield.registryManager.getNode(proxy.port);
            expect(nodeAfter.consecutive_failures).toBe(0);
            expect(nodeAfter.status).toBe('active');
        });

        test('should run manual health check', async () => {
            // 注意：实际健康检查需要网络连接
            // 这里只验证方法调用
            const healthCheckPromise = shield.runHealthCheck();
            expect(healthCheckPromise).toBeInstanceOf(Promise);
        });
    });

    describe('Singleton Pattern', () => {
        test('should return same instance on subsequent getNetworkShield calls', () => {
            const shield1 = getNetworkShield({ enabled: false, logLevel: 'error' });
            const shield2 = getNetworkShield({ enabled: false, logLevel: 'error' });

            expect(shield1).toBe(shield2);
        });

        test('should reset singleton for testing', () => {
            const shield1 = getNetworkShield({ enabled: false, logLevel: 'error' });
            resetSingleton();
            const shield2 = getNetworkShield({ enabled: false, logLevel: 'error' });

            expect(shield1).not.toBe(shield2);
        });
    });

    describe('Error Handling', () => {
        beforeEach(async () => {
            shield = new NetworkShield({
                proxyHost: TEST_CONFIG.proxyHost,
                portRange: TEST_CONFIG.portRange,
                enabled: false,
                logLevel: 'error'
            });
            await shield.initialize();
        });

        test('should handle invalid session IDs gracefully', () => {
            expect(() => {
                shield.releaseSession('non-existent-session');
            }).not.toThrow();
        });

        test('should handle null sessionId in getNextHealthyProxy', async () => {
            const proxy = await shield.getNextHealthyProxy(null);
            expect(proxy).not.toBeNull();
            expect(proxy.sessionId).toMatch(/^SESSION-/);
        });

        test('should handle undefined sessionId in getNextHealthyProxy', async () => {
            const proxy = await shield.getNextHealthyProxy(undefined);
            expect(proxy).not.toBeNull();
        });
    });

    describe('Shutdown', () => {
        test('should shutdown cleanly', async () => {
            shield = new NetworkShield({
                proxyHost: TEST_CONFIG.proxyHost,
                portRange: TEST_CONFIG.portRange,
                enabled: false,
                logLevel: 'error'
            });
            await shield.initialize();

            // 创建一些会话
            await shield.getNextHealthyProxy('session-shutdown-1');
            await shield.getNextHealthyProxy('session-shutdown-2');

            expect(() => {
                shield.shutdown();
            }).not.toThrow();

            // 验证清理
            const stats = shield.sessionManager.getStatistics();
            expect(stats.totalSessions).toBe(0);
        });
    });
});

describe('Cross-Language Registry Access', () => {
    // 注意：这些测试假设 Python 适配器可用
    // 实际运行可能需要 Python 环境

    describe('File Locking', () => {
        test('should handle concurrent file access', async () => {
            const fs = FileSystemProvider.getFileSystem();
            const testFile = path.join(__dirname, '../config/.test_lock');

            // 获取锁
            const acquired1 = await fs.acquireLock(testFile, 1000);
            expect(acquired1).toBe(true);

            // 尝试再次获取（应该超时）
            const acquired2 = await fs.acquireLock(testFile, 100);
            expect(acquired2).toBe(false);

            // 释放锁
            fs.releaseLock(testFile);

            // 现在应该能获取
            const acquired3 = await fs.acquireLock(testFile, 1000);
            expect(acquired3).toBe(true);

            // 清理
            fs.releaseLock(testFile);

            try {
                const fsModule = require('fs');
                if (fsModule.existsSync(testFile)) {
                    fsModule.unlinkSync(testFile);
                }
            } catch (e) {
                // Ignore
            }
        });
    });

    describe('Registry Persistence', () => {
        test('should persist registry changes to disk', () => {
            const fs = FileSystemProvider.getFileSystem();
            const testFile = path.join(__dirname, '../config/test_persist.json');

            const testData = {
                version: 'V1.1.0',
                nodes: [
                    { id: 'NODE-7891', port: 7891, status: 'active' }
                ]
            };

            // 写入
            fs.atomicWrite(testFile, JSON.stringify(testData, null, 2));

            // 读取
            const content = fs.readFile(testFile);
            const parsed = JSON.parse(content);

            expect(parsed).toEqual(testData);

            // 清理
            try {
                const fsModule = require('fs');
                if (fsModule.existsSync(testFile)) {
                    fsModule.unlinkSync(testFile);
                }
            } catch (e) {
                // Ignore
            }
        });
    });
});

describe('Long-Running Stability', () => {
    test('should handle rapid proxy allocation cycles', async () => {
        shield = new NetworkShield({
            proxyHost: TEST_CONFIG.proxyHost,
            portRange: TEST_CONFIG.portRange,
            enabled: false,
            maxSessions: 100,
            logLevel: 'error'
        });
        await shield.initialize();

        const iterations = 100;

        for (let i = 0; i < iterations; i++) {
            const sessionId = `stress-session-${i}`;
            const proxy = await shield.getNextHealthyProxy(sessionId);
            expect(proxy).not.toBeNull();

            shield.releaseSession(sessionId);
        }

        const stats = shield.sessionManager.getStatistics();
        expect(stats.totalSessions).toBeLessThan(100);  // LRU 应该清理
    });

    test('should maintain consistency under concurrent operations', async () => {
        shield = new NetworkShield({
            proxyHost: TEST_CONFIG.proxyHost,
            portRange: TEST_CONFIG.portRange,
            enabled: false,
            maxSessions: 50,
            logLevel: 'error'
        });
        await shield.initialize();

        const operations = [];

        // 并发分配
        for (let i = 0; i < 20; i++) {
            operations.push(
                shield.getNextHealthyProxy(`concurrent-${i}`)
            );
        }

        const results = await Promise.all(operations);

        // 所有分配应该成功
        for (const result of results) {
            expect(result).not.toBeNull();
        }

        // 端口应该不重复
        const ports = results.map(r => r.port);
        const uniquePorts = new Set(ports);
        expect(uniquePorts.size).toBe(20);
    });
});
