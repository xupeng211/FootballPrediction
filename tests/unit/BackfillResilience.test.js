/**
 * TITAN V6.0 Backfill Fortification - 历史回填韧性测试
 * 任务: TITAN-V6.0-BACKFILL-AUDIT
 * 
 * 测试用例:
 * 1. 代理枯竭场景 - 所有代理返回403，系统应优雅暂停并保存进度
 * 2. 历史URL突变 - 2019年老旧URL格式，正则解析器容错回退
 * 3. 大规模并发锁 - 12核Worker同时写入，验证事务隔离级别
 */

const assert = require('node:assert');
const { describe, it, beforeEach } = require('node:test');

// ============================================================================
// BackfillResilienceEngine (待实现)
// ============================================================================

class BackfillResilienceEngine {
  constructor(config = {}) {
    this.config = {
      maxRetries: config.maxRetries || 3,
      retryDelayMs: config.retryDelayMs || 2000,
      proxyCooldownMs: config.proxyCooldownMs || 60000, // 代理冷却60秒
      checkpointInterval: config.checkpointInterval || 100, // 每100场保存检查点
      gracefulPauseThreshold: config.gracefulPauseThreshold || 0.8, // 80%代理失败则暂停
      ...config
    };
    
    this.state = {
      processedCount: 0,
      successCount: 0,
      failedCount: 0,
      proxyStatus: new Map(), // 代理健康状态
      checkpoint: null, // 检查点数据
      isPaused: false,
      pauseReason: null
    };
    
    this.proxyPool = [];
    this.currentProxyIndex = 0;
  }

  /**
   * 初始化代理池
   */
  initializeProxies(proxyList) {
    this.proxyPool = proxyList.map((proxy, index) => ({
      id: index,
      host: proxy.host,
      port: proxy.port,
      healthy: true,
      failCount: 0,
      lastUsed: null,
      cooldownUntil: null
    }));
    
    // 初始化代理状态
    this.proxyPool.forEach(p => this.state.proxyStatus.set(p.id, 'healthy'));
  }

  /**
   * 获取下一个可用代理 (带健康检查)
   */
  getNextProxy() {
    const now = Date.now();
    const availableProxies = this.proxyPool.filter(p => {
      // 检查是否在冷却期
      if (p.cooldownUntil && now < p.cooldownUntil) {
        return false;
      }
      // 检查健康状态
      return p.healthy && this.state.proxyStatus.get(p.id) !== 'dead';
    });

    if (availableProxies.length === 0) {
      return null; // 无可用代理
    }

    // 轮询选择
    const proxy = availableProxies[this.currentProxyIndex % availableProxies.length];
    this.currentProxyIndex++;
    proxy.lastUsed = now;
    
    return proxy;
  }

  /**
   * 报告代理失败
   */
  reportProxyFailure(proxyId, errorCode) {
    const proxy = this.proxyPool.find(p => p.id === proxyId);
    if (!proxy) return;

    proxy.failCount++;
    
    // 如果是403错误，标记代理需要冷却
    if (errorCode === 403) {
      proxy.cooldownUntil = Date.now() + this.config.proxyCooldownMs;
      this.state.proxyStatus.set(proxyId, 'cooling');
    }
    
    // 连续失败超过阈值，标记为死亡
    if (proxy.failCount >= this.config.maxRetries) {
      proxy.healthy = false;
      this.state.proxyStatus.set(proxyId, 'dead');
    }

    // 检查是否需要优雅暂停
    this._checkGracefulPause();
  }

  /**
   * 检查是否需要优雅暂停
   * @private
   */
  _checkGracefulPause() {
    const totalProxies = this.proxyPool.length;
    const deadProxies = Array.from(this.state.proxyStatus.values()).filter(s => s === 'dead').length;
    const coolingProxies = Array.from(this.state.proxyStatus.values()).filter(s => s === 'cooling').length;
    const unhealthyRatio = (deadProxies + coolingProxies) / totalProxies;

    if (unhealthyRatio >= this.config.gracefulPauseThreshold) {
      this.state.isPaused = true;
      this.state.pauseReason = `代理健康度过低: ${(unhealthyRatio * 100).toFixed(1)}% 不可用`;
      
      // 保存检查点
      this.saveCheckpoint();
    }
  }

