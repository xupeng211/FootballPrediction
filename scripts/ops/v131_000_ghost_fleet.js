#!/usr/bin/env node
/**
 * V131.000 - Ghost Fleet Harvesting Mission
 * =============================================================================
 *
 * Full-scale harvesting operation with dynamic proxy discovery,
 * circuit breaker pattern, and stealth mode capabilities.
 *
 * @module v131_000_ghost_fleet
 * @version V131.000
 * @since 2026-01-27
 * @author Senior Lead Quant Engineer (Mission Control)
 *
 * Features:
 *   - 15-lane concurrent processing
 *   - 23-node proxy pool auto-discovery
 *   - Circuit breaker with auto-ejection (3 failures)
 *   - Stealth mode: Cookie dismissal + Jittered delays
 *   - Real-time telemetry every 100 matches
 *
 * @example
 *   ENABLE_PROXY_ROTATION=true PROXY_PORT_START=7891 PROXY_PORT_END=7913 \
 *     CONCURRENT_THREADS=15 node scripts/ops/v131_000_ghost_fleet.js
 */

'use strict';

const path = require('path');
const { QuantHarvester, ProxyPoolManager } = require('../../src/engines/QuantHarvester');

// ============================================================================
// MISSION CONFIGURATION (Environment-First)
// ============================================================================

const MISSION_CONFIG = {
    // Concurrency settings
    concurrent: parseInt(process.env.CONCURRENT_THREADS) || 15,
    batchSize: 50,

    // Proxy rotation (V129.000)
    enableProxyRotation: process.env.ENABLE_PROXY_ROTATION === 'true',
    proxyHost: process.env.PROXY_HOST || '172.25.16.1',
    proxyPortStart: parseInt(process.env.PROXY_PORT_START) || 7891,
    proxyPortEnd: parseInt(process.env.PROXY_PORT_END) || 7913,

    // Stealth mode (V127.000)
    headless: process.env.HEADLESS_MODE !== 'false',
    waitBaseMs: parseInt(process.env.WAIT_BASE_MS) || 2000,
    waitJitterMs: parseInt(process.env.WAIT_JITTER_MS) || 1500,

    // Telemetry
    reportInterval: 100,  // Report every 100 matches

    // Logging
    logLevel: process.env.LOG_LEVEL || 'info'
};

// ============================================================================
// DATABASE: TARGET EXTRACTION
// ============================================================================

/**
 * Extract all matches with status='READY_FOR_V130'
 * @returns {Promise<Array>} Array of match objects
 */
async function extractTargets() {
    const { Client } = require('pg');
    const { getDBConfig } = require('../../scripts/ops/modules/storage');

    const client = new Client(getDBConfig());

    try {
        await client.connect();

        const result = await client.query(`
            SELECT
                mm.fotmob_id as source_id,
                mm.oddsportal_url as source_url,
                m.match_date
            FROM matches_mapping mm
            JOIN matches m ON mm.fotmob_id = m.match_id
            WHERE mm.status = 'READY_FOR_V130'
            ORDER BY m.match_date DESC
        `);

        return result.rows.map(row => ({
            url: row.source_url,
            sourceId: row.source_id,
            matchTime: row.match_date
        }));

    } catch (error) {
        console.error('[V131.000] Failed to extract targets:', error.message);
        return [];
    } finally {
        await client.end().catch(() => {});
    }
}

// ============================================================================
// DATABASE: STATUS UPDATE
// ============================================================================

/**
 * Update match status after harvesting
 * @param {string} sourceId - Match identifier
 * @param {string} status - New status
 * @param {Object} metadata - Additional metadata
 */
async function updateMatchStatus(sourceId, status, metadata = {}) {
    const { Client } = require('pg');
    const { getDBConfig } = require('../../scripts/ops/modules/storage');

    const client = new Client(getDBConfig());

    try {
        await client.connect();

        await client.query(`
            UPDATE matches_mapping
            SET status = $1,
                updated_at = NOW()
            WHERE fotmob_id = $2
        `, [status, sourceId]);

    } catch (error) {
        console.warn(`[V131.000] Failed to update status for ${sourceId}:`, error.message);
    } finally {
        await client.end().catch(() => {});
    }
}

/**
 * Add new enum value for HARVESTED_GOLD_V131
 */
