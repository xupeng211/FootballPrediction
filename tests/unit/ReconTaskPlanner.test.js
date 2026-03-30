'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { ReconTaskPlanner } = require('../../src/infrastructure/recon/services/ReconTaskPlanner');
const { ReconMirrorManager } = require('../../src/infrastructure/recon/services/ReconMirrorManager');
const { ReconMatchEvaluator } = require('../../src/infrastructure/recon/services/ReconMatchEvaluator');

function createPlanner(overrides = {}) {
  const evaluator = new ReconMatchEvaluator({
    parser: {
      calculateSimilarity(left, right) {
        return String(left || '').toLowerCase().trim() === String(right || '').toLowerCase().trim() ? 1 : 0;
      }
    },
    logger: { info() {}, warn() {}, error() {} }
  });
  const mirrorManager = new ReconMirrorManager({ evaluator });
  evaluator.setMirrorManager(mirrorManager);

  return new ReconTaskPlanner({
    baseUrl: 'oddsportal://root',
    repository: overrides.repository || {},
    navigator: overrides.navigator || {},
    logger: overrides.logger || { info() {}, warn() {}, error() {} },
    configManager: overrides.configManager || null,
    matchEvaluator: evaluator,
    mirrorManager,
    sampleSize: overrides.sampleSize
  });
}

