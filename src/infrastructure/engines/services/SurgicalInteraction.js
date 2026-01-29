/**
 * SurgicalInteraction - V158.000 Modal Trigger Mechanism Repair
 * ============================================================
 *
 * Browser interaction utilities with anti-detection enhancements.
 * V145.000 Features:
 * - Human-like random stabilization (2.5s-4.8s)
 * - Pixel jitter (±3px) simulating hand tremor
 * - Scroll settle delay (800ms) for page rendering
 * - Physical overlay removal with detailed logging
 *
 * V146.000 Features:
 * - React async rendering wait (waitForSelector)
 * - Dynamic content detection for SPA architecture
 *
 * V148.000 Features:
 * - Target redirected: "Odds movement" title-based modal detection
 * - Multi-layer wait strategy for React SPA
 * - Configuration decoupling via ModalSelectorConfig
 *
 * V158.000 Features (P0 BLOCKER FIX):
 * - OneTrust cookie banner aggressive removal
 * - Z-index based overlay purge (>1000 non-data containers)
 * - Multi-point trigger strategy (hover → click → dispatchEvent)
 * - Physical center offset testing (top-left, center, bottom-right)
 * - Real-time polling for [role="dialog"] and .tooltip
 * - Enhanced selector calibration (broader div search)
 * - 2-second timeout with click degradation
 *
 * V160.000 Features:
 * - extractProviderNameFromCell() - Row-to-Shop identity bridge
 * - Multi-level parent row traversal for provider detection
 * - Comprehensive selector fallback strategy
 *
 * @module services/SurgicalInteraction
 * @version V158.000 (P0 Fix)
 * @since 2026-01-28
 * @author Senior Lead Interaction Engineer (Playwright Automation Specialist)
 */

'use strict';

const { OddsPortalSelectors } = require('../selectors/OddsPortalSelectors');
const { buildModalSelector, getModalTimeoutConfig, getDialogContainerSelectors } = require('../config/ModalSelectorConfig');

/**
 * SurgicalInteraction - Manages browser interactions with human-like behavior
 */
class SurgicalInteraction {
    /**
     * @param {Object} page - Playwright page object
     * @param {Object} config - Configuration object
     * @param {boolean} config.forceRemoveOverlays - Enable brute force overlay removal
     * @param {boolean} config.scrollIntoViewBeforeHover - Enable scroll before hover
     * @param {number} config.hoverStabilizeMs - DEPRECATED - Use humanizedStabilize instead
     * @param {number} config.modalRetryCount - Max retry attempts for hover
     * @param {number} config.humanizedStabilizeMinMs - Min random stabilization (ms)
     * @param {number} config.humanizedStabilizeMaxMs - Max random stabilization (ms)
     * @param {number} config.pixelJitterRangePx - Pixel jitter range (±px)
     * @param {number} config.scrollSettleDelayMs - Scroll settle delay (ms)
     * @param {string} config.logLevel - Logging level
     */
    constructor(page, config = {}) {
        this.page = page;

        // V145.000: Load humanized interaction config from environment
        const humanizedStabilizeMinMs = parseInt(process.env.HUMANIZED_STABILIZE_MIN_MS) || 2500;
        const humanizedStabilizeMaxMs = parseInt(process.env.HUMANIZED_STABILIZE_MAX_MS) || 4800;
        const pixelJitterRangePx = parseInt(process.env.PIXEL_JITTER_RANGE_PX) || 3;
        const scrollSettleDelayMs = parseInt(process.env.SCROLL_SETTLE_DELAY_MS) || 800;

        // V148.000: Load modal selector configuration
        const modalConfig = buildModalSelector('title-based');

        this.config = {
            forceRemoveOverlays: config.forceRemoveOverlays !== undefined
                ? config.forceRemoveOverlays
                : (process.env.FORCE_REMOVE_OVERLAYS === 'true'),
            scrollIntoViewBeforeHover: config.scrollIntoViewBeforeHover !== undefined
                ? config.scrollIntoViewBeforeHover
                : (process.env.SCROLL_INTO_VIEW_BEFORE_HOVER === 'true'),
            hoverStabilizeMs: config.hoverStabilizeMs || 1500, // Legacy fallback
            modalRetryCount: config.modalRetryCount || 2,
            logLevel: config.logLevel || 'info',
            // V145.000: Humanized interaction parameters
            humanizedStabilizeMinMs,
            humanizedStabilizeMaxMs,
            pixelJitterRangePx,
            scrollSettleDelayMs,
            // V148.000: Modal detection configuration
            modalConfig,
            modalTimeoutConfig: getModalTimeoutConfig()
        };
    }

