'use strict';

const { RECON_CONFIG } = require('../../../src/infrastructure/recon/services/ReconServiceConfig');
const { reconMatchExtractor } = require('../../../src/infrastructure/recon/services/ReconMatchExtractor');
const { CANONICAL_RESYNC_LEAGUE_IDS } = require('./restoreMappingsShared');

function collectTeamSlugs(config = RECON_CONFIG) {
  const buckets = Object.values(config?.team_slugs || {});
  return [...new Set(
    buckets.flatMap((items) => Array.isArray(items) ? items : [])
      .map((item) => String(item || '').trim())
      .filter(Boolean)
  )];
}

function isPlainObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function isH2hUrl(url) {
  return /\/football\/h2h\//iu.test(String(url || '').trim());
}

function isCanonicalEventUrl(url) {
  const rawUrl = String(url || '').trim();
  if (!rawUrl || isH2hUrl(rawUrl)) {
    return false;
  }

  try {
    const pathname = new URL(rawUrl).pathname;
    return /\/football\/.+-[A-Za-z0-9]{8}\/?$/u.test(pathname);
  } catch {
    return /\/football\/.+-[A-Za-z0-9]{8}\/?$/u.test(rawUrl);
  }
}

function looksLikeRealHash(hash) {
  return /^[A-Za-z0-9]{8}$/u.test(String(hash || '').trim());
}

function isEvidencePlaceholderUrl(url) {
  return /^evidence:\/\//iu.test(String(url || '').trim());
}

