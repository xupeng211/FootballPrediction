/**
 * TITAN V6.0 ASSISTED HARVEST - 半自动辅助收割协议
 * =================================================
 * 人机协作模式：指挥官确认渲染，脚本负责提取入库
 * 
 * @module scripts/ops/assisted_harvest
 * @version V6.0-ASSISTED-FIRE
 * @date 2026-03-16
 */

'use strict';

const { chromium } = require('playwright');
const { Pool } = require('pg');
const fs = require('fs');
const path = require('path');
const readline = require('readline');

// 数据库配置
const DB_CONFIG = {
  host: '127.0.0.1',
  port: 5432,
  database: 'football_db',
  user: 'football_user',
  password: process.env.DB_PASSWORD || 'football_pass',
};

// 20场英超比赛目标列表
const TARGET_MATCHES = [
  { match_id: '47_20232024_4813679', url: 'https://www.oddsportal.com/football/england/premier-league/fulham-burnley-8EamNN8b/', name: 'Fulham vs Burnley' },
  { match_id: '47_20252026_4813666', url: 'https://www.oddsportal.com/football/england/premier-league/brentford-wolves-0jR7cwU6/', name: 'Brentford vs Wolves' },
  { match_id: '47_20232024_4813675', url: 'https://www.oddsportal.com/football/england/premier-league/bournemouth-manchester-united-QZ5U62OH/', name: 'Bournemouth vs Man United' },
];

// 统计信息
const stats = {
  total: TARGET_MATCHES.length,
  success: 0,
  failed: 0,
  ignored: 0,
  manualTime: 0,
  startTime: Date.now()
};

/**
 * 等待用户输入
 */
function waitForUserInput(prompt) {
  return new Promise((resolve) => {
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout
    });
    
    rl.question(prompt, (answer) => {
      rl.close();
      resolve(answer.trim());
    });
  });
}

/**
 * 主函数
 */
async function assistedHarvest() {
  console.log('\n╔══════════════════════════════════════════════════════════════════╗');
  console.log('║     👤 TITAN V6.0 ASSISTED HARVEST 👤                          ║');
  console.log('║     半自动辅助收割协议 - 人机协作模式                          ║');
  console.log('╚══════════════════════════════════════════════════════════════════╝\n');

  console.log('🔧 配置信息:');
  console.log(`   📡 DB: ${DB_CONFIG.host}:${DB_CONFIG.port}/${DB_CONFIG.database}`);
  console.log(`   🎯 目标: ${TARGET_MATCHES.length} 场英超比赛`);
  console.log('   🎭 Mode: headless=false (可见窗口)');
  console.log('   👤 模式: 人工确认渲染 + 自动提取入库\n');

  const pool = new Pool(DB_CONFIG);
  let browser = null;
  let context = null;
  let page = null;

  try {
    // 启动浏览器（强制可见模式）
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

    // 加载黄金会话
    const sessionPath = path.join(process.cwd(), 'data/sessions/auth_gold.json');
    try {
      const sessionData = JSON.parse(fs.readFileSync(sessionPath, 'utf-8'));
      contextConfig.storageState = sessionData;
      console.log('✅ 已加载黄金会话');
    } catch (e) {
      console.log('⚠️  未找到黄金会话');
    }

    context = await browser.newContext(contextConfig);
    
    // 注入stealth脚本
    await context.addInitScript(() => {
      Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
      Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    });

    page = await context.newPage();

    // 处理每场比赛
    for (let i = 0; i < TARGET_MATCHES.length; i++) {
      const match = TARGET_MATCHES[i];
      const matchStartTime = Date.now();
      
      console.log(`\n${'='.repeat(70)}`);
      console.log(`[${i + 1}/${TARGET_MATCHES.length}] 🎯 ${match.name}`);
      console.log(`     🆔 Match ID: ${match.match_id}`);
      console.log(`     🔗 URL: ${match.url}`);
      console.log('='.repeat(70));

      // 导航到页面
      console.log('\n🌐 正在加载页面...');
      await page.goto(match.url, { waitUntil: 'load', timeout: 120000 });
      console.log('   ✅ 页面加载完成');

      // 交互式挂起：等待用户确认
      console.log('\n🚀 --------------------------------------------------------');
      console.log('🚀 请在浏览器中确认赔率已加载');
      console.log('🚀 如未加载请手动点击或滚动页面');
      console.log('🚀 完成后在本控制台按回车键继续...');
      console.log('--------------------------------------------------------\n');

      const startWait = Date.now();
      await waitForUserInput('⏳ 按回车键确认继续...');
      const manualTime = (Date.now() - startWait) / 1000;
      stats.manualTime += manualTime;

      console.log(`   ⏱️  人工确认耗时: ${manualTime.toFixed(1)}秒`);

      // 执行提取
      let retryCount = 0;
      let maxRetries = 3;
      let success = false;

      while (retryCount < maxRetries && !success) {
        // 提取数据
        const marketSentiment = await extractData(page);
        
        // 零失败校验
        if (marketSentiment.pinnacle_odds && marketSentiment.pinnacle_odds.closing) {
          // 数据有效，执行入库
          console.log('\n💾 执行物理入库...');
          const result = await upsertToDatabase(pool, match.match_id, marketSentiment);
          
          if (result) {
            const pin = marketSentiment.pinnacle_odds.closing;
            console.log(`\n🎉 历史突破！由指挥官手动确认，`);
            console.log(`     Match [${match.match_id}]`);
            console.log(`     真实平博赔率 [${pin[0]}, ${pin[1]}, ${pin[2]}]`);
            console.log(`     已物理入库！`);
            stats.success++;
            success = true;
          }
        } else {
          // 数据为空
          console.log('\n❌ 抓取失败，数据仍为空！');
          console.log('   pinnacle_odds: ', marketSentiment.pinnacle_odds);
          
          if (retryCount < maxRetries - 1) {
            const action = await waitForUserInput('   请检查浏览器后按 [R] 重试，或按 [C] 忽略，或按 [Q] 退出: ');
            
            if (action.toUpperCase() === 'R') {
              retryCount++;
              console.log(`   🔄 第${retryCount}次重试...`);
              continue;
            } else if (action.toUpperCase() === 'C') {
              console.log('   ⏭️  忽略本场比赛');
              stats.ignored++;
              break;
            } else if (action.toUpperCase() === 'Q') {
              console.log('   🛑 退出收割');
              throw new Error('USER_QUIT');
            }
          } else {
            console.log('   ❌ 已达最大重试次数，标记为失败');
            stats.failed++;
          }
        }
      }

      // 如果不是最后一场，导航到下一场
      if (i < TARGET_MATCHES.length - 1) {
        console.log('\n➡️  准备下一场比赛...');
        await page.waitForTimeout(2000);
      }
    }

    // 最终战报
    await printFinalReport();

  } catch (error) {
    if (error.message === 'USER_QUIT') {
      console.log('\n👋 用户主动退出');
    } else {
      console.error('\n💥 执行失败:', error.message);
    }
  } finally {
    if (page) await page.close();
    if (context) await context.close();
    if (browser) await browser.close();
    await pool.end();
  }
}

