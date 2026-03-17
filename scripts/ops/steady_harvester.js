/**
 * TITAN V6.0 STEADY HARVESTER - 稳健收割协议
 * ==========================================
 * 阵地战节奏：随机延迟 + 重试逻辑 + 容错熔断
 * 
 * @module scripts/ops/steady_harvester
 * @version V6.0-STEADY-PROTOCOL
 */

'use strict';

const { chromium } = require('playwright');
const { Pool } = require('pg');
const fs = require('fs');
const path = require('path');

// 载入模块化组件
const {
  silentHarvestLoop
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

// 熔断配置
const CIRCUIT_BREAKER = {
  maxConsecutiveFailures: 5,
  max404Rate: 0,  // 0% 404容忍
  maxFailureRate: 0.30,  // 30% 连续失败率触发熔断
  cooldownMinutes: 10
};

// 延迟配置
const DELAY_CONFIG = {
  preNavigation: { min: 5000, max: 15000 },   // 导航前 5-15秒
  postFailure: { min: 20000, max: 30000 },    // 失败后 20-30秒
  sessionCheck: 20  // 每20场检查session
};

/**
 * 随机延迟
 */
async function humanBreath(min, max) {
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
 * 检查Session存活
 */
async function checkSessionAlive(page) {
  try {
    const isAlive = await page.evaluate(() => {
      return document.body && document.body.textContent.length > 100;
    });
    return isAlive;
  } catch {
    return false;
  }
}

/**
 * 单场比赛收割（带重试）
 */
async function harvestSingleMatch(page, context, target, sessionData, stats) {
  const maxRetries = 2;
  let lastError = null;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    if (attempt > 0) {
      console.log(`\n🔄 [TACTICAL RETRY] 第${attempt}/${maxRetries}次重试...`);
      // Cookie清理 + 长延迟
      console.log('   🧹 清理Cookies...');
      await context.clearCookies();
      if (sessionData) {
        await context.addCookies(sessionData.cookies || []);
      }
      await humanBreath(DELAY_CONFIG.postFailure.min, DELAY_CONFIG.postFailure.max);
    }

    try {
      console.log(`\n🌐 正在加载页面...`);
      console.log(`   URL: ${target.url}`);

      const response = await page.goto(target.url, {
        waitUntil: 'domcontentloaded',
        timeout: 45000
      });

      // 404检测
      if (response && response.status() === 404) {
        stats.notFound404++;
        console.log('   ❌ 404错误 - 地址失效');
        return { success: false, error: '404', fatal: true };
      }

      stats.titleLoaded++;
      const pageTitle = await page.title();
      console.log(`   ✅ 页面加载完成: ${pageTitle}`);

      // 静默收割
      const parser = { extractOddsFromDOM, buildMarketSentiment };
      const result = await silentHarvestLoop(page, context, sessionData, parser);

      if (result.healingTriggered) {
        stats.healingTriggered++;
      }

      if (result.success && result.data) {
        const hasValidData = (result.data.pinnacle_odds?.closing?.length === 3) ||
                             (result.data.bet365_odds?.closing?.length === 3);

        if (hasValidData) {
          const upsertResult = await upsertToDatabase(stats.pool, target.match_id, result.data);

          if (upsertResult) {
            stats.consecutiveFailures = 0; // 重置连续失败计数
            return {
              success: true,
              data: result.data,
              healing: result.healingTriggered,
              attempts: attempt + 1
            };
          }
        }
      }

      // 数据提取失败但页面正常，不重试
      return { success: false, error: 'no_data', fatal: false };

    } catch (error) {
      lastError = error;
      console.log(`   💥 错误: ${error.message}`);

      // 网络错误，继续重试
      if (error.message.includes('Timeout') ||
          error.message.includes('ERR_HTTP_RESPONSE') ||
          error.message.includes('net::ERR')) {
        continue;
      }

      // 其他错误，不重试
      return { success: false, error: error.message, fatal: true };
    }
  }

  // 重试耗尽
  stats.consecutiveFailures++;
  return { success: false, error: lastError?.message || 'Max retries exceeded', fatal: false };
}

/**
 * 检查熔断条件
 */
function checkCircuitBreaker(stats) {
  // 404率检查
  if (stats.notFound404 > 0) {
    return {
      triggered: true,
      reason: `404错误率 > 0% (${stats.notFound404}次)`,
      action: 'IMMEDIATE_HALT'
    };
  }

  // 连续失败率检查
  if (stats.consecutiveFailures >= CIRCUIT_BREAKER.maxConsecutiveFailures) {
    const failureRate = stats.consecutiveFailures / CIRCUIT_BREAKER.maxConsecutiveFailures;
    if (failureRate >= 1.0) {
      return {
        triggered: true,
        reason: `连续失败 ${stats.consecutiveFailures} 次，超过阈值`,
        action: 'COOLDOWN_10MIN'
      };
    }
  }

  return { triggered: false };
}

/**
 * 稳健收割主函数
 */
async function steadyHarvest(strikeQueue, options = {}) {
  console.log('\n╔══════════════════════════════════════════════════════════════════╗');
  console.log('║     ⚔️  TITAN V6.0 STEADY HARVESTER - 稳健收割协议 ⚔️          ║');
  console.log('║     阵地战节奏：延迟 + 重试 + 熔断                             ║');
  console.log('╚══════════════════════════════════════════════════════════════════╝\n');

  const pool = new Pool(DB_CONFIG);
  let browser = null;
  let context = null;

  // 统计
  const stats = {
    pool,
    total: strikeQueue.length,
    success: 0,
    failed: 0,
    notFound404: 0,
    titleLoaded: 0,
    healingTriggered: 0,
    consecutiveFailures: 0,
    startTime: Date.now(),
    results: []
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
      headless: options.headless !== false,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--window-size=1920,1080'
      ]
    });

    const contextConfig = {
      viewport: { width: 1920, height: 1080 },
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    };

    if (sessionData) {
      contextConfig.storageState = sessionData;
    }

    context = await browser.newContext(contextConfig);
    const page = await context.newPage();

    // 注入stealth
    await context.addInitScript(() => {
      Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    });

    // 主循环
    for (let idx = 0; idx < strikeQueue.length; idx++) {
      const target = strikeQueue[idx];

      console.log('\n' + '='.repeat(70));
      console.log(`[${idx + 1}/${stats.total}] ⚔️  ${target.match_name}`);
      console.log(`     🏆 League: ${target.league}`);
      console.log(`     🆔 Match ID: ${target.match_id}`);
      console.log(`     🔗 Hash: ${target.hash}`);
      console.log(`     📅 Date: ${new Date(target.match_date).toLocaleDateString()}`);
      console.log('='.repeat(70));

      // 熔断检查
      const breaker = checkCircuitBreaker(stats);
      if (breaker.triggered) {
        console.log('\n╔══════════════════════════════════════════════════════════════════╗');
        console.log('║     🚨 CIRCUIT BREAKER TRIGGERED - 全局熔断 🚨                 ║');
        console.log(`║     原因: ${breaker.reason}`);
        console.log(`║     动作: ${breaker.action}`);
        console.log('╚══════════════════════════════════════════════════════════════════╝\n');
        break;
      }

      // Human Breath - 导航前随机延迟
      await humanBreath(DELAY_CONFIG.preNavigation.min, DELAY_CONFIG.preNavigation.max);

      // 执行收割
      const result = await harvestSingleMatch(page, context, target, sessionData, stats);

      // 记录结果
      stats.results.push({
        match_id: target.match_id,
        match_name: target.match_name,
        success: result.success,
        attempts: result.attempts || 1,
        healing: result.healing || false,
        error: result.error || null
      });

      if (result.success) {
        stats.success++;
        const bet365 = result.data.bet365_odds?.closing?.join(', ') || 'N/A';
        console.log(`\n💎 [GOLD ACQUIRED] ${target.match_name}`);
        console.log(`     Bet365: [${bet365}]`);
        console.log(`     Attempts: ${result.attempts}`);
        console.log(`     Healing: ${result.healing ? 'Yes' : 'No'}`);
      } else {
        stats.failed++;
        console.log(`\n❌ [FAILED] ${target.match_name}`);
        console.log(`     Error: ${result.error}`);
      }

      // 每20场检查session
      if ((idx + 1) % DELAY_CONFIG.sessionCheck === 0) {
        console.log('\n🔍 [SESSION CHECK] 检查Session存活...');
        const isAlive = await checkSessionAlive(page);
        if (!isAlive) {
          console.log('   ⚠️  Session已失效，尝试恢复...');
          await context.close();
          context = await browser.newContext(contextConfig);
          const newPage = await context.newPage();
          await context.addInitScript(() => {
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
          });
        } else {
          console.log('   ✅ Session正常');
        }
      }
    }

  } finally {
    if (context) await context.close();
    if (browser) await browser.close();
    await pool.end();
  }

  return stats;
}

