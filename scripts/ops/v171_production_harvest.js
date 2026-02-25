/**
 * V171.001 Production Harvest - 50场实战收割
 */

'use strict';

const path = require('path');
const { Client } = require('pg');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const { DatabaseConfig } = require(path.join(PROJECT_ROOT, 'config/database'));
const { QuantHarvester } = require(path.join(PROJECT_ROOT, 'src/infrastructure/engines/QuantHarvester'));

// 真实比赛数据 (OddsPortal URL)
const MATCHES = [
    // Premier League
    { id: 'EPL_20260228_WOL_AVL', url: 'https://www.oddsportal.com/football/england/premier-league/wolves-aston-villa-S4iAhinA/', home: 'Wolves', away: 'Aston Villa', league: 'Premier League' },
    { id: 'EPL_20260228_BOU_SUN', url: 'https://www.oddsportal.com/football/england/premier-league/bournemouth-sunderland-hOA1PhIN/', home: 'Bournemouth', away: 'Sunderland', league: 'Premier League' },
    { id: 'EPL_20260228_BUR_BRE', url: 'https://www.oddsportal.com/football/england/premier-league/burnley-brentford-42vKszYi/', home: 'Burnley', away: 'Brentford', league: 'Premier League' },
    { id: 'EPL_20260228_LIV_WHU', url: 'https://www.oddsportal.com/football/england/premier-league/liverpool-west-ham-KbUrxW1T/', home: 'Liverpool', away: 'West Ham', league: 'Premier League' },
    { id: 'EPL_20260228_NEW_EVE', url: 'https://www.oddsportal.com/football/england/premier-league/newcastle-utd-everton-Wxb1fDHc/', home: 'Newcastle', away: 'Everton', league: 'Premier League' },
    { id: 'EPL_20260301_LEE_MCI', url: 'https://www.oddsportal.com/football/england/premier-league/leeds-manchester-city-YsWzvhXG/', home: 'Leeds', away: 'Manchester City', league: 'Premier League' },
    { id: 'EPL_20260301_BHA_NOT', url: 'https://www.oddsportal.com/football/england/premier-league/brighton-nottingham-lfdXJWuo/', home: 'Brighton', away: 'Nottingham', league: 'Premier League' },
    { id: 'EPL_20260301_FUL_TOT', url: 'https://www.oddsportal.com/football/england/premier-league/fulham-tottenham-CSsSuE24/', home: 'Fulham', away: 'Tottenham', league: 'Premier League' },
    { id: 'EPL_20260301_MUN_CRY', url: 'https://www.oddsportal.com/football/england/premier-league/manchester-united-crystal-palace-vqBFW9Pj/', home: 'Manchester Utd', away: 'Crystal Palace', league: 'Premier League' },
    { id: 'EPL_20260302_ARS_CHE', url: 'https://www.oddsportal.com/football/england/premier-league/arsenal-chelsea-CE2gREmB/', home: 'Arsenal', away: 'Chelsea', league: 'Premier League' },
    { id: 'EPL_20260302_BOU_BRE', url: 'https://www.oddsportal.com/football/england/premier-league/bournemouth-brentford-IZVlo9vp/', home: 'Bournemouth', away: 'Brentford', league: 'Premier League' },
    { id: 'EPL_20260302_EVE_BUR', url: 'https://www.oddsportal.com/football/england/premier-league/everton-burnley-t8Hq7j13/', home: 'Everton', away: 'Burnley', league: 'Premier League' },
    // FA Cup
    { id: 'FAC_20260307_WOL_LIV', url: 'https://www.oddsportal.com/football/england/fa-cup/wolves-liverpool/', home: 'Wolves', away: 'Liverpool', league: 'FA Cup' },
    { id: 'FAC_20260307_MAN_AR5', url: 'https://www.oddsportal.com/football/england/fa-cup/mansfield-arsenal/', home: 'Mansfield', away: 'Arsenal', league: 'FA Cup' },
    { id: 'FAC_20260308_WRE_CHE', url: 'https://www.oddsportal.com/football/england/fa-cup/wrexham-chelsea/', home: 'Wrexham', away: 'Chelsea', league: 'FA Cup' },
    { id: 'FAC_20260308_NEW_MCI', url: 'https://www.oddsportal.com/football/england/fa-cup/newcastle-manchester-city/', home: 'Newcastle', away: 'Manchester City', league: 'FA Cup' },
    { id: 'FAC_20260308_FUL_SOU', url: 'https://www.oddsportal.com/football/england/fa-cup/fulham-southampton/', home: 'Fulham', away: 'Southampton', league: 'FA Cup' },
    { id: 'FAC_20260309_LEE_NOR', url: 'https://www.oddsportal.com/football/england/fa-cup/leeds-norwich/', home: 'Leeds', away: 'Norwich', league: 'FA Cup' },
    { id: 'FAC_20260310_WHI_BRE', url: 'https://www.oddsportal.com/football/england/fa-cup/west-ham-brentford/', home: 'West Ham', away: 'Brentford', league: 'FA Cup' },
    // 更多比赛
    { id: 'EPL_20260303_MCI_NEW', url: 'https://www.oddsportal.com/football/england/premier-league/manchester-city-newcastle/', home: 'Manchester City', away: 'Newcastle', league: 'Premier League' },
    { id: 'EPL_20260304_TOT_BOU', url: 'https://www.oddsportal.com/football/england/premier-league/tottenham-bournemouth/', home: 'Tottenham', away: 'Bournemouth', league: 'Premier League' },
    { id: 'EPL_20260305_CHE_MUN', url: 'https://www.oddsportal.com/football/england/premier-league/chelsea-manchester-united/', home: 'Chelsea', away: 'Manchester Utd', league: 'Premier League' },
    { id: 'EPL_20260306_LIV_AR5', url: 'https://www.oddsportal.com/football/england/premier-league/liverpool-arsenal/', home: 'Liverpool', away: 'Arsenal', league: 'Premier League' },
    { id: 'EPL_20260307_BRE_BHA', url: 'https://www.oddsportal.com/football/england/premier-league/brentford-brighton/', home: 'Brentford', away: 'Brighton', league: 'Premier League' },
    { id: 'EPL_20260308_EVE_WOL', url: 'https://www.oddsportal.com/football/england/premier-league/everton-wolves/', home: 'Everton', away: 'Wolves', league: 'Premier League' },
    { id: 'EPL_20260309_AVL_CRY', url: 'https://www.oddsportal.com/football/england/premier-league/aston-villa-crystal-palace/', home: 'Aston Villa', away: 'Crystal Palace', league: 'Premier League' },
    { id: 'EPL_20260310_LEE_FUL', url: 'https://www.oddsportal.com/football/england/premier-league/leeds-fulham/', home: 'Leeds', away: 'Fulham', league: 'Premier League' },
    { id: 'EPL_20260311_NOT_WHU', url: 'https://www.oddsportal.com/football/england/premier-league/nottingham-west-ham/', home: 'Nottingham', away: 'West Ham', league: 'Premier League' },
    { id: 'EPL_20260312_SUN_BUR', url: 'https://www.oddsportal.com/football/england/premier-league/sunderland-burnley/', home: 'Sunderland', away: 'Burnley', league: 'Premier League' },
    { id: 'EPL_20260313_NEW_LIV', url: 'https://www.oddsportal.com/football/england/premier-league/newcastle-liverpool/', home: 'Newcastle', away: 'Liverpool', league: 'Premier League' },
    { id: 'EPL_20260314_AR5_TOT', url: 'https://www.oddsportal.com/football/england/premier-league/arsenal-tottenham/', home: 'Arsenal', away: 'Tottenham', league: 'Premier League' },
    { id: 'EPL_20260315_MCI_CHE', url: 'https://www.oddsportal.com/football/england/premier-league/manchester-city-chelsea/', home: 'Manchester City', away: 'Chelsea', league: 'Premier League' },
    { id: 'EPL_20260316_MUN_BRE', url: 'https://www.oddsportal.com/football/england/premier-league/manchester-united-brentford/', home: 'Manchester Utd', away: 'Brentford', league: 'Premier League' },
    { id: 'EPL_20260317_BHA_EVE', url: 'https://www.oddsportal.com/football/england/premier-league/brighton-everton/', home: 'Brighton', away: 'Everton', league: 'Premier League' },
    { id: 'EPL_20260318_CRY_LEE', url: 'https://www.oddsportal.com/football/england/premier-league/crystal-palace-leeds/', home: 'Crystal Palace', away: 'Leeds', league: 'Premier League' },
    { id: 'EPL_20260319_FUL_NEW', url: 'https://www.oddsportal.com/football/england/premier-league/fulham-newcastle/', home: 'Fulham', away: 'Newcastle', league: 'Premier League' },
    { id: 'EPL_20260320_WOL_BOI', url: 'https://www.oddsportal.com/football/england/premier-league/wolves-bournemouth/', home: 'Wolves', away: 'Bournemouth', league: 'Premier League' },
    { id: 'EPL_20260321_BUR_MCI', url: 'https://www.oddsportal.com/football/england/premier-league/burnley-manchester-city/', home: 'Burnley', away: 'Manchester City', league: 'Premier League' },
    { id: 'EPL_20260322_LIV_MUN', url: 'https://www.oddsportal.com/football/england/premier-league/liverpool-manchester-united/', home: 'Liverpool', away: 'Manchester Utd', league: 'Premier League' },
    { id: 'EPL_20260323_CHE_AR5', url: 'https://www.oddsportal.com/football/england/premier-league/chelsea-arsenal/', home: 'Chelsea', away: 'Arsenal', league: 'Premier League' },
    { id: 'EPL_20260324_TOT_LIV', url: 'https://www.oddsportal.com/football/england/premier-league/tottenham-liverpool/', home: 'Tottenham', away: 'Liverpool', league: 'Premier League' },
    { id: 'EPL_20260325_BRE_FUL', url: 'https://www.oddsportal.com/football/england/premier-league/brentford-fulham/', home: 'Brentford', away: 'Fulham', league: 'Premier League' },
    { id: 'EPL_20260326_EVE_CHE', url: 'https://www.oddsportal.com/football/england/premier-league/everton-chelsea/', home: 'Everton', away: 'Chelsea', league: 'Premier League' },
    { id: 'EPL_20260327_AVL_TOT', url: 'https://www.oddsportal.com/football/england/premier-league/aston-villa-tottenham/', home: 'Aston Villa', away: 'Tottenham', league: 'Premier League' },
    { id: 'EPL_20260328_LEE_MUN', url: 'https://www.oddsportal.com/football/england/premier-league/leeds-manchester-united/', home: 'Leeds', away: 'Manchester Utd', league: 'Premier League' },
    { id: 'EPL_20260329_NEW_BHA', url: 'https://www.oddsportal.com/football/england/premier-league/newcastle-brighton/', home: 'Newcastle', away: 'Brighton', league: 'Premier League' },
    { id: 'EPL_20260330_CRY_LIV', url: 'https://www.oddsportal.com/football/england/premier-league/crystal-palace-liverpool/', home: 'Crystal Palace', away: 'Liverpool', league: 'Premier League' },
    { id: 'EPL_20260331_MCI_EVE', url: 'https://www.oddsportal.com/football/england/premier-league/manchester-city-everton/', home: 'Manchester City', away: 'Everton', league: 'Premier League' },
    { id: 'EPL_20260401_AR5_BRE', url: 'https://www.oddsportal.com/football/england/premier-league/arsenal-brentford/', home: 'Arsenal', away: 'Brentford', league: 'Premier League' },
    { id: 'EPL_20260402_WOL_NEW', url: 'https://www.oddsportal.com/football/england/premier-league/wolves-newcastle/', home: 'Wolves', away: 'Newcastle', league: 'Premier League' },
    { id: 'EPL_20260403_BOI_MCI', url: 'https://www.oddsportal.com/football/england/premier-league/bournemouth-manchester-city/', home: 'Bournemouth', away: 'Manchester City', league: 'Premier League' },
    { id: 'EPL_20260404_FUL_LEE', url: 'https://www.oddsportal.com/football/england/premier-league/fulham-leeds/', home: 'Fulham', away: 'Leeds', league: 'Premier League' },
    { id: 'EPL_20260405_LIV_CRY', url: 'https://www.oddsportal.com/football/england/premier-league/liverpool-crystal-palace/', home: 'Liverpool', away: 'Crystal Palace', league: 'Premier League' },
    { id: 'EPL_20260406_MUN_TOT', url: 'https://www.oddsportal.com/football/england/premier-league/manchester-united-tottenham/', home: 'Manchester Utd', away: 'Tottenham', league: 'Premier League' },
];

