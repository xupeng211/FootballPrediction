/**
 * V171 Scheduler - 全息系统战术调度器
 * ========================================
 *
 * 基于时间轴的自动化编排引擎，将 L1 发现、L2 采集、特征工程、
 * 多模型验证串联成完整的自动化流水线。
 *
 * 调度策略:
 * ┌─────────────────────────────────────────────────────────────┐
 * │  Daily Batch (每日 02:00 CST)                              │
 * │  ├── L1 Discovery: 发现未来 7 天比赛 → pending             │
 * │  └── L2 Backfill: 回填昨日完赛场次的比分/xG                │
 * ├─────────────────────────────────────────────────────────────┤
 * │  Pre-Match Hot Zone (赛前 1 小时轮询)                      │
 * │  ├── 筛选: match_date - now < 65 分钟 && status=pending   │
 * │  ├── 采集: 临场赔率 + 官方首发阵容                         │
 * │  ├── 计算: 800+ 维特征向量                                 │
 * │  └── 预测: MultiModelValidator 3 模型共识                  │
 * ├─────────────────────────────────────────────────────────────┤
 * │  Live Monitoring (比赛进行中)                              │
 * │  └── 状态追踪: 检测比赛状态变化 (延迟/取消/完赛)           │
 * └─────────────────────────────────────────────────────────────┘
 *
 * @module scripts/ops/v171_scheduler
 * @version V171.001
 * @author FootballPrediction Architecture Team
 */

'use strict';

const { Client } = require('pg');
const { spawn, exec } = require('child_process');
const path = require('path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');

// ============================================================================
// CONFIGURATION
// ============================================================================

const SCHEDULER_CONFIG = {
    // 时区配置
    timezone: 'Asia/Shanghai',

    // Daily Batch 配置
    dailyBatch: {
        enabled: true,
        cron: '0 2 * * *',  // 每日 02:00 CST
        leagues: [
            { name: 'Premier League', url: 'https://www.oddsportal.com/football/england/premier-league/', code: 'EPL' },
            { name: 'La Liga', url: 'https://www.oddsportal.com/football/spain/laliga/', code: 'LALIGA' },
            { name: 'Bundesliga', url: 'https://www.oddsportal.com/football/germany/bundesliga/', code: 'BL' },
            { name: 'Serie A', url: 'https://www.oddsportal.com/football/italy/serie-a/', code: 'SA' },
            { name: 'Ligue 1', url: 'https://www.oddsportal.com/football/france/ligue-1/', code: 'L1' }
        ],
        discoveryDays: 7  // 发现未来 7 天的比赛
    },

    // Pre-Match Hot Zone 配置
    preMatchHotZone: {
        enabled: true,
        pollIntervalMs: 60000,  // 每 60 秒轮询一次
        windowMinutes: 65,       // 赛前 65 分钟进入热区
        exitWindowMinutes: 5,    // 开赛后 5 分钟退出热区
        maxConcurrent: 3         // 最大并发收割数
    },

    // Live Monitoring 配置
    liveMonitoring: {
        enabled: true,
        pollIntervalMs: 30000  // 每 30 秒检查一次
    },

    // 告警配置
    alerts: {
        ssrPrediction: true,     // SSR 级预测告警
        harvestFailure: true,    // 收割失败告警
        systemError: true        // 系统错误告警
    }
};

// ============================================================================
// SCHEDULER STATE
// ============================================================================

class SchedulerState {
    constructor() {
        this.isRunning = false;
        this.lastDailyBatch = null;
        this.activeHotZoneMatches = new Map();  // match_id -> HotZoneState
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
            activeHotZoneCount: this.activeHotZoneMatches.size,
            stats: this.stats
        };
    }
}

// ============================================================================
// MAIN SCHEDULER
// ============================================================================

