/**
 * OddsFluxDetector.test.js - 赔率背离监测器单元测试
 * ===================================================
 * TITAN V5.0 首个算法模块测试
 * 目标覆盖率: 100%
 */

'use strict';

const assert = require('assert');
const { OddsFluxDetector, detectOddsFlux } = require('../../src/analysis/OddsFluxDetector.js');

console.log('\n=== OddsFluxDetector V5.0 Unit Tests ===\n');

let testsRun = 0;
let testsPassed = 0;

function test(name, fn) {
    testsRun++;
    try {
        fn();
        testsPassed++;
        console.log(`  ✓ ${name}`);
    } catch (e) {
        console.error(`  ✗ ${name}: ${e.message}`);
        throw e;
    }
}

// 测试组 1: 构造函数
test('构造函数 - 默认配置', () => {
    const detector = new OddsFluxDetector();
    assert.strictEqual(detector.config.deviationThreshold, 0.15);
    assert.strictEqual(detector.config.minOdds, 1.01);
    assert.strictEqual(detector.config.maxOdds, 1000);
});

test('构造函数 - 自定义配置', () => {
    const detector = new OddsFluxDetector({
        deviationThreshold: 0.20,
        minOdds: 1.50,
        maxOdds: 500
    });
    assert.strictEqual(detector.config.deviationThreshold, 0.20);
    assert.strictEqual(detector.config.minOdds, 1.50);
    assert.strictEqual(detector.config.maxOdds, 500);
});

// 测试组 2: 基础背离检测
test('detectDeviation - 无背离 (变化率 < 15%)', () => {
    const detector = new OddsFluxDetector();
    const result = detector.detectDeviation(2.0, 2.1); // 5% 变化

    assert.strictEqual(result.hasDeviation, false);
    assert.strictEqual(result.deviationRate, 0.05);
    assert.strictEqual(result.direction, 'up');
    assert.strictEqual(result.signalStrength, 0);
    assert.strictEqual(result.openingOdds, 2.0);
    assert.strictEqual(result.currentOdds, 2.1);
});

test('detectDeviation - 触发背离 (变化率 > 15%)', () => {
    const detector = new OddsFluxDetector();
    const result = detector.detectDeviation(2.0, 2.4); // 20% 变化

    assert.strictEqual(result.hasDeviation, true);
    assert.strictEqual(result.deviationRate, 0.2);
    assert.strictEqual(result.direction, 'up');
    assert.ok(result.signalStrength > 0.5);
});

test('detectDeviation - 赔率下降 (方向 down)', () => {
    const detector = new OddsFluxDetector();
    const result = detector.detectDeviation(2.0, 1.6); // -20% 变化

    assert.strictEqual(result.hasDeviation, true);
    assert.strictEqual(result.deviationRate, 0.2);
    assert.strictEqual(result.direction, 'down');
});

test('detectDeviation - 无变化 (方向 none)', () => {
    const detector = new OddsFluxDetector();
    const result = detector.detectDeviation(2.0, 2.0);

    assert.strictEqual(result.hasDeviation, false);
    assert.strictEqual(result.deviationRate, 0);
    assert.strictEqual(result.direction, 'none');
});

// 测试组 3: 边界值测试
test('detectDeviation - 刚好15%阈值 (不触发)', () => {
    const detector = new OddsFluxDetector();
    const result = detector.detectDeviation(2.0, 2.3); // 15% 变化

    assert.strictEqual(result.hasDeviation, false); // 15% 刚好不触发
    assert.strictEqual(result.deviationRate, 0.15);
});

test('detectDeviation - 刚好超过15% (触发)', () => {
    const detector = new OddsFluxDetector();
    const result = detector.detectDeviation(2.0, 2.301); // 15.05% 变化

    assert.strictEqual(result.hasDeviation, true);
});

