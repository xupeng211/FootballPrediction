/**
 * @file MarathonService - TITAN V6.6 马拉松收割服务
 * @module infrastructure/services/MarathonService
 * @version V6.6.0
 * @description
 * 核心调度服务，负责万场级别的数据回填任务
 * 特性:
 * - Reconciliation Loop (零缺口对齐)
 * - Tiered Strategy (多级收割策略: 22并发主冲击 → 5并发精准清扫)
 * - Self-Healing (浏览器自动重启)
 * - Proxy Drift (代理漂移自愈)
 */

'use strict';

const { Pool } = require('pg');
const { chromium } = require('playwright');
const pLimit = require('p-limit');
const { getNetworkShield } = require('../network/NetworkShield');

/**
 * 马拉松服务配置选项
 * @typedef {Object} MarathonServiceConfig
 * @property {number} [workers=22] - Worker 并发数
 * @property {number} [staggerMs=800] - 错峰启动间隔
 * @property {number} [batchSize=10000] - 批次大小
 * @property {number} [restartThreshold=500] - 浏览器重启阈值
 * @property {number} [navigationTimeout=45000] - 导航超时
 * @property {number} [progressInterval=10] - 进度报告间隔
 * @property {number} [proxyRetryThreshold=3] - 代理漂移阈值
 * @property {boolean} [headless=true] - 无头模式
 * @property {number} [maxRounds=5] - 最大对齐轮数
 * @property {number} [roundCooldownMs=3000] - 轮间冷却时间
 * @property {number|null} [leagueId=null] - 仅处理指定联赛 ID
 * @property {string|null} [season=null] - 仅处理指定赛季
 */

/**
 * 收割结果统计
 * @typedef {Object} HarvestStats
 * @property {number} total - 总场次
 * @property {number} success - 成功场次
 * @property {number} failed - 失败场次
 * @property {string} duration - 耗时
 * @property {string} rate - 平均速率
 * @property {number} browserRestarts - 浏览器重启次数
 */

/**
 * 马拉松收割服务
 * @class MarathonService
 */
class MarathonService {
  /**
   * 创建 MarathonService 实例
   * @param {MarathonServiceConfig} [config={}] - 配置选项
   */
  constructor(config = {}) {
    /** @type {MarathonServiceConfig} */
    this.config = {
      workers: 22,
      staggerMs: 800,
      batchSize: 10000,
      restartThreshold: 500,
      navigationTimeout: 45000,
      nextDataTimeoutMs: 15000,
      progressInterval: 10,
      proxyRetryThreshold: 3,
      headless: true,
      maxRounds: 5,
      roundCooldownMs: 3000,
      leagueId: null,
      season: null,
      minimumPayloadBytes: 10 * 1024,
      requiredContentModules: ['stats', 'lineup', 'shotmap'],
      silent: config.verbose ? false : process.env.SILENT_MODE !== 'false', // verbose 时强制显式输出
      ...config
    };
    
    // 日志级别控制
    this.logger = {
      info: (...args) => !this.config.silent && console.log(...args),
      warn: (...args) => console.warn(...args), // 警告始终输出
      error: (...args) => console.error(...args), // 错误始终输出
      banner: (...args) => console.log(...args), // 核心看板始终输出
      progress: (...args) => console.log(...args) // 进度报告始终输出
    };

    /** @type {import('pg').Pool} */
    this.dbPool = new Pool({
      host: process.env.DB_HOST || 'localhost',
      port: process.env.DB_PORT || 5432,
      database: process.env.DB_NAME || 'football_db',
      user: process.env.DB_USER || 'football_user',
      password: process.env.DB_PASSWORD || 'football_pass',
      max: 25,
      idleTimeoutMillis: 30000
    });

    /** @type {ReturnType<typeof getNetworkShield>} */
    this.networkShield = getNetworkShield();
    
    /** @type {import('playwright').Browser | null} */
    this.browser = null;
    
    /** @type {number} */
    this.browserLaunchCount = 0;
    
    /** @type {ReturnType<typeof pLimit>} */
    this.limit = pLimit(this.config.workers);
    
    /** @type {Map<number, WorkerState>} */
    this.workerStates = new Map();
    
    /** @type {Map<number, number>} */
    this.roundStats = new Map();
    
    this._initWorkerStates();
  }

