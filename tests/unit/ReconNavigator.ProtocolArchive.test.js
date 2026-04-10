'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { ReconNavigator } = require('../../src/infrastructure/recon/ReconNavigator');
const { ReconCircuitBreakerPool } = require('../../src/infrastructure/recon/ReconResilience');

describe('ReconNavigator - Protocol Archive', () => {
  it('navigate 时应重置跨联赛残留的 apiEndpoints 与 decryptor', async () => {
    const navigator = new ReconNavigator({
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      traceId: 'trace-reset'
    });

    const staleDecryptor = navigator.decryptor;
    navigator.apiEndpoints.add('oddsportal://stale-endpoint');
    navigator.browser = { isConnected: () => true };
    navigator.context = {};
    navigator.page = {
      isClosed: () => false,
      async goto() {},
      async waitForTimeout() {},
      async evaluate() {}
    };

    await navigator.navigate('oddsportal://fresh-page', { waitUntil: 'networkidle', timeout: 10 });

    assert.strictEqual(navigator.apiEndpoints.size, 0);
    assert.notStrictEqual(navigator.decryptor, staleDecryptor);
    assert.strictEqual(navigator.decryptor.traceId, 'trace-reset');
  });

  it('resetContextPerBatch 应重建 page 并重新挂载网络拦截', async () => {
    const attachedPages = [];
    const statePages = [];
    let detachCount = 0;
    let resetCount = 0;
    const rotatedPage = {
      isClosed: () => false
    };

    const navigator = new ReconNavigator({
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      traceId: 'trace-batch-reset'
    });

    navigator.browser = { isConnected: () => true };
    navigator.context = {};
    navigator.page = {
      isClosed: () => false
    };
    navigator.networkMonitor.detach = () => {
      detachCount += 1;
    };
    navigator.networkMonitor.reset = () => {
      resetCount += 1;
    };
    navigator.networkMonitor.attach = (page) => {
      attachedPages.push(page);
    };
    navigator.domScraper.setPage = (page) => {
      statePages.push({ type: 'dom', page });
    };
    navigator.stateProber.setPage = (page) => {
      statePages.push({ type: 'state', page });
    };
    navigator.browserContext.resetContext = async () => rotatedPage;
    navigator.browserContext.getFingerprintSummary = () => ({ fingerprintSeed: 'seed-rotated' });

    const page = await navigator.resetContextPerBatch({ reason: 'unit_batch' });

    assert.strictEqual(page, rotatedPage);
    assert.strictEqual(navigator.page, rotatedPage);
    assert.strictEqual(detachCount, 1);
    assert.strictEqual(resetCount, 1);
    assert.deepStrictEqual(attachedPages, [rotatedPage]);
    assert.deepStrictEqual(statePages, [
      { type: 'dom', page: rotatedPage },
      { type: 'state', page: rotatedPage }
    ]);
  });

  it('protocolArchiveExtract 应在档案批次开始前触发 context reset', async () => {
    let resetCalls = 0;
    const navigator = new ReconNavigator({
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      traceId: 'trace-protocol-reset'
    });

    navigator.browser = { isConnected: () => true };
    navigator.context = {};
    navigator.page = {
      isClosed: () => false,
      async waitForTimeout() {}
    };
    navigator.resetContextPerBatch = async () => {
      resetCalls += 1;
      return navigator.page;
    };
    navigator.navigate = async () => {};
    navigator.apiEndpoints.add('oddsportal://ajax-sport-country-tournament-archive_/1/foo/bar/2/1/');
    navigator._fetchAndDecrypt = async () => ({
      matches: [
        {
          hash: 'archive-hash',
          url: 'oddsportal://match/archive-hash',
          homeTeam: 'A',
          awayTeam: 'B',
          matchDate: '2025-08-15T19:00:00.000Z'
        }
      ],
      pageStats: [{ page: 1, rows: 1, newRows: 1, total: 1 }]
    });

    const result = await navigator.protocolArchiveExtract(
      'oddsportal://root/football/england/premier-league-2025-2026/results/',
      { preferCurrentSeasonSource: false, maxPages: 3, timeoutMs: 1500 }
    );

    assert.strictEqual(resetCalls, 1);
    assert.strictEqual(result.matches.length, 1);
    assert.strictEqual(result.matches[0].hash, 'archive-hash');
  });

  it('应通过单一 payload 对象向 page.evaluate 传递 fetchUrl 与 timeout', async () => {
    const evaluatePayloads = [];

    const navigator = new ReconNavigator({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    navigator.browser = { isConnected: () => true };
    navigator.context = {};
    navigator.page = {
      isClosed: () => false,
      async evaluate(fn, payload) {
        evaluatePayloads.push(payload);
        if (!payload || typeof payload !== 'object') {
          throw new Error('payload_missing');
        }

        return {
          success: true,
          text: 'encrypted-body'
        };
      }
    };

    navigator.decryptor = {
      getAlgorithmVersion: () => 'mock',
      decrypt: async () => JSON.stringify({
        s: 1,
        d: {
          total: 1,
          rows: [
            {
              encodeEventId: '44RKa9ke',
              url: '/football/england/premier-league-2024-2025/bournemouth-leicester-44RKa9ke/',
              'home-name': 'Bournemouth',
              'away-name': 'Leicester',
              'date-start-timestamp': 1748185200
            }
          ]
        }
      })
    };

    const result = await navigator._fetchAndDecrypt(
      'oddsportal://ajax-sport-country-tournament-archive_/1/foo/1/0/',
      1,
      90000
    );

    assert.strictEqual(result.totalCandidates, 1);
    assert.strictEqual(result.matches[0].hash, '44RKa9ke');
    assert.strictEqual(evaluatePayloads.length, 1);
    assert.strictEqual(evaluatePayloads[0].fetchTimeout, 90000);
    assert.ok(evaluatePayloads[0].fetchUrl.startsWith('oddsportal://ajax-sport-country-tournament-archive_/1/foo/1/0/'));
    assert.ok(evaluatePayloads[0].fetchUrl.includes('/?_='), 'fetchUrl 应带缓存穿透参数');
  });

  it('解密失败后应重提取 decryptor 并重试一次', async () => {
    let refreshed = false;
    let extractCalls = 0;

    const navigator = new ReconNavigator({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    navigator.browser = { isConnected: () => true };
    navigator.context = {};
    navigator.page = {
      isClosed: () => false,
      async evaluate(_fn, payload) {
        return {
          success: true,
          text: payload.fetchUrl.includes('/?_=') ? 'encrypted-body' : ''
        };
      }
    };

    navigator.decryptor = {
      getAlgorithmVersion: () => 'stale',
      async extractDecryptor() {
        extractCalls++;
        refreshed = true;
      },
      async decrypt() {
        if (!refreshed) {
          throw new Error('stale decryptor');
        }

        return JSON.stringify({
          d: {
            total: 1,
            rows: [
              {
                encodeEventId: 'RtRyH123',
                url: '/football/england/premier-league-2024-2025/a-b-RtRyH123/',
                'home-name': 'A',
                'away-name': 'B',
                'date-start-timestamp': 1748185200
              }
            ]
          }
        });
      }
    };

    const result = await navigator._fetchAndDecrypt(
      'oddsportal://ajax-sport-country-tournament-archive_/1/foo/1/0/',
      1,
      90000
    );

    assert.strictEqual(extractCalls, 1);
    assert.strictEqual(result.totalCandidates, 1);
    assert.strictEqual(result.matches[0].hash, 'RtRyH123');
  });

  it('脚本包装响应应先解包，不应误触发 decryptor', async () => {
    let decryptCalls = 0;
    let extractCalls = 0;

    const navigator = new ReconNavigator({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    navigator.decryptor = {
      getAlgorithmVersion: () => null,
      async extractDecryptor() {
        extractCalls++;
        throw new Error('should_not_extract_for_script_wrapper');
      },
      async decrypt() {
        decryptCalls++;
        throw new Error('should_not_decrypt_for_script_wrapper');
      }
    };

    const wrappedBody = [
      "if (typeof pageVar == 'string') { pageVar = JSON.parse(pageVar); }",
      'if (typeof pageVar != "undefined") {',
      '  pageVar = pageOutrightsVar = Object.assign(pageVar, JSON.parse("{\\"d\\":{\\"total\\":1,\\"rows\\":[{\\"encodeEventId\\":\\"WrPdH456\\",\\"url\\":\\"/football/europe/champions-league-2025-2026/a-b-WrPdH456/\\",\\"home-name\\":\\"A\\",\\"away-name\\":\\"B\\",\\"date-start-timestamp\\":1748185200}]}}"));',
      '}'
    ].join(' ');

    const matches = await navigator._parseApiResponse(
      wrappedBody,
      'https://www.oddsportal.com/ajax-user-data/t/champions-league-2025-2026/'
    );

    assert.strictEqual(extractCalls, 0);
    assert.strictEqual(decryptCalls, 0);
    assert.strictEqual(matches.length, 1);
    assert.strictEqual(matches[0].hash, 'WrPdH456');
    assert.strictEqual(matches[0].homeTeam, 'A');
    assert.strictEqual(matches[0].awayTeam, 'B');
  });

  it('当前赛季应改走联赛主页的 tournament 接口，而不是 results archive 接口', async () => {
    const navigatedUrls = [];
    const fetchCalls = [];

    const navigator = new ReconNavigator({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    navigator.browser = { isConnected: () => true };
    navigator.context = {};
    navigator.page = {
      isClosed: () => false,
      async waitForTimeout() {},
      async evaluate() {
        return [];
      }
    };
    navigator.navigate = async (url) => {
      navigatedUrls.push(url);
    };
    navigator._getCurrentTournamentEndpoint = () =>
      'oddsportal://ajax-sport-country-tournament_/1/KKay4EE8/X262144e5337354f3b0f5c5135943/1/';
    navigator._fetchCurrentTournament = async (url, maxPages, timeoutMs) => {
      fetchCalls.push({ url, maxPages, timeoutMs });
      return {
        matches: [
          {
            hash: 'current-hash',
            url: 'oddsportal://match/current-hash',
            homeTeam: 'Bournemouth',
            awayTeam: 'Leicester',
            matchDate: '2025-08-15T19:00:00.000Z'
          }
        ],
        pagesScanned: 2,
        totalCandidates: 1,
        pageStats: [{ page: 1, rows: 1, newRows: 1, total: 1 }]
      };
    };

    const result = await navigator.protocolArchiveExtract(
      'oddsportal://root/football/england/premier-league-2025-2026/results/',
      { preferCurrentSeasonSource: true, maxPages: 7, timeoutMs: 1234 }
    );

    assert.deepStrictEqual(navigatedUrls, [
      'oddsportal://root/football/england/premier-league/results/',
      'oddsportal://root/football/england/premier-league/'
    ]);
    assert.deepStrictEqual(fetchCalls, [
      {
        url: 'oddsportal://ajax-sport-country-tournament_/1/KKay4EE8/X262144e5337354f3b0f5c5135943/1/',
        maxPages: 7,
        timeoutMs: 1234
      }
    ]);
    assert.strictEqual(result.sourceState, 'CURRENT_TOURNAMENT');
    assert.strictEqual(result.totalCandidates, 1);
    assert.strictEqual(result.matches[0].hash, 'current-hash');
  });

  it('联赛主页存在静态 oddsRequest 时，应直接从 HTML 恢复 current tournament 接口', async () => {
    const navigator = new ReconNavigator({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    navigator.browser = { isConnected: () => true };
    navigator.context = {};
    navigator.page = {
      isClosed: () => false,
      url() {
        return 'oddsportal://root/football/japan/j1-league/';
      },
      async content() {
        return [
          '<html><body>',
          '<tournament-component :sport-data="{&quot;oddsRequest&quot;:{&quot;url&quot;:&quot;/ajax-sport-country-tournament_/1/lv6akwBC/X262144/1/?_=1775367493&quot;}}"></tournament-component>',
          '</body></html>'
        ].join('');
      }
    };

    const endpoint = await navigator._getCurrentTournamentEndpoint();

    assert.strictEqual(
      endpoint,
      'oddsportal://root/ajax-sport-country-tournament_/1/lv6akwBC/X262144/1/?_=1775367493'
    );
    assert.ok(navigator.apiEndpoints.has(endpoint));
  });

  it('联赛主页缺失 outright id 时应使用 otCode 修复 archive 与 tournament 接口', async () => {
    const navigator = new ReconNavigator({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    navigator.browser = { isConnected: () => true };
    navigator.context = {};
    navigator.page = {
      isClosed: () => false,
      async waitForTimeout() {},
      async content() {
        return [
          '<html><body>',
          '<script>',
          "pageOutrightsVar = '{\"id\":\"\",\"sid\":1,\"cid\":100,\"archive\":true}';",
          '</script>',
          '</body></html>'
        ].join('');
      },
      async evaluate(fn) {
        if (typeof fn === 'function') {
          return '5fdb38ad-528a-4fb9-a576-b8c42e07565d';
        }
        return null;
      }
    };
    navigator.navigate = async () => {};
    navigator._getCurrentTournamentEndpoint = () => null;

    const context = await navigator._resolveLeagueTournamentContext(
      'oddsportal://root/football/japan/j1-league-2026/results/',
      1234,
      'oddsportal://ajax-sport-country-tournament-archive_/1//X262144/1/0/'
    );

    assert.deepStrictEqual(context, {
      leagueUrl: 'oddsportal://root/football/japan/j1-league-2026/',
      tournamentId: '5fdb38ad-528a-4fb9-a576-b8c42e07565d',
      repairedArchiveUrl: 'oddsportal://ajax-sport-country-tournament-archive_/1/5fdb38ad-528a-4fb9-a576-b8c42e07565d/X262144/1/0/',
      currentTournamentUrl: 'oddsportal://ajax-sport-country-tournament_/1/5fdb38ad-528a-4fb9-a576-b8c42e07565d/X262144/1/'
    });
  });

  it('当前赛季 results 页 DOM 出现比赛行时，应优先使用 DOM 候选而不是 archive 接口', async () => {
    const navigatedUrls = [];

    const navigator = new ReconNavigator({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    navigator.browser = { isConnected: () => true };
    navigator.context = {};
    navigator.page = {
      isClosed: () => false,
      async waitForTimeout() {},
      async evaluate(_fn, payload) {
        if (payload && payload.leaguePathPrefix) {
          return [
            {
              hash: 'dom-hash',
              url: 'oddsportal://match/dom-hash',
              homeTeam: 'Brentford',
              awayTeam: 'Everton',
              matchDate: null,
              source: 'current_results_dom'
            }
          ];
        }
        return undefined;
      }
    };
    navigator.navigate = async (url) => {
      navigatedUrls.push(url);
    };
    navigator._getCurrentTournamentEndpoint = () => {
      throw new Error('should_not_use_tournament_api_when_dom_ready');
    };

    const result = await navigator.protocolArchiveExtract(
      'oddsportal://root/football/england/premier-league-2025-2026/results/',
      { preferCurrentSeasonSource: true, maxPages: 7, timeoutMs: 1234 }
    );

    assert.deepStrictEqual(navigatedUrls, [
      'oddsportal://root/football/england/premier-league/results/'
    ]);
    assert.strictEqual(result.sourceState, 'CURRENT_RESULTS_DOM');
    assert.strictEqual(result.totalCandidates, 1);
    assert.strictEqual(result.matches[0].hash, 'dom-hash');
  });

  it('当前赛季 results 页 archive URL 缺少 tournament id 时，应通过 pageOutrightsVar 修复后再抓取', async () => {
    const fetchedArchiveUrls = [];

    const navigator = new ReconNavigator({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    navigator.browser = { isConnected: () => true };
    navigator.context = {};
    navigator.page = {
      isClosed: () => false,
      async waitForTimeout() {},
      async evaluate(fn, payload) {
        if (payload && payload.leaguePathPrefix) {
          return [];
        }

        if (typeof fn === 'function') {
          return {
            id: 'KKay4EE8',
            sid: 1,
            cid: 198,
            archive: true
          };
        }

        return null;
      }
    };
    navigator.navigate = async () => {
      navigator.apiEndpoints = new Set([
        'oddsportal://ajax-sport-country-tournament-archive_/1//X262144/1/0/?_=1'
      ]);
    };
    navigator._fetchAndDecrypt = async (url) => {
      fetchedArchiveUrls.push(url);
      return {
        matches: [
          {
            hash: 'archive-hash',
            url: 'oddsportal://match/archive-hash',
            homeTeam: 'Aston Villa',
            awayTeam: 'Newcastle United',
            matchDate: '2025-08-16T11:30:00.000Z'
          }
        ],
        pagesScanned: 4,
        totalCandidates: 1,
        pageStats: [{ page: 1, rows: 1, newRows: 1, total: 1 }]
      };
    };
    navigator._getCurrentTournamentEndpoint = () => null;

    const result = await navigator.protocolArchiveExtract(
      'oddsportal://root/football/england/premier-league-2025-2026/results/',
      { preferCurrentSeasonSource: true, maxPages: 8, timeoutMs: 1234 }
    );

    assert.deepStrictEqual(fetchedArchiveUrls, [
      'oddsportal://ajax-sport-country-tournament-archive_/1/KKay4EE8/X262144/1/0/?_=1'
    ]);
    assert.strictEqual(result.sourceState, 'CURRENT_RESULTS_ARCHIVE');
    assert.strictEqual(result.totalCandidates, 1);
    assert.strictEqual(result.matches[0].hash, 'archive-hash');
  });

  it('当前赛季 results 页 archive 返回空时，应继续用修复后的 archive URL 反推 current tournament 接口', async () => {
    const fetchArchiveCalls = [];
    const fetchTournamentCalls = [];

    const navigator = new ReconNavigator({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    navigator.browser = { isConnected: () => true };
    navigator.context = {};
    navigator.page = {
      isClosed: () => false,
      async waitForTimeout() {},
      async evaluate(fn, payload) {
        if (payload && payload.leaguePathPrefix) {
          return [];
        }

        if (typeof fn === 'function') {
          return {
            id: 'KKay4EE8',
            sid: 1,
            cid: 198,
            archive: true
          };
        }

        return null;
      }
    };
    navigator.navigate = async () => {
      navigator.apiEndpoints = new Set([
        'oddsportal://ajax-sport-country-tournament-archive_/1//X262144/1/0/?_=1'
      ]);
    };
    navigator._fetchAndDecrypt = async (url) => {
      fetchArchiveCalls.push(url);
      return {
        matches: [],
        pagesScanned: 1,
        totalCandidates: 0,
        pageStats: [{ page: 1, rows: 0, total: 0 }]
      };
    };
    navigator._getCurrentTournamentEndpoint = () => null;
    navigator._fetchCurrentTournament = async (url) => {
      fetchTournamentCalls.push(url);
      return {
        matches: [
          {
            hash: 'archive-fallback-current',
            url: 'oddsportal://match/archive-fallback-current',
            homeTeam: 'Vissel Kobe',
            awayTeam: 'Kyoto Sanga FC',
            matchDate: '2026-02-21T05:00:00.000Z'
          }
        ],
        pagesScanned: 1,
        totalCandidates: 1,
        pageStats: [{ page: 1, rows: 1, newRows: 1, total: 1 }]
      };
    };

    const result = await navigator.protocolArchiveExtract(
      'oddsportal://root/football/japan/j1-league-2026/results/',
      { preferCurrentSeasonSource: true, maxPages: 8, timeoutMs: 1234 }
    );

    assert.deepStrictEqual(fetchArchiveCalls, [
      'oddsportal://ajax-sport-country-tournament-archive_/1/KKay4EE8/X262144/1/0/?_=1'
    ]);
    assert.deepStrictEqual(fetchTournamentCalls, [
      'oddsportal://ajax-sport-country-tournament_/1/KKay4EE8/X262144/1/'
    ]);
    assert.strictEqual(result.sourceState, 'CURRENT_RESULTS_TOURNAMENT');
    assert.strictEqual(result.totalCandidates, 1);
    assert.strictEqual(result.matches[0].hash, 'archive-fallback-current');
  });

  it('archive 拦截为空时应从 performance 资源条目补抓 archive endpoint', async () => {
    const fetchedArchiveUrls = [];

    const navigator = new ReconNavigator({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    navigator.browser = { isConnected: () => true };
    navigator.context = {};
    navigator.page = {
      isClosed: () => false,
      async waitForTimeout() {},
      async evaluate(fn, payload) {
        if (payload && payload.leaguePathPrefix) {
          return [];
        }

        const source = typeof fn === 'function' ? fn.toString() : '';
        if (source.includes("performance.getEntriesByType('resource')")) {
          return [
            'oddsportal://ajax-sport-country-tournament-archive_/1/U1ymuRr3/X262144/1/0/?_=1'
          ];
        }

        return null;
      }
    };
    navigator.navigate = async () => {
      navigator.apiEndpoints = new Set();
    };
    navigator._fetchAndDecrypt = async (url) => {
      fetchedArchiveUrls.push(url);
      return {
        matches: [
          {
            hash: 'resource-probe-hit',
            url: 'oddsportal://match/resource-probe-hit',
            homeTeam: 'Leeds United',
            awayTeam: 'Southampton',
            matchDate: '2025-08-09T11:30:00.000Z'
          }
        ],
        pagesScanned: 1,
        totalCandidates: 1,
        pageStats: [{ page: 1, rows: 1, newRows: 1, total: 1 }]
      };
    };

    const result = await navigator.protocolArchiveExtract(
      'oddsportal://root/football/england/championship-2025-2026/results/',
      { maxPages: 8, timeoutMs: 1234 }
    );

    assert.deepStrictEqual(fetchedArchiveUrls, [
      'oddsportal://ajax-sport-country-tournament-archive_/1/U1ymuRr3/X262144/1/0/?_=1'
    ]);
    assert.strictEqual(result.totalCandidates, 1);
    assert.strictEqual(result.matches[0].hash, 'resource-probe-hit');
  });

  it('当前赛季联赛主页缺失显式 tournament 接口时，应根据修复后的 archive URL 反推 current tournament 接口', async () => {
    const fetchCalls = [];

    const navigator = new ReconNavigator({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    navigator.browser = { isConnected: () => true };
    navigator.context = {};
    navigator.page = {
      isClosed: () => false,
      async waitForTimeout() {},
      async evaluate(fn, payload) {
        if (payload && payload.leaguePathPrefix) {
          return [];
        }

        if (typeof fn === 'function') {
          return '5fdb38ad-528a-4fb9-a576-b8c42e07565d';
        }

        return null;
      },
      async content() {
        return [
          '<html><body>',
          '<script>',
          "pageOutrightsVar = '{\"id\":\"\",\"sid\":1,\"cid\":100,\"archive\":true}';",
          '</script>',
          '</body></html>'
        ].join('');
      }
    };
    navigator.navigate = async (url) => {
      if (url.endsWith('/results/')) {
        navigator.apiEndpoints = new Set();
        return;
      }

      navigator.apiEndpoints = new Set([
        'oddsportal://ajax-sport-country-tournament-archive_/1//X262144/1/0/?_=1'
      ]);
    };
    navigator._getCurrentTournamentEndpoint = () => null;
    navigator._fetchCurrentTournament = async (url, maxPages, timeoutMs) => {
      fetchCalls.push({ url, maxPages, timeoutMs });
      return {
        matches: [
          {
            hash: 'otcode-current',
            url: 'oddsportal://match/otcode-current',
            homeTeam: 'Machida Zelvia',
            awayTeam: 'FC Tokyo',
            matchDate: '2026-02-14T05:00:00.000Z'
          }
        ],
        pagesScanned: 1,
        totalCandidates: 1,
        pageStats: [{ page: 1, rows: 1, newRows: 1, total: 1 }]
      };
    };

    const result = await navigator.protocolArchiveExtract(
      'oddsportal://root/football/japan/j1-league-2026/results/',
      { preferCurrentSeasonSource: true, maxPages: 7, timeoutMs: 1234 }
    );

    assert.deepStrictEqual(fetchCalls, [
      {
        url: 'oddsportal://ajax-sport-country-tournament_/1/5fdb38ad-528a-4fb9-a576-b8c42e07565d/X262144/1/',
        maxPages: 7,
        timeoutMs: 1234
      }
    ]);
    assert.strictEqual(result.sourceState, 'CURRENT_TOURNAMENT');
    assert.strictEqual(result.totalCandidates, 1);
    assert.strictEqual(result.matches[0].hash, 'otcode-current');
  });

  it('forcePureProtocol 在当前赛季 archive 空源时应继续回落到 current tournament 接口', async () => {
    const navigatedUrls = [];
    const fetchCalls = [];

    const navigator = new ReconNavigator({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    navigator.browser = { isConnected: () => true };
    navigator.context = {};
    navigator.page = {
      isClosed: () => false,
      url() {
        return navigatedUrls[navigatedUrls.length - 1] || 'oddsportal://root/football/japan/j1-league/';
      },
      async waitForTimeout() {},
      async content() {
        return [
          '<html><body>',
          '<tournament-component :sport-data="{&quot;oddsRequest&quot;:{&quot;url&quot;:&quot;/ajax-sport-country-tournament_/1/lv6akwBC/X262144/1/?_=1775367493&quot;}}"></tournament-component>',
          '</body></html>'
        ].join('');
      }
    };
    navigator.navigate = async (url) => {
      navigatedUrls.push(url);
      navigator.apiEndpoints = new Set();
    };
    navigator._extractViaPureProtocol = async () => ({
      matches: [],
      pagesScanned: 1,
      totalCandidates: 0,
      pageStats: [{ page: 1, rows: 0, source: 'pure_protocol_archive:empty' }],
      sourceState: 'SOURCE_EMPTY'
    });
    navigator._fetchCurrentTournament = async (url, maxPages, timeoutMs) => {
      fetchCalls.push({ url, maxPages, timeoutMs });
      return {
        matches: [
          {
            hash: 'current-fallback-hash',
            url: 'oddsportal://match/current-fallback-hash',
            homeTeam: 'Kawasaki Frontale',
            awayTeam: 'Urawa Reds',
            matchDate: '2026-02-14T05:00:00.000Z'
          }
        ],
        pagesScanned: 1,
        totalCandidates: 1,
        pageStats: [{ page: 1, rows: 1, newRows: 1, total: 1 }]
      };
    };

    const result = await navigator.protocolArchiveExtract(
      'oddsportal://root/football/japan/j1-league-2026/results/',
      {
        forcePureProtocol: true,
        preferCurrentSeasonSource: true,
        maxPages: 7,
        timeoutMs: 1234
      }
    );

    assert.deepStrictEqual(navigatedUrls, [
      'oddsportal://root/football/japan/j1-league-2026/'
    ]);
    assert.deepStrictEqual(fetchCalls, [
      {
        url: 'oddsportal://root/ajax-sport-country-tournament_/1/lv6akwBC/X262144/1/?_=1775367493',
        maxPages: 7,
        timeoutMs: 1234
      }
    ]);
    assert.strictEqual(result.sourceState, 'CURRENT_TOURNAMENT_FALLBACK');
    assert.strictEqual(result.totalCandidates, 1);
    assert.strictEqual(result.matches[0].hash, 'current-fallback-hash');
  });

  it('非当前赛季 archive URL 缺少 tournament id 时，应切到联赛主页补全后再抓取', async () => {
    const navigatedUrls = [];
    const fetchedArchiveUrls = [];
    const resultsUrl = 'oddsportal://root/football/portugal/primeira-liga-2025-2026/results/';
    const leagueUrl = 'oddsportal://root/football/portugal/primeira-liga/';

    const navigator = new ReconNavigator({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    navigator.browser = { isConnected: () => true };
    navigator.context = {};
    navigator.page = {
      isClosed: () => false,
      async waitForTimeout() {}
    };
    navigator.navigate = async (url) => {
      navigatedUrls.push(url);
      if (url === resultsUrl) {
        navigator.apiEndpoints = new Set([
          'oddsportal://ajax-sport-country-tournament-archive_/1//X262144/1/0/?_=1'
        ]);
        return;
      }

      if (url === leagueUrl) {
        navigator.apiEndpoints = new Set();
      }
    };
    navigator.stateProber.extractPageOutrightsMeta = async () => ({
      id: 'U1ymuRr3',
      sid: 1,
      cid: 155,
      archive: false
    });
    navigator._fetchAndDecryptWithOptions = async (url) => {
      fetchedArchiveUrls.push(url);
      return {
        matches: [
          {
            hash: 'archive-fixed',
            url: 'oddsportal://match/archive-fixed',
            homeTeam: 'Sporting CP',
            awayTeam: 'Benfica',
            matchDate: '2025-08-10T19:00:00.000Z'
          }
        ],
        pagesScanned: 1,
        totalCandidates: 1,
        pageStats: [{ page: 1, rows: 1, newRows: 1, total: 1 }]
      };
    };

    const result = await navigator.protocolArchiveExtract(resultsUrl, {
      maxPages: 8,
      timeoutMs: 1234
    });

    assert.deepStrictEqual(navigatedUrls, [resultsUrl, leagueUrl]);
    assert.deepStrictEqual(fetchedArchiveUrls, [
      'oddsportal://ajax-sport-country-tournament-archive_/1/U1ymuRr3/X262144/1/0/?_=1'
    ]);
    assert.strictEqual(result.totalCandidates, 1);
    assert.strictEqual(result.matches[0].hash, 'archive-fixed');
  });

  it('archive 解密失败时应 relaunch 浏览器并重试一次', async () => {
    let fetchCalls = 0;
    let closeCalls = 0;
    let launchCalls = 0;
    const navigatedUrls = [];

    const navigator = new ReconNavigator({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    navigator.close = async () => {
      closeCalls++;
    };
    navigator.launch = async () => {
      launchCalls++;
      navigator.page = {
        isClosed: () => false,
        async waitForTimeout() {}
      };
      return navigator.page;
    };
    navigator.navigate = async (url) => {
      navigatedUrls.push(url);
    };
    navigator.page = {
      isClosed: () => false,
      async waitForTimeout() {}
    };
    navigator.networkMonitor.fetchArchivePages = async () => {
      fetchCalls++;
      if (fetchCalls === 1) {
        return {
          matches: [],
          pagesScanned: 1,
          totalCandidates: 0,
          pageStats: [{ page: 1, rows: 0, error: 'decrypt_failed:Failed to extract decryptor from any source' }]
        };
      }

      return {
        matches: [
          {
            hash: 'after-relaunch',
            url: 'oddsportal://match/after-relaunch',
            homeTeam: 'A',
            awayTeam: 'B',
            matchDate: '2025-08-12T18:00:00.000Z'
          }
        ],
        pagesScanned: 1,
        totalCandidates: 1,
        pageStats: [{ page: 1, rows: 1, newRows: 1, total: 1 }]
      };
    };

    const result = await navigator._fetchAndDecryptWithOptions(
      'oddsportal://ajax-sport-country-tournament-archive_/1/U1ymuRr3/X262144/1/0/?_=1',
      1,
      90000,
      { warmUrl: 'oddsportal://root/football/portugal/primeira-liga-2025-2026/results/' }
    );

    assert.strictEqual(closeCalls, 1);
    assert.strictEqual(launchCalls, 1);
    assert.deepStrictEqual(navigatedUrls, [
      'oddsportal://root/football/portugal/primeira-liga-2025-2026/results/'
    ]);
    assert.strictEqual(result.totalCandidates, 1);
    assert.strictEqual(result.matches[0].hash, 'after-relaunch');
    assert.strictEqual(result.retriedAfterRelaunch, true);
  });

  it('浏览器上下文丢失时，ensureBrowserHealthy 应自动重启并恢复 page', async () => {
    let launchCount = 0;

    function navigatorLaunchStub() {
      launchCount++;
      this.browser = { isConnected: () => true, close: async () => {} };
      this.context = { close: async () => {} };
      this.page = {
        isClosed: () => false,
        addInitScript: async () => {},
        on() {},
        goto: async () => {},
        waitForTimeout: async () => {},
        evaluate: async () => {}
      };
      this.isClosed = false;
      return this.page;
    }

    const navigator = new ReconNavigator({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    navigator.launch = navigatorLaunchStub;
    await navigator.launch();
    navigator.browser = null;
    navigator.context = null;
    navigator.page = null;
    navigator.isClosed = true;

    await navigator.ensureBrowserHealthy();

    assert.strictEqual(launchCount, 2);
    assert.ok(navigator.page);
    assert.strictEqual(navigator.isClosed, false);
  });

  it('fetchFullSeasonArchive 应识别 results 分页并聚合每页拦截结果', async () => {
    const baseUrl = 'oddsportal://root/football/england/championship-2025-2026/results/';
    const page2Url = 'oddsportal://root/football/england/championship-2025-2026/results/page/2/';
    const page3Url = 'oddsportal://root/football/england/championship-2025-2026/results/page/3/';
    const navigatedUrls = [];
    const pageMatches = {
      [baseUrl]: [
        {
          hash: 'page-1',
          url: 'oddsportal://match/page-1',
          homeTeam: 'Leeds United',
          awayTeam: 'Burnley',
          matchDate: '2025-08-12T19:00:00.000Z'
        }
      ],
      [page2Url]: [
        {
          hash: 'page-2',
          url: 'oddsportal://match/page-2',
          homeTeam: 'Sunderland',
          awayTeam: 'Coventry',
          matchDate: '2025-08-13T19:00:00.000Z'
        }
      ],
      [page3Url]: [
        {
          hash: 'page-3',
          url: 'oddsportal://match/page-3',
          homeTeam: 'Norwich',
          awayTeam: 'Watford',
          matchDate: '2025-08-14T19:00:00.000Z'
        }
      ]
    };

    const navigator = new ReconNavigator({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    navigator.browser = { isConnected: () => true };
    navigator.context = {};
    navigator.page = {
      isClosed: () => false,
      async waitForTimeout() {},
      async evaluate(_fn, currentResultsUrl) {
        return {
          pageUrls: [
            `${currentResultsUrl}page/2/`
          ],
          totalPages: 3
        };
      }
    };
    navigator.navigate = async (url) => {
      navigatedUrls.push(url);
      navigator.interceptedData = pageMatches[url] || [];
      navigator.apiEndpoints = new Set([
        `oddsportal://ajax/${navigatedUrls.length}`
      ]);
    };
    navigator.protocolArchiveExtract = async () => ({
      matches: [],
      pagesScanned: 0,
      totalCandidates: 0,
      pageStats: [],
      sourceState: 'SOURCE_EMPTY'
    });

    const result = await navigator.fetchFullSeasonArchive(baseUrl, {
      maxPages: 10,
      timeoutMs: 1234
    });

    assert.deepStrictEqual(navigatedUrls, [baseUrl, page2Url, page3Url]);
    assert.deepStrictEqual(result.pageUrls, [baseUrl, page2Url, page3Url]);
    assert.strictEqual(result.sourceState, 'FULL_SEASON_SWEEP');
    assert.strictEqual(result.totalCandidates, 3);
    assert.deepStrictEqual(
      result.matches.map((item) => item.hash),
      ['page-1', 'page-2', 'page-3']
    );
  });

  it('fetchFullSeasonArchive 在英冠 sweep 与 archive 为空时，应走 current season 补救链路', async () => {
    const baseUrl = 'oddsportal://root/football/england/championship-2025-2026/results/';
    const navigator = new ReconNavigator({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    navigator.browser = { isConnected: () => true };
    navigator.context = {};
    navigator.page = {
      isClosed: () => false,
      async waitForTimeout() {}
    };

    navigator.domScraper.discoverSeasonResultPages = async () => ({
      pageUrls: [baseUrl],
      initialMatches: [],
      initialSource: 'page_dom'
    });
    navigator.protocolArchiveExtract = async () => ({
      matches: [],
      pagesScanned: 0,
      totalCandidates: 0,
      pageStats: [],
      sourceState: 'SOURCE_EMPTY'
    });

    let probedBaseUrl = null;
    navigator.stateProber.probeCurrentSeasonFromPageState = async (inputBaseUrl) => {
      probedBaseUrl = inputBaseUrl;
      return {
        matches: [
          {
            hash: 'championship-recovery',
            url: 'oddsportal://match/championship-recovery',
            homeTeam: 'Sheffield United',
            awayTeam: 'Middlesbrough',
            matchDate: '2025-08-15T19:00:00.000Z'
          }
        ],
        pagesScanned: 1,
        totalCandidates: 1,
        pageStats: [
          {
            page: 1,
            rows: 1,
            newRows: 1,
            total: 1,
            source: 'CURRENT_RESULTS_ARCHIVE'
          }
        ],
        sourceState: 'CURRENT_RESULTS_ARCHIVE'
      };
    };

    const result = await navigator.fetchFullSeasonArchive(baseUrl, {
      maxPages: 10,
      timeoutMs: 1234,
      preferCurrentSeasonSource: true
    });

    assert.strictEqual(probedBaseUrl, baseUrl);
    assert.strictEqual(result.totalCandidates, 1);
    assert.strictEqual(result.matches[0].hash, 'championship-recovery');
    assert.strictEqual(result.pageStats.at(-1).source, 'CURRENT_RESULTS_ARCHIVE');
  });

  it('fetchFullSeasonArchive 在当前赛季结果候选过少时，应补跑 current season 补救链路', async () => {
    const baseUrl = 'oddsportal://root/football/japan/j2-league/results/';
    const navigator = new ReconNavigator({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    navigator.browser = { isConnected: () => true };
    navigator.context = {};
    navigator.page = {
      isClosed: () => false,
      async waitForTimeout() {}
    };

    navigator.domScraper.discoverSeasonResultPages = async () => ({
      pageUrls: [baseUrl],
      initialMatches: [
        {
          hash: 'dom-1',
          url: 'oddsportal://match/dom-1',
          homeTeam: 'Vegalta Sendai',
          awayTeam: 'Mito HollyHock',
          matchDate: '2025-08-15T10:00:00.000Z'
        },
        {
          hash: 'dom-2',
          url: 'oddsportal://match/dom-2',
          homeTeam: 'Oita Trinita',
          awayTeam: 'Montedio Yamagata',
          matchDate: '2025-08-16T10:00:00.000Z'
        }
      ],
      initialSource: 'page_dom'
    });
    navigator.protocolArchiveExtract = async () => ({
      matches: [],
      pagesScanned: 0,
      totalCandidates: 0,
      pageStats: [],
      sourceState: 'SOURCE_EMPTY'
    });

    let probedBaseUrl = null;
    navigator.stateProber.probeCurrentSeasonFromPageState = async (inputBaseUrl) => {
      probedBaseUrl = inputBaseUrl;
      return {
        matches: [
          {
            hash: 'state-1',
            url: 'oddsportal://match/state-1',
            homeTeam: 'Jubilo Iwata',
            awayTeam: 'Sagan Tosu',
            matchDate: '2025-08-17T10:00:00.000Z'
          },
          {
            hash: 'state-2',
            url: 'oddsportal://match/state-2',
            homeTeam: 'Ventforet Kofu',
            awayTeam: 'Ehime',
            matchDate: '2025-08-18T10:00:00.000Z'
          }
        ],
        pagesScanned: 1,
        totalCandidates: 2,
        pageStats: [
          {
            page: 1,
            rows: 2,
            newRows: 2,
            total: 4,
            source: 'CURRENT_RESULTS_ARCHIVE'
          }
        ],
        sourceState: 'CURRENT_RESULTS_ARCHIVE'
      };
    };

    const result = await navigator.fetchFullSeasonArchive(baseUrl, {
      maxPages: 10,
      timeoutMs: 1234,
      preferCurrentSeasonSource: true,
      minCandidatesForStateProbe: 3
    });

    assert.strictEqual(probedBaseUrl, baseUrl);
    assert.strictEqual(result.totalCandidates, 4);
    assert.deepStrictEqual(
      result.matches.map((item) => item.hash),
      ['dom-1', 'dom-2', 'state-1', 'state-2']
    );
    assert.strictEqual(result.pageStats.at(-1).source, 'CURRENT_RESULTS_ARCHIVE');
  });

  it('fetchFullSeasonArchive 在 forceDomOnly=true 时不得回落到 protocolArchiveExtract', async () => {
    const baseUrl = 'oddsportal://root/football/japan/j1-league-2026/results/';
    const navigator = new ReconNavigator({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    navigator.browser = { isConnected: () => true };
    navigator.context = {};
    navigator.page = {
      isClosed: () => false,
      async waitForTimeout() {}
    };

    navigator.domScraper.discoverSeasonResultPages = async () => ({
      pageUrls: [baseUrl],
      initialMatches: [],
      initialSource: 'page_dom'
    });
    navigator.protocolArchiveExtract = async () => {
      throw new Error('should_not_call_protocol_archive');
    };
    navigator.stateProber.probeCurrentSeasonFromPageState = async () => {
      throw new Error('should_not_probe_current_season');
    };

    const result = await navigator.fetchFullSeasonArchive(baseUrl, {
      maxPages: 10,
      timeoutMs: 1234,
      preferCurrentSeasonSource: true,
      forceDomOnly: true
    });

    assert.strictEqual(result.totalCandidates, 0);
    assert.strictEqual(result.sourceState, 'SOURCE_EMPTY');
  });

  it('navigate 的熔断应按联赛 key 隔离，不得污染其他目标', async () => {
    const navigator = new ReconNavigator({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    navigator.browser = { isConnected: () => true };
    navigator.context = {};
    navigator.page = { isClosed: () => false };
    navigator.circuitBreakerPool = new ReconCircuitBreakerPool({
      failureThreshold: 1,
      resetTimeout: 60_000,
      logger: { info() {}, warn() {}, error() {} }
    });
    navigator.browserContext.navigate = async (_url, options) => {
      if (options.contentReadySelector === 'fail') {
        throw new Error('Navigation timeout');
      }
      return true;
    };

    await assert.rejects(
      () => navigator.navigate('oddsportal://timeout-1', {
        timeout: 10,
        circuitBreakerKey: 'league:epl',
        contentReadySelector: 'fail'
      }),
      /Navigation timeout/
    );
    await assert.doesNotReject(
      () => navigator.navigate('oddsportal://timeout-mls', {
        timeout: 10,
        circuitBreakerKey: 'league:mls'
      })
    );
    await assert.rejects(
      () => navigator.navigate('oddsportal://timeout-2', {
        timeout: 10,
        circuitBreakerKey: 'league:epl',
        contentReadySelector: 'fail'
      }),
      /Circuit breaker is OPEN/
    );
  });

  it('navigate 遇到 503 时应按 [5s,15s,30s] 退避重试后再成功', async () => {
    const navigator = new ReconNavigator({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    navigator.browser = { isConnected: () => true };
    navigator.context = {};
    navigator.page = {
      isClosed: () => false,
      async waitForTimeout() {}
    };
    const retryDelays = [];
    let attempts = 0;
    navigator._waitBeforeRetry = async (delayMs) => {
      retryDelays.push(delayMs);
    };
    navigator.browserContext.navigate = async () => {
      attempts += 1;
      if (attempts < 3) {
        const error = new Error('page.goto: net::ERR_HTTP_RESPONSE_CODE_FAILURE');
        error.statusCode = 503;
        error.retryAfterMs = 1000;
        throw error;
      }
      return true;
    };

    await assert.doesNotReject(
      () => navigator.navigate('oddsportal://epl-results', {
        timeout: 100,
        circuitBreakerKey: 'league:epl'
      })
    );

    assert.strictEqual(attempts, 3);
    assert.deepStrictEqual(retryDelays, [5000, 15000]);
  });

  it('navigate 遇到 503 时应先报告代理失败并 rotate 后再 relaunch', async () => {
    const reportedFailures = [];
    const rotated = [];
    const launchedProxyPorts = [];

    const navigator = new ReconNavigator({
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      proxy: { host: 'proxy-a', port: 3101, url: 'http://proxy-a:3101', server: 'http://proxy-a:3101' },
      proxyRotator: {
        reportFailure(port, errorType) {
          reportedFailures.push({ port, errorType });
        },
        rotate() {
          rotated.push(true);
          return {
            host: 'proxy-b',
            port: 3102,
            url: 'http://proxy-b:3102',
            server: 'http://proxy-b:3102'
          };
        }
      }
    });

    navigator.browser = { isConnected: () => true };
    navigator.context = {};
    navigator.page = {
      isClosed: () => false,
      async waitForTimeout() {}
    };
    navigator.browserContext.proxy = navigator.proxy;

    const retryDelays = [];
    let attempts = 0;
    navigator._waitBeforeRetry = async (delayMs) => {
      retryDelays.push(delayMs);
    };
    navigator.close = async () => {};
    navigator.launch = async (options = {}) => {
      launchedProxyPorts.push(options.proxy?.port || null);
      navigator.browser = { isConnected: () => true };
      navigator.context = {};
      navigator.page = {
        isClosed: () => false,
        async waitForTimeout() {}
      };
      return navigator.page;
    };
    navigator.browserContext.navigate = async () => {
      attempts += 1;
      if (attempts === 1) {
        const error = new Error('page.goto: net::ERR_HTTP_RESPONSE_CODE_FAILURE');
        error.statusCode = 503;
        throw error;
      }
      return true;
    };

    await assert.doesNotReject(
      () => navigator.navigate('oddsportal://epl-results', {
        timeout: 100,
        circuitBreakerKey: 'league:epl'
      })
    );

    assert.deepStrictEqual(reportedFailures, [{ port: 3101, errorType: '503' }]);
    assert.strictEqual(rotated.length, 1);
    assert.deepStrictEqual(launchedProxyPorts, [3102]);
    assert.strictEqual(navigator.proxy.port, 3102);
    assert.deepStrictEqual(retryDelays, [5000]);
  });

  it('_fetchAndDecrypt 遇到 HTTP_503 时应自动退避重试', async () => {
    const navigator = new ReconNavigator({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    navigator.browser = { isConnected: () => true };
    navigator.context = {};
    navigator.page = { isClosed: () => false };
    const retryDelays = [];
    let attempts = 0;
    navigator._waitBeforeRetry = async (delayMs) => {
      retryDelays.push(delayMs);
    };
    navigator.networkMonitor.fetchArchivePages = async () => {
      attempts += 1;
      if (attempts === 1) {
        return {
          matches: [],
          pagesScanned: 1,
          totalCandidates: 0,
          pageStats: [{
            page: 1,
            rows: 0,
            error: 'HTTP_503',
            statusCode: 503,
            retryAfterRaw: '2',
            retryAfterMs: 2000
          }],
          httpFailure: {
            page: 1,
            url: 'oddsportal://archive/page/1',
            error: 'HTTP_503',
            statusCode: 503,
            retryAfterRaw: '2',
            retryAfterMs: 2000
          }
        };
      }

      return {
        matches: [{
          hash: 'retry-hash',
          url: 'oddsportal://match/retry-hash',
          homeTeam: 'A',
          awayTeam: 'B',
          matchDate: '2025-08-15T19:00:00.000Z'
        }],
        pagesScanned: 1,
        totalCandidates: 1,
        pageStats: [{ page: 1, rows: 1, newRows: 1, total: 1 }]
      };
    };

    const result = await navigator._fetchAndDecrypt(
      'oddsportal://archive',
      1,
      100,
      { circuitBreakerKey: 'league:epl' }
    );

    assert.strictEqual(result.totalCandidates, 1);
    assert.strictEqual(attempts, 2);
    assert.deepStrictEqual(retryDelays, [5000]);
  });
});
