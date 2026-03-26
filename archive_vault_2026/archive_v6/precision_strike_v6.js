/**
 * TITAN V6.0 PRECISION STRIKE V6 - 侦察打击一体化精确打击
 * =========================================================
 * 使用真实侦察到的URL进行精确打击，验证0% 404错误率目标
 * 
 * @module scripts/ops/precision_strike_v6
 * @version V6.0-PRECISION-STRIKE
 * @date 2026-03-16
 */

'use strict';

const { chromium } = require('playwright');
const { Pool } = require('pg');
const fs = require('fs');
const path = require('path');

// 载入模块化组件
const {
  silentHarvestLoop,
  healVision,
  checkPageHealth
} = require('../../src/infrastructure/harvesters/StealthNavigator');

const {
  extractOddsFromDOM,
  buildMarketSentiment
} = require('../../src/infrastructure/harvesters/OddsPortalParser');

// 数据库配置
const DB_CONFIG = {
  host: '127.0.0.1',
  port: 5432,
  database: 'football_db',
  user: 'football_user',
  password: process.env.DB_PASSWORD || 'football_pass',
};

// 基于真实侦察的StrikeMap（之前recon_fixtures.js侦察到的真实URL）
const STRIKE_MAP = {
  // 之前成功侦察到的真实URL（带hash）
  '54_20232024_4829555': {
    match_name: 'RB Leipzig vs Hoffenheim',
    league: 'Bundesliga',
    url: 'https://www.oddsportal.com/football/germany/bundesliga/rb-leipzig-hoffenheim-SrS8qyAO/',
    hash: 'SrS8qyAO'
  },
  '54_20232024_4829552': {
    match_name: '1. FC Köln vs Borussia Mönchengladbach',
    league: 'Bundesliga',
    url: 'https://www.oddsportal.com/football/germany/bundesliga/1-fc-koln-b-monchengladbach-CYEFuS8j/',
    hash: 'CYEFuS8j'
  },
  '54_20232024_4829550': {
    match_name: 'Bayern München vs Union Berlin',
    league: 'Bundesliga',
    url: 'https://www.oddsportal.com/football/germany/bundesliga/bayern-munich-union-berlin-hj5ikutm/',
    hash: 'hj5ikutm'
  },
  // 使用之前NIGHT RAID成功的英超URL
  '47_20232024_4813679': {
    match_name: 'Fulham vs Burnley',
    league: 'Premier League',
    url: 'https://www.oddsportal.com/football/england/premier-league/fulham-burnley-8EamNN8b/',
    hash: '8EamNN8b'
  },
  '47_20232024_4813666': {
    match_name: 'Brentford vs Wolverhampton Wanderers',
    league: 'Premier League',
    url: 'https://www.oddsportal.com/football/england/premier-league/brentford-wolves-0jR7cwU6/',
    hash: '0jR7cwU6'
  },
  '47_20232024_4813675': {
    match_name: 'AFC Bournemouth vs Manchester United',
    league: 'Premier League',
    url: 'https://www.oddsportal.com/football/england/premier-league/bournemouth-manchester-united-QZ5U62OH/',
    hash: 'QZ5U62OH'
  },
  '47_20232024_4813676': {
    match_name: 'Brighton & Hove Albion vs Liverpool',
    league: 'Premier League',
    url: 'https://www.oddsportal.com/football/england/premier-league/brighton-liverpool-bm4x5tgU/',
    hash: 'bm4x5tgU'
  },
  '47_20232024_4813677': {
    match_name: 'Crystal Palace vs Leeds',
    league: 'Premier League',
    url: 'https://www.oddsportal.com/football/england/premier-league/crystal-palace-leeds-0EuWc7um/',
    hash: '0EuWc7um'
  },
  '47_20232024_4813678': {
    match_name: 'Everton vs Chelsea',
    league: 'Premier League',
    url: 'https://www.oddsportal.com/football/england/premier-league/everton-chelsea-A7YyVJiS/',
    hash: 'A7YyVJiS'
  },
  '47_20232024_4813680': {
    match_name: 'Aston Villa vs West Ham',
    league: 'Premier League',
    url: 'https://www.oddsportal.com/football/england/premier-league/aston-villa-west-ham-IFxl2UgH/',
    hash: 'IFxl2UgH'
  }
};

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

    const result = await pool.query(query, [
      matchId,
      JSON.stringify(marketSentiment)
    ]);

    return result.rows.length > 0;
  } catch (error) {
    console.error(`   ❌ 入库失败: ${error.message}`);
    return false;
  }
}

/**
 * 精确打击主函数
 */
