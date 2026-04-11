'use strict';

const crypto = require('crypto');
const RECON_CONFIG = require('../../../../config/recon_config.json');
const { Normalizer } = require('../../../utils/Normalizer');

const ODDSPORTAL_BASE_URL = RECON_CONFIG.oddsportal?.base_url || 'https://www.oddsportal.com';
const ODDSPORTAL_LEAGUES = RECON_CONFIG.leagues || {};
const TEAM_COMPOUND_TOKENS = new Set([
  'ac',
  'atletico',
  'bayer',
  'bayern',
  'borussia',
  'crystal',
  'inter',
  'los',
  'manchester',
  'newcastle',
  'nottingham',
  'paris',
  'porto',
  'psv',
  'real',
  'saint',
  'san',
  'sporting',
  'tottenham',
  'west',
  'wolverhampton'
]);

function buildOddsPortalLeagueCatalog() {
  const catalog = {};

  for (const [key, entry] of Object.entries(ODDSPORTAL_LEAGUES)) {
    if (!entry || !entry.name || !entry.country || !entry.slug) {
      continue;
    }

    const normalizedEntry = {
      key,
      name: entry.name,
      country: entry.country,
      slug: entry.slug
    };

    catalog[key] = normalizedEntry;
    catalog[entry.name] = normalizedEntry;
    catalog[entry.slug] = normalizedEntry;
    catalog[entry.name.toLowerCase()] = normalizedEntry;
    catalog[entry.slug.toLowerCase()] = normalizedEntry;
  }

  return Object.freeze(catalog);
}

const ODDSPORTAL_LEAGUE_CATALOG = buildOddsPortalLeagueCatalog();

function slugifyPathSegment(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/&/g, ' and ')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .replace(/-+/g, '-');
}

function buildDeterministicMatchHash(pathname) {
  return crypto
    .createHash('md5')
    .update(String(pathname || '').toLowerCase())
    .digest('hex')
    .slice(0, 8);
}

function normalizeTeamSegment(segment) {
  const slug = slugifyPathSegment(segment);
  if (!slug) {
    return null;
  }

  const normalized = Normalizer.normalizeTeamName(slug.replace(/-/g, ' '));
  return normalized || slug.replace(/-/g, ' ');
}

function scoreTeamSegment(segment) {
  const slug = slugifyPathSegment(segment);
  if (!slug) {
    return -1;
  }

  const tokens = slug.split('-').filter(Boolean);
  let score = tokens.length > 1 ? 1.25 : 1.0;

  if (tokens.length > 1 && TEAM_COMPOUND_TOKENS.has(tokens[0])) {
    score += 1.0;
  }

  const normalized = Normalizer.normalizeTeamName(slug.replace(/-/g, ' '));
  const normalizedSlug = slugifyPathSegment(normalized);
  if (normalizedSlug && normalizedSlug !== slug) {
    score += 0.75;
  }

  return score;
}

function parseMatchTeams(matchSlug) {
  const decodedSlug = slugifyPathSegment(decodeURIComponent(matchSlug || ''));
  if (!decodedSlug) {
    return { home_team: null, away_team: null };
  }

  if (decodedSlug.includes('-vs-')) {
    const [home, away] = decodedSlug.split('-vs-');
    return {
      home_team: normalizeTeamSegment(home),
      away_team: normalizeTeamSegment(away)
    };
  }

  const tokens = decodedSlug.split('-').filter(Boolean);
  if (tokens.length < 2) {
    return {
      home_team: normalizeTeamSegment(decodedSlug),
      away_team: null
    };
  }

  if (tokens.length === 2) {
    return {
      home_team: normalizeTeamSegment(tokens[0]),
      away_team: normalizeTeamSegment(tokens[1])
    };
  }

  let bestSplit = null;

  for (let index = 1; index < tokens.length; index++) {
    const left = tokens.slice(0, index).join('-');
    const right = tokens.slice(index).join('-');
    const score = scoreTeamSegment(left) + scoreTeamSegment(right);

    if (!bestSplit || score > bestSplit.score) {
      bestSplit = { left, right, score };
    }
  }

  return {
    home_team: normalizeTeamSegment(bestSplit?.left),
    away_team: normalizeTeamSegment(bestSplit?.right)
  };
}

module.exports = {
  ODDSPORTAL_BASE_URL,
  ODDSPORTAL_LEAGUE_CATALOG,
  buildDeterministicMatchHash,
  parseMatchTeams,
  slugifyPathSegment
};
