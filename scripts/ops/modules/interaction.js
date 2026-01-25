/**
 * V43.200 Interaction Module
 * ==========================
 *
 * Encapsulates Playwright-based interaction logic with resilience features
 *
 * Core Features:
 *   - Smart Hover with Exponential Backoff Retry
 *   - Timeout Degradation (graceful skip on failure)
 *   - Error Recovery with structured logging
 *
 * @module interaction
 * @author Senior DevOps & Systems Engineer
 * @version V43.200
 * @since 2026-01-24
 */

'use strict';

const path = require('path');
const fs = require('fs');
const logger = require('./logger');
const log = logger.createLogger('interaction');

/**
 * @typedef {Object} HoverConfig
 * @property {number} [hoverWait=2000] - Wait time after hover in milliseconds
 * @property {number} [maxRetries=3] - Maximum number of retry attempts
 * @property {number} [baseDelay=500] - Base delay for exponential backoff
 * @property {number} [maxDelay=5000] - Maximum delay cap
 * @property {number} [backoffMultiplier=2] - Multiplier for exponential backoff
 * @property {number} [nodeIndex=0] - Node index for logging
 */

/**
 * @typedef {Object} HoverResult
 * @property {boolean} success - Whether hover was successful
 * @property {number} attempts - Number of attempts made
 * @property {number} nodeIndex - Index of the node
 * @property {string} [error] - Error message if failed
 */

/**
 * @typedef {Object} RowMetadata
 * @property {ElementHandle} element - Playwright element handle
 * @property {number} index - Row index
 * @property {string} provider - Provider name
 * @property {boolean} matched - Whether row matched target keys
 */

// ============================================================================
// CONFIGURATION
// ============================================================================

/**
 * Load retry configuration from schema_map.json
 * @returns {Object} - Configuration object
 */
function loadRetryConfig() {
    const configPath = path.join(__dirname, '../config/schema_map.json');

    try {
        const configData = fs.readFileSync(configPath, 'utf-8');
        const schemaConfig = JSON.parse(configData);

        return {
            hoverWait: schemaConfig.retry_config.hover.hover_wait,
            maxRetries: schemaConfig.retry_config.hover.max_retries,
            baseDelay: schemaConfig.retry_config.hover.base_delay,
            maxDelay: schemaConfig.retry_config.hover.max_delay,
            backoffMultiplier: schemaConfig.retry_config.hover.backoff_multiplier
        };
    } catch (error) {
        log.warn(`Could not load retry config from schema_map.json: ${error.message}`);
        // Fallback to default values
        return {
            hoverWait: 2000,
            maxRetries: 3,
            baseDelay: 500,
            maxDelay: 5000,
            backoffMultiplier: 2
        };
    }
}

const DEFAULT_CONFIG = loadRetryConfig();

// ============================================================================
// ERROR CLASS
// ============================================================================

class InteractionError extends Error {
    constructor(type, nodeIndex, message, originalError = null) {
        super(message);
        this.name = 'InteractionError';
        this.errorType = type;
        this.nodeIndex = nodeIndex;
        this.timestamp = new Date().toISOString();
        this.originalError = originalError;
    }

    toString() {
        return `[${this.errorType}] [Node_${this.nodeIndex}] [${this.timestamp}] ${this.message}`;
    }
}

// ============================================================================
// SMART HOVER WITH EXPONENTIAL BACKOFF
// ============================================================================

/**
 * Smart hover with exponential backoff retry mechanism
 *
 * @param {ElementHandle} element - Playwright element handle
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {HoverConfig} [config={}] - Configuration options
 * @returns {Promise<HoverResult>} - Result object with success status
 * @throws {InteractionError} When max retries exceeded
 *
 * @example
 * const result = await smartHover(element, page, { maxRetries: 3, nodeIndex: 5 });
 * if (result.success) {
 *   console.log(`Hover succeeded after ${result.attempts} attempts`);
 * }
 */
