/* eslint-disable max-lines */
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');

const { reconSourceProber } = require('../../src/infrastructure/recon/services/ReconSourceProber');
const { Normalizer } = require('../../src/utils/Normalizer');

function createLogger() {
  const events = {
    info: [],
    warn: [],
    debug: [],
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
      debug(event, payload) {
        events.debug.push({ event, payload });
      },
    },
  };
}

function createProber(overrides = {}) {
  const { events, logger } = createLogger();
  return {
    ...reconSourceProber,
    logger,
    navigator: null,
    navigatorFactory: null,
    archiveMaxPages: 40,
    pageSettleWaitMs: 3,
    taskPlanner: {
      selectCandidateSource: async (target) => ({
        source: {
          season: target?.dbSeason || null,
          url: target?.resultsUrl || 'results://default',
        },
        extractResult: {
          matches: [],
          pagesScanned: 1,
          totalCandidates: 0,
          sourceState: 'SOURCE_EMPTY',
        },
        candidates: [],
        seasonMirror: new Map(),
        sampleLinked: 0,
      }),
      buildFixturesUrl: () => '',
      resolveArchiveMaxPages: () => 25,
      buildCircuitBreakerKey: () => 'recon:test',
    },
    _resolveAvailableProxyCount: () => 0,
    _resolveRouteProbeTimeoutMs: () => 1200,
    _resetRouteFailureStreak() {},
    _recordRouteProbeFailure(_target, _routeKind, _error, metadata = {}) {
      return {
        shouldDegrade: false,
        sourceState: 'ROUTE_PROBE_FAILED',
        searchBlocked: false,
        signals: {},
        metadata,
      };
    },
    _buildEmptyRouteSource(routeKind, target, sourceState) {
      return {
        routeKind,
        source: {
          season: target?.dbSeason || null,
          url: target?.resultsUrl || '',
        },
        extractResult: {
          matches: [],
          pagesScanned: 0,
          totalCandidates: 0,
          sourceState,
        },
        candidates: [],
        seasonMirror: new Map(),
        sampleLinked: 0,
      };
    },
    _buildDegradedRouteSource(routeKind, target, sourceState, error, metadata = {}) {
      return {
        routeKind,
        source: {
          season: target?.dbSeason || null,
          url: target?.resultsUrl || '',
        },
        extractResult: {
          matches: [],
          pagesScanned: 0,
          totalCandidates: 0,
          sourceState,
        },
        candidates: [],
        seasonMirror: new Map(),
        sampleLinked: 0,
        error: error?.message || '',
        metadata,
      };
    },
    _buildSeasonMirror(candidates = []) {
      return new Map(
        candidates.map(candidate => [candidate.match_id || candidate.hash || candidate.url, candidate])
      );
    },
    _scoreCandidatePoolSample(pendingMatches = [], candidates = []) {
      const candidateIds = new Set(
        candidates
          .map(candidate => candidate.match_id)
          .filter(Boolean)
      );
      return pendingMatches.filter(match => candidateIds.has(match.match_id)).length;
    },
    _buildRouteProbeSample(pendingMatches = []) {
      return pendingMatches.slice(0, 4);
    },
    _acquireTargetNavigator: async () => ({ navigator: null }),
    _releaseTargetNavigator: async () => {},
    _isSearchProbeBlocked: () => false,
    _canUseLocalDictionaryFallback: () => false,
    _buildLocalDictionarySelectedSource(target, pendingMatches, sourceState) {
      return {
        routeKind: 'local_dictionary',
        source: {
          season: target?.dbSeason || null,
          url: 'dictionary://recon',
        },
        extractResult: {
          matches: pendingMatches,
          pagesScanned: 0,
          totalCandidates: pendingMatches.length,
          sourceState,
        },
        localFallbackCandidateCount: pendingMatches.length,
        candidates: pendingMatches.map(match => ({
          match_id: match.match_id,
          source: 'local_dictionary',
        })),
        seasonMirror: new Map(),
        sampleLinked: pendingMatches.length,
      };
    },
    _buildFallbackEventSlug(homeTeam, awayTeam) {
      const slugify = (value) => String(Normalizer.normalizeTeamName(value) || value || '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '');
      const homeSlug = slugify(homeTeam);
      const awaySlug = slugify(awayTeam);
      return homeSlug && awaySlug ? `${homeSlug}-${awaySlug}` : '';
    },
    _resolveTrustedOddsPortalBaseUrl() {
      return 'https://www.oddsportal.com';
    },
    __events: events,
    ...overrides,
  };
}

describe('ReconSourceProber', () => {
  it('_dedupeCandidatesByIdentity 应按 hash/url 去重并忽略空候选', () => {
    const prober = createProber();

    const deduped = prober._dedupeCandidatesByIdentity([
      { hash: 'abc12345', url: 'https://example.com/a' },
      { hash: 'abc12345', url: 'https://example.com/a-dup' },
      { url: 'https://example.com/b' },
      { url: 'https://example.com/b' },
      { hash: '', url: '' },
    ]);

    assert.deepEqual(deduped, [
      { hash: 'abc12345', url: 'https://example.com/a' },
      { url: 'https://example.com/b' },
    ]);
  });

  it('_canRunParallelRouteProbes 应要求 navigatorFactory 与足够代理', () => {
    const prober = createProber();
    assert.equal(prober._canRunParallelRouteProbes(), false);

    prober.navigatorFactory = () => ({});
    prober._resolveAvailableProxyCount = () => 2;

    assert.equal(prober._canRunParallelRouteProbes(), true);
  });

  it('_combineCandidateRouteSources 应整合成功路由并保留元信息', () => {
    const prober = createProber();
    const target = {
      dbSeason: '2025/2026',
      resultsUrl: 'results://mls',
      league: { name: 'MLS' },
    };

    const combined = prober._combineCandidateRouteSources([
      {
        routeKind: 'results',
        source: { season: '2025/2026', url: 'results://mls' },
        extractResult: { pagesScanned: 2, sourceState: 'SOURCE_READY' },
        candidates: [{ match_id: 'm1', hash: 'AAAA1111' }],
        sampleLinked: 1,
      },
      {
        routeKind: 'fixtures',
        source: { season: '2025/2026', url: 'fixtures://mls' },
        extractResult: { pagesScanned: 1, sourceState: 'FIXTURES_SWEEP_READY' },
        candidates: [{ match_id: 'm2', hash: 'BBBB2222' }],
        sampleLinked: 1,
      },
    ], target, [{ match_id: 'm1' }, { match_id: 'm2' }], 0.75);

    assert.equal(combined.routeKind, 'combined');
    assert.equal(combined.extractResult.totalCandidates, 2);
    assert.equal(combined.extractResult.pagesScanned, 3);
    assert.equal(combined.sampleLinked, 2);
    assert.deepEqual(combined.routeKinds, ['results', 'fixtures']);
    assert.equal(prober.__events.info[0].event, 'recon_candidate_routes_combined');
  });

  it('_combineCandidateRouteSources 在无成功路由时应回退到空结果源', () => {
    const prober = createProber();

    const combined = prober._combineCandidateRouteSources([], {
      dbSeason: '2025/2026',
      resultsUrl: 'results://mls',
    }, [], 0.75);

    assert.equal(combined.extractResult.sourceState, 'SOURCE_EMPTY');
    assert.equal(combined.routeKind, 'results');
  });

  it('_probeCandidateRoutes 在 Matrix 剪枝且 results 为空时应直接短路', async () => {
    const prober = createProber({
      _probeResultsCandidateSource: async () => ({
        routeKind: 'results',
        source: { season: '2025/2026', url: 'results://mls' },
        extractResult: { pagesScanned: 1, totalCandidates: 0, sourceState: 'SOURCE_EMPTY' },
        candidates: [],
        seasonMirror: new Map(),
        sampleLinked: 0,
      }),
      _probeFixturesCandidateSource: async () => {
        throw new Error('fixtures should not run');
      },
      _probeSearchCandidateSource: async () => {
        throw new Error('search should not run');
      },
    });

    const combined = await prober._probeCandidateRoutes(
      { league: { name: 'MLS' }, dbSeason: '2025/2026', matrixModePruning: true },
      [{ match_id: 'm1' }],
      0.75
    );

    assert.deepEqual(combined.routeKinds, ['results']);
    assert.equal(combined.extractResult.sourceState, 'SOURCE_EMPTY');
    assert.equal(prober.__events.info[0].event, 'recon_candidate_routes_short_circuit');
  });

  it('_probeCandidateRoutes 在前移短路标记命中时应跳过 fixtures 并继续 search', async () => {
    const prober = createProber({
      _probeResultsCandidateSource: async () => ({
        routeKind: 'results',
        source: { season: '2025/2026', url: 'results://j1' },
        extractResult: { pagesScanned: 1, totalCandidates: 0, sourceState: 'SOURCE_EMPTY' },
        candidates: [],
        seasonMirror: new Map(),
        sampleLinked: 0,
        forceSearchShortCircuit: true,
        probeDurationMs: 20000,
        shortCircuitTimeoutMs: 20000,
      }),
      _probeFixturesCandidateSource: async () => {
        throw new Error('fixtures should be skipped');
      },
      _probeSearchCandidateSource: async () => ({
        routeKind: 'search',
        source: { season: '2025/2026', url: 'search://j1' },
        extractResult: { pagesScanned: 1, totalCandidates: 1, sourceState: 'SEARCH_SWEEP_READY' },
        candidates: [{ match_id: 'm1', hash: 'AAAA1111' }],
        seasonMirror: new Map(),
        sampleLinked: 1,
      }),
    });

    const combined = await prober._probeCandidateRoutes(
      { league: { name: 'J1 League' }, dbSeason: '2025/2026', matrixModePruning: true },
      [{ match_id: 'm1' }],
      0.75
    );

    assert.deepEqual(combined.routeKinds, ['results', 'search']);
    assert.equal(combined.extractResult.totalCandidates, 1);
    assert.ok(
      prober.__events.info.some(({ event }) => event === 'recon_results_probe_search_short_circuit')
    );
  });

  it('_probeCandidateRoutes 在样本已满足阈值时应跳过 search', async () => {
    const prober = createProber({
      _canRunParallelRouteProbes: () => true,
      _probeResultsCandidateSource: async () => ({
        routeKind: 'results',
        source: { season: '2025/2026', url: 'results://mls' },
        extractResult: { pagesScanned: 1, totalCandidates: 1, sourceState: 'SOURCE_READY' },
        candidates: [{ match_id: 'm1', hash: 'AAAA1111' }],
        seasonMirror: new Map(),
        sampleLinked: 1,
      }),
      _probeFixturesCandidateSource: async () => ({
        routeKind: 'fixtures',
        source: { season: '2025/2026', url: 'fixtures://mls' },
        extractResult: { pagesScanned: 1, totalCandidates: 1, sourceState: 'FIXTURES_SWEEP_READY' },
        candidates: [{ match_id: 'm2', hash: 'BBBB2222' }],
        seasonMirror: new Map(),
        sampleLinked: 1,
      }),
      _probeSearchCandidateSource: async () => {
        throw new Error('search should be skipped after threshold');
      },
    });

    const combined = await prober._probeCandidateRoutes(
      { league: { name: 'MLS' }, dbSeason: '2025/2026', matrixModePruning: false },
      [{ match_id: 'm1' }, { match_id: 'm2' }],
      0.75
    );

    assert.equal(combined.extractResult.totalCandidates, 2);
    assert.ok(
      prober.__events.info.some(({ event }) => event === 'recon_candidate_routes_short_circuit')
    );
  });

  it('_probeCandidateRoutes 在多路全失败时应抛出聚合错误', async () => {
    const prober = createProber({
      _buildRouteProbeSample() {
        return [{ match_id: 'm1' }];
      },
      _probeResultsCandidateSource: async () => {
        const error = new Error('results failed');
        error.code = 'RESULTS_FAILED';
        throw error;
      },
      _probeFixturesCandidateSource: async () => {
        throw new Error('fixtures failed');
      },
      _probeSearchCandidateSource: async () => {
        throw new Error('search failed');
      },
    });

    await assert.rejects(
      prober._probeCandidateRoutes(
        { league: { name: 'MLS' }, dbSeason: '2025/2026', matrixModePruning: true, matrixModeShortCircuitRatio: 'bad' },
        [{ match_id: 'm1' }],
        0.75
      ),
      error => error?.message === 'results failed'
    );
  });

  it('_probeResultsCandidateSource 失败降级时应返回 degraded source', async () => {
    const prober = createProber({
      taskPlanner: {
        selectCandidateSource: async () => {
          throw new Error('boom');
        },
      },
      _recordRouteProbeFailure() {
        return {
          shouldDegrade: true,
          sourceState: 'RESULTS_DEGRADED',
          searchBlocked: true,
          signals: {},
        };
      },
    });

    const routeSource = await prober._probeResultsCandidateSource(
      { league: { name: 'MLS' }, dbSeason: '2025/2026', resultsUrl: 'results://mls' },
      [],
      0.75
    );

    assert.equal(routeSource.extractResult.sourceState, 'RESULTS_DEGRADED');
    assert.equal(routeSource.metadata.searchBlocked, true);
  });

  it('_probeResultsCandidateSource 遇到 LEAGUE_TIMEOUT 时应直接上抛', async () => {
    const timeoutError = new Error('timeout');
    timeoutError.code = 'LEAGUE_TIMEOUT';
    const prober = createProber({
      taskPlanner: {
        async selectCandidateSource() {
          throw timeoutError;
        },
      },
    });

    await assert.rejects(
      prober._probeResultsCandidateSource({ dbSeason: '2025/2026', league: { name: 'MLS' } }, [], 0.75),
      error => error === timeoutError
    );
  });

  it('_probeResultsCandidateSource 在 J1 results probe 超时后应返回强制 search 空源', async () => {
    const originalNow = Date.now;
    const navigatorOptions = [];
    const plannerCalls = [];
    Date.now = () => 1000;

    try {
      const prober = createProber({
        _resolveRouteProbeTimeoutMs: () => 25000,
        taskPlanner: {
          async selectCandidateSource(target, _pendingMatches, _confidenceThreshold, options) {
            plannerCalls.push({ target, options });
            const error = new Error('LEAGUE_TIMEOUT');
            error.code = 'LEAGUE_TIMEOUT';
            throw error;
          },
        },
        async _executeRouteProbeWithNavigator(_target, _navigator, options, probe) {
          navigatorOptions.push(options);
          return probe({ id: 'dedicated-nav' });
        },
      });

      const routeSource = await prober._probeResultsCandidateSource(
        { league: { name: 'J1 League' }, dbSeason: '2025/2026', resultsUrl: 'results://j1' },
        [{ match_id: 'm1' }],
        0.75
      );

      assert.equal(routeSource.routeKind, 'results');
      assert.equal(routeSource.forceSearchShortCircuit, true);
      assert.equal(routeSource.shortCircuitTimeoutMs, 20000);
      assert.equal(routeSource.extractResult.sourceState, 'SOURCE_EMPTY');
      assert.equal(navigatorOptions[0].useDedicatedNavigator, true);
      assert.equal(plannerCalls[0].target.leagueDeadlineAt, 21000);
      assert.equal(plannerCalls[0].options.leagueDeadlineAt, 21000);
    } finally {
      Date.now = originalNow;
    }
  });

  it('_probeResultsCandidateSource 在真实联赛预算先到期时不应伪装成 search 短路', async () => {
    const originalNow = Date.now;
    Date.now = () => 1000;

    try {
      const prober = createProber({
        _resolveRouteProbeTimeoutMs: () => 25000,
        taskPlanner: {
          async selectCandidateSource() {
            const error = new Error('LEAGUE_TIMEOUT');
            error.code = 'LEAGUE_TIMEOUT';
            throw error;
          }
        },
        async _executeRouteProbeWithNavigator(_target, _navigator, _options, probe) {
          return probe({ id: 'dedicated-nav' });
        }
      });

      await assert.rejects(
        () => prober._probeResultsCandidateSource(
          {
            league: { name: 'J1 League' },
            dbSeason: '2025/2026',
            resultsUrl: 'results://j1',
            leagueDeadlineAt: 5000
          },
          [{ match_id: 'm1' }],
          0.75
        ),
        (error) => error?.code === 'LEAGUE_TIMEOUT'
      );
    } finally {
      Date.now = originalNow;
    }
  });

  it('_probeFixturesCandidateSource 缺少 fixturesUrl 时应直接返回 null', async () => {
    const prober = createProber({
      taskPlanner: {
        buildFixturesUrl: () => '',
      },
    });

    const routeSource = await prober._probeFixturesCandidateSource(
      { dbSeason: '2025/2026', league: { name: 'MLS' } },
      [],
      0.75
    );

    assert.equal(routeSource, null);
  });

  it('_probeFixturesCandidateSource 应生成 fixtures route，并在异常时按策略降级', async () => {
    const prober = createProber({
      taskPlanner: {
        buildFixturesUrl: () => 'fixtures://mls',
      },
      async _executeRouteProbeWithNavigator(_target, _navigator, _options, probe) {
        return probe({
          async protocolArchiveExtract() {
            return {
              matches: [{ match_id: 'm1', hash: 'AAAA1111' }],
              pagesScanned: 2,
              totalCandidates: 1,
              sourceState: '',
            };
          },
        });
      },
    });

    const routeSource = await prober._probeFixturesCandidateSource(
      { dbSeason: '2025/2026', league: { name: 'MLS' } },
      [{ match_id: 'm1' }],
      0.75
    );

    assert.equal(routeSource.routeKind, 'fixtures');
    assert.equal(routeSource.extractResult.totalCandidates, 1);
    assert.equal(routeSource.extractResult.sourceState, 'FIXTURES_SWEEP_READY');

    const degraded = createProber({
      taskPlanner: {
        buildFixturesUrl: () => 'fixtures://mls',
      },
      async _executeRouteProbeWithNavigator() {
        throw new Error('fixtures blew up');
      },
      _recordRouteProbeFailure() {
        return {
          shouldDegrade: true,
          sourceState: 'FIXTURES_DEGRADED',
          searchBlocked: false,
          signals: {},
        };
      },
    });

    const degradedSource = await degraded._probeFixturesCandidateSource(
      { dbSeason: '2025/2026', league: { name: 'MLS' } },
      [{ match_id: 'm1' }],
      0.75
    );

    assert.equal(degradedSource.extractResult.sourceState, 'FIXTURES_DEGRADED');
  });

  it('_probeSearchCandidateSource 在 search 被禁用时应返回 degraded source', async () => {
    const prober = createProber();

    const routeSource = await prober._probeSearchCandidateSource(
      { dbSeason: '2025/2026', league: { name: 'MLS' }, disableSearchRoute: true },
      [{ match_id: 'm1' }],
      0.75
    );

    assert.equal(routeSource.extractResult.sourceState, 'ROUTE_SKIPPED_SEARCH_DISABLED');
    assert.equal(routeSource.metadata.searchBlocked, true);
  });

  it('_probeSearchCandidateSource 应覆盖空 pending、blocked、成功与降级分支', async () => {
    const prober = createProber({
      _isSearchProbeBlocked: () => true,
    });
    assert.equal(
      await prober._probeSearchCandidateSource({ dbSeason: '2025/2026' }, [], 0.75),
      null
    );

    const blocked = await prober._probeSearchCandidateSource(
      { dbSeason: '2025/2026', league: { name: 'MLS' } },
      [{ match_id: 'm1' }],
      0.75
    );
    assert.equal(blocked.extractResult.sourceState, 'ROUTE_SKIPPED_DEGRADED_LEAGUE');

    const successProber = createProber({
      async _executeRouteProbeWithNavigator(_target, _navigator, _options, probe) {
        return probe({
          async resetContextPerBatch() {},
          async navigate() {},
          page: {
            async evaluate() {
              return [{ match_id: 'm1', hash: 'AAAA1111' }];
            },
          },
        });
      },
    });
    const success = await successProber._probeSearchCandidateSource(
      { dbSeason: '2025/2026', league: { name: 'MLS' } },
      [{ match_id: 'm1', home_team: 'Alpha', away_team: 'Beta' }],
      0.75
    );
    assert.equal(success.extractResult.sourceState, 'SEARCH_SWEEP_READY');
    assert.equal(success.extractResult.totalCandidates, 1);

    const degraded = createProber({
      async _executeRouteProbeWithNavigator() {
        throw new Error('search 503');
      },
      _recordRouteProbeFailure() {
        return {
          shouldDegrade: false,
          sourceState: 'SEARCH_DEGRADED',
          searchBlocked: true,
          signals: { has503: true, hasTimeout: false },
        };
      },
    });
    const degradedSource = await degraded._probeSearchCandidateSource(
      { dbSeason: '2025/2026', league: { name: 'MLS' } },
      [{ match_id: 'm1' }],
      0.75
    );
    assert.equal(degradedSource.extractResult.sourceState, 'SEARCH_DEGRADED');
  });

  it('_executeRouteProbeWithNavigator 应使用独占 navigator 并在结束后释放', async () => {
    const released = [];
    const prober = createProber({
      _acquireTargetNavigator: async () => ({
        navigator: { id: 'dedicated-nav' },
      }),
      _releaseTargetNavigator: async (handle) => {
        released.push(handle?.navigator?.id || null);
      },
    });

    const value = await prober._executeRouteProbeWithNavigator(
      { league: { name: 'MLS' } },
      null,
      { routeKind: 'fixtures', useDedicatedNavigator: true },
      async (navigator) => navigator.id
    );

    assert.equal(value, 'dedicated-nav');
    assert.deepEqual(released, ['dedicated-nav']);
  });

  it('_executeRouteProbeWithNavigator 在无可用 navigator 时应返回空路由', async () => {
    const prober = createProber({
      navigator: null,
    });

    const routeSource = await prober._executeRouteProbeWithNavigator(
      { dbSeason: '2025/2026' },
      null,
      { routeKind: 'search' },
      async () => ({})
    );

    assert.equal(routeSource.extractResult.sourceState, 'ROUTE_SKIPPED_NO_NAVIGATOR');
  });

  it('_fetchCandidateRouteArchive 应优先调用 fetchFullSeasonArchive', async () => {
    const calls = [];
    const prober = createProber();
    const navigator = {
      async fetchFullSeasonArchive(url, options) {
        calls.push({ url, options });
        return { matches: [{ match_id: 'm1' }], pagesScanned: 2, totalCandidates: 1, sourceState: 'SOURCE_READY' };
      },
    };

    const result = await prober._fetchCandidateRouteArchive(
      'fixtures',
      'fixtures://mls',
      { dbSeason: '2025/2026' },
      [{ match_id: 'm1' }],
      navigator
    );

    assert.equal(result.totalCandidates, 1);
    assert.equal(calls[0].options.forceDomOnly, true);
    assert.equal(calls[0].options.disableTournamentFallback, true);
  });

  it('_fetchCandidateRouteArchive 应覆盖无 navigator、protocolArchive 与无 handler 分支', async () => {
    const prober = createProber();

    const noNavigator = await prober._fetchCandidateRouteArchive(
      'results',
      'results://mls',
      { dbSeason: '2025/2026' },
      [],
      null
    );
    assert.equal(noNavigator.sourceState, 'ROUTE_SKIPPED_NO_NAVIGATOR');

    const protocolRoute = await prober._fetchCandidateRouteArchive(
      'results',
      'results://mls',
      { dbSeason: '2025/2026' },
      [],
      {
        async protocolArchiveExtract(url, options) {
          return {
            matches: [{ url, options }],
            pagesScanned: 1,
            totalCandidates: 1,
            sourceState: 'SOURCE_READY',
          };
        },
      }
    );
    assert.equal(protocolRoute.totalCandidates, 1);

    const noHandler = await prober._fetchCandidateRouteArchive(
      'results',
      'results://mls',
      { dbSeason: '2025/2026' },
      [],
      {}
    );
    assert.equal(noHandler.sourceState, 'ROUTE_SKIPPED_NO_ARCHIVE_HANDLER');
  });

  it('_collectSearchCandidatesForPendingMatches 与 _collectSearchCandidatesFromUrl 应完成 URL 去重与页面抽取', async () => {
    const prober = createProber();
    const navigationCalls = [];
    const waitCalls = [];
    const navigator = {
      async resetContextPerBatch(payload) {
        navigationCalls.push({ reset: payload.reason });
      },
      async navigate(url, options) {
        navigationCalls.push({ url, options });
      },
      page: {
        async waitForTimeout(ms) {
          waitCalls.push(ms);
        },
        async evaluate(fn, payload) {
          const originalDocument = globalThis.document;
          globalThis.document = {
            querySelectorAll() {
              return [
                {
                  getAttribute(name) {
                    return name === 'href'
                      ? '/football/usa/mls/alpha-beta-AbCd1234/'
                      : '';
                  },
                },
                {
                  getAttribute(name) {
                    return name === 'href'
                      ? 'https://www.oddsportal.com/football/usa/mls/alpha-beta-AbCd1234/#same'
                      : '';
                  },
                },
                {
                  getAttribute(name) {
                    return name === 'href'
                      ? '/football/usa/mls/results/'
                      : '';
                  },
                },
              ];
            },
          };

          try {
            return await fn(payload);
          } finally {
            globalThis.document = originalDocument;
          }
        },
      },
    };

    const searchResult = await prober._collectSearchCandidatesForPendingMatches(
      { league: { name: 'MLS' }, dbSeason: '2025/2026' },
      [
        { home_team: 'Alpha', away_team: 'Beta' },
        { home_team: 'Alpha', away_team: 'Beta' },
      ],
      navigator,
      { timeoutMs: 700 }
    );

    assert.equal(searchResult.pagesScanned, 1);
    assert.equal(searchResult.matches.length, 1);
    assert.equal(searchResult.matches[0].hash, 'AbCd1234');
    assert.equal(searchResult.sourceUrls.length, 1);
    assert.equal(searchResult.emptySearchSamples.length, 0);
    assert.equal(waitCalls[0], 3);
    assert.equal(navigationCalls[0].reset, 'search_candidate_batch');
    assert.equal(
      searchResult.sourceUrls[0],
      'https://www.oddsportal.com/search/alpha-beta/'
    );
  });

  it('_collectSearchCandidatesForPendingMatches 应覆盖无 navigator、空 slug 与无效链接分支', async () => {
    const prober = createProber({
      _buildFallbackEventSlug(homeTeam, awayTeam) {
        return homeTeam && awayTeam ? `${homeTeam}-${awayTeam}` : '';
      },
    });

    const emptyResult = await prober._collectSearchCandidatesForPendingMatches(
      { dbSeason: '2025/2026' },
      [{ home_team: 'Alpha', away_team: 'Beta' }],
      null
    );
    assert.equal(emptyResult.pagesScanned, 0);

    const navigator = {
      async navigate() {},
      page: {
        async evaluate(fn, payload) {
          const originalDocument = globalThis.document;
          globalThis.document = {
            querySelectorAll() {
              return [
                { getAttribute: () => '' },
                { getAttribute: () => '/football/usa/mls/not-a-match/' },
              ];
            },
          };
          try {
            return fn(payload);
          } finally {
            globalThis.document = originalDocument;
          }
        },
      },
    };
    const sparseResult = await prober._collectSearchCandidatesForPendingMatches(
      { dbSeason: '2025/2026' },
      [
        { home_team: '', away_team: '' },
        { home_team: 'Alpha', away_team: 'Beta' },
      ],
      navigator,
      { timeoutMs: 500 }
    );

    assert.equal(sparseResult.pagesScanned, 2);
    assert.equal(sparseResult.matches.length, 0);
    assert.equal(prober._buildSearchUrlForMatch({ home_team: '', away_team: '' }), '');
  });

  it('_collectSearchCandidatesForPendingMatches 在 J1 search URL 超时时应审计并继续后续搜索', async () => {
    const prober = createProber();
    const resetReasons = [];
    const navigationCalls = [];
    const navigator = {
      proxy: { port: 7897 },
      async resetContextPerBatch(payload) {
        resetReasons.push(payload.reason);
      },
      async navigate(url, options) {
        navigationCalls.push({ url, options });
        if (url.includes('/search/alpha-beta/')) {
          throw new Error('page.goto: Timeout 20000ms exceeded.');
        }
      },
      page: {
        async waitForTimeout() {},
        async evaluate(fn, payload) {
          if (!payload.sourceUrl.includes('/search/gamma-delta/')) {
            return [];
          }

          const originalDocument = globalThis.document;
          globalThis.document = {
            querySelectorAll() {
              return [{
                getAttribute(name) {
                  return name === 'href'
                    ? '/football/japan/j1-league/gamma-delta-AbCd1234/'
                    : '';
                }
              }];
            }
          };

          try {
            return await fn(payload);
          } finally {
            globalThis.document = originalDocument;
          }
        }
      }
    };

    const searchResult = await prober._collectSearchCandidatesForPendingMatches(
      { league: { name: 'J1 League' }, dbSeason: '2025/2026' },
      [
        { match_id: 'm1', home_team: 'Alpha', away_team: 'Beta' },
        { match_id: 'm2', home_team: 'Gamma', away_team: 'Delta' }
      ],
      navigator,
      { timeoutMs: 20000 }
    );

    assert.equal(searchResult.matches.length, 1);
    assert.equal(searchResult.matches[0].hash, 'AbCd1234');
    assert.equal(searchResult.failedSearchSamples.length, 1);
    assert.equal(searchResult.failedSearchSamples[0].matchId, 'm1');
    assert.equal(searchResult.failedSearchSamples[0].proxyPort, 7897);
    assert.equal(searchResult.failedSearchSamples[0].timeoutMs, 20000);
    assert.equal(searchResult.emptySearchSamples.length, 1);
    assert.deepEqual(resetReasons, ['search_candidate_batch', 'search_candidate_timeout_recover']);
    assert.equal(navigationCalls[0].options.timeout, 20000);
    assert.equal(navigationCalls[1].options.timeout, 20000);
    assert.equal(navigationCalls[2].options.timeout, 20000);
    assert.equal(navigationCalls[2].url, 'https://www.oddsportal.com/search/alpha/');
  });

  it('_collectSearchCandidatesForPendingMatches 在 exact search 全空时应级联触发 fuzzy_prefix', async () => {
    const prober = createProber();
    const navigationCalls = [];
    const navigator = {
      async resetContextPerBatch() {},
      async navigate(url) {
        navigationCalls.push(url);
      },
      page: {
        async waitForTimeout() {},
        async evaluate(fn, payload) {
          if (!payload.sourceUrl.includes('/search/yokohama-f/')) {
            return [];
          }

          const originalDocument = globalThis.document;
          globalThis.document = {
            querySelectorAll() {
              return [{
                getAttribute(name) {
                  return name === 'href'
                    ? '/football/japan/j1-league/yokohama-f-marinos-vissel-kobe-AbCd1234/'
                    : '';
                }
              }];
            }
          };

          try {
            return await fn(payload);
          } finally {
            globalThis.document = originalDocument;
          }
        }
      }
    };

    const searchResult = await prober._collectSearchCandidatesForPendingMatches(
      { league: { name: 'J1 League' }, dbSeason: '2025/2026' },
      [{ match_id: 'm1', home_team: 'Yokohama F.Marinos', away_team: 'Vissel Kobe' }],
      navigator,
      { timeoutMs: 20000 }
    );

    assert.equal(searchResult.matches.length, 1);
    assert.equal(searchResult.matches[0].hash, 'AbCd1234');
    assert.deepEqual(navigationCalls, [
      'https://www.oddsportal.com/search/yokohama-f-marinos-vissel-kobe/',
      'https://www.oddsportal.com/search/vissel-kobe-yokohama-f-marinos/',
      'https://www.oddsportal.com/search/yokohama-f/'
    ]);
  });

  it('_collectSearchCandidatesForPendingMatches 在 exact search 已命中时不应触发 fuzzy_prefix', async () => {
    const prober = createProber();
    const navigationCalls = [];
    const navigator = {
      async resetContextPerBatch() {},
      async navigate(url) {
        navigationCalls.push(url);
      },
      page: {
        async waitForTimeout() {},
        async evaluate(fn, payload) {
          if (!payload.sourceUrl.includes('/search/alpha-united-beta/')) {
            return [];
          }

          const originalDocument = globalThis.document;
          globalThis.document = {
            querySelectorAll() {
              return [{
                getAttribute(name) {
                  return name === 'href'
                    ? '/football/japan/j1-league/alpha-united-beta-AbCd1234/'
                    : '';
                }
              }];
            }
          };

          try {
            return await fn(payload);
          } finally {
            globalThis.document = originalDocument;
          }
        }
      }
    };

    const searchResult = await prober._collectSearchCandidatesForPendingMatches(
      { league: { name: 'J1 League' }, dbSeason: '2025/2026' },
      [{ match_id: 'm1', home_team: 'Alpha United', away_team: 'Beta' }],
      navigator,
      { timeoutMs: 20000 }
    );

    assert.equal(searchResult.matches.length, 1);
    assert.ok(
      navigationCalls.includes('https://www.oddsportal.com/search/alpha-united-beta/')
    );
    assert.ok(
      navigationCalls.includes('https://www.oddsportal.com/search/beta-alpha-united/')
    );
    assert.ok(
      !navigationCalls.includes('https://www.oddsportal.com/search/alpha-united/')
    );
  });

  it('_collectSearchCandidatesForPendingMatches 在联赛预算耗尽时应短路 search 循环', async () => {
    const prober = createProber();
    const navigationCalls = [];
    const originalNow = Date.now;
    let nowCallCount = 0;
    Date.now = () => {
      nowCallCount += 1;
      return nowCallCount >= 3 ? 5000 : 1000;
    };

    try {
      const searchResult = await prober._collectSearchCandidatesForPendingMatches(
        {
          league: { name: 'J1 League' },
          dbSeason: '2025/2026',
          leagueDeadlineAt: 4000
        },
        [
          { match_id: 'm1', home_team: 'Alpha', away_team: 'Beta' },
          { match_id: 'm2', home_team: 'Gamma', away_team: 'Delta' }
        ],
        {
          async resetContextPerBatch() {},
          async navigate(url) {
            navigationCalls.push(url);
          },
          page: {
            async waitForTimeout() {},
            async evaluate() {
              return [];
            }
          }
        },
        { timeoutMs: 20000 }
      );

      assert.equal(searchResult.matches.length, 0);
      assert.equal(searchResult.pagesScanned, 1);
      assert.equal(searchResult.emptySearchSamples.length, 0);
      assert.equal(navigationCalls.length, 1);
      assert.ok(
        prober.__events.warn.some(({ event }) => event === 'recon_search_budget_short_circuit')
      );
    } finally {
      Date.now = originalNow;
    }
  });

  it('_probeSearchCandidateSource 在容错 search 超时样本存在时应输出审计日志而非整路由失败', async () => {
    const prober = createProber({
      async _executeRouteProbeWithNavigator(_target, _navigator, _options, probe) {
        return probe({
          async resetContextPerBatch() {},
          async navigate(url) {
            if (url.includes('/search/alpha-beta/')) {
              throw new Error('page.goto: Timeout 20000ms exceeded.');
            }
          },
          page: {
            async waitForTimeout() {},
            async evaluate() {
              return [];
            }
          }
        });
      }
    });

    const routeSource = await prober._probeSearchCandidateSource(
      { dbSeason: '2025/2026', league: { name: 'J1 League' } },
      [{ match_id: 'm1', home_team: 'Alpha', away_team: 'Beta' }],
      0.75
    );

    assert.equal(routeSource.extractResult.sourceState, 'SOURCE_EMPTY');
    assert.ok(
      prober.__events.warn.some(({ event }) => event === 'recon_search_navigation_failure_audit')
    );
  });

  it('_probeSearchCandidateSource 在所有变体都跑空时应输出 deep audit', async () => {
    const prober = createProber({
      async _executeRouteProbeWithNavigator(_target, _navigator, _options, probe) {
        return probe({
          async resetContextPerBatch() {},
          async navigate() {},
          page: {
            async waitForTimeout() {},
            async evaluate() {
              return [];
            }
          }
        });
      }
    });

    const routeSource = await prober._probeSearchCandidateSource(
      { dbSeason: '2025/2026', league: { name: 'J1 League' } },
      [{ match_id: 'm1', home_team: 'Yokohama F.Marinos', away_team: 'Vissel Kobe' }],
      0.75
    );

    assert.equal(routeSource.extractResult.sourceState, 'SOURCE_EMPTY');
    const deepAuditEvent = prober.__events.warn.find(({ event }) => event === 'recon_search_source_empty_deep_audit');
    assert.ok(deepAuditEvent);
    assert.deepEqual(deepAuditEvent.payload, {
      league: 'J1 League',
      season: '2025/2026',
      target_match_id: 'm1',
      home_team_raw: 'Yokohama F.Marinos',
      away_team_raw: 'Vissel Kobe',
      attempted_slugs: [
        'yokohama-f-marinos-vissel-kobe',
        'vissel-kobe-yokohama-f-marinos',
        'yokohama-f'
      ]
    });
  });

  it('_buildSearchUrlForMatch 应使用标准化别名生成搜索 slug', () => {
    const prober = createProber();

    assert.equal(
      prober._buildSearchUrlForMatch({
        home_team: 'Ld Alajuelense',
        away_team: 'Club Sport Herediano'
      }),
      'https://www.oddsportal.com/search/alajuelense-herediano/'
    );
  });

  it('_buildSearchDescriptorsForMatch 在高噪联赛应补充反向、字典与 fuzzy_prefix 搜索变体', () => {
    const prober = createProber({
      matchEvaluator: {
        normalizeTeamName(teamName) {
          return String(teamName || '')
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .replace(/[^a-z0-9]+/gi, ' ')
            .trim()
            .toLowerCase();
        }
      },
      _buildLocalDictionaryIndex() {
        return new Map([
          ['flamengo', { remote_name: 'Flamengo RJ' }],
          ['internacional', { remote_name: 'Internacional' }]
        ]);
      },
      _resolveLocalDictionaryRemoteName(teamName, index) {
        return index.get(this._normalizeLocalDictionaryTeamName(teamName))?.remote_name || null;
      },
      _normalizeLocalDictionaryTeamName(teamName) {
        return this.matchEvaluator.normalizeTeamName(teamName);
      }
    });

    const descriptors = prober._buildSearchDescriptorsForMatch(
      {
        home_team: 'Flamengo',
        away_team: 'Internacional'
      },
      {
        league: { name: 'Brasileirão' }
      }
    );

    assert.deepEqual(
      descriptors.map((descriptor) => descriptor.origin),
      ['raw', 'raw_reversed', 'dictionary_remote', 'dictionary_remote_reversed', 'fuzzy_prefix']
    );
    assert.deepEqual(
      descriptors.map((descriptor) => descriptor.cascadeStage),
      ['exact', 'exact', 'exact', 'exact', 'fuzzy']
    );
    assert.deepEqual(
      descriptors.map((descriptor) => descriptor.searchSlug),
      [
        'flamengo-internacional',
        'internacional-flamengo',
        'flamengo-rj-internacional',
        'internacional-flamengo-rj',
        'flamengo'
      ]
    );
  });

  it('_selectCandidateSourceWithLocalFallback 在远端为空时应切换到本地字典', async () => {
    const prober = createProber({
      _probeCandidateRoutes: async () => ({
        routeKind: 'results',
        source: { season: '2025/2026', url: 'results://mls' },
        extractResult: { matches: [], pagesScanned: 0, totalCandidates: 0, sourceState: 'SOURCE_EMPTY' },
        candidates: [],
        seasonMirror: new Map(),
        sampleLinked: 0,
      }),
      _canUseLocalDictionaryFallback: () => true,
    });

    const routeSource = await prober._selectCandidateSourceWithLocalFallback(
      { league: { name: 'MLS' }, dbSeason: '2025/2026' },
      [{ match_id: 'm1' }],
      0.75
    );

    assert.equal(routeSource.routeKind, 'local_dictionary');
    assert.equal(prober.__events.warn[0].event, 'recon_local_dictionary_fallback_armed');
  });

  it('_selectCandidateSourceWithLocalFallback 在 probe 抛错时也应走恢复分支', async () => {
    const prober = createProber({
      _probeCandidateRoutes: async () => {
        throw new Error('upstream failed');
      },
      _canUseLocalDictionaryFallback: () => true,
    });

    const routeSource = await prober._selectCandidateSourceWithLocalFallback(
      { league: { name: 'MLS' }, dbSeason: '2025/2026' },
      [{ match_id: 'm1' }],
      0.75
    );

    assert.equal(routeSource.routeKind, 'local_dictionary');
    assert.equal(prober.__events.warn[0].event, 'recon_local_dictionary_fallback_recovered');
  });
});
