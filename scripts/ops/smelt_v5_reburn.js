#!/usr/bin/env node
/**
 * TITAN V5.0 - 30维特征全量重炼
 * =============================
 *
 * 使用 SmelterOrchestrator 处理所有比赛
 * 生成30维特征（Golden + Tactical + Rolling + Efficiency + Draw）
 *
 * 用法:
 *   node scripts/ops/smelt_v5_reburn.js [--full-recalculate]
 *
 * @version V5.0.0-REBURN
 * @since 2026-03-14
 */

'use strict';

const { Pool } = require('pg');
const { SmelterOrchestrator } = require('../../src/feature_engine/smelter/SmelterOrchestrator');

// 数据库配置
const DB_CONFIG = {
    host: process.env.DB_HOST || 'host.docker.internal',
    port: parseInt(process.env.DB_PORT || '5432'),
    database: process.env.DB_NAME || 'football_db',
    user: process.env.DB_USER || 'football_user',
    password: process.env.DB_PASSWORD || 'football_pass',
    max: 10,
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 2000,
};

/**
 * 主函数
 */
async function main() {
    const args = process.argv.slice(2);
    const fullRecalculate = args.includes('--full-recalculate');

    console.log('\n' + '='.repeat(70));
    console.log('🔥 TITAN V5.0 - 30维特征全量重炼');
    console.log('='.repeat(70));
    console.log(`📅 时间: ${new Date().toISOString()}`);
    console.log(`🔄 模式: ${fullRecalculate ? '全量重算' : '增量处理'}`);
    console.log('='.repeat(70) + '\n');

    const pool = new Pool(DB_CONFIG);
    const startTime = Date.now();

    try {
        // 获取比赛总数
        const countResult = await pool.query(`
            SELECT COUNT(*) as total FROM matches WHERE status = 'Harvested'
        `);
        const totalMatches = parseInt(countResult.rows[0].total);
        console.log(`📊 数据库中比赛总数: ${totalMatches.toLocaleString()} 场`);

        // 获取已处理数量
        const processedResult = await pool.query(`
            SELECT COUNT(*) as processed FROM l3_features
        `);
        const processedCount = parseInt(processedResult.rows[0].processed);
        console.log(`✅ 已处理: ${processedCount.toLocaleString()} 场`);
        console.log(`⏳ 待处理: ${(totalMatches - processedCount).toLocaleString()} 场`);
        console.log();

        // 创建Orchestrator
        const orchestrator = new SmelterOrchestrator({
            pool,
            config: {
                batchSize: 100,
                delayMs: 10,
                enableStreaming: false
            }
        });

        // 运行熔炼
        const stats = await orchestrator.run({
            fullRecalculate,
            limit: null  // 无限制，处理全部
        });

        // 统计结果
        const duration = Date.now() - startTime;
        console.log('\n' + '='.repeat(70));
        console.log('✅ 重炼完成!');
        console.log('='.repeat(70));
        console.log(`📊 总比赛: ${stats.total}`);
        console.log(`✅ 成功: ${stats.success}`);
        console.log(`❌ 失败: ${stats.failed}`);
        console.log(`⏭️ 跳过: ${stats.skipped}`);
        console.log(`⏱️ 耗时: ${(duration / 1000).toFixed(2)} 秒`);
        console.log(`⚡ 速度: ${(stats.success / (duration / 1000)).toFixed(1)} 场/秒`);
        console.log('='.repeat(70));

        // 验证30维特征
        await verify30Features(pool);

    } catch (error) {
        console.error('\n❌ 重炼失败:', error.message);
        console.error(error.stack);
        process.exit(1);
    } finally {
        await pool.end();
    }
}

/**
 * 验证30维特征
 */
async function verify30Features(pool) {
    console.log('\n🔍 验证30维特征存储...');
    console.log('='.repeat(70));

    try {
        // 检查l3_features表结构
        const schemaResult = await pool.query(`
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'l3_features'
            ORDER BY ordinal_position
        `);

        console.log(`📋 l3_features表字段数: ${schemaResult.rows.length}`);

        // 检查是否有新特征字段
        const hasRolling = schemaResult.rows.some(r => r.column_name.includes('rolling'));
        const hasEfficiency = schemaResult.rows.some(r => r.column_name.includes('efficiency'));
        const hasDraw = schemaResult.rows.some(r => r.column_name.includes('draw'));

        console.log(`   Rolling特征字段: ${hasRolling ? '✅' : '⏳'}`);
        console.log(`   Efficiency特征字段: ${hasEfficiency ? '✅' : '⏳'}`);
        console.log(`   Draw特征字段: ${hasDraw ? '✅' : '⏳'}`);

        // 随机抽样检查
        const sampleResult = await pool.query(`
            SELECT match_id, golden_features, tactical_features
            FROM l3_features
            ORDER BY RANDOM()
            LIMIT 1
        `);

        if (sampleResult.rows.length > 0) {
            const sample = sampleResult.rows[0];
            console.log(`\n📸 随机抽样 (Match ID: ${sample.match_id})`);
            console.log(`   Golden特征: ${Object.keys(sample.golden_features || {}).length} 个字段`);
            console.log(`   Tactical特征: ${Object.keys(sample.tactical_features || {}).length} 个字段`);
        }

        console.log('='.repeat(70));

    } catch (error) {
        console.error('验证失败:', error.message);
    }
}

// 运行主函数
main();
