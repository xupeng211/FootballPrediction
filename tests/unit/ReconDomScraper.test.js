'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { ReconDomScraper } = require('../../src/infrastructure/recon/services/ReconDomScraper');

describe('ReconDomScraper', () => {
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
});
