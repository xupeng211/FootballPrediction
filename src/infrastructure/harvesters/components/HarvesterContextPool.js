'use strict';

const { ContextPoolManager } = require('../../browser/ContextPoolManager');

/**
 * HarvesterContextPool - 收割器专用 BrowserContext 池
 * ==================================================
 *
 * 在 ContextPoolManager 基础上补齐：
 * - 并发创建去重
 * - 超时 Context 回收
 * - 依赖故障时的全量清池
 */
class HarvesterContextPool extends ContextPoolManager {
    /**
     * @param {object} [config]
     * @param {number} [config.maxUsage=10]
     * @param {number} [config.maxSize=20]
     * @param {number} [config.idleTimeoutMs=0]
     */
    constructor(config = {}) {
        super(config);
        this.config.idleTimeoutMs = config.idleTimeoutMs || 0;
        this._pendingCreates = new Map();
    }

    /**
     * @returns {Map}
     */
    getPool() {
        return this._pool;
    }

    /**
     * @param {Map} pool
     */
    replacePool(pool) {
        this._pool = pool instanceof Map ? pool : new Map();
    }

    /**
     * @returns {object}
     */
    getMutableStats() {
        return this._stats;
    }

    /**
     * @param {number} workerId
     * @returns {boolean}
     */
    isContextValid(workerId) {
        const entry = this.getEntry(workerId);
        if (!entry?.context) {
            return false;
        }

        if (!this.config.idleTimeoutMs || this.config.idleTimeoutMs <= 0) {
            return true;
        }

        return Date.now() - entry.lastAccessTime <= this.config.idleTimeoutMs;
    }

    /**
     * @param {number} workerId
     * @param {object} identity
     * @param {object} deps
     * @returns {Promise<{context: object, isNew: boolean, entry: object}>}
     */
    async getOrCreate(workerId, identity, deps) {
        await this.reapExpiredContexts();

        if (this._pendingCreates.has(workerId)) {
            return this._pendingCreates.get(workerId);
        }

        const entry = this.getEntry(workerId);
        const currentPort = identity?.proxy?.port;
        const invalidEntry = entry && !this.isContextValid(workerId);
        const { needsRebuild, reason } = this._shouldRebuild(entry, currentPort);

        if (!invalidEntry && !needsRebuild) {
            return super.getOrCreate(workerId, identity, deps);
        }

        const createPromise = (async () => {
            if (invalidEntry) {
                await this.closeWorkerContext(workerId, 'IDLE_TIMEOUT');
            }

            return super.getOrCreate(workerId, identity, deps);
        })();

        this._pendingCreates.set(workerId, createPromise);

        try {
            return await createPromise;
        } finally {
            this._pendingCreates.delete(workerId);
        }
    }

    /**
     * 回收超时 Context。
     * @returns {Promise<number>} 清理数量
     */
    async reapExpiredContexts() {
        if (!this.config.idleTimeoutMs || this.config.idleTimeoutMs <= 0) {
            return 0;
        }

        const now = Date.now();
        const expiredWorkerIds = [];

        for (const [workerId, entry] of this._pool) {
            if (!entry?.context) {
                expiredWorkerIds.push(workerId);
                continue;
            }

            if (now - entry.lastAccessTime > this.config.idleTimeoutMs) {
                expiredWorkerIds.push(workerId);
            }
        }

        for (const workerId of expiredWorkerIds) {
            await this.closeWorkerContext(workerId, 'IDLE_TIMEOUT');
        }

        return expiredWorkerIds.length;
    }

    /**
     * @param {number} workerId
     * @param {string} [reason]
     * @returns {Promise<boolean>}
     */
    async closeWorkerContext(workerId, reason = '') {
        const entry = this.getEntry(workerId);
        if (!entry?.context) {
            this._pool.delete(workerId);
            return false;
        }

        await this._safeClose(entry.context);
        this._pool.delete(workerId);

        if (reason) {
            this._logInfo(`🧹 [W${workerId}] Context 已关闭 (${reason})`);
        }

        return true;
    }

    /**
     * 向旧接口暴露 LRU 淘汰。
     * @returns {Promise<void>}
     */
    async evictLRU() {
        await this._evictLRU();
    }

    /**
     * 清理所有 Context。
     * @returns {Promise<void>}
     */
    async closeAllContexts() {
        await this.cleanup();
        this._pendingCreates.clear();
    }

    /**
     * 依赖故障时的保护性清理。
     * @param {string} reason
     * @returns {Promise<boolean>}
     */
    async handleDependencyFailure(reason) {
        if (!reason) {
            return false;
        }

        const normalized = String(reason).toLowerCase();
        if (!normalized.includes('db') && !normalized.includes('database')) {
            return false;
        }

        await this.closeAllContexts();
        return true;
    }
}

module.exports = {
    HarvesterContextPool,
};
