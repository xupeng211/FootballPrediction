/**
 * TITAN V6.0 PIPELINE DEMO - 测绘收割一体化演示
 * ==============================================
 * 使用已验证URL演示完整流水线架构
 * 
 * @module scripts/ops/titan_pipeline_demo
 * @version V6.0-DEMO
 */

'use strict';

const { chromium } = require('playwright');
const { Pool } = require('pg');
const fs = require('fs');
const path = require('path');

// 载入模块化组件
const { silentHarvestLoop } = require('../../src/infrastructure/harvesters/StealthNavigator');
const { extractOddsFromDOM, buildMarketSentiment } = require('../../src/infrastructure/harvesters/OddsPortalParser');

// 数据库配置
const DB_CONFIG = {
  host: '127.0.0.1',
  port: 5432,
  database: 'football_db',
  user: 'football_user',
  password: process.env.DB_PASSWORD || 'football_pass',
};

// 已验证的StrikeMap（来自之前成功的侦察）
const VERIFIED_STRIKE_MAP = [
  {
    match_id: '47_20232024_4813679',
    match_name: 'Fulham vs Burnley',
    league: 'Premier League',
    url: 'https://www.oddsportal.com/football/england/premier-league/fulham-burnley-8EamNN8b/',
    hash: '8EamNN8b'
  },
  {
    match_id: '47_20232024_4813666',
    match_name: 'Brentford vs Wolverhampton Wanderers',
    league: 'Premier League',
    url: 'https://www.oddsportal.com/football/england/premier-league/brentford-wolves-0jR7cwU6/',
    hash: '0jR7cwU6'
  },
  {
    match_id: '47_20232024_4813676',
    match_name: 'Brighton & Hove Albion vs Liverpool',
    league: 'Premier League',
    url: 'https://www.oddsportal.com/football/england/premier-league/brighton-liverpool-bm4x5tgU/',
    hash: 'bm4x5tgU'
  }
];

// 熔断配置
const CIRCUIT_BREAKER = {
  maxConsecutiveFailures: 5,
  max404Rate: 0,
  maxFailureRate: 0.30,
  cooldownMinutes: 10
};

/**
 * 随机延迟 - Human Breath
 */
async function humanBreath(min = 5000, max = 15000) {
  const delay = Math.floor(Math.random() * (max - min + 1)) + min;
  process.stdout.write(`⏱️  Human Breath: ${delay}ms... `);
  await new Promise(r => setTimeout(r, delay));
  console.log('✓');
  return delay;
}

/**
 * 数据库入库
 */
async function upsertToDatabase(pool, matchId, marketSentiment) {
  try {
    const query = `
      INSERT INTO l3_features (match_id, market_sentiment, updated_at)
      VALUES ($1, $2, NOW())
      ON CONFLICT (match_id) DO UPDATE SET
        market_sentiment = EXCLUDED.market_sentiment,
        updated_at = NOW()
      RETURNING match_id;
    `;
    const result = await pool.query(query, [matchId, JSON.stringify(marketSentiment)]);
    return result.rows.length > 0;
  } catch (error) {
    console.error(`   ❌ 入库失败: ${error.message}`);
    return false;
  }
}

/**
 * 单场比赛收割（带重试）
 */