  /**
   * 初始化 Worker 状态
   * @private
   */
  _initWorkerStates() {
    const maxWorkerSlots = Math.max(this.config.workers, 5);
    for (let i = 1; i <= maxWorkerSlots; i++) {
      this.workerStates.set(i, {
        consecutiveFailures: 0,
        currentProxy: null,
        totalHarvested: 0,
        matchesSinceRestart: 0,
        isRestarting: false
      });
    }
  }

  /**
   * 初始化浏览器
   * @returns {Promise<void>}
   */
  async init() {
    this.browserLaunchCount++;
    this.logger.info(`\n🚀 [MARATHON] 启动浏览器 (#${this.browserLaunchCount})...`);
    
    this.browser = await chromium.launch({
      headless: this.config.headless,
      args: [
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--disable-software-rasterizer',
        '--disable-extensions',
        '--disable-background-networking',
        '--disable-sync',
        '--no-first-run',
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--max-old-space-size=4096'
      ]
    });

    this.logger.info(`✅ [MARATHON] 浏览器 #${this.browserLaunchCount} 就绪`);
  }

  /**
   * Reconciliation Loop - 零缺口对齐循环
   * @param {Object} options - 对齐选项
   * @param {number} [options.limit=10000] - 最大采集数
   * @returns {Promise<{rounds: number, totalStats: HarvestStats, deadLetters: Array}>}
   */
  async reconcile(options = {}) {
    const { limit = 10000 } = options;
    let round = 0;
    const maxRounds = this.config.maxRounds;

    this.logger.banner('\n╔══════════════════════════════════════════════════════════════════╗');
    this.logger.banner('║  🔄 TITAN MARATHON - RECONCILIATION LOOP (零缺口模式)           ║');
    this.logger.banner('║                                                                  ║');
    this.logger.banner('║  策略: 22并发主冲击 -> 5并发精准清扫 -> 死信报告                ║');
    this.logger.banner(`║  限制: 最大 ${maxRounds} 轮循环，严禁无限循环                            ║`);
    this.logger.banner('╚══════════════════════════════════════════════════════════════════╝\n');

    while (round < maxRounds) {
      round++;
      
      // 检查当前缺口
      const pendingCount = await this._getPendingCount();
      this.logger.banner(`📊 第 ${round}/${maxRounds} 轮 - 当前待采集: ${pendingCount} 场`);
      
      if (pendingCount === 0) {
        this.logger.banner('✅ 缺口已清零，退出循环');
        break;
      }

      // 获取待采集列表
      const matches = await this._getPendingMatches(limit);
      if (matches.length === 0) {
        this.logger.banner('✅ 没有待采集比赛，任务完成');
        break;
      }

      // 多级策略：第一轮22并发，后续5并发
      const isMainBlast = round === 1;
      const workers = isMainBlast ? this.config.workers : 5;
      const timeout = isMainBlast ? 45000 : 60000;
      
      this.logger.banner(`\n🚀 [TIER ${isMainBlast ? 1 : 2}] ${isMainBlast ? '主冲击' : '精准清扫'}模式: ${workers}并发 | 超时${timeout/1000}s`);

      // 执行本轮收割
      const result = await this._executeRound(matches, { workers, timeout });
      this.roundStats.set(round, result);
      
      this.logger.progress(`\n📊 [ROUND ${round}] 完成: 成功 ${result.success} | 失败 ${result.failed} | 速率 ${result.rate}`);

      // 轮间冷却
      if (round < maxRounds && pendingCount > 0) {
        this.logger.info(`⏱️  轮间冷却 ${this.config.roundCooldownMs/1000} 秒...`);
        await this._sleep(this.config.roundCooldownMs);
      }
    }

    // 生成最终报告
    return this._generateReconciliationReport(round);
  }

