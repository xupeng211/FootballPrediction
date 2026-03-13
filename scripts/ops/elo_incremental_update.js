#!/usr/bin/env node
/**
 * Elo 增量更新脚本
 * ==================
 *
 * 扫描缺失 Elo 的已完赛比赛，自动计算并更新
 *
 * 用法:
 *   node scripts/ops/elo_incremental_update.js           # 增量更新
 *   node scripts/ops/elo_incremental_update.js --match 55_20242025_4803308  # 单场更新
 * @module scripts/ops/elo_incremental_update
 * @version V1.0.0
 */

'use strict';

const { EloAutoUpdater } = require('../../src/feature_engine/elo/EloAutoUpdater');

/**
 *
 */
async function main() {
    const args = process.argv.slice(2);
    const matchId = args.find(a => a.startsWith('--match'))?.split('=')[1] ||
                    args[args.indexOf('--match') + 1];

    console.log('\n' + '═'.repeat(60));
    console.log('  Elo 增量更新系统 V1.0');
    console.log('═'.repeat(60) + '\n');

    const updater = new EloAutoUpdater();

    try {
        await updater.initialize();

        let result;
        if (matchId) {
            console.log(`📌 单场模式: ${matchId}\n`);
            result = await updater.processMatch(matchId);
        } else {
            console.log('📌 增量模式: 扫描缺失 Elo 的比赛\n');
            result = await updater.incrementalUpdate();
        }

        console.log('\n' + '─'.repeat(60));
        console.log('  执行结果');
        console.log('─'.repeat(60));
        console.log(`  处理比赛: ${result.processed || 0} 场`);
        console.log(`  更新球队: ${result.teamsSaved || 0} 支`);
        if (result.message) {
            console.log(`  消息: ${result.message}`);
        }
        console.log('═'.repeat(60) + '\n');

    } catch (error) {
        console.error('❌ 错误:', error.message);
        process.exit(1);
    } finally {
        await updater.close();
    }
}

main();
