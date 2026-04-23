#!/usr/bin/env node
/**
 * Titan 7.0 神级收割 - 弹性 Workers 物理隔离
 * =========================================
 *
 * Playwright 原生 SOCKS5 代理注入
 * 默认端口池 10001-10040，可通过环境变量裁剪健康端口集
 */

'use strict';

const { ProductionHarvester } = require('../../src/infrastructure/harvesters/ProductionHarvester');
const { resolveSeasonContext } = require('./helpers/seasonRuntimeConfig');

function parseLeagueIds(value) {
    const raw = String(value || '').trim();
    if (!raw) {
        return [];
    }

    return [...new Set(
        raw
            .split(',')
            .map(entry => Number.parseInt(entry.trim(), 10))
            .filter(entry => Number.isInteger(entry) && entry > 0)
    )];
}

function resolveTitanConfig() {
    const seasonContext = resolveSeasonContext({
        seasonEnvVar: 'TITAN_SEASON',
        seasonTagEnvVar: 'TITAN_SEASON_TAG'
    });

    return {
        workerCount: Number(process.env.TITAN_MAX_WORKERS || process.env.MAX_WORKERS || '40'),
        targetMatchCount: Number(process.env.TITAN_TARGET_MATCHES || '2130'),
        progressEvery: Number(process.env.TITAN_PROGRESS_EVERY || '10'),
        season: seasonContext.season,
        seasonTag: seasonContext.seasonTag,
        leagueIds: parseLeagueIds(process.env.TITAN_LEAGUE_IDS)
    };
}

function applyTitanEnvironment(workerCount) {
    process.env.PROXY_RADAR_MODE = 'false';
    process.env.PROXY_HOST = process.env.PROXY_HOST || process.env.WSL2_PROXY_HOST || '127.0.0.1';
    process.env.WSL2_PROXY_HOST = process.env.WSL2_PROXY_HOST || process.env.PROXY_HOST || '127.0.0.1';
    process.env.PROXY_PROTOCOL = process.env.PROXY_PROTOCOL || 'socks5';
    process.env.PROXY_PORT_START = process.env.PROXY_PORT_START || '10001';
    process.env.PROXY_PORT_END = process.env.PROXY_PORT_END || '10040';
    process.env.PLAYWRIGHT_BLOCK_RESOURCES = process.env.PLAYWRIGHT_BLOCK_RESOURCES || 'true';
    process.env.MAX_WORKERS = String(workerCount);
    process.env.HARVEST_NAVIGATION_WAIT_UNTIL = process.env.HARVEST_NAVIGATION_WAIT_UNTIL || 'domcontentloaded';
    process.env.HARVEST_NAVIGATION_TIMEOUT_MS = process.env.HARVEST_NAVIGATION_TIMEOUT_MS || '30000';
    process.env.HARVEST_POST_NAVIGATION_WAIT_MS = process.env.HARVEST_POST_NAVIGATION_WAIT_MS || '2000';
    process.env.HARVEST_POST_NAVIGATION_WAIT_MS_RETRY = process.env.HARVEST_POST_NAVIGATION_WAIT_MS_RETRY || '1500';
}

function createTitanHarvester(workerCount, targetMatchCount) {
    return new ProductionHarvester({
        maxWorkers: workerCount,
        minDelayMs: 3000,
        maxDelayMs: 5000,
        batchSize: targetMatchCount,
        dryRun: false
    });
}

function buildPendingFilters(season, leagueIds) {
    const pendingFilters = {
        season,
        finishedOnly: true
    };

    if (leagueIds.length > 0) {
        pendingFilters.leagueIds = leagueIds;
    }

    return pendingFilters;
}

function logHarvesterConfig(harvester) {
    console.log(`⚡ 并发配置: ${harvester.config.maxWorkers} Workers (${process.env.PROXY_HOST}:${process.env.PROXY_PORTS || `${process.env.PROXY_PORT_START}-${process.env.PROXY_PORT_END}`} | ${process.env.PROXY_PROTOCOL.toUpperCase()})\n`);
}

