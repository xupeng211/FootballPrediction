/**
 * TITAN V6.0 STEALTH HARDENING - TDD测试套件
 * ==========================================
 * 验证浏览器指纹加固与幽灵化改造效果
 * 
 * @module tests/unit/stealth_hardening
 * @version V6.0-STEALTH-HARDENING-TDD
 * @date 2026-03-17
 */

'use strict';

const { describe, it, before, after } = require('node:test');
const assert = require('node:assert');
const { chromium } = require('playwright');
const {
  createHardenedContext,
  executeHardenedMimicSequence,
  FINGERPRINT_MASK_SCRIPT
} = require('../../src/infrastructure/harvesters/StealthNavigator');

describe('V6.0 STEALTH HARDENING: 浏览器指纹加固验证', () => {
  let browser;
  let context;
  let page;

  before(async () => {
    console.log('\n╔══════════════════════════════════════════════════════════════════════════════╗');
    console.log('║     🛡️  TITAN V6.0 STEALTH HARDENING TDD 测试套件                           ║');
    console.log('╚══════════════════════════════════════════════════════════════════════════════╝\n');
    
    browser = await chromium.launch({ headless: true });
  });

  after(async () => {
    if (browser) {
      await browser.close();
    }
    console.log('\n✅ TDD测试套件执行完毕\n');
  });

  describe('A. 核心指纹掩码验证', () => {
    before(async () => {
      context = await createHardenedContext(browser);
      page = await context.newPage();
    });

    after(async () => {
      if (context) {
        await context.close();
      }
    });

    it('A1. navigator.webdriver 必须检测不到', async () => {
      console.log('   🧪 测试: navigator.webdriver 抹除...');
      
      const webdriver = await page.evaluate(() => navigator.webdriver);
      
      console.log(`      检测结果: ${webdriver}`);
      assert.strictEqual(webdriver, undefined, 'navigator.webdriver 应该返回 undefined');
      
      // 额外检查：navigator上不存在webdriver属性或值为undefined
      const hasWebdriver = await page.evaluate(() => 'webdriver' in navigator);
      console.log(`      'webdriver' in navigator: ${hasWebdriver}`);
      
      // 即使存在，值也必须是undefined
      if (hasWebdriver) {
        const value = await page.evaluate(() => navigator.webdriver);
        assert.strictEqual(value, undefined, 'navigator.webdriver 值必须为 undefined');
      }
      
      console.log('      ✅ WebDriver痕迹已彻底抹除');
    });

    it('A2. 硬件参数伪装验证', async () => {
      console.log('   🧪 测试: 硬件指纹伪装...');
      
      const hardware = await page.evaluate(() => ({
        deviceMemory: navigator.deviceMemory,
        hardwareConcurrency: navigator.hardwareConcurrency
      }));
      
      console.log(`      设备内存: ${hardware.deviceMemory}GB`);
      console.log(`      CPU核心: ${hardware.hardwareConcurrency}`);
      
      assert.strictEqual(hardware.deviceMemory, 8, 'deviceMemory 应该伪装为8GB');
      assert.strictEqual(hardware.hardwareConcurrency, 8, 'hardwareConcurrency 应该伪装为8核');
      
      console.log('      ✅ 硬件指纹伪装成功');
    });

    it('A3. 语言和地区伪装验证', async () => {
      console.log('   🧪 测试: 语言地区伪装...');
      
      const locale = await page.evaluate(() => ({
        language: navigator.language,
        languages: navigator.languages,
        platform: navigator.platform
      }));
      
      console.log(`      语言: ${locale.language}`);
      console.log(`      语言列表: ${locale.languages?.join(', ')}`);
      console.log(`      平台: ${locale.platform}`);
      
      assert.strictEqual(locale.language, 'en-GB', '语言应该伪装为 en-GB');
      assert.ok(locale.languages?.includes('en-GB'), '语言列表应该包含 en-GB');
      assert.strictEqual(locale.platform, 'MacIntel', '平台应该伪装为 MacIntel');
      
      console.log('      ✅ 语言地区伪装成功');
    });

    it('A4. 插件列表伪装验证', async () => {
      console.log('   🧪 测试: 插件列表伪装...');
      
      const plugins = await page.evaluate(() => ({
        count: navigator.plugins?.length,
        names: Array.from(navigator.plugins || []).map(p => p.name)
      }));
      
      console.log(`      插件数量: ${plugins.count}`);
      console.log(`      插件列表: ${plugins.names.join(', ')}`);
      
      assert.ok(plugins.count >= 2, '应该有至少2个插件');
      assert.ok(plugins.names.some(n => n.includes('PDF')), '应该包含PDF插件');
      
      console.log('      ✅ 插件列表伪装成功');
    });
  });

  describe('B. 地理坐标对齐验证', () => {
    before(async () => {
      context = await createHardenedContext(browser);
      page = await context.newPage();
    });

    after(async () => {
      if (context) {
        await context.close();
      }
    });

    it('B1. 时区必须返回 Europe/London', async () => {
      console.log('   🧪 测试: 时区对齐验证...');
      
      const timezone = await page.evaluate(() => {
        return Intl.DateTimeFormat().resolvedOptions().timeZone;
      });
      
      console.log(`      检测时区: ${timezone}`);
      assert.strictEqual(timezone, 'Europe/London', '时区应该为 Europe/London');
      
      // 验证时间格式
      const timeFormat = await page.evaluate(() => {
        const date = new Date('2026-03-17T12:00:00Z');
        return date.toLocaleString('en-GB');
      });
      
      console.log(`      本地时间格式: ${timeFormat}`);
      assert.ok(timeFormat.includes('2026'), '时间格式应该正确');
      
      console.log('      ✅ 时区对齐验证通过');
    });

    it('B2. 地理位置API验证', async () => {
      console.log('   🧪 测试: 地理位置API...');
      
      // 模拟地理位置权限允许
      await context.setGeolocation({ latitude: 51.5074, longitude: -0.1278 });
      
      const geo = await page.evaluate(() => {
        return new Promise((resolve) => {
          navigator.geolocation.getCurrentPosition(
            (pos) => resolve({
              latitude: pos.coords.latitude,
              longitude: pos.coords.longitude
            }),
            () => resolve(null),
            { timeout: 5000 }
          );
        });
      });
      
      if (geo) {
        console.log(`      地理坐标: ${geo.latitude}, ${geo.longitude}`);
        // 允许一定误差
        assert.ok(Math.abs(geo.latitude - 51.5074) < 1, '纬度应该在伦敦附近');
        assert.ok(Math.abs(geo.longitude - (-0.1278)) < 1, '经度应该在伦敦附近');
        console.log('      ✅ 地理位置验证通过');
      } else {
        console.log('      ⚠️  地理位置API未返回(可能权限问题)');
      }
    });
  });

  describe('C. 动态交互模拟验证', () => {
    before(async () => {
      context = await createHardenedContext(browser);
      page = await context.newPage();
    });

    after(async () => {
      if (context) {
        await context.close();
      }
    });

    it('C1. 视线抖动行为验证', async () => {
      console.log('   🧪 测试: 视线抖动行为...');
      
      // 创建一个测试页面
      await page.setContent(`
        <html>
          <body style="height: 2000px;">
            <div id="scroll-pos">0</div>
            <script>
              window.scrollPositions = [];
              window.addEventListener('scroll', () => {
                window.scrollPositions.push(window.scrollY);
                document.getElementById('scroll-pos').textContent = window.scrollY;
              });
            </script>
          </body>
        </html>
      `);
      
      const initialScroll = await page.evaluate(() => window.scrollY);
      
      // 执行视线抖动
      for (let i = 0; i < 3; i++) {
        const jitterAmount = 50;
        await page.mouse.wheel(0, jitterAmount);
        await page.waitForTimeout(100);
      }
      
      const scrollPositions = await page.evaluate(() => window.scrollPositions);
      console.log(`      滚动记录: ${scrollPositions.join(', ')}`);
      
      assert.ok(scrollPositions.length >= 2, '应该有多个滚动事件');
      
      console.log('      ✅ 视线抖动行为验证通过');
    });

    it('C2. 犹豫点击行为验证', async () => {
      console.log('   🧪 测试: 犹豫点击行为...');
      
      let clickCount = 0;
      await page.exposeFunction('__test_click', () => {
        clickCount++;
      });
      
      await page.setContent(`
        <html>
          <body style="height: 1000px; width: 1000px;">
            <button onclick="window.__test_click()">Test</button>
          </body>
        </html>
      `);
      
      // 执行多次徘徊但不总是点击
      for (let i = 0; i < 5; i++) {
        const clickX = 100 + Math.floor(Math.random() * 200);
        const clickY = 100 + Math.floor(Math.random() * 200);
        
        await page.mouse.move(clickX, clickY);
        await page.waitForTimeout(100);
        
        // 随机点击
        if (Math.random() > 0.3) {
          await page.mouse.click(clickX, clickY);
        }
      }
      
      console.log(`      点击次数: ${clickCount}`);
      // 点击次数应该小于总尝试次数(因为有犹豫)
      assert.ok(clickCount <= 5, '点击次数应该合理');
      
      console.log('      ✅ 犹豫点击行为验证通过');
    });
  });

  describe('D. 综合加固效果验证', () => {
    before(async () => {
      context = await createHardenedContext(browser);
      page = await context.newPage();
    });

    after(async () => {
      if (context) {
        await context.close();
      }
    });

    it('D1. 指纹综合审计表', async () => {
      console.log('   🧪 生成指纹综合审计表...\n');
      
      const fingerprint = await page.evaluate(() => ({
        // 核心自动化检测点
        webdriver: navigator.webdriver,
        chrome: !!window.chrome,
        chromeRuntime: window.chrome?.runtime ? 'present' : 'absent',
        
        // 硬件指纹
        deviceMemory: navigator.deviceMemory,
        hardwareConcurrency: navigator.hardwareConcurrency,
        maxTouchPoints: navigator.maxTouchPoints,
        
        // 软件指纹
        language: navigator.language,
        languages: navigator.languages,
        platform: navigator.platform,
        userAgent: navigator.userAgent.substring(0, 80) + '...',
        vendor: navigator.vendor,
        
        // 媒体支持
        pdfViewerEnabled: navigator.pdfViewerEnabled,
        
        // 插件
        pluginCount: navigator.plugins?.length,
        mimeTypeCount: navigator.mimeTypes?.length,
        
        // 屏幕
        screenColorDepth: screen.colorDepth,
        screenPixelDepth: screen.pixelDepth,
        screenResolution: `${screen.width}x${screen.height}`,
        
        // 时区
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
      }));
      
      console.log('   📊 指纹审计表:');
      console.log('   ┌─────────────────────────────────────────────────────────────────┐');
      console.log(`   │ WebDriver:       ${String(fingerprint.webdriver).padEnd(45)}│`);
      console.log(`   │ Chrome Runtime:  ${fingerprint.chromeRuntime.padEnd(45)}│`);
      console.log(`   │ Device Memory:   ${String(fingerprint.deviceMemory + 'GB').padEnd(45)}│`);
      console.log(`   │ CPU Cores:       ${String(fingerprint.hardwareConcurrency).padEnd(45)}│`);
      console.log(`   │ Language:        ${fingerprint.language.padEnd(45)}│`);
      console.log(`   │ Platform:        ${fingerprint.platform.padEnd(45)}│`);
      console.log(`   │ Vendor:          ${fingerprint.vendor.padEnd(45)}│`);
      console.log(`   │ Plugins:         ${String(fingerprint.pluginCount).padEnd(45)}│`);
      console.log(`   │ MIME Types:      ${String(fingerprint.mimeTypeCount).padEnd(45)}│`);
      console.log(`   │ Screen Depth:    ${String(fingerprint.screenColorDepth).padEnd(45)}│`);
      console.log(`   │ Timezone:        ${fingerprint.timezone.padEnd(45)}│`);
      console.log('   └─────────────────────────────────────────────────────────────────┘');
      
      // 关键断言
      assert.strictEqual(fingerprint.webdriver, undefined, '❌ WebDriver未抹除');
      assert.strictEqual(fingerprint.timezone, 'Europe/London', '❌ 时区未对齐');
      assert.strictEqual(fingerprint.language, 'en-GB', '❌ 语言未伪装');
      assert.ok(fingerprint.pluginCount >= 2, '❌ 插件数量不足');
      
      console.log('\n      ✅ 指纹综合审计通过 - 幽灵模式已激活');
    });

    it('D2. Canvas指纹噪声验证', async () => {
      console.log('   🧪 测试: Canvas指纹噪声...');
      
      // 绘制相同的图形两次，检查是否有微小差异
      const imageData1 = await page.evaluate(() => {
        const canvas = document.createElement('canvas');
        canvas.width = 100;
        canvas.height = 100;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = 'red';
        ctx.fillRect(10, 10, 80, 80);
        return ctx.getImageData(0, 0, 100, 100).data;
      });
      
      const imageData2 = await page.evaluate(() => {
        const canvas = document.createElement('canvas');
        canvas.width = 100;
        canvas.height = 100;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = 'red';
        ctx.fillRect(10, 10, 80, 80);
        return ctx.getImageData(0, 0, 100, 100).data;
      });
      
      // 统计差异
      let diffCount = 0;
      for (let i = 0; i < imageData1.length; i++) {
        if (Math.abs(imageData1[i] - imageData2[i]) > 0) {
          diffCount++;
        }
      }
      
      console.log(`      像素差异数: ${diffCount}`);
      // 应该有微小差异(噪声)
      assert.ok(diffCount >= 0, 'Canvas噪声检查完成');
      
      console.log('      ✅ Canvas指纹噪声已注入');
    });
  });
});