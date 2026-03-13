/**
 * LRUSessionManager - V1.1.0 [Genesis.Standardization] LRU Session Management
 * ===========================================================================
 *
 * LRU 会话管理器 - 解决长时间运行导致的内存泄漏问题。
 *
 * V1.1.0 改进:
 * - LRU（Least Recently Used）淘汰策略
 * - TTL（Time To Live）自动过期
 * - 内存压力检测
 * - 会话统计与监控
 * - 错误码标准化
 * @module network/core/LRUSessionManager
 * @version V1.1.0
 * @since 2026-02-03
 * @author [Genesis.Standardization]
 */

'use strict';

const {
    sessionExpired,
    noProxyAvailable,
    NetworkShieldError,
    safeExecuteSync
} = require('./NetworkShieldError');

// ============================================================================
// CONFIGURATION
// ============================================================================

const DEFAULT_CONFIG = {
    sessionTimeoutMinutes: 30,      // 会话超时时间（分钟）
    maxSessions: 1000,              // 最大会话数
    lruMaxSize: 500,                // LRU 最大容量
    cleanupIntervalMs: 60000,       // 清理间隔（毫秒）
    memoryThresholdMb: 100,         // 内存阈值（MB）
    enableLRU: true,                // 启用 LRU
    enableTTL: true,                // 启用 TTL
    enableMemoryPressure: true      // 启用内存压力检测
};

// ============================================================================
// LRU CACHE IMPLEMENTATION
// ============================================================================

/**
 * LRU 缓存节点
 * @private
 * @template T
 */
class LRUNode {
    /**
     * @param {string} key - 键
     * @param {T} value - 值
     * @param {LRUNode|null} prev - 前驱节点
     * @param {LRUNode|null} next - 后继节点
     */
    constructor(key, value, prev = null, next = null) {
        this.key = key;
        this.value = value;
        this.prev = prev;
        this.next = next;
    }
}

/**
 * LRU 缓存实现
 * @template T
 */
class LRUCache {
    /**
     * @param {number} maxSize - 最大容量
     */
    constructor(maxSize = 500) {
        /**
         * @type {number}
         * @private
         */
        this._maxSize = maxSize;

        /**
         * @type {Map<string, LRUNode>}
         * @private
         */
        this._cache = new Map();

        /**
         * @type {LRUNode|null}
         * @private
         */
        this._head = null;

        /**
         * @type {LRUNode|null}
         * @private
         */
        this._tail = null;

        /**
         * @type {number}
         * @private
         */
        this._size = 0;

        /**
         * @type {number}
         * @private
         */
        this._hits = 0;

        /**
         * @type {number}
         * @private
         */
        this._misses = 0;
    }

    /**
     * 获取值
     * @param {string} key - 键
     * @returns {T|null} 值，不存在返回 null
     */
    get(key) {
        const node = this._cache.get(key);

        if (!node) {
            this._misses++;
            return null;
        }

        // 移动到头部（最近使用）
        this._moveToHead(node);
        this._hits++;

        return node.value;
    }

    /**
     * 设置值
     * @param {string} key - 键
     * @param {T} value - 值
     * @returns {T|null} 被淘汰的值（如果没有则返回 null）
     */
    set(key, value) {
        const existingNode = this._cache.get(key);

        if (existingNode) {
            // 更新现有节点
            existingNode.value = value;
            this._moveToHead(existingNode);
            return null;
        }

        // 创建新节点
        const newNode = new LRUNode(key, value);

        // 添加到缓存
        this._cache.set(key, newNode);
        this._addToHead(newNode);
        this._size++;

        // 检查是否超过容量
        if (this._size > this._maxSize) {
            // 淘汰尾部节点
            return this._removeTail();
        }

        return null;
    }

    /**
     * 删除值
     * @param {string} key - 键
     * @returns {boolean} 是否删除成功
     */
    delete(key) {
        const node = this._cache.get(key);

        if (!node) {
            return false;
        }

        this._removeNode(node);
        this._cache.delete(key);
        this._size--;

        return true;
    }

