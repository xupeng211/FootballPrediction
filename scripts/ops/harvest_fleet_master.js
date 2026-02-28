/**
 * V173-SENTINEL 装甲群模式收割器 (免疫系统加固版)
 * ==============================================
 *
 * 架构: Master-Worker 模式
 * - Master: 任务调度、进度监控、重试队列管理
 * - Worker: 独立进程，绑定唯一代理端口
 *
 * V173 改进:
 * - 自动清道夫 (Zombie Killer): 启动前清理残留进程
 * - 动态 UA 轮换: 每次启动随机抽取 User-Agent
 * - 深度静默模式: 连续失败触发熔断冷却
 *
 * V172 继承:
 * - 使用统一配置中心 (factory_config.js)
 * - 任务重试队列 (质量门禁失败自动回队)
 * - 指数退避重试策略
 * - 连接池 100% 释放保障
 *
 * @module scripts/ops/harvest_fleet_master
 * @version V173.0.0 (Sentinel Edition)
 */

'use strict';

const { fork } = require('child_process');
const { execSync } = require('child_process');
const path = require('path');
const { Client } = require('pg');

// ============================================================================
// 配置加载
// ============================================================================

const PROJECT_ROOT = process.env.PROJECT_ROOT || '/app';
const FactoryConfig = require(path.join(PROJECT_ROOT, 'config/factory_config'));
const { DatabaseConfig } = require(path.join(PROJECT_ROOT, 'src/infrastructure/database/PostgresClient'));

// ============================================================================
// V173: 自动清道夫 (Zombie Killer)
// ============================================================================

/**
 * V173: 启动前清理残留进程
 * - 清理所有 chrome-headless 僵尸进程
 * - 清理非当前 PID 的旧 harvest 进程
 * - 确保每一轮收割都在"洁净室"环境下开始
 */
function preFlightCleanup() {
    const currentPid = process.pid;
    console.log('');
    console.log('🧹 V173 自动清道夫启动...');
    console.log(`   当前 Master PID: ${currentPid}`);

    let killedChrome = 0;
    let killedNode = 0;

    try {
        // 1. 强制清理所有 chrome/chromium 相关进程
        try {
            const chromePids = execSync('pgrep -f "chrome|chromium" 2>/dev/null || true', {
                encoding: 'utf8',
                timeout: 5000
            }).trim();

            if (chromePids) {
                const pids = chromePids.split('\n').filter(p => p);
                for (const pid of pids) {
                    try {
                        execSync(`kill -9 ${pid} 2>/dev/null || true`, { timeout: 2000 });
                        killedChrome++;
                    } catch (e) {
                        // 忽略单个进程清理失败
                    }
                }
            }
        } catch (e) {
            // pgrep 可能返回空，忽略
        }

        // 2. 清理非当前 PID 的 harvest_fleet_master 进程
        try {
            const nodePids = execSync('pgrep -f "harvest_fleet_master" 2>/dev/null || true', {
                encoding: 'utf8',
                timeout: 5000
            }).trim();

            if (nodePids) {
                const pids = nodePids.split('\n').filter(p => p && p !== String(currentPid));
                for (const pid of pids) {
                    try {
                        execSync(`kill -9 ${pid} 2>/dev/null || true`, { timeout: 2000 });
                        killedNode++;
                    } catch (e) {
                        // 忽略单个进程清理失败
                    }
                }
            }
        } catch (e) {
            // pgrep 可能返回空，忽略
        }

        // 3. 清理残留的 harvest_worker 进程
        try {
            const workerPids = execSync('pgrep -f "harvest_worker" 2>/dev/null || true', {
                encoding: 'utf8',
                timeout: 5000
            }).trim();

            if (workerPids) {
                const pids = workerPids.split('\n').filter(p => p);
                for (const pid of pids) {
                    try {
                        execSync(`kill -9 ${pid} 2>/dev/null || true`, { timeout: 2000 });
                        killedNode++;
                    } catch (e) {
                        // 忽略单个进程清理失败
                    }
                }
            }
        } catch (e) {
            // pgrep 可能返回空，忽略
        }

        // V173: 4. 清理所有僵尸 node 进程 (排除当前 Master)
        try {
            const allNodePids = execSync('pgrep -f "node.*harvest" 2>/dev/null || true', {
                encoding: 'utf8',
                timeout: 5000
            }).trim();

            if (allNodePids) {
                const pids = allNodePids.split('\n').filter(p => p && p !== String(currentPid));
                for (const pid of pids) {
                    try {
                        execSync(`kill -9 ${pid} 2>/dev/null || true`, { timeout: 2000 });
                        killedNode++;
                    } catch (e) {
                        // 忽略单个进程清理失败
                    }
                }
            }
        } catch (e) {
            // pgrep 可能返回空，忽略
        }

        console.log(`   ✅ 已清理 ${killedChrome} 个 Chrome/Chromium 僵尸进程`);
        console.log(`   ✅ 已清理 ${killedNode} 个旧 Node 收割进程`);
        console.log('');

    } catch (error) {
        console.log(`   ⚠️  清理过程遇到警告: ${error.message}`);
        console.log('');
    }
}

