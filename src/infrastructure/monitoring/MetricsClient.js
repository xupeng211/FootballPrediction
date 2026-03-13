/**
 * MetricsClient - Node.js 指标客户端
 * ==================================
 *
 * 通过 HTTP 调用 Python API 记录收割指标
 * 支持 Prometheus 格式导出
 *
 * V4.46.6: 新增 L1 发现层指标支持
 * @module infrastructure/monitoring/MetricsClient
 * @version V4.46.6
 */

'use strict';

const http = require('http');

// ============================================================================
// 内存指标存储 (用于 /metrics 端点)
// ============================================================================

const metricsStore = {
    // 收割指标
    harvestTotal: 0,
    harvestSuccess: 0,
    harvestFailed: 0,
    harvestDurationMs: [],

    // 错误分类
    errorsByType: {},

    // 代理指标
    proxyRequests: 0,
    proxySuccess: 0,
    proxyFailed: 0,
    proxyByPort: {},

    // V4.46.5 HARDENING: L2 堆积量监控
    matchesPending: 0,       // 待收割比赛数
    matchesProcessed: 0,    // 已处理比赛数
    l2Backlog: 0,           // L2 堆积量
    lastBacklogUpdate: null, // 最后更新时间

    // V4.46.6: L1 发现层指标
    l1DiscoveredTotal: 0,       // L1 发现总数
    l1InsertedTotal: 0,         // L1 插入总数
    l1UpdatedTotal: 0,          // L1 更新总数
    l1FetchDurationMs: [],      // L1 HTTP 请求耗时
    l1BatchWriteDurationMs: [], // L1 批量写入耗时
    l1BatchesTotal: 0,          // L1 批量写入次数
    l1LastRunTime: null,        // L1 最后运行时间
    l1ByLeague: {},             // 按联赛统计

    // 时间戳
    lastHarvestTime: null,
    startTime: Date.now(),
};

// ============================================================================
// MetricsClient 类
// ============================================================================

/**
 *
 */
class MetricsClient {
    /**
     * @param {object} config - 配置选项
     * @param {string} [config.apiHost] - API 主机
     * @param {number} [config.apiPort] - API 端口
     */
    constructor(config = {}) {
        this.apiHost = config.apiHost || process.env.API_HOST || 'localhost';
        this.apiPort = config.apiPort || parseInt(process.env.API_PORT) || 8000;
        this.enabled = process.env.ENABLE_METRICS !== 'false';
    }

    /**
     * 记录收割开始
     * @param {string} matchId - 比赛 ID
     * @param {number} workerId - Worker ID
     */
    recordHarvestStart(matchId, workerId) {
        metricsStore.harvestTotal++;
        metricsStore.lastHarvestTime = Date.now();
    }

    /**
     * 记录收割成功
     * @param {string} matchId - 比赛 ID
     * @param {number} workerId - Worker ID
     * @param {number} durationMs - 耗时（毫秒）
     * @param {number} dataSize - 数据大小（字节）
     * @param {number} proxyPort - 代理端口
     */
    recordHarvestSuccess(matchId, workerId, durationMs, dataSize, proxyPort) {
        metricsStore.harvestSuccess++;
        metricsStore.harvestDurationMs.push(durationMs);

        // 保留最近 100 条耗时记录
        if (metricsStore.harvestDurationMs.length > 100) {
            metricsStore.harvestDurationMs.shift();
        }

        // 代理统计
        metricsStore.proxyRequests++;
        metricsStore.proxySuccess++;
        if (!metricsStore.proxyByPort[proxyPort]) {
            metricsStore.proxyByPort[proxyPort] = { success: 0, failed: 0 };
        }
        metricsStore.proxyByPort[proxyPort].success++;

        // 异步通知 Python API
        this._notifyPythonAPI('success', {
            matchId,
            workerId,
            durationMs,
            dataSize,
            proxyPort
        });
    }

