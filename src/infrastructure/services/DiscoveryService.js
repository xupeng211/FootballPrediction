/**
 * @file DiscoveryService - TITAN V6.7 L1 发现引擎 (Project Hound)
 * @module infrastructure/services/DiscoveryService
 * @version V6.7.5-STEALTH-EXTRACTED
 * @description
 * 工业级赛程发现服务 - 影子浏览器版本 (完全重构)
 * 职责: 轻量级协调器，负责流程编排
 * 
 * 职责分离:
 * - 解析逻辑 -> DiscoveryParser
 * - 浏览器管理 -> BrowserProvider
 * - 网络拦截 -> NetworkInterceptor
 * - 赛季策略 -> SeasonStrategy
 * - 数据提取 -> FotMobExtractor
 * - 持久化层 -> FixtureRepository
 */

'use strict';

const { Pool } = require('pg');
const path = require('path');
const pLimit = require('p-limit');

// V6.7.6-FINAL: 引入全模块化组件
const { DiscoveryParser } = require('./DiscoveryParser');
const { BrowserProvider } = require('./BrowserProvider');
const { NetworkInterceptor } = require('./NetworkInterceptor');
const { SeasonStrategyFactory, SeasonDiscovery } = require('./SeasonStrategy');
const { FotMobExtractor } = require('./FotMobExtractor');
const { FixtureRepository } = require('./FixtureRepository');
const { HttpClient } = require('./HttpClient');
const { UIHelper } = require('./UIHelper');
const { L1ConfigManager } = require('./L1ConfigManager');

require('dotenv').config({ path: path.resolve(__dirname, '../../../.env') });

/**
 * L1 发现服务 (Project Hound)
 * @class DiscoveryService
 */
class DiscoveryService {
  constructor(config = {}) {
    const {
      dbPool,
      configManager,
      parser,
      browserProvider,
      networkInterceptor,
      seasonStrategyFactory,
      seasonDiscovery,
      extractor,
      fixtureRepository,
      httpClient,
      uiHelper,
      ...runtimeConfig
    } = config;

    this.config = {
      concurrency: 5,
      delayMs: 2000,
      batchSize: 50,
      lookbackDays: 30,
      lookaheadDays: 7,
      silent: process.env.SILENT_MODE !== 'false',
      verbose: false,
      ...runtimeConfig
    };

    this.logger = {
      info: (...args) => !this.config.silent && console.log(...args),
      warn: (...args) => console.warn(...args),
      error: (...args) => console.error(...args),
      banner: (...args) => console.log(...args),
      progress: (...args) => console.log(...args)
    };

    this.dbPool = dbPool || new Pool({
      host: process.env.DB_HOST || 'localhost',
      port: parseInt(process.env.DB_PORT || '5432'),
      database: process.env.DB_NAME || 'football_db',
      user: process.env.DB_USER || 'football_user',
      password: process.env.DB_PASSWORD || 'football_pass',
      max: 20,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 5000,
      application_name: 'discovery_service_v672'
    });

    this.limiter = pLimit(this.config.concurrency);
    this.stats = { total: 0, inserted: 0, updated: 0, failed: 0, startTime: null, criticalWarnings: [] };
    this.configManager = configManager || new L1ConfigManager({ logger: this.logger });
    this.leagueConfig = this.configManager.getRuntimeConfig();
    
    // V6.7.2: 初始化解析器
    this.parser = parser || new DiscoveryParser(this.logger, this.leagueConfig);
    
    // V6.7.4-REFACTORED: 初始化职责分离的模块
    this.browserProvider = browserProvider || new BrowserProvider({
      logger: this.logger,
      headless: true
    });
    
    this.networkInterceptor = networkInterceptor || new NetworkInterceptor({
      logger: this.logger
      // V6.7.5-EXTRACTED: 回调逻辑已移至 FotMobExtractor
    });
    
    this.seasonStrategyFactory = seasonStrategyFactory || new SeasonStrategyFactory({
      singleYearLeagues: this.configManager.getSingleYearLeagueIds()
    });
    
    this.seasonDiscovery = seasonDiscovery || new SeasonDiscovery({
      logger: this.logger,
      apiRequest: (url) => this.httpClient.request(url)
    });
    
    // V6.7.5-EXTRACTED: 初始化数据提取器
    this.extractor = extractor || new FotMobExtractor({
      logger: this.logger,
      browserProvider: this.browserProvider,
      networkInterceptor: this.networkInterceptor,
      makeStealthRequest: (url) => this.httpClient.request(url)
    });
    
    // V6.7.5-EXTRACTED: 初始化数据仓储
    this.fixtureRepository = fixtureRepository || new FixtureRepository({
      dbPool: this.dbPool,
      logger: this.logger,
      batchSize: this.config.batchSize
    });
    
    // V6.7.6-FINAL: 初始化 HTTP 客户端
    this.httpClient = httpClient || new HttpClient({
      logger: this.logger,
      browserProvider: this.browserProvider,
      useStealthMode: !process.env.DEBUG_RAW_HTTP
    });
    
    // V6.7.6-FINAL: 初始化 UI 辅助
    this.uiHelper = uiHelper || new UIHelper({ logger: this.logger });
  }

