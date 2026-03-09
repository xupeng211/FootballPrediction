/**
 * V4.46.1 熔断器测试
 * =====================
 *
 * 测试目标: 验证 NetworkShield 在所有代理不可用时
 *          能正确抛出 CIRCUIT_BREAKER_OPEN 错误，而不是死循环
 *
 * 用法:
 *   node scripts/ops/circuit_breaker_test.js
 *
 * @version V4.46.1
 */

'use strict';

console.log('🛡️ V4.46.1 熔断器测试启动...');
console.log(`📅 ${new Date().toISOString()}`);
console.log('');

// ============================================================================
// 测试工具
// ============================================================================

let assert;
try {
    assert = require('node:assert');
} catch {
    assert = require('assert');
}

// ============================================================================
// 模块加载
// ============================================================================

let NetworkShield, getNetworkShield;

try {
    const module = require('../../src/infrastructure/network/NetworkShield');
    NetworkShield = module.NetworkShield;
    getNetworkShield = module.getNetworkShield;
    console.log('✅ NetworkShield 模块加载成功');
} catch (error) {
    console.error('❌ 模块加载失败:', error.message);
    process.exit(1);
}

// ============================================================================
// 测试用例
// ============================================================================

/**
 * 测试1: 正常分配端口
 */
async function testNormalPortAssignment() {
    console.log('\n📋 测试1: 正常端口分配');

    const shield = new NetworkShield();
    const result = shield.assignPort(1);

    assert(result.port >= 7890 && result.port <= 7911, '端口应在 7890-7911 范围内');
    assert(result.host, '应返回 host');
    assert(result.url, '应返回 url');

    console.log(`   ✓ Worker 1 分配到端口 ${result.port}`);
    console.log('   ✅ 测试1通过');
}

/**
 * 测试2: Session Stickiness (重复分配应返回相同端口)
 */
async function testSessionStickiness() {
    console.log('\n📋 测试2: Session Stickiness');

    const shield = new NetworkShield();
    const result1 = shield.assignPort(5);
    const result2 = shield.assignPort(5);

    assert(result1.port === result2.port, '同一 Worker 应分配相同端口');

    console.log(`   ✓ Worker 5 两次都分配到端口 ${result1.port}`);
    console.log('   ✅ 测试2通过');
}

/**
 * 测试3: 全局熔断保护 - 冷却窗口机制
 * V4.46.1: 验证 60 秒冷却窗口
 */
async function testGlobalCircuitBreakerCooldown() {
    console.log('\n📋 测试3: 全局熔断保护 - 冷却窗口机制');

    const shield = new NetworkShield();

    // 模拟所有代理节点熔断
    console.log('   🔧 模拟所有代理节点熔断...');
    for (const node of shield.proxyNodes) {
        node.status = 'cooldown';
        node.failureCount = 5;
    }

    // 模拟最近刚重置过熔断器 (30秒前)
    shield.lastGlobalResetTime = Date.now() - 30000;

    const statusBefore = shield.getStatus();
    console.log(`   📊 代理池状态: ${statusBefore.active}/${statusBefore.total} 可用`);
    console.log(`   ⏰ 模拟 30 秒前刚重置过熔断器`);

    let errorThrown = false;
    let error = null;

    try {
        shield.assignPort(99);
    } catch (e) {
        errorThrown = true;
        error = e;
        console.log(`   🚨 捕获到错误: ${e.name}`);
        console.log(`   📝 错误消息: ${e.message}`);
        console.log(`   🏷️ 错误代码: ${e.code}`);

        assert(e.name === 'CircuitBreakerOpenError', '错误类型应为 CircuitBreakerOpenError');
        assert(e.code === 'CIRCUIT_BREAKER_OPEN', '错误代码应为 CIRCUIT_BREAKER_OPEN');
        assert(e.message.includes('冷却') || e.message.includes('60 秒'), '错误消息应包含冷却信息');
    }

    assert(errorThrown, '冷却窗口内必须抛出错误');
    console.log('   ✅ 测试3通过 - 冷却窗口机制正常工作！');
}

