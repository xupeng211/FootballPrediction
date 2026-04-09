'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');

const { reconTaskPlannerUrlUtils } = require('../../src/infrastructure/recon/services/ReconTaskPlannerUrlUtils');

function createContext(overrides = {}) {
  return {
    ...reconTaskPlannerUrlUtils,
    baseUrl: 'oddsportal://root/',
    resultsPathTemplate: '/football/{country}/{league}-{season}/results/',
    fixturesPathTemplate: '/football/{country}/{league}-{season}/fixtures/',
    annualLeagueIds: new Set([81]),
    matchEvaluator: {
      isPlaceholderFixture(match) {
        return Boolean(match?.placeholder);
      }
    },
    ...overrides
  };
}

describe('ReconTaskPlannerUrlUtils', () => {
  it('应覆盖赛季格式化、联赛类型判定与 season year 解析', () => {
    const context = createContext();

    assert.equal(context.formatSeasonForUrl('2025/2026'), '2025-2026');
    assert.equal(context.formatSeasonForUrl(null), '');
    assert.equal(context.formatSeasonForAnnualLeagueUrl('2025/2026'), '2026');
    assert.equal(context.formatSeasonForAnnualLeagueUrl('2026'), '2026');
    assert.equal(context.formatSeasonForLeagueUrl('2025/2026', { id: 81 }), '2026');
    assert.equal(context.formatSeasonForLeagueUrl('2025-2026', { seasonType: 'single_year' }), '2026');
    assert.equal(context.formatSeasonForLeagueUrl('2026', { season_type: 'single_year' }), '2026');
    assert.equal(context.formatSeasonForLeagueUrl('2025/2026', { seasonType: 'seasonal' }), '2025-2026');
    assert.equal(context.isSingleYearLeague({ season_type: 'single_year' }), true);
    assert.equal(context.isAnnualLeague({ id: 81 }), true);
    assert.equal(context.isAnnualLeague({ id: 999 }), false);
    assert.equal(context.normalizeDbSeason('2025-2026'), '2025/2026');
    assert.deepEqual(context.parseSeasonYears('2025/2026'), { startYear: 2025, endYear: 2026 });
    assert.equal(context.parseSeasonYears('unknown'), null);
    assert.equal(context.shiftSeason('2025/2026', 1), '2026-2027');
    assert.equal(context.shiftSeason('single-year', 1), 'single-year');
    assert.deepEqual(
      context.getPendingMatchYears([
        { match_date: '2024-03-01T00:00:00.000Z' },
        { match_date: '2025-03-01T00:00:00.000Z' },
        { match_date: 'invalid-date' },
        { match_date: '2024-06-01T00:00:00.000Z' }
      ]),
      [2024, 2025]
    );
  });

  it('应覆盖当前赛季判定、占位符过滤与 future finals 窗口', () => {
    const context = createContext();
    const now = new Date();
    const currentYear = now.getUTCFullYear();
    const currentSeason = now.getUTCMonth() + 1 >= 7
      ? `${currentYear}-${currentYear + 1}`
      : `${currentYear - 1}-${currentYear}`;

    assert.equal(context.isCurrentSeason(String(currentYear)), true);
    assert.equal(context.isCurrentSeason(currentSeason), true);
    assert.equal(context.isCurrentSeason('not-a-season'), false);

    const filtered = context.filterPlaceholderFixtures([
      { match_id: 'a', placeholder: true },
      { match_id: 'b', placeholder: false }
    ]);
    assert.deepEqual(filtered, [{ match_id: 'b', placeholder: false }]);

    const fallbackContext = createContext({ matchEvaluator: null });
    const rawMatches = [{ match_id: 'x' }];
    assert.deepEqual(fallbackContext.filterPlaceholderFixtures(rawMatches), rawMatches);

    assert.deepEqual(
      context.getFutureFinalsWindow(
        { league: { awaitingFinals: true } },
        [{ match_date: 'not-a-date' }],
        new Date('2026-01-01T00:00:00.000Z')
      ),
      { shouldSkip: false, kickoffDate: null }
    );

    assert.deepEqual(
      context.getFutureFinalsWindow(
        { league: { awaiting_finals: true } },
        [{ match_date: '2026-02-01T00:00:00.000Z' }],
        new Date('2026-01-01T00:00:00.000Z')
      ),
      { shouldSkip: true, kickoffDate: '2026-02-01T00:00:00.000Z' }
    );
  });

  it('应覆盖 URL 构建辅助方法与附加路径模板', () => {
    const context = createContext();
    const league = {
      id: 130,
      country: 'Costa Rica',
      slug: 'Primera División',
      resultsSlug: 'primera-division',
      seasonType: 'single_year',
      resultsUrlStrategy: 'seasonless',
      additional_results_paths: ['/football/{country}/{league}/standings/', ''],
      additionalHistoricalResultsPaths: ['/football/{country}/{league}-{year}/archive/'],
      seasonless_current_year_basis: 'start'
    };

    assert.equal(context.normalizePathSegment('Primera División'), 'primera-division');
    assert.equal(context.slugIncludesYear('j1-league-2025'), true);
    assert.equal(context.getResultsUrlStrategy(league), 'seasonless');
    assert.equal(context.getSeasonlessCurrentYearBasis(league), 'start');
    assert.equal(
      context.renderSeasonPathUrl('/football/{country}/{league}-{season}/results/', league, '2025/2026'),
      'oddsportal://root/football/costa-rica/primera-division-2026/results/'
    );
    assert.equal(
      context.renderLeaguePathTemplate('/football/{country}/{league}-{year}/archive/', league, { year: 2024 }),
      'oddsportal://root/football/costa-rica/primera-division-2024/archive/'
    );
    assert.equal(context.buildResultsUrl(league, '2025/2026'), 'oddsportal://root/football/costa-rica/primera-division/results/');
    assert.equal(context.buildFixturesUrl(league, '2025/2026'), 'oddsportal://root/football/costa-rica/primera-division-2026/fixtures/');
    assert.equal(createContext({ fixturesPathTemplate: null }).buildFixturesUrl(league, '2025/2026'), null);
    assert.equal(context.buildSeasonlessSubpageUrl(league, ''), 'oddsportal://root/football/costa-rica/primera-division/');
    assert.equal(context.buildSeasonlessResultsUrl(league), 'oddsportal://root/football/costa-rica/primera-division/results/');
    assert.equal(context.buildSeasonlessFixturesUrl(league), 'oddsportal://root/football/costa-rica/primera-division/fixtures/');
    assert.deepEqual(
      context.getAdditionalPathTemplates(league, 'additionalResultsPaths', 'additional_results_paths'),
      ['/football/{country}/{league}/standings/']
    );
    assert.deepEqual(context.getAdditionalPathTemplates({}, 'additionalResultsPaths'), []);
    assert.deepEqual(
      context.buildAdditionalResultsUrls(league, '2025/2026'),
      ['oddsportal://root/football/costa-rica/primera-division/standings/']
    );
    assert.deepEqual(
      context.buildAdditionalHistoricalResultsUrls(league, 2024),
      ['oddsportal://root/football/costa-rica/primera-division-2024/archive/']
    );
    assert.deepEqual(
      context.buildCurrentSeasonSourceUrls(league, '2025/2026'),
      [
        'oddsportal://root/football/costa-rica/primera-division/results/',
        'oddsportal://root/football/costa-rica/primera-division/standings/'
      ]
    );
    assert.deepEqual(
      context.buildHistoricalSeasonSourceUrls(league, 2024),
      [
        'oddsportal://root/football/costa-rica/primera-division-2024/results/',
        'oddsportal://root/football/costa-rica/primera-division-2024/archive/'
      ]
    );
    assert.equal(context.buildLeagueUrl(league), 'oddsportal://root/football/costa-rica/primera-division/');
    assert.equal(
      context.buildSeasonlessHistoricalResultsUrl(league, 2024),
      'oddsportal://root/football/costa-rica/primera-division-2024/results/'
    );
  });

  it('应为年度制联赛去重当前赛季 source URL', () => {
    const context = createContext({
      resultsPathTemplate: '/football/{country}/{league}/results/',
      fixturesPathTemplate: '/football/{country}/{league}/fixtures/'
    });
    const league = {
      id: 81,
      country: 'usa',
      slug: 'mls'
    };

    assert.deepEqual(
      context.buildAnnualCurrentSeasonSources(league, '2025/2026'),
      [
        {
          season: '2026',
          url: 'oddsportal://root/football/usa/mls/results/',
          mode: 'current_results'
        },
        {
          season: '2026',
          url: 'oddsportal://root/football/usa/mls/fixtures/',
          mode: 'current_fixtures'
        }
      ]
    );
  });

  it('J2 League 应将 seasonless results 提升为 primary，并跳过稳定 404 的 fixtures sweep', () => {
    const context = createContext();

    assert.deepEqual(
      context.buildAnnualCurrentSeasonSources({
        id: 8974,
        country: 'Japan',
        slug: 'j2-league',
        seasonType: 'single_year'
      }, '2025/2026'),
      [
        {
          season: '2026',
          url: 'oddsportal://root/football/japan/j2-league/results/',
          mode: 'current_results'
        }
      ]
    );
  });

  it('应为 SOURCE_EMPTY 问题联赛补 canonical fallback URL', () => {
    const context = createContext();

    assert.deepEqual(
      context.buildSeasonalSourceUrls({
        id: 140,
        country: 'Spain',
        slug: 'segunda-division',
        seasonType: 'dual_year'
      }, '2025/2026', { dbSeason: '2025/2026' }),
      [
        'oddsportal://root/football/spain/segunda-division-2025-2026/results/',
        'oddsportal://root/football/spain/laliga2-2025-2026/results/',
        'oddsportal://root/football/spain/laliga2/results/'
      ]
    );

    assert.deepEqual(
      context.buildSeasonalSourceUrls({
        id: 230,
        country: 'Mexico',
        slug: 'liga-mx',
        seasonType: 'single_year'
      }, '2026', { dbSeason: '2025/2026' }),
      [
        'oddsportal://root/football/mexico/liga-mx/results/',
        'oddsportal://root/football/mexico/liga-mx/',
        'oddsportal://root/football/mexico/liga-mx-2025-2026/results/'
      ]
    );
  });

  it('欧冠应补 league root fallback，以便补抓次回合与当前页数据', () => {
    const context = createContext();

    assert.deepEqual(
      context.buildSeasonalSourceUrls({
        id: 42,
        country: 'Europe',
        slug: 'champions-league',
        seasonType: 'dual_year'
      }, '2025/2026'),
      [
        'oddsportal://root/football/europe/champions-league-2025-2026/results/',
        'oddsportal://root/football/europe/champions-league/results/',
        'oddsportal://root/football/europe/champions-league/'
      ]
    );
  });

  it('法国杯应补 league root fallback，以便补抓业余轮次当前页数据', () => {
    const context = createContext();

    assert.deepEqual(
      context.buildSeasonalSourceUrls({
        id: 181,
        country: 'France',
        slug: 'coupe-de-france',
        seasonType: 'dual_year'
      }, '2025/2026'),
      [
        'oddsportal://root/football/france/coupe-de-france-2025-2026/results/',
        'oddsportal://root/football/france/coupe-de-france/results/',
        'oddsportal://root/football/france/coupe-de-france/'
      ]
    );
  });
});