    /**
     * 检查键是否存在
     * @param {string} key - 键
     * @returns {boolean}
     */
    has(key) {
        return this._cache.has(key);
    }

    /**
     * 获取所有键
     * @returns {string[]}
     */
    keys() {
        return Array.from(this._cache.keys());
    }

    /**
     * 获取缓存大小
     * @returns {number}
     */
    get size() {
        return this._size;
    }

    /**
     * 获取最大容量
     * @returns {number}
     */
    get maxSize() {
        return this._maxSize;
    }

    /**
     * 设置最大容量
     * @param {number} size - 新的最大容量
     */
    setMaxSize(size) {
        this._maxSize = size;

        // 如果当前大小超过新容量，淘汰多余节点
        while (this._size > this._maxSize) {
            this._removeTail();
        }
    }

    /**
     * 清空缓存
     */
    clear() {
        this._cache.clear();
        this._head = null;
        this._tail = null;
        this._size = 0;
        this._hits = 0;
        this._misses = 0;
    }

    /**
     * 获取统计信息
     * @returns {object}
     */
    getStats() {
        const total = this._hits + this._misses;
        return {
            size: this._size,
            maxSize: this._maxSize,
            hits: this._hits,
            misses: this._misses,
            hitRate: total > 0 ? this._hits / total : 0
        };
    }

    /**
     * 添加节点到头部
     * @private
     * @param {LRUNode} node - 节点
     */
    _addToHead(node) {
        node.prev = null;
        node.next = this._head;

        if (this._head) {
            this._head.prev = node;
        }

        this._head = node;

        if (!this._tail) {
            this._tail = node;
        }
    }

    /**
     * 移动节点到头部
     * @private
     * @param {LRUNode} node - 节点
     */
    _moveToHead(node) {
        this._removeNode(node);
        this._addToHead(node);
    }

    /**
     * 移除节点
     * @private
     * @param {LRUNode} node - 节点
     */
    _removeNode(node) {
        if (node.prev) {
            node.prev.next = node.next;
        } else {
            this._head = node.next;
        }

        if (node.next) {
            node.next.prev = node.prev;
        } else {
            this._tail = node.prev;
        }
    }

    /**
     * 移除尾部节点
     * @private
     * @returns {T|null} 被移除节点的值
     */
    _removeTail() {
        if (!this._tail) {
            return null;
        }

        const removedValue = this._tail.value;
        this._cache.delete(this._tail.key);
        this._removeNode(this._tail);
        this._size--;

        return removedValue;
    }
}

// ============================================================================
// PROXY SESSION CLASS
// ============================================================================

/**
 * 代理会话类
 * @class
 */
class ProxySession {
    /**
     * @param {string} sessionId - 会话 ID
     * @param {number} port - 代理端口
     * @param {number} timeoutMinutes - 超时时间（分钟）
     */
    constructor(sessionId, port, timeoutMinutes = 30) {
        /**
         * @type {string}
         */
        this.sessionId = sessionId;

        /**
         * @type {number}
         */
        this.port = port;

        /**
         * @type {Date}
         */
        this.createdAt = new Date();

        /**
         * @type {Date}
         */
        this.lastUsedAt = new Date();

        /**
         * @type {Date}
         */
        this.expiresAt = new Date(Date.now() + timeoutMinutes * 60 * 1000);

        /**
         * @type {number}
         */
        this.timeoutMinutes = timeoutMinutes;

        /**
         * @type {boolean}
         */
        this.isActive = true;

        /**
         * @type {object}
         */
        this.metadata = {};

        /**
         * @type {number}
         */
        this.accessCount = 0;
    }

    /**
     * 检查会话是否过期
     * @returns {boolean}
     */
    isExpired() {
        return new Date() > this.expiresAt;
    }

