#!/usr/bin/env node
/**
 * V4.46.4 意甲专项收割器 - 低并发 + 长超时
 * ==========================================
 *
 * 针对被 403 拦截的比赛进行专项收割
 *
 * @module scripts/ops/hyper_swarm_stealth
 * @version V4.46.4
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
    max: 30
};

async function main() {
    console.log('');
    console.log('╔═══════════════════════════════════════════════════════════════╗');
    console.log('║  🔬 TITAN-V4.46.4 意甲专项收割器                             ║');
    console.log('║  低并发 | 长超时 | 高容错                                    ║');
    console.log('╚═══════════════════════════════════════════════════════════════╝');

    const pool = new Pool(DB_CONFIG);

    // 获取待收割比赛
    const result = await pool.query(`
        SELECT m.match_id, m.home_team, m.away_team, m.match_date
        FROM matches m
        LEFT JOIN raw_match_data r ON m.match_id = r.match_id
        WHERE r.match_id IS NULL
        ORDER BY m.match_date
    `);

    const pendingMatches = result.rows;
    const total = pendingMatches.length;

    console.log(`📊 待收割比赛: ${total} 场`);

    if (total === 0) {
        console.log('✅ 所有比赛已收割完成！');
        await pool.end();
        return;
    }

    pendingMatches.forEach(m => {
        console.log(`   - ${m.home_team} vs ${m.away_team} (${m.match_date.toISOString().slice(0, 10)})`);
    });
    console.log('');

    const matchIds = pendingMatches.map(m => m.match_id);

    // 低并发 + 长超时配置
    const swarm = new SwarmHarvester({
        concurrency: 3,  // 低并发
        initStaggerMs: 2000,  // 长错峰
        verboseLogging: true,
        harvesterOptions: {
            minDelayMs: 5000,   // 长延迟
            maxDelayMs: 10000,
            maxRetries: 5,      // 更多重试
            skipZombieCleanup: true
        }
    });

    const startTime = Date.now();
    const report = await swarm.batchRun(matchIds, 3);
    const elapsed = (Date.now() - startTime) / 1000;

    console.log('');
    console.log('╔═══════════════════════════════════════════════════════════════╗');
    console.log('║  📊 意甲专项收割完成报告                                      ║');
    console.log('╚═══════════════════════════════════════════════════════════════╝');
    console.log(`  总任务: ${report.total} 场`);
    console.log(`  成功: ${report.success} 场`);
    console.log(`  失败: ${report.failed} 场`);
    console.log(`  成功率: ${report.successRate}%`);
    console.log(`  总耗时: ${elapsed.toFixed(1)} 秒`);
    console.log('═══════════════════════════════════════════════════════════════');

    await pool.end();

    process.exit(report.success > 0 ? 0 : 1);
}

main().catch(err => {
    console.error('❌ 收割失败:', err);
    process.exit(1);
});
