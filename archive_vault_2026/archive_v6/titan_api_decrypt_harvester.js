/**
 * TITAN V6.0 API-DECRYPT HARVESTER - API深度破译收割机
 * =====================================================
 * 提取完整赔率变动曲线与原始时间戳
 * 
 * @module scripts/ops/titan_api_decrypt_harvester
 * @version V6.0-API-DECRYPT
 */

'use strict';

const { chromium } = require('playwright');
const { Pool } = require('pg');
const fs = require('fs');
const path = require('path');

// 载入V6.0 API-DECRYPT模块
const {
  deepParseOddsData,
  buildMarketSentiment
} = require('../../src/infrastructure/harvesters/OddsPortalParser');

const { silentHarvestLoop } = require('../../src/infrastructure/harvesters/StealthNavigator');

// 数据库配置
const DB_CONFIG = {
  host: '127.0.0.1',
  port: 5432,
  database: 'football_db',
  user: 'football_user',
  password: process.env.DB_PASSWORD || 'football_pass',
};

// 已验证URL
const VERIFIED_STRIKE_MAP = [
  {
    match_id: '47_20232024_4813679',
    match_name: 'Fulham vs Burnley',
    league: 'Premier League',
    url: 'https://www.oddsportal.com/football/england/premier-league/fulham-burnley-8EamNN8b/',
    hash: '8EamNN8b'
  }
];

/**
 * 随机延迟
 */
async function humanBreath(min = 5000, max = 15000) {
  const delay = Math.floor(Math.random() * (max - min + 1)) + min;
  process.stdout.write(`⏱️  Human Breath: ${delay}ms... `);
  await new Promise(r => setTimeout(r, delay));
  console.log('✓');
  return delay;
}

/**
 * 数据库入库（含时序数据）
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
 * 显示变盘时序图
 */
function displayOddsTimeline(matchName, bookieName, timeline) {
  console.log(`\n📈 [ODDS TIMELINE] ${matchName} - ${bookieName}`);
  console.log('─'.repeat(70));
  
  if (!timeline || !timeline.history || timeline.history.length === 0) {
    console.log('   无时序数据');
    return;
  }

  // 表头
  console.log('   Time                | Home  | Draw  | Away  | Change');
  console.log('   ───────────────────────────────────────────────────────');

  let prevOdds = null;
  
  timeline.history.forEach((point, idx) => {
    const date = point.ts 
      ? new Date(point.ts * 1000).toISOString().slice(0, 19).replace('T', ' ')
      : `Point ${idx + 1}`;
    const odds = point.o;
    const label = idx === 0 ? ' [OPEN]' : (idx === timeline.history.length - 1 ? ' [CLOSE]' : '');
    
    let changeStr = '';
    if (prevOdds) {
      const homeChange = ((odds[0] - prevOdds[0]) / prevOdds[0] * 100).toFixed(2);
      const drawChange = ((odds[1] - prevOdds[1]) / prevOdds[1] * 100).toFixed(2);
      const awayChange = ((odds[2] - prevOdds[2]) / prevOdds[2] * 100).toFixed(2);
      
      const formatChange = (c) => {
        const num = parseFloat(c);
        if (num > 0) return `+${c}%`;
        if (num < 0) return `${c}%`;
        return '0%';
      };
      
      changeStr = `H:${formatChange(homeChange)} D:${formatChange(drawChange)} A:${formatChange(awayChange)}`;
    } else {
      changeStr = '---';
    }
    
    console.log(`   ${date.padEnd(19)} | ${odds[0].toFixed(2)} | ${odds[1].toFixed(2)} | ${odds[2].toFixed(2)} | ${changeStr}${label}`);
    
    prevOdds = odds;
  });

  console.log('   ───────────────────────────────────────────────────────');
  console.log(`   Volatility Index: ${timeline.volatility_index?.toFixed(4) || 'N/A'}`);
  console.log(`   History Points: ${timeline._point_count || 0} ${timeline._is_premium ? '[PREMIUM DATA]' : ''}`);
  console.log(`   Last Changed: ${timeline.last_changed_at ? new Date(timeline.last_changed_at * 1000).toISOString() : 'N/A'}`);
  console.log('─'.repeat(70));
}

/**
 * 主收割函数
 */