async function prepareDatabaseSchema() {
    const { Client } = require('pg');
    const { getDBConfig } = require('../../scripts/ops/modules/storage');

    const client = new Client(getDBConfig());

    try {
        await client.connect();

        // Try to add the new enum value (will fail if exists)
        try {
            await client.query(`ALTER TYPE mapping_status ADD VALUE 'HARVESTED_GOLD_V131' AFTER 'harvested'`);
            console.log('[V131.000] Added status: HARVESTED_GOLD_V131');
        } catch (e) {
            // Enum value already exists, ignore
        }

    } catch (error) {
        console.warn('[V131.000] Schema prep warning:', error.message);
    } finally {
        await client.end().catch(() => {});
    }
}

// ============================================================================
// TELEMETRY: MISSION DASHBOARD
// ============================================================================

class MissionTelemetry {
    constructor(totalTargets, reportInterval = 100) {
        this.totalTargets = totalTargets;
        this.reportInterval = reportInterval;
        this.processed = 0;
        this.successful = 0;
        this.failed = 0;
        this.totalTrajectoryPoints = 0;
        this.totalTime = 0;
        this.lastReported = 0;
        this.startTime = Date.now();
        this.proxyStats = { healthy: 0, ejected: 0 };
    }

    update(result, proxyStats = null) {
        this.processed++;
        this.totalTime += result.duration || 0;

        if (result.success) {
            this.successful++;
            this.totalTrajectoryPoints += result.trajectoryPoints || 0;
        } else {
            this.failed++;
        }

        if (proxyStats) {
            this.proxyStats = proxyStats;
        }

        // Check if we should report
        if (this.processed - this.lastReported >= this.reportInterval) {
            this.report();
            this.lastReported = Math.floor(this.processed / this.reportInterval) * this.reportInterval;
        }
    }

    report() {
        const elapsed = Date.now() - this.startTime;
        const progress = (this.processed / this.totalTargets * 100).toFixed(1);
        const successRate = (this.successful / this.processed * 100).toFixed(1);
        const avgTime = (this.totalTime / this.processed).toFixed(2);
        const remainingTargets = this.totalTargets - this.processed;
        const eta = remainingTargets * avgTime;
        const etaMinutes = (eta / 60).toFixed(1);

        console.log(`
╔════════════════════════════════════════════════════════════════╗
║  V131.000 GHOST FLEET TELEMETRY                                  ║
╠════════════════════════════════════════════════════════════════╣
║  Progress:    ${this.processed}/${this.totalTargets} (${progress}%)
║  Success Rate: ${successRate}% (${this.successful}✅ / ${this.failed}❌)
║  Alive IPs:    ${this.proxyStats.healthy} healthy, ${this.proxyStats.ejected} ejected
║  Trajectory Points: ${this.totalTrajectoryPoints.toLocaleString()}
║  Avg Time:    ${avgTime}s/match
║  ETA:         ${etaMinutes} minutes
╚════════════════════════════════════════════════════════════════╝
        `.trim());
    }

    getFinalReport() {
        const elapsed = Date.now() - this.startTime;
        const successRate = (this.successful / this.processed * 100).toFixed(2);
        const avgTime = (this.totalTime / this.processed).toFixed(2);

        return {
            totalTargets: this.totalTargets,
            processed: this.processed,
            successful: this.successful,
            failed: this.failed,
            successRate: successRate + '%',
            totalTrajectoryPoints: this.totalTrajectoryPoints,
            avgTimePerMatch: avgTime + 's',
            totalElapsedTime: (elapsed / 1000).toFixed(1) + 's',
            proxyStats: this.proxyStats
        };
    }
}

// ============================================================================
// MAIN MISSION EXECUTOR
// ============================================================================

/**
 * V131.000 Main Mission Class
 */
class GhostFleetMission {
    constructor(config = {}) {
        this.config = { ...MISSION_CONFIG, ...config };
        this.harvester = null;
        this.telemetry = null;
        this.targets = [];
    }

