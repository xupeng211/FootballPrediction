/**
 * ReconMetrics - Prometheus 指标收集器
 * =====================================
 *
 * 职责: 提供深度遥测能力，暴露 Prometheus 格式指标
 * 核心指标:
 * - recon_match_stitched_total: 缝合成功总数
 * - recon_selector_fallback_hit: 选择器降级命中分布
 * - recon_fuzzy_confidence_avg: 模糊匹配平均置信度
 * - recon_navigator_latency: 页面加载延迟分布
 * - recon_zombie_killed_total: 僵尸进程清理数
 *
 * @module infrastructure/recon/ReconMetrics
 * @version V6.7-OBSERVABILITY
 * @date 2026-03-22
 */

'use strict';

const promClient = require('prom-client');

/**
 * Prometheus 指标收集器类
 * @class ReconMetrics
 */
class ReconMetrics {
  /**
   * 创建指标收集器
   * @param {Object} options - 配置选项
   * @param {string} options.prefix - 指标前缀 (默认: 'recon')
   * @param {Object} options.logger - 结构化日志器
   */
  constructor(options = {}) {
    this.prefix = options.prefix || 'recon';
    this.logger = options.logger || console;
    this.register = new promClient.Registry();

    // 初始化默认指标
    this.initCounters();
    this.initHistograms();
    this.initGauges();

    this.logger.info('metrics_initialized', { prefix: this.prefix });
  }

  /**
   * 初始化计数器 (Counter)
   * @private
   */
  initCounters() {
    // 缝合成功总数
    this.matchStitchedTotal = new promClient.Counter({
      name: `${this.prefix}_match_stitched_total`,
      help: 'Total number of matches successfully stitched',
      labelNames: ['season', 'league', 'method'],
      registers: [this.register]
    });

    // 缝合失败总数
    this.matchFailedTotal = new promClient.Counter({
      name: `${this.prefix}_match_failed_total`,
      help: 'Total number of matches that failed to stitch',
      labelNames: ['season', 'league', 'reason'],
      registers: [this.register]
    });

    // 选择器降级命中
    this.selectorFallbackHit = new promClient.Counter({
      name: `${this.prefix}_selector_fallback_hit_total`,
      help: 'Number of times a fallback selector was used',
      labelNames: ['selector_name', 'page_type'],
      registers: [this.register]
    });

    // 僵尸进程清理数
    this.zombieKilledTotal = new promClient.Counter({
      name: `${this.prefix}_zombie_killed_total`,
      help: 'Total number of zombie processes killed by Guardian',
      labelNames: ['process_name'],
      registers: [this.register]
    });

    // 代理切换次数
    this.proxySwitchesTotal = new promClient.Counter({
      name: `${this.prefix}_proxy_switches_total`,
      help: 'Total number of proxy switches due to bans',
      labelNames: ['reason'],
      registers: [this.register]
    });

    // 熔断触发次数
    this.circuitBreakerTrips = new promClient.Counter({
      name: `${this.prefix}_circuit_breaker_trips_total`,
      help: 'Total number of circuit breaker trips',
      labelNames: ['reason'],
      registers: [this.register]
    });
  }

  /**
   * 初始化直方图 (Histogram)
   * @private
   */
  initHistograms() {
    // 模糊匹配置信度分布
    this.fuzzyConfidence = new promClient.Histogram({
      name: `${this.prefix}_fuzzy_confidence`,
      help: 'Distribution of fuzzy matching confidence scores',
      labelNames: ['season', 'league'],
      buckets: [0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0],
      registers: [this.register]
    });

    // 导航延迟分布
    this.navigatorLatency = new promClient.Histogram({
      name: `${this.prefix}_navigator_latency_seconds`,
      help: 'Page navigation latency distribution',
      labelNames: ['league', 'page_type'],
      buckets: [1, 2, 5, 10, 30, 60, 120],
      registers: [this.register]
    });

    // 扫描耗时分布
    this.scanDuration = new promClient.Histogram({
      name: `${this.prefix}_scan_duration_seconds`,
      help: 'Full scan duration distribution',
      labelNames: ['season', 'league'],
      buckets: [10, 30, 60, 120, 300, 600],
      registers: [this.register]
    });

    // 重试延迟分布
    this.retryDelay = new promClient.Histogram({
      name: `${this.prefix}_retry_delay_seconds`,
      help: 'Retry delay distribution (with jitter)',
      labelNames: ['error_type'],
      buckets: [1, 2, 5, 10, 30],
      registers: [this.register]
    });
  }

  /**
   * 初始化仪表盘 (Gauge)
   * @private
   */
  initGauges() {
    // 活跃锁数量
    this.activeLocks = new promClient.Gauge({
      name: `${this.prefix}_active_locks`,
      help: 'Number of active distributed locks',
      registers: [this.register]
    });

    // 缝合成功率
    this.stitchingRate = new promClient.Gauge({
      name: `${this.prefix}_stitching_rate`,
      help: 'Current stitching success rate (0-1)',
      labelNames: ['season', 'league'],
      registers: [this.register]
    });

    // 熔断器状态 (0=closed, 1=open, 2=half_open)
    this.circuitBreakerState = new promClient.Gauge({
      name: `${this.prefix}_circuit_breaker_state`,
      help: 'Circuit breaker state (0=closed, 1=open, 2=half_open)',
      registers: [this.register]
    });

    // 代理池健康度
    this.proxyPoolHealth = new promClient.Gauge({
      name: `${this.prefix}_proxy_pool_health`,
      help: 'Number of healthy proxies in pool',
      registers: [this.register]
    });

    // Guardian 运行状态
    this.guardianRunning = new promClient.Gauge({
      name: `${this.prefix}_guardian_running`,
      help: 'Guardian daemon running state (0=stopped, 1=running)',
      registers: [this.register]
    });
  }

