'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const { ReconRetryCoordinator } = require('../../src/infrastructure/recon/services/ReconRetryCoordinator');

test('ReconRetryCoordinator 应对 429 执行退避、上报 provider，并立即触发代理轮换', async () => {
  const providerCalls = [];
  const reportedFailures = [];
  const launchedProxyPorts = [];
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
      reportFailure(port, errorType) {
        reportedFailures.push({ port, errorType });
      },
      rotate() {
        return { port: 7912 };
      }
    },
    browserContext: {
      proxy: { port: 7911 },
      async navigate() {}
    },
    lastLaunchOptions: {},
    http503RetryDelaysMs: [25],
    navigationTimeoutMs: 100,
    postApiDiscoveryWaitMs: 0,
    async close() {},
    async launch(options = {}) {
      launchedProxyPorts.push(options.proxy?.port || null);
    },
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
  assert.strictEqual(providerCalls.length, 1);
  assert.strictEqual(providerCalls[0].target, 'lease-429');
  assert.strictEqual(providerCalls[0].metadata.statusCode, 429);
  assert.deepStrictEqual(reportedFailures, [{ port: 7911, errorType: '429' }]);
  assert.deepStrictEqual(launchedProxyPorts, [7912]);
  assert.strictEqual(navigator.proxy.port, 7912);
});

test('ReconRetryCoordinator 在 503 重试前记录当前 Context 的 Cookie 持有状态', async () => {
  const warnEvents = [];
  let waitCalls = 0;
  let attempt = 0;

  const navigator = {
    logger: {
      info() {},
      error() {},
      debug() {},
      warn(event, payload) {
        warnEvents.push({ event, payload });
      }
    },
    traceId: 'trace-retry-503-cookie-state',
    page: null,
    context: {
      async cookies() {
        return [
          { name: 'sid', value: '1' },
          { name: 'cf_clearance', value: '2' }
        ];
      }
    },
    browserContext: {
      sessionManager: {
        runtimeSnapshot: {
          cookies: [
            { name: 'sid', value: '1' }
          ]
        }
      }
    },
    proxy: { port: 7901 },
    proxyLease: null,
    proxyProvider: null,
    proxyRotator: null,
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
          statusCode: 503,
          retryAfterMs: 10,
          retryAfterRaw: '10'
        }
      };
    }
    return { ok: true };
  }, {
    operationName: 'navigate',
    breakerKey: 'league:england/championship',
    inspectUrl: 'https://www.oddsportal.com/football/england/championship/results/'
  });

  assert.deepEqual(result, { ok: true });
  assert.strictEqual(waitCalls, 1);

  const cookieStateEvent = warnEvents.find((entry) => entry.event === 'navigator_http_503_cookie_state');
  assert.ok(cookieStateEvent);
  assert.strictEqual(cookieStateEvent.payload.proxyPort, 7901);
  assert.strictEqual(cookieStateEvent.payload.contextCookies, 2);
  assert.strictEqual(cookieStateEvent.payload.hasContextCookies, true);
  assert.strictEqual(cookieStateEvent.payload.runtimeSnapshotCookies, 1);
  assert.strictEqual(cookieStateEvent.payload.hasRuntimeSnapshotCookies, true);
});

test('ReconRetryCoordinator 在 page.goto TLS 断连时记录代理与 JA3 审计', async () => {
  const warnEvents = [];
  const navigator = {
    logger: {
      info() {},
      error() {},
      debug() {},
      warn(event, payload) {
        warnEvents.push({ event, payload });
      }
    },
    traceId: 'trace-retry-tls-audit',
    page: null,
    context: null,
    browserContext: {
      sessionManager: {
        load() {
          return { sourceFormat: 'session_buffer_golden' };
        },
        resolveProtocolIdentity({ proxyPort, ciphersCount, sigalgsCount }) {
          assert.strictEqual(proxyPort, 7902);
          assert.strictEqual(ciphersCount, 8);
          assert.strictEqual(sigalgsCount, 8);
          return {
            lineageKey: 'proxy:7902',
            ja3ProfileId: 'proxy:7902:6:7',
            cipherIdx: 6,
            sigalgIdx: 7,
            source: 'session_buffer_pool'
          };
        }
      }
    },
    proxy: { port: 7902 },
    proxyLease: {
      id: 'lease-7902',
      proxy: { port: 7902 }
    },
    proxyProvider: null,
    proxyRotator: null,
    http503RetryDelaysMs: [25],
    navigationTimeoutMs: 100,
    postApiDiscoveryWaitMs: 0,
    async close() {},
    async launch() {},
    async _waitBeforeRetry() {}
  };

  const coordinator = new ReconRetryCoordinator(navigator);

  await assert.rejects(async () => coordinator.executeWith503Retry(async () => {
    throw new Error(
      'page.goto: net::ERR_CONNECTION_CLOSED; Client network socket disconnected before secure TLS connection was established'
    );
  }, {
    operationName: 'navigate',
    breakerKey: 'league:laliga2',
    inspectUrl: 'https://www.oddsportal.com/football/spain/laliga2/results/'
  }), /ERR_CONNECTION_CLOSED/);

  const auditEvent = warnEvents.find((entry) => entry.event === 'navigator_http_503_profile_audit');
  assert.ok(auditEvent);
  assert.strictEqual(auditEvent.payload.proxyPort, 7902);
  assert.strictEqual(auditEvent.payload.ja3ProfileId, 'proxy:7902:6:7');
  assert.strictEqual(auditEvent.payload.lineageKey, 'proxy:7902');
  assert.strictEqual(auditEvent.payload.tlsDisconnect, true);
  assert.strictEqual(auditEvent.payload.sourceFormat, 'session_buffer_golden');
  assert.strictEqual(auditEvent.payload.operation, 'navigate');
});
