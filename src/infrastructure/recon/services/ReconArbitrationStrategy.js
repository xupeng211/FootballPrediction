'use strict';

function clampConfidence(value) {
  return Math.max(0, Math.min(1, Number(value || 0)));
}

function roundConfidence(value) {
  return Number(clampConfidence(value).toFixed(3));
}

function pickFirstNonEmpty(values = []) {
  for (const value of values) {
    const normalized = String(value || '').trim();
    if (normalized) {
      return normalized;
    }
  }

  return '';
}

/**
 * ReconArbitrationStrategy
 *
 * Responsibilities:
 * 1. Absorb source noise before DB persistence.
 * 2. Rank duplicate fixtures with kickoff-aware scoring.
 * 3. Classify safe hash rollover vs. suspicious overwrite.
 *
 * High-risk area:
 * This strategy runs immediately before match_id binding and mapping persistence.
 * A bad decision here becomes a wrong canonical link downstream.
 */
class ReconArbitrationStrategy {
  /**
   * @param {Object} [options]
   * @param {number} [options.teamSimilarityThreshold=0.75]
   * @param {number} [options.kickoffToleranceMs=300000]
   * @param {number} [options.kickoffSoftWindowMs=7200000]
   * @param {number} [options.kickoffHardRejectMs=43200000]
   * @param {Object} [options.logger]
   */
  constructor(options = {}) {
    this.logger = options.logger || { info() {}, warn() {}, error() {} };
    this.teamSimilarityThreshold = Number.isFinite(Number(options.teamSimilarityThreshold))
      ? Number(options.teamSimilarityThreshold)
      : 0.75;
    this.kickoffToleranceMs = Number.isFinite(Number(options.kickoffToleranceMs))
      ? Number(options.kickoffToleranceMs)
      : 5 * 60 * 1000;
    this.kickoffSoftWindowMs = Number.isFinite(Number(options.kickoffSoftWindowMs))
      ? Number(options.kickoffSoftWindowMs)
      : 2 * 60 * 60 * 1000;
    this.kickoffHardRejectMs = Number.isFinite(Number(options.kickoffHardRejectMs))
      ? Number(options.kickoffHardRejectMs)
      : 12 * 60 * 60 * 1000;
  }

  /**
   * @param {string|Date|null} value
   * @returns {number|null}
   */
  toTimestamp(value) {
    const timestamp = new Date(value || '').getTime();
    return Number.isFinite(timestamp) ? timestamp : null;
  }

  /**
   * @param {string|Date|null} sourceDate
   * @param {string|Date|null} candidateDate
   * @returns {{known: boolean, diffMs: number|null, withinTolerance: boolean, withinSoftWindow: boolean, hardReject: boolean}}
   */
  evaluateKickoffDelta(sourceDate, candidateDate) {
    const sourceTs = this.toTimestamp(sourceDate);
    const candidateTs = this.toTimestamp(candidateDate);

    if (sourceTs === null || candidateTs === null) {
      return {
        known: false,
        diffMs: null,
        withinTolerance: false,
        withinSoftWindow: false,
        hardReject: false
      };
    }

    const diffMs = Math.abs(sourceTs - candidateTs);
    return {
      known: true,
      diffMs,
      withinTolerance: diffMs <= this.kickoffToleranceMs,
      withinSoftWindow: diffMs <= this.kickoffSoftWindowMs,
      hardReject: diffMs > this.kickoffHardRejectMs
    };
  }

  /**
   * @param {{known: boolean, withinTolerance: boolean, withinSoftWindow: boolean, diffMs: number|null}} kickoff
   * @returns {number|null}
   */
  resolveKickoffScore(kickoff) {
    if (!kickoff.known) {
      return null;
    }

    if (kickoff.withinTolerance) {
      return 1;
    }

    if (kickoff.withinSoftWindow) {
      return 0.92;
    }

    return 0.45;
  }