    /**
     * 记录收割失败
     * @param {string} matchId - 比赛 ID
     * @param {number} workerId - Worker ID
     * @param {string} errorType - 错误类型
     * @param {string} errorMessage - 错误消息
     * @param {number} proxyPort - 代理端口
     */
    recordHarvestFailure(matchId, workerId, errorType, errorMessage, proxyPort) {
        metricsStore.harvestFailed++;

        // 错误分类统计
        if (!metricsStore.errorsByType[errorType]) {
            metricsStore.errorsByType[errorType] = 0;
        }
        metricsStore.errorsByType[errorType]++;

        // 代理统计
        metricsStore.proxyRequests++;
        metricsStore.proxyFailed++;
        if (proxyPort && !metricsStore.proxyByPort[proxyPort]) {
            metricsStore.proxyByPort[proxyPort] = { success: 0, failed: 0 };
        }
        if (proxyPort) {
            metricsStore.proxyByPort[proxyPort].failed++;
        }

        // 异步通知 Python API
        this._notifyPythonAPI('failure', {
            matchId,
            workerId,
            errorType,
            errorMessage,
            proxyPort
        });
    }

    /**
     * 记录代理健康状态
     * @param {number} port - 代理端口
     * @param {number} healthScore - 健康分数 (0-100)
     */
    recordProxyHealth(port, healthScore) {
        if (!metricsStore.proxyByPort[port]) {
            metricsStore.proxyByPort[port] = { success: 0, failed: 0, healthScore: 100 };
        }
        metricsStore.proxyByPort[port].healthScore = healthScore;
    }

    /**
     * V4.46.5 HARDENING: 记录待收割比赛数（L2 堆积量）
     * 应在收割循环开始时调用
     * @param {number} pending - 待收割比赛数
     * @param {number} processed - 已处理比赛数
     */
    recordPendingMatches(pending, processed = 0) {
        metricsStore.matchesPending = pending;
        metricsStore.matchesProcessed = processed;
        metricsStore.l2Backlog = pending - processed;
        metricsStore.lastBacklogUpdate = Date.now();
    }

    /**
     * V4.46.5 HARDENING: 更新已处理比赛数
     * @param {number} processed - 新增已处理数
     */
    updateProcessedMatches(processed) {
        metricsStore.matchesProcessed += processed;
        metricsStore.l2Backlog = metricsStore.matchesPending - metricsStore.matchesProcessed;
    }

    // ========================================================================
    // V4.46.6: L1 发现层指标方法
    // ========================================================================

    /**
     * V4.46.6: 记录 L1 发现计数
     * @param {number} count - 发现的比赛数
     * @param {string} [leagueName] - 联赛名称 (可选)
     */
    recordL1Discovery(count, leagueName = null) {
        metricsStore.l1DiscoveredTotal += count;
        metricsStore.l1LastRunTime = Date.now();

        // 按联赛统计
        if (leagueName) {
            if (!metricsStore.l1ByLeague[leagueName]) {
                metricsStore.l1ByLeague[leagueName] = { discovered: 0, inserted: 0, updated: 0 };
            }
            metricsStore.l1ByLeague[leagueName].discovered += count;
        }
    }

    /**
     * V4.46.6: 记录 L1 HTTP 请求耗时
     * @param {number} durationMs - 耗时（毫秒）
     */
    recordL1FetchDuration(durationMs) {
        metricsStore.l1FetchDurationMs.push(durationMs);

        // 保留最近 100 条记录
        if (metricsStore.l1FetchDurationMs.length > 100) {
            metricsStore.l1FetchDurationMs.shift();
        }
    }

    /**
     * V4.46.6: 记录 L1 批量写入
     * @param {number} durationMs - 耗时（毫秒）
     * @param {number} batchSize - 批量大小
     * @param {number} [inserted] - 插入数量
     * @param {number} [updated] - 更新数量
     */
    recordL1BatchWrite(durationMs, batchSize, inserted = 0, updated = 0) {
        metricsStore.l1BatchWriteDurationMs.push({ duration: durationMs, size: batchSize });
        metricsStore.l1BatchesTotal++;
        metricsStore.l1InsertedTotal += inserted;
        metricsStore.l1UpdatedTotal += updated;

        // 保留最近 50 条记录
        if (metricsStore.l1BatchWriteDurationMs.length > 50) {
            metricsStore.l1BatchWriteDurationMs.shift();
        }
    }

