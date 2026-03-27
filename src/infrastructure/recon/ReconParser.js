/**
 * ReconParser - 配置驱动队名解析器
 * ==================================
 *
 * 职责:
 * 1. 从 OddsPortal slug / 文本中提取候选队名
 * 2. 将最终标准名统一委托给 Normalizer
 * 3. 通过通用前缀/缩写规则补强变体识别
 *
 * @module infrastructure/recon/ReconParser
 */

'use strict';

const { Normalizer } = require('../../utils/Normalizer');

const UNKNOWN_TEAMS = Object.freeze({
  homeTeam: 'Unknown',
  awayTeam: 'Unknown'
});

const TEAM_PREFIX_TOKENS = new Set([
  '1', 'ac', 'afc', 'as', 'cf', 'fc', 'rc', 'rcd', 'sc', 'sd', 'sv', 'tsg', 'ud', 'us', 'vfb'
]);

class ReconParser {
  constructor(options = {}) {
    this.logger = options.logger || console;
    this.fuzzball = options.fuzzball || null;
    this.dbPool = options.dbPool || null;
    this.traceId = options.traceId || null;

    const config = options.config || {};
    this.teamSlugs = [...new Set(config.teamSlugs || this.getDefaultTeamSlugs())];
    this.teamMappings = config.teamMappings || {};
    this.sortedSlugs = [...this.teamSlugs].sort((a, b) =>
      b.split('-').length - a.split('-').length
    );

    this.knownTeams = this._buildKnownTeams();
    this.knownTeamSet = new Set(this.knownTeams);

    this.logger.info('parser_initialized', {
      teamCount: this.teamSlugs.length,
      canonicalCount: this.knownTeams.length,
      normalization: 'centralized_normalizer'
    });
  }

  parseMatchUrl(url) {
    const match = url.match(/\/([^\/]+)-([a-zA-Z0-9]{8})\/$/);

    if (!match) {
      return { hash: null, slug: null, ...UNKNOWN_TEAMS };
    }

    const cleanSlug = match[1];
    const hash = match[2];
    const teams = this.extractTeamsFromSlugEnhanced(cleanSlug);

    return { hash, slug: cleanSlug, ...teams };
  }

  extractTeamsFromSlugEnhanced(slug) {
    const teams = this.extractTeamsFromSlug(slug);
    if (teams.homeTeam === 'Unknown' || teams.awayTeam === 'Unknown') {
      return { ...UNKNOWN_TEAMS, confidence: 0 };
    }

    return { ...teams, confidence: 1.0 };
  }

  extractTeamsFromSlug(slug) {
    const cleanSlug = this.teamNameToSlug(slug);
    if (!cleanSlug) {
      return { ...UNKNOWN_TEAMS };
    }

    const exactMatch = this._tryExactSlugSplit(cleanSlug);
    if (exactMatch) {
      return exactMatch;
    }

    const parts = cleanSlug.split('-').filter(Boolean);
    if (parts.length < 2) {
      return { ...UNKNOWN_TEAMS };
    }

    let bestCandidate = null;

    for (let i = 1; i < parts.length; i++) {
      const leftPart = parts.slice(0, i).join('-');
      const rightPart = parts.slice(i).join('-');

      const leftMatch = this._resolveTeamCandidate(leftPart);
      const rightMatch = this._resolveTeamCandidate(rightPart);

      if (!leftMatch || !rightMatch || leftMatch.team === rightMatch.team) {
        continue;
      }

      let score = (leftMatch.score + rightMatch.score) / 2;
      if (this.sortedSlugs.includes(leftPart)) score += 0.02;
      if (this.sortedSlugs.includes(rightPart)) score += 0.02;

      if (!bestCandidate || score > bestCandidate.score) {
        bestCandidate = {
          homeTeam: leftMatch.team,
          awayTeam: rightMatch.team,
          score
        };
      }
    }

    if (bestCandidate && bestCandidate.score >= 0.82) {
      return {
        homeTeam: bestCandidate.homeTeam,
        awayTeam: bestCandidate.awayTeam
      };
    }

    return { ...UNKNOWN_TEAMS };
  }

