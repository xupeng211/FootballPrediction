'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { reconMatrixFlow } = require('../../src/infrastructure/recon/services/ReconMatrixFlow');
const { reconMatchExtractor } = require('../../src/infrastructure/recon/services/ReconMatchExtractor');

describe('ReconMatrixFlow', () => {
  it('应将 season_mirror 与 pure_protocol source 归一化为 protocol_extract', () => {
    const flow = { ...reconMatrixFlow };

    assert.strictEqual(
      flow._normalizeMappingMethod({
        method: 'season_mirror',
        candidate: { source: 'pure_protocol_archive:xbsqV0go' }
      }),
      'protocol_extract'
    );
  });

  it('应保留数据库白名单中的 mapping_method', () => {
    const flow = { ...reconMatrixFlow };

    assert.strictEqual(
      flow._normalizeMappingMethod({
        method: 'exact',
        candidate: { source: 'pure_protocol_archive:xbsqV0go' }
      }),
      'exact'
    );
  });

  it('SOURCE_EMPTY 回退到本地字典时应尊重 matchLimit', async () => {
    const captured = [];
    const flow = {
      ...reconMatrixFlow,
      defaultReconConcurrency: 2,
      reconBatchSize: 25,
      confidenceThreshold: 0.75,
      logger: { info() {}, warn() {}, error() {} },
      mirrorManager: { buildSeasonMirror: () => new Map() },
      taskPlanner: {
        resolveReconPolicy: () => ({ effectiveConfidenceThreshold: 0.75 }),
        selectProcessablePendingMatches: () => {
          throw new Error('不应进入 selectProcessablePendingMatches');
        }
      },
      _primeLeagueDictionary: async () => [{ remote_name: 'Alpha', local_team_name: 'Alpha' }],
      _canUseLocalDictionaryFallback: () => true,
      _shouldUseLocalDictionaryOnly: () => false,
      _selectCandidateSourceWithLocalFallback: async () => ({
        candidates: [],
        source: {
          season: '2025/2026',
          url: 'https://example.com/results/'
        },
        extractResult: {
          sourceState: 'SOURCE_EMPTY'
        }
      }),
      _runLocalDictionaryOnlyTarget: async (_target, pendingMatches) => {
        captured.push(pendingMatches.map((match) => match.match_id));
        return {
          pendingTotal: pendingMatches.length,
          linked: 0,
          mismatched: pendingMatches.length,
          sourceSeason: '2025/2026',
          sourceUrl: 'dictionary://recon/1/2025%2F2026',
          candidateCount: pendingMatches.length,
          effectiveConfidenceThreshold: 0.75
        };
      },
      _buildLocalDictionarySourceUrl: () => 'dictionary://recon/1/2025%2F2026'
    };

    const result = await flow._runReconTarget(
      {
        leagueId: 1,
        dbSeason: '2025/2026',
        season: '2025/2026',
        league: { id: 1, name: 'Test League' }
      },
      {
        pendingMatches: [
          { match_id: 'm3', pipeline_status: 'harvested' },
          { match_id: 'm1', pipeline_status: 'harvested' },
          { match_id: 'm2', pipeline_status: 'harvested' }
        ],
        matchLimit: 2
      }
    );

    assert.deepStrictEqual(captured, [['m1', 'm2']]);
    assert.strictEqual(result.pendingTotal, 2);
    assert.strictEqual(result.mismatched, 2);
  });

  it('全量 RECON_MISMATCH 也应先回源选择 source，不得被本地字典短路', async () => {
    const selectedCalls = [];
    const persisted = [];
    const flow = {
      ...reconMatrixFlow,
      baseUrl: 'https://www.oddsportal.com',
      defaultReconConcurrency: 1,
      reconBatchSize: 25,
      confidenceThreshold: 0.75,
      logger: { info() {}, warn() {}, error() {} },
      mirrorManager: { buildSeasonMirror: () => new Map() },
      taskPlanner: {
        resolveReconPolicy: () => ({ effectiveConfidenceThreshold: 0.75 }),
        selectProcessablePendingMatches: (pendingMatches, _candidates, _threshold, matchLimit) => (
          Number.isInteger(matchLimit) && matchLimit > 0
            ? pendingMatches.slice(0, matchLimit)
            : pendingMatches
        )
      },
      matchExtractor: reconMatchExtractor,
      _primeLeagueDictionary: async () => [{ remote_name: 'Alpha', local_team_name: 'Alpha' }],
      _canUseLocalDictionaryFallback: () => true,
      _runLocalDictionaryOnlyTarget: async () => {
        throw new Error('不应在全量 mismatch 时直接短路到本地字典');
      },
      _selectCandidateSourceWithLocalFallback: async (_target, pendingMatches) => {
        selectedCalls.push(pendingMatches.map((match) => match.match_id));
        return {
          candidates: [{
            hash: 'AbCd1234',
            url: 'https://www.oddsportal.com/football/test-country/test-league/alpha-beta-AbCd1234/',
            homeTeam: 'Alpha',
            awayTeam: 'Beta',
            matchDate: '2026-04-05T05:00:00.000Z',
            source: 'current_results_dom'
          }],
          source: {
            season: '2025/2026',
            url: 'https://www.oddsportal.com/football/test-country/test-league/results/'
          },
          seasonMirror: new Map()
        };
      },
      _findBestCandidate: () => ({
        candidate: {
          hash: 'AbCd1234',
          url: 'https://www.oddsportal.com/football/test-country/test-league/alpha-beta-AbCd1234/',
          homeTeam: 'Alpha',
          awayTeam: 'Beta',
          matchDate: '2026-04-05T05:00:00.000Z',
          source: 'current_results_dom'
        },
        confidence: 1,
        method: 'exact',
        isReversed: false
      }),
      _createReconRunId: () => 'run-remote-first',
      _shouldEmitReconProgressSnapshot: () => false,
      _emitReconProgressSnapshot() {},
      _persistReconBatches: async (mappings, mismatches) => {
        persisted.push({ mappings, mismatches });
        return {
          linkedApplied: mappings.length,
          mismatchUpdated: mismatches.length
        };
      }
    };

    const result = await flow._runReconTarget(
      {
        leagueId: 223,
        dbSeason: '2025/2026',
        season: '2025/2026',
        resultsUrl: 'https://www.oddsportal.com/football/test-country/test-league/results/',
        league: { id: 223, name: 'J1 League' }
      },
      {
        pendingMatches: [
          { match_id: 'm2', pipeline_status: 'RECON_MISMATCH', home_team: 'Alpha', away_team: 'Beta', match_date: '2026-04-05T05:00:00.000Z' },
          { match_id: 'm1', pipeline_status: 'RECON_MISMATCH', home_team: 'Alpha', away_team: 'Beta', match_date: '2026-04-05T05:00:00.000Z' }
        ],
        matchLimit: 1
      }
    );

    assert.deepStrictEqual(selectedCalls, [['m1', 'm2']]);
    assert.strictEqual(persisted.length, 1);
    assert.strictEqual(persisted[0].mappings.length, 1);
    assert.strictEqual(result.pendingTotal, 1);
    assert.strictEqual(result.linked, 1);
  });

  it('linked 前应先把 h2h 候选洗白为 canonical URL', async () => {
    const flow = {
      ...reconMatrixFlow,
      baseUrl: 'https://www.oddsportal.com',
      logger: { info() {}, warn() {}, error() {} },
      matchExtractor: reconMatchExtractor,
      _findBestCandidate: () => ({
        candidate: {
          hash: 'QwErTy12',
          url: 'https://www.oddsportal.com/football/h2h/kashiwa-reysol-AbCd1234/yokohama-f-marinos-EfGh5678/#QwErTy12',
          homeTeam: 'Kashiwa Reysol',
          awayTeam: 'Yokohama F.Marinos',
          matchDate: '2026-04-05T05:00:00.000Z',
          source: 'current_results_dom'
        },
        confidence: 1,
        method: 'exact',
        isReversed: false
      })
    };

    const outcome = await flow._reconcilePendingMatch(
      {
        match_id: '223_20252026_4691098',
        home_team: 'Kashiwa Reysol',
        away_team: 'Yokohama F.Marinos',
        match_date: '2026-04-05T05:00:00.000Z',
        pipeline_status: 'harvested'
      },
      [],
      {
        dbSeason: '2025/2026',
        resultsUrl: 'https://www.oddsportal.com/football/japan/j1-league/results/',
        reconSourceUrl: 'https://www.oddsportal.com/football/japan/j1-league/results/',
        league: { name: 'J1 League' }
      },
      0.15,
      null
    );

    assert.strictEqual(outcome.status, 'linked');
    assert.strictEqual(
      outcome.mapping.full_url,
      'https://www.oddsportal.com/football/japan/j1-league/kashiwa-reysol-yokohama-f-marinos-QwErTy12/'
    );
  });

  it('runReconMatrix 应在联赛级扇出中分配独立 navigator 端口并受 p-limit 限流', async () => {
    const workerStarts = [];
    let active = 0;
    let maxActive = 0;
    let nextPort = 7890;

    const preparedTargets = ['Premier League', 'Serie A', 'Bundesliga'].map((leagueName, index) => ({
      target: {
        leagueId: index + 1,
        league: { id: index + 1, name: leagueName },
        dbSeason: '2025/2026'
      },
      pendingMatches: [{ match_id: `${index + 1}` }],
      desiredLimit: 1
    }));

    const flow = {
      ...reconMatrixFlow,
      defaultReconConcurrency: 22,
      leagueParallelism: 22,
      reconBatchSize: 25,
      confidenceThreshold: 0.75,
      logger: { info() {}, warn() {}, error() {} },
      navigatorFactory: async () => {
        const port = nextPort++;
        return {
          proxyPort: port,
          ownsNavigator: true,
          navigator: {
            proxy: { port },
            async ensureBrowserHealthy() {},
            async close() {}
          }
        };
      },
      buildScanTargets: async () => preparedTargets.map((item) => item.target),
      taskPlanner: {
        prepareReconPendingTargets: async () => preparedTargets
      },
      _runReconTarget: async (target, options = {}) => {
        active++;
        maxActive = Math.max(maxActive, active);
        workerStarts.push({
          league: target.league.name,
          port: options.navigator?.proxy?.port || null
        });
        await new Promise((resolve) => {
          setTimeout(resolve, 25);
        });
        active--;
        return {
          pendingTotal: 1,
          linked: 1,
          mismatched: 0,
          sourceSeason: '2025/2026',
          sourceUrl: 'oddsportal://results/',
          candidateCount: 1
        };
      }
    };

    const result = await flow.runReconMatrix({
      season: '2025/2026',
      concurrency: 1,
      leagueConcurrency: 2,
      limit: 3
    });

    assert.equal(maxActive, 2);
    assert.deepStrictEqual(workerStarts, [
      { league: 'Premier League', port: 7890 },
      { league: 'Serie A', port: 7891 },
      { league: 'Bundesliga', port: 7892 }
    ]);
    assert.equal(result.scannedLeagues, 3);
    assert.equal(result.linked, 3);
  });

  it('未显式传入 leagueConcurrency 时，应默认复用请求的 concurrency 而不是退回配置值', async () => {
    let active = 0;
    let maxActive = 0;

    const preparedTargets = Array.from({ length: 6 }, (_, index) => ({
      target: {
        leagueId: index + 1,
        league: { id: index + 1, name: `League-${index + 1}` },
        dbSeason: '2025/2026'
      },
      pendingMatches: [{ match_id: `${index + 1}` }],
      desiredLimit: 1
    }));

    const flow = {
      ...reconMatrixFlow,
      defaultReconConcurrency: 5,
      leagueParallelism: 2,
      reconBatchSize: 25,
      confidenceThreshold: 0.75,
      logger: { info() {}, warn() {}, error() {} },
      navigatorFactory: async () => ({
        proxyPort: null,
        ownsNavigator: true,
        navigator: {
          async ensureBrowserHealthy() {},
          async close() {}
        }
      }),
      buildScanTargets: async () => preparedTargets.map((item) => item.target),
      taskPlanner: {
        prepareReconPendingTargets: async () => preparedTargets
      },
      _runReconTarget: async () => {
        active++;
        maxActive = Math.max(maxActive, active);
        await new Promise((resolve) => {
          setTimeout(resolve, 25);
        });
        active--;
        return {
          pendingTotal: 1,
          linked: 1,
          mismatched: 0,
          sourceSeason: '2025/2026',
          sourceUrl: 'oddsportal://results/',
          candidateCount: 1
        };
      }
    };

    await flow.runReconMatrix({
      season: '2025/2026',
      concurrency: 6,
      limit: 6
    });

    assert.equal(maxActive, 6);
  });
});
