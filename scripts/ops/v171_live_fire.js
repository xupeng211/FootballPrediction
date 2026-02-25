/**
 * V171.000 Live Fire - 实战收割脚本
 * ==================================
 *
 * 真实比赛数据收割 + 多模型预测
 *
 * Usage:
 *   node scripts/ops/v171_live_fire.js
 *
 * @version V171.000
 */

'use strict';

const { chromium } = require('playwright');
const { Client } = require('pg');
const path = require('path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const { DatabaseConfig } = require(path.join(PROJECT_ROOT, 'config/database'));
const { QuantHarvester } = require(path.join(PROJECT_ROOT, 'src/infrastructure/engines/QuantHarvester'));

// ============================================================================
// 配置
// ============================================================================

const CONFIG = {
    // 联赛配置
    leagues: [
        {
            name: 'Premier League',
            url: 'https://www.oddsportal.com/football/england/premier-league/',
            path: 'england/premier-league'
        },
        {
            name: 'La Liga',
            url: 'https://www.oddsportal.com/football/spain/la-liga/',
            path: 'spain/la-liga'
        }
    ],
    maxMatches: 3,
    enableProxy: true,  // 启用代理
    enablePythonBridge: true  // 启用 Python 桥接
};

// ============================================================================
// 获取真实比赛 URL
// ============================================================================

async function fetchRealMatchUrls() {
    console.log('');
    console.log('📡 [Step 1] 获取真实比赛 URL...');
    console.log('');

    const browser = await chromium.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const context = await browser.newContext({
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    });

    const page = await context.newPage();
    const matches = [];

    for (const league of CONFIG.leagues) {
        console.log(`🔍 扫描联赛: ${league.name}`);

        try {
            await page.goto(league.url, { waitUntil: 'domcontentloaded', timeout: 30000 });
            await page.waitForTimeout(8000);

            // 提取比赛链接
            const matchLinks = await page.evaluate(() => {
                const links = [];
                const rows = document.querySelectorAll('tr, div.flex, div[class*="row"]');

                rows.forEach(row => {
                    const link = row.querySelector('a[href*="/football/"]');
                    if (link) {
                        const href = link.getAttribute('href') || '';
                        const text = link.innerText || '';

                        // 检查是否是比赛链接（包含两队名称）
                        if (href.includes('-vs-') || (text.includes('–') || text.includes('vs'))) {
                            links.push({
                                text: text.trim(),
                                href: href.startsWith('http') ? href : `https://www.oddsportal.com${href}`
                            });
                        }
                    }
                });

                return links.filter(l => l.href.length > 30);
            });

            console.log(`   找到 ${matchLinks.length} 个潜在比赛链接`);

            // 提取赔率数据
            const oddsData = await page.evaluate(() => {
                const results = [];
                const rows = document.querySelectorAll('tr, div.flex, div[class*="row"]');

                rows.forEach(row => {
                    const text = row.innerText || '';
                    const links = row.querySelectorAll('a');

                    // 检查是否包含球队名称和赔率
                    if (text.includes('–') || text.includes('vs')) {
                        // 提取赔率（格式如 1.54 4.60 6.90）
                        const oddsMatch = text.match(/(\d+\.\d{2})\s+(\d+\.\d{2})\s+(\d+\.\d{2})/);

                        if (oddsMatch && links.length > 0) {
                            const mainLink = links[0];
                            const href = mainLink.getAttribute('href') || '';
                            const teamText = mainLink.innerText || '';

                            // 解析主客队
                            const parts = teamText.split(/[–\-]/).map(s => s.trim()).filter(s => s);

                            if (parts.length >= 2) {
                                results.push({
                                    homeTeam: parts[0],
                                    awayTeam: parts[1],
                                    homeOdds: parseFloat(oddsMatch[1]),
                                    drawOdds: parseFloat(oddsMatch[2]),
                                    awayOdds: parseFloat(oddsMatch[3]),
                                    href: href.startsWith('http') ? href : `https://www.oddsportal.com${href}`
                                });
                            }
                        }
                    }
                });

                return results;
            });

            for (const match of oddsData) {
                if (matches.length >= CONFIG.maxMatches) break;

                const matchId = `REAL_${Date.now()}_${matches.length}`;

                matches.push({
                    id: matchId,
                    url: match.href,
                    home_team: match.homeTeam,
                    away_team: match.awayTeam,
                    league_name: league.name,
                    initial_odds: {
                        home: match.homeOdds,
                        draw: match.drawOdds,
                        away: match.awayOdds
                    }
                });

                console.log(`   ✅ ${match.homeTeam} vs ${match.awayTeam}`);
                console.log(`      赔率: ${match.homeOdds} / ${match.drawOdds} / ${match.awayOdds}`);
                console.log(`      URL: ${match.href}`);
            }

            if (matches.length >= CONFIG.maxMatches) break;

        } catch (e) {
            console.log(`   ⚠️ 获取 ${league.name} 失败: ${e.message}`);
        }
    }

    await browser.close();

    return matches;
}

// ============================================================================
// 存储比赛到数据库
// ============================================================================

async function storeMatchesToDb(client, matches) {
    console.log('');
    console.log('💾 [Step 2] 存储比赛数据到数据库...');
    console.log('');

    for (const match of matches) {
        try {
            // 插入比赛
            await client.query(`
                INSERT INTO matches (match_id, home_team, away_team, league_name, season, match_date)
                VALUES ($1, $2, $3, $4, $5, NOW())
                ON CONFLICT (match_id) DO UPDATE SET
                    home_team = EXCLUDED.home_team,
                    away_team = EXCLUDED.away_team,
                    league_name = EXCLUDED.league_name
            `, [match.id, match.home_team, match.away_team, match.league_name, '2025-2026']);

            // 如果有初始赔率，也存储
            if (match.initial_odds) {
                await client.query(`
                    INSERT INTO metrics_multi_source_data (
                        match_id, source_name,
                        init_h, init_d, init_a,
                        final_h, final_d, final_a,
                        integrity_score, is_valid
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (match_id, source_name) DO UPDATE SET
                        init_h = EXCLUDED.init_h,
                        init_d = EXCLUDED.init_d,
                        init_a = EXCLUDED.init_a,
                        data_timestamp = NOW()
                `, [
                    match.id,
                    'Entity_Average',
                    match.initial_odds.home,
                    match.initial_odds.draw,
                    match.initial_odds.away,
                    match.initial_odds.home,
                    match.initial_odds.draw,
                    match.initial_odds.away,
                    1.05,
                    true
                ]);
            }

            console.log(`   ✅ ${match.home_team} vs ${match.away_team} 已存储`);

        } catch (e) {
            console.log(`   ⚠️ 存储 ${match.id} 失败: ${e.message}`);
        }
    }
}

// ============================================================================
// 主函数
// ============================================================================

async function main() {
    console.log('');
    console.log('╔════════════════════════════════════════════════════════════════╗');
    console.log('║     V171.000 [Integration.Alpha] - LIVE FIRE                   ║');
    console.log('║            实战收割 + 多模型预测                                ║');
    console.log('╚════════════════════════════════════════════════════════════════╝');

    let client = null;
    let harvester = null;

    try {
        // Step 1: 获取真实比赛 URL
        const matches = await fetchRealMatchUrls();

        if (matches.length === 0) {
            console.log('');
            console.log('❌ 未找到可用的比赛，请检查网络或稍后重试');
            return;
        }

        // Step 2: 连接数据库
        client = new Client({
            host: DatabaseConfig.host,
            port: DatabaseConfig.port,
            database: DatabaseConfig.database,
            user: DatabaseConfig.user,
            password: DatabaseConfig.password
        });
        await client.connect();

        // Step 3: 存储比赛
        await storeMatchesToDb(client, matches);

        // Step 4: 初始化 QuantHarvester
        console.log('');
        console.log('🚀 [Step 3] 初始化 QuantHarvester...');
        console.log('');

        harvester = new QuantHarvester({
            enableProxy: CONFIG.enableProxy,
            enablePythonBridge: CONFIG.enablePythonBridge,
            logLevel: 'info'
        });

        await harvester.init();

        // Step 5: 执行收割
        console.log('');
        console.log('🎯 [Step 4] 开始收割赔率数据...');
        console.log('');

        const harvestTasks = matches.map(m => ({
            id: m.id,
            url: m.url,
            league_name: m.league_name
        }));

        const results = await harvester.harvestBatch(harvestTasks);

        // Step 6: 检查预测结果
        console.log('');
        console.log('╔════════════════════════════════════════════════════════════════╗');
        console.log('║                    HARVEST RESULTS                            ║');
        console.log('╠════════════════════════════════════════════════════════════════╣');

        let successCount = 0;
        results.forEach((r, i) => {
            const status = r.success ? '✅' : '❌';
            console.log(`${status} ${matches[i].home_team} vs ${matches[i].away_team}`);
            console.log(`   数据点: ${r.dataPoints || 0}, 耗时: ${r.elapsed}ms, 方法: ${r.method || 'N/A'}`);
            if (r.success) successCount++;
        });

        console.log('╠════════════════════════════════════════════════════════════════╣');
        console.log(`║  成功: ${successCount}/${results.length}                                                ║`);
        console.log('╚════════════════════════════════════════════════════════════════╝');

        // Step 7: 检查预测
        if (successCount > 0) {
            console.log('');
            console.log('📊 [Step 5] 检查预测结果...');
            console.log('');

            const predResult = await client.query(`
                SELECT match_id, predicted_result, final_confidence, model_version
                FROM predictions
                WHERE match_id = ANY($1)
                ORDER BY prediction_date DESC
            `, [matches.map(m => m.id)]);

            if (predResult.rows.length > 0) {
                console.log('╔════════════════════════════════════════════════════════════════╗');
                console.log('║                    PREDICTIONS                                ║');
                console.log('╠════════════════════════════════════════════════════════════════╣');

                predResult.rows.forEach(pred => {
                    const match = matches.find(m => m.id === pred.match_id);
                    console.log(`🏆 ${match?.home_team || '?'} vs ${match?.away_team || '?'}`);
                    console.log(`   预测: ${pred.predicted_result.toUpperCase()}`);
                    console.log(`   置信度: ${(pred.final_confidence * 100).toFixed(1)}%`);
                    console.log(`   模型: ${pred.model_version}`);
                    console.log('');
                });

                console.log('╚════════════════════════════════════════════════════════════════╝');
            } else {
                console.log('⚠️ 暂无预测结果（可能需要更多数据）');
            }
        }

        console.log('');
        console.log('✅ V171.000 Live Fire 完成!');

    } catch (error) {
        console.error('');
        console.error('❌ FATAL ERROR:', error.message);
        console.error(error.stack);
    } finally {
        if (harvester) await harvester.shutdown();
        if (client) await client.end();
    }
}

// ============================================================================
// ENTRY POINT
// ============================================================================

main().catch(console.error);
