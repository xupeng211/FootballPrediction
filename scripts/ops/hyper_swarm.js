#!/usr/bin/env node
/**
 * V4.46.4 超频蜂群收割器 - HYPER-DRIVE
 * ======================================
 *
 * 15 并发 + Worker 池化 + 浏览器只启动一次
 * 预期吞吐量: 0.5 场/秒 (10x 提升)
 *
 * @module scripts/ops/hyper_swarm
 * @version V4.46.4-HYPER-DRIVE
 */

'use strict';

const { SwarmHarvester } = require('../../src/infrastructure/harvesters/SwarmHarvester');
const { Pool } = require('pg');

// 数据库配置
const DB_CONFIG = {
    host: process.env.DB_HOST || 'localhost',
    port: parseInt(process.env.DB_PORT) || 5432,
    database: process.env.DB_NAME || 'football_db',
    user: process.env.DB_USER || 'football_user',
    password: process.env.DB_PASSWORD,
    max: 30
};

async function main() {
    console.log('');
    console.log('╔═══════════════════════════════════════════════════════════════╗');
    console.log('║  🚀 TITAN-V4.46.4 超频蜂群收割器 (HYPER-DRIVE)               ║');
    console.log('║  Worker 池化 | 浏览器只启动一次 | 10x 吞吐量                  ║');
    console.log('╚═══════════════════════════════════════════════════════════════╝');

    const pool = new Pool(DB_CONFIG);

    // 获取待收割比赛
    const result = await pool.query(`
        SELECT m.match_id, m.home_team, m.away_team, m.match_date
        FROM matches m
        LEFT JOIN raw_match_data r ON m.match_id = r.match_id
        WHERE r.match_id IS NULL
        ORDER BY m.match_date DESC
    `);

    const pendingMatches = result.rows;
    const total = pendingMatches.length;

    console.log(`📊 待收割比赛: ${total} 场`);
    console.log(`🐝 并发 Worker: 15 (池化模式)`);
    console.log(`⏱️  优化延迟: 1-3s (超频模式)`);
    console.log('');

    if (total === 0) {
        console.log('✅ 所有比赛已收割完成！');
        await pool.end();
        return;
    }

    // 提取 match_id 列表
    const matchIds = pendingMatches.map(m => m.match_id);

    // 创建超频蜂群收割器 (V4.46.4 HYPER-DRIVE)
    const swarm = new SwarmHarvester({
        concurrency: 15,
        initStaggerMs: 500,  // Worker 初始化错峰 500ms
        verboseLogging: true,
        harvesterOptions: {
            minDelayMs: 1000,   // V4.46.4 超频: 1-3s
            maxDelayMs: 3000,
            maxRetries: 3,
            skipZombieCleanup: true
        }
    });

    // 启动收割
    const startTime = Date.now();
    const report = await swarm.batchRun(matchIds, 15);
    const elapsed = (Date.now() - startTime) / 1000;

    // 输出最终报告
    console.log('');
    console.log('╔═══════════════════════════════════════════════════════════════╗');
    console.log('║  📊 V4.46.4 HYPER-DRIVE 最终报告                              ║');
    console.log('╚═══════════════════════════════════════════════════════════════╝');
    console.log(`  总任务: ${report.total} 场`);
    console.log(`  成功: ${report.success} 场`);
    console.log(`  失败: ${report.failed} 场`);
    console.log(`  成功率: ${report.successRate}%`);
    console.log(`  总耗时: ${elapsed.toFixed(1)} 秒`);
    console.log(`  吞吐量: ${report.avgSpeed.toFixed(2)} 场/秒`);
    console.log('');

    // 性能评估
    if (report.avgSpeed >= 0.3) {
        console.log('  🚀 性能评级: EXCELLENT (吞吐量 >= 0.3 场/秒)');
    } else if (report.avgSpeed >= 0.1) {
        console.log('  ✅ 性能评级: GOOD (吞吐量 >= 0.1 场/秒)');
    } else {
        console.log('  ⚠️  性能评级: NEEDS IMPROVEMENT (吞吐量 < 0.1 场/秒)');
    }

    console.log('═══════════════════════════════════════════════════════════════');

    await pool.end();

    // 返回成功数用于后续判断
    process.exit(report.success > 0 ? 0 : 1);
}

main().catch(err => {
    console.error('❌ 超频收割失败:', err);
    process.exit(1);
});
