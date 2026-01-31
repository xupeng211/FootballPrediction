/**
 * V108.000 Main Entry Point - Pipeline Integration
 * ================================================
 *
 * V108.000: 多维动态数据同步与主流程模块化集成
 *   - 路由判断: 联赛页 → 静态批量扫描，详情页 → 动态交互提取
 *   - V108.000 Multi-Axis Hover: Home/Draw/Away 三轴独立提取
 *   - Promise.race 竞速模型: 毫秒级响应优化
 *   - 并发约束: MAX_CONCURRENT=10 (交互式页面)
 *
 * @version V108.000
 * @since 2026-01-27
 */

'use strict';

const { chromium } = require('playwright');
const { CONFIG, log } = require('./v91_000_config');
const { ComponentMonitor } = require('./v91_000_monitor_service');
const { ParserEngine } = require('./v91_000_parser_engine');
const storage = require('./modules/storage');
// V108.000: Import multi-axis hover engine
const { extractMultiAxisFromRow } = require('./v107_000_hover_modal_engine');

// ============================================================================
// CIRCUIT BREAKER - V92.000
// ============================================================================

class CircuitBreaker {
    constructor(threshold = 2) {
        this.failureCount = 0;
        this.successCount = 0;
        this.threshold = threshold;
        this.isDegraded = false;
    }

    recordFailure() {
        this.failureCount++;
        if (this.failureCount >= this.threshold) this.isDegraded = true;
    }

    recordSuccess() {
        this.successCount++;
        if (this.failureCount > 0) this.failureCount--;
        if (this.failureCount === 0) this.isDegraded = false;
    }

    getStatus() {
        return { isDegraded: this.isDegraded, failureCount: this.failureCount, successCount: this.successCount };
    }
}

// ============================================================================
// MAIN HARVESTER - V108.000
// ============================================================================

/**
 * V108.000: Main Harvester - Pipeline Integration with Multi-Axis Support
 * V108.000: Enhanced with dynamic hover extraction for detail pages
 */
class MainHarvester {
    constructor() {
        this.browser = null;
        this.storage = null;
        this.circuitBreaker = new CircuitBreaker();
        this.metricRecords = [];
        this.totalPoints = 0;
        this.totalDBDelta = 0;
        this.contextPool = [];
        this.contextPoolSize = CONFIG.concurrency.maxConcurrent;
        this.urlsProcessed = 0;
        this.urlsSuccess = 0;
        this.urlsFailed = 0;
        // V101.000: Opening odds statistics
        this.openingOddsStats = {
            totalRecords: 0,
            openingOddsFound: 0,
            historyCaptureRate: 0
        };
        // V104.000: Movement audit statistics
        this.movementAudit = {
            totalMovements: 0,
            movementsByVendor: {},
            movementsBySource: {
                'data-attr': 0,
                'title-regex': 0,
                'current-fallback': 0
            }
        };
        // V108.000: Multi-axis extraction statistics
        this.multiAxisStats = {
            detailPagesProcessed: 0,
            leaguePagesProcessed: 0,
            totalAxesCaptured: 0,
            totalInitValues: 0,
            avgAxesPerProvider: 0
        };
    }

    async initialize() {
        log.info('[V104.000] Initializing harvester with STEALTH MODE...');

        // V104.000: Professional-grade stealth mode
        // 1. Remove --enable-automation flag (bypasses Playwright detection)
        // 2. Inject real Chrome User Agent
        const launchOptions = {
            ...CONFIG.browser,
            // V104.000: CRITICAL - ignoreDefaultArgs to remove --enable-automation
            ignoreDefaultArgs: CONFIG.browser.ignoreDefaultArgs || ['--enable-automation']
        };

        this.browser = await chromium.launch(launchOptions);
        this.storage = storage;
        this.dbPool = await this.storage.createPool();

        for (let i = 0; i < this.contextPoolSize; i++) {
            // V104.000: Apply User Agent to each context
            const contextOptions = {
                ...CONFIG.browser,
                userAgent: CONFIG.browser.userAgent || CONFIG.browser.args?.find(arg => arg.includes('User-Agent')) || 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
            };
            const context = await this.browser.newContext(contextOptions);
            this.contextPool.push(context);
        }

        log.success(`[V104.000] Harvester initialized with ${this.contextPoolSize} browser contexts (STEALTH MODE ACTIVE)`);
    }

    async getContext(workerId) {
        const index = workerId % this.contextPoolSize;
        return this.contextPool[index];
    }

    /**
     * V104.000: Check if URL is a match detail page
     * Detail pages have format: /football/{league}/{teams}-{hash}/
     */
    isDetailPage(url) {
        // Detail pages typically have 8-digit hash at the end
        return /-\d{8}\//.test(url) || /\/football\/[^\/]+\/[^\/]+-[^\/]+-\d+\//.test(url);
    }

