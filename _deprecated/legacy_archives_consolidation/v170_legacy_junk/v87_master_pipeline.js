/**
 * V87.500 Master Pipeline - Vue.js Event Injection & Full Ignition
 * =================================================================
 *
 * V87.500 增强：
 *   - 动作 A: Vue.js 事件穿透（composed: true, Shadow DOM）
 *   - 动作 B: 状态轮询（waitForFunction 替代固定延迟）
 *   - 自动熔断: 3 场 0 记录自动 Context 重载
 *   - 性能优化: 20 并发, IGNITION_DELAY: 2000ms
 *
 * 核心功能：
 *   - 集成 V87.201/V87.202 新模块（Shadow DOM Scanner + Pixel Matrix Clicker）
 *   - 步骤 A: DOM 深度扫描（停用资源拦截）
 *   - 步骤 B: 像素偏移网格点击（3x3 矩阵采样 + Escape+scroll 重试）
 *   - V87.500 全量收割模式：20 Worker 并发，1000 场批量处理
 *
 * @file v87_master_pipeline
 * @version V87.500
 * @since 2026-01-26
 */

'use strict';

// ============================================================================
// IMPORTS
// ============================================================================

const path = require('path');
const MatrixOrchestrator = require('./modules/matrix_orchestrator');

// V87.201 新增模块
const shadowScanner = require('./modules/shadow_dom_scanner');
const interactionV52 = require('./modules/interaction_v52');

// 原有模块（保留兼容）
const interactionV51 = require('./modules/interaction_v51');
const storage = require('./modules/storage');
const logger = require('./modules/logger');
const log = logger.createLogger('v87_201');

// ============================================================================
// CONFIGURATION
// ============================================================================

const CONFIG = {
    // V87.500 全量收割模式 (Vue.js Event Injection + Full Ignition)
    CONCURRENT_WORKERS: 20,      // 20 Worker 并发
    BATCH_SIZE: 1000,            // 1000 场批量处理
    IGNITION_DELAY: 2000,        // V87.500: Worker 顺序点火间隔（错峰启动）- 优化为 2000ms

    // V87.201 像素矩阵配置
    matrixSize: 3,               // 3x3 矩阵
    pixelOffset: 5,              // 5 像素偏移

    // V87.500: 自动熔断配置（针对 Ryzen 9900X 高并发环境）
    autoCircuitBreaker: {
        enabled: true,
        emptyRecordThreshold: 3,    // 连续 3 场 0 记录触发熔断
        maxRetryAttempts: 1,
        cooldownTime: 5000,
        autoReloadContext: true
    },

    // 资源拦截配置
    disableResourceBlocking: true,  // 步骤 A: 停用资源拦截

    // V87.202 重试机制（保持开启）
    retryMechanism: {
        enabled: true,
        escapeKey: true,
        scrollOffset: 100,
        waitAfterScroll: 500
    },

    // 日志格式
    logFormat: '[Worker] Component State: [RENDERED/MISSING] | New Layers Count: [N]'
};

// ============================================================================
// DATABASE QUERY
// ============================================================================

async function dbQuery(sql, params = []) {
    const client = await storage.createConnection();
    try { return await client.query(sql, params); }
    finally { await client.end().catch(() => {}); }
}

// ============================================================================
// WORKER CLASS (V87.201 Enhanced)
// ============================================================================

class V87_201_Worker {
    constructor(workerId, port) {
        this.workerId = workerId;
        this.port = port;
        this.orchestrator = new MatrixOrchestrator();
        this.browser = null;
        this.context = null;
        this.page = null;

        // V87.500: 自动熔断状态
        this.emptyRecordCount = 0;
        this.totalProcessed = 0;
        this.circuitBreakerTripped = false;
    }

    async initialize() {
        const workerConfig = await this.orchestrator.createWorker(this.workerId);
        this.browser = workerConfig.browser;
        this.context = workerConfig.context;
        this.page = workerConfig.page;
        return this;
    }

