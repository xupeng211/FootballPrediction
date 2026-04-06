'use strict';

const { RECON_CONFIG, getReconConfigSection } = require('./ReconServiceConfig');

const DOM_SCRAPER_CONFIG = getReconConfigSection(['recon_runtime', 'dom_scraper'], {});
const HOME_SELECTORS = DOM_SCRAPER_CONFIG.home_selectors || [];
const AWAY_SELECTORS = DOM_SCRAPER_CONFIG.away_selectors || [];
const PARTICIPANT_SELECTORS = DOM_SCRAPER_CONFIG.participant_selectors || [];
const RESULT_ANCHOR_SELECTORS = DOM_SCRAPER_CONFIG.result_anchor_selectors || [];
const PAGINATION_SELECTORS = DOM_SCRAPER_CONFIG.pagination_selectors || [];
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

const reconDomCollectionFlow = {
  async extractCurrentSeasonResultRows(baseUrl, options = {}) {
    const currentUrl = String(baseUrl || '').trim() || this.baseUrl || RECON_CONFIG.oddsportal.base_url;
    const leaguePathPrefix = this.buildLeaguePathPrefix(baseUrl);

    if (this.page && typeof this.page.content === 'function') {
      try {
        const html = await this.page.content();
        return this.parseCurrentSeasonResultRowsFromHtml(html, {
          currentUrl,
          leaguePathPrefix,
          forceJsonExtract: options.forceJsonExtract === true
        });
      } catch (_error) {
        // content() failure falls back to evaluate-based probing
      }
    }

    if (!this.page || typeof this.page.evaluate !== 'function') {
      return [];
    }

    return this.page.evaluate(({
      baseOrigin,
      pageUrl,
      pageLeaguePathPrefix,
      leaguePathPrefix,
      forceJsonExtract,
      resultAnchorSelectors,
      eventContainerSelectors,
      eventScopeSelectors,
      homeSelectors,
      awaySelectors,
      participantSelectors
    }) => {
      const eventScopeSelector = Array.isArray(eventScopeSelectors)
        ? [...new Set(eventScopeSelectors)].join(', ')
        : 'tr';

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
        .replace(/-\d{4}(?=\/results)/i, '')
        .replace(/\/(results|standings|outrights)(?:\/page\/\d+)?\/?$/i, '/')
        .replace(/\/+$/, '/');
      const seen = new Set();
      const pathPrefix = normalizeLeaguePrefix(pageLeaguePathPrefix || leaguePathPrefix);
      const canonicalPathPrefix = normalizeLeaguePrefix(document.querySelector('link[rel="canonical"]')?.href || '');
      const matches = [];

      const appendCandidate = (candidate) => {
        if (!candidate || typeof candidate !== 'object') {
          return;
        }

        const absoluteHref = resolveHref(candidate.url || '');
        let pathname = '';
        try {
          pathname = absoluteHref ? new URL(absoluteHref).pathname : '';
        } catch (_error) {
          pathname = '';
        }

        const hash = cleanText(candidate.hash || extractMatchKey(pathname));
        const homeTeam = cleanText(candidate.homeTeam);
        const awayTeam = cleanText(candidate.awayTeam);
        if (!hash || !homeTeam || !awayTeam || seen.has(hash)) {
          return;
        }

        seen.add(hash);
        matches.push({
          url: absoluteHref || candidate.url || '',
          hash,
          homeTeam,
          awayTeam,
          matchDate: candidate.matchDate || null,
          source: candidate.source || 'current_results_dom'
        });
      };

      const extractMatchesFromPayload = (payload, source) => {
        const results = [];
        const visit = (value, depth = 0) => {
          if (depth > 10 || value == null) {
            return;
          }

          if (Array.isArray(value)) {
            for (const item of value) {
              visit(item, depth + 1);
            }
            return;
          }

          if (typeof value !== 'object') {
            return;
          }

          const url = value.url || value.href || value.link || '';
          const hash = value.hash || value.eventHash || value.encodeEventId || value.matchId || value.eventId || value.id || '';
          const homeTeam = value['home-name'] || value.homeName || value.home_team || value.home || '';
          const awayTeam = value['away-name'] || value.awayName || value.away_team || value.away || '';
          const timestamp = value['date-start-timestamp'] || value.dateStartTimestamp || value.timestamp || null;

          if (url && hash && homeTeam && awayTeam) {
            const matchDate = Number.isFinite(Number(timestamp))
              ? new Date(Number(timestamp) * 1000).toISOString()
              : null;
            results.push({
              url,
              hash,
              homeTeam,
              awayTeam,
              matchDate,
              source
            });
          }

          for (const nested of Object.values(value)) {
            visit(nested, depth + 1);
          }
        };

        visit(payload, 0);
        return results;
      };

      const nextDataNode = document.querySelector('#__NEXT_DATA__');
      if (nextDataNode?.textContent) {
        try {
          const parsed = JSON.parse(nextDataNode.textContent);
          for (const candidate of extractMatchesFromPayload(parsed, 'current_results_next_data')) {
            appendCandidate(candidate);
          }
        } catch (_error) {}
      }

      for (const script of Array.from(document.scripts || [])) {
        const text = String(script.textContent || '');
        const payloadPattern = /JSON\.parse\("((?:\\.|[^"\\])*)"\)/g;
        let hit;

        while ((hit = payloadPattern.exec(text)) !== null) {
          try {
            const decoded = JSON.parse(`"${hit[1]}"`);
            const parsed = JSON.parse(decoded);
            for (const candidate of extractMatchesFromPayload(parsed, 'current_results_script_json')) {
              appendCandidate(candidate);
            }
          } catch (_error) {
            continue;
          }
        }
      }

      if (forceJsonExtract && matches.length > 0) {
        return matches;
      }

      const extractNamesFromSlug = (pathname) => {
        const cleanPath = String(pathname || '').replace(/\/+$/, '');
        const lastSegment = cleanPath.split('/').filter(Boolean).pop() || '';
        const slugWithHash = /\/match\//i.test(cleanPath)
          ? ''
          : lastSegment.replace(/-[A-Za-z0-9]{8}$/i, '');
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

      const extractTeamsFromText = (value) => {
        const cleanValue = cleanText(value);
        if (!cleanValue) {
          return { homeTeam: '', awayTeam: '' };
        }

        for (const separator of [/\s+vs\.?\s+/i, /\s+-\s+/]) {
          const parts = cleanValue.split(separator).map((item) => cleanText(item)).filter(Boolean);
          if (parts.length === 2) {
            return { homeTeam: parts[0], awayTeam: parts[1] };
          }
        }

        return { homeTeam: '', awayTeam: '' };
      };

      const extractMatchKey = (pathname) => {
        const raw = String(pathname || '').trim();
        if (!raw) {
          return '';
        }

        const fragmentMatch = raw.match(/#([A-Za-z0-9]{8})(?:[/?#]|$)/);
        if (fragmentMatch) {
          return fragmentMatch[1];
        }

        const normalizedPath = raw
          .replace(/^https?:\/\/[^/]+/i, '')
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
      };

      const extractTeamsFromH2hPath = (pathname) => {
        const match = String(pathname || '').match(/\/football\/h2h\/([^/]+)\/([^/]+)\/?$/i);
        if (!match) {
          return { homeTeam: '', awayTeam: '' };
        }

        const decodeTeam = (segment) => String(segment || '')
          .replace(/-[A-Za-z0-9]{8}$/i, '')
          .replace(/-/g, ' ')
          .trim()
          .replace(/\s+/g, ' ');

        return {
          homeTeam: decodeTeam(match[1]),
          awayTeam: decodeTeam(match[2])
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

      const configuredAnchors = Array.from(document.querySelectorAll(resultAnchorSelectors.join(', ')));
      const containerAnchors = Array.from(document.querySelectorAll(eventContainerSelectors.join(', ')))
        .flatMap((container) => Array.from(container.querySelectorAll('a[href]')));
      const documentLinkAnchors = Array.from(document.links || []).filter((anchor) => {
        const href = anchor.getAttribute('href') || anchor.href || '';
        return /\/match\/[^/]+\/?$/i.test(href)
          || /-([A-Za-z0-9]{8})\/?$/i.test(href)
          || /\/football\/h2h\/[^/]+\/[^/]+\/?#?[A-Za-z0-9]*$/i.test(href);
      });
      const probedAnchors = Array.from(document.querySelectorAll('a[href]')).filter((anchor) => {
        const href = anchor.getAttribute('href') || anchor.href || '';
        const text = cleanText(anchor.textContent);
        return /\/match\/[^/]+\/?$/i.test(href)
          || /\/football\/h2h\/[^/]+\/[^/]+\/?#?[A-Za-z0-9]*$/i.test(href)
          || /\bvs\.?\b|-/i.test(text);
      });
      const anchors = [...new Set([
        ...configuredAnchors,
        ...containerAnchors,
        ...documentLinkAnchors,
        ...probedAnchors
      ])];

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

        const isMatchRoute = /\/match\/[^/]+\/?$/i.test(pathname);
        const isH2hRoute = /\/football\/h2h\/[^/]+\/[^/]+\/?$/i.test(pathname);
        const normalizedPath = String(pathname || '')
          .replace(/-\d{4}-\d{4}(?=\/)/i, '')
          .replace(/-\d{4}(?=\/results)/i, '');
        const matchesPrimaryPath = pathPrefix ? normalizedPath.startsWith(pathPrefix) : false;
        const matchesCanonicalPath = canonicalPathPrefix ? normalizedPath.startsWith(canonicalPathPrefix) : false;

        if ((pathPrefix || canonicalPathPrefix) && !isMatchRoute && !isH2hRoute && !matchesPrimaryPath && !matchesCanonicalPath) {
          continue;
        }

        if (/\/(results|standings|outrights)\/?$/i.test(pathname)) {
          continue;
        }

        const hash = extractMatchKey(absoluteHref) || extractMatchKey(pathname);
        if (!hash) {
          continue;
        }
        if (seen.has(hash)) {
          continue;
        }

        const scope = anchor.closest(eventScopeSelector) || anchor;
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
          const parsedH2h = extractTeamsFromH2hPath(pathname);
          homeTeam = homeTeam || parsedH2h.homeTeam;
          awayTeam = awayTeam || parsedH2h.awayTeam;
        }

        if (!homeTeam || !awayTeam) {
          const parsed = extractNamesFromSlug(pathname);
          homeTeam = homeTeam || parsed.homeTeam;
          awayTeam = awayTeam || parsed.awayTeam;
        }

        if (!homeTeam || !awayTeam) {
          const parsed = extractTeamsFromText(anchor.textContent || anchor.getAttribute('title') || '');
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
      forceJsonExtract: options.forceJsonExtract === true,
      resultAnchorSelectors: RESULT_ANCHOR_SELECTORS,
      eventContainerSelectors: EVENT_CONTAINER_SELECTORS,
      eventScopeSelectors: EVENT_SCOPE_SELECTORS,
      homeSelectors: HOME_SELECTORS,
      awaySelectors: AWAY_SELECTORS,
      participantSelectors: PARTICIPANT_SELECTORS
    });
  },

  async extractPaginationMeta(resultsUrl) {
    const currentUrl = this.normalizeResultsUrl(resultsUrl);

    if (this.page && typeof this.page.content === 'function') {
      try {
        const html = await this.page.content();
        return this.extractPaginationMetaFromHtml(html, currentUrl);
      } catch (_error) {
        // content() failure falls back to evaluate-based probing
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
  },

  async extractSeasonNavigationUrls(resultsUrl) {
    const currentUrl = this.normalizeResultsUrl(resultsUrl);

    if (this.page && typeof this.page.content === 'function') {
      try {
        const html = await this.page.content();
        return this.extractSeasonNavigationUrlsFromHtml(html, currentUrl);
      } catch (_error) {
        // content() failure falls back to evaluate-based probing
      }
    }

    if (!this.page || typeof this.page.evaluate !== 'function') {
      return [];
    }

    return this.page.evaluate(({ currentResultsUrl }) => {
      const normalizeResultsUrl = (value) => `${String(value || '').trim().replace(/\/+$/, '')}/`;
      const normalizeLeaguePrefix = (value) => String(value || '')
        .replace(/^https?:\/\/[^/]+/i, '')
        .replace(/-\d{4}-\d{4}(?=\/)/i, '/')
        .replace(/-\d{4}(?=\/results)/i, '/')
        .replace(/\/results(?:\/page\/\d+)?\/?$/i, '/')
        .replace(/\/+$/, '/');
      const resolveHref = (rawHref) => {
        try {
          return normalizeResultsUrl(new URL(rawHref, currentResultsUrl).href);
        } catch (_error) {
          return '';
        }
      };
      const getPathname = (url) => {
        try {
          return new URL(url).pathname;
        } catch (_error) {
          return '';
        }
      };

      const currentPathname = getPathname(currentResultsUrl);
      const leaguePathPrefix = normalizeLeaguePrefix(currentResultsUrl);
      const seasonUrls = new Map();

      for (const anchor of Array.from(document.querySelectorAll('a[href]'))) {
        const absoluteHref = resolveHref(anchor.getAttribute('href') || '');
        if (!absoluteHref) {
          continue;
        }

        const pathname = getPathname(absoluteHref);
        const normalizedPath = normalizeLeaguePrefix(pathname);
        if (!pathname || pathname === currentPathname) {
          continue;
        }
        if (!/\/results(?:\/page\/\d+)?\/?$/i.test(pathname)) {
          continue;
        }
        if (leaguePathPrefix && normalizedPath !== leaguePathPrefix) {
          continue;
        }
        if (!/-\d{4}\/results(?:\/page\/\d+)?\/?$/i.test(pathname)) {
          continue;
        }

        seasonUrls.set(absoluteHref, absoluteHref);
      }

      return [...seasonUrls.values()].sort((left, right) => {
        const extractSeasonYearFromResultsPath = (url) => {
          const match = String(url || '').match(/-(\d{4})\/results(?:\/page\/\d+)?\/?$/i);
          return match ? Number(match[1]) : 0;
        };

        return extractSeasonYearFromResultsPath(right) - extractSeasonYearFromResultsPath(left);
      });
    }, {
      currentResultsUrl: currentUrl
    }).catch(() => []);
  },

  async discoverSeasonResultPages(resultsUrl, options = {}, hooks = {}) {
    const timeoutMs = options.timeoutMs ?? this.timeoutMs;
    const maxPages = Math.max(1, Number(options.maxPages ?? this.maxPages));
    const includeSeasonNavigation = options.includeSeasonNavigation !== false;
    const normalizedResultsUrl = this.normalizeResultsUrl(resultsUrl);

    if (typeof hooks.navigate === 'function') {
      await hooks.navigate(normalizedResultsUrl, { waitUntil: 'domcontentloaded', timeout: timeoutMs });
    }

    await this._wait(hooks.waitForTimeout, this.postNavigationWaitMs);

    const interceptedMatches = typeof hooks.getInterceptedData === 'function'
      ? hooks.getInterceptedData()
      : [];
    const domMatches = await this.extractCurrentSeasonResultRows(normalizedResultsUrl, options);
    const initialMatches = this.mergeInitialMatches(interceptedMatches, domMatches);
    const initialSource = this.describeInitialSource(interceptedMatches, domMatches);

    const paginationMeta = await this.extractPaginationMeta(normalizedResultsUrl);
    const discoveredPageUrls = this.normalizeResultsPageUrls(
      normalizedResultsUrl,
      paginationMeta.pageUrls,
      paginationMeta.totalPages,
      maxPages
    );
    const seasonNavigationUrls = includeSeasonNavigation && initialMatches.length === 0
      ? await this.extractSeasonNavigationUrls(normalizedResultsUrl)
      : [];
    const pageUrls = this.mergeSeasonNavigationUrls(
      discoveredPageUrls,
      seasonNavigationUrls,
      maxPages
    );

    return {
      pageUrls,
      initialMatches,
      initialSource
    };
  },

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
  },

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
  },

  _scoreInitialMatch(match) {
    let score = 0;
    if (match?.matchDate) score += 4;
    if (match?.url) score += 2;
    if (match?.homeTeam) score += 1;
    if (match?.awayTeam) score += 1;
    return score;
  },

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
  },

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
      // DOM wake-up failures must not interrupt the main flow
    }
  },

  async _wait(waitForTimeout, ms) {
    if (typeof waitForTimeout === 'function') {
      await waitForTimeout(ms);
      return;
    }

    if (this.page && typeof this.page.waitForTimeout === 'function') {
      await this.page.waitForTimeout(ms);
    }
  }
};

module.exports = { reconDomCollectionFlow };
