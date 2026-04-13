'use strict';

function isMatrixModePruningEnabled(target = {}) {
  return target?.matrixModePruning === true;
}

function resolveMatrixShortCircuitRatio(target = {}) {
  const rawRatio = Number(target?.matrixModeShortCircuitRatio ?? 0.5);
  if (!Number.isFinite(rawRatio)) {
    return 0.5;
  }

  return Math.min(1, Math.max(0, rawRatio));
}

function resolveSampleLinkedThreshold(sampleTarget, target = {}) {
  if (!Number.isInteger(sampleTarget) || sampleTarget <= 0) {
    return 0;
  }

  if (!isMatrixModePruningEnabled(target)) {
    return sampleTarget;
  }

  return Math.max(1, Math.ceil(sampleTarget * resolveMatrixShortCircuitRatio(target)));
}

function getCandidateCount(routeSource = null) {
  return Array.isArray(routeSource?.candidates) ? routeSource.candidates.length : 0;
}

const reconSourceProber = {
  _dedupeCandidatesByIdentity(candidates = []) {
    const deduped = [];
    const seen = new Set();

    for (const candidate of Array.isArray(candidates) ? candidates : []) {
      const key = String(candidate?.hash || candidate?.url || '').trim();
      if (!key || seen.has(key)) {
        continue;
      }

      seen.add(key);
      deduped.push(candidate);
    }

    return deduped;
  },

  _canRunParallelRouteProbes() {
    if (typeof this.navigatorFactory !== 'function') {
      return false;
    }

    const availableProxyCount = this._resolveAvailableProxyCount();
    return availableProxyCount >= 2;
  },

  _combineCandidateRouteSources(routeSources = [], target, pendingMatches, confidenceThreshold) {
    const combinedRouteState = this._buildCandidateRouteState(
      routeSources,
      pendingMatches,
      confidenceThreshold
    );
    const { successfulRoutes, combinedCandidates, combinedSeasonMirror, combinedSampleLinked } = combinedRouteState;
    if (successfulRoutes.length === 0) {
      return this._buildEmptyRouteSource('results', target, 'SOURCE_EMPTY');
    }
    const combinedSourceUrls = [...new Set(
      successfulRoutes
        .map((route) => String(route?.source?.url || '').trim())
        .filter(Boolean)
    )];
    const combinedSeasonLabels = [...new Set(
      successfulRoutes
        .map((route) => String(route?.source?.season || '').trim())
        .filter(Boolean)
    )];
    const sourceState = combinedCandidates.length > 0
      ? 'MULTI_ROUTE_SWEEP'
      : successfulRoutes
        .map((route) => String(route?.extractResult?.sourceState || '').trim())
        .find(Boolean) || 'SOURCE_EMPTY';

    this.logger.info('recon_candidate_routes_combined', {
      league: target?.league?.name || null,
      season: target?.dbSeason || null,
      routeKinds: successfulRoutes.map((route) => route.routeKind),
      sourceUrls: combinedSourceUrls,
      candidateCount: combinedCandidates.length,
      sampleLinked: combinedSampleLinked
    });

    return {
      routeKind: 'combined',
      source: {
        season: combinedSeasonLabels.join(',') || target?.dbSeason || null,
        url: combinedSourceUrls.join(' | ') || target?.resultsUrl || ''
      },
      sources: successfulRoutes.map((route) => ({
        ...route.source,
        routeKind: route.routeKind,
        candidateCount: Array.isArray(route.candidates) ? route.candidates.length : 0
      })),
      extractResult: {
        matches: combinedCandidates,
        pagesScanned: successfulRoutes.reduce((sum, route) => sum + Number(route?.extractResult?.pagesScanned || 0), 0),
        totalCandidates: combinedCandidates.length,
        sourceState
      },
      candidates: combinedCandidates,
      seasonMirror: combinedSeasonMirror,
      sampleLinked: combinedSampleLinked,
      routeKinds: successfulRoutes.map((route) => route.routeKind)
    };
  },

  _buildCandidateRouteState(routeSources = [], pendingMatches, confidenceThreshold) {
    const successfulRoutes = (Array.isArray(routeSources) ? routeSources : [])
      .filter((route) => route && typeof route === 'object');
    const combinedCandidates = this._dedupeCandidatesByIdentity(
      successfulRoutes.flatMap((route) => Array.isArray(route.candidates) ? route.candidates : [])
    );
    const combinedSeasonMirror = this._buildSeasonMirror(combinedCandidates);
    const combinedSampleLinked = this._scoreCandidatePoolSample(
      pendingMatches,
      combinedCandidates,
      confidenceThreshold,
      combinedSeasonMirror
    );

    return {
      successfulRoutes,
      combinedCandidates,
      combinedSeasonMirror,
      combinedSampleLinked
    };
  },

  // eslint-disable-next-line complexity
  async _probeCandidateRoutes(target, pendingMatches, confidenceThreshold, navigator = null) {
    const sharedNavigator = navigator || this.navigator || null;
    const matrixModePruning = isMatrixModePruningEnabled(target);
    const runInParallel = matrixModePruning ? false : this._canRunParallelRouteProbes();
    const sampleTarget = typeof this._buildRouteProbeSample === 'function'
      ? this._buildRouteProbeSample(pendingMatches).length
      : 0;
    const sampleLinkedThreshold = resolveSampleLinkedThreshold(sampleTarget, target);
    const settled = [];

    if (runInParallel) {
      const parallelResults = await Promise.allSettled([
        this._probeResultsCandidateSource(target, pendingMatches, confidenceThreshold, sharedNavigator),
        this._probeFixturesCandidateSource(target, pendingMatches, confidenceThreshold, sharedNavigator, {
          useDedicatedNavigator: true
        })
      ]);
      settled.push(...parallelResults);
    } else {
      try {
        const resultsRoute = await this._probeResultsCandidateSource(target, pendingMatches, confidenceThreshold, sharedNavigator);
        settled.push({
          status: 'fulfilled',
          value: resultsRoute
        });
      } catch (error) {
        settled.push({
          status: 'rejected',
          reason: error
        });
      }

      const resultsOnlyState = this._buildCandidateRouteState(
        settled
          .filter((item) => item.status === 'fulfilled')
          .map((item) => item.value),
        pendingMatches,
        confidenceThreshold
      );
      const resultsRoute = settled.find((item) => item.status === 'fulfilled')?.value || null;
      const shouldShortCircuitOnEmptyResults = matrixModePruning
        && resultsRoute
        && getCandidateCount(resultsRoute) === 0;

      if (shouldShortCircuitOnEmptyResults || (
        sampleLinkedThreshold > 0
        && resultsOnlyState.combinedSampleLinked >= sampleLinkedThreshold
      )) {
        this.logger.info('recon_candidate_routes_short_circuit', {
          league: target?.league?.name || null,
          season: target?.dbSeason || null,
          sampleSize: sampleTarget,
          sampleLinked: resultsOnlyState.combinedSampleLinked,
          sampleLinkedThreshold,
          matrixModePruning,
          skippedRoutes: ['fixtures', 'search']
        });
        return this._combineCandidateRouteSources(
          settled
            .filter((item) => item.status === 'fulfilled')
            .map((item) => item.value),
          target,
          pendingMatches,
          confidenceThreshold
        );
      } else {
        try {
          settled.push({
            status: 'fulfilled',
            value: await this._probeFixturesCandidateSource(target, pendingMatches, confidenceThreshold, sharedNavigator, {
              useDedicatedNavigator: false
            })
          });
        } catch (error) {
          settled.push({
            status: 'rejected',
            reason: error
          });
        }
      }
    }

    const successfulRoutes = [];
    const routeFailures = [];

    for (const item of settled) {
      if (item.status === 'fulfilled') {
        if (item.value) {
          successfulRoutes.push(item.value);
        }
        continue;
      }

      routeFailures.push(item.reason);
    }

    if (successfulRoutes.length === 0 && routeFailures.length > 0) {
      const primaryError = routeFailures[0] instanceof Error
        ? routeFailures[0]
        : new Error(String(routeFailures[0] || 'recon_route_probe_failed'));
      primaryError.routeFailures = routeFailures.map((failure) => failure?.message || String(failure || ''));
      throw primaryError;
    }

    const preSearchState = this._buildCandidateRouteState(
      successfulRoutes,
      pendingMatches,
      confidenceThreshold
    );
    if (
      sampleLinkedThreshold > 0
      && preSearchState.combinedSampleLinked >= sampleLinkedThreshold
    ) {
      this.logger.info('recon_candidate_routes_short_circuit', {
        league: target?.league?.name || null,
        season: target?.dbSeason || null,
        sampleSize: sampleTarget,
        sampleLinked: preSearchState.combinedSampleLinked,
        sampleLinkedThreshold,
        matrixModePruning,
        skippedRoutes: ['search']
      });
      return this._combineCandidateRouteSources(
        successfulRoutes,
        target,
        pendingMatches,
        confidenceThreshold
      );
    }

    try {
      const searchRoute = await this._probeSearchCandidateSource(target, pendingMatches, confidenceThreshold, sharedNavigator, {
        useDedicatedNavigator: runInParallel
      });
      if (searchRoute) {
        successfulRoutes.push(searchRoute);
      }
    } catch (error) {
      routeFailures.push(error);
    }

    return this._combineCandidateRouteSources(
      successfulRoutes,
      target,
      pendingMatches,
      confidenceThreshold
    );
  },

  async _probeResultsCandidateSource(target, pendingMatches, confidenceThreshold, navigator = null) {
    const timeoutMs = this._resolveRouteProbeTimeoutMs('results', target);
    const matrixModePruning = isMatrixModePruningEnabled(target);
    let selectedSource;
    try {
      selectedSource = await this.taskPlanner.selectCandidateSource(
        target,
        pendingMatches,
        confidenceThreshold,
        {
          navigator: navigator || this.navigator || null,
          timeoutMs,
          disableTournamentFallback: true,
          matrixModePruning,
          matrixModeShortCircuitRatio: target?.matrixModeShortCircuitRatio,
          leagueDeadlineAt: target?.leagueDeadlineAt ?? null
        }
      );
      this._resetRouteFailureStreak(target, 'results');
    } catch (error) {
      if (error?.code === 'LEAGUE_TIMEOUT') {
        throw error;
      }
      const failure = this._recordRouteProbeFailure(target, 'results', error, { timeoutMs });
      if (failure.shouldDegrade) {
        return this._buildDegradedRouteSource(
          'results',
          target,
          failure.sourceState,
          error,
          {
            timeoutMs,
            searchBlocked: failure.searchBlocked
          }
        );
      }
      throw error;
    }

    return {
      ...selectedSource,
      routeKind: 'results'
    };
  },

  async _probeFixturesCandidateSource(target, pendingMatches, confidenceThreshold, navigator = null, options = {}) {
    const fixturesUrl = target?.fixturesUrl
      || this.taskPlanner?.buildFixturesUrl?.(target?.league, target?.season || target?.dbSeason)
      || null;
    if (!fixturesUrl) {
      return null;
    }

    const timeoutMs = this._resolveRouteProbeTimeoutMs('fixtures', target);
    try {
      const routeSource = await this._executeRouteProbeWithNavigator(
        target,
        navigator,
        {
          routeKind: 'fixtures',
          launchBrowser: true,
          useDedicatedNavigator: options.useDedicatedNavigator === true
        },
        async (activeNavigator) => {
          const extractResult = await this._fetchCandidateRouteArchive('fixtures', fixturesUrl, target, pendingMatches, activeNavigator);
          const candidates = this._dedupeCandidatesByIdentity(extractResult?.matches || []);
          const seasonMirror = this._buildSeasonMirror(candidates);

          return {
            routeKind: 'fixtures',
            source: {
              season: target?.dbSeason || null,
              url: fixturesUrl
            },
            extractResult: {
              ...extractResult,
              matches: candidates,
              totalCandidates: candidates.length,
              sourceState: extractResult?.sourceState || (candidates.length > 0 ? 'FIXTURES_SWEEP_READY' : 'SOURCE_EMPTY')
            },
            candidates,
            seasonMirror,
            sampleLinked: this._scoreCandidatePoolSample(pendingMatches, candidates, confidenceThreshold, seasonMirror)
          };
        }
      );
      this._resetRouteFailureStreak(target, 'fixtures');
      return routeSource;
    } catch (error) {
      if (error?.code === 'LEAGUE_TIMEOUT') {
        throw error;
      }
      const failure = this._recordRouteProbeFailure(target, 'fixtures', error, { timeoutMs });
      if (failure.shouldDegrade) {
        return this._buildDegradedRouteSource(
          'fixtures',
          target,
          failure.sourceState,
          error,
          {
            timeoutMs,
            searchBlocked: failure.searchBlocked
          }
        );
      }
      throw error;
    }
  },

  async _probeSearchCandidateSource(target, pendingMatches, confidenceThreshold, navigator = null, options = {}) {
    if (!Array.isArray(pendingMatches) || pendingMatches.length === 0) {
      return null;
    }

    const timeoutMs = this._resolveRouteProbeTimeoutMs('search', target);
    if (target?.disableSearchRoute === true) {
      return this._buildDegradedRouteSource(
        'search',
        target,
        'ROUTE_SKIPPED_SEARCH_DISABLED',
        null,
        {
          timeoutMs,
          searchBlocked: true
        }
      );
    }

    if (this._isSearchProbeBlocked(target)) {
      return this._buildDegradedRouteSource(
        'search',
        target,
        'ROUTE_SKIPPED_DEGRADED_LEAGUE',
        null,
        {
          timeoutMs,
          searchBlocked: true
        }
      );
    }

    try {
      const routeSource = await this._executeRouteProbeWithNavigator(
        target,
        navigator,
        {
          routeKind: 'search',
          launchBrowser: true,
          useDedicatedNavigator: options.useDedicatedNavigator === true
        },
        async (activeNavigator) => {
          const searchResult = await this._collectSearchCandidatesForPendingMatches(
            target,
            pendingMatches,
            activeNavigator,
            { timeoutMs }
          );
          const candidates = this._dedupeCandidatesByIdentity(searchResult?.matches || []);
          const seasonMirror = this._buildSeasonMirror(candidates);

          return {
            routeKind: 'search',
            source: {
              season: target?.dbSeason || null,
              url: (searchResult?.sourceUrls || []).join(' | ')
            },
            extractResult: {
              matches: candidates,
              pagesScanned: Number(searchResult?.pagesScanned || 0),
              totalCandidates: candidates.length,
              sourceState: candidates.length > 0 ? 'SEARCH_SWEEP_READY' : 'SOURCE_EMPTY'
            },
            candidates,
            seasonMirror,
            sampleLinked: this._scoreCandidatePoolSample(pendingMatches, candidates, confidenceThreshold, seasonMirror)
          };
        }
      );
      this._resetRouteFailureStreak(target, 'search');
      return routeSource;
    } catch (error) {
      if (error?.code === 'LEAGUE_TIMEOUT') {
        throw error;
      }
      const failure = this._recordRouteProbeFailure(target, 'search', error, { timeoutMs });
      if (failure.shouldDegrade || failure.signals.has503 || failure.signals.hasTimeout) {
        return this._buildDegradedRouteSource(
          'search',
          target,
          failure.sourceState,
          error,
          {
            timeoutMs,
            searchBlocked: true
          }
        );
      }
      throw error;
    }
  },

  async _executeRouteProbeWithNavigator(target, navigator, options = {}, probe) {
    const routeKind = options.routeKind || 'unknown';
    const useDedicatedNavigator = options.useDedicatedNavigator === true;
    let handle = null;

    try {
      if (useDedicatedNavigator) {
        handle = await this._acquireTargetNavigator(target, {
          launchBrowser: options.launchBrowser !== false
        });
      }

      const activeNavigator = handle?.navigator || navigator || this.navigator || null;
      if (!activeNavigator) {
        return this._buildEmptyRouteSource(routeKind, target, 'ROUTE_SKIPPED_NO_NAVIGATOR');
      }

      return await probe(activeNavigator);
    } finally {
      await this._releaseTargetNavigator(handle);
    }
  },

  async _fetchCandidateRouteArchive(routeKind, url, target, pendingMatches, navigator) {
    if (!navigator) {
      return { matches: [], pagesScanned: 0, totalCandidates: 0, sourceState: 'ROUTE_SKIPPED_NO_NAVIGATOR' };
    }

    const circuitBreakerKey = typeof this.taskPlanner?.buildCircuitBreakerKey === 'function'
      ? `${this.taskPlanner.buildCircuitBreakerKey(target)}:${routeKind}:${target?.dbSeason || 'unknown'}`
      : `recon:${routeKind}:${target?.dbSeason || 'unknown'}`;
    const extractOptions = {
      maxPages: this.taskPlanner?.resolveArchiveMaxPages?.(target, pendingMatches) || this.archiveMaxPages || 50,
      timeoutMs: this._resolveRouteProbeTimeoutMs(routeKind, target),
      preferCurrentSeasonSource: true,
      circuitBreakerKey,
      disableTournamentFallback: true,
      forceDomOnly: routeKind === 'fixtures',
      leagueDeadlineAt: target?.leagueDeadlineAt ?? null
    };

    if (typeof navigator.fetchFullSeasonArchive === 'function') {
      return navigator.fetchFullSeasonArchive(url, extractOptions);
    }

    if (typeof navigator.protocolArchiveExtract === 'function') {
      return navigator.protocolArchiveExtract(url, extractOptions);
    }

    return { matches: [], pagesScanned: 0, totalCandidates: 0, sourceState: 'ROUTE_SKIPPED_NO_ARCHIVE_HANDLER' };
  },

  async _collectSearchCandidatesForPendingMatches(target, pendingMatches, navigator, options = {}) {
    if (!navigator || typeof navigator.navigate !== 'function' || !navigator.page) {
      return { matches: [], pagesScanned: 0, sourceUrls: [] };
    }

    if (typeof navigator.resetContextPerBatch === 'function') {
      await navigator.resetContextPerBatch({
        reason: 'search_candidate_batch'
      });
    }

    const matches = [];
    const sourceUrls = [];
    const seenCandidateKeys = new Set();

    for (const l1Match of Array.isArray(pendingMatches) ? pendingMatches : []) {
      const searchUrl = this._buildSearchUrlForMatch(l1Match);
      if (!searchUrl) {
        continue;
      }

      sourceUrls.push(searchUrl);
      const searchCandidates = await this._collectSearchCandidatesFromUrl(searchUrl, navigator, target, options);
      for (const candidate of searchCandidates) {
        const candidateKey = String(candidate?.hash || candidate?.url || '').trim();
        if (!candidateKey || seenCandidateKeys.has(candidateKey)) {
          continue;
        }

        seenCandidateKeys.add(candidateKey);
        matches.push(candidate);
      }
    }

    return {
      matches,
      pagesScanned: sourceUrls.length,
      sourceUrls
    };
  },

  _buildSearchUrlForMatch(l1Match) {
    const slug = this._buildFallbackEventSlug(l1Match?.home_team, l1Match?.away_team);
    if (!slug) {
      return '';
    }

    return `${this._resolveTrustedOddsPortalBaseUrl()}/search/${encodeURIComponent(slug)}/`;
  },

  async _collectSearchCandidatesFromUrl(searchUrl, navigator, target, options = {}) {
    await navigator.navigate(searchUrl, {
      waitUntil: 'domcontentloaded',
      timeout: Number(options.timeoutMs || this._resolveRouteProbeTimeoutMs('search', target))
    });
    if (typeof navigator.page?.waitForTimeout === 'function') {
      await navigator.page.waitForTimeout(this.pageSettleWaitMs);
    }

    return navigator.page.evaluate(({ baseUrl, sourceUrl }) => {
      const matches = [];
      const seen = new Set();
      const hashPattern = /-([A-Za-z0-9]{8})\/?(?:[#?].*)?$/;

      document.querySelectorAll('a[href*="/football/"]').forEach((link) => {
        const href = String(link.getAttribute('href') || '').trim();
        if (!href) {
          return;
        }

        const absoluteUrl = href.startsWith('http')
          ? href
          : `${String(baseUrl || '').replace(/\/+$/u, '')}/${href.replace(/^\/+/u, '')}`;
        if (/\/(?:results|fixtures)\//iu.test(absoluteUrl)) {
          return;
        }

        const match = absoluteUrl.match(hashPattern);
        if (!match) {
          return;
        }

        const normalizedUrl = absoluteUrl.split('#')[0];
        if (seen.has(normalizedUrl)) {
          return;
        }

        seen.add(normalizedUrl);
        matches.push({
          url: normalizedUrl,
          hash: match[1],
          source: 'search_route',
          sourceUrl
        });
      });

      return matches;
    }, {
      baseUrl: this._resolveTrustedOddsPortalBaseUrl(),
      sourceUrl: searchUrl
    });
  },

  async _selectCandidateSourceWithLocalFallback(target, pendingMatches, confidenceThreshold, navigator = null) {
    try {
      const selectedSource = await this._probeCandidateRoutes(
        target,
        pendingMatches,
        confidenceThreshold,
        navigator
      );
      const hasCandidates = Array.isArray(selectedSource?.candidates) && selectedSource.candidates.length > 0;
      if (hasCandidates || !this._canUseLocalDictionaryFallback(target, pendingMatches)) {
        return selectedSource;
      }

      this.logger.warn('recon_local_dictionary_fallback_armed', {
        league: target?.league?.name || null,
        season: target?.dbSeason || null,
        sourceState: selectedSource?.extractResult?.sourceState || 'SOURCE_EMPTY',
        routeKinds: selectedSource?.routeKinds || [],
        pendingTotal: pendingMatches.length
      });
      return this._buildLocalDictionarySelectedSource(target, pendingMatches, 'LOCAL_DICTIONARY_FALLBACK');
    } catch (error) {
      if (!this._canUseLocalDictionaryFallback(target, pendingMatches)) {
        throw error;
      }

      this.logger.warn('recon_local_dictionary_fallback_recovered', {
        league: target?.league?.name || null,
        season: target?.dbSeason || null,
        pendingTotal: pendingMatches.length,
        error: error.message
      });
      return this._buildLocalDictionarySelectedSource(target, pendingMatches, 'LOCAL_DICTIONARY_FALLBACK');
    }
  }
};

module.exports = { reconSourceProber };
