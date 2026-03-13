/**
 * ErrorAuditor - 错误审计员测试
 * =====================================
 *
 * 测试覆盖：
 * - 错误分类逻辑
 * - 可重试判断
 * - 推荐退避时间
 * - 统计功能
 */

const { describe, it, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert');

const { ErrorAuditor } = require('../../src/core/harvesters/ErrorAuditor');
const { ErrorType, RETRYABLE_PATTERNS, NON_RETRYABLE_PATTERNS } = require('../../src/core/harvesters/ErrorAuditor');

describe('ErrorAuditor 测试', () => {
    let auditor;

    beforeEach(() => {
        auditor = new ErrorAuditor();
    });

    afterEach(() => {
        auditor.resetStats();
    });

    // ========================================================================
    // 测试 1: 错误分类
    // ========================================================================

    describe('错误分类', () => {
        it('应该正确识别 BLOCKED 错误 (Turnstile)', () => {
            const errorType = auditor.classifyError('Turnstile challenge required');
            assert.strictEqual(errorType, ErrorType.BLOCKED);
        });

        it('应该正确识别 BLOCKED 错误 (Captcha)', () => {
            const errorType = auditor.classifyError('Captcha verification failed');
            assert.strictEqual(errorType, ErrorType.BLOCKED);
        });

        it('应该正确识别 BLOCKED 错误 (Circuit Breaker)', () => {
            const errorType = auditor.classifyError('circuit_breaker_open');
            assert.strictEqual(errorType, ErrorType.BLOCKED);
        });

        it('应该正确识别 RATE_LIMITED 错误', () => {
            const errorType = auditor.classifyError('403 Forbidden');
            assert.strictEqual(errorType, ErrorType.RATE_LIMITED);
        });

        it('应该正确识别 NETWORK_ERROR 错误', () => {
            const errorType = auditor.classifyError('Connection refused');
            assert.strictEqual(errorType, ErrorType.NETWORK_ERROR);
        });

        it('应该正确识别 TIMEOUT 错误', () => {
            const errorType = auditor.classifyError('Request timeout');
            assert.strictEqual(errorType, ErrorType.TIMEOUT);
        });

        it('应该正确识别 NO_data 错误', () => {
            const errorType = auditor.classifyError('no_data');
            assert.strictEqual(errorType, ErrorType.NO_DATA);
        });

        it('应该对未知错误返回 UNKNOWN', () => {
            const errorType = auditor.classifyError('Some random error');
            assert.strictEqual(errorType, ErrorType.UNKNOWN);
        });
    });

    // ========================================================================
    // 测试 2: 可重试判断
    // ========================================================================

    describe('可重试判断', () => {
        it('应该将网络错误标记为可重试', () => {
            const retryableErrors = [
                'ERR_CONNECTION_CLOSED',
                'ERR_CONNECTION_RESET',
                'ERR_TIMED_OUT',
                'ETIMEDOUT',
                'ECONNRESET',
                'ECONNREFUSED',
                'ENOTFOUND',
                'net::ERR_CONNECTION_FAILED',
                'Navigation timeout',
                'CF_BLOCK'
            ];

            for (const errorMsg of retryableErrors) {
                const isRetryable = auditor.isRetryableError(new Error(errorMsg));
                assert.strictEqual(isRetryable, true, `${errorMsg} 应该是可重试的`);
            }
        });

        it('应该将 BLOCKED 错误标记为不可重试', () => {
            const nonRetryableErrors = [
                '403 Forbidden',
                'ERR_BLOCKED_BY_CLIENT',
                'Access denied',
                'Turnstile challenge required'
            ];

            for (const errorMsg of nonRetryableErrors) {
                const isRetryable = auditor.isRetryableError(new Error(errorMsg));
                assert.strictEqual(isRetryable, false, `${errorMsg} 应该是不可重试的`);
            }
        });

        it('应该将 SIZE_TOO_SMALL 标记为可重试', () => {
            const isRetryable = auditor.isRetryableError(new Error('SIZE_TOO_SMALL:500'));
            assert.strictEqual(isRetryable, true, 'SIZE_TOO_SMALL 应该是可重试的');
        });

        it('应该将 no_data 标记为不可重试', () => {
            const isRetryable = auditor.isRetryableError(new Error('NO_DATA:无法获取数据'));
            assert.strictEqual(isRetryable, false, 'NO_DATA 应该是不可重试的');
        });
    });

    // ========================================================================
    // 测试 3: 推荐退避时间
    // ========================================================================

    describe('推荐退避时间', () => {
        it('BLOCKED 错误应该返回 60000ms', () => {
            const backoff = auditor.getRecommendedBackoff(ErrorType.BLOCKED, 1);
            assert.strictEqual(backoff, 60000);
        });

        it('BLOCKED 错误第 2 次尝试应该返回更长时间', () => {
            const backoff1 = auditor.getRecommendedBackoff(ErrorType.BLOCKED, 1);
            const backoff2 = auditor.getRecommendedBackoff(ErrorType.BLOCKED, 2);
            const backoff3 = auditor.getRecommendedBackoff(ErrorType.BLOCKED, 3);

            // 指数退避，最大 60 秒
            assert.ok(backoff2 > backoff1, '第 2 次应该更长');
            assert.ok(backoff3 > backoff2, '第 3 次应该更长');
            assert.ok(backoff3 <= 60000, '第 3 次退避应该不超过 60 秒');
        });

        it('RATE_LIMITED 错误应该返回 30000ms', () => {
            const backoff = auditor.getRecommendedBackoff(ErrorType.RATE_LIMITED, 1);
            assert.strictEqual(backoff, 30000);
        });

        it('TIMEOUT 错误应该返回 10000ms', () => {
            const backoff = auditor.getRecommendedBackoff(ErrorType.TIMEOUT, 1);
            assert.strictEqual(backoff, 10000);
        });

        it('NETWORK_ERROR 应该返回 5000ms', () => {
            const backoff = auditor.getRecommendedBackoff(ErrorType.NETWORK_ERROR, 1);
            assert.strictEqual(backoff, 5000);
        });

        it('NO_DATA 错误应该返回 0ms', () => {
            const backoff = auditor.getRecommendedBackoff(ErrorType.NO_DATA, 0);
            assert.strictEqual(backoff, 0);
        });

        it('UNKNOWN 错误应该返回 5000ms', () => {
            const backoff = auditor.getRecommendedBackoff(ErrorType.UNKNOWN, 1);
            assert.strictEqual(backoff, 5000);
        });
    });

    // ========================================================================
    // 测试 4: 统计功能
    // ========================================================================

    describe('统计功能', () => {
        it('应该正确记录错误', () => {
            const result = auditor.recordError('Turnstile required');
            assert.strictEqual(result.type, ErrorType.BLOCKED);
            assert.strictEqual(result.retryable, false);

            const result2 = auditor.recordError('ERR_CONNECTION_RESET');
            assert.strictEqual(result2.type, ErrorType.NETWORK_ERROR);
            assert.strictEqual(result2.retryable, true);
        });

        it('应该正确获取统计', () => {
            const stats = auditor.getStats();
            assert.strictEqual(stats.totalErrors, 2);
            assert.strictEqual(stats.byType[ErrorType.BLOCKED, 1);
            assert.strictEqual(stats.byType[ErrorType.NETWORK_ERROR, 1);
        });

        it('应该重置统计', () => {
            auditor.resetStats();
            const stats = auditor.getStats();
            assert.strictEqual(stats.totalErrors, 0);
            assert.deepStrictEqual(stats.byType, {});
        });
    });

    // ========================================================================
    // 测试 5: 辅助方法
    // ========================================================================

    describe('辅助方法', () => {
        it('isBlockingError 应该返回 true', () => {
            assert.strictEqual(auditor.isBlockingError(ErrorType.BLOCKED), true);
        });

        it('isBlockingError 对其他类型应返回 false', () => {
            assert.strictEqual(auditor.isBlockingError(ErrorType.RATE_LIMITED), false);
            assert.strictEqual(auditor.isBlockingError(ErrorType.TIMEout), false);
            assert.strictEqual(auditor.isBlockingError(ErrorType.NETWORK_ERROR), false);
        });

        it('isRateLimitedError 应该返回 true', () => {
            assert.strictEqual(auditor.isRateLimitedError(ErrorType.RATE_LIMITED), true);
        });

        it('isRateLimitedError 对其他类型应返回 false', () => {
            assert.strictEqual(auditor.isRateLimitedError(ErrorType.BLOCKED), false);
            assert.strictEqual(auditor.isRateLimitedError(ErrorType.TIMEout), false);
        });

        it('formatErrorForLog 应该正确格式化', () => {
            const formatted = auditor.formatErrorForLog('Turnstile required');
            assert.strictEqual(formatted, '[BLOCKED] (不可重试) Turnstile required');
        });

        it('formatErrorForLog 应该标记可重试错误', () => {
            const formatted = auditor.formatErrorForLog('ERR_CONNECTION_RESET');
            assert.strictEqual(formatted, '[NETWORK_ERROR] (可重试) ERR_CONNECTION_RESET');
        });
    });
});
