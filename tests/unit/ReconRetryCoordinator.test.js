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

test('ReconRetryCoordinator helper 应覆盖 Retry-After、waitBeforeRetry 与 inspectHttpFailure 分支', async () => {
  const debugEvents = [];
  const waitCalls = [];
  const navigator = {
    logger: {
      info() {},
      warn() {},
      error() {},
      debug(event, payload) {
        debugEvents.push({ event, payload });
      }
    },
    traceId: 'trace-retry-helpers',
    page: {
      isClosed() {
        return false;
      },
      async waitForTimeout(ms) {
        waitCalls.push(ms);
      }
    },
    context: {
      request: {
        async get(url, options) {
          assert.strictEqual(url, 'https://www.oddsportal.com/archive/');
          assert.strictEqual(options.failOnStatusCode, false);
          assert.strictEqual(options.timeout, 15000);
          return {
            async allHeaders() {
              return { 'Retry-After': '2' };
            },
            status() {
              return 503;
            }
          };
        }
      }
    },
    browserContext: {},
    http503RetryDelaysMs: [25],
    navigationTimeoutMs: 20000,
    postApiDiscoveryWaitMs: 0,
    proxyProvider: null,
    proxyRotator: null,
    async close() {},
    async launch() {},
    async _waitBeforeRetry() {}
  };

  const coordinator = new ReconRetryCoordinator(navigator);
  assert.strictEqual(coordinator.parseRetryAfterMs('2'), 2000);
  assert.strictEqual(coordinator.parseRetryAfterMs('not-a-date'), 0);
  assert.ok(coordinator.parseRetryAfterMs(new Date(Date.now() + 1200).toUTCString()) > 0);

  await coordinator.waitBeforeRetry('7');
  assert.deepStrictEqual(waitCalls, [7]);

  const inspected = await coordinator.inspectHttpFailure('https://www.oddsportal.com/archive/', 50000);
  assert.deepStrictEqual(inspected, {
    statusCode: 503,
    retryAfterRaw: '2',
    retryAfterMs: 2000
  });

  const originalSetTimeout = global.setTimeout;
  let fallbackDelay = null;
  navigator.page = {
    isClosed() {
      return true;
    }
  };
  global.setTimeout = (handler, delay) => {
    fallbackDelay = delay;
    handler();
    return 1;
  };
  try {
    await coordinator.waitBeforeRetry(11);
  } finally {
    global.setTimeout = originalSetTimeout;
  }
  assert.strictEqual(fallbackDelay, 11);

  navigator.context.request.get = async () => {
    throw new Error('inspect_failed');
  };
  assert.strictEqual(await coordinator.inspectHttpFailure('https://www.oddsportal.com/archive/', 100), null);
  assert.ok(debugEvents.some((entry) => entry.event === 'navigator_http_failure_inspect_failed'));
});

