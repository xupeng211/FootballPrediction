/**
 * Event Simulator - V163.Diagnostic Human Behavior Simulation
 * ============================================================
 *
 * Human-like event simulation for anti-detection.
 * Extracted from SurgicalInteraction.js for modular architecture.
 *
 * V145.000 Features:
 * - Random stabilization (2.5s-4.8s)
 * - Pixel jitter (±3px) simulating hand tremor
 * - Random render wait (800-1200ms)
 *
 * V163.Diagnostic Features:
 * - Multi-point trigger strategy (hover → click → dispatchEvent)
 * - State-driven waiting with dynamic predicates
 *
 * @module services/modules/event_simulator
 * @version V1.0
 * @since 2026-01-31
 * @author [Genesis.Standardization]
 */

'use strict';

/**
 * Event Simulator - Human behavior simulation
 */
class EventSimulator {
    /**
     * @param {Object} page - Playwright page object
     * @param {Object} config - Configuration object
     * @param {number} config.humanizedStabilizeMinMs - Min random stabilization (ms)
     * @param {number} config.humanizedStabilizeMaxMs - Max random stabilization (ms)
     * @param {number} config.pixelJitterRangePx - Pixel jitter range (±px)
     * @param {number} config.modalRetryCount - Max retry attempts
     * @param {string} config.logLevel - Logging level
     */
    constructor(page, config = {}) {
        this.page = page;

        // Load humanized interaction config from environment
        const humanizedStabilizeMinMs = parseInt(process.env.HUMANIZED_STABILIZE_MIN_MS) || 2500;
        const humanizedStabilizeMaxMs = parseInt(process.env.HUMANIZED_STABILIZE_MAX_MS) || 4800;
        const pixelJitterRangePx = parseInt(process.env.PIXEL_JITTER_RANGE_PX) || 3;

        this.config = {
            humanizedStabilizeMinMs,
            humanizedStabilizeMaxMs,
            pixelJitterRangePx,
            modalRetryCount: config.modalRetryCount || 2,
            logLevel: config.logLevel || 'info'
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
            console.log(`[V145.000] 📏 Pixel jitter: (${offsetX}, ${offsetY})px`);
        }

        return { offsetX, offsetY };
    }

    /**
     * V145.000: Humanized Reliable Hover with Anti-Detection Features
     * V163.Diagnostic: Multi-point trigger strategy
     *
     * @param {ElementHandle} cell - The odds cell to hover
     * @param {Object} randomRenderWaitFn - Function for random render wait
     * @param {number} cellIndex - Cell index for logging
     * @param {string} axisName - Axis name (home/draw/away)
     * @param {number} totalCells - Total cells for logging
     * @returns {Promise<Object>} Result object with success flag and retry count
     */
    async performReliableHover(cell, randomRenderWaitFn, cellIndex, axisName, totalCells) {
        const maxRetries = this.config.modalRetryCount;
        let retryCount = 0;
        let modalDetected = false;
        let triggerMethod = null;

        console.log(`[V145.000] 🎯 HUMANIZED HOVER: Cell ${cellIndex + 1}/${totalCells} (${axisName})`);

        // V163.Diagnostic: Trigger strategies based on probe results
        const triggerStrategies = [
            { name: 'primary-click', type: 'click', timeout: 2500 },
            { name: 'fallback-mouseover', type: 'dispatch', event: 'mouseover', timeout: 2000 }
        ];

        for (let attempt = 0; attempt <= maxRetries; attempt++) {
            const strategy = triggerStrategies[Math.min(attempt, triggerStrategies.length - 1)];

            try {
                // Execute trigger strategy
                if (strategy.type === 'click') {
                    console.log(`[V163.Diagnostic] ⚡ Executing PRIMARY CLICK`);
                    await cell.click({ force: true, delay: 50 });
                } else if (strategy.type === 'dispatch') {
                    console.log(`[V163.Diagnostic] ⚡ Dispatching fallback event: ${strategy.event}`);
                    await cell.dispatchEvent(strategy.event, { bubbles: true, cancelable: true });
                }

                // State-driven wait for modal content
                console.log(`[V163.LeanSlam] ⏱️  State-driven wait (max ${strategy.timeout}ms)...`);
                let titleDetected = false;

                try {
                    await this.page.waitForFunction(() => {
                        const modal = document.querySelector('.tooltip, [role="dialog"], .modal-content, [class*="popup"], [class*="dialog"]');
                        if (!modal) return false;

                        const hasRows = modal.querySelectorAll('tr, .row, [class*="row"]').length > 0;
                        const hasTimePattern = /\d{1,2}\s+\w+\.?\s*,?\s*\d{1,2}:\d{2}/.test(modal.textContent);

                        return (hasRows || hasTimePattern) && modal.offsetParent !== null;
                    }, { timeout: strategy.timeout });

                    titleDetected = true;
                    console.log(`[V163.LeanSlam] ✅ Modal content detected via ${strategy.name}`);

                } catch (timeoutError) {
                    titleDetected = false;
                }

                if (titleDetected) {
                    if (!triggerMethod) {
                        triggerMethod = strategy.name;
                    }
                    console.log(`[V148.000] ✅ SUCCESS: Modal detected via '${triggerMethod}' on attempt ${attempt + 1}`);

                    // V150.000: Deep render wait for full trajectory extraction
                    await randomRenderWaitFn();

                    modalDetected = true;
                    break;
                } else {
                    if (attempt < maxRetries) {
                        console.log(`[V148.000] ⚠️  No modal via ${strategy.name}, will retry...`);
                        retryCount++;

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
            triggerMethod: triggerMethod
        };
    }
}

module.exports = { EventSimulator };
