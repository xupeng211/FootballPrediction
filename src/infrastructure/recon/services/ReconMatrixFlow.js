'use strict';

const pLimit = require('p-limit');

const reconMatrixFlow = {
  async buildScanTargets(options = {}) {
    return this.taskPlanner.buildScanTargets({
      ...options,
      currentSeasonOnly: options.currentSeasonOnly ?? this.currentSeasonOnly
    });
  },

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

    const targetPendingMap = await this.taskPlanner.prepareReconPendingTargets(targets, limit, {
      allowMismatchRetry: true,
      confidenceThreshold
    });

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
          league: target.league.name,
          season: target.dbSeason,
          pendingTotal: result.pendingTotal,
          linked: result.linked,
          mismatched: result.mismatched,
          sourceSeason: result.sourceSeason,
          sourceUrl: result.sourceUrl,
          candidateCount: result.candidateCount
        });
      } catch (error) {
        summary.success = false;
        summary.errors.push({ league: target.league.name, error: error.message });
        this.logger.error('recon_matrix_target_failed', { league: target.league.name, season, error: error.message });
      }
    }

    return summary;
  },

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
    const reconPolicy = this.taskPlanner.resolveReconPolicy(target, orderedPending, confidenceThreshold);
    const effectiveThreshold = Number(reconPolicy.effectiveConfidenceThreshold || confidenceThreshold);
    const runtimeTarget = {
      ...target,
      reconPolicy: {
        ...(target?.reconPolicy || {}),
        ...reconPolicy
      }
    };
    const selectedSource = await this.taskPlanner.selectCandidateSource(runtimeTarget, orderedPending, effectiveThreshold);
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
      effectiveThreshold,
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
        this._reconcilePendingMatch(l1Match, candidates, runtimeTarget, effectiveThreshold, seasonMirror)
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

    const deduped = this._dedupeMappingsBySeasonHash(mappings);
    if (deduped.droppedMatchIds.length > 0) {
      for (const droppedMatchId of deduped.droppedMatchIds) {
        if (!mismatches.includes(droppedMatchId)) {
          mismatches.push(droppedMatchId);
        }
      }

      this.logger.warn('recon_mapping_hash_dedup', {
        season: target.dbSeason,
        league: target.league.name,
        droppedCount: deduped.droppedMatchIds.length,
        droppedMatchIds: deduped.droppedMatchIds.slice(0, 10),
        truncated: deduped.droppedMatchIds.length > 10
      });
    }

    const persistedMappings = deduped.mappings;

    await this._persistReconBatches(
      persistedMappings,
      mismatches,
      Math.max(1, Number(batchSize)),
      {
        reconRunId,
        season: target.dbSeason,
        league: target.league.name,
        sourceSeason: selectedSource?.source?.season || this.taskPlanner.formatSeasonForUrl(target.season),
        sourceUrl: selectedSource?.source?.url || target.resultsUrl,
        allowMismatchRetry: target?.reconPolicy?.allowMismatchRetry === true
      }
    );

    return {
      pendingTotal: selectedPending.length,
      linked: persistedMappings.length,
      mismatched: mismatches.length,
      sourceSeason: selectedSource?.source?.season || this.taskPlanner.formatSeasonForUrl(target.season),
      sourceUrl: selectedSource?.source?.url || target.resultsUrl,
      candidateCount: Array.isArray(candidates) ? candidates.length : 0,
      effectiveConfidenceThreshold: effectiveThreshold
    };
  },

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
          pipelineStatus: 'RECON_LINKED',
          preserve_linked_status: true
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
    }
  },

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
  },

  _buildSeasonMirror(candidates) {
    return this.mirrorManager.buildSeasonMirror(candidates);
  },

  _findBestCandidate(l1Match, candidates, seasonMirror = null) {
    return this.matchEvaluator.findBestCandidate(l1Match, candidates, seasonMirror);
  },

  _dedupeMappingsBySeasonHash(mappings = []) {
    const selectedByHash = new Map();
    const droppedMatchIds = [];

    const comparePriority = (left, right) => {
      const leftConfidence = Number(left?.match_confidence || 0);
      const rightConfidence = Number(right?.match_confidence || 0);
      if (leftConfidence !== rightConfidence) {
        return leftConfidence - rightConfidence;
      }

      return String(left?.match_id || '').localeCompare(String(right?.match_id || ''));
    };

    for (const mapping of Array.isArray(mappings) ? mappings : []) {
      const season = String(mapping?.season || '').trim();
      const hash = String(mapping?.oddsportal_hash || '').trim();
      const matchId = String(mapping?.match_id || '').trim();
      if (!season || !hash || !matchId) {
        continue;
      }

      const key = `${season}::${hash}`;
      if (!selectedByHash.has(key)) {
        selectedByHash.set(key, mapping);
        continue;
      }

      const current = selectedByHash.get(key);
      if (comparePriority(mapping, current) > 0) {
        droppedMatchIds.push(String(current.match_id));
        selectedByHash.set(key, mapping);
      } else {
        droppedMatchIds.push(matchId);
      }
    }

    return {
      mappings: [...selectedByHash.values()],
      droppedMatchIds: [...new Set(droppedMatchIds)].sort((a, b) => a.localeCompare(b))
    };
  }
};

module.exports = { reconMatrixFlow };
