/**
 * V148.000 Modal Selector Configuration
 * =======================================
 *
 * Modal selector configuration for React SPA architecture.
 * Based on V147 competitive analysis of jordantete/OddsHarvester.
 *
 * @module config/ModalSelectorConfig
 * @version V148.000
 * @since 2026-01-28
 * @author Principal Frontend Reverse Engineer
 */

'use strict';

/**
 * V148.000: Modal detection selectors
 *
 * Key finding from V147 audit: The actual data modal contains
 * an h3 heading with "Odds movement" text, NOT the .height-content
 * helper element.
 */
const MODAL_SELECTORS = {
    // Primary: Look for the "Odds movement" heading (from competitor analysis)
    primaryTitle: 'h3:text-is("Odds movement")',

    // Alternative: Text-based selector (Playwright compatibility)
    alternativeTitle: 'h3:has-text("Odds movement")',

    // Fallback: Generic modal containers (in case title changes)
    dialogContainers: [
        '[role="dialog"]',
        '.modal-content',
        '[class*="popup"]',
        '[class*="tooltip"]'
    ],

    // Legacy: The old .height-content (DOES NOT contain data!)
    legacyHelper: '.height-content'
};

/**
 * V148.000: Modal detection timeout configuration
 */
const MODAL_TIMEOUT_CONFIG = {
    // Time to wait for "Odds movement" title to appear (milliseconds)
    titleWaitTimeout: 5000,

    // Time to wait for modal container to be visible (milliseconds)
    containerWaitTimeout: 3000,

    // Total time to wait for modal content to populate (milliseconds)
    contentPopulateTimeout: 2000
};

/**
 * V148.000: Modal detection strategies
 */
const DETECTION_STRATEGIES = {
    // Strategy 1: Wait for "Odds movement" title (PRIMARY - from competitor)
    TITLE_BASED: 'title-based',

    // Strategy 2: Wait for dialog container with data (FALLBACK)
    CONTAINER_BASED: 'container-based',

    // Strategy 3: Legacy .height-content check (DEPRECATED - does not contain data)
    LEGACY_HELPER: 'legacy-helper'
};

/**
 * V148.000: Get primary modal title selector
 * @returns {string} Playwright-compatible selector for modal title
 */
function getPrimaryTitleSelector() {
    return MODAL_SELECTORS.primaryTitle;
}

/**
 * V148.000: Get alternative modal title selector (fallback)
 * @returns {string} Playwright-compatible selector for modal title
 */
function getAlternativeTitleSelector() {
    return MODAL_SELECTORS.alternativeTitle;
}

/**
 * V148.000: Get dialog container selectors
 * @returns {string[]} Array of container selectors
 */
function getDialogContainerSelectors() {
    return MODAL_SELECTORS.dialogContainers;
}

/**
 * V148.000: Get modal detection timeout configuration
 * @returns {Object} Timeout configuration object
 */
function getModalTimeoutConfig() {
    return {
        titleWait: MODAL_TIMEOUT_CONFIG.titleWaitTimeout,
        containerWait: MODAL_TIMEOUT_CONFIG.containerWaitTimeout,
        contentPopulate: MODAL_TIMEOUT_CONFIG.contentPopulateTimeout
    };
}

/**
 * V148.000: Build modal detection selector
 * Combines title selector with container closest() traversal
 *
 * @param {string} strategy - Detection strategy ('title-based', 'container-based', etc.)
 * @returns {Object} Selector configuration
 */
function buildModalSelector(strategy = DETECTION_STRATEGIES.TITLE_BASED) {
    switch (strategy) {
        case DETECTION_STRATEGIES.TITLE_BASED:
            return {
                titleSelector: getPrimaryTitleSelector(),
                containerTraversal: true,
                description: 'Find h3 title, then traverse to container'
            };

        case DETECTION_STRATEGIES.CONTAINER_BASED:
            return {
                containerSelectors: getDialogContainerSelectors(),
                titleTraversal: false,
                description: 'Find container directly'
            };

        case DETECTION_STRATEGIES.LEGACY_HELPER:
            return {
                helperSelector: MODAL_SELECTORS.legacyHelper,
                deprecated: true,
                description: 'Legacy .height-content (DOES NOT CONTAIN DATA!)'
            };

        default:
            console.error(`[V148.000] ❌ Unknown strategy: ${strategy}`);
            return null;
    }
}

/**
 * V148.000: Validate modal selector configuration
 * @param {Object} selectorConfig - Selector configuration to validate
 * @returns {boolean} True if configuration is valid
 */
function validateSelectorConfig(selectorConfig) {
    if (!selectorConfig) {
        console.error('[V148.000] ❌ Selector config is null');
        return false;
    }

    if (selectorConfig.deprecated) {
        console.warn('[V148.000] ⚠️  WARNING: Using deprecated selector strategy');
    }

    if (selectorConfig.titleSelector || selectorConfig.helperSelector || selectorConfig.containerSelectors) {
        return true;
    }

    console.error('[V148.000] ❌ Invalid selector config');
    return false;
}

module.exports = {
    MODAL_SELECTORS,
    MODAL_TIMEOUT_CONFIG,
    DETECTION_STRATEGIES,
    getPrimaryTitleSelector,
    getAlternativeTitleSelector,
    getDialogContainerSelectors,
    getModalTimeoutConfig,
    buildModalSelector,
    validateSelectorConfig
};
