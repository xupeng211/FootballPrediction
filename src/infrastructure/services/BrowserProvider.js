/**
 * @file BrowserProvider - Playwright 浏览器生命周期管理
 * @module infrastructure/services/BrowserProvider
 * @version V6.7.4-STEALTH
 * @description
 * 职责: 管理 Playwright 实例、Context 隔离、Stealth 配置
 * 从 DiscoveryService 解耦，支持独立测试和复用
 */

'use strict';

const { chromium } = require('playwright');

function classifyBrowserFailure(reason = '') {
  const message = String(reason || '').toLowerCase();

  if (message.includes('err_empty_response') || message.includes('empty response')) {
    return {
      failureClass: 'upstream_block',
      rotateProxy: false
    };
  }

  if (
    message.includes('execution context was destroyed')
    || message.includes('target closed')
    || message.includes('target page')
    || message.includes('page crashed')
  ) {
    return {
      failureClass: 'browser_context_transient',
      rotateProxy: false
    };
  }

  if (message.includes('timeout')) {
    return {
      failureClass: 'browser_context_transient',
      rotateProxy: false
    };
  }

  return {
    failureClass: 'proxy_transport',
    rotateProxy: false
  };
}

function isClosedLifecycleError(error) {
  const message = String(error?.message || '').toLowerCase();
  return (
    message.includes('target page, context or browser has been closed')
    || message.includes('browser has been closed')
    || message.includes('target closed')
    || message.includes('context closed')
    || message.includes('page closed')
  );
}

/**
 * 浏览器提供者
 * @class BrowserProvider
 */
class BrowserProvider {
  /**
   * 创建浏览器提供者
   * @param {Object} options - 配置选项
   * @param {Object} options.logger - 日志对象
   * @param {boolean} options.headless - 是否无头模式 (默认: true)
   * @param {Object} options.viewport - 视口大小 (默认: 1920x1080)
   */
  constructor(options = {}) {
    this.logger = options.logger || {
      info: () => {},
      warn: () => {},
      error: () => {}
    };
    
    this.config = {
      headless: options.headless !== false,
      viewport: options.viewport || { width: 1920, height: 1080 },
      userAgent: options.userAgent || 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    };
    
    this.browser = null;
    this.page = null;
    this.defaultTimeoutMs = options.defaultTimeoutMs || 20000;
    this.proxyProvider = options.proxyProvider || null;
    this.proxyConsumer = options.proxyConsumer || 'l1-discovery-browser';
    this.proxySessionKey = options.proxySessionKey || 'main-browser';
    this.proxyLease = null;
    this.browserLaunchPromise = null;
    this.pageRecoveryPromise = null;
    this.closePromise = null;
    this.isClosing = false;
    this.pageOperationTail = Promise.resolve();
  }

  /**
   * 检查浏览器是否已初始化
   * @returns {boolean}
   */
  isInitialized() {
    return this._hasLiveBrowser() && this._hasLivePage();
  }

  /**
   * 初始化浏览器 (闪击模式)
   * @returns {Promise<Page>} Playwright Page 实例
   */
  async initialize() {
    if (this.isInitialized()) {
      return this.page;
    }

    if (this.pageRecoveryPromise) {
      return this.pageRecoveryPromise;
    }

    if (this.browserLaunchPromise) {
      return this.browserLaunchPromise;
    }

    this.browserLaunchPromise = this._initializeInternal();

    try {
      return await this.browserLaunchPromise;
    } finally {
      this.browserLaunchPromise = null;
    }
  }