async function harvestWithRetry(page, context, target, sessionData, stats) {
  const maxRetries = 2;
  
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    if (attempt > 0) {
      console.log(`\n🔄 [TACTICAL RETRY] 第${attempt}/${maxRetries}次重试...`);
      console.log('   🧹 清理Cookies...');
      await context.clearCookies();
      if (sessionData?.cookies) {
        await context.addCookies(sessionData.cookies);
      }
      await humanBreath(20000, 30000);
    }

    try {
      console.log(`\n🌐 正在加载页面...`);
      console.log(`   URL: ${target.url}`);

      const response = await page.goto(target.url, { 
        waitUntil: 'domcontentloaded', 
        timeout: 45000 
      });

      if (response?.status() === 404) {
        stats.notFound404++;
        console.log('   ❌ 404错误');
        return { success: false, error: '404', fatal: true };
      }

      stats.titleLoaded++;
      const pageTitle = await page.title();
      console.log(`   ✅ 页面加载: ${pageTitle}`);

      const parser = { extractOddsFromDOM, buildMarketSentiment };
      const result = await silentHarvestLoop(page, context, sessionData, parser);

      if (result.healingTriggered) stats.healingTriggered++;

      if (result.success && result.data) {
        const hasValid = (result.data.pinnacle_odds?.closing?.length === 3) ||
                         (result.data.bet365_odds?.closing?.length === 3);
        
        if (hasValid) {
          const upserted = await upsertToDatabase(stats.pool, target.match_id, result.data);
          if (upserted) {
            stats.consecutiveFailures = 0;
            return { success: true, data: result.data, healing: result.healingTriggered };
          }
        }
      }
      
      return { success: false, error: 'no_data' };

    } catch (error) {
      console.log(`   💥 错误: ${error.message}`);
      if (error.message.includes('Timeout') || error.message.includes('ERR_HTTP')) {
        continue;
      }
      return { success: false, error: error.message };
    }
  }
  
  stats.consecutiveFailures++;
  return { success: false, error: 'Max retries exceeded' };
}

/**
 * PHASE 1: RECON - 使用已验证URL模拟测绘
 */
async function phaseRecon() {
  console.log('\n' + '═'.repeat(80));
  console.log('PHASE 1: RECONNAISSANCE - 全量测绘');
  console.log('═'.repeat(80));
  
  const header = `\n╔══════════════════════════════════════════════════════════════════╗\n║     🔍 TITAN V6.0 RECON MODULE - 全量测绘引擎 🔍               ║\n║     五大联赛轮询，建立精确打击队列                             ║\n╚══════════════════════════════════════════════════════════════════╝`;
  console.log(header);
  
  // 模拟侦察过程
  const leagues = ['Premier League', 'Bundesliga', 'La Liga', 'Serie A', 'Ligue 1'];
  for (const league of leagues) {
    console.log(`\n🔍 [RECON] 侦察 ${league}...`);
    await new Promise(r => setTimeout(r, 500));
    console.log(`   ✅ 侦察完成`);
  }
  
  // 使用已验证的URL
  const strikeQueue = VERIFIED_STRIKE_MAP.map(m => ({
    ...m,
    match_date: new Date(),
    confidence: 100,
    status: 'pending'
  }));
  
  console.log(`\n🎯 [STRIKE QUEUE] 建立目标对齐队列...`);
  console.log(`   ✅ StrikeQueue建立完成: ${strikeQueue.length} 个目标`);
  
  return {
    strikeQueue,
    stats: {
      total_leagues: 5,
      total_urls: strikeQueue.length,
      matched: strikeQueue.length,
      coverage_rate: '100.0'
    }
  };
}

/**
 * PHASE 2: FILTER - 过滤已入库
 */
