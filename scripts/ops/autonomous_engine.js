#!/usr/bin/env node
/**
 * AutonomousOrchestrator - V201.1 全自动闭环流水线
 * ================================================
 *
 * 中央编排器：L1 → L2 → L3 → RECALCULATE_ELO → PREDICT 五层流水线自动编排
 * 实现状态轮询、自动触发、错误隔离、自愈重试
 *
 * @module scripts/ops/autonomous_engine
 * @version V201.1.0
 */

'use strict';

const { Pool } = require('pg');
const { spawn } = require('child_process');

// 导入三层模块
const { FixtureSeeder } = require('../../src/infrastructure/FixtureSeeder');
const { ProductionHarvester } = require('../../src/infrastructure/harvesters/ProductionHarvester');
const { FeatureSmelter } = require('../../src/feature_engine/smelter/FeatureSmelter');

// 导入统一注册中心
const Registry = require('../../config/registry');

// ============================================================================
// 配置常量
// ============================================================================

const ORCHESTRATOR_CONFIG = {
    /** 循环间隔 (ms) - 默认 6 小时 */
    LOOP_INTERVAL_MS: parseInt(process.env.LOOP_INTERVAL_MS) || 6 * 60 * 60 * 1000,

    /** L2 最大重试次数 */
    L2_MAX_RETRIES: parseInt(process.env.L2_MAX_RETRIES) || 3,

    /** L2 重试间隔 (ms) */
    L2_RETRY_DELAY_MS: parseInt(process.env.L2_RETRY_DELAY_MS) || 60000,

    /** L3 最大重试次数 */
    L3_MAX_RETRIES: parseInt(process.env.L3_MAX_RETRIES) || 2,

    /** L3 重试间隔 (ms) */
    L3_RETRY_DELAY_MS: parseInt(process.env.L3_RETRY_DELAY_MS) || 30000,

    /** 预测天数 */
    PREDICT_DAYS: parseInt(process.env.PREDICT_DAYS) || 4,

    /** 数据库配置 */
    db: {
        host: process.env.DB_HOST || 'localhost',
        port: parseInt(process.env.DB_PORT || '5432'),
        database: process.env.DB_NAME || 'football_db',
        user: process.env.DB_USER || 'football_user',
        password: process.env.DB_PASSWORD || ''
    }
};

// ============================================================================
// 日志系统
// ============================================================================

function timestamp() {
    return new Date().toISOString();
}

const log = {
    info: (msg, meta = null) => {
        const metaStr = meta ? ` | ${JSON.stringify(meta)}` : '';
        console.log(`[${timestamp()}] [INFO] [Orchestrator] ${msg}${metaStr}`);
    },
    warn: (msg, meta = null) => {
        const metaStr = meta ? ` | ${JSON.stringify(meta)}` : '';
        console.warn(`[${timestamp()}] [WARN] [Orchestrator] ${msg}${metaStr}`);
    },
    error: (msg, error = null) => {
        const meta = error ? { error: error.message, stack: error.stack } : {};
        console.error(`[${timestamp()}] [ERROR] [Orchestrator] ${msg}`, meta);
    },
    success: (msg, meta = null) => {
        const metaStr = meta ? ` | ${JSON.stringify(meta)}` : '';
        console.log(`[${timestamp()}] [SUCCESS] [Orchestrator] ✅ ${msg}${metaStr}`);
    },
    section: (title) => {
        console.log('\n' + '═'.repeat(70));
        console.log(`  ${title}`);
        console.log('═'.repeat(70));
    }
};

// ============================================================================
// AutonomousOrchestrator 类
// ============================================================================

class AutonomousOrchestrator {
    constructor(config = {}) {
        this.config = { ...ORCHESTRATOR_CONFIG, ...config };
        this.pool = null;
        this.dryRun = false;
        this.onlyStages = null;
    }

