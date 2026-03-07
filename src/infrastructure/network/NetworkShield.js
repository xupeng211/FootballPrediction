/**
 * NetworkShield - V1.1.0 [Genesis.Standardization] Production-Grade Proxy Management
 * ============================================================================
 *
 * 工业级跨语言代理管理组件 - 统一管理 Python (L2) 和 Node.js (L3) 的网络出口，
 * 并深度对接 Windows 端的 Clash Verge (22个节点)。
 *
 * V1.1.0 改进:
 * - 依赖注入：支持 AbstractFileSystem 和 LRUSessionManager
 * - 错误码标准化：使用 NetworkShieldError
 * - RadarLogger 集成：统一的日志标准
 * - JSDoc 完整类型标注
 * - 改进的并发锁：基于文件系统的原子锁
 * - LRU 会话管理：解决长时间运行的内存泄漏
 *
 * Core Features:
 * - 解耦设计 (Decoupled architecture)
 * - 中央注册制 (Central registry management)
 * - 自适应健康检查 (Adaptive health checking)
 * - 智能轮换 (Smart rotation with session binding)
 * - 自愈熔断 (Self-healing circuit breaker)
 * - 跨语言状态同步 (Cross-language state sync)
 *
 * @module network/NetworkShield
 * @version V1.1.0
 * @since 2026-02-03
 * @author [Genesis.Standardization]
 */

'use strict';

// V4.20: 核心网络模块迁移到 src/core/network/
const { getRegistryManager } = require('../../core/network/RegistryManager');
const { BatchHealthChecker } = require('./health/HealthChecker');
const { CircuitBreakerRegistry } = require('../../core/network/CircuitBreaker');
const { LRUSessionManager } = require('../../core/network/LRUSessionManager');
const { RadarLogger } = require('./../engines/services/logging/RadarLogger');
const { noProxyAvailable, NetworkShieldError } = require('../../core/network/NetworkShieldError');
const { FileSystemProvider } = require('../../core/network/AbstractFileSystem');

// ============================================================================
// DEFAULT CONFIGURATION
// ============================================================================

/**
 * @typedef {Object} NetworkShieldConfig
 * @property {string} [proxyHost='172.25.16.1'] - 代理主机
 * @property {{start: number, end: number}} [portRange={start: 7891, end: 7912}] - 端口范围
 * @property {string} [protocol='http'] - 代理协议
 * @property {number} [healthCheckInterval=60000] - 健康检查间隔（毫秒）
 * @property {number} [cooldownMinutes=15] - 冷却时间（分钟）
 * @property {number} [sessionTimeoutMinutes=30] - 会话超时时间（分钟）
 * @property {number} [maxConsecutiveFailures=2] - 最大连续失败次数
 * @property {string} [logLevel='info'] - 日志级别
 * @property {boolean} [enabled=true] - 是否启用代理
 * @property {number} [lruMaxSize=500] - LRU 最大容量
 * @property {number} [maxSessions=1000] - 最大会话数
 * @property {boolean} [useMemoryFS=false] - 是否使用内存文件系统
 */

const DEFAULT_CONFIG = Object.freeze({
    proxyHost: '172.25.16.1',
    portRange: { start: 7891, end: 7912 },
    protocol: 'http',
    healthCheckInterval: 60000,
    cooldownMinutes: 15,
    sessionTimeoutMinutes: 30,
    maxConsecutiveFailures: 2,
    logLevel: 'info',
    enabled: true,
    lruMaxSize: 500,
    maxSessions: 1000,
    useMemoryFS: false
});

// ============================================================================
// NETWORK SHIELD MAIN CLASS
// ============================================================================

