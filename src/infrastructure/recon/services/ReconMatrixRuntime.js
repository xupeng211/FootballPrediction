/* eslint-disable complexity */
'use strict';

const DEFAULT_LEAGUE_STARTUP_STAGGER_MS = 2000;

function createAdaptiveAggregateStats() {
  return {
    processedPending: 0,
    linked: 0,
    completedLeagues: 0
  };
}

function buildAdaptiveFeedbackMetadata(targetPendingMap, nextIndex, runningSize, aggregateStats, phase) {
  return {
    phase,
    queueRemaining: Math.max(0, targetPendingMap.length - nextIndex),
    activeLeagueWorkers: runningSize,
    aggregateStats
  };
}

function resolveOutcomePendingTotal(outcome, targetPendingMap, index) {
  const rawOutcomePendingTotal = outcome?.result?.pendingTotal
    ?? outcome?.pendingTotal
    ?? targetPendingMap[index]?.pendingMatches?.length
    ?? 0;

  return Math.max(0, Number(rawOutcomePendingTotal) || 0);
}

function buildAdaptiveFeedbackPayload(outcome, runningSize, proxySnapshot, successRateGuard) {
  return {
    phase: 'feedback',
    league: outcome?.target?.league?.name || null,
    season: outcome?.target?.dbSeason || null,
    proxyPort: outcome?.proxyPort || null,
    activeLeagueWorkers: runningSize,
    proxyAvailable: proxySnapshot?.available ?? null,
    proxyTotal: proxySnapshot?.total ?? null,
    successRate: successRateGuard.successRate !== null
      ? Number(successRateGuard.successRate.toFixed(4))
      : null,
    lowSuccessRateGuardActive: successRateGuard.active,
    lowSuccessRateCap: successRateGuard.active ? successRateGuard.cap : null
  };
}

