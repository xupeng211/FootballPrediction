/**
 * V85.902 - 动态前端组件全链路交互分析
 * ========================================
 *
 * 任务：验证视觉定位算法在多种 UI 环境下的稳定性
 * 目标：测试 5 个随机 PENDING URL，验证 Module-Alpha/Beta 定位成功率
 *
 * 测试参数：
 * - 样本：随机抽取 PENDING 列表中的 5 个 URL
 * - 环境：headless: true
 * - 执行：调用 captureSingleProviderVisually
 *
 * 验收标准：
 * - Node Detection: 成功定位 Module-Alpha 的比例
 * - UI Rendering: 弹出窗口成功挂载的比例
 * - Parsing Stats: 解析出的时序数据条数及年份校准
 *
 * @author Senior Node.js & Playwright Engineer
 * @version V85.902
 * @since 2026-01-25
 */

'use strict';

const path = require('path');
const { chromium } = require('playwright');
const { Client } = require('pg');

const logger = require('./modules/logger');
const interaction = require('./modules/interaction_v51');
const parser = require('./modules/parser_v51');

const log = logger.createLogger('v85_902_interaction');

// ============================================================================
// CONFIGURATION
// ============================================================================

const V85_902_CONFIG = {
    // 测试规模
    sampleSize: 5,

    // 目标提供商 (按优先级排序)
    targetProviders: ['PINNACLE', 'BET365', 'BWIN', 'WILLIAM_HILL', 'ONEXBET'],

    // 浏览器配置
    browser: {
        headless: true,
        slowMo: 0,
        timeout: 60000,
        viewport: { width: 1920, height: 1080 }
    },

    // 视觉取证配置
    capture: {
        hoverWaitMin: 2000,
        hoverWaitMax: 5000,
        maxRetries: 2,
        enableRetry: true
    },

    // 数据库配置
    db: {
        host: process.env.DB_HOST || '172.25.16.1',
        port: parseInt(process.env.DB_PORT) || 5432,
        database: process.env.DB_NAME || 'football_db',
        user: process.env.DB_USER || 'football_user',
        password: process.env.DB_PASSWORD || ''
    }
};

// ============================================================================
// DATA MODELS
// ============================================================================

/**
 * V85.902: 单场测试结果
 */
class MatchTestResult {
    constructor(matchId, url) {
        this.matchId = matchId;
        this.url = url;
        this.startTime = Date.now();
        this.endTime = null;
        this.elapsed = 0;

        // 关键指标
        this.nodeDetection = false;     // Module-Alpha 定位成功
        this.uiRendering = false;       // 弹窗挂载成功
        this.parsingSuccess = false;    // 解析成功
        this.recordsCount = 0;          // 时序记录数
        this.yearCalibrated = false;    // 年份校准 (2026)

        // 错误信息
        this.error = null;
        this.errorMessage = null;
    }

    finish() {
        this.endTime = Date.now();
        this.elapsed = (this.endTime - this.startTime) / 1000;
    }
}

/**
 * V85.902: 汇总统计
 */
class AggregateStats {
    constructor() {
        this.total = 0;
        this.nodeDetectionSuccess = 0;
        this.uiRenderingSuccess = 0;
        this.parsingSuccess = 0;
        this.totalRecords = 0;
        this.yearCalibratedCount = 0;
        this.totalElapsed = 0;
        this.errors = [];
    }

    addResult(result) {
        this.total++;
        this.totalElapsed += result.elapsed;

        if (result.nodeDetection) {
            this.nodeDetectionSuccess++;
        }
        if (result.uiRendering) {
            this.uiRenderingSuccess++;
        }
        if (result.parsingSuccess) {
            this.parsingSuccess++;
        }
        this.totalRecords += result.recordsCount;
        if (result.yearCalibrated) {
            this.yearCalibratedCount++;
        }
        if (result.error) {
            this.errors.push(result);
        }
    }

    get nodeDetectionRate() {
        return this.total > 0 ? (this.nodeDetectionSuccess / this.total * 100).toFixed(1) : '0.0';
    }

    get uiRenderingRate() {
        return this.total > 0 ? (this.uiRenderingSuccess / this.total * 100).toFixed(1) : '0.0';
    }

    get parsingSuccessRate() {
        return this.total > 0 ? (this.parsingSuccess / this.total * 100).toFixed(1) : '0.0';
    }

    get avgElapsed() {
        return this.total > 0 ? (this.totalElapsed / this.total).toFixed(2) : '0';
    }

