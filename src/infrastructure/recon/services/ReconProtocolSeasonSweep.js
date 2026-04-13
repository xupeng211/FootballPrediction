'use strict';

const { waitForDelay } = require('../../shared/helpers/browserUtils');
const { getReconConfigSection } = require('./ReconServiceConfig');

const STATE_PROBER_CONFIG = getReconConfigSection(['recon_runtime', 'state_prober'], {});

function buildSeasonSweepContext(handler, baseUrl, options = {}) {
  const timeoutMs = options.timeoutMs ?? handler.navigator.archiveTimeoutMs;
  const maxPages = options.maxPages ?? handler.navigator.archiveMaxPages;
  const readySelector = typeof options.readySelector === 'string' ? options.readySelector.trim() : '';
  const circuitBreakerKey = handler.navigator._resolveCircuitBreakerKey(baseUrl, options);

  return {
    baseUrl,
    resultsUrl: handler.navigator.domScraper.normalizeResultsUrl(baseUrl),
    timeoutMs,
    maxPages,
    readySelector,
    circuitBreakerKey,
    preferCurrentSeasonSource: options.preferCurrentSeasonSource === true,
    forceDomOnly: options.forceDomOnly === true,
    minCandidatesForStateProbe: Math.max(
      0,
      Number(options.minCandidatesForStateProbe ?? STATE_PROBER_CONFIG.minimum_current_results_candidates ?? 0) || 0
    ),
    navigateOptions: readySelector
      ? { contentReadySelector: readySelector, circuitBreakerKey }
      : { circuitBreakerKey }
  };
}

function createSeasonSweepAccumulator() {
  const seen = new Set();
  const matches = [];
  const pageStats = [];

  return {
    matches,
    pageStats,
    append(pageMatches, page, url, source) {
      let newRows = 0;
      for (const match of Array.isArray(pageMatches) ? pageMatches : []) {
        const key = match?.hash || match?.url;
        if (!key || seen.has(key)) {
          continue;
        }
        seen.add(key);
        matches.push(match);
        newRows += 1;
      }

      pageStats.push({
        page,
        url,
        rows: Array.isArray(pageMatches) ? pageMatches.length : 0,
        newRows,
        total: matches.length,
        source
      });
    },
    mergePageStats(extraPageStats = [], fallbackSource = 'archive_api') {
      for (const [index, stat] of extraPageStats.entries()) {
        pageStats.push({
          ...stat,
          page: stat?.page || (pageStats.length + index + 1),
          source: stat?.source || fallbackSource
        });
      }
    }
  };
}

function shouldProbeCurrentSeason(context, totalMatches) {
  return context.preferCurrentSeasonSource
    && !context.forceDomOnly
    && (
      totalMatches === 0
      || (context.minCandidatesForStateProbe > 0 && totalMatches < context.minCandidatesForStateProbe)
    );
}

async function collectSeasonPages(handler, discovery, context, accumulator, options = {}) {
  accumulator.append(discovery.initialMatches, 1, discovery.pageUrls[0] || context.resultsUrl, discovery.initialSource);

  for (let index = 1; index < discovery.pageUrls.length; index++) {
    const pageUrl = discovery.pageUrls[index];
    await handler.navigator.navigate(pageUrl, {
      waitUntil: 'domcontentloaded',
      timeout: context.timeoutMs,
      ...context.navigateOptions
    });
    await waitForDelay(handler.page, handler.navigator.pageRevisitWaitMs);

    let pageMatches = handler.navigator.getInterceptedData();
    let source = 'page_intercept';
    if (pageMatches.length === 0) {
      pageMatches = await handler.navigator.domScraper.extractCurrentSeasonResultRows(pageUrl, options);
      source = 'page_dom';
    }

    accumulator.append(pageMatches, index + 1, pageUrl, source);
  }
}

async function mergeArchiveMatches(handler, context, accumulator) {
  const archiveResult = await handler._callNavigatorOverride(
    'protocolArchiveExtract',
    (resolvedBaseUrl, resolvedOptions) => handler.protocolArchiveExtract(resolvedBaseUrl, resolvedOptions),
    context.resultsUrl,
    {
      maxPages: context.maxPages,
      timeoutMs: context.timeoutMs,
      preferCurrentSeasonSource: false,
      readySelector: context.readySelector,
      circuitBreakerKey: context.circuitBreakerKey
    }
  );

  const beforeCount = accumulator.matches.length;
  accumulator.append(archiveResult?.matches || [], accumulator.pageStats.length + 1, context.resultsUrl, 'archive_api');
  if (Array.isArray(archiveResult?.pageStats) && archiveResult.pageStats.length > 0) {
    accumulator.pageStats.pop();
    accumulator.mergePageStats(archiveResult.pageStats, 'archive_api');
  } else if (Array.isArray(archiveResult?.matches) && archiveResult.matches.length > 0) {
    accumulator.pageStats[accumulator.pageStats.length - 1].newRows = accumulator.matches.length - beforeCount;
  }
}

