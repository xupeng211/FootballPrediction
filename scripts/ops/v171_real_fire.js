/**
 * V171.001 Live Fire - 真实比赛收割 + 基本面数据
 */

'use strict';

const path = require('path');
const { Client } = require('pg');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const { DatabaseConfig } = require(path.join(PROJECT_ROOT, 'config/database'));
const { QuantHarvester } = require(path.join(PROJECT_ROOT, 'src/infrastructure/engines/QuantHarvester'));
const { FundamentalHarvester } = require(path.join(PROJECT_ROOT, 'src/infrastructure/engines/FundamentalHarvester'));

// 真实比赛 URL（从 OddsPortal 获取）
const REAL_MATCHES = [
    {
        id: 'EPL_20260228_LIV_WHU',
        url: 'https://www.oddsportal.com/football/england/premier-league/liverpool-west-ham-KbUrxW1T/',
        home_team: 'Liverpool',
        away_team: 'West Ham',
        league_name: 'Premier League'
    },
    {
        id: 'EPL_20260301_ARS_CHE',
        url: 'https://www.oddsportal.com/football/england/premier-league/arsenal-chelsea-CE2gREmB/',
        home_team: 'Arsenal',
        away_team: 'Chelsea',
        league_name: 'Premier League'
    }
];

async function main() {
    console.log('');
    console.log('╔════════════════════════════════════════════════════════════════╗');
    console.log('║     V171.000 LIVE FIRE - 真实比赛收割                          ║');
    console.log('╚════════════════════════════════════════════════════════════════╝');
    console.log('');

    const client = new Client({
        host: DatabaseConfig.host,
        port: DatabaseConfig.port,
        database: DatabaseConfig.database,
        user: DatabaseConfig.user,
        password: DatabaseConfig.password
    });

    let harvester = null;

    try {
        // 连接数据库
        await client.connect();
        console.log('✅ 数据库连接成功');

        // 存储比赛
        console.log('');
        console.log('💾 存储比赛到数据库...');
        for (const match of REAL_MATCHES) {
            await client.query(`
                INSERT INTO matches (match_id, home_team, away_team, league_name, season, match_date)
                VALUES ($1, $2, $3, $4, $5, NOW())
                ON CONFLICT (match_id) DO UPDATE SET
                    home_team = EXCLUDED.home_team,
                    away_team = EXCLUDED.away_team
            `, [match.id, match.home_team, match.away_team, match.league_name, '2025-2026']);
            console.log(`   ✅ ${match.home_team} vs ${match.away_team}`);
        }

        // 初始化 QuantHarvester
        console.log('');
        console.log('🚀 初始化 QuantHarvester...');
        console.log('   代理: 启用 (NetworkShield 22节点)');
        console.log('   Python 桥接: 启用');

        harvester = new QuantHarvester({
            enableProxy: true,
            enablePythonBridge: true,
            logLevel: 'info'
        });

        await harvester.init();

        // 执行收割
        console.log('');
        console.log('🎯 开始收割赔率数据...');
        console.log('');

        const results = await harvester.harvestBatch(REAL_MATCHES);

        // 输出结果
        console.log('');
        console.log('╔════════════════════════════════════════════════════════════════╗');
        console.log('║                    HARVEST RESULTS                            ║');
        console.log('╠════════════════════════════════════════════════════════════════╣');

        let successCount = 0;
        results.forEach((r, i) => {
            const status = r.success ? '✅' : '❌';
            const match = REAL_MATCHES[i];
            console.log(`${status} ${match.home_team} vs ${match.away_team}`);
            console.log(`   数据点: ${r.dataPoints || 0}, 耗时: ${r.elapsed}ms, 方法: ${r.method || 'N/A'}`);
            if (r.success) successCount++;
        });

        console.log('╠════════════════════════════════════════════════════════════════╣');
        console.log(`║  成功: ${successCount}/${results.length}                                                ║`);
        console.log('╚════════════════════════════════════════════════════════════════╝');

        // V171.001: 采集基本面数据（阵容、伤停、身价）
        console.log('');
        console.log('🎯 开始采集基本面数据...');

        const fundamentalsHarvester = new FundamentalHarvester();
        let fundamentalsSuccess = 0;

        for (const match of REAL_MATCHES) {
            try {
                // 尝试使用 FotMob match_id（需要转换）
                // 这里使用 match.id 作为占位符，实际可能需要 FotMob 的真实 match ID
                const fundamentals = await fundamentalsHarvester.harvest(match.id, { saveToDb: true });
                if (fundamentals) {
                    console.log(`   ✅ ${match.home_team} vs ${match.away_team} - 基本面数据已保存`);
                    fundamentalsSuccess++;
                }
            } catch (e) {
                console.log(`   ⚠️ ${match.home_team} vs ${match.away_team} - 基本面采集失败: ${e.message}`);
            }
        }

        await fundamentalsHarvester.close();

        console.log('');
        console.log(`📊 基本面数据采集完成: ${fundamentalsSuccess}/${REAL_MATCHES.length}`);

        // 检查 match_fundamentals 表
        const fundResult = await client.query(`
            SELECT match_id, home_formation, away_formation,
                   jsonb_array_length(home_missing) as home_missing_count,
                   jsonb_array_length(away_missing) as away_missing_count
            FROM match_fundamentals
            WHERE match_id = ANY($1)
        `, [REAL_MATCHES.map(m => m.id)]);

        if (fundResult.rows.length > 0) {
            console.log('');
            console.log('╔════════════════════════════════════════════════════════════════╗');
            console.log('║                    FUNDAMENTALS STORED                        ║');
            console.log('╠════════════════════════════════════════════════════════════════╣');
            fundResult.rows.forEach(row => {
                const match = REAL_MATCHES.find(m => m.id === row.match_id);
                console.log(`📋 ${match?.home_team || row.match_id}`);
                console.log(`   阵型: ${row.home_formation || 'N/A'} vs ${row.away_formation || 'N/A'}`);
                console.log(`   缺阵: ${row.home_missing_count}H / ${row.away_missing_count}A`);
            });
            console.log('╚════════════════════════════════════════════════════════════════╝');
        }

        // 检查预测
        if (successCount > 0) {
            console.log('');
            console.log('📊 检查预测结果...');

            await new Promise(resolve => setTimeout(resolve, 2000));

            const predResult = await client.query(`
                SELECT match_id, predicted_result, final_confidence, model_version
                FROM predictions
                WHERE match_id = ANY($1)
                ORDER BY prediction_date DESC
            `, [REAL_MATCHES.map(m => m.id)]);

            if (predResult.rows.length > 0) {
                console.log('');
                console.log('╔════════════════════════════════════════════════════════════════╗');
                console.log('║                    PREDICTIONS                                ║');
                console.log('╠════════════════════════════════════════════════════════════════╣');

                predResult.rows.forEach(pred => {
                    const match = REAL_MATCHES.find(m => m.id === pred.match_id);
                    console.log(`🏆 ${match?.home_team || '?'} vs ${match?.away_team || '?'}`);
                    console.log(`   预测: ${pred.predicted_result.toUpperCase()}`);
                    console.log(`   置信度: ${(pred.final_confidence * 100).toFixed(1)}%`);
                    console.log(`   模型: ${pred.model_version}`);
                    console.log('');
                });

                console.log('╚════════════════════════════════════════════════════════════════╝');
            } else {
                console.log('⚠️ 暂无预测结果（收割可能未完全成功）');
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
        await client.end();
    }
}

main();
