/**
 * TITAN V6.0 SNIFFER HARVEST - 内存级JSON拦截收割机
 * ==================================================
 * 使用JSON Sniffer技术捕获解密后的明文赔率数据
 * 
 * @module scripts/ops/sniffer_harvest_v6
 * @version V6.0-SNIFFER
 * @date 2026-03-16
 */

'use strict';

const { chromium } = require('playwright');
const { Pool } = require('pg');
const fs = require('fs');
const path = require('path');

// 载入模块化组件
const {
  injectJsonSniffer,
  parseSnifferDataToMarketSentiment,
  checkPageHealth,
  healVision,
  bezierMouseMovement
} = require('../../src/infrastructure/harvesters/StealthNavigator');

// 数据库配置
const DB_CONFIG = {
  host: '127.0.0.1',
  port: 5432,
  database: 'football_db',
  user: 'football_user',
  password: process.env.DB_PASSWORD || 'football_pass',
};

// 5场英超比赛目标
const TARGETS = [
  {
    match_id: '47_20232024_4813679',
    match_name: 'Fulham vs Burnley',
    url: 'https://www.oddsportal.com/football/england/premier-league/fulham-burnley-8EamNN8b/',
    hash: '8EamNN8b'
  },
  {
    match_id: '47_20232024_4813666',
    match_name: 'Brentford vs Wolves',
    url: 'https://www.oddsportal.com/football/england/premier-league/brentford-wolves-0jR7cwU6/',
    hash: '0jR7cwU6'
  },
  {
    match_id: '47_20232024_4813675',
    match_name: 'Bournemouth vs Man United',
    url: 'https://www.oddsportal.com/football/england/premier-league/bournemouth-manchester-united-QZ5U62OH/',
    hash: 'QZ5U62OH'
  },
  {
    match_id: '47_20232024_4813676',
    match_name: 'Brighton vs Liverpool',
    url: 'https://www.oddsportal.com/football/england/premier-league/brighton-liverpool-bm4x5tgU/',
    hash: 'bm4x5tgU'
  },
  {
    match_id: '47_20232024_4813678',
    match_name: 'Everton vs Chelsea',
    url: 'https://www.oddsportal.com/football/england/premier-league/everton-chelsea-A7YyVJiS/',
    hash: 'A7YyVJiS'
  }
];

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
 * 查询并验证入库数据
 */
async function verifyDatabaseEntry(pool, matchId) {
  try {
    const query = `
      SELECT 
        m.match_id,
        m.home_team,
        m.away_team,
        l3.market_sentiment->'bet365_odds'->'history' as bet365_history,
        l3.market_sentiment->'bet365_odds'->'_point_count' as point_count,
        l3.market_sentiment->'bet365_odds'->'_is_premium' as is_premium,
        l3.market_sentiment->>'extract_method' as extract_method,
        l3.market_sentiment->'bet365_odds'->'closing' as closing,
        l3.updated_at
      FROM l3_features l3
      JOIN matches m ON l3.match_id = m.match_id
      WHERE l3.match_id = $1;
    `;
    const result = await pool.query(query, [matchId]);
    return result.rows[0] || null;
  } catch (error) {
    console.error(`   ❌ 查询失败: ${error.message}`);
    return null;
  }
}

/**
 * 打印时序变盘表
 */
function printOddsTimeline(matchName, history) {
  if (!history || history.length === 0) {
    console.log('   无时序数据');
    return;
  }
  
  console.log(`\n   📊 ${matchName} - 时序变盘表`);
  console.log('   ' + '─'.repeat(60));
  console.log('   序号 | Unix时间戳 | UTC时间              | 赔率 [主, 平, 客]');
  console.log('   ' + '─'.repeat(60));
  
  history.forEach((node, idx) => {
    const ts = node.ts || node.t;
    const odds = node.o || node.odds;
    const date = ts ? new Date(ts * 1000).toISOString().slice(0, 19).replace('T', ' ') : 'N/A';
    const label = idx === 0 ? '[OPEN]' : (idx === history.length - 1 ? '[CLOSE]' : '');
    console.log(`   ${String(idx + 1).padStart(2)}   | ${ts} | ${date} | [${odds?.join(', ') || 'N/A'}] ${label}`);
  });
  
  console.log('   ' + '─'.repeat(60));
  console.log(`   总计: ${history.length} 个变盘节点\n`);
}

