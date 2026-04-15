'use strict';

const { afterEach, describe, test } = require('node:test');
const assert = require('node:assert/strict');

const {
  ProxyProvider,
  getProxyProvider,
  resetProxyProvider
} = require('../../src/infrastructure/network/ProxyProvider');

describe('src/infrastructure/network/ProxyProvider', () => {
  afterEach(() => {
    resetProxyProvider();
    delete process.env.PROXY_SERVER;
    delete process.env.PROXY_HOST;
    delete process.env.WSL2_PROXY_HOST;
  });

  test('100 次并发租约应在当前可用端口间近似均衡分布', async () => {
    const provider = new ProxyProvider({
      healthCheckIntervalMs: 0
    });
    const totalPorts = provider.getNodeStates().length;

    const leases = await Promise.all(
      Array.from({ length: 100 }, (_, index) => provider.acquire({
        consumer: 'l2-harvest',
        sessionKey: `worker-${index}`,
        sticky: false
      }))
    );

    const counts = new Map();
    leases.forEach((lease) => {
      counts.set(lease.proxy.port, (counts.get(lease.proxy.port) || 0) + 1);
    });

    const allocations = Array.from(counts.values());
    const min = Math.min(...allocations);
    const max = Math.max(...allocations);

    assert.strictEqual(counts.size, totalPorts);
    assert.ok(max - min <= 1);

    await Promise.all(leases.map((lease) => provider.release(lease.id)));
    assert.strictEqual(provider.getStats().activeLeases, 0);
  });

  test('连续 503 应在观察窗后进入 90 秒冷却并触发告警', async () => {
    let now = 1_000;
    const alerts = [];
    const provider = new ProxyProvider({
      now: () => now,
      healthCheckIntervalMs: 0,
      failureCooldownMs: 60000,
      http503CooldownMs: 90000,
      failureThreshold: 6,
      http503ObservationThreshold: 3
    });

    provider.on('alert', payload => {
      alerts.push(payload);
    });

    const lease = await provider.acquire({
      consumer: 'recon',
      sessionKey: 'worker-a',
      sticky: false
    });

    await provider.reportFailure(lease.id, { statusCode: 503, reason: 'HTTP 503' });
    await provider.reportFailure(lease.id, { statusCode: 503, reason: 'HTTP 503' });

    let node = provider.getNodeStates().find(item => item.port === lease.proxy.port);
    assert.strictEqual(node.cooling, false);
    assert.ok(alerts.some(item => item.type === 'proxy_under_observation' && item.port === lease.proxy.port));

    await provider.reportFailure(lease.id, { statusCode: 503, reason: 'HTTP 503' });
    node = provider.getNodeStates().find(item => item.port === lease.proxy.port);
    assert.strictEqual(node.cooling, true);
    assert.ok(alerts.some(item => item.type === 'proxy_cooled_down' && item.port === lease.proxy.port));

    now += 89_999;
    node = provider.getNodeStates().find(item => item.port === lease.proxy.port);
    assert.strictEqual(node.cooling, true);

    now += 2;
    node = provider.getNodeStates().find(item => item.port === lease.proxy.port);
    assert.strictEqual(node.cooling, false);
  });

  test('403 应立即触发 30 分钟关键冷却并跌破健康分租用阈值', async () => {
    let now = 10_000;
    const provider = new ProxyProvider({
      now: () => now,
      healthCheckIntervalMs: 0,
      criticalErrorCooldownMs: 1_800_000,
      minHealthScore: 60
    });
    const totalPorts = provider.getNodeStates().length;

    const lease = await provider.acquire({
      consumer: 'recon',
      sessionKey: 'critical-403',
      sticky: false
    });

    await provider.reportFailure(lease.id, { statusCode: 403, reason: 'Forbidden' });

    let node = provider.getNodeStates().find(item => item.port === lease.proxy.port);
    assert.strictEqual(node.cooling, true);
    assert.ok(node.healthScore < 60);
    assert.strictEqual(provider.getStats().available, totalPorts - 1);

    now += 1_799_999;
    node = provider.getNodeStates().find(item => item.port === lease.proxy.port);
    assert.strictEqual(node.cooling, true);

    now += 2;
    node = provider.getNodeStates().find(item => item.port === lease.proxy.port);
    assert.strictEqual(node.cooling, false);
  });

  test('健康分低于 60 的端口不得再次被租用', async () => {
    const provider = new ProxyProvider({
      healthCheckIntervalMs: 0,
      minHealthScore: 60,
      criticalErrorCooldownMs: 1_800_000
    });

    const lease = await provider.acquire({
      consumer: 'recon',
      sessionKey: 'health-gate',
      sticky: false
    });
    const blockedPort = lease.proxy.port;

    await provider.reportFailure(lease.id, { statusCode: 403, reason: 'Forbidden' });
    await provider.release(lease.id);

    const nextLease = await provider.acquire({
      consumer: 'recon',
      sessionKey: 'health-gate-next',
      sticky: false
    });

    assert.notStrictEqual(nextLease.proxy.port, blockedPort);
    assert.ok(provider.getNodeStates().find(item => item.port === blockedPort).healthScore < 60);
  });

  test('默认主机应统一解析为 host.docker.internal', () => {
    const provider = getProxyProvider({
      healthCheckIntervalMs: 0
    });

    const stats = provider.getStats();
    const nodes = provider.getNodeStates();

    assert.strictEqual(stats.host, 'host.docker.internal');
    assert.ok(nodes.every(node => node.host === 'host.docker.internal'));
  });

  test('ERR_EMPTY_RESPONSE 应触发软退避而不是判定代理物理死亡', async () => {
    let now = 5_000;
    const alerts = [];
    const provider = new ProxyProvider({
      now: () => now,
      healthCheckIntervalMs: 0,
      minHealthScore: 60,
      upstreamBlockBaseCooldownMs: 5_000,
      upstreamBlockMaxCooldownMs: 20_000
    });
    const totalPorts = provider.getNodeStates().length;

    provider.on('alert', payload => {
      alerts.push(payload);
    });

    const lease = await provider.acquire({
      consumer: 'discovery',
      sessionKey: 'soft-upstream',
      sticky: false
    });

    await provider.reportFailure(lease.id, {
      reason: 'page.goto: net::ERR_EMPTY_RESPONSE',
      failureClass: 'upstream_block'
    });

    let node = provider.getNodeStates().find(item => item.port === lease.proxy.port);
    assert.strictEqual(node.cooling, true);
    assert.ok(node.healthScore >= 96);
    assert.ok(alerts.some(item => item.type === 'proxy_soft_backoff' && item.port === lease.proxy.port));

    now += 5_001;
    node = provider.getNodeStates().find(item => item.port === lease.proxy.port);
    assert.strictEqual(node.cooling, false);
    assert.strictEqual(provider.getStats().available, totalPorts);
  });

  test('软故障连续出现时不得将节点健康分打穿到不可租用', async () => {
    let now = 8_000;
    const provider = new ProxyProvider({
      now: () => now,
      healthCheckIntervalMs: 0,
      minHealthScore: 60,
      transientContextCooldownMs: 1_000,
      upstreamBlockBaseCooldownMs: 1_000,
      upstreamBlockMaxCooldownMs: 3_000
    });
    const totalPorts = provider.getNodeStates().length;

    const lease = await provider.acquire({
      consumer: 'discovery',
      sessionKey: 'soft-floor',
      sticky: false
    });

    for (let index = 0; index < 8; index++) {
      await provider.reportFailure(lease.id, {
        reason: 'page.evaluate: Execution context was destroyed',
        failureClass: 'browser_context_transient'
      });
      now += 1_100;
    }

    let node = provider.getNodeStates().find(item => item.port === lease.proxy.port);
    assert.ok(node.healthScore >= 60);

    now += 3_100;
    node = provider.getNodeStates().find(item => item.port === lease.proxy.port);
    assert.strictEqual(node.cooling, false);
    assert.strictEqual(provider.getStats().available, totalPorts);
  });

  test('初始化时应先完成代理网关 TCP 预检', async () => {
    let tcpProbeCalls = 0;
    const provider = new ProxyProvider({
      host: 'host.docker.internal',
      ports: [7891, 7892],
      defaultPort: 7891,
      healthCheckIntervalMs: 0,
      probes: {
        tcp: async (node) => {
          tcpProbeCalls += 1;
          assert.strictEqual(node.host, 'host.docker.internal');
          assert.strictEqual(node.port, 7891);
          return { ok: true, latencyMs: 12 };
        },
        http: async () => ({ ok: true, statusCode: 200, latencyMs: 12 })
      }
    });

    const result = await provider.initialize();
    assert.strictEqual(result.ok, true);
    assert.strictEqual(result.host, 'host.docker.internal');
    assert.strictEqual(result.port, 7891);
    assert.strictEqual(tcpProbeCalls, 1);

    await provider.initialize();
    assert.strictEqual(tcpProbeCalls, 1);
  });

  test('代理网关 TCP 预检失败时应抛出清晰错误', async () => {
    const provider = new ProxyProvider({
      host: 'host.docker.internal',
      ports: [7891],
      defaultPort: 7891,
      healthCheckIntervalMs: 0,
      probes: {
        tcp: async () => ({ ok: false, error: 'connect ECONNREFUSED' }),
        http: async () => ({ ok: true, statusCode: 200, latencyMs: 8 })
      }
    });

    await assert.rejects(
      provider.initialize(),
      /代理网关无法连接，请检查 host\.docker\.internal 是否可用/
    );
  });
});
