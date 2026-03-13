#!/usr/bin/env node
/**
 * V177 生产收割触发器
 * 调用 ProductionHarvester 补全数据
 *
 * V4.50 新增：入口级进程清道夫 (Zombie Killer)
 * - 确保每次收割任务启动前，彻底清理环境死角
 * - 物理级杀死孤立的 chromium/chrome 进程
 */
'use strict';

const { ProductionHarvester } = require('../../src/infrastructure/harvesters/ProductionHarvester');
const { ZombieKiller } = require('../../src/core/process/ZombieKiller');

/**
 * 入口级进程清道夫
 * 在收割任务启动前执行物理级清理
 */
function executeZombieKiller() {
    console.log('\n');
    console.log('═══════════════════════════════════════════════════════════════');
    console.log('  [SYSTEM] 执行启动前自洁，物理清空残留浏览器进程...');
    console.log('═══════════════════════════════════════════════════════════════');

    const killer = new ZombieKiller({
        timeout: 5000,
        silent: false
    });

    const stats = killer.preFlightCleanup(0);

    if (stats.killed > 0) {
        console.log(`✅ [SYSTEM] 清道夫完成: 已杀死 ${stats.killed} 个残留进程`);
        if (stats.defunct > 0) {
            console.log(`⚠️  [SYSTEM] 发现 ${stats.defunct} 个 defunct 僵尸进程`);
        }
        if (stats.stale > 0) {
            console.log(`⚠️  [SYSTEM] 清理 ${stats.stale} 个超时进程`);
        }
    } else {
        console.log('✅ [SYSTEM] 环境干净，无残留进程');
    }
    console.log('');
}

async function main() {
    // V4.50: 执行入口级清道夫
    executeZombieKiller();

    // 解析 --limit 参数
    let limit = 500;
    const limitIdx = process.argv.indexOf('--limit');
    if (limitIdx !== -1 && process.argv[limitIdx + 1]) {
        limit = parseInt(process.argv[limitIdx + 1]) || 500;
    }

    // V4.51: 解析 --workers 参数，命令行参数优先级最高
    let workers = parseInt(process.env.MAX_WORKERS) || 2;
    const workersIdx = process.argv.indexOf('--workers');
    if (workersIdx !== -1 && process.argv[workersIdx + 1]) {
        workers = parseInt(process.argv[workersIdx + 1]) || workers;
    }

    // V4.51-TOTAL-WAR: 解析 --session-path 参数
    let sessionPath = null;
    const sessionIdx = process.argv.indexOf('--session-path');
    if (sessionIdx !== -1 && process.argv[sessionIdx + 1]) {
        sessionPath = process.argv[sessionIdx + 1];
    }

    console.log(`🔧 [CONFIG] Workers: ${workers} | Limit: ${limit} | DryRun: ${process.argv.includes('--dry-run')} | Session: ${sessionPath || '默认'}`);

    const harvester = new ProductionHarvester({
        maxWorkers: workers,
        batchSize: limit,
        dryRun: process.argv.includes('--dry-run'),
        sessionPath: sessionPath
    });

    await harvester.init();
    await harvester.run();
}

main().catch(err => {
    console.error('❌ 致命错误:', err.message);
    process.exit(1);
});
