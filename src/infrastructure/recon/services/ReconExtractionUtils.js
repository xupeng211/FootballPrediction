'use strict';

const { JSDOM } = require('jsdom');
const { reconMatchExtractor } = require('./ReconMatchExtractor');
const { RECON_CONFIG, getReconConfigSection } = require('./ReconServiceConfig');

const DOM_SCRAPER_CONFIG = getReconConfigSection(['recon_runtime', 'dom_scraper'], {});
const NETWORK_MONITOR_CONFIG = getReconConfigSection(['recon_runtime', 'network_monitor'], {});
const BASE_URL = DOM_SCRAPER_CONFIG.base_url || RECON_CONFIG.oddsportal.base_url;
const HOME_SELECTORS = DOM_SCRAPER_CONFIG.home_selectors || [];
const AWAY_SELECTORS = DOM_SCRAPER_CONFIG.away_selectors || [];
const PARTICIPANT_SELECTORS = DOM_SCRAPER_CONFIG.participant_selectors || [];
const RESULT_ANCHOR_SELECTORS = DOM_SCRAPER_CONFIG.result_anchor_selectors || [];
const PAGINATION_SELECTORS = DOM_SCRAPER_CONFIG.pagination_selectors || [];
const EMBEDDED_MATCH_EXTRACT_DEPTH = Math.max(1, Number(NETWORK_MONITOR_CONFIG.extract_max_depth || 10));
const EVENT_CONTAINER_SELECTORS = [
  'div[role="row"]',
  '[data-testid="event-name"]',
  '[data-testid="events"]',
  '[data-testid*="event"]',
  '[data-testid*="match"]',
  '[class*="event-row"]',
  '[class*="EventRow"]',
  'div[class*="sportName"]'
];
const EVENT_SCOPE_SELECTORS = [...new Set([
  ...EVENT_CONTAINER_SELECTORS,
  'tr'
])];

