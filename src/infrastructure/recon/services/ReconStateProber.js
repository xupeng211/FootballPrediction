'use strict';

const { JSDOM } = require('jsdom');
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
      return outrightId;
    }

    if (!this.page || typeof this.page.evaluate !== 'function') {
      return '';
    }

    try {
      const pageVarOtCode = await this.page.evaluate(() => {
        const token = window.pageVar?.otCode;
        return typeof token === 'string' ? token.trim() : '';
      });

      return typeof pageVarOtCode === 'string' ? pageVarOtCode.trim() : '';
    } catch (_error) {
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

    return archiveEndpoint.replace('/1//X', `/1/${tournamentToken}/X`);
  }

  async probeCurrentSeasonFromPageState(baseUrl, options = {}, hooks = {}) {
    const maxPages = options.maxPages || this.maxPages;
    const timeoutMs = options.timeoutMs || this.timeoutMs;
    const currentResultsUrl = this.deriveCurrentResultsUrl(baseUrl) || baseUrl;

    await hooks.navigate?.(currentResultsUrl, { waitUntil: 'domcontentloaded', timeout: timeoutMs });
    await this._wait(hooks.waitForTimeout, this.postNavigationWaitMs);

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

    const tournamentApiUrl = hooks.getCurrentTournamentEndpoint?.()
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