  /**
   * @param {string} fallbackMethod
   * @param {{known: boolean, withinTolerance: boolean, withinSoftWindow: boolean, diffMs: number|null}} kickoff
   * @returns {string}
   */
  resolveKickoffMethod(fallbackMethod, kickoff) {
    if (kickoff.known && kickoff.withinTolerance && kickoff.diffMs > 0) {
      return `${fallbackMethod}_kickoff_tolerance`;
    }

    if (kickoff.known && kickoff.withinSoftWindow && kickoff.diffMs > this.kickoffToleranceMs) {
      return `${fallbackMethod}_kickoff_window`;
    }

    return fallbackMethod;
  }

  /**
   * @param {Object} input
   * @param {Object} [input.match]
   * @param {Object} [input.leagueConfig]
   * @param {Object|null} [input.existingMapping]
   * @returns {string}
   */
  resolveLeagueName({ match = {}, leagueConfig = {}, existingMapping = null }) {
    return pickFirstNonEmpty([
      leagueConfig?.name,
      match?.leagueName,
      match?.league_name,
      existingMapping?.league_name,
      'Unknown League'
    ]);
  }

  /**
   * @param {Object} input
   * @param {Object} input.sourceMatch
   * @param {Object} input.candidateMatch
   * @param {string} input.homeTeam
   * @param {string} input.awayTeam
   * @param {Function} input.similarityFn
   * @param {string} [input.fallbackMethod='exact']
   * @returns {Object|null}
   */
  scoreCandidateMatch({
    sourceMatch,
    candidateMatch,
    homeTeam,
    awayTeam,
    similarityFn,
    fallbackMethod = 'exact'
  }) {
    const directHome = similarityFn(homeTeam, candidateMatch.home_team);
    const directAway = similarityFn(awayTeam, candidateMatch.away_team);
    const reverseHome = similarityFn(homeTeam, candidateMatch.away_team);
    const reverseAway = similarityFn(awayTeam, candidateMatch.home_team);

    const directScore = (directHome + directAway) / 2;
    const reverseScore = (reverseHome + reverseAway) / 2;
    const orientationScore = Math.max(directScore, reverseScore);

    if (orientationScore < this.teamSimilarityThreshold) {
      return null;
    }

    const kickoff = this.evaluateKickoffDelta(
      sourceMatch?.matchDate || sourceMatch?.date || sourceMatch?.match_date,
      candidateMatch?.match_date
    );

    if (kickoff.hardReject) {
      return null;
    }

    const kickoffScore = this.resolveKickoffScore(kickoff);

    const score = kickoffScore === null
      ? orientationScore
      : ((orientationScore * 0.8) + (kickoffScore * 0.2));
    const method = this.resolveKickoffMethod(fallbackMethod, kickoff);

    return {
      matchId: candidateMatch.match_id,
      dbHome: candidateMatch.home_team,
      dbAway: candidateMatch.away_team,
      matchDate: candidateMatch.match_date || null,
      confidence: roundConfidence(score),
      method,
      kickoffDeltaMs: kickoff.diffMs,
      orientationScore: roundConfidence(orientationScore)
    };
  }

