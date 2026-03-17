/**
 * TITAN V6.0 OMNI LIVE PROBE - 集成测试
 * =====================================
 * 在真实OddsPortal页面上验证全维度嗅探器
 * 
 * @module tests/integration/omni_live_probe
 * @version V6.0-LIVE-PROBE
 * @date 2026-03-16
 */

'use strict';

const { test, describe, before, after } = require('node:test');
const assert = require('node:assert');
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

// 测试配置
const TEST_CONFIG = {
  targetUrl: 'https://www.oddsportal.com/football/england/premier-league/fulham-burnley-8EamNN8b/',
  maxWaitTime: 30000, // 30秒
  checkInterval: 500,
  headless: false // GUI模式便于观察
};

describe('TITAN V6.0 OMNI LIVE PROBE - 实境集成测试', () => {
  let browser;
  let context;
  let page;
  let snifferState;

  before(async () => {
    console.log('\n🔧 [SETUP] 启动浏览器...');
    browser = await chromium.launch({
      headless: TEST_CONFIG.headless,
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1920,1080']
    });

    // 加载黄金会话
    const sessionPath = path.join(process.cwd(), 'data/sessions/auth_gold.json');
    let storageState = null;
    try {
      storageState = JSON.parse(fs.readFileSync(sessionPath, 'utf-8'));
      console.log('✅ 黄金会话已加载');
    } catch (e) {
      console.log('⚠️  未找到黄金会话，使用空会话');
    }

    context = await browser.newContext({
      viewport: { width: 1920, height: 1080 },
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
      storageState: storageState
    });

    page = await context.newPage();
    
    // 初始化状态对象
    snifferState = {
      injected: false,
      hasConfig: false,
      hasOddsStream: false,
      ready: false,
      goldenHits: 0,
      channels: { ws: 0, fetch: 0, xhr: 0, json: 0 },
      capturedData: []
    };
  });

  after(async () => {
    console.log('\n🔧 [TEARDOWN] 关闭浏览器...');
    if (context) await context.close();
    if (browser) await browser.close();
  });

  // ============================================================================
  // TEST A: Sniffer注入验证
  // ============================================================================
  test('A. window.__titan_omni_sniffer_injected 必须为 true', async () => {
    console.log('\n📡 [TEST A] 验证Sniffer注入...');

    // 注入Omni Sniffer
    await page.exposeFunction('__titan_emit_stream', (stream) => {
      snifferState.capturedData.push(stream);
      
      if (stream.type === 'CONFIG_JSON') {
        snifferState.hasConfig = true;
      }
      if (stream.type === 'GOLDEN_STREAM') {
        snifferState.hasOddsStream = true;
        snifferState.goldenHits++;
      }
      
      if (stream.channel) {
        snifferState.channels[stream.channel]++;
      }
      
      if (snifferState.hasConfig && snifferState.hasOddsStream) {
        snifferState.ready = true;
      }
    });

    // 注入脚本
    await page.addInitScript(() => {
      const ODDS_PATTERN = /(\d+\.\d{2}).*?(\d+\.\d{2}).*?(\d+\.\d{2})/;
      const TIMESTAMP_PATTERN = /\d{10}(?!\d)/g;
      const TARGET_KEYS = ['userData', 'bookiehash', 'oddsdata'];

      // WebSocket拦截
      const OriginalWebSocket = window.WebSocket;
      window.WebSocket = function(url, protocols) {
        const ws = new OriginalWebSocket(url, protocols);
        ws.addEventListener('message', (event) => {
          const text = typeof event.data === 'string' ? event.data : '';
          const hasOdds = ODDS_PATTERN.test(text);
          const hasTs = TIMESTAMP_PATTERN.test(text);
          if (hasOdds || hasTs) {
            window.__titan_emit_stream({
              channel: 'ws',
              url: url,
              type: (hasOdds && hasTs) ? 'GOLDEN_STREAM' : 'ODDS_RELATED',
              timestamp: Date.now(),
              sample: text.substring(0, 200),
              size: text.length
            });
          }
        });
        return ws;
      };
      Object.setPrototypeOf(window.WebSocket, OriginalWebSocket);

      // Fetch拦截
      const originalFetch = window.fetch;
      window.fetch = async function(url, options) {
        const response = await originalFetch.apply(this, arguments);
        try {
          const cloned = response.clone();
          const text = await cloned.text();
          const hasOdds = ODDS_PATTERN.test(text);
          const hasTs = TIMESTAMP_PATTERN.test(text);
          
          let isConfig = false;
          try {
            const json = JSON.parse(text);
            isConfig = TARGET_KEYS.some(key => json.hasOwnProperty(key));
            if (isConfig) {
              window.__titan_emit_stream({ channel: 'fetch', url, type: 'CONFIG_JSON', keys: Object.keys(json) });
            }
          } catch (e) {}
          
          if (!isConfig && (hasOdds || hasTs)) {
            window.__titan_emit_stream({
              channel: 'fetch',
              url,
              type: (hasOdds && hasTs) ? 'GOLDEN_STREAM' : 'ODDS_RELATED',
              sample: text.substring(0, 200),
              size: text.length
            });
          }
        } catch (e) {}
        return response;
      };

      // XHR拦截
      const OriginalXHR = window.XMLHttpRequest;
      window.XMLHttpRequest = function() {
        const xhr = new OriginalXHR();
        const originalSend = xhr.send;
        xhr.send = function(body) {
          const onReady = () => {
            if (xhr.readyState === 4 && xhr.responseText) {
              const text = xhr.responseText;
              const hasOdds = ODDS_PATTERN.test(text);
              const hasTs = TIMESTAMP_PATTERN.test(text);
              
              try {
                const json = JSON.parse(text);
                if (TARGET_KEYS.some(key => json.hasOwnProperty(key))) {
                  window.__titan_emit_stream({ channel: 'xhr', url: xhr.responseURL, type: 'CONFIG_JSON' });
                  return;
                }
              } catch (e) {}
              
              if (hasOdds || hasTs) {
                window.__titan_emit_stream({
                  channel: 'xhr',
                  url: xhr.responseURL,
                  type: (hasOdds && hasTs) ? 'GOLDEN_STREAM' : 'ODDS_RELATED',
                  sample: text.substring(0, 200),
                  size: text.length
                });
              }
            }
          };
          xhr.addEventListener('load', onReady);
          return originalSend.apply(xhr, arguments);
        };
        return xhr;
      };

      window.__titan_omni_sniffer_injected = true;
    });

    // 验证注入
    const injected = await page.evaluate(() => window.__titan_omni_sniffer_injected === true);
    assert.strictEqual(injected, true, 'Omni Sniffer必须成功注入');
    snifferState.injected = true;
    console.log('✅ Sniffer注入成功');
  });

  // ============================================================================
  // TEST B: 访问真实URL并捕获数据流
  // ============================================================================
  test('B. 在30秒内必须捕获到赔率数据流', async () => {
    console.log(`\n📡 [TEST B] 访问真实URL: ${TEST_CONFIG.targetUrl}`);
    
    // 导航到页面
    try {
      await page.goto(TEST_CONFIG.targetUrl, { 
        waitUntil: 'networkidle',
        timeout: 60000 
      });
    } catch (e) {
      console.log('⚠️  页面加载超时，继续测试...');
    }

    console.log('   页面加载完成，等待数据流捕获...');

    // 执行拟人化交互
    await page.mouse.move(500, 500);
    await page.mouse.wheel(0, 300);
    await page.waitForTimeout(2000);

    // 等待30秒
    const startTime = Date.now();
    while (Date.now() - startTime < TEST_CONFIG.maxWaitTime) {
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      process.stdout.write(`   等待中... ${elapsed}s | WS:${snifferState.channels.ws} Fetch:${snifferState.channels.fetch} XHR:${snifferState.channels.xhr}\r`);
      
      if (snifferState.hasOddsStream) {
        console.log(`\n✅ 捕获到赔率数据流！耗时 ${elapsed}秒`);
        break;
      }
      
      await page.waitForTimeout(TEST_CONFIG.checkInterval);
    }

    assert.strictEqual(snifferState.hasOddsStream, true, '必须在30秒内捕获到赔率数据流');
  });

  // ============================================================================
  // TEST C: 数据格式验证
  // ============================================================================
  test('C. 捕获数据必须符合赔率正则表达式', async () => {
    console.log('\n📡 [TEST C] 验证数据格式...');
    
    const oddsPattern = /(\d+\.\d{2},?){3,}/;
    let validDataCount = 0;
    
    for (const data of snifferState.capturedData) {
      if (data.sample && oddsPattern.test(data.sample)) {
        validDataCount++;
        console.log(`   ✅ 有效赔率数据 [${data.channel}]: ${data.sample.substring(0, 50)}...`);
      }
    }
    
    assert.strictEqual(validDataCount > 0, true, '必须捕获到符合格式的赔率数据');
    console.log(`✅ 共 ${validDataCount} 条有效赔率数据`);
  });

  // ============================================================================
  // TEST D: 全维度审计报告
  // ============================================================================
  test('D. 生成全维度审计报告', async () => {
    console.log('\n📊 [TEST D] 全维度审计报告');
    console.log('═══════════════════════════════════════════════════════════════');
    console.log('频道统计:');
    console.log(`   WebSocket:  ${snifferState.channels.ws} 次命中`);
    console.log(`   Fetch:      ${snifferState.channels.fetch} 次命中`);
    console.log(`   XHR:        ${snifferState.channels.xhr} 次命中`);
    console.log(`   JSON.parse: ${snifferState.channels.json} 次命中`);
    console.log('───────────────────────────────────────────────────────────────');
    console.log(`Golden Streams: ${snifferState.goldenHits}`);
    console.log(`Config JSON: ${snifferState.hasConfig ? '✅' : '❌'}`);
    console.log(`Odds Stream: ${snifferState.hasOddsStream ? '✅' : '❌'}`);
    console.log(`Ready State: ${snifferState.ready ? '✅' : '❌'}`);
    console.log('═══════════════════════════════════════════════════════════════');

    // 判断哪个频道是数据大动脉
    const maxChannel = Object.entries(snifferState.channels)
      .sort((a, b) => b[1] - a[1])[0];
    
    if (maxChannel[1] > 0) {
      console.log(`\n🏆 数据大动脉: ${maxChannel[0].toUpperCase()} 频道 (${maxChannel[1]} 次命中)`);
    }

    assert.strictEqual(snifferState.capturedData.length > 0, true, '必须捕获到数据');
  });
});

// ============================================================================
// 测试摘要
// ============================================================================

console.log('\n╔══════════════════════════════════════════════════════════════════════════════╗');
console.log('║     🧪 TITAN V6.0 OMNI LIVE PROBE - 实境集成测试                             ║');
console.log('║     在真实OddsPortal页面上验证全维度嗅探器                                     ║');
console.log('╚══════════════════════════════════════════════════════════════════════════════╝\n');
console.log('📋 测试场景:');
console.log('   A. Sniffer注入验证 - window.__titan_omni_sniffer_injected');
console.log('   B. 30秒数据捕获 - 必须触发赔率流');
console.log('   C. 格式验证 - 正则 (\\d+\\.\\d{2},?){3,}');
console.log('   D. 全维度审计 - 识别数据大动脉');
console.log('\n⚠️  警告: 此测试访问真实网站，请确保网络连接正常\n');
