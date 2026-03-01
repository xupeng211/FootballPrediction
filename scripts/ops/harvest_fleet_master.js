/**
 * V174-REFRESH 装甲群模式收割器 (模块化重构版)
 * ==============================================
 *
 * 薄层入口，仅负责:
 * 1. 依赖注入和模块组装
 * 2. 信号处理
 * 3. Worker 生命周期管理
 *
 * 核心逻辑已移至模块:
 * - TaskPool: 任务调度
 * - ProxyRegistry: 代理管理
 * - Dashboard: UI 渲染
 * - MasterGate: IPC 消息处理
 *
 * @module scripts/ops/harvest_fleet_master
 * @version V174.0.0
 */

'use strict';

const { fork } = require('child_process');
const path = require('path');
const { Client } = require('pg');

// 配置加载
const PROJECT_ROOT = process.env.PROJECT_ROOT || '/app';
const FactoryConfig = require(path.join(PROJECT_ROOT, 'config/factory_config'));
const { DatabaseConfig } = require(path.join(PROJECT_ROOT, 'src/infrastructure/database/PostgresClient'));

// V174: 模块导入
const { ZombieKiller, preFlightCleanup, getZombieStats } = require(path.join(PROJECT_ROOT, 'src/core/process'));
const { TaskPool } = require(path.join(PROJECT_ROOT, 'src/core/scheduler'));
const { ProxyRegistry } = require(path.join(PROJECT_ROOT, 'src/core/network'));
const { Dashboard } = require(path.join(PROJECT_ROOT, 'src/core/ui'));
const { MasterGate, MessageTypes } = require(path.join(PROJECT_ROOT, 'src/core/ipc'));

// ============================================================================
// FleetMaster - 主控制器 (薄层)
// ============================================================================

class FleetMaster {
    constructor() {
        // 数据库
        this.client = null;

        // V174: 模块化组件
        this.taskPool = null;
        this.proxyRegistry = new ProxyRegistry({
            ports: FactoryConfig.PROXY_CONFIG.ports,
            host: '172.25.16.1'
        });
        this.dashboard = null;
        this.masterGate = new MasterGate({
            circuitBreakerThreshold: 5
        });

        // Worker 管理
        this.workers = new Map();
        this.running = true;

        // 心跳
        this._heartbeatInterval = null;
        this._statusFilePath = '/app/logs/live_status.json';
        this._readyResolvers = new Map();
        this._restartCount = new Map();

        // V175: 僵尸扫描器
        this._zombieKiller = new ZombieKiller({ silent: false });
        this._zombieScanInterval = null;
    }

    // ========================================================================
    // 初始化
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

