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
const fs = require('fs');
const path = require('path');
const {
    createConnection,
    getOrCreateEntity,
    upsertTemporalRecords,
    StorageError
} = require('../../scripts/ops/modules/storage');
const { TrajectoryParser, SyncTimestamp, alignTimestamp } = require('./parsers/TrajectoryParser');

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
    logLevel: process.env.LOG_LEVEL || 'info',

    // V127.000: Stealth Mode - Human behavior simulation
    waitBaseMs: parseInt(process.env.WAIT_BASE_MS) || 2000,
    waitJitterMs: parseInt(process.env.WAIT_JITTER_MS) || 1500,
    cookieBannerTimeout: parseInt(process.env.COOKIE_BANNER_TIMEOUT) || 2000,

    // V129.000: Dynamic Proxy Discovery Configuration
    proxyHost: process.env.PROXY_HOST || '172.25.16.1',
    proxyPortStart: parseInt(process.env.PROXY_PORT_START) || 7891,
    proxyPortEnd: parseInt(process.env.PROXY_PORT_END) || 7913,
    proxyScanTimeout: parseInt(process.env.PROXY_SCAN_TIMEOUT) || 500,
    proxyProtocol: process.env.PROXY_PROTOCOL || 'http',
    enableProxyRotation: process.env.ENABLE_PROXY_ROTATION === 'true'
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
// V129.000: DYNAMIC PROXY DISCOVERY ENGINE
// ============================================================================

/**
 * V129.000 Dynamic Proxy Discovery Engine
 * Auto-discovers proxy nodes via port scanning with circuit breaker pattern
 */
class ProxyPoolManager {
    constructor(config = {}) {
        // Discovery configuration
        this.discoveryConfig = {
            host: config.proxyHost || process.env.PROXY_HOST || '172.25.16.1',
            portStart: parseInt(config.proxyPortStart || process.env.PROXY_PORT_START) || 7891,
            portEnd: parseInt(config.proxyPortEnd || process.env.PROXY_PORT_END) || 7913,
            scanTimeout: config.scanTimeout || 500,  // 500ms per port
            protocol: config.protocol || 'http'
        };

        // Memory-only proxy pool (no file I/O)
        this.proxies = [];
        this.currentIndex = 0;
        this.enabled = false;

        // V129.000: Circuit Breaker - Health tracking
        this.failureCount = new Map();  // proxyId -> consecutive failures
        this.maxFailures = 3;  // Auto-eject after 3 consecutive failures

        // V129.000: Fallback to static file only if auto-discovery fails
        this.configPath = config.proxyConfigPath || path.join(__dirname, '../../config/proxies.json');
    }

    /**
     * V129.000: Auto-discover proxy nodes via port scanning
     * Uses concurrent probing with ultra-short timeout for fast discovery
     *
     * @param {string} host - Target host to scan (optional, uses config default)
     * @param {number} startPort - Start port (optional, uses config default)
     * @param {number} endPort - End port (optional, uses config default)
     * @returns {Promise<number>} Number of discovered proxies
     */
    async discoverProxies(host = null, startPort = null, endPort = null) {
        const targetHost = host || this.discoveryConfig.host;
        const start = startPort || this.discoveryConfig.portStart;
        const end = endPort || this.discoveryConfig.portEnd;

        console.log(`[V129.000] Starting proxy discovery: ${targetHost}:${start}-${end}`);

        const discovered = [];
        const totalPorts = end - start + 1;

        // Create probe promises for all ports
        const probePromises = [];
        for (let port = start; port <= end; port++) {
            probePromises.push(this._probePort(targetHost, port));
        }

        // Execute probes concurrently (Promise.allSettled for resilience)
        const results = await Promise.allSettled(probePromises);

        // Collect successful probes
        results.forEach((result, index) => {
            const port = start + index;
            if (result.status === 'fulfilled' && result.value) {
                discovered.push({
                    id: `PROXY-${String(port).slice(-2)}`,
                    protocol: this.discoveryConfig.protocol,
                    host: targetHost,
                    port: port,
                    source: 'auto_discovery',
                    verified: true,
                    last_checked: new Date().toISOString()
                });
            }
        });

        // Update memory pool
        this.proxies = discovered;
        this.enabled = discovered.length > 0;

        console.log(`[V129.000] Discovery complete: ${discovered.length}/${totalPorts} nodes available`);

        // Fallback to static file if no proxies discovered
        if (this.enabled === false) {
            console.warn('[V129.000] Auto-discovery found no proxies, attempting fallback...');
            await this._loadFallback();
        }

        return discovered.length;
    }

    /**
     * V129.000: Probe single port with ultra-short timeout
     * Uses Node.js net.connect for TCP-level handshake test
     *
     * @param {string} host - Target host
     * @param {number} port - Target port
     * @returns {Promise<boolean>} True if port is open
     * @private
     */
    async _probePort(host, port) {
        return new Promise((resolve) => {
            const net = require('net');
            const socket = new net.Socket();

            // Set ultra-short timeout for fast scanning
            socket.setTimeout(this.discoveryConfig.scanTimeout);

            socket.on('connect', () => {
                socket.destroy();
                resolve(true);  // Port is open
            });

            socket.on('timeout', () => {
                socket.destroy();
                resolve(false);  // Port timeout
            });

            socket.on('error', () => {
                socket.destroy();
                resolve(false);  // Port closed
            });

            socket.connect(port, host);
        });
    }

