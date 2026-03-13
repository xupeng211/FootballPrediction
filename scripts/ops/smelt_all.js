#!/usr/bin/env node
/**
 * V176 全量熔炼触发器
 * ====================
 *
 * 调用 FeatureSmelter 执行特征熔炼
 *
 * 用法:
 *   node smelt_all.js                     # 仅处理缺失特征的记录
 *   node smelt_all.js --full-recalculate  # 重新计算所有特征
 *   node smelt_all.js --dry-run           # 预览模式
 *
 * @module scripts/ops/smelt_all
 * @version V176.0.0
 */

'use strict';

const { FeatureSmelter } = require('../../src/feature_engine/smelter/FeatureSmelter');

async function main() {
    const fullRecalculate = process.argv.includes('--full-recalculate');
    const dryRun = process.argv.includes('--dry-run');

    const smelter = new FeatureSmelter();

    try {
        await smelter.init();
        await smelter.run({ fullRecalculate, dryRun });
    } finally {
        await smelter.close();
    }
}

main().catch(err => {
    console.error('❌ 致命错误:', err.message);
    process.exit(1);
});