                // 初始化任务池
                this.taskPool = new TaskPool(this.client, {
                    minSizeBytes: FactoryConfig.QUALITY_GATE.minSizeBytes,
                    maxRetries: FactoryConfig.RETRY.maxAttempts
                });

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
            } catch (e) { }
            this.client = null;
        }
    }

    // ========================================================================
    // IPC 消息处理器设置
    // ========================================================================

    _setupIpcHandlers() {
        // READY
        this.masterGate.on(MessageTypes.READY, (workerId) => {
            if (this._readyResolvers.has(workerId)) {
                this._readyResolvers.get(workerId)();
                this._readyResolvers.delete(workerId);
            }
            this.dashboard.updateWorker(workerId, 'READY', {
                port: this.proxyRegistry.getPort(workerId)
            });
            this._sendTask(workerId);
        });

        // TASK_START
        this.masterGate.on(MessageTypes.TASK_START, (workerId, msg) => {
            this.dashboard.updateWorker(workerId, 'RUNNING', {
                currentMatch: msg.matchId,
                port: this.proxyRegistry.getPort(workerId)
            });
        });

        // TASK_SUCCESS
        this.masterGate.on(MessageTypes.TASK_SUCCESS, (workerId) => {
            this._recordSuccess(workerId);
            this._sendTask(workerId);
        });

        // TASK_FAILED
        this.masterGate.on(MessageTypes.TASK_FAILED, (workerId) => {
            this._recordFailure(workerId);
            this._checkCircuitBreaker(workerId);
            this._sendTask(workerId);
        });

        // TASK_RETRY
        this.masterGate.on(MessageTypes.TASK_RETRY, (workerId, msg) => {
            this._handleRetry(workerId, msg);
        });

        // 熔断
        this.masterGate.on('circuitBreak', (workerId) => {
            this._recloneWorker(workerId);
        });
    }

    // ========================================================================
    // Worker 管理
    // ========================================================================

    spawnWorker(workerId, proxyPort) {
        const workerPath = FactoryConfig.PATH_CONFIG.workerScript;

        const worker = fork(workerPath, [], {
            env: {
                ...process.env,
                PROJECT_ROOT,
                WORKER_ID: workerId,
                PROXY_PORT: proxyPort,
                MIN_DELAY_MS: FactoryConfig.TIMING.minDelayMs,
                MAX_DELAY_MS: FactoryConfig.TIMING.maxDelayMs
            }
        });

        this.workers.set(workerId, {
            process: worker,
            port: proxyPort,
            status: 'STARTING',
            tasks: []
        });

        worker.on('message', (msg) => this.masterGate.handle(workerId, msg));

        worker.on('exit', (code, signal) => {
            console.log(`⚠️  Worker ${workerId} 退出 (code: ${code})`);
            if (code !== 0 && this.running) {
                setTimeout(() => this._recloneWorker(workerId),
                    FactoryConfig.CIRCUIT_BREAKER.restartDelayMs);
            }
        });

        return worker;
    }

    async _terminateWorker(workerId) {
        const worker = this.workers.get(workerId);
        if (!worker) return;

        try {
            if (worker.process?.connected) {
                worker.process.send({ type: 'SHUTDOWN' });
                await new Promise(r => setTimeout(r, 2000));
            }
            if (worker.process?.pid) {
                try { process.kill(worker.process.pid, 'SIGKILL'); } catch (e) { }
            }
        } catch (e) { }

        this.workers.delete(workerId);
    }

    async _recloneWorker(workerId) {
        const restarts = this._restartCount.get(workerId) || 0;
        if (restarts >= 3) {
            console.log(`🛑 Worker ${workerId} 达到最大重启次数`);
            return;
        }

        this._restartCount.set(workerId, restarts + 1);
        console.log(`🧬 重新克隆 Worker ${workerId}...`);

        await this._terminateWorker(workerId);
        this.proxyRegistry.release(workerId);

        const newPort = this.proxyRegistry.assign(workerId);
        if (!newPort) return;

        await new Promise(r => setTimeout(r, 5000));

        const readyPromise = new Promise((resolve) => {
            this._readyResolvers.set(workerId, resolve);
        });

        this.spawnWorker(workerId, newPort);

        try {
            await Promise.race([
                readyPromise,
                new Promise((_, reject) =>
                    setTimeout(() => reject(new Error('超时')), 30000))
            ]);
            this.dashboard.updateWorker(workerId, 'READY', { port: newPort });
        } catch (e) { }
    }

    // ========================================================================
    // 任务管理
    // ========================================================================

    _sendTask(workerId) {
        const task = this.taskPool.getNext();
        if (!task) {
            this.dashboard.updateWorker(workerId, 'WAITING');
            return;
        }

        const worker = this.workers.get(workerId);
        if (worker?.process) {
            worker.tasks.push(task);
            if (worker.tasks.length > 10) worker.tasks.shift();
            worker.process.send({ type: 'TASK', task });
        }
    }

    _handleRetry(workerId, msg) {
        const { matchId, retryCount, backoffDelay } = msg;
        const task = this._findTask(matchId);

        if (task && retryCount <= FactoryConfig.RETRY.maxAttempts) {
            setTimeout(() => {
                this.taskPool.requeue(task);
                this.dashboard.retried++;
                this._tryAssignTask();
            }, backoffDelay);
            this.dashboard.updateWorker(workerId, 'RETRYING');
        }
    }

    _findTask(matchId) {
        for (const [, worker] of this.workers) {
            const task = worker.tasks.find(t => t.match_id === matchId);
            if (task) return task;
        }
        return null;
    }

    _tryAssignTask() {
        for (const [workerId, worker] of this.workers) {
            if (worker.status === 'WAITING' || worker.status === 'READY') {
                this._sendTask(workerId);
                break;
            }
        }
    }

    _recordSuccess(workerId) {
        this.masterGate.resetErrors(workerId);
        const worker = this.workers.get(workerId);
        if (worker) worker.status = 'SUCCESS';
        this.dashboard.recordResult(true);
    }

    _recordFailure(workerId) {
        const worker = this.workers.get(workerId);
        if (worker) worker.status = 'ERROR';
        this.dashboard.recordResult(false);
    }

    _checkCircuitBreaker(workerId) {
        const state = this.masterGate.getWorkerState(workerId);
        if (state?.consecutiveErrors >= 5) {
            console.log(`🛑 Worker ${workerId} 触发熔断`);
            setImmediate(() => this._recloneWorker(workerId));
            const worker = this.workers.get(workerId);
            if (worker) worker.status = 'RECOVERING';
            this.dashboard.updateWorker(workerId, 'RECOVERING');
        }
    }

    // ========================================================================
    // 主循环
    // ========================================================================

    async run() {
        preFlightCleanup(0);

        console.log('');
        console.log('═'.repeat(80));
        console.log('  V174-REFRESH 装甲群收割器 (模块化重构版)');
        console.log('═'.repeat(80));
        console.log('');

        // 打印配置
        this._printConfig();

        await this.connect();

        // 加载任务
        console.log('🔍 加载任务...');
        const tasks = await this.taskPool.loadTasks();
        console.log(`   找到 ${tasks.length} 场比赛需要收割`);

        if (tasks.length === 0) {
            console.log('✅ 所有比赛已有高质量 L2 数据');
            await this.disconnect();
            return;
        }

        // 初始化仪表盘
        this.dashboard = new Dashboard({
            total: tasks.length,
            title: 'V174-REFRESH 装甲群收割器'
        });

        // 设置 IPC 处理器
        this._setupIpcHandlers();

        // 启动 Workers
        await this._startWorkers();

        // 启动心跳
        this._startHeartbeat();

        // V175: 启动僵尸扫描
        this._startZombieScan();

        // 等待完成
        await this._waitForCompletion();

        // V175: 停止僵尸扫描
        this._stopZombieScan();

        this._stopHeartbeat();
        this.dashboard.summary();
        await this.disconnect();
    }

    _printConfig() {
        console.log('📋 配置:');
        console.log(`   Worker 数量: ${FactoryConfig.CONCURRENCY.maxWorkers}`);
        this.proxyRegistry.printStatus();
        console.log(`   单场延时: ${FactoryConfig.TIMING.minDelayMs / 1000}s ~ ${FactoryConfig.TIMING.maxDelayMs / 1000}s`);
        console.log('');
    }

    async _startWorkers() {
        console.log('🚀 启动 Worker (V174 错峰模式)...');

        for (let i = 0; i < FactoryConfig.CONCURRENCY.maxWorkers; i++) {
            const workerId = i + 1;
            const port = this.proxyRegistry.assign(workerId);

            if (port) {
                const readyPromise = new Promise((resolve) => {
                    this._readyResolvers.set(workerId, resolve);
                });

                this.spawnWorker(workerId, port);
                console.log(`   Worker ${workerId} -> Port ${port}`);

                try {
                    await Promise.race([
                        readyPromise,
                        new Promise((_, reject) =>
                            setTimeout(() => reject(new Error('超时')), 30000))
                    ]);
                    console.log(`   ✅ Worker ${workerId} 已就绪`);
                } catch (e) {
                    console.log(`   ⚠️ Worker ${workerId} 就绪超时`);
                }

                if (i < FactoryConfig.CONCURRENCY.maxWorkers - 1) {
                    await new Promise(r => setTimeout(r, 10000));
                }
            }
        }

        console.log('');
        console.log('🔥 装甲群已就位，开始收割!');
    }

    async _waitForCompletion() {
        return new Promise((resolve) => {
            const check = setInterval(() => {
                if (this.dashboard.processed >= this.dashboard.total) {
                    clearInterval(check);
                    this.running = false;
                    this._shutdownAll();
                    resolve();
                }
            }, FactoryConfig.CONCURRENCY.monitorIntervalMs);
        });
    }

    _shutdownAll() {
        for (const [, worker] of this.workers) {
            if (worker.process) {
                worker.process.send({ type: 'SHUTDOWN' });
            }
        }
    }

    // ========================================================================
    // 心跳
    // ========================================================================

    _startHeartbeat() {
        const fs = require('fs');
        const logDir = path.dirname(this._statusFilePath);
        if (!fs.existsSync(logDir)) {
            fs.mkdirSync(logDir, { recursive: true });
        }

        this._writeHeartbeat();
        this._heartbeatInterval = setInterval(() => this._writeHeartbeat(), 10000);
    }

    _stopHeartbeat() {
        if (this._heartbeatInterval) {
            clearInterval(this._heartbeatInterval);
        }
        this._writeHeartbeat();
    }

    // ========================================================================
    // V175: 僵尸进程扫描
    // ========================================================================

    _startZombieScan() {
        // 每 30 秒扫描一次僵尸进程
        this._zombieScanInterval = setInterval(() => {
            const stats = getZombieStats();

            // 如果有 defunct 进程，尝试清理
            if (stats.defunct > 0) {
                console.log(`⚠️ [ZombieScanner] 检测到 ${stats.defunct} 个 defunct 进程`);
                this._zombieKiller.preFlightCleanup(0);
            }

            // 如果有超时进程，清理
            if (stats.stale > 0) {
                console.log(`⚠️ [ZombieScanner] 检测到 ${stats.stale} 个超时进程`);
                this._zombieKiller.preFlightCleanup(0);
            }

            // 如果僵尸进程超过 5 个，发出警告
            if (stats.defunct > 5) {
                console.log(`🚨 [ZombieScanner] 警告: defunct 进程过多 (${stats.defunct})，建议检查容器健康状态`);
            }
        }, 30000); // 30 秒扫描一次

        console.log('🛡️ [ZombieScanner] 已启动定期扫描 (30s)');
    }

    _stopZombieScan() {
        if (this._zombieScanInterval) {
            clearInterval(this._zombieScanInterval);
            this._zombieScanInterval = null;
        }
    }

    _writeHeartbeat() {
        const fs = require('fs');
        const status = {
            version: 'V175.0.0',
            timestamp: new Date().toISOString(),
            ...this.dashboard.getSnapshot(),
            taskPool: this.taskPool?.getStats(),
            proxyRegistry: this.proxyRegistry.getSnapshot(),
            // V175: 僵尸进程统计
            zombieStats: getZombieStats()
        };

        try {
            fs.writeFileSync(this._statusFilePath, JSON.stringify(status, null, 2));
        } catch (e) { }
    }
}

// ============================================================================
// 主入口
// ============================================================================

async function main() {
    const master = new FleetMaster();

    process.on('SIGINT', async () => {
        console.log('\n收到中断信号...');
        master.running = false;
        master._shutdownAll();
        await master.disconnect();
        process.exit(0);
    });

    process.on('uncaughtException', async (error) => {
        console.error('\n❌ 未捕获异常:', error.message);
        master.running = false;
        master._shutdownAll();
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
