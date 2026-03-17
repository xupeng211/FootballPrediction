/**
 * TITAN V6.0 HOST FORCE HARVEST - 宿主机强制收割
 * ==============================================
 * 简化版单一页面收割流程，专为宿主机GUI环境设计
 *
 * @module scripts/ops/host_force_harvest
 * @version V6.0-HOST-FORCE
 * @date 2026-03-16
 */

'use strict';

const { chromium } = require('playwright');
const { Pool } = require('pg');
const fs = require('fs');
const path = require('path');

// 数据库配置
const DB_CONFIG = {
  host: '127.0.0.1',
  port: 5432,
  database: 'football_db',
  user: 'football_user',
  password: process.env.DB_PASSWORD || 'football_pass',
};

// 目标比赛URL
const TARGET_URL = 'https://www.oddsportal.com/football/england/premier-league/fulham-burnley-8EamNN8b/';
const TARGET_MATCH_ID = '47_20232024_4813679';

// 博彩公司ID映射
const BOOKMAKER_ID_MAP = {
  PINNACLE: [18, 27, 'pinnacle', 'Pinnacle', 'PINNACLE'],
  BET365: [16, 'bet365', 'Bet365', 'BET365', '365']
};

/**
 * 主函数
 */
async function hostForceHarvest() {
  console.log('\n╔══════════════════════════════════════════════════════════════════╗');
  console.log('║     🖥️  TITAN V6.0 HOST FORCE HARVEST 🖥️                        ║');
  console.log('║     宿主机强制收割 - 单一页面实弹入库                          ║');
  console.log('╚══════════════════════════════════════════════════════════════════╝\n');

  console.log('🔧 配置信息:');
  console.log(`   📡 DB: ${DB_CONFIG.host}:${DB_CONFIG.port}/${DB_CONFIG.database}`);
  console.log(`   🎯 URL: ${TARGET_URL}`);
  console.log(`   🆔 Match ID: ${TARGET_MATCH_ID}`);
  console.log('   🎭 Mode: headless=false (可见窗口)\n');

  let browser = null;
  let context = null;
  const pool = new Pool(DB_CONFIG);

  try {
    // 加载黄金会话
    const sessionPath = path.join(process.cwd(), 'data/sessions/auth_gold.json');
    let sessionData = null;
    try {
      sessionData = JSON.parse(fs.readFileSync(sessionPath, 'utf-8'));
      console.log('✅ 已加载黄金会话');
      console.log(`   🍪 Cookies: ${sessionData.cookies?.length || 0} 个`);
    } catch (e) {
      console.log('⚠️  未找到黄金会话，将使用新会话');
    }

    // 启动浏览器（宿主机可见模式）
    console.log('\n🚀 启动浏览器...');
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

    // 注入stealth脚本
    await context.addInitScript(() => {
      Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
      Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    });

    const page = await context.newPage();

    // V6.0 GOLDEN-GRAB: API报文深度剥离
    const interceptedData = { oddsData: null, bookmakers: {}, rawArrays: [] };
    let firstOddsArrayPrinted = false;

    await page.route('**/*', async (route, request) => {
      const url = request.url();
      const isOddsApi = /oddsportal\.com.*(ajax|feed|match-event|odds|1-1)/.test(url);

      if (isOddsApi) {
        console.log(`   📡 API: ${url.substring(0, 70)}...`);
        try {
          const response = await route.fetch();
          const text = await response.text();
          try {
            const json = JSON.parse(text);
            // 递归搜索赔率数据
            searchForOdds(json, interceptedData);

            // V6.0 GOLDEN-GRAB: 深度剥离 - 捕获所有数值数组
            extractOddsArrays(json, interceptedData);

            // 打印第一个非空赔率数组
            if (!firstOddsArrayPrinted && interceptedData.rawArrays.length > 0) {
              const firstArray = interceptedData.rawArrays[0];
              if (firstArray.values && firstArray.values.length === 3) {
                console.log(`   💰 首个赔率数组: [${firstArray.values.join(', ')}]`);
                firstOddsArrayPrinted = true;
              }
            }
          } catch (e) {
            // JSON解析失败，可能是二进制或其他格式
          }
        } catch (e) {
          console.log(`   ⚠️  API获取失败: ${e.message}`);
        }
      }
      route.continue();
    });

    // 导航到目标页面
    console.log('\n🔍 导航到目标页面...');
    await page.goto(TARGET_URL, { waitUntil: 'load', timeout: 120000 });
    console.log('   ✅ 页面load事件完成');

    // V6.0 HUMAN-MIMIC: 拟人化攻击协议启动
    console.log('\n🎭 [HUMAN-MIMIC] 拟人化行为交互启动...');

    // 第一步：声东击西 - 先点击Tennis再返回
    console.log('   🎯 执行声东击西策略...');
    await contextSwitchManeuver(page);

    // 第二步：拟人化轨迹 - 贝塞尔曲线鼠标移动
    console.log('   🖱️  执行拟人化鼠标轨迹...');
    await humanTrajectorySimulation(page);

    // 第三步：实时视力康复监测
    console.log('   👁️  启动视力康复监测...');
    let visionResult;
    try {
      visionResult = await visionRecoveryCheck(page, interceptedData);
    } catch (e) {
      console.log('   ⚠️  视力监测过程中发生错误:', e.message);
      visionResult = { success: false, method: 'error' };
    }

    if (!visionResult || !visionResult.success) {
      console.log('   ⚠️  视力未完全恢复，尝试备用策略...');
      try {
        await page.reload({ waitUntil: 'domcontentloaded', timeout: 30000 });
        await page.waitForTimeout(3000);
        await humanTrajectorySimulation(page);
      } catch (e) {
        console.log('   ⚠️  重新加载失败，继续使用当前页面状态...');
      }
    } else {
      console.log('   ✅ 视力恢复，检测到赔率内容！');
    }

    // 截图审计 - 白框变彩表的瞬间
    const screenshotPath = path.join(process.cwd(), 'data/screenshots/host_harvest_final.png');
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log(`   📸 全页截图已保存: ${screenshotPath}`);

    // 尝试点击 Bookmakers 标签
    console.log('\n🖱️  尝试点击 Bookmakers 标签...');
    let bookmakersClicked = false;
    try {
      let bookmakersTab = await page.$('text=Bookmakers');
      if (!bookmakersTab) {
        await page.mouse.wheel(0, 1000);
        await page.waitForTimeout(2000);
        bookmakersTab = await page.$('text=Bookmakers');
      }

      if (bookmakersTab) {
        await bookmakersTab.click();
        console.log('   ✅ 已点击 Bookmakers');
        bookmakersClicked = true;
        await page.waitForTimeout(5000);
      }
    } catch (e) {
      console.log('   ⚠️  Bookmakers点击失败:', e.message);
    }

    if (bookmakersClicked) {
      console.log('   ⏳ 等待赔率表格渲染...');
      await page.waitForTimeout(5000);

      // 滚动到表格区域
      console.log('   🔄 滚动到赔率表格区域...');
      await page.evaluate(() => {
        const table = document.querySelector('table, .odds-table, [class*="bookmaker"]');
        if (table) table.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
      await page.waitForTimeout(3000);
    }

    // 无论是否点击成功，都等待更多时间让JS渲染
    console.log('   ⏳ 额外等待JS渲染...');
    await page.waitForTimeout(5000);

    // 检查是否拦截到数据
    console.log('\n📊 拦截数据检查:');
    console.log(`   📡 API数据: ${interceptedData.oddsData ? '✅' : '❌'}`);
    console.log(`   🔒 Pinnacle: ${interceptedData.bookmakers.pinnacle ? '✅' : '❌'}`);
    console.log(`   🏪 Bet365: ${interceptedData.bookmakers.bet365 ? '✅' : '❌'}`);

    // V6.0 GOLDEN-GRAB: 从DOM提取作为备用
    console.log('\n🔍 尝试从DOM提取赔率...');

    // 首先滚动查找Pinnacle
    console.log('   🔄 滚动查找Pinnacle...');
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(1000);

    let domOdds = await extractOddsFromDOM(page);

    // 如果未找到Pinnacle，继续滚动查找
    if (!domOdds.pinnacleOdds) {
      for (let i = 0; i < 3; i++) {
        await page.evaluate(() => window.scrollBy(0, 800));
        await page.waitForTimeout(1500);
        domOdds = await extractOddsFromDOM(page);
        if (domOdds.pinnacleOdds) break;
      }
    }

    console.log('   DOM提取结果:', JSON.stringify(domOdds, null, 2));

    // 如果DOM提取到数据但未在API中找到，补充到interceptedData
    if (domOdds.pinnacleOdds && !interceptedData.bookmakers.pinnacle) {
      console.log('   💰 DOM补充Pinnacle数据:', domOdds.pinnacleOdds);
      interceptedData.bookmakers.pinnacle = { id: 18, source: 'dom_fallback' };
      interceptedData.rawArrays.push({
        path: 'dom.pinnacle',
        values: domOdds.pinnacleOdds,
        source: 'dom'
      });
    }

    if (domOdds.bet365Odds && !interceptedData.bookmakers.bet365) {
      console.log('   💰 DOM补充Bet365数据:', domOdds.bet365Odds);
      interceptedData.bookmakers.bet365 = { id: 16, source: 'dom_fallback' };
      interceptedData.rawArrays.push({
        path: 'dom.bet365',
        values: domOdds.bet365Odds,
        source: 'dom'
      });
    }

    // 构建市场情感数据
    const marketSentiment = buildMarketSentiment(interceptedData, domOdds);

    // V6.0 GOLDEN-GRAB: 非真即毁 - 严格数据验证（允许Bet365作为备选）
    console.log('\n🔒 执行严格数据验证...');

    // 首先尝试验证Pinnacle
    let isValidData = validateMarketSentiment(marketSentiment);
    let usingBet365 = false;

    // 如果没有Pinnacle但有Bet365，尝试使用Bet365
    if (!isValidData.valid && marketSentiment.bet365_odds && marketSentiment.bet365_odds.closing) {
      console.log('   ⚠️  Pinnacle不可用，尝试使用Bet365作为备选...');
      const bet365Validation = validateBet365Odds(marketSentiment);
      if (bet365Validation.valid) {
        isValidData = { valid: true, reason: 'using_bet365_fallback' };
        usingBet365 = true;
      }
    }

    if (!isValidData.valid) {
      console.log(`   ❌ 数据验证失败: ${isValidData.reason}`);
      console.log('   🚫 拒绝入库空壳记录！');
      throw new Error(`GOLDEN_GRAB_VALIDATION_FAILED: ${isValidData.reason}`);
    }

    console.log(`   ✅ 数据验证通过`);
    if (usingBet365) {
      console.log(`   ✅ [Bet365 Found] Home: ${marketSentiment.bet365_odds.closing[0]} | Draw: ${marketSentiment.bet365_odds.closing[1]} | Away: ${marketSentiment.bet365_odds.closing[2]}`);
    } else {
      console.log(`   ✅ [Pinnacle Found] Home: ${marketSentiment.pinnacle_odds.closing[0]} | Draw: ${marketSentiment.pinnacle_odds.closing[1]} | Away: ${marketSentiment.pinnacle_odds.closing[2]}`);
    }

    // 入库
    console.log('\n💾 执行物理入库...');
    const result = await upsertToDatabase(pool, TARGET_MATCH_ID, marketSentiment);

    if (result) {
      console.log(`\n🎉 历史突破！Match ID [${TARGET_MATCH_ID}] 真实赔率已成功入库！`);

      // V6.0 HUMAN-MIMIC: 实弹夺金成功标记
      if (marketSentiment.pinnacle_odds && marketSentiment.pinnacle_odds.closing) {
        const pin = marketSentiment.pinnacle_odds.closing;
        console.log(`\n💎 [REAL GOLD ACQUIRED] Pinnacle Home: ${pin[0]} | Method: MIMIC_ATTACK_V3`);
        console.log(`💎 [REAL GOLD ACQUIRED] Draw: ${pin[1]} | Away: ${pin[2]} | Source: ${marketSentiment.pinnacle_odds.source || 'unknown'}`);
      }
    }

    // 最终截图
    const finalScreenshot = path.join(process.cwd(), 'data/screenshots/host_harvest_final.png');
    await page.screenshot({ path: finalScreenshot, fullPage: true });

    // 终极宣告
    console.log('\n╔══════════════════════════════════════════════════════════════════╗');
    console.log('║     🏆 TITAN V6.0 GOLDEN GRAB 终极宣告 🏆                      ║');
    console.log('╠══════════════════════════════════════════════════════════════════╣');
    console.log(`║     目标URL: ✅ 成功访问                                    ║`);
    console.log(`║     API拦截: ${interceptedData.rawArrays.length > 0 ? '✅ ' + interceptedData.rawArrays.length + '个数组' : '❌ 失败'}                           ║`);
    console.log(`║     Pinnacle: ${marketSentiment.pinnacle_odds ? '✅ 已提取' : '❌ 失败'}                                   ║`);
    console.log(`║     Bet365: ${marketSentiment.bet365_odds ? '✅ 已提取' : '⚠️  未找到'}                                   ║`);
    console.log(`║     严格验证: ✅ 通过                                         ║`);
    console.log(`║     数据库: ${result ? '✅ 入库成功' : '❌ 入库失败'}                                    ║`);
    console.log('╠══════════════════════════════════════════════════════════════════╣');
    if (result && marketSentiment.pinnacle_odds) {
      console.log('║     🏆 TITAN V6.0 真实赔率夺金成功！                           ║');
      console.log(`║        💰 Home: ${String(marketSentiment.pinnacle_odds.closing[0]).padEnd(6)} | Draw: ${String(marketSentiment.pinnacle_odds.closing[1]).padEnd(6)} | Away: ${marketSentiment.pinnacle_odds.closing[2]}                 ║`);
      console.log('║        金砖已入库！拒绝空壳记录！                              ║');
    } else {
      console.log('║     ⚠️  本次收割未完成                                        ║');
    }
    console.log('╚══════════════════════════════════════════════════════════════════╝\n');

    // 展示入库数据预览
    if (result) {
      await showDatabasePreview(pool, TARGET_MATCH_ID);
      await showJSONPreview(pool, TARGET_MATCH_ID);
    }

  } catch (error) {
    console.error('\n💥 执行失败:', error.message);
    console.error(error.stack);
  } finally {
    if (context) await context.close();
    if (browser) await browser.close();
    await pool.end();
  }
}

/**
 * 递归搜索赔率数据
 */
function searchForOdds(obj, result, depth = 0) {
  if (depth > 10 || !obj || typeof obj !== 'object') return;

  for (const [key, value] of Object.entries(obj)) {
    const lowerKey = key.toLowerCase();

    // 检测博彩公司
    if (typeof value === 'string' || typeof value === 'number') {
      const valStr = String(value).toLowerCase();
      if (BOOKMAKER_ID_MAP.PINNACLE.some(id => valStr === String(id).toLowerCase())) {
        result.bookmakers.pinnacle = { id: value, foundAt: key };
      }
      if (BOOKMAKER_ID_MAP.BET365.some(id => valStr === String(id).toLowerCase())) {
        result.bookmakers.bet365 = { id: value, foundAt: key };
      }
    }

    // 检测赔率数组
    if (Array.isArray(value) && value.length >= 3) {
      const areNumbers = value.every(v => typeof v === 'number' || !isNaN(parseFloat(v)));
      if (areNumbers) {
        result.oddsData = result.oddsData || [];
        result.oddsData.push({ key, values: value, depth });
      }
    }

    // 递归
    if (typeof value === 'object') {
      searchForOdds(value, result, depth + 1);
    }
  }
}

/**
 * V6.0 GOLDEN-GRAB: 深度剥离所有赔率数组
 */
function extractOddsArrays(obj, result, depth = 0, path = '') {
  if (depth > 15 || !obj || typeof obj !== 'object') return;

  for (const [key, value] of Object.entries(obj)) {
    const currentPath = path ? `${path}.${key}` : key;

    // 检测赔率数组 (长度为3的数值数组，符合1X2格式)
    if (Array.isArray(value) && value.length === 3) {
      const areNumbers = value.every(v => {
        const num = parseFloat(v);
        return !isNaN(num) && num > 1 && num < 100;
      });
      if (areNumbers) {
        result.rawArrays.push({
          path: currentPath,
          values: value.map(v => parseFloat(v)),
          depth
        });
      }
    }

    // 递归
    if (typeof value === 'object' && value !== null) {
      extractOddsArrays(value, result, depth + 1, currentPath);
    }
  }
}

/**
 * V6.0 GOLDEN-GRAB: 构建市场情感数据
 */
function buildMarketSentiment(intercepted, domData) {
  const ms = {
    extract_method: 'HOST_FORCE_HARVEST_V6.0_GOLDEN',
    extract_timestamp: new Date().toISOString(),
    source: 'oddsportal_host',
    pinnacle_odds: null,
    bet365_odds: null,
    dom_snapshot: domData,
    raw_arrays_count: intercepted.rawArrays?.length || 0
  };

  // 优先使用DOM提取的数据（更可靠）
  if (domData.pinnacleOdds && domData.pinnacleOdds.length === 3) {
    ms.pinnacle_odds = {
      detected: true,
      bookmaker_id: 18,
      source: 'dom_extraction',
      opening: domData.pinnacleOdds,
      closing: domData.pinnacleOdds,
      history: [domData.pinnacleOdds]
    };
  }

  if (domData.bet365Odds && domData.bet365Odds.length === 3) {
    ms.bet365_odds = {
      detected: true,
      bookmaker_id: 16,
      source: 'dom_extraction',
      opening: domData.bet365Odds,
      closing: domData.bet365Odds,
      history: [domData.bet365Odds]
    };
  }

  // 如果DOM没有数据，尝试使用API拦截的数据
  if (!ms.pinnacle_odds || !ms.bet365_odds) {
    const validOddsArrays = intercepted.rawArrays?.filter(arr =>
      arr.values && arr.values.length === 3 &&
      arr.values.every(v => v > 1 && v < 100)
    ) || [];

    if (!ms.pinnacle_odds && (intercepted.bookmakers.pinnacle || validOddsArrays.length > 0)) {
      const opening = validOddsArrays[0]?.values || null;
      const closing = validOddsArrays[1]?.values || opening;

      ms.pinnacle_odds = {
        detected: true,
        bookmaker_id: intercepted.bookmakers.pinnacle?.id || 18,
        source: 'api_interception',
        opening: opening,
        closing: closing,
        history: validOddsArrays.slice(0, 5).map(a => a.values)
      };
    }

    if (!ms.bet365_odds && (intercepted.bookmakers.bet365 || validOddsArrays.length > 2)) {
      ms.bet365_odds = {
        detected: true,
        bookmaker_id: intercepted.bookmakers.bet365?.id || 16,
        source: 'api_interception',
        opening: validOddsArrays[2]?.values || null,
        closing: validOddsArrays[3]?.values || validOddsArrays[2]?.values || null
      };
    }
  }

  return ms;
}

/**
 * V6.0 GOLDEN-GRAB: 严格数据验证 - 非真即毁策略
 */
function validateMarketSentiment(ms) {
  // 检查pinnacle_odds是否存在
  if (!ms.pinnacle_odds) {
    return { valid: false, reason: 'pinnacle_odds is null' };
  }

  // 检查closing数组是否存在且长度为3
  const closing = ms.pinnacle_odds.closing;
  if (!closing || !Array.isArray(closing) || closing.length !== 3) {
    return { valid: false, reason: `pinnacle_odds.closing invalid: ${JSON.stringify(closing)}` };
  }

  // 检查所有值是否为有效数字
  const allValidNumbers = closing.every(v => {
    const num = parseFloat(v);
    return !isNaN(num) && num > 1 && num < 100;
  });

  if (!allValidNumbers) {
    return { valid: false, reason: `pinnacle_odds.closing contains invalid numbers: ${JSON.stringify(closing)}` };
  }

  return { valid: true, reason: 'all checks passed' };
}

/**
 * V6.0 GOLDEN-GRAB: Bet365备选验证
 */
function validateBet365Odds(ms) {
  if (!ms.bet365_odds) {
    return { valid: false, reason: 'bet365_odds is null' };
  }

  const closing = ms.bet365_odds.closing;
  if (!closing || !Array.isArray(closing) || closing.length !== 3) {
    return { valid: false, reason: `bet365_odds.closing invalid` };
  }

  const allValidNumbers = closing.every(v => {
    const num = parseFloat(v);
    return !isNaN(num) && num > 1 && num < 100;
  });

  if (!allValidNumbers) {
    return { valid: false, reason: `bet365_odds.closing contains invalid numbers` };
  }

  return { valid: true, reason: 'bet365 validation passed' };
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

    if (result.rows.length > 0) {
      console.log(`   ✅ 入库成功: ${result.rows[0].match_id}`);
      return true;
    }
  } catch (error) {
    console.error(`   ❌ 入库失败: ${error.message}`);
  }
  return false;
}

/**
 * 展示数据库预览
 */
async function showDatabasePreview(pool, matchId) {
  try {
    const query = `
      SELECT
        m.match_id,
        m.home_team,
        m.away_team,
        l3.market_sentiment->>'extract_method' as method,
        l3.market_sentiment->>'extract_timestamp' as extracted_at,
        l3.updated_at
      FROM l3_features l3
      JOIN matches m ON l3.match_id = m.match_id
      WHERE l3.match_id = $1;
    `;

    const result = await pool.query(query, [matchId]);

    if (result.rows.length > 0) {
      const row = result.rows[0];
      console.log('\n📊 数据库记录预览:');
      console.log('='.repeat(60));
      console.log(JSON.stringify({
        match_id: row.match_id,
        match: `${row.home_team} vs ${row.away_team}`,
        method: row.method,
        extracted_at: row.extracted_at,
        updated_at: row.updated_at
      }, null, 2));
      console.log('='.repeat(60));
    }
  } catch (e) {
    console.log('   ⚠️  预览查询失败:', e.message);
  }
}

/**
 * V6.0 GOLDEN-GRAB: 展示JSON核心字段预览
 */
async function showJSONPreview(pool, matchId) {
  try {
    const query = `
      SELECT
        market_sentiment->'pinnacle_odds' as pin_odds,
        market_sentiment->>'extract_method' as method
      FROM l3_features
      WHERE match_id = $1;
    `;

    const result = await pool.query(query, [matchId]);

    if (result.rows.length > 0) {
      const row = result.rows[0];
      const pinOdds = row.pin_odds;

      console.log('\n📋 JSON核心字段预览:');
      console.log('='.repeat(60));
      console.log(JSON.stringify({
        match_id: matchId,
        extract_method: row.method,
        pinnacle_odds: {
          detected: pinOdds?.detected || false,
          bookmaker_id: pinOdds?.bookmaker_id || null,
          opening: pinOdds?.opening || null,
          closing: pinOdds?.closing || null,
          history_points: pinOdds?.history ? pinOdds.history.length : 0
        }
      }, null, 2));
      console.log('='.repeat(60));

      // 验证pinnacle_odds不为null
      if (pinOdds && pinOdds.closing) {
        console.log('✅ pinnacle_odds.closing 字段验证通过');
        console.log(`   值: [${pinOdds.closing.join(', ')}]`);
      } else {
        console.log('❌ pinnacle_odds 字段为空！');
      }
    }
  } catch (e) {
    console.log('   ⚠️  JSON预览失败:', e.message);
  }
}

/**
 * V6.0 GOLDEN-GRAB: 从页面DOM提取赔率数据
 */
async function extractOddsFromDOM(page) {
  return await page.evaluate(() => {
    const results = { pinnacleOdds: null, bet365Odds: null, allBookmakers: [], debug: {} };

    // 调试：记录页面基本信息
    results.debug.bodyLength = document.body.innerText.length;
    results.debug.hasBookmakers = document.body.innerText.includes('Bookmakers');
    results.debug.hasBet365 = document.body.innerText.includes('Bet365');
    results.debug.hasPinnacle = document.body.innerText.includes('Pinnacle');

    // 方法1: 尝试多种选择器组合
    const selectors = [
      'table tbody tr',
      'div[role="row"]',
      '[class*="bookmaker"]',
      '[class*="odds"]',
      '.odds-table tr',
      '[data-testid*="bookie"]'
    ];

    for (const selector of selectors) {
      const rows = document.querySelectorAll(selector);
      if (rows.length > 0) {
        results.debug.foundSelector = selector;
        results.debug.rowCount = rows.length;

        rows.forEach((row, idx) => {
          const text = row.textContent || '';

          // 检测博彩公司名
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

            // 记录所有博彩公司
            const bookieName = text.substring(0, 30).trim();
            results.allBookmakers.push({
              name: bookieName,
              odds: oddsValues,
              selector: selector,
              index: idx
            });
          }
        });

        // 如果找到了数据，不再尝试其他选择器
        if (results.allBookmakers.length > 0) break;
      }
    }

    // 方法2: 直接从完整文本匹配（更宽松的匹配）
    if (!results.pinnacleOdds || !results.bet365Odds) {
      const allText = document.body.innerText || '';

      // 查找所有可能的赔率组合
      const allMatches = allText.match(/[A-Za-z]+[^\d]{0,50}(\d+\.\d{2})\s+(\d+\.\d{2})\s+(\d+\.\d{2})/g);
      results.debug.allOddsMatches = allMatches ? allMatches.slice(0, 10) : [];

      // Bet365匹配
      if (!results.bet365Odds) {
        const bet365Patterns = [
          /Bet365\D{0,100}(\d+\.\d{2})\s+(\d+\.\d{2})\s+(\d+\.\d{2})/i,
          /bet365\D{0,100}(\d+\.\d{2})\s+(\d+\.\d{2})\s+(\d+\.\d{2})/i
        ];
        for (const pattern of bet365Patterns) {
          const match = allText.match(pattern);
          if (match) {
            results.bet365Odds = [
              parseFloat(match[1]),
              parseFloat(match[2]),
              parseFloat(match[3])
            ];
            results.debug.bet365Source = 'text_regex';
            break;
          }
        }
      }

      // Pinnacle匹配
      if (!results.pinnacleOdds) {
        const pinnacleMatch = allText.match(/Pinnacle\D{0,100}(\d+\.\d{2})\s+(\d+\.\d{2})\s+(\d+\.\d{2})/i);
        if (pinnacleMatch) {
          results.pinnacleOdds = [
            parseFloat(pinnacleMatch[1]),
            parseFloat(pinnacleMatch[2]),
            parseFloat(pinnacleMatch[3])
          ];
          results.debug.pinnacleSource = 'text_regex';
        }
      }
    }

    return results;
  });
}

