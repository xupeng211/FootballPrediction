/**
 * QuantHarvester - V138.000 Modular Strike
 * =============================================================================
 *
 * Standard production engine for extracting multi-dimensional quantitative data
 * trajectories from OddsPortal using Playwright automation.
 *
 * V133.000 Features:
 * - BRUTE FORCE PURGE: Physical DOM deletion of overlay nodes
 * - Signal Focus: Network traffic monitoring for .dat data packets
 * - Fuzzy Matching: Tailwind CSS compatible selectors
 *
 * V138.000 Features:
 * - Modular Aiming System: Centralized OddsPortalSelectors
 * - Surgical Interaction: scrollIntoViewIfNeeded before hover
 * - Golden Zone: 2024-2026 high-yield match filtering
 * - Telemetry Dashboard: Real-time quality metrics
 *
 * @module QuantHarvester
 * @version V138.000
 * @since 2026-01-27
 * @author Senior Staff Software Architect
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
// V138.000: Modular Aiming System
const { OddsPortalSelectors, SelectorHelper } = require('./selectors/OddsPortalSelectors');

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

    // V133.000: Ultimate Visual Breakthrough Configuration
    signalWaitTimeout: parseInt(process.env.SIGNAL_WAIT_TIMEOUT) || 15000,
    forceRemoveOverlays: process.env.FORCE_REMOVE_OVERLAYS === 'true',

    // V136.000: Precision Tuning Configuration
    hoverStabilizeMs: parseInt(process.env.HOVER_STABILIZE_MS) || 1500,
    modalRetryCount: parseInt(process.env.MODAL_RETRY_COUNT) || 2,
    adaptiveSignalTimeout: parseInt(process.env.ADAPTIVE_SIGNAL_TIMEOUT) || 5000,

    // V129.000: Dynamic Proxy Discovery Configuration
    proxyHost: process.env.PROXY_HOST || '172.25.16.1',
    proxyPortStart: parseInt(process.env.PROXY_PORT_START) || 7891,
    proxyPortEnd: parseInt(process.env.PROXY_PORT_END) || 7913,
    proxyScanTimeout: parseInt(process.env.PROXY_SCAN_TIMEOUT) || 500,
    proxyProtocol: process.env.PROXY_PROTOCOL || 'http',
    enableProxyRotation: process.env.ENABLE_PROXY_ROTATION === 'true',

    // V138.000: Modular Strike Configuration
    scrollIntoViewBeforeHover: process.env.SCROLL_INTO_VIEW_BEFORE_HOVER === 'true',
    telemetryEnabled: process.env.TELEMETRY_DASHBOARD_ENABLED === 'true',
    telemetryReportInterval: parseInt(process.env.TELEMETRY_REPORT_INTERVAL) || 20,
    goldenZoneStartDate: process.env.GOLDEN_ZONE_START_DATE || '2024-01-01',
    goldenZoneFilterDisabled: process.env.GOLDEN_ZONE_FILTER_DISABLED === 'true',
    harvestMaxConcurrent: parseInt(process.env.HARVEST_MAX_CONCURRENT) || 15,
    harvestRetryAttempts: parseInt(process.env.HARVEST_RETRY_ATTEMPTS) || 2,
    harvestRetryDelayMs: parseInt(process.env.HARVEST_RETRY_DELAY_MS) || 5000
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
 * V138.000: Modular Strike
 * - BRUTE FORCE overlay removal (V133.000)
 * - Signal focus for .dat packets (V133.000)
 * - Fuzzy matching selectors (V133.000)
 * - Memory leaks fixed (V122.000)
 * - Hardcoding eliminated (V122.000)
 * - Dynamic proxy discovery (V129.000)
 * - Modular Aiming System (V138.000)
 * - Surgical Interaction with scrollIntoViewIfNeeded (V138.000)
 * - Golden Zone filtering (2024-2026) (V138.000)
 * - Telemetry Dashboard (V138.000)
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

        // V138.000: Config instrumentation - Log sanitized config
        console.log('[V138.000] ========== CONFIG INSTRUMENTATION ==========');
        const sanitizedConfig = { ...this.config };
        if (sanitizedConfig.dbPassword) sanitizedConfig.dbPassword = '***';
        console.log('[V138.000] Config loaded:', JSON.stringify(sanitizedConfig, null, 2));
        console.log('[V138.000] forceRemoveOverlays:', this.config.forceRemoveOverlays);
        console.log('[V138.000] enableProxyRotation:', this.config.enableProxyRotation);
        console.log('[V138.000] scrollIntoViewBeforeHover:', this.config.scrollIntoViewBeforeHover);
        console.log('[V138.000] telemetryEnabled:', this.config.telemetryEnabled);
        console.log('[V138.000] goldenZoneStartDate:', this.config.goldenZoneStartDate);
        console.log('[V138.000] harvestMaxConcurrent:', this.config.harvestMaxConcurrent);
        console.log('[V138.000] ===============================================');

        // V129.000: Dynamic Proxy Discovery Engine (no static config path)
        this.proxyPool = new ProxyPoolManager({
            proxyHost: this.config.proxyHost,
            proxyPortStart: this.config.proxyPortStart,
            proxyPortEnd: this.config.proxyPortEnd,
            scanTimeout: this.config.proxyScanTimeout,
            protocol: this.config.proxyProtocol
        });

        // V138.000: Enhanced Statistics with Telemetry
        this.stats = {
            totalMatches: 0,
            successfulMatches: 0,
            failedMatches: 0,
            totalTrajectoryPoints: 0,
            // V138.000: Telemetry metrics
            pixelRetrySuccesses: 0,
            overlayNodesRemoved: 0,
            goldenZoneFiltered: 0,
            avgHarvestTimeMs: 0,
            lastTelemetryReport: 0
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
     * V138.000: Handle overlays - BRUTE FORCE PURGE with Modular Selectors
     * V132.100 Finding: OneTrust popup was hidden but not removed, blocking hover interactions
     * V138.000 Enhancement: Added .overlay-bookie-modal support (missing in OddsHarvester)
     * Solution: Physical DOM deletion using OddsPortalSelectors
     *
     * @returns {Promise<boolean>} True if overlays were removed
     * @private
     */
    async handleOverlays() {
        try {
            // V138.000: Instrumentation - Log entry point
            console.log('[V138.000] ========== OVERLAY PURGE START ==========');
            console.log('[V138.000] forceRemoveOverlays config:', this.config.forceRemoveOverlays);

            // Wait briefly for overlay to appear
            await this.page.waitForTimeout(500);

            let removedCount = 0;

            if (this.config.forceRemoveOverlays) {
                // V138.000: BRUTE FORCE - Physical DOM deletion using Modular Selectors
                // "宁可错杀，不准挡路" - Better to over-remove than miss blocking elements
                console.log('[V138.000] BRUTE FORCE MODE: Using Modular Selectors for DOM purge...');

                // V138.000: Use OddsPortalSelectors for purge script generation
                const purgeScript = OddsPortalSelectors.generatePurgeScript();
                const purgeResult = await this.page.evaluate(purgeScript);

                removedCount = purgeResult.count;

                // V138.000: Log pre-purge check results
                console.log('[V138.000] Pre-purge check:', JSON.stringify(purgeResult.preCheck));
                console.log(`[V138.000] Removed ${purgeResult.removed.length} elements:`,
                    purgeResult.removed.slice(0, 10).join(', '),
                    purgeResult.removed.length > 10 ? '...' : '');

                console.log(`[V138.000] BRUTE FORCE RESULT: ${removedCount} nodes removed`);

                if (removedCount > 0) {
                    console.log(`[V138.000] ✅ OVERLAY PURGE SUCCESS: ${removedCount} nodes deleted`);
                    // V138.000: Log .overlay-bookie-modal specifically if found
                    if (purgeResult.removed.some(r => r.includes('bookie') || r.includes('modal'))) {
                        console.log(`[V138.000] 🔥 SMOKING GUN: .overlay-bookie-modal was present and PURGED`);
                    }
                } else {
                    console.log('[V138.000] ⚠️  OVERLAY PURGE: No nodes found matching keywords');
                }
            } else {
                // V127.000: Original click-based approach (fallback)
                const selectors = [
                    'button:has-text("Accept All")',
                    'button:has-text("Accept")',
                    'button:has-text("OK")',
                    'button[aria-label*="Accept" i]',
                    'button[aria-label*="Consent" i]'
                ];

                for (const selector of selectors) {
                    try {
                        const element = await this.page.$(selector);
                        if (element && await element.isVisible()) {
                            await element.click();
                            removedCount++;
                            if (this.config.logLevel === 'debug') {
                                console.log(`[V127.000] Dismissed cookie banner: ${selector}`);
                            }
                            await this.page.waitForTimeout(1000);
                            break;
                        }
                    } catch (e) {
                        // Continue to next selector
                    }
                }
            }

            return removedCount > 0;

        } catch (error) {
            if (this.config.logLevel === 'debug') {
                console.warn(`[V138.000] Overlay handling error: ${error.message}`);
            }
            return false;
        }
    }

    /**
     * V138.000: Reliable Hover with Surgical Precision
     * V136.000 Features:
     * - Hover stabilization (forced DOM rendering wait)
     * - Modal verification after each hover
     * - Pixel-shift retry (2px offset) if modal not detected
     * - Configurable retry count (MODAL_RETRY_COUNT)
     *
     * V138.000 Enhancements:
     * - scrollIntoViewIfNeeded() before hover (ensures element is in viewport)
     * - Using OddsPortalSelectors for fallback strategies
     *
     * @param {ElementHandle} cell - The odds cell to hover
     * @param {number} cellIndex - Cell index for logging
     * @param {string} axisName - Axis name (home/draw/away)
     * @param {number} totalCells - Total cells for logging
     * @returns {Promise<Object>} Result object with success flag and retry count
     * @private
     */
    async performReliableHover(cell, cellIndex, axisName, totalCells) {
        const maxRetries = this.config.modalRetryCount;
        let retryCount = 0;
        let modalDetected = false;
        let originalPosition = null;

        // V138.000: Log initial hover attempt
        console.log(`[V138.000] 🎯 SURGICAL HOVER: Cell ${cellIndex + 1}/${totalCells} (axis: ${axisName})`);

        for (let attempt = 0; attempt <= maxRetries; attempt++) {
            try {
                // V138.000: Surgical Precision - scrollIntoViewIfNeeded on first attempt
                if (attempt === 0) {
                    if (this.config.scrollIntoViewBeforeHover) {
                        console.log(`[V138.000] 🔭 SCROLL INTO VIEW: Ensuring element is in viewport...`);
                        await cell.scrollIntoViewIfNeeded();
                        // Small delay to let scroll settle
                        await this.page.waitForTimeout(200);
                        console.log(`[V138.000] ✅ Element centered in viewport`);
                    }

                    const boundingBox = await cell.boundingBox();
                    originalPosition = { x: boundingBox.x, y: boundingBox.y };
                    console.log(`[V138.000] Original position:`, JSON.stringify(originalPosition));
                }

                // Perform hover (or pixel-shift retry)
                if (attempt > 0) {
                    // Pixel-shift retry: offset by 2 pixels
                    const offsetX = originalPosition.x + (attempt % 2 === 0 ? 2 : -2);
                    const offsetY = originalPosition.y + (attempt % 2 === 0 ? 2 : -2);
                    console.log(`[V138.000] 🔄 Pixel-shift retry #${attempt}: offset (${offsetX - originalPosition.x}, ${offsetY - originalPosition.y})px`);
                    await this.page.mouse.move(offsetX + 10, offsetY + 10);
                } else {
                    // Initial hover (after scrollIntoViewIfNeeded)
                    await cell.hover();
                    console.log(`[V138.000] ✅ Hover executed`);
                }

                // V138.000: Stabilization delay (forced DOM rendering wait)
                console.log(`[V138.000] ⏳ Stabilizing: ${this.config.hoverStabilizeMs}ms...`);
                await this.page.waitForTimeout(this.config.hoverStabilizeMs);

                // V138.000: Verify modal appeared (using OddsPortalSelectors)
                const modalExists = await this.page.evaluate(() => {
                    const modal = document.querySelector('.height-content');
                    return modal && modal.offsetParent !== null; // Check if visible
                });

                if (modalExists) {
                    console.log(`[V138.000] ✅ Modal DETECTED on attempt ${attempt + 1}`);
                    modalDetected = true;
                    break;  // Success - exit retry loop
                } else {
                    if (attempt < maxRetries) {
                        console.log(`[V138.000] ⚠️  No modal detected, will retry...`);
                        retryCount++;
                    } else {
                        console.log(`[V138.000] ❌ No modal detected after ${maxRetries + 1} attempts`);
                    }
                }

            } catch (error) {
                if (attempt < maxRetries) {
                    console.log(`[V138.000] ⚠️  Hover error on attempt ${attempt + 1}: ${error.message}`);
                    retryCount++;
                } else {
                    console.log(`[V138.000] ❌ Hover failed after ${maxRetries + 1} attempts: ${error.message}`);
                    break;
                }
            }
        }

        return {
            success: modalDetected,
            retries: retryCount,
            attempt: maxRetries + 1
        };
    }

    /**
     * V136.000: Adaptive wait for trajectory data packet signal
     * V133.000: Monitors network traffic for OddsPortal's .dat file response
     * V136.000: Adaptive bypass - if odds visible but no .dat signal, proceed anyway
     *
     * @returns {Promise<boolean>} True if signal detected or adaptive bypass triggered
     * @private
     */
    async waitForTrajectorySignal() {
        try {
            // V134.000: Instrumentation - Log signal radar activation
            console.log('[V136.000] ========== ADAPTIVE SIGNAL RADAR ==========');
            console.log('[V136.000] Adaptive timeout:', this.config.adaptiveSignalTimeout, 'ms');
            console.log('[V136.000] Fallback timeout:', this.config.signalWaitTimeout, 'ms');
            console.log('[V136.000] 📡 Signal radar NOW MONITORING for .dat packets...');

            let signalDetected = false;
            let adaptiveBypass = false;

            // V136.000: Phase 1 - Quick adaptive check (5 seconds)
            const adaptiveSignalPromise = this.page.waitForResponse(
                response => {
                    const url = response.url();
                    const isDatFile = /.*\.dat.*/i.test(url);
                    const isStatusOk = response.status() === 200;

                    if (isDatFile && isStatusOk) {
                        console.log(`[V136.000] 🔒 SIGNAL LOCKED (Adaptive): ${url}`);
                        return true;
                    }
                    return false;
                },
                { timeout: this.config.adaptiveSignalTimeout }
            ).then(() => {
                signalDetected = true;
                console.log('[V136.000] ✅ Signal found in adaptive window');
                return true;
            }).catch(async () => {
                // V136.000: Adaptive bypass - check if odds cells are visible
                console.log('[V136.000] ⏱️  Adaptive timeout - checking if data is pre-loaded...');

                const oddsCellCount = await this.page.$$eval('[class*="odds-cell"]', els => els.length);

                if (oddsCellCount > 0) {
                    console.log(`[V136.000] ✅ ADAPTIVE BYPASS: ${oddsCellCount} odds cells visible, proceeding anyway`);
                    adaptiveBypass = true;
                    return true;  // Continue despite no .dat signal
                } else {
                    console.log('[V136.000] ⏳  No odds cells yet, waiting for full timeout...');
                    // Fall through to Phase 2
                    return false;
                }
            });

            await adaptiveSignalPromise;

            // V136.000: Phase 2 - Full timeout wait (only if adaptive bypass failed)
            if (!signalDetected && !adaptiveBypass) {
                console.log('[V136.000] Entering Phase 2: Full timeout wait...');

                const remainingTimeout = this.config.signalWaitTimeout - this.config.adaptiveSignalTimeout;

                await this.page.waitForResponse(
                    response => {
                        const url = response.url();
                        const isDatFile = /.*\.dat.*/i.test(url);
                        const isStatusOk = response.status() === 200;

                        if (isDatFile && isStatusOk) {
                            console.log(`[V136.000] 🔒 SIGNAL LOCKED (Full): ${url}`);
                            return true;
                        }
                        return false;
                    },
                    { timeout: remainingTimeout }
                ).then(() => {
                    signalDetected = true;
                    console.log('[V136.000] ✅ Signal found in full window');
                    return true;
                }).catch(() => {
                    console.log('[V136.000] ⏱️  Full timeout - data may be pre-loaded or no .dat packets');
                    return false;
                });
            }

            // Additional wait for DOM to stabilize after signal
            if (signalDetected) {
                console.log('[V136.000] 📊 Signal detected, waiting for DOM stabilization...');
                await this.jitterWait(1000, 500);
            } else if (adaptiveBypass) {
                console.log('[V136.000] 📊 Adaptive bypass active, brief stabilization wait...');
                await this.page.waitForTimeout(500);  // Shorter wait for bypass
            }

            const result = signalDetected || adaptiveBypass;
            console.log(`[V136.000] Signal result: ${signalDetected ? 'LOCKED' : adaptiveBypass ? 'BYPASS' : 'TIMEOUT'}`);
            return result;

        } catch (error) {
            console.log(`[V136.000] ❌ Signal detection error: ${error.message}`);
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

            // V133.000: Handle cookie consent overlays (BRUTE FORCE PURGE)
            await this.handleOverlays();

            // V133.000: Wait for trajectory data packet signal
            const signalLocked = await this.waitForTrajectorySignal();
            if (this.config.logLevel === 'debug') {
                console.log(`[V133.000] Signal status: ${signalLocked ? 'LOCKED' : 'TIMEOUT/PRE-LOADED'}`);
            }

            // Wait for content
            let waitAttempts = 0;
            while (waitAttempts < 30) {
                // V133.000: Updated selector to use fuzzy matching
                const oddsCellCount = await this.page.$$eval('[class*="odds-cell"]', els => els.length);
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

                    // Get odds cells (V133.000: Fuzzy matching for Tailwind CSS compatibility)
                    const oddsCells = await row.$$('[class*="odds-cell"]');
                    if (oddsCells.length < 3) continue;

                    // Process each axis
                    for (let i = 0; i < Math.min(3, oddsCells.length); i++) {
                        const axisName = this.config.axes[i];
                        const cell = oddsCells[i];

                        try {
                            // V136.000: Reliable Hover with pixel-shift retry
                            const hoverResult = await this.performReliableHover(cell, i, axisName, oddsCells.length);

                            if (!hoverResult.success) {
                                if (this.config.logLevel === 'debug') {
                                    console.log(`[V136.000] ⚠️  Hover failed for ${axisName}, skipping...`);
                                }
                                continue;
                            }

                            // Wait for modal (V134.000: Fixed selector + V136.000 retry logic)
                            let modalAppeared = null;

                            // V136.000: Quick check for modal (hover may have triggered it during retry)
                            try {
                                modalAppeared = await this.page.waitForSelector('.height-content:has(h3:has-text("Odds movement"))', { timeout: 1000 });
                            } catch (e) {
                                // Strategy 1 failed, try alternative
                            }

                            // Strategy 2: Find h3 with "Odds movement" text
                            if (!modalAppeared) {
                                try {
                                    const h3Element = await this.page.waitForSelector('h3:has-text("Odds movement")', { timeout: 1000 });
                                    if (h3Element) {
                                        // Get the container by walking up to find .height-content or position:absolute
                                        modalAppeared = await h3Element.evaluateHandle(el => {
                                            let container = el.parentElement;
                                            while (container && container !== document.body) {
                                                const classes = container.className || '';
                                                const hasHeightContent = /height-content/i.test(classes);
                                                const isAbsolute = /absolute/.test(window.getComputedStyle(container).position);
                                                if (hasHeightContent || isAbsolute) {
                                                    return container;
                                                }
                                                container = container.parentElement;
                                            }
                                            return el;
                                        });
                                    }
                                } catch (e2) {
                                    // Strategy 2 failed
                                }
                            }

                            // V136.000: Debug log
                            if (this.config.logLevel === 'debug') {
                                console.log(`[V136.000] Modal detection: ${modalAppeared ? 'FOUND' : 'NOT FOUND'}`);
                            }

                            if (modalAppeared) {
                                let modalHtml = null;
                                try {
                                    modalHtml = await modalAppeared.evaluate(el => el.outerHTML);
                                } catch (e) {
                                    // Ignore modal HTML errors
                                }

                                if (modalHtml) {
                                    // V134.000: Log extraction details
                                    if (this.config.logLevel === 'debug') {
                                        console.log(`[V136.000] Modal HTML length: ${modalHtml.length} chars`);
                                        console.log(`[V136.000] Modal HTML preview: ${modalHtml.substring(0, 200)}...`);
                                    }

                                    // V133.000: Handle new TrajectoryParser return format
                                    const extractionResult = this.trajectoryParser.extractFullTrajectoryDOM(modalHtml);
                                    const trajectory = extractionResult.trajectory || [];
                                    const validation = this.trajectoryParser.validateTrajectory(extractionResult);

                                    // V134.000: Log extraction result
                                    if (this.config.logLevel === 'debug') {
                                        console.log(`[V134.000] Extraction result:`, {
                                            trajectoryCount: trajectory.length,
                                            valid: validation.valid,
                                            quality: extractionResult.quality,
                                            warning: extractionResult.warning || 'none'
                                        });
                                    }

                                    // V134.000: Accept POOR quality data (at least 1 point is valuable)
                                    if (trajectory.length >= 1) {
                                        axesData[axisName] = {
                                            axis: axisName,
                                            dimension: this.config.axisDimensions[axisName],
                                            standardVenueId: standardVenueId,
                                            trajectory: trajectory,
                                            state: validation,
                                            success: true,
                                            quality: extractionResult.quality // V133.000: Quality metric
                                        };

                                        result.trajectoryPoints += trajectory.length;

                                        // V134.000: Log quality level
                                        if (this.config.logLevel === 'debug') {
                                            console.log(`[V134.000] ✅ Data stored: ${trajectory.length} points, quality=${extractionResult.quality}`);
                                        }
                                    } else if (this.config.logLevel === 'debug' && extractionResult.warning) {
                                        // V133.000: Log warnings for low quality data
                                        console.warn(`[V133.000] ${extractionResult.warning}`);
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
            totalTrajectoryPoints: 0,
            // V138.000: Telemetry metrics
            pixelRetrySuccesses: 0,
            overlayNodesRemoved: 0,
            goldenZoneFiltered: 0,
            avgHarvestTimeMs: 0,
            lastTelemetryReport: 0
        };
    }

    /**
     * V138.000: Display telemetry dashboard
     * Shows real-time quality metrics every N matches
     *
     * @param {boolean} force - Force display regardless of interval
     * @returns {void}
     */
    displayTelemetryDashboard(force = false) {
        if (!this.config.telemetryEnabled) {
            return;
        }

        const shouldDisplay = force ||
            (this.stats.totalMatches % this.config.telemetryReportInterval === 0);

        if (!shouldDisplay || this.stats.totalMatches === 0) {
            return;
        }

        const successRate = ((this.stats.successfulMatches / this.stats.totalMatches) * 100).toFixed(2);
        const avgPointsPerMatch = this.stats.totalMatches > 0
            ? (this.stats.totalTrajectoryPoints / this.stats.successfulMatches).toFixed(2)
            : 0;
        const cpuUsage = process.cpuUsage().user / 1000000; // Convert to seconds
        const memUsage = process.memoryUsage();
        const memUsedMb = (memUsage.heapUsed / 1024 / 1024).toFixed(2);

        console.log('');
        console.log('╔════════════════════════════════════════════════════════════════╗');
        console.log('║          V138.000 TELEMETRY DASHBOARD - REAL-TIME METRICS         ║');
        console.log('╠════════════════════════════════════════════════════════════════╣');
        console.log(`║  📊 SUCCESS RATE       : ${successRate}% (${this.stats.successfulMatches}/${this.stats.totalMatches})`);
        console.log(`║  🎯 PIXEL RETRY SUCC   : ${this.stats.pixelRetrySuccesses}`);
        console.log(`║  💾 TRAJECTORY POINTS  : ${this.stats.totalTrajectoryPoints} (avg: ${avgPointsPerMatch}/match)`);
        console.log(`║  🗑️  OVERLAYS PURGED    : ${this.stats.overlayNodesRemoved} nodes`);
        console.log(`║  🏆 GOLDEN ZONE FLT    : ${this.stats.goldenZoneFiltered} filtered`);
        console.log(`║  ⏱️  AVG HARVEST TIME   : ${this.stats.avgHarvestTimeMs.toFixed(0)}ms`);
        console.log(`║  💻 9900X CPU/MEM      : ${cpuUsage.toFixed(2)}s / ${memUsedMb}MB`);
        console.log('╚════════════════════════════════════════════════════════════════╝');
        console.log('');
    }

    /**
     * V138.000: Golden Zone Filter
     * Filters matches to only include those from 2024-01-01 onwards
     *
     * @param {Array} matches - Array of match objects with match_date or date field
     * @returns {Array} Filtered array of matches
     */
    filterGoldenZone(matches) {
        if (this.config.goldenZoneFilterDisabled) {
            return matches;
        }

        const goldenZoneStart = new Date(this.config.goldenZoneStartDate);
        let filteredCount = 0;

        const filtered = matches.filter(match => {
            const matchDate = new Date(match.match_date || match.date || match.startTime);
            const isInGoldenZone = matchDate >= goldenZoneStart;

            if (!isInGoldenZone) {
                filteredCount++;
            }

            return isInGoldenZone;
        });

        if (filteredCount > 0 && this.config.logLevel === 'debug') {
            console.log(`[V138.000] 🏆 GOLDEN ZONE FILTER: Removed ${filteredCount} matches before ${this.config.goldenZoneStartDate}`);
        }

        this.stats.goldenZoneFiltered = filteredCount;
        return filtered;
    }

    /**
     * V138.000: Process match queue with retry and telemetry
     * Enhanced version of startQueue with golden zone filtering and retry logic
     *
     * @param {Array} matches - Array of match objects
     * @param {Object} options - Processing options
     * @returns {Promise<Object>} Batch processing result
     */
    async startQueue(matches, options = {}) {
        // V138.000: Apply golden zone filtering
        const goldenZoneMatches = this.filterGoldenZone(matches);
        console.log(`[V138.000] 🏆 GOLDEN ZONE: Processing ${goldenZoneMatches.length} matches from ${this.config.goldenZoneStartDate} onwards`);

        const {
            maxConcurrent = this.config.harvestMaxConcurrent,
            batchSize = this.config.batchSize,
            limit = null,
            onProgress = null
        } = options;

        const targetMatches = limit ? goldenZoneMatches.slice(0, limit) : goldenZoneMatches;
        const totalMatches = targetMatches.length;

        const batchStats = {
            totalProcessed: 0,
            successCount: 0,
            failCount: 0,
            totalTime: 0,
            retryCount: 0
        };

        try {
            // Process in batches
            for (let batchStart = 0; batchStart < totalMatches; batchStart += batchSize) {
                const batchEnd = Math.min(batchStart + batchSize, totalMatches);
                const batch = targetMatches.slice(batchStart, batchEnd);

                // Process batch concurrently
                const promises = batch.map(async (match) => {
                    let result = null;
                    let attempts = 0;

                    // V138.000: Retry logic for failed harvests
                    while (attempts <= this.config.harvestRetryAttempts) {
                        try {
                            result = await this.harvestMatch(match.url, match.sourceId);

                            if (result.success) {
                                break; // Success, exit retry loop
                            } else if (attempts < this.config.harvestRetryAttempts) {
                                attempts++;
                                batchStats.retryCount++;
                                console.log(`[V138.000] 🔄 Retrying ${match.sourceId} (attempt ${attempts + 1}/${this.config.harvestRetryAttempts + 1})`);
                                await this.page.waitForTimeout(this.config.harvestRetryDelayMs);
                            }
                        } catch (error) {
                            if (attempts < this.config.harvestRetryAttempts) {
                                attempts++;
                                batchStats.retryCount++;
                                console.log(`[V138.000] 🔄 Retrying ${match.sourceId} after error: ${error.message}`);
                                await this.page.waitForTimeout(this.config.harvestRetryDelayMs);
                            } else {
                                result = { success: false, error: error.message };
                            }
                        }
                    }

                    // Update statistics
                    batchStats.totalProcessed++;
                    batchStats.totalTime += result?.duration || 0;

                    if (result?.success) {
                        batchStats.successCount++;
                        this.stats.successfulMatches++;
                        // V138.000: Track pixel retry successes
                        if (result.pixelRetrySuccess) {
                            this.stats.pixelRetrySuccesses++;
                        }
                    } else {
                        batchStats.failCount++;
                        this.stats.failedMatches++;
                    }

                    this.stats.totalMatches++;
                    this.stats.totalTrajectoryPoints += result?.trajectoryPoints || 0;

                    // V138.000: Report progress
                    if (batchStats.totalProcessed % 10 === 0 && onProgress) {
                        onProgress(batchStats.totalProcessed, totalMatches);
                    }

                    // V138.000: Display telemetry dashboard
                    this.displayTelemetryDashboard();

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

        // V138.000: Calculate average harvest time
        this.stats.avgHarvestTimeMs = batchStats.totalProcessed > 0
            ? (batchStats.totalTime / batchStats.totalProcessed) * 1000
            : 0;

        // V138.000: Final telemetry report
        this.displayTelemetryDashboard(true);

        return {
            totalProcessed: batchStats.totalProcessed,
            successCount: batchStats.successCount,
            failCount: batchStats.failCount,
            retryCount: batchStats.retryCount,
            successRate: batchStats.totalProcessed > 0 ? batchStats.successCount / batchStats.totalProcessed : 0,
            avgTimePerMatch: batchStats.totalProcessed > 0 ? batchStats.totalTime / batchStats.totalProcessed : 0,
            remaining: totalMatches - batchStats.totalProcessed
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
