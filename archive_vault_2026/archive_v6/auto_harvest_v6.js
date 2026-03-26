/**
 * TITAN V6.0 AUTO HARVEST V6 - 无人值守自动收割
 * ===============================================
 * 基于 StealthNavigator VISION-HEALING 的静默收割协议
 * 
 * @module scripts/ops/auto_harvest_v6
 * @version V6.0-AUTO-HARVEST
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
  STATUS_HEALTHY,
  STATUS_BLIND
} = require('../../src/infrastructure/harvesters/StealthNavigator');

const {
  deepParseOddsData,
  extractOddsFromDOM,
  buildMarketSentiment,
  extractOddsArrays
} = require('../../src/infrastructure/harvesters/OddsPortalParser');

// 数据库配置
const DB_CONFIG = {
  host: '127.0.0.1',
  port: 5432,
  database: 'football_db',
  user: 'football_user',
  password: process.env.DB_PASSWORD || 'football_pass',
};

// 10场英超比赛目标
const TARGET_MATCHES = [
  { match_id: '47_20232024_4813679', url: 'https://www.oddsportal.com/football/england/premier-league/fulham-burnley-8EamNN8b/', name: 'Fulham vs Burnley' },
  { match_id: '47_20232024_4813666', url: 'https://www.oddsportal.com/football/england/premier-league/brentford-wolves-0jR7cwU6/', name: 'Brentford vs Wolves' },
  { match_id: '47_20232024_4813675', url: 'https://www.oddsportal.com/football/england/premier-league/bournemouth-manchester-united-QZ5U62OH/', name: 'Bournemouth vs Man United' },
  { match_id: '47_20232024_4813676', url: 'https://www.oddsportal.com/football/england/premier-league/brighton-liverpool-bm4x5tgU/', name: 'Brighton vs Liverpool' },
  { match_id: '47_20232024_4813677', url: 'https://www.oddsportal.com/football/england/premier-league/crystal-palace-leeds-0EuWc7um/', name: 'Crystal Palace vs Leeds' },
];

// 熔断配置
const CIRCUIT_BREAKER_THRESHOLD = 3; // 连续3场失败则熔断

/**
 * 无人值守全自动收割主函数
 */
