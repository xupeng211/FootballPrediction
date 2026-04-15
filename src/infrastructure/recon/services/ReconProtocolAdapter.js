'use strict';

// Low-level agents here are only instantiated from ProxyProvider-issued leases.
const http = require('node:http');
const https = require('node:https');
const { URL } = require('node:url');
const { HttpProxyAgent } = require('http-proxy-agent');
const { HttpsProxyAgent } = require('https-proxy-agent');
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
const { findLatestAppScript } = require('./ReconDecryptorSourceExtractor');
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

  _buildPureProtocolContextProbeTargets(target = {}) {
    const targets = [];
    const seen = new Set();
    const addTarget = (baseUrl, source) => {
      const normalizedBaseUrl = String(baseUrl || '').trim();
      if (!normalizedBaseUrl || seen.has(normalizedBaseUrl)) {
        return;
      }
      seen.add(normalizedBaseUrl);
      targets.push({
        ...target,
        url: normalizedBaseUrl,
        baseUrl: normalizedBaseUrl,
        contextSource: source
      });
    };

    addTarget(target?.baseUrl || target?.url || '', 'requested');
    addTarget(this.navigator?.stateProber?.deriveCurrentResultsUrl?.(target?.baseUrl || target?.url || ''), 'current_results');
    addTarget(this.navigator?.stateProber?.deriveLeaguePageUrl?.(target?.baseUrl || target?.url || ''), 'league_page');

    return targets;
  },

  _extractPureProtocolContextSignals(target = {}, html = '') {
    const embeddedState = extractEmbeddedProtocolStateFromHtml(html, target);
    const outrightMeta = this.navigator?.stateProber?.extractPageOutrightsMetaFromHtml?.(html) || null;
    return {
      embeddedState,
      outrightMeta,
      outrightId: typeof outrightMeta?.id === 'string' && outrightMeta.id.trim()
        ? outrightMeta.id.trim()
        : embeddedState.outrightId,
      tournamentId: extractTournamentIdFromHtml(html) || embeddedState.tournamentId
    };
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
    if (options.allowRuntimeStateProbe === false) {
      return { outrightId: '', bookmakerHash: '' };
    }

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

  _resolvePureProtocolUserAgent(options = {}) {
    return String(
      options.userAgent
      || this.navigator?.browserContext?.getFingerprintSummary?.()?.userAgent
      || this.navigator?.browserContext?.userAgent
      || PURE_PROTOCOL_CONFIG.user_agent
      || 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36'
    ).trim();
  },

  // eslint-disable-next-line complexity
  async _resolvePureProtocolCookieHeader(baseUrl = '', options = {}) {
    const explicitCookie = String(options.cookieHeader || options.cookie || '').trim();
    if (explicitCookie) {
      return explicitCookie;
    }

    const currentUrl = typeof this.page?.url === 'function' ? String(this.page.url() || '') : '';
    const normalizedBaseUrl = normalizePureProtocolComparableUrl(baseUrl);
    const normalizedCurrentUrl = normalizePureProtocolComparableUrl(currentUrl);
    if (
      normalizedBaseUrl
      && normalizedCurrentUrl
      && normalizedBaseUrl === normalizedCurrentUrl
      && this.page
      && typeof this.page.evaluate === 'function'
    ) {
      try {
        const cookieHeader = String(await this.page.evaluate(() => String(document.cookie || '')) || '').trim();
        if (cookieHeader) {
          return cookieHeader;
        }
      } catch {
        // ignore page cookie read failure
      }
    }

    const context = this.navigator?.context;
    if (context && typeof context.cookies === 'function') {
      try {
        const cookies = await context.cookies(baseUrl ? [baseUrl] : undefined);
        const cookieHeader = (Array.isArray(cookies) ? cookies : [])
          .filter((cookie) => cookie?.name && cookie?.value)
          .map((cookie) => `${cookie.name}=${cookie.value}`)
          .join('; ');
        if (cookieHeader) {
          return cookieHeader;
        }
      } catch {
        // ignore browser context cookie read failure
      }
    }

    return '';
  },

  _buildPureProtocolHeaders(referer = '', accept = 'application/json, text/plain, */*', options = {}) {
    const resolvedReferer = referer || 'https://www.oddsportal.com/';
    let resolvedOrigin = '';
    try {
      resolvedOrigin = new URL(resolvedReferer).origin;
    } catch {
      resolvedOrigin = 'https://www.oddsportal.com';
    }

    const headers = {
      accept,
      'accept-language': 'en-US,en;q=0.9,ja-JP;q=0.8,ja;q=0.7',
      referer: resolvedReferer,
      origin: options.origin || resolvedOrigin,
      'user-agent': this._resolvePureProtocolUserAgent(options),
      'sec-fetch-site': 'same-origin',
      'sec-fetch-mode': options.fetchMode || 'cors',
      'sec-fetch-dest': options.fetchDest || 'empty'
    };

    if (options.includeContentType !== false) {
      headers['content-type'] = options.contentType || 'application/json';
    }
    if (options.includeXRequestedWith !== false) {
      headers['x-requested-with'] = 'XMLHttpRequest';
    }
    if (options.cookieHeader) {
      headers.cookie = options.cookieHeader;
    }

    return headers;
  },

  async _resolveLatestPureProtocolAppScript(baseUrl = '', options = {}) {
    return findLatestAppScript(baseUrl, {
      allowRootFallback: true,
      logger: this.logger,
      traceId: this.navigator?.traceId || 'trace-pure-protocol',
      ...options
    });
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

    const cookieHeader = await this._resolvePureProtocolCookieHeader(target.baseUrl, options);
    const httpResponse = await this._fetchPureProtocolText(target.baseUrl, {
      timeoutMs: options.timeoutMs,
      referer: target.baseUrl,
      accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      cookieHeader,
      includeXRequestedWith: false,
      includeContentType: false,
      fetchDest: 'document',
      fetchMode: 'navigate'
    });
    if (httpResponse.success) {
      return { ...httpResponse, source: 'node_fetch' };
    }

    if (options.allowBrowserHtmlFallback === false) {
      return httpResponse;
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

  _resolvePureProtocolRequestProxy(options = {}) {
    const explicitLease = options.proxyLease?.proxy?.server
      ? options.proxyLease
      : options.requestProxyLease?.proxy?.server
        ? options.requestProxyLease
        : null;
    if (explicitLease) {
      return {
        lease: explicitLease,
        server: explicitLease.proxy.server,
        port: Number(explicitLease.proxy.port || 0) || null
      };
    }

    const explicitProxy = options.proxy?.server
      ? options.proxy
      : options.requestProxy?.server
        ? options.requestProxy
        : null;
    if (explicitProxy?.server) {
      return {
        lease: null,
        server: explicitProxy.server,
        port: Number(explicitProxy.port || 0) || null
      };
    }

    if (typeof options.proxyServer === 'string' && options.proxyServer.trim()) {
      return {
        lease: null,
        server: options.proxyServer.trim(),
        port: Number(options.proxyPort || 0) || null
      };
    }

    return null;
  },

  async _fetchPureProtocolTextViaProxyRequest(url, options = {}, redirectCount = 0) {
    const resolvedProxy = this._resolvePureProtocolRequestProxy(options);
    if (!resolvedProxy?.server) {
      throw new Error('PURE_PROTOCOL_PROXY_SERVER_MISSING');
    }

    const timeoutMs = Math.max(1, Number(options.timeoutMs || this.navigator?.archiveTimeoutMs || 45000));
    const requestUrl = new URL(url);
    const requestLib = requestUrl.protocol === 'https:' ? https : http;
    const requestHeaders = this._buildPureProtocolHeaders(options.referer, options.accept, options);
    const agent = requestUrl.protocol === 'https:'
      ? new HttpsProxyAgent(resolvedProxy.server)
      : new HttpProxyAgent(resolvedProxy.server);

    return new Promise((resolve) => {
      const req = requestLib.request({
        hostname: requestUrl.hostname,
        port: requestUrl.port || (requestUrl.protocol === 'https:' ? 443 : 80),
        path: `${requestUrl.pathname}${requestUrl.search}`,
        protocol: requestUrl.protocol,
        method: 'GET',
        headers: requestHeaders,
        agent
      }, (response) => {
        const chunks = [];
        response.on('data', chunk => chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk)));
        response.on('end', async () => {
          const text = Buffer.concat(chunks).toString('utf8');
          const retryAfterRaw = response.headers['retry-after'] || '';
          const statusCode = Number(response.statusCode) || null;
          const location = String(response.headers.location || '').trim();

          if (
            statusCode
            && statusCode >= 300
            && statusCode < 400
            && location
            && redirectCount < 5
          ) {
            try {
              const redirectedUrl = new URL(location, requestUrl).href;
              resolve(await this._fetchPureProtocolTextViaProxyRequest(
                redirectedUrl,
                options,
                redirectCount + 1
              ));
              return;
            } catch (error) {
              resolve({ success: false, status: null, error: error.message, text: '' });
              return;
            }
          }

          if (!statusCode || statusCode < 200 || statusCode >= 300) {
            resolve({
              success: false,
              status: statusCode,
              error: statusCode ? `HTTP_${statusCode}` : 'HTTP_REQUEST_FAILED',
              text,
              retryAfterRaw
            });
            return;
          }

          const embeddedFailure = detectEmbeddedHttpFailure(text);
          resolve(embeddedFailure
            ? { success: false, status: embeddedFailure.statusCode, error: embeddedFailure.error, text, retryAfterRaw }
            : { success: true, status: statusCode, text, retryAfterRaw });
        });
      });

      req.setTimeout(timeoutMs, () => {
        req.destroy(new Error('This operation was aborted'));
      });

      req.on('error', (error) => {
        resolve({ success: false, status: null, error: error.message, text: '' });
      });

      req.end();
    });
  },

  async _fetchPureProtocolTextOnce(url, options = {}) {
    const controller = new AbortController();
    const timeoutMs = Number(options.timeoutMs || this.navigator?.archiveTimeoutMs || 45000);
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const cookieHeader = await this._resolvePureProtocolCookieHeader(
        options.referer || options.baseUrl || url,
        options
      );
      const resolvedOptions = {
        ...options,
        cookieHeader: cookieHeader || options.cookieHeader || ''
      };
      if (this._resolvePureProtocolRequestProxy(resolvedOptions)?.server) {
        return this._fetchPureProtocolTextViaProxyRequest(url, resolvedOptions);
      }
      const response = await fetch(url, {
        headers: this._buildPureProtocolHeaders(options.referer, options.accept, resolvedOptions),
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

  // eslint-disable-next-line complexity
  async _resolvePureProtocolContext(target, options = {}) {
    const normalizedTarget = this._normalizePureProtocolTarget(target);
    const requestedBaseUrl = normalizedTarget.baseUrl;
    const probeTargets = this._buildPureProtocolContextProbeTargets(normalizedTarget);
    let selectedHtmlContext = null;
    let lastHtmlFailure = null;

    for (const probeTarget of probeTargets) {
      const htmlResponse = await this._resolvePureProtocolHtml(probeTarget, options);
      if (!htmlResponse.success) {
        lastHtmlFailure = {
          probeTarget,
          htmlResponse
        };
        continue;
      }

      const html = String(htmlResponse.text || '');
      const extractedSignals = this._extractPureProtocolContextSignals(probeTarget, html);
      if (!selectedHtmlContext) {
        selectedHtmlContext = {
          probeTarget,
          htmlResponse,
          html,
          ...extractedSignals
        };
      }

      const hasStrongToken = Boolean(extractedSignals.outrightId);
      const hasAnyToken = hasStrongToken || Boolean(extractedSignals.tournamentId);
      if (hasAnyToken) {
        selectedHtmlContext = {
          probeTarget,
          htmlResponse,
          html,
          ...extractedSignals
        };
        if (probeTarget.baseUrl !== requestedBaseUrl) {
          this.logger.info('pure_protocol_context_fallback_source_selected', {
            requestedBaseUrl,
            resolvedBaseUrl: probeTarget.baseUrl,
            contextSource: probeTarget.contextSource,
            outrightId: extractedSignals.outrightId || null,
            tournamentId: extractedSignals.tournamentId || null
          });
        }
        if (hasStrongToken) {
          break;
        }
      }
    }

    if (!selectedHtmlContext) {
      const error = new Error(lastHtmlFailure?.htmlResponse?.error || 'PURE_PROTOCOL_HTML_FETCH_FAILED');
      error.statusCode = Number(lastHtmlFailure?.htmlResponse?.status) || null;
      error.url = lastHtmlFailure?.probeTarget?.baseUrl || requestedBaseUrl;
      throw error;
    }

    const {
      probeTarget: resolvedTarget,
      html,
      embeddedState,
      outrightMeta
    } = selectedHtmlContext;
    let outrightId = selectedHtmlContext.outrightId || '';
    let tournamentId = selectedHtmlContext.tournamentId || '';
    let runtimeBookmakerHash = embeddedState.bookmakerHash || '';
    const cookieHeader = await this._resolvePureProtocolCookieHeader(resolvedTarget.baseUrl, options);

    if (!outrightId && !tournamentId) {
      const runtimeState = await this._resolvePureProtocolRuntimeState(resolvedTarget, options);
      outrightId = runtimeState.outrightId || '';
      runtimeBookmakerHash = runtimeState.bookmakerHash || runtimeBookmakerHash;
    }

    const appScriptResolution = await this._resolveLatestPureProtocolAppScript(resolvedTarget.baseUrl, {
      html,
      headers: this._buildPureProtocolHeaders(resolvedTarget.baseUrl, 'text/javascript,application/javascript,*/*;q=0.1', {
        ...options,
        cookieHeader,
        includeXRequestedWith: false,
        includeContentType: false,
        fetchDest: 'script',
        fetchMode: 'cors'
      }),
      cookieHeader
    });

    return {
      ...normalizedTarget,
      url: resolvedTarget.baseUrl,
      baseUrl: resolvedTarget.baseUrl,
      requestedBaseUrl,
      contextSource: resolvedTarget.contextSource || 'requested',
      html,
      outrightMeta,
      outrightId,
      tournamentId,
      appBundleUrl: appScriptResolution.appScriptUrl || extractAppBundleUrlFromHtml(html, resolvedTarget.baseUrl),
      appBundleSource: appScriptResolution.bundleSource || '',
      appScriptDiscoverySource: appScriptResolution.discoverySource || '',
      appScriptManifestMap: appScriptResolution.manifestAssetMap || new Map(),
      seasonToken: extractPureProtocolSeasonToken(requestedBaseUrl, { ...normalizedTarget, ...options }),
      locale: extractLocaleFromHtml(html),
      runtimeBookmakerHash,
      cookieHeader
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

  _buildPureProtocolScriptHeaders(context = {}, options = {}) {
    return this._buildPureProtocolHeaders(
      options.referer || context.baseUrl || context.appBundleUrl || 'https://www.oddsportal.com/',
      options.accept || 'text/javascript,application/javascript,*/*;q=0.1',
      {
        ...options,
        cookieHeader: options.cookieHeader || context.cookieHeader || '',
        includeXRequestedWith: false,
        includeContentType: false,
        fetchDest: 'script',
        fetchMode: 'cors'
      }
    );
  },

  // eslint-disable-next-line complexity
  _resolvePureProtocolManifestRemapUrl(context = {}, targetUrl = '') {
    const manifestAssetMap = context?.appScriptManifestMap instanceof Map
      ? context.appScriptManifestMap
      : null;
    if (!String(targetUrl || '').trim()) {
      return '';
    }

    try {
      const absoluteUrl = new URL(
        String(targetUrl || ''),
        context.appBundleUrl || context.baseUrl || 'https://www.oddsportal.com/'
      ).href;
      if (
        /\/build\/assets\/app-[^/]+\.js(?:[?#].*)?$/i.test(absoluteUrl)
        && String(context.appBundleUrl || '').trim()
        && absoluteUrl !== context.appBundleUrl
      ) {
        return context.appBundleUrl;
      }

      if (!manifestAssetMap || manifestAssetMap.size === 0) {
        return '';
      }

      const fileName = absoluteUrl.split('/').pop() || '';
      const fileStem = fileName.replace(/\.[^.]+$/u, '');
      const normalizedStem = fileStem.replace(/-[A-Za-z0-9_-]{6,}$/u, '');
      return manifestAssetMap.get(fileStem) || manifestAssetMap.get(normalizedStem) || '';
    } catch {
      return '';
    }
  },

  async _fetchPureProtocolScriptText(targetUrl, context = {}, options = {}) {
    if (typeof fetch !== 'function') {
      throw new Error('PURE_PROTOCOL_FETCH_UNAVAILABLE');
    }

    const resolvedUrl = new URL(
      String(targetUrl || ''),
      context.appBundleUrl || context.baseUrl || 'https://www.oddsportal.com/'
    ).href;
    const response = await fetch(resolvedUrl, {
      headers: this._buildPureProtocolScriptHeaders(context, options),
      redirect: 'follow'
    });
    if (!response.ok) {
      throw new Error(`HTTP_${response.status}:${resolvedUrl}`);
    }

    return response.text();
  },

  _createPureProtocolSourceLoader(context = {}) {
    return async (targetUrl) => {
      const requestedUrl = new URL(
        String(targetUrl || ''),
        context.appBundleUrl || context.baseUrl || 'https://www.oddsportal.com/'
      ).href;

      try {
        return await this._fetchPureProtocolScriptText(requestedUrl, context, {
          referer: context.baseUrl || requestedUrl
        });
      } catch (error) {
        const remappedUrl = this._resolvePureProtocolManifestRemapUrl(context, requestedUrl);
        if (!remappedUrl || remappedUrl === requestedUrl) {
          throw error;
        }

        const remappedSource = await this._fetchPureProtocolScriptText(remappedUrl, context, {
          referer: context.baseUrl || requestedUrl
        });
        this.logger.info('app_script_manifest_remap_hit', {
          traceId: this.navigator?.traceId || 'trace-pure-protocol',
          requestedUrl,
          remappedUrl,
          source: 'pure_protocol'
        });
        return remappedSource;
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
      bundleSource: context.appBundleSource || '',
      sourceLoader: this._createPureProtocolSourceLoader(context),
      headers: this._buildPureProtocolScriptHeaders(context),
      globals: this._buildPureProtocolRuntimeGlobals(context, token, bookmakerHash),
      html: context.html
    });

    return decryptor;
  }
};

module.exports = {
  reconProtocolAdapter
};
