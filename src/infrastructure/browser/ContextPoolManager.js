/**
 * ContextPoolManager - 浏览器 Context 池管理器
 * ============================================
 *
 * 管理 BrowserContext 的复用、淘汰和清理。
 * 从 AbstractHarvester 剥离的工业级组件。
 *
 * V4.46.3 HYPER-DRIVE: Browser Context Pooling
 * V4.46.5 HARDENING: LRU 淘汰机制防止内存泄漏
 *
 * @module infrastructure/browser/ContextPoolManager
 * @version V1.0.0
 */

'use strict';

// ============================================================================
// ContextPoolManager - Context 池管理类
// ============================================================================

class ContextPoolManager {
    /**
     * 创建 ContextPoolManager 实例
     * @param {Object} [config={}] - 配置选项
     * @param {number} [config.maxUsage=10] - 每个 Context 最大复用次数
     * @param {number} [config.maxSize=20] - 池子最大容量
     */
    constructor(config = {}) {
        this.config = {
            maxUsage: config.maxUsage || 10,
            maxSize: config.maxSize || 20,
            ...config
        };

        // Context 池: workerId -> { context, usageCount, lastPort, lastAccessTime, ... }
        this._pool = new Map();

        // 统计数据
        this._stats = {
            totalCreations: 0,
            totalReuses: 0,
            totalEvictions: 0
        };
    }

    // ========================================================================
    // 核心方法
    // ========================================================================

    /**
     * 获取或创建 BrowserContext
     * @param {number} workerId - Worker ID
     * @param {Object} identity - Worker 身份信息
     * @param {Object} deps - 依赖注入
     * @param {Object} deps.browserFactory - BrowserFactory 实例
     * @param {Object} deps.networkManager - NetworkManager 实例
     * @returns {Promise<{context: BrowserContext, isNew: boolean, entry: Object}>}
     */
    async getOrCreate(workerId, identity, deps) {
        const entry = this._pool.get(workerId);
        const currentPort = identity.proxy.port;

        // 检查是否需要重建
        const { needsRebuild, reason } = this._shouldRebuild(entry, currentPort);

        if (needsRebuild) {
            return await this._createNewContext(workerId, identity, deps, reason, entry);
        }

        // 复用现有 context
        return this._reuseContext(workerId, currentPort);
    }

    /**
     * 判断是否需要重建 Context
     * @param {Object} entry - 池条目
     * @param {number} currentPort - 当前端口
     * @returns {{needsRebuild: boolean, reason: string}}
     * @private
     */
    _shouldRebuild(entry, currentPort) {
        if (!entry) {
            return { needsRebuild: true, reason: 'NEW_WORKER' };
        }

        if (entry.usageCount >= this.config.maxUsage) {
            return { needsRebuild: true, reason: `MAX_USAGE(${entry.usageCount}/${this.config.maxUsage})` };
        }

        if (entry.lastPort !== currentPort) {
            return { needsRebuild: true, reason: `PORT_CHANGE(${entry.lastPort}→${currentPort})` };
        }

        return { needsRebuild: false, reason: '' };
    }

    /**
     * 创建新 Context
     * @private
     */
    async _createNewContext(workerId, identity, deps, reason, oldEntry) {
        // LRU 淘汰检查
        await this._evictLRU();

        // 关闭旧 context
        if (oldEntry?.context) {
            await this._safeClose(oldEntry.context);
        }

        // 创建新 context
        const context = await deps.browserFactory.createContext(identity);

        // Cookie 热加载
        let cookieLoaded = false;
        if (deps.networkManager) {
            cookieLoaded = await deps.networkManager.loadSessionToContext(context, identity.proxy.port);
        }
        if (!cookieLoaded) {
            cookieLoaded = await deps.browserFactory.loadBrowserStateCookies(context);
        }

        const now = Date.now();
        const newEntry = {
            context,
            usageCount: 0,
            lastPort: identity.proxy.port,
            cookieLoaded,
            createdAt: now,
            lastAccessTime: now
        };

        this._pool.set(workerId, newEntry);
        this._stats.totalCreations++;

        console.log(`🔄 [W${workerId}] Context 创建: ${reason} | Port ${identity.proxy.port} | Cookie=${cookieLoaded} | Pool=${this._pool.size}/${this.config.maxSize}`);

        return { context, isNew: true, entry: newEntry };
    }

    /**
     * 复用现有 Context
     * @private
     */
    _reuseContext(workerId, currentPort) {
        const entry = this._pool.get(workerId);
        entry.usageCount++;
        entry.lastAccessTime = Date.now();
        this._stats.totalReuses++;

        console.log(`♻️  [W${workerId}] Context 复用: ${entry.usageCount}/${this.config.maxUsage} | Port ${currentPort}`);

        return { context: entry.context, isNew: false, entry };
    }

