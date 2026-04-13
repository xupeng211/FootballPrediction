'use strict';

const { JSDOM } = require('jsdom');

const EMBEDDED_PLACEHOLDER_STATUS_RE = /^\s*URL:[\s\S]*?\bStatus:\s*(\d{3})\b/i;
const BACKEND_FETCH_FAILED_RE = /backend fetch failed|guru meditation/i;

function decodeHtmlEntities(text = '') {
  return String(text || '')
    .replace(/&quot;/g, '"')
    .replace(/&#34;/g, '"')
    .replace(/&#39;/g, '\'')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>');
}

function addProtocolCandidate(bucket, value, state) {
  const normalized = String(value ?? '').trim();
  if (!normalized || /^(?:null|undefined)$/i.test(normalized) || state[bucket].includes(normalized)) {
    return;
  }

  state[bucket].push(normalized);
}

function readScriptTextsFromHtml(html) {
  try {
    const dom = new JSDOM(String(html || ''));
    return Array.from(dom.window.document.scripts).map((script) => String(script.textContent || ''));
  } catch {
    return [];
  }
}

function tryParseEmbeddedJson(rawValue, options = {}) {
  let payload = decodeHtmlEntities(String(rawValue || '')).trim();
  if (!payload) {
    return null;
  }

  if (
    options.unwrapQuotedJson === true
    && ((payload.startsWith('\'') && payload.endsWith('\'')) || (payload.startsWith('"') && payload.endsWith('"')))
  ) {
    payload = payload.slice(1, -1);
  }
  if (payload.endsWith(';')) {
    payload = payload.slice(0, -1).trim();
  }

  try {
    return JSON.parse(payload);
  } catch {
    return null;
  }
}

function extractStructuredStatePayloads(html) {
  const payloads = [];
  const rawHtml = String(html || '');
  const nextDataMatch = rawHtml.match(/<script[^>]+id=["']__NEXT_DATA__["'][^>]*>([\s\S]*?)<\/script>/i);
  if (nextDataMatch?.[1]) {
    payloads.push({ source: '__NEXT_DATA__', value: nextDataMatch[1], unwrapQuotedJson: false });
  }

  for (const scriptText of readScriptTextsFromHtml(rawHtml)) {
    for (const [source, pattern, unwrapQuotedJson] of [
      ['__INITIAL_STATE__', /(?:window\.)?__INITIAL_STATE__\s*=\s*({[\s\S]*})\s*;?/i, false],
      ['initialState', /(?:window\.)?initialState\s*=\s*({[\s\S]*})\s*;?/i, false],
      ['pageVar:json', /(?:window\.)?pageVar\s*=\s*({[\s\S]*})\s*;?/i, false],
      ['pageVar:string', /(?:window\.)?pageVar\s*=\s*('(?:\\'|[^'])*'|"(?:\\"|[^"])*")\s*;?/i, true]
    ]) {
      const match = scriptText.match(pattern);
      if (match?.[1]) {
        payloads.push({ source, value: match[1], unwrapQuotedJson });
      }
    }
  }

  return payloads;
}

function buildPureProtocolTargetHints(target = {}, html = '') {
  const hints = new Set();

  try {
    const pathname = new URL(target?.baseUrl || target?.url || '').pathname;
    const segments = pathname.split('/').filter(Boolean);
    const leagueSegment = segments.at(-2) === 'results' ? segments.at(-3) : segments.at(-1);
    const normalizedLeagueSegment = String(leagueSegment || '').trim().toLowerCase();
    if (normalizedLeagueSegment) {
      hints.add(normalizedLeagueSegment);
      hints.add(normalizedLeagueSegment.replace(/-\d{4}(?:-\d{4})?$/i, ''));
      hints.add(normalizedLeagueSegment.replace(/-/g, ' '));
    }
  } catch {
    // ignore invalid URL
  }

  const tournamentName = decodeHtmlEntities(html).match(/_tournamentName\s*["']?\s*:\s*"([^"]+)"/i)?.[1] || '';
  if (tournamentName) {
    const normalizedTournamentName = String(tournamentName).trim().toLowerCase();
    hints.add(normalizedTournamentName);
    hints.add(normalizedTournamentName.replace(/\s+/g, '-'));
    hints.add(normalizedTournamentName.replace(/\s+\d{4}(?:\/\d{4})?$/i, ''));
  }

  return [...hints].filter(Boolean);
}

function objectMatchesTargetHints(node, hints = []) {
  if (!node || typeof node !== 'object' || hints.length === 0) {
    return false;
  }

  const comparableValues = [
    node.name,
    node.title,
    node.slug,
    node.url,
    node.pathname,
    node.route,
    node.tournamentName,
    node._tournamentName,
    node._tournamentUrl,
    node._tournamentLink,
    node._tournamentLinkNoSeason
  ]
    .map((value) => String(value || '').trim().toLowerCase())
    .filter(Boolean);

  return comparableValues.some((value) => hints.some((hint) => value.includes(hint)));
}

function collectPageVarCandidates(node, targetState, pageVarLike) {
  if (!pageVarLike) {
    return;
  }

  addProtocolCandidate('pageVarOtCodes', node.otCode, targetState);
  addProtocolCandidate('bookmakerHashes', node.bookiehash, targetState);
  addProtocolCandidate('bookmakerHashes', node.myot, targetState);
}

function collectTournamentCandidates(node, targetState, tournamentLike) {
  if (!tournamentLike) {
    return;
  }

  addProtocolCandidate('tournamentIds', node._tournamentId, targetState);
  addProtocolCandidate('tournamentIds', node.tournamentId, targetState);
  addProtocolCandidate('tournamentIds', node.tournament_id, targetState);
  const idValue = node.outrightId ?? node.otCode ?? node.id;
  if (/^\d+$/.test(String(idValue ?? '').trim())) {
    addProtocolCandidate('tournamentIds', idValue, targetState);
    return;
  }

  addProtocolCandidate('tournamentObjectIds', idValue, targetState);
}

function collectStructuredProtocolStateCandidates(node, hints = [], trail = [], state = null) {
  const targetState = state || {
    tournamentObjectIds: [],
    pageVarOtCodes: [],
    tournamentIds: [],
    bookmakerHashes: []
  };

  if (node === null || node === undefined) {
    return targetState;
  }
  if (Array.isArray(node)) {
    for (const item of node) {
      collectStructuredProtocolStateCandidates(item, hints, trail, targetState);
    }
    return targetState;
  }
  if (typeof node !== 'object') {
    return targetState;
  }

  const trailText = trail.join('.').toLowerCase();
  const objectFingerprint = `${trailText} ${Object.keys(node).join(' ')}`.toLowerCase();
  const pageVarLike = objectFingerprint.includes('pagevar');
  const tournamentLike = objectFingerprint.includes('tournament') || objectFingerprint.includes('outright');
  collectPageVarCandidates(node, targetState, pageVarLike);
  collectTournamentCandidates(node, targetState, tournamentLike || objectMatchesTargetHints(node, hints));

  for (const [key, value] of Object.entries(node)) {
    collectStructuredProtocolStateCandidates(value, hints, [...trail, key], targetState);
  }

  return targetState;
}

function extractEmbeddedProtocolStateFromHtml(html, target = {}) {
  const stateCandidates = {
    tournamentObjectIds: [],
    pageVarOtCodes: [],
    tournamentIds: [],
    bookmakerHashes: []
  };
  const hints = buildPureProtocolTargetHints(target, html);

  for (const payload of extractStructuredStatePayloads(html)) {
    const parsed = tryParseEmbeddedJson(payload.value, {
      unwrapQuotedJson: payload.unwrapQuotedJson === true
    });
    if (parsed) {
      collectStructuredProtocolStateCandidates(parsed, hints, [payload.source], stateCandidates);
    }
  }

  return {
    outrightId: stateCandidates.tournamentObjectIds[0] || stateCandidates.pageVarOtCodes[0] || '',
    tournamentId: stateCandidates.tournamentIds[0] || '',
    bookmakerHash: stateCandidates.bookmakerHashes[0] || ''
  };
}

function detectEmbeddedHttpFailure(bodyText = '') {
  const text = String(bodyText || '').trim();
  if (!text) {
    return null;
  }

  const placeholderMatch = text.match(EMBEDDED_PLACEHOLDER_STATUS_RE);
  if (placeholderMatch) {
    return {
      statusCode: Number(placeholderMatch[1]) || 503,
      error: `EMBEDDED_HTTP_${placeholderMatch[1] || '503'}`
    };
  }

  return BACKEND_FETCH_FAILED_RE.test(text)
    ? { statusCode: 503, error: 'EMBEDDED_HTTP_503' }
    : null;
}

function extractPureProtocolSeasonToken(baseUrl, options = {}) {
  const normalizedBaseUrl = String(baseUrl || '').trim();
  const fromUrl = normalizedBaseUrl.match(/-((?:\d{4})(?:-\d{4})?)\/results\/?$/i)?.[1];
  if (fromUrl) {
    return fromUrl;
  }

  const season = String(options.season || options.dbSeason || '').trim();
  if (/^\d{4}\/\d{4}$/.test(season)) {
    return season.replace('/', '-');
  }
  return /^\d{4}(?:-\d{4})?$/.test(season) ? season : '';
}

function extractAppBundleUrlFromHtml(html, baseUrl) {
  const text = String(html || '');
  const relativeUrl = text.match(/<script[^>]+type="module"[^>]+src="([^"]*\/build\/assets\/app-[^"]+\.js[^"]*)"/i)?.[1]
    || text.match(/<link[^>]+rel="modulepreload"[^>]+href="([^"]*\/build\/assets\/app-[^"]+\.js[^"]*)"/i)?.[1]
    || '';

  if (!relativeUrl) {
    return '';
  }

  try {
    return new URL(relativeUrl, baseUrl).href;
  } catch {
    return '';
  }
}

function extractTournamentIdFromHtml(html) {
  const text = decodeHtmlEntities(html);
  const raw = text.match(/(?:_tournamentId|tournamentId)\s*["']?\s*:\s*(?:"([^"]+)"|'([^']+)'|([A-Za-z0-9-]+))/i);
  const token = String(raw?.[1] || raw?.[2] || raw?.[3] || '').trim();
  return /^(?:null|undefined)$/i.test(token) ? '' : token;
}

function extractLocaleFromHtml(html) {
  const text = String(html || '');
  return text.match(/_lang(?:&quot;|"):(?:&quot;|")([a-z-]+)(?:&quot;|")/i)?.[1]
    || text.match(/lang="([a-z-]+)"/i)?.[1]
    || 'en';
}

function normalizePureProtocolComparableUrl(url = '') {
  const normalized = String(url || '').trim();
  if (!normalized) {
    return '';
  }

  try {
    const parsed = new URL(normalized);
    parsed.hash = '';
    parsed.search = '';
    return parsed.href.replace(/\/+$/, '');
  } catch {
    return normalized.replace(/[?#].*$/, '').replace(/\/+$/, '');
  }
}

module.exports = {
  detectEmbeddedHttpFailure,
  extractAppBundleUrlFromHtml,
  extractEmbeddedProtocolStateFromHtml,
  extractLocaleFromHtml,
  extractPureProtocolSeasonToken,
  extractTournamentIdFromHtml,
  normalizePureProtocolComparableUrl
};
