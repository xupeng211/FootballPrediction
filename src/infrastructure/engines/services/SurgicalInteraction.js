/**
 * SurgicalInteraction - V164.000 Modular Architecture
 * =====================================================
 *
 * [Genesis.Standardization] V1.0 Refactored SurgicalInteraction
 *
 * Original file: 859 lines
 * Refactored into 3 modules:
 * - DOMNavigator: Modal detection & provider extraction
 * - EventSimulator: Human behavior simulation
 * - AntiFingerprint: Overlay removal & detection avoidance
 *
 * This file now serves as a facade, delegating to specialized modules.
 *
 * @module services/SurgicalInteraction
 * @version V164.000 (Modular Refactoring)
 * @since 2026-01-31
 * @author [Genesis.Standardization]
 */

'use strict';

const { DOMNavigator } = require('./modules/dom_navigator');
const { EventSimulator } = require('./modules/event_simulator');
const { AntiFingerprint } = require('./modules/anti_fingerprint');

/**
 * SurgicalInteraction - Facade for browser interactions
 *
 * Delegates to specialized modules for modularity and maintainability.
 */
class SurgicalInteraction {
    /**
     * @param {Object} page - Playwright page object
     * @param {Object} config - Configuration object
     */
    constructor(page, config = {}) {
        this.page = page;
        this.config = config;

        // Initialize specialized modules
        this.domNavigator = new DOMNavigator(page, config);
        this.eventSimulator = new EventSimulator(page, config);
        this.antiFingerprint = new AntiFingerprint(page, config);
    }

    // ========================================================================
    // DOM Navigation Methods (delegated to DOMNavigator)
    // ========================================================================

    /**
     * V148.000: Detect modal by "Odds movement" title
     * @returns {Promise<boolean>} True if modal is detected
     */
    async detectModalWithTitle() {
        return this.domNavigator.detectModalWithTitle();
    }

    /**
     * V160.000: Extract Provider Name from Parent Row
     * @param {ElementHandle} cell - The odds cell element
     * @returns {Promise<string|null>} Provider name or null
     */
    async extractProviderNameFromCell(cell) {
        return this.domNavigator.extractProviderNameFromCell(cell);
    }

    // ========================================================================
    // Event Simulation Methods (delegated to EventSimulator)
    // ========================================================================

    /**
     * V145.000: Random stabilization
     * @param {number} customMin - Optional custom minimum (ms)
     * @param {number} customMax - Optional custom maximum (ms)
     * @returns {Promise<number>} Actual delay time (ms)
     */
    async randomStabilize(customMin, customMax) {
        return this.eventSimulator.randomStabilize(customMin, customMax);
    }

    /**
     * V150.000: Random render wait
     * @returns {Promise<number>} Actual wait time (ms)
     */
    async randomRenderWait() {
        return this.eventSimulator.randomRenderWait();
    }

    /**
     * V145.000: Generate pixel jitter
     * @param {number} range - Pixel range
     * @returns {Object} X and Y offset values
     */
    generatePixelJitter(range) {
        return this.eventSimulator.generatePixelJitter(range);
    }

    /**
     * V145.000: Humanized Reliable Hover
     * @param {ElementHandle} cell - The odds cell to hover
     * @param {number} cellIndex - Cell index for logging
     * @param {string} axisName - Axis name (home/draw/away)
     * @param {number} totalCells - Total cells for logging
     * @returns {Promise<Object>} Result object
     */
    async performReliableHover(cell, cellIndex, axisName, totalCells) {
        return this.eventSimulator.performReliableHover(
            cell,
            () => this.randomRenderWait(),
            cellIndex,
            axisName,
            totalCells
        );
    }

    // ========================================================================
    // Anti-Fingerprint Methods (delegated to AntiFingerprint)
    // ========================================================================

    /**
     * V145.000: Scroll settle
     * @returns {Promise<void>}
     */
    async scrollSettle() {
        return this.antiFingerprint.scrollSettle();
    }

    /**
     * V146.000: Wait for React async rendering
     * @param {number} timeout - Maximum wait time (ms)
     * @returns {Promise<boolean>} True if rendered successfully
     */
    async waitForReactRender(timeout) {
        return this.antiFingerprint.waitForReactRender(timeout);
    }

    /**
     * V145.000: Handle overlays
     * @returns {Promise<boolean>} True if overlays were removed
     */
    async handleOverlays() {
        return this.antiFingerprint.handleOverlays();
    }

    // ========================================================================
    // Deprecated Methods (for backward compatibility)
    // ========================================================================

    /**
     * V127.000: Randomized jitter wait (DEPRECATED)
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
