'use strict';

function buildOrientationFrame(teamSimilarity, candidateHome, candidateAway, l1Home, l1Away, swapped = false) {
  const homeTarget = swapped ? l1Away : l1Home;
  const awayTarget = swapped ? l1Home : l1Away;
  const identityConflict = teamSimilarity.hasIdentityHardConflict(candidateHome, homeTarget)
    || teamSimilarity.hasIdentityHardConflict(candidateAway, awayTarget);
  const homeScore = identityConflict ? 0 : teamSimilarity.calculateSimilarity(candidateHome, homeTarget);
  const awayScore = identityConflict ? 0 : teamSimilarity.calculateSimilarity(candidateAway, awayTarget);
  const comparableHome = teamSimilarity.resolveComparableTeamName(candidateHome);
  const comparableAway = teamSimilarity.resolveComparableTeamName(candidateAway);

  return {
    dictionaryMatch: !identityConflict
      && teamSimilarity.isDictionaryExactMatch(candidateHome, homeTarget)
      && teamSimilarity.isDictionaryExactMatch(candidateAway, awayTarget),
    homeScore,
    awayScore,
    identityConflict,
    minScore: Math.min(homeScore, awayScore),
    normalizedMatch: !identityConflict
      && teamSimilarity.isComparableNameEquivalent(comparableHome, homeTarget)
      && teamSimilarity.isComparableNameEquivalent(comparableAway, awayTarget),
    score: (homeScore + awayScore) / 2
  };
}

function isOrientationMatch(frame, threshold) {
  return frame.dictionaryMatch
    || frame.normalizedMatch
    || (frame.homeScore > threshold && frame.awayScore > threshold);
}

function buildOrientationResult(teamSimilarity, candidate, l1Match, threshold) {
  const candidateHome = candidate?.homeTeam || '';
  const candidateAway = candidate?.awayTeam || '';
  const l1Home = l1Match?.home_team || '';
  const l1Away = l1Match?.away_team || '';
  const direct = buildOrientationFrame(teamSimilarity, candidateHome, candidateAway, l1Home, l1Away, false);
  const swapped = buildOrientationFrame(teamSimilarity, candidateHome, candidateAway, l1Home, l1Away, true);
  const directMatch = isOrientationMatch(direct, threshold);
  const swappedMatch = isOrientationMatch(swapped, threshold);
  const isReversed = swappedMatch && (
    !directMatch
    || swapped.score > direct.score
    || (swapped.dictionaryMatch && !direct.dictionaryMatch)
    || (swapped.normalizedMatch && !direct.normalizedMatch)
  );

  return {
    directMatch,
    swappedMatch,
    directMinScore: direct.minScore,
    directScore: direct.score,
    swappedScore: swapped.score,
    swappedMinScore: swapped.minScore,
    directNormalized: direct.normalizedMatch,
    swappedNormalized: swapped.normalizedMatch,
    directIdentityConflict: direct.identityConflict,
    swappedIdentityConflict: swapped.identityConflict,
    isReversed,
    dictionaryLocked: direct.dictionaryMatch || swapped.dictionaryMatch
  };
}

function selectIdentityConflict(orientation) {
  if (orientation.isReversed) {
    return orientation.swappedIdentityConflict;
  }

  return orientation.directScore >= orientation.swappedScore
    ? orientation.directIdentityConflict
    : orientation.swappedIdentityConflict;
}

function resolveSelectedOrientation(orientation) {
  if (orientation.isReversed) {
    return {
      averageScore: orientation.swappedScore,
      minScore: orientation.swappedMinScore,
      identityConflict: orientation.swappedIdentityConflict
    };
  }

  if (orientation.directScore >= orientation.swappedScore) {
    return {
      averageScore: orientation.directScore,
      minScore: orientation.directMinScore,
      identityConflict: orientation.directIdentityConflict
    };
  }

  return {
    averageScore: orientation.swappedScore,
    minScore: orientation.swappedMinScore,
    identityConflict: orientation.swappedIdentityConflict
  };
}

function calculateTeamConfidence(orientation, teamBalanceWeight) {
  const selected = resolveSelectedOrientation(orientation);
  return clampConfidence(
    (selected.averageScore * (1 - teamBalanceWeight))
    + (selected.minScore * teamBalanceWeight)
  );
}

function clampConfidence(value) {
  return Math.max(0, Math.min(1, value));
}

function applyHardDateMismatchCap(confidence, dateDeltaMs, hardDateMismatchWindowMs, hardDateMismatchConfidenceCap) {
  if (!Number.isFinite(dateDeltaMs)) {
    return confidence;
  }

  if (!Number.isFinite(hardDateMismatchWindowMs) || hardDateMismatchWindowMs <= 0) {
    return confidence;
  }

  if (dateDeltaMs <= hardDateMismatchWindowMs) {
    return confidence;
  }

  const cap = Number.isFinite(hardDateMismatchConfidenceCap)
    ? hardDateMismatchConfidenceCap
    : 0.49;
  return Math.min(confidence, clampConfidence(cap));
}

