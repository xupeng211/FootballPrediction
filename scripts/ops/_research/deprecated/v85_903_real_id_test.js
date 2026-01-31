/**
 * V85.970 - 视觉收割链路故障深度取证 (Diagnostic Strike)
 * ===============================================================
 *
 * 任务：诊断 V85.903 全线失败的根本原因
 * 目标：通过屏幕截图、遮罩层探测和源码快照识别阻塞因素
 *
 * V85.970 诊断增强：
 *   - 动作 A (屏幕截图): 在关键步骤前后捕获页面状态
 *   - 动作 B (遮罩层探测): 自动检测并关闭 Cookie/Consent 弹窗
 *   - 动作 C (源码快照): 失败时保存完整 DOM 源码
 *
 * 目标样本：
 * - SrOgIMxA - Brentford vs Leicester (Premier League 2024/2025)
 *
 * 测试参数：
 * - 环境：headless: false (可视化取证)
 * - 单样本：仅执行第一个失败样本
 * - 输出：logs/diag_*.png + logs/diag_source.html
 *
 * @author Senior Automation Diagnostic Engineer
 * @version V85.970
 * @since 2026-01-26
 */

'use strict';

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const logger = require('./modules/logger');
const interaction = require('./modules/interaction_v51');
const parser = require('./modules/parser_v51');

const log = logger.createLogger('v85_970_diagnostic');

// ============================================================================
// CONFIGURATION
// ============================================================================

// 诊断目标样本（第一个失败样本）
const DIAGNOSTIC_TARGET = {
    hash: 'SrOgIMxA',
    url: 'https://www.oddsportal.com/football/england/premier-league-2024-2025/brentford-leicester-SrOgIMxA/',
    league: 'Premier League',
    season: '2024/2025',
    home: 'Brentford',
    away: 'Leicester City'
};

const V85_970_CONFIG = {
    // 浏览器配置（headless: false 用于可视化取证）
    browser: {
        headless: false,  // V85.970: 设为 false 以可视化取证
        slowMo: 100,     // V85.970: 减慢执行以便观察
        timeout: 60000,
        viewport: { width: 1920, height: 1080 }
    },

    // 目标提供商 (按优先级排序)
    targetProviders: ['PINNACLE', 'BET365', 'BWIN', 'WILLIAM_HILL', 'ONEXBET'],

    // 视觉取证配置
    capture: {
        hoverWaitMin: 2000,
        hoverWaitMax: 5000,
        maxRetries: 2,
        enableRetry: true
    },

    // 诊断输出目录
    diagDir: 'logs'
};

// ============================================================================
// V85.970: 诊断取证函数
// ============================================================================

/**
 * V85.970 动作 A - 屏幕截图取证
 * @param {Page} page - Playwright 页面对象
 * @param {string} suffix - 文件名后缀
 */
async function captureScreenshot(page, suffix = 'error') {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `diag_${suffix}_${timestamp}.png`;
    const filepath = path.join(V85_970_CONFIG.diagDir, filename);

    try {
        await page.screenshot({ path: filepath, fullPage: true });
        log.info(`[DIAG A] ✓ Screenshot saved: ${filepath}`);
        return filepath;
    } catch (error) {
        log.error(`[DIAG A] ✗ Screenshot failed: ${error.message}`);
        return null;
    }
}

/**
 * V85.970 动作 B - 遮罩层探测与关闭
 * @param {Page} page - Playwright 页面对象
 * @returns {Object} - { detected: boolean, dismissed: boolean, details: string }
 */
