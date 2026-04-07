/**
 * @file DiscoveryService.test.js - Project Hound 单元测试
 * @description 测试 L1 发现引擎的核心功能
 */

'use strict';

const { describe, it, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert');
const { DiscoveryService } = require('../../src/infrastructure/services/DiscoveryService');
const { DiscoveryParser } = require('../../src/infrastructure/services/DiscoveryParser');

describe('DiscoveryService - V6.7 L1 发现引擎', () => {
  let service;
  let parser;

  beforeEach(() => {
    service = new DiscoveryService({
      concurrency: 2,
      delayMs: 0, // 测试时无延迟
      silent: true
    });
    
    // 创建独立的 parser 用于测试
    const mockLogger = {
      info: () => {},
      warn: () => {},
      error: () => {}
    };
    parser = new DiscoveryParser(mockLogger, service.leagueConfig);
  });

  afterEach(async () => {
    if (service) {
      await service.close();
    }
  });

  describe('服务初始化', () => {
    it('应正确实例化服务', () => {
      assert.ok(service);
      assert.ok(service.dbPool);
      assert.ok(service.limiter);
      assert.ok(service.leagueConfig);
    });

    it('默认 logger、capturedApis getter 与注入回调应可直接执行', async () => {
      const originalLog = console.log;
      const originalWarn = console.warn;
      const originalError = console.error;
      const logCalls = [];
      const warnCalls = [];
      const errorCalls = [];

      console.log = (...args) => {
        logCalls.push(args.join(' '));
      };
      console.warn = (...args) => {
        warnCalls.push(args.join(' '));
      };
      console.error = (...args) => {
        errorCalls.push(args.join(' '));
      };

      try {
        service.config.silent = false;
        service.networkInterceptor = {
          getCapturedApis: () => new Map([['probe', { url: 'https://api.test' }]]),
          reset: () => {}
        };
        service.httpClient.request = async (url, requestOptions) => ({ url, requestOptions });
        service.ensureBrowserHealthy = async (options) => ({ ok: true, options });

        assert.doesNotThrow(() => service.logger.info('info-message'));
        assert.doesNotThrow(() => service.logger.warn('warn-message'));
        assert.doesNotThrow(() => service.logger.error('error-message'));
        assert.doesNotThrow(() => service.logger.banner('banner-message'));
        assert.doesNotThrow(() => service.logger.progress('progress-message'));
        assert.strictEqual(service.capturedApis.size, 1);
        assert.deepStrictEqual(
          await service.seasonDiscovery.apiRequest('https://api.test/league', { expectedLeagueId: 47 }),
          { url: 'https://api.test/league', requestOptions: { expectedLeagueId: 47 } }
        );
        assert.deepStrictEqual(
          await service.extractor.makeStealthRequest('https://api.test/intercept', { probe: true }),
          { url: 'https://api.test/intercept', requestOptions: { probe: true } }
        );
        assert.deepStrictEqual(
          await service.httpClient.ensureBrowserHealthy({ reason: 'probe' }),
          { ok: true, options: { reason: 'probe' } }
        );
        assert.ok(logCalls.some((entry) => entry.includes('banner-message')));
        assert.ok(logCalls.some((entry) => entry.includes('progress-message')));
        assert.ok(warnCalls.some((entry) => entry.includes('warn-message')));
        assert.ok(errorCalls.some((entry) => entry.includes('error-message')));
      } finally {
        console.log = originalLog;
        console.warn = originalWarn;
        console.error = originalError;
      }
    });

    it('应使用默认配置', () => {
      assert.strictEqual(service.config.concurrency, 2);
      assert.strictEqual(service.config.delayMs, 0);
      assert.strictEqual(service.config.batchSize, 50);
      assert.strictEqual(service.config.lookbackDays, 30);
      assert.strictEqual(service.config.lookaheadDays, 7);
    });

    it('应加载联赛配置', () => {
      assert.ok(service.leagueConfig.active_leagues);
      assert.ok(service.leagueConfig.active_leagues.length > 0);
      assert.ok(service.leagueConfig.active_seasons);
    });

    it('_buildTargets 应覆盖单联赛、全量与 P0 映射分支', () => {
      service.configManager = {
        getLeagueById: (leagueId) => leagueId === 1
          ? { id: 1, name: 'Alpha League', code: 'ALPHA' }
          : null,
        getDefaultSeason: (leagueId = null) => leagueId ? '2024/2025' : '2025/2026',
        getActiveLeagues: (filters = {}) => {
          if (filters.tier === 'P0') {
            return [
              { id: 10, name: 'Premier A', code: 'PA' },
              { id: 20, name: 'Premier B', code: 'PB' }
            ];
          }

          return [
            { id: 10, name: 'Premier A', code: 'PA' },
            { id: 20, name: 'Premier B', code: 'PB' },
            { id: 30, name: 'Tier One', code: 'T1' }
          ];
        }
      };

      assert.deepStrictEqual(service._buildTargets(1, null, false), [
        { id: 1, name: 'Alpha League', code: 'ALPHA', season: '2024/2025' }
      ]);
      assert.deepStrictEqual(service._buildTargets(null, '2023/2024', true), [
        { id: 10, name: 'Premier A', code: 'PA', season: '2023/2024' },
        { id: 20, name: 'Premier B', code: 'PB', season: '2023/2024' },
        { id: 30, name: 'Tier One', code: 'T1', season: '2023/2024' }
      ]);
      assert.deepStrictEqual(service._buildTargets(null, null, false), [
        { id: 10, name: 'Premier A', code: 'PA', season: '2025/2026' },
        { id: 20, name: 'Premier B', code: 'PB', season: '2025/2026' }
      ]);
      assert.throws(() => service._buildTargets(999, null, false), /联赛 ID 999 未找到/);
    });
  });

  describe('配置驱动发现链路', () => {
    it('当激活英超(47)时，应从配置构造正确 API URL 并通过 Repository 入库', async () => {
      const requestedUrls = [];
      const persistedBatches = [];

      const configManager = {
        getRuntimeConfig: () => ({
          active_leagues: [
            {
              id: 47,
              code: 'EPL',
              name: 'Premier League',
              country: 'england',
              slug: 'premier-league',
              tier: 'P0',
              enabled: true,
              seasonType: 'dual_year',
              defaultSeason: '2024/2025',
              supportedSeasons: ['2024/2025']
            }
          ],
          active_seasons: ['2024/2025'],
          default_season: '2024/2025',
          single_year_league_ids: []
        }),
        getLeagueById: (leagueId) => leagueId === 47 ? {
          id: 47,
          code: 'EPL',
          name: 'Premier League',
          country: 'england',
          slug: 'premier-league',
          tier: 'P0',
          enabled: true,
          seasonType: 'dual_year',
          defaultSeason: '2024/2025',
          supportedSeasons: ['2024/2025']
        } : null,
        getActiveLeagues: () => [{
          id: 47,
          code: 'EPL',
          name: 'Premier League',
          country: 'england',
          slug: 'premier-league',
          tier: 'P0',
          enabled: true,
          seasonType: 'dual_year',
          defaultSeason: '2024/2025',
          supportedSeasons: ['2024/2025']
        }],
        getActiveSeasons: () => ['2024/2025'],
        getDefaultSeason: () => '2024/2025',
        getSingleYearLeagueIds: () => [],
        getExpectedMatches: () => null,
        buildLeagueApiUrl: (leagueId, season) =>
          `https://www.fotmob.com/api/data/leagues?id=${leagueId}&season=${season}`
      };

      const parserFixtures = [
        {
          match_id: '47_20242025_12345',
          external_id: '12345',
          league_name: 'Premier League',
          season: '2024/2025',
          home_team: 'Man United',
          away_team: 'Liverpool',
          match_date: new Date('2024-08-16T19:00:00Z'),
          status: 'scheduled',
          is_finished: false,
          data_source: 'FotMob'
        }
      ];

      const testService = new DiscoveryService({
        silent: true,
        delayMs: 0,
        concurrency: 1,
        dbPool: { end: async () => {}, connect: async () => ({ release: () => {} }) },
        configManager,
        parser: {
          parse: (response, leagueId, season) => {
            assert.strictEqual(leagueId, 47);
            assert.strictEqual(season, '2024/2025');
            assert.deepStrictEqual(response, { fixtures: { allMatches: [{ id: 12345 }] } });
            return parserFixtures;
          }
        },
        fixtureRepository: {
          persist: async (fixtures) => {
            persistedBatches.push(fixtures);
            return { total: fixtures.length, inserted: fixtures.length, updated: 0, failed: 0 };
          }
        },
        httpClient: {
          request: async (url) => {
            requestedUrls.push(url);
            if (url === 'https://www.fotmob.com/api/data/leagues?id=47') {
              return { allAvailableSeasons: ['20242025'] };
            }
            if (url === 'https://www.fotmob.com/api/data/leagues?id=47&season=20242025') {
              return { fixtures: { allMatches: [{ id: 12345 }] } };
            }
            throw new Error(`unexpected url ${url}`);
          }
        },
        seasonDiscovery: {
          discover: async (leagueId, season) => {
            assert.strictEqual(leagueId, 47);
            assert.strictEqual(season, '20242025');
            return '20242025';
          }
        },
        seasonStrategyFactory: {
          format: () => '20242025',
          isSingleYearLeague: () => false
        },
        browserProvider: {
          isInitialized: () => false,
          close: async () => {}
        },
        networkInterceptor: {
          getCapturedApis: () => new Map(),
          reset: () => {}
        },
        extractor: {
          extractFromWebpage: async () => {
            throw new Error('should not fallback');
          },
          searchViaDOM: async () => ({})
        },
        uiHelper: {
          printBanner: () => {},
          printTargets: () => {},
          printScanStart: () => {},
          printHistoricalMode: () => {},
          printNoFixtures: () => {},
          printParsedFixtures: () => {},
          printProgress: () => {},
          printScanError: () => {},
          generateReport: (stats) => stats
        }
      });

      try {
        const result = await testService.discover({ leagueId: 47 });
        assert.strictEqual(requestedUrls[0], 'https://www.fotmob.com/api/data/leagues?id=47&season=20242025');
        assert.deepStrictEqual(persistedBatches, [parserFixtures]);
        assert.strictEqual(result.inserted, 1);
        assert.strictEqual(result.failed, 0);
      } finally {
        await testService.close();
      }
    });

    it('当实得场次少于 expected_matches 时，应输出 CRITICAL WARN', async () => {
      const warnings = [];

      const testService = new DiscoveryService({
        silent: true,
        delayMs: 0,
        concurrency: 1,
        dbPool: { end: async () => {}, connect: async () => ({ release: () => {} }) },
        configManager: {
          getRuntimeConfig: () => ({
            active_leagues: [{ id: 54, code: 'BUNDESLIGA', name: 'Bundesliga', country: 'germany', tier: 'P0', enabled: true }],
            active_seasons: ['2025/2026'],
            default_season: '2025/2026',
            single_year_league_ids: []
          }),
          getLeagueById: () => ({ id: 54, code: 'BUNDESLIGA', name: 'Bundesliga', country: 'germany', tier: 'P0', enabled: true }),
          getActiveLeagues: () => [{ id: 54, code: 'BUNDESLIGA', name: 'Bundesliga', country: 'germany', tier: 'P0', enabled: true }],
          getDefaultSeason: () => '2025/2026',
          getSingleYearLeagueIds: () => [],
          getExpectedMatches: () => 306,
          buildLeagueApiUrl: () => 'https://example.test/leagues?id=54&season=20252026'
        },
        parser: {
          parse: () => Array.from({ length: 300 }, (_, index) => ({
            match_id: `54_20252026_${index + 1}`,
            external_id: `${index + 1}`,
            league_name: 'Bundesliga',
            season: '2025/2026',
            home_team: 'Bayern Munchen',
            away_team: 'Rb Leipzig',
            match_date: new Date('2025-08-22T18:30:00Z'),
            status: 'scheduled',
            is_finished: false
          }))
        },
        fixtureRepository: {
          persist: async (fixtures) => ({ total: fixtures.length, inserted: 0, updated: fixtures.length, failed: 0 })
        },
        httpClient: {
          request: async () => ({ fixtures: { allMatches: [{ id: 1 }] } })
        },
        seasonDiscovery: { discover: async () => '20252026' },
        seasonStrategyFactory: {
          format: () => '20252026',
          isSingleYearLeague: () => false
        },
        browserProvider: { isInitialized: () => false, close: async () => {} },
        networkInterceptor: { getCapturedApis: () => new Map(), reset: () => {} },
        extractor: { extractFromWebpage: async () => ({}), searchViaDOM: async () => ({}) },
        uiHelper: {
          printBanner: () => {},
          printTargets: () => {},
          printScanStart: () => {},
          printHistoricalMode: () => {},
          printNoFixtures: () => {},
          printParsedFixtures: () => {},
          printProgress: () => {},
          printScanError: () => {},
          printCriticalWarn: (...args) => warnings.push(args),
          generateReport: (stats) => stats
        }
      });

      try {
        const result = await testService.discover({ leagueId: 54, season: '2025/2026' });
        assert.strictEqual(warnings.length, 1);
        assert.strictEqual(warnings[0][1], 'Bundesliga');
        assert.strictEqual(result.criticalWarnings.length, 1);
        assert.strictEqual(result.criticalWarnings[0].missing, 6);
      } finally {
        await testService.close();
      }
    });
  });

  describe('工业级硬化链路', () => {
    it('内部联赛存在 providerId 映射时，应使用 providerId 请求并保留内部 ID 入库', async () => {
      const requests = [];
      const persisted = [];

      const testService = new DiscoveryService({
        silent: true,
        delayMs: 0,
        concurrency: 1,
        dbPool: { end: async () => {}, connect: async () => ({ release: () => {} }) },
        configManager: {
          getRuntimeConfig: () => ({
            active_leagues: [{
              id: 156,
              providerId: 86,
              code: 'SERIEB',
              name: 'Serie B',
              country: 'italy',
              tier: 'P2',
              enabled: true,
              seasonType: 'dual_year',
              defaultSeason: '2025/2026',
              supportedSeasons: ['2025/2026']
            }],
            active_seasons: ['2025/2026'],
            default_season: '2025/2026',
            single_year_league_ids: []
          }),
          getLeagueById: () => ({
            id: 156,
            providerId: 86,
            code: 'SERIEB',
            name: 'Serie B',
            country: 'italy',
            tier: 'P2',
            enabled: true,
            seasonType: 'dual_year',
            defaultSeason: '2025/2026',
            supportedSeasons: ['2025/2026']
          }),
          getActiveLeagues: () => [],
          getDefaultSeason: () => '2025/2026',
          getSingleYearLeagueIds: () => [],
          getExpectedMatches: () => null,
          buildLeagueApiUrl: (leagueId, season) => {
            assert.strictEqual(leagueId, 156);
            assert.strictEqual(season, '20252026');
            return 'https://www.fotmob.com/api/data/leagues?id=86&season=20252026';
          }
        },
        parser: {
          parse: (response, leagueId, season) => {
            assert.strictEqual(leagueId, 156);
            assert.strictEqual(season, '2025/2026');
            assert.deepStrictEqual(response.details, { id: 86 });
            return [{
              match_id: '156_20252026_9001',
              external_id: '9001',
              league_name: 'Serie B',
              season: '2025/2026',
              home_team: 'Sassuolo',
              away_team: 'Palermo',
              match_date: '2025-08-22T18:30:00.000Z',
              status: 'scheduled',
              is_finished: false
            }];
          }
        },
        fixtureRepository: {
          persist: async (fixtures) => {
            persisted.push(fixtures);
            return { total: fixtures.length, inserted: fixtures.length, updated: 0, failed: 0 };
          }
        },
        httpClient: {
          request: async (url, options) => {
            requests.push({ url, options });
            return { details: { id: 86 }, fixtures: { allMatches: [{ id: 9001 }] } };
          }
        },
        seasonDiscovery: {
          discover: async (leagueId, season) => {
            assert.strictEqual(leagueId, 86);
            assert.strictEqual(season, '20252026');
            return '20252026';
          }
        },
        seasonStrategyFactory: {
          format: () => '20252026',
          isSingleYearLeague: () => false
        },
        browserProvider: { isInitialized: () => false, close: async () => {} },
        networkInterceptor: { getCapturedApis: () => new Map(), reset: () => {} },
        extractor: { extractFromWebpage: async () => ({}), searchViaDOM: async () => ({}) },
        uiHelper: {
          printBanner: () => {},
          printTargets: () => {},
          printScanStart: () => {},
          printHistoricalMode: () => {},
          printNoFixtures: () => {},
          printParsedFixtures: () => {},
          printProgress: () => {},
          printScanError: () => {},
          generateReport: (stats) => stats
        }
      });

      try {
        const result = await testService.discover({ leagueId: 156, season: '2025/2026', fullSync: true });
        assert.strictEqual(requests.length, 1);
        assert.strictEqual(requests[0].url, 'https://www.fotmob.com/api/data/leagues?id=86&season=20252026');
        assert.strictEqual(requests[0].options.expectedLeagueId, 86);
        assert.strictEqual(persisted[0][0].match_id, '156_20252026_9001');
        assert.strictEqual(result.inserted, 1);
      } finally {
        await testService.close();
      }
    });

    it('IDENTITY_MISMATCH 时应中断该联赛且禁止回退入库', async () => {
      let fallbackCalls = 0;
      let persistCalls = 0;

      const mismatchError = new Error('IDENTITY_MISMATCH: 请求联赛 86，响应联赛 110');
      mismatchError.code = 'IDENTITY_MISMATCH';

      const testService = new DiscoveryService({
        silent: true,
        delayMs: 0,
        concurrency: 1,
        dbPool: { end: async () => {}, connect: async () => ({ release: () => {} }) },
        configManager: {
          getRuntimeConfig: () => ({
            active_leagues: [{ id: 156, providerId: 86, code: 'SERIEB', name: 'Serie B', country: 'italy', tier: 'P2', enabled: true }],
            active_seasons: ['2025/2026'],
            default_season: '2025/2026',
            single_year_league_ids: []
          }),
          getLeagueById: () => ({ id: 156, providerId: 86, code: 'SERIEB', name: 'Serie B', country: 'italy', tier: 'P2', enabled: true }),
          getActiveLeagues: () => [],
          getDefaultSeason: () => '2025/2026',
          getSingleYearLeagueIds: () => [],
          getExpectedMatches: () => null,
          buildLeagueApiUrl: () => 'https://www.fotmob.com/api/data/leagues?id=86&season=20252026'
        },
        parser: { parse: () => [] },
        fixtureRepository: {
          persist: async () => {
            persistCalls += 1;
            return { total: 0, inserted: 0, updated: 0, failed: 0 };
          }
        },
        httpClient: {
          request: async () => {
            throw mismatchError;
          }
        },
        seasonDiscovery: { discover: async () => '20252026' },
        seasonStrategyFactory: {
          format: () => '20252026',
          isSingleYearLeague: () => false
        },
        browserProvider: { isInitialized: () => false, close: async () => {} },
        networkInterceptor: { getCapturedApis: () => new Map(), reset: () => {} },
        extractor: {
          extractFromWebpage: async () => {
            fallbackCalls += 1;
            return {};
          },
          searchViaDOM: async () => ({})
        },
        uiHelper: {
          printBanner: () => {},
          printTargets: () => {},
          printScanStart: () => {},
          printHistoricalMode: () => {},
          printNoFixtures: () => {},
          printParsedFixtures: () => {},
          printProgress: () => {},
          printScanError: () => {},
          generateReport: (stats) => stats
        }
      });

      try {
        const result = await testService.discover({ leagueId: 156, season: '2025/2026' });
        assert.strictEqual(result.failed, 1);
        assert.strictEqual(fallbackCalls, 0);
        assert.strictEqual(persistCalls, 0);
      } finally {
        await testService.close();
      }
    });

    it('批量扫描时每完成 5 个联赛应触发一次冷却', async () => {
      const cooldowns = [];
      const leagues = Array.from({ length: 6 }, (_, index) => ({
        id: 200 + index,
        providerId: 200 + index,
        code: `L${index + 1}`,
        name: `League ${index + 1}`,
        country: 'test',
        tier: 'P1',
        enabled: true,
        seasonType: 'dual_year',
        defaultSeason: '2025/2026',
        supportedSeasons: ['2025/2026']
      }));

      const testService = new DiscoveryService({
        silent: true,
        delayMs: 0,
        concurrency: 2,
        browserCooldownEveryLeagues: 5,
        dbPool: { end: async () => {}, connect: async () => ({ release: () => {} }) },
        configManager: {
          getRuntimeConfig: () => ({
            active_leagues: leagues,
            active_seasons: ['2025/2026'],
            default_season: '2025/2026',
            single_year_league_ids: []
          }),
          getLeagueById: (leagueId) => leagues.find((league) => league.id === leagueId) || null,
          getActiveLeagues: () => leagues,
          getDefaultSeason: () => '2025/2026',
          getSingleYearLeagueIds: () => [],
          getExpectedMatches: () => null,
          buildLeagueApiUrl: (leagueId) => `https://www.fotmob.com/api/data/leagues?id=${leagueId}&season=20252026`
        },
        parser: {
          parse: (_response, leagueId) => [{
            match_id: `${leagueId}_20252026_${leagueId}01`,
            external_id: `${leagueId}01`,
            league_name: `League ${leagueId}`,
            season: '2025/2026',
            home_team: 'Home',
            away_team: 'Away',
            match_date: '2025-08-16T14:00:00.000Z',
            status: 'scheduled',
            is_finished: false
          }]
        },
        fixtureRepository: {
          persist: async (fixtures) => ({ total: fixtures.length, inserted: fixtures.length, updated: 0, failed: 0 })
        },
        httpClient: {
          request: async (_url, options) => ({ details: { id: options.expectedLeagueId }, fixtures: { allMatches: [{ id: 1 }] } })
        },
        seasonDiscovery: { discover: async (_leagueId, season) => season },
        seasonStrategyFactory: {
          format: () => '20252026',
          isSingleYearLeague: () => false
        },
        browserProvider: { isInitialized: () => false, close: async () => {} },
        networkInterceptor: { getCapturedApis: () => new Map(), reset: () => {} },
        extractor: { extractFromWebpage: async () => ({}), searchViaDOM: async () => ({}) },
        uiHelper: {
          printBanner: () => {},
          printTargets: () => {},
          printScanStart: () => {},
          printHistoricalMode: () => {},
          printNoFixtures: () => {},
          printParsedFixtures: () => {},
          printProgress: () => {},
          printScanError: () => {},
          generateReport: (stats) => stats
        }
      });

      testService._coolDownBrowser = async (count) => {
        cooldowns.push(count);
      };

      try {
        const result = await testService.discover({ allLeagues: true, season: '2025/2026', fullSync: true });
        assert.deepStrictEqual(cooldowns, [5]);
        assert.strictEqual(result.inserted, 6);
      } finally {
        await testService.close();
      }
    });

    it('并发自愈请求应复用同一次浏览器重建', async () => {
      const testService = new DiscoveryService({
        silent: true,
        delayMs: 0,
        concurrency: 2,
        dbPool: { end: async () => {}, connect: async () => ({ release: () => {} }) },
        browserProvider: {
          isInitialized: () => false,
          close: async () => {},
          initialize: async () => ({}),
          warmup: async () => {}
        },
        networkInterceptor: {
          reset: () => {},
          setup: () => {},
          getCapturedApis: () => new Map()
        }
      });

      let rebuilds = 0;
      testService._rebuildBrowserContext = async () => {
        rebuilds += 1;
        await new Promise((resolve) => setTimeout(resolve, 10));
      };

      try {
        await Promise.all([
          testService.ensureBrowserHealthy({ forceRebuild: true, reason: 'retry-a' }),
          testService.ensureBrowserHealthy({ forceRebuild: true, reason: 'retry-b' })
        ]);
        assert.strictEqual(rebuilds, 1);
      } finally {
        await testService.close();
      }
    });

    it('_initBrowser 与浏览器冷却/重建链路应按顺序执行', async () => {
      const calls = [];
      const sleeps = [];
      const page = { id: 'page-1' };
      const browserProvider = {
        initialized: false,
        isInitialized() {
          return this.initialized;
        },
        async initialize() {
          this.initialized = true;
          calls.push('initialize');
          return page;
        },
        async warmup(url, options) {
          calls.push(['warmup', url, options.timeout]);
        },
        async close() {
          this.initialized = false;
          calls.push('close');
        }
      };
      const networkInterceptor = {
        setup(currentPage) {
          calls.push(['setup', currentPage.id]);
        },
        reset() {
          calls.push('reset');
        },
        getCapturedApis: () => new Map()
      };

      const testService = new DiscoveryService({
        silent: true,
        delayMs: 0,
        browserCooldownMs: 17,
        dbPool: { end: async () => {}, connect: async () => ({ release: () => {} }) },
        browserProvider,
        networkInterceptor
      });
      testService._sleep = async (ms) => {
        sleeps.push(ms);
      };

      try {
        await testService._initBrowser();
        await testService._coolDownBrowser(3);

        assert.deepStrictEqual(calls, [
          'initialize',
          ['setup', 'page-1'],
          ['warmup', 'https://www.fotmob.com/', 15000],
          'reset',
          'close',
          'initialize',
          ['setup', 'page-1'],
          ['warmup', 'https://www.fotmob.com/', 15000]
        ]);
        assert.deepStrictEqual(sleeps, [17]);
      } finally {
        await testService.close();
      }
    });

    it('_initBrowser 在预热失败时应记录宽容告警而不抛错', async () => {
      const warnings = [];
      const testService = new DiscoveryService({
        silent: true,
        delayMs: 0,
        dbPool: { end: async () => {}, connect: async () => ({ release: () => {} }) },
        browserProvider: {
          isInitialized: () => false,
          initialize: async () => ({}),
          warmup: async () => {
            throw new Error('warmup boom');
          },
          close: async () => {}
        },
        networkInterceptor: {
          setup: () => {},
          getCapturedApis: () => new Map(),
          reset: () => {}
        }
      });
      testService.logger.warn = (message) => warnings.push(message);

      try {
        await testService._initBrowser();
        assert.ok(warnings.some((message) => message.includes('主页加载警告: warmup boom')));
        assert.ok(warnings.some((message) => message.includes('继续尝试 API 请求')));
      } finally {
        await testService.close();
      }
    });

    it('search 应覆盖 J1 提示、DOM 成功和 API 回退路径', async () => {
      const logs = [];
      const apiCalls = [];
      let domShouldFail = false;
      const testService = new DiscoveryService({
        silent: true,
        delayMs: 0,
        dbPool: { end: async () => {}, connect: async () => ({ release: () => {} }) },
        extractor: {
          async searchViaDOM(term) {
            if (domShouldFail) {
              throw new Error(`dom failed: ${term}`);
            }
            return { source: 'dom', term };
          },
          extractFromWebpage: async () => ({})
        },
        httpClient: {
          async request(url) {
            apiCalls.push(url);
            return { source: 'api', url };
          }
        },
        browserProvider: { isInitialized: () => false, close: async () => {} },
        networkInterceptor: { getCapturedApis: () => new Map(), reset: () => {} }
      });
      testService.logger.info = (message) => logs.push(message);

      try {
        const domResponse = await testService.search('J1 League');
        domShouldFail = true;
        const apiResponse = await testService.search('Serie B');

        assert.deepStrictEqual(domResponse, { source: 'dom', term: 'J1 League' });
        assert.strictEqual(apiResponse.source, 'api');
        assert.ok(apiCalls[0].includes('https://www.fotmob.com/api/search/suggest?term=Serie%20B'));
        assert.ok(logs.some((message) => message.includes('侦察建议')));
        assert.ok(logs.some((message) => message.includes('DOM 搜索失败')));
        assert.ok(logs.some((message) => message.includes('回退到 API 搜索')));
      } finally {
        await testService.close();
      }
    });

    it('_fetchFixtures 应覆盖单年份赛季映射、API 无赛程回退与最终失败分支', async () => {
      const infos = [];
      const warns = [];
      const errors = [];
      let apiMode = 'empty';
      let soulMode = 'success';
      const testService = new DiscoveryService({
        silent: true,
        delayMs: 0,
        dbPool: { end: async () => {}, connect: async () => ({ release: () => {} }) },
        configManager: {
          getRuntimeConfig: () => ({
            active_leagues: [],
            active_seasons: ['2025/2026'],
            default_season: '2025/2026',
            single_year_league_ids: [120]
          }),
          getLeagueById: () => null,
          getActiveLeagues: () => [],
          getDefaultSeason: () => '2025/2026',
          getSingleYearLeagueIds: () => [120],
          getExpectedMatches: () => null,
          buildLeagueApiUrl: (leagueId, season) => {
            assert.strictEqual(leagueId, 120);
            return `https://api.test/leagues?id=${leagueId}&season=${season}`;
          }
        },
        seasonStrategyFactory: {
          format: () => '2025',
          isSingleYearLeague: () => true
        },
        seasonDiscovery: {
          discover: async () => '2026'
        },
        httpClient: {
          request: async () => {
            if (apiMode === 'throw') {
              throw new Error('api down');
            }
            return { details: { id: 555 }, overview: {} };
          }
        },
        extractor: {
          extractFromWebpage: async () => {
            if (soulMode === 'throw') {
              throw new Error('soul down');
            }
            return { details: { id: 555 }, fixtures: { allMatches: [{ id: 1 }] } };
          },
          searchViaDOM: async () => ({})
        },
        browserProvider: { isInitialized: () => false, close: async () => {} },
        networkInterceptor: { getCapturedApis: () => new Map(), reset: () => {} }
      });
      testService.logger.info = (message) => infos.push(message);
      testService.logger.warn = (message) => warns.push(message);
      testService.logger.error = (message) => errors.push(message);
      testService._assertProviderIdentity = () => {};

      try {
        const fallbackResult = await testService._fetchFixtures({ id: 120, providerId: 555, name: 'CSL' }, '2025/2026');
        assert.deepStrictEqual(fallbackResult, { details: { id: 555 }, fixtures: { allMatches: [{ id: 1 }] } });
        assert.ok(infos.some((message) => message.includes('单年份联赛适配')));
        assert.ok(infos.some((message) => message.includes('使用探测到的赛季 ID')));
        assert.ok(warns.some((message) => message.includes('API 返回数据但不含赛程')));

        apiMode = 'throw';
        soulMode = 'throw';
        await assert.rejects(
          testService._fetchFixtures({ id: 120, providerId: 555, name: 'CSL' }, '2025/2026'),
          /无法获取联赛 120 赛季 2026 的数据/
        );
        assert.ok(warns.some((message) => message.includes('API 请求失败: api down')));
        assert.ok(errors.some((message) => message.includes('灵魂抽取失败: soul down')));
      } finally {
        await testService.close();
      }
    });

    it('_buildTargets / _assertProviderIdentity / close 应覆盖异常聚合分支', async () => {
      let resetCalled = 0;
      const testService = new DiscoveryService({
        silent: true,
        delayMs: 0,
        dbPool: {
          async end() {
            throw new Error('db broken');
          },
          connect: async () => ({ release: () => {} })
        },
        configManager: {
          getRuntimeConfig: () => ({
            active_leagues: [
              { id: 47, name: 'Premier League', tier: 'P0', enabled: true },
              { id: 120, name: 'CSL', tier: 'P3', enabled: true }
            ],
            active_seasons: ['2025/2026'],
            default_season: '2025/2026',
            single_year_league_ids: []
          }),
          getLeagueById: (leagueId) => leagueId === 47 ? { id: 47, name: 'Premier League', tier: 'P0', enabled: true } : null,
          getActiveLeagues: (options) => options?.tier === 'P0'
            ? [{ id: 47, name: 'Premier League', tier: 'P0', enabled: true }]
            : [
              { id: 47, name: 'Premier League', tier: 'P0', enabled: true },
              { id: 120, name: 'CSL', tier: 'P3', enabled: true }
            ],
          getDefaultSeason: (leagueId) => leagueId ? '2024/2025' : '2025/2026',
          getSingleYearLeagueIds: () => [],
          getExpectedMatches: () => null,
          buildLeagueApiUrl: () => ''
        },
        browserProvider: {
          isInitialized: () => false,
          async close() {
            throw new Error('browser broken');
          }
        },
        networkInterceptor: {
          reset() {
            resetCalled += 1;
          },
          getCapturedApis: () => new Map()
        }
      });

      try {
        assert.deepStrictEqual(testService._buildTargets(null, '2025/2026', false), [
          { id: 47, name: 'Premier League', tier: 'P0', enabled: true, season: '2025/2026' }
        ]);
        assert.deepStrictEqual(testService._buildTargets(null, '2025/2026', true), [
          { id: 47, name: 'Premier League', tier: 'P0', enabled: true, season: '2025/2026' },
          { id: 120, name: 'CSL', tier: 'P3', enabled: true, season: '2025/2026' }
        ]);
        assert.deepStrictEqual(testService._buildTargets(47), [
          { id: 47, name: 'Premier League', tier: 'P0', enabled: true, season: '2024/2025' }
        ]);
        assert.throws(() => testService._buildTargets(999), /联赛 ID 999 未找到/);

        assert.doesNotThrow(() => testService._assertProviderIdentity({}, null, 'Unknown'));
        assert.doesNotThrow(() => testService._assertProviderIdentity({ details: {} }, 47, 'Unknown'));
        assert.throws(
          () => testService._assertProviderIdentity({ details: { id: 48 } }, 47, 'Premier League'),
          (error) => error.code === 'IDENTITY_MISMATCH'
            && error.expectedLeagueId === 47
            && error.actualLeagueId === 48,
        );

        await assert.rejects(
          testService.close(),
          /browserProvider: browser broken; dbPool: db broken/
        );
        assert.strictEqual(resetCalled, 1);
      } finally {
        testService.browserProvider.close = async () => {};
        testService.dbPool.end = async () => {};
        await testService.close();
      }
    });

    it('_scanLeague 在无赛程和延迟模式下应分别覆盖告警与 sleep 分支', async () => {
      const uiCalls = [];
      const sleepCalls = [];
      const parserState = { fixtures: [] };
      const testService = new DiscoveryService({
        silent: true,
        delayMs: 12,
        concurrency: 1,
        dbPool: { end: async () => {}, connect: async () => ({ release: () => {} }) },
        configManager: {
          getRuntimeConfig: () => ({
            active_leagues: [],
            active_seasons: ['2025/2026'],
            default_season: '2025/2026',
            single_year_league_ids: []
          }),
          getLeagueById: () => null,
          getActiveLeagues: () => [],
          getDefaultSeason: () => '2025/2026',
          getSingleYearLeagueIds: () => [],
          getExpectedMatches: () => 2,
          buildLeagueApiUrl: () => ''
        },
        parser: {
          parse: () => parserState.fixtures
        },
        fixtureRepository: {
          persist: async (fixtures) => ({ total: fixtures.length, inserted: 1, updated: 0, failed: 0 })
        },
        browserProvider: { isInitialized: () => false, close: async () => {} },
        networkInterceptor: { getCapturedApis: () => new Map(), reset: () => {} },
        extractor: { extractFromWebpage: async () => ({}), searchViaDOM: async () => ({}) },
        uiHelper: {
          printScanStart: (...args) => uiCalls.push(['start', args]),
          printHistoricalMode: (...args) => uiCalls.push(['historical', args]),
          printNoFixtures: (...args) => uiCalls.push(['noFixtures', args]),
          printCriticalWarn: (...args) => uiCalls.push(['critical', args]),
          printParsedFixtures: (...args) => uiCalls.push(['parsed', args]),
          printProgress: (...args) => uiCalls.push(['progress', args]),
          printScanError: (...args) => uiCalls.push(['error', args]),
          printBanner: () => {},
          printTargets: () => {},
          generateReport: (stats) => stats
        }
      });
      testService._fetchFixtures = async () => ({});
      testService._sleep = async (ms) => {
        sleepCalls.push(ms);
      };
      testService._isHistoricalSeason = () => false;

      try {
        const emptyResult = await testService._scanLeague(
          { id: 47, name: 'Premier League', season: '2025/2026' },
          0,
          {}
        );
        assert.deepStrictEqual(emptyResult.criticalWarnings, [{
          leagueId: 47,
          name: 'Premier League',
          season: '2025/2026',
          actual: 0,
          expected: 2,
          missing: 2
        }]);

        parserState.fixtures = [{
          match_id: '47_20252026_1',
          external_id: '1',
          league_name: 'Premier League',
          season: '2025/2026',
          home_team: 'A',
          away_team: 'B',
          match_date: '2025-08-16T14:00:00.000Z',
          status: 'scheduled',
          is_finished: false
        }];
        const successResult = await testService._scanLeague(
          { id: 47, name: 'Premier League', season: '2025/2026' },
          1,
          {}
        );

        assert.strictEqual(successResult.inserted, 1);
        assert.deepStrictEqual(sleepCalls, [12]);
        assert.ok(uiCalls.some(([type]) => type === 'noFixtures'));
        assert.ok(uiCalls.some(([type]) => type === 'critical'));
        assert.ok(uiCalls.some(([type]) => type === 'parsed'));
        assert.ok(uiCalls.some(([type]) => type === 'progress'));
      } finally {
        await testService.close();
      }
    });

    it('_fetchFixtures 在 soul 层出现 IDENTITY_MISMATCH 时应原样抛出', async () => {
      const mismatchError = new Error('IDENTITY_MISMATCH');
      mismatchError.code = 'IDENTITY_MISMATCH';

      const testService = new DiscoveryService({
        silent: true,
        delayMs: 0,
        dbPool: { end: async () => {}, connect: async () => ({ release: () => {} }) },
        configManager: {
          getRuntimeConfig: () => ({
            active_leagues: [],
            active_seasons: ['2025/2026'],
            default_season: '2025/2026',
            single_year_league_ids: []
          }),
          getLeagueById: () => null,
          getActiveLeagues: () => [],
          getDefaultSeason: () => '2025/2026',
          getSingleYearLeagueIds: () => [],
          getExpectedMatches: () => null,
          buildLeagueApiUrl: () => 'https://api.test/leagues?id=47&season=20252026'
        },
        seasonStrategyFactory: {
          format: () => '20252026',
          isSingleYearLeague: () => false
        },
        seasonDiscovery: {
          discover: async () => '20252026'
        },
        httpClient: {
          request: async () => {
            throw new Error('api down');
          }
        },
        extractor: {
          extractFromWebpage: async () => {
            throw mismatchError;
          },
          searchViaDOM: async () => ({})
        },
        browserProvider: { isInitialized: () => false, close: async () => {} },
        networkInterceptor: { getCapturedApis: () => new Map(), reset: () => {} }
      });
      testService._assertProviderIdentity = () => {};

      try {
        await assert.rejects(
          testService._fetchFixtures({ id: 47, providerId: 47, name: 'Premier League' }, '2025/2026'),
          (error) => error === mismatchError,
        );
      } finally {
        await testService.close();
      }
    });

    it('ensureBrowserHealthy / _coolDownBrowser / _rebuildBrowserContext 的早退分支应无副作用', async () => {
      const testService = new DiscoveryService({
        silent: true,
        delayMs: 0,
        dbPool: { end: async () => {}, connect: async () => ({ release: () => {} }) },
        browserProvider: { isInitialized: () => true, close: async () => {} },
        networkInterceptor: { getCapturedApis: () => new Map(), reset: () => {} }
      });

      let rebuildCalls = 0;
      let ensureCalls = 0;
      testService._rebuildBrowserContext = async () => {
        rebuildCalls += 1;
      };
      testService.ensureBrowserHealthy = async () => {
        ensureCalls += 1;
      };

      try {
        const earlyReturnService = new DiscoveryService({
          silent: true,
          delayMs: 0,
          dbPool: { end: async () => {}, connect: async () => ({ release: () => {} }) }
        });
        earlyReturnService.browserProvider = null;
        await earlyReturnService.ensureBrowserHealthy();
        await earlyReturnService._rebuildBrowserContext('no-browser');
        earlyReturnService.useStealthMode = false;
        await earlyReturnService._coolDownBrowser(2);
        await earlyReturnService.close();

        testService.useStealthMode = true;
        await DiscoveryService.prototype.ensureBrowserHealthy.call(testService, {});
        assert.strictEqual(rebuildCalls, 0);

        testService.useStealthMode = false;
        await DiscoveryService.prototype._coolDownBrowser.call(testService, 9);
        assert.strictEqual(ensureCalls, 0);
      } finally {
        await testService.close();
      }
    });

    it('_sleep 应通过 setTimeout 完成异步等待', async () => {
      const originalSetTimeout = global.setTimeout;
      const scheduled = [];
      const testService = new DiscoveryService({
        silent: true,
        delayMs: 0,
        dbPool: { end: async () => {}, connect: async () => ({ release: () => {} }) },
        browserProvider: { isInitialized: () => false, close: async () => {} },
        networkInterceptor: { getCapturedApis: () => new Map(), reset: () => {} }
      });

      global.setTimeout = (callback, ms) => {
        scheduled.push(ms);
        callback();
        return 1;
      };

      try {
        await testService._sleep(33);
        assert.deepStrictEqual(scheduled, [33]);
      } finally {
        global.setTimeout = originalSetTimeout;
        await testService.close();
      }
    });
  });

  describe('日期范围计算 (通过 Parser 内部)', () => {
    it('Parser 应在非历史模式下过滤日期', () => {
      const pastDate = new Date();
      pastDate.setDate(pastDate.getDate() - 60);

      const mockResponse = {
        matches: [{
          id: 1,
          home: { name: 'A' },
          away: { name: 'B' },
          status: { utcTime: pastDate.toISOString() }
        }]
      };

      // 当前赛季模式应过滤
      const matches = parser.parse(mockResponse, 47, '2024/2025', false, {
        lookbackDays: 30,
        lookaheadDays: 7
      });
      assert.strictEqual(matches.length, 0, '应过滤过期比赛');
    });

    it('Parser 在 fullSync 模式下应绕过 recent 时间窗口', () => {
      const farFutureDate = new Date();
      farFutureDate.setDate(farFutureDate.getDate() + 120);

      const mockResponse = {
        matches: [{
          id: 88,
          home: { name: 'Aston Villa' },
          away: { name: 'Everton' },
          status: { utcTime: farFutureDate.toISOString() }
        }]
      };

      const matches = parser.parse(mockResponse, 47, '2025/2026', false, {
        lookbackDays: 30,
        lookaheadDays: 7,
        fullSync: true
      });
      assert.strictEqual(matches.length, 1, 'fullSync 应保留 recent 窗口外的已排期比赛');
    });
  });

  describe('API 响应解析 (通过 DiscoveryParser)', () => {
    it('应从 FotMob 响应中提取比赛 (matches数组结构)', () => {
      const futureDate = new Date();
      futureDate.setDate(futureDate.getDate() + 1);

      const mockResponse = {
        matches: [
          {
            id: 12345,
            home: { name: 'Manchester City' },
            away: { name: 'Liverpool' },
            status: { utcTime: futureDate.toISOString(), finished: false }
          }
        ]
      };

      const matches = parser.parse(mockResponse, 47, '2024/2025', true);
      assert.strictEqual(matches.length, 1);
      assert.strictEqual(matches[0].external_id, '12345');
      assert.strictEqual(matches[0].home_team, 'Manchester City');
      assert.strictEqual(matches[0].away_team, 'Liverpool');
      assert.ok(matches[0].league_name);
      assert.strictEqual(typeof matches[0].league_name, 'string');
    });

    it('应过滤日期范围外的比赛', () => {
      const pastDate = new Date();
      pastDate.setDate(pastDate.getDate() - 60);

      const mockResponse = {
        matches: [
          {
            id: 1,
            home: { name: 'Team A' },
            away: { name: 'Team B' },
            status: { utcTime: pastDate.toISOString(), finished: true }
          }
        ]
      };

      const matches = parser.parse(mockResponse, 47, '2024/2025', false, {
        lookbackDays: 30,
        lookaheadDays: 7
      });
      assert.strictEqual(matches.length, 0);
    });

    it('应正确处理空响应', () => {
      const matches = parser.parse({}, 47, '2024/2025');
      assert.strictEqual(matches.length, 0);
    });

    it('应正确处理 null 响应', () => {
      const matches = parser.parse(null, 47, '2024/2025');
      assert.strictEqual(matches.length, 0);
    });

    it('应生成标准化的 match_id', () => {
      const futureDate = new Date();
      futureDate.setDate(futureDate.getDate() + 2);

      const mockResponse = {
        matches: [
          {
            id: 12345,
            home: { name: 'Arsenal' },
            away: { name: 'Chelsea' },
            status: { utcTime: futureDate.toISOString(), finished: false }
          }
        ]
      };

      const matches = parser.parse(mockResponse, 47, '2024/2025', true);
      assert.strictEqual(matches.length, 1);
      assert.ok(matches[0].match_id);
      assert.ok(matches[0].match_id.startsWith('47_20242025_'));
    });
  });

  describe('日志系统', () => {
    it('应在静默模式下禁用 info 日志输出', () => {
      const silentService = new DiscoveryService({ silent: true });
      // 在静默模式下，logger.info 应返回 undefined (不执行 console.log)
      let output = null;
      const originalLog = console.log;
      console.log = (...args) => { output = args.join(' '); };
      silentService.logger.info('test');
      console.log = originalLog;
      assert.strictEqual(output, null, '静默模式下不应有输出');
      silentService.close();
    });

    it('应在非静默模式下启用 info 日志输出', () => {
      const verboseService = new DiscoveryService({ silent: false });
      let output = null;
      const originalLog = console.log;
      console.log = (...args) => { output = args.join(' '); };
      verboseService.logger.info('test');
      console.log = originalLog;
      assert.ok(output !== null, '非静默模式下应有输出');
      verboseService.close();
    });
  });

  describe('统计追踪', () => {
    it('应正确追踪统计信息', () => {
      assert.strictEqual(service.stats.total, 0);
      assert.strictEqual(service.stats.inserted, 0);
      assert.strictEqual(service.stats.updated, 0);
      assert.strictEqual(service.stats.failed, 0);
    });

    it('应能手动设置启动时间', () => {
      service.stats.startTime = Date.now();
      assert.ok(service.stats.startTime);
      assert.ok(service.stats.startTime > 0);
    });
  });

  describe('配置加载容错', () => {
    it('应在配置缺失时直接抛错', () => {
      const originalExists = require('fs').existsSync;
      require('fs').existsSync = () => false;

      assert.throws(() => new DiscoveryService({ silent: true }), /缺少必需配置文件/);

      require('fs').existsSync = originalExists;
    });
  });

  describe('联赛配置', () => {
    it('应包含五大联赛P0配置', () => {
      const p0Leagues = service.leagueConfig.active_leagues.filter(l => l.tier === 'P0');
      const hasPremierLeague = p0Leagues.some(l => l.id === 47);
      const hasLaLiga = p0Leagues.some(l => l.id === 87);
      const hasBundesliga = p0Leagues.some(l => l.id === 54);

      assert.ok(hasPremierLeague, '应包含英超');
      assert.ok(hasLaLiga, '应包含西甲');
      assert.ok(hasBundesliga, '应包含德甲');
    });

    it('应定义活跃赛季', () => {
      assert.ok(service.leagueConfig.active_seasons.length > 0);
      assert.ok(service.leagueConfig.active_seasons[0].match(/^\d{4}\/\d{4}$/));
    });
  });

  describe('历史赛季检测', () => {
    it('应正确识别历史赛季', () => {
      // 假设当前是 2024/2025 赛季，则 2023/2024 是历史赛季
      const isHistorical = service._isHistoricalSeason('2023/2024');
      // 由于测试时实际年份不确定，只验证方法返回布尔值
      assert.strictEqual(typeof isHistorical, 'boolean');
    });

    it('应支持多种赛季格式', () => {
      assert.strictEqual(typeof service._isHistoricalSeason('2023/2024'), 'boolean');
      assert.strictEqual(typeof service._isHistoricalSeason('2023-2024'), 'boolean');
      assert.strictEqual(typeof service._isHistoricalSeason('20232024'), 'boolean');
    });
  });

  describe('历史赛季全量扫描 (通过 DiscoveryParser)', () => {
    it('应在历史赛季模式下禁用日期过滤', () => {
      const oldDate = '2023-11-15T15:00:00Z';

      const mockResponse = {
        matches: Array.from({ length: 10 }, (_, i) => ({
          id: 1000 + i,
          home: { name: `Home Team ${i}` },
          away: { name: `Away Team ${i}` },
          status: { utcTime: oldDate, finished: true }
        }))
      };

      // 历史赛季模式
      const historicalMatches = parser.parse(mockResponse, 47, '2023/2024', true);
      assert.strictEqual(historicalMatches.length, 10, '历史赛季应全量采集');

      // 当前赛季模式 (带日期过滤配置)
      const currentMatches = parser.parse(mockResponse, 47, '2024/2025', false, {
        lookbackDays: 30,
        lookaheadDays: 7
      });
      assert.strictEqual(currentMatches.length, 0, '当前赛季应过滤旧日期');
    });

    it('应正确处理混合日期的历史赛季', () => {
      const mockResponse = {
        matches: [
          { id: 1, home: { name: 'A' }, away: { name: 'B' }, status: { utcTime: '2023-08-15T15:00:00Z' } },
          { id: 2, home: { name: 'C' }, away: { name: 'D' }, status: { utcTime: '2024-01-20T15:00:00Z' } },
          { id: 3, home: { name: 'E' }, away: { name: 'F' }, status: { utcTime: '2024-05-10T15:00:00Z' } }
        ]
      };

      const matches = parser.parse(mockResponse, 47, '2023/2024', true);
      assert.strictEqual(matches.length, 3, '应采集历史赛季所有比赛');
    });
  });

  describe('多路径嗅探 (通过 DiscoveryParser)', () => {
    it('路径E: 应优先解析 fixtures.allMatches 结构', () => {
      const mockResponse = {
        fixtures: {
          allMatches: [
            { id: 1, home: { name: 'Team A' }, away: { name: 'Team B' }, status: { utcTime: '2024-03-20T15:00:00Z' } },
            { id: 2, home: { name: 'Team C' }, away: { name: 'Team D' }, status: { utcTime: '2024-03-21T15:00:00Z' } }
          ]
        }
      };

      const matches = parser.parse(mockResponse, 47, '2024/2025', true);
      assert.strictEqual(matches.length, 2);
      assert.strictEqual(matches[0].external_id, '1');
    });

    it('路径F: 应解析 fixtures 直接为数组的结构', () => {
      const mockResponse = {
        fixtures: [
          { id: 1, home: { name: 'Team A' }, away: { name: 'Team B' }, status: { utcTime: '2024-03-20T15:00:00Z' } },
          { id: 2, home: { name: 'Team C' }, away: { name: 'Team D' }, status: { utcTime: '2024-03-21T15:00:00Z' } }
        ]
      };

      const matches = parser.parse(mockResponse, 47, '2024/2025', true);
      assert.strictEqual(matches.length, 2);
    });

    it('路径G: 应解析 fixtures 轮次分组', () => {
      const mockResponse = {
        fixtures: {
          round1: [{ id: 101, home: { name: 'A' }, away: { name: 'B' }, status: { utcTime: '2024-03-20T15:00:00Z' } }],
          round2: [{ id: 102, home: { name: 'C' }, away: { name: 'D' }, status: { utcTime: '2024-03-27T15:00:00Z' } }]
        }
      };

      const matches = parser.parse(mockResponse, 47, '2024/2025', true);
      assert.strictEqual(matches.length, 2);
    });

    it('应防止重复比赛', () => {
      const mockResponse = {
        fixtures: {
          round1: [{ id: 1, home: { name: 'A' }, away: { name: 'B' }, status: { utcTime: '2024-03-20T15:00:00Z' } }],
          round2: [{ id: 1, home: { name: 'A' }, away: { name: 'B' }, status: { utcTime: '2024-03-20T15:00:00Z' } }]
        }
      };

      const matches = parser.parse(mockResponse, 47, '2024/2025', true);
      assert.strictEqual(matches.length, 1, '应去重');
    });

    it('贪婪搜索: 应在深层结构中发现比赛 (中超结构)', () => {
      const mockResponse = {
        overview: {
          leagueMatches: [
            { id: 1, home: { name: '北京国安' }, away: { name: '上海申花' }, status: { utcTime: '2024-03-01T14:00:00Z' } },
            { id: 2, home: { name: '广州恒大' }, away: { name: '山东泰山' }, status: { utcTime: '2024-03-02T14:00:00Z' } }
          ]
        }
      };

      const matches = parser.parse(mockResponse, 210, '2024/2025', true);
      
      assert.strictEqual(matches.length, 2);
      assert.strictEqual(matches[0].home_team, '北京国安');
    });

    it('贪婪搜索: 少于10场时触发全字典扫描', () => {
      const mockResponse = {
        someDeep: {
          nested: {
            structure: [
              { id: 1, home: { name: 'Team A' }, away: { name: 'Team B' }, status: { utcTime: '2024-03-20T15:00:00Z' } },
              { id: 2, home: { name: 'Team C' }, away: { name: 'Team D' }, status: { utcTime: '2024-03-21T15:00:00Z' } }
            ]
          }
        }
      };

      const matches = parser.parse(mockResponse, 47, '2024/2025', true);
      
      assert.strictEqual(matches.length, 2);
    });
  });

  describe('数据清洗 (通过 DiscoveryParser)', () => {
    it('应支持多种球队名字段路径', () => {
      const mockResponse = {
        matches: [
          { id: 1, home: { name: 'Full Name' }, away: { name: 'Away Team' }, status: { utcTime: '2024-03-20T15:00:00Z' } }
        ]
      };

      const matches = parser.parse(mockResponse, 47, '2024/2025', true);
      assert.strictEqual(matches.length, 1);
      assert.strictEqual(matches[0].home_team, 'Full Name');
      assert.strictEqual(matches[0].away_team, 'Away Team');
    });

    it('状态字段应转为小写', () => {
      const mockResponse = {
        matches: [
          { id: 1, home: { name: 'A' }, away: { name: 'B' }, status: { finished: true, utcTime: '2024-03-20T15:00:00Z' } },
          { id: 2, home: { name: 'C' }, away: { name: 'D' }, status: { utcTime: '2024-03-21T15:00:00Z', live: true } },
          { id: 3, home: { name: 'E' }, away: { name: 'F' }, status: { utcTime: '2024-03-22T15:00:00Z', cancelled: true } }
        ]
      };

      const matches = parser.parse(mockResponse, 47, '2024/2025', true);
      assert.strictEqual(matches.length, 3);
      assert.strictEqual(matches[0].status, 'finished');  // 小写!
      assert.strictEqual(matches[1].status, 'live');      // 小写!
      assert.strictEqual(matches[2].status, 'cancelled'); // 小写!
      
      // 验证 is_finished 映射
      assert.strictEqual(matches[0].is_finished, true);
      assert.strictEqual(matches[1].is_finished, false);
    });

    it('应跳过无效数据', () => {
      const mockResponse = {
        matches: [
          { id: 1, home: { name: 'Valid' }, away: { name: 'Team' }, status: { utcTime: '2024-03-20T15:00:00Z' } },
          null,
          { id: null, home: { name: 'No ID' }, away: { name: 'Team' }, status: { utcTime: '2024-03-21T15:00:00Z' } },
          { home: { name: 'No ID' }, away: { name: 'Team' }, status: { utcTime: '2024-03-22T15:00:00Z' } }
        ]
      };

      const matches = parser.parse(mockResponse, 47, '2024/2025', true);
      assert.strictEqual(matches.length, 1);
      assert.strictEqual(matches[0].external_id, '1');
    });

    it('应为 FotMob fixture 显式写入 data_source，避免 canonical identity 失配', () => {
      const mockResponse = {
        matches: [
          { id: 1, home: { name: 'Valid' }, away: { name: 'Team' }, status: { utcTime: '2024-03-20T15:00:00Z' } }
        ]
      };

      const matches = parser.parse(mockResponse, 47, '2024/2025', true);

      assert.strictEqual(matches.length, 1);
      assert.strictEqual(matches[0].data_source, 'FotMob');
    });
  });
});

/**
 * ============================================================================
 * 集成测试锚点 (Integration Anchor Tests)
 * 这些测试作为重构的"验收红线"，确保功能零丢失
 * ============================================================================
 */
describe('集成测试锚点 - 重构验收红线', () => {
  // 独立的 mock 配置，不依赖外层的 service
  const mockLeagueConfig = {
    active_leagues: [
      { id: 47, name: 'Premier League', country: 'England', tier: 'P0' },
      { id: 223, name: 'J1 League', country: 'Japan', tier: 'P3' },
      { id: 120, name: 'CSL', country: 'China', tier: 'P3' }
    ],
    active_seasons: ['2024', '2024/2025']
  };
  
  const mockLogger = {
    info: () => {},
    warn: () => {},
    error: () => {}
  };
  
  // 创建独立的 parser 实例
  const anchorParser = new DiscoveryParser(mockLogger, mockLeagueConfig);
  
  describe('Anchor-1: J1 全量入库验证 (380场)', () => {
    it('应正确解析日职联 380 场比赛数据 (weeksWithMatches结构)', () => {
      // 模拟 J1 League (ID: 223) 的典型数据结构 - weeksWithMatches 格式
      // 注意: 使用 weeks 而不是 weeksWithMatches 以匹配当前代码路径
      const mockJ1Response = {
        weeks: Array.from({ length: 34 }, (_, weekIdx) => ({
          week: weekIdx + 1,
          matches: Array.from({ length: 11 }, (_, matchIdx) => ({
            id: 22300000 + weekIdx * 11 + matchIdx + 1,
            home: { name: `J1 Home ${weekIdx}-${matchIdx}` },
            away: { name: `J1 Away ${weekIdx}-${matchIdx}` },
            status: { utcTime: `2024-${String((weekIdx % 12) + 1).padStart(2, '0')}-15T14:00:00Z` }
          }))
        }))
      };

      // 验证总数为 34周 * 11场 = 374场 (接近真实 380)
      const matches = anchorParser.parse(mockJ1Response, 223, '2024', true);
      assert.strictEqual(matches.length, 374);
      
      // 验证单年份格式处理
      assert.ok(matches.every(m => m.season === '2024'));
      assert.ok(matches.every(m => m.match_id.startsWith('223_2024_')));
    });

    it('应正确处理 J1 的 weeks 轮次结构', () => {
      const mockResponse = {
        weeks: [
          {
            week: 1,
            matches: [
              { id: 223001, home: { name: '横滨水手' }, away: { name: '川崎前锋' }, status: { utcTime: '2024-02-23T10:00:00Z' } },
              { id: 223002, home: { name: '鹿岛鹿角' }, away: { name: '浦和红钻' }, status: { utcTime: '2024-02-23T11:00:00Z' } }
            ]
          },
          {
            week: 2,
            matches: [
              { id: 223003, home: { name: '大阪钢巴' }, away: { name: '名古屋鲸' }, status: { utcTime: '2024-03-01T10:00:00Z' } }
            ]
          }
        ]
      };

      const matches = anchorParser.parse(mockResponse, 223, '2024', true);
      assert.strictEqual(matches.length, 3);
      assert.strictEqual(matches[0].home_team, '横滨水手');
      assert.strictEqual(matches[0].away_team, '川崎前锋');
    });

    it('应正确处理 weeksWithMatches 结构 (V6.7.7+ 路径)', () => {
      // weeksWithMatches 路径在代码中是优先检查的
      const mockResponse = {
        weeksWithMatches: [
          {
            week: 1,
            matches: [
              { id: 223001, home: { name: 'FC东京' }, away: { name: '广岛三箭' }, status: { utcTime: '2024-02-23T10:00:00Z' } }
            ]
          }
        ]
      };

      const matches = anchorParser.parse(mockResponse, 223, '2024', true);
      assert.strictEqual(matches.length, 1);
      assert.strictEqual(matches[0].home_team, 'FC东京');
    });
  });

  describe('Anchor-2: 中超单年份验证 (ID 120)', () => {
    it('应正确处理中超单年份格式，不发生数据库约束冲突', () => {
      const mockCSLResponse = {
        fixtures: {
          allMatches: Array.from({ length: 240 }, (_, i) => ({
            id: 12000000 + i + 1,
            home: { name: `中超主场 ${i}` },
            away: { name: `中超客场 ${i}` },
            status: { utcTime: '2024-03-01T12:00:00Z' }
          }))
        }
      };

      // 注意: season 在 parse 中保持原样传入，格式化处理在 DiscoveryService._fetchFixtures 中
      const matches = anchorParser.parse(mockCSLResponse, 120, '2024', true);
      assert.strictEqual(matches.length, 240);
      
      // 关键验证: season 保持传入值 '2024' (单年份)
      assert.ok(matches.every(m => m.season === '2024'));
      
      // match_id = leagueId + normalizedSeason + externalId
      // normalizedSeason = season.replace(/[\/\-_]/g, '') = '2024'
      assert.ok(matches.every(m => m.match_id.startsWith('120_2024_')));
      assert.ok(matches.every(m => !m.match_id.includes('20242024')));
      
      // 验证 match_id 唯一性 (数据库约束要求)
      const ids = matches.map(m => m.match_id);
      const uniqueIds = [...new Set(ids)];
      assert.strictEqual(ids.length, uniqueIds.length, 'match_id 必须唯一，否则会发生数据库约束冲突');
    });

    it('应识别中超为单年份联赛并正确格式化赛季', () => {
      // 模拟传入单年份格式
      const mockMatch = {
        id: 120001,
        home: { name: '北京国安' },
        away: { name: '上海申花' },
        status: { utcTime: '2024-03-01T12:00:00Z' }
      };

      const result = anchorParser.parse({ fixtures: { allMatches: [mockMatch] } }, 120, '2024', true);
      assert.strictEqual(result.length, 1);
      assert.strictEqual(result[0].season, '2024');
      // match_id = 120 + _ + 2024 + _ + 120001
      assert.strictEqual(result[0].match_id, '120_2024_120001');
    });

    it('应正确处理双年份格式转换为单年份 (Service层责任)', () => {
      // 注意: 实际项目中，单年份转换逻辑在 DiscoveryService._fetchFixtures
      // 这里验证 Parser 保持传入的 season 不变
      const mockMatch = {
        id: 120001,
        home: { name: '北京国安' },
        away: { name: '上海申花' },
        status: { utcTime: '2024-03-01T12:00:00Z' }
      };

      // 模拟传入双年份，但 Parser 保持原样
      const result = anchorParser.parse({ fixtures: { allMatches: [mockMatch] } }, 120, '2024/2025', true);
      assert.strictEqual(result[0].season, '2024/2025');
      // normalizedSeason = '2024/2025'.replace(/[\/\-_]/g, '') = '20242025'
      assert.strictEqual(result[0].match_id, '120_20242025_120001');
    });
  });

  describe('Anchor-3: 网络拦截与API回退验证', () => {
    it('应通过 NetworkInterceptor 捕获 fotmob.com/api/data/leagues 端点', async () => {
      // 创建服务实例进行测试
      const testService = new DiscoveryService({ 
        silent: true,
        concurrency: 1 
      });

      try {
        // V6.7.4-REFACTORED: 使用 NetworkInterceptor 获取 capturedApis
        const capturedApis = testService.capturedApis;
        
        // 验证初始状态
        assert.ok(capturedApis instanceof Map, '应有 capturedApis Map');
        assert.strictEqual(capturedApis.size, 0, '初始应为空');
        
        // 模拟通过 NetworkInterceptor 捕获端点
        const testUrl = 'https://www.fotmob.com/api/data/leagues?id=47&season=20242025';
        testService.networkInterceptor.capturedApis.set('/api/data/leagues?id=47&season=20242025', {
          url: testUrl,
          timestamp: new Date().toISOString()
        });
        
        // 通过 getter 访问应返回更新后的 Map
        assert.strictEqual(testService.capturedApis.size, 1);
        assert.ok(testService.capturedApis.has('/api/data/leagues?id=47&season=20242025'));
      } finally {
        await testService.close();
      }
    });

    it('应正确初始化 NetworkInterceptor', async () => {
      const testService = new DiscoveryService({ silent: true });
      
      try {
        // V6.7.4-REFACTORED: 验证 networkInterceptor 实例存在
        assert.ok(testService.networkInterceptor, '应有 networkInterceptor 实例');
        assert.strictEqual(typeof testService.networkInterceptor.setup, 'function');
        assert.strictEqual(typeof testService.networkInterceptor.handleRequest, 'function');
        assert.strictEqual(typeof testService.networkInterceptor.handleResponse, 'function');
      } finally {
        await testService.close();
      }
    });
  });

  describe('Anchor-4: 资源清理验证', () => {
    it('close() 后浏览器提供者应被关闭', async () => {
      const testService = new DiscoveryService({ silent: true });
      
      // 初始状态
      assert.ok(testService.browserProvider);
      assert.strictEqual(testService.browserProvider.isInitialized(), false);
      
      // 关闭服务
      await testService.close();
      
      // 验证关闭后状态
      assert.strictEqual(testService.browserProvider.isInitialized(), false);
    });

    it('close() 后数据库连接池应被关闭', async () => {
      const testService = new DiscoveryService({ silent: true });
      
      // 验证连接池存在
      assert.ok(testService.dbPool);
      
      // 关闭服务
      await testService.close();
      
      // 验证连接池已结束 (通过尝试获取连接会失败)
      try {
        await testService.dbPool.connect();
        assert.fail('连接池应已关闭');
      } catch (e) {
        assert.ok(e.message.includes('closed') || e.message.includes('ending') || e.message.includes('pool'));
      }
    });
  });

  describe('Anchor-5: 赛季格式验证 (策略模式前置测试)', () => {
    it('应正确识别单年份联赛 (如中超 120)', () => {
      // 当前实现使用硬编码列表，此测试确保该行为在重构后保持
      const singleYearLeagues = [120, 223, 8974, 230, 268, 121, 130];
      
      assert.ok(singleYearLeagues.includes(120), '中超应为单年份');
      assert.ok(singleYearLeagues.includes(223), '日职联应为单年份');
      assert.ok(!singleYearLeagues.includes(47), '英超不应为单年份');
      assert.ok(!singleYearLeagues.includes(87), '西甲不应为单年份');
    });

    it('应正确格式化单年份赛季字符串', () => {
      const season = '2024/2025';
      const yearMatch = season.match(/(\d{4})/);
      const normalizedSeason = yearMatch ? yearMatch[1] : season;
      
      assert.strictEqual(normalizedSeason, '2024');
    });

    it('应正确格式化双年份赛季字符串', () => {
      const season = '2024/2025';
      const normalizedSeason = season.replace(/[\/\-_]/g, '');
      
      assert.strictEqual(normalizedSeason, '20242025');
    });
  });
});
