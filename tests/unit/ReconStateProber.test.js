'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { ReconStateProber } = require('../../src/infrastructure/recon/services/ReconStateProber');

describe('ReconStateProber', () => {
  it('应从 pageOutrightsVar 脚本字符串中提取 tournamentId', () => {
    const prober = new ReconStateProber({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    const html = [
      '<html><body>',
      '<script>',
      "window.pageOutrightsVar = '{\"id\":\"KKay4EE8\",\"sid\":1,\"cid\":198,\"archive\":true}';",
      '</script>',
      '</body></html>'
    ].join('');

    const meta = prober.extractPageOutrightsMetaFromHtml(html);

    assert.deepStrictEqual(meta, {
      id: 'KKay4EE8',
      sid: 1,
      cid: 198,
      archive: true
    });
  });

  it('应使用提取出的 tournamentId 修复缺失 id 的 archive endpoint', async () => {
    const prober = new ReconStateProber({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    prober.setPage({
      async content() {
        return [
          '<html><body>',
          '<script>',
          "pageOutrightsVar = '{\"id\":\"KKay4EE8\",\"sid\":1,\"cid\":198}';",
          '</script>',
          '</body></html>'
        ].join('');
      }
    });

    const repaired = await prober.resolveCurrentSeasonArchiveEndpoint([
      'https://www.oddsportal.com/ajax-sport-country-tournament-archive_/1//X262144/1/0/?_=1'
    ], {
      scoreArchiveUrl(url) {
        return url.includes('/1//X') ? 1 : 10;
      }
    });

    assert.strictEqual(
      repaired,
      'https://www.oddsportal.com/ajax-sport-country-tournament-archive_/1/KKay4EE8/X262144/1/0/?_=1'
    );
  });

  it('缺失 outright id 时应回退到 pageVar.otCode 修复 archive endpoint', async () => {
    const prober = new ReconStateProber({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    prober.setPage({
      async content() {
        return [
          '<html><body>',
          '<script>',
          "pageOutrightsVar = '{\"id\":\"\",\"sid\":1,\"cid\":100,\"archive\":true}';",
          '</script>',
          '</body></html>'
        ].join('');
      },
      async evaluate() {
        return '5fdb38ad-528a-4fb9-a576-b8c42e07565d';
      }
    });

    const repaired = await prober.resolveCurrentSeasonArchiveEndpoint([
      'https://www.oddsportal.com/ajax-sport-country-tournament-archive_/1//X262144/1/0/?_=1'
    ], {
      scoreArchiveUrl(url) {
        return url.includes('/1//X') ? 1 : 10;
      }
    });

    assert.strictEqual(
      repaired,
      'https://www.oddsportal.com/ajax-sport-country-tournament-archive_/1/5fdb38ad-528a-4fb9-a576-b8c42e07565d/X262144/1/0/?_=1'
    );
  });

  it('extractTournamentToken 应记录 token 缺失阶段日志', async () => {
    const logs = [];
    const prober = new ReconStateProber({
      logger: {
        info() {},
        error() {},
        debug(event, payload) {
          logs.push({ level: 'debug', event, payload });
        },
        warn(event, payload) {
          logs.push({ level: 'warn', event, payload });
        }
      }
    });

    prober.setPage({
      async content() {
        return [
          '<html><body>',
          '<script>',
          "pageOutrightsVar = '{\"id\":\"\",\"sid\":1,\"cid\":100,\"archive\":true}';",
          '</script>',
          '</body></html>'
        ].join('');
      },
      async evaluate() {
        return '';
      }
    });

    const token = await prober.extractTournamentToken();

    assert.strictEqual(token, '');
    assert.ok(logs.some((entry) => entry.event === 'recon_tournament_token_page_outrights_missing'));
    assert.ok(logs.some((entry) => entry.event === 'recon_tournament_token_otcode_missing'));
  });

  it('seasonless results URL 应能反推出联赛主页 URL', () => {
    const prober = new ReconStateProber({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    assert.strictEqual(
      prober.deriveLeaguePageUrl('https://www.oddsportal.com/football/brazil/serie-a/results/'),
      'https://www.oddsportal.com/football/brazil/serie-a/'
    );
  });

  it('probeCurrentSeasonFromPageState 应优先返回已拦截的 current season 数据', async () => {
    const prober = new ReconStateProber({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    const intercepted = [{
      hash: 'championship-live-1',
      url: 'https://www.oddsportal.com/football/england/championship-2025-2026/a-b-championship-live-1/',
      homeTeam: 'Leeds United',
      awayTeam: 'Burnley',
      matchDate: '2026-01-01T00:00:00.000Z'
    }];

    const result = await prober.probeCurrentSeasonFromPageState(
      'https://www.oddsportal.com/football/england/championship-2025-2026/results/',
      {},
      {
        async navigate() {},
        async waitForTimeout() {},
        getInterceptedData() {
          return intercepted;
        },
        getApiEndpoints() {
          return [];
        }
      }
    );

    assert.strictEqual(result.sourceState, 'CURRENT_RESULTS_INTERCEPT');
    assert.strictEqual(result.totalCandidates, 1);
    assert.strictEqual(result.matches[0].hash, 'championship-live-1');
  });

  it('results 页为空时应优先使用联赛页 DOM 结果而不是继续请求 current tournament API', async () => {
    const prober = new ReconStateProber({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });
    prober._awaitInterceptedData = async () => [];

    const navigatedUrls = [];
    let tournamentFetchCalled = false;

    const result = await prober.probeCurrentSeasonFromPageState(
      'https://www.oddsportal.com/football/usa/mls-2025-2026/results/',
      {},
      {
        async navigate(url) {
          navigatedUrls.push(url);
        },
        async waitForTimeout() {},
        getInterceptedData() {
          return [];
        },
        getApiEndpoints() {
          return [];
        },
        async collectCurrentSeasonResultsDom(url) {
          if (url.endsWith('/results/')) {
            return { matches: [], totalCandidates: 0, pagesScanned: 1, pageStats: [] };
          }

          return {
            matches: [{
              hash: 'mls-dom-hash',
              url: 'https://www.oddsportal.com/football/h2h/inter-miami-fc-los-angeles-fc/#mls-dom-hash'
            }],
            totalCandidates: 1,
            pagesScanned: 1,
            pageStats: [{ page: 1, rows: 1, newRows: 1, total: 1 }]
          };
        },
        async fetchCurrentTournament() {
          tournamentFetchCalled = true;
          throw new Error('should_not_fetch_current_tournament_when_league_dom_ready');
        }
      }
    );

    assert.deepStrictEqual(navigatedUrls, [
      'https://www.oddsportal.com/football/usa/mls/results/',
      'https://www.oddsportal.com/football/usa/mls/'
    ]);
    assert.strictEqual(tournamentFetchCalled, false);
    assert.strictEqual(result.sourceState, 'CURRENT_TOURNAMENT_DOM');
    assert.strictEqual(result.matches[0].hash, 'mls-dom-hash');
  });
});
