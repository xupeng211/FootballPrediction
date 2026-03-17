/**
 * TITAN V6.0 MAIN HARVESTER - 测绘收割一体化流水线
 * ==================================================
 * 全自动循环：Recon → Filter → Strike → Report
 * 
 * @module scripts/ops/titan_main_harvester
 * @version V6.0-PIPELINE
 * @date 2026-03-16
 */

'use strict';

const { runReconnaissance } = require('./recon_module');
const { steadyHarvest, generateReport } = require('./steady_harvester');
const { Pool } = require('pg');

// 数据库配置
const DB_CONFIG = {
  host: '127.0.0.1',
  port: 5432,
  database: 'football_db',
  user: 'football_user',
  password: process.env.DB_PASSWORD || 'football_pass',
};

/**
 * 过滤已入库场次
 */
async function filterHarvestedMatches(pool, strikeQueue) {
  console.log('\n🔄 [FILTER] 过滤已入库场次...');

  const matchIds = strikeQueue.map(t => t.match_id);

  const query = `
    SELECT match_id FROM l3_features 
    WHERE match_id = ANY($1);
  `;

  const result = await pool.query(query, [matchIds]);
  const harvestedIds = new Set(result.rows.map(r => r.match_id));

  const pending = strikeQueue.filter(t => !harvestedIds.has(t.match_id));
  const filtered = strikeQueue.filter(t => harvestedIds.has(t.match_id));

  console.log(`   📊 原队列: ${strikeQueue.length} 场`);
  console.log(`   ✅ 已入库: ${filtered.length} 场`);
  console.log(`   🎯 待收割: ${pending.length} 场`);

  return pending;
}

/**
 * 获取最新入库记录
 */
async function getLatestRecords(pool, limit = 5) {
  const query = `
    SELECT 
      m.match_id,
      m.home_team,
      m.away_team,
      m.league_name,
      l3.market_sentiment->'bet365_odds'->'closing' as bet365,
      l3.market_sentiment->'pinnacle_odds'->'closing' as pinnacle,
      l3.updated_at
    FROM l3_features l3
    JOIN matches m ON l3.match_id = m.match_id
    ORDER BY l3.updated_at DESC
    LIMIT $1;
  `;

  const result = await pool.query(query, [limit]);
  return result.rows;
}

/**
 * 显示跨联赛入库摘要
 */
function showCrossLeagueSummary(records) {
  console.log('\n📊 最新跨联赛入库记录摘要:');
  console.log('─'.repeat(90));
  console.log(`${'Match'.padEnd(40)} | ${'League'.padEnd(15)} | Bet365`);
  console.log('─'.repeat(90));

  for (const row of records) {
    const matchName = `${row.home_team} vs ${row.away_team}`.substring(0, 38).padEnd(40);
    const league = row.league_name.substring(0, 13).padEnd(15);
    const bet365 = row.bet365 ? row.bet365.join(', ') : 'N/A';
    console.log(`${matchName} | ${league} | ${bet365}`);
  }

  console.log('─'.repeat(90));
}

/**
 * 主流水线
 */
