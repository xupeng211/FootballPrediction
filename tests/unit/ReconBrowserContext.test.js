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
      async newPage() {
        events.push('newPage');
        return page;
      }
    };

    const browser = {
      async newContext(options) {
        events.push({ type: 'newContext', options });
        return context;
      },
      async close() {
        events.push('browser.close');
      }
    };

    const chromium = {
      async launch(options) {
        events.push({ type: 'launch', options });
        return browser;
      }
    };

    const browserContext = new ReconBrowserContext({
      logger: { info() {}, warn() {}, error() {} },
      traceId: 'trace-browser',
      chromium,
      headless: true,
      proxy: { host: '127.0.0.1', port: 8899 }
    });

    const launchedPage = await browserContext.launch({ timeout: 4321 });

    assert.strictEqual(launchedPage, page);
    assert.strictEqual(browserContext.browser, browser);
    assert.strictEqual(browserContext.context, context);
    assert.strictEqual(browserContext.page, page);
    assert.deepStrictEqual(events[0], {
      type: 'launch',
      options: {
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox'],
        timeout: 4321,
        proxy: { server: 'http://127.0.0.1:8899' }
      }
    });
    assert.deepStrictEqual(events[1], {
      type: 'newContext',
      options: {
        userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        viewport: { width: 1920, height: 1080 }
      }
    });
    assert.strictEqual(events[2], 'newPage');
    assert.deepStrictEqual(events[3], { type: 'addInitScript', value: 'function' });

    await browserContext.close();

    assert.strictEqual(browserContext.browser, null);
    assert.strictEqual(browserContext.context, null);
    assert.strictEqual(browserContext.page, null);
    assert.strictEqual(browserContext.isClosed, true);
    assert.strictEqual(events[4], 'browser.close');
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
    assert.deepStrictEqual(events[1], {
      type: 'waitForSelector',
      selector: '.ready-selector',
      options: {
        timeout: 5000,
        state: 'attached'
      }
    });
  });
});
