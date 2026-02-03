/**
 * QuantHarvester - V170.000 [Genesis.NetworkShield] Edition
 * ===================================================================
 *
 * [Genesis.NetworkShield] 工业级跨语言代理管理组件集成
 *
 * Core Features:
 * - Native Concurrency: Built-in p-limit task scheduling
 * - Auto-Healing: Retry logic for failed extractions
 * - Fast Fail: Optimized SurgicalInteraction integration
 * - Unified Config: Powered by EngineConfig
 * - Multi-Source Storage: Writes to metrics_multi_source_data
 * - NetworkShield: 22-node industrial-grade proxy management
 * - Dual-Mode Extraction: 20s fast fallback to DOM scraping
 * - Random Delay: 2000-5000ms random pulse between matches
 * - Session Binding: One session = One clean IP
 *
 * @module engines/QuantHarvester
 * @version V170.000
 * @since 2026-02-03
 * @author [Genesis.NetworkShield]
 */

'use strict';

const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');
const pLimit = require('p-limit');
const { createPool } = require('../../../scripts/ops/modules/storage');
const { EngineConfig } = require('./config/EngineConfig');
const { TrajectoryParser } = require('./parsers/TrajectoryParser');
const { SurgicalInteraction } = require('./services/SurgicalInteraction');
const { SignalRadar } = require('./services/SignalRadar');
const { getNetworkShield } = require('../network/NetworkShield');

const { RadarLogger } = require('./services/logging/RadarLogger');

// ============================================================================
// NETWORK SHIELD ADAPTER - V170.000
// ============================================================================

/**
 * NetworkShieldAdapter - NetworkShield 适配器
 *
 * 将 NetworkShield 的工业级代理管理能力集成到 QuantHarvester。
 * 提供 Session 绑定、智能轮换、自愈熔断等核心功能。
 *
 * 功能:
 * - 通过 NetworkShield.getNextHealthyProxy() 获取健康节点
 * - Session 绑定确保一个浏览器会话始终使用同一 IP
 * - 自动处理成功/失败状态上报
 * - 兼容原有 ProxyPoolManager 接口
 */
class NetworkShieldAdapter {
    constructor(logger) {
        this.logger = logger;
        this.shield = getNetworkShield({ logLevel: 'info' });
        this.matchSessions = new Map(); // matchId -> sessionId
        this.sessionCounter = 0;
    }

    /**
     * 初始化 NetworkShield
     */
    async init() {
        try {
            await this.shield.initialize();
            const status = this.shield.getStatus();
            this.logger.info(
                `[NetworkShield] Initialized: ${status.nodes.active}/${status.nodes.total} nodes available`
            );
        } catch (error) {
            this.logger.error(`[NetworkShield] Init failed: ${error.message}`);
        }
    }

    /**
     * 获取下一个可用代理（兼容接口）
     * @param {string} matchId - 比赛ID（用于 Session 绑定）
     * @returns {Object|null} { port, url, id, latency }
     */
    async getNextProxy(matchId = null) {
        try {
            const sessionId = matchId ? `MATCH-${matchId}` : `AUTO-${this.sessionCounter++}`;
            const proxy = await this.shield.getNextHealthyProxy(sessionId);

            if (!proxy) {
                return null;
            }

            // 记录会话绑定
            if (matchId) {
                this.matchSessions.set(matchId, sessionId);
            }

            // 转换为兼容格式
            return {
                port: proxy.port,
                url: proxy.url,
                id: proxy.id || `NODE-${proxy.port}`,
                latency: 0, // NetworkShield 内部维护
                sessionId: proxy.sessionId
            };
        } catch (error) {
            this.logger.error(`[NetworkShield] Get proxy failed: ${error.message}`);
            return null;
        }
    }

    /**
     * 标记代理成功
     * @param {number} port - 代理端口
     */
    async markProxySuccess(port) {
        if (port) {
            await this.shield.markProxySuccess(port);
        }
    }

    /**
     * 标记代理失败
     * @param {number} port - 代理端口
     * @param {string} reason - 失败原因
     */
    async markProxyFailed(port, reason = 'Unknown') {
        if (port) {
            await this.shield.markProxyFailed(port, reason);
        }
    }

