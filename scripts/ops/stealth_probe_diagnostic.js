/**
 * TITAN V6.0 STEALTH PROBE - 隐身探测与拦截点校准
 * ===========================================================
 * 深度探测协议 - 查明嗅探器0命中的真实原因
 * 
 * @module ops/stealth_probe_diagnostic
 * @version V6.0-STEALTH-PROBE
 * @date 2026-03-16
 */

'use strict';

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// 配置
const CONFIG = {
  headless: true,  // Docker环境使用headless
  timeout: 60000,
  screenshotOnFailure: true,
  dumpHtml: true,
  trafficAudit: true,
  earlyInjection: true,
  simulateInteraction: true
};

// 早期注入的 Sniffer 代码
const EARLY_SNIFFER_CODE = `
(() => {
  console.log('--- TITAN SNIFFER ARMED ---');
  
  window.__TITAN_SNIFFER_STATE = {
    armed: true,
    timestamp: Date.now(),
    captured: []
  };
  
  // 拦截 Fetch
  const originalFetch = window.fetch;
  window.fetch = async function(...args) {
    const url = args[0];
    console.log('[SNIFFER] Fetch intercepted:', url);
    window.__TITAN_SNIFFER_STATE.captured.push({ type: 'fetch', url, time: Date.now() });
    return originalFetch.apply(this, args);
  };
  
  // 拦截 XHR
  const originalXHR = window.XMLHttpRequest;
  window.XMLHttpRequest = function() {
    const xhr = new originalXHR();
    const originalOpen = xhr.open;
    xhr.open = function(method, url) {
      console.log('[SNIFFER] XHR intercepted:', url);
      window.__TITAN_SNIFFER_STATE.captured.push({ type: 'xhr', url, time: Date.now() });
      return originalOpen.apply(this, arguments);
    };
    return xhr;
  };
  
  console.log('--- TITAN SNIFFER ARMED COMPLETE ---');
})();
`;

async function ensureDir(dir) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

async function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

