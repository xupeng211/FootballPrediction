'use strict';

function compareByMatchId(left, right) {
  return String(left?.match_id || '').localeCompare(String(right?.match_id || ''));
}

function normalizeMismatchRecord(record) {
  if (typeof record === 'string') {
    return { match_id: record, evidence: null };
  }

  const matchId = String(record?.match_id || record?.matchId || '');
  if (!matchId) {
    return null;
  }

  return {
    match_id: matchId,
    evidence: record?.evidence || null
  };
}

function normalizeMismatchRecords(mismatchRecords = []) {
  const normalized = (Array.isArray(mismatchRecords) ? mismatchRecords : [])
    .map(normalizeMismatchRecord)
    .filter(Boolean)
    .map((record) => [record.match_id, record]);

  return [...new Map(normalized).values()].sort(compareByMatchId);
}

function buildH2HNormalizationPayload(mapping, metadata, rawUrl, fallbackSlug) {
  return {
    league_id: Number(mapping?.league_id || metadata?.leagueId || 0) || undefined,
    countrySlug: metadata?.countrySlug || '',
    leagueSlug: metadata?.leagueSlug || '',
    homeTeam: mapping.home_team,
    awayTeam: mapping.away_team,
    hash: mapping.oddsportal_hash,
    url: rawUrl,
    slug: fallbackSlug
  };
}

function compareMappingPriority(left, right) {
  const leftConfidence = Number(left?.match_confidence || 0);
  const rightConfidence = Number(right?.match_confidence || 0);
  if (leftConfidence !== rightConfidence) {
    return leftConfidence - rightConfidence;
  }

  return String(left?.match_id || '').localeCompare(String(right?.match_id || ''));
}

