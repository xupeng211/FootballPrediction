/**
 * SafeAccess - 安全的对象属性访问工具
 * ==============================================
 *
 * 提供可选链式的安全属性访问，杜绝 undefined 错误。
 *
 * @module core/utils/SafeAccess
 * @version V175.0.0
 */

'use strict';

/**
 * 安全获取嵌套对象属性
 * @param {Object} obj - 源对象
 * @param {string} path - 属性路径，用 '.' 分隔
 * @param {*} defaultValue - 默认值
 * @returns {*}
 *
 * @example
 * safeGet(data, 'content.stats.0.stats.0.value', null)
 * // 等同于 data?.content?.stats?.[0]?.stats?.[0]?.value ?? null
 */
function safeGet(obj, path, defaultValue = undefined) {
    if (!obj || typeof path !== 'string') {
        return defaultValue;
    }

    const keys = path.split('.');
    let current = obj;

    for (const key of keys) {
        // 处理数组索引 (如 "0", "1")
        if (/^\d+$/.test(key) && Array.isArray(current)) {
            const index = parseInt(key);
            if (index < 0 || index >= current.length) {
                return defaultValue;
            }
            current = current[index];
        } else if (current && typeof current === 'object' && key in current) {
            current = current[key];
        } else {
            return defaultValue;
        }

        if (current === undefined || current === null) {
            return defaultValue;
        }
    }

    return current ?? defaultValue;
}

/** 用于检测路径不存在的唯一标记 */
const NOT_FOUND = Symbol('not-found');

/**
 * 安全检查对象是否有指定路径
 * @param {Object} obj - 源对象
 * @param {string} path - 属性路径
 * @returns {boolean}
 */
function hasPath(obj, path) {
    return safeGet(obj, path, NOT_FOUND) !== NOT_FOUND;
}

/**
 * 安全获取数组元素
 * @param {Array} arr - 源数组
 * @param {number} index - 索引
 * @param {*} defaultValue - 默认值
 * @returns {*}
 */
function safeArrayGet(arr, index, defaultValue = undefined) {
    if (!Array.isArray(arr) || index < 0 || index >= arr.length) {
        return defaultValue;
    }
    return arr[index] ?? defaultValue;
}

/**
 * 类型检查工具
 */
const is = {
    object: (v) => v !== null && typeof v === 'object' && !Array.isArray(v),
    array: (v) => Array.isArray(v),
    string: (v) => typeof v === 'string',
    number: (v) => typeof v === 'number' && !isNaN(v),
    boolean: (v) => typeof v === 'boolean',
    function: (v) => typeof v === 'function',
    nullOrUndefined: (v) => v === null || v === undefined,
    empty: (v) => v === null || v === undefined || v === '' ||
               (Array.isArray(v) && v.length === 0) ||
               (typeof v === 'object' && Object.keys(v).length === 0)
};

module.exports = {
    safeGet,
    hasPath,
    safeArrayGet,
    is
};
