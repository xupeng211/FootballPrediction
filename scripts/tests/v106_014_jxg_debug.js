/**
 * V106.014 JXG Step-by-Step Debug
 * ===============================
 *
 * V106.014: Debug JXG decompress step by step
 *
 * @version V106.014
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

async function debugJXG() {
    console.log('[V106.014] JXG STEP-BY-STEP DEBUG');
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

        // Load JXG library
        console.log('Loading JXG library...');
        await page.addScriptTag({
            url: 'https://www.oddsportal.com/js/lscompressor.min.js?v=260126090850'
        });
        await page.waitForTimeout(2000);

        // Get captured data
        const fs = require('fs');
        const filepath = 'logs/v106_diagnostic/route_raw_1769436645357.bin';
        const base64Text = fs.readFileSync(filepath, 'utf-8');

        console.log('Testing with captured data...');
        console.log('');

        // Step-by-step debug in browser
        const debugResult = await page.evaluate((data) => {
            console.log('=== STEP 1: Base64.decodeAsArray ===');
            try {
                const decodedArray = JXG.Util.Base64.decodeAsArray(data);
                console.log('Array length:', decodedArray.length);
                console.log('First 10 values:', decodedArray.slice(0, 10));
                console.log('First 20 values as hex:', decodedArray.slice(0, 20).map(b => '0x' + (b & 0xFF).toString(16).padStart(2, '0')).join(' '));
                console.log('');

                // Check for magic bytes
                const b0 = decodedArray[0] & 0xFF;
                const b1 = decodedArray[1] & 0xFF;
                console.log('Magic bytes check:');
                console.log('  b0 =', b0, '(0x' + b0.toString(16) + ')');
                console.log('  b1 =', b1, '(0x' + b1.toString(16) + ')');
                console.log('  78 da (raw deflate)?', b0 === 0x78 && b1 === 0xda);
                console.log('  1f 8b (gzip)?', b0 === 0x1f && b1 === 0x8b);
                console.log('  50 4b (zip)?', b0 === 0x50 && b1 === 0x4b);
                console.log('');

                console.log('=== STEP 2: new JXG.Util.Unzip() ===');
                const unzipper = new JXG.Util.Unzip(decodedArray);
                console.log('Unzipper created:', typeof unzipper);
                console.log('');

                console.log('=== STEP 3: unzipper.unzip() ===');
                const unzipped = unzipper.unzip();
                console.log('Unzipped result:', unzipped);
                console.log('Type:', typeof unzipped);
                console.log('Is array?', Array.isArray(unzipped));
                console.log('Length:', unzipped ? unzipped.length : 'N/A');

                if (unzipped && unzipped.length > 0) {
                    console.log('unzipped[0]:', unzipped[0]);
                    console.log('unzipped[0][0]:', unzipped[0] ? unzipped[0][0] : 'undefined');
                } else {
                    console.log('WARNING: unzipped is empty or null!');
                }
                console.log('');

                console.log('=== STEP 4: RawUrlDecode ===');
                if (unzipped && unzipped[0] && unzipped[0][0]) {
                    const urlDecoded = JXG.Util.RawUrlDecode(unzipped[0][0]);
                    console.log('URL decoded length:', urlDecoded.length);
                    console.log('First 100 chars:', urlDecoded.substring(0, 100));
                    console.log('');

                    console.log('=== STEP 5: JSON.parse ===');
                    try {
                        const json = JSON.parse(urlDecoded);
                        console.log('[SUCCESS] JSON parsed!');
                        console.log('Keys:', Object.keys(json));
                        return { success: true, json: json };
                    } catch (e) {
                        console.log('[FAIL] JSON parse:', e.message);
                        console.log('Raw preview:', urlDecoded.substring(0, 500));
                        return { success: false, error: e.message, preview: urlDecoded.substring(0, 500) };
                    }
                } else {
                    console.log('[FAIL] Cannot proceed - unzipped[0][0] is undefined');
                    return { success: false, error: 'unzipped[0][0] is undefined' };
                }
            } catch (e) {
                console.log('[ERROR]', e.message);
                console.log('Stack:', e.stack);
                return { success: false, error: e.message, stack: e.stack };
            }
        }, base64Text);

        console.log('');
        console.log('=== FINAL RESULT ===');
        console.log(JSON.stringify(debugResult, null, 2));

        if (debugResult.success) {
            console.log('');
            console.log('[V106.014] SUCCESS! JSON data:');
            console.log(JSON.stringify(debugResult.json, null, 2).substring(0, 3000));
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
    debugJXG().catch(error => {
        console.error('[V106.014] Fatal error:', error);
        process.exit(1);
    });
}

module.exports = { debugJXG };
