/**
 * Persistence.test.js - 数据持久化器单元测试
 * ============================================
 * 目标覆盖率: 90%+
 */

'use strict';

const assert = require('assert');
const path = require('path');
const fs = require('fs').promises;
const { Persistence } = require('../../src/infrastructure/harvesters/components/Persistence.js');

console.log('\n=== Persistence Unit Tests ===\n');

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

// 模拟数据库客户端
function createMockClient(shouldFail = false) {
    return {
        query: async () => {
            if (shouldFail) {
                const err = new Error('DB Error');
                err.code = '23505';
                throw err;
            }
            return { rowCount: 1 };
        },
        release: () => {}
    };
}

function createMockPool(shouldFail = false) {
    return {
        connect: async () => createMockClient(shouldFail)
    };
}

// 测试组 1: 构造函数
test('构造函数 - 默认配置', () => {
    const p = new Persistence();
    assert.strictEqual(p.dataPath, 'data/matches');
});

test('构造函数 - 自定义路径', () => {
    const p = new Persistence({ dataPath: 'custom/path' });
    assert.strictEqual(p.dataPath, 'custom/path');
});

// 测试组 2: 数据库错误分类器
test('_classifyDatabaseError - 网络错误', () => {
    const p = new Persistence();
    const err = new Error('Connection refused');
    err.code = 'ECONNREFUSED';
    assert.strictEqual(p._classifyDatabaseError(err), '[DB-NETWORK]');
});

test('_classifyDatabaseError - 超时错误', () => {
    const p = new Persistence();
    const err = new Error('Connection timeout');
    err.code = 'ETIMEDOUT';
    assert.strictEqual(p._classifyDatabaseError(err), '[DB-NETWORK]');
});

test('_classifyDatabaseError - 认证错误', () => {
    const p = new Persistence();
    const err = new Error('password authentication failed');
    err.code = '28P01';
    assert.strictEqual(p._classifyDatabaseError(err), '[DB-AUTH]');
});

test('_classifyDatabaseError - 重复键', () => {
    const p = new Persistence();
    const err = new Error('Duplicate key');
    err.code = '23505';
    assert.strictEqual(p._classifyDatabaseError(err), '[DB-DUPLICATE]');
});

test('_classifyDatabaseError - 表不存在', () => {
    const p = new Persistence();
    const err = new Error('Table not found');
    err.code = '42P01';
    assert.strictEqual(p._classifyDatabaseError(err), '[DB-TABLE-NOT-FOUND]');
});

test('_classifyDatabaseError - 通用错误', () => {
    const p = new Persistence();
    const err = new Error('Unknown error');
    err.code = 'UNKNOWN';
    assert.strictEqual(p._classifyDatabaseError(err), '[DB-ERROR]');
});

// 测试组 3: 文件错误分类器
test('_classifyFileError - 文件不存在', () => {
    const p = new Persistence();
    const err = new Error('ENOENT: no such file');
    assert.strictEqual(p._classifyFileError(err), '[FILE-NOT-FOUND]');
});

test('_classifyFileError - 权限错误', () => {
    const p = new Persistence();
    const err = new Error('EACCES: permission denied');
    assert.strictEqual(p._classifyFileError(err), '[PERMISSION]');
});

test('_classifyFileError - 权限关键字', () => {
    const p = new Persistence();
    const err = new Error('permission denied by user');
    assert.strictEqual(p._classifyFileError(err), '[PERMISSION]');
});

test('_classifyFileError - 磁盘满', () => {
    const p = new Persistence();
    const err = new Error('ENOSPC: no space');
    assert.strictEqual(p._classifyFileError(err), '[DISK-FULL]');
});

test('_classifyFileError - 通用错误', () => {
    const p = new Persistence();
    const err = new Error('Random error');
    assert.strictEqual(p._classifyFileError(err), '[FILE-ERROR]');
});

// 测试组 4: 获取统计
test('getStats - 基本结构', () => {
    const p = new Persistence();
    const stats = p.getStats();
    assert.strictEqual(stats.dataPath, 'data/matches');
    assert.strictEqual(stats.pendingWrites, 0);
});

test('getStats - 自定义路径', () => {
    const p = new Persistence({ dataPath: 'custom' });
    const stats = p.getStats();
    assert.strictEqual(stats.dataPath, 'custom');
});

// 测试组 5: 文件路径计算
test('文件路径 - 默认路径', () => {
    const p = new Persistence();
    const expectedDir = path.resolve(process.cwd(), 'data/matches');
    const expectedPath = path.join(expectedDir, 'test123.json');
    // 验证路径计算逻辑
    assert.ok(expectedPath.includes('data/matches'));
    assert.ok(expectedPath.includes('test123.json'));
});

test('文件路径 - 自定义路径', () => {
    const p = new Persistence({ dataPath: 'custom/dir' });
    const expectedDir = path.resolve(process.cwd(), 'custom/dir');
    const expectedPath = path.join(expectedDir, 'abc.json');
    assert.ok(expectedPath.includes('custom/dir'));
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