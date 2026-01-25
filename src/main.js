/**
 * V66.000 - Main Entry Point
 * ==============================
 *
 * Unified entry point for the refactored data collection system.
 * Implements defensive programming, resource cleanup, and structured logging.
 *
 * @file main.js
 * @author Principal Software Architect
 * @version V66.000
 * @since 2026-01-25
 */

'use strict';

// ============================================================================
// IMPORTS
// ============================================================================

const fs = require('fs');
const path = require('path');

// Core modules
const { getGlobalPool, cleanupGlobalPool, generateTraceId } = require('./core/browser');
const { createRetryPolicy } = require('./core/retry');

// Business modules
const { createCollector } = require('./modules/collector');
const { upsertFullTemporalRecords } = require('./modules/sink');
const { parseJsonResponse } = require('./modules/parser');

// Configuration
const providersConfig = require('./config/providers.json');

// ============================================================================
// CONFIGURATION
// ============================================================================

const APP_CONFIG = {
    version: 'V66.000',
    name: 'FootballPrediction Data Collector',
    providersPath: path.join(__dirname, 'config', 'providers.json'),
    logLevel: process.env.LOG_LEVEL || 'info'
};

// ============================================================================
// STRUCTURED LOGGER
// ============================================================================

/**
 * Create structured logger entry
 * @param {string} level - Log level
 * @param {string} message - Log message
 * @param {Object} [data] - Additional data
 * @returns {Object} - Structured log entry
 */
function createLogEntry(level, message, data = {}) {
    return {
        level,
        trace_id: generateTraceId(),
        module: 'main',
        version: APP_CONFIG.version,
        message,
        ...data,
        timestamp: new Date().toISOString()
    };
}

/**
 * Log structured message
 * @param {string} level - Log level
 * @param {string} message - Log message
 * @param {Object} [data] - Additional data
 */
function log(level, message, data = {}) {
    const entry = createLogEntry(level, message, data);
    console.log(JSON.stringify(entry));
}

// ============================================================================
// APPLICATION CLASS
// ============================================================================>

/**
 * V66.000: Main Application Class
 *
 * Orchestrates the entire data collection pipeline with proper resource management.
 */
class Application {
    /**
     * @param {Object} [options={}] - Application options
     */
    constructor(options = {}) {
        this.options = options;
        this.traceId = generateTraceId();
        this.browserPool = null;
        this.dbPool = null;
        this.isRunning = false;
        this.shutdownHandlers = [];

        // Register signal handlers
        this._registerSignalHandlers();
    }

    /**
     * Initialize the application
     * @returns {Promise<void>}
     */
    async initialize() {
        try {
            log('info', 'Initializing application', {
                version: APP_CONFIG.version,
                node_version: process.version
            });

            // Initialize browser pool
            this.browserPool = getGlobalPool();
            await this.browserPool.initialize();

            log('info', 'Browser pool initialized', {
                stats: this.browserPool.getStats()
            });

            // Initialize database pool
            const { createPool } = require('./modules/sink');
            this.dbPool = createPool();

            log('info', 'Database pool initialized');

            // Load provider configuration
            this._loadProviderConfig();

            log('info', 'Application initialized');

        } catch (error) {
            log('error', 'Initialization failed', {
                error: error.message,
                stack: error.stack
            });
            throw error;
        }
    }

