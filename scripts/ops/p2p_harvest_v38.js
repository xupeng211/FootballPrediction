#!/usr/bin/env node
/**
 * V38.4 Node.js Playwright点对点真实收割 (Point-to-Point Harvesting)
 * =====================================================================
 * 2023/24赛季真实历史数据回填 - 带Cookie认证突破
 * 
 * 核心功能:
 * - 自动加载 data/sessions/auth_gold.json Cookie
 * - API拦截 + DOM提取双策略
 * - 真实OddsPortal赔率抓取
 * 
 * @version V38.4-P2P-AUTH
 * @date 2026-03-17
 */

const { chromium } = require('playwright');
const fs = require('fs').promises;
const path = require('path');

// ============================================================================
// Cookie 加载模块（整合自 capture_auth_oddsportal.js）
// ============================================================================

/**
 * 从文件加载 storageState 格式的 Cookie
 */
async function loadStorageState(sessionPath) {
  try {
    const data = await fs.readFile(sessionPath, 'utf-8');
    const storageState = JSON.parse(data);
    console.log(`✅ 已加载认证会话: ${sessionPath}`);
    console.log(`   Cookie数量: ${storageState.cookies?.length || 0}`);
    
    // 显示关键Cookie
    const keyCookies = storageState.cookies?.filter(c => 
      ['session', 'auth', 'token', 'turnstile', 'cf_clearance', 'user'].some(k => 
        c.name.toLowerCase().includes(k)
      )
    );
    if (keyCookies?.length > 0) {
      console.log(`   关键Cookie: ${keyCookies.map(c => c.name).join(', ')}`);
    }
    
    return storageState;
  } catch (e) {
    console.log(`⚠️  无法加载会话: ${e.message}`);
    return null;
  }
}

/**
 * 手动解析 Cookie 字符串
 */
function parseManualCookies(cookieStr, domain = '.oddsportal.com') {
  const cookies = [];
  const pairs = cookieStr.split(/;\s*/);
  
  for (const pair of pairs) {
    const eqIndex = pair.indexOf('=');
    if (eqIndex === -1) continue;
    
    const name = pair.substring(0, eqIndex).trim();
    const value = pair.substring(eqIndex + 1).trim();
    
    if (name) {
      cookies.push({
        name, value, domain, path: '/',
        expires: Math.floor(Date.now() / 1000) + 86400 * 7,
        httpOnly: false, secure: true, sameSite: 'Lax'
      });
    }
  }
  
  return { cookies, origins: [{ origin: `https://www${domain}`, localStorage: [] }] };
}

// ============================================================================
// 3场真实的2023/24赛季英超比赛
// ============================================================================

const REAL_2023_24_MATCHES = [
  {
    id: '47_20232024_4813679',
    home_team: 'Fulham',
    away_team: 'Burnley',
    match_date: '2024-05-11',
    url: 'https://www.oddsportal.com/football/england/premier-league/fulham-burnley-8EamNN8b/',
    hash: '8EamNN8b'
  },
  {
    id: '47_20232024_4813666',
    home_team: 'Brentford',
    away_team: 'Wolves',
    match_date: '2024-05-11',
    url: 'https://www.oddsportal.com/football/england/premier-league/brentford-wolves-0jR7cwU6/',
    hash: '0jR7cwU6'
  },
  {
    id: '47_20232024_4813675',
    home_team: 'Bournemouth',
    away_team: 'Manchester United',
    match_date: '2024-05-19',
    url: 'https://www.oddsportal.com/football/england/premier-league/bournemouth-manchester-united-QZ5U62OH/',
    hash: 'QZ5U62OH'
  }
];

// ============================================================================
// P2P 收割器（带Cookie认证）
// ============================================================================

class P2PHarvester {
  constructor(options = {}) {
    this.sessionPath = options.sessionPath || 'data/sessions/auth_gold.json';
    this.proxyServer = options.proxyServer || 'http://172.25.16.1:7890';
    this.headless = options.headless !== false;
    this.results = [];
  }