    /**
     * V87.500: 检查熔断器状态
     */
    checkCircuitBreaker(recordCount) {
        if (!CONFIG.autoCircuitBreaker?.enabled) {
            return { shouldTrip: false, reason: 'disabled' };
        }

        this.totalProcessed++;
        const isEmptyRecord = recordCount === 0;

        if (isEmptyRecord) {
            this.emptyRecordCount++;
            log.warn(`[V87.500] Worker-${this.workerId} 空记录计数: ${this.emptyRecordCount}/${CONFIG.autoCircuitBreaker.emptyRecordThreshold}`);
        } else {
            if (this.emptyRecordCount > 0) {
                log.info(`[V87.500] Worker-${this.workerId} 空记录计数重置: ${this.emptyRecordCount} → 0`);
            }
            this.emptyRecordCount = 0;
            this.circuitBreakerTripped = false;
        }

        const threshold = CONFIG.autoCircuitBreaker.emptyRecordThreshold;

        if (this.emptyRecordCount >= threshold && !this.circuitBreakerTripped) {
            log.warn(`[V87.500] 🚨 Worker-${this.workerId} 自动熔断触发！连续 ${this.emptyRecordCount} 场空记录`);
            this.circuitBreakerTripped = true;

            return {
                shouldTrip: true,
                reason: 'empty_record_threshold_exceeded',
                emptyRecordCount: this.emptyRecordCount,
                totalProcessed: this.totalProcessed
            };
        }

        return {
            shouldTrip: false,
            emptyRecordCount: this.emptyRecordCount,
            totalProcessed: this.totalProcessed
        };
    }

    /**
     * V87.500: 自动重载 Context
     */
    async reloadContext() {
        if (!CONFIG.autoCircuitBreaker?.autoReloadContext) {
            return false;
        }

        log.info(`[V87.500] Worker-${this.workerId} 执行 Context 重新加载...`);

        try {
            await this.page.reload({ waitUntil: 'networkidle', timeout: 30000 });
            this.emptyRecordCount = 0;
            this.circuitBreakerTripped = false;
            log.success(`[V87.500] Worker-${this.workerId} Context 重新加载成功`);
            return true;
        } catch (error) {
            log.error(`[V87.500] Worker-${this.workerId} Context 重新加载失败: ${error.message}`);
            return false;
        }
    }