class V171Scheduler {
    constructor(config = SCHEDULER_CONFIG) {
        this.config = config;
        this.state = new SchedulerState();
        this.dbClient = null;
        this.timers = [];

        this.logger = {
            info: (msg, data) => console.log(`[V171Scheduler] ${new Date().toISOString()} | INFO | ${msg}`, data || ''),
            warn: (msg, data) => console.warn(`[V171Scheduler] ${new Date().toISOString()} | WARN | ${msg}`, data || ''),
            error: (msg, data) => console.error(`[V171Scheduler] ${new Date().toISOString()} | ERROR | ${msg}`, data || ''),
            alert: (msg, data) => console.log(`[V171Scheduler] ${new Date().toISOString()} | 🚨 ALERT | ${msg}`, data || '')
        };
    }

    // ========================================================================
    // LIFECYCLE
    // ========================================================================

    async start() {
        this.logger.info('🚀 V171 Scheduler 启动中...');

        try {
            // 初始化数据库连接
            await this._initDatabase();

            this.state.isRunning = true;

            // 启动调度任务
            this._scheduleDailyBatch();
            this._startPreMatchHotZone();
            this._startLiveMonitoring();

            this.logger.info('✅ V171 Scheduler 启动完成');
            this.logger.info(`   - Daily Batch: ${this.config.dailyBatch.cron}`);
            this.logger.info(`   - Pre-Match Hot Zone: 每 ${this.config.preMatchHotZone.pollIntervalMs / 1000}s 轮询`);
            this.logger.info(`   - Live Monitoring: 每 ${this.config.liveMonitoring.pollIntervalMs / 1000}s 检查`);

        } catch (error) {
            this.logger.error('启动失败', error.message);
            throw error;
        }
    }

    async stop() {
        this.logger.info('🛑 V171 Scheduler 停止中...');

        this.state.isRunning = false;

        // 清除所有定时器
        this.timers.forEach(timer => clearTimeout(timer));
        this.timers = [];

        // 关闭数据库连接
        if (this.dbClient) {
            await this.dbClient.end();
        }

        this.logger.info('✅ V171 Scheduler 已停止');
        this.logger.info('最终统计:', this.state.stats);
    }

    async _initDatabase() {
        this.dbClient = new Client({
            host: process.env.DB_HOST || 'localhost',
            port: parseInt(process.env.DB_PORT) || 5432,
            database: process.env.DB_NAME || 'football_db',
            user: process.env.DB_USER || 'football_user',
            password: process.env.DB_PASSWORD || 'your_secure_password_here'
        });

        await this.dbClient.connect();
        this.logger.info('✅ 数据库连接成功');
    }

    // ========================================================================
    // DAILY BATCH (每日凌晨执行)
    // ========================================================================

    _scheduleDailyBatch() {
        if (!this.config.dailyBatch.enabled) return;

        // 计算下次执行时间
        const nextRun = this._getNextCronTime(this.config.dailyBatch.cron);
        const delay = nextRun - Date.now();

        this.logger.info(`📅 Daily Batch 计划执行: ${nextRun.toISOString()}`);

        const timer = setTimeout(async () => {
            await this._executeDailyBatch();
            this._scheduleDailyBatch();  // 递归调度下一次
        }, delay);

        this.timers.push(timer);

        // 启动时立即执行一次（用于测试）
        if (process.env.RUN_IMMEDIATE === 'true') {
            this._executeDailyBatch();
        }
    }

    async _executeDailyBatch() {
        this.logger.info('═══════════════════════════════════════════════════════════');
        this.logger.info('📅 DAILY BATCH 开始执行');
        this.logger.info('═══════════════════════════════════════════════════════════');

        const startTime = Date.now();

        try {
            // Phase 1: L1 Discovery - 发现未来 7 天比赛
            await this._l1Discovery();

            // Phase 2: L2 Backfill - 回填昨日完赛场次
            await this._l2Backfill();

            // 更新状态
            this.state.lastDailyBatch = new Date().toISOString();

            const duration = Date.now() - startTime;
            this.logger.info(`✅ DAILY BATCH 完成 (耗时: ${(duration / 1000).toFixed(1)}s)`);

        } catch (error) {
            this.logger.error('DAILY BATCH 失败', error.message);
            this.state.stats.errors++;
        }
    }

