/**
 * ErrorHandler.test.js - 高级错误审计器单元测试
 * ================================================
 * 目标覆盖率: 90%+
 */

'use strict';

const assert = require('assert');
const { ErrorHandler, ErrorType } = require('../../src/infrastructure/harvesters/components/ErrorHandler.js');

console.log('\n=== ErrorHandler Unit Tests ===\n');

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
    const eh = new ErrorHandler();
    assert.strictEqual(eh.config.maxRetries, 3);
    assert.strictEqual(eh.config.enableDetailedLogging, false);
    assert.strictEqual(eh.stats.total, 0);
});

test('构造函数 - 自定义配置', () => {
    const eh = new ErrorHandler({ maxRetries: 5, enableDetailedLogging: true });
    assert.strictEqual(eh.config.maxRetries, 5);
    assert.strictEqual(eh.config.enableDetailedLogging, true);
});

// 测试组 2: 错误分类 - RETRYABLE
test('classify - timeout错误', () => {
    const eh = new ErrorHandler();
    const err = new Error('Connection timeout');
    assert.strictEqual(eh.classify(err), ErrorType.RETRYABLE);
});

test('classify - ECONNRESET错误', () => {
    const eh = new ErrorHandler();
    const err = new Error('ECONNRESET');
    err.code = 'ECONNRESET';
    assert.strictEqual(eh.classify(err), ErrorType.RETRYABLE);
});

test('classify - ETIMEDOUT错误', () => {
    const eh = new ErrorHandler();
    const err = new Error('ETIMEDOUT');
    err.code = 'ETIMEDOUT';
    assert.strictEqual(eh.classify(err), ErrorType.RETRYABLE);
});

test('classify - network错误', () => {
    const eh = new ErrorHandler();
    const err = new Error('Network unreachable');
    assert.strictEqual(eh.classify(err), ErrorType.RETRYABLE);
});

test('classify - rate limit错误', () => {
    const eh = new ErrorHandler();
    const err = new Error('Rate limit exceeded');
    assert.strictEqual(eh.classify(err), ErrorType.RETRYABLE);
});

test('classify - too many requests错误', () => {
    const eh = new ErrorHandler();
    const err = new Error('Too many requests');
    assert.strictEqual(eh.classify(err), ErrorType.RETRYABLE);
});

// 测试组 3: 错误分类 - FATAL
test('classify - authentication failed', () => {
    const eh = new ErrorHandler();
    const err = new Error('Authentication failed');
    assert.strictEqual(eh.classify(err), ErrorType.FATAL);
});

test('classify - access denied', () => {
    const eh = new ErrorHandler();
    const err = new Error('Access denied');
    assert.strictEqual(eh.classify(err), ErrorType.FATAL);
});

test('classify - permission denied', () => {
    const eh = new ErrorHandler();
    const err = new Error('Permission denied');
    assert.strictEqual(eh.classify(err), ErrorType.FATAL);
});

test('classify - not found', () => {
    const eh = new ErrorHandler();
    const err = new Error('Resource not found');
    assert.strictEqual(eh.classify(err), ErrorType.FATAL);
});

test('classify - parse error', () => {
    const eh = new ErrorHandler();
    const err = new Error('Parse error');
    assert.strictEqual(eh.classify(err), ErrorType.FATAL);
});

// 测试组 4: 错误分类 - IGNORE
test('classify - aborted错误', () => {
    const eh = new ErrorHandler();
    const err = new Error('Request aborted');
    assert.strictEqual(eh.classify(err), ErrorType.IGNORE);
});

test('classify - cancelled错误', () => {
    const eh = new ErrorHandler();
    const err = new Error('Request cancelled');
    assert.strictEqual(eh.classify(err), ErrorType.IGNORE);
});

test('classify - closed错误（忽略模式）', () => {
    const eh = new ErrorHandler();
    // 注意：'Connection closed' 包含 'connection closed' 会匹配 RETRYABLE
    // 这里测试纯 'closed' 关键字
    const err = new Error('Stream closed unexpectedly');
    assert.strictEqual(eh.classify(err), ErrorType.IGNORE);
});

// 测试组 5: 错误分类 - 网络/认证/超时/数据
test('classify - 网络错误代码', () => {
    const eh = new ErrorHandler();
    const err = new Error('Connection refused');
    err.code = 'ECONNREFUSED';
    // 优先匹配 RETRYABLE 中的 ECONNREFUSED 模式
    assert.strictEqual(eh.classify(err), ErrorType.RETRYABLE);
});

test('classify - 认证错误代码', () => {
    const eh = new ErrorHandler();
    // 使用不匹配 FATAL 模式的消息，让 code 检测生效
    const err = new Error('DB access issue');
    err.code = '28P01';
    // 28P01 会被 _isAuthError 检测为 AUTH
    assert.strictEqual(eh.classify(err), ErrorType.AUTH);
});

