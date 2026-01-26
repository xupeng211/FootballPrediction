/**
 * QuantHarvester - V122.000 Industrial Grade Quant Price Trajectory Harvester
 * =============================================================================
 *
 * Standard production engine for extracting multi-dimensional quantitative data
 * trajectories from OddsPortal using Playwright automation.
 *
 * @module QuantHarvester
 * @version V122.000
 * @since 2026-01-27
 * @author Senior Staff Engineer (Tier-1 Standard)
 *
 * @example
 * const harvester = new QuantHarvester();
 * await harvester.init();
 * const result = await harvester.harvestMatch('https://www.oddsportal.com/.../hash/');
 * const results = await harvester.startQueue(100);
 * await harvester.shutdown();
 */

'use strict';

const { chromium } = require('playwright');
const { JSDOM } = require('jsdom');
const {
    createConnection,
    getOrCreateEntity,
    upsertTemporalRecords,
    StorageError
} = require('../../scripts/ops/modules/storage');

// ============================================================================
// CONFIGURATION (Environment-First, Zero Hardcoding)
// ============================================================================

/**
 * Default configuration loaded from environment variables
 * All sensitive data and deployment-specific settings are externalized
 */
const DEFAULT_CONFIG = {
    // Browser settings
    userAgent: process.env.BROWSER_USER_AGENT || 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    viewport: {
        width: parseInt(process.env.BROWSER_VIEWPORT_WIDTH) || 1920,
        height: parseInt(process.env.BROWSER_VIEWPORT_HEIGHT) || 1080
    },
    timeout: parseInt(process.env.BROWSER_TIMEOUT) || 60000,
    headless: process.env.HEADLESS_MODE !== 'false', // Default true
    disableImages: process.env.DISABLE_IMAGES === 'true',

    // Concurrency settings
    maxConcurrent: parseInt(process.env.CONCURRENT_THREADS) || 10,
    batchSize: parseInt(process.env.BATCH_SIZE) || 50,

    // Data processing
    axes: ['home', 'draw', 'away'],
    axisDimensions: { home: 'A', draw: 'B', away: 'C' },
    currentYear: new Date().getFullYear(),

    // Quality thresholds
    minTrajectoryPoints: parseInt(process.env.MIN_TRAJECTORY_POINTS) || 2,

    // Database settings (from environment - no hardcoding)
    dbHost: process.env.DB_HOST || 'localhost',
    dbPort: parseInt(process.env.DB_PORT) || 5432,
    dbName: process.env.DB_NAME || 'football_db',
    dbUser: process.env.DB_USER || 'football_user',
    dbPassword: process.env.DB_PASSWORD || '',

    // Logging
    logLevel: process.env.LOG_LEVEL || 'info'
};

// ============================================================================
// MARKET VENUE WHITELIST
// ============================================================================

/**
 * Market venue whitelist configuration
 * Standardizes venue names and filters approved data sources
 */
const MARKET_VENUE_WHITELIST = {
    venues: {
        'PIN-01': {
            standardId: 'PIN-01',
            names: ['pinnacle', 'pin', 'pinnacle sports', 'pinnacle.com'],
            priority: 1
        },
        'WIL-02': {
            standardId: 'WIL-02',
            names: ['william hill', 'williamhill', 'william hill sports', 'wh'],
            priority: 2
        },
        'B365-03': {
            standardId: 'B365-03',
            names: ['bet365', 'b365', 'bet365.com', 'bet 365'],
            priority: 3
        },
        'LAD-04': {
            standardId: 'LAD-04',
            names: ['ladbrokes', 'lad', 'ladbrokes.com', 'ladbrokes coral'],
            priority: 4
        },
        '188-05': {
            standardId: '188-05',
            names: ['188bet', '188', '188bet.com', '188 bet'],
            priority: 5
        },
        'SBO-06': {
            standardId: 'SBO-06',
            names: ['sbobet', 'sbo', 'sbobet.com', 'sbo bet'],
            priority: 6
        },
        'BWI-07': {
            standardId: 'BWI-07',
            names: ['betway', 'bwi', 'betway.com', 'bet way'],
            priority: 7
        }
    },

    /**
     * Normalize venue name to standard ID
     * @param {string} venueName - Raw venue name from page
     * @returns {string|null} Standard venue ID or null
     */
    normalizeVenueName(venueName) {
        if (!venueName || typeof venueName !== 'string') {
            return null;
        }
        const normalized = venueName.toLowerCase().trim();
        for (const [standardId, config] of Object.entries(this.venues)) {
            if (config.names.some(name => normalized.includes(name))) {
                return standardId;
            }
        }
        return null;
    },

    /**
     * Check if venue is whitelisted
     * @param {string} venueName - Raw venue name
     * @returns {boolean} True if allowed
     */
    isAllowed(venueName) {
        return this.normalizeVenueName(venueName) !== null;
    },

    /**
     * Get all allowed venue IDs
     * @returns {string[]} Array of standard venue IDs
     */
    getAllowedIds() {
        return Object.keys(this.venues);
    }
};

