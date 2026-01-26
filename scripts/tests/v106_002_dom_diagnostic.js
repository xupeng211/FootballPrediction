/**
 * V106.002 DOM Structure Diagnostic - Live Page Analysis
 * ======================================================
 *
 * V106.002: Diagnostic tool to analyze actual DOM structure on live pages
 *   - Dump all div elements with "border" class
 *   - Look for bookmaker logos and odds patterns
 *   - Identify correct selectors for current OddsPortal structure
 *
 * @version V106.002
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
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Sec-Gpc': '1',
    'Upgrade-Insecure-Requests': '1',
    'Referer': 'https://www.oddsportal.com/football/england/premier-league/'
};

const CONFIG = {
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    viewport: { width: 1920, height: 1080 },
    timeout: 90000
};

const log = {
    info: (msg) => console.log(`[V106.002] [INFO] ${msg}`),
    success: (msg) => console.log(`[V106.002] [✓] ${msg}`),
    warn: (msg) => console.warn(`[V106.002] [!] ${msg}`),
    error: (msg) => console.error(`[V106.002] [✗] ${msg}`),
    section: (title) => {
        console.log('\n' + '='.repeat(70));
        console.log(`[V106.002] ${title}`);
        console.log('='.repeat(70));
    }
};

async function diagnoseDOMStructure() {
    log.section('V106.002 DOM STRUCTURE DIAGNOSTIC');

    const browser = await chromium.launch({
        headless: true,
        args: [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-setuid-sandbox'
        ],
        ignoreDefaultArgs: ['--enable-automation']
    });

    const context = await browser.newContext({
        userAgent: CONFIG.userAgent,
        viewport: CONFIG.viewport,
        locale: 'en-US',
        timezoneId: 'America/New_York',
        javaScriptEnabled: true
    });

    await context.addInitScript(() => {
        Object.defineProperty(navigator, 'webdriver', { get: () => false });
        window.chrome = { runtime: {} };
    });

    const page = await context.newPage();
    await page.setExtraHTTPHeaders(REALISTIC_HEADERS);

    try {
        log.info(`Navigating to: ${TARGET_URL}`);
        await page.goto(TARGET_URL, {
            timeout: CONFIG.timeout,
            waitUntil: 'networkidle'
        });

        // Wait for JavaScript rendering
        log.info('Waiting for JavaScript rendering (10 seconds)...');
        await page.waitForTimeout(10000);

        // Get page info
        const title = await page.title();
        const url = page.url();
        log.info(`Title: "${title}"`);
        log.info(`URL: "${url}"`);

        // Diagnostic 1: Look for all div elements with specific patterns
        log.section('DIAGNOSTIC 1: DIV PATTERNS');

        const patterns = [
            'div[class*="border"]',
            'div[class*="odd"]',
            'div[class*="bookmaker"]',
            'div[class*="bet"]',
            'table',
            'img[alt*="logo" i]',
            'img[class*="logo" i]'
        ];

        for (const pattern of patterns) {
            const count = await page.locator(pattern).count();
            if (count > 0) {
                log.success(`Pattern "${pattern}": ${count} elements`);
            } else {
                log.info(`Pattern "${pattern}": 0 elements`);
            }
        }

        // Diagnostic 2: Sample actual class names
        log.section('DIAGNOSTIC 2: ACTUAL CLASS NAMES');

        const classSamples = await page.evaluate(() => {
            const samples = new Set();
            const divs = document.querySelectorAll('div');

            divs.forEach(div => {
                const className = div.className;
                if (className && typeof className === 'string') {
                    // Look for interesting patterns
                    if (className.includes('border') ||
                        className.includes('odd') ||
                        className.includes('flex') ||
                        className.includes('bet')) {
                        samples.add(className);
                    }
                }
            });

            return Array.from(samples).slice(0, 20);
        });

        log.info(`Found ${classSamples.length} unique class names with patterns:`);
        classSamples.forEach((cls, i) => {
            log.info(`  ${i + 1}. "${cls}"`);
        });

        // Diagnostic 3: Look for specific keywords in page
        log.section('DIAGNOSTIC 3: PAGE CONTENT ANALYSIS');

        const contentAnalysis = await page.evaluate(() => {
            const bodyText = document.body.innerText || '';

            // Look for betting keywords
            const keywords = [
                '1X2', 'odds', 'Opening', 'Pinnacle', 'Bet365', 'bet365',
                'Home', 'Draw', 'Away', 'bookmaker', 'movement', 'history'
            ];

            const found = keywords.filter(kw => {
                return bodyText.toLowerCase().includes(kw.toLowerCase());
            });

            // Look for odds patterns
            const oddsPattern = /\b([1-9]\.\d{2}|1\d\.\d{2}|20\.00)\b/g;
            const matches = bodyText.match(oddsPattern) || [];

            // Look for bookmaker names
            const bookmakers = [];
            const images = document.querySelectorAll('img');
            images.forEach(img => {
                const alt = img.alt || '';
                const title = img.title || '';
                if (alt.length > 0 && alt.length < 30) bookmakers.push(alt);
                if (title.length > 0 && title.length < 30) bookmakers.push(title);
            });

            return {
                foundKeywords: found,
                oddsCount: matches.length,
                uniqueOdds: [...new Set(matches)].slice(0, 20),
                potentialBookmakers: [...new Set(bookmakers)].slice(0, 10),
                bodyLength: bodyText.length
            };
        });

        log.info(`Body length: ${contentAnalysis.bodyLength} characters`);
        log.info(`Keywords found: ${contentAnalysis.foundKeywords.join(', ') || 'NONE'}`);
        log.info(`Odds patterns: ${contentAnalysis.oddsCount} matches`);
        log.info(`Unique odds: ${contentAnalysis.uniqueOdds.slice(0, 10).join(', ')}...`);
        log.info(`Potential bookmakers: ${contentAnalysis.potentialBookmakers.join(', ') || 'NONE'}`);

        // Diagnostic 4: Get HTML structure preview
        log.section('DIAGNOSTIC 4: HTML STRUCTURE PREVIEW');

        const htmlPreview = await page.evaluate(() => {
            // Get first 50 div elements with their classes and structure
            const divs = document.querySelectorAll('div');
            const result = [];

            for (let i = 0; i < Math.min(50, divs.length); i++) {
                const div = divs[i];
                const info = {
                    index: i,
                    tagName: div.tagName,
                    className: div.className || '',
                    id: div.id || '',
                    childCount: div.children.length,
                    textPreview: div.textContent?.trim().substring(0, 50) || ''
                };
                result.push(info);
            }

            return result;
        });

        log.info('First 50 div elements:');
        htmlPreview.forEach(item => {
            if (item.className || item.id || item.textPreview) {
                log.info(`  [${item.index}] div.${item.className.substring(0, 40)}#${item.id} (${item.childCount} children)`);
                if (item.textPreview) {
                    log.info(`       Text: "${item.textPreview}"`);
                }
            }
        });

        // Diagnostic 5: Look for specific bookmaker patterns
        log.section('DIAGNOSTIC 5: BOOKMAKER PATTERN SEARCH');

        const bookmakerSearch = await page.evaluate(() => {
            const results = [];

            // Look for containers with images
            const containers = document.querySelectorAll('div');
            containers.forEach(container => {
                const images = container.querySelectorAll('img');
                if (images.length > 0) {
                    const imgInfo = [];
                    images.forEach(img => {
                        imgInfo.push({
                            src: img.src?.substring(0, 50) || '',
                            alt: img.alt || '',
                            title: img.title || '',
                            className: img.className || ''
                        });
                    });

                    if (imgInfo.length > 0) {
                        results.push({
                            containerClass: container.className,
                            containerId: container.id,
                            images: imgInfo
                        });
                    }
                }
            });

            return results.slice(0, 10);
        });

        log.info(`Found ${bookmakerSearch.length} containers with images:`);
        bookmakerSearch.forEach((item, i) => {
            log.info(`  Container ${i + 1}: div.${item.containerClass.substring(0, 30)}#${item.containerId}`);
            item.images.forEach(img => {
                const label = img.alt || img.title || img.src.substring(0, 30);
                log.info(`    - Image: "${label}"`);
            });
        });

        // Final verdict
        log.section('V106.002 DIAGNOSTIC SUMMARY');

        if (contentAnalysis.foundKeywords.length >= 3 && contentAnalysis.oddsCount >= 10) {
            log.success('[SUCCESS] Page contains betting data');
            log.info('Recommendations:');
            log.info('  1. Use the class names discovered above');
            log.info('  2. Focus on containers with bookmaker images');
            log.info('  3. Look for odds patterns in text content');
        } else if (contentAnalysis.foundKeywords.length === 0) {
            log.error('[BLOCKED] No betting keywords found - page may be geo-blocked');
            log.info('Recommendations:');
            log.info('  1. Try with proxy/VPN');
            log.info('  2. Check if login is required');
            log.info('  3. Verify cookies are set');
        } else {
            log.warn('[LIMITED] Partial content detected');
            log.info('Recommendations:');
            log.info('  1. Increase wait time for JavaScript rendering');
            log.info('  2. Try scrolling to trigger lazy loading');
            log.info('  3. Check if specific tab needs to be activated');
        }

    } catch (error) {
        log.error(`Diagnostic failed: ${error.message}`);
        console.error(error.stack);
    } finally {
        await page.close();
        await context.close();
        await browser.close();
    }
}

if (require.main === module) {
    diagnoseDOMStructure().catch(error => {
        console.error('[V106.002] Fatal error:', error);
        process.exit(1);
    });
}

module.exports = { diagnoseDOMStructure };
