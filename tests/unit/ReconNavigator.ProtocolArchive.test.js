'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { ReconNavigator } = require('../../src/infrastructure/recon/ReconNavigator');

describe('ReconNavigator - Protocol Archive', () => {
  it('navigate 时应重置跨联赛残留的 apiEndpoints 与 decryptor', async () => {
    const navigator = new ReconNavigator({
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      traceId: 'trace-reset'
    });

    const staleDecryptor = navigator.decryptor;
    navigator.apiEndpoints.add('oddsportal://stale-endpoint');
    navigator.page = {
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

    navigator.page = {
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

    navigator.page = {
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

  it('当前赛季应改走联赛主页的 tournament 接口，而不是 results archive 接口', async () => {
    const navigatedUrls = [];
    const fetchCalls = [];

    const navigator = new ReconNavigator({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    navigator.page = {
      async waitForTimeout() {}
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

    navigator.page = {
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
});
