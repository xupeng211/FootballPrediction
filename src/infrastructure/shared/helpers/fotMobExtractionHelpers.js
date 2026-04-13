'use strict';

function normalizeLeagueId(value) {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

function extractLeagueIdFromFallbackKey(key) {
  const rawKey = String(key || '').trim();
  if (!rawKey || !/leagues/i.test(rawKey)) {
    return null;
  }

  try {
    const parsed = new URL(rawKey, 'https://www.fotmob.com');
    const queryLeagueId = normalizeLeagueId(parsed.searchParams.get('id') || parsed.searchParams.get('leagueId'));
    if (queryLeagueId) {
      return queryLeagueId;
    }

    const pathMatch = parsed.pathname.match(/\/leagues\/(\d+)(?:\/|$)/i);
    return pathMatch ? normalizeLeagueId(pathMatch[1]) : null;
  } catch {
    const queryMatch = rawKey.match(/[?&](?:id|leagueId)=(\d+)(?:&|$)/i);
    if (queryMatch) {
      return normalizeLeagueId(queryMatch[1]);
    }

    const pathMatch = rawKey.match(/\/leagues\/(\d+)(?:\/|$)/i);
    return pathMatch ? normalizeLeagueId(pathMatch[1]) : null;
  }
}

function resolveFallbackLeagueKey(fallback, leagueId) {
  const normalizedLeagueId = normalizeLeagueId(leagueId);
  if (!fallback || typeof fallback !== 'object' || !normalizedLeagueId) {
    return '';
  }

  return Object.keys(fallback).find((key) => extractLeagueIdFromFallbackKey(key) === normalizedLeagueId) || '';
}

function extractPrimaryLeagueData(pageProps, leagueId, season, countMatches, logger = console) {
  const fallback = pageProps?.fallback;
  if (fallback && typeof fallback === 'object') {
    const leagueKey = resolveFallbackLeagueKey(fallback, leagueId);

    if (leagueKey && fallback[leagueKey]) {
      const data = fallback[leagueKey];
      const matchCount = countMatches(data);
      logger.info(`[HOUND-SOUL] ✅ 从 fallback["${leagueKey}"] 提取 ${matchCount} 场数据`);
      return { data, matchCount };
    }
  }

  if (pageProps?.fixtures || pageProps?.allMatches) {
    const data = {
      fixtures: pageProps.fixtures || pageProps.allMatches,
      leagueId,
      season,
      ...pageProps
    };
    const matchCount = countMatches(data);
    logger.info(`[HOUND-SOUL] ✅ 从 pageProps 提取 ${matchCount} 场数据`);
    return { data, matchCount };
  }

  return { data: null, matchCount: 0 };
}

function buildDomScanPayload(domData, leagueId, season) {
  return {
    fixtures: { allMatches: domData },
    leagueId,
    season,
    _source: 'dom_scan'
  };
}

function dedupeById(entries = []) {
  const results = [];
  const seen = new Set();

  for (const entry of entries) {
    if (seen.has(entry.id)) {
      continue;
    }

    seen.add(entry.id);
    results.push(entry);
  }

  return results;
}

module.exports = {
  buildDomScanPayload,
  dedupeById,
  extractPrimaryLeagueData
};