/**
 * NetworkShield - 中央代理管理类
 *
 * @class
 * @example
 * const shield = new NetworkShield({
 *   proxyHost: '172.25.16.1',
 *   logLevel: 'info'
 * });
 *
 * await shield.initialize();
 *
 * const proxy = await shield.getNextHealthyProxy('session-123');
 * if (proxy) {
 *   // 使用代理...
 *   await shield.markProxySuccess(proxy.port);
 *   shield.releaseSession('session-123');
 * }
 */
class NetworkShield {
    /**
     * 创建 NetworkShield 实例
     *
     * @param {NetworkShieldConfig} [options={}] - 配置选项
     */
    constructor(options = {}) {
        /**
         * @type {NetworkShieldConfig}
         * @readonly
         */
        this.options = { ...DEFAULT_CONFIG, ...options };

        // 初始化日志（使用 RadarLogger）
        /**
         * @type {RadarLogger}
         * @readonly
         */
        this.logger = new RadarLogger({
            prefix: '[NetworkShield]',
            level: this.options.logLevel.toLowerCase()
        });

        // 初始化文件系统（依赖注入）
        const fs = FileSystemProvider.getFileSystem({
            memory: this.options.useMemoryFS
        });

        // 初始化核心组件
        /**
         * @type {RegistryManager}
         * @readonly
         */
        this.registryManager = getRegistryManager({ fileSystem: fs });

        /**
         * @type {BatchHealthChecker}
         * @readonly
         */
        this.healthChecker = new BatchHealthChecker({
            proxyHost: this.options.proxyHost,
            registryManager: this.registryManager
        });

        /**
         * @type {CircuitBreakerRegistry}
         * @readonly
         */
        this.circuitBreakerRegistry = new CircuitBreakerRegistry(
            { failureThreshold: this.options.maxConsecutiveFailures },
            this.logger
        );

        /**
         * @type {LRUSessionManager}
         * @readonly
         */
        this.sessionManager = new LRUSessionManager({
            sessionTimeoutMinutes: this.options.sessionTimeoutMinutes,
            lruMaxSize: this.options.lruMaxSize,
            maxSessions: this.options.maxSessions,
            logger: this.logger
        });

        // 运行状态
        /**
         * @type {boolean}
         * @private
         */
        this._isInitialized = false;

        /**
         * @type {NodeJS.Timeout|null}
         * @private
         */
        this._healthCheckInterval = null;

        this._logBanner();
    }

    // ========================================================================
    // PUBLIC METHODS
    // ========================================================================

    /**
     * 初始化 NetworkShield
     *
     * @returns {Promise<NetworkShieldStatus>} 初始化结果
     * @throws {NetworkShieldError} 健康检查失败
     *
     * @typedef {Object} NetworkShieldStatus
     * @property {boolean} enabled - 是否启用代理
     * @property {boolean} initialized - 是否已初始化
     * @property {Object} nodes - 节点统计
     * @property {Object} sessions - 会话统计
     * @property {Object} requests - 请求统计
     * @property {number} avg_health_score - 平均健康分数
     */
    async initialize() {
        if (this._isInitialized) {
            this.logger.warn('[NetworkShield] Already initialized');
            return this.getStatus();
        }

        this.logger.info('[NetworkShield] 🚀 Initializing...');

        // 尊重 PROXY_ENABLED 环境变量
        if (process.env.PROXY_ENABLED === 'false') {
            this.options.enabled = false;
            this.logger.warn('[NetworkShield] ⚠️  Proxy DISABLED via environment (PROXY_ENABLED=false)');
            this._isInitialized = true;
            return this.getStatus();
        }

        try {
            // 步骤 1: 执行初始健康检查
            this.logger.info('[NetworkShield] 🔍 Running initial health check...');
            const healthSummary = await this.healthChecker.runFullHealthCheck();

            // 步骤 2: 输出初始化摘要
            this.logger.info(
                `[NetworkShield] ✅ Health Check Complete: ${healthSummary.healthy}/${healthSummary.total} nodes healthy`
            );

            // 步骤 3: 启动定期健康检查
            this._startPeriodicHealthCheck();

            this._isInitialized = true;

            const status = this.getStatus();
            this._logInitializationSuccess(status);

            return status;
        } catch (error) {
            this.logger.error(`[NetworkShield] ❌ Initialization failed: ${error.message}`);
            throw error;
        }
    }

