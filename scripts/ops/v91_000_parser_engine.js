/**
 * V103.000 Parser Engine - Black Box Detection Mode
 * =================================================
 *
 * Core data extraction logic:
 *   - extractMetricData() - Native TreeWalker traversal + semantic vendor detection
 *   - identifyIdentity() - Vendor signature mapping
 *
 * V103.000: Black Box Detection Mode + Enhanced Radar Selectors
 *   - V103.000: Enhanced radar selectors (attribute contains matching)
 *   - V103.000: Movement audit with opening_source tracking
 *   - V103.000: Complete JSON output for records with Opening != Closing
 *
 * @version V103.000
 * @since 2026-01-26
 */

'use strict';

const { log } = require('./v91_000_config');

// ============================================================================
// PARSER ENGINE - V103.000
// ============================================================================

/**
 * V103.000: Parser Engine - Match Detail Page Penetration with Movement Audit
 *
 * Key features:
 *   - V90.700: Native TreeWalker (no custom recursion)
 *   - V90.700: Semantic vendor detection via img.bookmaker-logo title/alt
 *   - V90.700: Full-page numeric pattern matching
 *   - V101.000: FORCED opening odds extraction with multiple fallback strategies
 *   - V103.000: Detail page container selectors + Movement audit
 */
class ParserEngine {
    constructor(page, config = {}) {
        this.page = page;
        this.config = config;
    }

