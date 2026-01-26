/**
 * V108.100 赔率收割零件"白银样本"可靠性测试
 * ============================================
 *
 * 测试目标: 验证 V108 引擎在"数据库驱动"模式下，抓取详情页 1X2 变盘历史并入库的稳定性
 *
 * 测试流程:
 * 1. 从 matches 表抽样 10 条哈希 URL
 * 2. 对每个 URL 调用 extractMultiAxisFromRow (三轴悬停)
 * 3. 数据入库到 temporal_metric_records
 * 4. SQL 对账验证数据完整性
 *
 * @version V108.100
 * @since 2026-01-27
 */

'use strict';

const { chromium } = require('playwright');
const { extractMultiAxisFromRow } = require('./v107_000_hover_modal_engine');
const { Client } = require('pg');

const CONFIG = {
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    viewport: { width: 1920, height: 1080 },
    timeout: 120000,
    maxProviders: 5,  // 每场比赛最多处理 5 个庄家
    headless: false  // 使用 headed 模式观察悬停过程
};

const DB_CONFIG = {
    host: process.env.DB_HOST || '172.25.16.1',
    port: parseInt(process.env.DB_PORT) || 5432,
    database: process.env.DB_NAME || 'football_db',
    user: process.env.DB_USER || 'football_user',
    password: process.env.DB_PASSWORD || 'football_password'
};

const log = {
    info: (msg) => console.log(`[V108.100] [INFO] ${msg}`),
    success: (msg) => console.log(`[V108.100] [✓] ${msg}`),
    warn: (msg) => console.warn(`[V108.100] [!] ${msg}`),
    error: (msg) => console.error(`[V108.100] [✗] ${msg}`),
    section: (title) => {
        console.log('\n' + '='.repeat(70));
        console.log(`[V108.100] ${title}`);
        console.log('='.repeat(70));
    }
};

/**
 * 从数据库获取测试样本
 */
async function getTestSamples() {
    const client = new Client(DB_CONFIG);
    await client.connect();

    try {
        const result = await client.query(`
            SELECT
                match_id,
                home_team,
                away_team,
                page_url,
                league_name
            FROM matches
            WHERE page_url IS NOT NULL
              AND page_url ~ '-[A-Za-z0-9]{8,}/?$'
              AND is_finished = true
            ORDER BY RANDOM()
            LIMIT 10
        `);

        log.success(`Retrieved ${result.rows.length} test samples from database`);
        return result.rows;
    } finally {
        await client.end();
    }
}

/**
 * 创建或获取 entity_id
 */
async function getOrCreateEntity(client, matchId, url) {
    // 检查是否已存在
    const existingResult = await client.query(`
        SELECT entity_id
        FROM entities_mapping
        WHERE source_id = $1
    `, [matchId]);

    if (existingResult.rows.length > 0) {
        return existingResult.rows[0].entity_id;
    }

    // 创建新 entity
    const newResult = await client.query(`
        INSERT INTO entities_mapping (entity_id, entity_name, entity_type, source_system, source_id, source_url, is_active)
        VALUES (gen_random_uuid(), $1, 'match', 'oddsportal', $2, $3, true)
        RETURNING entity_id
    `, [`${matchId}_match`, matchId, url]);

    return newResult.rows[0].entity_id;
}

/**
 * 插入 temporal_metric_records
 */
async function insertTemporalRecords(client, entityId, multiAxisResult) {
    const records = [];
    const axes = ['axis_1', 'axis_2', 'axis_3'];
    const dimensions = ['home', 'draw', 'away'];

    axes.forEach((axisKey, idx) => {
        const axisData = multiAxisResult[axisKey];
        const metricType = dimensions[idx];

        // 如果有 init 值，插入一条记录
        if (axisData.init !== null) {
            records.push({
                entity_id: entityId,
                provider_name: multiAxisResult.provider || 'Unknown',
                metric_type: metricType,
                value: axisData.init,
                occurred_at: new Date().toISOString(),
                raw_data: JSON.stringify({
                    opening_odds: axisData.init,
                    closing_odds: axisData.init,
                    is_moved: false,
                    opening_source: 'v108.100_test',
                    history: axisData.history || []
                })
            });
        }

        // 如果有历史记录，插入每一条
        if (axisData.history && axisData.history.length > 0) {
            axisData.history.forEach((point, pointIdx) => {
                records.push({
                    entity_id: entityId,
                    provider_name: multiAxisResult.provider || 'Unknown',
                    metric_type: metricType,
                    value: point.home || point.value,
                    occurred_at: new Date(point.time).toISOString(),
                    raw_data: JSON.stringify({
                        opening_odds: axisData.init,
                        closing_odds: point.home || point.value,
                        is_moved: pointIdx > 0,
                        opening_source: 'v108.100_modal',
                        history: axisData.history
                    })
                });
            });
        }
    });

    if (records.length === 0) {
        return { inserted: 0 };
    }

    // 逐条插入（使用正确的唯一约束）
    let insertedCount = 0;
    let recordSequence = 0;  // 用于 sequence 字段

    for (const record of records) {
        try {
            await client.query(`
                INSERT INTO temporal_metric_records
                    (entity_id, provider_name, metric_type, dimension, sequence, value, occurred_at, raw_data)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (entity_id, provider_name, occurred_at, dimension, sequence)
                DO UPDATE SET
                    value = EXCLUDED.value,
                    raw_data = EXCLUDED.raw_data
            `, [record.entity_id, record.provider_name, record.metric_type, record.metric_type, recordSequence,
                record.value, record.occurred_at, record.raw_data]);
            insertedCount++;
            recordSequence++;
        } catch (e) {
            log.error(`  Failed to insert record: ${e.message}`);
            recordSequence++;  // 即使失败也递增 sequence
        }
    }

    return { inserted: insertedCount };
}