async function runProbe() {
  console.log('╔══════════════════════════════════════════════════════════════════════════════╗');
  console.log('║     🕵️  TITAN V6.0 STEALTH PROBE - 隐身探测协议                              ║');
  console.log('╚══════════════════════════════════════════════════════════════════════════════╝\n');

  await ensureDir('data/audit');
  
  let browser;
  let page;
  
  try {
    console.log('[INIT] 启动浏览器...');
    browser = await chromium.launch({
      headless: CONFIG.headless,
      args: [
        '--disable-blink-features=AutomationControlled',
        '--disable-web-security',
        '--disable-features=IsolateOrigins,site-per-process'
      ]
    });
    
    const context = await browser.newContext({
      viewport: { width: 1920, height: 1080 },
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    });
    
    page = await context.newPage();
    
    // ========== 1. 早期注入时序抢跑 ==========
    if (CONFIG.earlyInjection) {
      console.log('[INJECTION] 🏃 执行早期注入...');
      await page.addInitScript(EARLY_SNIFFER_CODE);
      console.log('[INJECTION] ✅ 早期注入完成');
    }
    
    // ========== 2. 全量流量审计 ==========
    const trafficLog = [];
    
    if (CONFIG.trafficAudit) {
      console.log('[AUDIT] 📊 开启全量流量审计...');
      
      page.on('request', request => {
        const url = request.url();
        if (url.includes('ajax') || url.includes('feed') || url.includes('.dat') || url.includes('oddsportal')) {
          console.log(`[REQUEST]  ${url.substring(0, 100)}...`);
          trafficLog.push({ type: 'request', url, time: Date.now() });
        }
      });
      
      page.on('response', response => {
        const url = response.url();
        if (url.includes('ajax') || url.includes('feed') || url.includes('.dat') || url.includes('oddsportal')) {
          console.log(`[RESPONSE] ${response.status()} | ${url.substring(0, 100)}...`);
          trafficLog.push({ type: 'response', url, status: response.status(), time: Date.now() });
        }
      });
      
      // 监听控制台
      page.on('console', msg => {
        const text = msg.text();
        if (text.includes('TITAN SNIFFER') || text.includes('SNIFFER')) {
          console.log(`[CONSOLE] 🔊 ${text}`);
        }
      });
    }
    
    // ========== 3. 访问目标页面 ==========
    const targetUrl = 'https://www.oddsportal.com/football/england/premier-league/fulham-burnley-8EamNN8b/';
    console.log(`[NAVIGATE] 🌐 访问: ${targetUrl}`);
    
    const response = await page.goto(targetUrl, { 
      waitUntil: 'networkidle',
      timeout: 60000 
    });
    
    console.log(`[NAVIGATE] 页面状态: ${response.status()}`);
    
    // 检查页面内容
    const title = await page.title();
    console.log(`[NAVIGATE] 页面标题: ${title}`);
    
    // 检查是否有反爬特征
    const content = await page.content();
    const checks = {
      cloudflare: content.includes('cf-browser-verification') || content.includes('Checking your browser'),
      blocked: content.includes('403') || content.includes('Forbidden'),
      captcha: content.includes('captcha') || content.includes('CAPTCHA'),
      botDetected: content.includes('bot') || content.includes('automated')
    };
    
    console.log('[SECURITY] 🔒 反爬检测:');
    Object.entries(checks).forEach(([key, val]) => {
      console.log(`  - ${key}: ${val ? '⚠️ DETECTED' : '✅ Clean'}`);
    });
    
    // ========== 4. 动态触发协议 ==========
    if (CONFIG.simulateInteraction && !checks.cloudflare && !checks.blocked) {
      console.log('[INTERACTION] 🖱️  执行模拟交互...');
      
      // 等待页面加载
      await sleep(3000);
      
      // 查找Bet365相关元素
      const bet365Elements = await page.locator('text=Bet365').all();
      console.log(`[INTERACTION] 发现 ${bet365Elements.length} 个Bet365元素`);
      
      if (bet365Elements.length > 0) {
        // 尝试悬停和点击
        try {
          const target = bet365Elements[0];
          console.log('[INTERACTION] 悬停于Bet365元素...');
          await target.hover();
          await sleep(1000);
          
          console.log('[INTERACTION] 轻微点击Bet365元素...');
          await target.click({ force: true });
          await sleep(2000);
          
          console.log('[INTERACTION] ✅ 交互完成');
        } catch (e) {
          console.log(`[INTERACTION] ⚠️  交互失败: ${e.message}`);
        }
      }
      
      // 查找赔率数字并交互
      const oddsElements = await page.locator('text=/\\d\\.\\d{2}/').all();
      console.log(`[INTERACTION] 发现 ${oddsElements.length} 个赔率元素`);
      
      if (oddsElements.length > 0) {
        try {
          console.log('[INTERACTION] 悬停于赔率元素...');
          await oddsElements[0].hover();
          await sleep(1000);
        } catch (e) {
          console.log(`[INTERACTION] ⚠️  赔率交互失败: ${e.message}`);
        }
      }
    }
    
    // 检查 Sniffer 状态
    console.log('[VERIFY] 🔍 检查Sniffer注入状态...');
    const snifferState = await page.evaluate(() => {
      return window.__TITAN_SNIFFER_STATE || null;
    });
    
    if (snifferState) {
      console.log(`[VERIFY] ✅ Sniffer已武装`);
      console.log(`[VERIFY]   - 捕获请求数: ${snifferState.captured.length}`);
      snifferState.captured.slice(0, 5).forEach((c, i) => {
        console.log(`[VERIFY]   [${i+1}] ${c.type}: ${c.url.substring(0, 60)}...`);
      });
    } else {
      console.log('[VERIFY] ❌ Sniffer未检测到');
    }
    
    // 等待更多网络请求
    console.log('[WAIT] ⏳ 等待网络请求 (10秒)...');
    await sleep(10000);
    
    // ========== 5. 生成诊断报告 ==========
    console.log('\n[REPORT] 📊 生成诊断报告...\n');
    
    const report = {
      timestamp: new Date().toISOString(),
      targetUrl,
      pageStatus: response.status(),
      pageTitle: title,
      securityChecks: checks,
      snifferState: snifferState ? {
        armed: snifferState.armed,
        capturedCount: snifferState.captured.length,
        sampleCaptures: snifferState.captured.slice(0, 10)
      } : null,
      trafficLog: trafficLog.slice(0, 20),
      conclusion: {
        blocked: checks.cloudflare || checks.blocked,
        snifferWorking: snifferState !== null,
        dataCaptured: snifferState && snifferState.captured.length > 0
      }
    };
    
    fs.writeFileSync('data/audit/stealth_probe_report.json', JSON.stringify(report, null, 2));
    console.log('[REPORT] ✅ 诊断报告已保存: data/audit/stealth_probe_report.json');
    
    // ========== 6. 失败现场勘察 ==========
    if (report.conclusion.blocked || !report.conclusion.dataCaptured) {
      console.log('[FORENSIC] 🔍 执行失败现场勘察...');
      
      if (CONFIG.screenshotOnFailure) {
        await page.screenshot({ 
          path: 'data/audit/failure_screenshot.png',
          fullPage: true 
        });
        console.log('[FORENSIC] ✅ 截图已保存: data/audit/failure_screenshot.png');
      }
      
      if (CONFIG.dumpHtml) {
        const html = await page.content();
        fs.writeFileSync('data/audit/failure_dump.html', html);
        console.log('[FORENSIC] ✅ HTML已保存: data/audit/failure_dump.html');
      }
    }
    
    // ========== 阻碍点判定 ==========
    console.log('\n╔══════════════════════════════════════════════════════════════════════════════╗');
    console.log('║                   ⚖️  阻碍点判定报告                                          ║');
    console.log('╚══════════════════════════════════════════════════════════════════════════════╝\n');
    
    if (checks.cloudflare) {
      console.log('🚫 【阻碍点】Cloudflare浏览器验证');
      console.log('   └─ 需要: 更强的反检测措施或代理');
    } else if (checks.blocked) {
      console.log('🚫 【阻碍点】IP被封禁 (403 Forbidden)');
      console.log('   └─ 需要: 更换代理IP');
    } else if (!snifferState) {
      console.log('🚫 【阻碍点】Sniffer注入失败');
      console.log('   └─ 可能原因: 页面刷新导致注入丢失');
    } else if (snifferState.captured.length === 0) {
      console.log('🚫 【阻碍点】未捕获到赔率数据请求');
      console.log('   └─ 可能原因:');
      console.log('      1. 赔率数据通过不同API端点返回');
      console.log('      2. 需要用户登录');
      console.log('      3. 赔率数据已预渲染在HTML中');
    } else {
      console.log('✅ 【状态】Sniffer工作正常，有数据捕获');
    }
    
    console.log('\n[TRAFFIC] 📊 流量审计摘要:');
    console.log(`   - 总请求数: ${trafficLog.filter(t => t.type === 'request').length}`);
    console.log(`   - 总响应数: ${trafficLog.filter(t => t.type === 'response').length}`);
    
    console.log('\n[PROBE] ✅ 隐身探测完成');
    
  } catch (error) {
    console.error('[ERROR] ❌ 探测失败:', error.message);
    
    // 紧急现场保存
    if (page) {
      try {
        await page.screenshot({ path: 'data/audit/error_screenshot.png' });
        const html = await page.content();
        fs.writeFileSync('data/audit/error_dump.html', html);
        console.log('[FORENSIC] ✅ 错误现场已保存');
      } catch (e) {
        console.error('[FORENSIC] ⚠️  现场保存失败:', e.message);
      }
    }
    
  } finally {
    if (browser) {
      await browser.close();
      console.log('[CLEANUP] 浏览器已关闭');
    }
  }
}

// 执行探测
runProbe().catch(console.error);
