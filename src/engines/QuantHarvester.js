/**
 * QuantHarvester - V141.000 Slender Commander (Refactored)
 * ==================================================================
 *
 * Standard production engine for extracting multi-dimensional quantitative data
 * trajectories from OddsPortal using Playwright automation.
 *
 * V141.000 Refactoring:
 * - Extracted TelemetryService for metrics tracking
 * - Extracted SurgicalInteraction for overlay handling and hover operations
 * - Extracted SignalRadar for network traffic monitoring
 * - Reduced from 1608 lines to ~400 lines
 *
 * V138.000 Features (Retained):
 * - Golden Zone: 2024-2026 high-yield match filtering
 * - Proxy rotation support
 *
 * @module QuantHarvester
 * @version V141.000
 * @since 2026-01-27
 * @author Senior Lead Software Architect (Refactoring Specialist)
 */

'use strict';

const { chromium } = require('playwright');
const {
    createConnection,
    getOrCreateEntity,
    upsertTemporalRecords,
    StorageError
} = require('../../scripts/ops/modules/storage');
const { TrajectoryParser, SyncTimestamp, alignTimestamp } = require('./parsers/TrajectoryParser');
const { OddsPortalSelectors } = require('./selectors/OddsPortalSelectors');
// V141.000: Import extracted services
const { TelemetryService } = require('./services/TelemetryService');
const { SurgicalInteraction } = require('./services/SurgicalInteraction');
const { SignalRadar } = require('./services/SignalRadar');
// V146.000: Import React SPA index configuration
const {
    AXIS_INDEX_OFFSETS,
    CELLS_PER_ROW,
    getIndexOffset,
    validateRowStructure
} = require('./config/ReactIndexConfig');

// ============================================================================
// MARKET VENUE WHITELIST (V133.000)
// ============================================================================

/**
 * Whitelist of high-quality bookmakers for trajectory extraction
 */
const MARKET_VENUE_WHITELIST = {
    PINNACLE: { id: 'Entity_P', name: 'Pinnacle', priority: 1 },
    BET365: { id: 'Entity_B365', name: 'bet365', priority: 2 },
    BETWAY: { id: 'Entity_BW', name: 'Betway', priority: 3 },
    WILLIAM_HILL: { id: 'Entity_WH', name: 'William Hill', priority: 4 },
    UNIBET: { id: 'Entity_UH', name: 'Unibet', priority: 5 }
};

// ============================================================================
// CONFIGURATION (Environment-First, Zero Hardcoding)
// ============================================================================