    /**
     * V145.000: Random stabilization - simulates human response time
     * @param {number} customMin - Optional custom minimum (ms)
     * @param {number} customMax - Optional custom maximum (ms)
     * @returns {Promise<number>} Actual delay time (ms)
     */
    async randomStabilize(customMin = null, customMax = null) {
        const minMs = customMin || this.config.humanizedStabilizeMinMs;
        const maxMs = customMax || this.config.humanizedStabilizeMaxMs;

        const delay = Math.floor(Math.random() * (maxMs - minMs + 1)) + minMs;

        if (this.config.logLevel === 'debug') {
            console.log(`[V145.000] 🎲 Random stabilization: ${delay}ms (range: ${minMs}-${maxMs}ms)`);
        }

        await this.page.waitForTimeout(delay);
        return delay;
    }

    /**
     * V150.000: Random render wait for deep trajectory extraction
     * Wait for React SPA to render full trajectory data (800-1200ms)
     * This gives the modal enough time to populate historical odds data
     *
     * @returns {Promise<number>} Actual wait time (ms)
     */
    async randomRenderWait() {
        const minMs = 800;
        const maxMs = 1200;
        const delay = Math.floor(Math.random() * (maxMs - minMs + 1)) + minMs;

        if (this.config.logLevel === 'debug') {
            console.log(`[V150.000] 🎨 Deep render wait: ${delay}ms (range: ${minMs}-${maxMs}ms)`);
        }

        await this.page.waitForTimeout(delay);
        return delay;
    }

    /**
     * V145.000: Generate pixel jitter - simulates hand tremor
     * @param {number} range - Pixel range (default: from config)
     * @returns {Object} X and Y offset values
     */
    generatePixelJitter(range = null) {
        const jitterRange = range || this.config.pixelJitterRangePx;
        const offsetX = Math.floor(Math.random() * (jitterRange * 2 + 1)) - jitterRange;
        const offsetY = Math.floor(Math.random() * (jitterRange * 2 + 1)) - jitterRange;

        if (this.config.logLevel === 'debug') {
            console.log(`[V145.000) 📏 Pixel jitter: (${offsetX}, ${offsetY})px`);
        }

        return { offsetX, offsetY };
    }

    /**
     * V146.000: Wait for React async rendering to complete
     * Ensures .odds-cell elements are present before proceeding
     *
     * @param {number} timeout - Maximum wait time (milliseconds), default from config
     * @returns {Promise<boolean>} True if cells rendered successfully
     */
    async waitForReactRender(timeout = null) {
        const waitTimeout = timeout || this.config.reactRenderTimeoutMs || 10000;

        if (this.config.logLevel === 'debug') {
            console.log(`[V146.000] ⏳ Waiting for React render: ${waitTimeout}ms timeout...`);
        }

        try {
            // V146.000: Wait for odds cells to be present in DOM
            await this.page.waitForSelector('[class*="odds-cell"]', {
                timeout: waitTimeout,
                state: 'attached'
            });

            if (this.config.logLevel === 'debug') {
                console.log(`[V146.000] ✅ React render complete - odds cells detected`);
            }

            return true;
        } catch (error) {
            console.log(`[V146.000] ⚠️  React render timeout: ${error.message}`);
            // Don't fail - cells may render later
            return false;
        }
    }

    /**
     * V145.000: Scroll settle - give page time to render after scrolling
     * @returns {Promise<void>}
     */
    async scrollSettle() {
        const delay = this.config.scrollSettleDelayMs;

        if (this.config.logLevel === 'debug') {
            console.log(`[V145.000] 📜 Scroll settling: ${delay}ms...`);
        }

        await this.page.waitForTimeout(delay);
    }

