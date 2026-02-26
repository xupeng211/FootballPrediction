/**
 * V173-A1 增量数据工厂 (Incremental Data Factory)
 * ================================================
 *
 * 模式:
 * - Incremental Mode: 每日增量 (默认)
 * - Repair Mode: 补漏修复
 * - Full Mode: 全量扫荡
 *
 * 特性:
 * - 自动增量筛选
 * - 哨兵监控
 * - 自动补漏
 * - 日志滚动
 *
 * @module scripts/ops/incremental_factory
 * @version V173.100
 */

'use strict';

const { fork } = require('child_process');
const path = require('path');
const fs = require('fs');
const { Client } = require('pg');

// ============================================================================
// 配置
// ============================================================================

const FACTORY_CONFIG = {
    // 运行模式
    mode: process.env.FACTORY_MODE || 'incremental',  // incremental | repair | full

    // 并发配置
    maxWorkers: parseInt(process.env.MAX_WORKERS) || 3,
    proxyPorts: (process.env.PROXY_PORTS || '7890,7891,7892').split(',').map(p => parseInt(p)),

    // 延时配置
    staggerStartMs: 5000,
    minDelayMs: 5000,
    maxDelayMs: 12000,

    // 哨兵配置
    maxFailureRate: 0.10,           // 最大失败率 10%
    maxConsecutive403: 5,            // 最大连续 403 次数
    healthReportPath: '/app/logs/factory_health.json',

    // 日志滚动
    logRetentionDays: 7,

    // Cookie 配置
    cookiePath: '/app/data/browser_profile/browser_state.json',
    cookieMaxAge: 24 * 60 * 60 * 1000,  // 24 小时

    // 增量模式配置
    incrementalLookbackDays: 7,      // 回溯天数

    // 补漏配置
    repairMaxAttempts: 3,            // 最大重试次数
    repairCooldownMs: 60000          // 补漏冷却时间
};

// ============================================================================
// 哨兵监控系统
// ============================================================================

class FactorySentinel {
    constructor() {
        this.metrics = {
            startTime: Date.now(),
            endTime: null,
            totalTasks: 0,
            processed: 0,
            success: 0,
            failed: 0,
            skipped: 0,
            consecutive403: 0,
            errors: [],
            avgResponseTime: 0,
            responseTimes: []
        };
        this.healthStatus = 'healthy';
        this.alerts = [];
    }

    recordSuccess(responseTime) {
        this.metrics.success++;
        this.metrics.processed++;
        this.metrics.consecutive403 = 0;
        this.metrics.responseTimes.push(responseTime);
    }

    recordFailure(error, matchId) {
        this.metrics.failed++;
        this.metrics.processed++;

        const errorMsg = error.message || String(error);

        // 检测 403 错误
        if (errorMsg.includes('403') || errorMsg.includes('Forbidden')) {
            this.metrics.consecutive403++;
        }

        this.metrics.errors.push({
            matchId,
            error: errorMsg.substring(0, 200),
            timestamp: new Date().toISOString()
        });

        this._checkHealth();
    }

    _checkHealth() {
        const failureRate = this.metrics.processed > 0
            ? this.metrics.failed / this.metrics.processed
            : 0;

        // 检查失败率
        if (failureRate > FACTORY_CONFIG.maxFailureRate && this.metrics.processed >= 10) {
            this.healthStatus = 'degraded';
            this.alerts.push({
                type: 'HIGH_FAILURE_RATE',
                message: `失败率 ${((failureRate) * 100).toFixed(1)}% 超过阈值 ${FACTORY_CONFIG.maxFailureRate * 100}%`,
                timestamp: new Date().toISOString()
            });
        }

        // 检查连续 403
        if (this.metrics.consecutive403 >= FACTORY_CONFIG.maxConsecutive403) {
            this.healthStatus = 'critical';
            this.alerts.push({
                type: 'CONSECUTIVE_403',
                message: `连续 ${this.metrics.consecutive403} 次 403 错误，可能需要更换 Cookie`,
                timestamp: new Date().toISOString()
            });
        }
    }

    shouldAbort() {
        return this.healthStatus === 'critical';
    }

    finalize() {
        this.metrics.endTime = Date.now();

        // 计算平均响应时间
        if (this.metrics.responseTimes.length > 0) {
            this.metrics.avgResponseTime = this.metrics.responseTimes.reduce((a, b) => a + b, 0) / this.metrics.responseTimes.length;
        }

        return this.generateReport();
    }

