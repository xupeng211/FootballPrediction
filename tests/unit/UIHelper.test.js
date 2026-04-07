'use strict';

const { afterEach, describe, it } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');

const { UIHelper } = require('../../src/infrastructure/services/UIHelper');

describe('UIHelper', () => {
  const originalDateNow = Date.now;
  const originalReadFileSync = fs.readFileSync;

  afterEach(() => {
    Date.now = originalDateNow;
    fs.readFileSync = originalReadFileSync;
  });

  it('应输出横幅、报告、联赛列表与搜索结果', () => {
    const banners = [];
    const infos = [];
    const warnings = [];
    const progresses = [];
    const errors = [];
    const helper = new UIHelper({
      logger: {
        info(message) {
          infos.push(message);
        },
        warn(message) {
          warnings.push(message);
        },
        error(message) {
          errors.push(message);
        },
        banner(message) {
          banners.push(message);
        },
        progress(message) {
          progresses.push(message);
        }
      }
    });

    Date.now = () => 200000;

    helper.printBanner('V9.9.9');
    const report = helper.generateReport({
      total: 12,
      inserted: 5,
      updated: 6,
      failed: 1,
      criticalWarnings: [{
        name: 'EPL',
        season: '2025/2026',
        actual: 360,
        expected: 380,
        missing: 20
      }]
    }, 140000);

    helper.printProgress('W1', 'Premier League', { inserted: 5, updated: 6, failed: 1 });
    helper.printTargets(7);
    helper.printScanStart('W1', 'Premier League', '2025/2026');
    helper.printHistoricalMode('W1', '2023/2024');
    helper.printParsedFixtures('W1', 'Premier League', 380);
    helper.printCriticalWarn('W1', 'Premier League', '2025/2026', 360, 380);
    helper.printNoFixtures('W1', 'Premier League');
    helper.printScanError('W1', 'Premier League', 'timeout', 2500);

    helper._loadI18nConfig = () => ({
      locales: {
        zh: {
          leagues: {
            47: '英超'
          }
        }
      }
    });
    helper.printLeagueList([
      { id: 47, name: 'Premier League', country: 'England', tier: 'P0' },
      { id: 54, name: 'Bundesliga', country: 'Germany', tier: 'P2' }
    ]);
    helper.printSearchResults({
      leagues: [{ id: 47, name: 'Premier League', country: 'England' }],
      teams: Array.from({ length: 11 }, (_, index) => ({
        id: index + 1,
        name: `Team ${index + 1}`,
        country: 'England'
      }))
    });
    helper.printSearchResults({ leagues: [], teams: [] });

    assert.deepStrictEqual(report, {
      total: 12,
      inserted: 5,
      updated: 6,
      failed: 1,
      criticalWarnings: [{
        name: 'EPL',
        season: '2025/2026',
        actual: 360,
        expected: 380,
        missing: 20
      }],
      duration: '60.0s',
      rate: '12.0'
    });
    assert.ok(banners.some((line) => line.includes('PROJECT HOUND V9.9.9')));
    assert.ok(banners.some((line) => line.includes('Premier League (英超)')));
    assert.ok(banners.some((line) => line.includes('... 还有 1 支球队 ...')));
    assert.ok(banners.some((line) => line.includes('未找到匹配结果')));
    assert.ok(progresses.some((line) => line.includes('新增 5 | 更新 6 | 失败 1')));
    assert.ok(infos.some((line) => line.includes('历史赛季 2023/2024')));
    assert.ok(infos.some((line) => line.includes('解析出 380 场有效比赛')));
    assert.ok(warnings.some((line) => line.includes('[CRITICAL WARN] EPL 2025/2026')));
    assert.ok(warnings.some((line) => line.includes('Premier League 2025/2026')));
    assert.ok(errors.some((line) => line.includes('Premier League 扫描失败: timeout')));
  });

  it('国际化配置加载失败时应回退到空配置并记录告警', () => {
    const warnings = [];
    const helper = new UIHelper({
      logger: {
        info() {},
        warn(message) {
          warnings.push(message);
        },
        error() {},
        banner() {},
        progress() {}
      }
    });

    fs.readFileSync = () => {
      throw new Error('missing-config');
    };

    const config = helper._loadI18nConfig();

    assert.deepStrictEqual(config, { locales: { zh: { leagues: {} } } });
    assert.ok(warnings.some((message) => message.includes('missing-config')));
  });

  it('未显式传入 logger 时应提供可调用的默认空实现', () => {
    const helper = new UIHelper();

    assert.doesNotThrow(() => helper.logger.info('noop'));
    assert.doesNotThrow(() => helper.logger.warn('noop'));
    assert.doesNotThrow(() => helper.logger.error('noop'));
    assert.doesNotThrow(() => helper.logger.banner('noop'));
    assert.doesNotThrow(() => helper.logger.progress('noop'));
  });
});