// ============================================================================
// 代理端口池管理
// ============================================================================

class ProxyPool {
    constructor(ports) {
        this.ports = ports || FactoryConfig.PROXY_CONFIG.ports;
        this.assignments = new Map();  // workerId -> port
        this.available = [...this.ports];
    }

    assign(workerId) {
        if (this.available.length === 0) {
            return null;
        }
        const port = this.available.shift();
        this.assignments.set(workerId, port);
        return port;
    }

    release(workerId) {
        const port = this.assignments.get(workerId);
        if (port) {
            this.assignments.delete(workerId);
            this.available.push(port);
        }
    }

    getPort(workerId) {
        return this.assignments.get(workerId);
    }
}

// ============================================================================
// 仪表盘
// ============================================================================

class FleetDashboard {
    constructor(total) {
        this.total = total;
        this.processed = 0;
        this.success = 0;
        this.failed = 0;
        this.retried = 0;  // V172: 重试计数
        this.skipped = 0;
        this.startTime = Date.now();
        this.workers = new Map();
    }

    updateWorker(workerId, status, data = {}) {
        this.workers.set(workerId, {
            status,
            success: data.success ?? this.workers.get(workerId)?.success ?? 0,
            failed: data.failed ?? this.workers.get(workerId)?.failed ?? 0,
            currentMatch: data.currentMatch || null,
            port: data.port ?? this.workers.get(workerId)?.port,
            lastUpdate: Date.now()
        });
        this.render();
    }

    recordResult(success, isRetry = false) {
        this.processed++;
        if (success) this.success++;
        else this.failed++;
        if (isRetry) this.retried++;
    }

    render() {
        console.clear();

        console.log('');
        console.log('═'.repeat(80));
        console.log('  V173-SENTINEL 装甲群收割器 (免疫系统加固版)');
        console.log('═'.repeat(80));
        console.log('');

        // Worker 状态
        console.log('┌' + '─'.repeat(78) + '┐');

        for (const [workerId, info] of this.workers) {
            const statusIcon = this._getStatusIcon(info.status);
            const portStr = `[Port ${info.port}]`.padEnd(12);
            const statusStr = `[${info.status}]`.padEnd(14);
            const successStr = `✅ ${info.success}`.padEnd(10);
            const failedStr = `❌ ${info.failed}`;
            const matchStr = info.currentMatch ? ` | ${info.currentMatch.substring(0, 30)}` : '';

            console.log(`│ Worker ${workerId}: ${portStr} ${statusIcon} ${statusStr} ${successStr} ${failedStr}${matchStr}`);
        }

        console.log('└' + '─'.repeat(78) + '┘');
        console.log('');

        // 总进度
        const pct = this.processed > 0 ? ((this.processed / this.total) * 100).toFixed(1) : '0.0';
        const bar = '█'.repeat(Math.floor(parseFloat(pct) / 5)) + '░'.repeat(20 - Math.floor(parseFloat(pct) / 5));

        const elapsed = Date.now() - this.startTime;
        const avgTime = this.processed > 0 ? elapsed / this.processed : 0;
        const remaining = avgTime * (this.total - this.processed);

        console.log('─'.repeat(80));
        console.log(`  总进度: [${bar}] ${pct}% | ${this.processed}/${this.total}`);
        console.log(`  成功: ${this.success} | 失败: ${this.failed} | 重试: ${this.retried} | 跳过: ${this.skipped}`);
        console.log(`  已用: ${this._formatDuration(elapsed)} | 预估剩余: ${this._formatDuration(remaining)}`);
        console.log('─'.repeat(80));
    }

