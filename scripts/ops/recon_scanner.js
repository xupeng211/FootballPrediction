/**
 * TITAN V11.0 RECON SCANNER - Clean Sweep Edition
 * ================================================
 *
 * V11.0 变更:
 * - 移除所有具体扫描算法（移至 ReconEngine.js）
 * - 移除硬编码 season（'2025-2026' Bug 修复）
 * - 仅保留 CLI 入口和任务编排
 * - 全链路 season 动态透传
 *
 * 用法:
 *   node scripts/ops/recon_scanner.js --season 2024-2025 --league BUNDESLIGA
 *   node scripts/ops/recon_scanner.js --season 2024-2025 --all-leagues
 *
 * @module scripts/ops/recon_scanner
 * @version V11.0-CLEAN-SWEEP
 * @date 2026-03-25
 */

'use strict';

const path = require('path');
const { Pool } = require('pg');
const { loadReconConfig } = require('../../src/infrastructure/recon/services/ReconServiceConfig');

// 工业级组件导入
const { ReconNavigator, ReconParser, ReconStitcher, ReconMetrics, ReconGuardian, ReconHealthServer } = require('../../src/infrastructure/recon');
const { ReconEngine } = require('../../src/infrastructure/recon/ReconEngine');
const { ProxyRotator } = require('../../src/infrastructure/harvesters/ProxyRotator');
const { FixtureRepository } = require('../../src/infrastructure/services/FixtureRepository');
const { L1ConfigManager } = require('../../src/infrastructure/services/L1ConfigManager');

const DEFAULT_RECON_CONFIG_PATH = path.join(__dirname, '../../config/recon_config.json');

// 加载配置
const RECON_CONFIG = loadConfig();

/**
 * 加载配置文件
 */
function loadConfig(configPath = DEFAULT_RECON_CONFIG_PATH) {
  return loadReconConfig(configPath);
}

/**
 * 默认配置
 */
function getDefaultConfig() {
  return {
    version: 'V11.0-DEFAULT',
    oddsportal: { base_url: 'https://www.oddsportal.com' },
    matching: { fuzzy_threshold: 0.85 },
    logging: { component: 'ReconScanner', enable_structured: false }
  };
}

function computeExitCode(results, totalCoverage) {
  if (Array.isArray(results) && results.some((result) => result?.success === false)) {
    return 1;
  }

  const totalPending = Array.isArray(results)
    ? results.reduce((sum, result) => sum + Number(result?.pendingTotal || 0), 0)
    : 0;

  if (totalPending === 0) {
    return 0;
  }

  return Number(totalCoverage) >= 95 ? 0 : 1;
}

/**
 * ReconScanner - 侦察编排器 (V11.0 精简版)
 */
class ReconScanner {
  constructor(dependencies = {}) {
    this.config = dependencies.config || RECON_CONFIG;
    this.traceId = dependencies.traceId || `recon-${Date.now()}-${Math.random().toString(36).substring(2, 8)}`;
    this.logger = this._createTraceLogger(
      dependencies.logger || this._createLogger(),
      this.traceId,
      'ReconScanner'
    );
    this.navigator = dependencies.navigator;
    this.parser = dependencies.parser;
    this.stitcher = dependencies.stitcher;
    this.proxyRotator = dependencies.proxyRotator;
    this.repository = dependencies.repository;
    this.engine = dependencies.engine;
    this.metrics = dependencies.metrics;
    this.guardian = dependencies.guardian;
    this.healthServer = dependencies.healthServer;
    this.configManager = dependencies.configManager;
    this.resources = [];

    this.logger.info('scanner_initialized', { traceId: this.traceId, version: 'V11.0' });
  }

  _createLogger() {
    return {
      info: (event, data) => console.log(`[INFO] ${event}:`, JSON.stringify(data)),
      warn: (event, data) => console.warn(`[WARN] ${event}:`, JSON.stringify(data)),
      error: (event, data) => console.error(`[ERROR] ${event}:`, JSON.stringify(data)),
      debug: (event, data) => process.env.DEBUG && console.log(`[DEBUG] ${event}:`, JSON.stringify(data))
    };
  }