  /**
   * 执行单轮收割
   * @private
   * @param {Array} matches - 比赛列表
   * @param {Object} options - 本轮配置
   * @returns {Promise<HarvestStats>}
   */
  async _executeRound(matches, options) {
    const { workers, timeout } = options;
    this.limit = pLimit(workers);
    
    const stats = {
      completed: 0,
      success: 0,
      failed: 0,
      startTime: Date.now(),
      lastReportedProgress: 0
    };

    this._printBanner(matches.length, workers);

    // 分批处理
    const batchSize = workers;
    const results = [];
    
    for (let i = 0; i < matches.length; i += batchSize) {
      const batch = matches.slice(i, i + batchSize);
      
      const batchPromises = batch.map((match, idx) => {
        const globalIndex = i + idx;
        const workerId = (globalIndex % workers) + 1;
        
        return this.limit(async () => {
          const result = await this._harvestWithProxyDrift(match, globalIndex, workerId, timeout);
          
          // 原子更新统计
          stats.completed++;
          if (result.success) {
            stats.success++;
            this._updateWorkerSuccess(workerId, result.proxy);
          } else {
            stats.failed++;
            if (this.config.verbose) {
              this.logger.warn(`[W${workerId}] HARVEST_FAILED match=${match.match_id} reason=${result.error}`);
            }
          }
          
          // 进度报告
          if (stats.completed - stats.lastReportedProgress >= this.config.progressInterval) {
            this._printProgress(stats.completed, matches.length, stats);
            stats.lastReportedProgress = stats.completed;
          }
          
          return result;
        });
      });
      
      const batchResults = await Promise.all(batchPromises);
      results.push(...batchResults);
      
      // 批次间错峰
      if (i + batchSize < matches.length) {
        await this._sleep(this.config.staggerMs);
      }
    }

    return this._generateRoundReport(stats);
  }

  /**
   * 带代理漂移的收割
   * @private
   */
  async _harvestWithProxyDrift(match, index, workerId, timeout) {
    const { match_id, external_id, home_team, away_team } = match;
    const startTime = Date.now();
    
    const workerState = this._getWorkerState(workerId);
    
    // 代理漂移检查
    if (workerState.consecutiveFailures >= this.config.proxyRetryThreshold) {
      this.logger.info(`[W${workerId}] 🔄 代理漂移: 连续 ${workerState.consecutiveFailures} 次失败，切换代理...`);
      if (workerState.currentProxy) {
        try {
          this.networkShield.forceReassign(workerId, workerState.currentProxy);
          workerState.consecutiveFailures = 0;
        } catch (e) {
          this.logger.warn(`[W${workerId}] 代理切换失败: ${e.message}`);
        }
      }
    }

    // 分配代理
    let proxyConfig;
    try {
      proxyConfig = this.networkShield.assignPort(workerId);
      workerState.currentProxy = proxyConfig.port;
    } catch (e) {
      return { success: false, match_id, error: '代理分配失败: ' + e.message, time: Date.now() - startTime };
    }

    // 检查 Worker 浏览器重启
    if (workerState.matchesSinceRestart >= this.config.restartThreshold) {
      await this._checkGlobalRestart();
    }

    let context = null;
    let page = null;

    try {
      // 创建上下文
      const browserProxyServer = this._resolveBrowserProxyServer(proxyConfig);
      context = await this.browser.newContext({
        viewport: { width: 1920, height: 1080 },
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        ignoreHTTPSErrors: true,
        proxy: browserProxyServer ? { server: browserProxyServer } : undefined,
        extraHTTPHeaders: this._buildApiHeaders()
      });
      
      page = await context.newPage();

      const rawData = await this._extractLuxuryPayload(page, match, timeout);
      const dataSize = JSON.stringify(rawData).length;

      // 入库
      await this._saveToDatabase(match_id, external_id, rawData);

      // 标记成功
      if (this.networkShield?.markSuccess) {
        this.networkShield.markSuccess(proxyConfig.port);
      }
      
      const duration = Date.now() - startTime;
      
      return { 
        success: true, 
        match_id, 
        size: dataSize, 
        time: duration,
        proxy: proxyConfig.port 
      };

    } catch (error) {
      const duration = Date.now() - startTime;
      
      workerState.consecutiveFailures++;
      if (this.networkShield?.markFailed) {
        this.networkShield.markFailed(proxyConfig.port, error.message);
      }
      
      return { 
        success: false, 
        match_id, 
        error: error.message, 
        time: duration,
        proxy: proxyConfig.port,
        consecutiveFailures: workerState.consecutiveFailures
      };
    } finally {
      if (page) {
        await page.close().catch(() => {});
      }
      if (context) {
        await context.close().catch(() => {});
      }
    }
  }

