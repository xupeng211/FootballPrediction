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
        await waitForDelay(this.page, this.navigator.postApiDiscoveryWaitMs);
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
    if (!context.appBundleUrl) {
      throw new Error('PURE_PROTOCOL_APP_BUNDLE_MISSING');
    }

    const tokenCandidates = [...new Set([context.outrightId, context.tournamentId].map((token) => String(token || '').trim()).filter(Boolean))];
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

    const decryptor = await this._createPureProtocolDecryptor(context, samplePayload, sampleToken, bookmakerHash);
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

    await this.navigator.navigate(leagueUrl, {
      waitUntil: 'domcontentloaded',
      timeout: timeoutMs,
      circuitBreakerKey
    });
    await waitForDelay(this.page, this.navigator.postApiDiscoveryWaitMs);

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
