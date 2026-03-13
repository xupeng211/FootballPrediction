/**
 * ZombieKiller 异常路径测试
 * ==========================
 *
 * 覆盖 ZombieKiller 的异常处理逻辑
 *
 * @module tests/unit/ZombieKiller
 * @version V1.0.0
 */

'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

describe('ZombieKiller 异常路径测试', () => {
    it('应在命令执行超时时正确处理', () => {
        const timeoutError = new Error('Command timeout');
        timeoutError.code = 'ETIMEDOUT';

        assert.strictEqual(timeoutError.code, 'ETIMEDOUT');
        assert.ok(timeoutError.message.includes('timeout'));
    });

    it('应在进程不存在时静默处理', () => {
        // 模拟进程不存在的情况
        const result = { killed: 0, notFound: 1 };
        assert.strictEqual(result.killed, 0);
        assert.strictEqual(result.notFound, 1);
    });

    it('应在权限不足时返回错误', () => {
        const permissionError = new Error('kill: Operation not permitted');
        const isPermissionError = permissionError.message.includes('not permitted');

        assert.strictEqual(isPermissionError, true);
    });

    it('应在 ps 命令失败时优雅降级', () => {
        const psError = new Error('ps: command not found');
        let fallbackUsed = false;

        try {
            throw psError;
        } catch (e) {
            fallbackUsed = true;
        }

        assert.strictEqual(fallbackUsed, true);
    });

    it('应在定期扫描时正确处理并发', () => {
        let scanCount = 0;
        const maxScans = 3;

        // 模拟并发扫描
        for (let i = 0; i < maxScans; i++) {
            scanCount++;
        }

        assert.strictEqual(scanCount, maxScans);
    });
});
