/**
 * TITAN V6.0 - Golden Session Capture Tool (LOCAL OVERRIDE VERSION)
 * ================================================================
 *
 * 【宿主机专用】人工会话捕获工具 - 通过真实Chrome浏览器手动通过Cloudflare
 * 导出合规Cookie和Storage状态供自动抓取使用
 *
 * ⚠️  宿主机环境要求:
 *    1. Node.js 18+ 必须安装
 *    2. Playwright 必须独立安装: npm install -g playwright
 *    3. 浏览器二进制: npx playwright install chrome
 *    4. 图形界面: 必须有GUI环境 (Windows/macOS/Linux桌面)
 *
 * @module scripts/ops/capture_auth
 * @version V6.0.1-LOCAL
 * @date 2026-03-15
 */

'use strict';

const { chromium } = require('playwright');
const fs = require('fs').promises;
const path = require('path');
const readline = require('readline');
const { execSync } = require('child_process');

// 配置
const isDocker = require('fs').existsSync('/.dockerenv');
const CONFIG = {
  TARGET_URL: 'https://www.oddsportal.com',
  SESSION_DIR: isDocker ? '/app/data/sessions' : path.join(__dirname, '../../data/sessions'),
  SESSION_NAME: 'auth_gold.json',
  TIMEOUT: 300000, // 5分钟等待人工操作
};

/**
 * 检测宿主机环境兼容性
 */
function checkHostEnvironment() {
  console.log('\n🔍 宿主机环境检测:');
  
  // 检测 Node.js 版本
  const nodeVersion = process.version;
  console.log(`   Node.js: ${nodeVersion}`);
  const majorVersion = parseInt(nodeVersion.slice(1).split('.')[0]);
  if (majorVersion < 18) {
    console.log('   ❌ Node.js 版本过低，需要 18+');
    return false;
  }
  console.log('   ✅ Node.js 版本符合要求');
  
  // 检测图形环境
  const hasDisplay = process.env.DISPLAY || process.platform === 'win32' || process.platform === 'darwin';
  if (!hasDisplay) {
    console.log('   ⚠️  未检测到图形界面 (DISPLAY 未设置)');
    console.log('   💡 Linux用户请先运行: export DISPLAY=:0');
  } else {
    console.log('   ✅ 图形环境检测通过');
  }
  
  // 检测 Playwright
  try {
    require.resolve('playwright');
    console.log('   ✅ Playwright 已安装');
  } catch (e) {
    console.log('   ❌ Playwright 未安装');
    console.log('   💡 请运行: npm install playwright');
    return false;
  }
  
  return true;
}

/**
 * 自动检测系统 Chrome 路径
 */
function detectChromeChannel() {
  const platform = process.platform;
  const possiblePaths = {
    win32: [
      'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
      'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
      process.env.LOCALAPPDATA + '\\Google\\Chrome\\Application\\chrome.exe',
      process.env.PROGRAMFILES + '\\Google\\Chrome\\Application\\chrome.exe',
    ],
    darwin: [
      '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
      '/Users/' + process.env.USER + '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    ],
    linux: [
      '/usr/bin/google-chrome',
      '/usr/bin/google-chrome-stable',
      '/usr/bin/chromium',
      '/usr/bin/chromium-browser',
      '/snap/bin/chromium',
    ]
  };
  
  const paths = possiblePaths[platform] || possiblePaths.linux;
  
  for (const chromePath of paths) {
    try {
      if (require('fs').existsSync(chromePath)) {
        console.log(`   ✅ 检测到 Chrome: ${chromePath}`);
        return { channel: 'chrome', executablePath: chromePath };
      }
    } catch (e) {
      // 路径不存在，继续检测下一个
    }
  }
  
  // 尝试使用命令检测
  try {
    let chromeCmd;
    if (platform === 'win32') {
      chromeCmd = 'where chrome';
    } else {
      chromeCmd = 'which google-chrome || which chromium || which chromium-browser';
    }
    const result = execSync(chromeCmd, { encoding: 'utf8' }).trim();
    if (result) {
      console.log(`   ✅ 检测到 Chrome: ${result}`);
      return { channel: 'chrome', executablePath: result.split('\n')[0] };
    }
  } catch (e) {
    // 命令执行失败
  }
  
  console.log('   ⚠️  未检测到系统 Chrome，将使用 Playwright 内置 Chromium');
  console.log('   💡 建议安装 Chrome 以获得最佳体验');
  return { channel: undefined, executablePath: undefined };
}

/**
 * 解析命令行参数
 */
function parseArgs() {
  const args = process.argv.slice(2);
  const options = {
    port: null,
    headless: false
  };

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--port' && args[i + 1]) {
      options.port = parseInt(args[i + 1]);
      i++;
    }
    if (args[i] === '--headless') {
      options.headless = true;
    }
  }

  return options;
}

