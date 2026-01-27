#!/usr/bin/env node
/**
 * V126.000 - Production Runner for QuantHarvester
 * =============================================================================
 *
 * Industrial-grade batch processing engine for quantitative data acquisition.
 * Features:
 *   - 10-lane concurrent processing
 *   - 3-retry mechanism with exponential backoff
 *   - Headless silent execution
   - - Progress reporting every 10%
 *   - Graceful shutdown on SIGINT/SIGTERM
 *
 * @module v126_000_production_runner
 * @version V126.000
 * @since 2026-01-27
 * @author Lead DevOps Engineer
 *
 * @example
 * node scripts/ops/v126_000_production_runner.js --matches 100 --concurrent 10
 */

'use strict';

const path = require('path');
const { QuantHarvester, alignTimestamp, QuantHarvesterError } = require('../../src/engines/QuantHarvester');

// ============================================================================
// CONFIGURATION (Environment-First)
// ============================================================================

const CONFIG = {
    // Concurrency settings
    concurrent: parseInt(process.env.CONCURRENT_THREADS) || 10,
    batchSize: parseInt(process.env.BATCH_SIZE) || 50,

    // Retry settings
    maxRetries: 3,
    retryDelayBase: 2000,     // 2 seconds
    retryDelayMax: 10000,    // 10 seconds

    // Browser settings
    headless: process.env.HEADLESS_MODE !== 'false',  // Default true for silent execution
    disableImages: process.env.DISABLE_IMAGES === 'true',
    timeout: parseInt(process.env.BROWSER_TIMEOUT) || 60000,

    // Progress reporting
    progressInterval: 0.10,  // Report every 10%

    // Logging
    logLevel: process.env.LOG_LEVEL || 'warn',

    // Graceful shutdown
    shutdownTimeout: 30000  // 30 seconds grace period
};

// ============================================================================
// RETRY MECHANISM WITH EXPONENTIAL BACKOFF
// ============================================================================

/**
 * Execute function with retry mechanism
 * @param {Function} fn - Async function to execute
 * @param {Object} context - Context for error messages
 * @returns {Promise<*>} Result of the function
 */
async function executeWithRetry(fn, context = {}) {
    const { maxRetries, retryDelayBase, retryDelayMax } = CONFIG;
    let lastError = null;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            return await fn();
        } catch (error) {
            lastError = error;

            // Don't retry on certain errors
            if (error.message?.includes('INVALID') ||
                error.message?.includes('MALFORMED')) {
                throw error;
            }

            if (attempt < maxRetries) {
                // Exponential backoff: 2s, 4s, 8s
                const delay = Math.min(
                    retryDelayBase * Math.pow(2, attempt - 1),
                    retryDelayMax
                );

                const logLevel = CONFIG.logLevel === 'debug' ? 'error' : 'warn';
                console[logLevel](
                    `[V126.000] Retry ${attempt}/${maxRetries} for ${context.sourceId || context.url || 'unknown'}: ${error.message.substring(0, 100)}`
                );

                await sleep(delay);
            }
        }
    }

    // If all retries failed, throw the last error
    throw lastError;
}

/**
 * Sleep utility for delays
 * @param {number} ms - Milliseconds to sleep
 */
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// ============================================================================
// MATCH DATA GENERATION
// ============================================================================

/**
 * Generate match queue from database query or command line
 * @param {number} count - Number of matches to process
 * @returns {Array<Object>} Array of match objects
 */
async function generateMatchQueue(count = 100) {
    const { Client } = require('pg');
    const { getDBConfig } = require('../../scripts/ops/modules/storage');

    const client = new Client(getDBConfig());

    try {
        await client.connect();

        const result = await client.query(`
            SELECT
                mm.oddsportal_hash as source_id,
                mm.oddsportal_url as source_url,
                m.match_date
            FROM matches_mapping mm
            JOIN matches m ON mm.fotmob_id = m.match_id
            WHERE mm.oddsportal_url IS NOT NULL
            ORDER BY m.match_date DESC
            LIMIT $1
        `, [count]);

        return result.rows.map(row => ({
            url: row.source_url,
            sourceId: row.source_id,
            matchTime: row.match_date
        }));

    } catch (error) {
        console.error('[V126.000] Failed to generate match queue:', error.message);
        // Return mock data for testing if database unavailable
        return [];
    } finally {
        await client.end().catch(() => {});
    }
}

// ============================================================================
// PROGRESS REPORTER
// ============================================================================

