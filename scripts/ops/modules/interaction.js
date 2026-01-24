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
// EXPORTS
// ============================================================================

/**
 * @type {typeof smartHover}
 */
exports.smartHover = smartHover;

/**
 * @type {typeof identifyProviderRows}
 */
exports.identifyProviderRows = identifyProviderRows;

/**
 * @type {typeof locateTriggerElement}
 */
exports.locateTriggerElement = locateTriggerElement;

/**
 * @type {typeof InteractionError}
 */
exports.InteractionError = InteractionError;

/**
 * @type {HoverConfig}
 */
exports.DEFAULT_CONFIG = DEFAULT_CONFIG;

module.exports = {
    smartHover,
    identifyProviderRows,
    locateTriggerElement,
    InteractionError,
    DEFAULT_CONFIG
};
