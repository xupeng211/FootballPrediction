'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { ReconTaskPlanner } = require('../../src/infrastructure/recon/services/ReconTaskPlanner');
const { ReconMirrorManager } = require('../../src/infrastructure/recon/services/ReconMirrorManager');
const { ReconMatchEvaluator } = require('../../src/infrastructure/recon/services/ReconMatchEvaluator');

function createPlanner(overrides = {}) {
  const evaluator = new ReconMatchEvaluator({
    parser: {
      calculateSimilarity(left, right) {
        return String(left || '').toLowerCase().trim() === String(right || '').toLowerCase().trim() ? 1 : 0;
      }
    },
    logger: { info() {}, warn() {}, error() {} }
  });
  const mirrorManager = new ReconMirrorManager({ evaluator });
  evaluator.setMirrorManager(mirrorManager);

  return new ReconTaskPlanner({
    baseUrl: 'oddsportal://root',
    repository: overrides.repository || {},
    navigator: overrides.navigator || {},
    logger: overrides.logger || { info() {}, warn() {}, error() {} },
    configManager: overrides.configManager || null,
    matchEvaluator: evaluator,
    mirrorManager,
    sampleSize: overrides.sampleSize,
    resultsPathTemplate: overrides.resultsPathTemplate,
    fixturesPathTemplate: overrides.fixturesPathTemplate,
    mismatchRetryThresholdFloorByLeagueId: overrides.mismatchRetryThresholdFloorByLeagueId,
    annualLeagueIds: overrides.annualLeagueIds,
    forceDomLeagueIds: overrides.forceDomLeagueIds,
    excludeAllLeagueIds: overrides.excludeAllLeagueIds
  });
}