async function detectAndDismissCookieModal(page) {
    const result = {
        detected: false,
        dismissed: false,
        details: 'No modal detected'
    };

    // Cookie 遮罩层选择器列表
    const cookieSelectors = [
        // 常见 Cookie 弹窗选择器
        'div[class*="cookie"]',
        'div[id*="cookie"]',
        'div[class*="consent"]',
        'div[id*="consent"]',
        'div[class*="banner"]',

        // Accept/Agree 按钮
        'button:has-text("Accept")',
        'button:has-text("Accept All")',
        'button:has-text("Agree")',
        'button:has-text("I Agree")',
        'button:has-text("Got it")',
        'button:has-text("OK")',

        // 关闭按钮 X
        'button[aria-label="Close"]',
        'button[aria-label="close"]',
        '.close',
        '.cookie-close',

        // OddsPortal 特定
        '#onetrust-consent-sdk',
        '.ot-sdk-container'
    ];

    log.info('[DIAG B] Scanning for cookie/consent modals...');

    for (const selector of cookieSelectors) {
        try {
            const element = await page.$(selector);
            if (element) {
                const isVisible = await element.isVisible();
                if (isVisible) {
                    result.detected = true;
                    result.details = `Modal found: ${selector}`;
                    log.warn(`[DIAG B] ⚠ Modal detected: ${selector}`);

                    // 尝试点击关闭
                    try {
                        await element.click({ timeout: 3000 });
                        result.dismissed = true;
                        log.success(`[DIAG B] ✓ Modal dismissed: ${selector}`);

                        // 等待动画完成
                        await page.waitForTimeout(1000);
                        break;
                    } catch (clickError) {
                        log.error(`[DIAG B] ✗ Failed to dismiss modal: ${clickError.message}`);

                        // 尝试按 ESC 键关闭
                        try {
                            await page.keyboard.press('Escape');
                            result.dismissed = true;
                            log.success('[DIAG B] ✓ Modal dismissed via ESC');
                            await page.waitForTimeout(1000);
                            break;
                        } catch (escError) {
                            log.error(`[DIAG B] ✗ ESC also failed: ${escError.message}`);
                        }
                    }
                }
            }
        } catch (error) {
            // 选择器无效，继续尝试下一个
            continue;
        }
    }

    if (!result.detected) {
        log.info('[DIAG B] ✓ No cookie/consent modal detected');
    }

    return result;
}

/**
 * V85.970 动作 C - 源码快照
 * @param {Page} page - Playwright 页面对象
 * @param {string} suffix - 文件名后缀
 */
async function captureSourceSnapshot(page, suffix = 'error') {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `diag_source_${suffix}_${timestamp}.html`;
    const filepath = path.join(V85_970_CONFIG.diagDir, filename);

    try {
        const html = await page.content();
        fs.writeFileSync(filepath, html, 'utf8');
        log.info(`[DIAG C] ✓ Source snapshot saved: ${filepath} (${html.length} bytes)`);
        return filepath;
    } catch (error) {
        log.error(`[DIAG C] ✗ Source snapshot failed: ${error.message}`);
        return null;
    }
}

/**
 * V85.970 - DOM 结构审计
 * @param {Page} page - Playwright 页面对象
 * @returns {Object} - DOM 审计结果
 */
async function auditDomStructure(page) {
    const audit = {
        url: page.url(),
        title: await page.title(),
        hasBorderBlackBorders: false,
        borderCount: 0,
        hasPinnacleLogo: false,
        hasBet365Logo: false,
        bodyTextLength: 0,
        hasTables: false,
        tableCount: 0,
        hasOddsElements: false
    };

    try {
        // 检查 div.border-black-borders 容器
        const borderElements = await page.$$('div.border-black-borders');
        audit.borderCount = borderElements.length;
        audit.hasBorderBlackBorders = borderElements.length > 0;

        // 检查 Pinnacle Logo
        const pinnacleLogo = await page.$('img[title*="Pinnacle" i]');
        audit.hasPinnacleLogo = pinnacleLogo !== null;

        // 检查 bet365 Logo
        const bet365Logo = await page.$('img[title*="bet365" i]');
        audit.hasBet365Logo = bet365Logo !== null;

        // 检查页面文本长度
        const bodyText = await page.evaluate(() => document.body.innerText);
        audit.bodyTextLength = bodyText.length;

        // 检查表格
        const tables = await page.$$('table');
        audit.tableCount = tables.length;
        audit.hasTables = tables.length > 0;

        // 检查赔率元素（常见的赔率格式）
        const oddsElements = await page.$$('[class*="odd"]');
        audit.hasOddsElements = oddsElements.length > 0;

        log.info('[DOM AUDIT] Results:');
        log.info(`  - URL: ${audit.url}`);
        log.info(`  - Title: ${audit.title}`);
        log.info(`  - div.border-black-borders: ${audit.borderCount} (${audit.hasBorderBlackBorders ? 'FOUND' : 'NOT FOUND'})`);
        log.info(`  - Pinnacle Logo: ${audit.hasPinnacleLogo ? 'FOUND' : 'NOT FOUND'}`);
        log.info(`  - bet365 Logo: ${audit.hasBet365Logo ? 'FOUND' : 'NOT FOUND'}`);
        log.info(`  - Tables: ${audit.tableCount}`);
        log.info(`  - Body Text: ${audit.bodyTextLength} chars`);
        log.info(`  - Odds Elements: ${audit.hasOddsElements ? 'FOUND' : 'NOT FOUND'}`);

    } catch (error) {
        log.error(`[DOM AUDIT] ✗ Audit failed: ${error.message}`);
    }

    return audit;
}