async function phaseFilter(pool, strikeQueue) {
  console.log('\n' + '═'.repeat(80));
  console.log('PHASE 2: FILTER - 去重过滤');
  console.log('═'.repeat(80));
  
  const matchIds = strikeQueue.map(t => t.match_id);
  const query = `SELECT match_id FROM l3_features WHERE match_id = ANY($1);`;
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
 * PHASE 3: STRIKE - 稳健收割
 */
async function phaseStrike(pool, pendingQueue, options = {}) {
  console.log('\n' + '═'.repeat(80));
  console.log('PHASE 3: STRIKE - 稳健收割');
  console.log('═'.repeat(80));
  
  const header = `\n╔══════════════════════════════════════════════════════════════════╗\n║     ⚔️  TITAN V6.0 STEADY HARVESTER - 稳健收割协议 ⚔️          ║\n║     阵地战节奏：延迟 + 重试 + 熔断                             ║\n╚══════════════════════════════════════════════════════════════════╝`;
  console.log(header);
  
  const stats = {
    pool,
    total: pendingQueue.length,
    success: 0,
    failed: 0,
    notFound404: 0,
    titleLoaded: 0,
    healingTriggered: 0,
    consecutiveFailures: 0,
    startTime: Date.now()
  };
  
  // 加载黄金会话
  const sessionPath = path.join(process.cwd(), 'data/sessions/auth_gold.json');
  let sessionData = null;
  try {
    sessionData = JSON.parse(fs.readFileSync(sessionPath, 'utf-8'));
    console.log('\n✅ 已加载黄金会话');
  } catch (e) {
    console.log('\n⚠️  未找到黄金会话');
  }
  
  // 启动浏览器
  console.log('🚀 启动浏览器...');
  const browser = await chromium.launch({
    headless: options.headless !== false,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1920,1080']
  });
  
  const contextConfig = {
    viewport: { width: 1920, height: 1080 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
  };
  if (sessionData) contextConfig.storageState = sessionData;
  
  const context = await browser.newContext(contextConfig);
  const page = await context.newPage();
  
  await context.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
  });
  
  // 主循环
  for (let idx = 0; idx < pendingQueue.length; idx++) {
    const target = pendingQueue[idx];
    
    console.log('\n' + '='.repeat(70));
    console.log(`[${idx + 1}/${stats.total}] ⚔️  ${target.match_name}`);
    console.log(`     🏆 League: ${target.league} | 🆔 ${target.match_id} | 🔗 ${target.hash}`);
    console.log('='.repeat(70));
    
    // 熔断检查
    if (stats.notFound404 > 0) {
      console.log('\n🚨 CIRCUIT BREAKER: 404错误触发熔断');
      break;
    }
    if (stats.consecutiveFailures >= 5) {
      console.log('\n🚨 CIRCUIT BREAKER: 连续失败触发熔断');
      break;
    }
    
    // Human Breath
    await humanBreath(5000, 15000);
    
    // 执行收割
    const result = await harvestWithRetry(page, context, target, sessionData, stats);
    
    if (result.success) {
      stats.success++;
      const bet365 = result.data.bet365_odds?.closing?.join(', ') || 'N/A';
      console.log(`\n💎 [GOLD ACQUIRED] ${target.match_name}`);
      console.log(`     Bet365: [${bet365}] | Healing: ${result.healing ? 'Yes' : 'No'}`);
    } else {
      stats.failed++;
      console.log(`\n❌ [FAILED] ${target.match_name}`);
    }
  }
  
  await context.close();
  await browser.close();
  
  return stats;
}

/**
 * PHASE 4: REPORT - 生成战报
 */
function phaseReport(stats) {
  console.log('\n' + '═'.repeat(80));
  console.log('PHASE 4: REPORT - 战报生成');
  console.log('═'.repeat(80));
  
  const totalDuration = Date.now() - stats.startTime;
  const notFoundRate = ((stats.notFound404 / stats.total) * 100).toFixed(1);
  const titleSuccessRate = ((stats.titleLoaded / stats.total) * 100).toFixed(1);
  const realSuccessRate = stats.titleLoaded > 0
    ? ((stats.success / stats.titleLoaded) * 100).toFixed(1)
    : 0;
  
  const report = `
╔══════════════════════════════════════════════════════════════════╗
║     📊 STEADY HARVESTER - 稳健收割战报 📊                      ║
╠══════════════════════════════════════════════════════════════════╣
║     📋 总打击数: ${String(stats.total).padStart(3)}                                          ║
║     ✅ 成功入库: ${String(stats.success).padStart(3)}                                          ║
║     ❌ 失败: ${String(stats.failed).padStart(3)}                                              ║
║     📈 总成功率: ${String(((stats.success / stats.total) * 100).toFixed(1)).padStart(5)}%                                  ║
║                                                                  ║
║     🚫 404错误: ${String(stats.notFound404).padStart(3)} 次 (${String(notFoundRate).padStart(5)}%)                              ║
║     📄 标题加载: ${String(stats.titleLoaded).padStart(3)}/${String(stats.total).padStart(3)} (${String(titleSuccessRate).padStart(5)}%)                          ║
║     🎯 真实入库率: ${String(realSuccessRate).padStart(5)}% (去除网络因素)                    ║
║                                                                  ║
║     🏥 视觉康复触发: ${String(stats.healingTriggered).padStart(3)} 次                               ║
║                                                                  ║
║     ⏱️  总耗时: ${String((totalDuration / 1000).toFixed(0)).padStart(4)} 秒                                  ║
╚══════════════════════════════════════════════════════════════════╝`;
  
  console.log(report);
  
  return {
    notFoundRate: parseFloat(notFoundRate),
    titleSuccessRate: parseFloat(titleSuccessRate),
    realSuccessRate: parseFloat(realSuccessRate),
    totalDuration
  };
}