  /**
   * 解析浏览器实际使用的代理地址。
   * curl 类工具会读取环境变量，Playwright 需要在 context 中显式声明。
   * @private
   * @param {object} proxyConfig
   * @returns {string|null}
   */
  _resolveBrowserProxyServer(proxyConfig) {
    return process.env.BROWSER_PROXY_SERVER
      || process.env.HTTPS_PROXY
      || process.env.HTTP_PROXY
      || process.env.https_proxy
      || process.env.http_proxy
      || proxyConfig?.url
      || null;
  }

  _buildApiHeaders() {
    return {
      accept: 'application/json, text/plain, */*',
      'accept-language': 'en-US,en;q=0.9',
      'x-requested-with': 'XMLHttpRequest',
      referer: 'https://www.fotmob.com/'
    };
  }

  /**
   * 直接请求 matchDetails JSON API，缺任一关键模块则失败
   * @private
   * @param {import('playwright').Page} page
   * @param {object} match
   * @param {number} timeout
   * @returns {Promise<object>}
   */
  async _extractLuxuryPayload(page, match, timeout) {
    const candidateUrls = this._buildMatchDetailsApiUrls(match.external_id);
    const attemptErrors = [];

    for (const url of candidateUrls) {
      try {
        const response = await page.goto(url, {
          waitUntil: 'commit',
          timeout
        });
        if (!response) {
          throw new Error(`API_NO_RESPONSE url=${url}`);
        }

        const responseText = await response.text();
        if (!response.ok()) {
          throw new Error(`API_HTTP_${response.status()} url=${url} body=${responseText.slice(0, 240)}`);
        }

        const apiPayload = JSON.parse(responseText);
        const diagnostics = this._buildPayloadDiagnostics(apiPayload, match, url);
        const validation = this._validatePayloadDiagnostics(diagnostics, match);
        if (!validation.valid) {
          throw new Error(`${validation.reason} diagnostics=${JSON.stringify(diagnostics)}`);
        }

        if (this.config.verbose) {
          this.logger.info(
            `[MARATHON] Extracted full payload bytes=${diagnostics.payloadBytes} modules=${diagnostics.contentKeys.join(',')} match=${match.match_id}`
          );
        }

        return apiPayload;
      } catch (error) {
        attemptErrors.push({
          url,
          error: error.message
        });
      }
    }

    throw new Error(`MATCH_DETAILS_API_FAILED attempts=${JSON.stringify(attemptErrors)}`);
  }

  /**
   * 构建 matchDetails API 候选。FotMob 近期页面使用 /api/data/matchDetails。
   * @private
   * @param {string|number} externalId
   * @returns {string[]}
   */
  _buildMatchDetailsApiUrls(externalId) {
    const id = encodeURIComponent(String(externalId).trim());
    return [
      `https://www.fotmob.com/api/data/matchDetails?matchId=${id}`,
      `https://www.fotmob.com/api/matchDetails?matchId=${id}`
    ];
  }

  /**
   * 构造 payload 诊断信息
   * @private
   * @param {object} payload
   * @param {object} match
   * @param {string} finalUrl
   * @returns {object}
   */
  _buildPayloadDiagnostics(payload, match, finalUrl) {
    const content = payload?.content || {};
    const generalMatchId = String(payload?.general?.matchId || '').trim();
    const contentKeys = Object.keys(content);
    const payloadBytes = JSON.stringify(payload).length;

    return {
      finalUrl,
      expectedExternalId: String(match.external_id),
      generalMatchId,
      contentKeys,
      payloadBytes,
      hasStats: !!content.stats,
      hasLineup: !!content.lineup,
      hasShotmap: !!content.shotmap,
      statsKeys: content.stats && typeof content.stats === 'object'
        ? Object.keys(content.stats).slice(0, 10)
        : [],
      lineupKeys: content.lineup && typeof content.lineup === 'object'
        ? Object.keys(content.lineup).slice(0, 10)
        : [],
      shotCount: Array.isArray(content?.shotmap?.shots) ? content.shotmap.shots.length : 0
    };
  }

