#!/usr/bin/env node
/* eslint-disable max-lines */
'use strict';

require('dotenv').config();

const fs = require('node:fs');
const path = require('node:path');

const { chromium } = require('playwright');
const { Pool } = require('pg');

const { ReconPureDecryptor } = require('../../src/infrastructure/recon/services/ReconPureDecryptor');
const { extractGoldenFeatures } = require('../../src/feature_engine/extractors/GoldenFeatureExtractor');
const { extractTacticalFeatures } = require('../../src/feature_engine/extractors/TacticalMomentumExtractor');
const {
  extractOddsMovementFeaturesFromOddsData
} = require('../../src/feature_engine/extractors/OddsMovementExtractor');
const {
  CURRENT_BOOKMAKER,
  DEFAULT_RETRIES,
  DEFAULT_RETRY_DELAY_MS,
  DEFAULT_USER_AGENT,
  OPENING_BOOKMAKER,
  UPSERT_ODDS_SQL,
  extractMedianOddsSnapshots
} = require('./odds_harvest_pipeline.shared');
const { resolveSeasonContext } = require('./helpers/seasonRuntimeConfig');

const RESULTS_BASE_URL = 'https://www.oddsportal.com';
const { season: TARGET_SEASON } = resolveSeasonContext({
  seasonEnvVar: 'ODDS_SNIPER_SEASON',
  seasonTagEnvVar: 'ODDS_SNIPER_SEASON_TAG'
});
const DEFAULT_PROXY_PROTOCOL = process.env.PROXY_PROTOCOL || 'socks5';
const DEFAULT_PROXY_HOST = process.env.PROXY_HOST || process.env.WSL2_PROXY_HOST || '127.0.0.1';
const DEFAULT_PROXY_PORT = Number.parseInt(process.env.ODDS_SNIPER_PROXY_PORT || '10001', 10);
const DEFAULT_FETCH_TIMEOUT_MS = Number.parseInt(process.env.ODDS_SNIPER_FETCH_TIMEOUT_MS || '60000', 10);
const DEFAULT_PAGE_SETTLE_MS = Number.parseInt(process.env.ODDS_SNIPER_PAGE_SETTLE_MS || '10000', 10);

const FETCH_MATCH_ROWS_SQL = `
  SELECT
      m.match_id,
      m.external_id,
      m.season,
      m.league_name,
      m.home_team,
      m.away_team,
      m.match_date,
      m.pipeline_status,
      r.raw_data
  FROM matches m
  INNER JOIN raw_match_data r ON r.match_id = m.match_id
  WHERE m.match_id = ANY($1::varchar[])
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
      $9,
      FALSE,
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
      mapping_method = EXCLUDED.mapping_method,
      is_reversed = FALSE,
      is_evidence_only = FALSE,
      retry_count = 0,
      last_error = NULL,
      harvested_at = NOW(),
      updated_at = NOW()
`;

const FETCH_CANONICAL_ODDS_SQL = `
  SELECT
      id,
      match_id,
      bookmaker,
      home_odds,
      draw_odds,
      away_odds,
      collected_at
  FROM odds
  WHERE match_id = ANY($1::varchar[])
    AND home_odds IS NOT NULL
    AND draw_odds IS NOT NULL
    AND away_odds IS NOT NULL
  ORDER BY match_id ASC, collected_at ASC NULLS LAST, id ASC
`;

const UPSERT_L3_SQL = `
  INSERT INTO l3_features (
      match_id,
      external_id,
      golden_features,
      tactical_features,
      odds_movement_features,
      odds_features,
      elo_features,
      rolling_features,
      efficiency_features,
      draw_features,
      market_sentiment,
      stitch_summary,
      computed_at,
      updated_at
  ) VALUES (
      $1, $2, $3::jsonb, $4::jsonb, $5::jsonb, $6::jsonb, '{}'::jsonb, '{}'::jsonb,
      '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, $7::jsonb, NOW(), NOW()
  )
  ON CONFLICT (match_id) DO UPDATE SET
      external_id = EXCLUDED.external_id,
      golden_features = EXCLUDED.golden_features,
      tactical_features = EXCLUDED.tactical_features,
      odds_movement_features = EXCLUDED.odds_movement_features,
      odds_features = EXCLUDED.odds_features,
      stitch_summary = EXCLUDED.stitch_summary,
      computed_at = EXCLUDED.computed_at,
      updated_at = NOW()
`;