/**
 * 测试4: 熔断恢复机制 - 冷却窗口过期后可重置
 */
async function testCircuitBreakerRecoveryAfterCooldown() {
    console.log('\n📋 测试4: 熔断恢复机制 - 冷却窗口过期后可重置');

    const shield = new NetworkShield();

    // 模拟所有代理节点熔断
    for (const node of shield.proxyNodes) {
        node.status = 'cooldown';
        node.failureCount = 5;
    }

    // 模拟很久以前重置过 (120秒前，超过60秒冷却窗口)
    shield.lastGlobalResetTime = Date.now() - 120000;

    console.log(`   ⏰ 模拟 120 秒前重置过熔断器 (已过冷却窗口)`);

    // 应该能成功分配 (熔断器会被重置)
    const result = shield.assignPort(10);
    assert(result.port >= 7890 && result.port <= 7911, '应分配到有效端口');

    console.log(`   ✓ Worker 10 分配到端口 ${result.port}`);
    console.log('   ✅ 测试4通过');
}

/**
 * 测试5: 部分代理可用时的正常分配
 */
async function testPartialCircuitBreaker() {
    console.log('\n📋 测试5: 部分代理可用时的正常分配');

    const shield = new NetworkShield();

    // 部分代理熔断
    for (let i = 0; i < 15; i++) {
        shield.proxyNodes[i].status = 'cooldown';
    }

    const statusBefore = shield.getStatus();
    console.log(`   📊 熔断前: ${statusBefore.active}/${statusBefore.total} 可用`);

    // 应该能分配到可用端口
    const result = shield.assignPort(20);
    assert(result.port >= 7890 && result.port <= 7911, '应分配到有效端口');

    console.log(`   ✓ Worker 20 分配到端口 ${result.port}`);
    console.log('   ✅ 测试5通过');
}

/**
 * 测试6: 强制重分配熔断保护
 */
async function testForceReassignCircuitBreaker() {
    console.log('\n📋 测试6: 强制重分配熔断保护');

    const shield = new NetworkShield();

    // 先分配一个端口
    const firstResult = shield.assignPort(30);
    console.log(`   📍 Worker 30 初始端口: ${firstResult.port}`);

    // 模拟所有代理熔断
    for (const node of shield.proxyNodes) {
        node.status = 'cooldown';
    }

    // 模拟最近刚重置过
    shield.lastGlobalResetTime = Date.now() - 10000;

    let errorThrown = false;

    try {
        shield.forceReassign(30, firstResult.port);
    } catch (error) {
        errorThrown = true;
        assert(error.code === 'CIRCUIT_BREAKER_OPEN', '错误代码应为 CIRCUIT_BREAKER_OPEN');
        console.log(`   🚨 正确抛出熔断错误: ${error.message}`);
    }

    assert(errorThrown, '强制重分配在冷却窗口内必须抛出错误');
    console.log('   ✅ 测试6通过');
}

/**
 * 测试7: 错误分类联动测试
 */
async function testErrorClassification() {
    console.log('\n📋 测试7: 错误分类联动 (AbstractHarvester)');

    // 模拟 _classifyError 逻辑
    function classifyError(errorMessage) {
        const msg = (errorMessage || '').toLowerCase();
        if (msg.includes('circuit_breaker_open') || msg.includes('全局熔断') || msg.includes('所有代理节点不可用') || msg.includes('冷却')) return 'BLOCKED';
        if (msg.includes('403') || msg.includes('forbidden')) return 'RATE_LIMITED';
        if (msg.includes('timeout')) return 'TIMEOUT';
        return 'UNKNOWN';
    }

    const testCases = [
        { msg: 'CIRCUIT_BREAKER_OPEN: 全局熔断', expected: 'BLOCKED' },
        { msg: '所有代理节点不可用', expected: 'BLOCKED' },
        { msg: '全局熔断：无可用代理', expected: 'BLOCKED' },
        { msg: '全局冷却中：60 秒内已重置过熔断器', expected: 'BLOCKED' },
        { msg: '403 Forbidden', expected: 'RATE_LIMITED' },
        { msg: 'Request timeout', expected: 'TIMEOUT' }
    ];

    for (const tc of testCases) {
        const result = classifyError(tc.msg);
        assert(result === tc.expected, `"${tc.msg}" 应分类为 ${tc.expected}`);
        console.log(`   ✓ "${tc.msg}" → ${result}`);
    }

    console.log('   ✅ 测试7通过');
}

