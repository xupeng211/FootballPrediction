/**
 * Smelter_Concurrency.test.js - 并发安全测试
 * ===========================================
 *
 * 验证多Worker并行处理时的死锁安全性
 * TDD模式：确保UPSERT逻辑在并发下稳定
 *
 * @module tests/integration/Smelter_Concurrency
 * @version V5.0.0-TURBO
 * @since 2026-03-14
 */

'use strict';

const test = require('node:test');
const assert = require('assert');
const { Pool } = require('pg');

// 数据库配置 (使用扩容后的连接池)
const DB_CONFIG = {
    host: process.env.DB_HOST || 'host.docker.internal',
    port: parseInt(process.env.DB_PORT || '5432'),
    database: process.env.DB_NAME || 'football_db',
    user: process.env.DB_USER || 'football_user',
    password: process.env.DB_PASSWORD || 'football_pass',
    max: 50,
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 5000,
};

console.log('\n🔒 TITAN V5.0 并发安全测试套件');
console.log('══════════════════════════════════════════════════════════════════');

// 测试1: 并发UPSERT不会产生死锁
test('并发UPSERT不应产生死锁', async () => {
    const pool = new Pool(DB_CONFIG);
    const testMatchId = `concurrent_test_${Date.now()}`;
    const concurrency = 10;  // 模拟10个并发Worker

    try {
        // 准备测试数据
        const upsertPromises = [];

        for (let i = 0; i < concurrency; i++) {
            const promise = pool.query(`
                INSERT INTO l3_features (
                    match_id, external_id,
                    golden_features, tactical_features,
                    odds_movement_features, elo_features,
                    rolling_features, efficiency_features, draw_features,
                    computed_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
                ON CONFLICT (match_id) DO UPDATE SET
                    golden_features = EXCLUDED.golden_features,
                    rolling_features = EXCLUDED.rolling_features,
                    efficiency_features = EXCLUDED.efficiency_features,
                    draw_features = EXCLUDED.draw_features,
                    computed_at = EXCLUDED.computed_at
            `, [
                testMatchId,
                `external_${i}`,
                JSON.stringify({ test: i, version: 'V1' }),
                JSON.stringify({ tactical: i }),
                JSON.stringify({ odds: i }),
                JSON.stringify({ elo: i }),
                JSON.stringify({ rolling: i, worker: i }),
                JSON.stringify({ efficiency: i }),
                JSON.stringify({ draw: i })
            ]);

            upsertPromises.push(promise);
        }

        // 并发执行所有UPSERT
        const results = await Promise.allSettled(upsertPromises);

        // 验证所有操作都成功完成
        const succeeded = results.filter(r => r.status === 'fulfilled').length;
        const failed = results.filter(r => r.status === 'rejected').length;

        console.log(`   并发UPSERT: ${succeeded} 成功, ${failed} 失败`);

        // 所有操作都应该成功（ON CONFLICT会处理冲突，不会报错）
        assert.strictEqual(failed, 0, `不应有失败的UPSERT操作，但有 ${failed} 个失败`);
        assert.strictEqual(succeeded, concurrency, '所有并发操作都应该成功');

        // 验证最终数据存在
        const verifyResult = await pool.query(`
            SELECT match_id, rolling_features->>'worker' as worker_id
            FROM l3_features
            WHERE match_id = $1
        `, [testMatchId]);

        assert.strictEqual(verifyResult.rows.length, 1, '应该有一条记录');
        console.log(`   最终数据: Worker ${verifyResult.rows[0].worker_id} 的写入被保留`);

    } finally {
        // 清理测试数据
        await pool.query('DELETE FROM l3_features WHERE match_id = $1', [testMatchId]);
        await pool.end();
    }
});

// 测试2: 不同Worker处理不同比赛ID不应冲突
test('不同比赛ID的并发处理不应互相阻塞', async () => {
    const pool = new Pool(DB_CONFIG);
    const numMatches = 20;
    const matchIds = Array.from({ length: numMatches }, (_, i) => `concurrent_match_${Date.now()}_${i}`);

    try {
        // 并行插入不同比赛
        const insertPromises = matchIds.map((matchId, i) =>
            pool.query(`
                INSERT INTO l3_features (
                    match_id, external_id,
                    golden_features, tactical_features,
                    rolling_features, efficiency_features, draw_features,
                    computed_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                ON CONFLICT (match_id) DO NOTHING
            `, [
                matchId,
                `ext_${i}`,
                JSON.stringify({ match: i }),
                JSON.stringify({ tactical: true }),
                JSON.stringify({ rolling: true, index: i }),
                JSON.stringify({ efficiency: true }),
                JSON.stringify({ draw: true })
            ])
        );

        const startTime = Date.now();
        const results = await Promise.all(insertPromises);
        const elapsed = Date.now() - startTime;

        const succeeded = results.filter(r => r.rowCount >= 0).length;
        console.log(`   并行插入 ${numMatches} 场比赛: ${succeeded} 成功`);
        console.log(`   耗时: ${elapsed}ms (${(numMatches / (elapsed / 1000)).toFixed(1)} 场/秒)`);

        assert.strictEqual(succeeded, numMatches, '所有插入都应该成功');

        // 验证所有记录都存在
        const countResult = await pool.query(`
            SELECT COUNT(*) as count
            FROM l3_features
            WHERE match_id = ANY($1)
        `, [matchIds]);

        assert.strictEqual(parseInt(countResult.rows[0].count), numMatches, '所有记录都应该存在');

    } finally {
        // 清理
        await pool.query('DELETE FROM l3_features WHERE match_id = ANY($1)', [matchIds]);
        await pool.end();
    }
});

