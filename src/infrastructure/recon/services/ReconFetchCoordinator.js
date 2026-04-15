/* eslint-disable complexity, max-lines */
'use strict';

const { waitForDelay } = require('../../shared/helpers/browserUtils');
const { ReconEndpointHelper } = require('./ReconEndpointHelper');
const { getReconConfigSection } = require('./ReconServiceConfig');

const PURE_PROTOCOL_FETCH_CONFIG = getReconConfigSection(['recon_runtime', 'protocol_fetch'], {});

function appendUniqueProtocolMatches(collection, seen, pageMatches) {
  for (const match of Array.isArray(pageMatches) ? pageMatches : []) {
    const key = match?.hash || match?.url;
    if (!key || seen.has(key)) {
      continue;
    }
    seen.add(key);
    collection.push(match);
  }
}

function pushProtocolFailureStat(pageStats, page, url, failure, extra = {}) {
  pageStats.push({
    page,
    url,
    rows: 0,
    ...failure,
    ...extra
  });
}

function resolvePureProtocolPageSummary(parsed, pageMatches = []) {
  const rowCount = Array.isArray(parsed?.d?.rows)
    ? parsed.d.rows.length
    : Array.isArray(parsed?.rows)
      ? parsed.rows.length
      : pageMatches.length;
  const total = Number(parsed?.d?.total) || Number(parsed?.total) || pageMatches.length;
  return { rowCount, total };
}

function buildPureProtocolHeaderAudit(handler, config = {}) {
  if (typeof handler?._buildPureProtocolHeaders !== 'function') {
    return {
      accept: String(config.accept || 'application/json, text/plain, */*'),
      referer: String(config.referer || ''),
      userAgent: '',
      origin: '',
      contentType: '',
      xRequestedWith: '',
      secFetchMode: '',
      secFetchDest: '',
      cookiePresent: Boolean(config.requestCookieHeader),
      cookieLength: String(config.requestCookieHeader || '').length
    };
  }

  const headers = handler._buildPureProtocolHeaders(
    config.referer,
    config.accept,
    {
      cookieHeader: config.requestCookieHeader || '',
      includeContentType: config.includeContentType,
      includeXRequestedWith: config.includeXRequestedWith,
      fetchMode: config.fetchMode,
      fetchDest: config.fetchDest,
      origin: config.origin,
      userAgent: config.userAgent
    }
  );

  return {
    accept: String(headers.accept || ''),
    referer: String(headers.referer || ''),
    userAgent: String(headers['user-agent'] || ''),
    origin: String(headers.origin || ''),
    contentType: String(headers['content-type'] || ''),
    xRequestedWith: String(headers['x-requested-with'] || ''),
    secFetchMode: String(headers['sec-fetch-mode'] || ''),
    secFetchDest: String(headers['sec-fetch-dest'] || ''),
    cookiePresent: Boolean(headers.cookie),
    cookieLength: String(headers.cookie || '').length
  };
}

function buildPureProtocolArchiveAudit(handler, config = {}, pageUrl = '') {
  return {
    requestedBaseUrl: String(config.requestedBaseUrl || ''),
    resolvedBaseUrl: String(config.resolvedBaseUrl || ''),
    contextSource: String(config.contextSource || ''),
    archiveToken: String(config.archiveToken || ''),
    sampleToken: String(config.sampleToken || ''),
    outrightId: String(config.outrightId || ''),
    tournamentId: String(config.tournamentId || ''),
    bookmakerHash: String(config.bookmakerHash || ''),
    pageUrl,
    proxyPort: Number(config.requestProxyPort || 0) || null,
    headers: buildPureProtocolHeaderAudit(handler, config)
  };
}

function logPureProtocolArchiveRawPayload(handler, eventName, config, page, pageUrl, response = {}, extra = {}) {
  const rawPayload = String(response?.text || '');
  handler.logger.warn(eventName, {
    ...buildPureProtocolArchiveAudit(handler, config, pageUrl),
    page,
    statusCode: Number(response?.status) || null,
    error: String(response?.error || ''),
    rawPayloadLength: rawPayload.length,
    rawPayload,
    ...extra
  });
}

