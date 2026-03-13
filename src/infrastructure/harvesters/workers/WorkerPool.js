/**
 * WorkerPool - V4.46 Worker 调度中心
 * ====================================
 *
 * 从 ProductionHarvester 剥离的 Worker 调度逻辑
 * 统一管理 Worker 的启动、清理、任务分配、并发控制
 *
 * @module infrastructure/harvesters/workers/WorkerPool
 * @version V4.46.0
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
 */
class WorkerPool {
    /**
     * @param {Object} options - 配置选项
     * @param {number} [options.maxWorkers] - 最大 Worker 数量
     * @param {Function} [options.logger] - 日志函数
     */
    constructor(options = {}) {
        this.maxWorkers = options.maxWorkers || 6;
        this.logger = options.logger || console;

        // 活跃 Worker 集合
        this.activeWorkers = new Set();

        // 任务队列
        this.taskQueue = [];

        // 统计信息
        this.stats = {
            totalTasks: 0,
            completedTasks: 0,
            failedTasks: 0,
            activeWorkers: 0,
            peakConcurrency: 0
        };
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
     * @param {Object} [options] - 执行选项
     * @returns {Promise<Array>} 执行结果
     */
    async executeAll(tasks, executor, options = {}) {
        const limit = pLimit(this.maxWorkers);
        this.stats.totalTasks = tasks.length;

        const results = await Promise.all(
            tasks.map((task, index) =>
                limit(async () => {
                    const workerId = this.getWorkerId(index);
                    this.register(workerId);

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
     * @param {Object} retryOptions - 重试选项
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
                    const workerId = this.getWorkerId(index);
                    let lastError = null;

                    for (let attempt = 1; attempt <= maxRetries; attempt++) {
                        this.register(workerId);

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
     * @returns {Object}
     */
    getStats() {
        return { ...this.stats };
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
 * @param {Object} [options] - 配置选项
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
