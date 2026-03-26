/**
 * TITAN V6.0 StealthNavigator - 战术操纵模块
 * ===========================================
 * 负责拟人化浏览器交互，解决"看得见"的问题
 * 
 * @module infrastructure/harvesters/StealthNavigator
 * @version V6.0-STEALTH-NAVIGATOR
 * @date 2026-03-16
 */

'use strict';

const RECON_CONFIG = require('../../../config/recon_config.json');
const BASE_URL = RECON_CONFIG.oddsportal.base_url;

/**
 * 贝塞尔曲线鼠标移动模拟
 * @param {Object} page - Playwright页面对象
 * @param {number} moveCount - 移动次数（默认3-5次随机）
 */
async function bezierMouseMovement(page, moveCount = null) {
  const width = 1920;
  const height = 1080;
  const count = moveCount || (3 + Math.floor(Math.random() * 3));

  for (let i = 0; i < count; i++) {
    const startX = Math.random() * width * 0.8 + width * 0.1;
    const startY = Math.random() * height * 0.8 + height * 0.1;
    const endX = Math.random() * width * 0.8 + width * 0.1;
    const endY = Math.random() * height * 0.8 + height * 0.1;

    // 贝塞尔曲线控制点
    const cp1X = startX + (endX - startX) * 0.3 + (Math.random() - 0.5) * 200;
    const cp1Y = startY + (endY - startY) * 0.3 + (Math.random() - 0.5) * 200;
    const cp2X = startX + (endX - startX) * 0.7 + (Math.random() - 0.5) * 200;
    const cp2Y = startY + (endY - startY) * 0.7 + (Math.random() - 0.5) * 200;

    // 生成贝塞尔曲线上的点
    const steps = 20 + Math.floor(Math.random() * 10);
    for (let t = 0; t <= 1; t += 1/steps) {
      const x = Math.pow(1-t, 3) * startX + 3 * Math.pow(1-t, 2) * t * cp1X +
                3 * (1-t) * Math.pow(t, 2) * cp2X + Math.pow(t, 3) * endX;
      const y = Math.pow(1-t, 3) * startY + 3 * Math.pow(1-t, 2) * t * cp1Y +
                3 * (1-t) * Math.pow(t, 2) * cp2Y + Math.pow(t, 3) * endY;

      await page.mouse.move(x, y);
      await page.waitForTimeout(10 + Math.random() * 20);
    }

    // 随机停留
    await page.waitForTimeout(200 + Math.random() * 300);
  }
}

/**
 * 模拟人类翻页滚动行为
 * @param {Object} page - Playwright页面对象
 * @param {number} scrollCount - 滚动次数
 */
async function humanLikeScrolling(page, scrollCount = 3) {
  for (let i = 0; i < scrollCount; i++) {
    const scrollAmount = 300 + Math.floor(Math.random() * 200);
    await page.mouse.wheel(0, scrollAmount);
    await page.waitForTimeout(500 + Math.random() * 500);

    // 偶尔向上滚动一点（人类阅读时的回滚）
    if (Math.random() > 0.6) {
      await page.mouse.wheel(0, -100 - Math.floor(Math.random() * 100));
      await page.waitForTimeout(300 + Math.random() * 200);
    }
  }
}

/**
 * 声东击西策略 - 访问其他页面后返回，触发全局状态机重新初始化
 * @param {Object} page - Playwright页面对象
 * @param {string} targetUrl - 最终目标URL
 */
async function contextSwitchManeuver(page, targetUrl) {
  try {
    // 访问Tennis分类
    await page.goto(`${BASE_URL}/tennis/`, { 
      waitUntil: 'domcontentloaded', 
      timeout: 30000 
    });
    await page.waitForTimeout(2000 + Math.random() * 1000);

    // 返回目标页面
    await page.goto(targetUrl, { 
      waitUntil: 'domcontentloaded', 
      timeout: 60000 
    });
    await page.waitForTimeout(3000);
  } catch (e) {
    console.log('   ⚠️  声东击西策略部分失败:', e.message);
  }
}

/**
 * 实时视力康复监测
 * 循环检测Pinnacle是否出现，最多60秒
 * @param {Object} page - Playwright页面对象
 * @param {Object} interceptedData - 拦截数据对象
 * @param {number} timeout - 超时时间（毫秒）
 * @returns {Object} { success: boolean, method: string }
 */
async function visionRecoveryCheck(page, interceptedData, timeout = 60000) {
  const startTime = Date.now();
  const checkInterval = 2000;

  while (Date.now() - startTime < timeout) {
    // 检查页面是否有Pinnacle赔率
    const hasPinnacle = await page.evaluate(() => {
      const text = document.body.innerText || '';
      const hasPinnacleText = /Pinnacle/i.test(text);
      const hasOddsPattern = /Pinnacle\D{0,100}\d+\.\d{2}/.test(text);
      return { hasPinnacleText, hasOddsPattern, textLength: text.length };
    });

    if (hasPinnacle.hasPinnacleText && hasPinnacle.hasOddsPattern) {
      return { success: true, method: 'pinnacle_detected' };
    }

    // 检查是否从API拦截到数据
    if (interceptedData && interceptedData.rawArrays && interceptedData.rawArrays.length > 0) {
      return { success: true, method: 'api_intercepted' };
    }

    // 继续拟人化交互
    if (Math.random() > 0.5) {
      await page.mouse.wheel(0, 200 + Math.floor(Math.random() * 200));
    }
    await page.waitForTimeout(checkInterval);
  }

  return { success: false, method: 'timeout' };
}