describe('ReconTaskPlanner', () => {
  it('allowMismatchRetry 开启时仍不得低于 0.75 硬门槛，并启用 forceMultiMode', () => {
    const planner = createPlanner();
    const policy = planner.resolveReconPolicy(
      { leagueId: 47, league: { name: 'Premier League' } },
      [{ match_id: 'm1', pipeline_status: 'RECON_MISMATCH' }],
      0.75,
      { allowMismatchRetry: true }
    );

    assert.strictEqual(policy.allowMismatchRetry, true);
    assert.strictEqual(policy.hasMismatchRetry, true);
    assert.strictEqual(policy.effectiveConfidenceThreshold, 0.75);
    assert.strictEqual(policy.forceMultiMode, true);
  });

  it('即使联赛覆盖了 mismatch_retry_threshold_floor，也不得跌破全局 0.75 门槛', () => {
    const planner = createPlanner({
      mismatchRetryThresholdFloorByLeagueId: {
        131: 0.25
      }
    });

    const policy = planner.resolveReconPolicy(
      { leagueId: 131, league: { id: 131, name: 'Copa América' } },
      [{ match_id: '131_20252026_0001', pipeline_status: 'RECON_MISMATCH' }],
      0.4,
      { allowMismatchRetry: true }
    );

    assert.strictEqual(policy.effectiveConfidenceThreshold, 0.75);
  });

  it('应在有限配额内优先调度高置信度任务', () => {
    const planner = createPlanner();
    const pendingMatches = [
      {
        match_id: '47_20242025_1000',
        home_team: 'Home 0',
        away_team: 'Away 0',
        match_date: '2024-08-01T12:00:00.000Z'
      },
      {
        match_id: '47_20242025_1001',
        home_team: 'Home 1',
        away_team: 'Away 1',
        match_date: '2024-08-03T12:00:00.000Z'
      },
      {
        match_id: '47_20242025_1002',
        home_team: 'Home 2',
        away_team: 'Away 2',
        match_date: '2024-08-02T12:00:00.000Z'
      }
    ];
    const candidates = [
      {
        hash: 'hash_1000',
        url: 'oddsportal://match/1000',
        homeTeam: 'Home 0',
        awayTeam: 'Away 0',
        matchDate: '2024-08-01T12:00:00.000Z'
      },
      {
        hash: 'hash_1001',
        url: 'oddsportal://match/1001',
        homeTeam: 'Home 1',
        awayTeam: 'Away 1',
        matchDate: '2024-08-03T12:00:00.000Z'
      }
    ];

    const selected = planner.selectProcessablePendingMatches(
      pendingMatches,
      candidates,
      0.75,
      2
    );

    assert.deepStrictEqual(
      selected.map((match) => match.match_id),
      ['47_20242025_1001', '47_20242025_1000']
    );
  });

  it('prepareReconPendingTargets 应优先返回 harvested 积压更高的联赛', async () => {
    const leagues = [
      { id: 47, code: 'EPL', name: 'Premier League', country: 'england', slug: 'premier-league' },
      { id: 130, code: 'MLS', name: 'MLS', country: 'usa', slug: 'mls', resultsUrlStrategy: 'seasonless', seasonType: 'single_year' }
    ];
    const planner = createPlanner({
      configManager: {
        getActiveLeagues() {
          return leagues;
        }
      },
      repository: {
        async getReconEligibleMatches(dbSeason, leagueName) {
          assert.strictEqual(dbSeason, '2025/2026');
          if (leagueName === 'Premier League') {
            return [
              { match_id: '47_20252026_0001', pipeline_status: 'HARVESTED' },
              { match_id: '47_20252026_0002', pipeline_status: 'RECON_MISMATCH' }
            ];
          }
          if (leagueName === 'MLS') {
            return [
              { match_id: '130_20252026_0001', pipeline_status: 'HARVESTED' },
              { match_id: '130_20252026_0002', pipeline_status: 'HARVESTED' },
              { match_id: '130_20252026_0003', pipeline_status: 'HARVESTED' }
            ];
          }
          return [];
        }
      }
    });

    const targets = await planner.buildScanTargets({
      season: '2025-2026',
      currentSeasonOnly: true
    });
    const prepared = await planner.prepareReconPendingTargets(targets, null, {
      allowMismatchRetry: true,
      confidenceThreshold: 0.75
    });

    assert.deepStrictEqual(
      prepared.map(({ target }) => target.league.name),
      ['MLS', 'Premier League']
    );
  });

  it('mismatchRetryOnly 开启时应仅返回 RECON_MISMATCH 目标集', async () => {
    const planner = createPlanner({
      configManager: {
        getActiveLeagues() {
          return [
            { id: 47, code: 'EPL', name: 'Premier League', country: 'england', slug: 'premier-league' }
          ];
        }
      },
      repository: {
        async getReconEligibleMatches(_dbSeason, leagueName) {
          if (leagueName !== 'Premier League') {
            return [];
          }

          return [
            { match_id: '47_20252026_0001', pipeline_status: 'HARVESTED' },
            { match_id: '47_20252026_0002', pipeline_status: 'RECON_MISMATCH' },
            { match_id: '47_20252026_0003', pipeline_status: 'RECON_MISMATCH' }
          ];
        }
      }
    });

    const targets = await planner.buildScanTargets({
      season: '2025-2026',
      leagueIds: [47]
    });
    const prepared = await planner.prepareReconPendingTargets(targets, null, {
      allowMismatchRetry: true,
      mismatchRetryOnly: true,
      confidenceThreshold: 0.15
    });

    assert.equal(prepared.length, 1);
    assert.deepStrictEqual(
      prepared[0].pendingMatches.map((match) => match.match_id),
      ['47_20252026_0002', '47_20252026_0003']
    );
    assert.equal(prepared[0].priority.harvestedCount, 0);
    assert.equal(prepared[0].priority.mismatchCount, 2);
  });

  it('当前赛季 SOURCE_EMPTY 时应保留当前赛季 source，不得回退到上一赛季', async () => {
    const calls = [];
    const planner = createPlanner({
      navigator: {
        async fetchFullSeasonArchive(url, options) {
          calls.push({ url, options });
          return {
            matches: [],
            pagesScanned: 1,
            totalCandidates: 0,
            sourceState: 'SOURCE_EMPTY'
          };
        }
      }
    });

    const target = {
      leagueId: 47,
      league: { name: 'Premier League', country: 'england', slug: 'premier-league' },
      season: '2025-2026',
      dbSeason: '2025/2026',
      resultsUrl: 'oddsportal://root/football/england/premier-league-2025-2026/results/'
    };
    const pendingMatches = [{
      match_id: '47_20252026_5000',
      home_team: 'Arsenal',
      away_team: 'Chelsea',
      match_date: '2025-08-01T19:00:00.000Z'
    }];

    const selected = await planner.selectCandidateSource(target, pendingMatches, 0.75);

    assert.strictEqual(selected.source.season, '2025-2026');
    assert.strictEqual(selected.source.url, target.resultsUrl);
    assert.strictEqual(selected.extractResult.sourceState, 'SOURCE_EMPTY');
    assert.strictEqual(selected.sampleLinked, 0);
    assert.deepStrictEqual(calls, [
      {
        url: target.resultsUrl,
        options: {
          maxPages: 50,
          timeoutMs: planner.archiveTimeoutMs,
          preferCurrentSeasonSource: true,
          circuitBreakerKey: 'recon:47:2025/2026:results_archive:2025-2026:0',
          forcePureProtocol: false
        }
      }
    ]);
  });

  it('current_season 分支也应无损透传 readySelector 到 protocolArchiveExtract', async () => {
    const calls = [];
    const planner = createPlanner({
      navigator: {
        async protocolArchiveExtract(url, options) {
          calls.push({ url, options });
          return {
            matches: [],
            pagesScanned: 1,
            totalCandidates: 0,
            sourceState: 'SOURCE_EMPTY'
          };
        }
      }
    });

    const target = {
      leagueId: 120,
      league: {
        id: 120,
        name: 'CSL',
        country: 'china',
        slug: 'super-league',
        resultsUrlStrategy: 'seasonless'
      },
      readySelector: '[data-testid="match-row"]',
      season: '2025-2026',
      dbSeason: '2025/2026',
      resultsUrl: 'oddsportal://root/football/china/super-league/results/'
    };
    const pendingMatches = [{
      match_id: '120_20252026_5000',
      home_team: 'Shanghai Port',
      away_team: 'Beijing Guoan',
      match_date: '2026-03-01T12:00:00.000Z'
    }];

    await planner.selectCandidateSource(target, pendingMatches, 0.75);

    assert.deepStrictEqual(calls, [
      {
        url: 'oddsportal://root/football/china/super-league/results/',
        options: {
          maxPages: 50,
          timeoutMs: planner.archiveTimeoutMs,
          preferCurrentSeasonSource: true,
          circuitBreakerKey: 'recon:120:2025/2026:current_season:2026:0',
          forcePureProtocol: false,
          readySelector: '[data-testid="match-row"]'
        }
      }
    ]);
  });

  it('seasonless 联赛应生成 canonical results URL，不得拼接双年份后缀', () => {
    const planner = createPlanner();

    const url = planner.buildResultsUrl({
      name: 'Süper Lig',
      country: 'turkey',
      slug: 's-per-lig',
      resultsSlug: 'super-lig',
      resultsUrlStrategy: 'seasonless'
    }, '2025-2026');

    assert.strictEqual(
      url,
      'oddsportal://root/football/turkey/super-lig/results/'
    );
  });

  it('年度制联赛应将 2025/2026 强制映射到 2026 results URL', () => {
    const planner = createPlanner();

    const url = planner.buildResultsUrl({
      id: 268,
      name: 'Brasileirão',
      country: 'brazil',
      slug: 'brasileirao',
      resultsSlug: 'serie-a',
      resultsUrlStrategy: 'seasonless'
    }, '2025-2026');

    assert.strictEqual(
      url,
      'oddsportal://root/football/brazil/serie-a-2026/results/'
    );
  });

  it('MLS 应使用 seasonless 的 canonical results URL', () => {
    const planner = createPlanner();

    const url = planner.buildResultsUrl({
      name: 'MLS',
      country: 'usa',
      slug: 'mls',
      resultsUrlStrategy: 'seasonless'
    }, '2025-2026');

    assert.strictEqual(
      url,
      'oddsportal://root/football/usa/mls/results/'
    );
  });

  it('MLS 额外结果路径应扩展为 league root，多 URL 组合抓取当前与历史赛季', () => {
    const planner = createPlanner();

    const currentUrls = planner.buildCurrentSeasonSourceUrls({
      name: 'MLS',
      country: 'usa',
      slug: 'mls',
      resultsUrlStrategy: 'seasonless',
      additionalResultsPaths: ['/football/{country}/{league}/']
    }, '2026');
    const historicalUrls = planner.buildHistoricalSeasonSourceUrls({
      name: 'MLS',
      country: 'usa',
      slug: 'mls',
      resultsUrlStrategy: 'seasonless',
      additionalHistoricalResultsPaths: ['/football/{country}/{league}-{year}/']
    }, 2025);

    assert.deepStrictEqual(currentUrls, [
      'oddsportal://root/football/usa/mls/results/',
      'oddsportal://root/football/usa/mls/'
    ]);
    assert.deepStrictEqual(historicalUrls, [
      'oddsportal://root/football/usa/mls-2025/results/',
      'oddsportal://root/football/usa/mls-2025/'
    ]);
  });

  it('single_year 的 seasonless 联赛应补充起始年份 historical results source', () => {
    const planner = createPlanner();

    const sources = planner.buildCandidateSources({
      league: {
        id: 130,
        name: 'MLS',
        country: 'usa',
        slug: 'mls',
        resultsUrlStrategy: 'seasonless',
        seasonType: 'single_year'
      },
      season: '2026',
      dbSeason: '2025/2026',
      pendingMatches: [{
        match_id: '130_20252026_0001',
        match_date: '2026-03-15T02:30:00.000Z'
      }]
    });

    assert.deepStrictEqual(sources, [
      {
        season: '2026',
        url: 'oddsportal://root/football/usa/mls/results/',
        mode: 'current_season'
      },
      {
        season: '2025',
        url: 'oddsportal://root/football/usa/mls-2025/results/',
        mode: 'historical_results'
      }
    ]);
  });

  it('currentSeasonOnly 开启时，seasonless 联赛不得回扫 historical results source', () => {
    const planner = createPlanner();

    const sources = planner.buildCandidateSources({
      league: {
        id: 130,
        name: 'MLS',
        country: 'usa',
        slug: 'mls',
        resultsUrlStrategy: 'seasonless',
        seasonType: 'single_year'
      },
      season: '2026',
      dbSeason: '2025/2026',
      currentSeasonOnly: true,
      pendingMatches: [{
        match_id: '130_20252026_0001',
        match_date: '2026-03-15T02:30:00.000Z'
      }]
    });

    assert.deepStrictEqual(sources, [
      {
        season: '2026',
        url: 'oddsportal://root/football/usa/mls/results/',
        mode: 'current_season'
      }
    ]);
  });

  it('年度制联赛应优先生成带年份与根路径回退的四门 source', () => {
    const planner = createPlanner();

    const sources = planner.buildCandidateSources({
      league: {
        id: 121,
        name: 'Primera División',
        country: 'argentina',
        slug: 'primera-division',
        resultsUrlStrategy: 'seasonal'
      },
      season: '2025-2026',
      dbSeason: '2025/2026',
      pendingMatches: [{
        match_id: '121_20252026_0001',
        match_date: '2026-02-11T00:00:00.000Z'
      }]
    });

    assert.deepStrictEqual(sources, [
      {
        season: '2026',
        url: 'oddsportal://root/football/argentina/primera-division-2026/results/',
        mode: 'current_results'
      },
      {
        season: '2026',
        url: 'oddsportal://root/football/argentina/primera-division/results/',
        mode: 'current_results_fallback'
      },
      {
        season: '2026',
        url: 'oddsportal://root/football/argentina/primera-division-2026/fixtures/',
        mode: 'current_fixtures'
      },
      {
        season: '2026',
        url: 'oddsportal://root/football/argentina/primera-division/fixtures/',
        mode: 'current_fixtures_fallback'
      }
    ]);
  });

  it('harvested 积压达到高水位时应强制提升 maxPages 到 100', async () => {
    const calls = [];
    const planner = createPlanner({
      navigator: {
        async fetchFullSeasonArchive(url, options) {
          calls.push({ url, options });
          return {
            matches: [],
            pagesScanned: 1,
            totalCandidates: 0,
            sourceState: 'SOURCE_EMPTY'
          };
        }
      }
    });

    const target = {
      leagueId: 268,
      league: {
        id: 268,
        name: 'Brasileirão',
        country: 'brazil',
        slug: 'serie-a',
        resultsUrlStrategy: 'seasonless'
      },
      season: '2025-2026',
      dbSeason: '2025/2026',
      resultsUrl: 'oddsportal://root/football/brazil/serie-a-2026/results/'
    };
    const pendingMatches = Array.from({ length: 365 }, (_, index) => ({
      match_id: `268_20252026_${4000 + index}`,
      home_team: `Home ${index}`,
      away_team: `Away ${index}`,
      match_date: '2026-03-01T12:00:00.000Z'
    }));

    await planner.selectCandidateSource(target, pendingMatches, 0.75);

    assert.strictEqual(calls.length, 4);
    assert.strictEqual(calls[0].options.maxPages, 100);
    assert.strictEqual(calls[0].url, 'oddsportal://root/football/brazil/serie-a-2026/results/');
    assert.strictEqual(calls[1].options.maxPages, 100);
    assert.strictEqual(calls[1].url, 'oddsportal://root/football/brazil/serie-a/results/');
    assert.strictEqual(calls[2].options.maxPages, 100);
    assert.strictEqual(calls[2].url, 'oddsportal://root/football/brazil/serie-a-2026/fixtures/');
    assert.strictEqual(calls[3].options.maxPages, 100);
    assert.strictEqual(calls[3].url, 'oddsportal://root/football/brazil/serie-a/fixtures/');
  });

  it('single_year 联赛应使用结束年份生成 results URL', () => {
    const planner = createPlanner();

    const target = planner.buildTarget('2025-2026', {
      id: 223,
      name: 'J1 League',
      country: 'Japan',
      slug: 'j1-league',
      seasonType: 'single_year',
      resultsUrlStrategy: 'seasonal'
    });

    assert.strictEqual(target.season, '2026');
    assert.strictEqual(
      target.resultsUrl,
      'oddsportal://root/football/japan/j1-league-2026/results/'
    );
  });

  it('J1 与 J2 当前赛季都应使用年度制 results URL', () => {
    const planner = createPlanner();

    const j1Target = planner.buildTarget('2025-2026', {
      id: 223,
      name: 'J1 League',
      country: 'Japan',
      slug: 'j1-league',
      seasonType: 'single_year',
      resultsUrlStrategy: 'seasonless'
    });
    const j2Target = planner.buildTarget('2025-2026', {
      id: 8974,
      name: 'J2 League',
      country: 'Japan',
      slug: 'j2-league',
      seasonType: 'single_year',
      resultsUrlStrategy: 'seasonless'
    });

    assert.strictEqual(j1Target.season, '2026');
    assert.strictEqual(
      j1Target.resultsUrl,
      'oddsportal://root/football/japan/j1-league-2026/results/'
    );
    assert.strictEqual(j2Target.season, '2026');
    assert.strictEqual(
      j2Target.resultsUrl,
      'oddsportal://root/football/japan/j2-league-2026/results/'
    );
  });

  it('J2 应升级为年度制 source，优先尝试 2026 results 与 fixtures 回退', () => {
    const planner = createPlanner();

    const sources = planner.buildCandidateSources({
      league: {
        id: 8974,
        name: 'J2 League',
        country: 'japan',
        slug: 'j2-league',
        resultsUrlStrategy: 'seasonless',
        seasonType: 'single_year',
        seasonlessCurrentYearBasis: 'start'
      },
      season: '2026',
      dbSeason: '2025/2026',
      pendingMatches: [{
        match_id: '8974_20252026_4691330',
        match_date: '2025-03-01T05:00:00.000Z'
      }]
    });

    assert.deepStrictEqual(sources, [
      {
        season: '2026',
        url: 'oddsportal://root/football/japan/j2-league-2026/results/',
        mode: 'current_results'
      },
      {
        season: '2026',
        url: 'oddsportal://root/football/japan/j2-league/results/',
        mode: 'current_results_fallback'
      },
      {
        season: '2026',
        url: 'oddsportal://root/football/japan/j2-league-2026/fixtures/',
        mode: 'current_fixtures'
      },
      {
        season: '2026',
        url: 'oddsportal://root/football/japan/j2-league/fixtures/',
        mode: 'current_fixtures_fallback'
      }
    ]);
  });

  it('seasonal SOURCE_EMPTY 联赛应追加 canonical fallback URL', () => {
    const planner = createPlanner();

    const sources = planner.buildCandidateSources({
      league: {
        id: 140,
        name: 'Segunda División',
        country: 'spain',
        slug: 'segunda-division',
        resultsUrlStrategy: 'seasonal',
        seasonType: 'dual_year'
      },
      season: '2025-2026',
      dbSeason: '2025/2026',
      pendingMatches: [{
        match_id: '140_20252026_0001',
        match_date: '2026-03-01T05:00:00.000Z'
      }]
    });

    assert.deepStrictEqual(sources, [
      {
        season: '2025-2026',
        url: 'oddsportal://root/football/spain/segunda-division-2025-2026/results/',
        mode: 'results_archive'
      },
      {
        season: '2025-2026',
        url: 'oddsportal://root/football/spain/laliga2-2025-2026/results/',
        mode: 'results_archive_fallback'
      },
      {
        season: '2025-2026',
        url: 'oddsportal://root/football/spain/laliga2/results/',
        mode: 'results_archive_fallback'
      }
    ]);
  });

  it('年度制 force_dom_league_ids 命中时应优先走带根路径回退的 full season DOM sweep', async () => {
    const calls = [];
    const planner = createPlanner({
      forceDomLeagueIds: [223],
      navigator: {
        async fetchFullSeasonArchive(url, options) {
          calls.push({ type: 'full', url, options });
          return {
            matches: [],
            pagesScanned: 1,
            totalCandidates: 0,
            sourceState: 'SOURCE_EMPTY'
          };
        },
        async protocolArchiveExtract() {
          calls.push({ type: 'protocol' });
          throw new Error('should_not_call_protocol');
        }
      }
    });

    const target = {
      leagueId: 223,
      league: {
        id: 223,
        name: 'J1 League',
        country: 'japan',
        slug: 'j1-league',
        seasonType: 'single_year',
        resultsUrlStrategy: 'seasonless'
      },
      readySelector: 'text=Fixture Ready',
      season: '2026',
      dbSeason: '2025/2026',
      resultsUrl: 'oddsportal://root/football/japan/j1-league-2026/results/'
    };
    const pendingMatches = [{
      match_id: '223_20252026_4690937',
      home_team: 'Machida Zelvia',
      away_team: 'FC Tokyo',
      match_date: '2026-02-14T05:00:00.000Z'
    }];

    await planner.selectCandidateSource(target, pendingMatches, 0.75);

    assert.deepStrictEqual(calls, [
      {
        type: 'full',
        url: target.resultsUrl,
        options: {
          maxPages: 50,
          timeoutMs: planner.archiveTimeoutMs,
          preferCurrentSeasonSource: true,
          forcePureProtocol: false,
          readySelector: 'text=Fixture Ready',
          circuitBreakerKey: 'recon:223:2025/2026:current_results:2026:0'
        }
      },
      {
        type: 'full',
        url: 'oddsportal://root/football/japan/j1-league/results/',
        options: {
          maxPages: 50,
          timeoutMs: planner.archiveTimeoutMs,
          preferCurrentSeasonSource: true,
          forcePureProtocol: false,
          readySelector: 'text=Fixture Ready',
          circuitBreakerKey: 'recon:223:2025/2026:current_results_fallback:2026:1'
        }
      },
      {
        type: 'full',
        url: 'oddsportal://root/football/japan/j1-league-2026/fixtures/',
        options: {
          maxPages: 50,
          timeoutMs: planner.archiveTimeoutMs,
          preferCurrentSeasonSource: true,
          forceDomOnly: true,
          forcePureProtocol: false,
          readySelector: 'text=Fixture Ready',
          circuitBreakerKey: 'recon:223:2025/2026:current_fixtures:2026:2'
        }
      },
      {
        type: 'full',
        url: 'oddsportal://root/football/japan/j1-league/fixtures/',
        options: {
          maxPages: 50,
          timeoutMs: planner.archiveTimeoutMs,
          preferCurrentSeasonSource: true,
          forceDomOnly: true,
          forcePureProtocol: false,
          readySelector: 'text=Fixture Ready',
          circuitBreakerKey: 'recon:223:2025/2026:current_fixtures_fallback:2026:3'
        }
      }
    ]);
  });

  it('all-leagues 构建目标时应默认排除 exclude_all_league_ids，但显式 leagueIds 仍可命中', async () => {
    const leagues = [
      { id: 47, code: 'EPL', name: 'Premier League', country: 'england', slug: 'premier-league' },
      { id: 223, code: 'J1', name: 'J1 League', country: 'japan', slug: 'j1-league' }
    ];
    const planner = createPlanner({
      excludeAllLeagueIds: [223],
      configManager: {
        getActiveLeagues() {
          return leagues;
        }
      }
    });

    const defaultTargets = await planner.buildScanTargets({ season: '2025-2026' });
    const explicitTargets = await planner.buildScanTargets({ season: '2025-2026', leagueIds: [223] });

    assert.deepStrictEqual(defaultTargets.map((target) => target.leagueId), [47]);
    assert.deepStrictEqual(explicitTargets.map((target) => target.leagueId), [223]);
  });

  it('single_year 的四位年份应被识别为当前赛季', () => {
    const planner = createPlanner();
    const currentYear = new Date().getUTCFullYear();

    assert.strictEqual(planner.isCurrentSeason(String(currentYear)), true);
    assert.strictEqual(planner.isCurrentSeason(String(currentYear - 1)), false);
  });

  it('多词 country 应转换为 OddsPortal 连字符路径段', () => {
    const planner = createPlanner();

    const url = planner.buildResultsUrl({
      name: 'Copa América',
      country: 'South America',
      slug: 'copa-america',
      resultsSlug: 'copa-america',
      resultsUrlStrategy: 'seasonal'
    }, '2025-2026');

    assert.strictEqual(
      url,
      'oddsportal://root/football/south-america/copa-america-2025-2026/results/'
    );
  });

  it('slug 已包含年份时不得追加系统 season 后缀', () => {
    const planner = createPlanner();

    const url = planner.buildResultsUrl({
      name: 'FIFA World Cup',
      country: 'world',
      slug: 'world-cup-2026',
      resultsSlug: 'world-cup-2026',
      resultsUrlStrategy: 'seasonal'
    }, '2025-2026');

    assert.strictEqual(
      url,
      'oddsportal://root/football/world/world-cup-2026/results/'
    );
  });

  it('sample 评估应跳过占位符对阵，不得让其稀释 sampleLinked', async () => {
    const planner = createPlanner({
      sampleSize: 1,
      navigator: {
        async fetchFullSeasonArchive() {
          return {
            matches: [{
              hash: 'real-match',
              url: 'oddsportal://match/real',
              homeTeam: 'Mexico',
              awayTeam: 'South Africa',
              matchDate: '2026-06-11T19:00:00.000Z'
            }],
            pagesScanned: 1,
            totalCandidates: 1,
            sourceState: 'FULL_SEASON_SWEEP'
          };
        }
      }
    });

    const target = {
      leagueId: 77,
      league: { name: 'FIFA World Cup', country: 'world', slug: 'world-cup-2026' },
      season: '2025-2026',
      dbSeason: '2025/2026',
      resultsUrl: 'oddsportal://root/football/world/world-cup-2026/results/'
    };
    const pendingMatches = [
      {
        match_id: '77_20252026_0001',
        home_team: '1e',
        away_team: '3abcdf',
        match_date: '2026-06-29T20:30:00.000Z'
      },
      {
        match_id: '77_20252026_9999',
        home_team: 'Mexico',
        away_team: 'South Africa',
        match_date: '2026-06-11T19:00:00.000Z'
      }
    ];

    const selected = await planner.selectCandidateSource(target, pendingMatches, 0.75);

    assert.strictEqual(selected.sampleLinked, 1);
    assert.strictEqual(selected.candidates.length, 1);
  });

  it('awaiting finals 联赛在开赛前应跳过 Recon 扫描', async () => {
    let navigatorCalls = 0;
    const logs = [];
    const planner = createPlanner({
      navigator: {
        async fetchFullSeasonArchive() {
          navigatorCalls += 1;
          return {
            matches: [],
            pagesScanned: 0,
            totalCandidates: 0,
            sourceState: 'SOURCE_EMPTY'
          };
        }
      },
      logger: {
        info(event, payload) {
          logs.push({ event, payload });
        },
        warn() {},
        error() {}
      }
    });

    const target = {
      leagueId: 77,
      league: {
        name: 'FIFA World Cup',
        country: 'world',
        slug: 'world-cup-2026',
        awaitingFinals: true
      },
      season: '2025-2026',
      dbSeason: '2025/2026',
      resultsUrl: 'oddsportal://root/football/world/world-cup-2026/results/'
    };
    const pendingMatches = [{
      match_id: '77_20252026_5000',
      home_team: 'Mexico',
      away_team: 'South Africa',
      match_date: '2099-06-11T19:00:00.000Z'
    }];

    const selected = await planner.selectCandidateSource(target, pendingMatches, 0.75);

    assert.strictEqual(navigatorCalls, 0);
    assert.strictEqual(selected.extractResult.sourceState, 'SKIPPED_FUTURE_FINALS');
    assert.ok(logs.some((entry) => entry.event === 'skipping_future_finals'));
  });

  it('未标记 awaiting finals 的联赛不得被未来赛程跳过，中超应继续扫描', async () => {
    let navigatorCalls = 0;
    const planner = createPlanner({
      navigator: {
        async protocolArchiveExtract() {
          navigatorCalls += 1;
          return {
            matches: [],
            pagesScanned: 1,
            totalCandidates: 0,
            sourceState: 'SOURCE_EMPTY'
          };
        }
      }
    });

    const target = {
      leagueId: 120,
      league: {
        name: 'CSL',
        country: 'china',
        slug: 'super-league',
        resultsUrlStrategy: 'seasonless'
      },
      season: '2025-2026',
      dbSeason: '2025/2026',
      resultsUrl: 'oddsportal://root/football/china/super-league/results/'
    };
    const pendingMatches = [{
      match_id: '120_20252026_5000',
      home_team: 'Shanghai Port',
      away_team: 'Beijing Guoan',
      match_date: '2099-03-01T12:00:00.000Z'
    }];

    await planner.selectCandidateSource(target, pendingMatches, 0.75);

    assert.strictEqual(navigatorCalls, 1);
  });

  it('清零失配策略不得突破 0.75 硬门槛，但仍应强制启用多模式嗅探', () => {
    const planner = createPlanner();
    const target = {
      leagueId: 47,
      league: { id: 47, name: 'Premier League' },
      reconPolicy: { allowMismatchRetry: true }
    };
    const pendingMatches = [{
      match_id: '47_20252026_4813754',
      home_team: 'West Ham United',
      away_team: 'Leeds United',
      match_date: '2026-05-24T15:00:00.000Z',
      pipeline_status: 'RECON_MISMATCH'
    }];

    const policy = planner.resolveReconPolicy(target, pendingMatches, 0.5);

    assert.deepStrictEqual(policy, {
      allowMismatchRetry: true,
      hasMismatchRetry: true,
      effectiveConfidenceThreshold: 0.75,
      forceMultiMode: true
    });
  });

  it('allowMismatchRetry 开启时应向仓储请求 harvested 和 RECON_MISMATCH 目标集', async () => {
    const calls = [];
    const planner = createPlanner({
      repository: {
        async getReconEligibleMatches(season, leagueName, options) {
          calls.push({ season, leagueName, options });
          return [];
        }
      }
    });

    await planner.loadReconPendingMatches({
      dbSeason: '2025/2026',
      league: { name: 'Premier League' }
    }, {
      allowMismatchRetry: true
    });

    assert.deepStrictEqual(calls, [{
      season: '2025/2026',
      leagueName: 'Premier League',
      options: {
        allowMismatchRetry: true,
        allNonLinked: false
      }
    }]);
  });

  it('allNonLinked 开启时应向仓储请求全量非 Linked 目标集', async () => {
    const calls = [];
    const planner = createPlanner({
      repository: {
        async getReconEligibleMatches(season, leagueName, options) {
          calls.push({ season, leagueName, options });
          return [];
        }
      }
    });

    await planner.loadReconPendingMatches({
      dbSeason: '2025/2026',
      league: { name: 'Premier League' }
    }, {
      allNonLinked: true
    });

    assert.deepStrictEqual(calls, [{
      season: '2025/2026',
      leagueName: 'Premier League',
      options: {
        allowMismatchRetry: false,
        allNonLinked: true
      }
    }]);
  });

  it('seasonless 跨年联赛应组合当前赛季页与历史年份结果页', async () => {
    const calls = [];
    const planner = createPlanner({
      navigator: {
        async protocolArchiveExtract(url, options) {
          calls.push({ type: 'protocol', url, options });
          return {
            matches: [{
              hash: 'future-match',
              url: 'oddsportal://match/future',
              homeTeam: 'Qingdao Hainiu',
              awayTeam: 'Henan Songshan Longmen',
              matchDate: '2026-04-04T07:30:00.000Z'
            }],
            pagesScanned: 1,
            totalCandidates: 1,
            sourceState: 'CURRENT_TOURNAMENT'
          };
        },
        async fetchFullSeasonArchive(url, options) {
          calls.push({ type: 'archive', url, options });
          return {
            matches: [{
              hash: 'past-match',
              url: 'oddsportal://match/past',
              homeTeam: 'Changchun Yatai',
              awayTeam: 'Shanghai Shenhua',
              matchDate: '2025-06-29T10:30:00.000Z'
            }],
            pagesScanned: 1,
            totalCandidates: 1,
            sourceState: 'FULL_SEASON_SWEEP'
          };
        }
      }
    });

    const target = {
      leagueId: 120,
      league: {
        name: 'CSL',
        country: 'China',
        slug: 'super-league',
        resultsUrlStrategy: 'seasonless'
      },
      season: '2025-2026',
      dbSeason: '2025/2026',
      resultsUrl: 'oddsportal://root/football/china/super-league/results/'
    };
    const pendingMatches = [
      {
        match_id: '120_20252026_0001',
        home_team: 'Changchun Yatai',
        away_team: 'Shanghai Shenhua',
        match_date: '2025-06-29T10:30:00.000Z'
      },
      {
        match_id: '120_20252026_0002',
        home_team: 'Qingdao Hainiu',
        away_team: 'Henan FC',
        match_date: '2026-04-04T07:30:00.000Z'
      }
    ];

    const selected = await planner.selectCandidateSource(target, pendingMatches, 0.75);

    assert.strictEqual(calls.length, 2);
    assert.deepStrictEqual(
      calls.map((call) => call.url),
      [
        'oddsportal://root/football/china/super-league/results/',
        'oddsportal://root/football/china/super-league-2025/results/'
      ]
    );
    assert.strictEqual(calls[0].type, 'protocol');
    assert.strictEqual(calls[0].options.preferCurrentSeasonSource, true);
    assert.strictEqual(selected.source.url, 'oddsportal://root/football/china/super-league/results/');
    assert.strictEqual(selected.candidates.length, 1);
    assert.strictEqual(selected.sampleLinked, 1);
  });

  it('MLS 首个 current source 超时后应继续回退到备用 URL', async () => {
    const calls = [];
    const logs = [];
    const planner = createPlanner({
      navigator: {
        async protocolArchiveExtract(url, options) {
          calls.push({ url, options });
          if (url.endsWith('/football/usa/mls/results/')) {
            throw new Error('page.goto: Timeout 20000ms exceeded');
          }
          return {
            matches: [{
              hash: 'mls-root-match',
              url: 'oddsportal://match/mls-root',
              homeTeam: 'Inter Miami',
              awayTeam: 'LA Galaxy',
              matchDate: '2025-08-17T23:30:00.000Z'
            }],
            pagesScanned: 2,
            totalCandidates: 1,
            sourceState: 'CURRENT_TOURNAMENT'
          };
        }
      },
      logger: {
        info(event, payload) {
          logs.push({ level: 'info', event, payload });
        },
        warn(event, payload) {
          logs.push({ level: 'warn', event, payload });
        },
        error() {}
      }
    });

    const target = {
      leagueId: 130,
      league: {
        id: 130,
        name: 'MLS',
        country: 'usa',
        slug: 'mls',
        resultsUrlStrategy: 'seasonless',
        additionalResultsPaths: ['/football/{country}/{league}/']
      },
      season: '2025-2026',
      dbSeason: '2025/2026',
      resultsUrl: 'oddsportal://root/football/usa/mls/results/'
    };
    const pendingMatches = [{
      match_id: '130_20252026_5000',
      home_team: 'Inter Miami',
      away_team: 'LA Galaxy',
      match_date: '2025-08-17T23:30:00.000Z'
    }];

    const selected = await planner.selectCandidateSource(target, pendingMatches, 0.75);

    assert.ok(calls.length >= 2);
    assert.deepStrictEqual(
      calls.slice(0, 2).map((entry) => entry.url),
      [
        'oddsportal://root/football/usa/mls/results/',
        'oddsportal://root/football/usa/mls/'
      ]
    );
    assert.notStrictEqual(
      calls[0].options.circuitBreakerKey,
      calls[1].options.circuitBreakerKey
    );
    assert.ok(logs.some((entry) => entry.event === 'recon_candidate_source_failed'));
    assert.ok(selected.sampleLinked >= 1);
    assert.strictEqual(selected.candidates.length, 1);
    assert.ok(selected.source.url.includes('/football/usa/mls/'));
  });
});
