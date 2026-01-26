/**
 * V107.001 DOM Structure Analysis
 * ================================
 *
 * V107.001: Analyze actual DOM structure to find correct selectors
 *
 * @version V107.001
 * @since 2026-01-27
 */

'use strict';

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const TARGET_URL = 'https://www.oddsportal.com/football/england/premier-league/brighton-everton-vPKFVEM6/';
const OUTPUT_DIR = path.join(__dirname, '../../logs/v107_hover');

if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

const CONFIG = {
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    viewport: { width: 1920, height: 1080 },
    timeout: 60000
};

async function analyzeDOMStructure() {
    console.log('[V107.001] DOM STRUCTURE ANALYSIS');
    console.log('=' .repeat(70));

    const browser = await chromium.launch({
        headless: false
    });

    const page = await browser.newPage({
        userAgent: CONFIG.userAgent,
        viewport: CONFIG.viewport
    });

    try {
        console.log('Navigating to:', TARGET_URL);
        await page.goto(TARGET_URL, {
            timeout: CONFIG.timeout,
            waitUntil: 'networkidle'
        });

        console.log('Waiting for page to stabilize...');
        await page.waitForTimeout(5000);

        console.log('\n' + '='.repeat(70));
        console.log('ANALYZING PAGE STRUCTURE');
        console.log('='.repeat(70));

        // Analyze page structure in browser context
        const analysis = await page.evaluate(() => {
            const results = {};

            // 1. Check React containers
            results.reactContainers = [];
            document.querySelectorAll('[id*="react"], [id*="app"]').forEach(el => {
                results.reactContainers.push({
                    id: el.id,
                    children: el.children.length,
                    innerHTML_length: el.innerHTML.length,
                    textContent_length: el.textContent?.length || 0
                });
            });

            // 2. Look for odds/numbers in the page
            results.oddsElements = [];
            document.querySelectorAll('div, span, td').forEach(el => {
                const text = el.textContent?.trim();
                // Look for decimal odds patterns (e.g., 1.5, 2.25, 3.75)
                if (text && /^\d+\.\d+$/.test(text) && parseFloat(text) > 1 && parseFloat(text) < 10) {
                    // Get parent hierarchy
                    const parents = [];
                    let parent = el.parentElement;
                    let depth = 0;
                    while (parent && depth < 5) {
                        parents.push({
                            tagName: parent.tagName,
                            classList: Array.from(parent.classList),
                            id: parent.id
                        });
                        parent = parent.parentElement;
                        depth++;
                    }
                    results.oddsElements.push({
                        text,
                        tagName: el.tagName,
                        classList: Array.from(el.classList),
                        parents: parents.slice(0, 3)
                    });
                }
            });
            // Limit to first 20
            results.oddsElements = results.oddsElements.slice(0, 20);

            // 3. Look for tables with odds data
            results.tables = [];
            document.querySelectorAll('table').forEach((table, idx) => {
                const rows = table.querySelectorAll('tr').length;
                const cells = table.querySelectorAll('td').length;
                const hasNumbers = /\d+\.\d+/.test(table.textContent);
                results.tables.push({
                    index: idx,
                    rows,
                    cells,
                    hasNumbers,
                    classList: Array.from(table.classList)
                });
            });

            // 4. Look for specific elements that might contain odds
            results.specificSelectors = {
                'div[class*="border"]': document.querySelectorAll('div[class*="border"]').length,
                'div[class*="odd"]': document.querySelectorAll('div[class*="odd"]').length,
                'div[class*="bet"]': document.querySelectorAll('div[class*="bet"]').length,
                'div[class*="provider"]': document.querySelectorAll('div[class*="provider"]').length,
                'div[class*="bookmaker"]': document.querySelectorAll('div[class*="bookmaker"]').length,
                'span[class*="odd"]': document.querySelectorAll('span[class*="odd"]').length,
                'td[class*="odd"]': document.querySelectorAll('td[class*="odd"]').length,
            };

            // 5. Get main content area
            results.mainContent = {
                bodyLength: document.body.innerHTML.length,
                bodyPreview: document.body.innerHTML.substring(0, 2000)
            };

            // 6. Look for hover-able elements
            results.hoverableElements = [];
            document.querySelectorAll('[onmouseover], [data-hover], [class*="hover"], button').forEach(el => {
                results.hoverableElements.push({
                    tagName: el.tagName,
                    classList: Array.from(el.classList),
                    hasOnMouseOver: el.hasAttribute('onmouseover')
                });
            });
            results.hoverableElements = results.hoverableElements.slice(0, 10);

            return results;
        });

        // Print analysis
        console.log('\n1. REACT CONTAINERS:');
        console.log(JSON.stringify(analysis.reactContainers, null, 2));

        console.log('\n2. ODDS ELEMENTS (sample):');
        for (const elem of analysis.oddsElements.slice(0, 5)) {
            console.log(`  ${elem.text} - ${elem.tagName}.${elem.classList.join('.')}`);
            if (elem.parents.length > 0) {
                console.log(`    Parent: ${elem.parents[0].tagName} . ${elem.parents[0].classList.join('.')}`);
            }
        }

        console.log('\n3. TABLES:');
        console.log(JSON.stringify(analysis.tables, null, 2));

        console.log('\n4. SPECIFIC SELECTORS:');
        console.log(JSON.stringify(analysis.specificSelectors, null, 2));

        console.log('\n5. HOVERABLE ELEMENTS:');
        console.log(JSON.stringify(analysis.hoverableElements, null, 2));

        console.log('\n6. MAIN CONTENT:');
        console.log(`  Body length: ${analysis.mainContent.bodyLength} chars`);
        console.log(`  Preview: ${analysis.mainContent.bodyPreview.substring(0, 500)}`);

        // Save full analysis
        const analysisPath = path.join(OUTPUT_DIR, 'dom_analysis.json');
        fs.writeFileSync(analysisPath, JSON.stringify(analysis, null, 2), 'utf-8');
        console.log(`\nFull analysis saved to: ${analysisPath}`);

        // Save page HTML
        const pageHtml = await page.content();
        const htmlPath = path.join(OUTPUT_DIR, 'page_full.html');
        fs.writeFileSync(htmlPath, pageHtml, 'utf-8');
        console.log(`Page HTML saved to: ${htmlPath}`);

    } catch (error) {
        console.error('Error:', error.message);
        console.error(error.stack);
    } finally {
        await browser.close();
    }
}

if (require.main === module) {
    analyzeDOMStructure().catch(error => {
        console.error('[V107.001] Fatal error:', error);
        process.exit(1);
    });
}

module.exports = { analyzeDOMStructure };
