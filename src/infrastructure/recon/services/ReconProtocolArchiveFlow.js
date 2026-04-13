'use strict';

const { waitForDelay } = require('../../shared/helpers/browserUtils');

function decodeHtmlEntities(text = '') {
  return String(text || '')
    .replace(/&quot;/g, '"')
    .replace(/&#34;/g, '"')
    .replace(/&#39;/g, '\'')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>');
}

function buildArchiveFlowContext(handler, baseUrl, options = {}) {
  const maxPages = options.maxPages ?? handler.navigator.archiveMaxPages;
  const timeoutMs = options.timeoutMs ?? handler.navigator.archiveTimeoutMs;
  const readySelector = typeof options.readySelector === 'string' ? options.readySelector.trim() : '';
  const circuitBreakerKey = handler.navigator._resolveCircuitBreakerKey(baseUrl, options);

  return {
    maxPages,
    timeoutMs,
    readySelector,
    preferCurrentSeasonSource: options.preferCurrentSeasonSource === true,
    circuitBreakerKey,
    navigateOptions: readySelector
      ? { contentReadySelector: readySelector, circuitBreakerKey }
      : { circuitBreakerKey }
  };
}

function logArchiveCompletion(handler, result, context, extra = {}) {
  handler.logger.info('protocol_archive_complete', {
    pagesScanned: result.pageStats?.length || 0,
    totalCandidates: result.matches?.length || 0,
    sourceState: result.sourceState || extra.defaultSourceState,
    breakerKey: context.circuitBreakerKey,
    ...extra.meta
  });
}

async function fallbackToLeagueTournament(handler, baseUrl, archiveApiUrl, context, reason) {
  return handler._callNavigatorOverride(
    '_fallbackToLeagueTournament',
    (resolvedBaseUrl, resolvedArchiveUrl, resolvedMaxPages, resolvedTimeoutMs, resolvedReason, resolvedOptions) => (
      handler._fallbackToLeagueTournament(
        resolvedBaseUrl,
        resolvedArchiveUrl,
        resolvedMaxPages,
        resolvedTimeoutMs,
        resolvedReason,
        resolvedOptions
      )
    ),
    baseUrl,
    archiveApiUrl,
    context.maxPages,
    context.timeoutMs,
    reason,
    { circuitBreakerKey: context.circuitBreakerKey }
  );
}

function chooseArchiveEndpoint(handler, endpoints = []) {
  return [...endpoints].sort((left, right) => handler._scoreArchiveUrl(right) - handler._scoreArchiveUrl(left))[0] || null;
}

async function discoverArchiveEndpoints(handler, context) {
  let archiveEndpoints = Array.from(handler.navigator.apiEndpoints)
    .filter((url) => /ajax-sport-country-tournament-archive_/i.test(url));

  if (archiveEndpoints.length > 0) {
    return archiveEndpoints;
  }

  const resourceEndpoints = await handler._discoverArchiveEndpointsFromPageResources();
  archiveEndpoints = resourceEndpoints.filter((url) => /ajax-sport-country-tournament-archive_/i.test(url));

  if (archiveEndpoints.length > 0) {
    handler.logger.info('protocol_archive_resource_probe_hit', {
      endpointCount: archiveEndpoints.length,
      breakerKey: context.circuitBreakerKey
    });
  }

  return archiveEndpoints;
}

async function fetchForcedPureProtocol(handler, baseUrl, options, context) {
  let pureResult = null;
  let pureError = null;

  try {
    pureResult = await handler._callNavigatorOverride(
      '_extractViaPureProtocol',
      (resolvedTarget, resolvedOptions) => handler._extractViaPureProtocol(resolvedTarget, resolvedOptions),
      { url: baseUrl, baseUrl },
      options
    );
  } catch (error) {
    pureError = error;
  }

  if (context.preferCurrentSeasonSource && (!pureResult || pureResult.matches?.length === 0)) {
    const fallbackResult = await fallbackToLeagueTournament(
      handler,
      baseUrl,
      null,
      context,
      pureError ? 'pure_protocol_failed' : 'pure_protocol_source_empty'
    );
    if (Array.isArray(fallbackResult?.matches) && fallbackResult.matches.length > 0) {
      logArchiveCompletion(handler, fallbackResult, context, {
        defaultSourceState: 'CURRENT_TOURNAMENT_FALLBACK',
        meta: { pureProtocol: true }
      });
      return fallbackResult;
    }
  }

  if (pureError) {
    throw pureError;
  }

  logArchiveCompletion(handler, pureResult, context, {
    defaultSourceState: 'SOURCE_EMPTY',
    meta: { pureProtocol: true }
  });
  return pureResult;
}

async function fetchPreferredCurrentSeason(handler, baseUrl, context) {
  handler.logger.info('protocol_current_season_start', {
    baseUrl,
    maxPages: context.maxPages,
    breakerKey: context.circuitBreakerKey
  });

  const currentResult = await handler.navigator.stateProber.probeCurrentSeasonFromPageState(
    baseUrl,
    {
      maxPages: context.maxPages,
      timeoutMs: context.timeoutMs,
      maxScrollRounds: handler.navigator.scrollAttempts,
      readySelector: context.readySelector,
      circuitBreakerKey: context.circuitBreakerKey
    },
    handler._buildStateProbeHooks(context.navigateOptions, context.circuitBreakerKey)
  );

  logArchiveCompletion(handler, currentResult, context, { defaultSourceState: 'SOURCE_EMPTY' });
  return currentResult;
}

async function fetchArchiveApiResult(handler, baseUrl, context, archiveApiUrl) {
  const archiveContext = archiveApiUrl.includes('/1//')
    ? await handler._resolveLeagueTournamentContext(baseUrl, context.timeoutMs, archiveApiUrl, {
      circuitBreakerKey: context.circuitBreakerKey
    })
    : { repairedArchiveUrl: archiveApiUrl, currentTournamentUrl: null, leagueUrl: null, tournamentId: null };

  const result = await handler._callNavigatorOverride(
    '_fetchAndDecrypt',
    (resolvedUrl, resolvedMaxPages, resolvedTimeoutMs, resolvedOptions) => (
      handler._fetchAndDecrypt(resolvedUrl, resolvedMaxPages, resolvedTimeoutMs, resolvedOptions)
    ),
    archiveContext.repairedArchiveUrl || archiveApiUrl,
    context.maxPages,
    context.timeoutMs,
    {
      warmUrl: handler.navigator.stateProber.deriveCurrentResultsUrl(baseUrl) || baseUrl,
      circuitBreakerKey: context.circuitBreakerKey
    }
  );

  if (result.matches.length === 0 && handler._resultHasDecryptFailure(result)) {
    const fallbackResult = await fallbackToLeagueTournament(
      handler,
      baseUrl,
      archiveContext.repairedArchiveUrl || archiveApiUrl,
      context,
      'archive_decrypt_failed'
    );
    if (fallbackResult.matches.length > 0) {
      logArchiveCompletion(handler, fallbackResult, context, {
        defaultSourceState: 'CURRENT_TOURNAMENT_FALLBACK'
      });
      return fallbackResult;
    }
  }

  logArchiveCompletion(handler, result, context);
  return result;
}

const reconProtocolArchiveFlow = {
  _extractCurrentTournamentEndpointFromHtml(html) {
    const decodedHtml = decodeHtmlEntities(String(html || ''));
    const rawUrl = decodedHtml.match(/oddsRequest"\s*:\s*{\s*"url"\s*:\s*"([^"]*ajax-sport-country-tournament_[^"]+)"/i)?.[1]
      || decodedHtml.match(/:odds-request\s*=\s*"\{\s*"url"\s*:\s*"([^"]*ajax-sport-country-tournament_[^"]+)"/i)?.[1]
      || '';
    const normalizedUrl = String(rawUrl || '').replace(/\\\//g, '/').trim();
    if (!normalizedUrl || /archive_/i.test(normalizedUrl)) {
      return null;
    }

    const pageUrl = this.page && typeof this.page.url === 'function'
      ? String(this.page.url() || '').trim()
      : '';

    try {
      return new URL(normalizedUrl, pageUrl || 'https://www.oddsportal.com/').href;
    } catch {
      return normalizedUrl;
    }
  },

  _resultHasDecryptFailure(result) {
    return Array.isArray(result?.pageStats)
      && result.pageStats.some((stat) => typeof stat?.error === 'string' && stat.error.startsWith('decrypt_failed:'));
  },

  async _getCurrentTournamentEndpoint() {
    const endpoints = Array.from(this.navigator.apiEndpoints)
      .filter((url) => /ajax-sport-country-tournament_\/\d+\/[^/]+\/X/i.test(url))
      .filter((url) => !/archive_/i.test(url));

    if (endpoints.length > 0) {
      return endpoints.sort((left, right) => this._scoreTournamentUrl(right) - this._scoreTournamentUrl(left))[0];
    }

    if (!this.page || typeof this.page.content !== 'function') {
      return null;
    }

    try {
      const extracted = this._extractCurrentTournamentEndpointFromHtml(await this.page.content());
      if (extracted) {
        this.navigator.apiEndpoints.add(extracted);
      }
      return extracted;
    } catch {
      return null;
    }
  },

  _scoreTournamentUrl(url) {
    let score = 0;
    if (/ajax-sport-country-tournament_\/\d+\/[^/]+\/X/i.test(url)) score += 10;
    if (!/\/\d+\/\?_=/i.test(url)) score += 2;
    score += Math.min(url.length / 100, 3);
    return score;
  },

  _scoreArchiveUrl(url) {
    let score = 0;
    if (!url.includes('/1//')) score += 5;
    if (/\/archive_\/\d+\/[^/]+\/[^/]+\/\d+\/\d+\//i.test(url)) score += 8;
    if (/\/page\/\d+\//i.test(url)) score += 2;
    score += Math.min(url.length / 100, 3);
    return score;
  },

  _buildStateProbeHooks(defaultNavigateOptions = {}, circuitBreakerKey = 'default') {
    return {
      navigate: (url, options) => this.navigator.navigate(url, { ...options, ...defaultNavigateOptions }),
      waitForTimeout: async (ms) => waitForDelay(this.page, ms),
      getInterceptedData: () => this.navigator.getInterceptedData(),
      getApiEndpoints: () => Array.from(this.navigator.apiEndpoints),
      scoreArchiveUrl: (url) => this._callNavigatorOverride('_scoreArchiveUrl', (resolvedUrl) => this._scoreArchiveUrl(resolvedUrl), url),
      fetchArchive: (url, maxPages, timeoutMs) => this._callNavigatorOverride(
        '_fetchAndDecrypt',
        (resolvedUrl, resolvedMaxPages, resolvedTimeoutMs, resolvedOptions) => (
          this._fetchAndDecrypt(resolvedUrl, resolvedMaxPages, resolvedTimeoutMs, resolvedOptions)
        ),
        url,
        maxPages,
        timeoutMs,
        { circuitBreakerKey }
      ),
      collectCurrentSeasonResultsDom: (currentResultsUrl, options = {}) => {
        this.navigator.domScraper.setPage(this.page);
        return this.navigator.domScraper.collectCurrentSeasonResults(currentResultsUrl, {
          ...options,
          maxScrollRounds: options.maxScrollRounds || this.navigator.scrollAttempts,
          scrollDelayMs: this.navigator.scrollDelayMs
        });
      },
      getCurrentTournamentEndpoint: () => this._callNavigatorOverride('_getCurrentTournamentEndpoint', () => this._getCurrentTournamentEndpoint()),
      buildCurrentTournamentUrlFromArchive: (url) => this._callNavigatorOverride(
        '_buildTournamentUrlFromArchive',
        (resolvedUrl) => this._buildTournamentUrlFromArchive(resolvedUrl),
        url
      ),
      fetchCurrentTournament: (url, maxPages, timeoutMs) => this._callNavigatorOverride(
        '_fetchCurrentTournament',
        (resolvedUrl, resolvedMaxPages, resolvedTimeoutMs, resolvedOptions) => (
          this._fetchCurrentTournament(resolvedUrl, resolvedMaxPages, resolvedTimeoutMs, resolvedOptions)
        ),
        url,
        maxPages,
        timeoutMs,
        { circuitBreakerKey }
      )
    };
  },

  async _discoverArchiveEndpointsFromPageResources() {
    if (!this.page || typeof this.page.evaluate !== 'function') {
      return [];
    }

    try {
      const endpoints = await this.page.evaluate(() => {
        const resourceEntries = Array.isArray(performance.getEntriesByType('resource'))
          ? performance.getEntriesByType('resource')
          : [];
        const discovered = new Set();

        for (const entry of resourceEntries) {
          if (entry?.name && typeof entry.name === 'string' && /ajax-sport-country-tournament-archive_/i.test(entry.name)) {
            discovered.add(entry.name.trim());
          }
        }

        return [...discovered];
      });

      const normalized = Array.isArray(endpoints)
        ? endpoints.map((url) => String(url || '').trim()).filter(Boolean)
        : [];
      for (const endpoint of normalized) {
        this.navigator.apiEndpoints.add(endpoint);
      }
      return normalized;
    } catch (error) {
      if (typeof this.logger?.debug === 'function') {
        this.logger.debug('protocol_archive_resource_probe_failed', { error: error.message });
      }
      return [];
    }
  },

  async protocolArchiveExtract(baseUrl, options = {}) {
    const context = buildArchiveFlowContext(this, baseUrl, options);

    if (options.forcePureProtocol === true) {
      return fetchForcedPureProtocol(this, baseUrl, options, context);
    }

    if (typeof this.navigator.resetContextPerBatch === 'function') {
      await this.navigator.resetContextPerBatch({ reason: 'protocol_archive_extract' });
    } else {
      await this.navigator.ensureBrowserHealthy();
    }

    if (context.preferCurrentSeasonSource) {
      return fetchPreferredCurrentSeason(this, baseUrl, context);
    }

    this.logger.info('protocol_archive_start', {
      baseUrl,
      maxPages: context.maxPages,
      breakerKey: context.circuitBreakerKey
    });

    await this.navigator.navigate(baseUrl, { waitUntil: 'domcontentloaded', ...context.navigateOptions });
    await waitForDelay(this.page, this.navigator.postApiDiscoveryWaitMs);

    const archiveEndpoints = await discoverArchiveEndpoints(this, context);
    if (archiveEndpoints.length === 0) {
      this.logger.warn('protocol_archive_no_api');
      return fallbackToLeagueTournament(this, baseUrl, null, context, 'archive_api_missing');
    }

    return fetchArchiveApiResult(this, baseUrl, context, chooseArchiveEndpoint(this, archiveEndpoints));
  }
};

module.exports = { reconProtocolArchiveFlow };