    /**
     * V129.000: Fallback loader for static proxy configuration
     * Only used if auto-discovery fails completely
     *
     * @returns {Promise<boolean>}
     * @private
     */
    async _loadFallback() {
        try {
            if (fs.existsSync(this.configPath)) {
                const config = JSON.parse(fs.readFileSync(this.configPath, 'utf8'));
                this.proxies = config.proxies || [];
                this.enabled = this.proxies.length > 0;
                console.log(`[V129.000] Fallback loaded: ${this.proxies.length} proxies from ${this.configPath}`);
                return this.enabled;
            }
        } catch (error) {
            console.warn(`[V129.000] Fallback failed: ${error.message}`);
        }
        return false;
    }

    /**
     * V129.000: Get next proxy with circuit breaker health check
     * Skips proxies with consecutive failure count >= maxFailures
     *
     * @returns {Object|null} Proxy configuration or null
     */
    getNextProxy() {
        if (!this.enabled || this.proxies.length === 0) {
            return null;
        }

        // Find next healthy proxy (round-robin with skip logic)
        let attempts = 0;
        const maxAttempts = this.proxies.length;
        let proxy = null;
        let originalIndex = this.currentIndex;

        do {
            proxy = this.proxies[this.currentIndex];
            this.currentIndex = (this.currentIndex + 1) % this.proxies.length;
            attempts++;

            // Check circuit breaker status
            const failures = this.failureCount.get(proxy.id) || 0;
            if (failures < this.maxFailures) {
                return {
                    server: `${proxy.protocol}://${proxy.host}:${proxy.port}`,
                    id: proxy.id,
                    username: proxy.username || undefined,
                    password: proxy.password || undefined
                };
            }

            // All proxies exhausted
            if (attempts >= maxAttempts) {
                console.warn('[V129.000] Circuit Breaker: All proxies exhausted, resetting...');
                this.failureCount.clear();
                this.currentIndex = originalIndex;
                return null;
            }
        } while (attempts < maxAttempts);

        return null;
    }

    /**
     * V129.000: Report proxy failure (triggers circuit breaker)
     * Call this when harvestMatch encounters proxy-related errors
     *
     * @param {string} proxyId - Proxy identifier
     */
    reportFailure(proxyId) {
        if (!proxyId) return;

        const currentFailures = this.failureCount.get(proxyId) || 0;
        const newFailures = currentFailures + 1;
        this.failureCount.set(proxyId, newFailures);

        if (newFailures >= this.maxFailures) {
            console.warn(`[V129.000] Circuit Breaker: Proxy ${proxyId} ejected (${newFailures} failures)`);
        }
    }

    /**
     * V129.000: Report proxy success (resets circuit breaker counter)
     * Call this when harvestMatch succeeds
     *
     * @param {string} proxyId - Proxy identifier
     */
    reportSuccess(proxyId) {
        if (!proxyId) return;

        const currentFailures = this.failureCount.get(proxyId);
        if (currentFailures && currentFailures > 0) {
            this.failureCount.delete(proxyId);
            console.log(`[V129.000] Circuit Breaker: Proxy ${proxyId} recovered`);
        }
    }

    /**
     * V129.000: Get random proxy (alternative strategy, not recommended for circuit breaker)
     * @returns {Object|null} Proxy configuration or null
     */
    getRandomProxy() {
        if (!this.enabled || this.proxies.length === 0) {
            return null;
        }

        // Filter healthy proxies only
        const healthyProxies = this.proxies.filter(p => {
            const failures = this.failureCount.get(p.id) || 0;
            return failures < this.maxFailures;
        });

        if (healthyProxies.length === 0) {
            return null;
        }

        const proxy = healthyProxies[Math.floor(Math.random() * healthyProxies.length)];
        return {
            server: `${proxy.protocol}://${proxy.host}:${proxy.port}`,
            id: proxy.id,
            username: proxy.username || undefined,
            password: proxy.password || undefined
        };
    }

    /**
     * Check if proxy pool is enabled
     * @returns {boolean}
     */
    isEnabled() {
        return this.enabled;
    }

    /**
     * V129.000: Get proxy pool statistics including circuit breaker status
     * @returns {Object}
     */
    getStats() {
        const healthyCount = this.proxies.filter(p => {
            const failures = this.failureCount.get(p.id) || 0;
            return failures < this.maxFailures;
        }).length;

        const ejectedCount = this.proxies.length - healthyCount;

        return {
            total: this.proxies.length,
            enabled: this.enabled,
            healthy: healthyCount,
            ejected: ejectedCount,
            currentIndex: this.currentIndex,
            discoveryRange: `${this.discoveryConfig.host}:${this.discoveryConfig.portStart}-${this.discoveryConfig.portEnd}`,
            failureMap: Object.fromEntries(this.failureCount)
        };
    }

