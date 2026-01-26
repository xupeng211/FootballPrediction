/**
 * V106.006 Raw Body Diagnostic
 * ============================
 *
 * V106.006: Capture raw response body as Buffer to analyze encoding
 *
 * @version V106.006
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
    info: (msg) => console.log(`[V106.006] [INFO] ${msg}`),
    success: (msg) => console.log(`[V106.006] [✓] ${msg}`),
    warn: (msg) => console.warn(`[V106.006] [!] ${msg}`),
    error: (msg) => console.error(`[V106.006] [✗] ${msg}`),
    section: (title) => {
        console.log('\n' + '='.repeat(70));
        console.log(`[V106.006] ${title}`);
        console.log('='.repeat(70));
    }
};

async function diagnoseRawBody() {
    log.section('V106.006 RAW BODY DIAGNOSTIC');

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
                // V106.006: Use body() instead of text() to get raw Buffer
                const bodyBuffer = await response.body();
                log.info(`[CAPTURED] ${url.substring(0, 80)}...`);
                log.info(`  Content-Type: ${response.headers()['content-type']}`);
                log.info(`  Content-Encoding: ${response.headers()['content-encoding'] || 'none'}`);
                log.info(`  Buffer length: ${bodyBuffer.length} bytes`);

                // Save raw buffer
                const filename = `match_event_raw_${Date.now()}.bin`;
                const filepath = path.join(OUTPUT_DIR, filename);
                fs.writeFileSync(filepath, bodyBuffer);
                log.success(`  Saved raw buffer to: ${filepath}`);

                // Try to decode as UTF-8
                const asText = bodyBuffer.toString('utf-8');
                log.info(`  As UTF-8: ${asText.length} chars`);
                log.info(`  Preview: ${asText.substring(0, 200)}`);

                // Check for magic bytes
                const header = bodyBuffer.subarray(0, 4);
                log.info(`  First 4 bytes (hex): ${header.toString('hex')}`);
                log.info(`  Gzip magic (1f 8b)? ${header[0] === 0x1f && header[1] === 0x8b}`);
                log.info(`  Zlib magic (78 da)? ${header[0] === 0x78 && header[1] === 0xda}`);

                // Try to parse as JSON directly
                try {
                    const json = JSON.parse(asText);
                    log.success(`  [SUCCESS] Direct JSON parse!`);
                    log.info(`  Keys: ${Object.keys(json).join(', ')}`);
                    capturedResponses.push({
                        url: url,
                        json: json,
                        type: 'direct-json'
                    });
                } catch (e) {
                    log.info(`  Not direct JSON: ${e.message.substring(0, 100)}`);

                    // Try gzip decompression
                    try {
                        const decompressed = require('zlib').gunzipSync(bodyBuffer);
                        const json = JSON.parse(decompressed.toString('utf-8'));
                        log.success(`  [SUCCESS] Gzip + JSON!`);
                        log.info(`  Keys: ${Object.keys(json).join(', ')}`);
                        capturedResponses.push({
                            url: url,
                            json: json,
                            type: 'gzip-json'
                        });
                    } catch (e2) {
                        log.warn(`  Gzip failed: ${e2.message.substring(0, 100)}`);
                        capturedResponses.push({
                            url: url,
                            buffer: bodyBuffer,
                            text: asText,
                            type: 'unknown'
                        });
                    }
                }

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

        // Final analysis
        log.section('FINAL ANALYSIS');

        const directJson = capturedResponses.filter(r => r.type === 'direct-json');
        const gzipJson = capturedResponses.filter(r => r.type === 'gzip-json');
        const unknown = capturedResponses.filter(r => r.type === 'unknown');

        log.info(`Direct JSON: ${directJson.length}`);
        log.info(`Gzip + JSON: ${gzipJson.length}`);
        log.info(`Unknown format: ${unknown.length}`);

        if (directJson.length > 0) {
            log.success('[V106.006] Direct JSON capture SUCCESS!');
            console.log(JSON.stringify(directJson[0].json, null, 2).substring(0, 1000));
        } else if (gzipJson.length > 0) {
            log.success('[V106.006] Gzip + JSON capture SUCCESS!');
            console.log(JSON.stringify(gzipJson[0].json, null, 2).substring(0, 1000));
        } else {
            log.error('[V106.006] Unable to decode any responses');
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
    diagnoseRawBody().catch(error => {
        console.error('[V106.006] Fatal error:', error);
        process.exit(1);
    });
}

module.exports = { diagnoseRawBody };
