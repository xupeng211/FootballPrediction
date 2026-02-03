/**
 * RegistryManager - V1.1.0 [Genesis.Standardization] Production-Grade Registry Manager
 * ============================================================================
 *
 * 管理配置文件 active_registry.json 的核心组件 - 企业级重构版本。
 *
 * V1.1.0 改进:
 * - 依赖注入：支持 AbstractFileSystem 适配器
 * - 错误码标准化：使用 NetworkShieldError
 * - 改进的并发锁：基于文件系统的原子锁
 * - 跨语言状态同步 (Cross-language state sync)
 * - 自动备份和恢复 (Auto backup/restore)
 * - 版本控制 (Version control)
 * - 线程安全 (Thread-safe)
 *
 * @module network/core/RegistryManager
 * @version V1.1.0
 * @since 2026-02-03
 * @author [Genesis.Standardization]
 */

'use strict';

const path = require('path');
const { FileSystemProvider } = require('./AbstractFileSystem');
const {
    NetworkShieldError,
    registryLocked,
    filesystemError,
    invalidConfig,
    safeExecute,
    safeExecuteSync
} = require('./NetworkShieldError');

// ============================================================================
// DEFAULT CONFIGURATION
// ============================================================================

const DEFAULT_CONFIG = {
    registryPath: path.join(process.cwd(), 'config', 'active_registry.json'),
    backupPath: path.join(process.cwd(), 'config', 'active_registry.backup.json'),
    lockPath: path.join(process.cwd(), 'config', '.registry.lock'),
    lockTimeout: 5000,        // 5 seconds
    lockPollInterval: 100,    // 100ms
    enableBackup: true,       // 启用自动备份
    cacheTTL: 1000            // 缓存有效期（毫秒）
};

// ============================================================================
// REGISTRY MANAGER CLASS
// ============================================================================

/**
 * RegistryManager - 中央注册表管理器
 *
 * @class
 * @example
 * const manager = new RegistryManager({
 *   fileSystem: FileSystemProvider.getFileSystem()
 * });
 * await manager.updateRegistry(registry => {
 *   registry.nodes.push(newNode);
 *   return registry;
 * });
 */
class RegistryManager {
    /**
     * 创建 RegistryManager 实例
     *
     * @param {Object} options - 配置选项
     * @param {IFileSystem} [options.fileSystem] - 文件系统实现（DI）
     * @param {string} [options.registryPath] - 注册表文件路径
     * @param {string} [options.backupPath] - 备份文件路径
     * @param {string} [options.lockPath] - 锁文件路径
     * @param {number} [options.lockTimeout] - 锁超时时间（毫秒）
     * @param {number} [options.cacheTTL] - 缓存有效期（毫秒）
     * @param {boolean} [options.enableBackup] - 是否启用备份
     */
    constructor(options = {}) {
        this.options = { ...DEFAULT_CONFIG, ...options };

        /**
         * @type {IFileSystem} 文件系统实现（依赖注入）
         * @private
         */
        this._fs = options.fileSystem || FileSystemProvider.getFileSystem();

        /**
         * @type {Object|null} 缓存的注册表数据
         * @private
         */
        this._cache = null;

        /**
         * @type {number} 缓存时间戳
         * @private
         */
        this._cacheTime = 0;

        /**
         * @type {boolean} 是否持有锁
         * @private
         */
        this._lockAcquired = false;

        /**
         * @type {string|null} 当前锁的 token（用于验证）
         * @private
         */
        this._lockToken = null;
    }

    // ========================================================================
    // PUBLIC METHODS
    // ========================================================================

    /**
     * 获取注册表数据
     *
     * @returns {Object} 注册表数据
     * @throws {NetworkShieldError} 文件系统错误
     *
     * @example
     * const registry = manager.getRegistry();
     * console.log(registry.nodes.length);
     */
    getRegistry() {
        // 检查缓存是否有效
        const now = Date.now();
        if (this._cache !== null && (now - this._cacheTime) < this.options.cacheTTL) {
            return this._cache;
        }

        return this._loadRegistry();
    }