  /**
   * 初始化影子浏览器 (Stealth Mode) - V6.7.4-REFACTORED
   * 委托给 BrowserProvider 管理
   * @private
   */
  async _initBrowser() {
    if (!this.useStealthMode || this.browserProvider.isInitialized()) return;
    
    this.logger.info('[STEALTH] 🕵️  启动影子浏览器 (闪击模式)...');
    
    try {
      // 初始化浏览器
      const page = await this.browserProvider.initialize();
      
      // 设置网络拦截
      this.networkInterceptor.setup(page);
      
      // 预热页面获取 Cookies
      await this.browserProvider.warmup('https://www.fotmob.com/', {
        waitUntil: 'domcontentloaded',
        timeout: 15000
      });
      
      this.logger.info('[STEALTH] ✅ 影子浏览器就绪');
    } catch (e) {
      // 宽容模式: 即使主页加载失败，也继续尝试 API 请求
      this.logger.warn(`[STEALTH] ⚠️  主页加载警告: ${e.message}`);
      this.logger.warn('[STEALTH] 💡 继续尝试 API 请求 (Cookie 可能已获取)');
    }
  }

    /**

     * 获取捕获的 API 列表

     * V6.7.4-REFACTORED: 委托给 NetworkInterceptor

     * @returns {Map<string, Object>}

     */

    get capturedApis() {

      return this.networkInterceptor ? this.networkInterceptor.getCapturedApis() : new Map();

    }

  /**
   * 主入口: 执行发现扫描
   */
  async discover(options = {}) {
    this.stats = { total: 0, inserted: 0, updated: 0, failed: 0, startTime: Date.now(), criticalWarnings: [] };
    this.uiHelper.printBanner('V6.7.6-FINAL');

    const { leagueId, season, allLeagues = false } = options;
    const targets = this._buildTargets(leagueId, season, allLeagues);

    this.uiHelper.printTargets(targets.length);

    const results = await Promise.all(
      targets.map((target, index) =>
        this.limiter(() => this._scanLeague(target, index))
      )
    );

    results.forEach(r => {
      this.stats.total += r.total;
      this.stats.inserted += r.inserted;
      this.stats.updated += r.updated;
      this.stats.failed += r.failed;
      if (Array.isArray(r.criticalWarnings) && r.criticalWarnings.length > 0) {
        this.stats.criticalWarnings.push(...r.criticalWarnings);
      }
    });

    return this.uiHelper.generateReport(this.stats, this.stats.startTime);
  }

  /**
   * 构建扫描目标列表
   * @private
   */
  _buildTargets(leagueId, season, allLeagues) {
    if (leagueId) {
      const league = this.configManager.getLeagueById(leagueId);
      if (!league) throw new Error(`联赛 ID ${leagueId} 未找到`);
      const seasons = season ? [season] : [this.configManager.getDefaultSeason(leagueId)];
      return seasons.map(s => ({ ...league, season: s }));
    }

    const targetLeagues = allLeagues
      ? this.configManager.getActiveLeagues()
      : this.configManager.getActiveLeagues({ tier: 'P0' });
    const targetSeasons = season ? [season] : [this.configManager.getDefaultSeason()];
    
    if (allLeagues) {
      return targetLeagues.flatMap(l => targetSeasons.map(s => ({ ...l, season: s })));
    }
    return targetLeagues.map(l => ({ ...l, season: targetSeasons[0] }));
  }

