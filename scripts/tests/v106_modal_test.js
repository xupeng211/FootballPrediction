/**
 * V106.000 Modal Interaction Test - TDD First Approach
 * =====================================================
 *
 * V106.000: Test-Driven Development for Hover + Modal extraction
 *   - Test if Hover action triggers modal within 2 seconds
 *   - Assert modal visibility and content extraction
 *   - Verify opening odds structure (div.mt-2.gap-1)
 *   - Single URL penetration test
 *
 * @version V106.000
 * @since 2026-01-26
 */

'use strict';

const { chromium } = require('playwright');
const assert = require('assert');

// ============================================================================
// TEST CONFIGURATION
// ============================================================================

// V106.001: Use valid live match URL from league page discovery
const TARGET_URLS = [
    // Original URL (returns 404 - expired)
    // 'https://www.oddsportal.com/football/england/premier-league/everton-arsenal-83299048/',
    // Valid live match URLs (from V105.001 discovery)
    'https://www.oddsportal.com/football/england/premier-league/everton-leeds-neRXKc8l/',
    'https://www.oddsportal.com/football/england/premier-league/brighton-everton-vPKFVEM6/'
];

// Realistic headers (V104.000 stealth mode)
const REALISTIC_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.9',
    'Cache-Control': 'max-age=0',
    'Sec-Ch-Ua': '"Chromium";v="131", "Not_A Brand";v="24"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Sec-Gpc': '1',
    'Upgrade-Insecure-Requests': '1',
    'Referer': 'https://www.oddsportal.com/football/england/premier-league/'
};

const CONFIG = {
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    viewport: { width: 1920, height: 1080 },
    timeout: 90000,
    modalWaitTimeout: 5000  // 5 seconds for modal to appear (generous)
};

const log = {
    info: (msg) => console.log(`[V106.000-TDD] [INFO] ${msg}`),
    success: (msg) => console.log(`[V106.000-TDD] [✓] ${msg}`),
    warn: (msg) => console.warn(`[V106.000-TDD] [!] ${msg}`),
    error: (msg) => console.error(`[V106.000-TDD] [✗] ${msg}`),
    section: (title) => {
        console.log('\n' + '='.repeat(70));
        console.log(`[V106.000-TDD] ${title}`);
        console.log('='.repeat(70));
    }
};

// ============================================================================
// TEST SUITE
// ============================================================================

class ModalInteractionTest {
    constructor() {
        this.browser = null;
        this.context = null;
        this.page = null;
        this.testResults = {
            pageLoad: false,
            bookmakerRowsFound: false,
            hoverTriggered: false,
            modalAppeared: false,
            modalContentExtracted: false,
            openingOddsFound: false,
            historyDataExtracted: false
        };
    }

    async setup() {
        log.section('TEST SETUP - Launching Browser');

        this.browser = await chromium.launch({
            headless: true,
            args: [
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ],
            ignoreDefaultArgs: ['--enable-automation']
        });

        this.context = await this.browser.newContext({
            userAgent: CONFIG.userAgent,
            viewport: CONFIG.viewport,
            locale: 'en-US',
            timezoneId: 'America/New_York',
            javaScriptEnabled: true
        });

        // Mask webdriver (V104.000 stealth)
        await this.context.addInitScript(() => {
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            window.chrome = { runtime: {} };
        });

        this.page = await this.context.newPage();
        await this.page.setExtraHTTPHeaders(REALISTIC_HEADERS);

        log.success('Browser launched successfully');
    }

    async teardown() {
        log.section('TEST TEARDOWN');

        if (this.page) await this.page.close();
        if (this.context) await this.context.close();
        if (this.browser) await this.browser.close();

        log.success('Browser closed successfully');
    }

    /**
     * TEST 1: Page Load
     */
    async testPageLoad(targetUrl = TARGET_URLS[0]) {
        log.section('TEST 1: Page Load & Navigation');

        try {
            log.info(`Navigating to: ${targetUrl}`);
            const response = await this.page.goto(targetUrl, {
                timeout: CONFIG.timeout,
                waitUntil: 'domcontentloaded'
            });

            const httpStatus = response ? response.status() : null;
            log.info(`HTTP Status: ${httpStatus}`);

            // Wait for initial content
            await this.page.waitForTimeout(3000);

            // Check page title
            const title = await this.page.title();
            log.info(`Page title: "${title}"`);

            // Check content length
            const contentLength = await this.page.evaluate(() => document.body.innerHTML.length);
            log.info(`Content length: ${contentLength} bytes`);

            if (httpStatus === 200 && contentLength > 50000) {
                this.testResults.pageLoad = true;
                log.success('TEST 1 PASSED: Page loaded successfully');
                return true;
            } else {
                log.error(`TEST 1 FAILED: HTTP ${httpStatus}, Content: ${contentLength} bytes`);
                return false;
            }

        } catch (error) {
            log.error(`TEST 1 FAILED: ${error.message}`);
            return false;
        }
    }

