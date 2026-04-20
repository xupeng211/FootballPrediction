'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { reconFetchCoordinator } = require('../../src/infrastructure/recon/services/ReconFetchCoordinator');

function makeNetworkMonitor(overrides = {}) {
  return {
    sourceUrl: '',
    pageSize: 25,
    setPage: () => {},
    fetchArchivePages: async () => ({ matches: [], pageStats: [], pagesScanned: 0, totalCandidates: 0 }),
    fetchCurrentTournamentPages: async () => ({ matches: [], pageStats: [], pagesScanned: 0, totalCandidates: 0 }),
    ...overrides
  };
}

function makeNavigator(overrides = {}) {
  return {
    traceId: 'test-trace',
    proxyLease: null,
    proxy: null,
    proxyProvider: null,
    archiveTimeoutMs: 5000,
    archiveMaxPages: 5,
    postApiDiscoveryWaitMs: 100,
    _protocolRouteCache: null,
    stateProber: {
      deriveLeaguePageUrl: (url) => `${url}standings/`,
      deriveCurrentResultsUrl: (url) => `${url}results/`,
      extractTournamentToken: async () => ''
    },
    networkMonitor: makeNetworkMonitor(),
    _resolveCircuitBreakerKey: () => 'test-breaker-key',
    _executeWith503Retry: async (fn) => fn(),
    _executeWithCircuitBreaker: async (key, fn) => fn(),
    ...overrides
  };
}

function makeHandler(navOverrides = {}, handlerOverrides = {}) {
  const handler = {
    logger: { warn: () => {}, info: () => {}, debug: () => {} },
    page: null,
    navigator: makeNavigator(navOverrides),
    _callNavigatorOverride: async (name, fn, ...args) => fn(...args),
    _resultHasDecryptFailure: () => false,
    _buildArchivePageUrl: (b, p) => `${b.replace(/\/$/, '')}/${p}/`,
    _buildPureProtocolHeaders: () => ({ accept: 'application/json' }),
    _fetchPureProtocolText: async () => ({ success: false, text: '', status: 0, error: 'test' }),
    _resolveLatestPureProtocolAppScript: async () => ({ appScriptUrl: '' }),
    _resolvePureProtocolCookieHeader: async () => '',
    _resolveDecryptorFromAppScript: async () => null,
    _decryptPureProtocolResponse: async () => ({ success: false }),
    _emitReconEvent: () => {},
    _resolveLeagueTournamentContext: async () => null,
    _resolvePureProtocolBookmakerHash: () => '',
    _resolvePureProtocolContext: async () => null,
    _createPureProtocolMonitor: () => makeNetworkMonitor(),
    ...handlerOverrides
  };
  Object.assign(handler, reconFetchCoordinator);
  Object.assign(handler, handlerOverrides);
  return handler;
}