const reconExtractionUtils = {
  buildLeaguePathPrefix(baseUrl) {
    try {
      const parsedUrl = new URL(baseUrl);
      return parsedUrl.pathname
        .replace(/-\d{4}-\d{4}\/results(?:\/page\/\d+)?\/?$/i, '/')
        .replace(/\/results(?:\/page\/\d+)?\/?$/i, '/');
    } catch (_error) {
      return String(baseUrl || '')
        .replace(/^https?:\/\/[^/]+/i, '')
        .replace(/-\d{4}-\d{4}\/results(?:\/page\/\d+)?\/?$/i, '/')
        .replace(/\/results(?:\/page\/\d+)?\/?$/i, '/');
    }
  },

  parseCurrentSeasonResultRowsFromHtml(html, options = {}) {
    const rawHtml = String(html || '');
    const dom = new JSDOM(String(html || ''));
    const document = dom.window.document;
    const currentUrl = options.currentUrl || this.baseUrl;
    const leaguePathPrefix = String(options.leaguePathPrefix || '').trim();
    const canonicalLeaguePathPrefix = this._extractCanonicalLeaguePathPrefix(
      document.querySelector('link[rel="canonical"]')?.href || ''
    );
    const forceJsonExtract = options.forceJsonExtract === true;
    const seen = new Set();
    const matches = [];
    this._appendCandidateMatches(matches, seen, this._extractFromNextData(rawHtml), {
      currentUrl,
      leaguePathPrefix,
      canonicalLeaguePathPrefix,
      source: 'current_results_next_data'
    });
    this._appendCandidateMatches(matches, seen, this._extractFromEmbeddedJsonScripts(rawHtml), {
      currentUrl,
      leaguePathPrefix,
      canonicalLeaguePathPrefix,
      source: 'current_results_script_json'
    });

    if (forceJsonExtract && matches.length > 0) {
      return matches;
    }

    const configuredSelector = RESULT_ANCHOR_SELECTORS.filter(Boolean).join(', ');
    const baseAnchors = configuredSelector
      ? Array.from(document.querySelectorAll(configuredSelector))
      : [];
    const fallbackAnchors = this._collectEventAnchors(document);
    const dynamicAnchors = this._probeAnchorPatterns(document);
    const anchors = [...new Set([...baseAnchors, ...fallbackAnchors, ...dynamicAnchors])];

    for (const anchor of anchors) {
      const absoluteHref = this._resolveHref(anchor.getAttribute('href') || '', currentUrl);
      if (!absoluteHref) {
        continue;
      }

      const pathname = this._getPathname(absoluteHref);
      if (!pathname) {
        continue;
      }

      const isMatchRoute = /\/match\/[^/]+\/?$/i.test(pathname);
      const isH2hRoute = /\/football\/h2h\/[^/]+\/[^/]+\/?$/iu.test(pathname);
      const matchesPrimaryPath = leaguePathPrefix
        ? this._matchesLeaguePath(pathname, leaguePathPrefix)
        : false;
      const matchesCanonicalPath = canonicalLeaguePathPrefix
        ? this._matchesLeaguePath(pathname, canonicalLeaguePathPrefix)
        : false;

      if ((leaguePathPrefix || canonicalLeaguePathPrefix) && !isMatchRoute && !isH2hRoute && !matchesPrimaryPath && !matchesCanonicalPath) {
        continue;
      }

      if (/\/(results|standings|outrights)\/?$/i.test(pathname)) {
        continue;
      }

      const hash = this._extractMatchKey(absoluteHref) || this._extractMatchKey(pathname);
      if (!hash) {
        continue;
      }
      if (seen.has(hash)) {
        continue;
      }

      const scope = anchor.closest(EVENT_SCOPE_SELECTORS.join(', ')) || anchor;
      let { homeTeam, awayTeam } = this._extractTeamsFromScope(scope);

      if (!homeTeam || !awayTeam) {
        const parsedH2hNames = this._extractTeamsFromH2hPath(pathname);
        homeTeam = homeTeam || parsedH2hNames.homeTeam;
        awayTeam = awayTeam || parsedH2hNames.awayTeam;
      }

      if (!homeTeam || !awayTeam) {
        const parsedNames = this._extractNamesFromSlug(pathname);
        homeTeam = homeTeam || parsedNames.homeTeam;
        awayTeam = awayTeam || parsedNames.awayTeam;
      }

      if (!homeTeam || !awayTeam) {
        const parsedFromText = this._extractTeamsFromText(anchor.textContent || anchor.getAttribute('title') || '');
        homeTeam = homeTeam || parsedFromText.homeTeam;
        awayTeam = awayTeam || parsedFromText.awayTeam;
      }

      if (!homeTeam || !awayTeam) {
        continue;
      }

      this._appendCandidateMatches(matches, seen, [{
        url: absoluteHref,
        hash,
        homeTeam,
        awayTeam,
        matchDate: null,
        source: options.source || 'current_results_dom'
      }], {
        currentUrl,
        leaguePathPrefix,
        canonicalLeaguePathPrefix,
        source: options.source || 'current_results_dom'
      });
    }

    return matches;
  },

  extractPaginationMetaFromHtml(html, currentResultsUrl) {
    const dom = new JSDOM(String(html || ''));
    const document = dom.window.document;
    const anchors = Array.from(document.querySelectorAll(PAGINATION_SELECTORS.join(', ')));
    const pageUrls = [];
    let totalPages = 1;

    for (const anchor of anchors) {
      const rawHref = anchor.getAttribute('href') || '';
      if (!rawHref) {
        continue;
      }

      const absoluteHref = this._resolveHref(rawHref, currentResultsUrl);
      if (!absoluteHref) {
        continue;
      }

      const label = this._cleanText(anchor.textContent);
      const pageMatch = absoluteHref.match(/\/page\/(\d+)\/?$/i);

      pageUrls.push(absoluteHref);

      if (/^\d+$/.test(label)) {
        totalPages = Math.max(totalPages, Number(label));
      }

      if (pageMatch) {
        totalPages = Math.max(totalPages, Number(pageMatch[1]));
      }
    }

    return { pageUrls, totalPages };
  },

  extractTeamsFromStandings(html, options = {}) {
    const dom = new JSDOM(String(html || ''));
    const document = dom.window.document;
    const currentUrl = options.currentUrl || this.baseUrl || BASE_URL;
    const seen = new Set();
    const teams = [];
    const anchors = this._collectStandingsTeamAnchors(document);

    for (const anchor of anchors) {
      const absoluteHref = this._resolveHref(anchor.getAttribute('href') || anchor.href || '', currentUrl);
      const teamRef = this._extractTeamReference(absoluteHref);

      if (!teamRef) {
        continue;
      }

      const teamName = this._cleanText(
        anchor.textContent
        || anchor.getAttribute('title')
        || anchor.getAttribute('aria-label')
        || teamRef.teamName
      );

      if (!this._looksLikeStandaloneTeamLabel(teamName)) {
        continue;
      }

      const dedupeKey = String(teamRef.teamHash || teamRef.teamUrl || teamName)
        .trim()
        .toLowerCase();
      if (!dedupeKey || seen.has(dedupeKey)) {
        continue;
      }

      seen.add(dedupeKey);
      teams.push({
        teamName,
        teamHash: teamRef.teamHash,
        teamUrl: teamRef.teamUrl,
        source: options.source || 'standings_dom'
      });
    }

    return teams;
  },

  extractSeasonNavigationUrlsFromHtml(html, currentResultsUrl) {
    const dom = new JSDOM(String(html || ''));
    const document = dom.window.document;
    const currentUrl = this.normalizeResultsUrl(currentResultsUrl);
    const leaguePathPrefix = this.buildLeaguePathPrefix(currentUrl);
    const currentPathname = this._getPathname(currentUrl);
    const seasonUrls = new Map();

    for (const anchor of Array.from(document.querySelectorAll('a[href]'))) {
      const absoluteHref = this._resolveHref(anchor.getAttribute('href') || '', currentUrl);
      if (!absoluteHref) {
        continue;
      }

      const normalizedHref = this.normalizeResultsUrl(absoluteHref);
      const pathname = this._getPathname(normalizedHref);
      if (!pathname || pathname === currentPathname) {
        continue;
      }

      if (!/\/results(?:\/page\/\d+)?\/?$/i.test(pathname)) {
        continue;
      }

      if (!leaguePathPrefix || !this._matchesLeaguePath(pathname, leaguePathPrefix)) {
        continue;
      }

      if (!/-\d{4}\/results(?:\/page\/\d+)?\/?$/i.test(pathname)) {
        continue;
      }

      seasonUrls.set(normalizedHref, normalizedHref);
    }

    return [...seasonUrls.values()].sort((left, right) => (
      this._extractSeasonYearFromResultsPath(right) - this._extractSeasonYearFromResultsPath(left)
    ));
  },

  normalizeResultsPageUrls(resultsUrl, discoveredUrls = [], totalPages = 1, maxPages = null) {
    const normalizedResultsUrl = this.normalizeResultsUrl(resultsUrl);
    const pageBaseUrl = normalizedResultsUrl
      .replace(/\/page\/\d+\/?$/i, '')
      .replace(/\/+$/, '');
    const deduped = new Map();
    const normalizedMaxPages = Math.max(1, Number(maxPages ?? this.maxPages));
    const expectedPages = Math.min(
      normalizedMaxPages,
      Math.max(1, Number(totalPages || 1))
    );

    const tryAppend = (candidateUrl) => {
      const normalized = this.normalizeResultsUrl(candidateUrl);
      if (!normalized) {
        return;
      }

      const sameSeries = normalized === normalizedResultsUrl
        || normalized.startsWith(`${pageBaseUrl}/page/`);

      if (!sameSeries) {
        return;
      }

      deduped.set(normalized, normalized);
    };

    tryAppend(normalizedResultsUrl);
    for (const discoveredUrl of discoveredUrls) {
      tryAppend(discoveredUrl);
    }

    for (let page = 2; page <= expectedPages; page++) {
      tryAppend(`${pageBaseUrl}/page/${page}/`);
    }

    return [...deduped.values()].sort((left, right) => (
      this.extractResultsPageNumber(left) - this.extractResultsPageNumber(right)
    ));
  },

  mergeSeasonNavigationUrls(baseUrls = [], seasonUrls = [], maxPages = null) {
    const deduped = new Map();
    const normalizedMaxPages = Math.max(1, Number(maxPages ?? this.maxPages));

    for (const url of Array.isArray(baseUrls) ? baseUrls : []) {
      const normalized = this.normalizeResultsUrl(url);
      if (normalized) {
        deduped.set(normalized, normalized);
      }
    }

    for (const url of Array.isArray(seasonUrls) ? seasonUrls : []) {
      if (deduped.size >= normalizedMaxPages) {
        break;
      }

      const normalized = this.normalizeResultsUrl(url);
      if (normalized && !deduped.has(normalized)) {
        deduped.set(normalized, normalized);
      }
    }

    return [...deduped.values()];
  },

  normalizeResultsUrl(url) {
    const normalized = String(url || '').trim();
    if (!normalized) {
      return '';
    }
    return `${normalized.replace(/\/+$/, '')}/`;
  },

  extractResultsPageNumber(url) {
    const match = String(url || '').match(/\/page\/(\d+)\/?$/i);
    return match ? Number(match[1]) : 1;
  },

  _extractTeamsFromScope(scope) {
    const homeTeam = this._getFirstText(scope, HOME_SELECTORS);
    const awayTeam = this._getFirstText(scope, AWAY_SELECTORS);

    if (homeTeam && awayTeam) {
      return { homeTeam, awayTeam };
    }

    const participantTitles = Array.from(scope.querySelectorAll('[title]'))
      .map((node) => this._cleanText(node.getAttribute('title') || ''))
      .filter(Boolean);
    const participantAlts = Array.from(scope.querySelectorAll('img[alt]'))
      .map((node) => this._cleanText(node.getAttribute('alt') || ''))
      .filter(Boolean);
    const participantTexts = Array.from(scope.querySelectorAll(PARTICIPANT_SELECTORS.join(', ')))
      .map((node) => this._cleanText(node.textContent || ''))
      .filter(Boolean);
    const combinedNames = [...new Set([...participantTitles, ...participantAlts, ...participantTexts])];

    return {
      homeTeam: homeTeam || combinedNames[0] || '',
      awayTeam: awayTeam || combinedNames[1] || ''
    };
  },

  _extractNamesFromSlug(pathname) {
    const cleanPath = String(pathname || '').replace(/\/+$/, '');
    const lastSegment = cleanPath.split('/').filter(Boolean).pop() || '';
    const slugWithHash = lastSegment
      .replace(/-[A-Za-z0-9]{8}$/i, '')
      .replace(/^[A-Za-z0-9-]+$/, (value) => (/\/match\//i.test(cleanPath) ? '' : value));
    const parts = slugWithHash.split('-');

    if (parts.length < 2) {
      return { homeTeam: '', awayTeam: '' };
    }

    const midpoint = Math.ceil(parts.length / 2);
    const toTitle = (value) => value
      .split('-')
      .filter(Boolean)
      .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
      .join(' ');

    return {
      homeTeam: toTitle(parts.slice(0, midpoint).join('-')),
      awayTeam: toTitle(parts.slice(midpoint).join('-'))
    };
  },

  _extractTeamsFromH2hPath(pathname) {
    const match = String(pathname || '').match(/\/football\/h2h\/([^/]+)\/([^/]+)\/?$/iu);
    if (!match) {
      return { homeTeam: '', awayTeam: '' };
    }

    const decodeTeam = (segment) => String(segment || '')
      .replace(/-[A-Za-z0-9]{8}$/u, '')
      .replace(/-/g, ' ')
      .trim()
      .replace(/\s+/g, ' ');

    return {
      homeTeam: decodeTeam(match[1]),
      awayTeam: decodeTeam(match[2])
    };
  },

  _extractTeamsFromText(value) {
    const cleanValue = this._cleanText(value);
    if (!cleanValue) {
      return { homeTeam: '', awayTeam: '' };
    }

    const separators = [/\s+vs\.?\s+/i, /\s+-\s+/];
    for (const separator of separators) {
      const parts = cleanValue.split(separator).map((item) => this._cleanText(item)).filter(Boolean);
      if (parts.length === 2) {
        return {
          homeTeam: parts[0],
          awayTeam: parts[1]
        };
      }
    }

    return { homeTeam: '', awayTeam: '' };
  },

  _getFirstText(scope, selectors) {
    for (const selector of selectors) {
      const node = scope.querySelector(selector);
      const text = this._cleanText(node?.textContent || node?.getAttribute?.('title') || '');
      if (text) {
        return text;
      }
    }

    return '';
  },

  _collectStandingsTeamAnchors(document) {
    if (!document) {
      return [];
    }

    const selectors = [
      'table a[href]',
      '[role="row"] a[href]',
      '[class*="standings"] a[href]',
      '[data-testid*="standings"] a[href]',
      'a[href*="/team/"]',
      'a[href*="/teams/"]'
    ];

    return [...new Set(
      selectors.flatMap((selector) => Array.from(document.querySelectorAll(selector)))
    )];
  },

  _resolveHref(rawHref, baseUrl) {
    try {
      return new URL(rawHref, baseUrl || this.baseUrl || BASE_URL).href;
    } catch (_error) {
      return '';
    }
  },

  _getPathname(url) {
    try {
      return new URL(url).pathname;
    } catch (_error) {
      return '';
    }
  },

  _cleanText(value) {
    return String(value || '').replace(/\s+/g, ' ').trim();
  },

  _looksLikeStandaloneTeamLabel(value) {
    const label = this._cleanText(value);
    if (!label) {
      return false;
    }

    if (!/[a-z\u00c0-\u024f]/i.test(label)) {
      return false;
    }

    if (/\bvs\.?\b/i.test(label)) {
      return false;
    }

    if (/\d+\s*[-:]\s*\d+/.test(label)) {
      return false;
    }

    return !/\b(standings?|results?|table|outrights?)\b/i.test(label);
  },

  _extractTeamReference(url) {
    const pathname = this._getPathname(url);
    if (!pathname) {
      return null;
    }

    if (/\/football\/h2h\/|\/match\//i.test(pathname)) {
      return null;
    }

    if (/\/(results|standings|outrights)(?:\/page\/\d+)?\/?$/i.test(pathname)) {
      return null;
    }

    const segments = pathname.split('/').filter(Boolean);
    if (segments.length === 0) {
      return null;
    }

    const hasExplicitTeamPrefix = segments.some((segment) => /^(team|teams)$/i.test(segment));
    if (
      !hasExplicitTeamPrefix
      && /^football$/i.test(segments[0] || '')
      && segments.length >= 4
      && /-\d{4}(?:-\d{4})?$/i.test(segments[2] || '')
    ) {
      return null;
    }

    const lastSegment = segments[segments.length - 1] || '';
    const match = lastSegment.match(/^(.*)-([A-Za-z0-9]{6,12})$/);
    if (!match) {
      return null;
    }

    const teamSlug = match[1];
    const teamHash = match[2];
    const teamName = this._decodeTeamSlugToName(teamSlug);
    if (!teamName) {
      return null;
    }

    return {
      teamName,
      teamHash,
      teamUrl: url
    };
  },

  _decodeTeamSlugToName(teamSlug) {
    const parts = String(teamSlug || '')
      .split('-')
      .map((part) => this._cleanText(part))
      .filter(Boolean);

    if (parts.length === 0) {
      return '';
    }

    return parts
      .map((part) => {
        if (/^[a-z]{1,3}$/i.test(part)) {
          return part.toUpperCase();
        }

        return part.charAt(0).toUpperCase() + part.slice(1);
      })
      .join(' ');
  },

  _appendCandidateMatches(target, seen, candidates, options = {}) {
    for (const candidate of Array.isArray(candidates) ? candidates : []) {
      if (!candidate || typeof candidate !== 'object') {
        continue;
      }

      const resolvedUrl = this._resolveHref(candidate.url || '', options.currentUrl || this.baseUrl || BASE_URL);
      const pathname = resolvedUrl ? this._getPathname(resolvedUrl) : '';

      if (pathname && !this._isCandidateInScope(pathname, options.leaguePathPrefix, options.canonicalLeaguePathPrefix)) {
        continue;
      }

      const hash = this._cleanText(candidate.hash || this._extractMatchKey(resolvedUrl || pathname));
      const homeTeam = this._cleanText(candidate.homeTeam);
      const awayTeam = this._cleanText(candidate.awayTeam);

      if (!hash || !homeTeam || !awayTeam || seen.has(hash)) {
        continue;
      }

      seen.add(hash);
      target.push({
        url: resolvedUrl || candidate.url || '',
        hash,
        homeTeam,
        awayTeam,
        matchDate: candidate.matchDate || null,
        source: candidate.source || options.source || 'current_results_dom'
      });
    }
  },

  _extractFromNextData(html) {
    const nextDataMatch = String(html || '').match(
      /<script[^>]*id=["']__NEXT_DATA__["'][^>]*>([\s\S]*?)<\/script>/i
    );

    if (!nextDataMatch) {
      return [];
    }

    try {
      const parsed = JSON.parse(nextDataMatch[1]);
      return this._extractMatchesFromJsonPayload(parsed, 'current_results_next_data');
    } catch (_error) {
      return [];
    }
  },

  _extractFromEmbeddedJsonScripts(html) {
    const matches = [];
    const payloadPattern = /JSON\.parse\("((?:\\.|[^"\\])*)"\)/g;
    let hit;

    while ((hit = payloadPattern.exec(String(html || ''))) !== null) {
      try {
        const decoded = JSON.parse(`"${hit[1]}"`);
        const parsed = JSON.parse(decoded);
        matches.push(...this._extractMatchesFromJsonPayload(parsed, 'current_results_script_json'));
      } catch (_error) {
        continue;
      }
    }

    return matches;
  },

  _extractMatchesFromJsonPayload(payload, source) {
    return reconMatchExtractor.extractMatchesFromJson.call({
      baseUrl: this.baseUrl || BASE_URL,
      extractMaxDepth: EMBEDDED_MATCH_EXTRACT_DEPTH,
      extractStructuredRowMatches: reconMatchExtractor.extractStructuredRowMatches,
      isMatchObject: reconMatchExtractor.isMatchObject,
      normalizeMatchObject: reconMatchExtractor.normalizeMatchObject
    }, payload, source);
  },

  _collectEventAnchors(document) {
    if (!document) {
      return [];
    }

    const containers = Array.from(document.querySelectorAll(EVENT_CONTAINER_SELECTORS.join(', ')))
      .filter(Boolean);
    const anchors = [];
    for (const container of containers) {
      anchors.push(...Array.from(container.querySelectorAll('a[href]')));
    }

    for (const anchor of Array.from(document.links || [])) {
      const href = anchor.getAttribute('href') || anchor.href || '';
      if (
        /\/match\/[^/]+\/?$/i.test(href)
        || /-([A-Za-z0-9]{8})\/?$/i.test(href)
        || /\/football\/h2h\/[^/]+\/[^/]+\/?#?[A-Za-z0-9]*$/iu.test(href)
      ) {
        anchors.push(anchor);
      }
    }

    return anchors;
  },

  _isCandidateInScope(pathname, leaguePathPrefix, canonicalLeaguePathPrefix) {
    const isMatchRoute = /\/match\/[^/]+\/?$/i.test(String(pathname || ''));
    const isH2hRoute = /\/football\/h2h\/[^/]+\/[^/]+\/?$/iu.test(String(pathname || ''));
    const matchesPrimaryPath = leaguePathPrefix
      ? this._matchesLeaguePath(pathname, leaguePathPrefix)
      : false;
    const matchesCanonicalPath = canonicalLeaguePathPrefix
      ? this._matchesLeaguePath(pathname, canonicalLeaguePathPrefix)
      : false;

    if (!leaguePathPrefix && !canonicalLeaguePathPrefix) {
      return true;
    }

    return isMatchRoute || isH2hRoute || matchesPrimaryPath || matchesCanonicalPath;
  },

  _probeAnchorPatterns(document) {
    if (!document) {
      return [];
    }

    const anchors = [];
    const candidates = Array.from(document.querySelectorAll('a[href]'));
    for (const anchor of candidates) {
      const text = this._cleanText(anchor.textContent);
      const href = anchor.getAttribute('href') || anchor.href || '';
      if (/\/match\/[^/]+\/?$/i.test(href)) {
        anchors.push(anchor);
        continue;
      }
      if (/\/football\/h2h\/[^/]+\/[^/]+\/?#?[A-Za-z0-9]*$/iu.test(href)) {
        anchors.push(anchor);
        continue;
      }
      if (!text) {
        continue;
      }
      if (/\bvs\.?\b|-/i.test(text)) {
        anchors.push(anchor);
      }
    }
    return anchors;
  },

  _matchesLeaguePath(pathname, leaguePathPrefix) {
    const normalizedPath = String(pathname || '')
      .replace(/-\d{4}-\d{4}(?=\/)/i, '')
      .replace(/-\d{4}(?=\/results)/i, '');
    const normalizedPrefix = this._normalizeLeaguePathPrefix(leaguePathPrefix);
    return normalizedPrefix ? normalizedPath.startsWith(normalizedPrefix) : true;
  },

  _extractCanonicalLeaguePathPrefix(canonicalUrl) {
    return this._normalizeLeaguePathPrefix(canonicalUrl);
  },

  _normalizeLeaguePathPrefix(value) {
    return String(value || '')
      .replace(/^https?:\/\/[^/]+/i, '')
      .replace(/-\d{4}-\d{4}(?=\/)/i, '')
      .replace(/-\d{4}(?=\/results)/i, '')
      .replace(/\/(results|standings|outrights)(?:\/page\/\d+)?\/?$/i, '/')
      .replace(/\/+$/, '/');
  },

  _extractSeasonYearFromResultsPath(url) {
    const match = String(url || '').match(/-(\d{4})\/results(?:\/page\/\d+)?\/?$/i);
    return match ? Number(match[1]) : 0;
  },

  _extractMatchKey(pathname) {
    const raw = String(pathname || '').trim();
    if (!raw) {
      return '';
    }

    const fragmentMatch = raw.match(/#([A-Za-z0-9]{8})(?:[/?#]|$)/u);
    if (fragmentMatch) {
      return fragmentMatch[1];
    }

    const normalizedPath = raw
      .replace(/^https?:\/\/[^/]+/iu, '')
      .split('#')[0]
      .split('?')[0]
      .replace(/\/+$/, '');
    const hashMatch = normalizedPath.match(/-([A-Za-z0-9]{8})$/);
    if (hashMatch) {
      return hashMatch[1];
    }

    const matchRoute = normalizedPath.match(/\/match\/([^/?#]+)$/i);
    if (matchRoute) {
      return matchRoute[1];
    }

    return '';
  }
};

module.exports = { reconExtractionUtils };
