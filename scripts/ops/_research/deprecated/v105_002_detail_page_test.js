/**
 * V105.002 Detail Page Validation - Live Match Test
 * =================================================
 *
 * V105.002: Test detail page extraction with live match URLs
 *   - Use current valid match URLs from league page
 *   - Full content verification (1X2, Opening odds)
 *   - Data extraction validation
 *
 * @version V105.002
 * @since 2026-01-26
 */

'use strict';

const { chromium } = require('playwright');

// ============================================================================
// CONFIGURATION
// ============================================================================

// Live match URLs found in league page
const LIVE_MATCH_URLS = [
    'https://www.oddsportal.com/football/england/premier-league/everton-leeds-neRXKc8l/',
    'https://www.oddsportal.com/football/england/premier-league/brighton-everton-vPKFVEM6/',
    'https://www.oddsportal.com/football/england/premier-league/fulham-everton-MqW2ea1b/'
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
    timeout: 60000
};

const log = {
    info: (msg) => console.log(`[V105.002] [INFO] ${msg}`),
    success: (msg) => console.log(`[V105.002] [SUCCESS] ${msg}`),
    warn: (msg) => console.warn(`[V105.002] [WARN] ${msg}`),
    error: (msg) => console.error(`[V105.002] [ERROR] ${msg}`),
    section: (title) => {
        console.log('\n' + '='.repeat(70));
        console.log(`[V105.002] ${title}`);
        console.log('='.repeat(70));
    }
};

// ============================================================================
// DETAIL PAGE VALIDATOR CLASS
// ============================================================================

class DetailPageValidator {
    /**
     * V105.002: Extract and validate odds data from detail page
     */
    async validateDetailPage(url) {
        log.section(`VALIDATING: ${url.substring(0, 60)}...`);

        let browser = null;
        let context = null;
        let page = null;

        try {
            // Launch browser with stealth mode
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

            // Navigate to detail page
            log.info('Navigating to detail page...');
            const response = await page.goto(url, {
                timeout: CONFIG.timeout,
                waitUntil: 'domcontentloaded'
            });

            const httpStatus = response ? response.status() : null;
            log.info(`HTTP Status: ${httpStatus}`);

            // Wait for content
            await page.waitForTimeout(3000);

            // Get page info
            const title = await page.title();
            const content = await page.content();
            const contentLength = content.length;

            log.info(`Title: "${title}"`);
            log.info(`Content length: ${contentLength} bytes`);

            const result = {
                url: url,
                httpStatus: httpStatus,
                title: title,
                contentLength: contentLength,
                success: false,
                errors: []
            };

            // Check for blocking
            if (httpStatus === 404 || httpStatus === 403) {
                result.errors.push('HTTP_BLOCKING');
                log.error(`[BLOCKING] HTTP ${httpStatus}`);
                return result;
            }

            if (contentLength < 1000) {
                result.errors.push('LOW_CONTENT');
                log.error('[LOW CONTENT] Suspiciously small page');
                return result;
            }

            // Deep content analysis
            const analysis = await page.evaluate(() => {
                const analysis = {
                    bettingKeywords: [],
                    oddsPatterns: [],
                    tableElements: 0,
                    buttonsFound: 0,
                    tabElements: 0
                };

                // Check for betting keywords
                const keywords = ['1X2', 'Opening odds', 'Home/Draw/Away', 'Pinnacle', 'Bet365', 'betting'];
                const bodyText = document.body.innerText || '';

                for (const kw of keywords) {
                    if (bodyText.toLowerCase().includes(kw.toLowerCase())) {
                        analysis.bettingKeywords.push(kw);
                    }
                }

                // Count structural elements
                analysis.tableElements = document.querySelectorAll('table').length;
                analysis.buttonsFound = document.querySelectorAll('button, [role="button"]').length;
                analysis.tabElements = document.querySelectorAll('[role="tab"], .tab, [class*="tab"]').length;

                // Look for odds patterns
                const floatPattern = /\b([1-9]\.\d{2}|1\d\.\d{2}|20\.00)\b/g;
                const matches = bodyText.match(floatPattern) || [];
                analysis.oddsPatterns = [...new Set(matches)].slice(0, 20); // Unique values, first 20

                return analysis;
            });

            result.analysis = analysis;

            log.info(`Tables: ${analysis.tableElements}, Buttons: ${analysis.buttonsFound}, Tabs: ${analysis.tabElements}`);
            log.info(`Keywords: ${analysis.bettingKeywords.join(', ') || 'NONE'}`);
            log.info(`Odds patterns: ${analysis.oddsPatterns.length} unique values`);

            // Success criteria
            const hasKeywords = analysis.bettingKeywords.length >= 2;
            const hasOdds = analysis.oddsPatterns.length >= 5;
            const hasStructure = analysis.tableElements > 0 || analysis.tabElements > 0;

            if (hasKeywords && hasOdds && hasStructure) {
                result.success = true;
                log.success('[VALIDATION] Detail page content verified!');
                log.success(`  - Keywords: ${analysis.bettingKeywords.join(', ')}`);
                log.success(`  - Odds: ${analysis.oddsPatterns.slice(0, 5).join(', ')}...`);
                log.success(`  - Structure: ${analysis.tableElements} tables, ${analysis.tabElements} tabs`);
            } else {
                log.error('[VALIDATION] Content incomplete:');
                if (!hasKeywords) log.error('  - Missing betting keywords');
                if (!hasOdds) log.error('  - Missing odds patterns');
                if (!hasStructure) log.error('  - Missing table/tab structure');
                result.errors.push('INCOMPLETE_CONTENT');
            }

            return result;

        } catch (error) {
            log.error(`Validation failed: ${error.message}`);
            return {
                url: url,
                success: false,
                errors: ['FATAL_ERROR'],
                fatalError: error.message
            };
        } finally {
            if (page) await page.close();
            if (context) await context.close();
            if (browser) await browser.close();
        }
    }

