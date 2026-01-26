/**
 * V85.951 Node-417 Armoring Test
 * =================================
 *
 * 针对特定动态组件 (Identifier-417) 的定位精度增强验证
 *
 * 功能：
 *   - 三级联合定位器验证 (属性/合约/结构匹配)
 *   - 坐标偏移重试机制验证 (Hover Calibration)
 *   - 失败样本诊断与重测
 *
 * @author Senior UI Automation Engineer
 * @version V85.951
 * @since 2026-01-25
 */

'use strict';

const { chromium } = require('playwright');
const path = require('path');

// 导入 V85.951 增强模块
const interactionV51 = require('./modules/interaction_v51');

// ============================================================================
// CONFIGURATION
// ============================================================================

const TEST_CONFIG = {
    // 失败样本 URL (用于验证)
    sampleUrls: {
        'ruGqvr3C': 'https://www.oddsportal.com/match/ruGqvr3C/',  // 样本 1
        '4hZVgSCF': 'https://www.oddsportal.com/match/4hZVgSCF/'   // 样本 2
    },

    // 目标提供商
    targetProviders: ['PINNACLE', 'BET365'],

    // 浏览器配置
    browser: {
        headless: false,
        timeout: 30000
    },

    // V85.951 测试配置
    v85_951: {
        enableTripleLocator: true,
        enableCalibratedHover: true,
        maxProviders: 2,
        maxRetries: 2
    }
};

// ============================================================================
// TEST FUNCTIONS
// ============================================================================

/**
 * V85.951: 单个提供商定位测试
 *
 * @param {import('@playwright/test').Page} page - Playwright 页面对象
 * @param {string} providerKey - 提供商键
 * @returns {Promise<Object>}
 */
async function testProviderLocator(page, providerKey) {
    console.log(`\n[V85.951] 测试提供商定位: ${providerKey}`);
    console.log('='.repeat(60));

    const startTime = Date.now();

    try {
        // 使用三级联合定位器
        const result = await interactionV51.locateProviderWithTripleLocator(page, providerKey);

        const elapsedTime = Date.now() - startTime;

        const report = {
            provider: providerKey,
            success: result.element !== null,
            method: result.method,
            selector: result.selector,
            elapsedTime: `${elapsedTime}ms`,
            timestamp: new Date().toISOString()
        };

        console.log(`  ✓ 方法: ${result.method}`);
        console.log(`  ✓ 选择器: ${result.selector}`);
        console.log(`  ✓ 状态: ${result.element ? '成功' : '失败'}`);
        console.log(`  ✓ 耗时: ${elapsedTime}ms`);

        return report;

    } catch (error) {
        const elapsedTime = Date.now() - startTime;
        console.error(`  ✗ 错误: ${error.message}`);

        return {
            provider: providerKey,
            success: false,
            method: 'error',
            selector: '',
            error: error.message,
            elapsedTime: `${elapsedTime}ms`
        };
    }
}

/**
 * V85.951: 坐标偏移重试测试
 *
 * @param {import('@playwright/test').Page} page - Playwright 页面对象
 * @returns {Promise<Object>}
 */
async function testCalibratedHover(page) {
    console.log('\n[V85.951] 测试坐标偏移重试');
    console.log('='.repeat(60));

    const startTime = Date.now();

    try {
        // 首先定位一个提供商行
        const locatorResult = await interactionV51.locateProviderWithTripleLocator(page, 'PINNACLE');

        if (!locatorResult.element) {
            throw new Error('无法定位提供商行');
        }

        // 执行坐标偏移重试
        const hoverResult = await interactionV51.calibratedHover(locatorResult.element, page, {
            initialTimeout: 3000,
            anchorSelector: 'h3:text("Odds movement"), h3:has-text("Odds movement")'
        });

        const elapsedTime = Date.now() - startTime;

        const report = {
            success: hoverResult.success,
            attempts: hoverResult.attempts,
            finalMethod: hoverResult.finalMethod,
            elapsedTime: `${elapsedTime}ms`,
            timestamp: new Date().toISOString()
        };

        console.log(`  ✓ 成功: ${hoverResult.success}`);
        console.log(`  ✓ 尝试次数: ${hoverResult.attempts}`);
        console.log(`  ✓ 最终方法: ${hoverResult.finalMethod}`);
        console.log(`  ✓ 耗时: ${elapsedTime}ms`);

        return report;

    } catch (error) {
        const elapsedTime = Date.now() - startTime;
        console.error(`  ✗ 错误: ${error.message}`);

        return {
            success: false,
            attempts: 0,
            finalMethod: 'error',
            error: error.message,
            elapsedTime: `${elapsedTime}ms`
        };
    }
}

/**
 * V85.951: 综合验证测试
 *
 * @param {import('@playwright/test').Page} page - Playwright 页面对象
 * @returns {Promise<Object>}
 */
async function runComprehensiveTest(page) {
    console.log('\n[V85.951] 综合验证测试启动');
    console.log('='.repeat(60));

    const results = {
        locator: {},
        hover: null,
        summary: {
            totalTests: 0,
            passedTests: 0,
            failedTests: 0
        }
    };

    // 测试所有目标提供商的定位
    for (const providerKey of TEST_CONFIG.targetProviders) {
        const report = await testProviderLocator(page, providerKey);
        results.locator[providerKey] = report;
        results.summary.totalTests++;

        if (report.success) {
            results.summary.passedTests++;
        } else {
            results.summary.failedTests++;
        }
    }

    // 测试坐标偏移重试
    const hoverReport = await testCalibratedHover(page);
    results.hover = hoverReport;
    results.summary.totalTests++;

    if (hoverReport.success) {
        results.summary.passedTests++;
    } else {
        results.summary.failedTests++;
    }

    return results;
}

