/**
 * V181-ENVIRONMENT-REFINE 认证状态捕获脚本
 * 系统弹窗屏蔽 + Cloudflare 优化
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const readline = require('readline');

// V181: 随机 User-Agent 库
const USER_AGENT_POOL = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
];

// V181: 随机选择 User-Agent
/**
 *
 */
function getRandomUserAgent() {
    return USER_AGENT_POOL[Math.floor(Math.random() * USER_AGENT_POOL.length)];
}

// V181: 随机硬件参数
/**
 *
 */
function getRandomHardwareParams() {
    return {
        hardwareConcurrency: 4 + Math.floor(Math.random() * 12),
        deviceMemory: [4, 8, 8, 16, 16, 32][Math.floor(Math.random() * 6)],
        platform: 'Win32'
    };
}

const AUTH_CONFIG = {
    targetUrl: 'https://www.fotmob.com/',
    userDataDir: './data/browser_profile',
    savePath: './data/browser_profile/browser_state.json',
    testMatches: [
        'https://www.fotmob.com/matches/liverpool-vs-chelsea/4813729',
        'https://www.fotmob.com/matches/-/4813729'
    ]
};

const log = {
    info: (msg) => console.log(`[${new Date().toISOString().slice(11, 19)}] ${msg}`),
    success: (msg) => console.log(`[${new Date().toISOString().slice(11, 19)}] ✅ ${msg}`),
    warn: (msg) => console.log(`[${new Date().toISOString().slice(11, 19)}] ⚠️  ${msg}`),
    error: (msg) => console.log(`[${new Date().toISOString().slice(11, 19)}] ❌ ${msg}`),
    step: (n, msg) => console.log(`\n[${new Date().toISOString().slice(11, 19)}] 步骤 ${n}: ${msg}`)
};

// V181: 强制清除 Bot 追踪标志（保留 Cookie）
/**
 *
 */
function cleanBotTrackingFlags() {
    const profileDir = AUTH_CONFIG.userDataDir;
    if (!fs.existsSync(profileDir)) {
        return;
    }

    log.info('正在清理 Bot 追踪标志...');

    // 要清除的目录列表
    const dirsToClean = [
        'Default/Web Storage',
        'Default/IndexedDB',
        'Default/Local Storage',
        'Default/Session Storage',
        'Default/Service Worker',
        'Default/Cache',
        'Default/Code Cache',
        'Default/GPUCache',
        'Default/optimization_guide'
    ];

    for (const dir of dirsToClean) {
        const fullPath = path.join(profileDir, dir);
        if (fs.existsSync(fullPath)) {
            try {
                fs.rmSync(fullPath, { recursive: true, force: true });
                log.info(`  已清理: ${dir}`);
            } catch (e) {
                log.warn(`  跳过: ${dir} (${e.message})`);
            }
        }
    }

    log.success('Bot 追踪标志清理完成');
}

// V181: 深度隐身脚本注入 - 在 page.goto 之前执行
/**
 *
 * @param page
 */