    /**
     * 更新注册表数据（原子操作）
     *
     * @param {Function} updater - 更新函数，接收当前注册表并返回更新后的注册表
     * @returns {Promise<Object>} 更新后的注册表数据
     * @throws {NetworkShieldError} 锁超时、文件系统错误
     *
     * @example
     * const updated = await manager.updateRegistry(registry => {
     *   registry.last_updated = new Date().toISOString();
     *   return registry;
     * });
     */
    async updateRegistry(updater) {
        await this._acquireLock();

        try {
            const registry = this._loadRegistry();
            const updated = updater(registry);

            // 验证更新结果
            this._validateRegistry(updated);

            // 更新时间戳
            updated.last_updated = new Date().toISOString();

            // 持久化到磁盘
            this._saveRegistry(updated);

            // 更新缓存
            this._cache = updated;
            this._cacheTime = Date.now();

            return updated;
        } finally {
            this._releaseLock();
        }
    }

    /**
     * 获取节点信息
     *
     * @param {number} port - 节点端口
     * @returns {Object|null} 节点信息，未找到返回 null
     * @throws {NetworkShieldError} 文件系统错误
     */
    getNode(port) {
        const registry = this.getRegistry();
        return registry.nodes.find(n => n.port === port) || null;
    }

    /**
     * 更新单个节点
     *
     * @param {number} port - 节点端口
     * @param {Function} updater - 节点更新函数
     * @returns {Promise<Object>} 更新后的节点信息
     * @throws {NetworkShieldError} 节点不存在、锁超时、文件系统错误
     */
    async updateNode(port, updater) {
        return this.updateRegistry(registry => {
            const nodeIndex = registry.nodes.findIndex(n => n.port === port);

            if (nodeIndex === -1) {
                throw invalidConfig('port', `Node ${port} not found in registry`);
            }

            const node = registry.nodes[nodeIndex];
            updater(node);
            registry.nodes[nodeIndex] = node;

            // 更新统计
            this._updateStatistics(registry);

            return registry;
        }).then(registry => registry.nodes.find(n => n.port === port));
    }

    /**
     * 获取可用节点列表
     *
     * @returns {Array<Object>} 可用节点列表（按健康分数降序）
     * @throws {NetworkShieldError} 文件系统错误
     */
    getAvailableNodes() {
        const registry = this.getRegistry();
        const now = new Date().toISOString();

        const available = registry.nodes.filter(node => {
            // 检查是否在冷却期
            if (node.cooldown_until && node.cooldown_until > now) {
                return false;
            }

            // 检查状态
            return node.status === 'active';
        });

        // 按健康分数排序（降序）
        available.sort((a, b) => b.health_score - a.health_score);

        return available;
    }

    /**
     * 标记节点失败
     *
     * @param {number} port - 节点端口
     * @param {string} [reason='Unknown'] - 失败原因
     * @param {number} [cooldownMinutes=15] - 冷却时间（分钟）
     * @returns {Promise<Object>} 更新后的节点信息
     * @throws {NetworkShieldError} 锁超时、文件系统错误
     */
    async markNodeFailed(port, reason = 'Unknown', cooldownMinutes = 15) {
        return this.updateNode(port, node => {
            node.consecutive_failures += 1;
            node.last_failure = new Date().toISOString();

            // 连续失败 2 次，进入冷却期
            if (node.consecutive_failures >= 2) {
                const cooldownUntil = new Date();
                cooldownUntil.setMinutes(cooldownUntil.getMinutes() + cooldownMinutes);
                node.cooldown_until = cooldownUntil.toISOString();
                node.status = 'cooled';
            }

            node.health_score = Math.max(0, node.health_score - 10);
            node.total_requests += 1;
        });
    }

    /**
     * 标记节点成功
     *
     * @param {number} port - 节点端口
     * @param {number} [latency=0] - 延迟（毫秒）
     * @returns {Promise<Object>} 更新后的节点信息
     * @throws {NetworkShieldError} 锁超时、文件系统错误
     */
    async markNodeSuccess(port, latency = 0) {
        return this.updateNode(port, node => {
            node.consecutive_failures = 0;
            node.last_success = new Date().toISOString();
            node.last_failure = null;

            // 恢复健康分数
            node.health_score = Math.min(100, node.health_score + 5);
            node.avg_latency_ms = node.avg_latency_ms > 0
                ? (node.avg_latency_ms * 0.9 + latency * 0.1)
                : latency;
            node.total_requests += 1;
            node.successful_requests += 1;

            // 如果之前是冷却状态，现在恢复活跃
            if (node.status === 'cooled') {
                node.status = 'active';
                node.cooldown_until = null;
            }
        });
    }

