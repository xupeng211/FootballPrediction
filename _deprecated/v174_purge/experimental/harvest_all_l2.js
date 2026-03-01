/**
 * V172-L3-01 全量收割控制器 (Bulk Harvesting Controller)
 * =======================================================
 *
 * 目标: 批量抓取所有缺失 L2 原始数据的比赛
 * 策略: 小步快跑，逐场采集，保护 Cookie 信誉
 *
 * 核心特性:
 * - 严禁并行: for...of 循环逐场采集
 * - 动态延时: 5s ~ 15s 随机休眠
 * - 状态持久化: 每 5 场保存一次 Cookie
 * - 断点续爬: 失败跳过继续
 * - 进度仪表盘: 实时打印进度
 *
 * @module scripts/ops/harvest_all_l2
 * @version V172.300
 */

'use strict';

const path = require('path');
const fs = require('fs');
const PROJECT_ROOT = '/app';

const { DatabaseConfig } = require(path.join(PROJECT_ROOT, 'config/database'));
const { Client } = require('pg');
const { MatchDetailEngine } = require(path.join(PROJECT_ROOT, 'src/domain/services/harvesting/MatchDetailEngine'));

// ============================================================================
// 配置
// ============================================================================

const HARVEST_CONFIG = {
    // 批次配置
    batchSize: 50,              // 每批次处理比赛数
    batchCooldownMs: 60000,     // 批次间散热期 (1 分钟)

    // 单场采集配置
    minDelayMs: 5000,           // 最小延时 (5 秒)
    maxDelayMs: 15000,          // 最大延时 (15 秒)

    // 状态持久化
    cookieSaveInterval: 5,      // 每 N 场保存一次 Cookie

    // 并发控制 (严禁并行!)
    concurrency: 1,             // 固定为 1，禁止修改

    // 重试配置
    maxRetries: 2,              // 单场最大重试次数
    retryDelayMs: 10000         // 重试前延时
};

// ============================================================================
// 工具函数
// ============================================================================

/**
 * 随机数生成 (范围)
 */
