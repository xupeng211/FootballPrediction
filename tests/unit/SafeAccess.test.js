/**
 * SafeAccess 单元测试
 * ==============================================
 *
 * 测试安全访问工具函数
 *
 * @module tests/unit/SafeAccess.test
 */

'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');
const { safeGet, hasPath, safeArrayGet, is } = require('../../src/core/utils/SafeAccess');

describe('SafeAccess', () => {
    describe('safeGet', () => {
        const testObj = {
            a: {
                b: {
                    c: 42,
                    d: null
                },
                arr: [1, 2, 3]
            },
            x: 'value'
        };

        it('应正确获取嵌套属性', () => {
            assert.strictEqual(safeGet(testObj, 'a.b.c'), 42);
        });

        it('应正确获取数组元素', () => {
            assert.strictEqual(safeGet(testObj, 'a.arr.0'), 1);
            assert.strictEqual(safeGet(testObj, 'a.arr.2'), 3);
        });

        it('应在路径不存在时返回默认值', () => {
            assert.strictEqual(safeGet(testObj, 'a.b.e', 'default'), 'default');
            assert.strictEqual(safeGet(testObj, 'x.y.z', null), null);
        });

        it('应处理 null 值', () => {
            assert.strictEqual(safeGet(testObj, 'a.b.d', 'fallback'), 'fallback');
        });

        it('应处理 null/undefined 源对象', () => {
            assert.strictEqual(safeGet(null, 'a.b', 'default'), 'default');
            assert.strictEqual(safeGet(undefined, 'a.b', 'default'), 'default');
        });

        it('应处理数组越界', () => {
            assert.strictEqual(safeGet(testObj, 'a.arr.10', 'default'), 'default');
            assert.strictEqual(safeGet(testObj, 'a.arr.-1', 'default'), 'default');
        });
    });

    describe('hasPath', () => {
        const testObj = { a: { b: 1 } };

        it('应在路径存在时返回 true', () => {
            assert.strictEqual(hasPath(testObj, 'a.b'), true);
            assert.strictEqual(hasPath(testObj, 'a'), true);
        });

        it('应在路径不存在时返回 false', () => {
            assert.strictEqual(hasPath(testObj, 'a.c'), false);
            assert.strictEqual(hasPath(testObj, 'x.y'), false);
        });
    });

    describe('safeArrayGet', () => {
        const arr = [1, 2, 3];

        it('应正确获取数组元素', () => {
            assert.strictEqual(safeArrayGet(arr, 0), 1);
            assert.strictEqual(safeArrayGet(arr, 2), 3);
        });

        it('应处理越界索引', () => {
            assert.strictEqual(safeArrayGet(arr, 10, 'default'), 'default');
            assert.strictEqual(safeArrayGet(arr, -1, 'default'), 'default');
        });

        it('应处理非数组输入', () => {
            assert.strictEqual(safeArrayGet(null, 0, 'default'), 'default');
            assert.strictEqual(safeArrayGet('string', 0, 'default'), 'default');
        });
    });

    describe('is 类型检查', () => {
        it('is.object 应正确识别对象', () => {
            assert.strictEqual(is.object({}), true);
            assert.strictEqual(is.object([]), false);
            assert.strictEqual(is.object(null), false);
        });

        it('is.array 应正确识别数组', () => {
            assert.strictEqual(is.array([]), true);
            assert.strictEqual(is.array({}), false);
        });

        it('is.string 应正确识别字符串', () => {
            assert.strictEqual(is.string('test'), true);
            assert.strictEqual(is.string(123), false);
        });

        it('is.number 应正确识别数字', () => {
            assert.strictEqual(is.number(42), true);
            assert.strictEqual(is.number(NaN), false);
            assert.strictEqual(is.number('42'), false);
        });

        it('is.empty 应正确识别空值', () => {
            assert.strictEqual(is.empty(null), true);
            assert.strictEqual(is.empty(''), true);
            assert.strictEqual(is.empty([]), true);
            assert.strictEqual(is.empty({}), true);
            assert.strictEqual(is.empty('value'), false);
            assert.strictEqual(is.empty([1]), false);
        });
    });
});
