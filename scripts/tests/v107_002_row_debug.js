/**
 * V107.002 Row Structure Debug
 * ============================
 *
 * V107.002: Debug actual row structure found by selector
 *
 * @version V107.002
 * @since 2026-01-27
 */

'use strict';

const { chromium } = require('playwright');

const TARGET_URL = 'https://www.oddsportal.com/football/england/premier-league/brighton-everton-vPKFVEM6/';

async function debugRowStructure() {
    console.log('[V107.002] ROW STRUCTURE DEBUG');
    console.log('='.repeat(70));

    const browser = await chromium.launch({
        headless: false
    });

    const page = await browser.newPage({
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        viewport: { width: 1920, height: 1080 }
    });

    try {
        console.log('Navigating to:', TARGET_URL);
        await page.goto(TARGET_URL, {
            timeout: 60000,
            waitUntil: 'networkidle'
        });

        await page.waitForTimeout(5000);

        // Test the selector that found 17 elements
        const selector = 'div[class*="border"][class*="flex"][class*="h-9"]';
        console.log(`\nTesting selector: ${selector}`);

        const elements = await page.$$(selector);
        console.log(`Found ${elements.length} elements`);

        // Analyze first 3 elements
        for (let i = 0; i < Math.min(3, elements.length); i++) {
            console.log(`\n--- Element ${i + 1} ---`);

            const info = await elements[i].evaluate(el => {
                return {
                    tagName: el.tagName,
                    className: el.className,
                    childElementCount: el.childElementCount,
                    textContent: el.textContent?.trim().substring(0, 100),
                    innerHTML: el.innerHTML.substring(0, 500)
                };
            });

            console.log(`Tag: ${info.tagName}`);
            console.log(`Class: ${info.className}`);
            console.log(`Children: ${info.childElementCount}`);
            console.log(`Text: ${info.textContent}`);
            console.log(`HTML preview: ${info.innerHTML}`);

            // Check if it has odds-cell children
            const hasOddsCell = await elements[i].evaluate(el => {
                return el.querySelector('.odds-cell') !== null;
            });
            console.log(`Has .odds-cell child: ${hasOddsCell}`);

            // Count children with border class
            const borderChildren = await elements[i].$$eval('div[class*="border"]', els => els.length);
            console.log(`Children with 'border' class: ${borderChildren}`);
        }

        // Now try to find the actual odds cells directly
        console.log(`\n\n=== LOOKING FOR ODDS CELLS DIRECTLY ===`);

        const oddsCells = await page.$$('div.odds-cell');
        console.log(`Found ${oddsCells.length} div.odds-cell elements`);

        if (oddsCells.length > 0) {
            console.log(`\n--- First odds cell ---`);
            const cellInfo = await oddsCells[0].evaluate(el => {
                // Get parent chain
                const parents = [];
                let p = el.parentElement;
                let depth = 0;
                while (p && depth < 5) {
                    parents.push({
                        tagName: p.tagName,
                        className: p.className,
                        text: p.textContent?.trim().substring(0, 50)
                    });
                    p = p.parentElement;
                    depth++;
                }
                return {
                    tagName: el.tagName,
                    className: el.className,
                    text: el.textContent?.trim(),
                    parents: parents
                };
            });

            console.log(`Cell class: ${cellInfo.className}`);
            console.log(`Cell text: ${cellInfo.text}`);
            console.log(`Parent chain:`);
            for (let i = 0; i < cellInfo.parents.length; i++) {
                console.log(`  ${i}: ${cellInfo.parents[i].tagName}`);
                console.log(`     Class: ${cellInfo.parents[i].className.substring(0, 100)}`);
                console.log(`     Text: ${cellInfo.parents[i].text}`);
            }
        }

    } catch (error) {
        console.error('Error:', error.message);
        console.error(error.stack);
    } finally {
        await browser.close();
    }
}

if (require.main === module) {
    debugRowStructure().catch(error => {
        console.error('[V107.002] Fatal error:', error);
        process.exit(1);
    });
}

module.exports = { debugRowStructure };
