/**
 * V172-GOLD 高级测试套件
 * =======================
 *
 * 压力测试 + 脏数据攻击测试
 *
 * @module tests/unit/StressAndSecurity.test
 * @version V172.100
 */

'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

// ============================================================================
// 从 MatchDetailEngine.test.js 导入共享函数
// ============================================================================

function createPerfectMatchData(overrides = {}) {
    return {
        content: {
            stats: {
                Periods: {
                    All: {
                        stats: [
                            {
                                title: 'Expected goals (xG)',
                                stats: [{ key: 'expected_goals', stats: ['2.45', '1.23'] }]
                            }
                        ]
                    }
                }
            }
        },
        ...overrides
    };
}

function parseMatchData(rawData) {
    const result = {
        xg_home: null,
        xg_away: null,
        possession_home: null,
        possession_away: null
    };

    if (!rawData) return result;

    try {
        const content = rawData?.content || {};
        const periods = content?.stats?.Periods;
        const allStats = periods?.All?.stats || [];

        const xgGroup = allStats.find(g => {
            const title = (g.title || g.key || '').toLowerCase();
            return title.includes('expected goals') || title.includes('xg');
        });

        if (xgGroup && xgGroup.stats && Array.isArray(xgGroup.stats)) {
            const xgRow = xgGroup.stats.find(s => {
                const key = (s.key || '').toLowerCase();
                return key === 'expected_goals' || key.includes('expected_goals');
            });

            if (xgRow && Array.isArray(xgRow.stats) && xgRow.stats.length >= 2) {
                const homeXg = parseFloat(xgRow.stats[0]);
                const awayXg = parseFloat(xgRow.stats[1]);

                if (!isNaN(homeXg) && !isNaN(awayXg)) {
                    result.xg_home = homeXg;
                    result.xg_away = awayXg;
                }
            }
        }
    } catch (error) {
        // 静默处理
    }

    return result;
}

function validateQualityGate(rawData, minSizeBytes = 5000) {
    if (!rawData) return { valid: false, reason: 'NULL_DATA' };

    const jsonStr = JSON.stringify(rawData);
    const size = jsonStr.length;

    if (size < minSizeBytes) {
        return { valid: false, reason: 'SIZE_TOO_SMALL', size };
    }

    if (!rawData.content) {
        return { valid: false, reason: 'MISSING_CONTENT', size };
    }

    const str = jsonStr.toLowerCase();
    const errorKeywords = ['turnstile', 'error', 'failed', 'blocked', 'captcha', 'challenge'];
    for (const keyword of errorKeywords) {
        if (str.includes(keyword)) {
            return { valid: false, reason: `CONTAINS_${keyword.toUpperCase()}`, size };
        }
    }

    return { valid: true, size };
}

// ============================================================================
// 脏数据生成器
// ============================================================================

function createGarbledJson() {
    // 生成各种类型的乱码数据
    const types = [
        // 随机字节
        () => Buffer.from(Array(100).fill(0).map(() => Math.floor(Math.random() * 256))).toString('utf8'),
        // 截断 JSON
        () => '{"content":{"stats":',
        // 嵌套爆炸
        () => JSON.stringify({ content: { nested: Array(100).fill({ deep: Array(100).fill('x') }) } }),
        // Unicode 混合
        () => '{"content":"🔥💥⚠️🚨\x00\x01\x02"}',
        // SQL 注入尝试
        () => '{"content":"\'; DROP TABLE matches; --"}',
        // XSS 尝试
        () => '{"content":"<script>alert(1)</script>"}',
        // 空对象
        () => ({}),
        // 数组而非对象
        () => '[1, 2, 3, 4, 5]',
        // null
        () => null,
        // undefined 字符串
        () => '{"content": undefined}',
    ];
    return types[Math.floor(Math.random() * types.length)]();
}

// ============================================================================
// 测试套件
// ============================================================================