    /**
     * V4.46.6: 记录 L1 完成统计
     * @param {object} stats - 统计对象
     */
    recordL1Complete(stats) {
        metricsStore.l1DiscoveredTotal = stats.fixtures || 0;
        metricsStore.l1InsertedTotal = stats.inserted || 0;
        metricsStore.l1UpdatedTotal = stats.updated || 0;
        metricsStore.l1LastRunTime = Date.now();
    }

    /**
     * 获取 Prometheus 格式指标
     * @returns {string} Prometheus 文本格式
     */
    getPrometheusMetrics() {
        const lines = [];
        const now = Date.now();

        // 帮助和类型声明
        lines.push('# HELP titan_harvest_total Total harvest attempts');
        lines.push('# TYPE titan_harvest_total counter');
        lines.push(`titan_harvest_total ${metricsStore.harvestTotal}`);

        lines.push('# HELP titan_harvest_success_total Successful harvests');
        lines.push('# TYPE titan_harvest_success_total counter');
        lines.push(`titan_harvest_success_total ${metricsStore.harvestSuccess}`);

        lines.push('# HELP titan_harvest_failed_total Failed harvests');
        lines.push('# TYPE titan_harvest_failed_total counter');
        lines.push(`titan_harvest_failed_total ${metricsStore.harvestFailed}`);

        // 平均耗时
        const avgDuration = metricsStore.harvestDurationMs.length > 0
            ? metricsStore.harvestDurationMs.reduce((a, b) => a + b, 0) / metricsStore.harvestDurationMs.length
            : 0;

        lines.push('# HELP titan_harvest_duration_avg_ms Average harvest duration in milliseconds');
        lines.push('# TYPE titan_harvest_duration_avg_ms gauge');
        lines.push(`titan_harvest_duration_avg_ms ${avgDuration.toFixed(2)}`);

        // 成功率
        const successRate = metricsStore.harvestTotal > 0
            ? (metricsStore.harvestSuccess / metricsStore.harvestTotal * 100)
            : 0;

        lines.push('# HELP titan_harvest_success_rate Harvest success rate (0-100)');
        lines.push('# TYPE titan_harvest_success_rate gauge');
        lines.push(`titan_harvest_success_rate ${successRate.toFixed(2)}`);

        // V4.46.5 HARDENING: L2 堆积量指标
        lines.push('# HELP titan_matches_pending Matches pending harvest');
        lines.push('# TYPE titan_matches_pending gauge');
        lines.push(`titan_matches_pending ${metricsStore.matchesPending}`);

        lines.push('# HELP titan_matches_processed Matches processed');
        lines.push('# TYPE titan_matches_processed gauge');
        lines.push(`titan_matches_processed ${metricsStore.matchesProcessed}`);

        lines.push('# HELP titan_l2_backlog L2 backlog (pending - processed)');
        lines.push('# TYPE titan_l2_backlog gauge');
        lines.push(`titan_l2_backlog ${metricsStore.l2Backlog}`);

        if (metricsStore.lastBacklogUpdate) {
            const backlogUpdateSecondsAgo = (now - metricsStore.lastBacklogUpdate) / 1000;
            lines.push('# HELP titan_l2_backlog_update_seconds_ago Seconds since last backlog update');
            lines.push('# TYPE titan_l2_backlog_update_seconds_ago gauge');
            lines.push(`titan_l2_backlog_update_seconds_ago ${backlogUpdateSecondsAgo.toFixed(2)}`);
        }

        // V4.46.6: L1 发现层指标
        lines.push('# HELP titan_l1_discovered_total Total matches discovered by L1');
        lines.push('# TYPE titan_l1_discovered_total counter');
        lines.push(`titan_l1_discovered_total ${metricsStore.l1DiscoveredTotal}`);

        lines.push('# HELP titan_l1_inserted_total Total matches inserted by L1');
        lines.push('# TYPE titan_l1_inserted_total counter');
        lines.push(`titan_l1_inserted_total ${metricsStore.l1InsertedTotal}`);

        lines.push('# HELP titan_l1_updated_total Total matches updated by L1');
        lines.push('# TYPE titan_l1_updated_total counter');
        lines.push(`titan_l1_updated_total ${metricsStore.l1UpdatedTotal}`);

        lines.push('# HELP titan_l1_batches_total Total L1 batch write operations');
        lines.push('# TYPE titan_l1_batches_total counter');
        lines.push(`titan_l1_batches_total ${metricsStore.l1BatchesTotal}`);

        // L1 HTTP 请求平均耗时
        const l1AvgFetchDuration = metricsStore.l1FetchDurationMs.length > 0
            ? metricsStore.l1FetchDurationMs.reduce((a, b) => a + b, 0) / metricsStore.l1FetchDurationMs.length
            : 0;
        lines.push('# HELP titan_l1_fetch_duration_avg_ms Average L1 HTTP fetch duration in milliseconds');
        lines.push('# TYPE titan_l1_fetch_duration_avg_ms gauge');
        lines.push(`titan_l1_fetch_duration_avg_ms ${l1AvgFetchDuration.toFixed(2)}`);

        // L1 批量写入平均耗时
        const l1AvgBatchDuration = metricsStore.l1BatchWriteDurationMs.length > 0
            ? metricsStore.l1BatchWriteDurationMs.reduce((a, b) => a + b.duration, 0) / metricsStore.l1BatchWriteDurationMs.length
            : 0;
        lines.push('# HELP titan_l1_batch_write_duration_avg_ms Average L1 batch write duration in milliseconds');
        lines.push('# TYPE titan_l1_batch_write_duration_avg_ms gauge');
        lines.push(`titan_l1_batch_write_duration_avg_ms ${l1AvgBatchDuration.toFixed(2)}`);

        // L1 最后运行时间
        if (metricsStore.l1LastRunTime) {
            const l1RunSecondsAgo = (now - metricsStore.l1LastRunTime) / 1000;
            lines.push('# HELP titan_l1_last_run_seconds_ago Seconds since last L1 run');
            lines.push('# TYPE titan_l1_last_run_seconds_ago gauge');
            lines.push(`titan_l1_last_run_seconds_ago ${l1RunSecondsAgo.toFixed(2)}`);
        }

        // 代理统计
        lines.push('# HELP titan_proxy_requests_total Total proxy requests');
        lines.push('# TYPE titan_proxy_requests_total counter');
        lines.push(`titan_proxy_requests_total ${metricsStore.proxyRequests}`);

        lines.push('# HELP titan_proxy_by_port Proxy statistics by port');
        lines.push('# TYPE titan_proxy_by_port gauge');

        for (const [port, stats] of Object.entries(metricsStore.proxyByPort)) {
            lines.push(`titan_proxy_by_port{port="${port}",status="success"} ${stats.success}`);
            lines.push(`titan_proxy_by_port{port="${port}",status="failed"} ${stats.failed}`);
            if (stats.healthScore !== undefined) {
                lines.push(`titan_proxy_by_port{port="${port}",status="health"} ${stats.healthScore}`);
            }
        }

        // 错误分类
        lines.push('# HELP titan_harvest_errors_by_type Harvest errors by type');
        lines.push('# TYPE titan_harvest_errors_by_type counter');
        for (const [errorType, count] of Object.entries(metricsStore.errorsByType)) {
            lines.push(`titan_harvest_errors_by_type{type="${errorType}"} ${count}`);
        }

        // 运行时间
        const uptimeSeconds = (now - metricsStore.startTime) / 1000;
        lines.push('# HELP titan_process_uptime_seconds Process uptime in seconds');
        lines.push('# TYPE titan_process_uptime_seconds gauge');
        lines.push(`titan_process_uptime_seconds ${uptimeSeconds.toFixed(2)}`);

        // 最后收割时间
        if (metricsStore.lastHarvestTime) {
            const lastHarvestSecondsAgo = (now - metricsStore.lastHarvestTime) / 1000;
            lines.push('# HELP titan_harvest_last_seconds_ago Seconds since last harvest');
            lines.push('# TYPE titan_harvest_last_seconds_ago gauge');
            lines.push(`titan_harvest_last_seconds_ago ${lastHarvestSecondsAgo.toFixed(2)}`);
        }

        lines.push('');
        return lines.join('\n');
    }