  /**
   * 扫描单个联赛
   * @private
   */
  async _scanLeague(target, index) {
    const { id: leagueId, name, season } = target;
    const workerId = (index % this.config.concurrency) + 1;
    const startTime = Date.now();

    try {
      this.uiHelper.printScanStart(`W${workerId}`, name, season);

      // 检测历史赛季
      const isHistorical = this._isHistoricalSeason(season);
      if (isHistorical) {
        this.uiHelper.printHistoricalMode(`W${workerId}`, season);
      }

      // 获取原始数据
      const response = await this._fetchFixtures(leagueId, season);

      // V6.7.2: 使用解析器
      const fixtures = this.parser.parse(response, leagueId, season, isHistorical, {
        lookbackDays: this.config.lookbackDays,
        lookaheadDays: this.config.lookaheadDays
      });
      const expectedMatches = this.configManager.getExpectedMatches(leagueId, season);
      const criticalWarnings = [];

      if (!fixtures || fixtures.length === 0) {
        this.uiHelper.printNoFixtures(`W${workerId}`, name);
        if (expectedMatches && expectedMatches > 0) {
          const warning = {
            leagueId,
            name,
            season,
            actual: 0,
            expected: expectedMatches,
            missing: expectedMatches
          };
          criticalWarnings.push(warning);
          this.uiHelper.printCriticalWarn(`W${workerId}`, name, season, 0, expectedMatches);
        }
        return { total: 0, inserted: 0, updated: 0, failed: 0, criticalWarnings };
      }

      this.uiHelper.printParsedFixtures(`W${workerId}`, name, fixtures.length);
      if (expectedMatches && fixtures.length < expectedMatches) {
        const warning = {
          leagueId,
          name,
          season,
          actual: fixtures.length,
          expected: expectedMatches,
          missing: expectedMatches - fixtures.length
        };
        criticalWarnings.push(warning);
        this.uiHelper.printCriticalWarn(`W${workerId}`, name, season, fixtures.length, expectedMatches);
      }

      // V6.7.5-EXTRACTED: 使用 Repository 入库
      const result = await this.fixtureRepository.persist(fixtures);
      result.criticalWarnings = criticalWarnings;

      this.uiHelper.printProgress(`W${workerId}`, name, result);

      if (this.config.delayMs > 0) {
        await this._sleep(this.config.delayMs);
      }

      return result;
    } catch (error) {
      const failTime = Date.now() - startTime;
      this.uiHelper.printScanError(`W${workerId}`, name, error.message, failTime);
      return { total: 0, inserted: 0, updated: 0, failed: 1, error: error.message, criticalWarnings: [] };
    }
  }

  /**
   * 检测历史赛季
   * 支持格式: "2024" (单年), "2023/2024", "2023-2024", "20232024" (双年)
   * @private
   */
  _isHistoricalSeason(season) {
    const now = new Date();
    const currentYear = now.getFullYear();

    // 提取所有4位年份数字
    const yearMatches = season.match(/\d{4}/g);
    if (!yearMatches || yearMatches.length === 0) return false;

    // 获取赛季中的最大年份
    const seasonYears = yearMatches.map(y => parseInt(y));
    const maxSeasonYear = Math.max(...seasonYears);

    // 🔧 如果赛季中的任何年份小于当前年份，判定为历史赛季
    // 示例: "2024" < 2026 -> 历史赛季 ✅
    // 示例: "2023/2024" < 2026 -> 历史赛季 ✅
    return maxSeasonYear < currentYear;
  }

  /**
   * 探测真实赛季 ID 映射 (V6.7.7-SEASON-DISCOVERY)
   * V6.7.6-FINAL: 使用 HttpClient 进行请求
   * @private
   */
  async _discoverSeasonId(leagueId, targetYear) {
    this.logger.info(`[HOUND-DEBUG] 🔍 启动赛季指纹探测: ${leagueId} / ${targetYear}`);
    return await this.seasonDiscovery.discover(leagueId, targetYear);
  }