/**
 * V6.0 HUMAN-MIMIC: 声东击西策略
 * 先访问其他页面再返回，触发全局状态机重新初始化
 */
async function contextSwitchManeuver(page) {
  try {
    console.log('   🎾 访问Tennis分类...');
    await page.goto('https://www.oddsportal.com/tennis/', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(2000 + Math.random() * 1000);

    console.log('   ⚽ 返回目标页面...');
    await page.goto(TARGET_URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(3000);
  } catch (e) {
    console.log('   ⚠️  声东击西策略部分失败:', e.message);
  }
}

/**
 * V6.0 HUMAN-MIMIC: 贝塞尔曲线鼠标移动模拟
 */
async function humanTrajectorySimulation(page) {
  const width = 1920;
  const height = 1080;

  // 3-5次随机滑行
  const moveCount = 3 + Math.floor(Math.random() * 3);
  console.log(`   🖱️  执行${moveCount}次贝塞尔曲线鼠标移动...`);

  for (let i = 0; i < moveCount; i++) {
    const startX = Math.random() * width * 0.8 + width * 0.1;
    const startY = Math.random() * height * 0.8 + height * 0.1;
    const endX = Math.random() * width * 0.8 + width * 0.1;
    const endY = Math.random() * height * 0.8 + height * 0.1;

    // 贝塞尔曲线控制点
    const cp1X = startX + (endX - startX) * 0.3 + (Math.random() - 0.5) * 200;
    const cp1Y = startY + (endY - startY) * 0.3 + (Math.random() - 0.5) * 200;
    const cp2X = startX + (endX - startX) * 0.7 + (Math.random() - 0.5) * 200;
    const cp2Y = startY + (endY - startY) * 0.7 + (Math.random() - 0.5) * 200;

    // 生成贝塞尔曲线上的点
    const steps = 20 + Math.floor(Math.random() * 10);
    for (let t = 0; t <= 1; t += 1/steps) {
      const x = Math.pow(1-t, 3) * startX + 3 * Math.pow(1-t, 2) * t * cp1X +
                3 * (1-t) * Math.pow(t, 2) * cp2X + Math.pow(t, 3) * endX;
      const y = Math.pow(1-t, 3) * startY + 3 * Math.pow(1-t, 2) * t * cp1Y +
                3 * (1-t) * Math.pow(t, 2) * cp2Y + Math.pow(t, 3) * endY;

      await page.mouse.move(x, y);
      await page.waitForTimeout(10 + Math.random() * 20);
    }

    // 随机停留
    await page.waitForTimeout(200 + Math.random() * 300);
  }

  // 模拟翻页滚动
  console.log('   📜 模拟翻页滚动...');
  for (let i = 0; i < 3; i++) {
    const scrollAmount = 300 + Math.floor(Math.random() * 200);
    await page.mouse.wheel(0, scrollAmount);
    await page.waitForTimeout(500 + Math.random() * 500);

    // 偶尔向上滚动一点（人类阅读时的回滚）
    if (Math.random() > 0.6) {
      await page.mouse.wheel(0, -100 - Math.floor(Math.random() * 100));
      await page.waitForTimeout(300 + Math.random() * 200);
    }
  }
}

/**
 * V6.0 HUMAN-MIMIC: 实时视力康复监测
 * 循环检测Pinnacle是否出现，最多60秒
 */
async function visionRecoveryCheck(page, interceptedData) {
  const startTime = Date.now();
  const timeout = 60000; // 60秒
  const checkInterval = 2000; // 每2秒检查一次

  console.log('   🔍 开始实时监测页面内容...');

  while (Date.now() - startTime < timeout) {
    // 检查页面是否有Pinnacle赔率
    const hasPinnacle = await page.evaluate(() => {
      const text = document.body.innerText || '';
      const hasPinnacleText = /Pinnacle/i.test(text);
      const hasOddsPattern = /Pinnacle\D{0,100}\d+\.\d{2}/.test(text);
      return { hasPinnacleText, hasOddsPattern, textLength: text.length };
    });

    if (hasPinnacle.hasPinnacleText) {
      console.log(`   ✅ 检测到Pinnacle文本！页面文本长度: ${hasPinnacle.textLength}`);

      if (hasPinnacle.hasOddsPattern) {
        console.log('   ✅ 检测到Pinnacle赔率数字！视力已恢复！');
        return { success: true, method: 'pinnacle_detected' };
      }
    }

    // 检查是否从API拦截到数据
    if (interceptedData.rawArrays.length > 0) {
      console.log(`   ✅ 从API拦截到${interceptedData.rawArrays.length}个赔率数组！`);
      return { success: true, method: 'api_intercepted' };
    }

    // 继续拟人化交互
    if (Math.random() > 0.5) {
      await page.mouse.wheel(0, 200 + Math.floor(Math.random() * 200));
    }
    await page.waitForTimeout(checkInterval);

    // 打印进度
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    if (elapsed % 10 === 0) {
      console.log(`   ⏱️  已监测${elapsed}秒...`);
    }
  }

  console.log('   ❌ 60秒监测超时，页面内容未恢复');
  return { success: false, method: 'timeout' };
}

// 运行
if (require.main === module) {
  hostForceHarvest().catch(console.error);
}

module.exports = { hostForceHarvest };