  async init() {
    console.log('🔧 初始化P2P收割机...');
    
    // 1. 加载认证会话
    let storageState = await loadStorageState(this.sessionPath);
    
    if (!storageState && process.env.MANUAL_COOKIES) {
      console.log('🔧 使用环境变量手动Cookie');
      storageState = parseManualCookies(process.env.MANUAL_COOKIES);
    }

    if (!storageState) {
      console.log('⚠️  警告: 未找到认证会话，将以游客模式访问');
      console.log('   提示: 请先运行 node scripts/capture_auth_oddsportal.js 完成登录');
    }

    // 2. 启动浏览器
    console.log('🚀 启动Playwright浏览器...');
    this.browser = await chromium.launch({
      headless: this.headless,
      proxy: { server: this.proxyServer },
      args: [
        '--no-sandbox', 
        '--disable-setuid-sandbox',
        '--window-size=1920,1080'
      ]
    });

    // 3. 创建上下文（关键：注入storageState）
    const contextOptions = {
      viewport: { width: 1920, height: 1080 },
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    };
    
    if (storageState) {
      contextOptions.storageState = storageState;
      console.log('💉 Cookie已注入浏览器上下文');
    }

    this.context = await this.browser.newContext(contextOptions);
    
    // 4. 额外动态Cookie注入
    if (storageState?.cookies) {
      await this.context.addCookies(storageState.cookies);
      console.log(`✅ 动态注入 ${storageState.cookies.length} 个Cookie`);
    }

    this.page = await this.context.newPage();
    
    // 5. 反检测脚本
    await this.context.addInitScript(() => {
      delete navigator.webdriver;
      Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    });

    // 6. 设置API拦截
    await this.setupAPIInterception();
    
    console.log('✅ 浏览器初始化完成\n');
  }

  async setupAPIInterception() {
    this.interceptedData = [];
    
    await this.page.route('**/*', async (route, request) => {
      const url = request.url();
      
      // 拦截API请求
      if (/odds|api|ajax|feed|match-event/.test(url)) {
        try {
          const response = await route.fetch();
          const body = await response.text();
          
          // 尝试解析JSON
          try {
            const json = JSON.parse(body);
            if (json.odds || json.data?.odds || json.markets) {
              console.log(`   📡 API拦截: ${url.substring(0, 60)}...`);
              this.interceptedData.push({ url, data: json });
            }
          } catch (e) {}
        } catch (e) {}
      }
      
      route.continue();
    });
  }

  async harvestMatch(match) {
    console.log(`\n🔍 [${match.id}] ${match.home_team} vs ${match.away_team}`);
    console.log(`   📅 ${match.match_date}`);
    console.log(`   🔗 ${match.url}`);
    
    const result = {
      match_id: match.id,
      home_team: match.home_team,
      away_team: match.away_team,
      url: match.url,
      status: 'pending',
      odds: null,
      error: null,
      html_length: 0,
      api_data_count: 0
    };

    try {
      // 导航到比赛页面
      console.log('   🌐 导航到页面...');
      const response = await this.page.goto(match.url, {
        waitUntil: 'domcontentloaded',
        timeout: 60000
      });

      if (response.status() === 404) {
        result.status = 'error';
        result.error = 'HTTP 404';
        console.log('   ❌ 页面404');
        return result;
      }

      // 等待页面渲染
      console.log('   ⏳ 等待赔率加载...');
      await this.page.waitForTimeout(5000);

      // 获取页面信息
      const title = await this.page.title();
      const html = await this.page.content();
      result.html_length = html.length;
      
      console.log(`   📄 页面标题: ${title}`);
      console.log(`   📄 HTML大小: ${html.length.toLocaleString()} bytes`);

      // 检查是否有赔率数据
      const hasOddsPortal = html.includes('oddsportal') || html.includes('OddsPortal');
      const hasBookmakers = html.toLowerCase().includes('bet365') || html.toLowerCase().includes('pinnacle');
      
      console.log(`   🔍 检测到OddsPortal: ${hasOddsPortal ? '✅' : '❌'}`);
      console.log(`   🔍 检测到博彩公司: ${hasBookmakers ? '✅' : '❌'}`);

      // 尝试提取赔率（简化的DOM提取）
      const oddsData = await this.extractOddsFromDOM();
      if (oddsData) {
        result.odds = oddsData;
        console.log(`   💰 提取到赔率: ${JSON.stringify(oddsData)}`);
      }

      result.api_data_count = this.interceptedData.length;
      result.status = 'success';
      
      // 保存HTML用于调试
      const debugFile = `debug_${match.id}.html`;
      await fs.writeFile(debugFile, html);
      console.log(`   🐛 HTML已保存: ${debugFile}`);

    } catch (error) {
      result.status = 'error';
      result.error = error.message;
      console.log(`   ❌ 错误: ${error.message}`);
    }

    this.results.push(result);
    return result;
  }