/**
 * 执行完整的拟人化交互序列
 * @param {Object} page - Playwright页面对象
 */
async function executeHumanMimicSequence(page) {
  await bezierMouseMovement(page);
  await humanLikeScrolling(page);
}

// ===================================================================
// V6.0 STEALTH HARDENING: 浏览器指纹加固与幽灵化改造
// ===================================================================

/**
 * 高级指纹掩码脚本 - 在页面任何JS执行前注入
 * 抹除自动化痕迹，模拟真实人类浏览器指纹
 */
const FINGERPRINT_MASK_SCRIPT = `
(() => {
  // ===== 1. WebDriver彻底抹除 =====
  Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
    configurable: true,
    enumerable: true
  });
  
  // 删除chrome对象上的自动化标记
  if (window.chrome) {
    Object.defineProperty(window.chrome, 'runtime', {
      get: () => ({ 
        OnInstalledReason: {CHROME_UPDATE: "chrome_update"},
        OnRestartRequiredReason: {APP_UPDATE: "app_update"},
        PlatformArch: {X86_64: "x86_64"},
        PlatformNaclArch: {X86_64: "x86_64"},
        PlatformOs: {MAC: "mac", WIN: "win", LINUX: "linux"},
        RequestUpdateCheckStatus: {NO_UPDATE: "no_update", THROTTLED: "throttled", UPDATE_AVAILABLE: "update_available"}
      }),
      configurable: true
    });
  }
  
  // ===== 2. 硬件指纹伪装 =====
  Object.defineProperty(navigator, 'deviceMemory', {
    get: () => 8,  // 8GB内存
    configurable: true
  });
  
  Object.defineProperty(navigator, 'hardwareConcurrency', {
    get: () => 8,  // 8核CPU
    configurable: true
  });
  
  // ===== 3. 语言和地区伪装 =====
  Object.defineProperty(navigator, 'languages', {
    get: () => ['en-GB', 'en-US', 'en'],
    configurable: true
  });
  
  Object.defineProperty(navigator, 'language', {
    get: () => 'en-GB',
    configurable: true
  });
  
  // ===== 4. 平台伪装 (MacIntel或Win32) =====
  Object.defineProperty(navigator, 'platform', {
    get: () => 'MacIntel',
    configurable: true
  });
  
  Object.defineProperty(navigator, 'vendor', {
    get: () => 'Google Inc.',
    configurable: true
  });
  
  Object.defineProperty(navigator, 'product', {
    get: () => 'Gecko',
    configurable: true
  });
  
  Object.defineProperty(navigator, 'productSub', {
    get: () => '20030107',
    configurable: true
  });
  
  // ===== 5. 插件列表伪装 =====
  const fakePlugins = [
    {
      name: 'Chrome PDF Plugin',
      filename: 'internal-pdf-viewer',
      description: 'Portable Document Format',
      version: 'undefined',
      length: 1,
      item: () => null,
      namedItem: () => null
    },
    {
      name: 'Native Client',
      filename: 'native-client.nmf',
      description: '',
      version: 'undefined',
      length: 2,
      item: () => null,
      namedItem: () => null
    },
    {
      name: 'Widevine Content Decryption Module',
      filename: 'widevinecdmadapter.dll',
      description: 'Widevine Content Decryption Module',
      version: 'undefined',
      length: 0,
      item: () => null,
      namedItem: () => null
    }
  ];
  
  Object.defineProperty(navigator, 'plugins', {
    get: () => {
      const plugins = [...fakePlugins];
      plugins.length = fakePlugins.length;
      plugins.item = (idx) => plugins[idx];
      plugins.namedItem = (name) => plugins.find(p => p.name === name);
      return plugins;
    },
    configurable: true
  });
  
  // ===== 6. MIME类型伪装 =====
  const fakeMimeTypes = [
    { type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format', enabledPlugin: fakePlugins[0] },
    { type: 'application/x-google-chrome-pdf', suffixes: 'pdf', description: 'Portable Document Format', enabledPlugin: fakePlugins[0] },
    { type: 'application/x-nacl', suffixes: '', description: 'Native Client executable', enabledPlugin: fakePlugins[1] },
    { type: 'application/x-pnacl', suffixes: '', description: 'Portable Native Client executable', enabledPlugin: fakePlugins[1] }
  ];
  
  Object.defineProperty(navigator, 'mimeTypes', {
    get: () => {
      const mimeTypes = [...fakeMimeTypes];
      mimeTypes.length = fakeMimeTypes.length;
      mimeTypes.item = (idx) => mimeTypes[idx];
      mimeTypes.namedItem = (name) => mimeTypes.find(m => m.type === name);
      return mimeTypes;
    },
    configurable: true
  });
  
  // ===== 7. 屏幕参数伪装 =====
  Object.defineProperty(screen, 'colorDepth', {
    get: () => 30,  // Retina显示
    configurable: true
  });
  
  Object.defineProperty(screen, 'pixelDepth', {
    get: () => 30,
    configurable: true
  });
  
  // ===== 8. Canvas指纹噪声 (基础版) =====
  const originalGetContext = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function(type) {
    const context = originalGetContext.apply(this, arguments);
    if (context && type === '2d') {
      // 添加微小噪声到getImageData
      const originalGetImageData = context.getImageData;
      context.getImageData = function() {
        const imageData = originalGetImageData.apply(this, arguments);
        // 添加1-2像素的随机噪声
        for (let i = 0; i < imageData.data.length; i += 4) {
          if (Math.random() > 0.95) {
            imageData.data[i] = Math.max(0, Math.min(255, imageData.data[i] + (Math.random() > 0.5 ? 1 : -1)));
          }
        }
        return imageData;
      };
    }
    return context;
  };
  
  // ===== 9. WebGL指纹伪装 =====
  const getParameterProxyHandler = {
    apply: function(target, thisArg, args) {
      const param = args[0];
      // 伪装UNMASKED_VENDOR和UNMASKED_RENDERER
      if (param === 37445) return 'Intel Inc.';  // UNMASKED_VENDOR
      if (param === 37446) return 'Intel Iris OpenGL Engine';  // UNMASKED_RENDERER
      return target.apply(thisArg, args);
    }
  };
  
  const originalGetContextWebGL = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function(type) {
    const context = originalGetContextWebGL.apply(this, arguments);
    if (context && (type === 'webgl' || type === 'experimental-webgl')) {
      const originalGetParameter = context.getParameter;
      context.getParameter = new Proxy(originalGetParameter, getParameterProxyHandler);
    }
    return context;
  };
  
  // ===== 10. Notification权限伪装 =====
  if (window.Notification) {
    Object.defineProperty(Notification, 'permission', {
      get: () => 'default',
      configurable: true
    });
  }
  
  // ===== 11. 权限API伪装 =====
  if (navigator.permissions) {
    const originalQuery = navigator.permissions.query;
    navigator.permissions.query = async function(parameters) {
      if (parameters.name === 'notifications') {
        return { state: 'prompt', onchange: null };
      }
      return originalQuery.apply(this, arguments);
    };
  }
  
  console.log('[TITAN STEALTH] 指纹加固完成 - 幽灵模式已激活');
})();
`;

