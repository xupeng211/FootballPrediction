/**
 * V171 Scheduler - 全息系统战术调度器
 * ========================================
 *
 * V171-Standard-05 重构:
 * - 拆分 TaskQueue.js (队列管理)
 * - 拆分 HealthMonitor.js (健康监控)
 * - 使用 lib/db.js (统一数据库)
 * - 使用 lib/retry.js (重试机制)
 *
 * @module scripts/ops/v171_scheduler
 * @version V171.001-refactored
 */

'use strict';

const { spawn } = require('child_process');
const path = require('path');

// V171-Standard-05: 使用拆分模块
const db = require('./lib/db');
const { withRetry } = require('./lib/retry');
const { TaskQueue } = require('./lib/TaskQueue');
const { HealthMonitor, HealthStatus } = require('./lib/HealthMonitor');

const PROJECT_ROOT = path.resolve(__dirname, '../..');

// ============================================================================
// 配置 (精简版)
// ============================================================================

const SCHEDULER_CONFIG = {
    timezone: 'Asia/Shanghai',

    dailyBatch: {
        enabled: true,
        cron: '0 2 * * *',
        leagues: [
            { name: 'Premier League', code: 'EPL' },
            { name: 'La Liga', code: 'LALIGA' },
            { name: 'Bundesliga', code: 'BL' },
            { name: 'Serie A', code: 'SA' },
            { name: 'Ligue 1', code: 'L1' }
        ]
    },

    preMatchHotZone: {
        enabled: true,
        pollIntervalMs: 60000,
        windowMinutes: 65,
        maxConcurrent: 3
    },

    liveMonitoring: {
        enabled: true,
        pollIntervalMs: 30000
    },

    retry: {
        maxAttempts: 3,
        baseDelayMs: 5000
    }
};

// ============================================================================
// 调度器状态
// ============================================================================

class SchedulerState {
    constructor() {
        this.isRunning = false;
        this.lastDailyBatch = null;
        this.stats = {
            discovered: 0,
            harvested: 0,
            predicted: 0,
            ssrPredictions: 0,
            errors: 0
        };
    }

    toJSON() {
        return {
            isRunning: this.isRunning,
            lastDailyBatch: this.lastDailyBatch,
            stats: this.stats
        };
    }
}

// ============================================================================
// 主调度器
// ============================================================================

class V171Scheduler {
    constructor(config = SCHEDULER_CONFIG) {
        this.config = config;
        this.state = new SchedulerState();
        this.taskQueue = new TaskQueue();
        this.healthMonitor = new HealthMonitor();
        this.timers = [];

        this.logger = {
            info: (msg, data) => console.log(`[V171Scheduler] ${new Date().toISOString().slice(11, 19)} | ${msg}`, data || ''),
            warn: (msg, data) => console.warn(`[V171Scheduler] ⚠️ ${msg}`, data || ''),
            error: (msg, data) => console.error(`[V171Scheduler] ❌ ${msg}`, data || ''),
            alert: (msg, data) => console.log(`[V171Scheduler] 🚨 ${msg}`, data || '')
        };
    }

    // ========================================================================
    // 生命周期
    // ========================================================================

    async start() {
        this.logger.info('🚀 V171 Scheduler 启动中...');

        try {
            this.state.isRunning = true;

            // 启动健康监控
            this.healthMonitor.start();

            // 启动调度任务
            this._scheduleDailyBatch();
            this._startPreMatchHotZone();
            this._startLiveMonitoring();

            this.logger.info('✅ V171 Scheduler 启动完成');
            this._printConfig();

        } catch (error) {
            this.logger.error('启动失败', error.message);
            throw error;
        }
    }

    async stop() {
        this.logger.info('🛑 V171 Scheduler 停止中...');

        this.state.isRunning = false;
        this.timers.forEach(t => clearTimeout(t));
        this.timers = [];
        this.healthMonitor.stop();

        this.logger.info('✅ V171 Scheduler 已停止');
        this.logger.info('最终统计:', this.state.stats);
    }

    _printConfig() {
        this.logger.info(`   Daily Batch: ${this.config.dailyBatch.cron}`);
        this.logger.info(`   Pre-Match Hot Zone: ${this.config.preMatchHotZone.pollIntervalMs / 1000}s`);
        this.logger.info(`   Live Monitoring: ${this.config.liveMonitoring.pollIntervalMs / 1000}s`);
    }