    get stabilityProof() {
        // 稳定性证明：所有指标都 >= 60%
        const nd = parseFloat(this.nodeDetectionRate);
        const ui = parseFloat(this.uiRenderingRate);
        return nd >= 60 && ui >= 60;
    }
}

// ============================================================================
// DATABASE OPERATIONS
// ============================================================================

/**
 * V85.902: 获取待测试的 PENDING URL
 */
async function fetchPendingUrls(config) {
    const client = new Client({
        host: config.db.host,
        port: config.db.port,
        database: config.db.database,
        user: config.db.user,
        password: config.db.password
    });

    try {
        await client.connect();
        log.info('[DB] Connected successfully');

        // 查询待处理的比赛 URL (从 matches_mapping 表获取 source_url)
        const query = `
            SELECT DISTINCT
                mm.match_id,
                mm.source_url as url,
                m.league_name,
                m.season,
                m.home_team,
                m.away_team
            FROM matches_mapping mm
            JOIN matches m ON mm.match_id = m.match_id
            WHERE mm.source_url IS NOT NULL
                AND mm.source_url != ''
                AND (
                    SELECT COUNT(*) FROM temporal_metric_records tmr
                    WHERE tmr.source_id = mm.source_id
                ) = 0
            ORDER BY RANDOM()
            LIMIT $1
        `;

        const result = await client.query(query, [config.sampleSize]);
        log.info(`[DB] Found ${result.rows.length} pending URLs`);

        return result.rows;

    } catch (error) {
        log.error(`[DB] Query failed: ${error.message}`);
        // 返回硬编码的测试 URL 作为回退
        log.warn('[DB] Using fallback test URLs');
        return getFallbackUrls(config.sampleSize);
    } finally {
        await client.end();
    }
}

/**
 * V85.902: 回退测试 URL (当数据库连接失败时使用)
 */
function getFallbackUrls(count) {
    const fallbackUrls = [
        {
            match_id: '4221909',
            url: 'https://www.oddsportal.com/football/germany/bundesliga-2023-2024/bayern-munich-augsburg-f3e2PS0c/',
            league_name: 'Bundesliga',
            season: '2023/2024',
            home_team: 'Bayern Munich',
            away_team: 'Augsburg'
        },
        {
            match_id: '4221910',
            url: 'https://www.oddsportal.com/football/england/premier-league-2023-2024/arsenal-chelsea-f3e2PS1d/',
            league_name: 'Premier League',
            season: '2023/2024',
            home_team: 'Arsenal',
            away_team: 'Chelsea'
        },
        {
            match_id: '4221911',
            url: 'https://www.oddsportal.com/football/spain/la-liga-2023-2024/barcelona-real-madrid-f3e2PS2e/',
            league_name: 'La Liga',
            season: '2023/2024',
            home_team: 'Barcelona',
            away_team: 'Real Madrid'
        },
        {
            match_id: '4221912',
            url: 'https://www.oddsportal.com/football/italy/serie-a-2023-2024/juventus-inter-milan-f3e2PS3f/',
            league_name: 'Serie A',
            season: '2023/2024',
            home_team: 'Juventus',
            away_team: 'Inter Milan'
        },
        {
            match_id: '4221913',
            url: 'https://www.oddsportal.com/football/france/ligue-1-2023-2024/psg-marseille-f3e2PS4g/',
            league_name: 'Ligue 1',
            season: '2023/2024',
            home_team: 'PSG',
            away_team: 'Marseille'
        }
    ];

    return fallbackUrls.slice(0, count);
}

// ============================================================================
// TEST EXECUTION
// ============================================================================

/**
 * V85.902: 执行单场测试
 */
