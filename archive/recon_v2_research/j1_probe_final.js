'use strict';

const { chromium } = require('playwright');
const { ReconDecryptor } = require('../../src/infrastructure/recon/ReconDecryptor');
const { ReconBrowserContext } = require('../../src/infrastructure/recon/services/ReconBrowserContext');
const { ReconDomScraper } = require('../../src/infrastructure/recon/services/ReconDomScraper');

const TARGET_URL = 'https://www.oddsportal.com/football/japan/j1-league-2026/results/';
const HOME_URL = 'https://www.oddsportal.com/';
const FULL_CHROMIUM_PATH = '/root/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome';
const EXTERNAL_SESSION_PATH = process.env.EXTERNAL_SESSION_PATH || '/home/xupeng/projects/FootballPrediction/11';
const ARCHIVE_PATTERN = /ajax-sport-country-tournament-archive_/i;
const CONSENT_LABELS = ['I Accept', 'Accept All', 'Accept', 'Allow All'];

function resolveCookieProfile() {
  const profile = String(process.env.COOKIE_PROFILE || '').trim().toUpperCase();
  if (profile === 'A') {
    return {
      name: 'preference_group',
      includeNames: [
        'op_user_cookie',
        'op_user_hash',
        'op_user_time',
        'op_user_time_zone',
        'op_user_full_time_zone'
      ],
      excludeNames: []
    };
  }

  if (profile === 'B') {
    return {
      name: 'state_group',
      includeNames: ['op_user_hash', 'op_user_time_zone', 'OptanonConsent'],
      excludeNames: []
    };
  }

  if (profile === 'C') {
    return {
      name: 'blacklist_exclusion',
      includeNames: [],
      excludeNames: ['oddsportalcom_session']
    };
  }

  return {
    name: 'default',
    includeNames: [],
    excludeNames: ['oddsportalcom_session']
  };
}

function trimText(value, max = 240) {
  const text = String(value || '').replace(/\s+/g, ' ').trim();
  return text.length > max ? `${text.slice(0, max)}...` : text;
}

