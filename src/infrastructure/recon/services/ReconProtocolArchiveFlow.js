'use strict';

const reconProtocolArchiveFlow = {
  _resultHasDecryptFailure(result) {
    return Array.isArray(result?.pageStats)
      && result.pageStats.some((stat) => typeof stat?.error === 'string'
        && stat.error.startsWith('decrypt_failed:'));
  },

  _getCurrentTournamentEndpoint() {
    const endpoints = Array.from(this.navigator.apiEndpoints)
      .filter((url) => /ajax-sport-country-tournament_\/\d+\/[^/]+\/X/i.test(url))
      .filter((url) => !/archive_/i.test(url));

    if (endpoints.length === 0) {
      return null;
    }

    return endpoints.sort((a, b) => this._scoreTournamentUrl(b) - this._scoreTournamentUrl(a))[0];
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
      navigate: (url, options) => this.navigator.navigate(url, {
        ...options,
        ...defaultNavigateOptions
      }),
      waitForTimeout: async (ms) => {
        if (this.page && typeof this.page.waitForTimeout === 'function') {
          await this.page.waitForTimeout(ms);
        }
      },
      getApiEndpoints: () => Array.from(this.navigator.apiEndpoints),
      scoreArchiveUrl: (url) => this._callNavigatorOverride(
        '_scoreArchiveUrl',
        (resolvedUrl) => this._scoreArchiveUrl(resolvedUrl),
        url
      ),
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
      getCurrentTournamentEndpoint: () => this._callNavigatorOverride(
        '_getCurrentTournamentEndpoint',
        () => this._getCurrentTournamentEndpoint()
      ),
      buildCurrentTournamentUrlFromArchive: (url) => this._callNavigatorOverride(
        '_buildTournamentUrlFromArchive',
        (resolvedUrl) => this._buildTournamentUrlFromArchive(resolvedUrl),
        url
      ),
      fetchCurrentTournament: (url, maxPages, timeoutMs) => (
        this._callNavigatorOverride(
          '_fetchCurrentTournament',
          (resolvedUrl, resolvedMaxPages, resolvedTimeoutMs, resolvedOptions) => (
            this._fetchCurrentTournament(resolvedUrl, resolvedMaxPages, resolvedTimeoutMs, resolvedOptions)
          ),
          url,
          maxPages,
          timeoutMs,
          { circuitBreakerKey }
        )
      )
    };
  },

  async protocolArchiveExtract(baseUrl, options = {}) {
    await this.navigator.ensureBrowserHealthy();

    const maxPages = options.maxPages ?? this.navigator.archiveMaxPages;
    const timeoutMs = options.timeoutMs ?? this.navigator.archiveTimeoutMs;
    const preferCurrentSeasonSource = options.preferCurrentSeasonSource === true;
    const readySelector = typeof options.readySelector === 'string' ? options.readySelector.trim() : '';
    const circuitBreakerKey = this.navigator._resolveCircuitBreakerKey(baseUrl, options);
    const navigateOptions = readySelector
      ? { contentReadySelector: readySelector, circuitBreakerKey }
      : { circuitBreakerKey };

    if (preferCurrentSeasonSource) {
      this.logger.info('protocol_current_season_start', { baseUrl, maxPages, breakerKey: circuitBreakerKey });
      const currentResult = await this.navigator.stateProber.probeCurrentSeasonFromPageState(
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
      this.logger.info('protocol_archive_complete', {
        pagesScanned: currentResult.pageStats?.length || 0,
        totalCandidates: currentResult.matches?.length || 0,
        sourceState: currentResult.sourceState || 'SOURCE_EMPTY',
        breakerKey: circuitBreakerKey
      });
      return currentResult;
    }

    this.logger.info('protocol_archive_start', { baseUrl, maxPages, breakerKey: circuitBreakerKey });
    await this.navigator.navigate(baseUrl, { waitUntil: 'domcontentloaded', ...navigateOptions });
    await this.page.waitForTimeout(this.navigator.postApiDiscoveryWaitMs);

    const archiveEndpoints = Array.from(this.navigator.apiEndpoints)
      .filter((url) => /ajax-sport-country-tournament-archive_/i.test(url));

    if (archiveEndpoints.length === 0) {
      this.logger.warn('protocol_archive_no_api');
      return this._callNavigatorOverride(
        '_fallbackToLeagueTournament',
        (resolvedBaseUrl, resolvedArchiveUrl, resolvedMaxPages, resolvedTimeoutMs, resolvedReason, resolvedOptions) => (
          this._fallbackToLeagueTournament(
            resolvedBaseUrl,
            resolvedArchiveUrl,
            resolvedMaxPages,
            resolvedTimeoutMs,
            resolvedReason,
            resolvedOptions
          )
        ),
        baseUrl,
        null,
        maxPages,
        timeoutMs,
        'archive_api_missing',
        { circuitBreakerKey }
      );
    }

    const archiveApiUrl = archiveEndpoints.sort((a, b) => this._scoreArchiveUrl(b) - this._scoreArchiveUrl(a))[0];
    const archiveContext = archiveApiUrl.includes('/1//')
      ? await this._resolveLeagueTournamentContext(baseUrl, timeoutMs, archiveApiUrl, {
        circuitBreakerKey
      })
      : { repairedArchiveUrl: archiveApiUrl, currentTournamentUrl: null, leagueUrl: null, tournamentId: null };

    const result = await this._callNavigatorOverride(
      '_fetchAndDecrypt',
      (resolvedUrl, resolvedMaxPages, resolvedTimeoutMs, resolvedOptions) => (
        this._fetchAndDecrypt(resolvedUrl, resolvedMaxPages, resolvedTimeoutMs, resolvedOptions)
      ),
      archiveContext.repairedArchiveUrl || archiveApiUrl,
      maxPages,
      timeoutMs,
      {
        warmUrl: this.navigator.stateProber.deriveCurrentResultsUrl(baseUrl) || baseUrl,
        circuitBreakerKey
      }
    );

    if (result.matches.length === 0 && this._resultHasDecryptFailure(result)) {
      const fallbackResult = await this._callNavigatorOverride(
        '_fallbackToLeagueTournament',
        (resolvedBaseUrl, resolvedArchiveUrl, resolvedMaxPages, resolvedTimeoutMs, resolvedReason, resolvedOptions) => (
          this._fallbackToLeagueTournament(
            resolvedBaseUrl,
            resolvedArchiveUrl,
            resolvedMaxPages,
            resolvedTimeoutMs,
            resolvedReason,
            resolvedOptions
          )
        ),
        baseUrl,
        archiveContext.repairedArchiveUrl || archiveApiUrl,
        maxPages,
        timeoutMs,
        'archive_decrypt_failed',
        { circuitBreakerKey }
      );

      if (fallbackResult.matches.length > 0) {
        this.logger.info('protocol_archive_complete', {
          pagesScanned: fallbackResult.pageStats?.length || 0,
          totalCandidates: fallbackResult.matches?.length || 0,
          sourceState: fallbackResult.sourceState || 'CURRENT_TOURNAMENT_FALLBACK',
          breakerKey: circuitBreakerKey
        });
        return fallbackResult;
      }
    }

    this.logger.info('protocol_archive_complete', {
      pagesScanned: result.pageStats.length,
      totalCandidates: result.matches.length,
      breakerKey: circuitBreakerKey
    });

    return result;
  }
};

module.exports = { reconProtocolArchiveFlow };
