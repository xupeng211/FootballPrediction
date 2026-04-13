/* eslint-disable complexity, max-lines */
'use strict';

const { JSDOM } = require('jsdom');
const { ReconEndpointHelper } = require('./ReconEndpointHelper');
const { getReconConfigSection } = require('./ReconServiceConfig');

class ReconStateProber {
  constructor(options = {}) {
    const runtimeConfig = getReconConfigSection(['recon_runtime', 'state_prober'], {});

    this.logger = options.logger || console;
    this.traceId = options.traceId || 'trace-unknown';
    this.page = options.page || null;
    this.timeoutMs = Number(options.timeoutMs ?? runtimeConfig.timeout_ms);
    this.maxPages = Number(options.maxPages ?? runtimeConfig.max_pages);
    this.postNavigationWaitMs = Number(options.postNavigationWaitMs ?? runtimeConfig.post_navigation_wait_ms);
  }

  setPage(page) {
    this.page = page;
  }

  deriveLeaguePageUrl(baseUrl) {
    const normalized = String(baseUrl || '').trim();
    if (!normalized) {
      return '';
    }

    const derived = normalized
      .replace(
        /(\/football\/[^/]+\/)([^/]+)-\d{4}-\d{4}\/results(?:\/page\/\d+)?\/?$/i,
        '$1$2/'
      )
      .replace(
        /(\/football\/[^/]+\/[^/]+)\/results(?:\/page\/\d+)?\/?$/i,
        '$1/'
      );

    return derived === normalized ? '' : derived;
  }

  deriveCurrentResultsUrl(baseUrl) {
    const normalized = String(baseUrl || '').trim();
    if (!normalized) {
      return '';
    }

    const derived = normalized.replace(
      /(\/football\/[^/]+\/)([^/]+)-\d{4}-\d{4}\/results(?:\/page\/\d+)?\/?$/i,
      '$1$2/results/'
    );

    return derived === normalized ? normalized : derived;
  }

  extractPageOutrightsMetaFromHtml(html) {
    const dom = new JSDOM(String(html || ''));
    const scripts = Array.from(dom.window.document.scripts).map((script) => script.textContent || '');

    for (const text of scripts) {
      const match = text.match(/pageOutrightsVar\s*=\s*'([^']+)'/);
      if (!match) {
        continue;
      }

      try {
        return JSON.parse(match[1]);
      } catch (_error) {
        return null;
      }
    }