function resolveWarmCachedDecryptor(handler) {
  const candidate = handler.navigator?.decryptor || handler.navigator?.networkMonitor?.decryptor || null;
  if (!candidate || typeof candidate.decrypt !== 'function') {
    return null;
  }

  if (typeof candidate.decryptFn !== 'function') {
    return null;
  }

  return {
    async decrypt(encryptedData) {
      return candidate.decrypt(encryptedData);
    },
    getAlgorithmVersion() {
      return typeof candidate.getAlgorithmVersion === 'function'
        ? candidate.getAlgorithmVersion()
        : null;
    }
  };
}

function resolvePureProtocolTokenPlan(context = {}) {
  const normalizedOutrightId = String(context?.outrightId || '').trim();
  const normalizedTournamentId = String(context?.tournamentId || '').trim();
  const sampleTokenCandidates = [...new Set([normalizedOutrightId, normalizedTournamentId].filter(Boolean))];
  const archiveTokenCandidates = normalizedOutrightId
    ? [normalizedOutrightId]
    : normalizedTournamentId
      ? [normalizedTournamentId]
      : [];

  return {
    sampleTokenCandidates,
    archiveTokenCandidates,
    preferredArchiveToken: archiveTokenCandidates[0] || ''
  };
}

function resolveSampleProxyFailoverConfig(options = {}) {
  return {
    maxProxyAttempts: Math.max(
      1,
      Number(options.sampleProxyFailoverMaxAttempts ?? PURE_PROTOCOL_FETCH_CONFIG.sample_proxy_failover_max_attempts ?? 3)
    ),
    retryDelayMs: Math.max(
      0,
      Number(options.sampleProxyFailoverRetryDelayMs ?? PURE_PROTOCOL_FETCH_CONFIG.sample_proxy_failover_retry_delay_ms ?? 250)
    ),
    fetchAttemptsPerProxy: Math.max(
      1,
      Number(options.sampleFetchAttemptsPerProxy ?? PURE_PROTOCOL_FETCH_CONFIG.sample_fetch_attempts_per_proxy ?? 1)
    )
  };
}

function resolveCurrentSampleProxyState(handler, options = {}) {
  const explicitLease = options.requestProxyLease?.proxy?.server
    ? options.requestProxyLease
    : options.proxyLease?.proxy?.server
      ? options.proxyLease
      : null;
  if (explicitLease) {
    return {
      lease: explicitLease,
      server: explicitLease.proxy.server,
      port: Number(explicitLease.proxy.port || 0) || null,
      temporary: false
    };
  }

  const navigatorLease = handler.navigator?.proxyLease?.proxy?.server
    ? handler.navigator.proxyLease
    : null;
  if (navigatorLease) {
    return {
      lease: navigatorLease,
      server: navigatorLease.proxy.server,
      port: Number(navigatorLease.proxy.port || 0) || null,
      temporary: false
    };
  }

  const explicitServer = String(options.proxyServer || '').trim();
  if (explicitServer) {
    return {
      lease: null,
      server: explicitServer,
      port: Number(options.proxyPort || 0) || null,
      temporary: false
    };
  }

  const navigatorProxy = handler.navigator?.proxy?.server
    ? handler.navigator.proxy
    : null;
  if (navigatorProxy?.server) {
    return {
      lease: null,
      server: navigatorProxy.server,
      port: Number(navigatorProxy.port || 0) || null,
      temporary: false
    };
  }

  return {
    lease: null,
    server: '',
    port: null,
    temporary: false
  };
}

function resolveSampleProxyProvider(handler) {
  const provider = handler.navigator?.proxyProvider || null;
  if (
    !provider
    || typeof provider.acquire !== 'function'
    || typeof provider.release !== 'function'
  ) {
    return null;
  }

  return provider;
}

function buildSampleFailureMetadata(result = {}, url = '') {
  const reason = String(result.error || 'PURE_PROTOCOL_SAMPLE_FETCH_FAILED');
  const statusCode = Number(result.status) || null;
  const failureClass = statusCode === 503 || reason.includes('503')
    ? 'upstream_block'
    : 'hard_proxy_failure';

  return {
    port: null,
    statusCode,
    reason,
    failureClass,
    url,
    stage: 'pure_protocol_sample'
  };
}

async function reportSampleProxyFailure(handler, proxyState, failureMetadata = {}) {
  const provider = resolveSampleProxyProvider(handler);
  if (!provider || !proxyState?.port) {
    return;
  }

  const metadata = {
    ...failureMetadata,
    port: proxyState.port
  };
  await provider.reportFailure(proxyState.lease?.id || null, metadata);
}

