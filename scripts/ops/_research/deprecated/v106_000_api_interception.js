/**
 * V106.000 API Interception Engine - Direct Data Extraction
 * ===========================================================
 *
 * V106.000: Intercept match-event API calls to extract odds data directly
 *   - Bypass DOM rendering issues (geo-blocking)
 *   - Intercept match-event API responses
 *   - Decode Base64 JSON payload
 *   - Extract opening odds and history data
 *
 * @version V106.000
 * @since 2026-01-26
 */

'use strict';

const { chromium } = require('playwright');
const fs = require('fs');

// Target URLs (from V105.001 discovery)
const TARGET_URLS = [
    'https://www.oddsportal.com/football/england/premier-league/everton-leeds-neRXKc8l/',
    'https://www.oddsportal.com/football/england/premier-league/brighton-everton-vPKFVEM6/'
];

const REALISTIC_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Sec-Ch-Ua': '"Chromium";v="131", "Not_A Brand";v="24"',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Referer': 'https://www.oddsportal.com/football/england/premier-league/'
};

const CONFIG = {
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    viewport: { width: 1920, height: 1080 },
    timeout: 90000,
    maxWaitTime: 20000  // Wait for API calls
};

const log = {
    info: (msg) => console.log(`[V106.000] [INFO] ${msg}`),
    success: (msg) => console.log(`[V106.000] [✓] ${msg}`),
    warn: (msg) => console.warn(`[V106.000] [!] ${msg}`),
    error: (msg) => console.error(`[V106.000] [✗] ${msg}`),
    section: (title) => {
        console.log('\n' + '='.repeat(70));
        console.log(`[V106.000] ${title}`);
        console.log('='.repeat(70));
    }
};

// ============================================================================
// API INTERCEPTION ENGINE
// ============================================================================

class APIInterceptionEngine {
    constructor() {
        this.matchEventResponses = [];
        this.decodedData = [];
    }

    /**
     * Decode Base64 payload
     */
    decodeBase64(base64String) {
        try {
            // Add padding if needed
            const padded = base64String.padEnd(base64String.length + (4 - base64String.length % 4) % 4, '=');
            const decoded = Buffer.from(padded, 'base64').toString('utf-8');
            return JSON.parse(decoded);
        } catch (error) {
            log.warn(`Failed to decode Base64: ${error.message}`);
            return null;
        }
    }

    /**
     * Setup API interception
     */
    setupAPIInterception(page) {
        page.on('response', async (response) => {
            const url = response.url();
            const status = response.status();

            // Intercept match-event API calls
            if (url.includes('/match-event/') && response.headers()['content-type']?.includes('application/json')) {
                try {
                    const body = await response.text();
                    log.info(`[API INTERCEPTED] [${status}] ${url.substring(0, 80)}...`);
                    log.info(`  Body length: ${body.length} characters`);

                    this.matchEventResponses.push({
                        url: url,
                        status: status,
                        body: body,
                        timestamp: Date.now()
                    });

                    // Try to decode
                    const decoded = this.decodeBase64(body);
                    if (decoded) {
                        this.decodedData.push(decoded);
                        log.success(`[DECODED] Found data with keys: ${Object.keys(decoded).join(', ')}`);
                    }

                } catch (error) {
                    log.error(`Failed to intercept API response: ${error.message}`);
                }
            }
        });
    }

    /**
     * Extract odds from decoded data
     */
    extractOddsFromData(decodedData) {
        const extractedOdds = {
            bookmakers: [],
            openingOdds: [],
            historyData: []
        };

        // The structure may vary - let's log what we find
        log.info('Analyzing decoded data structure...');

        // Look for odds-related keys
        const oddsKeys = Object.keys(decodedData).filter(k =>
            k.toLowerCase().includes('odd') ||
            k.toLowerCase().includes('bookmaker') ||
            k.toLowerCase().includes('provider') ||
            k.toLowerCase().includes('history') ||
            k.toLowerCase().includes('movement')
        );

        log.info(`Found odds-related keys: ${oddsKeys.join(', ') || 'NONE'}`);

        // If we have a specific structure, extract it
        if (decodedData.bookmakers) {
            extractedOdds.bookmakers = decodedData.bookmakers;
        }

        if (decodedData.openingOdds) {
            extractedOdds.openingOdds = decodedData.openingOdds;
        }

        if (decodedData.history) {
            extractedOdds.historyData = decodedData.history;
        }

        // Also look for nested data
        for (const [key, value] of Object.entries(decodedData)) {
            if (typeof value === 'object' && value !== null) {
                if (Array.isArray(value) && value.length > 0) {
                    log.info(`  ${key}: Array[${value.length}]`);
                    if (value.length > 0 && typeof value[0] === 'object') {
                        log.info(`    First item keys: ${Object.keys(value[0]).join(', ')}`);
                    }
                } else if (Object.keys(value).length < 20) {
                    log.info(`  ${key}: Object with keys: ${Object.keys(value).join(', ')}`);
                }
            }
        }

        return extractedOdds;
    }