    generateReport() {
        const report = {
            version: 'V173-A1',
            timestamp: new Date().toISOString(),
            mode: FACTORY_CONFIG.mode,
            health: this.healthStatus,
            alerts: this.alerts,
            metrics: {
                totalTasks: this.metrics.totalTasks,
                processed: this.metrics.processed,
                success: this.metrics.success,
                failed: this.metrics.failed,
                skipped: this.metrics.skipped,
                successRate: this.metrics.processed > 0
                    ? ((this.metrics.success / this.metrics.processed) * 100).toFixed(2) + '%'
                    : '0%',
                avgResponseTime: Math.round(this.metrics.avgResponseTime) + 'ms',
                duration: Math.round((this.metrics.endTime - this.metrics.startTime) / 1000) + 's'
            },
            errors: this.metrics.errors.slice(-10),  // 最近 10 个错误
            cookieStatus: this._checkCookieStatus()
        };

        // 保存报告
        this._saveReport(report);

        return report;
    }

    _checkCookieStatus() {
        try {
            const stats = fs.statSync(FACTORY_CONFIG.cookiePath);
            const age = Date.now() - stats.mtimeMs;
            const ageHours = Math.round(age / (60 * 60 * 1000));

            return {
                exists: true,
                ageHours,
                fresh: age < FACTORY_CONFIG.cookieMaxAge,
                lastModified: stats.mtime
            };
        } catch {
            return { exists: false };
        }
    }

    _saveReport(report) {
        const reportPath = FACTORY_CONFIG.healthReportPath;
        const dir = path.dirname(reportPath);

        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }

        fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
    }
}

// ============================================================================
// 增量数据工厂
// ============================================================================

class IncrementalFactory {
    constructor() {
        this.client = null;
        this.sentinel = new FactorySentinel();
        this.workers = new Map();
        this.taskQueue = [];
        this.running = true;
    }

    // ========================================================================
    // 数据库连接
    // ========================================================================

    async connect() {
        const { DatabaseConfig } = require('/app/config/database');
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
        for (const [id, worker] of this.workers) {
            if (worker.process) {
                worker.process.send({ type: 'SHUTDOWN' });
            }
        }
        if (this.client) {
            await this.client.end();
        }
    }

    // ========================================================================
    // 任务加载 - 多模式支持
    // ========================================================================

    async loadTasks() {
        switch (FACTORY_CONFIG.mode) {
            case 'incremental':
                return this._loadIncrementalTasks();
            case 'repair':
                return this._loadRepairTasks();
            case 'full':
                return this._loadFullTasks();
            default:
                return this._loadIncrementalTasks();
        }
    }

    /**
     * 增量模式: 只收割最近结束且缺失数据的比赛
     */
    async _loadIncrementalTasks() {
        const query = `
            SELECT
                m.match_id,
                m.external_id,
                m.home_team,
                m.away_team,
                m.league_name,
                m.match_date,
                m.status
            FROM matches m
            LEFT JOIN raw_match_data r ON m.match_id = r.match_id
            WHERE m.external_id IS NOT NULL
              AND m.external_id <> ''
              AND (m.status = 'completed' OR m.status = 'finished')
              AND m.match_date > NOW() - INTERVAL '${FACTORY_CONFIG.incrementalLookbackDays} days'
              AND (
                  r.match_id IS NULL
                  OR r.l2_raw_json IS NULL
                  OR r.l2_raw_json::text = '{}'
                  OR LENGTH(r.l2_raw_json::text) < 5000
              )
            ORDER BY m.match_date DESC
        `;

        const result = await this.client.query(query);
        console.log(`   📈 增量模式: 找到 ${result.rows.length} 场新比赛`);
        return result.rows;
    }

    /**
     * 补漏模式: 只处理之前失败的任务
     */
    async _loadRepairTasks() {
        const query = `
            SELECT
                m.match_id,
                m.external_id,
                m.home_team,
                m.away_team,
                m.league_name,
                m.match_date,
                m.status
            FROM matches m
            JOIN raw_match_data r ON m.match_id = r.match_id
            WHERE m.external_id IS NOT NULL
              AND m.external_id <> ''
              AND (
                  LENGTH(r.l2_raw_json::text) < 5000
                  OR r.l2_raw_json::text LIKE '%error%'
                  OR r.l2_raw_json::text LIKE '%TURNSTILE%'
                  OR r.l2_raw_json::text LIKE '%Failed%'
              )
            ORDER BY m.match_date DESC
        `;

        const result = await this.client.query(query);
        console.log(`   🔧 补漏模式: 找到 ${result.rows.length} 条坏账`);
        return result.rows;
    }

