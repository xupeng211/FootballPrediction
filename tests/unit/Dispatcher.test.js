/**
 * Dispatcher.test.js - 任务分派器单元测试
 * ========================================
 * 目标覆盖率: 90%+
 */

'use strict';

const assert = require('assert');
const { Dispatcher } = require('../../src/infrastructure/harvesters/components/Dispatcher.js');

console.log('\n=== Dispatcher Unit Tests ===\n');

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

// 测试组 1: 构造函数和默认值
test('构造函数 - 默认配置', () => {
    const d = new Dispatcher();
    assert.strictEqual(d.config.maxWorkers, 6);
    assert.strictEqual(d.config.batchSize, 500);
    assert.strictEqual(d.stats.total, 0);
    assert.strictEqual(d.startTime, null);
});

test('构造函数 - 自定义配置', () => {
    const d = new Dispatcher({ maxWorkers: 10, batchSize: 1000 });
    assert.strictEqual(d.config.maxWorkers, 10);
    assert.strictEqual(d.config.batchSize, 1000);
});

// 测试组 2: Worker ID 计算
test('calculateWorkerId - 正常情况', () => {
    const d = new Dispatcher({ maxWorkers: 6 });
    assert.strictEqual(d.calculateWorkerId(0), 1);
    assert.strictEqual(d.calculateWorkerId(5), 6);
    assert.strictEqual(d.calculateWorkerId(6), 1);
    assert.strictEqual(d.calculateWorkerId(11), 6);
    assert.strictEqual(d.calculateWorkerId(12), 1);
});

test('calculateWorkerId - 边界值', () => {
    const d = new Dispatcher({ maxWorkers: 6 });
    assert.strictEqual(d.calculateWorkerId(-1), 0); // -1 % 6 = -1, +1 = 0
    assert.strictEqual(d.calculateWorkerId(1000), 5); // 1000 % 6 = 4, +1 = 5
});

test('calculateWorkerId - 不同worker数', () => {
    const d = new Dispatcher({ maxWorkers: 3 });
    assert.strictEqual(d.calculateWorkerId(0), 1);
    assert.strictEqual(d.calculateWorkerId(2), 3);
    assert.strictEqual(d.calculateWorkerId(3), 1);
});

// 测试组 3: 延迟计算
test('calculateDelay - 正常情况', () => {
    const d = new Dispatcher();
    const delay = d.calculateDelay(false, 1000, 2000);
    assert.ok(delay >= 1000 && delay <= 2000, `延迟 ${delay} 应在 1000-2000 范围内`);
});

test('calculateDelay - 重试情况', () => {
    const d = new Dispatcher();
    const delay = d.calculateDelay(true, 1000, 2000);
    assert.ok(delay >= 3000 && delay <= 6000, `重试延迟 ${delay} 应在 3000-6000 范围内`);
});

test('calculateDelay - 多次随机', () => {
    const d = new Dispatcher();
    for (let i = 0; i < 20; i++) {
        const delay = d.calculateDelay(false, 1000, 2000);
        assert.ok(delay >= 1000 && delay <= 2000);
    }
});

// 测试组 4: 成功率计算
test('calculateSuccessRate - 正常情况', () => {
    const d = new Dispatcher();
    d.stats.total = 100;
    d.stats.success = 85;
    assert.strictEqual(d.calculateSuccessRate(), '85.0');
});

test('calculateSuccessRate - 零除保护', () => {
    const d = new Dispatcher();
    assert.strictEqual(d.calculateSuccessRate(), '0.0');
});

test('calculateSuccessRate - 100%成功', () => {
    const d = new Dispatcher();
    d.stats.total = 50;
    d.stats.success = 50;
    assert.strictEqual(d.calculateSuccessRate(), '100.0');
});

test('calculateSuccessRate - 0%成功', () => {
    const d = new Dispatcher();
    d.stats.total = 100;
    d.stats.success = 0;
    assert.strictEqual(d.calculateSuccessRate(), '0.0');
});

