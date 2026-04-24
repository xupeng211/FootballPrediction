'use strict';

const { afterEach, describe, test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');

const MODULE_PATH = path.resolve(__dirname, '../../src/infrastructure/services/BrowserProvider.js');
const PLAYWRIGHT_ID = require.resolve('playwright');

function overrideModule(moduleId, exportsValue) {
  const previous = require.cache[moduleId];
  require.cache[moduleId] = {
    id: moduleId,
    filename: moduleId,
    loaded: true,
    exports: exportsValue,
  };

  return () => {
    if (previous) {
      require.cache[moduleId] = previous;
    } else {
      delete require.cache[moduleId];
    }
  };
}

function loadBrowserProvider(fakeChromium) {
  const restorePlaywright = overrideModule(PLAYWRIGHT_ID, { chromium: fakeChromium });
  delete require.cache[MODULE_PATH];

  try {
    return require(MODULE_PATH);
  } finally {
    restorePlaywright();
  }
}

describe('src/infrastructure/services/BrowserProvider', () => {
  const originalSetTimeout = global.setTimeout;
  const originalFetch = global.fetch;
  const originalWindow = global.window;
  const originalDocument = global.document;

  afterEach(() => {
    global.setTimeout = originalSetTimeout;
    if (typeof originalFetch === 'undefined') {
      delete global.fetch;
    } else {
      global.fetch = originalFetch;
    }
    if (typeof originalWindow === 'undefined') {
      delete global.window;
    } else {
      global.window = originalWindow;
    }
    if (typeof originalDocument === 'undefined') {
      delete global.document;
    } else {
      global.document = originalDocument;
    }
    delete require.cache[MODULE_PATH];
  });

  test('应完成初始化、预热、页面操作与关闭流程', async () => {
    const infoLogs = [];
    const warnLogs = [];
    const errorLogs = [];
    const gotoCalls = [];
    const waitCalls = [];
    const evaluateCalls = [];
    let removedListeners = false;
    let browserClosed = false;

    const fakePage = {
      async goto(url, options) {
        gotoCalls.push({ url, options });
      },
      async evaluate(fn, payload) {
        const source = fn.toString();
        evaluateCalls.push({ source, payload });

        if (source.includes('window.scrollTo')) {
          return undefined;
        }
        if (source.includes('document.body.scrollHeight')) {
          return 777;
        }

        return payload?.apiUrl
          ? { success: true, data: { ok: true }, status: 200 }
          : 'eval-ok';
      },
      async waitForSelector(selector, options) {
        waitCalls.push({ selector, options });
      },
      url() {
        return 'https://www.fotmob.com/live';
      },
      removeAllListeners() {
        removedListeners = true;
      },
    };

    const fakeBrowser = {
      async newPage(options) {
        assert.deepStrictEqual(options, {
          viewport: { width: 1600, height: 900 },
          userAgent: 'UA-CUSTOM',
        });
        return fakePage;
      },
      async close() {
        browserClosed = true;
      },
    };

    const { BrowserProvider } = loadBrowserProvider({
      async launch(options) {
        assert.strictEqual(options.headless, false);
        assert.ok(options.args.includes('--no-sandbox'));
        return fakeBrowser;
      },
    });

    const provider = new BrowserProvider({
      logger: {
        info: message => infoLogs.push(message),
        warn: message => warnLogs.push(message),
        error: message => errorLogs.push(message),
      },
      headless: false,
      viewport: { width: 1600, height: 900 },
      userAgent: 'UA-CUSTOM',
      defaultTimeoutMs: 50,
    });

    assert.strictEqual(provider.isInitialized(), false);
    const page = await provider.initialize();
    assert.strictEqual(page, fakePage);
    assert.strictEqual(provider.isInitialized(), true);
    assert.strictEqual(await provider.initialize(), fakePage);
    assert.strictEqual(provider.getPage(), fakePage);
    assert.strictEqual(provider.getBrowser(), fakeBrowser);

    await provider.warmup('https://www.fotmob.com/', { waitUntil: 'networkidle', timeout: 1234 });
    assert.deepStrictEqual(gotoCalls[0], {
      url: 'https://www.fotmob.com/',
      options: {
        waitUntil: 'networkidle',
        timeout: 1234,
      },
    });

    const fetchResult = await provider.fetch('https://api.example.com/data', { timeout: 10 });
    assert.deepStrictEqual(fetchResult, { success: true, data: { ok: true }, status: 200 });

    assert.strictEqual(await provider.getCurrentUrl(), 'https://www.fotmob.com/live');
    await provider.goto('https://www.fotmob.com/match/1');
    assert.deepStrictEqual(gotoCalls[1], {
      url: 'https://www.fotmob.com/match/1',
      options: {
        waitUntil: 'domcontentloaded',
        timeout: 20000,
      },
    });

    assert.strictEqual(await provider.scroll({ to: 'bottom' }), 777);
    assert.strictEqual(await provider.scroll({ to: 'top' }), 777);
    assert.strictEqual(await provider.getPageHeight(), 777);

    await provider.waitForSelector('.match-row', { state: 'visible', timeout: 222 });
    assert.deepStrictEqual(waitCalls[0], {
      selector: '.match-row',
      options: {
        state: 'visible',
        timeout: 222,
      },
    });

    assert.strictEqual(await provider.evaluate(() => 'ok'), 'eval-ok');

    const sleepCalls = [];
    global.setTimeout = (callback, ms) => {
      sleepCalls.push(ms);
      callback();
      return 1;
    };
    await provider.sleep(25);
    assert.deepStrictEqual(sleepCalls, [25]);

    await provider.close();
    assert.strictEqual(removedListeners, true);
    assert.strictEqual(browserClosed, true);
    assert.strictEqual(provider.getPage(), null);
    assert.strictEqual(provider.getBrowser(), null);
    assert.strictEqual(infoLogs.some(message => message.includes('浏览器实例创建成功')), true);
    assert.strictEqual(warnLogs.length, 0);
    assert.strictEqual(errorLogs.length, 0);
    assert.ok(evaluateCalls.length >= 5);
  });

  test('接入 ProxyProvider 后应携带代理启动并在关闭时释放租约', async () => {
    const acquireCalls = [];
    const releaseCalls = [];
    let launchProxy = null;

    const fakeProxyProvider = {
      async acquire(options) {
        acquireCalls.push(options);
        return {
          id: 'LEASE-1',
          proxy: {
            host: '172.25.16.1',
            port: 7890,
            server: 'http://172.25.16.1:7890',
          },
        };
      },
      async release(leaseId) {
        releaseCalls.push(leaseId);
      },
      async reportSuccess() {},
      async reportFailure() {},
    };

    const fakeBrowser = {
      async newPage() {
        return {
          removeAllListeners() {},
        };
      },
      async close() {},
    };

    const { BrowserProvider } = loadBrowserProvider({
      async launch(options) {
        launchProxy = options.proxy;
        return fakeBrowser;
      },
    });

    const provider = new BrowserProvider({
      proxyProvider: fakeProxyProvider,
      proxyConsumer: 'l1-browser',
      proxySessionKey: 'worker-1',
    });

    await provider.initialize();
    await provider.close();

    assert.strictEqual(acquireCalls.length, 1);
    assert.strictEqual(acquireCalls[0].consumer, 'l1-browser');
    assert.deepStrictEqual(launchProxy, {
      server: 'http://172.25.16.1:7890',
    });
    assert.deepStrictEqual(releaseCalls, ['LEASE-1']);
  });

  test('固定代理模式应直接使用 fixedProxy 启动浏览器', async () => {
    let launchProxy = null;

    const fakeBrowser = {
      async newPage() {
        return {
          removeAllListeners() {},
        };
      },
      async close() {},
    };

    const { BrowserProvider } = loadBrowserProvider({
      async launch(options) {
        launchProxy = options.proxy;
        return fakeBrowser;
      },
    });

    const provider = new BrowserProvider({
      fixedProxy: {
        server: 'socks5://127.0.0.1:10001',
        port: 10001,
      },
    });

    await provider.initialize();
    await provider.close();

    assert.deepStrictEqual(launchProxy, {
      server: 'socks5://127.0.0.1:10001',
    });
  });

  test('初始化失败与页面预热失败时应记录错误/告警', async () => {
    const infoLogs = [];
    const warnLogs = [];
    const errorLogs = [];

    const { BrowserProvider } = loadBrowserProvider({
      async launch() {
        throw new Error('launch failed');
      },
    });

    const failingProvider = new BrowserProvider({
      logger: {
        info: message => infoLogs.push(message),
        warn: message => warnLogs.push(message),
        error: message => errorLogs.push(message),
      },
    });

    await assert.rejects(
      failingProvider.initialize(),
      /launch failed/,
    );
    assert.ok(errorLogs.some(message => message.includes('浏览器启动失败')));

    const fakePage = {
      async goto() {
        throw new Error('warmup failed');
      },
      removeAllListeners() {},
      url() {
        return '';
      },
      async evaluate() {
        return 0;
      },
      async waitForSelector() {},
    };
    const fakeBrowser = {
      async newPage() {
        return fakePage;
      },
      async close() {},
    };

    const { BrowserProvider: WarmupProvider } = loadBrowserProvider({
      async launch() {
        return fakeBrowser;
      },
    });

    const warmupProvider = new WarmupProvider({
      logger: {
        info: message => infoLogs.push(message),
        warn: message => warnLogs.push(message),
        error: message => errorLogs.push(message),
      },
    });

    await warmupProvider.initialize();
    await warmupProvider.warmup();
    assert.strictEqual(await warmupProvider.getCurrentUrl(), '');
    assert.strictEqual(await warmupProvider.getPageHeight(), 0);
    assert.ok(warnLogs.some(message => message.includes('页面预热警告')));
    assert.ok(warnLogs.some(message => message.includes('继续执行')));
  });

  test('预热失败后应废弃失败页并创建干净页', async () => {
    const warnLogs = [];
    let newPageCalls = 0;
    let failedPageClosed = false;

    const failedPage = {
      async goto() {
        throw new Error('page.goto: net::ERR_EMPTY_RESPONSE');
      },
      async waitForSelector() {},
      url() {
        return '';
      },
      removeAllListeners() {},
      async evaluate() {
        return 0;
      },
      async close() {
        failedPageClosed = true;
      },
      isClosed() {
        return false;
      }
    };

    const freshPage = {
      async goto() {},
      async waitForSelector() {},
      url() {
        return 'about:blank';
      },
      removeAllListeners() {},
      async evaluate() {
        return 0;
      },
      async close() {},
      isClosed() {
        return false;
      }
    };

    const fakeBrowser = {
      isConnected() {
        return true;
      },
      async newPage() {
        newPageCalls += 1;
        return newPageCalls === 1 ? failedPage : freshPage;
      },
      async close() {}
    };

    const { BrowserProvider } = loadBrowserProvider({
      async launch() {
        return fakeBrowser;
      }
    });

    const provider = new BrowserProvider({
      logger: {
        info() {},
        warn: message => warnLogs.push(message),
        error() {}
      }
    });

    try {
      await provider.initialize();
      await provider.warmup();

      assert.strictEqual(provider.getPage(), freshPage);
      assert.strictEqual(newPageCalls, 2);
      assert.strictEqual(failedPageClosed, true);
      assert.ok(warnLogs.some(message => message.includes('预热失败后已重置页面')));
    } finally {
      await provider.close();
    }
  });

  test('fetch/evaluate 应覆盖超时与空页面分支', async () => {
    const { BrowserProvider } = loadBrowserProvider({
      async launch() {
        return {
          async newPage() {
            return {
              async goto() {},
              async waitForSelector() {},
              url() {
                return 'about:blank';
              },
              removeAllListeners() {},
              async evaluate() {
                return new Promise(() => {});
              },
            };
          },
          async close() {},
        };
      },
    });

    const provider = new BrowserProvider({
      logger: { info() {}, warn() {}, error() {} },
      defaultTimeoutMs: 5,
    });

    global.setTimeout = (callback) => {
      callback();
      return 1;
    };

    await provider.initialize();
    assert.strictEqual(await provider.getCurrentUrl(), 'about:blank');
    await assert.rejects(
      provider.fetch('https://api.example.com/slow', { timeout: 5 }),
      /Browser fetch timeout after 5ms/,
    );
    await assert.rejects(
      provider.evaluate(() => 'slow'),
      /Browser evaluate timeout after 5ms/,
    );

    provider.page = null;
    provider.browser = null;
    assert.strictEqual(await provider.getCurrentUrl(), '');
    assert.strictEqual(await provider.scroll(), 0);
    assert.strictEqual(await provider.getPageHeight(), 0);
    assert.strictEqual(await provider.evaluate(() => 'noop'), null);
    await provider.waitForSelector('.noop');
    await provider.close();
  });

  test('fetch 在未初始化时应自动拉起浏览器', async () => {
    const launchCalls = [];
    const newPageCalls = [];
    const evaluatePayloads = [];
    const fetchCalls = [];

    const { BrowserProvider } = loadBrowserProvider({
      async launch() {
        launchCalls.push('launch');
        return {
          async newPage(options) {
            newPageCalls.push(options);
            return {
              async goto() {},
              async waitForSelector() {},
              url() {
                return 'about:blank';
              },
              removeAllListeners() {},
              async evaluate(fn, payload) {
                evaluatePayloads.push(payload);
                return fn(payload);
              },
            };
          },
          async close() {},
        };
      },
    });

    const provider = new BrowserProvider({
      logger: { info() {}, warn() {}, error() {} },
      defaultTimeoutMs: 15,
    });

    global.fetch = async (url, options) => {
      fetchCalls.push({ url, options });
      return {
        ok: true,
        status: 200,
        headers: { get: () => 'application/json' },
        async json() {
          return { initialized: true };
        },
      };
    };

    const result = await provider.fetch('https://api.example.com/lazy-init');
    assert.deepStrictEqual(result, {
      success: true,
      data: { initialized: true },
      status: 200,
    });
    assert.strictEqual(await provider.getCurrentUrl(), 'about:blank');
    assert.strictEqual(launchCalls.length, 1);
    assert.strictEqual(newPageCalls.length, 1);
    assert.deepStrictEqual(fetchCalls[0], {
      url: 'https://api.example.com/lazy-init',
      options: {
        method: 'GET',
        headers: {
          Accept: 'application/json, text/plain, */*',
          'Accept-Language': 'en-US,en;q=0.9',
          Referer: 'https://www.fotmob.com/',
        },
        credentials: 'include',
      },
    });
    assert.deepStrictEqual(evaluatePayloads[0], {
      apiUrl: 'https://api.example.com/lazy-init',
      opts: {
        method: 'GET',
        headers: {
          Accept: 'application/json, text/plain, */*',
          'Accept-Language': 'en-US,en;q=0.9',
          Referer: 'https://www.fotmob.com/',
        },
        credentials: 'include',
      },
    });
  });

  test('页面级软故障应上报为轻量失败分类，并支持页面恢复', async () => {
    const failureReports = [];
    const released = [];
    let pageSequence = 0;

    const fakeProxyProvider = {
      async acquire() {
        return {
          id: 'LEASE-1',
          proxy: {
            host: '127.0.0.1',
            port: 7890,
            server: 'http://127.0.0.1:7890'
          }
        };
      },
      async release(leaseId) {
        released.push(leaseId);
      },
      async reportSuccess() {},
      async reportFailure(_leaseId, metadata) {
        failureReports.push(metadata);
      }
    };

    const buildPage = () => ({
      id: ++pageSequence,
      async goto() {
        throw new Error('page.goto: net::ERR_EMPTY_RESPONSE');
      },
      async waitForSelector() {},
      url() {
        return 'about:blank';
      },
      removeAllListeners() {},
      async evaluate() {
        return 0;
      },
      async close() {},
      isClosed() {
        return false;
      }
    });

    const fakeBrowser = {
      async newPage() {
        return buildPage();
      },
      async close() {}
    };

    const { BrowserProvider } = loadBrowserProvider({
      async launch() {
        return fakeBrowser;
      }
    });

    const provider = new BrowserProvider({
      logger: { info() {}, warn() {}, error() {} },
      proxyProvider: fakeProxyProvider
    });

    await provider.initialize();
    await provider.warmup();
    await assert.rejects(
      provider.goto('https://www.fotmob.com/match/1'),
      /ERR_EMPTY_RESPONSE/
    );

    const recoveredPage = await provider.recoverPage('soft-failure');

    assert.equal(failureReports.length >= 2, true);
    assert.equal(failureReports[0].failureClass, 'upstream_block');
    assert.equal(failureReports[0].rotateProxy, false);
    assert.equal(recoveredPage.id, 3);

    await provider.close();
    assert.deepStrictEqual(released, ['LEASE-1']);
  });

  test('recoverPage 在 browser 已断连时应阻断 newPage 并重建 Browser 实例', async () => {
    const warnLogs = [];
    let launchCount = 0;
    let zombieNewPageCalls = 0;
    let zombieBrowserCloseCalls = 0;
    let zombieConnected = true;

    const zombiePage = {
      async goto() {},
      async waitForSelector() {},
      url() {
        return 'about:blank';
      },
      removeAllListeners() {},
      async evaluate() {
        return 0;
      },
      async close() {},
      isClosed() {
        return false;
      }
    };

    const freshPage = {
      async goto() {},
      async waitForSelector() {},
      url() {
        return 'about:blank';
      },
      removeAllListeners() {},
      async evaluate() {
        return 0;
      },
      async close() {},
      isClosed() {
        return false;
      }
    };

    const zombieBrowser = {
      isConnected() {
        return zombieConnected;
      },
      async newPage() {
        zombieNewPageCalls += 1;
        return zombiePage;
      },
      async close() {
        zombieBrowserCloseCalls += 1;
      }
    };

    const freshBrowser = {
      isConnected() {
        return true;
      },
      async newPage() {
        return freshPage;
      },
      async close() {}
    };

    const { BrowserProvider } = loadBrowserProvider({
      async launch() {
        launchCount += 1;
        return launchCount === 1 ? zombieBrowser : freshBrowser;
      }
    });

    const provider = new BrowserProvider({
      logger: {
        info() {},
        warn: (message) => warnLogs.push(message),
        error() {}
      }
    });

    try {
      const initialPage = await provider.initialize();
      assert.strictEqual(initialPage, zombiePage);

      zombieConnected = false;
      const recoveredPage = await provider.recoverPage('disconnected-browser');

      assert.strictEqual(recoveredPage, freshPage);
      assert.strictEqual(zombieNewPageCalls, 1);
      assert.strictEqual(zombieBrowserCloseCalls, 1);
      assert.strictEqual(launchCount, 2);
      assert.ok(warnLogs.some(message => message.includes('阻断僵尸 newPage')));
    } finally {
      await provider.close();
    }
  });

  test('recoverPage 在 newPage 命中关闭竞态时应回收旧实例并重建 Browser', async () => {
    const warnLogs = [];
    let launchCount = 0;
    let zombieNewPageCalls = 0;
    let zombieBrowserCloseCalls = 0;

    const zombiePage = {
      async goto() {},
      async waitForSelector() {},
      url() {
        return 'about:blank';
      },
      removeAllListeners() {},
      async evaluate() {
        return 0;
      },
      async close() {},
      isClosed() {
        return false;
      }
    };

    const freshPage = {
      async goto() {},
      async waitForSelector() {},
      url() {
        return 'about:blank';
      },
      removeAllListeners() {},
      async evaluate() {
        return 0;
      },
      async close() {},
      isClosed() {
        return false;
      }
    };

    const zombieBrowser = {
      isConnected() {
        return true;
      },
      async newPage() {
        zombieNewPageCalls += 1;
        if (zombieNewPageCalls === 1) {
          return zombiePage;
        }
        throw new Error('browser.newPage: Target page, context or browser has been closed');
      },
      async close() {
        zombieBrowserCloseCalls += 1;
      }
    };

    const freshBrowser = {
      isConnected() {
        return true;
      },
      async newPage() {
        return freshPage;
      },
      async close() {}
    };

    const { BrowserProvider } = loadBrowserProvider({
      async launch() {
        launchCount += 1;
        return launchCount === 1 ? zombieBrowser : freshBrowser;
      }
    });

    const provider = new BrowserProvider({
      logger: {
        info() {},
        warn: (message) => warnLogs.push(message),
        error() {}
      }
    });

    try {
      await provider.initialize();
      const recoveredPage = await provider.recoverPage('target-closed-race');

      assert.strictEqual(recoveredPage, freshPage);
      assert.strictEqual(zombieNewPageCalls, 2);
      assert.strictEqual(zombieBrowserCloseCalls, 1);
      assert.strictEqual(launchCount, 2);
      assert.ok(warnLogs.some(message => message.includes('newPage 命中关闭竞态')));
    } finally {
      await provider.close();
    }
  });

  test('共享 page 的导航与 fetch 应串行执行，避免恢复导航打断并发请求', async () => {
    const order = [];
    let releaseGoto = null;
    const gotoGate = new Promise(resolve => {
      releaseGoto = resolve;
    });

    const fakePage = {
      async goto() {
        order.push('goto-start');
        await gotoGate;
        order.push('goto-end');
      },
      async waitForSelector() {},
      url() {
        return 'about:blank';
      },
      removeAllListeners() {},
      async evaluate(_fn, payload) {
        if (payload?.apiUrl) {
          order.push('fetch-eval');
          return { success: true, status: 200, data: { ok: true } };
        }
        return 0;
      },
      async close() {},
      isClosed() {
        return false;
      }
    };

    const fakeBrowser = {
      async newPage() {
        return fakePage;
      },
      async close() {}
    };

    const { BrowserProvider } = loadBrowserProvider({
      async launch() {
        return fakeBrowser;
      }
    });

    const provider = new BrowserProvider({
      logger: { info() {}, warn() {}, error() {} }
    });

    try {
      await provider.initialize();

      const warmupPromise = provider.warmup('https://www.fotmob.com/');
      await new Promise(resolve => setImmediate(resolve));

      const fetchPromise = provider.fetch('https://api.example.com/serialized');
      await new Promise(resolve => setImmediate(resolve));

      assert.deepStrictEqual(order, ['goto-start']);

      releaseGoto();

      await warmupPromise;
      const fetchResult = await fetchPromise;

      assert.deepStrictEqual(fetchResult, { success: true, status: 200, data: { ok: true } });
      assert.deepStrictEqual(order, ['goto-start', 'goto-end', 'fetch-eval']);
    } finally {
      await provider.close();
    }
  });

  test('懒初始化与浏览器内 fetch 分支应覆盖默认 logger、HTTP 错误、HTML 响应和异常响应', async () => {
    const launchCalls = [];
    const gotoCalls = [];
    const fetchCalls = [];
    let scrollPosition = null;

    const fakePage = {
      async goto(url, options) {
        gotoCalls.push({ url, options });
      },
      async evaluate(fn, payload) {
        const source = fn.toString();
        if (payload?.apiUrl) {
          global.fetch = async (url, options) => {
            fetchCalls.push({ url, options });
            if (url.includes('/404')) {
              return {
                ok: false,
                status: 404,
                headers: { get: () => 'application/json' },
              };
            }
            if (url.includes('/html')) {
              return {
                ok: true,
                status: 200,
                headers: { get: () => 'text/html; charset=utf-8' },
              };
            }
            if (url.includes('/throw')) {
              throw new Error('network exploded');
            }
            return {
              ok: true,
              status: 200,
              headers: { get: () => 'application/json' },
              async json() {
                return { ok: true, echo: options.method };
              },
            };
          };
          return fn(payload);
        }

        if (source.includes('window.scrollTo')) {
          global.document = { body: { scrollHeight: 321 } };
          global.window = {
            scrollTo(x, y) {
              scrollPosition = [x, y];
            },
          };
          return fn();
        }

        if (source.includes('document.body.scrollHeight')) {
          global.document = { body: { scrollHeight: 321 } };
          return fn();
        }

        return fn();
      },
      async waitForSelector() {},
      url() {
        return 'https://www.fotmob.com/home';
      },
      removeAllListeners() {},
    };

    const fakeBrowser = {
      async newPage() {
        return fakePage;
      },
      async close() {},
    };

    const { BrowserProvider } = loadBrowserProvider({
      async launch(options) {
        launchCalls.push(options);
        return fakeBrowser;
      },
    });

    const provider = new BrowserProvider({ defaultTimeoutMs: 25 });
    provider.logger.info('noop');
    provider.logger.warn('noop');
    provider.logger.error('noop');

    await provider.warmup('https://www.fotmob.com/bootstrap');
    assert.strictEqual(launchCalls.length, 1);
    assert.strictEqual(await provider.getCurrentUrl(), 'https://www.fotmob.com/home');
    assert.deepStrictEqual(gotoCalls[0], {
      url: 'https://www.fotmob.com/bootstrap',
      options: {
        waitUntil: 'domcontentloaded',
        timeout: 15000,
      },
    });

    const okResult = await provider.fetch('https://api.example.com/ok', { method: 'POST' });
    assert.deepStrictEqual(okResult, { success: true, data: { ok: true, echo: 'POST' }, status: 200 });

    const httpError = await provider.fetch('https://api.example.com/404');
    assert.deepStrictEqual(httpError, { error: 'HTTP 404', status: 404 });

    const htmlError = await provider.fetch('https://api.example.com/html');
    assert.deepStrictEqual(htmlError, {
      error: 'Received HTML instead of JSON',
      isHtml: true,
      status: 200,
    });

    const thrownError = await provider.fetch('https://api.example.com/throw');
    assert.deepStrictEqual(thrownError, { error: 'network exploded' });
    assert.strictEqual(await provider.evaluate(() => 'browser-ok'), 'browser-ok');

    provider.page = null;
    await provider.goto('https://www.fotmob.com/match/2', { timeout: 4321 });
    assert.strictEqual(launchCalls.length, 1);
    assert.deepStrictEqual(gotoCalls[1], {
      url: 'https://www.fotmob.com/match/2',
      options: {
        waitUntil: 'domcontentloaded',
        timeout: 4321,
      },
    });

    assert.strictEqual(await provider.scroll({ to: 'bottom' }), 321);
    assert.deepStrictEqual(scrollPosition, [0, 321]);
    assert.strictEqual(await provider.scroll({ to: 'top' }), 321);
    assert.deepStrictEqual(scrollPosition, [0, 0]);

    assert.strictEqual(fetchCalls.length >= 4, true);
  });
});