async function injectStealthScripts(page) {
    const hardware = getRandomHardwareParams();

    await page.addInitScript((hw) => {
        // ═══════════════════════════════════════════════════════════════
        // 核心指纹覆盖 - 必须与 UA 完全一致
        // ═══════════════════════════════════════════════════════════════

        // 覆盖 webdriver 标志
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
            configurable: true
        });

        // 【关键修复】覆盖 platform
        Object.defineProperty(navigator, 'platform', {
            get: () => hw.platform,
            configurable: true
        });

        // 【关键修复】模拟语言
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
            configurable: true
        });

        // 模拟硬件并发
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => hw.hardwareConcurrency,
            configurable: true
        });

        // 模拟设备内存
        Object.defineProperty(navigator, 'deviceMemory', {
            get: () => hw.deviceMemory,
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

        // ═══════════════════════════════════════════════════════════════
        // WebGL 指纹伪装
        // ═══════════════════════════════════════════════════════════════
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

        // ═══════════════════════════════════════════════════════════════
        // Canvas 指纹噪音
        // ═══════════════════════════════════════════════════════════════
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

        // ═══════════════════════════════════════════════════════════════
        // 隐藏自动化标志
        // ═══════════════════════════════════════════════════════════════
        delete window.__webdriver_evaluate;
        delete window.__webdriver_script_function;
        delete window.__webdriver_script_fn;
        delete window.__webdriver_unwrapped;
        delete window.__selenium_evaluate;
        delete window.__selenium_script_function;
        delete window.__selenium_script_fn;
        delete window.__fxdriver_evaluate;
        delete window.__driver_evaluate;
        delete window.__webdriver_script_fn;
        delete window.__lastWatirAlert;
        delete window.__lastWatirConfirm;
        delete window.__lastWatirPrompt;
        delete window._Selenium_IDE_Recorder;
        delete window._selenium;
        delete window.calledSelenium;

        if (window.chrome) {
            window.chrome.runtime = window.chrome.runtime || {};
        }

        // ═══════════════════════════════════════════════════════════════
        // 覆盖 permissions 查询
        // ═══════════════════════════════════════════════════════════════
        const originalQueryInterface = window.navigator.permissions?.query;
        if (originalQueryInterface) {
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' && typeof Notification !== 'undefined' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQueryInterface(parameters)
            );
        }

        // ═══════════════════════════════════════════════════════════════
        // 覆盖 toString 保持原生外观
        // ═══════════════════════════════════════════════════════════════
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

        // ═══════════════════════════════════════════════════════════════
        // iframe contentWindow 检测绕过
        // ═══════════════════════════════════════════════════════════════
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

        console.log('[Stealth] V181 深度隐身脚本已注入');
    }, hardware);
}

/**
 *
 */