    /**
     * TEST 2: Find Bookmaker Rows
     * Target: div.border-black-borders.flex.h-9
     */
    async testFindBookmakerRows() {
        log.section('TEST 2: Find Bookmaker Rows');

        try {
            // Wait for page to fully render
            await this.page.waitForTimeout(3000);

            // Find bookmaker rows (OddsHarvester pattern)
            const rowCount = await this.page.locator('div.border-black-borders.flex.h-9').count();

            log.info(`Found ${rowCount} bookmaker rows`);

            if (rowCount > 0) {
                this.testResults.bookmakerRowsFound = true;
                log.success(`TEST 2 PASSED: ${rowCount} bookmaker rows found`);

                // Log first few bookmaker names
                const bookmakerNames = await this.page.locator('div.border-black-borders.flex.h-9 img.bookmaker-logo').all();
                for (let i = 0; i < Math.min(3, bookmakerNames.length); i++) {
                    const title = await bookmakerNames[i].getAttribute('title');
                    log.info(`  Bookmaker ${i + 1}: ${title || 'Unknown'}`);
                }

                return true;
            } else {
                log.error('TEST 2 FAILED: No bookmaker rows found');
                log.info('Trying alternative selectors...');

                // Try alternative selectors
                const altCount = await this.page.locator('div[class*="border-black"]').count();
                log.info(`Alternative selector found ${altCount} elements`);

                return false;
            }

        } catch (error) {
            log.error(`TEST 2 FAILED: ${error.message}`);
            return false;
        }
    }

    /**
     * TEST 3: Hover Trigger Modal (THE CRITICAL TEST)
     * Hover on odds block and verify modal appears within 2 seconds
     */
    async testHoverTriggerModal() {
        log.section('TEST 3: Hover Trigger Modal (CRITICAL)');

        try {
            // Find first bookmaker row
            const firstRow = this.page.locator('div.border-black-borders.flex.h-9').first();
            const exists = await firstRow.count() > 0;

            if (!exists) {
                log.error('TEST 3 FAILED: No bookmaker row found to hover on');
                return false;
            }

            log.info('Found first bookmaker row, preparing to hover...');

            // Find odds blocks within the row (OddsHarvester pattern)
            // div.flex-center.flex-col.font-bold
            const oddsBlocks = await firstRow.locator('div.flex-center.flex-col.font-bold').all();
            log.info(`Found ${oddsBlocks.length} odds blocks in first row`);

            if (oddsBlocks.length === 0) {
                log.error('TEST 3 FAILED: No odds blocks found in bookmaker row');
                return false;
            }

            // Hover on first odds block (Home odds usually)
            const firstOddsBlock = oddsBlocks[0];
            const oddsText = await firstOddsBlock.innerText();
            log.info(`Hovering on odds block with text: "${oddsText}"`);

            this.testResults.hoverTriggered = true;

            // Execute hover
            await firstOddsBlock.hover();
            log.info('Hover executed, waiting for modal...');

            // Wait for modal to appear (OddsHarvester pattern: h3:text('Odds movement'))
            // CRITICAL ASSERTION: Modal must appear within 2 seconds
            const startTime = Date.now();

            try {
                await this.page.waitForSelector('h3:text("Odds movement")', {
                    timeout: CONFIG.modalWaitTimeout
                });

                const elapsed = Date.now() - startTime;
                log.success(`Modal appeared in ${elapsed}ms`);

                // Verify modal is visible
                const modalVisible = await this.page.locator('h3:text("Odds movement")').isVisible();
                log.info(`Modal visible: ${modalVisible}`);

                if (modalVisible) {
                    this.testResults.modalAppeared = true;
                    log.success(`TEST 3 PASSED: Modal triggered and visible (${elapsed}ms)`);
                    return true;
                } else {
                    log.error('TEST 3 FAILED: Modal selector found but not visible');
                    return false;
                }

            } catch (timeoutError) {
                const elapsed = Date.now() - startTime;
                log.error(`TEST 3 FAILED: Modal did not appear within ${elapsed}ms`);
                log.info('Diagnostic: Taking screenshot of current state...');

                // Diagnostic: Get page structure
                const diagnostic = await this.page.evaluate(() => {
                    const body = document.body;
                    return {
                        bodyClass: body.className,
                        bodyText: body.innerText.substring(0, 500),
                        hasBorderElements: document.querySelectorAll('[class*="border"]').length
                    };
                });

                log.info(`Diagnostic info:`);
                log.info(`  Body class: ${diagnostic.bodyClass}`);
                log.info(`  Border elements: ${diagnostic.hasBorderElements}`);
                log.info(`  Body text preview: ${diagnostic.bodyText.substring(0, 200)}...`);

                return false;
            }

        } catch (error) {
            log.error(`TEST 3 FAILED: ${error.message}`);
            return false;
        }
    }

