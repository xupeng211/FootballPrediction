/**
 * ProxyRegistry - 代理端口注册表
 * ==============================================
 *
 * 负责:
 * - 22 个代理端口的分配与释放
 * - 端口健康检查
 * - 故障切换与轮换
 * @module core/network/ProxyRegistry
 * @version V174.0.0
 */

'use strict';

/**
 * ProxyRegistry - 代理端口注册表
 */
class ProxyRegistry {
    /**
     * @param {object} config - 配置选项
     * @param {number[]} config.ports - 代理端口列表
     * @param {string} config.host - 代理服务器地址
     */
    constructor(config = {}) {
        this.ports = config.ports || Array.from({ length: 22 }, (_, i) => 7890 + i);
        this.host = config.host || '172.25.16.1';

        // 状态
        this.assignments = new Map();   // workerId -> port
        this.available = [...this.ports];
        this.healthStatus = new Map();  // port -> { healthy, lastCheck, failures }

        // 统计
        this.stats = {
            assigned: 0,
            released: 0,
            failedOvers: 0
        };
    }

    /**
     * 为 Worker 分配端口
     * @param {number} workerId - Worker ID
     * @returns {number|null} 分配的端口，无可用端口返回 null
     */
    assign(workerId) {
        if (this.available.length === 0) {
            return null;
        }

        const port = this.available.shift();
        this.assignments.set(workerId, port);

        // 初始化健康状态
        if (!this.healthStatus.has(port)) {
            this.healthStatus.set(port, {
                healthy: true,
                lastCheck: Date.now(),
                failures: 0
            });
        }

        this.stats.assigned++;
        return port;
    }

    /**
     * 释放 Worker 的端口
     * @param {number} workerId - Worker ID
     */
    release(workerId) {
        const port = this.assignments.get(workerId);
        if (port) {
            this.assignments.delete(workerId);
            this.available.push(port);
            this.stats.released++;
        }
    }

    /**
     * 获取 Worker 的端口
     * @param {number} workerId - Worker ID
     * @returns {number|undefined}
     */
    getPort(workerId) {
        return this.assignments.get(workerId);
    }

    /**
     * 获取下一个可用端口 (用于故障切换)
     * @param {number} currentPort - 当前端口
     * @returns {number}
     */
    getNextPort(currentPort) {
        const currentIndex = this.ports.indexOf(currentPort);
        const nextIndex = (currentIndex + 1) % this.ports.length;
        return this.ports[nextIndex];
    }

    /**
     * 标记端口为不健康
     * @param {number} port - 端口号
     * @param {string} reason - 原因
     */
    markUnhealthy(port, reason = 'UNKNOWN') {
        const status = this.healthStatus.get(port) || {
            healthy: true,
            lastCheck: Date.now(),
            failures: 0
        };

        status.healthy = false;
        status.failures++;
        status.lastFailure = Date.now();
        status.failureReason = reason;
        this.healthStatus.set(port, status);

        console.log(`⚠️ 代理端口 ${port} 标记为不健康: ${reason}`);
    }

    /**
     * 标记端口为健康
     * @param {number} port - 端口号
     */
    markHealthy(port) {
        const status = this.healthStatus.get(port) || {
            healthy: true,
            lastCheck: Date.now(),
            failures: 0
        };

        status.healthy = true;
        status.lastCheck = Date.now();
        this.healthStatus.set(port, status);
    }

    /**
     * 检查端口是否健康
     * @param {number} port - 端口号
     * @returns {boolean}
     */
    isHealthy(port) {
        const status = this.healthStatus.get(port);
        return status ? status.healthy : true;
    }

    /**
     * 获取代理服务器地址
     * @param {number} port - 端口号
     * @returns {string}
     */
    getServer(port) {
        return `http://${this.host}:${port}`;
    }

    /**
     * 故障切换 - 为 Worker 分配新端口
     * @param {number} workerId - Worker ID
     * @returns {number|null}
     */
    failover(workerId) {
        const currentPort = this.assignments.get(workerId);

        if (currentPort) {
            this.markUnhealthy(currentPort, 'FAILOVER');
            this.release(workerId);
        }

        // 找一个健康的端口
        for (let i = 0; i < this.ports.length; i++) {
            const nextPort = this.assign(workerId);
            if (nextPort && this.isHealthy(nextPort)) {
                this.stats.failedOvers++;
                console.log(`🔄 Worker ${workerId} 故障切换到端口 ${nextPort}`);
                return nextPort;
            }
        }

        return null;
    }

    /**
     * 获取所有端口状态快照
     * @returns {object}
     */
    getSnapshot() {
        const snapshot = {};

        for (const port of this.ports) {
            const workerEntry = [...this.assignments.entries()].find(([, p]) => p === port);
            const status = this.healthStatus.get(port);

            snapshot[port] = {
                status: workerEntry ? 'IN_USE' : 'IDLE',
                workerId: workerEntry ? workerEntry[0] : null,
                healthy: status ? status.healthy : true,
                failures: status ? status.failures : 0
            };
        }

        return snapshot;
    }

    /**
     * 获取统计信息
     * @returns {object}
     */
    getStats() {
        return {
            ...this.stats,
            total: this.ports.length,
            available: this.available.length,
            inUse: this.assignments.size
        };
    }

    /**
     * 重置所有状态
     */
    reset() {
        this.assignments.clear();
        this.available = [...this.ports];
        this.healthStatus.clear();
        this.stats = { assigned: 0, released: 0, failedOvers: 0 };
    }

    /**
     * 打印状态摘要
     */
    printStatus() {
        console.log(`📡 代理池状态: ${this.available.length}/${this.ports.length} 可用`);
        console.log(`   端口范围: ${this.ports[0]} - ${this.ports[this.ports.length - 1]}`);
    }
}

module.exports = {
    ProxyRegistry
};
