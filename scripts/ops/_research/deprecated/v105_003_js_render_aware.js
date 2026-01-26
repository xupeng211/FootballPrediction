/**
 * V105.003 JavaScript-Aware Harvester - Dynamic Content Rendering
 * ===============================================================
 *
 * V105.003: Handle JavaScript-rendered content on detail pages
 *   - Extended wait times for JS execution
 *   - Force scroll to trigger lazy loading
 *   - Multiple content sampling attempts
 *   - XHR interception to detect API calls
 *
 * @version V105.003
 * @since 2026-01-26
 */

'use strict';

const { chromium } = require('playwright');

const LIVE_MATCH_URLS = [
    'https://www.oddsportal.com/football/england/premier-league/everton-leeds-neRXKc8l/',
    'https://www.oddsportal.com/football/england/premier-league/brighton-everton-vPKFVEM6/'
];

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
    maxWaitTime: 30000  // Maximum wait for JS rendering
};

const log = {
    info: (msg) => console.log(`[V105.003] [INFO] ${msg}`),
    success: (msg) => console.log(`[V105.003] [SUCCESS] ${msg}`),
    warn: (msg) => console.warn(`[V105.003] [WARN] ${msg}`),
    error: (msg) => console.error(`[V105.003] [ERROR] ${msg}`),
    section: (title) => {
        console.log('\n' + '='.repeat(70));
        console.log(`[V105.003] ${title}`);
        console.log('='.repeat(70));
    }
};

// ============================================================================
// JS-AWARE HARVESTER CLASS
// ============================================================================

class JSAwareHarvester {
    constructor() {
        this.apiCalls = [];
    }

    /**
     * V105.003: Set up XHR interception to detect API calls
     */
    setupXHRInterception(page) {
        page.on('response', async (response) => {
            const url = response.url();
            const contentType = response.headers()['content-type'] || '';

            // Capture JSON API calls
            if (url.includes('/api/') || contentType.includes('application/json')) {
                this.apiCalls.push({
                    url: url,
                    status: response.status(),
                    contentType: contentType,
                    timestamp: Date.now()
                });
                log.info(`[API] ${response.status()} ${url.substring(0, 80)}...`);
            }
        });
    }

    /**
     * V105.003: Force scroll and interaction to trigger lazy loading
     */
    async forceScrollAndInteraction(page) {
        log.info('Forcing scroll and interaction...');

        try {
            // Scroll down progressively
            for (let i = 0; i < 5; i++) {
                await page.evaluate((scrollAmount) => {
                    window.scrollBy(0, scrollAmount);
                }, 300);
                await page.waitForTimeout(500);
            }

            // Scroll back up
            await page.evaluate(() => {
                window.scrollTo(0, 0);
            });
            await page.waitForTimeout(1000);

        } catch (e) {
            log.warn(`Scroll interaction failed: ${e.message}`);
        }
    }

    /**
     * V105.003: Wait for content with multiple sampling attempts
     */
    async waitForContentWithRetry(page, maxAttempts = 10) {
        log.info(`Waiting for content (max ${maxAttempts} attempts)...`);

        for (let attempt = 1; attempt <= maxAttempts; attempt++) {
            await page.waitForTimeout(2000); // Wait 2 seconds between attempts

            const analysis = await page.evaluate(() => {
                const bodyText = document.body.innerText || '';
                const keywords = ['1X2', 'odds', 'Opening', 'Pinnacle', 'Bet365', 'betting'];
                const found = keywords.filter(k => bodyText.toLowerCase().includes(k.toLowerCase()));

                const floatPattern = /\b([1-9]\.\d{2}|1\d\.\d{2}|20\.00)\b/g;
                const matches = bodyText.match(floatPattern) || [];
                const uniqueOdds = [...new Set(matches)].length;

                const tables = document.querySelectorAll('table').length;
                const tabs = document.querySelectorAll('[role="tab"], .tab, [class*="tab"]').length;

                return {
                    attempt: attempt,
                    keywords: found,
                    oddsCount: uniqueOdds,
                    tables: tables,
                    tabs: tabs,
                    bodyLength: bodyText.length
                };
            });

            log.info(`Attempt ${attempt}: ${analysis.keywords.length} keywords, ${analysis.oddsCount} odds, ${analysis.tables} tables, ${analysis.tabs} tabs`);

            // Success check
            if (analysis.keywords.length >= 3 && analysis.oddsCount >= 5) {
                log.success(`Content detected at attempt ${attempt}!`);
                return { success: true, analysis: analysis };
            }
        }

        log.warn('No substantial content detected after all attempts');
        return { success: false, analysis: null };
    }