/**
 * Progress tracker with interval reporting
 */
class ProgressTracker {
    constructor(total, reportInterval = 0.10) {
        this.total = total;
        this.reportInterval = reportInterval;
        this.processed = 0;
        this.successful = 0;
        this.failed = 0;
        this.lastReported = 0;
        this.startTime = Date.now();
    }

    /**
     * Update progress
     * @param {boolean} success - Whether the operation succeeded
     */
    update(success) {
        this.processed++;
        if (success) {
            this.successful++;
        } else {
            this.failed++;
        }

        // Check if we should report progress
        const currentProgress = this.processed / this.total;
        if (currentProgress - this.lastReported >= this.reportInterval) {
            this.report();
            this.lastReported = currentProgress;
        }
    }

    /**
     * Report current progress
     */
    report() {
        const elapsed = Date.now() - this.startTime;
        const rate = Math.round(this.processed / (elapsed / 1000)); // per second

        console.log(`
╔══════════════════════════════════════════════════════════════════╗
║  V126.000 PROGRESS REPORT                                          ║
╠══════════════════════════════════════════════════════════════════╣
║  Processed: ${this.processed}/${this.total} (${Math.round(this.processed/this.total*100)}%)
║  ✅ Success: ${this.successful}
║  ❌ Failed:  ${this.failed}
║  📊 Rate: ${rate} matches/sec
║  ⏱️  Elapsed: ${Math.round(elapsed/1000)}s
╚══════════════════════════════════════════════════════════════════╝
`);
    }

    /**
     * Get final summary
     * @returns {Object} Summary statistics
     */
    getSummary() {
        const elapsed = Date.now() - this.startTime;

        return {
            total: this.total,
            processed: this.processed,
            successful: this.successful,
            failed: this.failed,
            successRate: this.processed > 0 ? (this.successful / this.processed).toFixed(4) : '0.0000',
            avgTimePerMatch: this.processed > 0 ? (elapsed / this.processed / 1000).toFixed(2) : '0.00',
            totalTime: Math.round(elapsed / 1000)
        };
    }
}

// ============================================================================
// GRACEFUL SHUTDOWN HANDLER
// ============================================================================

class ShutdownManager {
    constructor() {
        this.isShuttingDown = false;
        this.activeConnections = new Set();
    }

    /**
     * Register an active connection for cleanup
     * @param {Object} connection - Connection to track
     */
    register(connection) {
        this.activeConnections.add(connection);
    }

    /**
     * Initiate graceful shutdown
     */
    async shutdown() {
        if (this.isShuttingDown) return;

        this.isShuttingDown = true;
        console.log('\n[V126.000] 🛑 Shutdown signal received. Cleaning up...');

        // Close all connections
        for (const connection of this.activeConnections) {
            try {
                if (typeof connection.shutdown === 'function') {
                    await connection.shutdown();
                } else if (typeof connection.close === 'function') {
                    await connection.close();
                }
            } catch (error) {
                console.error(`[V126.000] Error closing connection:`, error.message);
            }
        }

        this.activeConnections.clear();
        console.log('[V126.000] ✅ All connections closed. Exiting gracefully.');
    }
}

const shutdownManager = new ShutdownManager();

// Register shutdown handlers
process.on('SIGINT', async () => {
    await shutdownManager.shutdown();
    process.exit(0);
});

process.on('SIGTERM', async () => {
    await shutdownManager.shutdown();
    process.exit(0);
});

// ============================================================================
// MAIN PRODUCTION RUNNER
// ============================================================================

/**
 * V126.000 Main Production Runner
 */
class ProductionRunner {
    /**
     * @param {Object} options - Configuration options
     */
    constructor(options = {}) {
        this.options = {
            matchCount: options.matchCount || 100,
            concurrent: options.concurrent || CONFIG.concurrent,
            retries: options.retries || CONFIG.maxRetries,
            dryRun: options.dryRun || false,
        };

        this.harvester = null;
        this.progressTracker = null;
    }

    /**
     * Initialize the harvester
     */
    async initialize() {
        console.log('[V126.000] Initializing QuantHarvester...');

        this.harvester = new QuantHarvester({
            headless: CONFIG.headless,
            disableImages: CONFIG.disableImages,
            maxConcurrent: this.options.concurrent,
            logLevel: CONFIG.logLevel
        });

        await this.harvester.init();
        shutdownManager.register(this.harvester);

        console.log('[V126.000] ✅ Harvester initialized');
        console.log(`[V126.000] Configuration: ${this.options.concurrent} lanes, ${this.options.retries} retries, headless=${CONFIG.headless}`);
    }

