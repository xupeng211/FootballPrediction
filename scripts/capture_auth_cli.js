#!/usr/bin/env node
/**
 * @file OddsPortal Cookie 命令行捕获器
 * @description 无需图形界面，直接接受 Cookie 字符串
 * @version 1.0.0
 */

const fs = require('fs').promises;
const path = require('path');
const readline = require('readline');

const LOG_PREFIX = '[AUTH-CLI]';

function createReadline() {
  return readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });
}

function ask(rl, question) {
  return new Promise(resolve => {
    rl.question(question, answer => resolve(answer.trim()));
  });
}

/**
 * 解析 Cookie 字符串为标准格式
 */
function parseCookieString(cookieStr) {
  const cookies = [];
  const pairs = cookieStr.split(/;\s*/);
  
  for (const pair of pairs) {
    const trimmed = pair.trim();
    if (!trimmed) continue;
    
    const eqIndex = trimmed.indexOf('=');
    if (eqIndex === -1) continue;
    
    const name = trimmed.substring(0, eqIndex).trim();
    const value = trimmed.substring(eqIndex + 1).trim();
    
    if (name) {
      cookies.push({
        name,
        value,
        domain: '.oddsportal.com',
        path: '/',
        expires: Math.floor(Date.now() / 1000) + 86400 * 30, // 30天
        httpOnly: false,
        secure: true,
        sameSite: 'Lax'
      });
    }
  }
  
  return {
    cookies,
    origins: [
      { origin: 'https://www.oddsportal.com', localStorage: [] }
    ]
  };
}

async function main() {
  console.log('\n' + '='.repeat(60));
  console.log('🎯 OddsPortal Cookie 命令行捕获器');
  console.log('='.repeat(60));
  console.log('');
  console.log('请按以下步骤获取 Cookie:');
  console.log('1. 在本机浏览器打开 https://www.oddsportal.com');
  console.log('2. 完成登录并通过 Cloudflare 验证');
  console.log('3. 按 F12 打开开发者工具 -> Application/Storage -> Cookies');
  console.log('4. 复制所有 Cookie（格式: name=value; name2=value2）');
  console.log('');
  
  const rl = createReadline();
  
  try {
    const cookieStr = await ask(rl, '\n📝 请粘贴 Cookie 字符串（或输入"skip"跳过）: ');
    
    if (cookieStr.toLowerCase() === 'skip') {
      console.log('⏭️  已跳过，将使用游客模式');
      rl.close();
      return;
    }
    
    if (!cookieStr || cookieStr.length < 10) {
      console.log('⚠️  Cookie 太短，可能无效');
    }
    
    console.log('\n🔧 解析 Cookie...');
    const storageState = parseCookieString(cookieStr);
    
    console.log(`✅ 解析成功: ${storageState.cookies.length} 个 Cookie`);
    console.log('   关键 Cookie:', storageState.cookies.slice(0, 5).map(c => c.name).join(', '));
    
    // 保存会话
    const dataDir = path.join(__dirname, '..', 'data', 'sessions');
    await fs.mkdir(dataDir, { recursive: true });
    
    const sessionPath = path.join(dataDir, 'auth_gold.json');
    await fs.writeFile(sessionPath, JSON.stringify(storageState, null, 2));
    
    console.log('\n' + '='.repeat(60));
    console.log('✅ 会话已保存！');
    console.log('='.repeat(60));
    console.log(`📝 文件路径: ${sessionPath}`);
    console.log(`📊 Cookie 数量: ${storageState.cookies.length}`);
    console.log('');
    console.log('💡 现在可以运行:');
    console.log('   node scripts/ops/p2p_harvest_v38.js');
    console.log('='.repeat(60));
    
  } catch (error) {
    console.error(`${LOG_PREFIX} ✗ 错误:`, error.message);
  } finally {
    rl.close();
  }
}

main();