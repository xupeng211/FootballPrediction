#!/usr/bin/env node
/**
 * @file OddsPortal 登录捕获脚本
 * @description 捕获 OddsPortal 登录态，用于历史数据抓取
 * @version 1.0.0
 */

const { chromium } = require('playwright');
const readline = require('readline');
const fs = require('fs').promises;
const path = require('path');

const LOG_PREFIX = '[AUTH-ODDSPORTAL]';

// 极简 Stealth
const MINIMAL_STEALTH_SCRIPT = `
(() => {
  delete navigator.webdriver;
})();
`;

const CIVILIAN_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';
const CIVILIAN_VIEWPORT = { width: 1920, height: 1080 };
const USER_DATA_DIR = path.join(__dirname, '..', 'data', 'browser_profile_oddsportal');

async function forceCleanProfile() {
  try {
    await fs.rm(USER_DATA_DIR, { recursive: true, force: true });
    console.log(`${LOG_PREFIX} ✓ 已清理旧配置文件`);
  } catch (err) {
    console.log(`${LOG_PREFIX} 无需清理（目录不存在）`);
  }
}

function createReadline() {
  return readline.createInterface({ input: process.stdin, output: process.stdout });
}

function ask(rl, question) {
  return new Promise(resolve => {
    rl.question(question, answer => resolve(answer.trim()));
  });
}

async function saveSession(storageState) {
  const dataDir = path.join(__dirname, '..', 'data', 'sessions');
  await fs.mkdir(dataDir, { recursive: true });

  // 保存为 auth_gold.json（标准名称）
  const sessionPath = path.join(dataDir, 'auth_gold.json');
  await fs.writeFile(sessionPath, JSON.stringify(storageState, null, 2));

  // 同时保存带时间戳的版本
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const backupPath = path.join(dataDir, `oddsportal_session_${timestamp}.json`);
  await fs.writeFile(backupPath, JSON.stringify(storageState, null, 2));

  // 提取 cookie 字符串
  const cookieStr = storageState.cookies
    ?.map(c => `${c.name}=${c.value}`)
    .join('; ') || '';

  const cookiePath = path.join(dataDir, `oddsportal_cookies_${timestamp}.txt`);
  await fs.writeFile(cookiePath, cookieStr);

  return { sessionPath, backupPath, cookiePath, cookieStr };
}

function showInstructions() {
  console.log('\n' + '='.repeat(60));
  console.log('🎯 OddsPortal 登录捕获引导');
  console.log('='.repeat(60));
  console.log('1. 浏览器将打开 OddsPortal 网站');
  console.log('2. 请像普通用户一样完成登录');
  console.log('3. 如果遇到 Cloudflare，请完成验证');
  console.log('4. 确保能看到历史比赛的赔率数据');
  console.log('5. 完成后回到这里按 Enter 保存会话');
  console.log('='.repeat(60) + '\n');
}

async function main() {
  console.log(`${LOG_PREFIX} 启动 OddsPortal 登录捕获脚本`);
  console.log(`${LOG_PREFIX} 模式: 可视化登录 | 窗口: 1920x1080`);

  await forceCleanProfile();

  let browser = null;
  const rl = createReadline();

  try {
    console.log(`${LOG_PREFIX} 启动浏览器...`);

    browser = await chromium.launchPersistentContext(USER_DATA_DIR, {
      headless: false,  // ★★★ 可视化模式 ★★★
      viewport: CIVILIAN_VIEWPORT,
      userAgent: CIVILIAN_USER_AGENT,
      locale: 'en-US',
      timezoneId: 'Europe/London',
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-blink-features=AutomationControlled',
        '--disable-dev-shm-usage',
        '--window-size=1920,1080',
        '--window-position=50,50'
      ]
    });

    console.log(`${LOG_PREFIX} ✓ 浏览器启动成功`);

    await browser.addInitScript(MINIMAL_STEALTH_SCRIPT);
    console.log(`${LOG_PREFIX} ✓ Stealth 已注入`);

    const page = await browser.newPage();
    console.log(`${LOG_PREFIX} ✓ 新页面已创建`);

    showInstructions();

    // 导航到 OddsPortal 历史比赛页面
    const targetUrl = 'https://www.oddsportal.com/football/england/premier-league/results/';
    console.log(`${LOG_PREFIX} 正在导航到: ${targetUrl}`);
    console.log(`${LOG_PREFIX} （这是英超历史结果页，登录后能看到完整赔率）`);

    try {
      await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
      console.log(`${LOG_PREFIX} ✓ 页面加载完成`);
      
      // 等待几秒让用户看到页面
      await new Promise((resolve) => {
        setTimeout(resolve, 3000);
      });

      // 尝试关闭可能的弹窗
      try {
        const closeBtn = await page.$('button[aria-label="Close"], .modal-close, .popup-close');
        if (closeBtn) await closeBtn.click();
      } catch (e) {
        // 弹窗关闭失败时静默忽略
      }
      
    } catch (navErr) {
      console.warn(`${LOG_PREFIX} 导航警告: ${navErr.message}`);
    }

    console.log('\n⏳ 请在浏览器中完成以下操作：');
    console.log('   1. 如有登录按钮，请点击并登录');
    console.log('   2. 如遇 Cloudflare 验证，请完成');
    console.log('   3. 确保能看到历史比赛的赔率表格');
    console.log('   4. 完成后回到这里按 Enter 保存会话\n');

    await ask(rl, '🎯 确认已完成登录并能看到赔率数据，按 Enter 保存会话...');

    // 再次访问具体比赛页验证
    console.log('\n验证登录状态...');
    const testUrl = 'https://www.oddsportal.com/football/england/premier-league/fulham-burnley-8EamNN8b/';
    await page.goto(testUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await new Promise((resolve) => {
      setTimeout(resolve, 5000);
    });
    
    const title = await page.title();
    console.log(`${LOG_PREFIX} 验证页面标题: ${title}`);

    // 保存会话
    console.log(`${LOG_PREFIX} 正在捕获会话状态...`);
    const storageState = await browser.storageState();
    const { sessionPath, backupPath, cookiePath, cookieStr } = await saveSession(storageState);

    console.log('\n' + '='.repeat(60));
    console.log('✅ 登录捕获完成！');
    console.log('='.repeat(60));
    console.log(`📝 主会话文件: ${sessionPath}`);
    console.log(`💾 备份文件: ${backupPath}`);
    console.log(`🍪 Cookie 文件: ${cookiePath}`);
    console.log(`🔑 Cookie 预览: ${cookieStr.substring(0, 100)}${cookieStr.length > 100 ? '...' : ''}`);
    console.log(`📊 Cookie 数量: ${storageState.cookies?.length || 0}`);
    console.log('='.repeat(60));
    console.log('\n💡 提示: 现在可以运行 p2p_harvest_v38.js 进行带证收割！');

  } catch (error) {
    console.error(`${LOG_PREFIX} ✗ 错误:`, error.message);
    process.exit(1);
  } finally {
    if (browser) {
      await browser.close();
      console.log(`${LOG_PREFIX} 浏览器已关闭`);
    }
    rl.close();
  }
}

main().catch(err => {
  console.error(`${LOG_PREFIX} 致命错误:`, err);
  process.exit(1);
});
