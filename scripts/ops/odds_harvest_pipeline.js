#!/usr/bin/env node
'use strict';

require('dotenv').config();

const { spawn } = require('node:child_process');
const { chromium } = require('playwright');
const { Pool } = require('pg');

const { ReconPureDecryptor } = require('../../src/infrastructure/recon/services/ReconPureDecryptor');
const { EntityMapper } = require('../../src/infrastructure/etl/EntityMapper');
const {
  COVERAGE_SQL,
  CURRENT_BOOKMAKER,
  DEFAULT_CONCURRENCY,
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
  UPSERT_MAPPING_SQL,
  UPSERT_ODDS_SQL,
  extractMedianOddsSnapshots,
  normalizeTitleKey,
  parseArgs,
  sleep
} = require('./odds_harvest_pipeline.shared');

const pool = new Pool({
  host: process.env.DB_HOST || '127.0.0.1',
  port: Number.parseInt(process.env.DB_PORT || '5432', 10),
  database: process.env.DB_NAME || 'football_db',
  user: process.env.DB_USER || 'football_user',
  password: process.env.DB_PASSWORD || '',
  max: Math.max(8, Math.min(DEFAULT_CONCURRENCY + 4, 32))
});

function normalizeLeagueSelection(rawValue) {
  return String(rawValue || '').trim().toLowerCase();
}

function resolveRequestedRoutes(requestedLeagues = []) {
  const routeEntries = Object.values(LEAGUE_ROUTE_CATALOG);
  const requested = new Set(requestedLeagues.map(normalizeLeagueSelection));
  const matches = routeEntries.filter((entry) => (
    requested.has(entry.leagueName.toLowerCase())
    || requested.has(normalizeTitleKey(entry.leagueName))
  ));

  if (requestedLeagues.length === 0) {
    return routeEntries;
  }

  if (matches.length !== requestedLeagues.length) {
    const known = routeEntries.map((entry) => entry.leagueName).join(', ');
    throw new Error(`未知联赛参数: ${requestedLeagues.join(', ')} | 可用联赛: ${known}`);
  }

  return matches;
}

function buildResultsUrl(route, season) {
  return `${RESULTS_BASE_URL}/football/${route.country}/${route.slug}-${season.replace('/', '-')}/results/`;
}

async function acceptCookieBanner(page) {
  const candidates = [
    '#onetrust-accept-btn-handler',
    'button:has-text("Accept")',
    'button:has-text("I Accept")'
  ];

  for (const selector of candidates) {
    try {
      const locator = page.locator(selector).first();
      if (await locator.isVisible({ timeout: 5000 }).catch(() => false)) {
        await locator.click({ timeout: 5000, force: true }).catch(() => {});
        await page.waitForTimeout(1000);
        return;
      }
    } catch {
      // ignore optional banner selectors
    }
  }
}

async function goToPaginationPage(page, pageNumber) {
  let lastError = null;

  for (let attempt = 1; attempt <= 3; attempt += 1) {
    try {
      await acceptCookieBanner(page);
      await page.locator(`a.pagination-link[data-number="${pageNumber}"]`).click({
        timeout: 15000,
        force: true
      });
      await acceptCookieBanner(page);
      await page.waitForFunction(
        (targetPage) => {
          const active = document.querySelector('a.pagination-link.active')?.getAttribute('data-number');
          const rows = document.querySelectorAll('div.group[data-testid="game-row"]').length;
          return active === String(targetPage) && rows > 0;
        },
        pageNumber,
        { timeout: 30000 }
      );
      await page.waitForTimeout(400);
      return;
    } catch (error) {
      lastError = error;
      await page.waitForTimeout(1500 * attempt);
    }
  }

  throw lastError;
}

async function waitForRowsReady(page, label) {
  let lastError = null;

  for (let attempt = 1; attempt <= 3; attempt += 1) {
    try {
      await acceptCookieBanner(page);
      await page.waitForFunction(
        () => document.querySelectorAll('div.group[data-testid="game-row"]').length > 0,
        undefined,
        { timeout: 30000 }
      );
      return;
    } catch (error) {
      lastError = error;
      console.warn(`[ENUM] ${label} rows-ready retry ${attempt}/3`);
      await page.reload({
        waitUntil: 'networkidle',
        timeout: 120000
      }).catch(() => {});
      await page.waitForTimeout(1500 * attempt);
    }
  }

  throw lastError;
}

