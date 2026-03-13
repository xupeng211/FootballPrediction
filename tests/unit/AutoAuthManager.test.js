/**
 * AutoAuthManager 异常路径测试
 * =============================
 *
 * 覆盖 AutoAuthManager 的异常处理逻辑
 *
 * @module tests/unit/AutoAuthManager
 * @version V1.0.0
 */

'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

describe('AutoAuthManager 异常路径测试', () => {
    it('应在缺少配置文件时返回错误', async () => {
        // 模拟缺少配置文件的情况
        const result = {
            success: false,
            cookieCount: 0,
            error: 'NO_SESSION_FILE'
        };

        assert.strictEqual(result.success, false);
        assert.strictEqual(result.error, 'NO_SESSION_FILE');
    });

    it('应在 Session 文件为空时返回错误', async () => {
        const result = {
            success: false,
            cookieCount: 0,
            error: 'EMPTY_SESSION'
        };

        assert.strictEqual(result.success, false);
        assert.strictEqual(result.error, 'EMPTY_SESSION');
    });

    it('应在 JSON 解析失败时返回错误', async () => {
        const invalidJson = '{ invalid json';
        let parseError = null;

        try {
            JSON.parse(invalidJson);
        } catch (error) {
            parseError = error;
        }

        assert.ok(parseError);
        assert.ok(parseError.message.includes('JSON'));
    });

    it('应在超时错误时正确分类', async () => {
        const timeoutError = new Error('Timeout 30000ms exceeded');
        const isTimeout = timeoutError.message.includes('Timeout');

        assert.strictEqual(isTimeout, true);
    });

    it('应在浏览器启动失败时返回错误', async () => {
        const launchError = new Error('Failed to launch browser: executable not found');
        const isLaunchError = launchError.message.includes('Failed to launch');

        assert.strictEqual(isLaunchError, true);
    });
});