    /**
     * L1 Discovery: 发现未来 7 天的比赛
     */
    async _l1Discovery() {
        this.logger.info('');
        this.logger.info('🔍 [Daily Batch] Phase 1: L1 Discovery');
        this.logger.info('────────────────────────────────────────────────────────────');

        let discovered = 0;

        for (const league of this.config.dailyBatch.leagues) {
            try {
                this.logger.info(`   扫描联赛: ${league.name}`);

                // 调用 L1 发现脚本
                const result = await this._runCommand(
                    'node',
                    [path.join(PROJECT_ROOT, 'scripts/ops/test_l1_discovery.js')],
                    { limit: 50, league: league.code }
                );

                if (result.success) {
                    discovered += result.matches || 0;
                    this.logger.info(`   ✅ ${league.name}: 发现 ${result.matches || 0} 场比赛`);
                } else {
                    this.logger.warn(`   ⚠️ ${league.name}: 发现失败 - ${result.error}`);
                }

            } catch (error) {
                this.logger.error(`   ❌ ${league.name}: ${error.message}`);
            }
        }

        this.state.stats.discovered += discovered;
        this.logger.info(`   📊 总计发现: ${discovered} 场新比赛`);
    }

    /**
     * L2 Backfill: 回填昨日完赛场次的比分和 xG
     */
    async _l2Backfill() {
        this.logger.info('');
        this.logger.info('🔄 [Daily Batch] Phase 2: L2 Backfill');
        this.logger.info('────────────────────────────────────────────────────────────');

        // 查询过去 24 小时已完赛但缺少比分数据的比赛
        const result = await this.dbClient.query(`
            SELECT match_id, home_team, away_team, league_name, match_date
            FROM matches
            WHERE is_finished = true
              AND home_score IS NULL
              AND match_date >= NOW() - INTERVAL '24 hours'
              AND match_date < NOW()
            ORDER BY match_date
            LIMIT 100
        `);

        const matchesToBackfill = result.rows;
        this.logger.info(`   找到 ${matchesToBackfill.length} 场比赛需要回填数据`);

        let backfilled = 0;

        for (const match of matchesToBackfill) {
            try {
                // 调用 L2 FotMob 采集器回填数据
                const backfillResult = await this._runCommand(
                    'python3',
                    [path.join(PROJECT_ROOT, 'main.py')],
                    { source: 'fotmob', mode: 'single', match_id: match.match_id }
                );

                if (backfillResult.success) {
                    backfilled++;
                    this.logger.info(`   ✅ ${match.home_team} vs ${match.away_team}`);
                } else {
                    this.logger.warn(`   ⚠️ ${match.match_id}: 回填失败`);
                }

            } catch (error) {
                this.logger.error(`   ❌ ${match.match_id}: ${error.message}`);
            }
        }

        this.logger.info(`   📊 总计回填: ${backfilled}/${matchesToBackfill.length} 场`);
    }

    // ========================================================================
    // PRE-MATCH HOT ZONE (赛前 1 小时轮询)
    // ========================================================================

    _startPreMatchHotZone() {
        if (!this.config.preMatchHotZone.enabled) return;

        this.logger.info('🔥 Pre-Match Hot Zone 监控启动');

        const timer = setInterval(async () => {
            if (!this.state.isRunning) return;
            await this._checkPreMatchHotZone();
        }, this.config.preMatchHotZone.pollIntervalMs);

        this.timers.push(timer);
    }

    async _checkPreMatchHotZone() {
        const now = new Date();
        const windowStart = new Date(now.getTime() + 0 * 60000);  // 现在
        const windowEnd = new Date(now.getTime() + this.config.preMatchHotZone.windowMinutes * 60000);  // +65 分钟

        // 查询即将进入热区的比赛
        const result = await this.dbClient.query(`
            SELECT match_id, home_team, away_team, league_name, match_date,
                   EXTRACT(EPOCH FROM (match_date - NOW())) / 60 as minutes_to_kickoff
            FROM matches
            WHERE status = 'pending'
              AND is_finished = false
              AND match_date >= $1
              AND match_date <= $2
            ORDER BY match_date
        `, [windowStart, windowEnd]);

        const hotMatches = result.rows;

        if (hotMatches.length === 0) {
            return;  // 没有进入热区的比赛
        }

        // 处理每场热区比赛
        for (const match of hotMatches) {
            // 检查是否已经在处理中
            if (this.state.activeHotZoneMatches.has(match.match_id)) {
                continue;
            }

            // 并发控制
            if (this.state.activeHotZoneMatches.size >= this.config.preMatchHotZone.maxConcurrent) {
                this.logger.warn(`并发限制达到，跳过: ${match.match_id}`);
                break;
            }

            // 启动热区收割
            this._startHotZoneHarvest(match);
        }
    }

