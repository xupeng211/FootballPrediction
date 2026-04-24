'use strict';

const reconConfig = require('../../config/recon_config.json');
const routeConfig = require('../../config/odds_harvest_routes.json');
const { Normalizer } = require('../../src/utils/Normalizer');
const { resolveSeasonContext } = require('./helpers/seasonRuntimeConfig');

const { season: TARGET_SEASON, seasonTag: TARGET_SEASON_TAG } = resolveSeasonContext({
  seasonEnvVar: 'ODDS_HARVEST_SEASON',
  seasonTagEnvVar: 'ODDS_HARVEST_SEASON_TAG'
});
const DEFAULT_USER_AGENT = process.env.ODDS_HARVEST_USER_AGENT
  || 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36';
const DEFAULT_CONCURRENCY = Math.max(
  1,
  Number.parseInt(process.env.ODDS_HARVEST_WORKERS || '24', 10)
);
const DEFAULT_PROGRESS_EVERY = Math.max(
  1,
  Number.parseInt(process.env.ODDS_HARVEST_PROGRESS_EVERY || '25', 10)
);
const DEFAULT_L3_BATCH_SIZE = Math.max(
  0,
  Number.parseInt(process.env.ODDS_HARVEST_L3_EVERY || '200', 10)
);
const DEFAULT_RETRIES = Math.max(
  1,
  Number.parseInt(process.env.ODDS_HARVEST_RETRIES || '3', 10)
);
const DEFAULT_RETRY_DELAY_MS = Math.max(
  100,
  Number.parseInt(process.env.ODDS_HARVEST_RETRY_DELAY_MS || '1200', 10)
);
const MATCH_DELTA_HOURS = Math.max(
  1,
  Number.parseInt(process.env.ODDS_HARVEST_MATCH_DELTA_HOURS || '72', 10)
);
const MATCH_DELTA_MS = MATCH_DELTA_HOURS * 60 * 60 * 1000;
const OPENING_BOOKMAKER = 'oddsportal_median_opening';
const CURRENT_BOOKMAKER = 'oddsportal_median_current';
const ONE_X_TWO_MARKET_KEY = 'E-1-2-0-0-0';
const RESULTS_BASE_URL = reconConfig.oddsportal?.base_url || 'https://www.oddsportal.com';
const MONTHS = Object.freeze({
  jan: 0,
  january: 0,
  feb: 1,
  february: 1,
  mar: 2,
  march: 2,
  apr: 3,
  april: 3,
  may: 4,
  jun: 5,
  june: 5,
  jul: 6,
  july: 6,
  aug: 7,
  august: 7,
  sep: 8,
  sept: 8,
  september: 8,
  oct: 9,
  october: 9,
  nov: 10,
  november: 10,
  dec: 11,
  december: 11
});
const ODDSPORTAL_TEAM_ALIASES = Object.freeze({
  'Manchester Utd': 'Manchester United',
  'Man Utd': 'Manchester United',
  'Manchester City': 'Manchester City',
  Newcastle: 'Newcastle United',
  'Newcastle Utd': 'Newcastle United',
  Tottenham: 'Tottenham Hotspur',
  Spurs: 'Tottenham Hotspur',
  Nottingham: 'Nottingham Forest',
  Wolves: 'Wolverhampton Wanderers',
  Brighton: 'Brighton & Hove Albion',
  Bournemouth: 'AFC Bournemouth',
  Leicester: 'Leicester City',
  'West Ham': 'West Ham United',
  Ipswich: 'Ipswich Town',
  'Crystal Palace': 'Crystal Palace',
  Leverkusen: 'Bayer Leverkusen',
  'Bayern Munich': 'Bayern Munich',
  Dortmund: 'Borussia Dortmund',
  Monchengladbach: 'Borussia Monchengladbach',
  'B. Monchengladbach': 'Borussia Monchengladbach',
  'Borussia Mgladbach': 'Borussia Monchengladbach',
  "M'gladbach": 'Borussia Monchengladbach',
  'Ein Frankfurt': 'Eintracht Frankfurt',
  Frankfurt: 'Eintracht Frankfurt',
  'RB Leipzig': 'RB Leipzig',
  Leipzig: 'RB Leipzig',
  Heidenheim: 'FC Heidenheim',
  Verona: 'Hellas Verona',
  Inter: 'Inter Milan',
  Milan: 'Milan',
  'AC Milan': 'Milan',
  'Atl. Madrid': 'Atletico Madrid',
  'Ath Bilbao': 'Athletic Club',
  'Athletic Bilbao': 'Athletic Club',
  Betis: 'Real Betis',
  Valladolid: 'Real Valladolid',
  Sociedad: 'Real Sociedad',
  Alaves: 'Deportivo Alaves',
  Celta: 'Celta Vigo',
  PSG: 'Paris Saint Germain',
  'Paris SG': 'Paris Saint Germain',
  Marseille: 'Olympique Marseille',
  Lyon: 'Olympique Lyon',
  Rennes: 'Stade Rennais',
  'St Etienne': 'FC Saint Etienne',
  'Club Brugge KV': 'Club Brugge',
  'Olympiacos Piraeus': 'Olympiacos',
  PAOK: 'Paok Thessaloniki',
  'PAOK Thessaloniki': 'Paok Thessaloniki',
  'Royale Union SG': 'Union St Gilloise',
  'Union Saint-Gilloise': 'Union St Gilloise',
  'Dyn. Kyiv': 'Dynamo Kyiv',
  'Dynamo Kiev': 'Dynamo Kyiv',
  Qarabag: 'Qarabag Fk',
  'Qarabag FK': 'Qarabag Fk'
});