  async _initializeInternal() {
    await this._waitForCloseIfNeeded();

    if (this.page && !this._hasLivePage()) {
      this.page = null;
    }

    if (this.browser && !this._hasLiveBrowser()) {
      await this._disposeStaleBrowser('initialize-stale-browser');
    }

    if (this._hasLiveBrowser() && !this.page) {
      return this.recoverPage('initialize-page-recovery');
    }
    
    this.logger.info('[BrowserProvider] 🕵️  启动影子浏览器 (闪击模式)...');
    
    try {
      const proxyLease = await this.ensureProxyLease('browser-launch');
      this.browser = await chromium.launch({
        headless: this.config.headless,
        ...(proxyLease ? { proxy: { server: proxyLease.proxy.server } } : {}),
        args: [
          '--disable-dev-shm-usage',
          '--disable-gpu',
          '--disable-software-rasterizer',
          '--disable-extensions',
          '--disable-background-networking',
          '--disable-sync',
          '--no-first-run',
          '--disable-default-apps',
          '--disable-background-timer-throttling',
          '--disable-backgrounding-occluded-windows',
          '--disable-renderer-backgrounding',
          '--blink-settings=imagesEnabled=false',
          '--disable-setuid-sandbox',
          '--no-sandbox'
        ]
      });
      
      this.page = await this._createFreshPage('initialize-launch');
      
      this.logger.info(
        `[BrowserProvider] ✅ 浏览器实例创建成功${proxyLease ? ` | Port ${proxyLease.proxy.port}` : ''}`
      );
      return this.page;
      
    } catch (error) {
      await this.reportProxyFailure({
        reason: error.message,
        statusCode: error.statusCode || null,
        ...classifyBrowserFailure(error.message)
      });
      await this.releaseProxyLease();
      this.logger.error(`[BrowserProvider] ❌ 浏览器启动失败: ${error.message}`);
      throw error;
    }
  }

  /**
   * 访问初始页面获取 Cookies
   * @param {string} url - 初始页面 URL
   * @param {Object} options - 导航选项
   * @returns {Promise<void>}
   */
  async warmup(url = 'https://www.fotmob.com/', options = {}) {
    if (!this.isInitialized()) {
      await this.initialize();
    }
    
    return this._runPageOperation(async () => {
      this.logger.info('[BrowserProvider] 🍪 获取初始 Cookies (轻量模式)...');
      
      try {
        const startTime = Date.now();
        await this.page.goto(url, {
          waitUntil: options.waitUntil || 'domcontentloaded',
          timeout: options.timeout || 15000
        });
        
        await this.reportProxySuccess({
          latencyMs: Date.now() - startTime,
          statusCode: 200
        });
        this.logger.info('[BrowserProvider] ✅ 页面预热完成');
      } catch (error) {
        await this.reportProxyFailure({
          reason: error.message,
          statusCode: error.statusCode || null,
          ...classifyBrowserFailure(error.message)
        });
        // 宽容模式: 即使主页加载失败，也可能已获取到 Cookie
        this.logger.warn(`[BrowserProvider] ⚠️  页面预热警告: ${error.message}`);
        this.logger.warn('[BrowserProvider] 💡 继续执行 (Cookie 可能已获取)');
        if (this._shouldResetPageAfterWarmupFailure(error)) {
          await this._resetPageAfterWarmupFailure(`warmup-failed:${error.message}`);
        }
      }
    }, 'warmup');
  }

  /**
   * 获取当前 Page 实例
   * @returns {Page|null}
   */
  getPage() {
    return this.page;
  }

  /**
   * 获取当前 Browser 实例
   * @returns {Browser|null}
   */
  getBrowser() {
    return this.browser;
  }