// ============================================================================
// SYNC TIMESTAMP MODULE (2026 Calibration)
// ============================================================================

/**
 * SyncTimestamp - Time alignment utilities
 * Handles parsing of various timestamp formats into ISO 8601
 */
class SyncTimestamp {
    /**
     * @param {number} currentYear - Current year for timestamp calibration
     */
    constructor(currentYear = new Date().getFullYear()) {
        this.currentYear = currentYear;
        this.monthMap = {
            'jan': 0, 'jan.': 0, 'january': 0,
            'feb': 1, 'feb.': 1, 'february': 1,
            'mar': 2, 'mar.': 2, 'march': 2,
            'apr': 3, 'apr.': 3, 'april': 3,
            'may': 4, 'may.': 4,
            'jun': 5, 'jun.': 5, 'june': 5,
            'jul': 6, 'jul.': 6, 'july': 6,
            'aug': 7, 'aug.': 7, 'august': 7,
            'sep': 8, 'sep.': 8, 'september': 8,
            'oct': 9, 'oct.': 9, 'october': 9,
            'nov': 10, 'nov.': 10, 'november': 10,
            'dec': 11, 'dec.': 11, 'december': 11
        };
    }

    /**
     * Parse date string to ISO 8601 format
     * @param {string} dateStr - Date string in various formats
     * @returns {string|null} ISO 8601 timestamp or null
     */
    parse(dateStr) {
        if (!dateStr || typeof dateStr !== 'string') {
            return null;
        }

        try {
            // Format: "24 Jan, 10:00" or "Jan 24, 10:00"
            const pattern1 = /^(\d{1,2})\s+(\w+\.?)\s*,?\s*(\d{1,2}):(\d{2})$/i;
            const match1 = dateStr.trim().match(pattern1);
            if (match1) {
                const day = parseInt(match1[1]);
                const monthStr = match1[2].toLowerCase();
                const hour = parseInt(match1[3]);
                const minute = parseInt(match1[4]);

                if (this.monthMap[monthStr] !== undefined) {
                    const date = new Date(Date.UTC(this.currentYear, this.monthMap[monthStr], day, hour, minute));
                    return date.toISOString();
                }
            }

            const pattern2 = /^(\w+\.?)\s+(\d{1,2})\s*,?\s*(\d{1,2}):(\d{2})$/i;
            const match2 = dateStr.trim().match(pattern2);
            if (match2) {
                const monthStr = match2[1].toLowerCase();
                const day = parseInt(match2[2]);
                const hour = parseInt(match2[3]);
                const minute = parseInt(match2[4]);

                if (this.monthMap[monthStr] !== undefined) {
                    const date = new Date(Date.UTC(this.currentYear, this.monthMap[monthStr], day, hour, minute));
                    return date.toISOString();
                }
            }

        } catch (error) {
            return null;
        }

        return null;
    }
}

/**
 * Standalone alignTimestamp function for test compatibility
 * @param {string} dateStr - Date string to align
 * @returns {string|null} ISO 8601 timestamp
 */
function alignTimestamp(dateStr) {
    const sync = new SyncTimestamp();
    return sync.parse(dateStr);
}

// ============================================================================
// DOM-FIRST TRAJECTORY PARSER
// ============================================================================