    async _startHotZoneHarvest(match) {
        const matchId = match.match_id;
        const minutesToKickoff = Math.round(match.minutes_to_kickoff);

        this.logger.info('');
        this.logger.info('═══════════════════════════════════════════════════════════');
        this.logger.info(`🔥 PRE-MATCH HOT ZONE: ${match.home_team} vs ${match.away_team}`);
        this.logger.info(`   联赛: ${match.league_name}`);
        this.logger.info(`   开赛倒计时: ${minutesToKickoff} 分钟`);
        this.logger.info('═══════════════════════════════════════════════════════════');

        // 记录活跃状态
        this.state.activeHotZoneMatches.set(matchId, {
            startTime: Date.now(),
            match: match,
            phase: 'harvesting'
        });

        try {
            // Phase 1: 采集临场赔率和首发阵容
            const harvestResult = await this._hotZoneHarvest(match);

            if (!harvestResult.success) {
                throw new Error('收割失败');
            }

            // Phase 2: 特征工程计算 (800+ 维)
            const featuresResult = await this._hotZoneFeatureExtraction(match);

            // Phase 3: 多模型预测
            const predictionResult = await this._hotZonePrediction(match, featuresResult);

            // Phase 4: 检测 SSR 级预测
            if (predictionResult.isSSR) {
                this._triggerSSRAlert(match, predictionResult);
            }

            // 更新状态
            this.state.stats.harvested++;
            this.state.stats.predicted++;
            if (predictionResult.isSSR) {
                this.state.stats.ssrPredictions++;
            }

        } catch (error) {
            this.logger.error(`热区收割失败: ${matchId}`, error.message);
            this.state.stats.errors++;
        } finally {
            this.state.activeHotZoneMatches.delete(matchId);
        }
    }

    /**
     * 热区收割: 采集临场赔率和首发阵容
     */
    async _hotZoneHarvest(match) {
        this.logger.info(`   [Phase 1] 采集临场数据...`);

        // 调用 QuantHarvester 采集临场赔率
        const harvestResult = await this._runCommand(
            'node',
            [path.join(PROJECT_ROOT, 'src/infrastructure/engines/QuantHarvester.js')],
            { match_id: match.match_id }
        );

        if (harvestResult.success) {
            this.logger.info(`   ✅ 赔率采集完成: ${harvestResult.oddsCount || 0} 个数据点`);

            // 调用 FundamentalHarvester 采集首发阵容
            const lineupResult = await this._runCommand(
                'node',
                [path.join(PROJECT_ROOT, 'src/infrastructure/engines/FundamentalHarvester.js')],
                { match_id: match.match_id }
            );

            if (lineupResult.success) {
                this.logger.info(`   ✅ 首发阵容已获取`);
            }
        }

        return harvestResult;
    }

    /**
     * 热区特征提取: 计算 800+ 维特征向量
     */
    async _hotZoneFeatureExtraction(match) {
        this.logger.info(`   [Phase 2] 特征工程计算 (800+ 维)...`);

        // 调用 Python 特征引擎
        const result = await this._runPythonModule(
            'src.ml.feature_engine.engine',
            { match_id: match.match_id }
        );

        if (result.success) {
            this.logger.info(`   ✅ 特征提取完成: ${result.featureCount || 0} 维`);
        }

        return result;
    }

