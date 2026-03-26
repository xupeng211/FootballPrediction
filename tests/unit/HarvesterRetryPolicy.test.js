'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { HarvesterRetryPolicy } = require('../../src/infrastructure/harvesters/components/HarvesterRetryPolicy');

function createHarvesterMock(overrides = {}) {
    return {
        config: { maxWorkers: 2 },
        stats: { processed: 0, success: 0, failed: 0, retries: 0 },
        networkManager: null,
        autoAuthCalls: [],
        delayCalls: [],
        _recordSuccess() {
            this.stats.processed++;
            this.stats.success++;
        },
        _recordFailure() {
            this.stats.processed++;
            this.stats.failed++;
        },
        _recordRetry() {
            this.stats.retries++;
        },
        async _triggerAutoAuth(index, errorMessage) {
            this.autoAuthCalls.push({ index, errorMessage });
        },
        async _delay(ms) {
            this.delayCalls.push(ms);
        },
        async _harvestSingleMatch() {
            return { success: true };
        },
        ...overrides,
    };
}

describe('HarvesterRetryPolicy 单元测试', () => {
    describe('错误分类与重试决策', () => {
        it('应将网络错误判定为可重试', () => {
            const policy = new HarvesterRetryPolicy();
            assert.strictEqual(policy.isRetryableError(new Error('ECONNRESET')), true);
        });

        it('应将 NO_DATA 判定为可重试', () => {
            const policy = new HarvesterRetryPolicy();
            assert.strictEqual(policy.isRetryableError(new Error('NO_DATA:无法获取数据')), true);
        });

        it('应将权限/封锁错误判定为不可重试', () => {
            const policy = new HarvesterRetryPolicy();
            assert.strictEqual(policy.isRetryableError(new Error('403 Forbidden')), false);
            assert.strictEqual(policy.isRetryableError(new Error('Turnstile challenge required')), false);
        });

        it('应分类数据库错误', () => {
            const policy = new HarvesterRetryPolicy();

            assert.strictEqual(policy.classifyDatabaseError(new Error('duplicate key value')), 'DUPLICATE_KEY');
            assert.strictEqual(policy.classifyDatabaseError(new Error('ECONNREFUSED')), 'CONNECTION_ERROR');
            assert.strictEqual(policy.classifyDatabaseError(new Error('Query timed out')), 'TIMEOUT');
            assert.strictEqual(
                policy.classifyDatabaseError(new Error('syntax error at or near "\' OR 1=1"')),
                'SQL_SYNTAX_ERROR'
            );
        });

        it('应分类文件错误', () => {
            const policy = new HarvesterRetryPolicy();

            assert.strictEqual(policy.classifyFileError(new Error('EACCES: permission denied')), 'PERMISSION_DENIED');
            assert.strictEqual(policy.classifyFileError(new Error('ENOSPC: no space left on device')), 'NO_SPACE');
            assert.strictEqual(policy.classifyFileError(new Error('unknown file issue')), 'UNKNOWN');
        });
    });

    describe('指数退避', () => {
        it('应按指数增长并封顶', () => {
            const policy = new HarvesterRetryPolicy({ baseBackoffMs: 1000, maxBackoffMs: 8000 });

            assert.strictEqual(policy.getRecommendedBackoff(1), 2000);
            assert.strictEqual(policy.getRecommendedBackoff(2), 4000);
            assert.strictEqual(policy.getRecommendedBackoff(3), 8000);
            assert.strictEqual(policy.getRecommendedBackoff(4), 8000);
        });
    });

    describe('执行重试链路', () => {
        it('应在首次成功时直接返回', async () => {
            const policy = new HarvesterRetryPolicy();
            const harvester = createHarvesterMock({
                async _harvestSingleMatch() {
                    return { success: true, match_id: 'm1' };
                }
            });

            const result = await policy.executeWithRetry(harvester, { match_id: 'm1', home_team: 'A', away_team: 'B' }, 0, 3);

            assert.strictEqual(result.success, true);
            assert.strictEqual(harvester.stats.retries, 0);
            assert.deepStrictEqual(harvester.delayCalls, []);
        });

        it('应在可重试错误后切端口并重试成功', async () => {
            const policy = new HarvesterRetryPolicy({ baseBackoffMs: 1000, maxBackoffMs: 8000 });
            let attempts = 0;
            let clearedPort = null;
            let reassignedPort = null;

            const harvester = createHarvesterMock({
                networkManager: {
                    getWorkerIdentity: () => ({ proxy: { port: 7890 } }),
                    forceReassignPort: async (workerId, oldPort) => {
                        reassignedPort = oldPort;
                        return { port: 7891 };
                    },
                    sessionManager: {
                        clearSession: async port => {
                            clearedPort = port;
                        }
                    }
                },
                async _harvestSingleMatch() {
                    attempts++;
                    if (attempts === 1) {
                        return { success: false, error: 'ERR_CONNECTION_RESET' };
                    }
                    return { success: true, match_id: 'm2' };
                }
            });

            const result = await policy.executeWithRetry(harvester, { match_id: 'm2', home_team: 'A', away_team: 'B' }, 0, 3);

            assert.strictEqual(result.success, true);
            assert.strictEqual(attempts, 2);
            assert.strictEqual(harvester.stats.retries, 1);
            assert.strictEqual(clearedPort, 7890);
            assert.strictEqual(reassignedPort, 7890);
            assert.deepStrictEqual(harvester.delayCalls, [2000]);
        });

        it('应在 BLOCKED 错误时触发自动鉴权且不重试', async () => {
            const policy = new HarvesterRetryPolicy();
            const harvester = createHarvesterMock({
                async _harvestSingleMatch() {
                    return { success: false, match_id: 'm3', error: 'Turnstile challenge required' };
                }
            });

            const result = await policy.executeWithRetry(harvester, { match_id: 'm3', home_team: 'A', away_team: 'B' }, 0, 3);

            assert.strictEqual(result.success, false);
            assert.strictEqual(harvester.autoAuthCalls.length, 1);
            assert.deepStrictEqual(harvester.delayCalls, []);
        });

        it('应在抛出不可重试异常时立即失败并带 attempts', async () => {
            const policy = new HarvesterRetryPolicy();
            const harvester = createHarvesterMock({
                async _harvestSingleMatch() {
                    throw new Error('403 Forbidden');
                }
            });

            const result = await policy.executeWithRetry(harvester, { match_id: 'm4', home_team: 'A', away_team: 'B' }, 0, 3);

            assert.strictEqual(result.success, false);
            assert.strictEqual(result.attempts, 1);
            assert.strictEqual(result.error, '403 Forbidden');
        });

        it('应在连续 SIZE_TOO_SMALL 时触发冷却', async () => {
            const policy = new HarvesterRetryPolicy({ cooldownThreshold: 3, cooldownMs: 30000 });
            let attempts = 0;
            const harvester = createHarvesterMock({
                networkManager: {
                    getWorkerIdentity: () => ({ proxy: { port: 7890 } }),
                    forceReassignPort: async () => ({ port: 7891 }),
                    sessionManager: {
                        clearSession: async () => {}
                    }
                },
                async _harvestSingleMatch() {
                    attempts++;
                    return { success: false, match_id: 'm5', error: 'SIZE_TOO_SMALL:512' };
                }
            });

            const result = await policy.executeWithRetry(harvester, { match_id: 'm5', home_team: 'A', away_team: 'B' }, 0, 4);

            assert.strictEqual(result.success, false);
            assert.strictEqual(attempts, 4);
            assert.ok(harvester.delayCalls.includes(30000));
            assert.deepStrictEqual(harvester.delayCalls, [2000, 4000, 30000, 8000]);
        });

        it('应在单场执行超时后触发 watchdog 并释放并发位', async () => {
            const policy = new HarvesterRetryPolicy();
            const closedContexts = [];
            const harvester = createHarvesterMock({
                config: { maxWorkers: 2, harvestTimeoutMs: 20 },
                async _closeWorkerContext(workerId, reason) {
                    closedContexts.push({ workerId, reason });
                    return true;
                },
                async _harvestSingleMatch() {
                    return new Promise(() => {});
                }
            });

            const result = await policy.executeWithRetry(
                harvester,
                { match_id: 'm-timeout', home_team: 'A', away_team: 'B' },
                0,
                1
            );

            assert.strictEqual(result.success, false);
            assert.match(result.error, /WATCHDOG_TIMEOUT/);
            assert.deepStrictEqual(closedContexts, [{ workerId: 1, reason: 'WATCHDOG_TIMEOUT' }]);
        });
    });
});
