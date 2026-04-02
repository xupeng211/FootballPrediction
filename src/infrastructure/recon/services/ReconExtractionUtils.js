'use strict';

const { JSDOM } = require('jsdom');
const { RECON_CONFIG, getReconConfigSection } = require('./ReconServiceConfig');

const DOM_SCRAPER_CONFIG = getReconConfigSection(['recon_runtime', 'dom_scraper'], {});
const BASE_URL = DOM_SCRAPER_CONFIG.base_url || RECON_CONFIG.oddsportal.base_url;
const HOME_SELECTORS = DOM_SCRAPER_CONFIG.home_selectors || [];
const AWAY_SELECTORS = DOM_SCRAPER_CONFIG.away_selectors || [];
const PARTICIPANT_SELECTORS = DOM_SCRAPER_CONFIG.participant_selectors || [];
const RESULT_ANCHOR_SELECTORS = DOM_SCRAPER_CONFIG.result_anchor_selectors || [];
const PAGINATION_SELECTORS = DOM_SCRAPER_CONFIG.pagination_selectors || [];

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
    const dom = new JSDOM(String(html || ''));
    const document = dom.window.document;
    const currentUrl = options.currentUrl || this.baseUrl;
    const leaguePathPrefix = String(options.leaguePathPrefix || '').trim();
    const canonicalLeaguePathPrefix = this._extractCanonicalLeaguePathPrefix(
      document.querySelector('link[rel="canonical"]')?.href || ''
    );
    const seen = new Set();
    const anchors = Array.from(document.querySelectorAll(RESULT_ANCHOR_SELECTORS.join(', ')));
    const matches = [];

    for (const anchor of anchors) {
      const absoluteHref = this._resolveHref(anchor.getAttribute('href') || '', currentUrl);
      if (!absoluteHref) {
        continue;
      }

      const pathname = this._getPathname(absoluteHref);
      if (!pathname) {
        continue;
      }

      const matchesPrimaryPath = leaguePathPrefix
        ? this._matchesLeaguePath(pathname, leaguePathPrefix)
        : false;
      const matchesCanonicalPath = canonicalLeaguePathPrefix
        ? this._matchesLeaguePath(pathname, canonicalLeaguePathPrefix)
        : false;

      if ((leaguePathPrefix || canonicalLeaguePathPrefix) && !matchesPrimaryPath && !matchesCanonicalPath) {
        continue;
      }

      if (/\/(results|standings|outrights)\/?$/i.test(pathname)) {
        continue;
      }

      const hashMatch = pathname.match(/-([A-Za-z0-9]{8})\/?$/);
      if (!hashMatch) {
        continue;
      }

      const hash = hashMatch[1];
      if (seen.has(hash)) {
        continue;
      }

      const scope = anchor.closest('.eventRow') || anchor;
      let { homeTeam, awayTeam } = this._extractTeamsFromScope(scope);

      if (!homeTeam || !awayTeam) {
        const parsedNames = this._extractNamesFromSlug(pathname);
        homeTeam = homeTeam || parsedNames.homeTeam;
        awayTeam = awayTeam || parsedNames.awayTeam;
      }

      if (!homeTeam || !awayTeam) {
        continue;
      }

      seen.add(hash);
      matches.push({
        url: absoluteHref,
        hash,
        homeTeam,
        awayTeam,
        matchDate: null,
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
    const slugWithHash = lastSegment.replace(/-[A-Za-z0-9]{8}$/i, '');
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
  }
};

module.exports = { reconExtractionUtils };