/**
 * V85.951: 失败样本验证
 *
 * @param {string} sampleName - 样本名称
 * @param {string} url - 目标 URL
 * @returns {Promise<Object>}
 */
async function validateFailedSample(sampleName, url) {
    console.log(`\n[V85.951] 验证失败样本: ${sampleName}`);
    console.log('='.repeat(60));
    console.log(`  URL: ${url}`);

    const browser = await chromium.launch({ headless: TEST_CONFIG.browser.headless });
    const context = await browser.newContext({
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    });
    const page = await context.newPage();

    try {
        await page.goto(url, { timeout: TEST_CONFIG.browser.timeout, waitUntil: 'networkidle' });
        await page.waitForTimeout(2000); // 等待动态内容加载

        const results = await runComprehensiveTest(page);

        await browser.close();

        return {
            sample: sampleName,
            url: url,
            ...results,
            timestamp: new Date().toISOString()
        };

    } catch (error) {
        await browser.close();
        console.error(`  ✗ 错误: ${error.message}`);

        return {
            sample: sampleName,
            url: url,
            error: error.message,
            timestamp: new Date().toISOString()
        };
    }
}

// ============================================================================
// REPORT GENERATION
// ============================================================================

/**
 * 生成 V85.951 验证报告
 *
 * @param {Object} results - 测试结果
 * @returns {string} - 格式化报告
 */
function generateReport(results) {
    const lines = [];

    lines.push('');
    lines.push('╔════════════════════════════════════════════════════════════╗');
    lines.push('║           [V85.951] Node-417 Armoring Report              ║');
    lines.push('╚════════════════════════════════════════════════════════════╝');
    lines.push('');
    lines.push(`时间戳: ${new Date().toISOString()}`);
    lines.push('');

    // 汇总统计
    if (results.summary) {
        lines.push('─── 测试统计 ───');
        lines.push(`  总测试数: ${results.summary.totalTests}`);
        lines.push(`  通过: ${results.summary.passedTests}`);
        lines.push(`  失败: ${results.summary.failedTests}`);
        lines.push(`  成功率: ${results.summary.totalTests > 0 ? ((results.summary.passedTests / results.summary.totalTests) * 100).toFixed(1) : 0}%`);
        lines.push('');
    }

    // 定位器结果
    if (results.locator) {
        lines.push('─── 三级联合定位器结果 ───');
        for (const [provider, report] of Object.entries(results.locator)) {
            lines.push(`  ${provider}:`);
            lines.push(`    状态: ${report.success ? '✓ 成功' : '✗ 失败'}`);
            lines.push(`    方法: ${report.method}`);
            lines.push(`    选择器: ${report.selector}`);
            lines.push(`    耗时: ${report.elapsedTime}`);
        }
        lines.push('');
    }

    // Hover 结果
    if (results.hover) {
        lines.push('─── 坐标偏移重试结果 ───');
        lines.push(`  状态: ${results.hover.success ? '✓ 成功' : '✗ 失败'}`);
        lines.push(`  尝试次数: ${results.hover.attempts}`);
        lines.push(`  最终方法: ${results.hover.finalMethod}`);
        lines.push(`  耗时: ${results.hover.elapsedTime}`);
        lines.push('');
    }

    // 选择路径汇总
    lines.push('─── Selection Path ───');
    lines.push('  复合选择器策略:');
    lines.push('    1. img[title*="Pinnacle" i] (权重 1: 属性匹配)');
    lines.push('    2. [data-bookmaker-id="417"] (权重 2: 合约匹配)');
    lines.push('    3. div:has-text("Pinnacle") (权重 3: 结构匹配)');
    lines.push('');

    // 最终状态
    const successRate = results.summary?.totalTests > 0
        ? ((results.summary.passedTests / results.summary.totalTests) * 100).toFixed(0)
        : '0';

    lines.push('─── 最终验证 ───');
    lines.push(`  Detection Rate: ${successRate}%`);
    lines.push(`  Ready for V86 Stress Test? ${successRate >= 80 ? 'YES ✓' : 'NO ✗'}`);
    lines.push('');

    return lines.join('\n');
}

// ============================================================================
// MAIN ENTRY
// ============================================================================

async function main() {
    console.log('\n[V85.951] Node-417 Armoring Test Suite');
    console.log('='.repeat(60));

    const allResults = [];

    // 验证失败样本
    for (const [sampleName, url] of Object.entries(TEST_CONFIG.sampleUrls)) {
        const result = await validateFailedSample(sampleName, url);
        allResults.push(result);

        // 输出单个样本报告
        console.log(generateReport(result));
    }

    // 汇总报告
    if (allResults.length > 1) {
        const totalTests = allResults.reduce((sum, r) => sum + (r.summary?.totalTests || 0), 0);
        const passedTests = allResults.reduce((sum, r) => sum + (r.summary?.passedTests || 0), 0);
        const overallRate = ((passedTests / totalTests) * 100).toFixed(0);

        console.log('╔════════════════════════════════════════════════════════════╗');
        console.log(`║           [V85.951] Overall Detection Rate: ${overallRate}%           ║`);
        console.log(`║  Success Rate: ${passedTests}/${totalTests} (${overallRate}%)                            ║`);
        console.log(`║  Ready for V86 Stress Test? ${overallRate >= 80 ? 'YES ✓' : 'NO ✗'}                    ║`);
        console.log('╚════════════════════════════════════════════════════════════╝');
    }
}

// 运行测试
if (require.main === module) {
    main().catch(error => {
        console.error('[V85.951] 测试失败:', error);
        process.exit(1);
    });
}

module.exports = {
    testProviderLocator,
    testCalibratedHover,
    runComprehensiveTest,
    validateFailedSample,
    generateReport
};
