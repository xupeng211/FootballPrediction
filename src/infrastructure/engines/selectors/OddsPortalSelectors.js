/**
 * OddsPortalSelectors - V138.000 Modular Aiming System
 * =============================================================================
 *
 * Centralized CSS selector management for OddsPortal website elements.
 * Inspired by jordantete/OddsHarvester competitive analysis.
 *
 * Design Philosophy:
 * - Multiple fallback selectors for each element type
 * - Tailwind CSS compatible (attribute matching with *)
 * - Defensive programming with graceful degradation
 *
 * @module OddsPortalSelectors
 * @version V138.000
 * @since 2026-01-27
 * @author Senior Staff Software Architect
 */

'use strict';

/**
 * V138.000: Centralized selector definitions
 * All selectors organized by category with multiple fallbacks
 */
class OddsPortalSelectors {
    /**
     * Overlay and modal selectors (V138.000: Enhanced coverage)
     */
    static OVERLAYS = {
        // Primary OneTrust cookie consent
        ONE_TRUST_CONSENT_SDK: '#onetrust-consent-sdk',
        ONE_TRUST_BANNER_SDK: '#onetrust-banner-sdk',
        ONE_TRUST_ACCEPT_BTN: '#onetrust-accept-btn-handler',
        ONE_TRUST_PC_FILTER: '.onetrust-pc-dark-filter',
        ONE_TRUST_PC_CONTAINER: '.ot-pc-container',

        // V138.000 NEW: overlay-bookie-modal (missing in OddsHarvester)
        OVERLAY_BOOKIE_MODAL: '.overlay-bookie-modal',
        BOOKIE_MODAL_VARIANT: '[class*="bookie-modal"]',

        // Generic overlay patterns
        GENERIC_OVERLAY: '[role="dialog"]',
        COOKIE_CONSENT: '.cookie-consent',
        CONSENT_BANNER: '[class*="consent-banner"]',

        // All overlay keywords for BRUTE FORCE PURGE (V133.000)
        PURGE_KEYWORDS: ['onetrust', 'cookie', 'consent', 'overlay', 'banner', 'popup', 'bookie', 'modal']
    };

    /**
     * Odds cell selectors (V138.000: Tailwind CSS compatible)
     */
    static ODDS_CELLS = {
        // Primary selector (V133.000 fuzzy matching)
        PRIMARY: '[class*="odds-cell"]',

        // OddsHarvester alternative patterns
        ODD_CONTAINER: '[data-testid="odd-container-default"]',
        FLEX_CENTER_ODDS: 'div.flex-center.flex-col.font-bold',

        // Fallback selectors
        ODD_BLOCK: '[class*="odd"]',
        PRICE_CELL: '[data-testid*="odd"]',
        TEXT_ODDS: 'div[class*="text-"][class*="font-bold"]',

        // All selectors array for fallback iteration
        ALL_SELECTORS: [
            '[class*="odds-cell"]',
            '[data-testid="odd-container-default"]',
            'div.flex-center.flex-col.font-bold',
            '[class*="odd"]',
            '[data-testid*="odd"]'
        ]
    };

    /**
     * Modal selectors (V138.000: V134 discovery integration)
     */
    static MODALS = {
        // V134.000 Discovery: .height-content container
        HEIGHT_CONTENT: '.height-content',

        // Odds movement heading
        ODDS_MOVEMENT_HEADING: 'h3:has-text("Odds movement")',
        ODDS_MOVEMENT_TEXT: 'h3:text("Odds movement")',

        // Alternative modal patterns
        MODAL_WRAPPER: '[class*="modal"]',
        POPUP_CONTAINER: '[class*="popup"]',
        DIALOG_CONTENT: '[role="dialog"]',

        // Modal detection strategies
        DETECTION_STRATEGIES: [
            '.height-content:has(h3:has-text("Odds movement"))',
            '.height-content',
            'h3:has-text("Odds movement")',
            '[class*="modal"][class*="odds"]'
        ]
    };

