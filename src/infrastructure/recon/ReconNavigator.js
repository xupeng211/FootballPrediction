'use strict';

const { ReconCircuitBreaker, ReconCircuitBreakerPool } = require('./ReconResilience');
const { ReconBrowserContext } = require('./services/ReconBrowserContext');
const { ReconDomScraper } = require('./services/ReconDomScraper');
const { ReconNetworkMonitor, createDefaultStats } = require('./services/ReconNetworkMonitor');
const { ReconProtocolHandler } = require('./services/ReconProtocolHandler');
const { ReconRetryCoordinator } = require('./services/ReconRetryCoordinator');
const { ReconStateProber } = require('./services/ReconStateProber');
const { RECON_CONFIG, getReconConfigSection } = require('./services/ReconServiceConfig');

const BASE_URL = RECON_CONFIG.oddsportal.base_url;
const HTTP_503_RETRY_DELAYS_MS = [5000, 15000, 30000];

function generateTraceId() {
  return `trace-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

class ReconNavigator {
  constructor(options = {}) {
    const navigatorConfig = getReconConfigSection(['recon_runtime', 'navigator'], {});

    this.logger = options.logger || console;
    this.proxy = options.proxy;
    this.proxyRotator = options.proxyRotator || null;
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
    this.enableStealthFingerprint = options.enableStealthFingerprint;

    // V11.0: TraceID 机制 - 每笔收割请求唯一编号
    this.traceId = options.traceId || generateTraceId();
    this.sessionStartTime = Date.now();
    this.http503RetryDelaysMs = Array.isArray(options.http503RetryDelaysMs) && options.http503RetryDelaysMs.length > 0
      ? [...options.http503RetryDelaysMs]
      : [...HTTP_503_RETRY_DELAYS_MS];

    const breakerOptions = {
      failureThreshold: navigatorConfig.circuit_breaker?.failure_threshold,
      resetTimeout: navigatorConfig.circuit_breaker?.reset_timeout_ms,
      maxEntries: navigatorConfig.circuit_breaker?.max_entries,
      logger: this.logger
    };

    this._defaultCircuitBreaker = new ReconCircuitBreaker(breakerOptions);
    this.circuitBreaker = this._defaultCircuitBreaker;
    this.circuitBreakerPool = new ReconCircuitBreakerPool(breakerOptions);

    this.browserContext = new ReconBrowserContext({
      logger: this.logger,
      traceId: this.traceId,
      headless: this.headless,
      proxy: this.proxy,
      enableStealthFingerprint: this.enableStealthFingerprint
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
    this.retryCoordinator = new ReconRetryCoordinator(this);
    this.protocolHandler = new ReconProtocolHandler(this);
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

  _deriveCircuitBreakerKey(url, fallbackKey = 'default') {
    const normalized = String(url || '').trim();
    if (!normalized) {
      return fallbackKey;
    }

    const pageMatch = normalized.match(/\/football\/([^/]+)\/([^/?#]+?)(?:\/results(?:\/page\/\d+)?)?\/?$/i);
    if (pageMatch) {
      const country = pageMatch[1];
      const slug = pageMatch[2]
        .replace(/-\d{4}-\d{4}$/i, '')
        .replace(/-\d{4}$/i, '');
      return `league:${country}/${slug}`;
    }

    return fallbackKey;
  }

  _resolveCircuitBreakerKey(url, options = {}) {
    const explicitKey = typeof options.circuitBreakerKey === 'string'
      ? options.circuitBreakerKey.trim()
      : '';
    if (explicitKey) {
      return explicitKey;
    }

    return this._deriveCircuitBreakerKey(url, 'default');
  }

  _getCircuitBreaker(key = 'default') {
    if (
      this.circuitBreaker
      && this.circuitBreaker !== this._defaultCircuitBreaker
      && typeof this.circuitBreaker.execute === 'function'
    ) {
      return this.circuitBreaker;
    }

    if (this.circuitBreakerPool && typeof this.circuitBreakerPool.get === 'function') {
      return this.circuitBreakerPool.get(key);
    }

    return this.circuitBreaker || this._defaultCircuitBreaker;
  }

  async _executeWithCircuitBreaker(key, fn, options = {}) {
    return this._getCircuitBreaker(key).execute(fn, options);
  }

  _parseRetryAfterMs(value) {
    return this.retryCoordinator.parseRetryAfterMs(value);
  }

  async _waitBeforeRetry(delayMs) {
    return this.retryCoordinator.waitBeforeRetry(delayMs);
  }

  async _inspectHttpFailure(url, timeoutMs) {
    return this.retryCoordinator.inspectHttpFailure(url, timeoutMs);
  }

  async _resolveRetryableHttpFailureFromError(error, context = {}) {
    return this.retryCoordinator.resolveRetryableHttpFailureFromError(error, context);
  }

  _resolveRetryableHttpFailureFromResult(result) {
    return this.retryCoordinator.resolveRetryableHttpFailureFromResult(result);
  }

  _buildRetryError(context = {}, failure = {}) {
    return this.retryCoordinator.buildRetryError(context, failure);
  }

  async _executeWith503Retry(operation, context = {}) {
    return this.retryCoordinator.executeWith503Retry(operation, context);
  }

  async launch(options = {}) {
    if (this.isHealthy()) {
      return this.page;
    }

    if (this._launching) {
      return this._launching;
    }

    this._launching = this._executeWithCircuitBreaker('browser:launch', async () => {
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
    this.networkMonitor.detach?.();
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
    const waitUntil = options.waitUntil || 'domcontentloaded';
    const breakerKey = this._resolveCircuitBreakerKey(url, options);

    return this._executeWithCircuitBreaker(breakerKey, async () => this._executeWith503Retry(
      async () => {
        this.logger.info('navigate_start', { url, breakerKey });
        this.networkMonitor.reset();
        this.networkMonitor.setPage(this.page);

        await this.browserContext.navigate(url, {
          timeout,
          waitUntil,
          warmupDelayMs: this.warmupDelayMs,
          scrollIterations: this.scrollIterations,
          scrollStepPx: this.scrollStepPx,
          scrollDelayMs: this.navigateScrollDelayMs,
          readySelectors: options.readySelectors,
          readyTimeoutMs: options.readyTimeoutMs,
          contentReadySelector: options.contentReadySelector
        });

        this.logger.info('navigate_complete', {
          url,
          breakerKey,
          interceptedCount: this.interceptedData.length
        });
        return true;
      },
      {
        operationName: 'navigate',
        breakerKey,
        inspectUrl: url,
        timeoutMs: timeout
      }
    )).catch((error) => {
      this.logger.error('navigate_error', { url, breakerKey, error: error.message });
      throw error;
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
    return this.protocolHandler.protocolArchiveExtract(baseUrl, options);
  }

  async fetchFullSeasonArchive(baseUrl, options = {}) {
    return this.protocolHandler.fetchFullSeasonArchive(baseUrl, options);
  }

  _buildStateProbeHooks(defaultNavigateOptions = {}, circuitBreakerKey = 'default') {
    return this.protocolHandler._buildStateProbeHooks(defaultNavigateOptions, circuitBreakerKey);
  }

  _getCurrentTournamentEndpoint() {
    return this.protocolHandler._getCurrentTournamentEndpoint();
  }

  _scoreTournamentUrl(url) {
    return this.protocolHandler._scoreTournamentUrl(url);
  }

  /**
   * 评分档案 URL 质量
   * @private
   */
  _scoreArchiveUrl(url) {
    return this.protocolHandler._scoreArchiveUrl(url);
  }

  /**
   * 获取并解密数据
   * @private
   */
  async _fetchAndDecrypt(apiBaseUrl, maxPages, timeoutMs, options = {}) {
    return this.protocolHandler._fetchAndDecrypt(apiBaseUrl, maxPages, timeoutMs, options);
  }

  async _fetchAndDecryptWithOptions(apiBaseUrl, maxPages, timeoutMs, options = {}) {
    return this.protocolHandler._fetchAndDecryptWithOptions(apiBaseUrl, maxPages, timeoutMs, options);
  }

  async _fetchCurrentTournament(apiBaseUrl, maxPages, timeoutMs, options = {}) {
    return this.protocolHandler._fetchCurrentTournament(apiBaseUrl, maxPages, timeoutMs, options);
  }

  async extractViaPureProtocol(target, options = {}) {
    return this.protocolHandler._extractViaPureProtocol(target, options);
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
    this.networkMonitor.detach?.();
    this.networkMonitor.reset();
    await this.browserContext.close();
    this.networkMonitor.setPage(null);
    this.domScraper.setPage(null);
    this.stateProber.setPage(null);
  }

  _resultHasDecryptFailure(result) {
    return this.protocolHandler._resultHasDecryptFailure(result);
  }

  async _resolveLeagueTournamentContext(baseUrl, timeoutMs, archiveApiUrl = null, options = {}) {
    return this.protocolHandler._resolveLeagueTournamentContext(baseUrl, timeoutMs, archiveApiUrl, options);
  }

  _repairArchiveEndpointWithTournamentId(archiveApiUrl, tournamentId) {
    return this.protocolHandler._repairArchiveEndpointWithTournamentId(archiveApiUrl, tournamentId);
  }

  _buildTournamentUrlFromArchive(archiveApiUrl, tournamentId) {
    return this.protocolHandler._buildTournamentUrlFromArchive(archiveApiUrl, tournamentId);
  }

  async _fallbackToLeagueTournament(baseUrl, archiveApiUrl, maxPages, timeoutMs, reason = 'fallback', options = {}) {
    return this.protocolHandler._fallbackToLeagueTournament(
      baseUrl,
      archiveApiUrl,
      maxPages,
      timeoutMs,
      reason,
      options
    );
  }
}

module.exports = { ReconNavigator };
