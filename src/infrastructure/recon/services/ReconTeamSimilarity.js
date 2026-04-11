'use strict';

const { Normalizer } = require('../../../utils/Normalizer');
const {
  decodeCandidateTeamSegment,
  extractCandidatePathname,
  extractTeamsFromH2hPath,
  hasTextualTeamName,
  isPlaceholderTeamName,
  isPlaceholderToken,
  normalizeDictionaryComparableName,
  normalizeLeaguePlaceComparableName,
  normalizeTeamName,
  splitCompositeTeamName,
  tokenizeIdentityName
} = require('../../shared/helpers/reconNameHelpers');

function toPositiveLeagueId(value) {
  const normalized = Number(value);
  return Number.isInteger(normalized) && normalized > 0 ? normalized : null;
}

function normalizeLeagueIdSet(values = []) {
  return new Set(
    values
      .map((leagueId) => Number(leagueId))
      .filter((leagueId) => Number.isInteger(leagueId) && leagueId > 0)
  );
}

function hasExactNormalizedMatch(left, right) {
  return Boolean(left && right && left === right);
}

function resolveComparablePair(left, right, normalizeMethod) {
  const normalizedLeft = normalizeMethod(left);
  const normalizedRight = normalizeMethod(right);
  return hasExactNormalizedMatch(normalizedLeft, normalizedRight);
}

function matchesByStringContains(left, right, minLength) {
  if (!left || !right) {
    return false;
  }

  const shorter = left.length <= right.length ? left : right;
  const longer = shorter === left ? right : left;
  return shorter.length >= minLength && longer.includes(shorter);
}

function buildDictionaryEntry(activeLeagueId, entry, normalizeFn) {
  const remoteName = String(entry?.remote_name || entry?.remoteName || '').trim();
  const localTeamId = String(entry?.local_team_id || entry?.localTeamId || '').trim();
  const localTeamName = String(entry?.local_team_name || entry?.localTeamName || '').trim();
  const key = normalizeFn(remoteName);

  return key && localTeamId
    ? {
      key,
      value: {
        leagueId: activeLeagueId,
        remoteName,
        localTeamId,
        localTeamName: localTeamName || null,
        normalizedLocalTeamName: localTeamName ? normalizeFn(localTeamName) : null
      }
    }
    : null;
}

function resolveDictionarySegments(segments, resolveEntry) {
  const localSegments = [];

  for (const segment of segments) {
    const entry = resolveEntry(segment);
    if (!entry?.localTeamName) {
      return null;
    }

    localSegments.push(entry.localTeamName);
  }

  return localSegments.length > 1
    ? {
      value: localSegments.join(' '),
      usedDictionary: true
    }
    : null;
}

function chooseBestUrlSplit(parts, l1Match, calculateSimilarity) {
  let bestSplit = null;
  const l1Home = l1Match?.home_team || '';
  const l1Away = l1Match?.away_team || '';

  for (let index = 1; index < parts.length; index++) {
    const left = parts.slice(0, index).join(' ');
    const right = parts.slice(index).join(' ');
    const directScore = (
      calculateSimilarity(left, l1Home) +
      calculateSimilarity(right, l1Away)
    ) / 2;
    const swappedScore = (
      calculateSimilarity(left, l1Away) +
      calculateSimilarity(right, l1Home)
    ) / 2;
    const splitScore = Math.max(directScore, swappedScore);

    if (!bestSplit || splitScore > bestSplit.score) {
      bestSplit = { left, right, score: splitScore };
    }
  }

  return bestSplit;
}

function extractAgeMarker(tokens) {
  const ageToken = tokens.find((token) => /^u\d{1,2}$/.test(token));
  return ageToken ? ageToken.toUpperCase() : null;
}

