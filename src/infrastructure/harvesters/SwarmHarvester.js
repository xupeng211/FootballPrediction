/**
 * SwarmHarvester - TITAN 蜂群收割指挥官
 * ======================================
 *
 * 功能：多线程并发收割，利用 22 个代理节点实现吞吐量最大化
 *
 * 特性:
 * - 动态 IP 轮询：每个 Worker 使用不同代理端口
 * - 安全错峰：Worker 启动时间错开 3-5 秒，防止 CPU 瞬时爆表
 * - 故障隔离：单个 Worker 失败不影响其他 Worker
 * - 实时监控：输出每个 Worker 的进度和状态
 *
 * @module infrastructure/harvesters/SwarmHarvester
 * @version V4.46-SWARM
 */

'use strict';

const pLimit = require('p-limit');
const { ProductionHarvester } = require('./ProductionHarvester');
const { getNetworkManager } = require('../network/NetworkManager');
const FactoryConfig = require('../../../config/factory_config');

// ============================================================================
// SwarmHarvester - 蜂群收割指挥官
// ============================================================================

class SwarmHarvester {
    /**
     * 创建蜂群收割器实例
     * @param {Object} [config={}] - 配置选项
     * @param {number} [config.concurrency=3] - 并发 Worker 数量
     * @param {number} [config.staggerStartMs=5000] - Worker 启动错峰间隔 (ms)
     * @param {boolean} [config.verboseLogging=true] - 详细日志
     */
    constructor(config = {}) {
        this.config = {
            concurrency: config.concurrency || 3,
            staggerStartMs: config.staggerStartMs || 5000,
            staggerJitterMs: config.staggerJitterMs || 2000, // 随机抖动
            verboseLogging: config.verboseLogging !== false,
            ...config
        };

        // NetworkManager 用于获取代理配置
        this.networkManager = getNetworkManager();

        // 统计信息
        this.stats = {
            total: 0,
            completed: 0,
            success: 0,
            failed: 0,
            startTime: null,
            workerStats: new Map() // 每个 Worker 的统计
        };

        // 活跃 Worker 追踪
        this.activeWorkers = new Map();
    }

    // ========================================================================
    // 核心 API: 批量并发收割
    // ========================================================================

    /**
     * 批量并发收割比赛数据
     * @param {Array<string|number>} matchIds - 比赛 ID 列表
     * @param {number} [concurrency] - 并发数（覆盖构造函数配置）
     * @returns {Promise<Object>} 收割结果统计
     */
    async batchRun(matchIds, concurrency) {
        const actualConcurrency = concurrency || this.config.concurrency;

        if (!matchIds || matchIds.length === 0) {
            console.log('⚠️ 没有提供比赛 ID，无需收割');
            return { success: false, reason: 'EMPTY_MATCH_LIST' };
        }

        this.stats.total = matchIds.length;
        this.stats.startTime = Date.now();

        console.log('╔═══════════════════════════════════════════════════════════════╗');
        console.log('║  🐝 TITAN-SWARM 蜂群收割引擎激活                              ║');
        console.log('║  并发模式 | 动态 IP 轮询 | 安全错峰启动 | 故障隔离            ║');
        console.log('╚═══════════════════════════════════════════════════════════════╝');
        console.log(`📊 任务: ${matchIds.length} 场比赛`);
        console.log(`🐝 并发: ${actualConcurrency} 个 Worker`);
        console.log(`⏱️  错峰: ${this.config.staggerStartMs}ms ± ${this.config.staggerJitterMs}ms`);
        console.log('');

        // 为每个 Worker 预分配代理配置（确保 IP 不重复）
        const swarmConfigs = this.networkManager.generateSwarmConfigs(actualConcurrency);

        console.log('📡 代理分配:');
        swarmConfigs.forEach(cfg => {
            console.log(`   Worker-${cfg.workerId}: Port ${cfg.port}`);
        });
        console.log('');

        // 创建并发限制器
        const limit = pLimit(actualConcurrency);

        // 启动蜂群收割
        const results = await Promise.all(
            matchIds.map((matchId, index) =>
                limit(async () => {
                    const workerId = (index % actualConcurrency) + 1;
                    const proxyConfig = swarmConfigs[workerId - 1];

                    return this._swarmHarvest(matchId, workerId, proxyConfig, index);
                })
            )
        );

        // 汇总统计
        this._aggregateResults(results);

        return this._generateReport();
    }

