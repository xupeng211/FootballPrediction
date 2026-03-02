#!/usr/bin/env node
/**
 * V177 生产收割触发器
 * 调用 ProductionHarvester 补全数据
 */
'use strict';

const { ProductionHarvester } = require('../../src/infrastructure/harvesters/ProductionHarvester');

async function main() {
    // 解析 --limit 参数
    let limit = 500;
    const limitIdx = process.argv.indexOf('--limit');
    if (limitIdx !== -1 && process.argv[limitIdx + 1]) {
        limit = parseInt(process.argv[limitIdx + 1]) || 500;
    }

    const harvester = new ProductionHarvester({
        maxWorkers: parseInt(process.env.MAX_WORKERS) || 2,
        batchSize: limit,
        dryRun: process.argv.includes('--dry-run')
    });

    await harvester.init();
    await harvester.run();
}

main().catch(err => {
    console.error('❌ 致命错误:', err.message);
    process.exit(1);
});
