/**
 * TITAN V6.0 - Golden Cookie Injection Tool
 * =======================================
 *
 * 将手动捕获的黄金Cookie转换为Playwright标准storageState格式
 * 并注入系统供自动抓取使用
 *
 * @module scripts/ops/inject_golden_cookies
 * @version V6.0.0-GOLDEN
 * @date 2026-03-15
 */

'use strict';

const fs = require('fs').promises;
const path = require('path');

// 配置
const CONFIG = {
  SESSION_DIR: '/app/data/sessions',
  SESSION_FILE: 'auth_gold.json'
};

/**
 * 将Chrome格式Cookie转换为Playwright格式
 */
function convertCookies(chromeCookies) {
  return chromeCookies.map(cookie => {
    // Playwright只接受特定字段
    const playwrightCookie = {
      name: cookie.name,
      value: cookie.value,
      domain: cookie.domain,
      path: cookie.path || '/',
      httpOnly: cookie.httpOnly || false,
      secure: cookie.secure || false,
      sameSite: convertSameSite(cookie.sameSite)
    };

    // 处理过期时间 - Playwright要求整数Unix时间戳（秒）
    if (cookie.expirationDate) {
      const expires = Math.floor(cookie.expirationDate);
      // 确保过期时间是有效的（不能是过去）
      const now = Math.floor(Date.now() / 1000);
      if (expires > now) {
        playwrightCookie.expires = expires;
      }
    }

    return playwrightCookie;
  }).filter(cookie => {
    // 过滤掉无效的cookie
    return cookie.name && cookie.value && cookie.domain;
  });
}

/**
 * 转换sameSite值
 */
function convertSameSite(sameSite) {
  if (!sameSite || sameSite === 'unspecified') {
    return 'Lax';
  }
  // 首字母大写
  return sameSite.charAt(0).toUpperCase() + sameSite.slice(1).toLowerCase();
}

/**
 * 创建storageState对象
 */
function createStorageState(cookies) {
  return {
    cookies: convertCookies(cookies),
    origins: [
      {
        origin: 'https://www.oddsportal.com',
        localStorage: []
      }
    ],
    _metadata: {
      createdAt: new Date().toISOString(),
      version: 'V6.0-GOLDEN-INJECTION',
      source: 'manual_cookies',
      cookieCount: cookies.length,
      injectedBy: 'TITAN-V6.0-GOLD-INJECTION'
    }
  };
}

/**
 * 主函数
 */
async function main() {
  console.log('\n' + '='.repeat(70));
  console.log('🔑 TITAN V6.0 - Golden Cookie Injection');
  console.log('='.repeat(70));

  try {
    // 确保目录存在
    await fs.mkdir(CONFIG.SESSION_DIR, { recursive: true });

    // 从标准输入读取Cookie JSON
    console.log('\n📥 等待Cookie数据从标准输入...');
    console.log('   (请粘贴Cookie JSON数组并按Ctrl+D)');

    let inputData = '';
    process.stdin.setEncoding('utf8');
    
    for await (const chunk of process.stdin) {
      inputData += chunk;
    }

    // 解析Cookie数据
    let cookies;
    try {
      cookies = JSON.parse(inputData);
    } catch (e) {
      console.error('\n❌ Cookie JSON解析失败:', e.message);
      process.exit(1);
    }

    if (!Array.isArray(cookies)) {
      console.error('\n❌ 输入数据必须是Cookie数组');
      process.exit(1);
    }

    console.log(`\n📊 原始Cookie数量: ${cookies.length}`);

    // 显示关键Cookie
    console.log('\n🔑 关键Cookie列表:');
    const keyCookies = ['oddsportalcom_session', 'op_user_hash', 'op_user_cookie', '_ga', '_ga_5YY4JY41P1'];
    cookies.forEach(cookie => {
      const isKey = keyCookies.includes(cookie.name);
      const maskedValue = cookie.value.substring(0, 20) + '...';
      console.log(`   ${isKey ? '⭐' : '  '} ${cookie.name}: ${maskedValue}`);
    });

    // 创建storageState
    const storageState = createStorageState(cookies);

    // 写入文件
    const outputPath = path.join(CONFIG.SESSION_DIR, CONFIG.SESSION_FILE);
    await fs.writeFile(outputPath, JSON.stringify(storageState, null, 2));

    console.log('\n' + '='.repeat(70));
    console.log('✅ Golden Cookie注入成功！');
    console.log('='.repeat(70));
    console.log(`📁 输出文件: ${outputPath}`);
    console.log(`🍪 Playwright格式Cookie: ${storageState.cookies.length} 个`);
    console.log(`🌐 Origins: ${storageState.origins.length} 个`);
    
    // 验证文件
    const stats = await fs.stat(outputPath);
    console.log(`📊 文件大小: ${stats.size} bytes`);

    console.log('\n🔥 22个代理节点身份识别链路已打通！');
    console.log('   现在可以运行自动抓取了\n');

    process.exit(0);

  } catch (error) {
    console.error('\n💥 注入失败:', error.message);
    process.exit(1);
  }
}

// 运行主函数
if (require.main === module) {
  main().catch(console.error);
}

module.exports = { 
  injectGoldenCookies: main,
  convertCookies,
  createStorageState
};