    /**
     * 单场比赛收割（指定 Worker 和代理配置）
     * @private
     * @param {string|number} matchId - 比赛 ID
     * @param {number} workerId - Worker 编号
     * @param {Object} proxyConfig - 代理配置
     * @param {number} index - 任务索引
     * @returns {Promise<Object>} 收割结果
     */
    async _swarmHarvest(matchId, workerId, proxyConfig, index) {
        const startTime = Date.now();

        // 初始化 Worker 统计
        if (!this.stats.workerStats.has(workerId)) {
            this.stats.workerStats.set(workerId, {
                workerId,
                port: proxyConfig.port,
                total: 0,
                success: 0,
                failed: 0,
                tasks: []
            });
        }
        const workerStat = this.stats.workerStats.get(workerId);
        workerStat.total++;

        // 安全错峰：第一个 Worker 立即启动，后续错开
        if (index >= 0) {
            const delay = this._calculateStaggerDelay(index);
            if (delay > 0) {
                console.log(`⏱️  Worker-${workerId} 错峰等待 ${delay}ms...`);
                await this._delay(delay);
            }
        }

        // 标记 Worker 为活跃状态
        this.activeWorkers.set(workerId, {
            matchId,
            startTime: Date.now(),
            port: proxyConfig.port
        });

        console.log(`🐝 Worker-${workerId} [Port ${proxyConfig.port}] 开始收割: Match ${matchId}`);

        try {
            // 创建独立的 Harvester 实例
            const harvester = new ProductionHarvester({
                maxWorkers: 1, // 单个 Worker 内部不并发
                verboseLogging: this.config.verboseLogging,
                ...this.config.harvesterOptions
            });

            // 初始化（浏览器、数据库等）
            await harvester.init();

            // 强制替换 Worker 身份为预分配的代理配置
            await this._injectWorkerIdentity(harvester, workerId, proxyConfig);

            // 执行收割
            const result = await harvester.run({ matchId });

            // 清理资源
            await harvester.cleanup();

            // 更新统计
            const duration = Date.now() - startTime;
            if (result.success) {
                workerStat.success++;
                console.log(`✅ Worker-${workerId} [Port ${proxyConfig.port}] 完成: Match ${matchId} (${duration}ms)`);
            } else {
                workerStat.failed++;
                console.log(`❌ Worker-${workerId} [Port ${proxyConfig.port}] 失败: Match ${matchId} - ${result.error || 'Unknown'}`);
            }

            workerStat.tasks.push({
                matchId,
                success: result.success,
                duration,
                error: result.error
            });

            return {
                success: result.success,
                matchId,
                workerId,
                port: proxyConfig.port,
                duration,
                error: result.error
            };

        } catch (error) {
            const duration = Date.now() - startTime;
            workerStat.failed++;
            console.error(`💥 Worker-${workerId} [Port ${proxyConfig.port}] 异常: Match ${matchId} - ${error.message}`);

            workerStat.tasks.push({
                matchId,
                success: false,
                duration,
                error: error.message
            });

            return {
                success: false,
                matchId,
                workerId,
                port: proxyConfig.port,
                duration,
                error: error.message
            };

        } finally {
            // 移除活跃标记
            this.activeWorkers.delete(workerId);
        }
    }

    // ========================================================================
    // 辅助方法
    // ========================================================================

    /**
     * 计算错峰启动延迟
     * @private
     * @param {number} index - 任务索引
     * @returns {number} 延迟毫秒数
     */
    _calculateStaggerDelay(index) {
        // 第一个任务立即启动
        if (index === 0) return 0;

        // 基础错峰延迟 + 随机抖动
        const baseDelay = Math.floor(index / this.config.concurrency) * this.config.staggerStartMs;
        const jitter = Math.floor(Math.random() * this.config.staggerJitterMs);

        return Math.min(baseDelay + jitter, 30000); // 最大 30 秒
    }

