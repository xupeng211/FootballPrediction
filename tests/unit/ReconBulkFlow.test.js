'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { ReconEngine } = require('../../src/infrastructure/recon/ReconEngine');
const { FixtureRepository } = require('../../src/infrastructure/services/FixtureRepository');

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function createPendingMatches(count, leagueName = 'Premier League', season = '2024/2025') {
  return Array.from({ length: count }, (_, index) => ({
    match_id: `47_20242025_${1000 + index}`,
    home_team: `Home ${index}`,
    away_team: `Away ${index}`,
    league_name: leagueName,
    season,
    match_date: new Date(Date.UTC(2024, 7, 1, 12, index % 60, 0)).toISOString()
  }));
}

function createWebCandidates(matches) {
  return matches.map((match) => ({
    hash: `hash_${match.match_id}`,
    url: `oddsportal://football/england/premier-league-2024-2025/${match.match_id}/`,
    homeTeam: match.home_team,
    awayTeam: match.away_team
  }));
}

describe('ReconEngine - Bulk Flow TDD', () => {
  it('应通过 L1ConfigManager 生成待扫描 URL 列表', async () => {
    const engine = new ReconEngine({
      configManager: {
        getActiveLeagues() {
          return [
            { id: 47, name: 'Premier League', country: 'england', slug: 'premier-league', enabled: true },
            { id: 54, name: 'Bundesliga', country: 'germany', slug: 'bundesliga', enabled: true }
          ];
        }
      },
      baseUrl: 'oddsportal://root',
      logger: { info() {}, warn() {}, error() {} }
    });

    const targets = await engine.buildScanTargets({ season: '2024-2025' });

    assert.deepStrictEqual(
      targets.map((target) => ({
        leagueId: target.leagueId,
        url: target.resultsUrl
      })),
      [
        {
          leagueId: 47,
          url: 'oddsportal://root/football/england/premier-league-2024-2025/results/'
        },
        {
          leagueId: 54,
          url: 'oddsportal://root/football/germany/bundesliga-2024-2025/results/'
        }
      ]
    );
  });

  it('应在 50 场待对齐比赛上严格执行 5 并发限制', async () => {
    const pendingMatches = createPendingMatches(50);
    let active = 0;
    let maxActive = 0;

    const engine = new ReconEngine({
      configManager: {
        getActiveLeagues() {
          return [{ id: 47, name: 'Premier League', country: 'england', slug: 'premier-league', enabled: true }];
        }
      },
      repository: {
        async getUnstitchedMatches() {
          return pendingMatches;
        },
        async batchSaveOddsPortalMappings() {
          return { success: true, inserted: pendingMatches.length };
        },
        async batchUpdateMatchPipelineStatus() {
          return { updated: pendingMatches.length };
        }
      },
      navigator: {
        async protocolArchiveExtract() {
          return { matches: createWebCandidates(pendingMatches), pagesScanned: 1 };
        }
      },
      parser: { calculateSimilarity: () => 1 },
      logger: { info() {}, warn() {}, error() {} },
      baseUrl: 'oddsportal://root'
    });

    engine._reconcilePendingMatch = async (l1Match) => {
      active++;
      maxActive = Math.max(maxActive, active);
      await delay(5);
      active--;

      return {
        status: 'linked',
        mapping: {
          match_id: l1Match.match_id,
          oddsportal_hash: `hash_${l1Match.match_id}`,
          full_url: `oddsportal://match/${l1Match.match_id}`,
          season: '2024/2025',
          league_name: 'Premier League',
          home_team: l1Match.home_team,
          away_team: l1Match.away_team
        }
      };
    };

    const result = await engine.runReconMatrix({
      season: '2024-2025',
      concurrency: 5,
      confidenceThreshold: 0.75
    });

    assert.strictEqual(result.success, true);
    assert.strictEqual(result.totalPending, 50);
    assert.strictEqual(result.linked, 50);
    assert.strictEqual(maxActive, 5);
  });

  it('应在对齐成功和失败后分别回写 RECON_LINKED 与 RECON_MISMATCH', async () => {
    const pendingMatches = createPendingMatches(2);
    const statusCalls = [];
    const savedBatches = [];

    const engine = new ReconEngine({
      configManager: {
        getActiveLeagues() {
          return [{ id: 47, name: 'Premier League', country: 'england', slug: 'premier-league', enabled: true }];
        }
      },
      repository: {
        async getUnstitchedMatches() {
          return pendingMatches;
        },
        async batchSaveOddsPortalMappings(mappings) {
          savedBatches.push(mappings);
          return { success: true, inserted: mappings.length };
        },
        async batchUpdateMatchPipelineStatus(matchIds, status) {
          statusCalls.push({ matchIds, status });
          return { updated: matchIds.length };
        }
      },
      navigator: {
        async protocolArchiveExtract() {
          return { matches: createWebCandidates(pendingMatches), pagesScanned: 1 };
        }
      },
      parser: { calculateSimilarity: () => 1 },
      logger: { info() {}, warn() {}, error() {} },
      baseUrl: 'oddsportal://root'
    });

    engine._reconcilePendingMatch = async (l1Match) => {
      if (l1Match.match_id.endsWith('1000')) {
        return {
          status: 'linked',
          mapping: {
            match_id: l1Match.match_id,
            oddsportal_hash: `hash_${l1Match.match_id}`,
            full_url: `oddsportal://match/${l1Match.match_id}`,
            season: '2024/2025',
            league_name: 'Premier League',
            home_team: l1Match.home_team,
            away_team: l1Match.away_team
          }
        };
      }

      return {
        status: 'mismatch',
        matchId: l1Match.match_id
      };
    };

    const result = await engine.runReconMatrix({
      season: '2024-2025',
      concurrency: 2,
      confidenceThreshold: 0.75
    });

    assert.strictEqual(result.linked, 1);
    assert.strictEqual(result.mismatched, 1);
    assert.strictEqual(savedBatches.length, 1);
    assert.deepStrictEqual(statusCalls, [
      { matchIds: ['47_20242025_1000'], status: 'RECON_LINKED' },
      { matchIds: ['47_20242025_1001'], status: 'RECON_MISMATCH' }
    ]);
  });
});

describe('FixtureRepository - Recon sorting defense', () => {
  it('批量写入 matches_oddsportal_mapping 时应按 match_id 升序排序', async () => {
    const insertOrder = [];

    const pool = {
      async query() {
        return {
          rows: [
            { column_name: 'match_confidence' },
            { column_name: 'mapping_method' }
          ]
        };
      },
      async connect() {
        return {
          async query(sql, params) {
            if (sql.includes('RETURNING match_id')) {
              insertOrder.push(params[0]);
              return { rows: [{ match_id: params[0] }] };
            }

            return { rows: [] };
          },
          release() {}
        };
      }
    };

    const repository = new FixtureRepository({
      dbPool: pool,
      maxRetries: 1,
      logger: { info() {}, warn() {}, error() {} }
    });

    await repository.batchSaveOddsPortalMappings([
      {
        match_id: '47_20242025_1002',
        oddsportal_hash: 'hash-2',
        full_url: 'oddsportal://example/2',
        season: '2024/2025',
        league_name: 'Premier League',
        home_team: 'C',
        away_team: 'D'
      },
      {
        match_id: '47_20242025_1001',
        oddsportal_hash: 'hash-1',
        full_url: 'oddsportal://example/1',
        season: '2024/2025',
        league_name: 'Premier League',
        home_team: 'A',
        away_team: 'B'
      }
    ]);

    assert.deepStrictEqual(insertOrder, [
      '47_20242025_1001',
      '47_20242025_1002'
    ]);
  });
});