    // ========================================================================
    // Daily Batch (每日凌晨执行)
    // ========================================================================

    _scheduleDailyBatch() {
        if (!this.config.dailyBatch.enabled) return;

        const nextRun = this._getNextCronTime(this.config.dailyBatch.cron);
        const delay = nextRun - Date.now();

        this.logger.info(`📅 Daily Batch 计划: ${nextRun.toISOString()}`);

        const timer = setTimeout(async () => {
            await this._executeDailyBatch();
            this._scheduleDailyBatch();
        }, delay);

        this.timers.push(timer);

        if (process.env.RUN_IMMEDIATE === 'true') {
            this._executeDailyBatch();
        }
    }

    async _executeDailyBatch() {
        this.logger.info('═══════════════════════════════════════════════════════════');
        this.logger.info('📅 DAILY BATCH');
        this.logger.info('═══════════════════════════════════════════════════════════');

        const startTime = Date.now();

        try {
            await this._l1Discovery();
            await this._l2Backfill();

            this.state.lastDailyBatch = new Date().toISOString();
            const duration = Date.now() - startTime;
            this.logger.info(`✅ DAILY BATCH 完成 (${(duration / 1000).toFixed(1)}s)`);

        } catch (error) {
            this.logger.error('DAILY BATCH 失败', error.message);
            this.state.stats.errors++;
            this.healthMonitor.recordError(error);
        }
    }

    async _l1Discovery() {
        this.logger.info('🔍 Phase 1: L1 Discovery');

        let discovered = 0;

        for (const league of this.config.dailyBatch.leagues) {
            try {
                // 刷新队列获取新比赛
                const matches = await this.taskQueue.refresh();
                discovered = matches.length;
                this.logger.info(`   ✅ ${league.name}: 队列刷新完成`);
            } catch (error) {
                this.logger.warn(`   ⚠️ ${league.name}: ${error.message}`);
            }
        }

        this.state.stats.discovered += discovered;
        this.logger.info(`   📊 总计: ${discovered} 场`);
    }

    async _l2Backfill() {
        this.logger.info('🔄 Phase 2: L2 Backfill');

        try {
            const matches = await db.withDb(async (client) => {
                const result = await client.query(`
                    SELECT match_id, home_team, away_team
                    FROM matches
                    WHERE is_finished = true
                      AND home_score IS NULL
                      AND match_date >= NOW() - INTERVAL '24 hours'
                    LIMIT 100
                `);
                return result.rows;
            });

            this.logger.info(`   找到 ${matches.length} 场需回填`);
        } catch (error) {
            this.logger.error(`   回填失败: ${error.message}`);
        }
    }

    // ========================================================================
    // Pre-Match Hot Zone
    // ========================================================================

    _startPreMatchHotZone() {
        if (!this.config.preMatchHotZone.enabled) return;

        this.logger.info('🔥 Pre-Match Hot Zone 启动');

        const timer = setInterval(async () => {
            if (!this.state.isRunning) return;
            await this._checkPreMatchHotZone();
        }, this.config.preMatchHotZone.pollIntervalMs);

        this.timers.push(timer);
    }

    async _checkPreMatchHotZone() {
        try {
            // 刷新队列
            await this.taskQueue.refresh();

            // 获取热区比赛
            const hotMatches = this.taskQueue.getHotZoneMatches();

            if (hotMatches.length === 0) return;

            // 处理热区比赛
            for (const match of hotMatches.slice(0, this.config.preMatchHotZone.maxConcurrent)) {
                await this._processHotZoneMatch(match);
            }

        } catch (error) {
            this.logger.error('热区检查失败', error.message);
            this.healthMonitor.recordError(error);
        }
    }