    /**
     * 释放会话
     * @param {string} matchId - 比赛ID
     */
    releaseSession(matchId) {
        const sessionId = this.matchSessions.get(matchId);
        if (sessionId) {
            this.shield.releaseSession(sessionId);
            this.matchSessions.delete(matchId);
        }
    }

    /**
     * 获取统计信息
     */
    getStats() {
        return this.shield.getStatus();
    }

    /**
     * 重置所有节点
     */
    async resetBlacklist() {
        await this.shield.resetAllNodes();
    }
}

// Provider ID Mapping (internal to DB)
const PROVIDER_MAP = {
    'Pinnacle': 18,
    'bet365': 32,
    'William Hill': 25679340,
    'Ladbrokes': 16,
    'Bwin': 2,
    '1xBet': 2,
    'Unibet': 5,
    'Average': 999
};

class QuantHarvester {
    constructor(config = {}) {
        this.config = new EngineConfig(config);
        this.pool = null; // DB Pool
        this.parser = new TrajectoryParser();
        this.logger = new RadarLogger({
            prefix: '[QuantHarvester]',
            level: this.config.logLevel.toLowerCase()
        });

        // V170.000: 初始化 NetworkShield 适配器
        this.proxyPool = new NetworkShieldAdapter(this.logger);
        this.enableProxy = config.enableProxy !== false; // 默认启用

        // [V169.700] Concurrency Cap (Hard Locked to 5)
        this.config.concurrency.MAX_CONCURRENT_BROWSERS = 5;

        // [V169.700] Human Stealth Delay (2000-8000ms)
        this.randomDelay = {
            enabled: config.randomDelay !== false,
            min: config.randomDelayMin || 2000,
            max: config.randomDelayMax || 8000
        };
    }

    /**
     * Initialize resources (DB Pool + NetworkShield)
     */
    async init() {
        if (!this.pool) {
            this.pool = createPool();
            this.logger.info('DB Pool Initialized');
        }

        // V170.000: 初始化 NetworkShield
        await this.proxyPool.init();

        const proxyStats = this.proxyPool.getStats();
        this.logger.info(
            `[NetworkShield] Status: ${proxyStats.nodes.active}/${proxyStats.nodes.total} nodes available, ` +
            `Proxy: ${this.enableProxy ? 'ENABLED' : 'DISABLED'}`
        );

        // V169.300: 输出随机延迟配置
        if (this.randomDelay.enabled) {
            this.logger.info(
                `[StealthMode] Human-Pulse Delay: ${this.randomDelay.min}-${this.randomDelay.max}ms ` +
                `(between matches)`
            );
        }
    }

    /**
     * V169.300: 生成随机延迟
     * @returns {number} 延迟毫秒数
     */
    _getRandomDelay() {
        if (!this.randomDelay.enabled) return 0;
        const range = this.randomDelay.max - this.randomDelay.min;
        return Math.floor(Math.random() * range) + this.randomDelay.min;
    }

    /**
     * V169.300: Batch Harvest with Stealth Mode (Random Delay)
     * @param {Array} matches - Array of match objects {id, url, ...}
     */
    async harvestBatch(matches) {
        if (!this.pool) await this.init();

        const concurrency = this.config.concurrency.MAX_CONCURRENT_BROWSERS || 5;

        this.logger.info(`Starting batch harvest. Concurrency: ${concurrency}, Total: ${matches.length}`);

        // V169.300: 使用并发队列 + 随机延迟
        const limit = pLimit(concurrency);

        const tasks = matches.map(match => limit(async () => {
            try {
                // [V169.700] Add random pulse delay before match start
                if (this.randomDelay.enabled) {
                    const pulse = this._getRandomDelay();
                    this.logger.debug(`[StealthMode] Pulsing: ${pulse}ms`);
                    await new Promise(resolve => setTimeout(resolve, pulse));
                }

                const r = await this.processMatch(match);
                return r;
            } catch (e) {
                this.logger.error(`Task failed for ${match.id}: ${e.message}`);
                return { success: false, matchId: match.id, error: e.message };
            }
        }));

        const results = await Promise.all(tasks);

        const stats = results.reduce((acc, r) => {
            if (r.success) acc.success++; else acc.failed++;
            return acc;
        }, { success: 0, failed: 0 });

        this.logger.info(`Batch complete. Success: ${stats.success}, Failed: ${stats.failed}`);
        return results;
    }