function normalizeStringList(value) {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.map((entry) => String(entry || '').trim()).filter(Boolean);
}

function normalizeLeagueRoute(route) {
  return {
    leagueName: String(route?.leagueName || '').trim(),
    country: String(route?.country || '').trim(),
    slug: String(route?.slug || '').trim(),
    expectedMatches: Number.parseInt(route?.expectedMatches, 10),
    seasonType: String(route?.seasonType || 'dual_year').trim().toLowerCase(),
    resultsUrlStrategy: String(route?.resultsUrlStrategy || 'seasonal').trim().toLowerCase(),
    additionalResultsPaths: normalizeStringList(route?.additionalResultsPaths),
    additionalHistoricalResultsPaths: normalizeStringList(route?.additionalHistoricalResultsPaths),
    resultsPathTemplate: String(route?.resultsPathTemplate || '').trim() || null
  };
}

function isValidLeagueRoute(route) {
  return Boolean(
    route.leagueName
    && route.country
    && route.slug
    && Number.isInteger(route.expectedMatches)
    && route.expectedMatches > 0
    && ['dual_year', 'single_year'].includes(route.seasonType)
    && ['seasonal', 'seasonless'].includes(route.resultsUrlStrategy)
  );
}

function buildLeagueRouteCatalog() {
  const routes = Array.isArray(routeConfig?.routes) ? routeConfig.routes : [];
  if (routes.length === 0) {
    throw new Error('config/odds_harvest_routes.json 未声明任何联赛路由');
  }

  const catalog = {};
  for (const route of routes) {
    const normalizedRoute = normalizeLeagueRoute(route);
    if (!isValidLeagueRoute(normalizedRoute)) {
      throw new Error(`无效联赛路由配置: ${JSON.stringify(route)}`);
    }

    catalog[normalizedRoute.leagueName] = Object.freeze({
      ...normalizedRoute,
      additionalResultsPaths: Object.freeze(normalizedRoute.additionalResultsPaths),
      additionalHistoricalResultsPaths: Object.freeze(normalizedRoute.additionalHistoricalResultsPaths)
    });
  }

  return Object.freeze(catalog);
}

const LEAGUE_ROUTE_CATALOG = buildLeagueRouteCatalog();