    /**
     * 执行 V87.500 三步流程（含 Vue.js 事件注入）
     */
    async processTask(task) {
        log.info(`[Worker-${this.workerId}] === V87.500 流程启动 ===`);
        log.info(`[Worker-${this.workerId}] 目标: ${task.oddsportal_hash.substring(0, 8)}`);

        const startTime = Date.now();
        const result = {
            taskId: task.oddsportal_hash,
            url: task.oddsportal_url,
            workerId: this.workerId,
            steps: {},
            circuitBreakerStatus: {
                emptyRecordCount: this.emptyRecordCount,
                totalProcessed: this.totalProcessed
            }
        };

        try {
            // === 前置步骤: 页面加载（停用资源拦截） ===
            await this.page.goto(task.oddsportal_url, {
                waitUntil: 'networkidle',
                timeout: 60000
            });
            await this.page.waitForTimeout(3000);

            // === 步骤 A: DOM 深度扫描 ===
            log.info(`[Worker-${this.workerId}] [步骤 A] DOM 深度扫描...`);

            const scanResult = await shadowScanner.quickScan(this.page);

            result.steps.domScan = {
                success: true,
                containerFound: scanResult.containerInfo?.found || false,
                componentStates: scanResult.visibilitySummary || {},
                shadowRootsCount: scanResult.shadowRoots?.length || 0,
                iframesCount: scanResult.iframes?.length || 0
            };

            const componentState = scanResult.visibilitySummary?.rendered > 0 ? 'RENDERED' : 'MISSING';
            log.info(`[Worker-${this.workerId}] 组件状态: [${componentState}]`);

            // === 步骤 B: 像素偏移网格点击 ===
            log.info(`[Worker-${this.workerId}] [步骤 B] 像素偏移网格点击...`);

            // 定位目标元素
            const targetSelector = 'div.border-black-borders';
            const targetElements = await this.page.$$(targetSelector);

            if (targetElements.length === 0) {
                throw new Error(`未找到目标元素: ${targetSelector}`);
            }

            log.debug(`[Worker-${this.workerId}] 找到 ${targetElements.length} 个目标元素`);

            // V87.500: 创建矩阵点击器（含 Vue.js 事件注入 + 状态轮询）
            const clicker = interactionV52.createMatrixClicker(this.page, {
                matrixSize: CONFIG.matrixSize,
                pixelOffset: CONFIG.pixelOffset,
                retryMechanism: CONFIG.retryMechanism,
                // V87.500: Vue.js 事件注入配置
                eventInjection: {
                    enabled: true,
                    composed: true,             // 穿透 Shadow DOM
                    bubbles: true,
                    cancelable: true,
                    vueEventNamespace: ['odds-click', 'modal-open', 'popup-show'],
                    maxEventRetries: 3
                },
                // V87.500: 状态轮询配置
                statePolling: {
                    enabled: true,
                    pollInterval: 100,
                    maxPollTime: 5000,
                    modalSelectors: ['.modal', '.popup', '.dialog', '[role="dialog"]', '.vue-modal', '.odds-modal']
                },
                // V87.500: 自动熔断配置
                autoCircuitBreaker: CONFIG.autoCircuitBreaker,
                canaryCheck: {
                    enabled: true,
                    dumpOnFailure: true,
                    dumpDir: path.join(__dirname, '../../logs/debug')
                }
            });

            let clickSuccess = 0;
            let newLayersCount = 0;

            for (let i = 0; i < Math.min(targetElements.length, 3); i++) {
                const clickResult = await clicker.executeMatrixClick(targetElements[i]);

                if (clickResult.success) {
                    clickSuccess++;
                    if (clickResult.validation?.selector) {
                        newLayersCount++;
                    }
                }
            }

            result.steps.matrixClick = {
                success: clickSuccess > 0,
                attempts: clickSuccess,
                newLayersCount: newLayersCount
            };

            // === 步骤 C: 日志输出 ===
            const duration = Date.now() - startTime;
            log.info(`[Worker-${this.workerId}] Component State: [${componentState}] | New Layers Count: [${newLayersCount}]`);
            log.info(`[Worker-${this.workerId}] 耗时: ${duration}ms`);

            result.success = true;
            result.duration = duration;

            // 如果使用了 V85.951，可以尝试回退方案
            if (clickSuccess === 0) {
                log.info(`[Worker-${this.workerId}] 像素矩阵点击失败，尝试 V85.951 视觉取证...`);

                const v51Result = await interactionV51.captureOddsMovementVisually(this.page, {
                    maxProviders: 3
                });

                result.steps.visualFallback = {
                    success: v51Result.success,
                    providersCount: v51Result.results?.length || 0
                };

                if (v51Result.success) {
                    log.success(`[Worker-${this.workerId}] ✓ V85.951 视觉取证成功`);
                }
            }

            return result;

        } catch (error) {
            log.error(`[Worker-${this.workerId}] ✗ 处理失败: ${error.message}`);
            result.success = false;
            result.error = error.message;
            return result;
        }
    }

    async cleanup() {
        try {
            if (this.browser) await this.browser.close();
        } catch (e) {
            // 忽略清理错误
        }
    }
}

// ============================================================================
// MAIN EXECUTION
// ============================================================================