describe('ReconFetchCoordinator mixin', () => {
  describe('导出结构', () => {
    it('reconFetchCoordinator 应是非空对象', () => {
      assert.ok(reconFetchCoordinator && typeof reconFetchCoordinator === 'object');
    });

    it('应包含核心 async 方法', () => {
      assert.ok(typeof reconFetchCoordinator._fetchAndDecrypt === 'function');
      assert.ok(typeof reconFetchCoordinator._fetchAndDecryptWithOptions === 'function');
      assert.ok(typeof reconFetchCoordinator._fetchCurrentTournament === 'function');
      assert.ok(typeof reconFetchCoordinator._fallbackToLeagueTournament === 'function');
      assert.ok(typeof reconFetchCoordinator._extractViaPureProtocol === 'function');
      assert.ok(typeof reconFetchCoordinator._resolveLeagueTournamentContext === 'function');
    });

    it('应包含工具方法', () => {
      assert.ok(typeof reconFetchCoordinator._buildArchivePageUrl === 'function');
      assert.ok(typeof reconFetchCoordinator._buildCurrentTournamentPageUrl === 'function');
      assert.ok(typeof reconFetchCoordinator._fetchPureProtocolPaginatedPages === 'function');
      assert.ok(typeof reconFetchCoordinator._repairArchiveEndpointWithTournamentId === 'function');
      assert.ok(typeof reconFetchCoordinator._buildTournamentUrlFromArchive === 'function');
    });
  });

  describe('_fetchAndDecrypt 转发', () => {
    it('应委托给 _fetchAndDecryptWithOptions', async () => {
      const calls = [];
      const handler = makeHandler();
      handler._fetchAndDecryptWithOptions = async (url, maxPages, timeout, opts) => {
        calls.push({ url, maxPages, timeout, opts });
        return { matches: [], pageStats: [], totalFound: 0 };
      };

      const result = await handler._fetchAndDecrypt('https://op.com/', 3, 6000);
      assert.strictEqual(calls.length, 1);
      assert.strictEqual(calls[0].url, 'https://op.com/');
      assert.strictEqual(calls[0].maxPages, 3);
      assert.ok(Array.isArray(result.matches));
    });
  });

  describe('_fetchAndDecryptWithOptions', () => {
    it('fetch 成功无解密失败时直接返回', async () => {
      const fetchResult = { matches: [{ hash: 'h1' }], pageStats: [], pagesScanned: 1, totalCandidates: 1 };
      const handler = makeHandler({
        networkMonitor: makeNetworkMonitor({
          fetchArchivePages: async () => fetchResult
        })
      }, {
        _resultHasDecryptFailure: () => false
      });

      const result = await handler._fetchAndDecryptWithOptions('https://op.com/', 1, 5000);
      assert.ok(result);
      assert.deepStrictEqual(result.matches, fetchResult.matches);
    });

    it('fetch 失败时仍返回结果对象', async () => {
      const handler = makeHandler({
        networkMonitor: makeNetworkMonitor({
          fetchArchivePages: async () => ({ matches: [], pageStats: [], pagesScanned: 0, totalCandidates: 0 })
        })
      });

      const result = await handler._fetchAndDecryptWithOptions('https://op.com/', 1, 2000);
      assert.ok(result);
      assert.deepStrictEqual(result.matches, []);
    });

    it('有解密失败时触发 navigator relaunch 路径', async () => {
      let relaunched = false;
      const handler = makeHandler({
        networkMonitor: makeNetworkMonitor({
          fetchArchivePages: async () => ({ matches: [], pageStats: [], pagesScanned: 0, totalCandidates: 0 })
        }),
        close: async () => {},
        launch: async () => { relaunched = true; },
        lastLaunchOptions: {}
      }, {
        _resultHasDecryptFailure: () => true
      });

      await handler._fetchAndDecryptWithOptions('https://op.com/', 1, 2000);
      assert.ok(relaunched);
    });

    it('relaunch 失败时捕获错误并返回 initialResult', async () => {
      const warns = [];
      const handler = makeHandler({
        networkMonitor: makeNetworkMonitor({
          fetchArchivePages: async () => ({ matches: [], pageStats: [] })
        }),
        close: async () => { throw new Error('close failed'); }
      }, {
        _resultHasDecryptFailure: () => true,
        logger: { warn: (event) => warns.push(event), info: () => {}, debug: () => {} }
      });

      const result = await handler._fetchAndDecryptWithOptions('https://op.com/', 1, 2000);
      assert.ok(result);
      assert.ok(warns.some((event) => event.includes('relaunch')));
    });
  });

  describe('_fetchCurrentTournament', () => {
    it('应通过 navigator 获取 tournament 页面', async () => {
      const handler = makeHandler({
        networkMonitor: makeNetworkMonitor({
          fetchCurrentTournamentPages: async () => ({ matches: [{ hash: 'x' }], pageStats: [] })
        })
      });

      const result = await handler._fetchCurrentTournament('https://op.com/t/', 5, 10000);
      assert.ok(result);
      assert.ok(Array.isArray(result.matches));
    });

    it('空 matches 时返回空结果集', async () => {
      const handler = makeHandler({
        networkMonitor: makeNetworkMonitor({
          fetchCurrentTournamentPages: async () => ({ matches: [], pageStats: [] })
        })
      });

      const result = await handler._fetchCurrentTournament('https://op.com/t/', 5, 10000);
      assert.ok(result);
      assert.deepStrictEqual(result.matches, []);
    });
  });

  describe('_fallbackToLeagueTournament', () => {
    it('context 无 currentTournamentUrl 时返回 SOURCE_EMPTY', async () => {
      const handler = makeHandler({}, {
        _resolveLeagueTournamentContext: async () => ({ currentTournamentUrl: null, leagueUrl: null })
      });

      const result = await handler._fallbackToLeagueTournament('https://op.com/', null, 5, 5000);
      assert.strictEqual(result.sourceState, 'SOURCE_EMPTY');
      assert.deepStrictEqual(result.matches, []);
    });

    it('context 有 currentTournamentUrl 时调用 _fetchCurrentTournament', async () => {
      const fetchCalls = [];
      const handler = makeHandler({}, {
        _resolveLeagueTournamentContext: async () => ({
          currentTournamentUrl: 'https://op.com/t/tid1/',
          leagueUrl: 'https://op.com/'
        })
      });
      handler._fetchCurrentTournament = async (url) => {
        fetchCalls.push(url);
        return { matches: [{ hash: 'h1' }], pageStats: [], sourceState: 'CURRENT_TOURNAMENT_FALLBACK' };
      };

      const result = await handler._fallbackToLeagueTournament('https://op.com/', null, 5, 5000);
      assert.ok(fetchCalls.length > 0);
      assert.strictEqual(result.sourceState, 'CURRENT_TOURNAMENT_FALLBACK');
    });

    it('_fetchCurrentTournament 返回空 matches 时 sourceState 为 SOURCE_EMPTY', async () => {
      const handler = makeHandler({}, {
        _resolveLeagueTournamentContext: async () => ({
          currentTournamentUrl: 'https://op.com/t/',
          leagueUrl: 'https://op.com/'
        })
      });
      handler._fetchCurrentTournament = async () => ({ matches: [], pageStats: [] });

      const result = await handler._fallbackToLeagueTournament('https://op.com/', null, 5, 5000);
      assert.strictEqual(result.sourceState, 'SOURCE_EMPTY');
    });
  });

  describe('_buildArchivePageUrl', () => {
    it('第 1 页不含 page 路径段', () => {
      const handler = makeHandler();
      const url = handler._buildArchivePageUrl('https://op.com/archive', 1);
      assert.ok(url.startsWith('https://op.com/archive'));
      assert.ok(!url.includes('/page/'));
    });

    it('第 2 页含 page/2 路径段', () => {
      const handler = makeHandler();
      const url = handler._buildArchivePageUrl('https://op.com/archive', 2);
      assert.ok(url.includes('/page/2/'));
    });
  });

  describe('_buildCurrentTournamentPageUrl', () => {
    it('第 1 页不含数字路径段', () => {
      const handler = makeHandler();
      const url = handler._buildCurrentTournamentPageUrl('https://op.com/t', 1);
      assert.ok(url.startsWith('https://op.com/t'));
    });

    it('第 3 页含数字路径段', () => {
      const handler = makeHandler();
      const url = handler._buildCurrentTournamentPageUrl('https://op.com/t', 3);
      assert.ok(url.includes('/3/'));
    });
  });

  describe('_buildTournamentUrlFromArchive', () => {
    it('非法 archiveApiUrl 返回 null', () => {
      const handler = makeHandler();
      const result = handler._buildTournamentUrlFromArchive('https://op.com/', 'tid1');
      assert.strictEqual(result, null);
    });

    it('空 archiveApiUrl 返回 null', () => {
      const handler = makeHandler();
      assert.strictEqual(handler._buildTournamentUrlFromArchive('', 'tid'), null);
    });

    it('合法 archiveApiUrl 返回构建的 tournament URL', () => {
      const handler = makeHandler();
      const url = 'https://www.oddsportal.com/ajax-sport-country-tournament-archive_/1/tid123/X2X3/1/0/';
      const result = handler._buildTournamentUrlFromArchive(url, 'tid123');
      assert.ok(typeof result === 'string');
    });
  });

  describe('_fetchPureProtocolPaginatedPages', () => {
    it('空配置应返回 matches 数组', async () => {
      const monitor = makeNetworkMonitor();
      const handler = makeHandler({}, {
        _createPureProtocolMonitor: () => monitor,
        _fetchPureProtocolText: async () => ({ success: true, text: JSON.stringify({ d: { rows: [], total: 0 } }), status: 200 }),
        _decryptPureProtocolResponse: async () => ({ success: true, parsed: { d: { rows: [], total: 0 } }, matches: [] })
      });

      const result = await handler._fetchPureProtocolPaginatedPages({
        apiBaseUrl: 'https://op.com/api/',
        maxPages: 1,
        timeoutMs: 2000,
        source: 'test',
        referer: 'https://op.com/',
        decryptor: { decrypt: async (d) => d },
        buildBaseUrl: (u) => u,
        buildPageUrl: (b, p) => `${b}/${p}/`
      });
      assert.ok(result);
      assert.ok(Array.isArray(result.matches));
    });

    it('无效解密时不应崩溃', async () => {
      const handler = makeHandler({}, {
        _createPureProtocolMonitor: () => makeNetworkMonitor(),
        _fetchPureProtocolText: async () => ({ success: true, text: 'encrypted_blob', status: 200 }),
        _decryptPureProtocolResponse: async () => ({ success: false, error: 'decrypt_failed' })
      });

      const result = await handler._fetchPureProtocolPaginatedPages({
        apiBaseUrl: 'https://op.com/api/',
        maxPages: 1,
        timeoutMs: 1000,
        source: 'test',
        referer: 'https://op.com/',
        decryptor: null,
        buildBaseUrl: (u) => u,
        buildPageUrl: (b, p) => `${b}/${p}/`
      });
      assert.ok(result);
    });
  });

  describe('_resolveLeagueTournamentContext', () => {
    it('navigator.stateProber.deriveLeaguePageUrl 返回空时返回 null 上下文', async () => {
      const handler = makeHandler({
        stateProber: {
          deriveLeaguePageUrl: () => null,
          deriveCurrentResultsUrl: (u) => u,
          extractTournamentToken: async () => ''
        }
      });

      const result = await handler._resolveLeagueTournamentContext('https://op.com/', 5000, null, {});
      assert.ok(result);
      assert.strictEqual(result.tournamentId, null);
    });
  });
});
