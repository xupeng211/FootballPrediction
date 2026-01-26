/**
 * V106.009 Browser Context Data Inspection
 * ========================================
 *
 * V106.009: Intercept API calls from within browser context
 *
 * @version V106.009
 * @since 2026-01-26
 */

'use strict';

const { chromium } = require('playwright');

const TARGET_URL = 'https://www.oddsportal.com/football/england/premier-league/brighton-everton-vPKFVEM6/';

const CONFIG = {
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    viewport: { width: 1920, height: 1080 },
    timeout: 90000
};

const log = {
    info: (msg) => console.log(`[V106.009] ${msg}`),
    success: (msg) => console.log(`[V106.009] [✓] ${msg}`),
    warn: (msg) => console.warn(`[V106.009] [!] ${msg}`),
    error: (msg) => console.error(`[V106.009] [✗] ${msg}`),
    section: (title) => {
        console.log('\n' + '='.repeat(70));
        console.log(`[V106.009] ${title}`);
        console.log('='.repeat(70));
    }
};

async function inspectInBrowserContext() {
    log.section('V106.009 BROWSER CONTEXT INSPECTION');

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

        // V106.009: Inject fetch interceptor in browser context
        window.capturedData = [];
        const originalFetch = window.fetch;
        window.fetch = async function(...args) {
            const url = args[0];
            if (typeof url === 'string' && url.includes('/match-event/')) {
                console.log('[INJECTED FETCH] Intercepting:', url.substring(0, 80));
                const response = await originalFetch.apply(this, args);

                // Clone the response to read it
                const clonedResponse = response.clone();
                const bodyText = await clonedResponse.text();

                // Store captured data
                window.capturedData.push({
                    url: url,
                    body: bodyText,
                    headers: Array.from(response.headers.entries())
                });

                console.log('[INJECTED FETCH] Captured:', bodyText.length, 'chars');
                console.log('[INJECTED FETCH] First 100 chars:', bodyText.substring(0, 100));

                return response;
            }
            return originalFetch.apply(this, args);
        };
    });

    const page = await context.newPage();

    // Listen for console messages from the injected script
    page.on('console', msg => {
        const text = msg.text();
        if (text.includes('[INJECTED FETCH]')) {
            console.log('[BROWSER]', text);
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

        // Get captured data from browser context
        log.section('ANALYZING CAPTURED DATA');
        const capturedData = await page.evaluate(() => window.capturedData || []);

        log.info(`Captured ${capturedData.length} responses in browser context`);

        for (let i = 0; i < capturedData.length; i++) {
            const data = capturedData[i];
            console.log(`\n--- Response ${i + 1} ---`);
            console.log(`URL: ${data.url.substring(0, 80)}...`);
            console.log(`Body length: ${data.body.length} chars`);
            console.log(`First 200 chars: ${data.body.substring(0, 200)}`);

            // Try to decode
            try {
                // First Base64 decode
                const buf1 = Buffer.from(data.body, 'base64');
                const str1 = buf1.toString('utf-8');
                console.log(`First decode: ${buf1.length} bytes`);
                console.log(`Preview: ${str1.substring(0, 100)}`);

                // Check if it's valid JSON
                try {
                    const json = JSON.parse(str1);
                    console.log('[SUCCESS] Direct JSON after first decode!');
                    console.log('Keys:', Object.keys(json));
                } catch (e) {
                    // Try second decode
                    const cleanStr1 = str1.replace(/[^A-Za-z0-9+/=]/g, '');
                    const padded = cleanStr1.padEnd(cleanStr1.length + (4 - cleanStr1.length % 4) % 4, '=');
                    const buf2 = Buffer.from(padded, 'base64');
                    const str2 = buf2.toString('utf-8');
                    console.log(`Second decode: ${buf2.length} bytes`);
                    console.log(`Preview: ${str2.substring(0, 100)}`);

                    try {
                        const json = JSON.parse(str2);
                        console.log('[SUCCESS] JSON after second decode!');
                        console.log('Keys:', Object.keys(json));
                    } catch (e2) {
                        console.log('Not JSON after second decode either');
                    }
                }
            } catch (e) {
                console.log('Decode error:', e.message.substring(0, 100));
            }
        }

    } catch (error) {
        log.error(`Error: ${error.message}`);
    } finally {
        await page.close();
        await context.close();
        await browser.close();
    }
}

if (require.main === module) {
    inspectInBrowserContext().catch(error => {
        console.error('[V106.009] Fatal error:', error);
        process.exit(1);
    });
}

module.exports = { inspectInBrowserContext };
