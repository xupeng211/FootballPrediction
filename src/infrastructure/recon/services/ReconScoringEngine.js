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
    directScore: direct.score,
    swappedScore: swapped.score,
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

function selectTeamConfidence(orientation) {
  return orientation.isReversed
    ? orientation.swappedScore
    : Math.max(orientation.directScore, orientation.swappedScore);
}

function clampConfidence(value) {
  return Math.max(0, Math.min(1, value));
}

function calculateConfidence({ dateConfidence, dateWeight, orientation, placeholderFixture, teamWeight }) {
  const selectedIdentityConflict = selectIdentityConflict(orientation);
  if (selectedIdentityConflict) {
    return 0;
  }

  if (placeholderFixture && (orientation.directNormalized || orientation.swappedNormalized)) {
    return 1.0;
  }

  if (orientation.dictionaryLocked) {
    return 1.0;
  }

  const teamConfidence = selectTeamConfidence(orientation);
  return dateConfidence === null
    ? teamConfidence
    : clampConfidence((teamConfidence * teamWeight) + (dateConfidence * dateWeight));
}

function resolveMatchMethod(confidence, dictionaryLocked, exactMatchThreshold) {
  if (dictionaryLocked) {
    return 'dictionary';
  }

  return confidence >= exactMatchThreshold ? 'exact' : 'fuzzy';
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
  const confidence = calculateConfidence({
    dateConfidence,
    dateWeight: engine.dateWeight,
    orientation,
    placeholderFixture,
    teamWeight: engine.teamWeight
  });

  return {
    candidate: resolvedCandidate,
    confidence,
    method: resolveMatchMethod(confidence, orientation.dictionaryLocked, engine.exactMatchThreshold),
    isReversed: orientation.isReversed
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

  calculateDateConfidence(candidateDate, matchDate) {
    const candidate = new Date(candidateDate);
    const target = new Date(matchDate);

    if (Number.isNaN(candidate.getTime()) || Number.isNaN(target.getTime())) {
      return null;
    }

    const diffDays = Math.abs(candidate.getTime() - target.getTime()) / 86400000;
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
      const evaluation = evaluateCandidateScore(this, candidate, l1Match, placeholderFixture);
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