test('classify - 超时错误代码', () => {
    const eh = new ErrorHandler();
    const err = new Error('Request timed out');
    err.code = 'TIMEOUT';
    // 优先匹配 RETRYABLE
    assert.strictEqual(eh.classify(err), ErrorType.RETRYABLE);
});

test('classify - 数据错误代码', () => {
    const eh = new ErrorHandler();
    const err = new Error('Validation failed');
    // validation 属于 data error
    assert.strictEqual(eh.classify(err), ErrorType.DATA);
});

// 测试组 6: 边界条件
test('classify - null错误', () => {
    const eh = new ErrorHandler();
    assert.strictEqual(eh.classify(null), ErrorType.UNKNOWN);
});

test('classify - undefined错误', () => {
    const eh = new ErrorHandler();
    assert.strictEqual(eh.classify(undefined), ErrorType.UNKNOWN);
});

test('classify - 空消息错误', () => {
    const eh = new ErrorHandler();
    const err = new Error();
    assert.strictEqual(eh.classify(err), ErrorType.UNKNOWN);
});

test('classify - 未知错误', () => {
    const eh = new ErrorHandler();
    const err = new Error('Something completely unknown');
    assert.strictEqual(eh.classify(err), ErrorType.UNKNOWN);
});

// 测试组 7: 可重试性判断
test('isRetryable - 可重试错误', () => {
    const eh = new ErrorHandler();
    const err = new Error('Timeout');
    assert.strictEqual(eh.isRetryable(err, 1), true);
});

test('isRetryable - 不可重试错误', () => {
    const eh = new ErrorHandler();
    const err = new Error('Authentication failed');
    assert.strictEqual(eh.isRetryable(err, 1), false);
});

test('isRetryable - 达到最大重试次数', () => {
    const eh = new ErrorHandler({ maxRetries: 3 });
    const err = new Error('Timeout');
    assert.strictEqual(eh.isRetryable(err, 3), false);
    assert.strictEqual(eh.isRetryable(err, 4), false);
});

test('isRetryable - 网络错误可重试', () => {
    const eh = new ErrorHandler();
    const err = new Error('Network error');
    err.code = 'ECONNRESET';
    assert.strictEqual(eh.isRetryable(err, 1), true);
});

test('isRetryable - 超时错误可重试', () => {
    const eh = new ErrorHandler();
    const err = new Error('Timed out');
    assert.strictEqual(eh.isRetryable(err, 1), true);
});

// 测试组 8: 错误审计
test('audit - 基本审计', () => {
    const eh = new ErrorHandler();
    const err = new Error('Timeout');
    const type = eh.audit(err);
    assert.strictEqual(type, ErrorType.RETRYABLE);
    assert.strictEqual(eh.stats.total, 1);
    assert.strictEqual(eh.stats.byType[ErrorType.RETRYABLE], 1);
    assert.strictEqual(eh.stats.retryable, 1);
});

test('audit - 多次审计', () => {
    const eh = new ErrorHandler();
    eh.audit(new Error('Timeout'));
    eh.audit(new Error('Authentication failed')); // 匹配 FATAL
    eh.audit(new Error('Timeout'));
    assert.strictEqual(eh.stats.total, 3);
    assert.strictEqual(eh.stats.byType[ErrorType.RETRYABLE], 2);
    assert.strictEqual(eh.stats.byType[ErrorType.FATAL], 1);
    assert.strictEqual(eh.stats.retryable, 2);
    assert.strictEqual(eh.stats.fatal, 1);
});

test('audit - 带上下文', () => {
    const eh = new ErrorHandler({ enableDetailedLogging: true });
    const err = new Error('Test');
    const type = eh.audit(err, { matchId: '123' });
    assert.strictEqual(eh.stats.total, 1);
});

// 测试组 9: 生成报告
test('generateReport - 空报告', () => {
    const eh = new ErrorHandler();
    const report = eh.generateReport();
    assert.strictEqual(report.total, 0);
    assert.deepStrictEqual(report.byType, {});
    assert.strictEqual(report.retryable, 0);
    assert.strictEqual(report.fatal, 0);
    assert.strictEqual(report.retryRate, '0.0');
});

test('generateReport - 完整报告', () => {
    const eh = new ErrorHandler();
    eh.audit(new Error('Timeout'));
    eh.audit(new Error('Timeout'));
    eh.audit(new Error('Authentication failed'));
    const report = eh.generateReport();
    assert.strictEqual(report.total, 3);
    assert.strictEqual(report.byType[ErrorType.RETRYABLE], 2);
    assert.strictEqual(report.byType[ErrorType.FATAL], 1);
    assert.strictEqual(report.retryable, 2);
    assert.strictEqual(report.fatal, 1);
    assert.strictEqual(report.retryRate, '66.7');
});

// 测试组 10: 添加自定义模式
test('addPattern - 添加可重试模式', () => {
    const eh = new ErrorHandler();
    eh.addPattern('retryable', /custom retry pattern/);
    const err = new Error('custom retry pattern found');
    assert.strictEqual(eh.classify(err), ErrorType.RETRYABLE);
});

