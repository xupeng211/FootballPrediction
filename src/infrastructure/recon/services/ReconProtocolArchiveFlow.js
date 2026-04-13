/* eslint-disable max-lines */
'use strict';

const { waitForDelay } = require('../../shared/helpers/browserUtils');
const { ReconEndpointHelper } = require('./ReconEndpointHelper');

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
    baseUrl,
    maxPages,
    timeoutMs,
    readySelector,
    preferCurrentSeasonSource: options.preferCurrentSeasonSource === true,
    disableTournamentFallback: options.disableTournamentFallback === true,
    leagueDeadlineAt: normalizeLeagueDeadlineAt(options.leagueDeadlineAt),
    circuitBreakerKey,
    navigateOptions: readySelector
      ? { contentReadySelector: readySelector, circuitBreakerKey }
      : { circuitBreakerKey }
  };
}

function normalizeLeagueDeadlineAt(deadlineAt) {
  const normalized = Number(deadlineAt);
  return Number.isFinite(normalized) && normalized > 0 ? normalized : null;
}

function buildLeagueTimeoutError(context, stage = 'protocol_archive_timeout') {
  const error = new Error('LEAGUE_TIMEOUT');
  error.code = 'LEAGUE_TIMEOUT';
  error.stage = stage;
  error.sourceUrl = context.baseUrl;
  error.sourceSeason = null;
  return error;
}

function resolveRemainingLeagueBudgetMs(context) {
  if (!Number.isFinite(context?.leagueDeadlineAt)) {
    return null;
  }

  return Number(context.leagueDeadlineAt) - Date.now();
}

function assertLeagueBudget(handler, context, stage) {
  const remainingBudgetMs = resolveRemainingLeagueBudgetMs(context);
  if (remainingBudgetMs === null || remainingBudgetMs > 0) {
    return remainingBudgetMs;
  }

  handler.logger.warn('protocol_archive_league_timeout', {
    baseUrl: context.baseUrl,
    breakerKey: context.circuitBreakerKey,
    stage
  });
  throw buildLeagueTimeoutError(context, stage);
}

function resolveOperationTimeoutMs(handler, context, stage, fallbackTimeoutMs = null) {
  const remainingBudgetMs = assertLeagueBudget(handler, context, stage);
  const normalizedFallbackTimeoutMs = Math.max(
    1,
    Number(fallbackTimeoutMs ?? context.timeoutMs ?? handler.navigator.archiveTimeoutMs) || 1
  );

  if (remainingBudgetMs === null) {
    return normalizedFallbackTimeoutMs;
  }

  return Math.max(1, Math.min(normalizedFallbackTimeoutMs, remainingBudgetMs));
}

function buildEmptyArchiveResult(sourceState = 'SOURCE_EMPTY') {
  return {
    matches: [],
    pagesScanned: 0,
    totalCandidates: 0,
    pageStats: [],
    sourceState
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
  if (context.disableTournamentFallback) {
    handler.logger.info('protocol_archive_tournament_fallback_skipped', {
      baseUrl,
      reason,
      breakerKey: context.circuitBreakerKey
    });
    return buildEmptyArchiveResult('SOURCE_EMPTY');
  }

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
    resolveOperationTimeoutMs(handler, context, `fallback_${reason}`),
    reason,
    { circuitBreakerKey: context.circuitBreakerKey }
  );
}

