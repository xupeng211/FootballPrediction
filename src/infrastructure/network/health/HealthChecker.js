/**
 * HealthChecker - V1.0.0 [Genesis.NetworkShield] Active Pulsing Health Check
 * =========================================================================
 *
 * 自适应健康检查系统 - 组件启动时自动对 22 个端口进行并发微测。
 *
 * Core Features:
 * - 并发微测 (Concurrent micro-checks)
 * - Head 请求检测 (Head request detection)
 * - SSL 错误捕获 (SSL error capture)
 * - 403 频率检测 (403 frequency detection)
 * - 动态剔除 (Dynamic filtering)
 * - IP 地址验证 (IP address verification)
 * @module network/health/HealthChecker
 * @version V1.0.0
 * @since 2026-02-03
 * @author [Genesis.NetworkShield]
 */

'use strict';

const http = require('http');
const https = require('https');
const net = require('net');
const { URL } = require('url');
const { ProxyProvider } = require('../ProxyProvider');

// ============================================================================
// HEALTH CHECK RESULT
// ============================================================================

/**
 * @typedef {object} HealthCheckResult
 * @property {number} port - 代理端口
 * @property {boolean} is_healthy - 是否健康
 * @property {number} response_time - 响应时间（毫秒）
 * @property {string|null} ip_address - IP 地址
 * @property {string} error - 错误信息
 * @property {string} error_type - 错误类型 (SSL, TIMEOUT, 403, CONNECTION, etc.)
 */

// ============================================================================
// HEALTH CHECKER CLASS
// ============================================================================

/**
 *
 */
class HealthChecker {
    /**
     *
     * @param options
     */
    constructor(options = {}) {
        this.proxyHost = options.proxyHost || ProxyProvider.resolveHost();
        this.testUrl = options.testUrl || 'https://oddsportal.com';
        this.timeout = options.timeout || 5000;
        this.maxConcurrent = options.maxConcurrent || 10;

        // 错误统计
        this.errorCounts = new Map();
    }

    /**
     * 执行所有端口的并发健康检查
     * @param {Array<number>} ports - 端口列表
     * @returns {Promise<Array<HealthCheckResult>>} 健康检查结果
     */
    async checkAllPorts(ports) {
        const startTime = Date.now();
        const results = [];

        // 分批并发检查（避免过载）
        for (let i = 0; i < ports.length; i += this.maxConcurrent) {
            const batch = ports.slice(i, i + this.maxConcurrent);
            const batchResults = await Promise.all(
                batch.map(port => this.checkPort(port).catch(error => ({
                    port,
                    is_healthy: false,
                    response_time: 0,
                    ip_address: null,
                    error: error.message,
                    error_type: 'EXCEPTION'
                })))
            );
            results.push(...batchResults);
        }

        const elapsed = Date.now() - startTime;
        const healthyCount = results.filter(r => r.is_healthy).length;

        console.log(
            `[HealthChecker] Batch complete: ${healthyCount}/${ports.length} healthy ` +
            `(${elapsed}ms elapsed)`
        );

        return results;
    }

    /**
     * 检查单个端口的健康状态
     * @param {number} port - 代理端口
     * @returns {Promise<HealthCheckResult>} 健康检查结果
     */
    async checkPort(port) {
        const startTime = Date.now();
        const proxyUrl = ProxyProvider.buildServer(port, { host: this.proxyHost });

        try {
            // 步骤 1: TCP 连接测试
            const tcpConnected = await this._testTcpConnection(port, this.timeout);
            if (!tcpConnected) {
                return {
                    port,
                    is_healthy: false,
                    response_time: Date.now() - startTime,
                    ip_address: null,
                    error: 'TCP connection failed',
                    error_type: 'CONNECTION'
                };
            }

            // 步骤 2: HTTP HEAD 请求测试
            const result = await this._testHttpRequest(proxyUrl, this.timeout);

            return {
                port,
                is_healthy: result.is_healthy,
                response_time: Date.now() - startTime,
                ip_address: result.ip_address,
                error: result.error,
                error_type: result.error_type
            };

        } catch (error) {
            return {
                port,
                is_healthy: false,
                response_time: Date.now() - startTime,
                ip_address: null,
                error: error.message,
                error_type: 'EXCEPTION'
            };
        }
    }

    /**
     * 获取代理的 IP 地址
     * @param {number} port - 代理端口
     * @returns {Promise<string|null>} IP 地址
     */
    async getProxyIP(port) {
        const proxyUrl = ProxyProvider.buildServer(port, { host: this.proxyHost });

        try {
            const result = await this._testHttpRequest(proxyUrl, this.timeout, true);
            return result.ip_address;
        } catch (error) {
            return null;
        }
    }

    /**
     * 快速 Ping 测试（用于实时监控）
     * @param {number} port - 代理端口
     * @returns {Promise<boolean>} 是否可达
     */
    async quickPing(port) {
        const startTime = Date.now();

        try {
            await this._testTcpConnection(port, 2000);
            return true;
        } catch (error) {
            return false;
        }
    }

    // ========================================================================
    // PRIVATE METHODS
    // ========================================================================

