'use strict';

const { Normalizer } = require('../../../utils/Normalizer');

const reconMatchValidator = {
  formatSeasonForDb(season) {
    if (!season || typeof season !== 'string') {
      return season;
    }
    return season.includes('-') ? season.replace('-', '/') : season;
  },

  _normalizeTeamName(teamName) {
    const rawTeamName = typeof teamName === 'string' ? teamName : String(teamName || '');
    return String(Normalizer.normalizeTeamName(rawTeamName) || rawTeamName || '')
      .toLowerCase()
      .trim();
  },

  _hasTextualTeamName(teamName) {
    return typeof teamName === 'string' && /[a-z\u00c0-\u024f]/i.test(teamName);
  },

  _resolveWebMatchTeams(match, l1Matches = []) {
    if (!match) {
      return match;
    }

    if (this._hasTextualTeamName(match.homeTeam) && this._hasTextualTeamName(match.awayTeam)) {
      return match;
    }

    const derivedTeams = this._deriveTeamsFromUrl(match.url, l1Matches);
    if (!derivedTeams) {
      return {
        ...match,
        homeTeam: String(match.homeTeam || ''),
        awayTeam: String(match.awayTeam || '')
      };
    }

    return {
      ...match,
      homeTeam: derivedTeams.homeTeam,
      awayTeam: derivedTeams.awayTeam
    };
  },

  _deriveTeamsFromUrl(url, l1Matches = []) {
    const slugMatch = String(url || '').match(/\/([^/]+)-[A-Za-z0-9]{8}\/?$/);
    if (!slugMatch) {
      return null;
    }

    const parts = slugMatch[1].split('-').filter(Boolean);
    if (parts.length < 2) {
      return null;
    }

    let bestSplit = null;

    for (let index = 1; index < parts.length; index++) {
      const left = parts.slice(0, index).join(' ');
      const right = parts.slice(index).join(' ');

      let splitScore = 0;
      let bestL1Pair = null;
      for (const l1Match of l1Matches) {
        const directScore = (
          this._calculateTeamSimilarity(left, l1Match.home_team) +
          this._calculateTeamSimilarity(right, l1Match.away_team)
        ) / 2;
        const swappedScore = (
          this._calculateTeamSimilarity(left, l1Match.away_team) +
          this._calculateTeamSimilarity(right, l1Match.home_team)
        ) / 2;

        if (directScore >= splitScore) {
          splitScore = directScore;
          bestL1Pair = {
            homeTeam: l1Match.home_team,
            awayTeam: l1Match.away_team
          };
        }

        if (swappedScore > splitScore) {
          splitScore = swappedScore;
          bestL1Pair = {
            homeTeam: l1Match.away_team,
            awayTeam: l1Match.home_team
          };
        }
      }

      if (!bestSplit || splitScore > bestSplit.score) {
        bestSplit = { left, right, score: splitScore, bestL1Pair };
      }
    }

    if (!bestSplit) {
      return null;
    }

    if (bestSplit.bestL1Pair) {
      return bestSplit.bestL1Pair;
    }

    return {
      homeTeam: Normalizer.normalizeTeamName(bestSplit.left) || bestSplit.left,
      awayTeam: Normalizer.normalizeTeamName(bestSplit.right) || bestSplit.right
    };
  },

  _calculateTeamSimilarity(left, right) {
    const normalizedLeft = this._normalizeTeamName(left);
    const normalizedRight = this._normalizeTeamName(right);

    if (normalizedLeft && normalizedRight && normalizedLeft === normalizedRight) {
      return 1.0;
    }

    return this.parser
      ? this.parser.calculateSimilarity(left, right)
      : this.simpleSimilarity(left, right);
  },

  _resolveOrientation(sourceHome, sourceAway, l1Home, l1Away) {
    const directHome = this._calculateTeamSimilarity(sourceHome, l1Home);
    const directAway = this._calculateTeamSimilarity(sourceAway, l1Away);
    const swappedHome = this._calculateTeamSimilarity(sourceHome, l1Away);
    const swappedAway = this._calculateTeamSimilarity(sourceAway, l1Home);
    const directScore = (directHome + directAway) / 2;
    const swappedScore = (swappedHome + swappedAway) / 2;

    const directNormalized = this._normalizeTeamName(sourceHome) === this._normalizeTeamName(l1Home)
      && this._normalizeTeamName(sourceAway) === this._normalizeTeamName(l1Away);
    const swappedNormalized = this._normalizeTeamName(sourceHome) === this._normalizeTeamName(l1Away)
      && this._normalizeTeamName(sourceAway) === this._normalizeTeamName(l1Home);

    const directMatch = directNormalized || (directHome > 0.75 && directAway > 0.75);
    const swappedMatch = swappedNormalized || (swappedHome > 0.75 && swappedAway > 0.75);
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
  },

  extractTeamsFromText(text) {
    if (!text || !this.parser) return null;

    const cleanText = text.toLowerCase()
      .replace(/\d{1,2}:\d{2}/g, '')
      .replace(/\d+\.\d+/g, '')
      .replace(/[^\w\s-]/g, ' ')
      .trim();

    const knownTeams = Array.isArray(this.parser.knownTeams) ? this.parser.knownTeams : [];
    const foundTeams = [];

    for (const team of knownTeams) {
      const teamLower = team.toLowerCase();
      if (cleanText.includes(teamLower)) {
        foundTeams.push(team);
      } else if (this.parser.fuzzball) {
        const score = this.parser.fuzzball.partial_ratio(teamLower, cleanText);
        if (score > 75) foundTeams.push(team);
      }
      if (foundTeams.length >= 2) break;
    }

    if (foundTeams.length >= 2) {
      return { homeTeam: foundTeams[0], awayTeam: foundTeams[1] };
    }

    return null;
  },

  extractHomeTeamFromText(text) {
    if (!text) return null;
    const parts = text.split(/\s+vs\s+|\s+-\s+|\n/);
    return parts[0]?.trim() || null;
  },

  simpleSimilarity(s1, s2) {
    const a = s1.toLowerCase().trim();
    const b = s2.toLowerCase().trim();

    if (a === b) return 1.0;
    if (a.includes(b) || b.includes(a)) {
      return Math.min(a.length, b.length) / Math.max(a.length, b.length);
    }

    const words1 = new Set(a.split(' '));
    const words2 = new Set(b.split(' '));
    const intersection = new Set([...words1].filter((x) => words2.has(x)));
    const union = new Set([...words1, ...words2]);

    return intersection.size / union.size;
  },

  getWordRoot(teamName) {
    if (!teamName) return '';

    const normalized = String(teamName)
      .toLowerCase()
      .replace(/[^a-z\s]/g, '')
      .trim();

    return normalized.split(' ').map((word) => word.substring(0, 4)).join(' ');
  },

  calculateRootSimilarity(root1, root2) {
    const r1 = root1.split(' ');
    const r2 = root2.split(' ');

    let matches = 0;
    for (const word1 of r1) {
      for (const word2 of r2) {
        if (word1 === word2 || word1.includes(word2) || word2.includes(word1)) {
          matches++;
        }
      }
    }

    return matches / Math.max(r1.length, r2.length);
  }
};

module.exports = { reconMatchValidator };
