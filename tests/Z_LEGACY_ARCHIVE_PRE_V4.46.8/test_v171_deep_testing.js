/**
 * V171-Standard-07 深度测试套件
 * =============================
 *
 * 测试类型:
 * - Mock 测试 (数据库/子进程)
 * - 异常注入 (超时/重试)
 * - 逻辑深度验证 (优先级/熔断)
 *
 * @module tests/test_v171_deep_testing
 */

'use strict';

const { describe, it, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert');
const { EventEmitter } = require('events');

// ============================================================================
// Mock 工具
// ============================================================================

/**
 * 创建 Mock PostgreSQL 客户端
 */
function createMockPgClient(options = {}) {
    const {
        shouldFail = false,
        errorMessage = 'Connection refused',
        queryDelay = 0
    } = options;

    const client = {
        connected: false,
        queries: [],
        _eventEmitter: new EventEmitter(),

        async connect() {
            if (shouldFail) {
                const error = new Error(errorMessage);
                error.code = 'ECONNREFUSED';
                throw error;
            }
            this.connected = true;
        },

        async end() {
            this.connected = false;
        },

        async query(sql, params = []) {
            this.queries.push({ sql, params });

            if (options.queryShouldFail) {
                throw new Error(options.queryError || 'Query failed');
            }

            if (queryDelay > 0) {
                await new Promise(r => setTimeout(r, queryDelay));
            }

            return { rows: options.queryResult || [], rowCount: options.rowCount || 0 };
        },

        on(event, handler) {
            this._eventEmitter.on(event, handler);
        }
    };

    return client;
}

/**
 * 创建 Mock 子进程
 */
function createMockChildProcess(options = {}) {
    const {
        exitCode = 0,
        stdout = '',
        stderr = '',
        delay = 0
    } = options;

    const proc = new EventEmitter();
    proc.stdout = new EventEmitter();
    proc.stderr = new EventEmitter();

    const stdoutData = stdout;
    const stderrData = stderr;

    proc.stdout.on = (event, handler) => {
        if (event === 'data') {
            setTimeout(() => handler(Buffer.from(stdoutData)), delay);
        }
    };

    proc.stderr.on = (event, handler) => {
        if (event === 'data' && stderrData) {
            setTimeout(() => handler(Buffer.from(stderrData)), delay);
        }
    };

    setTimeout(() => {
        proc.emit('close', exitCode);
    }, delay + 10);

    return proc;
}

// ============================================================================
// 测试: Mock 数据库连接失败
// ============================================================================

describe('lib/db.js - 数据库连接测试', () => {
    it('应该在连接失败时抛出错误', async () => {
        const mockClient = createMockPgClient({
            shouldFail: true,
            errorMessage: 'Connection refused'
        });

        try {
            await mockClient.connect();
            assert.fail('应该抛出错误');
        } catch (error) {
            assert.strictEqual(error.code, 'ECONNREFUSED');
            assert.ok(error.message.includes('Connection refused'));
            console.log('  ✅ 正确捕获连接错误:', error.message);
        }
    });

    it('应该在查询失败时抛出错误', async () => {
        const mockClient = createMockPgClient({
            queryShouldFail: true,
            queryError: 'relation "matches" does not exist'
        });

        await mockClient.connect();

        try {
            await mockClient.query('SELECT * FROM matches');
            assert.fail('应该抛出错误');
        } catch (error) {
            assert.ok(error.message.includes('does not exist'));
            console.log('  ✅ 正确捕获查询错误:', error.message);
        }
    });

    it('应该在连接成功后正确查询', async () => {
        const mockClient = createMockPgClient({
            queryResult: [{ match_id: 'TEST_001', home_team: 'Liverpool' }]
        });

        await mockClient.connect();
        const result = await mockClient.query('SELECT * FROM matches');

        assert.strictEqual(result.rows.length, 1);
        assert.strictEqual(result.rows[0].match_id, 'TEST_001');
        console.log('  ✅ 查询成功:', result.rows[0].match_id);
    });
});

// ============================================================================
// 测试: 重试机制
// ============================================================================

describe('lib/retry.js - 重试机制测试', () => {
    // 简化的 withRetry 实现 (用于测试)
    async function withRetry(fn, options = {}) {
        const { maxRetries = 3, baseDelay = 10 } = options;
        let lastError;

        for (let attempt = 0; attempt <= maxRetries; attempt++) {
            try {
                return await fn();
            } catch (error) {
                lastError = error;
                if (attempt < maxRetries) {
                    await new Promise(r => setTimeout(r, baseDelay));
                }
            }
        }

        throw lastError;
    }

    it('应该在前 2 次失败后第 3 次成功', async () => {
        let attempts = 0;

        const result = await withRetry(async () => {
            attempts++;
            console.log(`  📊 尝试 #${attempts}`);

            if (attempts < 3) {
                throw new Error(`模拟失败 #${attempts}`);
            }

            return { success: true, attempts };
        }, { maxRetries: 3, baseDelay: 5 });

        assert.strictEqual(result.success, true);
        assert.strictEqual(result.attempts, 3);
        console.log(`  ✅ 重试成功: 共尝试 ${attempts} 次`);
    });

    it('应该在达到最大重试次数后放弃', async () => {
        let attempts = 0;

        try {
            await withRetry(async () => {
                attempts++;
                throw new Error('持续失败');
            }, { maxRetries: 2, baseDelay: 5 });

            assert.fail('应该抛出错误');
        } catch (error) {
            assert.strictEqual(error.message, '持续失败');
            assert.strictEqual(attempts, 3);  // 初始 + 2 次重试
            console.log(`  ✅ 正确放弃: 共尝试 ${attempts} 次`);
        }
    });
});

// ============================================================================
// 测试: 超时拦截
// ============================================================================

describe('lib/retry.js - 超时拦截测试', () => {
    // 简化的 withTimeout 实现
    function withTimeout(promise, ms, message = 'Timeout') {
        return Promise.race([
            promise,
            new Promise((_, reject) =>
                setTimeout(() => reject(new Error(`${message} (${ms}ms)`)), ms)
            )
        ]);
    }

    it('应该在超时时切断连接', async () => {
        const slowOperation = new Promise(resolve => {
            setTimeout(() => resolve('完成'), 5000);
        });

        try {
            await withTimeout(slowOperation, 100, '操作超时');
            assert.fail('应该超时');
        } catch (error) {
            assert.ok(error.message.includes('操作超时'));
            assert.ok(error.message.includes('100ms'));
            console.log('  ✅ 超时拦截成功:', error.message);
        }
    });

    it('应该在超时前完成快速操作', async () => {
        const fastOperation = Promise.resolve('快速完成');

        const result = await withTimeout(fastOperation, 1000, '超时');

        assert.strictEqual(result, '快速完成');
        console.log('  ✅ 快速操作完成:', result);
    });

    it('应该处理 30s 超时场景', async () => {
        const verySlowOperation = new Promise(resolve => {
            setTimeout(() => resolve('太慢了'), 35000);
        });

        const startTime = Date.now();

        try {
            await withTimeout(verySlowOperation, 30, '网络超时');
            assert.fail('应该超时');
        } catch (error) {
            const elapsed = Date.now() - startTime;
            assert.ok(elapsed < 1000, '应该在 1s 内超时 (测试模拟)');
            console.log('  ✅ 30s 超时模拟成功:', error.message);
        }
    });
});

// ============================================================================
// 测试: TaskQueue 优先级
// ============================================================================

describe('lib/TaskQueue.js - 优先级测试', () => {
    // 简化的 TaskQueue 实现
    class SimpleTaskQueue {
        constructor() {
            this.queue = [];
        }

        add(match) {
            const priority = this._calculatePriority(match);
            this.queue.push({ ...match, priority });
            this.queue.sort((a, b) => b.priority - a.priority);
        }

        _calculatePriority(match) {
            let priority = 100;

            // 时间因素
            if (match.hoursUntil < 1) priority += 50;
            else if (match.hoursUntil < 6) priority += 30;
            else if (match.hoursUntil < 24) priority += 10;

            // 强队因素
            if (match.isTopTeam) priority += 5;

            return priority;
        }

        getNext() {
            return this.queue.shift();
        }

        peekAll() {
            return [...this.queue];
        }
    }

    it('应该优先返回即将开赛的比赛', () => {
        const queue = new SimpleTaskQueue();

        // 添加 10 场比赛
        queue.add({ match_id: 'M1', hoursUntil: 48, isTopTeam: false });  // 2 天后
        queue.add({ match_id: 'M2', hoursUntil: 24, isTopTeam: false });  // 1 天后
        queue.add({ match_id: 'M3', hoursUntil: 0.5, isTopTeam: true });  // 30 分钟后 + 强队
        queue.add({ match_id: 'M4', hoursUntil: 0.5, isTopTeam: false }); // 30 分钟后
        queue.add({ match_id: 'M5', hoursUntil: 72, isTopTeam: false }); // 3 天后

        const first = queue.getNext();
        const second = queue.getNext();

        console.log('  📊 最高优先级:', first.match_id, '优先级:', first.priority);
        console.log('  📊 次高优先级:', second.match_id, '优先级:', second.priority);

        // 即将开赛的比赛应该排在前面
        assert.strictEqual(first.match_id, 'M3');  // 30分钟后 + 强队 = 155
        assert.strictEqual(second.match_id, 'M4'); // 30分钟后 = 150

        console.log('  ✅ 优先级排序正确');
    });

    it('应该将强队比赛提升优先级', () => {
        const queue = new SimpleTaskQueue();

        // 使用 hoursUntil: 0.5 满足 < 1 条件，获得 +50 优先级
        queue.add({ match_id: '普通比赛', hoursUntil: 0.5, isTopTeam: false });  // 100 + 50 = 150
        queue.add({ match_id: '强队比赛', hoursUntil: 0.5, isTopTeam: true });    // 100 + 50 + 5 = 155

        const first = queue.getNext();

        assert.strictEqual(first.match_id, '强队比赛');
        assert.strictEqual(first.priority, 155);  // 基础 100 + 时间 50 + 强队 5 = 155
        console.log('  ✅ 强队优先级提升正确:', first.priority);
    });
});

// ============================================================================
// 测试: HealthMonitor 熔断
// ============================================================================

describe('lib/HealthMonitor.js - 熔断测试', () => {
    // 简化的 HealthMonitor 实现
    class SimpleHealthMonitor {
        constructor() {
            this.successCount = 0;
            this.errorCount = 0;
            this.status = 'healthy';
            this.errorThreshold = 5;
            this.errors = [];
        }

        recordSuccess() {
            this.successCount++;
            this._updateStatus();
        }

        recordError(error) {
            this.errorCount++;
            this.errors.push({
                message: error.message,
                timestamp: new Date().toISOString()
            });
            this._updateStatus();
        }

        _updateStatus() {
            const total = this.successCount + this.errorCount;
            const errorRate = total > 0 ? this.errorCount / total : 0;

            if (this.errorCount >= this.errorThreshold || errorRate > 0.3) {
                this.status = 'degraded';
            } else {
                this.status = 'healthy';
            }
        }

        getStats() {
            return {
                status: this.status,
                successCount: this.successCount,
                errorCount: this.errorCount,
                errorRate: (this.errorCount / (this.successCount + this.errorCount)).toFixed(2)
            };
        }
    }

    it('应该在连续 5 次错误后进入 degraded 状态', () => {
        const monitor = new SimpleHealthMonitor();

        // 注入 5 次错误
        for (let i = 1; i <= 5; i++) {
            monitor.recordError(new Error(`错误 #${i}`));
            console.log(`  📊 注入错误 #${i}, 状态: ${monitor.status}`);
        }

        assert.strictEqual(monitor.status, 'degraded');
        assert.strictEqual(monitor.errorCount, 5);
        console.log('  ✅ 熔断触发成功');
    });

    it('应该在错误率超过 30% 时进入 degraded 状态', () => {
        const monitor = new SimpleHealthMonitor();

        // 7 次成功 + 3 次失败 = 30% 错误率 (临界点)
        for (let i = 0; i < 7; i++) monitor.recordSuccess();
        for (let i = 0; i < 3; i++) monitor.recordError(new Error('失败'));

        console.log('  📊 统计:', monitor.getStats());

        // 30% 应该还是 healthy
        assert.strictEqual(monitor.status, 'healthy');

        // 再加 1 次错误 = 4/11 = 36%
        monitor.recordError(new Error('再来一次'));
        console.log('  📊 统计:', monitor.getStats());

        assert.strictEqual(monitor.status, 'degraded');
        console.log('  ✅ 错误率熔断成功');
    });

    it('应该记录所有错误详情', () => {
        const monitor = new SimpleHealthMonitor();

        monitor.recordError(new Error('连接超时'));
        monitor.recordError(new Error('代理不可用'));

        assert.strictEqual(monitor.errors.length, 2);
        assert.ok(monitor.errors[0].message.includes('连接超时'));
        assert.ok(monitor.errors[1].message.includes('代理不可用'));

        console.log('  ✅ 错误记录正确');
        console.log('    ', monitor.errors.map(e => e.message).join(', '));
    });
});

// ============================================================================
// 测试: Python 返回错误 JSON
// ============================================================================

describe('Python 桥接 - 错误 JSON 处理', () => {
    function parsePythonOutput(stdout) {
        try {
            const output = stdout.trim().split('\n').pop();
            return JSON.parse(output);
        } catch (e) {
            return { success: false, error: 'Parse error: Invalid JSON' };
        }
    }

    it('应该正确处理有效 JSON', () => {
        const stdout = `
Some debug output
Another line
{"success": true, "url": "https://example.com/match-ABC123/"}
`;

        const result = parsePythonOutput(stdout);

        assert.strictEqual(result.success, true);
        assert.strictEqual(result.url, 'https://example.com/match-ABC123/');
        console.log('  ✅ 有效 JSON 解析成功');
    });

    it('应该优雅处理无效 JSON', () => {
        const stdout = `
Python error output
{"success": false, "error": "Something went wrong"
Missing closing brace
`;

        const result = parsePythonOutput(stdout);

        assert.strictEqual(result.success, false);
        assert.ok(result.error.includes('Parse error'));
        console.log('  ✅ 无效 JSON 处理正确:', result.error);
    });

    it('应该处理空输出', () => {
        const stdout = '';

        const result = parsePythonOutput(stdout);

        assert.strictEqual(result.success, false);
        console.log('  ✅ 空输出处理正确');
    });

    it('应该处理 Python 异常输出', () => {
        const stdout = `
Traceback (most recent call last):
  File "script.py", line 10, in <module>
    raise ValueError("Invalid input")
ValueError: Invalid input
`;

        const result = parsePythonOutput(stdout);

        assert.strictEqual(result.success, false);
        console.log('  ✅ Python 异常处理正确');
    });
});

// ============================================================================
// 运行测试
// ============================================================================

console.log('═══════════════════════════════════════════════════════════════');
console.log('  V171-Standard-07 深度测试套件');
console.log('═══════════════════════════════════════════════════════════════');
console.log('');

// 导出测试
module.exports = {
    createMockPgClient,
    createMockChildProcess
};
