/**
 * Event Simulator - V165.000 Genesis.HeartBypass
 * ================================================
 *
 * [Genesis.V164.Surgical_Upgrade] Event-Driven Interaction System
 *
 * Major Changes:
 * - DEPRECATED: Hardcoded waits (randomStabilize: 2500-4800ms, randomRenderWait: 800-1200ms)
 * - NEW: Event-driven state detection via waitForFunction()
 * - NEW: Memory-based data ready detection
 * - NEW: Zero-latency trigger when data is available
 *
 * Performance Improvement:
 * - Eliminated ~6s of hardcoded waits per interaction
 * - Replaced with 50ms polling for memory data readiness
 *
 * @module services/modules/event_simulator
 * @version V165.000
 * @since 2026-02-01
 * @author [Genesis.V164.Surgical_Upgrade]
 */

'use strict';

/**
 * V165.000: Memory-ready predicate function
 * Checks if window._TITAN_ARTERY_DATA has intercepted data
 */
const MEMORY_READY_PREDICATE = `
() => {
    const data = window._TITAN_ARTERY_DATA || [];
    return data.length > 0;
}
`;

/**
 * Event Simulator - V165.000 Event-Driven Edition
 */
class EventSimulator {
    /**
     * @param {Object} page - Playwright page object
     * @param {Object} config - Configuration object
     * @param {number} config.memoryReadyTimeout - Max wait for memory data (ms)
     * @param {number} config.statePollInterval - Polling interval (ms)
     * @param {string} config.logLevel - Logging level
     */
    constructor(page, config = {}) {
        this.page = page;

        // V165.000: Event-driven config
        this.config = {
            memoryReadyTimeout: config.memoryReadyTimeout || 3000,  // Reduced from 4800
            statePollInterval: config.statePollInterval || 50,      // 50ms polling
            modalRetryCount: config.modalRetryCount || 2,
            logLevel: config.logLevel || 'info'
        };
    }

    /**
     * V165.000: Wait for memory data to be ready
     * Event-driven - replaces randomStabilize()
     *
     * @returns {Promise<boolean>} True if memory data is ready
     */
    async waitForMemoryData() {
        if (this.config.logLevel === 'debug') {
            console.log(`[V165.000] ⏳ Waiting for memory data (max ${this.config.memoryReadyTimeout}ms)...`);
        }

        try {
            await this.page.waitForFunction(
                MEMORY_READY_PREDICATE,
                { polling: this.config.statePollInterval },
                this.config.memoryReadyTimeout
            );

            if (this.config.logLevel === 'debug') {
                console.log('[V165.000] ✅ Memory data READY - zero-wait trigger!');
            }

            return true;

        } catch (error) {
            if (this.config.logLevel === 'debug') {
                console.log('[V165.000] ⏱️  Memory data timeout (continuing anyway)...');
            }
            return false;
        }
    }

    /**
     * V165.000: Random stabilization (DEPRECATED - kept for compatibility)
     * Now just a lightweight check instead of hard wait
     *
     * @param {number} customMin - Ignored (for compatibility)
     * @param {number} customMax - Ignored (for compatibility)
     * @returns {Promise<number>} Actual delay time (0-100ms)
     */
    async randomStabilize(customMin = null, customMax = null) {
        console.warn('[V165.000] ⚠️  randomStabilize() is DEPRECATED, use waitForMemoryData() instead');

        // V165.000: Minimal wait instead of 2.5-4.8s
        const delay = Math.floor(Math.random() * 100);  // 0-100ms jitter

        if (this.config.logLevel === 'debug') {
            console.log(`[V165.000] 🎲 Minimal jitter: ${delay}ms (was 2500-4800ms)`);
        }

        await this.page.waitForTimeout(delay);
        return delay;
    }