async function reportSampleProxySuccess(handler, proxyState, metadata = {}) {
  const provider = resolveSampleProxyProvider(handler);
  if (!provider || !proxyState?.port) {
    return;
  }

  await provider.reportSuccess(proxyState.lease?.id || null, {
    ...metadata,
    port: proxyState.port
  });
}

async function releaseTemporarySampleProxy(handler, proxyState) {
  const provider = resolveSampleProxyProvider(handler);
  if (!provider || !proxyState?.temporary || !proxyState.lease) {
    return;
  }

  await provider.release(proxyState.lease);
}

async function acquireRetrySampleProxy(handler, excludedPorts = [], attempt = 1) {
  const provider = resolveSampleProxyProvider(handler);
  if (!provider) {
    return null;
  }

  const lease = await provider.acquire({
    consumer: 'recon-pure-protocol-sample',
    sessionKey: `${handler.navigator?.traceId || 'trace-pure-protocol'}:sample:${attempt}`,
    sticky: false,
    excludePorts: [...new Set(excludedPorts.map(Number).filter(Boolean))],
    metadata: {
      reason: 'pure_protocol_sample_retry',
      traceId: handler.navigator?.traceId || 'trace-pure-protocol'
    }
  });

  if (!lease?.proxy?.server) {
    return null;
  }

  return {
    lease,
    server: lease.proxy.server,
    port: Number(lease.proxy.port || 0) || null,
    temporary: true
  };
}

async function resolvePureProtocolSample(handler, context, tokenCandidates = [], bookmakerHash = '', options = {}) {
  let samplePayload = '';
  let sampleToken = tokenCandidates[0] || '';
  const failoverConfig = resolveSampleProxyFailoverConfig(options);
  const failedPorts = new Set();
  let activeProxyState = resolveCurrentSampleProxyState(handler, options);
  let lastFailure = null;

  try {
    for (let proxyAttempt = 1; proxyAttempt <= failoverConfig.maxProxyAttempts; proxyAttempt++) {
      lastFailure = null;

      for (const token of tokenCandidates) {
        const sampleArchiveUrl = `https://www.oddsportal.com/ajax-sport-country-tournament-archive_/1/${token}/${bookmakerHash}/1/0/`;
        const sampleRequestUrl = handler._buildArchivePageUrl(sampleArchiveUrl.replace(/\/+$/, ''), 1);
        const sampleResponse = await handler._fetchPureProtocolText(
          sampleRequestUrl,
          {
            timeoutMs: options.timeoutMs,
            referer: context.baseUrl,
            maxAttempts: failoverConfig.fetchAttemptsPerProxy,
            retryDelayMs: failoverConfig.retryDelayMs,
            proxyLease: activeProxyState.lease || undefined,
            proxyServer: activeProxyState.server || undefined,
            proxyPort: activeProxyState.port || undefined
          }
        );

        if (sampleResponse.success && String(sampleResponse.text || '').trim()) {
          samplePayload = sampleResponse.text;
          sampleToken = token;
          await reportSampleProxySuccess(handler, activeProxyState, {
            statusCode: Number(sampleResponse.status) || 200,
            stage: 'pure_protocol_sample'
          });
          return {
            samplePayload,
            sampleToken,
            requestProxyLease: activeProxyState.lease || null,
            requestProxyServer: activeProxyState.server || '',
            requestProxyPort: activeProxyState.port || null
          };
        }

        lastFailure = sampleResponse.success
          ? {
            success: false,
            status: Number(sampleResponse.status) || null,
            error: 'EMPTY_SAMPLE_PAYLOAD',
            text: sampleResponse.text || '',
            url: sampleRequestUrl
          }
          : {
            ...sampleResponse,
            url: sampleRequestUrl
          };
      }

      if (!lastFailure || !handler._isRetryablePureProtocolFetchFailure(lastFailure)) {
        break;
      }

      if (activeProxyState.port) {
        failedPorts.add(activeProxyState.port);
      }
      await reportSampleProxyFailure(
        handler,
        activeProxyState,
        buildSampleFailureMetadata(lastFailure, lastFailure.url || '')
      );

      if (proxyAttempt >= failoverConfig.maxProxyAttempts || failedPorts.size === 0) {
        break;
      }

      const nextProxyState = await acquireRetrySampleProxy(
        handler,
        [...failedPorts],
        proxyAttempt + 1
      );

      await releaseTemporarySampleProxy(handler, activeProxyState);

      if (!nextProxyState) {
        break;
      }

      handler.logger.warn('pure_protocol_sample_proxy_switching', {
        traceId: handler.navigator?.traceId || 'trace-pure-protocol',
        fromProxyPort: activeProxyState.port || null,
        toProxyPort: nextProxyState.port || null,
        attempt: proxyAttempt + 1,
        maxAttempts: failoverConfig.maxProxyAttempts,
        error: lastFailure.error || '',
        statusCode: Number(lastFailure.status) || null
      });

      activeProxyState = nextProxyState;

      if (failoverConfig.retryDelayMs > 0) {
        await handler._waitPureProtocolFetchRetry(failoverConfig.retryDelayMs);
      }
    }
  } finally {
    if (!samplePayload) {
      await releaseTemporarySampleProxy(handler, activeProxyState);
    }
  }

  return {
    samplePayload,
    sampleToken,
    requestProxyLease: null,
    requestProxyServer: '',
    requestProxyPort: null
  };
}

