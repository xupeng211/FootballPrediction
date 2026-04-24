'use strict';

const { afterEach, describe, test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');

const MODULE_PATH = path.resolve(__dirname, '../../src/infrastructure/network/NetworkManager.js');
const FACTORY_ID = path.resolve(__dirname, '../../config/factory_config.js');
const SHIELD_ID = path.resolve(__dirname, '../../src/infrastructure/network/NetworkShield.js');
const SESSION_ID = path.resolve(__dirname, '../../src/infrastructure/network/SessionManager.js');
const PATH_RESOLVER_ID = path.resolve(__dirname, '../../src/infrastructure/utils/PathResolver.js');
const FINGERPRINT_ID = path.resolve(__dirname, '../../src/infrastructure/network/StealthFingerprint.js');
const { BrowserProvider } = require('../../src/infrastructure/services/BrowserProvider');
const { getProxyProvider, resetProxyProvider } = require('../../src/infrastructure/network/ProxyProvider');

function overrideModule(moduleId, exportsValue) {
  const previous = require.cache[moduleId];
  require.cache[moduleId] = {
    id: moduleId,
    filename: moduleId,
    loaded: true,
    exports: exportsValue,
  };

  return () => {
    if (previous) {
      require.cache[moduleId] = previous;
    } else {
      delete require.cache[moduleId];
    }
  };
}

function loadNetworkManagerModule(overrides = {}) {
  const state = {
    shieldConfigs: [],
    sessionConfigs: [],
    consoleLogs: [],
    consoleWarns: [],
    consoleErrors: [],
  };

  const originalConsoleLog = console.log;
  const originalConsoleWarn = console.warn;
  const originalConsoleError = console.error;

  console.log = (...args) => {
    state.consoleLogs.push(args.join(' '));
  };
  console.warn = (...args) => {
    state.consoleWarns.push(args.join(' '));
  };
  console.error = (...args) => {
    state.consoleErrors.push(args.join(' '));
  };

  const shield = overrides.shield || {
    getStatus: () => ({ active: 22, total: 22 }),
    getNextHealthyProxy: async sessionId => ({
      sessionId,
      port: 7891,
      url: 'http://172.25.16.1:7891',
    }),
    markSuccess() {},
    markFailed() {},
    shutdown() {},
  };

  const sessionManager = overrides.sessionManager || {
    async initialize() {},
    async getOrRefreshSession() {
      return {
        cookies: ['cookie'],
        expiresAt: Date.now() + 3600000,
      };
    },
    async loadSessionToContext() {
      return true;
    },
    getStats() {
      return {
        cachedSessions: 2,
        totalRefreshes: 5,
        successfulRefreshes: 4,
        failedRefreshes: 1,
        cacheHits: 3,
        cacheMisses: 1,
      };
    },
  };

  const restorers = [
    overrideModule(FACTORY_ID, overrides.factoryConfig || {
      PROXY_CONFIG: {
        serverTemplate: 'http://172.25.16.1:{port}',
        getPortByWorker(workerId) {
          return 7900 + workerId;
        },
        getServer(port) {
          return `http://172.25.16.1:${port}`;
        },
      },
    }),
    overrideModule(SHIELD_ID, {
      getNetworkShield(config) {
        state.shieldConfigs.push(config);
        if (overrides.getNetworkShieldError) {
          throw overrides.getNetworkShieldError;
        }
        return shield;
      },
    }),
    overrideModule(SESSION_ID, {
      getSessionManager(config) {
        state.sessionConfigs.push(config);
        return sessionManager;
      },
    }),
    overrideModule(PATH_RESOLVER_ID, {
      getPathResolver() {
        return {
          getSessionsPath() {
            return '/tmp/sessions';
          },
        };
      },
    }),
    overrideModule(FINGERPRINT_ID, {
      generateStealthHeaders: overrides.stealthGenerator || (() => ({
        userAgent: 'UA-DEFAULT',
        viewport: { width: 1280, height: 720 },
      })),
    }),
  ];

  delete require.cache[MODULE_PATH];

  let loaded;
  try {
    loaded = require(MODULE_PATH);
  } finally {
    for (const restore of restorers.reverse()) {
      restore();
    }
  }

  return {
    ...loaded,
    state,
    shield,
    sessionManager,
    restore() {
      console.log = originalConsoleLog;
      console.warn = originalConsoleWarn;
      console.error = originalConsoleError;
    },
  };
}

function createProxyProvider(options = {}) {
  const ports = options.ports || Array.from({ length: 22 }, (_, index) => 7890 + index);
  const host = options.host || '172.25.16.1';
  const state = {
    acquireCalls: [],
    releaseCalls: [],
    reportSuccessCalls: [],
    reportFailureCalls: [],
    reportPortSuccessCalls: [],
    reportPortFailureCalls: [],
  };
  const sequence = [...(options.portSequence || [])];
  const nodeStates = options.nodeStates || (() => ports.map((port) => ({
    port,
    host,
    server: `http://${host}:${port}`,
    probeHealthy: true,
    cooling: false,
    isolated: false,
    failureCount: 0,
  })));

  function buildAssignment(port) {
    return {
      host,
      port,
      url: `http://${host}:${port}`,
      server: `http://${host}:${port}`,
    };
  }

  function buildLease(port) {
    const proxy = buildAssignment(port);
    return {
      id: `LEASE-${port}-${state.acquireCalls.length}`,
      proxy,
    };
  }

  function resolvePort(request = {}) {
    if (options.acquireError) {
      throw options.acquireError;
    }
    if (Number.isFinite(Number(request.preferredPort))) {
      return Number(request.preferredPort);
    }
    if (sequence.length > 0) {
      return sequence.shift();
    }
    return options.defaultPort || ports[0];
  }

  const provider = {
    state,
    getPorts() {
      return [...ports];
    },
    getHost() {
      return host;
    },
    getStats() {
      return {
        host,
        total: ports.length,
        healthy: ports.length,
        cooling: 0,
        isolated: 0,
        available: ports.length,
        activeLeases: Math.max(0, state.acquireCalls.length - state.releaseCalls.length),
      };
    },
    getNodeStates() {
      return nodeStates();
    },
    buildAssignment,
    acquireSync(request = {}) {
      state.acquireCalls.push(request);
      return buildLease(resolvePort(request));
    },
    async acquire(request = {}) {
      return this.acquireSync(request);
    },
    acquireAssignmentSync(request = {}) {
      const lease = this.acquireSync(request);
      return {
        lease,
        assignment: {
          ...lease.proxy,
          sessionId: lease.id,
        },
      };
    },
    async acquireAssignment(request = {}) {
      return this.acquireAssignmentSync(request);
    },
    releaseSync(leaseId) {
      state.releaseCalls.push(leaseId);
      return true;
    },
    async release(leaseId) {
      return this.releaseSync(leaseId);
    },
    async reportSuccess(leaseId, metadata = {}) {
      state.reportSuccessCalls.push({ leaseId, metadata });
      return true;
    },
    async reportFailure(leaseId, metadata = {}) {
      state.reportFailureCalls.push({ leaseId, metadata });
      return true;
    },
    async reportPortSuccess(port, metadata = {}) {
      state.reportPortSuccessCalls.push({ port, metadata });
      return true;
    },
    async reportPortFailure(port, metadata = {}) {
      state.reportPortFailureCalls.push({ port, metadata });
      return true;
    },
  };

  return provider;
}

describe('src/infrastructure/network/NetworkManager', () => {
  const originalDateNow = Date.now;
  const originalRandom = Math.random;

  afterEach(() => {
    Date.now = originalDateNow;
    Math.random = originalRandom;
    delete require.cache[MODULE_PATH];
    resetProxyProvider();
  });

  test('WorkerIdentity 应计算成功率并在连续失败时触发重建', () => {
    Date.now = () => 1700000000000;
    const loaded = loadNetworkManagerModule();
    try {
      const fresh = new loaded.WorkerIdentity(1, { port: 7890 }, { viewport: { width: 1, height: 1 } });
      assert.strictEqual(fresh.getSuccessRate(), 1);
      assert.strictEqual(fresh.needsReidentity(), false);
      assert.ok(fresh.sessionId.startsWith('WORKER-1-1700000000000'));

      fresh.recordRequest(false);
      fresh.recordRequest(false);
      fresh.recordRequest(false);
      fresh.recordRequest(true);

      assert.strictEqual(fresh.requestCount, 4);
      assert.strictEqual(fresh.successCount, 1);
      assert.strictEqual(fresh.failureCount, 3);
      assert.strictEqual(fresh.getSuccessRate(), 0.25);
      assert.strictEqual(fresh.needsReidentity(), true);
    } finally {
      loaded.restore();
    }
  });

  test('initialize 应完成预清理、NetworkShield 与 SessionManager 初始化，并覆盖降级分支', async () => {
    let preFlightCalled = false;
    const loaded = loadNetworkManagerModule();
    try {
      const proxyProvider = createProxyProvider();
      const manager = new loaded.NetworkManager({ proxyProvider });

      await manager.initialize({
        async preFlightCleanup() {
          preFlightCalled = true;
        },
      });

      assert.strictEqual(preFlightCalled, true);
      assert.strictEqual(loaded.state.sessionConfigs.length, 1);
      assert.ok(manager.networkShield);
      assert.strictEqual(manager.sessionManager, loaded.sessionManager);
      assert.ok(loaded.state.consoleLogs.some(message => message.includes('NetworkShield 已就绪')));
      assert.ok(loaded.state.consoleLogs.some(message => message.includes('SessionManager 已就绪')));

      const degraded = loadNetworkManagerModule();
      try {
        const degradedManager = new degraded.NetworkManager({ proxyProvider });
        degradedManager._createNetworkShieldAdapter = () => {
          throw new Error('shield boot failed');
        };
        await degradedManager._initNetworkShield();

        assert.strictEqual(degradedManager.networkShield, null);
        assert.ok(degraded.state.consoleErrors.some(message => message.includes('NetworkShield 初始化失败')));
        assert.ok(degraded.state.consoleLogs.some(message => message.includes('降级模式')));
      } finally {
        degraded.restore();
      }
    } finally {
      loaded.restore();
    }
  });

  test('assignWorkerIdentity 应覆盖复用、Shield 回退、Session 警告与降级代理池分支', async () => {
    Date.now = () => 1700000001000;
    const stealthInputs = [];
    const loaded = loadNetworkManagerModule({
      stealthGenerator: (seed) => {
        stealthInputs.push(seed);
        return {
        userAgent: 'UA-CUSTOM',
        viewport: { width: 1440, height: 900 },
        };
      },
    });
    try {
      const proxyProvider = createProxyProvider({
        defaultPort: 7891
      });
      const manager = new loaded.NetworkManager({ proxyProvider });
      manager.sessionManager = loaded.sessionManager;

      const identity = await manager.assignWorkerIdentity(2);
      assert.strictEqual(identity.proxy.port, 7891);
      assert.strictEqual(identity.stealth.userAgent, 'UA-CUSTOM');
      assert.deepStrictEqual(stealthInputs[0], { workerId: 2, port: 7891, useFixed: true });
      assert.strictEqual(manager.getWorkerIdentity(2), identity);
      assert.ok(loaded.state.consoleLogs.some(message => message.includes('Worker 2 新身份绑定')));

      const reused = await manager.assignWorkerIdentity(2);
      assert.strictEqual(reused, identity);
      assert.ok(loaded.state.consoleLogs.some(message => message.includes('复用身份')));

      const fallbackLoaded = loadNetworkManagerModule({
        sessionManager: {
          async initialize() {},
          async getOrRefreshSession() {
            throw new Error('session refresh failed');
          },
          async loadSessionToContext() {
            return false;
          },
          getStats() {
            return {
              cachedSessions: 0,
              totalRefreshes: 0,
              successfulRefreshes: 0,
              failedRefreshes: 0,
              cacheHits: 0,
              cacheMisses: 0,
            };
          },
        },
      });
      try {
        const failingProvider = createProxyProvider({
          acquireError: new Error('all proxies down')
        });
        const fallbackManager = new fallbackLoaded.NetworkManager({ proxyProvider: failingProvider });
        fallbackManager.sessionManager = fallbackLoaded.sessionManager;

        const fallbackIdentity = await fallbackManager.assignWorkerIdentity(3);
        assert.strictEqual(fallbackIdentity.proxy.port, 7903);
        assert.ok(fallbackLoaded.state.consoleWarns.some(message => message.includes('ProxyProvider 获取代理失败')));
        assert.ok(fallbackLoaded.state.consoleWarns.some(message => message.includes('会话刷新失败')));

        const degradedManager = new fallbackLoaded.NetworkManager({
          proxyProvider: createProxyProvider({
            acquireError: new Error('all proxies down')
          })
        });
        degradedManager.networkShield = null;
        degradedManager.sessionManager = null;
        const degradedIdentity = await degradedManager.assignWorkerIdentity(4);
        assert.strictEqual(degradedIdentity.proxy.port, 7904);
      } finally {
        fallbackLoaded.restore();
      }
    } finally {
      loaded.restore();
    }
  });

  test('代理状态、轮询配置、避障重分配与统计接口应按预期工作', async () => {
    Date.now = () => 1700000002000;
    Math.random = () => 0;

    const loaded = loadNetworkManagerModule({
      sessionManager: {
        async initialize() {},
        async getOrRefreshSession() {
          return null;
        },
        async loadSessionToContext(context, port) {
          return { context, port, loaded: true };
        },
        getStats() {
          return {
            cachedSessions: 1,
            totalRefreshes: 2,
            successfulRefreshes: 1,
            failedRefreshes: 1,
            cacheHits: 5,
            cacheMisses: 2,
          };
        },
      },
    });
    try {
      const proxyProvider = createProxyProvider({
        defaultPort: 7895,
        portSequence: [7895, 7892]
      });
      const manager = new loaded.NetworkManager({ proxyProvider });
      manager.sessionManager = loaded.sessionManager;

      const identity = await manager.assignWorkerIdentity(5);
      await manager.markProxySuccess(5);
      assert.strictEqual(proxyProvider.state.reportSuccessCalls.length, 1);
      assert.strictEqual(proxyProvider.state.reportSuccessCalls[0].metadata.workerId, 5);

      identity.failureCount = 2;
      identity.requestCount = 2;
      identity.successCount = 0;
      await manager.markProxyFailed(5, 'timeout');
      assert.strictEqual(proxyProvider.state.reportFailureCalls.length, 1);
      assert.strictEqual(proxyProvider.state.reportFailureCalls[0].metadata.port, 7895);
      assert.strictEqual(manager.getWorkerIdentity(5), undefined);

      const indexedConfig = manager.getRotatedConfig(2);
      assert.strictEqual(indexedConfig.port, 7892);
      assert.ok(indexedConfig.sessionId.startsWith('session_7892_1700000002000_'));

      manager.failedPorts.add(7890);
      const randomConfig = manager.getRotatedConfig();
      assert.strictEqual(randomConfig.port, 7891);

      const swarm = manager.generateSwarmConfigs(3);
      assert.strictEqual(swarm.length, 3);
      assert.deepStrictEqual(
        swarm.map(config => config.workerId),
        [1, 2, 3],
      );
      assert.strictEqual(new Set(swarm.map(config => config.port)).size, 3);

      const alternative = manager.getAlternativePort(7891);
      assert.strictEqual(alternative, 7892);

      manager.availablePorts = [9001];
      manager.failedPorts = new Set([9001]);
      const resetPort = manager.getAlternativePort(9001);
      assert.strictEqual(resetPort, 9001);
      assert.strictEqual(manager.failedPorts.size, 0);

      manager.availablePorts = Array.from({ length: 22 }, (_, index) => 7890 + index);
      const reassigned = await manager.forceReassignPort(8, 7895);
      assert.strictEqual(reassigned.workerId, 8);
      assert.notStrictEqual(reassigned.proxy.port, 7895);

      assert.deepStrictEqual(
        await manager.loadSessionToContext({ name: 'ctx' }, 7899),
        { context: { name: 'ctx' }, port: 7899, loaded: true },
      );
      manager.sessionManager = null;
      assert.strictEqual(await manager.loadSessionToContext({ name: 'ctx' }, 7899), false);

      manager.workerIdentities.set(8, reassigned);
      const workerStats = manager.getWorkerStats();
      assert.strictEqual(workerStats.length, 1);
      assert.strictEqual(workerStats[0].workerId, 8);
      assert.strictEqual(manager.getSessionStats(), null);

      manager.sessionManager = loaded.sessionManager;
      assert.deepStrictEqual(manager.getSessionStats(), loaded.sessionManager.getStats());

      manager.shutdown();
      assert.ok(loaded.state.consoleLogs.some(message => message.includes('SessionManager 统计')));
      assert.ok(loaded.state.consoleLogs.some(message => message.includes('ProxyProvider 统计')));
    } finally {
      loaded.restore();
    }
  });

  test('L2 触发封禁后，L1 应立刻避开同一端口', async () => {
    resetProxyProvider();
    const provider = getProxyProvider({
      healthCheckIntervalMs: 0,
      rateLimitIsolationMs: 60000
    });
    const loaded = loadNetworkManagerModule();

    try {
      const manager = new loaded.NetworkManager({
        proxyProvider: provider
      });
      manager.sessionManager = {
        async getOrRefreshSession() {
          return null;
        }
      };

      const l2Identity = await manager.assignWorkerIdentity(1);
      const l2Port = l2Identity.proxy.port;
      assert.ok(Number.isInteger(l2Port), 'L2 应拿到有效代理端口');

      await manager.markProxyFailed(1, 'HTTP 429');

      const browserProvider = new BrowserProvider({
        proxyProvider: provider,
        proxyConsumer: 'l1-discovery-browser',
        proxySessionKey: 'cross-layer'
      });

      const l1Lease = await browserProvider.ensureProxyLease('cross-layer-check');
      assert.notStrictEqual(l1Lease.proxy.port, l2Port);
      await browserProvider.releaseProxyLease();
    } finally {
      loaded.restore();
    }
  });

  test('单例导出应支持复用与 reset', () => {
    const loaded = loadNetworkManagerModule();
    try {
      const first = loaded.getNetworkManager({ maxWorkers: 3 });
      const second = loaded.getNetworkManager({ maxWorkers: 9 });

      assert.strictEqual(first, second);
      assert.strictEqual(first.maxWorkers, 3);

      let shutdownCalled = false;
      first.shutdown = () => {
        shutdownCalled = true;
      };

      loaded.resetNetworkManager();
      assert.strictEqual(shutdownCalled, true);

      const third = loaded.getNetworkManager({ maxWorkers: 7 });
      assert.notStrictEqual(third, first);
      assert.strictEqual(third.maxWorkers, 7);
    } finally {
      loaded.restore();
    }
  });
});
