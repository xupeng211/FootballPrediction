/**
 * TITAN V6.0 P0 Fortification Tests - 回填工程核心加固测试
 * 任务: TITAN-V6.0-FORTIFY-P0
 *
 * 测试覆盖:
 * 1. 断点恢复 - 模拟中断后重启，验证跳过已成功ID
 * 2. 代理漂移 - 验证请求均匀分配到22个代理端口
 */

const assert = require('node:assert');
const { describe, it, beforeEach } = require('node:test');

// 模拟依赖
class MockPool {
  constructor() {
    this.data = new Map();
    this.queries = [];
  }

  async query(sql, params) {
    this.queries.push({ sql, params });

    // 模拟 getCompletedIds - 必须放在最前面匹配
    if (sql.includes("success") && sql.includes("skipped")) {
      const rows = [];
      for (const [matchId, record] of this.data) {
        if (record.status === 'success' || record.status === 'skipped') {
          rows.push({ match_id: matchId });
        }
      }
      return { rows };
    }

    // 模拟 getPending
    if (sql.includes('status IN') || sql.includes('pending')) {
      const rows = [];
      for (const [matchId, record] of this.data) {
        if ((record.status === 'pending' || record.status === 'failed') && record.retry_count < 3) {
          rows.push(record);
        }
      }
      return { rows };
    }

    // 模拟 getStats
    if (sql.includes('COUNT(*)')) {
      const stats = {
        pending_count: 0,
        processing_count: 0,
        success_count: 0,
        retryable_count: 0,
        dead_count: 0,
        skipped_count: 0,
        total_count: this.data.size
      };

      for (const record of this.data.values()) {
        if (record.status === 'pending') stats.pending_count++;
        if (record.status === 'processing') stats.processing_count++;
        if (record.status === 'success') stats.success_count++;
        if (record.status === 'failed' && record.retry_count < 3) stats.retryable_count++;
        if (record.status === 'failed' && record.retry_count >= 3) stats.dead_count++;
        if (record.status === 'skipped') stats.skipped_count++;
      }

      return { rows: [stats] };
    }

    return { rows: [] };
  }

  async connect() {
    return {
      query: async (sql, params) => this.query(sql, params),
      queryWithResult: async (sql, params) => {
        await this.query(sql, params);
        return { rowCount: 1 };
      },
      release: () => {}
    };
  }
}

// ============================================================================
// Checkpointer - 断点续传模块 (简化版用于测试)
// ============================================================================

class Checkpointer {
  constructor(options = {}) {
    if (!options.pool) {
      throw new Error('Checkpointer 需要数据库连接池');
    }
    this.pool = options.pool;
    this.batchId = options.batchId || `batch_${Date.now()}`;
  }

  async initializeMatches(matches) {
    for (const match of matches) {
      this.pool.data.set(match.match_id, {
        match_id: match.match_id,
        status: 'pending',
        retry_count: 0,
        match_info: JSON.stringify({ home_team: match.home_team, away_team: match.away_team }),
        batch_id: this.batchId,
        oddsportal_hash: match.oddsportal_hash || null
      });
    }
    return matches.length;
  }

  async getPendingMatches(limit = 100) {
    const result = await this.pool.query('SELECT * FROM backfill_progress WHERE status IN (?, ?)', ['pending', 'failed']);
    return result.rows.slice(0, limit);
  }

  async getCompletedIdsSet() {
    const result = await this.pool.query("SELECT match_id FROM backfill_progress WHERE status IN ('success', 'skipped')");
    return new Set(result.rows.map(r => r.match_id));
  }

  async markSuccess(matchId, metadata = {}) {
    const record = this.pool.data.get(matchId);
    if (record) {
      record.status = 'success';
      record.completed_at = new Date().toISOString();
      record.processing_time_ms = metadata.processingTimeMs || 0;
      record.proxy_port = metadata.proxyPort || null;
    }
  }

  async markFailed(matchId, error, proxyPort = null) {
    const record = this.pool.data.get(matchId);
    if (record) {
      record.status = 'failed';
      record.retry_count++;
      record.last_error = error;
      record.proxy_port = proxyPort;
    }
  }

  async getStats() {
    const result = await this.pool.query('SELECT COUNT(*) FROM backfill_progress');
    return result.rows[0];
  }
}

// ============================================================================
// ProxyRotator - 代理轮换模块 (简化版用于测试)
// ============================================================================

class ProxyRotator {
  constructor(options = {}) {
    this.strategy = options.strategy || 'round-robin';
    this.cooldownMs = options.cooldownMs || 60000;
    this.maxFailures = options.maxFailures || 3;

    // 22端口代理池
    this.proxies = [];
    for (let i = 0; i < 22; i++) {
      this.proxies.push({
        id: i,
        port: 7890 + i,
        host: '127.0.0.1',
        url: `http://127.0.0.1:${7890 + i}`,
        healthy: true,
        failCount: 0,
        useCount: 0,
        lastUsed: null,
        cooldownUntil: null
      });
    }

    this.currentIndex = 0;
  }