    /**
     * V108.000: Dynamic hover extraction for detail pages
     * Uses multi-axis hover engine to capture Home/Draw/Away history
     */
    async extractWithV108MultiAxis(page, entityId) {
        log.info('[V108.000] Starting multi-axis dynamic extraction...');

        const v108Result = {
            success: false,
            temporalSequence: [],
            fieldCount: 0,
            historyPoints: 0,
            openingOddsStats: { totalRecords: 0, openingOddsFound: 0, historyCaptureRate: 0 },
            movementAudit: { totalMovements: 0, movementsByVendor: {}, movementsBySource: {} }
        };

        try {
            // Find all bookmaker rows (border-black-borders)
            const bookmakerRows = await page.$$('div.border-black-borders.flex.h-9, div[class*="border"][class*="flex"][class*="h-9"]');
            log.info(`[V108.000] Found ${bookmakerRows.length} bookmaker rows`);

            if (bookmakerRows.length === 0) {
                log.warn('[V108.000] No bookmaker rows found');
                return v108Result;
            }

            // Process each row with multi-axis hover
            const maxProviders = Math.min(bookmakerRows.length, 10);
            let totalInitValues = 0;
            let totalAxesCaptured = 0;

            for (let i = 0; i < maxProviders; i++) {
                log.info(`[V108.000] Processing provider ${i + 1}/${maxProviders}...`);

                try {
                    const multiAxisResult = await extractMultiAxisFromRow(page, bookmakerRows[i], i);

                    if (multiAxisResult.success) {
                        // Count init values and axes
                        const axes = ['axis_1', 'axis_2', 'axis_3'];
                        const dimensions = ['home', 'draw', 'away'];

                        axes.forEach((axisKey, idx) => {
                            const axisData = multiAxisResult[axisKey];
                            if (axisData.init !== null || axisData.history.length > 0) {
                                totalAxesCaptured++;
                                if (axisData.init !== null) {
                                    totalInitValues++;
                                }
                            }

                            // Convert to temporal sequence format
                            if (axisData.history.length > 0) {
                                axisData.history.forEach((point, pointIdx) => {
                                    v108Result.temporalSequence.push({
                                        vendor: multiAxisResult.provider || `Provider_${i}`,
                                        metricType: dimensions[idx],
                                        value: point.home || point.value,
                                        metricTime: new Date(point.time).toISOString() || new Date().toISOString(),
                                        isMoved: pointIdx > 0,
                                        openingOdds: axisData.init,
                                        closingOdds: point.home || point.value
                                    });
                                });

                                v108Result.historyPoints += axisData.history.length;
                            }
                        });

                        log.success(`[V108.000] Provider ${i + 1} extracted: ${multiAxisResult.provider}`);
                    }
                } catch (e) {
                    log.error(`[V108.000] Error processing provider ${i + 1}: ${e.message}`);
                }

                // Wait between providers
                if (i < maxProviders - 1) {
                    await page.waitForTimeout(1500);
                }
            }

            // Update statistics
            v108Result.fieldCount = v108Result.temporalSequence.length;
            v108Result.success = v108Result.temporalSequence.length > 0;

            // V108.000: Update multi-axis stats
            this.multiAxisStats.detailPagesProcessed++;
            this.multiAxisStats.totalAxesCaptured += totalAxesCaptured;
            this.multiAxisStats.totalInitValues += totalInitValues;
            this.multiAxisStats.avgAxesPerProvider =
                this.multiAxisStats.detailPagesProcessed > 0
                    ? (this.multiAxisStats.totalAxesCaptured / this.multiAxisStats.detailPagesProcessed).toFixed(2)
                    : 0;

            // Update opening odds stats
            v108Result.openingOddsStats.totalRecords = maxProviders;
            v108Result.openingOddsStats.openingOddsFound = totalInitValues;
            v108Result.openingOddsStats.historyCaptureRate =
                maxProviders > 0 ? ((totalInitValues / (maxProviders * 3)) * 100).toFixed(2) : 0;

            log.success(`[V108.000] Multi-axis extraction complete:`);
            log.success(`  Axes captured: ${totalAxesCaptured}`);
            log.success(`  Init values: ${totalInitValues}`);
            log.success(`  History points: ${v108Result.historyPoints}`);
            log.success(`  Temporal records: ${v108Result.temporalSequence.length}`);

        } catch (error) {
            log.error(`[V108.000] Dynamic extraction failed: ${error.message}`);
        }

        return v108Result;
    }