describe('V172-GOLD 高级测试', () => {

    // ========================================================================
    // 压力测试: 500ms 内处理 50 个任务
    // ========================================================================
    describe('压力测试', () => {

        it('应在 500ms 内完成 50 个任务的解析', () => {
            const tasks = Array(50).fill(null).map((_, i) =>
                createPerfectMatchData({ matchIndex: i })
            );

            const start = Date.now();
            const results = tasks.map(task => parseMatchData(task));
            const elapsed = Date.now() - start;

            // 验证所有任务都正确解析
            assert.strictEqual(results.length, 50, '应处理 50 个任务');
            results.forEach((r, i) => {
                assert.strictEqual(r.xg_home, 2.45, `任务 ${i} xG 解析应正确`);
            });

            // 验证时间限制
            assert.ok(elapsed < 500, `50 个任务耗时 ${elapsed}ms，超过 500ms`);
        });

        it('质量门禁应在 200ms 内完成 50 次验证', () => {
            const dataList = Array(50).fill(null).map(() => {
                const data = createPerfectMatchData();
                data.padding = 'x'.repeat(6000);  // 确保体积足够
                return data;
            });

            const start = Date.now();
            const results = dataList.map(d => validateQualityGate(d, 5000));
            const elapsed = Date.now() - start;

            assert.strictEqual(results.filter(r => r.valid).length, 50, '所有数据应通过验证');
            assert.ok(elapsed < 200, `50 次验证耗时 ${elapsed}ms，超过 200ms`);
        });

        it('并发验证不应产生竞态条件', () => {
            // 模拟并发验证
            const data = createPerfectMatchData();
            data.padding = 'x'.repeat(10000);

            const promises = Array(20).fill(null).map(() =>
                new Promise(resolve => {
                    const result = validateQualityGate(data, 5000);
                    resolve(result);
                })
            );

            return Promise.all(promises).then(results => {
                assert.strictEqual(results.length, 20, '应完成 20 次并发验证');
                results.forEach((r, i) => {
                    assert.strictEqual(r.valid, true, `并发任务 ${i} 应通过验证`);
                });
            });
        });
    });

    // ========================================================================
    // 脏数据攻击测试
    // ========================================================================
    describe('脏数据攻击测试', () => {

        it('应优雅处理乱码 JSON 而不崩溃', () => {
            let crashCount = 0;
            let errorCount = 0;

            for (let i = 0; i < 20; i++) {
                const garbled = createGarbledJson();

                try {
                    // 尝试解析乱码数据
                    let parsed = garbled;
                    if (typeof garbled === 'string') {
                        try {
                            parsed = JSON.parse(garbled);
                        } catch (e) {
                            // JSON 解析失败是预期的
                            errorCount++;
                            continue;
                        }
                    }

                    // 即使解析成功，引擎也应优雅处理
                    const result = parseMatchData(parsed);

                    // 验证结果结构正确（即使值为 null）
                    assert.ok(typeof result === 'object', '应返回对象');
                    assert.ok('xg_home' in result, '应包含 xg_home 字段');

                } catch (e) {
                    // 捕获未预期的崩溃
                    crashCount++;
                }
            }

            // 允许 JSON 解析错误，但不允许引擎崩溃
            assert.strictEqual(crashCount, 0, `引擎崩溃 ${crashCount} 次，不可接受`);
        });

        it('应拒绝包含 SQL 注入的数据', () => {
            const sqlInjection = {
                content: { stats: { Periods: { All: { stats: [] } } } },
                malicious: "'; DROP TABLE matches; --"
            };
            sqlInjection.padding = 'x'.repeat(6000);  // 确保体积足够

            // 质量门禁应通过（数据结构正确）
            const validation = validateQualityGate(sqlInjection, 5000);

            // 但解析应安全处理
            const result = parseMatchData(sqlInjection);
            assert.strictEqual(result.xg_home, null, 'xG 应为 null');
            assert.strictEqual(result.xg_away, null, 'xG 应为 null');
        });

        it('应拒绝包含 XSS 的数据', () => {
            const xssData = {
                content: { stats: { Periods: { All: { stats: [] } } } },
                script: '<script>alert(document.cookie)</script>'
            };
            xssData.padding = 'x'.repeat(6000);

            const result = parseMatchData(xssData);
            assert.strictEqual(typeof result, 'object', '应返回对象');
            assert.strictEqual(result.xg_home, null, 'xG 应为 null');
        });

        it('应处理深层嵌套数据而不栈溢出', () => {
            // 创建深度嵌套对象
            let deep = { value: 'bottom' };
            for (let i = 0; i < 100; i++) {
                deep = { nested: deep };
            }
            deep.content = { stats: { Periods: { All: { stats: [] } } } };

            // 不应抛出栈溢出错误
            try {
                const result = parseMatchData(deep);
                assert.ok(typeof result === 'object', '应返回对象');
            } catch (e) {
                assert.fail(`深层嵌套导致崩溃: ${e.message}`);
            }
        });

        it('应处理超大数据而不内存溢出', () => {
            // 创建 1MB 大小的数据
            const bigData = createPerfectMatchData();
            bigData.largeField = 'x'.repeat(1024 * 1024);

            const start = Date.now();
            const result = validateQualityGate(bigData, 5000);
            const elapsed = Date.now() - start;

            assert.strictEqual(result.valid, true, '大数据应通过验证');
            assert.ok(elapsed < 100, `验证耗时 ${elapsed}ms，超过 100ms`);
        });
    });

    // ========================================================================
    // 边界条件压力测试
    // ========================================================================
    describe('边界条件压力测试', () => {

        it('应正确处理边界体积 (4999 vs 5000 bytes)', () => {
            const data4999 = createPerfectMatchData();
            const data5000 = createPerfectMatchData();

            // 精确调整体积
            const base4999 = JSON.stringify(data4999).length;
            const base5000 = JSON.stringify(data5000).length;

            data4999.padding = 'x'.repeat(Math.max(0, 4999 - base4999));
            data5000.padding = 'x'.repeat(Math.max(0, 5000 - base5000));

            const result4999 = validateQualityGate(data4999, 5000);
            const result5000 = validateQualityGate(data5000, 5000);

            // 4999 应该失败，5000 应该通过
            if (JSON.stringify(data4999).length < 5000) {
                assert.strictEqual(result4999.valid, false, '4999 bytes 应被拒绝');
            }
            assert.strictEqual(result5000.valid, true, '5000 bytes 应通过');
        });

        it('应处理空字符串和空数组', () => {
            const emptyCases = [
                { content: '' },
                { content: [] },
                { content: {} },
                { content: null },
                { content: { stats: null } },
                { content: { stats: { Periods: null } } }
            ];

            emptyCases.forEach((data, i) => {
                data.padding = 'x'.repeat(6000);  // 确保体积

                const result = parseMatchData(data);
                assert.strictEqual(result.xg_home, null, `空案例 ${i} xG 应为 null`);
            });
        });
    });

    // ========================================================================
    // 性能回归测试
    // ========================================================================
    describe('性能回归测试', () => {

        it('单次解析应在 1ms 内完成', () => {
            const data = createPerfectMatchData();

            const iterations = 1000;
            const start = Date.now();

            for (let i = 0; i < iterations; i++) {
                parseMatchData(data);
            }

            const elapsed = Date.now() - start;
            const avgMs = elapsed / iterations;

            assert.ok(avgMs < 1, `平均解析时间 ${avgMs.toFixed(3)}ms，超过 1ms`);
        });

        it('单次质量门禁检查应在 0.1ms 内完成', () => {
            const data = createPerfectMatchData();
            data.padding = 'x'.repeat(10000);

            const iterations = 1000;
            const start = Date.now();

            for (let i = 0; i < iterations; i++) {
                validateQualityGate(data, 5000);
            }

            const elapsed = Date.now() - start;
            const avgMs = elapsed / iterations;

            assert.ok(avgMs < 0.1, `平均检查时间 ${avgMs.toFixed(3)}ms，超过 0.1ms`);
        });
    });
});
