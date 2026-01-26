/**
 * V106.013 Browser JXG Decompress Test
 * ====================================
 *
 * V106.013: Use browser's JXG library to decompress API responses
 *
 * @version V106.013
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
    info: (msg) => console.log(`[V106.013] ${msg}`),
    success: (msg) => console.log(`[V106.013] [✓] ${msg}`),
    warn: (msg) => console.warn(`[V106.013] [!] ${msg}`),
    error: (msg) => console.error(`[V106.013] [✗] ${msg}`),
    section: (title) => {
        console.log('\n' + '='.repeat(70));
        console.log(`[V106.013] ${title}`);
        console.log('='.repeat(70));
    }
};

async function testBrowserJXG() {
    log.section('V106.013 BROWSER JXG DECOMPRESS TEST');

    const browser = await chromium.launch({
        headless: true,
        args: ['--disable-blink-features=AutomationControlled'],
        ignoreDefaultArgs: ['--enable-automation']
    });

    const context = await browser.newContext({
        userAgent: CONFIG.userAgent,
        viewport: CONFIG.viewport
    });

    const page = await context.newPage();

    // Capture console messages
    page.on('console', msg => {
        const text = msg.text();
        if (text.includes('[JXG TEST]')) {
            console.log('[BROWSER]', text);
        }
    });

    try {
        log.info(`Navigating to: ${TARGET_URL}`);
        await page.goto(TARGET_URL, {
            timeout: CONFIG.timeout,
            waitUntil: 'networkidle'
        });

        log.info('Waiting for page to load...');
        await page.waitForTimeout(5000);

        log.section('TESTING JXG DECOMPRESS IN BROWSER');

        // Test if JXG is available
        const jxgExists = await page.evaluate(() => {
            return typeof JXG !== 'undefined' && typeof JXG.decompress === 'function';
        });

        if (!jxgExists) {
            log.error('JXG library not found on page!');
            log.info('Loading JXG library manually...');

            // Load JXG library manually
            await page.addScriptTag({
                url: 'https://www.oddsportal.com/js/lscompressor.min.js?v=260126090850'
            });
            await page.waitForTimeout(2000);
        }

        // Get a sample API response from the captured data
        const fs = require('fs');
        const filepath = 'logs/v106_diagnostic/route_raw_1769436645357.bin';
        const base64Text = fs.readFileSync(filepath, 'utf-8');

        log.info('Testing JXG.decompress with captured response...');

        // Test decompression in browser context
        const result = await page.evaluate((base64Data) => {
            console.log('[JXG TEST] Input length:', base64Data.length);

            try {
                // Try to decompress using JXG
                const decompressed = JXG.decompress(base64Data);
                console.log('[JXG TEST] Decompressed length:', decompressed.length);
                console.log('[JXG TEST] First 100 chars:', decompressed.substring(0, 100));

                // Try to parse as JSON
                try {
                    const json = JSON.parse(decompressed);
                    console.log('[JXG TEST] JSON parse SUCCESS!');
                    console.log('[JXG TEST] Keys:', Object.keys(json));
                    return {
                        success: true,
                        json: json,
                        keys: Object.keys(json)
                    };
                } catch (e) {
                    console.log('[JXG TEST] JSON parse FAILED:', e.message);
                    console.log('[JXG TEST] Raw preview:', decompressed.substring(0, 500));
                    return {
                        success: false,
                        error: 'JSON parse failed: ' + e.message,
                        preview: decompressed.substring(0, 500)
                    };
                }
            } catch (e) {
                console.log('[JXG TEST] Decompress FAILED:', e.message);
                return {
                    success: false,
                    error: 'Decompress failed: ' + e.message
                };
            }
        }, base64Text);

        log.section('RESULT');
        console.log(JSON.stringify(result, null, 2));

        if (result.success) {
            log.success('[V106.013] JXG DECOMPRESS SUCCESS!');
            console.log('');
            console.log('Parsed JSON:');
            console.log(JSON.stringify(result.json, null, 2).substring(0, 3000));
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
    testBrowserJXG().catch(error => {
        console.error('[V106.013] Fatal error:', error);
        process.exit(1);
    });
}

module.exports = { testBrowserJXG };