function extractHashFromUrl(url, fallbackHash = null) {
  const normalizedFallback = String(fallbackHash || '').trim();
  if (looksLikeRealHash(normalizedFallback)) {
    return normalizedFallback;
  }

  const rawUrl = String(url || '').trim();
  if (!rawUrl) {
    return '';
  }

  const fragmentMatch = rawUrl.match(/#([A-Za-z0-9]{8})$/u);
  if (fragmentMatch) {
    return fragmentMatch[1];
  }

  const segmentMatch = rawUrl.match(/-([A-Za-z0-9]{8})\/?$/u);
  return segmentMatch ? segmentMatch[1] : '';
}

function dedupeCandidates(candidates = []) {
  const seen = new Set();
  const deduped = [];

  for (const candidate of Array.isArray(candidates) ? candidates : []) {
    if (!candidate) {
      continue;
    }

    const key = [
      String(candidate.hash || '').trim(),
      String(candidate.url || '').trim(),
      String(candidate.homeTeam || '').trim(),
      String(candidate.awayTeam || '').trim()
    ].join('::');

    if (!key || seen.has(key)) {
      continue;
    }

    seen.add(key);
    deduped.push(candidate);
  }

  return deduped;
}

function createExtractor(sourceUrl = null) {
  const baseUrl = RECON_CONFIG?.oddsportal?.base_url || 'https://www.oddsportal.com';
  return {
    baseUrl,
    sourceUrl: sourceUrl || undefined,
    resultsUrl: sourceUrl || undefined,
    leagueUrl: sourceUrl || undefined,
    extractMaxDepth: 8,
    ...reconMatchExtractor
  };
}

function pickSignalUrl(node) {
  return [node.url, node.link, node.matchUrl]
    .find((value) => typeof value === 'string' && value.trim()) || '';
}

function resolveSignalHash(node, url) {
  const directHash = [node.encodeEventId, node.eventHash, node.hash]
    .find((value) => looksLikeRealHash(value));
  return String(directHash || extractHashFromUrl(url) || '').trim();
}

function resolveSignalSlug(node) {
  return String(node.slug || node.eventSlug || '').trim();
}

function hasValidSignalPath(url, slug) {
  const hasFootballPath = /(?:^https?:\/\/[^/]+)?\/football\//iu.test(url);
  if (!hasFootballPath && !slug) {
    return false;
  }

  return !(url && /\/matches\//iu.test(url) && !hasFootballPath);
}

function resolveSignalHomeTeam(node) {
  return node.homeTeam ?? node.homeName ?? node.home ?? node.home_team ?? node['home-name'] ?? null;
}

function resolveSignalAwayTeam(node) {
  return node.awayTeam ?? node.awayName ?? node.away ?? node.away_team ?? node['away-name'] ?? null;
}

function buildSignalIdentity(node, url, hash, slug) {
  return {
    encodeEventId: hash,
    slug: slug || undefined,
    eventSlug: slug || undefined,
    countrySlug: node.countrySlug || node.country || undefined,
    leagueSlug: node.leagueSlug || node.competitionSlug || undefined,
    url: url || undefined
  };
}

function buildNormalizedSignal(node, url, hash, slug) {
  return {
    homeTeam: resolveSignalHomeTeam(node),
    awayTeam: resolveSignalAwayTeam(node),
    participants: Array.isArray(node.participants) ? node.participants : undefined,
    ...buildSignalIdentity(node, url, hash, slug),
    matchDate: node.matchDate || node.match_date || node.date || undefined,
    'date-start-timestamp': node['date-start-timestamp'] || undefined
  };
}

function normalizeRawSignalObject(node) {
  const url = String(pickSignalUrl(node) || '').trim();
  const hash = resolveSignalHash(node, url);
  const slug = resolveSignalSlug(node);

  if (!hash || !hasValidSignalPath(url, slug)) {
    return null;
  }

  return buildNormalizedSignal(node, url, hash, slug);
}

function extractRawOddsPortalCandidates(rawData, sourceUrl = null) {
  if (!rawData || typeof rawData !== 'object') {
    return [];
  }

  const extractor = createExtractor(sourceUrl);
  const collectedSignals = [];
  const queue = [{ value: rawData, depth: 0 }];

  while (queue.length > 0) {
    const { value, depth } = queue.shift();
    if (depth > 8 || !value || typeof value !== 'object') {
      continue;
    }

    if (Array.isArray(value)) {
      for (const item of value) {
        queue.push({ value: item, depth: depth + 1 });
      }
      continue;
    }

    const normalizedSignal = normalizeRawSignalObject(value);
    if (normalizedSignal) {
      collectedSignals.push(normalizedSignal);
    }

    for (const nestedValue of Object.values(value)) {
      if (nestedValue && typeof nestedValue === 'object') {
        queue.push({ value: nestedValue, depth: depth + 1 });
      }
    }
  }

  return dedupeCandidates(
    collectedSignals
      .map((signal) => extractor.normalizeMatchObject(signal, 'raw_restore'))
      .filter(Boolean)
  );
}

function buildEvidenceCandidate(row) {
  if (!row?.evidence_hash && !row?.evidence_url) {
    return null;
  }

  const realHash = extractHashFromUrl(row.evidence_url, row.evidence_hash);
  if (!realHash) {
    return null;
  }

  const url = isEvidencePlaceholderUrl(row.evidence_url)
    ? ''
    : String(row.evidence_url || '').trim();

  return {
    hash: realHash,
    url,
    homeTeam: String(row.evidence_home_team || row.home_team || '').trim(),
    awayTeam: String(row.evidence_away_team || row.away_team || '').trim(),
    matchDate: row.match_date || null
  };
}

function buildBrazilCanonicalCandidate(row, sourceUrl = null) {
  if (Number(row?.league_id) !== 268) {
    return null;
  }

  const currentUrl = String(row?.full_url || row?.evidence_url || '').trim();
  const currentHash = extractHashFromUrl(currentUrl, row?.oddsportal_hash || row?.evidence_hash);
  if (!looksLikeRealHash(currentHash) || !currentUrl) {
    return null;
  }

  const extractor = createExtractor(sourceUrl);
  const candidate = extractor.normalizeMatchObject({
    'home-name': row?.remote_home_team || row?.evidence_home_team || row?.home_team || '',
    'away-name': row?.remote_away_team || row?.evidence_away_team || row?.away_team || '',
    encodeEventId: currentHash,
    countrySlug: 'brazil',
    leagueSlug: 'serie-a',
    url: currentUrl
  }, 'canonical_brazil_resync');

  return candidate && isCanonicalEventUrl(candidate.url) ? candidate : null;
}

function candidateHitsDictionary(evaluator, candidate, matchRow) {
  if (!evaluator || !candidate || !matchRow) {
    return false;
  }

  const directDictionaryMatch = evaluator.isDictionaryExactMatch(candidate.homeTeam, matchRow.home_team)
    && evaluator.isDictionaryExactMatch(candidate.awayTeam, matchRow.away_team);
  const swappedDictionaryMatch = evaluator.isDictionaryExactMatch(candidate.homeTeam, matchRow.away_team)
    && evaluator.isDictionaryExactMatch(candidate.awayTeam, matchRow.home_team);

  if (directDictionaryMatch || swappedDictionaryMatch) {
    return true;
  }

  return Boolean(
    evaluator.resolveLeagueDictionaryEntry(candidate.homeTeam)
    && evaluator.resolveLeagueDictionaryEntry(candidate.awayTeam)
  );
}

function chooseCanonicalOverride(row, resolvedCandidate, rawCandidates = [], sourceUrl = null) {
  const resolvedHash = extractHashFromUrl(resolvedCandidate?.url, resolvedCandidate?.hash);
  if (!CANONICAL_RESYNC_LEAGUE_IDS.has(Number(row?.league_id))) {
    return null;
  }

  const rawCanonical = rawCandidates.find((candidate) => (
    isCanonicalEventUrl(candidate?.url)
    && extractHashFromUrl(candidate?.url, candidate?.hash) === resolvedHash
  ));
  if (rawCanonical) {
    return rawCanonical;
  }

  if (Number(row?.league_id) === 268) {
    return buildBrazilCanonicalCandidate({
      ...row,
      full_url: resolvedCandidate?.url || row?.full_url || row?.evidence_url,
      oddsportal_hash: resolvedHash,
      remote_home_team: resolvedCandidate?.homeTeam || row?.remote_home_team,
      remote_away_team: resolvedCandidate?.awayTeam || row?.remote_away_team
    }, sourceUrl);
  }

  return null;
}

module.exports = {
  collectTeamSlugs,
  isPlainObject,
  isH2hUrl,
  isCanonicalEventUrl,
  looksLikeRealHash,
  isEvidencePlaceholderUrl,
  extractHashFromUrl,
  dedupeCandidates,
  createExtractor,
  normalizeRawSignalObject,
  extractRawOddsPortalCandidates,
  buildEvidenceCandidate,
  buildBrazilCanonicalCandidate,
  candidateHitsDictionary,
  chooseCanonicalOverride
};