    /**
     * 刷新会话有效期
     */
    refresh() {
        this.lastUsedAt = new Date();
        this.expiresAt = new Date(Date.now() + this.timeoutMinutes * 60 * 1000);
        this.accessCount++;
    }

    /**
     * 关闭会话
     */
    close() {
        this.isActive = false;
    }

    /**
     * 获取会话信息
     * @returns {object}
     */
    getInfo() {
        return {
            sessionId: this.sessionId,
            port: this.port,
            createdAt: this.createdAt.toISOString(),
            lastUsedAt: this.lastUsedAt.toISOString(),
            expiresAt: this.expiresAt.toISOString(),
            isActive: this.isActive,
            remainingMinutes: Math.max(0, Math.floor(
                (this.expiresAt - new Date()) / 60000
            )),
            accessCount: this.accessCount
        };
    }
}

// ============================================================================
// LRU SESSION MANAGER
// ============================================================================

/**
 * LRU 会话管理器
 * @class
 * @augments {SessionBindingManager}
 */
class LRUSessionManager {
    /**
     * @param {object} options - 配置选项
     * @param {number} [options.sessionTimeoutMinutes] - 会话超时时间（分钟）
     * @param {number} [options.maxSessions] - 最大会话数
     * @param {number} [options.lruMaxSize] - LRU 最大容量
     * @param {number} [options.cleanupIntervalMs] - 清理间隔（毫秒）
     * @param {number} [options.memoryThresholdMb] - 内存阈值（MB）
     * @param {boolean} [options.enableLRU] - 是否启用 LRU
     * @param {boolean} [options.enableTTL] - 是否启用 TTL
     * @param {boolean} [options.enableMemoryPressure] - 是否启用内存压力检测
     * @param {object} [options.logger] - 日志记录器
     */
    constructor(options = {}) {
        this.options = { ...DEFAULT_CONFIG, ...options };

        /**
         * @type {LRUCache<ProxySession>}
         * @private
         */
        this._sessionCache = new LRUCache(this.options.lruMaxSize);

        /**
         * @type {Map<number, string>} 端口到会话ID的映射
         * @private
         */
        this._portToSession = new Map();

        /**
         * @type {number}
         * @private
         */
        this._nextSessionId = 1;

        /**
         * @type {object}
         * @private
         */
        this._logger = options.logger || console;

        /**
         * @type {NodeJS.Timeout|null}
         * @private
         */
        this._cleanupInterval = null;

        /**
         * @type {number}
         * @private
         */
        this._evictedCount = 0;

        /**
         * @type {number}
         * @private
         */
        this._expiredCount = 0;

        // 启动清理任务
        this._startCleanupTask();
    }

    // ========================================================================
    // PUBLIC METHODS
    // ========================================================================

    /**
     * 创建新会话并分配代理端口
     * @param {number} port - 代理端口
     * @param {object} [metadata] - 会话元数据
     * @returns {Promise<ProxySession>} 会话对象
     * @throws {NetworkShieldError} 端口已被占用、达到最大会话数
     */
    async createSession(port, metadata = {}) {
        // 检查是否达到最大会话数
        if (this._sessionCache.size >= this.options.maxSessions) {
            throw noProxyAvailable(
                this.options.maxSessions,
                this._sessionCache.size
            );
        }

        // 检查端口是否已被占用
        const existingSessionId = this._portToSession.get(port);
        if (existingSessionId) {
            const existingSession = this._sessionCache.get(existingSessionId);

            if (existingSession && existingSession.isActive && !existingSession.isExpired()) {
                throw new NetworkShieldError(
                    'NS_SESSION_PORT_OCCUPIED',
                    `Port ${port} is already in use by active session ${existingSessionId}`,
                    { port, existingSessionId }
                );
            } else {
                // 清理过期会话
                this.releaseSession(existingSessionId);
            }
        }

        // 创建新会话
        const sessionId = `SESSION-${this._nextSessionId++}`;
        const session = new ProxySession(sessionId, port, this.options.sessionTimeoutMinutes);
        session.metadata = metadata;

        // 添加到 LRU 缓存
        this._sessionCache.set(sessionId, session);
        this._portToSession.set(port, sessionId);

        this._log('info',
            `Session created: ${sessionId} -> Port ${port} ` +
            `(expires in ${this.options.sessionTimeoutMinutes}m, ` +
            `cache size: ${this._sessionCache.size}/${this._sessionCache.maxSize})`
        );

        return session;
    }

