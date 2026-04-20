/* eslint-disable complexity, max-lines */
'use strict';

const { RECON_CONFIG, getReconConfigSection } = require('./ReconServiceConfig');
const { reconTaskPlannerSourceSelector } = require('./ReconTaskPlannerSourceSelector');
const { reconTaskPlannerUrlUtils } = require('./ReconTaskPlannerUrlUtils');

const PENDING_STATUS_PRIORITY = new Map([
  ['HARVESTED', 0],
  ['RECON_MISMATCH', 1]
]);

function resolveMatchDateTimestamp(match = null) {
  const rawMatchDate = match?.match_date || match?.matchDate || null;
  if (!rawMatchDate) {
    return 0;
  }

  const timestamp = new Date(rawMatchDate).getTime();
  return Number.isFinite(timestamp) ? timestamp : 0;
}

function normalizePendingPipelineStatus(match = null) {
  return String(match?.pipeline_status || '').trim().toUpperCase();
}

function isFuturePendingMatch(match = null, now = new Date()) {
  const kickoffAt = resolveMatchDateTimestamp(match);
  return kickoffAt > 0 && kickoffAt > now.getTime();
}

function comparePendingMatchesForProcessing(left, right, now = new Date()) {
  const leftTimestamp = resolveMatchDateTimestamp(left);
  const rightTimestamp = resolveMatchDateTimestamp(right);
  const leftIsFuture = isFuturePendingMatch(left, now);
  const rightIsFuture = isFuturePendingMatch(right, now);

  if (leftIsFuture !== rightIsFuture) {
    return leftIsFuture ? 1 : -1;
  }

  const leftStatusPriority = PENDING_STATUS_PRIORITY.get(normalizePendingPipelineStatus(left)) ?? 2;
  const rightStatusPriority = PENDING_STATUS_PRIORITY.get(normalizePendingPipelineStatus(right)) ?? 2;
  if (leftStatusPriority !== rightStatusPriority) {
    return leftStatusPriority - rightStatusPriority;
  }

  if (leftTimestamp !== rightTimestamp) {
    return leftIsFuture
      ? leftTimestamp - rightTimestamp
      : rightTimestamp - leftTimestamp;
  }

  return String(left?.match_id || '').localeCompare(String(right?.match_id || ''));
}

class ReconTaskPlanner {
  constructor(options = {}) {
    const matchingConfig = RECON_CONFIG.matching || {};
    const runtimeConfig = getReconConfigSection(['recon_runtime', 'task_planner'], {});

    this.navigator = options.navigator || null;
    this.repository = options.repository || null;
    this.logger = options.logger || console;
    this.configManager = options.configManager || null;
    this.baseUrl = options.baseUrl || runtimeConfig.base_url;
    this.matchEvaluator = options.matchEvaluator || null;
    this.mirrorManager = options.mirrorManager || null;
    this.sampleSize = Math.max(1, Number(options.sampleSize ?? runtimeConfig.sample_size));
    this.archiveMaxPages = Math.max(1, Number(options.archiveMaxPages ?? runtimeConfig.archive_max_pages));
    this.highVolumeArchiveMaxPages = Math.max(
      this.archiveMaxPages,
      Number(options.highVolumeArchiveMaxPages ?? runtimeConfig.high_volume_archive_max_pages ?? 100)
    );
    this.highVolumePendingThreshold = Math.max(
      1,
      Number(options.highVolumePendingThreshold ?? runtimeConfig.high_volume_pending_threshold ?? 300)
    );
    this.archiveTimeoutMs = Math.max(1, Number(options.archiveTimeoutMs ?? runtimeConfig.archive_timeout_ms));
    this.resultsPathTemplate = options.resultsPathTemplate || runtimeConfig.results_path;
    this.fixturesPathTemplate = options.fixturesPathTemplate || runtimeConfig.fixtures_path;
    this.mismatchRetryThresholdDelta = Number(options.mismatchRetryThresholdDelta ?? runtimeConfig.mismatch_retry_threshold_delta ?? 0.05);
    this.mismatchRetryThresholdFloor = Number(options.mismatchRetryThresholdFloor ?? runtimeConfig.mismatch_retry_threshold_floor ?? 0.45);
    this.minimumConfidenceThreshold = Number(
      options.minimumConfidenceThreshold
      ?? runtimeConfig.minimum_confidence_threshold
      ?? matchingConfig.confidence_threshold
      ?? 0.75
    );
    this.mismatchRetryThresholdFloorByLeagueId = new Map(
      Object.entries(
        options.mismatchRetryThresholdFloorByLeagueId
        ?? runtimeConfig.mismatch_retry_threshold_floor_by_league_id
        ?? {}
      )
        .map(([leagueId, floor]) => [Number(leagueId), Number(floor)])
        .filter(([leagueId, floor]) => Number.isInteger(leagueId) && leagueId > 0 && Number.isFinite(floor))
    );
    this.confidenceThresholdOverrideByLeagueId = new Map(
      Object.entries(
        options.confidenceThresholdOverrideByLeagueId
        ?? runtimeConfig.confidence_threshold_override_by_league_id
        ?? {}
      )
        .map(([leagueId, threshold]) => [Number(leagueId), Number(threshold)])
        .filter(([leagueId, threshold]) => Number.isInteger(leagueId) && leagueId > 0 && Number.isFinite(threshold))
    );
    this.forceDomLeagueIds = new Set(
      (options.forceDomLeagueIds || runtimeConfig.force_dom_league_ids || [])
        .map((id) => Number(id))
        .filter((id) => Number.isInteger(id) && id > 0)
    );
    this.forceMultiModeLeagueIds = new Set(
      (options.forceMultiModeLeagueIds || runtimeConfig.force_multi_mode_league_ids || [])
        .map((id) => Number(id))
        .filter((id) => Number.isInteger(id) && id > 0)
    );
    this.annualLeagueIds = new Set(
      (options.annualLeagueIds || runtimeConfig.annual_league_ids || [])
        .map((id) => Number(id))
        .filter((id) => Number.isInteger(id) && id > 0)
    );
    this.excludeAllLeagueIds = new Set(
      (options.excludeAllLeagueIds || runtimeConfig.exclude_all_league_ids || [])
        .map((id) => Number(id))
        .filter((id) => Number.isInteger(id) && id > 0)
    );
  }

