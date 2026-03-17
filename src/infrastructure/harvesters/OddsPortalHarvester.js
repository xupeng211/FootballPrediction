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
const { SessionWarmer } = require('./SessionWarmer');

// V6.0 SURGICAL-SPLIT: 模块化导入
const {
  executeHumanMimicSequence,
  contextSwitchManeuver,
  visionRecoveryCheck
} = require('./StealthNavigator');

const {
  deepParseOddsData,
  extractOddsFromDOM,
  buildMarketSentiment,
  extractOddsArrays,
  findValuesByKey,
  findBookieById,
  BOOKMAKER_ID_MAP,
  ODDS_FIELD_PATTERNS
} = require('./OddsPortalParser');

// V6.0 配置常量 - 住宅代理增强版
const HARVESTER_CONFIG = {
  // 9900X多线程配置
  MAX_WORKERS: 12,  // 12核Worker Pool
  MAX_CONCURRENCY: 24,  // 并行任务数
  
  // 页面配置
  PAGE_TIMEOUT: 30000,  // 30秒超时
  NAVIGATION_TIMEOUT: 60000,
  
  // 重试配置
  MAX_RETRIES: 3,
  RETRY_DELAY_MS: 2000,
  
  // 输出配置
  OUTPUT_DIR: '/app/data/oddsportal',
  SESSION_DIR: '/app/data/sessions',
  
  // OddsPortal配置
  BASE_URL: 'https://www.oddsportal.com',
  LEAGUE_URLS: {
    'Premier League': '/soccer/england/premier-league/',
    'La Liga': '/soccer/spain/laliga/',
    'Bundesliga': '/soccer/germany/bundesliga/',
    'Serie A': '/soccer/italy/serie-a/',
    'Ligue 1': '/soccer/france/ligue-1/',
  },
  
  // V6.0 会话配置 - 强制使用黄金会话
  SESSION_FILE: 'auth_gold.json',  // 强制指向黄金Cookie
  USE_WARMED_SESSION: true,  // 使用预热会话
  AUTO_WARM_IF_NEEDED: false  // 禁用自动预热，强制使用手动注入的会话
};

// NOTE: BOOKMAKER_ID_MAP 和 ODDS_FIELD_PATTERNS 现在从 OddsPortalParser 导入
// 保留此处注释以说明常量来源

/**
 * OddsPortal URL解析器
 * 从URL中提取hash段落
 */
class OddsPortalURLParser {
  /**
   * 解析比赛URL，提取hash
   * @param {string} url - OddsPortal比赛URL
   * @returns {Object} 解析结果 {league, season, match_hash, teams}
   */
  static parseMatchURL(url) {
    // 支持的URL格式:
    // https://www.oddsportal.com/soccer/england/premier-league/manchester-united-chelsea/
    // https://www.oddsportal.com/soccer/england/premier-league-2023-2024/manchester-united-chelsea/
    // https://www.oddsportal.com/soccer/spain/laliga/real-madrid-barcelona/
    
    try {
      // 解析URL路径部分
      const urlObj = new URL(url);
      const pathParts = urlObj.pathname.split('/').filter(p => p.length > 0);
      
      // 基本验证: 路径应包含至少4部分 (soccer, country, league, match)
      if (pathParts.length < 4) {
        return null;
      }
      
      const [sport, country, leaguePart, ...matchParts] = pathParts;
      
      // 验证sport必须是soccer
      if (sport !== 'soccer') {
        return null;
      }
      
      // 解析联赛和赛季
      // leaguePart可能是: premier-league 或 premier-league-2023-2024
      let league = leaguePart;
      let season = null;
      
      const seasonMatch = leaguePart.match(/^(.+)-(\d{4})-(\d{4})$/);
      if (seasonMatch) {
        league = seasonMatch[1];
        season = `${seasonMatch[2]}/${seasonMatch[3]}`;
      }
      
      // 解析队名 (matchParts数组的最后部分)
      const matchSlug = matchParts[matchParts.length - 1] || '';
      let home_team = null;
      let away_team = null;
      
      if (matchSlug) {
        // 解码并解析队名 (格式: team-a-vs-team-b 或 team-a-team-b)
        const decoded = decodeURIComponent(matchSlug);
        // 尝试多种分隔符
        const separators = ['-vs-', '-vs-', '-v-', ' vs ', ' v ', '-@-', '-', '_'];
        for (const sep of separators) {
          if (decoded.includes(sep)) {
            const teams = decoded.split(sep).map(t => t.trim());
            if (teams.length >= 2) {
              home_team = teams[0].replace(/-/g, ' ');
              away_team = teams[1].replace(/-/g, ' ');
              break;
            }
          }
        }
        // 如果没有找到分隔符，尝试简单的分割
        if (!home_team && decoded.includes('-')) {
          const parts = decoded.split('-');
          const mid = Math.floor(parts.length / 2);
          home_team = parts.slice(0, mid).join(' ');
          away_team = parts.slice(mid).join(' ');
        }
      }
      
      // 生成hash (用于matches_mapping表)
      const matchHash = this._generateHash(url);
      
      return {
        league,
        season,
        match_hash: matchHash,
        home_team,
        away_team,
        raw_url: url,
        country
      };
    } catch (error) {
      return null;
    }
  }
  
  /**
   * 生成URL hash
   * @private
   */
  static _generateHash(url) {
    // 使用URL的最后部分作为hash
    const parts = url.split('/');
    const relevant = parts.slice(-3).join('/');
    
    // 简单的hash生成 (生产环境应使用SHA-256)
    let hash = 0;
    for (let i = 0; i < relevant.length; i++) {
      const char = relevant.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32bit integer
    }
    return Math.abs(hash).toString(16);
  }
  
