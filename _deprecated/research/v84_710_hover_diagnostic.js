#!/usr/bin/env node
/**
 * V84.710 - Hover 交互诊断工具
 * =============================
 *
 * 用于诊断 OddsPortal 2026 的 hover 交互行为
 *
 * Usage:
 *   DEBUG=pw:api node v84_710_hover_diagnostic.js "<URL>"
 */

'use strict';

const { chromium } = require('playwright');

async function diagnoseHover(url) {
    console.log('='.repeat(60));
    console.log('V84.710 Hover 交互诊断');
    console.log('='.repeat(60));
    console.log(`URL: ${url}`);
    console.log('');

    const browser = await chromium.launch({
        headless: false,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const context = await browser.newContext({
        viewport: { width: 1920, height: 1080 },
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    });

    const page = await context.newPage();

    // 页面加载
    console.log('[1/4] 加载页面...');
    await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(5000);
    console.log('  页面加载完成');

    // 查找可交互元素
    console.log('');
    console.log('[2/4] 查找可交互元素...');

    const selectors = [
        '[data-testid="bookie-logo"]',
        '[data-testid="bookmaker-name"]',
        '[data-testid="betting-exchanges-table-row"]',
        '[data-testid="dropping-odds"]',
        'div[class*="bottom-"]',
        'a[href*="pinnacle"]',
        'a[href*="bet365"]'
    ];

    for (const selector of selectors) {
        const count = await page.$$(selector);
        if (count.length > 0) {
            console.log(`  ✓ ${selector}: ${count.length} 个`);
        }
    }

    // 尝试 hover 第一个元素
    console.log('');
    console.log('[3/4] 测试 hover 交互...');

    const firstElement = await page.$('[data-testid="betting-exchanges-table-row"]');
    if (!firstElement) {
        console.log('  ✗ 未找到可交互元素');
        await browser.close();
        return;
    }

    console.log('  Hover 前的 DOM 状态:');
    const beforeTooltip = await page.$('div[class*="bottom-"]');
    console.log(`    bottom- divs: ${beforeTooltip ? '存在' : '不存在'}`);

    // 执行 hover
    console.log('  执行 hover...');
    await firstElement.hover();
    await page.waitForTimeout(5000);

    console.log('  Hover 后的 DOM 状态:');
    const afterTooltip = await page.$$('div[class*="bottom-"]');
    console.log(`    bottom- divs: ${afterTooltip.length} 个`);

    // 检查新出现的元素
    console.log('');
    console.log('[4/4] 检查新出现的元素...');

    const newElements = await page.evaluate(() => {
        const results = [];

        // 查找所有可能包含赔率的元素
        const oddElements = document.querySelectorAll('[class*="odd"], [class*="price"], [data-odd]');

        for (const el of oddElements) {
            const text = el.textContent || '';
            if (/\d+\.\d+/.test(text)) {
                results.push({
                    tag: el.tagName,
                    class: el.className,
                    text: text.substring(0, 50),
                    visible: el.offsetParent !== null
                });
            }
        }

        return results.slice(0, 10);
    });

    console.log(`  找到 ${newElements.length} 个可能包含赔率的元素:`);
    for (const el of newElements) {
        console.log(`    - ${el.tag}.${el.class.substring(0, 30)}: "${el.text}" (visible: ${el.visible})`);
    }

    // 截图
    const screenshotPath = '/home/user/projects/FootballPrediction/logs/hover_screenshot.png';
    await page.screenshot({ path: screenshotPath, fullPage: false });
    console.log('');
    console.log(`  截图已保存: ${screenshotPath}`);

    // 导出 hover 后的 HTML
    const htmlContent = await page.content();
    const htmlPath = '/home/user/projects/FootballPrediction/logs/hover_snapshot.html';
    require('fs').writeFileSync(htmlPath, htmlContent, 'utf8');
    console.log(`  HTML 已导出: ${htmlPath}`);
    console.log(`    文件大小: ${(htmlContent.length / 1024).toFixed(2)} KB`);

    await browser.close();

    console.log('');
    console.log('='.repeat(60));
    console.log('V84.710 诊断完成');
    console.log('='.repeat(60));
}

// CLI 入口
if (require.main === module) {
    const url = process.argv[2];
    if (!url) {
        console.error('Usage: node v84_710_hover_diagnostic.js "<URL>"');
        process.exit(1);
    }

    diagnoseHover(url)
        .then(() => process.exit(0))
        .catch(error => {
            console.error('[FATAL]', error);
            process.exit(1);
        });
}

module.exports = { diagnoseHover };