const DEFAULT_CONFIG = {
    // Browser settings
    userAgent: process.env.BROWSER_USER_AGENT || 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    viewport: {
        width: parseInt(process.env.BROWSER_VIEWPORT_WIDTH) || 1920,
        height: parseInt(process.env.BROWSER_VIEWPORT_HEIGHT) || 1080
    },
    timeout: parseInt(process.env.BROWSER_TIMEOUT) || 60000,
    headless: process.env.HEADLESS_MODE !== 'false',
    disableImages: process.env.DISABLE_IMAGES === 'true',

    // Concurrency settings
    maxConcurrent: parseInt(process.env.CONCURRENT_THREADS) || 10,
    batchSize: parseInt(process.env.BATCH_SIZE) || 50,

    // Data processing
    axes: ['home', 'draw', 'away'],
    axisDimensions: { home: 'A', draw: 'B', away: 'C' },
    currentYear: new Date().getFullYear(),

    // Database settings
    dbHost: process.env.DB_HOST || 'localhost',
    dbPort: parseInt(process.env.DB_PORT) || 5432,
    dbName: process.env.DB_NAME || 'football_db',
    dbUser: process.env.DB_USER || 'football_user',
    dbPassword: process.env.DB_PASSWORD || '',

    // Logging
    logLevel: process.env.LOG_LEVEL || 'info',

    // Stealth Mode
    waitBaseMs: parseInt(process.env.WAIT_BASE_MS) || 2000,
    waitJitterMs: parseInt(process.env.WAIT_JITTER_MS) || 1500,

    // V141.000: Module configurations
    signalWaitTimeout: parseInt(process.env.SIGNAL_WAIT_TIMEOUT) || 15000,
    adaptiveSignalTimeout: parseInt(process.env.ADAPTIVE_SIGNAL_TIMEOUT) || 5000,
    forceRemoveOverlays: process.env.FORCE_REMOVE_OVERLAYS === 'true',
    scrollIntoViewBeforeHover: process.env.SCROLL_INTO_VIEW_BEFORE_HOVER === 'true',
    hoverStabilizeMs: parseInt(process.env.HOVER_STABILIZE_MS) || 1500,
    modalRetryCount: parseInt(process.env.MODAL_RETRY_COUNT) || 2,

    // Telemetry
    telemetryEnabled: process.env.TELEMETRY_DASHBOARD_ENABLED === 'true',
    telemetryReportInterval: parseInt(process.env.TELEMETRY_REPORT_INTERVAL) || 20,

    // Golden Zone
    goldenZoneStartDate: process.env.GOLDEN_ZONE_START_DATE || '2024-01-01',
    goldenZoneFilterDisabled: process.env.GOLDEN_ZONE_FILTER_DISABLED === 'false',

    // Proxy
    enableProxyRotation: process.env.ENABLE_PROXY_ROTATION === 'true',
    proxyHost: process.env.PROXY_HOST || '172.25.16.1',
    proxyPortStart: parseInt(process.env.PROXY_PORT_START) || 7891,
    proxyPortEnd: parseInt(process.env.PROXY_PORT_END) || 7913,
    proxyScanTimeout: parseInt(process.env.PROXY_SCAN_TIMEOUT) || 500,
    proxyProtocol: process.env.PROXY_PROTOCOL || 'http',

    // Harvest retry
    harvestMaxConcurrent: parseInt(process.env.HARVEST_MAX_CONCURRENT) || 15,
    harvestRetryAttempts: parseInt(process.env.HARVEST_RETRY_ATTEMPTS) || 2,
    harvestRetryDelayMs: parseInt(process.env.HARVEST_RETRY_DELAY_MS) || 5000
};

// ============================================================================
// ERROR CLASS
// ============================================================================

class QuantHarvesterError extends Error {
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
// PROXY POOL MANAGER (V129.000)
// ============================================================================

class ProxyPoolManager {
    constructor(config) {
        this.config = config;
        this.proxies = [];
        this.currentIndex = 0;
    }

    async discoverProxies() {
        const discovered = [];
        for (let port = this.config.proxyPortStart; port <= this.config.proxyPortEnd; port++) {
            const isAlive = await this.probePort(this.config.proxyHost, port);
            if (isAlive) discovered.push(`${this.config.proxyHost}:${port}`);
        }
        this.proxies = discovered.map((server, idx) => ({ id: `proxy-${idx}`, server }));
        return discovered.length;
    }

    async probePort(host, port) {
        try {
            const net = require('net');
            return new Promise(resolve => {
                const socket = net.createConnection({ host, port, timeout: this.config.scanTimeout });
                socket.on('connect', () => {
                    socket.destroy();
                    resolve(true);
                });
                socket.on('error', () => resolve(false));
                socket.on('timeout', () => {
                    socket.destroy();
                    resolve(false);
                });
            });
        } catch {
            return false;
        }
    }

    isEnabled() {
        return this.proxies.length > 0;
    }

    getNextProxy() {
        if (this.proxies.length === 0) return null;
        const proxy = this.proxies[this.currentIndex];
        this.currentIndex = (this.currentIndex + 1) % this.proxies.length;
        return proxy;
    }

    reportSuccess(proxyId) {
        // Circuit breaker: track success rate
    }

