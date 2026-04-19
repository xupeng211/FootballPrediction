/* eslint-disable complexity */
'use strict';

const { Normalizer } = require('../../../utils/Normalizer');
const { getReconConfigSection } = require('./ReconServiceConfig');

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

function resolveFiniteNumber(...values) {
  for (const value of values) {
    const normalized = Number(value);
    if (Number.isFinite(normalized)) {
      return normalized;
    }
  }

  return null;
}

function buildCandidateNormalizationPayload(candidate, l1Match, target, rawUrl, fallbackSlug) {
  const matchDate = candidate.matchDate || candidate.match_date || l1Match?.match_date || null;
  const homeTeam = candidate.homeTeam || l1Match?.home_team || '';
  const awayTeam = candidate.awayTeam || l1Match?.away_team || '';

  return {
    match_id: l1Match?.match_id || '',
    matchDate: matchDate,
    match_date: matchDate,
    hash: candidate.hash,
    eventId: candidate.hash,
    encodeEventId: candidate.hash,
    homeTeam: homeTeam,
    awayTeam: awayTeam,
    'home-name': l1Match?.home_team || homeTeam,
    'away-name': l1Match?.away_team || awayTeam,
    league_id: Number(target?.league?.id || 0) || undefined,
    countrySlug: target?.league?.country || '',
    leagueSlug: target?.league?.slug || '',
    slug: fallbackSlug,
    url: rawUrl
  };
}

