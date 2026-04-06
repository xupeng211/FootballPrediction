'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { ReconDomScraper } = require('../../src/infrastructure/recon/services/ReconDomScraper');

describe('ReconDomScraper', () => {
  it('应从积分榜 HTML 中提取球队名与 team hash', () => {
    const scraper = new ReconDomScraper({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    const html = [
      '<table class="standings-table">',
      '  <tbody>',
      '    <tr>',
      '      <td class="team-cell"><a href="/football/team/deportivo-la-coruna-Q51ZzMS6/">Dep La Coruna</a></td>',
      '    </tr>',
      '    <tr>',
      '      <td class="team-cell"><a href="/football/team/gijon-69w4Rb2d/">Gijon</a></td>',
      '    </tr>',
      '  </tbody>',
      '</table>'
    ].join('');

    const teams = scraper.extractTeamsFromStandings(html, {
      currentUrl: 'https://www.oddsportal.com/football/spain/segunda-division-2025-2026/standings/'
    });

    assert.deepStrictEqual(teams, [
      {
        teamName: 'Dep La Coruna',
        teamHash: 'Q51ZzMS6',
        teamUrl: 'https://www.oddsportal.com/football/team/deportivo-la-coruna-Q51ZzMS6/',
        source: 'standings_dom'
      },
      {
        teamName: 'Gijon',
        teamHash: '69w4Rb2d',
        teamUrl: 'https://www.oddsportal.com/football/team/gijon-69w4Rb2d/',
        source: 'standings_dom'
      }
    ]);
  });

  it('unsupported standings 壳页不应误提取球队链接', () => {
    const scraper = new ReconDomScraper({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    const html = [
      '<div class="message">We are very sorry but required league is not supported!</div>',
      '<a href="/football/spain/segunda-division-2025-2026/results/">Results</a>'
    ].join('');

    const teams = scraper.extractTeamsFromStandings(html, {
      currentUrl: 'https://www.oddsportal.com/football/spain/segunda-division-2025-2026/standings/'
    });

    assert.deepStrictEqual(teams, []);
  });

  it('应从包含 .eventRow 的结果页 HTML 中提取 homeTeam、awayTeam 与 hash', () => {
    const scraper = new ReconDomScraper({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    const html = [
      '<div class="results">',
      '  <div class="eventRow">',
      '    <a href="/football/england/championship-2025-2026/leeds-united-burnley-AbCd1234/">',
      '      <span class="participant-name eventRow__home" title="Leeds United">Leeds United</span>',
      '      <span class="participant-name eventRow__away" title="Burnley">Burnley</span>',
      '    </a>',
      '  </div>',
      '  <div class="eventRow">',
      '    <a href="/football/england/championship-2025-2026/sunderland-coventry-EfGh5678/">',
      '      <span class="eventRow__home">Sunderland</span>',
      '      <span class="eventRow__away">Coventry</span>',
      '    </a>',
      '  </div>',
      '  <div class="eventRow">',
      '    <a href="/football/england/premier-league-2025-2026/arsenal-chelsea-ZzYy1122/">',
      '      <span class="eventRow__home">Arsenal</span>',
      '      <span class="eventRow__away">Chelsea</span>',
      '    </a>',
      '  </div>',
      '</div>'
    ].join('');

    const matches = scraper.parseCurrentSeasonResultRowsFromHtml(html, {
      currentUrl: 'https://www.oddsportal.com/football/england/championship-2025-2026/results/',
      leaguePathPrefix: '/football/england/championship/'
    });

    assert.strictEqual(matches.length, 2);
    assert.deepStrictEqual(matches.map((item) => ({
      hash: item.hash,
      homeTeam: item.homeTeam,
      awayTeam: item.awayTeam
    })), [
      {
        hash: 'AbCd1234',
        homeTeam: 'Leeds United',
        awayTeam: 'Burnley'
      },
      {
        hash: 'EfGh5678',
        homeTeam: 'Sunderland',
        awayTeam: 'Coventry'
      }
    ]);
  });

  it('应从结果页 HTML 中识别分页锚点并推导完整 pageUrls', () => {
    const scraper = new ReconDomScraper({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    const html = [
      '<nav class="pagination">',
      '  <a href="/football/england/championship-2025-2026/results/">1</a>',
      '  <a href="/football/england/championship-2025-2026/results/page/2/">2</a>',
      '  <a href="/football/england/championship-2025-2026/results/page/4/">4</a>',
      '</nav>'
    ].join('');

    const meta = scraper.extractPaginationMetaFromHtml(
      html,
      'https://www.oddsportal.com/football/england/championship-2025-2026/results/'
    );
    const pageUrls = scraper.normalizeResultsPageUrls(
      'https://www.oddsportal.com/football/england/championship-2025-2026/results/',
      meta.pageUrls,
      meta.totalPages,
      5
    );

    assert.deepStrictEqual(pageUrls, [
      'https://www.oddsportal.com/football/england/championship-2025-2026/results/',
      'https://www.oddsportal.com/football/england/championship-2025-2026/results/page/2/',
      'https://www.oddsportal.com/football/england/championship-2025-2026/results/page/3/',
      'https://www.oddsportal.com/football/england/championship-2025-2026/results/page/4/'
    ]);
  });

  it('应接受 canonical league path 与 resultsUrl 不同的 sponsor alias 页面', () => {
    const scraper = new ReconDomScraper({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    const html = [
      '<html><head>',
      '  <link rel="canonical" href="https://www.oddsportal.com/football/brazil/serie-a-betano/" />',
      '</head><body>',
      '  <div class="eventRow">',
      '    <a href="/football/brazil/serie-a-betano/athletico-pr-botafogo-rj-xUgkXiV8/">',
      '      <span class="eventRow__home">Athletico PR</span>',
      '      <span class="eventRow__away">Botafogo RJ</span>',
      '    </a>',
      '  </div>',
      '</body></html>'
    ].join('');

    const matches = scraper.parseCurrentSeasonResultRowsFromHtml(html, {
      currentUrl: 'https://www.oddsportal.com/football/brazil/serie-a/results/',
      leaguePathPrefix: '/football/brazil/serie-a/'
    });

    assert.strictEqual(matches.length, 1);
    assert.strictEqual(matches[0].hash, 'xUgkXiV8');
    assert.strictEqual(matches[0].homeTeam, 'Athletico PR');
    assert.strictEqual(matches[0].awayTeam, 'Botafogo RJ');
  });

  it('新版 /match/ 链接在 data-testid 缺失时仍应通过 document.links 兜底提取', () => {
    const scraper = new ReconDomScraper({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    const html = [
      '<html><body>',
      '  <main>',
      '    <section>',
      '      <a href="/match/inter-miami-vs-nycfc-mls-2026-001/">Inter Miami vs NYCFC</a>',
      '      <a href="/match/la-galaxy-vs-austin-mls-2026-002/">LA Galaxy - Austin</a>',
      '      <a href="/football/england/premier-league-2025-2026/arsenal-chelsea-ZzYy1122/">Arsenal - Chelsea</a>',
      '    </section>',
      '  </main>',
      '</body></html>'
    ].join('');

    const matches = scraper.parseCurrentSeasonResultRowsFromHtml(html, {
      currentUrl: 'https://www.oddsportal.com/football/usa/mls/results/',
      leaguePathPrefix: '/football/usa/mls/'
    });

    assert.deepStrictEqual(matches.map((item) => ({
      hash: item.hash,
      homeTeam: item.homeTeam,
      awayTeam: item.awayTeam
    })), [
      {
        hash: 'inter-miami-vs-nycfc-mls-2026-001',
        homeTeam: 'Inter Miami',
        awayTeam: 'NYCFC'
      },
      {
        hash: 'la-galaxy-vs-austin-mls-2026-002',
        homeTeam: 'LA Galaxy',
        awayTeam: 'Austin'
      }
    ]);
  });

  it('新版 data-testid 容器中的 h2h 片段链接也应提取 eventId 与队名', () => {
    const scraper = new ReconDomScraper({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    const html = [
      '<html><body>',
      '  <div data-testid="event-row">',
      '    <a href="/football/h2h/kashiwa-reysol-AbCd1234/yokohama-f-marinos-EfGh5678/#QwErTy12">',
      '      <span data-testid="home-team">Kashiwa Reysol</span>',
      '      <span data-testid="away-team">Yokohama F.Marinos</span>',
      '    </a>',
      '  </div>',
      '</body></html>'
    ].join('');

    const matches = scraper.parseCurrentSeasonResultRowsFromHtml(html, {
      currentUrl: 'https://www.oddsportal.com/football/japan/j1-league/results/',
      leaguePathPrefix: '/football/japan/j1-league/'
    });

    assert.deepStrictEqual(matches, [
      {
        url: 'https://www.oddsportal.com/football/h2h/kashiwa-reysol-AbCd1234/yokohama-f-marinos-EfGh5678/#QwErTy12',
        hash: 'QwErTy12',
        homeTeam: 'Kashiwa Reysol',
        awayTeam: 'Yokohama F.Marinos',
        matchDate: null,
        source: 'current_results_dom'
      }
    ]);
  });

  it('应从 __NEXT_DATA__ 脚本中直接提取比赛候选', () => {
    const scraper = new ReconDomScraper({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    const html = [
      '<html><body>',
      '  <script id="__NEXT_DATA__" type="application/json">',
      JSON.stringify({
        props: {
          pageProps: {
            d: {
              rows: [
                {
                  encodeEventId: 'NtDt1234',
                  url: '/football/england/championship-2025-2026/leeds-united-burnley-NtDt1234/',
                  'home-name': 'Leeds United',
                  'away-name': 'Burnley',
                  'date-start-timestamp': 1767225600
                }
              ]
            }
          }
        }
      }),
      '  </script>',
      '</body></html>'
    ].join('');

    const matches = scraper.parseCurrentSeasonResultRowsFromHtml(html, {
      currentUrl: 'https://www.oddsportal.com/football/england/championship-2025-2026/results/',
      leaguePathPrefix: '/football/england/championship/'
    });

    assert.strictEqual(matches.length, 1);
    assert.deepStrictEqual(matches[0], {
      url: 'https://www.oddsportal.com/football/england/championship-2025-2026/leeds-united-burnley-NtDt1234/',
      hash: 'NtDt1234',
      homeTeam: 'Leeds United',
      awayTeam: 'Burnley',
      matchDate: '2026-01-01T00:00:00.000Z',
      source: 'current_results_next_data'
    });
  });

  it('forceJsonExtract 开启时应优先返回 __NEXT_DATA__ 结果，不再混入 DOM 锚点候选', () => {
    const scraper = new ReconDomScraper({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    const html = [
      '<html><body>',
      '  <script id="__NEXT_DATA__" type="application/json">',
      JSON.stringify({
        props: {
          pageProps: {
            d: {
              rows: [
                {
                  encodeEventId: 'JsnOly01',
                  url: '/football/spain/segunda-division-2025-2026/levante-mirandes-JsnOly01/',
                  'home-name': 'Levante',
                  'away-name': 'Mirandes',
                  'date-start-timestamp': 1764547200
                }
              ]
            }
          }
        }
      }),
      '  </script>',
      '  <div class="eventRow">',
      '    <a href="/football/spain/segunda-division-2025-2026/oviedo-racing-domOnly88/">',
      '      <span class="eventRow__home">Oviedo</span>',
      '      <span class="eventRow__away">Racing</span>',
      '    </a>',
      '  </div>',
      '</body></html>'
    ].join('');

    const matches = scraper.parseCurrentSeasonResultRowsFromHtml(html, {
      currentUrl: 'https://www.oddsportal.com/football/spain/segunda-division-2025-2026/results/',
      leaguePathPrefix: '/football/spain/segunda-division/',
      forceJsonExtract: true
    });

    assert.strictEqual(matches.length, 1);
    assert.strictEqual(matches[0].hash, 'JsnOly01');
    assert.strictEqual(matches[0].source, 'current_results_next_data');
  });

  it('discoverSeasonResultPages 应合并首屏拦截与 DOM 结果，避免被第一页 API 截断', async () => {
    const scraper = new ReconDomScraper({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    scraper.extractCurrentSeasonResultRows = async () => ([
      {
        hash: 'sharedHash',
        url: 'https://www.oddsportal.com/shared',
        homeTeam: 'Qingdao West Coast',
        awayTeam: 'Henan Songshan Longmen',
        matchDate: null
      },
      {
        hash: 'domOnly1',
        url: 'https://www.oddsportal.com/dom-1',
        homeTeam: 'Changchun Yatai',
        awayTeam: 'Shanghai Shenhua',
        matchDate: null
      },
      {
        hash: 'domOnly2',
        url: 'https://www.oddsportal.com/dom-2',
        homeTeam: 'Meizhou Hakka',
        awayTeam: 'Tianjin Jinmen Tiger',
        matchDate: null
      }
    ]);

    scraper.extractPaginationMeta = async () => ({
      pageUrls: [],
      totalPages: 1
    });

    const result = await scraper.discoverSeasonResultPages(
      'https://www.oddsportal.com/football/china/super-league-2025/results/',
      { maxPages: 5, timeoutMs: 1000 },
      {
        navigate: async () => {},
        waitForTimeout: async () => {},
        getInterceptedData: () => ([
          {
            hash: 'sharedHash',
            url: 'https://www.oddsportal.com/shared',
            homeTeam: 'Qingdao West Coast',
            awayTeam: 'Henan Songshan Longmen',
            matchDate: '2026-04-22T11:35:00Z'
          }
        ])
      }
    );

    assert.strictEqual(result.initialSource, 'page_intercept+page_dom');
    assert.strictEqual(result.initialMatches.length, 3);
    assert.deepStrictEqual(result.initialMatches.map((item) => item.hash), [
      'sharedHash',
      'domOnly1',
      'domOnly2'
    ]);
    assert.strictEqual(
      result.initialMatches.find((item) => item.hash === 'sharedHash')?.matchDate,
      '2026-04-22T11:35:00Z'
    );
  });

  it('seasonless 目录页无比赛行时应识别年份 results 链接', async () => {
    const scraper = new ReconDomScraper({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    const html = [
      '<html><body>',
      '  <main>',
      '    <a href="/football/usa/mls/results/">2026</a>',
      '    <a href="/football/usa/mls-2025/results/">2025</a>',
      '    <a href="/football/usa/mls-2024/results/">2024</a>',
      '    <a href="/football/usa/mls/outrights/">Outrights</a>',
      '  </main>',
      '</body></html>'
    ].join('');

    scraper.extractCurrentSeasonResultRows = async () => [];
    scraper.extractPaginationMeta = async () => ({ pageUrls: [], totalPages: 1 });
    scraper.extractSeasonNavigationUrls = async () => (
      scraper.extractSeasonNavigationUrlsFromHtml(
        html,
        'https://www.oddsportal.com/football/usa/mls/results/'
      )
    );

    const result = await scraper.discoverSeasonResultPages(
      'https://www.oddsportal.com/football/usa/mls/results/',
      { maxPages: 5, timeoutMs: 1000 },
      {
        navigate: async () => {},
        waitForTimeout: async () => {},
        getInterceptedData: () => []
      }
    );

    assert.deepStrictEqual(result.pageUrls, [
      'https://www.oddsportal.com/football/usa/mls/results/',
      'https://www.oddsportal.com/football/usa/mls-2025/results/',
      'https://www.oddsportal.com/football/usa/mls-2024/results/'
    ]);
  });

  it('seasonless 年份链接在 maxPages 限制下应优先保留最近年份', async () => {
    const scraper = new ReconDomScraper({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    const html = [
      '<html><body>',
      '  <main>',
      '    <a href="/football/usa/mls/results/">2026</a>',
      '    <a href="/football/usa/mls-2025/results/">2025</a>',
      '    <a href="/football/usa/mls-2024/results/">2024</a>',
      '    <a href="/football/usa/mls-2023/results/">2023</a>',
      '    <a href="/football/usa/mls-2022/results/">2022</a>',
      '  </main>',
      '</body></html>'
    ].join('');

    scraper.extractCurrentSeasonResultRows = async () => [];
    scraper.extractPaginationMeta = async () => ({ pageUrls: [], totalPages: 1 });
    scraper.extractSeasonNavigationUrls = async () => (
      scraper.extractSeasonNavigationUrlsFromHtml(
        html,
        'https://www.oddsportal.com/football/usa/mls/results/'
      )
    );

    const result = await scraper.discoverSeasonResultPages(
      'https://www.oddsportal.com/football/usa/mls/results/',
      { maxPages: 3, timeoutMs: 1000 },
      {
        navigate: async () => {},
        waitForTimeout: async () => {},
        getInterceptedData: () => []
      }
    );

    assert.deepStrictEqual(result.pageUrls, [
      'https://www.oddsportal.com/football/usa/mls/results/',
      'https://www.oddsportal.com/football/usa/mls-2025/results/',
      'https://www.oddsportal.com/football/usa/mls-2024/results/'
    ]);
  });

  it('includeSeasonNavigation=false 时不得把其他赛季 results 链接并入当前 source', async () => {
    const scraper = new ReconDomScraper({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    const html = [
      '<html><body>',
      '  <main>',
      '    <a href="/football/usa/mls/results/">2026</a>',
      '    <a href="/football/usa/mls-2025/results/">2025</a>',
      '    <a href="/football/usa/mls-2024/results/">2024</a>',
      '  </main>',
      '</body></html>'
    ].join('');

    scraper.extractCurrentSeasonResultRows = async () => [];
    scraper.extractPaginationMeta = async () => ({ pageUrls: [], totalPages: 1 });
    scraper.extractSeasonNavigationUrls = async () => (
      scraper.extractSeasonNavigationUrlsFromHtml(
        html,
        'https://www.oddsportal.com/football/usa/mls/results/'
      )
    );

    const result = await scraper.discoverSeasonResultPages(
      'https://www.oddsportal.com/football/usa/mls/results/',
      { maxPages: 5, timeoutMs: 1000, includeSeasonNavigation: false },
      {
        navigate: async () => {},
        waitForTimeout: async () => {},
        getInterceptedData: () => []
      }
    );

    assert.deepStrictEqual(result.pageUrls, [
      'https://www.oddsportal.com/football/usa/mls/results/'
    ]);
  });
});
