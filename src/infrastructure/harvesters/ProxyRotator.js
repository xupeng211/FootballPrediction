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
 * ProxyRotator 类 - V6.0 住宅代理增强版
 */
class ProxyRotator {
  /**
   * @param {object} options - 配置选项
   * @param {string} options.strategy - 轮换策略: 'round-robin' | 'random' | 'least-used' | 'residential-priority'
   * @param {number} options.cooldownMs - 代理冷却时间 (默认60秒)
   * @param {number} options.maxFailures - 最大失败次数 (默认3)
   * @param {Array} options.residentialProxies - 住宅代理列表 [{host, port, username, password}]
   */
  constructor(options = {}) {
    this.strategy = options.strategy || 'round-robin';
    this.cooldownMs = options.cooldownMs || 60000;
    this.maxFailures = options.maxFailures || 3;

    // 获取22端口本地代理池 (Docker 环境使用 host.docker.internal 访问宿主机代理)
    const proxyHost = process.env.PROXY_HOST || 'host.docker.internal';
    this.localProxies = PROXY.getAllPorts().map((port, index) => ({
      id: index,
      port,
      host: proxyHost,
      url: `http://${proxyHost}:${port}`,
      server: `http://${proxyHost}:${port}`,
      type: 'datacenter',
      healthy: true,
      failCount: 0,
      useCount: 0,
      lastUsed: null,
      cooldownUntil: null,
      userAgent: USER_AGENTS[index % USER_AGENTS.length]
    }));

    // 住宅代理池 (高优先级)
    this.residentialProxies = (options.residentialProxies || []).map((proxy, index) => ({
      id: `res_${index}`,
      host: proxy.host,
      port: proxy.port,
      username: proxy.username,
      password: proxy.password,
      url: `http://${proxy.username}:${proxy.password}@${proxy.host}:${proxy.port}`,
      server: `http://${proxy.host}:${proxy.port}`,
      type: 'residential',
      healthy: true,
      failCount: 0,
      useCount: 0,
      lastUsed: null,
      cooldownUntil: null,
      userAgent: USER_AGENTS[index % USER_AGENTS.length],
      cost: proxy.cost || 0.1 // 每请求成本(美元)
    }));

    // 合并代理池 (住宅代理优先)
    this.proxies = [...this.residentialProxies, ...this.localProxies];
    
    // 住宅代理使用统计
    this.residentialStats = {
      totalCost: 0,
      sessionEstablishCount: 0
    };

    this.currentIndex = 0;

    this.logger = new StructuredLogger({
      component: 'ProxyRotator',
      logDir: '/app/logs/pipeline',
      enableStructured: true
    });

    this.logger.info('✅ ProxyRotator V6.0 初始化完成', {
      localProxyCount: this.localProxies.length,
      residentialProxyCount: this.residentialProxies.length,
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
      default: {
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

  rotate(options = {}) {
    const nextProxy = this.getNextProxy();
    this.logger.info('🔁 代理轮换', {
      reason: options.reason || 'manual',
      statusCode: options.statusCode || null,
      nextPort: nextProxy?.port || null
    });
    return nextProxy;
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
   * @param {object} options - 选项
   * @param {boolean} options.forceResidential - 强制使用住宅代理
   * @returns {object|null} Playwright代理配置
   */
  getPlaywrightProxy(options = {}) {
    let proxy;
    
    // 如果需要强制使用住宅代理
    if (options.forceResidential && this.residentialProxies.length > 0) {
      const availableResidential = this.residentialProxies.filter(p => {
        if (!p.healthy) return false;
        if (p.cooldownUntil && Date.now() < p.cooldownUntil) return false;
        if (p.failCount >= this.maxFailures) return false;
        return true;
      });
      
      if (availableResidential.length > 0) {
        proxy = availableResidential[0];
        this.logger.info('🏠 使用住宅代理', { proxy: proxy.id });
      }
    }
    
    // 如果没有强制要求或住宅代理不可用，使用普通代理
    if (!proxy) {
      proxy = this.getNextProxy();
    }
    
    if (!proxy) return null;

    // 构建Playwright代理配置
    const config = {
      server: proxy.server,
      bypass: undefined
    };

    // 住宅代理需要认证
    if (proxy.type === 'residential' && proxy.username) {
      config.username = proxy.username;
      config.password = proxy.password;
      
      // 记录成本
      this.residentialStats.totalCost += proxy.cost || 0.1;
      this.residentialStats.sessionEstablishCount++;
      
      this.logger.info('💰 住宅代理认证使用', { 
        proxy: proxy.id,
        accumulatedCost: this.residentialStats.totalCost.toFixed(2)
      });
    }

    return config;
  }

  /**
   * 获取住宅代理状态统计
   * @returns {object} 统计信息
   */
  getResidentialStats() {
    return {
      ...this.residentialStats,
      availableCount: this.residentialProxies.filter(p => p.healthy).length,
      totalCount: this.residentialProxies.length
    };
  }

  /**
   * 报告住宅代理成功建立会话
   * @param {string} proxyId - 代理ID
   */
  reportResidentialSessionSuccess(proxyId) {
    const proxy = this.residentialProxies.find(p => p.id === proxyId);
    if (proxy) {
      proxy.useCount++;
      proxy.lastUsed = Date.now();
      this.logger.info('✅ 住宅代理会话建立成功', { proxy: proxyId });
    }
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
    const resStats = this.getResidentialStats();

    console.log('\n' + '='.repeat(60));
    console.log('🛡️  NetworkShield V6.0 代理状态报告');
    console.log('='.repeat(60));
    console.log(`本地代理: ${this.localProxies.length} | 住宅代理: ${this.residentialProxies.length}`);
    console.log(`健康可用: ${status.healthy} ✅`);
    console.log(`冷却中:   ${status.cooling} ⏳`);
    console.log(`已死亡:   ${status.dead} 💀`);
    console.log(`立即可用: ${status.available} 🟢`);
    console.log(`总请求数: ${status.utilization}`);
    
    // 住宅代理成本统计
    if (this.residentialProxies.length > 0) {
      console.log('\n💰 住宅代理成本:');
      console.log(`  累计成本: $${resStats.totalCost.toFixed(2)} USD`);
      console.log(`  会话建立: ${resStats.sessionEstablishCount} 次`);
      console.log(`  平均成本: $${resStats.sessionEstablishCount > 0 ? (resStats.totalCost / resStats.sessionEstablishCount).toFixed(3) : '0.000'}/请求`);
    }
    
    console.log('='.repeat(60));

    // 打印住宅代理详情
    if (this.residentialProxies.length > 0) {
      console.log('\n🏠 住宅代理详情:');
      this.residentialProxies.forEach(p => {
        let statusIcon = '✅';
        if (!p.healthy) statusIcon = '💀';
        else if (p.cooldownUntil && Date.now() < p.cooldownUntil) statusIcon = '⏳';
        
        console.log(`  ${statusIcon} ${p.host}:${p.port}: 使用${p.useCount}次 成本$${(p.useCount * p.cost).toFixed(2)}`);
      });
    }

    // 打印本地代理详情
    console.log('\n🌐 本地代理详情:');
    this.localProxies.forEach(p => {
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