  findTeamMatch(name) {
    const match = this._resolveTeamCandidate(name);
    return match ? match.team : null;
  }

  normalizeTeamName(name) {
    return Normalizer.normalizeTeamName(name);
  }

  calculateSimilarity(name1, name2) {
    const canonical1 = this.normalizeTeamName(name1);
    const canonical2 = this.normalizeTeamName(name2);

    const n1 = this._sanitizeComparable(canonical1 || name1);
    const n2 = this._sanitizeComparable(canonical2 || name2);

    if (!n1 || !n2) return 0;
    if (n1 === n2) return 1.0;

    if (this.fuzzball) {
      try {
        return this.fuzzball.token_set_ratio(n1, n2) / 100;
      } catch (error) {
        // 回退到 LCS
      }
    }

    const lcs = this.longestCommonSubstring(n1, n2);
    return (2 * lcs) / (n1.length + n2.length);
  }

  longestCommonSubstring(s1, s2) {
    const m = s1.length;
    const n = s2.length;
    let maxLength = 0;
    const dp = Array(m + 1).fill(null).map(() => Array(n + 1).fill(0));

    for (let i = 1; i <= m; i++) {
      for (let j = 1; j <= n; j++) {
        if (s1[i - 1] === s2[j - 1]) {
          dp[i][j] = dp[i - 1][j - 1] + 1;
          maxLength = Math.max(maxLength, dp[i][j]);
        }
      }
    }

    return maxLength;
  }

  findBestMatch(query, candidates, threshold = 0.85) {
    let bestMatch = null;
    let bestScore = 0;

    for (const candidate of candidates) {
      const score = this.calculateSimilarity(query, candidate);
      if (score > bestScore) {
        bestScore = score;
        bestMatch = candidate;
      }
    }

    if (bestMatch && bestScore >= threshold) {
      return { team: bestMatch, confidence: bestScore };
    }

    return null;
  }

  teamNameToSlug(teamName) {
    return this._normalizeSlug(teamName);
  }

  _buildKnownTeams() {
    const canonicalTeams = new Set();

    for (const slug of this.teamSlugs) {
      const team = this.normalizeTeamName(slug);
      if (team) canonicalTeams.add(team);
    }

    for (const key of Object.keys(this.teamMappings)) {
      const team = this.normalizeTeamName(key);
      if (team) canonicalTeams.add(team);
    }

    for (const value of Object.values(this.teamMappings)) {
      const team = this.normalizeTeamName(value);
      if (team) canonicalTeams.add(team);
    }

    return [...canonicalTeams].sort();
  }

  _tryExactSlugSplit(cleanSlug) {
    const parts = cleanSlug.split('-').filter(Boolean);

    for (let i = 1; i < parts.length; i++) {
      const leftPart = parts.slice(0, i).join('-');
      const rightPart = parts.slice(i).join('-');

      if (this.sortedSlugs.includes(leftPart) && this.sortedSlugs.includes(rightPart)) {
        return {
          homeTeam: this.normalizeTeamName(leftPart),
          awayTeam: this.normalizeTeamName(rightPart)
        };
      }
    }

    return null;
  }