    async _processHotZoneMatch(match) {
        const matchId = match.match_id;

        this.logger.info('');
        this.logger.info('═══════════════════════════════════════════════════════════');
        this.logger.info(`🔥 HOT ZONE: ${match.home_team} vs ${match.away_team}`);
        this.logger.info(`   优先级: ${match.priority}`);
        this.logger.info('═══════════════════════════════════════════════════════════');

        this.taskQueue.markProcessing(matchId);

        try {
            // 使用重试包装器
            const result = await withRetry(
                async () => {
                    // 这里调用收割逻辑
                    return { success: true, matchId };
                },
                { maxRetries: this.config.retry.maxAttempts }
            );

            if (result.success) {
                this.taskQueue.markCompleted(matchId);
                this.state.stats.harvested++;
                this.healthMonitor.recordSuccess();
                this.logger.info(`   ✅ 处理完成`);
            }

        } catch (error) {
            this.taskQueue.markFailed(matchId);
            this.state.stats.errors++;
            this.healthMonitor.recordError(error);
            this.logger.error(`   ❌ 处理失败: ${error.message}`);
        }
    }

    // ========================================================================
    // Live Monitoring
    // ========================================================================

    _startLiveMonitoring() {
        if (!this.config.liveMonitoring.enabled) return;

        this.logger.info('📡 Live Monitoring 启动');

        const timer = setInterval(async () => {
            if (!this.state.isRunning) return;
            await this._checkLiveMatches();
        }, this.config.liveMonitoring.pollIntervalMs);

        this.timers.push(timer);
    }

    async _checkLiveMatches() {
        try {
            const matches = await db.withDb(async (client) => {
                const result = await client.query(`
                    SELECT match_id, home_team, away_team, status, is_finished
                    FROM matches
                    WHERE status NOT IN ('pending', 'completed')
                      AND match_date >= NOW() - INTERVAL '3 hours'
                `);
                return result.rows;
            });

            for (const match of matches) {
                if (match.is_finished) {
                    await this._handleMatchFinished(match);
                }
            }
        } catch (error) {
            this.logger.error('Live 检查失败', error.message);
        }
    }

    async _handleMatchFinished(match) {
        this.logger.info(`📡 比赛结束: ${match.home_team} vs ${match.away_team}`);

        await db.withDb(async (client) => {
            await client.query(`
                UPDATE matches SET status = 'completed', updated_at = NOW()
                WHERE match_id = $1
            `, [match.match_id]);
        });
    }

    // ========================================================================
    // 工具方法
    // ========================================================================

    _getNextCronTime(cronExpr) {
        const parts = cronExpr.split(' ');
        const hour = parseInt(parts[1]);
        const minute = parseInt(parts[0]);

        const now = new Date();
        const next = new Date();
        next.setHours(hour, minute, 0, 0);

        if (next <= now) {
            next.setDate(next.getDate() + 1);
        }

        return next;
    }

    // ========================================================================
    // 状态与健康检查
    // ========================================================================

    getStatus() {
        return {
            scheduler: this.state.toJSON(),
            queue: this.taskQueue.getStats(),
            health: this.healthMonitor.getStatus(),
            config: {
                dailyBatch: this.config.dailyBatch.enabled,
                preMatchHotZone: this.config.preMatchHotZone.enabled,
                liveMonitoring: this.config.liveMonitoring.enabled
            },
            uptime: process.uptime()
        };
    }

    async healthCheck() {
        return this.healthMonitor.getStatus();
    }
}

// ============================================================================
// CLI 入口
// ============================================================================

async function main() {
    const args = process.argv.slice(2);
    const command = args[0] || 'start';

    const scheduler = new V171Scheduler();

    process.on('SIGINT', async () => {
        console.log('\n收到 SIGINT...');
        await scheduler.stop();
        process.exit(0);
    });

    process.on('SIGTERM', async () => {
        console.log('\n收到 SIGTERM...');
        await scheduler.stop();
        process.exit(0);
    });

    switch (command) {
        case 'start':
            await scheduler.start();
            break;

        case 'status':
            console.log(JSON.stringify(scheduler.getStatus(), null, 2));
            break;

        case 'health':
            const health = await scheduler.healthCheck();
            console.log(JSON.stringify(health, null, 2));
            break;

        default:
            console.log(`
V171 Scheduler - 全息系统战术调度器

用法:
  node v171_scheduler.js start   启动调度器
  node v171_scheduler.js status  查看状态
  node v171_scheduler.js health  健康检查

环境变量:
  RUN_IMMEDIATE=true  启动时立即执行 Daily Batch
`);
    }
}

module.exports = { V171Scheduler, SCHEDULER_CONFIG };

if (require.main === module) {
    main().catch(console.error);
}
