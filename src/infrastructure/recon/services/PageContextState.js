'use strict';

const {
  buildHttpStatusError,
  pageClosed,
  waitForDelay
} = require('../../shared/helpers/browserUtils');
const { buildStealthIdentity } = require('./StealthIdentityFactory');
const {
  applyStealthIdentityState,
  createPageContextState,
  resolveList,
  syncStealthProviderProfile
} = require('./BrowserContextConfigFactory');
const { mergeContextExtraHTTPHeaders } = require('../../shared/helpers/browserHeaderUtils');

const BACKEND_FETCH_FAILED_RE = /backend fetch failed|guru meditation/i;

const pageContextState = {
  _buildStealthIdentity() {
    return buildStealthIdentity(this.traceId, this.proxy, {
      enableFingerprintRotation: this.enableFingerprintRotation,
      generation: this.contextGeneration + 1
    });
  },

  _applyStealthIdentity(stealthIdentity) {
    applyStealthIdentityState(this, stealthIdentity);
  },

  _syncStealthProviderProfile() {
    syncStealthProviderProfile(this);
  },

  _buildContextOptions(externalSession = null) {
    const contextUserAgent = this.userAgent;
    return {
      userAgent: contextUserAgent,
      viewport: this.viewport,
      locale: this.locale,
      timezoneId: this.timezoneId,
      deviceScaleFactor: this.deviceScaleFactor,
      screen: this.viewport,
      hasTouch: this.hasTouch,
      isMobile: this.isMobile,
      extraHTTPHeaders: mergeContextExtraHTTPHeaders({
        baseHeaders: externalSession?.extraHTTPHeaders || {},
        extraHeaders: this.stealthExtraHTTPHeaders,
        userAgent: contextUserAgent,
        acceptLanguage: this.acceptLanguage,
        platform: this.platform
      })
    };
  },

  async _initializeFreshPage(context, externalSession = null) {
    await this.injectExternalSession(context, externalSession);
    const page = await context.newPage();
    await this.stealthProvider.applyStealthFingerprint(page, this.enableStealthFingerprint, {
      fingerprintSeed: this.stealthIdentity?.fingerprintSeed || '',
      hardwareConcurrency: this.hardwareConcurrency,
      deviceMemory: this.deviceMemory,
      platform: this.platform,
      language: this.locale,
      languages: [this.locale, 'en', 'en-GB'],
      webgl: this.stealthIdentity?.webgl || null,
      canvasSalt: this.stealthIdentity?.canvasSalt || '',
      webglSalt: this.stealthIdentity?.webglSalt || ''
    });
    if (this.antiDetectionScript && typeof page.addInitScript === 'function') {
      await page.addInitScript(this.antiDetectionScript);
    }
    return page;
  },

  async _closeActiveContext() {
    const context = this.context;
    const page = this.page;
    await this.refreshRuntimeSessionSnapshot(typeof page?.url === 'function' ? page.url() : '');
    this.context = null;
    this.page = null;
    this._sessionPrimed = false;

    if (page && typeof page.close === 'function' && !pageClosed(page)) {
      try {
        await page.close();
      } catch (_error) {
        // 页面已挂时允许继续关闭 context
      }
    }

    return this._closeTargetWithTimeout('context', context);
  },

  getFingerprintSummary() {
    return {
      contextGeneration: this.contextGeneration,
      fingerprintSeed: this.stealthIdentity?.fingerprintSeed || null,
      userAgent: this.userAgent,
      viewport: this.viewport,
      platform: this.platform,
      hardwareConcurrency: this.hardwareConcurrency,
      deviceMemory: this.deviceMemory
    };
  },

  async injectExternalSession(context = this.context, sessionSnapshot = null) {
    if (!context || typeof context.addCookies !== 'function') {
      return { applied: false, cookies: 0, sourceFormat: 'unavailable' };
    }

    const snapshot = sessionSnapshot || this.sessionManager.load();
    const cookies = Array.isArray(snapshot?.cookies) ? snapshot.cookies : [];
    if (cookies.length === 0) {
      return { applied: false, cookies: 0, sourceFormat: snapshot?.sourceFormat || 'empty' };
    }

    await context.addCookies(cookies);
    this.logger.info('recon_external_session_injected', {
      traceId: this.traceId,
      sourceFormat: snapshot?.sourceFormat || 'unknown',
      cookies: cookies.length
    });
    return { applied: true, cookies: cookies.length, sourceFormat: snapshot?.sourceFormat || 'unknown' };
  },

  async refreshRuntimeSessionSnapshot(url = '') {
    if (!this.sessionManager || !this.context || typeof this.context.cookies !== 'function') {
      return { applied: false, cookies: 0, sourceFormat: 'runtime_unavailable' };
    }

    const candidateUrls = [...new Set(
      [url, this.homeWarmupUrl]
        .map((value) => String(value || '').trim())
        .filter(Boolean)
    )];

    try {
      let cookies = [];
      for (const candidateUrl of candidateUrls) {
        const scopedCookies = await this.context.cookies([candidateUrl]);
        if (Array.isArray(scopedCookies) && scopedCookies.length > cookies.length) {
          cookies = scopedCookies;
        }
      }

      if (cookies.length === 0) {
        cookies = await this.context.cookies();
      }

      return this.sessionManager.setRuntimeSnapshot({
        cookies,
        userAgent: this.userAgent,
        extraHTTPHeaders: {
          'accept-language': this.acceptLanguage,
          ...(this.userAgent ? { 'user-agent': this.userAgent } : {})
        }
      });
    } catch (error) {
      this.logger.debug?.('recon_runtime_session_snapshot_refresh_failed', {
        traceId: this.traceId,
        error: error.message
      });
      return { applied: false, cookies: 0, sourceFormat: 'runtime_error' };
    }
  },

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
  },

  async navigate(url, options = {}) {
    if (!this.page) {
      throw new Error('browser_page_unavailable');
    }

    const timeout = options.timeout || this.navigationTimeoutMs;
    const waitUntil = options.waitUntil || 'domcontentloaded';

    await this.primeSession(url, { timeout, waitUntil });
    const response = await this.page.goto(url, { timeout, waitUntil });
    await this.throwIfBackendFetchFailed(response, url, 'target');
    await this.handleConsent();
    if (pageClosed(this.page)) {
      return;
    }

    await this.waitForNavigationReady({ selectors: options.readySelectors, timeout: options.readyTimeoutMs });
    if (pageClosed(this.page)) {
      return;
    }

    await this.waitForKnownContent({ selector: options.contentReadySelector, timeout: options.readyTimeoutMs });
    if (pageClosed(this.page)) {
      return;
    }

    await waitForDelay(this.page, options.warmupDelayMs ?? this.warmupDelayMs);
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
    await this.refreshRuntimeSessionSnapshot(url);
  },

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
    await this.throwIfBackendFetchFailed(null, this.homeWarmupUrl, 'warmup');
    await this.handleConsent();
    await waitForDelay(this.page, this.homeWarmupWaitMs);
    await this.refreshRuntimeSessionSnapshot(this.homeWarmupUrl);
    this._sessionPrimed = true;
  },

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
      this.logger.warn('recon_known_content_selector_missed', { traceId: this.traceId, selector });
      return false;
    }
  },

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

    this.logger.warn('recon_navigation_ready_selector_missed', { traceId: this.traceId, selectors, timeout });
    return false;
  },

  async readBackendFailureSignal() {
    if (!this.page || pageClosed(this.page)) {
      return null;
    }

    let title = '';
    let bodyText = '';

    try {
      if (typeof this.page.title === 'function') {
        title = String(await this.page.title() || '');
      }
    } catch (_error) {
      title = '';
    }

    try {
      if (typeof this.page.evaluate === 'function') {
        bodyText = String(await this.page.evaluate(() => document.body?.innerText || '') || '');
      }
    } catch (_error) {
      bodyText = '';
    }

    const combined = `${title}\n${bodyText}`.trim();
    return combined && BACKEND_FETCH_FAILED_RE.test(combined)
      ? { statusCode: 503, title, snippet: combined.slice(0, 200) }
      : null;
  },

  async throwIfBackendFetchFailed(response, url, phase = 'target') {
    if (response && typeof response.status === 'function') {
      const statusCode = Number(response.status()) || 0;
      if (statusCode >= 500) {
        this.logger.warn('recon_navigation_http_failure', {
          traceId: this.traceId,
          url,
          phase,
          statusCode
        });
        throw buildHttpStatusError(statusCode, `HTTP_${statusCode}`, { url, phase });
      }
    }

    const embeddedFailure = await this.readBackendFailureSignal();
    if (!embeddedFailure) {
      return;
    }

    this.logger.warn('recon_navigation_backend_fetch_failed', {
      traceId: this.traceId,
      url,
      phase,
      title: embeddedFailure.title,
      snippet: embeddedFailure.snippet
    });
    throw buildHttpStatusError(
      embeddedFailure.statusCode,
      `HTTP_${embeddedFailure.statusCode} backend_fetch_failed`,
      { url, phase }
    );
  },

  async triggerDataLoading(options = {}) {
    if (!this.page) {
      return;
    }

    const iterations = options.iterations || this.scrollIterations;
    const stepPx = options.stepPx || this.scrollStepPx;
    const delayMs = options.delayMs || this.scrollDelayMs;
    for (let index = 0; index < iterations; index++) {
      await this.page.evaluate((amount) => window.scrollBy(0, amount), stepPx);
      await waitForDelay(this.page, delayMs);
    }
  },

  shouldForceUnlockJ1(url) {
    return this.bookmakerUnlocker.shouldForceUnlockJ1(url);
  },

  async maybeForceUnlockJ1(url) {
    return this.bookmakerUnlocker.maybeForceUnlockJ1(this.page, url, {
      shouldForceUnlockJ1: (targetUrl) => this.shouldForceUnlockJ1(targetUrl),
      readBookmakerState: () => this.readBookmakerState(),
      openBookmakerMenu: () => this.openBookmakerMenu(),
      applyBookmakerSelection: () => this.applyBookmakerSelection(),
      waitForBookmakerStateChange: (beforeState, timeoutMs) => this.waitForBookmakerStateChange(beforeState, timeoutMs),
      retriggerArchiveRequest: (options) => this.retriggerArchiveRequest(options)
    });
  },

  async openBookmakerMenu() {
    return this.bookmakerUnlocker.openBookmakerMenu(this.page);
  },

  async applyBookmakerSelection() {
    return this.bookmakerUnlocker.applyBookmakerSelection(this.page);
  },

  async readBookmakerState() {
    return this.bookmakerUnlocker.readBookmakerState(this.page);
  },

  async waitForBookmakerStateChange(beforeState, timeoutMs) {
    return this.bookmakerUnlocker.waitForBookmakerStateChange(this.page, beforeState, timeoutMs);
  },

  async retriggerArchiveRequest(options = {}) {
    return this.bookmakerUnlocker.retriggerArchiveRequest(this.page, options);
  },

  async handleConsent() {
    return this.stealthProvider.dismissConsent(this.page, {
      labels: this.consentLabels,
      visibilityTimeoutMs: this.consentVisibilityTimeoutMs,
      clickTimeoutMs: this.consentClickTimeoutMs,
      postClickWaitMs: this.consentPostClickWaitMs
    });
  }
};

module.exports = {
  createPageContextState,
  pageContextState
};
