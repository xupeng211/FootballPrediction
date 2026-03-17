/**
 * TITAN V6.0 RAW API DUMPER - 原始API报文全量倾倒
 * ==================================================
 * 实战拦截：将OddsPortal后台异步报文进行物理备份
 * 
 * @module scripts/ops/raw_api_dumper
 * @version V6.0-RAW-DUMP
 * @date 2026-03-16
 */

'use strict';

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// 确保倾倒目录存在 (使用/tmp避免权限问题)
const DUMP_DIR = '/tmp/titan_raw_dumps';
if (!fs.existsSync(DUMP_DIR)) {
  fs.mkdirSync(DUMP_DIR, { recursive: true });
}

// 目标URL配置（已验证的真实URL）
const TARGETS = [
  {
    match_id: '47_20232024_4813679',
    match_name: 'Fulham vs Burnley',
    url: 'https://www.oddsportal.com/football/england/premier-league/fulham-burnley-8EamNN8b/'
  },
  {
    match_id: '54_20232024_4829555',
    match_name: 'RB Leipzig vs Hoffenheim',
    url: 'https://www.oddsportal.com/football/germany/bundesliga/rb-leipzig-hoffenheim-SrS8qyAO/'
  }
];

// 拦截关键词
const INTERCEPT_PATTERNS = [
  /ajax/i,
  /feed/i,
  /match-event/i,
  /odds/i,
  /1-1/i,
  /api/i,
  /data/i,
  /load/i
];

/**
 * 检查URL是否应该被拦截
 */
function shouldIntercept(url) {
  if (!url.includes('oddsportal.com')) return false;
  
  return INTERCEPT_PATTERNS.some(pattern => pattern.test(url));
}

/**
 * 保存原始报文到文件
 */
function saveRawDump(matchId, url, method, headers, body) {
  const timestamp = Date.now();
  const filename = `dump_${matchId}_${timestamp}.txt`;
  const filepath = path.join(DUMP_DIR, filename);
  
  const dumpContent = [
    '═══════════════════════════════════════════════════════════════════════════════',
    'TITAN V6.0 RAW API DUMP - 原始API报文备份',
    '═══════════════════════════════════════════════════════════════════════════════',
    `Match ID: ${matchId}`,
    `Timestamp: ${new Date().toISOString()}`,
    `Unix Time: ${timestamp}`,
    '',
    '═══════════════════════════════════════════════════════════════════════════════',
    'REQUEST',
    '═══════════════════════════════════════════════════════════════════════════════',
    `URL: ${url}`,
    `Method: ${method}`,
    '',
    'Headers:',
    JSON.stringify(headers, null, 2),
    '',
    '═══════════════════════════════════════════════════════════════════════════════',
    'RESPONSE BODY (RAW)',
    '═══════════════════════════════════════════════════════════════════════════════',
    body,
    '',
    '═══════════════════════════════════════════════════════════════════════════════',
    'END OF DUMP',
    '═══════════════════════════════════════════════════════════════════════════════'
  ].join('\n');
  
  fs.writeFileSync(filepath, dumpContent, 'utf-8');
  
  return filepath;
}

/**
 * 主倾倒函数
 */