function applyWeakTeamAlignmentCap(
  confidence,
  teamConfidence,
  orientation,
  weakSideTeamSimilarityFloor,
  weakSideMaxTeamScoreGap
) {
  if (
    orientation?.dictionaryLocked
    || orientation?.directNormalized
    || orientation?.swappedNormalized
  ) {
    return confidence;
  }

  const selected = resolveSelectedOrientation(orientation);
  const minScore = Number(selected?.minScore);
  const averageScore = Number(selected?.averageScore);
  const hasWeakSideFloor = Number.isFinite(weakSideTeamSimilarityFloor) && weakSideTeamSimilarityFloor >= 0;
  const hasMaxGap = Number.isFinite(weakSideMaxTeamScoreGap) && weakSideMaxTeamScoreGap >= 0;
  const scoreGap = Number.isFinite(averageScore) && Number.isFinite(minScore)
    ? averageScore - minScore
    : null;
  const shouldCap =
    (hasWeakSideFloor && Number.isFinite(minScore) && minScore < weakSideTeamSimilarityFloor)
    || (hasMaxGap && Number.isFinite(scoreGap) && scoreGap > weakSideMaxTeamScoreGap);

  if (!shouldCap) {
    return confidence;
  }

  return Math.min(confidence, clampConfidence(teamConfidence));
}

function calculateConfidence({
  dateDeltaMs,
  dateConfidence,
  dateWeight,
  hardDateMismatchConfidenceCap,
  hardDateMismatchWindowMs,
  orientation,
  placeholderFixture,
  weakSideMaxTeamScoreGap,
  weakSideTeamSimilarityFloor,
  teamBalanceWeight,
  teamWeight
}) {
  const selected = resolveSelectedOrientation(orientation);
  const selectedIdentityConflict = selected.identityConflict ?? selectIdentityConflict(orientation);
  if (selectedIdentityConflict) {
    return 0;
  }

  if (placeholderFixture && (orientation.directNormalized || orientation.swappedNormalized)) {
    return 1.0;
  }

  if (orientation.dictionaryLocked) {
    return applyHardDateMismatchCap(
      1.0,
      dateDeltaMs,
      hardDateMismatchWindowMs,
      hardDateMismatchConfidenceCap
    );
  }

  const teamConfidence = calculateTeamConfidence(orientation, teamBalanceWeight);
  const rawConfidence = dateConfidence === null
    ? teamConfidence
    : clampConfidence((teamConfidence * teamWeight) + (dateConfidence * dateWeight));
  const weakTeamCappedConfidence = applyWeakTeamAlignmentCap(
    rawConfidence,
    teamConfidence,
    orientation,
    weakSideTeamSimilarityFloor,
    weakSideMaxTeamScoreGap
  );
  return applyHardDateMismatchCap(
    weakTeamCappedConfidence,
    dateDeltaMs,
    hardDateMismatchWindowMs,
    hardDateMismatchConfidenceCap
  );
}

function resolveMatchMethod(confidence, dictionaryLocked, exactMatchThreshold) {
  if (dictionaryLocked) {
    return 'dictionary';
  }

  return confidence >= exactMatchThreshold ? 'exact' : 'fuzzy';
}

function resolveDateDeltaMs(candidateDate, matchDate) {
  const candidate = new Date(candidateDate);
  const target = new Date(matchDate);

  if (Number.isNaN(candidate.getTime()) || Number.isNaN(target.getTime())) {
    return null;
  }

  return Math.abs(candidate.getTime() - target.getTime());
}

function evaluateCandidateScore(engine, candidate, l1Match, placeholderFixture) {
  const resolvedCandidate = engine.teamSimilarity.resolveCandidateTeams(candidate, l1Match);
  if (!resolvedCandidate?.homeTeam || !resolvedCandidate?.awayTeam) {
    return null;
  }

  const orientation = engine.evaluateCandidateOrientation(resolvedCandidate, l1Match);
  if (placeholderFixture && !(orientation.directNormalized || orientation.swappedNormalized)) {
    return null;
  }

  const dateConfidence = engine.calculateDateConfidence(
    candidate.matchDate || candidate.match_date,
    l1Match.match_date
  );
  const dateDeltaMs = engine.calculateKickoffDeltaMs(
    candidate.matchDate || candidate.match_date,
    l1Match.match_date
  );
  const selectedOrientation = resolveSelectedOrientation(orientation);
  const teamConfidence = calculateTeamConfidence(orientation, engine.teamBalanceWeight);
  const confidence = calculateConfidence({
    dateDeltaMs,
    dateConfidence,
    dateWeight: engine.dateWeight,
    hardDateMismatchConfidenceCap: engine.hardDateMismatchConfidenceCap,
    hardDateMismatchWindowMs: engine.hardDateMismatchWindowMs,
    orientation,
    placeholderFixture,
    weakSideMaxTeamScoreGap: engine.weakSideMaxTeamScoreGap,
    weakSideTeamSimilarityFloor: engine.weakSideTeamSimilarityFloor,
    teamBalanceWeight: engine.teamBalanceWeight,
    teamWeight: engine.teamWeight
  });

  return {
    candidate: resolvedCandidate,
    confidence,
    dateConfidence,
    dateDeltaMs,
    method: resolveMatchMethod(confidence, orientation.dictionaryLocked, engine.exactMatchThreshold),
    orientation,
    isReversed: orientation.isReversed,
    selectedAverageScore: selectedOrientation.averageScore,
    selectedIdentityConflict: selectedOrientation.identityConflict,
    selectedMinScore: selectedOrientation.minScore,
    teamConfidence
  };
}