const COVERAGE_SQL = `
  SELECT
      COUNT(*)::int AS total_matches,
      COUNT(*) FILTER (
          WHERE m.pipeline_status IN ('harvested', 'RECON_LINKED')
      )::int AS active_matches,
      COUNT(*) FILTER (
          WHERE COALESCE((l3.odds_features->>'has_odds_data')::boolean, FALSE) = FALSE
      )::int AS l3_gap,
      COUNT(*) FILTER (
          WHERE (
              SELECT COUNT(*)
              FROM odds o
              WHERE o.match_id = m.match_id
                AND o.bookmaker IN ($2, $3)
          ) < 2
      )::int AS odds_gap,
      COUNT(*) FILTER (
          WHERE (
              SELECT COUNT(*)
              FROM odds o
              WHERE o.match_id = m.match_id
                AND o.bookmaker IN ($2, $3)
          ) >= 2
      )::int AS odds_complete
  FROM matches m
  LEFT JOIN l3_features l3 ON l3.match_id = m.match_id
  WHERE m.season = $1
`;

const TARGETS_SQL = `
  SELECT
      m.match_id,
      m.external_id,
      m.league_name,
      m.home_team,
      m.away_team,
      m.match_date,
      COALESCE((l3.odds_features->>'has_odds_data')::boolean, FALSE) AS l3_has_odds
  FROM matches m
  LEFT JOIN l3_features l3 ON l3.match_id = m.match_id
  WHERE m.season = $1
    AND m.pipeline_status IN ('harvested', 'RECON_LINKED')
    AND (
      SELECT COUNT(*)
      FROM odds o
      WHERE o.match_id = m.match_id
        AND o.bookmaker IN ($2, $3)
    ) < 2
  ORDER BY m.match_date ASC, m.match_id ASC
`;

const UPSERT_MAPPING_SQL = `
  INSERT INTO matches_oddsportal_mapping (
      match_id,
      oddsportal_hash,
      full_url,
      season,
      league_name,
      home_team,
      away_team,
      status,
      match_confidence,
      mapping_method,
      is_reversed,
      is_evidence_only,
      retry_count,
      last_error,
      harvested_at,
      created_at,
      updated_at
  ) VALUES (
      $1, $2, $3, $4, $5, $6, $7,
      'harvested',
      $8,
      'protocol_extract',
      $9,
      FALSE,
      0,
      NULL,
      NOW(),
      NOW(),
      NOW()
  )
  ON CONFLICT (match_id, season) DO UPDATE SET
      oddsportal_hash = EXCLUDED.oddsportal_hash,
      full_url = EXCLUDED.full_url,
      league_name = EXCLUDED.league_name,
      home_team = EXCLUDED.home_team,
      away_team = EXCLUDED.away_team,
      status = 'harvested',
      match_confidence = EXCLUDED.match_confidence,
      mapping_method = 'protocol_extract',
      is_reversed = EXCLUDED.is_reversed,
      is_evidence_only = FALSE,
      retry_count = 0,
      last_error = NULL,
      harvested_at = NOW(),
      updated_at = NOW()
`;

const UPSERT_ODDS_SQL = `
  INSERT INTO odds (
      match_id,
      bookmaker,
      home_odds,
      draw_odds,
      away_odds,
      collected_at
  ) VALUES ($1, $2, $3, $4, $5, $6)
  ON CONFLICT (match_id, bookmaker) DO UPDATE SET
      home_odds = EXCLUDED.home_odds,
      draw_odds = EXCLUDED.draw_odds,
      away_odds = EXCLUDED.away_odds,
      collected_at = EXCLUDED.collected_at
`;

function buildDefaultOptions() {
  return {
    season: TARGET_SEASON,
    concurrency: DEFAULT_CONCURRENCY,
    limit: null,
    progressEvery: DEFAULT_PROGRESS_EVERY,
    l3Every: DEFAULT_L3_BATCH_SIZE,
    l3Workers: Number.parseInt(process.env.L3_STITCH_WORKERS || '12', 10),
    l3Enabled: true,
    mappingOnly: false,
    skipDomFilter: false,
    dryRun: false,
    leagues: [],
    retries: DEFAULT_RETRIES
  };
}

function parseCountArg(value, minimum) {
  return Math.max(minimum, Number.parseInt(value, 10));
}

function addLeague(options, value) {
  options.leagues.push(value.trim());
}

