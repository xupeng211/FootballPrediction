/* eslint-disable complexity, max-lines */
/** @module infrastructure/recon/ReconEngineImpl */

'use strict';

const { L1ConfigManager } = require('../services/L1ConfigManager');
const { ReconMatchEvaluator } = require('./services/ReconMatchEvaluator');
const { reconMatchExtractor } = require('./services/ReconMatchExtractor');
const { ReconMirrorManager } = require('./services/ReconMirrorManager');
const { ReconTaskPlanner } = require('./services/ReconTaskPlanner');
const { RECON_CONFIG, getReconConfigSection, resolveRuntimeFeatureFlags } = require('./services/ReconServiceConfig');
const { reconMatrixFlow } = require('./services/ReconMatrixFlow');
const { reconScanModes } = require('./services/ReconScanModes');

class ReconEngine {
  constructor(options = {}) {
    const engineConfig = getReconConfigSection(['recon_runtime', 'engine'], {});
    const matchingConfig = RECON_CONFIG.matching || {};

    this._navigator = null;
    this.stitcher = options.stitcher;
    this.repository = options.repository;
    this.parser = options.parser;
    this.logger = options.logger || console;
    this.proxyRotator = options.proxyRotator;
    this.navigatorFactory = options.navigatorFactory || null;
    this.traceId = options.traceId || null;
    this.configManager = options.configManager || new L1ConfigManager({ logger: this.logger });
    this.baseUrl = options.baseUrl || options.config?.oddsportal?.base_url || 'https://www.oddsportal.com';
    this.engineConfig = engineConfig;
    this.reconBatchSize = Math.max(1, Number(options.reconBatchSize ?? engineConfig.recon_batch_size));
    this.defaultReconConcurrency = Math.max(1, Number(options.defaultReconConcurrency ?? engineConfig.default_concurrency));
    this.leagueParallelism = Math.max(
      1,
      Number(options.leagueParallelism ?? engineConfig.league_parallelism ?? this.defaultReconConcurrency)
    );
    this.confidenceThreshold = Number(options.confidenceThreshold ?? engineConfig.confidence_threshold ?? matchingConfig.confidence_threshold);
    this.minimumConfidenceThreshold = Number(
      options.minimumConfidenceThreshold
      ?? engineConfig.minimum_confidence_threshold
      ?? matchingConfig.confidence_threshold
      ?? 0.75
    );
    this.archiveMaxPages = Math.max(1, Number(options.archiveMaxPages ?? engineConfig.archive_max_pages));
    this.archiveTimeoutMs = Math.max(1, Number(options.archiveTimeoutMs ?? engineConfig.archive_timeout_ms));
    this.pageSettleWaitMs = Math.max(0, Number(options.pageSettleWaitMs ?? engineConfig.page_settle_wait_ms));
    this.domScrollStepPx = Math.max(1, Number(options.domScrollStepPx ?? engineConfig.dom_scroll_step_px));
    this.domScrollDelayMs = Math.max(0, Number(options.domScrollDelayMs ?? engineConfig.dom_scroll_delay_ms));
    this.progressLogEvery = Math.max(1, Number(options.progressLogEvery ?? engineConfig.progress_log_every));
    this.progressHighSuccessThreshold = Number(options.progressHighSuccessThreshold ?? engineConfig.progress_high_success_threshold ?? 1);
    this.progressSampleMultiplier = Math.max(1, Number(options.progressSampleMultiplier ?? engineConfig.progress_sample_multiplier ?? 1));
    this.dynamicConcurrencyInitial = Math.max(
      1,
      Number(options.dynamicConcurrencyInitial ?? engineConfig.adaptive_concurrency_initial ?? 5)
    );
    this.dynamicConcurrencySuccessWindow = Math.max(
      1,
      Number(options.dynamicConcurrencySuccessWindow ?? engineConfig.adaptive_concurrency_success_window ?? 3)
    );
    this.minimumReadyProxyCount = Math.max(
      1,
      Number(options.minimumReadyProxyCount ?? engineConfig.suspend_proxy_threshold ?? 2)
    );
    this.suspendPollIntervalMs = Math.max(
      250,
      Number(options.suspendPollIntervalMs ?? engineConfig.suspend_poll_interval_ms ?? 5000)
    );
    this.proxyHealthMinScore = Math.max(
      1,
      Number(options.proxyHealthMinScore ?? engineConfig.proxy_min_health_score ?? 60)
    );
    this.perpetualReconMode = options.perpetualReconMode === true
      || engineConfig.perpetual_recon_mode === true;
    this.perpetualReconPassDelayMs = Math.max(
      0,
      Number(options.perpetualReconPassDelayMs ?? engineConfig.perpetual_recon_pass_delay_ms ?? this.suspendPollIntervalMs)
    );
    this.featureFlags = options.featureFlags || resolveRuntimeFeatureFlags();
    this.reconStrategy = options.reconStrategy || this.featureFlags.reconStrategy;
    this.disableDomFallback = options.disableDomFallback ?? this.featureFlags.disableDomFallback;
    this.currentSeasonOnly = options.currentSeasonOnly === true;
    this.allNonLinked = options.allNonLinked === true;
    this.forceDomMode = options.forceDomMode === true;
    this.matchExtractor = options.matchExtractor || reconMatchExtractor;
    this.runtimeState = 'RUNNING';
    this.suspendReason = null;
    this.suspendedAt = null;
    this.lastSuspendHeartbeatAt = null;

    this.matchEvaluator = options.matchEvaluator || new ReconMatchEvaluator({ parser: this.parser, logger: this.logger });
    this.mirrorManager = options.mirrorManager || new ReconMirrorManager({ evaluator: this.matchEvaluator });
    if (typeof this.matchEvaluator.setMirrorManager === 'function') {
      this.matchEvaluator.setMirrorManager(this.mirrorManager);
    }
    this.taskPlanner = options.taskPlanner || new ReconTaskPlanner({
      navigator: this.navigator,
      repository: this.repository,
      logger: this.logger,
      configManager: this.configManager,
      baseUrl: this.baseUrl,
      matchEvaluator: this.matchEvaluator,
      mirrorManager: this.mirrorManager,
      minimumConfidenceThreshold: this.minimumConfidenceThreshold
    });

    this.navigator = options.navigator || this.taskPlanner?.navigator || null;
  }