    /**
     * V129.000: Reset circuit breaker (manual recovery)
     */
    resetCircuitBreaker() {
        this.failureCount.clear();
        console.log('[V129.000] Circuit Breaker: Manual reset complete');
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

        // V129.000: Dynamic Proxy Discovery Engine (no static config path)
        this.proxyPool = new ProxyPoolManager({
            proxyHost: this.config.proxyHost,
            proxyPortStart: this.config.proxyPortStart,
            proxyPortEnd: this.config.proxyPortEnd,
            scanTimeout: this.config.proxyScanTimeout,
            protocol: this.config.proxyProtocol
        });

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

            // V129.000: Auto-discover proxy nodes if rotation is enabled
            if (this.config.enableProxyRotation) {
                const discovered = await this.proxyPool.discoverProxies();
                console.log(`[V129.000] Proxy discovery: ${discovered} nodes found`);
            }

            // Launch browser
            this.browser = await chromium.launch({
                headless: this.config.headless,
                args: ['--disable-blink-features=AutomationControlled']
            });

            // V129.000: Get proxy configuration for this instance
            const contextConfig = {
                userAgent: this.config.userAgent,
                viewport: this.config.viewport
            };

            // Inject proxy if rotation is enabled and pool is available
            this.currentProxyId = null;
            if (this.config.enableProxyRotation && this.proxyPool.isEnabled()) {
                const proxy = this.proxyPool.getNextProxy();
                if (proxy) {
                    contextConfig.proxy = proxy;
                    this.currentProxyId = proxy.id;
                    if (this.config.logLevel === 'debug') {
                        console.log(`[V129.000] Using proxy: ${proxy.server} (ID: ${proxy.id})`);
                    }
                }
            }

            this.context = await this.browser.newContext(contextConfig);

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
     * V127.000: Randomized jitter wait for stealth
     * Replaces all hardcoded waitForTimeout calls with human-like random delays
     * @param {number} baseMs - Base wait time in milliseconds
     * @param {number} rangeMs - Random jitter range in milliseconds
     * @returns {Promise<void>}
     * @private
     */
    async jitterWait(baseMs = null, rangeMs = null) {
        const base = baseMs ?? this.config.waitBaseMs;
        const range = rangeMs ?? this.config.waitJitterMs;
        const delay = base + Math.random() * range;
        await this.page.waitForTimeout(delay);
    }

    /**
     * V127.000: Handle cookie consent overlays
     * Automatically detects and dismisses OneTrust Cookie banners
     * @returns {Promise<boolean>} True if banner was handled
     * @private
     */
    async handleOverlays() {
        try {
            // Wait briefly for overlay to appear
            await this.page.waitForTimeout(500);

            // Try multiple selector patterns for OneTrust/Accept buttons
            const selectors = [
                'button:has-text("Accept All")',
                'button:has-text("Accept")',
                'button:has-text("OK")',
                'button[aria-label*="Accept" i]',
                'button[aria-label*="Consent" i]',
                '.onetrust-pc-dark-filter',  // Dark background overlay
                '#onetrust-consent-sdk'  // Main container
            ];

            for (const selector of selectors) {
                try {
                    const element = await this.page.$(selector);
                    if (element) {
                        // Check if element is visible
                        const isVisible = await element.isVisible();
                        if (isVisible) {
                            await element.click();
                            if (this.config.logLevel === 'debug') {
                                console.log(`[V127.000] Dismissed cookie banner: ${selector}`);
                            }
                            await this.page.waitForTimeout(1000);
                            return true;
                        }
                    }
                } catch (e) {
                    // Selector not found or error, continue to next
                }
            }

            // If we reached here, no banner was dismissed (which is OK)
            return false;

        } catch (error) {
            // Silently fail - don't block execution if banner handling fails
            if (this.config.logLevel === 'debug') {
                console.warn(`[V127.000] Cookie banner handling skipped: ${error.message}`);
            }
            return false;
        }
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

            // V127.000: Handle cookie consent overlays
            await this.handleOverlays();

            // Wait for content
            let waitAttempts = 0;
            while (waitAttempts < 30) {
                const oddsCellCount = await this.page.$$eval('div.odds-cell, .odds-cell', els => els.length);
                if (oddsCellCount > 0) break;
                await this.jitterWait(1000, 500);  // V127.000: Randomized wait
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
                            await this.jitterWait();  // V127.000: Randomized 2-3.5s wait

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
                                await this.jitterWait(500, 300);  // V127.000: Randomized 0.5-0.8s wait
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

            // V129.000: Report success to circuit breaker
            if (this.currentProxyId) {
                this.proxyPool.reportSuccess(this.currentProxyId);
            }

        } catch (error) {
            result.error = error.message;

            // V129.000: Report failure to circuit breaker
            if (this.currentProxyId) {
                this.proxyPool.reportFailure(this.currentProxyId);
            }
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
    ProxyPoolManager,
    SyncTimestamp,
    alignTimestamp,
    TrajectoryParser,
    DEFAULT_CONFIG
};