    /**
     * Initialize the mission
     */
    async initialize() {
        console.log('╔════════════════════════════════════════════════════════════════╗');
        console.log('║           V131.000 - GHOST FLEET MISSION                          ║');
        console.log('╚════════════════════════════════════════════════════════════════╝');
        console.log('');

        // Prepare database schema
        await prepareDatabaseSchema();

        // Extract targets
        console.log('[V131.000] Extracting targets from database...');
        this.targets = await extractTargets();

        if (this.targets.length === 0) {
            console.log('[V131.000] No targets found. Mission aborted.');
            return false;
        }

        console.log(`[V131.000] Targets locked: ${this.targets.length} matches`);
        console.log('');

        // Initialize harvester
        console.log('[V131.000] Initializing QuantHarvester...');
        this.harvester = new QuantHarvester({
            headless: this.config.headless,
            enableProxyRotation: this.config.enableProxyRotation,
            proxyHost: this.config.proxyHost,
            proxyPortStart: this.config.proxyPortStart,
            proxyPortEnd: this.config.proxyPortEnd,
            maxConcurrent: this.config.concurrent,
            logLevel: this.config.logLevel
        });

        await this.harvester.init();

        // Initialize telemetry
        this.telemetry = new MissionTelemetry(
            this.targets.length,
            this.config.reportInterval
        );

        console.log('[V131.000] Mission initialized successfully');
        console.log('');

        return true;
    }

    /**
     * Execute the mission
     */
    async execute() {
        if (!this.telemetry) {
            throw new Error('Mission not initialized. Call initialize() first.');
        }

        console.log('╔════════════════════════════════════════════════════════════════╗');
        console.log('║           MISSION EXECUTION PHASE                                ║');
        console.log('╚════════════════════════════════════════════════════════════════╝');
        console.log('');

        const startTime = Date.now();

        // Process targets
        for (const target of this.targets) {
            try {
                const result = await this.harvester.harvestMatch(target.url, target.sourceId);

                // Update telemetry
                const proxyStats = this.harvester.proxyPool.getStats();
                this.telemetry.update(result, {
                    healthy: proxyStats.healthy,
                    ejected: proxyStats.ejected
                });

                // Update database status on success
                if (result.success) {
                    await updateMatchStatus(target.sourceId, 'HARVESTED_GOLD_V131', {
                        trajectoryPoints: result.trajectoryPoints,
                        duration: result.duration
                    });
                }

            } catch (error) {
                console.error(`[V131.000] Error processing ${target.sourceId}:`, error.message);

                // Update telemetry with failure
                this.telemetry.update({ success: false, duration: 0 });
            }
        }

        // Final telemetry report
        console.log('');
        console.log('╔════════════════════════════════════════════════════════════════╗');
        console.log('║           V131.000 - FINAL MISSION REPORT                        ║');
        console.log('╚════════════════════════════════════════════════════════════════╝');
        console.log('');

        const report = this.telemetry.getFinalReport();

        console.log(`Total Targets:       ${report.totalTargets}`);
        console.log(`Processed:           ${report.processed}`);
        console.log(`Successful:          ${report.successful}`);
        console.log(`Failed:              ${report.failed}`);
        console.log(`Success Rate:        ${report.successRate}`);
        console.log(`Trajectory Points:   ${report.totalTrajectoryPoints.toLocaleString()}`);
        console.log(`Avg Time/Match:      ${report.avgTimePerMatch}`);
        console.log(`Total Elapsed:       ${report.totalElapsedTime}`);
        console.log(`Proxy Health:        ${report.proxyStats.healthy} healthy, ${report.proxyStats.ejected} ejected`);
        console.log('');

        return report;
    }

    /**
     * Cleanup resources
     */
    async shutdown() {
        if (this.harvester) {
            console.log('[V131.000] Shutting down harvester...');
            await this.harvester.shutdown();
        }
    }
}

// ============================================================================
// MAIN ENTRY POINT
// ============================================================================

async function main() {
    const mission = new GhostFleetMission();

    try {
        // Initialize
        const initialized = await mission.initialize();
        if (!initialized) {
            process.exit(0);
        }

        // Execute
        const report = await mission.execute();

        // Shutdown
        await mission.shutdown();

        console.log('════════════════════════════════════════════════════════════════');
        console.log('[V131.000] Mission Complete. Good Hunting.');
        console.log('════════════════════════════════════════════════════════════════');

        process.exit(0);

    } catch (error) {
        console.error('[V131.000] Mission Failed:', error);
        await mission.shutdown();
        process.exit(1);
    }
}

// Run if executed directly
if (require.main === module) {
    main().catch(error => {
        console.error('[V131.000] Unhandled error:', error);
        process.exit(1);
    });
}

// ============================================================================
// EXPORTS
// ============================================================================

module.exports = {
    GhostFleetMission,
    extractTargets,
    updateMatchStatus,
    prepareDatabaseSchema,
    MissionTelemetry
};
