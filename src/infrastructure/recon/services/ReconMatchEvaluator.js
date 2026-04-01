'use strict';

const { Normalizer } = require('../../../utils/Normalizer');
const { RECON_CONFIG, getReconConfigSection } = require('./ReconServiceConfig');

class ReconMatchEvaluator {
  constructor(options = {}) {
    const matchingConfig = RECON_CONFIG.matching || {};
    const runtimeConfig = getReconConfigSection(['recon_runtime', 'match_evaluator'], {});

    this.parser = options.parser || null;
    this.logger = options.logger || console;
    this.mirrorManager = options.mirrorManager || null;
    this.orientationSimilarityThreshold = Number(
      options.orientationSimilarityThreshold
      ?? runtimeConfig.orientation_similarity_threshold
      ?? matchingConfig.orientation_similarity_threshold
    );
    this.exactMatchThreshold = Number(
      options.exactMatchThreshold
      ?? runtimeConfig.exact_match_threshold
      ?? matchingConfig.exact_match_threshold
    );
    this.teamWeight = Number(
      options.teamWeight
      ?? runtimeConfig.team_weight
      ?? matchingConfig.team_weight
    );
    this.dateWeight = Number(
      options.dateWeight
      ?? runtimeConfig.date_weight
      ?? matchingConfig.date_weight
    );
    this.dateConfidenceBands = Array.isArray(options.dateConfidenceBands)
      ? options.dateConfidenceBands
      : Array.isArray(matchingConfig.date_confidence_bands)
        ? matchingConfig.date_confidence_bands
        : [];
  }

  setMirrorManager(mirrorManager) {
    this.mirrorManager = mirrorManager || null;
    return this;
  }

  calculateSimilarity(left, right) {
    if (!left || !right) {
      return 0;
    }

    const normalizedLeft = this.normalizeTeamName(left);
    const normalizedRight = this.normalizeTeamName(right);

    if (normalizedLeft && normalizedRight && normalizedLeft === normalizedRight) {
      return 1.0;
    }

    if (this.parser?.calculateSimilarity) {
      return this.parser.calculateSimilarity(left, right);
    }

    const comparableLeft = String(left || '').toLowerCase().trim();
    const comparableRight = String(right || '').toLowerCase().trim();
    if (comparableLeft === comparableRight) {
      return 1.0;
    }
    if (comparableLeft.includes(comparableRight) || comparableRight.includes(comparableLeft)) {
      return 0.8;
    }
    return 0;
  }

  normalizeTeamName(teamName) {
    return String(Normalizer.normalizeTeamName(teamName || '') || '')
      .toLowerCase()
      .trim();
  }

  isPlaceholderToken(token) {
    return /^\d+[a-z]+$/i.test(String(token || '').trim());
  }

  isPlaceholderTeamName(teamName) {
    const normalized = String(teamName || '')
      .trim()
      .toLowerCase()
      .replace(/\s+/g, ' ');

    if (!normalized) {
      return false;
    }

    if (/\bplay[\s-]?off\b/i.test(normalized)) {
      return true;
    }

    if (/^(winner|loser)\b/i.test(normalized)) {
      return true;
    }

    const tokens = normalized.split(' ').filter(Boolean);
    return tokens.length > 0 && tokens.every((token) => this.isPlaceholderToken(token));
  }

  isPlaceholderFixture(l1Match) {
    return this.isPlaceholderTeamName(l1Match?.home_team)
      || this.isPlaceholderTeamName(l1Match?.away_team);
  }

  hasTextualTeamName(teamName) {
    return typeof teamName === 'string' && /[a-z\u00c0-\u024f]/i.test(teamName);
  }

  resolveCandidateTeams(candidate, l1Match) {
    if (!candidate) {
      return candidate;
    }

    if (this.hasTextualTeamName(candidate.homeTeam) && this.hasTextualTeamName(candidate.awayTeam)) {
      return candidate;
    }

    const derivedTeams = this.deriveTeamsFromCandidateUrl(candidate.url, l1Match);
    if (!derivedTeams) {
      return candidate;
    }

    return {
      ...candidate,
      homeTeam: derivedTeams.homeTeam,
      awayTeam: derivedTeams.awayTeam
    };
  }

  deriveTeamsFromCandidateUrl(url, l1Match) {
    const pathname = this.extractCandidatePathname(url);
    const h2hTeams = this.extractTeamsFromH2hPath(pathname);
    if (h2hTeams) {
      return h2hTeams;
    }

    const match = pathname.match(/\/([^/]+)-[A-Za-z0-9]{8}\/?$/);
    if (!match) {
      return null;
    }

    const slug = match[1];
    const parts = slug.split('-').filter(Boolean);
    if (parts.length < 2) {
      return null;
    }

    let bestSplit = null;
    const l1Home = l1Match?.home_team || '';
    const l1Away = l1Match?.away_team || '';

    for (let index = 1; index < parts.length; index++) {
      const left = parts.slice(0, index).join(' ');
      const right = parts.slice(index).join(' ');
      const directScore = (
        this.calculateSimilarity(left, l1Home) +
        this.calculateSimilarity(right, l1Away)
      ) / 2;
      const swappedScore = (
        this.calculateSimilarity(left, l1Away) +
        this.calculateSimilarity(right, l1Home)
      ) / 2;
      const splitScore = Math.max(directScore, swappedScore);

      if (!bestSplit || splitScore > bestSplit.score) {
        bestSplit = { left, right, score: splitScore };
      }
    }

    if (!bestSplit) {
      return null;
    }

    return {
      homeTeam: Normalizer.normalizeTeamName(bestSplit.left) || bestSplit.left,
      awayTeam: Normalizer.normalizeTeamName(bestSplit.right) || bestSplit.right
    };
  }

