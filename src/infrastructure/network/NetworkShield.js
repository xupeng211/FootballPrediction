/**
 * NetworkShield - V4.46 网络护盾
 * ========================================
 *
 * 22 节点代理池管理、熔断保护、Session Stickiness
 *
 * @module infrastructure/network/NetworkShield
 * @version V4.46.0
 */

'use strict';

const { logger } = require('../utils/Logger');
const FactoryConfig = require('../../../config/factory_config');

/**
 * NetworkShield - 网络护盾
 *
 * 功能:
 * 1. 代理池管理 (22 节点)
 * 2. 熔断器保护
 * 3. Session Stickiness (Worker 与端口绑定)
 */
class NetworkShield {
    /**
     * @param {Object} config - 配置选项
     * @param {Array} [config.proxyNodes] - 代理节点列表
     */
    constructor(config = {}) {
        this.logger = logger;
        this.proxyNodes = config.proxyNodes || this._getDefaultProxyNodes();
        this.circuitBreaker = new Map(); // 熔断器状态
        this.portAssignments = new Map(); // Worker -> Port 绑定
        this.logger.info('V4.46 NetworkShield 启动：22 节点代理池模式');
    }

    /**
     * 获取默认代理节点配置
     * @returns {Array} 代理节点列表
     * @private
     */
    _getDefaultProxyNodes() {
        const host = process.env.PROXY_HOST || '172.25.16.1';
        const nodes = [];

        // 22 个代理节点 (端口 7890-7911)
        for (let port = 7890; port <= 7911; port++) {
            nodes.push({
                host,
                port,
                url: `http://${host}:${port}`,
                status: 'active',
                failureCount: 0,
                lastFailure: null
            });
        }

        return nodes;
    }

    /**
     * 为 Worker 分配代理端口 (Session Stickiness)
     * @param {number} workerId - Worker ID
     * @returns {Object} 代理配置
     */
    assignPort(workerId) {
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
            this.logger.warn('所有代理节点已熔断，尝试重置...');
            this._resetCircuitBreaker();
            return this.assignPort(workerId);
        }

        const nodeIndex = workerId % activeNodes.length;
        const selectedNode = activeNodes[nodeIndex];

        this.portAssignments.set(workerId, selectedNode.port);
        this.logger.debug(`Worker ${workerId} 绑定到端口 ${selectedNode.port}`);

        return { host: selectedNode.host, port: selectedNode.port, url: selectedNode.url };
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
     * @param {number} workerId - Worker ID
     * @param {number} oldPort - 旧端口
     * @returns {Object} 新的代理配置
     */
    forceReassign(workerId, oldPort) {
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
            this._resetCircuitBreaker();
            return this.assignPort(workerId);
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
     * 获取代理池状态
     * @returns {Object} 代理池状态
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
     * @param {Object} [options] - 上下文选项
     * @returns {Promise<import('playwright').BrowserContext>}
     */
    async getNewContext(browser, options = {}) {
        return await browser.newContext({
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
 * @param {Object} [config] - 配置选项
 * @returns {NetworkShield}
 */
function getNetworkShield(config = {}) {
    if (!networkShieldInstance) {
        networkShieldInstance = new NetworkShield(config);
    }
    return networkShieldInstance;
}

module.exports = { NetworkShield, getNetworkShield };
