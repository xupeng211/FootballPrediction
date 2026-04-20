/* eslint-disable complexity */
'use strict';

const pLimit = require('p-limit');

const RESULTS_SEARCH_SHORT_CIRCUIT_TIMEOUT_MS = 20000;
const SEARCH_SHORT_CIRCUIT_LEAGUES = new Set([
  'j1 league',
  'brasileirao'
]);

function resolvePendingMatchTimestamp(match = null) {
  const timestamp = new Date(match?.match_date || match?.matchDate || '').getTime();
  return Number.isFinite(timestamp) ? timestamp : null;
}

function isFuturePendingMatch(match = null, now = new Date()) {
  const kickoffAt = resolvePendingMatchTimestamp(match);
  return kickoffAt !== null && kickoffAt > now.getTime();
}

function hasFuturePendingMatches(pendingMatches = [], now = new Date()) {
  return (Array.isArray(pendingMatches) ? pendingMatches : [])
    .some((match) => isFuturePendingMatch(match, now));
}

function shouldDeferFuturePendingFromResults(routeKind, routeSource = null) {
  if (routeKind !== 'results' && routeKind !== 'results_terminal') {
    return false;
  }

  const sourceMode = String(routeSource?.source?.mode || '').trim();
  return sourceMode !== 'current_fixtures' && sourceMode !== 'current_fixtures_fallback';
}

function splitDeferredFuturePendingMatches(pendingMatches = [], routeKind, routeSource = null, now = new Date()) {
  if (!shouldDeferFuturePendingFromResults(routeKind, routeSource)) {
    return {
      eligiblePending: Array.isArray(pendingMatches) ? [...pendingMatches] : [],
      deferredPending: []
    };
  }

  const eligiblePending = [];
  const deferredPending = [];
  for (const match of (Array.isArray(pendingMatches) ? pendingMatches : [])) {
    if (isFuturePendingMatch(match, now)) {
      deferredPending.push(match);
      continue;
    }
    eligiblePending.push(match);
  }

  return { eligiblePending, deferredPending };
}

function mergeDeferredPendingMatches(originalPending = [], deferredPending = [], routeRemainingPending = []) {
  const orderedIds = (Array.isArray(originalPending) ? originalPending : [])
    .map((match) => String(match?.match_id || ''))
    .filter(Boolean);
  const byId = new Map(
    [...(Array.isArray(deferredPending) ? deferredPending : []), ...(Array.isArray(routeRemainingPending) ? routeRemainingPending : [])]
      .map((match) => [String(match?.match_id || ''), match])
      .filter(([matchId]) => Boolean(matchId))
  );

  return orderedIds
    .filter((matchId, index) => orderedIds.indexOf(matchId) === index)
    .map((matchId) => byId.get(matchId))
    .filter(Boolean);
}

function normalizeLeagueName(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/gi, ' ')
    .trim()
    .toLowerCase();
}

function getRouteCandidateCount(routeSource = null) {
  return Array.isArray(routeSource?.candidates) ? routeSource.candidates.length : 0;
}

function shouldPreferSearchShortCircuit(target = {}) {
  return SEARCH_SHORT_CIRCUIT_LEAGUES.has(normalizeLeagueName(target?.league?.name));
}

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
    lastSourceState: resultsSource?.extractResult?.sourceState || 'SOURCE_EMPTY',
    resultsProbeDurationMs: Number(resultsSource?.probeDurationMs || 0),
    routeSampleTarget: 0,
    routeShortCircuitThreshold: 0
  };
}

