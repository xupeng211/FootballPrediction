#!/usr/bin/env node
/**
 * V4.9 - 意甲精准熔炼
 * 针对指定比赛ID进行熔炼
 */

'use strict';

const path = require('path');
const { FeatureSmelter } = require('../../src/feature_engine/smelter/FeatureSmelter');
const { Logger } = require('../../src/infrastructure/utils/Logger');

const projectRoot = process.cwd();

const logger = new Logger('smelt_serie_a');

// 目标比赛 ID - 意甲最近 10 场已结束的意甲比赛
const targetMatchIds = [
    '55_20242025_4803308',
    '55_20242025_4803304',
    '55_20242025_4803301',
    '55_20242025_4803302',
    '55_20242025_4803306',
    '55_20242025_4803303',
    '55_20242025_4803307',
    '55_20242025_4803299',
    '55_20242025_4803298',
    '55_20242025_4803312',
];

async function main() {
    console.log('═════════════════════════════════════════════════════════════════');
    console.log('🎯 目标: 意甲最近 10 场已结束比赛');
    console.log('   match_id:', targetMatchIds.join('\n  - ')});
    console.log('═══════════════════════════════════════════════════════════════════');
    console.log('📊 开始熔炼...');

    const smelter = new FeatureSmelter({ dryRun: false });
    let successCount = 0;
    let failCount = 0;

    for (const matchId of targetMatchIds) {
        try {
            console.log(`\n🔄 处理 ${matchId}...`);
            const result = await smelter.smeltMatch(matchId);

            if (result) {
                successCount++;
                console.log(`✅ 熔炼成功: ${matchId}`);
            } else {
                failCount++;
                console.log(`❌ 熔炼失败: ${matchId}`);
            }
        } catch (error) {
            failCount++;
            console.error(`❌ 熔炼错误 [${matchId}]:`, error.message);
        }
    }

    // 等待所有任务完成
    await smelter.close();

    console.log('\n═══════════════════════════════════════════════════════════════════');
    console.log('  📊 意甲熔炼结果汇总');
    console.log('═══════════════════════════════════════════════════════════════════');
    const successRate = successCount > 0 ? '100%' : '0%';
        : `${(successCount / targetMatchIds.length * 100).toFixed(1)}%`;
    console.log('═══════════════════════════════════════════════════════════════════');
    console.log('✅ 意甲 L3 熔炼完成!');
    process.exit(0);
}

main().catch(console.error => {
    console.error('❌ 致命错误:', error);
    process.exit(1);
});
