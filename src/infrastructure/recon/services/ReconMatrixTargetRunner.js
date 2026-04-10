'use strict';

const pLimit = require('p-limit');

function buildReconTargetState(target, runtimeTarget, scopedPending, effectiveThreshold, routeMetadata, progress, resultsSource) {
  return {
    target,
    runtimeTarget,
    effectiveThreshold,
    routeMetadata,
    progress,
    resultsSource,
    remainingRoutePending: scopedPending,
    totalLinked: 0,
    totalMismatched: 0,
    totalCandidateCount: 0,
    finalSourceSeason: null,
    finalSourceUrl: null,
    lastSourceState: resultsSource?.extractResult?.sourceState || 'SOURCE_EMPTY'
  };
}

const reconMatrixTargetRunner = {
  async _prepareReconTargetState(target, options = {}) {
    const {
      concurrency = this.defaultReconConcurrency,
      confidenceThreshold = this.confidenceThreshold,
      forceDomMode = this.forceDomMode === true,
      forceJsonExtract = false,
      forcePureProtocol = false,
      pendingMatches: pendingMatchesOverride = null,
      matchLimit = null,
      navigator = this.navigator || null
    } = options;

    const pendingMatches = Array.isArray(pendingMatchesOverride)
      ? pendingMatchesOverride
      : await this.taskPlanner.loadReconPendingMatches(target, {
        allNonLinked: this.allNonLinked === true
      });

    if (!Array.isArray(pendingMatches) || pendingMatches.length === 0) {
      return null;
    }

    const orderedPending = [...pendingMatches].sort((a, b) => String(a.match_id).localeCompare(String(b.match_id)));
    const reconPolicy = this.taskPlanner.resolveReconPolicy(target, orderedPending, confidenceThreshold);
    const effectiveThreshold = Math.max(
      Number(reconPolicy.effectiveConfidenceThreshold || confidenceThreshold || 0),
      Number(this.minimumConfidenceThreshold || 0)
    );
    const runtimeTarget = {
      ...target,
      forceDomMode,
      forceJsonExtract,
      forcePureProtocol,
      reconPolicy: {
        ...(target?.reconPolicy || {}),
        ...reconPolicy
      }
    };
    runtimeTarget.leagueDictionaryEntries = await this._primeLeagueDictionary(runtimeTarget);

    const resultsSource = await this._probeResultsCandidateSource(
      runtimeTarget,
      orderedPending,
      effectiveThreshold,
      navigator
    );
    const resultsCandidates = Array.isArray(resultsSource?.candidates) ? resultsSource.candidates : [];
    const resultsSeasonMirror = resultsSource?.seasonMirror
      || this.mirrorManager.buildSeasonMirror(resultsCandidates);
    const scopedPending = this._resolveScopedPendingMatches(
      orderedPending,
      matchLimit,
      resultsCandidates,
      effectiveThreshold,
      resultsSeasonMirror
    );

    if (!Array.isArray(scopedPending) || scopedPending.length === 0) {
      return null;
    }

    const reconRunId = this._createReconRunId(target);
    const routeMetadata = {
      reconRunId,
      season: target.dbSeason,
      league: target.league.name,
      allowMismatchRetry: target?.reconPolicy?.allowMismatchRetry === true
    };
    const progress = {
      processed: 0,
      linked: 0,
      mismatched: 0,
      total: scopedPending.length,
      startedAt: Date.now()
    };

    return {
      ...buildReconTargetState(
        target,
        runtimeTarget,
        scopedPending,
        effectiveThreshold,
        routeMetadata,
        progress,
        resultsSource
      ),
      limiter: pLimit(Math.max(1, Number(concurrency))),
      persistLimiter: pLimit(1),
      navigator
    };
  },

  _applyReconRouteResult(routeState, routeResult, routeSource) {
    routeState.totalLinked += Number(routeResult?.linked || 0);
    routeState.totalMismatched += Number(routeResult?.mismatched || 0);
    routeState.totalCandidateCount += Number(
      routeSource?.localFallbackCandidateCount || routeSource?.candidates?.length || 0
    );
    routeState.remainingRoutePending = Array.isArray(routeResult?.remainingPending)
      ? routeResult.remainingPending
      : [];
    routeState.finalSourceSeason = routeSource?.source?.season || routeState.finalSourceSeason;
    routeState.finalSourceUrl = routeSource?.source?.url || routeState.finalSourceUrl;
    routeState.lastSourceState = routeSource?.extractResult?.sourceState || routeState.lastSourceState;
  },

  async _processReconRoute(routeState, routeKind, routeSource, routeOptions = {}) {
    const normalizedRouteSource = routeSource
      || this._buildEmptyRouteSource(routeKind, routeState.runtimeTarget, 'SOURCE_EMPTY');
    const routeResult = await this._processPendingMatchesWithShortCircuit(
      routeKind,
      normalizedRouteSource,
      routeState.remainingRoutePending,
      routeState.runtimeTarget,
      {
        confidenceThreshold: routeState.effectiveThreshold,
        limiter: routeState.limiter,
        persistLimiter: routeState.persistLimiter,
        progress: routeState.progress,
        metadata: routeState.routeMetadata,
        finalPass: routeOptions.finalPass === true,
        forceProcessWithoutCandidates: routeOptions.forceProcessWithoutCandidates === true
      }
    );

    this._applyReconRouteResult(routeState, routeResult, normalizedRouteSource);
  },

  async _runReconFixturesRoute(routeState) {
    const fixturesSource = await this._probeFixturesCandidateSource(
      routeState.runtimeTarget,
      routeState.remainingRoutePending,
      routeState.effectiveThreshold,
      routeState.navigator,
      { useDedicatedNavigator: false }
    );

    await this._processReconRoute(
      routeState,
      'fixtures',
      fixturesSource || this._buildEmptyRouteSource(
        'fixtures',
        routeState.runtimeTarget,
        'ROUTE_SKIPPED_NO_FIXTURES_URL'
      )
    );
  },

  _shouldUseLocalDictionaryRoute(routeState) {
    return routeState.remainingRoutePending.length > 0
      && this._canUseLocalDictionaryFallback(routeState.runtimeTarget, routeState.remainingRoutePending);
  },

  async _runReconSearchRoute(routeState, canUseLocalDictionaryFallback) {
    const searchSource = await this._probeSearchCandidateSource(
      routeState.runtimeTarget,
      routeState.remainingRoutePending,
      routeState.effectiveThreshold,
      routeState.navigator,
      { useDedicatedNavigator: false }
    );
    const searchHasCandidates = Array.isArray(searchSource?.candidates) && searchSource.candidates.length > 0;

    await this._processReconRoute(routeState, 'search', searchSource, {
      finalPass: canUseLocalDictionaryFallback !== true
        && (routeState.totalCandidateCount > 0 || searchHasCandidates)
    });
  },

  async _runReconLocalDictionaryRoute(routeState) {
    await this._processReconRoute(
      routeState,
      'local_dictionary',
      this._buildLocalDictionarySelectedSource(
        routeState.runtimeTarget,
        routeState.remainingRoutePending,
        'LOCAL_DICTIONARY_FALLBACK'
      ),
      {
        finalPass: true,
        forceProcessWithoutCandidates: true
      }
    );
  },

  async _runReconTargetRoutes(routeState) {
    await this._processReconRoute(routeState, 'results', routeState.resultsSource);

    if (routeState.remainingRoutePending.length > 0) {
      await this._runReconFixturesRoute(routeState);
    }

    const canUseLocalDictionaryFallback = this._shouldUseLocalDictionaryRoute(routeState);
    if (routeState.remainingRoutePending.length > 0) {
      await this._runReconSearchRoute(routeState, canUseLocalDictionaryFallback);
    }

    if (routeState.remainingRoutePending.length > 0 && canUseLocalDictionaryFallback) {
      await this._runReconLocalDictionaryRoute(routeState);
    }
  },

  _assertReconTargetResolved(routeState, target) {
    if (routeState.remainingRoutePending.length === 0) {
      return;
    }

    const error = new Error(routeState.lastSourceState || 'SOURCE_EMPTY');
    error.code = routeState.lastSourceState || 'SOURCE_EMPTY';
    error.sourceUrl = routeState.finalSourceUrl || target.resultsUrl;
    error.sourceSeason = routeState.finalSourceSeason || this.taskPlanner.formatSeasonForUrl(target.season);
    throw error;
  },

  _buildReconTargetResult(routeState, target) {
    return {
      pendingTotal: routeState.progress.total,
      linked: routeState.totalLinked,
      mismatched: routeState.totalMismatched,
      sourceSeason: routeState.finalSourceSeason || this.taskPlanner.formatSeasonForUrl(target.season),
      sourceUrl: routeState.finalSourceUrl || target.resultsUrl,
      candidateCount: routeState.totalCandidateCount,
      effectiveConfidenceThreshold: routeState.effectiveThreshold
    };
  },

  async _runReconTarget(target, options = {}) {
    const routeState = await this._prepareReconTargetState(target, options);
    if (!routeState) {
      return { pendingTotal: 0, linked: 0, mismatched: 0 };
    }

    await this._runReconTargetRoutes(routeState);
    this._assertReconTargetResolved(routeState, target);
    return this._buildReconTargetResult(routeState, target);
  }
};

module.exports = { reconMatrixTargetRunner };