const reconMatrixTargetRunner = {
  _shouldUseTargetDrivenSingleMatch(runtimeTarget = {}, pendingMatches = [], candidates = []) {
    return Number.isInteger(runtimeTarget?.matchLimit)
      && runtimeTarget.matchLimit === 1
      && Array.isArray(pendingMatches)
      && pendingMatches.length === 1
      && Array.isArray(candidates)
      && candidates.length > 0;
  },

  _buildTargetDrivenResultsSource(resultsSource = null, scopedPending = [], effectiveThreshold = 0) {
    const targetMatch = Array.isArray(scopedPending) ? scopedPending[0] : null;
    const matchId = String(targetMatch?.match_id || '');
    if (!resultsSource || !targetMatch || !matchId) {
      return resultsSource;
    }

    const preselectedCandidates = resultsSource?.targetDrivenCandidateMap instanceof Map
      ? (resultsSource.targetDrivenCandidateMap.get(matchId) || [])
      : [];
    const selectedCandidates = Array.isArray(preselectedCandidates) && preselectedCandidates.length > 0
      ? preselectedCandidates
      : [];
    const matched = selectedCandidates.length > 0
      ? {
        candidate: selectedCandidates[0],
        confidence: Number(resultsSource?.targetDrivenBestMatch?.confidence || 0)
      }
      : this.matchEvaluator?.findBestCandidate(targetMatch, resultsSource?.candidates || [], null) || null;
    const narrowedCandidates = selectedCandidates.length > 0
      ? selectedCandidates
      : matched?.candidate
        ? [matched.candidate]
        : [];

    if (narrowedCandidates.length === 0) {
      return resultsSource;
    }

    this.logger.info('recon_target_driven_single_match_ready', {
      league: resultsSource?.source?.league || null,
      sourceUrl: resultsSource?.source?.url || null,
      matchId,
      originalCandidateCount: Array.isArray(resultsSource?.candidates) ? resultsSource.candidates.length : 0,
      narrowedCandidateCount: narrowedCandidates.length,
      confidence: Number(matched?.confidence || 0),
      effectiveThreshold: Number(effectiveThreshold || 0),
      candidateHash: narrowedCandidates[0]?.hash || null,
      candidateUrl: narrowedCandidates[0]?.url || null
    });

    return {
      ...resultsSource,
      candidates: narrowedCandidates,
      seasonMirror: new Map(),
      originalCandidateCount: Array.isArray(resultsSource?.candidates) ? resultsSource.candidates.length : 0,
      targetDrivenSingleMatch: true,
      targetDrivenBestMatch: {
        matchId,
        confidence: Number(matched?.confidence || 0),
        candidateHash: narrowedCandidates[0]?.hash || null,
        candidateUrl: narrowedCandidates[0]?.url || null
      }
    };
  },

  _shouldAllowPrepareScopedPendingBudgetGrace(runtimeTarget = {}, scopedPending = [], resultsSource = null) {
    return Number.isInteger(runtimeTarget?.matchLimit)
      && runtimeTarget.matchLimit === 1
      && Array.isArray(scopedPending)
      && scopedPending.length === 1
      && resultsSource?.targetDrivenSingleMatch === true
      && Array.isArray(resultsSource?.candidates)
      && resultsSource.candidates.length > 0;
  },

  _isResultsSourceIncomplete(routeState = null) {
    return routeState?.resultsSource?.sourceHealth?.incomplete === true
      || routeState?.resultsSource?.extractResult?.sourceIncomplete === true;
  },

  _buildIncompleteResultsSourceError(routeState = null, stage = 'results_source_incomplete') {
    const sourceHealth = routeState?.resultsSource?.sourceHealth
      || routeState?.resultsSource?.extractResult?.sourceHealth
      || {};
    const error = new Error('RECON_SOURCE_INCOMPLETE');
    error.code = 'RECON_SOURCE_INCOMPLETE';
    error.stage = stage;
    error.retryable = true;
    error.shouldSwitchProxy = true;
    error.sourceUrl = routeState?.resultsSource?.source?.url
      || routeState?.finalSourceUrl
      || routeState?.runtimeTarget?.resultsUrl
      || routeState?.target?.resultsUrl
      || null;
    error.sourceSeason = routeState?.resultsSource?.source?.season
      || routeState?.finalSourceSeason
      || routeState?.runtimeTarget?.dbSeason
      || routeState?.target?.dbSeason
      || null;
    error.incompleteReasons = [...(sourceHealth?.incompleteReasons || [])];
    error.pageFailureCount = Number(sourceHealth?.pageFailureCount || 0);
    error.expectedPages = Number(sourceHealth?.expectedPages || 0);
    error.observedPages = Number(sourceHealth?.observedPages || 0);
    error.requiredCandidateFloor = Number(sourceHealth?.requiredCandidateFloor || 0);
    error.candidateCount = Number(sourceHealth?.candidateCount || 0);
    error.candidateShortfall = Number(sourceHealth?.candidateShortfall || 0);
    return error;
  },

  async _prepareReconTargetState(target, options = {}) {
    const {
      concurrency = this.defaultReconConcurrency,
      confidenceThreshold = this.confidenceThreshold,
      forceDomMode = this.forceDomMode === true,
      forceJsonExtract = false,
      forcePureProtocol = false,
      pendingMatches: pendingMatchesOverride = null,
      matchLimit = null,
      navigator = this.navigator || null,
      resultsOnlyMode = false,
      disableSearchRoute = false,
      matrixModePruning = false,
      matrixModeShortCircuitRatio = 0.5,
      leagueDeadlineAt = null
    } = options;

    const pendingMatches = Array.isArray(pendingMatchesOverride)
      ? pendingMatchesOverride
      : await this.taskPlanner.loadReconPendingMatches(target, {
        allNonLinked: this.allNonLinked === true
      });

    if (!Array.isArray(pendingMatches) || pendingMatches.length === 0) {
      return null;
    }

    const orderedPending = typeof this.taskPlanner?.orderPendingMatchesForProcessing === 'function'
      ? this.taskPlanner.orderPendingMatchesForProcessing(pendingMatches)
      : [...pendingMatches].sort((a, b) => String(a.match_id).localeCompare(String(b.match_id)));
    const reconPolicy = this.taskPlanner.resolveReconPolicy(target, orderedPending, confidenceThreshold);
    const resolvedPolicyThreshold = Number(reconPolicy.effectiveConfidenceThreshold);
    const effectiveThreshold = Number.isFinite(resolvedPolicyThreshold)
      ? resolvedPolicyThreshold
      : Math.max(
        Number(confidenceThreshold || 0),
        Number(this.minimumConfidenceThreshold || 0)
      );
    const runtimeTarget = {
      ...target,
      forceDomMode,
      forceJsonExtract,
      forcePureProtocol,
      matchLimit,
      resultsOnlyMode,
      disableSearchRoute,
      matrixModePruning,
      matrixModeShortCircuitRatio,
      leagueDeadlineAt,
      reconPolicy: {
        ...(target?.reconPolicy || {}),
        ...reconPolicy
      }
    };
    runtimeTarget.leagueDictionaryEntries = await this._primeLeagueDictionary(runtimeTarget);

    this._assertLeagueBudget(runtimeTarget, null, 'prepare_results_source');
    const resultsProbeStartedAt = Date.now();
    const resultsSource = await this._probeResultsCandidateSource(
      runtimeTarget,
      orderedPending,
      effectiveThreshold,
      navigator
    );
    const resultsProbeDurationMs = Math.max(0, Date.now() - resultsProbeStartedAt);
    const resultsCandidates = Array.isArray(resultsSource?.candidates) ? resultsSource.candidates : [];
    const targetDrivenSingleMatch = this._shouldUseTargetDrivenSingleMatch(
      runtimeTarget,
      orderedPending,
      resultsCandidates
    );
    const resultsSeasonMirror = targetDrivenSingleMatch
      ? new Map()
      : resultsSource?.seasonMirror || this.mirrorManager.buildSeasonMirror(resultsCandidates);
    const scopedPending = this._resolveScopedPendingMatches(
      orderedPending,
      matchLimit,
      resultsCandidates,
      effectiveThreshold,
      resultsSeasonMirror
    );
    const preparedResultsSource = targetDrivenSingleMatch
      ? this._buildTargetDrivenResultsSource(resultsSource, scopedPending, effectiveThreshold)
      : resultsSource;
    const preparedResultsSourceWithMetrics = preparedResultsSource
      ? {
        ...preparedResultsSource,
        probeDurationMs: Number(preparedResultsSource?.probeDurationMs || resultsProbeDurationMs)
      }
      : preparedResultsSource;
    const hasFuturePending = hasFuturePendingMatches(scopedPending);

    if (!Array.isArray(scopedPending) || scopedPending.length === 0) {
      return null;
    }
    runtimeTarget.resultsOnlyMode = hasFuturePending ? false : resultsOnlyMode;
    runtimeTarget.disableSearchRoute = hasFuturePending ? false : disableSearchRoute;
    runtimeTarget.allowFutureSlowRoutes = hasFuturePending;
    if (!this._shouldAllowPrepareScopedPendingBudgetGrace(runtimeTarget, scopedPending, preparedResultsSource)) {
      this._assertLeagueBudget(runtimeTarget, null, 'prepare_scoped_pending');
    } else {
      const deadlineAt = Number(runtimeTarget?.leagueDeadlineAt || 0);
      if (Number.isFinite(deadlineAt) && deadlineAt > 0 && Date.now() >= deadlineAt) {
        this.logger.warn('recon_prepare_scoped_pending_budget_grace', {
          league: runtimeTarget?.league?.name || null,
          season: runtimeTarget?.dbSeason || null,
          matchId: scopedPending[0]?.match_id || null,
          originalCandidateCount: Number(preparedResultsSource?.originalCandidateCount || resultsCandidates.length || 0),
          narrowedCandidateCount: Number(preparedResultsSource?.candidates?.length || 0),
          sourceUrl: preparedResultsSource?.source?.url || runtimeTarget?.resultsUrl || null
        });
      }
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
        preparedResultsSourceWithMetrics
      ),
      routeSampleTarget: typeof this._buildRouteProbeSample === 'function'
        ? this._buildRouteProbeSample(scopedPending).length
        : 0,
      routeShortCircuitThreshold: this._resolveRouteShortCircuitThreshold(scopedPending, runtimeTarget),
      limiter: pLimit(Math.max(1, Number(concurrency))),
      persistLimiter: pLimit(1),
      navigator
    };
  },

  _resolveRouteShortCircuitThreshold(pendingMatches, runtimeTarget = {}) {
    const sampleTarget = typeof this._buildRouteProbeSample === 'function'
      ? this._buildRouteProbeSample(pendingMatches).length
      : 0;
    if (sampleTarget <= 0) {
      return 0;
    }

    if (runtimeTarget?.matrixModePruning !== true) {
      return sampleTarget;
    }

    const rawRatio = Number(runtimeTarget?.matrixModeShortCircuitRatio ?? 0.5);
    const ratio = Number.isFinite(rawRatio)
      ? Math.min(1, Math.max(0, rawRatio))
      : 0.5;

    return Math.max(1, Math.ceil(sampleTarget * ratio));
  },

  _buildLeagueTimeoutError(target, routeState = null, stage = 'league_timeout') {
    const error = new Error('LEAGUE_TIMEOUT');
    error.code = 'LEAGUE_TIMEOUT';
    error.stage = stage;
    error.sourceUrl = routeState?.finalSourceUrl
      || routeState?.runtimeTarget?.resultsUrl
      || target?.resultsUrl
      || null;
    error.sourceSeason = routeState?.finalSourceSeason
      || routeState?.runtimeTarget?.dbSeason
      || target?.dbSeason
      || null;
    return error;
  },

  _assertLeagueBudget(target, routeState = null, stage = 'league_budget_check') {
    const deadlineAt = Number(target?.leagueDeadlineAt || routeState?.runtimeTarget?.leagueDeadlineAt || 0);
    if (!Number.isFinite(deadlineAt) || deadlineAt <= 0 || Date.now() < deadlineAt) {
      return false;
    }

    this.logger.warn('recon_league_timeout', {
      league: target?.league?.name || routeState?.target?.league?.name || null,
      season: target?.dbSeason || routeState?.target?.dbSeason || null,
      stage,
      linked: Number(routeState?.totalLinked || 0),
      remainingPending: Number(routeState?.remainingRoutePending?.length || 0)
    });

    if (Number(routeState?.totalLinked || 0) > 0) {
      return true;
    }

    throw this._buildLeagueTimeoutError(target, routeState, stage);
  },

  _shouldFinalizeAfterResults(routeState) {
    if (routeState.remainingRoutePending.length === 0 || routeState.runtimeTarget?.matrixModePruning !== true) {
      return false;
    }

    if (
      routeState.runtimeTarget?.allowFutureSlowRoutes === true
      && hasFuturePendingMatches(routeState.remainingRoutePending)
    ) {
      return false;
    }

    if (this._isResultsSourceIncomplete(routeState)) {
      return false;
    }

    const resultsCandidateCount = Array.isArray(routeState.resultsSource?.candidates)
      ? routeState.resultsSource.candidates.length
      : 0;
    if (resultsCandidateCount === 0) {
      return !this._shouldShortCircuitResultsToSearch(routeState);
    }

    return routeState.routeShortCircuitThreshold > 0
      && Number(routeState.resultsSource?.sampleLinked || 0) >= routeState.routeShortCircuitThreshold;
  },

  async _finalizeRemainingPending(routeState) {
    if (routeState.remainingRoutePending.length === 0) {
      return;
    }

    await this._processReconRoute(
      routeState,
      'results_terminal',
      routeState.resultsSource,
      { finalPass: true }
    );
  },

  async _finalizeRemainingPendingWithLocalDictionary(routeState) {
    const canUseLocalDictionaryFallback = this._shouldUseLocalDictionaryRoute(routeState);
    if (canUseLocalDictionaryFallback) {
      await this._runReconLocalDictionaryRoute(routeState);
      return true;
    }

    await this._finalizeRemainingPending(routeState);
    return true;
  },

  async _finalizeIfBudgetExhausted(routeState, stage) {
    if (!this._assertLeagueBudget(routeState.runtimeTarget, routeState, stage)) {
      return false;
    }

    await this._finalizeRemainingPending(routeState);
    return true;
  },

  async _handlePostResultsFlow(routeState) {
    if (routeState.remainingRoutePending.length === 0) {
      return true;
    }

    if (await this._finalizeIfBudgetExhausted(routeState, 'after_results')) {
      return true;
    }

    if (this._shouldFinalizeAfterResults(routeState)) {
      await this._finalizeRemainingPendingWithLocalDictionary(routeState);
      return true;
    }

    return false;
  },

  _shouldShortCircuitResultsToSearch(routeState = null) {
    if (!routeState || routeState.runtimeTarget?.disableSearchRoute === true) {
      return false;
    }

    if (!shouldPreferSearchShortCircuit(routeState.runtimeTarget || routeState.target || {})) {
      return false;
    }

    if (!Array.isArray(routeState.remainingRoutePending) || routeState.remainingRoutePending.length === 0) {
      return false;
    }

    if (getRouteCandidateCount(routeState.resultsSource) > 0) {
      return false;
    }

    if (routeState.resultsSource?.forceSearchShortCircuit === true) {
      return true;
    }

    const probeDurationMs = Number(
      routeState.resultsProbeDurationMs
      || routeState.resultsSource?.probeDurationMs
      || 0
    );
    return probeDurationMs >= RESULTS_SEARCH_SHORT_CIRCUIT_TIMEOUT_MS;
  },

  async _runPostResultsFallbackRoutes(routeState) {
    if (
      routeState.remainingRoutePending.length > 0
      && routeState.runtimeTarget?.resultsOnlyMode === true
      && !(
        routeState.runtimeTarget?.allowFutureSlowRoutes === true
        && hasFuturePendingMatches(routeState.remainingRoutePending)
      )
    ) {
      if (this._isResultsSourceIncomplete(routeState)) {
        this.logger.warn('recon_results_only_incomplete_source_retry', {
          league: routeState.target?.league?.name || null,
          season: routeState.target?.dbSeason || null,
          sourceUrl: routeState.resultsSource?.source?.url || null,
          sourceSeason: routeState.resultsSource?.source?.season || null,
          sourceState: routeState.resultsSource?.extractResult?.sourceState || 'SOURCE_EMPTY',
          incompleteReasons: routeState.resultsSource?.sourceHealth?.incompleteReasons
            || routeState.resultsSource?.extractResult?.sourceHealth?.incompleteReasons
            || [],
          remainingPending: routeState.remainingRoutePending.length
        });
        throw this._buildIncompleteResultsSourceError(routeState, 'results_only_incomplete_source');
      }

      this.logger.info('recon_results_only_finalize', {
        league: routeState.target?.league?.name || null,
        season: routeState.target?.dbSeason || null,
        remainingPending: routeState.remainingRoutePending.length,
        skippedRoutes: ['fixtures', 'search', 'local_dictionary']
      });
      await this._finalizeRemainingPending(routeState);
      return;
    }

    if (
      routeState.remainingRoutePending.length > 0
      && routeState.runtimeTarget?.allowFutureSlowRoutes === true
      && hasFuturePendingMatches(routeState.remainingRoutePending)
    ) {
      this.logger.info('recon_results_only_bypassed_for_future_pending', {
        league: routeState.target?.league?.name || null,
        season: routeState.target?.dbSeason || null,
        remainingPending: routeState.remainingRoutePending.length
      });
    }

    if (routeState.remainingRoutePending.length > 0 && this._shouldShortCircuitResultsToSearch(routeState)) {
      const canUseLocalDictionaryFallback = this._shouldUseLocalDictionaryRoute(routeState);
      this.logger.info('recon_results_search_short_circuit', {
        league: routeState.target?.league?.name || null,
        season: routeState.target?.dbSeason || null,
        remainingPending: routeState.remainingRoutePending.length,
        resultsProbeDurationMs: Number(
          routeState.resultsProbeDurationMs
          || routeState.resultsSource?.probeDurationMs
          || 0
        ),
        sourceState: routeState.resultsSource?.extractResult?.sourceState || 'SOURCE_EMPTY',
        skippedRoutes: ['fixtures']
      });
      if (await this._finalizeIfBudgetExhausted(routeState, 'before_search_short_circuit')) {
        return;
      }
      await this._runReconSearchRoute(routeState, canUseLocalDictionaryFallback);
      if (routeState.remainingRoutePending.length > 0 && canUseLocalDictionaryFallback) {
        if (await this._finalizeIfBudgetExhausted(routeState, 'before_local_dictionary')) {
          return;
        }
        await this._runReconLocalDictionaryRoute(routeState);
      }
      return;
    }

    if (routeState.remainingRoutePending.length > 0) {
      if (await this._finalizeIfBudgetExhausted(routeState, 'before_fixtures')) {
        return;
      }
      await this._runReconFixturesRoute(routeState);
    }

    const canUseLocalDictionaryFallback = this._shouldUseLocalDictionaryRoute(routeState);
    if (routeState.remainingRoutePending.length > 0 && routeState.runtimeTarget?.disableSearchRoute !== true) {
      if (await this._finalizeIfBudgetExhausted(routeState, 'before_search')) {
        return;
      }
      await this._runReconSearchRoute(routeState, canUseLocalDictionaryFallback);
    }

    if (routeState.remainingRoutePending.length > 0 && canUseLocalDictionaryFallback) {
      if (await this._finalizeIfBudgetExhausted(routeState, 'before_local_dictionary')) {
        return;
      }
      await this._runReconLocalDictionaryRoute(routeState);
      return;
    }

    if (routeState.remainingRoutePending.length > 0 && routeState.runtimeTarget?.disableSearchRoute === true) {
      this.logger.info('recon_search_route_skipped', {
        league: routeState.target?.league?.name || null,
        season: routeState.target?.dbSeason || null,
        remainingPending: routeState.remainingRoutePending.length
      });
      await this._finalizeRemainingPending(routeState);
    }
  },

  _applyReconRouteResult(routeState, routeResult, routeSource) {
    routeState.totalLinked += Number(routeResult?.linked || 0);
    routeState.totalMismatched += Number(routeResult?.mismatched || 0);
    routeState.totalCandidateCount += Number(
      routeSource?.originalCandidateCount || routeSource?.localFallbackCandidateCount || routeSource?.candidates?.length || 0
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
    const { eligiblePending, deferredPending } = splitDeferredFuturePendingMatches(
      routeState.remainingRoutePending,
      routeKind,
      normalizedRouteSource,
      new Date()
    );
    let routeResult;

    if (eligiblePending.length === 0 && deferredPending.length > 0) {
      this.logger.info('recon_future_pending_deferred_from_results', {
        league: routeState.runtimeTarget?.league?.name || null,
        season: routeState.runtimeTarget?.dbSeason || null,
        routeKind,
        deferredPending: deferredPending.length
      });
      routeResult = {
        linked: 0,
        mismatched: 0,
        remainingPending: []
      };
    } else {
      routeResult = await this._processPendingMatchesWithShortCircuit(
        routeKind,
        normalizedRouteSource,
        eligiblePending,
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
    }

    routeResult.remainingPending = mergeDeferredPendingMatches(
      routeState.remainingRoutePending,
      deferredPending,
      routeResult?.remainingPending
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
    if (await this._handlePostResultsFlow(routeState)) {
      return;
    }

    await this._runPostResultsFallbackRoutes(routeState);
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