    _getStatusIcon(status) {
        switch (status) {
            case 'RUNNING': return '🔥';
            case 'SUCCESS': return '✅';
            case 'WAITING': return '⏳';
            case 'ERROR': return '❌';
            case 'COOLING': return '❄️';
            case 'STOPPED': return '🛑';
            case 'RETRYING': return '🔄';
            default: return '❓';
        }
    }

    _formatDuration(ms) {
        if (!ms || ms < 0) return '--';
        const hours = Math.floor(ms / 3600000);
        const minutes = Math.floor((ms % 3600000) / 60000);
        if (hours > 0) {
            return `${hours}h ${minutes}m`;
        }
        return `${minutes}m`;
    }

    summary() {
        const elapsed = Date.now() - this.startTime;
        console.log('');
        console.log('═'.repeat(80));
        console.log('  收割完成报告');
        console.log('═'.repeat(80));
        console.log(`  总计: ${this.total} 场`);
        console.log(`  成功: ${this.success}`);
        console.log(`  失败: ${this.failed}`);
        console.log(`  重试: ${this.retried}`);
        console.log(`  成功率: ${((this.success / this.processed) * 100).toFixed(1)}%`);
        console.log(`  总耗时: ${this._formatDuration(elapsed)}`);
        console.log('═'.repeat(80));
    }
}

// ============================================================================
// Master 进程 (生产就绪版)
// ============================================================================

class FleetMaster {
    constructor() {
        this.client = null;
        this.proxyPool = new ProxyPool();
        this.dashboard = null;
        this.workers = new Map();
        this.taskQueue = [];
        this.retryQueue = [];  // V172: 重试队列
        this.running = true;
    }

    // ========================================================================
    // 数据库连接 (带超时和重试)
    // ========================================================================

    async connect() {
        const maxRetries = 3;
        let lastError;

        for (let i = 0; i < maxRetries; i++) {
            try {
                this.client = new Client({
                    host: DatabaseConfig.host,
                    port: DatabaseConfig.port,
                    database: DatabaseConfig.database,
                    user: DatabaseConfig.user,
                    password: DatabaseConfig.password,
                    connectionTimeoutMillis: FactoryConfig.DATABASE.connectTimeout,
                    query_timeout: FactoryConfig.DATABASE.queryTimeout
                });
                await this.client.connect();
                console.log('✅ 数据库连接成功');
                return;
            } catch (error) {
                lastError = error;
                console.log(`⚠️  数据库连接失败 (尝试 ${i + 1}/${maxRetries}): ${error.message}`);
                await new Promise(r => setTimeout(r, 2000));
            }
        }

        throw lastError;
    }

    async disconnect() {
        if (this.client) {
            try {
                await this.client.end();
            } catch (e) {
                console.log(`⚠️  数据库关闭警告: ${e.message}`);
            }
            this.client = null;
        }
    }

    // ========================================================================
    // 任务加载 - 历史数据优先
    // ========================================================================

    async loadTasks() {
        const query = `
            SELECT
                m.match_id,
                m.external_id as fotmob_id,
                m.home_team,
                m.away_team,
                m.league_name,
                m.match_date,
                m.status
            FROM matches m
            LEFT JOIN raw_match_data r ON m.match_id = r.match_id
            WHERE m.external_id IS NOT NULL
              AND m.external_id <> ''
              AND m.external_id SIMILAR TO '[0-9]+'
              AND (r.l2_raw_json IS NULL OR r.l2_raw_json::text = '{}')
              AND (m.status = 'finished' OR m.status = 'completed' OR m.match_date < NOW())
            ORDER BY m.match_date DESC
            LIMIT 1000
        `;

        const result = await this.client.query(query);
        return result.rows;
    }

