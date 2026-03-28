'use strict';

const { chromium: playwrightChromium } = require('playwright');
const { getReconConfigSection } = require('./ReconServiceConfig');

const DEFAULT_CONSENT_LABELS = ['I Accept', 'Accept All', 'Accept', 'Allow All'];

class ReconBrowserContext {
  constructor(options = {}) {
    const runtimeConfig = getReconConfigSection(['recon_runtime', 'browser_context'], {});

    this.logger = options.logger || console;
    this.traceId = options.traceId || 'trace-unknown';
    this.chromium = options.chromium || playwrightChromium;
    this.headless = options.headless !== false;
    this.proxy = options.proxy;
    this.browser = null;
    this.context = null;
    this.page = null;
    this.isClosed = false;
    this.launchTimeoutMs = Number(options.launchTimeoutMs ?? runtimeConfig.launch_timeout_ms);
    this.navigationTimeoutMs = Number(options.navigationTimeoutMs ?? runtimeConfig.navigation_timeout_ms);
    this.userAgent = options.userAgent || runtimeConfig.user_agent;
    this.viewport = options.viewport || runtimeConfig.viewport;
    this.launchArgs = Array.isArray(options.launchArgs)
      ? options.launchArgs
      : Array.isArray(runtimeConfig.launch_args)
        ? runtimeConfig.launch_args
        : [];
    this.warmupDelayMs = Number(options.warmupDelayMs ?? runtimeConfig.warmup_delay_ms);
    this.scrollIterations = Number(options.scrollIterations ?? runtimeConfig.scroll_iterations);
    this.scrollStepPx = Number(options.scrollStepPx ?? runtimeConfig.scroll_step_px);
    this.scrollDelayMs = Number(options.scrollDelayMs ?? runtimeConfig.scroll_delay_ms);
    this.consentVisibilityTimeoutMs = Number(options.consentVisibilityTimeoutMs ?? runtimeConfig.consent_visibility_timeout_ms);
    this.consentClickTimeoutMs = Number(options.consentClickTimeoutMs ?? runtimeConfig.consent_click_timeout_ms);
    this.consentPostClickWaitMs = Number(options.consentPostClickWaitMs ?? runtimeConfig.consent_post_click_wait_ms);
    this.consentLabels = Array.isArray(options.consentLabels) && options.consentLabels.length > 0
      ? [...options.consentLabels]
      : Array.isArray(runtimeConfig.consent_labels) && runtimeConfig.consent_labels.length > 0
        ? [...runtimeConfig.consent_labels]
        : [...DEFAULT_CONSENT_LABELS];
  }

  buildLaunchOptions(options = {}) {
    const timeout = options.timeout || this.launchTimeoutMs;
    const proxy = options.proxy || this.proxy;
    const launchOptions = {
      headless: this.headless,
      args: this.launchArgs,
      timeout
    };

    if (proxy?.host && proxy?.port) {
      launchOptions.proxy = { server: `http://${proxy.host}:${proxy.port}` };
    }

    return launchOptions;
  }

  async launch(options = {}) {
    const launchOptions = options.launchOptions || this.buildLaunchOptions(options);

    let browser = null;
    let context = null;
    let page = null;

    try {
      browser = await this.chromium.launch(launchOptions);
      context = await browser.newContext({
        userAgent: this.userAgent,
        viewport: this.viewport
      });
      page = await context.newPage();
      await page.addInitScript(() => {
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
      });

      this.browser = browser;
      this.context = context;
      this.page = page;
      this.isClosed = false;

      return this.page;
    } catch (error) {
      await this._cleanupPartialLaunch(browser, context, page);
      this.browser = null;
      this.context = null;
      this.page = null;
      this.isClosed = true;
      throw error;
    }
  }

  isHealthy() {
    try {
      if (!this.browser || typeof this.browser.isConnected !== 'function' || !this.browser.isConnected()) {
        return false;
      }

      if (!this.context || !this.page) {
        return false;
      }

      if (typeof this.page.isClosed === 'function' && this.page.isClosed()) {
        return false;
      }

      return true;
    } catch (_error) {
      return false;
    }
  }

  async navigate(url, options = {}) {
    if (!this.page) {
      throw new Error('browser_page_unavailable');
    }

    const timeout = options.timeout || this.navigationTimeoutMs;
    const waitUntil = options.waitUntil || 'networkidle';
    const warmupDelayMs = options.warmupDelayMs ?? this.warmupDelayMs;

    await this.page.goto(url, { timeout, waitUntil });
    await this.handleConsent();

    if (warmupDelayMs > 0) {
      await this.page.waitForTimeout(warmupDelayMs);
    }

    await this.triggerDataLoading({
      iterations: options.scrollIterations || this.scrollIterations,
      stepPx: options.scrollStepPx || this.scrollStepPx,
      delayMs: options.scrollDelayMs || this.scrollDelayMs
    });
  }

  async triggerDataLoading(options = {}) {
    if (!this.page) {
      return;
    }

    const iterations = options.iterations || this.scrollIterations;
    const stepPx = options.stepPx || this.scrollStepPx;
    const delayMs = options.delayMs || this.scrollDelayMs;

    for (let i = 0; i < iterations; i++) {
      await this.page.evaluate((amount) => window.scrollBy(0, amount), stepPx);
      await this.page.waitForTimeout(delayMs);
    }
  }

  async handleConsent() {
    if (!this.page || typeof this.page.getByRole !== 'function') {
      return false;
    }

    for (const label of this.consentLabels) {
      try {
        const button = this.page.getByRole('button', { name: label }).first();
        if (await button.isVisible({ timeout: this.consentVisibilityTimeoutMs })) {
          await button.click({ timeout: this.consentClickTimeoutMs });
          await this.page.waitForTimeout(this.consentPostClickWaitMs);
          this.logger.info('consent_dismissed', { traceId: this.traceId, label });
          return true;
        }
      } catch (_error) {
        // 当前标签未命中时继续探测下一个按钮
      }
    }

    return false;
  }

  async close() {
    this.isClosed = true;

    const browser = this.browser;
    this.browser = null;
    this.context = null;
    this.page = null;

    if (!browser || typeof browser.close !== 'function') {
      return;
    }

    try {
      await browser.close();
    } catch (error) {
      this.logger.warn('recon_browser_context_close_failed', {
        traceId: this.traceId,
        error: error.message
      });
    }
  }

  async _cleanupPartialLaunch(browser, context, page) {
    const closers = [page, context, browser];

    for (const target of closers) {
      if (!target || typeof target.close !== 'function') {
        continue;
      }

      try {
        await target.close();
      } catch (_error) {
        // 启动补偿阶段不再抛出二次清理异常
      }
    }
  }
}

module.exports = {
  ReconBrowserContext
};
