'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const { ReconRetryCoordinator } = require('../../src/infrastructure/recon/services/ReconRetryCoordinator');

test('ReconRetryCoordinator 应对 429 执行退避并上报 provider，但不触发代理轮换', async () => {
  const providerCalls = [];
  let rotateCalls = 0;
  let waitCalls = 0;
  let attempt = 0;

  const navigator = {
    logger: { info() {}, warn() {}, error() {}, debug() {} },
    traceId: 'trace-retry-429',
    page: null,
    context: null,
    proxy: { port: 7911 },
    proxyLease: {
      id: 'lease-429',
      proxy: { port: 7911 }
    },
    proxyProvider: {
      async reportFailure(target, metadata) {
        providerCalls.push({ target, metadata });
      }
    },
    proxyRotator: {
      reportFailure() {
        rotateCalls += 1;
      },
      rotate() {
        rotateCalls += 1;
        return { port: 7912 };
      }
    },
    browserContext: {
      async navigate() {}
    },
    lastLaunchOptions: {},
    http503RetryDelaysMs: [25],
    navigationTimeoutMs: 100,
    postApiDiscoveryWaitMs: 0,
    async close() {},
    async launch() {},
    async _waitBeforeRetry() {
      waitCalls += 1;
    }
  };

  const coordinator = new ReconRetryCoordinator(navigator);
  const result = await coordinator.executeWith503Retry(async () => {
    attempt += 1;
    if (attempt === 1) {
      return {
        httpFailure: {
          statusCode: 429,
          retryAfterMs: 10,
          retryAfterRaw: '10'
        }
      };
    }
    return { ok: true };
  }, {
    operationName: 'fetch_archive_pages',
    breakerKey: 'league:epl'
  });

  assert.deepEqual(result, { ok: true });
  assert.strictEqual(waitCalls, 1);
  assert.strictEqual(rotateCalls, 0);
  assert.strictEqual(providerCalls.length, 1);
  assert.strictEqual(providerCalls[0].target, 'lease-429');
  assert.strictEqual(providerCalls[0].metadata.statusCode, 429);
});