test('addPattern - 添加致命模式', () => {
    const eh = new ErrorHandler();
    eh.addPattern('fatal', /critical failure/);
    const err = new Error('critical failure occurred');
    assert.strictEqual(eh.classify(err), ErrorType.FATAL);
});

test('addPattern - 添加忽略模式', () => {
    const eh = new ErrorHandler();
    eh.addPattern('ignore', /user skip/);
    const err = new Error('user skip this step');
    assert.strictEqual(eh.classify(err), ErrorType.IGNORE);
});

test('addPattern - 无效类别不添加', () => {
    const eh = new ErrorHandler();
    eh.addPattern('invalid', /test/);
    // 不报错即可
    assert.strictEqual(eh.errorPatterns.invalid, undefined);
});

// 测试组 11: 重置统计
test('resetStats - 完全重置', () => {
    const eh = new ErrorHandler();
    eh.audit(new Error('Test'));
    eh.resetStats();
    assert.strictEqual(eh.stats.total, 0);
    assert.deepStrictEqual(eh.stats.byType, {});
    assert.strictEqual(eh.stats.retryable, 0);
    assert.strictEqual(eh.stats.fatal, 0);
});

// 测试组 12: 数据库错误分类器（兼容旧版）
test('classifyDatabaseError - 完整测试', () => {
    const eh = new ErrorHandler();
    
    const networkErr = new Error('conn');
    networkErr.code = 'ECONNREFUSED';
    assert.strictEqual(eh.classifyDatabaseError(networkErr), '[DB-NETWORK]');
    
    const authErr = new Error('password');
    authErr.code = '28P01';
    assert.strictEqual(eh.classifyDatabaseError(authErr), '[DB-AUTH]');
    
    const dupErr = new Error('dup');
    dupErr.code = '23505';
    assert.strictEqual(eh.classifyDatabaseError(dupErr), '[DB-DUPLICATE]');
    
    const tableErr = new Error('table');
    tableErr.code = '42P01';
    assert.strictEqual(eh.classifyDatabaseError(tableErr), '[DB-TABLE-NOT-FOUND]');
    
    const unknownErr = new Error('unknown');
    unknownErr.code = 'UNKNOWN';
    assert.strictEqual(eh.classifyDatabaseError(unknownErr), '[DB-ERROR]');
});

// 测试组 13: 文件错误分类器（兼容旧版）
test('classifyFileError - 完整测试', () => {
    const eh = new ErrorHandler();
    
    const notFoundErr = new Error('ENOENT');
    assert.strictEqual(eh.classifyFileError(notFoundErr), '[FILE-NOT-FOUND]');
    
    const permErr = new Error('EACCES');
    assert.strictEqual(eh.classifyFileError(permErr), '[PERMISSION]');
    
    const diskErr = new Error('ENOSPC');
    assert.strictEqual(eh.classifyFileError(diskErr), '[DISK-FULL]');
    
    const unknownErr = new Error('unknown');
    assert.strictEqual(eh.classifyFileError(unknownErr), '[FILE-ERROR]');
});

// 测试组 14: 内部辅助方法
test('_isNetworkError - 边界测试', () => {
    const eh = new ErrorHandler();
    
    // ECONNRESET 和 ETIMEDOUT 在 RETRYABLE 模式中
    const err1 = new Error('test');
    err1.code = 'ECONNRESET';
    assert.strictEqual(eh.classify(err1), ErrorType.RETRYABLE);
    
    const err2 = new Error('test');
    err2.code = 'ETIMEDOUT';
    assert.strictEqual(eh.classify(err2), ErrorType.RETRYABLE);
    
    // 其他网络错误代码会被 _isNetworkError 检测
    const err3 = new Error('test');
    err3.code = 'ENOTFOUND';
    assert.strictEqual(eh.classify(err3), ErrorType.NETWORK);
    
    const err4 = new Error('test');
    err4.code = 'EAI_AGAIN';
    assert.strictEqual(eh.classify(err4), ErrorType.NETWORK);
});

test('_isAuthError - 边界测试', () => {
    const eh = new ErrorHandler();
    
    // 28P01 会被 _isAuthError 检测为 AUTH
    const err1 = new Error('test');
    err1.code = '28P01';
    assert.strictEqual(eh.classify(err1), ErrorType.AUTH);
    
    // EACCES 会被 _isAuthError 检测为 AUTH
    const err2 = new Error('test');
    err2.code = 'EACCES';
    assert.strictEqual(eh.classify(err2), ErrorType.AUTH);
});

test('_isTimeoutError - 边界测试', () => {
    const eh = new ErrorHandler();
    
    const err = new Error('test');
    err.code = 'ETIMEDOUT';
    // 在 RETRYABLE 中优先匹配
    assert.strictEqual(eh.classify(err), ErrorType.RETRYABLE);
});

test('_isDataError - 边界测试', () => {
    const eh = new ErrorHandler();
    
    const err = new Error('validation failed');
    assert.strictEqual(eh.classify(err), ErrorType.DATA);
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