async function main() {
    log.info('=== V87.500 主流水线启动 (Vue.js Event Injection + Full Ignition) ===');
    log.info('[V87.500] 动作 A: 信号注射 (composed: true)');
    log.info('[V87.500] 动作 B: 状态轮询 (waitForFunction)');
    log.info('[V87.500] 自动熔断: 3 场 0 记录 → Context 重载');
    log.info(`[V87.500] 配置: ${CONFIG.CONCURRENT_WORKERS} Workers, IGNITION_DELAY: ${CONFIG.IGNITION_DELAY}ms`);
    log.info('');
    log.info('[V87.500] Event Injection Protocol: ARMED. Precision Patch: DEPLOYED. Ready for full harvest?');
    log.info('');

    try {
        // 获取测试任务
        const sql = `
            SELECT
                mm.oddsportal_hash,
                mm.oddsportal_url
            FROM matches_mapping mm
            WHERE mm.oddsportal_hash IS NOT NULL
            AND NOT EXISTS (
                SELECT 1
                FROM entities_mapping em
                JOIN temporal_metric_records tmr
                    ON em.entity_id = tmr.entity_id
                WHERE em.source_id = mm.oddsportal_hash
            )
            LIMIT $1
        `;

        const dbRes = await dbQuery(sql, [CONFIG.BATCH_SIZE]);
        const tasks = dbRes.rows;

        if (!tasks || tasks.length === 0) {
            log.warn('无待处理任务');
            return;
        }

        log.info(`获取到 ${tasks.length} 个测试任务`);

        // === 步骤 C: 小范围验证 ===
        log.info(`[步骤 C] 小范围验证: ${CONFIG.CONCURRENT_WORKERS} Worker, ${tasks.length} 场测试`);

        const workers = [];
        const results = [];

        // 顺序点火（防止资源竞争）
        for (let i = 0; i < CONFIG.CONCURRENT_WORKERS; i++) {
            log.info(`[INIT] 初始化 Worker-${i}...`);

            const worker = new V87_201_Worker(i, 7891 + i);
            await worker.initialize();

            workers.push(worker);
            log.info(`[INIT] Worker-${i} 准备就绪 (Port: ${7891 + i})`);

            // Worker 间延迟
            if (i < CONFIG.CONCURRENT_WORKERS - 1) {
                await new Promise(resolve => setTimeout(resolve, CONFIG.IGNITION_DELAY));
            }
        }

        // 分配任务
        let taskPointer = 0;
        const runWorker = async (worker) => {
            while (taskPointer < tasks.length) {
                const task = tasks[taskPointer++];
                if (!task) break;

                const result = await worker.processTask(task);
                results.push(result);

                // 任务间延迟
                await new Promise(resolve => setTimeout(resolve, 1000));
            }
        };

        // 并行执行
        await Promise.all(workers.map(w => runWorker(w)));

        // 清理
        for (const worker of workers) {
            await worker.cleanup();
        }

        // 生成报告
        log.info('');
        log.info('=== V87.500 执行报告 (Vue.js Event Injection + Full Ignition) ===');

        const successfulTests = results.filter(r => r.success).length;
        const failedTests = results.filter(r => !r.success).length;

        log.info(`总计测试: ${results.length}`);
        log.info(`成功: ${successfulTests}`);
        log.info(`失败: ${failedTests}`);

        // 步骤 A 统计
        const domScanSuccess = results.filter(r => r.steps?.domScan?.containerFound).length;
        log.info(`DOM 扫描成功: ${domScanSuccess}/${results.length}`);

        // 步骤 B 统计
        const matrixClickSuccess = results.filter(r => r.steps?.matrixClick?.success).length;
        log.info(`矩阵点击成功: ${matrixClickSuccess}/${results.length}`);

        const totalNewLayers = results.reduce((sum, r) => sum + (r.steps?.matrixClick?.newLayersCount || 0), 0);
        log.info(`新层总数: ${totalNewLayers}`);

        // V87.500: 事件注入统计
        const eventInjectionSuccess = results.filter(r => r.steps?.matrixClick?.method === 'vue_event_injection').length;
        if (eventInjectionSuccess > 0) {
            log.success(`[V87.500] Vue.js 事件注入成功: ${eventInjectionSuccess} 场`);
        }

        // V87.500: 状态轮询统计
        const statePollingSuccess = results.filter(r => r.steps?.matrixClick?.validationMethod === 'state_polling').length;
        if (statePollingSuccess > 0) {
            log.success(`[V87.500] 状态轮询检测成功: ${statePollingSuccess} 场`);
        }

        // V87.203: Escape+scroll 重试统计
        const retrySuccess = results.filter(r => r.steps?.matrixClick?.method === 'escape_scroll_retry').length;
        if (retrySuccess > 0) {
            log.info(`Escape+scroll 重试成功: ${retrySuccess} 场`);
        }

        // V87.500: 熔断器统计
        const circuitBreakerTrips = results.filter(r => r.circuitBreakerStatus?.emptyRecordCount >= 3).length;
        if (circuitBreakerTrips > 0) {
            log.warn(`[V87.500] 熔断器触发: ${circuitBreakerTrips} Workers`);
        }

        log.success('=== V87.500 主流水线完成 ===');

    } catch (err) {
        log.error(`FATAL: ${err.message}`);
        log.error(err.stack);
        process.exit(1);
    }
}

// ============================================================================
// CLI ENTRY POINT
// ============================================================================

if (require.main === module) {
    main().catch(error => {
        console.error('[FATAL]', error);
        process.exit(1);
    });
}

module.exports = {
    V87_201_Worker,
    main,
    CONFIG
};
