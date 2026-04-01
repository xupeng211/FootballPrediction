'use strict';

const { chromium: playwrightChromium } = require('playwright');
const { ReconBookmakerUnlocker } = require('./ReconBookmakerUnlocker');
const {
  ReconStealthProvider,
  DEFAULT_ACCEPT_LANGUAGE,
  DEFAULT_CONSENT_LABELS
} = require('./ReconStealthProvider');
const { RECON_CONFIG, getReconConfigSection } = require('./ReconServiceConfig');
const { ReconSessionManager } = require('./ReconSessionManager');

const DEFAULT_READY_SELECTORS = [
  ...((RECON_CONFIG.oddsportal?.selectors?.match_row) || []),
  '.eventRow a[href]',
  '.pagination a[href]',
  'main',
  'body'
];

function resolveList(primary, secondary, fallback) {
  if (Array.isArray(primary) && primary.length > 0) {
    return [...primary];
  }
  if (Array.isArray(secondary) && secondary.length > 0) {
    return [...secondary];
  }
  return [...fallback];
}

function pageClosed(page) { return !page || (typeof page.isClosed === 'function' && page.isClosed()); }

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
    this.navigationReadySelectors = resolveList(
      options.navigationReadySelectors,
      runtimeConfig.navigation_ready_selectors,
      DEFAULT_READY_SELECTORS
    );
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
    this.externalSessionPath = String(options.externalSessionPath || runtimeConfig.external_session_path || '');
    this.preferFullChromium = options.preferFullChromium ?? runtimeConfig.prefer_full_chromium ?? false;
    this.persistentProfileEnabled = options.persistentProfileEnabled ?? runtimeConfig.persistent_profile_enabled ?? true;
    this.playwrightCacheRoot = String(options.playwrightCacheRoot || runtimeConfig.playwright_cache_root || '/root/.cache/ms-playwright');
    this.userDataDirRoot = String(options.userDataDirRoot || runtimeConfig.user_data_dir_root || '');
    this.stealthProvider = options.stealthProvider || new ReconStealthProvider({
      logger: this.logger,
      traceId: this.traceId,
      hardwareConcurrency: this.hardwareConcurrency,
      deviceMemory: this.deviceMemory,
      platform: this.platform,
      userDataDirRoot: this.userDataDirRoot,
      playwrightCacheRoot: this.playwrightCacheRoot
    });
    this.resolvePreferredExecutablePath = options.resolvePreferredExecutablePath
      || (() => this.stealthProvider.resolvePreferredExecutablePath());
    this.userDataDir = null;
    this.sessionManager = options.sessionManager || new ReconSessionManager({
      logger: this.logger,
      traceId: this.traceId,
      sessionPath: this.externalSessionPath,
      defaultSourceUrl: RECON_CONFIG.oddsportal?.base_url
    });
    this.bookmakerUnlocker = options.bookmakerUnlocker || new ReconBookmakerUnlocker({
      logger: this.logger,
      traceId: this.traceId,
      forceUnlockJ1: options.forceUnlockJ1 || runtimeConfig.force_unlock_j1 || {}
    });
    this.forceUnlockJ1 = this.bookmakerUnlocker.config;
    this._sessionPrimed = false;
    this.consentLabels = resolveList(options.consentLabels, runtimeConfig.consent_labels, DEFAULT_CONSENT_LABELS);
  }

  buildLaunchOptions(options = {}) {
    const launchOptions = {
      headless: this.headless,
      args: this.launchArgs,
      timeout: options.timeout || this.launchTimeoutMs
    };

    if (this.proxy?.host && this.proxy?.port) {
      launchOptions.proxy = { server: `http://${this.proxy.host}:${this.proxy.port}` };
    }

    if (!options.executablePath && this.preferFullChromium) {
      const executablePath = this.resolvePreferredExecutablePath();
      if (executablePath) {
        launchOptions.executablePath = executablePath;
        this.logger.info('recon_browser_full_chromium_selected', {
          traceId: this.traceId,
          executablePath
        });
      } else {
        this.logger.debug('recon_browser_full_chromium_unavailable', {
          traceId: this.traceId,
          cacheRoot: this.playwrightCacheRoot
        });
      }
    }

    return launchOptions;
  }

  async launch(options = {}) {
    const launchOptions = options.launchOptions || this.buildLaunchOptions(options);
    const externalSession = this.sessionManager.load();
    const sessionHeaders = externalSession?.extraHTTPHeaders || {};
    const contextUserAgent = externalSession?.userAgent || this.userAgent;
    const acceptLanguage = sessionHeaders['accept-language'] || this.acceptLanguage;

    let browser = null;
    let context = null;
    let page = null;
    let userDataDir = null;

    try {
      const contextOptions = {
        userAgent: contextUserAgent,
        viewport: this.viewport,
        locale: this.locale,
        timezoneId: this.timezoneId,
        extraHTTPHeaders: {
          ...sessionHeaders,
          'accept-language': acceptLanguage,
          ...(contextUserAgent ? { 'user-agent': contextUserAgent } : {})
        }
      };

      if (this.persistentProfileEnabled && typeof this.chromium.launchPersistentContext === 'function') {
        userDataDir = await this.stealthProvider.createUserDataDir();
        context = await this.chromium.launchPersistentContext(userDataDir, {
          ...launchOptions,
          ...contextOptions
        });
        browser = typeof context.browser === 'function' ? context.browser() : null;
        this.userDataDir = userDataDir;
        this.logger.info('recon_browser_context_profile_created', {
          traceId: this.traceId,
          userDataDir
        });
      } else {
        browser = await this.chromium.launch(launchOptions);
        context = await browser.newContext(contextOptions);
      }

      await this.injectExternalSession(context, externalSession);
      page = await context.newPage();
      await this.stealthProvider.applyStealthFingerprint(page, this.enableStealthFingerprint);

      this.browser = browser;
      this.context = context;
      this.page = page;
      this.isClosed = false;
      this._sessionPrimed = false;
      return this.page;
    } catch (error) {
      await this._cleanupPartialLaunch(browser, context, page);
      if (userDataDir) {
        this.userDataDir = null;
        await this.stealthProvider.cleanupUserDataDir(userDataDir);
      }
      this.browser = null;
      this.context = null;
      this.page = null;
      this.isClosed = true;
      throw error;
    }
  }

  async injectExternalSession(context = this.context, sessionSnapshot = null) {
    if (!context || typeof context.addCookies !== 'function') {
      return { applied: false, cookies: 0, sourceFormat: 'unavailable' };
    }

    const snapshot = sessionSnapshot || this.sessionManager.load();
    const cookies = Array.isArray(snapshot?.cookies) ? snapshot.cookies : [];
    if (cookies.length === 0) {
      return {
        applied: false,
        cookies: 0,
        sourceFormat: snapshot?.sourceFormat || 'empty'
      };
    }

    await context.addCookies(cookies);
    this.logger.info('recon_external_session_injected', {
      traceId: this.traceId,
      sourceFormat: snapshot?.sourceFormat || 'unknown',
      cookies: cookies.length
    });
    return {
      applied: true,
      cookies: cookies.length,
      sourceFormat: snapshot?.sourceFormat || 'unknown'
    };
  }

  isHealthy() {
    try {
      return Boolean(
        this.browser
        && typeof this.browser.isConnected === 'function'
        && this.browser.isConnected()
        && this.context
        && this.page
        && !pageClosed(this.page)
      );
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
    await this.primeSession(url, { timeout, waitUntil });
    await this.page.goto(url, { timeout, waitUntil });
    await this.handleConsent();
    if (pageClosed(this.page)) {
      return;
    }

    await this.waitForNavigationReady({
      selectors: options.readySelectors,
      timeout: options.readyTimeoutMs
    });
    if (pageClosed(this.page)) {
      return;
    }

    await this.waitForKnownContent({
      selector: options.contentReadySelector,
      timeout: options.readyTimeoutMs
    });
    if (pageClosed(this.page)) {
      return;
    }

    const warmupDelayMs = options.warmupDelayMs ?? this.warmupDelayMs;
    if (warmupDelayMs > 0) {
      await this.page.waitForTimeout(warmupDelayMs);
    }
    if (pageClosed(this.page)) {
      return;
    }

    await this.triggerDataLoading({
      iterations: options.scrollIterations || this.scrollIterations,
      stepPx: options.scrollStepPx || this.scrollStepPx,
      delayMs: options.scrollDelayMs || this.scrollDelayMs
    });
    if (pageClosed(this.page)) {
      return;
    }

    await this.maybeForceUnlockJ1(url);
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

    await this.page.goto(this.homeWarmupUrl, {
      timeout: options.timeout || this.navigationTimeoutMs,
      waitUntil: options.waitUntil || 'domcontentloaded'
    });
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

    const selectors = resolveList(options.selectors, this.navigationReadySelectors, this.navigationReadySelectors);
    const timeout = Number(options.timeout ?? this.navigationReadyTimeoutMs);

    for (const selector of selectors) {
      if (!selector || typeof selector !== 'string') {
        continue;
      }

      try {
        await this.page.waitForSelector(selector, { timeout, state: 'attached' });
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

  shouldForceUnlockJ1(url) {
    return this.bookmakerUnlocker.shouldForceUnlockJ1(url);
  }

  async maybeForceUnlockJ1(url) {
    return this.bookmakerUnlocker.maybeForceUnlockJ1(this.page, url, {
      shouldForceUnlockJ1: (targetUrl) => this.shouldForceUnlockJ1(targetUrl),
      readBookmakerState: () => this.readBookmakerState(),
      openBookmakerMenu: () => this.openBookmakerMenu(),
      applyBookmakerSelection: () => this.applyBookmakerSelection(),
      waitForBookmakerStateChange: (beforeState, timeoutMs) => this.waitForBookmakerStateChange(beforeState, timeoutMs),
      retriggerArchiveRequest: (options) => this.retriggerArchiveRequest(options)
    });
  }

  async openBookmakerMenu() {
    return this.bookmakerUnlocker.openBookmakerMenu(this.page);
  }

  async applyBookmakerSelection() {
    return this.bookmakerUnlocker.applyBookmakerSelection(this.page);
  }

  async readBookmakerState() {
    return this.bookmakerUnlocker.readBookmakerState(this.page);
  }

  async waitForBookmakerStateChange(beforeState, timeoutMs) {
    return this.bookmakerUnlocker.waitForBookmakerStateChange(this.page, beforeState, timeoutMs);
  }

  async retriggerArchiveRequest(options = {}) {
    return this.bookmakerUnlocker.retriggerArchiveRequest(this.page, options);
  }

  async handleConsent() {
    return this.stealthProvider.dismissConsent(this.page, {
      labels: this.consentLabels,
      visibilityTimeoutMs: this.consentVisibilityTimeoutMs,
      clickTimeoutMs: this.consentClickTimeoutMs,
      postClickWaitMs: this.consentPostClickWaitMs
    });
  }

  async close() {
    this.isClosed = true;

    const browser = this.browser;
    const context = this.context;
    const userDataDir = this.userDataDir;
    this.browser = null;
    this.context = null;
    this.page = null;
    this.userDataDir = null;
    this._sessionPrimed = false;

    if (context && typeof context.close === 'function') {
      try {
        await context.close();
      } catch (error) {
        this.logger.warn('recon_browser_context_close_failed', {
          traceId: this.traceId,
          error: error.message
        });
      }
    }

    if (browser && browser !== context && typeof browser.close === 'function') {
      try {
        await browser.close();
      } catch (error) {
        this.logger.warn('recon_browser_context_close_failed', {
          traceId: this.traceId,
          error: error.message
        });
      }
    }

    await this.stealthProvider.cleanupUserDataDir(userDataDir);
  }

  async _cleanupPartialLaunch(browser, context, page) {
    for (const target of [page, context, browser]) {
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

module.exports = { ReconBrowserContext };