  buildTarget(season, leagueConfig, options = {}) {
    return {
      leagueId: Number(leagueConfig?.id || 0),
      league: leagueConfig,
      readySelector: leagueConfig?.readySelector || leagueConfig?.ready_selector || null,
      season: this.formatSeasonForLeagueUrl(season, leagueConfig),
      dbSeason: this.normalizeDbSeason(season),
      resultsUrl: this.buildResultsUrl(leagueConfig, season),
      currentSeasonOnly: options.currentSeasonOnly === true
    };
  }

  buildCircuitBreakerKey(target) {
    const leagueId = Number(target?.leagueId || target?.league?.id || 0);
    const leagueName = String(target?.league?.name || 'unknown')
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '') || 'unknown';
    const dbSeason = String(target?.dbSeason || '').trim() || 'unknown';
    return `recon:${leagueId || leagueName}:${dbSeason}`;
  }

  orderPendingMatchesForProcessing(pendingMatches = [], now = new Date()) {
    return [...(Array.isArray(pendingMatches) ? pendingMatches : [])]
      .sort((left, right) => comparePendingMatchesForProcessing(left, right, now));
  }

  async buildScanTargets(options = {}) {
    const { season, tier = null, leagueIds = null, currentSeasonOnly = false } = options;

    if (!season || typeof season !== 'string') {
      throw new Error('season is required for buildScanTargets');
    }

    const allowedLeagueIds = Array.isArray(leagueIds) && leagueIds.length > 0
      ? new Set(leagueIds.map((id) => Number(id)))
      : null;

    const leagues = this.configManager
      .getActiveLeagues({ tier })
      .filter((league) => league.enabled !== false)
      .filter((league) => allowedLeagueIds || !this.excludeAllLeagueIds.has(Number(league.id)))
      .filter((league) => !allowedLeagueIds || allowedLeagueIds.has(Number(league.id)));

    return leagues.map((league) => this.buildTarget(season, league, { currentSeasonOnly }));
  }

  async prepareReconPendingTargets(targets, limit = null, options = {}) {
    const prepared = [];
    const lightweightSingleMatchMode = Number.isInteger(limit)
      && limit === 1
      && options.mismatchRetryOnly !== true
      && options.allNonLinked !== true;

    for (const target of targets) {
      const allPendingMatches = await this.loadReconPendingMatches(target, {
        ...options,
        limit: lightweightSingleMatchMode ? null : options.limit
      });
      const pendingMatches = options.mismatchRetryOnly === true
        ? (Array.isArray(allPendingMatches)
          ? allPendingMatches.filter((match) => String(match?.pipeline_status || '').trim().toUpperCase() === 'RECON_MISMATCH')
          : [])
        : allPendingMatches;
      if (Array.isArray(pendingMatches) && pendingMatches.length > 0) {
        const orderedPendingMatches = this.orderPendingMatchesForProcessing(pendingMatches);
        const harvestedCount = orderedPendingMatches
          .filter((match) => String(match?.pipeline_status || '').trim().toUpperCase() === 'HARVESTED')
          .length;
        const mismatchCount = orderedPendingMatches
          .filter((match) => String(match?.pipeline_status || '').trim().toUpperCase() === 'RECON_MISMATCH')
          .length;
        const latestMatchDateTs = orderedPendingMatches.reduce(
          (maxValue, match) => Math.max(maxValue, resolveMatchDateTimestamp(match)),
          0
        );
        const reconPolicy = this.resolveReconPolicy(
          target,
          orderedPendingMatches,
          options.confidenceThreshold,
          { allowMismatchRetry: options.allowMismatchRetry === true }
        );
        prepared.push({
          target: {
            ...target,
            reconPolicy
          },
          pendingMatches: orderedPendingMatches,
          priority: {
            harvestedCount,
            mismatchCount,
            latestMatchDateTs,
            totalPending: orderedPendingMatches.length
          },
          desiredLimit: null
        });
      }
    }

    prepared.sort((left, right) =>
      Number(right?.priority?.harvestedCount || 0) - Number(left?.priority?.harvestedCount || 0)
      || Number(right?.priority?.mismatchCount || 0) - Number(left?.priority?.mismatchCount || 0)
      || Number(right?.priority?.latestMatchDateTs || 0) - Number(left?.priority?.latestMatchDateTs || 0)
      || Number(right?.priority?.totalPending || 0) - Number(left?.priority?.totalPending || 0)
      || String(left?.target?.league?.name || '').localeCompare(String(right?.target?.league?.name || ''))
    );

    if (!Number.isInteger(limit) || limit <= 0) {
      return prepared;
    }

    const capped = prepared.map(({ target, pendingMatches }) => ({
      target,
      pendingMatches,
      desiredLimit: 0
    }));

    let selected = 0;
    let cursor = 0;
    const capacities = prepared.map(({ pendingMatches }) => pendingMatches.length);

    while (selected < limit) {
      let pickedInRound = false;

      for (let index = 0; index < prepared.length && selected < limit; index++) {
        const currentIndex = (cursor + index) % prepared.length;
        if (capped[currentIndex].desiredLimit >= capacities[currentIndex]) {
          continue;
        }

        capped[currentIndex].desiredLimit += 1;
        selected++;
        pickedInRound = true;
      }

      if (!pickedInRound) {
        break;
      }

      cursor = (cursor + 1) % Math.max(prepared.length, 1);
    }

    return capped.filter(({ desiredLimit }) => desiredLimit > 0);
  }

  async loadReconPendingMatches(target, options = {}) {
    if (this.repository && typeof this.repository.getReconEligibleMatches === 'function') {
      return this.repository.getReconEligibleMatches(target.dbSeason, target.league.name, {
        limit: Number.isInteger(options.limit) && options.limit > 0 ? options.limit : null,
        allowMismatchRetry: options.allowMismatchRetry === true,
        allNonLinked: options.allNonLinked === true
      });
    }

    return this.repository.getUnstitchedMatches(target.dbSeason, target.league.name);
  }

  resolveMismatchRetryThresholdFloor(target) {
    const leagueId = Number(target?.leagueId || target?.league?.id || 0);
    if (Number.isInteger(leagueId) && this.mismatchRetryThresholdFloorByLeagueId.has(leagueId)) {
      return Number(this.mismatchRetryThresholdFloorByLeagueId.get(leagueId));
    }

    return Number(this.mismatchRetryThresholdFloor);
  }

  resolveConfidenceThresholdOverride(target) {
    const leagueId = Number(target?.leagueId || target?.league?.id || 0);
    if (Number.isInteger(leagueId) && this.confidenceThresholdOverrideByLeagueId.has(leagueId)) {
      return Number(this.confidenceThresholdOverrideByLeagueId.get(leagueId));
    }

    return null;
  }

  resolveReconPolicy(target, pendingMatches, confidenceThreshold = 0.5, options = {}) {
    const requestedThreshold = Number.isFinite(Number(confidenceThreshold))
      ? Number(confidenceThreshold)
      : 0;
    const configuredRetry = options.allowMismatchRetry === true
      || target?.reconPolicy?.allowMismatchRetry === true;
    const leagueId = Number(target?.leagueId || target?.league?.id || 0);
    const normalizedPendingMatches = Array.isArray(pendingMatches) ? pendingMatches : [];
    const hasMismatchRetry = normalizedPendingMatches
      .some((match) => String(match?.pipeline_status || '').trim().toUpperCase() === 'RECON_MISMATCH');
    const mismatchOnly = normalizedPendingMatches.length > 0
      && normalizedPendingMatches.every((match) => String(match?.pipeline_status || '').trim().toUpperCase() === 'RECON_MISMATCH');
    const thresholdFloor = this.resolveMismatchRetryThresholdFloor(target);
    const thresholdOverride = this.resolveConfidenceThresholdOverride(target);
    const allowExplicitLowerThreshold = configuredRetry
      && mismatchOnly
      && requestedThreshold > 0
      && requestedThreshold < this.minimumConfidenceThreshold;
    const baselineThreshold = allowExplicitLowerThreshold
      ? Math.max(requestedThreshold, thresholdFloor)
      : Number.isFinite(thresholdOverride)
      ? Number(thresholdOverride)
      : Math.max(requestedThreshold, this.minimumConfidenceThreshold);
    const effectiveThreshold = configuredRetry && hasMismatchRetry
      ? Math.max(
        baselineThreshold,
        thresholdFloor,
        requestedThreshold - this.mismatchRetryThresholdDelta
      )
      : baselineThreshold;

    return {
      allowMismatchRetry: configuredRetry,
      hasMismatchRetry,
      effectiveConfidenceThreshold: effectiveThreshold,
      forceMultiMode: this.forceMultiModeLeagueIds.has(leagueId) || (configuredRetry && hasMismatchRetry)
    };
  }

  resolveArchiveMaxPages(_target, pendingMatches = []) {
    const pendingTotal = Array.isArray(pendingMatches) ? pendingMatches.length : 0;
    if (pendingTotal >= this.highVolumePendingThreshold) {
      return this.highVolumeArchiveMaxPages;
    }

    return this.archiveMaxPages;
  }

  selectProcessablePendingMatches(pendingMatches, candidates, confidenceThreshold, matchLimit = null, seasonMirror = null) {
    const orderedPending = this.orderPendingMatchesForProcessing(pendingMatches);

    if (!Number.isInteger(matchLimit) || matchLimit <= 0 || orderedPending.length <= matchLimit) {
      return orderedPending;
    }

    const ranked = orderedPending.map((match) => {
      const candidateMatch = this.matchEvaluator?.findBestCandidate(match, candidates, seasonMirror);
      return {
        match,
        confidence: candidateMatch?.confidence || 0,
        matchDate: match.match_date || null
      };
    });

    const linkedFirst = ranked
      .filter((item) => item.confidence >= confidenceThreshold)
      .sort((left, right) => {
        if (right.confidence !== left.confidence) {
          return right.confidence - left.confidence;
        }

        const rightDate = right.matchDate ? new Date(right.matchDate).getTime() : 0;
        const leftDate = left.matchDate ? new Date(left.matchDate).getTime() : 0;
        if (rightDate !== leftDate) {
          return rightDate - leftDate;
        }

        return String(right.match.match_id).localeCompare(String(left.match.match_id));
      })
      .slice(0, matchLimit)
      .map((item) => item.match);

    if (linkedFirst.length >= matchLimit) {
      return linkedFirst;
    }

    const selectedIds = new Set(linkedFirst.map((item) => item.match_id));
    const fallbackMatches = orderedPending
      .filter((item) => !selectedIds.has(item.match_id))
      .slice(0, matchLimit - linkedFirst.length);

    return [...linkedFirst, ...fallbackMatches];
  }
}

Object.assign(
  ReconTaskPlanner.prototype,
  reconTaskPlannerSourceSelector,
  reconTaskPlannerUrlUtils
);

module.exports = { ReconTaskPlanner };