/**
 * 提取数据
 */
async function extractData(page) {
  console.log('\n⛏️  执行数据提取...');
  
  const interceptedData = { oddsData: null, bookmakers: {}, rawArrays: [] };

  // 设置API拦截
  await page.route('**/*', async (route, request) => {
    const url = request.url();
    const isOddsApi = /oddsportal\.com.*(ajax|feed|match-event|odds|1-1)/.test(url);

    if (isOddsApi) {
      try {
        const response = await route.fetch();
        const text = await response.text();
        try {
          const json = JSON.parse(text);
          extractOddsArrays(json, interceptedData);
        } catch (e) {}
      } catch (e) {}
    }
    route.continue();
  });

  // 从DOM提取
  const domOdds = await extractOddsFromDOM(page);
  console.log('   DOM提取结果:', JSON.stringify(domOdds, null, 2));

  // 构建市场情感数据
  const marketSentiment = buildMarketSentiment(interceptedData, domOdds);
  
  return marketSentiment;
}

/**
 * 从DOM提取赔率
 */
async function extractOddsFromDOM(page) {
  return await page.evaluate(() => {
    const results = { pinnacleOdds: null, bet365Odds: null, allBookmakers: [] };

    // 尝试多种选择器
    const selectors = [
      'table tbody tr',
      'div[role="row"]',
      '[class*="bookmaker"]',
      '[class*="odds"]'
    ];

    for (const selector of selectors) {
      const rows = document.querySelectorAll(selector);
      
      rows.forEach((row) => {
        const text = row.textContent || '';
        const isPinnacle = /Pinnacle/i.test(text);
        const isBet365 = /Bet365|bet365/i.test(text);

        // 提取数字（赔率格式: x.xx）
        const oddsPattern = /(\d+\.\d{2})/g;
        const odds = text.match(oddsPattern);

        if (odds && odds.length >= 3) {
          const oddsValues = odds.slice(0, 3).map(o => parseFloat(o));

          if (isPinnacle && !results.pinnacleOdds) {
            results.pinnacleOdds = oddsValues;
          }
          if (isBet365 && !results.bet365Odds) {
            results.bet365Odds = oddsValues;
          }

          const bookieName = text.substring(0, 30).trim();
          results.allBookmakers.push({ name: bookieName, odds: oddsValues });
        }
      });

      if (results.allBookmakers.length > 0) break;
    }

    // 从完整文本匹配（备用）
    if (!results.pinnacleOdds || !results.bet365Odds) {
      const allText = document.body.innerText || '';

      if (!results.pinnacleOdds) {
        const pinnacleMatch = allText.match(/Pinnacle\D{0,100}(\d+\.\d{2})\s+(\d+\.\d{2})\s+(\d+\.\d{2})/i);
        if (pinnacleMatch) {
          results.pinnacleOdds = [parseFloat(pinnacleMatch[1]), parseFloat(pinnacleMatch[2]), parseFloat(pinnacleMatch[3])];
        }
      }

      if (!results.bet365Odds) {
        const bet365Match = allText.match(/Bet365\D{0,100}(\d+\.\d{2})\s+(\d+\.\d{2})\s+(\d+\.\d{2})/i);
        if (bet365Match) {
          results.bet365Odds = [parseFloat(bet365Match[1]), parseFloat(bet365Match[2]), parseFloat(bet365Match[3])];
        }
      }
    }

    return results;
  });
}