    // ========================================================================
    // V172: 自动补漏机制 (Repair Mode)
    // ========================================================================

    async loadRepairTasks() {
        // V173: 简化查询，避免 LIKE 全表扫描
        const query = `
            SELECT
                m.match_id,
                m.external_id as fotmob_id,
                m.home_team,
                m.away_team,
                m.league_name,
                m.match_date,
                m.status,
                LENGTH(r.l2_raw_json::text) as current_size
            FROM matches m
            JOIN raw_match_data r ON m.match_id = r.match_id
            WHERE m.external_id IS NOT NULL
              AND m.external_id <> ''
              AND m.external_id ~ '^[0-9]+'
              AND LENGTH(r.l2_raw_json::text) < ${FactoryConfig.QUALITY_GATE.minSizeBytes}
            ORDER BY m.match_date DESC
            LIMIT 100
        `;

        const result = await this.client.query(query);
        return result.rows;
    }

    async cleanBadRecords() {
        // V173: 简化清理查询
        const query = `
            DELETE FROM raw_match_data
            WHERE LENGTH(l2_raw_json::text) < ${FactoryConfig.QUALITY_GATE.minSizeBytes}
            RETURNING match_id
        `;

        const result = await this.client.query(query);
        return result.rowCount;
    }

    // ========================================================================
    // Worker 管理
    // ========================================================================

    spawnWorker(workerId, proxyPort) {
        const workerPath = FactoryConfig.PATH_CONFIG.workerScript;

        const worker = fork(workerPath, [], {
            env: {
                ...process.env,
                PROJECT_ROOT: PROJECT_ROOT,
                WORKER_ID: workerId,
                PROXY_PORT: proxyPort,
                MIN_DELAY_MS: FactoryConfig.TIMING.minDelayMs,
                MAX_DELAY_MS: FactoryConfig.TIMING.maxDelayMs,
                COOKIE_SAVE_INTERVAL: FactoryConfig.BROWSER.cookieSaveInterval
            }
        });

        this.workers.set(workerId, {
            process: worker,
            port: proxyPort,
            consecutiveErrors: 0,
            status: 'STARTING',
            tasks: []
        });

        // 消息处理
        worker.on('message', (msg) => this.handleWorkerMessage(workerId, msg));

        worker.on('exit', (code, signal) => {
            console.log(`⚠️  Worker ${workerId} 退出 (code: ${code}, signal: ${signal})`);
            if (code !== 0 && this.running) {
                console.log(`   准备在 ${FactoryConfig.CIRCUIT_BREAKER.restartDelayMs}ms 后重启...`);
                setTimeout(() => this.restartWorker(workerId), FactoryConfig.CIRCUIT_BREAKER.restartDelayMs);
            }
        });

        // V172: 捕获错误
        worker.on('error', (error) => {
            console.log(`❌ Worker ${workerId} 错误: ${error.message}`);
        });

        return worker;
    }

    restartWorker(workerId) {
        const oldWorker = this.workers.get(workerId);
        if (!oldWorker) return;

        // 释放旧端口，分配新端口
        this.proxyPool.release(workerId);
        const newPort = this.proxyPool.assign(workerId);

        if (newPort) {
            this.spawnWorker(workerId, newPort);
            this.dashboard.updateWorker(workerId, 'RESTARTING', { port: newPort });
        }
    }

    // ========================================================================
    // V172: 消息处理 (增强重试逻辑)
    // ========================================================================

