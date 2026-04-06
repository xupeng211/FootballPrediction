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
    this.activeLeagueId = Number.isInteger(Number(options.activeLeagueId))
      ? Number(options.activeLeagueId)
      : null;
    this.activeLeagueDictionary = new Map();
    this.dictionaryStringContainsLeagueIds = new Set(
      (options.dictionaryStringContainsLeagueIds
        ?? runtimeConfig.dictionary_string_contains_league_ids
        ?? [])
        .map((leagueId) => Number(leagueId))
        .filter((leagueId) => Number.isInteger(leagueId) && leagueId > 0)
    );
    this.dictionaryStringContainsMinLength = Math.max(
      1,
      Number(
        options.dictionaryStringContainsMinLength
        ?? runtimeConfig.dictionary_string_contains_min_length
        ?? 5
      )
    );

    if (Array.isArray(options.leagueDictionaryEntries)) {
      this.setLeagueDictionaryEntries(this.activeLeagueId, options.leagueDictionaryEntries);
    }
  }

  setMirrorManager(mirrorManager) {
    this.mirrorManager = mirrorManager || null;
    return this;
  }

  setLeagueDictionaryEntries(leagueId, entries = []) {
    const normalizedLeagueId = Number(leagueId);
    this.activeLeagueId = Number.isInteger(normalizedLeagueId) && normalizedLeagueId > 0
      ? normalizedLeagueId
      : null;
    this.activeLeagueDictionary = new Map();

    for (const entry of Array.isArray(entries) ? entries : []) {
      const remoteName = String(entry?.remote_name || entry?.remoteName || '').trim();
      const localTeamId = String(entry?.local_team_id || entry?.localTeamId || '').trim();
      const localTeamName = String(entry?.local_team_name || entry?.localTeamName || '').trim();
      const key = this.normalizeTeamName(remoteName);

      if (!key || !localTeamId) {
        continue;
      }

      this.activeLeagueDictionary.set(key, {
        leagueId: this.activeLeagueId,
        remoteName,
        localTeamId,
        localTeamName: localTeamName || null,
        normalizedLocalTeamName: localTeamName ? this.normalizeTeamName(localTeamName) : null
      });
    }

    return this;
  }

  clearLeagueDictionary() {
    this.activeLeagueId = null;
    this.activeLeagueDictionary = new Map();
    return this;
  }

  shouldAllowDictionaryStringContains() {
    return Number.isInteger(this.activeLeagueId)
      && this.activeLeagueId > 0
      && this.dictionaryStringContainsLeagueIds.has(this.activeLeagueId);
  }

  normalizeDictionaryComparableName(teamName) {
    const raw = String(teamName || '')
      .replace(/\([^)]*\)/g, ' ')
      .replace(/\[[^\]]*\]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();

    return this.normalizeTeamName(raw);
  }

  isComparableNameEquivalent(left, right) {
    const normalizedLeft = this.normalizeTeamName(left);
    const normalizedRight = this.normalizeTeamName(right);
    if (normalizedLeft && normalizedRight && normalizedLeft === normalizedRight) {
      return true;
    }

    const simplifiedLeft = this.normalizeDictionaryComparableName(left);
    const simplifiedRight = this.normalizeDictionaryComparableName(right);
    if (simplifiedLeft && simplifiedRight && simplifiedLeft === simplifiedRight) {
      return true;
    }

    if (!this.shouldAllowDictionaryStringContains() || !simplifiedLeft || !simplifiedRight) {
      return false;
    }

    const shorter = simplifiedLeft.length <= simplifiedRight.length
      ? simplifiedLeft
      : simplifiedRight;
    const longer = shorter === simplifiedLeft
      ? simplifiedRight
      : simplifiedLeft;

    return shorter.length >= this.dictionaryStringContainsMinLength
      && longer.includes(shorter);
  }

  calculateSimilarity(left, right) {
    if (!left || !right) {
      return 0;
    }

    const normalizedLeft = this.normalizeTeamName(this.resolveComparableTeamName(left));
    const normalizedRight = this.normalizeTeamName(this.resolveComparableTeamName(right));

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

  resolveComparableTeamName(teamName) {
    const dictionaryComparable = this.resolveDictionaryComparableTeamName(teamName);
    if (dictionaryComparable?.value) {
      return dictionaryComparable.value;
    }

    return teamName;
  }

  normalizeTeamName(teamName) {
    const raw = String(teamName || '')
      .replace(/[\\/]+/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();

    return String(Normalizer.normalizeTeamName(raw) || raw || '')
      .toLowerCase()
      .trim();
  }

  resolveLeagueDictionaryEntry(teamName) {
    const key = this.normalizeTeamName(teamName);
    if (!key || !(this.activeLeagueDictionary instanceof Map)) {
      return null;
    }

    return this.activeLeagueDictionary.get(key) || null;
  }

  splitCompositeTeamName(teamName) {
    return String(teamName || '')
      .split(/[\\/]+/)
      .map((segment) => String(segment || '').trim())
      .filter(Boolean);
  }

  resolveDictionaryComparableTeamName(teamName) {
    const directEntry = this.resolveLeagueDictionaryEntry(teamName);
    if (directEntry?.localTeamName) {
      return {
        value: directEntry.localTeamName,
        usedDictionary: true
      };
    }

    const segments = this.splitCompositeTeamName(teamName);
    if (segments.length <= 1) {
      return null;
    }

    const localSegments = [];
    for (const segment of segments) {
      const entry = this.resolveLeagueDictionaryEntry(segment);
      if (!entry?.localTeamName) {
        return null;
      }
      localSegments.push(entry.localTeamName);
    }

    return {
      value: localSegments.join(' '),
      usedDictionary: true
    };
  }

  isDictionaryExactMatch(remoteTeamName, localTeamName) {
    const comparable = this.resolveDictionaryComparableTeamName(remoteTeamName);
    if (!comparable?.value) {
      return false;
    }

    return this.isComparableNameEquivalent(comparable.value, localTeamName);
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
    const comparableCandidateHome = this.resolveComparableTeamName(candidateHome);
    const comparableCandidateAway = this.resolveComparableTeamName(candidateAway);
    const l1Home = l1Match?.home_team || '';
    const l1Away = l1Match?.away_team || '';

    const directHome = this.calculateSimilarity(candidateHome, l1Home);
    const directAway = this.calculateSimilarity(candidateAway, l1Away);
    const swappedHome = this.calculateSimilarity(candidateHome, l1Away);
    const swappedAway = this.calculateSimilarity(candidateAway, l1Home);
    const directDictionaryMatch = this.isDictionaryExactMatch(candidateHome, l1Home)
      && this.isDictionaryExactMatch(candidateAway, l1Away);
    const swappedDictionaryMatch = this.isDictionaryExactMatch(candidateHome, l1Away)
      && this.isDictionaryExactMatch(candidateAway, l1Home);
    const directScore = (directHome + directAway) / 2;
    const swappedScore = (swappedHome + swappedAway) / 2;

    const directNormalized = this.isComparableNameEquivalent(comparableCandidateHome, l1Home)
      && this.isComparableNameEquivalent(comparableCandidateAway, l1Away);
    const swappedNormalized = this.isComparableNameEquivalent(comparableCandidateHome, l1Away)
      && this.isComparableNameEquivalent(comparableCandidateAway, l1Home);
    const directMatch = directDictionaryMatch || directNormalized || (
      directHome > this.orientationSimilarityThreshold && directAway > this.orientationSimilarityThreshold
    );
    const swappedMatch = swappedDictionaryMatch || swappedNormalized || (
      swappedHome > this.orientationSimilarityThreshold && swappedAway > this.orientationSimilarityThreshold
    );
    const isReversed = swappedMatch && (
      !directMatch ||
      swappedScore > directScore ||
      (swappedDictionaryMatch && !directDictionaryMatch) ||
      (swappedNormalized && !directNormalized)
    );

    return {
      directMatch,
      swappedMatch,
      directScore,
      swappedScore,
      directNormalized,
      swappedNormalized,
      isReversed,
      dictionaryLocked: directDictionaryMatch || swappedDictionaryMatch
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
    const placeholderFixture = this.isPlaceholderFixture(l1Match);

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
      const resolvedCandidate = this.resolveCandidateTeams(candidate, l1Match);
      if (!resolvedCandidate?.homeTeam || !resolvedCandidate?.awayTeam) {
        continue;
      }

      const orientation = this.evaluateCandidateOrientation(resolvedCandidate, l1Match);
      if (placeholderFixture && !(orientation.directNormalized || orientation.swappedNormalized)) {
        continue;
      }
      const teamConfidence = orientation.isReversed
        ? orientation.swappedScore
        : Math.max(orientation.directScore, orientation.swappedScore);
      const dateConfidence = this.calculateDateConfidence(
        candidate.matchDate || candidate.match_date,
        l1Match.match_date
      );
      const confidence = placeholderFixture && (orientation.directNormalized || orientation.swappedNormalized)
        ? 1.0
        : orientation.dictionaryLocked
        ? 1.0
        : dateConfidence === null
        ? teamConfidence
        : Math.max(0, Math.min(1, (teamConfidence * this.teamWeight) + (dateConfidence * this.dateWeight)));

      if (!best || confidence > best.confidence) {
        best = {
          candidate: resolvedCandidate,
          confidence,
          method: orientation.dictionaryLocked
            ? 'dictionary'
            : confidence >= this.exactMatchThreshold
              ? 'exact'
              : 'fuzzy',
          isReversed: orientation.isReversed
        };
      }
    }

    return best;
  }

  isStrictMatch(candidate, l1Match) {
    const resolvedCandidate = this.resolveCandidateTeams(candidate, l1Match);
    if (!resolvedCandidate?.homeTeam || !resolvedCandidate?.awayTeam) {
      return false;
    }

    const orientation = this.evaluateCandidateOrientation(resolvedCandidate, l1Match);
    if (this.isPlaceholderFixture(l1Match)) {
      return orientation.directNormalized || orientation.swappedNormalized;
    }
    return orientation.directMatch || orientation.swappedMatch;
  }
}

module.exports = { ReconMatchEvaluator };