function chooseArchiveEndpoint(handler, endpoints = []) {
  return [...endpoints].sort((left, right) => handler._scoreArchiveUrl(right) - handler._scoreArchiveUrl(left))[0] || null;
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

  if (Array.isArray(current.archiveEndpoints) || Array.isArray(patch.archiveEndpoints)) {
    next.archiveEndpoints = [...new Set(
      [
        ...(Array.isArray(current.archiveEndpoints) ? current.archiveEndpoints : []),
        ...(Array.isArray(patch.archiveEndpoints) ? patch.archiveEndpoints : [])
      ]
        .map((url) => String(url || '').trim())
        .filter((url) => /ajax-sport-country-tournament-archive_/i.test(url))
    )];
  }

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

function normalizeComparableResultsUrl(handler, url) {
  const normalized = typeof handler.navigator.domScraper?.normalizeResultsUrl === 'function'
    ? handler.navigator.domScraper.normalizeResultsUrl(url)
    : String(url || '').trim().split('#')[0].split('?')[0].replace(/\/+$/, '/');

  return String(normalized || '').trim();
}

function isReusableResultsPage(handler, baseUrl) {
  const currentUrl = typeof handler.page?.url === 'function'
    ? handler.page.url()
    : '';

  if (!currentUrl) {
    return false;
  }

  return normalizeComparableResultsUrl(handler, currentUrl) === normalizeComparableResultsUrl(handler, baseUrl);
}

function resolveSeedArchiveEndpoints(handler, context, options = {}) {
  const seededEndpoints = Array.isArray(options.seedArchiveEndpoints)
    ? options.seedArchiveEndpoints
    : [];
  const cachedEndpoints = readProtocolRouteCacheEntry(handler, context.circuitBreakerKey).archiveEndpoints || [];
  const endpoints = [...new Set(
    [...seededEndpoints, ...cachedEndpoints]
      .map((url) => String(url || '').trim())
      .filter((url) => /ajax-sport-country-tournament-archive_/i.test(url))
  )];

  if (endpoints.length > 0) {
    writeProtocolRouteCacheEntry(handler, context.circuitBreakerKey, {
      baseUrl: context.baseUrl,
      archiveEndpoints: endpoints
    });
  }

  return endpoints;
}

function resultHasMatches(result) {
  return Array.isArray(result?.matches) && result.matches.length > 0;
}

function buildBlindArchiveUrl(token = '', bookmakerHash = '') {
  const resolvedToken = String(token || '').trim();
  const resolvedBookmakerHash = String(bookmakerHash || '').trim();
  if (!resolvedToken || !/^X(?:\d+X)*\d+$/i.test(resolvedBookmakerHash)) {
    return '';
  }

  return `https://www.oddsportal.com/ajax-sport-country-tournament-archive_/1/${resolvedToken}/${resolvedBookmakerHash}/1/0/`;
}

function buildBlindLogMeta(context, strategy, extra = {}) {
  return {
    baseUrl: context.baseUrl,
    breakerKey: context.circuitBreakerKey,
    strategy,
    ...extra
  };
}

function logBlindHit(handler, context, strategy, result, extra = {}) {
  handler.logger.info('protocol_archive_blind_hit', {
    ...buildBlindLogMeta(context, strategy, extra),
    totalCandidates: result.matches?.length || 0,
    pagesScanned: result.pageStats?.length || result.pagesScanned || 0,
    sourceState: result.sourceState || 'SOURCE_EMPTY'
  });
}

function logBlindMiss(handler, context, strategy, extra = {}) {
  handler.logger.info('protocol_archive_blind_miss', {
    ...buildBlindLogMeta(context, strategy, extra)
  });
}

function resolveBlindLeagueContext(handler, context) {
  return readProtocolRouteCacheEntry(handler, context.circuitBreakerKey).leagueContext || {};
}

function resolveBlindArchiveCandidates(handler, context, seedArchiveEndpoints = []) {
  const cachedLeagueContext = resolveBlindLeagueContext(handler, context);
  const tournamentId = String(cachedLeagueContext.tournamentId || '').trim();
  const candidates = [
    ...seedArchiveEndpoints,
    cachedLeagueContext.repairedArchiveUrl || ''
  ]
    .map((url) => String(url || '').trim())
    .filter((url) => /ajax-sport-country-tournament-archive_/i.test(url))
    .map((url) => {
      if (!ReconEndpointHelper.hasMissingTournamentToken(url)) {
        return url;
      }

      return tournamentId
        ? handler._repairArchiveEndpointWithTournamentId(url, tournamentId)
        : '';
    })
    .filter(Boolean);

  return [...new Set(candidates)]
    .sort((left, right) => handler._scoreArchiveUrl(right) - handler._scoreArchiveUrl(left));
}

function resolveBlindCurrentTournamentUrl(handler, context, archiveApiUrl = '') {
  const cachedLeagueContext = resolveBlindLeagueContext(handler, context);
  const cachedTournamentUrl = String(cachedLeagueContext.currentTournamentUrl || '').trim();
  if (cachedTournamentUrl) {
    return cachedTournamentUrl;
  }

  const tournamentId = String(cachedLeagueContext.tournamentId || '').trim();
  const repairedArchiveUrl = String(cachedLeagueContext.repairedArchiveUrl || archiveApiUrl || '').trim();
  if (!tournamentId || !repairedArchiveUrl) {
    return '';
  }

  return handler._callNavigatorOverride(
    '_buildTournamentUrlFromArchive',
    (resolvedArchiveUrl, resolvedTournamentId) => handler._buildTournamentUrlFromArchive(
      resolvedArchiveUrl,
      resolvedTournamentId
    ),
    repairedArchiveUrl,
    tournamentId
  ) || '';
}

function cacheBlindPureProtocolContext(handler, context, result) {
  const meta = result?.pureProtocolMeta || {};
  const tournamentId = String(meta.tournamentId || meta.outrightId || '').trim();
  const archiveApiUrl = buildBlindArchiveUrl(tournamentId, meta.bookmakerHash);
  if (!archiveApiUrl) {
    return;
  }

  const leagueUrl = handler.navigator.stateProber?.deriveLeaguePageUrl?.(context.baseUrl) || null;
  const currentTournamentUrl = handler._callNavigatorOverride(
    '_buildTournamentUrlFromArchive',
    (resolvedArchiveUrl, resolvedTournamentId) => handler._buildTournamentUrlFromArchive(
      resolvedArchiveUrl,
      resolvedTournamentId
    ),
    archiveApiUrl,
    tournamentId
  ) || null;

  writeProtocolRouteCacheEntry(handler, context.circuitBreakerKey, {
    baseUrl: context.baseUrl,
    archiveEndpoints: [archiveApiUrl],
    leagueContext: {
      leagueUrl,
      tournamentId: tournamentId || null,
      repairedArchiveUrl: archiveApiUrl,
      currentTournamentUrl
    }
  });
}

async function resolveBlindHtmlArchiveCandidate(handler, baseUrl, context, options = {}) {
  const timeoutMs = resolveOperationTimeoutMs(handler, context, 'blind_html_state_probe');
  let pureContext = null;

  try {
    pureContext = await handler._callNavigatorOverride(
      '_resolvePureProtocolContext',
      (resolvedTarget, resolvedOptions) => handler._resolvePureProtocolContext(resolvedTarget, resolvedOptions),
      { url: baseUrl, baseUrl },
      {
        ...options,
        timeoutMs,
        leagueDeadlineAt: context.leagueDeadlineAt,
        allowBrowserHtmlFallback: false,
        allowRuntimeStateProbe: false
      }
    );
  } catch (error) {
    logBlindMiss(handler, context, 'html_state_archive_endpoint', { error: error.message });
    return '';
  }

  const tournamentId = String(pureContext?.outrightId || pureContext?.tournamentId || '').trim();
  const bookmakerHash = handler._callNavigatorOverride(
    '_resolvePureProtocolBookmakerHash',
    (resolvedTarget, resolvedOptions) => handler._resolvePureProtocolBookmakerHash(resolvedTarget, resolvedOptions),
    pureContext || {},
    options
  );
  const archiveApiUrl = buildBlindArchiveUrl(tournamentId, bookmakerHash);

  if (!archiveApiUrl) {
    logBlindMiss(handler, context, 'html_state_archive_endpoint', {
      tournamentId: tournamentId || null,
      bookmakerHash: bookmakerHash || null
    });
    return '';
  }

  const leagueUrl = handler.navigator.stateProber?.deriveLeaguePageUrl?.(context.baseUrl) || null;
  const currentTournamentUrl = handler._callNavigatorOverride(
    '_buildTournamentUrlFromArchive',
    (resolvedArchiveUrl, resolvedTournamentId) => handler._buildTournamentUrlFromArchive(
      resolvedArchiveUrl,
      resolvedTournamentId
    ),
    archiveApiUrl,
    tournamentId
  ) || null;

  writeProtocolRouteCacheEntry(handler, context.circuitBreakerKey, {
    baseUrl: context.baseUrl,
    archiveEndpoints: [archiveApiUrl],
    leagueContext: {
      leagueUrl,
      tournamentId: tournamentId || null,
      repairedArchiveUrl: archiveApiUrl,
      currentTournamentUrl
    }
  });

  return archiveApiUrl;
}

async function discoverArchiveEndpoints(handler, context) {
  let archiveEndpoints = Array.from(handler.navigator.apiEndpoints)
    .filter((url) => /ajax-sport-country-tournament-archive_/i.test(url));

  if (archiveEndpoints.length > 0) {
    writeProtocolRouteCacheEntry(handler, context.circuitBreakerKey, {
      baseUrl: context.baseUrl,
      archiveEndpoints
    });
    return archiveEndpoints;
  }

  const resourceEndpoints = await handler._discoverArchiveEndpointsFromPageResources();
  archiveEndpoints = resourceEndpoints.filter((url) => /ajax-sport-country-tournament-archive_/i.test(url));

  if (archiveEndpoints.length > 0) {
    writeProtocolRouteCacheEntry(handler, context.circuitBreakerKey, {
      baseUrl: context.baseUrl,
      archiveEndpoints
    });
    handler.logger.info('protocol_archive_resource_probe_hit', {
      endpointCount: archiveEndpoints.length,
      breakerKey: context.circuitBreakerKey
    });
  }

  return archiveEndpoints;
}

async function waitForArchiveEndpoints(handler, context) {
  const budget = resolveAdaptiveDiscoveryBudget(handler);
  const startedAt = Date.now();
  let archiveEndpoints = [];
  const initialRemainingBudgetMs = resolveRemainingLeagueBudgetMs(context);
  const effectiveMaxWaitMs = initialRemainingBudgetMs === null
    ? budget.maxWaitMs
    : Math.max(1, Math.min(budget.maxWaitMs, initialRemainingBudgetMs));
  const effectiveMinWaitMs = Math.min(budget.minWaitMs, effectiveMaxWaitMs);

  while (Date.now() - startedAt <= effectiveMaxWaitMs) {
    assertLeagueBudget(handler, context, 'discover_archive_endpoints');
    archiveEndpoints = await discoverArchiveEndpoints(handler, context);
    const waitedMs = Date.now() - startedAt;

    if ((archiveEndpoints.length > 0 && waitedMs >= effectiveMinWaitMs) || waitedMs >= effectiveMaxWaitMs) {
      handler.logger.info('protocol_archive_discovery_budget_complete', {
        endpointCount: archiveEndpoints.length,
        waitedMs,
        breakerKey: context.circuitBreakerKey
      });
      return archiveEndpoints;
    }

    await waitForDelay(handler.page, Math.min(budget.probeIntervalMs, Math.max(1, effectiveMaxWaitMs - waitedMs)));
  }

  return archiveEndpoints;
}

async function fetchForcedPureProtocol(handler, baseUrl, options, context) {
  let pureResult = null;
  let pureError = null;
  const pureProtocolTimeoutMs = resolveOperationTimeoutMs(handler, context, 'forced_pure_protocol');

  try {
    pureResult = await handler._callNavigatorOverride(
      '_extractViaPureProtocol',
      (resolvedTarget, resolvedOptions) => handler._extractViaPureProtocol(resolvedTarget, resolvedOptions),
      { url: baseUrl, baseUrl },
      {
        ...options,
        timeoutMs: pureProtocolTimeoutMs,
        leagueDeadlineAt: context.leagueDeadlineAt
      }
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
  const timeoutMs = resolveOperationTimeoutMs(handler, context, 'preferred_current_season');
  handler.logger.info('protocol_current_season_start', {
    baseUrl,
    maxPages: context.maxPages,
    timeoutMs,
    breakerKey: context.circuitBreakerKey
  });

  const currentResult = await handler.navigator.stateProber.probeCurrentSeasonFromPageState(
    baseUrl,
    {
      maxPages: context.maxPages,
      timeoutMs,
      maxScrollRounds: handler.navigator.scrollAttempts,
      readySelector: context.readySelector,
      disableTournamentFallback: context.disableTournamentFallback,
      circuitBreakerKey: context.circuitBreakerKey
    },
    handler._buildStateProbeHooks(context.navigateOptions, context.circuitBreakerKey)
  );

  logArchiveCompletion(handler, currentResult, context, { defaultSourceState: 'SOURCE_EMPTY' });
  return currentResult;
}

async function fetchArchiveApiResult(handler, baseUrl, context, archiveApiUrl) {
  const timeoutMs = resolveOperationTimeoutMs(handler, context, 'archive_api_fetch');
  const archiveContext = archiveApiUrl.includes('/1//')
    ? await handler._resolveLeagueTournamentContext(baseUrl, timeoutMs, archiveApiUrl, {
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
    timeoutMs,
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

async function tryBlindArchiveEndpoint(handler, baseUrl, context, archiveApiUrl, strategy) {
  await handler.navigator.ensureBrowserHealthy();
  const timeoutMs = resolveOperationTimeoutMs(handler, context, 'blind_archive_api_fetch');
  const result = await handler._callNavigatorOverride(
    '_fetchAndDecrypt',
    (resolvedUrl, resolvedMaxPages, resolvedTimeoutMs, resolvedOptions) => (
      handler._fetchAndDecrypt(resolvedUrl, resolvedMaxPages, resolvedTimeoutMs, resolvedOptions)
    ),
    archiveApiUrl,
    context.maxPages,
    timeoutMs,
    {
      warmUrl: handler.navigator.stateProber.deriveCurrentResultsUrl(baseUrl) || baseUrl,
      circuitBreakerKey: context.circuitBreakerKey,
      allowRecovery: false
    }
  );

  if (!resultHasMatches(result)) {
    logBlindMiss(handler, context, strategy, {
      archiveApiUrl,
      decryptFailure: handler._resultHasDecryptFailure(result),
      totalCandidates: result.matches?.length || 0,
      sourceState: result.sourceState || 'SOURCE_EMPTY'
    });
    return null;
  }

  logArchiveCompletion(handler, result, context);
  logBlindHit(handler, context, strategy, result, { archiveApiUrl });
  return result;
}

async function tryBlindCurrentTournament(handler, context, currentTournamentUrl, strategy) {
  if (!currentTournamentUrl || context.disableTournamentFallback) {
    return null;
  }

  await handler.navigator.ensureBrowserHealthy();
  const timeoutMs = resolveOperationTimeoutMs(handler, context, 'blind_current_tournament');
  const result = await handler._callNavigatorOverride(
    '_fetchCurrentTournament',
    (resolvedUrl, resolvedMaxPages, resolvedTimeoutMs, resolvedOptions) => (
      handler._fetchCurrentTournament(resolvedUrl, resolvedMaxPages, resolvedTimeoutMs, resolvedOptions)
    ),
    currentTournamentUrl,
    context.maxPages,
    timeoutMs,
    {
      circuitBreakerKey: context.circuitBreakerKey,
      retryNavigateUrl: null
    }
  );
  const normalizedResult = {
    ...result,
    sourceState: resultHasMatches(result) ? 'CURRENT_TOURNAMENT_FALLBACK' : 'SOURCE_EMPTY'
  };

  if (!resultHasMatches(normalizedResult)) {
    logBlindMiss(handler, context, strategy, {
      currentTournamentUrl,
      totalCandidates: normalizedResult.matches?.length || 0,
      sourceState: normalizedResult.sourceState
    });
    return null;
  }

  logArchiveCompletion(handler, normalizedResult, context, {
    defaultSourceState: 'CURRENT_TOURNAMENT_FALLBACK'
  });
  logBlindHit(handler, context, strategy, normalizedResult, { currentTournamentUrl });
  return normalizedResult;
}

async function tryBlindPureProtocol(handler, baseUrl, context, options = {}) {
  const timeoutMs = resolveOperationTimeoutMs(handler, context, 'blind_pure_protocol');
  let pureResult = null;

  try {
    pureResult = await handler._callNavigatorOverride(
      '_extractViaPureProtocol',
      (resolvedTarget, resolvedOptions) => handler._extractViaPureProtocol(resolvedTarget, resolvedOptions),
      { url: baseUrl, baseUrl },
      {
        ...options,
        timeoutMs,
        leagueDeadlineAt: context.leagueDeadlineAt,
        allowBrowserHtmlFallback: false,
        allowRuntimeStateProbe: false
      }
    );
  } catch (error) {
    logBlindMiss(handler, context, 'pure_protocol_html_probe', { error: error.message });
    return null;
  }

  if (!resultHasMatches(pureResult)) {
    logBlindMiss(handler, context, 'pure_protocol_html_probe', {
      totalCandidates: pureResult?.matches?.length || 0,
      sourceState: pureResult?.sourceState || 'SOURCE_EMPTY'
    });
    return null;
  }

  cacheBlindPureProtocolContext(handler, context, pureResult);
  logArchiveCompletion(handler, pureResult, context, {
    defaultSourceState: 'SOURCE_EMPTY',
    meta: { pureProtocol: true, blind: true }
  });
  logBlindHit(handler, context, 'pure_protocol_html_probe', pureResult, {
    tournamentId: pureResult?.pureProtocolMeta?.tournamentId || pureResult?.pureProtocolMeta?.outrightId || null
  });
  return pureResult;
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

  async _tryBlindProtocolArchiveExtract(baseUrl, options = {}) {
    if (options.disableBlindProtocol === true || options.forceDomOnly === true) {
      return null;
    }

    const context = buildArchiveFlowContext(this, baseUrl, options);
    if (!context.preferCurrentSeasonSource) {
      return null;
    }

    const seedArchiveEndpoints = resolveSeedArchiveEndpoints(this, context, options);
    let blindArchiveCandidates = resolveBlindArchiveCandidates(this, context, seedArchiveEndpoints);
    if (blindArchiveCandidates.length === 0) {
      const htmlArchiveCandidate = await resolveBlindHtmlArchiveCandidate(this, baseUrl, context, options);
      blindArchiveCandidates = resolveBlindArchiveCandidates(
        this,
        context,
        htmlArchiveCandidate ? [htmlArchiveCandidate] : []
      );
    }

    for (const archiveApiUrl of blindArchiveCandidates) {
      try {
        const blindArchiveResult = await tryBlindArchiveEndpoint(
          this,
          baseUrl,
          context,
          archiveApiUrl,
          'cached_archive_endpoint'
        );
        if (blindArchiveResult) {
          return blindArchiveResult;
        }
      } catch (error) {
        if (error?.code === 'LEAGUE_TIMEOUT') {
          throw error;
        }

        logBlindMiss(this, context, 'cached_archive_endpoint', {
          archiveApiUrl,
          error: error.message
        });
      }
    }

    const currentTournamentUrl = resolveBlindCurrentTournamentUrl(
      this,
      context,
      blindArchiveCandidates[0] || ''
    );
    if (currentTournamentUrl) {
      try {
        const blindTournamentResult = await tryBlindCurrentTournament(
          this,
          context,
          currentTournamentUrl,
          'cached_tournament_context'
        );
        if (blindTournamentResult) {
          return blindTournamentResult;
        }
      } catch (error) {
        if (error?.code === 'LEAGUE_TIMEOUT') {
          throw error;
        }

        logBlindMiss(this, context, 'cached_tournament_context', {
          currentTournamentUrl,
          error: error.message
        });
      }
    }

    return tryBlindPureProtocol(this, baseUrl, context, options);
  },

  async protocolArchiveExtract(baseUrl, options = {}) {
    const context = buildArchiveFlowContext(this, baseUrl, options);
    const seedArchiveEndpoints = resolveSeedArchiveEndpoints(this, context, options);
    const reuseCurrentPage = options.reuseCurrentPage === true && isReusableResultsPage(this, baseUrl);
    const skipContextReset = options.skipContextReset === true && (seedArchiveEndpoints.length > 0 || reuseCurrentPage);

    if (options.forcePureProtocol === true) {
      return fetchForcedPureProtocol(this, baseUrl, options, context);
    }

    if (context.preferCurrentSeasonSource) {
      const blindResult = await this._tryBlindProtocolArchiveExtract(baseUrl, {
        ...options,
        maxPages: context.maxPages,
        timeoutMs: context.timeoutMs,
        readySelector: context.readySelector,
        circuitBreakerKey: context.circuitBreakerKey,
        disableTournamentFallback: context.disableTournamentFallback,
        leagueDeadlineAt: context.leagueDeadlineAt,
        seedArchiveEndpoints
      });
      if (blindResult) {
        return blindResult;
      }
    }

    if (!skipContextReset) {
      if (typeof this.navigator.resetContextPerBatch === 'function') {
        await this.navigator.resetContextPerBatch({ reason: 'protocol_archive_extract' });
      } else {
        await this.navigator.ensureBrowserHealthy();
      }
    } else {
      await this.navigator.ensureBrowserHealthy();
      this.logger.info('protocol_archive_context_reused', {
        baseUrl,
        breakerKey: context.circuitBreakerKey,
        seedArchiveEndpointCount: seedArchiveEndpoints.length,
        reuseCurrentPage
      });
    }

    if (context.preferCurrentSeasonSource) {
      return fetchPreferredCurrentSeason(this, baseUrl, context);
    }

    this.logger.info('protocol_archive_start', {
      baseUrl,
      maxPages: context.maxPages,
      breakerKey: context.circuitBreakerKey
    });

    if (seedArchiveEndpoints.length > 0) {
      return fetchArchiveApiResult(this, baseUrl, context, chooseArchiveEndpoint(this, seedArchiveEndpoints));
    }

    if (!reuseCurrentPage) {
      await this.navigator.navigate(baseUrl, {
        waitUntil: 'domcontentloaded',
        timeout: resolveOperationTimeoutMs(this, context, 'archive_root_navigate'),
        ...context.navigateOptions
      });
    }

    const archiveEndpoints = await waitForArchiveEndpoints(this, context);
    if (archiveEndpoints.length === 0) {
      this.logger.warn('protocol_archive_no_api');
      return fallbackToLeagueTournament(this, baseUrl, null, context, 'archive_api_missing');
    }

    return fetchArchiveApiResult(this, baseUrl, context, chooseArchiveEndpoint(this, archiveEndpoints));
  }
};

module.exports = { reconProtocolArchiveFlow };