    /**
     * V105.002: Run validation on all live matches
     */
    async runValidation() {
        log.section('V105.002 DETAIL PAGE VALIDATION START');

        const results = [];

        for (let i = 0; i < LIVE_MATCH_URLS.length; i++) {
            const result = await this.validateDetailPage(LIVE_MATCH_URLS[i]);
            results.push(result);

            // Delay between requests
            if (i < LIVE_MATCH_URLS.length - 1) {
                log.info('Waiting 5 seconds...');
                await new Promise(resolve => setTimeout(resolve, 5000));
            }
        }

        // Generate report
        this.generateReport(results);

        return results;
    }

    /**
     * V105.002: Generate validation report
     */
    generateReport(results) {
        log.section('V105.002 VALIDATION REPORT');

        console.log('\n┌─────────────────────────────────────────────────────────────────┐');
        console.log('│                    V105.002 VALIDATION RESULTS                    │');
        console.log('├─────────────────────────────────────────────────────────────────┤');

        results.forEach((result, i) => {
            const status = result.success ? '✓ PASS' : '✗ FAIL';
            const urlShort = result.url?.substring(0, 45) || 'N/A';
            console.log(`│ Test ${i + 1}: ${status.padEnd(8)} | HTTP ${result.httpStatus || 'N/A'} | ${result.contentLength || 0} bytes │`);
            console.log(`│         URL: ${urlShort}...`);
            console.log(`│         Title: "${(result.title || '').substring(0, 40)}..."`);
            if (result.analysis) {
                console.log(`│         Tables: ${result.analysis.tableElements} | Tabs: ${result.analysis.tabElements}`);
                console.log(`│         Keywords: ${result.analysis.bettingKeywords.join(', ') || 'NONE'}`);
                console.log(`│         Odds: ${result.analysis.oddsPatterns.slice(0, 5).join(', ') || 'NONE'}...`);
            }
            console.log(`│         Errors: ${result.errors?.join(', ') || 'NONE'}`);
            console.log('├─────────────────────────────────────────────────────────────────┤');
        });

        console.log('└─────────────────────────────────────────────────────────────────┘\n');

        // Final verdict
        log.section('V105.002 FINAL VERDICT');

        const successCount = results.filter(r => r.success).length;
        if (successCount === results.length) {
            log.success(`[SUCCESS] All ${results.length} detail pages validated successfully!`);
            log.info('Next step: Integrate into main harvesting system');
        } else if (successCount > 0) {
            log.warn(`[PARTIAL] ${successCount}/${results.length} pages succeeded`);
            log.info('Some detail pages are accessible, others may be geo-blocked');
        } else {
            log.error('[FAILED] All detail pages failed validation');
            log.info('Need to investigate anti-bot protections further');
        }
    }
}

// ============================================================================
// MAIN ENTRY POINT
// ============================================================================

async function main() {
    const validator = new DetailPageValidator();

    try {
        const results = await validator.runValidation();

        // Exit with appropriate code
        const allSuccess = results.every(r => r.success);
        process.exit(allSuccess ? 0 : 1);

    } catch (error) {
        log.error(`Fatal error: ${error.message}`);
        console.error(error.stack);
        process.exit(1);
    }
}

if (require.main === module) {
    main().catch(error => {
        console.error('[V105.002] Fatal error:', error);
        process.exit(1);
    });
}

module.exports = { DetailPageValidator, main };