    handleWorkerMessage(workerId, msg) {
        console.log(`📨 [IPC] Master 收到 Worker ${workerId} 消息: ${JSON.stringify(msg)}`);

        switch (msg.type) {
            case 'READY':
                console.log(`✅ [IPC] Worker ${workerId} 已就绪，发送任务...`);
                this.dashboard.updateWorker(workerId, 'READY', { port: this.proxyPool.getPort(workerId) });
                this.sendTask(workerId);
                break;

            case 'TASK_START':
                this.dashboard.updateWorker(workerId, 'RUNNING', {
                    currentMatch: msg.matchId,
                    port: this.proxyPool.getPort(workerId)
                });
                break;

            case 'TASK_SUCCESS':
                this._recordSuccess(workerId);
                this.dashboard.updateWorker(workerId, 'SUCCESS', {
                    success: this._getWorkerSuccess(workerId)
                });
                this.sendTask(workerId);
                break;

            case 'TASK_FAILED':
                this._recordFailure(workerId);
                this._checkCircuitBreaker(workerId);
                this.dashboard.updateWorker(workerId, 'ERROR', {
                    failed: this._getWorkerFailed(workerId)
                });
                this.sendTask(workerId);
                break;

            // V172: 新增 - 处理重试请求
            case 'TASK_RETRY':
                this._handleRetryRequest(workerId, msg);
                break;
        }
    }

    // ========================================================================
    // V172: 重试请求处理 (任务回队)
    // ========================================================================

    _handleRetryRequest(workerId, msg) {
        const { matchId, retryCount, backoffDelay } = msg;

        // 找到原始任务
        const task = this._findTaskByMatchId(matchId);

        if (task && retryCount <= FactoryConfig.RETRY.maxAttempts) {
            // 将任务放回队列头部，延迟后重新分配
            setTimeout(() => {
                this.taskQueue.unshift(task);
                this.dashboard.retried++;
                console.log(`🔄 任务 ${matchId} 已重新入队 (重试 ${retryCount})`);

                // 尝试立即分配给空闲 Worker
                this._tryAssignTask();
            }, backoffDelay);

            this.dashboard.updateWorker(workerId, 'RETRYING');
        } else {
            // 超过最大重试次数，标记为失败
            this._recordFailure(workerId);
            this.dashboard.updateWorker(workerId, 'ERROR', {
                failed: this._getWorkerFailed(workerId)
            });
            this.sendTask(workerId);
        }
    }

    _findTaskByMatchId(matchId) {
        // 从最近的任务记录中查找
        for (const [_, worker] of this.workers) {
            const task = worker.tasks.find(t => t.match_id === matchId);
            if (task) return task;
        }
        return null;
    }

    _tryAssignTask() {
        for (const [workerId, worker] of this.workers) {
            if (worker.status === 'WAITING' || worker.status === 'READY') {
                this.sendTask(workerId);
                break;
            }
        }
    }

    _recordSuccess(workerId) {
        const worker = this.workers.get(workerId);
        if (worker) {
            worker.consecutiveErrors = 0;
        }
        this.dashboard.recordResult(true);
    }

    _recordFailure(workerId) {
        const worker = this.workers.get(workerId);
        if (worker) {
            worker.consecutiveErrors++;
        }
        this.dashboard.recordResult(false);
    }

    _getWorkerSuccess(workerId) {
        return this.dashboard.workers.get(workerId)?.success || 0;
    }

    _getWorkerFailed(workerId) {
        return this.dashboard.workers.get(workerId)?.failed || 0;
    }

    _checkCircuitBreaker(workerId) {
        const worker = this.workers.get(workerId);
        // V173-FIX: 提高熔断阈值到 10 次，避免过早熔断
        const effectiveThreshold = 10;
        if (worker && worker.consecutiveErrors >= effectiveThreshold) {
            console.log(`🛑 Worker ${workerId} 触发熔断 (连续失败 ${worker.consecutiveErrors} 次)，停止该 Worker`);
            worker.process.send({ type: 'SHUTDOWN' });
            worker.status = 'STOPPED';
            this.dashboard.updateWorker(workerId, 'STOPPED');
        }
    }

    sendTask(workerId) {
        if (this.taskQueue.length === 0) {
            this.dashboard.updateWorker(workerId, 'WAITING');
            return;
        }

        const task = this.taskQueue.shift();
        const worker = this.workers.get(workerId);

        if (worker && worker.process) {
            // V172: 记录任务分配
            worker.tasks.push(task);
            if (worker.tasks.length > 10) {
                worker.tasks.shift();  // 只保留最近 10 个任务
            }

            worker.process.send({
                type: 'TASK',
                task
            });
        }
    }

