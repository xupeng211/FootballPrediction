/**
 * ProxyRotator - V6.0 P0 代理轮换模块
 * ===================================
 *
 * NetworkShield 22端口防御阵列管理器
 * 提供轮询、随机选择、健康检查、冷却恢复等功能
 *
 * @module infrastructure/harvesters/ProxyRotator
 * @version V6.0.0-FORTIFY
 * @since 2026-03-15
 */

'use strict';

const { StructuredLogger } = require('../../utils/StructuredLogger');
const { PROXY } = require('../../../config/registry');

// User-Agent 池 (用于隐身)
const USER_AGENTS = [
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
  'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0',
  'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/121.0',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0'
];

/**
 * ProxyRotator 类
 */
class ProxyRotator {
  /**
   * @param {object} options - 配置选项
   * @param {string} options.strategy - 轮换策略: 'round-robin' | 'random' | 'least-used'
   * @param {number} options.cooldownMs - 代理冷却时间 (默认60秒)
   * @param {number} options.maxFailures - 最大失败次数 (默认3)
   */
  constructor(options = {}) {
    this.strategy = options.strategy || 'round-robin';
    this.cooldownMs = options.cooldownMs || 60000;
    this.maxFailures = options.maxFailures || 3;

    // 获取22端口代理池
    this.proxies = PROXY.getAllPorts().map((port, index) => ({
      id: index,
      port,
      host: '127.0.0.1',
      url: `http://127.0.0.1:${port}`,
      healthy: true,
      failCount: 0,
      useCount: 0,
      lastUsed: null,
      cooldownUntil: null,
      userAgent: USER_AGENTS[index % USER_AGENTS.length]
    }));

    this.currentIndex = 0;

    this.logger = new StructuredLogger({
      component: 'ProxyRotator',
      logDir: '/app/logs/pipeline',
      enableStructured: true
    });

    this.logger.info('✅ ProxyRotator 初始化完成', {
      proxyCount: this.proxies.length,
      strategy: this.strategy
    });
  }

  /**
   * 获取下一个可用代理
   * @returns {object|null} 代理配置或null
   */
  getNextProxy() {
    const now = Date.now();

    // 获取可用代理列表
    const available = this.proxies.filter(p => {
      // 检查是否健康
      if (!p.healthy) return false;
      // 检查是否在冷却期
      if (p.cooldownUntil && now < p.cooldownUntil) return false;
      // 检查失败次数
      if (p.failCount >= this.maxFailures) return false;
      return true;
    });

    if (available.length === 0) {
      this.logger.warn('⚠️  无可用代理', {
        total: this.proxies.length,
        healthy: this.proxies.filter(p => p.healthy).length
      });
      return null;
    }

    let selected;

    switch (this.strategy) {
      case 'random':
        selected = available[Math.floor(Math.random() * available.length)];
        break;

      case 'least-used':
        selected = available.reduce((min, p) =>
          p.useCount < min.useCount ? p : min
        , available[0]);
        break;

      case 'round-robin':
      default:
        // 轮询: 从当前索引开始查找下一个可用
        const startIndex = this.currentIndex;
        do {
          const proxy = this.proxies[this.currentIndex % this.proxies.length];
          this.currentIndex++;

          if (available.includes(proxy)) {
            selected = proxy;
            break;
          }
        } while (this.currentIndex % this.proxies.length !== startIndex % this.proxies.length);
        break;
    }

    if (!selected) {
      selected = available[0];
    }

    // 更新代理状态
    selected.useCount++;
    selected.lastUsed = now;

    this.logger.debug('🔄 选择代理', {
      port: selected.port,
      strategy: this.strategy,
      useCount: selected.useCount,
      availableCount: available.length
    });

    return {
      id: selected.id,
      port: selected.port,
      host: selected.host,
      url: selected.url,
      userAgent: selected.userAgent,
      server: selected.url // Playwright proxy server格式
    };
  }

  /**
   * 报告代理成功
   * @param {number} port - 代理端口
   */
  reportSuccess(port) {
    const proxy = this.proxies.find(p => p.port === port);
    if (proxy) {
      // 重置失败计数
      proxy.failCount = 0;
      proxy.healthy = true;

      this.logger.debug('✅ 代理报告成功', { port });
    }
  }