    /**
     * 获取 JSON 格式统计
     * @returns {object} 统计对象
     */
    getStats() {
        const avgDuration = metricsStore.harvestDurationMs.length > 0
            ? metricsStore.harvestDurationMs.reduce((a, b) => a + b, 0) / metricsStore.harvestDurationMs.length
            : 0;

        return {
            harvest: {
                total: metricsStore.harvestTotal,
                success: metricsStore.harvestSuccess,
                failed: metricsStore.harvestFailed,
                successRate: metricsStore.harvestTotal > 0
                    ? (metricsStore.harvestSuccess / metricsStore.harvestTotal * 100).toFixed(2) + '%'
                    : '0%',
                avgDurationMs: avgDuration.toFixed(2),
            },
            // V4.46.5 HARDENING: L2 堆积量统计
            backlog: {
                pending: metricsStore.matchesPending,
                processed: metricsStore.matchesProcessed,
                backlog: metricsStore.l2Backlog,
                lastUpdate: metricsStore.lastBacklogUpdate
                    ? ((Date.now() - metricsStore.lastBacklogUpdate) / 1000).toFixed(0) + 's ago'
                    : 'N/A',
            },
            proxy: {
                requests: metricsStore.proxyRequests,
                success: metricsStore.proxySuccess,
                failed: metricsStore.proxyFailed,
                byPort: metricsStore.proxyByPort,
            },
            errors: metricsStore.errorsByType,
            uptime: ((Date.now() - metricsStore.startTime) / 1000).toFixed(0) + 's',
        };
    }