    /**
     * 全量模式: 扫荡所有缺失数据
     */
    async _loadFullTasks() {
        const query = `
            SELECT
                m.match_id,
                m.external_id,
                m.home_team,
                m.away_team,
                m.league_name,
                m.match_date,
                m.status
            FROM matches m
            LEFT JOIN raw_match_data r ON m.match_id = r.match_id
            WHERE m.external_id IS NOT NULL
              AND m.external_id <> ''
              AND (
                  r.match_id IS NULL
                  OR r.l2_raw_json IS NULL
                  OR r.l2_raw_json::text = '{}'
                  OR LENGTH(r.l2_raw_json::text) < 5000
              )
            ORDER BY m.match_date DESC
        `;

        const result = await this.client.query(query);
        console.log(`   🌊 全量模式: 找到 ${result.rows.length} 场比赛`);
        return result.rows;
    }

    // ========================================================================
    // Worker 管理
    // ========================================================================

    spawnWorker(workerId, proxyPort) {
        const workerPath = path.join(__dirname, 'harvest_worker.js');

        const worker = fork(workerPath, [], {
            env: {
                ...process.env,
                WORKER_ID: workerId,
                PROXY_PORT: proxyPort,
                MIN_DELAY_MS: FACTORY_CONFIG.minDelayMs,
                MAX_DELAY_MS: FACTORY_CONFIG.maxDelayMs,
                COOKIE_SAVE_INTERVAL: 3
            }
        });

        this.workers.set(workerId, {
            process: worker,
            port: proxyPort,
            consecutiveErrors: 0,
            status: 'STARTING'
        });

        worker.on('message', (msg) => this.handleWorkerMessage(workerId, msg));
        worker.on('exit', (code) => {
            if (code !== 0 && this.running) {
                console.log(`⚠️  Worker ${workerId} 退出 (code: ${code})`);
                if (!this.sentinel.shouldAbort()) {
                    setTimeout(() => this.spawnWorker(workerId, proxyPort), 30000);
                }
            }
        });

        return worker;
    }

    handleWorkerMessage(workerId, msg) {
        const worker = this.workers.get(workerId);

        switch (msg.type) {
            case 'READY':
                this._updateWorkerStatus(workerId, 'READY');
                this.sendTask(workerId);
                break;

            case 'TASK_START':
                this._updateWorkerStatus(workerId, 'RUNNING', msg.matchId);
                break;

            case 'TASK_SUCCESS':
                worker.consecutiveErrors = 0;
                this.sentinel.recordSuccess(msg.responseTime || 0);
                this.sendTask(workerId);
                break;

            case 'TASK_FAILED':
                worker.consecutiveErrors++;
                this.sentinel.recordFailure(new Error(msg.error), msg.matchId);

                if (this.sentinel.shouldAbort()) {
                    console.log('🚨 哨兵触发紧急停止！');
                    this.running = false;
                    this.disconnect();
                } else {
                    this.sendTask(workerId);
                }
                break;
        }
    }

    _updateWorkerStatus(workerId, status, currentMatch = null) {
        const worker = this.workers.get(workerId);
        if (worker) {
            worker.status = status;
            worker.currentMatch = currentMatch;
        }
        this.renderDashboard();
    }

    sendTask(workerId) {
        if (this.taskQueue.length === 0) {
            this._updateWorkerStatus(workerId, 'WAITING');
            return;
        }

        const task = this.taskQueue.shift();
        const worker = this.workers.get(workerId);

        if (worker?.process) {
            worker.process.send({ type: 'TASK', task });
        }
    }

    // ========================================================================
    // 仪表盘
    // ========================================================================

    renderDashboard() {
        console.clear();

        console.log('');
        console.log('═'.repeat(80));
        console.log(`  V173-A1 增量数据工厂 [${FACTORY_CONFIG.mode.toUpperCase()} MODE]`);
        console.log(`  健康: ${this.sentinel.healthStatus.toUpperCase()}`);
        console.log('═'.repeat(80));
        console.log('');

        // Worker 状态
        console.log('┌' + '─'.repeat(78) + '┐');
        for (const [workerId, worker] of this.workers) {
            const icon = worker.status === 'RUNNING' ? '🔥' :
                         worker.status === 'WAITING' ? '⏳' : '❓';
            const matchStr = worker.currentMatch ? ` | ${worker.currentMatch.substring(0, 25)}` : '';
            console.log(`│ Worker ${workerId} [Port ${worker.port}]: ${icon} ${worker.status.padEnd(10)}${matchStr}`);
        }
        console.log('└' + '─'.repeat(78) + '┘');

        // 进度
        const processed = this.sentinel.metrics.processed;
        const total = this.sentinel.metrics.totalTasks;
        const pct = total > 0 ? ((processed / total) * 100).toFixed(1) : '0.0';
        const bar = '█'.repeat(Math.floor(parseFloat(pct) / 5)) + '░'.repeat(20 - Math.floor(parseFloat(pct) / 5));

        console.log('');
        console.log('─'.repeat(80));
        console.log(`  进度: [${bar}] ${pct}% | ${processed}/${total}`);
        console.log(`  成功: ${this.sentinel.metrics.success} | 失败: ${this.sentinel.metrics.failed}`);
        console.log('─'.repeat(80));

        // 告警
        if (this.sentinel.alerts.length > 0) {
            console.log('');
            console.log('⚠️  告警:');
            this.sentinel.alerts.forEach(alert => {
                console.log(`   [${alert.type}] ${alert.message}`);
            });
        }
    }