// 测试组 5: 时间计算
test('getElapsedTime - 未开始', () => {
    const d = new Dispatcher();
    assert.strictEqual(d.getElapsedTime(), '0.0');
});

test('getElapsedTime - 已开始', () => {
    const d = new Dispatcher();
    d.startTimer();
    const elapsed = parseFloat(d.getElapsedTime());
    assert.ok(elapsed >= 0 && elapsed < 1, '已开始的时间应在 0-1 秒内');
});

test('startTimer - 设置正确', () => {
    const d = new Dispatcher();
    const before = Date.now();
    d.startTimer();
    const after = Date.now();
    assert.ok(d.startTime >= before && d.startTime <= after);
});

// 测试组 6: 统计更新
test('updateStats - 成功', () => {
    const d = new Dispatcher();
    d.updateStats(true, false);
    assert.strictEqual(d.stats.processed, 1);
    assert.strictEqual(d.stats.success, 1);
    assert.strictEqual(d.stats.failed, 0);
    assert.strictEqual(d.stats.retries, 0);
});

test('updateStats - 失败', () => {
    const d = new Dispatcher();
    d.updateStats(false, false);
    assert.strictEqual(d.stats.processed, 1);
    assert.strictEqual(d.stats.success, 0);
    assert.strictEqual(d.stats.failed, 1);
});

test('updateStats - 重试', () => {
    const d = new Dispatcher();
    d.updateStats(true, true);
    assert.strictEqual(d.stats.retries, 1);
});

test('updateStats - 多次更新', () => {
    const d = new Dispatcher();
    d.updateStats(true, false);
    d.updateStats(false, true);
    d.updateStats(true, false);
    assert.strictEqual(d.stats.processed, 3);
    assert.strictEqual(d.stats.success, 2);
    assert.strictEqual(d.stats.failed, 1);
    assert.strictEqual(d.stats.retries, 1);
});

// 测试组 7: 扫尾轮数
test('incrementSweepRound - 单次', () => {
    const d = new Dispatcher();
    d.incrementSweepRound();
    assert.strictEqual(d.stats.sweepRounds, 1);
});

test('incrementSweepRound - 多次', () => {
    const d = new Dispatcher();
    for (let i = 0; i < 5; i++) {
        d.incrementSweepRound();
    }
    assert.strictEqual(d.stats.sweepRounds, 5);
});

// 测试组 8: 设置总任务数
test('setTotal - 设置正确', () => {
    const d = new Dispatcher();
    d.setTotal(100);
    assert.strictEqual(d.stats.total, 100);
});

// 测试组 9: 报告生成
test('generateReport - 基本结构', () => {
    const d = new Dispatcher();
    d.startTimer();
    d.setTotal(100);
    d.updateStats(true, false);
    const report = d.generateReport();
    assert.ok(report.elapsed);
    assert.strictEqual(report.total, 100);
    assert.strictEqual(report.processed, 1);
    assert.strictEqual(report.success, 1);
    assert.strictEqual(report.failed, 0);
    assert.strictEqual(report.retries, 0);
    assert.strictEqual(report.sweepRounds, 0);
    assert.ok(report.successRate);
});

test('generateReport - 完整数据', () => {
    const d = new Dispatcher();
    d.startTimer();
    d.setTotal(100);
    d.updateStats(true, false);
    d.updateStats(false, true);
    d.updateStats(true, false);
    d.incrementSweepRound();
    const report = d.generateReport();
    assert.strictEqual(report.total, 100);
    assert.strictEqual(report.processed, 3);
    assert.strictEqual(report.success, 2);
    assert.strictEqual(report.failed, 1);
    assert.strictEqual(report.retries, 1);
    assert.strictEqual(report.sweepRounds, 1);
});