    /**
     * V104.000: Process URL with detail page detection and tab activation
     */
    async processUrl(url, index, total, workerId = 0) {
        log.info(`\n=== Processing URL ${index + 1}/${total}: ${url} ===`);

        // V104.000: Detect if this is a detail page
        const isDetailPage = this.isDetailPage(url);
        log.info(`[V104.000] Page type: ${isDetailPage ? 'DETAIL PAGE' : 'LEAGUE PAGE'}`);

        let page = null;
        let structureSnapshot = null;
        let workerContext = null;
        let urlOpeningStats = null;
        let urlMovementAudit = null;  // V104.000: Track movement audit for this URL

        try {
            workerContext = await this.getContext(workerId);
            page = await workerContext.newPage();
            const monitor = new ComponentMonitor(page, CONFIG);
            const parser = new ParserEngine(page, CONFIG);

            // Step 1: Navigate
            log.info(`[Step 1] Navigating to: ${url}`);
            const timeout = isDetailPage ? 45000 : 30000;  // V104.000: Longer timeout for detail pages
            await page.goto(url, { timeout: timeout, waitUntil: 'networkidle' });

            // V104.000: Page Content Verification - Detail Page Rendering Authorization
            log.info('[V104.000] Verifying page content...');
            try {
                // Wait for body to be visible
                await page.waitForSelector('body', { state: 'visible', timeout: 10000 });
            } catch (e) {
                log.warn('[V104.000] Body not visible, proceeding anyway...');
            }

            // Check page title for Access Denied or empty title
            const pageTitle = await page.title();
            const pageUrl = page.url();
            log.info(`[V104.000] Page title: "${pageTitle}"`);
            log.info(`[V104.000] Page URL: "${pageUrl}"`);

            // V104.000: Detect access denied or suspicious titles
            if (pageTitle.includes('Access Denied') || pageTitle.includes('access denied') ||
                pageTitle.includes('Blocked') || pageTitle.includes('blocked') ||
                pageTitle.includes('403') || pageTitle.includes('Forbidden') ||
                pageTitle.trim() === '' || pageTitle.length < 3) {
                log.error('[V104.000] ACCESS DENIED DETECTED - Forcing refresh...');
                await page.reload({ timeout: timeout, waitUntil: 'networkidle' });
                const newTitle = await page.title();
                log.info(`[V104.000] After refresh - Page title: "${newTitle}"`);
            } else {
                log.success('[V104.000] Page content verification PASSED');
            }

            // Step 2: Clean UI
            log.info('[Step 2] Cleaning UI...');
            await monitor.cleanUI();

            // Step 3: Locate target element
            log.info('[Step 3] Locating target element...');

            const targetElement = await page.evaluateHandle(() => {
                const navBlacklist = ['sub-nav-inactive-tab', 'nav', 'outrights', 'menu', 'tab-inactive', 'navigation', 'navbar'];

                function isNavigationElement(node) {
                    const className = (node.className || '').toString().toLowerCase();
                    const id = (node.id || '').toLowerCase();
                    const text = (node.textContent || '').trim().toLowerCase();
                    const dataTestId = (node.getAttribute ? node.getAttribute('data-testid') || '' : '').toLowerCase();

                    return navBlacklist.some(keyword => 
                        className.includes(keyword) || id.includes(keyword) || text.includes(keyword) || dataTestId.includes(keyword)
                    );
                }

                // V104.000: Enhanced RADAR selectors - attribute contains matching
                const detailPageSelectors = [
                    'div#odds-data-table',
                    '[data-id="odds-table"]',
                    'table#odds-table',
                    'div[class*="odds-table"]',
                    // V104.000: RADAR selectors
                    'div[class*="odds"]',
                    'table[class*="odds"]',
                    '[data-testid*="odds"]',
                    'section[class*="odds"]',
                    'div[id*="odds"]',
                    '[data-component*="odds"]'
                ];

                const leaguePageSelectors = [
                    'div.border-black-borders',
                    'div[class*="event-row"]',
                    'div#tournamentTable',
                    'div.main-content',
                    'div[class*="tournament"]',
                    'div[class*="odds"]'
                ];

                const allSelectors = [...detailPageSelectors, ...leaguePageSelectors];

                for (const selector of allSelectors) {
                    try {
                        const elements = document.querySelectorAll(selector);
                        for (const el of elements) {
                            if (!isNavigationElement(el)) {
                                return el;
                            }
                        }
                    } catch (e) {
                        // Invalid selector, continue
                    }
                }

                return null;
            });

            const elementHandle = await targetElement.asElement();
            const hasTargetElement = elementHandle !== null;

            if (!hasTargetElement) {
                log.warn('[Step 3] Target element not found, using body as fallback');

                // V104.000: DOM DUMPING - Capture page content for diagnostic
                log.error('[V104.000] === DOM DUMP: BLACK BOX PROBE ===');
                const domDump = await page.evaluate(() => {
                    const bodyText = document.body.innerText || '';
                    // First 5000 chars for analysis
                    const preview = bodyText.substring(0, 5000);
                    // Check for betting keywords
                    const keywords = ['1X2', 'Bookmakers', 'Odds', 'Home/Draw/Away', 'betting', 'Pinnacle', 'Bet365'];
                    const foundKeywords = keywords.filter(k => preview.toLowerCase().includes(k.toLowerCase()));
                    return {
                        preview: preview,
                        foundKeywords: foundKeywords,
                        bodyClass: document.body.className,
                        bodyId: document.body.id
                    };
                });
                log.error(`[V104.000] DOM Preview (first 5000 chars):\n${domDump.preview}`);
                log.error(`[V104.000] Found betting keywords: ${domDump.foundKeywords.join(', ') || 'NONE'}`);
                log.error(`[V104.000] Body class: ${domDump.bodyClass}, id: ${domDump.bodyId}`);
                log.error('[V104.000] === END DOM DUMP ===');

                structureSnapshot = await page.evaluate(() => ({
                    tagName: document.body.tagName,
                    className: document.body.className,
                    textContent: document.body.textContent?.substring(0, 100)
                }));
            } else {
                structureSnapshot = await monitor.structureSampling(elementHandle);
            }

            // Step 4: Triple-Tap Interaction
            log.info('[Step 4] Triple-Tap Interaction...');

            // V104.000: PHASE 0 - Tab Activation for Detail Pages
            // For detail pages, activate "Full time" or "1X2" tab FIRST before clicking
            if (isDetailPage) {
                log.info('[Step 4.0] DETAIL PAGE: Activating "Full time" / "1X2" tab...');

                // V104.000: Precision Click Anchor - Click at (0, 0) to activate page interaction listeners
                // This activates the page's JavaScript event handlers before tab activation
                log.info('[V104.000] Precision Click Anchor: Clicking (0, 0) to activate interaction listeners...');
                try {
                    await page.mouse.click(0, 0);
                    log.success('[V104.000] Precision click SUCCESS - Page interaction activated');
                    await page.waitForTimeout(500);  // Brief wait for event propagation
                } catch (e) {
                    log.warn(`[V104.000] Precision click failed: ${e.message}`);
                }

                await monitor.lockNavigation();

                // V104.000: Try text-based click first (RADAR approach)
                let tabActivated = false;
                const textSelectors = ['Odds', '1X2', 'Full Time', 'Full time', 'Home/Draw/Away'];

                for (const textSel of textSelectors) {
                    try {
                        log.info(`[V104.000] Attempting text-based click: "text=${textSel}"`);
                        await page.click(`text="${textSel}"`, { timeout: 3000 });
                        log.success(`[V104.000] Text-based click SUCCESS: "${textSel}"`);
                        tabActivated = true;
                        await page.waitForTimeout(2000);
                        break;
                    } catch (e) {
                        // Try next text selector
                        continue;
                    }
                }

                // Fallback to original method
                if (!tabActivated) {
                    log.info('[V104.000] Text-based click failed, trying original method...');
                    tabActivated = await monitor.forceTabActivation();
                }

                if (tabActivated) {
                    log.success('[Step 4.0] Tab activation SUCCESS');
                    await page.waitForTimeout(2000);  // Wait for tab content to load
                    this.circuitBreaker.recordSuccess();
                } else {
                    log.warn('[Step 4.0] Tab activation FAILED - continuing anyway');
                    this.circuitBreaker.recordFailure();
                }
                await monitor.unlockNavigation();
            }

            // Phase 1: Adaptive Click
            log.info('[Step 4.1] Phase 1: Adaptive Click...');
            await monitor.lockNavigation();

            const clickTarget = elementHandle || await page.$('body');
            const clickResult = await monitor.adaptiveClick(clickTarget, CONFIG.anchorSelectors || []);

            if (clickResult.layersDetected) {
                log.success('[Step 4.1] Layers detected, proceeding with extraction...');
                await monitor.cleanUI();
                await page.waitForTimeout(isDetailPage ? 5000 : 3000);  // V104.000: Longer wait for detail pages
                this.circuitBreaker.recordSuccess();
            } else {
                log.warn('[Step 4.1] No layers detected');
                this.circuitBreaker.recordFailure();
            }

            // Phase 2: Extract data
            log.info('[Step 4.2] Extracting data...');

            // V108.000: ROUTING LOGIC - 联赛页 vs 详情页
            let extractedData;
            if (isDetailPage) {
                // V108.000: 详情页 → 动态交互提取 (Multi-Axis Hover)
                log.info('[V108.000] DETAIL PAGE detected - Using Multi-Axis Hover Extraction...');
                extractedData = await this.extractWithV108MultiAxis(page, null);
                this.multiAxisStats.detailPagesProcessed++;
            } else {
                // V104.000: 联赛页 → 静态批量扫描 (ParserEngine)
                log.info('[V104.000] LEAGUE PAGE detected - Using Static Batch Scanning...');

                // V99.000: EXTREME DATA BREATHING
                log.info('[V99.000] Data Breathing: EXTREME MODE...');
                try {
                    await page.waitForFunction(() => {
                        const walker = document.createTreeWalker(
                            document.body,
                            NodeFilter.SHOW_ELEMENT,
                            {
                                acceptNode: (node) => {
                                    if (node.tagName !== 'SPAN' && node.tagName !== 'DIV') return NodeFilter.FILTER_SKIP;
                                    const text = node.textContent || '';
                                    return /\d+\.?\d*/.test(text) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_SKIP;
                                }
                            },
                            false
                        );
                        return walker.nextNode() !== null;
                    }, { timeout: 10000 });
                    log.success('[V99.000] Data Breathing: Numeric content detected!');
                } catch (e) {
                    log.warn(`[V99.000] Data Breathing: Timeout (${e.message})`);
                }

                extractedData = await parser.extractMetricData();
                this.multiAxisStats.leaguePagesProcessed++;
            }

            // V104.000: Track opening odds and movement statistics
            urlOpeningStats = extractedData.openingOddsStats || {
                totalRecords: 0,
                openingOddsFound: 0,
                historyCaptureRate: 0
            };
            urlMovementAudit = extractedData.movementAudit || {
                totalMovements: 0,
                movementsByVendor: {},
                movementsBySource: { 'data-attr': 0, 'title-regex': 0, 'current-fallback': 0 }
            };

            log.info(`[V108.000] URL Stats: Opening=${urlOpeningStats.openingOddsFound}/${urlOpeningStats.totalRecords} (${urlOpeningStats.historyCaptureRate}%) | Movements=${urlMovementAudit.totalMovements}`);

            // V99.000: TAB ENFORCEMENT if no data (only for league pages)
            if (!isDetailPage && (!extractedData.fieldCount || extractedData.fieldCount === 0)) {
                log.warn('[V99.000] Tab Enforcement: No fields detected, attempting tab activation...');
                const tabActivated = await monitor.forceTabActivation();
                if (tabActivated) {
                    log.info('[V99.000] Tab Enforcement: Tabs activated, re-extracting...');
                    try {
                        await page.waitForFunction(() => {
                            const walker = document.createTreeWalker(
                                document.body,
                                NodeFilter.SHOW_ELEMENT,
                                {
                                    acceptNode: (node) => {
                                        if (node.tagName !== 'SPAN' && node.tagName !== 'DIV') return NodeFilter.FILTER_SKIP;
                                        const text = node.textContent || '';
                                        return /\d+\.?\d*/.test(text) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_SKIP;
                                    }
                                },
                                false
                            );
                            return walker.nextNode() !== null;
                        }, { timeout: 8000 });
                    } catch (e) {
                        log.warn(`[V99.000] Data Breathing (retry): Timeout (${e.message})`);
                    }
                    extractedData = await parser.extractMetricData();
                    urlOpeningStats = extractedData.openingOddsStats || urlOpeningStats;
                    urlMovementAudit = extractedData.movementAudit || urlMovementAudit;
                }
            }

            // V104.000: Sample Audit
            if (extractedData && extractedData.temporalSequence && extractedData.temporalSequence.length > 0) {
                const audits = parser.auditSampleMatches(extractedData);
            }

            await monitor.unlockNavigation();

            // Step 5: Database persistence
            log.info('[Step 5] Persisting to database...');

            const client = await this.dbPool.connect();
            let recordsInsertedThisUrl = 0;
            let entityId = null;

            try {
                const sourceId = url.split('/').pop() || 'unknown';
                const urlHash = Buffer.from(url).toString('base64').substring(0, 16);
                const uniqueProcessId = `${sourceId}_${urlHash}_${Date.now()}`;
                entityId = await this.storage.getOrCreateEntity(client, sourceId, url, 'match');

                log.info(`[V93.500] ID LOCKING: Entity ID ${entityId} locked`);

                const temporalPoints = extractedData.temporalSequence || [];
                const records = [];

                for (const point of temporalPoints) {
                    for (const dim of ['home', 'draw', 'away']) {
                        if (point.dimensions[dim]) {
                            const openingOddsValue = point.openingOdds?.[dim] || point.dimensions[dim];
                            const closingOddsValue = point.closingOdds?.[dim] || point.dimensions[dim];
                            const isMovedValue = point.isMoved?.[dim] || false;
                            const openingSourceValue = point.openingSource?.[dim] || 'current-fallback';

                            records.push({
                                entity_id: entityId,
                                provider_name: point.vendor || 'Unknown',
                                metric_type: dim,
                                value: point.dimensions[dim],
                                occurred_at: point.metricTime,
                                raw_data: JSON.stringify({
                                    opening_odds: openingOddsValue,
                                    closing_odds: closingOddsValue,
                                    is_moved: isMovedValue,
                                    opening_source: openingSourceValue
                                })
                            });
                        }
                    }
                }

                if (records.length > 0) {
                    const upsertResult = await this.storage.upsertTemporalRecords(client, entityId, records);
                    recordsInsertedThisUrl = upsertResult.total || records.length;
                    log.success(`[Step 5] Inserted ${recordsInsertedThisUrl} records for entity ${entityId}`);

                    await new Promise(resolve => setTimeout(resolve, 2000));

                    const verifyResult = await client.query(
                        'SELECT COUNT(*) as count FROM temporal_metric_records WHERE entity_id = $1',
                        [entityId]
                    );
                    const actualCount = parseInt(verifyResult.rows[0].count);
                    log.success(`[V95.000] Physical verification: Entity ${entityId} has ${actualCount} total records`);

                    if (actualCount <= 0) {
                        log.error(`[V95.000] PHYSICAL VERIFICATION FAILED`);
                        this.circuitBreaker.recordFailure();
                    } else {
                        log.success(`[V95.000] PHYSICAL VERIFICATION PASSED`);
                        this.circuitBreaker.recordSuccess();
                    }
                }

                this.metricRecords.push(...records);
                this.totalPoints += extractedData.historyPoints || 0;
                this.totalDBDelta += recordsInsertedThisUrl;

                // Accumulate statistics
                if (urlOpeningStats) {
                    this.openingOddsStats.totalRecords += urlOpeningStats.totalRecords;
                    this.openingOddsStats.openingOddsFound += urlOpeningStats.openingOddsFound;
                }

                // V104.000: Accumulate movement audit statistics
                if (urlMovementAudit) {
                    this.movementAudit.totalMovements += urlMovementAudit.totalMovements;
                    for (const [vendor, count] of Object.entries(urlMovementAudit.movementsByVendor || {})) {
                        this.movementAudit.movementsByVendor[vendor] = (this.movementAudit.movementsByVendor[vendor] || 0) + count;
                    }
                    for (const [source, count] of Object.entries(urlMovementAudit.movementsBySource || {})) {
                        this.movementAudit.movementsBySource[source] = (this.movementAudit.movementsBySource[source] || 0) + count;
                    }
                }

            } catch (dbError) {
                log.error(`[V93.500] Database error: ${dbError.message}`);
                this.circuitBreaker.recordFailure();
            } finally {
                client.release();
            }

            if (structureSnapshot) {
                this.structureSnapshot = structureSnapshot;
            }

            this.urlsProcessed++;
            if (extractedData.historyPoints > 0) {
                this.urlsSuccess++;
            }

            return {
                success: true,
                fieldCount: extractedData.fieldCount,
                historyPoints: extractedData.historyPoints,
                recordsInserted: recordsInsertedThisUrl,
                entityId: entityId,
                openingOddsStats: urlOpeningStats,
                movementAudit: urlMovementAudit,  // V104.000: Return movement audit
                containerType: extractedData.containerType || 'unknown'  // V104.000: Container type
            };

        } catch (error) {
            this.circuitBreaker.recordFailure();
            this.urlsProcessed++;
            this.urlsFailed++;
            log.error(`[V95.000] URL processing error: ${error.message}`);
            return { success: false, error: error.message };
        } finally {
            if (page && !page.isClosed()) {
                await page.close();
                log.info(`[V95.000] Page closed for URL ${index + 1}`);
            }
        }
    }