  _createTraceLogger(baseLogger, traceId, component) {
    const wrapPayload = (data = {}) => {
      if (data === null || data === undefined) {
        return { traceId, component };
      }

      if (typeof data !== 'object' || Array.isArray(data)) {
        return { traceId, component, value: data };
      }

      return {
        traceId,
        component,
        ...data
      };
    };

    const wrap = (level) => {
      const fn = typeof baseLogger[level] === 'function'
        ? baseLogger[level].bind(baseLogger)
        : typeof baseLogger.info === 'function'
          ? baseLogger.info.bind(baseLogger)
          : () => {};

      return (event, data = {}) => fn(event, wrapPayload(data));
    };

    return {
      info: wrap('info'),
      warn: wrap('warn'),
      error: wrap('error'),
      debug: wrap('debug')
    };
  }

  _childLogger(component, existingLogger = null) {
    return this._createTraceLogger(
      existingLogger || this._createLogger(),
      this.traceId,
      component
    );
  }

  /**
   * 初始化组件
   */
  async initialize() {
    // 初始化指标收集器
    if (!this.metrics) {
      this.metrics = new ReconMetrics({
        component: 'ReconScanner',
        logger: this._childLogger('ReconMetrics'),
        traceId: this.traceId
      });
    }

    // 初始化 Guardian
    if (!this.guardian) {
      this.guardian = new ReconGuardian({
        checkIntervalMs: 60000,
        logger: this._childLogger('ReconGuardian'),
        traceId: this.traceId
      });
      await this.guardian.start();
    }

    // 初始化健康检查服务器 (V11.0: 默认禁用，避免端口冲突)
    if (!this.healthServer && process.env.ENABLE_HEALTH_SERVER === 'true') {
      this.healthServer = new ReconHealthServer({
        port: 0,
        metrics: this.metrics,
        logger: this._childLogger('ReconHealthServer'),
        traceId: this.traceId
      });
      await this.healthServer.start();
    }

    // 初始化代理轮询器
    if (this.proxyRotator === undefined) {
      this.proxyRotator = new ProxyRotator({
        logger: this._childLogger('ProxyRotator'),
        strategy: 'round-robin'
      });
    }

    if (this.repository) {
      this.repository.traceId = this.traceId;
      this.repository.logger = this._childLogger('FixtureRepository', this.repository.logger);
      if (typeof this.repository.init === 'function') {
        await this.repository.init();
      }
      if (this.healthServer && typeof this.healthServer.registerDatabaseCheck === 'function') {
        this.healthServer.registerDatabaseCheck(this.repository);
      }
    }

    if (!this.configManager) {
      this.configManager = new L1ConfigManager({
        logger: this._childLogger('L1ConfigManager')
      });
    }

    // 初始化解析器
    if (!this.parser) {
      this.parser = new ReconParser({
        logger: this._childLogger('ReconParser'),
        traceId: this.traceId,
        config: { teamSlugs: this._getAllTeamSlugs(), teamMappings: this.config.team_mappings }
      });
    } else {
      this.parser.traceId = this.traceId;
      this.parser.logger = this._childLogger('ReconParser', this.parser.logger);
    }

    if (!this.stitcher && this.repository) {
      this.stitcher = new ReconStitcher({
        repository: this.repository,
        parser: this.parser,
        logger: this._childLogger('ReconStitcher')
      });
    } else if (this.stitcher) {
      this.stitcher.traceId = this.traceId;
      this.stitcher.logger = this._childLogger('ReconStitcher', this.stitcher.logger);
    }

    // 初始化引擎
    if (!this.engine) {
      this.engine = new ReconEngine({
        navigator: this.navigator,
        stitcher: this.stitcher,
        repository: this.repository,
        parser: this.parser,
        logger: this._childLogger('ReconEngine'),
        traceId: this.traceId,
        proxyRotator: this.proxyRotator,
        configManager: this.configManager,
        baseUrl: this.config.oddsportal?.base_url
      });
    } else {
      this.engine.traceId = this.traceId;
      this.engine.logger = this._childLogger('ReconEngine', this.engine.logger);
      this.engine.configManager = this.configManager;
      this.engine.baseUrl = this.config.oddsportal?.base_url || this.engine.baseUrl;
    }

    this.logger.info('scanner_components_initialized');
  }

