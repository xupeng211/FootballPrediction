/**
 * NetworkShield - V4.46.1 网络护盾
 * ========================================
 *
 * 22 节点代理池管理、熔断保护、Session Stickiness
 *
 * V4.46.1 修复：
 * - 添加 MAX_GLOBAL_RETRIES 防止递归死循环
 * - 全局熔断时抛出 CIRCUIT_BREAKER_OPEN 错误
 * @module infrastructure/network/NetworkShield
 * @version V4.46.1
 */

'use strict';

const { logger } = require('../utils/Logger');
const FactoryConfig = require('../../../config/factory_config');
const { ProxyProvider } = require('./ProxyProvider');

// ============================================================================
// V4.46.1: 全局常量 - 防止无限递归
// ============================================================================

/** 全局熔断最大重试次数 */
const MAX_GLOBAL_RETRIES = 3;

/** 自定义错误：熔断器开启 */
class CircuitBreakerOpenError extends Error {
    /**
     *
     * @param message
     */
    constructor(message = '所有代理节点不可用，全局熔断已开启') {
        super(message);
        this.name = 'CircuitBreakerOpenError';
        this.code = 'CIRCUIT_BREAKER_OPEN';
    }
}

/**
 * NetworkShield - 网络护盾
 *
 * 功能:
 * 1. 代理池管理 (22 节点)
 * 2. 熔断器保护
 * 3. Session Stickiness (Worker 与端口绑定)
 * 4. V4.46.1: 全局熔断保护
 */
class NetworkShield {
    /**
     * @param {object} config - 配置选项
     * @param {Array} [config.proxyNodes] - 代理节点列表
     */
    constructor(config = {}) {
        this.logger = logger;
        this.proxyNodes = config.proxyNodes || this._getDefaultProxyNodes();
        this.circuitBreaker = new Map(); // 熔断器状态
        this.portAssignments = new Map(); // Worker -> Port 绑定

        // V4.46.1: 全局重试计数器
        this.globalRetryCount = 0;
        this.lastGlobalResetTime = 0;

        this.logger.info('V4.46.1 NetworkShield 启动：22 节点代理池模式 + 全局熔断保护');
    }

    /**
     * 获取默认代理节点配置
     * @returns {Array} 代理节点列表
     * @private
     */
    _getDefaultProxyNodes() {
        const host = ProxyProvider.resolveHost();
        const nodes = [];

        for (const port of ProxyProvider.resolvePorts()) {
            nodes.push({
                host,
                port,
                url: ProxyProvider.buildServer(port, { host }),
                status: 'active',
                failureCount: 0,
                lastFailure: null
            });
        }

        return nodes;
    }

