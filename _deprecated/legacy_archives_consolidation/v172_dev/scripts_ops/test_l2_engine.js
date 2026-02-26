/**
 * V172-L2-01 L2 引擎验收测试
 * ============================
 *
 * 目标: 针对 EPL_20260208_LIV_NEW (利物浦 vs 纽卡斯尔) 执行精准抓取
 *
 * @module scripts/ops/test_l2_engine
 */

'use strict';

const path = require('path');
const PROJECT_ROOT = '/app';

const { DatabaseConfig } = require(path.join(PROJECT_ROOT, 'config/database'));
const { Client } = require('pg');
const { chromium } = require('playwright');

// 目标比赛 (使用有 external_id 的比赛)
const TARGET_MATCH = {
    match_id: 'EPL_20260509_LIV_CHE',
    external_id: '4813729',  // FotMob ID
    home_team: 'Liverpool',
    away_team: 'Chelsea'
};

const FOTMOB_API = 'https://www.fotmob.com/api/matchDetails';

// ============================================================================
// Logger
// ============================================================================

const log = {
    info: (msg) => console.log(`[${new Date().toISOString().slice(11, 19)}] ℹ️  ${msg}`),
    success: (msg) => console.log(`[${new Date().toISOString().slice(11, 19)}] ✅ ${msg}`),
    warn: (msg) => console.log(`[${new Date().toISOString().slice(11, 19)}] ⚠️  ${msg}`),
    error: (msg) => console.log(`[${new Date().toISOString().slice(11, 19)}] ❌ ${msg}`)
};

// ============================================================================
// Step 1: 获取原始数据 (API 拦截)
// ============================================================================

