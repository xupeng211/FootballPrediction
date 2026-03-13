/**
 * WorkerPool - V4.51 Worker 调度中心 (TITAN-INFRA-STRENGTHENING)
 * ================================================================
 *
 * 从 ProductionHarvester 剥离的 Worker 调度逻辑
 * 统一管理 Worker 的启动、清理、任务分配、并发控制
 *
 * V4.51 强化:
 * - 智能背压检测 (Smart Throttling)
 * - 异步操作计数器
 * - 动态流量整形
 * @module infrastructure/harvesters/workers/WorkerPool
 * @version V4.51.0
 */

'use strict';

const pLimit = require('p-limit');

/**
 * WorkerPool - Worker 调度中心
 *
 * 功能:
 * 1. Worker 注册/注销管理
 * 2. 任务分配与并发控制
 * 3. Worker 统计信息
 * 4. 智能背压检测 (V4.51)
 */
class WorkerPool {
    /**
     * @param {object} options - 配置选项
     * @param {number} [options.maxWorkers] - 最大 Worker 数量
     * @param {Function} [options.logger] - 日志函数
     * @param {number} [options.maxPendingOperations] - 最大挂起异步操作数 (默认: 36 = 12 workers * 3)
     * @param {number} [options.backpressurePollInterval] - 背压检测轮询间隔 (ms, 默认: 100)
     */
    constructor(options = {}) {
        this.maxWorkers = options.maxWorkers || 6;
        this.logger = options.logger || console;

        // V4.51: 智能背压配置
        // 高延迟环境下，每个 worker 可能同时处理多个异步操作
        // 阈值 = maxWorkers * 3 (页面导航 + API 请求 + DOM 操作)
        this.maxPendingOperations = options.maxPendingOperations || (this.maxWorkers * 3);
        this.backpressurePollInterval = options.backpressurePollInterval || 100;

        // 活跃 Worker 集合
        this.activeWorkers = new Set();

        // 任务队列
        this.taskQueue = [];

        // V4.51: 挂起的异步操作计数器
        this.pendingOperations = 0;

        // 统计信息
        this.stats = {
            totalTasks: 0,
            completedTasks: 0,
            failedTasks: 0,
            activeWorkers: 0,
            peakConcurrency: 0,
            backpressureDelays: 0  // V4.51: 背压延迟次数
        };
    }

    // ===================================================================
    // V4.51: 智能背压检测 (Smart Throttling)
    // ===================================================================

    /**
     * 增加挂起操作计数
     * @private
     */
    _incrementPending() {
        this.pendingOperations++;
    }

    /**
     * 减少挂起操作计数
     * @private
     */
    _decrementPending() {
        this.pendingOperations = Math.max(0, this.pendingOperations - 1);
    }

    /**
     * 检查是否需要背压
     * @returns {boolean}
     * @private
     */
    _needsBackpressure() {
        return this.pendingOperations >= this.maxPendingOperations;
    }

    /**
     * 等待背压解除
     * 微秒级轮询，直到 pendingOperations 降至阈值以下
     * @returns {Promise<void>}
     * @private
     */
    async _waitForBackpressureRelease() {
        let waitCycles = 0;
        const startTime = Date.now();

        while (this._needsBackpressure()) {
            waitCycles++;
            await this._delay(this.backpressurePollInterval);

            // 每 10 轮输出一次日志
            if (waitCycles % 10 === 0) {
                this.logger(`[WorkerPool] 背压等待中... 挂起操作: ${this.pendingOperations}/${this.maxPendingOperations}, 已等待: ${Date.now() - startTime}ms`);
            }

            // 安全阀：最多等待 30 秒
            if (Date.now() - startTime > 30000) {
                this.logger(`[WorkerPool] ⚠️ 背压等待超时，强制继续 (挂起操作: ${this.pendingOperations})`);
                break;
            }
        }

        if (waitCycles > 0) {
            this.stats.backpressureDelays++;
            this.logger(`[WorkerPool] 背压解除，延迟 ${Date.now() - startTime}ms (周期: ${waitCycles})`);
        }
    }

    // ========================================================================
    // Worker 生命周期管理
    // ========================================================================

    /**
     * 注册 Worker 为活跃状态
     * @param {number} workerId - Worker ID
     */
    register(workerId) {
        this.activeWorkers.add(workerId);
        this.stats.activeWorkers = this.activeWorkers.size;
        this.stats.peakConcurrency = Math.max(
            this.stats.peakConcurrency,
            this.activeWorkers.size
        );
    }

    /**
     * 注销 Worker 活跃状态
     * @param {number} workerId - Worker ID
     */
    unregister(workerId) {
        this.activeWorkers.delete(workerId);
        this.stats.activeWorkers = this.activeWorkers.size;
    }

    /**
     * 检查 Worker 是否活跃
     * @param {number} workerId - Worker ID
     * @returns {boolean}
     */
    isActive(workerId) {
        return this.activeWorkers.has(workerId);
    }

    /**
     * 获取活跃 Worker 数量
     * @returns {number}
     */
    getActiveCount() {
        return this.activeWorkers.size;
    }

    /**
     * 等待所有活跃 Worker 完成
     * @param {Function} onProgress - 进度回调
     * @returns {Promise<void>}
     */
    async waitForAll(onProgress) {
        while (this.activeWorkers.size > 0) {
            if (onProgress) {
                onProgress(this.activeWorkers.size);
            }
            await this._delay(500);
        }
    }

    // ========================================================================
    // 任务调度
    // ========================================================================

    /**
     * 计算 Worker ID (Round-Robin)
     * @param {number} taskIndex - 任务索引
     * @returns {number} Worker ID (1-based)
     */
    getWorkerId(taskIndex) {
        return (taskIndex % this.maxWorkers) + 1;
    }