    /**
     * V103.000: Data Extraction with Detail Page Scoping + Movement Audit
     *
     * V103.000 Enhancements:
     *   - Detail page container selectors (div#odds-data-table, [data-id="odds-table"])
     *   - Movement audit with complete JSON output for Opening != Closing records
     *   - Opening source tracking (data-attr/title-regex/current-fallback)
     *
     * @returns {Promise<Object>} Extracted data with numeric values, vendors, and debug info
     */
    async extractMetricData() {
        log.info('[V103.000] CONTENT SCOPING: Detail page penetration + Movement audit ENABLED...');

        const extractedData = await this.page.evaluate((config) => {
            const results = {
                textContent: [],
                numericValues: [],
                providersDetected: [],
                fieldCount: 0,
                temporalSequence: [],
                historyPoints: 0,
                vendorIdentities: [],
                allContainers: [],
                htmlFragments: [],
                debugInfo: [],
                // V101.000: Track opening odds capture statistics
                openingOddsStats: {
                    totalRecords: 0,
                    openingOddsFound: 0,
                    historyCaptureRate: 0
                },
                // V103.000: Movement audit - track records with actual odds movement
                movementAudit: {
                    totalMovements: 0,
                    movementsByVendor: {},
                    movementsBySource: {
                        'data-attr': 0,
                        'title-regex': 0,
                        'current-fallback': 0
                    },
                    movementRecords: []  // V103.000: Complete JSON for Opening != Closing
                }
            };

            // V97.000: RELAXED Numeric patterns
            const numericPatterns = [
                /\d+\.\d{2}/g,  /\d+,\d{2}/g,
                /\d+\.\d{1}/g,  /\d+,\d{1}/g,
                /\d+\.\d{0,2}/g, /\d+,\d{0,2}/g,
                /\d{1,3}\.\d{1,2}/g, /\d{1,3},\d{1,2}/g
            ];

            // V103.000: ENHANCED RADAR SELECTORS - Attribute contains matching
            // Detail pages have different structure than league pages
            const detailPageSelectors = [
                'div#odds-data-table',           // V103.000: Primary odds data table
                '[data-id="odds-table"]',         // V103.000: Data attribute selector
                'table#odds-table',               // V103.000: Table with odds data
                'div[class*="odds-table"]',       // V103.000: Any odds-table variant
                'div[data-tab="odds"]',           // V103.000: Tab-based odds container
                'div[class*="betting-odds"]',     // V103.000: Betting odds container
                'table.betting-table',            // V103.000: Betting table
                'div[class*="odd-history"]',      // V103.000: Odds history container
                // V103.000: RADAR selectors - attribute contains matching
                'div[class*="odds"]',             // V103.000: Any div with "odds" in class
                'table[class*="odds"]',           // V103.000: Any table with "odds" in class
                '[data-testid*="odds"]',          // V103.000: Any element with "odds" in testid
                'section[class*="odds"]',         // V103.000: Section with odds
                'div[id*="odds"]',                // V103.000: Any div with "odds" in id
                '[data-component*="odds"]'        // V103.000: Component-based odds
            ];

            // V103.000: League page selectors (fallback)
            const leaguePageSelectors = [
                'div.border-black-borders',
                'div[class*="border-black"]',
                'div[class*="tournament"]',
                'div[class*="event"]',
                'div[data-testid="event-name"]',
                'table[class*="table"]',
                'div.main-content',
                'div#tournamentTable'
            ];

            let targetContainer = null;
            let containerType = 'unknown';

            // V103.000: Phase 1 - Try detail page selectors first (PRIORITY)
            results.debugInfo.push('[V103.000] Phase 1: Searching for DETAIL PAGE containers...');
            for (const selector of detailPageSelectors) {
                try {
                    const element = document.querySelector(selector);
                    if (element) {
                        targetContainer = element;
                        containerType = 'detail-page';
                        results.debugInfo.push(`[V103.000] Detail page container FOUND: ${selector}`);
                        break;
                    }
                } catch (e) {
                    // Selector may be invalid, continue
                }
            }

            // V103.000: Phase 2 - Fallback to league page selectors
            if (!targetContainer) {
                results.debugInfo.push('[V103.000] Phase 2: Detail page containers not found, trying LEAGUE PAGE selectors...');
                for (const selector of leaguePageSelectors) {
                    try {
                        const elements = document.querySelectorAll(selector);
                        for (const element of elements) {
                            // Walk up to find a suitable container with enough children
                            let current = element;
                            let level = 0;
                            while (current && level < 6) {
                                if (current.children && current.children.length >= 5) {
                                    const text = current.textContent || '';
                                    const hasDecimal = /\d+\.\d+/.test(text) || /\d+,\d+/.test(text);
                                    if (hasDecimal) {
                                        targetContainer = current;
                                        containerType = 'league-page';
                                        break;
                                    }
                                }
                                current = current.parentElement;
                                level++;
                            }
                            if (targetContainer) break;
                        }
                        if (targetContainer) break;
                    } catch (e) {
                        // Selector may be invalid, continue
                    }
                }
            }

            // V103.000: Phase 3 - UNIVERSAL ADAPTER (last resort)
            if (!targetContainer) {
                results.debugInfo.push('[V103.000] Phase 3: No trusted containers found, activating UNIVERSAL ADAPTER...');
                const bettingKeywords = ['1X2', 'Home/Draw/Away', 'Home Draw Away', 'odds', 'betting'];
                let bestCandidate = null;
                let maxNumericCount = 0;

                const allDivs = document.querySelectorAll('div');
                for (const div of allDivs) {
                    const text = (div.textContent || '').toLowerCase();
                    const hasBettingKeyword = bettingKeywords.some(keyword =>
                        text.toLowerCase().includes(keyword.toLowerCase())
                    );

                    if (hasBettingKeyword) {
                        const walker = document.createTreeWalker(div, NodeFilter.SHOW_TEXT, null, false);
                        let count = 0;
                        const numericPattern = /\b\d+\.\d{2}\b/;
                        let textNode;
                        while (textNode = walker.nextNode()) {
                            const text = textNode.textContent || '';
                            const matches = text.match(numericPattern);
                            if (matches) count += matches.length;
                        }

                        if (count > maxNumericCount && div.children && div.children.length >= 3) {
                            bestCandidate = div;
                            maxNumericCount = count;
                        }
                    }
                }

                if (bestCandidate && maxNumericCount > 0) {
                    targetContainer = bestCandidate;
                    containerType = 'universal-adapter';
                    results.debugInfo.push(`[V103.000] UNIVERSAL ADAPTER: Found container with ${maxNumericCount} numeric values`);
                } else {
                    results.debugInfo.push('[V103.000] WARNING: No suitable container found, using body');
                    targetContainer = document.body;
                    containerType = 'body-fallback';
                }
            }

            results.debugInfo.push(`[V103.000] Container LOCKED: ${targetContainer.tagName}#${targetContainer.id || targetContainer.className?.substring(0, 50)} (Type: ${containerType})`);

            // V93.500: Blacklist keywords
            const blacklistKeywords = ['advertisement', 'footer', 'header', 'menu', 'sidebar', 'banner', 'popup', 'cookie', 'consent', 'privacy', 'odds-format', 'outrights'];

            function isBlacklisted(node) {
                const className = (node.className || '').toString().toLowerCase();
                const id = (node.id || '').toLowerCase();
                const tagName = (node.tagName || '').toLowerCase();
                return blacklistKeywords.some(keyword => className.includes(keyword) || id.includes(keyword) || tagName.includes(keyword));
            }

            function isInsideAdvertisement(node) {
                let current = node;
                let levels = 0;
                while (current && current !== document.body && levels < 10) {
                    const className = (current.className || '').toString().toLowerCase();
                    const id = (current.id || '').toLowerCase();
                    const text = (current.textContent || '').trim().toLowerCase();
                    if (className.includes('advertisement') || className.includes('ad-') ||
                        id.includes('advertisement') || id.includes('ad-') ||
                        text.includes('sponsored') || text.includes('ad by')) {
                        return true;
                    }
                    current = current.parentElement;
                    levels++;
                }
                return false;
            }

            // DOM traversal
            const numericNodes = [];
            const processedNodes = new Set();

            const walker = document.createTreeWalker(
                targetContainer,
                NodeFilter.SHOW_ELEMENT,
                {
                    acceptNode: function(node) {
                        if (isBlacklisted(node)) return NodeFilter.FILTER_REJECT;
                        if (isInsideAdvertisement(node)) return NodeFilter.FILTER_REJECT;
                        return NodeFilter.FILTER_ACCEPT;
                    }
                },
                false
            );

            let node;
            let depth = 0;
            while (node = walker.nextNode()) {
                if (processedNodes.has(node)) continue;
                processedNodes.add(node);

                const text = node.textContent?.trim() || '';
                if (text.length === 0) continue;

                for (const pattern of numericPatterns) {
                    const matches = text.match(pattern);
                    if (matches && matches.length > 0) {
                        numericNodes.push({
                            node: node,
                            text: text.substring(0, 100),
                            matches: matches,
                            depth: depth,
                            tagName: node.tagName,
                            className: (node.className || '').toString().substring(0, 100),
                            id: node.id || ''
                        });
                        break;
                    }
                }
                depth++;
            }

            results.debugInfo.push(`[V103.000] Found ${numericNodes.length} numeric nodes`);

            // V100.000: Vendor signatures
            const vendorSignatures = {
                'Type_B': { text: ['b365', '365', 'bet365'], imgAlt: ['bet365', 'b365 logo'], imgSrc: ['bet365', 'b365'], title: ['Bet365', 'bet 365'] },
                'Type_P': { text: ['pinna', 'pinnacle', 'ps3838'], imgAlt: ['pinnacle', 'pinny'], imgSrc: ['pinnacle', 'ps3838'], title: ['Pinnacle', 'Pinny'] },
                'Type_U': { text: ['uni', 'unibet'], imgAlt: ['unibet', 'uni'], imgSrc: ['unibet'], title: ['Unibet'] },
                'Type_W': { text: ['bwin', 'william', 'hill', 'wh'], imgAlt: ['bwin', 'william hill', 'willhill'], imgSrc: ['bwin', 'williamhill', 'wh'], title: ['Bwin', 'William Hill'] },
                'Type_X': { text: ['1x', 'xbet', '1xbet'], imgAlt: ['1xbet', '1x'], imgSrc: ['1xbet', '1x'], title: ['1xBet', '1X'] },
                'Type_S': { text: ['betfair', 'sporting', 'bet fair'], imgAlt: ['betfair', 'sporting', 'bf'], imgSrc: ['betfair', 'sporting', 'bf'], title: ['Betfair', 'Sporting'] }
            };

            function findVendorViaLogo(nearbyNode) {
                let current = nearbyNode;
                let level = 0;
                while (current && current !== document.body && level < 8) {
                    const logos = current.querySelectorAll('img.bookmaker-logo, img[class*="logo"], img[alt*="bet"], img[title*="bet"]');
                    for (const logo of logos) {
                        const logoTitle = (logo.getAttribute('title') || '').toLowerCase();
                        const logoAlt = (logo.getAttribute('alt') || '').toLowerCase();
                        const logoSrc = (logo.getAttribute('src') || '').toLowerCase();

                        for (const [vendor, patterns] of Object.entries(vendorSignatures)) {
                            if (patterns.text?.some(p => logoTitle.includes(p) || logoAlt.includes(p)) ||
                                patterns.imgAlt?.some(p => logoAlt.includes(p)) ||
                                patterns.imgSrc?.some(p => logoSrc.includes(p)) ||
                                patterns.title?.some(p => logoTitle.includes(p))) {
                                return { vendor, level, method: 'enhanced_img_logo' };
                            }
                        }
                    }
                    current = current.parentElement;
                    level++;
                }
                return null;
            }

            const enrichedNodes = numericNodes.map((numericNode) => {
                const logoResult = findVendorViaLogo(numericNode.node);
                if (logoResult) {
                    return { ...numericNode, vendor: logoResult.vendor, vendorDistance: logoResult.level, vendorMethod: logoResult.method };
                }

                let vendorFound = null;
                let current = numericNode.node;
                let level = 0;

                while (current && current !== document.body && level < 5) {
                    const className = (current.className || '').toString().toLowerCase();
                    const id = (current.id || '').toLowerCase();
                    const dataAttr = current.getAttribute('data-vendor')?.toLowerCase() || current.getAttribute('data-provider')?.toLowerCase() || '';
                    const title = current.getAttribute('title')?.toLowerCase() || '';

                    for (const [vendor, patterns] of Object.entries(vendorSignatures)) {
                        if (patterns.text?.some(pattern => className.includes(pattern) || id.includes(pattern) || dataAttr.includes(pattern) || title.includes(pattern))) {
                            vendorFound = vendor;
                            break;
                        }
                    }
                    if (vendorFound) break;
                    current = current.parentElement;
                    level++;
                }

                return { ...numericNode, vendor: vendorFound, vendorDistance: level, vendorMethod: vendorFound ? 'metadata_fallback' : null };
            });

            const allNumericValues = [];
            const vendorCounts = {};
            const vendorHotspots = new Map();

            // V101.000: Enhanced title regex patterns
            const titleOpeningPatterns = [
                /(?:opening\s+odds?|opened)\s*[:\-=]?\s*(\d+[.,]\d+)/i,
                /(?:started?\s+(?:at|from))\s*[:\-=]?\s*(\d+[.,]\d+)/i,
                /(?:initial\s+odds?|first\s+odds?)\s*[:\-=]?\s*(\d+[.,]\d+)/i,
                /(?:begin\s+odds?|beginning)\s*[:\-=]?\s*(\d+[.,]\d+)/i,
                /\b(?:open|start)\b.*?(\d+\.\d{2})/i
            ];

            enrichedNodes.forEach((enrichedNode) => {
                if (enrichedNode.vendor && enrichedNode.vendor !== 'Type_Unknown') {
                    const positionKey = `${enrichedNode.depth}_${enrichedNode.index}`;
                    vendorHotspots.set(positionKey, enrichedNode.vendor);
                }

                for (const pattern of numericPatterns) {
                    const matches = enrichedNode.text.match(pattern);
                    if (matches) {
                        matches.forEach(match => {
                            const normalized = match.replace(',', '.');
                            const value = parseFloat(normalized);

                            if (!isNaN(value) && value >= 1.01 && value <= 1000) {
                                let vendorIdentity = enrichedNode.vendor || 'Type_Unknown';

                                if (vendorIdentity === 'Type_Unknown') {
                                    for (let dOffset = 0; dOffset <= 3; dOffset++) {
                                        for (let iOffset = -2; iOffset <= 2; iOffset++) {
                                            const checkKey = `${enrichedNode.depth - dOffset}_${enrichedNode.index + iOffset}`;
                                            if (vendorHotspots.has(checkKey)) {
                                                vendorIdentity = vendorHotspots.get(checkKey);
                                                break;
                                            }
                                        }
                                        if (vendorIdentity !== 'Type_Unknown') break;
                                    }
                                }

                                // V101.000: FORCED Opening Odds Extraction
                                const node = enrichedNode.node;
                                let finalOpeningOdds = null;
                                let openingSource = 'none';

                                const dataOpeningOdds = node.getAttribute('data-opening-odds') ||
                                                        node.getAttribute('data-initial-odds') ||
                                                        node.getAttribute('data-start-odds');
                                if (dataOpeningOdds) {
                                    finalOpeningOdds = parseFloat(dataOpeningOdds.replace(',', '.'));
                                    openingSource = 'data-attr';
                                }

                                if (!finalOpeningOdds || isNaN(finalOpeningOdds)) {
                                    const titleAttr = node.getAttribute('title') || node.getAttribute('data-tooltip') || '';
                                    if (titleAttr) {
                                        for (const titlePattern of titleOpeningPatterns) {
                                            const titleMatch = titleAttr.match(titlePattern);
                                            if (titleMatch && titleMatch[1]) {
                                                finalOpeningOdds = parseFloat(titleMatch[1].replace(',', '.'));
                                                openingSource = 'title-regex';
                                                break;
                                            }
                                        }
                                    }
                                }

                                if (!finalOpeningOdds || isNaN(finalOpeningOdds)) {
                                    finalOpeningOdds = value;
                                    openingSource = 'current-fallback';
                                }

                                const finalClosingOdds = value;
                                const isMoved = openingSource !== 'current-fallback' && Math.abs(finalOpeningOdds - finalClosingOdds) > 0.01;

                                // V101.000: Track opening odds statistics
                                results.openingOddsStats.totalRecords++;
                                if (openingSource !== 'current-fallback') {
                                    results.openingOddsStats.openingOddsFound++;
                                }

                                // V103.000: MOVEMENT AUDIT - Track records with actual odds movement
                                if (isMoved) {
                                    results.movementAudit.totalMovements++;
                                    results.movementAudit.movementsBySource[openingSource]++;
                                    results.movementAudit.movementsByVendor[vendorIdentity] = (results.movementAudit.movementsByVendor[vendorIdentity] || 0) + 1;

                                    // V103.000: Store complete JSON for movement records
                                    results.movementAudit.movementRecords.push({
                                        vendor: vendorIdentity,
                                        dimension: node.getAttribute('data-metric-type') || 'unknown',
                                        openingOdds: finalOpeningOdds,
                                        closingOdds: finalClosingOdds,
                                        movement: finalClosingOdds - finalOpeningOdds,
                                        movementPercent: ((finalClosingOdds - finalOpeningOdds) / finalOpeningOdds * 100).toFixed(2),
                                        openingSource: openingSource,
                                        titleAttr: node.getAttribute('title')?.substring(0, 100) || null,
                                        nodeId: node.id || '',
                                        nodeClass: (node.className || '').toString().substring(0, 50)
                                    });
                                }

                                allNumericValues.push({
                                    value: value,
                                    raw: match,
                                    vendor: vendorIdentity,
                                    tagName: enrichedNode.tagName,
                                    depth: enrichedNode.depth,
                                    openingOdds: finalOpeningOdds,
                                    closingOdds: finalClosingOdds,
                                    isMoved: isMoved,
                                    openingSource: openingSource,
                                    titleAttr: node.getAttribute('title')?.substring(0, 100) || null
                                });

                                vendorCounts[vendorIdentity] = (vendorCounts[vendorIdentity] || 0) + 1;
                            }
                        });
                    }
                }
            });

            // Calculate History Capture Rate
            if (results.openingOddsStats.totalRecords > 0) {
                results.openingOddsStats.historyCaptureRate = (results.openingOddsStats.openingOddsFound / results.openingOddsStats.totalRecords * 100).toFixed(2);
            }

            // Deduplicate
            const uniqueValues = [];
            const seenValues = new Set();
            allNumericValues.forEach(nv => {
                const key = `${nv.value}_${nv.vendor || 'Type_Unknown'}`;
                if (!seenValues.has(key)) {
                    seenValues.add(key);
                    uniqueValues.push(nv);
                }
            });

            results.numericValues = uniqueValues.map(nv => nv.value);
            results.fieldCount = uniqueValues.length;
            results.providersDetected = Object.keys(vendorCounts);
            results.numericValuesRaw = allNumericValues;

            // Build vendor identities
            results.vendorIdentities = Object.entries(vendorCounts).map(([vendor, count]) => ({
                assetId: vendor,
                count: count,
                method: 'global_pattern_match'
            }));

            // Create temporal points
            const vendorGroups = {};
            uniqueValues.forEach(nv => {
                const vendor = nv.vendor || 'Type_Unknown';
                if (!vendorGroups[vendor]) vendorGroups[vendor] = [];
                vendorGroups[vendor].push(nv.value);
            });

            Object.entries(vendorGroups).forEach(([vendor, values]) => {
                if (values.length >= 1) {
                    const homeRaw = uniqueValues.find(nv => nv.vendor === vendor && nv.value === values[0]) || {};
                    const drawRaw = uniqueValues.find(nv => nv.vendor === vendor && nv.value === values[1]) || {};
                    const awayRaw = uniqueValues.find(nv => nv.vendor === vendor && nv.value === values[2]) || {};

                    results.temporalSequence.push({
                        vendor: vendor,
                        metricTime: new Date().toISOString(),
                        dimensions: { home: values[0] || null, draw: values[1] || null, away: values[2] || null },
                        openingOdds: {
                            home: homeRaw.openingOdds || values[0] || null,
                            draw: drawRaw.openingOdds || values[1] || null,
                            away: awayRaw.openingOdds || values[2] || null
                        },
                        closingOdds: {
                            home: homeRaw.closingOdds || values[0] || null,
                            draw: drawRaw.closingOdds || values[1] || null,
                            away: awayRaw.closingOdds || values[2] || null
                        },
                        isMoved: {
                            home: homeRaw.isMoved || false,
                            draw: drawRaw.isMoved || false,
                            away: awayRaw.isMoved || false
                        },
                        openingSource: {
                            home: homeRaw.openingSource || 'current-fallback',
                            draw: drawRaw.openingSource || 'current-fallback',
                            away: awayRaw.openingSource || 'current-fallback'
                        },
                        valueCount: values.length
                    });
                }
            });

            results.historyPoints = results.temporalSequence.length;
            results.containerType = containerType;

            results.debugInfo.push(`[V103.000] Container type: ${containerType}`);
            results.debugInfo.push(`[V103.000] Unique numeric values: ${uniqueValues.length}`);
            results.debugInfo.push(`[V103.000] Vendors detected: ${results.providersDetected.join(', ') || 'none'}`);
            results.debugInfo.push(`[V103.000] Temporal points: ${results.historyPoints}`);
            results.debugInfo.push(`[V103.000] Opening odds stats: ${results.openingOddsStats.openingOddsFound}/${results.openingOddsStats.totalRecords} (${results.openingOddsStats.historyCaptureRate}%)`);
            results.debugInfo.push(`[V103.000] Movement audit: ${results.movementAudit.totalMovements} records with odds movement`);

            return results;
        }, {
            minNumericValue: this.config.extraction?.minNumericValue || 1.01,
            maxNumericValue: this.config.extraction?.maxNumericValue || 1000
        });

        log.info(`[V103.000] Extraction Complete: ${extractedData.fieldCount} fields`);
        log.info(`[V103.000]  - Container type: ${extractedData.containerType || 'unknown'}`);
        log.info(`[V103.000]  - Vendors detected: ${extractedData.providersDetected.join(', ') || 'none'}`);
        log.info(`[V103.000]  - History Capture Rate: ${extractedData.openingOddsStats?.historyCaptureRate || 0}%`);
        log.info(`[V103.000]  - Total movements: ${extractedData.movementAudit?.totalMovements || 0}`);

        // V103.000: Print movement records if found
        if (extractedData.movementAudit && extractedData.movementAudit.totalMovements > 0) {
            log.success('[V103.000] === MOVEMENT AUDIT - Opening != Closing Records ===');
            extractedData.movementAudit.movementRecords.forEach((record, idx) => {
                log.success(`[V103.000] Movement ${idx + 1}:`);
                log.success(`  [V103.000]   Vendor: ${record.vendor}`);
                log.success(`  [V103.000]   Dimension: ${record.dimension}`);
                log.success(`  [V103.000]   Opening: ${record.openingOdds.toFixed(2)} → Closing: ${record.closingOdds.toFixed(2)} (${record.movement > 0 ? '+' : ''}${record.movement.toFixed(2)}, ${record.movementPercent}%)`);
                log.success(`  [V103.000]   Source: ${record.openingSource}`);
                if (record.titleAttr) {
                    log.debug(`  [V103.000]   Title: ${record.titleAttr}`);
                }
                // V103.000: Complete JSON output
                log.debug(`  [V103.000]   Complete JSON: ${JSON.stringify(record)}`);
            });
            log.success('[V103.000] === MOVEMENT AUDIT COMPLETE ===');
        }

        if (extractedData.debugInfo && extractedData.debugInfo.length > 0) {
            extractedData.debugInfo.forEach(debug => {
                log.debug(`[V103.000] Debug: ${debug.substring(0, 200)}`);
            });
        }

        return extractedData;
    }

