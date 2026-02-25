/**
 * V85.500 - 视觉采集逻辑单点爆破实测
 * ======================================
 *
 * 任务：验证 V85.000 视觉定位逻辑
 * 目标：Bayern Munich vs Augsburg (Match ID: 4221909)
 * 提供商：Pinnacle (Visual ID: 417 / Title: 'Pinnacle')
 *
 * 测试参数：
 * - headless: false (可视化验证)
 * - slowMo: 100 (慢速模式便于观察)
 * - URL: https://www.oddsportal.com/football/germany/bundesliga-2023-2024/bayern-munich-augsburg-f3e2PS0c/
 *
 * 关键指标：
 * 1. 定位成功率：日志是否输出 [PINNACLE] 找到行元素？
 * 2. 触发成功率：是否捕获到包含 h3:text("Odds movement") 的容器？
 * 3. 数据密度：最终生成的记录数是否 >= 2？
 *
 * @author Senior Node.js & Playwright Engineer
 * @version V85.500
 * @since 2026-01-25
 */

'use strict';

const path = require('path');
const { chromium } = require('playwright');
const logger = require('./modules/logger');
const interaction = require('./modules/interaction_v51');
const parser = require('./modules/parser_v51');

const log = logger.createLogger('v85_500_visual_strike');

// ============================================================================
// CONFIGURATION
// ============================================================================

const V85_500_CONFIG = {
    // 目标比赛信息
    target: {
        matchId: '4221909',
        match: 'Bayern Munich vs Augsburg',
        league: 'Bundesliga 2023/2024',
        providerKey: 'PINNACLE',
        providerName: 'Pinnacle',
        url: 'https://www.oddsportal.com/football/germany/bundesliga-2023-2024/bayern-munich-augsburg-f3e2PS0c/'
    },

    // 浏览器配置 (V85.700: headless 模式用于数据核验)
    browser: {
        headless: true,     // V85.700: headless 模式
        slowMo: 50,         // 快速模式
        timeout: 60000,     // 页面超时 60 秒
        viewport: { width: 1920, height: 1080 }
    },

    // 视觉取证配置
    capture: {
        hoverWaitMin: 2000,
        hoverWaitMax: 5000,
        maxRetries: 2,
        enableRetry: true
    },

    // 验收标准
    acceptance: {
        minRecords: 2,              // 最小时序记录数
        requiresAnchor: true,       // 必需包含 "Odds movement" 锚点
        requiresOpeningOdds: false  // 开盘赔率为可选（单值模式）
    }
};

// ============================================================================
// TEST EXECUTION
// ============================================================================

/**
 * V85.500: 执行视觉采集单点爆破测试
 *
 * @returns {Promise<Object>} - 测试结果对象
 */
