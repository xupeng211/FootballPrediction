'use strict';

const { JSDOM } = require('jsdom');

function buildParseContext(context, document, options) {
  const currentUrl = options.currentUrl || context.baseUrl;
  const leaguePathPrefix = String(options.leaguePathPrefix || '').trim();
  return {
    currentUrl,
    document,
    eventScopeSelectors: options.eventScopeSelectors || [],
    forceJsonExtract: options.forceJsonExtract === true,
    leaguePathPrefix,
    canonicalLeaguePathPrefix: context._extractCanonicalLeaguePathPrefix(
      document.querySelector('link[rel="canonical"]')?.href || ''
    ),
    source: options.source || 'current_results_dom'
  };
}

function appendStructuredMatches(context, rawHtml, matches, seen, parseContext) {
  const seeds = [
    {
      candidates: context._extractFromNextData(rawHtml),
      source: 'current_results_next_data'
    },
    {
      candidates: context._extractFromEmbeddedJsonScripts(rawHtml),
      source: 'current_results_script_json'
    }
  ];

  for (const seed of seeds) {
    context._appendCandidateMatches(matches, seen, seed.candidates, {
      ...parseContext,
      source: seed.source
    });
  }
}

function collectResultAnchors(context, document, options) {
  const configuredSelector = (options.resultAnchorSelectors || []).filter(Boolean).join(', ');
  const baseAnchors = configuredSelector
    ? Array.from(document.querySelectorAll(configuredSelector))
    : [];
  const fallbackAnchors = context._collectEventAnchors(document);
  const dynamicAnchors = context._probeAnchorPatterns(document);
  return [...new Set([...baseAnchors, ...fallbackAnchors, ...dynamicAnchors])];
}

function resolveAnchorTeams(context, anchor, scope, pathname) {
  let { homeTeam, awayTeam } = context._extractTeamsFromScope(scope);
  if (!homeTeam || !awayTeam) {
    const parsedH2hNames = context._extractTeamsFromH2hPath(pathname);
    homeTeam = homeTeam || parsedH2hNames.homeTeam;
    awayTeam = awayTeam || parsedH2hNames.awayTeam;
  }
  if (!homeTeam || !awayTeam) {
    const parsedNames = context._extractNamesFromSlug(pathname);
    homeTeam = homeTeam || parsedNames.homeTeam;
    awayTeam = awayTeam || parsedNames.awayTeam;
  }
  if (!homeTeam || !awayTeam) {
    const parsedFromText = context._extractTeamsFromText(anchor.textContent || anchor.getAttribute('title') || '');
    homeTeam = homeTeam || parsedFromText.homeTeam;
    awayTeam = awayTeam || parsedFromText.awayTeam;
  }

  return { homeTeam, awayTeam };
}

function buildAnchorCandidate(context, anchor, parseContext, seen) {
  const absoluteHref = context._resolveHref(anchor.getAttribute('href') || '', parseContext.currentUrl);
  if (!absoluteHref) {
    return null;
  }

  const pathname = context._getPathname(absoluteHref);
  if (
    !pathname
    || /\/(results|standings|outrights)\/?$/i.test(pathname)
    || !context._isCandidateInScope(pathname, parseContext.leaguePathPrefix, parseContext.canonicalLeaguePathPrefix)
  ) {
    return null;
  }

  const hash = context._extractMatchKey(absoluteHref) || context._extractMatchKey(pathname);
  if (!hash || seen.has(hash)) {
    return null;
  }

  const scope = anchor.closest(parseContext.eventScopeSelectors.join(', ')) || anchor;
  const { homeTeam, awayTeam } = resolveAnchorTeams(context, anchor, scope, pathname);
  if (!homeTeam || !awayTeam) {
    return null;
  }

  return {
    url: absoluteHref,
    hash,
    homeTeam,
    awayTeam,
    matchDate: null,
    source: parseContext.source
  };
}

