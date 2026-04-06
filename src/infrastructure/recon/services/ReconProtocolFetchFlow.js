'use strict';

const { JSDOM } = require('jsdom');

const { ReconEndpointHelper } = require('./ReconEndpointHelper');
const { ReconPureDecryptor } = require('./ReconPureDecryptor');
const { ReconNetworkMonitor } = require('./ReconNetworkMonitor');
const { getReconConfigSection } = require('./ReconServiceConfig');

const EMBEDDED_PLACEHOLDER_STATUS_RE = /^\s*URL:[\s\S]*?\bStatus:\s*(\d{3})\b/i;
const BACKEND_FETCH_FAILED_RE = /backend fetch failed|guru meditation/i;
const RETRYABLE_PURE_PROTOCOL_FETCH_ERROR_RE = /fetch failed|socket|terminated|econnreset|und_err|other side closed|networkerror|timed out|aborted/i;
const PURE_PROTOCOL_CONFIG = getReconConfigSection(['recon_runtime', 'protocol_fetch'], {});

function detectEmbeddedHttpFailure(bodyText = '') {
  const text = String(bodyText || '').trim();
  if (!text) {
    return null;
  }

  const placeholderMatch = text.match(EMBEDDED_PLACEHOLDER_STATUS_RE);
  if (placeholderMatch) {
    return {
      statusCode: Number(placeholderMatch[1]) || 503,
      error: `EMBEDDED_HTTP_${placeholderMatch[1] || '503'}`
    };
  }

  if (BACKEND_FETCH_FAILED_RE.test(text)) {
    return {
      statusCode: 503,
      error: 'EMBEDDED_HTTP_503'
    };
  }

  return null;
}

