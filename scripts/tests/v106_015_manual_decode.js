/**
 * V106.015 Manual Decode Implementation
 * ====================================
 *
 * V106.015: Manually implement correct Base64 + deflate decode
 *
 * @version V106.015
 * @since 2026-01-26
 */

'use strict';

const { chromium } = require('playwright');
const fs = require('fs');

const TARGET_URL = 'https://www.oddsportal.com/football/england/premier-league/brighton-everton-vPKFVEM6/';

const CONFIG = {
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    viewport: { width: 1920, height: 1080 },
    timeout: 90000
};

async function manualDecode() {
    console.log('[V106.015] MANUAL DECODE IMPLEMENTATION');
    console.log('='.repeat(70));

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

    page.on('console', msg => {
        console.log('[BROWSER]', msg.text());
    });

    try {
        console.log('Navigating to:', TARGET_URL);
        await page.goto(TARGET_URL, {
            timeout: CONFIG.timeout,
            waitUntil: 'networkidle'
        });
        await page.waitForTimeout(3000);

        // Get captured data
        const filepath = 'logs/v106_diagnostic/route_raw_1769436645357.bin';
        const base64Text = fs.readFileSync(filepath, 'utf-8');

        console.log('Testing with captured data...');
        console.log('');

        // Manual decode in browser
        const result = await page.evaluate((base64Data) => {
            console.log('=== MANUAL DECODE TEST ===');
            console.log('Input length:', base64Data.length);
            console.log('');

            // Step 1: Decode Base64 to string
            console.log('Step 1: atob() Base64 decode');
            const step1 = atob(base64Data);
            console.log('Result length:', step1.length);
            console.log('First 100 chars:', step1.substring(0, 100));
            console.log('Is valid Base64?', /^[A-Za-z0-9+/=]+$/.test(step1));
            console.log('');

            // Step 2: Check if step 1 is ALSO Base64
            if (/^[A-Za-z0-9+/=]+$/.test(step1)) {
                console.log('Step 2: Second Base64 decode (atob)');
                const step2 = atob(step1);
                console.log('Result length:', step2.length);
                console.log('First 100 chars:', step2.substring(0, 100));
                console.log('');

                // Step 3: Check if it's URL encoded
                if (step2.includes('%')) {
                    console.log('Step 3: URL decode');
                    let urlDecoded = step2;
                    let iterations = 0;
                    while (urlDecoded.includes('%') && iterations < 10) {
                        const newDecoded = decodeURIComponent(urlDecoded);
                        if (newDecoded === urlDecoded) break;
                        urlDecoded = newDecoded;
                        iterations++;
                    }
                    console.log('URL decode iterations:', iterations);
                    console.log('Result length:', urlDecoded.length);
                    console.log('First 200 chars:', urlDecoded.substring(0, 200));
                    console.log('');

                    // Step 4: Try JSON parse
                    console.log('Step 4: JSON.parse');
                    try {
                        const json = JSON.parse(urlDecoded);
                        console.log('[SUCCESS] JSON parsed!');
                        console.log('Keys:', Object.keys(json));
                        return { success: true, json: json, method: 'double-base64-urldecode' };
                    } catch (e) {
                        console.log('[FAIL] JSON parse:', e.message);
                        return { success: false, error: 'JSON parse failed', preview: urlDecoded.substring(0, 500) };
                    }
                } else {
                    // Not URL encoded, might be compressed
                    console.log('Step 3: Check for compression');
                    console.log('First 20 chars codes:', Array.from(step2.substring(0, 20)).map(c => c.charCodeAt(0)));

                    // Try to detect format by checking for specific patterns
                    const hasBraces = step2.includes('{') || step2.includes('}');
                    const hasBrackets = step2.includes('[') || step2.includes(']');

                    console.log('Has braces:', hasBraces);
                    console.log('Has brackets:', hasBrackets);

                    if (hasBraces || hasBrackets) {
                        console.log('Might be text, trying JSON parse directly...');
                        try {
                            const json = JSON.parse(step2);
                            console.log('[SUCCESS] JSON parsed!');
                            return { success: true, json: json, method: 'double-base64-direct' };
                        } catch (e) {
                            console.log('[FAIL] JSON parse:', e.message);
                        }
                    }

                    return { success: false, error: 'Unknown format after double decode', preview: step2.substring(0, 500) };
                }
            } else {
                console.log('Step 1 result is NOT Base64, might be compressed or different format');
                return { success: false, error: 'Step 1 is not Base64' };
            }
        }, base64Text);

        console.log('');
        console.log('=== FINAL RESULT ===');
        console.log('Method:', result.method);
        console.log('Success:', result.success);

        if (result.success) {
            console.log('');
            console.log('[V106.015] SUCCESS! JSON data:');
            console.log(JSON.stringify(result.json, null, 2).substring(0, 3000));
        } else {
            console.log('Error:', result.error);
            if (result.preview) {
                console.log('Preview:', result.preview);
            }
        }

    } catch (error) {
        console.error('[ERROR]', error.message);
        console.error(error.stack);
    } finally {
        await page.close();
        await context.close();
        await browser.close();
    }
}

if (require.main === module) {
    manualDecode().catch(error => {
        console.error('[V106.015] Fatal error:', error);
        process.exit(1);
    });
}

module.exports = { manualDecode };
