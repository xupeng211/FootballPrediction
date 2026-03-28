'use strict';

const { ReconCircuitBreaker } = require('./ReconResilience');
const { ReconBrowserContext } = require('./services/ReconBrowserContext');
const { ReconDomScraper } = require('./services/ReconDomScraper');
const { ReconNetworkMonitor, createDefaultStats } = require('./services/ReconNetworkMonitor');
const { ReconStateProber } = require('./services/ReconStateProber');
const { RECON_CONFIG, getReconConfigSection } = require('./services/ReconServiceConfig');

const BASE_URL = RECON_CONFIG.oddsportal.base_url;

function generateTraceId() {
  return `trace-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

class ReconNavigator {
  constructor(options = {}) {
    const navigatorConfig = getReconConfigSection(['recon_runtime', 'navigator'], {});

    this.logger = options.logger || console;
    this.proxy = options.proxy;
    this.headless = options.headless !== false;
    this.scrollAttempts = options.scrollAttempts || navigatorConfig.scroll_attempts;
    this.scrollDelayMs = options.scrollDelayMs || navigatorConfig.scroll_delay_ms;
    this.launchTimeoutMs = Number(options.launchTimeoutMs ?? navigatorConfig.launch_timeout_ms);
    this.navigationTimeoutMs = Number(options.navigationTimeoutMs ?? navigatorConfig.navigation_timeout_ms);
    this.warmupDelayMs = Number(options.warmupDelayMs ?? navigatorConfig.warmup_delay_ms);
    this.scrollIterations = Number(options.scrollIterations ?? navigatorConfig.scroll_iterations);
    this.scrollStepPx = Number(options.scrollStepPx ?? navigatorConfig.scroll_step_px);
    this.navigateScrollDelayMs = Number(options.navigateScrollDelayMs ?? navigatorConfig.navigate_scroll_delay_ms);
    this.archiveMaxPages = Number(options.archiveMaxPages ?? navigatorConfig.archive_max_pages);
    this.archiveTimeoutMs = Number(options.archiveTimeoutMs ?? navigatorConfig.archive_timeout_ms);
    this.postApiDiscoveryWaitMs = Number(options.postApiDiscoveryWaitMs ?? navigatorConfig.post_api_discovery_wait_ms);
    this.pageRevisitWaitMs = Number(options.pageRevisitWaitMs ?? navigatorConfig.page_revisit_wait_ms);

    // V11.0: TraceID 机制 - 每笔收割请求唯一编号
    this.traceId = options.traceId || generateTraceId();
    this.sessionStartTime = Date.now();

    this.circuitBreaker = new ReconCircuitBreaker({
      failureThreshold: navigatorConfig.circuit_breaker?.failure_threshold,
      resetTimeout: navigatorConfig.circuit_breaker?.reset_timeout_ms
    });

    this.browserContext = new ReconBrowserContext({
      logger: this.logger,
      traceId: this.traceId,
      headless: this.headless,
      proxy: this.proxy
    });
    this.stats = createDefaultStats();
    this.networkMonitor = new ReconNetworkMonitor({
      logger: this.logger,
      traceId: this.traceId,
      baseUrl: BASE_URL,
      stats: this.stats
    });
    this.domScraper = new ReconDomScraper({
      logger: this.logger,
      traceId: this.traceId,
      baseUrl: BASE_URL,
      scrollAttempts: this.scrollAttempts,
      scrollDelayMs: this.scrollDelayMs
    });
    this.stateProber = new ReconStateProber({
      logger: this.logger,
      traceId: this.traceId
    });
    this.isClosed = false;
    this.lastLaunchOptions = {};
    this._launching = null;
    this._healing = null;

    this.logger.info('[ReconNavigator] 实例创建', { traceId: this.traceId, headless: this.headless });
  }

  get browser() {
    return this.browserContext.browser;
  }

  set browser(value) {
    this.browserContext.browser = value;
  }

  get context() {
    return this.browserContext.context;
  }

  set context(value) {
    this.browserContext.context = value;
  }

  get page() {
    return this.browserContext.page;
  }

  set page(value) {
    this.browserContext.page = value;
    this.networkMonitor.setPage(value);
    this.domScraper.setPage(value);
    this.stateProber.setPage(value);
  }

  get interceptedData() {
    return this.networkMonitor.interceptedData;
  }

  set interceptedData(value) {
    this.networkMonitor.interceptedData = Array.isArray(value) ? value : [];
  }

  get apiEndpoints() {
    return this.networkMonitor.apiEndpoints;
  }

  set apiEndpoints(value) {
    this.networkMonitor.apiEndpoints = value instanceof Set
      ? value
      : new Set(Array.isArray(value) ? value : []);
  }

  get decryptor() {
    return this.networkMonitor.decryptor;
  }

  set decryptor(value) {
    this.networkMonitor.decryptor = value || this.networkMonitor.decryptorFactory();
  }

  getTraceId() {
    return this.traceId;
  }

  getSessionDuration() {
    return Date.now() - this.sessionStartTime;
  }

  getStats() {
    return {
      ...this.stats,
      traceId: this.traceId,
      sessionDurationMs: this.getSessionDuration()
    };
  }

  async launch(options = {}) {
    if (this.isHealthy()) {
      return this.page;
    }

    if (this._launching) {
      return this._launching;
    }

    this._launching = this.circuitBreaker.execute(async () => {
      const timeout = options.timeout || this.launchTimeoutMs;
      this.lastLaunchOptions = { ...options, timeout };

      this.logger.info('[ReconNavigator] 启动浏览器', { traceId: this.traceId, headless: this.headless });

      try {
        return await this._performLaunch(this.lastLaunchOptions);
      } catch (error) {
        this.logger.error('navigator_launch_failed', { error: error.message });
        throw error;
      }
    });

    try {
      return await this._launching;
    } finally {
      this._launching = null;
    }
  }

  async _performLaunch(launchOptions) {
    const page = await this.browserContext.launch(launchOptions);
    this.isClosed = false;
    this.networkMonitor.reset();
    this.networkMonitor.setPage(page);
    this.domScraper.setPage(page);
    this.stateProber.setPage(page);
    this.networkMonitor.attach(page);
    this.logger.info('[ReconNavigator] 网络拦截已启用', { traceId: this.traceId });
    return page;
  }

  isHealthy() {
    return this.browserContext.isHealthy();
  }

  async ensureBrowserHealthy() {
    if (this.isHealthy()) {
      return true;
    }

    if (this._healing) {
      await this._healing;
      return this.isHealthy();
    }

    this.logger.warn('navigator_unhealthy_relaunch', {
      traceId: this.traceId,
      hasBrowser: Boolean(this.browser),
      hasContext: Boolean(this.context),
      hasPage: Boolean(this.page)
    });

    this._healing = (async () => {
      await this.close();
      await this.launch(this.lastLaunchOptions || {});
      return this.isHealthy();
    })();

    try {
      return await this._healing;
    } finally {
      this._healing = null;
    }
  }

  async navigate(url, options = {}) {
    await this.ensureBrowserHealthy();

    const timeout = options.timeout || this.navigationTimeoutMs;
    const waitUntil = options.waitUntil || 'networkidle';

    return this.circuitBreaker.execute(async () => {
      this.logger.info('navigate_start', { url });
      this.networkMonitor.reset();
      this.networkMonitor.setPage(this.page);

      try {
        await this.browserContext.navigate(url, {
          timeout,
          waitUntil,
          warmupDelayMs: this.warmupDelayMs,
          scrollIterations: this.scrollIterations,
          scrollStepPx: this.scrollStepPx,
          scrollDelayMs: this.navigateScrollDelayMs
        });

        this.logger.info('navigate_complete', {
          url, interceptedCount: this.interceptedData.length
        });
        return true;
      } catch (error) {
        this.logger.error('navigate_error', { url, error: error.message });
        throw error;
      }
    });
  }

  async _parseApiResponse(body, url = '') {
    return this.networkMonitor.parseApiResponse(body, url);
  }

  async _decodeResponsePayload(body, url = '') {
    return this.networkMonitor.decodeResponsePayload(body, url);
  }

  /**
   * 协议级档案抓取 (V11.0 主要数据获取方式)
   * @param {string} baseUrl
   * @param {object} [options]
   * @param {number} [options.maxPages] - 默认读取配置中心
   * @param {number} [options.timeoutMs] - 默认读取配置中心
   * @param {boolean} [options.preferCurrentSeasonSource=false]
   * @returns {Promise<Object>}
   * @throws {Error} 当浏览器不可恢复或候选源抓取失败时抛出
   */
  async protocolArchiveExtract(baseUrl, options = {}) {
    await this.ensureBrowserHealthy();

    const maxPages = options.maxPages ?? this.archiveMaxPages;
    const timeoutMs = options.timeoutMs ?? this.archiveTimeoutMs;
    const preferCurrentSeasonSource = options.preferCurrentSeasonSource === true;

    if (preferCurrentSeasonSource) {
      this.logger.info('protocol_current_season_start', { baseUrl, maxPages });
      const currentResult = await this.stateProber.probeCurrentSeasonFromPageState(
        baseUrl,
        { maxPages, timeoutMs, maxScrollRounds: this.scrollAttempts },
        this._buildStateProbeHooks()
      );
      this.logger.info('protocol_archive_complete', {
        pagesScanned: currentResult.pageStats?.length || 0,
        totalCandidates: currentResult.matches?.length || 0,
        sourceState: currentResult.sourceState || 'SOURCE_EMPTY'
      });
      return currentResult;
    }

    this.logger.info('protocol_archive_start', { baseUrl, maxPages });
    await this.navigate(baseUrl, { waitUntil: 'networkidle' });

    // 等待 API 端点被发现
    await this.page.waitForTimeout(this.postApiDiscoveryWaitMs);
    
    const archiveEndpoints = Array.from(this.apiEndpoints)
      .filter(url => /ajax-sport-country-tournament-archive_/i.test(url));

    if (archiveEndpoints.length === 0) {
      this.logger.warn('protocol_archive_no_api');
      return { matches: [], pagesScanned: 0, totalCandidates: 0 };
    }

    // 使用评分最高的端点
    const archiveApiUrl = archiveEndpoints.sort((a, b) => this._scoreArchiveUrl(b) - this._scoreArchiveUrl(a))[0];
    
    // 执行解密抓取
    const result = await this._fetchAndDecrypt(archiveApiUrl, maxPages, timeoutMs);
    
    this.logger.info('protocol_archive_complete', {
      pagesScanned: result.pageStats.length,
      totalCandidates: result.matches.length
    });

    return result;
  }

  async fetchFullSeasonArchive(baseUrl, options = {}) {
    await this.ensureBrowserHealthy();

    const timeoutMs = options.timeoutMs ?? this.archiveTimeoutMs;
    const maxPages = options.maxPages ?? this.archiveMaxPages;
    const preferCurrentSeasonSource = options.preferCurrentSeasonSource === true;
    const resultsUrl = this.domScraper.normalizeResultsUrl(baseUrl);

    this.logger.info('season_sweep_start', {
      baseUrl: resultsUrl,
      maxPages,
      preferCurrentSeasonSource
    });

    const discovery = await this.domScraper.discoverSeasonResultPages(
      resultsUrl,
      { timeoutMs, maxPages },
      {
        navigate: (url, navigateOptions) => this.navigate(url, navigateOptions),
        getInterceptedData: () => this.getInterceptedData(),
        waitForTimeout: async (ms) => {
          if (this.page && typeof this.page.waitForTimeout === 'function') {
            await this.page.waitForTimeout(ms);
          }
        }
      }
    );
    const seen = new Set();
    const matches = [];
    const pageStats = [];

    const appendMatches = (pageMatches, pageIndex, pageUrl, source) => {
      let newRows = 0;

      for (const match of Array.isArray(pageMatches) ? pageMatches : []) {
        const key = match?.hash || match?.url;
        if (!key || seen.has(key)) {
          continue;
        }

        seen.add(key);
        matches.push(match);
        newRows++;
      }

      pageStats.push({
        page: pageIndex,
        url: pageUrl,
        rows: Array.isArray(pageMatches) ? pageMatches.length : 0,
        newRows,
        total: matches.length,
        source
      });
    };

    appendMatches(
      discovery.initialMatches,
      1,
      discovery.pageUrls[0] || resultsUrl,
      discovery.initialSource
    );

    for (let index = 1; index < discovery.pageUrls.length; index++) {
      const pageUrl = discovery.pageUrls[index];
      await this.navigate(pageUrl, { waitUntil: 'networkidle', timeout: timeoutMs });
      await this.page.waitForTimeout(this.pageRevisitWaitMs);

      const interceptedMatches = this.getInterceptedData();
      let pageMatches = interceptedMatches;
      let source = 'page_intercept';

      if (pageMatches.length === 0) {
        pageMatches = await this.domScraper.extractCurrentSeasonResultRows(pageUrl);
        source = 'page_dom';
      }

      appendMatches(pageMatches, index + 1, pageUrl, source);
    }

    const archiveResult = await this.protocolArchiveExtract(resultsUrl, {
      maxPages,
      timeoutMs,
      preferCurrentSeasonSource: false
    });

    let archiveNewRows = 0;
    for (const match of Array.isArray(archiveResult?.matches) ? archiveResult.matches : []) {
      const key = match?.hash || match?.url;
      if (!key || seen.has(key)) {
        continue;
      }

      seen.add(key);
      matches.push(match);
      archiveNewRows++;
    }

    if (Array.isArray(archiveResult?.pageStats) && archiveResult.pageStats.length > 0) {
      for (const [index, stat] of archiveResult.pageStats.entries()) {
        pageStats.push({
          ...stat,
          page: stat?.page || (discovery.pageUrls.length + index + 1),
          source: stat?.source || 'archive_api'
        });
      }
    } else if (Array.isArray(archiveResult?.matches) && archiveResult.matches.length > 0) {
      pageStats.push({
        page: discovery.pageUrls.length + 1,
        url: resultsUrl,
        rows: archiveResult.matches.length,
        newRows: archiveNewRows,
        total: matches.length,
        source: 'archive_api'
      });
    }

    if (matches.length === 0 && preferCurrentSeasonSource) {
      const currentSeasonResult = await this.stateProber.probeCurrentSeasonFromPageState(
        baseUrl,
        { maxPages, timeoutMs, maxScrollRounds: this.scrollAttempts },
        this._buildStateProbeHooks()
      );
      let currentSeasonNewRows = 0;

      for (const match of Array.isArray(currentSeasonResult?.matches) ? currentSeasonResult.matches : []) {
        const key = match?.hash || match?.url;
        if (!key || seen.has(key)) {
          continue;
        }

        seen.add(key);
        matches.push(match);
        currentSeasonNewRows++;
      }

      if (Array.isArray(currentSeasonResult?.pageStats) && currentSeasonResult.pageStats.length > 0) {
        for (const [index, stat] of currentSeasonResult.pageStats.entries()) {
          pageStats.push({
            ...stat,
            page: stat?.page || (pageStats.length + index + 1),
            source: stat?.source || currentSeasonResult?.sourceState || 'current_results_archive'
          });
        }
      } else if (Array.isArray(currentSeasonResult?.matches) && currentSeasonResult.matches.length > 0) {
        pageStats.push({
          page: pageStats.length + 1,
          url: this.stateProber.deriveCurrentResultsUrl(baseUrl) || baseUrl,
          rows: currentSeasonResult.matches.length,
          newRows: currentSeasonNewRows,
          total: matches.length,
          source: currentSeasonResult?.sourceState || 'current_results_archive'
        });
      }
    }

    this.logger.info('season_sweep_complete', {
      pageCount: discovery.pageUrls.length,
      totalCandidates: matches.length
    });

    return {
      matches,
      pagesScanned: pageStats.length,
      totalCandidates: matches.length,
      pageStats,
      sourceState: matches.length > 0 ? 'FULL_SEASON_SWEEP' : 'SOURCE_EMPTY',
      pageUrls: discovery.pageUrls
    };
  }

  _buildStateProbeHooks() {
    return {
      navigate: (url, options) => this.navigate(url, options),
      waitForTimeout: async (ms) => {
        if (this.page && typeof this.page.waitForTimeout === 'function') {
          await this.page.waitForTimeout(ms);
        }
      },
      getApiEndpoints: () => Array.from(this.apiEndpoints),
      scoreArchiveUrl: (url) => this._scoreArchiveUrl(url),
      fetchArchive: (url, maxPages, timeoutMs) => this._fetchAndDecrypt(url, maxPages, timeoutMs),
      collectCurrentSeasonResultsDom: (currentResultsUrl, options = {}) => {
        this.domScraper.setPage(this.page);
        return this.domScraper.collectCurrentSeasonResults(currentResultsUrl, {
          ...options,
          maxScrollRounds: options.maxScrollRounds || this.scrollAttempts,
          scrollDelayMs: this.scrollDelayMs
        });
      },
      getCurrentTournamentEndpoint: () => this._getCurrentTournamentEndpoint(),
      fetchCurrentTournament: (url, maxPages, timeoutMs) => (
        this._fetchCurrentTournament(url, maxPages, timeoutMs)
      )
    };
  }

  _getCurrentTournamentEndpoint() {
    const endpoints = Array.from(this.apiEndpoints)
      .filter((url) => /ajax-sport-country-tournament_\/\d+\/[^/]+\/X/i.test(url))
      .filter((url) => !/archive_/i.test(url));

    if (endpoints.length === 0) {
      return null;
    }

    return endpoints.sort((a, b) => this._scoreTournamentUrl(b) - this._scoreTournamentUrl(a))[0];
  }

  _scoreTournamentUrl(url) {
    let score = 0;
    if (/ajax-sport-country-tournament_\/\d+\/[^/]+\/X/i.test(url)) score += 10;
    if (!/\/\d+\/\?_=/i.test(url)) score += 2;
    score += Math.min(url.length / 100, 3);
    return score;
  }

  /**
   * 评分档案 URL 质量
   * @private
   */
  _scoreArchiveUrl(url) {
    let score = 0;
    if (!url.includes('/1//')) score += 5;
    if (/\/archive_\/\d+\/[^/]+\/[^/]+\/\d+\/\d+\//i.test(url)) score += 8;
    if (/\/page\/\d+\//i.test(url)) score += 2;
    score += Math.min(url.length / 100, 3);
    return score;
  }

  /**
   * 获取并解密数据
   * @private
   */
  async _fetchAndDecrypt(apiBaseUrl, maxPages, timeoutMs) {
    return this.circuitBreaker.execute(async () => {
      this.networkMonitor.setPage(this.page);
      return this.networkMonitor.fetchArchivePages(apiBaseUrl, maxPages, timeoutMs);
    });
  }

  async _fetchCurrentTournament(apiBaseUrl, maxPages, timeoutMs) {
    return this.circuitBreaker.execute(async () => {
      this.networkMonitor.setPage(this.page);
      return this.networkMonitor.fetchCurrentTournamentPages(apiBaseUrl, maxPages, timeoutMs);
    });
  }

  /**
   * 获取拦截数据
   * @returns {Array}
   */
  getInterceptedData() {
    return this.networkMonitor.getInterceptedData();
  }

  /**
   * 关闭浏览器
   */
  async close() {
    this.isClosed = true;
    this.networkMonitor.reset();
    await this.browserContext.close();
    this.networkMonitor.setPage(null);
    this.domScraper.setPage(null);
    this.stateProber.setPage(null);
  }
}

module.exports = { ReconNavigator };