test('ReconRetryCoordinator 应覆盖失败提取、proxy failure 上报与 rotation 失败链路', async () => {
  const warnEvents = [];
  const debugEvents = [];
  const reportedRotatorFailures = [];
  const rotationPayloads = [];
  const launchedProxyPorts = [];
  const navigator = {
    logger: {
      info() {},
      error() {},
      warn(event, payload) {
        warnEvents.push({ event, payload });
      },
      debug(event, payload) {
        debugEvents.push({ event, payload });
      }
    },
    traceId: 'trace-retry-rotation',
    page: {
      async waitForTimeout() {}
    },
    context: {
      request: {
        async get() {
          return {
            async allHeaders() {
              return { 'retry-after': '1' };
            },
            status() {
              return 429;
            }
          };
        }
      }
    },
    browserContext: {
      proxy: { port: 7901 },
      sessionManager: {
        load() {
          return { sourceFormat: 'json' };
        },
        resolveProtocolIdentity() {
          return {
            lineageKey: 'proxy:7901',
            ja3ProfileId: 'proxy:7901:1:1',
            source: 'session_buffer_pool'
          };
        }
      },
      async navigate() {
        throw new Error('navigate_failed');
      }
    },
    proxy: { port: 7901 },
    proxyLease: null,
    proxyProvider: {
      async reportFailure() {
        throw new Error('provider_failed');
      }
    },
    proxyRotator: {
      reportFailure(port, errorType) {
        reportedRotatorFailures.push({ port, errorType });
      },
      rotate(payload) {
        rotationPayloads.push(payload);
        return { port: 7902 };
      }
    },
    lastLaunchOptions: {},
    http503RetryDelaysMs: [10],
    navigationTimeoutMs: 100,
    postApiDiscoveryWaitMs: 0,
    async close() {},
    async launch(options = {}) {
      launchedProxyPorts.push(options.proxy?.port || null);
    },
    async _waitBeforeRetry() {}
  };

  const coordinator = new ReconRetryCoordinator(navigator);
  const extracted = coordinator.extractFailureFromError(
    new Error('ERR_HTTP_RESPONSE_CODE_FAILURE 503'),
    { inspectUrl: 'https://www.oddsportal.com/retry/' }
  );
  assert.strictEqual(extracted.isResponseCodeFailure, true);
  assert.strictEqual(extracted.statusCode, 503);
  assert.strictEqual(extracted.inspectUrl, 'https://www.oddsportal.com/retry/');

  const resolved = await coordinator.resolveRetryableHttpFailureFromError(
    new Error('generic failure'),
    { inspectUrl: 'https://www.oddsportal.com/retry/', timeoutMs: 80 }
  );
  assert.deepStrictEqual(resolved, {
    retryable: true,
    statusCode: 429,
    retryAfterMs: 1000,
    retryAfterRaw: '1'
  });

  assert.strictEqual(
    await coordinator.reportCurrentProxyFailure({ statusCode: 429 }, { operationName: 'navigate', breakerKey: 'league:a' }),
    false
  );
  assert.ok(debugEvents.some((entry) => entry.event === 'navigator_proxy_failure_report_failed'));

  const nextProxy = await coordinator.rotateProxyForRetry(
    { statusCode: 429, retryAfterMs: 1000, retryAfterRaw: '1' },
    {
      operationName: 'navigate',
      breakerKey: 'league:a',
      inspectUrl: 'https://www.oddsportal.com/retry/',
      retryNavigateUrl: 'https://www.oddsportal.com/retry/',
      retryReadySelector: '#ready',
      timeoutMs: 33
    },
    0
  );

  assert.deepStrictEqual(nextProxy, { port: 7902 });
  assert.deepStrictEqual(reportedRotatorFailures, [{ port: 7901, errorType: '429' }]);
  assert.strictEqual(rotationPayloads[0].statusCode, 429);
  assert.strictEqual(rotationPayloads[0].currentPort, 7901);
  assert.deepStrictEqual(launchedProxyPorts, [7902]);
  assert.strictEqual(navigator.proxy.port, 7902);
  assert.ok(warnEvents.some((entry) => entry.event === 'navigator_proxy_rotated_for_429'));
  assert.ok(warnEvents.some((entry) => entry.event === 'navigator_proxy_rotation_failed'));

  const auditedError = new Error('503 service unavailable');
  assert.strictEqual(
    coordinator.auditBrowserNavigationFailure({ statusCode: 503 }, { operationName: 'navigate', breakerKey: 'league:b' }, auditedError),
    true
  );
  assert.strictEqual(
    coordinator.auditBrowserNavigationFailure({ statusCode: 503 }, { operationName: 'navigate', breakerKey: 'league:b' }, auditedError),
    false
  );

  const sealedError = new Error('503 service unavailable');
  Object.preventExtensions(sealedError);
  assert.strictEqual(
    coordinator.auditBrowserNavigationFailure({ statusCode: 503 }, { operationName: 'navigate', breakerKey: 'league:c' }, sealedError),
    true
  );
  assert.strictEqual(
    coordinator.auditBrowserNavigationFailure({ statusCode: 404 }, { operationName: 'fetch', breakerKey: 'league:d' }, new Error('404')),
    false
  );
});

test('ReconRetryCoordinator 应在重试耗尽时构造 retry error，并保留 retry-after 信息', async () => {
  const navigator = {
    logger: { info() {}, warn() {}, error() {}, debug() {} },
    traceId: 'trace-retry-exhausted',
    page: null,
    context: null,
    browserContext: {},
    proxyProvider: null,
    proxyRotator: null,
    http503RetryDelaysMs: [],
    navigationTimeoutMs: 100,
    postApiDiscoveryWaitMs: 0,
    async close() {},
    async launch() {},
    async _waitBeforeRetry() {
      throw new Error('should_not_wait');
    }
  };

  const coordinator = new ReconRetryCoordinator(navigator);
  const nonRetryable = await coordinator.executeWith503Retry(async () => ({ ok: true }), {
    operationName: 'noop'
  });
  assert.deepStrictEqual(nonRetryable, { ok: true });

  const resultFailure = coordinator.resolveRetryableHttpFailureFromResult({
    httpFailure: {
      statusCode: '502',
      retryAfterRaw: '3'
    }
  });
  assert.deepStrictEqual(resultFailure, {
    retryable: true,
    statusCode: 502,
    retryAfterMs: 3000,
    retryAfterRaw: '3'
  });

  await assert.rejects(
    () => coordinator.executeWith503Retry(async () => ({
      httpFailure: {
        statusCode: 503,
        retryAfterRaw: '7'
      }
    }), {
      operationName: 'fetch_archive_pages',
      breakerKey: 'league:epl'
    }),
    (error) => {
      assert.strictEqual(error.code, 'HTTP_503');
      assert.strictEqual(error.statusCode, 503);
      assert.strictEqual(error.retryAfterMs, 7000);
      assert.strictEqual(error.retryAfterRaw, '7');
      assert.match(error.message, /fetch_archive_pages failed with HTTP_503 after retries/);
      return true;
    }
  );
});