function setSeason(options, value) {
  options.season = Normalizer.normalizeSeason(value);
}

function setLimit(options, value) {
  options.limit = parseCountArg(value, 1);
}

function setConcurrency(options, value) {
  options.concurrency = parseCountArg(value, 1);
}

function setProgressEvery(options, value) {
  options.progressEvery = parseCountArg(value, 1);
}

function setL3Every(options, value) {
  options.l3Every = Math.max(0, Number.parseInt(value, 10));
}

function setL3Workers(options, value) {
  options.l3Workers = parseCountArg(value, 1);
}

function setRetries(options, value) {
  options.retries = parseCountArg(value, 1);
}

const VALUE_ARG_HANDLERS = Object.freeze({
  '--season': setSeason,
  '--league': addLeague,
  '--limit': setLimit,
  '--workers': setConcurrency,
  '--progress-every': setProgressEvery,
  '--l3-every': setL3Every,
  '--l3-workers': setL3Workers,
  '--retries': setRetries
});

const FLAG_ARG_HANDLERS = Object.freeze({
  '--mapping-only': (options) => {
    options.mappingOnly = true;
  },
  '--skip-dom-filter': (options) => {
    options.skipDomFilter = true;
  },
  '--skip-l3': (options) => {
    options.l3Enabled = false;
  },
  '--dry-run': (options) => {
    options.dryRun = true;
  }
});

function parseArgs(argv) {
  const options = buildDefaultOptions();

  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    const valueHandler = VALUE_ARG_HANDLERS[token];

    if (valueHandler && argv[index + 1]) {
      valueHandler(options, argv[index + 1]);
      index += 1;
      continue;
    }

    const flagHandler = FLAG_ARG_HANDLERS[token];
    if (flagHandler) {
      flagHandler(options);
    }
  }

  if (options.leagues.length === 0) {
    options.leagues = Object.keys(LEAGUE_ROUTE_CATALOG);
  }

  return options;
}

function sleep(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function normalizePositiveNumber(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 1.01 && parsed < 100 ? parsed : null;
}

function median(values) {
  if (!Array.isArray(values) || values.length === 0) {
    return null;
  }
  const sorted = [...values].sort((left, right) => left - right);
  const middle = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 1) {
    return sorted[middle];
  }
  return (sorted[middle - 1] + sorted[middle]) / 2;
}

function toIsoTimestamp(seconds, fallbackMs) {
  const numeric = Number(seconds);
  if (Number.isFinite(numeric) && numeric > 0) {
    return new Date(numeric * 1000).toISOString();
  }
  if (Number.isFinite(fallbackMs) && fallbackMs > 0) {
    return new Date(fallbackMs).toISOString();
  }
  return new Date().toISOString();
}

function extractSnapshot(points) {
  const homeValues = points.map((point) => point.home).filter(Boolean);
  const drawValues = points.map((point) => point.draw).filter(Boolean);
  const awayValues = points.map((point) => point.away).filter(Boolean);

  if (homeValues.length === 0 || drawValues.length === 0 || awayValues.length === 0) {
    return null;
  }

  return {
    home: median(homeValues),
    draw: median(drawValues),
    away: median(awayValues)
  };
}

function findOneXTwoMarket(back = {}) {
  if (back?.[ONE_X_TWO_MARKET_KEY]) {
    return back[ONE_X_TWO_MARKET_KEY];
  }

  return Object.values(back || {}).find((entry) => (
    Number(entry?.bettingTypeId) === 1
    && Number(entry?.scopeId) === 2
    && Number(entry?.handicapTypeId || 0) === 0
  )) || null;
}

function buildPointSnapshot(triplet, timestamp) {
  const home = normalizePositiveNumber(triplet?.[0]);
  const draw = normalizePositiveNumber(triplet?.[1]);
  const away = normalizePositiveNumber(triplet?.[2]);

  if (!home || !draw || !away) {
    return null;
  }

  return {
    home,
    draw,
    away,
    collectedAt: timestamp
  };
}

function collectProviderIds(market = {}) {
  return new Set([
    ...Object.keys(market.odds || {}),
    ...Object.keys(market.openingOdd || {})
  ]);
}

