/**
 * 指纹穿透测试脚本
 * =================
 *
 * 访问 bot.sannysoft.com 检测浏览器指纹一致性
 *
 * 用法: node scripts/ops/fingerprint_check.js
 */

'use strict';

const { chromium } = require('playwright');
const { generateStealthHeaders } = require('../../src/infrastructure/network/StealthFingerprint');

// 获取 Chromium 实际版本
function getChromiumVersion() {
    // 从 Playwright 获取实际 Chromium 版本
    return require('playwright-core/browsers.json');
}

async function main() {
    console.log('');
    console.log('╔════════════════════════════════════════════════════════════╗');
    console.log('║  🔍 [FINGERPRINT_CHECK] 浏览器指纹穿透测试                  ║');
    console.log('╚════════════════════════════════════════════════════════════╝');
    console.log('');

    // 获取隐身配置
    const stealth = generateStealthHeaders(true);
    console.log('📋 当前指纹配置:');
    console.log(`   UA: ${stealth.userAgent.substring(0, 60)}...`);
    console.log(`   Viewport: ${stealth.viewport.width}x${stealth.viewport.height}`);
    console.log(`   Timezone: ${stealth.timezoneId}`);
    console.log(`   Locale: ${stealth.locale}`);
    console.log('');

    // 启动浏览器
    const browser = await chromium.launch({
        headless: true,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-blink-features=AutomationControlled',
            '--disable-gpu'
        ]
    });

    // 创建上下文
    const context = await browser.newContext({
        viewport: stealth.viewport,
        userAgent: stealth.userAgent,
        extraHTTPHeaders: stealth.extraHTTPHeaders,
        locale: stealth.locale,
        timezoneId: stealth.timezoneId
    });

    const page = await context.newPage();

    // 注入隐身脚本 (V4.46.1 与 AbstractHarvester 一致)
    await page.addInitScript(() => {
        // ═══════════════════════════════════════════════════════════════
        // 核心指纹覆盖 - 必须与 UA 完全一致
        // ═══════════════════════════════════════════════════════════════

        // 覆盖 webdriver 标志
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
            configurable: true
        });

        // 【关键修复】覆盖 platform - 必须与 UA 中的 Windows 匹配
        Object.defineProperty(navigator, 'platform', {
            get: () => 'Win32',
            configurable: true
        });

        // 模拟语言
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
            configurable: true
        });

        // 模拟硬件并发
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => 8 + (Math.floor(Math.random() * 17)),
            configurable: true
        });

        // 模拟设备内存
        Object.defineProperty(navigator, 'deviceMemory', {
            get: () => [4, 8, 8, 16, 16, 32][Math.floor(Math.random() * 6)],
            configurable: true
        });

        // 模拟 Chrome 插件数组
        Object.defineProperty(navigator, 'plugins', {
            get: () => {
                const plugins = [
                    Object.create(Plugin.prototype, {
                        name: { value: 'Chrome PDF Plugin' },
                        description: { value: 'Portable Document Format' },
                        filename: { value: 'internal-pdf-viewer' },
                        length: { value: 1 }
                    }),
                    Object.create(Plugin.prototype, {
                        name: { value: 'Chrome PDF Viewer' },
                        description: { value: '' },
                        filename: { value: 'mhjfbmdg-nopdfs' },
                        length: { value: 1 }
                    }),
                    Object.create(Plugin.prototype, {
                        name: { value: 'Native Client' },
                        description: { value: '' },
                        filename: { value: 'internal-nacl' },
                        length: { value: 1 }
                    })
                ];
                plugins.item = (i) => plugins[i] || null;
                plugins.namedItem = (name) => plugins.find(p => p.name === name) || null;
                plugins.refresh = () => {};
                return plugins;
            },
            configurable: true
        });

        // WebGL 指纹伪装
        const WEBGL_RENDERERS = [
            { vendor: 'Google Inc. (NVIDIA)', renderer: 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)' },
            { vendor: 'Google Inc. (NVIDIA)', renderer: 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 Direct3D11 vs_5_0 ps_5_0, D3D11)' },
            { vendor: 'Google Inc. (AMD)', renderer: 'ANGLE (AMD, AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0, D3D11)' },
            { vendor: 'Google Inc. (Intel)', renderer: 'ANGLE (Intel, Intel UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)' }
        ];
        const selectedRenderer = WEBGL_RENDERERS[Math.floor(Math.random() * WEBGL_RENDERERS.length)];

        const getParameterProxyHandler = {
            apply: function(target, thisArg, args) {
                const param = args[0];
                if (param === 37445) return selectedRenderer.vendor;
                if (param === 37446) return selectedRenderer.renderer;
                return target.apply(thisArg, args);
            }
        };

        if (typeof WebGLRenderingContext !== 'undefined') {
            const originalGetParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = new Proxy(originalGetParameter, getParameterProxyHandler);
        }

        if (typeof WebGL2RenderingContext !== 'undefined') {
            const originalGetParameter2 = WebGL2RenderingContext.prototype.getParameter;
            WebGL2RenderingContext.prototype.getParameter = new Proxy(originalGetParameter2, getParameterProxyHandler);
        }

        // Canvas 指纹噪音
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(type) {
            if (this.width > 0 && this.height > 0) {
                const ctx = this.getContext('2d');
                if (ctx) {
                    const imageData = ctx.getImageData(0, 0, this.width, this.height);
                    for (let i = 0; i < imageData.data.length; i += 4) {
                        imageData.data[i] ^= (Math.random() * 2) | 0;
                    }
                    ctx.putImageData(imageData, 0, 0);
                }
            }
            return originalToDataURL.apply(this, arguments);
        };

        // 隐藏自动化标志
        delete window.__webdriver_evaluate;
        delete window.__webdriver_script_function;
        delete window.__webdriver_script_fn;
        delete window.__webdriver_unwrapped;
        delete window.__selenium_evaluate;
        delete window.__driver_evaluate;
        delete window._Selenium_IDE_Recorder;
        delete window._selenium;
        delete window.calledSelenium;

        if (window.chrome) {
            window.chrome.runtime = window.chrome.runtime || {};
        }

        // 覆盖 permissions 查询
        const originalQueryInterface = window.navigator.permissions?.query;
        if (originalQueryInterface) {
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQueryInterface(parameters)
            );
        }

        // 覆盖 toString
        const oldToString = Function.prototype.toString;
        Function.prototype.toString = function() {
            if (this === navigator.permissions?.query) {
                return 'function query() { [native code] }';
            }
            if (this === HTMLCanvasElement.prototype.toDataURL) {
                return 'function toDataURL() { [native code] }';
            }
            return oldToString.call(this);
        };

        // iframe contentWindow 检测绕过
        const originalContentWindow = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'contentWindow');
        Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
            get: function() {
                const window = originalContentWindow.get.call(this);
                if (window) {
                    Object.defineProperty(window.navigator, 'webdriver', { get: () => undefined });
                }
                return window;
            }
        });
    });

    console.log('🌐 访问 bot.sannysoft.com...');

    try {
        await page.goto('https://bot.sannysoft.com/', {
            waitUntil: 'networkidle',
            timeout: 60000
        });

        await page.waitForTimeout(3000);

        // 提取检测结果
        const results = await page.evaluate(() => {
            const rows = document.querySelectorAll('table tr');
            const items = [];

            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                if (cells.length >= 2) {
                    const name = cells[0].textContent.trim();
                    const value = cells[1].textContent.trim();
                    const status = cells[2]?.textContent.trim() || '';

                    items.push({ name, value, status });
                }
            });

            return items;
        });

        console.log('');
        console.log('╔════════════════════════════════════════════════════════════╗');
        console.log('║  📊 检测结果                                               ║');
        console.log('╠════════════════════════════════════════════════════════════╣');

        let failCount = 0;
        let passCount = 0;
        const criticalTests = ['WebDriver', 'Chrome', 'Plugins', 'Languages', 'Platform', 'User Agent'];

        results.forEach(item => {
            const isFail = item.status.toLowerCase().includes('fail') ||
                          item.status.toLowerCase().includes('bad');
            const isCritical = criticalTests.some(t => item.name.includes(t));

            if (isFail) {
                failCount++;
                const marker = isCritical ? '❌ [CRITICAL]' : '⚠️  [FAIL]';
                console.log(`║  ${marker} ${item.name}: ${item.value.substring(0, 30)}`);
            } else if (item.status.toLowerCase().includes('pass') || item.status.toLowerCase().includes('ok')) {
                passCount++;
                if (isCritical) {
                    console.log(`║  ✅ ${item.name}: ${item.value.substring(0, 40)}`);
                }
            }
        });

        console.log('╠════════════════════════════════════════════════════════════╣');
        console.log(`║  统计: ✅ Pass: ${passCount} | ❌ Fail: ${failCount}                           ║`);
        console.log('╚════════════════════════════════════════════════════════════╝');

        // 获取 navigator 信息
        const navInfo = await page.evaluate(() => ({
            userAgent: navigator.userAgent,
            platform: navigator.platform,
            languages: navigator.languages,
            hardwareConcurrency: navigator.hardwareConcurrency,
            deviceMemory: navigator.deviceMemory,
            webdriver: navigator.webdriver,
            plugins: Array.from(navigator.plugins).map(p => p.name)
        }));

        console.log('');
        console.log('📋 Navigator 信息:');
        console.log(`   userAgent: ${navInfo.userAgent}`);
        console.log(`   platform: ${navInfo.platform}`);
        console.log(`   languages: ${JSON.stringify(navInfo.languages)}`);
        console.log(`   hardwareConcurrency: ${navInfo.hardwareConcurrency}`);
        console.log(`   deviceMemory: ${navInfo.deviceMemory}`);
        console.log(`   webdriver: ${navInfo.webdriver}`);
        console.log(`   plugins: ${navInfo.plugins.length} 个`);

        // 截图保存
        const screenshotPath = '/app/logs/fingerprint_check.png';
        await page.screenshot({ path: screenshotPath, fullPage: true });
        console.log(`\n📸 截图已保存: ${screenshotPath}`);

        // 返回结果
        if (failCount > 0) {
            console.log('\n⚠️  检测到指纹问题，需要修复隐身脚本！');
        } else {
            console.log('\n✅ 所有检测通过，指纹伪装成功！');
        }

    } catch (error) {
        console.error('❌ 检测失败:', error.message);
    } finally {
        await page.close();
        await context.close();
        await browser.close();
    }
}

main().catch(console.error);
