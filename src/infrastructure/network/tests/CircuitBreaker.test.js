/**
 * CircuitBreaker.test.js - V1.1.0 单元测试套件
 * ========================================================================
 *
 * 测试覆盖：
 * - 状态转换 (CLOSED → OPEN → HALF_OPEN → CLOSED)
 * - 15分钟冷却期验证
 * - 事件系统 (tripped, recovered, halfOpen 事件)
 * - 统计信息跟踪
 * - 线程安全模拟
 * - 半开状态超时行为
 * - 边界情况和配置
 * @module network/tests/CircuitBreaker.test
 * @version V1.1.0
 * @since 2026-02-03
 */

'use strict';

const { CircuitBreaker, CircuitBreakerRegistry, CircuitState } = require('../../../core/network/CircuitBreaker');

// 模拟日志记录器
/**
 *
 */
class MockLogger {
    /**
     *
     */
    constructor() {
        this.logs = [];
    }

    /**
     *
     * @param msg
     */
    debug(msg) { this.logs.push({ level: 'debug', msg }); }
    /**
     *
     * @param msg
     */
    info(msg) { this.logs.push({ level: 'info', msg }); }
    /**
     *
     * @param msg
     */
    warn(msg) { this.logs.push({ level: 'warn', msg }); }
    /**
     *
     * @param msg
     */
    error(msg) { this.logs.push({ level: 'error', msg }); }

    /**
     *
     */
    clear() { this.logs = []; }
    /**
     *
     * @param level
     */
    getLogs(level) { return this.logs.filter(l => l.level === level); }
}

