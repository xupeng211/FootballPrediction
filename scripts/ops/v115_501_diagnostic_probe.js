/**
 * V115.501 DOM Structure Diagnostic Probe
 * ========================================
 * 用于诊断 V115.500 提取失败的根本原因
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const TEST_URL = 'https://www.oddsportal.com/football/england/premier-league-2023-2024/sheffield-utd-chelsea-KYOISX2L/';

async function runDiagnostic() {
    console.log('[V115.501] Starting DOM Structure Diagnostic...\n');

    const browser = await chromium.launch({ headless: false });
    const context = await browser.newContext({
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    });
    const page = await context.newPage();

    try {
        console.log(`[1] Loading page: ${TEST_URL}`);
        await page.goto(TEST_URL, { timeout: 60000, waitUntil: 'networkidle' });

        // 等待内容加载
        let waitAttempts = 0;
        while (waitAttempts < 30) {
            const count = await page.$$eval('div[class*="odd"]', els => els.length);
            if (count > 0) break;
            await page.waitForTimeout(1000);
            waitAttempts++;
        }
        console.log(`[2] Page loaded after ${waitAttempts}s`);

        // 诊断步骤 1: 查找庄家行
        console.log('\n[3] Searching for bookmaker rows...');

        const selectors = [
            'div.flex.h-9.border-b.border-black-borders',
            'div[class*="bookmaker"]',
            'div[class*="row"]',
            'tr',
            'div[class*="flex"]'
        ];

        const diagnosticData = {
            url: TEST_URL,
            timestamp: new Date().toISOString(),
            findings: {}
        };

        for (const selector of selectors) {
            try {
                const elements = await page.$$(selector);
                console.log(`  - Selector "${selector}": ${elements.length} elements`);

                if (elements.length > 0) {
                    // 获取前 3 个元素的 HTML 结构
                    const htmlStructures = [];
                    for (let i = 0; i < Math.min(3, elements.length); i++) {
                        const html = await elements[i].evaluate(el => el.outerHTML.substring(0, 500));
                        htmlStructures.push(html);
                    }
                    diagnosticData.findings[selector] = {
                        count: elements.length,
                        sampleHtml: htmlStructures
                    };
                }
            } catch (e) {
                console.log(`  - Selector "${selector}": ERROR - ${e.message}`);
            }
        }

        // 诊断步骤 2: 查找庄家名称元素
        console.log('\n[4] Searching for bookmaker name elements...');

        const nameSelectors = [
            'img[alt]',
            'span[class*="name"]',
            'div[class*="name"]',
            'a[title]'
        ];

        for (const selector of nameSelectors) {
            try {
                const elements = await page.$$(selector);
                console.log(`  - Selector "${selector}": ${elements.length} elements`);

                if (elements.length > 0) {
                    const names = [];
                    for (let i = 0; i < Math.min(10, elements.length); i++) {
                        try {
                            const text = await elements[i].evaluate(el =>
                                el.getAttribute('alt') || el.getAttribute('title') || el.textContent?.trim()
                            );
                            if (text && text.length > 0 && text.length < 100) {
                                names.push(text);
                            }
                        } catch (e) { }
                    }
                    console.log(`    Sample names: ${names.slice(0, 5).join(', ')}`);
                    diagnosticData.findings[`names_${selector}`] = names.slice(0, 10);
                }
            } catch (e) {
                console.log(`  - Selector "${selector}": ERROR - ${e.message}`);
            }
        }

        // 诊断步骤 3: 查找赔率单元格
        console.log('\n[5] Searching for odds cells...');

        const oddsSelectors = [
            'div.odds-cell',
            'div[class*="odd"]',
            'span[class*="odd"]',
            'a[href*="/odds/"]'
        ];

        for (const selector of oddsSelectors) {
            try {
                const elements = await page.$$(selector);
                console.log(`  - Selector "${selector}": ${elements.length} elements`);

                if (elements.length > 0) {
                    const oddsValues = [];
                    for (let i = 0; i < Math.min(10, elements.length); i++) {
                        try {
                            const text = await elements[i].evaluate(el => el.textContent?.trim());
                            if (text && text.match(/^\d+\.\d+$/)) {
                                oddsValues.push(text);
                            }
                        } catch (e) { }
                    }
                    console.log(`    Sample odds: ${oddsValues.slice(0, 5).join(', ')}`);
                    diagnosticData.findings[`odds_${selector}`] = oddsValues.slice(0, 10);
                }
            } catch (e) {
                console.log(`  - Selector "${selector}": ERROR - ${e.message}`);
            }
        }

        // 诊断步骤 4: 尝试悬停并检测 Modal
        console.log('\n[6] Testing hover interaction...');

        // 找一个可能的赔率单元格
        const oddsCell = await page.$('div[class*="odd"]');
        if (oddsCell) {
            console.log('  Found odds cell, attempting hover...');

            await oddsCell.hover();
            await page.waitForTimeout(3000);

            // 检查 Modal
            const modalSelectors = [
                'h3:has-text("Odds movement")',
                'div[class*="modal"]',
                'div[class*="popup"]',
                'div[class*="tooltip"]'
            ];

            for (const selector of modalSelectors) {
                try {
                    const modal = await page.$(selector);
                    if (modal) {
                        console.log(`  ✓ Modal detected with selector: ${selector}`);

                        const modalHtml = await modal.evaluate(el => {
                            let container = el;
                            let depth = 0;
                            while (container && depth < 10) {
                                const classes = container.className || '';
                                const hasModalClass = /modal|popup|dialog|tooltip|dropdown/i.test(classes);
                                const hasRole = container.getAttribute('role') === 'dialog';
                                const isFixedOrAbsolute = /fixed|absolute/.test(window.getComputedStyle(container).position);

                                if (hasModalClass || hasRole || (isFixedOrAbsolute && classes.length > 10)) {
                                    return container.outerHTML.substring(0, 2000);
                                }
                                container = container.parentElement;
                                depth++;
                            }
                            return el.outerHTML.substring(0, 2000);
                        });

                        console.log(`  Modal HTML preview: ${modalHtml.substring(0, 300)}...`);
                        diagnosticData.findings.modalDetected = true;
                        diagnosticData.findings.modalSelector = selector;
                        diagnosticData.findings.modalHtmlPreview = modalHtml.substring(0, 1000);
                        break;
                    }
                } catch (e) {
                    console.log(`  ✗ Modal check failed for selector ${selector}: ${e.message}`);
                }
            }
        } else {
            console.log('  ✗ No odds cell found for hover test');
        }

        // 保存诊断数据
        const outputPath = path.join(__dirname, '../../logs/v115_500_test/v115_501_diagnostic.json');
        fs.writeFileSync(outputPath, JSON.stringify(diagnosticData, null, 2), 'utf-8');
        console.log(`\n[7] Diagnostic data saved to: ${outputPath}`);

        // 打印总结
        console.log('\n' + '='.repeat(80));
        console.log('[V115.501] DIAGNOSTIC SUMMARY');
        console.log('='.repeat(80));
        console.log(`Bookmaker rows found: ${Object.values(diagnosticData.findings).filter(f => f.count && f.count > 0).reduce((sum, f) => sum + f.count, 0) || 0}`);
        console.log(`Names extracted: ${Object.values(diagnosticData.findings).filter(f => Array.isArray(f) && f.length > 0).reduce((sum, f) => sum + f.length, 0) || 0}`);
        console.log(`Modal detected: ${diagnosticData.findings.modalDetected ? 'YES' : 'NO'}`);
        console.log('='.repeat(80) + '\n');

    } finally {
        await page.close();
        await context.close();
        await browser.close();
    }
}

runDiagnostic().catch(console.error);