    /**
     * 初始化
     */
    async init() {
        log.info('🚀 初始化 AutonomousOrchestrator V201.1...');

        this.pool = new Pool({
            ...this.config.db,
            max: 5,
            idleTimeoutMillis: 30000
        });

        // 测试连接
        const client = await this.pool.connect();
        await client.query('SELECT 1');
        client.release();

        log.success('数据库连接池已就绪');
    }

    /**
     * 关闭连接
     */
    async close() {
        if (this.pool) {
            await this.pool.end();
            log.info('数据库连接池已关闭');
        }
    }

    // ========================================================================
    // 阶段 1: L1 Discovery (赛程播种)
    // ========================================================================

    async runL1Discovery() {
        log.section('阶段 1/5: L1 Discovery (赛程播种)');

        if (this.dryRun) {
            log.info('[DRY-RUN] 跳过 L1 Discovery');
            return { success: true, skipped: true };
        }

        try {
            // 从配置加载活跃联赛
            const leagueConfig = require('../../config/leagues.json');
            const activeLeagues = leagueConfig.active_leagues || [];
            const activeSeasons = leagueConfig.active_seasons || ['2024/2025'];

            log.info(`活跃联赛: ${activeLeagues.map(l => l.name).join(', ')}`);
            log.info(`活跃赛季: ${activeSeasons.join(', ')}`);

            // 创建 Seeder 实例
            const seeder = new FixtureSeeder({
                leagues: activeLeagues,
                seasons: activeSeasons
            });

            await seeder.init();
            const stats = await seeder.seedAll();
            await seeder.close();

            const totalSeeded = stats?.total || 0;
            log.success(`L1 Discovery 完成，共播种 ${totalSeeded} 场比赛`);
            return { success: true, seeded: totalSeeded, stats };

        } catch (error) {
            log.error(`L1 Discovery 失败: ${error.message}`);
            return { success: false, error: error.message };
        }
    }

    // ========================================================================
    // 阶段 2: L2 Harvest (赔率收割)
    // ========================================================================

    async runL2Harvest() {
        log.section('阶段 2/5: L2 Harvest (赔率收割)');

        if (this.dryRun) {
            log.info('[DRY-RUN] 跳过 L2 Harvest');
            return { success: true, skipped: true };
        }

        try {
            // 检查待收割数量
            const pending = await this._getPendingL2Count();
            log.info(`待收割 L2 数据: ${pending} 场`);

            if (pending === 0) {
                log.success('L2 数据已全部收割完成');
                return { success: true, harvested: 0 };
            }

            // 执行收割
            const harvester = new ProductionHarvester({
                batchSize: Math.min(pending, 500),
                maxWorkers: 1
            });

            await harvester.init();
            const result = await harvester.run();
            await harvester.close();

            log.success(`L2 Harvest 完成，收割 ${result.success || 0} 场`);
            return { success: true, ...result };

        } catch (error) {
            log.error(`L2 Harvest 失败: ${error.message}`);
            return { success: false, error: error.message };
        }
    }

    // ========================================================================
    // 阶段 3: L3 Smelt (特征熔炼)
    // ========================================================================

    async runL3Smelt() {
        log.section('阶段 3/5: L3 Smelt (特征熔炼)');

        if (this.dryRun) {
            log.info('[DRY-RUN] 跳过 L3 Smelt');
            return { success: true, skipped: true };
        }

        try {
            // 检查待熔炼数量
            const pending = await this._getPendingL3Count();
            log.info(`待熔炼 L3 特征: ${pending} 场`);

            if (pending === 0) {
                log.success('L3 特征已全部熔炼完成');
                return { success: true, smelted: 0 };
            }

            // 执行熔炼
            const smelter = new FeatureSmelter({
                batchSize: Math.min(pending, 500)
            });

            await smelter.init();
            const result = await smelter.run();
            await smelter.close();

            log.success(`L3 Smelt 完成，熔炼 ${result.success || 0} 场`);
            return { success: true, ...result };

        } catch (error) {
            log.error(`L3 Smelt 失败: ${error.message}`);
            return { success: false, error: error.message };
        }
    }

