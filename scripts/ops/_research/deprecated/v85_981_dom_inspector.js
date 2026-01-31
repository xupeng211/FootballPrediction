/**
 * V85.981 DOM Inspector - 页面结构诊断工具
 * ===============================================
 *
 * 用途: 检查页面的实际 DOM 结构，找出提供商行的真实定位方式
 *
 * @usage: node scripts/ops/v85_981_dom_inspector.js
 * @author Senior Node.js & Playwright Engineer
 * @version V85.981
 * @since 2026-01-26
 */

'use strict';

const { chromium } = require('playwright');
const fs = require('fs');

const CONFIG = {
    targetUrl: 'https://www.oddsportal.com/football/england/premier-league-2024-2025/brentford-leicester-SrOgIMxA/',
    headless: false,
    slowMo: 100
};

async function inspectPageStructure() {
    console.log('=== V85.981 DOM Inspector ===');
    console.log(`目标 URL: ${CONFIG.targetUrl}`);

    const browser = await chromium.launch({ headless: CONFIG.headless, slowMo: CONFIG.slowMo });
    const context = await browser.newContext({
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    });
    const page = await context.newPage();

    try {
        // 导航到页面
        console.log('[1/4] 导航到页面...');
        await page.goto(CONFIG.targetUrl, { waitUntil: 'networkidle', timeout: 30000 });
        console.log('[1/4] 页面加载完成');

        // 等待页面稳定 - 更长等待时间以支持动态内容
        console.log('[1/4] 等待动态内容加载 (10秒)...');
        await page.waitForTimeout(10000);

        // 尝试处理 Cookie 弹窗
        console.log('[1/4] 处理 Cookie 弹窗...');
        try {
            const rejectButton = await page.$('button:has-text("Reject All"), button.ot-pc-refuse-all-handler');
            if (rejectButton) {
                await rejectButton.click();
                await page.waitForTimeout(2000);
                console.log('[1/4] Cookie 弹窗已关闭');
            }
        } catch (e) {
            console.log('[1/4] 无 Cookie 弹窗或已关闭');
        }

        // 等待更多动态内容
        await page.waitForTimeout(5000);

        // ===============================================================
        // 检查 1: 查找所有 img 标签 (Logo 诊断)
        // ===============================================================
        console.log('\n[2/4] 检查 Logo 元素...');

        const logoInfo = await page.evaluate(() => {
            const images = Array.from(document.querySelectorAll('img'));
            const providerLogos = images.filter(img => {
                const src = img.src || '';
                const title = img.title || '';
                const alt = img.alt || '';
                return src.includes('innacle') ||
                       title.includes('innacle') ||
                       alt.includes('innacle') ||
                       src.includes('et365') ||
                       title.includes('et365');
            });

            return {
                totalImages: images.length,
                providerLogos: providerLogos.map(img => ({
                    src: img.src,
                    title: img.title,
                    alt: img.alt,
                    className: img.className,
                    parentClass: img.parentElement?.className || 'N/A'
                }))
            };
        });

        console.log(`  - 总图片数: ${logoInfo.totalImages}`);
        console.log(`  - 提供商 Logo 数: ${logoInfo.providerLogos.length}`);
        logoInfo.providerLogos.forEach((logo, i) => {
            console.log(`\n  [Logo ${i + 1}]`);
            console.log(`    src: ${logo.src?.substring(0, 100) || 'N/A'}`);
            console.log(`    title: ${logo.title || 'N/A'}`);
            console.log(`    alt: ${logo.alt || 'N/A'}`);
            console.log(`    className: ${logo.className || 'N/A'}`);
            console.log(`    parentClass: ${logo.parentClass || 'N/A'}`);
        });

        // ===============================================================
        // 检查 2: 查找提供商行结构
        // ===============================================================
        console.log('\n[3/4] 检查提供商行结构...');

        const rowInfo = await page.evaluate(() => {
            // 尝试多种选择器
            const selectors = [
                'div.border-black-borders',
                'div[class*="provider"]',
                'div[class*="bookmaker"]',
                'div[class*="odds"]',
                'table tr',
                'tbody tr'
            ];

            const results = [];

            for (const selector of selectors) {
                const elements = Array.from(document.querySelectorAll(selector));
                if (elements.length > 0) {
                    // 取前 3 个元素作为样本
                    for (let i = 0; i < Math.min(3, elements.length); i++) {
                        const el = elements[i];
                        results.push({
                            selector: selector,
                            index: i,
                            className: el.className,
                            textContent: el.textContent?.substring(0, 100) || 'N/A',
                            innerHTML: el.innerHTML?.substring(0, 200) || 'N/A'
                        });
                    }
                }
            }

            return results;
        });

        console.log(`  - 找到 ${rowInfo.length} 个候选元素:`);
        rowInfo.forEach((row, i) => {
            console.log(`\n  [Row ${i + 1}] ${row.selector} [${row.index}]`);
            console.log(`    className: ${row.className || 'N/A'}`);
            console.log(`    text: ${row.text?.substring(0, 50) || 'N/A'}...`);
        });

        // ===============================================================
        // 检查 3: 查找 "Show more" 类型的展开按钮
        // ===============================================================
        console.log('\n[4/4] 检查展开按钮...');

        const expandButtons = await page.evaluate(() => {
            const buttons = Array.from(document.querySelectorAll('button, a, div[role="button"]'));
            return buttons
                .filter(btn => {
                    const text = btn.textContent?.toLowerCase() || '';
                    return text.includes('show') ||
                           text.includes('more') ||
                           text.includes('expand') ||
                           text.includes('all');
                })
                .map(btn => ({
                    tagName: btn.tagName,
                    textContent: btn.textContent?.trim() || 'N/A',
                    className: btn.className,
                    ariaLabel: btn.getAttribute('aria-label') || 'N/A'
                }));
        });

        console.log(`  - 找到 ${expandButtons.length} 个展开按钮:`);
        expandButtons.forEach((btn, i) => {
            console.log(`\n  [Button ${i + 1}]`);
            console.log(`    tagName: ${btn.tagName}`);
            console.log(`    text: ${btn.textContent || 'N/A'}`);
            console.log(`    className: ${btn.className || 'N/A'}`);
            console.log(`    ariaLabel: ${btn.ariaLabel || 'N/A'}`);
        });

        // ===============================================================
        // 保存完整 HTML 到文件
        // ===============================================================
        console.log('\n保存页面 HTML...');

        const htmlContent = await page.content();
        const outputPath = '/tmp/v85_981_page_structure.html';
        fs.writeFileSync(outputPath, htmlContent);
        console.log(`  - HTML 已保存到: ${outputPath}`);

        // 保持浏览器打开 60 秒以便手动检查
        console.log('\n保持浏览器打开 60 秒以便手动检查...');
        await page.waitForTimeout(60000);

    } finally {
        await browser.close();
    }
}

(async () => {
    try {
        await inspectPageStructure();
        process.exit(0);
    } catch (error) {
        console.error('诊断失败:', error.message);
        console.error(error.stack);
        process.exit(1);
    }
})();