async function autoHarvestV6() {
  console.log('\n╔══════════════════════════════════════════════════════════════════╗');
  console.log('║     🌙 TITAN V6.0 NIGHT RAID - 无人值守全自动收割 🌙           ║');
  console.log('║     自愈系统在线，开始搬运金砖                                 ║');
  console.log('╚══════════════════════════════════════════════════════════════════╝\n');

  console.log('🔧 配置信息:');
  console.log(`   📡 DB: ${DB_CONFIG.host}:${DB_CONFIG.port}/${DB_CONFIG.database}`);
  console.log(`   🎯 目标: ${TARGET_MATCHES.length} 场英超比赛`);
  console.log(`   🎭 Mode: headless=false (可见窗口)`);
  console.log(`   🔒 熔断阈值: 连续 ${CIRCUIT_BREAKER_THRESHOLD} 场失败即退出\n`);

  let browser = null;
  let context = null;
  const pool = new Pool(DB_CONFIG);

  // 统计数据
  const stats = {
    total: TARGET_MATCHES.length,
    success: 0,
    failed: 0,
    healingTriggered: 0,
    healingSuccess: 0,
    consecutiveFailures: 0,
    startTime: Date.now()
  };

  try {
    // 加载黄金会话
    const sessionPath = path.join(process.cwd(), 'data/sessions/auth_gold.json');
    let sessionData = null;
    try {
      sessionData = JSON.parse(fs.readFileSync(sessionPath, 'utf-8'));
      console.log('✅ 已加载黄金会话');
      console.log(`   🍪 Cookies: ${sessionData.cookies?.length || 0} 个\n`);
    } catch (e) {
      console.log('⚠️  未找到黄金会话，将使用新会话\n');
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

    // 循环处理每场比赛
    for (let i = 0; i < TARGET_MATCHES.length; i++) {
      const match = TARGET_MATCHES[i];
      
      console.log('\n' + '='.repeat(70));
      console.log(`[${i + 1}/${TARGET_MATCHES.length}] 🎯 ${match.name}`);
      console.log(`     🆔 Match ID: ${match.match_id}`);
      console.log('='.repeat(70));

      try {
        // 导航到比赛页面
        console.log('\n🌐 正在加载页面...');
        await page.goto(match.url, { 
          waitUntil: 'load', 
          timeout: 120000 
        });
        console.log('   ✅ 页面加载完成');

        // 执行静默收割循环
        const parser = {
          extractOddsFromDOM,
          buildMarketSentiment
        };
        
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
          const hasValidData = (result.data.pinnacle_odds && result.data.pinnacle_odds.closing && result.data.pinnacle_odds.closing.length === 3) ||
                               (result.data.bet365_odds && result.data.bet365_odds.closing && result.data.bet365_odds.closing.length === 3);
          
          if (hasValidData) {
            // 执行入库
            const upsertResult = await upsertToDatabase(pool, match.match_id, result.data);
            
            if (upsertResult) {
              stats.success++;
              stats.consecutiveFailures = 0; // 重置连续失败计数
              
              const bet365Odds = result.data.bet365_odds?.closing?.join(', ') || 'N/A';
              const pinnacleOdds = result.data.pinnacle_odds?.closing?.join(', ') || 'N/A';
              
              console.log(`\n💎 [GOLD ACQUIRED] Match: ${match.name}`);
              console.log(`     Bet365: [${bet365Odds}]`);
              console.log(`     Pinnacle: [${pinnacleOdds}]`);
              console.log(`     Healing: ${result.healingTriggered ? 'Yes' : 'No'}`);
            } else {
              console.log(`   ❌ 数据库入库失败`);
              stats.failed++;
              stats.consecutiveFailures++;
            }
          } else {
            console.log(`   ❌ 数据验证失败，赔率数组长度不为3`);
            stats.failed++;
            stats.consecutiveFailures++;
          }
        } else {
          console.log(`   ❌ 静默收割失败，未能获取有效数据`);
          stats.failed++;
          stats.consecutiveFailures++;
        }

        // 熔断检查
        if (stats.consecutiveFailures >= CIRCUIT_BREAKER_THRESHOLD) {
          console.log('\n💥 💥 💥 熔断触发！💥 💥 💥');
          console.log(`   连续 ${CIRCUIT_BREAKER_THRESHOLD} 场比赛失败`);
          console.log('   对方防线全面升级，任务终止！');
          break;
        }

        // 比赛间延迟
        if (i < TARGET_MATCHES.length - 1) {
          const delay = 3000 + Math.floor(Math.random() * 2000);
          console.log(`\n⏱️  等待 ${delay}ms 后处理下一场...`);
          await new Promise(r => setTimeout(r, delay));
        }

      } catch (error) {
        console.log(`   💥 处理异常: ${error.message}`);
        stats.failed++;
        stats.consecutiveFailures++;
      }
    }

    // 最终统计
    const totalDuration = Date.now() - stats.startTime;
    const healingSuccessRate = stats.healingTriggered > 0 
      ? ((stats.healingSuccess / stats.healingTriggered) * 100).toFixed(1) 
      : 0;

    console.log('\n\n╔══════════════════════════════════════════════════════════════════╗');
    console.log('║     🌙 TITAN V6.0 NIGHT RAID 突击战报 🌙                       ║');
    console.log('╠══════════════════════════════════════════════════════════════════╣');
    console.log(`║     📋 总比赛数: ${String(stats.total).padStart(2)}                                            ║`);
    console.log(`║     ✅ 成功入库: ${String(stats.success).padStart(2)}                                            ║`);
    console.log(`║     ❌ 失败: ${String(stats.failed).padStart(2)}                                                ║`);
    console.log(`║     📈 成功率: ${String(((stats.success / stats.total) * 100).toFixed(1)).padStart(5)}%                                      ║`);
    console.log(`║                                                                  ║`);
    console.log(`║     🏥 视觉康复触发: ${String(stats.healingTriggered).padStart(2)} 次                                ║`);
    console.log(`║     🏥 康复成功: ${String(stats.healingSuccess).padStart(2)} 次                                    ║`);
    console.log(`║     🏥 康复成功率: ${String(healingSuccessRate).padStart(5)}%                                  ║`);
    console.log(`║                                                                  ║`);
    console.log(`║     ⏱️  总耗时: ${String((totalDuration / 1000).toFixed(1)).padStart(5)} 秒                                   ║`);
    console.log(`║     ⏱️  平均耗时: ${String((totalDuration / stats.total / 1000).toFixed(1)).padStart(5)} 秒/场                              ║`);
    console.log('╚══════════════════════════════════════════════════════════════════╝\n');

    // 打印最新数据库记录
    await showLatestRecord(pool);

  } catch (error) {
    console.error('\n💥 全局异常:', error.message);
    process.exit(1);
  } finally {
    if (context) await context.close();
    if (browser) await browser.close();
    await pool.end();
  }
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
 * 显示最新数据库记录
 */
async function showLatestRecord(pool) {
  try {
    const query = `
      SELECT 
        m.match_id,
        m.home_team,
        m.away_team,
        l3.market_sentiment->'bet365_odds'->'closing' as bet365_closing,
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
      console.log(`   Bet365: ${row.bet365_closing ? row.bet365_closing.join(', ') : 'N/A'}`);
      console.log(`   入库时间: ${row.updated_at}`);
      console.log('─'.repeat(70) + '\n');
    }
  } catch (e) {
    console.log('   ⚠️  查询最新记录失败:', e.message);
  }
}

// 运行
if (require.main === module) {
  autoHarvestV6().then(code => {
    process.exit(code || 0);
  }).catch(err => {
    console.error(err);
    process.exit(1);
  });
}

module.exports = { autoHarvestV6 };