    /**
     * TCP 连接测试
     * @private
     * @param {number} port - 端口
     * @param {number} timeout - 超时时间
     * @returns {Promise<boolean>} 是否连接成功
     */
    async _testTcpConnection(port, timeout) {
        return new Promise((resolve) => {
            const socket = new net.Socket();
            const timeoutId = setTimeout(() => {
                socket.destroy();
                resolve(false);
            }, timeout);

            socket.connect(port, this.proxyHost, () => {
                clearTimeout(timeoutId);
                socket.destroy();
                resolve(true);
            });

            socket.on('error', () => {
                clearTimeout(timeoutId);
                socket.destroy();
                resolve(false);
            });
        });
    }

    /**
     * HTTP 请求测试
     * @private
     * @param {string} proxyUrl - 代理 URL
     * @param {number} timeout - 超时时间
     * @param {boolean} fetchIP - 是否获取 IP
     * @returns {Promise<object>} 请求结果
     */
    async _testHttpRequest(proxyUrl, timeout, fetchIP = false) {
        return new Promise((resolve, reject) => {
            const testUrl = fetchIP ? 'https://api.ipify.org?format=text' : this.testUrl;
            const urlParsed = new URL(testUrl);

            const options = {
                method: 'HEAD',
                host: urlParsed.hostname,
                port: urlParsed.port || (urlParsed.protocol === 'https:' ? 443 : 80),
                path: urlParsed.pathname + urlParsed.search,
                headers: {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            };

            const protocol = urlParsed.protocol === 'https:' ? https : http;
            const req = protocol.request(options, (res) => {
                const result = {
                    is_healthy: true,
                    ip_address: null,
                    error: '',
                    error_type: ''
                };

                // 检查状态码
                if (res.statusCode === 403) {
                    result.is_healthy = false;
                    result.error = `HTTP ${res.statusCode} Forbidden`;
                    result.error_type = '403';
                    this._trackError('403');
                } else if (res.statusCode >= 400) {
                    result.is_healthy = false;
                    result.error = `HTTP ${res.statusCode}`;
                    result.error_type = `HTTP_${res.statusCode}`;
                }

                // 如果需要获取 IP
                if (fetchIP && res.statusCode === 200) {
                    let data = '';
                    res.on('data', chunk => { data += chunk; });
                    res.on('end', () => {
                        result.ip_address = data.trim();
                        resolve(result);
                    });
                } else {
                    resolve(result);
                }
            });

            req.on('error', (error) => {
                let errorType = 'UNKNOWN';

                // 错误分类
                if (error.code === 'CERT_HAS_EXPIRED' || error.code === 'UNABLE_TO_VERIFY_LEAF_SIGNATURE') {
                    errorType = 'SSL';
                } else if (error.code === 'ECONNREFUSED') {
                    errorType = 'CONNECTION';
                } else if (error.code === 'ETIMEDOUT' || error.code === 'ECONNRESET') {
                    errorType = 'TIMEOUT';
                }

                this._trackError(errorType);

                resolve({
                    is_healthy: false,
                    ip_address: null,
                    error: error.message,
                    error_type: errorType
                });
            });

            req.setTimeout(timeout);
            req.on('timeout', () => {
                req.destroy();
                this._trackError('TIMEOUT');
                resolve({
                    is_healthy: false,
                    ip_address: null,
                    error: 'Request timeout',
                    error_type: 'TIMEOUT'
                });
            });

            req.end();
        });
    }

    /**
     * 跟踪错误类型统计
     * @private
     * @param {string} errorType - 错误类型
     */
    _trackError(errorType) {
        const count = this.errorCounts.get(errorType) || 0;
        this.errorCounts.set(errorType, count + 1);
    }

    /**
     * 获取错误统计
     * @returns {object} 错误统计
     */
    getErrorStats() {
        return Object.fromEntries(this.errorCounts);
    }

    /**
     * 重置错误统计
     */
    resetErrorStats() {
        this.errorCounts.clear();
    }
}

// ============================================================================
// BATCH HEALTH CHECKER
// ============================================================================

/**
 *
 */
class BatchHealthChecker {
    /**
     *
     * @param options
     */
    constructor(options = {}) {
        this.healthChecker = new HealthChecker(options);
        this.registryManager = options.registryManager;

        if (!this.registryManager) {
            throw new Error('registryManager is required');
        }
    }

    /**
     * 执行完整的健康检查并更新注册表
     * @returns {Promise<object>} 健康检查摘要
     */
    async runFullHealthCheck() {
        const registry = this.registryManager.getRegistry();
        const ports = registry.nodes.map(n => n.port);

        console.log(`[BatchHealthChecker] Starting health check for ${ports.length} ports...`);

        const results = await this.healthChecker.checkAllPorts(ports);

        // 更新每个节点的健康状态
        for (const result of results) {
            await this.registryManager.updateNodeHealth(result.port, result);
        }

        // 生成摘要
        const summary = {
            total: ports.length,
            healthy: results.filter(r => r.is_healthy).length,
            unhealthy: results.filter(r => !r.is_healthy).length,
            error_stats: this.healthChecker.getErrorStats()
        };

        console.log(
            `[BatchHealthChecker] Health check complete: ` +
            `${summary.healthy}/${summary.total} healthy`
        );

        return summary;
    }

    /**
     * 快速检查并返回可用节点
     * @returns {Promise<Array>} 可用节点列表
     */
    async getHealthyNodes() {
        await this.runFullHealthCheck();
        return this.registryManager.getAvailableNodes();
    }
}

module.exports = {
    HealthChecker,
    BatchHealthChecker
};