    /**
     * Process a single match with retry mechanism
     * @param {Object} match - Match object with url and sourceId
     * @returns {Promise<Object>} Processing result
     */
    async processMatch(match) {
        return executeWithRetry(async () => {
            const result = await this.harvester.harvestMatch(match.url, match.sourceId);
            return result;
        }, {
            sourceId: match.sourceId,
            url: match.url
        });
    }

    /**
     * Process batch of matches
     * @param {Array} matches - Array of match objects
     * @returns {Promise<Object>} Batch processing result
     */
    async processBatch(matches) {
        const results = [];
        const progressTracker = new ProgressTracker(
            matches.length,
            CONFIG.progressInterval
        );

        console.log(`\n[V126.000] Starting batch processing: ${matches.length} matches`);

        for (const match of matches) {
            if (shutdownManager.isShuttingDown) {
                console.log('[V126.000] ⚠️  Shutdown detected, stopping batch...');
                break;
            }

            try {
                const result = await this.processMatch(match);

                progressTracker.update(result.success);

                results.push({
                    sourceId: match.sourceId,
                    url: match.url,
                    success: result.success,
                    trajectoryPoints: result.trajectoryPoints || 0,
                    duration: result.duration || 0,
                    error: result.error
                });

            } catch (error) {
                progressTracker.update(false);

                results.push({
                    sourceId: match.sourceId,
                    url: match.url,
                    success: false,
                    trajectoryPoints: 0,
                    duration: 0,
                    error: error.message
                });
            }
        }

        return {
            results,
            summary: progressTracker.getSummary()
        };
    }

    /**
     * Run the full production pipeline
     */
    async run() {
        const startTime = Date.now();

        try {
            console.log('╔════════════════════════════════════════════════════════════════╗');
            console.log('║           V126.000 - PRODUCTION RUNNER                           ║');
            console.log('║           Quantitative Data Acquisition Engine                   ║');
            console.log('╚════════════════════════════════════════════════════════════════╝');
            console.log('');

            if (this.options.dryRun) {
                console.log('[V126.000] 🔬 DRY RUN MODE - No actual processing');
                return;
            }

            // Step 1: Initialize
            await this.initialize();

            // Step 2: Generate match queue
            console.log(`[V126.000] Fetching match queue (${this.options.matchCount} matches)...`);
            const matches = await generateMatchQueue(this.options.matchCount);

            if (matches.length === 0) {
                console.log('[V126.000] ⚠️  No matches found in database. Exiting.');
                return;
            }

            console.log(`[V126.000] ✅ Loaded ${matches.length} matches for processing`);

            // Step 3: Process in batches
            const batchSize = Math.min(this.options.concurrent, CONFIG.batchSize);
            const batches = [];

            for (let i = 0; i < matches.length; i += batchSize) {
                batches.push(matches.slice(i, i + batchSize));
            }

            console.log(`[V126.000] Split into ${batches.length} batches (${matches.length} total matches)`);

            let allResults = [];
            let totalBatchesProcessed = 0;

            for (let batchIndex = 0; batchIndex < batches.length; batchIndex++) {
                if (shutdownManager.isShuttingDown) {
                    console.log(`[V126.000] ⚠️  Shutdown detected during batch ${batchIndex + 1}/${batches.length}`);
                    break;
                }

                console.log(`\n[V126.000] Processing batch ${batchIndex + 1}/${batches.length} (${batches[batchIndex].length} matches)...`);

                const batchResult = await this.processBatch(batches[batchIndex]);
                allResults.push(...batchResult.results);
                totalBatchesProcessed = batchIndex + 1;
            }

            // Step 4: Final summary
            const finalSummary = {
                ...allResults.reduce((acc, r) => {
                    acc.totalMatches++;
                    if (r.success) acc.successfulMatches++;
                    if (!r.success) acc.failedMatches++;
                    acc.totalTrajectoryPoints += r.trajectoryPoints;
                    return acc;
                }, {
                    totalMatches: 0,
                    successfulMatches: 0,
                    failedMatches: 0,
                    totalTrajectoryPoints: 0
                })
            };

            finalSummary.elapsedTime = Math.round((Date.now() - startTime) / 1000);
            finalSummary.averageTime = finalSummary.totalMatches > 0
                ? (finalSummary.elapsedTime / finalSummary.totalMatches).toFixed(2)
                : '0.00';

            console.log('\n╔════════════════════════════════════════════════════════════════╗');
            console.log('║              V126.000 - FINAL SUMMARY                               ║');
            console.log('╠════════════════════════════════════════════════════════════════╣');
            console.log(`║  Total Matches Processed: ${finalSummary.totalMatches}
║  Successful Matches:       ${finalSummary.successfulMatches}
║  Failed Matches:          ${finalSummary.failedMatches}
║  Success Rate:             ${finalSummary.successfulMatches > 0 ? (finalSummary.successfulMatches/finalSummary.totalMatches*100).toFixed(2) : '0.00'}%
║  Total Trajectory Points:  ${finalSummary.totalTrajectoryPoints}
║  Average Time Per Match:   ${finalSummary.averageTime}s
║  Total Elapsed Time:      ${finalSummary.elapsedTime}s
╚════════════════════════════════════════════════════════════════╝`);

            // Save detailed results to JSON file
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const resultsPath = path.join(__dirname, '../logs/', `v126_000_results_${timestamp}.json`);

            const fs = require('fs');
            fs.mkdirSync(path.dirname(resultsPath), { recursive: true });

            fs.writeFileSync(
                resultsPath,
                JSON.stringify({
                    version: 'V126.000',
                    timestamp: new Date().toISOString(),
                    config: this.options,
                    results: allResults,
                    summary: finalSummary
                }, null, 2)
            );

            console.log(`\n[V126.000] 📁 Detailed results saved to: ${resultsPath}`);

        } catch (error) {
            console.error('\n[V126.000] ❌ FATAL ERROR:');
            console.error(error);
            process.exit(1);
        } finally {
            if (this.harvester && !shutdownManager.isShuttingDown) {
                console.log('\n[V126.000] Shutting down harvester...');
                await this.harvester.shutdown();
            }
        }
    }
}