/**
 * Sniffer收割主函数
 */
async function snifferHarvestV6() {
  console.log('\n╔══════════════════════════════════════════════════════════════════════════════╗');
  console.log('║     🕸️  TITAN V6.0 SNIFFER HARVEST - 嗅探打击实测 🕸️                        ║');
  console.log('║     对5场英超比赛执行精确打击                                                ║');
  console.log('╚══════════════════════════════════════════════════════════════════════════════╝\n');

  const pool = new Pool(DB_CONFIG);
  let browser = null;
  let context = null;

  // 战报统计
  const stats = {
    total: TARGETS.length,
    snifferSuccess: 0,
    domFallback: 0,
    failed: 0,
    premiumCount: 0,
    results: []
  };

  // Sniffer捕获的数据存储
  const snifferState = {
    data: null,
    received: false,
    timestamp: null
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

    // ===== SNIFFER核心：注入JSON拦截器 =====
    console.log('\n🕸️  [SNIFFER] 注入JSON内存拦截器...');
    
    // 暴露回调函数到浏览器环境
    await page.exposeFunction('__titan_emit_data', (extracted) => {
      snifferState.data = extracted;
      snifferState.received = true;
      snifferState.timestamp = Date.now();
      
      console.log(`\n   💎 [SNIFFER-HIT] 内存拦截成功！`);
      console.log(`      捕获时间戳: ${new Date(extracted.timestamp).toISOString()}`);
      console.log(`      特征Key: ${extracted.keys.join(', ')}`);
      console.log(`      包含赔率数据: ${extracted.hasOddsData ? '✅' : '❌'}`);
      console.log(`      包含用户数据: ${extracted.hasUserData ? '✅' : '❌'}`);
      
      if (extracted.data?.oddsdata) {
        const bet365 = extracted.data.oddsdata.bet365;
        const pinnacle = extracted.data.oddsdata.pinnacle;
        
        if (bet365?.history) {
          console.log(`      Bet365变盘节点: ${bet365.history.length} 个`);
        }
        if (pinnacle?.history) {
          console.log(`      Pinnacle变盘节点: ${pinnacle.history.length} 个`);
        }
      }
    });

    // 注入Sniffer脚本
    await page.addInitScript(() => {
      const originalParse = window.JSON.parse;
      let _isParsing = false;
      const TARGET_KEYS = ['userData', 'bookiehash', 'oddsdata', 'myBookmakers'];

      function isOddsData(obj) {
        if (!obj || typeof obj !== 'object') return false;
        const keys = Object.keys(obj);
        return TARGET_KEYS.some(key => keys.includes(key));
      }

      function deepClone(obj) {
        try {
          return JSON.parse(JSON.stringify(obj));
        } catch (e) {
          return obj;
        }
      }

      window.JSON.parse = function(text, reviver) {
        if (_isParsing) {
          return originalParse.call(window.JSON, text, reviver);
        }

        _isParsing = true;
        let parsed;
        try {
          parsed = originalParse.call(window.JSON, text, reviver);
        } finally {
          _isParsing = false;
        }

        if (isOddsData(parsed)) {
          const cloned = deepClone(parsed);
          const extracted = {
            timestamp: Date.now(),
            keys: Object.keys(parsed),
            hasOddsData: !!parsed.oddsdata,
            hasUserData: !!parsed.userData,
            data: cloned
          };

          if (window.__titan_emit_data) {
            window.__titan_emit_data(extracted);
          }
        }

        return parsed;
      };

      window.__titan_sniffer_injected = true;
    });

    console.log('   ✅ JSON内存拦截器已注入');

    // 处理每个目标
    for (let idx = 0; idx < TARGETS.length; idx++) {
      const target = TARGETS[idx];
      
      console.log('\n' + '='.repeat(80));
      console.log(`[${idx + 1}/${TARGETS.length}] 🎯 ${target.match_name}`);
      console.log(`   Hash: ${target.hash}`);
      console.log('='.repeat(80));

      // 重置Sniffer状态
      snifferState.data = null;
      snifferState.received = false;
      snifferState.timestamp = null;

      // 导航到页面
      console.log('\n🌐 正在加载页面...');
      try {
        await page.goto(target.url, { 
          waitUntil: 'networkidle', 
          timeout: 60000 
        });
        console.log('   ✅ 页面加载完成');
      } catch (e) {
        console.log(`   ⚠️  页面加载超时，继续执行...`);
      }

      // 执行拟人化交互触发JSON解析
      console.log('\n🖱️  执行拟人化交互触发数据加载...');
      await bezierMouseMovement(page, 2);
      await page.mouse.wheel(0, 500);
      await page.waitForTimeout(3000);

      // ===== 状态锁：等待Sniffer数据 =====
      console.log('\n🔒 [STATE LOCK] 等待Sniffer捕获数据 (15秒超时)...');
      
      const maxWaitTime = 15000;
      const startWait = Date.now();
      
      while (!snifferState.received && (Date.now() - startWait) < maxWaitTime) {
        await page.waitForTimeout(500);
        process.stdout.write(`   等待中... ${((Date.now() - startWait) / 1000).toFixed(1)}s\r`);
      }

      let marketSentiment = null;
      let extractMethod = null;

      if (snifferState.received) {
        console.log(`\n   ✅ 状态锁解除：收到Sniffer数据`);
        extractMethod = 'SNIFFER';
        
        // 解析Sniffer数据
        marketSentiment = parseSnifferDataToMarketSentiment(snifferState.data);
        
        if (marketSentiment) {
          console.log('\n📊 解析结果:');
          console.log(`   Bet365节点数: ${marketSentiment.bet365_odds?._point_count || 0}`);
          console.log(`   Pinnacle节点数: ${marketSentiment.pinnacle_odds?._point_count || 0}`);
          console.log(`   PREMIUM数据: ${marketSentiment._is_premium_data ? '✅ YES' : '❌ NO'}`);

          // 打印时序变盘表
          if (marketSentiment.bet365_odds?.history?.length > 0) {
            printOddsTimeline(target.match_name, marketSentiment.bet365_odds.history);
          }
        }
      } else {
        console.log(`\n   ⚠️  状态锁超时：未收到Sniffer数据`);
        
        // ===== 故障隔离：healVision后重试 =====
        console.log('\n🏥 [FAIL-SAFE] 执行视觉康复后重试...');
        await healVision(page, context, sessionData);
        
        // 重新等待5秒
        console.log('\n🔒 [STATE LOCK] 再次等待Sniffer数据 (5秒)...');
        const retryStart = Date.now();
        while (!snifferState.received && (Date.now() - retryStart) < 5000) {
          await page.waitForTimeout(500);
        }

        if (snifferState.received) {
          console.log(`   ✅ 重试成功：收到Sniffer数据`);
          extractMethod = 'SNIFFER_RETRY';
          marketSentiment = parseSnifferDataToMarketSentiment(snifferState.data);
        } else {
          console.log(`\n   ⚠️  重试失败，回退到DOM提取模式...`);
          extractMethod = 'DOM_FALLBACK';
          
          // DOM提取
          const domResult = await page.evaluate(() => {
            const results = { bet365Odds: null };
            const text = document.body.innerText || '';
            
            const bet365Match = text.match(/Bet365\D{0,100}(\d+\.\d{2})\s+(\d+\.\d{2})\s+(\d+\.\d{2})/i);
            if (bet365Match) {
              results.bet365Odds = [
                parseFloat(bet365Match[1]),
                parseFloat(bet365Match[2]),
                parseFloat(bet365Match[3])
              ];
            }
            
            return results;
          });

          if (domResult.bet365Odds) {
            console.log(`   ✅ DOM提取成功: [${domResult.bet365Odds.join(', ')}]`);
            marketSentiment = {
              extract_method: 'DOM_FALLBACK',
              extract_timestamp: new Date().toISOString(),
              bet365_odds: {
                detected: true,
                closing: domResult.bet365Odds,
                source: 'dom_fallback'
              },
              _is_premium_data: false
            };
          }
        }
      }

      // 入库
      if (marketSentiment) {
        const upserted = await upsertToDatabase(pool, target.match_id, marketSentiment);
        
        if (upserted) {
          console.log(`   ✅ 数据入库成功 [${extractMethod}]`);
          
          // 验证入库数据
          const verified = await verifyDatabaseEntry(pool, target.match_id);
          if (verified) {
            console.log(`\n   📋 入库验证:`);
            console.log(`      提取方法: ${verified.extract_method}`);
            console.log(`      Bet365节点: ${verified.point_count || 0}`);
            console.log(`      PREMIUM: ${verified.is_premium ? '✅' : '❌'}`);
            console.log(`      终盘赔率: [${verified.closing?.join(', ') || 'N/A'}]`);
          }

          // 统计
          if (extractMethod === 'SNIFFER' || extractMethod === 'SNIFFER_RETRY') {
            stats.snifferSuccess++;
          } else {
            stats.domFallback++;
          }
          
          if (marketSentiment._is_premium_data) {
            stats.premiumCount++;
          }
          
          stats.results.push({
            match_name: target.match_name,
            method: extractMethod,
            is_premium: marketSentiment._is_premium_data,
            point_count: marketSentiment.bet365_odds?._point_count || 0
          });
        }
      } else {
        console.log(`   ❌ 数据提取失败`);
        stats.failed++;
        stats.results.push({
          match_name: target.match_name,
          method: 'FAILED',
          is_premium: false,
          point_count: 0
        });
      }

      // 间隔
      if (idx < TARGETS.length - 1) {
        console.log(`\n⏱️  等待5秒后下一场...`);
        await page.waitForTimeout(5000);
      }
    }

    // ===== 战报 =====
    console.log('\n\n' + '═'.repeat(80));
    console.log('📊 SNIFFER STRIKE 实测战报');
    console.log('═'.repeat(80));
    
    console.log(`\n📈 统计摘要:`);
    console.log(`   总场次: ${stats.total}`);
    console.log(`   Sniffer成功: ${stats.snifferSuccess} (${((stats.snifferSuccess/stats.total)*100).toFixed(1)}%)`);
    console.log(`   DOM备选: ${stats.domFallback} (${((stats.domFallback/stats.total)*100).toFixed(1)}%)`);
    console.log(`   失败: ${stats.failed}`);
    console.log(`   [PREMIUM DATA]: ${stats.premiumCount} 场`);
    
    console.log(`\n📋 详细结果:`);
    console.log('─'.repeat(80));
    console.log('Match'.padEnd(30) + ' | Method'.padEnd(15) + ' | Points | Premium');
    console.log('─'.repeat(80));
    
    stats.results.forEach(r => {
      const name = r.match_name.substring(0, 28).padEnd(30);
      const method = r.method.padEnd(15);
      const points = String(r.point_count).padEnd(6);
      const premium = r.is_premium ? '✨ YES' : 'NO';
      console.log(`${name} | ${method} | ${points} | ${premium}`);
    });
    console.log('─'.repeat(80));

  } catch (error) {
    console.error('\n💥 错误:', error);
  } finally {
    if (context) await context.close();
    if (browser) await browser.close();
    await pool.end();
  }

  console.log('\n╔══════════════════════════════════════════════════════════════════════════════╗');
  console.log('║     ✅ SNIFFER STRIKE 实测完成                                               ║');
  console.log('╚══════════════════════════════════════════════════════════════════════════════╝\n');
}

// 运行
if (require.main === module) {
  snifferHarvestV6().then(() => {
    console.log('✅ SNIFFER HARVEST COMPLETE');
    process.exit(0);
  }).catch(err => {
    console.error('💥 FAILED:', err);
    process.exit(1);
  });
}

module.exports = { snifferHarvestV6 };