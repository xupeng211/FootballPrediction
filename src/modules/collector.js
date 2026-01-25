/**
 * V66.000 - Data Collector Module
 * ================================
 *
 * Unified data collection with XHR interception and DOM fallback.
 * Integrates browser pool and retry mechanism for resilience.
 *
 * @module modules/collector
 * @author Principal Software Architect
 * @version V66.000
 * @since 2026-01-25
 */

'use strict';

const { getGlobalPool, generateTraceId } = require('../core/browser');
const { RetryPolicy } = require('../core/retry');
const { parseTooltipHTML, parseJsonResponse } = require('./parser');

// ============================================================================
// CONFIGURATION
// ============================================================================

const COLLECTOR_CONFIG = {
    // Navigation settings
    defaultTimeout: parseInt(process.env.NAVIGATION_TIMEOUT) || 30000,
    waitUntil: process.env.WAIT_UNTIL || 'networkidle',

    // Interaction settings
    hoverWait: parseInt(process.env.HOVER_WAIT) || 2000,
    maxHoverRetries: parseInt(process.env.HOVER_MAX_RETRIES) || 3,

    // API interception
    interceptPatterns: [
        '/ajax-match-odds/',
        '/api/'
    ],

    // Selectors
    tooltipAnchor: 'h3:text("Odds movement")',
    providerRowSelector: '[data-testid="over-under-expanded-row"], div[data-testid="game-row"]',
    triggerSelector: '[data-testid*="odd-container"]'
};

// ============================================================================
// ERROR CLASS
// ============================================================================

class CollectorError extends Error {
    constructor(code, message, traceId = null, context = {}) {
        super(message);
        this.name = 'CollectorError';
        this.errorCode = code;
        this.traceId = traceId || generateTraceId();
        this.timestamp = new Date().toISOString();
        this.context = context;
    }

    toJSON() {
        return {
            error_code: this.errorCode,
            trace_id: this.traceId,
            timestamp: this.timestamp,
            message: this.message,
            context: this.context
        };
    }
}

// ============================================================================
// XHR INTERCEPTOR
// ============================================================================

/**
 * Setup API response interceptor
 * @param {import('@playwright/test').Page} page - Playwright page
 * @returns {Array} - Captured responses array
 */
function setupApiInterceptor(page) {
    const capturedResponses = [];

    page.on('response', async (response) => {
        try {
            const url = response.url();

            // Check URL pattern
            const isMatch = COLLECTOR_CONFIG.interceptPatterns.some(pattern =>
                url.includes(pattern)
            );

            if (!isMatch) return;

            // Check content type
            const contentType = response.headerValue('content-type') || '';
            if (!contentType.includes('json')) return;

            // Parse JSON
            const jsonData = await response.json();
            capturedResponses.push({ url, json: jsonData });

            console.debug(JSON.stringify({
                level: 'debug',
                module: 'modules/collector/interceptor',
                message: 'Captured API response',
                url: url.substring(0, 60)
            }));

        } catch (error) {
            // Response capture failed, continue
        }
    });

    return capturedResponses;
}

// ============================================================================
// DATA COLLECTOR CLASS
// ============================================================================

/**
 * V66.000: Unified Data Collector
 *
 * Orchestrates browser interaction, API interception, and data extraction.
 */
class DataCollector {
    /**
     * @param {Object} [options={}] - Configuration options
     */
    constructor(options = {}) {
        this.config = { ...COLLECTOR_CONFIG, ...options };
        this.browserPool = getGlobalPool();
        this.retryPolicy = new RetryPolicy();
        this.traceId = generateTraceId();
        this.context = null;
        this.page = null;
        this.capturedResponses = [];
    }

    /**
     * Initialize browser context and page
     * @returns {Promise<void>}
     */
    async initialize() {
        try {
            this.context = await this.browserPool.acquireContext();
            this.page = await this.context.newPage();

            // Setup API interceptor
            this.capturedResponses = setupApiInterceptor(this.page);

            this._log('info', 'Collector initialized');

        } catch (error) {
            throw new CollectorError(
                'INIT_FAILED',
                `Failed to initialize collector: ${error.message}`,
                this.traceId,
                { originalError: error.message }
            );
        }
    }

    /**
     * Navigate to target URL
     * @param {string} url - Target URL
     * @returns {Promise<void>}
     */
    async navigate(url) {
        if (!this.page) {
            await this.initialize();
        }

        try {
            await this.page.goto(url, {
                waitUntil: this.config.waitUntil,
                timeout: this.config.defaultTimeout
            });

            this._log('info', 'Navigated to URL', { url });

        } catch (error) {
            throw new CollectorError(
                'NAVIGATION_FAILED',
                `Failed to navigate to ${url}: ${error.message}`,
                this.traceId,
                { url, originalError: error.message }
            );
        }
    }