  /**
   * 校验 payload 诊断结果
   * @private
   * @param {object} diagnostics
   * @param {object} match
   * @returns {{valid: boolean, reason?: string}}
   */
  _validatePayloadDiagnostics(diagnostics, match) {
    if (!diagnostics.payloadBytes || diagnostics.payloadBytes < this.config.minimumPayloadBytes) {
      return {
        valid: false,
        reason: `PAYLOAD_TOO_SMALL_${diagnostics.payloadBytes}`
      };
    }

    if (diagnostics.generalMatchId && diagnostics.generalMatchId !== String(match.external_id)) {
      return {
        valid: false,
        reason: `HISTORICAL_REDIRECT_MISMATCH expected=${match.external_id} actual=${diagnostics.generalMatchId}`
      };
    }

    for (const moduleName of this.config.requiredContentModules) {
      const flagName = `has${moduleName.charAt(0).toUpperCase()}${moduleName.slice(1)}`;
      if (!diagnostics[flagName]) {
        return {
          valid: false,
          reason: `INCOMPLETE_CONTENT_MISSING_${moduleName.toUpperCase()}`
        };
      }
    }

    return { valid: true };
  }

  /**
   * 更新 Worker 成功状态
   * @private
   */
  _updateWorkerSuccess(workerId, proxyPort) {
    const state = this._getWorkerState(workerId);
    state.consecutiveFailures = 0;
    state.totalHarvested++;
    state.matchesSinceRestart++;
  }

  /**
   * 获取或初始化 worker 状态
   * @private
   * @param {number} workerId
   * @returns {WorkerState}
   */
  _getWorkerState(workerId) {
    if (!this.workerStates.has(workerId)) {
      this.workerStates.set(workerId, {
        consecutiveFailures: 0,
        currentProxy: null,
        totalHarvested: 0,
        matchesSinceRestart: 0,
        isRestarting: false
      });
    }

    return this.workerStates.get(workerId);
  }

  /**
   * 检查全局浏览器重启
   * @private
   */
  async _checkGlobalRestart() {
    const workersNeedingRestart = Array.from(this.workerStates.values())
      .filter(s => s.matchesSinceRestart >= this.config.restartThreshold).length;
    
    if (workersNeedingRestart >= Math.ceil(this.config.workers / 2)) {
      await this._globalRestartBrowser();
    }
  }

  /**
   * 全局浏览器重启
   * @private
   */
  async _globalRestartBrowser() {
    this.logger.info(`\n♻️  [MARATHON] 执行全局浏览器重启...`);
    
    if (this.browser) {
      await this.browser.close();
    }
    
    // 重置所有 Worker 计数
    for (const state of this.workerStates.values()) {
      state.matchesSinceRestart = 0;
      state.isRestarting = false;
    }
    
    await this.init();
    this.logger.info('✅ [MARATHON] 浏览器重启完成\n');
  }

  /**
   * 保存到数据库
   * @private
   */
  async _saveToDatabase(matchId, externalId, rawData) {
    const client = await this.dbPool.connect();
    
    try {
      const jsonData = JSON.stringify(rawData);
      if (jsonData.length < this.config.minimumPayloadBytes) {
        throw new Error(`数据哨兵拦截: ${(jsonData.length/1024).toFixed(1)}KB < ${(this.config.minimumPayloadBytes/1024).toFixed(1)}KB`);
      }

      const query = `
        INSERT INTO raw_match_data (match_id, external_id, raw_data, collected_at, data_version, data_hash)
        VALUES ($1, $2, $3::jsonb, NOW(), 'V26.1-MARATHON', md5($3))
        ON CONFLICT (match_id)
        DO UPDATE SET 
          external_id = EXCLUDED.external_id,
          raw_data = EXCLUDED.raw_data,
          collected_at = NOW(),
          data_version = EXCLUDED.data_version,
          data_hash = EXCLUDED.data_hash
        RETURNING match_id
      `;
      
      await client.query(query, [matchId, externalId, jsonData]);
      await client.query(
        `
          UPDATE matches
          SET pipeline_status = 'harvested',
              updated_at = NOW()
          WHERE match_id = $1
        `,
        [matchId]
      );
    } finally {
      client.release();
    }
  }

