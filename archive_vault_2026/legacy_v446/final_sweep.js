#!/usr/bin/env node
/**
 * V4.46.3 最终扫荡收割器
 * ========================
 *
 * 5 并发稳健模式，收割剩余 87 场硬骨头
 *
 * @module scripts/ops/final_sweep
 * @version V4.46.3
 */

'use strict';

const { SwarmHarvester } = require('../../src/infrastructure/harvesters/SwarmHarvester');
const { Pool } = require('pg');

const DB_CONFIG = {
    host: process.env.DB_HOST || 'localhost',
    port: parseInt(process.env.DB_PORT) || 5432,
    database: process.env.DB_NAME || 'football_db',
    user: process.env.DB_USER || 'football_user',
    password: process.env.DB_PASSWORD,
    max: 20
};

async function main() {
    console.log('╔═══════════════════════════════════════════════════════════════╗');
    console.log('║  🎯 TITAN-V4.46.3 最终扫荡收割器                              ║');
    console.log('║  5 并发 | 稳健模式 | 403 逃逸                                 ║');
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
    console.log(`🐝 并发 Worker: 5 (稳健模式)`);
    console.log(`⏱️  延迟: 3-6s | 重试: 5 次 | 403 冷却: 30s`);
    console.log('');

    if (total === 0) {
        console.log('✅ 所有比赛已收割完成！');
        await pool.end();
        return { success: 0, failed: 0, total: 0 };
    }

    const matchIds = pendingMatches.map(m => m.match_id);

    const swarm = new SwarmHarvester({
        concurrency: 5,
        staggerStartMs: 3000,
        staggerJitterMs: 1000,
        verboseLogging: true,
        harvesterOptions: {
            minDelayMs: 3000,
            maxDelayMs: 6000,
            maxRetries: 5,
            skipZombieCleanup: true
        }
    });

    const startTime = Date.now();
    const report = await swarm.batchRun(matchIds, 5);
    const elapsed = (Date.now() - startTime) / 1000;

    console.log('');
    console.log('╔═══════════════════════════════════════════════════════════════╗');
    console.log('║  📊 最终扫荡收割报告                                           ║');
    console.log('╚═══════════════════════════════════════════════════════════════╝');
    console.log(`  总任务: ${report.total} 场`);
    console.log(`  成功: ${report.success} 场`);
    console.log(`  失败: ${report.failed} 场`);
    console.log(`  成功率: ${report.successRate}%`);
    console.log(`  总耗时: ${elapsed.toFixed(1)} 秒`);
    console.log('═══════════════════════════════════════════════════════════════');

    await pool.end();

    return report;
}

main()
    .then(report => {
        process.exit(report.success > 0 ? 0 : 1);
    })
    .catch(err => {
        console.error('❌ 最终扫荡失败:', err);
        process.exit(1);
    });