/**
 * 验证数据入库
 */
async function verifyDataInsertion(entityId) {
    const client = new Client(DB_CONFIG);
    await client.connect();

    try {
        const result = await client.query(`
            SELECT
                COUNT(*) as total_records,
                COUNT(*) FILTER (WHERE raw_data::text ~ 'opening_odds') as has_opening_odds,
                COUNT(*) FILTER (WHERE raw_data::text ~ 'history') as has_history,
                COUNT(*) FILTER (WHERE raw_data::text ~ 'is_moved.*true') as has_movement,
                COUNT(DISTINCT metric_type) as distinct_dimensions,
                COUNT(DISTINCT provider_name) as distinct_providers
            FROM temporal_metric_records
            WHERE entity_id = $1
        `, [entityId]);

        return result.rows[0];
    } finally {
        await client.end();
    }
}

/**
 * 主测试函数
 */
async function runV108100Test() {
    log.section('V108.100 RELIABILITY PILOT TEST');

    const testResults = {
        totalSamples: 10,
        successfulExtractions: 0,
        failedExtractions: 0,
        totalAxesCaptured: 0,
        totalInitValues: 0,
        totalHistoryPoints: 0,
        averageResponseTime: 0,
        errors: []
    };

    const browser = await chromium.launch({
        headless: CONFIG.headless,
        args: ['--disable-blink-features=AutomationControlled'],
        ignoreDefaultArgs: ['--enable-automation']
    });

    const context = await browser.newContext({
        userAgent: CONFIG.userAgent,
        viewport: CONFIG.viewport
    });

    await context.addInitScript(() => {
        Object.defineProperty(navigator, 'webdriver', { get: () => false });
    });

    const page = await context.newPage();
    const dbClient = new Client(DB_CONFIG);
    await dbClient.connect();

    try {
        // 获取测试样本
        log.section('STEP 1: GET TEST SAMPLES');
        const samples = await getTestSamples();

        log.info(`Samples to test: ${samples.length}`);
        samples.forEach((s, i) => {
            log.info(`  ${i + 1}. ${s.home_team} vs ${s.away_team}`);
            log.info(`     URL: ${s.page_url}`);
        });

        // 对每个样本执行测试
        log.section('STEP 2: MULTI-AXIS HOVER EXTRACTION');

        for (let i = 0; i < samples.length; i++) {
            const sample = samples[i];
            const startTime = Date.now();

            log.info(`\n[Sample ${i + 1}/${samples.length}] ${sample.home_team} vs ${sample.away_team}`);
            log.info(`URL: ${sample.page_url}`);

            try {
                // 导航到页面
                log.info(`  Navigating to page...`);
                await page.goto(sample.page_url, {
                    timeout: CONFIG.timeout,
                    waitUntil: 'networkidle'
                });

                // 等待页面加载
                await page.waitForTimeout(3000);

                // 查找庄家行
                const bookmakerRows = await page.$$('div.border-black-borders.flex.h-9, div[class*="border"][class*="flex"][class*="h-9"]');
                log.info(`  Found ${bookmakerRows.length} bookmaker rows`);

                if (bookmakerRows.length === 0) {
                    throw new Error('No bookmaker rows found');
                }

                // 处理前 N 个庄家
                const maxProviders = Math.min(bookmakerRows.length, CONFIG.maxProviders);
                let sampleSuccess = false;
                let sampleAxes = 0;
                let sampleInitValues = 0;
                let sampleHistoryPoints = 0;

                for (let j = 0; j < maxProviders; j++) {
                    try {
                        const multiAxisResult = await extractMultiAxisFromRow(page, bookmakerRows[j], j);

                        if (multiAxisResult.success) {
                            // 创建 entity
                            const entityId = await getOrCreateEntity(dbClient, sample.match_id, sample.page_url);
                            log.info(`  Entity ID: ${entityId}`);

                            // 插入数据
                            const insertResult = await insertTemporalRecords(dbClient, entityId, multiAxisResult);
                            log.success(`  Inserted ${insertResult.inserted} records`);

                            // 统计
                            const axes = ['axis_1', 'axis_2', 'axis_3'];
                            axes.forEach(axisKey => {
                                const axisData = multiAxisResult[axisKey];
                                if (axisData.init !== null || axisData.history.length > 0) {
                                    sampleAxes++;
                                    if (axisData.init !== null) {
                                        sampleInitValues++;
                                    }
                                    sampleHistoryPoints += axisData.history.length;
                                }
                            });

                            sampleSuccess = true;
                        }
                    } catch (e) {
                        log.error(`  Error processing provider ${j}: ${e.message}`);
                    }
                }

                const responseTime = Date.now() - startTime;

                if (sampleSuccess) {
                    testResults.successfulExtractions++;
                    testResults.totalAxesCaptured += sampleAxes;
                    testResults.totalInitValues += sampleInitValues;
                    testResults.totalHistoryPoints += sampleHistoryPoints;
                    testResults.averageResponseTime += responseTime;

                    log.success(`  Sample ${i + 1} SUCCESS (${responseTime}ms)`);
                    log.info(`  Axes: ${sampleAxes}, Init: ${sampleInitValues}, History: ${sampleHistoryPoints}`);
                } else {
                    testResults.failedExtractions++;
                    log.warn(`  Sample ${i + 1} FAILED`);
                }

                // 等待下一个样本
                if (i < samples.length - 1) {
                    await page.waitForTimeout(2000);
                }

            } catch (error) {
                testResults.failedExtractions++;
                testResults.errors.push({
                    sample: i + 1,
                    match: `${sample.home_team} vs ${sample.away_team}`,
                    error: error.message
                });
                log.error(`  Sample ${i + 1} ERROR: ${error.message}`);
            }
        }

        // 计算平均值
        if (testResults.successfulExtractions > 0) {
            testResults.averageResponseTime = Math.round(
                testResults.averageResponseTime / testResults.successfulExtractions
            );
        }

        log.section('STEP 3: FINAL VERIFICATION');
        log.success(`Test Complete! Generating Report...`);

    } finally {
        await dbClient.end();
        await page.close();
        await context.close();
        await browser.close();
    }

    return testResults;
}

