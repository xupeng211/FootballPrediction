/**
 * SafeAccess - 安全数据访问工具
 * =============================
 *
 * 提供安全的对象属性访问函数
 * @module core/utils/SafeAccess
 */

'use strict';

/**
 * 安全获取对象属性
 * @param {object} obj - 源对象
 * @param {string} path - 属性路径 (如 'a.b.c')
 * @param {*} defaultValue - 默认值
 * @returns {*}
 */
function safeGet(obj, path, defaultValue = undefined) {
    if (!obj || typeof obj !== 'object') {
        return defaultValue;
    }

    const keys = path.split('.');
    let current = obj;

    for (const key of keys) {
        if (current === null || current === undefined || typeof current !== 'object') {
            return defaultValue;
        }
        current = current[key];
    }

    return current !== undefined && current !== null ? current : defaultValue;
}

/**
 * 检查路径是否存在
 * @param {object} obj - 源对象
 * @param {string} path - 属性路径
 * @returns {boolean}
 */
function hasPath(obj, path) {
    if (!obj || typeof obj !== 'object') {
        return false;
    }

    const keys = path.split('.');
    let current = obj;

    for (const key of keys) {
        if (current === null || current === undefined || typeof current !== 'object') {
            return false;
        }
        if (!(key in current)) {
            return false;
        }
        current = current[key];
    }

    return true;
}

/**
 * 检查值是否为有效对象
 * @param {*} value
 * @returns {boolean}
 */
function isObject(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
}

/**
 * 检查值是否为数组
 * @param {*} value
 * @returns {boolean}
 */
function isArray(value) {
    return Array.isArray(value);
}

/**
 * 检查值是否为字符串
 * @param {*} value
 * @returns {boolean}
 */
function isString(value) {
    return typeof value === 'string';
}

/**
 * 检查值是否为数字
 * @param {*} value
 * @returns {boolean}
 */
function isNumber(value) {
    return typeof value === 'number' && !isNaN(value);
}

/**
 * 检查值是否为空
 * @param {*} value
 * @returns {boolean}
 */
function isEmpty(value) {
    if (value === null || value === undefined) return true;
    if (isString(value) && value === '') return true;
    if (isArray(value) && value.length === 0) return true;
    if (isObject(value) && Object.keys(value).length === 0) return true;
    return false;
}

/**
 * 安全获取数组元素
 * @param {Array} arr - 源数组
 * @param {number} index - 索引
 * @param {*} defaultValue - 默认值
 * @returns {*}
 */
function safeArrayGet(arr, index, defaultValue = undefined) {
    if (!isArray(arr)) {
        return defaultValue;
    }
    if (index < 0 || index >= arr.length) {
        return defaultValue;
    }
    return arr[index] !== undefined ? arr[index] : defaultValue;
}

/**
 * is 类型检查对象
 */
const is = {
    object: isObject,
    array: isArray,
    string: isString,
    number: isNumber,
    empty: isEmpty
};

module.exports = { safeGet, hasPath, safeArrayGet, is };
