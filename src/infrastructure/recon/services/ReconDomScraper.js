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

class ReconDomScraper {
  constructor(options = {}) {
    this.logger = options.logger || console;
    this.traceId = options.traceId || 'trace-unknown';
    this.baseUrl = options.baseUrl || BASE_URL;
    this.page = options.page || null;
    this.scrollAttempts = options.scrollAttempts || DOM_SCRAPER_CONFIG.scroll_attempts;
    this.scrollDelayMs = options.scrollDelayMs || DOM_SCRAPER_CONFIG.scroll_delay_ms;
    this.timeoutMs = Number(options.timeoutMs ?? DOM_SCRAPER_CONFIG.timeout_ms);
    this.maxPages = Number(options.maxPages ?? DOM_SCRAPER_CONFIG.max_pages);
    this.postNavigationWaitMs = Number(options.postNavigationWaitMs ?? DOM_SCRAPER_CONFIG.post_navigation_wait_ms);
    this.minScrollRounds = Number(options.minScrollRounds ?? DOM_SCRAPER_CONFIG.min_scroll_rounds);
    this.stagnantRoundsThreshold = Number(options.stagnantRoundsThreshold ?? DOM_SCRAPER_CONFIG.stagnant_rounds_threshold);
    this.pageScrollFloorPx = Number(options.pageScrollFloorPx ?? DOM_SCRAPER_CONFIG.page_scroll_floor_px);
    this.pageScrollStepBasePx = Number(options.pageScrollStepBasePx ?? DOM_SCRAPER_CONFIG.page_scroll_step_base_px);
    this.pageScrollWaitCapMs = Number(options.pageScrollWaitCapMs ?? DOM_SCRAPER_CONFIG.page_scroll_wait_cap_ms);
    this.pageScrollWaitMs = Number(options.pageScrollWaitMs ?? DOM_SCRAPER_CONFIG.page_scroll_wait_ms);
    this.wakeMouseX = Number(options.wakeMouseX ?? DOM_SCRAPER_CONFIG.wake_mouse_x);
    this.wakeMouseY = Number(options.wakeMouseY ?? DOM_SCRAPER_CONFIG.wake_mouse_y);
    this.wakeScrollStepPx = Number(options.wakeScrollStepPx ?? DOM_SCRAPER_CONFIG.wake_scroll_step_px);
  }

