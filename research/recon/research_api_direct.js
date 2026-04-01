'use strict';

const { performance } = require('node:perf_hooks');
const vm = require('node:vm');

const { ReconSessionManager } = require('../../src/infrastructure/recon/services/ReconSessionManager');
const { ReconPureDecryptor } = require('../../src/infrastructure/recon/services/ReconPureDecryptor');

const DEFAULT_RESULTS_URL = 'https://www.oddsportal.com/football/england/premier-league-2025-2026/results/';
const DEFAULT_SESSION_PATH = process.env.RECON_SESSION_PATH || '/app/11';
const DEFAULT_UA = process.env.RECON_USER_AGENT
  || 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36';
const DEFAULT_SEC_CH_UA = process.env.RECON_SEC_CH_UA
  || '"Not:A-Brand";v="99", "HeadlessChrome";v="145", "Chromium";v="145"';

class CookieJar {
  constructor(initialCookies = []) {
    this.cookies = new Map();
    for (const cookie of initialCookies || []) {
      if (cookie?.name) {
        this.cookies.set(cookie.name, cookie.value || '');
      }
    }
  }

  absorb(setCookies = []) {
    for (const raw of setCookies || []) {
      const [pair] = String(raw || '').split(';');
      const separatorIndex = pair.indexOf('=');
      if (separatorIndex <= 0) {
        continue;
      }

      this.cookies.set(
        pair.slice(0, separatorIndex).trim(),
        pair.slice(separatorIndex + 1).trim()
      );
    }
  }

  toHeader() {
    return [...this.cookies.entries()]
      .map(([name, value]) => `${name}=${value}`)
      .join('; ');
  }
}

function buildCookieHeader(cookies = []) {
  return cookies
    .map((cookie) => `${cookie.name}=${cookie.value}`)
    .join('; ');
}

async function fetchText(url, headers = [], cookieJar = null) {
  const finalHeaders = new Headers();
  for (const [name, value] of headers) {
    if (value !== undefined && value !== null && value !== '') {
      finalHeaders.append(name, value);
    }
  }

  const cookieHeader = cookieJar ? cookieJar.toHeader() : '';
  if (cookieHeader && !finalHeaders.has('cookie')) {
    finalHeaders.append('cookie', cookieHeader);
  }

  const response = await fetch(url, {
    headers: finalHeaders,
    redirect: 'follow'
  });

  const text = await response.text();
  const setCookies = typeof response.headers.getSetCookie === 'function'
    ? response.headers.getSetCookie()
    : [];
  if (cookieJar) {
    cookieJar.absorb(setCookies);
  }

  return {
    ok: response.ok,
    status: response.status,
    text,
    headers: Object.fromEntries(response.headers.entries()),
    setCookies
  };
}

function parseBundleUrl(html, baseUrl) {
  const match = String(html || '').match(/<script[^>]+src="([^"]*\/build\/assets\/app-[^"]+\.js)"/i);
  return match ? new URL(match[1], baseUrl).href : '';
}

function parseAjaxUserDataUrl(html, baseUrl) {
  const match = String(html || '').match(/<script[^>]+src="([^"]*\/ajax-user-data\/[^"]+)"/i);
  return match ? new URL(match[1], baseUrl).href : '';
}

function parseOtCode(scriptBody) {
  const raw = String(scriptBody || '');
  const direct = raw.match(/"otCode":"([^"]+)"/);
  if (direct) {
    return direct[1];
  }

  const escaped = raw.match(/\\"otCode\\":\\"([^"]+)\\"/);
  return escaped ? escaped[1] : '';
}

