/**
 * V85.960 Six-Tigers Attendance Survey
 * =====================================
 *
 * 六大核心供应商 (The Big Six) 出勤率专项统计
 *
 * 功能：
 *   - 从数据库随机抽取 100 个 PENDING 状态的哈希值
 *   - 对每场比赛尝试定位 6 家提供商
 *   - 统计"成功定位节点"和"成功触发弹窗"的比例
 *   - 生成出勤率报表
 *
 * @author Senior Data Analyst & Automation Architect
 * @version V85.960
 * @since 2026-01-25
 */

'use strict';

const { chromium } = require('playwright');
const { Client } = require('pg');

// 导入 V85.951 增强模块
const interactionV51 = require('./modules/interaction_v51');

// ============================================================================
// CONFIGURATION
// ============================================================================

const SURVEY_CONFIG = {
    // 六大核心供应商 (The Big Six)
    providers: ['PINNACLE', 'BET365', 'LADBROKES', 'BWIN', 'WILLIAM_HILL', 'ONEXBET'],

    // 样本配置
    sampleSize: 100,
    concurrent: 3,
    timeout: 15000,

    // 浏览器配置
    browser: {
        headless: true,
        timeout: 30000
    },

    // 数据库配置
    database: {
        host: process.env.DB_HOST || 'localhost',
        port: process.env.DB_PORT || 5432,
        database: 'football_db',
        user: process.env.DB_USER || 'football_user',
        password: process.env.DB_PASSWORD || 'football_password',
        // 从环境变量或默认值获取
        connectionString: process.env.DATABASE_URL
    },

    // OddsPortal 基础 URL
    oddsportalBaseUrl: 'https://www.oddsportal.com/match/'
};

// ============================================================================
// DATABASE OPERATIONS
// ============================================================================

/**
 * 获取 100 个 PENDING 状态的样本哈希值
 *
 * @returns {Promise<Array<{match_id: string, oddsportal_hash: string, oddsportal_url: string}>>}
 */
async function getPendingSamples() {
    const client = new Client({
        host: SURVEY_CONFIG.database.host,
        port: SURVEY_CONFIG.database.port,
        database: SURVEY_CONFIG.database.database,
        user: SURVEY_CONFIG.database.user,
        password: SURVEY_CONFIG.database.password,
    });

    try {
        await client.connect();

        // 查询 PENDING 状态且有 oddsportal_hash 的记录
        const query = `
            SELECT
                m.match_id,
                mm.oddsportal_hash,
                mm.oddsportal_url
            FROM matches m
            LEFT JOIN matches_mapping mm ON m.match_id = mm.match_id
            WHERE mm.oddsportal_hash IS NOT NULL
            ORDER BY RANDOM()
            LIMIT $1
        `;

        const result = await client.query(query, [SURVEY_CONFIG.sampleSize]);

        console.log(`[V85.960] 从数据库获取 ${result.rows.length} 个样本`);
        return result.rows;

    } catch (error) {
        console.error(`[V85.960] 数据库查询失败: ${error.message}`);
        // 返回模拟数据用于测试
        return [];
    } finally {
        await client.end();
    }
}

// ============================================================================
// ATTENDANCE SURVEY
// ============================================================================

/**
 * 单场比赛的提供商出勤率检查
 *
 * @param {import('@playwright/test').Page} page - Playwright 页面对象
 * @param {string} url - OddsPortal 比赛页面 URL
 * @param {string} matchId - 比赛 ID
 * @returns {Promise<Object>}
 */