  /**
   * 获取待采集数量
   * @private
   */
  async _getPendingCount() {
    const client = await this.dbPool.connect();
    try {
      const { whereClause, params } = this._buildPendingFilterClauses();
      const result = await client.query(`
        SELECT COUNT(*) as count
        FROM matches m
        LEFT JOIN raw_match_data r ON m.match_id = r.match_id
        WHERE r.match_id IS NULL
          ${whereClause}
      `, params);
      return parseInt(result.rows[0].count);
    } finally {
      client.release();
    }
  }

  /**
   * 获取待采集列表
   * @private
   */
  async _getPendingMatches(limit = 10000) {
    const client = await this.dbPool.connect();
    
    try {
      const { whereClause, params } = this._buildPendingFilterClauses();
      const query = `
        SELECT m.match_id, m.external_id, m.home_team, m.away_team, m.match_date
        FROM matches m
        LEFT JOIN raw_match_data r ON m.match_id = r.match_id
        WHERE r.match_id IS NULL
          ${whereClause}
        ORDER BY m.match_date
        LIMIT $${params.length + 1}
      `;
      
      const result = await client.query(query, [...params, limit]);
      return result.rows;
    } finally {
      client.release();
    }
  }

  /**
   * 获取死信清单
   * @private
   */
  async _getDeadLetterMatches(limit = 20) {
    const client = await this.dbPool.connect();
    try {
      const { whereClause, params } = this._buildPendingFilterClauses();
      const result = await client.query(`
        SELECT m.match_id, m.external_id, m.home_team, m.away_team, m.match_date
        FROM matches m
        LEFT JOIN raw_match_data r ON m.match_id = r.match_id
        WHERE r.match_id IS NULL
          ${whereClause}
        ORDER BY m.match_date DESC
        LIMIT $${params.length + 1}
      `, [...params, limit]);
      return result.rows;
    } finally {
      client.release();
    }
  }

  /**
   * 构建待采集过滤条件
   * @private
   * @returns {{whereClause: string, params: Array<string|number>}}
   */
  _buildPendingFilterClauses() {
    const conditions = [
      `m.external_id IS NOT NULL`,
      `m.external_id NOT LIKE 'csv%'`
    ];
    const params = [];

    if (Number.isInteger(this.config.leagueId) && this.config.leagueId > 0) {
      params.push(`${this.config.leagueId}_%`);
      conditions.push(`m.match_id LIKE $${params.length}`);
    }

    if (typeof this.config.season === 'string' && this.config.season.trim()) {
      params.push(this.config.season.trim());
      conditions.push(`m.season = $${params.length}`);
    }

    return {
      whereClause: conditions.length > 0 ? `AND ${conditions.join('\n          AND ')}` : '',
      params
    };
  }

  /**
   * 打印启动横幅
   * @private
   */
  _printBanner(total, workers) {
    console.log('');
    console.log('╔══════════════════════════════════════════════════════════════════╗');
    console.log('║                                                                  ║');
    console.log('║           🏃 TITAN MARATHON V6.6 🏃                             ║');
    console.log('║                                                                  ║');
    console.log('║     万场饱和收割 | 22 Worker × 22 IP | 9900X 极限压榨          ║');
    console.log('║     800ms 错峰启动 | 500场自动重启 | 代理漂移自愈              ║');
    console.log('║                                                                  ║');
    console.log('╚══════════════════════════════════════════════════════════════════╝');
    console.log(`📊 任务规模: ${total} 场比赛`);
    console.log(`🐝 并发配置: ${workers} Workers`);
    console.log(`⏱️  错峰延迟: ${this.config.staggerMs}ms/Worker`);
    console.log(`♻️  重启阈值: 每 ${this.config.restartThreshold} 场`);
    console.log('');
  }