    /**
     * Collect data from a provider row
     * @param {Object} providerConfig - Provider configuration
     * @returns {Promise<Array>} - Collected temporal records
     */
    async collectFromProvider(providerConfig) {
        const { id, selector, name } = providerConfig;

        return this.retryPolicy.execute(async () => {
            try {
                // Locate provider row
                const row = await this.page.$(selector);
                if (!row) {
                    throw new CollectorError(
                        'ROW_NOT_FOUND',
                        `Provider row not found: ${selector}`,
                        this.traceId,
                        { providerId: id }
                    );
                }

                // Hover to trigger tooltip
                await row.hover();
                await this.page.waitForTimeout(this.config.hoverWait);

                // Check for tooltip anchor
                const tooltipAnchor = await this.page.$(this.config.tooltipAnchor);
                if (!tooltipAnchor) {
                    throw new CollectorError(
                        'TOOLTIP_NOT_FOUND',
                        'Tooltip anchor not found after hover',
                        this.traceId,
                        { providerId: id }
                    );
                }

                // Extract tooltip content
                const tooltipContent = await this.page.evaluate(() => {
                    const tooltip = document.querySelector('h3:has-text("Odds movement")')?.closest('div');
                    return tooltip ? tooltip.innerHTML : null;
                });

                if (!tooltipContent) {
                    throw new CollectorError(
                        'CONTENT_EXTRACTION_FAILED',
                        'Failed to extract tooltip content',
                        this.traceId,
                        { providerId: id }
                    );
                }

                // Parse HTML
                const records = parseTooltipHTML(tooltipContent, name);

                this._log('info', 'Collected data from provider', {
                    providerId: id,
                    recordCount: records.length
                });

                return records;

            } catch (error) {
                if (error instanceof CollectorError) {
                    throw error;
                }
                throw new CollectorError(
                    'COLLECTION_FAILED',
                    `Failed to collect from provider ${id}: ${error.message}`,
                    this.traceId,
                    { providerId: id, originalError: error.message }
                );
            }
        }, {
            maxRetries: this.config.maxHoverRetries
        });
    }

    /**
     * Collect data from all configured providers
     * @param {Array} providerConfigs - Array of provider configurations
     * @returns {Promise<Array>} - Aggregated collected records
     */
    async collectFromAllProviders(providerConfigs) {
        const allRecords = [];

        for (const providerConfig of providerConfigs) {
            try {
                const records = await this.collectFromProvider(providerConfig);
                allRecords.push(...records);

                // Human delay between providers
                await this.page.waitForTimeout(3000 + Math.random() * 2000);

            } catch (error) {
                this._log('error', 'Provider collection failed', {
                    providerId: providerConfig.id,
                    error: error.message
                });
                // Continue with next provider
            }
        }

        this._log('info', 'Collection complete', {
            totalProviders: providerConfigs.length,
            totalRecords: allRecords.length
        });

        return allRecords;
    }

    /**
     * Check if API data was captured
     * @returns {boolean} - True if API responses were captured
     */
    hasApiData() {
        return Array.isArray(this.capturedResponses) && this.capturedResponses.length > 0;
    }

    /**
     * Get captured API data
     * @returns {Array} - Captured responses
     */
    getCapturedApiData() {
        return this.capturedResponses;
    }

    /**
     * Cleanup resources
     * @returns {Promise<void>}
     */
    async cleanup() {
        try {
            if (this.page && !this.page.isClosed()) {
                await this.page.close();
            }

            if (this.context) {
                await this.context.close();
            }

            this._log('info', 'Collector cleaned up');

        } catch (error) {
            this._log('error', 'Cleanup error', {
                error: error.message
            });
        } finally {
            this.page = null;
            this.context = null;
        }
    }

    /**
     * Internal logging
     * @private
     */
    _log(level, message, data = {}) {
        const logEntry = {
            level,
            trace_id: this.traceId,
            module: 'modules/collector',
            message,
            ...data,
            timestamp: new Date().toISOString()
        };
        console.log(JSON.stringify(logEntry));
    }
}

// ============================================================================
// FACTORY FUNCTION
// ============================================================================>

/**
 * Create a new data collector
 * @param {Object} [options] - Configuration options
 * @returns {DataCollector} - New collector instance
 */
function createCollector(options) {
    return new DataCollector(options);
}

// ============================================================================
// EXPORTS
// ============================================================================

module.exports = {
    DataCollector,
    CollectorError,
    createCollector,
    setupApiInterceptor,
    COLLECTOR_CONFIG
};
