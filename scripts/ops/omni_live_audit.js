/**
 * TITAN V6.0 OMNI LIVE AUDIT - 全维度实境审计
 * ===========================================
 * 对5场英超比赛执行全频段扫描，识别数据大动脉
 * 
 * @module scripts/ops/omni_live_audit
 * @version V6.0-OMNI-AUDIT
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
 * 注入Omni Sniffer到页面
 */
async function injectOmniSniffer(page, snifferState, isFirstInject = false) {
  // 只在第一次注入时注册exposeFunction
  if (isFirstInject) {
    await page.exposeFunction('__titan_emit_stream', (stream) => {
      snifferState.totalHits++;
      
      // 实时日志打印
      const timestamp = new Date().toISOString().split('T')[1].split('.')[0];
      if (stream.channel === 'ws') {
        console.log(`   📡 [WS-CHANNEL] HIT! Data size: ${stream.size || 0} bytes | ${timestamp}`);
      } else if (stream.channel === 'fetch') {
        console.log(`   📡 [FETCH-CHANNEL] HIT! URL: ${stream.url?.substring(0, 60)}... | ${timestamp}`);
      } else if (stream.channel === 'xhr') {
        console.log(`   📡 [XHR-CHANNEL] HIT! URL: ${stream.url?.substring(0, 60)}... | ${timestamp}`);
      }
      
      // 更新频道统计
      if (stream.channel) {
        snifferState.channels[stream.channel] = (snifferState.channels[stream.channel] || 0) + 1;
      }
      
      // 检查是否为GOLDEN_STREAM
      if (stream.type === 'GOLDEN_STREAM') {
        snifferState.goldenHits++;
        snifferState.goldenStreams.push(stream);
        console.log(`      💎 GOLDEN STREAM! Sample: ${stream.sample?.substring(0, 80)}...`);
      }
      
      // 检查是否包含赔率模式
      const oddsPattern = /(\d+\.\d{2}).*?(\d+\.\d{2}).*?(\d+\.\d{2})/;
      if (stream.sample && oddsPattern.test(stream.sample)) {
        const match = stream.sample.match(oddsPattern);
        if (match) {
          console.log(`      🎯 赔率捕获: [${match[1]}, ${match[2]}, ${match[3]}]`);
          snifferState.capturedOdds.push({
            channel: stream.channel,
            odds: [parseFloat(match[1]), parseFloat(match[2]), parseFloat(match[3])],
            timestamp: Date.now()
          });
        }
      }
      
      // 保存所有数据
      snifferState.allData.push(stream);
    });
  }

  // 注入拦截脚本
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
            sample: text.substring(0, 300),
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
            window.__titan_emit_stream({ 
              channel: 'fetch', 
              url, 
              type: 'CONFIG_JSON', 
              keys: Object.keys(json),
              size: text.length
            });
          }
        } catch (e) {}
        
        if (!isConfig && (hasOdds || hasTs)) {
          window.__titan_emit_stream({
            channel: 'fetch',
            url,
            type: (hasOdds && hasTs) ? 'GOLDEN_STREAM' : 'ODDS_RELATED',
            sample: text.substring(0, 300),
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
                window.__titan_emit_stream({ 
                  channel: 'xhr', 
                  url: xhr.responseURL, 
                  type: 'CONFIG_JSON',
                  size: text.length
                });
                return;
              }
            } catch (e) {}
            
            if (hasOdds || hasTs) {
              window.__titan_emit_stream({
                channel: 'xhr',
                url: xhr.responseURL,
                type: (hasOdds && hasTs) ? 'GOLDEN_STREAM' : 'ODDS_RELATED',
                sample: text.substring(0, 300),
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
    Object.setPrototypeOf(window.XMLHttpRequest, OriginalXHR);

    window.__titan_omni_sniffer_injected = true;
  });
}

/**
 * 主审计函数
 */
async function runOmniLiveAudit() {
  console.log('\n╔══════════════════════════════════════════════════════════════════════════════╗');
  console.log('║     🔬 TITAN V6.0 OMNI LIVE AUDIT - 全维度实境审计                           ║');
  console.log('║     5场英超比赛全频段扫描 | 识别数据大动脉                                   ║');
  console.log('╚══════════════════════════════════════════════════════════════════════════════╝\n');

  const pool = new Pool(DB_CONFIG);
  let browser;
  let context;

  // 审计统计
  const auditStats = {
    matches: [],
    totalHits: 0,
    goldenHits: 0,
    channelSummary: { ws: 0, fetch: 0, xhr: 0 },
    dataArtery: null
  };

  try {
    // 加载黄金会话
    const sessionPath = path.join(process.cwd(), 'data/sessions/auth_gold.json');
    let storageState = null;
    try {
      storageState = JSON.parse(fs.readFileSync(sessionPath, 'utf-8'));
      console.log('✅ 黄金会话已加载\n');
    } catch (e) {
      console.log('⚠️  未找到黄金会话\n');
    }

    // 启动浏览器
    console.log('🚀 启动浏览器...');
    browser = await chromium.launch({
      headless: false,
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1920,1080']
    });

    context = await browser.newContext({
      viewport: { width: 1920, height: 1080 },
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
      storageState: storageState
    });

    const page = await context.newPage();

    // 逐场审计
    for (let i = 0; i < TARGETS.length; i++) {
      const target = TARGETS[i];
      
      console.log('\n' + '═'.repeat(80));
      console.log(`[${i + 1}/${TARGETS.length}] 🔍 ${target.match_name}`);
      console.log(`     Hash: ${target.hash}`);
      console.log('═'.repeat(80));

      // 初始化状态
      const snifferState = {
        totalHits: 0,
        goldenHits: 0,
        channels: { ws: 0, fetch: 0, xhr: 0 },
        goldenStreams: [],
        capturedOdds: [],
        allData: []
      };

      // 注入Sniffer（第一场注册exposeFunction）
      await injectOmniSniffer(page, snifferState, i === 0);
      console.log('🕸️  Omni Sniffer 已注入\n');

      // 访问页面
      console.log('🌐 加载页面...');
      try {
        await page.goto(target.url, { waitUntil: 'networkidle', timeout: 60000 });
      } catch (e) {
        console.log('⚠️  页面加载超时，继续...');
      }

      // 执行交互
      console.log('🖱️  执行拟人化交互...\n');
      await page.mouse.move(800, 600);
      await page.waitForTimeout(1000);
      await page.mouse.wheel(0, 500);
      await page.waitForTimeout(2000);

      // 等待30秒捕获数据
      console.log('⏱️  等待数据流捕获 (30秒)...\n');
      await page.waitForTimeout(30000);

      // 本场统计
      console.log('\n📊 本场统计:');
      console.log(`   总命中: ${snifferState.totalHits}`);
      console.log(`   Golden Streams: ${snifferState.goldenHits}`);
      console.log(`   WebSocket: ${snifferState.channels.ws} 次`);
      console.log(`   Fetch: ${snifferState.channels.fetch} 次`);
      console.log(`   XHR: ${snifferState.channels.xhr} 次`);
      console.log(`   捕获赔率: ${snifferState.capturedOdds.length} 组`);

      // 保存到全局统计
      auditStats.matches.push({
        match_name: target.match_name,
        totalHits: snifferState.totalHits,
        goldenHits: snifferState.goldenHits,
        channels: { ...snifferState.channels },
        capturedOdds: snifferState.capturedOdds.length
      });
      auditStats.totalHits += snifferState.totalHits;
      auditStats.goldenHits += snifferState.goldenHits;
      auditStats.channelSummary.ws += snifferState.channels.ws;
      auditStats.channelSummary.fetch += snifferState.channels.fetch;
      auditStats.channelSummary.xhr += snifferState.channels.xhr;

      // 间隔
      if (i < TARGETS.length - 1) {
        console.log('\n⏱️  等待5秒后下一场...');
        await page.waitForTimeout(5000);
      }
    }

    // 识别数据大动脉
    const maxChannel = Object.entries(auditStats.channelSummary)
      .sort((a, b) => b[1] - a[1])[0];
    auditStats.dataArtery = maxChannel[0];

  } catch (error) {
    console.error('\n💥 错误:', error);
  } finally {
    if (context) await context.close();
    if (browser) await browser.close();
    await pool.end();
  }

  // 生成审计看板
  console.log('\n\n' + '╔' + '═'.repeat(78) + '╗');
  console.log('║' + ' '.repeat(20) + '📊 全维度审计看板' + ' '.repeat(39) + '║');
  console.log('╠' + '═'.repeat(78) + '╣');
  
  console.log('║  比赛详情:' + ' '.repeat(67) + '║');
  console.log('║' + '─'.repeat(78) + '║');
  
  auditStats.matches.forEach(m => {
    const name = m.match_name.substring(0, 25).padEnd(27);
    const hits = String(m.totalHits).padStart(3);
    const golden = String(m.goldenHits).padStart(2);
    const line = `║  ${name} | 命中:${hits} | Golden:${golden} | WS:${m.channels.ws} F:${m.channels.fetch} X:${m.channels.xhr}`;
    console.log(line.padEnd(79) + '║');
  });
  
  console.log('║' + '─'.repeat(78) + '║');
  console.log('║  频道贡献比例:' + ' '.repeat(63) + '║');
  console.log('║' + '─'.repeat(78) + '║');
  
  const total = auditStats.channelSummary.ws + auditStats.channelSummary.fetch + auditStats.channelSummary.xhr;
  if (total > 0) {
    const wsPct = ((auditStats.channelSummary.ws / total) * 100).toFixed(1);
    const fetchPct = ((auditStats.channelSummary.fetch / total) * 100).toFixed(1);
    const xhrPct = ((auditStats.channelSummary.xhr / total) * 100).toFixed(1);
    
    console.log(`║    WebSocket: ${String(auditStats.channelSummary.ws).padStart(4)} 次 (${wsPct.padStart(5)}%)` + ' '.repeat(48) + '║');
    console.log(`║    Fetch:     ${String(auditStats.channelSummary.fetch).padStart(4)} 次 (${fetchPct.padStart(5)}%)` + ' '.repeat(48) + '║');
    console.log(`║    XHR:       ${String(auditStats.channelSummary.xhr).padStart(4)} 次 (${xhrPct.padStart(5)}%)` + ' '.repeat(48) + '║');
  }
  
  console.log('║' + '─'.repeat(78) + '║');
  console.log('║' + `  🏆 数据大动脉: ${auditStats.dataArtery?.toUpperCase()} 频道`.padEnd(78) + '║');
  console.log('║' + `  📈 总命中: ${auditStats.totalHits} | Golden Streams: ${auditStats.goldenHits}`.padEnd(78) + '║');
  console.log('╚' + '═'.repeat(78) + '╝\n');

  // 最终判决
  console.log('╔══════════════════════════════════════════════════════════════════════════════╗');
  console.log('║     🏛️  最终判决                                                              ║');
  console.log('╠══════════════════════════════════════════════════════════════════════════════╣');
  if (auditStats.dataArtery) {
    console.log(`║  OddsPortal 的"数据大动脉"是: ${auditStats.dataArtery.toUpperCase()} 频道`.padEnd(78) + '║');
    console.log('║'.padEnd(79) + '║');
    if (auditStats.dataArtery === 'ws') {
      console.log('║  WebSocket 负责实时推送赔率变动，是主要的时序数据源'.padEnd(78) + '║');
    } else if (auditStats.dataArtery === 'fetch') {
      console.log('║  Fetch API 负责初始赔率加载，是主要的配置数据源'.padEnd(78) + '║');
    } else {
      console.log('║  XHR 负责传统的AJAX数据请求，兼容旧版数据接口'.padEnd(78) + '║');
    }
  } else {
    console.log('║  未能识别数据大动脉 - 所有频道均未捕获到有效数据'.padEnd(78) + '║');
    console.log('║  建议: 检查网络连接、页面加载状态、或数据加密方式'.padEnd(78) + '║');
  }
  console.log('╚══════════════════════════════════════════════════════════════════════════════╝\n');
}

// 执行审计
runOmniLiveAudit().catch(console.error);