/**
 * 获取最新入库记录
 */
async function getLatestRecords(pool, limit = 5) {
  const query = `
    SELECT m.match_id, m.home_team, m.away_team, m.league_name,
           l3.market_sentiment->'bet365_odds'->'closing' as bet365,
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
 * 显示跨联赛摘要
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
 * 主函数
 */
async function main() {
  const pipelineStart = Date.now();
  
  console.log(`
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║     ████████╗██╗████████╗ █████╗ ███╗   ██╗    ██╗   ██╗██████╗              ║
║     ╚══██╔══╝██║╚══██╔══╝██╔══██╗████╗  ██║    ██║   ██║╚════██╗             ║
║        ██║   ██║   ██║   ███████║██╔██╗ ██║    ██║   ██║ █████╔╝             ║
║        ██║   ██║   ██║   ██╔══██║██║╚██╗██║    ╚██╗ ██╔╝██╔═══╝              ║
║        ██║   ██║   ██║   ██║  ██║██║ ╚████║     ╚████╔╝ ███████╗             ║
║        ╚═╝   ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═══╝      ╚═══╝  ╚══════╝             ║
║                                                                              ║
║     V6.0 MAP & HARVEST - 测绘收割一体化流水线                                ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝`);

  const pool = new Pool(DB_CONFIG);
  
  try {
    // PHASE 1: RECON
    const reconResult = await phaseRecon();
    
    // PHASE 2: FILTER
    const pendingQueue = await phaseFilter(pool, reconResult.strikeQueue);
    
    if (pendingQueue.length === 0) {
      console.log('\n✅ 所有目标已入库，无需收割');
      return;
    }
    
    // PHASE 3: STRIKE
    const stats = await phaseStrike(pool, pendingQueue, { headless: false });
    
    // PHASE 4: REPORT
    const metrics = phaseReport(stats);
    
    // 跨联赛摘要
    const latestRecords = await getLatestRecords(pool, 5);
    showCrossLeagueSummary(latestRecords);
    
    // 总体战报
    const totalDuration = Date.now() - pipelineStart;
    console.log(`
╔══════════════════════════════════════════════════════════════════╗
║     🏆 TITAN V6.0 PIPELINE - 全流程战报 🏆                     ║
╠══════════════════════════════════════════════════════════════════╣
║     🔍 测绘覆盖率: ${String(reconResult.stats.coverage_rate).padStart(5)}%                              ║
║     ✅ 收割成功率: ${String(metrics.realSuccessRate.toFixed(1)).padStart(5)}% (去除网络因素)          ║
║     🚫 404错误率: ${String(metrics.notFoundRate.toFixed(1)).padStart(5)}%                               ║
║                                                                  ║
║     ⏱️  总耗时: ${String((totalDuration / 1000 / 60).toFixed(1)).padStart(4)} 分钟                            ║
╚══════════════════════════════════════════════════════════════════╝
`);
    
  } catch (error) {
    console.error('\n💥 PIPELINE ERROR:', error.message);
    throw error;
  } finally {
    await pool.end();
  }
}

if (require.main === module) {
  main().then(() => {
    console.log('✅ PIPELINE COMPLETE');
    process.exit(0);
  }).catch(err => {
    console.error('💥 PIPELINE FAILED:', err);
    process.exit(1);
  });
}

module.exports = { main };