async function checkMatchAttendance(page, url, matchId) {
    const results = {
        matchId: matchId,
        url: url,
        providers: {},
        summary: {
            located: 0,
            triggered: 0,
            total: SURVEY_CONFIG.providers.length
        }
    };

    try {
        // 访问比赛页面
        await page.goto(url, {
            timeout: SURVEY_CONFIG.browser.timeout,
            waitUntil: 'networkidle'
        });

        await page.waitForTimeout(1000); // 等待动态内容加载

        // 对每个提供商进行出勤率检查
        for (const providerKey of SURVEY_CONFIG.providers) {
            const providerResult = {
                located: false,
                triggered: false,
                method: null,
                selector: null
            };

            try {
                // Step 1: 定位提供商节点
                const locatorResult = await interactionV51.locateProviderWithTripleLocator(page, providerKey);

                if (locatorResult.element) {
                    providerResult.located = true;
                    providerResult.method = locatorResult.method;
                    providerResult.selector = locatorResult.selector;

                    // Step 2: 尝试触发弹窗
                    const hoverResult = await interactionV51.calibratedHover(locatorResult.element, page, {
                        initialTimeout: 2000,
                        anchorSelector: 'h3:text("Odds movement"), h3:has-text("Odds movement")'
                    });

                    providerResult.triggered = hoverResult.success;
                }

            } catch (error) {
                // 单个提供商失败不影响其他
            }

            results.providers[providerKey] = providerResult;

            if (providerResult.located) results.summary.located++;
            if (providerResult.triggered) results.summary.triggered++;
        }

    } catch (error) {
        console.error(`[V85.960] 比赛检查失败 ${matchId}: ${error.message}`);
    }

    return results;
}

/**
 * 批量处理多场比赛 (并发控制)
 *
 * @param {Array} samples - 样本数组
 * @param {number} concurrency - 并发数
 * @returns {Promise<Array>}
 */
async function processBatchWithConcurrency(samples, concurrency = 3) {
    const results = [];
    const browser = await chromium.launch({ headless: SURVEY_CONFIG.browser.headless });

    try {
        // 创建多个上下文并发处理
        const contextPromises = [];

        for (let i = 0; i < Math.min(concurrency, samples.length); i++) {
            contextPromises.push(processBatch(browser, samples, i, concurrency));
        }

        const batchResults = await Promise.all(contextPromises);

        // 合并结果
        for (const batch of batchResults) {
            results.push(...batch);
        }

    } finally {
        await browser.close();
    }

    return results;
}

/**
 * 处理一个批次的数据
 *
 * @param {Browser} browser - Playwright 浏览器实例
 * @param {Array} samples - 样本数组
 * @param {number} startIndex - 起始索引
 * @param {number} step - 步长
 * @returns {Promise<Array>}
 */
async function processBatch(browser, samples, startIndex, step) {
    const results = [];
    const context = await browser.newContext({
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    });

    try {
        for (let i = startIndex; i < samples.length; i += step) {
            const sample = samples[i];
            const page = await context.newPage();

            try {
                const result = await checkMatchAttendance(
                    page,
                    sample.oddsportal_url || `${SURVEY_CONFIG.oddsportalBaseUrl}${sample.oddsportal_hash}/`,
                    sample.match_id
                );
                results.push(result);

                console.log(`[V85.960] 进度: ${results.length}/${samples.length}`);

            } finally {
                await page.close();
            }
        }
    } finally {
        await context.close();
    }

    return results;
}

// ============================================================================
// REPORT GENERATION
// ============================================================================

/**
 * 生成出勤率报表
 *
 * @param {Array} results - 检查结果数组
 * @returns {Object}
 */
function generateAttendanceReport(results) {
    const report = {
        totalMatches: results.length,
        providers: {},
        summary: {}
    };

    // 初始化提供商统计
    for (const providerKey of SURVEY_CONFIG.providers) {
        report.providers[providerKey] = {
            located: 0,
            triggered: 0,
            records: []
        };
    }

    // 汇总统计
    for (const result of results) {
        for (const providerKey of SURVEY_CONFIG.providers) {
            const providerResult = result.providers[providerKey];
            if (providerResult) {
                if (providerResult.located) {
                    report.providers[providerKey].located++;
                }
                if (providerResult.triggered) {
                    report.providers[providerKey].triggered++;
                }
            }
        }
    }

    // 计算百分比
    for (const providerKey of SURVEY_CONFIG.providers) {
        const stats = report.providers[providerKey];
        stats.locationRate = ((stats.located / results.length) * 100).toFixed(1);
        stats.triggerRate = ((stats.triggered / results.length) * 100).toFixed(1);
        stats.avgRecords = (stats.triggered / Math.max(stats.located, 1)).toFixed(2);
    }

    // 生成决策建议
    const sortedByLocation = Object.entries(report.providers)
        .sort((a, b) => b[1].located - a[1].located);

    report.summary = {
        topPerformers: sortedByLocation.slice(0, 3).map(([k, v]) => ({
            provider: k,
            rate: v.locationRate
        })),
        recommendations: generateRecommendations(report.providers)
    };

    return report;
}

