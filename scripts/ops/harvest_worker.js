/**
 * V174-REFRESH Worker 进程 (模块化重构版)
 * ==========================================
 *
 * 薄层入口，仅负责:
 * 1. 依赖注入和模块组装
 * 2. 信号处理
 * 3. 消息路由
 *
 * 核心逻辑已移至 src/scripts/harvest_worker_entry.js
 *
 * @module scripts/ops/harvest_worker
 * @version V174.0.0
 */

'use strict';

const path = require('path');

// 导入模块化入口
const PROJECT_ROOT = process.env.PROJECT_ROOT || '/app';
const { HarvestWorkerEntry, WORKER_ID, log } = require(path.join(PROJECT_ROOT, 'src/scripts/harvest_worker_entry'));
const { preFlightCleanup, forceKillBrowser } = require(path.join(PROJECT_ROOT, 'src/core/process'));

// ============================================================================
// Worker 进程包装器
// ============================================================================

class WorkerProcess {
    constructor() {
        this.entry = new HarvestWorkerEntry();
        this.running = true;
    }

    async run() {
        // 预清理 - 杀死僵尸进程
        preFlightCleanup(WORKER_ID);

        // 初始化
        await this.entry.init();

        // 信号处理
        this.setupSignalHandlers();

        // 消息监听
        this.setupMessageHandler();

        // 异常处理
        this.setupErrorHandlers();
    }

    setupSignalHandlers() {
        const gracefulShutdown = async (signal) => {
            log.info(`收到 ${signal} 信号，正在清理资源...`);
            this.running = false;
            await this.entry.close();
            forceKillBrowser(WORKER_ID);
            process.exit(0);
        };

        process.on('SIGINT', () => gracefulShutdown('SIGINT'));
        process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
    }

    setupMessageHandler() {
        process.on('message', async (msg) => {
            switch (msg.type) {
                case 'TASK':
                    await this.entry.harvest(msg.task);
                    await this.entry.randomDelay();
                    break;

                case 'TASK_RETRY_FROM_MASTER':
                    await this.entry.harvest(msg.task);
                    await this.entry.randomDelay();
                    break;

                case 'SHUTDOWN':
                    log.info('收到关闭信号');
                    this.running = false;
                    await this.entry.close();
                    forceKillBrowser(WORKER_ID);
                    process.exit(0);
                    break;
            }
        });
    }

    setupErrorHandlers() {
        process.on('uncaughtException', async (error) => {
            log.error(`未捕获异常: ${error.message}`);
            await this.entry.close();
            forceKillBrowser(WORKER_ID);
            process.exit(1);
        });

        process.on('unhandledRejection', async (reason) => {
            log.error(`未处理的 Promise 拒绝: ${reason}`);
            await this.entry.close();
            forceKillBrowser(WORKER_ID);
            process.exit(1);
        });
    }
}

// ============================================================================
// 启动
// ============================================================================

const worker = new WorkerProcess();
worker.run().catch(error => {
    console.error(`[Worker ${WORKER_ID}] 启动失败:`, error);
    process.exit(1);
});