/**
 * 提取赔率数组
 */
function extractOddsArrays(obj, result, depth = 0, path = '') {
  if (depth > 15 || !obj || typeof obj !== 'object') return;

  for (const [key, value] of Object.entries(obj)) {
    const currentPath = path ? `${path}.${key}` : key;

    if (Array.isArray(value) && value.length === 3) {
      const areNumbers = value.every(v => {
        const num = parseFloat(v);
        return !isNaN(num) && num > 1 && num < 100;
      });
      if (areNumbers) {
        result.rawArrays.push({ path: currentPath, values: value.map(v => parseFloat(v)), depth });
      }
    }

    if (typeof value === 'object' && value !== null) {
      extractOddsArrays(value, result, depth + 1, currentPath);
    }
  }
}

/**
 * 构建市场情感数据
 */
function buildMarketSentiment(intercepted, domData) {
  const ms = {
    extract_method: 'ASSISTED_HARVEST_V6.0',
    extract_timestamp: new Date().toISOString(),
    source: 'oddsportal_assisted',
    pinnacle_odds: null,
    bet365_odds: null,
    dom_snapshot: domData
  };

  // 优先使用DOM提取的数据
  if (domData.pinnacleOdds && domData.pinnacleOdds.length === 3) {
    ms.pinnacle_odds = {
      detected: true,
      bookmaker_id: 18,
      source: 'dom_extraction',
      closing: domData.pinnacleOdds
    };
  }

  if (domData.bet365Odds && domData.bet365Odds.length === 3) {
    ms.bet365_odds = {
      detected: true,
      bookmaker_id: 16,
      source: 'dom_extraction',
      closing: domData.bet365Odds
    };
  }

  return ms;
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

    if (result.rows.length > 0) {
      return true;
    }
  } catch (error) {
    console.error(`   ❌ 入库失败: ${error.message}`);
  }
  return false;
}

/**
 * 打印最终战报
 */
async function printFinalReport() {
  const totalTime = (Date.now() - stats.startTime) / 1000;
  const avgManualTime = stats.total > 0 ? (stats.manualTime / stats.total).toFixed(1) : 0;
  const successRate = stats.total > 0 ? ((stats.success / stats.total) * 100).toFixed(1) : 0;

  console.log('\n' + '='.repeat(70));
  console.log('📊 TITAN V6.0 ASSISTED HARVEST 最终战报');
  console.log('='.repeat(70));
  console.log(`   📋 总比赛数: ${stats.total}`);
  console.log(`   ✅ 成功入库: ${stats.success}`);
  console.log(`   ❌ 失败: ${stats.failed}`);
  console.log(`   ⏭️  忽略: ${stats.ignored}`);
  console.log(`   📈 成功率: ${successRate}%`);
  console.log(`   ⏱️  总耗时: ${totalTime.toFixed(1)}秒`);
  console.log(`   ⏱️  平均人工确认耗时: ${avgManualTime}秒/场`);
  console.log('='.repeat(70));

  if (stats.success === stats.total) {
    console.log('🏆 恭喜！100%胜率达成！所有比赛数据已成功入库！');
  } else if (stats.success > 0) {
    console.log(`🎯 部分成功！${stats.success}/${stats.total} 场比赛数据已入库`);
  } else {
    console.log('⚠️  本次收割未能成功入库数据，请检查浏览器配置和页面状态');
  }
  console.log('='.repeat(70) + '\n');
}

// 运行
if (require.main === module) {
  assistedHarvest().catch(console.error);
}

module.exports = { assistedHarvest };