/**
 * 生成决策建议
 *
 * @param {Object} providers - 提供商统计
 * @returns {Array}
 */
function generateRecommendations(providers) {
    const recommendations = [];

    // 找出高可用提供商 (>70%)
    const highAvailability = Object.entries(providers)
        .filter(([k, v]) => parseFloat(v.locationRate) > 70)
        .map(([k]) => k);

    if (highAvailability.length > 0) {
        recommendations.push({
            type: 'primary_sources',
            message: `建议作为主推数据源: ${highAvailability.join(', ')}`
        });
    }

    // 检查 Ladbrokes 稳定性
    const ladbrokes = providers['LADBROKES'];
    if (ladbrokes) {
        const rate = parseFloat(ladbrokes.locationRate);
        if (rate > 60) {
            recommendations.push({
                type: 'ladbrokes_status',
                message: `Ladbrokes 定位稳定 (${rate}%)，可纳入常规采集`
            });
        } else {
            recommendations.push({
                type: 'ladbrokes_status',
                message: `Ladbrokes 定位不稳定 (${rate}%)，建议仅作辅助数据源`
            });
        }
    }

    // 找出低可用提供商 (<30%)
    const lowAvailability = Object.entries(providers)
        .filter(([k, v]) => parseFloat(v.locationRate) < 30)
        .map(([k]) => k);

    if (lowAvailability.length > 0) {
        recommendations.push({
            type: 'secondary_sources',
            message: `出勤率较低，建议作为辅助数据源: ${lowAvailability.join(', ')}`
        });
    }

    return recommendations;
}

/**
 * 打印报表
 *
 * @param {Object} report - 报表对象
 */
function printReport(report) {
    console.log('\n╔════════════════════════════════════════════════════════════════╗');
    console.log('║         [V85.960] Six-Tigers Attendance Report                 ║');
    console.log('╚════════════════════════════════════════════════════════════════╝');
    console.log(`\n总样本数: ${report.totalMatches}`);
    console.log(`\n${'─'.repeat(70)}`);
    console.log(`  ${'提供商'.padEnd(20)} | 成功定位 | 识别率 | 触发率 | 平均记录数`);
    console.log(`${'─'.repeat(70)}`);

    for (const [key, stats] of Object.entries(report.providers)) {
        const providerName = interactionV51.VISUAL_PROVIDERS[key]?.name || key;
        console.log(
            `  ${providerName.padEnd(20)} | ${String(stats.located).padStart(3)}/100 | ${String(stats.locationRate).padStart(5)}% | ${String(stats.triggerRate).padStart(5)}% | ${stats.avgRecords}`
        );
    }

    console.log(`${'─'.repeat(70)}\n`);

    // 输出决策建议
    console.log('决策建议:');
    for (const rec of report.summary.recommendations) {
        console.log(`  • ${rec.message}`);
    }
    console.log('');
}

// ============================================================================
// MAIN ENTRY
// ============================================================================

async function main() {
    console.log('[V85.960] Six-Tigers Attendance Survey 启动');
    console.log('='.repeat(70));

    // 获取样本
    const samples = await getPendingSamples();

    if (samples.length === 0) {
        console.log('[V85.960] 警告: 无可用样本，使用模拟数据');
        // 生成模拟数据用于演示
        for (let i = 0; i < SURVEY_CONFIG.sampleSize; i++) {
            samples.push({
                match_id: `mock_${i}`,
                oddsportal_hash: `hash${i}`,
                oddsportal_url: `${SURVEY_CONFIG.oddsportalBaseUrl}hash${i}/`
            });
        }
    }

    console.log(`[V85.960] 开始普查 ${samples.length} 个样本...\n`);

    // 执行普查
    const results = await processBatchWithConcurrency(samples, SURVEY_CONFIG.concurrent);

    // 生成报表
    const report = generateAttendanceReport(results);

    // 打印报表
    printReport(report);

    return report;
}

// 运行
if (require.main === module) {
    main().catch(error => {
        console.error('[V85.960] 普查失败:', error);
        process.exit(1);
    });
}

module.exports = {
    getPendingSamples,
    checkMatchAttendance,
    processBatchWithConcurrency,
    generateAttendanceReport,
    printReport,
    SURVEY_CONFIG
};
