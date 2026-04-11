'use strict';

const { Normalizer } = require('../../../utils/Normalizer');
const {
  ODDSPORTAL_BASE_URL,
  ODDSPORTAL_LEAGUE_CATALOG,
  buildDeterministicMatchHash,
  parseMatchTeams,
  slugifyPathSegment
} = require('./oddsPortalUrlUtils');

class OddsPortalURLParser {
  static buildURL(league, season, homeTeam, awayTeam) {
    const route = ODDSPORTAL_LEAGUE_CATALOG[league] || ODDSPORTAL_LEAGUE_CATALOG[String(league || '').toLowerCase()];
    if (!route) {
      throw new Error(`未知联赛: ${league}`);
    }

    const normalizedSeason = Normalizer.normalizeSeason(season).replace('/', '-');
    const homeSlug = slugifyPathSegment(homeTeam);
    const awaySlug = slugifyPathSegment(awayTeam);

    return `${ODDSPORTAL_BASE_URL}/soccer/${route.country}/${route.slug}-${normalizedSeason}/${homeSlug}-${awaySlug}/`;
  }

  static parseMatchURL(url) {
    try {
      const urlObject = new URL(url);
      const pathParts = urlObject.pathname.split('/').filter(Boolean);

      if (pathParts.length < 4) {
        return null;
      }

      const [sport, , leaguePart, ...matchParts] = pathParts;
      if (sport !== 'soccer') {
        return null;
      }

      const seasonMatch = leaguePart.match(/^(.+)-(\d{4})-(\d{4})$/);
      const league = seasonMatch ? seasonMatch[1] : leaguePart;
      const season = seasonMatch ? `${seasonMatch[2]}/${seasonMatch[3]}` : null;
      const explicitHash = matchParts[matchParts.length - 2];
      const matchSlug = matchParts[matchParts.length - 1] || '';

      return {
        league,
        season,
        match_hash: /^[a-z0-9]{8}$/i.test(explicitHash || '')
          ? explicitHash.toLowerCase()
          : buildDeterministicMatchHash(urlObject.pathname),
        ...parseMatchTeams(matchSlug),
        raw_url: url,
        full_path: urlObject.pathname
      };
    } catch (error) {
      return null;
    }
  }
}

module.exports = {
  OddsPortalURLParser
};