async function smartHover(element, page, config = {}) {
    const finalConfig = { ...DEFAULT_CONFIG, ...config };
    let attempt = 0;
    let delay = finalConfig.baseDelay;
    const nodeIndex = config.nodeIndex || 0;

    while (attempt < finalConfig.maxRetries) {
        attempt++;

        try {
            // Execute hover action
            await element.hover();

            // Wait for tooltip to appear
            await page.waitForTimeout(finalConfig.hoverWait);

            // Check for tooltip presence (anchor-based detection)
            const tooltipAnchor = await page.$("h3:text('Odds movement')");

            if (tooltipAnchor) {
                return {
                    success: true,
                    attempts: attempt,
                    nodeIndex: nodeIndex
                };
            }

            // Tooltip not detected, retry with backoff
            if (attempt < finalConfig.maxRetries) {
                const logMessage = `Hover attempt ${attempt}/${finalConfig.maxRetries} failed (no tooltip), retrying in ${delay}ms...`;
                log.warn(logMessage);
                await page.waitForTimeout(delay);
                delay = Math.min(delay * finalConfig.backoffMultiplier, finalConfig.maxDelay);
            }

        } catch (error) {
            const errorMsg = `Hover attempt ${attempt}/${finalConfig.maxRetries} failed: ${error.message}`;

            if (attempt < finalConfig.maxRetries) {
                log.warn(`Hover attempt ${attempt}/${finalConfig.maxRetries} failed: ${error.message} - Retrying in ${delay}ms...`);
                await page.waitForTimeout(delay);
                delay = Math.min(delay * finalConfig.backoffMultiplier, finalConfig.maxDelay);
            } else {
                throw new InteractionError(
                    'HOVER_FAILURE',
                    nodeIndex,
                    `Max retries exceeded for hover action`,
                    error
                );
            }
        }
    }

    // All retries exhausted
    return {
        success: false,
        attempts: attempt,
        nodeIndex: nodeIndex,
        error: 'Max retries exceeded'
    };
}

// ============================================================================
// ROW IDENTIFICATION
// ============================================================================

/**
 * Identify provider rows using precision selector
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} rowSelector - CSS selector for provider rows
 * @param {string[]} targetKeys - Provider name patterns for fuzzy matching
 * @returns {Promise<RowMetadata[]>} - Array of row elements with metadata
 *
 * @example
 * const rows = await identifyProviderRows(page, 'div.row', ['pinnacle', 'bet365']);
 * console.log(`Found ${rows.filter(r => r.matched).length} matching rows`);
 */
async function identifyProviderRows(page, rowSelector, targetKeys) {
    const rows = await page.$$(rowSelector);
    const matchedRows = [];

    for (let i = 0; i < rows.length; i++) {
        try {
            const row = rows[i];
            let providerName = 'unknown';
            let matched = false;

            // Extract provider identity from img attributes
            const imgElements = await row.$$('img');

            for (const img of imgElements) {
                try {
                    const title = await img.getAttribute('title');
                    const alt = await img.getAttribute('alt');

                    const textToCheck = `${title || ''} ${alt || ''}`.toLowerCase();

                    for (const key of targetKeys) {
                        if (textToCheck.includes(key.toLowerCase())) {
                            providerName = key;
                            matched = true;
                            break;
                        }
                    }

                    if (matched) break;
                } catch (e) {
                    // Continue
                }
            }

            matchedRows.push({
                element: row,
                index: i,
                provider: providerName,
                matched: matched
            });

        } catch (e) {
            // Skip failed row
            log.debug(`Row ${i} skipped: ${e.message}`);
        }
    }

    return matchedRows;
}

// ============================================================================
// TRIGGER ELEMENT LOCATION
// ============================================================================

/**
 * Locate hover trigger element within a row
 *
 * @param {ElementHandle} rowElement - Row element handle
 * @param {string} triggerSelector - CSS selector for trigger element
 * @returns {Promise<ElementHandle|null>} - Trigger element or null if not found
 *
 * @example
 * const trigger = await locateTriggerElement(rowElement, 'div.hover-trigger');
 * if (trigger) {
 *   await trigger.hover();
 * }
 */
async function locateTriggerElement(rowElement, triggerSelector) {
    try {
        const triggers = await rowElement.$$(triggerSelector);
        return triggers.length > 0 ? triggers[0] : null;
    } catch (error) {
        return null;
    }
}

// ============================================================================
// V49.000 HUMAN BEHAVIOR SIMULATOR (Anti-Scraping)
// ============================================================================

/**
 * V49.000: Human behavior configuration
 */