    /**
     * V145.000: Handle overlays - BRUTE FORCE PURGE with detailed logging
     * V158.000: Enhanced OneTrust cookie banner aggressive removal
     * V158.000: Z-index based overlay purge (>1000 non-data containers)
     *
     * @returns {Promise<boolean>} True if overlays were removed
     */
    async handleOverlays() {
        try {
            console.log('[V145.000] 🧹 PHYSICAL CLEANUP START');
            console.log('[V145.000] Force remove config:', this.config.forceRemoveOverlays);

            // [V162.Precision] Environment Initialization: CSS Hiding (Surgical Mode)
            await this.page.addStyleTag({
                content: `
                    #onetrust-banner-sdk, .onetrust-pc-dark-filter,
                    [id*="onetrust"], [class*="ot-sdk"] {
                        display: none !important;
                        visibility: hidden !important;
                        pointer-events: none !important;
                    }
                `
            });
            console.log('[V162.Precision] 🛡️ CSS Shield Activated: OneTrust hidden');

            // Wait briefly for overlay to appear
            await this.page.waitForTimeout(500);

            let removedCount = 0;
            const removedElements = [];

            if (this.config.forceRemoveOverlays) {
                console.log('[V145.000] 💀 BRUTE FORCE MODE ENGAGED');

                // V158.000: AGGRESSIVE OneTrust Removal - try multiple methods
                console.log('[V158.000] 🎯 TARGET: OneTrust Cookie Banner (z-index: 2147483645)');

                // Method 1: Try clicking "Reject All" button
                const oneTrustReject = await this.page.evaluate(() => {
                    const rejectBtn = document.querySelector('#onetrust-reject-all-handler');
                    if (rejectBtn && rejectBtn.offsetParent !== null) {
                        rejectBtn.click();
                        return true;
                    }
                    return false;
                });

                if (oneTrustReject) {
                    console.log('[V158.000] ✅ OneTrust: Clicked "Reject All" button');
                    await this.page.waitForTimeout(1000);
                }

                // Method 2: Remove OneTrust container directly
                const oneTrustPurge = await this.page.evaluate(() => {
                    const selectors = [
                        '#onetrust-banner-sdk',
                        '#onetrust-consent-sdk',
                        '.ot-sdk-container',
                        '[id*="onetrust"]',
                        '[class*="ot-sdk"]'
                    ];

                    let count = 0;
                    for (const sel of selectors) {
                        const elements = document.querySelectorAll(sel);
                        elements.forEach(el => {
                            el.remove();
                            count++;
                        });
                    }
                    return count;
                });

                if (oneTrustPurge > 0) {
                    console.log(`[V158.000] 🔥 OneTrust: Purged ${oneTrustPurge} containers`);
                    removedCount += oneTrustPurge;
                    removedElements.push('OneTrust containers');
                }

                // V158.000: Z-INDEX BASED OVERLAY PURGE (NEW)
                // Find and remove all elements with z-index > 1000 that are not data containers
                const zIndexPurge = await this.page.evaluate(() => {
                    const allElements = document.querySelectorAll('*');
                    const removed = [];
                    const dataKeywords = ['odds', 'bet', 'match', 'team', 'score', 'time', 'league', 'sport'];

                    for (const el of allElements) {
                        try {
                            const style = window.getComputedStyle(el);
                            const zIndex = parseInt(style.zIndex);

                            // Check if element has high z-index and is visible
                            if (zIndex > 1000 && el.offsetParent !== null) {
                                const text = el.textContent?.toLowerCase() || '';
                                const className = el.className?.toLowerCase() || '';

                                // Skip if it looks like a data container
                                const isDataContainer = dataKeywords.some(kw =>
                                    text.includes(kw) || className.includes(kw)
                                );

                                if (!isDataContainer) {
                                    removed.push({
                                        tag: el.tagName,
                                        class: className,
                                        zIndex: zIndex,
                                        text: text.substring(0, 50)
                                    });
                                    el.remove();
                                }
                            }
                        } catch (e) {
                            // Continue on error
                        }
                    }

                    return removed;
                });

                if (zIndexPurge.length > 0) {
                    console.log(`[V158.000] 🔥 Z-INDEX PURGE: Removed ${zIndexPurge.length} high-z overlays`);
                    zIndexPurge.slice(0, 5).forEach(item => {
                        console.log(`[V158.000]   - ${item.tag}.${item.class} (z-index: ${item.zIndex})`);
                    });
                    removedCount += zIndexPurge.length;
                    removedElements.push('High-z-index overlays');
                }

                // V145.000: Use OddsPortalSelectors for general overlay purge
                const purgeScript = OddsPortalSelectors.generatePurgeScript();
                const purgeResult = await this.page.evaluate(purgeScript);

                removedCount += purgeResult.count;
                removedElements.push(...purgeResult.removed);

                // V145.000: Enhanced logging with specific class names
                console.log(`[V145.000] 🔪 PHYSICAL PURGE COMPLETE`);
                console.log(`[V145.000] ✅ 已物理粉碎遮罩层: ${removedElements.slice(0, 5).join(', ')}${removedElements.length > 5 ? '...' : ''}`);
                console.log(`[V145.000] Total nodes removed: ${removedCount}`);

                // Log specific overlay types found
                if (removedElements.some(r => r.includes('bookie'))) {
                    console.log('[V145.000] 🔥 SMOKED: .overlay-bookie-modal');
                }
                if (removedElements.some(r => r.includes('onetrust'))) {
                    console.log('[V145.000] 🔥 SMOKED: #onetrust-banner');
                }
                if (removedElements.some(r => r.includes('consent'))) {
                    console.log('[V145.000] 🔥 SMOKED: Cookie consent banner');
                }

                if (removedCount > 0) {
                    console.log(`[V145.000] ✅ OVERLAY PURGE: ${removedCount} nodes eliminated`);
                } else {
                    console.log('[V145.000] ℹ️  No overlays detected - clean slate');
                }
            } else {
                console.log('[V145.000) ⚠️  WARNING: Force remove DISABLED - using click fallback');
                // Fallback click-based approach...
            }

            return removedCount > 0;

        } catch (error) {
            console.warn(`[V145.000] ❌ Overlay handling error: ${error.message}`);
            return false;
        }
    }

