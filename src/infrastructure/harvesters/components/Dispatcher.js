/**
 * Dispatcher - 任务分派器
 * =========================
 *
 * 负责收割任务的分派与调度：
 * - Worker ID 计算与分配
 * - 批次逻辑处理
 * - CLI 参数解析
 * - 统计报告生成
 *
 * @module infrastructure/harvesters/components/Dispatcher
 * @version V1.0.0
 */

'use strict';

/**
 * 任务分派器类
 */
class Dispatcher {
    /**
     * 创建 Dispatcher 实例
     * @param {object} config - 配置选项
     * @param {number} config.maxWorkers - 最大 Worker 数量
     * @param {number} config.batchSize - 批次大小
     */
    constructor(config = {}) {
        this.config = {
            maxWorkers: config.maxWorkers || 6,
            batchSize: config.batchSize || 500
        };
        this.stats = {
            total: 0,
            processed: 0,
            success: 0,
            failed: 0,
            retries: 0,
            sweepRounds: 0
        };
        this.startTime = null;
    }

    /**
     * 计算 Worker ID
     * @param {number} index - 任务索引
     * @returns {number} Worker ID (1-based)
     */
    calculateWorkerId(index) {
        return (index % this.config.maxWorkers) + 1;
    }

    /**
     * 计算重试延迟
     * @param {boolean} isRetry - 是否为重试
     * @param {number} baseDelay - 基础延迟
     * @param {number} maxDelay - 最大延迟
     * @returns {number} 延迟时间（毫秒）
     */
    calculateDelay(isRetry, baseDelay, maxDelay) {
        const actualBase = isRetry ? 3000 : baseDelay;
        const actualMax = isRetry ? 6000 : maxDelay;
        return actualBase + Math.random() * (actualMax - actualBase);
    }

    /**
     * 计算成功率
     * @returns {string} 成功率（百分比，保留一位小数）
     */
    calculateSuccessRate() {
        return this.stats.total > 0
            ? ((this.stats.success / this.stats.total) * 100).toFixed(1)
            : '0.0';
    }

    /**
     * 获取已运行时间
     * @returns {string} 已运行时间（秒，保留一位小数）
     */
    getElapsedTime() {
        if (!this.startTime) return '0.0';
        return ((Date.now() - this.startTime) / 1000).toFixed(1);
    }

    /**
     * 开始计时
     */
    startTimer() {
        this.startTime = Date.now();
    }

    /**
     * 更新统计
     * @param {boolean} success - 是否成功
     * @param {boolean} isRetry - 是否为重试
     */
    updateStats(success, isRetry = false) {
        this.stats.processed++;
        if (success) {
            this.stats.success++;
        } else {
            this.stats.failed++;
        }
        if (isRetry) {
            this.stats.retries++;
        }
    }

    /**
     * 增加扫尾轮数
     */
    incrementSweepRound() {
        this.stats.sweepRounds++;
    }

    /**
     * 设置总任务数
     * @param {number} total - 总任务数
     */
    setTotal(total) {
        this.stats.total = total;
    }

    /**
     * 生成统计报告
     * @returns {object} 统计报告对象
     */
    generateReport() {
        return {
            elapsed: this.getElapsedTime(),
            total: this.stats.total,
            processed: this.stats.processed,
            success: this.stats.success,
            failed: this.stats.failed,
            retries: this.stats.retries,
            sweepRounds: this.stats.sweepRounds,
            successRate: this.calculateSuccessRate()
        };
    }

    /**
     * 打印统计报告
     */
    printReport() {
        const report = this.generateReport();
        console.log('═══════════════════════════════════════════════════════════════');
        console.log('                    📊 收割完成报告');
        console.log('═══════════════════════════════════════════════════════════════');
        console.log(`  运行时间: ${report.elapsed} 秒`);
        console.log(`  总计: ${report.total} 场`);
        console.log(`  成功: ${report.success} 场`);
        console.log(`  失败: ${report.failed} 场`);
        console.log(`  成功率: ${report.successRate}%`);
        console.log(`  重试次数: ${report.retries}`);
        console.log(`  扫尾轮数: ${report.sweepRounds}`);
        console.log('═══════════════════════════════════════════════════════════════');
    }

    /**
     * 解析 CLI 参数
     * @param {string[]} args - 命令行参数
     * @returns {object} 解析后的选项
     */
    static parseCliArgs(args) {
        const options = {
            matchId: null,
            force: false,
            verbose: false
        };

        for (const arg of args) {
            if (arg.startsWith('--matchId=')) {
                options.matchId = arg.split('=')[1];
            } else if (arg === '--force' || arg === '-f') {
                options.force = true;
            } else if (arg === '--verbose' || arg === '-v') {
                options.verbose = true;
            }
        }

        return options;
    }

    /**
     * 生成批次查询参数
     * @param {boolean} serieAPilot - 是否为意甲试点模式
     * @returns {object} 查询参数
     */
    generateBatchQueryParams(serieAPilot = false) {
        if (serieAPilot) {
            return {
                limit: 10,
                league: 'Serie A',
                orderBy: 'match_date DESC'
            };
        }
        return {
            limit: this.config.batchSize,
            orderBy: 'match_date DESC'
        };
    }

    /**
     * 获取日志前缀
     * @param {number} workerId - Worker ID
     * @param {number} attempt - 尝试次数
     * @param {boolean} isRetry - 是否为重试
     * @returns {string} 日志前缀
     */
    getLogPrefix(workerId, attempt = 1, isRetry = false) {
        const workerPart = workerId ? `[W${workerId}]` : '';
        const retryPart = isRetry ? `-R${attempt}` : '';
        return `${workerPart}${retryPart}`;
    }

    /**
     * 重置统计
     */
    resetStats() {
        this.stats = {
            total: 0,
            processed: 0,
            success: 0,
            failed: 0,
            retries: 0,
            sweepRounds: 0
        };
        this.startTime = null;
    }
}

module.exports = { Dispatcher };
