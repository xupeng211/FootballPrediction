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

  test('100 次并发租约应在 22 个端口间近似均衡分布', async () => {
    const provider = new ProxyProvider({
      healthCheckIntervalMs: 0
    });

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

    assert.strictEqual(counts.size, 22);
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

  test('WSL2 默认主机应统一解析为 172.25.16.1', () => {
    const provider = getProxyProvider({
      healthCheckIntervalMs: 0
    });

    const stats = provider.getStats();
    const nodes = provider.getNodeStates();

    assert.strictEqual(stats.host, '172.25.16.1');
    assert.ok(nodes.every(node => node.host === '172.25.16.1'));
  });
});