async function enumerateLeagueEvents(route, season) {
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage']
  });

  const eventsByHash = new Map();
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1200 },
    userAgent: DEFAULT_USER_AGENT
  });

  try {
    await page.goto(buildResultsUrl(route, season), {
      waitUntil: 'networkidle',
      timeout: 120000
    });
    await waitForRowsReady(page, `${route.leagueName}:initial`);

    const totalPages = await page.evaluate(() => {
      const numbers = Array.from(document.querySelectorAll('a.pagination-link[data-number]'))
        .map((element) => Number(element.getAttribute('data-number') || '1'))
        .filter((value) => Number.isFinite(value) && value > 0);
      return numbers.length > 0 ? Math.max(...numbers) : 1;
    });

    for (let pageNumber = 1; pageNumber <= totalPages; pageNumber += 1) {
      if (pageNumber > 1) {
        await goToPaginationPage(page, pageNumber);
      }

      const pageRows = await page.evaluate((baseUrl) => {
        const nodes = Array.from(document.querySelectorAll('[data-testid="date-header"], div.group[data-testid="game-row"]'));
        let currentDate = null;
        const rows = [];

        for (const node of nodes) {
          if (node.getAttribute('data-testid') === 'date-header') {
            currentDate = node.textContent?.replace(/\s+/g, ' ').trim() || null;
            continue;
          }

          const anchor = node.querySelector('a[href*="/football/h2h/"]');
          const href = anchor?.getAttribute('href');
          if (!href) {
            continue;
          }

          const participants = Array.from(node.querySelectorAll('.participant-name'))
            .map((element) => element.textContent?.trim())
            .filter(Boolean);
          const fullUrl = new URL(href, baseUrl).toString();

          rows.push({
            fullUrl,
            hash: /#([A-Za-z0-9]{8})$/.exec(fullUrl)?.[1] || null,
            homeTeam: participants[0] || null,
            awayTeam: participants[1] || null,
            dateLabel: currentDate
          });
        }

        return rows;
      }, RESULTS_BASE_URL);

      for (const row of pageRows) {
        if (!row.hash) {
          continue;
        }
        eventsByHash.set(row.hash, {
          ...row,
          leagueName: route.leagueName
        });
      }

      console.log(
        `[ENUM] ${route.leagueName} page=${pageNumber}/${totalPages} rows=${pageRows.length} unique=${eventsByHash.size}`
      );
    }
  } finally {
    await page.close().catch(() => {});
    await browser.close().catch(() => {});
  }

  return Array.from(eventsByHash.values());
}

async function fetchText(url, options = {}) {
  const retries = options.retries || DEFAULT_RETRIES;
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
        signal: AbortSignal.timeout(Number.parseInt(process.env.ODDS_HARVEST_FETCH_TIMEOUT_MS || '30000', 10))
      });

      if (!response.ok) {
        throw new Error(`HTTP_${response.status}`);
      }

      return await response.text();
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

