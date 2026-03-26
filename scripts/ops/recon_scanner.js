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

const fs = require('fs');
const path = require('path');
const { Pool } = require('pg');

// 工业级组件导入
const { ReconNavigator, ReconParser, ReconStitcher, ReconMetrics, ReconGuardian, ReconHealthServer } = require('../../src/infrastructure/recon');
const { ReconEngine } = require('../../src/infrastructure/recon/ReconEngine');
const { ProxyRotator } = require('../../src/infrastructure/harvesters/ProxyRotator');
const { FixtureRepository } = require('../../src/infrastructure/services/FixtureRepository');

// 加载配置
const RECON_CONFIG = loadConfig();

/**
 * 加载配置文件
 */
function loadConfig() {
  const configPath = path.join(__dirname, '../../config/recon_config.json');
  try {
    const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
    console.log('✅ 配置加载成功:', config.version);
    return config;
  } catch (e) {
    console.warn('⚠️  配置文件加载失败，使用默认配置');
    return getDefaultConfig();
  }
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
        proxyRotator: this.proxyRotator
      });
    } else {
      this.engine.traceId = this.traceId;
      this.engine.logger = this._childLogger('ReconEngine', this.engine.logger);
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
      // 启动浏览器
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
      this.resources.push({ type: 'navigator', instance: navigator });

      // 更新引擎的 navigator
      this.engine.navigator = navigator;

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
    } finally {
      await this.cleanup();
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
    if (this.guardian) await this.guardian.stop();
    if (this.healthServer) await this.healthServer.stop();
    this.logger.info('scanner_closed');
  }
}

/**
 * 解析命令行参数
 */
function parseArgs() {
  const args = process.argv.slice(2);
  const result = {
    season: null,  // V11.0: 不再设置默认值，必须从 CLI 传入
    league: 'EPL',
    allLeagues: false,
    useProxy: true,
    dateDriven: false,
    crossLeague: false,
    additionalSlugs: []
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

/**
 * 主函数
 */
async function main() {
  const args = parseArgs();

  console.log('\n╔══════════════════════════════════════════════════════════════════╗');
  console.log('║     🔍 TITAN V11.0 RECON SCANNER - Clean Sweep Edition 🔍       ║');
  console.log('╠══════════════════════════════════════════════════════════════════╣');
  console.log(`║     版本: V11.0-CLEAN-SWEEP                                      ║`);
  console.log(`║     赛季: ${args.season}                                    ║`);
  console.log('║     架构: Navigator + Engine + Decryptor                         ║');
  console.log('║     特性: 动态 season 透传 | 协议解密 | 零硬编码                ║');
  console.log('╚══════════════════════════════════════════════════════════════════╝\n');

  // 初始化数据库连接
  const dbPool = new Pool({
    host: process.env.DB_HOST || 'host.docker.internal',
    port: parseInt(process.env.DB_PORT || '5432'),
    database: process.env.DB_NAME || 'football_db',
    user: process.env.DB_USER || 'football_user',
    password: process.env.DB_PASSWORD || 'football_pass'
  });

  // 初始化 Repository
  const repository = new FixtureRepository({ dbPool });

  // 创建扫描器
  const scanner = new ReconScanner({
    repository,
    proxyRotator: args.useProxy ? undefined : null
  });
  
  await scanner.initialize();

  // 确定要扫描的联赛
  const leagues = args.allLeagues
    ? Object.values(RECON_CONFIG.leagues || {})
    : [RECON_CONFIG.leagues?.[args.league] || RECON_CONFIG.leagues?.EPL].filter(Boolean);

  if (leagues.length === 0 || !leagues[0]) {
    console.error(`❌ 错误: 找不到联赛配置: ${args.league}`);
    console.error('可用联赛:', Object.keys(RECON_CONFIG.leagues || {}).join(', '));
    process.exit(1);
  }

  // 执行扫描
  const results = [];
  for (const league of leagues) {
    const result = await scanner.scan(args.season, league, {
      dateDriven: args.dateDriven,
      crossLeague: args.crossLeague,
      additionalSlugs: args.additionalSlugs
    });
    results.push(result);
  }

  // 关闭资源
  await scanner.close();
  await repository.close();

  // 输出汇总
  console.log('\n╔══════════════════════════════════════════════════════════════════╗');
  console.log('║                    📊 侦察任务汇总报告 📊                        ║');
  console.log('╠══════════════════════════════════════════════════════════════════╣');
  
  let totalInserted = 0;
  let totalPending = 0;
  
  results.forEach(r => {
    if (r.success) {
      totalInserted += r.inserted || 0;
      totalPending += r.pendingTotal || 0;
      const coverage = r.coverage || 0;
      const status = coverage >= 95 ? '✅' : coverage >= 80 ? '⚠️' : '❌';
      console.log(`║  ${status} ${(r.league || 'Unknown').padEnd(18)}: ${String(r.inserted || 0).padStart(3)} / ${String(r.pendingTotal || 0).padStart(3)} (${coverage.toFixed(1)}%)`);
    } else {
      console.log(`║  ❌ ${(r.league || 'Unknown').padEnd(18)}: 错误 - ${r.error}`);
    }
  });
  
  const totalCoverage = totalPending > 0 ? (totalInserted / totalPending * 100).toFixed(2) : '0.00';
  console.log('╠══════════════════════════════════════════════════════════════════╣');
  console.log(`║  总计: ${totalInserted} / ${totalPending} 场 (${totalCoverage}%)                         ║`);
  console.log('╚══════════════════════════════════════════════════════════════════╝\n');

  // 退出码
  process.exit(totalCoverage >= 95 ? 0 : 1);
}

// 执行
if (require.main === module) {
  main().catch(error => {
    console.error('\n💥 侦察失败:', error.message);
    process.exit(1);
  });
}

// 导出供测试使用
module.exports = { ReconScanner, loadConfig, RECON_CONFIG };
