#!/usr/bin/env node
/**
 * V193.4 - 精准熔炼脚本
 * 针对指定比赛ID进行熔炼
 */
const path = require('path');

const projectRoot = process.cwd();
const FeatureSmelter = require(path.join(projectRoot, 'src/feature_engine/smelter/FeatureSmelter'));

async function main() {
    const targetMatchIds = [
        '87_20242025_4837372',  // Celta Vigo vs Real Madrid
        '87_20242025_4837370'   // Athletic Club vs Barcelona
    ];

    console.log('═══════════════════════════════════════════════════════════════');
    console.log('  V193.4 精准熔炼');
    console.log('═══════════════════════════════════════════════════════════════');
    console.log(`目标: ${targetMatchIds.length} 场比赛`);
    console.log(`  - ${targetMatchIds.join('\n  - ')}`);
    console.log('');

    const smelter = new FeatureSmelter({ dryRun: false });

    let successCount = 0;
    let failCount = 0;

    for (const matchId of targetMatchIds) {
        try {
            console.log(`\n🔄 正在熔炼: ${matchId}`);
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
            console.error(`❌ 熔炼错误 [${matchId}]: ${error.message}`);
        }
    }

    console.log('\n═══════════════════════════════════════════════════════════════');
    console.log('  熔炼完成报告');
    console.log('═══════════════════════════════════════════════════════════════');
    console.log(`成功: ${successCount}`);
    console.log(`失败: ${failCount}`);

    await smelter.close();
}

main().catch(console.error);
    console.error('❌ 致命错误:', error);
    process.exit(1);
});