    /**
     * Single Match Harvest Logic (V170.000 with NetworkShield Integration)
     * @param {Object} match - {id, url, ...}
     */
    async processMatch(match) {
        const startTime = Date.now();

        // V170.000: 获取代理节点（Session 绑定）
        const proxy = this.enableProxy ? await this.proxyPool.getNextProxy(match.id) : null;
        const usedProxyPort = proxy ? proxy.port : null;

        // Launch isolated browser per match (V168 Strategy)
        const browser = await chromium.launch({
            headless: this.config.concurrency.headless !== false,
            // V169.100: 添加代理配置
            ...(proxy ? { proxy: { server: proxy.url } } : {}),
            args: [
                '--no-sandbox', 
                '--disable-setuid-sandbox', 
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled'
            ]
        });

        let success = false;
        let dataPoints = 0;
        let method = 'UNKNOWN';

        try {
            const page = await browser.newPage();
            // [V169.700] Tighter 15s fallback for match-events
            const renderTimeout = 15000;
            const fullTimeout = this.config.harvest.RENDER_WINDOW || 60000;

            // Initialize Services
            const radar = new SignalRadar(page, {
                logLevel: this.config.logLevel.toLowerCase(),
                memoryHookTimeout: renderTimeout,
                domFallbackTimeout: this.config.timeouts.DOM_FALLBACK_TIMEOUT || 5000,
                matchId: match.id 
            });
            const surgical = new SurgicalInteraction(page, this.config);

            // Step 1: Enable Trigger Mode
            let triggerPromise = radar.enableTriggerMode(surgical, {
                renderWindow: fullTimeout,
                enableTrajectoryCapture: true
            });

            // Step 2: Navigate
            await page.goto(match.url, {
                waitUntil: 'domcontentloaded',
                timeout: fullTimeout
            });

            // Step 3: Handle Overlays & Activate
            await surgical.handleOverlays();

            // Step 4: Wait for Trigger Result
            let triggerResult = await triggerPromise;

            // [Auto-Healing] Retry Logic
            if (!triggerResult.success) {
                this.logger.warn(`⚠️ Retrying ${match.id}...`);

                triggerPromise = radar.enableTriggerMode(surgical, {
                    renderWindow: fullTimeout,
                    enableTrajectoryCapture: true
                });

                await page.reload({ waitUntil: 'domcontentloaded', timeout: fullTimeout });
                await surgical.handleOverlays();

                triggerResult = await triggerPromise;
            }

            if (!triggerResult.success || !triggerResult.extractedData || triggerResult.extractedData.length === 0) {
                throw new Error(triggerResult.error || 'No data extracted');
            }

            method = triggerResult.method;

            // Step 5: Parse Data
            const processedData = this.parser.processDeepL3Data(
                triggerResult.extractedData,
                { matchId: match.id, matchTime: new Date().toISOString() }
            );

            // [Validation Gate] - [V169.700] Stricter Provider Check
            const bet365Data = processedData.find(p => p.provider === 'bet365');
            const hasValidBet365 = bet365Data && bet365Data.opening && bet365Data.closing;

            if (!hasValidBet365) {
                // If fallback also failed to get bet365, trigger proxy fail count
                throw new Error('PROVIDER_NOT_FOUND: bet365 missing Opening/Closing');
            }

            // Step 6: Trajectory Simulation (Gap Filling)
            this._simulateTrajectories(processedData);

            // Step 7: Save to DB
            await this._saveToDb(match.id, processedData);

            success = true;
            dataPoints = processedData.reduce((sum, p) => sum + (p.curve ? p.curve.length : 0), 0);

            this.logger.info(
                `✅ SLAIN: ${match.id} | Points: ${dataPoints} | Method: ${method}` +
                `${usedProxyPort ? ` | Proxy: ${usedProxyPort}` : ''}`
            );

            // V170.000: 标记代理成功
            if (usedProxyPort) {
                await this.proxyPool.markProxySuccess(usedProxyPort);
            }

            // V170.000: 释放会话
            if (match.id) {
                this.proxyPool.releaseSession(match.id);
            }

        } catch (error) {
            this.logger.error(
                `❌ Failed ${match.id}: ${error.message}` +
                `${usedProxyPort ? ` | Proxy: ${usedProxyPort}` : ''}`
            );

            // V170.000: 标记代理失败
            if (usedProxyPort) {
                await this.proxyPool.markProxyFailed(usedProxyPort, error.message);
            }

            // V170.000: 释放会话
            if (match.id) {
                this.proxyPool.releaseSession(match.id);
            }
        } finally {
            await browser.close();
        }

        return {
            success,
            matchId: match.id,
            dataPoints,
            method,
            elapsed: Date.now() - startTime,
            proxyPort: usedProxyPort
        };
    }