async function precisionStrikeV6() {
  console.log('\n╔══════════════════════════════════════════════════════════════════╗');
  console.log('║     🎯 TITAN V6.0 PRECISION STRIKE V6 - 精确打击 🎯            ║');
  console.log('║     使用真实侦察URL，0% 404错误率目标                          ║');
  console.log('╚══════════════════════════════════════════════════════════════════╝\n');

  const pool = new Pool(DB_CONFIG);
  let browser = null;
  let context = null;

  // 统计
  const stats = {
    total: Object.keys(STRIKE_MAP).length,
    success: 0,
    failed: 0,
    notFound404: 0,
    titleLoaded: 0,
    healingTriggered: 0,
    healingSuccess: 0,
    startTime: Date.now()
  };

  try {
    // 加载黄金会话
    const sessionPath = path.join(process.cwd(), 'data/sessions/auth_gold.json');
    let sessionData = null;
    try {
      sessionData = JSON.parse(fs.readFileSync(sessionPath, 'utf-8'));
      console.log('✅ 已加载黄金会话\n');
    } catch (e) {
      console.log('⚠️  未找到黄金会话\n');
    }

    // 启动浏览器
    console.log('🚀 启动浏览器...');
    browser = await chromium.launch({
      headless: false,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--window-size=1920,1080',
        '--disable-blink-features=AutomationControlled'
      ]
    });

    const contextConfig = {
      viewport: { width: 1920, height: 1080 },
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      locale: 'en-US',
      timezoneId: 'America/New_York'
    };

    if (sessionData) {
      contextConfig.storageState = sessionData;
    }

    context = await browser.newContext(contextConfig);
    const page = await context.newPage();

    // 注入stealth脚本
    await context.addInitScript(() => {
      Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
      Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    });

    // 循环打击
    let idx = 0;
    for (const [matchId, target] of Object.entries(STRIKE_MAP)) {
      idx++;
      console.log('\n' + '='.repeat(70));
      console.log(`[${idx}/${stats.total}] 🎯 ${target.match_name}`);
      console.log(`     🏆 League: ${target.league}`);
      console.log(`     🆔 Match ID: ${matchId}`);
      console.log(`     🔗 URL Hash: ${target.hash}`);
      console.log('='.repeat(70));

      let pageLoaded = false;
      let pageTitle = '';

      try {
        // 导航到比赛页面
        console.log('\n🌐 正在加载页面...');
        console.log(`   URL: ${target.url}`);
        
        const response = await page.goto(target.url, { 
          waitUntil: 'load', 
          timeout: 60000 
        });

        // 检查404
        if (response && response.status() === 404) {
          console.log('   ❌ 404错误 - 页面不存在');
          stats.notFound404++;
          stats.failed++;
          continue;
        }

        pageLoaded = true;
        pageTitle = await page.title();
        console.log(`   ✅ 页面加载完成`);
        console.log(`   📄 页面标题: ${pageTitle}`);
        stats.titleLoaded++;

        // 执行静默收割循环
        const parser = { extractOddsFromDOM, buildMarketSentiment };
        const result = await silentHarvestLoop(page, context, sessionData, parser);

        // 记录康复统计
        if (result.healingTriggered) {
          stats.healingTriggered++;
          if (result.success) {
            stats.healingSuccess++;
          }
        }

        // 验证并入库
        if (result.success && result.data) {
          const hasValidData = (result.data.pinnacle_odds?.closing?.length === 3) ||
                               (result.data.bet365_odds?.closing?.length === 3);

          if (hasValidData) {
            const upsertResult = await upsertToDatabase(pool, matchId, result.data);

            if (upsertResult) {
              stats.success++;
              const bet365Odds = result.data.bet365_odds?.closing?.join(', ') || 'N/A';
              const pinnacleOdds = result.data.pinnacle_odds?.closing?.join(', ') || 'N/A';

              console.log(`\n💎 [GOLD ACQUIRED] ${target.match_name}`);
              console.log(`     Bet365: [${bet365Odds}]`);
              console.log(`     Pinnacle: [${pinnacleOdds}]`);
              console.log(`     Healing: ${result.healingTriggered ? 'Yes' : 'No'}`);
            } else {
              console.log(`   ❌ 数据库入库失败`);
              stats.failed++;
            }
          } else {
            console.log(`   ❌ 数据验证失败`);
            stats.failed++;
          }
        } else {
          console.log(`   ❌ 静默收割失败`);
          stats.failed++;
        }

      } catch (error) {
        console.log(`   💥 错误: ${error.message}`);
        if (error.message.includes('404')) {
          stats.notFound404++;
        }
        stats.failed++;
      }

      // 间隔
      if (idx < stats.total) {
        const delay = 3000 + Math.floor(Math.random() * 2000);
        console.log(`\n⏱️  等待 ${delay}ms 后下一场...`);
        await new Promise(r => setTimeout(r, delay));
      }
    }

    // 生成战报
    const totalDuration = Date.now() - stats.startTime;
    const notFoundRate = ((stats.notFound404 / stats.total) * 100).toFixed(1);
    const titleSuccessRate = ((stats.titleLoaded / stats.total) * 100).toFixed(1);
    const healingSuccessRate = stats.healingTriggered > 0
      ? ((stats.healingSuccess / stats.healingTriggered) * 100).toFixed(1)
      : 0;

    console.log('\n\n╔══════════════════════════════════════════════════════════════════╗');
    console.log('║     🎯 PRECISION STRIKE V6 - 精确打击战报 🎯                   ║');
    console.log('╠══════════════════════════════════════════════════════════════════╣');
    console.log(`║     📋 总打击数: ${String(stats.total).padStart(2)}                                            ║`);
    console.log(`║     ✅ 成功入库: ${String(stats.success).padStart(2)}                                            ║`);
    console.log(`║     ❌ 失败: ${String(stats.failed).padStart(2)}                                                ║`);
    console.log(`║     📈 成功率: ${String(((stats.success / stats.total) * 100).toFixed(1)).padStart(5)}%                                      ║`);
    console.log(`║                                                                  ║`);
    console.log(`║     🚫 404错误: ${String(stats.notFound404).padStart(2)} 次 (${String(notFoundRate).padStart(5)}%)                                ║`);
    console.log(`║     📄 标题加载: ${String(stats.titleLoaded).padStart(2)}/${String(stats.total).padStart(2)} (${String(titleSuccessRate).padStart(5)}%)                           ║`);
    console.log(`║                                                                  ║`);
    console.log(`║     🏥 视觉康复触发: ${String(stats.healingTriggered).padStart(2)} 次                                ║`);
    console.log(`║     🏥 康复成功: ${String(stats.healingSuccess).padStart(2)} 次                                    ║`);
    console.log(`║     🏥 康复成功率: ${String(healingSuccessRate).padStart(5)}%                                  ║`);
    console.log(`║                                                                  ║`);
    console.log(`║     ⏱️  总耗时: ${String((totalDuration / 1000).toFixed(1)).padStart(5)} 秒                                   ║`);
    console.log('╠══════════════════════════════════════════════════════════════════╣');

    if (parseFloat(notFoundRate) === 0 && parseFloat(titleSuccessRate) === 100) {
      console.log('║     ✅ 目标达成: 404错误率0%，标题加载率100%                   ║');
      console.log('║     ✅ 精确打击成功！可启动大规模总攻                          ║');
    } else {
      console.log('║     ⚠️  目标未达成: 需要进一步优化                             ║');
    }

    console.log('╚══════════════════════════════════════════════════════════════════╝\n');

    // 显示最新记录
    await showLatestRecord(pool);

  } catch (error) {
    console.error('\n💥 全局异常:', error.message);
  } finally {
    if (context) await context.close();
    if (browser) await browser.close();
    await pool.end();
  }
}

