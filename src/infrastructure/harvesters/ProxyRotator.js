/**
 * ProxyRotator - ProxyProvider 兼容包装层
 * ======================================
 *
 * 保留 Recon / Backfill 旧接口：
 * - getNextProxy()
 * - rotate()
 * - getPlaywrightProxy()
 * - reportSuccess()
 * - reportFailure()
 * - getHealthStatus()
 * - getStats()
 *
 * 22 端口本地代理的真实状态统一委托给 ProxyProvider。
 */

'use strict';

const { StructuredLogger } = require('../../utils/StructuredLogger');
const { getProxyProvider } = require('../network/ProxyProvider');

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

class ProxyRotator {
  constructor(options = {}) {
    this.strategy = options.strategy || 'round-robin';
    this.cooldownMs = Number.isFinite(Number(options.cooldownMs)) && Number(options.cooldownMs) > 0
      ? Number(options.cooldownMs)
      : 90000;
    this.maxFailures = Number.isFinite(Number(options.maxFailures)) && Number(options.maxFailures) > 0
      ? Number(options.maxFailures)
      : 8;
    this.consumer = options.consumer || 'recon-engine';
    this.proxyProviderOptions = options.proxyProviderOptions || {};
    this.proxyProvider = options.proxyProvider || getProxyProvider(this.proxyProviderOptions);
    this.sequence = 0;
    this.currentIndex = 0;
    this.localProxyStats = new Map();

    this.localProxies = this.proxyProvider.getPorts().map((port, index) => ({
      id: index,
      ...this.proxyProvider.buildAssignment(port),
      type: 'datacenter',
      userAgent: USER_AGENTS[index % USER_AGENTS.length]
    }));

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
      cost: proxy.cost || 0.1
    }));

    this.proxies = [...this.residentialProxies, ...this.localProxies];
    this.residentialStats = {
      totalCost: 0,
      sessionEstablishCount: 0
    };

    this.logger = options.logger || new StructuredLogger({
      component: 'ProxyRotator',
      logDir: '/app/logs/pipeline',
      enableStructured: true
    });

    this.logger.info('ProxyRotator 已切换为 ProxyProvider 兼容层', {
      localProxyCount: this.localProxies.length,
      residentialProxyCount: this.residentialProxies.length,
      strategy: this.strategy,
      host: this.proxyProvider.getHost()
    });
  }

  getNextProxy(options = {}) {
    let selected = null;

    if (options.forceResidential || this.strategy === 'residential-priority') {
      selected = this._selectResidentialProxy();
    }

    if (!selected) {
      const available = this._getAvailableLocalProxies();
      if (available.length === 0) {
        this.logger.warn('⚠️  无可用代理', {
          total: this.localProxies.length,
          healthy: this.getHealthStatus().healthy,
          available: this.getHealthStatus().available
        });
        return null;
      }

      selected = this._selectLocalProxy(available);
    }

    if (selected.type === 'residential') {
      this._recordResidentialUsage(selected);
      return {
        id: selected.id,
        host: selected.host,
        port: selected.port,
        url: selected.url,
        server: selected.server,
        userAgent: selected.userAgent,
        type: selected.type,
        username: selected.username,
        password: selected.password
      };
    }

    const { lease, assignment } = this.proxyProvider.acquireAssignmentSync({
      consumer: this.consumer,
      sessionKey: `${this.consumer}:${++this.sequence}`,
      sticky: false,
      preferredPort: selected.port,
      excludePorts: options.excludePorts || []
    });
    this.proxyProvider.releaseSync(lease.id);
    this._recordLocalUsage(assignment.port);
    const proxyMeta = this.localProxies.find(proxy => proxy.port === assignment.port) || selected;
    const localStat = this._getLocalStat(assignment.port);

    this.logger.debug('🔄 选择代理', {
      port: assignment.port,
      strategy: this.strategy,
      useCount: localStat.useCount
    });

    return {
      id: proxyMeta.id,
      host: assignment.host,
      port: assignment.port,
      url: assignment.url,
      server: assignment.server,
      userAgent: proxyMeta.userAgent,
      type: proxyMeta.type,
      sessionId: lease.id
    };
  }

  rotate(options = {}) {
    const excludePorts = [];
    if (options.currentPort) {
      excludePorts.push(options.currentPort);
    }

    const nextProxy = this.getNextProxy({
      excludePorts,
      forceResidential: options.forceResidential
    });

    this.logger.info('🔁 代理轮换', {
      reason: options.reason || 'manual',
      statusCode: options.statusCode || null,
      currentPort: options.currentPort || null,
      nextPort: nextProxy?.port || null
    });

    return nextProxy;
  }

  reportSuccess(port) {
    if (this.localProxies.some(proxy => proxy.port === port)) {
      void this.proxyProvider.reportPortSuccess(port, { statusCode: 200 });
      this.logger.debug('✅ 代理报告成功', { port });
      return;
    }

    const residential = this.residentialProxies.find(proxy => proxy.port === port);
    if (residential) {
      residential.failCount = 0;
      residential.healthy = true;
      this.logger.debug('✅ 住宅代理报告成功', { port });
    }
  }

  reportFailure(port, errorType = 'other') {
    if (this.localProxies.some(proxy => proxy.port === port)) {
      void this.proxyProvider.reportPortFailure(port, {
        statusCode: this._mapErrorTypeToStatusCode(errorType),
        reason: errorType
      });

      const node = this._getProviderNode(port);
      const failCount = node?.failureCount || 0;
      if (String(errorType) === '503' && !node?.cooling && failCount < this.maxFailures) {
        this.logger.warn('👀 代理进入 503 观察期', {
          port,
          failCount,
          observationThreshold: this.maxFailures,
          reason: errorType
        });
      }
      if (this._isCoolingNode(node, failCount)) {
        this.logger.warn('❌ 代理进入冷却', {
          port,
          failCount,
          cooldownMs: this.cooldownMs,
          reason: errorType
        });
      }
      if (failCount >= this.maxFailures) {
        this.logger.error('💀 代理标记为死亡', { port, failCount });
      }
      return;
    }

    const residential = this.residentialProxies.find(proxy => proxy.port === port);
    if (!residential) {
      return;
    }

    residential.failCount++;
    if (String(errorType) === '403' || residential.failCount >= this.maxFailures) {
      residential.cooldownUntil = Date.now() + this.cooldownMs;
    }
    if (residential.failCount >= this.maxFailures * 2) {
      residential.healthy = false;
    }
  }

  getPlaywrightProxy(options = {}) {
    const proxy = this.getNextProxy({
      forceResidential: options.forceResidential
    });

    if (!proxy) {
      return null;
    }

    const config = {
      server: proxy.server,
      bypass: undefined
    };

    if (proxy.type === 'residential' && proxy.username) {
      config.username = proxy.username;
      config.password = proxy.password;
      this.residentialStats.totalCost += proxy.cost || 0.1;
      this.residentialStats.sessionEstablishCount++;
      this.logger.info('💰 住宅代理认证使用', {
        proxy: proxy.id,
        accumulatedCost: this.residentialStats.totalCost.toFixed(2)
      });
    }

    return config;
  }

  getResidentialStats() {
    return {
      ...this.residentialStats,
      availableCount: this.residentialProxies.filter(proxy => this._isResidentialAvailable(proxy)).length,
      totalCount: this.residentialProxies.length
    };
  }

  reportResidentialSessionSuccess(proxyId) {
    const proxy = this.residentialProxies.find(item => item.id === proxyId);
    if (!proxy) {
      return;
    }

    proxy.useCount++;
    proxy.lastUsed = Date.now();
    this.logger.info('✅ 住宅代理会话建立成功', { proxy: proxyId });
  }

  getRandomUserAgent() {
    return USER_AGENTS[Math.floor(Math.random() * USER_AGENTS.length)];
  }

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

  getHealthStatus() {
    const nodeStates = this.proxyProvider.getNodeStates();
    const minHealthScore = Number(this.proxyProvider?.config?.minHealthScore || 0);
    const residentialAvailable = this.residentialProxies.filter(proxy => this._isResidentialAvailable(proxy)).length;
    const healthy = nodeStates.filter(node => (
      node.eligibleForLease
      && node.failureCount < this.maxFailures
    )).length + residentialAvailable;
    const cooling = nodeStates.filter(node => node.cooling || node.isolated).length
      + this.residentialProxies.filter(proxy => proxy.cooldownUntil && Date.now() < proxy.cooldownUntil).length;
    const dead = nodeStates.filter(node => (
      (!node.probeHealthy || node.failureCount >= this.maxFailures || node.healthScore < minHealthScore)
      && !node.cooling
      && !node.isolated
    )).length
      + this.residentialProxies.filter(proxy => !proxy.healthy || proxy.failCount >= this.maxFailures * 2).length;
    const utilization = Array.from(this.localProxyStats.values())
      .reduce((sum, stat) => sum + stat.useCount, 0)
      + this.residentialProxies.reduce((sum, proxy) => sum + proxy.useCount, 0);

    return {
      total: nodeStates.length + this.residentialProxies.length,
      healthy,
      cooling,
      dead,
      available: healthy,
      utilization
    };
  }

  getStats() {
    return {
      ...this.getHealthStatus(),
      host: this.proxyProvider.getHost()
    };
  }

  resetAll() {
    this.proxyProvider.resetAll();
    this.localProxyStats.clear();

    this.residentialProxies.forEach(proxy => {
      proxy.healthy = true;
      proxy.failCount = 0;
      proxy.useCount = 0;
      proxy.lastUsed = null;
      proxy.cooldownUntil = null;
    });

    this.logger.info('🔄 所有代理状态已重置');
  }

  printStatusReport() {
    const status = this.getHealthStatus();
    const resStats = this.getResidentialStats();

    console.log('\n' + '='.repeat(60));
    console.log('🛡️  ProxyProvider 统一代理状态报告');
    console.log('='.repeat(60));
    console.log(`本地代理: ${this.localProxies.length} | 住宅代理: ${this.residentialProxies.length}`);
    console.log(`健康可用: ${status.healthy} ✅`);
    console.log(`冷却中:   ${status.cooling} ⏳`);
    console.log(`已死亡:   ${status.dead} 💀`);
    console.log(`立即可用: ${status.available} 🟢`);
    console.log(`总请求数: ${status.utilization}`);

    if (this.residentialProxies.length > 0) {
      console.log('\n💰 住宅代理成本:');
      console.log(`  累计成本: $${resStats.totalCost.toFixed(2)} USD`);
      console.log(`  会话建立: ${resStats.sessionEstablishCount} 次`);
      console.log(`  平均成本: $${resStats.sessionEstablishCount > 0 ? (resStats.totalCost / resStats.sessionEstablishCount).toFixed(3) : '0.000'}/请求`);
    }

    console.log('='.repeat(60));

    if (this.residentialProxies.length > 0) {
      console.log('\n🏠 住宅代理详情:');
      this.residentialProxies.forEach(proxy => {
        let statusIcon = '✅';
        if (!proxy.healthy) statusIcon = '💀';
        else if (proxy.cooldownUntil && Date.now() < proxy.cooldownUntil) statusIcon = '⏳';

        console.log(`  ${statusIcon} ${proxy.host}:${proxy.port}: 使用${proxy.useCount}次 成本$${(proxy.useCount * proxy.cost).toFixed(2)}`);
      });
    }

    console.log('\n🌐 本地代理详情:');
    const minHealthScore = Number(this.proxyProvider?.config?.minHealthScore || 0);
    this.proxyProvider.getNodeStates().forEach(node => {
      const stat = this._getLocalStat(node.port);
      let statusIcon = '✅';
      if (node.failureCount >= this.maxFailures || !node.probeHealthy || node.healthScore < minHealthScore) statusIcon = '💀';
      else if (node.cooling || node.isolated) statusIcon = '⏳';
      else if (node.failureCount > 0) statusIcon = '⚠️';

      console.log(`  ${statusIcon} Port ${node.port}: 使用${stat.useCount}次 失败${node.failureCount}次 健康分${node.healthScore}`);
    });

    return status;
  }

  _selectResidentialProxy() {
    const available = this.residentialProxies.filter(proxy => this._isResidentialAvailable(proxy));
    return available[0] || null;
  }

  _selectLocalProxy(available) {
    switch (this.strategy) {
      case 'random':
        return available[Math.floor(Math.random() * available.length)];

      case 'least-used':
        return available.reduce((best, current) => (
          this._getLocalStat(current.port).useCount < this._getLocalStat(best.port).useCount ? current : best
        ), available[0]);

      case 'round-robin':
      case 'residential-priority':
      default:
        return this._selectRoundRobin(available);
    }
  }

  _selectRoundRobin(available) {
    const availablePorts = new Set(available.map(proxy => proxy.port));
    for (let attempts = 0; attempts < this.localProxies.length; attempts++) {
      const proxy = this.localProxies[this.currentIndex % this.localProxies.length];
      this.currentIndex++;
      if (availablePorts.has(proxy.port)) {
        return proxy;
      }
    }
    return available[0];
  }

  _getAvailableLocalProxies() {
    const nodeStates = new Map(
      this.proxyProvider.getNodeStates().map(node => [node.port, node])
    );

    return this.localProxies.filter(proxy => {
      const node = nodeStates.get(proxy.port);
      if (!node) {
        return false;
      }

      return node.probeHealthy
        && node.eligibleForLease
        && !node.cooling
        && !node.isolated
        && node.failureCount < this.maxFailures;
    });
  }

  _recordLocalUsage(port) {
    const stat = this._getLocalStat(port);
    stat.useCount++;
    stat.lastUsed = Date.now();
  }

  _recordResidentialUsage(proxy) {
    proxy.useCount++;
    proxy.lastUsed = Date.now();
  }

  _getLocalStat(port) {
    if (!this.localProxyStats.has(port)) {
      this.localProxyStats.set(port, {
        useCount: 0,
        lastUsed: null
      });
    }

    return this.localProxyStats.get(port);
  }

  _getProviderNode(port) {
    return this.proxyProvider.getNodeStates().find(node => node.port === port) || null;
  }

  _isCoolingNode(node, failCount) {
    if (!node) {
      return false;
    }

    return node.cooling || node.isolated || failCount >= this.maxFailures;
  }

  _isResidentialAvailable(proxy) {
    if (!proxy.healthy) {
      return false;
    }
    if (proxy.cooldownUntil && Date.now() < proxy.cooldownUntil) {
      return false;
    }
    return proxy.failCount < this.maxFailures;
  }

  _mapErrorTypeToStatusCode(errorType) {
    switch (String(errorType || '').toLowerCase()) {
      case '403':
        return 403;
      case '429':
      case 'rate_limited':
        return 429;
      case '503':
        return 503;
      default:
        return null;
    }
  }
}

module.exports = { ProxyRotator, USER_AGENTS };