  /**
   * 打印进度
   * @private
   */
  _printProgress(current, total, stats) {
    const percentage = ((current / total) * 100).toFixed(1);
    const elapsed = (Date.now() - stats.startTime) / 1000;
    const rate = current / elapsed;
    const ratePerMin = (rate * 60).toFixed(0);
    const remaining = total - current;
    const etaMin = Math.ceil(remaining / rate / 60);

    console.log('');
    console.log('╔══════════════════════════════════════════════════════════════════╗');
    console.log(`║  📊 [PROGRESS] ${current.toString().padStart(5)}/${total.toLocaleString()} (${percentage.padStart(5)}%)                          ║`);
    console.log(`║  ⚡ 速率: ${ratePerMin.padStart(4)} 场/min | 预计剩余: ${etaMin.toString().padStart(3)} min                        ║`);
    console.log(`║  ✅ 成功: ${stats.success.toString().padStart(5)} | ❌ 失败: ${stats.failed.toString().padStart(4)}                        ║`);
    console.log('╚══════════════════════════════════════════════════════════════════╝');
  }

  /**
   * 生成单轮报告
   * @private
   */
  _generateRoundReport(stats) {
    const duration = Date.now() - stats.startTime;
    const durationMin = (duration / 60000).toFixed(1);
    const rate = stats.completed > 0 ? (stats.completed / (duration / 60000)).toFixed(1) : '0.0';

    return {
      total: stats.completed,
      success: stats.success,
      failed: stats.failed,
      duration: `${durationMin} min`,
      rate: `${rate} 场/min`
    };
  }

  /**
   * 生成对齐报告
   * @private
   */
  async _generateReconciliationReport(rounds) {
    const totalStats = {
      success: 0,
      failed: 0
    };

    this.logger.banner('\n╔══════════════════════════════════════════════════════════════════╗');
    this.logger.banner('║  📊 RECONCILIATION 最终报告                                      ║');
    this.logger.banner('╠══════════════════════════════════════════════════════════════════╣');

    for (let i = 1; i <= rounds; i++) {
      const stats = this.roundStats.get(i);
      if (stats) {
        const tier = i === 1 ? '🚀' : '🎯';
        this.logger.banner(`║  第${i}轮 ${tier}: 成功 ${stats.success.toString().padStart(5)} | 失败 ${stats.failed.toString().padStart(4)} | ${stats.rate.padStart(10)} ║`);
        totalStats.success += stats.success;
        totalStats.failed += stats.failed;
      }
    }

    this.logger.banner('╠══════════════════════════════════════════════════════════════════╣');
    this.logger.banner(`║  总计采集: ${totalStats.success.toString().padStart(6)} 场成功 | ${totalStats.failed.toString().padStart(5)} 场失败          ║`);
    
    // 检查最终缺口
    const finalPending = await this._getPendingCount();
    this.logger.banner(`║  剩余缺口: ${finalPending.toString().padStart(6)} 场                                          ║`);
    this.logger.banner('╚══════════════════════════════════════════════════════════════════╝');

    // 死信处理
    let deadLetters = [];
    if (finalPending > 0) {
      this.logger.banner('\n📋 死信清单 (前 20 场):');
      deadLetters = await this._getDeadLetterMatches(20);
      deadLetters.forEach((m, i) => {
        this.logger.banner(`   ${i+1}. ${m.match_id} | ${m.home_team} vs ${m.away_team}`);
      });
    } else {
      this.logger.banner('\n✅ [MARATHON] 零缺口对齐完成！所有场次采集成功。');
    }

    return {
      rounds,
      totalStats,
      deadLetters,
      finalPending
    };
  }

  /**
   * 延迟
   * @private
   */
  _sleep(ms) {
    return new Promise(resolve => {
      setTimeout(resolve, ms);
    });
  }

  /**
   * 清理资源
   */
  async cleanup() {
    if (this.browser) {
      await this.browser.close();
      this.logger.info('🛑 [MARATHON] 浏览器已关闭');
    }
    
    if (this.dbPool) {
      await this.dbPool.end();
      this.logger.info('🛑 [MARATHON] 数据库连接已释放');
    }
  }
}

/**
 * Worker 状态
 * @typedef {Object} WorkerState
 * @property {number} consecutiveFailures - 连续失败次数
 * @property {number|null} currentProxy - 当前代理端口
 * @property {number} totalHarvested - 总收割数
 * @property {number} matchesSinceRestart - 自重启收割数
 * @property {boolean} isRestarting - 是否正在重启
 */

module.exports = { MarathonService };
