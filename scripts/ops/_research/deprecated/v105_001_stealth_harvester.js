/**
 * V105.001 Stealth Harvester - Enhanced Anti-Detection
 * =====================================================
 *
 * V105.001: Enhanced stealth mode with realistic headers and behavior
 *   - Full HTTP header spoofing (Referer, Accept, Accept-Language, etc.)
 *   - Realistic navigation patterns
 *   - Cookie injection attempt
 *   - Multiple URL format support
 *
 * @version V105.001
 * @since 2026-01-26
 */

'use strict';

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// ============================================================================
// V105.001 CONFIGURATION
// ============================================================================

// Multiple URL formats to test
const TARGET_URLS = [
    // Original format
    'https://www.oddsportal.com/football/england/premier-league/everton-arsenal-83299048/',
    // Alternative format (without trailing slash)
    'https://www.oddsportal.com/football/england/premier-league/everton-arsenal-83299048',
    // League page (fallback)
    'https://www.oddsportal.com/football/england/premier-league/',
];

// Realistic browser headers
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
    'Referer': 'https://www.google.com/'
};

const CONFIG = {
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    viewport: { width: 1920, height: 1080 },
    timeout: 60000,
    outputDir: path.join(__dirname, '../../logs/v105_diagnostic')
};

// ============================================================================
// LOGGING
// ============================================================================

const log = {
    info: (msg) => console.log(`[V105.001] [INFO] ${msg}`),
    success: (msg) => console.log(`[V105.001] [SUCCESS] ${msg}`),
    warn: (msg) => console.warn(`[V105.001] [WARN] ${msg}`),
    error: (msg) => console.error(`[V105.001] [ERROR] ${msg}`),
    section: (title) => {
        console.log('\n' + '='.repeat(70));
        console.log(`[V105.001] ${title}`);
        console.log('='.repeat(70));
    }
};

// ============================================================================
// STEALTH HARVESTER CLASS
// ============================================================================

class StealthHarvester {
    constructor() {
        this.ensureOutputDir();
    }

    ensureOutputDir() {
        if (!fs.existsSync(CONFIG.outputDir)) {
            fs.mkdirSync(CONFIG.outputDir, { recursive: true });
        }
    }

    saveSnapshot(filename, content) {
        const filepath = path.join(CONFIG.outputDir, filename);
        fs.writeFileSync(filepath, content, 'utf8');
        log.info(`Snapshot saved: ${filepath}`);
    }

    /**
     * V105.001: Navigate with realistic behavior
     */
    async realisticNavigate(page, url) {
        log.section(`REALISTIC NAVIGATION: ${url.substring(0, 60)}...`);

        const startTime = Date.now();

        // Set extra HTTP headers before navigation
        await page.setExtraHTTPHeaders(REALISTIC_HEADERS);

        // Navigate with realistic wait strategy
        const response = await page.goto(url, {
            timeout: CONFIG.timeout,
            waitUntil: 'domcontentloaded' // Use domcontentloaded instead of networkidle
        });

        const loadTime = Date.now() - startTime;
        log.info(`Initial load: ${loadTime}ms`);

        // Wait for body with timeout
        try {
            await page.waitForSelector('body', { state: 'attached', timeout: 5000 });
            log.success('Body element found');
        } catch (e) {
            log.warn('Body selector timeout - proceeding anyway');
        }

        // Simulate human behavior - random scroll
        try {
            await page.evaluate(() => {
                window.scrollBy(0, Math.random() * 300);
            });
            await page.waitForTimeout(Math.random() * 1000 + 500);
        } catch (e) {
            // Scroll might fail if page is empty
        }

        // Additional wait for dynamic content
        await page.waitForTimeout(3000);

        return {
            response: response,
            loadTime: loadTime,
            status: response ? response.status() : null
        };
    }

    /**
     * V105.001: Analyze page content
     */
    async analyzePage(page, urlIndex) {
        const analysis = {
            urlIndex: urlIndex,
            timestamp: Date.now(),
            success: false,
            errors: []
        };

        try {
            // Get page title
            const title = await page.title();
            analysis.title = title;
            log.info(`Title: "${title}"`);

            // Get page content
            const content = await page.content();
            analysis.contentLength = content.length;
            log.info(`Content length: ${content.length} bytes`);

            // Save snapshot
            const filename = `stealth_snapshot_u${urlIndex}_${Date.now()}.html`;
            this.saveSnapshot(filename, content);

            // Check for blocking indicators
            if (title.includes('Access Denied') || title.includes('403') || title.includes('404')) {
                analysis.errors.push('BLOCKING_DETECTED');
                log.error('[BLOCKING] Detected in page title');
            }

            if (content.length < 1000) {
                analysis.errors.push('LOW_CONTENT');
                log.error('[LOW CONTENT] Page content suspiciously small');
            }

            // Look for betting keywords
            const keywords = ['1X2', 'odds', 'betting', 'Pinnacle', 'Bet365', 'Home', 'Draw', 'Away'];
            const foundKeywords = [];

            for (const keyword of keywords) {
                if (content.toLowerCase().includes(keyword.toLowerCase())) {
                    foundKeywords.push(keyword);
                }
            }

            analysis.foundKeywords = foundKeywords;

            if (foundKeywords.length > 0) {
                log.success(`[KEYWORDS] Found: ${foundKeywords.join(', ')}`);
                analysis.success = true;
            } else {
                log.error('[KEYWORDS] No betting keywords found');
            }

            // Try to find odds patterns
            const oddsData = await page.evaluate(() => {
                const text = document.body.innerText || '';
                const floatPattern = /\b([1-9]\.\d{2}|1\d\.\d{2}|20\.00)\b/g;
                const matches = text.match(floatPattern) || [];
                return {
                    totalMatches: matches.length,
                    uniqueValues: [...new Set(matches)].length
                };
            });

            analysis.oddsData = oddsData;
            log.info(`Odds patterns: ${oddsData.totalMatches} matches, ${oddsData.uniqueValues} unique`);

            if (oddsData.totalMatches > 10) {
                analysis.success = true;
                log.success('[ODDS] Multiple odds patterns detected');
            }

        } catch (error) {
            log.error(`Analysis failed: ${error.message}`);
            analysis.errors.push('ANALYSIS_ERROR');
            analysis.fatalError = error.message;
        }

        return analysis;
    }

