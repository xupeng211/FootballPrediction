'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const { ReconEngine } = require('../../src/infrastructure/recon/ReconEngine');
const { ReconParser } = require('../../src/infrastructure/recon/ReconParser');
const { ReconStitcher } = require('../../src/infrastructure/recon/ReconStitcher');
const { FixtureRepository } = require('../../src/infrastructure/services/FixtureRepository');

test('ReconEngine 应在候选主客反转时写入 is_reversed=true 且保留 L1 主客定义', async () => {
  const l1Match = {
    match_id: '47_20252026_1000',
    home_team: 'Wolves',
    away_team: 'Spurs',
    match_date: '2025-08-16T14:00:00.000Z'
  };

  const engine = new ReconEngine({
    parser: {
      calculateSimilarity(left, right) {
        const normalize = (value) => String(value || '').toLowerCase().trim();
        return normalize(left) === normalize(right) ? 1 : 0;
      }
    },
    logger: { info() {}, warn() {}, error() {} }
  });

  engine._findBestCandidate = function findBestCandidateStub() {
    return {
      candidate: {
        hash: 'op_hash_1',
        url: 'oddsportal://wolves-vs-spurs',
        homeTeam: 'Spurs',
        awayTeam: 'Wolves',
        matchDate: '2025-08-16T14:00:00.000Z'
      },
      confidence: 1,
      method: 'exact',
      isReversed: true
    };
  };

  const outcome = await engine._reconcilePendingMatch(l1Match, [], {
    dbSeason: '2025/2026',
    league: { name: 'Premier League' }
  }, 0.75);

  assert.equal(outcome.status, 'linked');
  assert.equal(outcome.mapping.home_team, 'Wolves');
  assert.equal(outcome.mapping.away_team, 'Spurs');
  assert.equal(outcome.mapping.is_reversed, true);
});

