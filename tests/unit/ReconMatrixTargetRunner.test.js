'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');

const { reconMatrixTargetRunner } = require('../../src/infrastructure/recon/services/ReconMatrixTargetRunner');

function createLogger() {
  const events = {
    info: [],
    warn: [],
  };

  return {
    events,
    logger: {
      info(event, payload) {
        events.info.push({ event, payload });
      },
      warn(event, payload) {
        events.warn.push({ event, payload });
      },
      error() {},
    },
  };
}

function createRunner(overrides = {}) {
  const { events, logger } = createLogger();
  return {
    ...reconMatrixTargetRunner,
    logger,
    defaultReconConcurrency: 2,
    confidenceThreshold: 0.75,
    minimumConfidenceThreshold: 0.7,
    forceDomMode: false,
    allNonLinked: false,
    navigator: { id: 'shared' },
    taskPlanner: {
      async loadReconPendingMatches() {
        return [
          { match_id: 'm2', pipeline_status: 'pending' },
          { match_id: 'm1', pipeline_status: 'pending' },
          { match_id: 'm3', pipeline_status: 'pending' },
        ];
      },
      resolveReconPolicy() {
        return {
          effectiveConfidenceThreshold: 0.82,
          allowMismatchRetry: true,
        };
      },
      formatSeasonForUrl(season) {
        return `fmt:${season}`;
      },
    },
    mirrorManager: {
      buildSeasonMirror(candidates = []) {
        return new Map(candidates.map(candidate => [candidate.match_id, candidate]));
      },
    },
    async _primeLeagueDictionary() {
      return [{ remote_name: 'Alpha', local_team_name: 'Alpha' }];
    },
    async _probeResultsCandidateSource(_target, pendingMatches) {
      return {
        source: { season: '2025/2026', url: 'results://mls' },
        extractResult: { sourceState: 'SOURCE_READY' },
        candidates: pendingMatches.slice(0, 2).map(match => ({ match_id: match.match_id })),
        seasonMirror: new Map(),
        sampleLinked: 2,
      };
    },
    _resolveScopedPendingMatches(pendingMatches, matchLimit) {
      if (!Number.isInteger(matchLimit) || matchLimit <= 0) {
        return pendingMatches;
      }

      return pendingMatches.slice(0, matchLimit);
    },
    _createReconRunId() {
      return 'recon-run-1';
    },
    _buildRouteProbeSample(pendingMatches = []) {
      return pendingMatches.slice(0, 4);
    },
    _canUseLocalDictionaryFallback() {
      return false;
    },
    _buildLocalDictionarySelectedSource(runtimeTarget, pendingMatches, sourceState) {
      return {
        source: { season: runtimeTarget?.dbSeason || null, url: 'dictionary://recon' },
        extractResult: { sourceState },
        localFallbackCandidateCount: pendingMatches.length,
        candidates: pendingMatches.map(match => ({ match_id: match.match_id, source: 'local_dictionary' })),
      };
    },
    async _processPendingMatchesWithShortCircuit(_routeKind, routeSource, pendingMatches, _runtimeTarget, options = {}) {
      const linked = options.finalPass === true ? 0 : Math.min(1, pendingMatches.length);
      return {
        linked,
        mismatched: linked === 0 ? pendingMatches.length : 0,
        remainingPending: linked > 0 ? pendingMatches.slice(1) : [],
      };
    },
    async _probeFixturesCandidateSource() {
      return {
        source: { season: '2025/2026', url: 'fixtures://mls' },
        extractResult: { sourceState: 'FIXTURES_READY' },
        candidates: [{ match_id: 'm2' }],
      };
    },
    async _probeSearchCandidateSource() {
      return {
        source: { season: '2025/2026', url: 'search://mls' },
        extractResult: { sourceState: 'SEARCH_READY' },
        candidates: [{ match_id: 'm3' }],
      };
    },
    __events: events,
    ...overrides,
  };
}