const HUMAN_BEHAVIOR_CONFIG = {
    // Random hover duration (simulates reading chart)
    hoverDuration: {
        min: 2500,  // 2.5 seconds
        max: 5000,  // 5 seconds
    },

    // Random page scroll (30% probability)
    scrolling: {
        enabled: true,
        probability: 0.3,
        minOffset: -50,
        maxOffset: 50
    },

    // Mouse jitter (natural movement)
    jitter: {
        enabled: true,
        probability: 0.2
    }
};

/**
 * V49.000: Generate random number in range
 * @param {number} min - Minimum value
 * @param {number} max - Maximum value
 * @returns {number} - Random value
 */
function randomInRange(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

/**
 * V49.000: Apply human behavior simulation during interaction
 *
 * Simulates:
 * - Random hover duration (2.5s - 5s)
 * - Occasional page scrolling (30% chance)
 * - Random mouse movements
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @returns {Promise<void>}
 *
 * @example
 * await applyHumanBehavior(page);
 * // Hover + random scroll + jitter applied
 */
async function applyHumanBehavior(page) {
    // Random hover duration
    const hoverDuration = randomInRange(
        HUMAN_BEHAVIOR_CONFIG.hoverDuration.min,
        HUMAN_BEHAVIOR_CONFIG.hoverDuration.max
    );

    log.debug(`Human behavior: Hover for ${hoverDuration}ms`);

    // 30% chance to scroll
    if (HUMAN_BEHAVIOR_CONFIG.scrolling.enabled &&
        Math.random() < HUMAN_BEHAVIOR_CONFIG.scrolling.probability) {

        const scrollOffset = randomInRange(
            HUMAN_BEHAVIOR_CONFIG.scrolling.minOffset,
            HUMAN_BEHAVIOR_CONFIG.scrolling.maxOffset
        );

        try {
            await page.evaluate((offset) => {
                window.scrollBy(0, offset);
            }, scrollOffset);
            log.debug(`Human behavior: Scrolled ${scrollOffset}px`);
        } catch (e) {
            // Scroll may fail in some contexts, ignore
        }
    }

    // Apply hover duration
    await page.waitForTimeout(hoverDuration);
}

/**
 * V49.000: Enhanced smart hover with human behavior simulation
 *
 * Combines exponential backoff retry with human-like behavior patterns
 *
 * @param {ElementHandle} element - Playwright element handle
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {Object} [config={}] - Configuration options
 * @returns {Promise<HoverResult>} - Result object with success status
 */
async function smartHoverWithBehavior(element, page, config = {}) {
    const finalConfig = { ...DEFAULT_CONFIG, ...config };
    let attempt = 0;
    let delay = finalConfig.baseDelay;
    const nodeIndex = config.nodeIndex || 0;

    while (attempt < finalConfig.maxRetries) {
        attempt++;

        try {
            // Execute hover action
            await element.hover();

            // V49.000: Apply human behavior simulation
            await applyHumanBehavior(page);

            // Check for tooltip presence
            const tooltipAnchor = await page.$("h3:text('Odds movement')");

            if (tooltipAnchor) {
                return {
                    success: true,
                    attempts: attempt,
                    nodeIndex: nodeIndex
                };
            }

            // Tooltip not detected, retry with backoff
            if (attempt < finalConfig.maxRetries) {
                const logMessage = `Hover attempt ${attempt}/${finalConfig.maxRetries} failed (no tooltip), retrying in ${delay}ms...`;
                log.warn(logMessage);
                await page.waitForTimeout(delay);
                delay = Math.min(delay * finalConfig.backoffMultiplier, finalConfig.maxDelay);
            }

        } catch (error) {
            const errorMsg = `Hover attempt ${attempt}/${finalConfig.maxRetries} failed: ${error.message}`;

            if (attempt < finalConfig.maxRetries) {
                log.warn(`Hover attempt ${attempt}/${finalConfig.maxRetries} failed: ${error.message} - Retrying in ${delay}ms...`);
                await page.waitForTimeout(delay);
                delay = Math.min(delay * finalConfig.backoffMultiplier, finalConfig.maxDelay);
            } else {
                throw new InteractionError(
                    'HOVER_FAILURE',
                    nodeIndex,
                    `Max retries exceeded for hover action`,
                    error
                );
            }
        }
    }

    // All retries exhausted
    return {
        success: false,
        attempts: attempt,
        nodeIndex: nodeIndex,
        error: 'Max retries exceeded'
    };
}

// ============================================================================
// V49.000 RATE LIMITER WITH HUMAN TIMING
// ============================================================================

/**
 * V49.000: Apply human-like delay between provider operations
 *
 * Simulates a human researcher switching between different bookmakers
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {number} [minDelay=4000] - Minimum delay in ms (default: 4s)
 * @param {number} [maxDelay=8000] - Maximum delay in ms (default: 8s)
 * @returns {Promise<void>}
 */
async function applyHumanDelay(page, minDelay = 4000, maxDelay = 8000) {
    const delay = randomInRange(minDelay, maxDelay);
    log.info(`Human delay: Waiting ${delay}ms before next operation...`);
    await page.waitForTimeout(delay);
}

// ============================================================================
// V50.200 API INTERCEPTOR (Protocol-Level Network Interception)
// ============================================================================

/**
 * V50.200: Setup API response interceptor
 *
 * Intercepts network-level JSON responses from OddsPortal API endpoints.
 * Supports both /ajax-match-odds/ and /api/ URL patterns.
 * Captures data for API-first + UI-fallback hybrid strategy.
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @returns {Promise<Array<{url: string, json: Object}>>} - Captured responses array
 *
 * @example
 * const capturedResponses = await setupApiInterceptor(page);
 * // Later, responses will be automatically captured
 * console.log(`Captured ${capturedResponses.length} API responses`);
 */
async function setupApiInterceptor(page) {
    // Create shared array reference for captured responses
    const capturedResponses = [];

    // Register response handler
    page.on('response', async (response) => {
        try {
            const url = response.url();

            // Check URL pattern match
            const isAjaxMatchOdds = url.includes('/ajax-match-odds/');
            const isApiEndpoint = url.includes('/api/');

            if (!isAjaxMatchOdds && !isApiEndpoint) {
                return; // Skip non-matching URLs
            }

            // Check content type
            const contentType = response.headerValue('content-type') || '';
            if (!contentType.includes('json')) {
                return; // Skip non-JSON responses
            }

            // Parse JSON response
            const jsonData = await response.json();

            // Store in capture array
            capturedResponses.push({
                url: url,
                json: jsonData
            });

            // Also store in browser global._api_buffer for later access
            try {
                await page.evaluate((data) => {
                    global._api_buffer = global._api_buffer || [];
                    global._api_buffer.push(data);
                }, jsonData);
            } catch (e) {
                // Global storage may fail in some contexts, ignore
                log.debug(`Could not store in global._api_buffer: ${e.message}`);
            }

            log.debug(`V50.200: Captured API response from ${url.substring(0, 60)}...`);

        } catch (error) {
            // Response may not be JSON or parsing failed
            log.debug(`V50.200: Response capture failed: ${error.message}`);
        }
    });

    log.info('V50.200: API interceptor registered (watching /ajax-match-odds/ and /api/)');

    return capturedResponses;
}

/**
 * V50.200: Check if API data was captured
 *
 * @param {Array} capturedResponses - Responses array from setupApiInterceptor
 * @returns {boolean} - True if any API responses were captured
 */
function hasApiData(capturedResponses) {
    return Array.isArray(capturedResponses) && capturedResponses.length > 0;
}

// ============================================================================
// V49.520 TESTID-BASED IDENTIFICATION (React/Vue Architecture Support)
// ============================================================================

/**
 * V49.520: Identify data nodes using stable data-testid attribute
 *
 * Replaces class-based string matching with attribute-based selection.
 * Compatible with React/Vue single-page applications.
 * Supports both result list pages (game-row) and match detail pages (over-under-expanded-row).
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @returns {Promise<Array<{element: ElementHandle, index: number, nodeType: string, metricCount: number, matched: boolean}>>} - Array of node metadata
 *
 * @example
 * const nodes = await identifyNodesByTestId(page);
 * console.log(`Found ${nodes.length} nodes`);
 */
async function identifyNodesByTestId(page) {
    const nodes = [];

    try {
        // Strategy 1: Try match detail page structure (over-under-expanded-row)
        let providerRows = await page.$$('[data-testid="over-under-expanded-row"]');
        let pageType = 'detail';

        // Strategy 2: Fallback to result list page structure (game-row)
        if (providerRows.length === 0) {
            providerRows = await page.$$('div[data-testid="game-row"]');
            pageType = 'list';
        }

        log.debug(`V49.520: Found ${providerRows.length} provider rows via data-testid (${pageType} page)`);

        for (let i = 0; i < providerRows.length; i++) {
            const row = providerRows[i];

            // Count metric containers (odd-container) within this row
            const metricContainers = await row.$$('[data-testid*="odd-container"]');

            nodes.push({
                element: row,
                index: i,
                nodeType: pageType === 'detail' ? 'Detail_Node_X' : 'List_Node_X',
                metricCount: metricContainers.length,
                matched: true
            });
        }

        log.info(`V49.520: Identified ${nodes.length} nodes via data-testid (${pageType} page)`);
        return nodes;

    } catch (error) {
        log.error(`V49.520: Node identification failed: ${error.message}`);
        return [];
    }
}

/**
 * V49.520: Locate interaction trigger by data-testid priority
 *
 * Prioritizes data-testid attributes over class selectors for stability.
 * Falls back to class-based selection if testid not found.
 *
 * @param {ElementHandle} nodeElement - Node element handle
 * @param {string} [fallbackSelector] - Fallback CSS selector
 * @returns {Promise<ElementHandle|null>} - Trigger element or null
 *
 * @example
 * const trigger = await locateTriggerByTestId(nodeElement);
 * if (trigger) {
 *   await trigger.hover();
 * }
 */
async function locateTriggerByTestId(nodeElement, fallbackSelector = null) {
    try {
        // Strategy 1: Look for data-testid with interaction trigger
        const testIdTrigger = await nodeElement.$('[data-testid="interaction-trigger"]');
        if (testIdTrigger) {
            log.debug('V49.520: Trigger found via data-testid');
            return testIdTrigger;
        }

        // Strategy 2: Look for hover-related data-testid
        const hoverTrigger = await nodeElement.$('[data-testid*="hover"], [data-testid*="trigger"]');
        if (hoverTrigger) {
            log.debug('V49.520: Trigger found via hover data-testid');
            return hoverTrigger;
        }

        // Strategy 3: Fallback to provided selector
        if (fallbackSelector) {
            const triggers = await nodeElement.$$(fallbackSelector);
            if (triggers.length > 0) {
                log.debug('V49.520: Trigger found via fallback selector');
                return triggers[0];
            }
        }

        // Strategy 4: Return the node itself as trigger (last resort)
        log.debug('V49.520: Using node element as trigger');
        return nodeElement;

    } catch (error) {
        log.warn(`V49.520: Trigger location failed: ${error.message}`);
        return null;
    }
}

// ============================================================================
// EXPORTS
// ============================================================================

/**
 * @type {typeof smartHover}
 */
exports.smartHover = smartHover;

/**
 * @type {typeof smartHoverWithBehavior}
 */
exports.smartHoverWithBehavior = smartHoverWithBehavior;

/**
 * @type {typeof identifyProviderRows}
 */
exports.identifyProviderRows = identifyProviderRows;

/**
 * @type {typeof locateTriggerElement}
 */
exports.locateTriggerElement = locateTriggerElement;

/**
 * V49.520: TestID-based node identification
 */
exports.identifyNodesByTestId = identifyNodesByTestId;

/**
 * V49.520: TestID-based trigger location
 */
exports.locateTriggerByTestId = locateTriggerByTestId;

/**
 * @type {typeof InteractionError}
 */
exports.InteractionError = InteractionError;

/**
 * @type {typeof applyHumanBehavior}
 */
exports.applyHumanBehavior = applyHumanBehavior;

/**
 * @type {typeof applyHumanDelay}
 */
exports.applyHumanDelay = applyHumanDelay;

/**
 * @type {HoverConfig}
 */
exports.DEFAULT_CONFIG = DEFAULT_CONFIG;

/**
 * V49.000: Human behavior config
 */
exports.HUMAN_BEHAVIOR_CONFIG = HUMAN_BEHAVIOR_CONFIG;

/**
 * V50.200: API interceptor setup
 */
exports.setupApiInterceptor = setupApiInterceptor;

/**
 * V50.200: Check if API data was captured
 */
exports.hasApiData = hasApiData;

module.exports = {
    smartHover,
    smartHoverWithBehavior,
    identifyProviderRows,
    locateTriggerElement,
    identifyNodesByTestId,
    locateTriggerByTestId,
    InteractionError,
    applyHumanBehavior,
    applyHumanDelay,
    DEFAULT_CONFIG,
    HUMAN_BEHAVIOR_CONFIG,
    setupApiInterceptor,
    hasApiData
};