  /**
   * 在浏览器上下文内执行 fetch 请求
   * @param {string} url - 请求 URL
   * @param {Object} options - fetch 选项
   * @returns {Promise<Object>} 响应数据
   */
  async fetch(url, options = {}) {
    if (!this.isInitialized()) {
      await this.initialize();
    }
    
    const defaultOptions = {
      method: 'GET',
      headers: {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.fotmob.com/'
      },
      credentials: 'include'
    };
    
    const fetchOptions = { ...defaultOptions, ...options };
    
    // 🔧 修复: 将多个参数封装为单个对象传递
    const timeoutMs = options.timeout || this.defaultTimeoutMs;
    return this._runPageOperation(() => Promise.race([
      this.page.evaluate(async ({ apiUrl, opts }) => {
        try {
          const response = await fetch(apiUrl, opts);
          
          if (!response.ok) {
            return { error: `HTTP ${response.status}`, status: response.status };
          }
          
          const contentType = response.headers.get('content-type') || '';
          if (contentType.includes('text/html')) {
            return { error: 'Received HTML instead of JSON', isHtml: true, status: response.status };
          }
          
          const data = await response.json();
          return { success: true, data, status: response.status };
        } catch (e) {
          return { error: e.message };
        }
      }, { apiUrl: url, opts: fetchOptions }),
      new Promise((_, reject) => {
        setTimeout(() => reject(new Error(`Browser fetch timeout after ${timeoutMs}ms`)), timeoutMs);
      })
    ]), 'fetch');
  }

  /**
   * 获取当前页面 URL
   * @returns {Promise<string>}
   */
  async getCurrentUrl() {
    if (!this.page) return '';
    return this._runPageOperation(() => this.page.url(), 'getCurrentUrl');
  }

  /**
   * 导航到指定 URL
   * @param {string} url - 目标 URL
   * @param {Object} options - 导航选项
   * @returns {Promise<void>}
   */
  async goto(url, options = {}) {
    if (!this.isInitialized()) {
      await this.initialize();
    }
    
    return this._runPageOperation(async () => {
      const startTime = Date.now();
      try {
        await this.page.goto(url, {
          waitUntil: options.waitUntil || 'domcontentloaded',
          timeout: options.timeout || 20000
        });
        await this.reportProxySuccess({
          latencyMs: Date.now() - startTime,
          statusCode: 200
        });
      } catch (error) {
        await this.reportProxyFailure({
          reason: error.message,
          statusCode: error.statusCode || null,
          ...classifyBrowserFailure(error.message)
        });
        throw error;
      }
    }, 'goto');
  }

  /**
   * 执行页面滚动
   * @param {Object} options - 滚动选项
   * @returns {Promise<number>} 滚动后的页面高度
   */
  async scroll(options = {}) {
    if (!this.page) return 0;
    
    const scrollTo = options.to || 'bottom';
    
    return this._runPageOperation(async () => {
      if (scrollTo === 'bottom') {
        await this.page.evaluate(() => {
          window.scrollTo(0, document.body.scrollHeight);
        });
      } else if (scrollTo === 'top') {
        await this.page.evaluate(() => {
          window.scrollTo(0, 0);
        });
      }
      
      // 返回当前页面高度
      return this.page.evaluate(() => document.body.scrollHeight);
    }, 'scroll');
  }

  /**
   * 获取页面高度
   * @returns {Promise<number>}
   */
  async getPageHeight() {
    if (!this.page) return 0;
    return this._runPageOperation(() => this.page.evaluate(() => document.body.scrollHeight), 'getPageHeight');
  }

  /**
   * 等待选择器
   * @param {string} selector - CSS 选择器
   * @param {Object} options - 等待选项
   * @returns {Promise<void>}
   */
  async waitForSelector(selector, options = {}) {
    if (!this.page) return;
    await this._runPageOperation(() => this.page.waitForSelector(selector, {
      state: options.state || 'attached',
      timeout: options.timeout || 10000
    }), 'waitForSelector');
  }

  /**
   * 在页面内执行函数
   * @param {Function} fn - 要执行的函数
   * @param {Array} args - 函数参数
   * @returns {Promise<any>}
   */
  async evaluate(fn, ...args) {
    if (!this.page) return null;
    return this._runPageOperation(() => Promise.race([
      this.page.evaluate(fn, ...args),
      new Promise((_, reject) => {
        setTimeout(() => reject(new Error(`Browser evaluate timeout after ${this.defaultTimeoutMs}ms`)), this.defaultTimeoutMs);
      })
    ]), 'evaluate');
  }