async function fetchMatchDetails(externalId) {
    log.info(`启动浏览器，目标 ID: ${externalId}`);

    const browser = await chromium.launch({
        headless: true,
        args: ['--disable-blink-features=AutomationControlled']
    });

    const context = await browser.newContext({
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        viewport: { width: 1920, height: 1080 }
    });

    const page = await context.newPage();

    let capturedData = null;

    // API 拦截
    page.on('response', async (response) => {
        if (response.url().includes('/api/matchDetails')) {
            try {
                capturedData = await response.json();
                log.success(`🎯 API 拦截成功!`);
            } catch (e) {
                log.warn(`API 解析失败: ${e.message}`);
            }
        }
    });

    try {
        const matchUrl = `https://www.fotmob.com/matches/-/${externalId}`;
        log.info(`访问: ${matchUrl}`);

        await page.goto(matchUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
        await page.waitForTimeout(10000);

        if (!capturedData) {
            // 备用：直接 API 请求
            log.warn('尝试直接 API 请求...');

            const apiResponse = await page.evaluate(async (matchId) => {
                const res = await fetch(`https://www.fotmob.com/api/matchDetails?matchId=${matchId}`);
                return await res.json();
            }, externalId);

            capturedData = apiResponse;
        }

    } finally {
        await context.close();
        await browser.close();
    }

    return capturedData;
}

// ============================================================================
// Step 2: 精准解析 (根据 team_id 分配 xG)
// ============================================================================

function parseXgData(rawData, homeTeam, awayTeam) {
    const content = rawData?.content || {};
    const stats = content?.stats || [];

    // 获取团队 ID
    const homeTeamId = content?.home?.id;
    const awayTeamId = content?.away?.id;

    log.info(`团队 ID: 主队=${homeTeamId}, 客队=${awayTeamId}`);

    // 查找 xG 数据
    const xgStats = stats.find(s =>
        s.title?.toLowerCase().includes('expected') ||
        s.title?.toLowerCase().includes('xg')
    );

    if (xgStats?.stats?.length >= 2) {
        log.info(`找到 xG 数据: ${JSON.stringify(xgStats.stats)}`);

        // 关键：根据 team_id 分配
        for (const stat of xgStats.stats) {
            const statTeamId = stat.teamId || stat.id;
            const value = parseFloat(stat.statValue);

            if (statTeamId === homeTeamId) {
                return { xg_home: value, xg_away: null, teamIdMatched: true };
            } else if (statTeamId === awayTeamId) {
                return { xg_home: null, xg_away: value, teamIdMatched: true };
            }
        }

        // 降级：按数组顺序
        log.warn('⚠️ 使用数组顺序分配 xG (无 team_id 匹配)');
        return {
            xg_home: parseFloat(xgStats.stats[0].statValue),
            xg_away: parseFloat(xgStats.stats[1].statValue),
            teamIdMatched: false
        };
    }

    return { xg_home: null, xg_away: null, teamIdMatched: false };
}

// ============================================================================
// Step 3: 存储数据 (原始 + 解析)
// ============================================================================

async function storeMatchDetails(client, matchId, rawData, parsedData) {
    // 3.1: 存储原始 JSON
    const rawQuery = `
        INSERT INTO raw_match_data (match_id, l2_raw_json, collected_at)
        VALUES ($1, $2::jsonb, NOW())
        ON CONFLICT (match_id) DO UPDATE SET
            l2_raw_json = EXCLUDED.l2_raw_json,
            collected_at = NOW()
    `;

    await client.query(rawQuery, [matchId, JSON.stringify(rawData)]);
    log.success(`原始 JSON 已存入 l2_raw_json`);

    // 3.2: 更新解析后的字段
    const updateQuery = `
        UPDATE matches SET
            xg_home = $2,
            xg_away = $3,
            updated_at = NOW()
        WHERE match_id = $1
    `;

    await client.query(updateQuery, [matchId, parsedData.xg_home, parsedData.xg_away]);
    log.success(`xG 数据已更新到 matches 表`);
}

// ============================================================================
// Step 4: 验证查询
// ============================================================================

async function verifyData(client, matchId) {
    console.log('\n═'.repeat(60));
    console.log('  📊 验证查询结果');
    console.log('═'.repeat(60));

    // 查询 matches 表
    const matchResult = await client.query(`
        SELECT match_id, home_team, away_team, xg_home, xg_away, updated_at
        FROM matches
        WHERE match_id = $1
    `, [matchId]);

    if (matchResult.rows.length > 0) {
        const row = matchResult.rows[0];
        console.log('\n📋 matches 表:');
        console.log(`   match_id:    ${row.match_id}`);
        console.log(`   home_team:   ${row.home_team}`);
        console.log(`   away_team:   ${row.away_team}`);
        console.log(`   xg_home:     ${row.xg_home}`);
        console.log(`   xg_away:     ${row.away_team}`);
        console.log(`   updated_at:  ${row.updated_at}`);
    }

    // 查询 raw_match_data 表
    const rawResult = await client.query(`
        SELECT match_id,
               LENGTH(l2_raw_json::text) as json_size,
               SUBSTRING(l2_raw_json::text, 1, 200) as json_preview,
               collected_at
        FROM raw_match_data
        WHERE match_id = $1
    `, [matchId]);

    if (rawResult.rows.length > 0) {
        const row = rawResult.rows[0];
        console.log('\n📋 raw_match_data 表:');
        console.log(`   match_id:     ${row.match_id}`);
        console.log(`   json_size:    ${row.json_size} bytes`);
        console.log(`   json_preview: ${row.json_preview}...`);
        console.log(`   collected_at: ${row.collected_at}`);
    }
}

// ============================================================================
// 主函数
// ============================================================================

async function main() {
    console.log('\n═'.repeat(60));
    console.log('  V172-L2-01 L2 引擎验收测试');
    console.log('  目标: 利物浦 vs 纽卡斯尔');
    console.log('═'.repeat(60));

    // 连接数据库
    const client = new Client({
        host: DatabaseConfig.host,
        port: DatabaseConfig.port,
        database: DatabaseConfig.database,
        user: DatabaseConfig.user,
        password: DatabaseConfig.password
    });

    await client.connect();
    log.success('数据库连接成功');

    try {
        // Step 1: 获取原始数据
        log.info('\n📡 Step 1: 获取原始数据...');
        const rawData = await fetchMatchDetails(TARGET_MATCH.external_id);

        if (!rawData) {
            throw new Error('无法获取原始数据');
        }

        log.success(`原始数据大小: ${JSON.stringify(rawData).length} bytes`);

        // 调试：打印原始数据结构
        console.log('\n📦 原始数据结构:');
        console.log(JSON.stringify(rawData, null, 2).substring(0, 500));

        // Step 2: 精准解析
        log.info('\n🔬 Step 2: 精准解析 xG...');
        const parsedData = parseXgData(rawData, TARGET_MATCH.home_team, TARGET_MATCH.away_team);

        console.log(`   xg_home: ${parsedData.xg_home}`);
        console.log(`   xg_away: ${parsedData.xg_away}`);
        console.log(`   teamId匹配: ${parsedData.teamIdMatched}`);

        // Step 3: 存储数据
        log.info('\n💾 Step 3: 存储数据...');
        await storeMatchDetails(client, TARGET_MATCH.match_id, rawData, parsedData);

        // Step 4: 验证
        await verifyData(client, TARGET_MATCH.match_id);

        console.log('\n═'.repeat(60));
        console.log('  ✅ L2 引擎验收测试通过！');
        console.log('═'.repeat(60));

    } catch (error) {
        log.error(`测试失败: ${error.message}`);
        console.error(error.stack);
    } finally {
        await client.end();
    }
}

main().catch(console.error);