function parsePageVar(scriptBody) {
  const raw = String(scriptBody || '');
  const match = raw.match(/JSON\.parse\((['"])((?:\\.|(?!\1)[\s\S])*)\1\)/);
  if (!match) {
    return {};
  }

  try {
    const decoded = vm.runInNewContext(`${match[1]}${match[2]}${match[1]}`, Object.create(null), {
      timeout: 1000
    });
    const parsed = JSON.parse(decoded);
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

function buildArchiveUrl(otCode) {
  if (!otCode) {
    throw new Error('otCode missing');
  }

  return `https://www.oddsportal.com/ajax-sport-country-tournament-archive_/1/${otCode}/X/2025-2026/1/0/?_=${Date.now()}`;
}

function extractRowsPayload(parsed) {
  if (Array.isArray(parsed?.d?.rows)) {
    return parsed.d.rows;
  }

  if (Array.isArray(parsed?.rows)) {
    return parsed.rows;
  }

  if (Array.isArray(parsed?.matches)) {
    return parsed.matches;
  }

  return [];
}

function sanitizeRow(row) {
  if (!row || typeof row !== 'object') {
    return row;
  }

  const subset = {};
  for (const key of ['id', 'hid', 'aid', 'home_name', 'away_name', 'url', 't', 'date', 'score']) {
    if (row[key] !== undefined) {
      subset[key] = row[key];
    }
  }

  return Object.keys(subset).length > 0 ? subset : row;
}

function summarizePayloadShape(parsed) {
  const topLevelKeys = parsed && typeof parsed === 'object' ? Object.keys(parsed) : [];
  const payload = parsed?.d && typeof parsed.d === 'object' ? parsed.d : parsed;
  const payloadKeys = payload && typeof payload === 'object' ? Object.keys(payload).slice(0, 30) : [];

  return {
    topLevelKeys,
    payloadKeys,
    nullResultText: payload?.nullResultText || parsed?.nullResultText || '',
    samplePayload: payload && typeof payload === 'object'
      ? Object.fromEntries(
        Object.entries(payload)
          .filter(([key]) => ['nullResultText', 'rows', 'matches', 'pagination', 'page', 'total'].includes(key))
      )
      : payload
  };
}

function summarizePageState(pageVar) {
  return {
    otCode: pageVar?.otCode || '',
    geoIPcode: pageVar?.userData?.geoIPcode || '',
    isLimitedUserRestricted: Boolean(pageVar?.userData?.isLimitedUserRestricted),
    bookmakerCount: Array.isArray(pageVar?.userData?.myBookmakers) ? pageVar.userData.myBookmakers.length : 0,
    bookiehash: pageVar?.userData?.bookiehash || ''
  };
}

async function main() {
  const session = process.env.RESEARCH_DISABLE_SESSION === '1'
    ? { cookies: [], userAgent: '' }
    : new ReconSessionManager({
      sessionPath: DEFAULT_SESSION_PATH,
      traceId: 'research-api-direct',
      logger: console
    }).load({ excludeNames: [] });
  const userAgent = session.userAgent || DEFAULT_UA;
  const cookieJar = new CookieJar(session.cookies);

  const pageHeaders = [
    ['sec-ch-ua', DEFAULT_SEC_CH_UA],
    ['sec-ch-ua-mobile', '?0'],
    ['sec-ch-ua-platform', '"Linux"'],
    ['upgrade-insecure-requests', '1'],
    ['user-agent', userAgent],
    ['accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'],
    ['sec-fetch-site', 'none'],
    ['sec-fetch-mode', 'navigate'],
    ['sec-fetch-user', '?1'],
    ['sec-fetch-dest', 'document'],
    ['accept-language', 'en-US,en;q=0.9'],
    ['cache-control', 'no-cache'],
    ['pragma', 'no-cache']
  ];

  const apiHeaders = [
    ['sec-ch-ua-platform', '"Linux"'],
    ['referer', DEFAULT_RESULTS_URL],
    ['sec-ch-ua', DEFAULT_SEC_CH_UA],
    ['sec-ch-ua-mobile', '?0'],
    ['x-requested-with', 'XMLHttpRequest'],
    ['user-agent', userAgent],
    ['accept', 'application/json, text/plain, */*'],
    ['content-type', 'application/json'],
    ['sec-fetch-site', 'same-origin'],
    ['sec-fetch-mode', 'cors'],
    ['sec-fetch-dest', 'empty'],
    ['accept-language', 'en-US,en;q=0.9']
  ];

  const fetchStart = performance.now();
  console.error('[research] fetch results page');
  const pageResponse = await fetchText(DEFAULT_RESULTS_URL, pageHeaders, cookieJar);
  const pageFetchMs = performance.now() - fetchStart;
  if (!pageResponse.ok) {
    throw new Error(`results page failed: HTTP_${pageResponse.status}`);
  }

  const bundleUrl = parseBundleUrl(pageResponse.text, DEFAULT_RESULTS_URL);
  const ajaxUserDataUrl = parseAjaxUserDataUrl(pageResponse.text, DEFAULT_RESULTS_URL);
  if (!bundleUrl || !ajaxUserDataUrl) {
    throw new Error('bundle or ajax-user-data url missing');
  }

  console.error('[research] fetch ajax-user-data');
  const ajaxHeaders = [
    ['sec-ch-ua-platform', '"Linux"'],
    ['referer', DEFAULT_RESULTS_URL],
    ['sec-ch-ua', DEFAULT_SEC_CH_UA],
    ['sec-ch-ua-mobile', '?0'],
    ['user-agent', userAgent],
    ['accept', '*/*'],
    ['sec-fetch-site', 'same-origin'],
    ['sec-fetch-mode', 'no-cors'],
    ['sec-fetch-dest', 'script'],
    ['accept-language', 'en-US,en;q=0.9']
  ];
  const ajaxUserDataResponse = await fetchText(ajaxUserDataUrl, ajaxHeaders, cookieJar);
  if (!ajaxUserDataResponse.ok) {
    throw new Error(`ajax-user-data failed: HTTP_${ajaxUserDataResponse.status}`);
  }

  const otCode = parseOtCode(ajaxUserDataResponse.text);
  const pageVar = parsePageVar(ajaxUserDataResponse.text);
  if (!otCode) {
    throw new Error('otCode not found');
  }

  const archiveUrl = buildArchiveUrl(otCode);
  const apiStart = performance.now();
  console.error('[research] fetch archive api');
  const archiveResponse = await fetchText(archiveUrl, apiHeaders, cookieJar);
  const apiFetchMs = performance.now() - apiStart;
  if (!archiveResponse.ok) {
    throw new Error(`archive api failed: HTTP_${archiveResponse.status}`);
  }

  const pureDecryptor = new ReconPureDecryptor({
    traceId: 'research-api-direct',
    logger: console
  });

  console.error('[research] load pure decryptor');
  const decryptorLoadStart = performance.now();
  await pureDecryptor.loadFromBundleUrl(bundleUrl, {
    headers: pageHeaders,
    sampleEncryptedData: archiveResponse.text,
    globals: {
      pageVar,
      pageOutrightsVar: pageVar
    }
  });
  const decryptorLoadMs = performance.now() - decryptorLoadStart;

  const decryptStart = performance.now();
  console.error('[research] decrypt payload');
  const parsed = await pureDecryptor.decrypt(archiveResponse.text);
  const decryptMs = performance.now() - decryptStart;
  const rows = extractRowsPayload(parsed);

  console.log(JSON.stringify({
    resultsUrl: DEFAULT_RESULTS_URL,
    bundleUrl,
    ajaxUserDataUrl,
    archiveUrl,
    algorithmVersion: pureDecryptor.getAlgorithmVersion(),
    pageFetchMs: Number(pageFetchMs.toFixed(2)),
    apiFetchMs: Number(apiFetchMs.toFixed(2)),
    decryptorLoadMs: Number(decryptorLoadMs.toFixed(2)),
    decryptMs: Number(decryptMs.toFixed(2)),
    rowCount: rows.length,
    sampleRows: rows.slice(0, 3).map(sanitizeRow),
    ...(process.env.RESEARCH_DEBUG === '1' ? { pageState: summarizePageState(pageVar) } : {}),
    ...(process.env.RESEARCH_DEBUG === '1' ? { cookieJar: cookieJar.toHeader() } : {}),
    ...(process.env.RESEARCH_DEBUG === '1' ? summarizePayloadShape(parsed) : {})
  }, null, 2));
}

main().catch((error) => {
  console.error(JSON.stringify({
    error: error.message,
    stack: error.stack
  }, null, 2));
  process.exitCode = 1;
});