const FINAL_ODDS_SQL = `
  SELECT
      match_id,
      bookmaker,
      home_odds,
      draw_odds,
      away_odds,
      collected_at
  FROM odds
  WHERE match_id = ANY($1::varchar[])
  ORDER BY match_id ASC, bookmaker ASC
`;

const FINAL_NONE_SQL = `
  SELECT COUNT(*)::int AS odds_source_none
  FROM l3_features
  WHERE COALESCE(odds_features->>'odds_source', 'none') = 'none'
`;

const pool = new Pool({
  host: process.env.DB_HOST || '127.0.0.1',
  port: Number.parseInt(process.env.DB_PORT || '5432', 10),
  database: process.env.DB_NAME || 'football_db',
  user: process.env.DB_USER || 'football_user',
  password: process.env.DB_PASSWORD || '',
  max: 8
});

function createSilentLogger() {
  return {
    info() {},
    warn() {},
    error() {},
    debug() {}
  };
}

function normalizeText(value) {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

function sleep(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
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

function toPositiveNumber(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

function ensureTargetShape(target) {
  const normalized = {
    match_id: normalizeText(target?.match_id),
    url: normalizeText(target?.url),
    hash: normalizeText(target?.hash),
    season: normalizeText(target?.season) || TARGET_SEASON
  };

  if (!normalized.match_id) {
    throw new Error(`无效目标: 缺少 match_id -> ${JSON.stringify(target)}`);
  }
  if (!normalized.url) {
    throw new Error(`无效目标 ${normalized.match_id}: 缺少 url`);
  }
  if (!normalized.hash) {
    const inferred = inferHashFromUrl(normalized.url);
    if (!inferred) {
      throw new Error(`无效目标 ${normalized.match_id}: 缺少 hash 且无法从 url 推断`);
    }
    normalized.hash = inferred;
  }

  return normalized;
}

function inferHashFromUrl(url) {
  const hashMatch = /#([A-Za-z0-9]{8})$/.exec(String(url || '').trim());
  if (hashMatch) {
    return hashMatch[1];
  }

  const pathMatch = /-([A-Za-z0-9]{8})\/?(?:[#?].*)?$/.exec(String(url || '').trim());
  return pathMatch ? pathMatch[1] : '';
}

function parseArgs(argv) {
  const options = {
    matchIds: [],
    dryRun: false,
    skipHarvest: false,
    skipStitch: false,
    useProxy: false,
    proxyServer: '',
    targetsFile: ''
  };

  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];

    if (token === '--match-id' && argv[index + 1]) {
      options.matchIds.push(normalizeText(argv[index + 1]));
      index += 1;
      continue;
    }

    if (token === '--targets-file' && argv[index + 1]) {
      options.targetsFile = normalizeText(argv[index + 1]);
      index += 1;
      continue;
    }

    if (token === '--proxy-server' && argv[index + 1]) {
      options.proxyServer = normalizeText(argv[index + 1]);
      options.useProxy = true;
      index += 1;
      continue;
    }

    if (token === '--dry-run') {
      options.dryRun = true;
      continue;
    }

    if (token === '--skip-harvest') {
      options.skipHarvest = true;
      continue;
    }

    if (token === '--skip-stitch') {
      options.skipStitch = true;
      continue;
    }

    if (token === '--use-proxy') {
      options.useProxy = true;
    }
  }

  return options;
}

function resolveTargets(options) {
  if (!options.targetsFile) {
    throw new Error('必须提供 --targets-file，脚本不再内置 24/25 专项目标列表');
  }

  const filePath = path.resolve(process.cwd(), options.targetsFile);
  const parsed = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  if (!Array.isArray(parsed)) {
    throw new Error(`targets-file 必须是数组: ${filePath}`);
  }

  const catalog = new Map(parsed.map((target) => {
    const normalized = ensureTargetShape(target);
    return [normalized.match_id, normalized];
  }));

  if (options.matchIds.length === 0) {
    return [...catalog.values()];
  }

  return options.matchIds.map((matchId) => {
    const target = catalog.get(matchId);
    if (!target) {
      throw new Error(`targets-file 中不存在 match_id=${matchId}`);
    }
    return target;
  });
}

function parsePageVar(html) {
  const match = String(html || '').match(/var\s+pageVar\s*=\s*'([\s\S]*?)';/i);
  if (!match) {
    return null;
  }

  const candidates = [
    match[1],
    match[1].replace(/\\'/g, '\'')
  ];

  for (const candidate of candidates) {
    try {
      return JSON.parse(candidate);
    } catch {
      // try next variant
    }
  }

  return null;
}

function extractBundleUrl(html) {
  const scriptMatch = [...String(html || '').matchAll(
    /(?:src|href)=["']([^"']*\/build\/assets\/app-[^"']+\.js[^"']*)["']/g
  )][0]?.[1]
    || [...String(html || '').matchAll(
      /https:\/\/www\.oddsportal\.com\/build\/assets\/app-[^"']+\.js/g
    )][0]?.[0];

  return scriptMatch ? new URL(scriptMatch, RESULTS_BASE_URL).toString() : '';
}

function buildMinimalEntryHtml(bundleUrl, locale = 'en') {
  const safeLocale = normalizeText(locale) || 'en';
  const safeBundleUrl = normalizeText(bundleUrl);
  return [
    '<!doctype html>',
    `<html lang="${safeLocale}">`,
    '<head>',
    '  <meta charset="utf-8">',
    `  <script type="module" src="${safeBundleUrl}"></script>`,
    '</head>',
    '<body></body>',
    '</html>'
  ].join('\n');
}

async function fetchText(url, options = {}) {
  const retries = Math.max(1, Number(options.retries || DEFAULT_RETRIES));
  const timeoutMs = Number(options.timeoutMs || DEFAULT_FETCH_TIMEOUT_MS);
  const headers = {
    'user-agent': DEFAULT_USER_AGENT,
    'accept-language': 'en-US,en;q=0.9',
    ...options.headers
  };

  let lastError = null;
  for (let attempt = 1; attempt <= retries; attempt += 1) {
    try {
      const response = await fetch(url, {
        method: 'GET',
        headers,
        signal: AbortSignal.timeout(timeoutMs)
      });
      const text = await response.text();
      if (!response.ok) {
        throw new Error(`HTTP_${response.status}: ${text.slice(0, 200)}`);
      }
      return text;
    } catch (error) {
      lastError = error;
      if (attempt === retries) {
        break;
      }
      await sleep(DEFAULT_RETRY_DELAY_MS * attempt);
    }
  }

  throw lastError;
}

async function createProtocolContext(target) {
  const html = await fetchText(target.url, {
    headers: { referer: target.url }
  });
  const pageVar = parsePageVar(html);
  const bundleUrl = extractBundleUrl(html);
  if (!bundleUrl) {
    throw new Error(`未从页面提取到 app bundle: ${target.url}`);
  }

  const decryptor = new ReconPureDecryptor({
    logger: createSilentLogger(),
    traceId: `odds_sniper_${target.match_id}`
  });

  await decryptor.loadFromBundleUrl(bundleUrl, {
    html: buildMinimalEntryHtml(bundleUrl, pageVar?.locale || 'en'),
    headers: { referer: target.url },
    globals: {
      pageVar,
      location: { href: target.url }
    }
  });

  return {
    html,
    pageVar,
    bundleUrl,
    decryptor
  };
}

async function extractViaProtocol(target) {
  const context = await createProtocolContext(target);
  const ajaxPayload = await fetchText(
    `${RESULTS_BASE_URL}/ajax-event-data/${target.hash}/0`,
    { headers: { referer: target.url } }
  );
  const ajax = await context.decryptor.decrypt(ajaxPayload);
  const requestPreMatch = ajax?.d?.requestPreMatch?.url;
  const kickoffMs = Number(ajax?.d?.eventBody?.startDate || 0) * 1000;

  if (!requestPreMatch || !kickoffMs) {
    throw new Error(`旧 payload 缺少 requestPreMatch/startDate: ${target.match_id}`);
  }

  const preMatchPayload = await fetchText(
    `${RESULTS_BASE_URL}${requestPreMatch}`,
    { headers: { referer: target.url } }
  );
  const preMatch = await context.decryptor.decrypt(preMatchPayload);
  const oddsSnapshots = extractMedianOddsSnapshots(preMatch, kickoffMs);

  if (!oddsSnapshots) {
    throw new Error(`Pre-match payload 未提取到 1X2 中位赔率: ${target.match_id}`);
  }

  return {
    mode: 'protocol',
    mappingMethod: 'protocol_extract',
    bundleUrl: context.bundleUrl,
    geoIPcode: normalizeText(context.pageVar?.geoIPcode),
    requestPreMatch,
    oddsSnapshots
  };
}

function resolveProxyServer(options = {}, protocolMeta = {}) {
  if (options.proxyServer) {
    return options.proxyServer;
  }

  const restrictedGeo = new Set(['JP', 'KR']);
  const shouldUseProxy = options.useProxy || restrictedGeo.has(protocolMeta.geoIPcode);
  if (!shouldUseProxy) {
    return '';
  }

  if (!DEFAULT_PROXY_HOST || !DEFAULT_PROXY_PORT) {
    return '';
  }

  return `${DEFAULT_PROXY_PROTOCOL}://${DEFAULT_PROXY_HOST}:${DEFAULT_PROXY_PORT}`;
}

async function acceptCookieBanner(page) {
  const selectors = [
    '#onetrust-accept-btn-handler',
    'button:has-text("I Accept")',
    'button:has-text("Accept")'
  ];

  for (const selector of selectors) {
    const locator = page.locator(selector).first();
    if (await locator.isVisible().catch(() => false)) {
      await locator.click({ force: true }).catch(() => {});
      await page.waitForTimeout(1000);
      return;
    }
  }
}

function buildFallbackOddsFromTriplets(triplets, fallbackIso) {
  if (!Array.isArray(triplets) || triplets.length === 0) {
    return null;
  }

  const openingCandidates = triplets.filter((triplet) => /open|opening/i.test(triplet.text));
  const currentCandidates = triplets.filter((triplet) => /close|closing|current|latest|now/i.test(triplet.text));
  const openingRows = openingCandidates.length > 0 ? openingCandidates : [triplets[0]];
  const currentRows = currentCandidates.length > 0 ? currentCandidates : [triplets[triplets.length - 1]];

  const aggregate = (rows) => {
    const homes = rows.map((row) => row.home).filter(Boolean);
    const draws = rows.map((row) => row.draw).filter(Boolean);
    const aways = rows.map((row) => row.away).filter(Boolean);
    if (homes.length === 0 || draws.length === 0 || aways.length === 0) {
      return null;
    }
    return {
      home: median(homes),
      draw: median(draws),
      away: median(aways),
      collectedAt: fallbackIso
    };
  };

  const opening = aggregate(openingRows);
  const current = aggregate(currentRows);

  if (!opening && !current) {
    return null;
  }

  return {
    opening: opening || current,
    current: current || opening,
    providerCount: triplets.length
  };
}

async function extractViaDom(target, options = {}, protocolMeta = {}) {
  const proxyServer = resolveProxyServer(options, protocolMeta);
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
    ...(proxyServer ? { proxy: { server: proxyServer } } : {})
  });

  const manualSessionPath = path.resolve(process.cwd(), 'manual_session.json');
  const context = await browser.newContext({
    userAgent: DEFAULT_USER_AGENT,
    ...(fs.existsSync(manualSessionPath) ? { storageState: manualSessionPath } : {})
  });
  const page = await context.newPage();

  try {
    await page.goto(target.url, {
      waitUntil: 'domcontentloaded',
      timeout: 120000
    });
    await acceptCookieBanner(page);
    await page.waitForTimeout(DEFAULT_PAGE_SETTLE_MS);

    const extraction = await page.evaluate(() => {
      const triplets = [];
      const seen = new Set();
      const html = document.documentElement.outerHTML;
      const textNodes = Array.from(document.querySelectorAll('main table tr, main [role="row"], main section, main div'));

      for (const node of textNodes) {
        const text = (node.innerText || node.textContent || '').replace(/\s+/g, ' ').trim();
        if (!text) {
          continue;
        }

        const values = [...text.matchAll(/\b\d+\.\d{2}\b/g)]
          .map((match) => Number(match[0]))
          .filter((value) => Number.isFinite(value));
        if (values.length < 3) {
          continue;
        }

        const signature = `${text}::${values.slice(0, 3).join('|')}`;
        if (seen.has(signature)) {
          continue;
        }
        seen.add(signature);

        triplets.push({
          text,
          home: values[0],
          draw: values[1],
          away: values[2]
        });
      }

      if (triplets.length === 0) {
        const regex = /(\d+\.\d{2})[^0-9]+(\d+\.\d{2})[^0-9]+(\d+\.\d{2})/g;
        for (const match of html.matchAll(regex)) {
          triplets.push({
            text: match[0].slice(0, 200),
            home: Number(match[1]),
            draw: Number(match[2]),
            away: Number(match[3])
          });
          if (triplets.length >= 20) {
            break;
          }
        }
      }

      return {
        title: document.title,
        url: location.href,
        triplets
      };
    });

    const fallbackIso = new Date().toISOString();
    const oddsSnapshots = buildFallbackOddsFromTriplets(extraction.triplets, fallbackIso);
    if (!oddsSnapshots) {
      throw new Error(`DOM fallback 未找到有效赔率三元组: ${extraction.title}`);
    }

    return {
      mode: 'dom',
      mappingMethod: 'manual',
      proxyServer,
      oddsSnapshots
    };
  } finally {
    await page.close().catch(() => {});
    await context.close().catch(() => {});
    await browser.close().catch(() => {});
  }
}

async function upsertMappingAndOdds(row, target, extraction, options = {}) {
  if (options.dryRun) {
    return;
  }

  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    await client.query(UPSERT_MAPPING_SQL, [
      row.match_id,
      target.hash,
      target.url,
      row.season,
      row.league_name,
      row.home_team,
      row.away_team,
      1.0,
      extraction.mappingMethod
    ]);
    await client.query(UPSERT_ODDS_SQL, [
      row.match_id,
      OPENING_BOOKMAKER,
      extraction.oddsSnapshots.opening.home,
      extraction.oddsSnapshots.opening.draw,
      extraction.oddsSnapshots.opening.away,
      extraction.oddsSnapshots.opening.collectedAt
    ]);
    await client.query(UPSERT_ODDS_SQL, [
      row.match_id,
      CURRENT_BOOKMAKER,
      extraction.oddsSnapshots.current.home,
      extraction.oddsSnapshots.current.draw,
      extraction.oddsSnapshots.current.away,
      extraction.oddsSnapshots.current.collectedAt
    ]);
    await client.query('COMMIT');
  } catch (error) {
    await client.query('ROLLBACK').catch(() => {});
    throw error;
  } finally {
    client.release();
  }
}

function groupRowsByKey(rows, keyField) {
  const grouped = new Map();
  for (const row of rows) {
    const key = row?.[keyField];
    if (!key) {
      continue;
    }
    if (!grouped.has(key)) {
      grouped.set(key, []);
    }
    grouped.get(key).push(row);
  }
  return grouped;
}

function normalizeCanonicalOddsRow(row) {
  return {
    home: toPositiveNumber(row.home_odds),
    draw: toPositiveNumber(row.draw_odds),
    away: toPositiveNumber(row.away_odds),
    collectedAt: row.collected_at ? new Date(row.collected_at).toISOString() : null
  };
}

function aggregateOddsTriplet(points, collectedAt = null) {
  const homeValues = points.map((point) => point.home).filter(Boolean);
  const drawValues = points.map((point) => point.draw).filter(Boolean);
  const awayValues = points.map((point) => point.away).filter(Boolean);

  if (homeValues.length === 0 || drawValues.length === 0 || awayValues.length === 0) {
    return null;
  }

  return {
    home: median(homeValues),
    draw: median(drawValues),
    away: median(awayValues),
    collectedAt
  };
}

function buildOddsDataFromCanonicalRows(rows) {
  if (!rows || rows.length === 0) {
    return null;
  }

  const groupedByTimestamp = new Map();
  for (const row of rows) {
    const normalized = normalizeCanonicalOddsRow(row);
    if (!normalized.home || !normalized.draw || !normalized.away) {
      continue;
    }

    const timestampKey = normalized.collectedAt || `snapshot-${row.id}`;
    if (!groupedByTimestamp.has(timestampKey)) {
      groupedByTimestamp.set(timestampKey, []);
    }
    groupedByTimestamp.get(timestampKey).push(normalized);
  }

  const history = Array.from(groupedByTimestamp.entries())
    .map(([timestampKey, points]) => aggregateOddsTriplet(points, timestampKey.startsWith('snapshot-') ? null : timestampKey))
    .filter(Boolean);

  if (history.length === 0) {
    return null;
  }

  return {
    initial: history[0],
    current: history[history.length - 1],
    history,
    hasData: true,
    odds_source: 'odds',
    _odds_source: 'odds',
    _odds_source_rows: rows.length,
    _odds_source_points: history.length
  };
}

function countShotmapShots(rawData) {
  const shots = rawData?.content?.shotmap?.shots;
  return Array.isArray(shots) ? shots.length : 0;
}

function countRatingSamples(goldenFeatures) {
  return Number(goldenFeatures?.home_rating_available_count || 0)
    + Number(goldenFeatures?.away_rating_available_count || 0);
}

function buildConflictSummary(rawData, tacticalFeatures, goldenFeatures, oddsFeatures) {
  const conflicts = [];
  const hasContent = !!rawData?.content && typeof rawData.content === 'object';
  const hasLineup = !!rawData?.content?.lineup && typeof rawData.content.lineup === 'object';
  const hasShotmap = !!rawData?.content?.shotmap && typeof rawData.content.shotmap === 'object';
  const shotmapShots = countShotmapShots(rawData);
  const ratingSamples = countRatingSamples(goldenFeatures);
  const hasXgSignal = Number.isFinite(Number(tacticalFeatures?.home_xg))
    && Number.isFinite(Number(tacticalFeatures?.away_xg));

  if (!hasContent) {
    conflicts.push('missing_content');
  }
  if (!hasLineup) {
    conflicts.push('missing_lineup');
  }
  if (!hasShotmap) {
    conflicts.push('missing_shotmap');
  }
  if (!hasXgSignal) {
    conflicts.push('invalid_xg');
  }

  return {
    has_content: hasContent,
    has_lineup: hasLineup,
    has_shotmap: hasShotmap,
    shotmap_shots: shotmapShots,
    rating_samples: ratingSamples,
    has_odds_data: !!oddsFeatures?.has_odds_data,
    odds_source: oddsFeatures?._odds_source || 'none',
    conflicts
  };
}

async function runTargetedStitch(matchIds) {
  const client = await pool.connect();
  try {
    const rows = (await client.query(FETCH_MATCH_ROWS_SQL, [matchIds])).rows;
    const oddsRows = (await client.query(FETCH_CANONICAL_ODDS_SQL, [matchIds])).rows;
    const canonicalByMatchId = groupRowsByKey(oddsRows, 'match_id');

    for (const row of rows) {
      const goldenFeatures = extractGoldenFeatures(row.raw_data);
      const tacticalFeatures = extractTacticalFeatures(row.raw_data);
      const canonicalData = buildOddsDataFromCanonicalRows(canonicalByMatchId.get(row.match_id) || []);
      if (!canonicalData) {
        throw new Error(`单点 L3 stitch 未找到 canonical odds: ${row.match_id}`);
      }

      const oddsFeatures = {
        ...extractOddsMovementFeaturesFromOddsData(canonicalData, tacticalFeatures),
        odds_source: canonicalData.odds_source,
        _odds_source: canonicalData._odds_source,
        _odds_source_rows: canonicalData._odds_source_rows,
        _odds_source_points: canonicalData._odds_source_points
      };
      const summary = buildConflictSummary(row.raw_data, tacticalFeatures, goldenFeatures, oddsFeatures);

      await client.query(UPSERT_L3_SQL, [
        row.match_id,
        row.external_id || row.match_id,
        JSON.stringify(goldenFeatures),
        JSON.stringify(tacticalFeatures),
        JSON.stringify(oddsFeatures),
        JSON.stringify(oddsFeatures),
        JSON.stringify(summary)
      ]);
    }
  } finally {
    client.release();
  }
}

async function fetchMatchRows(matchIds) {
  const client = await pool.connect();
  try {
    return (await client.query(FETCH_MATCH_ROWS_SQL, [matchIds])).rows;
  } finally {
    client.release();
  }
}

async function fetchFinalOdds(matchIds) {
  const client = await pool.connect();
  try {
    return (await client.query(FINAL_ODDS_SQL, [matchIds])).rows;
  } finally {
    client.release();
  }
}

async function fetchFinalNoneCount() {
  const client = await pool.connect();
  try {
    return (await client.query(FINAL_NONE_SQL)).rows[0]?.odds_source_none ?? null;
  } finally {
    client.release();
  }
}

function printHarvestResult(row, extraction) {
  console.log(
    `[SNIPER] ${row.match_id} ${row.home_team} vs ${row.away_team} `
    + `mode=${extraction.mode} open=${extraction.oddsSnapshots.opening.home}/${extraction.oddsSnapshots.opening.draw}/${extraction.oddsSnapshots.opening.away} `
    + `current=${extraction.oddsSnapshots.current.home}/${extraction.oddsSnapshots.current.draw}/${extraction.oddsSnapshots.current.away}`
  );
}

async function run() {
  const options = parseArgs(process.argv.slice(2));
  const targets = resolveTargets(options);
  const matchIds = targets.map((target) => target.match_id);
  const rows = await fetchMatchRows(matchIds);
  const rowsByMatchId = new Map(rows.map((row) => [row.match_id, row]));

  if (rows.length !== targets.length) {
    const missing = matchIds.filter((matchId) => !rowsByMatchId.has(matchId));
    throw new Error(`数据库缺少目标比赛: ${missing.join(', ')}`);
  }

  if (!options.skipHarvest) {
    for (const target of targets) {
      const row = rowsByMatchId.get(target.match_id);
      let extraction = null;
      let protocolMeta = {};

      try {
        extraction = await extractViaProtocol(target);
      } catch (error) {
        console.warn(`[SNIPER] 协议提取失败 ${target.match_id}: ${error.message}`);
        protocolMeta = { geoIPcode: '' };
        try {
          const context = await createProtocolContext(target);
          protocolMeta.geoIPcode = normalizeText(context.pageVar?.geoIPcode);
        } catch {
          // ignore fallback probe failure
        }
        extraction = await extractViaDom(target, options, protocolMeta);
      }

      printHarvestResult(row, extraction);
      await upsertMappingAndOdds(row, target, extraction, options);
    }
  }

  if (!options.skipStitch) {
    await runTargetedStitch(matchIds);
    console.log(`[SNIPER] 单点 L3 stitch 完成: ${matchIds.join(', ')}`);
  }

  const finalOddsRows = await fetchFinalOdds(matchIds);
  const oddsSourceNone = await fetchFinalNoneCount();

  console.log('[SNIPER] 最终赔率落库快照:');
  for (const row of finalOddsRows) {
    console.log(
      `  ${row.match_id} | ${row.bookmaker} | `
      + `${row.home_odds}/${row.draw_odds}/${row.away_odds} | ${row.collected_at.toISOString()}`
    );
  }
  console.log(`[SNIPER] odds_source_none=${oddsSourceNone}`);

  if (Number(oddsSourceNone) !== 0) {
    throw new Error(`收尾失败: odds_source_none=${oddsSourceNone}`);
  }
}

run()
  .then(async () => {
    await pool.end().catch(() => {});
  })
  .catch(async (error) => {
    console.error(`[FATAL] ${error.stack || error.message}`);
    await pool.end().catch(() => {});
    process.exit(1);
  });
