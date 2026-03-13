#!/usr/bin/env node
/**
 * TITAN-WAREHOUSE-SMELT - 全量特征熔炼
 * =====================================
 *
 * 处理 raw_match_data 表中所有数据，无批次限制
 *
 * 用法:
 *   node scripts/ops/smelt_all_full.js
 *
 * @version V1.0.0
 */

'use strict';

const { FeatureSmelter } = require('../../src/feature_engine/smelter/FeatureSmelter');

/**
 * 主函数
 */
async function main() {
    console.log('🔥 TITAN-WAREHOUSE-SMELT 启动');
    console.log('📦 处理模式: 全量无限制');
    console.log('');

    // 创建自定义配置的 Smelter (大批量)
    const smelter = new FeatureSmelter({
        batchSize: 50000,  // 足够大的数字来处理所有数据
        delayMs: 0,        // 无延时
        rollingLookback: 5
    });

    const startTime = Date.now();

    try {
        await smelter.init();

        // 获取待处理数量
        const pool = smelter.pool;
        const countResult = await pool.query(`
            SELECT COUNT(*) as total
            FROM matches m
            INNER JOIN raw_match_data r ON m.match_id = r.match_id
            LEFT JOIN l3_features l3 ON m.match_id = l3.match_id
            WHERE m.external_id IS NOT NULL
              AND l3.match_id IS NULL
        `);
        const pendingCount = parseInt(countResult.rows[0].total);

        console.log(`📊 待处理比赛: ${pendingCount} 场`);
        console.log('🚀 开始全量熔炼...');
        console.log('');

        // 执行全量熔炼（强制重算所有记录）
        const stats = await smelter.run({ fullRecalculate: true });

        const duration = Date.now() - startTime;

        console.log('');
        console.log('🎉 TITAN-WAREHOUSE-SMELT 完成');
        console.log('═══════════════════════════════════════');
        console.log(`📊 总处理数: ${stats.total}`);
        console.log(`✅ 成功熔炼: ${stats.success}`);
        console.log(`⏭️ 跳过数量: ${stats.skipped}`);
        console.log(`❌ 失败数量: ${stats.failed}`);
        console.log(`⏱️ 总耗时: ${(duration/1000).toFixed(1)} 秒`);
        console.log(`🚀 平均速度: ${(stats.total/(duration/1000)).toFixed(0)} 场/秒`);
        console.log('═══════════════════════════════════════');

    } catch (err) {
        console.error('💥 熔炼失败:', err.message);
        process.exit(1);
    } finally {
        await smelter.close();
    }
}

main().catch(err => {
    console.error('💥 致命错误:', err);
    process.exit(1);
});