async function resolvePureProtocolDecryptor(handler, context, samplePayload, sampleToken, bookmakerHash) {
  const cachedDecryptor = resolveWarmCachedDecryptor(handler);
  if (cachedDecryptor) {
    handler.logger.info('pure_protocol_cached_decryptor_hit', {
      baseUrl: context.baseUrl,
      algorithmVersion: cachedDecryptor.getAlgorithmVersion?.() || null
    });
    return cachedDecryptor;
  }

  if (!context.appBundleUrl) {
    throw new Error('PURE_PROTOCOL_APP_BUNDLE_MISSING');
  }

  return handler._createPureProtocolDecryptor(context, samplePayload, sampleToken, bookmakerHash);
}

function getProtocolRouteCache(handler) {
  if (!(handler.navigator._protocolRouteCache instanceof Map)) {
    handler.navigator._protocolRouteCache = new Map();
  }

  return handler.navigator._protocolRouteCache;
}

function readProtocolRouteCacheEntry(handler, cacheKey) {
  if (!cacheKey) {
    return {};
  }

  return getProtocolRouteCache(handler).get(cacheKey) || {};
}

function writeProtocolRouteCacheEntry(handler, cacheKey, patch = {}) {
  if (!cacheKey) {
    return {};
  }

  const cache = getProtocolRouteCache(handler);
  const current = cache.get(cacheKey) || {};
  const next = {
    ...current,
    ...patch,
    updatedAt: Date.now()
  };

  if (current.leagueContext || patch.leagueContext) {
    next.leagueContext = {
      ...(current.leagueContext || {}),
      ...(patch.leagueContext || {})
    };
  }

  cache.set(cacheKey, next);
  return next;
}

function resolveAdaptiveDiscoveryBudget(handler) {
  const configuredMaxWaitMs = Number(handler.navigator.postApiDiscoveryWaitMs || 5000);
  const maxWaitMs = Math.min(5000, Math.max(3000, configuredMaxWaitMs || 5000));

  return {
    minWaitMs: Math.min(3000, maxWaitMs),
    maxWaitMs,
    probeIntervalMs: 250
  };
}

async function waitForTournamentContextSignals(handler, archiveApiUrl) {
  const budget = resolveAdaptiveDiscoveryBudget(handler);
  const startedAt = Date.now();
  let tournamentToken = '';
  let currentTournamentUrl = null;

  while (Date.now() - startedAt <= budget.maxWaitMs) {
    tournamentToken = await handler.navigator.stateProber.extractTournamentToken();
    currentTournamentUrl = await handler._callNavigatorOverride(
      '_getCurrentTournamentEndpoint',
      () => handler._getCurrentTournamentEndpoint()
    ) || handler._callNavigatorOverride(
      '_buildTournamentUrlFromArchive',
      (resolvedArchiveUrl, resolvedTournamentToken) => handler._buildTournamentUrlFromArchive(
        resolvedArchiveUrl,
        resolvedTournamentToken
      ),
      archiveApiUrl,
      tournamentToken
    );

    const waitedMs = Date.now() - startedAt;
    if (((tournamentToken || currentTournamentUrl) && waitedMs >= budget.minWaitMs) || waitedMs >= budget.maxWaitMs) {
      handler.logger.info('protocol_tournament_context_budget_complete', {
        breakerKey: handler.navigator._resolveCircuitBreakerKey(archiveApiUrl || currentTournamentUrl || '', {}),
        waitedMs,
        hasTournamentToken: Boolean(tournamentToken),
        hasCurrentTournamentUrl: Boolean(currentTournamentUrl)
      });
      return {
        tournamentToken,
        currentTournamentUrl: currentTournamentUrl || null
      };
    }

    await waitForDelay(handler.page, Math.min(budget.probeIntervalMs, budget.maxWaitMs - waitedMs));
  }

  return {
    tournamentToken,
    currentTournamentUrl: currentTournamentUrl || null
  };
}