/**
 * 创建加固的浏览器上下文
 * 地理坐标对齐Europe/London
 * 
 * @param {Object} browser - Playwright浏览器实例
 * @returns {Object} 加固后的浏览器上下文
 */
async function createHardenedContext(browser) {
  const context = await browser.newContext({
    // 视口设置 - 模拟常见分辨率
    viewport: { width: 1920, height: 1080 },
    
    // 设备缩放 - 模拟Retina
    deviceScaleFactor: 2,
    
    // 用户代理 - 最新Chrome
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    
    // 地理位置对齐 - 伦敦
    locale: 'en-GB',
    timezoneId: 'Europe/London',
    geolocation: { latitude: 51.5074, longitude: -0.1278 },  // 伦敦市中心
    permissions: ['geolocation'],
    
    // 颜色主题
    colorScheme: 'light',
    
    // 额外HTTP头
    extraHTTPHeaders: {
      'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
      'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
      'Sec-Ch-Ua-Mobile': '?0',
      'Sec-Ch-Ua-Platform': '"macOS"',
      'Sec-Fetch-Dest': 'document',
      'Sec-Fetch-Mode': 'navigate',
      'Sec-Fetch-Site': 'none',
      'Sec-Fetch-User': '?1',
      'Upgrade-Insecure-Requests': '1'
    }
  });
  
  // 注入指纹掩码脚本 - 在所有页面创建前
  await context.addInitScript(FINGERPRINT_MASK_SCRIPT);
  
  console.log('[STEALTH HARDENING] 加固上下文已创建 - 坐标: London, 时区: Europe/London');
  
  return context;
}

/**
 * 增强型拟人化交互 - 含视线抖动和犹豫行为
 * @param {Object} page - Playwright页面对象
 */
async function executeHardenedMimicSequence(page) {
  // 1. 初始视线扫描 - 贝塞尔曲线移动
  await bezierMouseMovement(page, 3 + Math.floor(Math.random() * 3));
  
  // 2. 视线抖动 - 微小随机滚动
  console.log('   [HARDENING] 执行视线抖动...');
  for (let i = 0; i < 3; i++) {
    const jitterAmount = 20 + Math.floor(Math.random() * 80);  // 20-100像素
    await page.mouse.wheel(0, Math.random() > 0.5 ? jitterAmount : -jitterAmount);
    await page.waitForTimeout(300 + Math.random() * 400);
  }
  
  // 3. 非交互区域随机点击 - 犹豫行为
  console.log('   [HARDENING] 执行犹豫点击...');
  const viewport = await page.viewportSize();
  for (let i = 0; i < 2; i++) {
    const clickX = Math.floor(Math.random() * (viewport?.width || 1920) * 0.7) + 100;
    const clickY = Math.floor(Math.random() * (viewport?.height || 1080) * 0.7) + 100;
    
    // 鼠标移动到目标但不立即点击 - 徘徊
    await page.mouse.move(clickX, clickY);
    await page.waitForTimeout(800 + Math.random() * 1200);  // 0.8-2秒徘徊
    
    // 随机决定是否点击（犹豫）
    if (Math.random() > 0.3) {
      await page.mouse.click(clickX, clickY);
      console.log(`      🖱️  犹豫后点击: (${clickX}, ${clickY})`);
    } else {
      console.log(`      🤔 徘徊后放弃点击: (${clickX}, ${clickY})`);
    }
    
    await page.waitForTimeout(500 + Math.random() * 1000);
  }
  
  // 4. 正常滚动
  await humanLikeScrolling(page, 2 + Math.floor(Math.random() * 3));
  
  // 5. 查找并模拟Bet365赔率悬停
  console.log('   [HARDENING] 查找Bet365赔率...');
  try {
    const bet365Elements = await page.locator('text=Bet365').all();
    if (bet365Elements.length > 0) {
      console.log(`      发现 ${bet365Elements.length} 个Bet365元素`);
      
      // 悬停但不点击 - 观察行为
      await bet365Elements[0].hover();
      console.log('      👁️  悬停观察Bet365 (2-4秒)...');
      await page.waitForTimeout(2000 + Math.random() * 2000);
      
      // 查找相邻的赔率数字
      const oddsNearby = await page.locator('text=/\\d+\\.\\d{2}/').locator('xpath=..').all();
      if (oddsNearby.length > 0) {
        await oddsNearby[0].hover();
        console.log('      👁️  悬停观察赔率数值...');
        await page.waitForTimeout(1500 + Math.random() * 1500);
        
        // 轻微点击赔率区域触发数据加载
        await oddsNearby[0].click({ force: true, delay: 100 + Math.random() * 200 });
        console.log('      🖱️  轻微点击赔率区域');
      }
    }
  } catch (e) {
    console.log(`      ⚠️ Bet365交互失败: ${e.message}`);
  }
  
  console.log('   [HARDENING] ✅ 加固交互序列完成');
}