async function captureAuth() {
    // V181: 随机选择 User-Agent
    const selectedUA = getRandomUserAgent();
    const hardware = getRandomHardwareParams();

    console.log('\n' + '='.repeat(70));
    console.log('  V181-ENVIRONMENT-REFINE 认证状态捕获工具');
    console.log('  系统弹窗屏蔽 + Cloudflare 优化');
    console.log('='.repeat(70));
    console.log('\n配置:');
    console.log(`   User-Agent: ${selectedUA.slice(0, 60)}...`);
    console.log(`   Hardware: ${hardware.hardwareConcurrency} cores, ${hardware.deviceMemory}GB RAM`);
    console.log(`   Platform: ${hardware.platform}`);
    console.log(`   Viewport: 1366x768 (降维模式)`);
    console.log('   数据目录:', AUTH_CONFIG.userDataDir);

    // V181: 确保目录存在
    if (!fs.existsSync(AUTH_CONFIG.userDataDir)) {
        fs.mkdirSync(AUTH_CONFIG.userDataDir, { recursive: true });
    }

    // V181: 强制清除 Bot 追踪标志
    cleanBotTrackingFlags();

    log.step(1, '启动隐身持久化浏览器 (V181 弹窗屏蔽版)...');

    // V181: 增强启动参数（屏蔽弹窗 + 反检测）
    const context = await chromium.launchPersistentContext(AUTH_CONFIG.userDataDir, {
        headless: false,
        // V181: 降维窗口大小 1366x768
        viewport: { width: 1366, height: 768 },
        deviceScaleFactor: 1,
        userAgent: selectedUA,
        locale: 'en-US',
        timezoneId: 'Europe/London',
        // V181: 关键反检测参数
        ignoreDefaultArgs: ['--enable-automation'],
        args: [
            '--disable-blink-features=AutomationControlled',
            '--disable-infobars',
            // V181: 屏蔽系统弹窗
            '--no-default-browser-check',
            '--disable-external-intent-requests',
            '--disable-popup-blocking',
            '--disable-notifications',
            '--disable-geolocation',
            '--disable-dev-shm-usage',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--disable-features=IsolateOrigins,site-per-process',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-gpu',
            // V181: 降维窗口大小
            '--window-size=1366,768'
        ],
        ignoreHTTPSErrors: true,
        // V181: 禁用所有权限请求
        permissions: []
    });

    // V181: 禁用所有页面的通知和地理位置
    context.on('page', async (page) => {
        await page.evaluate(() => {
            // V181-fix: 覆盖通知权限（带类型检查）
            if (typeof Notification !== 'undefined') {
                Object.defineProperty(Notification, 'permission', {
                    get: () => 'denied',
                    configurable: true
                });
            }
            // V181-fix: 覆盖地理位置（带类型检查）
            if (typeof navigator !== 'undefined' && navigator.geolocation) {
                navigator.geolocation.getCurrentPosition = () => {};
                navigator.geolocation.watchPosition = () => {};
            }
        });
    });

    const pages = context.pages();
    const page = pages.length > 0 ? pages[0] : await context.newPage();

    // V181: 注入深度隐身脚本（在 goto 之前！）
    log.step(2, '注入 V181 深度隐身脚本...');
    await injectStealthScripts(page);
    log.success('隐身脚本注入完成');

    // V181: 设置页面权限（最高优先级）
    await page.evaluate(() => {
        // V181-fix: 安全覆盖通知权限
        if (typeof Notification !== 'undefined') {
            Object.defineProperty(Notification, 'permission', {
                get: () => 'denied',
                configurable: true
            });
        }
        // V181-fix: 安全覆盖地理位置
        if (typeof navigator !== 'undefined' && navigator.geolocation) {
            navigator.geolocation.getCurrentPosition = () => {};
            navigator.geolocation.watchPosition = () => {};
        }
    });

    log.step(3, '导航到 FotMob...');
    await page.goto(AUTH_CONFIG.targetUrl, { waitUntil: 'domcontentloaded' });

    // V181: 模拟人类行为（随机滚动）
    log.info('模拟人类浏览行为...');
    for (let i = 0; i < 3; i++) {
        await page.mouse.move(
            300 + Math.random() * 500,
            200 + Math.random() * 300,
            { steps: 10 + Math.floor(Math.random() * 10) }
        );
        await page.waitForTimeout(500 + Math.random() * 1000);
    }

    console.log('\n' + '='.repeat(70));
    console.log('  请在浏览器中完成以下操作:');
    console.log('='.repeat(70));
    console.log('');
    console.log('  1. 如果出现 Turnstile 验证，请手动完成');
    console.log('     💡 提示: V181 已屏蔽弹窗并优化隐身');
    console.log('  2. 点击任意一场比赛，进入详情页');
    console.log('  3. 确认能看到 xG 数据');
    console.log('  4. 可选：浏览 1-2 场其他比赛');
    console.log('');
    console.log('  完成后，回到此终端按 Enter 键保存状态...');
    console.log('');
    console.log('='.repeat(70));

    await waitForEnter();

    log.step(4, '保存浏览器状态...');

    const state = await context.storageState({ path: AUTH_CONFIG.savePath });

    log.success(`状态已保存到: ${AUTH_CONFIG.savePath}`);
    log.info(`Cookies: ${state.cookies ? state.cookies.length : 0}`);

    if (state.cookies && state.cookies.length > 0) {
        const fotmobCookies = state.cookies.filter(c => c.domain.includes('fotmob'));
        log.info(`FotMob Cookies: ${fotmobCookies.length}`);
    }

    log.step(5, '验证身份有效性...');

    try {
        await page.goto(AUTH_CONFIG.testMatches[1], { timeout: 30000 });
        await page.waitForTimeout(3000);

        const content = await page.content();
        const hasTurnstile = content.includes('Turnstile') || content.includes('challenge');
        const hasMatchData = content.includes('xG') || content.includes('Expected');

        if (hasTurnstile) {
            log.warn('检测到 Turnstile，身份可能未完全验证');
        } else if (hasMatchData) {
            log.success('身份验证成功！检测到比赛数据');
        } else {
            log.info('页面加载成功，等待数据确认...');
        }
    } catch (e) {
        log.warn(`验证失败: ${e.message}`);
    }

    await context.close();

    console.log('\n' + '='.repeat(70));
    console.log('  认证捕获完成！');
    console.log('  V181 环境净化已应用');
    console.log('='.repeat(70));
}

/**
 *
 */
function waitForEnter() {
    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout
    });
    return new Promise(resolve => {
        rl.question('', () => {
            rl.close();
            resolve();
        });
    });
}

captureAuth().catch(error => {
    console.error('\n捕获失败:', error.message);
    process.exit(1);
});