    /**
     * 清理指定 Worker 的 Cookies（403 逃逸）
     * @param {number} workerId - Worker ID
     * @returns {Promise<boolean>} 是否成功
     */
    async clearCookies(workerId) {
        const entry = this._pool.get(workerId);
        if (entry?.context) {
            try {
                await entry.context.clearCookies();
                entry.usageCount = 0;  // 重置计数
                console.log(`🧹 [W${workerId}] 403 逃逸: Cookies 已清理`);
                return true;
            } catch (e) {
                console.log(`⚠️  [W${workerId}] 403 逃逸失败: ${e.message}`);
                return false;
            }
        }
        return false;
    }

    /**
     * 关闭指定 Worker 的 Context
     * @param {number} workerId - Worker ID
     */
    async closeWorkerContext(workerId) {
        const entry = this._pool.get(workerId);
        if (entry?.context) {
            await this._safeClose(entry.context);
            this._pool.delete(workerId);
        }
    }

    /**
     * LRU 淘汰 - 清理最久未使用的 Context
     * @private
     */
    async _evictLRU() {
        // V4.51.1: 修复淘汰条件，当池已满时触发淘汰
        if (this._pool.size < this.config.maxSize) {
            return;
        }

        // 找到最久未使用的条目
        let oldestEntry = null;
        let oldestWorkerId = null;
        let oldestTime = Infinity;

        for (const [workerId, entry] of this._pool) {
            if (entry.lastAccessTime < oldestTime) {
                oldestTime = entry.lastAccessTime;
                oldestEntry = entry;
                oldestWorkerId = workerId;
            }
        }

        if (oldestEntry && oldestWorkerId !== null) {
            await this._safeClose(oldestEntry.context);
            this._pool.delete(oldestWorkerId);
            this._stats.totalEvictions++;

            const idleSeconds = ((Date.now() - oldestTime) / 1000).toFixed(0);
            console.log(`🗑️ [LRU] 淘汰 W${oldestWorkerId} Context (空闲 ${idleSeconds}s)`);
        }
    }

    /**
     * 安全关闭 Context
     * @private
     */
    async _safeClose(context) {
        if (context) {
            try {
                await context.close();
            } catch (e) {
                // 忽略关闭错误
            }
        }
    }

    // ========================================================================
    // 清理与统计
    // ========================================================================

    /**
     * 清理所有 Context
     */
    async cleanup() {
        let cleaned = 0;
        for (const entry of this._pool.values()) {
            await this._safeClose(entry.context);
            cleaned++;
        }
        this._pool.clear();

        if (cleaned > 0 || this._stats.totalCreations > 0) {
            const reuseRate = this._getReuseRate();
            const evictionRate = this._getEvictionRate();
            console.log(`🧹 Context 池清理: ${cleaned} 个 | 创建=${this._stats.totalCreations} | 复用=${this._stats.totalReuses} (${reuseRate}% 复用率) | 淘汰=${this._stats.totalEvictions} (${evictionRate}%)`);
        }
    }

    /**
     * 获取复用率
     * @returns {string}
     */
    _getReuseRate() {
        const total = this._stats.totalCreations + this._stats.totalReuses;
        if (total === 0) return '0';
        return ((this._stats.totalReuses / total) * 100).toFixed(0);
    }

    /**
     * 获取淘汰率
     * @returns {string}
     */
    _getEvictionRate() {
        if (this._stats.totalCreations === 0) return '0';
        return ((this._stats.totalEvictions / this._stats.totalCreations) * 100).toFixed(0);
    }

    /**
     * 获取统计数据
     * @returns {Object}
     */
    getStats() {
        return {
            poolSize: this._pool.size,
            maxSize: this.config.maxSize,
            ...this._stats,
            reuseRate: this._getReuseRate() + '%',
            evictionRate: this._getEvictionRate() + '%'
        };
    }

    /**
     * 获取池子大小
     * @returns {number}
     */
    getSize() {
        return this._pool.size;
    }

    /**
     * 获取池条目
     * @param {number} workerId
     * @returns {Object|undefined}
     */
    getEntry(workerId) {
        return this._pool.get(workerId);
    }

    /**
     * 重置统计数据
     */
    resetStats() {
        this._stats = {
            totalCreations: 0,
            totalReuses: 0,
            totalEvictions: 0
        };
    }
}

// ============================================================================
// 单例模式
// ============================================================================

let _instance = null;

/**
 * 获取 ContextPoolManager 单例
 * @param {Object} [config={}] - 配置选项
 * @returns {ContextPoolManager}
 */
function getContextPoolManager(config = {}) {
    if (!_instance) {
        _instance = new ContextPoolManager(config);
    }
    return _instance;
}

/**
 * 重置单例（用于测试）
 */
function resetContextPoolManager() {
    if (_instance) {
        _instance._pool.clear();
    }
    _instance = null;
}

module.exports = {
    ContextPoolManager,
    getContextPoolManager,
    resetContextPoolManager
};
