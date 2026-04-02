'use strict';

const reconMatchExtractor = {
  extractMatchesFromJson(json, source = 'api_intercept') {
    const matches = [];
    const seen = new Set();
    if (!json || typeof json !== 'object') {
      return matches;
    }

    const pushMatch = (candidate) => {
      if (!candidate) {
        return;
      }

      const dedupeKey = candidate.hash || candidate.url || `${candidate.homeTeam}|${candidate.awayTeam}|${candidate.matchDate || ''}`;
      if (!dedupeKey || seen.has(dedupeKey)) {
        return;
      }

      seen.add(dedupeKey);
      matches.push(candidate);
    };

    for (const rowMatch of this.extractStructuredRowMatches(json, source)) {
      pushMatch(rowMatch);
    }

    const extract = (obj, depth = 0) => {
      if (depth > this.extractMaxDepth) {
        return;
      }

      if (Array.isArray(obj)) {
        obj.forEach((item) => {
          if (this.isMatchObject(item)) {
            const match = this.normalizeMatchObject(item, source);
            pushMatch(match);
          } else if (typeof item === 'object') {
            extract(item, depth + 1);
          }
        });
      } else {
        Object.values(obj).forEach((value) => {
          if (typeof value === 'object' && value !== null) {
            extract(value, depth + 1);
          }
        });
      }
    };

    extract(json);
    return matches;
  },

  extractStructuredRowMatches(json, source = 'api_intercept') {
    const rowSets = [];

    if (Array.isArray(json?.d?.rows)) {
      rowSets.push(json.d.rows);
    }

    if (Array.isArray(json?.rows)) {
      rowSets.push(json.rows);
    }

    return rowSets
      .flat()
      .map((row) => this.normalizeMatchObject(row, source))
      .filter(Boolean);
  },

  isMatchObject(obj) {
    if (!obj || typeof obj !== 'object') {
      return false;
    }

    const indicators = [
      'homeTeam', 'awayTeam', 'home', 'away', 'home-name', 'away-name',
      'homeName', 'awayName', 'matchId', 'eventId', 'encodeEventId', 'hash', 'id'
    ];
    const keys = Object.keys(obj).map((key) => key.toLowerCase());
    return indicators.filter((indicator) => (
      keys.some((key) => key.includes(indicator.toLowerCase()))
    )).length >= 2;
  },

  normalizeMatchObject(obj, source = 'api_intercept') {
    try {
      let homeTeam = '';
      let awayTeam = '';

      if (Array.isArray(obj.participants) && obj.participants.length >= 2) {
        const home = obj.participants.find((participant) => participant?.side === 'home' || participant?.isHome === true)
          || obj.participants[0];
        const away = obj.participants.find((participant) => participant?.side === 'away' || participant?.isHome === false)
          || obj.participants[1];
        homeTeam = home?.name || home?.title || '';
        awayTeam = away?.name || away?.title || '';
      } else {
        homeTeam = obj.homeTeam || obj.home || obj.home_team || obj.team1 || obj.homeName || obj['home-name'] || '';
        awayTeam = obj.awayTeam || obj.away || obj.away_team || obj.team2 || obj.awayName || obj['away-name'] || '';
      }

      if (typeof homeTeam === 'object') {
        homeTeam = homeTeam.name || homeTeam.title || '';
      }
      if (typeof awayTeam === 'object') {
        awayTeam = awayTeam.name || awayTeam.title || '';
      }

      const hash = obj.hash || obj.eventHash || obj.encodeEventId || obj.id || obj.matchId || obj.eventId || '';
      const slug = obj.slug || obj.eventSlug || '';
      const countrySlug = obj.countrySlug || obj.country || '';
      const leagueSlug = obj.leagueSlug || obj.competitionSlug || '';

      let url = obj.url || obj.link || '';
      if (url && url.startsWith('/')) {
        url = `${this.baseUrl}${url}`;
      }
      if (!url && hash) {
        url = `${this.baseUrl}/football/${countrySlug}/${leagueSlug}/${slug}-${hash}/`;
      }

      if (!homeTeam || !awayTeam || !hash) {
        return null;
      }

      return {
        url,
        hash: hash.toString(),
        slug,
        homeTeam,
        awayTeam,
        matchDate: obj.matchDate || obj.match_date || (
          obj['date-start-timestamp']
            ? new Date(Number(obj['date-start-timestamp']) * 1000).toISOString()
            : null
        ),
        source
      };
    } catch {
      return null;
    }
  }
};

module.exports = { reconMatchExtractor };