  get navigator() {
    return this._navigator;
  }

  set navigator(value) {
    this._navigator = value || null;
    if (this.taskPlanner) {
      this.taskPlanner.navigator = this._navigator;
    }
  }

  _createReconRunId(target) {
    return [
      'recon',
      target?.league?.id || 'unknown',
      target?.dbSeason || 'unknown',
      Date.now()
    ].join('-');
  }

  _emitReconProgressSnapshot(target, progress) {
    const processed = progress.processed || 0;
    const total = progress.total || 0;
    const remaining = Math.max(0, total - processed);
    const elapsedMs = Math.max(1, Date.now() - progress.startedAt);
    const avgMsPerMatch = processed > 0 ? elapsedMs / processed : 0;
    const etaSeconds = remaining > 0 && avgMsPerMatch > 0
      ? Math.max(0, Math.round((remaining * avgMsPerMatch) / 1000))
      : 0;
    const memoryMb = Number((process.memoryUsage().rss / 1024 / 1024).toFixed(1));

    this.logger.info('recon_progress_snapshot', {
      league: target?.league?.name || null,
      season: target?.dbSeason || null,
      processed,
      total,
      linked: progress.linked || 0,
      mismatched: progress.mismatched || 0,
      etaSeconds,
      memoryMb,
      message: `[RECON-PROGRESS] 已对齐 ${processed}/${total} | Linked=${progress.linked || 0} Mismatched=${progress.mismatched || 0} | ETA=${etaSeconds}s | Memory=${memoryMb}MB`
    });
  }

  _shouldEmitReconProgressSnapshot(progress) {
    const processed = Number(progress?.processed || 0);
    const total = Number(progress?.total || 0);
    if (processed <= 0) {
      return false;
    }

    if (total > 0 && processed === total) {
      return true;
    }

    const linked = Number(progress?.linked || 0);
    const successRate = processed > 0 ? linked / processed : 0;
    const cadence = successRate >= this.progressHighSuccessThreshold
      ? this.progressLogEvery * this.progressSampleMultiplier
      : this.progressLogEvery;

    return processed % Math.max(1, cadence) === 0;
  }

  _summarizeMatchIds(matchIds = []) {
    const ordered = [...new Set(matchIds.map((id) => String(id)))]
      .sort((left, right) => left.localeCompare(right));

    return {
      count: ordered.length,
      preview: ordered.slice(0, 5),
      first: ordered[0] || null,
      last: ordered[ordered.length - 1] || null,
      truncated: ordered.length > 5
    };
  }