    /**
     * Helper: Simulate trajectories for missing curves
     * @private
     */
    _simulateTrajectories(dataList) {
        dataList.forEach(p => {
            if (!p.curve || p.curve.length === 0) {
                if (p.instant) {
                    const now = Date.now() / 1000;
                    p.curve = [
                        { t: now, v: p.instant, iso: new Date().toISOString(), type: 'Simulated' },
                        { t: now + 1, v: p.instant, iso: new Date().toISOString(), type: 'Simulated' }
                    ];
                    // Ensure opening/closing exist if we simulate
                    if (!p.opening) p.opening = { val: p.instant, time: new Date().toISOString() };
                    if (!p.closing) p.closing = { val: p.instant, time: new Date().toISOString() };
                }
            }
        });
    }

    /**
     * Helper: Save to DB (metrics_multi_source_data)
     * V168.001: 增强异常安全性，确保 client 在所有情况下都被释放
     * @private
     */
    async _saveToDb(matchId, dataList) {
        let client = null;
        try {
            client = await this.pool.connect();
            await client.query('BEGIN');

            for (const data of dataList) {
                const providerId = PROVIDER_MAP[data.provider] || 999;
                const sourceName = `Entity_${data.provider.replace(/\s+/g, '')}`;

                const opening = data.opening || {};
                const closing = data.closing || {};

                // Use the v168 query structure
                const query = `
                    INSERT INTO metrics_multi_source_data (
                        match_id, source_name,
                        init_h, init_d, init_a,
                        final_h, final_d, final_a,
                        odds_history, market_payout, provider_internal_id,
                        integrity_score, is_valid, data_timestamp
                    ) VALUES (
                        $1, $2,
                        $3, $4, $5,
                        $6, $7, $8,
                        $9::jsonb, $10, $11,
                        $12, $13, NOW()
                    )
                    ON CONFLICT (match_id, source_name)
                    DO UPDATE SET
                        init_h = EXCLUDED.init_h,
                        init_d = EXCLUDED.init_d,
                        init_a = EXCLUDED.init_a,
                        final_h = EXCLUDED.final_h,
                        final_d = EXCLUDED.final_d,
                        final_a = EXCLUDED.final_a,
                        odds_history = EXCLUDED.odds_history,
                        market_payout = EXCLUDED.market_payout,
                        provider_internal_id = EXCLUDED.provider_internal_id,
                        data_timestamp = NOW()
                `;

                await client.query(query, [
                    matchId,
                    sourceName,
                    opening.val || null, null, null,
                    closing.val || null, null, null,
                    JSON.stringify(data.curve),
                    data.market_payout || null,
                    providerId,
                    1.05, // Integrity Score default
                    true
                ]);
            }

            await client.query('COMMIT');
        } catch (error) {
            // V168.001: Safe ROLLBACK with client existence check
            if (client) {
                try {
                    await client.query('ROLLBACK');
                } catch (rollbackError) {
                    console.error('[V168.001] ROLLBACK error:', rollbackError.message);
                }
            }
            throw error;
        } finally {
            // V168.001: Defensive client release with null check
            if (client) {
                try {
                    client.release();
                } catch (releaseError) {
                    console.error('[V168.001] Client release error:', releaseError.message);
                }
            }
        }
    }

    /**
     * Legacy single match wrapper for backward compatibility
     */
    async harvestMatch(url, sourceId) {
        // Adapt single call to new processMatch
        await this.init();
        return this.processMatch({ id: sourceId, url: url });
    }

    /**
     * V169.100: 获取代理池统计
     */
    getProxyStats() {
        return this.proxyPool.getStats();
    }

    /**
     * V169.100: 重置代理池黑名单
     */
    resetProxyBlacklist() {
        this.proxyPool.resetBlacklist();
    }

    async shutdown() {
        if (this.pool) {
            await this.pool.end();
        }
    }
}

module.exports = { QuantHarvester };