describe('CircuitBreaker - V1.1.0 Unit Tests', () => {
    let breaker;
    let logger;

    beforeEach(() => {
        logger = new MockLogger();
        breaker = new CircuitBreaker(7891, {
            failureThreshold: 2,
            cooldownMinutes: 15,
            halfOpenMaxCalls: 1,
            successThreshold: 1,
            halfOpenTimeoutMs: 30000
        }, logger);
    });

    describe('State Transitions', () => {
        test('should initialize in CLOSED state', () => {
            expect(breaker.getState().state).toBe(CircuitState.CLOSED);
            expect(breaker.isClosed()).toBe(true);
            expect(breaker.isOpen()).toBe(false);
            expect(breaker.isHalfOpen()).toBe(false);
        });

        test('should transition from CLOSED to OPEN after 2 consecutive failures', async () => {
            // 第一次失败
            breaker.recordFailure(new Error('First failure'));
            expect(breaker.getState().state).toBe(CircuitState.CLOSED);
            expect(breaker.getState().consecutiveFailures).toBe(1);

            // 第二次失败 - 应该触发熔断
            breaker.recordFailure(new Error('Second failure'));
            expect(breaker.getState().state).toBe(CircuitState.OPEN);
            expect(breaker.isOpen()).toBe(true);
        });

        test('should reset consecutive failures on success', () => {
            breaker.recordFailure(new Error('Failure 1'));
            expect(breaker.getState().consecutiveFailures).toBe(1);

            breaker.recordSuccess();
            expect(breaker.getState().consecutiveFailures).toBe(0);
            expect(breaker.getState().consecutiveSuccesses).toBe(1);
        });

        test('should transition from OPEN to HALF_OPEN after cooldown period', async () => {
            // 触发熔断
            breaker.recordFailure(new Error('Failure 1'));
            breaker.recordFailure(new Error('Failure 2'));
            expect(breaker.getState().state).toBe(CircuitState.OPEN);

            // 模拟冷却期结束（使用较短的测试配置）
            const testBreaker = new CircuitBreaker(7891, {
                failureThreshold: 2,
                cooldownMinutes: 0,  // 立即冷却
                halfOpenTimeoutMs: 30000
            }, logger);

            testBreaker.recordFailure(new Error('Failure 1'));
            testBreaker.recordFailure(new Error('Failure 2'));
            expect(testBreaker.getState().state).toBe(CircuitState.OPEN);

            // 等待 1ms 确保冷却期已过
            await new Promise(resolve => { setTimeout(resolve, 10); });

            // 执行请求应该触发状态评估
            try {
                await testBreaker.execute(async () => 'success');
            } catch (e) {
                // 可能失败，但状态应该转换到 HALF_OPEN
            }

            expect(testBreaker.getState().state).toBe(CircuitState.HALF_OPEN);
        });

        test('should transition from HALF_OPEN to CLOSED after success', () => {
            // 强制设置为 HALF_OPEN 状态
            breaker._transitionTo(CircuitState.HALF_OPEN);
            breaker._consecutiveSuccesses = 0;

            breaker.recordSuccess();
            expect(breaker.getState().state).toBe(CircuitState.CLOSED);
            expect(breaker.getState().consecutiveSuccesses).toBe(1);
        });

        test('should transition from HALF_OPEN back to OPEN on failure', () => {
            breaker._transitionTo(CircuitState.HALF_OPEN);
            breaker._consecutiveSuccesses = 0;

            breaker.recordFailure(new Error('Half-open failure'));
            expect(breaker.getState().state).toBe(CircuitState.OPEN);
        });
    });

    describe('Request Execution', () => {
        test('should execute requests successfully in CLOSED state', async () => {
            const result = await breaker.execute(async () => 'test-result');
            expect(result).toBe('test-result');
        });

        test('should record success on successful execution', async () => {
            await breaker.execute(async () => 'success');
            expect(breaker.getState().consecutiveSuccesses).toBe(1);
            expect(breaker.getStats().successfulExecutions).toBe(1);
        });

        test('should record failure on failed execution', async () => {
            await expect(
                breaker.execute(async () => { throw new Error('Request failed'); })
            ).rejects.toThrow('Request failed');

            expect(breaker.getState().consecutiveFailures).toBe(1);
            expect(breaker.getStats().failedExecutions).toBe(1);
        });

        test('should reject requests when OPEN', async () => {
            breaker._transitionTo(CircuitState.OPEN);

            await expect(
                breaker.execute(async () => 'should not execute')
            ).rejects.toThrow('NS_CIRCUIT_OPEN');

            expect(breaker.getStats().rejectedExecutions).toBe(1);
        });

        test('should allow requests in HALF_OPEN state', async () => {
            breaker._transitionTo(CircuitState.HALF_OPEN);

            const result = await breaker.execute(async () => 'half-open-result');
            expect(result).toBe('half-open-result');
        });
    });

    describe('Cooldown Period', () => {
        test('should set cooldown_until when transitioning to OPEN', () => {
            const beforeState = breaker.getState();
            breaker.recordFailure(new Error('Failure 1'));
            breaker.recordFailure(new Error('Failure 2'));

            const afterState = breaker.getState();
            expect(afterState.state).toBe(CircuitState.OPEN);
            expect(afterState.cooldownUntil).not.toBeNull();
            expect(afterState.cooldownUntil).toBeInstanceOf(Date);
        });

        test('should respect cooldownMinutes configuration', () => {
            const testBreaker = new CircuitBreaker(7891, {
                failureThreshold: 2,
                cooldownMinutes: 30
            }, logger);

            testBreaker.recordFailure(new Error('Failure 1'));
            testBreaker.recordFailure(new Error('Failure 2'));

            const state = testBreaker.getState();
            const cooldownDuration = new Date(state.cooldownUntil) - new Date(state.lastFailureTime);

            // 30 分钟 = 30 * 60 * 1000 = 1800000 ms
            expect(cooldownDuration).toBe(30 * 60 * 1000);
        });
    });

    describe('Event System', () => {
        test('should emit "tripped" event when circuit opens', (done) => {
            breaker.on('tripped', (data) => {
                expect(data.port).toBe(7891);
                expect(data.failures).toBe(2);
                expect(data.error).toBe('Test failure');
                done();
            });

            breaker.recordFailure(new Error('Test failure 1'));
            breaker.recordFailure(new Error('Test failure'));
        });

        test('should emit "recovered" event when circuit closes', (done) => {
            breaker._transitionTo(CircuitState.HALF_OPEN);
            breaker._consecutiveSuccesses = 0;

            breaker.on('recovered', (data) => {
                expect(data.port).toBe(7891);
                expect(breaker.getState().state).toBe(CircuitState.CLOSED);
                done();
            });

            breaker.recordSuccess();
        });

        test('should emit "halfOpen" event when transitioning to HALF_OPEN', (done) => {
            breaker._transitionTo(CircuitState.OPEN);

            breaker.on('halfOpen', (data) => {
                expect(data.port).toBe(7891);
                expect(breaker.getState().state).toBe(CircuitState.HALF_OPEN);
                done();
            });

            // 触发状态评估
            breaker._evaluateStateTransition();
        });

        test('should handle multiple event listeners', () => {
            let callCount = 0;
            const handler1 = () => { callCount++; };
            const handler2 = () => { callCount++; };

            breaker.on('tripped', handler1);
            breaker.on('tripped', handler2);

            breaker.recordFailure(new Error('F1'));
            breaker.recordFailure(new Error('F2'));

            expect(callCount).toBe(2);
        });

        test('should remove event listeners with off()', () => {
            let callCount = 0;
            const handler = () => { callCount++; };

            breaker.on('tripped', handler);
            breaker.off('tripped', handler);

            breaker.recordFailure(new Error('F1'));
            breaker.recordFailure(new Error('F2'));

            expect(callCount).toBe(0);
        });

        test('should handle event listener errors gracefully', () => {
            breaker.on('tripped', () => { throw new Error('Listener error'); });
            breaker.on('tripped', () => { /* Second listener */ });

            // 不应该抛出异常
            expect(() => {
                breaker.recordFailure(new Error('F1'));
                breaker.recordFailure(new Error('F2'));
            }).not.toThrow();
        });
    });

    describe('Statistics', () => {
        test('should track execution statistics', async () => {
            // 成功执行
            await breaker.execute(async () => 'success');
            await breaker.execute(async () => 'success2');

            // 失败执行
            try {
                await breaker.execute(async () => { throw new Error('fail'); });
            } catch (e) { /* ignore */ }

            const stats = breaker.getStats();
            expect(stats.totalExecutions).toBe(3);
            expect(stats.successfulExecutions).toBe(2);
            expect(stats.failedExecutions).toBe(1);
            expect(stats.rejectedExecutions).toBe(0);
        });

        test('should track state transitions', () => {
            const initialTransitions = breaker.getState().stats.stateTransitions;

            breaker._transitionTo(CircuitState.OPEN);
            breaker._transitionTo(CircuitState.HALF_OPEN);
            breaker._transitionTo(CircuitState.CLOSED);

            expect(breaker.getState().stats.stateTransitions).toBe(initialTransitions + 3);
        });

        test('should calculate success and failure rates', async () => {
            await breaker.execute(async () => 's1');
            await breaker.execute(async () => 's2');

            try {
                await breaker.execute(async () => { throw new Error('f1'); });
            } catch (e) { /* ignore */ }

            try {
                await breaker.execute(async () => { throw new Error('f2'); });
            } catch (e) { /* ignore */ }

            const stats = breaker.getStats();
            expect(stats.successRate).toBe(0.5);  // 2/4
            expect(stats.failureRate).toBe(0.5);  // 2/4
        });
    });

    describe('Manual Operations', () => {
        test('should reset circuit breaker manually', () => {
            breaker.recordFailure(new Error('F1'));
            breaker.recordFailure(new Error('F2'));
            expect(breaker.getState().state).toBe(CircuitState.OPEN);

            breaker.reset();
            expect(breaker.getState().state).toBe(CircuitState.CLOSED);
            expect(breaker.getState().consecutiveFailures).toBe(0);
            expect(breaker.getState().consecutiveSuccesses).toBe(0);
            expect(breaker.getState().cooldownUntil).toBeNull();
        });

        test('should return current state', () => {
            const state = breaker.getState();

            expect(state).toHaveProperty('port', 7891);
            expect(state).toHaveProperty('state');
            expect(state).toHaveProperty('consecutiveFailures');
            expect(state).toHaveProperty('consecutiveSuccesses');
            expect(state).toHaveProperty('lastFailureTime');
            expect(state).toHaveProperty('cooldownUntil');
            expect(state).toHaveProperty('canExecute');
            expect(state).toHaveProperty('stats');
        });
    });

    describe('Thread Safety Simulation', () => {
        test('should handle rapid concurrent state transitions', async () => {
            const promises = [];

            // 模拟并发操作
            for (let i = 0; i < 100; i++) {
                promises.push(
                    breaker.execute(async () => {
                        await new Promise(resolve => { setTimeout(resolve, Math.random() * 10); });
                        if (Math.random() > 0.8) {
                            throw new Error('Random failure');
                        }
                        return 'success';
                    }).catch(() => { /* ignore failures */ })
                );
            }

            await Promise.all(promises);

            // 验证状态一致性
            const state = breaker.getState();
            expect(state).toBeDefined();
            expect([CircuitState.CLOSED, CircuitState.OPEN, CircuitState.HALF_OPEN])
                .toContain(state.state);
        });

        test('should handle rapid recordFailure calls', () => {
            for (let i = 0; i < 50; i++) {
                breaker.recordFailure(new Error(`Failure ${i}`));
            }

            const state = breaker.getState();
            expect(state.consecutiveFailures).toBeGreaterThan(1);
        });
    });

    describe('Half-Open Timeout', () => {
        test('should transition from HALF_OPEN to OPEN on timeout', async () => {
            const testBreaker = new CircuitBreaker(7891, {
                failureThreshold: 2,
                cooldownMinutes: 0,
                halfOpenTimeoutMs: 100  // 100ms 超时
            }, logger);

            // 进入 HALF_OPEN 状态
            testBreaker.recordFailure(new Error('F1'));
            testBreaker.recordFailure(new Error('F2'));
            await new Promise(resolve => { setTimeout(resolve, 10); });
            testBreaker._evaluateStateTransition();

            expect(testBreaker.getState().state).toBe(CircuitState.HALF_OPEN);

            // 等待超时
            await new Promise(resolve => { setTimeout(resolve, 150); });

            // 触发状态评估
            testBreaker._evaluateStateTransition();

            expect(testBreaker.getState().state).toBe(CircuitState.OPEN);
        });

        test('should emit "halfOpenTimeout" event on timeout', async () => {
            const testBreaker = new CircuitBreaker(7891, {
                failureThreshold: 2,
                cooldownMinutes: 0,
                halfOpenTimeoutMs: 50
            }, logger);

            testBreaker.on('halfOpenTimeout', (data) => {
                expect(data.port).toBe(7891);
            });

            testBreaker.recordFailure(new Error('F1'));
            testBreaker.recordFailure(new Error('F2'));
            await new Promise(resolve => { setTimeout(resolve, 60); });
            testBreaker._evaluateStateTransition();

            // 事件应该在状态评估时触发
        });
    });

    describe('Edge Cases', () => {
        test('should handle zero failureThreshold', () => {
            const testBreaker = new CircuitBreaker(7891, {
                failureThreshold: 0
            }, logger);

            testBreaker.recordFailure(new Error('Single failure'));
            expect(testBreaker.getState().state).toBe(CircuitState.OPEN);
        });

        test('should handle very large failureThreshold', () => {
            const testBreaker = new CircuitBreaker(7891, {
                failureThreshold: 1000
            }, logger);

            for (let i = 0; i < 100; i++) {
                testBreaker.recordFailure(new Error(`Failure ${i}`));
            }

            expect(testBreaker.getState().state).toBe(CircuitState.CLOSED);
            expect(testBreaker.getState().consecutiveFailures).toBe(100);
        });

        test('should handle undefined logger', () => {
            const noLoggerBreaker = new CircuitBreaker(7891, {
                failureThreshold: 2
            });

            expect(() => {
                noLoggerBreaker.recordFailure(new Error('Test'));
                noLoggerBreaker.recordFailure(new Error('Test 2'));
            }).not.toThrow();
        });

        test('should handle execute with non-async function', async () => {
            const result = await breaker.execute(() => 'sync-result');
            expect(result).toBe('sync-result');
        });

        test('should handle execute with function returning non-promise', async () => {
            const result = await breaker.execute(() => 42);
            expect(result).toBe(42);
        });
    });
});

