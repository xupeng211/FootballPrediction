/**
 * V85.980 Matrix Force-Unlock Test
 * ====================================
 *
 * 测试目标:
 *   - 补丁动作 A: 激活折叠内容 (Pinnacle 是否现身)
 *   - 补丁动作 B: Click Fallback (点击是否唤起弹窗)
 *   - 补丁动作 C: Logo 路径选择器 (src 比 title 更稳定)
 *
 * @usage: node scripts/ops/v85_980_matrix_force_unlock_test.js
 * @author Senior Node.js & Playwright Engineer
 * @version V85.980
 * @since 2026-01-26
 */

'use strict';

const { chromium } = require('playwright');
const path = require('path');
const interactionV51 = require('./modules/interaction_v51');
const logger = require('./modules/logger');
const log = logger.createLogger('v85_980_test');

// ============================================================================
// CONFIGURATION
// ============================================================================

const CONFIG = {
    // 目标哈希 (用户指定的测试案例)
    targetHash: 'SrOgIMxA',

    // OddsPortal URL (从数据库获取的完整 URL)
    targetUrl: 'https://www.oddsportal.com/football/england/premier-league-2024-2025/brentford-leicester-SrOgIMxA/',

    // 浏览器配置
    browserConfig: {
        headless: false,  // 显示浏览器窗口以便观察
        slowMo: 100,      // 慢速模式以便观察
        timeout: 60000
    },

    // Ghost Protocol 配置 (反爬检测)
    ghostProtocol: {
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        viewport: { width: 1920, height: 1080 },
        locale: 'en-US',
        timezoneId: 'America/New_York'
    }
};

// ============================================================================
// TEST FUNCTIONS
// ============================================================================

/**
 * V85.980: 主测试函数
 */