async function mergeCurrentSeasonProbe(handler, context, accumulator) {
  const currentSeasonResult = await handler.navigator.stateProber.probeCurrentSeasonFromPageState(
    context.baseUrl,
    {
      maxPages: context.maxPages,
      timeoutMs: context.timeoutMs,
      maxScrollRounds: handler.navigator.scrollAttempts,
      readySelector: context.readySelector,
      circuitBreakerKey: context.circuitBreakerKey
    },
    handler._buildStateProbeHooks(context.navigateOptions, context.circuitBreakerKey)
  );

  const beforeCount = accumulator.matches.length;
  accumulator.append(
    currentSeasonResult?.matches || [],
    accumulator.pageStats.length + 1,
    handler.navigator.stateProber.deriveCurrentResultsUrl(context.baseUrl) || context.baseUrl,
    currentSeasonResult?.sourceState || 'current_results_archive'
  );
  if (Array.isArray(currentSeasonResult?.pageStats) && currentSeasonResult.pageStats.length > 0) {
    accumulator.pageStats.pop();
    accumulator.mergePageStats(
      currentSeasonResult.pageStats,
      currentSeasonResult?.sourceState || 'current_results_archive'
    );
  } else {
    accumulator.pageStats[accumulator.pageStats.length - 1].newRows = accumulator.matches.length - beforeCount;
  }

  if (accumulator.matches.length > 0 && context.minCandidatesForStateProbe > 0) {
    handler.logger.info('season_sweep_low_yield_recovered', {
      baseUrl: context.resultsUrl,
      totalCandidates: accumulator.matches.length,
      minCandidatesForStateProbe: context.minCandidatesForStateProbe,
      breakerKey: context.circuitBreakerKey
    });
  }
}

const reconProtocolSeasonSweep = {
  async fetchFullSeasonArchive(baseUrl, options = {}) {
    if (typeof this.navigator.resetContextPerBatch === 'function') {
      await this.navigator.resetContextPerBatch({ reason: 'fetch_full_season_archive' });
    } else {
      await this.navigator.ensureBrowserHealthy();
    }

    const context = buildSeasonSweepContext(this, baseUrl, options);
    this.logger.info('season_sweep_start', {
      baseUrl: context.resultsUrl,
      maxPages: context.maxPages,
      preferCurrentSeasonSource: context.preferCurrentSeasonSource,
      forceDomOnly: context.forceDomOnly,
      breakerKey: context.circuitBreakerKey
    });

    const discovery = await this.navigator.domScraper.discoverSeasonResultPages(
      context.resultsUrl,
      { timeoutMs: context.timeoutMs, maxPages: context.maxPages, includeSeasonNavigation: false },
      {
        navigate: (url, dynamicNavigateOptions) => this.navigator.navigate(url, {
          ...dynamicNavigateOptions,
          ...context.navigateOptions
        }),
        getInterceptedData: () => this.navigator.getInterceptedData(),
        waitForTimeout: async (ms) => waitForDelay(this.page, ms)
      }
    );

    const accumulator = createSeasonSweepAccumulator();
    await collectSeasonPages(this, discovery, context, accumulator, options);

    if (!context.forceDomOnly) {
      await mergeArchiveMatches(this, context, accumulator);
    }

    if (shouldProbeCurrentSeason(context, accumulator.matches.length)) {
      await mergeCurrentSeasonProbe(this, context, accumulator);
    }

    this.logger.info('season_sweep_complete', {
      pageCount: discovery.pageUrls.length,
      totalCandidates: accumulator.matches.length,
      breakerKey: context.circuitBreakerKey
    });

    return {
      matches: accumulator.matches,
      pagesScanned: accumulator.pageStats.length,
      totalCandidates: accumulator.matches.length,
      pageStats: accumulator.pageStats,
      sourceState: accumulator.matches.length > 0 ? 'FULL_SEASON_SWEEP' : 'SOURCE_EMPTY',
      pageUrls: discovery.pageUrls
    };
  }
};

module.exports = { reconProtocolSeasonSweep };