function randomInRange(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

/**
 * 随机延时
 */
async function randomDelay(minMs, maxMs) {
    const ms = randomInRange(minMs, maxMs);
    const seconds = (ms / 1000).toFixed(1);
    console.log(`   💤 休眠 ${seconds}s (模拟真人节奏)...`);
    await new Promise(r => setTimeout(r, ms));
}

/**
 * 格式化时间
 */
function formatDuration(ms) {
    const hours = Math.floor(ms / 3600000);
    const minutes = Math.floor((ms % 3600000) / 60000);
    if (hours > 0) {
        return `${hours}小时${minutes}分钟`;
    }
    return `${minutes}分钟`;
}

// ============================================================================
// 进度仪表盘
// ============================================================================

class ProgressDashboard {
    constructor(total) {
        this.total = total;
        this.processed = 0;
        this.success = 0;
        this.failed = 0;
        this.skipped = 0;
        this.startTime = Date.now();
        this.lastUpdateTime = Date.now();
    }

    update(status) {
        this.processed++;
        if (status === 'success') this.success++;
        else if (status === 'failed') this.failed++;
        else if (status === 'skipped') this.skipped++;

        this.render();
    }

    render() {
        const pct = ((this.processed / this.total) * 100).toFixed(1);
        const bar = '█'.repeat(Math.floor(pct / 5)) + '░'.repeat(20 - Math.floor(pct / 5));

        const elapsed = Date.now() - this.startTime;
        const avgTime = elapsed / this.processed;
        const remaining = (this.total - this.processed) * avgTime;

        console.log('');
        console.log('═'.repeat(70));
        console.log(`  📊 收割进度: [${bar}] ${pct}%`);
        console.log('═'.repeat(70));
        console.log(`  📈 已处理: ${this.processed} / ${this.total}`);
        console.log(`  ✅ 成功: ${this.success} | ❌ 失败: ${this.failed} | ⏭️ 跳过: ${this.skipped}`);
        console.log(`  ⏱️  已用时间: ${formatDuration(elapsed)}`);
        console.log(`  🕐 预计剩余: ${formatDuration(remaining)}`);
        console.log('═'.repeat(70));
    }

    summary() {
        const elapsed = Date.now() - this.startTime;
        console.log('');
        console.log('═'.repeat(70));
        console.log('  📊 收割完成报告');
        console.log('═'.repeat(70));
        console.log(`  总计: ${this.total} 场比赛`);
        console.log(`  ✅ 成功: ${this.success}`);
        console.log(`  ❌ 失败: ${this.failed}`);
        console.log(`  ⏭️ 跳过: ${this.skipped}`);
        console.log(`  ⏱️  总耗时: ${formatDuration(elapsed)}`);
        console.log(`  📊 成功率: ${((this.success / this.processed) * 100).toFixed(1)}%`);
        console.log('═'.repeat(70));
    }
}

// ============================================================================
// 全量收割控制器
// ============================================================================

class BulkHarvestController {
    constructor() {
        this.client = null;
        this.engine = null;
        this.dashboard = null;
        this.harvestedCount = 0;
    }

    // ========================================================================
    // 数据库连接
    // ========================================================================

    async connect() {
        this.client = new Client({
            host: DatabaseConfig.host,
            port: DatabaseConfig.port,
            database: DatabaseConfig.database,
            user: DatabaseConfig.user,
            password: DatabaseConfig.password
        });
        await this.client.connect();
        console.log('✅ 数据库连接成功');
    }

    async disconnect() {
        if (this.engine) {
            await this.engine.close();
        }
        if (this.client) {
            await this.client.end();
        }
    }

    // ========================================================================
    // 目标筛选
    // ========================================================================

    async getTargets() {
        // 查询 external_id 不为空且 l2_raw_json 缺失的比赛
        const query = `
            SELECT
                m.match_id,
                m.external_id,
                m.home_team,
                m.away_team,
                m.league_name,
                m.match_date
            FROM matches m
            LEFT JOIN raw_match_data r ON m.match_id = r.match_id
            WHERE m.external_id IS NOT NULL
              AND m.external_id <> ''
              AND (r.l2_raw_json IS NULL OR r.l2_raw_json::text = '{}')
            ORDER BY m.match_date DESC
        `;

        const result = await this.client.query(query);
        return result.rows;
    }

    // ========================================================================
    // 单场收割
    // ========================================================================

    async harvestOne(match) {
        const { match_id, external_id, home_team, away_team } = match;

        console.log(`\n📍 [${this.dashboard.processed + 1}/${this.dashboard.total}] ${home_team} vs ${away_team}`);
        console.log(`   match_id: ${match_id}`);
        console.log(`   external_id: ${external_id}`);

        let retries = 0;
        while (retries <= HARVEST_CONFIG.maxRetries) {
            try {
                const result = await this.engine.harvestMatch({
                    match_id,
                    external_id,
                    home_team,
                    away_team
                });

                if (result.success) {
                    console.log(`   ✅ 采集成功! xG: ${result.data?.xg_home} - ${result.data?.xg_away}`);
                    this.harvestedCount++;

                    // 状态持久化: 每 5 场保存一次 Cookie
                    if (this.harvestedCount % HARVEST_CONFIG.cookieSaveInterval === 0) {
                        await this.saveCookieState();
                    }

                    return 'success';
                } else {
                    throw new Error(result.error || 'Unknown error');
                }

            } catch (error) {
                retries++;
                if (retries <= HARVEST_CONFIG.maxRetries) {
                    console.log(`   ⚠️  第 ${retries} 次重试...`);
                    await randomDelay(HARVEST_CONFIG.retryDelayMs, HARVEST_CONFIG.retryDelayMs + 5000);
                } else {
                    console.log(`   ❌ 采集失败: ${error.message}`);
                    return 'failed';
                }
            }
        }

        return 'failed';
    }

    // ========================================================================
    // 状态持久化
    // ========================================================================

    async saveCookieState() {
        try {
            const profilePath = process.env.BROWSER_PROFILE_PATH || '/app/data/browser_profile';
            const statePath = path.join(profilePath, 'browser_state.json');

            // MatchDetailEngine 会在内部保存，这里只是打印确认
            console.log(`   💾 Cookie 已自动保存 (每 ${HARVEST_CONFIG.cookieSaveInterval} 场)`);
        } catch (e) {
            console.log(`   ⚠️  Cookie 保存失败: ${e.message}`);
        }
    }

    // ========================================================================
    // 批量收割主循环
    // ========================================================================

    async run() {
        console.log('\n' + '═'.repeat(70));
        console.log('  V172-L3-01 全量收割控制器');
        console.log('═'.repeat(70));
        console.log('');
        console.log('📋 配置:');
        console.log(`   批次大小: ${HARVEST_CONFIG.batchSize} 场`);
        console.log(`   批次散热: ${HARVEST_CONFIG.batchCooldownMs / 1000}s`);
        console.log(`   单场延时: ${HARVEST_CONFIG.minDelayMs / 1000}s ~ ${HARVEST_CONFIG.maxDelayMs / 1000}s`);
        console.log(`   Cookie 保存: 每 ${HARVEST_CONFIG.cookieSaveInterval} 场`);
        console.log('');

        // 连接数据库
        await this.connect();

        // 获取目标列表
        console.log('🔍 查询待收割目标...');
        const targets = await this.getTargets();
        console.log(`   找到 ${targets.length} 场比赛需要收割`);
        console.log('');

        if (targets.length === 0) {
            console.log('✅ 所有比赛已有 L2 数据，无需收割');
            await this.disconnect();
            return;
        }

        // 初始化引擎
        this.engine = new MatchDetailEngine({
            headless: true,
            enableProxy: true,
            proxyServer: process.env.HTTPS_PROXY || process.env.HTTP_PROXY || 'http://172.25.16.1:7890',
            timeout: 90000
        });

        // 初始化仪表盘
        this.dashboard = new ProgressDashboard(targets.length);

        // 批次处理
        const batchCount = Math.ceil(targets.length / HARVEST_CONFIG.batchSize);

        for (let batch = 0; batch < batchCount; batch++) {
            const start = batch * HARVEST_CONFIG.batchSize;
            const end = Math.min(start + HARVEST_CONFIG.batchSize, targets.length);
            const batchTargets = targets.slice(start, end);

            console.log('\n' + '─'.repeat(70));
            console.log(`  📦 批次 ${batch + 1}/${batchCount} (${batchTargets.length} 场)`);
            console.log('─'.repeat(70));

            // 逐场采集 (严禁并行!)
            for (const match of batchTargets) {
                const status = await this.harvestOne(match);
                this.dashboard.update(status);

                // 动态延时 (模拟真人节奏)
                if (this.dashboard.processed < targets.length) {
                    await randomDelay(HARVEST_CONFIG.minDelayMs, HARVEST_CONFIG.maxDelayMs);
                }
            }

            // 批次间散热
            if (batch < batchCount - 1) {
                console.log('\n☕ 批次完成，散热中...');
                await new Promise(r => setTimeout(r, HARVEST_CONFIG.batchCooldownMs));
            }
        }

        // 最终报告
        this.dashboard.summary();

        // 断开连接
        await this.disconnect();
    }
}

// ============================================================================
// 主入口
// ============================================================================

async function main() {
    const controller = new BulkHarvestController();

    try {
        await controller.run();
    } catch (error) {
        console.error('\n❌ 收割异常:', error.message);
        console.error(error.stack);
        await controller.disconnect();
        process.exit(1);
    }
}

main();