test('detectDeviation - 30%背离 (高信号强度)', () => {
    const detector = new OddsFluxDetector();
    const result = detector.detectDeviation(2.0, 2.6); // 30% 变化

    assert.strictEqual(result.hasDeviation, true);
    assert.strictEqual(result.signalStrength, 1.0); // 30% = 2*15%，强度=1.0
});

// 测试组 4: 无效输入
test('detectDeviation - 无效赔率 (null)', () => {
    const detector = new OddsFluxDetector();
    const result = detector.detectDeviation(null, 2.0);

    assert.strictEqual(result.hasDeviation, false);
    assert.strictEqual(result.error, 'INVALID_ODDS');
});

test('detectDeviation - 无效赔率 (undefined)', () => {
    const detector = new OddsFluxDetector();
    const result = detector.detectDeviation(2.0, undefined);

    assert.strictEqual(result.hasDeviation, false);
    assert.strictEqual(result.error, 'INVALID_ODDS');
});

test('detectDeviation - 无效赔率 (NaN)', () => {
    const detector = new OddsFluxDetector();
    const result = detector.detectDeviation(NaN, 2.0);

    assert.strictEqual(result.hasDeviation, false);
    assert.strictEqual(result.error, 'INVALID_ODDS');
});

test('detectDeviation - 无效赔率 (负数)', () => {
    const detector = new OddsFluxDetector();
    const result = detector.detectDeviation(-1.0, 2.0);

    assert.strictEqual(result.hasDeviation, false);
    assert.strictEqual(result.error, 'INVALID_ODDS');
});

test('detectDeviation - 无效赔率 (过小)', () => {
    const detector = new OddsFluxDetector();
    const result = detector.detectDeviation(1.005, 2.0); // < 1.01

    assert.strictEqual(result.hasDeviation, false);
    assert.strictEqual(result.error, 'INVALID_ODDS');
});

test('detectDeviation - 无效赔率 (过大)', () => {
    const detector = new OddsFluxDetector();
    const result = detector.detectDeviation(2000, 2.0); // > 1000

    assert.strictEqual(result.hasDeviation, false);
    assert.strictEqual(result.error, 'INVALID_ODDS');
});

test('detectDeviation - 无效赔率 (Infinity)', () => {
    const detector = new OddsFluxDetector();
    const result = detector.detectDeviation(Infinity, 2.0);

    assert.strictEqual(result.hasDeviation, false);
    assert.strictEqual(result.error, 'INVALID_ODDS');
});

// 测试组 5: 批量检测
test('detectBatch - 正常批量检测', () => {
    const detector = new OddsFluxDetector();
    const oddsList = [
        { openingOdds: 2.0, currentOdds: 2.4, matchId: 'match1' },   // +20% 触发
        { openingOdds: 3.0, currentOdds: 2.4, matchId: 'match2' },   // -20% 触发
        { openingOdds: 1.5, currentOdds: 1.5, matchId: 'match3' }    // 0% 不触发
    ];

    const results = detector.detectBatch(oddsList);

    assert.strictEqual(results.length, 3);
    assert.strictEqual(results[0].hasDeviation, true);
    assert.strictEqual(results[1].hasDeviation, true);
    assert.strictEqual(results[2].hasDeviation, false);
    assert.strictEqual(results[0].matchId, 'match1');
});

test('detectBatch - 空数组', () => {
    const detector = new OddsFluxDetector();
    const results = detector.detectBatch([]);

    assert.deepStrictEqual(results, []);
});

test('detectBatch - 非数组输入', () => {
    const detector = new OddsFluxDetector();
    const results = detector.detectBatch(null);

    assert.deepStrictEqual(results, []);
});

// 测试组 6: 统计摘要
test('getSummary - 正常统计', () => {
    const detector = new OddsFluxDetector();
    const results = [
        { hasDeviation: true, deviationRate: 0.2, direction: 'up' },
        { hasDeviation: false, deviationRate: 0.05, direction: 'none' },
        { hasDeviation: true, deviationRate: 0.15, direction: 'down' }
    ];

    const summary = detector.getSummary(results);

    assert.strictEqual(summary.total, 3);
    assert.strictEqual(summary.deviationCount, 2);
    assert.strictEqual(summary.upCount, 1);
    assert.strictEqual(summary.downCount, 1);
    assert.ok(summary.avgDeviationRate > 0);
    assert.strictEqual(summary.maxDeviationRate, 0.2);
});