/**
 * V6.0 FORCE-CLICK-RECOVERY: 精准点穴与诱导式数据拦截
 * 专门针对Bet365赔率行进行精准点击，强制诱导数据包发出
 * 
 * @param {Object} page - Playwright页面对象
 */
async function executePrecisionAcupuncture(page) {
  console.log('   [ACUPUNCTURE] 🎯 启动精准点穴协议...');
  
  try {
    // 步骤1: 定位Bet365行 - 多种选择器尝试
    let bet365Row = null;
    const selectors = [
      'tr:has-text("Bet365")',
      'tr:has(td:has-text("Bet365"))',
      '[data-bookmaker="Bet365"]',
      '.bookmaker-row:has-text("Bet365")',
      'tr[data-provider="16"]',
      'tr:has(.bookmaker:has-text("Bet365"))'
    ];
    
    for (const selector of selectors) {
      try {
        const row = await page.locator(selector).first();
        if (await row.isVisible().catch(() => false)) {
          bet365Row = row;
          console.log(`      ✅ 定位Bet365行: ${selector}`);
          break;
        }
      } catch (e) {
        continue;
      }
    }
    
    if (!bet365Row) {
      console.log('      ⚠️ 未找到Bet365行，尝试通用赔率行...');
      // 尝试找任何包含odds类的行
      bet365Row = await page.locator('tr:has(td.odds)').first();
    }
    
    if (!bet365Row) {
      console.log('      ❌ 无法定位任何赔率行');
      return;
    }
    
    // 步骤2: 在Bet365行内寻找赔率单元格
    console.log('      🔍 寻找赔率单元格...');
    const oddsSelectors = [
      'td.odds',
      'td .odds-now',
      'td:has-text(".")',  // 简化选择器
      '.odds-cell',
      '[data-odds]',
      'td:nth-child(n+2)'
    ];
    
    let oddsCells = [];
    for (const selector of oddsSelectors) {
      try {
        const cells = await bet365Row.locator(selector).all();
        if (cells.length >= 3) {  // 至少需要3个赔率单元格(主/平/客)
          oddsCells = cells;
          console.log(`      ✅ 找到 ${cells.length} 个赔率单元格: ${selector}`);
          break;
        }
      } catch (e) {
        continue;
      }
    }
    
    if (oddsCells.length === 0) {
      console.log('      ⚠️ 未找到标准赔率单元格，尝试直接点击行');
      oddsCells = [bet365Row];
    }
    
    // 步骤3: 诱导点击 - 按顺序点击赔率单元格
    console.log('      🖱️  执行诱导点击序列...');
    for (let i = 0; i < Math.min(oddsCells.length, 3); i++) {
      const cell = oddsCells[i];
      
      // 先悬停
      await cell.hover();
      console.log(`      👁️  悬停单元格 ${i + 1}/${Math.min(oddsCells.length, 3)}`);
      await page.waitForTimeout(500 + Math.random() * 500);
      
      // 强制点击（带延迟模拟人类）
      await cell.click({ 
        force: true, 
        delay: 150,
        button: 'left'
      });
      console.log(`      🖱️  点穴点击单元格 ${i + 1}`);
      
      // 点击后短暂等待
      await page.waitForTimeout(800 + Math.random() * 400);
    }
    
    // 步骤4: 震荡观察期 - 模拟人类看弹出轨迹图
    console.log('      ⏱️  进入震荡观察期 (3秒)...');
    await page.waitForTimeout(3000);
    
    // 微小滚动 - 模拟观察轨迹图时的滚动
    for (let i = 0; i < 3; i++) {
      const wheelAmount = 30 + Math.floor(Math.random() * 50);  // 微小滚动
      await page.mouse.wheel(0, Math.random() > 0.5 ? wheelAmount : -wheelAmount);
      console.log(`      🔄 微小滚动 ${i + 1}/3`);
      await page.waitForTimeout(600 + Math.random() * 400);
    }
    
    // 步骤5: 二次诱导 - 再次点击第一个单元格
    if (oddsCells.length > 0) {
      console.log('      🖱️  二次诱导点击...');
      await oddsCells[0].click({ force: true, delay: 100 });
      await page.waitForTimeout(1000);
    }
    
    console.log('   [ACUPUNCTURE] ✅ 精准点穴完成 - 数据包应该已被触发');
    
  } catch (e) {
    console.log(`   [ACUPUNCTURE] ⚠️ 点穴过程出错: ${e.message}`);
  }
}