function decodeHtmlEntities(text = '') {
  return String(text || '')
    .replace(/&quot;/g, '"')
    .replace(/&#34;/g, '"')
    .replace(/&#39;/g, '\'')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>');
}

const reconProtocolFetchFlow = {
  async _fetchAndDecrypt(apiBaseUrl, maxPages, timeoutMs, options = {}) {
    return this._callNavigatorOverride(
      '_fetchAndDecryptWithOptions',
      (resolvedUrl, resolvedMaxPages, resolvedTimeoutMs, resolvedOptions) => (
        this._fetchAndDecryptWithOptions(resolvedUrl, resolvedMaxPages, resolvedTimeoutMs, resolvedOptions)
      ),
      apiBaseUrl,
      maxPages,
      timeoutMs,
      options
    );
  },

  async _fetchAndDecryptWithOptions(apiBaseUrl, maxPages, timeoutMs, options = {}) {
    const breakerKey = this.navigator._resolveCircuitBreakerKey(apiBaseUrl, options);
    const fetchOnce = () => this.navigator._executeWithCircuitBreaker(
      breakerKey,
      async () => this.navigator._executeWith503Retry(
        async () => {
          this.navigator.networkMonitor.setPage(this.page);
          return this.navigator.networkMonitor.fetchArchivePages(apiBaseUrl, maxPages, timeoutMs);
        },
        {
          operationName: 'fetch_archive_pages',
          breakerKey,
          inspectUrl: apiBaseUrl,
          retryNavigateUrl: options.warmUrl || null,
          retryReadySelector: options.readySelector || '',
          timeoutMs
        }
      )
    );

    const initialResult = await fetchOnce();
    if (!this._resultHasDecryptFailure(initialResult) || options.allowRecovery === false) {
      return initialResult;
    }

    this.logger.warn('navigator_relaunch_after_decrypt_failure', {
      apiBaseUrl,
      warmUrl: options.warmUrl || null
    });

    try {
      await this.navigator.close();
      await this.navigator.launch(this.navigator.lastLaunchOptions || {});

      if (options.warmUrl) {
        await this.navigator.navigate(options.warmUrl, {
          waitUntil: 'domcontentloaded',
          timeout: timeoutMs,
          circuitBreakerKey: breakerKey
        });
        if (this.page && typeof this.page.waitForTimeout === 'function') {
          await this.page.waitForTimeout(this.navigator.postApiDiscoveryWaitMs);
        }
      }

      const retriedResult = await fetchOnce();
      retriedResult.retriedAfterRelaunch = true;
      return retriedResult;
    } catch (error) {
      this.logger.warn('navigator_relaunch_after_decrypt_failure_failed', {
        apiBaseUrl,
        error: error.message
      });
      return initialResult;
    }
  },

  async _fetchCurrentTournament(apiBaseUrl, maxPages, timeoutMs, options = {}) {
    const breakerKey = this.navigator._resolveCircuitBreakerKey(apiBaseUrl, options);
    const retryNavigateUrl = options.retryNavigateUrl
      || (this.page && typeof this.page.url === 'function' ? this.page.url() : '');

    return this.navigator._executeWithCircuitBreaker(
      breakerKey,
      async () => this.navigator._executeWith503Retry(
        async () => {
          this.navigator.networkMonitor.setPage(this.page);
          return this.navigator.networkMonitor.fetchCurrentTournamentPages(apiBaseUrl, maxPages, timeoutMs);
        },
        {
          operationName: 'fetch_current_tournament_pages',
          breakerKey,
          inspectUrl: apiBaseUrl,
          retryNavigateUrl,
          timeoutMs
        }
      )
    );
  },

  _normalizePureProtocolTarget(target) {
    if (typeof target === 'string') {
      return {
        url: target,
        baseUrl: target
      };
    }

    const url = String(
      target?.url
      || target?.baseUrl
      || target?.resultsUrl
      || ''
    ).trim();

    return {
      ...(target || {}),
      url,
      baseUrl: url
    };
  },

  _extractPureProtocolSeasonToken(baseUrl, options = {}) {
    const normalizedBaseUrl = String(baseUrl || '').trim();
    const fromUrl = normalizedBaseUrl.match(/-((?:\d{4})(?:-\d{4})?)\/results\/?$/i)?.[1];
    if (fromUrl) {
      return fromUrl;
    }

    const season = String(options.season || options.dbSeason || '').trim();
    if (/^\d{4}\/\d{4}$/.test(season)) {
      return season.replace('/', '-');
    }
    if (/^\d{4}-\d{4}$/.test(season) || /^\d{4}$/.test(season)) {
      return season;
    }

    return '';
  },

  _extractAppBundleUrlFromHtml(html, baseUrl) {
    const text = String(html || '');
    const relativeUrl = text.match(/<script[^>]+type="module"[^>]+src="([^"]*\/build\/assets\/app-[^"]+\.js[^"]*)"/i)?.[1]
      || text.match(/<link[^>]+rel="modulepreload"[^>]+href="([^"]*\/build\/assets\/app-[^"]+\.js[^"]*)"/i)?.[1]
      || '';

    if (!relativeUrl) {
      return '';
    }

    try {
      return new URL(relativeUrl, baseUrl).href;
    } catch {
      return '';
    }
  },

  _extractTournamentIdFromHtml(html) {
    const text = decodeHtmlEntities(html);
    const raw = text.match(/(?:_tournamentId|tournamentId)\s*["']?\s*:\s*(?:"([^"]+)"|'([^']+)'|([A-Za-z0-9-]+))/i);
    const token = String(raw?.[1] || raw?.[2] || raw?.[3] || '').trim();
    return /^(?:null|undefined)$/i.test(token) ? '' : token;
  },

  _extractLocaleFromHtml(html) {
    const text = String(html || '');
    return text.match(/_lang(?:&quot;|"):(?:&quot;|")([a-z-]+)(?:&quot;|")/i)?.[1]
      || text.match(/lang="([a-z-]+)"/i)?.[1]
      || 'en';
  },

  _resolvePureProtocolBookmakerHash(target = {}, options = {}) {
    const candidates = [
      options.bookmakerHash,
      options.bookiehash,
      target?.runtimeBookmakerHash,
      target?.pageVarBookmakerHash,
      target?.bookmakerHash,
      target?.bookiehash,
      PURE_PROTOCOL_CONFIG.default_bookiehash,
      PURE_PROTOCOL_CONFIG.default_bookmaker_hash
    ];

    for (const candidate of candidates) {
      const normalized = String(candidate || '').trim();
      if (/^X(?:\d+X)*\d+$/i.test(normalized)) {
        return normalized;
      }
    }

    return '';
  },

  _extractScriptTextsFromHtml(html) {
    try {
      const dom = new JSDOM(String(html || ''));
      return Array.from(dom.window.document.scripts).map((script) => String(script.textContent || ''));
    } catch {
      return [];
    }
  },

  _tryParseEmbeddedJson(rawValue, options = {}) {
    let payload = decodeHtmlEntities(String(rawValue || '')).trim();
    if (!payload) {
      return null;
    }

    if (options.unwrapQuotedJson === true) {
      if (
        (payload.startsWith('\'') && payload.endsWith('\''))
        || (payload.startsWith('"') && payload.endsWith('"'))
      ) {
        payload = payload.slice(1, -1);
      }
    }

    if (payload.endsWith(';')) {
      payload = payload.slice(0, -1).trim();
    }

    try {
      return JSON.parse(payload);
    } catch {
      return null;
    }
  },

  _extractStructuredStatePayloads(html) {
    const payloads = [];
    const rawHtml = String(html || '');
    const nextDataMatch = rawHtml.match(/<script[^>]+id=["']__NEXT_DATA__["'][^>]*>([\s\S]*?)<\/script>/i);
    if (nextDataMatch?.[1]) {
      payloads.push({
        source: '__NEXT_DATA__',
        value: nextDataMatch[1],
        unwrapQuotedJson: false
      });
    }

    for (const scriptText of this._extractScriptTextsFromHtml(rawHtml)) {
      for (const [source, pattern, unwrapQuotedJson] of [
        ['__INITIAL_STATE__', /(?:window\.)?__INITIAL_STATE__\s*=\s*({[\s\S]*})\s*;?/i, false],
        ['initialState', /(?:window\.)?initialState\s*=\s*({[\s\S]*})\s*;?/i, false],
        ['pageVar:json', /(?:window\.)?pageVar\s*=\s*({[\s\S]*})\s*;?/i, false],
        ['pageVar:string', /(?:window\.)?pageVar\s*=\s*('(?:\\'|[^'])*'|"(?:\\"|[^"])*")\s*;?/i, true]
      ]) {
        const match = scriptText.match(pattern);
        if (match?.[1]) {
          payloads.push({
            source,
            value: match[1],
            unwrapQuotedJson
          });
        }
      }
    }

    return payloads;
  },

  _buildPureProtocolTargetHints(target = {}, html = '') {
    const hints = new Set();

    try {
      const pathname = new URL(target?.baseUrl || target?.url || '').pathname;
      const segments = pathname.split('/').filter(Boolean);
      const leagueSegment = segments.at(-2) === 'results'
        ? segments.at(-3)
        : segments.at(-1);
      const normalizedLeagueSegment = String(leagueSegment || '').trim().toLowerCase();
      if (normalizedLeagueSegment) {
        hints.add(normalizedLeagueSegment);
        hints.add(normalizedLeagueSegment.replace(/-\d{4}(?:-\d{4})?$/i, ''));
        hints.add(normalizedLeagueSegment.replace(/-/g, ' '));
      }
    } catch {
      // ignore invalid URL
    }

    const decodedHtml = decodeHtmlEntities(html);
    const tournamentName = decodedHtml.match(/_tournamentName\s*["']?\s*:\s*"([^"]+)"/i)?.[1] || '';
    if (tournamentName) {
      hints.add(String(tournamentName).trim().toLowerCase());
      hints.add(String(tournamentName).trim().toLowerCase().replace(/\s+/g, '-'));
      hints.add(String(tournamentName).trim().toLowerCase().replace(/\s+\d{4}(?:\/\d{4})?$/i, ''));
    }

    return [...hints].filter(Boolean);
  },

  _objectMatchesTargetHints(node, hints = []) {
    if (!node || typeof node !== 'object' || hints.length === 0) {
      return false;
    }

    const comparableValues = [
      node.name,
      node.title,
      node.slug,
      node.url,
      node.pathname,
      node.route,
      node.tournamentName,
      node._tournamentName,
      node._tournamentUrl,
      node._tournamentLink,
      node._tournamentLinkNoSeason
    ]
      .map((value) => String(value || '').trim().toLowerCase())
      .filter(Boolean);

    return comparableValues.some((value) => hints.some((hint) => value.includes(hint)));
  },

  _collectStructuredProtocolStateCandidates(node, hints = [], trail = [], state = null) {
    const targetState = state || {
      tournamentObjectIds: [],
      pageVarOtCodes: [],
      tournamentIds: [],
      bookmakerHashes: []
    };

    if (node === null || node === undefined) {
      return targetState;
    }

    if (Array.isArray(node)) {
      for (const item of node) {
        this._collectStructuredProtocolStateCandidates(item, hints, trail, targetState);
      }
      return targetState;
    }

    if (typeof node !== 'object') {
      return targetState;
    }

    const addCandidate = (bucket, value) => {
      const normalized = String(value ?? '').trim();
      if (!normalized || /^(?:null|undefined)$/i.test(normalized)) {
        return;
      }
      if (!targetState[bucket].includes(normalized)) {
        targetState[bucket].push(normalized);
      }
    };

    const trailText = trail.join('.').toLowerCase();
    const keys = Object.keys(node);
    const objectFingerprint = `${trailText} ${keys.join(' ')}`.toLowerCase();
    const pageVarLike = objectFingerprint.includes('pagevar');
    const tournamentLike = objectFingerprint.includes('tournament') || objectFingerprint.includes('outright');
    const targetLike = this._objectMatchesTargetHints(node, hints);

    if (pageVarLike) {
      addCandidate('pageVarOtCodes', node.otCode);
      addCandidate('bookmakerHashes', node.bookiehash);
      addCandidate('bookmakerHashes', node.myot);
    }

    if (tournamentLike || targetLike) {
      addCandidate('tournamentIds', node._tournamentId);
      addCandidate('tournamentIds', node.tournamentId);
      addCandidate('tournamentIds', node.tournament_id);
      const idValue = node.outrightId ?? node.otCode ?? node.id;
      if (/^\d+$/.test(String(idValue ?? '').trim())) {
        addCandidate('tournamentIds', idValue);
      } else {
        addCandidate('tournamentObjectIds', idValue);
      }
    }

    for (const [key, value] of Object.entries(node)) {
      this._collectStructuredProtocolStateCandidates(value, hints, [...trail, key], targetState);
    }

    return targetState;
  },

  _extractEmbeddedProtocolStateFromHtml(html, target = {}) {
    const hints = this._buildPureProtocolTargetHints(target, html);
    const aggregate = {
      outrightId: '',
      tournamentId: '',
      bookmakerHash: ''
    };

    const stateCandidates = {
      tournamentObjectIds: [],
      pageVarOtCodes: [],
      tournamentIds: [],
      bookmakerHashes: []
    };

    for (const payload of this._extractStructuredStatePayloads(html)) {
      const parsed = this._tryParseEmbeddedJson(payload.value, {
        unwrapQuotedJson: payload.unwrapQuotedJson === true
      });
      if (!parsed) {
        continue;
      }

      this._collectStructuredProtocolStateCandidates(parsed, hints, [payload.source], stateCandidates);
    }

    aggregate.outrightId = stateCandidates.tournamentObjectIds[0]
      || stateCandidates.pageVarOtCodes[0]
      || '';
    aggregate.tournamentId = stateCandidates.tournamentIds[0] || '';
    aggregate.bookmakerHash = stateCandidates.bookmakerHashes[0] || '';

    return aggregate;
  },

  async _resolvePureProtocolRuntimeState(context, options = {}) {
    if (
      !this.navigator
      || typeof this.navigator.ensureBrowserHealthy !== 'function'
      || typeof this.navigator.navigate !== 'function'
      || !this.navigator.stateProber
    ) {
      return {
        outrightId: '',
        bookmakerHash: ''
      };
    }

    try {
      await this.navigator.ensureBrowserHealthy();
      const warmUrl = this.navigator.stateProber.deriveCurrentResultsUrl(context.baseUrl) || context.baseUrl;
      await this.navigator.navigate(warmUrl, {
        waitUntil: 'domcontentloaded',
        timeout: options.timeoutMs ?? this.navigator.archiveTimeoutMs
      });
      if (this.page && typeof this.page.waitForTimeout === 'function') {
        await this.page.waitForTimeout(this.navigator.postApiDiscoveryWaitMs);
      }

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
      return {
        outrightId: '',
        bookmakerHash: ''
      };
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

  _normalizePureProtocolComparableUrl(url = '') {
    const normalized = String(url || '').trim();
    if (!normalized) {
      return '';
    }

    try {
      const parsed = new URL(normalized);
      parsed.hash = '';
      parsed.search = '';
      return parsed.href.replace(/\/+$/, '');
    } catch (_error) {
      return normalized.replace(/[?#].*$/, '').replace(/\/+$/, '');
    }
  },

  _resolvePureProtocolActivePageCandidates(baseUrl = '') {
    const candidates = new Set();
    const push = (value) => {
      const normalized = this._normalizePureProtocolComparableUrl(value);
      if (normalized) {
        candidates.add(normalized);
      }
    };

    push(baseUrl);
    push(this.navigator?.stateProber?.deriveCurrentResultsUrl?.(baseUrl));
    push(this.navigator?.stateProber?.deriveLeaguePageUrl?.(baseUrl));
    return candidates;
  },

  async _readPureProtocolHtmlFromActivePage(baseUrl = '') {
    if (!this.page || typeof this.page.content !== 'function') {
      return '';
    }

    const currentUrl = typeof this.page.url === 'function' ? this.page.url() : '';
    const candidates = this._resolvePureProtocolActivePageCandidates(baseUrl);
    const normalizedCurrentUrl = this._normalizePureProtocolComparableUrl(currentUrl);

    if (normalizedCurrentUrl && candidates.size > 0 && !candidates.has(normalizedCurrentUrl)) {
      return '';
    }

    try {
      return String(await this.page.content() || '');
    } catch (_error) {
      return '';
    }
  },

  async _loadPureProtocolHtmlViaBrowser(baseUrl = '', options = {}) {
    if (
      !this.navigator
      || typeof this.navigator.ensureBrowserHealthy !== 'function'
      || typeof this.navigator.navigate !== 'function'
    ) {
      return '';
    }

    try {
      await this.navigator.ensureBrowserHealthy();
      const warmUrl = this.navigator.stateProber?.deriveCurrentResultsUrl?.(baseUrl) || baseUrl;
      await this.navigator.navigate(warmUrl, {
        waitUntil: 'domcontentloaded',
        timeout: options.timeoutMs ?? this.navigator.archiveTimeoutMs
      });
      if (this.page && typeof this.page.waitForTimeout === 'function') {
        await this.page.waitForTimeout(this.navigator.postApiDiscoveryWaitMs);
      }
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
      return {
        success: true,
        status: 200,
        text: activePageHtml,
        source: 'browser_active_page'
      };
    }

    const httpResponse = await this._fetchPureProtocolText(target.baseUrl, {
      timeoutMs: options.timeoutMs,
      referer: target.baseUrl,
      accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    });
    if (httpResponse.success) {
      return {
        ...httpResponse,
        source: 'node_fetch'
      };
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
    if (status === 429 || status === 503 || status === 504) {
      return true;
    }

    if (status && status >= 500) {
      return true;
    }

    return RETRYABLE_PURE_PROTOCOL_FETCH_ERROR_RE.test(String(result.error || ''));
  },

  async _waitPureProtocolFetchRetry(delayMs = 0) {
    const normalizedDelayMs = Math.max(0, Number(delayMs) || 0);
    if (normalizedDelayMs <= 0) {
      return;
    }

    if (this.navigator && typeof this.navigator._waitBeforeRetry === 'function') {
      await this.navigator._waitBeforeRetry(normalizedDelayMs);
      return;
    }

    await new Promise((resolve) => {
      setTimeout(resolve, normalizedDelayMs);
    });
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
        return {
          success: false,
          status: response.status,
          error: `HTTP_${response.status}`,
          text,
          retryAfterRaw
        };
      }

      const embeddedFailure = detectEmbeddedHttpFailure(text);
      if (embeddedFailure) {
        return {
          success: false,
          status: embeddedFailure.statusCode,
          error: embeddedFailure.error,
          text,
          retryAfterRaw
        };
      }

      return {
        success: true,
        status: response.status,
        text,
        retryAfterRaw
      };
    } catch (error) {
      return {
        success: false,
        status: null,
        error: error.message,
        text: ''
      };
    } finally {
      clearTimeout(timer);
    }
  },

  async _fetchPureProtocolText(url, options = {}) {
    const maxAttempts = Math.max(
      1,
      Number(options.maxAttempts || PURE_PROTOCOL_CONFIG.fetch_max_attempts || 3)
    );
    const retryDelayMs = Math.max(
      0,
      Number(options.retryDelayMs ?? PURE_PROTOCOL_CONFIG.fetch_retry_delay_ms ?? 750)
    );

    let lastResult = {
      success: false,
      status: null,
      error: 'PURE_PROTOCOL_FETCH_UNINITIALIZED',
      text: ''
    };

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
    const outrightMeta = this.navigator?.stateProber?.extractPageOutrightsMetaFromHtml?.(html) || null;
    const embeddedState = this._extractEmbeddedProtocolStateFromHtml(html, normalizedTarget);
    let outrightId = typeof outrightMeta?.id === 'string' ? outrightMeta.id.trim() : '';
    let tournamentId = this._extractTournamentIdFromHtml(html) || embeddedState.tournamentId;
    let runtimeBookmakerHash = embeddedState.bookmakerHash || '';
    const appBundleUrl = this._extractAppBundleUrlFromHtml(html, normalizedTarget.baseUrl);
    const seasonToken = this._extractPureProtocolSeasonToken(normalizedTarget.baseUrl, options);
    const locale = this._extractLocaleFromHtml(html);

    if (!outrightId) {
      outrightId = embeddedState.outrightId;
    }

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
      appBundleUrl,
      seasonToken,
      locale,
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
        userData: {
          myBookmakers: []
        }
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
  },

  _buildArchivePageUrl(base, page) {
    return page === 1
      ? `${base}/?_=${Date.now()}`
      : `${base}/page/${page}/?_=${Date.now()}`;
  },

  _buildCurrentTournamentPageUrl(base, page) {
    return page === 1
      ? `${base}/?_=${Date.now()}`
      : `${base}/${page}/?_=${Date.now()}`;
  },

  async _fetchPureProtocolPaginatedPages(config = {}) {
    const {
      apiBaseUrl,
      maxPages,
      timeoutMs,
      source,
      referer,
      decryptor,
      buildBaseUrl,
      buildPageUrl
    } = config;

    const seenHashes = new Set();
    const matches = [];
    const pageStats = [];
    const monitor = this._createPureProtocolMonitor();
    monitor.sourceUrl = String(referer || apiBaseUrl || '').trim();
    const base = buildBaseUrl(apiBaseUrl);
    let pageLimit = Math.max(1, Number(maxPages || 1));
    let httpFailure = null;

    for (let page = 1; page <= pageLimit; page++) {
      const pageUrl = buildPageUrl(base, page);
      const response = await this._fetchPureProtocolText(pageUrl, {
        timeoutMs,
        referer
      });

      if (!response.success) {
        httpFailure = {
          page,
          url: pageUrl,
          statusCode: Number(response.status) || null,
          error: response.error,
          retryAfterRaw: response.retryAfterRaw || '',
          retryAfterMs: 0
        };
        pageStats.push({
          page,
          url: pageUrl,
          rows: 0,
          ...httpFailure
        });
        break;
      }

      if (!String(response.text || '').trim()) {
        pageStats.push({
          page,
          url: pageUrl,
          rows: 0,
          total: matches.length,
          source: `${source}:empty`
        });
        break;
      }

      try {
        const parsed = await decryptor.decrypt(response.text);
        const pageMatches = monitor.extractMatchesFromJson(parsed, source);
        const rowCount = Array.isArray(parsed?.d?.rows)
          ? parsed.d.rows.length
          : Array.isArray(parsed?.rows)
            ? parsed.rows.length
            : pageMatches.length;
        const total = Number(parsed?.d?.total) || Number(parsed?.total) || pageMatches.length;

        let newRows = 0;
        for (const match of pageMatches) {
          const hash = match?.hash || '';
          if (!hash || seenHashes.has(hash)) {
            continue;
          }

          seenHashes.add(hash);
          matches.push(match);
          newRows++;
        }

        pageStats.push({
          page,
          url: pageUrl,
          rows: rowCount,
          newRows,
          total,
          source
        });

        if (rowCount === 0 && newRows === 0) {
          break;
        }

        if (total > 0) {
          pageLimit = Math.min(pageLimit, Math.ceil(total / monitor.pageSize));
        }
      } catch (error) {
        pageStats.push({
          page,
          url: pageUrl,
          rows: 0,
          error: `decrypt_failed:${error.message}`
        });
        break;
      }
    }

    return {
      matches,
      pagesScanned: pageStats.length,
      totalCandidates: matches.length,
      pageStats,
      httpFailure
    };
  },

  async _extractViaPureProtocol(target, options = {}) {
    const context = await this._resolvePureProtocolContext(target, options);
    if (!context.appBundleUrl) {
      throw new Error('PURE_PROTOCOL_APP_BUNDLE_MISSING');
    }

    const tokenCandidates = [...new Set(
      [context.outrightId, context.tournamentId]
        .map((token) => String(token || '').trim())
        .filter(Boolean)
    )];
    const bookmakerHash = this._resolvePureProtocolBookmakerHash(context, options);

    if (tokenCandidates.length === 0) {
      throw new Error('PURE_PROTOCOL_TOURNAMENT_TOKEN_MISSING');
    }
    if (!bookmakerHash) {
      throw new Error('PURE_PROTOCOL_BOOKMAKER_HASH_MISSING');
    }

    let samplePayload = '';
    let sampleToken = tokenCandidates[0];

    for (const token of tokenCandidates) {
      const sampleArchiveUrl = `https://www.oddsportal.com/ajax-sport-country-tournament-archive_/1/${token}/${bookmakerHash}/1/0/`;
      const sampleResponse = await this._fetchPureProtocolText(this._buildArchivePageUrl(sampleArchiveUrl.replace(/\/+$/, ''), 1), {
        timeoutMs: options.timeoutMs,
        referer: context.baseUrl
      });

      if (sampleResponse.success && String(sampleResponse.text || '').trim()) {
        samplePayload = sampleResponse.text;
        sampleToken = token;
        break;
      }
    }

    if (!samplePayload) {
      throw new Error('PURE_PROTOCOL_SAMPLE_PAYLOAD_MISSING');
    }

    const decryptor = await this._createPureProtocolDecryptor(
      context,
      samplePayload,
      sampleToken,
      bookmakerHash
    );
    const combinedMatches = [];
    const combinedPageStats = [];
    const seen = new Set();
    const appendMatches = (pageMatches) => {
      for (const match of Array.isArray(pageMatches) ? pageMatches : []) {
        const key = match?.hash || match?.url;
        if (!key || seen.has(key)) {
          continue;
        }
        seen.add(key);
        combinedMatches.push(match);
      }
    };

    for (const token of tokenCandidates) {
      const archiveBaseUrl = `https://www.oddsportal.com/ajax-sport-country-tournament-archive_/1/${token}/${bookmakerHash}/1/0/`;
      const archiveResult = await this._fetchPureProtocolPaginatedPages({
        apiBaseUrl: archiveBaseUrl,
        maxPages: options.maxPages ?? this.navigator.archiveMaxPages,
        timeoutMs: options.timeoutMs ?? this.navigator.archiveTimeoutMs,
        source: `pure_protocol_archive:${token}`,
        referer: context.baseUrl,
        decryptor,
        buildBaseUrl: (url) => url.split('?')[0].replace(/\/page\/\d+\/?$/, '').replace(/\/+$/, ''),
        buildPageUrl: (base, page) => this._buildArchivePageUrl(base, page)
      });
      appendMatches(archiveResult.matches);
      combinedPageStats.push(...archiveResult.pageStats);
    }

    return {
      matches: combinedMatches,
      pagesScanned: combinedPageStats.length,
      totalCandidates: combinedMatches.length,
      pageStats: combinedPageStats,
      sourceState: combinedMatches.length > 0 ? 'PURE_PROTOCOL' : 'SOURCE_EMPTY',
      pureProtocolMeta: {
        baseUrl: context.baseUrl,
        appBundleUrl: context.appBundleUrl,
        outrightId: context.outrightId || null,
        tournamentId: context.tournamentId || null,
        bookmakerHash,
        seasonToken: context.seasonToken,
        locale: context.locale
      }
    };
  },

  async _resolveLeagueTournamentContext(baseUrl, timeoutMs, archiveApiUrl = null, options = {}) {
    const circuitBreakerKey = this.navigator._resolveCircuitBreakerKey(baseUrl, options);
    const leagueUrl = this.navigator.stateProber.deriveLeaguePageUrl(baseUrl);
    if (!leagueUrl) {
      return {
        leagueUrl: null,
        tournamentId: null,
        repairedArchiveUrl: archiveApiUrl,
        currentTournamentUrl: null
      };
    }

    await this.navigator.navigate(leagueUrl, {
      waitUntil: 'domcontentloaded',
      timeout: timeoutMs,
      circuitBreakerKey
    });
    if (this.page && typeof this.page.waitForTimeout === 'function') {
      await this.page.waitForTimeout(this.navigator.postApiDiscoveryWaitMs);
    }

    const tournamentToken = await this.navigator.stateProber.extractTournamentToken();
    const repairedArchiveUrl = tournamentToken
      ? this._repairArchiveEndpointWithTournamentId(archiveApiUrl, tournamentToken)
      : archiveApiUrl;
    const currentTournamentUrl = await this._callNavigatorOverride(
      '_getCurrentTournamentEndpoint',
      () => this._getCurrentTournamentEndpoint()
    ) || this._callNavigatorOverride(
      '_buildTournamentUrlFromArchive',
      (resolvedArchiveUrl, resolvedTournamentToken) => this._buildTournamentUrlFromArchive(
        resolvedArchiveUrl,
        resolvedTournamentToken
      ),
      archiveApiUrl,
      tournamentToken
    );

    return {
      leagueUrl,
      tournamentId: tournamentToken || null,
      repairedArchiveUrl,
      currentTournamentUrl
    };
  },

  _repairArchiveEndpointWithTournamentId(archiveApiUrl, tournamentId) {
    return ReconEndpointHelper.repairArchiveEndpointWithTournamentToken(archiveApiUrl, tournamentId);
  },

  _buildTournamentUrlFromArchive(archiveApiUrl, tournamentId) {
    if (!archiveApiUrl) {
      return null;
    }

    const match = archiveApiUrl.match(/^(.*?\/ajax-sport-country-tournament)-archive_\/(\d+)\/[^/]*\/(X[^/]+)\/(\d+)\/\d+\/?/i);
    if (!match) {
      return null;
    }

    const resolvedTournamentId = tournamentId || archiveApiUrl.match(
      /\/ajax-sport-country-tournament-archive_\/\d+\/([^/]+)\/X/i
    )?.[1];
    if (!resolvedTournamentId) {
      return null;
    }

    return `${match[1]}_/${match[2]}/${resolvedTournamentId}/${match[3]}/${match[4]}/`;
  },

  async _fallbackToLeagueTournament(baseUrl, archiveApiUrl, maxPages, timeoutMs, reason = 'fallback', options = {}) {
    const circuitBreakerKey = this.navigator._resolveCircuitBreakerKey(baseUrl, options);
    const context = await this._callNavigatorOverride(
      '_resolveLeagueTournamentContext',
      (resolvedBaseUrl, resolvedTimeoutMs, resolvedArchiveUrl, resolvedOptions) => (
        this._resolveLeagueTournamentContext(
          resolvedBaseUrl,
          resolvedTimeoutMs,
          resolvedArchiveUrl,
          resolvedOptions
        )
      ),
      baseUrl,
      timeoutMs,
      archiveApiUrl,
      { circuitBreakerKey }
    );
    if (!context.currentTournamentUrl) {
      return {
        matches: [],
        pagesScanned: 0,
        totalCandidates: 0,
        pageStats: [],
        sourceState: 'SOURCE_EMPTY'
      };
    }

    this.logger.warn('protocol_archive_fallback_current_tournament', {
      baseUrl,
      reason,
      currentTournamentUrl: context.currentTournamentUrl,
      breakerKey: circuitBreakerKey
    });

    const result = await this._callNavigatorOverride(
      '_fetchCurrentTournament',
      (resolvedUrl, resolvedMaxPages, resolvedTimeoutMs, resolvedOptions) => (
        this._fetchCurrentTournament(resolvedUrl, resolvedMaxPages, resolvedTimeoutMs, resolvedOptions)
      ),
      context.currentTournamentUrl,
      maxPages,
      timeoutMs,
      {
        circuitBreakerKey,
        retryNavigateUrl: context.leagueUrl || baseUrl
      }
    );
    return {
      ...result,
      sourceState: Array.isArray(result?.matches) && result.matches.length > 0
        ? 'CURRENT_TOURNAMENT_FALLBACK'
        : 'SOURCE_EMPTY'
    };
  }
};

module.exports = { reconProtocolFetchFlow };