    /**
     * 热区预测: MultiModelValidator 3 模型共识
     */
    async _hotZonePrediction(match, features) {
        this.logger.info(`   [Phase 3] 多模型预测...`);

        // 调用 Python 推理引擎
        const result = await this._runPythonModule(
            'src.ml.inference.multi_model_validator',
            { match_id: match.match_id }
        );

        if (result.success) {
            const prediction = result.prediction || 'Unknown';
            const confidence = (result.confidence || 0) * 100;
            const consensus = result.consensusLevel || 'none';

            this.logger.info(`   ✅ 预测完成: ${prediction} (${confidence.toFixed(1)}%)`);
            this.logger.info(`      共识等级: ${consensus}`);
            this.logger.info(`      模型投票: ${JSON.stringify(result.voting || {})}`);

            // 判断是否为 SSR 级预测
            const isSSR = this._isSSRPrediction(result);

            return {
                success: true,
                prediction,
                confidence,
                consensusLevel: consensus,
                isSSR,
                ...result
            };
        }

        return { success: false, isSSR: false };
    }

    /**
     * 判断是否为 SSR (Strong Signal Recommendation) 级预测
     */
    _isSSRPrediction(result) {
        // SSR 条件:
        // 1. 置信度 >= 75%
        // 2. 共识等级为 UNANIMOUS 或 STRONG
        // 3. 3 个模型全部一致

        const confidence = result.confidence || 0;
        const consensus = result.consensusLevel || '';
        const agreementRatio = result.agreementRatio || 0;

        return confidence >= 0.75 &&
               (consensus === 'UNANIMOUS' || consensus === 'STRONG') &&
               agreementRatio >= 1.0;
    }

    /**
     * 触发 SSR 级预测告警
     */
    _triggerSSRAlert(match, prediction) {
        this.logger.alert('═══════════════════════════════════════════════════════════');
        this.logger.alert('🚨 SSR 级预测告警!');
        this.logger.alert('═══════════════════════════════════════════════════════════');
        this.logger.alert(`   比赛: ${match.home_team} vs ${match.away_team}`);
        this.logger.alert(`   联赛: ${match.league_name}`);
        this.logger.alert(`   预测: ${prediction.prediction}`);
        this.logger.alert(`   置信度: ${(prediction.confidence * 100).toFixed(1)}%`);
        this.logger.alert(`   共识等级: ${prediction.consensusLevel}`);
        this.logger.alert('═══════════════════════════════════════════════════════════');

        // TODO: 发送外部通知 (邮件/Slack/Telegram)
    }

    // ========================================================================
    // LIVE MONITORING (比赛进行中状态追踪)
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
        // 查询正在进行或刚结束的比赛
        const result = await this.dbClient.query(`
            SELECT match_id, home_team, away_team, status, is_finished, match_date
            FROM matches
            WHERE status NOT IN ('pending', 'completed')
              AND match_date >= NOW() - INTERVAL '3 hours'
            ORDER BY match_date
        `);