/**
 * TrajectoryParser - DOM-based trajectory extraction
 * Extracts quantitative data trajectories from modal HTML
 */
class TrajectoryParser {
    /**
     * Extract full trajectory from modal HTML using DOM traversal
     * V122.000: Memory leak fixed with explicit JSDOM cleanup
     *
     * @param {string} modalHtml - Modal HTML content
     * @returns {Array<{time: string, value: number, type: string}>}
     */
    extractFullTrajectoryDOM(modalHtml) {
        const trajectory = [];
        let dom = null;

        try {
            if (!modalHtml || typeof modalHtml !== 'string') {
                return trajectory;
            }

            dom = new JSDOM(modalHtml);
            const document = dom.window.document;

            // Step 1: Extract Opening odds
            const openingElements = document.querySelectorAll('*');
            for (const el of openingElements) {
                if (el.textContent && el.textContent.includes('Opening odds')) {
                    const parent = el.parentElement;
                    if (parent) {
                        const textContent = parent.textContent;
                        const timeMatch = textContent.match(/(\d{1,2}\s+\w+\.?\s*,?\s*\d{1,2}:\d{2})/);
                        const oddsMatch = textContent.match(/(\d+\.\d+)/);

                        if (timeMatch && oddsMatch) {
                            const sync = new SyncTimestamp();
                            const timestamp = sync.parse(timeMatch[1]);
                            if (timestamp) {
                                trajectory.push({
                                    time: timestamp,
                                    value: parseFloat(oddsMatch[1]),
                                    type: 'Initial'
                                });
                            }
                        }
                    }
                    break;
                }
            }

            // Step 2: Extract Historical data
            const tableRows = document.querySelectorAll('tr');
            tableRows.forEach((row) => {
                try {
                    const cells = row.querySelectorAll('td');
                    if (cells.length >= 2) {
                        const firstCell = cells[0].textContent.trim();
                        const secondCell = cells[1].textContent.trim();

                        const sync = new SyncTimestamp();
                        const timestamp = sync.parse(firstCell);
                        const value = parseFloat(secondCell);

                        if (timestamp && !isNaN(value) && value > 1.0) {
                            // Check for duplicates
                            const exists = trajectory.some(p =>
                                p.time === timestamp && p.value === value
                            );
                            if (!exists) {
                                trajectory.push({
                                    time: timestamp,
                                    value: value,
                                    type: 'Historical'
                                });
                            }
                        }
                    }
                } catch (e) {
                    // Ignore row errors
                }
            });

            // Step 3: Sort by time
            trajectory.sort((a, b) => new Date(a.time) - new Date(b.time));

        } catch (error) {
            // Log error but don't fail
            console.error('[TrajectoryParser] Extraction error:', error.message);
        } finally {
            // V122.000: CRITICAL - Fix memory leak by explicitly closing JSDOM
            if (dom) {
                try {
                    dom.window.close();
                } catch (e) {
                    // Ignore cleanup errors
                }
            }
        }

        return trajectory;
    }

    /**
     * Validate trajectory state
     * @param {Array} trajectory - Trajectory array
     * @returns {Object} Validation result
     */
    validateTrajectory(trajectory) {
        if (!Array.isArray(trajectory) || trajectory.length === 0) {
            return {
                valid: false,
                initial: null,
                current: null,
                hasDrift: false,
                error: 'Trajectory is empty'
            };
        }

        if (trajectory.length < DEFAULT_CONFIG.minTrajectoryPoints) {
            return {
                valid: false,
                initial: trajectory[0]?.value || null,
                current: trajectory[trajectory.length - 1]?.value || null,
                hasDrift: false,
                error: `Insufficient points: ${trajectory.length} < ${DEFAULT_CONFIG.minTrajectoryPoints}`
            };
        }

        const initial = trajectory[0].value;
        const current = trajectory[trajectory.length - 1].value;
        const hasDrift = Math.abs(current - initial) > 0.001;

        return {
            valid: true,
            initial,
            current,
            hasDrift,
            trajectoryLength: trajectory.length
        };
    }
}

// ============================================================================
// ERROR CLASS
// ============================================================================

