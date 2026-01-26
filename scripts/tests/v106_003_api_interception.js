/**
 * V106.003 API Interception Test - Network Analysis
 * ===================================================
 *
 * V106.003: Monitor API calls and network requests to diagnose blocking
 *   - Capture all XHR/fetch requests
 *   - Check for API responses
 *   - Identify if data is being loaded via AJAX
 *
 * @version V106.003
 * @since 2026-01-26
 */

'use strict';

const { chromium } = require('playwright');

const TARGET_URL = 'https://www.oddsportal.com/football/england/premier-league/everton-leeds-neRXKc8l/';

const REALISTIC_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.9',
    'Cache-Control': 'max-age=0',
    'Sec-Ch-Ua': '"Chromium";v="131", "Not_A Brand";v="24"',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Referer': 'https://www.oddsportal.com/football/england/premier-league/'
};

const CONFIG = {
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
};

const log = {
    info: (msg) => console.log(`[V106.003] [INFO] ${msg}`),
    success: (msg) => console.log(`[V106.003] [✓] ${msg}`),
    warn: (msg) => console.warn(`[V106.003] [!] ${msg}`),
    error: (msg) => console.error(`[V106.003] [✗] ${msg}`),
    section: (title) => {
        console.log('\n' + '='.repeat(70));
        console.log(`[V106.003] ${title}`);
        console.log('='.repeat(70));
    }
};

async function testAPIInterception() {
    log.section('V106.003 API INTERCEPTION TEST');

    const browser = await chromium.launch({
        headless: true,
        args: ['--disable-blink-features=AutomationControlled'],
        ignoreDefaultArgs: ['--enable-automation']
    });

    const context = await browser.newContext({
        userAgent: CONFIG.userAgent
    });

    const page = await context.newPage();
    await page.setExtraHTTPHeaders(REALISTIC_HEADERS);

    // Track all API calls
    const apiCalls = [];
    const allResponses = [];

    page.on('request', request => {
        const url = request.url();
        const resourceType = request.resourceType();

        if (resourceType === 'xhr' || resourceType === 'fetch') {
            log.info(`[API REQUEST] ${request.method()} ${url.substring(0, 80)}...`);
        }
    });

    page.on('response', async response => {
        const url = response.url();
        const status = response.status();
        const contentType = response.headers()['content-type'] || '';

        allResponses.push({
            url: url,
            status: status,
            contentType: contentType,
            resourceType: response.request().resourceType()
        });

        // Log API responses
        if (response.request().resourceType() === 'xhr' || response.request().resourceType() === 'fetch') {
            log.info(`[API RESPONSE] [${status}] ${url.substring(0, 60)}... (${contentType})`);

            if (contentType.includes('application/json')) {
                try {
                    const body = await response.text();
                    const preview = body.substring(0, 200);
                    log.info(`  Body preview: ${preview}...`);
                    apiCalls.push({
                        url: url,
                        status: status,
                        body: body.substring(0, 1000) // Store first 1KB
                    });
                } catch (e) {
                    log.warn(`  Failed to read body: ${e.message}`);
                }
            }
        }

        // Log errors
        if (status >= 400) {
            log.error(`[ERROR ${status}] ${url.substring(0, 80)}...`);
        }
    });

    try {
        log.info(`Navigating to: ${TARGET_URL}`);
        await page.goto(TARGET_URL, {
            timeout: 60000,
            waitUntil: 'networkidle'
        });

        // Wait for JavaScript
        log.info('Waiting for JavaScript execution (15 seconds)...');
        await page.waitForTimeout(15000);

        // Check React containers
        const reactStatus = await page.evaluate(() => {
            const containers = {
                'react-event-header': document.querySelector('#react-event-header')?.innerHTML?.length || 0,
                'react-leagues-events': document.querySelector('#react-leagues-events')?.innerHTML?.length || 0,
                'react-bonus-offer-mobile': document.querySelector('#react-bonus-offer-mobile')?.innerHTML?.length || 0
            };
            return containers;
        });

        log.info('React container status:');
        for (const [name, length] of Object.entries(reactStatus)) {
            log.info(`  #${name}: ${length} characters`);
        }

        // Generate report
        log.section('V106.003 NETWORK REPORT');

        console.log('\n┌─────────────────────────────────────────────────────────────────┐');
        console.log('│                    V106.003 NETWORK SUMMARY                      │');
        console.log('├─────────────────────────────────────────────────────────────────┤');
        console.log(`│ Total Responses: ${String(allResponses.length).padStart(50)}  │`);
        console.log(`│ API Calls (JSON): ${String(apiCalls.length).padStart(48)}  │`);
        console.log('├─────────────────────────────────────────────────────────────────┤');

        // Show API calls
        if (apiCalls.length > 0) {
            console.log('│ API CALLS DETECTED:                                              │');
            apiCalls.forEach((call, i) => {
                console.log(`│ ${i + 1}. [${call.status}] ${call.url.substring(0, 55)}...    │`);
            });
        } else {
            console.log('│ NO API CALLS DETECTED                                           │');
        }

        // Show error responses
        const errors = allResponses.filter(r => r.status >= 400);
        if (errors.length > 0) {
            console.log('├─────────────────────────────────────────────────────────────────┤');
            console.log('│ ERROR RESPONSES:                                                 │');
            errors.slice(0, 5).forEach((err, i) => {
                console.log(`│ ${i + 1}. [${err.status}] ${err.url.substring(0, 55)}...    │`);
            });
        }

        console.log('└─────────────────────────────────────────────────────────────────┘\n');

        // Verdict
        log.section('V106.003 VERDICT');

        if (apiCalls.length > 0) {
            log.success(`[DATA AVAILABLE] ${apiCalls.length} API calls detected`);
            log.info('The page makes API calls - we can intercept and parse them!');
            log.info('Next: Implement API interception to bypass DOM rendering.');
        } else if (errors.some(e => e.status === 403 || e.status === 401)) {
            log.error('[BLOCKED] Authentication required (401/403)');
            log.info('Recommendation: Need to implement login/authentication.');
        } else {
            log.error('[EMPTY] No data detected - page may be geo-blocked');
            log.info('Recommendation: Try with proxy or different geographic location.');
        }

    } catch (error) {
        log.error(`Test failed: ${error.message}`);
    } finally {
        await page.close();
        await context.close();
        await browser.close();
    }
}

if (require.main === module) {
    testAPIInterception().catch(error => {
        console.error('[V106.003] Fatal error:', error);
        process.exit(1);
    });
}

module.exports = { testAPIInterception };
