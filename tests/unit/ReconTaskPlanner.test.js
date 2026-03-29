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
    mirrorManager
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
});