/**
 * Custom error class for QuantHarvester operations
 */
class QuantHarvesterError extends Error {
    /**
     * @param {string} type - Error type identifier
     * @param {string} message - Error message
     * @param {Object} context - Additional context
     */
    constructor(type, message, context = {}) {
        super(message);
        this.name = 'QuantHarvesterError';
        this.errorType = type;
        this.timestamp = new Date().toISOString();
        this.context = context;
    }

    toString() {
        return `[${this.errorType}] [${this.timestamp}] ${this.message}`;
    }
}

// ============================================================================
// MAIN QUANT HARVESTER CLASS
// ============================================================================

/**
 * QuantHarvester - Main harvester class
 * V122.000: Refactored for production readiness
 * - Memory leaks fixed
 * - Hardcoding eliminated
 * - Dependency standardized (uses storage.js)
 * - Export compliance for unit tests
 */
class QuantHarvester {
    static #instance = null;

    /**
     * @param {Object} config - Configuration object
     */
    constructor(config = {}) {
        if (QuantHarvester.#instance) {
            return QuantHarvester.#instance;
        }

        this.config = { ...DEFAULT_CONFIG, ...config };
        this.syncTimestamp = new SyncTimestamp(this.config.currentYear);
        this.trajectoryParser = new TrajectoryParser();
        this.dbClient = null;
        this.browser = null;
        this.context = null;
        this.page = null;
        this.isInitialized = false;

        // Statistics
        this.stats = {
            totalMatches: 0,
            successfulMatches: 0,
            failedMatches: 0,
            totalTrajectoryPoints: 0
        };

        QuantHarvester.#instance = this;
    }

    /**
     * Get singleton instance
     * @param {Object} config - Configuration object
     * @returns {QuantHarvester} Singleton instance
     */
    static getInstance(config) {
        if (!QuantHarvester.#instance) {
            QuantHarvester.#instance = new QuantHarvester(config);
        }
        return QuantHarvester.#instance;
    }

    /**
     * Initialize the harvester (setup browser and database connection)
     * @returns {Promise<void>}
     * @throws {QuantHarvesterError} If initialization fails
     */
    async init() {
        if (this.isInitialized) {
            return;
        }

        try {
            // Connect to database using storage module
            this.dbClient = await createConnection();

            // Launch browser
            this.browser = await chromium.launch({
                headless: this.config.headless,
                args: ['--disable-blink-features=AutomationControlled']
            });

            this.context = await this.browser.newContext({
                userAgent: this.config.userAgent,
                viewport: this.config.viewport
            });

            this.page = await this.context.newPage();

            // Disable images if configured
            if (this.config.disableImages) {
                await this.page.route('**/*.{png,jpg,jpeg,gif,svg,webp}', route => route.abort());
            }

            this.isInitialized = true;

        } catch (error) {
            throw new QuantHarvesterError(
                'INIT_FAILED',
                `Failed to initialize QuantHarvester: ${error.message}`,
                { error: error.message }
            );
        }
    }

    /**
     * Initialize database connection only (for CLI usage without browser)
     * @returns {Promise<void>}
     */
    async initDatabaseOnly() {
        this.dbClient = await createConnection();
    }

