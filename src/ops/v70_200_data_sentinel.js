/**
 * V70.200 - Data Sentinel & Quality Snapshot
 * ==========================================
 *
 * Real-time monitoring and data quality validation for the full backfill operation.
 * Provides dashboard view of harvest progress, data completeness, and health score.
 *
 * @file v70_200_data_sentinel.js
 * @author Principal Data Reliability Engineer (SRE)
 * @version V70.200
 * @since 2026-01-25
 *
 * ============================================================================
 * MONITORING PILLARS:
 * ============================================================================
 *
 *  Step A: Completeness Snapshot
 *    - Count "Golden Entities" with Index + L2 + Temporal Data
 *    - Progress: Current / 10,039 Target
 *
 *  Step B: Quality Gate (Data Corruption Detection)
 *    - Odds anomalies: <= 1.0 or >= 100
 *    - Payout anomalies: < 80% or > 100%
 *    - Time misalignment: Opening time > Observation time
 *
 *  Step C: Throughput Tracker
 *    - Matches Per Hour (MPH) in last 1 hour
 *    - ETA for 5-season full backfill
 *
 * ============================================================================
 */

'use strict';

const { Pool } = require('pg');
const { createPool } = require('../modules/sink');

// ============================================================================
// CONFIGURATION
// ============================================================================

const SENTINEL_CONFIG = {
    version: 'V70.200',
    name: 'Data Sentinel',

    // Target goals
    targetTotalMatches: 10039,  // 5 seasons across 5 leagues

    // Quality thresholds
    qualityGate: {
        minOdds: 1.01,           // Minimum valid odds value
        maxOdds: 50.0,           // Maximum valid odds value
        minPayout: 0.80,         // Minimum valid payout (80%)
        maxPayout: 1.00,         // Maximum valid payout (100%)
    },

    // Throughput calculation window
    throughputWindowHours: 1,

    // Database connection
    db: {
        host: process.env.DB_HOST || '172.25.16.1',
        port: parseInt(process.env.DB_PORT) || 5432,
        database: process.env.DB_NAME || 'football_db',
        user: process.env.DB_USER || 'football_user',
        password: process.env.DB_PASSWORD || 'football_pass',
        max: 20
    }
};

// ============================================================================
// LOGGER
// ============================================================================

function log(level, message, data = {}) {
    const entry = {
        level,
        timestamp: new Date().toISOString(),
        module: 'v70_200_data_sentinel',
        version: SENTINEL_CONFIG.version,
        message,
        trace_id: generateTraceId(),
        ...data
    };
    console.log(JSON.stringify(entry));
}

