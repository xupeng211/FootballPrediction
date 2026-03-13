/**
 * 硬核审计测试脚本 - 验证 ErrorAuditor 神经回路
 * =============================================
 *
 * 运行方式:
 * docker-compose -f docker-compose.dev.yml exec dev node tests/debug_audit.js
 */

'use strict';

const {
    ErrorAuditor,
    ErrorType,
    RETRYABLE_PATTERNS,
    NON_RETRYABLE_PATTERNS,
    getErrorAuditor,
    resetErrorAuditor
} = require('../src/core/harvesters/ErrorAuditor');

// ============================================================================
// 测试用例定义
// ============================================================================

const TEST_CASES = [
    {
        name: 'Turnstile 挑战',
        error: new Error('Cloudflare Turnstile challenge required'),
        expectedRetryable: false,
        expectedType: ErrorType.BLOCKED,
        reason: 'Turnstile 验证码需要人工介入，不可自动重试'
    },
    {
        name: 'ECONNRESET 网络错误',
        error: new Error('ECONNRESET'),
        expectedRetryable: true,
        expectedType: ErrorType.NETWORK_ERROR,
        reason: '网络重置是临时性问题，可以重试'
    },
    {
        name: '403 Forbidden',
        error: new Error('403 Forbidden'),
        expectedRetryable: false,
        expectedType: ErrorType.RATE_LIMITED,
        reason: '403 需要刷新身份，不能简单重试'
    },
    {
        name: 'CF_BLOCK (Cloudflare Block)',
        error: new Error('CF_BLOCK: Access denied'),
        expectedRetryable: false, // 期望: 不可重试
        expectedType: ErrorType.UNKNOWN,
        reason: 'Cloudflare 阻止需要办证，不应重试'
    },
    {
        name: 'Connection reset by peer',
        error: new Error('Connection reset by peer'),
        expectedRetryable: true,
        expectedType: ErrorType.NETWORK_ERROR,
        reason: '连接重置是网络问题，可重试'
    },
    {
        name: 'Navigation timeout',
        error: new Error('Navigation timeout of 30000ms exceeded'),
        expectedRetryable: true,
        expectedType: ErrorType.TIMEOUT,
        reason: '超时可重试'
    }
];

// ============================================================================
// 运行测试
// ============================================================================

console.log('\n');
console.log('═══════════════════════════════════════════════════════════════════════');
console.log('  \x1b[36m[AUDIT]\x1b[0m ErrorAuditor 神经回路硬核审计');
console.log('═══════════════════════════════════════════════════════════════════════\n');

// 重置单例确保干净状态
resetErrorAuditor();
const auditor = getErrorAuditor();

console.log('📋 RETRYABLE_PATTERNS (' + RETRYABLE_PATTERNS.length + '):');
console.log('   ' + RETRYABLE_PATTERNS.join(', '));
console.log('\n📋 NON_RETRYABLE_PATTERNS (' + NON_RETRYABLE_PATTERNS.length + '):');
console.log('   ' + NON_RETRYABLE_PATTERNS.join(', '));
console.log('\n');

let passed = 0;
let failed = 0;

for (const testCase of TEST_CASES) {
    const { name, error, expectedRetryable, expectedType, reason } = testCase;

    const actualRetryable = auditor.isRetryableError(error);
    const actualType = auditor.classifyError(error.message);

    const retryableMatch = actualRetryable === expectedRetryable;
    const typeMatch = actualType === expectedType;
    const success = retryableMatch && typeMatch;

    if (success) {
        passed++;
        console.log(`\x1b[32m✅ PASS\x1b[0m [${name}]`);
    } else {
        failed++;
        console.log(`\x1b[31m❌ FAIL\x1b[0m [${name}]`);
    }

    console.log(`   错误消息: "${error.message}"`);
    console.log(`   重试判断: ${actualRetryable} (期望: ${expectedRetryable}) ${retryableMatch ? '✓' : '✗'}`);
    console.log(`   错误类型: ${actualType} (期望: ${expectedType}) ${typeMatch ? '✓' : '✗'}`);
    console.log(`   判定逻辑: ${reason}`);

    if (!success) {
        console.log(`   \x1b[33m⚠️  预期与实际不符！\x1b[0m`);
    }
    console.log('');
}

// ============================================================================
// 测试结果汇总
// ============================================================================

console.log('═══════════════════════════════════════════════════════════════════════');
console.log(`  测试结果: \x1b[32m${passed} 通过\x1b[0m / \x1b[31m${failed} 失败\x1b[0m / ${TEST_CASES.length} 总计`);
console.log('═══════════════════════════════════════════════════════════════════════');

// 特殊检查: CF_BLOCK 是否被错误标记为可重试
console.log('\n');
console.log('═══════════════════════════════════════════════════════════════════════');
console.log('  \x1b[33m[CF_BLOCK 专项检查]\x1b[0m');
console.log('═══════════════════════════════════════════════════════════════════════');

const cfBlockInRetryable = RETRYABLE_PATTERNS.includes('CF_BLOCK');
const cfBlockInNonRetryable = NON_RETRYABLE_PATTERNS.includes('CF_BLOCK');

console.log(`  CF_BLOCK 在 RETRYABLE_PATTERNS: ${cfBlockInRetryable ? '\x1b[31m是 (错误!)\x1b[0m' : '\x1b[32m否\x1b[0m'}`);
console.log(`  CF_BLOCK 在 NON_RETRYABLE_PATTERNS: ${cfBlockInNonRetryable ? '\x1b[32m是\x1b[0m' : '\x1b[33m否 (应该添加)\x1b[0m'}`);

if (cfBlockInRetryable && !cfBlockInNonRetryable) {
    console.log('\n  \x1b[31m🚨 严重问题: CF_BLOCK 被错误放入 RETRYABLE_PATTERNS！\x1b[0m');
    console.log('  Cloudflare 阻止需要刷新身份，不应自动重试！');
}

console.log('\n');

// 退出码
process.exit(failed > 0 ? 1 : 0);
