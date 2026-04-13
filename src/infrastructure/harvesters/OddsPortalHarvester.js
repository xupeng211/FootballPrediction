/* eslint-disable complexity, max-lines */
/**
 * TITAN V5.5 OddsPortal Harvester
 * ==============================
 * 基于Playwright的多线程赔率收割机
 * 利用9900X的多核能力进行并行处理
 * 
 * @module infrastructure/harvesters/OddsPortalHarvester
 * @version V5.5.0-ODDS-REANIMATION
 * @date 2026-03-14
 */

'use strict';

const { chromium } = require('playwright');
const fs = require('fs').promises;
const path = require('path');
const RECON_CONFIG = require('../../../config/recon_config.json');
const { HarvesterRetryPolicy } = require('./components/HarvesterRetryPolicy');
const { HarvesterContextPool } = require('./components/HarvesterContextPool');

// V6.0 SURGICAL-SPLIT: 模块化导入
const {
  deepParseOddsData,
  extractOddsFromDOM,
  buildMarketSentiment,
  OddsPortalURLParser
} = require('./OddsPortalParser');

const ODDSPORTAL_CONFIG = RECON_CONFIG.oddsportal || {};
const LEAGUE_CONFIG = RECON_CONFIG.leagues || {};

/**
 * 构建联赛路由目录。
 * @returns {Object<string, {key: string, country: string, slug: string, name: string}>}
 */
function buildLeagueRouteCatalog() {
  const catalog = {};

  for (const [key, entry] of Object.entries(LEAGUE_CONFIG)) {
    const normalized = {
      key,
      country: entry.country,
      slug: entry.slug,
      name: entry.name,
    };

    catalog[key] = normalized;
    catalog[entry.name] = normalized;
  }

  return Object.freeze(catalog);
}

const LEAGUE_ROUTE_CATALOG = buildLeagueRouteCatalog();
const HARVESTER_PATH_CONFIG = ODDSPORTAL_CONFIG.harvester?.paths || {};

/**
 * 解析联赛路由配置。
 * @param {string} league
 * @returns {{key: string, country: string, slug: string, name: string}}
 */
function resolveLeagueRoute(league) {
  const route = LEAGUE_ROUTE_CATALOG[league];
  if (!route) {
    throw new Error(`未知联赛: ${league}`);
  }
  return route;
}

/**
 * 构建联赛 referer URL。
 * @param {string} league
 * @returns {string}
 */
function buildLeagueRefererUrl(league) {
  const route = resolveLeagueRoute(league);
  return `${ODDSPORTAL_CONFIG.base_url}/football/${route.country}/${route.slug}/results/`;
}

const HARVESTER_CONFIG = {
  MAX_WORKERS: 12,
  MAX_CONCURRENCY: 24,
  CONTEXT_MAX_USAGE: 8,
  CONTEXT_POOL_MAX_SIZE: 12,
  PAGE_TIMEOUT: 30000,
  NAVIGATION_TIMEOUT: 60000,
  MAX_RETRIES: 3,
  RETRY_DELAY_MS: 2000,
  OUTPUT_DIR: HARVESTER_PATH_CONFIG.output_dir,
  SESSION_DIR: HARVESTER_PATH_CONFIG.session_dir,
  SCREENSHOT_DIR: HARVESTER_PATH_CONFIG.screenshot_dir,
  SESSION_FILE: ODDSPORTAL_CONFIG.harvester?.session_file,
  DEFAULT_REFERER_LEAGUE: ODDSPORTAL_CONFIG.harvester?.default_referer_league || 'EPL',
  ODDSPORTAL: {
    baseUrl: ODDSPORTAL_CONFIG.base_url,
    leagues: LEAGUE_ROUTE_CATALOG,
  },
  USE_WARMED_SESSION: true,
  AUTO_WARM_IF_NEEDED: false,
};

/**
 * OddsPortal Harvester主类
 * 基于Playwright的多线程赔率收割机
 */
class OddsPortalHarvester {
  /**
   * @param {Object} options - 配置选项
   */
  constructor(options = {}) {
    // V6.0 HOST-FORCE-UP: 宿主机环境检测
    const isHostEnv = !require('fs').existsSync('/.dockerenv') &&
      (!require('fs').existsSync('/proc/self/cgroup') ||
       !require('fs').readFileSync('/proc/self/cgroup', 'utf8').includes('docker'));

    this.config = {
      ...HARVESTER_CONFIG,
      ...options
    };

    // V6.0 HOST-FORCE-UP: 宿主机模式下调整路径
    if (isHostEnv) {
      this.config.SESSION_DIR = path.join(process.cwd(), 'data/sessions');
      this.config.OUTPUT_DIR = path.join(process.cwd(), 'data/oddsportal');
      this.config.SCREENSHOT_DIR = path.join(process.cwd(), 'data/screenshots');
    }

    this.browser = null;
    this.context = null;
    this.contextPool = new HarvesterContextPool({
      maxUsage: this.config.CONTEXT_MAX_USAGE,
      maxSize: this.config.CONTEXT_POOL_MAX_SIZE,
    });
    this.retryPolicy = new HarvesterRetryPolicy({
      baseBackoffMs: this.config.RETRY_DELAY_MS,
    });
    this._contextConfig = null;
    this.workers = [];
    this.stats = {
      matchesHarvested: 0,
      hashesExtracted: 0,
      errors: 0,
      startTime: null
    };

    // 为每个实例生成唯一的 WebGL 指纹种子
    this.webglSeed = Math.floor(Math.random() * 10000);
  }
  
