'use strict';

const { RECON_CONFIG, getReconConfigSection } = require('./ReconServiceConfig');
const { ReconDecryptor } = require('../ReconDecryptor');
const { reconInterceptHandler } = require('./ReconInterceptHandler');
const { reconResponseDecoder } = require('./ReconResponseDecoder');
const { reconMatchExtractor } = require('./ReconMatchExtractor');

const BASE_URL = RECON_CONFIG.oddsportal.base_url;

function compileRegexPatterns(patterns = []) {
  return patterns
    .map((pattern) => {
      if (pattern instanceof RegExp) {
        return pattern;
      }

      const raw = String(pattern || '');
      const match = raw.match(/^\/([\s\S]*)\/([a-z]*)$/i);
      if (!match) {
        return null;
      }

      try {
        return new RegExp(match[1], match[2]);
      } catch {
        return null;
      }
    })
    .filter(Boolean);
}

function createDefaultStats() {
  return {
    requestsTotal: 0,
    requestsSuccess: 0,
    requestsFailed: 0,
    decryptedSuccess: 0,
    decryptedFailed: 0
  };
}

class ReconNetworkMonitor {
  constructor(options = {}) {
    const runtimeConfig = getReconConfigSection(['recon_runtime', 'network_monitor'], {});

    this.logger = options.logger || console;
    this.traceId = options.traceId || 'trace-unknown';
    this.baseUrl = options.baseUrl || BASE_URL;
    this.page = options.page || null;
    this.decryptorFactory = options.decryptorFactory || (() => (
      new ReconDecryptor({
        logger: this.logger,
        traceId: this.traceId,
        allowBestEffortCandidate: true,
        sampleCrossValidateCount: Number(
          options.decryptorSampleCrossValidateCount
          ?? runtimeConfig.decryptor_sample_cross_validate_count
          ?? 3
        ),
        maxCachedSamples: Number(
          options.decryptorMaxCachedSamples
          ?? runtimeConfig.decryptor_max_cached_samples
          ?? 8
        ),
        readinessTimeoutMs: Number(
          options.decryptorReadinessTimeoutMs
          ?? runtimeConfig.decryptor_readiness_timeout_ms
          ?? 12000
        ),
        readinessPollMs: Number(
          options.decryptorReadinessPollMs
          ?? runtimeConfig.decryptor_readiness_poll_ms
          ?? 250
        )
      })
    ));
    this.decryptor = options.decryptor || this.decryptorFactory();
    this.interceptedData = [];
    this.apiEndpoints = new Set();
    this.stats = options.stats || createDefaultStats();
    this._responseHandler = null;
    this.scriptEvalTimeoutMs = Number(options.scriptEvalTimeoutMs ?? runtimeConfig.script_eval_timeout_ms);
    this.extractMaxDepth = Number(options.extractMaxDepth ?? runtimeConfig.extract_max_depth);
    this.pageSize = Number(options.pageSize ?? runtimeConfig.page_size);
    this.fetchTimeoutMs = Number(options.fetchTimeoutMs ?? runtimeConfig.fetch_timeout_ms);
    this.matchApiPatterns = compileRegexPatterns(options.matchApiPatterns || runtimeConfig.match_api_patterns || []);
    this.scriptWrapperPatterns = compileRegexPatterns(options.scriptWrapperPatterns || runtimeConfig.script_wrapper_patterns || []);
    this.knownErrorPatterns = compileRegexPatterns(options.knownErrorPatterns || runtimeConfig.known_error_patterns || []);
    this._attachedPage = null;
  }

  setPage(page) {
    this.page = page;
  }

  reset() {
    this.interceptedData = [];
    this.apiEndpoints = new Set();
    this.decryptor = this.decryptorFactory();
  }

  async fetchArchivePages(apiBaseUrl, maxPages, timeoutMs) {
    return this._fetchPaginatedPages({
      apiBaseUrl,
      maxPages,
      timeoutMs,
      source: 'archive_api',
      buildBaseUrl: (url) => url.split('?')[0].replace(/\/page\/\d+\/?$/, '').replace(/\/+$/, ''),
      buildPageUrl: (base, page) => (
        page === 1
          ? `${base}/?_=${Date.now()}`
          : `${base}/page/${page}/?_=${Date.now()}`
      )
    });
  }

