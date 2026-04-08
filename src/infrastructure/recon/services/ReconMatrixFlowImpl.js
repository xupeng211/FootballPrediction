'use strict';

const crypto = require('crypto');
const pLimit = require('p-limit');

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
    const summary = { success: true, season, scannedLeagues: 0, totalPending: 0, linked: 0, mismatched: 0, errors: [], perLeague: [] };

    const targetPendingMap = await this.taskPlanner.prepareReconPendingTargets(targets, limit, {
      allowMismatchRetry: true,
      confidenceThreshold,
      mismatchRetryOnly,
      allNonLinked
    });

    const leagueLimiter = pLimit(Math.max(1, Number(leagueConcurrency)));
    const outcomes = await Promise.all(
      targetPendingMap.map(({ target, pendingMatches, desiredLimit = null }) => leagueLimiter(async () => {
        let navigatorHandle = null;
        let proxyPort = null;

        try {
          navigatorHandle = await this._acquireTargetNavigator(target, {
            launchBrowser: forcePureProtocol !== true
          });
          proxyPort = Number(navigatorHandle?.proxyPort || navigatorHandle?.navigator?.proxy?.port || 0) || null;

          this.logger.info('recon_league_worker_start', {
            league: target.league.name,
            season: target.dbSeason,
            pendingTotal: pendingMatches.length,
            desiredLimit,
            proxyPort,
            leagueConcurrency: Math.max(1, Number(leagueConcurrency)),
            matchConcurrency: Math.max(1, Number(concurrency))
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
            linked: result.linked,
            mismatched: result.mismatched,
            pendingTotal: result.pendingTotal
          });

          return { target, result };
        } catch (error) {
          this.logger.error('recon_matrix_target_failed', {
            league: target.league.name,
            season,
            proxyPort,
            error: error.message
          });
          return { target, error };
        } finally {
          await this._releaseTargetNavigator(navigatorHandle);
        }
      }))
    );

    for (const outcome of outcomes) {
      if (outcome?.error) {
        summary.success = false;
        summary.errors.push({ league: outcome.target.league.name, error: outcome.error.message });
        continue;
      }

      const { target, result } = outcome;
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
    }

    return summary;
  },

  async _acquireTargetNavigator(_target, options = {}) {
    const launchBrowser = options.launchBrowser !== false;

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

    const selectedSource = await this._selectCandidateSourceWithLocalFallback(
      runtimeTarget,
      remainingPending,
      effectiveThreshold,
      navigator
    );
    const candidates = selectedSource.candidates;
    const seasonMirror = selectedSource.seasonMirror || this.mirrorManager.buildSeasonMirror(candidates);

    if (!Array.isArray(candidates) || candidates.length === 0) {
      if (this._canUseLocalDictionaryFallback(runtimeTarget, orderedPending)) {
        const fallbackPending = Number.isInteger(remainingMatchLimit) && remainingMatchLimit > 0
          ? remainingPending.slice(0, Math.min(remainingMatchLimit, remainingPending.length))
          : remainingPending;

        return this._runLocalDictionaryOnlyTarget(runtimeTarget, fallbackPending, {
          batchSize,
          confidenceThreshold: effectiveThreshold,
          sourceSeason: selectedSource?.source?.season || runtimeTarget.dbSeason,
          sourceUrl: selectedSource?.source?.url || this._buildLocalDictionarySourceUrl(runtimeTarget)
        });
      }

      const sourceState = selectedSource?.extractResult?.sourceState || 'SOURCE_EMPTY';
      const error = new Error(sourceState);
      error.code = sourceState;
      error.sourceUrl = selectedSource?.source?.url || target.resultsUrl;
      error.sourceSeason = selectedSource?.source?.season || this.taskPlanner.formatSeasonForUrl(target.season);
      throw error;
    }

    const selectedPending = this.taskPlanner.selectProcessablePendingMatches(
      remainingPending,
      candidates,
      effectiveThreshold,
      remainingMatchLimit,
      seasonMirror
    );
    const runtimeTargetWithSource = {
      ...runtimeTarget,
      reconSourceUrl: selectedSource?.source?.url || target.resultsUrl,
      reconSourceSeason: selectedSource?.source?.season || this.taskPlanner.formatSeasonForUrl(target.season)
    };
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
        this._reconcilePendingMatch(l1Match, candidates, runtimeTargetWithSource, effectiveThreshold, seasonMirror)
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
        mismatches.push({
          match_id: String(outcome.matchId),
          evidence: outcome.evidence || null
        });
      }
    }

    const deduped = this._dedupeMappingsBySeasonHash(mappings);
    if (deduped.droppedMatchIds.length > 0) {
      for (const droppedMatchId of deduped.droppedMatchIds) {
        if (!mismatches.some((item) => String(item?.match_id || item) === String(droppedMatchId))) {
          mismatches.push({
            match_id: String(droppedMatchId),
            evidence: null
          });
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

    if (deduped.bypassedMatchIds.length > 0) {
      this.logger.warn('recon_mapping_hash_bypass', {
        season: target.dbSeason,
        league: target.league.name,
        bypassedCount: deduped.bypassedMatchIds.length,
        bypassedMatchIds: deduped.bypassedMatchIds.slice(0, 10),
        bypassedHashKeys: deduped.bypassedHashKeys.slice(0, 5),
        truncated: deduped.bypassedMatchIds.length > 10 || deduped.bypassedHashKeys.length > 5
      });
    }

    const persistedMappings = deduped.mappings;

    const persistResult = await this._persistReconBatches(
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
      linked: Number(persistResult?.linkedApplied || 0),
      mismatched: Number(persistResult?.mismatchUpdated || 0),
      sourceSeason: selectedSource?.source?.season || this.taskPlanner.formatSeasonForUrl(target.season),
      sourceUrl: selectedSource?.source?.url || target.resultsUrl,
      candidateCount: Number(selectedSource?.localFallbackCandidateCount || (Array.isArray(candidates) ? candidates.length : 0)),
      effectiveConfidenceThreshold: effectiveThreshold
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

  async _selectCandidateSourceWithLocalFallback(target, pendingMatches, confidenceThreshold, navigator = null) {
    try {
      const selectedSource = await this.taskPlanner.selectCandidateSource(
        target,
        pendingMatches,
        confidenceThreshold,
        { navigator: navigator || this.navigator || null }
      );
      const hasCandidates = Array.isArray(selectedSource?.candidates) && selectedSource.candidates.length > 0;
      if (hasCandidates || !this._canUseLocalDictionaryFallback(target, pendingMatches)) {
        return selectedSource;
      }

      this.logger.warn('recon_local_dictionary_fallback_armed', {
        league: target?.league?.name || null,
        season: target?.dbSeason || null,
        sourceState: selectedSource?.extractResult?.sourceState || 'SOURCE_EMPTY',
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