// ===================================================================
// V6.0 VISION-HEALING: 自动失明监测与视觉康复
// ===================================================================

const STATUS_HEALTHY = 'HEALTHY';
const STATUS_BLIND = 'BLIND';
const STATUS_RECOVERING = 'RECOVERING';

/**
 * 自动失明监测 - 检查页面健康状态
 * @param {Object} page - Playwright页面对象
 * @returns {Object} { status: 'HEALTHY'|'BLIND', details: {} }
 */
async function checkPageHealth(page) {
  const healthCheck = await page.evaluate(() => {
    const bodyText = document.body.innerText || '';
    const textLength = bodyText.length;
    
    // 检查是否包含赔率数字 (如 1.50, 4.33, 7.50)
    const oddsPattern = /\d+\.\d{2}/;
    const hasOdds = oddsPattern.test(bodyText);
    
    // 检查关键元素
    const hasBookmakers = /bookmaker|pinnacle|bet365/i.test(bodyText);
    const hasOddsTable = document.querySelector('table, .odds-table, [class*="odds"]') !== null;
    
    return {
      textLength,
      hasOdds,
      hasBookmakers,
      hasOddsTable,
      sampleText: bodyText.substring(0, 200)
    };
  });
  
  // 判定标准: 文本长度<1000 且 无赔率数字 = 失明
  const isBlind = healthCheck.textLength < 1000 || !healthCheck.hasOdds;
  
  return {
    status: isBlind ? STATUS_BLIND : STATUS_HEALTHY,
    details: healthCheck
  };
}

/**
 * 视觉康复三部曲 - 强制唤醒页面渲染
 * @param {Object} page - Playwright页面对象
 * @param {Object} context - Playwright上下文对象
 * @param {Object} sessionData - 黄金会话数据
 * @returns {Object} { success: boolean, attempts: number }
 */
async function healVision(page, context, sessionData) {
  console.log('   🏥 [VISION-HEALING] 启动视觉康复协议...');
  
  const maxAttempts = 3;
  
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    console.log(`   🔄 康复尝试 ${attempt}/${maxAttempts}`);
    
    try {
      // A. 深度清理 - 清除Cookie并重新注入黄金Session
      if (context) {
        await context.clearCookies();
        console.log('      🧹 深度清理: Cookie已清除');
        
        if (sessionData && sessionData.cookies) {
          await context.addCookies(sessionData.cookies);
          console.log('      💉 黄金Session已重新注入');
        }
      }
      
      // B. 强制重启 - 随机延迟后reload
      const delay = 2000 + Math.floor(Math.random() * 3000); // 2-5秒
      console.log(`      ⏱️  随机延迟 ${delay}ms...`);
      await page.waitForTimeout(delay);
      
      await page.reload({ 
        waitUntil: 'load', 
        timeout: 60000 
      });
      console.log('      🔄 页面已强制重启');
      
      // C. 拟人震荡 - 快速随机滚动和点击
      const quickScrollAmount = 500 + Math.floor(Math.random() * 1000); // 500-1500像素
      await page.mouse.wheel(0, quickScrollAmount);
      await page.waitForTimeout(500);
      
      // 点击页面空白处 (随机位置)
      const viewport = page.viewportSize();
      const clickX = Math.floor(Math.random() * (viewport?.width || 1920) * 0.8) + 50;
      const clickY = Math.floor(Math.random() * (viewport?.height || 1080) * 0.8) + 50;
      await page.mouse.click(clickX, clickY);
      console.log(`      🖱️  拟人震荡: 滚动${quickScrollAmount}px + 点击(${clickX},${clickY})`);
      
      // 等待页面稳定
      await page.waitForTimeout(2000);
      
      // 检查康复效果
      const health = await checkPageHealth(page);
      if (health.status === STATUS_HEALTHY) {
        console.log('   ✅ [VISION-HEALING] 视觉康复成功！');
        return { success: true, attempts: attempt };
      }
      
    } catch (e) {
      console.log(`      ⚠️  康复尝试 ${attempt} 失败: ${e.message}`);
    }
  }
  
  console.log('   ❌ [VISION-HEALING] 视觉康复失败，已达最大尝试次数');
  return { success: false, attempts: maxAttempts };
}

/**
 * 静默收割循环 - 无人值守自动收割
 * @param {Object} page - Playwright页面对象
 * @param {Object} context - Playwright上下文对象
 * @param {Object} sessionData - 黄金会话数据
 * @param {Object} parser - OddsPortalParser模块
 * @returns {Object} { success: boolean, data: {}, healingTriggered: boolean }
 */