function logHarvestStart(config, pendingMatches) {
    console.log(`🎯 开始神级收割 (${pendingMatches.length} 场)...`);
    console.log(`🧭 过滤条件: season=${config.season} seasonTag=${config.seasonTag} leagueIds=${config.leagueIds.length > 0 ? config.leagueIds.join(',') : 'ALL'} finishedOnly=true`);
    console.log(`━`.repeat(60));
}

function logHarvestSummary(harvester, results, harvestElapsed) {
    const throughputPerMin = (results.success / (harvestElapsed / 1000 / 60)).toFixed(2);
    const baselineThroughput = 5.8;
    const improvement = (parseFloat(throughputPerMin) / baselineThroughput).toFixed(1);

    console.log(`\n━`.repeat(60));
    console.log('✅ 神级收割完成!\n');

    console.log('📈 性能指标:');
    console.log(`   • 总耗时: ${(harvestElapsed / 1000 / 60).toFixed(1)} 分钟`);
    console.log(`   • 成功: ${results.success} 场`);
    console.log(`   • 失败: ${results.failed} 场`);
    console.log(`   • 成功率: ${(results.success / (results.success + results.failed) * 100).toFixed(1)}%`);
    console.log(`   • 吞吐量: ${throughputPerMin} 场/分钟`);
    console.log(`   • 并发数: ${harvester.config.maxWorkers} Workers`);

    console.log(`\n🚀 性能提升:`);
    console.log(`   • 基准吞吐量 (5 Workers): ${baselineThroughput} 场/分钟`);
    console.log(`   • 当前吞吐量 (${harvester.config.maxWorkers} Workers): ${throughputPerMin} 场/分钟`);
    console.log(`   • 提升倍数: ${improvement}x`);

    return {
        workers: harvester.config.maxWorkers,
        throughput: parseFloat(throughputPerMin),
        improvement: parseFloat(improvement)
    };
}

async function executeTitanHarvest(harvester, config) {
    console.log(`📡 初始化收割器 (${config.workerCount} Workers 物理隔离)...`);
    const startTime = Date.now();

    await harvester.init();

    const initElapsed = Date.now() - startTime;
    console.log(`✅ 收割器初始化完成 (耗时: ${initElapsed}ms)`);
    logHarvesterConfig(harvester);

    console.log(`🔍 查询 ${config.season} 赛季待收割比赛...`);
    const pendingMatches = await harvester.getPendingMatches(
        config.targetMatchCount,
        buildPendingFilters(config.season, config.leagueIds)
    );

    console.log(`📊 待收割比赛数: ${pendingMatches.length} 场\n`);

    if (pendingMatches.length === 0) {
        console.log(`✅ ${config.season} 赛季数据已完整收割`);
        await harvester.cleanup();
        return { success: true, message: '无待收割比赛' };
    }

    logHarvestStart(config, pendingMatches);

    const harvestStartTime = Date.now();
    const results = await harvester.runBulk({
        limit: pendingMatches.length,
        concurrency: config.workerCount,
        captureResults: true,
        progressEvery: config.progressEvery,
        season: config.season,
        finishedOnly: true,
        leagueIds: config.leagueIds
    });
    const harvestElapsed = Date.now() - harvestStartTime;
    const summary = logHarvestSummary(harvester, results, harvestElapsed);

    await harvester.cleanup();

    return {
        success: true,
        ...summary,
        results
    };
}

async function titan40Workers() {
    const config = resolveTitanConfig();
    console.log(`🚀 Titan 7.0 神级收割启动 (${config.workerCount} Workers 物理隔离)...\n`);
    applyTitanEnvironment(config.workerCount);

    const harvester = createTitanHarvester(config.workerCount, config.targetMatchCount);

    try {
        return await executeTitanHarvest(harvester, config);
    } catch (error) {
        console.error('\n❌ 神级收割失败:', error.message);
        console.error(error.stack);
        await harvester.cleanup();
        return { success: false, error: error.message };
    }
}

if (require.main === module) {
    titan40Workers()
        .then(result => process.exit(result.success ? 0 : 1))
        .catch(error => {
            console.error('未捕获的错误:', error);
            process.exit(1);
        });
}

module.exports = { titan40Workers };