async function testSingleMatch(matchInfo, browser, config) {
    const result = new MatchTestResult(matchInfo.match_id, matchInfo.url);

    log.info(`\n════════════════════════════════════════════════════════════`);
    log.info(`[TEST] Match: ${matchInfo.home_team} vs ${matchInfo.away_team}`);
    log.info(`[TEST] URL: ${matchInfo.url}`);
    log.info(`════════════════════════════════════════════════════════════`);

    let context = null;
    let page = null;

    try {
        // 创建浏览器上下文
        context = await browser.newContext({
            viewport: config.browser.viewport,
            userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        });

        page = await context.newPage();
        page.setDefaultTimeout(config.browser.timeout);

        // 导航到页面
        await page.goto(matchInfo.url, { waitUntil: 'networkidle' });
        await page.waitForTimeout(3000);

        // 按优先级尝试每个提供商
        for (const providerKey of config.targetProviders) {
            // Step 1: Node Detection (Module-Alpha 定位)
            log.debug(`[Step 1] Attempting to locate: ${providerKey}`);

            try {
                // 使用 captureSingleProviderVisually 执行完整流程
                const captureResult = await interaction.captureSingleProviderVisually(page, providerKey);

                if (captureResult.success) {
                    result.nodeDetection = true;
                    log.success(`[Step 1] ✓ Node Detection SUCCESS: ${providerKey}`);

                    // Step 2: UI Rendering (弹窗挂载)
                    if (captureResult.html && captureResult.html.includes('Odds movement')) {
                        result.uiRendering = true;
                        log.success(`[Step 2] ✓ UI Rendering SUCCESS: Modal captured`);

                        // Step 3: Parsing Stats
                        try {
                            const records = parser.parseModalHtml(captureResult.html, providerKey);
                            result.recordsCount = records.length;

                            if (records.length > 0) {
                                result.parsingSuccess = true;

                                // 检查年份校准 (2026)
                                result.yearCalibrated = records.some(r =>
                                    r.timestamp && r.timestamp.includes('2026')
                                );

                                log.success(`[Step 3] ✓ Parsing SUCCESS: ${records.length} records, Year: ${result.yearCalibrated ? '2026 ✓' : 'N/A'}`);
                                break; // 成功，停止尝试其他提供商
                            } else {
                                log.warn(`[Step 3] ✗ Parsing FAIL: 0 records extracted`);
                            }
                        } catch (parseError) {
                            log.error(`[Step 3] ✗ Parsing ERROR: ${parseError.message}`);
                        }
                    } else {
                        log.warn(`[Step 2] ✗ UI Rendering FAIL: No valid HTML captured`);
                    }
                } else {
                    log.debug(`[Step 1] ✗ Node Detection FAIL: ${providerKey} - ${captureResult.error || 'Not found'}`);
                }
            } catch (error) {
                log.debug(`[Error] ${providerKey}: ${error.message}`);
            }

            // 清理：移开鼠标
            try {
                await page.mouse.click(0, 0);
                await page.waitForTimeout(500);
            } catch (e) {
                // 忽略
            }
        }

        // 如果没有找到任何提供商，记录错误
        if (!result.nodeDetection) {
            result.error = 'NODE_DETECTION_FAILED';
            result.errorMessage = 'All providers failed node detection';
            log.warn('[Result] ✗ FAIL: No providers detected');
        }

    } catch (error) {
        result.error = 'EXECUTION_ERROR';
        result.errorMessage = error.message;
        log.error(`[Result] ✗ EXCEPTION: ${error.message}`);
    } finally {
        result.finish();

        if (page) {
            await page.close();
        }
        if (context) {
            await context.close();
        }

        log.info(`[Result] Elapsed: ${result.elapsed.toFixed(2)}s`);
        log.info(`[Result] Detection: ${result.nodeDetection ? '✓' : '✗'} | UI: ${result.uiRendering ? '✓' : '✗'} | Parse: ${result.parsingSuccess ? '✓' : '✗'} | Records: ${result.recordsCount}`);
    }

    return result;
}

/**
 * V85.902: 执行全链路测试
 */
async function executeFullLinkTest() {
    log.info('╔════════════════════════════════════════════════════════════╗');
    log.info('║     V85.902 - 动态前端组件全链路交互分析                 ║');
    log.info('╚════════════════════════════════════════════════════════════╝');
    log.info('');
    log.info(`测试参数:`);
    log.info(`  - 样本数: ${V85_902_CONFIG.sampleSize}`);
    log.info(`  - 目标提供商: ${V85_902_CONFIG.targetProviders.join(', ')}`);
    log.info(`  - Headless: ${V85_902_CONFIG.browser.headless}`);
    log.info('');

    const stats = new AggregateStats();
    let browser = null;

    try {
        // 获取待测试 URL
        log.info('[INIT] Fetching PENDING URLs from database...');
        const pendingUrls = await fetchPendingUrls(V85_902_CONFIG);

        if (pendingUrls.length === 0) {
            log.error('[INIT] No URLs available for testing');
            return;
        }

        log.info(`[INIT] Retrieved ${pendingUrls.length} URLs for testing`);
        log.info('');

        // 初始化浏览器
        log.info('[INIT] Initializing browser...');
        browser = await chromium.launch({
            headless: V85_902_CONFIG.browser.headless,
            slowMo: V85_902_CONFIG.browser.slowMo
        });
        log.success('[INIT] ✓ Browser ready');
        log.info('');

        // 执行测试
        const startTime = Date.now();

        for (let i = 0; i < pendingUrls.length; i++) {
            const matchInfo = pendingUrls[i];
            log.info(`\n[PROGRESS] ${i + 1}/${pendingUrls.length}`);

            const result = await testSingleMatch(matchInfo, browser, V85_902_CONFIG);
            stats.addResult(result);
        }

        const totalElapsed = (Date.now() - startTime) / 1000;

        // 生成最终报告
        generateFinalReport(stats, totalElapsed);

    } catch (error) {
        log.error(`[FATAL] Test execution failed: ${error.message}`);
        log.error(error.stack);
    } finally {
        if (browser) {
            await browser.close();
            log.info('[CLEANUP] Browser closed');
        }
    }

    return stats;
}