async function rawApiDumper() {
  console.log('\n╔══════════════════════════════════════════════════════════════════════════════╗');
  console.log('║     📦 TITAN V6.0 RAW API DUMPER - 原始报文全量倾倒 📦                       ║');
  console.log('║     实战拦截：物理备份所有后台异步报文                                       ║');
  console.log('╚══════════════════════════════════════════════════════════════════════════════╝\n');
  
  console.log(`📁 倾倒目录: ${DUMP_DIR}\n`);
  
  // 加载黄金会话
  const sessionPath = path.join(process.cwd(), 'data/sessions/auth_gold.json');
  let sessionData = null;
  try {
    sessionData = JSON.parse(fs.readFileSync(sessionPath, 'utf-8'));
    console.log('✅ 已加载黄金会话\n');
  } catch (e) {
    console.log('⚠️  未找到黄金会话，继续执行\n');
  }
  
  // 启动浏览器
  console.log('🚀 启动浏览器...');
  const browser = await chromium.launch({
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
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
  };
  if (sessionData) contextConfig.storageState = sessionData;
  
  const context = await browser.newContext(contextConfig);
  const page = await context.newPage();
  
  // 注入stealth
  await context.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
  });
  
  // 拦截到的报文统计
  const interceptedDumps = [];
  
  // 设置请求拦截
  await page.route('**/*', async (route, request) => {
    const url = request.url();
    const method = request.method();
    
    if (shouldIntercept(url)) {
      console.log(`\n📡 拦截到请求: ${method} ${url.substring(0, 80)}...`);
      
      try {
        // 继续请求并获取响应
        const response = await route.fetch();
        const headers = response.headers();
        
        // 获取原始响应文本（不解析JSON）
        const rawBody = await response.text();
        
        console.log(`   📊 响应大小: ${rawBody.length} 字节`);
        
        // 保存到文件
        const currentTarget = TARGETS.find(t => url.includes(t.match_id.split('_')[2])) || TARGETS[0];
        const filepath = saveRawDump(currentTarget.match_id, url, method, headers, rawBody);
        
        console.log(`   💾 已保存: ${filepath}`);
        
        interceptedDumps.push({
          url: url,
          method: method,
          size: rawBody.length,
          filepath: filepath,
          timestamp: Date.now()
        });
        
      } catch (error) {
        console.log(`   ❌ 拦截失败: ${error.message}`);
      }
    }
    
    await route.continue();
  });
  
  // 处理每个目标
  for (const target of TARGETS) {
    console.log('\n' + '='.repeat(80));
    console.log(`🎯 目标: ${target.match_name}`);
    console.log(`   Match ID: ${target.match_id}`);
    console.log(`   URL: ${target.url}`);
    console.log('='.repeat(80));
    
    try {
      // 导航到页面
      console.log('\n🌐 正在加载页面...');
      await page.goto(target.url, { 
        waitUntil: 'networkidle', 
        timeout: 60000 
      });
      console.log('   ✅ 页面加载完成');
      
      // 静默等待15秒，捕获延迟加载数据
      console.log('\n⏱️  静默等待15秒，捕获延迟加载数据...');
      for (let i = 15; i > 0; i--) {
        process.stdout.write(`   剩余 ${i} 秒... \r`);
        await page.waitForTimeout(1000);
      }
      console.log('\n   ✅ 等待完成');
      
      // 尝试滚动触发更多请求
      console.log('\n🖱️  执行页面滚动触发更多请求...');
      await page.evaluate(() => {
        window.scrollTo(0, document.body.scrollHeight / 2);
      });
      await page.waitForTimeout(3000);
      
      await page.evaluate(() => {
        window.scrollTo(0, document.body.scrollHeight);
      });
      await page.waitForTimeout(3000);
      
      console.log('   ✅ 滚动完成');
      
    } catch (error) {
      console.log(`   ❌ 错误: ${error.message}`);
    }
  }
  
  // 关闭浏览器
  await context.close();
  await browser.close();
  
  // 生成报告
  console.log('\n' + '═'.repeat(80));
  console.log('📊 倾倒战报');
  console.log('═'.repeat(80));
  
  console.log(`\n📦 总拦截报文数: ${interceptedDumps.length}`);
  
  if (interceptedDumps.length > 0) {
    const totalSize = interceptedDumps.reduce((sum, d) => sum + d.size, 0);
    console.log(`📊 总数据量: ${(totalSize / 1024).toFixed(2)} KB`);
    
    console.log('\n📁 倾倒文件列表:');
    console.log('─'.repeat(80));
    interceptedDumps.forEach((dump, idx) => {
      const filename = path.basename(dump.filepath);
      console.log(`   ${idx + 1}. ${filename} (${(dump.size / 1024).toFixed(2)} KB)`);
    });
    console.log('─'.repeat(80));
    
    // 显示一个典型文件路径
    const sampleFile = interceptedDumps[0].filepath;
    console.log(`\n🚀 原始报文已倾倒至: ${sampleFile}`);
    console.log('   请指挥官打开该文件，搜索页面上看到的 Bet365 赔率数字（如 1.50）');
    console.log('   确定其所属的 Key 名称。');
    
    // 显示混淆报文片段
    if (interceptedDumps.length > 0) {
      const firstDump = interceptedDumps[0];
      const content = fs.readFileSync(firstDump.filepath, 'utf-8');
      const bodyMatch = content.match(/RESPONSE BODY \(RAW\)[\s\S]*?═══════════════════([\s\S]*?)═══════════════════/);
      
      if (bodyMatch) {
        const body = bodyMatch[1].trim();
        console.log('\n📄 典型混淆报文片段 (前500字符):');
        console.log('─'.repeat(80));
        console.log(body.substring(0, 500));
        console.log('─'.repeat(80));
        
        // 检查是否有非标准结构
        const hasObfuscatedKeys = /[\"']\w{1,2}[\"']:/.test(body);
        const hasNestedArrays = /\[\s*\[/.test(body);
        const hasTimestampSeparation = /\d{10,13}/.test(body);
        
        console.log('\n🔍 结构分析:');
        console.log(`   • 混淆Key (如 a,b,c,t): ${hasObfuscatedKeys ? '✅ 发现' : '❌ 未发现'}`);
        console.log(`   • 嵌套数组结构: ${hasNestedArrays ? '✅ 发现' : '❌ 未发现'}`);
        console.log(`   • 时间戳分离: ${hasTimestampSeparation ? '✅ 发现' : '❌ 未发现'}`);
      }
    }
  } else {
    console.log('\n⚠️  未拦截到任何API请求');
    console.log('   可能原因:');
    console.log('   1. 页面未完全加载');
    console.log('   2. 网络连接超时');
    console.log('   3. 拦截模式不匹配');
  }
  
  console.log('\n╔══════════════════════════════════════════════════════════════════════════════╗');
  console.log('║     ✅ RAW API DUMP 完成                                                     ║');
  console.log('╚══════════════════════════════════════════════════════════════════════════════╝\n');
  
  return interceptedDumps;
}

// 运行
if (require.main === module) {
  rawApiDumper().then((dumps) => {
    console.log(`\n✅ 倾倒完成，共 ${dumps.length} 个报文`);
    process.exit(0);
  }).catch(err => {
    console.error('\n💥 FAILED:', err);
    process.exit(1);
  });
}

module.exports = { rawApiDumper };