    /**
     * 为 Worker 分配代理端口 (Session Stickiness)
     * V4.46.1: 添加全局重试限制，防止无限递归
     * @param {number} workerId - Worker ID
     * @param {number} [retryCount] - 内部重试计数器 (递归保护)
     * @returns {object} 代理配置
     * @throws {CircuitBreakerOpenError} 当全局熔断时抛出
     */
    assignPort(workerId, retryCount = 0) {
        // 检查是否已有绑定
        if (this.portAssignments.has(workerId)) {
            const port = this.portAssignments.get(workerId);
            const node = this.proxyNodes.find(n => n.port === port);
            if (node && node.status === 'active') {
                return { host: node.host, port: node.port, url: node.url };
            }
        }

        // 分配新端口 (轮询 + 健康检查)
        const activeNodes = this.proxyNodes.filter(n => n.status === 'active');

        if (activeNodes.length === 0) {
            // V4.46.1: 全局熔断保护 - 限制最大重试次数
            if (retryCount >= MAX_GLOBAL_RETRIES) {
                const error = new CircuitBreakerOpenError(
                    `全局熔断：所有代理节点不可用 (已重试 ${retryCount} 次)`
                );
                this.logger.error(`🚨 ${error.message}`);

                // 记录到指标系统
                this._recordGlobalCircuitBreakerOpen();

                throw error;
            }

            // V4.46.1: 检查全局冷却窗口 - 如果 60 秒内已经重置过，直接报错
            const now = Date.now();
            const GLOBAL_COOLDOWN_MS = 60000;
            if (this.lastGlobalResetTime > 0 && (now - this.lastGlobalResetTime) < GLOBAL_COOLDOWN_MS) {
                const error = new CircuitBreakerOpenError(
                    `全局冷却中：60 秒内已重置过熔断器，拒绝重复重置`
                );
                this.logger.error(`🚨 ${error.message}`);
                this._recordGlobalCircuitBreakerOpen();
                throw error;
            }

            this.logger.warn(`所有代理节点已熔断，尝试重置 (${retryCount + 1}/${MAX_GLOBAL_RETRIES})...`);
            this._resetCircuitBreaker();

            // 递归调用时传递重试计数
            return this.assignPort(workerId, retryCount + 1);
        }

        // 成功分配，重置全局重试计数器
        if (retryCount > 0) {
            this.globalRetryCount = 0;
        }

        const nodeIndex = workerId % activeNodes.length;
        const selectedNode = activeNodes[nodeIndex];

        this.portAssignments.set(workerId, selectedNode.port);
        this.logger.debug(`Worker ${workerId} 绑定到端口 ${selectedNode.port}`);

        return { host: selectedNode.host, port: selectedNode.port, url: selectedNode.url };
    }

    /**
     * V4.51: 为 NetworkManager 提供兼容接口
     * 包装 assignPort 方法返回统一格式
     * @param {string} sessionId - 会话ID
     * @returns {Promise<object>} 代理配置
     */
    async getNextHealthyProxy(sessionId) {
        const workerId = parseInt(sessionId.replace('WORKER-', '')) || 1;
        const assignment = this.assignPort(workerId);
        return {
            sessionId,
            port: assignment.port,
            url: assignment.url
        };
    }

    /**
     * 标记代理成功
     * @param {number} port - 代理端口
     */
    markSuccess(port) {
        const node = this.proxyNodes.find(n => n.port === port);
        if (node) {
            node.failureCount = 0;
            node.status = 'active';
        }
    }

    /**
     * 标记代理失败
     * @param {number} port - 代理端口
     * @param {string} [reason] - 失败原因
     */
    markFailed(port, reason = 'unknown') {
        const node = this.proxyNodes.find(n => n.port === port);
        if (node) {
            node.failureCount++;
            node.lastFailure = { time: Date.now(), reason };

            // 熔断：连续 5 次失败触发 60 秒冷却
            if (node.failureCount >= 5) {
                node.status = 'cooldown';
                this.logger.warn(`代理端口 ${port} 熔断 (连续失败 ${node.failureCount} 次)`);

                // 60 秒后自动恢复
                setTimeout(() => {
                    node.status = 'active';
                    node.failureCount = 0;
                    this.logger.info(`代理端口 ${port} 已恢复`);
                }, 60000);
            }
        }
    }