/**
 * 测试8: 防死循环验证 (连续多次分配不应卡住)
 */
async function testNoInfiniteLoop() {
    console.log('\n📋 测试8: 防死循环验证');

    const shield = new NetworkShield();

    // 模拟所有代理熔断 + 冷却窗口内
    for (const node of shield.proxyNodes) {
        node.status = 'cooldown';
    }
    shield.lastGlobalResetTime = Date.now() - 10000;

    const startTime = Date.now();
    let errorCount = 0;
    const maxAttempts = 10;

    // 连续尝试分配，应该快速失败而不是死循环
    for (let i = 0; i < maxAttempts; i++) {
        try {
            shield.assignPort(i + 100);
        } catch (e) {
            errorCount++;
        }
    }

    const duration = Date.now() - startTime;

    assert(errorCount === maxAttempts, '所有尝试都应该抛出错误');
    assert(duration < 1000, `10 次分配应该在 1 秒内完成 (实际: ${duration}ms)，否则可能存在死循环`);

    console.log(`   ✓ ${maxAttempts} 次分配全部快速失败`);
    console.log(`   ✓ 总耗时: ${duration}ms (防死循环验证通过)`);
    console.log('   ✅ 测试8通过');
}

// ============================================================================
// 主函数
// ============================================================================

async function main() {
    console.log('╔═══════════════════════════════════════════════════════════════╗');
    console.log('║  🛡️ V4.46.1 熔断器压力测试                                    ║');
    console.log('║  目标: 验证全局熔断时不会死循环                               ║');
    console.log('╚═══════════════════════════════════════════════════════════════╝');

    const tests = [
        { name: '正常端口分配', fn: testNormalPortAssignment },
        { name: 'Session Stickiness', fn: testSessionStickiness },
        { name: '全局熔断冷却窗口', fn: testGlobalCircuitBreakerCooldown },
        { name: '冷却窗口过期恢复', fn: testCircuitBreakerRecoveryAfterCooldown },
        { name: '部分代理可用', fn: testPartialCircuitBreaker },
        { name: '强制重分配熔断', fn: testForceReassignCircuitBreaker },
        { name: '错误分类联动', fn: testErrorClassification },
        { name: '防死循环验证', fn: testNoInfiniteLoop }
    ];

    let passed = 0;
    let failed = 0;

    for (const test of tests) {
        try {
            await test.fn();
            passed++;
        } catch (error) {
            failed++;
            console.error(`   ❌ ${test.name} 失败: ${error.message}`);
        }
    }

    console.log('\n╔═══════════════════════════════════════════════════════════════╗');
    console.log('║  📊 测试结果汇总                                               ║');
    console.log('╚═══════════════════════════════════════════════════════════════╝');
    console.log(`   通过: ${passed}/${tests.length}`);
    console.log(`   失败: ${failed}/${tests.length}`);
    console.log('');

    if (failed === 0) {
        console.log('🎉 所有测试通过！V4.46.1 熔断器已就绪！');
        console.log('   "防爆盖"已扣紧，代理池死循环风险已消除！');
        return 0;
    } else {
        console.log('⚠️  部分测试失败，请检查上述错误');
        return 1;
    }
}

// ============================================================================
// 启动
// ============================================================================

(async () => {
    try {
        const exitCode = await main();
        process.exit(exitCode);
    } catch (error) {
        console.error('💥 测试执行失败:', error.message);
        console.error(error.stack);
        process.exit(1);
    }
})();