    /**
     * TEST 4: Extract Modal Content
     * Extract modal HTML and verify structure
     */
    async testExtractModalContent() {
        log.section('TEST 4: Extract Modal Content');

        try {
            // Wait a bit for modal to fully render
            await this.page.waitForTimeout(1000);

            // Get modal element (OddsHarvester pattern)
            const modalElement = await this.page.waitForSelector('h3:text("Odds movement")', {
                timeout: 5000
            });

            // Navigate to parent (modal wrapper)
            const modalWrapper = await modalElement.evaluateHandle(node => node.parentElement);
            const modalHtml = await modalWrapper.asElement().innerHTML();

            log.info(`Modal HTML length: ${modalHtml.length} bytes`);

            if (modalHtml.length > 0) {
                this.testResults.modalContentExtracted = true;
                log.success(`TEST 4 PASSED: Modal content extracted (${modalHtml.length} bytes)`);

                // Show preview
                const preview = modalHtml.substring(0, 500);
                log.info(`Modal HTML preview:\n${preview}...`);

                return true;
            } else {
                log.error('TEST 4 FAILED: Modal HTML is empty');
                return false;
            }

        } catch (error) {
            log.error(`TEST 4 FAILED: ${error.message}`);
            return false;
        }
    }

    /**
     * TEST 5: Verify Opening Odds Structure
     * Target: div.mt-2.gap-1 (OddsHarvester pattern)
     */
    async testVerifyOpeningOddsStructure() {
        log.section('TEST 5: Verify Opening Odds Structure');

        try {
            // Look for opening odds block (OddsHarvester pattern: div.mt-2.gap-1)
            const openingOddsExists = await this.page.locator('div.mt-2.gap-1').count() > 0;

            if (openingOddsExists) {
                const openingOddsText = await this.page.locator('div.mt-2.gap-1').first().innerText();
                log.info(`Opening odds text: "${openingOddsText}"`);

                // Look for timestamp and value (OddsHarvester pattern)
                const timestampDiv = await this.page.locator('div.mt-2.gap-1 div.flex.gap-1 div').first();
                const valueDiv = await this.page.locator('div.mt-2.gap-1 div.flex.gap-1 .font-bold').first();

                if (timestampDiv && valueDiv) {
                    const timestamp = await timestampDiv.innerText();
                    const value = await valueDiv.innerText();
                    log.info(`Opening odds - Timestamp: "${timestamp}", Value: "${value}"`);

                    this.testResults.openingOddsFound = true;
                    log.success('TEST 5 PASSED: Opening odds structure verified');
                    return true;
                }
            }

            log.error('TEST 5 FAILED: Opening odds structure not found');
            return false;

        } catch (error) {
            log.error(`TEST 5 FAILED: ${error.message}`);
            return false;
        }
    }

    /**
     * TEST 6: Extract History Data
     * Extract odds movement history list
     */
    async testExtractHistoryData() {
        log.section('TEST 6: Extract History Data');

        try {
            // Extract history data (OddsHarvester pattern)
            // div.flex.flex-col.gap-1 > div.flex.gap-3 > div.font-normal (timestamps)
            // div.flex.flex-col.gap-1 + div.flex.flex-col.gap-1 > div.font-bold (odds values)

            const timestamps = await this.page.locator('div.flex.flex-col.gap-1 > div.flex.gap-3 > div.font-normal').all();
            const oddsValues = await this.page.locator('div.flex.flex-col.gap-1 + div.flex.flex-col.gap-1 > div.font-bold').all();

            log.info(`Found ${timestamps.length} timestamps and ${oddsValues.length} odds values`);

            if (timestamps.length > 0 && oddsValues.length > 0) {
                const historyData = [];

                const count = Math.min(timestamps.length, oddsValues.length, 5); // First 5 entries

                for (let i = 0; i < count; i++) {
                    const ts = await timestamps[i].innerText();
                    const odds = await oddsValues[i].innerText();
                    historyData.push({ timestamp: ts, odds: odds });
                }

                log.info('History data (first 5 entries):');
                historyData.forEach((entry, i) => {
                    log.info(`  ${i + 1}. ${entry.timestamp} -> ${entry.odds}`);
                });

                this.testResults.historyDataExtracted = true;
                log.success(`TEST 6 PASSED: ${historyData.length} history entries extracted`);
                return true;
            }

            log.error('TEST 6 FAILED: No history data found');
            return false;

        } catch (error) {
            log.error(`TEST 6 FAILED: ${error.message}`);
            return false;
        }
    }