    /**
     * Harvest trajectory data from a single match URL
     * @param {string} url - OddsPortal match URL
     * @param {string} sourceId - Unique source identifier
     * @returns {Promise<Object>} Harvest result
     */
    async harvestMatch(url, sourceId) {
        if (!this.isInitialized) {
            await this.init();
        }

        const result = {
            sourceId,
            url,
            entityId: null,
            success: false,
            providerCount: 0,
            trajectoryPoints: 0,
            axes: { home: null, draw: null, away: null },
            error: null,
            startTime: Date.now()
        };

        try {
            // Navigate to page
            await this.page.goto(url, {
                timeout: this.config.timeout,
                waitUntil: 'networkidle'
            });

            // Wait for content
            let waitAttempts = 0;
            while (waitAttempts < 30) {
                const oddsCellCount = await this.page.$$eval('div.odds-cell, .odds-cell', els => els.length);
                if (oddsCellCount > 0) break;
                await this.page.waitForTimeout(1000);
                waitAttempts++;
            }

            // Create entity mapping using storage module
            result.entityId = await getOrCreateEntity(this.dbClient, sourceId, url);

            // Find bookmaker rows
            const bookmakerRows = await this.page.$$('div.flex.h-9.border-b.border-black-borders');

            const whitelistedProviders = new Set();
            const axesData = { home: [], draw: [], away: [] };

            // Process each bookmaker (limit to first 10)
            for (const row of bookmakerRows.slice(0, Math.min(10, bookmakerRows.length))) {
                try {
                    // Get venue name
                    const nameElement = await row.$('img[alt]');
                    let venueName = null;
                    if (nameElement) {
                        venueName = await nameElement.evaluate(el => el.getAttribute('alt'));
                    }

                    const standardVenueId = MARKET_VENUE_WHITELIST.normalizeVenueName(venueName);
                    if (!standardVenueId) continue;

                    whitelistedProviders.add(standardVenueId);

                    // Get odds cells
                    const oddsCells = await row.$$('div.odds-cell, div[class*="odd"]');
                    if (oddsCells.length < 3) continue;

                    // Process each axis
                    for (let i = 0; i < Math.min(3, oddsCells.length); i++) {
                        const axisName = this.config.axes[i];
                        const cell = oddsCells[i];

                        try {
                            await cell.hover();
                            await this.page.waitForTimeout(2000);

                            // Wait for modal
                            const modalSelector = 'h3:has-text("Odds movement")';
                            const modalAppeared = await this.page.$(modalSelector);

                            if (modalAppeared) {
                                let modalHtml = null;
                                try {
                                    modalHtml = await modalAppeared.evaluate(el => {
                                        let container = el;
                                        let depth = 0;
                                        while (container && depth < 10) {
                                            const classes = container.className || '';
                                            const hasModalClass = /modal|popup|dialog|tooltip|dropdown/i.test(classes);
                                            const hasRole = container.getAttribute('role') === 'dialog';
                                            const isFixedOrAbsolute = /fixed|absolute/.test(window.getComputedStyle(container).position);

                                            if (hasModalClass || hasRole || (isFixedOrAbsolute && classes.length > 10)) {
                                                return container.outerHTML;
                                            }
                                            container = container.parentElement;
                                            depth++;
                                        }
                                        return el.parentElement?.outerHTML || el.outerHTML;
                                    });
                                } catch (e) {
                                    // Ignore modal HTML errors
                                }

                                if (modalHtml) {
                                    const trajectory = this.trajectoryParser.extractFullTrajectoryDOM(modalHtml);
                                    const validation = this.trajectoryParser.validateTrajectory(trajectory);

                                    if (validation.valid) {
                                        axesData[axisName] = {
                                            axis: axisName,
                                            dimension: this.config.axisDimensions[axisName],
                                            standardVenueId: standardVenueId,
                                            trajectory: trajectory,
                                            state: validation,
                                            success: true
                                        };

                                        result.trajectoryPoints += trajectory.length;
                                    }
                                }

                                await this.page.mouse.move(0, 0);
                                await this.page.waitForTimeout(500);
                            }

                        } catch (e) {
                            // Ignore axis errors
                        }
                    }

                } catch (e) {
                    // Ignore bookmaker errors
                }
            }

            // Prepare records for database
            const records = [];
            for (const axisName of this.config.axes) {
                const axisData = axesData[axisName];
                if (axisData && axisData.success) {
                    for (const point of axisData.trajectory) {
                        records.push({
                            provider_name: axisData.standardVenueId,
                            metric_type: `quant_price_trajectory_${axisName}`,
                            dimension: axisData.dimension,
                            value: point.value,
                            occurred_at: point.time,
                            sequence: axisData.trajectory.indexOf(point),
                            raw_data: {
                                axis: axisName,
                                pointType: point.type,
                                venueId: axisData.standardVenueId,
                                state: axisData.state
                            }
                        });
                    }
                }
            }

            // Persist to database using storage module
            const persistResult = await upsertTemporalRecords(this.dbClient, result.entityId, records);

            result.success = true;
            result.providerCount = whitelistedProviders.size;
            result.trajectoryPoints = records.length;
            result.axes = axesData;
            result.persistResult = persistResult;

        } catch (error) {
            result.error = error.message;
        }

        result.endTime = Date.now();
        result.duration = (result.endTime - result.startTime) / 1000;

        // Update statistics
        this.stats.totalMatches++;
        if (result.success) {
            this.stats.successfulMatches++;
        } else {
            this.stats.failedMatches++;
        }
        this.stats.totalTrajectoryPoints += result.trajectoryPoints;

        return result;
    }

