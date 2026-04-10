'use strict';

const { DynamicConcurrencyManager } = require('./DynamicConcurrencyManager');

const DEFAULT_LEAGUE_STARTUP_STAGGER_MS = 2000;
const DEFAULT_LOW_SUCCESS_RATE_THRESHOLD = 0.5;
const DEFAULT_LOW_SUCCESS_RATE_LEAGUE_CAP = 3;
const DEFAULT_LOW_SUCCESS_RATE_MIN_COMPLETED_LEAGUES = 2;

function sleep(delayMs) {
  return new Promise((resolve) => {
    setTimeout(resolve, delayMs);
  });
}

const reconMatrixRuntimeSupport = {
  _buildReconMatrixSummary(options = {}, season = null) {
    return {
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
  },

  async _loadReconPendingTargets(targets, limit, options = {}) {
    return this.taskPlanner.prepareReconPendingTargets(targets, limit, {
      allowMismatchRetry: true,
      confidenceThreshold: options.confidenceThreshold,
      mismatchRetryOnly: options.mismatchRetryOnly,
      allNonLinked: options.allNonLinked
    });
  },

  async _handlePerpetualReconContinuation(summary, options = {}, normalizedLeagueConcurrency = 1) {
    const shouldContinue = typeof this.shouldContinuePerpetualRecon === 'function'
      ? this.shouldContinuePerpetualRecon(summary.remainingPending, {
        perpetualReconMode: options.perpetualReconMode,
        availableProxyCount: summary.availableProxies
      })
      : options.perpetualReconMode === true
        && summary.remainingPending > 0
        && summary.availableProxies > 0;

    if (!shouldContinue) {
      return false;
    }

    this.logger.warn('recon_matrix_perpetual_continue', {
      season: summary.season,
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

    return true;
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

  _resolveLowSuccessRateGuardState(requestedLeagueConcurrency, aggregateStats = null) {
    const normalizedConcurrency = Math.max(1, Number(requestedLeagueConcurrency) || 1);
    const processedPending = Math.max(0, Number(aggregateStats?.processedPending || 0));
    const linked = Math.max(0, Number(aggregateStats?.linked || 0));
    const completedLeagues = Math.max(0, Number(aggregateStats?.completedLeagues || 0));
    const thresholdRaw = Number(this.lowSuccessRateThreshold ?? DEFAULT_LOW_SUCCESS_RATE_THRESHOLD);
    const threshold = Number.isFinite(thresholdRaw)
      ? Math.min(1, Math.max(0, thresholdRaw))
      : DEFAULT_LOW_SUCCESS_RATE_THRESHOLD;
    const minCompletedLeagues = Math.max(
      1,
      Number(this.lowSuccessRateMinCompletedLeagues ?? DEFAULT_LOW_SUCCESS_RATE_MIN_COMPLETED_LEAGUES)
        || DEFAULT_LOW_SUCCESS_RATE_MIN_COMPLETED_LEAGUES
    );
    const cappedConcurrency = Math.max(
      1,
      Math.min(
        normalizedConcurrency,
        Number(this.lowSuccessRateLeagueCap ?? DEFAULT_LOW_SUCCESS_RATE_LEAGUE_CAP) || DEFAULT_LOW_SUCCESS_RATE_LEAGUE_CAP
      )
    );

    if (processedPending <= 0 || completedLeagues < minCompletedLeagues) {
      return {
        successRate: null,
        active: false,
        cap: normalizedConcurrency,
        threshold
      };
    }

    const successRate = linked / processedPending;
    const active = successRate < threshold;

    return {
      successRate,
      active,
      cap: active ? cappedConcurrency : normalizedConcurrency,
      threshold
    };
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
    const normalizedConcurrency = Math.max(1, Number(requestedLeagueConcurrency) || 1);
    const successRateGuard = this._resolveLowSuccessRateGuardState(
      normalizedConcurrency,
      metadata.aggregateStats
    );
    const proxyCap = snapshot
      ? Math.max(1, snapshot.available > 0 ? snapshot.available : 1)
      : normalizedConcurrency;
    const nextCeiling = Math.max(
      1,
      Math.min(
        normalizedConcurrency,
        proxyCap,
        successRateGuard.cap
      )
    );

    manager.setCeiling(nextCeiling, {
      proxyTotal: snapshot?.total ?? null,
      proxyHealthy: snapshot?.healthy ?? null,
      proxyCooling: snapshot?.cooling ?? null,
      proxyDead: snapshot?.dead ?? null,
      proxyAvailable: snapshot?.available ?? null,
      successRate: successRateGuard.successRate !== null
        ? Number(successRateGuard.successRate.toFixed(4))
        : null,
      lowSuccessRateGuardActive: successRateGuard.active,
      lowSuccessRateCap: successRateGuard.active ? successRateGuard.cap : null,
      lowSuccessRateThreshold: successRateGuard.threshold,
      ...metadata
    });

    return snapshot;
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
  }
};

module.exports = { reconMatrixRuntimeSupport };
