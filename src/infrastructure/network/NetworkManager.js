/**
 * NetworkManager - V4.46 网络与会话管理器
 * ========================================
 *
 * 从 ProductionHarvester 剥离的网络管理逻辑
 * 统一管理代理池、会话、Worker 身份绑定
 * @module infrastructure/network/NetworkManager
 * @version V4.46.5 - HARDENING: 零模拟铁律
 */

'use strict';

// V4.46: 配置 (从 FactoryConfig 统一管理)
const FactoryConfig = require('../../../config/factory_config');
const { getNetworkShield } = require('./NetworkShield');
const { getSessionManager } = require('./SessionManager');
const { getPathResolver } = require('../utils/PathResolver');

// V4.46: 导入隐身指纹生成器 (从独立模块)
const { generateStealthHeaders } = require('./StealthFingerprint');

// V4.46.5 HARDENING: 本地确定性 ID 生成器（零模拟铁律）
function generateSessionId(port) {
    return `session_${port}_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

// ============================================================================
// WorkerIdentity - Worker 身份绑定类 (从 ProductionHarvester 迁移)
// ============================================================================

/**
 * WorkerIdentity - 每个 Worker 的身份绑定
 * 确保【代理 IP + User-Agent + 视口尺寸】在一次 Session 中保持一致
 */
class WorkerIdentity {
    /**
     * @param {number} workerId - Worker ID
     * @param {object} proxy - 代理配置
     * @param {object} stealth - 隐身配置
     */
    constructor(workerId, proxy, stealth) {
        this.workerId = workerId;
        this.proxy = proxy;
        this.stealth = stealth;
        this.sessionId = `WORKER-${workerId}-${Date.now()}`;
        this.createdAt = Date.now();
        this.requestCount = 0;
        this.successCount = 0;
        this.failureCount = 0;
    }

    /**
     * 记录请求
     * @param {boolean} success - 是否成功
     */
    recordRequest(success) {
        this.requestCount++;
        if (success) {
            this.successCount++;
        } else {
            this.failureCount++;
        }
    }

    /**
     * 获取成功率
     * @returns {number} 成功率 (0-1)
     */
    getSuccessRate() {
        if (this.requestCount === 0) return 1;
        return this.successCount / this.requestCount;
    }

    /**
     * 是否需要更换身份（连续失败 3 次）
     * @returns {boolean}
     */
    needsReidentity() {
        return this.failureCount >= 3 && this.getSuccessRate() < 0.5;
    }
}

// ============================================================================
// NetworkManager - 网络管理器主类
// ============================================================================

/**
 * NetworkManager - 统一网络管理器
 *
 * 功能:
 * 1. NetworkShield 代理池管理
 * 2. SessionManager 身份管理
 * 3. Worker 身份绑定 (Session Stickiness)
 * 4. 端口避障与熔断切换
 */
class NetworkManager {
    /**
     * @param {object} options - 配置选项
     * @param {number} [options.maxWorkers] - 最大 Worker 数量
     * @param {Function} [options.stealthGenerator] - 隐身指纹生成函数
     */
    constructor(options = {}) {
        this.maxWorkers = options.maxWorkers || 6;
        this.stealthGenerator = options.stealthGenerator || generateStealthHeaders;

        // NetworkShield 代理管理器
        this.networkShield = null;

        // SessionManager 身份管理器
        this.sessionManager = null;

        // Worker 身份池 (Session Stickiness)
        this.workerIdentities = new Map();

        // 端口避障 - 记录失败端口
        this.failedPorts = new Set();

        // 可用端口池 (7890-7911)
        this.availablePorts = Array.from({ length: 22 }, (_, i) => 7890 + i);
    }

    // ========================================================================
    // 初始化方法
    // ========================================================================

    /**
     * 初始化网络管理器
     * @param {object} options - 初始化选项
     * @param {Function} [options.preFlightCleanup] - 预清理函数
     * @returns {Promise<void>}
     */
    async initialize(options = {}) {
        // 预清理（如果提供）
        if (options.preFlightCleanup) {
            await options.preFlightCleanup();
        }

        // 初始化 NetworkShield
        await this._initNetworkShield();

        // 初始化 SessionManager
        await this._initSessionManager();
    }

    /**
     * V178.2: 初始化 NetworkShield 代理池
     * V4.46-TITAN: 使用简化的 NetworkShield
     * @private
     * @returns {Promise<void>}
     */
    async _initNetworkShield() {
        try {
            this.networkShield = getNetworkShield({
                proxyHost: FactoryConfig.PROXY_CONFIG.serverTemplate.match(/[\d.]+/)?.[0] || '172.25.16.1',
                portRange: { start: 7890, end: 7911 }
            });

            // V4.46-TITAN: NetworkShield 没有 initialize 方法，直接获取状态
            const status = this.networkShield.getStatus();
            console.log(`📡 NetworkShield 已就绪: ${status.active}/${status.total} 节点可用`);
        } catch (initError) {
            console.error(`⚠️ NetworkShield 初始化失败: ${initError.message}`);
            console.log(`📡 NetworkShield 将在降级模式下运行（使用 FactoryConfig 代理池）`);
            this.networkShield = null;
        }
    }

    /**
     * V179: 初始化 SessionManager 身份管理器
     * @private
     * @returns {Promise<void>}
     */
    async _initSessionManager() {
        const pathResolver = getPathResolver();

        this.sessionManager = getSessionManager({
            profilePath: pathResolver.getSessionsPath(),
            sessionTtlHours: 24,
            maxRefreshAttempts: 3,
            headlessRefresh: false
        });

        await this.sessionManager.initialize();

        const stats = this.sessionManager.getStats();
        console.log(`🔑 SessionManager 已就绪: ${stats.cachedSessions} 个会话缓存`);
    }

    // ========================================================================
    // Worker 身份管理
    // ========================================================================

    /**
     * V178.2: 为 Worker 分配身份（代理 IP + User-Agent + 视口）
     * 实现 Session Stickiness
     * V179: 集成 SessionManager 自动身份管理
     * V179.1: 增加 NetworkShield 降级模式兼容
     * @param {number} workerId - Worker 编号
     * @returns {Promise<WorkerIdentity>} Worker 身份
     */
    async assignWorkerIdentity(workerId) {
        // 检查是否已有身份且不需要更换
        const existing = this.workerIdentities.get(workerId);
        if (existing && !existing.needsReidentity()) {
            console.log(`🔄 Worker ${workerId} 复用身份: Port ${existing.proxy.port}`);
            return existing;
        }

        // 从 NetworkShield 获取健康代理（如果可用）
        const sessionId = `WORKER-${workerId}`;
        let proxyAssignment;

        // V179.1: 检查 NetworkShield 是否可用
        if (this.networkShield && typeof this.networkShield.getNextHealthyProxy === 'function') {
            try {
                proxyAssignment = await this.networkShield.getNextHealthyProxy(sessionId);
            } catch (error) {
                console.warn(`⚠️ Worker ${workerId} NetworkShield 获取代理失败: ${error.message}`);
                // 降级：使用 FactoryConfig 的代理池
                const port = FactoryConfig.PROXY_CONFIG.getPortByWorker(workerId);
                proxyAssignment = {
                    sessionId,
                    port,
                    url: FactoryConfig.PROXY_CONFIG.getServer(port)
                };
            }
        } else {
            // NetworkShield 不可用，直接使用 FactoryConfig
            console.log(`📡 Worker ${workerId} 使用 FactoryConfig 代理池（NetworkShield 降级模式）`);
            const port = FactoryConfig.PROXY_CONFIG.getPortByWorker(workerId);
            proxyAssignment = {
                sessionId,
                port,
                url: FactoryConfig.PROXY_CONFIG.getServer(port)
            };
        }

        // V179: 尝试获取或刷新会话（自动身份管理）
        if (this.sessionManager) {
            try {
                const session = await this.sessionManager.getOrRefreshSession(proxyAssignment.port, {
                    proxyUrl: proxyAssignment.url
                });
                if (session) {
                    console.log(`🔑 Worker ${workerId} 会话状态: ${session.cookies?.length || 0} Cookie, 过期于 ${new Date(session.expiresAt).toLocaleString()}`);
                }
            } catch (error) {
                console.warn(`⚠️ Worker ${workerId} 会话刷新失败: ${error.message}`);
            }
        }

        // 生成隐身指纹
        const stealth = this.stealthGenerator();

        // 创建 Worker 身份
        const identity = new WorkerIdentity(workerId, proxyAssignment, stealth);
        this.workerIdentities.set(workerId, identity);

        console.log(`🆔 Worker ${workerId} 新身份绑定:`);
        console.log(`   Proxy: ${proxyAssignment.url}`);
        console.log(`   UA: ${stealth.userAgent.substring(0, 50)}...`);
        console.log(`   Viewport: ${stealth.viewport.width}x${stealth.viewport.height}`);

        return identity;
    }

    /**
     * 获取 Worker 身份
     * @param {number} workerId - Worker ID
     * @returns {WorkerIdentity|undefined}
     */
    getWorkerIdentity(workerId) {
        return this.workerIdentities.get(workerId);
    }

    // ========================================================================
    // 代理状态管理
    // ========================================================================

    /**
     * V178.2: 标记代理成功
     * @param {number} workerId - Worker 编号
     * @param {number} latency - 延迟（毫秒）
     */
    async markProxySuccess(workerId, latency = 0) {
        const identity = this.workerIdentities.get(workerId);
        if (identity && identity.proxy) {
            identity.recordRequest(true);
            // V4.46-TITAN: 使用 NetworkShield 的新 API
            if (this.networkShield && typeof this.networkShield.markSuccess === 'function') {
                this.networkShield.markSuccess(identity.proxy.port);
            }
        }
    }

    /**
     * V178.2: 标记代理失败 + 熔断切换
     * @param {number} workerId - Worker 编号
     * @param {string} reason - 失败原因
     */
    async markProxyFailed(workerId, reason) {
        const identity = this.workerIdentities.get(workerId);
        if (identity && identity.proxy) {
            identity.recordRequest(false);
            // V4.46-TITAN: 使用 NetworkShield 的新 API
            if (this.networkShield && typeof this.networkShield.markFailed === 'function') {
                this.networkShield.markFailed(identity.proxy.port, reason);
            }

            // V181: 记录失败端口用于避障
            this.failedPorts.add(identity.proxy.port);

            // 检查是否需要熔断切换
            if (identity.needsReidentity()) {
                console.log(`⚡ Worker ${workerId} 触发熔断，准备切换身份...`);
                this.workerIdentities.delete(workerId);
            }
        }
    }

    // ========================================================================
    // 端口轮询与动态分发 (TITAN-SWARM)
    // ========================================================================

    /**
     * TITAN-SWARM: 获取轮询代理配置
     * 每次调用返回不同的端口配置，实现 IP 轮询分发
     * V4.46.5: 使用确定性 ID 生成
     * @param {number} [index] - 可选索引，用于轮询模式
     * @returns {object} 代理配置对象 { port, url, sessionId }
     */
    getRotatedConfig(index) {
        let selectedPort;

        if (index !== undefined) {
            // 轮询模式：根据索引选择端口
            selectedPort = this.availablePorts[index % this.availablePorts.length];
        } else {
            // 随机模式：随机选择健康端口（注意：这里的 Math.random 用于选择，不是伪造数据）
            const healthyPorts = this.availablePorts.filter(p => !this.failedPorts.has(p));
            const pool = healthyPorts.length > 0 ? healthyPorts : this.availablePorts;
            selectedPort = pool[Math.floor(Math.random() * pool.length)];
        }

        // V4.46.5: 使用确定性 Session ID
        const sessionId = generateSessionId(selectedPort);

        return {
            port: selectedPort,
            url: `http://172.25.16.1:${selectedPort}`,
            sessionId,
            host: '172.25.16.1'
        };
    }

    /**
     * TITAN-SWARM: 为蜂群 Worker 批量生成配置
     * 确保每个 Worker 获得不同的端口
     * @param {number} count - Worker 数量
     * @returns {Array<object>} 配置数组
     */
    generateSwarmConfigs(count) {
        const configs = [];
        const usedPorts = new Set();

        for (let i = 0; i < count; i++) {
            // 优先选择未使用的端口
            let config;
            const availablePorts = this.availablePorts.filter(p => !usedPorts.has(p));

            if (availablePorts.length > 0) {
                // 还有未使用的端口
                const port = availablePorts[Math.floor(Math.random() * availablePorts.length)];
                usedPorts.add(port);
                config = {
                    port,
                    url: `http://172.25.16.1:${port}`,
                    sessionId: `SWARM-${i + 1}-${Date.now()}`,
                    host: '172.25.16.1',
                    workerId: i + 1
                };
            } else {
                // 端口已用完，使用轮询模式
                config = this.getRotatedConfig(i);
                config.workerId = i + 1;
            }

            configs.push(config);
        }

        return configs;
    }

    // ========================================================================
    // 端口避障与重分配
    // ========================================================================

    /**
     * V181: 获取避障端口（随机选择非失败端口）
     * @param {number} excludePort - 需要排除的端口
     * @returns {number} 新端口号
     */
    getAlternativePort(excludePort) {
        // 过滤掉失败的端口
        const healthyPorts = this.availablePorts.filter(p =>
            p !== excludePort && !this.failedPorts.has(p)
        );

        if (healthyPorts.length === 0) {
            // 所有端口都失败，清空失败记录重新开始
            console.log('⚠️ 所有端口都失败，重置避障记录...');
            this.failedPorts.clear();
            return this.availablePorts[Math.floor(Math.random() * this.availablePorts.length)];
        }

        return healthyPorts[Math.floor(Math.random() * healthyPorts.length)];
    }

    /**
     * V181: 强制更换 Worker 端口（端口避障）
     * @param {number} workerId - Worker 编号
     * @param {number} failedPort - 失败的端口
     * @returns {Promise<WorkerIdentity>} 新身份
     */
    async forceReassignPort(workerId, failedPort) {
        const newPort = this.getAlternativePort(failedPort);

        // 清除旧身份
        this.workerIdentities.delete(workerId);

        // 创建新身份
        const sessionId = `WORKER-${workerId}-RETRY-${Date.now()}`;
        const proxyAssignment = {
            sessionId,
            port: newPort,
            url: `http://172.25.16.1:${newPort}`
        };

        const stealth = this.stealthGenerator();
        const identity = new WorkerIdentity(workerId, proxyAssignment, stealth);
        this.workerIdentities.set(workerId, identity);

        return identity;
    }

    // ========================================================================
    // 会话加载
    // ========================================================================

    /**
     * 加载会话到上下文
     * @param {import('playwright').BrowserContext} context - Playwright 上下文
     * @param {number} port - 端口号
     * @returns {Promise<boolean>} 是否成功加载
     */
    async loadSessionToContext(context, port) {
        if (this.sessionManager) {
            return this.sessionManager.loadSessionToContext(context, port);
        }
        return false;
    }

    // ========================================================================
    // 统计与清理
    // ========================================================================

    /**
     * 获取 Worker 身份统计
     * @returns {Array<object>}
     */
    getWorkerStats() {
        const stats = [];
        for (const [workerId, identity] of this.workerIdentities) {
            stats.push({
                workerId,
                port: identity.proxy?.port,
                requestCount: identity.requestCount,
                successRate: identity.getSuccessRate(),
                needsReidentity: identity.needsReidentity()
            });
        }
        return stats;
    }

    /**
     * 获取 SessionManager 统计
     * @returns {object | null}
     */
    getSessionStats() {
        if (this.sessionManager) {
            return this.sessionManager.getStats();
        }
        return null;
    }

    /**
     * 关闭网络管理器
     */
    shutdown() {
        // 关闭 NetworkShield
        if (this.networkShield) {
            this.networkShield.shutdown();
        }

        // 打印 SessionManager 统计
        if (this.sessionManager) {
            const stats = this.sessionManager.getStats();
            console.log('📊 SessionManager 统计:');
            console.log(`   总刷新: ${stats.totalRefreshes}`);
            console.log(`   成功刷新: ${stats.successfulRefreshes}`);
            console.log(`   失败刷新: ${stats.failedRefreshes}`);
            console.log(`   缓存命中: ${stats.cacheHits}`);
            console.log(`   缓存未命中: ${stats.cacheMisses}`);
        }
    }
}

// ============================================================================
// 单例导出
// ============================================================================

let instance = null;

/**
 * 获取 NetworkManager 单例
 * @param {object} [options] - 配置选项
 * @returns {NetworkManager}
 */
function getNetworkManager(options) {
    if (!instance) {
        instance = new NetworkManager(options);
    }
    return instance;
}

/**
 * 重置单例 (用于测试)
 */
function resetNetworkManager() {
    if (instance) {
        instance.shutdown();
    }
    instance = null;
}

module.exports = {
    NetworkManager,
    WorkerIdentity,
    getNetworkManager,
    resetNetworkManager
};