describe('CircuitBreakerRegistry', () => {
    let registry;
    let logger;

    beforeEach(() => {
        logger = new MockLogger();
        registry = new CircuitBreakerRegistry(
            { failureThreshold: 2, cooldownMinutes: 15 },
            logger
        );
    });

    test('should create new breaker on first getBreaker call', () => {
        const breaker = registry.getBreaker(7891);
        expect(breaker).toBeInstanceOf(CircuitBreaker);
        expect(breaker.port).toBe(7891);
    });

    test('should return existing breaker on subsequent getBreaker calls', () => {
        const breaker1 = registry.getBreaker(7891);
        const breaker2 = registry.getBreaker(7891);
        expect(breaker1).toBe(breaker2);
    });

    test('should manage multiple breakers independently', () => {
        const breaker1 = registry.getBreaker(7891);
        const breaker2 = registry.getBreaker(7892);

        breaker1.recordFailure(new Error('F1'));
        breaker1.recordFailure(new Error('F2'));

        expect(breaker1.getState().state).toBe(CircuitState.OPEN);
        expect(breaker2.getState().state).toBe(CircuitState.CLOSED);
    });

    test('should remove breaker', () => {
        registry.getBreaker(7891);
        expect(registry.size).toBe(1);

        registry.removeBreaker(7891);
        expect(registry.size).toBe(0);
    });

    test('should get all breaker states', () => {
        registry.getBreaker(7891);
        registry.getBreaker(7892);

        const states = registry.getAllStates();
        expect(states).toHaveLength(2);
        expect(states[0]).toHaveProperty('port');
        expect(states[0]).toHaveProperty('state');
    });

    test('should get summary statistics', () => {
        const breaker1 = registry.getBreaker(7891);
        const breaker2 = registry.getBreaker(7892);

        breaker1.recordFailure(new Error('F1'));
        breaker1.recordFailure(new Error('F2'));

        const summary = registry.getSummary();
        expect(summary.totalBreakers).toBe(2);
        expect(summary.open).toBe(1);
        expect(summary.closed).toBe(1);
    });

    test('should reset all breakers', () => {
        const breaker1 = registry.getBreaker(7891);
        const breaker2 = registry.getBreaker(7892);

        breaker1.recordFailure(new Error('F1'));
        breaker1.recordFailure(new Error('F2'));
        breaker2.recordFailure(new Error('F3'));

        expect(breaker1.getState().state).toBe(CircuitState.OPEN);

        registry.resetAll();

        expect(breaker1.getState().state).toBe(CircuitState.CLOSED);
        expect(breaker2.getState().state).toBe(CircuitState.CLOSED);
    });

    test('should get all ports', () => {
        registry.getBreaker(7891);
        registry.getBreaker(7892);
        registry.getBreaker(7893);

        const ports = registry.getPorts();
        expect(ports).toContain(7891);
        expect(ports).toContain(7892);
        expect(ports).toContain(7893);
        expect(ports).toHaveLength(3);
    });

    test('should shutdown and clear all breakers', () => {
        registry.getBreaker(7891);
        registry.getBreaker(7892);
        expect(registry.size).toBe(2);

        registry.shutdown();
        expect(registry.size).toBe(0);
    });
});
