'use strict';

const {
  assertSuccessfulRebind,
  shouldForceOverwriteEvidenceOnlyConflict,
  shouldPreferIncomingProtocolOverwrite,
  shouldPreferIncomingSequentialHashOverwrite
} = require('../../shared/helpers/reconMappingStoreShared');

function roundDecisionValue(value) {
  return Number.isFinite(value) ? Number(value.toFixed(3)) : 0;
}

function buildDecisionEvidence(decision = {}) {
  return {
    date_distance_ms: Number.isFinite(decision.dateDistanceMs)
      ? decision.dateDistanceMs
      : null,
    existing_confidence: roundDecisionValue(decision.existingConfidence),
    incoming_confidence: roundDecisionValue(decision.incomingConfidence),
    confidence_delta: roundDecisionValue(decision.confidenceDelta),
    score_delta: roundDecisionValue(decision.scoreDelta),
    existing_score: roundDecisionValue(decision.existingScore),
    incoming_score: roundDecisionValue(decision.incomingScore)
  };
}

class ReconHashConflictResolver {
  constructor(options = {}) {
    this.arbiter = options.arbiter;
    this.logger = options.logger || { info() {}, warn() {}, error() {} };
    this.RepositoryError = options.RepositoryError;
    this.queries = options.queries;
    this.statusUpdater = options.statusUpdater;
    this.persistence = null;
  }

  attachPersistence(persistence) {
    this.persistence = persistence;
  }

  requirePersistence() {
    if (!this.persistence) {
      throw new TypeError('[ReconMappingStore] 缺少必需依赖: conflictPersistence');
    }

    return this.persistence;
  }

  async resolveHashConflictWithClient(client, conflict = {}) {
    const context = await this.buildConflictContext(client, conflict);
    if (!context) {
      return { resolved: false };
    }

    const preferredOverwrite = await this.applyPreferredOverwrite(client, context);
    if (preferredOverwrite) {
      return preferredOverwrite;
    }

    const duplicateResolution = await this.handleSameFixtureConflict(client, context);
    if (duplicateResolution) {
      return duplicateResolution;
    }

    const preservedResolution = this.buildPreservedLinkResolution(context);
    if (preservedResolution) {
      return preservedResolution;
    }

    const rebindResolution = await this.handleIncomingRebind(client, context);
    if (rebindResolution) {
      return rebindResolution;
    }

    return this.forceFallbackOverwrite(client, context);
  }

  async buildConflictContext(client, conflict = {}) {
    const existingMapping = conflict.existingMapping || null;
    const incomingMapping = conflict.incomingMapping || null;
    if (!existingMapping || !incomingMapping) {
      return null;
    }

    const matchRows = await this.queries.fetchMatchesByIdsWithClient(client, [
      existingMapping.match_id,
      incomingMapping.match_id
    ]);
    const existingMatch = matchRows.get(String(existingMapping.match_id));
    const incomingMatch = matchRows.get(String(incomingMapping.match_id));
    if (!existingMatch || !incomingMatch) {
      return null;
    }

    const decision = this.arbiter.analyzeConflict({
      existingMatch,
      incomingMatch,
      existingMapping,
      incomingMapping
    });
    const existingLinked = existingMatch.pipeline_status === 'RECON_LINKED';
    const preserveLinkedStatus = Boolean(conflict.preserveLinkedStatus);

    return {
      decision,
      existingLinked,
      existingMapping,
      existingMatch,
      evidenceOnlyOverwritePreferred: shouldForceOverwriteEvidenceOnlyConflict(existingMapping, incomingMapping),
      hasOptionalFields: conflict.hasOptionalFields || {},
      incomingMapping,
      incomingMatch,
      pipelineStatus: conflict.pipelineStatus || null,
      preserveLinkedStatus,
      protocolOverwritePreferred: existingLinked && preserveLinkedStatus
        ? shouldPreferIncomingProtocolOverwrite({
          arbiter: this.arbiter,
          decision,
          existingMapping,
          existingMatch,
          incomingMapping,
          incomingMatch
        })
        : false,
      sequentialHashOverwritePreferred: existingLinked && preserveLinkedStatus
        ? shouldPreferIncomingSequentialHashOverwrite({
          arbiter: this.arbiter,
          decision,
          existingMapping,
          existingMatch,
          incomingMapping,
          incomingMatch
        })
        : false
    };
  }