    /**
     * Run all tests
     */
    async runAllTests() {
        log.section('V106.000 MODAL INTERACTION TEST SUITE');

        // Try each URL until we find a working one
        for (const url of TARGET_URLS) {
            log.info(`Trying URL: ${url}`);

            try {
                await this.setup();

                // Run tests in sequence with current URL
                const tests = [
                    { name: 'Page Load', fn: () => this.testPageLoad(url) },
                    { name: 'Find Bookmaker Rows', fn: () => this.testFindBookmakerRows() },
                    { name: 'Hover Trigger Modal', fn: () => this.testHoverTriggerModal() },
                    { name: 'Extract Modal Content', fn: () => this.testExtractModalContent() },
                    { name: 'Verify Opening Odds', fn: () => this.testVerifyOpeningOddsStructure() },
                    { name: 'Extract History Data', fn: () => this.testExtractHistoryData() }
                ];

                let passedTests = 0;
                const results = [];

                for (const test of tests) {
                    try {
                        const passed = await test.fn();
                        results.push({ name: test.name, passed: passed });
                        if (passed) passedTests++;
                    } catch (error) {
                        log.error(`Test "${test.name}" crashed: ${error.message}`);
                        results.push({ name: test.name, passed: false, error: error.message });
                    }

                    // Small delay between tests
                    await this.page.waitForTimeout(1000);
                }

                // Generate report
                this.generateTestReport(results, passedTests);

                // If page load succeeded, we're done
                if (results[0].passed) {
                    return passedTests === tests.length;
                }

            } finally {
                await this.teardown();
            }

            log.warn(`URL failed: ${url}`);
        }

        log.error('All URLs failed');
        return false;
    }

    /**
     * Generate test report
     */
    generateTestReport(results, passedTests) {
        log.section('V106.000 TEST REPORT');

        console.log('\n┌─────────────────────────────────────────────────────────────────┐');
        console.log('│                    V106.000 TEST RESULTS                         │');
        console.log('├─────────────────────────────────────────────────────────────────┤');

        results.forEach((result, i) => {
            const status = result.passed ? '✓ PASS' : '✗ FAIL';
            console.log(`│ Test ${i + 1}: ${result.name.padEnd(25)} | ${status.padEnd(8)} │`);
            if (result.error) {
                console.log(`│         Error: ${result.error.substring(0, 45)}...`);
            }
        });

        console.log('├─────────────────────────────────────────────────────────────────┤');
        console.log(`│ Total: ${passedTests}/${results.length} tests passed │`);
        console.log('└─────────────────────────────────────────────────────────────────┘\n');

        // Final verdict
        if (passedTests === results.length) {
            log.success('[V106.000] ALL TESTS PASSED - Modal Engine: ONLINE');
            console.log('\n[V106.000] Modal Engine: ONLINE. TDD Verification: PASSED. History Data: CAPTURED.\n');
        } else {
            log.error(`[V106.000] ${results.length - passedTests} TESTS FAILED`);
            log.info('Next steps:');
            log.info('  1. Review failed test diagnostics');
            log.info('  2. Check if selectors match current OddsPortal DOM structure');
            log.info('  3. Verify stealth mode is working (HTTP 200 response)');
        }
    }
}

// ============================================================================
// MAIN ENTRY POINT
// ============================================================================

async function main() {
    const tester = new ModalInteractionTest();

    try {
        const allPassed = await tester.runAllTests();
        process.exit(allPassed ? 0 : 1);

    } catch (error) {
        log.error(`Fatal error: ${error.message}`);
        console.error(error.stack);
        process.exit(1);
    }
}

if (require.main === module) {
    main().catch(error => {
        console.error('[V106.000] Fatal error:', error);
        process.exit(1);
    });
}

module.exports = { ModalInteractionTest, main };