// 测试组 10: printReport（模拟console.log）
test('printReport - 不报错', () => {
    const d = new Dispatcher();
    d.startTimer();
    d.setTotal(10);
    d.updateStats(true, false);
    // 只验证不抛出错误
    d.printReport();
});

// 测试组 11: CLI参数解析
test('parseCliArgs - 空参数', () => {
    const opts = Dispatcher.parseCliArgs([]);
    assert.strictEqual(opts.matchId, null);
    assert.strictEqual(opts.force, false);
    assert.strictEqual(opts.verbose, false);
});

test('parseCliArgs - matchId', () => {
    const opts = Dispatcher.parseCliArgs(['--matchId=abc123']);
    assert.strictEqual(opts.matchId, 'abc123');
});

test('parseCliArgs - force长选项', () => {
    const opts = Dispatcher.parseCliArgs(['--force']);
    assert.strictEqual(opts.force, true);
});

test('parseCliArgs - force短选项', () => {
    const opts = Dispatcher.parseCliArgs(['-f']);
    assert.strictEqual(opts.force, true);
});

test('parseCliArgs - verbose长选项', () => {
    const opts = Dispatcher.parseCliArgs(['--verbose']);
    assert.strictEqual(opts.verbose, true);
});

test('parseCliArgs - verbose短选项', () => {
    const opts = Dispatcher.parseCliArgs(['-v']);
    assert.strictEqual(opts.verbose, true);
});

test('parseCliArgs - 组合参数', () => {
    const opts = Dispatcher.parseCliArgs(['--matchId=xyz', '--force', '-v']);
    assert.strictEqual(opts.matchId, 'xyz');
    assert.strictEqual(opts.force, true);
    assert.strictEqual(opts.verbose, true);
});

// 测试组 12: 批次查询参数
test('generateBatchQueryParams - 默认模式', () => {
    const d = new Dispatcher({ batchSize: 500 });
    const params = d.generateBatchQueryParams(false);
    assert.strictEqual(params.limit, 500);
    assert.strictEqual(params.orderBy, 'match_date DESC');
    assert.strictEqual(params.league, undefined);
});

test('generateBatchQueryParams - Serie A模式', () => {
    const d = new Dispatcher();
    const params = d.generateBatchQueryParams(true);
    assert.strictEqual(params.limit, 10);
    assert.strictEqual(params.league, 'Serie A');
    assert.strictEqual(params.orderBy, 'match_date DESC');
});

// 测试组 13: 日志前缀
test('getLogPrefix - 基本', () => {
    const d = new Dispatcher();
    assert.strictEqual(d.getLogPrefix(1), '[W1]');
    assert.strictEqual(d.getLogPrefix(6), '[W6]');
});

test('getLogPrefix - 带重试', () => {
    const d = new Dispatcher();
    assert.strictEqual(d.getLogPrefix(1, 2, true), '[W1]-R2');
});

test('getLogPrefix - 无Worker', () => {
    const d = new Dispatcher();
    assert.strictEqual(d.getLogPrefix(null), '');
});

// 测试组 14: 重置统计
test('resetStats - 完全重置', () => {
    const d = new Dispatcher();
    d.startTimer();
    d.setTotal(100);
    d.updateStats(true, false);
    d.incrementSweepRound();
    d.resetStats();
    assert.strictEqual(d.stats.total, 0);
    assert.strictEqual(d.stats.processed, 0);
    assert.strictEqual(d.stats.success, 0);
    assert.strictEqual(d.stats.failed, 0);
    assert.strictEqual(d.stats.retries, 0);
    assert.strictEqual(d.stats.sweepRounds, 0);
    assert.strictEqual(d.startTime, null);
});

// 总结
console.log(`\n=== 测试结果: ${testsPassed}/${testsRun} 通过 ===\n`);

if (testsPassed === testsRun) {
    console.log('✅ 所有测试通过！');
    process.exit(0);
} else {
    console.error('❌ 有测试失败');
    process.exit(1);
}