  /**
   * 生成 WebGL 指纹 - 每个代理独特
   * @private
   */
  _generateWebGLFingerprint() {
    const vendors = ['Intel Inc.', 'NVIDIA Corporation', 'AMD', 'Apple Inc.', 'Intel Open Source Technology Center'];
    const renderers = [
      'Intel Iris Xe Graphics',
      'NVIDIA GeForce RTX 3060',
      'AMD Radeon RX 6600',
      'Apple M1',
      'Intel UHD Graphics 620',
      'NVIDIA GeForce GTX 1060',
      'AMD Radeon Pro 5500M',
      'Intel HD Graphics 630'
    ];
    
    // 使用 seed 确保同一实例指纹一致
    const vendorIndex = this.webglSeed % vendors.length;
    const rendererIndex = (this.webglSeed * 7) % renderers.length;
    
    return {
      vendor: vendors[vendorIndex],
      renderer: renderers[rendererIndex],
      seed: this.webglSeed
    };
  }
  
  /**
   * 初始化浏览器 - V6.0 STEALTH MODE
   */
  async initialize() {
    console.log('🔧 V6.0 Stealth Harvester 初始化中...');

    let warmedSession = null;
    if (this.config.USE_WARMED_SESSION) {
      const sessionPath = path.join(this.config.SESSION_DIR, this.config.SESSION_FILE);
      try {
        const sessionData = await fs.readFile(sessionPath, 'utf-8');
        warmedSession = JSON.parse(sessionData);
        console.log(`   📁 加载预热会话: ${this.config.SESSION_FILE}`);
        console.log(`   🍪 Cookies: ${warmedSession.cookies?.length || 0} 个`);
      } catch (error) {
        console.log('   ⚠️  未找到预热会话，将使用新会话');
      }
    }

    const viewports = [
      { width: 1920, height: 1080 },
      { width: 1366, height: 768 },
      { width: 1440, height: 900 },
      { width: 1536, height: 864 },
      { width: 1280, height: 720 }
    ];
    this.stealthViewport = viewports[Math.floor(Math.random() * viewports.length)];

    const userAgents = [
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
      'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0'
    ];
    this.stealthUserAgent = userAgents[Math.floor(Math.random() * userAgents.length)];
    
    console.log(`   🎭 Viewport: ${this.stealthViewport.width}x${this.stealthViewport.height}`);
    console.log(`   🎭 User-Agent: ${this.stealthUserAgent.substring(0, 60)}...`);

    const isHeadless = this.config.headless !== false;
    if (!isHeadless) {
      console.log('   🖥️  宿主机模式: 强制开启可见浏览器窗口');
    }

    this.browser = await chromium.launch({
      headless: isHeadless,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-accelerated-2d-canvas',
        ...(isHeadless ? ['--disable-gpu'] : []),
        `--window-size=${this.stealthViewport.width},${this.stealthViewport.height}`,
        '--disable-blink-features=AutomationControlled',
        '--disable-web-security',
        '--disable-features=IsolateOrigins,site-per-process',
        '--no-first-run',
        '--no-default-browser-check'
      ]
    });

    this._contextConfig = {
      viewport: this.stealthViewport,
      userAgent: this.stealthUserAgent,
      locale: 'en-US',
      timezoneId: 'America/New_York',
      bypassCSP: true,
      javaScriptEnabled: true
    };

    if (warmedSession) {
      this._contextConfig.storageState = warmedSession;
      console.log('   ✅ 已加载预热会话状态');
    }

    for (let i = 0; i < this.config.MAX_WORKERS; i++) {
      this.workers.push({
        id: i,
        contextKey: i + 1,
        page: null,
        busy: false,
        stats: { requests: 0, errors: 0 }
      });
    }