  async applyPreferredOverwrite(client, context) {
    const shouldForce = context.evidenceOnlyOverwritePreferred || context.sequentialHashOverwritePreferred;
    if (!shouldForce) {
      return null;
    }

    const reason = context.evidenceOnlyOverwritePreferred
      ? 'replace_evidence_only_conflict'
      : 'sequential_hash_rollover';

    const forcedResolution = await this.requirePersistence().forceOverwriteSeasonHashConflictWithClient(
      client,
      context.existingMapping,
      context.incomingMapping,
      context.hasOptionalFields,
      {
        pipelineStatus: context.pipelineStatus,
        preserveLinkedStatus: context.preserveLinkedStatus,
        reason
      }
    );

    return forcedResolution?.resolved ? forcedResolution : null;
  }

  async handleSameFixtureConflict(client, context) {
    if (!context.decision.sameFixture) {
      return null;
    }

    const winner = context.decision.preferredWinner;
    const winnerMatch = winner === 'existing' ? context.existingMatch : context.incomingMatch;
    const loserMatch = winner === 'existing' ? context.incomingMatch : context.existingMatch;
    const resolution = winner === 'incoming'
      ? await this.promoteIncomingDuplicateWinner(client, context)
      : await this.keepExistingDuplicateWinner(client, context);

    this.logger.warn('[HEAL] 检测到同场重复 ID，已自动收敛 season/hash 冲突', {
      season: context.incomingMapping.season,
      oddsportal_hash: context.incomingMapping.oddsportal_hash,
      winner_match_id: String(winnerMatch.match_id),
      loser_match_id: String(loserMatch.match_id),
      resolution: winner === 'existing'
        ? 'keep_existing_mark_incoming_failed'
        : 'rebind_to_incoming_mark_existing_failed'
    });

    return {
      resolved: true,
      action: winner === 'existing' ? 'keep_existing_duplicate' : 'rebind_duplicate',
      ...resolution
    };
  }

  async promoteIncomingDuplicateWinner(client, context) {
    const rowCount = await this.requirePersistence().rebindMappingToMatchWithClient(
      client,
      context.existingMapping,
      context.incomingMapping,
      context.hasOptionalFields
    );
    assertSuccessfulRebind(this.RepositoryError, rowCount, {
      season: context.incomingMapping.season,
      oddsportal_hash: context.incomingMapping.oddsportal_hash,
      previous_match_id: String(context.existingMatch.match_id),
      rebound_match_id: String(context.incomingMatch.match_id),
      resolution: 'rebind_duplicate'
    });

    await this.statusUpdater.setSingleMatchPipelineStatusWithClient(client, context.existingMatch.match_id, 'failed', {
      requireNoMapping: true
    });

    if (!context.pipelineStatus) {
      return { linkedStatusUpdated: 0, mappingApplied: 1 };
    }

    await this.statusUpdater.setSingleMatchPipelineStatusWithClient(
      client,
      context.incomingMatch.match_id,
      context.pipelineStatus,
      {
        expectedCurrentStatus: context.incomingMatch.pipeline_status || 'harvested'
      }
    );

    return { linkedStatusUpdated: 1, mappingApplied: 1 };
  }

  async keepExistingDuplicateWinner(client, context) {
    await this.statusUpdater.setSingleMatchPipelineStatusWithClient(client, context.incomingMatch.match_id, 'failed', {
      expectedCurrentStatus: context.incomingMatch.pipeline_status || 'harvested'
    });

    return { linkedStatusUpdated: 0, mappingApplied: 0 };
  }