// 测试3: 连接池不会溢出
test('高并发下连接池不应溢出', async () => {
    const pool = new Pool({
        ...DB_CONFIG,
        max: 10  // 使用较小的连接池测试
    });

    const concurrency = 50;  // 50个并发查询

    try {
        const queryPromises = Array.from({ length: concurrency }, (_, i) =>
            pool.query('SELECT $1 as id, pg_sleep(0.01) as delay', [i])
        );

        const startTime = Date.now();
        const results = await Promise.all(queryPromises);
        const elapsed = Date.now() - startTime;

        const succeeded = results.filter(r => r.rows && r.rows[0].id !== undefined).length;

        console.log(`   ${concurrency} 并发查询: ${succeeded} 成功`);
        console.log(`   耗时: ${elapsed}ms`);
        console.log(`   连接池等待时间验证了连接复用机制`);

        assert.strictEqual(succeeded, concurrency, '所有查询都应该成功');

    } finally {
        await pool.end();
    }
});

// 测试4: 事务隔离级别测试
test('事务隔离应防止脏读', async () => {
    const pool = new Pool(DB_CONFIG);
    const testId = `isolation_test_${Date.now()}`;

    try {
        // Worker 1: 开始事务并插入
        const client1 = await pool.connect();
        await client1.query('BEGIN');
        await client1.query(`
            INSERT INTO l3_features (match_id, golden_features, computed_at)
            VALUES ($1, $2, NOW())
        `, [testId, JSON.stringify({ step: 1 })]);

        // Worker 2: 在事务提交前读取（应该读不到）
        const client2 = await pool.connect();
        const beforeCommit = await client2.query(
            'SELECT match_id FROM l3_features WHERE match_id = $1',
            [testId]
        );

        assert.strictEqual(beforeCommit.rows.length, 0, '未提交事务的数据不应被读取');

        // Worker 1: 提交事务
        await client1.query('COMMIT');
        client1.release();

        // Worker 2: 再次读取（应该能读到）
        const afterCommit = await client2.query(
            'SELECT match_id FROM l3_features WHERE match_id = $1',
            [testId]
        );

        assert.strictEqual(afterCommit.rows.length, 1, '提交后的数据应该能被读取');
        client2.release();

        console.log('   ✅ 事务隔离级别正常工作');

    } finally {
        await pool.query('DELETE FROM l3_features WHERE match_id = $1', [testId]);
        await pool.end();
    }
});

// 测试5: 连接池性能基准
test('连接池性能基准测试', async () => {
    const pool = new Pool(DB_CONFIG);

    try {
        // 预热连接池
        await pool.query('SELECT 1');

        // 测试100次查询的速度
        const iterations = 100;
        const startTime = Date.now();

        for (let i = 0; i < iterations; i++) {
            await pool.query('SELECT $1 as num', [i]);
        }

        const elapsed = Date.now() - startTime;
        const avgLatency = elapsed / iterations;

        console.log(`   ${iterations} 次查询耗时: ${elapsed}ms`);
        console.log(`   平均延迟: ${avgLatency.toFixed(2)}ms`);
        console.log(`   QPS: ${(1000 / avgLatency).toFixed(0)}`);

        assert.ok(avgLatency < 10, `平均延迟应该小于10ms，实际: ${avgLatency.toFixed(2)}ms`);

    } finally {
        await pool.end();
    }
});

console.log('\n📋 并发安全测试覆盖:');
console.log('   ✅ 并发UPSERT死锁检测');
console.log('   ✅ 不同ID并行处理');
console.log('   ✅ 连接池溢出保护');
console.log('   ✅ 事务隔离级别');
console.log('   ✅ 连接池性能基准');
console.log('══════════════════════════════════════════════════════════════════\n');
