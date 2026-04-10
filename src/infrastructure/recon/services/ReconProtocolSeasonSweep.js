'use strict';

const { getReconConfigSection } = require('./ReconServiceConfig');

const STATE_PROBER_CONFIG = getReconConfigSection(['recon_runtime', 'state_prober'], {});

const reconProtocolSeasonSweep = {
  async fetchFullSeasonArchive(baseUrl, options = {}) {
    if (typeof this.navigator.resetContextPerBatch === 'function') {
      await this.navigator.resetContextPerBatch({
        reason: 'fetch_full_season_archive'
      });
    } else {
      await this.navigator.ensureBrowserHealthy();
    }

    const timeoutMs = options.timeoutMs ?? this.navigator.archiveTimeoutMs;
    const maxPages = options.maxPages ?? this.navigator.archiveMaxPages;
    const preferCurrentSeasonSource = options.preferCurrentSeasonSource === true;
    const forceDomOnly = options.forceDomOnly === true;
    const readySelector = typeof options.readySelector === 'string' ? options.readySelector.trim() : '';
    const minCandidatesForStateProbe = Math.max(
      0,
      Number(
        options.minCandidatesForStateProbe
        ?? STATE_PROBER_CONFIG.minimum_current_results_candidates
        ?? 0
      ) || 0
    );
    const circuitBreakerKey = this.navigator._resolveCircuitBreakerKey(baseUrl, options);
    const navigateOptions = readySelector
      ? { contentReadySelector: readySelector, circuitBreakerKey }
      : { circuitBreakerKey };
    const resultsUrl = this.navigator.domScraper.normalizeResultsUrl(baseUrl);

    this.logger.info('season_sweep_start', {
      baseUrl: resultsUrl,
      maxPages,
      preferCurrentSeasonSource,
      forceDomOnly,
      breakerKey: circuitBreakerKey
    });

    const discovery = await this.navigator.domScraper.discoverSeasonResultPages(
      resultsUrl,
      { timeoutMs, maxPages, includeSeasonNavigation: false },
      {
        navigate: (url, dynamicNavigateOptions) => this.navigator.navigate(url, {
          ...dynamicNavigateOptions,
          ...navigateOptions
        }),
        getInterceptedData: () => this.navigator.getInterceptedData(),
        waitForTimeout: async (ms) => {
          if (this.page && typeof this.page.waitForTimeout === 'function') {
            await this.page.waitForTimeout(ms);
          }
        }
      }
    );

    const seen = new Set();
    const matches = [];
    const pageStats = [];
    const appendMatches = (pageMatches, pageIndex, pageUrl, source) => {
      let newRows = 0;
      for (const match of Array.isArray(pageMatches) ? pageMatches : []) {
        const key = match?.hash || match?.url;
        if (!key || seen.has(key)) {
          continue;
        }
        seen.add(key);
        matches.push(match);
        newRows++;
      }
      pageStats.push({
        page: pageIndex,
        url: pageUrl,
        rows: Array.isArray(pageMatches) ? pageMatches.length : 0,
        newRows,
        total: matches.length,
        source
      });
    };

    appendMatches(discovery.initialMatches, 1, discovery.pageUrls[0] || resultsUrl, discovery.initialSource);

    for (let index = 1; index < discovery.pageUrls.length; index++) {
      const pageUrl = discovery.pageUrls[index];
      await this.navigator.navigate(pageUrl, { waitUntil: 'domcontentloaded', timeout: timeoutMs, ...navigateOptions });
      await this.page.waitForTimeout(this.navigator.pageRevisitWaitMs);

      let pageMatches = this.navigator.getInterceptedData();
      let source = 'page_intercept';
      if (pageMatches.length === 0) {
        pageMatches = await this.navigator.domScraper.extractCurrentSeasonResultRows(pageUrl, options);
        source = 'page_dom';
      }

      appendMatches(pageMatches, index + 1, pageUrl, source);
    }

    if (!forceDomOnly) {
      const archiveResult = await this._callNavigatorOverride(
        'protocolArchiveExtract',
        (resolvedBaseUrl, resolvedOptions) => this.protocolArchiveExtract(resolvedBaseUrl, resolvedOptions),
        resultsUrl,
        {
          maxPages,
          timeoutMs,
          preferCurrentSeasonSource: false,
          readySelector,
          circuitBreakerKey
        }
      );

      let archiveNewRows = 0;
      for (const match of Array.isArray(archiveResult?.matches) ? archiveResult.matches : []) {
        const key = match?.hash || match?.url;
        if (!key || seen.has(key)) {
          continue;
        }

        seen.add(key);
        matches.push(match);
        archiveNewRows++;
      }

      if (Array.isArray(archiveResult?.pageStats) && archiveResult.pageStats.length > 0) {
        for (const [index, stat] of archiveResult.pageStats.entries()) {
          pageStats.push({
            ...stat,
            page: stat?.page || (discovery.pageUrls.length + index + 1),
            source: stat?.source || 'archive_api'
          });
        }
      } else if (Array.isArray(archiveResult?.matches) && archiveResult.matches.length > 0) {
        pageStats.push({
          page: discovery.pageUrls.length + 1,
          url: resultsUrl,
          rows: archiveResult.matches.length,
          newRows: archiveNewRows,
          total: matches.length,
          source: 'archive_api'
        });
      }
    }

    const shouldProbeCurrentSeason = preferCurrentSeasonSource
      && !forceDomOnly
      && (
        matches.length === 0
        || (minCandidatesForStateProbe > 0 && matches.length < minCandidatesForStateProbe)
      );

    if (shouldProbeCurrentSeason) {
      const currentSeasonResult = await this.navigator.stateProber.probeCurrentSeasonFromPageState(
        baseUrl,
        {
          maxPages,
          timeoutMs,
          maxScrollRounds: this.navigator.scrollAttempts,
          readySelector,
          circuitBreakerKey
        },
        this._buildStateProbeHooks(navigateOptions, circuitBreakerKey)
      );
      let currentSeasonNewRows = 0;

      for (const match of Array.isArray(currentSeasonResult?.matches) ? currentSeasonResult.matches : []) {
        const key = match?.hash || match?.url;
        if (!key || seen.has(key)) {
          continue;
        }
        seen.add(key);
        matches.push(match);
        currentSeasonNewRows++;
      }

      if (Array.isArray(currentSeasonResult?.pageStats) && currentSeasonResult.pageStats.length > 0) {
        for (const [index, stat] of currentSeasonResult.pageStats.entries()) {
          pageStats.push({
            ...stat,
            page: stat?.page || (pageStats.length + index + 1),
            source: stat?.source || currentSeasonResult?.sourceState || 'current_results_archive'
          });
        }
      } else if (Array.isArray(currentSeasonResult?.matches) && currentSeasonResult.matches.length > 0) {
        pageStats.push({
          page: pageStats.length + 1,
          url: this.navigator.stateProber.deriveCurrentResultsUrl(baseUrl) || baseUrl,
          rows: currentSeasonResult.matches.length,
          newRows: currentSeasonNewRows,
          total: matches.length,
          source: currentSeasonResult?.sourceState || 'current_results_archive'
        });
      }

      if (matches.length > 0 && minCandidatesForStateProbe > 0) {
        this.logger.info('season_sweep_low_yield_recovered', {
          baseUrl: resultsUrl,
          totalCandidates: matches.length,
          minCandidatesForStateProbe,
          breakerKey: circuitBreakerKey
        });
      }
    }

    this.logger.info('season_sweep_complete', {
      pageCount: discovery.pageUrls.length,
      totalCandidates: matches.length,
      breakerKey: circuitBreakerKey
    });

    return {
      matches,
      pagesScanned: pageStats.length,
      totalCandidates: matches.length,
      pageStats,
      sourceState: matches.length > 0 ? 'FULL_SEASON_SWEEP' : 'SOURCE_EMPTY',
      pageUrls: discovery.pageUrls
    };
  }
};

module.exports = { reconProtocolSeasonSweep };