const reconImmediateStore = {
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
    const orderedMappings = [...(Array.isArray(mappings) ? mappings : [])].sort(compareByMatchId);
    const orderedMismatchRecords = normalizeMismatchRecords(mismatchRecords);
    const linkedBatches = this._buildLinkedPersistBatches(orderedMappings, batchSize, metadata);
    const linkedTotalBatches = Math.max(1, linkedBatches.length || 0);
    const mismatchTotalBatches = Math.max(1, Math.ceil(orderedMismatchRecords.length / batchSize) || 0);
    let linkedApplied = 0;
    let mismatchUpdated = 0;

    for (let index = 0; index < linkedBatches.length; index++) {
      linkedApplied += await this._persistLinkedBatch(
        linkedBatches[index],
        index + 1,
        linkedTotalBatches,
        metadata
      );
    }

    for (let index = 0; index < orderedMismatchRecords.length; index += batchSize) {
      const batchRecords = orderedMismatchRecords.slice(index, index + batchSize);
      mismatchUpdated += await this._persistMismatchBatch(
        batchRecords,
        Math.floor(index / batchSize) + 1,
        mismatchTotalBatches,
        metadata
      );
    }

    return {
      linkedApplied,
      mismatchUpdated
    };
  },

  _logReconBatchPersist(eventName, batchType, batchIndex, totalBatches, matchIds, metadata = {}, extra = {}) {
    this.logger.info(eventName, {
      recon_run_id: metadata.reconRunId || null,
      season: metadata.season || null,
      league: metadata.league || null,
      sourceSeason: metadata.sourceSeason || null,
      sourceUrl: metadata.sourceUrl || null,
      batch_type: batchType,
      batch_index: batchIndex,
      total_batches: totalBatches,
      match_ids: this._summarizeMatchIds(matchIds),
      ...extra
    });
  },

  _buildLinkedBatchLogExtra(batchMeta, batch = [], extra = {}) {
    return {
      batch_size: batch.length,
      hash_bypass: batchMeta?.hashBypass === true,
      season_hash_key: batchMeta?.seasonHashKey || null,
      ...extra
    };
  },

  _buildLinkedBatchConflictPayload(batchMeta, batchIndex, totalBatches, matchIds, metadata = {}, error = null) {
    return {
      recon_run_id: metadata.reconRunId || null,
      season: metadata.season || null,
      league: metadata.league || null,
      batch_type: 'linked',
      batch_index: batchIndex,
      total_batches: totalBatches,
      match_ids: this._summarizeMatchIds(matchIds),
      season_hash_key: batchMeta?.seasonHashKey || null,
      error: error?.message || null,
      error_code: error?.code || null,
      conflict: error?.details || null
    };
  },

  async _persistLinkedBatch(batchMeta, batchIndex, totalBatches, metadata = {}) {
    const batch = Array.isArray(batchMeta?.mappings) ? batchMeta.mappings : [];
    const matchIds = batch.map((mapping) => mapping.match_id);

    this._logReconBatchPersist(
      'recon_batch_persist_start',
      'linked',
      batchIndex,
      totalBatches,
      matchIds,
      metadata,
      this._buildLinkedBatchLogExtra(batchMeta, batch)
    );

    let result;
    try {
      result = await this.repository.batchSaveOddsPortalMappings(batch, {
        pipelineStatus: 'RECON_LINKED',
        preserve_linked_status: true
      });
    } catch (error) {
      if (batchMeta?.hashBypass === true && this._isSkippableHashBypassConflict(error)) {
        this.logger.warn(
          'recon_batch_hash_bypass_conflict_skipped',
          this._buildLinkedBatchConflictPayload(batchMeta, batchIndex, totalBatches, matchIds, metadata, error)
        );
        return 0;
      }

      this.logger.error(
        'recon_batch_conflict',
        this._buildLinkedBatchConflictPayload(batchMeta, batchIndex, totalBatches, matchIds, metadata, error)
      );
      throw error;
    }

    this._logReconBatchPersist(
      'recon_batch_persist_complete',
      'linked',
      batchIndex,
      totalBatches,
      matchIds,
      metadata,
      this._buildLinkedBatchLogExtra(batchMeta, batch, {
        inserted: result?.inserted || 0,
        updated: result?.updated || 0
      })
    );

    return Number(result?.applied ?? result?.inserted ?? 0);
  },

  async _persistMismatchBatch(batchRecords, batchIndex, totalBatches, metadata = {}) {
    const batch = batchRecords.map((record) => String(record.match_id));

    this._logReconBatchPersist(
      'recon_batch_persist_start',
      'mismatch',
      batchIndex,
      totalBatches,
      batch,
      metadata,
      { batch_size: batch.length }
    );

    await this._persistMismatchEvidenceBatch(batchRecords);
    const result = await this.repository.batchUpdateMatchPipelineStatus(batch, 'RECON_MISMATCH', {
      season: metadata.season || null,
      expectedCurrentStatus: this._buildMismatchExpectedStatus(metadata)
    });

    this._logReconBatchPersist(
      'recon_batch_persist_complete',
      'mismatch',
      batchIndex,
      totalBatches,
      batch,
      metadata,
      { updated: result?.updated || 0 }
    );

    return Number(result?.updated || 0);
  },

  async _persistMismatchEvidenceBatch(batchRecords = []) {
    if (typeof this.repository.batchSaveMismatchEvidence !== 'function') {
      return;
    }

    const evidenceBatch = batchRecords
      .map((record) => record.evidence)
      .filter(Boolean);

    if (evidenceBatch.length === 0) {
      return;
    }

    await this.repository.batchSaveMismatchEvidence(evidenceBatch);
  },

  _buildMismatchExpectedStatus(metadata = {}) {
    return metadata.allowMismatchRetry === true
      ? ['harvested', 'RECON_MISMATCH']
      : 'harvested';
  },

  _buildSeasonHashKey(mapping = {}) {
    const season = String(mapping?.season || '').trim();
    const hash = String(mapping?.oddsportal_hash || '').trim();
    if (!season || !hash) {
      return '';
    }

    return `${season}::${hash}`;
  },

  _warnRejectedH2HUrl(mapping, metadata = {}, rawUrl, reason) {
    this.logger.warn('rejected_due_to_h2h_url', {
      match_id: String(mapping?.match_id || ''),
      season: String(mapping?.season || ''),
      oddsportal_hash: String(mapping?.oddsportal_hash || ''),
      full_url: rawUrl,
      candidate_source_url: String(metadata?.sourceUrl || mapping?.candidate_source_url || ''),
      reason
    });
  },

  _buildH2HNormalizationSourceUrls(mapping = {}, metadata = {}) {
    const normalizationCandidates = this._splitSourceUrls(
      mapping?.candidate_source_url
      || mapping?.sourceUrl
      || mapping?.source_url
      || metadata?.sourceUrl
      || ''
    );

    return normalizationCandidates.length > 0
      ? normalizationCandidates
      : [this._resolveTrustedOddsPortalBaseUrl()];
  },

  _createH2HNormalizationContext(sourceUrl) {
    return {
      ...this.matchExtractor,
      baseUrl: this._resolveTrustedOddsPortalBaseUrl(),
      sourceUrl,
      resultsUrl: sourceUrl,
      leagueUrl: sourceUrl,
      extractMaxDepth: 5
    };
  },

  _findCanonicalH2HUrl(mapping = {}, metadata = {}, rawUrl = '', candidateSourceUrls = [], fallbackSlug = '') {
    for (const sourceUrl of candidateSourceUrls) {
      const normalized = this.matchExtractor.normalizeMatchObject.call(
        this._createH2HNormalizationContext(sourceUrl),
        buildH2HNormalizationPayload(mapping, metadata, rawUrl, fallbackSlug),
        'recon_matrix_quality_gate'
      );

      if (!normalized?.url || !this._isCanonicalEventUrl(normalized.url, mapping.oddsportal_hash)) {
        continue;
      }

      return normalized.url;
    }

    return null;
  },

  _normalizeH2HMappingUrl(mapping = {}, metadata = {}) {
    const rawUrl = String(mapping?.full_url || '').trim();
    if (!/\/football\/h2h\//iu.test(rawUrl)) {
      return mapping;
    }

    if (!this.matchExtractor || typeof this.matchExtractor.normalizeMatchObject !== 'function') {
      this._warnRejectedH2HUrl(mapping, metadata, rawUrl, 'match_extractor_missing');
      return null;
    }

    const candidateSourceUrls = this._buildH2HNormalizationSourceUrls(mapping, metadata);
    const fallbackSlug = this._buildFallbackEventSlug(mapping.home_team, mapping.away_team);
    const normalizedUrl = this._findCanonicalH2HUrl(
      mapping,
      metadata,
      rawUrl,
      candidateSourceUrls,
      fallbackSlug
    );

    if (normalizedUrl) {
      return {
        ...mapping,
        full_url: normalizedUrl
      };
    }

    this._warnRejectedH2HUrl(mapping, metadata, rawUrl, 'canonical_hash_url_missing');
    return null;
  },

  _buildLinkedPersistBatches(mappings = [], batchSize = 25, metadata = {}) {
    const orderedMappings = [...(Array.isArray(mappings) ? mappings : [])]
      .map((mapping) => this._normalizeH2HMappingUrl(mapping, metadata))
      .filter(Boolean)
      .sort(compareByMatchId);
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

  _groupMappingsBySeasonHash(mappings = []) {
    const groupedByHash = new Map();

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

    return groupedByHash;
  },

  _selectMappingsByMatchId(group = [], droppedMatchIds = []) {
    const selectedByMatchId = new Map();

    for (const mapping of group) {
      const matchId = String(mapping?.match_id || '').trim();
      if (!matchId) {
        continue;
      }

      const current = selectedByMatchId.get(matchId);
      if (!current) {
        selectedByMatchId.set(matchId, mapping);
        continue;
      }

      if (compareMappingPriority(mapping, current) > 0) {
        droppedMatchIds.push(String(current.match_id));
        selectedByMatchId.set(matchId, mapping);
        continue;
      }

      droppedMatchIds.push(matchId);
    }

    return [...selectedByMatchId.values()];
  },

  _shouldBypassSeasonHashGroup(uniqueMatchMappings = []) {
    return uniqueMatchMappings.some((mapping) => (
      String(mapping?.status || '').trim().toLowerCase() === 'pending'
    ));
  },

  _chooseSeasonHashWinner(uniqueMatchMappings = [], droppedMatchIds = []) {
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

      if (compareMappingPriority(mapping, winner) > 0) {
        droppedMatchIds.push(String(winner.match_id));
        winner = mapping;
        continue;
      }

      droppedMatchIds.push(String(mapping.match_id));
    }

    return winner;
  },

  _finalizeSeasonHashDedupe(selectedMappings, droppedMatchIds, bypassedMatchIds, bypassedHashKeys) {
    return {
      mappings: selectedMappings,
      droppedMatchIds: [...new Set(droppedMatchIds)].sort((a, b) => a.localeCompare(b)),
      bypassedMatchIds: [...new Set(bypassedMatchIds)].sort((a, b) => a.localeCompare(b)),
      bypassedHashKeys: [...new Set(bypassedHashKeys)].sort((a, b) => a.localeCompare(b))
    };
  },

  _dedupeMappingsBySeasonHash(mappings = []) {
    const groupedByHash = this._groupMappingsBySeasonHash(mappings);
    const droppedMatchIds = [];
    const bypassedMatchIds = [];
    const bypassedHashKeys = [];
    const selectedMappings = [];

    for (const [key, group] of groupedByHash.entries()) {
      const uniqueMatchMappings = this._selectMappingsByMatchId(group, droppedMatchIds);
      if (uniqueMatchMappings.length === 0) {
        continue;
      }

      if (uniqueMatchMappings.length === 1) {
        selectedMappings.push(uniqueMatchMappings[0]);
        continue;
      }

      if (this._shouldBypassSeasonHashGroup(uniqueMatchMappings)) {
        selectedMappings.push(...uniqueMatchMappings);
        bypassedMatchIds.push(...uniqueMatchMappings.map((mapping) => String(mapping.match_id)));
        bypassedHashKeys.push(key);
        continue;
      }

      selectedMappings.push(this._chooseSeasonHashWinner(uniqueMatchMappings, droppedMatchIds));
    }

    return this._finalizeSeasonHashDedupe(
      selectedMappings,
      droppedMatchIds,
      bypassedMatchIds,
      bypassedHashKeys
    );
  }
};

module.exports = { reconImmediateStore };