/**
 * 显示最新记录
 */
async function showLatestRecord(pool) {
  try {
    const query = `
      SELECT 
        m.match_id,
        m.home_team,
        m.away_team,
        m.league_name,
        l3.market_sentiment->'bet365_odds'->'closing' as bet365,
        l3.updated_at
      FROM l3_features l3
      JOIN matches m ON l3.match_id = m.match_id
      ORDER BY l3.updated_at DESC
      LIMIT 1;
    `;

    const result = await pool.query(query);
    if (result.rows.length > 0) {
      const row = result.rows[0];
      console.log('📊 最新入库记录:');
      console.log('─'.repeat(70));
      console.log(`   Match ID: ${row.match_id}`);
      console.log(`   Match: ${row.home_team} vs ${row.away_team}`);
      console.log(`   League: ${row.league_name}`);
      console.log(`   Bet365: ${row.bet365 ? row.bet365.join(', ') : 'N/A'}`);
      console.log(`   时间: ${row.updated_at}`);
      console.log('─'.repeat(70) + '\n');
    }
  } catch (e) {
    // ignore
  }
}

// 运行
if (require.main === module) {
  precisionStrikeV6().then(() => {
    process.exit(0);
  }).catch(err => {
    console.error(err);
    process.exit(1);
  });
}

module.exports = { precisionStrikeV6 };