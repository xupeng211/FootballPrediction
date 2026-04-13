'use strict';

const { RECON_CONFIG, getReconConfigSection } = require('./ReconServiceConfig');
const { ReconDecryptor } = require('../ReconDecryptor');
const { reconInterceptHandler } = require('./ReconInterceptHandler');
const { reconResponseDecoder } = require('./ReconResponseDecoder');
const { reconMatchExtractor } = require('./ReconMatchExtractor');

const BASE_URL = RECON_CONFIG.oddsportal.base_url;
const EMBEDDED_PLACEHOLDER_STATUS_RE = /^\s*URL:[\s\S]*?\bStatus:\s*(\d{3})\b/i;
const BACKEND_FETCH_FAILED_RE = /backend fetch failed|guru meditation/i;

function compileRegexPatterns(patterns = []) {
  return patterns
    .map((pattern) => {
      if (pattern instanceof RegExp) {
        return pattern;
      }

      const match = String(pattern || '').match(/^\/([\s\S]*)\/([a-z]*)$/i);
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

function detectEmbeddedHttpFailure(bodyText = '') {
  const text = String(bodyText || '');
  if (!text.trim()) {
    return null;
  }

  const placeholderMatch = text.match(EMBEDDED_PLACEHOLDER_STATUS_RE);
  if (placeholderMatch) {
    const statusCode = Number(placeholderMatch[1]) || 503;
    return {
      statusCode,
      error: `EMBEDDED_HTTP_${statusCode}`,
      signal: 'archive_placeholder_status'
    };
  }

  return BACKEND_FETCH_FAILED_RE.test(text)
    ? { statusCode: 503, error: 'EMBEDDED_HTTP_503', signal: 'backend_fetch_failed_page' }
    : null;
}

function createDecryptorFactory(options, runtimeConfig, logger, traceId) {
  return options.decryptorFactory || (() => (
    new ReconDecryptor({
      logger,
      traceId,
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
}

function resolveMonitorPatterns(options, runtimeConfig) {
  return {
    matchApiPatterns: compileRegexPatterns(options.matchApiPatterns || runtimeConfig.match_api_patterns || []),
    scriptWrapperPatterns: compileRegexPatterns(options.scriptWrapperPatterns || runtimeConfig.script_wrapper_patterns || []),
    knownErrorPatterns: compileRegexPatterns(options.knownErrorPatterns || runtimeConfig.known_error_patterns || [])
  };
}

function resolveMonitorThresholds(options, runtimeConfig) {
  return {
    scriptEvalTimeoutMs: Number(options.scriptEvalTimeoutMs ?? runtimeConfig.script_eval_timeout_ms),
    extractMaxDepth: Number(options.extractMaxDepth ?? runtimeConfig.extract_max_depth),
    pageSize: Number(options.pageSize ?? runtimeConfig.page_size),
    fetchTimeoutMs: Number(options.fetchTimeoutMs ?? runtimeConfig.fetch_timeout_ms)
  };
}

function createMonitorState(options = {}) {
  const runtimeConfig = getReconConfigSection(['recon_runtime', 'network_monitor'], {});
  const logger = options.logger || console;
  const traceId = options.traceId || 'trace-unknown';
  const decryptorFactory = createDecryptorFactory(options, runtimeConfig, logger, traceId);

  return {
    logger,
    traceId,
    baseUrl: options.baseUrl || BASE_URL,
    page: options.page || null,
    decryptorFactory,
    decryptor: options.decryptor || decryptorFactory(),
    interceptedData: [],
    apiEndpoints: new Set(),
    stats: options.stats || createDefaultStats(),
    _responseHandler: null,
    _attachedPage: null,
    ...resolveMonitorThresholds(options, runtimeConfig),
    ...resolveMonitorPatterns(options, runtimeConfig)
  };
}

function appendUniqueMatches(matches, seenHashes, pageMatches = []) {
  let newRows = 0;

  for (const match of pageMatches) {
    const hash = match?.hash || '';
    if (!hash || seenHashes.has(hash)) {
      continue;
    }
    seenHashes.add(hash);
    matches.push(match);
    newRows += 1;
  }

  return newRows;
}

function buildHttpFailure(response, page, url) {
  return {
    page,
    url,
    statusCode: Number(response.status) || null,
    error: response.error,
    retryAfterRaw: response.retryAfterRaw || '',
    retryAfterMs: Number(response.retryAfterMs) || 0
  };
}

function resolveParsedPageSummary(parsed, pageMatches = []) {
  const rowCount = Array.isArray(parsed?.d?.rows)
    ? parsed.d.rows.length
    : Array.isArray(parsed?.rows)
      ? parsed.rows.length
      : pageMatches.length;
  const total = Number(parsed?.d?.total) || Number(parsed?.total) || pageMatches.length;

  return { rowCount, total };
}

async function processPaginatedPage(monitor, page, url, options, seenHashes, matches, pageStats) {
  const response = await monitor.fetchText(url, options.timeoutMs);

  if (!response.success) {
    const httpFailure = buildHttpFailure(response, page, url);
    pageStats.push({ page, rows: 0, ...httpFailure });
    return { done: true, httpFailure };
  }

  const embeddedFailure = detectEmbeddedHttpFailure(response.text);
  if (embeddedFailure) {
    const httpFailure = buildHttpFailure({
      ...response,
      status: embeddedFailure.statusCode,
      error: embeddedFailure.error
    }, page, url);
    pageStats.push({ page, rows: 0, bodySignal: embeddedFailure.signal, ...httpFailure });
    return { done: true, httpFailure };
  }

  try {
    const decoded = await monitor.decodeResponsePayload(response.text, url);
    const parsed = decoded?.parsed;
    if (!parsed || typeof parsed !== 'object') {
      pageStats.push({ page, rows: 0, total: 0, source: decoded?.source || 'empty' });
      return { done: true, httpFailure: null };
    }

    const pageMatches = monitor.extractMatchesFromJson(parsed, options.source);
    const { rowCount, total } = resolveParsedPageSummary(parsed, pageMatches);
    const newRows = appendUniqueMatches(matches, seenHashes, pageMatches);

    pageStats.push({
      page,
      rows: rowCount,
      newRows,
      total,
      source: decoded.source
    });

    return {
      done: rowCount === 0 && newRows === 0,
      httpFailure: null,
      total
    };
  } catch (error) {
    pageStats.push({ page, rows: 0, error: `decrypt_failed:${error.message}` });
    return { done: true, httpFailure: null };
  }
}

class ReconNetworkMonitor {
  constructor(options = {}) {
    Object.assign(this, createMonitorState(options));
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
    const base = options.buildBaseUrl(options.apiBaseUrl);
    let httpFailure = null;
    let pageLimit = options.maxPages;

    for (let page = 1; page <= pageLimit; page++) {
      const pageUrl = options.buildPageUrl(base, page);
      const outcome = await processPaginatedPage(
        this,
        page,
        pageUrl,
        options,
        seenHashes,
        matches,
        pageStats
      );

      httpFailure = outcome.httpFailure;
      if (outcome.done) {
        break;
      }
      if (outcome.total > 0) {
        pageLimit = Math.min(pageLimit, Math.ceil(outcome.total / this.pageSize));
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

    return this.page.evaluate(async ({ fetchUrl: inputUrl, fetchTimeout }) => {
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), fetchTimeout);

      try {
        const response = await fetch(inputUrl, {
          credentials: 'include',
          signal: ctrl.signal,
          referrer: window.location?.href || undefined,
          headers: {
            accept: '*/*',
            'x-requested-with': 'XMLHttpRequest'
          }
        });
        const text = await response.text();
        const retryAfterRaw = response.headers.get('retry-after') || '';
        clearTimeout(timer);

        return response.ok
          ? { success: true, status: response.status, text, retryAfterRaw }
          : { success: false, status: response.status, error: `HTTP_${response.status}`, text, retryAfterRaw };
      } catch (error) {
        clearTimeout(timer);
        return { success: false, error: error.message };
      }
    }, {
      fetchUrl,
      fetchTimeout: timeoutMs || this.fetchTimeoutMs
    });
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