  extractCandidatePathname(url) {
    const raw = String(url || '').trim();
    if (!raw) {
      return '';
    }

    try {
      const parsed = new URL(raw);
      return parsed.pathname || '';
    } catch {
      return raw.split('#')[0].split('?')[0];
    }
  }

  extractTeamsFromH2hPath(pathname) {
    const match = String(pathname || '').match(/\/football\/h2h\/([^/]+)\/([^/]+)\/?$/i);
    if (!match) {
      return null;
    }

    const left = this.decodeCandidateTeamSegment(match[1]);
    const right = this.decodeCandidateTeamSegment(match[2]);
    if (!left || !right) {
      return null;
    }

    return {
      homeTeam: left,
      awayTeam: right
    };
  }

  decodeCandidateTeamSegment(segment) {
    const slug = String(segment || '')
      .replace(/-[A-Za-z0-9]{8}$/i, '')
      .replace(/-/g, ' ')
      .trim();

    if (!slug) {
      return '';
    }

    return Normalizer.normalizeTeamName(slug) || slug;
  }

  evaluateCandidateOrientation(candidate, l1Match) {
    const candidateHome = candidate?.homeTeam || '';
    const candidateAway = candidate?.awayTeam || '';
    const l1Home = l1Match?.home_team || '';
    const l1Away = l1Match?.away_team || '';

    const directHome = this.calculateSimilarity(candidateHome, l1Home);
    const directAway = this.calculateSimilarity(candidateAway, l1Away);
    const swappedHome = this.calculateSimilarity(candidateHome, l1Away);
    const swappedAway = this.calculateSimilarity(candidateAway, l1Home);
    const directScore = (directHome + directAway) / 2;
    const swappedScore = (swappedHome + swappedAway) / 2;

    const directNormalized = this.normalizeTeamName(candidateHome) === this.normalizeTeamName(l1Home)
      && this.normalizeTeamName(candidateAway) === this.normalizeTeamName(l1Away);
    const swappedNormalized = this.normalizeTeamName(candidateHome) === this.normalizeTeamName(l1Away)
      && this.normalizeTeamName(candidateAway) === this.normalizeTeamName(l1Home);
    const directMatch = directNormalized || (
      directHome > this.orientationSimilarityThreshold && directAway > this.orientationSimilarityThreshold
    );
    const swappedMatch = swappedNormalized || (
      swappedHome > this.orientationSimilarityThreshold && swappedAway > this.orientationSimilarityThreshold
    );
    const isReversed = swappedMatch && (
      !directMatch ||
      swappedScore > directScore ||
      (swappedNormalized && !directNormalized)
    );

    return {
      directMatch,
      swappedMatch,
      directScore,
      swappedScore,
      isReversed
    };
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
    if (this.isPlaceholderFixture(l1Match)) {
      return null;
    }

    const mirrorMatched = this.mirrorManager?.findMirrorCandidate(l1Match, seasonMirror) || null;
    if (mirrorMatched) {
      return mirrorMatched;
    }

    if (!Array.isArray(candidates) || candidates.length === 0) {
      return null;
    }

    let best = null;

    for (const candidate of candidates) {
      const resolvedCandidate = this.resolveCandidateTeams(candidate, l1Match);
      if (!resolvedCandidate?.homeTeam || !resolvedCandidate?.awayTeam) {
        continue;
      }

      const orientation = this.evaluateCandidateOrientation(resolvedCandidate, l1Match);
      const teamConfidence = orientation.isReversed
        ? orientation.swappedScore
        : Math.max(orientation.directScore, orientation.swappedScore);
      const dateConfidence = this.calculateDateConfidence(
        candidate.matchDate || candidate.match_date,
        l1Match.match_date
      );
      const confidence = dateConfidence === null
        ? teamConfidence
        : Math.max(0, Math.min(1, (teamConfidence * this.teamWeight) + (dateConfidence * this.dateWeight)));

      if (!best || confidence > best.confidence) {
        best = {
          candidate: resolvedCandidate,
          confidence,
          method: confidence >= this.exactMatchThreshold ? 'exact' : 'fuzzy',
          isReversed: orientation.isReversed
        };
      }
    }

    return best;
  }

  isStrictMatch(candidate, l1Match) {
    if (this.isPlaceholderFixture(l1Match)) {
      return false;
    }

    const resolvedCandidate = this.resolveCandidateTeams(candidate, l1Match);
    if (!resolvedCandidate?.homeTeam || !resolvedCandidate?.awayTeam) {
      return false;
    }

    const orientation = this.evaluateCandidateOrientation(resolvedCandidate, l1Match);
    return orientation.directMatch || orientation.swappedMatch;
  }
}

module.exports = { ReconMatchEvaluator };