  // ==========================================================================
  // 便捷方法
  // ==========================================================================

  /**
   * 记录缝合成功
   * @param {string} season - 赛季
   * @param {string} league - 联赛
   * @param {string} method - 匹配方法 (exact/fuzzy)
   */
  recordStitchSuccess(season, league, method = 'exact') {
    this.matchStitchedTotal.inc({ season, league, method });
  }

  /**
   * 记录缝合失败
   * @param {string} season - 赛季
   * @param {string} league - 联赛
   * @param {string} reason - 失败原因
   */
  recordStitchFailure(season, league, reason = 'unknown') {
    this.matchFailedTotal.inc({ season, league, reason });
  }

  /**
   * 记录选择器降级命中
   * @param {string} selectorName - 选择器名称
   * @param {string} pageType - 页面类型
   */
  recordSelectorFallback(selectorName, pageType = 'oddsportal') {
    this.selectorFallbackHit.inc({ selector_name: selectorName, page_type: pageType });
  }

  /**
   * 记录模糊匹配置信度
   * @param {number} confidence - 置信度 (0-1)
   * @param {string} season - 赛季
   * @param {string} league - 联赛
   */
  recordFuzzyConfidence(confidence, season, league) {
    this.fuzzyConfidence.observe({ season, league }, confidence);
  }

  /**
   * 记录导航延迟
   * @param {number} seconds - 延迟秒数
   * @param {string} league - 联赛
   * @param {string} pageType - 页面类型
   */
  recordNavigatorLatency(seconds, league, pageType = 'results') {
    this.navigatorLatency.observe({ league, page_type: pageType }, seconds);
  }

  /**
   * 记录扫描耗时
   * @param {number} seconds - 扫描耗时秒数
   * @param {string} season - 赛季
   * @param {string} league - 联赛
   */
  recordScanDuration(seconds, season, league) {
    this.scanDuration.observe({ season, league }, seconds);
  }

  /**
   * 记录重试延迟
   * @param {number} seconds - 延迟秒数
   * @param {string} errorType - 错误类型
   */
  recordRetryDelay(seconds, errorType) {
    this.retryDelay.observe({ error_type: errorType }, seconds);
  }

  /**
   * 记录僵尸进程清理
   * @param {string} processName - 进程名称
   */
  recordZombieKilled(processName = 'chromium') {
    this.zombieKilledTotal.inc({ process_name: processName });
  }

  /**
   * 记录代理切换
   * @param {string} reason - 切换原因
   */
  recordProxySwitch(reason = 'banned') {
    this.proxySwitchesTotal.inc({ reason });
  }

  /**
   * 记录熔断触发
   * @param {string} reason - 熔断原因
   */
  recordCircuitBreakerTrip(reason = 'threshold_reached') {
    this.circuitBreakerTrips.inc({ reason });
  }

  /**
   * 更新活跃锁数量
   * @param {number} count - 锁数量
   */
  setActiveLocks(count) {
    this.activeLocks.set(count);
  }

  /**
   * 更新缝合成功率
   * @param {number} rate - 成功率 (0-1)
   * @param {string} season - 赛季
   * @param {string} league - 联赛
   */
  setStitchingRate(rate, season, league) {
    this.stitchingRate.set({ season, league }, rate);
  }

  /**
   * 更新熔断器状态
   * @param {string} state - 状态 (closed/open/half_open)
   */
  setCircuitBreakerState(state) {
    const stateMap = { closed: 0, open: 1, half_open: 2 };
    this.circuitBreakerState.set(stateMap[state] || 0);
  }

  /**
   * 更新代理池健康度
   * @param {number} count - 健康代理数
   */
  setProxyPoolHealth(count) {
    this.proxyPoolHealth.set(count);
  }

  /**
   * 更新 Guardian 运行状态
   * @param {boolean} running - 是否运行中
   */
  setGuardianRunning(running) {
    this.guardianRunning.set(running ? 1 : 0);
  }

  // ==========================================================================
  // 输出方法
  // ==========================================================================

  /**
   * 获取 Prometheus 格式指标
   * @returns {string} Prometheus 格式文本
   */
  async getMetrics() {
    return await this.register.metrics();
  }

  /**
   * 获取指标注册表
   * @returns {promClient.Registry} 注册表实例
   */
  getRegistry() {
    return this.register;
  }

  /**
   * 重置所有指标 (仅用于测试)
   */
  reset() {
    this.register.resetMetrics();
    this.logger.info('metrics_reset');
  }

  /**
   * 获取指标统计摘要
   * @returns {Object} 指标摘要
   */
  getSummary() {
    return {
      counters: this.register.getMetricsAsJSON().filter(m => m.type === 'counter').length,
      histograms: this.register.getMetricsAsJSON().filter(m => m.type === 'histogram').length,
      gauges: this.register.getMetricsAsJSON().filter(m => m.type === 'gauge').length
    };
  }
}

module.exports = { ReconMetrics };
