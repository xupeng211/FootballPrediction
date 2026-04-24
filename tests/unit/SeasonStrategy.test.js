'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const {
  SeasonStrategyFactory,
  SeasonDiscovery,
  SingleYearStrategy,
  DualYearStrategy
} = require('../../src/infrastructure/services/SeasonStrategy');

describe('SeasonStrategy', () => {
  it('单年份与双年份策略应正确格式化、校验并返回名称', () => {
    const dual = new DualYearStrategy();
    const single = new SingleYearStrategy();

    assert.strictEqual(dual.format('2024/2025'), '20242025');
    assert.strictEqual(dual.isValid('2024-2025'), true);
    assert.strictEqual(dual.isValid('2024'), false);
    assert.strictEqual(dual.getName(), 'dual_year');

    assert.strictEqual(single.format('2024/2025'), '2024');
    assert.strictEqual(single.format('season-2026'), '2026');
    assert.strictEqual(single.isValid('2026'), true);
    assert.strictEqual(single.isValid('unknown'), false);
    assert.strictEqual(single.getName(), 'single_year');
  });

  it('工厂应支持判定、格式化与动态注册单年份联赛', () => {
    const factory = new SeasonStrategyFactory({
      singleYearLeagues: [120]
    });

    assert.strictEqual(factory.isSingleYearLeague(120), true);
    assert.strictEqual(factory.isSingleYearLeague(47), false);
    assert.strictEqual(factory.getStrategyType(120), 'single_year');
    assert.strictEqual(factory.getStrategyType(47), 'dual_year');
    assert.strictEqual(factory.getStrategy(120).getName(), 'single_year');
    assert.strictEqual(factory.getStrategy('47').getName(), 'dual_year');
    assert.strictEqual(factory.format(120, '2025/2026'), '2025');
    assert.strictEqual(factory.format(47, '2025/2026'), '20252026');

    factory.registerSingleYearLeague(47);
    assert.strictEqual(factory.isSingleYearLeague(47), true);
    factory.registerSingleYearLeague(47);
    factory.unregisterSingleYearLeague(47);
    assert.strictEqual(factory.isSingleYearLeague(47), false);
  });

  it('默认配置与 no-op logger 分支应可直接执行', async () => {
    const defaultFactory = new SeasonStrategyFactory();
    const defaultDiscovery = new SeasonDiscovery({
      apiRequest: async () => ({ allAvailableSeasons: ['2028/2029'] })
    });

    assert.strictEqual(defaultFactory.isSingleYearLeague(120), true);
    defaultFactory.unregisterSingleYearLeague(999);
    assert.strictEqual(defaultFactory.isSingleYearLeague(999), false);
    assert.doesNotThrow(() => defaultDiscovery.logger.info('noop-info'));
    assert.doesNotThrow(() => defaultDiscovery.logger.warn('noop-warn'));
    assert.doesNotThrow(() => defaultDiscovery.logger.error('noop-error'));
    assert.strictEqual(await defaultDiscovery.discover(52, '2026'), '2026');
  });

  it('赛季探测应覆盖精确、包含、安全保底与异常分支', async () => {
    const warnings = [];
    const discovery = new SeasonDiscovery({
      logger: {
        info() {},
        warn(message) {
          warnings.push(message);
        },
        error() {}
      },
      apiRequest: async (_url, options) => {
        if (options.expectedLeagueId === 47) {
          return { allAvailableSeasons: ['2025', '2024/2025', '2023/2024'] };
        }
        if (options.expectedLeagueId === 48) {
          return { allAvailableSeasons: ['2025/2026', '2024/2025'] };
        }
        if (options.expectedLeagueId === 49) {
          return { allAvailableSeasons: ['2027/2028', '2023/2024'] };
        }
        if (options.expectedLeagueId === 50) {
          return {};
        }
        throw new Error('network-failed');
      }
    });

    assert.strictEqual(await discovery.discover(47, '2025'), '2025');
    assert.strictEqual(await discovery.discover(47, '20242025'), '2024/2025');
    assert.strictEqual(await discovery.discover(48, '2026'), '2025/2026');
    assert.strictEqual(await discovery.discover(49, '2026'), '2026');
    assert.strictEqual(await discovery.discover(50, '2026'), '2026');
    assert.strictEqual(await discovery.discover(51, '2026'), '2026');
    assert.ok(warnings.some((message) => message.includes('未获取到 allAvailableSeasons')));
    assert.ok(warnings.some((message) => message.includes('未找到可信赛季映射')));
    assert.ok(warnings.some((message) => message.includes('探测失败')));
  });
});