/**
 * V85.970 - 综合诊断函数
 * @param {Page} page - Playwright 页面对象
 * @param {string} stage - 诊断阶段标识
 */
async function runDiagnostics(page, stage = 'general') {
    log.info(`\n${'='.repeat(70)}`);
    log.info(`[V85.970] DIAGNOSTIC STRIKE - Stage: ${stage}`);
    log.info(`${'='.repeat(70)}`);

    const results = {
        stage,
        timestamp: new Date().toISOString(),
        screenshot: null,
        modal: null,
        sourceSnapshot: null,
        domAudit: null
    };

    // 动作 A: 屏幕截图
    log.info('\n--- [DIAG A] SCREENSHOT ---');
    results.screenshot = await captureScreenshot(page, stage);

    // 动作 B: 遮罩层探测
    log.info('\n--- [DIAG B] COOKIE MODAL DETECTION ---');
    results.modal = await detectAndDismissCookieModal(page);

    // 如果遮罩层被关闭，再次截图
    if (results.modal.dismissed) {
        log.info('[DIAG B] Modal dismissed, capturing updated screenshot...');
        await captureScreenshot(page, `${stage}_post_dismiss`);
    }

    // 动作 C: DOM 结构审计
    log.info('\n--- [DOM AUDIT] ---');
    results.domAudit = await auditDomStructure(page);

    // 动作 C: 源码快照（仅在某些阶段）
    if (stage === 'error' || stage === 'final') {
        log.info('\n--- [DIAG C] SOURCE SNAPSHOT ---');
        results.sourceSnapshot = await captureSourceSnapshot(page, stage);
    }

    log.info(`\n${'='.repeat(70)}`);
    log.info('[V85.970] DIAGNOSTIC COMPLETE');
    log.info(`${'='.repeat(70)}\n`);

    return results;
}

// ============================================================================
// DATA MODELS
// ============================================================================

/**
 * V85.970: 诊断测试结果
 */
class DiagnosticTestResult {
    constructor(sample) {
        this.hash = sample.hash;
        this.url = sample.url;
        this.league = sample.league;
        this.season = sample.season;
        this.home = sample.home;
        this.away = sample.away;
        this.startTime = Date.now();
        this.endTime = null;
        this.elapsed = 0;

        // 诊断结果
        this.diagnostics = {
            initial: null,
            postModal: null,
            error: null
        };

        // 测试结果
        this.nodeCapture = false;
        this.tooltipSuccess = false;
        this.parsingSuccess = false;
        this.recordsCount = 0;
        this.year2026 = false;

        // 错误信息
        this.error = null;
        this.errorMessage = null;

        // 根本原因分析
        this.rootCause = {
            blockDetected: false,
            urlValid: false,
            domStructureValid: false,
            details: ''
        };
    }

    finish() {
        this.endTime = Date.now();
        this.elapsed = (this.endTime - this.startTime) / 1000;
    }
}