  /**
   * @param {Object} input
   * @param {Object} input.sourceMatch
   * @param {Object[]} input.candidates
   * @param {string} input.homeTeam
   * @param {string} input.awayTeam
   * @param {Function} input.similarityFn
   * @param {string} [input.fallbackMethod='exact']
   * @returns {Object|null}
   */
  chooseBestMatchCandidate({
    sourceMatch = {},
    candidates = [],
    homeTeam,
    awayTeam,
    similarityFn,
    fallbackMethod = 'exact'
  }) {
    const ranked = candidates
      .map((candidateMatch) => this.scoreCandidateMatch({
        sourceMatch,
        candidateMatch,
        homeTeam,
        awayTeam,
        similarityFn,
        fallbackMethod
      }))
      .filter(Boolean)
      .sort((left, right) => {
        if (right.confidence !== left.confidence) {
          return right.confidence - left.confidence;
        }

        const leftKickoff = Number.isFinite(left.kickoffDeltaMs) ? left.kickoffDeltaMs : Number.MAX_SAFE_INTEGER;
        const rightKickoff = Number.isFinite(right.kickoffDeltaMs) ? right.kickoffDeltaMs : Number.MAX_SAFE_INTEGER;
        if (leftKickoff !== rightKickoff) {
          return leftKickoff - rightKickoff;
        }

        return String(left.matchId).localeCompare(String(right.matchId));
      });

    if (ranked.length === 0) {
      return null;
    }

    const sourceHasKickoff = this.toTimestamp(
      sourceMatch?.matchDate || sourceMatch?.date || sourceMatch?.match_date
    ) !== null;
    if (!sourceHasKickoff && ranked.length > 1) {
      const best = ranked[0];
      const runnerUp = ranked[1];
      if (Math.abs(best.confidence - runnerUp.confidence) < 0.02) {
        this.logger.warn('stitch_candidate_ambiguous_without_kickoff', {
          bestMatchId: String(best.matchId),
          runnerUpMatchId: String(runnerUp.matchId),
          bestConfidence: best.confidence,
          runnerUpConfidence: runnerUp.confidence
        });
        return null;
      }
    }

    return ranked[0];
  }

  /**
   * @param {Object} match
   * @param {Object} leagueConfig
   * @returns {string[]}
   */
  collectDegradedFields(match, leagueConfig) {
    const degradedFields = [];

    if (!String(leagueConfig?.name || '').trim()) {
      degradedFields.push('league_name');
    }
    if (this.toTimestamp(match?.matchDate || match?.date || match?.match_date) === null) {
      degradedFields.push('match_date');
    }

    return degradedFields;
  }

  /**
   * @param {Object} existingMapping
   * @param {Object} match
   * @returns {{changed: boolean, previousHash: string|null, incomingHash: string|null}}
   */
  buildHashLifecycle(existingMapping, match) {
    return {
      changed: Boolean(
        existingMapping?.oddsportal_hash
        && match?.hash
        && String(existingMapping.oddsportal_hash) !== String(match.hash)
      ),
      previousHash: existingMapping?.oddsportal_hash ? String(existingMapping.oddsportal_hash) : null,
      incomingHash: match?.hash ? String(match.hash) : null
    };
  }

  /**
   * @param {Object} input
   * @param {Object} input.match
   * @param {Object} input.matchInfo
   * @param {Object} input.leagueConfig
   * @param {Object|null} input.existingMapping
   * @returns {{leagueName: string, mappingMethod: string, matchConfidence: number, degradedFields: string[], hashLifecycle: Object, kickoffDeltaMs: number|null}}
   */
  buildMappingDecision({ match = {}, matchInfo = {}, leagueConfig = {}, existingMapping = null }) {
    const leagueName = this.resolveLeagueName({ match, leagueConfig, existingMapping });
    const degradedFields = this.collectDegradedFields(match, leagueConfig);
    const hashLifecycle = this.buildHashLifecycle(existingMapping, match);
    const kickoff = this.evaluateKickoffDelta(
      match?.matchDate || match?.date || match?.match_date,
      matchInfo?.matchDate || matchInfo?.match_date
    );

    return {
      leagueName,
      mappingMethod: hashLifecycle.changed
        ? 'sequential_hash_rollover'
        : String(matchInfo.method || 'exact'),
      matchConfidence: roundConfidence(
        Number.isFinite(Number(matchInfo.confidence))
          ? Number(matchInfo.confidence)
          : 0.75
      ),
      degradedFields,
      hashLifecycle,
      kickoffDeltaMs: kickoff.diffMs
    };
  }
}

module.exports = { ReconArbitrationStrategy };
