'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { ReconBrowserContext } = require('../../src/infrastructure/recon/services/ReconBrowserContext');

describe('ReconBrowserContext', () => {
  it('应独立完成 launch 与 close 生命周期', async () => {
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
        args: ['--no-sandbox', '--disable-setuid-sandbox'],
        timeout: 4321,
        userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        viewport: { width: 1920, height: 1080 },
        locale: 'en-US',
        timezoneId: 'Asia/Tokyo',
        proxy: { server: 'http://127.0.0.1:8899' },
        extraHTTPHeaders: {
          'accept-language': 'en-US,en;q=0.9,ja-JP;q=0.8,ja;q=0.7',
          'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
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

  it('启用高仿真指纹时才应注入 addInitScript', async () => {
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

    assert.deepStrictEqual(events, [{ type: 'addInitScript', value: 'function' }]);
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

  it('launch 后应自动注入 external session cookies，并用外部 UA 对齐 context', async () => {
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
    assert.strictEqual(events[0].options.userAgent, 'External-UA/1.0');
    assert.strictEqual(events[0].options.extraHTTPHeaders['user-agent'], 'External-UA/1.0');
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
      if (readCount === 1) {
        return {
          myBookmakers: [16, 44],
          bookiehash: 'before-hash',
          otCode: 'token-before'
        };
      }

      return {
        myBookmakers: [16, 44, 500],
        bookiehash: 'after-hash',
        otCode: 'token-after'
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
    assert.strictEqual(retriggerCalls, 1);
    assert.deepStrictEqual(result.after.myBookmakers, [16, 44, 500]);
  });
});