    // ========================================================================
    // 日志滚动
    // ========================================================================

    cleanOldLogs() {
        const logDir = '/app/logs';
        if (!fs.existsSync(logDir)) return;

        const cutoff = Date.now() - FACTORY_CONFIG.logRetentionDays * 24 * 60 * 60 * 1000;

        fs.readdirSync(logDir)
            .filter(f => f.endsWith('.log') || f.endsWith('.json'))
            .forEach(f => {
                const filePath = path.join(logDir, f);
                const stat = fs.statSync(filePath);
                if (stat.mtimeMs < cutoff) {
                    fs.unlinkSync(filePath);
                    console.log(`🗑️  清理旧日志: ${f}`);
                }
            });
    }

    // ========================================================================
    // 主循环
    // ========================================================================

    async run() {
        console.log('');
        console.log('═'.repeat(80));
        console.log('  V173-A1 增量数据工厂');
        console.log('═'.repeat(80));
        console.log('');
        console.log(`📋 模式: ${FACTORY_CONFIG.mode}`);
        console.log(`   Workers: ${FACTORY_CONFIG.maxWorkers}`);
        console.log(`   Ports: ${FACTORY_CONFIG.proxyPorts.join(', ')}`);
        console.log('');

        // 清理旧日志
        this.cleanOldLogs();

        await this.connect();

        // 加载任务
        console.log('🔍 加载任务...');
        this.taskQueue = await this.loadTasks();
        this.sentinel.metrics.totalTasks = this.taskQueue.length;

        if (this.taskQueue.length === 0) {
            console.log('');
            console.log('✅ 无新任务，工厂休眠');
            this.sentinel.finalize();
            await this.disconnect();
            return;
        }

        console.log('');
        console.log('🚀 启动 Workers...');

        // 错峰启动
        for (let i = 0; i < FACTORY_CONFIG.maxWorkers; i++) {
            const workerId = i + 1;
            const port = FACTORY_CONFIG.proxyPorts[i % FACTORY_CONFIG.proxyPorts.length];
            this.spawnWorker(workerId, port);
            console.log(`   Worker ${workerId} -> Port ${port}`);

            if (i < FACTORY_CONFIG.maxWorkers - 1) {
                await new Promise(r => setTimeout(r, FACTORY_CONFIG.staggerStartMs));
            }
        }

        // 等待完成
        await this.waitForCompletion();

        // 生成报告
        const report = this.sentinel.finalize();

        console.log('');
        console.log('═'.repeat(80));
        console.log('  工厂运行报告');
        console.log('═'.repeat(80));
        console.log(`  健康: ${report.health}`);
        console.log(`  成功率: ${report.metrics.successRate}`);
        console.log(`  处理: ${report.metrics.processed}/${report.metrics.totalTasks}`);
        console.log(`  耗时: ${report.metrics.duration}`);
        console.log(`  报告: ${FACTORY_CONFIG.healthReportPath}`);

        if (report.alerts.length > 0) {
            console.log('');
            console.log('⚠️  告警:');
            report.alerts.forEach(a => console.log(`   [${a.type}] ${a.message}`));
        }

        console.log('═'.repeat(80));

        await this.disconnect();
    }

    async waitForCompletion() {
        return new Promise((resolve) => {
            const check = setInterval(() => {
                if (this.sentinel.metrics.processed >= this.sentinel.metrics.totalTasks ||
                    this.sentinel.shouldAbort() ||
                    !this.running) {
                    clearInterval(check);
                    resolve();
                }
            }, 1000);
        });
    }
}

// ============================================================================
// Cron 调度支持
// ============================================================================

/**
 * Cron 模式: 每天凌晨 4:00 运行
 *
 * crontab -e:
 * 0 4 * * * docker exec football_prediction_dev node scripts/ops/incremental_factory.js >> /var/log/factory.log 2>&1
 */

// ============================================================================
// 主入口
// ============================================================================

async function main() {
    const factory = new IncrementalFactory();

    process.on('SIGINT', async () => {
        console.log('\n收到中断信号...');
        factory.running = false;
        await factory.disconnect();
        process.exit(0);
    });

    try {
        await factory.run();
    } catch (error) {
        console.error('\n❌ 工厂异常:', error.message);
        process.exit(1);
    }
}

main();
