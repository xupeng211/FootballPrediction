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

    it('HTTP 失败时应返回 httpFailure 并记录首屏失败统计', async () => {
      const warns = [];
      const handler = makeHandler({}, {
        logger: { warn: (event, payload) => warns.push({ event, payload }), info: () => {}, debug: () => {} },
        _createPureProtocolMonitor: () => ({
          pageSize: 25,
          sourceUrl: '',
          extractMatchesFromJson: () => []
        }),
        _fetchPureProtocolText: async () => ({
          success: false,
          status: 503,
          error: 'HTTP_503',
          retryAfterRaw: '5',
          text: 'blocked'
        })
      });

      const result = await handler._fetchPureProtocolPaginatedPages({
        apiBaseUrl: 'https://op.com/api/',
        maxPages: 1,
        timeoutMs: 1000,
        source: 'test',
        referer: 'https://op.com/',
        decryptor: { decrypt: async (value) => value },
        buildBaseUrl: (url) => url,
        buildPageUrl: (base, page) => `${base}/${page}/`
      });

      assert.deepStrictEqual(result.httpFailure, {
        page: 1,
        url: 'https://op.com/api//1/',
        statusCode: 503,
        error: 'HTTP_503',
        retryAfterRaw: '5',
        retryAfterMs: 0
      });
      assert.deepStrictEqual(result.pageStats, [{
        page: 1,
        url: 'https://op.com/api//1/',
        rows: 0,
        statusCode: 503,
        error: 'HTTP_503',
        retryAfterRaw: '5',
        retryAfterMs: 0
      }]);
      assert.ok(warns.some((entry) => entry.event === 'pure_protocol_archive_http_failure_payload'));
    });

    it('空 payload 时应记录 empty pageStats 并结束分页', async () => {
      const warns = [];
      const handler = makeHandler({}, {
        logger: { warn: (event, payload) => warns.push({ event, payload }), info: () => {}, debug: () => {} },
        _createPureProtocolMonitor: () => ({
          pageSize: 25,
          sourceUrl: '',
          extractMatchesFromJson: () => []
        }),
        _fetchPureProtocolText: async () => ({
          success: true,
          status: 200,
          text: ''
        })
      });

      const result = await handler._fetchPureProtocolPaginatedPages({
        apiBaseUrl: 'https://op.com/api/',
        maxPages: 1,
        timeoutMs: 1000,
        source: 'test',
        referer: 'https://op.com/',
        decryptor: { decrypt: async (value) => value },
        buildBaseUrl: (url) => url,
        buildPageUrl: (base, page) => `${base}/${page}/`
      });

      assert.deepStrictEqual(result.pageStats, [{
        page: 1,
        url: 'https://op.com/api//1/',
        rows: 0,
        total: 0,
        source: 'test:empty'
      }]);
      assert.strictEqual(result.httpFailure, null);
      assert.ok(warns.some((entry) => entry.event === 'pure_protocol_archive_blank_payload'));
    });

    it('解密成功时应分页去重、收敛 pageLimit 并同步 active proxy state', async () => {
      let fetchCount = 0;
      const handler = makeHandler({}, {
        _createPureProtocolMonitor: () => ({
          pageSize: 1,
          sourceUrl: '',
          extractMatchesFromJson(parsed) {
            return (parsed?.d?.rows || []).map((row) => row.match);
          }
        }),
        _fetchPureProtocolText: async () => {
          fetchCount += 1;
          if (fetchCount === 1) {
            return {
              success: true,
              status: 200,
              text: 'page-1',
              activeProxyState: {
                lease: {
                  id: 'lease-new',
                  proxy: { server: 'http://proxy-new', port: 7902 }
                },
                server: 'http://proxy-new',
                port: 7902
              }
            };
          }
          return {
            success: true,
            status: 200,
            text: 'page-2'
          };
        }
      });

      const result = await handler._fetchPureProtocolPaginatedPages({
        apiBaseUrl: 'https://op.com/api/',
        maxPages: 3,
        timeoutMs: 1000,
        source: 'test',
        referer: 'https://op.com/',
        decryptor: {
          async decrypt(text) {
            return text === 'page-1'
              ? {
                d: {
                  rows: [
                    { match: { hash: 'hash-1', url: 'https://op.com/match/1' } },
                    { match: { hash: 'hash-1', url: 'https://op.com/match/1' } }
                  ],
                  total: 2
                }
              }
              : {
                d: {
                  rows: [
                    { match: { hash: 'hash-2', url: 'https://op.com/match/2' } }
                  ],
                  total: 2
                }
              };
          }
        },
        buildBaseUrl: (url) => url,
        buildPageUrl: (base, page) => `${base}/${page}/`
      });

      assert.deepStrictEqual(result.matches, [
        { hash: 'hash-1', url: 'https://op.com/match/1' },
        { hash: 'hash-2', url: 'https://op.com/match/2' }
      ]);
      assert.strictEqual(result.pagesScanned, 2);
      assert.strictEqual(result.requestProxyLease.id, 'lease-new');
      assert.strictEqual(result.requestProxyPort, 7902);
    });

    it('首屏 decrypt failed 时应记录 payload 告警', async () => {
      const warns = [];
      const handler = makeHandler({}, {
        logger: { warn: (event, payload) => warns.push({ event, payload }), info: () => {}, debug: () => {} },
        _createPureProtocolMonitor: () => ({
          pageSize: 25,
          sourceUrl: '',
          extractMatchesFromJson: () => []
        }),
        _fetchPureProtocolText: async () => ({
          success: true,
          status: 200,
          text: 'encrypted-blob'
        })
      });

      const result = await handler._fetchPureProtocolPaginatedPages({
        apiBaseUrl: 'https://op.com/api/',
        maxPages: 1,
        timeoutMs: 1000,
        source: 'test',
        referer: 'https://op.com/',
        decryptor: {
          async decrypt() {
            throw new Error('bad decrypt');
          }
        },
        buildBaseUrl: (url) => url,
        buildPageUrl: (base, page) => `${base}/${page}/`
      });

      assert.deepStrictEqual(result.pageStats, [{
        page: 1,
        url: 'https://op.com/api//1/',
        rows: 0,
        error: 'decrypt_failed:bad decrypt'
      }]);
      assert.ok(warns.some((entry) => entry.event === 'pure_protocol_archive_decrypt_failed_payload'));
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

    it('命中缓存的 league context 时应跳过 navigate 并修复 archive URL', async () => {
      const breakerKey = 'breaker://cached';
      const navigations = [];
      const handler = makeHandler({
        _protocolRouteCache: new Map([[
          breakerKey,
          {
            leagueContext: {
              leagueUrl: 'https://op.com/league/',
              tournamentId: 'tid-cached',
              currentTournamentUrl: 'https://op.com/current/'
            }
          }
        ]]),
        stateProber: {
          deriveLeaguePageUrl: () => 'https://op.com/league/'
        },
        _resolveCircuitBreakerKey: () => breakerKey,
        navigate: async (url) => {
          navigations.push(url);
        }
      });

      const result = await handler._resolveLeagueTournamentContext(
        'https://op.com/results/',
        5000,
        'https://www.oddsportal.com/ajax-sport-country-tournament-archive_/1//X2X3/1/0/'
      );

      assert.equal(navigations.length, 0);
      assert.equal(result.leagueUrl, 'https://op.com/league/');
      assert.equal(result.tournamentId, 'tid-cached');
      assert.equal(result.currentTournamentUrl, 'https://op.com/current/');
      assert.match(result.repairedArchiveUrl, /tid-cached/);
    });

    it('未命中缓存时应导航发现 tournament token 并回写缓存', { concurrency: false }, async () => {
      const originalNow = Date.now;
      const timeMarks = [1000, 1001, 4101, 4200, 4300];
      const handler = makeHandler({
        _protocolRouteCache: new Map(),
        postApiDiscoveryWaitMs: 100,
        stateProber: {
          deriveLeaguePageUrl: () => 'https://op.com/league/',
          extractTournamentToken: async () => 'tid-live'
        },
        _resolveCircuitBreakerKey: () => 'breaker://live',
        navigateCalls: [],
        navigate: async (url, options) => {
          handler.navigator.navigateCalls.push({ url, options });
        }
      }, {
        _getCurrentTournamentEndpoint: () => 'https://op.com/current/live/',
        _buildTournamentUrlFromArchive: () => 'https://op.com/current/live/'
      });

      Date.now = () => timeMarks.shift() ?? 4300;

      try {
        const result = await handler._resolveLeagueTournamentContext(
          'https://op.com/results/',
          5000,
          'https://www.oddsportal.com/ajax-sport-country-tournament-archive_/1//X2X3/1/0/'
        );

        assert.equal(handler.navigator.navigateCalls.length, 1);
        assert.equal(result.tournamentId, 'tid-live');
        assert.equal(result.currentTournamentUrl, 'https://op.com/current/live/');
        assert.match(result.repairedArchiveUrl, /tid-live/);
        assert.equal(
          handler.navigator._protocolRouteCache.get('breaker://live').leagueContext.tournamentId,
          'tid-live'
        );
      } finally {
        Date.now = originalNow;
      }
    });

  });

  describe('_extractViaPureProtocol', () => {
    it('缺少 tournament token 时应抛出 PURE_PROTOCOL_TOURNAMENT_TOKEN_MISSING', async () => {
      const handler = makeHandler({}, {
        _resolvePureProtocolContext: async () => ({
          baseUrl: 'https://op.com/results/',
          outrightId: '',
          tournamentId: ''
        }),
        _resolvePureProtocolBookmakerHash: () => 'X2X3'
      });

      await assert.rejects(
        () => handler._extractViaPureProtocol({ baseUrl: 'https://op.com/results/' }),
        /PURE_PROTOCOL_TOURNAMENT_TOKEN_MISSING/
      );
    });

    it('sample 503 时应切换代理、恢复抓取并释放临时 lease', async () => {
      const events = [];
      let fetchCount = 0;
      const handler = makeHandler({
        traceId: 'trace-pure',
        archiveMaxPages: 2,
        archiveTimeoutMs: 1500,
        proxyLease: {
          id: 'lease-old',
          proxy: { server: 'http://proxy-old', port: 7891 }
        },
        proxyProvider: {
          async acquire(options) {
            events.push({ type: 'acquire', options });
            return {
              id: 'lease-new',
              proxy: { server: 'http://proxy-new', port: 7902 }
            };
          },
          async release(lease) {
            events.push({ type: 'release', leaseId: lease.id });
          },
          async reportFailure(leaseId, metadata) {
            events.push({ type: 'reportFailure', leaseId, metadata });
          },
          async reportSuccess(leaseId, metadata) {
            events.push({ type: 'reportSuccess', leaseId, metadata });
          }
        }
      }, {
        logger: {
          warn: (event, payload) => events.push({ type: 'warn', event, payload }),
          info: (event, payload) => events.push({ type: 'info', event, payload }),
          debug: () => {}
        },
        _resolvePureProtocolContext: async () => ({
          baseUrl: 'https://op.com/results/',
          requestedBaseUrl: 'https://op.com/results/',
          contextSource: 'requested',
          outrightId: 'ot-1',
          tournamentId: '',
          cookieHeader: 'session=abc',
          appBundleUrl: 'https://op.com/assets/app.js',
          seasonToken: '2025',
          locale: 'en'
        }),
        _resolvePureProtocolBookmakerHash: () => 'X2X3',
        _isRetryablePureProtocolFetchFailure: (result) => Number(result?.status) === 503,
        _waitPureProtocolFetchRetry: async (delayMs) => {
          events.push({ type: 'wait', delayMs });
        },
        _createPureProtocolMonitor: () => ({
          pageSize: 25,
          sourceUrl: '',
          extractMatchesFromJson(parsed, source) {
            events.push({ type: 'extract', source });
            return (parsed?.d?.rows || []).map((row) => row.match);
          }
        }),
        _createPureProtocolDecryptor: async (_context, samplePayload, sampleToken, bookmakerHash) => {
          events.push({ type: 'decryptor', samplePayload, sampleToken, bookmakerHash });
          return {
            async decrypt(text) {
              if (text === 'archive-encrypted') {
                return {
                  d: {
                    rows: [{ match: { hash: 'hash-1', url: 'https://op.com/match/1' } }],
                    total: 1
                  }
                };
              }
              return { d: { rows: [], total: 0 } };
            }
          };
        },
        _fetchPureProtocolText: async (_url, options = {}) => {
          fetchCount += 1;
          events.push({ type: 'fetch', fetchCount, proxyPort: options.proxyPort || null });
          if (fetchCount === 1) {
            return {
              success: false,
              status: 503,
              error: 'HTTP_503',
              text: 'blocked'
            };
          }
          if (fetchCount === 2) {
            return {
              success: true,
              status: 200,
              text: 'sample-encrypted'
            };
          }
          return {
            success: true,
            status: 200,
            text: 'archive-encrypted'
          };
        }
      });

      const result = await handler._extractViaPureProtocol({ baseUrl: 'https://op.com/results/' }, {
        maxPages: 2,
        timeoutMs: 1500
      });

      assert.equal(result.sourceState, 'PURE_PROTOCOL');
      assert.deepStrictEqual(result.matches, [{
        hash: 'hash-1',
        url: 'https://op.com/match/1'
      }]);
      assert.equal(events.filter((entry) => entry.type === 'fetch').length, 3);
      assert.equal(events.find((entry) => entry.type === 'fetch')?.proxyPort, 7891);
      assert.ok(events.some((entry) => entry.type === 'acquire' && entry.options.excludePorts.includes(7891)));
      assert.ok(events.some((entry) => entry.type === 'reportFailure' && entry.leaseId === 'lease-old'));
      assert.ok(events.some((entry) => entry.type === 'reportSuccess' && entry.leaseId === 'lease-new'));
      assert.ok(events.some((entry) => entry.type === 'release' && entry.leaseId === 'lease-new'));
      assert.ok(events.some((entry) => entry.type === 'warn' && entry.event === 'pure_protocol_sample_proxy_switching'));
    });

    it('缺少 bookmaker hash 时应抛出 PURE_PROTOCOL_BOOKMAKER_HASH_MISSING', async () => {
      const handler = makeHandler({}, {
        _resolvePureProtocolContext: async () => ({
          baseUrl: 'https://op.com/results/',
          outrightId: 'ot-1',
          tournamentId: ''
        }),
        _resolvePureProtocolBookmakerHash: () => ''
      });

      await assert.rejects(
        () => handler._extractViaPureProtocol({ baseUrl: 'https://op.com/results/' }),
        /PURE_PROTOCOL_BOOKMAKER_HASH_MISSING/
      );
    });

    it('sample payload 缺失时应抛出 PURE_PROTOCOL_SAMPLE_PAYLOAD_MISSING', async () => {
      const handler = makeHandler({}, {
        _resolvePureProtocolContext: async () => ({
          baseUrl: 'https://op.com/results/',
          outrightId: 'ot-1',
          tournamentId: '',
          appBundleUrl: 'https://op.com/assets/app.js'
        }),
        _resolvePureProtocolBookmakerHash: () => 'X2X3',
        _isRetryablePureProtocolFetchFailure: () => false,
        _fetchPureProtocolText: async () => ({
          success: true,
          status: 200,
          text: ''
        })
      });

      await assert.rejects(
        () => handler._extractViaPureProtocol({ baseUrl: 'https://op.com/results/' }),
        /PURE_PROTOCOL_SAMPLE_PAYLOAD_MISSING/
      );
    });

    it('命中 warm cached decryptor 且释放代理失败时应记录日志', async () => {
      const logs = [];
      let fetchCount = 0;
      const handler = makeHandler({
        traceId: 'trace-warm',
        proxyLease: {
          id: 'lease-navigator',
          proxy: { server: 'http://proxy-nav', port: 7891 }
        },
        decryptor: {
          decryptFn() {},
          async decrypt(text) {
            if (text === 'archive-encrypted') {
              return {
                d: {
                  rows: [{ match: { hash: 'hash-1', url: 'https://op.com/match/1' } }],
                  total: 1
                }
              };
            }
            return { d: { rows: [], total: 0 } };
          },
          getAlgorithmVersion() {
            return 'alg-v1';
          }
        },
        proxyProvider: {
          async release() {
            throw new Error('release failed');
          }
        }
      }, {
        logger: {
          warn: (event, payload) => logs.push({ level: 'warn', event, payload }),
          info: (event, payload) => logs.push({ level: 'info', event, payload }),
          debug: () => {}
        },
        _resolvePureProtocolContext: async () => ({
          baseUrl: 'https://op.com/results/',
          requestedBaseUrl: 'https://op.com/results/',
          contextSource: 'requested',
          outrightId: 'ot-1',
          tournamentId: '',
          cookieHeader: '',
          appBundleUrl: 'https://op.com/assets/app.js',
          seasonToken: '2025',
          locale: 'en'
        }),
        _resolvePureProtocolBookmakerHash: () => 'X2X3',
        _createPureProtocolMonitor: () => ({
          pageSize: 25,
          sourceUrl: '',
          extractMatchesFromJson(parsed) {
            return (parsed?.d?.rows || []).map((row) => row.match);
          }
        }),
        _fetchPureProtocolText: async () => {
          fetchCount += 1;
          return fetchCount === 1
            ? {
              success: true,
              status: 200,
              text: 'sample-encrypted'
            }
            : {
              success: true,
              status: 200,
              text: 'archive-encrypted'
            };
        }
      });

      const result = await handler._extractViaPureProtocol({ baseUrl: 'https://op.com/results/' }, {
        requestProxyLease: {
          id: 'lease-temp',
          proxy: { server: 'http://proxy-temp', port: 7902 }
        }
      });

      assert.equal(result.sourceState, 'PURE_PROTOCOL');
      assert.deepStrictEqual(result.matches, [{
        hash: 'hash-1',
        url: 'https://op.com/match/1'
      }]);
      assert.ok(logs.some((entry) => entry.event === 'pure_protocol_cached_decryptor_hit'));
      assert.ok(logs.some((entry) => entry.event === 'pure_protocol_sample_proxy_release_failed'));
    });
  });
});