  _getAllTeamSlugs() {
    const slugs = [];
    const teamSlugs = this.config.team_slugs || {};
    for (const league of Object.values(teamSlugs)) {
      if (Array.isArray(league)) slugs.push(...league);
    }
    return [...new Set(slugs)];
  }

  /**
   * 构建目标 URL (向后兼容)
   * @param {Object} leagueConfig - 联赛配置
   * @param {string} season - 赛季
   * @returns {string} 完整 URL
   */
  buildUrl(leagueConfig, season) {
    const [startYear, endYear] = season.split('-');
    const template = this.config.oddsportal?.results_path || '/football/{country}/{league}-{start}-{end}/standings/';
    return `${this.config.oddsportal?.base_url || 'https://www.oddsportal.com'}${template}`
      .replace('{country}', leagueConfig.country)
      .replace('{league}', leagueConfig.slug)
      .replace('{start}', startYear)
      .replace('{end}', endYear);
  }

  /**
   * 启动并绑定 Navigator
   * @returns {Promise<ReconNavigator>}
   */
  async ensureNavigator() {
    if (this.engine?.navigator) {
      const navigator = this.engine.navigator;

      if (typeof navigator.ensureBrowserHealthy === 'function') {
        await navigator.ensureBrowserHealthy();
        return navigator;
      }

      if (typeof navigator.isHealthy !== 'function' || navigator.isHealthy()) {
        return navigator;
      }

      if (typeof navigator.close === 'function') {
        await navigator.close().catch(() => {});
      }
    }

    const proxy = this.proxyRotator ? this.proxyRotator.getNextProxy() : null;
    const navigator = new ReconNavigator({
      logger: this._childLogger('ReconNavigator'),
      traceId: this.traceId,
      proxy,
      headless: true,
      scrollAttempts: this.config.oddsportal?.navigation?.scroll_attempts || 10,
      scrollDelayMs: this.config.oddsportal?.navigation?.scroll_delay_ms || 2000
    });

    await navigator.launch();
    this.resources = this.resources.filter((resource) => resource.type !== 'navigator');
    this.resources.push({ type: 'navigator', instance: navigator });
    this.engine.navigator = navigator;
    return navigator;
  }

  /**
   * 执行扫描 (V11.0: 委托给 ReconEngine)
   * @param {string} season - 赛季 (动态透传，禁止硬编码)
   * @param {Object} leagueConfig - 联赛配置
   * @param {Object} options - 扫描选项
   */
  async scan(season, leagueConfig, options = {}) {
    const startTime = Date.now();
    
    // V11.0 FIX: 严格验证 season 参数，禁止硬编码
    if (!season || typeof season !== 'string') {
      throw new Error('season parameter is required and must be a string');
    }
    if (season === '2025-2026') {
      this.logger.warn('deprecated_season_detected', { season, hint: 'Use dynamic season from CLI or config' });
    }

    this.logger.info('scan_start', { season, league: leagueConfig.name, traceId: this.traceId });

    try {
      await this.ensureNavigator();

      // 根据模式选择扫描策略
      let result;
      if (options.crossLeague) {
        // 跨联赛扫描（处理德乙、德国杯）
        result = await this.engine.crossLeagueScan(season, leagueConfig, options.additionalSlugs || []);
      } else if (options.dateDriven) {
        // 日期驱动扫描
        result = await this.engine.dateDrivenScan(season, leagueConfig);
      } else {
        // 智能扫描（自动选择最佳策略）
        result = await this.engine.smartScan(season, leagueConfig);
      }

      result.durationMs = Date.now() - startTime;
      result.traceId = this.traceId;

      this.logger.info('scan_complete', result);
      return result;

    } catch (error) {
      this.logger.error('scan_failed', { season, league: leagueConfig.name, error: error.message });
      return { success: false, season, league: leagueConfig.name, error: error.message };
    }
  }

