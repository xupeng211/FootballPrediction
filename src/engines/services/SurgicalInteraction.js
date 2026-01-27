/**
 * SurgicalInteraction - V141.000 Refactored Module
 * =====================================================
 *
 * Browser interaction utilities for overlay handling and hover operations.
 * Extracted from QuantHarvester.js for modular architecture.
 *
 * @module services/SurgicalInteraction
 * @version V141.000
 * @since 2026-01-27
 * @author Senior Lead Software Architect (Refactoring Specialist)
 *
 * Features:
 * - BRUTE FORCE overlay removal (V133.000)
 * - Reliable hover with pixel-shift retry (V136.000)
 * - scrollIntoViewIfNeeded support (V138.000)
 * - Modular selectors integration
 */

'use strict';

const { OddsPortalSelectors } = require('../selectors/OddsPortalSelectors');

/**
 * SurgicalInteraction - Manages browser interactions
 */
class SurgicalInteraction {
    /**
     * @param {Object} page - Playwright page object
     * @param {Object} config - Configuration object
     * @param {boolean} config.forceRemoveOverlays - Enable brute force overlay removal
     * @param {boolean} config.scrollIntoViewBeforeHover - Enable scroll before hover
     * @param {number} config.hoverStabilizeMs - Stabilization delay after hover (ms)
     * @param {number} config.modalRetryCount - Max retry attempts for hover
     * @param {string} config.logLevel - Logging level
     */
    constructor(page, config = {}) {
        this.page = page;
        this.config = {
            forceRemoveOverlays: config.forceRemoveOverlays || false,
            scrollIntoViewBeforeHover: config.scrollIntoViewBeforeHover || false,
            hoverStabilizeMs: config.hoverStabilizeMs || 1500,
            modalRetryCount: config.modalRetryCount || 2,
            logLevel: config.logLevel || 'info'
        };
    }

    /**
     * V138.000: Handle overlays - BRUTE FORCE PURGE with Modular Selectors
     * V132.100 Finding: OneTrust popup was hidden but not removed, blocking hover interactions
     * V138.000 Enhancement: Added .overlay-bookie-modal support (missing in OddsHarvester)
     * Solution: Physical DOM deletion using OddsPortalSelectors
     *
     * @returns {Promise<boolean>} True if overlays were removed
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
     * V127.000: Randomized jitter wait (human behavior simulation)
     * @param {number} min - Minimum wait time (ms)
     * @param {number} jitter - Jitter range (ms)
     * @returns {Promise<void>}
     */
    async jitterWait(min = 2000, jitter = 1500) {
        const delay = Math.floor(Math.random() * jitter) + min;
        await this.page.waitForTimeout(delay);
    }
}

module.exports = { SurgicalInteraction };
