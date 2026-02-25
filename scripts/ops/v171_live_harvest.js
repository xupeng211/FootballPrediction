/**
 * V171.000 Live Harvester - 实战收割入口
 * =======================================
 *
 * 真正的收割机入口，不是演示！
 *
 * Usage:
 *   node scripts/ops/v171_live_harvest.js [--limit N] [--no-proxy]
 *
 * @version V171.000
 */

'use strict';

const path = require('path');
const { Client } = require('pg');

// 项目根目录
const PROJECT_ROOT = path.resolve(__dirname, '../..');
const { DatabaseConfig } = require(path.join(PROJECT_ROOT, 'config/database'));

// 导入 QuantHarvester
const { QuantHarvester } = require(path.join(PROJECT_ROOT, 'src/infrastructure/engines/QuantHarvester'));

// ============================================================================
// CONFIGURATION
// ============================================================================

const CONFIG = {
    limit: parseInt(process.argv.find(a => a === '--limit') ? process.argv[process.argv.indexOf('--limit') + 1] : '3'),
    enableProxy: !process.argv.includes('--no-proxy'),
    enablePythonBridge: !process.argv.includes('--no-bridge'),
    logLevel: 'info'
};

// ============================================================================
// DATABASE HELPERS
// ============================================================================

async function getDBConnection() {
    const client = new Client({
        host: DatabaseConfig.host,
        port: DatabaseConfig.port,
        database: DatabaseConfig.database,
        user: DatabaseConfig.user,
        password: DatabaseConfig.password
    });
    await client.connect();
    return client;
}

async function getPendingMatches(client, limit) {
    // 获取需要采集赔率的比赛
    const query = `
        SELECT
            m.match_id,
            m.home_team,
            m.away_team,
            m.league_name,
            m.match_date
        FROM matches m
        WHERE m.match_date >= NOW() - INTERVAL '7 days'
          AND m.match_date <= NOW() + INTERVAL '7 days'
          AND NOT EXISTS (
              SELECT 1 FROM metrics_multi_source_data d
              WHERE d.match_id = m.match_id
              AND d.source_name LIKE 'Entity_%'
          )
        ORDER BY m.match_date ASC
        LIMIT $1
    `;

    const result = await client.query(query, [limit]);
    return result.rows;
}

async function generateOddsPortalUrl(match) {
    // V171.000: OddsPortal 2026 新 URL 格式
    // https://www.oddsportal.com/football/england/premier-league/arsenal-chelsea/
    const homeTeam = (match.home_team || 'unknown').toLowerCase().replace(/\s+/g, '-');
    const awayTeam = (match.away_team || 'unknown').toLowerCase().replace(/\s+/g, '-');

    // 根据联赛映射到 OddsPortal 路径
    const leaguePath = getLeaguePath(match.league_name);

    return `https://www.oddsportal.com/football/${leaguePath}/${homeTeam}-${awayTeam}/`;
}

function getLeaguePath(leagueName) {
    const leagueMap = {
        'Premier League': 'england/premier-league',
        'La Liga': 'spain/la-liga',
        'Bundesliga': 'germany/bundesliga',
        'Serie A': 'italy/serie-a',
        'Ligue 1': 'france/ligue-1',
        'FA Cup': 'england/fa-cup',
        'EFL Cup': 'england/efl-cup',
        'Champions League': 'europe/champions-league',
        'Europa League': 'europe/europa-league'
    };

    return leagueMap[leagueName] || 'england/premier-league';
}

// ============================================================================
// MAIN HARVEST FUNCTION
// ============================================================================