class ReconScoringEngine {
  constructor(options = {}) {
    this.teamSimilarity = options.teamSimilarity;
    this.mirrorManager = options.mirrorManager || null;
    this.orientationSimilarityThreshold = Number(options.orientationSimilarityThreshold);
    this.exactMatchThreshold = Number(options.exactMatchThreshold);
    this.teamWeight = Number(options.teamWeight);
    this.dateWeight = Number(options.dateWeight);
    this.teamBalanceWeight = Number.isFinite(Number(options.teamBalanceWeight))
      ? Number(options.teamBalanceWeight)
      : 0.5;
    this.hardDateMismatchWindowMs = Number.isFinite(Number(options.hardDateMismatchWindowMs))
      ? Number(options.hardDateMismatchWindowMs)
      : 48 * 60 * 60 * 1000;
    this.hardDateMismatchConfidenceCap = Number.isFinite(Number(options.hardDateMismatchConfidenceCap))
      ? Number(options.hardDateMismatchConfidenceCap)
      : 0.49;
    this.weakSideTeamSimilarityFloor = Number.isFinite(Number(options.weakSideTeamSimilarityFloor))
      ? Number(options.weakSideTeamSimilarityFloor)
      : 0.68;
    this.weakSideMaxTeamScoreGap = Number.isFinite(Number(options.weakSideMaxTeamScoreGap))
      ? Number(options.weakSideMaxTeamScoreGap)
      : 0.08;
    this.perfectKickoffWindowMs = Number.isFinite(Number(options.perfectKickoffWindowMs))
      ? Number(options.perfectKickoffWindowMs)
      : 2 * 60 * 60 * 1000;
    this.dateConfidenceBands = Array.isArray(options.dateConfidenceBands)
      ? options.dateConfidenceBands
      : [];
  }

  setMirrorManager(mirrorManager) {
    this.mirrorManager = mirrorManager || null;
    return this;
  }

  evaluateCandidateOrientation(candidate, l1Match) {
    return buildOrientationResult(
      this.teamSimilarity,
      candidate,
      l1Match,
      this.orientationSimilarityThreshold
    );
  }

  evaluateCandidate(candidate, l1Match) {
    const placeholderFixture = this.teamSimilarity.isPlaceholderFixture(l1Match);
    return evaluateCandidateScore(this, candidate, l1Match, placeholderFixture);
  }

  calculateKickoffDeltaMs(candidateDate, matchDate) {
    return resolveDateDeltaMs(candidateDate, matchDate);
  }

  calculateDateConfidence(candidateDate, matchDate) {
    const diffMs = this.calculateKickoffDeltaMs(candidateDate, matchDate);
    if (diffMs === null) {
      return null;
    }

    if (diffMs <= this.perfectKickoffWindowMs) {
      return 1;
    }

    const diffDays = diffMs / 86400000;
    for (const band of this.dateConfidenceBands) {
      if (diffDays <= Number(band?.max_diff_days)) {
        return Number(band?.score || 0);
      }
    }

    return 0;
  }

  findBestCandidate(l1Match, candidates, seasonMirror = null) {
    const placeholderFixture = this.teamSimilarity.isPlaceholderFixture(l1Match);
    const mirrorMatched = placeholderFixture
      ? null
      : this.mirrorManager?.findMirrorCandidate(l1Match, seasonMirror) || null;
    if (mirrorMatched) {
      return mirrorMatched;
    }

    if (!Array.isArray(candidates) || candidates.length === 0) {
      return null;
    }

    let best = null;
    for (const candidate of candidates) {
      const evaluation = this.evaluateCandidate(candidate, l1Match);
      if (evaluation && (!best || evaluation.confidence > best.confidence)) {
        best = evaluation;
      }
    }

    return best;
  }

  isStrictMatch(candidate, l1Match) {
    const resolvedCandidate = this.teamSimilarity.resolveCandidateTeams(candidate, l1Match);
    if (!resolvedCandidate?.homeTeam || !resolvedCandidate?.awayTeam) {
      return false;
    }

    const orientation = this.evaluateCandidateOrientation(resolvedCandidate, l1Match);
    return this.teamSimilarity.isPlaceholderFixture(l1Match)
      ? orientation.directNormalized || orientation.swappedNormalized
      : orientation.directMatch || orientation.swappedMatch;
  }
}

module.exports = { ReconScoringEngine };