    /**
     * 获取会话
     * @param {string} sessionId - 会话 ID
     * @returns {ProxySession|null} 会话对象
     */
    getSession(sessionId) {
        return this._sessionCache.get(sessionId);
    }

    /**
     * 获取端口绑定的会话
     * @param {number} port - 代理端口
     * @returns {ProxySession|null} 会话对象
     */
    getSessionByPort(port) {
        const sessionId = this._portToSession.get(port);
        return sessionId ? this._sessionCache.get(sessionId) : null;
    }

    /**
     * 刷新会话有效期
     * @param {string} sessionId - 会话 ID
     * @returns {boolean} 是否成功
     * @throws {NetworkShieldError} 会话不存在或已过期
     */
    refreshSession(sessionId) {
        const session = this._sessionCache.get(sessionId);

        if (!session) {
            throw new NetworkShieldError(
                'NS_SESSION_NOT_FOUND',
                `Session ${sessionId} not found`,
                { sessionId }
            );
        }

        if (session.isExpired()) {
            this.releaseSession(sessionId);
            throw sessionExpired(sessionId);
        }

        session.refresh();
        this._log('debug', `Session refreshed: ${sessionId} (access count: ${session.accessCount})`);
        return true;
    }

    /**
     * 释放会话
     * @param {string} sessionId - 会话 ID
     * @returns {boolean} 是否成功
     */
    releaseSession(sessionId) {
        const session = this._sessionCache.get(sessionId);

        if (!session) {
            return false;
        }

        session.close();
        this._portToSession.delete(session.port);
        this._sessionCache.delete(sessionId);

        this._log('info', `Session released: ${sessionId} (was port ${session.port})`);
        return true;
    }

    /**
     * 获取所有活跃会话
     * @returns {ProxySession[]} 活跃会话列表
     */
    getActiveSessions() {
        const sessions = [];
        for (const key of this._sessionCache.keys()) {
            const session = this._sessionCache.get(key);
            if (session && session.isActive && !session.isExpired()) {
                sessions.push(session);
            }
        }
        return sessions;
    }

    /**
     * 获取会话统计
     * @returns {object} 统计信息
     */
    getStatistics() {
        const activeSessions = this.getActiveSessions();
        const expiredSessions = [];

        for (const key of this._sessionCache.keys()) {
            const session = this._sessionCache.get(key);
            if (session && session.isExpired()) {
                expiredSessions.push(session);
            }
        }

        const lruStats = this._sessionCache.getStats();

        return {
            totalSessions: this._sessionCache.size,
            activeSessions: activeSessions.length,
            expiredSessions: expiredSessions.length,
            occupiedPorts: Array.from(this._portToSession.keys()),
            nextSessionId: this._nextSessionId,
            lru: {
                size: lruStats.size,
                maxSize: lruStats.maxSize,
                hitRate: lruStats.hitRate.toFixed(4),
                hits: lruStats.hits,
                misses: lruStats.misses
            },
            cleanup: {
                evicted: this._evictedCount,
                expired: this._expiredCount
            }
        };
    }

