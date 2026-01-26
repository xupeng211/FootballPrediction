/**
 * V106.008 Route Interception Test
 * ================================
 *
 * V106.008: Intercept and analyze match-event API using Playwright route
 *
 * @version V106.008
 * @since 2026-01-26
 */

'use strict';

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const TARGET_URL = 'https://www.oddsportal.com/football/england/premier-league/brighton-everton-vPKFVEM6/';
const OUTPUT_DIR = path.join(__dirname, '../../logs/v106_diagnostic');

const CONFIG = {
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    viewport: { width: 1920, height: 1080 },
    timeout: 90000
};

if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

const log = {
    info: (msg) => console.log(`[V106.008] ${msg}`),
    success: (msg) => console.log(`[V106.008] [✓] ${msg}`),
    warn: (msg) => console.log(`[V106.008] [!] ${msg}`),
    error: (msg) => console.log(`[V106.008] [✗] ${msg}`),
    section: (title) => {
        console.log('\n' + '='.repeat(70));
        console.log(`[V106.008] ${title}`);
        console.log('='.repeat(70));
    }
};

async function routeIntercept() {
    log.section('V106.008 ROUTE INTERCEPTION TEST');

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

    let capturedResponses = [];

    // V106.008: Route interception using fetch
    await page.route('**/match-event/**', async (route, request) => {
        const url = request.url();
        log.info(`[ROUTE] Intercepting: ${url.substring(0, 80)}...`);

        // Use fetch to get the response
        const response = await fetch(request.url(), {
            headers: request.headers()
        });

        const bodyBuffer = Buffer.from(await response.arrayBuffer());

        log.info(`  Status: ${response.status}`);
        log.info(`  Content-Type: ${response.headers.get('content-type')}`);
        log.info(`  Content-Encoding: ${response.headers.get('content-encoding') || 'none'}`);
        log.info(`  Body length: ${bodyBuffer.length} bytes`);

        // Save raw buffer
        const filename = `route_raw_${Date.now()}.bin`;
        const filepath = path.join(OUTPUT_DIR, filename);
        fs.writeFileSync(filepath, bodyBuffer);

        // Try to decode
        log.info(`  First 100 bytes (hex): ${bodyBuffer.subarray(0, 100).toString('hex')}`);
        log.info(`  First 100 chars (UTF-8): ${bodyBuffer.toString('utf-8').substring(0, 100)}`);

        // Check if it's valid UTF-8 JSON
        try {
            const text = bodyBuffer.toString('utf-8');
            const json = JSON.parse(text);
            log.success(`  [SUCCESS] Direct JSON parse!`);
            log.info(`  Keys: ${Object.keys(json).join(', ')}`);
            capturedResponses.push({ url, json, type: 'direct-json' });
        } catch (e) {
            log.info(`  Not direct JSON: ${e.message.substring(0, 50)}`);

            // Check if it's gzip
            if (bodyBuffer[0] === 0x1f && bodyBuffer[1] === 0x8b) {
                try {
                    const decompressed = require('zlib').gunzipSync(bodyBuffer);
                    const json = JSON.parse(decompressed.toString('utf-8'));
                    log.success(`  [SUCCESS] Gzip + JSON!`);
                    log.info(`  Keys: ${Object.keys(json).join(', ')}`);
                    capturedResponses.push({ url, json, type: 'gzip-json' });
                } catch (e2) {
                    log.error(`  Gzip decompression failed: ${e2.message.substring(0, 50)}`);
                }
            } else {
                log.warn(`  Not gzip data (magic bytes: ${bodyBuffer[0].toString(16)} ${bodyBuffer[1].toString(16)})`);
                capturedResponses.push({ url, buffer: bodyBuffer, type: 'unknown' });
            }
        }

        // Fulfill the request with the original response
        await route.fulfill({
            status: response.status,
            headers: Object.fromEntries(response.headers.entries()),
            body: bodyBuffer
        });
    });

    try {
        log.info(`Navigating to: ${TARGET_URL}`);
        await page.goto(TARGET_URL, {
            timeout: CONFIG.timeout,
            waitUntil: 'networkidle'
        });

        log.info('Waiting for API calls...');
        await page.waitForTimeout(20000);

        log.section('FINAL ANALYSIS');
        log.info(`Captured ${capturedResponses.length} responses`);

        const successCount = capturedResponses.filter(r => r.json).length;
        log.info(`Successfully decoded: ${successCount}`);

        if (successCount > 0) {
            const success = capturedResponses.find(r => r.json);
            log.success('[V106.008] INTERCEPTION SUCCESS!');
            console.log(JSON.stringify(success.json, null, 2).substring(0, 2000));
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
    routeIntercept().catch(error => {
        console.error('[V106.008] Fatal error:', error);
        process.exit(1);
    });
}

module.exports = { routeIntercept };