describe('ReconTaskPlanner', () => {
  it('应在有限配额内优先调度高置信度任务', () => {
    const planner = createPlanner();
    const pendingMatches = [
      {
        match_id: '47_20242025_1000',
        home_team: 'Home 0',
        away_team: 'Away 0',
        match_date: '2024-08-01T12:00:00.000Z'
      },
      {
        match_id: '47_20242025_1001',
        home_team: 'Home 1',
        away_team: 'Away 1',
        match_date: '2024-08-03T12:00:00.000Z'
      },
      {
        match_id: '47_20242025_1002',
        home_team: 'Home 2',
        away_team: 'Away 2',
        match_date: '2024-08-02T12:00:00.000Z'
      }
    ];
    const candidates = [
      {
        hash: 'hash_1000',
        url: 'oddsportal://match/1000',
        homeTeam: 'Home 0',
        awayTeam: 'Away 0',
        matchDate: '2024-08-01T12:00:00.000Z'
      },
      {
        hash: 'hash_1001',
        url: 'oddsportal://match/1001',
        homeTeam: 'Home 1',
        awayTeam: 'Away 1',
        matchDate: '2024-08-03T12:00:00.000Z'
      }
    ];

    const selected = planner.selectProcessablePendingMatches(
      pendingMatches,
      candidates,
      0.75,
      2
    );

    assert.deepStrictEqual(
      selected.map((match) => match.match_id),
      ['47_20242025_1001', '47_20242025_1000']
    );
  });

  it('当前赛季 SOURCE_EMPTY 时应保留当前赛季 source，不得回退到上一赛季', async () => {
    const calls = [];
    const planner = createPlanner({
      navigator: {
        async fetchFullSeasonArchive(url, options) {
          calls.push({ url, options });
          return {
            matches: [],
            pagesScanned: 1,
            totalCandidates: 0,
            sourceState: 'SOURCE_EMPTY'
          };
        }
      }
    });

    const target = {
      leagueId: 47,
      league: { name: 'Premier League', country: 'england', slug: 'premier-league' },
      season: '2025-2026',
      dbSeason: '2025/2026',
      resultsUrl: 'oddsportal://root/football/england/premier-league-2025-2026/results/'
    };
    const pendingMatches = [{
      match_id: '47_20252026_5000',
      home_team: 'Arsenal',
      away_team: 'Chelsea',
      match_date: '2025-08-01T19:00:00.000Z'
    }];

    const selected = await planner.selectCandidateSource(target, pendingMatches, 0.75);

    assert.strictEqual(selected.source.season, '2025-2026');
    assert.strictEqual(selected.source.url, target.resultsUrl);
    assert.strictEqual(selected.extractResult.sourceState, 'SOURCE_EMPTY');
    assert.strictEqual(selected.sampleLinked, 0);
    assert.deepStrictEqual(calls, [
      {
        url: target.resultsUrl,
        options: {
          maxPages: 50,
          timeoutMs: 90000,
          preferCurrentSeasonSource: true
        }
      }
    ]);
  });

  it('seasonless 联赛应生成 canonical results URL，不得拼接双年份后缀', () => {
    const planner = createPlanner();

    const url = planner.buildResultsUrl({
      name: 'Süper Lig',
      country: 'turkey',
      slug: 's-per-lig',
      resultsSlug: 'super-lig',
      resultsUrlStrategy: 'seasonless'
    }, '2025-2026');

    assert.strictEqual(
      url,
      'oddsportal://root/football/turkey/super-lig/results/'
    );
  });

  it('巴甲应使用 seasonless 的 serie-a results URL', () => {
    const planner = createPlanner();

    const url = planner.buildResultsUrl({
      name: 'Brasileirão',
      country: 'brazil',
      slug: 'brasileirao',
      resultsSlug: 'serie-a',
      resultsUrlStrategy: 'seasonless'
    }, '2025-2026');

    assert.strictEqual(
      url,
      'oddsportal://root/football/brazil/serie-a/results/'
    );
  });

  it('多词 country 应转换为 OddsPortal 连字符路径段', () => {
    const planner = createPlanner();

    const url = planner.buildResultsUrl({
      name: 'Copa América',
      country: 'South America',
      slug: 'copa-america',
      resultsSlug: 'copa-america',
      resultsUrlStrategy: 'seasonal'
    }, '2025-2026');

    assert.strictEqual(
      url,
      'oddsportal://root/football/south-america/copa-america-2025-2026/results/'
    );
  });

  it('slug 已包含年份时不得追加系统 season 后缀', () => {
    const planner = createPlanner();

    const url = planner.buildResultsUrl({
      name: 'FIFA World Cup',
      country: 'world',
      slug: 'world-cup-2026',
      resultsSlug: 'world-cup-2026',
      resultsUrlStrategy: 'seasonal'
    }, '2025-2026');

    assert.strictEqual(
      url,
      'oddsportal://root/football/world/world-cup-2026/results/'
    );
  });

  it('sample 评估应跳过占位符对阵，不得让其稀释 sampleLinked', async () => {
    const planner = createPlanner({
      sampleSize: 1,
      navigator: {
        async fetchFullSeasonArchive() {
          return {
            matches: [{
              hash: 'real-match',
              url: 'oddsportal://match/real',
              homeTeam: 'Mexico',
              awayTeam: 'South Africa',
              matchDate: '2026-06-11T19:00:00.000Z'
            }],
            pagesScanned: 1,
            totalCandidates: 1,
            sourceState: 'FULL_SEASON_SWEEP'
          };
        }
      }
    });

    const target = {
      leagueId: 77,
      league: { name: 'FIFA World Cup', country: 'world', slug: 'world-cup-2026' },
      season: '2025-2026',
      dbSeason: '2025/2026',
      resultsUrl: 'oddsportal://root/football/world/world-cup-2026/results/'
    };
    const pendingMatches = [
      {
        match_id: '77_20252026_0001',
        home_team: '1e',
        away_team: '3abcdf',
        match_date: '2026-06-29T20:30:00.000Z'
      },
      {
        match_id: '77_20252026_9999',
        home_team: 'Mexico',
        away_team: 'South Africa',
        match_date: '2026-06-11T19:00:00.000Z'
      }
    ];

    const selected = await planner.selectCandidateSource(target, pendingMatches, 0.75);

    assert.strictEqual(selected.sampleLinked, 1);
    assert.strictEqual(selected.candidates.length, 1);
  });

  it('awaiting finals 联赛在开赛前应跳过 Recon 扫描', async () => {
    let navigatorCalls = 0;
    const logs = [];
    const planner = createPlanner({
      navigator: {
        async fetchFullSeasonArchive() {
          navigatorCalls += 1;
          return {
            matches: [],
            pagesScanned: 0,
            totalCandidates: 0,
            sourceState: 'SOURCE_EMPTY'
          };
        }
      },
      logger: {
        info(event, payload) {
          logs.push({ event, payload });
        },
        warn() {},
        error() {}
      }
    });

    const target = {
      leagueId: 77,
      league: {
        name: 'FIFA World Cup',
        country: 'world',
        slug: 'world-cup-2026',
        awaitingFinals: true
      },
      season: '2025-2026',
      dbSeason: '2025/2026',
      resultsUrl: 'oddsportal://root/football/world/world-cup-2026/results/'
    };
    const pendingMatches = [{
      match_id: '77_20252026_5000',
      home_team: 'Mexico',
      away_team: 'South Africa',
      match_date: '2099-06-11T19:00:00.000Z'
    }];

    const selected = await planner.selectCandidateSource(target, pendingMatches, 0.75);

    assert.strictEqual(navigatorCalls, 0);
    assert.strictEqual(selected.extractResult.sourceState, 'SKIPPED_FUTURE_FINALS');
    assert.ok(logs.some((entry) => entry.event === 'skipping_future_finals'));
  });

  it('未标记 awaiting finals 的联赛不得被未来赛程跳过，中超应继续扫描', async () => {
    let navigatorCalls = 0;
    const planner = createPlanner({
      navigator: {
        async protocolArchiveExtract() {
          navigatorCalls += 1;
          return {
            matches: [],
            pagesScanned: 1,
            totalCandidates: 0,
            sourceState: 'SOURCE_EMPTY'
          };
        }
      }
    });

    const target = {
      leagueId: 120,
      league: {
        name: 'CSL',
        country: 'china',
        slug: 'super-league',
        resultsUrlStrategy: 'seasonless'
      },
      season: '2025-2026',
      dbSeason: '2025/2026',
      resultsUrl: 'oddsportal://root/football/china/super-league/results/'
    };
    const pendingMatches = [{
      match_id: '120_20252026_5000',
      home_team: 'Shanghai Port',
      away_team: 'Beijing Guoan',
      match_date: '2099-03-01T12:00:00.000Z'
    }];

    await planner.selectCandidateSource(target, pendingMatches, 0.75);

    assert.strictEqual(navigatorCalls, 1);
  });

  it('seasonless 跨年联赛应组合当前赛季页与历史年份结果页', async () => {
    const calls = [];
    const planner = createPlanner({
      navigator: {
        async protocolArchiveExtract(url, options) {
          calls.push({ type: 'protocol', url, options });
          return {
            matches: [{
              hash: 'future-match',
              url: 'oddsportal://match/future',
              homeTeam: 'Qingdao Hainiu',
              awayTeam: 'Henan Songshan Longmen',
              matchDate: '2026-04-04T07:30:00.000Z'
            }],
            pagesScanned: 1,
            totalCandidates: 1,
            sourceState: 'CURRENT_TOURNAMENT'
          };
        },
        async fetchFullSeasonArchive(url, options) {
          calls.push({ type: 'archive', url, options });
          return {
            matches: [{
              hash: 'past-match',
              url: 'oddsportal://match/past',
              homeTeam: 'Changchun Yatai',
              awayTeam: 'Shanghai Shenhua',
              matchDate: '2025-06-29T10:30:00.000Z'
            }],
            pagesScanned: 1,
            totalCandidates: 1,
            sourceState: 'FULL_SEASON_SWEEP'
          };
        }
      }
    });

    const target = {
      leagueId: 120,
      league: {
        name: 'CSL',
        country: 'China',
        slug: 'super-league',
        results_url_strategy: 'seasonless'
      },
      season: '2025-2026',
      dbSeason: '2025/2026',
      resultsUrl: 'oddsportal://root/football/china/super-league/results/'
    };
    const pendingMatches = [
      {
        match_id: '120_20252026_0001',
        home_team: 'Changchun Yatai',
        away_team: 'Shanghai Shenhua',
        match_date: '2025-06-29T10:30:00.000Z'
      },
      {
        match_id: '120_20252026_0002',
        home_team: 'Qingdao Hainiu',
        away_team: 'Henan FC',
        match_date: '2026-04-04T07:30:00.000Z'
      }
    ];

    const selected = await planner.selectCandidateSource(target, pendingMatches, 0.75);

    assert.strictEqual(calls.length, 2);
    assert.deepStrictEqual(
      calls.map((call) => call.url),
      [
        'oddsportal://root/football/china/super-league/',
        'oddsportal://root/football/china/super-league-2025/results/'
      ]
    );
    assert.strictEqual(calls[0].type, 'protocol');
    assert.strictEqual(calls[0].options.preferCurrentSeasonSource, true);
    assert.strictEqual(selected.candidates.length, 2);
    assert.strictEqual(selected.sampleLinked, 2);
  });
});