async function titanMainHarvester(options = {}) {
  const startTime = Date.now();

  console.log('\n');
  console.log('╔══════════════════════════════════════════════════════════════════════════════╗');
  console.log('║                                                                              ║');
  console.log('║     ████████╗██╗████████╗ █████╗ ███╗   ██╗    ██╗   ██╗██████╗              ║');
  console.log('║     ╚══██╔══╝██║╚══██╔══╝██╔══██╗████╗  ██║    ██║   ██║╚════██╗             ║');
  console.log('║        ██║   ██║   ██║   ███████║██╔██╗ ██║    ██║   ██║ █████╔╝             ║');
  console.log('║        ██║   ██║   ██║   ██╔══██║██║╚██╗██║    ╚██╗ ██╔╝██╔═══╝              ║');
  console.log('║        ██║   ██║   ██║   ██║  ██║██║ ╚████║     ╚████╔╝ ███████╗             ║');
  console.log('║        ╚═╝   ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═══╝      ╚═══╝  ╚══════╝             ║');
  console.log('║                                                                              ║');
  console.log('║     V6.0 MAP & HARVEST - 测绘收割一体化流水线                                ║');
  console.log('║                                                                              ║');
  console.log('╚══════════════════════════════════════════════════════════════════════════════╝');

  const pool = new Pool(DB_CONFIG);

  try {
    // ========== PHASE 1: RECON ==========
    console.log('\n' + '═'.repeat(80));
    console.log('PHASE 1: RECONNAISSANCE - 全量测绘');
    console.log('═'.repeat(80));

    const reconResult = await runReconnaissance(options);

    console.log('\n📊 测绘统计:');
    console.log(`   • 扫描联赛: ${reconResult.stats.total_leagues} 个`);
    console.log(`   • 提取URL: ${reconResult.stats.total_urls} 个`);
    console.log(`   • DB匹配: ${reconResult.stats.matched} 场`);
    console.log(`   • 未匹配: ${reconResult.stats.unmatched_count} 场`);
    console.log(`   • 覆盖率: ${reconResult.stats.coverage_rate}%`);

    if (reconResult.strikeQueue.length === 0) {
      console.log('\n⚠️  StrikeQueue为空，无待收割目标');
      return;
    }

    // ========== PHASE 2: FILTER ==========
    console.log('\n' + '═'.repeat(80));
    console.log('PHASE 2: FILTER - 去重过滤');
    console.log('═'.repeat(80));

    const pendingQueue = await filterHarvestedMatches(pool, reconResult.strikeQueue);

    if (pendingQueue.length === 0) {
      console.log('\n✅ 所有目标已入库，无需收割');
      return;
    }

    // ========== PHASE 3: STRIKE ==========
    console.log('\n' + '═'.repeat(80));
    console.log('PHASE 3: STRIKE - 稳健收割');
    console.log('═'.repeat(80));

    const strikeOptions = {
      headless: options.headless !== false,
      maxMatches: options.maxMatches || pendingQueue.length
    };

    // 限制数量
    const limitedQueue = pendingQueue.slice(0, strikeOptions.maxMatches);
    console.log(`\n🎯 实际收割目标: ${limitedQueue.length} 场`);

    const stats = await steadyHarvest(limitedQueue, strikeOptions);

    // ========== PHASE 4: REPORT ==========
    console.log('\n' + '═'.repeat(80));
    console.log('PHASE 4: REPORT - 战报生成');
    console.log('═'.repeat(80));

    const finalStats = generateReport(stats);

    // 显示最新入库记录
    const latestRecords = await getLatestRecords(pool, 5);
    showCrossLeagueSummary(latestRecords);

    // 总体统计
    const totalDuration = Date.now() - startTime;
    console.log('\n╔══════════════════════════════════════════════════════════════════╗');
    console.log('║     🏆 TITAN V6.0 PIPELINE - 全流程战报 🏆                     ║');
    console.log('╠══════════════════════════════════════════════════════════════════╣');
    console.log(`║     🔍 测绘覆盖率: ${String(reconResult.stats.coverage_rate).padStart(5)}%                              ║`);
    console.log(`║     ✅ 收割成功率: ${String(finalStats.metrics.realSuccessRate.toFixed(1)).padStart(5)}% (去除网络因素)          ║`);
    console.log(`║     🚫 404错误率: ${String(finalStats.metrics.notFoundRate.toFixed(1)).padStart(5)}%                               ║`);
    console.log(`║                                                                  ║`);
    console.log(`║     ⏱️  总耗时: ${String((totalDuration / 1000 / 60).toFixed(1)).padStart(4)} 分钟                            ║`);
    console.log('╚══════════════════════════════════════════════════════════════════╝\n');

    return {
      recon: reconResult,
      strike: finalStats,
      latestRecords
    };

  } catch (error) {
    console.error('\n💥 PIPELINE ERROR:', error.message);
    console.error(error.stack);
    throw error;
  } finally {
    await pool.end();
  }
}

// CLI入口
if (require.main === module) {
  const args = process.argv.slice(2);
  const options = {
    headless: !args.includes('--gui'),
    maxMatches: args.includes('--limit') ? parseInt(args[args.indexOf('--limit') + 1]) : undefined
  };

  titanMainHarvester(options).then(() => {
    console.log('✅ PIPELINE COMPLETE');
    process.exit(0);
  }).catch(err => {
    console.error('💥 PIPELINE FAILED:', err);
    process.exit(1);
  });
}

module.exports = { titanMainHarvester };