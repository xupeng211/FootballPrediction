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

  it('配置缺失时应回退到五大联赛默认配置', () => {
    const fallback = new L1ConfigManager({
      reconConfigPath: '/tmp/does-not-exist-recon.json',
      leaguesConfigPath: '/tmp/does-not-exist-leagues.json'
    });

    const runtimeConfig = fallback.getRuntimeConfig();
    assert.strictEqual(runtimeConfig.active_leagues.length, 5);
    assert.strictEqual(fallback.getLeagueByCode('SERIEA').id, 55);
  });
});