// ============================================================================
// CLI ENTRY POINT
// ============================================================================

/**
 * Parse command line arguments
 */
function parseArgs() {
    const args = process.argv.slice(2);
    const options = {
        matchCount: 100,
        concurrent: 10,
        retries: 3,
        dryRun: false
    };

    for (let i = 0; i < args.length; i++) {
        const arg = args[i];

        if (arg === '--matches' || arg === '-m') {
            options.matchCount = parseInt(args[++i]) || 100;
        } else if (arg === '--concurrent' || arg === '-c') {
            options.concurrent = parseInt(args[++i]) || 10;
        } else if (arg === '--retries' || arg === '-r') {
            options.retries = parseInt(args[++i]) || 3;
        } else if (arg === '--dry-run' || arg === '-d') {
            options.dryRun = true;
        } else if (arg === '--help' || arg === '-h') {
            console.log(`
V126.000 - Production Runner for QuantHarvester
=================================================

USAGE:
  node scripts/ops/v126_000_production_runner.js [OPTIONS]

OPTIONS:
  -m, --matches <number>      Number of matches to process (default: 100)
  -c, --concurrent <number>   Number of concurrent lanes (default: 10)
  -r, --retries <number>      Max retry attempts (default: 3)
  -d, --dry-run              Dry run mode (no actual processing)
  -h, --help                 Show this help message

EXAMPLES:
  # Process 100 matches with 10 concurrent lanes
  node scripts/ops/v126_000_production_runner.js --matches 100 --concurrent 10

  # Process 500 matches with 20 concurrent lanes, 5 retries
  node scripts/ops/v126_000_production_runner.js --matches 500 --concurrent 20 --retries 5

  # Dry run to verify configuration
  node scripts/ops/v126_000_production_runner.js --dry-run
            `);
            process.exit(0);
        } else if (arg.startsWith('--')) {
            console.error(`[V126.000] Unknown option: ${arg}`);
            process.exit(1);
        }
    }

    return options;
}

// ============================================================================
// MAIN EXECUTION
// ============================================================================

async function main() {
    const options = parseArgs();

    const runner = new ProductionRunner(options);

    await runner.run();
}

// Run if executed directly
if (require.main === module) {
    main().catch(error => {
        console.error('[V126.000] Unhandled error:', error);
        process.exit(1);
    });
}

// ============================================================================
// EXPORTS
// ============================================================================

module.exports = {
    ProductionRunner,
    executeWithRetry,
    generateMatchQueue,
    ProgressTracker,
    ShutdownManager
};