    /**
     * Bookmaker row selectors
     */
    static BOOKMAKER_ROWS = {
        // V133.000: Flex-based selector
        PRIMARY: 'div.flex.h-9.border-b.border-black-borders',

        // Border-based pattern (OddsHarvester style)
        BORDER_PATTERN: 'div[class*="border-black-borders"]',

        // Height-based pattern
        HEIGHT_PATTERN: 'div[class*="h-9"][class*="flex"]',

        // All selectors array
        ALL_SELECTORS: [
            'div.flex.h-9.border-b.border-black-borders',
            'div[class*="border-black-borders"]',
            'div[class*="h-9"][class*="flex"]'
        ]
    };

    /**
     * Bookmaker logo selectors
     */
    static BOOKMAKER_LOGO = {
        PRIMARY: 'img.bookmaker-logo',
        ALT_ATTRIBUTE: 'img[alt]',
        SRC_PATTERN: 'img[src*="bookmaker"]',

        ALL_SELECTORS: [
            'img.bookmaker-logo',
            'img[alt]',
            'img[src*="bookmaker"]',
            'img[class*="logo"]'
        ]
    };

    /**
     * Market tab selectors (OddsHarvester inspired)
     */
    static MARKET_TABS = {
        PRIMARY: 'ul.visible-links.bg-black-main.odds-tabs > li',
        FALLBACK_1: 'ul.odds-tabs > li',
        FALLBACK_2: 'ul[class*="odds-tabs"] > li',
        FALLBACK_3: 'div[class*="odds-tabs"] li',
        GENERIC_TAB: 'li[class*="tab"]',
        NAVIGATION: 'nav li',

        ALL_SELECTORS: [
            'ul.visible-links.bg-black-main.odds-tabs > li',
            'ul.odds-tabs > li',
            'ul[class*="odds-tabs"] > li',
            'div[class*="odds-tabs"] li',
            'li[class*="tab"]',
            'nav li'
        ]
    };

    /**
     * More button selectors (OddsHarvester inspired)
     */
    static MORE_BUTTON = {
        PRIMARY: 'button.toggle-odds:has-text("More")',
        FALLBACK_1: 'button[class*="toggle-odds"]',
        FALLBACK_2: '.visible-btn-odds:has-text("More")',
        FALLBACK_3: 'button:has-text("More")',
        GENERIC_TOGGLE: 'button[class*="toggle"]',

        ALL_SELECTORS: [
            'button.toggle-odds:has-text("More")',
            'button[class*="toggle-odds"]',
            '.visible-btn-odds:has-text("More")',
            'button:has-text("More")',
            'button[class*="toggle"]'
        ]
    };

    /**
     * V138.000: Get selector with fallback chain
     * Returns array of selectors to try in sequence
     *
     * @param {string} category - Selector category (OVERLAYS, ODDS_CELLS, etc.)
     * @param {string} key - Specific selector key (optional)
     * @returns {string[]} Array of selectors to try
     */
    static getSelectors(category, key = null) {
        const categoryMap = this[category];
        if (!categoryMap) {
            throw new Error(`[V138.000] Unknown selector category: ${category}`);
        }

        // If key specified, return specific selector
        if (key) {
            const selector = categoryMap[key];
            if (Array.isArray(selector)) {
                return selector;
            }
            return [selector];
        }

        // If ALL_SELECTORS exists, return it
        if (categoryMap.ALL_SELECTORS) {
            return categoryMap.ALL_SELECTORS;
        }

        // Otherwise return all values as array
        return Object.values(categoryMap).filter(
            val => typeof val === 'string' && !val.includes('ALL_SELECTORS')
        );
    }

    /**
     * V138.000: Get purge keywords for BRUTE FORCE overlay removal
     * @returns {string[]} Array of keyword strings
     */
    static getPurgeKeywords() {
        return this.OVERLAYS.PURGE_KEYWORDS;
    }

