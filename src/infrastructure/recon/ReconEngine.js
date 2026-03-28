/** @module infrastructure/recon/ReconEngine */

'use strict';

const pLimit = require('p-limit');
const { L1ConfigManager } = require('../services/L1ConfigManager');
const { ReconMatchEvaluator } = require('./services/ReconMatchEvaluator');
const { ReconMirrorManager } = require('./services/ReconMirrorManager');
const { ReconTaskPlanner } = require('./services/ReconTaskPlanner');
const { RECON_CONFIG, getReconConfigSection, resolveRuntimeFeatureFlags } = require('./services/ReconServiceConfig');

class ReconEngine {
  constructor(options = {}) {
    const engineConfig = getReconConfigSection(['recon_runtime', 'engine'], {});
    const matchingConfig = RECON_CONFIG.matching || {};

    this.navigator = options.navigator;
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

    this.matchEvaluator = options.matchEvaluator || new ReconMatchEvaluator({ parser: this.parser, logger: this.logger });
    this.mirrorManager = options.mirrorManager || new ReconMirrorManager({ evaluator: this.matchEvaluator });
    if (typeof this.matchEvaluator.setMirrorManager === 'function') {
      this.matchEvaluator.setMirrorManager(this.mirrorManager);
    }
    this.taskPlanner = options.taskPlanner || new ReconTaskPlanner({
      navigator: this.navigator, repository: this.repository, logger: this.logger, configManager: this.configManager,
      baseUrl: this.baseUrl, matchEvaluator: this.matchEvaluator, mirrorManager: this.mirrorManager
    });
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

  async buildScanTargets(options = {}) {
    return this.taskPlanner.buildScanTargets(options);
  }

  async runReconMatrix(options = {}) {
    const {
      season,
      concurrency = this.defaultReconConcurrency,
      tier = null,
      leagueIds = null,
      batchSize = this.reconBatchSize,
      confidenceThreshold = this.confidenceThreshold,
      limit = null
    } = options;

    const targets = await this.buildScanTargets({ season, tier, leagueIds });
    const summary = { success: true, season, scannedLeagues: 0, totalPending: 0, linked: 0, mismatched: 0, errors: [], perLeague: [] };

    const targetPendingMap = await this.taskPlanner.prepareReconPendingTargets(targets, limit);

    for (const { target, pendingMatches, desiredLimit = null } of targetPendingMap) {
      try {
        const result = await this._runReconTarget(target, {
          concurrency,
          batchSize,
          confidenceThreshold,
          pendingMatches,
          matchLimit: desiredLimit
        });

        summary.scannedLeagues++;
        summary.totalPending += result.pendingTotal;
        summary.linked += result.linked;
        summary.mismatched += result.mismatched;
        summary.perLeague.push({
          league: target.league.name, season: target.dbSeason, pendingTotal: result.pendingTotal, linked: result.linked,
          mismatched: result.mismatched, sourceSeason: result.sourceSeason, sourceUrl: result.sourceUrl, candidateCount: result.candidateCount
        });
      } catch (error) {
        summary.success = false;
        summary.errors.push({ league: target.league.name, error: error.message });
        this.logger.error('recon_matrix_target_failed', { league: target.league.name, season, error: error.message });
      }
    }

    return summary;
  }

  async protocolArchiveScan(season, leagueConfig) {
    const startTime = Date.now();
    const dbSeason = this.taskPlanner.normalizeDbSeason(season);

    this.logger.info('protocol_archive_scan_start', { season, dbSeason, league: leagueConfig.name });

    try {
      const unstitched = await this.taskPlanner.loadReconPendingMatches({ dbSeason, league: leagueConfig });
      if (unstitched.length === 0) {
        return { success: true, season, league: leagueConfig.name, inserted: 0, reason: 'no_pending_matches' };
      }

      const resultsUrl = this.taskPlanner.buildResultsUrl(leagueConfig, season);
      const preferCurrentSeasonSource = leagueConfig?.defaultSeason === dbSeason;
      const extractResult = await this.navigator.protocolArchiveExtract(resultsUrl, {
        maxPages: this.archiveMaxPages,
        timeoutMs: this.archiveTimeoutMs,
        preferCurrentSeasonSource
      });

      this.logger.info('protocol_extract_complete', { candidates: extractResult.matches.length, pagesScanned: extractResult.pagesScanned });

      const { inserted, unmatched } = await this._matchAndStitch(
        extractResult.matches,
        unstitched,
        dbSeason,
        leagueConfig
      );

      let reconciled = 0;
      if (unmatched > 0 && this.stitcher?.setReconciliation) {
        const recResult = await this.stitcher.setReconciliation(
          extractResult.matches,
          unstitched,
          dbSeason,
          leagueConfig
        );
        reconciled = recResult.inserted || 0;
      }

      const totalInserted = inserted + reconciled;
      const coverage = unstitched.length > 0 ? (totalInserted / unstitched.length * 100).toFixed(2) : '0.00';

      return {
        success: true, season, league: leagueConfig.name, pendingTotal: unstitched.length,
        candidatesFound: extractResult.matches.length, inserted: totalInserted, unmatched: unmatched - reconciled,
        coverage: parseFloat(coverage), durationMs: Date.now() - startTime
      };
    } catch (error) {
      this.logger.error('protocol_archive_scan_failed', { error: error.message });
      return { success: false, season, league: leagueConfig.name, error: error.message };
    }
  }

  async dateDrivenScan(season, leagueConfig) {
    this.logger.warn('date_driven_scan_deprecated', { season, league: leagueConfig?.name || null, fallback: 'season_mirror' });
    return this.smartScan(season, leagueConfig);
  }

  async crossLeagueScan(season, leagueConfig, additionalSlugs = []) {
    const startTime = Date.now();
    this.logger.info('cross_league_scan_start', { season, league: leagueConfig.name, additionalSlugs });

    const allResults = [];
    const mainResult = await this.smartScan(season, leagueConfig);
    allResults.push({ slug: leagueConfig.slug, ...mainResult });

    for (const slug of additionalSlugs) {
      const slugConfig = { ...leagueConfig, slug };
      const slugResult = await this.smartScan(season, slugConfig);
      allResults.push({ slug, ...slugResult });
    }

    const totalInserted = allResults.reduce((sum, result) => (
      sum + Number(result.inserted || result.totalInserted || 0)
    ), 0);

    return {
      success: true, season, primaryLeague: leagueConfig.name, scannedLeagues: allResults.length,
      totalInserted, details: allResults, durationMs: Date.now() - startTime
    };
  }

  async smartScan(season, leagueConfig) {
    const startTime = Date.now();

    if (this.reconStrategy === 'legacy') {
      this.logger.warn('smart_scan_strategy_override', {
        season,
        league: leagueConfig?.name || null,
        strategy: 'legacy_protocol_archive'
      });
      const legacyResult = await this.protocolArchiveScan(season, leagueConfig);

      if (legacyResult.success === false) {
        return {
          ...legacyResult,
          strategy: 'legacy_protocol_archive',
          durationMs: Date.now() - startTime
        };
      }

      return {
        success: true,
        season,
        league: leagueConfig.name,
        strategy: 'legacy_protocol_archive',
        pendingTotal: legacyResult.pendingTotal || 0,
        inserted: legacyResult.inserted || 0,
        linked: legacyResult.inserted || 0,
        mismatched: legacyResult.unmatched || 0,
        totalInserted: legacyResult.inserted || 0,
        coverage: Number(legacyResult.coverage || 0),
        sourceSeason: this.taskPlanner.formatSeasonForUrl(season),
        sourceUrl: this.taskPlanner.buildResultsUrl(leagueConfig, season),
        candidateCount: legacyResult.candidatesFound || 0,
        durationMs: Date.now() - startTime
      };
    }

    const target = this.taskPlanner.buildTarget(season, leagueConfig);

    this.logger.info('smart_scan_start', {
      season,
      league: leagueConfig.name,
      strategy: 'season_mirror',
      disableDomFallback: this.disableDomFallback
    });

    const pendingMatches = await this.taskPlanner.loadReconPendingMatches(target);
    if (!Array.isArray(pendingMatches) || pendingMatches.length === 0) {
      return {
        success: true, season, league: leagueConfig.name, strategy: 'season_mirror', pendingTotal: 0, inserted: 0,
        linked: 0, mismatched: 0, totalInserted: 0, coverage: 100, durationMs: Date.now() - startTime
      };
    }

    try {
      const result = await this._runReconTarget(target, {
        concurrency: this.defaultReconConcurrency,
        batchSize: this.reconBatchSize,
        confidenceThreshold: this.confidenceThreshold,
        pendingMatches
      });
      const coverage = result.pendingTotal > 0
        ? Number(((result.linked / result.pendingTotal) * 100).toFixed(2))
        : 100;

      this.logger.info('smart_scan_complete', {
        strategy: 'season_mirror', coverage, linked: result.linked,
        mismatched: result.mismatched, candidateCount: result.candidateCount
      });

      return {
        success: true, season, league: leagueConfig.name, strategy: 'season_mirror', pendingTotal: result.pendingTotal,
        inserted: result.linked, linked: result.linked, mismatched: result.mismatched, totalInserted: result.linked,
        coverage, sourceSeason: result.sourceSeason, sourceUrl: result.sourceUrl,
        candidateCount: result.candidateCount, durationMs: Date.now() - startTime
      };
    } catch (error) {
      if (error.code === 'SOURCE_EMPTY' && this.disableDomFallback) {
        this.logger.warn('season_sweep_empty_dom_fallback_disabled', {
          season,
          league: leagueConfig.name,
          strategy: 'season_mirror',
          error: error.message
        });
        return {
          success: false,
          season,
          league: leagueConfig.name,
          strategy: 'season_mirror_dom_disabled',
          error: error.message,
          durationMs: Date.now() - startTime
        };
      }

      if (error.code === 'SOURCE_EMPTY' && typeof this.domFallbackScan === 'function') {
        this.logger.warn('season_sweep_empty', { season, league: leagueConfig.name, fallback: 'dom_fallback' });
        const domResult = await this.domFallbackScan(season, leagueConfig);
        const coverage = pendingMatches.length > 0
          ? Number((((domResult.inserted || 0) / pendingMatches.length) * 100).toFixed(2))
          : 100;

        return {
          success: Boolean(domResult.success), season, league: leagueConfig.name, strategy: 'season_mirror_dom_fallback',
          pendingTotal: pendingMatches.length, inserted: domResult.inserted || 0, linked: domResult.inserted || 0,
          mismatched: Math.max(0, pendingMatches.length - Number(domResult.inserted || 0)),
          totalInserted: domResult.inserted || 0, coverage, durationMs: Date.now() - startTime
        };
      }

      this.logger.error('smart_scan_failed', { season, league: leagueConfig.name, error: error.message });
      return { success: false, season, league: leagueConfig.name, strategy: 'season_mirror', error: error.message, durationMs: Date.now() - startTime };
    }
  }

  async domFallbackScan(season, leagueConfig) {
    const startTime = Date.now();
    this.logger.info('dom_fallback_scan_start', { season, league: leagueConfig.name });

    try {
      const dbSeason = this.taskPlanner.normalizeDbSeason(season);
      const unstitched = await this.taskPlanner.loadReconPendingMatches({ dbSeason, league: leagueConfig });

      if (unstitched.length === 0) {
        return { success: true, inserted: 0, reason: 'no_pending_matches' };
      }

      const baseUrl = this.taskPlanner.buildResultsUrl(leagueConfig, season);
      const absoluteBaseUrl = this.baseUrl;
      const leagueCountry = String(leagueConfig.country || '').toLowerCase();
      const leagueSlug = String(leagueConfig.slug || '').toLowerCase();

      await this.navigator.navigate(baseUrl, { waitUntil: 'networkidle' });
      await this.navigator.page.waitForTimeout(this.pageSettleWaitMs);

      for (let index = 0; index < 5; index++) {
        await this.navigator.page.evaluate((scrollStepPx) => window.scrollBy(0, scrollStepPx), this.domScrollStepPx);
        await this.navigator.page.waitForTimeout(this.domScrollDelayMs);
      }

      const domMatches = await this.navigator.page.evaluate(({ absoluteBaseUrl, leagueCountry, leagueSlug }) => {
        const matches = [];
        const hashPattern = /-([a-zA-Z0-9]{8})\/$/;

        document.querySelectorAll('a[href*="/football/"]').forEach((link) => {
          const href = link.getAttribute('href') || '';
          const match = href.match(hashPattern);

          if (match && href.includes(leagueCountry) && href.includes(leagueSlug)) {
            const hash = match[1];
            const parent = link.closest('div[class*="event"], tr, .eventRow');
            let text = '';

            if (parent) {
              text = parent.innerText || parent.textContent || '';
            } else {
              text = link.innerText || link.textContent || '';
            }

            matches.push({
              url: href.startsWith('http') ? href : `${absoluteBaseUrl}${href}`,
              hash,
              rawText: text.replace(/\s+/g, ' ').trim(),
              source: 'dom_fallback'
            });
          }
        });

        const seen = new Set();
        return matches.filter((matchItem) => {
          if (seen.has(matchItem.hash)) {
            return false;
          }
          seen.add(matchItem.hash);
          return true;
        });
      }, { absoluteBaseUrl, leagueCountry, leagueSlug });

      this.logger.info('dom_extract_complete', { candidates: domMatches.length });

      let inserted = 0;
      for (const l1Match of unstitched) {
        const matched = domMatches.find((domMatch) => {
          const text = domMatch.rawText.toLowerCase();
          return text.includes(l1Match.home_team.toLowerCase()) && text.includes(l1Match.away_team.toLowerCase());
        });

        if (matched && this.stitcher) {
          try {
            const result = await this.stitcher.stitchWithHashLock(
              [{
                ...matched,
                homeTeam: l1Match.home_team,
                awayTeam: l1Match.away_team
              }],
              [l1Match],
              dbSeason,
              leagueConfig
            );
            inserted += result.inserted || 0;
          } catch (error) {
            this.logger.warn('dom_stitch_failed', { matchId: l1Match.match_id, error: error.message });
          }
        }
      }

      this.logger.info('dom_fallback_scan_complete', { inserted, candidates: domMatches.length });

      return {
        success: true, season, league: leagueConfig.name,
        candidatesFound: domMatches.length, inserted, durationMs: Date.now() - startTime
      };
    } catch (error) {
      this.logger.error('dom_fallback_scan_failed', { error: error.message });
      return { success: false, error: error.message };
    }
  }

  async _matchAndStitch(candidates, l1Matches, season, leagueConfig) {
    let inserted = 0;
    let unmatched = 0;
    const usedCandidates = new Set();

    for (const l1Match of l1Matches) {
      let matched = null;

      for (const candidate of candidates) {
        const key = candidate.hash || candidate.url;
        if (!key || usedCandidates.has(key)) {
          continue;
        }

        if (this._isStrictMatch(candidate, l1Match)) {
          matched = candidate;
          usedCandidates.add(key);
          break;
        }
      }

      if (matched && this.stitcher) {
        try {
          const result = await this.stitcher.stitchWithHashLock(
            [matched],
            [l1Match],
            season,
            leagueConfig
          );
          inserted += result.inserted || 0;
        } catch (error) {
          this.logger.error('stitch_failed', { matchId: l1Match.match_id, error: error.message });
          unmatched++;
        }
      } else {
        unmatched++;
      }
    }

    return { inserted, unmatched };
  }

  _isStrictMatch(candidate, l1Match) {
    return this.matchEvaluator.isStrictMatch(candidate, l1Match);
  }

  async _runReconTarget(target, options = {}) {
    const {
      concurrency = this.defaultReconConcurrency,
      batchSize = this.reconBatchSize,
      confidenceThreshold = this.confidenceThreshold,
      pendingMatches: pendingMatchesOverride = null,
      matchLimit = null
    } = options;

    const pendingMatches = Array.isArray(pendingMatchesOverride)
      ? pendingMatchesOverride
      : await this.taskPlanner.loadReconPendingMatches(target);

    if (!Array.isArray(pendingMatches) || pendingMatches.length === 0) {
      return { pendingTotal: 0, linked: 0, mismatched: 0 };
    }

    const limiter = pLimit(Math.max(1, Number(concurrency)));
    const orderedPending = [...pendingMatches].sort((a, b) => String(a.match_id).localeCompare(String(b.match_id)));
    const selectedSource = await this.taskPlanner.selectCandidateSource(target, orderedPending, confidenceThreshold);
    const candidates = selectedSource.candidates;
    const seasonMirror = selectedSource.seasonMirror || this.mirrorManager.buildSeasonMirror(candidates);

    if (!Array.isArray(candidates) || candidates.length === 0) {
      const sourceState = selectedSource?.extractResult?.sourceState || 'SOURCE_EMPTY';
      const error = new Error(sourceState);
      error.code = sourceState;
      error.sourceUrl = selectedSource?.source?.url || target.resultsUrl;
      error.sourceSeason = selectedSource?.source?.season || this.taskPlanner.formatSeasonForUrl(target.season);
      throw error;
    }

    const selectedPending = this.taskPlanner.selectProcessablePendingMatches(
      orderedPending,
      candidates,
      confidenceThreshold,
      matchLimit,
      seasonMirror
    );
    const reconRunId = this._createReconRunId(target);
    const progress = {
      processed: 0,
      linked: 0,
      mismatched: 0,
      total: selectedPending.length,
      startedAt: Date.now()
    };

    const outcomes = await Promise.all(
      selectedPending.map((l1Match) => limiter(() =>
        this._reconcilePendingMatch(l1Match, candidates, target, confidenceThreshold, seasonMirror)
          .then((outcome) => {
            progress.processed++;
            if (outcome?.status === 'linked') {
              progress.linked++;
            } else if (outcome?.status === 'mismatch') {
              progress.mismatched++;
            }

            if (this._shouldEmitReconProgressSnapshot(progress)) {
              this._emitReconProgressSnapshot(target, progress);
            }

            return outcome;
          })
      ))
    );

    const mappings = [];
    const mismatches = [];

    for (const outcome of outcomes) {
      if (outcome?.status === 'linked' && outcome.mapping) {
        mappings.push(outcome.mapping);
      } else if (outcome?.status === 'mismatch' && outcome.matchId) {
        mismatches.push(outcome.matchId);
      }
    }

    await this._persistReconBatches(
      mappings,
      mismatches,
      Math.max(1, Number(batchSize)),
      {
        reconRunId,
        season: target.dbSeason,
        league: target.league.name,
        sourceSeason: selectedSource?.source?.season || this.taskPlanner.formatSeasonForUrl(target.season),
        sourceUrl: selectedSource?.source?.url || target.resultsUrl
      }
    );

    return {
      pendingTotal: selectedPending.length,
      linked: mappings.length,
      mismatched: mismatches.length,
      sourceSeason: selectedSource?.source?.season || this.taskPlanner.formatSeasonForUrl(target.season),
      sourceUrl: selectedSource?.source?.url || target.resultsUrl,
      candidateCount: Array.isArray(candidates) ? candidates.length : 0
    };
  }

  async _persistReconBatches(mappings, mismatchIds, batchSize, metadata = {}) {
    const orderedMappings = [...mappings].sort((a, b) => String(a.match_id).localeCompare(String(b.match_id)));
    const orderedMismatchIds = [...new Set(mismatchIds.map((id) => String(id)))]
      .sort((a, b) => a.localeCompare(b));
    const linkedTotalBatches = Math.max(1, Math.ceil(orderedMappings.length / batchSize) || 0);
    const mismatchTotalBatches = Math.max(1, Math.ceil(orderedMismatchIds.length / batchSize) || 0);

    for (let index = 0; index < orderedMappings.length; index += batchSize) {
      const batch = orderedMappings.slice(index, index + batchSize);
      const batchIndex = Math.floor(index / batchSize) + 1;
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
        match_ids: this._summarizeMatchIds(batch.map((mapping) => mapping.match_id))
      });
      let result;
      try {
        result = await this.repository.batchSaveOddsPortalMappings(batch, {
          pipelineStatus: 'RECON_LINKED'
        });
      } catch (error) {
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
        inserted: result?.inserted || 0,
        updated: result?.updated || 0
      });
    }

    for (let index = 0; index < orderedMismatchIds.length; index += batchSize) {
      const batch = orderedMismatchIds.slice(index, index + batchSize);
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
      const result = await this.repository.batchUpdateMatchPipelineStatus(batch, 'RECON_MISMATCH', {
        season: metadata.season || null,
        expectedCurrentStatus: 'harvested'
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
    }
  }

  async _reconcilePendingMatch(l1Match, candidates, target, confidenceThreshold, seasonMirror = null) {
    const candidateMatch = this._findBestCandidate(l1Match, candidates, seasonMirror);

    if (!candidateMatch || candidateMatch.confidence < confidenceThreshold) {
      return {
        status: 'mismatch',
        matchId: l1Match.match_id
      };
    }

    return {
      status: 'linked',
      mapping: {
        match_id: l1Match.match_id,
        oddsportal_hash: candidateMatch.candidate.hash,
        full_url: candidateMatch.candidate.url,
        season: target.dbSeason,
        league_name: target.league.name,
        home_team: l1Match.home_team,
        away_team: l1Match.away_team,
        is_reversed: Boolean(candidateMatch.isReversed),
        match_confidence: candidateMatch.confidence,
        mapping_method: candidateMatch.method || 'recon_matrix',
        status: 'pending'
      }
    };
  }

  _buildSeasonMirror(candidates) {
    return this.mirrorManager.buildSeasonMirror(candidates);
  }

  _findBestCandidate(l1Match, candidates, seasonMirror = null) {
    return this.matchEvaluator.findBestCandidate(l1Match, candidates, seasonMirror);
  }
}

module.exports = { ReconEngine };