function collectIdentityMarkers(tokens, tokenSet) {
  return [
    extractAgeMarker(tokens),
    tokenSet.has('youth') || tokenSet.has('juvenil') || tokenSet.has('academy') ? 'YOUTH' : null,
    tokenSet.has('reserve') || tokenSet.has('reserves') ? 'RESERVE' : null,
    (tokenSet.has('b') && tokens.length > 1) || (tokenSet.has('team') && tokenSet.has('b')) ? 'B_TEAM' : null,
    (tokenSet.has('ii') && tokens.length > 1) || tokenSet.has('castilla') || (tokenSet.has('next') && tokenSet.has('gen'))
      ? 'SECOND_TEAM'
      : null
  ].filter(Boolean);
}

class ReconTeamSimilarity {
  constructor(options = {}) {
    this.parser = options.parser || null;
    this.activeLeagueId = toPositiveLeagueId(options.activeLeagueId);
    this.activeLeagueDictionary = new Map();
    this.dictionaryStringContainsLeagueIds = normalizeLeagueIdSet(options.dictionaryStringContainsLeagueIds || []);
    this.dictionaryStringContainsMinLength = Math.max(1, Number(options.dictionaryStringContainsMinLength ?? 5));
    this.placeNameEquivalentLeagueIds = normalizeLeagueIdSet(options.placeNameEquivalentLeagueIds || []);

    if (Array.isArray(options.leagueDictionaryEntries)) {
      this.setLeagueDictionaryEntries(this.activeLeagueId, options.leagueDictionaryEntries);
    }
  }

