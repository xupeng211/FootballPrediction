'use strict';

const vm = require('node:vm');

const { RECON_CONFIG, getReconConfigSection } = require('./ReconServiceConfig');
const { ReconDecryptor } = require('../ReconDecryptor');

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
      new ReconDecryptor({ logger: this.logger, traceId: this.traceId })
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
  }

  setPage(page) {
    this.page = page;
  }

  reset() {
    this.interceptedData = [];
    this.apiEndpoints = new Set();
    this.decryptor = this.decryptorFactory();
  }

  attach(page) {
    this.page = page || this.page;
    if (!this.page || typeof this.page.on !== 'function') {
      return;
    }

    this._responseHandler = async (response) => this.handleResponse(response);
    this.page.on('response', this._responseHandler);
  }

  async handleResponse(response) {
    try {
      const url = response.url();
      if (!this.isPotentialMatchApi(url)) {
        return;
      }

      this.stats.requestsTotal++;
      this.apiEndpoints.add(url);

      let body;
      try {
        body = await response.text();
      } catch (error) {
        this.logger.warn('[ReconNetworkMonitor] 读取响应体失败', {
          traceId: this.traceId,
          url: url.substring(0, 60),
          error: error.message
        });
        this.stats.requestsFailed++;
        return;
      }

      let data;
      try {
        data = await this.parseApiResponse(body, url);
      } catch (error) {
        this.logger.warn('[ReconNetworkMonitor] 解析响应失败', {
          traceId: this.traceId,
          url: url.substring(0, 60),
          error: error.message
        });
        this.stats.requestsFailed++;
        return;
      }

      if (data && data.length > 0) {
        this.interceptedData.push(...data);
        this.stats.requestsSuccess++;
        this.logger.info('[ReconNetworkMonitor] 数据拦截成功', {
          traceId: this.traceId,
          url: url.substring(0, 60),
          count: data.length
        });
      }
    } catch (error) {
      this.logger.error('[ReconNetworkMonitor] 响应处理异常', {
        traceId: this.traceId,
        error: error.message,
        stack: error.stack?.substring(0, 200)
      });
      this.stats.requestsFailed++;
    }
  }

  isPotentialMatchApi(url) {
    return this.matchApiPatterns.some((pattern) => pattern.test(url));
  }

  async parseApiResponse(body, url = '') {
    if (!body || typeof body !== 'string') {
      this.logger.debug('[ReconNetworkMonitor] 响应体为空或非字符串', { traceId: this.traceId });
      return [];
    }

    const trimmed = body.trim();
    if (!trimmed) {
      this.logger.debug('[ReconNetworkMonitor] 响应体为空', { traceId: this.traceId });
      return [];
    }

    try {
      const decoded = await this.decodeResponsePayload(trimmed, url);
      if (!decoded?.parsed || typeof decoded.parsed !== 'object') {
        return [];
      }

      const matches = this.extractMatchesFromJson(decoded.parsed, 'api_intercept');
      this.logger.debug('[ReconNetworkMonitor] 响应解析成功', {
        traceId: this.traceId,
        source: decoded.source,
        matchCount: matches.length
      });
      return matches;
    } catch (error) {
      if (!url.includes('/ajax-')) {
        this.logger.debug('[ReconNetworkMonitor] 非 ajax 响应解析失败', {
          traceId: this.traceId,
          error: error.message
        });
        return [];
      }

      this.stats.decryptedFailed++;
      this.logger.warn('[ReconNetworkMonitor] 解密失败，返回空数组', {
        traceId: this.traceId,
        url: url.substring(0, 60),
        error: error.message
      });
      return [];
    }
  }

  async decodeResponsePayload(body, url = '') {
    const trimmed = typeof body === 'string' ? body.trim() : '';
    if (!trimmed) {
      return { parsed: null, source: 'empty' };
    }

    const directJson = this.safeJsonParse(trimmed);
    if (directJson !== null) {
      return { parsed: directJson, source: 'json' };
    }

    const wrappedPayload = this.parseScriptWrappedPayload(trimmed);
    if (wrappedPayload.matched) {
      return {
        parsed: wrappedPayload.parsed,
        source: wrappedPayload.source
      };
    }

    if (this.isKnownErrorPayload(trimmed)) {
      return { parsed: null, source: 'error_payload' };
    }

    if (!url.includes('/ajax-')) {
      return { parsed: null, source: 'unsupported' };
    }

    this.logger.debug('[ReconNetworkMonitor] 检测到加密响应，尝试解密', { traceId: this.traceId });

    let decrypted;
    try {
      if (!this.decryptor.getAlgorithmVersion()) {
        await this.decryptor.extractDecryptor(this.page, trimmed);
      }
      decrypted = await this.decryptor.decrypt(trimmed);
    } catch (_initialError) {
      await this.decryptor.extractDecryptor(this.page, trimmed);
      decrypted = await this.decryptor.decrypt(trimmed);
    }

    const parsed = typeof decrypted === 'string' ? this.safeJsonParse(decrypted.trim()) : decrypted;
    if (!parsed || typeof parsed !== 'object') {
      throw new Error('decrypt_result_not_json');
    }

    this.stats.decryptedSuccess++;
    return { parsed, source: 'decrypted' };
  }

  safeJsonParse(text) {
    try {
      return JSON.parse(text);
    } catch {
      return null;
    }
  }

  parseScriptWrappedPayload(text) {
    const body = String(text || '').trim();
    if (!body) {
      return { matched: false, parsed: null, source: 'script_wrapper' };
    }

    const looksLikeWrapper = this.scriptWrapperPatterns.some((pattern) => pattern.test(body));
    if (!looksLikeWrapper) {
      return { matched: false, parsed: null, source: 'script_wrapper' };
    }

    const candidates = [];
    const jsonLiteralPattern = /JSON\.parse\((['"])((?:\\.|(?!\1)[\s\S])*)\1\)/g;

    for (const match of body.matchAll(jsonLiteralPattern)) {
      const quote = match[1];
      const literal = match[2];
      if (!literal) {
        continue;
      }

      try {
        const decodedText = vm.runInNewContext(`${quote}${literal}${quote}`, Object.create(null), {
          timeout: this.scriptEvalTimeoutMs
        });
        const parsed = JSON.parse(decodedText);
        if (parsed && typeof parsed === 'object') {
          candidates.push(parsed);
        }
      } catch (_error) {
        // 当前片段无法反序列化则继续
      }
    }

    if (candidates.length === 0) {
      return { matched: true, parsed: {}, source: 'script_wrapper_empty' };
    }

    const payloadWithMatches = candidates.find((candidate) => (
      this.extractMatchesFromJson(candidate, 'script_probe').length > 0
    ));

    return {
      matched: true,
      parsed: payloadWithMatches || this.mergeScriptPayloads(candidates),
      source: 'script_wrapper'
    };
  }

  mergeScriptPayloads(candidates) {
    const merged = {};

    for (const candidate of candidates) {
      if (!candidate || typeof candidate !== 'object' || Array.isArray(candidate)) {
        continue;
      }

      Object.assign(merged, candidate);
    }

    return Object.keys(merged).length > 0 ? merged : candidates[0];
  }

  isKnownErrorPayload(text) {
    const trimmed = String(text || '').trim();
    if (!trimmed) {
      return true;
    }

    return this.knownErrorPatterns.some((pattern) => pattern.test(trimmed));
  }

  extractMatchesFromJson(json, source = 'api_intercept') {
    const matches = [];
    const seen = new Set();
    if (!json || typeof json !== 'object') {
      return matches;
    }

    const pushMatch = (candidate) => {
      if (!candidate) {
        return;
      }

      const dedupeKey = candidate.hash || candidate.url || `${candidate.homeTeam}|${candidate.awayTeam}|${candidate.matchDate || ''}`;
      if (!dedupeKey || seen.has(dedupeKey)) {
        return;
      }

      seen.add(dedupeKey);
      matches.push(candidate);
    };

    for (const rowMatch of this.extractStructuredRowMatches(json, source)) {
      pushMatch(rowMatch);
    }

    const extract = (obj, depth = 0) => {
      if (depth > this.extractMaxDepth) {
        return;
      }

      if (Array.isArray(obj)) {
        obj.forEach((item) => {
          if (this.isMatchObject(item)) {
            const match = this.normalizeMatchObject(item, source);
            pushMatch(match);
          } else if (typeof item === 'object') {
            extract(item, depth + 1);
          }
        });
      } else {
        Object.values(obj).forEach((value) => {
          if (typeof value === 'object' && value !== null) {
            extract(value, depth + 1);
          }
        });
      }
    };

    extract(json);
    return matches;
  }

  extractStructuredRowMatches(json, source = 'api_intercept') {
    const rowSets = [];

    if (Array.isArray(json?.d?.rows)) {
      rowSets.push(json.d.rows);
    }

    if (Array.isArray(json?.rows)) {
      rowSets.push(json.rows);
    }

    return rowSets
      .flat()
      .map((row) => this.normalizeMatchObject(row, source))
      .filter(Boolean);
  }

  isMatchObject(obj) {
    if (!obj || typeof obj !== 'object') {
      return false;
    }

    const indicators = [
      'homeTeam', 'awayTeam', 'home', 'away', 'home-name', 'away-name',
      'homeName', 'awayName', 'matchId', 'eventId', 'encodeEventId', 'hash', 'id'
    ];
    const keys = Object.keys(obj).map((key) => key.toLowerCase());
    return indicators.filter((indicator) => (
      keys.some((key) => key.includes(indicator.toLowerCase()))
    )).length >= 2;
  }

  normalizeMatchObject(obj, source = 'api_intercept') {
    try {
      let homeTeam = '';
      let awayTeam = '';

      if (Array.isArray(obj.participants) && obj.participants.length >= 2) {
        const home = obj.participants.find((participant) => participant?.side === 'home' || participant?.isHome === true)
          || obj.participants[0];
        const away = obj.participants.find((participant) => participant?.side === 'away' || participant?.isHome === false)
          || obj.participants[1];
        homeTeam = home?.name || home?.title || '';
        awayTeam = away?.name || away?.title || '';
      } else {
        homeTeam = obj.homeTeam || obj.home || obj.home_team || obj.team1 || obj.homeName || obj['home-name'] || '';
        awayTeam = obj.awayTeam || obj.away || obj.away_team || obj.team2 || obj.awayName || obj['away-name'] || '';
      }

      if (typeof homeTeam === 'object') {
        homeTeam = homeTeam.name || homeTeam.title || '';
      }
      if (typeof awayTeam === 'object') {
        awayTeam = awayTeam.name || awayTeam.title || '';
      }

      const hash = obj.hash || obj.eventHash || obj.encodeEventId || obj.id || obj.matchId || obj.eventId || '';
      const slug = obj.slug || obj.eventSlug || '';
      const countrySlug = obj.countrySlug || obj.country || '';
      const leagueSlug = obj.leagueSlug || obj.competitionSlug || '';

      let url = obj.url || obj.link || '';
      if (url && url.startsWith('/')) {
        url = `${this.baseUrl}${url}`;
      }
      if (!url && hash) {
        url = `${this.baseUrl}/football/${countrySlug}/${leagueSlug}/${slug}-${hash}/`;
      }

      if (!homeTeam || !awayTeam || !hash) {
        return null;
      }

      return {
        url,
        hash: hash.toString(),
        slug,
        homeTeam,
        awayTeam,
        matchDate: obj.matchDate || obj.match_date || (
          obj['date-start-timestamp']
            ? new Date(Number(obj['date-start-timestamp']) * 1000).toISOString()
            : null
        ),
        source
      };
    } catch {
      return null;
    }
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
    let pageLimit = options.maxPages;
    const base = options.buildBaseUrl(options.apiBaseUrl);

    for (let page = 1; page <= pageLimit; page++) {
      const url = options.buildPageUrl(base, page);

      try {
        const response = await this.fetchText(url, options.timeoutMs);

        if (!response.success) {
          pageStats.push({ page, rows: 0, error: response.error });
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
      pageStats
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
        clearTimeout(timer);
        return { success: true, text: await response.text() };
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

module.exports = {
  ReconNetworkMonitor,
  createDefaultStats
};