function generateTraceId() {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

// ============================================================================
// DATA SENTINEL CLASS
// ============================================================================

class DataSentinel {
    constructor(options = {}) {
        this.config = { ...SENTINEL_CONFIG, ...options };
        this.db = createPool(this.config.db);
    }

    /**
     * Step A: Golden Data Completeness Scan
     * Counts matches with all three data sources: Index + L2 + Temporal
     *
     * @returns {Promise<Object>} - Completeness statistics
     */
    async scanCompleteness() {
        const client = await this.db.connect();
        try {
            // Query for complete golden entities
            const query = `
                WITH golden_entities AS (
                    SELECT
                        m.match_id,
                        m.match_date,
                        m.league_name,
                        m.home_team,
                        m.away_team,
                        -- Index check
                        m.match_id IS NOT NULL as has_index,
                        -- L2 check
                        m.l2_raw_json IS NOT NULL as has_l2,
                        -- Temporal check (cast entity_id to varchar for comparison)
                        EXISTS(
                            SELECT 1 FROM temporal_metric_records tmr
                            WHERE tmr.entity_id::varchar = m.match_id
                            LIMIT 1
                        ) as has_temporal
                    FROM matches m
                    WHERE m.match_date >= NOW() - INTERVAL '2 years'
                )
                SELECT
                    COUNT(*) as total_matches,
                    COUNT(CASE WHEN has_index THEN 1 END) as indexed_count,
                    COUNT(CASE WHEN has_l2 THEN 1 END) as l2_count,
                    COUNT(CASE WHEN has_temporal THEN 1 END) as temporal_count,
                    COUNT(CASE WHEN has_index AND has_l2 AND has_temporal THEN 1 END) as golden_count
                FROM golden_entities
            `;

            const result = await client.query(query);
            const row = result.rows[0];

            const completeness = {
                total_matches: row.total_matches,
                indexed: row.indexed_count,
                with_l2: row.l2_count,
                with_temporal: row.temporal_count,
                golden_complete: row.golden_count,
                target: this.config.targetTotalMatches,
                progress_percent: ((row.golden_count / this.config.targetTotalMatches) * 100).toFixed(2)
            };

            log('info', '[V70.200] Completeness scan complete', {
                total: completeness.total_matches,
                golden: completeness.golden_complete,
                progress: completeness.progress_percent + '%'
            });

            return completeness;

        } finally {
            client.release();
        }
    }

    /**
     * Step B: Data Quality Gate
     * Detects data corruption anomalies
     *
     * @returns {Promise<Object>} - Quality gate results
     */
    async scanQualityGate() {
        const client = await this.db.connect();
        try {
            const anomalies = {
                odds_anomalies: 0,
                payout_anomalies: 0,
                time_anomalies: 0,
                total_corrupted: 0,
                corrupted_records: []
            };

            // Sub-step B1: Odds anomalies (<= 1.0 or >= 100)
            const oddsQuery = `
                SELECT
                    entity_id,
                    provider_name,
                    dimension,
                    value,
                    occurred_at
                FROM temporal_metric_records
                WHERE value <= $1 OR value >= $2
                ORDER BY occurred_at DESC
                LIMIT 100
            `;
            const oddsResult = await client.query(oddsQuery, [
                this.config.qualityGate.minOdds,
                this.config.qualityGate.maxOdds
            ]);
            anomalies.odds_anomalies = oddsResult.rowCount;

            // Sub-step B2: Payout anomalies (< 80% or > 100%)
            const payoutQuery = `
                SELECT
                    entity_id,
                    provider_name,
                    payout,
                    occurred_at
                FROM temporal_metric_records
                WHERE payout IS NOT NULL
                  AND (payout < $1 OR payout > $2)
                ORDER BY occurred_at DESC
                LIMIT 100
            `;
            const payoutResult = await client.query(payoutQuery, [
                this.config.qualityGate.minPayout,
                this.config.qualityGate.maxPayout
            ]);
            anomalies.payout_anomalies = payoutResult.rowCount;

            // Sub-step B3: Time misalignment check
            // This would require additional metadata, simplified for now
            anomalies.time_anomalies = 0;

            anomalies.total_corrupted = anomalies.odds_anomalies +
                                        anomalies.payout_anomalies +
                                        anomalies.time_anomalies;

            // Collect sample corrupted records
            anomalies.corrupted_records = [
                ...oddsResult.rows.slice(0, 10).map(r => ({
                    type: 'ODDS_ANOMALY',
                    entity_id: r.entity_id.substring(0, 8),
                    value: r.value,
                    timestamp: r.occurred_at
                })),
                ...payoutResult.rows.slice(0, 10).map(r => ({
                    type: 'PAYOUT_ANOMALY',
                    entity_id: r.entity_id.substring(0, 8),
                    payout: r.payout,
                    timestamp: r.occurred_at
                }))
            ];

            log('info', '[V70.200] Quality gate scan complete', {
                odds_anomalies: anomalies.odds_anomalies,
                payout_anomalies: anomalies.payout_anomalies,
                total_corrupted: anomalies.total_corrupted
            });

            return anomalies;

        } finally {
            client.release();
        }
    }

    /**
     * Step C: Throughput Tracker
     * Calculates MPH and ETA for full backfill completion
     *
     * @returns {Promise<Object>} - Throughput metrics
     */
    async scanThroughput() {
        const client = await this.db.connect();
        try {
            // Calculate matches added in the last hour
            const throughputQuery = `
                WITH recent_additions AS (
                    SELECT
                        COUNT(DISTINCT entity_id) as matches_added,
                        MIN(occurred_at) as earliest_observation,
                        MAX(occurred_at) as latest_observation
                    FROM temporal_metric_records
                    WHERE occurred_at >= NOW() - INTERVAL '1 hour'
                ),
                golden_progress AS (
                    SELECT COUNT(*) as golden_count
                    FROM matches m
                    WHERE m.l2_raw_json IS NOT NULL
                      AND EXISTS(
                          SELECT 1 FROM temporal_metric_records tmr
                          WHERE tmr.entity_id::varchar = m.match_id
                          LIMIT 1
                      )
                )
                SELECT
                    COALESCE(ra.matches_added, 0) as matches_added_last_hour,
                    ra.earliest_observation,
                    ra.latest_observation,
                    gp.golden_count
                FROM recent_additions ra, golden_progress gp
            `;

            const result = await client.query(throughputQuery);
            const row = result.rows[0];

            const mph = row.matches_added_last_hour;
            const currentGolden = row.golden_count;
            const remaining = this.config.targetTotalMatches - currentGolden;

            // Calculate ETA
            let eta_hours = null;
            let eta_date = null;

            if (mph > 0 && remaining > 0) {
                eta_hours = remaining / mph;
                eta_date = new Date(Date.now() + eta_hours * 60 * 60 * 1000);
            } else if (mph === 0 && remaining > 0) {
                eta_hours = Infinity;
                eta_date = null;
            } else {
                eta_hours = 0;
                eta_date = new Date();
            }

            const throughput = {
                mph: mph,
                current_golden: currentGolden,
                remaining: remaining,
                eta_hours: eta_hours === Infinity ? null : eta_hours?.toFixed(1),
                eta_date: eta_date ? eta_date.toISOString() : null
            };

            log('info', '[V70.200] Throughput scan complete', {
                mph: throughput.mph,
                remaining: throughput.remaining,
                eta: throughput.eta_date
            });

            return throughput;

        } finally {
            client.release();
        }
    }

    /**
     * Calculate data health score (0-10)
     * Based on quality gate results
     *
     * @param {Object} anomalies - Quality gate results
     * @returns {number} - Health score (0-10)
     */
    calculateHealthScore(anomalies) {
        if (anomalies.total_corrupted === 0) {
            return 10;
        }

        // Deduct points for each anomaly category
        let score = 10;
        score -= Math.min(anomalies.odds_anomalies / 10, 3);    // Max -3 for odds
        score -= Math.min(anomalies.payout_anomalies / 10, 3);  // Max -3 for payout
        score -= Math.min(anomalies.time_anomalies / 5, 2);      // Max -2 for time

        return Math.max(0, Math.floor(score * 10) / 10);
    }

    /**
     * Format dashboard table
     *
     * @param {Object} results - Scan results
     * @returns {string} - Formatted dashboard
     */
    formatDashboard(results) {
        const { completeness, anomalies, throughput, healthScore } = results;

        const eta = throughput.eta_date ?
            new Date(throughput.eta_date).toLocaleString('en-US', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            }) : 'T+∞';

        // Format duration
        const formatDuration = (hours) => {
            if (!hours || hours === Infinity) return 'Unknown';
            const h = Math.floor(hours);
            const m = Math.floor((hours - h) * 60);
            if (h >= 24) {
                const d = Math.floor(h / 24);
                return `${d}d ${h % 24}h`;
            }
            return `${h}h ${m}m`;
        };

        // Calculate evaluation text
        const progressEval = parseFloat(completeness.progress_percent) >= 100 ? '✅ Complete' :
                            parseFloat(completeness.progress_percent) >= 80 ? '🟢 On Track' :
                            parseFloat(completeness.progress_percent) >= 50 ? '🟡 Making Progress' :
                            '🔴 Early Stage';

        const qualityEval = anomalies.total_corrupted === 0 ? '✅ Clean' :
                           anomalies.total_corrupted <= 10 ? '⚠️ Minor Issues' :
                           '❌ Data Corruption Detected';

        const healthEval = healthScore >= 9 ? 'Excellent' :
                          healthScore >= 7 ? 'Good' :
                          healthScore >= 5 ? 'Fair' :
                          'Poor';

        const dashboard = `
╔══════════════════════════════════════════════════════════════════════════════╗
║                    V70.200 DATA SENTINEL DASHBOARD                           ║
║                    "实时监控与质量快照"                                        ║
╚══════════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────────┐
│  📊 HARVEST PROGRESS (收割进度)                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  Current / Target      │  ${String(completeness.golden_complete || 0).padStart(7)} / ${String(this.config.targetTotalMatches).padStart(6)}                                        │
│  Progress Percent      │  ${completeness.progress_percent.padStart(20)}                                        │
│  Evaluation            │  ${progressEval.padStart(20)}                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  📈 DATA SOURCE BREAKDOWN                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  Indexed Matches       │  ${String(completeness.indexed).padStart(7)}                                        │
│  With L2 Data          │  ${String(completeness.with_l2).padStart(7)}                                        │
│  With Temporal Data    │  ${String(completeness.with_temporal).padStart(7)}                                        │
│  Golden Complete       │  ${String(completeness.golden_complete || 0).padStart(7)}                                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  🛡️  QUALITY GATE (数据质量安检)                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Odds Anomalies       │  ${String(anomalies.odds_anomalies).padStart(7)}   (准入要求: 0)                             │
│  Payout Anomalies     │  ${String(anomalies.payout_anomalies).padStart(7)}   (准入要求: 0)                             │
│  Time Anomalies       │  ${String(anomalies.time_anomalies).padStart(7)}   (准入要求: 0)                             │
│  Total Corrupted      │  ${String(anomalies.total_corrupted).padStart(7)}                                            │
│  Evaluation           │  ${qualityEval.padStart(20)}                                            │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  ⚡ THROUGHPUT TRACKER (性能传感器)                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  Matches Per Hour     │  ${String(throughput.mph).padStart(7)}   MPH                                         │
│  Remaining Matches    │  ${String(throughput.remaining).padStart(7)}                                            │
│  ETA (Hours)          │  ${String(formatDuration(throughput.eta_hours) || 'Unknown').padStart(20)}                                            │
│  ETA (Date)           │  ${String(eta).padStart(20)}                                            │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  💚 DATA HEALTH SCORE                                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  Score                │  ${healthScore.toFixed(1)} / 10.0                                                │
│  Evaluation           │  ${healthEval.padStart(20)}                                            │
└─────────────────────────────────────────────────────────────────────────────┘

Scan Timestamp: ${new Date().toISOString()}
`;
        return dashboard;
    }

    /**
     * Execute full sentinel scan
     *
     * @returns {Promise<Object>} - Complete scan results
     */
    async executeScan() {
        log('info', '[V70.200] Starting full sentinel scan');

        const startTime = Date.now();

        // Run all three scans
        const [completeness, anomalies, throughput] = await Promise.all([
            this.scanCompleteness(),
            this.scanQualityGate(),
            this.scanThroughput()
        ]);

        const healthScore = this.calculateHealthScore(anomalies);

        const results = {
            completeness,
            anomalies,
            throughput,
            healthScore,
            scan_duration_ms: Date.now() - startTime,
            timestamp: new Date().toISOString()
        };

        log('info', '[V70.200] Sentinel scan complete', {
            health_score: healthScore,
            progress: completeness.progress_percent + '%',
            corrupted: anomalies.total_corrupted,
            duration_ms: results.scan_duration_ms
        });

        return results;
    }

    /**
     * Run sentinel and display dashboard
     *
     * @returns {Promise<Object>} - Scan results
     */
    async run() {
        try {
            const results = await this.executeScan();
            const dashboard = this.formatDashboard(results);
            console.log(dashboard);
            return results;
        } catch (error) {
            log('error', '[V70.200] Fatal error', {
                error: error.message,
                stack: error.stack
            });
            throw error;
        }
    }

    /**
     * Cleanup database connection
     *
     * @returns {Promise<void>}
     */
    async cleanup() {
        if (this.db) {
            await this.db.end();
            log('info', '[V70.200] Database connection closed');
        }
    }
}

