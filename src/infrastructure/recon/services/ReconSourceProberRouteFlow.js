'use strict';

const {
  RESULTS_PROBE_SEARCH_SHORT_CIRCUIT_TIMEOUT_MS,
  getCandidateCount,
  hasForcedResultsProbeSearchShortCircuit,
  isMatrixModePruningEnabled,
  resolveResultsProbeShortCircuitBudget,
  resolveSampleLinkedThreshold,
  shouldForceResultsProbeSearchShortCircuit
} = require('./ReconSourceProberRouteUtils');

const reconSourceProberRouteFlow = {
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

  async _probeCandidateRoutes(target, pendingMatches, confidenceThreshold, navigator = null) {
    const sharedNavigator = navigator || this.navigator || null;
    const matrixModePruning = isMatrixModePruningEnabled(target);
    const runInParallel = matrixModePruning ? false : this._canRunParallelRouteProbes();
    const sampleTarget = typeof this._buildRouteProbeSample === 'function'
      ? this._buildRouteProbeSample(pendingMatches).length
      : 0;
    const sampleLinkedThreshold = resolveSampleLinkedThreshold(sampleTarget, target);
    const settled = runInParallel
      ? await this._probeRoutesInParallel(target, pendingMatches, confidenceThreshold, sharedNavigator)
      : await this._probeRoutesSequentially(
        target,
        pendingMatches,
        confidenceThreshold,
        sharedNavigator,
        matrixModePruning,
        sampleTarget,
        sampleLinkedThreshold
      );

    const { successfulRoutes, routeFailures } = this._partitionRouteProbeResults(settled);

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
      this._logRouteShortCircuit(target, sampleTarget, preSearchState.combinedSampleLinked, sampleLinkedThreshold, matrixModePruning, ['search']);
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

  async _probeRoutesInParallel(target, pendingMatches, confidenceThreshold, sharedNavigator) {
    return Promise.allSettled([
      this._probeResultsCandidateSource(target, pendingMatches, confidenceThreshold, sharedNavigator),
      this._probeFixturesCandidateSource(target, pendingMatches, confidenceThreshold, sharedNavigator, {
        useDedicatedNavigator: true
      })
    ]);
  },

  async _probeRoutesSequentially(
    target,
    pendingMatches,
    confidenceThreshold,
    sharedNavigator,
    matrixModePruning,
    sampleTarget,
    sampleLinkedThreshold
  ) {
    const settled = [];
    settled.push(await this._settleRouteProbe(() => (
      this._probeResultsCandidateSource(target, pendingMatches, confidenceThreshold, sharedNavigator)
    )));

    const resultsOnlyState = this._buildCandidateRouteState(
      settled
        .filter((item) => item.status === 'fulfilled')
        .map((item) => item.value),
      pendingMatches,
      confidenceThreshold
    );
    const resultsRoute = settled.find((item) => item.status === 'fulfilled')?.value || null;
    const shouldContinueSearchAfterEmptyResults = hasForcedResultsProbeSearchShortCircuit(resultsRoute);
    const shouldShortCircuitOnEmptyResults = matrixModePruning
      && resultsRoute
      && getCandidateCount(resultsRoute) === 0
      && !shouldContinueSearchAfterEmptyResults;

    if (shouldShortCircuitOnEmptyResults || (
      sampleLinkedThreshold > 0
      && resultsOnlyState.combinedSampleLinked >= sampleLinkedThreshold
    )) {
      this._logRouteShortCircuit(
        target,
        sampleTarget,
        resultsOnlyState.combinedSampleLinked,
        sampleLinkedThreshold,
        matrixModePruning,
        ['fixtures', 'search']
      );
      return settled;
    }

    if (shouldContinueSearchAfterEmptyResults) {
      this.logger.info('recon_results_probe_search_short_circuit', {
        league: target?.league?.name || null,
        season: target?.dbSeason || null,
        resultsProbeDurationMs: Number(
          resultsRoute?.probeDurationMs
          || resultsRoute?.shortCircuitTimeoutMs
          || 0
        ),
        shortCircuitTimeoutMs: Number(resultsRoute?.shortCircuitTimeoutMs || 0),
        sourceState: resultsRoute?.extractResult?.sourceState || 'SOURCE_EMPTY',
        skippedRoutes: ['fixtures']
      });
      return settled;
    }

    settled.push(await this._settleRouteProbe(() => (
      this._probeFixturesCandidateSource(target, pendingMatches, confidenceThreshold, sharedNavigator, {
        useDedicatedNavigator: false
      })
    )));

    return settled;
  },

  async _settleRouteProbe(probe) {
    try {
      return {
        status: 'fulfilled',
        value: await probe()
      };
    } catch (error) {
      return {
        status: 'rejected',
        reason: error
      };
    }
  },

  _partitionRouteProbeResults(settled = []) {
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

    return { successfulRoutes, routeFailures };
  },

  _logRouteShortCircuit(target, sampleSize, sampleLinked, sampleLinkedThreshold, matrixModePruning, skippedRoutes = []) {
    this.logger.info('recon_candidate_routes_short_circuit', {
      league: target?.league?.name || null,
      season: target?.dbSeason || null,
      sampleSize,
      sampleLinked,
      sampleLinkedThreshold,
      matrixModePruning,
      skippedRoutes
    });
  },

  async _probeResultsCandidateSource(target, pendingMatches, confidenceThreshold, navigator = null) {
    const timeoutMs = this._resolveRouteProbeTimeoutMs('results', target);
    const matrixModePruning = isMatrixModePruningEnabled(target);
    const enableSearchShortCircuit = shouldForceResultsProbeSearchShortCircuit(target);
    const shortCircuitTimeoutMs = enableSearchShortCircuit
      ? Math.min(timeoutMs, RESULTS_PROBE_SEARCH_SHORT_CIRCUIT_TIMEOUT_MS)
      : 0;
    const {
      probeDeadlineAt: shortCircuitProbeDeadlineAt,
      shortCircuitOwnsDeadline
    } = enableSearchShortCircuit
      ? resolveResultsProbeShortCircuitBudget(target, shortCircuitTimeoutMs)
      : { probeDeadlineAt: target?.leagueDeadlineAt ?? null, shortCircuitOwnsDeadline: false };
    let selectedSource;
    try {
      if (enableSearchShortCircuit) {
        selectedSource = await this._executeRouteProbeWithNavigator(
          target,
          navigator,
          {
            routeKind: 'results',
            launchBrowser: true,
            useDedicatedNavigator: true
          },
          async (activeNavigator) => this._selectResultsRouteSource(
            target,
            pendingMatches,
            confidenceThreshold,
            activeNavigator,
            timeoutMs,
            matrixModePruning,
            shortCircuitProbeDeadlineAt,
            shortCircuitOwnsDeadline,
            shortCircuitTimeoutMs
          )
        );
      } else {
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
      }
      this._resetRouteFailureStreak(target, 'results');
    } catch (error) {
      if (error?.code === 'LEAGUE_TIMEOUT' || error?.code === 'RECON_SOURCE_INCOMPLETE') {
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

  async _selectResultsRouteSource(
    target,
    pendingMatches,
    confidenceThreshold,
    activeNavigator,
    timeoutMs,
    matrixModePruning,
    shortCircuitProbeDeadlineAt,
    shortCircuitOwnsDeadline,
    shortCircuitTimeoutMs
  ) {
    try {
      return await this.taskPlanner.selectCandidateSource(
        {
          ...target,
          leagueDeadlineAt: shortCircuitProbeDeadlineAt
        },
        pendingMatches,
        confidenceThreshold,
        {
          navigator: activeNavigator || this.navigator || null,
          timeoutMs,
          disableTournamentFallback: true,
          matrixModePruning,
          matrixModeShortCircuitRatio: target?.matrixModeShortCircuitRatio,
          leagueDeadlineAt: shortCircuitProbeDeadlineAt
        }
      );
    } catch (error) {
      if (error?.code === 'LEAGUE_TIMEOUT' && shortCircuitOwnsDeadline) {
        return this._buildResultsProbeSearchShortCircuitSource(target, shortCircuitTimeoutMs);
      }
      throw error;
    }
  },

  _buildResultsProbeSearchShortCircuitSource(target, timeoutMs) {
    const routeSource = this._buildEmptyRouteSource('results', target, 'SOURCE_EMPTY');

    return {
      ...routeSource,
      forceSearchShortCircuit: true,
      probeDurationMs: timeoutMs,
      shortCircuitTimeoutMs: timeoutMs
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
        async (activeNavigator) => this._buildFixturesRouteSource(
          fixturesUrl,
          target,
          pendingMatches,
          confidenceThreshold,
          activeNavigator
        )
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

  async _buildFixturesRouteSource(fixturesUrl, target, pendingMatches, confidenceThreshold, activeNavigator) {
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
  }
};

module.exports = { reconSourceProberRouteFlow };