    /**
     * 更新节点健康检查结果
     *
     * @param {number} port - 节点端口
     * @param {Object} healthResult - 健康检查结果
     * @param {boolean} healthResult.is_healthy - 是否健康
     * @param {number} [healthResult.response_time] - 响应时间
     * @param {string} [healthResult.ip_address] - IP 地址
     * @returns {Promise<Object>} 更新后的节点信息
     * @throws {NetworkShieldError} 锁超时、文件系统错误
     */
    async updateNodeHealth(port, healthResult) {
        return this.updateNode(port, node => {
            node.last_check = new Date().toISOString();
            node.ip_address = healthResult.ip_address || node.ip_address;
            node.avg_latency_ms = healthResult.response_time || node.avg_latency_ms;

            if (healthResult.is_healthy) {
                node.health_score = Math.min(100, node.health_score + 10);
                if (node.status === 'cooled') {
                    node.status = 'active';
                    node.cooldown_until = null;
                }
            } else {
                node.health_score = Math.max(0, node.health_score - 20);
                node.consecutive_failures += 1;

                if (node.consecutive_failures >= 2) {
                    const cooldownUntil = new Date();
                    cooldownUntil.setMinutes(cooldownUntil.getMinutes() + 15);
                    node.cooldown_until = cooldownUntil.toISOString();
                    node.status = 'cooled';
                }
            }
        });
    }

    /**
     * 获取统计信息
     *
     * @returns {Object} 统计信息
     * @throws {NetworkShieldError} 文件系统错误
     */
    getStatistics() {
        const registry = this.getRegistry();
        return registry.statistics;
    }

    /**
     * 创建备份
     *
     * @returns {boolean} 是否成功
     */
    createBackup() {
        if (!this.options.enableBackup) {
            return false;
        }

        try {
            const data = this._loadRegistry();
            const content = JSON.stringify(data, null, 2);
            this._fs.writeFile(this.options.backupPath, content);
            return true;
        } catch (error) {
            // 静默失败
            return false;
        }
    }

    /**
     * 恢复备份
     *
     * @returns {boolean} 是否成功
     */
    restoreBackup() {
        try {
            if (!this._fs.exists(this.options.backupPath)) {
                return false;
            }

            const content = this._fs.readFile(this.options.backupPath);
            const backupData = JSON.parse(content);

            this._validateRegistry(backupData);
            this._saveRegistry(backupData);

            this._cache = backupData;
            this._cacheTime = Date.now();

            return true;
        } catch (error) {
            // 静默失败
            return false;
        }
    }

    /**
     * 重置所有节点状态
     *
     * @returns {Promise<Object>} 重置后的注册表
     * @throws {NetworkShieldError} 锁超时、文件系统错误
     */
    async resetAllNodes() {
        return this.updateRegistry(registry => {
            const now = new Date().toISOString();

            registry.nodes.forEach(node => {
                node.status = 'active';
                node.health_score = 100;
                node.consecutive_failures = 0;
                node.cooldown_until = null;
                node.last_check = now;
            });

            registry.active_sessions = {
                next_session_id: 1,
                sessions: []
            };

            this._updateStatistics(registry);

            return registry;
        });
    }

    /**
     * 刷新缓存
     */
    invalidateCache() {
        this._cache = null;
        this._cacheTime = 0;
    }

    // ========================================================================
    // PRIVATE METHODS
    // ========================================================================

    /**
     * 加载注册表数据
     * @private
     * @returns {Object} 注册表数据
     * @throws {NetworkShieldError} 文件系统错误、数据损坏
     */
    _loadRegistry() {
        return safeExecuteSync(() => {
            if (!this._fs.exists(this.options.registryPath)) {
                return this._createDefaultRegistry();
            }

            const content = this._fs.readFile(this.options.registryPath);

            try {
                const data = JSON.parse(content);
                this._validateRegistry(data);
                return data;
            } catch (parseError) {
                // 尝试恢复备份
                if (this.restoreBackup()) {
                    return this._cache;
                }
                throw parseError;
            }
        });
    }

    /**
     * 保存注册表数据
     * @private
     * @param {Object} data - 注册表数据
     * @throws {NetworkShieldError} 文件系统错误
     */
    _saveRegistry(data) {
        const content = JSON.stringify(data, null, 2);

        // 先创建备份
        if (this.options.enableBackup && this._fs.exists(this.options.registryPath)) {
            try {
                this._fs.copyFile(this.options.registryPath, this.options.backupPath);
            } catch {
                // 忽略备份失败
            }
        }

        // 原子写入
        this._fs.atomicWrite(this.options.registryPath, content);
    }