    // ========================================================================
    // 阶段 4: Recalculate Elo (战力重算) - 关键闭环！
    // ========================================================================

    async runRecalculateElo() {
        log.section('阶段 4/5: Recalculate Elo (战力重算)');

        if (this.dryRun) {
            log.info('[DRY-RUN] 跳过 Elo 重算');
            return { success: true, skipped: true };
        }

        try {
            // 检查有比分的比赛数量
            const pendingScores = await this._getMatchesWithScoresCount();
            log.info(`有比分的比赛: ${pendingScores} 场`);

            // 调用 Node 脚本重算 Elo
            const result = await this._runEloRecalculation();

            log.success('Elo 重算完成');
            return { success: true, ...result };

        } catch (error) {
            log.error(`Elo 重算失败: ${error.message}`);
            return { success: false, error: error.message };
        }
    }

    /**
     * 执行 Elo 重算脚本
     */
    async _runEloRecalculation() {
        return new Promise((resolve, reject) => {
            const args = ['/app/scripts/maintenance/recalculate_elo.js'];

            log.info(`执行: node ${args.join(' ')}`);

            const child = spawn('node', args, {
                env: process.env,
                cwd: '/app',
                stdio: 'inherit'
            });

            child.on('close', (code) => {
                if (code === 0) {
                    resolve({ exitCode: 0 });
                } else {
                    reject(new Error(`Elo 重算脚本退出码 ${code}`));
                }
            });

            child.on('error', (err) => {
                reject(err);
            });
        });
    }

    // ========================================================================
    // 阶段 5: Predict (预测生成)
    // ========================================================================

    async runPredict() {
        log.section('阶段 5/5: Predict (预测生成)');

        if (this.dryRun) {
            log.info('[DRY-RUN] 跳过预测');
            return { success: true, skipped: true };
        }

        try {
            // 调用 Python 预测脚本
            const result = await this._runPythonPredictor();

            log.success('预测生成完成');
            return { success: true, ...result };

        } catch (error) {
            log.error(`预测生成失败: ${error.message}`);
            return { success: false, error: error.message };
        }
    }

    /**
     * 执行 Python 预测脚本
     */
    async _runPythonPredictor() {
        return new Promise((resolve, reject) => {
            const args = [
                '/app/scripts/ops/predict_weekend.py',
                '--days', String(this.config.PREDICT_DAYS),
                '--save'
            ];

            log.info(`执行: python ${args.join(' ')}`);

            const python = spawn('python', args, {
                env: process.env,
                cwd: '/app',
                stdio: 'inherit'
            });

            python.on('close', (code) => {
                if (code === 0) {
                    resolve({ exitCode: 0 });
                } else {
                    reject(new Error(`预测脚本退出码 ${code}`));
                }
            });

            python.on('error', (err) => {
                reject(err);
            });
        });
    }

    // ========================================================================
    // 辅助方法
    // ========================================================================

    async _getActiveLeagues() {
        const result = await this.pool.query(`
            SELECT DISTINCT
                SPLIT_PART(match_id, '_', 1) as id,
                league_name as name
            FROM matches
            WHERE match_date >= NOW() - INTERVAL '30 days'
        `);
        return result.rows;
    }

    async _getPendingL2Count() {
        const result = await this.pool.query(`
            SELECT COUNT(*) as count
            FROM matches m
            LEFT JOIN raw_match_data r ON m.match_id = r.match_id
            WHERE r.match_id IS NULL
              AND m.match_date < NOW()
        `);
        return parseInt(result.rows[0].count) || 0;
    }

