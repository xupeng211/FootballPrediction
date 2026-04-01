/**
 * @file L1ConfigManager.test.js
 * @description L1 配置统一管理器单元测试
 */

'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');
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

  it('应为受保护联赛保留内部 ID，并映射到 providerId 请求 FotMob', () => {
    const serieB = manager.getLeagueById(156);
    const ligue2 = manager.getLeagueById(182);
    const coupeDeFrance = manager.getLeagueById(181);

    assert.ok(serieB);
    assert.ok(ligue2);
    assert.ok(coupeDeFrance);
    assert.strictEqual(serieB.providerId, 86);
    assert.strictEqual(ligue2.providerId, 110);
    assert.strictEqual(coupeDeFrance.providerId, 134);
    assert.strictEqual(
      manager.buildLeagueApiUrl(156, '20252026'),
      'https://www.fotmob.com/api/data/leagues?id=86&season=20252026'
    );
  });

  it('应能读取德甲赛季的 expected_matches', () => {
    assert.strictEqual(manager.getExpectedMatches(54, '2025/2026'), 306);
    assert.strictEqual(manager.getExpectedMatches(47, '2025/2026'), 380);
  });

  it('seasonless 联赛应保留 canonical slug 与 URL 策略', () => {
    const csl = manager.getLeagueById(120);
    const mls = manager.getLeagueById(130);
    const superLig = manager.getLeagueById(71);
    const euro = manager.getLeagueById(50);
    const brasileirao = manager.getLeagueById(268);
    const superLigByCode = manager.getLeagueByCode('SUPERLIG');

    assert.ok(csl);
    assert.ok(mls);
    assert.ok(superLig);
    assert.ok(euro);
    assert.ok(brasileirao);
    assert.ok(superLigByCode);
    assert.strictEqual(csl.slug, 'super-league');
    assert.strictEqual(csl.resultsSlug, 'super-league');
    assert.strictEqual(csl.resultsUrlStrategy, 'seasonless');
    assert.strictEqual(mls.slug, 'mls');
    assert.strictEqual(mls.resultsSlug, 'mls');
    assert.strictEqual(mls.resultsUrlStrategy, 'seasonless');
    assert.strictEqual(superLig.slug, 'super-lig');
    assert.strictEqual(superLig.resultsSlug, 'super-lig');
    assert.strictEqual(superLig.resultsUrlStrategy, 'seasonless');
    assert.strictEqual(superLigByCode.id, 71);
    assert.strictEqual(euro.slug, 'euro');
    assert.strictEqual(euro.resultsSlug, 'euro');
    assert.strictEqual(euro.resultsUrlStrategy, 'seasonless');
    assert.strictEqual(euro.enabled, false);
    assert.strictEqual(brasileirao.slug, 'brasileirao');
    assert.strictEqual(brasileirao.resultsSlug, 'serie-a');
    assert.strictEqual(brasileirao.resultsUrlStrategy, 'seasonless');
  });

  it('联赛级 ready_selector 应并入运行时配置', () => {
    const j1 = manager.getLeagueById(223);

    assert.ok(j1);
    assert.strictEqual(j1.readySelector, 'text=Machida');
  });

  it('临时下线的 UEFA Euro 不应出现在 active league 列表中', () => {
    const activeLeagueIds = manager.getActiveLeagues().map((league) => league.id);

    assert.ok(!activeLeagueIds.includes(50));
  });

  it('世界杯应保留 2026 专用 slug 与 seasonal URL 策略', () => {
    const worldCup = manager.getLeagueById(77);

    assert.ok(worldCup);
    assert.strictEqual(worldCup.slug, 'world-cup-2026');
    assert.strictEqual(worldCup.resultsSlug, 'world-cup-2026');
    assert.strictEqual(worldCup.resultsUrlStrategy, 'seasonal');
    assert.strictEqual(worldCup.awaitingFinals, true);
  });

  it('临时下线的 Copa América 不应出现在 active league 列表中', () => {
    const copaAmerica = manager.getLeagueById(131);
    const activeLeagueIds = manager.getActiveLeagues().map((league) => league.id);

    assert.ok(copaAmerica);
    assert.strictEqual(copaAmerica.enabled, false);
    assert.ok(!activeLeagueIds.includes(131));
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
});
