'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');

const { reconTaskPlannerUrlUtils } = require('../../src/infrastructure/recon/services/ReconTaskPlannerUrlUtils');
const { reconTaskPlannerSourceSelector } = require('../../src/infrastructure/recon/services/ReconTaskPlannerSourceSelector');

function createContext(overrides = {}) {
  const events = {
    info: [],
    warn: []
  };

  return {
    ...reconTaskPlannerUrlUtils,
    ...reconTaskPlannerSourceSelector,
    archiveTimeoutMs: 12000,
    sampleSize: 2,
    forceDomLeagueIds: new Set(),
    logger: {
      info(event, payload) {
        events.info.push({ event, payload });
      },
      warn(event, payload) {
        events.warn.push({ event, payload });
      }
    },
    mirrorManager: {
      buildSeasonMirror() {
        return new Map();
      }
    },
    matchEvaluator: {
      findBestCandidate(match, candidates) {
        return candidates.find((candidate) => candidate.match_id === match.match_id) || null;
      }
    },
    resolveReconPolicy() {
      return {
        effectiveConfidenceThreshold: 0.75,
        forceMultiMode: false
      };
    },
    resolveArchiveMaxPages() {
      return 50;
    },
    buildCircuitBreakerKey() {
      return 'recon:test';
    },
    __events: events,
    ...overrides
  };
}