    async _getPendingL3Count() {
        const result = await this.pool.query(`
            SELECT COUNT(*) as count
            FROM matches m
            JOIN raw_match_data r ON m.match_id = r.match_id
            LEFT JOIN l3_features f ON m.match_id = f.match_id
            WHERE r.raw_data IS NOT NULL
              AND f.match_id IS NULL
        `);
        return parseInt(result.rows[0].count) || 0;
    }

    async _getMatchesWithScoresCount() {
        const result = await this.pool.query(`
            SELECT COUNT(*) as count
            FROM matches
            WHERE home_score IS NOT NULL
              AND away_score IS NOT NULL
        `);
        return parseInt(result.rows[0].count) || 0;
    }

    _shouldRun(stage) {
        if (!this.onlyStages) return true;
        return this.onlyStages.includes(stage);
    }

    // ========================================================================
    // 主运行方法
    // ========================================================================

    /**
     * 执行完整流水线
     * @param {Object} options - 执行选项
     */
    async run(options = {}) {
        const { loop = false, dryRun = false, only = null } = options;

        this.dryRun = dryRun;
        this.onlyStages = only ? only.split(',').map(s => s.trim().toLowerCase()) : null;

        const results = {};

        do {
            const startTime = Date.now();

            log.section('🚀 V201.1 全自动流水线启动');
            log.info(`循环模式: ${loop}`);
            log.info(`预览模式: ${dryRun}`);
            log.info(`指定阶段: ${only || '全部'}`);

            // 阶段 1: L1 Discovery
            if (this._shouldRun('l1') || this._shouldRun('discovery')) {
                results.l1 = await this.runL1Discovery();
            }

            // 阶段 2: L2 Harvest
            if (this._shouldRun('l2') || this._shouldRun('harvest')) {
                results.l2 = await this.runL2Harvest();
            }

            // 阶段 3: L3 Smelt
            if (this._shouldRun('l3') || this._shouldRun('smelt')) {
                results.l3 = await this.runL3Smelt();
            }

            // 阶段 4: Recalculate Elo - 关键闭环！
            if (this._shouldRun('elo') || this._shouldRun('recalculate')) {
                results.elo = await this.runRecalculateElo();
            }

            // 阶段 5: Predict
            if (this._shouldRun('predict')) {
                results.predict = await this.runPredict();
            }

            const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);

            log.section('📊 流水线执行完成');
            log.success(`总耗时: ${elapsed}s`);
            log.info(`执行结果: ${JSON.stringify(results, null, 2)}`);

            if (loop) {
                log.info(`等待 ${this.config.LOOP_INTERVAL_MS / 1000 / 60} 分钟后执行下一轮...`);
                await new Promise(r => setTimeout(r, this.config.LOOP_INTERVAL_MS));
            }

        } while (loop);

        return results;
    }
}

// ============================================================================
// CLI 入口
// ============================================================================

async function main() {
    const args = process.argv.slice(2);

    const options = {
        loop: args.includes('--loop'),
        dryRun: args.includes('--dry-run'),
        only: null
    };

    // 解析 --only 参数
    const onlyIdx = args.indexOf('--only');
    if (onlyIdx !== -1 && args[onlyIdx + 1]) {
        options.only = args[onlyIdx + 1];
    }

    // 解析 --interval 参数
    const intervalIdx = args.indexOf('--interval');
    if (intervalIdx !== -1 && args[intervalIdx + 1]) {
        ORCHESTRATOR_CONFIG.LOOP_INTERVAL_MS = parseInt(args[intervalIdx + 1]);
    }

    const orchestrator = new AutonomousOrchestrator();

    try {
        await orchestrator.init();
        const results = await orchestrator.run(options);
        await orchestrator.close();

        // 检查是否有失败
        const hasFailure = Object.values(results).some(r => r && !r.success);
        process.exit(hasFailure ? 1 : 0);

    } catch (error) {
        log.error('流水线执行失败', error);
        await orchestrator.close();
        process.exit(1);
    }
}

// 运行
main();