  setPage(page) {
    this.page = page;
  }

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
  }

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
  }

  extractPaginationMetaFromHtml(html, currentResultsUrl) {
    const dom = new JSDOM(String(html || ''));
    const document = dom.window.document;
    const anchors = Array.from(
      document.querySelectorAll(PAGINATION_SELECTORS.join(', '))
    );
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
  }

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
  }

  normalizeResultsUrl(url) {
    const normalized = String(url || '').trim();
    if (!normalized) {
      return '';
    }

    return `${normalized.replace(/\/+$/, '')}/`;
  }

  extractResultsPageNumber(url) {
    const match = String(url || '').match(/\/page\/(\d+)\/?$/i);
    return match ? Number(match[1]) : 1;
  }

  async extractCurrentSeasonResultRows(baseUrl) {
    const currentUrl = String(baseUrl || '').trim() || this.baseUrl;
    const leaguePathPrefix = this.buildLeaguePathPrefix(baseUrl);

    if (this.page && typeof this.page.content === 'function') {
      try {
        const html = await this.page.content();
        return this.parseCurrentSeasonResultRowsFromHtml(html, {
          currentUrl,
          leaguePathPrefix
        });
      } catch (_error) {
        // content() 失败时回退到 evaluate 探测
      }
    }

    if (!this.page || typeof this.page.evaluate !== 'function') {
      return [];
    }

    return this.page.evaluate(({ baseOrigin, pageUrl, pageLeaguePathPrefix, resultAnchorSelectors, homeSelectors, awaySelectors, participantSelectors }) => {
      const resolveHref = (rawHref) => {
        try {
          return new URL(rawHref, pageUrl || baseOrigin).href;
        } catch (_error) {
          return '';
        }
      };

      const cleanText = (value) => String(value || '').replace(/\s+/g, ' ').trim();
      const normalizeLeaguePrefix = (value) => String(value || '')
        .replace(/^https?:\/\/[^/]+/i, '')
        .replace(/-\d{4}-\d{4}(?=\/)/i, '')
        .replace(/\/(results|standings|outrights)(?:\/page\/\d+)?\/?$/i, '/')
        .replace(/\/+$/, '/');
      const seen = new Set();
      const pathPrefix = normalizeLeaguePrefix(pageLeaguePathPrefix);
      const canonicalPathPrefix = normalizeLeaguePrefix(
        document.querySelector('link[rel="canonical"]')?.href || ''
      );
      const matches = [];

      const extractNamesFromSlug = (pathname) => {
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
      };

      const getFirstText = (scope, selectors) => {
        for (const selector of selectors) {
          const node = scope.querySelector(selector);
          const text = cleanText(node?.textContent || node?.getAttribute?.('title') || '');
          if (text) {
            return text;
          }
        }
        return '';
      };

      const anchors = Array.from(document.querySelectorAll(resultAnchorSelectors.join(', ')));

      for (const anchor of anchors) {
        const absoluteHref = resolveHref(anchor.getAttribute('href') || '');
        if (!absoluteHref) {
          continue;
        }

        let pathname = '';
        try {
          pathname = new URL(absoluteHref).pathname;
        } catch (_error) {
          continue;
        }

        const normalizedPath = String(pathname || '').replace(/-\d{4}-\d{4}(?=\/)/i, '');
        const matchesPrimaryPath = pathPrefix ? normalizedPath.startsWith(pathPrefix) : false;
        const matchesCanonicalPath = canonicalPathPrefix ? normalizedPath.startsWith(canonicalPathPrefix) : false;

        if ((pathPrefix || canonicalPathPrefix) && !matchesPrimaryPath && !matchesCanonicalPath) {
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
        let homeTeam = getFirstText(scope, homeSelectors);
        let awayTeam = getFirstText(scope, awaySelectors);

        if (!homeTeam || !awayTeam) {
          const participantTitles = Array.from(scope.querySelectorAll('[title]'))
            .map((node) => cleanText(node.getAttribute('title') || ''))
            .filter(Boolean);
          const participantAlts = Array.from(scope.querySelectorAll('img[alt]'))
            .map((node) => cleanText(node.getAttribute('alt') || ''))
            .filter(Boolean);
          const participantTexts = Array.from(scope.querySelectorAll(participantSelectors.join(', ')))
            .map((node) => cleanText(node.textContent || ''))
            .filter(Boolean);
          const combined = [...new Set([...participantTitles, ...participantAlts, ...participantTexts])];
          homeTeam = homeTeam || combined[0] || '';
          awayTeam = awayTeam || combined[1] || '';
        }

        if (!homeTeam || !awayTeam) {
          const parsed = extractNamesFromSlug(pathname);
          homeTeam = homeTeam || parsed.homeTeam;
          awayTeam = awayTeam || parsed.awayTeam;
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
          source: 'current_results_dom'
        });
      }

      return matches;
    }, {
      baseOrigin: this.baseUrl,
      pageUrl: currentUrl,
      pageLeaguePathPrefix: leaguePathPrefix,
      leaguePathPrefix,
      resultAnchorSelectors: RESULT_ANCHOR_SELECTORS,
      homeSelectors: HOME_SELECTORS,
      awaySelectors: AWAY_SELECTORS,
      participantSelectors: PARTICIPANT_SELECTORS
    });
  }

  async extractPaginationMeta(resultsUrl) {
    const currentUrl = this.normalizeResultsUrl(resultsUrl);

    if (this.page && typeof this.page.content === 'function') {
      try {
        const html = await this.page.content();
        return this.extractPaginationMetaFromHtml(html, currentUrl);
      } catch (_error) {
        // content() 失败时回退到 evaluate 探测
      }
    }

    if (!this.page || typeof this.page.evaluate !== 'function') {
      return { pageUrls: [], totalPages: 1 };
    }

    return this.page.evaluate(({ currentResultsUrl, paginationSelectors }) => {
      const pageUrls = [];
      let totalPages = 1;

      const anchors = Array.from(document.querySelectorAll(paginationSelectors.join(', ')));
      for (const anchor of anchors) {
        const rawHref = anchor.getAttribute('href') || '';
        if (!rawHref) {
          continue;
        }

        const absoluteHref = new URL(rawHref, currentResultsUrl).href;
        const label = (anchor.textContent || '').trim();
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
    }, {
      currentResultsUrl: currentUrl,
      paginationSelectors: PAGINATION_SELECTORS
    }).catch(() => ({ pageUrls: [], totalPages: 1 }));
  }

  async discoverSeasonResultPages(resultsUrl, options = {}, hooks = {}) {
    const timeoutMs = options.timeoutMs ?? this.timeoutMs;
    const maxPages = Math.max(1, Number(options.maxPages ?? this.maxPages));
    const normalizedResultsUrl = this.normalizeResultsUrl(resultsUrl);

    if (typeof hooks.navigate === 'function') {
      await hooks.navigate(normalizedResultsUrl, { waitUntil: 'networkidle', timeout: timeoutMs });
    }

    await this._wait(hooks.waitForTimeout, this.postNavigationWaitMs);

    const interceptedMatches = typeof hooks.getInterceptedData === 'function'
      ? hooks.getInterceptedData()
      : [];
    const domMatches = await this.extractCurrentSeasonResultRows(normalizedResultsUrl);
    const initialMatches = this.mergeInitialMatches(interceptedMatches, domMatches);
    const initialSource = this.describeInitialSource(interceptedMatches, domMatches);

    const paginationMeta = await this.extractPaginationMeta(normalizedResultsUrl);
    const pageUrls = this.normalizeResultsPageUrls(
      normalizedResultsUrl,
      paginationMeta.pageUrls,
      paginationMeta.totalPages,
      maxPages
    );

    return {
      pageUrls,
      initialMatches,
      initialSource
    };
  }

  mergeInitialMatches(interceptedMatches = [], domMatches = []) {
    const merged = new Map();
    const append = (matches = []) => {
      for (const match of Array.isArray(matches) ? matches : []) {
        const key = match?.hash || match?.url;
        if (!key) {
          continue;
        }

        const existing = merged.get(key);
        if (!existing || this._scoreInitialMatch(match) > this._scoreInitialMatch(existing)) {
          merged.set(key, match);
        }
      }
    };

    append(interceptedMatches);
    append(domMatches);

    return [...merged.values()];
  }

  describeInitialSource(interceptedMatches = [], domMatches = []) {
    const hasIntercepted = Array.isArray(interceptedMatches) && interceptedMatches.length > 0;
    const hasDom = Array.isArray(domMatches) && domMatches.length > 0;

    if (hasIntercepted && hasDom) {
      return 'page_intercept+page_dom';
    }

    if (hasIntercepted) {
      return 'page_intercept';
    }

    if (hasDom) {
      return 'page_dom';
    }

    return 'page_empty';
  }

  _scoreInitialMatch(match) {
    let score = 0;
    if (match?.matchDate) score += 4;
    if (match?.url) score += 2;
    if (match?.homeTeam) score += 1;
    if (match?.awayTeam) score += 1;
    return score;
  }

  async collectCurrentSeasonResults(currentResultsUrl, options = {}) {
    const maxScrollRounds = Math.max(
      this.minScrollRounds,
      Number(options.maxScrollRounds ?? this.scrollAttempts)
    );

    let bestMatches = [];
    let stagnantRounds = 0;

    for (let round = 0; round < maxScrollRounds; round++) {
      await this.wakeCurrentSeasonDom(round);
      const candidates = await this.extractCurrentSeasonResultRows(currentResultsUrl);

      if (candidates.length > bestMatches.length) {
        bestMatches = candidates;
        stagnantRounds = 0;
      } else {
        stagnantRounds++;
      }

      if (round >= 2 && stagnantRounds >= this.stagnantRoundsThreshold) {
        break;
      }

      if (round < maxScrollRounds - 1 && this.page) {
        await this.page.evaluate((step) => {
          window.scrollBy(0, step);
        }, Math.max(this.pageScrollFloorPx, (round + 1) * this.pageScrollStepBasePx));
        await this._wait(
          null,
          Math.min(this.pageScrollWaitCapMs, options.scrollDelayMs ?? this.scrollDelayMs ?? this.pageScrollWaitMs)
        );
      }
    }

    return {
      matches: bestMatches,
      pagesScanned: 1,
      totalCandidates: bestMatches.length,
      pageStats: [{
        page: 1,
        rows: bestMatches.length,
        newRows: bestMatches.length,
        total: bestMatches.length
      }]
    };
  }

  async wakeCurrentSeasonDom(round = 0) {
    if (!this.page) {
      return;
    }

    try {
      if (this.page.mouse && typeof this.page.mouse.click === 'function') {
        await this.page.mouse.click(this.wakeMouseX, this.wakeMouseY).catch(() => {});
      }

      await this.page.evaluate(({ iteration, wakeMouseX, wakeMouseY, wakeScrollStepPx }) => {
        document.body?.dispatchEvent(new MouseEvent('click', {
          bubbles: true,
          cancelable: true,
          clientX: wakeMouseX,
          clientY: wakeMouseY
        }));

        const depth = Math.min(
          document.body?.scrollHeight || window.innerHeight,
          window.innerHeight + ((iteration + 1) * wakeScrollStepPx)
        );

        window.scrollTo({ top: depth, behavior: 'auto' });
      }, {
        iteration: round,
        wakeMouseX: this.wakeMouseX,
        wakeMouseY: this.wakeMouseY,
        wakeScrollStepPx: this.wakeScrollStepPx
      });
    } catch (_error) {
      // DOM 唤醒失败不应中断主流程
    }
  }

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
  }

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
  }

  _getFirstText(scope, selectors) {
    for (const selector of selectors) {
      const node = scope.querySelector(selector);
      const text = this._cleanText(node?.textContent || node?.getAttribute?.('title') || '');
      if (text) {
        return text;
      }
    }

    return '';
  }

  _resolveHref(rawHref, baseUrl) {
    try {
      return new URL(rawHref, baseUrl || this.baseUrl).href;
    } catch (_error) {
      return '';
    }
  }

  _getPathname(url) {
    try {
      return new URL(url).pathname;
    } catch (_error) {
      return '';
    }
  }

  _cleanText(value) {
    return String(value || '').replace(/\s+/g, ' ').trim();
  }

  _matchesLeaguePath(pathname, leaguePathPrefix) {
    const normalizedPath = String(pathname || '').replace(/-\d{4}-\d{4}(?=\/)/i, '');
    const normalizedPrefix = this._normalizeLeaguePathPrefix(leaguePathPrefix);
    return normalizedPrefix ? normalizedPath.startsWith(normalizedPrefix) : true;
  }

  _extractCanonicalLeaguePathPrefix(canonicalUrl) {
    return this._normalizeLeaguePathPrefix(canonicalUrl);
  }

  _normalizeLeaguePathPrefix(value) {
    return String(value || '')
      .replace(/^https?:\/\/[^/]+/i, '')
      .replace(/-\d{4}-\d{4}(?=\/)/i, '')
      .replace(/\/(results|standings|outrights)(?:\/page\/\d+)?\/?$/i, '/')
      .replace(/\/+$/, '/');
  }

  async _wait(waitForTimeout, ms) {
    if (typeof waitForTimeout === 'function') {
      await waitForTimeout(ms);
      return;
    }

    if (this.page && typeof this.page.waitForTimeout === 'function') {
      await this.page.waitForTimeout(ms);
    }
  }
}

module.exports = {
  ReconDomScraper
};