    /**
     * 强制注入 Worker 身份到 Harvester
     * @private
     * @param {ProductionHarvester} harvester - Harvester 实例
     * @param {number} workerId - Worker ID
     * @param {Object} proxyConfig - 代理配置
     */
    async _injectWorkerIdentity(harvester, workerId, proxyConfig) {
        // 创建 Worker 身份
        const { WorkerIdentity } = require('../network/NetworkManager');
        const { generateStealthHeaders } = require('../network/StealthFingerprint');

        const stealth = generateStealthHeaders();
        const identity = new WorkerIdentity(workerId, proxyConfig, stealth);

        // 注入到 Harvester 的 NetworkManager
        if (harvester.networkManager) {
            harvester.networkManager.workerIdentities.set(workerId, identity);
        }
    }

    /**
     * 汇总结果
     * @private
     * @param {Array<Object>} results - 结果数组
     */
    _aggregateResults(results) {
        this.stats.completed = results.length;
        this.stats.success = results.filter(r => r.success).length;
        this.stats.failed = results.filter(r => !r.success).length;
    }

    /**
     * 生成收割报告
     * @private
     * @returns {Object} 报告对象
     */
    _generateReport() {
        const elapsed = Date.now() - this.stats.startTime;
        const rate = this.stats.total > 0
            ? ((this.stats.success / this.stats.total) * 100).toFixed(1)
            : '0.0';

        console.log('');
        console.log('╔═══════════════════════════════════════════════════════════════╗');
        console.log('║  📊 TITAN-SWARM 蜂群收割完成报告                              ║');
        console.log('╚═══════════════════════════════════════════════════════════════╝');
        console.log(`  总任务: ${this.stats.total} 场`);
        console.log(`  完成: ${this.stats.completed} 场`);
        console.log(`  成功: ${this.stats.success} 场`);
        console.log(`  失败: ${this.stats.failed} 场`);
        console.log(`  成功率: ${rate}%`);
        console.log(`  总耗时: ${(elapsed / 1000).toFixed(1)} 秒`);
        console.log(`  平均速度: ${(this.stats.completed / (elapsed / 1000)).toFixed(2)} 场/秒`);
        console.log('');
        console.log('  Worker 详情:');
        for (const [workerId, stat] of this.stats.workerStats) {
            const workerRate = stat.total > 0 ? ((stat.success / stat.total) * 100).toFixed(0) : 0;
            console.log(`    Worker-${workerId} [Port ${stat.port}]: ${stat.success}/${stat.total} (${workerRate}%)`);
        }
        console.log('═══════════════════════════════════════════════════════════════');

        return {
            total: this.stats.total,
            completed: this.stats.completed,
            success: this.stats.success,
            failed: this.stats.failed,
            successRate: parseFloat(rate),
            elapsedMs: elapsed,
            avgSpeed: this.stats.completed / (elapsed / 1000),
            workerDetails: Array.from(this.stats.workerStats.values())
        };
    }

    /**
     * 延迟辅助方法
     * @private
     * @param {number} ms - 毫秒数
     * @returns {Promise<void>}
     */
    _delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // ========================================================================
    // 实时监控 API
    // ========================================================================

    /**
     * 获取当前活跃 Worker 状态
     * @returns {Array<Object>} 活跃 Worker 列表
     */
    getActiveWorkers() {
        const workers = [];
        for (const [workerId, info] of this.activeWorkers) {
            workers.push({
                workerId,
                ...info,
                elapsedMs: Date.now() - info.startTime
            });
        }
        return workers;
    }

    /**
     * 获取统计信息
     * @returns {Object} 统计对象
     */
    getStats() {
        return {
            ...this.stats,
            workerStats: Array.from(this.stats.workerStats.values()),
            activeWorkers: this.getActiveWorkers()
        };
    }
}

// ============================================================================
// 便捷函数
// ============================================================================

/**
 * 快速启动蜂群收割
 * @param {Array<string|number>} matchIds - 比赛 ID 列表
 * @param {number} [concurrency=3] - 并发数
 * @param {Object} [options={}] - 额外配置
 * @returns {Promise<Object>} 收割结果
 */
async function swarmHarvest(matchIds, concurrency = 3, options = {}) {
    const swarm = new SwarmHarvester({
        concurrency,
        ...options
    });

    return await swarm.batchRun(matchIds, concurrency);
}

// ============================================================================
// 导出
// ============================================================================

module.exports = {
    SwarmHarvester,
    swarmHarvest
};