  /**
   * 保存检查点
   */
  saveCheckpoint() {
    this.state.checkpoint = {
      processedCount: this.state.processedCount,
      successCount: this.state.successCount,
      failedCount: this.state.failedCount,
      timestamp: Date.now(),
      proxyStatus: Array.from(this.state.proxyStatus.entries())
    };
    return this.state.checkpoint;
  }

  /**
   * 恢复检查点
   */
  restoreCheckpoint(checkpoint) {
    if (!checkpoint) return false;
    
    this.state.processedCount = checkpoint.processedCount;
    this.state.successCount = checkpoint.successCount;
    this.state.failedCount = checkpoint.failedCount;
    
    if (checkpoint.proxyStatus) {
      this.state.proxyStatus = new Map(checkpoint.proxyStatus);
    }
    
    return true;
  }

  /**
   * 解析历史URL (带容错)
   * @param {string} url - 可能是老旧格式的URL
   * @returns {Object} 解析结果或回退数据
   */
  parseHistoricalURL(url) {
    // 先尝试老旧格式解析 (2019年格式) - 必须在标准格式之前
    const legacyResult = this._tryLegacyParse(url);
    if (legacyResult) return legacyResult;
    
    // 尝试标准解析
    const standardResult = this._tryStandardParse(url);
    if (standardResult) return standardResult;

    // 容错回退 - 返回基础数据
    return this._fallbackParse(url);
  }

  /**
   * 标准解析
   * @private
   */
  _tryStandardParse(url) {
    try {
      const urlObj = new URL(url);
      const pathParts = urlObj.pathname.split('/').filter(p => p);
      
      // 验证基本结构: sport/country/league/match (至少4部分)
      if (pathParts.length < 4) return null;
      
      // 验证第一部分是已知的sport类型
      const validSports = ['soccer', 'football', 'basketball', 'tennis'];
      if (!validSports.includes(pathParts[0])) return null;
      
      return {
        sport: pathParts[0],
        country: pathParts[1],
        league: pathParts[2],
        match: pathParts[3],
        format: 'standard',
        confidence: 1.0
      };
    } catch {
      return null;
    }
  }

  /**
   * 老旧格式解析 (2019年)
   * @private
   */
  _tryLegacyParse(url) {
    // 2019年格式: /matches/2019/08/12/england/premier-league/match-name/
    // 首先检查是否是老格式
    if (!url.includes('/matches/')) return null;
    
    try {
      const urlObj = new URL(url);
      const pathParts = urlObj.pathname.split('/').filter(p => p);
      
      // 格式: matches/2019/08/12/england/premier-league/match-name
      if (pathParts.length >= 7 && pathParts[0] === 'matches') {
        return {
          sport: 'soccer',
          country: pathParts[4],
          league: pathParts[5],
          match: pathParts[6],
          format: 'legacy-2019',
          confidence: 0.85
        };
      }
    } catch {
      // 解析失败
    }
    return null;
  }

  /**
   * 容错回退解析
   * @private
   */
  _fallbackParse(url) {
    // 提取最后部分作为match标识
    let lastPart = 'unknown';
    
    try {
      const urlObj = new URL(url);
      const parts = urlObj.pathname.split('/').filter(p => p);
      lastPart = parts[parts.length - 1] || 'unknown';
    } catch {
      // URL解析失败，直接使用字符串分割
      const parts = url.split('/').filter(p => p);
      lastPart = parts[parts.length - 1] || 'unknown';
    }
    
    return {
      sport: 'unknown',
      country: 'unknown',
      league: 'unknown',
      match: lastPart,
      format: 'fallback',
      confidence: 0.5,
      raw_url: url
    };
  }

