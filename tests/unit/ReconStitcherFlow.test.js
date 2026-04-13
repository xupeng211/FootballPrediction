'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const { ReconStitcher } = require('../../src/infrastructure/recon/ReconStitcher');

const silentLogger = {
  info() {},
  warn() {},
  error() {}
};

function normalizeName(value) {
  return String(value || '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

function createParser(teams) {
  return {
    extractTeamsFromSlug() {
      return teams;
    },
    calculateSimilarity(left, right) {
      return normalizeName(left) === normalizeName(right) ? 1 : 0;
    }
  };
}

test('ReconStitcher 应在 5 分钟内的开球漂移中命中正确 match_id', async () => {
  const savedMappings = [];
  let requestedSeason = null;

  const stitcher = new ReconStitcher({
    repository: {
      async findMatchesByTeams(_homeTeam, _awayTeam, season) {
        requestedSeason = season;
        return [
          {
            match_id: '54_20252026_4824901',
            home_team: 'Bayern Munich',
            away_team: 'RB Leipzig',
            match_date: '2025-08-22T18:30:00.000Z'
          },
          {
            match_id: '54_20252026_4999999',
            home_team: 'Bayern Munich',
            away_team: 'RB Leipzig',
            match_date: '2025-09-12T18:30:00.000Z'
          }
        ];
      },
      async findMappingByHash() {
        return null;
      },
      async findMappingByMatchIdAndSeason() {
        return null;
      },
      async saveOddsPortalMapping(mapping) {
        savedMappings.push(mapping);
        return { success: true, matchId: mapping.match_id };
      }
    },
    parser: createParser({
      homeTeam: 'Bayern Munich',
      awayTeam: 'RB Leipzig'
    }),
    logger: silentLogger,
    enableLocking: false
  });

  const result = await stitcher.stitchSingle({
    hash: 'correct-date-hash',
    slug: 'bayern-munich-rb-leipzig-correct-date',
    url: 'oddsportal://correct-date',
    date: '2025-08-22T18:35:00.000Z'
  }, '2025-2026', { name: 'Bundesliga' });

  assert.equal(result.status, 'inserted');
  assert.equal(requestedSeason, '2025/2026');
  assert.equal(savedMappings.length, 1);
  assert.equal(savedMappings[0].match_id, '54_20252026_4824901');
  assert.equal(savedMappings[0].mapping_method, 'exact_kickoff_tolerance');
});

test('ReconStitcher 应在 LeagueName 缺失时回退到 source leagueName', async () => {
  const savedMappings = [];

  const stitcher = new ReconStitcher({
    repository: {
      async findMatchesByTeams() {
        return [{
          match_id: '55_20252026_4001',
          home_team: 'Juventus',
          away_team: 'Inter',
          match_date: '2025-09-01T18:45:00.000Z'
        }];
      },
      async findMappingByHash() {
        return null;
      },
      async findMappingByMatchIdAndSeason() {
        return null;
      },
      async saveOddsPortalMapping(mapping) {
        savedMappings.push(mapping);
        return { success: true, matchId: mapping.match_id };
      }
    },
    parser: createParser({
      homeTeam: 'Juventus',
      awayTeam: 'Inter'
    }),
    logger: silentLogger,
    enableLocking: false
  });

  const result = await stitcher.stitchSingle({
    hash: 'serie-a-hash',
    slug: 'juventus-inter-serie-a-hash',
    url: 'oddsportal://serie-a',
    date: '2025-09-01T18:45:00.000Z',
    leagueName: 'Serie A'
  }, '2025-2026', {});

  assert.equal(result.status, 'inserted');
  assert.equal(savedMappings.length, 1);
  assert.equal(savedMappings[0].league_name, 'Serie A');
});

test('ReconStitcher 应在同一 match_id 的 hash 变化时标记 sequential_hash_rollover', async () => {
  const savedMappings = [];
  const warnLogs = [];

  const stitcher = new ReconStitcher({
    repository: {
      async findMatchesByTeams() {
        return [{
          match_id: '47_20252026_4813435',
          home_team: 'AFC Bournemouth',
          away_team: 'Fulham',
          match_date: '2025-10-03T19:00:00.000Z'
        }];
      },
      async findMappingByHash() {
        return null;
      },
      async findMappingByMatchIdAndSeason() {
        return {
          match_id: '47_20252026_4813435',
          season: '2025/2026',
          league_name: 'Premier League',
          oddsportal_hash: 'old-hash'
        };
      },
      async saveOddsPortalMapping(mapping) {
        savedMappings.push(mapping);
        return { success: true, matchId: mapping.match_id };
      }
    },
    parser: createParser({
      homeTeam: 'AFC Bournemouth',
      awayTeam: 'Fulham'
    }),
    logger: {
      ...silentLogger,
      warn(message, payload) {
        warnLogs.push({ message, payload });
      }
    },
    enableLocking: false
  });

  const result = await stitcher.stitchSingle({
    hash: 'new-hash',
    slug: 'bournemouth-fulham-new-hash',
    url: 'oddsportal://new-hash',
    date: '2025-10-03T19:00:00.000Z'
  }, '2025-2026', { name: 'Premier League' });

  assert.equal(result.status, 'inserted');
  assert.equal(savedMappings.length, 1);
  assert.equal(savedMappings[0].mapping_method, 'sequential_hash_rollover');
  assert.ok(warnLogs.some((entry) => entry.message === 'stitch_hash_rollover_detected'));
});

test('ReconStitcher 应在 hash 锁争用时跳过当前缝合而非继续写库', async () => {
  let repositoryTouched = false;

  const stitcher = new ReconStitcher({
    repository: {
      async findMappingByHash() {
        repositoryTouched = true;
        return null;
      },
      async saveOddsPortalMapping() {
        repositoryTouched = true;
        return { success: true };
      }
    },
    parser: createParser({
      homeTeam: 'Arsenal',
      awayTeam: 'Chelsea'
    }),
    logger: silentLogger,
    enableLocking: true,
    lockManager: {
      async acquireRowLock() {
        throw new Error('redis_busy');
      }
    }
  });

  const result = await stitcher.stitchSingle({
    hash: 'lock-busy-hash',
    slug: 'arsenal-chelsea-lock-busy-hash',
    url: 'oddsportal://lock-busy-hash',
    date: '2025-08-18T19:00:00.000Z'
  }, '2025-2026', { name: 'Premier League' });

  assert.equal(result.status, 'skipped');
  assert.deepEqual(result.details, { reason: 'lock_contended' });
  assert.equal(repositoryTouched, false);
});