  buildPreservedLinkResolution(context) {
    const shouldPreserve = context.existingLinked
      && context.preserveLinkedStatus
      && !context.decision.incomingHasStrongerEvidence
      && !context.protocolOverwritePreferred;
    if (!shouldPreserve) {
      return null;
    }

    this.logger.warn('[HEAL] 检测到 season/hash 冲突，但新证据不足以推翻既有 RECON_LINKED，已保留原绑定', {
      season: context.incomingMapping.season,
      oddsportal_hash: context.incomingMapping.oddsportal_hash,
      existing_match_id: String(context.existingMatch.match_id),
      incoming_match_id: String(context.incomingMatch.match_id),
      preserve_linked_status: context.preserveLinkedStatus,
      existing_match_date: context.existingMatch.match_date,
      incoming_match_date: context.incomingMatch.match_date,
      evidence: buildDecisionEvidence(context.decision)
    });

    return {
      resolved: true,
      action: 'preserve_existing_link',
      linkedStatusUpdated: 0,
      mappingApplied: 0
    };
  }

  async handleIncomingRebind(client, context) {
    const incomingWins = context.decision.incomingScore >= this.arbiter.sameFixtureThreshold
      && context.decision.incomingScore > context.decision.existingScore;
    if (!incomingWins) {
      return null;
    }

    if (context.existingLinked && !context.decision.incomingHasStrongerEvidence && !context.protocolOverwritePreferred) {
      return { resolved: false };
    }

    const rowCount = await this.requirePersistence().rebindMappingToMatchWithClient(
      client,
      context.existingMapping,
      context.incomingMapping,
      context.hasOptionalFields
    );
    assertSuccessfulRebind(this.RepositoryError, rowCount, {
      season: context.incomingMapping.season,
      oddsportal_hash: context.incomingMapping.oddsportal_hash,
      previous_match_id: String(context.existingMatch.match_id),
      rebound_match_id: String(context.incomingMatch.match_id),
      resolution: 'rebind_wrong_fixture'
    });

    await this.statusUpdater.setSingleMatchPipelineStatusWithClient(client, context.existingMatch.match_id, 'harvested', {
      expectedCurrentStatus: 'RECON_LINKED',
      requireNoMapping: true
    });

    if (context.pipelineStatus) {
      await this.statusUpdater.setSingleMatchPipelineStatusWithClient(
        client,
        context.incomingMatch.match_id,
        context.pipelineStatus,
        {
          expectedCurrentStatus: context.incomingMatch.pipeline_status || 'harvested'
        }
      );
    }

    this.logger.warn('[HEAL] 检测到 season/hash 映射误绑，已自动重绑到更匹配的 match_id', {
      season: context.incomingMapping.season,
      oddsportal_hash: context.incomingMapping.oddsportal_hash,
      previous_match_id: String(context.existingMatch.match_id),
      rebound_match_id: String(context.incomingMatch.match_id),
      previous_match: {
        home_team: context.existingMatch.home_team,
        away_team: context.existingMatch.away_team,
        match_date: context.existingMatch.match_date
      },
      rebound_match: {
        home_team: context.incomingMatch.home_team,
        away_team: context.incomingMatch.away_team,
        match_date: context.incomingMatch.match_date
      },
      mapping_target: {
        home_team: context.incomingMapping.home_team,
        away_team: context.incomingMapping.away_team,
        full_url: context.incomingMapping.full_url
      },
      scores: {
        existing: roundDecisionValue(context.decision.existingScore),
        incoming: roundDecisionValue(context.decision.incomingScore)
      },
      preserve_linked_override: context.protocolOverwritePreferred,
      evidence: buildDecisionEvidence(context.decision)
    });

    return {
      resolved: true,
      action: 'rebind_wrong_fixture',
      linkedStatusUpdated: context.pipelineStatus ? 1 : 0,
      mappingApplied: 1
    };
  }

  async forceFallbackOverwrite(client, context) {
    const forcedResolution = await this.requirePersistence().forceOverwriteSeasonHashConflictWithClient(
      client,
      context.existingMapping,
      context.incomingMapping,
      context.hasOptionalFields,
      {
        pipelineStatus: context.pipelineStatus,
        preserveLinkedStatus: context.preserveLinkedStatus,
        reason: 'arbiter_force_overwrite'
      }
    );

    return forcedResolution?.resolved ? forcedResolution : { resolved: false };
  }
}

module.exports = { ReconHashConflictResolver };
