'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { ReconEngine } = require('../../src/infrastructure/recon/ReconEngine');
const { FixtureRepository } = require('../../src/infrastructure/services/FixtureRepository');

const delay = (ms) => new Promise((resolve) => {
  setTimeout(resolve, ms);
});

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

  it('构建结果页 URL 时应对 country 与 slug 做小写归一化', async () => {
    const engine = new ReconEngine({
      configManager: {
        getActiveLeagues() {
          return [
            { id: 48, name: 'Championship', country: 'England', slug: 'Championship', enabled: true }
          ];
        }
      },
      baseUrl: 'oddsportal://root',
      logger: { info() {}, warn() {}, error() {} }
    });

    const targets = await engine.buildScanTargets({ season: '2025-2026' });

    assert.strictEqual(
      targets[0].resultsUrl,
      'oddsportal://root/football/england/championship-2025-2026/results/'
    );
  });

  it('当前赛季结果页无候选时应报告 SOURCE_EMPTY，且不得回退到上一赛季 URL', async () => {
    const pendingMatches = createPendingMatches(3, 'Premier League', '2025/2026').map((match, index) => ({
      ...match,
      match_id: `47_20252026_${5000 + index}`
    }));
    const protocolCalls = [];

    const engine = new ReconEngine({
      configManager: {
        getActiveLeagues() {
          return [
            { id: 47, name: 'Premier League', country: 'england', slug: 'premier-league', enabled: true }
          ];
        }
      },
      repository: {
        async getReconEligibleMatches() {
          return pendingMatches;
        },
        async batchSaveOddsPortalMappings(mappings) {
          return { success: true, inserted: mappings.length };
        },
        async batchUpdateMatchPipelineStatus(matchIds) {
          return { updated: matchIds.length };
        }
      },
      navigator: {
        async protocolArchiveExtract(url, options = {}) {
          protocolCalls.push({ url, options });
          return {
            matches: [],
            pagesScanned: 1,
            totalCandidates: 0,
            sourceState: 'SOURCE_EMPTY'
          };
        }
      },
      parser: {
        calculateSimilarity(left, right) {
          return left === right ? 1 : 0;
        }
      },
      logger: { info() {}, warn() {}, error() {} },
      baseUrl: 'oddsportal://root'
    });

    const result = await engine.runReconMatrix({
      season: '2025-2026',
      concurrency: 2,
      confidenceThreshold: 0.75
    });

    assert.strictEqual(result.success, false);
    assert.strictEqual(result.linked, 0);
    assert.strictEqual(result.errors.length, 1);
    assert.strictEqual(result.errors[0].error, 'SOURCE_EMPTY');
    assert.deepStrictEqual(protocolCalls, [
      {
        url: 'oddsportal://root/football/england/premier-league-2025-2026/results/',
        options: {
          maxPages: 50,
          timeoutMs: engine.archiveTimeoutMs,
          preferCurrentSeasonSource: true,
          circuitBreakerKey: 'recon:47:2025/2026'
        }
      }
    ]);
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

  it('应仅消费 harvested 的 Recon 目标，并在全局 limit 下跨联赛分配', async () => {
    const championshipMatches = createPendingMatches(40, 'Championship').map((match, index) => ({
      ...match,
      match_id: `48_20242025_${2000 + index}`
    }));
    const eplMatches = createPendingMatches(40, 'Premier League').map((match, index) => ({
      ...match,
      match_id: `47_20242025_${3000 + index}`
    }));

    const engine = new ReconEngine({
      configManager: {
        getActiveLeagues() {
          return [
            { id: 48, name: 'Championship', country: 'england', slug: 'championship', enabled: true },
            { id: 47, name: 'Premier League', country: 'england', slug: 'premier-league', enabled: true }
          ];
        }
      },
      repository: {
        async getReconEligibleMatches(_season, leagueName) {
          return leagueName === 'Championship' ? championshipMatches : eplMatches;
        },
        async batchSaveOddsPortalMappings(mappings) {
          return { success: true, inserted: mappings.length };
        },
        async batchUpdateMatchPipelineStatus(matchIds) {
          return { updated: matchIds.length };
        }
      },
      navigator: {
        async protocolArchiveExtract(url) {
          return {
            matches: url.includes('championship')
              ? createWebCandidates(championshipMatches)
              : createWebCandidates(eplMatches),
            pagesScanned: 1
          };
        }
      },
      parser: { calculateSimilarity: () => 1 },
      logger: { info() {}, warn() {}, error() {} },
      baseUrl: 'oddsportal://root'
    });

    engine._reconcilePendingMatch = async (l1Match, _candidates, target) => ({
      status: 'linked',
      mapping: {
        match_id: l1Match.match_id,
        oddsportal_hash: `hash_${l1Match.match_id}`,
        full_url: `oddsportal://match/${l1Match.match_id}`,
        season: target.dbSeason,
        league_name: target.league.name,
        home_team: l1Match.home_team,
        away_team: l1Match.away_team
      }
    });

    const result = await engine.runReconMatrix({
      season: '2024-2025',
      concurrency: 5,
      limit: 50
    });

    assert.strictEqual(result.totalPending, 50);
    assert.strictEqual(result.linked, 50);
    assert.strictEqual(result.perLeague.length, 2);
    assert.ok(result.perLeague.every((item) => item.pendingTotal === 25));
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
        async batchSaveOddsPortalMappings(mappings, options) {
          savedBatches.push({ mappings, options });
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
    assert.deepStrictEqual(savedBatches, [
      {
        mappings: [
          {
            match_id: '47_20242025_1000',
            oddsportal_hash: 'hash_47_20242025_1000',
            full_url: 'oddsportal://match/47_20242025_1000',
            season: '2024/2025',
            league_name: 'Premier League',
            home_team: 'Home 0',
            away_team: 'Away 0'
          }
        ],
        options: {
          pipelineStatus: 'RECON_LINKED',
          preserve_linked_status: true
        }
      }
    ]);
    assert.deepStrictEqual(statusCalls, [
      { matchIds: ['47_20242025_1001'], status: 'RECON_MISMATCH' }
    ]);
  });

  it('批量对齐时在关闭高成功率降采样后应每 50 场输出一次进度快照', async () => {
    const pendingMatches = createPendingMatches(120);
    const logs = [];

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
          return { success: true, inserted: mappings.length };
        },
        async batchUpdateMatchPipelineStatus(matchIds) {
          return { updated: matchIds.length };
        }
      },
      navigator: {
        async protocolArchiveExtract() {
          return { matches: createWebCandidates(pendingMatches), pagesScanned: 1 };
        }
      },
      parser: { calculateSimilarity: () => 1 },
      logger: {
        info(event, payload) {
          logs.push({ event, payload });
        },
        warn() {},
        error() {}
      },
      baseUrl: 'oddsportal://root',
      progressHighSuccessThreshold: 2
    });

    engine._reconcilePendingMatch = async (l1Match) => ({
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
    });

    const result = await engine.runReconMatrix({
      season: '2024-2025',
      concurrency: 5,
      confidenceThreshold: 0.75
    });

    assert.strictEqual(result.linked, 120);
    const progressLogs = logs.filter((entry) => entry.event === 'recon_progress_snapshot');
    assert.deepStrictEqual(
      progressLogs.map((entry) => entry.payload.processed),
      [50, 100, 120]
    );
    assert.ok(
      progressLogs.every((entry) => typeof entry.payload.memoryMb === 'number' && entry.payload.memoryMb >= 0),
      '进度快照应包含内存占用'
    );
  });

  it('选择最佳候选时应优先同日比赛，避免被错误日期的同队名候选抢走', () => {
    const engine = new ReconEngine({
      parser: {
        calculateSimilarity(left, right) {
          return left === right ? 1 : 0.95;
        }
      },
      logger: { info() {}, warn() {}, error() {} }
    });

    const l1Match = {
      match_id: '54_20252026_4824901',
      home_team: 'Bayern Munich',
      away_team: 'RB Leipzig',
      match_date: '2025-08-22T18:30:00.000Z'
    };
    const wrongDateCandidate = {
      hash: 'wrong-date',
      url: 'oddsportal://wrong-date',
      homeTeam: 'Bayern Munich',
      awayTeam: 'RB Leipzig',
      matchDate: '2025-09-12T18:30:00.000Z'
    };
    const correctDateCandidate = {
      hash: 'correct-date',
      url: 'oddsportal://correct-date',
      homeTeam: 'Bayern Munich',
      awayTeam: 'RB Leipzig',
      matchDate: '2025-08-22T18:30:00.000Z'
    };

    const best = engine._findBestCandidate(l1Match, [wrongDateCandidate, correctDateCandidate]);

    assert.strictEqual(best.candidate.hash, 'correct-date');
    assert.ok(best.confidence > 0.95);
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

  it('映射写入与 RECON_LINKED 状态推进应在同一个事务中完成', async () => {
    const events = [];

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
            const normalized = sql.trim().split(/\s+/).slice(0, 4).join(' ');
            events.push({ sql: normalized, params });

            if (sql.includes('RETURNING match_id')) {
              return { rows: [{ match_id: params[0] }] };
            }

            if (sql.includes('UPDATE matches')) {
              return { rows: [], rowCount: Array.isArray(params?.[0]) ? params[0].length : 0 };
            }

            return { rows: [] };
          },
          release() {
            events.push({ sql: 'RELEASE' });
          }
        };
      }
    };

    const repository = new FixtureRepository({
      dbPool: pool,
      maxRetries: 1,
      logger: { info() {}, warn() {}, error() {} }
    });

    const result = await repository.batchSaveOddsPortalMappings([
      {
        match_id: '47_20252026_1002',
        oddsportal_hash: 'hash-2',
        full_url: 'oddsportal://example/2',
        season: '2025/2026',
        league_name: 'Premier League',
        home_team: 'C',
        away_team: 'D'
      },
      {
        match_id: '47_20252026_1001',
        oddsportal_hash: 'hash-1',
        full_url: 'oddsportal://example/1',
        season: '2025/2026',
        league_name: 'Premier League',
        home_team: 'A',
        away_team: 'B'
      }
    ], {
      pipelineStatus: 'RECON_LINKED'
    });

    assert.strictEqual(result.success, true);
    assert.strictEqual(result.inserted, 2);
    assert.strictEqual(result.updated, 2);
    assert.deepStrictEqual(
      events.map((event) => event.sql),
      [
        'BEGIN',
        'SELECT season, oddsportal_hash, match_id,',
        'INSERT INTO matches_oddsportal_mapping (match_id,',
        'INSERT INTO matches_oddsportal_mapping (match_id,',
        'UPDATE matches m SET',
        'COMMIT',
        'RELEASE'
      ]
    );
    assert.deepStrictEqual(events[4].params, [
      ['47_20252026_1001', '47_20252026_1002'],
      'RECON_LINKED'
    ]);
  });
});