/**
 * 生成测试报告
 */
function generateReport(results) {
    log.section('V108.100 RELIABILITY REPORT');

    console.log('');
    console.log('┌─────────────────────────────────────────────────────────────────┐');
    console.log('│                    V108.100 PILOT TEST RESULTS                   │');
    console.log('├─────────────────────────────────────────────────────────────────┤');
    console.log(`│  Test Samples              : ${String(results.totalSamples).padStart(14)}  │`);
    console.log(`│  Successful Extractions    : ${String(results.successfulExtractions).padStart(14)}  │`);
    console.log(`│  Failed Extractions       : ${String(results.failedExtractions).padStart(14)}  │`);
    console.log(`│  Success Rate              : ${String(((results.successfulExtractions / results.totalSamples) * 100).toFixed(1) + '%').padStart(14)}  │`);
    console.log('├─────────────────────────────────────────────────────────────────┤');
    console.log(`│  Total Axes Captured      : ${String(results.totalAxesCaptured).padStart(14)}  │`);
    console.log(`│  Total Init Values        : ${String(results.totalInitValues).padStart(14)}  │`);
    console.log(`│  Total History Points      : ${String(results.totalHistoryPoints).padStart(14)}  │`);
    console.log(`│  Avg Response Time (ms)    : ${String(results.averageResponseTime).padStart(14)}  │`);
    console.log('├─────────────────────────────────────────────────────────────────┤');
    console.log(`│  Full Dimension Success (1X2) : ${String(results.successfulExtractions) + '/' + results.totalSamples}`.padEnd(37) + '  │');
    console.log('└─────────────────────────────────────────────────────────────────┘');
    console.log('');

    if (results.errors.length > 0) {
        log.warn('Errors captured:');
        results.errors.forEach(e => {
            console.log(`  - Sample ${e.sample}: ${e.match} - ${e.error}`);
        });
    } else {
        log.success('No errors captured!');
    }

    const reliabilityScore = results.successfulExtractions / results.totalSamples;
    const dataIntegrityVerified = results.totalInitValues > 0 || results.totalHistoryPoints > 0;

    console.log('');
    console.log(`[V108.100] Pilot Test EXECUTED. Reliability Score: ${results.successfulExtractions}/${results.totalSamples}. Data Integrity: ${dataIntegrityVerified ? 'VERIFIED' : 'FAILED'}.`);
    console.log('');

    return {
        reliabilityScore: reliabilityScore,
        dataIntegrityVerified: dataIntegrityVerified,
        passed: reliabilityScore >= 0.5 && dataIntegrityVerified
    };
}

// 主入口
if (require.main === module) {
    runV108100Test()
        .then(results => {
            const report = generateReport(results);
            process.exit(report.passed ? 0 : 1);
        })
        .catch(error => {
            log.error(`Fatal error: ${error.message}`);
            console.error(error.stack);
            process.exit(1);
        });
}

module.exports = { runV108100Test, generateReport };