    /**
     * V165.000: Random render wait (DEPRECATED - kept for compatibility)
     * Now uses waitForFunction for React render detection
     *
     * @returns {Promise<number>} Actual wait time (ms)
     */
    async randomRenderWait() {
        console.warn('[V165.000] ⚠️  randomRenderWait() is DEPRECATED, using event-driven detection');

        try {
            // V165.000: Wait for actual render instead of fixed 800-1200ms
            const startTime = Date.now();

            await this.page.waitForFunction(() => {
                // Check if odds cells are rendered and visible
                const cells = document.querySelectorAll('[class*="odds-cell"]');
                return cells.length > 0 && Array.from(cells).some(c => c.offsetParent !== null);
            }, { polling: this.config.statePollInterval }, 1000);

            const elapsed = Date.now() - startTime;

            if (this.config.logLevel === 'debug') {
                console.log(`[V165.000] 🎨 React render detected in ${elapsed}ms (was 800-1200ms)`);
            }

            return elapsed;

        } catch (error) {
            // Fallback to minimal wait
            const fallbackDelay = 100;
            if (this.config.logLevel === 'debug') {
                console.log(`[V165.000] ⚠️  Render detection timeout, using ${fallbackDelay}ms fallback`);
            }
            await this.page.waitForTimeout(fallbackDelay);
            return fallbackDelay;
        }
    }

    /**
     * V165.000: Generate pixel jitter (unchanged - needed for anti-detection)
     * @param {number} range - Pixel range (default: from config)
     * @returns {Object} X and Y offset values
     */
    generatePixelJitter(range = 3) {
        const offsetX = Math.floor(Math.random() * (range * 2 + 1)) - range;
        const offsetY = Math.floor(Math.random() * (range * 2 + 1)) - range;

        if (this.config.logLevel === 'debug') {
            console.log(`[V165.000] 📏 Pixel jitter: (${offsetX}, ${offsetY})px`);
        }

        return { offsetX, offsetY };
    }

