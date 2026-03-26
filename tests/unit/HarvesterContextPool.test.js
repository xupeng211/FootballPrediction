'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { HarvesterContextPool } = require('../../src/infrastructure/harvesters/components/HarvesterContextPool');

describe('HarvesterContextPool 单元测试', () => {
    it('应对同一 Worker 的并发申请进行去重', async () => {
        const pool = new HarvesterContextPool({ maxSize: 5, maxUsage: 10 });
        let createCount = 0;

        const deps = {
            browserFactory: {
                createContext: async () => {
                    createCount++;
                    await new Promise(resolve => {
                        setTimeout(resolve, 20);
                    });
                    return {
                        id: createCount,
                        close: async () => {},
                        clearCookies: async () => {}
                    };
                },
                loadBrowserStateCookies: async () => false
            },
            networkManager: null
        };

        const identity = { proxy: { port: 7890 } };
        const [first, second] = await Promise.all([
            pool.getOrCreate(1, identity, deps),
            pool.getOrCreate(1, identity, deps)
        ]);

        assert.strictEqual(createCount, 1, '并发创建应只触发一次 createContext');
        assert.strictEqual(first.context, second.context, '同一 Worker 并发申请应拿到同一个 Context');
        assert.strictEqual(pool.getSize(), 1, '池内应只有一个 Context');
    });

    it('应自动回收超时 Context', async () => {
        const pool = new HarvesterContextPool({ maxSize: 5, maxUsage: 10, idleTimeoutMs: 10 });
        let closed = false;

        const deps = {
            browserFactory: {
                createContext: async () => ({
                    close: async () => {
                        closed = true;
                    },
                    clearCookies: async () => {}
                }),
                loadBrowserStateCookies: async () => false
            },
            networkManager: null
        };

        await pool.getOrCreate(1, { proxy: { port: 7890 } }, deps);
        const entry = pool.getEntry(1);
        entry.lastAccessTime = Date.now() - 1000;

        const cleaned = await pool.reapExpiredContexts();

        assert.strictEqual(cleaned, 1, '应回收一个超时 Context');
        assert.strictEqual(closed, true, '超时 Context 应被关闭');
        assert.strictEqual(pool.getSize(), 0, '超时回收后池应清空');
    });

    it('应在数据库连接丢失时清空整个池', async () => {
        const pool = new HarvesterContextPool({ maxSize: 5, maxUsage: 10 });
        const closedContexts = [];
        let contextId = 0;

        const deps = {
            browserFactory: {
                createContext: async () => {
                    const id = ++contextId;
                    return {
                        close: async () => {
                            closedContexts.push(id);
                        },
                        clearCookies: async () => {}
                    };
                },
                loadBrowserStateCookies: async () => false
            },
            networkManager: null
        };

        await pool.getOrCreate(1, { proxy: { port: 7890 } }, deps);
        await pool.getOrCreate(2, { proxy: { port: 7891 } }, deps);

        const handled = await pool.handleDependencyFailure('db_connection_lost');

        assert.strictEqual(handled, true, '数据库依赖故障应被识别');
        assert.deepStrictEqual(closedContexts.sort((a, b) => a - b), [1, 2], '所有 Context 都应被关闭');
        assert.strictEqual(pool.getSize(), 0, '故障清理后池应为空');
    });
});