    reportFailure(proxyId) {
        // Circuit breaker: track failures
    }
}

// ============================================================================
// MAIN QUANT HARVESTER CLASS (V141.000)
// ============================================================================

class QuantHarvester {
    static #instance = null;

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

        // V141.000: Initialize services
        this.telemetryService = new TelemetryService({
            telemetryEnabled: this.config.telemetryEnabled,
            telemetryReportInterval: this.config.telemetryReportInterval
        });

        // V141.000: Services will be initialized in init() when page is available
        this.surgicalInteraction = null;
        this.signalRadar = null;

        // Config logging
        console.log('[V141.000] ========== SLENDER COMMANDER ==========');
        console.log('[V141.000] Modular Architecture: ENABLED');
        console.log('[V141.000] Services: TelemetryService, SurgicalInteraction, SignalRadar');
        console.log('[V141.000] ===============================================');

        // Proxy pool
        this.proxyPool = new ProxyPoolManager({
            proxyHost: this.config.proxyHost,
            proxyPortStart: this.config.proxyPortStart,
            proxyPortEnd: this.config.proxyPortEnd,
            scanTimeout: this.config.proxyScanTimeout,
            protocol: this.config.proxyProtocol
        });

        QuantHarvester.#instance = this;
    }

    static getInstance(config) {
        if (!QuantHarvester.#instance) {
            QuantHarvester.#instance = new QuantHarvester(config);
        }
        return QuantHarvester.#instance;
    }

    async init() {
        if (this.isInitialized) return;

        try {
            // Connect to database
            this.dbClient = await createConnection();

            // Auto-discover proxies
            if (this.config.enableProxyRotation) {
                const discovered = await this.proxyPool.discoverProxies();
                console.log(`[V129.000] Proxy discovery: ${discovered} nodes found`);
            }

            // Launch browser
            this.browser = await chromium.launch({
                headless: this.config.headless,
                args: ['--disable-blink-features=AutomationControlled']
            });

            // Context config
            const contextConfig = {
                userAgent: this.config.userAgent,
                viewport: this.config.viewport
            };

            // Inject proxy
            this.currentProxyId = null;
            if (this.config.enableProxyRotation && this.proxyPool.isEnabled()) {
                const proxy = this.proxyPool.getNextProxy();
                if (proxy) {
                    contextConfig.proxy = proxy;
                    this.currentProxyId = proxy.id;
                }
            }

            this.context = await this.browser.newContext(contextConfig);
            this.page = await this.context.newPage();

            // V141.000: Initialize services with page
            this.surgicalInteraction = new SurgicalInteraction(this.page, {
                forceRemoveOverlays: this.config.forceRemoveOverlays,
                scrollIntoViewBeforeHover: this.config.scrollIntoViewBeforeHover,
                hoverStabilizeMs: this.config.hoverStabilizeMs,
                modalRetryCount: this.config.modalRetryCount,
                logLevel: this.config.logLevel
            });

            this.signalRadar = new SignalRadar(this.page, {
                signalWaitTimeout: this.config.signalWaitTimeout,
                adaptiveSignalTimeout: this.config.adaptiveSignalTimeout,
                logLevel: this.config.logLevel
            });

            // Disable images if configured
            if (this.config.disableImages) {
                await this.page.route('**/*.{png,jpg,jpeg,gif,svg,webp}', route => route.abort());
            }

            this.isInitialized = true;

        } catch (error) {
            throw new QuantHarvesterError('INIT_FAILED', `Failed to initialize: ${error.message}`);
        }
    }

    /**
     * V127.000: Randomized jitter wait
     */
    async jitterWait(baseMs = null, rangeMs = null) {
        const base = baseMs ?? this.config.waitBaseMs;
        const range = rangeMs ?? this.config.waitJitterMs;
        const delay = base + Math.random() * range;
        await this.page.waitForTimeout(delay);
    }