    /**
     * V145.000: Humanized Reliable Hover with Anti-Detection Features
     * V158.000: Multi-point trigger strategy (hover → click → dispatchEvent)
     * V158.000: 2-second timeout with click degradation
     * V158.000: Real-time polling for modal detection
     * V145.000 Enhancements:
     * - Random stabilization (2.5s-4.8s) instead of fixed 1.5s
     * - Pixel jitter (±3px) on all hover operations
     * - Scroll settle delay (800ms) after scrollIntoView
     * - Enhanced logging for debugging
     *
     * @param {ElementHandle} cell - The odds cell to hover
     * @param {number} cellIndex - Cell index for logging
     * @param {string} axisName - Axis name (home/draw/away)
     * @param {number} totalCells - Total cells for logging
     * @returns {Promise<Object>} Result object with success flag and retry count
     */
    async performReliableHover(cell, cellIndex, axisName, totalCells) {
        const maxRetries = this.config.modalRetryCount;
        let retryCount = 0;
        let modalDetected = false;
        let boundingBox = null;
        let triggerMethod = null;  // V158.000: Track which trigger method worked

        console.log(`[V145.000] 🎯 HUMANIZED HOVER: Cell ${cellIndex + 1}/${totalCells} (${axisName})`);
        console.log(`[V145.000] Config: forceRemove=${this.config.forceRemoveOverlays}, scrollBeforeHover=${this.config.scrollIntoViewBeforeHover}`);

        // [V163.Diagnostic] Logic Hardening based on Probe Results
        // Proved: 'click' works (1629ms latency), 'mouseenter'/'mouseover' failed.
        // Strategy: 1. Click (Primary) -> 2. Mouseover (Fallback)
        const triggerStrategies = [
            { name: 'primary-click', type: 'click', timeout: 2500 }, // Increased timeout to cover 1.6s latency
            { name: 'fallback-mouseover', type: 'dispatch', event: 'mouseover', timeout: 2000 }
        ];

        for (let attempt = 0; attempt <= maxRetries; attempt++) {
            // V158.000: Try different trigger strategies
            const strategy = triggerStrategies[Math.min(attempt, triggerStrategies.length - 1)];

            try {
                // [V163.Diagnostic] Trigger Execution
                if (strategy.type === 'click') {
                    console.log(`[V163.Diagnostic] ⚡ Executing PRIMARY CLICK`);
                    // Use force: true to bypass any remaining overlays
                    await cell.click({ force: true, delay: 50 }); // Add slight delay for realism
                } else if (strategy.type === 'dispatch') {
                    console.log(`[V163.Diagnostic] ⚡ Dispatching fallback event: ${strategy.event}`);
                    await cell.dispatchEvent(strategy.event, { bubbles: true, cancelable: true });
                }

                // [V163.LeanSlam] State-Driven Waiting (Dynamic Predicate)
                console.log(`[V163.LeanSlam] ⏱️  State-driven wait (max ${strategy.timeout}ms)...`);
                let titleDetected = false;
                
                try {
                    await this.page.waitForFunction(() => {
                        // 1. Find potential modal container
                        const modal = document.querySelector('.tooltip, [role="dialog"], .modal-content, [class*="popup"], [class*="dialog"]');
                        if (!modal) return false;

                        // 2. Predicate: Check for data presence (rows or time patterns)
                        // Look for specific odds history rows or time patterns
                        const hasRows = modal.querySelectorAll('tr, .row, [class*="row"]').length > 0;
                        // Strict time pattern: "24 May 12:00" or similar
                        const hasTimePattern = /\d{1,2}\s+\w+\.?\s*,?\s*\d{1,2}:\d{2}/.test(modal.textContent);
                        
                        return (hasRows || hasTimePattern) && modal.offsetParent !== null; // Visible
                    }, { timeout: strategy.timeout }); // Use strategy timeout (2.5s for click)

                    titleDetected = true;
                    console.log(`[V163.LeanSlam] ✅ Modal content detected via ${strategy.name}`);

                } catch (timeoutError) {
                    // console.log(`[V163.LeanSlam] ⚠️  Wait timeout: No data appeared within ${strategy.timeout}ms`);
                    titleDetected = false;
                }

                if (titleDetected) {
                    if (!triggerMethod) {
                        triggerMethod = strategy.name;
                    }
                    console.log(`[V148.000] ✅ SUCCESS: Modal detected via '${triggerMethod}' on attempt ${attempt + 1}`);

                    // V150.000: Deep render wait for full trajectory extraction
                    await this.randomRenderWait();

                    modalDetected = true;
                    break;
                } else {
                    if (attempt < maxRetries) {
                        console.log(`[V148.000] ⚠️  No modal via ${strategy.name}, will retry...`);
                        retryCount++;

                        // Move mouse away between attempts
                        await this.page.mouse.move(0, 0);
                        await this.page.waitForTimeout(500);
                    } else {
                        console.log(`[V148.000] ❌ FAIL: No modal after ${maxRetries + 1} attempts`);
                    }
                }

            } catch (error) {
                if (attempt < maxRetries) {
                    console.log(`[V145.000] ⚠️  ${strategy.name} error on attempt ${attempt + 1}: ${error.message}`);
                    retryCount++;
                } else {
                    console.log(`[V145.000] ❌ FATAL: All trigger methods failed: ${error.message}`);
                    break;
                }
            }
        }

        return {
            success: modalDetected,
            retries: retryCount,
            attempt: maxRetries + 1,
            triggerMethod: triggerMethod  // V158.000: Report which method worked
        };
    }