  async fetchCurrentTournamentPages(apiBaseUrl, maxPages, timeoutMs) {
    return this._fetchPaginatedPages({
      apiBaseUrl,
      maxPages,
      timeoutMs,
      source: 'current_tournament_api',
      buildBaseUrl: (url) => url.split('?')[0].replace(/\/\d+\/?$/, '').replace(/\/+$/, ''),
      buildPageUrl: (base, page) => `${base}/${page}/?_=${Date.now()}`
    });
  }

  async _fetchPaginatedPages(options) {
    const seenHashes = new Set();
    const matches = [];
    const pageStats = [];
    let httpFailure = null;
    let pageLimit = options.maxPages;
    const base = options.buildBaseUrl(options.apiBaseUrl);

    for (let page = 1; page <= pageLimit; page++) {
      const url = options.buildPageUrl(base, page);

      try {
        const response = await this.fetchText(url, options.timeoutMs);

        if (!response.success) {
          httpFailure = {
            page,
            url,
            statusCode: Number(response.status) || null,
            error: response.error,
            retryAfterRaw: response.retryAfterRaw || '',
            retryAfterMs: Number(response.retryAfterMs) || 0
          };
          pageStats.push({ page, rows: 0, ...httpFailure });
          break;
        }

        try {
          const decoded = await this.decodeResponsePayload(response.text, url);
          const parsed = decoded?.parsed;

          if (!parsed || typeof parsed !== 'object') {
            pageStats.push({ page, rows: 0, total: 0, source: decoded?.source || 'empty' });
            break;
          }

          const pageMatches = this.extractMatchesFromJson(parsed, options.source);
          const rowCount = Array.isArray(parsed?.d?.rows)
            ? parsed.d.rows.length
            : Array.isArray(parsed?.rows)
              ? parsed.rows.length
              : pageMatches.length;
          const total = Number(parsed?.d?.total) || Number(parsed?.total) || pageMatches.length;

          let newRows = 0;
          for (const match of pageMatches) {
            const hash = match?.hash || '';
            if (!hash || seenHashes.has(hash)) {
              continue;
            }
            seenHashes.add(hash);
            newRows++;
            matches.push(match);
          }

          pageStats.push({
            page,
            rows: rowCount,
            newRows,
            total,
            source: decoded.source
          });

          if (rowCount === 0 && newRows === 0) {
            break;
          }

          if (total > 0) {
            pageLimit = Math.min(pageLimit, Math.ceil(total / this.pageSize));
          }
        } catch (error) {
          pageStats.push({ page, rows: 0, error: `decrypt_failed:${error.message}` });
          break;
        }
      } catch (error) {
        pageStats.push({ page, rows: 0, error: error.message });
        break;
      }
    }

    return {
      matches,
      pagesScanned: pageStats.length,
      totalCandidates: matches.length,
      pageStats,
      httpFailure
    };
  }

  async fetchText(fetchUrl, timeoutMs) {
    if (!this.page || typeof this.page.evaluate !== 'function') {
      throw new Error('page_evaluate_unavailable');
    }

    const effectiveTimeoutMs = timeoutMs || this.fetchTimeoutMs;

    return this.page.evaluate(async ({ fetchUrl: inputUrl, fetchTimeout }) => {
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), fetchTimeout);
      try {
        const response = await fetch(inputUrl, { credentials: 'include', signal: ctrl.signal });
        const text = await response.text();
        const retryAfterRaw = response.headers.get('retry-after') || '';
        clearTimeout(timer);
        if (!response.ok) {
          return {
            success: false,
            status: response.status,
            error: `HTTP_${response.status}`,
            text,
            retryAfterRaw
          };
        }
        return {
          success: true,
          status: response.status,
          text,
          retryAfterRaw
        };
      } catch (error) {
        clearTimeout(timer);
        return { success: false, error: error.message };
      }
    }, { fetchUrl, fetchTimeout: effectiveTimeoutMs });
  }

  getInterceptedData() {
    const seen = new Set();
    return this.interceptedData.filter((item) => {
      const key = item.hash || item.url;
      if (!key || seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    });
  }
}

Object.assign(
  ReconNetworkMonitor.prototype,
  reconInterceptHandler,
  reconResponseDecoder,
  reconMatchExtractor
);

module.exports = {
  ReconNetworkMonitor,
  createDefaultStats
};