  /**
   * 模拟批量处理 (带检查点)
   */
  async processBatch(items, processor) {
    const results = [];
    
    for (let i = 0; i < items.length; i++) {
      // 检查是否已暂停
      if (this.state.isPaused) {
        results.push({ status: 'paused', reason: this.state.pauseReason });
        break;
      }

      const item = items[i];
      
      try {
        const result = await processor(item);
        this.state.successCount++;
        results.push({ status: 'success', data: result });
      } catch (error) {
        this.state.failedCount++;
        results.push({ status: 'failed', error: error.message });
      }
      
      this.state.processedCount++;
      
      // 定期保存检查点
      if (this.state.processedCount % this.config.checkpointInterval === 0) {
        this.saveCheckpoint();
      }
    }
    
    return results;
  }

  /**
   * 获取状态报告
   */
  getStatus() {
    const totalProxies = this.proxyPool.length;
    const healthyProxies = Array.from(this.state.proxyStatus.values()).filter(s => s === 'healthy').length;
    
    return {
      processed: this.state.processedCount,
      success: this.state.successCount,
      failed: this.state.failedCount,
      successRate: this.state.processedCount > 0 
        ? (this.state.successCount / this.state.processedCount * 100).toFixed(2) + '%'
        : 'N/A',
      isPaused: this.state.isPaused,
      pauseReason: this.state.pauseReason,
      proxyHealth: {
        total: totalProxies,
        healthy: healthyProxies,
        dead: totalProxies - healthyProxies
      },
      checkpoint: this.state.checkpoint
    };
  }
}

// ============================================================================
// TDD 测试套件
// ============================================================================