function extractBodySummary(body) {
  const text = String(body || '').trim();
  const summary = {
    bodyPreview: trimText(text, 320),
    rows: null,
    nullResultText: null,
    bodyType: 'unknown'
  };

  if (!text) {
    summary.bodyType = 'empty';
    return summary;
  }

  try {
    const parsed = JSON.parse(text);
    summary.bodyType = 'json';
    summary.rows = Array.isArray(parsed?.d?.rows)
      ? parsed.d.rows.length
      : Array.isArray(parsed?.rows)
        ? parsed.rows.length
        : null;
    summary.nullResultText = parsed?.d?.nullResultText || parsed?.nullResultText || null;
    return summary;
  } catch (_error) {
    // non-json body
  }

  const nullResultMatch = text.match(/nullResultText["']?\s*[:=]\s*["']([^"']+)["']/i);
  if (nullResultMatch) {
    summary.nullResultText = nullResultMatch[1];
  }

  const rowsMatch = text.match(/"rows"\s*:\s*\[/i);
  if (rowsMatch) {
    summary.bodyType = 'json_like';
  } else if (/<!doctype html|<html/i.test(text)) {
    summary.bodyType = 'html';
  } else {
    summary.bodyType = 'opaque';
  }

  return summary;
}

async function dismissConsent(page) {
  for (const label of CONSENT_LABELS) {
    try {
      const button = page.getByRole('button', { name: label }).first();
      if (await button.isVisible({ timeout: 2500 })) {
        await button.click({ timeout: 2500 });
        await page.waitForTimeout(1500);
        return { clicked: true, label };
      }
    } catch (_error) {
      // try next label
    }
  }

  return { clicked: false, label: null };
}

async function extractTournamentToken(page) {
  return page.evaluate(() => {
    const scripts = Array.from(document.scripts).map((script) => script.textContent || '');
    const hit = scripts.find((text) => text.includes('pageOutrightsVar')) || '';
    const match = hit.match(/pageOutrightsVar\s*=\s*'([^']+)'/);
    if (match) {
      try {
        const parsed = JSON.parse(match[1]);
        if (typeof parsed?.id === 'string' && parsed.id.trim()) {
          return parsed.id.trim();
        }
      } catch (_error) {
        // fallback to pageVar.otCode
      }
    }

    const fallback = window.pageVar?.otCode;
    return typeof fallback === 'string' ? fallback.trim() : '';
  });
}

async function fetchRepairedArchive(page, tournamentToken) {
  if (!tournamentToken) {
    return {
      repairedArchive: null,
      repairedPreview: null,
      repairedRows: null,
      repairedNullResultText: null
    };
  }

  const repairedArchive = `https://www.oddsportal.com/ajax-sport-country-tournament-archive_/1/${tournamentToken}/X262144X16384X0X0X134217728X0X0X0X0X0X0X0X0X134217729X0X0X1048576X0X1024X40X0X32X0X0X0X0X0X0X0X536870912X2560X2048X0X33554560X8519680X0X0X0X524288/1/0/`;
  const responseText = await page.evaluate(async (url) => {
    const response = await fetch(`${url}?_=${Date.now()}`, {
      credentials: 'include',
      headers: {
        'x-requested-with': 'XMLHttpRequest'
      }
    });
    return await response.text();
  }, repairedArchive);
  const summary = extractBodySummary(responseText);
  let decryptedRows = null;
  let decryptedNullResultText = null;
  let decryptedPreview = null;

  if (summary.bodyType === 'opaque') {
    try {
      const decryptor = new ReconDecryptor({
        logger: console,
        allowBestEffortCandidate: true
      });
      await decryptor.extractDecryptor(page, responseText);
      const decrypted = await decryptor.decrypt(responseText);
      const parsed = typeof decrypted === 'string' ? JSON.parse(decrypted) : decrypted;
      decryptedRows = Array.isArray(parsed?.d?.rows)
        ? parsed.d.rows.length
        : Array.isArray(parsed?.rows)
          ? parsed.rows.length
          : null;
      decryptedNullResultText = parsed?.d?.nullResultText || parsed?.nullResultText || null;
      decryptedPreview = trimText(JSON.stringify(parsed).slice(0, 500), 500);
    } catch (error) {
      decryptedPreview = `decrypt_failed:${error.message}`;
    }
  }

  return {
    repairedArchive,
    repairedPreview: summary.bodyPreview,
    repairedRows: summary.rows,
    repairedNullResultText: summary.nullResultText,
    repairedBodyType: summary.bodyType,
    decryptedRows,
    decryptedNullResultText,
    decryptedPreview
  };
}

async function fetchCurrentTournament(page, tournamentToken) {
  if (!tournamentToken) {
    return {
      tournamentApi: null,
      tournamentRows: null,
      tournamentNullResultText: null,
      tournamentPreview: null
    };
  }

  const tournamentApi = `https://www.oddsportal.com/ajax-sport-country-tournament_/1/${tournamentToken}/X262144X16384X0X0X134217728X0X0X0X0X0X0X0X0X134217729X0X0X1048576X0X1024X40X0X32X0X0X0X0X0X0X0X536870912X2560X2048X0X33554560X8519680X0X0X0X524288/1/`;
  const responseText = await page.evaluate(async (url) => {
    const response = await fetch(`${url}?_=${Date.now()}`, {
      credentials: 'include',
      headers: {
        'x-requested-with': 'XMLHttpRequest'
      }
    });
    return await response.text();
  }, tournamentApi);

  const summary = extractBodySummary(responseText);

  return {
    tournamentApi,
    tournamentRows: summary.rows,
    tournamentNullResultText: summary.nullResultText,
    tournamentPreview: summary.bodyPreview,
    tournamentBodyType: summary.bodyType
  };
}

async function extractDomMatches(page, limit = 5) {
  const scraper = new ReconDomScraper({
    logger: console,
    baseUrl: TARGET_URL
  });
  scraper.setPage(page);

  const scraperRows = await scraper.extractCurrentSeasonResultRows(TARGET_URL);
  if (Array.isArray(scraperRows) && scraperRows.length > 0) {
    return scraperRows.slice(0, limit);
  }

  return page.evaluate((maxRows) => {
    const anchors = Array.from(document.querySelectorAll('a[href*="/football/japan/j1-league-2026/"]'));
    const seen = new Set();
    const rows = [];

    for (const anchor of anchors) {
      const href = anchor.href || '';
      if (!/\/[A-Za-z0-9]{8}\/?$/.test(href) || seen.has(href)) {
        continue;
      }

      const text = (anchor.textContent || '').replace(/\s+/g, ' ').trim();
      if (!text) {
        continue;
      }

      seen.add(href);
      rows.push({
        url: href,
        text
      });
      if (rows.length >= maxRows) {
        break;
      }
    }

    return rows;
  }, limit);
}

async function runExperiment(name, options = {}) {
  const useFullChromium = process.env.USE_FULL_CHROMIUM === '1';
  const enableStealth = process.env.ENABLE_STEALTH === '1';
  const cookieProfile = resolveCookieProfile();
  const unlockContext = new ReconBrowserContext({
    logger: console,
    traceId: `probe-${name}`,
    externalSessionPath: EXTERNAL_SESSION_PATH,
    forceUnlockJ1: {
      enabled: true,
      url_patterns: ['/football/japan/j1-league'],
      menu_labels: ['BOOKMAKERS', 'Bookmakers'],
      select_all_labels: ['Select All'],
      fallback_bookmakers: ['Bet365', 'Pinnacle', '1xBet', 'William Hill'],
      open_wait_ms: 1200,
      post_select_wait_ms: 1800,
      state_wait_ms: 5000,
      retrigger_timeout_ms: 10000
    }
  });
  const externalSession = unlockContext.sessionManager.load({
    includeNames: cookieProfile.includeNames,
    excludeNames: cookieProfile.excludeNames
  });
  const externalUserAgent = externalSession.userAgent || null;
  const externalHeaders = externalSession.extraHTTPHeaders || {};
  const browser = await chromium.launch({
    headless: options.headless !== false,
    executablePath: useFullChromium ? FULL_CHROMIUM_PATH : undefined
  });

  const context = await browser.newContext({
    userAgent: externalUserAgent || undefined,
    locale: 'en-US',
    timezoneId: 'Asia/Tokyo',
    extraHTTPHeaders: {
      ...externalHeaders,
      'accept-language': externalHeaders['accept-language'] || 'en-US,en;q=0.9,ja-JP;q=0.8,ja;q=0.7',
      ...(externalUserAgent ? { 'user-agent': externalUserAgent } : {})
    }
  });
  unlockContext.context = context;
  const injectedSession = await unlockContext.injectExternalSession(context, externalSession);
  const page = await context.newPage();
  const hits = [];
  const documentResponses = [];
  unlockContext.page = page;

  if (enableStealth) {
    await page.addInitScript(() => {
      Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
      Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
      Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
      Object.defineProperty(navigator, 'platform', { get: () => 'MacIntel' });
      Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en', 'ja-JP', 'ja'] });
      Object.defineProperty(navigator, 'language', { get: () => 'en-US' });
      Object.defineProperty(navigator, 'plugins', {
        get: () => [
          { name: 'Chrome PDF Plugin' },
          { name: 'Chrome PDF Viewer' },
          { name: 'Native Client' }
        ]
      });
      window.chrome = window.chrome || { runtime: {} };
    });
  }

  page.on('response', async (response) => {
    const url = response.url();
    if (response.request().resourceType() === 'document') {
      documentResponses.push({
        url,
        status: response.status()
      });
    }
    if (!ARCHIVE_PATTERN.test(url)) {
      return;
    }

    const request = response.request();
    let body = '';
    try {
      body = await response.text();
    } catch (_error) {
      body = '';
    }

    const headers = await request.allHeaders();
    hits.push({
      url,
      method: request.method(),
      status: response.status(),
      headers: {
        'x-requested-with': headers['x-requested-with'] || null,
        referer: headers.referer || null,
        cookie: headers.cookie || null,
        'user-agent': headers['user-agent'] || null
      },
      ...extractBodySummary(body)
    });
  });

  const startedAt = Date.now();

  try {
    console.error(`[probe] ${name} start`);
    if (options.gotoHomeFirst) {
      await page.goto(HOME_URL, { waitUntil: 'domcontentloaded', timeout: 45000 });
      await page.waitForTimeout(3000);
    }

    const consent = options.clickConsent ? await dismissConsent(page) : { clicked: false, label: null };

    await page.goto(TARGET_URL, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(5000);

    if (options.scrollScreens) {
      for (let index = 0; index < options.scrollScreens; index++) {
        await page.evaluate(() => window.scrollBy(0, window.innerHeight));
        await page.waitForTimeout(2000);
      }
    }

    await page.waitForTimeout(5000);
    console.error(`[probe] ${name} done hits=${hits.length}`);
    const tournamentToken = await extractTournamentToken(page);
    const bookmakerBefore = await unlockContext.readBookmakerState();
    const unlockResult = await unlockContext.maybeForceUnlockJ1(TARGET_URL);
    const bookmakerAfter = await unlockContext.readBookmakerState();
    const repairedArchiveResult = await fetchRepairedArchive(page, tournamentToken);
    const currentTournamentResult = await fetchCurrentTournament(page, tournamentToken);
    const domMatches = await extractDomMatches(page, 5);

    const cookies = await context.cookies();
    return {
      name,
      success: true,
      durationMs: Date.now() - startedAt,
      consent,
      finalUrl: page.url(),
      title: await page.title(),
      browserMode: useFullChromium ? 'full_chromium' : 'headless_shell',
      stealth: enableStealth,
      cookieProfile,
      externalSession: {
        path: EXTERNAL_SESSION_PATH,
        sourceFormat: externalSession.sourceFormat,
        injectedCookies: injectedSession.cookies,
        hasExternalUserAgent: Boolean(externalUserAgent)
      },
      documentStatusCode: documentResponses.at(-1)?.status || null,
      cookieNames: cookies.map((item) => item.name).sort(),
      domMatches,
      tournamentToken,
      bookmakerBefore,
      unlockResult,
      bookmakerAfter,
      bookmakerLength: Array.isArray(bookmakerAfter?.myBookmakers) ? bookmakerAfter.myBookmakers.length : 0,
      archiveHits: hits,
      ...repairedArchiveResult
      ,
      ...currentTournamentResult
    };
  } catch (error) {
    return {
      name,
      success: false,
      durationMs: Date.now() - startedAt,
      cookieProfile,
      documentStatusCode: documentResponses.at(-1)?.status || null,
      error: error.message,
      archiveHits: hits
    };
  } finally {
    await context.close().catch(() => {});
    await browser.close().catch(() => {});
  }
}

async function main() {
  const experiments = [
    { name: 'A_no_cookie', gotoHomeFirst: false, clickConsent: false, scrollScreens: 0 },
    { name: 'B_home_and_consent', gotoHomeFirst: true, clickConsent: true, scrollScreens: 0 },
    { name: 'C_home_consent_scroll3', gotoHomeFirst: true, clickConsent: true, scrollScreens: 3 }
  ];
  const onlyExperiment = String(process.env.EXPERIMENT || '').trim();
  const results = [];

  for (const experiment of experiments) {
    if (onlyExperiment && experiment.name !== onlyExperiment) {
      continue;
    }
    results.push(await runExperiment(experiment.name, experiment));
  }

  console.log(JSON.stringify({
    generatedAt: new Date().toISOString(),
    targetUrl: TARGET_URL,
    experiments: results
  }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