  /**
   * 报告代理失败
   * @param {number} port - 代理端口
   * @param {string} errorType - 错误类型: 'timeout' | '403' | 'network' | 'other'
   */
  reportFailure(port, errorType = 'other') {
    const proxy = this.proxies.find(p => p.port === port);
    if (!proxy) return;

    proxy.failCount++;

    // 根据错误类型处理
    if (errorType === '403' || proxy.failCount >= this.maxFailures) {
      // 403错误或连续失败: 进入冷却
      proxy.cooldownUntil = Date.now() + this.cooldownMs;
      this.logger.warn('❌ 代理进入冷却', {
        port,
        failCount: proxy.failCount,
        cooldownMs: this.cooldownMs,
        reason: errorType
      });
    }

    if (proxy.failCount >= this.maxFailures * 2) {
      // 超过2倍阈值: 标记为不健康
      proxy.healthy = false;
      this.logger.error('💀 代理标记为死亡', {
        port,
        failCount: proxy.failCount
      });
    }
  }

  /**
   * 获取Playwright代理配置
   * @returns {object|null} Playwright代理配置
   */
  getPlaywrightProxy() {
    const proxy = this.getNextProxy();
    if (!proxy) return null;

    return {
      server: proxy.server,
      // Playwright支持的用户代理注入
      bypass: undefined
    };
  }

  /**
   * 获取随机User-Agent
   * @returns {string} User-Agent字符串
   */
  getRandomUserAgent() {
    return USER_AGENTS[Math.floor(Math.random() * USER_AGENTS.length)];
  }

  /**
   * 获取请求头 (含随机UA)
   * @returns {object} 请求头对象
   */
  getRequestHeaders() {
    return {
      'User-Agent': this.getRandomUserAgent(),
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
      'Accept-Language': 'en-US,en;q=0.5',
      'Accept-Encoding': 'gzip, deflate, br',
      'DNT': '1',
      'Connection': 'keep-alive',
      'Upgrade-Insecure-Requests': '1',
      'Sec-Fetch-Dest': 'document',
      'Sec-Fetch-Mode': 'navigate',
      'Sec-Fetch-Site': 'none',
      'Cache-Control': 'max-age=0'
    };
  }

  /**
   * 获取代理健康状态
   * @returns {object} 健康状态统计
   */
  getHealthStatus() {
    const now = Date.now();

    const healthy = this.proxies.filter(p => p.healthy).length;
    const cooling = this.proxies.filter(p =>
      p.cooldownUntil && now < p.cooldownUntil
    ).length;
    const dead = this.proxies.filter(p =>
      !p.healthy || p.failCount >= this.maxFailures * 2
    ).length;

    return {
      total: this.proxies.length,
      healthy,
      cooling,
      dead,
      available: healthy - cooling,
      utilization: this.proxies.reduce((sum, p) => sum + p.useCount, 0)
    };
  }

  /**
   * 重置所有代理状态
   */
  resetAll() {
    this.proxies.forEach(p => {
      p.healthy = true;
      p.failCount = 0;
      p.cooldownUntil = null;
    });

    this.logger.info('🔄 所有代理状态已重置');
  }

  /**
   * 打印代理状态报告
   */
  printStatusReport() {
    const status = this.getHealthStatus();

    console.log('\n' + '='.repeat(60));
    console.log('🛡️  NetworkShield 代理状态报告');
    console.log('='.repeat(60));
    console.log(`总代理数: ${status.total}`);
    console.log(`健康可用: ${status.healthy} ✅`);
    console.log(`冷却中:   ${status.cooling} ⏳`);
    console.log(`已死亡:   ${status.dead} 💀`);
    console.log(`立即可用: ${status.available} 🟢`);
    console.log(`总请求数: ${status.utilization}`);
    console.log('='.repeat(60));

    // 打印每个代理的详情
    console.log('\n代理详情:');
    this.proxies.forEach(p => {
      let statusIcon = '✅';
      if (!p.healthy) statusIcon = '💀';
      else if (p.cooldownUntil && Date.now() < p.cooldownUntil) statusIcon = '⏳';
      else if (p.failCount > 0) statusIcon = '⚠️';

      console.log(`  ${statusIcon} Port ${p.port}: 使用${p.useCount}次 失败${p.failCount}次`);
    });

    return status;
  }
}

module.exports = { ProxyRotator, USER_AGENTS };
