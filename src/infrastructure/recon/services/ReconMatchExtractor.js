/* eslint-disable complexity, max-lines */
'use strict';

const { getReconConfigSection } = require('./ReconServiceConfig');

const MAX_TEAM_NAME_LENGTH = 100;
const MAX_SLUG_LENGTH = 200;
const TRUSTED_ODDSPORTAL_PREFIX = 'https://www.oddsportal.com/';
const MALFORMED_URL_FRAGMENT_RE = /:{3,}/u;

function normalizeSlugToken(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/^\/+|\/+$/g, '');
}

function extractLeagueContextFromUrl(url) {
  try {
    const parsed = new URL(String(url || ''), 'https://www.oddsportal.com');
    const match = parsed.pathname.match(/^\/football\/([^/]+)\/([^/]+)/i);
    if (!match) {
      return { countrySlug: '', leagueSlug: '' };
    }

    return {
      countrySlug: normalizeSlugToken(match[1]),
      leagueSlug: normalizeSlugToken(match[2])
    };
  } catch {
    return { countrySlug: '', leagueSlug: '' };
  }
}

function buildFallbackEventSlug(homeTeam, awayTeam) {
  const slugify = (value) => String(value || '')
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
}

function normalizeEventHash(value) {
  return String(value || '')
    .trim()
    .replace(/^#/u, '');
}

function isCanonicalEventHash(value) {
  return /^[A-Za-z0-9]{8}$/u.test(normalizeEventHash(value));
}

function exceedsSafeLength(value, maxLength) {
  return String(value || '').length > maxLength;
}

function isTrustedOddsPortalUrl(value, expectedHash = '') {
  const rawValue = String(value || '').trim();
  if (!rawValue || !rawValue.startsWith(TRUSTED_ODDSPORTAL_PREFIX) || MALFORMED_URL_FRAGMENT_RE.test(rawValue)) {
    return false;
  }

  try {
    const parsed = new URL(rawValue);
    if (parsed.protocol !== 'https:' || parsed.host !== 'www.oddsportal.com') {
      return false;
    }

    const pathname = String(parsed.pathname || '');
    if (!/^\/football\/[^/]+\/[^/]+\/[^/]+-[A-Za-z0-9]{8}\/?$/u.test(pathname)) {
      return false;
    }

    if (/\/football\/h2h\//iu.test(pathname) || /\/match\//iu.test(pathname)) {
      return false;
    }

    if (expectedHash) {
      const urlHash = normalizeEventHash(pathname.split('/').filter(Boolean).pop()?.match(/-([A-Za-z0-9]{8})$/u)?.[1] || '');
      return urlHash === normalizeEventHash(expectedHash);
    }

    return true;
  } catch {
    return false;
  }
}

function extractEventSlugFromUrl(url) {
  try {
    const parsed = new URL(String(url || ''), 'https://www.oddsportal.com');
    const pathname = String(parsed.pathname || '').replace(/\/+$/u, '');
    if (!pathname || /\/football\/h2h\//iu.test(pathname) || /\/match\//iu.test(pathname)) {
      return '';
    }

    const lastSegment = pathname.split('/').filter(Boolean).pop() || '';
    if (!lastSegment) {
      return '';
    }

    const eventMatch = lastSegment.match(/^(.+)-([A-Za-z0-9]{8})$/u);
    if (eventMatch) {
      return normalizeSlugToken(eventMatch[1]);
    }

    return '';
  } catch {
    return '';
  }
}

const DEFAULT_ANNUAL_LEAGUE_IDS = new Set(
  (getReconConfigSection(['recon_runtime', 'task_planner', 'annual_league_ids'], []) || [])
    .map((id) => Number(id))
    .filter((id) => Number.isInteger(id) && id > 0)
);

function normalizeLeagueId(value) {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

function extractLeagueIdFromMatchId(value) {
  const match = String(value || '').trim().match(/^(\d+)_/u);
  return match ? normalizeLeagueId(match[1]) : null;
}

function resolveAnnualLeagueIds(context) {
  const source = context?.annualLeagueIds;
  if (source instanceof Set) {
    return source;
  }
  if (Array.isArray(source)) {
    return new Set(source.map((id) => Number(id)).filter((id) => Number.isInteger(id) && id > 0));
  }
  return DEFAULT_ANNUAL_LEAGUE_IDS;
}

function resolveLeagueId(context, obj, matchId) {
  const candidates = [
    obj?.league_id,
    obj?.leagueId,
    obj?.competition_id,
    obj?.competitionId,
    obj?.tournament_id,
    obj?.tournamentId,
    context?.leagueId,
    context?.league_id,
    context?.currentLeagueId,
    matchId
  ];

  for (const candidate of candidates) {
    const directLeagueId = normalizeLeagueId(candidate);
    if (directLeagueId) {
      return directLeagueId;
    }

    const matchLeagueId = extractLeagueIdFromMatchId(candidate);
    if (matchLeagueId) {
      return matchLeagueId;
    }
  }

  return null;
}

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
      const normalizeTeamText = (primaryValue, fallbackValue) => {
        const pickText = (value) => {
          if (typeof value === 'string') {
            return value.trim();
          }
          if (typeof value === 'number') {
            return '';
          }
          if (value && typeof value === 'object') {
            return String(value.name || value.title || '').trim();
          }
          return '';
        };

        return pickText(primaryValue) || pickText(fallbackValue);
      };

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
        homeTeam = normalizeTeamText(
          obj.homeTeam || obj.homeName || obj['home-name'],
          obj.home || obj.home_team || obj.team1
        );
        awayTeam = normalizeTeamText(
          obj.awayTeam || obj.awayName || obj['away-name'],
          obj.away || obj.away_team || obj.team2
        );
      }

      homeTeam = normalizeTeamText(homeTeam, obj['home-name']);
      awayTeam = normalizeTeamText(awayTeam, obj['away-name']);
      if (!homeTeam || !awayTeam) {
        return null;
      }
      if (exceedsSafeLength(homeTeam, MAX_TEAM_NAME_LENGTH) || exceedsSafeLength(awayTeam, MAX_TEAM_NAME_LENGTH)) {
        return null;
      }

      const rawHash = obj.hash || obj.eventHash || obj.encodeEventId || obj.id || obj.matchId || obj.eventId || '';
      const hash = normalizeEventHash(rawHash);
      if (!isCanonicalEventHash(hash)) {
        return null;
      }
      const rawUrl = obj.url || obj.link || '';
      const urlContext = extractLeagueContextFromUrl(rawUrl);
      const sourceUrlContext = extractLeagueContextFromUrl(
        this.sourceUrl || this.resultsUrl || this.leagueUrl || ''
      );
      const rawUrlLooksLikeH2H = /\/football\/h2h\//i.test(rawUrl);
      const rawUrlLooksLikeMatchRoute = /\/match\/[^/]+\/?$/iu.test(rawUrl);
      const resolvedCountryContext = rawUrlLooksLikeH2H
        ? (sourceUrlContext.countrySlug || urlContext.countrySlug)
        : (urlContext.countrySlug || sourceUrlContext.countrySlug);
      const resolvedLeagueContext = rawUrlLooksLikeH2H
        ? (sourceUrlContext.leagueSlug || urlContext.leagueSlug)
        : (urlContext.leagueSlug || sourceUrlContext.leagueSlug);
      const countrySlug = normalizeSlugToken(
        obj.countrySlug || obj.country || resolvedCountryContext
      );
      const leagueSlug = normalizeSlugToken(
        obj.leagueSlug || obj.competitionSlug || resolvedLeagueContext
      );
      const matchId = String(obj.match_id || obj.matchId || obj.localMatchId || '').trim();
      const matchDate = obj.matchDate || obj.match_date || (
        obj['date-start-timestamp']
          ? new Date(Number(obj['date-start-timestamp']) * 1000).toISOString()
          : null
      );
      const payloadSlug = normalizeSlugToken(obj.slug || obj.eventSlug || extractEventSlugFromUrl(rawUrl));
      if (payloadSlug && exceedsSafeLength(payloadSlug, MAX_SLUG_LENGTH)) {
        return null;
      }
      const leagueId = resolveLeagueId(this, obj, matchId);
      const annualLeagueIds = resolveAnnualLeagueIds(this);
      const isAnnualLeague = Number.isInteger(leagueId) && annualLeagueIds.has(leagueId);
      const isBrazilSerieA = countrySlug === 'brazil'
        && (/^serie-a(?:-|$)/.test(leagueSlug) || leagueSlug === 'brasileirao');
      const fallbackSlug = buildFallbackEventSlug(homeTeam, awayTeam);
      if (fallbackSlug && exceedsSafeLength(fallbackSlug, MAX_SLUG_LENGTH)) {
        return null;
      }
      const shouldPromoteFallbackSlug = !payloadSlug
        && fallbackSlug
        && isAnnualLeague
        && Boolean(
          matchId
          || matchDate
          || rawUrlLooksLikeH2H
          || rawUrlLooksLikeMatchRoute
          || sourceUrlContext.countrySlug
          || sourceUrlContext.leagueSlug
        );
      const slug = payloadSlug || (shouldPromoteFallbackSlug ? fallbackSlug : '');
      const canonicalCountrySlug = isBrazilSerieA ? 'brazil' : countrySlug;
      const canonicalLeagueSlug = isBrazilSerieA ? 'serie-a' : leagueSlug;
      const canonicalUrl = isCanonicalEventHash(hash) && slug && countrySlug && leagueSlug
        ? `${this.baseUrl}/football/${canonicalCountrySlug}/${canonicalLeagueSlug}/${slug}-${hash}/`
        : '';

      let url = rawUrl;
      if (url && url.startsWith('/')) {
        url = `${this.baseUrl}${url}`;
      }
      if (canonicalUrl && (rawUrlLooksLikeH2H || rawUrlLooksLikeMatchRoute || !url)) {
        url = canonicalUrl;
      } else if (!url && canonicalUrl) {
        url = canonicalUrl;
      }

      if (!url || !isTrustedOddsPortalUrl(url, hash)) {
        return null;
      }

      return {
        url,
        hash: hash.toString(),
        slug,
        homeTeam,
        awayTeam,
        matchDate,
        source
      };
    } catch {
      return null;
    }
  }
};

module.exports = { reconMatchExtractor, isTrustedOddsPortalUrl };
