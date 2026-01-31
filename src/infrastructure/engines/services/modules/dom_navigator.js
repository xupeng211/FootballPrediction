/**
 * DOM Navigator - V160.000 Modal Detection & Provider Extraction
 * ================================================================
 *
 * DOM navigation utilities for modal detection and provider identity.
 * Extracted from SurgicalInteraction.js for modular architecture.
 *
 * V160.000 Features:
 * - extractProviderNameFromCell() - Row-to-Shop identity bridge
 * - detectModalWithTitle() - Multi-layer modal detection
 *
 * @module services/modules/dom_navigator
 * @version V1.0
 * @since 2026-01-31
 * @author [Genesis.Standardization]
 */

'use strict';

const { buildModalSelector } = require('../../config/ModalSelectorConfig');

/**
 * DOM Navigator - DOM navigation and provider extraction
 */
class DOMNavigator {
    /**
     * @param {Object} page - Playwright page object
     * @param {Object} config - Configuration object
     * @param {string} config.logLevel - Logging level
     */
    constructor(page, config = {}) {
        this.page = page;
        this.config = {
            logLevel: config.logLevel || 'info',
            modalConfig: buildModalSelector('title-based')
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

                // Last resort: Find any div with time pattern data
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
     * const navigator = new DOMNavigator(page, config);
     * const providerName = await navigator.extractProviderNameFromCell(cell);
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

module.exports = { DOMNavigator };