// ============================================================================
// TEST EXECUTION
// ============================================================================

/**
 * V85.970: 执行诊断测试（仅第一个失败样本）
 */
async function executeDiagnosticTest() {
    log.info('╔════════════════════════════════════════════════════════════╗');
    log.info('║     V85.970 - 视觉收割链路故障深度取证                 ║');
    log.info('╚════════════════════════════════════════════════════════════╝');
    log.info('');
    log.info(`[TARGET] Hash: ${DIAGNOSTIC_TARGET.hash}`);
    log.info(`[MATCH] ${DIAGNOSTIC_TARGET.home} vs ${DIAGNOSTIC_TARGET.away}`);
    log.info(`[URL] ${DIAGNOSTIC_TARGET.url}`);
    log.info(`[MODE] headless: ${V85_970_CONFIG.browser.headless} (可视化取证)`);
    log.info('');

    const result = new DiagnosticTestResult(DIAGNOSTIC_TARGET);
    let browser = null;
    let context = null;
    let page = null;

    // 确保诊断目录存在
    if (!fs.existsSync(V85_970_CONFIG.diagDir)) {
        fs.mkdirSync(V85_970_CONFIG.diagDir, { recursive: true });
    }

    try {
        log.info('[INIT] Initializing browser...');
        browser = await chromium.launch({
            headless: V85_970_CONFIG.browser.headless,
            slowMo: V85_970_CONFIG.browser.slowMo
        });

        context = await browser.newContext({
            viewport: V85_970_CONFIG.browser.viewport,
            userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        });

        page = await context.newPage();
        page.setDefaultTimeout(V85_970_CONFIG.browser.timeout);

        log.success('[INIT] ✓ Browser ready');
        log.info('');

        // === 阶段 1: 导航到页面 ===
        log.info(`[STEP 1] Navigating to: ${DIAGNOSTIC_TARGET.url}`);
        await page.goto(DIAGNOSTIC_TARGET.url, { waitUntil: 'networkidle', timeout: 30000 });
        await page.waitForTimeout(3000);

        // === 阶段 2: 初始诊断 ===
        result.diagnostics.initial = await runDiagnostics(page, 'initial');

        // === 阶段 3: 遮罩层处理后的诊断 ===
        if (result.diagnostics.initial.modal.detected) {
            log.info('[STEP 2] Modal was detected and handled, running post-modal diagnostics...');
            result.diagnostics.postModal = await runDiagnostics(page, 'post_modal');
        }

        // === 阶段 4: 检查 URL 有效性 ===
        log.info('\n[STEP 3] Checking URL validity...');
        const statusCode = await page.evaluate(() => {
            // 检查页面是否有 404 或错误指示
            const title = document.title.toLowerCase();
            const body = document.body.innerText.toLowerCase();
            return {
                has404: title.includes('404') || title.includes('not found') || body.includes('404') || body.includes('not found'),
                title: document.title,
                bodyLength: document.body.innerText.length
            };
        });

        result.rootCause.urlValid = !statusCode.has404 && statusCode.bodyLength > 1000;
        log.info(`  - URL Valid: ${result.rootCause.urlValid ? 'YES' : 'NO'}`);
        log.info(`  - Page Title: ${statusCode.title}`);
        log.info(`  - Body Length: ${statusCode.bodyLength} chars`);

        // === 阶段 5: 检查 DOM 结构 ===
        log.info('\n[STEP 4] Checking DOM structure...');
        const domAudit = result.diagnostics.postModal || result.diagnostics.initial;
        result.rootCause.domStructureValid = domAudit.domAudit.hasBorderBlackBorders;
        log.info(`  - div.border-black-borders: ${result.rootCause.domStructureValid ? 'FOUND ✓' : 'NOT FOUND ✗'}`);
        log.info(`  - Pinnacle Logo: ${domAudit.domAudit.hasPinnacleLogo ? 'FOUND ✓' : 'NOT FOUND ✗'}`);
        log.info(`  - bet365 Logo: ${domAudit.domAudit.hasBet365Logo ? 'FOUND ✓' : 'NOT FOUND ✗'}`);

        // === 阶段 6: 尝试视觉取证 ===
        log.info('\n[STEP 5] Attempting visual capture...');
        try {
            const captureResult = await interaction.captureOddsMovementVisually(page, {
                maxProviders: 5,
                ...V85_970_CONFIG.capture
            });

            if (captureResult.success && captureResult.results.length > 0) {
                result.nodeCapture = true;
                result.tooltipSuccess = true;
                log.success(`[STEP 5] ✓ Visual Capture SUCCESS: ${captureResult.results.length} providers`);

                // 解析结果
                const firstResult = captureResult.results[0];
                try {
                    const records = parser.parseModalHtml(firstResult.html, firstResult.providerName);
                    result.recordsCount = records.length;

                    if (records.length > 0) {
                        result.parsingSuccess = true;
                        result.year2026 = records.some(r => r.timestamp && r.timestamp.includes('2026'));
                        log.success(`[STEP 6] ✓ Parsing SUCCESS: ${records.length} records`);
                    }
                } catch (parseError) {
                    log.error(`[STEP 6] ✗ Parsing ERROR: ${parseError.message}`);
                }
            } else {
                result.error = 'VISUAL_CAPTURE_FAILED';
                result.errorMessage = captureResult.errors.join('; ') || 'No providers captured';
                log.warn(`[STEP 5] ✗ Visual Capture FAIL: ${result.errorMessage}`);

                // 错误诊断
                result.diagnostics.error = await runDiagnostics(page, 'error');
            }
        } catch (captureError) {
            result.error = 'CAPTURE_EXCEPTION';
            result.errorMessage = captureError.message;
            log.error(`[STEP 5] ✗ Capture EXCEPTION: ${captureError.message}`);

            // 错误诊断
            result.diagnostics.error = await runDiagnostics(page, 'error');
        }

    } catch (error) {
        result.error = 'EXECUTION_ERROR';
        result.errorMessage = error.message;
        log.error(`[FATAL] ✗ EXCEPTION: ${error.message}`);
        log.error(error.stack);

        // 尝试在异常情况下也捕获诊断信息
        if (page) {
            try {
                result.diagnostics.error = await runDiagnostics(page, 'fatal_error');
            } catch (diagError) {
                log.error(`[DIAG] ✗ Failed to capture diagnostics: ${diagError.message}`);
            }
        }
    } finally {
        result.finish();

        // 最终诊断（如果还没有）
        if (!result.diagnostics.error && page) {
            result.diagnostics.error = await runDiagnostics(page, 'final');
        }

        if (page) {
            await page.close();
        }
        if (context) {
            await context.close();
        }
        if (browser) {
            await browser.close();
        }

        log.info(`\n[RESULT] Elapsed: ${result.elapsed.toFixed(2)}s`);
        log.info(`[RESULT] Node: ${result.nodeCapture ? '✓' : '✗'} | Tooltip: ${result.tooltipSuccess ? '✓' : '✗'} | Parse: ${result.parsingSuccess ? '✓' : '✗'} | Records: ${result.recordsCount}`);
    }

    // === 生成诊断报告 ===
    generateDiagnosticReport(result);

    return result;
}