test('FixtureRepository 应在可选列存在时持久化 is_reversed', async () => {
  const insertParams = [];
  const pool = {
    async query(sql) {
      if (sql.includes('information_schema.columns')) {
        return {
          rows: [
            { column_name: 'match_confidence' },
            { column_name: 'mapping_method' },
            { column_name: 'is_reversed' }
          ]
        };
      }

      return { rows: [] };
    },
    async connect() {
      return {
        async query(sql, params) {
          if (sql.includes('RETURNING match_id')) {
            insertParams.push(params);
            return { rows: [{ match_id: params[0] }] };
          }

          if (sql.includes('UPDATE matches')) {
            return { rows: [], rowCount: Array.isArray(params?.[0]) ? params[0].length : 0 };
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

  const result = await repository.batchSaveOddsPortalMappings([{
    match_id: '47_20252026_1000',
    oddsportal_hash: 'hash_1',
    full_url: 'oddsportal://example/1',
    season: '2025/2026',
    league_name: 'Premier League',
    home_team: 'Wolves',
    away_team: 'Spurs',
    is_reversed: true
  }], {
    pipelineStatus: 'RECON_LINKED'
  });

  assert.equal(result.success, true);
  assert.equal(insertParams.length, 1);
  assert.equal(insertParams[0][insertParams[0].length - 1], true);
});

test('ReconEngine 应在 archive 候选仅返回数字队伍 ID 时回退到 URL slug 解析真实队名', () => {
  const engine = new ReconEngine({
    parser: new ReconParser({
      logger: { info() {}, warn() {}, error() {} },
      traceId: 'slug-fallback'
    }),
    logger: { info() {}, warn() {}, error() {} }
  });

  const l1Match = {
    home_team: 'Benfica',
    away_team: 'Qarabag Fk',
    match_date: '2025-09-16T19:00:00.000Z'
  };

  const best = engine._findBestCandidate(l1Match, [{
    hash: 'hCfJZyrH',
    url: 'https://www.oddsportal.com/football/europe/champions-league/benfica-qarabag-agdam-hCfJZyrH/',
    homeTeam: 25545813,
    awayTeam: 25545815,
    matchDate: '2025-09-16T19:00:00.000Z'
  }]);

  assert.ok(best, '应找到 URL 回推后的候选');
  assert.ok(best.confidence >= 0.75, `期望置信度 >= 0.75，实际 ${best.confidence}`);
  assert.equal(best.candidate.homeTeam, 'Benfica');
  assert.match(best.candidate.awayTeam, /Qarabag/i);
});

test('ReconEngine 应优先通过 season mirror 直接命中同日同队候选', () => {
  const engine = new ReconEngine({
    parser: {
      calculateSimilarity() {
        return 0;
      }
    },
    logger: { info() {}, warn() {}, error() {} }
  });

  const l1Match = {
    home_team: 'Leeds United',
    away_team: 'Burnley',
    match_date: '2025-08-12T19:00:00.000Z'
  };
  const candidates = [{
    hash: 'season-mirror-hash',
    url: 'oddsportal://championship/leeds-burnley',
    homeTeam: 'Leeds United',
    awayTeam: 'Burnley',
    matchDate: '2025-08-12T19:00:00.000Z'
  }];
  const mirror = engine._buildSeasonMirror(candidates);

  const best = engine._findBestCandidate(l1Match, [], mirror);

  assert.ok(best, 'season mirror 应直接返回候选');
  assert.equal(best.method, 'season_mirror');
  assert.equal(best.candidate.hash, 'season-mirror-hash');
  assert.equal(best.isReversed, false);
  assert.equal(best.confidence, 1);
});

test('ReconStitcher 应在 hash lock 中把数字队伍 ID 回退为 URL slug 队名', async () => {
  const savedMappings = [];
  const stitcher = new ReconStitcher({
    repository: {
      async saveOddsPortalMapping(mapping) {
        savedMappings.push(mapping);
        return { success: true };
      }
    },
    logger: { info() {}, warn() {}, error() {} },
    parser: new ReconParser({
      logger: { info() {}, warn() {}, error() {} },
      traceId: 'stitcher-slug-fallback'
    }),
    enableLocking: false
  });

  const result = await stitcher.stitchWithHashLock([{
    hash: 'hCfJZyrH',
    url: 'https://www.oddsportal.com/football/europe/champions-league/benfica-qarabag-agdam-hCfJZyrH/',
    homeTeam: 25545813,
    awayTeam: 25545815
  }], [{
    match_id: '42_20252026_4947188',
    home_team: 'Benfica',
    away_team: 'Qarabag Fk'
  }], '2025-2026', { name: 'Champions League' });

  assert.equal(result.inserted, 1);
  assert.equal(savedMappings.length, 1);
  assert.equal(savedMappings[0].home_team, 'Benfica');
  assert.equal(savedMappings[0].away_team, 'Qarabag Fk');
});

test('ReconStitcher 应在 hash lock 中容忍对象型队名而不触发 toLowerCase 崩溃', async () => {
  const savedMappings = [];
  const stitcher = new ReconStitcher({
    repository: {
      async saveOddsPortalMapping(mapping) {
        savedMappings.push(mapping);
        return { success: true };
      }
    },
    logger: { info() {}, warn() {}, error() {} },
    parser: new ReconParser({
      logger: { info() {}, warn() {}, error() {} },
      traceId: 'stitcher-object-team'
    }),
    enableLocking: false
  });

  stitcher._resolveWebMatchTeams = (match) => match;

  const result = await stitcher.stitchWithHashLock([{
    hash: 'objTeamHash1',
    url: 'https://www.oddsportal.com/football/europe/champions-league/benfica-qarabag-agdam-objTeam1/',
    homeTeam: { toString: () => 'Benfica' },
    awayTeam: { toString: () => 'Qarabag Fk' }
  }], [{
    match_id: '42_20252026_4947188',
    home_team: 'Benfica',
    away_team: 'Qarabag Fk'
  }], '2025-2026', { name: 'Champions League' });

  assert.equal(result.inserted, 1);
  assert.equal(savedMappings.length, 1);
  assert.equal(savedMappings[0].match_id, '42_20252026_4947188');
});
