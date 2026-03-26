'use strict';

/**
 * HarvesterTelemetry - 收割器统计与指标组件
 * =======================================
 *
 * 统一管理：
 * - stats 状态
 * - metrics 上报
 * - 收割摘要生成
 * - 报告打印
 */
class HarvesterTelemetry {
    /**
     * @param {object} [config]
     * @param {object|null} [config.metricsClient]
     */
    constructor(config = {}) {
        this.metricsClient = config.metricsClient || null;
        this.startTime = null;
        this.stats = this._createDefaultStats();
    }

    /**
     * 创建默认统计对象。
     * @returns {{total: number, processed: number, success: number, failed: number, retries: number, sweepRounds: number}}
     * @private
     */
    _createDefaultStats() {
        return {
            total: 0,
            processed: 0,
            success: 0,
            failed: 0,
            retries: 0,
            sweepRounds: 0,
        };
    }

    /**
     * 更新 metrics 客户端。
     * @param {object|null} metricsClient
     */
    setMetricsClient(metricsClient) {
        this.metricsClient = metricsClient || null;
    }

    /**
     * 获取当前统计快照。
     * @returns {object}
     */
    getStats() {
        return this.stats;
    }

    /**
     * 用外部状态替换统计对象。
     * @param {object} stats
     */
    replaceStats(stats) {
        this.stats = { ...this._createDefaultStats(), ...(stats || {}) };
    }

    /**
     * 重置统计信息。
     * @returns {void}
     */
    resetStats() {
        this.stats = this._createDefaultStats();
    }

    /**
     * 记录本轮收割开始时间。
     * @param {number|null} startTime
     */
    setStartTime(startTime) {
        this.startTime = startTime;
    }

    /**
     * 增加重试计数。
     * @returns {void}
     */
    recordRetry() {
        this.stats.retries++;
    }

    /**
     * 记录单次成功。
     * @returns {void}
     */
    recordSuccess() {
        this.stats.processed++;
        this.stats.success++;
    }

    /**
     * 记录单次失败。
     * @returns {void}
     */
    recordFailure() {
        this.stats.processed++;
        this.stats.failed++;
    }

    /**
     * 上报收割开始指标。
     * @param {string} matchId
     * @param {number} workerId
     */
    recordHarvestStart(matchId, workerId) {
        this.metricsClient?.recordHarvestStart?.(matchId, workerId);
    }

    /**
     * 上报收割成功指标。
     * @param {string} matchId
     * @param {number} workerId
     * @param {number} durationMs
     * @param {number} size
     * @param {number|string} port
     */
    recordHarvestSuccess(matchId, workerId, durationMs, size, port) {
        this.metricsClient?.recordHarvestSuccess?.(matchId, workerId, durationMs, size, port);
    }

    /**
     * 上报收割失败指标。
     * @param {string} matchId
     * @param {number} workerId
     * @param {string} errorType
     * @param {string} errorMessage
     * @param {number|string} port
     */
    recordHarvestFailure(matchId, workerId, errorType, errorMessage, port) {
        this.metricsClient?.recordHarvestFailure?.(matchId, workerId, errorType, errorMessage, port);
    }

    /**
     * 输出批次统计日志。
     * @param {object} logger
     * @param {object} [payload={}]
     */
    logBatchStats(logger, payload = {}) {
        logger?.info?.('batch_stats', {
            ...payload,
            stats: { ...this.stats }
        });
    }

    /**
     * 生成收割摘要文本。
     * @param {object} [options={}]
     * @param {string} [options.harvesterName='AbstractHarvester']
     * @param {number} [options.maxWorkers=0]
     * @param {object|null} [options.contextStats=null]
     * @param {Map<number, object>|null} [options.workerIdentities=null]
     * @param {number} [options.now=Date.now()]
     * @returns {string[]}
     */
    generateHarvestSummary(options = {}) {
        const {
            harvesterName = 'AbstractHarvester',
            maxWorkers = 0,
            contextStats = null,
            workerIdentities = null,
            now = Date.now()
        } = options;

        const elapsed = this.startTime ? ((now - this.startTime) / 1000).toFixed(1) : '0.0';
        const rate = this.stats.total > 0 ? ((this.stats.success / this.stats.total) * 100).toFixed(1) : '0.0';
        const lines = [
            '═══════════════════════════════════════════════════════════════',
            `  📊 ${harvesterName} 收割完成报告`,
            '═══════════════════════════════════════════════════════════════',
            `  总计: ${this.stats.total} 场`,
            `  成功: ${this.stats.success} 场`,
            `  失败: ${this.stats.failed} 场`,
            `  成功率: ${rate}%`,
            `  重试次数: ${this.stats.retries}`,
            `  扫尾轮数: ${this.stats.sweepRounds}`,
            `  耗时: ${elapsed} 秒`,
            `  Worker 数: ${maxWorkers}`
        ];

        if (contextStats?.totalCreations > 0) {
            const reuseRate = ((contextStats.totalReuses / (contextStats.totalCreations + contextStats.totalReuses)) * 100).toFixed(0);
            const evictionRate = ((contextStats.totalEvictions / contextStats.totalCreations) * 100).toFixed(0);
            lines.push(
                `  Context 池: 创建=${contextStats.totalCreations} 复用=${contextStats.totalReuses} (${reuseRate}% 复用率) 淘汰=${contextStats.totalEvictions} (${evictionRate}%)`
            );
        }

        if (workerIdentities) {
            for (const [workerId, identity] of workerIdentities) {
                if (identity?.proxy) {
                    const successRate = (identity.getSuccessRate() * 100).toFixed(0);
                    lines.push(`    W${workerId}: Port ${identity.proxy.port} | ${identity.requestCount} 请求 | ${successRate}% 成功率`);
                }
            }
        }

        lines.push('═══════════════════════════════════════════════════════════════');
        return lines;
    }

    /**
     * 打印收割报告。
     * @param {object} [options={}]
     * @returns {void}
     */
    printReport(options = {}) {
        for (const line of this.generateHarvestSummary(options)) {
            console.log(line);
        }
    }
}

module.exports = {
    HarvesterTelemetry,
};
