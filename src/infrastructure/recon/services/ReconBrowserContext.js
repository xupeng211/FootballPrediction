'use strict';

const { chromium: playwrightChromium } = require('playwright');
const { RECON_CONFIG, getReconConfigSection } = require('./ReconServiceConfig');

const DEFAULT_CONSENT_LABELS = ['I Accept', 'Accept All', 'Accept', 'Allow All'];
const DEFAULT_READY_SELECTORS = [
  ...((RECON_CONFIG.oddsportal?.selectors?.match_row) || []),
  '.eventRow a[href]',
  '.pagination a[href]',
  'main',
  'body'
];
const DEFAULT_ACCEPT_LANGUAGE = 'en-US,en;q=0.9,ja-JP;q=0.8,ja;q=0.7';

class ReconBrowserContext {
  constructor(options = {}) {
    const runtimeConfig = getReconConfigSection(['recon_runtime', 'browser_context'], {});
    const networkMonitorConfig = getReconConfigSection(['recon_runtime', 'network_monitor'], {});

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
    this.navigationReadySelectors = Array.isArray(options.navigationReadySelectors) && options.navigationReadySelectors.length > 0
      ? [...options.navigationReadySelectors]
      : Array.isArray(runtimeConfig.navigation_ready_selectors) && runtimeConfig.navigation_ready_selectors.length > 0
        ? [...runtimeConfig.navigation_ready_selectors]
        : [...DEFAULT_READY_SELECTORS];
    this.navigationReadyTimeoutMs = Number(
      options.navigationReadyTimeoutMs
      ?? runtimeConfig.navigation_ready_timeout_ms
      ?? this.navigationTimeoutMs
    );
    this.homeWarmupEnabled = options.homeWarmupEnabled ?? networkMonitorConfig.home_warmup_enabled ?? false;
    this.homeWarmupUrl = String(
      options.homeWarmupUrl
      || networkMonitorConfig.home_warmup_url
      || RECON_CONFIG.oddsportal?.base_url
      || ''
    ).trim();
    this.homeWarmupWaitMs = Number(options.homeWarmupWaitMs ?? networkMonitorConfig.home_warmup_wait_ms ?? 5000);
    this.acceptLanguage = String(options.acceptLanguage || runtimeConfig.accept_language || DEFAULT_ACCEPT_LANGUAGE);
    this.locale = String(options.locale || runtimeConfig.locale || 'en-US');
    this.timezoneId = String(options.timezoneId || runtimeConfig.timezone_id || 'Asia/Tokyo');
    this.hardwareConcurrency = Number(options.hardwareConcurrency ?? runtimeConfig.hardware_concurrency ?? 8);
    this.deviceMemory = Number(options.deviceMemory ?? runtimeConfig.device_memory ?? 8);
    this.platform = String(options.platform || runtimeConfig.platform || 'MacIntel');
    this.enableStealthFingerprint = options.enableStealthFingerprint ?? runtimeConfig.enable_stealth_fingerprint ?? false;
    this._sessionPrimed = false;
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
        viewport: this.viewport,
        locale: this.locale,
        timezoneId: this.timezoneId,
        extraHTTPHeaders: {
          'accept-language': this.acceptLanguage
        }
      });
      page = await context.newPage();
      if (this.enableStealthFingerprint) {
        const hardwareConcurrency = this.hardwareConcurrency;
        const deviceMemory = this.deviceMemory;
        const platform = this.platform;
        await page.addInitScript(({ injectedHardwareConcurrency, injectedDeviceMemory, injectedPlatform }) => {
          Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
          Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => injectedHardwareConcurrency });
          Object.defineProperty(navigator, 'deviceMemory', { get: () => injectedDeviceMemory });
          Object.defineProperty(navigator, 'platform', { get: () => injectedPlatform });
          Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en', 'ja-JP', 'ja'] });
          Object.defineProperty(navigator, 'language', { get: () => 'en-US' });
          Object.defineProperty(navigator, 'plugins', {
            get: () => [
              { name: 'Chrome PDF Plugin' },
              { name: 'Chrome PDF Viewer' },
              { name: 'Native Client' }
            ]
          });
          window.chrome = window.chrome || { runtime: {} };
        }, {
          injectedHardwareConcurrency: hardwareConcurrency,
          injectedDeviceMemory: deviceMemory,
          injectedPlatform: platform
        });
      }

      this.browser = browser;
      this.context = context;
      this.page = page;
      this.isClosed = false;
      this._sessionPrimed = false;

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
    const waitUntil = options.waitUntil || 'domcontentloaded';
    const warmupDelayMs = options.warmupDelayMs ?? this.warmupDelayMs;

    await this.primeSession(url, { timeout, waitUntil });
    await this.page.goto(url, { timeout, waitUntil });
    await this.handleConsent();
    await this.waitForNavigationReady({
      selectors: options.readySelectors,
      timeout: options.readyTimeoutMs
    });
    await this.waitForKnownContent({
      selector: options.contentReadySelector,
      timeout: options.readyTimeoutMs
    });

    if (warmupDelayMs > 0) {
      await this.page.waitForTimeout(warmupDelayMs);
    }

    await this.triggerDataLoading({
      iterations: options.scrollIterations || this.scrollIterations,
      stepPx: options.scrollStepPx || this.scrollStepPx,
      delayMs: options.scrollDelayMs || this.scrollDelayMs
    });
  }

  async primeSession(targetUrl, options = {}) {
    if (
      this._sessionPrimed
      || !this.page
      || !this.homeWarmupEnabled
      || !this.homeWarmupUrl
      || !targetUrl
      || String(targetUrl).startsWith(this.homeWarmupUrl)
    ) {
      return;
    }

    const timeout = options.timeout || this.navigationTimeoutMs;
    const waitUntil = options.waitUntil || 'domcontentloaded';

    await this.page.goto(this.homeWarmupUrl, { timeout, waitUntil });
    await this.handleConsent();
    if (this.homeWarmupWaitMs > 0) {
      await this.page.waitForTimeout(this.homeWarmupWaitMs);
    }
    this._sessionPrimed = true;
  }

  async waitForKnownContent(options = {}) {
    if (!this.page || typeof this.page.waitForSelector !== 'function') {
      return false;
    }

    const selector = typeof options.selector === 'string' ? options.selector.trim() : '';
    if (!selector) {
      return false;
    }

    try {
      await this.page.waitForSelector(selector, {
        timeout: Number(options.timeout ?? this.navigationReadyTimeoutMs),
        state: 'visible'
      });
      return true;
    } catch (_error) {
      this.logger.warn('recon_known_content_selector_missed', {
        traceId: this.traceId,
        selector
      });
      return false;
    }
  }

  async waitForNavigationReady(options = {}) {
    if (!this.page || typeof this.page.waitForSelector !== 'function') {
      return false;
    }

    const selectors = Array.isArray(options.selectors) && options.selectors.length > 0
      ? options.selectors
      : this.navigationReadySelectors;
    const timeout = Number(options.timeout ?? this.navigationReadyTimeoutMs);

    for (const selector of selectors) {
      if (!selector || typeof selector !== 'string') {
        continue;
      }

      try {
        await this.page.waitForSelector(selector, {
          timeout,
          state: 'attached'
        });
        return true;
      } catch (_error) {
        // 尝试下一组选择器，直到命中首个稳定锚点
      }
    }

    this.logger.warn('recon_navigation_ready_selector_missed', {
      traceId: this.traceId,
      selectors,
      timeout
    });

    return false;
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
    this._sessionPrimed = false;

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