  async extractOddsFromDOM() {
    try {
      // 使用页面evaluate提取赔率
      const odds = await this.page.evaluate(() => {
        const results = {};
        
        // 尝试多种选择器查找赔率
        const selectors = [
          '[data-testid="odds"]',
          '.odds',
          '.price',
          'div[class*="odd"]',
          'table tbody tr'
        ];
        
        for (const selector of selectors) {
          const elements = document.querySelectorAll(selector);
          if (elements.length > 0) {
            results.foundElements = elements.length;
            results.selector = selector;
            
            // 提取文本内容
            elements.forEach((el, i) => {
              const text = el.textContent || '';
              if (text.includes('1.') || text.includes('2.') || text.includes('3.')) {
                results.sampleText = text.substring(0, 100);
              }
            });
            
            break;
          }
        }
        
        // 查找Bet365/Pinnacle文本
        const bodyText = document.body.innerText || '';
        results.hasBet365 = bodyText.toLowerCase().includes('bet365');
        results.hasPinnacle = bodyText.toLowerCase().includes('pinnacle');
        results.bodyLength = bodyText.length;
        
        return results;
      });
      
      return odds;
    } catch (e) {
      return null;
    }
  }

  async generateReport() {
    console.log('\n' + '='.repeat(70));
    console.log('📊 P2P收割报告');
    console.log('='.repeat(70));
    
    const success = this.results.filter(r => r.status === 'success');
    const errors = this.results.filter(r => r.status === 'error');
    
    console.log(`总场次: ${this.results.length}`);
    console.log(`成功: ${success.length}`);
    console.log(`失败: ${errors.length}`);
    
    console.log('\n详细结果:');
    for (const r of this.results) {
      const oddsInfo = r.odds ? ` odds=${JSON.stringify(r.odds).substring(0, 50)}` : '';
      console.log(`  ${r.match_id}: ${r.status} | HTML=${r.html_length}${oddsInfo}`);
    }
    
    // 保存结果到JSON
    const resultFile = `p2p_harvest_auth_${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
    await fs.writeFile(resultFile, JSON.stringify(this.results, null, 2));
    console.log(`\n💾 结果已保存: ${resultFile}`);
  }

  async close() {
    if (this.browser) await this.browser.close();
  }
}

// ============================================================================
// 主程序
// ============================================================================

async function main() {
  console.log('='.repeat(70));
  console.log('🚀 V38.4 Playwright点对点真实收割 (带Cookie认证)');
  console.log('='.repeat(70));
  console.log('⚠️  模式: Cookie认证突破 / 真实OddsPortal抓取');
  console.log('🎯 目标: 3场 2023/24 赛季真实英超比赛');
  console.log();

  // 检查会话文件
  const sessionPath = 'data/sessions/auth_gold.json';
  try {
    await fs.access(sessionPath);
    console.log('✅ 发现认证会话文件');
  } catch {
    console.log('⚠️  未找到认证会话，将尝试游客模式');
    console.log('   提示: 运行 node scripts/capture_auth_oddsportal.js 生成会话\n');
  }

  console.log('📋 待收割比赛列表:');
  REAL_2023_24_MATCHES.forEach((m, i) => {
    console.log(`   ${i + 1}. ${m.home_team} vs ${m.away_team} (${m.match_date})`);
  });
  console.log();

  // 初始化收割机
  const harvester = new P2PHarvester({
    sessionPath: 'data/sessions/auth_gold.json',
    proxyServer: 'http://172.25.16.1:7890',
    headless: true  // 可以设为false观察
  });

  await harvester.init();

  // 收割比赛
  for (let i = 0; i < REAL_2023_24_MATCHES.length; i++) {
    const match = REAL_2023_24_MATCHES[i];
    console.log(`\n[${i + 1}/${REAL_2023_24_MATCHES.length}] 开始收割...`);
    
    await harvester.harvestMatch(match);
    
    // 间隔
    if (i < REAL_2023_24_MATCHES.length - 1) {
      console.log('   ⏳ 等待5秒...');
      await new Promise(r => setTimeout(r, 5000));
    }
  }

  // 生成报告
  await harvester.generateReport();
  
  await harvester.close();
  
  console.log('\n✅ 收割完成');
}

main().catch(err => {
  console.error('💥 致命错误:', err);
  process.exit(1);
});
