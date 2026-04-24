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

function normalizeBulkConcurrency(requested) {
    const parsed = parseInt(requested, 10);
    const fallback = Number.isFinite(parsed) ? parsed : 8;
    return Math.max(1, fallback);
}

function getFlagValue(argv, flagName) {
    const index = argv.indexOf(flagName);
    if (index === -1 || !argv[index + 1]) {
        return null;
    }

    return argv[index + 1];
}

function parseLeagueIds(rawValue) {
    return String(rawValue || '')
        .split(',')
        .map((value) => value.trim())
        .filter(Boolean)
        .map((value) => parseInt(value, 10))
        .filter((value) => Number.isInteger(value) && value > 0);
}

function parseCliArgs(argv = process.argv.slice(2)) {
    let limit = null;
    const rawLimit = getFlagValue(argv, '--limit');
    if (rawLimit) {
        limit = parseInt(rawLimit, 10) || null;
    }

    let workers = parseInt(process.env.MAX_WORKERS, 10) || 8;
    const concurrencyIdx = argv.indexOf('--concurrency');
    const workersIdx = argv.indexOf('--workers');
    const rawConcurrency = concurrencyIdx !== -1 ? argv[concurrencyIdx + 1] : argv[workersIdx + 1];
    if (rawConcurrency) {
        workers = parseInt(rawConcurrency, 10) || workers;
    }

    const sessionPath = getFlagValue(argv, '--session-path');

    let progressEvery = parseInt(process.env.BULK_PROGRESS_EVERY, 10) || 100;
    const rawProgressEvery = getFlagValue(argv, '--progress-every');
    if (rawProgressEvery) {
        progressEvery = parseInt(rawProgressEvery, 10) || progressEvery;
    }

    const leagueIds = parseLeagueIds(getFlagValue(argv, '--league-ids'));

    return {
        limit,
        concurrency: normalizeBulkConcurrency(workers),
        dryRun: argv.includes('--dry-run'),
        sessionPath,
        progressEvery,
        leagueIds,
        season: getFlagValue(argv, '--season'),
        dateFrom: getFlagValue(argv, '--date-from'),
        dateTo: getFlagValue(argv, '--date-to'),
        finishedOnly: argv.includes('--finished-only')
    };
}

/**
 *
 */
async function main(argv = process.argv.slice(2), dependencies = {}) {
    if (!dependencies.skipZombieKiller) {
        executeZombieKiller();
    }

    const options = parseCliArgs(argv);
    const harvester = dependencies.harvester || new ProductionHarvester({
        maxWorkers: options.concurrency,
        bulkConcurrency: options.concurrency,
        batchSize: options.limit || 500,
        dryRun: options.dryRun,
        sessionPath: options.sessionPath,
        bulkProgressEvery: options.progressEvery
    });

    console.log(
        `🔧 [CONFIG] Concurrency: ${options.concurrency} | Limit: ${options.limit || 'ALL'} | ` +
        `ProgressEvery: ${options.progressEvery} | DryRun: ${options.dryRun} | Session: ${options.sessionPath || '默认'} | ` +
        `LeagueIds: ${options.leagueIds.length > 0 ? options.leagueIds.join(',') : 'ALL'} | ` +
        `Season: ${options.season || 'ALL'} | DateFrom: ${options.dateFrom || 'NONE'} | DateTo: ${options.dateTo || 'NONE'} | ` +
        `FinishedOnly: ${options.finishedOnly}`
    );

    try {
        await harvester.init();
        const result = await harvester.run({
            limit: options.limit,
            concurrency: options.concurrency,
            progressEvery: options.progressEvery,
            leagueIds: options.leagueIds,
            season: options.season,
            dateFrom: options.dateFrom,
            dateTo: options.dateTo,
            finishedOnly: options.finishedOnly
        });
        console.log(`📦 [SUMMARY] 批量收割完成: total=${result.total} success=${result.success} failed=${result.failed} concurrency=${result.concurrency}`);
        
        // V4.51.5: 确保资源正确释放，防止进程挂起
        console.log('\n[INFO] 正在关闭资源...');
        await harvester.cleanup();
        console.log('[INFO] 资源已释放，任务完成');
        return result;
    } catch (err) {
        console.error('❌ 致命错误:', err.message);
        try {
            await harvester.cleanup();
        } catch (cleanupErr) {
            console.error('清理时出错:', cleanupErr.message);
        }
        throw err;
    }
}

if (require.main === module) {
    main().then(
        () => process.exit(0),
        err => {
            console.error('❌ 未捕获的错误:', err.message);
            process.exit(1);
        }
    );
}

module.exports = {
    main,
    parseCliArgs,
    parseLeagueIds,
    getFlagValue,
    normalizeBulkConcurrency,
    executeZombieKiller
};
