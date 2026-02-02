/**
 * QuantHarvester - V168.000 [Genesis.Solidify] Edition
 * =======================================================
 *
 * [Genesis.Solidify] 实战收割逻辑固化至主干
 *
 * Core Features:
 * - Native Concurrency: Built-in p-limit task scheduling
 * - Auto-Healing: Retry logic for failed extractions
 * - Fast Fail: Optimized SurgicalInteraction integration
 * - Unified Config: Powered by EngineConfig
 * - Multi-Source Storage: Writes to metrics_multi_source_data
 *
 * @module engines/QuantHarvester
 * @version V168.000
 * @since 2026-02-02
 * @author [Genesis.Solidify]
 */

'use strict';

const { chromium } = require('playwright');
const pLimit = require('p-limit');
const { createPool } = require('../../../scripts/ops/modules/storage');
const { EngineConfig } = require('./config/EngineConfig');
const { TrajectoryParser } = require('./parsers/TrajectoryParser');
const { SurgicalInteraction } = require('./services/SurgicalInteraction');
const { SignalRadar } = require('./services/SignalRadar');

const { RadarLogger } = require('./services/logging/RadarLogger');

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
    }

    /**
     * Initialize resources (DB Pool)
     */
    async init() {
        if (!this.pool) {
            this.pool = createPool();
            this.logger.info('DB Pool Initialized');
        }
    }

    /**
     * Batch Harvest Entry Point
     * @param {Array} matches - Array of match objects {id, url, ...}
     */
    async harvestBatch(matches) {
        if (!this.pool) await this.init();

        const concurrency = this.config.concurrency.MAX_CONCURRENT_BROWSERS || 15;
        const limit = pLimit(concurrency);
        
        this.logger.info(`Starting batch harvest. Concurrency: ${concurrency}, Total: ${matches.length}`);

        const tasks = matches.map(match => limit(async () => {
            try {
                return await this.processMatch(match);
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
     * Single Match Harvest Logic (Solidified from v168)
     * @param {Object} match - {id, url, ...}
     */
    async processMatch(match) {
        const startTime = Date.now();
        // Launch isolated browser per match (V168 Strategy)
        // Note: In high-scale, might want to move to context reuse, but adhering to V168 for stability.
        const browser = await chromium.launch({
            headless: this.config.concurrency.headless !== false, // default true
            args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        });

        let success = false;
        let dataPoints = 0;
        let method = 'UNKNOWN';

        try {
            const page = await browser.newPage();
            // Use config-driven timeouts
            const timeout = this.config.harvest.RENDER_WINDOW || 60000;
            
            // Initialize Services
            const radar = new SignalRadar(page, { 
                logLevel: this.config.logLevel.toLowerCase(),
                memoryHookTimeout: this.config.timeouts.MEMORY_HOOK_TIMEOUT,
                domFallbackTimeout: this.config.timeouts.DOM_FALLBACK_TIMEOUT
            });
            const surgical = new SurgicalInteraction(page, this.config);

            // Step 1: Enable Trigger Mode
            let triggerPromise = radar.enableTriggerMode(surgical, {
                renderWindow: timeout,
                enableTrajectoryCapture: true
            });

            // Step 2: Navigate
            await page.goto(match.url, { 
                waitUntil: 'networkidle', 
                timeout: timeout 
            });

            // Step 3: Handle Overlays & Activate
            await surgical.handleOverlays();

            // Step 4: Wait for Trigger Result
            let triggerResult = await triggerPromise;

            // [Auto-Healing] Retry Logic
            if (!triggerResult.success) {
                this.logger.warn(`⚠️ Retrying ${match.id}...`);
                
                triggerPromise = radar.enableTriggerMode(surgical, {
                    renderWindow: timeout,
                    enableTrajectoryCapture: true
                });

                await page.reload({ waitUntil: 'networkidle', timeout: timeout });
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

            // [Validation Gate]
            const bet365Data = processedData.find(p => p.provider === 'bet365');
            const hasValidBet365 = bet365Data && bet365Data.opening && bet365Data.closing;

            if (!hasValidBet365 && processedData.length < this.config.harvest.MIN_PROVIDERS) {
                throw new Error('Gate: No valid data (bet365 missing Opening/Closing or insufficient providers)');
            }

            // Step 6: Trajectory Simulation (Gap Filling)
            this._simulateTrajectories(processedData);

            // Step 7: Save to DB
            await this._saveToDb(match.id, processedData);

            success = true;
            dataPoints = processedData.reduce((sum, p) => sum + (p.curve ? p.curve.length : 0), 0);
            
            this.logger.info(`✅ SLAIN: ${match.id} | Points: ${dataPoints} | Method: ${method}`);

        } catch (error) {
            this.logger.error(`❌ Failed ${match.id}: ${error.message}`);
            throw error;
        } finally {
            await browser.close();
        }

        return {
            success,
            matchId: match.id,
            dataPoints,
            method,
            elapsed: Date.now() - startTime
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

    async shutdown() {
        if (this.pool) {
            await this.pool.end();
        }
    }
}

module.exports = { QuantHarvester };