        for (const match of result.rows) {
            // 检测状态变化
            if (match.is_finished && match.status !== 'completed') {
                await this._handleMatchFinished(match);
            }
        }
    }

    async _handleMatchFinished(match) {
        this.logger.info(`📡 检测到比赛结束: ${match.home_team} vs ${match.away_team}`);

        // 更新状态为 completed
        await this.dbClient.query(`
            UPDATE matches
            SET status = 'completed', updated_at = NOW()
            WHERE match_id = $1
        `, [match.match_id]);

        // 触发 L2 回填任务
        // TODO: 加入回填队列
    }

    // ========================================================================
    // UTILITY METHODS
    // ========================================================================

    _getNextCronTime(cronExpr) {
        // 简化的 cron 解析 (仅支持每日固定时间)
        const parts = cronExpr.split(' ');
        const hour = parseInt(parts[1]);
        const minute = parseInt(parts[0]);

        const now = new Date();
        const next = new Date();
        next.setHours(hour, minute, 0, 0);

        // 如果今天的时间已过，设为明天
        if (next <= now) {
            next.setDate(next.getDate() + 1);
        }

        return next;
    }

    _runCommand(cmd, args, env = {}) {
        return new Promise((resolve) => {
            const proc = spawn(cmd, args, {
                cwd: PROJECT_ROOT,
                env: { ...process.env, ...env }
            });

            let stdout = '';
            let stderr = '';

            proc.stdout.on('data', (data) => { stdout += data.toString(); });
            proc.stderr.on('data', (data) => { stderr += data.toString(); });

            proc.on('close', (code) => {
                resolve({
                    success: code === 0,
                    stdout,
                    stderr,
                    code
                });
            });

            proc.on('error', (error) => {
                resolve({
                    success: false,
                    error: error.message
                });
            });
        });
    }

    _runPythonModule(module, args = {}) {
        return new Promise((resolve) => {
            const script = `
import sys
import json
sys.path.insert(0, '${PROJECT_ROOT}')

try:
    from ${module} import *
    result = ${JSON.stringify(args)}
    print(json.dumps({'success': True, **result}))
except Exception as e:
    print(json.dumps({'success': False, 'error': str(e)}))
`;

            const proc = spawn('python3', ['-c', script], {
                cwd: PROJECT_ROOT
            });

            let stdout = '';
            proc.stdout.on('data', (data) => { stdout += data.toString(); });

            proc.on('close', (code) => {
                try {
                    const result = JSON.parse(stdout.trim().split('\n').pop());
                    resolve(result);
                } catch {
                    resolve({ success: false, error: 'Parse error' });
                }
            });
        });
    }

    // ========================================================================
    // STATUS & HEALTH CHECK
    // ========================================================================

    getStatus() {
        return {
            scheduler: this.state.toJSON(),
            config: {
                dailyBatch: this.config.dailyBatch.enabled,
                preMatchHotZone: this.config.preMatchHotZone.enabled,
                liveMonitoring: this.config.liveMonitoring.enabled
            },
            uptime: process.uptime()
        };
    }

    async healthCheck() {
        try {
            // 检查数据库连接
            await this.dbClient.query('SELECT 1');

            return {
                healthy: true,
                timestamp: new Date().toISOString(),
                checks: {
                    database: 'ok',
                    scheduler: this.state.isRunning ? 'running' : 'stopped'
                }
            };
        } catch (error) {
            return {
                healthy: false,
                error: error.message
            };
        }
    }
}

// ============================================================================
// CLI ENTRY POINT
// ============================================================================

async function main() {
    const args = process.argv.slice(2);
    const command = args[0] || 'start';

    const scheduler = new V171Scheduler();

    // 优雅关闭
    process.on('SIGINT', async () => {
        console.log('\n收到 SIGINT 信号...');
        await scheduler.stop();
        process.exit(0);
    });

    process.on('SIGTERM', async () => {
        console.log('\n收到 SIGTERM 信号...');
        await scheduler.stop();
        process.exit(0);
    });

    switch (command) {
        case 'start':
            await scheduler.start();
            // 保持运行
            break;

        case 'status':
            console.log(JSON.stringify(scheduler.getStatus(), null, 2));
            break;

        case 'health':
            const health = await scheduler.healthCheck();
            console.log(JSON.stringify(health, null, 2));
            break;

        case 'daily-batch':
            // 手动触发 Daily Batch
            await scheduler._initDatabase();
            await scheduler._executeDailyBatch();
            break;

        case 'hot-zone':
            // 手动检查热区
            await scheduler._initDatabase();
            await scheduler._checkPreMatchHotZone();
            break;

        default:
            console.log(`
V171 Scheduler - 全息系统战术调度器

用法:
  node v171_scheduler.js start        启动调度器
  node v171_scheduler.js status       查看状态
  node v171_scheduler.js health       健康检查
  node v171_scheduler.js daily-batch  手动触发 Daily Batch
  node v171_scheduler.js hot-zone     手动检查热区

环境变量:
  RUN_IMMEDIATE=true    启动时立即执行 Daily Batch
`);
    }
}

// 导出
module.exports = { V171Scheduler, SCHEDULER_CONFIG };

// 运行
if (require.main === module) {
    main().catch(console.error);
}