async function main() {
    console.log('');
    console.log('╔════════════════════════════════════════════════════════════════╗');
    console.log('║     V171.000 [Integration.Alpha] - LIVE HARVESTER             ║');
    console.log('╚════════════════════════════════════════════════════════════════╝');
    console.log('');
    console.log(`Config: limit=${CONFIG.limit}, proxy=${CONFIG.enableProxy}, bridge=${CONFIG.enablePythonBridge}`);
    console.log('');

    let client = null;
    let harvester = null;

    try {
        // Step 1: 连接数据库
        console.log('[Step 1] Connecting to database...');
        client = await getDBConnection();
        console.log('✅ Database connected');

        // Step 2: 获取待采集比赛
        console.log('');
        console.log('[Step 2] Fetching pending matches...');
        const matches = await getPendingMatches(client, CONFIG.limit);

        if (matches.length === 0) {
            console.log('⚠️  No pending matches found. Trying recent matches without odds...');

            // 回退：获取最近的比赛
            const fallbackQuery = `
                SELECT
                    m.match_id,
                    m.home_team,
                    m.away_team,
                    m.league_name,
                    m.match_date
                FROM matches m
                WHERE m.match_date >= NOW() - INTERVAL '30 days'
                ORDER BY m.match_date DESC
                LIMIT $1
            `;
            const fallbackResult = await client.query(fallbackQuery, [CONFIG.limit]);

            if (fallbackResult.rows.length === 0) {
                console.log('❌ No matches found in database!');
                console.log('💡 Tip: Run "python main.py --source fotmob --mode single --limit 5" first to populate matches.');
                return;
            }

            matches.push(...fallbackResult.rows);
        }

        console.log(`✅ Found ${matches.length} matches to process`);
        matches.forEach((m, i) => {
            console.log(`   ${i + 1}. ${m.home_team} vs ${m.away_team} (${m.league_name || 'Unknown'})`);
        });

        // Step 3: 初始化 QuantHarvester
        console.log('');
        console.log('[Step 3] Initializing QuantHarvester...');
        harvester = new QuantHarvester({
            enableProxy: CONFIG.enableProxy,
            enablePythonBridge: CONFIG.enablePythonBridge,
            logLevel: CONFIG.logLevel
        });

        await harvester.init();
        console.log('✅ QuantHarvester initialized');

        // Step 4: 批量收割
        console.log('');
        console.log('[Step 4] Starting batch harvest...');
        console.log('');

        const harvestTasks = matches.map(m => {
            const leaguePath = getLeaguePath(m.league_name);
            const homeTeam = (m.home_team || 'home').toLowerCase().replace(/\s+/g, '-');
            const awayTeam = (m.away_team || 'away').toLowerCase().replace(/\s+/g, '-');

            return {
                id: m.match_id,
                url: `https://www.oddsportal.com/football/${leaguePath}/${homeTeam}-${awayTeam}/`,
                league_name: m.league_name
            };
        });

        const results = await harvester.harvestBatch(harvestTasks);

        // Step 5: 输出结果
        console.log('');
        console.log('╔════════════════════════════════════════════════════════════════╗');
        console.log('║                    HARVEST RESULTS                            ║');
        console.log('╠════════════════════════════════════════════════════════════════╣');

        let successCount = 0;
        let failCount = 0;

        results.forEach((r, i) => {
            const status = r.success ? '✅' : '❌';
            console.log(`${status} Match ${i + 1}: ${r.matchId} - ${r.success ? 'Success' : r.error || 'Failed'} (${r.elapsed}ms)`);
            if (r.success) successCount++;
            else failCount++;
        });

        console.log('╠════════════════════════════════════════════════════════════════╣');
        console.log(`║  Total: ${results.length} | Success: ${successCount} | Failed: ${failCount}                      ║`);
        console.log('╚════════════════════════════════════════════════════════════════╝');

        // Step 6: 检查预测结果
        if (CONFIG.enablePythonBridge && successCount > 0) {
            console.log('');
            console.log('[Step 5] Checking predictions...');
            const predQuery = `
                SELECT match_id, predicted_result, final_confidence, model_version
                FROM predictions
                WHERE match_id = ANY($1)
                ORDER BY prediction_date DESC
            `;
            const predResult = await client.query(predQuery, [matches.map(m => m.match_id)]);

            if (predResult.rows.length > 0) {
                console.log('');
                console.log('📊 Predictions:');
                predResult.rows.forEach(p => {
                    console.log(`   ${p.match_id}: ${p.predicted_result.toUpperCase()} (${(p.final_confidence * 100).toFixed(1)}%) via ${p.model_version}`);
                });
            } else {
                console.log('⚠️  No predictions generated yet.');
            }
        }

        console.log('');
        console.log('✅ V171.000 Live Harvest Complete!');

    } catch (error) {
        console.error('');
        console.error('❌ FATAL ERROR:', error.message);
        console.error('Stack:', error.stack);
        process.exit(1);
    } finally {
        if (harvester) {
            await harvester.shutdown();
        }
        if (client) {
            await client.end();
        }
    }
}

// ============================================================================
// ENTRY POINT
// ============================================================================

main().catch(e => {
    console.error('Unhandled error:', e);
    process.exit(1);
});