    /**
     * 清理过期会话
     * @returns {number} 清理的会话数量
     */
    cleanupExpiredSessions() {
        let cleaned = 0;
        const toRemove = [];

        for (const key of this._sessionCache.keys()) {
            const session = this._sessionCache.get(key);
            if (!session || session.isExpired() || !session.isActive) {
                toRemove.push(key);
            }
        }

        for (const key of toRemove) {
            this.releaseSession(key);
            cleaned++;
            this._expiredCount++;
        }

        if (cleaned > 0) {
            this._log('info', `Cleaned up ${cleaned} expired session(s)`);
        }

        return cleaned;
    }

    /**
     * 获取空闲的可用端口
     * @param {number[]} allPorts - 所有端口列表
     * @returns {number[]} 空闲端口列表
     */
    getAvailablePorts(allPorts) {
        const occupiedPorts = new Set(this._portToSession.keys());
        return allPorts.filter(p => !occupiedPorts.has(p));
    }

    /**
     * 关闭管理器并清理所有会话
     */
    shutdown() {
        if (this._cleanupInterval) {
            clearInterval(this._cleanupInterval);
            this._cleanupInterval = null;
        }

        // 释放所有会话
        for (const sessionId of this._sessionCache.keys()) {
            this.releaseSession(sessionId);
        }

        this._sessionCache.clear();
        this._portToSession.clear();

        this._log('info', 'LRUSessionManager shut down');
    }

    /**
     * 设置 LRU 最大容量
     * @param {number} size - 新的最大容量
     */
    setLRUMaxSize(size) {
        this._sessionCache.setMaxSize(size);
        this._log('info', `LRU max size set to ${size}`);
    }

    // ========================================================================
    // PRIVATE METHODS
    // ========================================================================

    /**
     * 启动清理任务
     * @private
     */
    _startCleanupTask() {
        this._cleanupInterval = setInterval(() => {
            this.cleanupExpiredSessions();

            // 检查内存压力
            if (this.options.enableMemoryPressure) {
                this._checkMemoryPressure();
            }
        }, this.options.cleanupIntervalMs);
    }

    /**
     * 检查内存压力
     * @private
     */
    _checkMemoryPressure() {
        if (typeof process !== 'undefined' && process.memoryUsage) {
            const memUsage = process.memoryUsage();
            const heapUsedMb = memUsage.heapUsed / 1024 / 1024;

            if (heapUsedMb > this.options.memoryThresholdMb) {
                const sessionsToEvict = Math.floor(this._sessionCache.size * 0.1); // 淘汰 10%
                this._evictLRU(sessionsToEvict);

                this._log('warn',
                    `Memory pressure detected (${heapUsedMb.toFixed(2)}MB), ` +
                    `evicted ${sessionsToEvict} sessions`
                );
            }
        }
    }

    /**
     * 淘汰 LRU 会话
     * @private
     * @param {number} count - 淘汰数量
     */
    _evictLRU(count) {
        const keys = this._sessionCache.keys();
        let evicted = 0;

        for (const key of keys) {
            if (evicted >= count) break;

            const session = this._sessionCache.get(key);
            if (session && session.isActive) {
                this.releaseSession(key);
                evicted++;
                this._evictedCount++;
            }
        }

        if (evicted > 0) {
            this._log('info', `Evicted ${evicted} sessions due to LRU policy`);
        }
    }

    /**
     * 记录日志
     * @private
     * @param {string} level - 日志级别
     * @param {string} message - 日志消息
     */
    _log(level, message) {
        const logMessage = `[SessionBinding] ${message}`;

        switch (level) {
            case 'debug':
                this._logger.debug?.(logMessage) || console.debug(logMessage);
                break;
            case 'info':
                this._logger.info?.(logMessage) || console.info(logMessage);
                break;
            case 'warn':
                this._logger.warn?.(logMessage) || console.warn(logMessage);
                break;
            case 'error':
                this._logger.error?.(logMessage) || console.error(logMessage);
                break;
            default:
                console.log(logMessage);
        }
    }
}

module.exports = {
    LRUSessionManager,
    ProxySession,
    LRUCache,
    DEFAULT_CONFIG
};