  getRuntimeState() {
    return {
      status: this.runtimeState,
      suspendReason: this.suspendReason,
      suspendedAt: this.suspendedAt,
      lastSuspendHeartbeatAt: this.lastSuspendHeartbeatAt
    };
  }

  _sleep(delayMs) {
    return new Promise((resolve) => {
      setTimeout(resolve, delayMs);
    });
  }

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
  }

  getAvailableProxyCount() {
    const snapshot = this._getProxyPoolSnapshot();
    if (snapshot) {
      return snapshot.available;
    }

    return this.proxyRotator ? 0 : 1;
  }

  shouldContinuePerpetualRecon(remainingPending = 0, options = {}) {
    const perpetualReconMode = options.perpetualReconMode === true
      || (options.perpetualReconMode !== false && this.perpetualReconMode === true);
    const normalizedPending = Math.max(0, Number(remainingPending) || 0);
    const availableProxyCount = Number.isFinite(Number(options.availableProxyCount))
      ? Number(options.availableProxyCount)
      : this.getAvailableProxyCount();

    return perpetualReconMode
      && normalizedPending > 0
      && availableProxyCount > 0;
  }

  async _runProxyPoolHeartbeat() {
    const provider = this.proxyRotator?.proxyProvider;
    if (provider && typeof provider.runHealthCheck === 'function') {
      try {
        await provider.runHealthCheck();
      } catch (error) {
        this.logger.warn('recon_engine_suspend_health_check_failed', {
          error: error.message
        });
      }
    }
  }

  _enterSuspendState(reason, details = {}) {
    if (this.runtimeState === 'SUSPEND' && this.suspendReason === reason) {
      return;
    }

    this.runtimeState = 'SUSPEND';
    this.suspendReason = reason;
    this.suspendedAt = new Date().toISOString();
    this.logger.warn('recon_engine_suspended', {
      reason,
      suspendedAt: this.suspendedAt,
      ...details
    });
  }

  _emitSuspendHeartbeat(reason, details = {}) {
    this.lastSuspendHeartbeatAt = new Date().toISOString();
    this.logger.info('recon_engine_suspend_heartbeat', {
      reason,
      suspendedAt: this.suspendedAt,
      heartbeatAt: this.lastSuspendHeartbeatAt,
      ...details
    });
  }

  _resumeFromSuspend(details = {}) {
    if (this.runtimeState !== 'SUSPEND') {
      return;
    }

    const suspendedAt = this.suspendedAt;
    this.runtimeState = 'RUNNING';
    this.suspendReason = null;
    this.suspendedAt = null;
    this.lastSuspendHeartbeatAt = null;
    this.logger.info('recon_engine_resumed', {
      resumedAt: new Date().toISOString(),
      previousSuspendedAt: suspendedAt,
      ...details
    });
  }

  async ensureProxyPoolCapacity(options = {}) {
    if (!this.proxyRotator) {
      return null;
    }

    const minimumAvailable = Math.max(
      1,
      Number(options.minimumAvailable ?? this.minimumReadyProxyCount)
    );
    const context = options.context || 'recon_engine';

    await this._runProxyPoolHeartbeat();
    let snapshot = this._getProxyPoolSnapshot();
    while (snapshot && snapshot.available < minimumAvailable) {
      this._enterSuspendState('INSUFFICIENT_PROXY_CAPACITY', {
        context,
        minimumAvailable,
        available: snapshot.available,
        total: snapshot.total,
        cooling: snapshot.cooling,
        dead: snapshot.dead
      });
      this._emitSuspendHeartbeat('INSUFFICIENT_PROXY_CAPACITY', {
        context,
        minimumAvailable,
        available: snapshot.available,
        total: snapshot.total,
        cooling: snapshot.cooling,
        dead: snapshot.dead
      });
      await this._sleep(this.suspendPollIntervalMs);
      await this._runProxyPoolHeartbeat();
      snapshot = this._getProxyPoolSnapshot();
    }

    this._resumeFromSuspend({
      context,
      minimumAvailable,
      available: snapshot?.available ?? null,
      total: snapshot?.total ?? null
    });

    return snapshot;
  }
}

Object.assign(ReconEngine.prototype, reconMatrixFlow, reconScanModes);

module.exports = { ReconEngine };