    return null;
  }

  async extractPageOutrightsMeta() {
    if (this.page && typeof this.page.content === 'function') {
      try {
        const html = await this.page.content();
        return this.extractPageOutrightsMetaFromHtml(html);
      } catch (_error) {
        // content() 失败时回退到 evaluate
      }
    }

    if (!this.page || typeof this.page.evaluate !== 'function') {
      return null;
    }

    try {
      return await this.page.evaluate(() => {
        const scripts = Array.from(document.scripts).map((script) => script.textContent || '');
        const hit = scripts.find((text) => text.includes('pageOutrightsVar')) || '';
        const match = hit.match(/pageOutrightsVar\s*=\s*'([^']+)'/);
        if (!match) {
          return null;
        }

        try {
          return JSON.parse(match[1]);
        } catch (_error) {
          return null;
        }
      });
    } catch (_error) {
      return null;
    }
  }

  async extractTournamentToken() {
    const meta = await this.extractPageOutrightsMeta();
    const outrightId = typeof meta?.id === 'string' ? meta.id.trim() : '';
    if (outrightId) {
      this.logger.debug('recon_tournament_token_resolved', {
        traceId: this.traceId,
        source: 'pageOutrightsVar.id'
      });
      return outrightId;
    }

    this.logger.debug('recon_tournament_token_page_outrights_missing', {
      traceId: this.traceId,
      hasMeta: Boolean(meta),
      metaIdType: typeof meta?.id
    });

    if (!this.page || typeof this.page.evaluate !== 'function') {
      this.logger.warn('recon_tournament_token_page_unavailable', {
        traceId: this.traceId
      });
      return '';
    }

    try {
      const pageVarOtCode = await this.page.evaluate(() => {
        const token = window.pageVar?.otCode;
        return typeof token === 'string' ? token.trim() : '';
      });

      const normalizedToken = typeof pageVarOtCode === 'string' ? pageVarOtCode.trim() : '';
      if (!normalizedToken) {
        this.logger.warn('recon_tournament_token_otcode_missing', {
          traceId: this.traceId
        });
        return '';
      }

      this.logger.debug('recon_tournament_token_resolved', {
        traceId: this.traceId,
        source: 'pageVar.otCode'
      });
      return normalizedToken;
    } catch (_error) {
      this.logger.warn('recon_tournament_token_otcode_eval_failed', {
        traceId: this.traceId
      });
      return '';
    }
  }

  async resolveCurrentSeasonArchiveEndpoint(apiEndpoints = [], options = {}) {
    const scoreArchiveUrl = options.scoreArchiveUrl || (() => 0);
    const archiveEndpoint = [...apiEndpoints]
      .filter((url) => /ajax-sport-country-tournament-archive_/i.test(url))
      .sort((a, b) => scoreArchiveUrl(b) - scoreArchiveUrl(a))[0];

    if (!archiveEndpoint) {
      return null;
    }

    if (!/\/1\/\/X/i.test(archiveEndpoint)) {
      return archiveEndpoint;
    }

    const tournamentToken = await this.extractTournamentToken();
    if (!tournamentToken) {
      return null;
    }

    return ReconEndpointHelper.repairArchiveEndpointWithTournamentToken(
      archiveEndpoint,
      tournamentToken
    );
  }

  async probeCurrentSeasonFromPageState(baseUrl, options = {}, hooks = {}) {
    const maxPages = options.maxPages || this.maxPages;
    const timeoutMs = options.timeoutMs || this.timeoutMs;
    const currentResultsUrl = this.deriveCurrentResultsUrl(baseUrl) || baseUrl;

    await hooks.navigate?.(currentResultsUrl, { waitUntil: 'domcontentloaded', timeout: timeoutMs });
    await this._wait(hooks.waitForTimeout, this.postNavigationWaitMs);

    const currentIntercepted = await this._awaitInterceptedData(hooks);
    if (Array.isArray(currentIntercepted) && currentIntercepted.length > 0) {
      return this._buildInterceptResult(currentIntercepted, currentResultsUrl, 'CURRENT_RESULTS_INTERCEPT');
    }

    const repairedArchiveUrl = await this.resolveCurrentSeasonArchiveEndpoint(
      hooks.getApiEndpoints?.() || [],
      { scoreArchiveUrl: hooks.scoreArchiveUrl }
    );
    const derivedTournamentUrl = repairedArchiveUrl
      ? hooks.buildCurrentTournamentUrlFromArchive?.(repairedArchiveUrl)
      : null;

    if (repairedArchiveUrl) {
      const archiveResult = await hooks.fetchArchive?.(repairedArchiveUrl, maxPages, timeoutMs);
      if (Array.isArray(archiveResult?.matches) && archiveResult.matches.length > 0) {
        return {
          ...archiveResult,
          sourceState: 'CURRENT_RESULTS_ARCHIVE'
        };
      }
    }

    if (derivedTournamentUrl) {
      const tournamentResult = await hooks.fetchCurrentTournament?.(derivedTournamentUrl, maxPages, timeoutMs);
      if (Array.isArray(tournamentResult?.matches) && tournamentResult.matches.length > 0) {
        return {
          ...tournamentResult,
          sourceState: 'CURRENT_RESULTS_TOURNAMENT'
        };
      }
    }

    const domResult = await hooks.collectCurrentSeasonResultsDom?.(currentResultsUrl, options);

    if (Array.isArray(domResult?.matches) && domResult.matches.length > 0) {
      return {
        ...domResult,
        sourceState: 'CURRENT_RESULTS_DOM'
      };
    }

    const leagueUrl = this.deriveLeaguePageUrl(baseUrl);
    if (!leagueUrl) {
      this.logger.warn('protocol_current_season_invalid_base', { baseUrl });
      return this._emptyResult();
    }

    await hooks.navigate?.(leagueUrl, { waitUntil: 'domcontentloaded', timeout: timeoutMs });
    await this._wait(hooks.waitForTimeout, this.postNavigationWaitMs);

    const leagueIntercepted = await this._awaitInterceptedData(hooks);
    if (Array.isArray(leagueIntercepted) && leagueIntercepted.length > 0) {
      return this._buildInterceptResult(leagueIntercepted, leagueUrl, 'CURRENT_TOURNAMENT_INTERCEPT');
    }

    const tournamentApiUrl = await hooks.getCurrentTournamentEndpoint?.()
      || derivedTournamentUrl
      || hooks.buildCurrentTournamentUrlFromArchive?.(
        await this.resolveCurrentSeasonArchiveEndpoint(
          hooks.getApiEndpoints?.() || [],
          { scoreArchiveUrl: hooks.scoreArchiveUrl }
        )
      );
    if (!tournamentApiUrl) {
      this.logger.warn('protocol_current_season_no_api', { leagueUrl });
      return this._emptyResult();
    }

    const result = await hooks.fetchCurrentTournament?.(tournamentApiUrl, maxPages, timeoutMs);
    return {
      ...result,
      sourceState: Array.isArray(result?.matches) && result.matches.length > 0
        ? 'CURRENT_TOURNAMENT'
        : 'SOURCE_EMPTY'
    };
  }

  _buildInterceptResult(matches, url, sourceState) {
    const safeMatches = Array.isArray(matches) ? matches : [];
    return {
      matches: safeMatches,
      pagesScanned: 1,
      totalCandidates: safeMatches.length,
      pageStats: [{
        page: 1,
        url,
        rows: safeMatches.length,
        newRows: safeMatches.length,
        total: safeMatches.length,
        source: sourceState
      }],
      sourceState
    };
  }

  async _awaitInterceptedData(hooks = {}, maxWaitMs = 15000) {
    const read = () => {
      const hits = hooks.getInterceptedData?.() || [];
      return Array.isArray(hits) ? hits : [];
    };

    let hits = read();
    const deadline = Date.now() + Math.max(0, Number(maxWaitMs) || 0);
    while (hits.length === 0 && Date.now() < deadline) {
      await this._wait(hooks.waitForTimeout, Math.min(1000, Math.max(0, deadline - Date.now())));
      hits = read();
    }

    return hits;
  }

  _emptyResult() {
    return {
      matches: [],
      pagesScanned: 0,
      totalCandidates: 0,
      pageStats: [],
      sourceState: 'SOURCE_EMPTY'
    };
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
  ReconStateProber
};
