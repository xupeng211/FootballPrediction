/** @module infrastructure/recon/ReconEngine */

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
    this.traceId = options.traceId || null;
    this.configManager = options.configManager || new L1ConfigManager({ logger: this.logger });
    this.baseUrl = options.baseUrl || options.config?.oddsportal?.base_url || 'https://www.oddsportal.com';
    this.engineConfig = engineConfig;
    this.reconBatchSize = Math.max(1, Number(options.reconBatchSize ?? engineConfig.recon_batch_size));
    this.defaultReconConcurrency = Math.max(1, Number(options.defaultReconConcurrency ?? engineConfig.default_concurrency));
    this.confidenceThreshold = Number(options.confidenceThreshold ?? engineConfig.confidence_threshold ?? matchingConfig.confidence_threshold);
    this.archiveMaxPages = Math.max(1, Number(options.archiveMaxPages ?? engineConfig.archive_max_pages));
    this.archiveTimeoutMs = Math.max(1, Number(options.archiveTimeoutMs ?? engineConfig.archive_timeout_ms));
    this.pageSettleWaitMs = Math.max(0, Number(options.pageSettleWaitMs ?? engineConfig.page_settle_wait_ms));
    this.domScrollStepPx = Math.max(1, Number(options.domScrollStepPx ?? engineConfig.dom_scroll_step_px));
    this.domScrollDelayMs = Math.max(0, Number(options.domScrollDelayMs ?? engineConfig.dom_scroll_delay_ms));
    this.progressLogEvery = Math.max(1, Number(options.progressLogEvery ?? engineConfig.progress_log_every));
    this.progressHighSuccessThreshold = Number(options.progressHighSuccessThreshold ?? engineConfig.progress_high_success_threshold ?? 1);
    this.progressSampleMultiplier = Math.max(1, Number(options.progressSampleMultiplier ?? engineConfig.progress_sample_multiplier ?? 1));
    this.featureFlags = options.featureFlags || resolveRuntimeFeatureFlags();
    this.reconStrategy = options.reconStrategy || this.featureFlags.reconStrategy;
    this.disableDomFallback = options.disableDomFallback ?? this.featureFlags.disableDomFallback;
    this.currentSeasonOnly = options.currentSeasonOnly === true;
    this.allNonLinked = options.allNonLinked === true;
    this.forceDomMode = options.forceDomMode === true;
    this.matchExtractor = options.matchExtractor || reconMatchExtractor;

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
      mirrorManager: this.mirrorManager
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
}

Object.assign(ReconEngine.prototype, reconMatrixFlow, reconScanModes);

module.exports = { ReconEngine };
