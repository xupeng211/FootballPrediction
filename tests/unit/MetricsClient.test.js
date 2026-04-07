'use strict';

const { afterEach, describe, test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const http = require('node:http');

const MODULE_PATH = path.resolve(__dirname, '../../src/infrastructure/monitoring/MetricsClient.js');
const ENV_KEYS = ['API_HOST', 'API_PORT', 'ENABLE_METRICS'];

function withEnv(overrides = {}) {
  const snapshot = new Map();
  for (const key of ENV_KEYS) {
    snapshot.set(key, process.env[key]);
  }

  for (const key of ENV_KEYS) {
    if (Object.prototype.hasOwnProperty.call(overrides, key)) {
      process.env[key] = overrides[key];
    } else {
      delete process.env[key];
    }
  }

  return () => {
    for (const key of ENV_KEYS) {
      const value = snapshot.get(key);
      if (value === undefined) {
        delete process.env[key];
      } else {
        process.env[key] = value;
      }
    }
  };
}

function loadMetricsModule(env = {}) {
  const restoreEnv = withEnv(env);
  delete require.cache[MODULE_PATH];
  return {
    ...require(MODULE_PATH),
    restoreEnv,
  };
}

describe('src/infrastructure/monitoring/MetricsClient', () => {
  const originalDateNow = Date.now;
  const originalHttpRequest = http.request;

  afterEach(() => {
    Date.now = originalDateNow;
    http.request = originalHttpRequest;
    delete require.cache[MODULE_PATH];
  });

  test('应记录收割、代理、L1 与 backlog 指标，并输出 Prometheus/JSON 统计', () => {
    Date.now = () => 5000;
    const loaded = loadMetricsModule({
      ENABLE_METRICS: 'false',
    });
    try {
      const client = new loaded.MetricsClient({
        apiHost: 'metrics.internal',
        apiPort: 9100,
      });

      client.reset();
      loaded.metricsStore.startTime = 1000;

      client.recordHarvestStart('match-1', 1);
      client.recordHarvestStart('match-2', 2);
      client.recordHarvestSuccess('match-1', 1, 120, 2048, 7890);
      client.recordHarvestFailure('match-2', 2, 'TIMEOUT', 'slow upstream', 7890);
      client.recordProxyHealth(7890, 88);
      client.recordPendingMatches(20, 5);
      client.updateProcessedMatches(3);
      client.recordL1Discovery(4, 'EPL');
      client.recordL1Discovery(2);
      client.recordL1FetchDuration(80);
      client.recordL1FetchDuration(120);
      client.recordL1BatchWrite(40, 20, 7, 2);
      client.recordL1Complete({ fixtures: 40, inserted: 30, updated: 10 });

      assert.strictEqual(client.apiHost, 'metrics.internal');
      assert.strictEqual(client.apiPort, 9100);
      assert.strictEqual(client.enabled, false);

      const prometheus = client.getPrometheusMetrics();
      assert.ok(prometheus.includes('titan_harvest_total 2'));
      assert.ok(prometheus.includes('titan_harvest_success_total 1'));
      assert.ok(prometheus.includes('titan_harvest_failed_total 1'));
      assert.ok(prometheus.includes('titan_l2_backlog 12'));
      assert.ok(prometheus.includes('titan_l1_discovered_total 40'));
      assert.ok(prometheus.includes('titan_proxy_by_port{port="7890",status="health"} 88'));
      assert.ok(prometheus.includes('titan_harvest_errors_by_type{type="TIMEOUT"} 1'));
      assert.ok(prometheus.includes('titan_harvest_last_seconds_ago 0.00'));

      assert.deepStrictEqual(client.getStats(), {
        harvest: {
          total: 2,
          success: 1,
          failed: 1,
          successRate: '50.00%',
          avgDurationMs: '120.00',
        },
        backlog: {
          pending: 20,
          processed: 8,
          backlog: 12,
          lastUpdate: '0s ago',
        },
        proxy: {
          requests: 2,
          success: 1,
          failed: 1,
          byPort: {
            7890: {
              success: 1,
              failed: 1,
              healthScore: 88,
            },
          },
        },
        errors: {
          TIMEOUT: 1,
        },
        uptime: '4s',
      });

      client.reset();
      assert.strictEqual(loaded.metricsStore.harvestTotal, 0);
      assert.deepStrictEqual(loaded.metricsStore.proxyByPort, {});
      assert.deepStrictEqual(loaded.metricsStore.errorsByType, {});
      assert.strictEqual(loaded.metricsStore.l1LastRunTime, null);
    } finally {
      loaded.restoreEnv();
    }
  });

  test('应裁剪近期耗时窗口，并复用 getMetricsClient 单例', () => {
    const loaded = loadMetricsModule({
      ENABLE_METRICS: 'false',
      API_HOST: 'env-host',
      API_PORT: '9200',
    });
    try {
      const singleton = loaded.getMetricsClient();
      const sameSingleton = loaded.getMetricsClient({ apiHost: 'ignored', apiPort: 9999 });
      const directClient = new loaded.MetricsClient();

      singleton.reset();
      assert.strictEqual(singleton, sameSingleton);
      assert.strictEqual(singleton.apiHost, 'env-host');
      assert.strictEqual(singleton.apiPort, 9200);
      assert.strictEqual(directClient.apiHost, 'env-host');
      assert.strictEqual(directClient.apiPort, 9200);

      for (let index = 0; index <= 100; index += 1) {
        singleton.recordHarvestSuccess(`match-${index}`, 1, index, 1000, 8000);
        singleton.recordL1FetchDuration(index);
      }
      for (let index = 0; index <= 50; index += 1) {
        singleton.recordL1BatchWrite(index, 10, 1, 1);
      }

      assert.strictEqual(loaded.metricsStore.harvestDurationMs.length, 100);
      assert.strictEqual(loaded.metricsStore.harvestDurationMs[0], 1);
      assert.strictEqual(loaded.metricsStore.harvestDurationMs.at(-1), 100);
      assert.strictEqual(loaded.metricsStore.l1FetchDurationMs.length, 100);
      assert.strictEqual(loaded.metricsStore.l1FetchDurationMs[0], 1);
      assert.strictEqual(loaded.metricsStore.l1FetchDurationMs.at(-1), 100);
      assert.strictEqual(loaded.metricsStore.l1BatchWriteDurationMs.length, 50);
      assert.deepStrictEqual(loaded.metricsStore.l1BatchWriteDurationMs[0], { duration: 1, size: 10 });
      assert.deepStrictEqual(loaded.metricsStore.l1BatchWriteDurationMs.at(-1), { duration: 50, size: 10 });

      singleton.reset();
    } finally {
      loaded.restoreEnv();
    }
  });

  test('notifyPythonAPI 应在禁用时短路，并在启用时覆盖 error/timeout 回调', () => {
    const writes = [];
    const requests = [];
    let destroyed = false;
    let ended = false;

    http.request = (options, onResponse) => {
      requests.push(options);
      const handlers = {};
      const req = {
        on(event, handler) {
          handlers[event] = handler;
          return req;
        },
        write(payload) {
          writes.push(payload);
        },
        end() {
          ended = true;
          if (typeof onResponse === 'function') {
            onResponse({ statusCode: 202 });
          }
          handlers.timeout();
          handlers.error(new Error('ignored'));
        },
        destroy() {
          destroyed = true;
        },
      };
      return req;
    };

    const disabledModule = loadMetricsModule({
      ENABLE_METRICS: 'false',
    });
    try {
      const disabledClient = new disabledModule.MetricsClient({ apiHost: 'disabled-host', apiPort: 9300 });
      disabledClient._notifyPythonAPI('success', { matchId: 'disabled' });
      assert.strictEqual(requests.length, 0);
    } finally {
      disabledModule.restoreEnv();
    }

    const enabledModule = loadMetricsModule({
      ENABLE_METRICS: 'true',
    });
    try {
      const enabledClient = new enabledModule.MetricsClient({ apiHost: 'enabled-host', apiPort: 9301 });
      enabledClient._notifyPythonAPI('failure', {
        matchId: 'm-1',
        errorType: 'TIMEOUT',
        errorMessage: 'slow',
      });

      assert.strictEqual(requests.length, 1);
      assert.deepStrictEqual(requests[0], {
        hostname: 'enabled-host',
        port: 9301,
        path: '/api/v1/monitoring/record',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(writes[0]),
        },
        timeout: 1000,
      });
      assert.deepStrictEqual(JSON.parse(writes[0]), {
        event: 'failure',
        matchId: 'm-1',
        errorType: 'TIMEOUT',
        errorMessage: 'slow',
      });
      assert.strictEqual(ended, true);
      assert.strictEqual(destroyed, true);
    } finally {
      enabledModule.restoreEnv();
    }
  });
});