  /**
   * 从 FotMob 获取赛程 (V6.7.7-SEASON-DISCOVERY: 赛季指纹探测 + 全量收割)
   * V6.7.4-REFACTORED: 使用 SeasonStrategyFactory 处理赛季格式
   * 优先使用浏览器内 API Fetch 获取全量数据，失败时回退到网页灵魂抽取
   * @private
   */
  async _fetchFixtures(leagueId, season) {
    // V6.7.4-REFACTORED: 使用策略工厂处理赛季格式
    let normalizedSeason = this.seasonStrategyFactory.format(leagueId, season);
    
    if (this.seasonStrategyFactory.isSingleYearLeague(leagueId)) {
      this.logger.info(`[HOUND] 单年份联赛适配: ${season} -> ${normalizedSeason}`);
    }
    
    // 🔥 V6.7.7: 先探测真实赛季 ID 映射
    const discoveredSeason = await this._discoverSeasonId(leagueId, normalizedSeason);
    if (discoveredSeason !== normalizedSeason) {
      this.logger.info(`[HOUND] 🎯 使用探测到的赛季 ID: ${normalizedSeason} -> ${discoveredSeason}`);
      normalizedSeason = discoveredSeason;
    }
    
    // 🔥 V6.7.10: 使用新的 /api/data/leagues 路径 (拦截器确认的真实频率)
    const apiUrl = this.configManager.buildLeagueApiUrl(leagueId, normalizedSeason);
    
    try {
      this.logger.info(`[HOUND-API] 🎯 优先请求全量 API: ${apiUrl}`);
      const response = await this.httpClient.request(apiUrl);
      
      // 检查是否获取到有效数据
      if (response && Object.keys(response).length > 0) {
        // 检查是否包含赛程数据
        const hasFixtures = response.fixtures || response.allMatches || 
                           (response.overview && response.overview.leagueMatches);
        
        if (hasFixtures) {
          this.logger.info(`[HOUND-API] ✅ 全量 API 请求成功，获取完整数据`);
          return response;
        } else {
          this.logger.warn(`[HOUND-API] ⚠️  API 返回数据但不含赛程，尝试备选...`);
        }
      }
    } catch (apiError) {
      this.logger.warn(`[HOUND-API] ⚠️  API 请求失败: ${apiError.message}`);
    }
    
    // 🔥 回退: 网页灵魂抽取 (数据可能截断)
    this.logger.info(`[HOUND-SOUL] 🔮 回退到网页灵魂抽取模式...`);
    try {
      const soulData = await this.extractor.extractFromWebpage(leagueId, normalizedSeason);
      if (soulData && Object.keys(soulData).length > 0) {
        this.logger.info(`[HOUND-SOUL] ✅ 灵魂抽取成功 (注意：数据可能截断)`);
        return soulData;
      }
    } catch (soulError) {
      this.logger.error(`[HOUND-SOUL] ❌ 灵魂抽取失败: ${soulError.message}`);
    }

    throw new Error(`无法获取联赛 ${leagueId} 赛季 ${normalizedSeason} 的数据`);
  }

  /**
   * 搜索联赛/球队 (V6.7.6-FINAL: 从 titan_discovery.js 迁移)
   * @param {string} term - 搜索关键词
   * @returns {Promise<Object>} 搜索结果
   */
  async search(term) {
    this.logger.info(`\n🔍 正在搜索: "${term}"...`);

    // 🔥 硬编码提示：日本 J 联赛直接提示已知 ID
    const searchTermUpper = term.toUpperCase();
    if (searchTermUpper.includes('J1') || searchTermUpper.includes('J2') || searchTermUpper.includes('日职')) {
      this.logger.info('╔══════════════════════════════════════════════════════════════════╗');
      this.logger.info('║  💡 侦察建议：已通过实时搜索确认 J1 为 223，J2 为 8974              ║');
      this.logger.info('║     请尝试直接扫描: node scripts/ops/titan_discovery.js --league=223 ║');
      this.logger.info('╚══════════════════════════════════════════════════════════════════╝\n');
    }

    // 🔥 V6.7.6-FINAL: 先尝试模拟搜索框输入 (DOM 交互)
    let response;
    try {
      response = await this.extractor.searchViaDOM(term);
    } catch (domError) {
      this.logger.info(`[STEALTH-SOUL] ⚠️  DOM 搜索失败: ${domError.message}`);
      this.logger.info(`[STEALTH-SOUL] 🔄 回退到 API 搜索...\n`);

      // 回退到 API 搜索
      const encodedTerm = encodeURIComponent(term);
      const url = `https://www.fotmob.com/api/search/suggest?term=${encodedTerm}`;
      this.logger.info(`🌐 前端拟态搜索: ${url}`);
      response = await this.httpClient.request(url);
    }

    return response;
  }

  /**
   * 关闭服务
   * V6.7.6-PRINCIPAL: 防御性编程，确保资源在任何情况下都能释放
   */
  async close() {
    const errors = [];

    // 关闭浏览器提供者
    if (this.browserProvider) {
      try {
        await this.browserProvider.close();
        this.logger.info('[DiscoveryService] 浏览器提供者已关闭');
      } catch (e) {
        errors.push({ component: 'browserProvider', error: e.message });
        this.logger.error(`[DiscoveryService] 浏览器关闭失败: ${e.message}`);
      }
    }

    // 关闭数据库连接池
    if (this.dbPool) {
      try {
        await this.dbPool.end();
        this.logger.info('[DiscoveryService] 数据库连接池已关闭');
      } catch (e) {
        errors.push({ component: 'dbPool', error: e.message });
        this.logger.error(`[DiscoveryService] 数据库连接池关闭失败: ${e.message}`);
      }
    }

    // 如果有错误，汇总抛出
    if (errors.length > 0) {
      const errorMessage = errors.map(e => `${e.component}: ${e.error}`).join('; ');
      throw new Error(`[DiscoveryService] 资源关闭过程中发生错误: ${errorMessage}`);
    }
  }

  /**
   * 延迟工具 (V6.7.6-FIX: 恢复此方法)
   * @private
   */
  _sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

module.exports = { DiscoveryService };