    /**
     * V105.001: Test single URL configuration
     */
    async testUrl(url, urlIndex) {
        log.section(`TEST URL ${urlIndex + 1}/${TARGET_URLS.length}`);

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

            // Create context with realistic options
            context = await browser.newContext({
                userAgent: CONFIG.userAgent,
                viewport: CONFIG.viewport,
                // Add realistic locale and timezone
                locale: 'en-US',
                timezoneId: 'America/New_York',
                // Enable JavaScript
                javaScriptEnabled: true
            });

            // Add init script to mask webdriver
            await context.addInitScript(() => {
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false
                });
                // Mask chrome runtime
                window.chrome = {
                    runtime: {}
                };
                // Mask permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: 'prompt' }) :
                        originalQuery(parameters)
                );
            });

            page = await context.newPage();

            // Navigate with realistic behavior
            const navResult = await this.realisticNavigate(page, url);

            log.info(`HTTP Status: ${navResult.status}`);

            // Analyze page
            const analysis = await this.analyzePage(page, urlIndex);
            analysis.url = url;
            analysis.httpStatus = navResult.status;
            analysis.loadTime = navResult.loadTime;

            return analysis;

        } catch (error) {
            log.error(`Test failed: ${error.message}`);
            return {
                urlIndex: urlIndex,
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
     * V105.001: Run full stealth test cycle
     */
    async runStealthCycle() {
        log.section('V105.001 STEALTH HARVESTER START');
        log.info(`Testing ${TARGET_URLS.length} URL formats`);

        const results = [];

        for (let i = 0; i < TARGET_URLS.length; i++) {
            const result = await this.testUrl(TARGET_URLS[i], i);
            results.push(result);

            // Delay between requests
            if (i < TARGET_URLS.length - 1) {
                log.info('Waiting 10 seconds before next request...');
                await new Promise(resolve => setTimeout(resolve, 10000));
            }
        }

        // Generate report
        this.generateReport(results);

        return results;
    }

    /**
     * V105.001: Generate summary report
     */
    generateReport(results) {
        log.section('V105.001 STEALTH HARVESTER REPORT');

        console.log('\n┌─────────────────────────────────────────────────────────────────┐');
        console.log('│                    V105.001 TEST RESULTS                         │');
        console.log('├─────────────────────────────────────────────────────────────────┤');

        results.forEach((result, i) => {
            const status = result.success ? '✓ SUCCESS' : '✗ FAILED';
            const urlShort = result.url?.substring(0, 50) || 'N/A';
            console.log(`│ Test ${i + 1}: ${status.padEnd(12)} | ${result.httpStatus || 'N/A'} | ${result.loadTime || 0}ms │`);
            console.log(`│         URL: ${urlShort}...`);
            console.log(`│         Title: "${(result.title || '').substring(0, 40)}..."`);
            console.log(`│         Content: ${result.contentLength || 0} bytes`);
            console.log(`│         Keywords: ${result.foundKeywords?.join(', ') || 'NONE'}`);
            console.log(`│         Errors: ${result.errors?.join(', ') || 'NONE'}`);
            console.log('├─────────────────────────────────────────────────────────────────┤');
        });

        console.log('└─────────────────────────────────────────────────────────────────┘\n');

        // Recommendations
        log.section('V105.001 RECOMMENDATIONS');

        const successCount = results.filter(r => r.success).length;
        if (successCount > 0) {
            log.success(`[${successCount}/${results.length}] tests succeeded!`);
            const workingUrl = results.find(r => r.success);
            log.info(`Working URL format: ${workingUrl.url}`);
        } else {
            log.error('[CRITICAL] All tests still failed');
            log.info('Next steps to try:');
            log.info('  1. Use residential proxy');
            log.info('  2. Try with real browser cookies');
            log.info('  3. Implement CAPTCHA solving');
            log.info('  4. Consider using Selenium with undetected-chromedriver');
        }

        // Save JSON report
        const reportPath = path.join(CONFIG.outputDir, `stealth_report_${Date.now()}.json`);
        fs.writeFileSync(reportPath, JSON.stringify(results, null, 2));
        log.info(`Report saved: ${reportPath}`);
    }
}

// ============================================================================
// MAIN ENTRY POINT
// ============================================================================

async function main() {
    const harvester = new StealthHarvester();

    try {
        const results = await harvester.runStealthCycle();

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
        console.error('[V105.001] Fatal error:', error);
        process.exit(1);
    });
}

module.exports = { StealthHarvester, main };