  _resolveTeamCandidate(name) {
    const comparable = this._sanitizeComparable(name);
    if (!comparable) {
      return null;
    }

    const directCanonical = this.normalizeTeamName(name);
    if (this.knownTeamSet.has(directCanonical)) {
      return { team: directCanonical, score: 1.0 };
    }

    const queryCore = this._stripPrefixTokens(comparable);
    const queryAcronym = this._buildAcronym(comparable);
    let bestMatch = null;

    for (const candidate of this.knownTeams) {
      const candidateComparable = this._sanitizeComparable(candidate);
      const candidateCore = this._stripPrefixTokens(candidateComparable);
      const candidateAcronym = this._buildAcronym(candidateComparable);

      let score = this.calculateSimilarity(comparable, candidateComparable);

      if (queryCore && queryCore === candidateCore) {
        score = Math.max(score, 0.97);
      }

      if (queryCore && queryCore.length >= 4 && candidateCore.startsWith(queryCore)) {
        score = Math.max(score, 0.88);
      }

      if (queryCore && candidateCore.length >= 4 && queryCore.startsWith(candidateCore)) {
        score = Math.max(score, 0.86);
      }

      if (queryAcronym && queryAcronym.length >= 2 && queryAcronym === candidateAcronym) {
        score = Math.max(score, 0.96);
      }

      if (!bestMatch || score > bestMatch.score) {
        bestMatch = { team: candidate, score };
      }
    }

    return bestMatch && bestMatch.score >= 0.82 ? bestMatch : null;
  }

  _normalizeSlug(value) {
    if (!value || typeof value !== 'string') {
      return '';
    }

    return value
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/&/g, ' and ')
      .replace(/['’.]/g, ' ')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '');
  }

  _sanitizeComparable(value) {
    return this._normalizeSlug(value).replace(/-/g, ' ').trim();
  }

  _stripPrefixTokens(value) {
    return value
      .split(' ')
      .filter(token => token && !TEAM_PREFIX_TOKENS.has(token))
      .join(' ')
      .trim();
  }

  _buildAcronym(value) {
    const tokens = value.split(' ').filter(Boolean);
    if (tokens.length === 0) {
      return '';
    }

    if (tokens.length === 1 && /^[a-z]{2,5}$/.test(tokens[0])) {
      return tokens[0].toUpperCase();
    }

    return tokens
      .filter(token => !TEAM_PREFIX_TOKENS.has(token))
      .map(token => token.charAt(0))
      .join('')
      .toUpperCase();
  }

  getDefaultTeamSlugs() {
    return [
      'aston-villa', 'crystal-palace', 'man-city', 'man-united', 'newcastle-utd',
      'nottingham-forest', 'sheffield-utd', 'west-ham', 'manchester-city',
      'manchester-united', 'brighton', 'bournemouth', 'wolverhampton-wanderers',
      'brentford', 'burnley', 'chelsea', 'everton', 'fulham',
      'liverpool', 'luton', 'arsenal', 'tottenham', 'wolves',
      'ipswich', 'southampton', 'leicester', 'west-ham-united',
      'alaves', 'almeria', 'athletic-bilbao', 'atletico-madrid', 'barcelona',
      'cadiz', 'celta-vigo', 'getafe', 'girona', 'granada',
      'las-palmas', 'mallorca', 'osasuna', 'rayo-vallecano', 'real-betis',
      'real-madrid', 'real-sociedad', 'sevilla', 'valencia', 'villarreal',
      'augsburg', 'bayer-leverkusen', 'bayern-munich', 'bochum', 'darmstadt',
      'dortmund', 'eintracht-frankfurt', 'freiburg', 'heidenheim', 'hoffenheim',
      'koln', 'mainz', 'monchengladbach', 'rb-leipzig', 'stuttgart',
      'union-berlin', 'werder-bremen', 'wolfsburg',
      'atalanta', 'bologna', 'cagliari', 'empoli', 'fiorentina',
      'frosinone', 'genoa', 'inter', 'juventus', 'lazio',
      'lecce', 'milan', 'monza', 'napoli', 'roma',
      'salernitana', 'sassuolo', 'torino', 'udinese', 'verona',
      'brest', 'clermont', 'le-havre', 'lens', 'lille',
      'lorient', 'lyon', 'marseille', 'metz', 'monaco',
      'montpellier', 'nantes', 'nice', 'psg', 'reims',
      'rennes', 'strasbourg', 'toulouse'
    ];
  }
}

module.exports = { ReconParser };