async function apiDecryptHarvest() {
  console.log('\n╔══════════════════════════════════════════════════════════════════════════════╗');
  console.log('║     🔓 TITAN V6.0 API-DECRYPT HARVESTER - API深度破译 🔓                     ║');
  console.log('║     提取赔率变动曲线与原始时间戳                                             ║');
  console.log('╚══════════════════════════════════════════════════════════════════════════════╝\n');

  const pool = new Pool(DB_CONFIG);
  let browser = null;
  let context = null;

  // 拦截到的API数据存储
  const interceptedApis = [];

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
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1920,1080']
    });

    const contextConfig = {
      viewport: { width: 1920, height: 1080 },
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    };
    if (sessionData) contextConfig.storageState = sessionData;

    context = await browser.newContext(contextConfig);
    const page = await context.newPage();

    // 注入stealth
    await context.addInitScript(() => {
      Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    });

    // 设置API拦截
    await page.route('**/*', async (route, request) => {
      const url = request.url();
      
      // 拦截OddsPortal API请求
      if (url.includes('oddsportal.com') && 
          (url.includes('/api/') || url.includes('match-event') || url.includes('odds'))) {
        try {
          const response = await route.fetch();
          const body = await response.json().catch(() => null);
          
          if (body) {
            interceptedApis.push({
              url: url,
              timestamp: Date.now(),
              data: body
            });
          }
          
          await route.continue();
        } catch (e) {
          await route.continue();
        }
      } else {
        await route.continue();
      }
    });

    // 处理每个目标
    for (const target of VERIFIED_STRIKE_MAP) {
      console.log('\n' + '='.repeat(80));
      console.log(`🎯 ${target.match_name}`);
      console.log(`   URL: ${target.url}`);
      console.log('='.repeat(80));

      // Human Breath
      await humanBreath(5000, 10000);

      // 导航到页面
      try {
        await page.goto(target.url, { waitUntil: 'domcontentloaded', timeout: 45000 });
        console.log('   ✅ 页面加载完成');
      } catch (e) {
        console.log(`   ⚠️  页面加载超时: ${e.message}`);
        continue;
      }

      // 等待API拦截
      console.log('   ⏳ 等待API响应...');
      await page.waitForTimeout(5000);

      // 处理拦截到的API数据
      if (interceptedApis.length > 0) {
        console.log(`   ✅ 拦截到 ${interceptedApis.length} 个API响应`);
        
        // 合并所有API数据
        const mergedApiData = interceptedApis.reduce((acc, api) => {
          return { ...acc, ...api.data };
        }, {});

        // 使用V6.0 API-DECRYPT解析
        const apiResult = deepParseOddsData(mergedApiData);
        
        console.log('\n📊 [API-DECRYPT] 解析结果:');
        
        // 显示Pinnacle时序
        if (apiResult.pinnacle && apiResult.pinnacle._point_count > 0) {
          displayOddsTimeline(target.match_name, 'Pinnacle', apiResult.pinnacle);
        }
        
        // 显示Bet365时序
        if (apiResult.bet365 && apiResult.bet365._point_count > 0) {
          displayOddsTimeline(target.match_name, 'Bet365', apiResult.bet365);
        }

        // 构建市场情感
        const marketSentiment = buildMarketSentiment(apiResult, null);
        
        // 标记PREMIUM DATA
        const isPremium = marketSentiment._is_premium_data;
        const premiumCount = marketSentiment._premium_count || 0;
        
        console.log(`\n${isPremium ? '💎 [PREMIUM DATA]' : '📄 [STANDARD DATA]'} ${target.match_name}`);
        console.log(`   Premium Bookmakers: ${premiumCount}`);
        console.log(`   Bet365 History Points: ${apiResult.bet365?._point_count || 0}`);
        console.log(`   Pinnacle History Points: ${apiResult.pinnacle?._point_count || 0}`);

        // 入库校验：至少3个历史点才标注[PREMIUM DATA]
        const hasEnoughHistory = 
          (apiResult.bet365?._point_count >= 3) || 
          (apiResult.pinnacle?._point_count >= 3);

        if (hasEnoughHistory) {
          console.log('   ✅ 满足PREMIUM DATA条件，执行入库...');
          const upserted = await upsertToDatabase(pool, target.match_id, marketSentiment);
          
          if (upserted) {
            console.log('   ✅ 入库成功');
          } else {
            console.log('   ❌ 入库失败');
          }
        } else {
          console.log('   ⚠️  历史点不足，跳过入库');
        }

        // 保存原始API数据（调试用）
        const debugPath = path.join(process.cwd(), `data/audit/api_decrypt_${target.match_id}_${Date.now()}.json`);
        fs.writeFileSync(debugPath, JSON.stringify({
          match: target,
          apis: interceptedApis,
          parsed: apiResult,
          sentiment: marketSentiment
        }, null, 2));
        console.log(`\n💾 原始API数据已保存: ${debugPath}`);
      } else {
        console.log('   ⚠️  未拦截到API响应，回退到DOM提取');
      }
    }

  } catch (error) {
    console.error('\n💥 错误:', error);
  } finally {
    if (context) await context.close();
    if (browser) await browser.close();
    await pool.end();
  }
}

// 运行
if (require.main === module) {
  apiDecryptHarvest().then(() => {
    console.log('\n✅ API-DECRYPT HARVEST COMPLETE');
    process.exit(0);
  }).catch(err => {
    console.error('\n💥 FAILED:', err);
    process.exit(1);
  });
}

module.exports = { apiDecryptHarvest };