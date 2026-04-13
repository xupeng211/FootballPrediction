'use strict';

const { waitForDelay } = require('../../shared/helpers/browserUtils');
const {
  detectEmbeddedHttpFailure,
  extractAppBundleUrlFromHtml,
  extractEmbeddedProtocolStateFromHtml,
  extractLocaleFromHtml,
  extractPureProtocolSeasonToken,
  extractTournamentIdFromHtml,
  normalizePureProtocolComparableUrl
} = require('../../shared/helpers/reconProtocolStateHelpers');
const { ReconNetworkMonitor } = require('./ReconNetworkMonitor');
const { ReconPureDecryptor } = require('./ReconPureDecryptor');
const { getReconConfigSection } = require('./ReconServiceConfig');

const RETRYABLE_PURE_PROTOCOL_FETCH_ERROR_RE = /fetch failed|socket|terminated|econnreset|und_err|other side closed|networkerror|timed out|aborted/i;
const PURE_PROTOCOL_CONFIG = getReconConfigSection(['recon_runtime', 'protocol_fetch'], {});

const reconProtocolAdapter = {
  _normalizePureProtocolTarget(target) {
    if (typeof target === 'string') {
      return { url: target, baseUrl: target };
    }

    const url = String(target?.url || target?.baseUrl || target?.resultsUrl || '').trim();
    return { ...(target || {}), url, baseUrl: url };
  },

  _resolvePureProtocolBookmakerHash(target = {}, options = {}) {
    for (const candidate of [
      options.bookmakerHash,
      options.bookiehash,
      target?.runtimeBookmakerHash,
      target?.pageVarBookmakerHash,
      target?.bookmakerHash,
      target?.bookiehash,
      PURE_PROTOCOL_CONFIG.default_bookiehash,
      PURE_PROTOCOL_CONFIG.default_bookmaker_hash
    ]) {
      const normalized = String(candidate || '').trim();
      if (/^X(?:\d+X)*\d+$/i.test(normalized)) {
        return normalized;
      }
    }

    return '';
  },

  async _resolvePureProtocolRuntimeState(context, options = {}) {
    if (
      !this.navigator
      || typeof this.navigator.ensureBrowserHealthy !== 'function'
      || typeof this.navigator.navigate !== 'function'
      || !this.navigator.stateProber
    ) {
      return { outrightId: '', bookmakerHash: '' };
    }

    try {
      await this.navigator.ensureBrowserHealthy();
      const warmUrl = this.navigator.stateProber.deriveCurrentResultsUrl(context.baseUrl) || context.baseUrl;
      await this.navigator.navigate(warmUrl, {
        waitUntil: 'domcontentloaded',
        timeout: options.timeoutMs ?? this.navigator.archiveTimeoutMs
      });
      await waitForDelay(this.page, this.navigator.postApiDiscoveryWaitMs);

      const runtimeToken = await this.navigator.stateProber.extractTournamentToken();
      const pageVarState = this.page && typeof this.page.evaluate === 'function'
        ? await this.page.evaluate(() => ({
          otCode: typeof window.pageVar?.otCode === 'string' ? window.pageVar.otCode.trim() : '',
          bookiehash: typeof window.pageVar?.bookiehash === 'string' ? window.pageVar.bookiehash.trim() : '',
          myot: typeof window.pageVar?.myot === 'string' ? window.pageVar.myot.trim() : ''
        }))
        : { otCode: '', bookiehash: '', myot: '' };

      return {
        outrightId: String(runtimeToken || pageVarState?.otCode || '').trim(),
        bookmakerHash: String(pageVarState?.bookiehash || pageVarState?.myot || '').trim()
      };
    } catch (error) {
      this.logger.warn('pure_protocol_runtime_state_probe_failed', {
        baseUrl: context.baseUrl,
        error: error.message
      });
      return { outrightId: '', bookmakerHash: '' };
    }
  },

  _createPureProtocolMonitor() {
    return new ReconNetworkMonitor({
      logger: this.logger,
      traceId: this.navigator?.traceId || 'trace-pure-protocol',
      decryptorFactory: () => ({
        getAlgorithmVersion() {
          return null;
        },
        async decrypt() {
          throw new Error('pure_protocol_monitor_decrypt_unused');
        },
        async extractDecryptor() {
          throw new Error('pure_protocol_monitor_extract_unused');
        }
      })
    });
  },

  _buildPureProtocolHeaders(referer = '', accept = 'application/json, text/plain, */*') {
    return {
      accept,
      'accept-language': 'en-US,en;q=0.9,ja-JP;q=0.8,ja;q=0.7',
      'content-type': 'application/json',
      referer: referer || 'https://www.oddsportal.com/',
      'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
      'x-requested-with': 'XMLHttpRequest'
    };
  },

  _resolvePureProtocolActivePageCandidates(baseUrl = '') {
    const candidates = new Set();
    for (const candidate of [
      baseUrl,
      this.navigator?.stateProber?.deriveCurrentResultsUrl?.(baseUrl),
      this.navigator?.stateProber?.deriveLeaguePageUrl?.(baseUrl)
    ]) {
      const normalized = normalizePureProtocolComparableUrl(candidate);
      if (normalized) {
        candidates.add(normalized);
      }
    }

    return candidates;
  },

  async _readPureProtocolHtmlFromActivePage(baseUrl = '') {
    if (!this.page || typeof this.page.content !== 'function') {
      return '';
    }

    const currentUrl = typeof this.page.url === 'function' ? this.page.url() : '';
    const candidates = this._resolvePureProtocolActivePageCandidates(baseUrl);
    const normalizedCurrentUrl = normalizePureProtocolComparableUrl(currentUrl);
    if (normalizedCurrentUrl && candidates.size > 0 && !candidates.has(normalizedCurrentUrl)) {
      return '';
    }

    try {
      return String(await this.page.content() || '');
    } catch {
      return '';
    }
  },

  async _loadPureProtocolHtmlViaBrowser(baseUrl = '', options = {}) {
    if (!this.navigator || typeof this.navigator.ensureBrowserHealthy !== 'function' || typeof this.navigator.navigate !== 'function') {
      return '';
    }

    try {
      await this.navigator.ensureBrowserHealthy();
      const warmUrl = this.navigator.stateProber?.deriveCurrentResultsUrl?.(baseUrl) || baseUrl;
      await this.navigator.navigate(warmUrl, {
        waitUntil: 'domcontentloaded',
        timeout: options.timeoutMs ?? this.navigator.archiveTimeoutMs
      });
      await waitForDelay(this.page, this.navigator.postApiDiscoveryWaitMs);
      return this._readPureProtocolHtmlFromActivePage(baseUrl);
    } catch (error) {
      this.logger.warn('pure_protocol_browser_html_probe_failed', {
        baseUrl,
        error: error.message
      });
      return '';
    }
  },

  async _resolvePureProtocolHtml(target, options = {}) {
    const activePageHtml = await this._readPureProtocolHtmlFromActivePage(target.baseUrl);
    if (String(activePageHtml || '').trim()) {
      return { success: true, status: 200, text: activePageHtml, source: 'browser_active_page' };
    }

    const httpResponse = await this._fetchPureProtocolText(target.baseUrl, {
      timeoutMs: options.timeoutMs,
      referer: target.baseUrl,
      accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    });
    if (httpResponse.success) {
      return { ...httpResponse, source: 'node_fetch' };
    }

    const browserHtml = await this._loadPureProtocolHtmlViaBrowser(target.baseUrl, options);
    if (String(browserHtml || '').trim()) {
      this.logger.warn('pure_protocol_html_fetch_http_fallback_hit', {
        baseUrl: target.baseUrl,
        error: httpResponse.error || '',
        statusCode: Number(httpResponse.status) || null
      });
      return {
        success: true,
        status: 200,
        text: browserHtml,
        source: 'browser_navigate_fallback',
        fallbackError: httpResponse.error || '',
        fallbackStatus: Number(httpResponse.status) || null
      };
    }

    return httpResponse;
  },

  _isRetryablePureProtocolFetchFailure(result = {}) {
    const status = Number(result.status) || null;
    return status === 429
      || status === 503
      || status === 504
      || Boolean(status && status >= 500)
      || RETRYABLE_PURE_PROTOCOL_FETCH_ERROR_RE.test(String(result.error || ''));
  },

  async _waitPureProtocolFetchRetry(delayMs = 0) {
    if (this.navigator && typeof this.navigator._waitBeforeRetry === 'function') {
      await this.navigator._waitBeforeRetry(Math.max(0, Number(delayMs) || 0));
      return;
    }
    await waitForDelay(null, delayMs);
  },

  async _fetchPureProtocolTextOnce(url, options = {}) {
    const controller = new AbortController();
    const timeoutMs = Number(options.timeoutMs || this.navigator?.archiveTimeoutMs || 45000);
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(url, {
        headers: this._buildPureProtocolHeaders(options.referer, options.accept),
        redirect: 'follow',
        signal: controller.signal
      });
      const text = await response.text();
      const retryAfterRaw = response.headers.get('retry-after') || '';

      if (!response.ok) {
        return { success: false, status: response.status, error: `HTTP_${response.status}`, text, retryAfterRaw };
      }

      const embeddedFailure = detectEmbeddedHttpFailure(text);
      return embeddedFailure
        ? { success: false, status: embeddedFailure.statusCode, error: embeddedFailure.error, text, retryAfterRaw }
        : { success: true, status: response.status, text, retryAfterRaw };
    } catch (error) {
      return { success: false, status: null, error: error.message, text: '' };
    } finally {
      clearTimeout(timer);
    }
  },

  async _fetchPureProtocolText(url, options = {}) {
    const maxAttempts = Math.max(1, Number(options.maxAttempts || PURE_PROTOCOL_CONFIG.fetch_max_attempts || 3));
    const retryDelayMs = Math.max(0, Number(options.retryDelayMs ?? PURE_PROTOCOL_CONFIG.fetch_retry_delay_ms ?? 750));
    let lastResult = { success: false, status: null, error: 'PURE_PROTOCOL_FETCH_UNINITIALIZED', text: '' };

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      const result = await this._fetchPureProtocolTextOnce(url, options);
      if (result.success) {
        return result;
      }

      lastResult = result;
      if (attempt >= maxAttempts || !this._isRetryablePureProtocolFetchFailure(result)) {
        return result;
      }

      const retryAfterMs = this.navigator && typeof this.navigator._parseRetryAfterMs === 'function'
        ? this.navigator._parseRetryAfterMs(result.retryAfterRaw)
        : 0;
      const scheduledDelayMs = Math.max(retryDelayMs, retryAfterMs || 0);

      this.logger.warn('pure_protocol_fetch_retrying', {
        url,
        attempt,
        maxAttempts,
        statusCode: Number(result.status) || null,
        error: result.error || '',
        delayMs: scheduledDelayMs
      });
      await this._waitPureProtocolFetchRetry(scheduledDelayMs);
    }

    return lastResult;
  },

  async _resolvePureProtocolContext(target, options = {}) {
    const normalizedTarget = this._normalizePureProtocolTarget(target);
    const htmlResponse = await this._resolvePureProtocolHtml(normalizedTarget, options);
    if (!htmlResponse.success) {
      const error = new Error(htmlResponse.error || 'PURE_PROTOCOL_HTML_FETCH_FAILED');
      error.statusCode = Number(htmlResponse.status) || null;
      error.url = normalizedTarget.baseUrl;
      throw error;
    }

    const html = String(htmlResponse.text || '');
    const embeddedState = extractEmbeddedProtocolStateFromHtml(html, normalizedTarget);
    const outrightMeta = this.navigator?.stateProber?.extractPageOutrightsMetaFromHtml?.(html) || null;
    let outrightId = typeof outrightMeta?.id === 'string' ? outrightMeta.id.trim() : '';
    let runtimeBookmakerHash = embeddedState.bookmakerHash || '';

    if (!outrightId) {
      outrightId = embeddedState.outrightId;
    }

    const tournamentId = extractTournamentIdFromHtml(html) || embeddedState.tournamentId;
    if (!outrightId && !tournamentId) {
      const runtimeState = await this._resolvePureProtocolRuntimeState(normalizedTarget, options);
      outrightId = runtimeState.outrightId || '';
      runtimeBookmakerHash = runtimeState.bookmakerHash || runtimeBookmakerHash;
    }

    return {
      ...normalizedTarget,
      html,
      outrightMeta,
      outrightId,
      tournamentId,
      appBundleUrl: extractAppBundleUrlFromHtml(html, normalizedTarget.baseUrl),
      seasonToken: extractPureProtocolSeasonToken(normalizedTarget.baseUrl, options),
      locale: extractLocaleFromHtml(html),
      runtimeBookmakerHash
    };
  },

  _buildPureProtocolRuntimeGlobals(context, token = '', bookmakerHash = '') {
    const resolvedToken = String(token || context?.outrightId || context?.tournamentId || '').trim();
    const resolvedBookmakerHash = String(bookmakerHash || '').trim() || 'X';
    return {
      location: new URL(context.baseUrl),
      pageVar: {
        locale: context.locale || 'en',
        otCode: resolvedToken,
        myot: resolvedBookmakerHash,
        bookiehash: resolvedBookmakerHash,
        myBookmakers: [],
        userData: { myBookmakers: [] }
      },
      pageOutrightsVar: {
        id: context.outrightId || resolvedToken,
        sid: Number(context.outrightMeta?.sid || 1) || 1,
        cid: Number(context.outrightMeta?.cid || 0) || 0,
        archive: true
      }
    };
  },

  async _createPureProtocolDecryptor(context, sampleEncryptedData = '', token = '', bookmakerHash = '') {
    const decryptor = new ReconPureDecryptor({
      logger: this.logger,
      traceId: this.navigator?.traceId || 'trace-pure-protocol'
    });

    await decryptor.loadFromBundleUrl(context.appBundleUrl, {
      sampleEncryptedData,
      headers: this._buildPureProtocolHeaders(context.baseUrl),
      globals: this._buildPureProtocolRuntimeGlobals(context, token, bookmakerHash)
    });

    return decryptor;
  }
};

module.exports = {
  reconProtocolAdapter
};