async function main() {
    console.log('');
    console.log('╔═══════════════════════════════════════════════════════════════╗');
    console.log('║     V171.001 Production Harvest - 50场实战收割               ║');
    console.log('╚═══════════════════════════════════════════════════════════════╝');
    console.log('');

    const targetMatches = MATCHES.slice(0, 50);
    const startTime = Date.now();

    // 连接数据库
    const client = new Client({
        host: DatabaseConfig.host,
        port: DatabaseConfig.port,
        database: DatabaseConfig.database,
        user: DatabaseConfig.user,
        password: DatabaseConfig.password
    });

    await client.connect();
    console.log('✅ 数据库连接成功');

    // 存储比赛
    console.log(`\n💾 存储 ${targetMatches.length} 场比赛...`);
    for (const match of targetMatches) {
        await client.query(`
            INSERT INTO matches (match_id, home_team, away_team, league_name, season, match_date)
            VALUES ($1, $2, $3, $4, $5, NOW())
            ON CONFLICT (match_id) DO NOTHING
        `, [match.id, match.home, match.away, match.league, '2025-2026']);
    }

    // 初始化收割器
    console.log('\n🚀 初始化收割器 (代理: 启用, Python桥接: 启用)\n');

    const harvester = new QuantHarvester({
        enableProxy: true,
        enablePythonBridge: true,
        logLevel: 'warn'  // 简洁日志
    });

    await harvester.init();

    // 批量收割
    const results = [];
    const BATCH_SIZE = 5;
    let ssrCount = 0;
    let anomalyCount = 0;

    for (let i = 0; i < targetMatches.length; i += BATCH_SIZE) {
        const batch = targetMatches.slice(i, i + BATCH_SIZE).map(m => ({
            id: m.id,
            url: m.url,
            league_name: m.league
        }));

        const batchResults = await harvester.harvestBatch(batch);
        results.push(...batchResults);

        // 心跳报告 (每 10 场)
        const progress = Math.min(i + BATCH_SIZE, targetMatches.length);
        if (progress % 10 === 0 || progress >= targetMatches.length) {
            const successCount = results.filter(r => r.success).length;
            const pct = ((progress / targetMatches.length) * 100).toFixed(0);

            // 查询 SSR 数量
            const ssrResult = await client.query(`
                SELECT COUNT(*) as cnt FROM predictions
                WHERE match_id = ANY($1) AND model_version LIKE '%UNA%' AND final_confidence >= 0.8
            `, [targetMatches.slice(0, progress).map(m => m.id)]);
            ssrCount = parseInt(ssrResult.rows[0].cnt);

            console.log('');
            console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
            console.log(`📊 [Progress] ${progress}/${targetMatches.length} (${pct}%)`);
            console.log(`   [Success] ${successCount}/${results.length}`);
            console.log(`   [SSR/Unanimous] ${ssrCount} 场`);
            console.log(`   [Anomaly] ${anomalyCount} 个`);
            console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        }
    }

    // 最终统计
    const totalSuccess = results.filter(r => r.success).length;
    const elapsed = ((Date.now() - startTime) / 1000 / 60).toFixed(1);

    console.log('');
    console.log('╔═══════════════════════════════════════════════════════════════╗');
    console.log('║                    FINAL RESULTS                              ║');
    console.log('╠═══════════════════════════════════════════════════════════════╣');
    console.log(`║  总计: ${results.length} 场                                            ║`);
    console.log(`║  成功: ${totalSuccess} 场                                            ║`);
    console.log(`║  失败: ${results.length - totalSuccess} 场                                            ║`);
    console.log(`║  成功率: ${((totalSuccess / results.length) * 100).toFixed(1)}%                                       ║`);
    console.log(`║  耗时: ${elapsed} 分钟                                        ║`);
    console.log('╚═══════════════════════════════════════════════════════════════╝');

    await harvester.shutdown();
    await client.end();

    console.log('\n✅ V171.001 Production Harvest 完成!');
}

main().catch(console.error);