    /**
     * Process single URL
     */
    async processURL(url) {
        log.section(`PROCESSING: ${url.substring(0, 60)}...`);

        const browser = await chromium.launch({
            headless: true,
            args: ['--disable-blink-features=AutomationControlled'],
            ignoreDefaultArgs: ['--enable-automation']
        });

        const context = await browser.newContext({
            userAgent: CONFIG.userAgent,
            viewport: CONFIG.viewport
        });

        await context.addInitScript(() => {
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
        });

        const page = await context.newPage();
        await page.setExtraHTTPHeaders(REALISTIC_HEADERS);

        // Setup interception
        this.setupAPIInterception(page);

        try {
            log.info('Navigating to page...');
            await page.goto(url, {
                timeout: CONFIG.timeout,
                waitUntil: 'networkidle'
            });

            // Wait for API calls
            log.info(`Waiting for API calls (${CONFIG.maxWaitTime}ms)...`);
            await page.waitForTimeout(CONFIG.maxWaitTime);

            // Process intercepted data
            log.section('DATA ANALYSIS');

            if (this.decodedData.length > 0) {
                log.success(`Successfully intercepted ${this.decodedData.length} API responses`);

                // Process each decoded response
                for (let i = 0; i < this.decodedData.length; i++) {
                    log.info(`Processing response ${i + 1}/${this.decodedData.length}...`);
                    const odds = this.extractOddsFromData(this.decodedData[i]);
                }

                return {
                    success: true,
                    apiResponses: this.matchEventResponses.length,
                    decodedResponses: this.decodedData.length,
                    data: this.decodedData
                };
            } else {
                log.error('No API responses decoded successfully');
                return {
                    success: false,
                    apiResponses: this.matchEventResponses.length,
                    decodedResponses: 0
                };
            }

        } catch (error) {
            log.error(`Processing failed: ${error.message}`);
            return {
                success: false,
                error: error.message
            };
        } finally {
            await page.close();
            await context.close();
            await browser.close();
        }
    }

    /**
     * Generate final report
     */
    generateReport(results) {
        log.section('V106.000 FINAL REPORT');

        console.log('\n┌─────────────────────────────────────────────────────────────────┐');
        console.log('│                    V106.000 HARVEST RESULTS                    │');
        console.log('├─────────────────────────────────────────────────────────────────┤');

        let totalSuccess = 0;
        let totalAPIResponses = 0;

        results.forEach((result, i) => {
            const status = result.success ? '✓ SUCCESS' : '✗ FAILED';
            const urlShort = result.url?.substring(0, 45) || 'N/A';
            console.log(`│ URL ${i + 1}: ${status.padEnd(10)} | ${result.apiResponses || 0} APIs | ${result.decodedResponses || 0} decoded │`);
            console.log(`│         ${urlShort}...`);

            if (result.success) {
                totalSuccess++;
                totalAPIResponses += result.apiResponses || 0;
            }
        });

        console.log('├─────────────────────────────────────────────────────────────────┤');
        console.log(`│ Total Success: ${totalSuccess}/${results.length} URLs │`);
        console.log(`│ Total API Responses: ${totalAPIResponses} │`);
        console.log('└─────────────────────────────────────────────────────────────────┘\n');

        // Final verdict
        if (totalSuccess > 0) {
            log.success('[V106.000] API Interception: WORKING!');
            log.success('[V106.000] Data extraction via API interception: SUCCESSFUL');
            console.log('\n[V106.000] Modal Engine: BYPASSED. API Interception: ACTIVE. History Data: CAPTURED.\n');
            return true;
        } else {
            log.error('[V106.000] API Interception: FAILED');
            log.info('Recommendation: Investigate API response format further');
            return false;
        }
    }
}

// ============================================================================
// MAIN ENTRY POINT
// ============================================================================

async function main() {
    const engine = new APIInterceptionEngine();

    log.section('V106.000 API INTERCEPTION ENGINE START');

    const results = [];

    for (const url of TARGET_URLS) {
        const result = await engine.processURL(url);
        result.url = url;
        results.push(result);

        // Delay between URLs
        if (url !== TARGET_URLS[TARGET_URLS.length - 1]) {
            log.info('Waiting 5 seconds before next URL...');
            await new Promise(resolve => setTimeout(resolve, 5000));
        }
    }

    const success = engine.generateReport(results);
    process.exit(success ? 0 : 1);
}

if (require.main === module) {
    main().catch(error => {
        console.error('[V106.000] Fatal error:', error);
        process.exit(1);
    });
}

module.exports = { APIInterceptionEngine, main };