describe('ReconMatrixTargetRunner', () => {
  it('_prepareReconTargetState 应构建运行时目标与短路阈值', async () => {
    const runner = createRunner();

    const state = await runner._prepareReconTargetState(
      {
        season: '2025/2026',
        dbSeason: '2025/2026',
        resultsUrl: 'results://mls',
        league: { name: 'MLS' },
      },
      {
        concurrency: 3,
        matchLimit: 2,
        matrixModePruning: true,
        matrixModeShortCircuitRatio: 0.5,
        disableSearchRoute: true,
      }
    );

    assert.equal(state.progress.total, 2);
    assert.equal(state.effectiveThreshold, 0.82);
    assert.equal(state.runtimeTarget.disableSearchRoute, true);
    assert.equal(state.runtimeTarget.leagueDictionaryEntries.length, 1);
    assert.equal(state.routeSampleTarget, 2);
    assert.equal(state.routeShortCircuitThreshold, 1);
    assert.ok(typeof state.limiter === 'function');
  });

  it('_prepareReconTargetState 在无待处理或 scopedPending 为空时应返回 null', async () => {
    const emptyRunner = createRunner({
      taskPlanner: {
        async loadReconPendingMatches() {
          return [];
        },
      },
    });
    assert.equal(
      await emptyRunner._prepareReconTargetState({ dbSeason: '2025/2026', league: { name: 'MLS' } }),
      null
    );

    const scopedRunner = createRunner({
      _resolveScopedPendingMatches() {
        return [];
      },
    });
    assert.equal(
      await scopedRunner._prepareReconTargetState({ dbSeason: '2025/2026', league: { name: 'MLS' } }),
      null
    );
  });

  it('_resolveRouteShortCircuitThreshold 应在 Matrix 模式下按比例计算并做边界收敛', () => {
    const runner = createRunner({
      _buildRouteProbeSample() {
        return [{}, {}, {}, {}];
      },
    });

    assert.equal(runner._resolveRouteShortCircuitThreshold([1, 2, 3], { matrixModePruning: false }), 4);
    assert.equal(
      runner._resolveRouteShortCircuitThreshold([1, 2, 3], { matrixModePruning: true, matrixModeShortCircuitRatio: 0.25 }),
      1
    );
    assert.equal(
      runner._resolveRouteShortCircuitThreshold([1, 2, 3], { matrixModePruning: true, matrixModeShortCircuitRatio: 'bad' }),
      2
    );
  });

  it('_assertLeagueBudget 在超时且尚未产出时应抛出 LEAGUE_TIMEOUT', () => {
    const runner = createRunner();

    assert.throws(
      () => runner._assertLeagueBudget(
        { leagueDeadlineAt: Date.now() - 10, league: { name: 'MLS' }, dbSeason: '2025/2026' },
        { totalLinked: 0, remainingRoutePending: [{ match_id: 'm1' }] },
        'before_search'
      ),
      error => error?.code === 'LEAGUE_TIMEOUT' && error?.stage === 'before_search'
    );
  });

  it('_assertLeagueBudget 在已有产出时应返回 true 并记录告警', () => {
    const runner = createRunner();

    const exhausted = runner._assertLeagueBudget(
      { leagueDeadlineAt: Date.now() - 10, league: { name: 'MLS' }, dbSeason: '2025/2026' },
      { totalLinked: 2, remainingRoutePending: [{ match_id: 'm1' }] },
      'after_results'
    );

    assert.equal(exhausted, true);
    assert.equal(runner.__events.warn[0].event, 'recon_league_timeout');
  });

  it('_shouldFinalizeAfterResults 应在 Matrix 剪枝命中时提前收口', () => {
    const runner = createRunner();

    assert.equal(runner._shouldFinalizeAfterResults({
      remainingRoutePending: [{ match_id: 'm2' }],
      runtimeTarget: { matrixModePruning: true },
      resultsSource: {
        candidates: [],
        sampleLinked: 0,
      },
      routeShortCircuitThreshold: 1,
    }), true);

    assert.equal(runner._shouldFinalizeAfterResults({
      remainingRoutePending: [{ match_id: 'm2' }],
      runtimeTarget: { matrixModePruning: true },
      resultsSource: {
        candidates: [{ match_id: 'm1' }],
        sampleLinked: 2,
      },
      routeShortCircuitThreshold: 2,
    }), true);
  });

  it('_handlePostResultsFlow 在预算耗尽时应立即 finalize', async () => {
    const calls = [];
    const runner = createRunner({
      _assertLeagueBudget() {
        return true;
      },
      async _finalizeRemainingPending(routeState) {
        calls.push(routeState.remainingRoutePending.length);
      },
    });

    const handled = await runner._handlePostResultsFlow({
      runtimeTarget: { leagueDeadlineAt: Date.now() - 10 },
      remainingRoutePending: [{ match_id: 'm2' }],
      totalLinked: 1,
      target: { league: { name: 'MLS' }, dbSeason: '2025/2026' },
    });

    assert.equal(handled, true);
    assert.deepEqual(calls, [1]);
  });

  it('_runPostResultsFallbackRoutes 在禁用 search 时应记录日志并走结果终态', async () => {
    const calls = [];
    const runner = createRunner({
      async _runReconFixturesRoute(routeState) {
        calls.push(`fixtures:${routeState.remainingRoutePending.length}`);
      },
      async _finalizeRemainingPending(routeState) {
        calls.push(`finalize:${routeState.remainingRoutePending.length}`);
      },
    });

    await runner._runPostResultsFallbackRoutes({
      target: { league: { name: 'MLS' }, dbSeason: '2025/2026' },
      runtimeTarget: { disableSearchRoute: true },
      remainingRoutePending: [{ match_id: 'm2' }],
    });

    assert.deepEqual(calls, ['fixtures:1', 'finalize:1']);
    assert.equal(runner.__events.info[0].event, 'recon_search_route_skipped');
  });

  it('_runPostResultsFallbackRoutes 在 results-only 模式时应跳过全部慢速路径', async () => {
    const calls = [];
    const runner = createRunner({
      async _runReconFixturesRoute() {
        calls.push('fixtures');
      },
      async _runReconSearchRoute() {
        calls.push('search');
      },
      async _runReconLocalDictionaryRoute() {
        calls.push('local_dictionary');
      },
      async _finalizeRemainingPending(routeState) {
        calls.push(`finalize:${routeState.remainingRoutePending.length}`);
      },
    });

    await runner._runPostResultsFallbackRoutes({
      target: { league: { name: 'MLS' }, dbSeason: '2025/2026' },
      runtimeTarget: { resultsOnlyMode: true, disableSearchRoute: true },
      remainingRoutePending: [{ match_id: 'm2' }, { match_id: 'm3' }],
    });

    assert.deepEqual(calls, ['finalize:2']);
    assert.equal(runner.__events.info[0].event, 'recon_results_only_finalize');
  });

  it('_runPostResultsFallbackRoutes 在 results-only 模式遇到残缺 results source 时应抛错重试', async () => {
    const calls = [];
    const runner = createRunner({
      async _finalizeRemainingPending() {
        calls.push('finalize');
      },
    });

    await assert.rejects(
      runner._runPostResultsFallbackRoutes({
        target: { league: { name: 'Premier League' }, dbSeason: '2025/2026' },
        runtimeTarget: { resultsOnlyMode: true, disableSearchRoute: true },
        remainingRoutePending: [{ match_id: 'm2' }, { match_id: 'm3' }],
        resultsSource: {
          source: { season: '2025/2026', url: 'results://premier-league' },
          extractResult: {
            sourceState: 'PURE_PROTOCOL',
            sourceIncomplete: true
          },
          sourceHealth: {
            incomplete: true,
            incompleteReasons: ['page_failure']
          }
        }
      }),
      (error) => {
        assert.equal(error.code, 'RECON_SOURCE_INCOMPLETE');
        assert.deepEqual(error.incompleteReasons, ['page_failure']);
        return true;
      }
    );

    assert.deepEqual(calls, []);
    assert.equal(runner.__events.warn[0].event, 'recon_results_only_incomplete_source_retry');
  });

  it('_applyReconRouteResult 应累计 route 结果并刷新最终源信息', () => {
    const runner = createRunner();
    const routeState = {
      totalLinked: 1,
      totalMismatched: 2,
      totalCandidateCount: 1,
      remainingRoutePending: [{ match_id: 'm2' }],
      finalSourceSeason: null,
      finalSourceUrl: null,
      lastSourceState: 'SOURCE_EMPTY',
    };

    runner._applyReconRouteResult(routeState, {
      linked: 2,
      mismatched: 1,
      remainingPending: [{ match_id: 'm3' }],
    }, {
      source: { season: '2025/2026', url: 'fixtures://mls' },
      extractResult: { sourceState: 'FIXTURES_READY' },
      localFallbackCandidateCount: 4,
      candidates: [{}, {}],
    });

    assert.equal(routeState.totalLinked, 3);
    assert.equal(routeState.totalMismatched, 3);
    assert.equal(routeState.totalCandidateCount, 5);
    assert.deepEqual(routeState.remainingRoutePending, [{ match_id: 'm3' }]);
    assert.equal(routeState.finalSourceSeason, '2025/2026');
    assert.equal(routeState.finalSourceUrl, 'fixtures://mls');
    assert.equal(routeState.lastSourceState, 'FIXTURES_READY');
  });

  it('_processReconRoute 应为缺失 routeSource 兜底空源并透传终态选项', async () => {
    const captured = [];
    const runner = createRunner({
      _buildEmptyRouteSource(routeKind, target, sourceState) {
        return {
          source: { season: target?.dbSeason || null, url: `empty://${routeKind}` },
          extractResult: { sourceState },
          candidates: [],
        };
      },
      async _processPendingMatchesWithShortCircuit(routeKind, routeSource, pendingMatches, runtimeTarget, options) {
        captured.push({ routeKind, routeSource, pendingMatches, runtimeTarget, options });
        return { linked: 0, mismatched: 1, remainingPending: [] };
      },
    });

    const routeState = {
      runtimeTarget: { dbSeason: '2025/2026' },
      remainingRoutePending: [{ match_id: 'm1' }],
      effectiveThreshold: 0.82,
      limiter: () => {},
      persistLimiter: () => {},
      progress: { total: 1 },
      routeMetadata: { reconRunId: 'recon-run-1' },
      totalLinked: 0,
      totalMismatched: 0,
      totalCandidateCount: 0,
      finalSourceSeason: null,
      finalSourceUrl: null,
      lastSourceState: 'SOURCE_EMPTY',
    };

    await runner._processReconRoute(routeState, 'search', null, {
      finalPass: true,
      forceProcessWithoutCandidates: true,
    });

    assert.equal(captured[0].routeKind, 'search');
    assert.equal(captured[0].options.finalPass, true);
    assert.equal(captured[0].options.forceProcessWithoutCandidates, true);
    assert.equal(routeState.totalMismatched, 1);
  });

  it('_runReconTarget 应产出最终结果，未收口时应抛出带源信息的错误', async () => {
    const runner = createRunner({
      async _runReconTargetRoutes(routeState) {
        routeState.totalLinked = 2;
        routeState.totalMismatched = 1;
        routeState.totalCandidateCount = 3;
        routeState.remainingRoutePending = [];
        routeState.finalSourceSeason = '2025/2026';
        routeState.finalSourceUrl = 'results://mls';
      },
    });

    const result = await runner._runReconTarget({
      season: '2025/2026',
      dbSeason: '2025/2026',
      resultsUrl: 'results://mls',
      league: { name: 'MLS' },
    });

    assert.deepEqual(result, {
      pendingTotal: 3,
      linked: 2,
      mismatched: 1,
      sourceSeason: '2025/2026',
      sourceUrl: 'results://mls',
      candidateCount: 3,
      effectiveConfidenceThreshold: 0.82,
    });

    const failingRunner = createRunner({
      async _runReconTargetRoutes() {},
    });

    await assert.rejects(
      failingRunner._runReconTarget({
        season: '2025/2026',
        dbSeason: '2025/2026',
        resultsUrl: 'results://mls',
        league: { name: 'MLS' },
      }),
      error => error?.code === 'SOURCE_READY' && error?.sourceUrl === 'results://mls'
    );
  });
});
