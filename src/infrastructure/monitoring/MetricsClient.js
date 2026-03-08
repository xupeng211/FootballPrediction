/**
 * MetricsClient - Node.js 指标客户端
 * ==================================
 *
 * 通过 HTTP 调用 Python API 记录收割指标
 * 支持 Prometheus 格式导出
 *
 * @module infrastructure/monitoring/MetricsClient
 * @version V4.46.0
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

    // 时间戳
    lastHarvestTime: null,
    startTime: Date.now(),
};

// ============================================================================
// MetricsClient 类
// ============================================================================

class MetricsClient {
    /**
     * @param {Object} config - 配置选项
     * @param {string} [config.apiHost='localhost'] - API 主机
     * @param {number} [config.apiPort=8000] - API 端口
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
     * 获取 Prometheus 格式指标
     * @returns {string} Prometheus 文本格式
     */
    getPrometheusMetrics() {
        const lines = [];
        const now = Date.now();

        // 帮助和类型声明
        lines.push('# HELP harvest_total Total harvest attempts');
        lines.push('# TYPE harvest_total counter');
        lines.push(`harvest_total ${metricsStore.harvestTotal}`);

        lines.push('# HELP harvest_success_total Successful harvests');
        lines.push('# TYPE harvest_success_total counter');
        lines.push(`harvest_success_total ${metricsStore.harvestSuccess}`);

        lines.push('# HELP harvest_failed_total Failed harvests');
        lines.push('# TYPE harvest_failed_total counter');
        lines.push(`harvest_failed_total ${metricsStore.harvestFailed}`);

        // 平均耗时
        const avgDuration = metricsStore.harvestDurationMs.length > 0
            ? metricsStore.harvestDurationMs.reduce((a, b) => a + b, 0) / metricsStore.harvestDurationMs.length
            : 0;

        lines.push('# HELP harvest_duration_avg_ms Average harvest duration in milliseconds');
        lines.push('# TYPE harvest_duration_avg_ms gauge');
        lines.push(`harvest_duration_avg_ms ${avgDuration.toFixed(2)}`);

        // 成功率
        const successRate = metricsStore.harvestTotal > 0
            ? (metricsStore.harvestSuccess / metricsStore.harvestTotal * 100)
            : 0;

        lines.push('# HELP harvest_success_rate Harvest success rate (0-100)');
        lines.push('# TYPE harvest_success_rate gauge');
        lines.push(`harvest_success_rate ${successRate.toFixed(2)}`);

        // 代理统计
        lines.push('# HELP proxy_requests_total Total proxy requests');
        lines.push('# TYPE proxy_requests_total counter');
        lines.push(`proxy_requests_total ${metricsStore.proxyRequests}`);

        lines.push('# HELP proxy_by_port Proxy statistics by port');
        lines.push('# TYPE proxy_by_port gauge');

        for (const [port, stats] of Object.entries(metricsStore.proxyByPort)) {
            lines.push(`proxy_by_port{port="${port}",status="success"} ${stats.success}`);
            lines.push(`proxy_by_port{port="${port}",status="failed"} ${stats.failed}`);
            if (stats.healthScore !== undefined) {
                lines.push(`proxy_by_port{port="${port}",status="health"} ${stats.healthScore}`);
            }
        }

        // 错误分类
        lines.push('# HELP harvest_errors_by_type Harvest errors by type');
        lines.push('# TYPE harvest_errors_by_type counter');
        for (const [errorType, count] of Object.entries(metricsStore.errorsByType)) {
            lines.push(`harvest_errors_by_type{type="${errorType}"} ${count}`);
        }

        // 运行时间
        const uptimeSeconds = (now - metricsStore.startTime) / 1000;
        lines.push('# HELP process_uptime_seconds Process uptime in seconds');
        lines.push('# TYPE process_uptime_seconds gauge');
        lines.push(`process_uptime_seconds ${uptimeSeconds.toFixed(2)}`);

        // 最后收割时间
        if (metricsStore.lastHarvestTime) {
            const lastHarvestSecondsAgo = (now - metricsStore.lastHarvestTime) / 1000;
            lines.push('# HELP harvest_last_seconds_ago Seconds since last harvest');
            lines.push('# TYPE harvest_last_seconds_ago gauge');
            lines.push(`harvest_last_seconds_ago ${lastHarvestSecondsAgo.toFixed(2)}`);
        }

        lines.push('');
        return lines.join('\n');
    }

    /**
     * 获取 JSON 格式统计
     * @returns {Object} 统计对象
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
        metricsStore.startTime = Date.now();
    }
}

// ============================================================================
// 单例
// ============================================================================

let metricsClientInstance = null;

/**
 * 获取 MetricsClient 单例
 * @param {Object} [config] - 配置选项
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