    /**
     * 强制重新分配端口 (避障)
     * V4.46.1: 添加全局熔断保护
     * @param {number} workerId - Worker ID
     * @param {number} oldPort - 旧端口
     * @param {number} [retryCount] - 内部重试计数器 (递归保护)
     * @returns {object} 新的代理配置
     * @throws {CircuitBreakerOpenError} 当全局熔断时抛出
     */
    forceReassign(workerId, oldPort, retryCount = 0) {
        this.logger.warn(`Worker ${workerId} 强制切换端口 (旧端口: ${oldPort})`);

        // 清除旧绑定
        this.portAssignments.delete(workerId);

        // 标记旧端口失败
        this.markFailed(oldPort, 'force_reassign');

        // 分配新端口 (跳过旧端口)
        const availableNodes = this.proxyNodes.filter(
            n => n.status === 'active' && n.port !== oldPort
        );

        if (availableNodes.length === 0) {
            // V4.46.1: 全局熔断保护 - 限制最大重试次数
            if (retryCount >= MAX_GLOBAL_RETRIES) {
                const error = new CircuitBreakerOpenError(
                    `强制切换失败：无可用代理节点 (已重试 ${retryCount} 次)`
                );
                this.logger.error(`🚨 ${error.message}`);
                this._recordGlobalCircuitBreakerOpen();
                throw error;
            }

            // V4.46.1: 检查全局冷却窗口
            const now = Date.now();
            const GLOBAL_COOLDOWN_MS = 60000;
            if (this.lastGlobalResetTime > 0 && (now - this.lastGlobalResetTime) < GLOBAL_COOLDOWN_MS) {
                const error = new CircuitBreakerOpenError(
                    `全局冷却中：60 秒内已重置过熔断器，拒绝重复重置`
                );
                this.logger.error(`🚨 ${error.message}`);
                this._recordGlobalCircuitBreakerOpen();
                throw error;
            }

            this.logger.warn(`无可用节点，重置熔断器 (${retryCount + 1}/${MAX_GLOBAL_RETRIES})...`);
            this._resetCircuitBreaker();

            // 递归调用时传递重试计数
            return this.assignPort(workerId, retryCount + 1);
        }

        const nodeIndex = Math.floor(Math.random() * availableNodes.length);
        const selectedNode = availableNodes[nodeIndex];

        this.portAssignments.set(workerId, selectedNode.port);
        this.logger.info(`Worker ${workerId} 新端口: ${selectedNode.port}`);

        return { host: selectedNode.host, port: selectedNode.port, url: selectedNode.url };
    }

    /**
     * 重置熔断器
     * @private
     */
    _resetCircuitBreaker() {
        this.logger.warn('重置所有代理节点状态');
        for (const node of this.proxyNodes) {
            node.status = 'active';
            node.failureCount = 0;
        }
    }

    /**
     * 记录全局熔断开启事件
     * V4.46.1: 供 MetricsClient 捕获
     * @private
     */
    _recordGlobalCircuitBreakerOpen() {
        this.globalRetryCount++;
        this.lastGlobalResetTime = Date.now();

        // 发送熔断事件 (供外部监听)
        this.logger.error({
            event: 'GLOBAL_CIRCUIT_BREAKER_OPEN',
            code: 'CIRCUIT_BREAKER_OPEN',
            globalRetryCount: this.globalRetryCount,
            timestamp: new Date().toISOString(),
            poolStatus: this.getStatus()
        });
    }

    /**
     * 获取代理池状态
     * @returns {object} 代理池状态
     */
    getStatus() {
        const active = this.proxyNodes.filter(n => n.status === 'active').length;
        const cooldown = this.proxyNodes.filter(n => n.status === 'cooldown').length;

        return {
            total: this.proxyNodes.length,
            active,
            cooldown,
            assignments: Object.fromEntries(this.portAssignments)
        };
    }

    /**
     * 保护页面 (注入隐身 Headers)
     * @param {import('playwright').Page} page - Playwright Page 对象
     */
    async protect(page) {
        await page.setExtraHTTPHeaders({
            'Accept-Language': 'en-US,en;q=0.9',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1'
        });
    }

    /**
     * 创建受保护的浏览器上下文
     * @param {import('playwright').Browser} browser - Playwright Browser 对象
     * @param {object} [options] - 上下文选项
     * @returns {Promise<import('playwright').BrowserContext>}
     */
    async getNewContext(browser, options = {}) {
        return browser.newContext({
            viewport: { width: 1920, height: 1080 },
            userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            ...options
        });
    }
}

// ============================================================================
// 单例工厂
// ============================================================================

let networkShieldInstance = null;

/**
 * 获取 NetworkShield 单例
 * @param {object} [config] - 配置选项
 * @returns {NetworkShield}
 */
function getNetworkShield(config = {}) {
    if (!networkShieldInstance) {
        networkShieldInstance = new NetworkShield(config);
    }
    return networkShieldInstance;
}

module.exports = { NetworkShield, getNetworkShield };
