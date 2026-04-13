'use strict';

const { waitForDelay } = require('../../shared/helpers/browserUtils');
const { ReconEndpointHelper } = require('./ReconEndpointHelper');

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

async function resolvePureProtocolSample(handler, context, tokenCandidates = [], bookmakerHash = '', options = {}) {
  let samplePayload = '';
  let sampleToken = tokenCandidates[0] || '';

  for (const token of tokenCandidates) {
    const sampleArchiveUrl = `https://www.oddsportal.com/ajax-sport-country-tournament-archive_/1/${token}/${bookmakerHash}/1/0/`;
    const sampleResponse = await handler._fetchPureProtocolText(
      handler._buildArchivePageUrl(sampleArchiveUrl.replace(/\/+$/, ''), 1),
      {
        timeoutMs: options.timeoutMs,
        referer: context.baseUrl
      }
    );
    if (sampleResponse.success && String(sampleResponse.text || '').trim()) {
      samplePayload = sampleResponse.text;
      sampleToken = token;
      break;
    }
  }

  return { samplePayload, sampleToken };
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
    referer: config.referer
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

    return {
      done: rowCount === 0 && state.matches.length === beforeCount,
      httpFailure: null,
      total
    };
  } catch (error) {
    state.pageStats.push({ page, url: pageUrl, rows: 0, error: `decrypt_failed:${error.message}` });
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
    const tokenCandidates = [...new Set([context.outrightId, context.tournamentId].map((token) => String(token || '').trim()).filter(Boolean))];
    const bookmakerHash = this._resolvePureProtocolBookmakerHash(context, options);
    if (tokenCandidates.length === 0) {
      throw new Error('PURE_PROTOCOL_TOURNAMENT_TOKEN_MISSING');
    }
    if (!bookmakerHash) {
      throw new Error('PURE_PROTOCOL_BOOKMAKER_HASH_MISSING');
    }

    const { samplePayload, sampleToken } = await resolvePureProtocolSample(
      this,
      context,
      tokenCandidates,
      bookmakerHash,
      options
    );
    if (!samplePayload) {
      throw new Error('PURE_PROTOCOL_SAMPLE_PAYLOAD_MISSING');
    }

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

    for (const token of tokenCandidates) {
      const archiveResult = await this._fetchPureProtocolPaginatedPages({
        apiBaseUrl: `https://www.oddsportal.com/ajax-sport-country-tournament-archive_/1/${token}/${bookmakerHash}/1/0/`,
        maxPages: options.maxPages ?? this.navigator.archiveMaxPages,
        timeoutMs: options.timeoutMs ?? this.navigator.archiveTimeoutMs,
        source: `pure_protocol_archive:${token}`,
        referer: context.baseUrl,
        decryptor,
        buildBaseUrl: (url) => url.split('?')[0].replace(/\/page\/\d+\/?$/, '').replace(/\/+$/, ''),
        buildPageUrl: (base, page) => this._buildArchivePageUrl(base, page)
      });
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