    /**
     * 验证注册表数据结构
     * @private
     * @param {Object} registry - 注册表数据
     * @throws {NetworkShieldError} 数据结构无效
     */
    _validateRegistry(registry) {
        if (!registry || typeof registry !== 'object') {
            throw invalidConfig('registry', 'Registry must be an object');
        }

        if (!Array.isArray(registry.nodes)) {
            throw invalidConfig('registry', 'Registry.nodes must be an array');
        }

        if (!registry.statistics || typeof registry.statistics !== 'object') {
            throw invalidConfig('registry', 'Registry.statistics must be an object');
        }
    }

    /**
     * 创建默认注册表
     * @private
     * @returns {Object} 默认注册表
     */
    _createDefaultRegistry() {
        const config = {
            registry_id: 'REG-CLASH-22',
            version: 'V1.1.0',
            last_updated: new Date().toISOString(),
            registry_config: {
                proxy_host: '172.25.16.1',
                port_range: { start: 7891, end: 7912 },
                protocol: 'http',
                cooldown_minutes: 15,
                max_consecutive_failures: 2
            },
            nodes: [],
            active_sessions: { next_session_id: 1, sessions: [] },
            statistics: { total_nodes: 0, active_nodes: 0 }
        };

        // 生成 22 个节点
        for (let port = 7891; port <= 7912; port++) {
            config.nodes.push({
                id: `NODE-${port}`,
                port,
                status: 'active',
                health_score: 100,
                consecutive_failures: 0,
                last_check: new Date().toISOString(),
                last_success: new Date().toISOString(),
                last_failure: null,
                cooldown_until: null,
                ip_address: null,
                avg_latency_ms: 0,
                total_requests: 0,
                successful_requests: 0,
                metadata: { provider: 'clash_verge', region: 'default' }
            });
        }

        config.statistics.total_nodes = 22;
        config.statistics.active_nodes = 22;

        return config;
    }

    /**
     * 更新统计信息
     * @private
     * @param {Object} registry - 注册表数据
     */
    _updateStatistics(registry) {
        const now = new Date().toISOString();
        const activeNodes = registry.nodes.filter(n => n.status === 'active');
        const cooledNodes = registry.nodes.filter(n =>
            n.status === 'cooled' || (n.cooldown_until && n.cooldown_until > now)
        );

        registry.statistics = {
            total_nodes: registry.nodes.length,
            active_nodes: activeNodes.length,
            cooled_nodes: cooledNodes.length,
            total_requests: registry.nodes.reduce((sum, n) => sum + n.total_requests, 0),
            successful_requests: registry.nodes.reduce((sum, n) => sum + n.successful_requests, 0),
            failed_requests: registry.nodes.reduce((sum, n) =>
                sum + (n.total_requests - n.successful_requests), 0),
            avg_health_score: registry.nodes.reduce((sum, n) => sum + n.health_score, 0) /
                registry.nodes.length
        };
    }

    /**
     * 获取文件锁
     * @private
     * @returns {Promise<void>}
     * @throws {NetworkShieldError} 锁超时
     */
    async _acquireLock() {
        const acquired = await this._fs.acquireLock(
            this.options.lockPath,
            this.options.lockTimeout
        );

        if (!acquired) {
            throw registryLocked(
                this.options.lockPath,
                this.options.lockTimeout
            );
        }

        this._lockAcquired = true;
        this._lockToken = `${process.pid}-${Date.now()}`;
    }

    /**
     * 释放文件锁
     * @private
     */
    _releaseLock() {
        if (this._lockAcquired) {
            this._fs.releaseLock(this.options.lockPath);
            this._lockAcquired = false;
            this._lockToken = null;
        }
    }
}

// ============================================================================
// SINGLETON INSTANCE
// ============================================================================

let _instance = null;
let _instanceOptions = null;

/**
 * 获取 RegistryManager 单例
 *
 * @param {Object} [options] - 配置选项（仅在首次调用时生效）
 * @returns {RegistryManager} 单例实例
 */
function getRegistryManager(options) {
    if (!_instance) {
        _instance = new RegistryManager(options);
        _instanceOptions = options;
    }

    // 如果提供了不同的 options，更新现有实例
    if (options && _instanceOptions !== options) {
        if (options.fileSystem) {
            _instance._fs = options.fileSystem;
        }
    }

    return _instance;
}

/**
 * 重置单例（用于测试）
 */
function resetSingleton() {
    _instance = null;
    _instanceOptions = null;
}

module.exports = {
    RegistryManager,
    getRegistryManager,
    resetSingleton,
    DEFAULT_CONFIG
};