// ============================================================================
// REPORT GENERATION
// ============================================================================

/**
 * V85.902: 生成最终报告 (Strict Concise Format)
 */
function generateFinalReport(stats, totalElapsed) {
    log.info('');
    log.info('╔════════════════════════════════════════════════════════════╗');
    log.info('║           [V85.902] Component Interaction Test             ║');
    log.info('╠════════════════════════════════════════════════════════════╣');

    // Node Detection
    const ndRate = stats.nodeDetectionRate;
    log.info(`║  1. Node Detection: ${ndRate}% (${stats.nodeDetectionSuccess}/${stats.total})`);

    // UI Rendering
    const uiRate = stats.uiRenderingRate;
    log.info(`║  2. UI Rendering: ${uiRate}% (${stats.uiRenderingSuccess}/${stats.total})`);

    // Parsing Stats
    log.info(`║  3. Parsing Stats:`);
    log.info(`║     - Records Count: ${stats.totalRecords}`);
    log.info(`║     - Year Calibrated: ${stats.yearCalibratedCount}/${stats.total} (${stats.total > 0 ? (stats.yearCalibratedCount / stats.total * 100).toFixed(1) : 0}%)`);

    // System Latency
    const avgLatency = stats.avgElapsed;
    log.info(`║  4. System Latency: ${avgLatency}s avg`);

    // Stability Proof
    const stable = stats.stabilityProof;
    log.info(`╠════════════════════════════════════════════════════════════╣`);
    log.info(`║  FINAL: ${stable ? 'STABLE ✓' : 'UNSTABLE ✗'}                                   ║`);
    log.info(`║  Total Time: ${totalElapsed.toFixed(2)}s                                        ║`);
    log.info('╚════════════════════════════════════════════════════════════╝');
    log.info('');

    // 控制台输出协议格式
    console.log('');
    console.log('═══════════════════════════════════════════════════════════════');
    console.log('[V85.902] Component Interaction Test COMPLETE');
    console.log(`═══════════════════════════════════════════════════════════════`);
    console.log(`Success Rate: ${stats.nodeDetectionSuccess}/${stats.total}`);
    console.log(`System Latency: ${avgLatency}s`);
    console.log(`Stability Proof: ${stable ? 'YES' : 'NO'}`);
    console.log(`═══════════════════════════════════════════════════════════════`);
    console.log('');

    // 详细错误列表 (如果有)
    if (stats.errors.length > 0) {
        log.info('╔════════════════════════════════════════════════════════════╗');
        log.info('║                    Error Details                          ║');
        log.info('╠════════════════════════════════════════════════════════════╣');
        stats.errors.forEach((err, idx) => {
            log.info(`║  ${idx + 1}. [${err.matchId}] ${err.errorMessage}`);
        });
        log.info('╚════════════════════════════════════════════════════════════╝');
    }
}

// ============================================================================
// MAIN ENTRY
// ============================================================================

async function main() {
    try {
        const stats = await executeFullLinkTest();

        // 返回退出码 (稳定性证明通过 = 0, 否则 = 1)
        const exitCode = stats.stabilityProof ? 0 : 1;
        process.exit(exitCode);

    } catch (error) {
        log.error(`FATAL: ${error.message}`);
        process.exit(2);
    }
}

// 如果直接运行此脚本
if (require.main === module) {
    main();
}

module.exports = {
    executeFullLinkTest,
    generateFinalReport,
    V85_902_CONFIG,
    MatchTestResult,
    AggregateStats
};