async function executeVisualStrikeTest() {
    log.info('╔════════════════════════════════════════════════════════════╗');
    log.info('║     V85.500 - 视觉采集逻辑单点爆破实测                    ║');
    log.info('╚════════════════════════════════════════════════════════════╝');
    log.info('');
    log.info(`目标比赛: ${V85_500_CONFIG.target.match}`);
    log.info(`比赛ID: ${V85_500_CONFIG.target.matchId}`);
    log.info(`目标提供商: ${V85_500_CONFIG.target.providerName} (${V85_500_CONFIG.target.providerKey})`);
    log.info(`测试URL: ${V85_500_CONFIG.target.url}`);
    log.info('');
    log.info('测试参数:');
    log.info(`  - headless: ${V85_500_CONFIG.browser.headless} (可视化验证)`);
    log.info(`  - slowMo: ${V85_500_CONFIG.browser.slowMo}ms`);
    log.info('');

    const result = {
        success: false,
        phase: 'INIT',
        metrics: {
            locationSuccess: false,
            triggerSuccess: false,
            htmlCaptured: false,
            recordsExtracted: 0,
            dataDensity: 0
        },
        captured: {
            htmlLength: 0,
            htmlPreview: '',
            timestamps: [],
            records: []
        },
        errors: []
    };

    let browser = null;
    let context = null;
    let page = null;

    try {
        // ====================================================================
        // PHASE 1: 浏览器初始化
        // ====================================================================
        result.phase = 'BROWSER_INIT';
        log.info('[PHASE 1] 浏览器初始化...');

        browser = await chromium.launch({
            headless: V85_500_CONFIG.browser.headless,
            slowMo: V85_500_CONFIG.browser.slowMo
        });

        context = await browser.newContext({
            viewport: V85_500_CONFIG.browser.viewport,
            userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        });

        page = await context.newPage();
        page.setDefaultTimeout(V85_500_CONFIG.browser.timeout);

        log.success('[PHASE 1] ✓ 浏览器初始化成功');

        // ====================================================================
        // PHASE 2: 导航到目标页面
        // ====================================================================
        result.phase = 'NAVIGATION';
        log.info('[PHASE 2] 导航到目标页面...');

        await page.goto(V85_500_CONFIG.target.url, {
            waitUntil: 'networkidle'
        });

        // 等待页面稳定
        await page.waitForTimeout(3000);

        log.success('[PHASE 2] ✓ 页面加载完成');
        log.debug('[PHASE 2] 等待 3 秒让页面稳定...');

        // ====================================================================
        // PHASE 3: 定位提供商行 (关键指标 1)
        // ====================================================================
        result.phase = 'LOCATION';
        log.info('[PHASE 3] 定位提供商行...');

        log.info(`正在查找提供商: ${V85_500_CONFIG.target.providerKey}`);
        log.info('请在浏览器窗口中观察鼠标是否移动到 Pinnacle Logo 所在的行...');

        // 使用 V85.000 视觉取证逻辑
        const captureResult = await interaction.captureSingleProviderVisually(
            page,
            V85_500_CONFIG.target.providerKey
        );

        if (!captureResult.success) {
            result.errors.push(`定位失败: ${captureResult.error}`);
            log.error(`[PHASE 3] ✗ 定位失败: ${captureResult.error}`);
            result.metrics.locationSuccess = false;
            return result;
        }

        result.metrics.locationSuccess = true;
        log.success(`[PHASE 3] ✓ 定位成功: 找到 ${captureResult.provider} 行元素`);

        // ====================================================================
        // PHASE 4: 触发并捕获弹窗 HTML (关键指标 2)
        // ====================================================================
        result.phase = 'CAPTURE';
        log.info('[PHASE 4] 验证捕获的 HTML...');

        const modalHTML = captureResult.html;
        result.captured.htmlLength = modalHTML.length;
        result.captured.htmlPreview = modalHTML.substring(0, 200);

        // 验证必需锚点
        const hasAnchor = modalHTML.includes('Odds movement');
        const hasOpeningOdds = modalHTML.includes('Opening odds');
        const hasTimePattern = modalHTML.match(/\d{1,2}\s+\w+\.?\s*,?\s*\d{1,2}:\d{2}/);

        result.metrics.triggerSuccess = hasAnchor;
        result.captured.htmlCaptured = true;

        log.info(`HTML 长度: ${modalHTML.length} 字符`);
        log.info(`必需锚点 "Odds movement": ${hasAnchor ? '✓' : '✗'}`);
        log.info(`开盘赔率标签: ${hasOpeningOdds ? '✓' : '✗'}`);
        log.info(`时间模式匹配: ${hasTimePattern ? '✓' : '✗'}`);

        // 显示 HTML 核心片段
        log.info('');
        log.info('═══════════════════════════════════════════════════════');
        log.info('弹窗 HTML 核心片段 (前 200 字符):');
        log.info('═══════════════════════════════════════════════════════');
        log.info(result.captured.htmlPreview);
        log.info('═══════════════════════════════════════════════════════');
        log.info('');

        if (!hasAnchor) {
            result.errors.push('捕获的 HTML 缺少必需锚点 "Odds movement"');
            log.error('[PHASE 4] ✗ HTML 验证失败: 缺少必需锚点');
            return result;
        }

        log.success('[PHASE 4] ✓ HTML 验证通过');

        // ====================================================================
        // PHASE 5: 解析时序数据 (关键指标 3)
        // ====================================================================
        result.phase = 'PARSING';
        log.info('[PHASE 5] 解析时序数据...');

        const records = parser.parseModalHtml(
            modalHTML,
            V85_500_CONFIG.target.providerName
        );

        result.captured.records = records;
        result.metrics.recordsExtracted = records.length;
        result.metrics.dataDensity = records.length;

        log.info(`解析结果: ${records.length} 条时序记录`);

        if (records.length > 0) {
            log.success('[PHASE 5] ✓ 解析成功');

            // ====================================================================
            // V85.700: 完整 JSON Dump (动作 A - 全量 Dump)
            // ====================================================================
            log.info('');
            log.info('╔════════════════════════════════════════════════════════════╗');
            log.info('║     [V85.700] 完整时序记录 JSON Dump                       ║');
            log.info('╚════════════════════════════════════════════════════════════╝');
            log.info('');

            // 输出完整 JSON
            console.log(JSON.stringify(records, null, 2));

            log.info('');
            log.info('═══════════════════════════════════════════════════════');
            log.info('时序记录摘要:');
            log.info('═══════════════════════════════════════════════════════');

            records.forEach((record, idx) => {
                log.info(`记录 #${idx + 1}:`);
                log.info(`  - 时间戳: ${record.timestamp}`);
                log.info(`  - 主胜赔率: ${record.home_odd}`);
                log.info(`  - 类型: ${record.metric_type}`);
                if (record.draw_odd !== null) {
                    log.info(`  - 平局赔率: ${record.draw_odd}`);
                    log.info(`  - 客胜赔率: ${record.away_odd}`);
                    log.info(`  - 返还率: ${record.payout}`);
                }
                if (record.dual_point_sampling && record.dual_point_sampling.initial) {
                    log.info(`  - 开盘赔率: ${record.dual_point_sampling.initial}`);
                    log.info(`  - 当前赔率: ${record.dual_point_sampling.current}`);
                    log.info(`  - 变动值: ${record.dual_point_sampling.delta}`);
                }
            });

            log.info('═══════════════════════════════════════════════════════');
            log.info('');

            // ====================================================================
            // V85.700: 字段核验清单 (动作 B & C)
            // ====================================================================
            log.info('╔════════════════════════════════════════════════════════════╗');
            log.info('║     [V85.700] 字段核验清单                                ║');
            log.info('╚════════════════════════════════════════════════════════════╝');
            log.info('');

            // 动作 B: 时间校准审计
            const yearCheck = records.some(r => r.timestamp && r.timestamp.includes('2026'));
            log.info(`[时间校准审计] 年份补全 (2026): ${yearCheck ? '✓ PASS' : '✗ FAIL'}`);
            log.info(`  首条时间戳: ${records[0].timestamp}`);
            log.info(`  末条时间戳: ${records[records.length - 1].timestamp}`);

            // 动作 C: 初盘发现
            const openingFound = records.some(r => r.dual_point_sampling && r.dual_point_sampling.initial !== null);
            log.info(`[初盘发现] Opening odds: ${openingFound ? '✓ PASS' : '✗ FAIL'}`);
            if (openingFound) {
                const openingRecord = records.find(r => r.dual_point_sampling && r.dual_point_sampling.initial !== null);
                log.info(`  开盘值: ${openingRecord.dual_point_sampling.initial}`);
            }

            // 时序密度
            log.info(`[时序密度] 记录总数: ${records.length}`);
            log.info(`  中间跳动: ${records.length > 2 ? records.length - 2 : 0} 条`);

            // 数值精度
            const numericCheck = records.every(r => typeof r.home_odd === 'number');
            log.info(`[数值精度] Float 类型: ${numericCheck ? '✓ PASS' : '✗ FAIL'}`);

            log.info('');
            log.info('═══════════════════════════════════════════════════════');
            log.info('');

            // 验证数据密度
            if (records.length < V85_500_CONFIG.acceptance.minRecords) {
                result.errors.push(
                    `数据密度不足: 需要 ${V85_500_CONFIG.acceptance.minRecords} 条记录，实际获得 ${records.length} 条`
                );
                log.warn(`[PHASE 5] ⚠ 数据密度不足: ${records.length} < ${V85_500_CONFIG.acceptance.minRecords}`);
            } else {
                log.success(`[PHASE 5] ✓ 数据密度合格: ${records.length} >= ${V85_500_CONFIG.acceptance.minRecords}`);
            }
        } else {
            result.errors.push('解析失败: 未提取到任何时序记录');
            log.error('[PHASE 5] ✗ 解析失败: 无记录');
            return result;
        }

        // ====================================================================
        // PHASE 6: 最终验收
        // ====================================================================
        result.phase = 'ACCEPTANCE';
        log.info('[PHASE 6] 最终验收...');

        const acceptanceCriteria = [
            { name: '定位成功', passed: result.metrics.locationSuccess },
            { name: '触发成功', passed: result.metrics.triggerSuccess },
            { name: '数据密度', passed: result.metrics.recordsExtracted >= V85_500_CONFIG.acceptance.minRecords }
        ];

        const allPassed = acceptanceCriteria.every(c => c.passed);
        result.success = allPassed;

        log.info('');
        log.info('╔════════════════════════════════════════════════════════════╗');
        log.info('║                    验收结果                                 ║');
        log.info('╠════════════════════════════════════════════════════════════╣');

        acceptanceCriteria.forEach(c => {
            const status = c.passed ? '✓ PASS' : '✗ FAIL';
            const padding = ' '.repeat(10 - c.name.length);
            log.info(`║ ${c.name}:${padding}${status}                               ║`);
        });

        log.info('╠════════════════════════════════════════════════════════════╣');
        log.info(`║ 总体结果: ${allPassed ? '✓ SUCCESS' : '✗ FAILURE'}                                 ║`);
        log.info('╚════════════════════════════════════════════════════════════╝');
        log.info('');

    } catch (error) {
        result.errors.push(`执行异常: ${error.message}`);
        log.error(`[${result.phase}] ✗ 执行异常: ${error.message}`);
        log.error(error.stack);
        result.success = false;

    } finally {
        // ====================================================================
        // CLEANUP: 保持浏览器打开以便观察
        // ====================================================================
        if (page) {
            log.info('');
            log.info('═══════════════════════════════════════════════════════');
            log.info('浏览器窗口保持打开，请观察视觉效果');
            log.info('按 Ctrl+C 退出...');
            log.info('═══════════════════════════════════════════════════════');

            // 保持浏览器打开 60 秒供观察
            await page.waitForTimeout(60000);
        }

        if (context) {
            await context.close();
        }
        if (browser) {
            await browser.close();
        }
    }

    return result;
}

