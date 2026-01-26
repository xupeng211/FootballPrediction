/**
 * V106.005 API Response Format Diagnostic
 * ========================================
 *
 * V106.005: Save raw API responses to analyze encoding format
 *
 * @version V106.005
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

// Ensure output directory exists
if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

const log = {
    info: (msg) => console.log(`[V106.005] [INFO] ${msg}`),
    success: (msg) => console.log(`[V106.005] [✓] ${msg}`),
    warn: (msg) => console.warn(`[V106.005] [!] ${msg}`),
    error: (msg) => console.error(`[V106.005] [✗] ${msg}`),
    section: (title) => {
        console.log('\n' + '='.repeat(70));
        console.log(`[V106.005] ${title}`);
        console.log('='.repeat(70));
    }
};

async function diagnoseAPIFormat() {
    log.section('V106.005 API FORMAT DIAGNOSTIC');

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

    let capturedResponses = [];

    page.on('response', async (response) => {
        const url = response.url();

        if (url.includes('/match-event/') && response.headers()['content-type']?.includes('application/json')) {
            try {
                const body = await response.text();
                log.info(`[CAPTURED] ${url.substring(0, 80)}...`);
                log.info(`  Length: ${body.length} chars`);
                log.info(`  First 100 chars: ${body.substring(0, 100)}`);

                // Save to file
                const filename = `match_event_response_${Date.now()}.txt`;
                const filepath = path.join(OUTPUT_DIR, filename);
                fs.writeFileSync(filepath, body, 'utf-8');
                log.success(`  Saved to: ${filepath}`);

                capturedResponses.push({
                    url: url,
                    body: body,
                    filepath: filepath
                });

            } catch (error) {
                log.error(`Failed to capture response: ${error.message}`);
            }
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

        // Analysis
        log.section('FORMAT ANALYSIS');

        if (capturedResponses.length > 0) {
            log.success(`Captured ${capturedResponses.length} responses`);

            for (let i = 0; i < capturedResponses.length; i++) {
                const resp = capturedResponses[i];
                log.section(`Response ${i + 1}`);

                const body = resp.body;

                // Check if it's valid Base64
                const base64Pattern = /^[A-Za-z0-9+/=]+$/;
                const isBase64 = base64Pattern.test(body);

                log.info(`Is valid Base64: ${isBase64}`);
                log.info(`First 200 chars: ${body.substring(0, 200)}`);

                // Try different decoding strategies
                log.info('Decoding attempts:');

                // 1. Direct Base64 decode
                try {
                    const padded = body.padEnd(body.length + (4 - body.length % 4) % 4, '=');
                    const decoded1 = Buffer.from(padded, 'base64').toString('utf-8');
                    log.info(`  1. Direct Base64: ${decoded1.length} chars`);
                    log.info(`     Preview: ${decoded1.substring(0, 100)}`);
                } catch (e) {
                    log.info(`  1. Direct Base64: FAILED - ${e.message}`);
                }

                // 2. Try to parse as JSON directly
                try {
                    const parsed = JSON.parse(body);
                    log.success(`  2. Direct JSON: SUCCESS - Found keys: ${Object.keys(parsed).join(', ')}`);
                } catch (e) {
                    log.info(`  2. Direct JSON: FAILED - ${e.message}`);
                }

                // 3. Check for gzip header
                if (body.substring(0, 2) === 'H4sI') {
                    log.info(`  3. Detected possible gzip+base64 (H4sI header)`);
                }

                // 4. Look for patterns
                if (body.includes('{"') || body.includes('[')) {
                    log.info(`  4. Contains JSON markers`);
                }
            }
        } else {
            log.error('No responses captured');
        }

    } catch (error) {
        log.error(`Diagnostic failed: ${error.message}`);
    } finally {
        await page.close();
        await context.close();
        await browser.close();
    }
}

if (require.main === module) {
    diagnoseAPIFormat().catch(error => {
        console.error('[V106.005] Fatal error:', error);
        process.exit(1);
    });
}

module.exports = { diagnoseAPIFormat };