  /**
   * 资源清理
   */
  async cleanup() {
    this.logger.info('cleanup_start', { resources: this.resources.length });

    for (const resource of this.resources) {
      try {
        if (resource.type === 'navigator' && resource.instance) {
          await resource.instance.close();
        }
      } catch (e) {
        this.logger.warn('cleanup_error', { type: resource.type, error: e.message });
      }
    }

    this.resources = [];
    this.logger.info('cleanup_complete');
  }

  /**
   * 关闭扫描器
   */
  async close() {
    await this.cleanup();
    if (this.engine) {
      this.engine.navigator = null;
    }
    if (this.guardian) await this.guardian.stop();
    if (this.healthServer) await this.healthServer.stop();
    this.logger.info('scanner_closed');
  }
}

/**
 * 解析命令行参数
 */
function parseArgs(argv = process.argv.slice(2)) {
  const args = Array.isArray(argv) ? [...argv] : [];
  const result = {
    season: null,  // V11.0: 不再设置默认值，必须从 CLI 传入
    league: 'EPL',
    allLeagues: false,
    useProxy: false,
    dateDriven: false,
    crossLeague: false,
    additionalSlugs: [],
    limit: null,
    concurrency: 5
  };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--season':
        result.season = args[++i];
        break;
      case '--league':
        result.league = args[++i];
        break;
      case '--all-leagues':
        result.allLeagues = true;
        break;
      case '--use-proxy':
        result.useProxy = true;
        break;
      case '--no-proxy':
        result.useProxy = false;
        break;
      case '--date-driven':
        result.dateDriven = true;
        break;
      case '--cross-league':
        result.crossLeague = true;
        break;
      case '--with-slug':
        result.additionalSlugs.push(args[++i]);
        break;
      case '--limit':
        result.limit = parseInt(args[++i], 10);
        break;
      case '--concurrency':
        result.concurrency = parseInt(args[++i], 10);
        break;
    }
  }

  // V11.0: 强制要求 season 参数
  if (!result.season) {
    console.error('❌ 错误: --season 参数是必需的');
    console.error('用法: node scripts/ops/recon_scanner.js --season 2024-2025 --league BUNDESLIGA');
    process.exit(1);
  }

  return result;
}

function buildDbPoolConfig() {
  return {
    host: process.env.DB_HOST || 'host.docker.internal',
    port: parseInt(process.env.DB_PORT || '5432', 10),
    database: process.env.DB_NAME || 'football_db',
    user: process.env.DB_USER || 'football_user',
    password: process.env.DB_PASSWORD || 'football_pass'
  };
}

function printBanner(output, args) {
  output.log('\n╔══════════════════════════════════════════════════════════════════╗');
  output.log('║     🔍 TITAN V11.0 RECON SCANNER - Clean Sweep Edition 🔍       ║');
  output.log('╠══════════════════════════════════════════════════════════════════╣');
  output.log('║     版本: V11.0-CLEAN-SWEEP                                      ║');
  output.log(`║     赛季: ${args.season}                                    ║`);
  output.log('║     架构: Navigator + Engine + Decryptor                         ║');
  output.log('║     特性: 动态 season 透传 | 协议解密 | Recon Matrix            ║');
  output.log('╚══════════════════════════════════════════════════════════════════╝\n');
}

async function cleanupRuntime({ scanner, repository, dbPool, output = console }) {
  let repositoryClosed = false;

  if (scanner && typeof scanner.close === 'function') {
    try {
      await scanner.close();
    } catch (error) {
      output.error('[cleanup] scanner.close 失败:', error.message);
    }
  }

  if (repository && typeof repository.close === 'function') {
    try {
      await repository.close();
      repositoryClosed = true;
    } catch (error) {
      output.error('[cleanup] repository.close 失败:', error.message);
    }
  }

  if (!repositoryClosed && dbPool && typeof dbPool.end === 'function') {
    try {
      await dbPool.end();
    } catch (error) {
      output.error('[cleanup] dbPool.end 失败:', error.message);
    }
  }
}