    /**
     * V105.003: Harvest detail page with JS awareness
     */
    async harvestDetailPage(url, urlIndex) {
        log.section(`HARVEST ${urlIndex + 1}: ${url.substring(0, 60)}...`);

        let browser = null;
        let context = null;
        let page = null;

        try {
            // Launch browser
            browser = await chromium.launch({
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

            context = await browser.newContext({
                userAgent: CONFIG.userAgent,
                viewport: CONFIG.viewport,
                locale: 'en-US',
                timezoneId: 'America/New_York',
                javaScriptEnabled: true
            });

            // Mask webdriver
            await context.addInitScript(() => {
                Object.defineProperty(navigator, 'webdriver', { get: () => false });
                window.chrome = { runtime: {} };
            });

            page = await context.newPage();
            await page.setExtraHTTPHeaders(REALISTIC_HEADERS);

            // Set up XHR interception
            this.setupXHRInterception(page);

            // Navigate
            log.info('Navigating...');
            const startTime = Date.now();
            const response = await page.goto(url, {
                timeout: CONFIG.timeout,
                waitUntil: 'networkidle' // Wait for network to be idle
            });
            const loadTime = Date.now() - startTime;
            log.info(`Initial load: ${loadTime}ms, HTTP ${response ? response.status() : 'NO_RESPONSE'}`);

            // Wait for body
            try {
                await page.waitForSelector('body', { state: 'attached', timeout: 10000 });
            } catch (e) {
                // Continue anyway
            }

            // Force scroll and interaction
            await this.forceScrollAndInteraction(page);

            // Wait for content with retry
            const contentResult = await this.waitForContentWithRetry(page, 10);

            // Final analysis
            const finalAnalysis = await page.evaluate(() => {
                const bodyText = document.body.innerText || '';
                const innerHTML = document.body.innerHTML || '';

                // Get all text content
                const allText = bodyText.substring(0, 5000); // First 5000 chars

                // Look for odds
                const floatPattern = /\b([1-9]\.\d{2}|1\d\.\d{2}|20\.00)\b/g;
                const matches = bodyText.match(floatPattern) || [];

                return {
                    title: document.title,
                    bodyLength: bodyText.length,
                    htmlLength: innerHTML.length,
                    textPreview: allText,
                    uniqueOdds: [...new Set(matches)].slice(0, 30),
                    tables: document.querySelectorAll('table').length,
                    divsWithOdds: document.querySelectorAll('div[class*="odd"], div[id*="odd"], [class*="bet"]').length
                };
            });

            const result = {
                url: url,
                urlIndex: urlIndex,
                httpStatus: response ? response.status() : null,
                loadTime: loadTime,
                success: contentResult.success,
                contentAnalysis: contentResult.analysis,
                finalAnalysis: finalAnalysis,
                apiCalls: this.apiCalls.slice(),
                timestamp: Date.now()
            };

            // Report
            if (contentResult.success) {
                log.success('=== HARVEST SUCCESS ===');
                log.success(`Title: ${finalAnalysis.title}`);
                log.success(`Odds found: ${finalAnalysis.uniqueOdds.slice(0, 10).join(', ')}...`);
                log.success(`Tables: ${finalAnalysis.tables}, Divs with odds: ${finalAnalysis.divsWithOdds}`);
            } else {
                log.error('=== HARVEST FAILED ===');
                log.error(`Title: ${finalAnalysis.title}`);
                log.error(`Body length: ${finalAnalysis.bodyLength}, HTML length: ${finalAnalysis.htmlLength}`);
                log.error(`Text preview: ${finalAnalysis.textPreview.substring(0, 200)}...`);
            }

            log.info(`API calls detected: ${this.apiCalls.length}`);

            return result;

        } catch (error) {
            log.error(`Harvest failed: ${error.message}`);
            return {
                url: url,
                urlIndex: urlIndex,
                success: false,
                error: error.message
            };
        } finally {
            if (page) await page.close();
            if (context) await context.close();
            if (browser) await browser.close();
            this.apiCalls = []; // Reset for next harvest
        }
    }

    /**
     * V105.003: Run harvest cycle
     */
    async runHarvestCycle() {
        log.section('V105.003 JS-AWARE HARVEST CYCLE START');

        const results = [];

        for (let i = 0; i < LIVE_MATCH_URLS.length; i++) {
            const result = await this.harvestDetailPage(LIVE_MATCH_URLS[i], i);
            results.push(result);

            // Delay between requests
            if (i < LIVE_MATCH_URLS.length - 1) {
                log.info('Waiting 10 seconds before next harvest...');
                await new Promise(resolve => setTimeout(resolve, 10000));
            }
        }

        // Generate report
        this.generateReport(results);

        return results;
    }

    /**
     * V105.003: Generate final report
     */
    generateReport(results) {
        log.section('V105.003 FINAL HARVEST REPORT');

        console.log('\n┌─────────────────────────────────────────────────────────────────┐');
        console.log('│                    V105.003 HARVEST RESULTS                        │');
        console.log('├─────────────────────────────────────────────────────────────────┤');

        results.forEach((result, i) => {
            const status = result.success ? '✓ SUCCESS' : '✗ FAILED';
            const urlShort = result.url?.substring(0, 45) || 'N/A';
            console.log(`│ Harvest ${i + 1}: ${status.padEnd(10)} | HTTP ${result.httpStatus || 'N/A'} | ${result.loadTime || 0}ms │`);
            console.log(`│             URL: ${urlShort}...`);
            if (result.finalAnalysis) {
                console.log(`│             Title: "${result.finalAnalysis.title.substring(0, 40)}..."`);
                console.log(`│             Body: ${result.finalAnalysis.bodyLength} bytes, HTML: ${result.finalAnalysis.htmlLength} bytes`);
            }
            if (result.success) {
                console.log(`│             Odds: ${result.finalAnalysis?.uniqueOdds.slice(0, 8).join(', ') || 'NONE'}...`);
            }
            console.log(`│             API calls: ${result.apiCalls?.length || 0}`);
            if (result.contentAnalysis) {
                console.log(`│             Final attempt: ${result.contentAnalysis.keywords?.length || 0} keywords, ${result.contentAnalysis.oddsCount || 0} odds`);
            }
            console.log('├─────────────────────────────────────────────────────────────────┤');
        });

        console.log('└─────────────────────────────────────────────────────────────────┘\n');

        // Final verdict
        log.section('V105.003 FINAL VERDICT');

        const successCount = results.filter(r => r.success).length;
        if (successCount > 0) {
            log.success(`[SUCCESS] ${successCount}/${results.length} pages harvested successfully!`);
            log.info('The JS-aware approach is working. Ready for production integration.');
        } else {
            log.error('[FAILED] All pages still failed');
            log.info('Possible issues:');
            log.info('  1. OddsPortal may require account login');
            log.info('  2. Geographic restrictions may apply');
            log.info('  3. More complex JavaScript execution may be needed');
            log.info('  4. Consider using puppeteer-extra with stealth plugin');
        }
    }
}

// ============================================================================
// MAIN ENTRY POINT
// ============================================================================

async function main() {
    const harvester = new JSAwareHarvester();

    try {
        const results = await harvester.runHarvestCycle();

        // Exit with appropriate code
        const anySuccess = results.some(r => r.success);
        process.exit(anySuccess ? 0 : 1);

    } catch (error) {
        log.error(`Fatal error: ${error.message}`);
        console.error(error.stack);
        process.exit(1);
    }
}

if (require.main === module) {
    main().catch(error => {
        console.error('[V105.003] Fatal error:', error);
        process.exit(1);
    });
}

module.exports = { JSAwareHarvester, main };