async function processPureProtocolPage(handler, monitor, config, state, page) {
  const pageUrl = config.buildPageUrl(state.base, page);
  const response = await handler._fetchPureProtocolText(pageUrl, {
    timeoutMs: config.timeoutMs,
    referer: config.referer,
    proxyLease: config.requestProxyLease || undefined,
    proxyServer: config.requestProxyServer || undefined,
    proxyPort: config.requestProxyPort || undefined
  });

  if (!response.success) {
    const httpFailure = {
      page,
      url: pageUrl,
      statusCode: Number(response.status) || null,
      error: response.error,
      retryAfterRaw: response.retryAfterRaw || '',
      retryAfterMs: 0
    };
    pushProtocolFailureStat(state.pageStats, page, pageUrl, httpFailure);
    if (page === 1 && state.matches.length === 0) {
      logPureProtocolArchiveRawPayload(
        handler,
        'pure_protocol_archive_http_failure_payload',
        config,
        page,
        pageUrl,
        response,
        {
          pageStatsState: 'http_failure'
        }
      );
    }
    return { done: true, httpFailure };
  }

  if (!String(response.text || '').trim()) {
    state.pageStats.push({
      page,
      url: pageUrl,
      rows: 0,
      total: state.matches.length,
      source: `${config.source}:empty`
    });
    if (page === 1 && state.matches.length === 0) {
      logPureProtocolArchiveRawPayload(
        handler,
        'pure_protocol_archive_blank_payload',
        config,
        page,
        pageUrl,
        response,
        {
          pageStatsState: 'blank_payload'
        }
      );
    }
    return { done: true, httpFailure: null };
  }

  try {
    const parsed = await config.decryptor.decrypt(response.text);
    const pageMatches = monitor.extractMatchesFromJson(parsed, config.source);
    const { rowCount, total } = resolvePureProtocolPageSummary(parsed, pageMatches);
    const beforeCount = state.matches.length;

    appendUniqueProtocolMatches(state.matches, state.seenHashes, pageMatches);
    state.pageStats.push({
      page,
      url: pageUrl,
      rows: rowCount,
      newRows: state.matches.length - beforeCount,
      total,
      source: config.source
    });

    if (page === 1 && beforeCount === 0 && rowCount === 0) {
      logPureProtocolArchiveRawPayload(
        handler,
        'pure_protocol_archive_zero_candidate_payload',
        config,
        page,
        pageUrl,
        response,
        {
          pageStatsState: 'zero_candidate_payload',
          parsedTopLevelKeys: Object.keys(parsed || {}).slice(0, 12),
          decryptedTotal: total,
          pageMatchesCount: Array.isArray(pageMatches) ? pageMatches.length : 0
        }
      );
    }

    return {
      done: rowCount === 0 && state.matches.length === beforeCount,
      httpFailure: null,
      total
    };
  } catch (error) {
    state.pageStats.push({ page, url: pageUrl, rows: 0, error: `decrypt_failed:${error.message}` });
    if (page === 1 && state.matches.length === 0) {
      logPureProtocolArchiveRawPayload(
        handler,
        'pure_protocol_archive_decrypt_failed_payload',
        config,
        page,
        pageUrl,
        response,
        {
          pageStatsState: 'decrypt_failed',
          decryptError: error.message
        }
      );
    }
    return { done: true, httpFailure: null };
  }
}