async function createDecryptor(sampleEventUrl) {
  const sampleHtml = await fetchText(sampleEventUrl, {
    headers: {
      referer: sampleEventUrl
    }
  });
  const bundlePath = [...sampleHtml.matchAll(/(?:src|href)=["']([^"']*\/build\/assets\/app-[^"']+\.js[^"']*)["']/g)][0]?.[1]
    || [...sampleHtml.matchAll(/https:\/\/www\.oddsportal\.com\/build\/assets\/app-[^"']+\.js/g)][0]?.[0];
  const bundleUrl = bundlePath
    ? new URL(bundlePath, RESULTS_BASE_URL).toString()
    : null;

  if (!bundleUrl) {
    throw new Error(`未从 H2H 页面提取到 bundle: ${sampleEventUrl}`);
  }

  const decryptor = new ReconPureDecryptor({
    logger: {
      info: (...args) => console.log('[DECRYPT]', ...args),
      warn: (...args) => console.warn('[DECRYPT]', ...args),
      error: (...args) => console.error('[DECRYPT]', ...args)
    },
    traceId: `odds_harvest_${Date.now()}`
  });

  await decryptor.loadFromBundleUrl(bundleUrl, { html: '' });
  return {
    bundleUrl,
    decryptor
  };
}

function buildTargetIndexes(targetRows) {
  const mapper = new EntityMapper({
    teamAliases: ODDSPORTAL_TEAM_ALIASES
  });
  const exactByLeague = new Map();

  for (const row of targetRows) {
    const leagueName = String(row.league_name);
    const key = mapper.buildMatchLookupKey(row.home_team, row.away_team);
    const normalized = {
      ...row,
      leagueName,
      normalizedKey: key,
      matchTimestampMs: new Date(row.match_date).getTime()
    };

    if (!exactByLeague.has(leagueName)) {
      exactByLeague.set(leagueName, new Map());
    }
    const leagueBucket = exactByLeague.get(leagueName);
    if (!leagueBucket.has(key)) {
      leagueBucket.set(key, []);
    }
    leagueBucket.get(key).push(normalized);
  }

  return {
    mapper,
    exactByLeague
  };
}

function resolveTargetMatch(indexes, candidate) {
  const leagueBucket = indexes.exactByLeague.get(candidate.leagueName);
  if (!leagueBucket) {
    return null;
  }

  const homeKey = indexes.mapper.buildMatchLookupKey(candidate.homeTeam, candidate.awayTeam);
  const reverseKey = indexes.mapper.buildMatchLookupKey(candidate.awayTeam, candidate.homeTeam);
  const candidateSets = [
    {
      key: homeKey,
      isReversed: false,
      rows: leagueBucket.get(homeKey) || []
    },
    {
      key: reverseKey,
      isReversed: true,
      rows: leagueBucket.get(reverseKey) || []
    }
  ];

  let best = null;

  for (const set of candidateSets) {
    for (const row of set.rows) {
      const deltaMs = Math.abs(row.matchTimestampMs - candidate.kickoffMs);
      if (!best || deltaMs < best.deltaMs) {
        best = {
          row,
          deltaMs,
          isReversed: set.isReversed
        };
      }
    }
  }

  if (!best || best.deltaMs > MATCH_DELTA_MS) {
    return null;
  }

  const confidence = best.deltaMs <= 6 * 60 * 60 * 1000
    ? 1.0
    : (best.deltaMs <= 24 * 60 * 60 * 1000 ? 0.96 : 0.9);

  return {
    ...best.row,
    deltaMs: best.deltaMs,
    isReversed: best.isReversed,
    matchConfidence: confidence
  };
}

function parseOddsPortalDateLabel(dateLabel) {
  const match = String(dateLabel || '').trim().match(/^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$/);
  if (!match) {
    return null;
  }

  const day = Number(match[1]);
  const month = MONTHS[match[2].toLowerCase()];
  const year = Number(match[3]);

  if (!Number.isInteger(day) || month === undefined || !Number.isInteger(year)) {
    return null;
  }

  return Date.UTC(year, month, day, 12, 0, 0);
}

function resolveDomCandidateMatch(indexes, candidate) {
  const dateMs = parseOddsPortalDateLabel(candidate.dateLabel);
  if (!dateMs) {
    return null;
  }

  return resolveTargetMatch(indexes, {
    leagueName: candidate.leagueName,
    homeTeam: candidate.homeTeam,
    awayTeam: candidate.awayTeam,
    kickoffMs: dateMs
  });
}

async function fetchAjaxEventData(decryptor, event) {
  const ajaxUrl = `${RESULTS_BASE_URL}/ajax-event-data/${event.hash}/0`;
  const ajaxPayload = await fetchText(ajaxUrl, {
    headers: {
      referer: event.fullUrl
    }
  });
  return decryptor.decrypt(ajaxPayload);
}

async function fetchPreMatchData(decryptor, event, requestPreMatchUrl) {
  const url = `${RESULTS_BASE_URL}${requestPreMatchUrl}`;
  const payload = await fetchText(url, {
    headers: {
      referer: event.fullUrl
    }
  });
  return decryptor.decrypt(payload);
}

async function upsertMappingAndOdds(match, event, oddsSnapshots, season, options = {}) {
  if (options.dryRun) {
    return;
  }

  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    await client.query(UPSERT_MAPPING_SQL, [
      match.match_id,
      event.hash,
      event.fullUrl,
      season,
      match.leagueName,
      match.home_team,
      match.away_team,
      match.matchConfidence,
      match.isReversed
    ]);
    await client.query(UPSERT_ODDS_SQL, [
      match.match_id,
      OPENING_BOOKMAKER,
      oddsSnapshots.opening.home,
      oddsSnapshots.opening.draw,
      oddsSnapshots.opening.away,
      oddsSnapshots.opening.collectedAt
    ]);
    await client.query(UPSERT_ODDS_SQL, [
      match.match_id,
      CURRENT_BOOKMAKER,
      oddsSnapshots.current.home,
      oddsSnapshots.current.draw,
      oddsSnapshots.current.away,
      oddsSnapshots.current.collectedAt
    ]);
    await client.query('COMMIT');
  } catch (error) {
    await client.query('ROLLBACK').catch(() => {});
    throw error;
  } finally {
    client.release();
  }
}

function buildProgressSnapshot(stats) {
  const elapsedMinutes = Math.max(1 / 60, (Date.now() - stats.startedAt) / 60000);
  return {
    processed: stats.processed,
    success: stats.success,
    noMatch: stats.noMatch,
    noOdds: stats.noOdds,
    failed: stats.failed,
    throughputPerMinute: Number((stats.success / elapsedMinutes).toFixed(2))
  };
}

function printProgress(stats, total) {
  const snapshot = buildProgressSnapshot(stats);
  console.log(
    `[HARVEST] ${snapshot.processed}/${total} | success=${snapshot.success} `
    + `no_match=${snapshot.noMatch} no_odds=${snapshot.noOdds} failed=${snapshot.failed} `
    + `throughput=${snapshot.throughputPerMinute} matches/min`
  );
}

async function runL3Stitch(options = {}) {
  if (!options.l3Enabled || options.mappingOnly) {
    return;
  }

  await new Promise((resolve, reject) => {
    const child = spawn(process.execPath, ['scripts/ops/l3_stitch_pipeline.js'], {
      cwd: process.cwd(),
      env: {
        ...process.env,
        L3_STITCH_SEASON: options.season || TARGET_SEASON,
        L3_STITCH_FULL_RECALCULATE: 'true',
        L3_STITCH_WORKERS: String(options.l3Workers || 12)
      },
      stdio: 'inherit'
    });

    child.on('exit', (code) => {
      if (code === 0) {
        resolve();
        return;
      }
      reject(new Error(`l3_stitch_pipeline.js exited with code ${code}`));
    });
  });
}

async function fetchCoverageStats(client, season) {
  const result = await client.query(COVERAGE_SQL, [season, OPENING_BOOKMAKER, CURRENT_BOOKMAKER]);
  return result.rows[0];
}

async function fetchTargetMatches(client, routeSet, season) {
  const result = await client.query(TARGETS_SQL, [season, OPENING_BOOKMAKER, CURRENT_BOOKMAKER]);
  const routeNames = new Set(routeSet.map((route) => route.leagueName));
  return result.rows.filter((row) => routeNames.has(String(row.league_name)));
}

async function run() {
  const options = parseArgs(process.argv.slice(2));
  const routes = resolveRequestedRoutes(options.leagues);
  const season = options.season;
  const rootClient = await pool.connect();

  try {
    const initialCoverage = await fetchCoverageStats(rootClient, season);
    const targetRows = await fetchTargetMatches(rootClient, routes, season);
    const indexes = buildTargetIndexes(targetRows);

    console.log('[BOOT] 24/25 赔率专项收割启动');
    console.log(`[BOOT] season=${season} leagues=${routes.map((route) => route.leagueName).join(', ')}`);
    console.log(`[BOOT] initial_l3_gap=${initialCoverage.l3_gap} initial_odds_gap=${initialCoverage.odds_gap}`);
    console.log(`[BOOT] target_rows=${targetRows.length} workers=${options.concurrency}`);

    if (targetRows.length === 0) {
      console.log('[BOOT] 当前没有待补赔率目标，退出。');
      return;
    }

    const enumeratedEvents = [];
    for (const route of routes) {
      const leagueEvents = await enumerateLeagueEvents(route, season);
      console.log(`[ENUM] ${route.leagueName} unique_events=${leagueEvents.length} expected=${route.expectedMatches}`);
      enumeratedEvents.push(...leagueEvents);
    }

    if (enumeratedEvents.length === 0) {
      throw new Error('结果页未抽取到任何 event，无法继续');
    }

    const candidateEvents = options.skipDomFilter
      ? enumeratedEvents
      : enumeratedEvents.filter((event) => resolveDomCandidateMatch(indexes, event));
    const selectedEvents = options.limit
      ? candidateEvents.slice(0, options.limit)
      : candidateEvents;

    console.log(
      `[ENUM] candidate_events=${candidateEvents.length} selected_events=${selectedEvents.length} `
      + `raw_events=${enumeratedEvents.length}`
    );

    const { bundleUrl, decryptor } = await createDecryptor(selectedEvents[0].fullUrl);
    console.log(`[DECRYPT] bundle=${bundleUrl}`);

    const stats = {
      startedAt: Date.now(),
      processed: 0,
      success: 0,
      noMatch: 0,
      noOdds: 0,
      failed: 0,
      l3Runs: 0
    };
    const pendingL3Marks = new Set();

    const processEvent = async (event) => {
      try {
        const ajax = await fetchAjaxEventData(decryptor, event);
        const eventData = ajax?.d?.eventData;
        const eventBody = ajax?.d?.eventBody;
        const requestPreMatch = ajax?.d?.requestPreMatch?.url;
        const kickoffMs = Number(eventBody?.startDate || 0) * 1000;

        if (!eventData?.home || !eventData?.away || !requestPreMatch || !kickoffMs) {
          throw new Error(`event payload 缺少关键字段 hash=${event.hash}`);
        }

        const matchedRow = resolveTargetMatch(indexes, {
          leagueName: event.leagueName,
          homeTeam: eventData.home,
          awayTeam: eventData.away,
          kickoffMs
        });

        if (!matchedRow) {
          stats.noMatch += 1;
          return;
        }

        const preMatch = await fetchPreMatchData(decryptor, event, requestPreMatch);
        const oddsSnapshots = extractMedianOddsSnapshots(preMatch, kickoffMs);

        if (!oddsSnapshots) {
          stats.noOdds += 1;
          return;
        }

        await upsertMappingAndOdds(matchedRow, event, oddsSnapshots, season, options);
        pendingL3Marks.add(matchedRow.match_id);
        stats.success += 1;
      } catch (error) {
        stats.failed += 1;
        console.error(`[HARVEST] failed hash=${event.hash} league=${event.leagueName}: ${error.message}`);
      } finally {
        stats.processed += 1;
        if (stats.processed % options.progressEvery === 0 || stats.processed === selectedEvents.length) {
          printProgress(stats, selectedEvents.length);
        }
      }
    };

    for (let index = 0; index < selectedEvents.length; index += options.concurrency) {
      const chunk = selectedEvents.slice(index, index + options.concurrency);
      await Promise.all(chunk.map((event) => processEvent(event)));

      if (
        options.l3Enabled
        && !options.mappingOnly
        && options.l3Every > 0
        && pendingL3Marks.size >= options.l3Every
      ) {
        console.log(`[L3] 触发增量批次 full-recalc，pending=${pendingL3Marks.size}`);
        await runL3Stitch(options);
        stats.l3Runs += 1;
        pendingL3Marks.clear();
      }
    }

    if (
      options.l3Enabled
      && !options.mappingOnly
      && pendingL3Marks.size > 0
    ) {
      console.log(`[L3] 执行收尾 full-recalc，pending=${pendingL3Marks.size}`);
      await runL3Stitch(options);
      stats.l3Runs += 1;
      pendingL3Marks.clear();
    }

    const finalCoverage = await fetchCoverageStats(rootClient, season);
    const finalSnapshot = buildProgressSnapshot(stats);

    console.log('[FINAL] 任务完成');
    console.log(
      `[FINAL] processed=${stats.processed} success=${stats.success} `
      + `no_match=${stats.noMatch} no_odds=${stats.noOdds} failed=${stats.failed}`
    );
    console.log(
      `[FINAL] throughput=${finalSnapshot.throughputPerMinute} matches/min `
      + `l3_runs=${stats.l3Runs} odds_gap=${finalCoverage.odds_gap} l3_gap=${finalCoverage.l3_gap}`
    );
  } finally {
    rootClient.release();
    await pool.end();
  }
}

run().catch((error) => {
  console.error(`[FATAL] ${error.stack || error.message}`);
  pool.end().catch(() => {});
  process.exit(1);
});