async function silentHarvestLoop(page, context, sessionData, parser) {
  console.log('   🤖 [SILENT LOOP] 启动静默收割...');
  
  // 1. 检查页面健康
  const health = await checkPageHealth(page);
  console.log(`      页面状态: ${health.status} (文本长度: ${health.details.textLength})`);
  
  let healingTriggered = false;
  
  // 2. 如果失明，执行视觉康复
  if (health.status === STATUS_BLIND) {
    healingTriggered = true;
    const healing = await healVision(page, context, sessionData);
    if (!healing.success) {
      console.log('      ❌ 视觉康复失败，跳过本次收割');
      return { success: false, data: null, healingTriggered };
    }
  }
  
  // 3. 执行拟人化交互
  await executeHumanMimicSequence(page);
  
  // 4. 尝试提取数据
  const domResult = await parser.extractOddsFromDOM(page);
  
  // 5. 构建市场情感数据
  const marketSentiment = parser.buildMarketSentiment(null, domResult);
  
  // 6. 验证数据完整性
  const hasValidData = (marketSentiment.pinnacle_odds && marketSentiment.pinnacle_odds.closing && marketSentiment.pinnacle_odds.closing.length === 3) ||
                       (marketSentiment.bet365_odds && marketSentiment.bet365_odds.closing && marketSentiment.bet365_odds.closing.length === 3);
  
  if (hasValidData) {
    console.log('      ✅ 静默收割成功，获取有效数据');
    return { success: true, data: marketSentiment, healingTriggered };
  } else {
    console.log('      ❌ 数据提取失败，pinnacle_odds 或 bet365_odds 为空');
    return { success: false, data: null, healingTriggered };
  }
}

// ===================================================================
// V6.0 JSON SNIFFER: 内存级JSON拦截器
// ===================================================================

/**
 * 注入JSON Sniffer钩子
 * 重写window.JSON.parse以捕获解密后的明文数据
 * 
 * @param {Object} page - Playwright页面对象
 * @param {Function} emitFunction - 数据回调函数 (通过page.exposeFunction暴露)
 */
async function injectJsonSniffer(page, emitFunction) {
  // 通过exposeFunction暴露Node.js回调到浏览器环境
  await page.exposeFunction('__titan_emit_data', (data) => {
    if (emitFunction) {
      emitFunction(data);
    }
  });

  // 注入Sniffer脚本
  await page.addInitScript(() => {
    // 保存原始JSON.parse
    const originalParse = window.JSON.parse;
    let _isParsing = false; // 防止递归标志

    // 特征Key列表
    const TARGET_KEYS = ['userData', 'bookiehash', 'oddsdata', 'myBookmakers'];

    /**
     * 判断是否为赔率数据
     */
    function isOddsData(obj) {
      if (!obj || typeof obj !== 'object') return false;
      const keys = Object.keys(obj);
      return TARGET_KEYS.some(key => keys.includes(key));
    }

    /**
     * 克隆对象（深拷贝）
     */
    function deepClone(obj) {
      try {
        return JSON.parse(JSON.stringify(obj));
      } catch (e) {
        return obj;
      }
    }

    // 重写JSON.parse
    window.JSON.parse = function(text, reviver) {
      // 防止递归
      if (_isParsing) {
        return originalParse.call(window.JSON, text, reviver);
      }

      _isParsing = true;
      let parsed;
      try {
        parsed = originalParse.call(window.JSON, text, reviver);
      } finally {
        _isParsing = false;
      }

      // 特征识别：检查是否为赔率数据
      if (isOddsData(parsed)) {
        // 克隆数据
        const cloned = deepClone(parsed);
        
        // 提取关键信息
        const extracted = {
          timestamp: Date.now(),
          keys: Object.keys(parsed),
          hasOddsData: !!parsed.oddsdata,
          hasUserData: !!parsed.userData,
          data: cloned
        };

        // 发送到Node.js环境
        if (window.__titan_emit_data) {
          window.__titan_emit_data(extracted);
        }

        // 同时触发DOM事件（备用方案）
        const event = new CustomEvent('titan_data_captured', { detail: extracted });
        document.dispatchEvent(event);
      }

      return parsed;
    };

    // 标记Sniffer已注入
    window.__titan_sniffer_injected = true;
  });

  console.log('   🕸️  [JSON SNIFFER] 内存拦截器已注入');
}

/**
 * 创建Sniffer数据接收器
 * 返回Promise，等待Sniffer捕获数据
 * 
 * @param {Object} page - Playwright页面对象
 * @param {number} timeout - 超时时间（毫秒）
 * @returns {Promise<Object>} 捕获的数据
 */
async function waitForSnifferData(page, timeout = 15000) {
  return new Promise((resolve, reject) => {
    let capturedData = null;
    const timer = setTimeout(() => {
      if (capturedData) {
        resolve(capturedData);
      } else {
        reject(new Error('Sniffer timeout'));
      }
    }, timeout);

    // 通过exposeFunction接收数据
    page.exposeFunction('__titan_sniffer_callback', (data) => {
      capturedData = data;
      clearTimeout(timer);
      
      // 打印捕获信息
      if (data.hasOddsData) {
        const bet365History = data.data?.oddsdata?.bet365?.history;
        const pinnacleHistory = data.data?.oddsdata?.pinnacle?.history;
        const count = (bet365History?.length || 0) + (pinnacleHistory?.length || 0);
        console.log(`   💎 [SNIFFER-HIT] 捕获到 Bet365 明文数据，包含 ${count} 个变盘节点。`);
      }
      
      resolve(data);
    }).catch(() => {
      // exposeFunction只能调用一次，忽略重复调用错误
    });
  });
}

/**
 * 解析Sniffer数据为MarketSentiment格式
 * 
 * @param {Object} snifferData - Sniffer捕获的原始数据
 * @returns {Object} marketSentiment结构
 */