async function runMatrixForceUnlockTest() {
    log.info('=== V85.980 Matrix Force-Unlock Test ===');
    log.info(`目标哈希: ${CONFIG.targetHash}`);
    log.info(`目标 URL: ${CONFIG.targetUrl}`);

    let browser = null;
    let context = null;
    let page = null;

    try {
        // =======================================================================
        // Step 1: 启动浏览器 (Ghost Protocol)
        // =======================================================================
        log.info('[1/6] 启动浏览器...');
        browser = await chromium.launch({
            headless: CONFIG.browserConfig.headless,
            slowMo: CONFIG.browserConfig.slowMo
        });

        context = await browser.newContext({
            userAgent: CONFIG.ghostProtocol.userAgent,
            viewport: CONFIG.ghostProtocol.viewport,
            locale: CONFIG.ghostProtocol.locale,
            timezoneId: CONFIG.ghostProtocol.timezoneId
        });

        page = await context.newPage();
        page.setDefaultTimeout(CONFIG.browserConfig.timeout);

        log.success('[1/6] 浏览器启动成功');

        // =======================================================================
        // Step 2: 导航到目标页面
        // =======================================================================
        log.info(`[2/6] 导航到目标页面: ${CONFIG.targetUrl}`);

        await page.goto(CONFIG.targetUrl, { waitUntil: 'networkidle', timeout: 30000 });
        log.success('[2/6] 页面加载完成');

        // =======================================================================
        // Step 3: V85.980 补丁动作 A - 激活折叠内容
        // =======================================================================
        log.info('[3/6] V85.980 补丁动作 A: 激活折叠内容...');

        const expandResult = await interactionV51.expandAllCollapsedContent(page);

        log.info(`[3/6] 补丁动作 A 结果:`);
        log.info(`  - Success: ${expandResult.success}`);
        log.info(`  - Expanded Count: ${expandResult.expandedCount}`);
        if (expandResult.errors.length > 0) {
            log.warn(`  - Errors: ${expandResult.errors.join(', ')}`);
        }

        // =======================================================================
        // Step 4: 检查 Pinnacle 是否现身
        // =======================================================================
        log.info('[4/6] 检查 Pinnacle 是否现身...');

        const pinnacleFound = await checkPinnaclePresence(page);

        log.info(`[4/6] Pinnacle 存在性检查:`);
        log.info(`  - Logo (title): ${pinnacleFound.logoTitle ? 'YES' : 'NO'}`);
        log.info(`  - Logo (src): ${pinnacleFound.logoSrc ? 'YES' : 'NO'}`);
        log.info(`  - Logo (alt): ${pinnacleFound.logoAlt ? 'YES' : 'NO'}`);
        log.info(`  - Row Element: ${pinnacleFound.rowElement ? 'YES' : 'NO'}`);
        log.info(`  - Overall: ${pinnacleFound.found ? 'YES ✓' : 'NO ✗'}`);

        if (!pinnacleFound.found) {
            log.warn('[4/6] Pinnacle 未找到，可能需要手动检查页面结构');
        }

        // =======================================================================
        // Step 5: V85.980 补丁动作 B + C - 视觉取证测试
        // =======================================================================
        log.info('[5/6] V85.980 补丁动作 B + C: 视觉取证测试...');

        const visualResult = await interactionV51.captureOddsMovementVisually(page, {
            maxProviders: 1,  // 只测试 Pinnacle
            expandCollapsed: false,  // 已经在 Step 3 执行过了
            enableRetry: true,
            maxRetries: 2
        });

        log.info(`[5/6] 视觉取证结果:`);
        log.info(`  - Success: ${visualResult.success}`);
        log.info(`  - Processed Count: ${visualResult.processedCount}`);
        log.info(`  - Summary: ${JSON.stringify(visualResult.summary)}`);

        if (visualResult.results.length > 0) {
            const result = visualResult.results[0];
            log.success(`  - Provider: ${result.provider}`);
            log.success(`  - HTML Length: ${result.htmlLength} chars`);
            log.success(`  - Attempts: ${result.attempt}`);
        }

        if (visualResult.errors.length > 0) {
            log.warn(`  - Errors:`);
            visualResult.errors.forEach(err => log.warn(`    - ${err}`));
        }

        // =======================================================================
        // Step 6: 最终报告
        // =======================================================================
        log.info('[6/6] 生成最终报告...');

        const report = {
            testVersion: 'V85.980',
            targetHash: CONFIG.targetHash,
            timestamp: new Date().toISOString(),

            patchA: {
                name: '激活折叠内容',
                success: expandResult.success,
                expandedCount: expandResult.expandedCount
            },

            pinnacleFound: pinnacleFound.found,

            patchBC: {
                name: '视觉取证 (B: Click Fallback + C: Logo Path)',
                success: visualResult.success,
                processedCount: visualResult.processedCount,
                htmlLength: visualResult.results.length > 0 ? visualResult.results[0].htmlLength : 0
            },

            readyForMassHarvest: expandResult.success && pinnacleFound.found && visualResult.success
        };

        log.success('=== V85.980 Matrix Force-Unlock Test COMPLETE ===');
        console.log('\n' + '='.repeat(60));
        console.log('[V85.980] Matrix Force-Unlock COMPLETE');
        console.log('='.repeat(60));
        console.log(`Pinnacle Found: ${report.pinnacleFound ? 'YES ✓' : 'NO ✗'}`);
        console.log(`Popup Active: ${report.patchBC.success ? 'YES ✓' : 'NO ✗'}`);
        console.log(`Ready for mass harvest: ${report.readyForMassHarvest ? 'YES ✓✓✓' : 'NO ✗✗✗'}`);
        console.log('='.repeat(60));

        // 保持浏览器打开 30 秒以便观察
        log.info('保持浏览器打开 30 秒以便观察...');
        await page.waitForTimeout(30000);

        return report;

    } catch (error) {
        log.error(`测试失败: ${error.message}`);
        throw error;
    } finally {
        if (page) await page.close().catch(() => {});
        if (context) await context.close().catch(() => {});
        if (browser) await browser.close().catch(() => {});
    }
}

/**
 * 检查 Pinnacle 是否存在于页面中
 */
async function checkPinnaclePresence(page) {
    const result = {
        logoTitle: false,
        logoSrc: false,
        logoAlt: false,
        rowElement: false,
        found: false
    };

    try {
        // 检查 img[title*="Pinnacle"]
        const titleElements = await page.$$('img[title*="Pinnacle" i]');
        result.logoTitle = titleElements.length > 0;

        // 检查 img[src*="pinnacle"]
        const srcElements = await page.$$('img[src*="pinnacle" i]');
        result.logoSrc = srcElements.length > 0;

        // 检查 img[alt*="Pinnacle"]
        const altElements = await page.$$('img[alt*="Pinnacle" i]');
        result.logoAlt = altElements.length > 0;

        // 检查行元素
        const rowElements = await page.$$('div.border-black-borders:has(img[title*="Pinnacle" i]), div.border-black-borders:has(img[src*="pinnacle" i])');
        result.rowElement = rowElements.length > 0;

        // 整体判定
        result.found = result.logoTitle || result.logoSrc || result.logoAlt || result.rowElement;

    } catch (e) {
        log.error(`Pinnacle 存在性检查失败: ${e.message}`);
    }

    return result;
}

// ============================================================================
// MAIN ENTRY
// ============================================================================

(async () => {
    try {
        await runMatrixForceUnlockTest();
        process.exit(0);
    } catch (error) {
        log.error(error.stack);
        process.exit(1);
    }
})();
