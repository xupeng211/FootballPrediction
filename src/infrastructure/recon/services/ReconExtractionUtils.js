'use strict';

const { reconMatchExtractor } = require('./ReconMatchExtractor');
const { RECON_CONFIG, getReconConfigSection } = require('./ReconServiceConfig');
const {
  cleanText,
  getFirstText,
  extractTeamsFromScope,
  extractNamesFromSlug,
  extractTeamsFromH2hPath,
  extractTeamsFromText,
  collectStandingsTeamAnchors,
  looksLikeStandaloneTeamLabel,
  extractTeamReference,
  decodeTeamSlugToName,
  collectEventAnchors,
  probeAnchorPatterns,
  isCandidateInScope
} = require('./ReconExtractionDomHelpers');
const {
  parseCurrentSeasonResultRowsFromHtml,
  extractTeamsFromStandings,
  appendCandidateMatches
} = require('./ReconExtractionResultParser');

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
const EVENT_SCOPE_SELECTORS = [...new Set([...EVENT_CONTAINER_SELECTORS, 'tr'])];

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
    return parseCurrentSeasonResultRowsFromHtml.call(this, html, {
      ...options,
      eventScopeSelectors: EVENT_SCOPE_SELECTORS,
      resultAnchorSelectors: RESULT_ANCHOR_SELECTORS
    });
  },

  extractPaginationMetaFromHtml(html, currentResultsUrl) {
    const document = new (require('jsdom').JSDOM)(String(html || '')).window.document;
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
    return extractTeamsFromStandings.call(this, html, {
      ...options,
      baseUrlFallback: BASE_URL
    });
  },

  extractSeasonNavigationUrlsFromHtml(html, currentResultsUrl) {
    const document = new (require('jsdom').JSDOM)(String(html || '')).window.document;
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
    const expectedPages = Math.min(normalizedMaxPages, Math.max(1, Number(totalPages || 1)));

    const tryAppend = (candidateUrl) => {
      const normalized = this.normalizeResultsUrl(candidateUrl);
      if (!normalized) {
        return;
      }

      if (normalized === normalizedResultsUrl || normalized.startsWith(`${pageBaseUrl}/page/`)) {
        deduped.set(normalized, normalized);
      }
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
    return normalized ? `${normalized.replace(/\/+$/, '')}/` : '';
  },

  extractResultsPageNumber(url) {
    const match = String(url || '').match(/\/page\/(\d+)\/?$/i);
    return match ? Number(match[1]) : 1;
  },

  _extractTeamsFromScope(scope) {
    return extractTeamsFromScope(scope, {
      homeSelectors: HOME_SELECTORS,
      awaySelectors: AWAY_SELECTORS,
      participantSelectors: PARTICIPANT_SELECTORS
    });
  },

  _extractNamesFromSlug: extractNamesFromSlug,
  _extractTeamsFromH2hPath: extractTeamsFromH2hPath,
  _extractTeamsFromText: extractTeamsFromText,
  _getFirstText: getFirstText,
  _collectStandingsTeamAnchors: collectStandingsTeamAnchors,

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

  _cleanText: cleanText,
  _looksLikeStandaloneTeamLabel: looksLikeStandaloneTeamLabel,

  _extractTeamReference(url) {
    return extractTeamReference(url, (value) => this._getPathname(value));
  },

  _decodeTeamSlugToName: decodeTeamSlugToName,

  _appendCandidateMatches(target, seen, candidates, options = {}) {
    return appendCandidateMatches.call(this, target, seen, candidates, {
      ...options,
      baseUrlFallback: BASE_URL
    });
  },

  _extractFromNextData(html) {
    const nextDataMatch = String(html || '').match(/<script[^>]*id=["']__NEXT_DATA__["'][^>]*>([\s\S]*?)<\/script>/i);
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
    return collectEventAnchors(document, EVENT_CONTAINER_SELECTORS);
  },

  _isCandidateInScope(pathname, leaguePathPrefix, canonicalLeaguePathPrefix) {
    return isCandidateInScope(
      pathname,
      leaguePathPrefix,
      canonicalLeaguePathPrefix,
      (value, prefix) => this._matchesLeaguePath(value, prefix)
    );
  },

  _probeAnchorPatterns: probeAnchorPatterns,

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
    return matchRoute ? matchRoute[1] : '';
  }
};

module.exports = { reconExtractionUtils };