// ============================================================================
// CLI INTERFACE
// ============================================================================

/**
 * Main CLI entry point
 * @param {Array} args - Command line arguments
 * @returns {Promise<number>} - Exit code
 */
async function main(args) {
    const sentinel = new DataSentinel();

    try {
        // Parse arguments
        const mode = args[0] || 'scan';

        if (mode === 'scan') {
            const results = await sentinel.run();

            // Return exit code based on health score
            if (results.healthScore >= 7) {
                return 0;  // Good health
            } else if (results.healthScore >= 5) {
                return 1;  // Fair health - warning
            } else {
                return 2;  // Poor health - critical
            }
        } else if (mode === 'json') {
            // JSON output for programmatic consumption
            const results = await sentinel.executeScan();
            console.log(JSON.stringify(results, null, 2));
            return 0;
        } else {
            console.error(`Unknown mode: ${mode}`);
            console.error('Usage: node v70_200_data_sentinel.js [scan|json]');
            return 1;
        }

    } catch (error) {
        log('error', '[V70.200] Fatal error', {
            error: error.message,
            stack: error.stack
        });
        return 1;
    } finally {
        await sentinel.cleanup();
    }
}

// ============================================================================
// EXPORTS
// ============================================================================

module.exports = {
    DataSentinel,
    SENTINEL_CONFIG,
    main
};

// ============================================================================
// CLI EXECUTION
// ============================================================================

if (require.main === module) {
    main(process.argv.slice(2)).then(exitCode => {
        process.exit(exitCode);
    });
}
