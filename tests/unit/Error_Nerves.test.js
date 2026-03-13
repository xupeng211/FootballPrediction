/**
 * Error_Nerves.test.js - TITAN 痛觉神经测试
 * ==========================================
 *
 * 12 项原子级测试，验证 ErrorAuditor 对抗性报错的精准识别能力。
 * @module tests/unit/Error_Nerves
 * @version V1.0.0
 */

'use strict';

const { describe, it, beforeEach } = require('node:test');
const assert = require('node:assert');
const { ErrorAuditor, ErrorType, resetErrorAuditor } = require('../../src/core/harvesters/ErrorAuditor');

describe('TITAN 痛觉神经测试 - 12 根神经纤维', () => {
    let auditor;

    beforeEach(() => {
        resetErrorAuditor();
        auditor = new ErrorAuditor();
    });

    // ============================================================================
    // A. 封锁识别 (Block Recognition - 4项)
    // ============================================================================

    describe('A. 封锁识别 (Block Recognition)', () => {
        it('A1: 403 Forbidden 必须返回 RATE_LIMITED 且不可重试', () => {
            const testCases = [
                '403 Forbidden',
                'HTTP 403: Access Forbidden',
                'Status code: 403',
                '403 - Forbidden'
            ];

            for (const msg of testCases) {
                const type = auditor.classifyError(msg);
                const retryable = auditor.isRetryableError(msg);

                assert.strictEqual(type, ErrorType.RATE_LIMITED,
                    `${msg} 应被分类为 RATE_LIMITED`);
                assert.strictEqual(retryable, false,
                    `${msg} 应不可重试`);
            }
        });

        it('A2: Cloudflare Turnstile 必须返回 BLOCKED 且不可重试', () => {
            const testCases = [
                'Cloudflare Turnstile challenge',
                'Turnstile verification required',
                'CF Turnstile blocked',
                'Managed Challenge (Turnstile)'
            ];

            for (const msg of testCases) {
                const type = auditor.classifyError(msg);
                const retryable = auditor.isRetryableError(msg);

                assert.strictEqual(type, ErrorType.BLOCKED,
                    `${msg} 应被分类为 BLOCKED`);
                assert.strictEqual(retryable, false,
                    `${msg} 应不可重试`);
            }
        });

        it('A3: CF_BLOCK: Access denied 必须判定为不可重试', () => {
            const testCases = [
                'CF_BLOCK: Access denied',
                'CF_BLOCK detected',
                'Access denied by Cloudflare',
                'CF_BLOCK: Request blocked'
            ];

            for (const msg of testCases) {
                const type = auditor.classifyError(msg);
                const retryable = auditor.isRetryableError(msg);

                assert.strictEqual(type, ErrorType.BLOCKED,
                    `${msg} 应被分类为 BLOCKED`);
                assert.strictEqual(retryable, false,
                    `${msg} 应不可重试`);
            }
        });

        it('A4: captcha 关键字必须被识别为 BLOCKED', () => {
            const testCases = [
                'captcha required',
                'CAPTCHA verification needed',
                'Please solve the captcha',
                'reCAPTCHA challenge',
                'hCaptcha verification'
            ];

            for (const msg of testCases) {
                const type = auditor.classifyError(msg);
                const retryable = auditor.isRetryableError(msg);

                assert.strictEqual(type, ErrorType.BLOCKED,
                    `${msg} 应被分类为 BLOCKED`);
                assert.strictEqual(retryable, false,
                    `${msg} 应不可重试`);
            }
        });
    });

    // ============================================================================
    // B. 网络抖动识别 (Network Resilience - 4项)
    // ============================================================================

    describe('B. 网络抖动识别 (Network Resilience)', () => {
        it('B5: ECONNRESET 必须返回 NETWORK_ERROR 且【允许重试】', () => {
            const testCases = [
                'ECONNRESET',
                'Error: ECONNRESET',
                'code: ECONNRESET',
                'ECONNRESET: Connection reset'
            ];

            for (const msg of testCases) {
                const type = auditor.classifyError(msg);
                const retryable = auditor.isRetryableError(msg);

                assert.strictEqual(type, ErrorType.NETWORK_ERROR,
                    `${msg} 应被分类为 NETWORK_ERROR`);
                assert.strictEqual(retryable, true,
                    `${msg} 应允许重试`);
            }
        });

        it('B6: Connection reset by peer 必须返回 NETWORK_ERROR 且【允许重试】', () => {
            const testCases = [
                'Connection reset by peer',
                'Error: Connection reset by peer',
                'read ECONNRESET: Connection reset by peer',
                'socket hang up: Connection reset by peer'
            ];

            for (const msg of testCases) {
                const type = auditor.classifyError(msg);
                const retryable = auditor.isRetryableError(msg);

                assert.strictEqual(type, ErrorType.NETWORK_ERROR,
                    `${msg} 应被分类为 NETWORK_ERROR`);
                assert.strictEqual(retryable, true,
                    `${msg} 应允许重试`);
            }
        });

        it('B7: ETIMEDOUT 必须判定为【允许重试】', () => {
            const testCases = [
                'ETIMEDOUT',
                'Error: ETIMEDOUT',
                'connect ETIMEDOUT',
                'ETIMEDOUT: Operation timed out'
            ];

            for (const msg of testCases) {
                const type = auditor.classifyError(msg);
                const retryable = auditor.isRetryableError(msg);

                assert.strictEqual(type, ErrorType.TIMEOUT,
                    `${msg} 应被分类为 TIMEOUT`);
                assert.strictEqual(retryable, true,
                    `${msg} 应允许重试`);
            }
        });

        it('B8: socket hang up 必须被正确分类为网络错误', () => {
            const testCases = [
                'socket hang up',
                'Error: socket hang up',
                'Socket hung up unexpectedly',
                'request failed: socket hang up'
            ];

            for (const msg of testCases) {
                const type = auditor.classifyError(msg);
                const retryable = auditor.isRetryableError(msg);

                assert.strictEqual(type, ErrorType.NETWORK_ERROR,
                    `${msg} 应被分类为 NETWORK_ERROR`);
                assert.strictEqual(retryable, true,
                    `${msg} 应允许重试`);
            }
        });
    });

    // ============================================================================
    // C. 边缘情况测试 (Edge Cases - 4项)
    // ============================================================================

    describe('C. 边缘情况测试 (Edge Cases)', () => {
        it('C9: 验证对包含 Timeout (首字母大写) 的消息识别', () => {
            const testCases = [
                'Timeout exceeded',
                'Request Timeout',
                'TIMEOUT: Operation failed',
                'Navigation Timeout'
            ];

            for (const msg of testCases) {
                const type = auditor.classifyError(msg);
                const retryable = auditor.isRetryableError(msg);

                assert.strictEqual(type, ErrorType.TIMEOUT,
                    `${msg} 应被分类为 TIMEOUT`);
                assert.strictEqual(retryable, true,
                    `${msg} 应允许重试`);
            }
        });

        it('C10: 验证对空错误消息或 null 错误的默认分类', () => {
            // 空字符串
            let type = auditor.classifyError('');
            assert.strictEqual(type, ErrorType.UNKNOWN,
                '空字符串应返回 UNKNOWN');

            // null
            type = auditor.classifyError(null);
            assert.strictEqual(type, ErrorType.UNKNOWN,
                'null 应返回 UNKNOWN');

            // undefined
            type = auditor.classifyError(undefined);
            assert.strictEqual(type, ErrorType.UNKNOWN,
                'undefined 应返回 UNKNOWN');

            // 只有空白字符
            type = auditor.classifyError('   ');
            assert.strictEqual(type, ErrorType.UNKNOWN,
                '空白字符应返回 UNKNOWN');
        });

        it('C11: 验证统计功能 - BLOCKED 错误计数器正确自增', () => {
            // 初始状态
            let stats = auditor.getStats();
            assert.strictEqual(stats.totalErrors, 0, '初始总错误数应为 0');
            assert.strictEqual(stats.byType[ErrorType.BLOCKED], undefined,
                '初始 BLOCKED 计数应为 undefined');

            // 记录 3 个 BLOCKED 错误
            auditor.recordError('CF_BLOCK: Access denied');
            auditor.recordError('Turnstile challenge');
            auditor.recordError('captcha required');

            stats = auditor.getStats();
            assert.strictEqual(stats.totalErrors, 3, '总错误数应为 3');
            assert.strictEqual(stats.byType[ErrorType.BLOCKED], 3,
                'BLOCKED 计数应为 3');

            // 再记录 1 个
            auditor.recordError('403 Forbidden');
            stats = auditor.getStats();
            assert.strictEqual(stats.totalErrors, 4, '总错误数应为 4');
            assert.strictEqual(stats.byType[ErrorType.RATE_LIMITED], 1,
                'RATE_LIMITED 计数应为 1');
        });

        it('C12: 验证退避建议 - RATE_LIMITED 错误必须返回大于 5000ms 的值', () => {
            const backoff1 = auditor.getRecommendedBackoff(ErrorType.RATE_LIMITED, 1);
            const backoff2 = auditor.getRecommendedBackoff(ErrorType.RATE_LIMITED, 2);
            const backoff3 = auditor.getRecommendedBackoff(ErrorType.RATE_LIMITED, 3);

            // 第一次尝试应返回 30000ms
            assert.strictEqual(backoff1, 30000,
                'RATE_LIMITED 第1次尝试退避应为 30000ms');
            assert.ok(backoff1 > 5000,
                `RATE_LIMITED 退避值 ${backoff1} 应大于 5000ms`);

            // 后续尝试应指数增长但仍大于 5000ms
            assert.ok(backoff2 > 5000,
                `RATE_LIMITED 第2次退避值 ${backoff2} 应大于 5000ms`);
            assert.ok(backoff3 > 5000,
                `RATE_LIMITED 第3次退避值 ${backoff3} 应大于 5000ms`);

            // 验证指数退避增长
            assert.ok(backoff2 > backoff1,
                '第2次退避应大于第1次');
            assert.ok(backoff3 > backoff2,
                '第3次退避应大于第2次');
        });
    });
});
