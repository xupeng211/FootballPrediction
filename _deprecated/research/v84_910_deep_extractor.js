#!/usr/bin/env node
/**
 * V84.910 - 深度数据提取器
 * =============================
 *
 * 提取 window.pageVar 和 window.pageOutrightsVar 的完整内容
 * 以及扫描页面中其他可能的隐藏数据源
 *
 * Usage:
 *   DEBUG=pw:api node v84_910_deep_extractor.js "<URL>" "[SOURCE_ID]"
 */

'use strict';

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const log = {
    info: (msg) => console.log(`[INFO] ${new Date().toISOString()} - ${msg}`),
    error: (msg) => console.error(`[ERROR] ${new Date().toISOString()} - ${msg}`),
    success: (msg) => console.log(`[✓] ${msg}`),
    fail: (msg) => console.log(`[✗] ${msg}`)
};

async function extractDeepData(url, sourceId) {
    log.info("=".repeat(70));
    log.info("V84.910 - 深度数据提取器");
    log.info("=".repeat(70));
    log.info(`URL: ${url}`);
    log.info(`Source ID: ${sourceId}`);
    log.info("");

    const browser = await chromium.launch({
        headless: false,
        timeout: 90000,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const context = await browser.newContext({
        viewport: { width: 1920, height: 1080 },
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    });

    const page = await context.newPage();

    // 导航到目标页面
    log.info("正在加载页面...");
    await page.goto(url, {
        waitUntil: 'networkidle',
        timeout: 90000
    });
    await page.waitForTimeout(5000);
    log.success("页面加载完成");
    log.info("");

    // 提取页面变量
    log.info("[深度提取] 页面变量");
    log.info("");

    const pageData = await page.evaluate(() => {
        const results = {
            pageVar: null,
            pageOutrightsVar: null,
            otherVars: {},
            scriptTags: [],
            hiddenDivs: []
        };

        // 提取 window.pageVar
        if (window.pageVar) {
            try {
                results.pageVar = {
                    type: typeof window.pageVar,
                    keys: Object.keys(window.pageVar),
                    data: window.pageVar
                };
            } catch (e) {
                results.pageVar = { error: e.message };
            }
        }

        // 提取 window.pageOutrightsVar
        if (window.pageOutrightsVar) {
            try {
                results.pageOutrightsVar = {
                    type: typeof window.pageOutrightsVar,
                    keys: Object.keys(window.pageOutrightsVar),
                    data: window.pageOutrightsVar
                };
            } catch (e) {
                results.pageOutrightsVar = { error: e.message };
            }
        }

        // 扫描其他可能的变量
        const suspectVarNames = [
            'oddsData', 'matchData', 'eventData', 'gameData',
            'bettingData', 'pinnacleData', 'oddsPortalData',
            'initialState', 'appState', 'store', '__STATE__',
            '__NEXT_DATA__', '__NUXT__', 'INITIAL_DATA'
        ];

        for (const varName of suspectVarNames) {
            if (window[varName] !== undefined) {
                try {
                    results.otherVars[varName] = {
                        type: typeof window[varName],
                        exists: true,
                        preview: JSON.stringify(window[varName]).substring(0, 500)
                    };
                } catch (e) {
                    results.otherVars[varName] = { error: e.message };
                }
            }
        }

        // 扫描 script 标签中的 JSON
        const scripts = Array.from(document.querySelectorAll('script'));
        for (const script of scripts) {
            const text = script.textContent || '';
            const type = script.type || '';
            const id = script.id || '';

            // 检查 application/json
            if (type === 'application/json') {
                try {
                    const parsed = JSON.parse(text);
                    results.scriptTags.push({
                        type: type,
                        id: id,
                        data: parsed,
                        keywords: JSON.stringify(parsed).toLowerCase()
                    });
                } catch (e) {
                    // 忽略解析错误
                }
            }

            // 检查包含关键字的脚本
            const keywords = ['pinnacle', 'odds', 'betting', 'opening', 'movement'];
            const lowerText = text.toLowerCase();
            const foundKeywords = keywords.filter(k => lowerText.includes(k));

            if (foundKeywords.length > 0 && text.length > 100) {
                results.scriptTags.push({
                    type: type,
                    id: id,
                    keywords: foundKeywords,
                    preview: text.substring(0, 500)
                });
            }
        }

        // 扫描隐藏的 div 容器
        const hiddenDivs = Array.from(document.querySelectorAll('div[style*="display: none"], div[hidden], div[class*="hidden"]'));
        for (const div of hiddenDivs.slice(0, 20)) {
            const id = div.id || '';
            const className = div.className || '';
            const dataAttrs = {};

            for (const attr of div.attributes) {
                if (attr.name.startsWith('data-')) {
                    dataAttrs[attr.name] = attr.value;
                }
            }

            results.hiddenDivs.push({
                id,
                className: typeof className === 'string' ? className.substring(0, 100) : String(className).substring(0, 100),
                dataAttrs,
                textContent: div.textContent ? div.textContent.substring(0, 200) : ''
            });
        }

        return results;
    });

    // 输出结果
    log.success("数据提取完成");
    log.info("");

    // 分析 pageVar
    if (pageData.pageVar && pageData.pageVar.data) {
        log.info("[分析] window.pageVar:");
        log.info(`  类型: ${pageData.pageVar.type}`);
        log.info(`  键: ${pageData.pageVar.keys.join(', ')}`);

        const pageVarStr = JSON.stringify(pageData.pageVar.data);
        const keywords = ['pinnacle', 'betting', 'odds', '18', 'movement'];
        const foundKeywords = keywords.filter(k => pageVarStr.toLowerCase().includes(k.toLowerCase()));

        if (foundKeywords.length > 0) {
            log.success(`  关键词匹配: ${foundKeywords.join(', ')}`);
        } else {
            log.info(`  未发现赔率相关关键词`);
        }
        log.info("");
    }

    // 分析 pageOutrightsVar
    if (pageData.pageOutrightsVar && pageData.pageOutrightsVar.data) {
        log.info("[分析] window.pageOutrightsVar:");
        log.info(`  类型: ${pageData.pageOutrightsVar.type}`);
        log.info(`  键: ${pageData.pageOutrightsVar.keys.join(', ')}`);

        const pageOutrightsVarStr = JSON.stringify(pageData.pageOutrightsVar.data);
        const keywords = ['pinnacle', 'betting', 'odds', '18', 'movement'];
        const foundKeywords = keywords.filter(k => pageOutrightsVarStr.toLowerCase().includes(k.toLowerCase()));

        if (foundKeywords.length > 0) {
            log.success(`  关键词匹配: ${foundKeywords.join(', ')}`);
        } else {
            log.info(`  未发现赔率相关关键词`);
        }
        log.info("");
    }

    // 分析其他变量
    if (Object.keys(pageData.otherVars).length > 0) {
        log.success(`[发现] 找到 ${Object.keys(pageData.otherVars).length} 个其他变量:`);
        for (const [varName, varData] of Object.entries(pageData.otherVars)) {
            log.info(`  window.${varName}: ${varData.type}, 存在: ${varData.exists}`);
        }
        log.info("");
    }

    // 分析 script 标签
    if (pageData.scriptTags.length > 0) {
        log.success(`[发现] 找到 ${pageData.scriptTags.length} 个可疑 script 标签:`);
        for (const script of pageData.scriptTags) {
            if (script.data) {
                log.info(`  <script type="${script.type}" id="${script.id}">`);
                log.info(`    包含 JSON 数据，键: ${Object.keys(script.data).slice(0, 10).join(', ')}`);

                // 检查关键词
                if (script.keywords) {
                    const foundKeywords = ['pinnacle', 'odds', 'betting', '18', 'movement']
                        .filter(k => script.keywords.includes(k));
                    if (foundKeywords.length > 0) {
                        log.success(`      关键词匹配: ${foundKeywords.join(', ')}`);
                    }
                }
            } else if (script.keywords) {
                log.info(`  <script> (预览): ${script.keywords.join(', ')}`);
                log.info(`    ${script.preview.substring(0, 150)}...`);
            }
        }
        log.info("");
    }

    // 分析隐藏 div
    if (pageData.hiddenDivs.length > 0) {
        log.info(`[发现] 找到 ${pageData.hiddenDivs.length} 个隐藏 div 容器`);
        for (const div of pageData.hiddenDivs.slice(0, 5)) {
            if (Object.keys(div.dataAttrs).length > 0 || div.textContent.length > 0) {
                log.info(`  div${div.id ? '#' + div.id : ''} [${div.className.substring(0, 30)}...]`);
                if (Object.keys(div.dataAttrs).length > 0) {
                    log.info(`    data-* 属性: ${Object.keys(div.dataAttrs).join(', ')}`);
                }
                if (div.textContent.length > 50) {
                    log.info(`    内容: ${div.textContent.substring(0, 100)}...`);
                }
            }
        }
        log.info("");
    }

    // 保存完整数据
    const outputPath = path.join(__dirname, '../../logs/v84_910_extraction_4221909.json');
    fs.writeFileSync(outputPath, JSON.stringify(pageData, null, 2), 'utf8');
    log.success(`完整数据已保存: ${outputPath}`);
    log.info("");

    await context.close();
    await browser.close();

    // 最终汇报
    log.info("=".repeat(70));
    log.info("[V84.910] Deep Extraction COMPLETE");
    log.info("=".repeat(70));
    log.info(`Report: ${outputPath}`);
    log.info("=".repeat(70));

    return pageData;
}

// CLI 入口
if (require.main === module) {
    const url = process.argv[2] || 'https://www.oddsportal.com/football/germany/bundesliga-2023-2024/bayern-munich-augsburg-f3e2PS0c/';
    const sourceId = process.argv[3] || '4221909';

    extractDeepData(url, sourceId)
        .then(() => process.exit(0))
        .catch(error => {
            console.error('[FATAL]', error);
            process.exit(1);
        });
}

module.exports = { extractDeepData };