  /**
   * 等待指定时间
   * @param {number} ms - 毫秒
   * @returns {Promise<void>}
   */
  async sleep(ms) {
    await new Promise(resolve => {
      setTimeout(resolve, ms);
    });
  }

  /**
   * 关闭浏览器
   * @returns {Promise<void>}
   */
  async close() {
    if (this.closePromise) {
      return this.closePromise;
    }

    this.isClosing = true;
    const browser = this.browser;
    const page = this.page;

    this.closePromise = this._runPageOperation(async () => {
      try {
        if (!browser) {
          return;
        }

        this.logger.info('[BrowserProvider] 🔒 关闭浏览器...');
        if (page && typeof page.removeAllListeners === 'function') {
          page.removeAllListeners();
        }
        await browser.close();
        this.logger.info('[BrowserProvider] ✅ 浏览器已关闭');
      } finally {
        this.browser = null;
        this.page = null;
        await this.releaseProxyLease();
      }
    }, 'close');

    try {
      await this.closePromise;
    } finally {
      this.closePromise = null;
      this.isClosing = false;
    }
  }

  async recoverPage(reason = 'page-recovery') {
    if (this.pageRecoveryPromise) {
      return this.pageRecoveryPromise;
    }

    if (this.browserLaunchPromise && !this._hasLiveBrowser()) {
      return this.browserLaunchPromise;
    }

    this.pageRecoveryPromise = this._recoverPageInternal(reason);

    try {
      return await this.pageRecoveryPromise;
    } finally {
      this.pageRecoveryPromise = null;
    }
  }

  async _recoverPageInternal(reason) {
    return this._runPageOperation(async () => {
      await this._waitForCloseIfNeeded();

      if (!this._hasLiveBrowser()) {
        this.logger.warn(
          `[BrowserProvider] 🧯 阻断僵尸 newPage，改为重建 Browser: ${reason} | state=${this._describeLifecycleState()}`
        );
        await this._disposeStaleBrowser(`${reason}:stale-browser`);
        return this._initializeInternal();
      }

      const previousPage = this.page;
      this.page = null;

      if (previousPage && typeof previousPage.removeAllListeners === 'function') {
        previousPage.removeAllListeners();
      }

      if (previousPage && typeof previousPage.close === 'function') {
        try {
          await previousPage.close();
        } catch (_error) {
          // 页面可能已经被底层浏览器回收，忽略即可
        }
      }

      try {
        this.page = await this._createFreshPage(reason);
        this.logger.warn(`[BrowserProvider] ♻️ 页面已恢复: ${reason}`);
        return this.page;
      } catch (error) {
        if (!isClosedLifecycleError(error) && this._hasLiveBrowser()) {
          throw error;
        }

        this.logger.warn(
          `[BrowserProvider] 🧯 newPage 命中关闭竞态，改为重建 Browser: ${reason} | ${error.message}`
        );
        await this._disposeStaleBrowser(`${reason}:target-closed`);
        return this._initializeInternal();
      }
    }, 'recoverPage');
  }

  async _createFreshPage(reason = 'page-create') {
    if (!this._hasLiveBrowser()) {
      throw new Error(`browser.newPage blocked: browser is ${this._describeLifecycleState()} (${reason})`);
    }

    return this.browser.newPage({
      viewport: this.config.viewport,
      userAgent: this.config.userAgent
    });
  }

  async _waitForCloseIfNeeded() {
    if (this.closePromise) {
      await this.closePromise;
    }
  }

  _hasLiveBrowser() {
    if (!this.browser || this.isClosing) {
      return false;
    }

    if (typeof this.browser.isConnected === 'function' && !this.browser.isConnected()) {
      return false;
    }

    return typeof this.browser.newPage === 'function';
  }

  _hasLivePage() {
    if (!this.page) {
      return false;
    }

    if (typeof this.page.isClosed === 'function' && this.page.isClosed()) {
      return false;
    }

    return true;
  }