  /**
   * 构建完整的OddsPortal URL
   * @param {string} league - 联赛名称
   * @param {string} season - 赛季 (如 2023/2024)
   * @param {string} homeTeam - 主队
   * @param {string} awayTeam - 客队
   * @returns {string} 完整URL
   */
  static buildURL(league, season, homeTeam, awayTeam) {
    const leaguePath = HARVESTER_CONFIG.LEAGUE_URLS[league];
    if (!leaguePath) {
      throw new Error(`未知联赛: ${league}`);
    }
    
    // 赛季格式转换: 2023/2024 -> 2023-2024
    const seasonFormatted = season ? season.replace('/', '-') : '';
    const teamsFormatted = `${homeTeam} - ${awayTeam}`.replace(/ /g, '-');
    
    return `${HARVESTER_CONFIG.BASE_URL}${leaguePath}${seasonFormatted}/${teamsFormatted}`;
  }
}

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
      const path = require('path');
      this.config.SESSION_DIR = path.join(process.cwd(), 'data/sessions');
      this.config.OUTPUT_DIR = path.join(process.cwd(), 'data/oddsportal');
    }

    this.browser = null;
    this.context = null;
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
    
    // 尝试加载预热会话
    let warmedSession = null;
    if (HARVESTER_CONFIG.USE_WARMED_SESSION) {
      const sessionPath = path.join(this.config.SESSION_DIR, HARVESTER_CONFIG.SESSION_FILE);
      try {
        const sessionData = await fs.readFile(sessionPath, 'utf-8');
        warmedSession = JSON.parse(sessionData);
        console.log(`   📁 加载预热会话: ${HARVESTER_CONFIG.SESSION_FILE}`);
        console.log(`   🍪 Cookies: ${warmedSession.cookies?.length || 0} 个`);
      } catch (e) {
        console.log('   ⚠️  未找到预热会话，将使用新会话');
      }
    }
    
    // 随机化 viewport (常见桌面分辨率)
    const viewports = [
      { width: 1920, height: 1080 },
      { width: 1366, height: 768 },
      { width: 1440, height: 900 },
      { width: 1536, height: 864 },
      { width: 1280, height: 720 }
    ];
    this.stealthViewport = viewports[Math.floor(Math.random() * viewports.length)];
    
    // 随机化 User-Agent (最新版 Chrome on Windows)
    const userAgents = [
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
      'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0'
    ];
    this.stealthUserAgent = userAgents[Math.floor(Math.random() * userAgents.length)];
    
    console.log(`   🎭 Viewport: ${this.stealthViewport.width}x${this.stealthViewport.height}`);
    console.log(`   🎭 User-Agent: ${this.stealthUserAgent.substring(0, 60)}...`);
    
    // V6.0 HOST-FORCE-UP: 支持宿主机可见模式
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
    
    // 构建上下文配置
    const contextConfig = {
      viewport: this.stealthViewport,
      userAgent: this.stealthUserAgent,
      locale: 'en-US',
      timezoneId: 'America/New_York',
      bypassCSP: true,
      javaScriptEnabled: true
    };
    
    // 如果有预热会话，添加 storageState
    if (warmedSession) {
      contextConfig.storageState = warmedSession;
      console.log('   ✅ 已加载预热会话状态');
    }
    
    this.context = await this.browser.newContext(contextConfig);
    
    // 注入 V6.0 深度 stealth 脚本 - 极限指纹伪装
    const webglFingerprint = this._generateWebGLFingerprint();
    
    await this.context.addInitScript((fingerprint) => {
      // 1. 抹除 webdriver 特征
      Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
      });
      
      // 2. 伪装 languages - 为每个代理生成独特语言组合
      Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en', 'es-419', 'es']
      });
      
      // 3. 深度伪装 plugins (带详细属性)
      const createFakePlugins = () => {
        const plugins = [
          {
            name: 'Chrome PDF Plugin',
            filename: 'internal-pdf-viewer',
            description: 'Portable Document Format plugin',
            version: 'undefined',
            length: 2,
            item: (idx) => plugins[0],
            namedItem: (name) => plugins[0]
          },
          {
            name: 'Native Client',
            filename: 'native_client.dll',
            description: 'Native Client module',
            version: 'undefined',
            length: 2,
            item: (idx) => plugins[1],
            namedItem: (name) => plugins[1]
          },
          {
            name: 'Widevine Content Decryption Module',
            filename: 'widevinecdmadapter.dll',
            description: 'Widevine Content Decryption Module',
            version: 'undefined',
            length: 0,
            item: (idx) => null,
            namedItem: (name) => null
          }
        ];
        plugins.length = 3;
        plugins.item = (idx) => plugins[idx];
        plugins.namedItem = (name) => plugins.find(p => p.name === name);
        return plugins;
      };
      
      Object.defineProperty(navigator, 'plugins', {
        get: createFakePlugins
      });
      
      // 4. 伪装 mimeTypes
      Object.defineProperty(navigator, 'mimeTypes', {
        get: () => [
          { type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format', enabledPlugin: navigator.plugins[0] },
          { type: 'application/x-google-chrome-pdf', suffixes: 'pdf', description: 'Portable Document Format', enabledPlugin: navigator.plugins[0] },
          { type: 'application/x-nacl', suffixes: '', description: 'Native Client executable', enabledPlugin: navigator.plugins[1] }
        ]
      });
      
      // 5. WebGL 指纹伪装 - 每个代理独特
      const getParameter = WebGLRenderingContext.prototype.getParameter;
      WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) { // UNMASKED_VENDOR_WEBGL
          return fingerprint.vendor;
        }
        if (parameter === 37446) { // UNMASKED_RENDERER_WEBGL
          return fingerprint.renderer;
        }
        return getParameter(parameter);
      };
      
      // 6. Canvas 指纹噪声
      const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
      const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;
      
      HTMLCanvasElement.prototype.toDataURL = function(type) {
        // 添加微小噪声到canvas
        const ctx = this.getContext('2d');
        if (ctx) {
          const imageData = ctx.getImageData(0, 0, this.width, this.height);
          const data = imageData.data;
          // 修改像素增加唯一性
          for (let i = 0; i < data.length; i += 4) {
            data[i] = data[i] ^ (fingerprint.seed & 0xFF);
          }
          ctx.putImageData(imageData, 0, 0);
        }
        return originalToDataURL.call(this, type);
      };
      
      // 7. 完整的 chrome 对象
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
      
      // 8. 伪装 Notification 权限
      const originalQuery = window.navigator.permissions.query;
      window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications'
          ? Promise.resolve({ state: Notification.permission })
          : originalQuery(parameters)
      );
      
      // 9. 抹除 Playwright 特有的特征
      delete navigator.__proto__.webdriver;
      
      // 10. 伪装 deviceMemory 和 hardwareConcurrency
      Object.defineProperty(navigator, 'deviceMemory', {
        get: () => 8
      });
      Object.defineProperty(navigator, 'hardwareConcurrency', {
        get: () => 8
      });
      
    }, webglFingerprint);
    
    // 9900X多Worker初始化
    for (let i = 0; i < this.config.MAX_WORKERS; i++) {
      this.workers.push({
        id: i,
        page: null,
        busy: false,
        stats: { requests: 0, errors: 0 }
      });
    }
    
    this.stats.startTime = Date.now();
    console.log(`✅ V6.0 Harvester 初始化完成 | Workers: ${this.config.MAX_WORKERS}`);
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
    const worker = await this._waitForWorker();
    worker.busy = true;
    
    try {
      if (!worker.page) {
        worker.page = await this.context.newPage();
      }
      
      // 导航到页面
      await worker.page.goto(matchURL, {
        waitUntil: 'networkidle',
        timeout: this.config.PAGE_TIMEOUT
      });
      
      // 等待内容加载
      await worker.page.waitForSelector('body', { timeout: 5000 });
      
      // 提取URL hash
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
    // 延迟初始化
    if (!this.browser) {
      await this.initialize();
    }
    
    const worker = await this._waitForWorker();
    worker.busy = true;
    
    try {
      if (!worker.page) {
        worker.page = await this.context.newPage();
      }
      
      console.log(`🔍 Harvester 正在抓取: ${url}`);
      
      // 设置更长的超时
      worker.page.setDefaultTimeout(60000);
      worker.page.setDefaultNavigationTimeout(60000);
      
      // V6.0 ULTIMATE-FOCUS: API深度侦听升级
      console.log('   🎧 Setting up API interception...');
      const interceptedOddsData = { apiData: null, source: null };
      
      await worker.page.route('**/*', async (route, request) => {
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
      
      // V6.0 STEALTH: 先访问联赛列表页作为 referer
      const refererUrl = 'https://www.oddsportal.com/soccer/england/premier-league/';
      try {
        await worker.page.goto(refererUrl, { waitUntil: 'domcontentloaded', timeout: 10000 });
        await worker.page.waitForTimeout(1000 + Math.floor(Math.random() * 1000));
      } catch (e) {
        // referer 访问失败不影响主流程
      }
      
      // 导航到目标页面 - 使用 referer
      const response = await worker.page.goto(url, {
        waitUntil: 'domcontentloaded',
        timeout: 60000,
        referer: refererUrl
      });
      
      // V6.0 ACTION MIMICRY: 模拟人类阅读节奏
      // 等待页面基础渲染
      await worker.page.waitForTimeout(2000);
      
      // 模拟鼠标移动到赔率区域
      try {
        const oddsSelectors = ['.odds', '[data-testid="odds"]', '.price', 'div[class*="odd"]'];
        for (const selector of oddsSelectors) {
          const element = await worker.page.$(selector);
          if (element) {
            const box = await element.boundingBox();
            if (box) {
              // 人类化移动：先快速接近，再微调
              await worker.page.mouse.move(
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
          await worker.page.waitForSelector(selector, { 
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
          await worker.page.reload({ waitUntil: 'domcontentloaded', timeout: 30000 });
          await worker.page.waitForTimeout(3000);
          
          // 再次尝试等待
          for (const selector of oddsSelectors) {
            try {
              await worker.page.waitForSelector(selector, { 
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
      const pageUrl = worker.page.url();
      
      // 检查响应状态
      if (!response) {
        throw new Error('页面导航失败: 无响应');
      }
      
      console.log(`   📄 Response Status: ${response.status()}`);
      console.log(`   📄 Final URL: ${pageUrl}`);
      
      // V6.0 反爬检测：检查页面标题
      const pageTitle = await worker.page.title();
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
      await worker.page.evaluate(() => {
        window.scrollBy({ top: 100 + Math.floor(Math.random() * 150), behavior: 'smooth' });
      });
      await worker.page.waitForTimeout(800 + Math.floor(Math.random() * 700));
      
      // 第2次滚动：回到顶部附近
      await worker.page.evaluate(() => {
        window.scrollBy({ top: -(50 + Math.floor(Math.random() * 80)), behavior: 'smooth' });
      });
      await worker.page.waitForTimeout(600 + Math.floor(Math.random() * 500));
      
      // 第3次滚动：向下阅读赔率区域
      await worker.page.evaluate(() => {
        window.scrollBy({ top: 200 + Math.floor(Math.random() * 200), behavior: 'smooth' });
      });
      await worker.page.waitForTimeout(1000 + Math.floor(Math.random() * 1000));
      
      // 最终停顿：模拟阅读赔率
      const readingTime = 1500 + Math.floor(Math.random() * 1500);
      console.log(`   ⏱️  Reading time: ${readingTime}ms`);
      await worker.page.waitForTimeout(readingTime);
      
      // V6.0 ULTIMATE-FOCUS: 超频动态等待与深度侦听
      console.log('   🔍 Ultimate focus rendering check...');
      
      // 延长基础等待时间至20s（给予本地JS充分渲染时间）
      const baseWaitTime = 20000;
      console.log(`   ⏱️  Base wait time: ${baseWaitTime}ms (Overclocked)`);
      await worker.page.waitForTimeout(baseWaitTime);
      
      // 智能钩子：等待1X2表格出现且包含小数赔率
      console.log('   ⏳ Waiting for 1X2 odds table...');
      let oddsTableFound = false;
      
      try {
        await worker.page.waitForFunction(() => {
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
        return await worker.page.evaluate(() => {
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
            const element = await worker.page.$(selector);
            if (element) {
              await element.click();
              console.log(`   ✅ Clicked: ${selector}`);
              break;
            }
          }
          
          await worker.page.waitForTimeout(5000);
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
        const oddsWrapContent = await worker.page.evaluate(() => {
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
          await worker.page.mouse.wheel(0, 500);
          await worker.page.waitForTimeout(2000);
          
          // 再次尝试小幅度滚动
          await worker.page.mouse.wheel(0, -200);
          await worker.page.waitForTimeout(1500);
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
      await worker.page.waitForTimeout(2000);
      
      const screenshotDir = '/app/data/screenshots';
      await fs.mkdir(screenshotDir, { recursive: true }).catch(() => {});
      const timestamp = Date.now();
      let screenshotPath = path.join(screenshotDir, `match_${timestamp}.png`);
      let screenshotSize = 0;
      let screenshotAttempts = 0;
      const maxScreenshotAttempts = 3;
      
      while (screenshotAttempts < maxScreenshotAttempts) {
        screenshotAttempts++;
        
        try {
          await worker.page.screenshot({ 
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
                await worker.page.mouse.wheel(0, 1000);
                await worker.page.waitForTimeout(3000);
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
      
      // V6.0 DEEP-PARSE: 深度解析API数据提取全维度赔率
      let odds = {};
      let oddsSource = 'unknown';
      let deepParseData = null;
      
      if (interceptedOddsData.apiData) {
        console.log('   💰 V6.0 DEEP-PARSE: Analyzing API payload structure...');
        
        // V6.0 DEEP-PARSE V2: 深度解析引擎
        deepParseData = this._deepParseOddsData(interceptedOddsData.apiData);
        
        if (deepParseData && deepParseData.closing_odds) {
          odds = {
            '1x2': deepParseData.closing_odds,
            opening: deepParseData.opening_odds,
            closing: deepParseData.closing_odds,
            curve: deepParseData.movement_curve,
            bookmakers: deepParseData.bookmakers,
            _source: 'api_deep_parse_v2',
            _parseVersion: 'V6.0-DEEP-PARSE',
            _apiUrl: interceptedOddsData.apiUrl
          };
          oddsSource = 'api_deep_parse_v2';
          
          console.log(`   ✅ DEEP-PARSE extracted:`);
          console.log(`      Closing: ${deepParseData.closing_odds.join(' | ')}`);
          if (deepParseData.opening_odds) {
            console.log(`      Opening: ${deepParseData.opening_odds.join(' | ')}`);
          }
          if (deepParseData.movement_curve) {
            console.log(`      Curve points: ${deepParseData.movement_curve.length}`);
          }
          if (deepParseData.bookmakers) {
            console.log(`      Bookmakers: ${Object.keys(deepParseData.bookmakers).join(', ')}`);
          }
        } else {
          // 回退到基础提取
          console.log('   ⚠️  DEEP-PARSE failed, falling back to basic extraction');
          const apiData = interceptedOddsData.apiData;
          let extractedOdds = null;
          
          if (apiData.odds && apiData.odds['1x2']) {
            extractedOdds = apiData.odds['1x2'];
          } else if (apiData.data && apiData.data.odds && apiData.data.odds['1x2']) {
            extractedOdds = apiData.data.odds['1x2'];
          }
          
          if (extractedOdds && extractedOdds.length === 3) {
            odds = {
              '1x2': extractedOdds.map(o => typeof o === 'number' ? o.toFixed(2) : o),
              _source: 'api_interception',
              _apiUrl: interceptedOddsData.apiUrl
            };
            oddsSource = 'api_interception';
            console.log(`   ✅ API odds extracted: ${odds['1x2'].join(' | ')}`);
          }
        }
      }
      
      // V6.0 API-EXCAVATOR: DOM Sniper 模式（API失败后启动）
      if (!odds['1x2'] && deepParseData && deepParseData._source === 'BOOKIE_NOT_FOUND') {
        console.log('   🎯 DOM Sniper: API extraction failed, starting sniper mode...');
        
        // 尝试点击 "All Bookmakers" 或展开更多博彩公司
        try {
          const allBookmakersSelectors = [
            'text=All Bookmakers',
            'text=Show all',
            'text=More bookies',
            '[data-testid="all-bookmakers"]',
            'button:has-text("All")',
            '.bookmakers-toggle'
          ];
          
          for (const selector of allBookmakersSelectors) {
            const btn = await worker.page.$(selector);
            if (btn) {
              await btn.click();
              console.log(`   🎯 DOM Sniper: Clicked "${selector}"`);
              await worker.page.waitForTimeout(3000);
              break;
            }
          }
        } catch (e) {
          // 忽略点击错误
        }
        
        // 狙击Pinnacle行
        const sniperResult = await worker.page.evaluate(() => {
          const result = { pinnacle: null, bet365: null };
          
          // 搜索包含Pinnacle或Bet365的表格行
          const rows = document.querySelectorAll('tr, .row, .bookmaker-row, [class*="bookmaker"]');
          
          for (const row of rows) {
            const text = row.innerText || row.textContent || '';
            const lowerText = text.toLowerCase();
            
            // 提取赔率数值（支持多种格式）
            const extractOdds = (rowElement) => {
              const oddsElements = rowElement.querySelectorAll('.odds, .odds-wrap, .price, [class*="odd"], .value');
              const values = [];
              
              for (const el of oddsElements) {
                const val = el.textContent?.trim() || el.innerText?.trim();
                if (val) {
                  // 清洗数据（如 "1.85 >" 提取1.85）
                  const match = val.match(/(\d+\.\d{2,3})/);
                  if (match) values.push(match[1]);
                }
              }
              
              return values.length >= 3 ? values.slice(0, 3) : null;
            };
            
            // 狙击Pinnacle
            if (lowerText.includes('pinnacle') && !result.pinnacle) {
              const odds = extractOdds(row);
              if (odds) {
                result.pinnacle = {
                  name: 'Pinnacle',
                  closing: odds,
                  source: 'dom_sniper'
                };
              }
            }
            
            // 狙击Bet365
            if ((lowerText.includes('bet365') || lowerText.includes('365')) && !result.bet365) {
              const odds = extractOdds(row);
              if (odds) {
                result.bet365 = {
                  name: 'Bet365',
                  closing: odds,
                  source: 'dom_sniper'
                };
              }
            }
          }
          
          return result;
        });
        
        // 使用狙击结果
        if (sniperResult.pinnacle || sniperResult.bet365) {
          console.log('   🎯 DOM Sniper: Targets acquired!');
          
          odds = {
            _source: 'dom_sniper',
            _sniperMode: true
          };
          
          if (sniperResult.pinnacle) {
            odds['1x2'] = sniperResult.pinnacle.closing;
            odds.pinnacle_odds = { closing: sniperResult.pinnacle.closing };
            odds._bookieStatus = { hasPinnacle: true };
            console.log(`      Pinnacle: ${sniperResult.pinnacle.closing.join(' | ')}`);
          }
          
          if (sniperResult.bet365) {
            odds.bet365_odds = { closing: sniperResult.bet365.closing };
            odds._bookieStatus = odds._bookieStatus || {};
            odds._bookieStatus.hasBet365 = true;
            console.log(`      Bet365: ${sniperResult.bet365.closing.join(' | ')}`);
          }
        } else {
          console.log('   🎯 DOM Sniper: No targets found');
        }
      }
      
      // 如果API拦截和Sniper都失败，从页面常规提取赔率数据
      if (!odds['1x2']) {
        console.log('   🔍 Extracting odds from DOM (standard mode)...');
        odds = await worker.page.evaluate(() => {
          const oddsData = {};
        
        // 方式1: 从页面script标签中的 JSON 数据提取
        try {
          const scripts = document.querySelectorAll('script');
          for (const script of scripts) {
            const text = script.textContent || '';
            // 查找包含 odds 的 JSON 数据
            if (text.includes('"odds"') || text.includes('"initialOdds"') || text.includes('"fullTime"')) {
              try {
                // 尝试多种正则匹配模式
                const patterns = [
                  /"odds"\s*:\s*(\{[^}]+\})/,
                  /"initialOdds"\s*:\s*(\{[^}]+\})/,
                  /"fullTime"\s*:\s*(\[[^\]]+\])/
                ];
                
                for (const pattern of patterns) {
                  const match = text.match(pattern);
                  if (match) {
                    const parsed = JSON.parse(match[1]);
                    if (parsed['1x2'] || parsed.fullTime || (Array.isArray(parsed) && parsed.length === 3)) {
                      oddsData['1x2'] = parsed['1x2'] || parsed.fullTime || parsed;
                      oddsData._source = 'script_json';
                      break;
                    }
                  }
                }
              } catch (e) {
                // 继续尝试其他方式
              }
            }
          }
        } catch (e) {
          console.log('Script extraction failed:', e.message);
        }
        
        // 方式2: 从DOM中提取显示的赔率
        if (!oddsData['1x2']) {
          try {
            // 多种选择器尝试
            const selectors = [
              '[data-testid*="odd"]',
              '.odds',
              '.odds-value', 
              '.price',
              '.flex-center.height-100',
              '[class*="odd"]',
              'div[title]'
            ];
            
            for (const selector of selectors) {
              const elements = document.querySelectorAll(selector);
              const values = Array.from(elements)
                .map(el => el.textContent?.trim())
                .filter(text => text && /^\d+\.\d+$/.test(text))
                .map(text => parseFloat(text))
                .filter(num => num > 1 && num < 100);
              
              if (values.length >= 3) {
                oddsData['1x2'] = values.slice(0, 3).map(v => v.toFixed(2));
                oddsData._source = 'dom_' + selector;
                break;
              }
            }
          } catch (e) {
            console.log('DOM extraction failed:', e.message);
          }
        }
        
        // 方式3: 从页面文本中提取数字（最后的尝试）
        if (!oddsData['1x2']) {
          try {
            const bodyText = document.body?.innerText || '';
            const numberPattern = /\b(\d+\.\d{2})\b/g;
            const numbers = [];
            let match;
            while ((match = numberPattern.exec(bodyText)) !== null) {
              const num = parseFloat(match[1]);
              if (num > 1.01 && num < 100) {
                numbers.push(match[1]);
              }
            }
            if (numbers.length >= 3) {
              oddsData['1x2'] = numbers.slice(0, 3);
              oddsData._source = 'text_extract';
            }
          } catch (e) {
            console.log('Text extraction failed:', e.message);
          }
        }
        
        // 添加页面诊断信息
        oddsData._diagnostic = {
          title: document.title,
          url: window.location.href,
          bodyTextLength: document.body?.innerText?.length || 0,
          hasBody: !!document.body,
          timestamp: new Date().toISOString()
        };
        
        return oddsData;
      });
      
      } // 关闭 if (!odds['1x2'])
      
      // 如果DOM提取成功，更新来源标记
      if (odds._source && odds._source.startsWith('dom_')) {
        oddsSource = 'dom_rendered';
      } else if (odds._source === 'api_interception') {
        oddsSource = 'api_interception';
      }
      
      // V6.0 SIGHT-RESTORE: 获取完整页面HTML用于验证
      const rawHtml = await worker.page.content();
      
      // 提取URL hash
      const parsed = OddsPortalURLParser.parseMatchURL(url);
      
      worker.stats.requests++;
      this.stats.matchesHarvested++;
      
      // V3 PRECISION-LOCK: 构建严格的market_sentiment数据结构
      const marketSentiment = {
        match_id: parsed?.match_hash || null,
        oddsportal_url: url,
        oddsportal_hash: parsed?.match_hash,
        extract_method: 'V6.0-PRECISION-LOCK-V3',
        extracted_at: new Date().toISOString(),
        
        // V3: 独立博彩公司字段 (严格白名单: Pinnacle > Bet365)
        pinnacle_odds: deepParseData?.pinnacle_odds || odds.pinnacle_odds || null,
        bet365_odds: deepParseData?.bet365_odds || odds.bet365_odds || null,
        
        // V3: 博彩公司状态标记
        _bookieStatus: deepParseData?._bookieStatus || { hasPinnacle: false, hasBet365: false },
        
        // 初盘/终盘数据 (优先使用Pinnacle，其次Bet365)
        opening_odds: odds.opening || null,
        closing_odds: odds.closing || odds['1x2'] || null,
        opening_at: odds.timestamps?.opening_at || null,
        closing_at: odds.timestamps?.closing_at || new Date().toISOString(),
        
        // 变盘曲线
        movement_curve: odds.curve || [],
        volatility: this._calculateVolatility(odds.opening, odds.closing || odds['1x2']),
        
        // 博彩公司数据 (V3: 仅包含白名单数据，无Average)
        bookmakers: deepParseData ? {
          ...(deepParseData.pinnacle_odds && { pinnacle: deepParseData.pinnacle_odds }),
          ...(deepParseData.bet365_odds && { bet365: deepParseData.bet365_odds })
        } : (odds.bookmakers || {}),
        
        // 原始1X2赔率
        odds_1x2: odds['1x2'] || null,
        
        // V3: 严格白名单标记
        _whitelist: ['pinnacle', 'bet365'],
        _averageDisabled: true,
        
        // 元数据
        _source: deepParseData?._source || oddsSource,
        _parseVersion: 'V6.0-PRECISION-LOCK-V3',
        _v3Lock: true,
        _diagnostic: odds._diagnostic || {
          title: pageTitle,
          url: pageUrl,
          timestamp: new Date().toISOString()
        }
      };
      
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

  // ============================================================
  // V6.0 API-EXCAVATOR: 递归挖掘算法
  // ============================================================

  /**
   * V6.0 API-EXCAVATOR: 递归深度搜索对象中的所有值
   * @deprecated 已迁移至 OddsPortalParser.findValuesByKey
   */
  _findValuesByKey(obj, targetKeys, results = [], maxDepth = 10, currentDepth = 0) {
    // V6.0 SURGICAL-SPLIT: 委托给模块化实现
    return findValuesByKey(obj, targetKeys, results, maxDepth, currentDepth);
  }



  /**
   * V6.0 API-EXCAVATOR: 递归查找博彩公司数据
   * @param {Object} obj - API返回的对象
   * @param {string} bookieKey - 'pinnacle' 或 'bet365'
   * @returns {Object|null} 博彩公司数据
   */
  /**
   * V6.0 API-EXCAVATOR: 递归查找博彩公司数据
   * @deprecated 已迁移至 OddsPortalParser.findBookieById
   */
  _findBookieById(obj, bookieKey) {
    // V6.0 SURGICAL-SPLIT: 委托给模块化实现
    return findBookieById(obj, bookieKey);
  }



  /**
   * V6.0 API-EXCAVATOR: 提取历史数据（变盘曲线）
   * @param {Object} bookieData - 博彩公司数据
   * @returns {Array} 变盘曲线数组
   */
  _extractHistoryCurve(bookieData) {
    if (!bookieData || typeof bookieData !== 'object') return [];

    const historyData = [];

    // 搜索所有可能的history字段
    const historyResults = this._findValuesByKey(bookieData, ODDS_FIELD_PATTERNS.HISTORY);
    
    for (const result of historyResults) {
      const history = result.value;
      if (!Array.isArray(history)) continue;

      for (const point of history) {
        if (!point || typeof point !== 'object') continue;

        // 提取时间戳
        let timestamp = null;
        for (const tsKey of ODDS_FIELD_PATTERNS.TIMESTAMP) {
          if (point[tsKey] !== undefined) {
            timestamp = point[tsKey];
            break;
          }
        }

        // 提取赔率 (支持多种格式)
        let home, draw, away;
        
        if (point.odds && Array.isArray(point.odds)) {
          [home, draw, away] = point.odds;
        } else if (point.values && Array.isArray(point.values)) {
          [home, draw, away] = point.values;
        } else {
          home = point.home || point[0] || point.h || point.homeOdds;
          draw = point.draw || point[1] || point.d || point.drawOdds;
          away = point.away || point[2] || point.a || point.awayOdds;
        }

        // 清洗数据（处理带趋势符号的字符串如 "1.85 > 1.83"）
        const cleanOdds = (val) => {
          if (val === undefined || val === null) return null;
          const str = String(val);
          // 提取第一个数字
          const match = str.match(/(\d+\.?\d*)/);
          return match ? parseFloat(match[1]).toFixed(2) : null;
        };

        home = cleanOdds(home);
        draw = cleanOdds(draw);
        away = cleanOdds(away);

        if (home && draw && away) {
          historyData.push({
            timestamp: timestamp || Date.now(),
            home,
            draw,
            away
          });
        }
      }
    }

    // 按时间戳排序
    return historyData.sort((a, b) => {
      const ta = typeof a.timestamp === 'number' ? a.timestamp : new Date(a.timestamp).getTime();
      const tb = typeof b.timestamp === 'number' ? b.timestamp : new Date(b.timestamp).getTime();
      return ta - tb;
    });
  }

  /**
   * V6.0 API-EXCAVATOR: 标准化赔率数组
   * @param {*} odds - 赔率数据（可能是数组或对象）
   * @returns {Array|null} 标准化的赔率数组 [home, draw, away]
   */
  _normalizeOddsArray(odds) {
    if (!odds) return null;

    // 如果是数组
    if (Array.isArray(odds)) {
      if (odds.length >= 3) {
        return odds.slice(0, 3).map(o => {
          const val = typeof o === 'number' ? o : parseFloat(String(o).replace(/[^\d.]/g, ''));
          return isNaN(val) ? null : val.toFixed(2);
        });
      }
      return null;
    }

    // 如果是对象，尝试提取
    if (typeof odds === 'object') {
      const home = odds.home || odds[0] || odds.h;
      const draw = odds.draw || odds[1] || odds.d;
      const away = odds.away || odds[2] || odds.a;
      
      if (home !== undefined && draw !== undefined && away !== undefined) {
        return [
          parseFloat(String(home)).toFixed(2),
          parseFloat(String(draw)).toFixed(2),
          parseFloat(String(away)).toFixed(2)
        ];
      }
    }

    return null;
  }

  /**
   * V6.0 DEEP-PARSE V3 API-EXCAVATOR: 深度解析赔率数据
   * @param {Object} apiData - API返回的原始数据
   * @returns {Object} 解析后的全维度赔率数据
   * @deprecated 已迁移至 OddsPortalParser.deepParseOddsData
   */
  _deepParseOddsData(apiData) {
    // V6.0 SURGICAL-SPLIT: 委托给模块化实现
    return deepParseOddsData(apiData);
  }



  /**
   * V3 PRECISION-LOCK: 严格白名单提取 (仅 Pinnacle > Bet365)
        
        // 检查odds嵌套结构
        if (data.odds && data.odds['1x2']) {
          result.closing_odds = data.odds['1x2'].map(o => 
            typeof o === 'number' ? o.toFixed(2) : o
          );
        }
      }

      // 策略3: 直接odds结构
      if (!result.closing_odds && apiData.odds) {
        if (apiData.odds['1x2'] && Array.isArray(apiData.odds['1x2'])) {
          result.closing_odds = apiData.odds['1x2'].map(o => 
            typeof o === 'number' ? o.toFixed(2) : o
          );
        }
      }

      // 策略4: fullTime结构
      if (!result.closing_odds && apiData.fullTime && Array.isArray(apiData.fullTime)) {
        result.closing_odds = apiData.fullTime.map(o => 
          typeof o === 'number' ? o.toFixed(2) : o
        );
      }

      // 策略5: 时间戳提取
      if (apiData.timestamp || apiData.dat_h || apiData.lastUpdated) {
        result.timestamps.closing_at = apiData.timestamp || apiData.dat_h || apiData.lastUpdated;
      }

      // 策略6: 历史数据提取 (movement curve)
      if (apiData.history || apiData.movement || apiData.timeline) {
        const historyData = apiData.history || apiData.movement || apiData.timeline;
        if (Array.isArray(historyData)) {
          result.movement_curve = historyData.map(point => ({
            timestamp: point.timestamp || point.time || point.dat_h,
            home: point.home || point[0],
            draw: point.draw || point[1],
            away: point.away || point[2]
          }));
          
          // 从历史中提取初盘 (第一个点)
          if (historyData.length > 0 && !result.opening_odds) {
            const firstPoint = historyData[0];
            result.opening_odds = [
              (firstPoint.home || firstPoint[0]).toFixed(2),
              (firstPoint.draw || firstPoint[1]).toFixed(2),
              (firstPoint.away || firstPoint[2]).toFixed(2)
            ];
          }
        }
      }

      return result;
    } catch (e) {
      console.log('   ⚠️  DEEP-PARSE error:', e.message);
      return null;
    }
  }

  /**
   * V3 PRECISION-LOCK: 严格白名单提取 (仅 Pinnacle > Bet365)
   * @param {Array} bookmakers - 博彩公司数组
   * @param {Object} result - 结果对象
   * @returns {Object} 包含独立 pinnacle_odds 和 bet365_odds 的对象
   */
  _extractBookmakerData(bookmakers, result) {
    // V3: 严格白名单 - 只认 Pinnacle 和 Bet365，禁用所有平均值
    const whitelist = [
      { pattern: /pinnacle/i, key: 'pinnacle', priority: 1 },
      { pattern: /bet365/i, key: 'bet365', priority: 2 }
    ];

    // 初始化独立字段
    result.pinnacle_odds = null;
    result.bet365_odds = null;
    result._bookieStatus = { hasPinnacle: false, hasBet365: false };

    // 遍历所有博彩公司
    for (const bm of bookmakers) {
      const bmName = (bm.name || bm.bookie || bm.provider || '').toLowerCase();
      
      for (const whitelistItem of whitelist) {
        if (whitelistItem.pattern.test(bmName)) {
          const oddsData = { opening: null, closing: null, history: [] };
          
          // 提取终盘 (closing)
          if (bm.odds || bm.current || bm.values || bm.closing) {
            const odds = bm.odds || bm.current || bm.values || bm.closing;
            if (Array.isArray(odds) && odds.length >= 3) {
              oddsData.closing = odds.slice(0, 3).map(o => 
                typeof o === 'number' ? o.toFixed(2) : String(o)
              );
            }
          }

          // 提取初盘 (opening)
          if (bm.opening || bm.initial || bm.start || bm.open) {
            const opening = bm.opening || bm.initial || bm.start || bm.open;
            if (Array.isArray(opening) && opening.length >= 3) {
              oddsData.opening = opening.slice(0, 3).map(o => 
                typeof o === 'number' ? o.toFixed(2) : String(o)
              );
            }
          }

          // 提取历史数据 (history/curve)
          if (bm.history || bm.movement || bm.timeline || bm.changes) {
            const history = bm.history || bm.movement || bm.timeline || bm.changes;
            if (Array.isArray(history)) {
              oddsData.history = history.map(point => ({
                timestamp: point.timestamp || point.time || point.dat_h || point.t,
                home: String(point.home || point[0] || point.h),
                draw: String(point.draw || point[1] || point.d),
                away: String(point.away || point[2] || point.a)
              })).filter(p => p.home && p.draw && p.away);
            }
          }

          // 保存到独立字段
          if (whitelistItem.key === 'pinnacle') {
            result.pinnacle_odds = oddsData;
            result._bookieStatus.hasPinnacle = !!(oddsData.closing || oddsData.opening);
            // 优先使用 Pinnacle 作为终盘
            if (oddsData.closing) {
              result.closing_odds = oddsData.closing;
              result._source = 'pinnacle';
            }
            if (oddsData.opening) {
              result.opening_odds = oddsData.opening;
            }
            console.log(`   🔒 V3 LOCK: Pinnacle extracted - Closing: ${oddsData.closing?.join('|') || 'N/A'}`);
          } else if (whitelistItem.key === 'bet365') {
            result.bet365_odds = oddsData;
            result._bookieStatus.hasBet365 = !!(oddsData.closing || oddsData.opening);
            // Bet365 作为次选
            if (oddsData.closing && !result.closing_odds) {
              result.closing_odds = oddsData.closing;
              result._source = 'bet365';
            }
            if (oddsData.opening && !result.opening_odds) {
              result.opening_odds = oddsData.opening;
            }
            console.log(`   🔒 V3 LOCK: Bet365 extracted - Closing: ${oddsData.closing?.join('|') || 'N/A'}`);
          }
        }
      }
    }

    // V3: 熔断逻辑 - 检查是否找到目标博彩公司
    if (!result._bookieStatus.hasPinnacle && !result._bookieStatus.hasBet365) {
      console.log('   🚫 V3 LOCK: BOOKIE_NOT_FOUND - No Pinnacle or Bet365 data');
      result._source = 'BOOKIE_NOT_FOUND';
    } else {
      const found = [];
      if (result._bookieStatus.hasPinnacle) found.push('Pinnacle');
      if (result._bookieStatus.hasBet365) found.push('Bet365');
      console.log(`   ✅ V3 LOCK: Bookies found - ${found.join(' + ')}`);
    }

    return result;
  }

  /**
   * 计算赔率波动率
   * @param {Array} opening - 初盘赔率 [home, draw, away]
   * @param {Array} closing - 终盘赔率 [home, draw, away]
   * @returns {Object} 波动率统计
   */
  _calculateVolatility(opening, closing) {
    if (!opening || !closing || opening.length !== 3 || closing.length !== 3) {
      return null;
    }

    try {
      const o = opening.map(x => parseFloat(x));
      const c = closing.map(x => parseFloat(x));

      // 计算每个结果的赔率变化百分比
      const changes = [
        ((c[0] - o[0]) / o[0]) * 100,  // Home change %
        ((c[1] - o[1]) / o[1]) * 100,  // Draw change %
        ((c[2] - o[2]) / o[2]) * 100   // Away change %
      ];

      // 计算平均绝对波动率
      const avgVolatility = (Math.abs(changes[0]) + Math.abs(changes[1]) + Math.abs(changes[2])) / 3;

      // 计算最大波动
      const maxChange = Math.max(...changes.map(Math.abs));

      return {
        home_change_pct: changes[0].toFixed(2),
        draw_change_pct: changes[1].toFixed(2),
        away_change_pct: changes[2].toFixed(2),
        avg_volatility_pct: avgVolatility.toFixed(2),
        max_change_pct: maxChange.toFixed(2),
        direction: changes[0] < 0 ? 'home_favored' : changes[0] > 0 ? 'home_against' : 'stable'
      };
    } catch (e) {
      return null;
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
    
    // 关闭所有Worker页面
    for (const worker of this.workers) {
      if (worker.page) {
        await worker.page.close();
      }
    }
    
    if (this.context) {
      await this.context.close();
    }
    
    if (this.browser) {
      await this.browser.close();
    }
    
    console.log('✅ Harvester 已关闭');
  }
}

// V6.0 SURGICAL-SPLIT: DEPRECATED ZONE 已清理
// 所有过时代码已物理删除，功能已迁移至：
// - StealthNavigator.js (战术操纵模块)
// - OddsPortalParser.js (情报解析模块)

// 导出模块
module.exports = {
  OddsPortalHarvester,
  OddsPortalURLParser,
  HARVESTER_CONFIG,
  // V6.0 SURGICAL-SPLIT: 同时导出新的子模块
  StealthNavigator: require('./StealthNavigator'),
  OddsPortalParser: require('./OddsPortalParser')
};