/**
 * V85.970: 生成诊断报告
 */
function generateDiagnosticReport(result) {
    log.info('');
    log.info('╔════════════════════════════════════════════════════════════╗');
    log.info('║           [V85.970] DIAGNOSTIC REPORT                       ║');
    log.info('╠════════════════════════════════════════════════════════════╣');

    // 基本信息
    log.info(`║  Target Hash: ${result.hash}`);
    log.info(`║  Match: ${result.home} vs ${result.away}`);
    log.info(`║  Elapsed: ${result.elapsed.toFixed(2)}s`);
    log.info(`╠════════════════════════════════════════════════════════════╣`);

    // 根本原因分析
    const domAudit = result.diagnostics.postModal || result.diagnostics.initial;

    // 1. 是否被 Cookie 弹窗遮挡
    const modalDetected = domAudit.modal.detected;
    log.info(`║  1. Block Detected (Cookie Modal): ${modalDetected ? 'YES ✗' : 'NO ✓'}`);

    // 2. URL 是否有效
    log.info(`║  2. URL Valid (Not 404): ${result.rootCause.urlValid ? 'YES ✓' : 'NO ✗'}`);

    // 3. DOM 结构是否有效
    log.info(`║  3. DOM Structure (div.border-black-borders): ${result.rootCause.domStructureValid ? 'FOUND ✓' : 'NOT FOUND ✗'}`);

    log.info(`╠════════════════════════════════════════════════════════════╣`);

    // 详细诊断结果
    if (domAudit.domAudit) {
        log.info(`║  DOM Audit Details:`);
        log.info(`║    - Page Title: ${domAudit.domAudit.title}`);
        log.info(`║    - Border Containers: ${domAudit.domAudit.borderCount}`);
        log.info(`║    - Pinnacle Logo: ${domAudit.domAudit.hasPinnacleLogo ? 'FOUND' : 'NOT FOUND'}`);
        log.info(`║    - bet365 Logo: ${domAudit.domAudit.hasBet365Logo ? 'FOUND' : 'NOT FOUND'}`);
        log.info(`║    - Tables: ${domAudit.domAudit.tableCount}`);
        log.info(`║    - Body Text: ${domAudit.domAudit.bodyTextLength} chars`);
    }

    log.info(`╠════════════════════════════════════════════════════════════╣`);

    // 证据文件
    log.info(`║  Evidence Files:`);
    if (domAudit.screenshot) {
        log.info(`║    - Screenshot: ${domAudit.screenshot}`);
    }
    if (domAudit.sourceSnapshot) {
        log.info(`║    - Source: ${domAudit.sourceSnapshot}`);
    }
    if (result.diagnostics.postModal && result.diagnostics.postModal.screenshot) {
        log.info(`║    - Post-Modal Screenshot: ${result.diagnostics.postModal.screenshot}`);
    }

    log.info('╚════════════════════════════════════════════════════════════╝');
    log.info('');

    // === 控制台输出协议（用户要求的格式）===
    console.log('');
    console.log('═══════════════════════════════════════════════════════════════');
    console.log('[V85.970] Visual Diagnosis COMPLETE');
    console.log('═══════════════════════════════════════════════════════════════');

    // 根本原因
    let rootCauseDesc = [];
    if (modalDetected) {
        rootCauseDesc.push('Cookie modal detected');
    }
    if (!result.rootCause.urlValid) {
        rootCauseDesc.push('URL returns 404 or error page');
    }
    if (!result.rootCause.domStructureValid) {
        rootCauseDesc.push('div.border-black-borders container not found');
    }

    const rootCauseText = rootCauseDesc.length > 0
        ? rootCauseDesc.join('; ')
        : 'Unknown - need deeper investigation';

    const blockDetected = modalDetected ? 'YES' : 'NO';

    console.log(`Block detected: ${blockDetected}`);
    console.log(`Root Cause: ${rootCauseText}`);

    const readyForPatch = result.rootCause.urlValid && result.rootCause.domStructureValid;
    console.log(`Ready for patch: ${readyForPatch ? 'YES' : 'NO'}`);
    console.log(`═══════════════════════════════════════════════════════════════`);
    console.log('');
}

// ============================================================================
// MAIN ENTRY
// ============================================================================

async function main() {
    try {
        const result = await executeDiagnosticTest();
        const exitCode = result.nodeCapture ? 0 : 1;
        process.exit(exitCode);
    } catch (error) {
        log.error(`FATAL: ${error.message}`);
        log.error(error.stack);
        process.exit(2);
    }
}

if (require.main === module) {
    main();
}

module.exports = {
    executeDiagnosticTest,
    generateDiagnosticReport,
    V85_970_CONFIG,
    DIAGNOSTIC_TARGET,
    captureScreenshot,
    detectAndDismissCookieModal,
    captureSourceSnapshot,
    auditDomStructure,
    runDiagnostics
};
