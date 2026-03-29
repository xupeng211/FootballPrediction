'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const { ReconEngine } = require('../../src/infrastructure/recon/ReconEngine');

test('ReconEngine 在 navigator 后置注入时必须同步闭合到 taskPlanner，避免 protocolArchiveExtract 空指针', async () => {
  const protocolCalls = [];
  const batchCalls = [];
  const pendingMatches = [{
    match_id: '47_20252026_5000',
    home_team: 'Arsenal',
    away_team: 'Chelsea',
    league_name: 'Premier League',
    season: '2025/2026',
    match_date: '2025-08-01T19:00:00.000Z'
  }];

  const engine = new ReconEngine({
    repository: {
      async getReconEligibleMatches() {
        return pendingMatches;
      },
      async batchSaveOddsPortalMappings(batch) {
        batchCalls.push({ type: 'linked', size: batch.length });
        return { success: true, inserted: batch.length, updated: batch.length };
      },
      async batchUpdateMatchPipelineStatus(batch) {
        batchCalls.push({ type: 'mismatch', size: batch.length });
        return { success: true, updated: batch.length };
      }
    },
    parser: {
      calculateSimilarity(left, right) {
        return String(left || '').toLowerCase() === String(right || '').toLowerCase() ? 1 : 0;
      }
    },
    logger: { info() {}, warn() {}, error() {} },
    baseUrl: 'oddsportal://root'
  });

  assert.equal(engine.navigator, null);
  assert.equal(engine.taskPlanner.navigator, null);

  engine.navigator = {
    async fetchFullSeasonArchive(url, options = {}) {
      protocolCalls.push({ url, options });
      return {
        matches: [{
          hash: 'hash_5000',
          url: 'oddsportal://match/5000',
          homeTeam: 'Arsenal',
          awayTeam: 'Chelsea',
          matchDate: '2025-08-01T19:00:00.000Z'
        }],
        pagesScanned: 1,
        totalCandidates: 1,
        sourceState: 'FULL_SEASON_SWEEP'
      };
    }
  };

  const result = await engine.smartScan('2025-2026', {
    id: 47,
    name: 'Premier League',
    country: 'england',
    slug: 'premier-league'
  });

  assert.equal(engine.taskPlanner.navigator, engine.navigator);
  assert.equal(result.success, true);
  assert.equal(result.linked, 1);
  assert.equal(result.totalInserted, 1);
  assert.deepEqual(batchCalls, [{ type: 'linked', size: 1 }]);
  assert.deepEqual(protocolCalls, [{
    url: 'oddsportal://root/football/england/premier-league-2025-2026/results/',
    options: {
      maxPages: 50,
      timeoutMs: 90000,
      preferCurrentSeasonSource: true
    }
  }]);
});

test('ReconEngine smartScan 遇到 SKIPPED_FUTURE_FINALS 时必须返回成功态，避免误判为失败', async () => {
  const engine = new ReconEngine({
    repository: {
      async getReconEligibleMatches() {
        return [{
          match_id: '72_20252026_0001',
          home_team: 'Mexico',
          away_team: 'South Africa',
          league_name: 'FIFA World Cup',
          season: '2025/2026',
          match_date: '2026-06-11T19:00:00.000Z'
        }];
      }
    },
    taskPlanner: {
      buildTarget() {
        return {
          dbSeason: '2025/2026',
          season: '2025-2026',
          league: { name: 'FIFA World Cup', slug: 'world-cup-2026', country: 'world' },
          resultsUrl: 'https://example.com/world-cup-2026/results/'
        };
      },
      async loadReconPendingMatches() {
        return [{
          match_id: '72_20252026_0001',
          home_team: 'Mexico',
          away_team: 'South Africa',
          league_name: 'FIFA World Cup',
          season: '2025/2026',
          match_date: '2026-06-11T19:00:00.000Z'
        }];
      },
      formatSeasonForUrl(season) {
        return season;
      }
    },
    logger: { info() {}, warn() {}, error() {} }
  });

  engine._runReconTarget = async () => {
    const error = new Error('SKIPPED_FUTURE_FINALS');
    error.code = 'SKIPPED_FUTURE_FINALS';
    error.sourceUrl = 'https://example.com/world-cup-2026/results/';
    error.sourceSeason = '2025-2026';
    throw error;
  };

  const result = await engine.smartScan('2025-2026', {
    name: 'FIFA World Cup',
    slug: 'world-cup-2026',
    country: 'world'
  });

  assert.equal(result.success, true);
  assert.equal(result.skipped, true);
  assert.equal(result.sourceState, 'SKIPPED_FUTURE_FINALS');
  assert.equal(result.skippedPendingTotal, 1);
  assert.equal(result.pendingTotal, 0);
  assert.equal(result.linked, 0);
  assert.equal(result.coverage, 100);
});
