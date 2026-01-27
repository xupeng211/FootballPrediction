/**
 * SurgicalInteraction - V148.000 Modal Remapping
 * =============================================
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
 * @module services/SurgicalInteraction
 * @version V148.000
 * @since 2026-01-28
 * @author Principal Frontend Reverse Engineer
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
     * Enhanced with V145.000 physical removal logging
     *
     * @returns {Promise<boolean>} True if overlays were removed
     */
    async handleOverlays() {
        try {
            console.log('[V145.000] 🧹 PHYSICAL CLEANUP START');
            console.log('[V145.000] Force remove config:', this.config.forceRemoveOverlays);

            // Wait briefly for overlay to appear
            await this.page.waitForTimeout(500);

            let removedCount = 0;
            const removedElements = [];

            if (this.config.forceRemoveOverlays) {
                console.log('[V145.000] 💀 BRUTE FORCE MODE ENGAGED');

                // V145.000: Use OddsPortalSelectors for purge script generation
                const purgeScript = OddsPortalSelectors.generatePurgeScript();
                const purgeResult = await this.page.evaluate(purgeScript);

                removedCount = purgeResult.count;
                removedElements = purgeResult.removed;

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

        console.log(`[V145.000] 🎯 HUMANIZED HOVER: Cell ${cellIndex + 1}/${totalCells} (${axisName})`);
        console.log(`[V145.000] Config: forceRemove=${this.config.forceRemoveOverlays}, scrollBeforeHover=${this.config.scrollIntoViewBeforeHover}`);

        for (let attempt = 0; attempt <= maxRetries; attempt++) {
            try {
                // V145.000: First attempt preparation
                if (attempt === 0) {
                    // Step 1: scrollIntoViewIfNeeded with settle delay
                    if (this.config.scrollIntoViewBeforeHover) {
                        console.log(`[V145.000] 📜 Scrolling into view...`);
                        await cell.scrollIntoViewIfNeeded();
                        await this.scrollSettle(); // V145.000: 800ms settle delay
                        console.log(`[V145.000] ✅ Scroll settled, element in viewport`);
                    }

                    // Get bounding box for pixel jitter calculation
                    boundingBox = await cell.boundingBox();
                    console.log(`[V145.000] 📍 Cell position: x=${Math.round(boundingBox.x)}, y=${Math.round(boundingBox.y)}, ` +
                                `w=${Math.round(boundingBox.width)}, h=${Math.round(boundingBox.height)}`);
                }

                // Step 2: Calculate hover position with pixel jitter
                const jitter = this.generatePixelJitter();

                // V145.000: Calculate center point with jitter offset
                const centerX = boundingBox.x + boundingBox.width / 2;
                const centerY = boundingBox.y + boundingBox.height / 2;

                // Add jitter to center point
                const hoverX = centerX + jitter.offsetX;
                const hoverY = centerY + jitter.offsetY;

                if (attempt > 0) {
                    // Retry attempt: larger pixel shift (4-8px range)
                    const shiftMultiplier = attempt + 1;
                    const shiftX = jitter.offsetX * shiftMultiplier;
                    const shiftY = jitter.offsetY * shiftMultiplier;
                    console.log(`[V145.000] 🔄 Retry #${attempt}: shift (${shiftX.toFixed(1)}, ${shiftY.toFixed(1)})px`);
                    await this.page.mouse.move(hoverX + shiftX, hoverY + shiftY);
                } else {
                    // Initial hover with pixel jitter
                    console.log(`[V145.000) 🎯 Hover at (${hoverX.toFixed(1)}, ${hoverY.toFixed(1)}) with jitter (${jitter.offsetX}, ${jitter.offsetY})`);
                    await this.page.mouse.move(hoverX, hoverY);
                }

                // V145.000: Random stabilization instead of fixed delay
                const actualDelay = await this.randomStabilize();
                console.log(`[V145.000] ⏱️  Human-like stabilization: ${actualDelay}ms`);

                // V148.000: Multi-layer wait strategy - TARGET REDIRECTED
                // Phase 1: Wait for "Odds movement" title to appear
                const titleDetected = await this.detectModalWithTitle();

                if (titleDetected) {
                    console.log(`[V148.000] ✅ SUCCESS: Modal detected via 'Odds movement' title on attempt ${attempt + 1}`);

                    // V150.000: Deep render wait for full trajectory extraction
                    // Wait for React SPA to populate historical odds data (800-1200ms)
                    await this.randomRenderWait();

                    modalDetected = true;
                    break;
                } else {
                    if (attempt < maxRetries) {
                        console.log(`[V148.000] ⚠️  No modal, will retry...`);
                        retryCount++;
                    } else {
                        console.log(`[V148.000] ❌ FAIL: No modal after ${maxRetries + 1} attempts`);
                    }
                }

            } catch (error) {
                if (attempt < maxRetries) {
                    console.log(`[V145.000] ⚠️  Hover error on attempt ${attempt + 1}: ${error.message}`);
                    retryCount++;
                } else {
                    console.log(`[V145.000] ❌ FATAL: Hover failed after ${maxRetries + 1} attempts: ${error.message}`);
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
     * V148.000: Detect modal by "Odds movement" title (TARGET REDIRECTED)
     *
     * Based on V147 competitive analysis, the actual data modal contains
     * an h3 heading with "Odds movement" text. This method implements
     * multi-layer wait strategy to detect this modal.
     *
     * @returns {Promise<boolean>} True if modal is detected
     */
    async detectModalWithTitle() {
        const timeoutConfig = this.config.modalTimeoutConfig;

        if (this.config.logLevel === 'debug') {
            console.log(`[V148.000] 🔍 Looking for 'Odds movement' modal...`);
        }

        try {
            // V148.000: Multi-layer wait strategy
            // Phase 1: Wait for "Odds movement" title to appear
            const titleSelector = this.config.modalConfig.titleSelector;

            try {
                await this.page.waitForSelector(titleSelector, {
                    timeout: timeoutConfig.titleWait,
                    state: 'visible'
                });

                if (this.config.logLevel === 'debug') {
                    console.log(`[V148.000] ✅ Found 'Odds movement' title`);
                }

                // Phase 2: Verify we can get the modal container
                // V149.000: Updated with correct container selector based on diagnostic findings
                const modalExists = await this.page.evaluate((titleSel) => {
                    const titleElement = document.querySelector(titleSel);
                    if (!titleElement) return false;

                    // V149.000: The actual modal container is .tooltip (not [role="dialog"])
                    // Parent chain: div.height-content → div.flex → div.tooltip
                    const modal = titleElement.closest('.tooltip, [role="dialog"], .modal-content, [class*="popup"]');
                    return modal && modal.offsetParent !== null;
                }, titleSelector);

                if (modalExists) {
                    if (this.config.logLevel === 'debug') {
                        console.log(`[V148.000] ✅ Modal container verified`);
                    }
                    return true;
                }

            } catch (waitError) {
                if (this.config.logLevel === 'debug') {
                    console.log(`[V148.000] ⚠️  Title wait timeout: ${waitError.message}`);
                }
            }

            // Phase 3: Fallback - try container-based detection
            if (this.config.logLevel === 'debug') {
                console.log(`[V148.000] 🔍 Trying fallback container detection...`);
            }

            // V149.000: Updated container selectors with .tooltip as primary
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
}

module.exports = { SurgicalInteraction };
