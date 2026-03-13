#!/usr/bin/env node
/**
 * @file 离线 Cookie 导入工具 (Manual Cookie Bridge)
 * @description 物理穿透方案：直接导入真实浏览器 Cookie，绕过所有自动化验证
 * @version 1.0.0
 */

const fs = require('fs').promises;
const path = require('path');
const readline = require('readline');

const LOG_PREFIX = '[COOKIE-BRIDGE]';

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
 * 解析 Cookie 字符串
 * @param {string} cookieStr - 原始 Cookie 字符串
 * @returns {Array} - 标准 cookies 数组
 */
function parseCookieString(cookieStr) {
  const cookies = [];

  // 清理输入
  const cleanStr = cookieStr.trim();
  if (!cleanStr) {
    return cookies;
  }

  // 分割 cookie 对（支持 ; 和 ; 加空格）
  const pairs = cleanStr.split(/;\s*/);

  for (const pair of pairs) {
    const trimmed = pair.trim();
    if (!trimmed) continue;

    // 找到第一个 = 的位置
    const eqIndex = trimmed.indexOf('=');
    if (eqIndex === -1) continue;

    const name = trimmed.substring(0, eqIndex).trim();
    const value = trimmed.substring(eqIndex + 1).trim();

    if (name) {
      cookies.push({
        name,
        value,
        domain: '.fotmob.com',
        path: '/',
        expires: Math.floor(Date.now() / 1000) + 86400 * 7, // 7天后过期
        httpOnly: false,
        secure: true,
        sameSite: 'Lax'
      });
    }
  }

  return cookies;
}

/**
 * 创建标准 storageState 对象
 * @param {Array} cookies - Cookie 数组
 * @returns {object} - 标准 storageState 格式
 */
function createStorageState(cookies) {
  return {
    cookies,
    origins: [
      {
        origin: 'https://www.fotmob.com',
        localStorage: []
      }
    ]
  };
}

/**
 * 保存会话文件
 * @param {object} storageState - 存储状态对象
 */
async function saveSession(storageState) {
  const dataDir = path.join(__dirname, '..', 'data', 'sessions');
  await fs.mkdir(dataDir, { recursive: true });

  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const sessionPath = path.join(dataDir, `manual_bridge_session_${timestamp}.json`);

  await fs.writeFile(sessionPath, JSON.stringify(storageState, null, 2));

  return sessionPath;
}

/**
 * 显示使用指引
 */
function showGuide() {
  console.log('\n' + '='.repeat(60));
  console.log('📋 离线 Cookie 导入工具 (Manual Cookie Bridge)');
  console.log('='.repeat(60));
  console.log('');
  console.log('【获取 Cookie 步骤】');
  console.log('1. 在 Windows/Mac 上打开 Chrome 浏览器');
  console.log('2. 访问 https://www.fotmob.com/');
  console.log('3. 按 F12 打开开发者工具');
  console.log('4. 切换到 Network (网络) 标签');
  console.log('5. 刷新页面 (F5)');
  console.log('6. 点击任意一个请求');
  console.log('7. 在右侧 Headers 中找到 "Cookie:" 字段');
  console.log('8. 复制整行 Cookie 字符串');
  console.log('');
  console.log('='.repeat(60));
  console.log('');
}

/**
 * 询问用户输入
 * @param rl
 * @param question
 */
function ask(rl, question) {
  return new Promise(resolve => {
    rl.question(question, answer => resolve(answer));
  });
}

/**
 * 主函数
 */
async function main() {
  console.log(`${LOG_PREFIX} 启动离线 Cookie 导入工具 v1.0`);
  console.log(`${LOG_PREFIX} 模式: 物理穿透 | 绕过自动化验证`);

  const rl = createReadline();

  try {
    // 显示指引
    showGuide();

    // 获取用户输入
    console.log('请从 Windows/Mac 浏览器 F12 网络请求头中复制 Cookie 并粘贴到此处：');
    console.log('(粘贴后按 Enter 确认)\n');

    const cookieInput = await ask(rl, '> ');

    if (!cookieInput.trim()) {
      console.log(`${LOG_PREFIX} ✗ 未输入 Cookie，退出`);
      process.exit(1);
    }

    // 解析 Cookie
    console.log(`${LOG_PREFIX} 正在解析 Cookie...`);
    const cookies = parseCookieString(cookieInput);

    if (cookies.length === 0) {
      console.log(`${LOG_PREFIX} ✗ 未解析到有效的 Cookie`);
      process.exit(1);
    }

    console.log(`${LOG_PREFIX} ✓ 成功解析 ${cookies.length} 个 Cookie`);

    // 显示解析结果摘要
    console.log('\n解析结果预览：');
    cookies.forEach((cookie, index) => {
      const valuePreview = cookie.value.length > 30
        ? cookie.value.substring(0, 30) + '...'
        : cookie.value;
      console.log(`  ${index + 1}. ${cookie.name}=${valuePreview}`);
    });

    // 创建 storageState
    const storageState = createStorageState(cookies);

    // 保存会话
    const sessionPath = await saveSession(storageState);

    // 输出结果
    console.log('\n' + '='.repeat(60));
    console.log('✓ Cookie 导入成功！');
    console.log('='.repeat(60));
    console.log(`文件路径: ${sessionPath}`);
    console.log(`Cookie 数量: ${cookies.length}`);
    console.log(`有效期至: ${new Date(Date.now() + 86400 * 7 * 1000).toLocaleString()}`);
    console.log('='.repeat(60));
    console.log('\n使用方式：');
    console.log(`  context = await browser.newContext({`);
    console.log(`    storageState: '${sessionPath}'`);
    console.log(`  });`);
    console.log('');

  } catch (error) {
    console.error(`${LOG_PREFIX} ✗ 错误:`, error.message);
    console.error(error.stack);
    process.exit(1);

  } finally {
    rl.close();
  }
}

// 执行
main().catch(err => {
  console.error(`${LOG_PREFIX} 致命错误:`, err);
  process.exit(1);
});