    this.stats.startTime = Date.now();
    console.log(`✅ V6.0 Harvester 初始化完成 | Workers: ${this.config.MAX_WORKERS}`);
  }

  /**
   * 为新建 Context 注入隐身脚本。
   * @param {import('playwright').BrowserContext} context
   * @returns {Promise<void>}
   * @private
   */
  async _injectStealthContext(context) {
    const webglFingerprint = this._generateWebGLFingerprint();

    await context.addInitScript((fingerprint) => {
      Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
      });
      Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en', 'es-419', 'es']
      });

      const createFakePlugins = () => {
        const plugins = [
          {
            name: 'Chrome PDF Plugin',
            filename: 'internal-pdf-viewer',
            description: 'Portable Document Format plugin',
            version: 'undefined',
            length: 2,
            item: () => plugins[0],
            namedItem: () => plugins[0]
          },
          {
            name: 'Native Client',
            filename: 'native_client.dll',
            description: 'Native Client module',
            version: 'undefined',
            length: 2,
            item: () => plugins[1],
            namedItem: () => plugins[1]
          },
          {
            name: 'Widevine Content Decryption Module',
            filename: 'widevinecdmadapter.dll',
            description: 'Widevine Content Decryption Module',
            version: 'undefined',
            length: 0,
            item: () => null,
            namedItem: () => null
          }
        ];
        plugins.length = 3;
        plugins.item = idx => plugins[idx];
        plugins.namedItem = name => plugins.find(plugin => plugin.name === name);
        return plugins;
      };

      Object.defineProperty(navigator, 'plugins', {
        get: createFakePlugins
      });
      Object.defineProperty(navigator, 'mimeTypes', {
        get: () => [
          { type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format', enabledPlugin: navigator.plugins[0] },
          { type: 'application/x-google-chrome-pdf', suffixes: 'pdf', description: 'Portable Document Format', enabledPlugin: navigator.plugins[0] },
          { type: 'application/x-nacl', suffixes: '', description: 'Native Client executable', enabledPlugin: navigator.plugins[1] }
        ]
      });

      const getParameter = WebGLRenderingContext.prototype.getParameter;
      WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) {
          return fingerprint.vendor;
        }
        if (parameter === 37446) {
          return fingerprint.renderer;
        }
        return getParameter(parameter);
      };

      const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
      HTMLCanvasElement.prototype.toDataURL = function(type) {
        const ctx = this.getContext('2d');
        if (ctx) {
          const imageData = ctx.getImageData(0, 0, this.width, this.height);
          const data = imageData.data;
          for (let i = 0; i < data.length; i += 4) {
            data[i] = data[i] ^ (fingerprint.seed & 0xFF);
          }
          ctx.putImageData(imageData, 0, 0);
        }
        return originalToDataURL.call(this, type);
      };

      window.chrome = {
        loadTimes: () => ({
          requestTime: Date.now() / 1000,
          startLoadTime: Date.now() / 1000,
          commitLoadTime: Date.now() / 1000,
          finishDocumentLoadTime: Date.now() / 1000,
          finishLoadTime: Date.now() / 1000,
          firstPaintTime: Date.now() / 1000,
          firstPaintAfterLoadTime: Date.now() / 1000,
          navigationType: 'Other',
          wasFetchedViaSpdy: false,
          wasNpnNegotiated: false,
          npnNegotiatedProtocol: '',
          wasAlternateProtocolAvailable: false,
          connectionInfo: 'h2',
          remoteAddress: '',
          remotePort: 0,
          socketReuseCount: 0,
          activeSocketCount: 1
        }),
        csi: () => ({
          onloadT: Date.now(),
          pageT: Date.now() - performance.timing.navigationStart,
          startE: performance.timing.navigationStart,
          tran: 15
        }),
        app: {
          isInstalled: false,
          InstallState: { DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' },
          RunningState: { CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' }
        },
        runtime: {
          OnInstalledReason: { CHROME_UPDATE: 'chrome_update', INSTALL: 'install', SHARED_MODULE_UPDATE: 'shared_module_update', UPDATE: 'update' },
          OnRestartRequiredReason: { APP_UPDATE: 'app_update', OS_UPDATE: 'os_update', PERIODIC: 'periodic' },
          PlatformArch: { ARM: 'arm', ARM64: 'arm64', MIPS: 'mips', MIPS64: 'mips64', X86_32: 'x86-32', X86_64: 'x86-64' },
          PlatformNaclArch: { ARM: 'arm', MIPS: 'mips', MIPS32: 'mips32', MIPS64: 'mips64', X86_32: 'x86-32', X86_64: 'x86-64' },
          PlatformOs: { ANDROID: 'android', CROS: 'cros', LINUX: 'linux', MAC: 'mac', OPENBSD: 'openbsd', WIN: 'win' },
          RequestUpdateCheckStatus: { NO_UPDATE: 'no_update', THROTTLED: 'throttled', UPDATE_AVAILABLE: 'update_available' }
        }
      };

      const originalQuery = window.navigator.permissions.query;
      window.navigator.permissions.query = parameters => (
        parameters.name === 'notifications'
          ? Promise.resolve({ state: Notification.permission })
          : originalQuery(parameters)
      );

      delete navigator.__proto__.webdriver;
      Object.defineProperty(navigator, 'deviceMemory', {
        get: () => 8
      });
      Object.defineProperty(navigator, 'hardwareConcurrency', {
        get: () => 8
      });
    }, webglFingerprint);
  }

  /**
   * 创建新的 BrowserContext。
   * @returns {Promise<import('playwright').BrowserContext>}
   * @private
   */
  async _createBrowserContext() {
    const context = await this.browser.newContext({ ...this._contextConfig });
    await this._injectStealthContext(context);
    this.context = context;
    return context;
  }

  /**
   * 获取或创建 Worker 专属 Context。
   * @param {object} worker
   * @returns {Promise<{context: import('playwright').BrowserContext, isNew: boolean}>}
   * @private
   */
  async _getWorkerContext(worker) {
    return this.contextPool.getOrCreate(worker.contextKey, { proxy: { port: worker.contextKey } }, {
      browserFactory: {
        createContext: async () => this._createBrowserContext(),
        loadBrowserStateCookies: async () => false,
      },
      networkManager: null,
    });
  }

  /**
   * 获取 Worker 页面；Context 重建时自动刷新页面。
   * @param {object} worker
   * @returns {Promise<import('playwright').Page>}
   * @private
   */
  async _getWorkerPage(worker) {
    const { context, isNew } = await this._getWorkerContext(worker);

    if (isNew && worker.page && !worker.page.isClosed?.()) {
      await worker.page.close().catch(() => {});
      worker.page = null;
    }

    if (!worker.page || worker.page.isClosed?.()) {
      worker.page = await context.newPage();
    }

    return worker.page;
  }

  /**
   * 生成默认 referer URL。
   * @returns {string}
   * @private
   */
  _buildRefererUrl() {
    return buildLeagueRefererUrl(this.config.DEFAULT_REFERER_LEAGUE);
  }

  /**
   * 使用统一重试策略进行页面导航。
   * @param {object} worker
   * @param {string} targetUrl
   * @param {object} options
   * @param {{label?: string, ignoreFailure?: boolean}} [meta]
   * @returns {Promise<import('playwright').Response|null>}
   * @private
   */
  async _gotoWithRetry(worker, targetUrl, options, meta = {}) {
    const label = meta.label || 'goto';
    const ignoreFailure = meta.ignoreFailure || false;
    let lastError = null;

    for (let attempt = 1; attempt <= this.config.MAX_RETRIES; attempt++) {
      const page = await this._getWorkerPage(worker);

      try {
        return await page.goto(targetUrl, options);
      } catch (error) {
        lastError = error;
        const retryable = this.retryPolicy.isRetryableError(error);

        if (!retryable || attempt === this.config.MAX_RETRIES) {
          if (ignoreFailure) {
            console.log(`   ⚠️  [${label}] 导航失败但继续流程: ${error.message}`);
            return null;
          }
          throw error;
        }

        const backoffMs = this.retryPolicy.getRecommendedBackoff(attempt);
        console.log(`   🔁 [${label}] 第 ${attempt} 次失败，${backoffMs}ms 后重试: ${error.message}`);

        await this.contextPool.closeWorkerContext(worker.contextKey, `RETRY_${label.toUpperCase()}`);
        if (worker.page && !worker.page.isClosed?.()) {
          await worker.page.close().catch(() => {});
        }
        worker.page = null;
        await new Promise(resolve => {
          setTimeout(resolve, backoffMs);
        });
      }
    }

    if (ignoreFailure) {
      return null;
    }

    throw lastError;
  }
  
  /**
   * 获取可用Worker
   * @private
   */
  _getAvailableWorker() {
    return this.workers.find(w => !w.busy);
  }
  
  /**
   * 等待可用Worker
   * @private
   */
  async _waitForWorker() {
    return new Promise((resolve) => {
      const check = () => {
        const worker = this._getAvailableWorker();
        if (worker) {
          resolve(worker);
        } else {
          setTimeout(check, 100);
        }
      };
      check();
    });
  }
  
  /**
   * 从页面提取URL hash
   * @param {string} matchURL - 比赛页面URL
   * @returns {Object} 提取结果
   */
  async extractHashFromPage(matchURL) {
    if (!this.browser) {
      await this.initialize();
    }

    const worker = await this._waitForWorker();
    worker.busy = true;
    
    try {
      const page = await this._getWorkerPage(worker);

      await this._gotoWithRetry(worker, matchURL, {
        waitUntil: 'networkidle',
        timeout: this.config.PAGE_TIMEOUT
      }, { label: 'hash-page' });

      await page.waitForSelector('body', { timeout: 5000 });

      const result = OddsPortalURLParser.parseMatchURL(matchURL);
      
      worker.stats.requests++;
      this.stats.hashesExtracted++;
      
      return {
        success: true,
        hash: result?.match_hash,
        parsed: result,
        url: matchURL,
        worker_id: worker.id
      };
      
    } catch (error) {
      worker.stats.errors++;
      this.stats.errors++;
      
      return {
        success: false,
        error: error.message,
        url: matchURL,
        worker_id: worker.id
      };
    } finally {
      worker.busy = false;
    }
  }
  
  /**
   * 单场比赛真实抓取 - 返回赔率数据
   * @param {string} url - OddsPortal比赛URL
   * @returns {Object} 抓取结果 {odds, hash, pageUrl, rawHtml}
   */
  async harvest(url) {
    if (!this.browser) {
      await this.initialize();
    }
    
    const worker = await this._waitForWorker();
    worker.busy = true;
    
    try {
      const page = await this._getWorkerPage(worker);
      
      console.log(`🔍 Harvester 正在抓取: ${url}`);
      
      page.setDefaultTimeout(60000);
      page.setDefaultNavigationTimeout(60000);
      
      // V6.0 ULTIMATE-FOCUS: API深度侦听升级
      console.log('   🎧 Setting up API interception...');
      const interceptedOddsData = { apiData: null, source: null };
      
      await page.route('**/*', async (route, request) => {
        const requestUrl = request.url();
        const isApiCall = /odds|feed|ajax|api|bet/.test(requestUrl.toLowerCase());
        
        if (isApiCall && request.resourceType() === 'xhr') {
          console.log(`   📡 API intercepted: ${requestUrl.substring(0, 80)}...`);
          
          try {
            const response = await route.fetch();
            const responseBody = await response.text();
            
            // 尝试解析JSON并提取赔率
            try {
              const jsonData = JSON.parse(responseBody);
              
              // 检查是否包含赔率数据
              if (jsonData && (
                jsonData.odds || 
                jsonData.data?.odds || 
                jsonData.fullTime || 
                jsonData.markets
              )) {
                console.log('   💰 Odds data intercepted from API!');
                interceptedOddsData.apiData = jsonData;
                interceptedOddsData.source = 'api_interception';
              }
            } catch (e) {
              // 不是JSON，忽略
            }
          } catch (e) {
            // 获取响应失败，继续
          }
        }
        
        route.continue();
      });
      
      const refererUrl = this._buildRefererUrl();
      try {
        await this._gotoWithRetry(worker, refererUrl, {
          waitUntil: 'domcontentloaded',
          timeout: 10000
        }, { label: 'referer', ignoreFailure: true });
        await page.waitForTimeout(1000 + Math.floor(Math.random() * 1000));
      } catch (e) {
        // referer 访问失败不影响主流程
      }
      
      const response = await this._gotoWithRetry(worker, url, {
        waitUntil: 'domcontentloaded',
        timeout: 60000,
        referer: refererUrl
      }, { label: 'match-page' });
      
      await page.waitForTimeout(2000);
      
      // 模拟鼠标移动到赔率区域
      try {
        const oddsSelectors = ['.odds', '[data-testid="odds"]', '.price', 'div[class*="odd"]'];
        for (const selector of oddsSelectors) {
          const element = await page.$(selector);
          if (element) {
            const box = await element.boundingBox();
            if (box) {
              // 人类化移动：先快速接近，再微调
              await page.mouse.move(
                box.x + box.width / 2 + (Math.random() * 20 - 10),
                box.y + box.height / 2 + (Math.random() * 20 - 10),
                { steps: 10 }
              );
              console.log('   🖱️  Mouse moved to odds area');
              break;
            }
          }
        }
      } catch (e) {
        // 鼠标移动失败不中断流程
      }
      
      // V6.0 SIGHT-RESTORE: 智能选择器等待替代固定超时
      console.log('   ⏳ Smart waiting for odds container...');
      let oddsLoaded = false;
      const oddsSelectors = [
        '.odds-wrap',
        '[data-testid="odds-container"]',
        '.odds',
        '.odds-value',
        '.price',
        '[class*="odds"]'
      ];
      
      // 尝试等待赔率选择器
      for (const selector of oddsSelectors) {
        try {
          await page.waitForSelector(selector, { 
            timeout: 15000, 
            state: 'visible' 
          });
          console.log(`   ✅ Odds selector found: ${selector}`);
          oddsLoaded = true;
          break;
        } catch (e) {
          // 继续尝试下一个选择器
        }
      }
      
      // 保险逻辑：如果超时未发现选择器，执行reload
      if (!oddsLoaded) {
        console.log('   🔄 Reloading page for odds...');
        try {
          await page.reload({ waitUntil: 'domcontentloaded', timeout: 30000 });
          await page.waitForTimeout(3000);
          
          // 再次尝试等待
          for (const selector of oddsSelectors) {
            try {
              await page.waitForSelector(selector, { 
                timeout: 10000, 
                state: 'visible' 
              });
              console.log(`   ✅ Odds selector found after reload: ${selector}`);
              oddsLoaded = true;
              break;
            } catch (e) {
              // 继续尝试
            }
          }
        } catch (reloadError) {
          console.log(`   ⚠️  Reload failed: ${reloadError.message}`);
        }
      }
      
      // 获取实际页面URL（可能有重定向）
      const pageUrl = page.url();
      
      // 检查响应状态
      if (!response) {
        throw new Error('页面导航失败: 无响应');
      }
      
      console.log(`   📄 Response Status: ${response.status()}`);
      console.log(`   📄 Final URL: ${pageUrl}`);
      
      // V6.0 反爬检测：检查页面标题
      const pageTitle = await page.title();
      console.log(`   📄 Page Title: ${pageTitle}`);
      
      // 检测拦截关键词
      const blockIndicators = [
        'just a moment',
        'cloudflare',
        'security check',
        'captcha',
        'access denied',
        'blocked'
      ];
      
      const isBlocked = blockIndicators.some(indicator => 
        pageTitle.toLowerCase().includes(indicator)
      );
      
      if (isBlocked) {
        throw new Error(`SCRAPE_BLOCKED_ERROR: 页面被拦截 (Title: "${pageTitle}")`);
      }
      
      // V6.0 ACTION MIMICRY: 人类阅读节奏模拟
      console.log('   🎭 Simulating human reading pattern...');
      
      // 第1次滚动：小幅度探索
      await page.evaluate(() => {
        window.scrollBy({ top: 100 + Math.floor(Math.random() * 150), behavior: 'smooth' });
      });
      await page.waitForTimeout(800 + Math.floor(Math.random() * 700));
      
      // 第2次滚动：回到顶部附近
      await page.evaluate(() => {
        window.scrollBy({ top: -(50 + Math.floor(Math.random() * 80)), behavior: 'smooth' });
      });
      await page.waitForTimeout(600 + Math.floor(Math.random() * 500));
      
      // 第3次滚动：向下阅读赔率区域
      await page.evaluate(() => {
        window.scrollBy({ top: 200 + Math.floor(Math.random() * 200), behavior: 'smooth' });
      });
      await page.waitForTimeout(1000 + Math.floor(Math.random() * 1000));
      
      // 最终停顿：模拟阅读赔率
      const readingTime = 1500 + Math.floor(Math.random() * 1500);
      console.log(`   ⏱️  Reading time: ${readingTime}ms`);
      await page.waitForTimeout(readingTime);
      
      // V6.0 ULTIMATE-FOCUS: 超频动态等待与深度侦听
      console.log('   🔍 Ultimate focus rendering check...');
      
      // 延长基础等待时间至20s（给予本地JS充分渲染时间）
      const baseWaitTime = 20000;
      console.log(`   ⏱️  Base wait time: ${baseWaitTime}ms (Overclocked)`);
      await page.waitForTimeout(baseWaitTime);
      
      // 智能钩子：等待1X2表格出现且包含小数赔率
      console.log('   ⏳ Waiting for 1X2 odds table...');
      let oddsTableFound = false;
      
      try {
        await page.waitForFunction(() => {
          // 查找包含"1X2"或类似标识的表格
          const tables = document.querySelectorAll('table, .odds-table, .market-table');
          for (const table of tables) {
            const text = table.innerText || table.textContent || '';
            // 检查是否包含1X2标识且有3个小数赔率
            const has1X2 = /1\s*X\s*2|home\s*draw\s*away/i.test(text);
            const oddsMatches = text.match(/\d+\.\d{2}/g);
            if (has1X2 && oddsMatches && oddsMatches.length >= 3) {
              return true;
            }
          }
          // 或者查找.odds-wrap中的赔率
          const oddsWrap = document.querySelector('.odds-wrap');
          if (oddsWrap) {
            const text = oddsWrap.innerText || '';
            const oddsMatches = text.match(/\d+\.\d{2}/g);
            if (oddsMatches && oddsMatches.length >= 3) {
              return true;
            }
          }
          return false;
        }, { timeout: 30000 });
        
        oddsTableFound = true;
        console.log('   ✅ 1X2 odds table detected!');
      } catch (e) {
        console.log('   ⚠️  1X2 odds table not found within 30s');
      }
      
      // V3 PRECISION-LOCK: Persistence Hook - 死磕 Pinnacle 和 Bet365
      console.log('   🔒 V3 PRECISION-LOCK: Checking for Pinnacle & Bet365...');
      
      // 首先检查页面是否包含目标博彩公司
      const checkBookies = async () => {
        return page.evaluate(() => {
          const pageText = document.body?.innerText || '';
          return {
            hasPinnacle: /pinnacle/i.test(pageText),
            hasBet365: /bet365/i.test(pageText),
            hasBookmakersTab: /bookmakers|all bookies|odds comparison/i.test(pageText)
          };
        });
      };
      
      let bookieCheck = await checkBookies();
      console.log(`   📊 Initial check: Pinnacle=${bookieCheck.hasPinnacle}, Bet365=${bookieCheck.hasBet365}`);
      
      // 如果没有找到目标博彩公司，尝试点击 Bookmakers 标签
      if (!bookieCheck.hasPinnacle && !bookieCheck.hasBet365 && bookieCheck.hasBookmakersTab) {
        console.log('   🖱️  V3 LOCK: Clicking Bookmakers tab...');
        try {
          // 尝试多种可能的选择器
          const bookmakerSelectors = [
            'text=Bookmakers',
            'text=All bookies',
            'text=Odds comparison',
            '[data-testid="bookmakers-tab"]',
            'button:has-text("Bookmakers")',
            'a:has-text("Bookmakers")'
          ];
          
          for (const selector of bookmakerSelectors) {
            const element = await page.$(selector);
            if (element) {
              await element.click();
              console.log(`   ✅ Clicked: ${selector}`);
              break;
            }
          }
          
          await page.waitForTimeout(5000);
          bookieCheck = await checkBookies();
          console.log(`   📊 After click: Pinnacle=${bookieCheck.hasPinnacle}, Bet365=${bookieCheck.hasBet365}`);
        } catch (e) {
          console.log('   ⚠️  Could not click Bookmakers tab:', e.message);
        }
      }
      
      // 视觉自检：确认赔率容器有内容
      let visualCheckAttempts = 0;
      const maxVisualAttempts = 3;
      let hasVisualContent = false;
      
      while (visualCheckAttempts < maxVisualAttempts && !hasVisualContent) {
        visualCheckAttempts++;
        
        // 检查 .odds-wrap 内容
        const oddsWrapContent = await page.evaluate(() => {
          const oddsWrap = document.querySelector('.odds-wrap');
          if (oddsWrap) {
            return {
              found: true,
              innerTextLength: oddsWrap.innerText?.length || 0,
              innerHTMLLength: oddsWrap.innerHTML?.length || 0
            };
          }
          return { found: false, innerTextLength: 0, innerHTMLLength: 0 };
        });
        
        console.log(`   📊 Visual check #${visualCheckAttempts}: .odds-wrap text=${oddsWrapContent.innerTextLength} chars`);
        
        if (oddsWrapContent.innerTextLength > 0) {
          hasVisualContent = true;
          console.log('   ✅ Visual content confirmed!');
        } else if (visualCheckAttempts < maxVisualAttempts) {
          // 内容为空，触发滚动唤醒懒加载
          console.log('   🔄 Waking up lazy load scripts...');
          await page.mouse.wheel(0, 500);
          await page.waitForTimeout(2000);
          
          // 再次尝试小幅度滚动
          await page.mouse.wheel(0, -200);
          await page.waitForTimeout(1500);
        }
      }
      
      // V3: 如果仍未找到目标博彩公司，标记为熔断
      if (!bookieCheck.hasPinnacle && !bookieCheck.hasBet365) {
        console.log('   🚫 V3 LOCK: BOOKIE_NOT_FOUND - Will attempt DOM extraction');
      }
      
      if (!hasVisualContent && !oddsTableFound) {
        console.log('   ⚠️  Warning: No visual content or odds table after all attempts');
      }
      
      // V6.0 ULTIMATE-FOCUS: 视觉审计闭环v2
      console.log('   📸 Visual audit v2: Taking screenshot...');
      
      // waitForFunction成功后延迟2秒再截图
      await page.waitForTimeout(2000);
      
      const screenshotDir = this.config.SCREENSHOT_DIR;
      await fs.mkdir(screenshotDir, { recursive: true }).catch(() => {});
      const timestamp = Date.now();
      let screenshotPath = path.join(screenshotDir, `match_${timestamp}.png`);
      let screenshotSize = 0;
      let screenshotAttempts = 0;
      const maxScreenshotAttempts = 3;
      
      while (screenshotAttempts < maxScreenshotAttempts) {
        screenshotAttempts++;
        
        try {
          await page.screenshot({ 
            path: screenshotPath, 
            fullPage: true 
          });
          
          // 获取截图文件大小
          const screenshotStats = await fs.stat(screenshotPath).catch(() => null);
          if (screenshotStats) {
            screenshotSize = screenshotStats.size;
            console.log(`   📸 Screenshot #${screenshotAttempts}: ${(screenshotSize / 1024).toFixed(2)} KB`);
            
            // 断言: 截图必须 > 100KB
            if (screenshotSize >= 100 * 1024) {
              console.log('   ✅ Screenshot quality verified (> 100KB)');
              break;
            } else {
              console.log(`   ⚠️  Screenshot too small (${(screenshotSize / 1024).toFixed(2)} KB < 100KB)`);
              
              if (screenshotAttempts < maxScreenshotAttempts) {
                console.log('   🔄 Scrolling to wake up rendering...');
                await page.mouse.wheel(0, 1000);
                await page.waitForTimeout(3000);
                // 更新路径重试
                screenshotPath = path.join(screenshotDir, `match_${timestamp}_retry${screenshotAttempts}.png`);
              }
            }
          }
        } catch (screenshotError) {
          console.log(`   ⚠️  Screenshot attempt ${screenshotAttempts} failed: ${screenshotError.message}`);
        }
      }
      
      if (screenshotSize < 100 * 1024) {
        console.log(`   ⚠️  Warning: Screenshot still < 100KB after all attempts`);
      }
      
      // V6.0 DEEP-PARSE: 委托解析组件进行深度解析
      let odds = {};
      let deepParseData = null;
      
      if (interceptedOddsData.apiData) {
        console.log('   💰 V6.0 DEEP-PARSE: Analyzing API payload structure...');
        deepParseData = deepParseOddsData(interceptedOddsData.apiData);
        
        if (deepParseData && (deepParseData.pinnacle?.closing || deepParseData.bet365?.closing)) {
          const mainBookie = deepParseData.pinnacle || deepParseData.bet365;
          odds = {
            '1x2': mainBookie.closing,
            opening: mainBookie.opening,
            closing: mainBookie.closing,
            curve: mainBookie.history,
            bookmakers: {
              ...(deepParseData.pinnacle && { pinnacle: deepParseData.pinnacle }),
              ...(deepParseData.bet365 && { bet365: deepParseData.bet365 })
            },
            _source: 'api_deep_parse_v6',
            _apiUrl: interceptedOddsData.apiUrl
          };
          console.log(`   ✅ DEEP-PARSE extracted from API (P0: ${Object.keys(odds.bookmakers).join(', ')})`);
        }
      }
      
      // V6.0 DOM-SNIPER: 如果API失败，启动狙击模式
      if (!odds['1x2']) {
        console.log('   🎯 DOM Sniper: API extraction failed, starting sniper mode...');
        const domResult = await extractOddsFromDOM(page);
        
        if (domResult['1x2'] || domResult.pinnacleOdds || domResult.bet365Odds) {
          odds = {
            '1x2': domResult['1x2'] || domResult.pinnacleOdds || domResult.bet365Odds,
            pinnacle_odds: domResult.pinnacleOdds ? { closing: domResult.pinnacleOdds } : null,
            bet365_odds: domResult.bet365Odds ? { closing: domResult.bet365Odds } : null,
            _source: domResult._source || 'dom_sniper',
            _diagnostic: domResult._diagnostic
          };
          console.log(`   🎯 DOM Sniper acquired: ${odds['1x2'].join(' | ')} (Source: ${odds._source})`);
        }
      }
      
      // V6.0 SIGHT-RESTORE: 获取完整页面HTML用于验证
      const rawHtml = await page.content();
      const parsed = OddsPortalURLParser.parseMatchURL(url);
      
      worker.stats.requests++;
      this.stats.matchesHarvested++;
      
      // V6.0 ULTIMATE-LOCK: 使用统一构建器生成市场情感数据
      const marketSentiment = buildMarketSentiment(deepParseData, {
        pinnacleOdds: odds.pinnacle_odds?.closing,
        bet365Odds: odds.bet365_odds?.closing,
        _source: odds._source
      }, {
        sourceChannel: odds._source
      });

      // 补充基础元数据
      marketSentiment.match_id = parsed?.match_hash || null;
      marketSentiment.oddsportal_url = url;
      marketSentiment.oddsportal_hash = parsed?.match_hash;
      
      return {
        odds,
        market_sentiment: marketSentiment,
        hash: parsed?.match_hash,
        pageUrl,
        url,
        _responseStatus: response?.status(),
        _pageTitle: pageTitle,
        rawHtml: rawHtml,
        _htmlLength: rawHtml.length,
        worker_id: worker.id
      };
      
    } catch (error) {
      worker.stats.errors++;
      this.stats.errors++;
      throw error;
    } finally {
      worker.busy = false;
    }
  }

  /**
   * 批量收割比赛hash
   * @param {Array} matches - 比赛列表 [{match_id, url}]
   * @returns {Array} 收割结果
   */
  async harvestBatch(matches) {
    console.log(`🚀 V5.5 开始批量收割: ${matches.length}场比赛`);
    
    const promises = matches.map(match => 
      this.extractHashFromPage(match.url)
    );
    
    const results = await Promise.all(promises);
    
    // 统计
    const successCount = results.filter(r => r.success).length;
    console.log(`✅ 批量收割完成: ${successCount}/${matches.length} 成功`);
    
    return results;
  }
  
  /**
   * 保存结果到文件
   * @param {Array} results - 收割结果
   * @param {string} filename - 输出文件名
   */
  async saveResults(results, filename = 'oddsportal_hashes.json') {
    const outputPath = path.join(this.config.OUTPUT_DIR, filename);
    
    // 确保目录存在
    await fs.mkdir(this.config.OUTPUT_DIR, { recursive: true });
    
    const output = {
      metadata: {
        version: 'V5.5',
        timestamp: new Date().toISOString(),
        total: results.length,
        success: results.filter(r => r.success).length
      },
      results: results.filter(r => r.success).map(r => ({
        hash: r.hash,
        url: r.url,
        parsed: r.parsed,
        // 对接matches_mapping表字段
        oddsportal_hash: r.hash,
        oddsportal_url: r.url,
        confidence: 0.95,  // 高置信度
        mapping_method: 'V5.5_HARVESTER'
      }))
    };
    
    await fs.writeFile(outputPath, JSON.stringify(output, null, 2));
    console.log(`💾 结果已保存: ${outputPath}`);
    
    return outputPath;
  }
  
  /**
   * 生成统计报告
   */
  getStats() {
    const elapsed = Date.now() - this.stats.startTime;
    return {
      ...this.stats,
      elapsed_ms: elapsed,
      throughput: this.stats.matchesHarvested / (elapsed / 1000)
    };
  }
  
  /**
   * 关闭Harvester
   */
  async close() {
    console.log('🔒 V5.5 Harvester 关闭中...');
    
    for (const worker of this.workers) {
      if (worker.page) {
        await worker.page.close();
      }
    }

    await this.contextPool.closeAllContexts();
    this.context = null;
    
    if (this.browser) {
      await this.browser.close();
    }
    
    console.log('✅ Harvester 已关闭');
  }
}

// 导出模块
module.exports = {
  OddsPortalHarvester,
  OddsPortalURLParser,
  HARVESTER_CONFIG,
  // V6.0 SURGICAL-SPLIT: 同时导出新的子模块
  StealthNavigator: require('./StealthNavigator'),
  OddsPortalParser: require('./OddsPortalParser')
};
