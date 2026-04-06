'use strict';

function decodeHtmlEntities(text = '') {
  return String(text || '')
    .replace(/&quot;/g, '"')
    .replace(/&#34;/g, '"')
    .replace(/&#39;/g, '\'')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>');
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
      && result.pageStats.some((stat) => typeof stat?.error === 'string'
        && stat.error.startsWith('decrypt_failed:'));
  },

  async _getCurrentTournamentEndpoint() {
    const endpoints = Array.from(this.navigator.apiEndpoints)
      .filter((url) => /ajax-sport-country-tournament_\/\d+\/[^/]+\/X/i.test(url))
      .filter((url) => !/archive_/i.test(url));

    if (endpoints.length > 0) {
      return endpoints.sort((a, b) => this._scoreTournamentUrl(b) - this._scoreTournamentUrl(a))[0];
    }

    if (this.page && typeof this.page.content === 'function') {
      try {
        const extracted = this._extractCurrentTournamentEndpointFromHtml(await this.page.content());
        if (extracted) {
          this.navigator.apiEndpoints.add(extracted);
          return extracted;
        }
      } catch (_error) {
        // HTML 提取失败时退回网络拦截结果
      }
    }

    return null;
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
      getInterceptedData: () => this.navigator.getInterceptedData(),
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
          if (!entry?.name || typeof entry.name !== 'string') {
            continue;
          }
          if (/ajax-sport-country-tournament-archive_/i.test(entry.name)) {
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
        this.logger.debug('protocol_archive_resource_probe_failed', {
          error: error.message
        });
      }
      return [];
    }
  },

  async protocolArchiveExtract(baseUrl, options = {}) {
    if (options.forcePureProtocol === true) {
      const maxPages = options.maxPages ?? this.navigator.archiveMaxPages;
      const timeoutMs = options.timeoutMs ?? this.navigator.archiveTimeoutMs;
      const preferCurrentSeasonSource = options.preferCurrentSeasonSource === true;
      const circuitBreakerKey = this.navigator._resolveCircuitBreakerKey(baseUrl, options);
      let pureResult = null;
      let pureError = null;

      try {
        pureResult = await this._callNavigatorOverride(
          '_extractViaPureProtocol',
          (resolvedTarget, resolvedOptions) => this._extractViaPureProtocol(resolvedTarget, resolvedOptions),
          { url: baseUrl, baseUrl },
          options
        );
      } catch (error) {
        pureError = error;
      }

      if (preferCurrentSeasonSource && (!pureResult || pureResult.matches?.length === 0)) {
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
          null,
          maxPages,
          timeoutMs,
          pureError ? 'pure_protocol_failed' : 'pure_protocol_source_empty',
          { circuitBreakerKey }
        );

        if (Array.isArray(fallbackResult?.matches) && fallbackResult.matches.length > 0) {
          this.logger.info('protocol_archive_complete', {
            pagesScanned: fallbackResult.pageStats?.length || 0,
            totalCandidates: fallbackResult.matches?.length || 0,
            sourceState: fallbackResult.sourceState || 'CURRENT_TOURNAMENT_FALLBACK',
            breakerKey: circuitBreakerKey,
            pureProtocol: true
          });

          return fallbackResult;
        }
      }

      if (pureError) {
        throw pureError;
      }

      this.logger.info('protocol_archive_complete', {
        pagesScanned: pureResult.pageStats?.length || 0,
        totalCandidates: pureResult.matches?.length || 0,
        sourceState: pureResult.sourceState || 'SOURCE_EMPTY',
        breakerKey: circuitBreakerKey,
        pureProtocol: true
      });

      return pureResult;
    }

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

    let archiveEndpoints = Array.from(this.navigator.apiEndpoints)
      .filter((url) => /ajax-sport-country-tournament-archive_/i.test(url));

    if (archiveEndpoints.length === 0) {
      const resourceEndpoints = await this._discoverArchiveEndpointsFromPageResources();
      archiveEndpoints = resourceEndpoints.filter((url) => /ajax-sport-country-tournament-archive_/i.test(url));

      if (archiveEndpoints.length > 0) {
        this.logger.info('protocol_archive_resource_probe_hit', {
          endpointCount: archiveEndpoints.length,
          breakerKey: circuitBreakerKey
        });
      }
    }

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