const reconFetchCoordinator = {
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
        await waitForDelay(this.page, Math.min(this.navigator.postApiDiscoveryWaitMs, 5000));
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
    const state = {
      base: config.buildBaseUrl(config.apiBaseUrl),
      seenHashes: new Set(),
      matches: [],
      pageStats: []
    };
    const monitor = this._createPureProtocolMonitor();
    monitor.sourceUrl = String(config.referer || config.apiBaseUrl || '').trim();
    let pageLimit = Math.max(1, Number(config.maxPages || 1));
    let httpFailure = null;

    for (let page = 1; page <= pageLimit; page++) {
      const outcome = await processPureProtocolPage(this, monitor, config, state, page);
      httpFailure = outcome.httpFailure;
      if (outcome.done) {
        break;
      }
      if (outcome.total > 0) {
        pageLimit = Math.min(pageLimit, Math.ceil(outcome.total / monitor.pageSize));
      }
    }

    return {
      matches: state.matches,
      pagesScanned: state.pageStats.length,
      totalCandidates: state.matches.length,
      pageStats: state.pageStats,
      httpFailure
    };
  },

  async _extractViaPureProtocol(target, options = {}) {
    const context = await this._resolvePureProtocolContext(target, options);
    const tokenPlan = resolvePureProtocolTokenPlan(context);
    const bookmakerHash = this._resolvePureProtocolBookmakerHash(context, options);
    if (tokenPlan.sampleTokenCandidates.length === 0) {
      throw new Error('PURE_PROTOCOL_TOURNAMENT_TOKEN_MISSING');
    }
    if (!bookmakerHash) {
      throw new Error('PURE_PROTOCOL_BOOKMAKER_HASH_MISSING');
    }

    const {
      samplePayload,
      sampleToken,
      requestProxyLease,
      requestProxyServer,
      requestProxyPort
    } = await resolvePureProtocolSample(
      this,
      context,
      tokenPlan.sampleTokenCandidates,
      bookmakerHash,
      options
    );
    if (!samplePayload) {
      throw new Error('PURE_PROTOCOL_SAMPLE_PAYLOAD_MISSING');
    }

    try {
      const decryptor = await resolvePureProtocolDecryptor(
        this,
        context,
        samplePayload,
        sampleToken,
        bookmakerHash
      );
      const combinedMatches = [];
      const combinedPageStats = [];
      const seen = new Set();

      for (const token of tokenPlan.archiveTokenCandidates) {
        const archiveApiUrl = `https://www.oddsportal.com/ajax-sport-country-tournament-archive_/1/${token}/${bookmakerHash}/1/0/`;
        this.logger.info('pure_protocol_archive_request_preflight', {
          requestedBaseUrl: context.requestedBaseUrl || context.baseUrl,
          resolvedBaseUrl: context.baseUrl,
          contextSource: context.contextSource || 'requested',
          archiveToken: token,
          sampleToken,
          outrightId: context.outrightId || null,
          tournamentId: context.tournamentId || null,
          bookmakerHash,
          archiveApiUrl,
          proxyPort: requestProxyPort || Number(this.navigator?.proxyLease?.proxy?.port || this.navigator?.proxy?.port || 0) || null,
          cookiePresent: Boolean(context.cookieHeader),
          cookieLength: String(context.cookieHeader || '').length,
          referer: context.baseUrl
        });

        const archiveResult = await this._fetchPureProtocolPaginatedPages({
          apiBaseUrl: archiveApiUrl,
          maxPages: options.maxPages ?? this.navigator.archiveMaxPages,
          timeoutMs: options.timeoutMs ?? this.navigator.archiveTimeoutMs,
          source: `pure_protocol_archive:${token}`,
          referer: context.baseUrl,
          decryptor,
          requestProxyLease,
          requestProxyServer,
          requestProxyPort,
          requestCookieHeader: context.cookieHeader || '',
          requestedBaseUrl: context.requestedBaseUrl || context.baseUrl,
          resolvedBaseUrl: context.baseUrl,
          contextSource: context.contextSource || 'requested',
          archiveToken: token,
          preferredArchiveToken: tokenPlan.preferredArchiveToken || '',
          sampleToken,
          outrightId: context.outrightId || '',
          tournamentId: context.tournamentId || '',
          bookmakerHash,
          buildBaseUrl: (url) => url.split('?')[0].replace(/\/page\/\d+\/?$/, '').replace(/\/+$/, ''),
          buildPageUrl: (base, page) => this._buildArchivePageUrl(base, page)
        });

        const archiveFirstTotal = archiveResult?.pageStats?.reduce((maxTotal, stat) => (
          Math.max(maxTotal, Math.max(0, Number(stat?.total || 0) || 0))
        ), 0) || 0;
        if ((archiveResult?.matches?.length || 0) === 0 && archiveFirstTotal === 0) {
          this.logger.info('pure_protocol_archive_empty_variant_skipped', {
            requestedBaseUrl: context.requestedBaseUrl || context.baseUrl,
            resolvedBaseUrl: context.baseUrl,
            archiveToken: token,
            preferredArchiveToken: tokenPlan.preferredArchiveToken || '',
            sampleToken,
            outrightId: context.outrightId || null,
            tournamentId: context.tournamentId || null,
            proxyPort: requestProxyPort || Number(this.navigator?.proxyLease?.proxy?.port || this.navigator?.proxy?.port || 0) || null,
            sourceState: archiveResult?.sourceState || 'SOURCE_EMPTY',
            pagesScanned: Number(archiveResult?.pagesScanned || archiveResult?.pageStats?.length || 0),
            totalCandidates: Number(archiveResult?.totalCandidates || archiveResult?.matches?.length || 0)
          });
          continue;
        }

        appendUniqueProtocolMatches(combinedMatches, seen, archiveResult.matches);
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
    } finally {
      if (
        requestProxyLease
        && requestProxyLease.id
        && requestProxyLease.id !== this.navigator?.proxyLease?.id
        && this.navigator?.proxyProvider
        && typeof this.navigator.proxyProvider.release === 'function'
      ) {
        await this.navigator.proxyProvider.release(requestProxyLease).catch((error) => {
          this.logger.warn('pure_protocol_sample_proxy_release_failed', {
            traceId: this.navigator?.traceId || 'trace-pure-protocol',
            proxyPort: Number(requestProxyLease?.proxy?.port || 0) || null,
            proxyLeaseId: requestProxyLease.id,
            error: error.message
          });
        });
      }
    }
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

    const cachedContext = readProtocolRouteCacheEntry(this, circuitBreakerKey).leagueContext || null;
    if (cachedContext?.tournamentId || cachedContext?.currentTournamentUrl) {
      return {
        leagueUrl: cachedContext.leagueUrl || leagueUrl,
        tournamentId: cachedContext.tournamentId || null,
        repairedArchiveUrl: cachedContext.tournamentId
          ? this._repairArchiveEndpointWithTournamentId(archiveApiUrl, cachedContext.tournamentId)
          : archiveApiUrl,
        currentTournamentUrl: cachedContext.currentTournamentUrl || null
      };
    }

    await this.navigator.navigate(leagueUrl, {
      waitUntil: 'domcontentloaded',
      timeout: timeoutMs,
      circuitBreakerKey
    });
    const discoveredContext = await waitForTournamentContextSignals(this, archiveApiUrl);
    const tournamentToken = String(discoveredContext.tournamentToken || '').trim();
    const repairedArchiveUrl = tournamentToken
      ? this._repairArchiveEndpointWithTournamentId(archiveApiUrl, tournamentToken)
      : archiveApiUrl;
    const resolvedContext = {
      leagueUrl,
      tournamentId: tournamentToken || null,
      repairedArchiveUrl,
      currentTournamentUrl: discoveredContext.currentTournamentUrl || null
    };

    writeProtocolRouteCacheEntry(this, circuitBreakerKey, {
      baseUrl,
      leagueContext: resolvedContext
    });

    return resolvedContext;
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
    return resolvedTournamentId
      ? `${match[1]}_/${match[2]}/${resolvedTournamentId}/${match[3]}/${match[4]}/`
      : null;
  },

  async _fallbackToLeagueTournament(baseUrl, archiveApiUrl, maxPages, timeoutMs, reason = 'fallback', options = {}) {
    const circuitBreakerKey = this.navigator._resolveCircuitBreakerKey(baseUrl, options);
    const context = await this._callNavigatorOverride(
      '_resolveLeagueTournamentContext',
      (resolvedBaseUrl, resolvedTimeoutMs, resolvedArchiveUrl, resolvedOptions) => (
        this._resolveLeagueTournamentContext(resolvedBaseUrl, resolvedTimeoutMs, resolvedArchiveUrl, resolvedOptions)
      ),
      baseUrl,
      timeoutMs,
      archiveApiUrl,
      { circuitBreakerKey }
    );

    if (!context.currentTournamentUrl) {
      return { matches: [], pagesScanned: 0, totalCandidates: 0, pageStats: [], sourceState: 'SOURCE_EMPTY' };
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

module.exports = {
  reconFetchCoordinator
};
