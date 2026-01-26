/**
 * V106.010 JavaScript Analysis
 * ===========================
 *
 * V106.010: Analyze page JavaScript to understand response decoding
 *
 * @version V106.010
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
    info: (msg) => console.log(`[V106.010] ${msg}`),
    success: (msg) => console.log(`[V106.010] [✓] ${msg}`),
    warn: (msg) => console.warn(`[V106.010] [!] ${msg}`),
    error: (msg) => console.error(`[V106.010] [✗] ${msg}`),
    section: (title) => {
        console.log('\n' + '='.repeat(70));
        console.log(`[V106.010] ${title}`);
        console.log('='.repeat(70));
    }
};

async function analyzeJavaScript() {
    log.section('V106.010 JAVASCRIPT ANALYSIS');

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

    // Listen for all console messages
    const consoleMessages = [];
    page.on('console', msg => {
        const text = msg.text();
        consoleMessages.push(text);
        if (text.includes('match-event') || text.includes('decode') || text.includes('decrypt')) {
            console.log('[CONSOLE]', text.substring(0, 200));
        }
    });

    // Monitor XHR requests
    const xhrRequests = [];
    await page.addInitScript(() => {
        const originalOpen = XMLHttpRequest.prototype.open;
        const originalSend = XMLHttpRequest.prototype.send;

        XMLHttpRequest.prototype.open = function(method, url, ...args) {
            this._url = url;
            return originalOpen.apply(this, [method, url, ...args]);
        };

        XMLHttpRequest.prototype.send = function(...args) {
            if (this._url && this._url.includes('/match-event/')) {
                console.log('[XHR] Request to:', this._url.substring(0, 80));

                this.addEventListener('load', function() {
                    console.log('[XHR] Response received');
                    console.log('[XHR] Status:', this.status);
                    console.log('[XHR] Response type:', this.responseType);
                    console.log('[XHR] Content-Type:', this.getResponseHeader('Content-Type'));

                    try {
                        if (this.responseType === '' || this.responseType === 'text') {
                            const text = this.responseText;
                            console.log('[XHR] Response length:', text.length);
                            console.log('[XHR] First 100 chars:', text.substring(0, 100));

                            // Try to decode
                            try {
                                const decoded = atob(text);
                                console.log('[XHR] First Base64 decode:', decoded.length, 'chars');
                                console.log('[XHR] Preview:', decoded.substring(0, 100));

                                // Try JSON
                                try {
                                    const json = JSON.parse(decoded);
                                    console.log('[XHR] JSON SUCCESS!', Object.keys(json));
                                } catch (e) {
                                    // Try double decode
                                    const decoded2 = atob(decoded);
                                    console.log('[XHR] Second decode:', decoded2.length);
                                    try {
                                        const json = JSON.parse(decoded2);
                                        console.log('[XHR] DOUBLE DECODE JSON SUCCESS!', Object.keys(json));
                                    } catch (e2) {
                                        console.log('[XHR] Not JSON after double decode');
                                    }
                                }
                            } catch (e) {
                                console.log('[XHR] Base64 decode failed:', e.message);
                            }
                        }
                    } catch (e) {
                        console.log('[XHR] Error reading response:', e.message);
                    }
                });
            }
            return originalSend.apply(this, args);
        };
    });

    try {
        log.info(`Navigating to: ${TARGET_URL}`);
        await page.goto(TARGET_URL, {
            timeout: CONFIG.timeout,
            waitUntil: 'networkidle'
        });

        log.info('Waiting for activity...');
        await page.waitForTimeout(20000);

        log.section('ANALYSIS RESULTS');
        log.info(`Total console messages: ${consoleMessages.length}`);

        // Search for decode/decrypt related console messages
        const relevantMessages = consoleMessages.filter(m =>
            m.includes('decode') || m.includes('decrypt') || m.includes('atob') ||
            m.includes('btoa') || m.includes('Base64')
        );
        log.info(`Decode-related messages: ${relevantMessages.length}`);
        for (const msg of relevantMessages) {
            console.log('  -', msg.substring(0, 150));
        }

        // Try to get the page's script content
        log.section('SEARCHING PAGE SCRIPTS');
        const scripts = await page.evaluate(() => {
            const results = [];
            const scriptTags = document.querySelectorAll('script');
            scriptTags.forEach((script, index) => {
                if (script.src) {
                    results.push({ type: 'external', src: script.src });
                } else if (script.textContent) {
                    const content = script.textContent;
                    if (content.includes('atob') || content.includes('decode') ||
                        content.includes('decrypt') || content.includes('Base64')) {
                        results.push({
                            type: 'inline',
                            index: index,
                            hasDecode: true,
                            length: content.length,
                            preview: content.substring(0, 200)
                        });
                    }
                }
            });
            return results;
        });

        log.info(`Found ${scripts.length} relevant scripts`);
        for (const script of scripts) {
            if (script.type === 'inline') {
                console.log(`\n[INLINE SCRIPT #${script.index}]`);
                console.log(`  Length: ${script.length} chars`);
                console.log(`  Preview: ${script.preview}`);
            } else {
                console.log(`\n[EXTERNAL SCRIPT] ${script.src.substring(0, 100)}`);
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
    analyzeJavaScript().catch(error => {
        console.error('[V106.010] Fatal error:', error);
        process.exit(1);
    });
}

module.exports = { analyzeJavaScript };