    /**
     * V148.000: Detect modal by "Odds movement" title (TARGET REDIRECTED)
     * V158.000: Enhanced selector calibration with broader div search
     *
     * Based on V147 competitive analysis, the actual data modal contains
     * an h3 heading with "Odds movement" text. This method implements
     * multi-layer wait strategy to detect this modal.
     *
     * V158.000 Enhancements:
     * - Search ALL divs for "Odds movement" content (broader search)
     * - Match any heading containing "Odds" or "movement"
     * - Look for time pattern data in modal content
     *
     * @returns {Promise<boolean>} True if modal is detected
     */
    async detectModalWithTitle() {
        if (this.config.logLevel === 'debug') {
            console.log(`[V148.000] 🔍 Looking for 'Odds movement' modal...`);
        }

        try {
            // V150.001: Use only native DOM methods (based on V149 diagnostic success)
            // Don't use Playwright pseudo-selectors in page.evaluate()
            const result = await this.page.evaluate(() => {
                // Find h3 with "Odds movement" text using native DOM methods
                const h3Elements = document.querySelectorAll('h3');
                let titleElement = null;
                for (const h3 of h3Elements) {
                    if (h3.textContent && h3.textContent.includes('Odds movement')) {
                        titleElement = h3;
                        break;
                    }
                }

                if (!titleElement) {
                    return { foundTitle: false, foundModal: false };
                }

                // V149.000: The actual modal container is .tooltip (not [role="dialog"])
                // Parent chain: div.height-content → div.flex → div.tooltip
                const modal = titleElement.closest('.tooltip, [role="dialog"], .modal-content, [class*="popup"]');

                if (!modal) {
                    return { foundTitle: true, foundModal: false };
                }

                // Check if modal is visible
                const isVisible = modal.offsetParent !== null;

                return {
                    foundTitle: true,
                    foundModal: true,
                    isVisible
                };
            });

            if (result.foundTitle && result.foundModal && result.isVisible) {
                if (this.config.logLevel === 'debug') {
                    console.log(`[V148.000] ✅ Found 'Odds movement' title and modal container`);
                }
                return true;
            }

            if (result.foundTitle && !result.foundModal) {
                if (this.config.logLevel === 'debug') {
                    console.log(`[V148.000] ⚠️  Found title but no modal container`);
                }
            }

            // Fallback: Try container-based detection
            if (this.config.logLevel === 'debug') {
                console.log(`[V148.000] 🔍 Trying fallback container detection...`);
            }

            const containerSelectors = ['.tooltip', '[role="dialog"]', '.modal-content', '[class*="popup"]'];
            const containerExists = await this.page.evaluate((containerSels) => {
                for (const sel of containerSels) {
                    const el = document.querySelector(sel);
                    if (el && el.offsetParent !== null) {
                        // Check if it has odds data (time pattern)
                        const hasOdds = /\d{1,2}\s+\w+\.?\s*,?\s*\d{1,2}:\d{2}/.test(el.textContent);
                        if (hasOdds) {
                            return true;
                        }
                    }
                }
                return false;
            }, containerSelectors);

            if (containerExists) {
                if (this.config.logLevel === 'debug') {
                    console.log(`[V148.000] ✅ Found container with odds data`);
                }
                return true;
            }

            // V158.000: SELECTOR CALIBRATION - Broader div search (NEW)
            // If standard selectors fail, search ALL divs for "Odds movement" content
            if (this.config.logLevel === 'debug') {
                console.log(`[V158.000] 🔍 V158.000 Broader div search for 'Odds movement'...`);
            }

            const broadSearchResult = await this.page.evaluate(() => {
                // Search all headings for "Odds" or "movement"
                const allHeadings = document.querySelectorAll('h1, h2, h3, h4, h5, h6, .title, [class*="title"]');
                const oddsKeywords = ['odds', 'movement', 'history', 'opening', 'closing'];
                let foundHeading = null;

                for (const heading of allHeadings) {
                    const text = (heading.textContent || '').toLowerCase();
                    if (oddsKeywords.some(kw => text.includes(kw))) {
                        foundHeading = heading;
                        break;
                    }
                }

                if (!foundHeading) {
                    return { found: false, method: 'no-heading' };
                }

                // Search all parent divs for modal container
                let modalDiv = foundHeading.closest('div');
                let depth = 0;
                const maxDepth = 15;

                while (modalDiv && depth < maxDepth) {
                    const classList = Array.from(modalDiv.classList || []);
                    const hasModalClass = classList.some(c =>
                        c.includes('tooltip') ||
                        c.includes('modal') ||
                        c.includes('popup') ||
                        c.includes('dialog') ||
                        c.includes('overlay') ||
                        c.includes('movement')
                    );

                    // Check for time pattern data (indicates odds data)
                    const hasTimePattern = /\d{1,2}\s+\w+\.?\s*,?\s*\d{1,2}:\d{2}/.test(modalDiv.textContent);

                    if (hasModalClass || hasTimePattern) {
                        return {
                            found: true,
                            method: hasModalClass ? 'modal-class' : 'time-pattern',
                            className: classList.join(' '),
                            hasTimePattern: hasTimePattern
                        };
                    }

                    modalDiv = modalDiv.parentElement;
                    depth++;
                }

                // Last resort: Find any div with time pattern data that appeared recently
                const allDivs = document.querySelectorAll('div');
                for (const div of allDivs) {
                    if (div.offsetParent !== null) {
                        const hasTimePattern = /\d{1,2}\s+\w+\.?\s*,?\s*\d{1,2}:\d{2}/.test(div.textContent);
                        const text = (div.textContent || '').toLowerCase();
                        const hasOddsKeyword = oddsKeywords.some(kw => text.includes(kw));

                        if (hasTimePattern && hasOddsKeyword) {
                            return {
                                found: true,
                                method: 'any-div-with-pattern',
                                className: Array.from(div.classList || []).join(' ')
                            };
                        }
                    }
                }

                return { found: false, method: 'exhausted' };
            });

            if (broadSearchResult.found) {
                console.log(`[V158.000] ✅ V158.000 Broad search SUCCESS: method=${broadSearchResult.method}`);
                if (broadSearchResult.className) {
                    console.log(`[V158.000]    Target class: ${broadSearchResult.className}`);
                }
                return true;
            }

            if (this.config.logLevel === 'debug') {
                console.log(`[V148.000] ❌ No modal detected`);
            }
            return false;

        } catch (error) {
            console.error(`[V148.000] ❌ Modal detection error: ${error.message}`);
            return false;
        }
    }

