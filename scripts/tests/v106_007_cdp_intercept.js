/**
 * V106.007 CDP Network Interception
 * =================================
 *
 * V106.007: Use Chrome DevTools Protocol to intercept raw network responses
 *
 * @version V106.007
 * @since 2026-01-26
 */

'use strict';

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const TARGET_URL = 'https://www.oddsportal.com/football/england/premier-league/brighton-everton-vPKFVEM6/';
const OUTPUT_DIR = path.join(__dirname, '../../logs/v106_diagnostic');

const REALISTIC_HEADERS = {
    'Accept-Language': 'en-US,en;q=0.9',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Referer': 'https://www.oddsportal.com/football/england/premier-league/'
};

const CONFIG = {
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    viewport: { width: 1920, height: 1080 },
    timeout: 90000
};

if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

const log = {
    info: (msg) => console.log(`[V106.007] [INFO] ${msg}`),
    success: (msg) => console.log(`[V106.007] [✓] ${msg}`),
    warn: (msg) => console.warn(`[V106.007] [!] ${msg}`),
    error: (msg) => console.error(`[V106.007] [✗] ${msg}`),
    section: (title) => {
        console.log('\n' + '='.repeat(70));
        console.log(`[V106.007] ${title}`);
        console.log('='.repeat(70));
    }
};

async function cdpIntercept() {
    log.section('V106.007 CDP NETWORK INTERCEPTION');

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

    // V106.007: Use CDP to intercept network responses
    const client = await context.newCDPSession(page);
    await client.send('Network.enable');

    const capturedData = [];

    client.on('Network.responseReceived', (params) => {
        const url = params.response.url;
        if (url.includes('/match-event/')) {
            log.info(`[CDP] Response received: ${url.substring(0, 80)}...`);
            log.info(`  MIME Type: ${params.response.mimeType}`);
            log.info(`  Headers: ${JSON.stringify(params.response.headers).substring(0, 200)}`);
        }
    });

    // Try to intercept the actual body
    let requestId = null;
    client.on('Network.requestWillBeSent', (params) => {
        if (params.request.url.includes('/match-event/') && !requestId) {
            requestId = params.requestId;
            log.info(`[CDP] Request detected: ${params.request.url.substring(0, 80)}...`);
        }
    });

    try {
        log.info(`Navigating to: ${TARGET_URL}`);
        await page.goto(TARGET_URL, {
            timeout: CONFIG.timeout,
            waitUntil: 'networkidle'
        });

        log.info('Waiting for API calls...');
        await page.waitForTimeout(20000);

        log.section('CDP ANALYSIS');
        log.info(`Captured ${capturedData.length} responses via CDP`);

        // Also try Playwright's route interception
        log.section('PLAYWRIGHT ROUTE INTERCEPTION');

    } catch (error) {
        log.error(`Error: ${error.message}`);
    } finally {
        await page.close();
        await context.close();
        await browser.close();
    }
}

if (require.main === module) {
    cdpIntercept().catch(error => {
        console.error('[V106.007] Fatal error:', error);
        process.exit(1);
    });
}

module.exports = { cdpIntercept };