// ============================================================================
// REPORT GENERATION
// ============================================================================

/**
 * V85.500: 生成测试报告
 *
 * @param {Object} result - 测试结果对象
 */
function generateTestReport(result) {
    log.info('');
    log.info('╔════════════════════════════════════════════════════════════╗');
    log.info('║           [V85.500] Visual Strike Test Report              ║');
    log.info('╚════════════════════════════════════════════════════════════╝');
    log.info('');

    // 基本信息
    log.info('【基本信息】');
    log.info(`  比赛ID: ${V85_500_CONFIG.target.matchId}`);
    log.info(`  比赛: ${V85_500_CONFIG.target.match}`);
    log.info(`  联赛: ${V85_500_CONFIG.target.league}`);
    log.info(`  提供商: ${V85_500_CONFIG.target.providerName}`);
    log.info(`  测试时间: ${new Date().toISOString()}`);
    log.info('');

    // 关键指标
    log.info('【关键指标】');
    log.info(`  1. 定位成功率: ${result.metrics.locationSuccess ? 'YES ✓' : 'NO ✗'}`);
    log.info(`  2. 触发成功率: ${result.metrics.triggerSuccess ? 'YES ✓' : 'NO ✗'}`);
    log.info(`  3. 数据密度: ${result.metrics.recordsExtracted} 条记录`);
    log.info('');

    // HTML 取证
    log.info('【HTML 取证】');
    log.info(`  HTML 长度: ${result.captured.htmlLength} 字符`);
    log.info(`  核心片段 (前 200 字符):`);
    log.info(`    ${result.captured.htmlPreview.substring(0, 100)}...`);
    log.info('');

    // 解析结果
    log.info('【解析结果】');
    log.info(`  时序记录数: ${result.metrics.recordsExtracted}`);
    if (result.captured.records.length > 0) {
        log.info(`  首条记录时间戳: ${result.captured.records[0].timestamp}`);
        log.info(`  末条记录时间戳: ${result.captured.records[result.captured.records.length - 1].timestamp}`);
    }
    log.info('');

    // 最终结论
    const bulkReady = result.success && result.metrics.recordsExtracted >= 2;
    log.info('【最终结论】');
    log.info(`  [V85.500] Visual Strike SUCCESS: ${result.success ? 'YES' : 'NO'}`);
    log.info(`  Records Count: ${result.metrics.recordsExtracted}`);
    log.info(`  Density: ${result.metrics.dataDensity}`);
    log.info(`  READY for bulk run?: ${bulkReady ? 'YES ✓' : 'NO ✗'}`);
    log.info('');

    // 错误列表
    if (result.errors.length > 0) {
        log.info('【错误列表】');
        result.errors.forEach((err, idx) => {
            log.info(`  ${idx + 1}. ${err}`);
        });
        log.info('');
    }
}

// ============================================================================
// MAIN ENTRY
// ============================================================================

async function main() {
    try {
        const result = await executeVisualStrikeTest();
        generateTestReport(result);

        // 返回退出码
        process.exit(result.success ? 0 : 1);

    } catch (error) {
        log.error(`FATAL: ${error.message}`);
        log.error(error.stack);
        process.exit(2);
    }
}

// 如果直接运行此脚本
if (require.main === module) {
    main();
}

module.exports = {
    executeVisualStrikeTest,
    generateTestReport,
    V85_500_CONFIG
};
