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
        const error = new Error('redis_busy');
        error.code = 'LOCK_CONTENDED';
        throw error;
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

test('ReconStitcher 应在锁后端故障时 fail-fast 而非伪装成锁争用', async () => {
  const stitcher = new ReconStitcher({
    repository: {
      async findMappingByHash() {
        return null;
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
        const error = new Error('redis_down');
        error.code = 'LOCK_BACKEND_ERROR';
        throw error;
      }
    }
  });

  await assert.rejects(
    () => stitcher.stitchSingle({
      hash: 'lock-backend-down',
      slug: 'arsenal-chelsea-lock-backend-down',
      url: 'oddsportal://lock-backend-down',
      date: '2025-08-18T19:00:00.000Z'
    }, '2025-2026', { name: 'Premier League' }),
    /redis_down/
  );
});

test('ReconStitcher 应在成功写库后记录 stitch_success 观测日志', async () => {
  const infoLogs = [];

  const stitcher = new ReconStitcher({
    repository: {
      async findMatchesByTeams() {
        return [{
          match_id: '130_20252026_9001',
          home_team: 'Inter Miami',
          away_team: 'Los Angeles FC',
          match_date: '2025-08-31T00:30:00.000Z'
        }];
      },
      async findMappingByHash() {
        return null;
      },
      async findMappingByMatchIdAndSeason() {
        return null;
      },
      async saveOddsPortalMapping(mapping) {
        return { success: true, matchId: mapping.match_id };
      }
    },
    parser: createParser({
      homeTeam: 'Inter Miami',
      awayTeam: 'Los Angeles FC'
    }),
    logger: {
      ...silentLogger,
      info(message, payload) {
        infoLogs.push({ message, payload });
      }
    },
    enableLocking: false
  });

  const result = await stitcher.stitchSingle({
    hash: 'mls-success-hash',
    slug: 'inter-miami-los-angeles-fc-mls-success-hash',
    url: 'oddsportal://mls-success-hash',
    date: '2025-08-31T00:30:00.000Z'
  }, '2025-2026', { name: 'MLS' });

  assert.equal(result.status, 'inserted');
  assert.ok(infoLogs.some((entry) => (
    entry.message === 'stitch_success'
      && entry.payload?.hash === 'mls-success-hash'
      && entry.payload?.matchId === '130_20252026_9001'
      && entry.payload?.league === 'MLS'
  )));
});