    /**
     * 执行并发任务
     * @param {Array} tasks - 任务列表
     * @param {Function} executor - 任务执行函数
     * @param {object} [options] - 执行选项
     * @returns {Promise<Array>} 执行结果
     */
    async executeAll(tasks, executor, options = {}) {
        const limit = pLimit(this.maxWorkers);
        this.stats.totalTasks = tasks.length;

        const results = await Promise.all(
            tasks.map((task, index) =>
                limit(async () => {
                    // V4.51: 智能背压检测 - 如果挂起操作过多，等待
                    await this._waitForBackpressureRelease();

                    const workerId = this.getWorkerId(index);
                    this.register(workerId);

                    // 增加挂起操作计数
                    this._incrementPending();

                    try {
                        const result = await executor(task, index, workerId);
                        this.stats.completedTasks++;
                        return result;
                    } catch (error) {
                        this.stats.failedTasks++;
                        // V4.51: 添加错误日志，确保异常不被吞没
                        console.error(`❌ [WorkerPool] Worker ${workerId} 执行失败:`, error.message);
                        // 返回失败结果而不是抛出，确保流程继续
                        return { success: false, error: error.message, workerId };
                    } finally {
                        this.unregister(workerId);
                        // 减少挂起操作计数
                        this._decrementPending();
                    }
                })
            )
        );

        return results;
    }

    /**
     * 执行任务并带重试
     * @param {Array} tasks - 任务列表
     * @param {Function} executor - 任务执行函数
     * @param {object} retryOptions - 重试选项
     * @returns {Promise<Array>} 执行结果
     */
    async executeWithRetry(tasks, executor, retryOptions = {}) {
        const maxRetries = retryOptions.maxRetries || 3;
        const shouldRetry = retryOptions.shouldRetry || (() => true);
        const onRetry = retryOptions.onRetry;

        const limit = pLimit(this.maxWorkers);
        this.stats.totalTasks = tasks.length;

        const results = await Promise.all(
            tasks.map((task, index) =>
                limit(async () => {
                    // V4.51: 智能背压检测 - 如果挂起操作过多，等待
                    await this._waitForBackpressureRelease();

                    const workerId = this.getWorkerId(index);
                    let lastError = null;

                    for (let attempt = 1; attempt <= maxRetries; attempt++) {
                        this.register(workerId);
                        // 增加挂起操作计数
                        this._incrementPending();

                        try {
                            const result = await executor(task, index, workerId, attempt);

                            if (result.success) {
                                this.stats.completedTasks++;
                                if (attempt > 1) {
                                    this.logger(`✅ [RETRY-${attempt}] 重试成功`);
                                }
                                return result;
                            }

                            // 检查是否可重试
                            if (!shouldRetry(result.error)) {
                                this.stats.failedTasks++;
                                return result;
                            }

                            lastError = result.error;
                        } catch (error) {
                            lastError = error.message;

                            if (!shouldRetry(error)) {
                                this.stats.failedTasks++;
                                return {
                                    success: false,
                                    error: error.message,
                                    attempts: attempt
                                };
                            }
                        } finally {
                            this.unregister(workerId);
                            // 减少挂起操作计数
                            this._decrementPending();
                        }

                        // 准备重试
                        if (attempt < maxRetries) {
                            if (onRetry) {
                                await onRetry(workerId, attempt);
                            }
                            await this._delay(this._getBackoff(attempt));
                        }
                    }

                    // 所有重试失败
                    this.stats.failedTasks++;
                    return {
                        success: false,
                        error: `重试 ${maxRetries} 次后仍失败: ${lastError}`,
                        attempts: maxRetries
                    };
                })
            )
        );

        return results;
    }

    // ========================================================================
    // 辅助方法
    // ========================================================================

    /**
     * 匂时
     * @param {number} ms - 毫秒数
     * @returns {Promise<void>}
     */
    _delay(ms) {
        return new Promise(resolve => {
            setTimeout(resolve, ms);
        });
    }

    /**
     * 计算指数退避时间
     * @param {number} attempt - 当前尝试次数
     * @returns {number} 退避时间 (ms)
     */
    _getBackoff(attempt) {
        return Math.min(1000 * Math.pow(2, attempt), 10000);
    }

    /**
     * 获取统计信息
     * @returns {object}
     */
    getStats() {
        return {
            ...this.stats,
            pendingOperations: this.pendingOperations,  // V4.51: 当前挂起操作数
            maxPendingOperations: this.maxPendingOperations  // V4.51: 背压阈值
        };
    }

    /**
     * V4.51: 获取背压状态报告
     * @returns {object}
     */
    getBackpressureReport() {
        return {
            pendingOperations: this.pendingOperations,
            maxPendingOperations: this.maxPendingOperations,
            pressureRatio: (this.pendingOperations / this.maxPendingOperations).toFixed(2),
            isThrottling: this._needsBackpressure(),
            totalDelays: this.stats.backpressureDelays
        };
    }

    /**
     * 重置统计信息
     */
    resetStats() {
        this.stats = {
            totalTasks: 0,
            completedTasks: 0,
            failedTasks: 0,
            activeWorkers: 0,
            peakConcurrency: 0
        };
    }
}

// ============================================================================
// 单例导出
// ============================================================================

let instance = null;

/**
 * 获取 WorkerPool 单例
 * @param {object} [options] - 配置选项
 * @returns {WorkerPool}
 */
function getWorkerPool(options) {
    if (!instance) {
        instance = new WorkerPool(options);
    }
    return instance;
}

 /**
  * 重置单例 (用于测试)
  */
function resetWorkerPool() {
    instance = null;
}

module.exports = {
    WorkerPool,
    getWorkerPool,
    resetWorkerPool
};