/**
 * 生成战报
 */
function generateReport(stats) {
  const totalDuration = Date.now() - stats.startTime;
  const notFoundRate = ((stats.notFound404 / stats.total) * 100).toFixed(1);
  const titleSuccessRate = ((stats.titleLoaded / stats.total) * 100).toFixed(1);
  const realSuccessRate = stats.titleLoaded > 0
    ? ((stats.success / stats.titleLoaded) * 100).toFixed(1)
    : 0;

  console.log('\n\n╔══════════════════════════════════════════════════════════════════╗');
  console.log('║     📊 STEADY HARVESTER - 稳健收割战报 📊                      ║');
  console.log('╠══════════════════════════════════════════════════════════════════╣');
  console.log(`║     📋 总打击数: ${String(stats.total).padStart(3)}                                          ║`);
  console.log(`║     ✅ 成功入库: ${String(stats.success).padStart(3)}                                          ║`);
  console.log(`║     ❌ 失败: ${String(stats.failed).padStart(3)}                                              ║`);
  console.log(`║     📈 总成功率: ${String(((stats.success / stats.total) * 100).toFixed(1)).padStart(5)}%                                  ║`);
  console.log(`║                                                                  ║`);
  console.log(`║     🚫 404错误: ${String(stats.notFound404).padStart(3)} 次 (${String(notFoundRate).padStart(5)}%)                              ║`);
  console.log(`║     📄 标题加载: ${String(stats.titleLoaded).padStart(3)}/${String(stats.total).padStart(3)} (${String(titleSuccessRate).padStart(5)}%)                          ║`);
  console.log(`║     🎯 真实入库率: ${String(realSuccessRate).padStart(5)}% (去除网络因素)                    ║`);
  console.log(`║                                                                  ║`);
  console.log(`║     🏥 视觉康复触发: ${String(stats.healingTriggered).padStart(3)} 次                               ║`);
  console.log(`║                                                                  ║`);
  console.log(`║     ⏱️  总耗时: ${String((totalDuration / 1000).toFixed(0)).padStart(4)} 秒                                  ║`);
  console.log(`║     ⏱️  场均耗时: ${String((totalDuration / stats.total / 1000).toFixed(1)).padStart(4)} 秒                              ║`);
  console.log('╚══════════════════════════════════════════════════════════════════╝\n');

  return {
    ...stats,
    metrics: {
      notFoundRate: parseFloat(notFoundRate),
      titleSuccessRate: parseFloat(titleSuccessRate),
      realSuccessRate: parseFloat(realSuccessRate),
      totalDuration,
      avgDurationPerMatch: totalDuration / stats.total
    }
  };
}

module.exports = {
  steadyHarvest,
  generateReport,
  humanBreath,
  CIRCUIT_BREAKER
};