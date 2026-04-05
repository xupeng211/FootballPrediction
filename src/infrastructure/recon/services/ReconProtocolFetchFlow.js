'use strict';

const { ReconEndpointHelper } = require('./ReconEndpointHelper');
const { ReconPureDecryptor } = require('./ReconPureDecryptor');
const { ReconNetworkMonitor } = require('./ReconNetworkMonitor');
const { getReconConfigSection } = require('./ReconServiceConfig');

const EMBEDDED_PLACEHOLDER_STATUS_RE = /^\s*URL:[\s\S]*?\bStatus:\s*(\d{3})\b/i;
const BACKEND_FETCH_FAILED_RE = /backend fetch failed|guru meditation/i;
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
    const text = String(html || '');
    return text.match(/_tournamentId(?:&quot;|"):(\d+)/i)?.[1] || '';
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

  async _fetchPureProtocolText(url, options = {}) {
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

  async _resolvePureProtocolContext(target, options = {}) {
    const normalizedTarget = this._normalizePureProtocolTarget(target);
    const htmlResponse = await this._fetchPureProtocolText(normalizedTarget.baseUrl, {
      timeoutMs: options.timeoutMs,
      referer: normalizedTarget.baseUrl,
      accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    });

    if (!htmlResponse.success) {
      const error = new Error(htmlResponse.error || 'PURE_PROTOCOL_HTML_FETCH_FAILED');
      error.statusCode = Number(htmlResponse.status) || null;
      error.url = normalizedTarget.baseUrl;
      throw error;
    }

    const html = String(htmlResponse.text || '');
    const outrightMeta = this.navigator?.stateProber?.extractPageOutrightsMetaFromHtml?.(html) || null;
    const outrightId = typeof outrightMeta?.id === 'string' ? outrightMeta.id.trim() : '';
    const tournamentId = this._extractTournamentIdFromHtml(html);
    const appBundleUrl = this._extractAppBundleUrlFromHtml(html, normalizedTarget.baseUrl);
    const seasonToken = this._extractPureProtocolSeasonToken(normalizedTarget.baseUrl, options);
    const locale = this._extractLocaleFromHtml(html);

    return {
      ...normalizedTarget,
      html,
      outrightMeta,
      outrightId,
      tournamentId,
      appBundleUrl,
      seasonToken,
      locale
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
    const bookmakerHash = this._resolvePureProtocolBookmakerHash(target, options);

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
    const currentTournamentUrl = this._callNavigatorOverride(
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