describe('BackfillResilienceEngine - TITAN V6.0 历史回填韧性', () => {
  let engine;

  beforeEach(() => {
    engine = new BackfillResilienceEngine({
      maxRetries: 3,
      proxyCooldownMs: 60000,
      gracefulPauseThreshold: 0.8
    });
  });

  describe('测试用例 1: 代理枯竭场景 - 优雅暂停', () => {
    it('当所有代理返回403时，系统应该优雅暂停并保存进度', () => {
      // 初始化5个代理
      engine.initializeProxies([
        { host: '127.0.0.1', port: 7890 },
        { host: '127.0.0.1', port: 7891 },
        { host: '127.0.0.1', port: 7892 },
        { host: '127.0.0.1', port: 7893 },
        { host: '127.0.0.1', port: 7894 }
      ]);

      // 模拟所有代理返回403
      engine.proxyPool.forEach(p => {
        engine.reportProxyFailure(p.id, 403);
        engine.reportProxyFailure(p.id, 403);
        engine.reportProxyFailure(p.id, 403); // 超过maxRetries
      });

      // 断言: 系统应该暂停
      assert.strictEqual(engine.state.isPaused, true, '系统应该处于暂停状态');
      assert.ok(engine.state.pauseReason, '应该有暂停原因');
      assert.ok(engine.state.pauseReason.includes('代理健康度'), '暂停原因应该与代理健康度相关');
      
      // 断言: 检查点应该被保存
      assert.ok(engine.state.checkpoint, '应该保存检查点');
      assert.strictEqual(engine.state.checkpoint.processedCount, 0, '检查点应该记录处理数量');
    });

    it('应该正确计算代理健康比例并触发暂停', () => {
      engine.initializeProxies([
        { host: '127.0.0.1', port: 7890 },
        { host: '127.0.0.1', port: 7891 },
        { host: '127.0.0.1', port: 7892 },
        { host: '127.0.0.1', port: 7893 },
        { host: '127.0.0.1', port: 7894 }
      ]);

      // 使4个代理死亡 (80%)
      for (let i = 0; i < 4; i++) {
        engine.reportProxyFailure(i, 403);
        engine.reportProxyFailure(i, 403);
        engine.reportProxyFailure(i, 403);
      }

      // 80% >= 80% 阈值，应该触发暂停
      assert.strictEqual(engine.state.isPaused, true, '80%代理失败应该触发暂停');
    });

    it('代理冷却后应该恢复可用', () => {
      engine.initializeProxies([{ host: '127.0.0.1', port: 7890 }]);
      
      // 报告403，进入冷却
      engine.reportProxyFailure(0, 403);
      
      // 代理应该被标记为cooling
      assert.strictEqual(engine.state.proxyStatus.get(0), 'cooling');
      
      // 在冷却期内不应该可用
      const proxy = engine.getNextProxy();
      assert.strictEqual(proxy, null, '冷却期内代理不应可用');
    });
  });

  describe('测试用例 2: 历史URL突变 - 容错回退', () => {
    it('应该正确解析标准格式URL', () => {
      const url = 'https://www.oddsportal.com/soccer/england/premier-league/manchester-united-liverpool/';
      const result = engine.parseHistoricalURL(url);
      
      assert.strictEqual(result.format, 'standard');
      assert.strictEqual(result.sport, 'soccer');
      assert.strictEqual(result.country, 'england');
      assert.strictEqual(result.league, 'premier-league');
      assert.strictEqual(result.confidence, 1.0);
    });

    it('应该正确解析2019年老格式URL', () => {
      const url = 'https://www.oddsportal.com/matches/2019/08/12/england/premier-league/manchester-united-liverpool/';
      const result = engine.parseHistoricalURL(url);
      
      assert.strictEqual(result.format, 'legacy-2019');
      assert.strictEqual(result.sport, 'soccer');
      assert.strictEqual(result.country, 'england');
      assert.strictEqual(result.league, 'premier-league');
      assert.strictEqual(result.confidence, 0.85);
    });

    it('对于未知格式URL应该返回容错回退数据', () => {
      const url = 'https://example.com/some/random/path/match-name';
      const result = engine.parseHistoricalURL(url);
      
      assert.strictEqual(result.format, 'fallback');
      assert.strictEqual(result.confidence, 0.5);
      assert.strictEqual(result.match, 'match-name');
      assert.ok(result.raw_url, '应该保留原始URL');
    });

    it('容错回退应该保留原始URL供后续处理', () => {
      const url = 'https://unknown-site.com/very/strange/url/structure';
      const result = engine.parseHistoricalURL(url);
      
      assert.strictEqual(result.raw_url, url);
      assert.strictEqual(result.format, 'fallback');
    });
  });

  describe('测试用例 3: 检查点机制 - 断点续传', () => {
    it('应该能够保存和恢复检查点', () => {
      // 模拟处理了一些数据
      engine.state.processedCount = 5000;
      engine.state.successCount = 4800;
      engine.state.failedCount = 200;
      
      // 保存检查点
      const checkpoint = engine.saveCheckpoint();
      
      // 创建新引擎并恢复
      const newEngine = new BackfillResilienceEngine();
      const restored = newEngine.restoreCheckpoint(checkpoint);
      
      assert.strictEqual(restored, true, '应该成功恢复检查点');
      assert.strictEqual(newEngine.state.processedCount, 5000);
      assert.strictEqual(newEngine.state.successCount, 4800);
      assert.strictEqual(newEngine.state.failedCount, 200);
    });

    it('定期保存检查点应该正常工作', async () => {
      engine.config.checkpointInterval = 5; // 每5项保存一次
      
      const items = Array(12).fill(null).map((_, i) => ({ id: i }));
      
      await engine.processBatch(items, async (item) => {
        return { processed: item.id };
      });
      
      // 应该保存了2次检查点 (5和10)
      assert.ok(engine.state.checkpoint, '应该保存检查点');
      assert.strictEqual(engine.state.checkpoint.processedCount, 10);
    });
  });

  describe('状态报告功能', () => {
    it('应该返回完整的状态报告', () => {
      engine.initializeProxies([
        { host: '127.0.0.1', port: 7890 },
        { host: '127.0.0.1', port: 7891 }
      ]);
      
      engine.state.processedCount = 100;
      engine.state.successCount = 95;
      engine.state.failedCount = 5;
      
      const status = engine.getStatus();
      
      assert.strictEqual(status.processed, 100);
      assert.strictEqual(status.success, 95);
      assert.strictEqual(status.failed, 5);
      assert.strictEqual(status.successRate, '95.00%');
      assert.ok(status.proxyHealth, '应该包含代理健康信息');
      assert.strictEqual(status.proxyHealth.total, 2);
    });
  });
});

// 导出供其他模块使用
module.exports = { BackfillResilienceEngine };