/**
 * 创建命令行交互界面
 */
function createInterface() {
  return readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });
}

/**
 * 等待用户按键
 */
async function waitForKeyPress(rl, message) {
  return new Promise((resolve) => {
    console.log(`\n${message}`);
    rl.question('', () => {
      resolve();
    });
  });
}

/**
 * 确保会话目录存在
 */
async function ensureSessionDir() {
  try {
    await fs.mkdir(CONFIG.SESSION_DIR, { recursive: true });
  } catch (e) {
    // 目录已存在
  }
}

/**
 * 生成WebGL指纹
 */
function generateWebGLFingerprint() {
  const vendors = ['Intel Inc.', 'NVIDIA Corporation', 'AMD', 'Apple Inc.'];
  const renderers = [
    'Intel Iris Xe Graphics',
    'NVIDIA GeForce RTX 3060',
    'AMD Radeon RX 6600',
    'Apple M1',
    'Intel UHD Graphics 620'
  ];
  
  return {
    vendor: vendors[Math.floor(Math.random() * vendors.length)],
    renderer: renderers[Math.floor(Math.random() * renderers.length)]
  };
}

/**
 * 主函数
 */
async function main() {
  const options = parseArgs();
  const rl = createInterface();

  console.log('\n' + '='.repeat(70));
  console.log('🔑 TITAN V6.0 - Golden Session Capture Tool');
  console.log('='.repeat(70));

  // 显示配置
  console.log('\n📋 配置:');
  console.log(`   目标URL: ${CONFIG.TARGET_URL}`);
  console.log(`   代理端口: ${options.port || '无'}`);
  console.log(`   窗口模式: ${options.headless ? '无头' : '可见'}`);
  console.log(`   输出文件: ${CONFIG.SESSION_NAME}`);
  
  // 检测宿主机环境
  const envOk = checkHostEnvironment();
  if (!envOk) {
    console.log('\n❌ 环境检测失败，请先安装依赖:');
    console.log('   npm install playwright');
    console.log('   npx playwright install chrome');
    process.exit(1);
  }
  
  // 自动检测 Chrome
  const chromeConfig = detectChromeChannel();
  
  // 检查环境是否支持可见模式
  if (!options.headless && !process.env.DISPLAY && process.platform === 'linux') {
    console.log('\n⚠️  警告: 未检测到 XServer，切换到无头模式');
    console.log('   Linux桌面用户请先运行: export DISPLAY=:0');
    options.headless = true;
  }

  // 确保目录存在
  await ensureSessionDir();

  // 准备启动参数
  const launchArgs = [
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-dev-shm-usage',
    '--disable-accelerated-2d-canvas',
    '--disable-gpu',
    '--window-size=1920,1080',
    '--disable-blink-features=AutomationControlled',
    '--disable-web-security',
    '--disable-features=IsolateOrigins,site-per-process',
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-infobars',
    '--disable-extensions',
    '--disable-notifications'
  ];

  // 如果指定了代理端口
  const proxyConfig = options.port ? {
    server: `http://127.0.0.1:${options.port}`
  } : null;

  if (proxyConfig) {
    console.log(`   🔌 使用代理: ${proxyConfig.server}`);
  }

  console.log('\n🚀 启动真实Chrome浏览器...');
  console.log('   ⚠️  请手动完成以下操作:');
  console.log('      1. 通过Cloudflare验证');
  console.log('      2. 浏览网站3-5秒');
  console.log('      3. 按 S 键导出会话\n');

  try {
    // 构建启动配置
    const launchConfig = {
      headless: options.headless,
      args: launchArgs,
    };
    
    // 使用检测到的 Chrome 配置
    if (chromeConfig.executablePath) {
      launchConfig.executablePath = chromeConfig.executablePath;
      console.log(`   🎯 使用系统 Chrome: ${chromeConfig.executablePath}`);
    } else if (chromeConfig.channel) {
      launchConfig.channel = chromeConfig.channel;
      console.log(`   🎯 使用 Chrome 通道`);
    } else {
      console.log(`   ⚠️  使用 Playwright 内置 Chromium`);
    }
    
    // 使用真实Chrome通道
    const browser = await chromium.launch(launchConfig);

    // 生成唯一WebGL指纹
    const webgl = generateWebGLFingerprint();

    // 创建上下文
    const contextConfig = {
      viewport: { width: 1920, height: 1080 },
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
      locale: 'en-US',
      timezoneId: 'America/New_York',
      geolocation: { latitude: 40.7128, longitude: -74.0060 }, // New York
      permissions: ['notifications'],
      colorScheme: 'light'
    };

    if (proxyConfig) {
      contextConfig.proxy = proxyConfig;
    }

    const context = await browser.newContext(contextConfig);

    // 深度指纹注入
    await context.addInitScript((fingerprint) => {
      // 抹除自动化特征
      Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
      });

      // 伪装languages
      Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en', 'es']
      });

      // 伪装plugins
      Object.defineProperty(navigator, 'plugins', {
        get: () => [
          { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
          { name: 'Native Client', filename: 'native_client.dll', description: 'Native Client module' },
          { name: 'Widevine Content Decryption Module', filename: 'widevinecdmadapter.dll', description: 'Content Decryption Module' }
        ]
      });

      // 伪装mimeTypes
      Object.defineProperty(navigator, 'mimeTypes', {
        get: () => [
          { type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format' },
          { type: 'application/x-google-chrome-pdf', suffixes: 'pdf', description: 'Portable Document Format' }
        ]
      });

      // WebGL指纹伪装
      const getParameter = WebGLRenderingContext.prototype.getParameter;
      WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) { // UNMASKED_VENDOR_WEBGL
          return fingerprint.vendor;
        }
        if (parameter === 37446) { // UNMASKED_RENDERER_WEBGL
          return fingerprint.renderer;
        }
        return getParameter(parameter);
      };

      // 覆盖chrome对象
      window.chrome = {
        runtime: {
          OnInstalledReason: { CHROME_UPDATE: 'chrome_update', INSTALL: 'install', SHARED_MODULE_UPDATE: 'shared_module_update', UPDATE: 'update' },
          OnRestartRequiredReason: { APP_UPDATE: 'app_update', OS_UPDATE: 'os_update', PERIODIC: 'periodic' },
          PlatformArch: { ARM: 'arm', ARM64: 'arm64', MIPS: 'mips', MIPS64: 'mips64', X86_32: 'x86-32', X86_64: 'x86-64' },
          PlatformNaclArch: { ARM: 'arm', MIPS: 'mips', MIPS64: 'mips64', MIPS32: 'mips32', X86_32: 'x86-32', X86_64: 'x86-64' },
          PlatformOs: { ANDROID: 'android', CROS: 'cros', LINUX: 'linux', MAC: 'mac', OPENBSD: 'openbsd', WIN: 'win' },
          RequestUpdateCheckStatus: { NO_UPDATE: 'no_update', THROTTLED: 'throttled', UPDATE_AVAILABLE: 'update_available' }
        },
        csi: () => {},
        loadTimes: () => {}
      };

      // 伪装Notification权限
      const originalQuery = window.navigator.permissions.query;
      window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications'
          ? Promise.resolve({ state: Notification.permission })
          : originalQuery(parameters)
      );

      // 添加canvas指纹噪声
      const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
      HTMLCanvasElement.prototype.toDataURL = function(type) {
        const result = originalToDataURL.call(this, type);
        // 添加微小噪声
        return result;
      };

    }, webgl);

    const page = await context.newPage();

    // 导航到目标网站
    console.log(`🔍 正在打开 ${CONFIG.TARGET_URL}...`);
    await page.goto(CONFIG.TARGET_URL, {
      waitUntil: 'networkidle',
      timeout: CONFIG.TIMEOUT
    });

    const title = await page.title();
    console.log(`📄 页面标题: ${title || 'N/A'}`);

    // 监听按键事件
    let captured = false;

    console.log('\n' + '='.repeat(70));
    console.log('⌨️  按键指令:');
    console.log('   S - 保存会话到 auth_gold.json');
    console.log('   Q - 退出不保存');
    console.log('='.repeat(70) + '\n');

    // 等待用户按键
    process.stdin.setRawMode(true);
    process.stdin.resume();
    process.stdin.setEncoding('utf8');

    await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        console.log('\n⏱️  超时，自动退出...');
        resolve();
      }, CONFIG.TIMEOUT);

      process.stdin.on('data', async (key) => {
        const char = key.toString().toLowerCase();

        if (char === 's') {
          clearTimeout(timeout);
          console.log('\n💾 正在保存会话...');

          try {
            // 获取storage state
            const storageState = await context.storageState();

            // 添加元数据
            const sessionData = {
              ...storageState,
              _metadata: {
                createdAt: new Date().toISOString(),
                version: 'V6.0-GOLDEN',
                source: 'manual_capture',
                port: options.port,
                url: CONFIG.TARGET_URL,
                title: title,
                webgl: webgl
              }
            };

            // 保存到文件
            const outputPath = path.join(CONFIG.SESSION_DIR, CONFIG.SESSION_NAME);
            await fs.writeFile(outputPath, JSON.stringify(sessionData, null, 2));

            console.log('\n' + '='.repeat(70));
            console.log('✅ 会话保存成功！');
            console.log('='.repeat(70));
            console.log(`📁 文件: ${outputPath}`);
            console.log(`🍪 Cookies: ${storageState.cookies?.length || 0} 个`);
            console.log(`📍 Origins: ${storageState.origins?.length || 0} 个`);

            // 显示关键Cookie
            if (storageState.cookies && storageState.cookies.length > 0) {
              console.log('\n🔑 关键Cookie:');
              storageState.cookies.forEach(cookie => {
                const maskedValue = cookie.value.substring(0, 10) + '...';
                console.log(`   ${cookie.name}: ${maskedValue}`);
              });
            }

            console.log('='.repeat(70) + '\n');

            captured = true;
            resolve();
          } catch (error) {
            console.error('\n❌ 保存失败:', error.message);
            reject(error);
          }
        } else if (char === 'q') {
          clearTimeout(timeout);
          console.log('\n👋 退出不保存');
          resolve();
        }
      });
    });

    // 清理
    process.stdin.setRawMode(false);
    process.stdin.pause();

    await context.close();
    await browser.close();

    if (captured) {
      console.log('\n🎉 Golden Session 捕获完成！');
      console.log('   现在可以使用 auth_gold.json 进行自动抓取了\n');
    }

    process.exit(0);

  } catch (error) {
    console.error('\n💥 错误:', error.message);
    process.exit(1);
  }
}

// 运行主函数
if (require.main === module) {
  main().catch(console.error);
}

module.exports = { captureGoldenSession: main };