    /**
     * 获取下一个健康的代理节点（Session 绑定）
     *
     * @param {string} [sessionId=null] - 会话 ID（可选，用于 Session 绑定）
     * @returns {Promise<ProxyAssignment|null>} 代理分配结果，无可用代理返回 null
     * @throws {NetworkShieldError} 无可用代理
     *
     * @typedef {Object} ProxyAssignment
     * @property {string} sessionId - 会话 ID
     * @property {number} port - 代理端口
     * @property {string} url - 代理 URL
     * @property {string} id - 节点 ID
     * @property {number} health_score - 健康分数
     * @property {string|null} ip_address - IP 地址
     */
    async getNextHealthyProxy(sessionId = null) {
        if (!this._isInitialized) {
            await this.initialize();
        }

        if (!this.options.enabled) {
            this.logger.info('[NetworkShield] Proxy is DISABLED');
            return null;
        }

        // 如果有 sessionId 且已有绑定会话，返回绑定的端口
        if (sessionId) {
            const existingSession = this.sessionManager.getSession(sessionId);
            if (existingSession && existingSession.isActive && !existingSession.isExpired()) {
                existingSession.refresh();
                const port = existingSession.port;
                const node = this.registryManager.getNode(port);

                if (node && node.status === 'active') {
                    this.logger.debug(
                        `[NetworkShield] Reusing existing session ${sessionId} -> Port ${port}`
                    );
                    return this._formatProxyResult(node, sessionId);
                }
            }
        }

        // 获取可用节点（排除已占用端口）
        const allPorts = this.registryManager.getAvailableNodes().map(n => n.port);
        const availablePorts = this.sessionManager.getAvailablePorts(allPorts);

        if (availablePorts.length === 0) {
            this.logger.error('[NetworkShield] No available proxy nodes!');
            throw noProxyAvailable(
                this.registryManager.getStatistics().total_nodes,
                this.registryManager.getStatistics().active_nodes
            );
        }

        // 选择健康分数最高的端口
        const nodes = this.registryManager.getAvailableNodes().filter(n =>
            availablePorts.includes(n.port)
        );

        // 按健康分数排序，选择最高的
        nodes.sort((a, b) => b.health_score - a.health_score);
        const selectedNode = nodes[0];

        // 创建会话绑定
        let finalSessionId = sessionId;
        if (!finalSessionId) {
            finalSessionId = `SESSION-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        }

        try {
            const session = await this.sessionManager.createSession(selectedNode.port, {
                createdAt: new Date().toISOString()
            });

            this.logger.info(
                `[NetworkShield] Assigned Clean IP (Port ${selectedNode.port}, ` +
                `Score: ${selectedNode.health_score}) to Session ${finalSessionId}`
            );

            return this._formatProxyResult(selectedNode, finalSessionId);
        } catch (error) {
            this.logger.error(`[NetworkShield] Failed to create session: ${error.message}`);
            return null;
        }
    }

    /**
     * 标记代理成功
     *
     * @param {number} port - 代理端口
     * @param {number} [latency=0] - 延迟（毫秒）
     * @returns {Promise<void>}
     */
    async markProxySuccess(port, latency = 0) {
        if (!port) return;

        try {
            await this.registryManager.markNodeSuccess(port, latency);

            // 更新熔断器
            const breaker = this.circuitBreakerRegistry.getBreaker(port);
            breaker.recordSuccess();

            this.logger.debug(`[NetworkShield] Port ${port} marked as SUCCESS`);
        } catch (error) {
            this.logger.error(`[NetworkShield] Failed to mark success: ${error.message}`);
        }
    }

    /**
     * 标记代理失败
     *
     * @param {number} port - 代理端口
     * @param {string} [reason='Unknown'] - 失败原因
     * @returns {Promise<void>}
     */
    async markProxyFailed(port, reason = 'Unknown') {
        if (!port) return;

        try {
            await this.registryManager.markNodeFailed(port, reason, this.options.cooldownMinutes);

            // 更新熔断器
            const breaker = this.circuitBreakerRegistry.getBreaker(port);
            breaker.recordFailure(new Error(reason));

            this.logger.warn(`[NetworkShield] Port ${port} marked as FAILED: ${reason}`);
        } catch (error) {
            this.logger.error(`[NetworkShield] Failed to mark failure: ${error.message}`);
        }
    }

    /**
     * 释放会话
     *
     * @param {string} sessionId - 会话 ID
     * @returns {void}
     */
    releaseSession(sessionId) {
        if (!sessionId) return;

        try {
            this.sessionManager.releaseSession(sessionId);
            this.logger.debug(`[NetworkShield] Session ${sessionId} released`);
        } catch (error) {
            this.logger.error(`[NetworkShield] Failed to release session: ${error.message}`);
        }
    }

    /**
     * 获取状态摘要
     *
     * @returns {NetworkShieldStatus} 状态摘要
     */
    getStatus() {
        const stats = this.registryManager.getStatistics();
        const sessionStats = this.sessionManager.getStatistics();
        const availableNodes = this.registryManager.getAvailableNodes();

        return {
            enabled: this.options.enabled,
            initialized: this._isInitialized,
            nodes: {
                total: stats.total_nodes,
                active: stats.active_nodes,
                cooled: stats.cooled_nodes,
                available: availableNodes.length
            },
            sessions: sessionStats,
            requests: {
                total: stats.total_requests,
                successful: stats.successful_requests,
                failed: stats.failed_requests
            },
            avg_health_score: stats.avg_health_score
        };
    }

    /**
     * 获取详细状态（用于调试）
     *
     * @returns {Object} 详细状态
     */
    getDetailedStatus() {
        const registry = this.registryManager.getRegistry();
        const status = this.getStatus();

        return {
            ...status,
            config: {
                proxy_host: this.options.proxyHost,
                port_range: this.options.portRange,
                protocol: this.options.protocol,
                cooldown_minutes: this.options.cooldownMinutes,
                session_timeout_minutes: this.options.sessionTimeoutMinutes
            },
            nodes: registry.nodes.map(n => ({
                port: n.port,
                status: n.status,
                health_score: n.health_score,
                consecutive_failures: n.consecutive_failures,
                cooldown_until: n.cooldown_until,
                ip_address: n.ip_address,
                avg_latency_ms: n.avg_latency_ms
            })),
            circuit_breakers: this.circuitBreakerRegistry.getAllStates()
        };
    }

    /**
     * 手动触发健康检查
     *
     * @returns {Promise<Object>} 健康检查结果
     */
    async runHealthCheck() {
        this.logger.info('[NetworkShield] Manual health check triggered...');
        return this.healthChecker.runFullHealthCheck();
    }

    /**
     * 重置所有节点状态
     *
     * @returns {Promise<NetworkShieldStatus>} 重置后的状态
     */
    async resetAllNodes() {
        this.logger.info('[NetworkShield] Resetting all nodes...');
        await this.registryManager.resetAllNodes();
        this.circuitBreakerRegistry.resetAll();
        return this.getStatus();
    }

    /**
     * 关闭 NetworkShield
     *
     * @returns {void}
     */
    shutdown() {
        this.logger.info('[NetworkShield] Shutting down...');

        if (this._healthCheckInterval) {
            clearInterval(this._healthCheckInterval);
            this._healthCheckInterval = null;
        }

        this.sessionManager.shutdown();
        this.circuitBreakerRegistry.shutdown();

        this.logger.info('[NetworkShield] Shutdown complete');
    }

    // ========================================================================
    // PRIVATE METHODS
    // ========================================================================

    /**
     * 启动定期健康检查
     * @private
     */
    _startPeriodicHealthCheck() {
        if (this._healthCheckInterval) {
            clearInterval(this._healthCheckInterval);
        }

        this._healthCheckInterval = setInterval(async () => {
            try {
                await this.healthChecker.runFullHealthCheck();
            } catch (error) {
                this.logger.error(`[NetworkShield] Periodic health check failed: ${error.message}`);
            }
        }, this.options.healthCheckInterval);

        this.logger.debug(
            `[NetworkShield] Periodic health check started ` +
            `(interval: ${this.options.healthCheckInterval}ms)`
        );
    }

    /**
     * 格式化代理结果
     * @private
     * @param {Object} node - 节点信息
     * @param {string} sessionId - 会话 ID
     * @returns {ProxyAssignment} 格式化的代理结果
     */
    _formatProxyResult(node, sessionId) {
        return {
            sessionId,
            port: node.port,
            url: `${this.options.protocol}://${this.options.proxyHost}:${node.port}`,
            id: node.id,
            health_score: node.health_score,
            ip_address: node.ip_address
        };
    }