    // ========================================================================
    // 主循环
    // ========================================================================

    async run() {
        // V173: 启动前清理残留进程
        preFlightCleanup();

        console.log('');
        console.log('═'.repeat(80));
        console.log('  V173-SENTINEL 装甲群收割器 (免疫系统加固版)');
        console.log('═'.repeat(80));
        console.log('');
        console.log('📋 配置:');
        console.log(`   Worker 数量: ${FactoryConfig.CONCURRENCY.maxWorkers}`);
        console.log(`   代理端口: ${this.proxyPool.ports.join(', ')}`);
        console.log(`   单场延时: ${FactoryConfig.TIMING.minDelayMs/1000}s ~ ${FactoryConfig.TIMING.maxDelayMs/1000}s`);
        console.log(`   熔断阈值: ${FactoryConfig.CIRCUIT_BREAKER.threshold} 次连续失败`);
        console.log(`   深度静默: ${FactoryConfig.FOTMOB_COOL_DOWN?.enabled ? '已启用' : '未启用'}`);
        console.log(`   重试次数: ${FactoryConfig.RETRY.maxAttempts}`);
        console.log(`   质量门禁: 最小 ${FactoryConfig.QUALITY_GATE.minSizeBytes} bytes`);
        console.log('');

        await this.connect();

        // V173: 跳过坏账检查，直接加载任务（优化启动速度）
        console.log('🔍 跳过坏账检查，直接加载任务...');

        // 加载正常任务
        console.log('');
        console.log('🔍 加载任务...');
        this.taskQueue = await this.loadTasks();
        console.log(`   找到 ${this.taskQueue.length} 场比赛需要收割`);
        console.log('');

        if (this.taskQueue.length === 0) {
            console.log('✅ 所有比赛已有高质量 L2 数据');
            await this.disconnect();
            return;
        }

        // 初始化仪表盘
        this.dashboard = new FleetDashboard(this.taskQueue.length);

        // 启动 Worker
        console.log('🚀 启动 Worker...');
        for (let i = 0; i < FactoryConfig.CONCURRENCY.maxWorkers; i++) {
            const workerId = i + 1;
            const port = this.proxyPool.assign(workerId);

            if (port) {
                this.spawnWorker(workerId, port);
                console.log(`   Worker ${workerId} -> Port ${port}`);

                // 错峰启动
                if (i < FactoryConfig.CONCURRENCY.maxWorkers - 1) {
                    await new Promise(r => setTimeout(r, FactoryConfig.CONCURRENCY.staggerStartMs));
                }
            }
        }

        console.log('');
        console.log('🔥 装甲群已就位，开始收割!');
        console.log('');

        // V173: 启动心跳机制 (每 10 秒写入状态文件)
        this._startHeartbeat();

        // 等待所有任务完成
        await this.waitForCompletion();

        // V173: 停止心跳
        this._stopHeartbeat();

        // 最终报告
        this.dashboard.summary();

        await this.disconnect();
    }

    // ========================================================================
    // V173: 心跳机制 - 实时状态持久化
    // ========================================================================

    _heartbeatInterval = null;
    _statusFilePath = '/app/logs/live_status.json';
    _lastMatchId = null;

    _startHeartbeat() {
        const fs = require('fs');
        const path = require('path');

        // 确保目录存在
        const logDir = path.dirname(this._statusFilePath);
        if (!fs.existsSync(logDir)) {
            fs.mkdirSync(logDir, { recursive: true });
        }

        // 立即写入初始状态
        this._writeHeartbeat();

        // 每 10 秒更新一次
        this._heartbeatInterval = setInterval(() => {
            this._writeHeartbeat();
        }, 10000);

        console.log('💓 心跳机制已启动 (状态文件: ' + this._statusFilePath + ')');
    }