function createCleanupRunner(cleanupFn) {
  let cleanupPromise = null;

  return async () => {
    if (!cleanupPromise) {
      cleanupPromise = Promise.resolve().then(() => cleanupFn());
    }

    return cleanupPromise;
  };
}

function registerSignalHandlers(signalEmitter, onSignal) {
  if (!signalEmitter || typeof onSignal !== 'function') {
    return () => {};
  }

  const subscriptions = [];
  const bindMethod = typeof signalEmitter.once === 'function' ? 'once' : 'on';

  for (const signal of ['SIGINT', 'SIGTERM']) {
    const handler = () => {
      void onSignal(signal);
    };
    signalEmitter[bindMethod](signal, handler);
    subscriptions.push([signal, handler]);
  }

  return () => {
    for (const [signal, handler] of subscriptions) {
      if (typeof signalEmitter.off === 'function') {
        signalEmitter.off(signal, handler);
      } else if (typeof signalEmitter.removeListener === 'function') {
        signalEmitter.removeListener(signal, handler);
      }
    }
  };
}

function signalToExitCode(signal) {
  if (signal === 'SIGINT') {
    return 130;
  }

  if (signal === 'SIGTERM') {
    return 143;
  }

  return 1;
}

/**
 * 主函数
 */
async function main(argv = process.argv.slice(2), dependencies = {}) {
  const output = dependencies.console || console;
  const parseArgsFn = dependencies.parseArgsFn || parseArgs;
  const createPool = dependencies.createPool || ((config) => new Pool(config));
  const createRepository = dependencies.createRepository || ((options) => new FixtureRepository(options));
  const createScanner = dependencies.createScanner || ((options) => new ReconScanner(options));
  const signalEmitter = dependencies.signalEmitter || process;

  const args = parseArgsFn(argv);
  let dbPool = null;
  let repository = null;
  let scanner = null;
  let shutdownRequested = false;
  let resolveShutdown;
  const shutdownSignalPromise = new Promise((resolve) => {
    resolveShutdown = resolve;
  });

  printBanner(output, args);

  const runCleanup = createCleanupRunner(async () => {
    await cleanupRuntime({ scanner, repository, dbPool, output });
  });

  const unregisterSignalHandlers = registerSignalHandlers(signalEmitter, async (signal) => {
    if (shutdownRequested) {
      return;
    }

    shutdownRequested = true;
    if (typeof output.warn === 'function') {
      output.warn(`[shutdown] 收到 ${signal}，开始清理 Recon 运行时资源`);
    }
    await runCleanup();
    resolveShutdown({ interrupted: true, signal });
  });

  try {
    const workPromise = (async () => {
      dbPool = createPool(buildDbPoolConfig());
      repository = createRepository({ dbPool });
      scanner = createScanner({
        repository,
        proxyRotator: args.useProxy ? undefined : null
      });

      await scanner.initialize();

      const activeLeagues = scanner.configManager.getActiveLeagues();
      const selectedLeague = scanner.configManager.getLeagueByCode(args.league)
        || scanner.configManager.getLeagueById(Number(args.league))
        || scanner.configManager.getLeagueByCode('EPL');

      const leagues = args.allLeagues
        ? activeLeagues
        : [selectedLeague].filter(Boolean);

      if (leagues.length === 0 || !leagues[0]) {
        output.error(`❌ 错误: 找不到联赛配置: ${args.league}`);
        output.error('可用联赛:', activeLeagues.map((league) => `${league.code}(${league.id})`).join(', '));
        return 1;
      }

      const useReconMatrix = Number.isInteger(args.limit) && args.limit > 0;
      const results = [];

      if (useReconMatrix) {
        await scanner.ensureNavigator();
        const result = await scanner.engine.runReconMatrix({
          season: args.season,
          leagueIds: leagues.map((league) => Number(league.id)),
          concurrency: Number.isInteger(args.concurrency) && args.concurrency > 0 ? args.concurrency : 5,
          limit: args.limit
        });
        results.push({
          success: result.success,
          league: useReconMatrix && args.allLeagues ? 'Recon Matrix' : (leagues[0]?.name || 'Recon Matrix'),
          inserted: result.linked || 0,
          mismatched: result.mismatched || 0,
          pendingTotal: result.totalPending || 0,
          coverage: result.totalPending > 0 ? (result.linked / result.totalPending * 100) : 0,
          perLeague: result.perLeague || [],
          errors: result.errors || [],
          error: Array.isArray(result.errors) && result.errors.length > 0
            ? result.errors.map((item) => `${item.league}: ${item.error}`).join(' | ')
            : undefined
        });
      } else {
        for (const league of leagues) {
          const result = await scanner.scan(args.season, league, {
            dateDriven: args.dateDriven,
            crossLeague: args.crossLeague,
            additionalSlugs: args.additionalSlugs
          });
          results.push(result);
        }
      }

      output.log('\n╔══════════════════════════════════════════════════════════════════╗');
      output.log('║                    📊 侦察任务汇总报告 📊                        ║');
      output.log('╠══════════════════════════════════════════════════════════════════╣');

      let totalInserted = 0;
      let totalPending = 0;

      results.forEach((result) => {
        if (result.success) {
          totalInserted += result.inserted || 0;
          totalPending += result.pendingTotal || 0;
          const coverage = result.coverage || 0;
          const status = coverage >= 95 ? '✅' : coverage >= 80 ? '⚠️' : '❌';
          output.log(`║  ${status} ${(result.league || 'Unknown').padEnd(18)}: ${String(result.inserted || 0).padStart(3)} / ${String(result.pendingTotal || 0).padStart(3)} (${coverage.toFixed(1)}%)`);
          if (Array.isArray(result.perLeague)) {
            result.perLeague.forEach((item) => {
              const leagueStatus = item.pendingTotal > 0 && item.linked === item.pendingTotal
                ? '✅'
                : item.linked > 0
                  ? '⚠️'
                  : '❌';
              output.log(`║    ${leagueStatus} ${(item.league || 'Unknown').padEnd(16)}: ${String(item.linked || 0).padStart(3)} 链接 / ${String(item.mismatched || 0).padStart(3)} 失配`);
            });
          }
        } else {
          output.log(`║  ❌ ${(result.league || 'Unknown').padEnd(18)}: 错误 - ${result.error}`);
        }
      });

      const totalCoverage = totalPending > 0 ? (totalInserted / totalPending * 100).toFixed(2) : '0.00';
      output.log('╠══════════════════════════════════════════════════════════════════╣');
      output.log(`║  总计: ${totalInserted} / ${totalPending} 场 (${totalCoverage}%)                         ║`);
      output.log('╚══════════════════════════════════════════════════════════════════╝\n');

      return computeExitCode(results, totalCoverage);
    })();

    const guardedWorkPromise = workPromise.catch((error) => {
      if (shutdownRequested) {
        return signalToExitCode('SIGTERM');
      }
      throw error;
    });

    const raceResult = await Promise.race([guardedWorkPromise, shutdownSignalPromise]);
    if (raceResult && typeof raceResult === 'object' && raceResult.interrupted) {
      return signalToExitCode(raceResult.signal);
    }

    return raceResult;
  } finally {
    unregisterSignalHandlers();
    await runCleanup();
  }
}

// 执行
if (require.main === module) {
  main().then(
    (exitCode) => process.exit(exitCode),
    (error) => {
      console.error('\n💥 侦察失败:', error.message);
      process.exit(1);
    }
  );
}

// 导出供测试使用
module.exports = {
  ReconScanner,
  loadConfig,
  RECON_CONFIG,
  parseArgs,
  computeExitCode,
  buildDbPoolConfig,
  cleanupRuntime,
  createCleanupRunner,
  registerSignalHandlers,
  signalToExitCode,
  main
};