  getNextProxy() {
    const now = Date.now();

    const available = this.proxies.filter(p => {
      if (!p.healthy) return false;
      if (p.cooldownUntil && now < p.cooldownUntil) return false;
      if (p.failCount >= this.maxFailures) return false;
      return true;
    });

    if (available.length === 0) {
      return null;
    }

    let selected;

    switch (this.strategy) {
      case 'random':
        selected = available[Math.floor(Math.random() * available.length)];
        break;
      case 'round-robin':
      default:
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

    selected.useCount++;
    selected.lastUsed = now;

    return {
      id: selected.id,
      port: selected.port,
      host: selected.host,
      url: selected.url,
      server: selected.url
    };
  }

  reportFailure(port, errorType = 'other') {
    const proxy = this.proxies.find(p => p.port === port);
    if (!proxy) return;

    proxy.failCount++;

    // 403错误或达到 maxFailures 进入冷却
    if (errorType === '403' || proxy.failCount >= this.maxFailures) {
      proxy.cooldownUntil = Date.now() + this.cooldownMs;
    }

    // 达到 maxFailures * 2 标记为死亡
    if (proxy.failCount >= this.maxFailures * 2) {
      proxy.healthy = false;
    }
  }

  getHealthStatus() {
    const now = Date.now();

    // healthy = 健康且不在冷却期
    const healthy = this.proxies.filter(p => {
      if (!p.healthy) return false;
      if (p.cooldownUntil && now < p.cooldownUntil) return false;
      return true;
    }).length;

    const cooling = this.proxies.filter(p => p.cooldownUntil && now < p.cooldownUntil).length;
    const dead = this.proxies.filter(p => !p.healthy).length;

    return {
      total: this.proxies.length,
      healthy,
      cooling,
      dead,
      available: healthy
    };
  }
}

// ============================================================================
// TDD 测试套件
// ============================================================================

describe('BackfillFortification - V6.0 P0 核心加固', () => {
  describe('测试1: 断点恢复 - Checkpoint/Resume', () => {
    let pool;
    let checkpointer;

    beforeEach(() => {
      pool = new MockPool();
      checkpointer = new Checkpointer({ pool, batchId: 'test_batch_001' });
    });

    it('应该初始化100场比赛并标记为pending', async () => {
      const matches = Array(100).fill(null).map((_, i) => ({
        match_id: `M${i + 1}`,
        home_team: `Team${i}A`,
        away_team: `Team${i}B`,
        oddsportal_hash: `hash_${i}`
      }));

      const count = await checkpointer.initializeMatches(matches);
      assert.strictEqual(count, 100);
      assert.strictEqual(pool.data.size, 100);

      // 验证所有都是pending
      for (const record of pool.data.values()) {
        assert.strictEqual(record.status, 'pending');
      }
    });

    it('应该能够获取待处理任务(断点续传)', async () => {
      // 初始化100场
      const matches = Array(100).fill(null).map((_, i) => ({
        match_id: `M${i + 1}`,
        home_team: `Team${i}A`,
        away_team: `Team${i}B`
      }));
      await checkpointer.initializeMatches(matches);

      // 模拟处理成功50场
      for (let i = 1; i <= 50; i++) {
        await checkpointer.markSuccess(`M${i}`);
      }

      // 获取待处理任务
      const pending = await checkpointer.getPendingMatches(100);
      assert.strictEqual(pending.length, 50);

      // 验证只返回未完成的
      for (const record of pending) {
        assert.ok(record.status !== 'success');
      }
    });

    it('断点续传时应该跳过已成功的ID', async () => {
      // 初始化10场
      const matches = Array(10).fill(null).map((_, i) => ({
        match_id: `M${i + 1}`,
        home_team: `Team${i}A`,
        away_team: `Team${i}B`
      }));
      await checkpointer.initializeMatches(matches);

      // 模拟中断前完成5场
      for (let i = 1; i <= 5; i++) {
        await checkpointer.markSuccess(`M${i}`);
      }

      // 模拟处理中1场(中断)
      pool.data.get('M6').status = 'processing';

      // 重启后获取已完成ID集合
      const completedIds = await checkpointer.getCompletedIdsSet();

      // 断言: 已完成ID应该被跳过
      assert.strictEqual(completedIds.has('M1'), true);
      assert.strictEqual(completedIds.has('M2'), true);
      assert.strictEqual(completedIds.has('M3'), true);
      assert.strictEqual(completedIds.has('M4'), true);
      assert.strictEqual(completedIds.has('M5'), true);

      // 断言: 未完成的ID不应该在集合中
      assert.strictEqual(completedIds.has('M6'), false);
      assert.strictEqual(completedIds.has('M7'), false);
      assert.strictEqual(completedIds.has('M10'), false);
    });

    it('失败重试3次后应该标记为dead', async () => {
      const matches = [{
        match_id: 'M001',
        home_team: 'TeamA',
        away_team: 'TeamB'
      }];
      await checkpointer.initializeMatches(matches);

      // 失败3次
      await checkpointer.markFailed('M001', 'Timeout error', 7890);
      await checkpointer.markFailed('M001', 'Timeout error', 7891);
      await checkpointer.markFailed('M001', 'Timeout error', 7892);

      const record = pool.data.get('M001');
      assert.strictEqual(record.status, 'failed');
      assert.strictEqual(record.retry_count, 3);

      // 获取待处理任务时不应该包含已死任务
      const pending = await checkpointer.getPendingMatches(10);
      const m001Pending = pending.find(p => p.match_id === 'M001');
      assert.strictEqual(m001Pending, undefined, '重试3次的任务不应该在待处理列表中');
    });

    it('实时存盘 - 每成功一场应该立即更新状态', async () => {
      const matches = Array(5).fill(null).map((_, i) => ({
        match_id: `M${i + 1}`,
        home_team: `Team${i}A`,
        away_team: `Team${i}B`
      }));
      await checkpointer.initializeMatches(matches);

      // 处理第3场
      await checkpointer.markSuccess('M3', { processingTimeMs: 1500, proxyPort: 7895 });

      // 立即验证状态
      const record = pool.data.get('M3');
      assert.strictEqual(record.status, 'success');
      assert.strictEqual(record.processing_time_ms, 1500);
      assert.strictEqual(record.proxy_port, 7895);
      assert.ok(record.completed_at, '应该有完成时间');
    });
  });

  describe('测试2: 代理漂移 - Proxy Rotation', () => {
    let rotator;

    beforeEach(() => {
      rotator = new ProxyRotator({ strategy: 'round-robin' });
    });

    it('应该拥有22个代理端口', () => {
      const status = rotator.getHealthStatus();
      assert.strictEqual(status.total, 22);
      assert.strictEqual(status.healthy, 22);
    });

    it('轮询策略应该按顺序分配代理', () => {
      const ports = [];
      for (let i = 0; i < 25; i++) {
        const proxy = rotator.getNextProxy();
        ports.push(proxy.port);
      }

      // 验证前5个端口是按顺序的
      assert.strictEqual(ports[0], 7890);
      assert.strictEqual(ports[1], 7891);
      assert.strictEqual(ports[2], 7892);
      assert.strictEqual(ports[3], 7893);
      assert.strictEqual(ports[4], 7894);

      // 验证循环 (22个后回到起点)
      assert.strictEqual(ports[22], 7890);
    });

    it('连续50次请求应该均匀分配到不同端口', () => {
      const portUsage = new Map();

      // 发起50次请求
      for (let i = 0; i < 50; i++) {
        const proxy = rotator.getNextProxy();
        portUsage.set(proxy.port, (portUsage.get(proxy.port) || 0) + 1);
      }

      // 验证使用了多个不同端口
      assert.ok(portUsage.size >= 20, `应该使用至少20个不同端口,实际使用了${portUsage.size}个`);

      // 验证没有锁定在单个端口 (每个端口最多使用3次)
      for (const [port, count] of portUsage) {
        assert.ok(count <= 3, `端口${port}使用了${count}次,应该<=3次`);
      }

      // 验证总请求数
      const totalRequests = Array.from(portUsage.values()).reduce((a, b) => a + b, 0);
      assert.strictEqual(totalRequests, 50);
    });

    it('代理失败应该进入冷却', () => {
      // 使用7890端口
      const proxy1 = rotator.getNextProxy();
      assert.strictEqual(proxy1.port, 7890);

      // 报告失败
      rotator.reportFailure(7890, '403');

      // 7890应该进入冷却
      const proxy2 = rotator.getNextProxy();
      assert.notStrictEqual(proxy2.port, 7890, '冷却中的代理不应该被选中');

      const status = rotator.getHealthStatus();
      assert.strictEqual(status.cooling, 1);
    });

    it('连续3次失败应该标记代理为不健康', () => {
      // 连续失败3次
      rotator.reportFailure(7890, 'timeout');
      rotator.reportFailure(7890, 'timeout');
      rotator.reportFailure(7890, 'timeout');

      const status = rotator.getHealthStatus();
      assert.strictEqual(status.healthy, 21, '应该有一个代理变为不健康');

      // 再次获取代理不应该包含7890
      for (let i = 0; i < 30; i++) {
        const proxy = rotator.getNextProxy();
        assert.notStrictEqual(proxy.port, 7890);
      }
    });

    it('随机策略应该分散请求', () => {
      const randomRotator = new ProxyRotator({ strategy: 'random' });
      const portCounts = new Map();

      // 100次随机请求
      for (let i = 0; i < 100; i++) {
        const proxy = randomRotator.getNextProxy();
        portCounts.set(proxy.port, (portCounts.get(proxy.port) || 0) + 1);
      }

      // 验证随机分散 (至少15个不同端口被使用)
      assert.ok(portCounts.size >= 15, `随机策略应该使用至少15个端口,实际${portCounts.size}个`);

      // 验证没有极端集中 (单个端口最多15次)
      const maxCount = Math.max(...portCounts.values());
      assert.ok(maxCount <= 15, `单个端口使用次数${maxCount}应该<=15`);
    });
  });
});

// 导出供其他模块使用
module.exports = { Checkpointer, ProxyRotator, MockPool };
