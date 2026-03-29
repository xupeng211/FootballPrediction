'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { ReconNavigator } = require('../../src/infrastructure/recon/ReconNavigator');
const { ReconCircuitBreaker } = require('../../src/infrastructure/recon/ReconResilience');

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
                encodeEventId: 'retry-hash',
                url: '/football/england/premier-league-2024-2025/a-b-retry-hash/',
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
    assert.strictEqual(result.matches[0].hash, 'retry-hash');
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
      '  pageVar = pageOutrightsVar = Object.assign(pageVar, JSON.parse("{\\"d\\":{\\"total\\":1,\\"rows\\":[{\\"encodeEventId\\":\\"wrapped-hash\\",\\"url\\":\\"/football/europe/champions-league-2025-2026/a-b-wrapped-hash/\\",\\"home-name\\":\\"A\\",\\"away-name\\":\\"B\\",\\"date-start-timestamp\\":1748185200}]}}"));',
      '}'
    ].join(' ');

    const matches = await navigator._parseApiResponse(
      wrappedBody,
      'https://www.oddsportal.com/ajax-user-data/t/champions-league-2025-2026/'
    );

    assert.strictEqual(extractCalls, 0);
    assert.strictEqual(decryptCalls, 0);
    assert.strictEqual(matches.length, 1);
    assert.strictEqual(matches[0].hash, 'wrapped-hash');
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

  it('navigate 连续 timeout 时应触发熔断，第二次请求直接被拒绝', async () => {
    const navigator = new ReconNavigator({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    navigator.browser = { isConnected: () => true };
    navigator.context = {};
    navigator.page = { isClosed: () => false };
    navigator.circuitBreaker = new ReconCircuitBreaker({
      failureThreshold: 1,
      resetTimeout: 60_000,
      logger: { info() {}, warn() {}, error() {} }
    });
    navigator.browserContext.navigate = async () => {
      throw new Error('Navigation timeout');
    };

    await assert.rejects(
      () => navigator.navigate('oddsportal://timeout-1', { timeout: 10 }),
      /Navigation timeout/
    );
    await assert.rejects(
      () => navigator.navigate('oddsportal://timeout-2', { timeout: 10 }),
      /Circuit breaker is OPEN/
    );
  });

  it('_fetchAndDecrypt 连续失败时应受熔断器保护', async () => {
    const navigator = new ReconNavigator({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    navigator.browser = { isConnected: () => true };
    navigator.context = {};
    navigator.page = { isClosed: () => false };
    navigator.circuitBreaker = new ReconCircuitBreaker({
      failureThreshold: 1,
      resetTimeout: 60_000,
      logger: { info() {}, warn() {}, error() {} }
    });
    navigator.networkMonitor.fetchArchivePages = async () => {
      throw new Error('503 Service Unavailable');
    };

    await assert.rejects(
      () => navigator._fetchAndDecrypt('oddsportal://archive', 1, 100),
      /503 Service Unavailable/
    );
    await assert.rejects(
      () => navigator._fetchAndDecrypt('oddsportal://archive', 1, 100),
      /Circuit breaker is OPEN/
    );
  });
});