    /**
     * 记录启动横幅
     * @private
     */
    _logBanner() {
        this.logger.info('');
        this.logger.info('╔══════════════════════════════════════════════════════════════╗');
        this.logger.info('║     [Genesis.NetworkShield] V1.1.0 - Production Grade         ║');
        this.logger.info('║            Cross-Language Proxy Management System           ║');
        this.logger.info('╚══════════════════════════════════════════════════════════════╝');
        this.logger.info('');
    }

    /**
     * 记录初始化成功
     * @private
     * @param {NetworkShieldStatus} status - 状态信息
     */
    _logInitializationSuccess(status) {
        this.logger.info('');
        this.logger.info('╔══════════════════════════════════════════════════════════════╗');
        this.logger.info('║           INFRASTRUCTURE SECURED - NETWORK SHIELD            ║');
        this.logger.info('╠══════════════════════════════════════════════════════════════╣');
        this.logger.info(`║  Nodes Managed:        ${String(status.nodes.total).padStart(20)} ║`);
        this.logger.info(`║  Active Nodes:         ${String(status.nodes.active).padStart(20)} ║`);
        this.logger.info(`║  Available:            ${String(status.nodes.available).padStart(20)} ║`);
        this.logger.info(`║  Avg Health Score:     ${String(status.avg_health_score.toFixed(1)).padStart(20)} ║`);
        this.logger.info(`║  Auto-Failover:        ${String('ACTIVE').padStart(20)} ║`);
        this.logger.info(`║  LRU Sessions:          ${String(status.sessions.lru?.size || 'N/A').padStart(20)} ║`);
        this.logger.info('╚══════════════════════════════════════════════════════════════╝');
        this.logger.info('');
        this.logger.info('[Genesis.NetworkShield] System is now PRODUCTION-GRADE ready.');
        this.logger.info('');
    }
}

// ============================================================================
// SINGLETON INSTANCE
// ============================================================================

let _shieldInstance = null;

/**
 * 获取 NetworkShield 单例
 *
 * @param {NetworkShieldConfig} [options] - 配置选项
 * @returns {NetworkShield} NetworkShield 实例
 */
function getNetworkShield(options) {
    if (!_shieldInstance) {
        _shieldInstance = new NetworkShield(options);
    }
    return _shieldInstance;
}

/**
 * 重置单例（用于测试）
 *
 * @returns {void}
 */
function resetSingleton() {
    if (_shieldInstance) {
        _shieldInstance.shutdown();
        _shieldInstance = null;
    }
}

module.exports = {
    NetworkShield,
    getNetworkShield,
    resetSingleton,
    DEFAULT_CONFIG
};
