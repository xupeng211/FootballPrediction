'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { chromium: playwrightChromium } = require('playwright');
const { RECON_CONFIG, getReconConfigSection } = require('./ReconServiceConfig');
const { ReconSessionManager } = require('./ReconSessionManager');

const DEFAULT_CONSENT_LABELS = ['I Accept', 'Accept All', 'Accept', 'Allow All'];
const DEFAULT_READY_SELECTORS = [
  ...((RECON_CONFIG.oddsportal?.selectors?.match_row) || []),
  '.eventRow a[href]',
  '.pagination a[href]',
  'main',
  'body'
];
const DEFAULT_ACCEPT_LANGUAGE = 'en-US,en;q=0.9,ja-JP;q=0.8,ja;q=0.7';
const DEFAULT_FORCE_UNLOCK_J1_URL_PATTERNS = ['/football/japan/j1-league'];
const DEFAULT_FORCE_UNLOCK_J1_MENU_LABELS = ['BOOKMAKERS', 'Bookmakers'];
const DEFAULT_FORCE_UNLOCK_J1_SELECT_ALL_LABELS = ['Select All'];
const DEFAULT_FORCE_UNLOCK_J1_BOOKMAKERS = ['Bet365', 'Pinnacle', '1xBet', 'William Hill'];

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
    this.externalSessionPath = String(options.externalSessionPath || runtimeConfig.external_session_path || '');
    this.preferFullChromium = options.preferFullChromium ?? runtimeConfig.prefer_full_chromium ?? false;
    this.playwrightCacheRoot = String(
      options.playwrightCacheRoot
      || runtimeConfig.playwright_cache_root
      || '/root/.cache/ms-playwright'
    );
    this.resolvePreferredExecutablePath = options.resolvePreferredExecutablePath
      || (() => this._resolvePreferredExecutablePath());
    this.sessionManager = options.sessionManager || new ReconSessionManager({
      logger: this.logger,
      traceId: this.traceId,
      sessionPath: this.externalSessionPath,
      defaultSourceUrl: RECON_CONFIG.oddsportal?.base_url
    });
    const forceUnlockJ1Config = options.forceUnlockJ1 || runtimeConfig.force_unlock_j1 || {};
    this.forceUnlockJ1 = {
      enabled: forceUnlockJ1Config.enabled === true,
      urlPatterns: Array.isArray(forceUnlockJ1Config.url_patterns) && forceUnlockJ1Config.url_patterns.length > 0
        ? [...forceUnlockJ1Config.url_patterns]
        : [...DEFAULT_FORCE_UNLOCK_J1_URL_PATTERNS],
      menuLabels: Array.isArray(forceUnlockJ1Config.menu_labels) && forceUnlockJ1Config.menu_labels.length > 0
        ? [...forceUnlockJ1Config.menu_labels]
        : [...DEFAULT_FORCE_UNLOCK_J1_MENU_LABELS],
      selectAllLabels: Array.isArray(forceUnlockJ1Config.select_all_labels) && forceUnlockJ1Config.select_all_labels.length > 0
        ? [...forceUnlockJ1Config.select_all_labels]
        : [...DEFAULT_FORCE_UNLOCK_J1_SELECT_ALL_LABELS],
      fallbackBookmakers: Array.isArray(forceUnlockJ1Config.fallback_bookmakers) && forceUnlockJ1Config.fallback_bookmakers.length > 0
        ? [...forceUnlockJ1Config.fallback_bookmakers]
        : [...DEFAULT_FORCE_UNLOCK_J1_BOOKMAKERS],
      openWaitMs: Number(forceUnlockJ1Config.open_wait_ms ?? 1200),
      postSelectWaitMs: Number(forceUnlockJ1Config.post_select_wait_ms ?? 1800),
      stateWaitMs: Number(forceUnlockJ1Config.state_wait_ms ?? 5000),
      retriggerTimeoutMs: Number(forceUnlockJ1Config.retrigger_timeout_ms ?? 10000)
    };
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

  _resolvePreferredExecutablePath() {
    try {
      if (!this.playwrightCacheRoot || !fs.existsSync(this.playwrightCacheRoot)) {
        return '';
      }

      const entries = fs.readdirSync(this.playwrightCacheRoot, { withFileTypes: true })
        .filter((entry) => entry.isDirectory() && /^chromium-\d+$/i.test(entry.name))
        .map((entry) => entry.name)
        .sort((left, right) => right.localeCompare(left, 'en'));

      for (const entry of entries) {
        const candidate = path.join(this.playwrightCacheRoot, entry, 'chrome-linux64', 'chrome');
        if (fs.existsSync(candidate)) {
          return candidate;
        }
      }
    } catch (error) {
      this.logger.warn('recon_browser_full_chromium_scan_failed', {
        traceId: this.traceId,
        error: error.message
      });
    }

    return '';
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

    try {
      browser = await this.chromium.launch(launchOptions);
      context = await browser.newContext({
        userAgent: contextUserAgent,
        viewport: this.viewport,
        locale: this.locale,
        timezoneId: this.timezoneId,
        extraHTTPHeaders: {
          ...sessionHeaders,
          'accept-language': acceptLanguage,
          ...(contextUserAgent ? { 'user-agent': contextUserAgent } : {})
        }
      });
      await this.injectExternalSession(context, externalSession);
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

  async injectExternalSession(context = this.context, sessionSnapshot = null) {
    if (!context || typeof context.addCookies !== 'function') {
      return {
        applied: false,
        cookies: 0,
        sourceFormat: 'unavailable'
      };
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

  shouldForceUnlockJ1(url) {
    if (!this.forceUnlockJ1.enabled) {
      return false;
    }

    const currentUrl = String(url || '').trim().toLowerCase();
    if (!currentUrl) {
      return false;
    }

    return this.forceUnlockJ1.urlPatterns.some((pattern) => currentUrl.includes(String(pattern || '').trim().toLowerCase()));
  }

  async maybeForceUnlockJ1(url) {
    if (!this.page || !this.shouldForceUnlockJ1(url)) {
      return {
        applied: false,
        reason: 'not_applicable'
      };
    }

    const before = await this.readBookmakerState();
    const menuOpened = await this.openBookmakerMenu();
    if (!menuOpened) {
      this.logger.warn('recon_force_unlock_j1_menu_missing', {
        traceId: this.traceId,
        url
      });
      return {
        applied: false,
        reason: 'menu_missing',
        before
      };
    }

    if (this.forceUnlockJ1.openWaitMs > 0) {
      await this.page.waitForTimeout(this.forceUnlockJ1.openWaitMs);
    }

    const selection = await this.applyBookmakerSelection();

    if (this.forceUnlockJ1.postSelectWaitMs > 0) {
      await this.page.waitForTimeout(this.forceUnlockJ1.postSelectWaitMs);
    }

    const after = await this.waitForBookmakerStateChange(before, this.forceUnlockJ1.stateWaitMs);
    const changed = this._bookmakerStateChanged(before, after);

    if (changed) {
      const retrigger = await this.retriggerArchiveRequest({
        timeoutMs: this.forceUnlockJ1.retriggerTimeoutMs
      });
      this.logger.info('recon_force_unlock_j1_changed', {
        traceId: this.traceId,
        beforeCount: Array.isArray(before?.myBookmakers) ? before.myBookmakers.length : 0,
        afterCount: Array.isArray(after?.myBookmakers) ? after.myBookmakers.length : 0,
        selection,
        retriggered: retrigger.success
      });
      return {
        applied: true,
        changed,
        before,
        after,
        selection,
        retrigger
      };
    }

    this.logger.warn('recon_force_unlock_j1_no_state_change', {
      traceId: this.traceId,
      beforeCount: Array.isArray(before?.myBookmakers) ? before.myBookmakers.length : 0,
      afterCount: Array.isArray(after?.myBookmakers) ? after.myBookmakers.length : 0,
      selection
    });

    return {
      applied: true,
      changed: false,
      before,
      after,
      selection
    };
  }

  async openBookmakerMenu() {
    if (!this.page) {
      return false;
    }

    if (typeof this.page.getByRole === 'function') {
      for (const label of this.forceUnlockJ1.menuLabels) {
        for (const role of ['link', 'button']) {
          try {
            const target = this.page.getByRole(role, { name: label }).first();
            const href = typeof target.getAttribute === 'function'
              ? await target.getAttribute('href')
              : null;
            if (typeof href === 'string' && /\/bookmakers\/?$/i.test(href.trim())) {
              continue;
            }
            if (await target.isVisible({ timeout: 1000 })) {
              await target.click({ timeout: 2000 });
              return true;
            }
          } catch (_error) {
            // fall through to DOM click
          }
        }
      }
    }

    if (typeof this.page.evaluate !== 'function') {
      return false;
    }

    return this.page.evaluate(({ menuLabels }) => {
      const normalize = (value) => String(value || '').replace(/\s+/g, ' ').trim().toLowerCase();
      const labels = menuLabels.map((item) => normalize(item)).filter(Boolean);
      const elements = Array.from(document.querySelectorAll('a,button,[role="button"],[role="link"]'));
      const candidate = elements.find((element) => {
        const text = normalize(element.textContent);
        const aria = normalize(element.getAttribute('aria-label'));
        const href = String(element.getAttribute('href') || '').trim();
        const isTopLevelBookmakersNav = /\/bookmakers\/?$/i.test(href);
        if (isTopLevelBookmakersNav) {
          return false;
        }
        return labels.includes(text) || labels.includes(aria);
      });

      if (!candidate) {
        return false;
      }

      candidate.click();
      return true;
    }, {
      menuLabels: this.forceUnlockJ1.menuLabels
    });
  }

  async applyBookmakerSelection() {
    if (!this.page || typeof this.page.evaluate !== 'function') {
      return {
        selectAllClicked: false,
        clickedBookmakers: []
      };
    }

    return this.page.evaluate(({ selectAllLabels, fallbackBookmakers }) => {
      const normalize = (value) => String(value || '').replace(/\s+/g, ' ').trim().toLowerCase();
      const selectAllTargets = selectAllLabels.map((item) => normalize(item)).filter(Boolean);
      const bookmakerTargets = fallbackBookmakers.map((item) => normalize(item)).filter(Boolean);
      const clickedBookmakers = [];

      const clickElement = (element) => {
        if (!element) {
          return false;
        }

        const target = element.closest('label,button,[role="button"],[role="checkbox"],a,div') || element;
        if (typeof target.click === 'function') {
          target.click();
          return true;
        }

        target.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
        return true;
      };

      const elements = Array.from(document.querySelectorAll('label,button,[role="button"],[role="checkbox"],input[type="checkbox"],a,span,div'));
      let selectAllClicked = false;

      for (const element of elements) {
        const text = normalize(element.textContent);
        const aria = normalize(element.getAttribute?.('aria-label'));
        if (!selectAllTargets.includes(text) && !selectAllTargets.includes(aria)) {
          continue;
        }

        if (clickElement(element)) {
          selectAllClicked = true;
          break;
        }
      }

      if (selectAllClicked) {
        return { selectAllClicked, clickedBookmakers };
      }

      for (const target of bookmakerTargets) {
        const element = elements.find((candidate) => {
          const text = normalize(candidate.textContent);
          const aria = normalize(candidate.getAttribute?.('aria-label'));
          return text.includes(target) || aria.includes(target);
        });

        if (element && clickElement(element)) {
          clickedBookmakers.push(target);
        }
      }

      return {
        selectAllClicked,
        clickedBookmakers
      };
    }, {
      selectAllLabels: this.forceUnlockJ1.selectAllLabels,
      fallbackBookmakers: this.forceUnlockJ1.fallbackBookmakers
    });
  }

  async readBookmakerState() {
    if (!this.page || typeof this.page.evaluate !== 'function') {
      return {
        myBookmakers: [],
        bookiehash: '',
        otCode: '',
        geoIPcode: ''
      };
    }

    return this.page.evaluate(() => ({
      myBookmakers: Array.isArray(window.pageVar?.userData?.myBookmakers)
        ? [...window.pageVar.userData.myBookmakers]
        : [],
      bookiehash: typeof window.pageVar?.bookiehash === 'string' ? window.pageVar.bookiehash : '',
      otCode: typeof window.pageVar?.otCode === 'string' ? window.pageVar.otCode : '',
      geoIPcode: typeof window.pageVar?.geoIPcode === 'string' ? window.pageVar.geoIPcode : ''
    }));
  }

  async waitForBookmakerStateChange(beforeState, timeoutMs) {
    if (!this.page || typeof this.page.waitForFunction !== 'function') {
      return this.readBookmakerState();
    }

    const timeout = Number(timeoutMs || 0);
    try {
      await this.page.waitForFunction(({ before }) => {
        const current = Array.isArray(window.pageVar?.userData?.myBookmakers)
          ? [...window.pageVar.userData.myBookmakers]
          : [];
        const previous = Array.isArray(before?.myBookmakers) ? before.myBookmakers : [];
        if (current.length !== previous.length) {
          return true;
        }

        return current.some((value, index) => value !== previous[index]);
      }, { timeout }, { before: beforeState });
    } catch (_error) {
      // 超时后直接读取当前状态，由调用方判定是否变化
    }

    return this.readBookmakerState();
  }

  _bookmakerStateChanged(beforeState, afterState) {
    const before = Array.isArray(beforeState?.myBookmakers) ? beforeState.myBookmakers : [];
    const after = Array.isArray(afterState?.myBookmakers) ? afterState.myBookmakers : [];

    if (before.length !== after.length) {
      return true;
    }

    if (before.some((value, index) => value !== after[index])) {
      return true;
    }

    return String(beforeState?.bookiehash || '') !== String(afterState?.bookiehash || '');
  }

  async retriggerArchiveRequest(options = {}) {
    if (!this.page || typeof this.page.evaluate !== 'function') {
      return { success: false, reason: 'page_unavailable' };
    }

    const timeoutMs = Number(options.timeoutMs ?? this.forceUnlockJ1.retriggerTimeoutMs);

    return this.page.evaluate(async ({ timeout }) => {
      const token = typeof window.pageVar?.otCode === 'string' ? window.pageVar.otCode.trim() : '';
      const bookiehash = typeof window.pageVar?.bookiehash === 'string' ? window.pageVar.bookiehash.trim() : '';
      if (!token || !bookiehash) {
        return {
          success: false,
          reason: 'missing_state',
          token,
          bookiehash
        };
      }

      const url = `https://www.oddsportal.com/ajax-sport-country-tournament-archive_/1/${token}/${bookiehash}/1/0/?_=${Date.now()}`;
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), timeout);

      try {
        const response = await fetch(url, {
          credentials: 'include',
          signal: ctrl.signal,
          headers: {
            'x-requested-with': 'XMLHttpRequest'
          }
        });
        const body = await response.text();
        clearTimeout(timer);
        return {
          success: response.ok,
          status: response.status,
          url,
          bodyPreview: String(body || '').slice(0, 240)
        };
      } catch (error) {
        clearTimeout(timer);
        return {
          success: false,
          reason: error.message,
          url
        };
      }
    }, {
      timeout: timeoutMs
    });
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