    /**
     * V165.000: Humanized Reliable Hover with Event-Driven Detection
     * V163.Diagnostic: Multi-point trigger strategy
     *
     * @param {ElementHandle} cell - The odds cell to hover
     * @param {Function} randomRenderWaitFn - Function for render wait (now event-driven)
     * @param {number} cellIndex - Cell index for logging
     * @param {string} axisName - Axis name (home/draw/away)
     * @param {number} totalCells - Total cells for logging
     * @returns {Promise<Object>} Result object with success flag
     */
    async performReliableHover(cell, randomRenderWaitFn, cellIndex, axisName, totalCells) {
        const maxRetries = this.config.modalRetryCount;
        let retryCount = 0;
        let modalDetected = false;
        let triggerMethod = null;

        console.log(`[V165.000] 🎯 EVENT-DRIVEN HOVER: Cell ${cellIndex + 1}/${totalCells} (${axisName})`);

        // V165.000: Trigger strategies
        const triggerStrategies = [
            { name: 'primary-click', type: 'click', timeout: 1500 },  // Reduced from 2500
            { name: 'fallback-mouseover', type: 'dispatch', event: 'mouseover', timeout: 1000 }  // Reduced from 2000
        ];

        for (let attempt = 0; attempt <= maxRetries; attempt++) {
            const strategy = triggerStrategies[Math.min(attempt, triggerStrategies.length - 1)];

            try {
                // Execute trigger strategy
                if (strategy.type === 'click') {
                    console.log(`[V165.000] ⚡ Executing PRIMARY CLICK`);
                    await cell.click({ force: true, delay: 30 });  // Reduced from 50
                } else if (strategy.type === 'dispatch') {
                    console.log(`[V165.000] ⚡ Dispatching fallback event: ${strategy.event}`);
                    await cell.dispatchEvent(strategy.event, { bubbles: true, cancelable: true });
                }

                // V165.000: Event-driven wait for modal content
                console.log(`[V165.000] ⏱️  Event-driven wait (max ${strategy.timeout}ms)...`);

                try {
                    // Check for modal OR memory data (dual trigger)
                    await this.page.waitForFunction(() => {
                        // Check 1: Modal content
                        const modal = document.querySelector('.tooltip, [role="dialog"], .modal-content, [class*="popup"]');
                        if (modal) {
                            const hasRows = modal.querySelectorAll('tr, .row, [class*="row"]').length > 0;
                            const hasTimePattern = /\d{1,2}\s+\w+\.?\s*,?\s*\d{1,2}:\d{2}/.test(modal.textContent);
                            const isVisible = modal.offsetParent !== null;

                            if ((hasRows || hasTimePattern) && isVisible) {
                                return true;
                            }
                        }

                        // Check 2: Memory data ready
                        const memoryData = window._TITAN_ARTERY_DATA || [];
                        return memoryData.length > 0;

                    }, { polling: this.config.statePollInterval }, strategy.timeout);

                    console.log(`[V165.000] ✅ SUCCESS: Modal/Data detected via '${strategy.name}' on attempt ${attempt + 1}`);

                    // V165.000: Use event-driven render wait instead of fixed delay
                    await randomRenderWaitFn();

                    modalDetected = true;
                    triggerMethod = strategy.name;
                    break;

                } catch (timeoutError) {
                    if (attempt < maxRetries) {
                        console.log(`[V165.000] ⚠️  No modal/data via ${strategy.name}, will retry...`);
                        retryCount++;

                        await this.page.mouse.move(0, 0);
                        await this.page.waitForTimeout(200);  // Reduced from 500
                    } else {
                        console.log(`[V165.000] ❌ FAIL: No modal/data after ${maxRetries + 1} attempts`);
                    }
                }

            } catch (error) {
                if (attempt < maxRetries) {
                    console.log(`[V165.000] ⚠️  ${strategy.name} error on attempt ${attempt + 1}: ${error.message}`);
                    retryCount++;
                } else {
                    console.log(`[V165.000] ❌ FATAL: All trigger methods failed: ${error.message}`);
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

    /**
     * V165.000: Quick state check (NEW)
     * Non-blocking check if memory data is ready
     *
     * @returns {Promise<boolean>} True if data is ready
     */
    async isMemoryDataReady() {
        try {
            const ready = await this.page.evaluate(MEMORY_READY_PREDICATE);
            return ready;
        } catch (error) {
            return false;
        }
    }

    /**
     * V165.000: Wait for any state (memory OR modal OR odds cells)
     * Unified state detection with minimal latency
     *
     * @param {number} timeout - Max timeout (ms)
     * @returns {Promise<Object>} Result with state and method
     */
    async waitForAnyState(timeout = 2000) {
        const startTime = Date.now();

        try {
            await this.page.waitForFunction(() => {
                // State 1: Memory data ready
                const memoryData = window._TITAN_ARTERY_DATA || [];
                if (memoryData.length > 0) return 'MEMORY';

                // State 2: Modal visible
                const modal = document.querySelector('.tooltip, [role="dialog"]');
                if (modal && modal.offsetParent !== null) {
                    const hasData = /\d{1,2}\s+\w+\.?\s*,?\s*\d{1,2}:\d{2}/.test(modal.textContent);
                    if (hasData) return 'MODAL';
                }

                // State 3: Odds cells rendered
                const cells = document.querySelectorAll('[class*="odds-cell"]');
                if (cells.length > 0) return 'CELLS';

                return false;

            }, { polling: this.config.statePollInterval }, timeout);

            const elapsed = Date.now() - startTime;

            // Determine which state was detected
            const state = await this.page.evaluate(() => {
                const memoryData = window._TITAN_ARTERY_DATA || [];
                if (memoryData.length > 0) return 'MEMORY';

                const modal = document.querySelector('.tooltip, [role="dialog"]');
                if (modal && modal.offsetParent !== null) {
                    if (/\d{1,2}\s+\w+\.?\s*,?\s*\d{1,2}:\d{2}/.test(modal.textContent)) {
                        return 'MODAL';
                    }
                }

                return 'CELLS';
            });

            console.log(`[V165.000] ✅ State detected: ${state} (${elapsed}ms)`);

            return { success: true, state, elapsed };

        } catch (error) {
            console.log(`[V165.000] ⏱️  State detection timeout after ${Date.now() - startTime}ms`);
            return { success: false, state: null, elapsed: Date.now() - startTime };
        }
    }
}

module.exports = { EventSimulator };