  setLeagueDictionaryEntries(leagueId, entries = []) {
    this.activeLeagueId = toPositiveLeagueId(leagueId);
    this.activeLeagueDictionary = new Map();

    for (const entry of Array.isArray(entries) ? entries : []) {
      const normalizedEntry = buildDictionaryEntry(this.activeLeagueId, entry, this.normalizeTeamName.bind(this));
      if (normalizedEntry) {
        this.activeLeagueDictionary.set(normalizedEntry.key, normalizedEntry.value);
      }
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
      && this.dictionaryStringContainsLeagueIds.has(this.activeLeagueId);
  }

  shouldAllowPlaceNameEquivalence() {
    return Number.isInteger(this.activeLeagueId)
      && this.placeNameEquivalentLeagueIds.has(this.activeLeagueId);
  }

  normalizeTeamName(teamName) {
    return normalizeTeamName(teamName);
  }

  normalizeDictionaryComparableName(teamName) {
    return normalizeDictionaryComparableName(teamName);
  }

  normalizeLeaguePlaceComparableName(teamName) {
    return normalizeLeaguePlaceComparableName(teamName);
  }

  resolveLeagueDictionaryEntry(teamName) {
    const key = this.normalizeTeamName(teamName);
    return key && this.activeLeagueDictionary instanceof Map
      ? this.activeLeagueDictionary.get(key) || null
      : null;
  }

  splitCompositeTeamName(teamName) {
    return splitCompositeTeamName(teamName);
  }

  resolveDictionaryComparableTeamName(teamName) {
    const directEntry = this.resolveLeagueDictionaryEntry(teamName);
    if (directEntry?.localTeamName) {
      return {
        value: directEntry.localTeamName,
        usedDictionary: true
      };
    }

    return resolveDictionarySegments(
      this.splitCompositeTeamName(teamName),
      this.resolveLeagueDictionaryEntry.bind(this)
    );
  }

  resolveComparableTeamName(teamName) {
    return this.resolveDictionaryComparableTeamName(teamName)?.value || teamName;
  }

  isComparableNameEquivalent(left, right) {
    if (resolveComparablePair(left, right, this.normalizeTeamName.bind(this))) {
      return true;
    }

    const simplifiedLeft = this.normalizeDictionaryComparableName(left);
    const simplifiedRight = this.normalizeDictionaryComparableName(right);
    if (hasExactNormalizedMatch(simplifiedLeft, simplifiedRight)) {
      return true;
    }

    if (this.shouldAllowPlaceNameEquivalence()) {
      const placeComparableLeft = this.normalizeLeaguePlaceComparableName(left);
      const placeComparableRight = this.normalizeLeaguePlaceComparableName(right);
      if (hasExactNormalizedMatch(placeComparableLeft, placeComparableRight)) {
        return true;
      }
    }

    return this.shouldAllowDictionaryStringContains()
      && matchesByStringContains(simplifiedLeft, simplifiedRight, this.dictionaryStringContainsMinLength);
  }

  calculateSimilarity(left, right) {
    if (!left || !right) {
      return 0;
    }

    if (this.shouldAllowPlaceNameEquivalence()) {
      const placeComparableLeft = this.normalizeLeaguePlaceComparableName(left);
      const placeComparableRight = this.normalizeLeaguePlaceComparableName(right);
      if (hasExactNormalizedMatch(placeComparableLeft, placeComparableRight)) {
        return 1.0;
      }
    }

    const normalizedLeft = this.normalizeTeamName(this.resolveComparableTeamName(left));
    const normalizedRight = this.normalizeTeamName(this.resolveComparableTeamName(right));
    if (hasExactNormalizedMatch(normalizedLeft, normalizedRight)) {
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

    return comparableLeft.includes(comparableRight) || comparableRight.includes(comparableLeft)
      ? 0.8
      : 0;
  }

  isDictionaryExactMatch(remoteTeamName, localTeamName) {
    const comparable = this.resolveDictionaryComparableTeamName(remoteTeamName);
    return comparable?.value
      ? this.isComparableNameEquivalent(comparable.value, localTeamName)
      : false;
  }

  isPlaceholderToken(token) {
    return isPlaceholderToken(token);
  }

  isPlaceholderTeamName(teamName) {
    return isPlaceholderTeamName(teamName);
  }

  isPlaceholderFixture(l1Match) {
    return this.isPlaceholderTeamName(l1Match?.home_team)
      || this.isPlaceholderTeamName(l1Match?.away_team);
  }

  hasTextualTeamName(teamName) {
    return hasTextualTeamName(teamName);
  }

  resolveCandidateTeams(candidate, l1Match) {
    if (!candidate) {
      return candidate;
    }

    if (this.hasTextualTeamName(candidate.homeTeam) && this.hasTextualTeamName(candidate.awayTeam)) {
      return candidate;
    }

    const derivedTeams = this.deriveTeamsFromCandidateUrl(candidate.url, l1Match);
    return derivedTeams
      ? { ...candidate, homeTeam: derivedTeams.homeTeam, awayTeam: derivedTeams.awayTeam }
      : candidate;
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

    const parts = String(match[1] || '').split('-').filter(Boolean);
    if (parts.length < 2) {
      return null;
    }

    const bestSplit = chooseBestUrlSplit(parts, l1Match, this.calculateSimilarity.bind(this));
    return bestSplit
      ? {
        homeTeam: Normalizer.normalizeTeamName(bestSplit.left) || bestSplit.left,
        awayTeam: Normalizer.normalizeTeamName(bestSplit.right) || bestSplit.right
      }
      : null;
  }

  extractCandidatePathname(url) {
    return extractCandidatePathname(url);
  }

  extractTeamsFromH2hPath(pathname) {
    return extractTeamsFromH2hPath(pathname);
  }

  decodeCandidateTeamSegment(segment) {
    return decodeCandidateTeamSegment(segment);
  }

  tokenizeIdentityName(teamName) {
    return tokenizeIdentityName(teamName);
  }

  extractIdentityMarkers(teamName) {
    const tokens = this.tokenizeIdentityName(teamName);
    return [...new Set(collectIdentityMarkers(tokens, new Set(tokens)))];
  }

  hasIdentityHardConflict(leftTeamName, rightTeamName) {
    const leftMarkers = this.extractIdentityMarkers(leftTeamName);
    const rightMarkers = this.extractIdentityMarkers(rightTeamName);
    return leftMarkers.length > 0 !== rightMarkers.length > 0;
  }
}

module.exports = { ReconTeamSimilarity };