    async processConcurrently(urls, maxConcurrent = CONFIG.concurrency.maxConcurrent) {
        log.info(`[V104.000] Processing ${urls.length} URLs with ${maxConcurrent} concurrent workers...`);

        const results = [];
        const queue = [...urls];
        const workers = [];

        for (let i = 0; i < Math.min(maxConcurrent, queue.length); i++) {
            workers.push(this.processQueue(queue, i, results));
        }

        await Promise.all(workers);
        return results;
    }

    async processQueue(queue, workerId, results) {
        while (queue.length > 0) {
            const url = queue.shift();
            const index = results.length;
            const result = await this.processUrl(url, index, results.length + queue.length, workerId);
            results.push(result);
        }
    }

    async getDatabaseDelta() {
        try {
            const client = await this.dbPool.connect();
            try {
                const countResult = await this.storage.getRecordCount(client);
                return countResult.total || 0;
            } finally {
                client.release();
            }
        } catch (error) {
            log.error(`[V104.000] Failed to get DB delta: ${error.message}`);
            return 0;
        }
    }

    /**
     * V108.000: Final report with Multi-Axis statistics
     */
    generateReport() {
        const elapsed = Date.now() - this.startTime;
        const breakerStatus = this.circuitBreaker.getStatus();

        const successRate = this.urlsProcessed > 0 ? ((this.urlsSuccess / this.urlsProcessed) * 100).toFixed(1) : '0.0';

        // Calculate History Capture Rate
        if (this.openingOddsStats.totalRecords > 0) {
            this.openingOddsStats.historyCaptureRate =
                ((this.openingOddsStats.openingOddsFound / this.openingOddsStats.totalRecords) * 100).toFixed(2);
        }

        log.success('=== V108.000 Pipeline Integration COMPLETE ===');
        log.info(`Elapsed time: ${elapsed}ms`);
        log.info(`Circuit breaker: ${breakerStatus.isDegraded ? 'DEGRADED' : 'OK'}`);

        // V108.000: Enhanced summary table with Multi-Axis metrics
        log.success('');
        log.success('┌─────────────────────────────────────────────────────────────────┐');
        log.success('│                      V108.000 HARVEST SUMMARY                    │');
        log.success('├─────────────────────────────────────────────────────────────────┤');
        log.success(`│  Total Points Extracted    : ${String(this.totalPoints).padStart(14)}  │`);
        log.success(`│  DB Records Inserted      : ${String(this.totalDBDelta).padStart(14)}  │`);
        log.success(`│  Total Metric Records     : ${String(this.metricRecords.length).padStart(14)}  │`);
        log.success(`│  URLs Processed           : ${String(this.urlsProcessed).padStart(14)}  │`);
        log.success(`│  URLs Success             : ${String(this.urlsSuccess).padStart(14)}  │`);
        log.success(`│  Success Rate (URL)       : ${String(successRate + '%').padStart(14)}  │`);
        log.success('├─────────────────────────────────────────────────────────────────┤');
        log.success('│              V108.000: MULTI-AXIS ROUTING METRICS                │');
        log.success('├─────────────────────────────────────────────────────────────────┤');
        log.success(`│  Detail Pages Processed   : ${String(this.multiAxisStats.detailPagesProcessed).padStart(14)}  │`);
        log.success(`│  League Pages Processed   : ${String(this.multiAxisStats.leaguePagesProcessed).padStart(14)}  │`);
        log.success(`│  Total Axes Captured      : ${String(this.multiAxisStats.totalAxesCaptured).padStart(14)}  │`);
        log.success(`│  Total Init Values        : ${String(this.multiAxisStats.totalInitValues).padStart(14)}  │`);
        log.success(`│  Avg Axes Per Provider    : ${String(this.multiAxisStats.avgAxesPerProvider).padStart(14)}  │`);
        log.success('├─────────────────────────────────────────────────────────────────┤');
        log.success('│              V108.000: OPENING ODDS CAPTURE METRICS               │');
        log.success('├─────────────────────────────────────────────────────────────────┤');
        log.success(`│  Total Records             : ${String(this.openingOddsStats.totalRecords).padStart(14)}  │`);
        log.success(`│  Opening Odds Found        : ${String(this.openingOddsStats.openingOddsFound).padStart(14)}  │`);
        log.success(`│  History Capture Rate      : ${String(this.openingOddsStats.historyCaptureRate + '%').padStart(14)}  │`);
        log.success('├─────────────────────────────────────────────────────────────────┤');
        log.success('│              V108.000: MOVEMENT AUDIT METRICS                   │');
        log.success('├─────────────────────────────────────────────────────────────────┤');
        log.success(`│  Total Movements          : ${String(this.movementAudit.totalMovements).padStart(14)}  │`);
        log.success(`│  Movements (data-attr)     : ${String(this.movementAudit.movementsBySource['data-attr'] || 0).padStart(14)}  │`);
        log.success(`│  Movements (title-regex)   : ${String(this.movementAudit.movementsBySource['title-regex'] || 0).padStart(14)}  │`);
        log.success(`│  Movements By Vendor       : ${JSON.stringify(this.movementAudit.movementsByVendor || {}).padStart(14)}  │`);
        log.success('├─────────────────────────────────────────────────────────────────┤');
        log.success(`│  Avg Time Per Record (ms)  : ${String((this.totalDBDelta > 0 ? (elapsed / this.totalDBDelta).toFixed(2) : 'N/A')).padStart(14)}  │`);
        log.success(`│  Total Elapsed Time (ms)   : ${String(elapsed).padStart(14)}  │`);
        log.success('└─────────────────────────────────────────────────────────────────┘');
        log.success('');

        const isSuccess = this.totalPoints > 0 && this.metricRecords.length > 0 && this.totalDBDelta > 0;

        return {
            success: isSuccess,
            totalPoints: this.totalPoints,
            dbDelta: this.totalDBDelta,
            metricRecords: this.metricRecords.length,
            breakerStatus: breakerStatus,
            elapsed: elapsed,
            successRate: parseFloat(successRate),
            openingOddsStats: this.openingOddsStats,
            movementAudit: this.movementAudit,
            multiAxisStats: this.multiAxisStats  // V108.000: Include multi-axis stats
        };
    }