test('ReconStitcher 应在 slug 解析失败时回退到结构化 homeTeam/awayTeam', async () => {
  const savedMappings = [];

  const stitcher = new ReconStitcher({
    repository: {
      async findMatchesByTeams() {
        return [{
          match_id: '130_20252026_9010',
          home_team: 'Austin FC',
          away_team: 'Toronto FC',
          match_date: '2025-06-15T00:30:00.000Z'
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
    parser: {
      extractTeamsFromSlug() {
        return { homeTeam: 'Unknown', awayTeam: 'Unknown' };
      },
      normalizeTeamName(value) {
        return normalizeName(value)
          .split(' ')
          .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
          .join(' ');
      },
      calculateSimilarity(left, right) {
        return normalizeName(left) === normalizeName(right) ? 1 : 0;
      }
    },
    logger: silentLogger,
    enableLocking: false
  });

  const result = await stitcher.stitchSingle({
    hash: 'mls-structured-teams',
    slug: 'unknown-slug',
    url: 'oddsportal://mls-structured-teams',
    date: '2025-06-15T00:30:00.000Z',
    homeTeam: 'austin fc',
    awayTeam: 'toronto fc'
  }, '2025-2026', { name: 'MLS' });

  assert.equal(result.status, 'inserted');
  assert.equal(savedMappings.length, 1);
  assert.equal(savedMappings[0].match_id, '130_20252026_9010');
});

test('ReconStitcher.stitch 应只预热一次赛季 fixture lookup 并复用到整批缝合', async () => {
  const savedMappings = [];
  let seasonLookupLoads = 0;

  const stitcher = new ReconStitcher({
    repository: {
      async findMatchesBySeason() {
        seasonLookupLoads++;
        return [
          {
            match_id: '47_20252026_1000',
            home_team: 'Arsenal',
            away_team: 'Chelsea',
            match_date: '2025-08-16T14:00:00.000Z'
          },
          {
            match_id: '47_20252026_1001',
            home_team: 'Liverpool',
            away_team: 'Everton',
            match_date: '2025-08-17T14:00:00.000Z'
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
    parser: {
      extractTeamsFromSlug() {
        return { homeTeam: 'Unknown', awayTeam: 'Unknown' };
      },
      normalizeTeamName(value) {
        return String(value || '').trim();
      },
      calculateSimilarity(left, right) {
        return normalizeName(left) === normalizeName(right) ? 1 : 0;
      }
    },
    logger: silentLogger,
    enableLocking: false
  });

  const result = await stitcher.stitch([
    {
      hash: 'batch-stitch-hash-1',
      slug: 'arsenal-chelsea',
      url: 'oddsportal://arsenal-chelsea',
      homeTeam: 'Arsenal',
      awayTeam: 'Chelsea',
      date: '2025-08-16T14:00:00.000Z'
    },
    {
      hash: 'batch-stitch-hash-2',
      slug: 'liverpool-everton',
      url: 'oddsportal://liverpool-everton',
      homeTeam: 'Liverpool',
      awayTeam: 'Everton',
      date: '2025-08-17T14:00:00.000Z'
    }
  ], '2025-2026', { name: 'Premier League' });

  assert.equal(result.inserted, 2);
  assert.equal(savedMappings.length, 2);
  assert.equal(seasonLookupLoads, 1);
});

test('ReconStitcher.stitchBatch 应把多场命中压缩为一次 batchSaveOddsPortalMappings', async () => {
  const batchCalls = [];
  let singleSaveCalls = 0;

  const stitcher = new ReconStitcher({
    repository: {
      async findMappingByHash() {
        return null;
      },
      async findMappingByMatchIdAndSeason() {
        return null;
      },
      async batchSaveOddsPortalMappings(mappings, options) {
        batchCalls.push({ mappings, options });
        return {
          success: true,
          inserted: mappings.length,
          applied: mappings.length
        };
      },
      async saveOddsPortalMapping() {
        singleSaveCalls++;
        return { success: true };
      }
    },
    parser: createParser({
      homeTeam: 'Arsenal',
      awayTeam: 'Chelsea'
    }),
    logger: silentLogger,
    enableLocking: false
  });

  const result = await stitcher.stitchBatch([
    {
      rawMatch: {
        hash: 'bulk-hash-1',
        url: 'oddsportal://bulk-1',
        homeTeam: 'Arsenal',
        awayTeam: 'Chelsea'
      },
      l1Match: {
        match_id: '47_20252026_1000',
        home_team: 'Arsenal',
        away_team: 'Chelsea',
        match_date: '2025-08-16T14:00:00.000Z'
      }
    },
    {
      rawMatch: {
        hash: 'bulk-hash-2',
        url: 'oddsportal://bulk-2',
        homeTeam: 'Liverpool',
        awayTeam: 'Everton'
      },
      l1Match: {
        match_id: '47_20252026_1001',
        home_team: 'Liverpool',
        away_team: 'Everton',
        match_date: '2025-08-17T14:00:00.000Z'
      }
    }
  ], '2025-2026', { name: 'Premier League' });

  assert.equal(result.inserted, 2);
  assert.equal(result.unmatched, 0);
  assert.equal(batchCalls.length, 1);
  assert.equal(batchCalls[0].mappings.length, 2);
  assert.deepEqual(batchCalls[0].options, {
    pipelineStatus: 'RECON_LINKED',
    preserve_linked_status: true
  });
  assert.equal(singleSaveCalls, 0);
});
