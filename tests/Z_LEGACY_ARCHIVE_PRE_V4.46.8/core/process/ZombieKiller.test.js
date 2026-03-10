/**
 * ZombieKiller 单元测试
 * @module tests/core/process/ZombieKiller.test
 */

'use strict';

const assert = require('assert');
const { ZombieKiller, preFlightCleanup, forceKillBrowser } = require('../../../src/core/process');

// ============================================================================
// 测试用例
// ============================================================================

async function testConstructor() {
    console.log('测试: ZombieKiller 构造函数');

    const killer = new ZombieKiller({
        timeout: 3000,
        targetProcesses: ['chrome', 'firefox'],
        silent: true
    });

    assert.strictEqual(killer.timeout, 3000);
    assert.deepStrictEqual(killer.targetProcesses, ['chrome', 'firefox']);
    assert.strictEqual(killer.silent, true);

    // 默认值测试
    const defaultKiller = new ZombieKiller();
    assert.strictEqual(defaultKiller.timeout, 5000);
    assert.deepStrictEqual(defaultKiller.targetProcesses, ['chromium', 'chrome']);
    assert.strictEqual(defaultKiller.silent, false);

    console.log('✅ 构造函数测试通过');
}

async function testFindZombieProcesses() {
    console.log('测试: findZombieProcesses 方法');

    const killer = new ZombieKiller({ silent: true });

    // 这个方法会调用 pgrep，在测试环境中可能没有僵尸进程
    const pids = killer.findZombieProcesses();

    // 应该返回数组（可能为空）
    assert.ok(Array.isArray(pids));

    console.log('✅ findZombieProcesses 测试通过');
}

async function testPreFlightCleanup() {
    console.log('测试: preFlightCleanup 方法');

    const killer = new ZombieKiller({ silent: true });
    const stats = killer.preFlightCleanup(1);

    // 验证返回结构
    assert.ok('found' in stats);
    assert.ok('killed' in stats);
    assert.ok('failed' in stats);
    assert.ok('pids' in stats);
    assert.ok(Array.isArray(stats.pids));

    // 验证 lastCleanupStats 被更新
    assert.strictEqual(killer.lastCleanupStats, stats);

    console.log('✅ preFlightCleanup 测试通过');
}

async function testForceKillBrowser() {
    console.log('测试: forceKillBrowser 方法');

    const killer = new ZombieKiller({ silent: true });
    const stats = killer.forceKillBrowser(1);

    // 验证返回结构
    assert.ok('found' in stats);
    assert.ok('killed' in stats);
    assert.ok('pids' in stats);
    assert.ok(Array.isArray(stats.pids));

    console.log('✅ forceKillBrowser 测试通过');
}

async function testHasZombieProcesses() {
    console.log('测试: hasZombieProcesses 方法');

    const killer = new ZombieKiller({ silent: true });
    const result = killer.hasZombieProcesses();

    // 应该返回布尔值
    assert.strictEqual(typeof result, 'boolean');

    console.log('✅ hasZombieProcesses 测试通过');
}

async function testGetLastStats() {
    console.log('测试: getLastStats 方法');

    const killer = new ZombieKiller({ silent: true });

    // 初始状态为 null
    assert.strictEqual(killer.getLastStats(), null);

    // 执行清理后应有统计
    killer.preFlightCleanup(1);
    assert.ok(killer.getLastStats() !== null);

    console.log('✅ getLastStats 测试通过');
}

async function testStaticMethods() {
    console.log('测试: 静态方法');

    // 测试 quickClean
    const quickStats = ZombieKiller.quickClean(1);
    assert.ok('found' in quickStats);
    assert.ok('killed' in quickStats);

    // 测试便捷函数
    const cleanupStats = preFlightCleanup(1);
    assert.ok('found' in cleanupStats);

    const killStats = forceKillBrowser(1);
    assert.ok('found' in killStats);

    console.log('✅ 静态方法测试通过');
}

async function testKillProcess() {
    console.log('测试: killProcess 方法');

    const killer = new ZombieKiller({ silent: true });

    // 测试杀死不存在的进程 (应该返回 false 或 true，取决于系统)
    const result = killer.killProcess('999999999');
    assert.strictEqual(typeof result, 'boolean');

    console.log('✅ killProcess 测试通过');
}

// ============================================================================
// 运行测试
// ============================================================================

async function runTests() {
    console.log('\n========================================');
    console.log('ZombieKiller 单元测试');
    console.log('========================================\n');

    try {
        await testConstructor();
        await testFindZombieProcesses();
        await testPreFlightCleanup();
        await testForceKillBrowser();
        await testHasZombieProcesses();
        await testGetLastStats();
        await testStaticMethods();
        await testKillProcess();

        console.log('\n========================================');
        console.log('✅ 所有 ZombieKiller 测试通过');
        console.log('========================================\n');

    } catch (error) {
        console.error('\n❌ 测试失败:', error.message);
        console.error(error.stack);
        process.exit(1);
    }
}

// 入口
runTests();