  _describeLifecycleState() {
    if (this.isClosing) {
      return 'closing';
    }

    if (!this.browser) {
      return 'browser-missing';
    }

    if (typeof this.browser.isConnected === 'function' && !this.browser.isConnected()) {
      return 'browser-disconnected';
    }

    if (!this.page) {
      return 'page-missing';
    }

    if (typeof this.page.isClosed === 'function' && this.page.isClosed()) {
      return 'page-closed';
    }

    return 'ready';
  }

  async _disposeStaleBrowser(reason = 'stale-browser') {
    const staleBrowser = this.browser;
    const stalePage = this.page;

    this.browser = null;
    this.page = null;

    if (stalePage && typeof stalePage.removeAllListeners === 'function') {
      stalePage.removeAllListeners();
    }

    if (stalePage && typeof stalePage.close === 'function') {
      try {
        await stalePage.close();
      } catch (_error) {
        // 页面已僵死时允许静默回收
      }
    }

    if (!staleBrowser || typeof staleBrowser.close !== 'function') {
      return;
    }

    try {
      await staleBrowser.close();
    } catch (error) {
      this.logger.warn(`[BrowserProvider] ⚠️  僵尸浏览器回收失败 (${reason}): ${error.message}`);
    }
  }

  _shouldResetPageAfterWarmupFailure(error) {
    const message = String(error?.message || '').toLowerCase();
    return (
      isClosedLifecycleError(error)
      || message.includes('err_empty_response')
      || message.includes('err_aborted')
      || message.includes('failed to fetch')
    );
  }

  async _resetPageAfterWarmupFailure(reason = 'warmup-failed') {
    if (!this._hasLiveBrowser()) {
      return;
    }

    const failedPage = this.page;
    this.page = null;

    if (failedPage && typeof failedPage.removeAllListeners === 'function') {
      failedPage.removeAllListeners();
    }

    if (failedPage && typeof failedPage.close === 'function') {
      try {
        await failedPage.close();
      } catch (_error) {
        // 预热失败页可能已进入失活态，忽略即可
      }
    }

    try {
      this.page = await this._createFreshPage(reason);
      this.logger.warn(`[BrowserProvider] ♻️ 预热失败后已重置页面: ${reason}`);
    } catch (error) {
      this.logger.warn(`[BrowserProvider] ⚠️ 预热失败后重置页面失败: ${error.message}`);
      await this._disposeStaleBrowser(`${reason}:reset-failed`);
    }
  }

  async _runPageOperation(task, _label = 'page-op') {
    const previousOperation = this.pageOperationTail;
    let releaseCurrent = null;
    this.pageOperationTail = new Promise(resolve => {
      releaseCurrent = resolve;
    });

    await previousOperation.catch(() => {});

    try {
      return await task();
    } finally {
      releaseCurrent();
    }
  }

  async ensureProxyLease(reason = 'browser') {
    if (!this.proxyProvider) {
      return null;
    }

    if (this.proxyLease) {
      return this.proxyLease;
    }

    this.proxyLease = await this.proxyProvider.acquire({
      consumer: this.proxyConsumer,
      sessionKey: this.proxySessionKey,
      sticky: true,
      metadata: { reason }
    });

    return this.proxyLease;
  }

  getCurrentProxyLease() {
    return this.proxyLease;
  }

  async reportProxySuccess(metadata = {}) {
    if (!this.proxyProvider || !this.proxyLease) {
      return;
    }

    await this.proxyProvider.reportSuccess(this.proxyLease.id, metadata);
  }

  async reportProxyFailure(metadata = {}) {
    if (!this.proxyProvider || !this.proxyLease) {
      return;
    }

    await this.proxyProvider.reportFailure(this.proxyLease.id, metadata);
  }

  async releaseProxyLease() {
    if (!this.proxyProvider || !this.proxyLease) {
      return;
    }

    const lease = this.proxyLease;
    this.proxyLease = null;
    await this.proxyProvider.release(lease.id);
  }
}

module.exports = { BrowserProvider };
