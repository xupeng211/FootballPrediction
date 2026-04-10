'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { ReconBrowserContext } = require('../../src/infrastructure/recon/services/ReconBrowserContext');

describe('ReconBrowserContext', () => {
  it('应独立完成 launch 与 close 生命周期', async () => {
    const events = [];
    const page = {};

    const context = {
      browser() {
        return browser;
      },
      async newPage() {
        events.push('newPage');
        return page;
      },
      async close() {
        events.push('context.close');
      }
    };

    const browser = {
      async close() {
        events.push('browser.close');
      }
    };

    const chromium = {
      async launchPersistentContext(userDataDir, options) {
        events.push({ type: 'launchPersistentContext', userDataDir, options });
        return context;
      }
    };

    const browserContext = new ReconBrowserContext({
      logger: { info() {}, warn() {}, error() {} },
      traceId: 'trace-browser',
      chromium,
      headless: true,
      proxy: { host: '127.0.0.1', port: 8899 },
      preferFullChromium: false
    });

    const launchedPage = await browserContext.launch({ timeout: 4321 });

    assert.strictEqual(launchedPage, page);
    assert.strictEqual(browserContext.browser, browser);
    assert.strictEqual(browserContext.context, context);
    assert.strictEqual(browserContext.page, page);
    assert.deepStrictEqual(events[0], {
      type: 'launchPersistentContext',
      userDataDir: browserContext.userDataDir,
      options: {
        headless: true,
        args: [
          '--no-sandbox',
          '--disable-setuid-sandbox',
          '--disable-blink-features=AutomationControlled',
          '--disable-dev-shm-usage',
          '--window-size=1920,1080',
          '--lang=en-US'
        ],
        timeout: 4321,
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        viewport: { width: 1920, height: 1080 },
        locale: 'en-US',
        timezoneId: 'Europe/London',
        deviceScaleFactor: 1,
        screen: { width: 1920, height: 1080 },
        hasTouch: false,
        isMobile: false,
        proxy: { server: 'http://127.0.0.1:8899' },
        extraHTTPHeaders: {
          'sec-ch-ua': '"Chromium";v="131", "Google Chrome";v="131", "Not-A.Brand";v="99"',
          'sec-ch-ua-mobile': '?0',
          'sec-ch-ua-platform': '"Windows"',
          'sec-fetch-dest': 'document',
          'sec-fetch-mode': 'navigate',
          'sec-fetch-site': 'none',
          'sec-fetch-user': '?1',
          'accept-language': 'en-US,en;q=0.9',
          'accept-encoding': 'gzip, deflate, br',
          'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        }
      }
    });
    assert.match(browserContext.userDataDir, /playwright_profile_trace-browser_/);
    assert.strictEqual(events[1], 'newPage');

    await browserContext.close();

    assert.strictEqual(browserContext.browser, null);
    assert.strictEqual(browserContext.context, null);
    assert.strictEqual(browserContext.page, null);
    assert.strictEqual(browserContext.isClosed, true);
    assert.strictEqual(events[2], 'context.close');
  });

  it('应同时注入基础 stealth 指纹与增强反检测脚本', async () => {
    const events = [];
    const page = {
      async addInitScript(fn) {
        events.push({ type: 'addInitScript', value: typeof fn });
      }
    };

    const context = {
      browser() {
        return browser;
      },
      async newPage() {
        return page;
      },
      async close() {}
    };

    const browser = {
      async close() {}
    };

    const chromium = {
      async launchPersistentContext() {
        return context;
      }
    };

    const browserContext = new ReconBrowserContext({
      logger: { info() {}, warn() {}, error() {} },
      traceId: 'trace-browser-stealth',
      chromium,
      enableStealthFingerprint: true
    });

    await browserContext.launch({ timeout: 4321 });

    assert.deepStrictEqual(events, [
      { type: 'addInitScript', value: 'function' },
      { type: 'addInitScript', value: 'string' }
    ]);
  });

  it('resetContext 应在批次切换时销毁旧 context 并注入全新指纹', async () => {
    const lifecycleEvents = [];
    const contextOptions = [];
    const initScripts = [];
    const pageA = {
      isClosed() {
        return false;
      },
      async close() {
        lifecycleEvents.push('pageA.close');
      },
      async addInitScript(value) {
        initScripts.push({ page: 'A', value: typeof value });
      }
    };
    const pageB = {
      isClosed() {
        return false;
      },
      async addInitScript(value) {
        initScripts.push({ page: 'B', value: typeof value });
      }
    };
    const contextA = {
      async newPage() {
        lifecycleEvents.push('contextA.newPage');
        return pageA;
      },
      async close() {
        lifecycleEvents.push('contextA.close');
      }
    };
    const contextB = {
      async newPage() {
        lifecycleEvents.push('contextB.newPage');
        return pageB;
      },
      async close() {
        lifecycleEvents.push('contextB.close');
      }
    };
    const browser = {
      isConnected() {
        return true;
      },
      async newContext(options) {
        contextOptions.push(options);
        return contextOptions.length === 1 ? contextA : contextB;
      },
      async close() {
        lifecycleEvents.push('browser.close');
      }
    };
    const chromium = {
      async launch(options) {
        lifecycleEvents.push({ type: 'launch', options });
        return browser;
      }
    };
    const identities = [
      {
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        viewport: { width: 1366, height: 768 },
        locale: 'en-US',
        timezoneId: 'Europe/London',
        platform: 'Win32',
        deviceScaleFactor: 1,
        hasTouch: false,
        isMobile: false,
        extraHTTPHeaders: { 'accept-language': 'en-US,en;q=0.9' },
        hardwareConcurrency: 8,
        deviceMemory: 8,
        webgl: {
          vendor: 'Google Inc. (Intel)',
          renderer: 'ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)'
        },
        fingerprintSeed: 'seed-a',
        canvasSalt: 'canvas-a',
        audioSalt: 'audio-a',
        webglSalt: 'webgl-a',
        antiDetectionScript: 'script-a'
      },
      {
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
        viewport: { width: 1912, height: 1072 },
        locale: 'en-US',
        timezoneId: 'Europe/London',
        platform: 'Win32',
        deviceScaleFactor: 1,
        hasTouch: false,
        isMobile: false,
        extraHTTPHeaders: {
          'accept-language': 'en-US,en;q=0.9',
          'sec-ch-ua': '"Chromium";v="131", "Microsoft Edge";v="131", "Not_A Brand";v="24"'
        },
        hardwareConcurrency: 16,
        deviceMemory: 16,
        webgl: {
          vendor: 'Google Inc. (NVIDIA)',
          renderer: 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)'
        },
        fingerprintSeed: 'seed-b',
        canvasSalt: 'canvas-b',
        audioSalt: 'audio-b',
        webglSalt: 'webgl-b',
        antiDetectionScript: 'script-b'
      }
    ];

    const browserContext = new ReconBrowserContext({
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      traceId: 'trace-browser-rotate',
      chromium,
      persistentProfileEnabled: false
    });
    browserContext.enableFingerprintRotation = true;
    browserContext.resetContextPerBatchEnabled = true;
    browserContext.contextGeneration = 0;
    browserContext._buildStealthIdentity = () => identities.shift();
    browserContext._applyStealthIdentity(browserContext._buildStealthIdentity());

    await browserContext.launch();
    await browserContext.resetContext({ reason: 'batch_reset' });

    assert.strictEqual(contextOptions.length, 2);
    assert.strictEqual(contextOptions[0].userAgent, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36');
    assert.strictEqual(contextOptions[1].userAgent, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0');
    assert.deepStrictEqual(contextOptions[0].viewport, { width: 1366, height: 768 });
    assert.deepStrictEqual(contextOptions[1].viewport, { width: 1912, height: 1072 });
    assert.deepStrictEqual(lifecycleEvents.slice(0, 5), [
      {
        type: 'launch',
        options: {
          headless: true,
          args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--window-size=1366,768',
            '--lang=en-US'
          ],
          timeout: 60000
        }
      },
      'contextA.newPage',
      'pageA.close',
      'contextA.close',
      'contextB.newPage'
    ]);
    assert.deepStrictEqual(initScripts, [
      { page: 'A', value: 'function' },
      { page: 'A', value: 'string' },
      { page: 'B', value: 'function' },
      { page: 'B', value: 'string' }
    ]);
    assert.strictEqual(browserContext.page, pageB);
    assert.strictEqual(browserContext.getFingerprintSummary().fingerprintSeed, 'seed-b');
  });

  it('启用 preferFullChromium 时应把完整 Chromium executablePath 注入 launchOptions', async () => {
    const events = [];
    const page = {
      async addInitScript() {}
    };

    const context = {
      browser() {
        return browser;
      },
      async newPage() {
        return page;
      },
      async close() {}
    };

    const browser = {
      async close() {}
    };

    const chromium = {
      async launchPersistentContext(_userDataDir, options) {
        events.push(options);
        return context;
      }
    };

    const browserContext = new ReconBrowserContext({
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      traceId: 'trace-browser-full-chromium',
      chromium,
      preferFullChromium: true,
      resolvePreferredExecutablePath: () => '/tmp/playwright/chromium/chrome'
    });

    await browserContext.launch();

    assert.strictEqual(events.length, 1);
    assert.strictEqual(events[0].executablePath, '/tmp/playwright/chromium/chrome');
  });

  it('launch 后应自动注入 external session cookies，并保持 Chrome 131 stealth UA', async () => {
    const events = [];
    const page = {
      async addInitScript() {}
    };

    const context = {
      browser() {
        return browser;
      },
      async addCookies(cookies) {
        events.push({ type: 'addCookies', cookies });
      },
      async newPage() {
        return page;
      },
      async close() {}
    };

    const browser = {
      async close() {}
    };

    const chromium = {
      async launchPersistentContext(_userDataDir, options) {
        events.push({ type: 'launchPersistentContext', options });
        return context;
      }
    };

    const browserContext = new ReconBrowserContext({
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      traceId: 'trace-browser-external-session',
      chromium,
      sessionManager: {
        load() {
          return {
            sourceFormat: 'json',
            userAgent: 'External-UA/1.0',
            extraHTTPHeaders: { 'user-agent': 'External-UA/1.0' },
            cookies: [
              {
                name: 'session-cookie',
                value: 'cookie-value',
                domain: '.oddsportal.com',
                path: '/',
                expires: -1,
                httpOnly: false,
                secure: true,
                sameSite: 'Lax'
              }
            ]
          };
        }
      }
    });

    await browserContext.launch();

    assert.strictEqual(events[0].type, 'launchPersistentContext');
    assert.strictEqual(
      events[0].options.userAgent,
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
    );
    assert.strictEqual(
      events[0].options.extraHTTPHeaders['user-agent'],
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
    );
    assert.strictEqual(events[1].type, 'addCookies');
    assert.strictEqual(events[1].cookies.length, 1);
    assert.strictEqual(events[1].cookies[0].name, 'session-cookie');
  });

  it('应独立处理 consent 按钮点击', async () => {
    const clicked = [];
    const waits = [];
    const hiddenLabels = new Set(['I Accept']);

    const browserContext = new ReconBrowserContext({
      logger: { info() {}, warn() {}, error() {} },
      traceId: 'trace-consent',
      chromium: { async launch() { throw new Error('not_used'); } }
    });

    browserContext.page = {
      getByRole(_role, { name }) {
        return {
          first() {
            return {
              async isVisible() {
                return !hiddenLabels.has(name);
              },
              async click() {
                clicked.push(name);
              }
            };
          }
        };
      },
      async waitForTimeout(ms) {
        waits.push(ms);
      }
    };

    const handled = await browserContext.handleConsent();

    assert.strictEqual(handled, true);
    assert.deepStrictEqual(clicked, ['Accept All']);
    assert.deepStrictEqual(waits, [1000]);
  });

  it('navigate 默认应使用 domcontentloaded 并等待显式选择器', async () => {
    const events = [];
    const browserContext = new ReconBrowserContext({
      logger: { info() {}, warn() {}, error() {} },
      traceId: 'trace-navigate',
      chromium: { async launch() { throw new Error('not_used'); } },
      navigationReadySelectors: ['.ready-selector']
    });

    browserContext.page = {
      async goto(url, options) {
        events.push({ type: 'goto', url, options });
      },
      getByRole() {
        return {
          first() {
            return {
              async isVisible() {
                return false;
              }
            };
          }
        };
      },
      async waitForSelector(selector, options) {
        events.push({ type: 'waitForSelector', selector, options });
      },
      async waitForTimeout(ms) {
        events.push({ type: 'waitForTimeout', ms });
      },
      async evaluate(fn, amount) {
        events.push({ type: 'evaluate', fn: typeof fn, amount });
      }
    };

    await browserContext.navigate('https://example.com/recon');

    assert.deepStrictEqual(events[0], {
      type: 'goto',
      url: 'https://example.com/recon',
      options: {
        timeout: 60000,
        waitUntil: 'domcontentloaded'
      }
    });
    assert.ok(events.some((event) => (
      event.type === 'waitForSelector'
      && event.selector === '.ready-selector'
      && event.options?.timeout === 5000
      && event.options?.state === 'attached'
    )));
  });

  it('启用首页预热时应先访问首页并等待指定时长', async () => {
    const events = [];
    const browserContext = new ReconBrowserContext({
      logger: { info() {}, warn() {}, error() {} },
      traceId: 'trace-home-warmup',
      chromium: { async launch() { throw new Error('not_used'); } },
      navigationReadySelectors: ['main'],
      homeWarmupEnabled: true,
      homeWarmupWaitMs: 5000
    });

    browserContext.page = {
      async goto(url, options) {
        events.push({ type: 'goto', url, options });
      },
      getByRole() {
        return {
          first() {
            return {
              async isVisible() {
                return false;
              }
            };
          }
        };
      },
      async waitForSelector(selector, options) {
        events.push({ type: 'waitForSelector', selector, options });
      },
      async waitForTimeout(ms) {
        events.push({ type: 'waitForTimeout', ms });
      },
      async evaluate() {}
    };

    await browserContext.navigate('https://example.com/recon');

    assert.deepStrictEqual(events[0], {
      type: 'goto',
      url: 'https://www.oddsportal.com',
      options: {
        timeout: 60000,
        waitUntil: 'domcontentloaded'
      }
    });
    assert.deepStrictEqual(events[1], { type: 'waitForTimeout', ms: 5000 });
    assert.deepStrictEqual(events[2], {
      type: 'goto',
      url: 'https://example.com/recon',
      options: {
        timeout: 60000,
        waitUntil: 'domcontentloaded'
      }
    });
  });

  it('navigate 命中 503 Backend fetch failed 页面时应抛出显式 HTTP_503', async () => {
    const browserContext = new ReconBrowserContext({
      logger: { info() {}, warn() {}, error() {} },
      traceId: 'trace-navigate-503',
      chromium: { async launch() { throw new Error('not_used'); } },
      navigationReadySelectors: ['main']
    });

    browserContext.page = {
      async goto() {
        return {
          status() {
            return 200;
          }
        };
      },
      async title() {
        return '503 Backend fetch failed';
      },
      async evaluate() {
        return 'Guru Meditation';
      }
    };

    await assert.rejects(
      browserContext.navigate('https://example.com/recon'),
      (error) => error?.statusCode === 503 && error?.message === 'HTTP_503 backend_fetch_failed'
    );
  });

  it('contentReadySelector 应按联赛配置等待可见内容', async () => {
    const events = [];
    const browserContext = new ReconBrowserContext({
      logger: { info() {}, warn() {}, error() {} },
      traceId: 'trace-ready-selector',
      chromium: { async launch() { throw new Error('not_used'); } },
      navigationReadySelectors: ['main']
    });

    browserContext.page = {
      async goto(url) {
        events.push({ type: 'goto', url });
      },
      getByRole() {
        return {
          first() {
            return {
              async isVisible() {
                return false;
              }
            };
          }
        };
      },
      async waitForSelector(selector, options) {
        events.push({ type: 'waitForSelector', selector, options });
      },
      async waitForTimeout(ms) {
        events.push({ type: 'waitForTimeout', ms });
      },
      async evaluate() {}
    };

    await browserContext.navigate('https://example.com/recon', {
      contentReadySelector: 'text=Fixture Ready'
    });

    assert.ok(events.some((event) => (
      event.type === 'waitForSelector'
      && event.selector === 'text=Fixture Ready'
      && event.options?.state === 'visible'
    )));
  });

  it('force_unlock_j1 命中且 myBookmakers 变化时应重触发 archive 请求', async () => {
    const browserContext = new ReconBrowserContext({
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      traceId: 'trace-force-unlock-j1',
      chromium: { async launch() { throw new Error('not_used'); } },
      forceUnlockJ1: {
        enabled: true,
        url_patterns: ['/football/japan/j1-league'],
        menu_labels: ['BOOKMAKERS'],
        select_all_labels: ['Select All'],
        fallback_bookmakers: ['Bet365', 'Pinnacle'],
        open_wait_ms: 0,
        post_select_wait_ms: 0,
        state_wait_ms: 0,
        retrigger_timeout_ms: 3000
      }
    });

    browserContext.page = {
      async waitForTimeout() {}
    };

    let readCount = 0;
    browserContext.openBookmakerMenu = async () => true;
    browserContext.applyBookmakerSelection = async () => ({
      selectAllClicked: false,
      clickedBookmakers: ['bet365']
    });
    browserContext.readBookmakerState = async () => {
      readCount++;
      return {
        myBookmakers: [16, 44],
        bookiehash: 'before-hash',
        otCode: 'token-before'
      };
    };
    browserContext.waitForBookmakerStateChange = async () => ({
      myBookmakers: [16, 44, 500],
      bookiehash: 'after-hash',
      otCode: 'token-after'
    });

    let retriggerCalls = 0;
    browserContext.retriggerArchiveRequest = async () => {
      retriggerCalls++;
      return { success: true, status: 200 };
    };

    const result = await browserContext.maybeForceUnlockJ1(
      'https://www.oddsportal.com/football/japan/j1-league-2026/results/'
    );

    assert.strictEqual(result.applied, true);
    assert.strictEqual(result.changed, true);
    assert.strictEqual(readCount, 1);
    assert.strictEqual(retriggerCalls, 1);
    assert.deepStrictEqual(result.after.myBookmakers, [16, 44, 500]);
  });

  it('close() 遇到挂死 context 时必须强制 SIGKILL 浏览器进程', async () => {
    const events = [];
    const killSignals = [];
    const browserProcess = {
      kill(signal) {
        killSignals.push(signal);
      }
    };

    const browser = {
      process() {
        return browserProcess;
      },
      async close() {
        events.push('browser.close');
      }
    };

    const context = {
      browser() {
        return browser;
      },
      async close() {
        events.push('context.close');
        return new Promise(() => {});
      }
    };

    const browserContext = new ReconBrowserContext({
      logger: { info() {}, warn() {}, error() {} },
      traceId: 'trace-close-timeout',
      chromium: { async launch() { throw new Error('not_used'); } },
      closeTimeoutMs: 10
    });

    browserContext.browser = browser;
    browserContext.context = context;
    browserContext.page = { isClosed: () => false };

    await browserContext.close();

    assert.deepStrictEqual(events, ['context.close', 'browser.close']);
    assert.deepStrictEqual(killSignals, ['SIGKILL']);
    assert.strictEqual(browserContext.browser, null);
    assert.strictEqual(browserContext.context, null);
    assert.strictEqual(browserContext.page, null);
  });

  it('close() 遇到 SIGKILL 权限错误时也必须继续 cleanupUserDataDir', async () => {
    const events = [];
    const browserProcess = {
      kill() {
        const error = new Error('operation not permitted');
        error.code = 'EPERM';
        throw error;
      }
    };

    const browser = {
      process() {
        return browserProcess;
      },
      async close() {
        events.push('browser.close');
      }
    };

    const context = {
      browser() {
        return browser;
      },
      async close() {
        events.push('context.close');
        return new Promise(() => {});
      }
    };

    let cleanedUserDataDir = null;
    const warnings = [];
    const browserContext = new ReconBrowserContext({
      logger: {
        info() {},
        warn(eventName, payload) {
          warnings.push({ eventName, payload });
        },
        error() {}
      },
      traceId: 'trace-close-kill-error',
      chromium: { async launch() { throw new Error('not_used'); } },
      closeTimeoutMs: 10,
      stealthProvider: {
        async applyStealthFingerprint() {},
        async cleanupUserDataDir(userDataDir) {
          cleanedUserDataDir = userDataDir;
        },
      }
    });

    browserContext.browser = browser;
    browserContext.context = context;
    browserContext.page = { isClosed: () => false };
    browserContext.userDataDir = '/tmp/recon-browser-context-test';

    await assert.doesNotReject(browserContext.close());

    assert.deepStrictEqual(events, ['context.close', 'browser.close']);
    assert.strictEqual(cleanedUserDataDir, '/tmp/recon-browser-context-test');
    assert.ok(warnings.some((entry) => (
      entry.eventName === 'recon_browser_context_process_kill_failed'
      && entry.payload?.error === 'operation not permitted'
    )));
  });
});