const reconMatrixRuntime = {
  _shouldRetryLeagueWorkerError(error, attempt, maxAttempts) {
    return error?.code === 'RECON_SOURCE_INCOMPLETE'
      && attempt < maxAttempts;
  },

  async buildScanTargets(options = {}) {
    return this.taskPlanner.buildScanTargets({
      ...options,
      currentSeasonOnly: options.currentSeasonOnly ?? this.currentSeasonOnly
    });
  },

  _resolveRunReconMatrixOptions(options = {}) {
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
      allNonLinked = this.allNonLinked === true,
      resultsOnlyMode = options.resultsOnlyMode ?? this.matrixResultsOnlyMode === true,
      disableSearchRoute = options.disableSearchRoute ?? this.disableSearchRouteInMatrix ?? true,
      matrixModePruning = options.matrixModePruning ?? this.matrixModePruning ?? true,
      matrixModeShortCircuitRatio = Number(
        options.matrixModeShortCircuitRatio
        ?? this.matrixModeShortCircuitRatio
        ?? 0.5
      ),
      leagueTimeBudgetMs = Math.max(
        1,
        Number(options.leagueTimeBudgetMs ?? this.matrixLeagueTimeBudgetMs ?? this.archiveTimeoutMs ?? 45000)
      )
    } = options;

    return {
      season,
      concurrency,
      leagueConcurrency,
      leagueStartupStaggerMs,
      tier,
      leagueIds,
      batchSize,
      confidenceThreshold,
      limit,
      forceDomMode,
      forceJsonExtract,
      forcePureProtocol,
      mismatchRetryOnly,
      allNonLinked,
      resultsOnlyMode,
      disableSearchRoute,
      matrixModePruning,
      matrixModeShortCircuitRatio,
      leagueTimeBudgetMs
    };
  },

  async _refreshReconMatrixPendingSnapshot(targets, summary, options = {}) {
    const targetPendingMap = await this._loadReconPendingTargets(targets, options.limit, {
      confidenceThreshold: options.confidenceThreshold,
      mismatchRetryOnly: options.mismatchRetryOnly,
      allNonLinked: options.allNonLinked
    });
    summary.remainingPending = this._countPendingMatches(targetPendingMap);
    summary.availableProxies = this._resolveAvailableProxyCount();
    return targetPendingMap;
  },

  _mergeReconMatrixOutcomes(summary, leagueSummaryMap, outcomes = []) {
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
  },

  async _runReconMatrixPasses(targets, summary, leagueSummaryMap, options = {}, adaptiveConcurrencyManager) {
    let targetPendingMap = await this._refreshReconMatrixPendingSnapshot(targets, summary, options);

    while (Array.isArray(targetPendingMap) && targetPendingMap.length > 0) {
      summary.passes += 1;

      const outcomes = await this._runAdaptiveLeagueWorkers(targetPendingMap, {
        season: options.season,
        concurrency: options.concurrency,
        batchSize: options.batchSize,
        confidenceThreshold: options.confidenceThreshold,
        forceDomMode: options.forceDomMode,
        forceJsonExtract: options.forceJsonExtract,
        forcePureProtocol: options.forcePureProtocol,
        resultsOnlyMode: options.resultsOnlyMode,
        leagueStartupStaggerMs: options.leagueStartupStaggerMs,
        disableSearchRoute: options.disableSearchRoute,
        matrixModePruning: options.matrixModePruning,
        matrixModeShortCircuitRatio: options.matrixModeShortCircuitRatio,
        leagueTimeBudgetMs: options.leagueTimeBudgetMs,
        requestedLeagueConcurrency: options.normalizedLeagueConcurrency,
        adaptiveConcurrencyManager,
        passIndex: summary.passes
      });

      this._mergeReconMatrixOutcomes(summary, leagueSummaryMap, outcomes);
      targetPendingMap = await this._refreshReconMatrixPendingSnapshot(targets, summary, options);

      if (!(await this._handlePerpetualReconContinuation(summary, options.rawOptions, options.normalizedLeagueConcurrency))) {
        break;
      }
    }
  },

  async runReconMatrix(options = {}) {
    const runOptions = this._resolveRunReconMatrixOptions(options);
    const {
      season,
      tier,
      leagueIds,
      leagueConcurrency,
      concurrency
    } = runOptions;

    this._resetRouteDegradeRegistry();
    const targets = await this.buildScanTargets({ season, tier, leagueIds });
    const summary = this._buildReconMatrixSummary(options, season);
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
    await this._runReconMatrixPasses(targets, summary, leagueSummaryMap, {
      ...runOptions,
      concurrency,
      normalizedLeagueConcurrency,
      rawOptions: options
    }, adaptiveConcurrencyManager);

    summary.perLeague = [...leagueSummaryMap.values()];
    summary.scannedLeagues = summary.perLeague.length;
    return summary;
  },

  _applyAdaptiveLeagueFeedback(manager, requestedLeagueConcurrency, targetPendingMap, nextIndex, runningSize, aggregateStats, phase) {
    return this._applyProxyFeedbackToConcurrency(
      manager,
      requestedLeagueConcurrency,
      buildAdaptiveFeedbackMetadata(targetPendingMap, nextIndex, runningSize, aggregateStats, phase)
    );
  },

  _dispatchAdaptiveLeagueWorkers(targetPendingMap, running, nextIndex, options = {}, adaptiveConcurrencyManager) {
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

    return nextIndex;
  },

  async _awaitAdaptiveLeagueWorker(running) {
    const completed = await Promise.race(running.values());
    running.delete(completed.index);
    return completed;
  },

  _updateAdaptiveAggregateStats(aggregateStats, outcome, targetPendingMap, index) {
    aggregateStats.processedPending += resolveOutcomePendingTotal(outcome, targetPendingMap, index);
    aggregateStats.linked += Math.max(0, Number(outcome?.result?.linked || 0));
    aggregateStats.completedLeagues += 1;
  },

  _recordAdaptiveLeagueFeedback(manager, requestedLeagueConcurrency, outcome, targetPendingMap, nextIndex, runningSize, aggregateStats) {
    const proxySnapshot = this._applyAdaptiveLeagueFeedback(
      manager,
      requestedLeagueConcurrency,
      targetPendingMap,
      nextIndex,
      runningSize,
      aggregateStats,
      'feedback'
    );
    const successRateGuard = this._resolveLowSuccessRateGuardState(requestedLeagueConcurrency, aggregateStats);
    const payload = buildAdaptiveFeedbackPayload(outcome, runningSize, proxySnapshot, successRateGuard);

    if (outcome?.error) {
      manager.recordFailure(outcome.error, payload);
      return;
    }

    manager.recordSuccess(payload);
  },

  async _runAdaptiveLeagueWorkers(targetPendingMap, options = {}) {
    const outcomes = [];
    const running = new Map();
    const adaptiveConcurrencyManager = options.adaptiveConcurrencyManager || this._createDynamicConcurrencyManager();
    const requestedLeagueConcurrency = Math.max(1, Number(options.requestedLeagueConcurrency) || 1);
    const aggregateStats = createAdaptiveAggregateStats();
    let nextIndex = 0;

    this._applyAdaptiveLeagueFeedback(
      adaptiveConcurrencyManager,
      requestedLeagueConcurrency,
      targetPendingMap,
      nextIndex,
      0,
      aggregateStats,
      'initial'
    );

    while (nextIndex < targetPendingMap.length || running.size > 0) {
      this._applyAdaptiveLeagueFeedback(
        adaptiveConcurrencyManager,
        requestedLeagueConcurrency,
        targetPendingMap,
        nextIndex,
        running.size,
        aggregateStats,
        'dispatch'
      );
      nextIndex = this._dispatchAdaptiveLeagueWorkers(
        targetPendingMap,
        running,
        nextIndex,
        options,
        adaptiveConcurrencyManager
      );

      if (running.size === 0) {
        continue;
      }

      const completed = await this._awaitAdaptiveLeagueWorker(running);
      outcomes[completed.index] = completed.outcome;
      this._updateAdaptiveAggregateStats(
        aggregateStats,
        completed.outcome,
        targetPendingMap,
        completed.index
      );
      this._recordAdaptiveLeagueFeedback(
        adaptiveConcurrencyManager,
        requestedLeagueConcurrency,
        completed.outcome,
        targetPendingMap,
        nextIndex,
        running.size,
        aggregateStats
      );
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
      resultsOnlyMode,
      leagueStartupStaggerMs,
      disableSearchRoute,
      matrixModePruning,
      matrixModeShortCircuitRatio,
      leagueTimeBudgetMs,
      allowedLeagueWorkers = 1,
      activeWorkersAtStart = 1
    } = options;
    const maxAttempts = forcePureProtocol === true ? 2 : 1;
    let lastError = null;
    let lastProxyPort = null;

    await this._delayLeagueWorkerStart(target, index, { leagueStartupStaggerMs });

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      let navigatorHandle = null;
      let proxyPort = null;

      try {
        navigatorHandle = await this._acquireTargetNavigator(target, {
          launchBrowser: forcePureProtocol !== true
        });
        proxyPort = Number(navigatorHandle?.proxyPort || navigatorHandle?.navigator?.proxy?.port || 0) || null;
        lastProxyPort = proxyPort;
        const proxySnapshot = this._getProxyPoolSnapshot();
        const leagueDeadlineAt = Number.isFinite(Number(leagueTimeBudgetMs)) && Number(leagueTimeBudgetMs) > 0
          ? Date.now() + Number(leagueTimeBudgetMs)
          : null;

        this.logger.info('recon_league_worker_start', {
          league: target.league.name,
          season: target.dbSeason,
          pendingTotal: pendingMatches.length,
          desiredLimit,
          proxyPort,
          attempt,
          maxAttempts,
          activeLeagueWorkers: activeWorkersAtStart,
          allowedLeagueWorkers,
          leagueStartupStaggerMs: Math.max(0, Number(leagueStartupStaggerMs) || 0),
          matchConcurrency: Math.max(1, Number(concurrency)),
          resultsOnlyMode,
          disableSearchRoute,
          matrixModePruning,
          matrixModeShortCircuitRatio,
          leagueTimeBudgetMs: Number(leagueTimeBudgetMs) || null,
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
          navigator: navigatorHandle?.navigator || null,
          resultsOnlyMode,
          disableSearchRoute,
          matrixModePruning,
          matrixModeShortCircuitRatio,
          leagueDeadlineAt
        });

        this.logger.info('recon_league_worker_complete', {
          league: target.league.name,
          season: target.dbSeason,
          proxyPort,
          attempt,
          maxAttempts,
          activeLeagueWorkers: activeWorkersAtStart,
          allowedLeagueWorkers,
          linked: result.linked,
          mismatched: result.mismatched,
          pendingTotal: result.pendingTotal
        });

        return { target, result, proxyPort };
      } catch (error) {
        lastError = error;
        if (this._shouldRetryLeagueWorkerError(error, attempt, maxAttempts)) {
          this.logger.warn('recon_league_worker_retry_scheduled', {
            league: target.league.name,
            season: target.dbSeason,
            proxyPort,
            attempt,
            nextAttempt: attempt + 1,
            reason: error.code,
            stage: error.stage || null,
            sourceUrl: error.sourceUrl || null,
            incompleteReasons: Array.isArray(error.incompleteReasons) ? error.incompleteReasons : []
          });
          continue;
        }

        this.logger.error('recon_matrix_target_failed', {
          league: target.league.name,
          season,
          proxyPort,
          attempt,
          maxAttempts,
          activeLeagueWorkers: activeWorkersAtStart,
          allowedLeagueWorkers,
          error: error.message,
          statusCode: Number(error?.statusCode || 0) || null
        });
        return { target, error, proxyPort, pendingTotal: pendingMatches.length };
      } finally {
        await this._releaseTargetNavigator(navigatorHandle);
      }
    }

    return {
      target,
      error: lastError || new Error('recon_league_worker_failed'),
      proxyPort: lastProxyPort,
      pendingTotal: pendingMatches.length
    };
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
  }
};

module.exports = { reconMatrixRuntime };