function parseSnifferDataToMarketSentiment(snifferData) {
  if (!snifferData || !snifferData.data) {
    return null;
  }

  const rawData = snifferData.data;
  const ms = {
    extract_method: 'JSON_SNIFFER_INTERCEPT_V6.0',
    extract_timestamp: new Date(snifferData.timestamp).toISOString(),
    source: 'memory_sniffer',
    _sniffer: true,
    _timestamp: snifferData.timestamp,
    pinnacle_odds: null,
    bet365_odds: null
  };

  // 解析oddsdata
  if (rawData.oddsdata) {
    const oddsData = rawData.oddsdata;

    // Bet365
    if (oddsData.bet365) {
      const b365 = oddsData.bet365;
      const history = b365.history || [];
      
      ms.bet365_odds = {
        detected: true,
        bookmaker_id: 16,
        history: history.map(h => ({ ts: h.t, o: h.o })),
        _point_count: history.length,
        _is_premium: history.length >= 3
      };

      // 如果有历史数据，设置opening/closing
      if (history.length > 0) {
        ms.bet365_odds.opening = history[0].o;
        ms.bet365_odds.closing = history[history.length - 1].o;
        ms.bet365_odds.opening_at = history[0].t;
        ms.bet365_odds.odds_last_changed_at = history[history.length - 1].t;
      }
    }

    // Pinnacle
    if (oddsData.pinnacle) {
      const pin = oddsData.pinnacle;
      const history = pin.history || [];
      
      ms.pinnacle_odds = {
        detected: true,
        bookmaker_id: 27,
        history: history.map(h => ({ ts: h.t || h.ts, o: h.o || h.price })),
        _point_count: history.length,
        _is_premium: history.length >= 3
      };

      if (history.length > 0) {
        ms.pinnacle_odds.opening = history[0].o || history[0].price;
        ms.pinnacle_odds.closing = history[history.length - 1].o || history[history.length - 1].price;
        ms.pinnacle_odds.opening_at = history[0].t || history[0].ts;
        ms.pinnacle_odds.odds_last_changed_at = history[history.length - 1].t || history[history.length - 1].ts;
      }
    }
  }

  // 标记是否为PREMIUM数据
  const bet365Points = ms.bet365_odds?._point_count || 0;
  const pinnaclePoints = ms.pinnacle_odds?._point_count || 0;
  ms._is_premium_data = (bet365Points >= 3) || (pinnaclePoints >= 3);
  ms._total_points = bet365Points + pinnaclePoints;

  return ms;
}

module.exports = {
  // 原有导出
  bezierMouseMovement,
  humanLikeScrolling,
  contextSwitchManeuver,
  visionRecoveryCheck,
  executeHumanMimicSequence,
  
  // V6.0 STEALTH HARDENING 新增
  createHardenedContext,
  executeHardenedMimicSequence,
  executePrecisionAcupuncture,  // FORCE-CLICK-RECOVERY
  FINGERPRINT_MASK_SCRIPT,
  
  // V6.0 VISION-HEALING
  checkPageHealth,
  healVision,
  silentHarvestLoop,
  STATUS_HEALTHY,
  STATUS_BLIND,
  STATUS_RECOVERING,
  
  // V6.0 JSON SNIFFER 新增
  injectJsonSniffer,
  waitForSnifferData,
  parseSnifferDataToMarketSentiment,
  
  // V6.0 OMNI SNIFFER 新增 (WebSocket/Fetch/XHR三位一体)
  injectOmniSniffer,
  waitForGoldenStream
};

// ============================================================================
// V6.0 OMNI SNIFFER: WebSocket + Fetch + XHR 三位一体全维度嗅探
// ============================================================================

/**
 * 全维度内存数据劫持 - 三频段拦截器
 * @param {Object} page - Playwright页面对象
 * @param {Object} snifferState - 状态存储对象
 */
