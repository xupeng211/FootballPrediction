/**
 * @file L1ConfigManager.test.js
 * @description L1 配置统一管理器单元测试
 */

'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('path');

const { L1ConfigManager } = require('../../src/infrastructure/services/L1ConfigManager');

describe('L1ConfigManager', () => {
  const manager = new L1ConfigManager({
    reconConfigPath: path.resolve(__dirname, '../../config/recon_config.json'),
    leaguesConfigPath: path.resolve(__dirname, '../../config/leagues.json')
  });

  it('应统一输出激活联赛列表', () => {
    const runtimeConfig = manager.getRuntimeConfig();

    assert.ok(Array.isArray(runtimeConfig.active_leagues));
    assert.ok(runtimeConfig.active_leagues.length >= 5);
    assert.ok(Array.isArray(runtimeConfig.active_seasons));
    assert.ok(runtimeConfig.active_seasons.includes('2025/2026'));
  });

  it('应解决 Serie A 的联赛 ID 冲突，统一为 55', () => {
    const serieA = manager.getLeagueByCode('SERIEA');

    assert.ok(serieA);
    assert.strictEqual(serieA.id, 55);
    assert.strictEqual(serieA.name, 'Serie A');
    assert.strictEqual(serieA.slug, 'serie-a');
  });

  it('应保留 Bundesliga 配置并默认使用双年份赛季', () => {
    const bundesliga = manager.getLeagueById(54);

    assert.ok(bundesliga);
    assert.strictEqual(bundesliga.code, 'BUNDESLIGA');
    assert.strictEqual(bundesliga.seasonType, 'dual_year');
    assert.strictEqual(manager.getDefaultSeason(54), '2025/2026');
  });

  it('应生成新的 FotMob leagues API URL', () => {
    const url = manager.buildLeagueApiUrl(47, '20242025');
    assert.strictEqual(url, 'https://www.fotmob.com/api/data/leagues?id=47&season=20242025');
  });

  it('33 项正式清单应移除旧保护联赛绕路，并直连新的 Coupe de France ID', () => {
    const coupeDeFrance = manager.getLeagueById(134);

    assert.strictEqual(manager.getLeagueById(156), null);
    assert.strictEqual(manager.getLeagueById(182), null);
    assert.ok(coupeDeFrance);
    assert.strictEqual(coupeDeFrance.providerId, 134);
    assert.strictEqual(
      manager.buildLeagueApiUrl(134, '20252026'),
      'https://www.fotmob.com/api/data/leagues?id=134&season=20252026'
    );
  });

  it('应能读取德甲赛季的 expected_matches', () => {
    assert.strictEqual(manager.getExpectedMatches(54, '2025/2026'), 306);
    assert.strictEqual(manager.getExpectedMatches(47, '2025/2026'), 380);
  });

  it('seasonless 联赛与 J1 单年份历史页联赛应保留 canonical slug 与 URL 策略', () => {
    const mls = manager.getLeagueById(130);
    const superLig = manager.getLeagueById(71);
    const brasileirao = manager.getLeagueById(268);
    const ligaProfesional = manager.getLeagueById(112);
    const ligaMx = manager.getLeagueById(230);
    const j1 = manager.getLeagueById(223);
    const kLeague1 = manager.getLeagueById(9080);
    const superLigByCode = manager.getLeagueByCode('SUPERLIG');

    assert.ok(mls);
    assert.ok(superLig);
    assert.ok(brasileirao);
    assert.ok(ligaProfesional);
    assert.ok(ligaMx);
    assert.ok(j1);
    assert.ok(kLeague1);
    assert.ok(superLigByCode);
    assert.strictEqual(mls.slug, 'mls');
    assert.strictEqual(mls.resultsSlug, 'mls');
    assert.strictEqual(mls.resultsUrlStrategy, 'seasonless');
    assert.deepStrictEqual(mls.additionalResultsPaths, [
      '/football/{country}/{league}/'
    ]);
    assert.deepStrictEqual(mls.additionalHistoricalResultsPaths, [
      '/football/{country}/{league}-{year}/'
    ]);
    assert.strictEqual(superLig.slug, 'super-lig');
    assert.strictEqual(superLig.resultsSlug, 'super-lig');
    assert.strictEqual(superLig.resultsUrlStrategy, 'seasonless');
    assert.strictEqual(superLigByCode.id, 71);
    assert.strictEqual(brasileirao.slug, 'brasileirao');
    assert.strictEqual(brasileirao.resultsSlug, 'brasileirao');
    assert.strictEqual(brasileirao.resultsUrlStrategy, 'seasonless');
    assert.strictEqual(ligaProfesional.slug, 'liga-profesional');
    assert.strictEqual(ligaProfesional.resultsSlug, 'liga-profesional');
    assert.strictEqual(ligaProfesional.resultsUrlStrategy, 'seasonless');
    assert.strictEqual(ligaMx.slug, 'liga-mx');
    assert.strictEqual(ligaMx.resultsSlug, 'liga-mx');
    assert.strictEqual(ligaMx.resultsUrlStrategy, 'seasonless');
    assert.strictEqual(j1.slug, 'j1-league');
    assert.strictEqual(j1.resultsSlug, 'j1-league');
    assert.strictEqual(j1.resultsUrlStrategy, 'seasonal');
    assert.strictEqual(j1.seasonlessCurrentYearBasis, 'start');
    assert.strictEqual(kLeague1.slug, 'k-league-1');
    assert.strictEqual(kLeague1.resultsSlug, 'k-league-1');
    assert.strictEqual(kLeague1.resultsUrlStrategy, 'seasonless');
    assert.strictEqual(kLeague1.seasonlessCurrentYearBasis, 'start');
  });

  it('联赛级 ready_selector 应并入运行时配置', () => {
    const j1 = manager.getLeagueById(223);

    assert.ok(j1);
    assert.strictEqual(j1.readySelector, "div[role='row']");
  });

  it('Euro 应出现在 active league 列表中', () => {
    const euro = manager.getLeagueById(50);
    const activeLeagueIds = manager.getActiveLeagues().map((league) => league.id);

    assert.ok(euro);
    assert.strictEqual(euro.enabled, true);
    assert.ok(activeLeagueIds.includes(50));
  });

  it('世界杯应保留 2026 专用 slug 与 seasonless URL 策略', () => {
    const worldCup = manager.getLeagueById(77);

    assert.ok(worldCup);
    assert.strictEqual(worldCup.slug, 'world-cup-2026');
    assert.strictEqual(worldCup.resultsSlug, 'world-cup-2026');
    assert.strictEqual(worldCup.resultsUrlStrategy, 'seasonless');
    assert.strictEqual(worldCup.awaitingFinals, true);
  });

  it('Copa America 应出现在 active league 列表中', () => {
    const copaAmerica = manager.getLeagueById(44);
    const activeLeagueIds = manager.getActiveLeagues().map((league) => league.id);

    assert.ok(copaAmerica);
    assert.strictEqual(copaAmerica.enabled, true);
    assert.ok(activeLeagueIds.includes(44));
  });

  it('Liga Profesional 应指向 Argentina 并保留真实 slug', () => {
    const ligaProfesional = manager.getLeagueById(112);

    assert.ok(ligaProfesional);
    assert.strictEqual(ligaProfesional.country, 'argentina');
    assert.strictEqual(ligaProfesional.slug, 'liga-profesional');
    assert.strictEqual(ligaProfesional.resultsSlug, 'liga-profesional');
  });

  it('配置缺失时应直接抛错，禁止静默回退', () => {
    assert.throws(() => new L1ConfigManager({
      reconConfigPath: '/tmp/does-not-exist-recon.json',
      leaguesConfigPath: '/tmp/does-not-exist-leagues.json'
    }), /缺少必需配置文件/);
  });

  it('联赛缺少 league_id 时应直接抛错', () => {
    assert.throws(() => new L1ConfigManager({
      runtimeConfig: null,
      reconConfigPath: path.resolve(__dirname, '../fixtures/recon_config_invalid_missing_league_id.json'),
      leaguesConfigPath: path.resolve(__dirname, '../../config/leagues.json'),
      seasonWindowsPath: path.resolve(__dirname, '../../config/season_windows.json')
    }), /缺少有效 league_id/);
  });

  it('get 查询不存在的嵌套 key 时应返回 default 且不抛错', () => {
    const runtimeManager = new L1ConfigManager({
      runtimeConfig: {
        limits: {
          retries: 3
        }
      }
    });

    assert.doesNotThrow(() => {
      assert.strictEqual(runtimeManager.get('limits.timeout.ms', 15000), 15000);
    });
  });

  it('get 遇到类型不匹配时应返回 default 并执行防御性降级', () => {
    const warnings = [];
    const runtimeManager = new L1ConfigManager({
      logger: {
        info() {},
        warn(message) {
          warnings.push(message);
        },
        error() {}
      },
      runtimeConfig: {
        threshold: {
          expectedNumber: { bad: true }
        },
        metrics: {
          sampleSize: 64
        }
      }
    });

    assert.strictEqual(runtimeManager.get('threshold.expectedNumber', 10, 'number'), 10);
    assert.strictEqual(runtimeManager.get('metrics.sampleSize', 0, 'number'), 64);
    assert.ok(warnings.some((message) => message.includes('threshold.expectedNumber')));
  });

  it('辅助 getter 与字符串 helper 应覆盖默认和数组类型分支', () => {
    const runtimeManager = new L1ConfigManager({
      runtimeConfig: {
        active_leagues: [
          { id: 120, providerId: 120, code: 'TEST', tier: 'P1', enabled: true, defaultSeason: '2025/2026' }
        ],
        active_seasons: ['2024/2025', '2025/2026'],
        default_season: '2025/2026',
        single_year_league_ids: [120],
        season_windows: {},
        features: {
          flags: ['alpha'],
          label: 'ready'
        }
      }
    });

    assert.deepStrictEqual(runtimeManager.getActiveSeasons(), ['2024/2025', '2025/2026']);
    assert.deepStrictEqual(runtimeManager.getSingleYearLeagueIds(), [120]);
    assert.strictEqual(runtimeManager.getDefaultSeason(), '2025/2026');
    assert.strictEqual(runtimeManager.getDefaultSeason(999), '2025/2026');
    assert.strictEqual(runtimeManager.getProviderLeagueId('bad-id'), null);
    assert.deepStrictEqual(runtimeManager.getActiveLeagues({ tier: 'P1' }).map((league) => league.id), [120]);
    assert.doesNotThrow(() => runtimeManager.logger.info('noop-info'));
    assert.doesNotThrow(() => runtimeManager.logger.warn('noop-warn'));
    assert.doesNotThrow(() => runtimeManager.logger.error('noop-error'));
    assert.strictEqual(runtimeManager.get('', 'fallback'), 'fallback');
    assert.deepStrictEqual(runtimeManager.get('features.flags', [], 'array'), ['alpha']);
    assert.strictEqual(runtimeManager.get('features.label', '', 'string'), 'ready');
    assert.deepStrictEqual(runtimeManager._normalizeStringArray([' alpha ', '', null, 'beta']), ['alpha', 'beta']);
    assert.deepStrictEqual(runtimeManager._normalizeStringArray('bad-input'), []);
    assert.strictEqual(runtimeManager._resolveProviderId({ provider_id: '12' }, null, 9), 12);
    assert.strictEqual(runtimeManager._resolveProviderId(null, { providerId: 'oops' }, 9), 9);
    assert.strictEqual(runtimeManager._inferSeasonType(120), 'single_year');
    assert.strictEqual(runtimeManager._leagueKey('São Paulo'), 'saopaulo');
    assert.strictEqual(runtimeManager._slugify(' Copa América 2026 '), 'copa-america-2026');
    assert.strictEqual(runtimeManager._codeFromName('J1 League'), 'J1LEAGUE');
  });

  it('expected matches 回退与配置异常分支应可预测', () => {
    const runtimeManager = new L1ConfigManager({
      runtimeConfig: {
        active_leagues: [
          { id: 999, providerId: 999, code: 'TEST', name: 'Test League', tier: 'P0', enabled: true }
        ],
        active_seasons: ['2025/2026'],
        default_season: '2025/2026',
        single_year_league_ids: [],
        season_windows: {
          fallbackWindow: {
            leagues: [999],
            expected_matches: 222,
            description: 'Season 25 fallback'
          }
        }
      }
    });
    const tempDir = fs.mkdtempSync(path.join(__dirname, '../fixtures/l1-config-'));
    const invalidJsonPath = path.join(tempDir, 'broken.json');
    fs.writeFileSync(invalidJsonPath, '{broken json', 'utf8');

    assert.strictEqual(runtimeManager.getExpectedMatches(999, '2025/2026'), 222);
    assert.strictEqual(runtimeManager.getExpectedMatches(999, null), null);
    assert.strictEqual(runtimeManager.getExpectedMatches(555, '2024/2025'), null);
    assert.throws(
      () => runtimeManager._loadRequiredJson(invalidJsonPath, 'broken.json'),
      /配置文件损坏: broken\.json/
    );
    assert.throws(
      () => runtimeManager._assertValidReconLeague('BROKEN', null),
      /联赛配置损坏: BROKEN/
    );
    assert.throws(
      () => runtimeManager._assertValidReconLeague('BROKEN', { league_id: 1 }),
      /联赛 BROKEN 缺少有效 name/
    );
  });
});
