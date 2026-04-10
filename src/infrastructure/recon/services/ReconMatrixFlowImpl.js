'use strict';

const crypto = require('crypto');
const pLimit = require('p-limit');
const { DynamicConcurrencyManager } = require('./DynamicConcurrencyManager');

const DEFAULT_LEAGUE_STARTUP_STAGGER_MS = 2000;

const ALLOWED_MAPPING_METHODS = new Set([
  'exact',
  'fuzzy',
  'manual',
  'unknown',
  'hash_lock',
  'set_reconciliation',
  'recon_matrix',
  'protocol_extract',
  'dictionary',
  'semantic',
  'V5.5_HARVESTER',
  'v41_186_auto'
]);

function sleep(delayMs) {
  return new Promise((resolve) => {
    setTimeout(resolve, delayMs);
  });
}

const reconMatrixFlow = {
  async buildScanTargets(options = {}) {
    return this.taskPlanner.buildScanTargets({
      ...options,
      currentSeasonOnly: options.currentSeasonOnly ?? this.currentSeasonOnly
    });
  },

  async runReconMatrix(options = {}) {
    const requestedConcurrency = Number.isInteger(options.concurrency) && options.concurrency > 0
      ? options.concurrency
      : this.defaultReconConcurrency;
    const requestedLeagueConcurrency = Number.isInteger(options.leagueConcurrency) && options.leagueConcurrency > 0
      ? options.leagueConcurrency
      : requestedConcurrency;
    const {
      season,
      concurrency = requestedConcurrency,
      leagueConcurrency = requestedLeagueConcurrency,
      leagueStartupStaggerMs = this.leagueStartupStaggerMs ?? DEFAULT_LEAGUE_STARTUP_STAGGER_MS,
      tier = null,
      leagueIds = null,
      batchSize = this.reconBatchSize,
      confidenceThreshold = this.confidenceThreshold,
      limit = null,
      forceDomMode = this.forceDomMode === true,
      forceJsonExtract = false,
      forcePureProtocol = false,
      mismatchRetryOnly = false,
      allNonLinked = this.allNonLinked === true
    } = options;

    const targets = await this.buildScanTargets({ season, tier, leagueIds });
    const summary = {
      success: true,
      season,
      scannedLeagues: 0,
      totalPending: 0,
      linked: 0,
      mismatched: 0,
      errors: [],
      perLeague: [],
      passes: 0,
      remainingPending: 0,
      availableProxies: null,
      perpetualMode: options.perpetualReconMode === true || this.perpetualReconMode === true
    };
    const normalizedLeagueConcurrency = Math.max(1, Number(leagueConcurrency));
    const adaptiveConcurrencyManager = this._createDynamicConcurrencyManager({
      floor: 1,
      initialConcurrency: Math.min(
        normalizedLeagueConcurrency,
        Math.max(1, Number(this.dynamicConcurrencyInitial || 5))
      ),
      maxConcurrency: normalizedLeagueConcurrency,
      successWindow: Math.max(1, Number(this.dynamicConcurrencySuccessWindow || 3))
    });
    const leagueSummaryMap = new Map();

    let targetPendingMap = await this.taskPlanner.prepareReconPendingTargets(targets, limit, {
      allowMismatchRetry: true,
      confidenceThreshold,
      mismatchRetryOnly,
      allNonLinked
    });
    summary.remainingPending = this._countPendingMatches(targetPendingMap);
    summary.availableProxies = this._resolveAvailableProxyCount();

    while (Array.isArray(targetPendingMap) && targetPendingMap.length > 0) {
      summary.passes += 1;

      const outcomes = await this._runAdaptiveLeagueWorkers(targetPendingMap, {
        season,
        concurrency,
        batchSize,
        confidenceThreshold,
        forceDomMode,
        forceJsonExtract,
        forcePureProtocol,
        leagueStartupStaggerMs,
        requestedLeagueConcurrency: normalizedLeagueConcurrency,
        adaptiveConcurrencyManager,
        passIndex: summary.passes
      });

      for (const outcome of outcomes) {
        if (outcome?.error) {
          summary.success = false;
          summary.errors.push({ league: outcome.target.league.name, error: outcome.error.message });
          continue;
        }

        const { target, result } = outcome;
        summary.totalPending += result.pendingTotal;
        summary.linked += result.linked;
        summary.mismatched += result.mismatched;
        this._mergeLeagueOutcomeIntoSummary(leagueSummaryMap, target, result);
      }

      targetPendingMap = await this.taskPlanner.prepareReconPendingTargets(targets, limit, {
        allowMismatchRetry: true,
        confidenceThreshold,
        mismatchRetryOnly,
        allNonLinked
      });
      summary.remainingPending = this._countPendingMatches(targetPendingMap);
      summary.availableProxies = this._resolveAvailableProxyCount();

      const shouldContinue = typeof this.shouldContinuePerpetualRecon === 'function'
        ? this.shouldContinuePerpetualRecon(summary.remainingPending, {
          perpetualReconMode: options.perpetualReconMode,
          availableProxyCount: summary.availableProxies
        })
        : options.perpetualReconMode === true
          && summary.remainingPending > 0
          && summary.availableProxies > 0;

      if (!shouldContinue) {
        break;
      }

      this.logger.warn('recon_matrix_perpetual_continue', {
        season,
        passIndex: summary.passes,
        remainingPending: summary.remainingPending,
        availableProxies: summary.availableProxies,
        leagueConcurrency: normalizedLeagueConcurrency
      });

      const delayMs = Math.max(
        0,
        Number(options.perpetualReconPassDelayMs ?? this.perpetualReconPassDelayMs ?? 0)
      );
      if (delayMs > 0) {
        await this._sleep(delayMs);
      }
    }

    summary.perLeague = [...leagueSummaryMap.values()];
    summary.scannedLeagues = summary.perLeague.length;
    return summary;
  },

  _countPendingMatches(targetPendingMap = []) {
    return (Array.isArray(targetPendingMap) ? targetPendingMap : [])
      .reduce((count, item) => count + Number(item?.pendingMatches?.length || 0), 0);
  },

  _resolveAvailableProxyCount() {
    if (typeof this.getAvailableProxyCount === 'function') {
      return this.getAvailableProxyCount();
    }

    const snapshot = this._getProxyPoolSnapshot();
    if (snapshot) {
      return snapshot.available;
    }

    return this.proxyRotator ? 0 : 1;
  },

  _mergeLeagueOutcomeIntoSummary(leagueSummaryMap, target, result) {
    const key = `${String(target?.dbSeason || '')}::${String(target?.league?.name || '')}`;
    const current = leagueSummaryMap.get(key) || {
      league: target?.league?.name || null,
      season: target?.dbSeason || null,
      pendingTotal: 0,
      linked: 0,
      mismatched: 0,
      sourceSeason: null,
      sourceUrl: null,
      candidateCount: 0,
      passes: 0
    };

    current.pendingTotal += Number(result?.pendingTotal || 0);
    current.linked += Number(result?.linked || 0);
    current.mismatched += Number(result?.mismatched || 0);
    current.candidateCount += Number(result?.candidateCount || 0);
    current.sourceSeason = result?.sourceSeason || current.sourceSeason;
    current.sourceUrl = result?.sourceUrl || current.sourceUrl;
    current.passes += 1;

    leagueSummaryMap.set(key, current);
  },

  _createDynamicConcurrencyManager(options = {}) {
    return new DynamicConcurrencyManager({
      logger: this.logger,
      ...options
    });
  },

  _getProxyPoolSnapshot() {
    if (!this.proxyRotator) {
      return null;
    }

    const stats = typeof this.proxyRotator.getHealthStatus === 'function'
      ? this.proxyRotator.getHealthStatus()
      : typeof this.proxyRotator.getStats === 'function'
        ? this.proxyRotator.getStats()
        : null;

    if (!stats || typeof stats !== 'object') {
      return null;
    }

    return {
      total: Math.max(0, Number(stats.total || 0)),
      healthy: Math.max(0, Number(stats.healthy || 0)),
      cooling: Math.max(0, Number(stats.cooling || 0)),
      dead: Math.max(0, Number(stats.dead || 0)),
      available: Math.max(0, Number(stats.available ?? stats.healthy ?? 0))
    };
  },

  _applyProxyFeedbackToConcurrency(manager, requestedLeagueConcurrency, metadata = {}) {
    const snapshot = this._getProxyPoolSnapshot();
    if (!snapshot) {
      return null;
    }

    const normalizedConcurrency = Math.max(1, Number(requestedLeagueConcurrency) || 1);
    const nextCeiling = Math.max(
      1,
      Math.min(
        normalizedConcurrency,
        snapshot.available > 0 ? snapshot.available : 1
      )
    );

    manager.setCeiling(nextCeiling, {
      proxyTotal: snapshot.total,
      proxyHealthy: snapshot.healthy,
      proxyCooling: snapshot.cooling,
      proxyDead: snapshot.dead,
      proxyAvailable: snapshot.available,
      ...metadata
    });

    return snapshot;
  },

  async _runAdaptiveLeagueWorkers(targetPendingMap, options = {}) {
    const outcomes = [];
    const running = new Map();
    const adaptiveConcurrencyManager = options.adaptiveConcurrencyManager || this._createDynamicConcurrencyManager();
    const requestedLeagueConcurrency = Math.max(1, Number(options.requestedLeagueConcurrency) || 1);
    let nextIndex = 0;

    this._applyProxyFeedbackToConcurrency(adaptiveConcurrencyManager, requestedLeagueConcurrency, {
      phase: 'initial',
      queueRemaining: targetPendingMap.length,
      activeLeagueWorkers: 0
    });

    while (nextIndex < targetPendingMap.length || running.size > 0) {
      this._applyProxyFeedbackToConcurrency(adaptiveConcurrencyManager, requestedLeagueConcurrency, {
        phase: 'dispatch',
        queueRemaining: Math.max(0, targetPendingMap.length - nextIndex),
        activeLeagueWorkers: running.size
      });

      while (
        nextIndex < targetPendingMap.length
        && running.size < adaptiveConcurrencyManager.getMaxActiveWorkers()
      ) {
        const currentIndex = nextIndex++;
        const workerPromise = this._executeLeagueWorker(targetPendingMap[currentIndex], currentIndex, {
          ...options,
          allowedLeagueWorkers: adaptiveConcurrencyManager.getMaxActiveWorkers(),
          activeWorkersAtStart: running.size + 1
        }).then((outcome) => ({ index: currentIndex, outcome }));

        running.set(currentIndex, workerPromise);
      }

      if (running.size === 0) {
        continue;
      }

      const { index, outcome } = await Promise.race(running.values());
      running.delete(index);
      outcomes[index] = outcome;

      const proxySnapshot = this._applyProxyFeedbackToConcurrency(adaptiveConcurrencyManager, requestedLeagueConcurrency, {
        phase: 'feedback',
        queueRemaining: Math.max(0, targetPendingMap.length - nextIndex),
        activeLeagueWorkers: running.size
      });

      if (outcome?.error) {
        adaptiveConcurrencyManager.recordFailure(outcome.error, {
          phase: 'feedback',
          league: outcome.target?.league?.name || null,
          season: outcome.target?.dbSeason || null,
          proxyPort: outcome.proxyPort || null,
          activeLeagueWorkers: running.size,
          proxyAvailable: proxySnapshot?.available ?? null,
          proxyTotal: proxySnapshot?.total ?? null
        });
      } else {
        adaptiveConcurrencyManager.recordSuccess({
          phase: 'feedback',
          league: outcome.target?.league?.name || null,
          season: outcome.target?.dbSeason || null,
          proxyPort: outcome.proxyPort || null,
          activeLeagueWorkers: running.size,
          proxyAvailable: proxySnapshot?.available ?? null,
          proxyTotal: proxySnapshot?.total ?? null
        });
      }
    }

    return outcomes.filter(Boolean);
  },

  async _executeLeagueWorker({ target, pendingMatches, desiredLimit = null }, index, options = {}) {
    const {
      season,
      concurrency,
      batchSize,
      confidenceThreshold,
      forceDomMode,
      forceJsonExtract,
      forcePureProtocol,
      leagueStartupStaggerMs,
      allowedLeagueWorkers = 1,
      activeWorkersAtStart = 1
    } = options;
    let navigatorHandle = null;
    let proxyPort = null;

    try {
      await this._delayLeagueWorkerStart(target, index, { leagueStartupStaggerMs });
      navigatorHandle = await this._acquireTargetNavigator(target, {
        launchBrowser: forcePureProtocol !== true
      });
      proxyPort = Number(navigatorHandle?.proxyPort || navigatorHandle?.navigator?.proxy?.port || 0) || null;
      const proxySnapshot = this._getProxyPoolSnapshot();

      this.logger.info('recon_league_worker_start', {
        league: target.league.name,
        season: target.dbSeason,
        pendingTotal: pendingMatches.length,
        desiredLimit,
        proxyPort,
        activeLeagueWorkers: activeWorkersAtStart,
        allowedLeagueWorkers,
        leagueStartupStaggerMs: Math.max(0, Number(leagueStartupStaggerMs) || 0),
        matchConcurrency: Math.max(1, Number(concurrency)),
        proxyAvailable: proxySnapshot?.available ?? null,
        proxyTotal: proxySnapshot?.total ?? null
      });

      const result = await this._runReconTarget(target, {
        concurrency,
        batchSize,
        confidenceThreshold,
        forceDomMode,
        forceJsonExtract,
        forcePureProtocol,
        pendingMatches,
        matchLimit: desiredLimit,
        navigator: navigatorHandle?.navigator || null
      });

      this.logger.info('recon_league_worker_complete', {
        league: target.league.name,
        season: target.dbSeason,
        proxyPort,
        activeLeagueWorkers: activeWorkersAtStart,
        allowedLeagueWorkers,
        linked: result.linked,
        mismatched: result.mismatched,
        pendingTotal: result.pendingTotal
      });

      return { target, result, proxyPort };
    } catch (error) {
      this.logger.error('recon_matrix_target_failed', {
        league: target.league.name,
        season,
        proxyPort,
        activeLeagueWorkers: activeWorkersAtStart,
        allowedLeagueWorkers,
        error: error.message,
        statusCode: Number(error?.statusCode || 0) || null
      });
      return { target, error, proxyPort };
    } finally {
      await this._releaseTargetNavigator(navigatorHandle);
    }
  },

  async _acquireTargetNavigator(_target, options = {}) {
    const launchBrowser = options.launchBrowser !== false;

    if (typeof this.ensureProxyPoolCapacity === 'function') {
      await this.ensureProxyPoolCapacity({
        minimumAvailable: this.minimumReadyProxyCount,
        context: launchBrowser ? 'recon_matrix_navigator_acquire' : 'recon_matrix_protocol_acquire'
      });
    }

    if (typeof this.navigatorFactory === 'function') {
      const created = await this.navigatorFactory({ launchBrowser });
      const handle = created?.navigator
        ? created
        : { navigator: created, ownsNavigator: true };

      if (
        launchBrowser
        && handle?.navigator
        && typeof handle.navigator.ensureBrowserHealthy === 'function'
      ) {
        await handle.navigator.ensureBrowserHealthy();
      }

      return {
        ...handle,
        ownsNavigator: handle?.ownsNavigator !== false,
        proxyPort: handle?.proxyPort ?? handle?.navigator?.proxy?.port ?? null
      };
    }

    if (
      launchBrowser
      && this.navigator
      && typeof this.navigator.ensureBrowserHealthy === 'function'
    ) {
      await this.navigator.ensureBrowserHealthy();
    }

    return {
      navigator: this.navigator || null,
      ownsNavigator: false,
      proxyPort: this.navigator?.proxy?.port || null
    };
  },

  async _releaseTargetNavigator(handle = null) {
    if (!handle?.navigator || handle.ownsNavigator === false) {
      return;
    }

    if (typeof handle.navigator.close === 'function') {
      await handle.navigator.close();
    }
  },

  _resolveLeagueWorkerStartupDelay(index, options = {}) {
    const stepMs = Number(options.leagueStartupStaggerMs);
    const normalizedStep = Number.isFinite(stepMs) && stepMs >= 0
      ? stepMs
      : DEFAULT_LEAGUE_STARTUP_STAGGER_MS;
    return Math.max(0, Number(index) || 0) * normalizedStep;
  },

  async _delayLeagueWorkerStart(target, index, options = {}) {
    const delayMs = this._resolveLeagueWorkerStartupDelay(index, options);
    if (delayMs <= 0) {
      return 0;
    }

    this.logger.info('recon_league_worker_stagger', {
      league: target?.league?.name || null,
      workerIndex: Number(index) || 0,
      delayMs
    });
    await this._sleep(delayMs);
    return delayMs;
  },

  async _sleep(delayMs) {
    await sleep(delayMs);
  },

  async _runReconTarget(target, options = {}) {
    const {
      concurrency = this.defaultReconConcurrency,
      batchSize = this.reconBatchSize,
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
      return { pendingTotal: 0, linked: 0, mismatched: 0 };
    }

    const limiter = pLimit(Math.max(1, Number(concurrency)));
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
    const remainingPending = orderedPending;
    const remainingMatchLimit = matchLimit;

    if (!Array.isArray(remainingPending) || remainingPending.length === 0) {
      return { pendingTotal: 0, linked: 0, mismatched: 0 };
    }

    const reconRunId = this._createReconRunId(target);
    const persistLimiter = pLimit(1);
    const resultsSource = await this._probeResultsCandidateSource(
      runtimeTarget,
      remainingPending,
      effectiveThreshold,
      navigator
    );
    const resultsCandidates = Array.isArray(resultsSource?.candidates) ? resultsSource.candidates : [];
    const resultsSeasonMirror = resultsSource?.seasonMirror
      || this.mirrorManager.buildSeasonMirror(resultsCandidates);
    const scopedPending = this._resolveScopedPendingMatches(
      remainingPending,
      remainingMatchLimit,
      resultsCandidates,
      effectiveThreshold,
      resultsSeasonMirror
    );

    if (!Array.isArray(scopedPending) || scopedPending.length === 0) {
      return { pendingTotal: 0, linked: 0, mismatched: 0 };
    }

    const progress = {
      processed: 0,
      linked: 0,
      mismatched: 0,
      total: scopedPending.length,
      startedAt: Date.now()
    };
    const routeMetadata = {
      reconRunId,
      season: target.dbSeason,
      league: target.league.name,
      allowMismatchRetry: target?.reconPolicy?.allowMismatchRetry === true
    };
    let remainingRoutePending = scopedPending;
    let totalLinked = 0;
    let totalMismatched = 0;
    let totalCandidateCount = 0;
    let finalSourceSeason = null;
    let finalSourceUrl = null;
    let lastSourceState = resultsSource?.extractResult?.sourceState || 'SOURCE_EMPTY';

    const applyRouteResult = (routeResult, routeSource) => {
      totalLinked += Number(routeResult?.linked || 0);
      totalMismatched += Number(routeResult?.mismatched || 0);
      totalCandidateCount += Number(routeSource?.localFallbackCandidateCount || routeSource?.candidates?.length || 0);
      remainingRoutePending = Array.isArray(routeResult?.remainingPending)
        ? routeResult.remainingPending
        : [];
      finalSourceSeason = routeSource?.source?.season || finalSourceSeason;
      finalSourceUrl = routeSource?.source?.url || finalSourceUrl;
      lastSourceState = routeSource?.extractResult?.sourceState || lastSourceState;
    };

    const processRoute = async (routeKind, routeSource, options = {}) => {
      const normalizedRouteSource = routeSource || this._buildEmptyRouteSource(routeKind, runtimeTarget, 'SOURCE_EMPTY');
      const routeResult = await this._processPendingMatchesWithShortCircuit(
        routeKind,
        normalizedRouteSource,
        remainingRoutePending,
        runtimeTarget,
        {
          confidenceThreshold: effectiveThreshold,
          limiter,
          persistLimiter,
          progress,
          metadata: routeMetadata,
          finalPass: options.finalPass === true,
          forceProcessWithoutCandidates: options.forceProcessWithoutCandidates === true
        }
      );
      applyRouteResult(routeResult, normalizedRouteSource);
    };

    await processRoute('results', resultsSource);

    if (remainingRoutePending.length > 0) {
      const fixturesSource = await this._probeFixturesCandidateSource(
        runtimeTarget,
        remainingRoutePending,
        effectiveThreshold,
        navigator,
        { useDedicatedNavigator: false }
      );
      await processRoute('fixtures', fixturesSource || this._buildEmptyRouteSource('fixtures', runtimeTarget, 'ROUTE_SKIPPED_NO_FIXTURES_URL'));
    }

    const canUseLocalDictionaryFallback = remainingRoutePending.length > 0
      && this._canUseLocalDictionaryFallback(runtimeTarget, remainingRoutePending);

    if (remainingRoutePending.length > 0) {
      const searchSource = await this._probeSearchCandidateSource(
        runtimeTarget,
        remainingRoutePending,
        effectiveThreshold,
        navigator,
        { useDedicatedNavigator: false }
      );
      const searchHasCandidates = Array.isArray(searchSource?.candidates) && searchSource.candidates.length > 0;
      await processRoute('search', searchSource, {
        finalPass: canUseLocalDictionaryFallback !== true && (totalCandidateCount > 0 || searchHasCandidates)
      });
    }

    if (remainingRoutePending.length > 0 && canUseLocalDictionaryFallback) {
      await processRoute(
        'local_dictionary',
        this._buildLocalDictionarySelectedSource(runtimeTarget, remainingRoutePending, 'LOCAL_DICTIONARY_FALLBACK'),
        {
          finalPass: true,
          forceProcessWithoutCandidates: true
        }
      );
    }

    if (remainingRoutePending.length > 0) {
      const error = new Error(lastSourceState || 'SOURCE_EMPTY');
      error.code = lastSourceState || 'SOURCE_EMPTY';
      error.sourceUrl = finalSourceUrl || target.resultsUrl;
      error.sourceSeason = finalSourceSeason || this.taskPlanner.formatSeasonForUrl(target.season);
      throw error;
    }

    return {
      pendingTotal: scopedPending.length,
      linked: totalLinked,
      mismatched: totalMismatched,
      sourceSeason: finalSourceSeason || this.taskPlanner.formatSeasonForUrl(target.season),
      sourceUrl: finalSourceUrl || target.resultsUrl,
      candidateCount: totalCandidateCount,
      effectiveConfidenceThreshold: effectiveThreshold
    };
  },

  _resolveScopedPendingMatches(pendingMatches, matchLimit, candidates, confidenceThreshold, seasonMirror = null) {
    const orderedPending = [...(Array.isArray(pendingMatches) ? pendingMatches : [])]
      .sort((a, b) => String(a.match_id).localeCompare(String(b.match_id)));

    if (!Number.isInteger(matchLimit) || matchLimit <= 0 || orderedPending.length <= matchLimit) {
      return orderedPending;
    }

    if (Array.isArray(candidates) && candidates.length > 0) {
      return this.taskPlanner.selectProcessablePendingMatches(
        orderedPending,
        candidates,
        confidenceThreshold,
        matchLimit,
        seasonMirror
      );
    }

    return orderedPending.slice(0, Math.min(matchLimit, orderedPending.length));
  },

  async _processPendingMatchesWithShortCircuit(routeKind, routeSource, pendingMatches, target, options = {}) {
    const {
      confidenceThreshold = this.confidenceThreshold,
      limiter = pLimit(1),
      persistLimiter = pLimit(1),
      progress = null,
      metadata = {},
      finalPass = false,
      forceProcessWithoutCandidates = false
    } = options;

    const candidates = Array.isArray(routeSource?.candidates) ? routeSource.candidates : [];
    const canProcessMatches = candidates.length > 0 || forceProcessWithoutCandidates === true || finalPass === true;
    if (!canProcessMatches) {
      this.logger.info('recon_route_short_circuit', {
        league: target?.league?.name || null,
        season: target?.dbSeason || null,
        routeKind,
        pendingTotal: pendingMatches.length,
        linked: 0,
        mismatched: 0,
        remainingPending: pendingMatches.length,
        sourceState: routeSource?.extractResult?.sourceState || 'SOURCE_EMPTY',
        finalPass
      });
      return {
        linked: 0,
        mismatched: 0,
        remainingPending: [...pendingMatches]
      };
    }

    const seasonMirror = routeSource?.seasonMirror || this.mirrorManager.buildSeasonMirror(candidates);
    const runtimeTargetWithSource = {
      ...target,
      reconSourceUrl: routeSource?.source?.url || target.resultsUrl,
      reconSourceSeason: routeSource?.source?.season || this.taskPlanner.formatSeasonForUrl(target.season)
    };
    const unresolvedMatches = [];
    let linked = 0;
    let mismatched = 0;

    await Promise.all(
      pendingMatches.map((l1Match) => limiter(async () => {
        const outcome = await this._reconcilePendingMatch(
          l1Match,
          candidates,
          runtimeTargetWithSource,
          confidenceThreshold,
          seasonMirror
        );

        if (outcome?.status === 'linked' && outcome.mapping) {
          const persistResult = await persistLimiter(() => this._persistReconOutcomeImmediately(outcome, {
            ...metadata,
            sourceSeason: runtimeTargetWithSource.reconSourceSeason,
            sourceUrl: runtimeTargetWithSource.reconSourceUrl
          }));
          linked += Number(persistResult?.linked || 0);
          if (progress) {
            progress.processed++;
            progress.linked += Number(persistResult?.linked || 0);
            if (this._shouldEmitReconProgressSnapshot(progress)) {
              this._emitReconProgressSnapshot(target, progress);
            }
          }
          return;
        }

        if (finalPass) {
          const persistResult = await persistLimiter(() => this._persistReconOutcomeImmediately(outcome, {
            ...metadata,
            sourceSeason: runtimeTargetWithSource.reconSourceSeason,
            sourceUrl: runtimeTargetWithSource.reconSourceUrl
          }));
          mismatched += Number(persistResult?.mismatched || 0);
          if (progress) {
            progress.processed++;
            progress.mismatched += Number(persistResult?.mismatched || 0);
            if (this._shouldEmitReconProgressSnapshot(progress)) {
              this._emitReconProgressSnapshot(target, progress);
            }
          }
          return;
        }

        unresolvedMatches.push(l1Match);
      }))
    );

    const orderedRemainingPending = unresolvedMatches
      .sort((left, right) => String(left?.match_id || '').localeCompare(String(right?.match_id || '')));

    this.logger.info('recon_route_short_circuit', {
      league: target?.league?.name || null,
      season: target?.dbSeason || null,
      routeKind,
      pendingTotal: pendingMatches.length,
      linked,
      mismatched,
      remainingPending: orderedRemainingPending.length,
      sourceState: routeSource?.extractResult?.sourceState || 'SOURCE_EMPTY',
      finalPass
    });

    return {
      linked,
      mismatched,
      remainingPending: orderedRemainingPending
    };
  },

  async _persistReconOutcomeImmediately(outcome, metadata = {}) {
    if (outcome?.status === 'linked' && outcome.mapping) {
      const persistResult = await this._persistReconBatches(
        [outcome.mapping],
        [],
        1,
        metadata
      );
      return {
        linked: Number(persistResult?.linkedApplied || 0),
        mismatched: 0
      };
    }

    if (outcome?.matchId) {
      const persistResult = await this._persistReconBatches(
        [],
        [{
          match_id: String(outcome.matchId),
          evidence: outcome.evidence || null
        }],
        1,
        metadata
      );
      return {
        linked: 0,
        mismatched: Number(persistResult?.mismatchUpdated || 0)
      };
    }

    return {
      linked: 0,
      mismatched: 0
    };
  },

  async _persistReconBatches(mappings, mismatchRecords, batchSize, metadata = {}) {
    const orderedMappings = [...mappings].sort((a, b) => String(a.match_id).localeCompare(String(b.match_id)));
    const orderedMismatchRecords = [...new Map(
      (Array.isArray(mismatchRecords) ? mismatchRecords : []).map((record) => {
        if (typeof record === 'string') {
          return [record, { match_id: record, evidence: null }];
        }

        const matchId = String(record?.match_id || record?.matchId || '');
        return [matchId, { match_id: matchId, evidence: record?.evidence || null }];
      }).filter(([matchId]) => Boolean(matchId))
    ).values()].sort((left, right) => String(left.match_id).localeCompare(String(right.match_id)));
    const orderedMismatchIds = orderedMismatchRecords.map((record) => String(record.match_id));
    const linkedBatches = this._buildLinkedPersistBatches(orderedMappings, batchSize, metadata);
    const linkedTotalBatches = Math.max(1, linkedBatches.length || 0);
    const mismatchTotalBatches = Math.max(1, Math.ceil(orderedMismatchIds.length / batchSize) || 0);
    let linkedApplied = 0;
    let mismatchUpdated = 0;

    for (let index = 0; index < linkedBatches.length; index++) {
      const batchMeta = linkedBatches[index];
      const batch = batchMeta.mappings;
      const batchIndex = index + 1;
      this.logger.info('recon_batch_persist_start', {
        recon_run_id: metadata.reconRunId || null,
        season: metadata.season || null,
        league: metadata.league || null,
        sourceSeason: metadata.sourceSeason || null,
        sourceUrl: metadata.sourceUrl || null,
        batch_type: 'linked',
        batch_index: batchIndex,
        total_batches: linkedTotalBatches,
        batch_size: batch.length,
        match_ids: this._summarizeMatchIds(batch.map((mapping) => mapping.match_id)),
        hash_bypass: batchMeta.hashBypass === true,
        season_hash_key: batchMeta.seasonHashKey || null
      });
      let result;
      try {
        result = await this.repository.batchSaveOddsPortalMappings(batch, {
          pipelineStatus: 'RECON_LINKED',
          preserve_linked_status: true
        });
      } catch (error) {
        if (batchMeta.hashBypass === true && this._isSkippableHashBypassConflict(error)) {
          this.logger.warn('recon_batch_hash_bypass_conflict_skipped', {
            recon_run_id: metadata.reconRunId || null,
            season: metadata.season || null,
            league: metadata.league || null,
            batch_type: 'linked',
            batch_index: batchIndex,
            total_batches: linkedTotalBatches,
            match_ids: this._summarizeMatchIds(batch.map((mapping) => mapping.match_id)),
            season_hash_key: batchMeta.seasonHashKey || null,
            error: error.message,
            error_code: error.code || null,
            conflict: error.details || null
          });
          continue;
        }

        this.logger.error('recon_batch_conflict', {
          recon_run_id: metadata.reconRunId || null,
          season: metadata.season || null,
          league: metadata.league || null,
          batch_type: 'linked',
          batch_index: batchIndex,
          total_batches: linkedTotalBatches,
          match_ids: this._summarizeMatchIds(batch.map((mapping) => mapping.match_id)),
          error: error.message,
          error_code: error.code || null,
          conflict: error.details || null
        });
        throw error;
      }
      this.logger.info('recon_batch_persist_complete', {
        recon_run_id: metadata.reconRunId || null,
        season: metadata.season || null,
        league: metadata.league || null,
        batch_type: 'linked',
        batch_index: batchIndex,
        total_batches: linkedTotalBatches,
        match_ids: this._summarizeMatchIds(batch.map((mapping) => mapping.match_id)),
        hash_bypass: batchMeta.hashBypass === true,
        season_hash_key: batchMeta.seasonHashKey || null,
        inserted: result?.inserted || 0,
        updated: result?.updated || 0
      });
      linkedApplied += Number(result?.applied ?? result?.inserted ?? 0);
    }

    for (let index = 0; index < orderedMismatchIds.length; index += batchSize) {
      const batchRecords = orderedMismatchRecords.slice(index, index + batchSize);
      const batch = batchRecords.map((record) => String(record.match_id));
      const batchIndex = Math.floor(index / batchSize) + 1;
      this.logger.info('recon_batch_persist_start', {
        recon_run_id: metadata.reconRunId || null,
        season: metadata.season || null,
        league: metadata.league || null,
        sourceSeason: metadata.sourceSeason || null,
        sourceUrl: metadata.sourceUrl || null,
        batch_type: 'mismatch',
        batch_index: batchIndex,
        total_batches: mismatchTotalBatches,
        batch_size: batch.length,
        match_ids: this._summarizeMatchIds(batch)
      });
      if (typeof this.repository.batchSaveMismatchEvidence === 'function') {
        const evidenceBatch = batchRecords
          .map((record) => record.evidence)
          .filter(Boolean);
        if (evidenceBatch.length > 0) {
          await this.repository.batchSaveMismatchEvidence(evidenceBatch);
        }
      }
      const result = await this.repository.batchUpdateMatchPipelineStatus(batch, 'RECON_MISMATCH', {
        season: metadata.season || null,
        expectedCurrentStatus: metadata.allowMismatchRetry === true
          ? ['harvested', 'RECON_MISMATCH']
          : 'harvested'
      });
      this.logger.info('recon_batch_persist_complete', {
        recon_run_id: metadata.reconRunId || null,
        season: metadata.season || null,
        league: metadata.league || null,
        batch_type: 'mismatch',
        batch_index: batchIndex,
        total_batches: mismatchTotalBatches,
        match_ids: this._summarizeMatchIds(batch),
        updated: result?.updated || 0
      });
      mismatchUpdated += Number(result?.updated || 0);
    }

    return {
      linkedApplied,
      mismatchUpdated
    };
  },

  async _reconcilePendingMatch(l1Match, candidates, target, confidenceThreshold, seasonMirror = null) {
    let candidateMatch = this._findBestCandidate(l1Match, candidates, seasonMirror);
    if (
      (!candidateMatch || candidateMatch.confidence < confidenceThreshold)
      && String(l1Match?.pipeline_status || '').trim().toUpperCase() === 'RECON_MISMATCH'
    ) {
      const localDictionaryCandidate = this._buildLocalDictionaryCandidate(l1Match, target);
      if (localDictionaryCandidate) {
        const localDictionaryMatch = this._findBestCandidate(l1Match, [localDictionaryCandidate], null);
        if (localDictionaryMatch && (!candidateMatch || localDictionaryMatch.confidence > candidateMatch.confidence)) {
          candidateMatch = localDictionaryMatch;
        }
      }
    }

    if (!candidateMatch || candidateMatch.confidence < confidenceThreshold) {
      return {
        status: 'mismatch',
        matchId: l1Match.match_id,
        evidence: this._buildMismatchEvidence(l1Match, candidateMatch, target)
      };
    }

    const normalizedCandidateMatch = this._normalizeCandidateMatchForLink(candidateMatch, l1Match, target);
    if (!normalizedCandidateMatch) {
      return {
        status: 'mismatch',
        matchId: l1Match.match_id,
        evidence: this._buildMismatchEvidence(l1Match, candidateMatch, target)
      };
    }

    return {
      status: 'linked',
      mapping: {
        match_id: l1Match.match_id,
        oddsportal_hash: normalizedCandidateMatch.candidate.hash,
        full_url: normalizedCandidateMatch.candidate.url,
        season: target.dbSeason,
        league_name: target.league.name,
        home_team: l1Match.home_team,
        away_team: l1Match.away_team,
        is_reversed: Boolean(normalizedCandidateMatch.isReversed),
        match_confidence: normalizedCandidateMatch.confidence,
        mapping_method: this._normalizeMappingMethod(normalizedCandidateMatch, 'recon_matrix'),
        originPipelineStatus: String(l1Match.pipeline_status || '').toLowerCase(),
        status: 'pending'
      }
    };
  },

  _buildMismatchEvidence(l1Match, candidateMatch, target) {
    const candidate = candidateMatch?.candidate || null;
    const candidateName = candidate?.homeTeam && candidate?.awayTeam
      ? `${candidate.homeTeam} vs ${candidate.awayTeam}`
      : null;

    return {
      match_id: String(l1Match.match_id),
      season: target.dbSeason,
      league_name: target.league.name,
      home_team: l1Match.home_team,
      away_team: l1Match.away_team,
      full_url: candidate?.url || `evidence://recon/${encodeURIComponent(String(l1Match.match_id))}`,
      candidate_name: candidateName,
      match_confidence: Number(candidateMatch?.confidence || 0),
      mapping_method: this._normalizeMappingMethod(candidateMatch, 'unknown'),
      is_reversed: Boolean(candidateMatch?.isReversed)
    };
  },

  _normalizeMappingMethod(candidateMatch, fallback = 'recon_matrix') {
    const rawMethod = String(candidateMatch?.method || '').trim();
    if (ALLOWED_MAPPING_METHODS.has(rawMethod)) {
      return rawMethod;
    }

    const candidateSource = String(candidateMatch?.candidate?.source || '').trim().toLowerCase();
    if (
      rawMethod === 'season_mirror'
      || rawMethod === 'set_closure'
      || candidateSource.startsWith('pure_protocol_')
      || candidateSource.includes('protocol')
    ) {
      return 'protocol_extract';
    }

    return fallback;
  },

  _buildSeasonMirror(candidates) {
    return this.mirrorManager.buildSeasonMirror(candidates);
  },

  _findBestCandidate(l1Match, candidates, seasonMirror = null) {
    return this.matchEvaluator.findBestCandidate(l1Match, candidates, seasonMirror);
  },

  _buildRouteProbeSample(pendingMatches = []) {
    const orderedPending = [...(Array.isArray(pendingMatches) ? pendingMatches : [])]
      .sort((left, right) => String(left?.match_id || '').localeCompare(String(right?.match_id || '')));
    const eligiblePending = typeof this.taskPlanner?.filterPlaceholderFixtures === 'function'
      ? this.taskPlanner.filterPlaceholderFixtures(orderedPending)
      : orderedPending;
    const sampleSize = Math.max(1, Number(this.taskPlanner?.sampleSize || eligiblePending.length || 1));

    return eligiblePending.slice(0, Math.min(sampleSize, eligiblePending.length));
  },

  _scoreCandidatePoolSample(pendingMatches = [], candidates = [], confidenceThreshold = this.confidenceThreshold, seasonMirror = null) {
    const sample = this._buildRouteProbeSample(pendingMatches);
    if (sample.length === 0 || !Array.isArray(candidates) || candidates.length === 0) {
      return 0;
    }

    return sample.reduce((count, l1Match) => {
      const matched = this._findBestCandidate(l1Match, candidates, seasonMirror);
      return matched && matched.confidence >= confidenceThreshold ? count + 1 : count;
    }, 0);
  },

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

  _buildEmptyRouteSource(routeKind, target, sourceState = 'SOURCE_EMPTY') {
    return {
      routeKind,
      source: {
        season: target?.dbSeason || null,
        url: ''
      },
      extractResult: {
        matches: [],
        pagesScanned: 0,
        totalCandidates: 0,
        sourceState
      },
      candidates: [],
      seasonMirror: new Map(),
      sampleLinked: 0
    };
  },

  _combineCandidateRouteSources(routeSources = [], target, pendingMatches, confidenceThreshold) {
    const successfulRoutes = (Array.isArray(routeSources) ? routeSources : [])
      .filter((route) => route && typeof route === 'object');
    if (successfulRoutes.length === 0) {
      return this._buildEmptyRouteSource('results', target, 'SOURCE_EMPTY');
    }

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

  async _probeCandidateRoutes(target, pendingMatches, confidenceThreshold, navigator = null) {
    const sharedNavigator = navigator || this.navigator || null;
    const runInParallel = this._canRunParallelRouteProbes();
    const routeProbes = [
      () => this._probeResultsCandidateSource(target, pendingMatches, confidenceThreshold, sharedNavigator),
      () => this._probeFixturesCandidateSource(target, pendingMatches, confidenceThreshold, sharedNavigator, {
        useDedicatedNavigator: runInParallel
      }),
      () => this._probeSearchCandidateSource(target, pendingMatches, confidenceThreshold, sharedNavigator, {
        useDedicatedNavigator: runInParallel
      })
    ];
    const settled = [];

    if (runInParallel) {
      const parallelResults = await Promise.allSettled(routeProbes.map((probe) => probe()));
      settled.push(...parallelResults);
    } else {
      for (const probe of routeProbes) {
        try {
          settled.push({
            status: 'fulfilled',
            value: await probe()
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

    return this._combineCandidateRouteSources(
      successfulRoutes,
      target,
      pendingMatches,
      confidenceThreshold
    );
  },

  async _probeResultsCandidateSource(target, pendingMatches, confidenceThreshold, navigator = null) {
    const selectedSource = await this.taskPlanner.selectCandidateSource(
      target,
      pendingMatches,
      confidenceThreshold,
      { navigator: navigator || this.navigator || null }
    );

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

    return this._executeRouteProbeWithNavigator(
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
  },

  async _probeSearchCandidateSource(target, pendingMatches, confidenceThreshold, navigator = null, options = {}) {
    if (!Array.isArray(pendingMatches) || pendingMatches.length === 0) {
      return null;
    }

    return this._executeRouteProbeWithNavigator(
      target,
      navigator,
      {
        routeKind: 'search',
        launchBrowser: true,
        useDedicatedNavigator: options.useDedicatedNavigator === true
      },
      async (activeNavigator) => {
        const searchResult = await this._collectSearchCandidatesForPendingMatches(target, pendingMatches, activeNavigator);
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
      timeoutMs: this.archiveTimeoutMs,
      preferCurrentSeasonSource: true,
      circuitBreakerKey,
      forceDomOnly: routeKind === 'fixtures'
    };

    if (typeof navigator.fetchFullSeasonArchive === 'function') {
      return navigator.fetchFullSeasonArchive(url, extractOptions);
    }

    if (typeof navigator.protocolArchiveExtract === 'function') {
      return navigator.protocolArchiveExtract(url, extractOptions);
    }

    return { matches: [], pagesScanned: 0, totalCandidates: 0, sourceState: 'ROUTE_SKIPPED_NO_ARCHIVE_HANDLER' };
  },

  async _collectSearchCandidatesForPendingMatches(target, pendingMatches, navigator) {
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
      const searchCandidates = await this._collectSearchCandidatesFromUrl(searchUrl, navigator, target);
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

  async _collectSearchCandidatesFromUrl(searchUrl, navigator, _target) {
    await navigator.navigate(searchUrl, { waitUntil: 'domcontentloaded' });
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
  },

  async _primeLeagueDictionary(target) {
    if (!this.matchEvaluator || typeof this.matchEvaluator.setLeagueDictionaryEntries !== 'function') {
      return [];
    }

    const leagueId = Number(target?.leagueId || target?.league?.id || 0);
    if (!Number.isInteger(leagueId) || leagueId <= 0) {
      this.matchEvaluator.clearLeagueDictionary?.();
      return [];
    }

    if (!this.repository || typeof this.repository.getLeagueDictionaryEntries !== 'function') {
      this.matchEvaluator.clearLeagueDictionary?.();
      return [];
    }

    const entries = await this.repository.getLeagueDictionaryEntries(leagueId, {
      season: target?.dbSeason || null
    });

    this.matchEvaluator.setLeagueDictionaryEntries(leagueId, entries);
    return entries;
  },

  _shouldUseLocalDictionaryOnly(target, pendingMatches = []) {
    return false;
  },

  _canUseLocalDictionaryFallback(target, pendingMatches = []) {
    const entries = Array.isArray(target?.leagueDictionaryEntries) ? target.leagueDictionaryEntries : [];
    if (entries.length === 0) {
      return false;
    }

    return pendingMatches.some((match) => Boolean(this._buildLocalDictionaryCandidate(match, target)));
  },

  _buildLocalDictionarySelectedSource(target, pendingMatches = [], sourceState = 'LOCAL_DICTIONARY_FALLBACK') {
    return {
      source: {
        season: target?.dbSeason || null,
        url: this._buildLocalDictionarySourceUrl(target)
      },
      extractResult: {
        matches: [],
        pagesScanned: 0,
        totalCandidates: pendingMatches.length,
        sourceState
      },
      candidates: [],
      seasonMirror: new Map(),
      sampleLinked: 0,
      localFallbackCandidateCount: pendingMatches.length
    };
  },

  _buildLocalDictionarySourceUrl(target) {
    const leagueId = Number(target?.leagueId || target?.league?.id || 0);
    const season = encodeURIComponent(String(target?.dbSeason || 'unknown'));
    return `dictionary://recon/${leagueId || 0}/${season}`;
  },

  _buildLocalDictionaryIndex(target) {
    if (target?.localDictionaryIndex instanceof Map) {
      return target.localDictionaryIndex;
    }

    const index = new Map();
    const normalizeTeamName = (teamName) => {
      if (this.matchEvaluator && typeof this.matchEvaluator.normalizeTeamName === 'function') {
        return this.matchEvaluator.normalizeTeamName(teamName);
      }

      return String(teamName || '').toLowerCase().trim();
    };

    for (const entry of Array.isArray(target?.leagueDictionaryEntries) ? target.leagueDictionaryEntries : []) {
      const key = normalizeTeamName(entry?.local_team_name);
      if (!key || index.has(key)) {
        continue;
      }

      index.set(key, entry);
    }

    target.localDictionaryIndex = index;
    return index;
  },

  _buildLocalDictionaryCandidate(l1Match, target) {
    const index = this._buildLocalDictionaryIndex(target);
    if (!(index instanceof Map) || index.size === 0) {
      return null;
    }

    const normalizeTeamName = (teamName) => {
      if (this.matchEvaluator && typeof this.matchEvaluator.normalizeTeamName === 'function') {
        return this.matchEvaluator.normalizeTeamName(teamName);
      }

      return String(teamName || '').toLowerCase().trim();
    };

    const resolveRemoteName = (teamName) => {
      const normalizedTeamName = normalizeTeamName(teamName);
      const directEntry = index.get(normalizedTeamName) || null;
      if (directEntry?.remote_name) {
        return String(directEntry.remote_name);
      }

      const slashSegments = String(teamName || '')
        .split(/\s*\/\s*/)
        .map((segment) => String(segment || '').trim())
        .filter(Boolean);
      if (slashSegments.length > 1) {
        const resolvedSlashSegments = [];
        for (const segment of slashSegments) {
          const entry = index.get(normalizeTeamName(segment)) || null;
          if (!entry?.remote_name) {
            return null;
          }
          resolvedSlashSegments.push(String(entry.remote_name));
        }

        return resolvedSlashSegments.join('/');
      }

      const tokens = normalizedTeamName.split(' ').filter(Boolean);
      if (tokens.length >= 2) {
        for (let splitIndex = 1; splitIndex < tokens.length; splitIndex++) {
          const leftKey = tokens.slice(0, splitIndex).join(' ');
          const rightKey = tokens.slice(splitIndex).join(' ');
          const leftEntry = index.get(leftKey) || null;
          const rightEntry = index.get(rightKey) || null;

          if (leftEntry?.remote_name && rightEntry?.remote_name) {
            return `${leftEntry.remote_name}/${rightEntry.remote_name}`;
          }
        }
      }

      if (this.matchEvaluator?.isPlaceholderTeamName?.(teamName)) {
        return String(teamName || '')
          .trim()
          .replace(/\s+/g, ' ');
      }

      return null;
    };

    const homeRemoteName = resolveRemoteName(l1Match?.home_team || '');
    const awayRemoteName = resolveRemoteName(l1Match?.away_team || '');

    if (!homeRemoteName || !awayRemoteName) {
      return null;
    }

    const hashSeed = [
      target?.leagueId || target?.league?.id || 0,
      target?.dbSeason || '',
      l1Match?.match_id || '',
      homeRemoteName,
      awayRemoteName
    ].join('::');
    const hash = `~${crypto.createHash('sha1').update(hashSeed).digest('hex').slice(0, 7)}`;
    const url = [
      this._buildLocalDictionarySourceUrl(target),
      encodeURIComponent(String(homeRemoteName)),
      encodeURIComponent(String(awayRemoteName)),
      encodeURIComponent(String(l1Match?.match_id || ''))
    ].join('/');

    return {
      hash,
      url,
      homeTeam: String(homeRemoteName),
      awayTeam: String(awayRemoteName),
      matchDate: l1Match?.match_date || null,
      source: 'local_dictionary'
    };
  },

  async _runLocalDictionaryOnlyTarget(target, pendingMatches, options = {}) {
    const {
      batchSize = this.reconBatchSize,
      confidenceThreshold = this.confidenceThreshold,
      sourceSeason = target?.dbSeason || null,
      sourceUrl = this._buildLocalDictionarySourceUrl(target)
    } = options;

    const outcomes = [];
    for (const l1Match of pendingMatches) {
      outcomes.push(await this._reconcilePendingMatch(l1Match, [], target, confidenceThreshold, null));
    }

    const mappings = [];
    const mismatches = [];

    for (const outcome of outcomes) {
      if (outcome?.status === 'linked' && outcome.mapping) {
        mappings.push(outcome.mapping);
      } else if (outcome?.status === 'mismatch' && outcome.matchId) {
        mismatches.push({
          match_id: String(outcome.matchId),
          evidence: outcome.evidence || null
        });
      }
    }

    const persistResult = await this._persistReconBatches(
      mappings,
      mismatches,
      Math.max(1, Number(batchSize)),
      {
        reconRunId: this._createReconRunId(target),
        season: target.dbSeason,
        league: target.league.name,
        sourceSeason,
        sourceUrl,
        allowMismatchRetry: target?.reconPolicy?.allowMismatchRetry === true
      }
    );

    return {
      pendingTotal: pendingMatches.length,
      linked: Number(persistResult?.linkedApplied || 0),
      mismatched: Number(persistResult?.mismatchUpdated || 0),
      sourceSeason,
      sourceUrl,
      candidateCount: pendingMatches.length,
      effectiveConfidenceThreshold: confidenceThreshold
    };
  },

  _buildSeasonHashKey(mapping = {}) {
    const season = String(mapping?.season || '').trim();
    const hash = String(mapping?.oddsportal_hash || '').trim();
    if (!season || !hash) {
      return '';
    }

    return `${season}::${hash}`;
  },

  _shouldCanonicalizeCandidateUrl(url) {
    const rawUrl = String(url || '').trim();
    return !rawUrl || /\/football\/h2h\//iu.test(rawUrl) || /\/match\/[^/]+\/?$/iu.test(rawUrl);
  },

  _normalizeCandidateMatchForLink(candidateMatch, l1Match, target = {}) {
    const candidate = candidateMatch?.candidate || null;
    if (!candidate) {
      return null;
    }

    const rawUrl = String(candidate.url || '').trim();
    if (!this._shouldCanonicalizeCandidateUrl(rawUrl)) {
      return candidateMatch;
    }

    const extractor = this.matchExtractor;
    if (!extractor || typeof extractor.normalizeMatchObject !== 'function') {
      return null;
    }

    const normalizationCandidates = this._splitSourceUrls(
      candidate?.sourceUrl
      || candidate?.source_url
      || target?.reconSourceUrl
      || target?.resultsUrl
      || ''
    );
    const candidateSourceUrls = normalizationCandidates.length > 0
      ? normalizationCandidates
      : [this._resolveTrustedOddsPortalBaseUrl()];
    const fallbackSlug = this._buildFallbackEventSlug(l1Match?.home_team, l1Match?.away_team);

    for (const sourceUrl of candidateSourceUrls) {
      const normalized = extractor.normalizeMatchObject.call({
        ...extractor,
        baseUrl: this._resolveTrustedOddsPortalBaseUrl(),
        sourceUrl,
        resultsUrl: sourceUrl,
        leagueUrl: sourceUrl,
        extractMaxDepth: 5
      }, {
        match_id: l1Match?.match_id || '',
        matchDate: candidate.matchDate || candidate.match_date || l1Match?.match_date || null,
        match_date: candidate.matchDate || candidate.match_date || l1Match?.match_date || null,
        hash: candidate.hash,
        eventId: candidate.hash,
        encodeEventId: candidate.hash,
        homeTeam: candidate.homeTeam || l1Match?.home_team || '',
        awayTeam: candidate.awayTeam || l1Match?.away_team || '',
        'home-name': l1Match?.home_team || candidate.homeTeam || '',
        'away-name': l1Match?.away_team || candidate.awayTeam || '',
        league_id: Number(target?.league?.id || 0) || undefined,
        countrySlug: target?.league?.country || '',
        leagueSlug: target?.league?.slug || '',
        slug: fallbackSlug,
        url: rawUrl
      }, 'recon_matrix_preflight');

      if (normalized?.url && this._isCanonicalEventUrl(normalized.url, candidate.hash)) {
        return {
          ...candidateMatch,
          candidate: {
            ...candidate,
            ...normalized,
            url: normalized.url,
            hash: normalized.hash || candidate.hash,
            homeTeam: normalized.homeTeam || candidate.homeTeam,
            awayTeam: normalized.awayTeam || candidate.awayTeam,
            matchDate: normalized.matchDate || candidate.matchDate || candidate.match_date || null
          }
        };
      }
    }

    this.logger.warn('rejected_due_to_h2h_url', {
      match_id: String(l1Match?.match_id || ''),
      season: String(target?.dbSeason || ''),
      oddsportal_hash: String(candidate?.hash || ''),
      full_url: rawUrl,
      candidate_source_url: String(target?.reconSourceUrl || target?.resultsUrl || ''),
      reason: 'preflight_canonical_url_missing'
    });
    return null;
  },

  _escapeRegExp(value) {
    return String(value || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  },

  _buildFallbackEventSlug(homeTeam, awayTeam) {
    const slugify = (value) => String(value || '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '');

    const homeSlug = slugify(homeTeam);
    const awaySlug = slugify(awayTeam);
    if (!homeSlug || !awaySlug) {
      return '';
    }

    return `${homeSlug}-${awaySlug}`;
  },

  _splitSourceUrls(sourceUrlValue) {
    const raw = String(sourceUrlValue || '').trim();
    if (!raw) {
      return [];
    }

    return raw
      .split('|')
      .map((item) => String(item || '').trim())
      .filter(Boolean);
  },

  _resolveTrustedOddsPortalBaseUrl() {
    const configuredBaseUrl = String(this.baseUrl || '').trim();
    return /^https:\/\/www\.oddsportal\.com\/?/iu.test(configuredBaseUrl)
      ? configuredBaseUrl.replace(/\/+$/u, '')
      : 'https://www.oddsportal.com';
  },

  _isCanonicalEventUrl(url, expectedHash = '') {
    const rawUrl = String(url || '').trim();
    const normalizedHash = String(expectedHash || '').trim();
    if (!rawUrl || /\/football\/h2h\//iu.test(rawUrl)) {
      return false;
    }

    try {
      const parsed = new URL(rawUrl, this._resolveTrustedOddsPortalBaseUrl());
      const pathname = String(parsed.pathname || '').replace(/\/+$/u, '');
      const lastSegment = pathname.split('/').filter(Boolean).pop() || '';
      if (!lastSegment) {
        return false;
      }

      if (normalizedHash) {
        return new RegExp(`-${this._escapeRegExp(normalizedHash)}$`, 'u').test(lastSegment);
      }

      return /-[A-Za-z0-9]{8}$/u.test(lastSegment);
    } catch {
      return false;
    }
  },

  _normalizeH2HMappingUrl(mapping = {}, metadata = {}) {
    const rawUrl = String(mapping?.full_url || '').trim();
    if (!/\/football\/h2h\//iu.test(rawUrl)) {
      return mapping;
    }

    const extractor = this.matchExtractor;
    if (!extractor || typeof extractor.normalizeMatchObject !== 'function') {
      this.logger.warn('rejected_due_to_h2h_url', {
        match_id: String(mapping?.match_id || ''),
        season: String(mapping?.season || ''),
        oddsportal_hash: String(mapping?.oddsportal_hash || ''),
        full_url: rawUrl,
        reason: 'match_extractor_missing'
      });
      return null;
    }

    const normalizationCandidates = this._splitSourceUrls(
      mapping?.candidate_source_url
      || mapping?.sourceUrl
      || mapping?.source_url
      || metadata?.sourceUrl
      || ''
    );
    const candidateSourceUrls = normalizationCandidates.length > 0
      ? normalizationCandidates
      : [this._resolveTrustedOddsPortalBaseUrl()];
    const fallbackSlug = this._buildFallbackEventSlug(mapping.home_team, mapping.away_team);

    for (const sourceUrl of candidateSourceUrls) {
      const normalized = extractor.normalizeMatchObject.call({
        ...extractor,
        baseUrl: this._resolveTrustedOddsPortalBaseUrl(),
        sourceUrl,
        resultsUrl: sourceUrl,
        leagueUrl: sourceUrl,
        extractMaxDepth: 5
      }, {
        league_id: Number(mapping?.league_id || metadata?.leagueId || 0) || undefined,
        countrySlug: metadata?.countrySlug || '',
        leagueSlug: metadata?.leagueSlug || '',
        homeTeam: mapping.home_team,
        awayTeam: mapping.away_team,
        hash: mapping.oddsportal_hash,
        url: rawUrl,
        slug: fallbackSlug
      }, 'recon_matrix_quality_gate');

      if (normalized?.url && this._isCanonicalEventUrl(normalized.url, mapping.oddsportal_hash)) {
        return {
          ...mapping,
          full_url: normalized.url
        };
      }
    }

    this.logger.warn('rejected_due_to_h2h_url', {
      match_id: String(mapping?.match_id || ''),
      season: String(mapping?.season || ''),
      oddsportal_hash: String(mapping?.oddsportal_hash || ''),
      full_url: rawUrl,
      candidate_source_url: String(metadata?.sourceUrl || mapping?.candidate_source_url || ''),
      reason: 'canonical_hash_url_missing'
    });
    return null;
  },

  _buildLinkedPersistBatches(mappings = [], batchSize = 25, metadata = {}) {
    const orderedMappings = [...(Array.isArray(mappings) ? mappings : [])]
      .map((mapping) => this._normalizeH2HMappingUrl(mapping, metadata))
      .filter(Boolean)
      .sort((a, b) => String(a.match_id).localeCompare(String(b.match_id)));
    const hashCounts = new Map();

    for (const mapping of orderedMappings) {
      const key = this._buildSeasonHashKey(mapping);
      if (!key) {
        continue;
      }

      hashCounts.set(key, Number(hashCounts.get(key) || 0) + 1);
    }

    const batches = [];
    let buffered = [];
    const flushBuffered = () => {
      if (buffered.length === 0) {
        return;
      }

      batches.push({
        mappings: buffered,
        hashBypass: false,
        seasonHashKey: null
      });
      buffered = [];
    };

    for (const mapping of orderedMappings) {
      const key = this._buildSeasonHashKey(mapping);
      if (key && Number(hashCounts.get(key) || 0) > 1) {
        flushBuffered();
        batches.push({
          mappings: [mapping],
          hashBypass: true,
          seasonHashKey: key
        });
        continue;
      }

      buffered.push(mapping);
      if (buffered.length >= Math.max(1, Number(batchSize))) {
        flushBuffered();
      }
    }

    flushBuffered();
    return batches;
  },

  _isSkippableHashBypassConflict(error) {
    const code = String(error?.code || '').trim().toUpperCase();
    return code === 'HASH_CONFLICT' || code === 'UNIQUE_VIOLATION';
  },

  _dedupeMappingsBySeasonHash(mappings = []) {
    const groupedByHash = new Map();
    const droppedMatchIds = [];
    const bypassedMatchIds = [];
    const bypassedHashKeys = [];

    const comparePriority = (left, right) => {
      const leftConfidence = Number(left?.match_confidence || 0);
      const rightConfidence = Number(right?.match_confidence || 0);
      if (leftConfidence !== rightConfidence) {
        return leftConfidence - rightConfidence;
      }

      return String(left?.match_id || '').localeCompare(String(right?.match_id || ''));
    };

    for (const mapping of Array.isArray(mappings) ? mappings : []) {
      const key = this._buildSeasonHashKey(mapping);
      const matchId = String(mapping?.match_id || '').trim();
      if (!key || !matchId) {
        continue;
      }

      if (!groupedByHash.has(key)) {
        groupedByHash.set(key, []);
      }

      groupedByHash.get(key).push(mapping);
    }

    const selectedMappings = [];

    for (const [key, group] of groupedByHash.entries()) {
      const selectedByMatchId = new Map();

      for (const mapping of group) {
        const matchId = String(mapping?.match_id || '').trim();
        if (!matchId) {
          continue;
        }

        if (!selectedByMatchId.has(matchId)) {
          selectedByMatchId.set(matchId, mapping);
          continue;
        }

        const current = selectedByMatchId.get(matchId);
        if (comparePriority(mapping, current) > 0) {
          droppedMatchIds.push(String(current.match_id));
          selectedByMatchId.set(matchId, mapping);
        } else {
          droppedMatchIds.push(matchId);
        }
      }

      const uniqueMatchMappings = [...selectedByMatchId.values()];
      if (uniqueMatchMappings.length === 0) {
        continue;
      }

      if (uniqueMatchMappings.length === 1) {
        selectedMappings.push(uniqueMatchMappings[0]);
        continue;
      }

      const hasPendingBypass = uniqueMatchMappings.some((mapping) => (
        String(mapping?.status || '').trim().toLowerCase() === 'pending'
      ));

      if (hasPendingBypass) {
        selectedMappings.push(...uniqueMatchMappings);
        bypassedMatchIds.push(...uniqueMatchMappings.map((mapping) => String(mapping.match_id)));
        bypassedHashKeys.push(key);
        continue;
      }

      let winner = uniqueMatchMappings[0];
      for (const mapping of uniqueMatchMappings.slice(1)) {
        const originStatus = String(mapping.originPipelineStatus || '').toLowerCase();
        const currentStatus = String(winner?.originPipelineStatus || '').toLowerCase();
        const preferNewBecauseHarvested = currentStatus === 'harvested' && originStatus !== 'harvested';
        const preferCurrentBecauseHarvested = currentStatus !== 'harvested' && originStatus === 'harvested';

        if (preferNewBecauseHarvested) {
          droppedMatchIds.push(String(winner.match_id));
          winner = mapping;
          continue;
        }

        if (preferCurrentBecauseHarvested) {
          droppedMatchIds.push(String(mapping.match_id));
          continue;
        }

        if (comparePriority(mapping, winner) > 0) {
          droppedMatchIds.push(String(winner.match_id));
          winner = mapping;
        } else {
          droppedMatchIds.push(String(mapping.match_id));
        }
      }

      selectedMappings.push(winner);
    }

    return {
      mappings: selectedMappings,
      droppedMatchIds: [...new Set(droppedMatchIds)].sort((a, b) => a.localeCompare(b)),
      bypassedMatchIds: [...new Set(bypassedMatchIds)].sort((a, b) => a.localeCompare(b)),
      bypassedHashKeys: [...new Set(bypassedHashKeys)].sort((a, b) => a.localeCompare(b))
    };
  }
};

module.exports = { reconMatrixFlow };