    /**
     * V138.000: Generate DOM purge script for overlay removal
     * Returns JavaScript code string for page.evaluate()
     *
     * @returns {string} JavaScript code for DOM purging
     */
    static generatePurgeScript() {
        const keywords = this.getPurgeKeywords();

        return `
            (function() {
                const keywords = ${JSON.stringify(keywords)};
                let count = 0;
                const removed = [];

                // Pre-purge check
                const preCheck = keywords.map(k => ({
                    keyword: k,
                    idCount: document.querySelectorAll('[id*="' + k + '"]').length,
                    classCount: document.querySelectorAll('[class*="' + k + '"]').length
                }));

                // Remove by ID
                keywords.forEach(keyword => {
                    const elements = document.querySelectorAll('[id*="' + keyword + '"]');
                    elements.forEach(el => {
                        removed.push(el.tagName + '#' + (el.id || 'unnamed'));
                        el.remove();
                        count++;
                    });
                });

                // Remove by class
                keywords.forEach(keyword => {
                    const elements = document.querySelectorAll('[class*="' + keyword + '"]');
                    elements.forEach(el => {
                        removed.push(el.tagName + '.' + (el.className || 'unnamed'));
                        el.remove();
                        count++;
                    });
                });

                // Remove specific OneTrust selectors
                // V149.000: DO NOT remove generic [role="dialog"] - it may contain data modals!
                const specificSelectors = [
                    '#onetrust-consent-sdk',
                    '#onetrust-banner-sdk',
                    '.onetrust-pc-dark-filter',
                    '.ot-pc-container',
                    // '[role="dialog"]',  // V149.000: REMOVED - breaks data modal detection
                    '.cookie-consent',
                    '.overlay-bookie-modal'
                ];

                specificSelectors.forEach(selector => {
                    try {
                        const elements = document.querySelectorAll(selector);
                        elements.forEach(el => {
                            removed.push(selector);
                            el.remove();
                            count++;
                        });
                    } catch (e) {
                        // Selector errors ignored
                    }
                });

                return {
                    count: count,
                    removed: removed,
                    preCheck: preCheck
                };
            })();
        `;
    }

    /**
     * V138.000: Validate selector against current page
     * Tests if selector matches any elements
     *
     * @param {Page} page - Playwright page object
     * @param {string} selector - CSS selector to validate
     * @returns {Promise<number>} Number of matching elements
     */
    static async validateSelector(page, selector) {
        try {
            const count = await page.locator(selector).count();
            return count;
        } catch (error) {
            return 0;
        }
    }

    /**
     * V138.000: Find working selector from fallback chain
     * Iterates through selector array and returns first working one
     *
     * @param {Page} page - Playwright page object
     * @param {string[]} selectors - Array of selectors to try
     * @returns {Promise<{selector: string, count: number}>} First working selector
     */
    static async findWorkingSelector(page, selectors) {
        for (const selector of selectors) {
            const count = await this.validateSelector(page, selector);
            if (count > 0) {
                return { selector, count };
            }
        }
        return { selector: null, count: 0 };
    }
}

/**
 * V138.000: Convenience exports for common operations
 */
class SelectorHelper {
    /**
     * Get all overlay purge keywords
     */
    static getOverlayKeywords() {
        return OddsPortalSelectors.getPurgeKeywords();
    }

    /**
     * Get all odds cell selectors
     */
    static getOddsCellSelectors() {
        return OddsPortalSelectors.getSelectors('ODDS_CELLS');
    }

    /**
     * Get all bookmaker row selectors
     */
    static getBookmakerRowSelectors() {
        return OddsPortalSelectors.getSelectors('BOOKMAKER_ROWS');
    }

    /**
     * Get all modal detection strategies
     */
    static getModalDetectionStrategies() {
        return OddsPortalSelectors.MODALS.DETECTION_STRATEGIES;
    }
}

module.exports = {
    OddsPortalSelectors,
    SelectorHelper
};
