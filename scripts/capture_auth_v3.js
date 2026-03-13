#!/usr/bin/env node
/**
 * @file 极简平民模式办证脚本 (Civilian Mode)
 * @description 像普通用户一样浏览，彻底卸载重型装甲
 * @version 3.0.0
 */

const { chromium } = require('playwright');
const readline = require('readline');
const fs = require('fs').promises;
const path = require('path');

const LOG_PREFIX = '[AUTH-v3]';

// ==================== 平民化配置 ====================

/**
 * 极简 Stealth - 只保留一行
 */
const MINIMAL_STEALTH_SCRIPT = `
(() => {
  delete navigator.webdriver;
})();
`;

/**
 * 固定 UA - 稍旧版本 Chrome，增加真实感
 */
const CIVILIAN_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.0.36';

/**
 * 标准窗口尺寸
 */
const CIVILIAN_VIEWPORT = {
  width: 1280,
  height: 1024
};

/**
 * 用户数据目录
 */
const USER_DATA_DIR = path.join(__dirname, '..', 'data', 'browser_profile');

// ==================== 工具函数 ====================

/**
 * 强制清理用户数据目录
 */
async function forceCleanProfile() {
  try {
    await fs.rm(USER_DATA_DIR, { recursive: true, force: true });
    console.log(`${LOG_PREFIX} ✓ 已清理旧配置文件`);
  } catch (err) {
    console.log(`${LOG_PREFIX} 无需清理（目录不存在）`);
  }
}

/**
 * 创建 readline 接口
 */
function createReadline() {
  return readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });
}

/**
 * 询问用户
 * @param rl
 * @param question
 */
function ask(rl, question) {
  return new Promise(resolve => {
    rl.question(question, answer => resolve(answer.trim()));
  });
}

/**
 * 保存会话
 * @param storageState
 */
async function saveSession(storageState) {
  const dataDir = path.join(__dirname, '..', 'data', 'sessions');
  await fs.mkdir(dataDir, { recursive: true });

  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const sessionPath = path.join(dataDir, `fotmob_session_v3_${timestamp}.json`);

  await fs.writeFile(sessionPath, JSON.stringify(storageState, null, 2));

  // 提取并保存 cookie 字符串
  const cookieStr = storageState.cookies
    ?.map(c => `${c.name}=${c.value}`)
    .join('; ') || '';

  const cookiePath = path.join(dataDir, `fotmob_cookies_v3_${timestamp}.txt`);
  await fs.writeFile(cookiePath, cookieStr);

  return { sessionPath, cookiePath, cookieStr };
}

/**
 * 显示指引
 */
function showInstructions() {
  console.log('\n' + '='.repeat(50));
  console.log('🏠 平民模式办证引导');
  console.log('='.repeat(50));
  console.log('1. 浏览器将以普通用户模式打开');
  console.log('2. 如遇验证，请像普通用户一样完成');
  console.log('3. 完成后按 Enter 保存会话');
  console.log('='.repeat(50) + '\n');
}

// ==================== 主程序 ====================

/**
 *
 */
async function main() {
  console.log(`${LOG_PREFIX} 启动平民模式办证脚本 v3.0`);
  console.log(`${LOG_PREFIX} 模式: 极简平民 | 窗口: 1280x1024`);
  console.log(`${LOG_PREFIX} Stealth: 仅 delete navigator.webdriver`);

  // 步骤1: 强制清理旧配置
  console.log(`${LOG_PREFIX} 正在清理用户数据目录...`);
  await forceCleanProfile();

  let browser = null;
  const rl = createReadline();

  try {
    // 步骤2: 启动持久化上下文（平民配置）
    console.log(`${LOG_PREFIX} 启动浏览器...`);

    browser = await chromium.launchPersistentContext(USER_DATA_DIR, {
      headless: false,

      // 标准窗口
      viewport: CIVILIAN_VIEWPORT,

      // 固定 UA
      userAgent: CIVILIAN_USER_AGENT,

      // 地区设置
      locale: 'en-US',
      timezoneId: 'America/New_York',

      // 启动参数
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-blink-features=AutomationControlled',
        '--disable-dev-shm-usage',
        '--window-size=1280,1024',
        '--window-position=100,100'
      ],

      // ========== 物理屏蔽协议弹窗 ==========
      prefs: {
        // 排除所有 fotmob 相关协议
        'protocol_handler.excluded_schemes.fotmob': true,
        'protocol_handler.excluded_schemes.af0654': true,
        'protocol_handler.excluded_schemes.web+whatsapp': true,
        'protocol_handler.excluded_schemes.whatsapp': true,
        'protocol_handler.excluded_schemes.mailto': true,
        'protocol_handler.excluded_schemes.tel': true,
        // 禁止所有协议配对
        'protocol_handler.allowed_origin_protocol_pairs': {},
        // 禁用外部协议处理
        'custom_handlers.enabled': false,
        // 恢复上次会话
        'profile.restore_on_startup': 1,
        // 禁用默认浏览器检查
        'default_browser_setting.enabled': false
      }
    });

    console.log(`${LOG_PREFIX} ✓ 浏览器启动成功`);

    // 步骤3: 注入极简 Stealth
    await browser.addInitScript(MINIMAL_STEALTH_SCRIPT);
    console.log(`${LOG_PREFIX} ✓ 极简 Stealth 已注入`);

    // 创建页面
    const page = await browser.newPage();
    console.log(`${LOG_PREFIX} ✓ 新页面已创建`);

    // 显示指引
    showInstructions();

    // 步骤4: 导航到 FotMob
    const targetUrl = 'https://www.fotmob.com/';
    console.log(`${LOG_PREFIX} 正在导航到: ${targetUrl}`);

    try {
      await page.goto(targetUrl, {
        waitUntil: 'networkidle',
        timeout: 60000
      });
      console.log(`${LOG_PREFIX} ✓ 页面加载完成`);
    } catch (navErr) {
      console.warn(`${LOG_PREFIX} 导航警告: ${navErr.message}`);
    }

    // 步骤5: 等待用户完成验证
    console.log('\n⏳ 请在浏览器中完成验证（如有）');
    console.log('⏳ 完成后按 Enter 保存会话...\n');

    await ask(rl, '按 Enter 保存会话...');

    // 步骤6: 保存会话
    console.log(`${LOG_PREFIX} 正在捕获会话状态...`);
    const storageState = await browser.storageState();
    const { sessionPath, cookiePath, cookieStr } = await saveSession(storageState);

    console.log('\n' + '='.repeat(50));
    console.log('✓ 办证完成！');
    console.log('='.repeat(50));
    console.log(`会话文件: ${sessionPath}`);
    console.log(`Cookie 文件: ${cookiePath}`);
    console.log(`Cookie 预览: ${cookieStr.substring(0, 80)}${cookieStr.length > 80 ? '...' : ''}`);
    console.log('='.repeat(50));

  } catch (error) {
    console.error(`${LOG_PREFIX} ✗ 错误:`, error.message);
    console.error(error.stack);
    process.exit(1);

  } finally {
    if (browser) {
      await browser.close();
      console.log(`${LOG_PREFIX} 浏览器已关闭`);
    }
    rl.close();
  }
}

// 执行
main().catch(err => {
  console.error(`${LOG_PREFIX} 致命错误:`, err);
  process.exit(1);
});