    /**
     * Harvest trajectory data from a single match URL
     */
    async harvestMatch(url, sourceId) {
        if (!this.isInitialized) await this.init();

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

            // V141.000: Use SurgicalInteraction for overlay handling
            await this.surgicalInteraction.handleOverlays();

            // V146.000: Wait for React async rendering (NEW for SPA architecture)
            await this.surgicalInteraction.waitForReactRender();

            // V141.000: Use SignalRadar for signal detection
            const signalResult = await this.signalRadar.waitForTrajectorySignal();
            if (this.config.logLevel === 'debug') {
                console.log(`[V141.000] Signal status: ${signalResult.method}`);
            }

            // Wait for odds content
            await this.signalRadar.waitForOddsContent(30);

            // Get or create entity
            result.entityId = await getOrCreateEntity(this.dbClient, {
                sourceSystem: 'oddsportal',
                sourceId: sourceId,
                entityType: 'match',
                entityName: `Match ${sourceId}`
            });

            // Find whitelisted bookmakers
            const bookmakerRows = await this.page.$$('ul.visible-links.bg-black-main.odds-tabs > li');
            const whitelistedProviders = new Map();

            for (const row of bookmakerRows) {
                try {
                    const nameElement = await row.$('div[class*="text-"]');
                    if (!nameElement) continue;

                    const name = await nameElement.textContent();
                    const venueKey = Object.keys(MARKET_VENUE_WHITELIST).find(
                        key => name.toLowerCase().includes(MARKET_VENUE_WHITELIST[key].name.toLowerCase())
                    );

                    if (venueKey) {
                        const venueId = MARKET_VENUE_WHITELIST[venueKey].id;
                        whitelistedProviders.set(venueId, {
                            element: row,
                            standardVenueId: venueId,
                            name: MARKET_VENUE_WHITELIST[venueKey].name
                        });
                    }
                } catch (e) {
                    // Continue
                }
            }

            result.providerCount = whitelistedProviders.size;

            // Extract trajectory for each axis
            const axesData = {};

            // V146.000: Get all odds cells once (React SPA architecture)
            const allOddsCells = await this.page.$$('[class*="odds-cell"]');
            const totalCells = allOddsCells.length;

            console.log(`[V146.000] 📊 React SPA Index-based Targeting`);
            console.log(`[V146.000] 📦 Total cells found: ${totalCells}`);

            // V146.000: Validate row structure
            if (!validateRowStructure(totalCells)) {
                console.log(`[V146.000] ⚠️  Row structure invalid: ${totalCells} cells (expected >= ${CELLS_PER_ROW})`);
                return result;
            }

            // V146.000: Calculate number of complete rows
            const numberOfRows = Math.floor(totalCells / CELLS_PER_ROW);
            console.log(`[V146.000] 📏 Complete rows detected: ${numberOfRows}`);

            for (const axisName of this.config.axes) {
                try {
                    const dimension = this.config.axisDimensions[axisName];
                    const indexOffset = getIndexOffset(axisName);

                    // Debug: log axis lookup
                    if (this.config.logLevel === 'debug') {
                        console.log(`[V146.000] 🔍 Axis lookup: ${axisName} -> offset=${indexOffset}, dim=${dimension}`);
                    }

                    if (indexOffset === null) {
                        console.log(`[V146.000] ⚠️  Unknown axis: ${axisName}`);
                        console.log(`[V146.000] 🔍 Available offsets:`, JSON.stringify(AXIS_INDEX_OFFSETS));
                        continue;
                    }

                    // V146.000: Collect cells for this axis using index-based mapping
                    const oddsCells = [];
                    for (let row = 0; row < numberOfRows; row++) {
                        const cellIndex = row * CELLS_PER_ROW + indexOffset;
                        if (cellIndex < totalCells) {
                            oddsCells.push(allOddsCells[cellIndex]);
                        }
                    }

                    console.log(`[V146.000] 🎯 Axis ${axisName} (offset ${indexOffset}): ${oddsCells.length} cells`);

                    if (oddsCells.length === 0) continue;

                    for (let i = 0; i < oddsCells.length; i++) {
                        const cell = oddsCells[i];

                        try {
                            // V141.000: Use SurgicalInteraction for reliable hover
                            const hoverResult = await this.surgicalInteraction.performReliableHover(
                                cell, i, axisName, oddsCells.length
                            );

                            // V148.000: Check for modal using TARGET REDIRECTED selector
                            // Based on V147 competitive analysis, we look for "Odds movement" title
                            // Note: Can't use Playwright pseudo-selectors in page.evaluate()
                            const modalExists = await this.page.evaluate(() => {
                                // Look for the "Odds movement" heading using native DOM methods
                                const h3Elements = document.querySelectorAll('h3');
                                let titleElement = null;
                                for (const h3 of h3Elements) {
                                    if (h3.textContent && h3.textContent.includes('Odds movement')) {
                                        titleElement = h3;
                                        break;
                                    }
                                }

                                if (!titleElement) return false;

                                // V149.000: Traverse up to find the modal container (.tooltip is the actual container)
                                const modal = titleElement.closest('.tooltip, [role="dialog"], .modal-content, [class*="popup"]');

                                return modal && modal.offsetParent !== null;
                            });

                            if (modalExists) {
                                let modalHtml = null;
                                try {
                                    // V148.000: Capture the modal HTML using native DOM methods
                                    modalHtml = await this.page.evaluate(() => {
                                        // Find the title using text content
                                        const h3Elements = document.querySelectorAll('h3');
                                        let titleElement = null;
                                        for (const h3 of h3Elements) {
                                            if (h3.textContent && h3.textContent.includes('Odds movement')) {
                                                titleElement = h3;
                                                break;
                                            }
                                        }

                                        if (!titleElement) return null;

                                        // Get the modal container
                                        const modal = titleElement.closest('[role="dialog"], .modal-content, [class*="popup"]');

                                        return modal ? modal.outerHTML : null;
                                    });
                                } catch (e) {
                                    // Ignore
                                }

                                if (modalHtml) {
                                    const extractionResult = this.trajectoryParser.extractFullTrajectoryDOM(modalHtml);
                                    const trajectory = extractionResult.trajectory || [];

                                    if (trajectory.length >= 1) {
                                        axesData[axisName] = {
                                            axis: axisName,
                                            dimension: dimension,
                                            standardVenueId: whitelistedProviders.values().next().value.standardVenueId,
                                            trajectory: trajectory,
                                            success: true,
                                            quality: extractionResult.quality
                                        };

                                        result.trajectoryPoints += trajectory.length;
                                    }
                                }

                                await this.page.mouse.move(0, 0);
                                await this.jitterWait(500, 300);
                            }

                        } catch (e) {
                            // Continue
                        }
                    }

                } catch (e) {
                    // Continue
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
                                venueId: axisData.standardVenueId
                            }
                        });
                    }
                }
            }

            // Persist to database
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

        // V141.000: Update telemetry
        this.telemetryService.updateStats(result);

        return result;
    }

    /**
     * V138.000: Golden Zone Filter
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

            if (!isInGoldenZone) filteredCount++;

            return isInGoldenZone;
        });

        if (filteredCount > 0 && this.config.logLevel === 'debug') {
            console.log(`[V138.000] 🏆 GOLDEN ZONE FILTER: Removed ${filteredCount} matches`);
        }

        this.telemetryService.setMetric('goldenZoneFiltered', filteredCount);
        return filtered;
    }

    /**
     * V138.000: Process match queue with retry
     */
    async startQueue(matches, options = {}) {
        const goldenZoneMatches = this.filterGoldenZone(matches);
        console.log(`[V138.000] 🏆 GOLDEN ZONE: Processing ${goldenZoneMatches.length} matches`);

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
            for (let batchStart = 0; batchStart < totalMatches; batchStart += batchSize) {
                const batchEnd = Math.min(batchStart + batchSize, totalMatches);
                const batch = targetMatches.slice(batchStart, batchEnd);

                const promises = batch.map(async (match) => {
                    let result = null;
                    let attempts = 0;

                    while (attempts <= this.config.harvestRetryAttempts) {
                        try {
                            result = await this.harvestMatch(match.url, match.sourceId);

                            if (result.success) break;
                            else if (attempts < this.config.harvestRetryAttempts) {
                                attempts++;
                                batchStats.retryCount++;
                                console.log(`[V138.000] 🔄 Retrying ${match.sourceId}`);
                                await this.page.waitForTimeout(this.config.harvestRetryDelayMs);
                            }
                        } catch (error) {
                            if (attempts < this.config.harvestRetryAttempts) {
                                attempts++;
                                batchStats.retryCount++;
                                await this.page.waitForTimeout(this.config.harvestRetryDelayMs);
                            } else {
                                result = { success: false, error: error.message };
                            }
                        }
                    }

                    batchStats.totalProcessed++;
                    batchStats.totalTime += result?.duration || 0;

                    if (result?.success) {
                        batchStats.successCount++;
                    } else {
                        batchStats.failCount++;
                    }

                    // V141.000: Display telemetry
                    this.telemetryService.displayTelemetryDashboard();

                    if (onProgress && batchStats.totalProcessed % 10 === 0) {
                        onProgress(batchStats.totalProcessed, totalMatches);
                    }

                    return result;
                });

                await Promise.all(promises);
            }

            this.telemetryService.setMetric('avgHarvestTimeMs',
                this.telemetryService.calculateAvgHarvestTime(batchStats.totalTime, batchStats.totalProcessed));

            this.telemetryService.displayTelemetryDashboard(true);

            return {
                totalProcessed: batchStats.totalProcessed,
                successCount: batchStats.successCount,
                failCount: batchStats.failCount,
                retryCount: batchStats.retryCount,
                successRate: batchStats.totalProcessed > 0 ? batchStats.successCount / batchStats.totalProcessed : 0,
                avgTimePerMatch: batchStats.totalProcessed > 0 ? batchStats.totalTime / batchStats.totalProcessed : 0,
                remaining: totalMatches - batchStats.totalProcessed
            };

        } catch (error) {
            throw new QuantHarvesterError('QUEUE_FAILED', `Queue processing failed: ${error.message}`);
        }
    }

    /**
     * V149.000: Diagnostic Method - Capture Modal HTML
     *
     * Captures the actual modal HTML for diagnostic purposes.
     * This method is used by v149_000_diagnostic.js to investigate
     * why TrajectoryParser returns 0 points despite successful modal detection.
     *
     * @param {string} url - OddsPortal match URL
     * @returns {Promise<string|null>} Modal HTML or null if not found
     */
    async _captureModalForDiagnostic(url) {
        let tempBrowser = null;
        let tempContext = null;
        let tempPage = null;

        try {
            // Initialize browser if not already initialized
            if (!this.isInitialized) {
                await this.init();
            }

            // Navigate to URL
            console.log(`[V149.000] 📍 Navigating to: ${url}`);
            await this.page.goto(url, { waitUntil: 'networkidle', timeout: this.config.timeout });

            // Wait for React rendering
            await this.surgicalInteraction.waitForReactRender();

            // V149.000: Remove overlays (Cookie banners, etc.)
            console.log('[V149.000] 🧹 Removing overlays...');
            await this.surgicalInteraction.handleOverlays();

            // Find first odds cell
            const oddsCells = await this.page.$$('.odds-cell');
            if (oddsCells.length === 0) {
                console.log('[V149.000] ⚠️  No odds cells found');
                return null;
            }

            console.log(`[V149.000] 🎯 Found ${oddsCells.length} odds cells, hovering on first...`);

            // Perform hover on first cell
            const cell = oddsCells[0];

            // Scroll into view if needed
            if (this.config.scrollIntoViewBeforeHover) {
                await cell.scrollIntoViewIfNeeded();
                await this.surgicalInteraction.scrollSettle();
            }

            // Get bounding box for hover
            const boundingBox = await cell.boundingBox();
            if (!boundingBox) {
                console.log('[V149.000] ⚠️  Could not get bounding box');
                return null;
            }

            // Calculate hover position (center with jitter)
            const jitter = this.surgicalInteraction.generatePixelJitter();
            const centerX = boundingBox.x + boundingBox.width / 2;
            const centerY = boundingBox.y + boundingBox.height / 2;
            const hoverX = centerX + jitter.offsetX;
            const hoverY = centerY + jitter.offsetY;

            // Perform hover
            await this.page.mouse.move(hoverX, hoverY);
            console.log(`[V149.000] 🎯 Hovered at (${hoverX.toFixed(1)}, ${hoverY.toFixed(1)})`);

            // Wait for random stabilization
            await this.surgicalInteraction.randomStabilize();

            // V149.000: Additional wait for modal to appear (React async rendering)
            console.log('[V149.000] ⏳ Waiting 3s for modal to appear...');
            await this.page.waitForTimeout(3000);

            // Detect and capture modal
            console.log('[V149.000] 🔍 Looking for modal...');
            const diagnosticInfo = await this.page.evaluate(() => {
                const result = {
                    h3Count: 0,
                    h3Texts: [],
                    dialogCount: 0,
                    popupCount: 0,
                    modalContentCount: 0,
                    fixedCount: 0,
                    tooltipCount: 0,
                    maxContentCount: 0,
                    foundTitle: false,
                    foundModal: false,
                    modalHtml: null,
                    parentChain: []
                };

                // Count all h3 elements
                const h3Elements = document.querySelectorAll('h3');
                result.h3Count = h3Elements.length;
                h3Elements.forEach((h3, idx) => {
                    result.h3Texts.push(`h3[${idx}]: "${h3.textContent?.trim().substring(0, 50)}"`);
                });

                // Count potential modal containers
                result.dialogCount = document.querySelectorAll('[role="dialog"]').length;
                result.popupCount = document.querySelectorAll('[class*="popup"]').length;
                result.modalContentCount = document.querySelectorAll('.modal-content').length;
                result.fixedCount = document.querySelectorAll('[class*="fixed"]').length;
                result.tooltipCount = document.querySelectorAll('[class*="tooltip"]').length;
                result.maxContentCount = document.querySelectorAll('[class*="max-content"]').length;

                // Find "Odds movement" title
                let titleElement = null;
                for (const h3 of h3Elements) {
                    if (h3.textContent && h3.textContent.includes('Odds movement')) {
                        titleElement = h3;
                        result.foundTitle = true;
                        console.log('[V149.000] ✅ Found "Odds movement" title');
                        break;
                    }
                }

                if (!titleElement) {
                    console.log('[V149.000] ❌ "Odds movement" title not found');
                    console.log('[V149.000] Available h3 texts:', result.h3Texts.join('\n'));
                    return result;
                }

                // V149.000: Capture parent chain to understand DOM structure
                let parent = titleElement.parentElement;
                let depth = 0;
                while (parent && depth < 15) {
                    const tagInfo = parent.tagName?.toLowerCase() || 'unknown';
                    const idInfo = parent.id ? `#${parent.id}` : '';
                    const classInfo = parent.className ? `.${parent.className.split(' ')[0]}` : '';
                    const roleInfo = parent.getAttribute('role') ? `[role="${parent.getAttribute('role')}"]` : '';

                    result.parentChain.push({
                        depth,
                        tag: tagInfo,
                        id: parent.id || '',
                        class: parent.className || '',
                        role: parent.getAttribute('role') || '',
                        selector: tagInfo + idInfo + classInfo + roleInfo
                    });

                    // Try to find modal-like container at each level
                    if (parent.getAttribute('role') === 'dialog' ||
                        parent.classList.contains('modal-content') ||
                        Array.from(parent.classList).some(c => c.includes('popup')) ||
                        Array.from(parent.classList).some(c => c.includes('fixed')) ||
                        Array.from(parent.classList).some(c => c.includes('tooltip'))) {
                        console.log(`[V149.000] ✅ Found potential modal at depth ${depth}:`, result.parentChain[result.parentChain.length - 1].selector);
                        result.foundModal = true;
                        result.modalHtml = parent.outerHTML;
                        break;
                    }

                    parent = parent.parentElement;
                    depth++;
                }

                // If still not found, get the entire parent chain as HTML
                if (!result.modalHtml && titleElement.parentElement) {
                    console.log('[V149.000] ⚠️  No modal container found, capturing parent tree...');
                    // Get a reasonable chunk of HTML (5 levels up)
                    let htmlChunk = titleElement.outerHTML;
                    let p = titleElement.parentElement;
                    for (let i = 0; i < 5 && p; i++) {
                        htmlChunk = p.outerHTML;
                        p = p.parentElement;
                    }
                    result.modalHtml = htmlChunk;
                }

                return result;
            });

            console.log('[V149.000] 📊 Diagnostic info:');
            console.log(`  - h3 elements: ${diagnosticInfo.h3Count}`);
            console.log(`  - [role="dialog"]: ${diagnosticInfo.dialogCount}`);
            console.log(`  - [class*="popup"]: ${diagnosticInfo.popupCount}`);
            console.log(`  - .modal-content: ${diagnosticInfo.modalContentCount}`);
            console.log(`  - [class*="fixed"]: ${diagnosticInfo.fixedCount}`);
            console.log(`  - [class*="tooltip"]: ${diagnosticInfo.tooltipCount}`);
            console.log(`  - [class*="max-content"]: ${diagnosticInfo.maxContentCount}`);
            console.log(`  - Found title: ${diagnosticInfo.foundTitle}`);
            console.log(`  - Found modal: ${diagnosticInfo.foundModal}`);

            if (diagnosticInfo.parentChain.length > 0) {
                console.log('[V149.000] Parent chain of "Odds movement" h3:');
                diagnosticInfo.parentChain.slice(0, 8).forEach(p => {
                    console.log(`  [${p.depth}] ${p.selector}`);
                });
            }

            if (diagnosticInfo.h3Texts.length > 0 && !diagnosticInfo.foundTitle) {
                console.log('[V149.000] Available h3 elements:');
                diagnosticInfo.h3Texts.slice(0, 5).forEach(t => console.log('  - ' + t));
            }

            const modalHtml = diagnosticInfo.modalHtml;
            if (modalHtml) {
                console.log(`[V149.000] ✅ Captured ${modalHtml.length} chars of modal HTML`);
            } else {
                console.log('[V149.000] ❌ Failed to capture modal HTML');
            }

            return modalHtml;

        } catch (error) {
            console.error(`[V149.000] ❌ Error capturing modal: ${error.message}`);
            return null;
        } finally {
            // Move mouse away to dismiss modal
            if (this.page) {
                await this.page.mouse.move(0, 0);
                await this.jitterWait(500, 300);
            }
        }
    }

    /**
     * Shutdown the harvester
     */
    async shutdown() {
        try {
            if (this.page) await this.page.close();
            if (this.context) await this.context.close();
            if (this.browser) await this.browser.close();
            if (this.dbClient) await this.dbClient.end();

            this.isInitialized = false;

        } catch (error) {
            throw new QuantHarvesterError('SHUTDOWN_FAILED', `Failed to shutdown: ${error.message}`);
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