    /**
     * Run data collection
     * @param {string} url - Target URL
     * @param {string} sourceId - Source identifier
     * @returns {Promise<Object>} - Collection result
     */
    async run(url, sourceId) {
        if (this.isRunning) {
            throw new Error('Application is already running');
        }

        this.isRunning = true;
        const collector = null;
        let result = { success: false, recordsCollected: 0 };

        try {
            log('info', 'Starting data collection', {
                url,
                sourceId
            });

            // Create collector
            const collector = createCollector();
            await collector.initialize();

            // Navigate to URL
            await collector.navigate(url);

            // Collect from all providers
            const providerConfigs = this._getEnabledProviders();
            const records = await collector.collectFromAllProviders(providerConfigs);

            result.recordsCollected = records.length;

            log('info', 'Data collection complete', {
                recordCount: records.length,
                providerCount: providerConfigs.length
            });

            // Get or create entity
            const client = await this.dbPool.connect();
            try {
                const { getOrCreateEntity } = require('./modules/sink');
                const entityId = await getOrCreateEntity(
                    client,
                    sourceId,
                    url,
                    'match'
                );

                log('info', 'Entity resolved', { entityId });

                // Store records
                const storeResult = await upsertFullTemporalRecords(
                    client,
                    entityId,
                    records
                );

                result = {
                    success: true,
                    recordsCollected: records.length,
                    recordsStored: storeResult.total_records,
                    entityId: entityId,
                    inserted: storeResult.inserted,
                    updated: storeResult.updated,
                    skipped: storeResult.skipped
                };

                log('info', 'Data storage complete', result);

            } finally {
                client.release();
            }

            // Cleanup collector
            await collector.cleanup();

            return result;

        } catch (error) {
            log('error', 'Collection failed', {
                error: error.message,
                stack: error.stack
            });
            result.error = error.message;
            return result;

        } finally {
            this.isRunning = false;
        }
    }

    /**
     * Graceful shutdown
     * @returns {Promise<void>}
     */
    async shutdown() {
        if (this.isRunning) {
            log('warn', 'Shutdown requested while running');
        }

        log('info', 'Starting graceful shutdown');

        try {
            // Close database pool
            if (this.dbPool) {
                const { closePool } = require('./modules/sink');
                await closePool(this.dbPool);
                this.dbPool = null;
            }

            // Close browser pool
            if (this.browserPool) {
                await this.browserPool.shutdown();
                this.browserPool = null;
            }

            log('info', 'Shutdown complete');

        } catch (error) {
            log('error', 'Shutdown error', {
                error: error.message
            });
        }
    }

    /**
     * Load provider configuration
     * @private
     */
    _loadProviderConfig() {
        try {
            const configPath = APP_CONFIG.providersPath;
            const configData = fs.readFileSync(configPath, 'utf-8');
            this.providerConfig = JSON.parse(configData);

            log('info', 'Provider config loaded', {
                providerCount: this.providerConfig.providers.length,
                enabledCount: this.providerConfig.providers.filter(p => p.enabled).length
            });

        } catch (error) {
            throw new Error(`Failed to load provider config: ${error.message}`);
        }
    }

    /**
     * Get enabled providers
     * @private
     * @returns {Array} - Array of enabled provider configurations
     */
    _getEnabledProviders() {
        return this.providerConfig.providers
            .filter(p => p.enabled)
            .sort((a, b) => a.priority - b.priority);
    }

    /**
     * Register signal handlers for graceful shutdown
     * @private
     */
    _registerSignalHandlers() {
        const shutdownHandler = async () => {
            log('info', 'Signal received, initiating shutdown');
            await this.shutdown();
            process.exit(0);
        };

        process.on('SIGINT', shutdownHandler);
        process.on('SIGTERM', shutdownHandler);
    }
}

// ============================================================================
// CLI INTERFACE
// ============================================================================

/**
 * Main CLI entry point
 * @param {Array} args - Command line arguments
 */
async function main(args) {
    const app = new Application();

    try {
        // Parse arguments
        const url = args[0] || process.env.TARGET_URL;
        const sourceId = args[1] || process.env.SOURCE_ID || 'manual_run';

        if (!url) {
            log('error', 'Missing required argument: url');
            console.error('Usage: node src/main.js <url> [sourceId]');
            process.exit(1);
        }

        // Initialize application
        await app.initialize();

        // Run collection
        const result = await app.run(url, sourceId);

        // Shutdown
        await app.shutdown();

        // Exit with appropriate code
        if (result.success) {
            log('info', 'Collection successful', result);
            process.exit(0);
        } else {
            log('error', 'Collection failed', result);
            process.exit(1);
        }

    } catch (error) {
        log('error', 'Application error', {
            error: error.message,
            stack: error.stack
        });

        // Ensure cleanup
        await app.shutdown();

        process.exit(1);
    }
}

// ============================================================================
// EXPORTS
// ============================================================================

module.exports = {
    Application,
    main,
    APP_CONFIG
};

// ============================================================================
// CLI EXECUTION
// ============================================================================

if (require.main === module) {
    main(process.argv.slice(2));
}