    /**
     * 异步通知 Python API (非阻塞)
     * @param event
     * @param data
     * @private
     */
    _notifyPythonAPI(event, data) {
        if (!this.enabled) return;

        // 异步发送，不等待响应
        const postData = JSON.stringify({ event, ...data });

        const options = {
            hostname: this.apiHost,
            port: this.apiPort,
            path: '/api/v1/monitoring/record',
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(postData),
            },
            timeout: 1000, // 1秒超时
        };

        const req = http.request(options, () => {
            // 静默成功
        });

        req.on('error', () => {
            // 静默失败，不影响主流程
        });

        req.on('timeout', () => {
            req.destroy();
        });

        req.write(postData);
        req.end();
    }

    /**
     * 重置所有指标
     */
    reset() {
        metricsStore.harvestTotal = 0;
        metricsStore.harvestSuccess = 0;
        metricsStore.harvestFailed = 0;
        metricsStore.harvestDurationMs = [];
        metricsStore.errorsByType = {};
        metricsStore.proxyRequests = 0;
        metricsStore.proxySuccess = 0;
        metricsStore.proxyFailed = 0;
        metricsStore.proxyByPort = {};
        // V4.46.5 HARDENING: 重置 L2 堆积量指标
        metricsStore.matchesPending = 0;
        metricsStore.matchesProcessed = 0;
        metricsStore.l2Backlog = 0;
        metricsStore.lastBacklogUpdate = null;
        // V4.46.6: 重置 L1 发现层指标
        metricsStore.l1DiscoveredTotal = 0;
        metricsStore.l1InsertedTotal = 0;
        metricsStore.l1UpdatedTotal = 0;
        metricsStore.l1FetchDurationMs = [];
        metricsStore.l1BatchWriteDurationMs = [];
        metricsStore.l1BatchesTotal = 0;
        metricsStore.l1LastRunTime = null;
        metricsStore.l1ByLeague = {};
        metricsStore.startTime = Date.now();
    }
}

// ============================================================================
// 单例
// ============================================================================

let metricsClientInstance = null;

/**
 * 获取 MetricsClient 单例
 * @param {object} [config] - 配置选项
 * @returns {MetricsClient}
 */
function getMetricsClient(config = {}) {
    if (!metricsClientInstance) {
        metricsClientInstance = new MetricsClient(config);
    }
    return metricsClientInstance;
}

// ============================================================================
// 导出
// ============================================================================

module.exports = {
    MetricsClient,
    getMetricsClient,
    metricsStore,
};