async function injectOmniSniffer(page, snifferState) {
  // 初始化统计
  snifferState.stats = { ws: 0, fetch: 0, xhr: 0, golden: 0 };
  snifferState.goldenStreams = [];
  snifferState.hasConfig = false;
  snifferState.hasOddsStream = false;
  snifferState.ready = false;

  // 暴露回调到Node.js
  await page.exposeFunction('__titan_emit_stream', (stream) => {
    if (stream.type === 'CONFIG_JSON') {
      snifferState.hasConfig = true;
      snifferState.configData = stream.data;
    }
    if (stream.type === 'GOLDEN_STREAM') {
      snifferState.goldenHits = (snifferState.goldenHits || 0) + 1;
      snifferState.goldenStreams.push(stream);
      snifferState.hasOddsStream = true;
    }
    if (snifferState.hasConfig && snifferState.hasOddsStream) {
      snifferState.ready = true;
    }
  });

  // 注入浏览器端拦截器 (带信号提纯)
  await page.addInitScript(() => {
    // ===== 信号提纯配置 =====
    const PURITY_CONFIG = {
      ALLOWED_DOMAINS: ['oddsportal.com/ajax-user-data/','oddsportal.com/ajax/','oddsportal.com/feed/','oddsportal.com/api/'],
      BLOCKED_DOMAINS: ['cookielaw.org','onetrust.com','googletagmanager.com','google-analytics.com','facebook.com','doubleclick.net'],
      ODDS_MIN: 1.01, ODDS_MAX: 99.99
    };
    window.__titan_purity_stats = { totalChecked: 0, passed: 0, blockedByDomain: 0, blockedByValue: 0 };
    
    function isAllowedDomain(url) {
      if (!url) return false;
      for (const blocked of PURITY_CONFIG.BLOCKED_DOMAINS) if (url.includes(blocked)) return false;
      for (const allowed of PURITY_CONFIG.ALLOWED_DOMAINS) if (url.includes(allowed)) return true;
      return false;
    }
    function isValidOddsRange(odds) {
      if (!Array.isArray(odds) || odds.length < 3) return false;
      return odds.every(n => { const num = parseFloat(n); return !isNaN(num) && num >= PURITY_CONFIG.ODDS_MIN && num <= PURITY_CONFIG.ODDS_MAX; });
    }
    function extractOdds(text) {
      const pattern = /(\d+\.\d{2})[^\d.]{0,20}(\d+\.\d{2})[^\d.]{0,20}(\d+\.\d{2})/;
      const match = text.match(pattern);
      if (match) return [parseFloat(match[1]), parseFloat(match[2]), parseFloat(match[3])];
      return null;
    }
    function purityFilter(url, text) {
      window.__titan_purity_stats.totalChecked++;
      if (!isAllowedDomain(url)) { window.__titan_purity_stats.blockedByDomain++; return { isGolden: false, reason: 'BLOCKED_DOMAIN' }; }
      const odds = extractOdds(text);
      if (!odds) return { isGolden: false, reason: 'NO_ODDS_PATTERN' };
      if (!isValidOddsRange(odds)) { window.__titan_purity_stats.blockedByValue++; return { isGolden: false, reason: 'INVALID_ODDS_RANGE', odds }; }
      window.__titan_purity_stats.passed++;
      return { isGolden: true, reason: 'PASSED', odds };
    }
    function getPurityScore() {
      const s = window.__titan_purity_stats;
      if (s.totalChecked === 0) return 100;
      return Math.max(0, Math.round(100 - ((s.blockedByDomain + s.blockedByValue) / s.totalChecked * 100)));
    }

    const TARGET_KEYS = ['userData', 'bookiehash', 'oddsdata'];
    
    // WebSocket拦截
    const OriginalWebSocket = window.WebSocket;
    window.WebSocket = function(url, protocols) {
      const ws = new OriginalWebSocket(url, protocols);
      ws.addEventListener('message', (event) => {
        const text = typeof event.data === 'string' ? event.data : '';
        const result = purityFilter(url, text);
        if (result.isGolden || result.reason === 'INVALID_ODDS_RANGE') {
          window.__titan_emit_stream({ channel: 'websocket', url, type: result.isGolden ? 'GOLDEN_STREAM' : 'ODDS_RELATED', timestamp: Date.now(), sample: text.substring(0, 300), odds: result.odds, purity: getPurityScore() });
        }
      });
      return ws;
    };
    Object.setPrototypeOf(window.WebSocket, OriginalWebSocket);
    window.WebSocket.prototype = OriginalWebSocket.prototype;

    // Fetch拦截
    const originalFetch = window.fetch;
    window.fetch = async function(url, options) {
      const response = await originalFetch.apply(this, arguments);
      try {
        const cloned = response.clone();
        const text = await cloned.text();
        const result = purityFilter(url, text);
        
        let isConfig = false;
        try {
          const json = JSON.parse(text);
          isConfig = TARGET_KEYS.some(key => json.hasOwnProperty(key));
          if (isConfig) window.__titan_emit_stream({ channel: 'fetch', url, type: 'CONFIG_JSON', keys: Object.keys(json), purity: getPurityScore() });
        } catch (e) {}
        
        if (!isConfig && (result.isGolden || result.reason === 'INVALID_ODDS_RANGE')) {
          window.__titan_emit_stream({ channel: 'fetch', url, type: result.isGolden ? 'GOLDEN_STREAM' : 'ODDS_RELATED', sample: text.substring(0, 300), odds: result.odds, purity: getPurityScore() });
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
            const result = purityFilter(xhr.responseURL, text);
            
            try {
              const json = JSON.parse(text);
              if (TARGET_KEYS.some(key => json.hasOwnProperty(key))) {
                window.__titan_emit_stream({ channel: 'xhr', url: xhr.responseURL, type: 'CONFIG_JSON', keys: Object.keys(json), purity: getPurityScore() });
                return;
              }
            } catch (e) {}
            
            if (result.isGolden || result.reason === 'INVALID_ODDS_RANGE') {
              window.__titan_emit_stream({ channel: 'xhr', url: xhr.responseURL, type: result.isGolden ? 'GOLDEN_STREAM' : 'ODDS_RELATED', sample: text.substring(0, 300), odds: result.odds, purity: getPurityScore() });
            }
          }
        };
        xhr.addEventListener('load', onReady);
        return originalSend.apply(xhr, arguments);
      };
      return xhr;
    };
    Object.setPrototypeOf(window.XMLHttpRequest, OriginalXHR);
    window.XMLHttpRequest.prototype = OriginalXHR.prototype;

    window.__titan_omni_sniffer_injected = true;
    console.log('[TITAN OMNI SNIFFER] 信号提纯版已注入 - 域名白名单+数值围栏');
  });
}

/**
 * 等待Golden Stream拼图集齐
 * @param {Object} snifferState - 状态对象
 * @param {number} maxWaitMs - 最大等待时间
 * @returns {Object} { ready: boolean }
 */
async function waitForGoldenStream(snifferState, maxWaitMs = 30000) {
  const startTime = Date.now();
  const checkInterval = 500;
  
  while (Date.now() - startTime < maxWaitMs) {
    if (snifferState.ready) return { ready: true, elapsed: Date.now() - startTime };
    await new Promise(resolve => setTimeout(resolve, checkInterval));
  }
  
  return { ready: false, elapsed: Date.now() - startTime };
}