    async cleanup() {
        if (this.contextPool && this.contextPool.length > 0) {
            for (const context of this.contextPool) {
                try { await context.close(); } catch (e) {}
            }
            this.contextPool = [];
        }
        if (this.browser) {
            try { await this.browser.close(); } catch (e) {}
        }
        try {
            if (this.dbPool) await this.dbPool.end();
        } catch (e) {}
    }
}

// ============================================================================
// MAIN ENTRY POINT - V108.000
// ============================================================================

async function main() {
    const harvester = new MainHarvester();
    harvester.startTime = Date.now();

    log.info('=== V108.000 Pipeline Integration START ===');
    log.info('[V108.000] Multi-Axis Sync: ACTIVE (Home/Draw/Away)');
    log.info('[V108.000] Routing Logic: ENABLED (League→Static, Detail→Dynamic)');
    log.info('[V108.000] Promise.race: ENABLED (Optimized response)');
    log.info('[V108.000] STEALTH MODE: ACTIVE (ignoreDefaultArgs + Real Chrome UA)');
    log.info('[V108.000] PAGE VERIFICATION: ENABLED (Access Denied detection)');
    log.info('[V108.000] PRECISION CLICK: ENABLED ((0,0) anchor for interaction)');
    log.info('[V108.000] MATCH DETAIL PENETRATION: ENABLED');
    log.info('[V108.000] MOVEMENT AUDIT: ENABLED');
    log.info(`[V108.000] Grid Harvest: READY (MAX_CONCURRENT=${CONFIG.concurrency.maxConcurrent})`);

    try {
        await harvester.initialize();
        const results = await harvester.processConcurrently(CONFIG.targetUrls);
        const report = harvester.generateReport();

        if (report.success) {
            console.log(`\n[V108.000] Multi-Axis Sync: ACTIVE. Main Pipeline: INTEGRATED.`);
            console.log(`[V108.000] System ready for precision sampling.`);
            console.log(`[V108.000] Total points: ${report.totalPoints} (> 0 ✓)`);
            console.log(`[V108.000] DB Delta: ${report.dbDelta} (> 0 ✓)`);
            console.log(`[V108.000] Metric Records: ${report.metricRecords}`);
            console.log(`[V108.000] History Rate: ${report.openingOddsStats.historyCaptureRate}%`);
            console.log(`[V108.000] Total Movements: ${report.movementAudit.totalMovements}`);
            console.log(`[V108.000] Elapsed: ${report.elapsed}ms`);
            console.log(`[V108.000] Detail Pages: ${report.multiAxisStats.detailPagesProcessed}`);
            console.log(`[V108.000] League Pages: ${report.multiAxisStats.leaguePagesProcessed}`);
            console.log(`[V108.000] Axes Captured: ${report.multiAxisStats.totalAxesCaptured}`);
            console.log(`[V108.000] Init Values: ${report.multiAxisStats.totalInitValues}`);
            console.log(`\n[V108.000] System ready for precision sampling.`);

            process.exit(0);
        } else {
            console.log(`\n[V108.000] Verification criteria not met:`);
            console.log(`  - Total points: ${report.totalPoints} (required: > 0)`);
            console.log(`  - DB Delta: ${report.dbDelta} (required: >= 0)`);
            console.log(`  - Metric Records: ${report.metricRecords} (required: > 0)`);

            process.exit(1);
        }
    } catch (error) {
        log.error(`[V108.000] Fatal error: ${error.message}`);
        log.error(error.stack);
        process.exit(1);
    } finally {
        await harvester.cleanup();
    }
}

if (require.main === module) {
    main().catch(error => {
        console.error('[V108.000] Fatal error:', error);
        process.exit(1);
    });
}

module.exports = { main, MainHarvester, CircuitBreaker };