const reconResultStitcher = {
  _resolveScopedPendingMatches(pendingMatches, matchLimit, candidates, confidenceThreshold, seasonMirror = null) {
    const orderedPending = [...(Array.isArray(pendingMatches) ? pendingMatches : [])]
      .sort((a, b) => String(a.match_id).localeCompare(String(b.match_id)));

    if (!Number.isInteger(matchLimit) || matchLimit <= 0 || orderedPending.length <= matchLimit) {
      return orderedPending;
    }

    if (Array.isArray(candidates) && candidates.length > 0) {
      return this.taskPlanner.selectProcessablePendingMatches(
        orderedPending,
        candidates,
        confidenceThreshold,
        matchLimit,
        seasonMirror
      );
    }

    return orderedPending.slice(0, Math.min(matchLimit, orderedPending.length));
  },

  async _processPendingMatchesWithShortCircuit(routeKind, routeSource, pendingMatches, target, options = {}) {
    const {
      confidenceThreshold = this.confidenceThreshold,
      limiter,
      persistLimiter,
      progress = null,
      metadata = {},
      finalPass = false,
      forceProcessWithoutCandidates = false
    } = options;

    const candidates = Array.isArray(routeSource?.candidates) ? routeSource.candidates : [];
    const canProcessMatches = candidates.length > 0 || forceProcessWithoutCandidates === true;
    if (!canProcessMatches) {
      this.logger.info('recon_route_short_circuit', {
        league: target?.league?.name || null,
        season: target?.dbSeason || null,
        routeKind,
        pendingTotal: pendingMatches.length,
        linked: 0,
        mismatched: 0,
        remainingPending: pendingMatches.length,
        sourceState: routeSource?.extractResult?.sourceState || 'SOURCE_EMPTY',
        finalPass
      });
      return {
        linked: 0,
        mismatched: 0,
        remainingPending: [...pendingMatches]
      };
    }

    const seasonMirror = routeSource?.seasonMirror || this.mirrorManager.buildSeasonMirror(candidates);
    const runtimeTargetWithSource = {
      ...target,
      reconSourceUrl: routeSource?.source?.url || target.resultsUrl,
      reconSourceSeason: routeSource?.source?.season || this.taskPlanner.formatSeasonForUrl(target.season)
    };
    const unresolvedMatches = [];
    let linked = 0;
    let mismatched = 0;

    await Promise.all(
      pendingMatches.map((l1Match) => limiter(async () => {
        const outcome = await this._reconcilePendingMatch(
          l1Match,
          candidates,
          runtimeTargetWithSource,
          confidenceThreshold,
          seasonMirror
        );

        if (outcome?.status === 'linked' && outcome.mapping) {
          const persistResult = await persistLimiter(() => this._persistReconOutcomeImmediately(outcome, {
            ...metadata,
            sourceSeason: runtimeTargetWithSource.reconSourceSeason,
            sourceUrl: runtimeTargetWithSource.reconSourceUrl
          }));
          linked += Number(persistResult?.linked || 0);
          if (progress) {
            progress.processed++;
            progress.linked += Number(persistResult?.linked || 0);
            if (this._shouldEmitReconProgressSnapshot(progress)) {
              this._emitReconProgressSnapshot(target, progress);
            }
          }
          return;
        }

        if (finalPass) {
          const persistResult = await persistLimiter(() => this._persistReconOutcomeImmediately(outcome, {
            ...metadata,
            sourceSeason: runtimeTargetWithSource.reconSourceSeason,
            sourceUrl: runtimeTargetWithSource.reconSourceUrl
          }));
          mismatched += Number(persistResult?.mismatched || 0);
          if (progress) {
            progress.processed++;
            progress.mismatched += Number(persistResult?.mismatched || 0);
            if (this._shouldEmitReconProgressSnapshot(progress)) {
              this._emitReconProgressSnapshot(target, progress);
            }
          }
          return;
        }

        unresolvedMatches.push(l1Match);
      }))
    );

    const orderedRemainingPending = unresolvedMatches
      .sort((left, right) => String(left?.match_id || '').localeCompare(String(right?.match_id || '')));

    this.logger.info('recon_route_short_circuit', {
      league: target?.league?.name || null,
      season: target?.dbSeason || null,
      routeKind,
      pendingTotal: pendingMatches.length,
      linked,
      mismatched,
      remainingPending: orderedRemainingPending.length,
      sourceState: routeSource?.extractResult?.sourceState || 'SOURCE_EMPTY',
      finalPass
    });

    return {
      linked,
      mismatched,
      remainingPending: orderedRemainingPending
    };
  },

  async _reconcilePendingMatch(l1Match, candidates, target, confidenceThreshold, seasonMirror = null) {
    let candidateMatch = this._findBestCandidate(l1Match, candidates, seasonMirror);
    const mismatchRetryMode = String(l1Match?.pipeline_status || '').trim().toUpperCase() === 'RECON_MISMATCH';
    if ((!candidateMatch || candidateMatch.confidence < confidenceThreshold) && mismatchRetryMode) {
      const fuzzyRetryCandidate = this._findBestMismatchRetryCandidate(l1Match, candidates);
      if (
        fuzzyRetryCandidate
        && (
          !candidateMatch
          || !this._isMismatchRetryCandidateEligible(candidateMatch)
          || fuzzyRetryCandidate.confidence > candidateMatch.confidence
        )
      ) {
        candidateMatch = fuzzyRetryCandidate;
      }

      const localDictionaryCandidate = this._buildLocalDictionaryCandidate(l1Match, target);
      if (localDictionaryCandidate) {
        const localDictionaryMatch = this._findBestCandidate(l1Match, [localDictionaryCandidate], null);
        if (localDictionaryMatch && (!candidateMatch || localDictionaryMatch.confidence > candidateMatch.confidence)) {
          candidateMatch = localDictionaryMatch;
        }
      }
    }

    const mismatchRetryPromoted = this._isMismatchRetryCandidateEligible(candidateMatch);
    if (!candidateMatch || (candidateMatch.confidence < confidenceThreshold && !mismatchRetryPromoted)) {
      return {
        status: 'mismatch',
        matchId: l1Match.match_id,
        evidence: this._buildMismatchEvidence(l1Match, candidateMatch, target)
      };
    }

    if (mismatchRetryMode && mismatchRetryPromoted && candidateMatch.confidence < confidenceThreshold) {
      this.logger.info('recon_mismatch_retry_promoted', {
        match_id: String(l1Match?.match_id || ''),
        league: target?.league?.name || null,
        season: target?.dbSeason || null,
        confidence: Number(candidateMatch.confidence || 0),
        confidenceThreshold,
        selectedMinScore: Number(candidateMatch.selectedMinScore || 0),
        dateDeltaMs: Number.isFinite(Number(candidateMatch.dateDeltaMs)) ? Number(candidateMatch.dateDeltaMs) : null
      });
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

  _getMismatchRetrySettings() {
    const runtimeConfig = getReconConfigSection(['recon_runtime', 'match_evaluator'], {});
    return {
      fuzzyConfidenceFloor: resolveFiniteNumber(
        this.mismatchRetryFuzzyConfidenceFloor,
        runtimeConfig.mismatch_retry_fuzzy_confidence_floor,
        0.7
      ),
      maxTeamScoreGap: Math.max(0, resolveFiniteNumber(
        this.mismatchRetryMaxTeamScoreGap,
        runtimeConfig.mismatch_retry_max_team_score_gap,
        0.08
      )),
      maxKickoffDeltaMs: Math.max(0, resolveFiniteNumber(
        this.mismatchRetryMaxKickoffDeltaMs,
        runtimeConfig.mismatch_retry_max_kickoff_delta_ms,
        2 * 60 * 60 * 1000
      )),
      teamSimilarityFloor: resolveFiniteNumber(
        this.mismatchRetryTeamSimilarityFloor,
        runtimeConfig.mismatch_retry_team_similarity_floor,
        0.68
      )
    };
  },

  _isMismatchRetryCandidateEligible(candidateMatch) {
    if (!candidateMatch) {
      return false;
    }

    const settings = this._getMismatchRetrySettings();
    const confidence = Number(candidateMatch.confidence || 0);
    const selectedAverageScore = Number(candidateMatch.selectedAverageScore || 0);
    const selectedMinScore = Number(candidateMatch.selectedMinScore || 0);
    const dateDeltaMs = resolveFiniteNumber(candidateMatch.dateDeltaMs);

    if (confidence < settings.fuzzyConfidenceFloor) {
      return false;
    }

    if (selectedMinScore < settings.teamSimilarityFloor) {
      return false;
    }

    if ((selectedAverageScore - selectedMinScore) > settings.maxTeamScoreGap) {
      return false;
    }

    if (dateDeltaMs === null) {
      return false;
    }

    return dateDeltaMs <= settings.maxKickoffDeltaMs;
  },

  _findBestMismatchRetryCandidate(l1Match, candidates = []) {
    if (!Array.isArray(candidates) || candidates.length === 0) {
      return null;
    }

    let best = null;
    for (const candidate of candidates) {
      const evaluation = typeof this.matchEvaluator?.evaluateCandidate === 'function'
        ? this.matchEvaluator.evaluateCandidate(candidate, l1Match)
        : null;
      if (!this._isMismatchRetryCandidateEligible(evaluation)) {
        continue;
      }

      if (!best || evaluation.confidence > best.confidence) {
        best = evaluation;
      }
    }

    return best;
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

  _buildRouteProbeSample(pendingMatches = []) {
    const orderedPending = [...(Array.isArray(pendingMatches) ? pendingMatches : [])]
      .sort((left, right) => String(left?.match_id || '').localeCompare(String(right?.match_id || '')));
    const eligiblePending = typeof this.taskPlanner?.filterPlaceholderFixtures === 'function'
      ? this.taskPlanner.filterPlaceholderFixtures(orderedPending)
      : orderedPending;
    const sampleSize = Math.max(1, Number(this.taskPlanner?.sampleSize || eligiblePending.length || 1));

    return eligiblePending.slice(0, Math.min(sampleSize, eligiblePending.length));
  },

  _scoreCandidatePoolSample(pendingMatches = [], candidates = [], confidenceThreshold = this.confidenceThreshold, seasonMirror = null) {
    const sample = this._buildRouteProbeSample(pendingMatches);
    if (sample.length === 0 || !Array.isArray(candidates) || candidates.length === 0) {
      return 0;
    }

    return sample.reduce((count, l1Match) => {
      const matched = this._findBestCandidate(l1Match, candidates, seasonMirror);
      return matched && matched.confidence >= confidenceThreshold ? count + 1 : count;
    }, 0);
  },

  _shouldCanonicalizeCandidateUrl(url) {
    const rawUrl = String(url || '').trim();
    return !rawUrl || /\/football\/h2h\//iu.test(rawUrl) || /\/match\/[^/]+\/?$/iu.test(rawUrl);
  },

  _resolveCandidateSourceUrls(candidate = {}, target = {}) {
    const normalizationCandidates = this._splitSourceUrls(
      candidate?.sourceUrl
      || candidate?.source_url
      || target?.reconSourceUrl
      || target?.resultsUrl
      || ''
    );

    return normalizationCandidates.length > 0
      ? normalizationCandidates
      : [this._resolveTrustedOddsPortalBaseUrl()];
  },

  _createCandidateNormalizationContext(sourceUrl) {
    return {
      ...this.matchExtractor,
      baseUrl: this._resolveTrustedOddsPortalBaseUrl(),
      sourceUrl,
      resultsUrl: sourceUrl,
      leagueUrl: sourceUrl,
      extractMaxDepth: 5
    };
  },

  _findCanonicalCandidateNormalization(candidateMatch, l1Match, target, rawUrl, candidateSourceUrls, fallbackSlug) {
    const candidate = candidateMatch?.candidate || {};

    for (const sourceUrl of candidateSourceUrls) {
      const normalized = this.matchExtractor.normalizeMatchObject.call(
        this._createCandidateNormalizationContext(sourceUrl),
        buildCandidateNormalizationPayload(candidate, l1Match, target, rawUrl, fallbackSlug),
        'recon_matrix_preflight'
      );

      if (!normalized?.url || !this._isCanonicalEventUrl(normalized.url, candidate.hash)) {
        continue;
      }

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

    return null;
  },

  _warnRejectedCandidateNormalization(l1Match, target, candidate, rawUrl) {
    this.logger.warn('rejected_due_to_h2h_url', {
      match_id: String(l1Match?.match_id || ''),
      season: String(target?.dbSeason || ''),
      oddsportal_hash: String(candidate?.hash || ''),
      full_url: rawUrl,
      candidate_source_url: String(target?.reconSourceUrl || target?.resultsUrl || ''),
      reason: 'preflight_canonical_url_missing'
    });
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

    const candidateSourceUrls = this._resolveCandidateSourceUrls(candidate, target);
    const fallbackSlug = this._buildFallbackEventSlug(l1Match?.home_team, l1Match?.away_team);
    const normalizedCandidateMatch = this._findCanonicalCandidateNormalization(
      candidateMatch,
      l1Match,
      target,
      rawUrl,
      candidateSourceUrls,
      fallbackSlug
    );

    if (normalizedCandidateMatch) {
      return normalizedCandidateMatch;
    }

    this._warnRejectedCandidateNormalization(l1Match, target, candidate, rawUrl);
    return null;
  },

  _escapeRegExp(value) {
    return String(value || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  },

  _buildFallbackEventSlug(homeTeam, awayTeam) {
    const slugify = (value) => String(Normalizer.normalizeTeamName(value) || value || '')
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
  }
};

module.exports = { reconResultStitcher };