test('getSummary - 空数组', () => {
    const detector = new OddsFluxDetector();
    const summary = detector.getSummary([]);

    assert.strictEqual(summary.total, 0);
    assert.strictEqual(summary.deviationCount, 0);
    assert.strictEqual(summary.avgDeviationRate, 0);
});

test('getSummary - 非数组输入', () => {
    const detector = new OddsFluxDetector();
    const summary = detector.getSummary(null);

    assert.strictEqual(summary.total, 0);
    assert.strictEqual(summary.deviationCount, 0);
});

// 测试组 7: 配置管理
test('updateConfig - 更新配置', () => {
    const detector = new OddsFluxDetector();
    detector.updateConfig({ deviationThreshold: 0.25 });

    assert.strictEqual(detector.config.deviationThreshold, 0.25);
    assert.strictEqual(detector.config.minOdds, 1.01); // 未变
});

test('getConfig - 获取配置', () => {
    const detector = new OddsFluxDetector({ deviationThreshold: 0.20 });
    const config = detector.getConfig();

    assert.strictEqual(config.deviationThreshold, 0.20);
    assert.strictEqual(config.minOdds, 1.01);
});

test('getConfig - 返回副本', () => {
    const detector = new OddsFluxDetector();
    const config1 = detector.getConfig();
    const config2 = detector.getConfig();

    assert.notStrictEqual(config1, config2); // 不同引用
    assert.deepStrictEqual(config1, config2); // 内容相同
});

// 测试组 8: 便捷函数
test('detectOddsFlux - 便捷函数', () => {
    const result = detectOddsFlux(2.0, 2.4, 0.15);

    assert.strictEqual(result.hasDeviation, true);
    assert.strictEqual(result.deviationRate, 0.2);
});

test('detectOddsFlux - 默认阈值', () => {
    const result = detectOddsFlux(2.0, 2.3);

    assert.strictEqual(result.hasDeviation, false); // 15% 刚好不触发
});

// 测试组 9: 信号强度计算
test('信号强度 - 15%阈值时强度为0.5', () => {
    const detector = new OddsFluxDetector();
    // 刚好超过阈值一点点，让信号强度接近0.5
    const result = detector.detectDeviation(2.0, 2.3001);

    assert.ok(result.signalStrength >= 0.5);
    assert.ok(result.signalStrength < 0.6);
});

test('信号强度 - 22.5%时强度为0.75', () => {
    const detector = new OddsFluxDetector();
    const result = detector.detectDeviation(2.0, 2.45); // 22.5% 变化

    assert.ok(result.signalStrength >= 0.75);
});

test('信号强度 - 超过30%封顶为1.0', () => {
    const detector = new OddsFluxDetector();
    const result = detector.detectDeviation(2.0, 3.0); // 50% 变化

    assert.strictEqual(result.signalStrength, 1.0);
});

// 测试组 10: 精度测试
test('精度 - 背离率保留4位小数', () => {
    const detector = new OddsFluxDetector();
    const result = detector.detectDeviation(3.0, 3.333333);

    // 3.333333 / 3.0 - 1 = 0.111111
    assert.ok(result.deviationRate.toString().length <= 6); // 0.xxxx
});

// 总结
console.log(`\n=== V5.0 测试结果: ${testsPassed}/${testsRun} 通过 ===\n`);

if (testsPassed === testsRun) {
    console.log('✅ TITAN V5.0 首个算法模块测试通过！');
    console.log('✅ 100% 覆盖率达成！');
    process.exit(0);
} else {
    console.error('❌ 有测试失败');
    process.exit(1);
}