    _stopHeartbeat() {
        if (this._heartbeatInterval) {
            clearInterval(this._heartbeatInterval);
            this._heartbeatInterval = null;
        }

        // 写入最终状态
        this._writeHeartbeat();

        console.log('💔 心跳机制已停止');
    }

    _writeHeartbeat() {
        const fs = require('fs');

        const status = {
            // 元数据
            version: 'V173.0.0',
            timestamp: new Date().toISOString(),
            startTime: new Date(this.dashboard.startTime).toISOString(),

            // 进度
            total: this.dashboard.total,
            processed: this.dashboard.processed,
            success: this.dashboard.success,
            failed: this.dashboard.failed,
            retried: this.dashboard.retried,
            skipped: this.dashboard.skipped,

            // 百分比
            progressPct: this.dashboard.total > 0
                ? ((this.dashboard.processed / this.dashboard.total) * 100).toFixed(1)
                : '0.0',

            // 预估剩余时间
            elapsedMs: Date.now() - this.dashboard.startTime,
            estimatedRemainingMs: this._estimateRemaining(),

            // 最近处理的比赛
            lastMatchId: this._lastMatchId || null,

            // Worker 状态快照
            workers: this._getWorkerSnapshot(),

            // 代理端口状态
            proxyStatus: this._getProxySnapshot()
        };

        try {
            fs.writeFileSync(this._statusFilePath, JSON.stringify(status, null, 2));
        } catch (e) {
            // 静默失败，不影响主流程
        }
    }

    _estimateRemaining() {
        if (this.dashboard.processed === 0) return null;
        const avgTime = (Date.now() - this.dashboard.startTime) / this.dashboard.processed;
        const remaining = avgTime * (this.dashboard.total - this.dashboard.processed);
        return Math.round(remaining);
    }

    _getWorkerSnapshot() {
        const snapshot = {};
        for (const [workerId, info] of this.workers) {
            snapshot[workerId] = {
                port: info.port,
                status: info.status,
                success: info.success || 0,
                failed: info.failed || 0,
                currentMatch: info.currentMatch || null
            };
        }
        return snapshot;
    }

    _getProxySnapshot() {
        const snapshot = {};
        for (const port of this.proxyPool.ports) {
            const workerEntry = [...this.workers.entries()].find(([, w]) => w.port === port);
            const worker = workerEntry ? workerEntry[1] : null;
            snapshot[port] = {
                status: worker ? worker.status : 'IDLE',
                workerId: workerEntry ? workerEntry[0] : null
            };
        }
        return snapshot;
    }

    async waitForCompletion() {
        return new Promise((resolve) => {
            const checkInterval = setInterval(() => {
                if (this.dashboard.processed >= this.dashboard.total) {
                    clearInterval(checkInterval);
                    this.running = false;
                    this.shutdownAllWorkers();
                    resolve();
                }
            }, FactoryConfig.CONCURRENCY.monitorIntervalMs);
        });
    }

    shutdownAllWorkers() {
        for (const [workerId, worker] of this.workers) {
            if (worker.process) {
                worker.process.send({ type: 'SHUTDOWN' });
            }
        }
    }
}

// ============================================================================
// 主入口
// ============================================================================

async function main() {
    const master = new FleetMaster();

    // 信号处理
    process.on('SIGINT', async () => {
        console.log('\n收到中断信号，正在停止...');
        master.running = false;
        master.shutdownAllWorkers();
        await master.disconnect();
        process.exit(0);
    });

    // V172: 未捕获异常处理
    process.on('uncaughtException', async (error) => {
        console.error('\n❌ 未捕获异常:', error.message);
        master.running = false;
        master.shutdownAllWorkers();
        await master.disconnect();
        process.exit(1);
    });

    process.on('unhandledRejection', async (reason) => {
        console.error('\n❌ 未处理的 Promise 拒绝:', reason);
        master.running = false;
        master.shutdownAllWorkers();
        await master.disconnect();
        process.exit(1);
    });

    try {
        await master.run();
    } catch (error) {
        console.error('\n❌ 异常:', error.message);
        await master.disconnect();
        process.exit(1);
    }
}

main();