function parseCurrentSeasonResultRowsFromHtml(html, options = {}) {
  const rawHtml = String(html || '');
  const document = new JSDOM(rawHtml).window.document;
  const parseContext = buildParseContext(this, document, options);
  const matches = [];
  const seen = new Set();

  appendStructuredMatches(this, rawHtml, matches, seen, parseContext);
  if (parseContext.forceJsonExtract && matches.length > 0) {
    return matches;
  }

  for (const anchor of collectResultAnchors(this, document, options)) {
    const candidate = buildAnchorCandidate(this, anchor, parseContext, seen);
    if (candidate) {
      this._appendCandidateMatches(matches, seen, [candidate], parseContext);
    }
  }

  return matches;
}

function buildStandingsTeamEntry(context, anchor, currentUrl, source) {
  const absoluteHref = context._resolveHref(anchor.getAttribute('href') || anchor.href || '', currentUrl);
  const teamRef = context._extractTeamReference(absoluteHref);
  if (!teamRef) {
    return null;
  }

  const teamName = context._cleanText(
    anchor.textContent
    || anchor.getAttribute('title')
    || anchor.getAttribute('aria-label')
    || teamRef.teamName
  );
  if (!context._looksLikeStandaloneTeamLabel(teamName)) {
    return null;
  }

  return {
    dedupeKey: String(teamRef.teamHash || teamRef.teamUrl || teamName).trim().toLowerCase(),
    value: {
      teamName,
      teamHash: teamRef.teamHash,
      teamUrl: teamRef.teamUrl,
      source
    }
  };
}

function extractTeamsFromStandings(html, options = {}) {
  const document = new JSDOM(String(html || '')).window.document;
  const currentUrl = options.currentUrl || this.baseUrl || options.baseUrlFallback;
  const seen = new Set();
  const teams = [];

  for (const anchor of this._collectStandingsTeamAnchors(document)) {
    const entry = buildStandingsTeamEntry(this, anchor, currentUrl, options.source || 'standings_dom');
    if (!entry?.dedupeKey || seen.has(entry.dedupeKey)) {
      continue;
    }

    seen.add(entry.dedupeKey);
    teams.push(entry.value);
  }

  return teams;
}

function resolveCandidateUrl(context, candidate, options) {
  const resolvedUrl = context._resolveHref(candidate.url || '', options.currentUrl || context.baseUrl || options.baseUrlFallback);
  const pathname = resolvedUrl ? context._getPathname(resolvedUrl) : '';
  if (pathname && !context._isCandidateInScope(pathname, options.leaguePathPrefix, options.canonicalLeaguePathPrefix)) {
    return null;
  }

  return {
    pathname,
    resolvedUrl
  };
}

function resolveCandidateIdentity(context, candidate, resolvedUrl, pathname) {
  return {
    awayTeam: context._cleanText(candidate.awayTeam),
    hash: context._cleanText(candidate.hash || context._extractMatchKey(resolvedUrl || pathname)),
    homeTeam: context._cleanText(candidate.homeTeam)
  };
}

function normalizeCandidate(context, candidate, options) {
  if (!candidate || typeof candidate !== 'object') {
    return null;
  }

  const resolvedCandidateUrl = resolveCandidateUrl(context, candidate, options);
  if (!resolvedCandidateUrl) {
    return null;
  }

  const { pathname, resolvedUrl } = resolvedCandidateUrl;
  const { hash, homeTeam, awayTeam } = resolveCandidateIdentity(context, candidate, resolvedUrl, pathname);
  if (!hash || !homeTeam || !awayTeam) {
    return null;
  }

  return {
    url: resolvedUrl || candidate.url || '',
    hash,
    homeTeam,
    awayTeam,
    matchDate: candidate.matchDate || null,
    source: candidate.source || options.source || 'current_results_dom'
  };
}

function appendCandidateMatches(target, seen, candidates, options = {}) {
  for (const candidate of Array.isArray(candidates) ? candidates : []) {
    const normalized = normalizeCandidate(this, candidate, options);
    if (!normalized || seen.has(normalized.hash)) {
      continue;
    }

    seen.add(normalized.hash);
    target.push(normalized);
  }
}

module.exports = {
  parseCurrentSeasonResultRowsFromHtml,
  extractTeamsFromStandings,
  appendCandidateMatches
};