    /**
     * V103.000: Sample Audit - Print detailed match information
     */
    auditSampleMatches(extractedData) {
        const audits = [];

        log.info('[V103.000] === SAMPLE AUDIT - First 3 Matches ===');

        extractedData.temporalSequence.slice(0, 3).forEach((point, idx) => {
            const vendor = point.vendor;
            const home = point.dimensions.home;
            const draw = point.dimensions.draw;
            const away = point.dimensions.away;

            const homeAudit = this._auditSingleOdds('Home', vendor, home, extractedData);
            const drawAudit = this._auditSingleOdds('Draw', vendor, draw, extractedData);
            const awayAudit = this._auditSingleOdds('Away', vendor, away, extractedData);

            const matchNum = idx + 1;
            log.success(`[V103.000] Match ${matchNum}: ${homeAudit.value} vs ${awayAudit.value} (Vendor: ${vendor})`);

            [homeAudit, drawAudit, awayAudit].forEach(audit => {
                if (audit.value) {
                    const openingStr = audit.openingOdds ? audit.openingOdds.toFixed(2) : 'N/A';
                    const closingStr = audit.closingOdds ? audit.closingOdds.toFixed(2) : 'N/A';
                    const movedStr = audit.isMoved ? 'YES' : 'NO';
                    const sourceStr = audit.openingSource || 'unknown';

                    log.success(`  [V103.000] ${audit.dimension}: Current=${closingStr} | Opening=${openingStr} | Source=${sourceStr} | IsMoved=${movedStr}`);
                }
            });

            audits.push({ matchNumber: matchNum, vendor: vendor, home: homeAudit, draw: drawAudit, away: awayAudit });
        });

        log.success('[V103.000] === SAMPLE AUDIT COMPLETE ===');
        return audits;
    }

    _auditSingleOdds(dimension, vendor, value, extractedData) {
        const rawEntry = (extractedData.numericValuesRaw || []).find(nv =>
            nv.vendor === vendor && Math.abs(nv.value - (value || 0)) < 0.01
        );

        return {
            dimension: dimension,
            vendor: vendor || 'Type_Unknown',
            value: value || null,
            openingOdds: rawEntry?.openingOdds || value || null,
            closingOdds: rawEntry?.closingOdds || value || null,
            isMoved: rawEntry?.isMoved || false,
            openingSource: rawEntry?.openingSource || 'current-fallback',
            titleAttr: rawEntry?.titleAttr || null
        };
    }

    identifyIdentity(vendorSignature) {
        const vendorMap = this.config.vendorMap || [];
        for (const vendor of vendorMap) {
            for (const alias of vendor.aliases) {
                if (vendorSignature.toLowerCase().includes(alias.toLowerCase())) {
                    return vendor.name;
                }
            }
        }
        return 'Unknown';
    }
}

module.exports = { ParserEngine };