function resolveCurrentTimestamp(market, providerId, kickoffMs) {
  const currentSeconds = Math.max(
    Number(market?.changeTime?.[providerId]?.[0] || 0),
    Number(market?.changeTime?.[providerId]?.[1] || 0),
    Number(market?.changeTime?.[providerId]?.[2] || 0)
  );
  return toIsoTimestamp(currentSeconds, kickoffMs);
}

function resolveOpeningTimestamp(market, providerId, kickoffMs) {
  const validSeconds = [0, 1, 2]
    .map((outcomeId) => Number(market?.openingChangeTime?.[providerId]?.[outcomeId] || 0))
    .filter((value) => Number.isFinite(value) && value > 0);
  const openingSeconds = validSeconds.length > 0 ? Math.min(...validSeconds) : 0;
  const fallbackMs = kickoffMs ? kickoffMs - (7 * 24 * 60 * 60 * 1000) : Date.now();
  return toIsoTimestamp(openingSeconds, fallbackMs);
}

function collectProviderPoints(market, providerIds, kickoffMs) {
  const currentPoints = [];
  const openingPoints = [];

  for (const providerId of providerIds) {
    const currentPoint = buildPointSnapshot(
      market?.odds?.[providerId],
      resolveCurrentTimestamp(market, providerId, kickoffMs)
    );
    if (currentPoint) {
      currentPoints.push(currentPoint);
    }

    const openingPoint = buildPointSnapshot(
      market?.openingOdd?.[providerId],
      resolveOpeningTimestamp(market, providerId, kickoffMs)
    );
    if (openingPoint) {
      openingPoints.push(openingPoint);
    }
  }

  return {
    currentPoints,
    openingPoints
  };
}

function latestCollectedAt(points, fallbackValue) {
  const latest = points
    .map((point) => point.collectedAt)
    .filter(Boolean)
    .sort()
    .slice(-1)[0];
  return latest || fallbackValue;
}

function buildSnapshotEntry(snapshot, fallback, collectedAt) {
  return {
    ...(snapshot || fallback),
    collectedAt
  };
}

function extractMedianOddsSnapshots(preMatchPayload, kickoffMs) {
  const market = findOneXTwoMarket(preMatchPayload?.d?.oddsdata?.back || {});
  if (!market) {
    return null;
  }

  const providerIds = collectProviderIds(market);
  const { currentPoints, openingPoints } = collectProviderPoints(market, providerIds, kickoffMs);
  const current = extractSnapshot(currentPoints);
  const opening = extractSnapshot(openingPoints);

  if (!current && !opening) {
    return null;
  }

  const fallback = current || opening;
  const fallbackCollectedAt = fallback?.collectedAt || toIsoTimestamp(null, kickoffMs);

  return {
    opening: buildSnapshotEntry(
      opening,
      fallback,
      openingPoints[0]?.collectedAt || fallbackCollectedAt
    ),
    current: buildSnapshotEntry(
      current || opening,
      fallback,
      latestCollectedAt(currentPoints, fallbackCollectedAt)
    ),
    providerCount: providerIds.size
  };
}

function normalizeTitleKey(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

module.exports = {
  COVERAGE_SQL,
  CURRENT_BOOKMAKER,
  DEFAULT_CONCURRENCY,
  DEFAULT_L3_BATCH_SIZE,
  DEFAULT_PROGRESS_EVERY,
  DEFAULT_RETRIES,
  DEFAULT_RETRY_DELAY_MS,
  DEFAULT_USER_AGENT,
  LEAGUE_ROUTE_CATALOG,
  MATCH_DELTA_MS,
  MONTHS,
  ODDSPORTAL_TEAM_ALIASES,
  OPENING_BOOKMAKER,
  RESULTS_BASE_URL,
  TARGETS_SQL,
  TARGET_SEASON,
  TARGET_SEASON_TAG,
  UPSERT_MAPPING_SQL,
  UPSERT_ODDS_SQL,
  extractMedianOddsSnapshots,
  normalizeTitleKey,
  parseArgs,
  sleep
};