describe('ReconTaskPlannerSourceSelector', () => {
  it('buildCandidateSources 应跳过空 URL 与重复 URL', () => {
    const context = createContext({
      getResultsUrlStrategy() {
        return 'seasonless';
      },
      getSeasonlessCurrentYearBasis() {
        return 'end';
      },
      buildCurrentSeasonSourceUrls() {
        return ['oddsportal://current', 'oddsportal://current', ''];
      },
      buildHistoricalSeasonSourceUrls() {
        return ['oddsportal://2024', ''];
      }
    });

    const sources = context.buildCandidateSources({
      league: { id: 130, seasonType: 'single_year' },
      season: '2025-2026',
      dbSeason: '2025/2026',
      pendingMatches: [{ match_date: '2024-03-01T00:00:00.000Z' }]
    });

    assert.deepEqual(sources, [
      {
        season: '2026',
        url: 'oddsportal://current',
        mode: 'current_season'
      },
      {
        season: '2024',
        url: 'oddsportal://2024',
        mode: 'historical_results'
      }
    ]);
  });

  it('selectCandidateSource 在 navigator 缺失时应直接抛错', async () => {
    const context = createContext({ navigator: null });

    await assert.rejects(
      context.selectCandidateSource({
        league: { name: 'MLS' },
        dbSeason: '2025/2026',
        season: '2025-2026',
        resultsUrl: 'oddsportal://root/results/'
      }, [], 0.75),
      /ReconTaskPlanner requires a navigator/
    );
  });

  it('forcePureProtocol 应强制走 protocolArchiveExtract', async () => {
    const calls = [];
    const context = createContext({
      navigator: {
        async protocolArchiveExtract(url, options) {
          calls.push({ url, options });
          return {
            matches: [{ match_id: '130_20252026_0001', confidence: 0.9 }],
            pagesScanned: 1,
            totalCandidates: 1,
            sourceState: 'SOURCE_READY'
          };
        }
      },
      buildCandidateSources() {
        return [{ season: '2025-2026', url: 'oddsportal://pure', mode: 'current_season' }];
      }
    });

    await context.selectCandidateSource({
      leagueId: 130,
      league: { id: 130, name: 'MLS' },
      dbSeason: '2025/2026',
      season: '2025-2026',
      resultsUrl: 'oddsportal://root/results/',
      forcePureProtocol: true
    }, [{
      match_id: '130_20252026_0001'
    }], 0.75);

    assert.deepEqual(calls, [{
      url: 'oddsportal://pure',
      options: {
        maxPages: 50,
        timeoutMs: 12000,
        preferCurrentSeasonSource: true,
        circuitBreakerKey: 'recon:test:current_season:2025-2026:0',
        forcePureProtocol: true
      }
    }]);
  });

  it('forceJsonExtract、forceDomOnly、forceDomLeague 与 forceMultiMode 分支应透传对应选项', async () => {
    const calls = [];
    const context = createContext({
      navigator: {
        async fetchFullSeasonArchive(url, options) {
          calls.push({ url, options });
          return {
            matches: [],
            pagesScanned: 0,
            totalCandidates: 0,
            sourceState: 'SOURCE_EMPTY'
          };
        }
      },
      buildCandidateSources() {
        return [{ season: '2025-2026', url: 'oddsportal://archive', mode: 'results_archive' }];
      }
    });

    await context.selectCandidateSource({
      leagueId: 130,
      league: { id: 130, name: 'MLS' },
      dbSeason: '2025/2026',
      season: '2025-2026',
      resultsUrl: 'oddsportal://root/results/',
      forceJsonExtract: true
    }, [], 0.75);

    await context.selectCandidateSource({
      leagueId: 130,
      league: { id: 130, name: 'MLS' },
      dbSeason: '2025/2026',
      season: '2025-2026',
      resultsUrl: 'oddsportal://root/results/',
      forceDomMode: true
    }, [], 0.75);

    context.forceDomLeagueIds = new Set([130]);
    await context.selectCandidateSource({
      leagueId: 130,
      league: { id: 130, name: 'MLS' },
      dbSeason: '2025/2026',
      season: '2025-2026',
      resultsUrl: 'oddsportal://root/results/'
    }, [], 0.75);

    context.resolveReconPolicy = () => ({
      effectiveConfidenceThreshold: 0.75,
      forceMultiMode: true
    });
    context.forceDomLeagueIds = new Set();
    await context.selectCandidateSource({
      leagueId: 130,
      league: { id: 130, name: 'MLS' },
      dbSeason: '2025/2026',
      season: '2025-2026',
      resultsUrl: 'oddsportal://root/results/'
    }, [], 0.75);

    assert.equal(calls.length, 4);
    assert.equal(calls[0].options.forceJsonExtract, true);
    assert.equal(calls[0].options.forceDomOnly, true);
    assert.equal(calls[1].options.forceDomOnly, true);
    assert.equal(calls[2].options.preferCurrentSeasonSource, true);
    assert.equal(calls[3].options.preferCurrentSeasonSource, true);
  });

  it('非 forceMultiMode 下应返回最佳 results source，而不是盲目合并所有候选', async () => {
    const calls = [];
    const context = createContext({
      navigator: {
        async fetchFullSeasonArchive(url) {
          calls.push(url);
          if (url === 'oddsportal://results-primary') {
            return {
              matches: [{ match_id: '47_20252026_0001', hash: 'h1', url, confidence: 1 }],
              pagesScanned: 1,
              totalCandidates: 1,
              sourceState: 'SOURCE_READY'
            };
          }

          return {
            matches: [{ match_id: 'noise-only', hash: 'h2', url, confidence: 0.1 }],
            pagesScanned: 1,
            totalCandidates: 1,
            sourceState: 'SOURCE_READY'
          };
        }
      },
      buildCandidateSources() {
        return [
          { season: '2025-2026', url: 'oddsportal://results-primary', mode: 'results_archive' },
          { season: '2025-2026', url: 'oddsportal://results-secondary', mode: 'historical_results' }
        ];
      }
    });

    const result = await context.selectCandidateSource({
      leagueId: 47,
      league: { id: 47, name: 'Premier League' },
      dbSeason: '2025/2026',
      season: '2025-2026',
      resultsUrl: 'oddsportal://root/results/'
    }, [{
      match_id: '47_20252026_0001'
    }], 0.75);

    assert.deepEqual(calls, ['oddsportal://results-primary', 'oddsportal://results-secondary']);
    assert.equal(result.source.url, 'oddsportal://results-primary');
    assert.equal(result.candidates.length, 1);
    assert.equal(result.sampleLinked, 1);
  });

  it('所有 source 均失败时应聚合 sourceFailures 并抛出首个错误', async () => {
    const context = createContext({
      navigator: {
        async fetchFullSeasonArchive() {
          throw new Error('archive exploded');
        }
      },
      buildCandidateSources() {
        return [{ season: '2025-2026', url: 'oddsportal://archive', mode: 'results_archive' }];
      }
    });

    await assert.rejects(
      context.selectCandidateSource({
        leagueId: 47,
        league: { id: 47, name: 'Premier League' },
        dbSeason: '2025/2026',
        season: '2025-2026',
        resultsUrl: 'oddsportal://root/results/'
      }, [], 0.75),
      (error) => {
        assert.equal(error.message, 'archive exploded');
        assert.deepEqual(error.sourceFailures, [{
          sourceSeason: '2025-2026',
          sourceUrl: 'oddsportal://archive',
          breakerKey: 'recon:test:results_archive:2025-2026:0',
          error: 'archive exploded'
        }]);
        return true;
      }
    );
    assert.equal(context.__events.warn.length, 1);
  });

  it('无可评估 source 时应回退到 SOURCE_EMPTY 默认结果', async () => {
    const context = createContext({
      navigator: {
        async fetchFullSeasonArchive() {
          return { matches: [] };
        }
      },
      buildCandidateSources() {
        return [];
      }
    });

    const result = await context.selectCandidateSource({
      leagueId: 47,
      league: { id: 47, name: 'Premier League' },
      dbSeason: '2025/2026',
      season: '2025-2026',
      resultsUrl: 'oddsportal://root/results/'
    }, [], 0.75);

    assert.deepEqual(await context.navigator.fetchFullSeasonArchive(), { matches: [] });

    assert.deepEqual(result, {
      source: {
        season: '2025-2026',
        url: 'oddsportal://root/results/'
      },
      extractResult: {
        matches: [],
        pagesScanned: 0,
        totalCandidates: 0,
        sourceState: 'SOURCE_EMPTY'
      },
      candidates: [],
      seasonMirror: new Map(),
      sampleLinked: 0
    });
  });
});
