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
const {
  parseArgs,
  buildDbPoolConfig,
  cleanupRuntime,
  createCleanupRunner,
  registerSignalHandlers,
  signalToExitCode,
  main: cliMain
} = require('./ReconCLIHandler');
const { loadReconConfig } = require('../../src/infrastructure/recon/services/ReconServiceConfig');

// 工业级组件导入
const { ReconNavigator, ReconParser, ReconStitcher, ReconMetrics, ReconGuardian, ReconHealthServer } = require('../../src/infrastructure/recon');
const { ReconEngine } = require('../../src/infrastructure/recon/ReconEngine');
const { ReconDiskSweeper } = require('../../src/infrastructure/recon/services/ReconDiskSweeper');
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

function isSkippedFutureFinalsResult(result) {
  return result?.sourceState === 'SKIPPED_FUTURE_FINALS' || result?.error === 'SKIPPED_FUTURE_FINALS';
}

function computeExitCode(results, totalCoverage) {
  if (
    Array.isArray(results) &&
    results.some((result) => result?.success === false && !isSkippedFutureFinalsResult(result))
  ) {
    return 1;
  }

  const totalPending = Array.isArray(results)
    ? results.reduce((sum, result) => {
      if (isSkippedFutureFinalsResult(result)) {
        return sum;
      }
      return sum + Number(result?.pendingTotal || 0);
    }, 0)
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
    this.diskSweeper = dependencies.diskSweeper;
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

    if (!this.diskSweeper) {
      this.diskSweeper = new ReconDiskSweeper({
        logger: this._childLogger('ReconDiskSweeper'),
        traceId: this.traceId,
        rootDir: this.config.recon_runtime?.browser_context?.user_data_dir_root,
        maxAgeMs: this.config.recon_runtime?.disk_sweeper?.max_age_ms,
        enabled: this.config.recon_runtime?.disk_sweeper?.enabled !== false
      });
    }
    if (typeof this.diskSweeper.sweep === 'function') {
      await this.diskSweeper.sweep();
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
      proxyRotator: this.proxyRotator,
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

async function main(argv = process.argv.slice(2), dependencies = {}) {
  return cliMain(argv, {
    ...dependencies,
    parseArgsFn: dependencies.parseArgsFn || parseArgs,
    buildDbPoolConfigFn: dependencies.buildDbPoolConfigFn || buildDbPoolConfig,
    computeExitCodeFn: dependencies.computeExitCodeFn || computeExitCode,
    isSkippedFutureFinalsResultFn: dependencies.isSkippedFutureFinalsResultFn || isSkippedFutureFinalsResult,
    createPool: dependencies.createPool || ((config) => new Pool(config)),
    createRepository: dependencies.createRepository || ((options) => new FixtureRepository(options)),
    createScanner: dependencies.createScanner || ((options) => new ReconScanner(options))
  });
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