    /**
     * V127.000: Randomized jitter wait (human behavior simulation)
     * DEPRECATED: Use randomStabilize() instead for human-like timing
     *
     * @param {number} min - Minimum wait time (ms)
     * @param {number} jitter - Jitter range (ms)
     * @returns {Promise<void>}
     */
    async jitterWait(min = 2000, jitter = 1500) {
        console.warn('[V145.000] ⚠️  jitterWait() is DEPRECATED, use randomStabilize() instead');
        const delay = Math.floor(Math.random() * jitter) + min;
        await this.page.waitForTimeout(delay);
    }

    /**
     * V160.000: Extract Provider Name from Parent Row (Identity Bridge)
     * ================================================================
     *
     * Extracts the bookmaker/provider name from the cell's parent row context.
     * This solves the "face blindness" issue where modal dialogs don't contain
     * provider identity information.
     *
     * @param {ElementHandle} cell - The odds cell element
     * @returns {Promise<string|null>} Provider name or null if not found
     *
     * @example
     * const providerName = await surgicalInteraction.extractProviderNameFromCell(cell);
     * // Returns: "Pinnacle", "bet365", "Bwin", etc.
     */
    async extractProviderNameFromCell(cell) {
        if (!cell) {
            console.log('[V160.000 Identity Bridge] ⚠️  No cell element provided');
            return null;
        }

        try {
            const providerName = await this.page.evaluate((cellElem) => {
                if (!cellElem) return null;

                // Strategy 1: Find parent row with expanded selectors
                let rowParent = cellElem.closest('tr, [class*="row"], .odds-row, li, .flex-row, [class*="group"], div.group');

                // Fallback: Traverse up to find row-like container
                if (!rowParent) {
                    let p = cellElem.parentElement;
                    let depth = 0;
                    while (p && depth < 8) {
                        const classList = Array.from(p.classList || []);
                        const tagName = p.tagName?.toLowerCase() || '';

                        // Check for row-like patterns
                        if (tagName === 'li' ||
                            tagName === 'tr' ||
                            classList.some(c => c.includes('row') ||
                                         c.includes('item') ||
                                         c.includes('group') ||
                                         c.includes('flex') ||
                                         c.includes('odds'))) {
                            rowParent = p;
                            break;
                        }
                        p = p.parentElement;
                        depth++;
                    }
                }

                if (!rowParent) return null;

                // Strategy 2: Comprehensive provider selectors
                const rowProviderSelectors = [
                    // Primary selectors
                    '.bookmaker-name',
                    '[class*="bookmaker"]',
                    '.provider-name',
                    '.name',
                    // Link-based selectors
                    'a[href*="/bookmaker/"]',
                    'a[href*="/bmakers/"]',
                    'a[href*="/bookie/"]',
                    // Text content selectors
                    'div[class*="text-"]',
                    'div[class*="name"]',
                    'span[class*="name"]',
                    // Image attributes
                    'img[alt*=" pinnacle" i], img[alt*="bet365" i], img[alt*="bwin" i]',
                    'img[alt*="william" i], img[alt*="unibet" i], img[alt*="1xbet" i], img[alt*="ladbrokes" i]',
                    // ARIA labels
                    '[aria-label*="bookmaker" i], [aria-label*="provider" i]'
                ];

                // Strategy 3: Try each selector with validation
                for (const sel of rowProviderSelectors) {
                    try {
                        const elem = rowParent.querySelector(sel);
                        if (elem) {
                            // Get text from element or attributes
                            let text = elem.textContent ||
                                       elem.getAttribute('alt') ||
                                       elem.getAttribute('aria-label') ||
                                       elem.getAttribute('title') || '';
                            text = text.trim();

                            // Validate: check length and exclude non-provider text
                            if (text && text.length > 1 && text.length < 50) {
                                const excludePatterns = [
                                    'Odds', 'movement', 'Opening', 'Current', 'History',
                                    'home', 'draw', 'away', 'win', 'lose', 'cancel',
                                    'slip', 'stake', 'return', 'payout', 'decimal',
                                    'fraction', 'american', ' asian'
                                ];
                                const hasExcluded = excludePatterns.some(p =>
                                    text.toLowerCase().includes(p.toLowerCase())
                                );

                                if (!hasExcluded) {
                                    return text;
                                }
                            }
                        }
                    } catch (e) {
                        // Continue to next selector
                    }
                }

                // Strategy 4: Pattern-based fallback - search for provider name patterns
                try {
                    const allText = rowParent.textContent || '';
                    const lines = allText.split('\n')
                        .map(l => l.trim())
                        .filter(l => l.length > 1 && l.length < 30);

                    // Provider name patterns (case-insensitive)
                    const providerPatterns = [
                        /pinnacle|pinny|pinn|平博/i,
                        /bet\s*365|b365|365\s*bet|365bet/i,
                        /bwin|b\s*-\s*win/i,
                        /william\s*hill|willhill|whill|威廉希尔/i,
                        /unibet|uni\s*bet/i,
                        /1xbet|1x\s*bet|xbet/i,
                        /ladbrokes|lad\s*brokes|lads|立博/i
                    ];

                    for (const line of lines) {
                        for (const pattern of providerPatterns) {
                            if (pattern.test(line)) {
                                // Extract just the provider name portion
                                const match = line.match(pattern)[0];
                                if (match && match.length < 30) {
                                    return match;
                                }
                            }
                        }
                    }
                } catch (e) {
                    // Fallback failed
                }

                return null;
            }, cell);

            if (this.config.logLevel === 'debug') {
                if (providerName) {
                    console.log(`[V160.000 Identity Bridge] ✅ Provider extracted: "${providerName}"`);
                } else {
                    console.log(`[V160.000 Identity Bridge] ⚠️  No provider name found in parent row`);
                }
            }

            return providerName;

        } catch (error) {
            console.warn(`[V160.000 Identity Bridge] ❌ Extraction error: ${error.message}`);
            return null;
        }
    }
}

module.exports = { SurgicalInteraction };