    /**
     * Process a queue of matches concurrently
     * @param {Array} matches - Array of match objects with url and sourceId
     * @param {Object} options - Processing options
     * @returns {Promise<Object>} Batch processing result
     */
    async startQueue(matches, options = {}) {
        const {
            maxConcurrent = this.config.maxConcurrent,
            batchSize = this.config.batchSize,
            limit = null,
            onProgress = null
        } = options;

        const targetMatches = limit ? matches.slice(0, limit) : matches;
        const totalMatches = targetMatches.length;

        const batchStats = {
            totalProcessed: 0,
            successCount: 0,
            failCount: 0,
            totalTime: 0
        };

        try {
            // Process in batches
            for (let batchStart = 0; batchStart < totalMatches; batchStart += batchSize) {
                const batchEnd = Math.min(batchStart + batchSize, totalMatches);
                const batch = targetMatches.slice(batchStart, batchEnd);

                // Process batch concurrently
                const promises = batch.map(async (match) => {
                    const result = await this.harvestMatch(match.url, match.sourceId);

                    batchStats.totalProcessed++;
                    batchStats.totalTime += result.duration;

                    if (result.success) {
                        batchStats.successCount++;
                    } else {
                        batchStats.failCount++;
                    }

                    // Report progress
                    if (batchStats.totalProcessed % 10 === 0 && onProgress) {
                        onProgress(batchStats.totalProcessed, totalMatches);
                    }

                    return result;
                });

                await Promise.all(promises);
            }

        } catch (error) {
            throw new QuantHarvesterError(
                'QUEUE_FAILED',
                `Queue processing failed: ${error.message}`,
                { error: error.message }
            );
        }

        return {
            totalProcessed: batchStats.totalProcessed,
            successCount: batchStats.successCount,
            failCount: batchStats.failCount,
            successRate: batchStats.totalProcessed > 0 ? batchStats.successCount / batchStats.totalProcessed : 0,
            avgTimePerMatch: batchStats.totalProcessed > 0 ? batchStats.totalTime / batchStats.totalProcessed : 0,
            remaining: totalMatches - batchStats.totalProcessed
        };
    }

    /**
     * Get harvest statistics
     * @returns {Object} Current statistics
     */
    getStats() {
        return { ...this.stats };
    }

    /**
     * Reset statistics
     */
    resetStats() {
        this.stats = {
            totalMatches: 0,
            successfulMatches: 0,
            failedMatches: 0,
            totalTrajectoryPoints: 0
        };
    }

    /**
     * Shutdown the harvester (close browser and database connection)
     * @returns {Promise<void>}
     * @throws {QuantHarvesterError} If shutdown fails
     */
    async shutdown() {
        try {
            if (this.page) {
                await this.page.close();
                this.page = null;
            }

            if (this.context) {
                await this.context.close();
                this.context = null;
            }

            if (this.browser) {
                await this.browser.close();
                this.browser = null;
            }

            if (this.dbClient) {
                await this.dbClient.end();
                this.dbClient = null;
            }

            this.isInitialized = false;

        } catch (error) {
            throw new QuantHarvesterError(
                'SHUTDOWN_FAILED',
                `Failed to shutdown QuantHarvester: ${error.message}`,
                { error: error.message }
            );
        }
    }
}

// ============================================================================
// EXPORTS
// ============================================================================

module.exports = {
    QuantHarvester,
    QuantHarvesterError,
    MARKET_VENUE_WHITELIST,
    SyncTimestamp,
    alignTimestamp,
    TrajectoryParser,
    DEFAULT_CONFIG
};
